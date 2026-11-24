#!/usr/bin/env python3
"""C11 judgment identity: document copies, judgments, proceedings, versions and renditions.

Reads (never writes) the Cycle 10 HF judgment audit (batches and registers) and the source bytes held as git blobs at a
pinned commit of the corpus repository, and writes:

  outputs/JUDGMENT_IDENTITY_REGISTER.csv      one row per stored file (3,959): copy -> judgment, proceedings, roles
  outputs/SAME_TEXT_GROUPS.csv                every same-text group, classified, with byte/render/metadata evidence
  outputs/COMPOSITE_AND_VERSION_CANDIDATES.csv files holding more than one document, and corrected-version markers
  outputs/INCOMPLETE_23_RECOVERY_PLAN.csv      per-file recovery plan for the 23 unresolved files
  outputs/IDENTITY_SUMMARY.json               accounting and the evidence-supported distinct-judgment count
  outputs/OUTPUT_SHA256SUMS                   checksums of the files above

Everything is AUTOMATED and NOT_LEGALLY_VERIFIED. Nothing is downloaded, merged or deleted; the tool only reads.

  python -I -B identity_c11.py --repo /home/user/c7 [--check]

--check rebuilds into a temporary directory and compares byte for byte with outputs/. Without PyMuPDF the full
rebuild is impossible; --check then verifies OUTPUT_SHA256SUMS and the accounting identity only and says so.
"""
import argparse, collections, csv, difflib, hashlib, importlib.util, io, json, os, re, subprocess, sys, tempfile
from pathlib import Path

TOOL_VERSION = "c11-identity/2"
HERE = Path(__file__).resolve().parent
PKG = HERE.parent
OUT = PKG / "outputs"
C10 = PKG.parent.parent / "C10-HF-JUDGMENTS"
COMMIT = "ad77758d"
VERIFY = "AUTOMATED_NOT_LEGALLY_VERIFIED"
EMPTY_SHA = hashlib.sha256(b"").hexdigest()
PRIOR_GROUPS, PRIOR_FILES = 62, 292   # C10 reconciliation review finding E2-10
RENDER_DPI = 40
OUTPUT_FILES = ["JUDGMENT_IDENTITY_REGISTER.csv", "SAME_TEXT_GROUPS.csv", "COMPOSITE_AND_VERSION_CANDIDATES.csv",
                "INCOMPLETE_23_RECOVERY_PLAN.csv", "IDENTITY_SUMMARY.json"]

COURT_CODE = {"High Court of Delhi": "DLHC", "High Court of Punjab and Haryana": "PHHC", "High Court of Jammu and Kashmir": "JKHC",
              "Supreme Court of India": "SCI", "Allahabad High Court": "ALHC"}
OFFICIAL_SITE = {
    "DLHC": "Delhi High Court judgment portal (delhihighcourt.nic.in) or the eCourts High Court services order search",
    "PHHC": "Punjab and Haryana High Court website (phhc.gov.in) case status / judgment copy",
    "JKHC": "High Court of J&K and Ladakh website (jkhighcourt.nic.in) judgments",
    "ALHC": "Allahabad High Court website (allahabadhighcourt.in) judgment search",
    "SCI": "Supreme Court of India judgment portal (sci.gov.in) or Digital SCR (digiscr.sci.gov.in)",
}

# ------------------------------------------------------------------------------------------------ patterns
COURT_HDR = re.compile(r"(?:[IiT]N THE (?:HIGH COURT OF|SUPREME COURT OF INDIA|ARMED FORCES TRIBUNAL)"
                       r"|\bHIGH COURT OF (?:JAMMU|DELHI|PUNJAB|JUDICATURE|J&K|THE STATE)[A-Z&,\s]*AT\b)")
COURT_NAME = re.compile(r"(SUPREME COURT OF INDIA|ARMED FORCES TRIBUNAL|HIGH COURT OF (?:JAMMU|DELHI|PUNJAB|JUDICATURE|J&K)[A-Z&,\s]{0,40}?AT\s+[A-Z]+)")
PAGE1 = re.compile(r"\bPage\s+1\s+of\s+(\d{1,4})\b", re.I)
PAGE_K = re.compile(r"\bPage\s+(\d{1,4})\s+of\s+(\d{1,4})\b", re.I)
REPORTABLE = re.compile(r"^\W{0,5}(?:NON[-\s]?)?REPORTABLE\b", re.I)
ROP = re.compile(r"RECORD\s+OF\s+PROCEEDINGS", re.I)
MONTHS_UC = "JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER"
SCR_START = re.compile(r"(?:(?:" + MONTHS_UC + r")\s*[0-9IlO]{1,2}\s*,?\s*[0-9IlO]{4}|[0-9]{1,2}\s+(?:" + MONTHS_UC + r")\s+[0-9]{4})"
                       r"[^\[\]]{0,12}\[[^\[\]]{3,240}?(?:JJ|J|CJI|CJ)\s*\.?\s*\]", re.I)
SCR_HDR = re.compile(r"SUPREME COURT REPORTS|\bS\.\s?C\.\s?R\.", re.I)
STRICT_CORR_UC = re.compile(r"\bCORRECTED\b")   # upper-case heading only
STRICT_CORR = re.compile(r"^\W{0,10}(?:CORRIGENDUM|Corrigendum)\b|\(\s*(?:corrected|modified|rectified)\s+(?:vide|as\s+per|in\s+terms\s+of)\s+"
                         r"(?:the\s+)?(?:order|corrigendum)[^)]{0,80}\)|\bcorrected\s+(?:copy|version|judgment)\b", re.I)
CORR_EXCLUDE = re.compile(r"check\s+corrigendum|corrigendum\s+PPO|corrigendum\s+notification", re.I)
OPERATIVE = re.compile(r"\b(?:dismissed|allowed|disposed\s+of|set\s+aside|quashed|remanded|stands?\s+closed)\b", re.I)
BYTE_MASKS = [rb"<xmp:(?:ModifyDate|CreateDate|MetadataDate)>[^<]*</xmp:(?:ModifyDate|CreateDate|MetadataDate)>",
              rb"/(?:CreationDate|ModDate)\s*\([^)]*\)", rb"/ID\s*\[\s*<[0-9A-Fa-f]*>\s*<[0-9A-Fa-f]*>\s*\]", rb"uuid:[0-9a-fA-F-]+",
              rb"<xmpMM:(?:DocumentID|InstanceID)>[^<]*<", rb"startxref\s+\d+", rb"\d{10} \d{5} [nf]"]
TIER_ORDER = ["BYTES_IDENTICAL_AFTER_MASKING_GENERATION_METADATA", "SAME_BASE_REVISION_DIFFERENT_INCREMENTAL_TAIL",
              "PAGE_CONTENT_STREAMS_AND_IMAGES_IDENTICAL", "PAGE_RENDERS_IDENTICAL", "PAGE_RENDERS_DIFFER", "BYTES_NOT_COMPARABLE"]
CONFIRMING_TIERS = set(TIER_ORDER[:4])

# known findings of the C10 independent review (review/REVIEW_FINDINGS.md); matched on stored metadata, never assumed
REVIEW_COMPOSITE = {"title_substring": "VIJAYNATH JHA", "court": "Supreme Court of India"}
REVIEW_VERSIONS_PATH = "legal_knowledge/judgment_originals/sci/2020/virendra_kumar_2020.pdf"
# a second judgment held inside a stored file, confirmed by a review reading; each gets its own key (file sha + page range)
REVIEW_EXTRA_JUDGMENTS = {
    "0f65307432d16f74f78ea8a4f37ad5d1d4b0e56188273575ac956eab22478d72": {
        "pages": "16-25", "court": "Supreme Court of India", "case_ny": (129, 2018), "date": "2018-02-16", "proceeding": "SCI:WPC-129-2018",
        "title": "Adarsh Cooperative Housing Society Ltd. v. Union of India, W.P.(C) 129/2018, SC, 16-02-2018, [2018] 4 SCR 575",
        "source": "C10 REVIEW_FINDINGS.md (composite); court corrected to Supreme Court by the C11 identity reading and the C11 review"},
    "081a8b22679359abc84e8a827510905b4dac8ce09f9cf0579f5f923949d2efa0": {
        "pages": "9-10", "court": "High Court of Delhi", "case_ny": (2881, 2008), "date": "2009-11-13",
        "proceeding": "DLHC:CM-11902-2009 in WPC-2881-2008",
        "title": "Delhi HC order of 13.11.2009 (Sanjay Kishan Kaul J.) dismissing an application to modify the judgment of 20.11.2008",
        "source": "C11 independent identity review (finding F1), confirmed by the automated additional-order detector"},
}
# one judgment delivered as separate opinions with no majority (review-confirmed)
REVIEW_SPLIT = {
    "b64df349c9f5158baca80734718844d35b7b98bc8d3741ee9b98b0808ce1c984":
        "TWO_OPINIONS_SPLIT_VERDICT pp.1-193 Rajiv Shakdher J. | pp.194-393 C. Hari Shankar J. (same cases, date, 2022/DHC/001825)",
}


# ------------------------------------------------------------------------------------------------ helpers
def load_jextract():
    spec = importlib.util.spec_from_file_location("c10_jextract", C10 / "tools" / "jextract.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def rcsv(p):
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def csv_text(fields, rows):
    s = io.StringIO()
    w = csv.DictWriter(s, fieldnames=fields, lineterminator="\n", extrasaction="raise")
    w.writeheader()
    for r in rows:
        w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fields})
    return s.getvalue()


def sha(b):
    return hashlib.sha256(b).hexdigest()


def collapse(t):
    return re.sub(r"\s+", " ", t or "").strip()


def alnum_key(t):
    """Letters only: punctuation/quote glyphs that a PDF generator maps to digits or symbols do not count."""
    return sha(re.sub(r"[^a-z]", "", (t or "").lower()).encode())


def digits_key(t):
    """Multi-digit numbers in order, with clock times (download/signing stamps such as 13:35:59) removed.

    Two orders in different cases can share every word and differ only in the case number; this key keeps them apart,
    while single digits (a quote glyph extracted as 9) and per-download time stamps do not count."""
    return sha("|".join(re.findall(r"\d{2,}", re.sub(r"\d{1,2}:\d{2}(?::\d{2})?", " ", t or ""))).encode())


def corr_marker(head):
    """Page-top correction marker: an upper-case CORRECTED heading, a corrigendum page, or '(corrected vide order ...)'.
    Ordinary uses ('corrigendum PPO', 'click here to check corrigendum', an impugned order 'modified vide') do not count."""
    if CORR_EXCLUDE.search(head):
        head = CORR_EXCLUDE.sub(" ", head)
    return bool(STRICT_CORR_UC.search(head) or STRICT_CORR.search(head))


def letters(t, n=3000):
    return re.sub(r"[^a-z]", "", (t or "").lower())[:n]


def readable_ratio(t):
    nonspace = len(re.sub(r"\s", "", t or ""))
    if not nonspace:
        return 0.0
    good = sum(len(w) for w in re.findall(r"\b(?:[A-Za-z][a-z]{1,}|[A-Z]{2,})\b", t))
    return round(good / nonspace, 3)


def ranges(nums):
    nums = sorted(set(nums))
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append(str(nums[i]) if i == j else f"{nums[i]}-{nums[j]}")
        i = j + 1
    return ",".join(out)


class Blobs:
    """Reads git blobs at the pinned commit through one `git cat-file --batch` process."""

    def __init__(self, repo):
        self.p = subprocess.Popen(["git", "-C", repo, "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def get(self, path):
        self.p.stdin.write(f"{COMMIT}:{path}\n".encode())
        self.p.stdin.flush()
        head = self.p.stdout.readline().split()
        if not head or head[-1] == b"missing":
            return None
        n = int(head[2])
        data = self.p.stdout.read(n)
        self.p.stdout.read(1)
        return data

    def close(self):
        self.p.stdin.close()
        self.p.wait()


def open_pdf(fitz, data):
    try:
        d = fitz.open(stream=data, filetype="pdf")
        n = d.page_count
        return d, n
    except Exception:  # noqa: BLE001  (an unreadable file is a result)
        return None, None


def page_texts(d, n):
    out = []
    for i in range(n):
        try:
            out.append(d[i].get_text())
        except Exception:  # noqa: BLE001
            out.append("")
    return out


def masked_hash(data):
    for p in BYTE_MASKS:
        data = re.sub(p, b"#", data)
    return sha(data)


def content_hash(d, n):
    h = hashlib.sha256()
    for i in range(n):
        try:
            pg = d[i]
            h.update(pg.read_contents())
            for im in pg.get_images(full=True):
                try:
                    h.update(hashlib.sha256(d.xref_stream_raw(im[0])).digest())
                except Exception:  # noqa: BLE001
                    h.update(b"?")
        except Exception:  # noqa: BLE001
            h.update(b"!")
    return h.hexdigest()


def render_hash(fitz, data):
    d, n = open_pdf(fitz, data)
    if d is None:
        return None
    h = hashlib.sha256()
    for i in range(n):
        try:
            h.update(d[i].get_pixmap(dpi=RENDER_DPI, colorspace=fitz.csGRAY).samples)
        except Exception:  # noqa: BLE001
            h.update(b"!")
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------ scan-aware identity (C11 review F1/F3/F6/F7)
# quote and dash glyphs that one PDF generator extracts as digits/symbols ('’' read as 9, '“' as <, '”' as =, '‘' as 8, dashes as 3/4)
GLYPH_MAP = str.maketrans({"’": "9", "“": "<", "”": "=", "‘": "8", "–": "3", "—": "4"})
OCR_DIGITS = str.maketrans("OoQlIiSB", "00011158")
# running footer/header of a common judgment: '<lead case number>/<year> & connected ... Page k of N' (no digits in between)
FOOTER = re.compile(r"\b([0-9OQlIS]{1,6})\s*(?:/|of)\s*([12][0-9OQlIB]{3})(?![0-9])[^0-9\n]{0,45}?P[ao]ge\s*([0-9OQlI]{1,3})\s*of\s*([0-9OQlI]{1,3})", re.I)
POINTER = re.compile(r"For\s+(?:detailed\s+|further\s+)?orders?\s*,?\s*(?:please\s+)?(?:see|refer\s+to)\s+(?:the\s+)?(?:common\s+)?(?:detailed\s+)?(?:order|judgment)?\s*(?:passed\s+)?(?:today\s+)?(?:in\s+)?(.{0,70})", re.I)
NUM_YEAR = re.compile(r"\b([0-9OQlI]{1,6})\s*(?:/|of)\s*([12][0-9OQlI]{3})\b")
LIST_CONT = re.compile(r"\s*(?:,|&|and|\.)\s*(?:No\.?\s*)?(\d{1,6})\s*/\s*((?:19|20)\d{2})\b")
TITLE_END = re.compile(r"\bCORAM\b|\bJ\s?U\s?D\s?G\s?M\s?E\s?N\s?T\b|\bO\s?R\s?D\s?E\s?R\b|\bHON'?BLE\b", re.I)


def glyph_digits_key(t):
    """digits_key after mapping quote/dash glyphs to the digits a faulty generator emits for them (applied to every text)."""
    return digits_key((t or "").translate(GLYPH_MAP))


def _ny(num, yr):
    try:
        n, y = int(num.translate(OCR_DIGITS)), int(yr.translate(OCR_DIGITS))
    except ValueError:
        return None
    return (n, y) if 1900 <= y <= 2030 and n > 0 else None


def footer_keys(texts):
    """(lead number, lead year, N) seen in running footers, with the page numbers k found for each page index."""
    out = []
    for i, t in enumerate(texts):
        for m in FOOTER.finditer(collapse(t)):
            ny = _ny(m.group(1), m.group(2))
            try:
                k, n = int(m.group(3).translate(OCR_DIGITS)), int(m.group(4).translate(OCR_DIGITS))
            except ValueError:
                continue
            if ny and 1 <= k <= n <= 999:
                out.append((i + 1, k, n, ny[0], ny[1]))
    return out


def pointer_keys(texts):
    out = []
    for t in texts[:2]:
        for m in POINTER.finditer(collapse(t)):
            mm = NUM_YEAR.search(m.group(1))
            if mm and _ny(mm.group(1), mm.group(2)):
                out.append(_ny(mm.group(1), mm.group(2)))
    return sorted(set(out))


def cause_title_cases(J, texts):
    """Every case number in the cause title (up to CORAM/JUDGMENT/ORDER, at most 3 pages), including bare continuations
    such as 'WP(C) Nos. 5946/2007, 9382/2007'. Automated and possibly partial."""
    flat = FOOTER.sub(" ", collapse(" ".join(texts[:3])))   # a running header/footer is not part of the cause title
    m = TITLE_END.search(flat, 200)
    head = flat[:m.start()] if m else flat[:6000]
    out = []
    for cm in J.CASE_RE.finditer(head):
        typ = cm.group("type")
        k = J._norm_case(typ, cm.group("num"), cm.group("year"))
        if k not in out:
            out.append(k)
        pos = cm.end()
        while True:
            c2 = LIST_CONT.match(head, pos)
            if not c2:
                break
            k2 = J._norm_case(typ, c2.group(1), c2.group(2))
            if k2 not in out:
                out.append(k2)
            pos = c2.end()
    return out


def head_keys(J, texts):
    """(number, year) of the case numbers opening page 1 and page 2 (a scanned copy often has its own cover sheet first)."""
    out = set()
    for t in texts[:2]:
        for k in cases_in(J, FOOTER.sub(" ", collapse(t))[:600]):
            mm = re.match(r".*-(\d+)-(\d{4})$", k)
            if mm:
                out.add((int(mm.group(1)), int(mm.group(2))))
    return out


def shingles(t):
    w = re.findall(r"[a-z]{2,}", (t or "").lower())
    return {" ".join(w[i:i + 3]) for i in range(len(w) - 2)}


def text_page_match(px, py, thr=0.3, min_sh=40):
    """Share of x's text-bearing pages whose 3-word shingles are contained (>= thr) in some page of y."""
    pages = [s for s in px if len(s) >= min_sh]
    if not pages:
        return 0.0, 0
    hit = 0
    for s in pages:
        best = max((len(s & q) / len(s) for q in py if q), default=0.0)
        if best >= thr:
            hit += 1
    return round(hit / len(pages), 3), len(pages)


def thumb(fitz, page, w=40):
    try:
        r = page.rect
        z = w / max(r.width, 1)
        pm = page.get_pixmap(matrix=fitz.Matrix(z, z), colorspace=fitz.csGRAY)
    except Exception:  # noqa: BLE001
        return None
    v = list(pm.samples[: pm.width * min(pm.height, int(w * 1.4))])
    if len(v) < w * 50:
        return None
    m = sum(v) / len(v)
    sd = (sum((x - m) ** 2 for x in v) / len(v)) ** 0.5
    if sd < 4:
        return None
    return [(x - m) / sd for x in v]


def image_match(tx, ty):
    """Best mean correlation of page thumbnails over page offsets -2..2; returns (mean, pairs, offset)."""
    best = (0.0, 0, 0)
    for off in range(-2, 3):
        cs = []
        for j, a in enumerate(tx):
            k = j + off
            if 0 <= k < len(ty) and a is not None and ty[k] is not None:
                b = ty[k]
                n = min(len(a), len(b))
                cs.append(sum(a[i] * b[i] for i in range(n)) / n)
        if len(cs) >= 3:
            mean = sum(cs) / len(cs)
            if mean > best[0]:
                best = (round(mean, 3), len(cs), off)
    return best


# ------------------------------------------------------------------------------------------------ per-file analysis
def cases_in(J, text):
    out = []
    for m in J.CASE_RE.finditer(text):
        k = J._norm_case(m.group("type"), m.group("num"), m.group("year"))
        if k not in out:
            out.append(k)
    return out


def segment_scan(J, texts):
    """Pages (>=2) that begin a new document, and SCR report starts on any page."""
    p1 = collapse(texts[0]) if texts else ""
    p1_cases = set(cases_in(J, p1[:1500]))
    m = COURT_NAME.search(p1[:600])
    p1_court = m.group(1) if m else ""
    starts = []
    for i, tx in enumerate(texts[1:], start=2):
        flat = collapse(tx)
        head = flat[:250]
        kinds = []
        if COURT_HDR.search(head):
            kinds.append("COURT_HEADER")
        if PAGE1.search(head):
            kinds.append("PAGE_1_OF_N_RESTART")
        if REPORTABLE.search(head[:80]):
            kinds.append("REPORTABLE_HEADER")
        if ROP.search(head):
            kinds.append("RECORD_OF_PROCEEDINGS")
        if kinds:
            starts.append({"page": i, "kinds": kinds, "head": head[:160], "flat": flat})
    scr = []
    for i, tx in enumerate(texts, start=1):
        flat = collapse(tx)
        mm = SCR_START.search(flat[:2500]) if i == 1 else SCR_START.search(flat)
        if mm:
            scr.append({"page": i, "snippet": flat[max(0, mm.start() - 140):mm.end()][-260:], "flat": flat, "pos": mm.start()})
    return p1, p1_cases, p1_court, starts, scr


def has_operative(texts, a, b):
    seg = collapse(" ".join(texts[a - 1:b]))
    return bool(OPERATIVE.search(seg[-1500:]))


def analyse_file(J, fitz, rec, data):
    """Returns the per-file evidence dict (no page texts are kept beyond what is needed)."""
    a = {"bytes_in_repo": data is not None}
    if data is None:
        return a
    a["rehash"] = sha(data)
    a["size"] = len(data)
    a["eof_offsets"] = [m.start() for m in re.finditer(rb"%%EOF", data)]
    a["base_revision_sha"] = sha(data[:a["eof_offsets"][0] + 5]) if a["eof_offsets"] else ""
    a["masked_sha"] = masked_hash(data)
    d, n = open_pdf(fitz, data)
    a["opens"] = d is not None
    if d is None:
        return a
    a["pages"] = n
    md = d.metadata or {}
    a["producer"] = (md.get("producer") or "").strip()
    a["creator"] = (md.get("creator") or "").strip()
    texts = page_texts(d, n)
    full = "\n".join(texts)
    a["text_sha256_recomputed"] = sha(full.encode("utf-8", "replace"))
    a["text_chars"] = sum(len(t.strip()) for t in texts)
    a["alnum_key"] = alnum_key(full)
    a["digits_key"] = digits_key(full)
    a["glyph_digits_key"] = glyph_digits_key(full)
    a["alnum_len"] = len(re.sub(r"[^a-z]", "", full.lower()))
    a["readable_ratio"] = readable_ratio(full)
    a["content_sha"] = content_hash(d, n)
    a["p1_norm"] = re.sub(r"[^a-z0-9]", "", collapse(texts[0]).lower())[:3000] if texts else ""
    a["pages_with_text"] = [i + 1 for i, t in enumerate(texts) if len(t.strip()) >= 50]
    a["printed_page_numbers"] = sorted({int(m.group(1)) for t in texts for m in PAGE_K.finditer(collapse(t)[:300])})
    a["printed_page_total"] = sorted({int(m.group(2)) for t in texts[:3] for m in PAGE_K.finditer(collapse(t)[:300])})
    a["scr_reporter"] = bool(SCR_HDR.search(collapse(" ".join(texts[:2]))[:4000]))
    a["strict_corr_pages"] = [i + 1 for i, t in enumerate(texts) if corr_marker(collapse(t)[:300])]
    p1, p1_cases, p1_court, starts, scr = segment_scan(J, texts)
    a["p1_cases"] = sorted(p1_cases)
    a["p1_court"] = p1_court
    seg = []
    bounds = [s["page"] for s in starts if "RECORD_OF_PROCEEDINGS" not in s["kinds"]]
    for s in starts:
        sc = set(cases_in(J, s["flat"][:1500]))
        cm = COURT_NAME.search(s["flat"][:600])
        sc_court = cm.group(1) if cm else ""
        if "RECORD_OF_PROCEEDINGS" in s["kinds"]:
            rel = "ANCILLARY_RECORD_OF_PROCEEDINGS"
        elif not sc:
            rel = "NO_CASE_NUMBER_ON_START_PAGE"
        elif not p1_cases:
            rel = "NO_CASE_NUMBER_ON_PAGE_1"
        elif sc & p1_cases:
            rel = "SHARED_CASE_NUMBER_WITH_PAGE_1"
        else:
            rel = "DIFFERENT_CASE_NUMBERS_FROM_PAGE_1"
        nxt = [b for b in bounds if b > s["page"]]
        end = (nxt[0] - 1) if nxt else n
        first_end = (bounds[0] - 1) if bounds else n
        sim = round(difflib.SequenceMatcher(None, letters(p1), letters(s["flat"]), autojunk=False).ratio(), 3)
        seg.append({"page": s["page"], "kinds": s["kinds"], "head": s["head"], "cases": sorted(sc), "court": sc_court, "sim_p1": sim,
                    "relation": rel, "court_differs": bool(sc_court and p1_court and sc_court.split(" AT")[0] != p1_court.split(" AT")[0]),
                    "operative_before": has_operative(texts, 1, first_end) if s["page"] == (bounds[0] if bounds else -1) else None,
                    "operative_in_segment": has_operative(texts, s["page"], end), "segment_end": end})
    a["segments"] = seg
    sc_out = []
    for k, s in enumerate(scr):
        cs = sorted(set(cases_in(J, s["snippet"])))
        sc_out.append({"page": s["page"], "snippet": s["snippet"], "cases": cs})
    a["scr_starts"] = sc_out
    a["footer"] = footer_keys(texts)
    a["pointer"] = pointer_keys(texts)
    a["head_keys"] = sorted(head_keys(J, texts))
    a["cause_title_cases"] = cause_title_cases(J, texts)
    return a


def classify_group(tq, worst, courts, dates, comp):
    """Classification of an exact same-text group from its evidence (text quality, worst byte tier, metadata, composite)."""
    if "EMPTY_OR_NEAR_EMPTY" in tq or "NO_TEXT_EXTRACTED" in tq:
        cls = "NOT_SAME_EMPTY_OR_NON_TEXT"
        why = "identical text only because the text layer is empty or near-empty; not merged"
    elif "NON_READABLE_TEXT_LAYER" in tq and worst not in CONFIRMING_TIERS:
        cls = "NOT_SAME_EMPTY_OR_NON_TEXT"
        why = "text layer is not readable and the pages do not render identically; not merged"
    elif len(courts) > 1 or len(dates) > 1:
        cls = "UNRESOLVED"
        why = "members disagree on court or decision date in metadata"
    elif comp:
        cls = "COMPOSITE_FILE"
        why = ("the shared file holds more than one document (see COMPOSITE_AND_VERSION_CANDIDATES); "
               "the copies are identical to each other, so the copies collapse, but the number of judgments inside needs review")
    elif worst in CONFIRMING_TIERS:
        cls = "CONFIRMED_DUPLICATE_SAME_JUDGMENT"
        why = "different bytes, same document content (" + worst + ")"
        if "NON_READABLE_TEXT_LAYER" in tq:
            why += "; text layer unreadable, so the match rests on bytes/renders, not on text"
    elif worst == "PAGE_RENDERS_DIFFER":
        cls = "SAME_JUDGMENT_DIFFERENT_RENDITION"
        why = "identical readable text, same court and date; page layout differs (re-generated PDF)"
    else:
        cls = "UNRESOLVED"
        why = "bytes could not be compared"
    return cls, why

# ------------------------------------------------------------------------------------------------ build
def build(repo):
    try:
        import pymupdf as fitz  # noqa: F401
    except ImportError:
        import fitz  # type: ignore  # noqa: F401
    J = load_jextract()

    # ---- inputs
    batch_files = sorted((C10 / "work" / "batches").glob("batch_*.jsonl"))
    recs = {}
    for bf in batch_files:
        lines = bf.read_text(encoding="utf-8").splitlines()
        for ln in lines[1:]:
            r = json.loads(ln)
            if r["sha256"] in recs:
                raise SystemExit(f"duplicate sha in batches: {r['sha256']}")
            recs[r["sha256"]] = r
    reg = {r["sha256"]: r for r in rcsv(C10 / "outputs" / "HF_JUDGMENT_COPY_REGISTER.csv")}
    meta = collections.defaultdict(list)
    for m in rcsv(C10 / "outputs" / "HF_JUDGMENT_METADATA_AUDIT.csv"):
        meta[m["sha256"]].append(m)
    for v in meta.values():
        v.sort(key=lambda m: m["doc_id"])
    dups = rcsv(C10 / "outputs" / "HF_JUDGMENT_DUPLICATES.csv")
    cont = rcsv(C10 / "outputs" / "CONTINUATION_MANIFEST.csv")
    if set(recs) != set(reg):
        raise SystemExit("batch files and copy register disagree on the set of files")
    shas = sorted(recs)

    input_digests = {}
    for p in batch_files + [C10 / "outputs" / n for n in ("HF_JUDGMENT_COPY_REGISTER.csv", "HF_JUDGMENT_METADATA_AUDIT.csv",
                                                          "HF_JUDGMENT_DUPLICATES.csv", "CONTINUATION_MANIFEST.csv")] + \
            [C10 / "review" / "REVIEW_FINDINGS.md", C10 / "tools" / "jextract.py"]:
        input_digests[str(p.relative_to(C10.parent))] = sha(p.read_bytes())

    # ---- per-file analysis (bytes from the pinned commit, always re-hashed)
    blobs = Blobs(repo)
    A = {}
    for s in shas:
        data = blobs.get(reg[s]["path"])
        A[s] = analyse_file(J, fitz, recs[s], data)
        if data is not None and A[s]["rehash"] != s:
            A[s]["rehash_mismatch"] = True
    text_mismatch = sorted(s for s in shas if A[s].get("text_sha256_recomputed") and recs[s].get("text_sha256")
                           and A[s]["text_sha256_recomputed"] != recs[s]["text_sha256"])

    def court_of(s):
        ms = meta.get(s)
        if ms:
            return ms[0]["court"]
        p = reg[s]["path"]
        return "Supreme Court of India" if "/sci/" in p or "third_party" in p else ""

    def date_of(s):
        return ";".join(sorted({m["issue_date_meta"] for m in meta.get(s, []) if m["issue_date_meta"]}))

    def url_date(s):
        for m in meta.get(s, []):
            mm = re.search(r"_(\d{4}-\d{2}-\d{2})\.pdf$", m.get("source_url") or "")
            if mm:
                return mm.group(1)
        return ""

    def date_set(s, printed=False):
        out = {m["issue_date_meta"] for m in meta.get(s, []) if m["issue_date_meta"]}
        if url_date(s):
            out.add(url_date(s))
        if printed:
            out.update(recs[s].get("decision_date_candidates") or [])
            out.update(recs[s].get("dates_text") or [])
        return out

    page_cache = {}

    def get_pages(s):
        """Page texts and thumbnails (lazily) of one file, re-read from the pinned blob and re-hashed."""
        if s not in page_cache:
            data = blobs.get(reg[s]["path"])
            if data is None or sha(data) != s:
                page_cache[s] = None
            else:
                d, n = open_pdf(fitz, data)
                page_cache[s] = None if d is None else {"doc": d, "texts": page_texts(d, n), "thumbs": None, "sh": None}
        return page_cache[s]

    def sh_of(s):
        g = get_pages(s)
        if g["sh"] is None:
            g["sh"] = [shingles(t) for t in g["texts"]]
        return g["sh"]

    def th_of(s):
        g = get_pages(s)
        if g["thumbs"] is None:
            g["thumbs"] = [thumb(fitz, g["doc"][i]) for i in range(len(g["texts"]))]
        return g["thumbs"]

    meta_issues = []

    def meta_cases(s):
        return [m["case_numbers_meta"] for m in meta.get(s, []) if m["case_numbers_meta"]]

    def text_quality(s):
        r, a = recs[s], A[s]
        ts = r.get("text_sha256")
        chars = r.get("text_chars_total") or 0
        if not ts:
            return "NO_TEXT_EXTRACTED"
        if ts == EMPTY_SHA or chars < 200:
            return "EMPTY_OR_NEAR_EMPTY"
        rr = a.get("readable_ratio")
        if rr is not None and rr < 0.4:
            return "NON_READABLE_TEXT_LAYER"
        return "READABLE"

    # ---- union-find over evidence edges between files
    parent = {s: s for s in shas}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[max(rx, ry)] = min(rx, ry)

    # ---- review-confirmed composite / versions (matched on stored metadata)
    review_composite = sorted(s for s in shas for m in meta.get(s, [])
                              if REVIEW_COMPOSITE["title_substring"] in m["title"].upper() and m["court"] == REVIEW_COMPOSITE["court"])
    review_versions = sorted(s for s in shas if reg[s]["path"] == REVIEW_VERSIONS_PATH)
    review_composite = sorted(set(review_composite) | {s for s in REVIEW_EXTRA_JUDGMENTS if s in recs})

    def strong_composite(s):
        a = A[s]
        if s in review_composite:
            return True
        segs = [g for g in a.get("segments", []) if g["relation"] == "DIFFERENT_CASE_NUMBERS_FROM_PAGE_1" or g["court_differs"]]
        if any(g["court_differs"] or ("COURT_HEADER" in g["kinds"] and g["operative_in_segment"] and g["operative_before"] is not False)
               for g in segs):
            return True
        if multi_document(s):
            return True
        return len(scr_composite(s)) > 0

    def multi_document(s):
        """Three or more pages that open with a court header: a file compiling several orders (e.g. a consigned case record)."""
        if reg[s]["source_completeness"] == "STORED_COPY_TRUNCATED_CONTENT_MAY_BE_MISSING":
            return []
        return [g for g in A[s].get("segments", []) if "COURT_HEADER" in g["kinds"]] if \
            len([g for g in A[s].get("segments", []) if "COURT_HEADER" in g["kinds"]]) >= 3 else []

    def scr_composite(s):
        st = A[s].get("scr_starts", [])
        if len(st) < 2:
            return []
        base = set(st[0]["cases"])
        return [x for x in st[1:] if not (set(x["cases"]) & base) and x["cases"]]

    # ---- exact same-text groups
    by_text = collections.defaultdict(list)
    for s in shas:
        ts = recs[s].get("text_sha256")
        if ts:
            by_text[ts].append(s)
    groups = sorted(([v for v in by_text.values() if len(v) > 1]), key=lambda v: (-len(v), recs[v[0]]["text_sha256"]))
    n_group_files = sum(len(v) for v in groups)

    blob2 = blobs  # reuse for render checks
    group_rows, group_of = [], {}
    for v in groups:
        ts = recs[v[0]]["text_sha256"]
        gid = "STG-" + ts[:12]
        rep = v[0]
        tq = sorted({text_quality(s) for s in v})
        tiers = {}
        renders = {}
        for s in v:
            group_of[s] = gid
            if s == rep:
                continue
            a, b = A[rep], A[s]
            if not (a.get("bytes_in_repo") and b.get("bytes_in_repo") and a.get("opens") and b.get("opens")):
                tiers[s] = "BYTES_NOT_COMPARABLE"
            elif a["masked_sha"] == b["masked_sha"]:
                tiers[s] = TIER_ORDER[0]
            elif a["base_revision_sha"] and a["base_revision_sha"] == b["base_revision_sha"]:
                tiers[s] = TIER_ORDER[1]
            elif a["content_sha"] == b["content_sha"]:
                tiers[s] = TIER_ORDER[2]
            else:
                if rep not in renders:
                    renders[rep] = render_hash(fitz, blob2.get(reg[rep]["path"]))
                renders[s] = render_hash(fitz, blob2.get(reg[s]["path"]))
                tiers[s] = TIER_ORDER[3] if renders[s] and renders[s] == renders[rep] else TIER_ORDER[4]
        worst = max(tiers.values(), key=TIER_ORDER.index) if tiers else TIER_ORDER[0]
        tier_counts = collections.Counter(tiers.values())
        courts = sorted({court_of(s) for s in v})
        dates = sorted({date_of(s) for s in v})
        pages = sorted({str(recs[s].get("pages")) for s in v})
        producers = sorted({A[s].get("producer", "") for s in v})
        mc = [c for s in v for c in meta_cases(s)]
        flat_text_cases = set()
        for s in v:
            flat_text_cases.update(recs[s].get("case_numbers_text_p1_3") or [])
        found = 0
        for c in mc:
            k = J.norm_case_string(c)
            num = re.search(r"/(\d{1,6})/((?:19|20)\d{2})", c)
            if (k and k in flat_text_cases) or (num and any(x.endswith(f"-{num.group(1)}-{num.group(2)}") for x in flat_text_cases)):
                found += 1
        eofs = sorted({len(A[s].get("eof_offsets", [])) for s in v})
        comp = sorted(s for s in v if strong_composite(s))
        incomplete = sorted(s for s in v if reg[s]["source_completeness"] != "COMPLETE_FILE_STRUCTURE")
        cls, why = classify_group(tq, worst, courts, dates, comp)
        merges = cls in ("CONFIRMED_DUPLICATE_SAME_JUDGMENT", "SAME_JUDGMENT_DIFFERENT_RENDITION", "COMPOSITE_FILE")
        if merges:
            for s in v[1:]:
                union(v[0], s)
        nat = []
        if tier_counts.get(TIER_ORDER[0]):
            nat.append("only generation metadata differs (creation/modification timestamps, XMP document/instance IDs, trailer /ID, xref offsets)")
        if tier_counts.get(TIER_ORDER[1]):
            nat.append("identical base revision up to the first %%EOF; the appended incremental update (digital-signature field) differs or is cut")
        if tier_counts.get(TIER_ORDER[2]):
            nat.append("page content streams and images identical; PDF container re-generated (producer/object layout differs)")
        if tier_counts.get(TIER_ORDER[3]):
            nat.append("page images render identically at 40 dpi; internal objects differ")
        if tier_counts.get(TIER_ORDER[4]):
            nat.append("page renders differ (glyph positioning/layout); extracted text identical")
        group_rows.append({
            "group_id": gid, "scope": "EXACT_TEXT_SHA256", "n_files": len(v), "representative_sha256": rep,
            "file_sha256s": ";".join(v), "text_sha256": ts, "text_chars": recs[rep].get("text_chars_total"),
            "text_quality": ";".join(tq), "readable_ratio": A[rep].get("readable_ratio", ""), "pages": ";".join(pages),
            "courts": ";".join(courts), "issue_dates_meta": ";".join(dates), "meta_records": sum(len(meta.get(s, [])) for s in v),
            "meta_case_numbers": ";".join(mc), "meta_case_numbers_found_in_text_p1_3": f"{found}/{len(mc)}",
            "first_page_excerpt": collapse(recs[rep].get("first_page_excerpt", ""))[:180], "producers": ";".join(producers),
            "eof_markers_per_file": ";".join(str(e) for e in eofs),
            "byte_comparison": ";".join(f"{k}={tier_counts[k]}" for k in TIER_ORDER if tier_counts.get(k)),
            "byte_diff_nature": " | ".join(nat), "incomplete_members": ";".join(incomplete),
            "composite_members": ";".join(comp), "classification": cls, "classification_basis": why,
            "judgment_count_change": -(len(v) - 1) if merges else 0, "verification": VERIFY})

    # ---- extension: identical text after removing punctuation/whitespace (different exact text hashes)
    by_alnum = collections.defaultdict(list)
    for s in shas:
        a = A[s]
        if a.get("alnum_key") and text_quality(s) == "READABLE" and a.get("alnum_len", 0) >= 500 and \
                reg[s]["source_completeness"] == "COMPLETE_FILE_STRUCTURE":
            by_alnum[a["alnum_key"] + a["glyph_digits_key"]].append(s)
    for key in sorted(by_alnum, key=lambda k: (-len(by_alnum[k]), k)):
        v = sorted(by_alnum[key])
        roots = sorted({find(s) for s in v})
        exact = sorted({recs[s]["text_sha256"] for s in v})
        if len(exact) < 2:
            continue
        courts = sorted({court_of(s) for s in v})
        dates = sorted({date_of(s) for s in v})
        udates = sorted({url_date(s) for s in v})
        pages = sorted({str(recs[s].get("pages")) for s in v})
        date_ok = len(dates) == 1 or (len(udates) == 1 and udates[0])
        ok = len(courts) == 1 and bool(date_ok) and len(pages) == 1
        if ok and len(dates) > 1:
            meta_issues.append({"files": ";".join(v), "issue": "issue_date_meta differs between copies of one document; every source_url "
                                f"carries the date {udates[0]}: metadata dates {';'.join(dates)} are not the date of the stored document"})
        before = len(roots)
        if ok:
            for s in v[1:]:
                union(v[0], s)
        gid = "STGX-" + key[:12]
        for s in v:
            group_of.setdefault(s, gid)
        group_rows.append({
            "group_id": gid, "scope": "NORMALIZED_TEXT_EXTENSION", "n_files": len(v), "representative_sha256": v[0],
            "file_sha256s": ";".join(v), "text_sha256": ";".join(exact), "text_chars": recs[v[0]].get("text_chars_total"),
            "text_quality": "READABLE", "readable_ratio": A[v[0]].get("readable_ratio", ""), "pages": ";".join(pages),
            "courts": ";".join(courts), "issue_dates_meta": ";".join(dates), "meta_records": sum(len(meta.get(s, [])) for s in v),
            "meta_case_numbers": ";".join(c for s in v for c in meta_cases(s)), "meta_case_numbers_found_in_text_p1_3": "",
            "first_page_excerpt": collapse(recs[v[0]].get("first_page_excerpt", ""))[:180],
            "producers": ";".join(sorted({A[s].get("producer", "") for s in v})), "eof_markers_per_file": "",
            "byte_comparison": f"exact_text_variants={len(exact)}",
            "byte_diff_nature": "letters identical and multi-digit numbers identical in order once clock times are removed and quote/dash glyphs are "
                                "mapped to the digits a faulty generator emits for them (' as 9, left/right double quote as < and =, left quote as 8, "
                                "dashes as 3/4); the exact text differs only in per-download signing/print time stamps or that glyph mapping",
            "incomplete_members": "", "composite_members": "",
            "classification": "SAME_JUDGMENT_DIFFERENT_RENDITION" if ok else "UNRESOLVED",
            "classification_basis": (("same court, decision date and page count; same words and same numbers (case numbers, dates) apart from "
                                      "time stamps and quote/dash glyphs extracted as digits" +
                                      (f"; crawler dates differ but every source_url carries {udates[0]} (metadata error, routed)" if len(dates) > 1 else ""))
                                     if ok else "letter sequence identical but court, date or page count differ"),
            "judgment_count_change": -(before - 1) if ok else 0, "verification": VERIFY})

    # ---- same words but different numbers: reported, never merged (template orders in different cases, or glyph noise)
    by_letters = collections.defaultdict(list)
    for s in shas:
        a = A[s]
        if a.get("alnum_key") and text_quality(s) == "READABLE" and a.get("alnum_len", 0) >= 500 and \
                reg[s]["source_completeness"] == "COMPLETE_FILE_STRUCTURE":
            by_letters[a["alnum_key"]].append(s)
    for key in sorted(by_letters, key=lambda k: (-len(by_letters[k]), k)):
        v = sorted(by_letters[key])
        roots = sorted({find(s) for s in v})
        if len(roots) < 2 or len({A[s]["glyph_digits_key"] for s in v}) < 2:
            continue
        gid = "STGN-" + key[:12]
        for s in v:
            group_of.setdefault(s, gid)
        group_rows.append({
            "group_id": gid, "scope": "SAME_WORDS_NUMBERS_DIFFER_NOT_MERGED", "n_files": len(v), "representative_sha256": v[0],
            "file_sha256s": ";".join(v), "text_sha256": ";".join(sorted({recs[s]["text_sha256"] for s in v})),
            "text_chars": recs[v[0]].get("text_chars_total"), "text_quality": "READABLE", "readable_ratio": A[v[0]].get("readable_ratio", ""),
            "pages": ";".join(sorted({str(recs[s].get("pages")) for s in v})), "courts": ";".join(sorted({court_of(s) for s in v})),
            "issue_dates_meta": ";".join(sorted({date_of(s) for s in v})), "meta_records": sum(len(meta.get(s, [])) for s in v),
            "meta_case_numbers": ";".join(c for s in v for c in meta_cases(s)), "meta_case_numbers_found_in_text_p1_3": "",
            "first_page_excerpt": collapse(recs[v[0]].get("first_page_excerpt", ""))[:180],
            "producers": ";".join(sorted({A[s].get("producer", "") for s in v})), "eof_markers_per_file": "",
            "byte_comparison": f"judgment_entities_after_merges={len(roots)}",
            "byte_diff_nature": "letter sequence identical but the multi-digit number sequence differs: either the same wording issued in "
                                "different cases (separate orders) or digit-like glyph noise; needs a reader",
            "incomplete_members": "", "composite_members": "", "classification": "UNRESOLVED",
            "classification_basis": "not merged: numbers (case numbers, dates, item numbers) differ", "judgment_count_change": 0,
            "verification": VERIFY})

    # ---- incomplete copies whose readable first page matches another file of the same court and date
    inc_rows = []
    by_cd = collections.defaultdict(list)
    for s in shas:
        by_cd[(court_of(s), date_of(s))].append(s)
    for s in shas:
        if reg[s]["source_completeness"] == "COMPLETE_FILE_STRUCTURE" or not A[s].get("p1_norm") or len(A[s]["p1_norm"]) < 300:
            continue
        for o in by_cd[(court_of(s), date_of(s))]:
            if o == s or not A[o].get("p1_norm") or len(A[o]["p1_norm"]) < 300:
                continue
            ratio = difflib.SequenceMatcher(None, A[s]["p1_norm"], A[o]["p1_norm"], autojunk=False).ratio()
            ps, po = recs[s].get("pages"), recs[o].get("pages")
            if ratio >= 0.95 and (ps is None or po is None or ps == po):
                # first-page similarity alone is unsafe (word-identical orders in different cases reach 0.96-0.99): every page
                # readable in both copies must match too
                gs_, go_ = get_pages(s), get_pages(o)
                if not gs_ or not go_:
                    continue
                both = [i for i in range(min(len(gs_["texts"]), len(go_["texts"])))
                        if len(gs_["texts"][i].strip()) >= 50 and len(go_["texts"][i].strip()) >= 50]
                sims = []
                for i in both:
                    la, lb = letters(gs_["texts"][i], 4000), letters(go_["texts"][i], 4000)
                    if i == both[-1]:   # the last readable page of a truncated copy may stop mid-page: compare the common prefix
                        n_ = min(len(la), len(lb))
                        la, lb = la[:n_], lb[:n_]
                    sims.append(difflib.SequenceMatcher(None, la, lb, autojunk=False).ratio())
                same_p1_cases = bool(A[s].get("p1_cases")) and A[s].get("p1_cases") == A[o].get("p1_cases")
                if sims and all(x >= 0.95 for x in sims) and (len(both) >= 2 or same_p1_cases):
                    x, y = sorted((s, o))
                    inc_rows.append((x, y, round(ratio, 3), len(both), round(min(sims), 3)))
    inc_rows = sorted(set(inc_rows))
    inc_links = collections.defaultdict(list)
    seen_pairs = set()
    for s, o, ratio, _nb, _ms in inc_rows:
        pair = tuple(sorted((s, o)))
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        inc_links[s].append((o, ratio))
        inc_links[o].append((s, ratio))
    # one group row per connected set of such links
    comp_inc = collections.defaultdict(set)
    tmp_parent = {}

    def tfind(x):
        while tmp_parent.get(x, x) != x:
            x = tmp_parent[x]
        return x
    for a_, b_ in sorted(seen_pairs):
        ra, rb = tfind(a_), tfind(b_)
        if ra != rb:
            tmp_parent[max(ra, rb)] = min(ra, rb)
    for a_, b_ in seen_pairs:
        comp_inc[tfind(a_)].update((a_, b_))
    for root in sorted(comp_inc):
        v = sorted(comp_inc[root])
        before = len({find(s) for s in v})
        for s in v[1:]:
            union(v[0], s)
        gid = "STGI-" + v[0][:12]
        for s in v:
            group_of.setdefault(s, gid)
        group_rows.append({
            "group_id": gid, "scope": "INCOMPLETE_COPY_ALL_PAGE_MATCH", "n_files": len(v), "representative_sha256": v[0],
            "file_sha256s": ";".join(v), "text_sha256": ";".join(sorted({recs[s].get("text_sha256") or "" for s in v})),
            "text_chars": "", "text_quality": ";".join(sorted({text_quality(s) for s in v})), "readable_ratio": "",
            "pages": ";".join(sorted({str(recs[s].get("pages")) for s in v})), "courts": ";".join(sorted({court_of(s) for s in v})),
            "issue_dates_meta": ";".join(sorted({date_of(s) for s in v})), "meta_records": sum(len(meta.get(s, [])) for s in v),
            "meta_case_numbers": ";".join(c for s in v for c in meta_cases(s)), "meta_case_numbers_found_in_text_p1_3": "",
            "first_page_excerpt": collapse(recs[v[0]].get("first_page_excerpt", ""))[:180],
            "producers": ";".join(sorted({A[s].get("producer", "") for s in v})), "eof_markers_per_file": "",
            "byte_comparison": "all readable pages match: " + ";".join(f"{x[:12]}~{y[:12]} p1={r}, {nb} common text pages, min page similarity {ms}"
                                                                 for x, y, r, nb, ms in inc_rows if x in v),
            "byte_diff_nature": "at least one member is a truncated or tail-cut copy, so whole-text hashes cannot match; the readable first "
                                "page and every page readable in both copies match (letter similarity >= 0.95) with the same court, decision "
                                "date and page count",
            "incomplete_members": ";".join(s for s in v if reg[s]["source_completeness"] != "COMPLETE_FILE_STRUCTURE"),
            "composite_members": "", "classification": "CONFIRMED_DUPLICATE_SAME_JUDGMENT",
            "classification_basis": "same judgment by all-page identity, court, date and page count; the copies differ in completeness",
            "judgment_count_change": -(before - 1), "verification": VERIFY})

    # ---- scanned copies of a common judgment: a lead case seen in running footers, pointer lines ('For orders, see ...') or
    #      the opening cause title, the same court and decision date, and a page-content match (text shingles or page images)
    lead_index = collections.defaultdict(set)
    file_keys = {}
    for s in shas:
        a = A[s]
        if not a.get("opens"):
            continue
        ks = collections.defaultdict(set)
        for (_pg, _k, _n, num, yr) in a.get("footer", []):
            ks[(num, yr)].add("FOOTER")
        for ny in a.get("pointer", []):
            ks[tuple(ny)].add("POINTER")
        for ny in a.get("head_keys", []):
            ks[tuple(ny)].add("CAUSE_TITLE")
        file_keys[s] = ks
        for ny in ks:
            lead_index[(court_of(s),) + tuple(ny)].add(s)

    def confirm(x, y, key):
        """Page-content confirmation. When either file shows the lead case only in a running footer (not in its own cause title
        or a pointer line) the text match must be strong (>= 0.8 both ways): word-identical orders in different cases on the same
        day share most of their pages, and a clerk can copy the wrong case number into a footer."""
        shx, shy = sh_of(x), sh_of(y)
        tx, ty = text_page_match(shx, shy), text_page_match(shy, shx)
        titled = all(file_keys[f][key] & {"POINTER", "CAUSE_TITLE"} or key in {
            tuple(int(z) for z in re.match(r".*-(\d+)-(\d{4})$", c).groups()) for c in A[f].get("cause_title_cases", [])
            if re.match(r".*-(\d+)-(\d{4})$", c)} for f in (x, y))
        need = 0.6 if titled else 0.8
        if tx[1] >= 2 and ty[1] >= 2 and tx[0] >= need and ty[0] >= need:
            return "TEXT_PAGES", f"text pages matched {tx[0]} of {tx[1]} / {ty[0]} of {ty[1]}" + ("" if titled else " (footer-only lead: >=0.8 required)")
        if not titled:
            return "", f"text {tx[0]} of {tx[1]} / {ty[0]} of {ty[1]}; lead case only in a footer, images not accepted"
        im = image_match(th_of(x), th_of(y))
        shorter = min(len(get_pages(x)["texts"]), len(get_pages(y)["texts"]))
        if im[0] >= 0.6 and im[1] >= 3 and im[1] >= 0.6 * shorter:
            return "PAGE_IMAGES", f"page thumbnails mean correlation {im[0]} over {im[1]} pages (offset {im[2]}); text {tx[0]}/{ty[0]}"
        return "", f"text {tx[0]} of {tx[1]} / {ty[0]} of {ty[1]}; images {im[0]} over {im[1]} pages"

    scan_rows, contained, extra_orders = [], [], []
    for key in sorted(lead_index):
        files = sorted(lead_index[key])
        if len(files) < 2 or len({find(f) for f in files}) < 2:
            continue
        if not any(file_keys[f][key[1:]] & {"FOOTER", "POINTER"} for f in files):
            continue   # a shared opening case number alone is no lead-case evidence
        if any(not get_pages(f) for f in files):
            files = [f for f in files if get_pages(f)]
        before = len({find(f) for f in files})
        links = []
        for i, x in enumerate(files):
            for y in files[i + 1:]:
                if find(x) == find(y):
                    continue
                same_date = bool(date_set(x) & date_set(y))
                method, ev = confirm(x, y, key[1:])
                if method and same_date:
                    union(x, y)
                    links.append((x, y, method, ev))
                elif method and not same_date:
                    contained.append((x, y, method, ev, key))
        if not links:
            continue
        merged = sorted({f for x, y, _m, _e in links for f in (x, y)})
        after = len({find(f) for f in files})
        gid = "STGS-" + merged[0][:12]
        for f in merged:
            group_of.setdefault(f, gid)
        # pages of a merged copy that match no page of its partner and carry their own operative order
        for x, y, _m, _e in links:
            for a_, b_ in ((x, y), (y, x)):
                ta, shb = get_pages(a_)["texts"], sh_of(b_)
                fts = [(pg - k, n) for (pg, k, n, num, yr) in A[a_].get("footer", []) if (num, yr) == key[1:]]
                if not fts:
                    continue
                off, ntot = collections.Counter(fts).most_common(1)[0][0]
                odd = [i + 1 for i, t in enumerate(ta) if i + 1 > off + ntot and len(t.strip()) >= 500
                       and max((len(shingles(t) & q) / max(1, len(shingles(t))) for q in shb if q), default=0) < 0.3]
                if odd and OPERATIVE.search(collapse(" ".join(ta[odd[0] - 1:]))[-1500:]):
                    extra_orders.append((a_, odd))
        scan_rows.append({
            "group_id": gid, "scope": "SCANNED_COPY_LEAD_CASE_MATCH", "n_files": len(merged), "representative_sha256": merged[0],
            "file_sha256s": ";".join(merged), "text_sha256": "", "text_chars": "",
            "text_quality": ";".join(sorted({text_quality(f) for f in merged})), "readable_ratio": "",
            "pages": ";".join(sorted({str(recs[f].get("pages")) for f in merged})), "courts": key[0],
            "issue_dates_meta": ";".join(sorted({date_of(f) for f in merged})), "meta_records": sum(len(meta.get(f, [])) for f in merged),
            "meta_case_numbers": ";".join(c for f in merged for c in meta_cases(f)), "meta_case_numbers_found_in_text_p1_3": "",
            "first_page_excerpt": collapse(recs[merged[0]].get("first_page_excerpt", ""))[:180],
            "producers": ";".join(sorted({A[f].get("producer", "") for f in merged})), "eof_markers_per_file": "",
            "byte_comparison": " | ".join(f"{x[:12]}~{y[:12]}: {m} ({e})" for x, y, m, e in links)[:3000],
            "byte_diff_nature": (f"lead case {key[1]}/{key[2]} found as " +
                                 ", ".join(f"{k}={sum(1 for f in merged if k in file_keys[f][key[1:]])}" for k in ("FOOTER", "POINTER", "CAUSE_TITLE")) +
                                 "; scanned copies (OCR text layers differ), usually a one-page sheet for the file's own case followed by the "
                                 "common judgment"),
            "incomplete_members": "", "composite_members": "", "classification": "CONFIRMED_DUPLICATE_SAME_JUDGMENT",
            "classification_basis": "same court, same lead case (footer/pointer/cause title) and same decision date, confirmed on page content "
                                    "(text shingles or page images); similarity alone never merges",
            "judgment_count_change": -(before - after), "verification": VERIFY})
    group_rows.extend(scan_rows)
    contained_rows = []
    for x, y, m, ev, key in sorted(set(contained)):
        if find(x) == find(y):
            continue
        contained_rows.append({"files": f"{x};{y}", "key": f"{key[0]} {key[1]}/{key[2]}", "method": m, "evidence": ev,
                               "dates": f"{';'.join(sorted(date_set(x)))} | {';'.join(sorted(date_set(y)))}"})

    # ---- one-page pointer orders ('For orders, see <lead case>'): the decision is the lead judgment; linked to it, not counted
    pointer_rows = []
    for s in shas:
        a = A[s]
        if not a.get("opens") or (a.get("pages") or 0) > 2 or (a.get("text_chars") or 0) >= 3000 or not a.get("pointer"):
            continue
        leads = []
        for ny in a["pointer"]:
            for o in sorted(lead_index.get((court_of(s),) + tuple(ny), set())):
                if o == s or (A[o].get("pages") or 0) <= 2:
                    continue
                mc = any(re.search(rf"/{ny[0]}/{ny[1]}$", c) for c in meta_cases(o)) or "FOOTER" in file_keys[o].get(tuple(ny), set())
                if mc and date_set(s, printed=True) & date_set(o):
                    leads.append(o)
        if not leads:
            pointer_rows.append({"sha256": s, "lead": "", "status": "LEAD_NOT_IN_CORPUS_OR_DATE_UNCONFIRMED", "pointer": a["pointer"]})
            continue
        lead = sorted(leads, key=lambda o: (-(A[o].get("pages") or 0), o))[0]
        before = len({find(s), find(lead)})
        union(s, lead)
        pointer_rows.append({"sha256": s, "lead": lead, "status": "LINKED_TO_LEAD_JUDGMENT", "pointer": a["pointer"], "change": -(before - 1)})
    for pr in [r for r in pointer_rows if r["status"] == "LINKED_TO_LEAD_JUDGMENT"]:
        s, lead = pr["sha256"], pr["lead"]
        group_of.setdefault(s, "STGP-" + lead[:12])
        group_rows.append({
            "group_id": "STGP-" + s[:12], "scope": "POINTER_ORDER_TO_LEAD_JUDGMENT", "n_files": 2, "representative_sha256": lead,
            "file_sha256s": f"{s};{lead}", "text_sha256": "", "text_chars": A[s].get("text_chars"), "text_quality": text_quality(s),
            "readable_ratio": "", "pages": f"{A[s].get('pages')};{A[lead].get('pages')}", "courts": court_of(s),
            "issue_dates_meta": f"{date_of(s)};{date_of(lead)}", "meta_records": len(meta.get(s, [])) + len(meta.get(lead, [])),
            "meta_case_numbers": ";".join(meta_cases(s) + meta_cases(lead)), "meta_case_numbers_found_in_text_p1_3": "",
            "first_page_excerpt": collapse(recs[s].get("first_page_excerpt", ""))[:180], "producers": "", "eof_markers_per_file": "",
            "byte_comparison": "pointer to " + ";".join(f"{n}/{y}" for n, y in pr["pointer"]),
            "byte_diff_nature": "one-page order for its own case that says 'For orders, see' the lead case; the lead judgment (same court, its "
                                "case number, same printed or recorded date) is in the corpus",
            "incomplete_members": "", "composite_members": "", "classification": "POINTER_ORDER_NOT_A_SEPARATE_JUDGMENT",
            "classification_basis": "the decision is the lead judgment; the pointer order is kept as a copy for its own proceeding",
            "judgment_count_change": pr["change"], "verification": VERIFY})

    # ---- composite and version candidates
    cand_rows = []
    for s in shas:
        a = A[s]
        if not a.get("opens"):
            continue
        truncated = reg[s]["source_completeness"] == "STORED_COPY_TRUNCATED_CONTENT_MAY_BE_MISSING"
        for g in a.get("segments", []):
            if g["relation"] == "ANCILLARY_RECORD_OF_PROCEEDINGS":
                kind, strength = "ANCILLARY_RECORD_OF_PROCEEDINGS", "INFO"
            elif truncated:
                kind, strength = "NOT_ASSESSED_TRUNCATED_FILE_PAGE_ORDER_UNRELIABLE", "INFO"
            elif g["court_differs"]:
                kind, strength = "COMPOSITE_CANDIDATE", "STRONG"
            elif g["relation"] == "DIFFERENT_CASE_NUMBERS_FROM_PAGE_1":
                strong = "COURT_HEADER" in g["kinds"] and g["operative_in_segment"] and g["operative_before"] is not False
                kind, strength = "COMPOSITE_CANDIDATE", "STRONG" if strong else "WEAK"
            elif g["relation"] == "SHARED_CASE_NUMBER_WITH_PAGE_1" and g["sim_p1"] >= 0.95:
                kind, strength = "REPEATED_COPY_INSIDE_FILE (start page matches page 1)", "STRONG"
            elif g["relation"] == "SHARED_CASE_NUMBER_WITH_PAGE_1":
                kind = "SEPARATE_OPINION_OR_VERSION_CANDIDATE (same case, different text)"
                strength = "STRONG" if a.get("strict_corr_pages") else "WEAK"
            else:
                kind, strength = "DOCUMENT_BOUNDARY_UNCLEAR", "WEAK"
            cand_rows.append({"sha256": s, "court": court_of(s), "title_meta": (meta.get(s) or [{}])[0].get("title", "")[:120],
                              "pages": a.get("pages"), "candidate_kind": kind, "strength": strength, "detector": "PAGE_HEADER_RESTART",
                              "evidence_page": g["page"], "evidence_signals": ";".join(g["kinds"]) + f";similarity_to_p1={g['sim_p1']}", "segment_end_page": g["segment_end"],
                              "page_1_case_numbers": ";".join(a["p1_cases"]), "segment_case_numbers": ";".join(g["cases"]),
                              "operative_phrase_before": "" if g["operative_before"] is None else g["operative_before"],
                              "operative_phrase_in_segment": g["operative_in_segment"],
                              "evidence_text": g["head"], "review_finding": "", "counted_in_revised_total": False, "verification": VERIFY})
        md = multi_document(s)
        if md:
            cand_rows.append({"sha256": s, "court": court_of(s), "title_meta": (meta.get(s) or [{}])[0].get("title", "")[:120],
                              "pages": a.get("pages"), "candidate_kind": "MULTI_DOCUMENT_FILE_CANDIDATE", "strength": "STRONG",
                              "detector": "PAGE_HEADER_RESTART (3+ court headers at page top)", "evidence_page": md[0]["page"],
                              "evidence_signals": "court-header pages " + ",".join(str(g["page"]) for g in md), "segment_end_page": "",
                              "page_1_case_numbers": ";".join(a["p1_cases"]),
                              "segment_case_numbers": ";".join(sorted({c for g in md for c in g["cases"]})),
                              "operative_phrase_before": "", "operative_phrase_in_segment": "",
                              "evidence_text": md[0]["head"], "review_finding": "", "counted_in_revised_total": False, "verification": VERIFY})
        st = a.get("scr_starts", [])
        if len(st) >= 2:
            base = set(st[0]["cases"])
            for x in st[1:]:
                diff = bool(x["cases"]) and not (set(x["cases"]) & base)
                cand_rows.append({"sha256": s, "court": court_of(s), "title_meta": (meta.get(s) or [{}])[0].get("title", "")[:120],
                                  "pages": a.get("pages"), "candidate_kind": "COMPOSITE_CANDIDATE" if diff else "DOCUMENT_BOUNDARY_UNCLEAR",
                                  "strength": "STRONG" if diff else "WEAK", "detector": "SCR_REPORT_START (date + bench line)",
                                  "evidence_page": x["page"], "evidence_signals": f"report starts on pages {','.join(str(y['page']) for y in st)}",
                                  "segment_end_page": "", "page_1_case_numbers": ";".join(st[0]["cases"]), "segment_case_numbers": ";".join(x["cases"]),
                                  "operative_phrase_before": "", "operative_phrase_in_segment": "",
                                  "evidence_text": x["snippet"][-200:], "review_finding": "", "counted_in_revised_total": False,
                                  "verification": VERIFY})
        if a.get("strict_corr_pages"):
            pg = a["strict_corr_pages"]
            cand_rows.append({"sha256": s, "court": court_of(s), "title_meta": (meta.get(s) or [{}])[0].get("title", "")[:120],
                              "pages": a.get("pages"), "candidate_kind": "CORRECTED_VERSION_MARKER",
                              "strength": "STRONG" if pg[0] <= 2 else "WEAK", "detector": "STRICT_CORRECTION_MARKER (page top 300 chars)",
                              "evidence_page": pg[0], "evidence_signals": "marker pages " + ranges(pg), "segment_end_page": "",
                              "page_1_case_numbers": ";".join(a.get("p1_cases", [])), "segment_case_numbers": "",
                              "operative_phrase_before": "", "operative_phrase_in_segment": "", "evidence_text": "",
                              "review_finding": "", "counted_in_revised_total": False, "verification": VERIFY})
    # review findings (independent C10 reading) are recorded explicitly
    for s in review_composite:
        x = REVIEW_EXTRA_JUDGMENTS.get(s, {})
        cand_rows.append({"sha256": s, "court": court_of(s), "title_meta": meta[s][0]["title"][:120], "pages": A[s].get("pages"),
                          "candidate_kind": "COMPOSITE_CONFIRMED_BY_REVIEW", "strength": "REVIEWED", "detector": x.get("source", ""),
                          "evidence_page": int(x["pages"].split("-")[0]) if x else "", "evidence_signals": "second judgment on pp." + x.get("pages", ""),
                          "segment_end_page": int(x["pages"].split("-")[-1]) if x else "", "page_1_case_numbers": ";".join(A[s].get("p1_cases", [])),
                          "segment_case_numbers": x.get("proceeding", ""), "operative_phrase_before": "", "operative_phrase_in_segment": "",
                          "evidence_text": x.get("title", ""), "review_finding": x.get("source", ""), "counted_in_revised_total": True,
                          "verification": VERIFY})
    for s, note in sorted(REVIEW_SPLIT.items()):
        if s in recs:
            cand_rows.append({"sha256": s, "court": court_of(s), "title_meta": meta[s][0]["title"][:120], "pages": A[s].get("pages"),
                              "candidate_kind": "TWO_OPINIONS_SPLIT_VERDICT_CONFIRMED_BY_REVIEW", "strength": "REVIEWED",
                              "detector": "C11 identity reading + C11 review (F9)", "evidence_page": 194, "evidence_signals": note,
                              "segment_end_page": A[s].get("pages"), "page_1_case_numbers": ";".join(A[s].get("p1_cases", [])),
                              "segment_case_numbers": "", "operative_phrase_before": "", "operative_phrase_in_segment": "",
                              "evidence_text": "one judgment in two opinions, each with its own 'Page 1 of N'", "review_finding": "F9",
                              "counted_in_revised_total": False, "verification": VERIFY})
    for a_, odd in sorted(set((a_, tuple(o)) for a_, o in extra_orders)):
        cand_rows.append({"sha256": a_, "court": court_of(a_), "title_meta": (meta.get(a_) or [{}])[0].get("title", "")[:120],
                          "pages": A[a_].get("pages"), "candidate_kind": "ADDITIONAL_ORDER_IN_FILE", "strength": "STRONG",
                          "detector": "SCANNED_COPY step: pages after the common judgment matching no page of the other copy, with an operative phrase",
                          "evidence_page": odd[0], "evidence_signals": "pages " + ranges(list(odd)), "segment_end_page": odd[-1],
                          "page_1_case_numbers": ";".join(A[a_].get("p1_cases", [])), "segment_case_numbers": "",
                          "operative_phrase_before": "", "operative_phrase_in_segment": True,
                          "evidence_text": collapse(get_pages(a_)["texts"][odd[0] - 1])[:200], "review_finding": "",
                          "counted_in_revised_total": a_ in REVIEW_EXTRA_JUDGMENTS, "verification": VERIFY})
    for c_ in contained_rows:
        x_, y_ = c_["files"].split(";")
        cand_rows.append({"sha256": x_, "court": court_of(x_), "title_meta": (meta.get(x_) or [{}])[0].get("title", "")[:120],
                          "pages": A[x_].get("pages"), "candidate_kind": "SAME_LEAD_CASE_CONTENT_MATCH_DATE_DIFFERS", "strength": "INFO",
                          "detector": "SCANNED_COPY step (beyond metadata date)", "evidence_page": "", "evidence_signals": c_["method"],
                          "segment_end_page": "", "page_1_case_numbers": ";".join(A[x_].get("p1_cases", [])),
                          "segment_case_numbers": "", "operative_phrase_before": "", "operative_phrase_in_segment": "",
                          "evidence_text": f"shares lead case {c_['key']} and page content with {y_[:16]} but dates differ ({c_['dates']}): "
                                           f"a later order carrying a copy of the judgment, or a metadata date error; not merged. {c_['evidence']}"[:400],
                          "review_finding": "", "counted_in_revised_total": False, "verification": VERIFY})
    for pr in pointer_rows:
        if pr["status"] != "LINKED_TO_LEAD_JUDGMENT":
            s = pr["sha256"]
            cand_rows.append({"sha256": s, "court": court_of(s), "title_meta": (meta.get(s) or [{}])[0].get("title", "")[:120],
                              "pages": A[s].get("pages"), "candidate_kind": "POINTER_ORDER_LEAD_NOT_LINKED", "strength": "INFO",
                              "detector": "POINTER step", "evidence_page": 1,
                              "evidence_signals": "pointer to " + ";".join(f"{n}/{y}" for n, y in pr["pointer"]), "segment_end_page": "",
                              "page_1_case_numbers": ";".join(A[s].get("p1_cases", [])), "segment_case_numbers": "",
                              "operative_phrase_before": "", "operative_phrase_in_segment": "",
                              "evidence_text": "lead judgment not found in the corpus with the same court, case number and date; counted as its own entity",
                              "review_finding": "", "counted_in_revised_total": False, "verification": VERIFY})
    for s in review_versions:
        cand_rows.append({"sha256": s, "court": court_of(s), "title_meta": "Virendra Kumar (SC, C.A. 9267/2019, 07-01-2020)",
                          "pages": recs[s].get("pages"), "candidate_kind": "TWO_VERSIONS_IN_ONE_FILE_CONFIRMED_BY_REVIEW", "strength": "REVIEWED",
                          "detector": "C10 REVIEW_FINDINGS.md", "evidence_page": 22,
                          "evidence_signals": "pp.1-21 marked CORRECTED; pp.22-42 the earlier version; operative paragraphs differ",
                          "segment_end_page": 42, "page_1_case_numbers": ";".join(recs[s].get("case_numbers_text_p1_3") or []),
                          "segment_case_numbers": "", "operative_phrase_before": "", "operative_phrase_in_segment": "",
                          "evidence_text": "bytes are not in the pinned commit (HF legal_knowledge copy); batch corrected_marker="
                                           + str(recs[s].get("corrected_marker")),
                          "review_finding": "Two versions in one file (REVIEW_FINDINGS.md)", "counted_in_revised_total": False,
                          "verification": VERIFY})
    cand_rows.sort(key=lambda r: (r["sha256"], str(r["evidence_page"]), r["candidate_kind"], r["detector"]))

    # ---- the 23 unresolved files
    plan_rows = []
    for c in sorted(cont, key=lambda r: r["sha256"]):
        s = c["sha256"]
        a, r, g = A[s], recs[s], reg[s]
        court = court_of(s)
        code = COURT_CODE.get(court, "SCI" if "/sci/" in g["path"] or "third_party" in g["path"] else "")
        ev = []
        if not a.get("bytes_in_repo"):
            state = "BYTES_NOT_IN_PINNED_COMMIT"
        else:
            state = "REHASH_OK" if a["rehash"] == s else "REHASH_MISMATCH"
        prefix_tests = []
        for off in a.get("eof_offsets", []):
            d2, n2 = open_pdf(fitz, (blobs.get(g["path"]) or b"")[:off + 5])
            prefix_tests.append(f"prefix to %%EOF@{off}: " + (f"opens, {n2} pages" if d2 is not None else "does not open"))
        if a.get("bytes_in_repo"):
            earlier = ("; ".join(prefix_tests) if prefix_tests else
                       f"NO %%EOF anywhere in {a['size']} bytes: no earlier complete revision inside the file")
        else:
            earlier = "NOT_TESTABLE (bytes unavailable)"
        if not a.get("bytes_in_repo"):
            present = "NONE (bytes unavailable)"
        elif not a.get("opens"):
            present = "NONE (file does not open: page tree or streams cut)"
        else:
            pw = a.get("pages_with_text", [])
            pp = a.get("printed_page_numbers", [])
            tot = a.get("printed_page_total", [])
            present = (f"declared {a['pages']} page objects; pages with text (>=50 chars): {ranges(pw) or 'none'} ({len(pw)}); "
                       f"printed page numbers seen: {ranges(pp) or 'none'}" + (f" of {'/'.join(str(t) for t in tot)}" if tot else "")
                       + " (numbers with a repeated digit such as 11 or 22 can be unreadable: the cut font drops repeated glyphs)")
        if not a.get("opens"):
            content = "NO_CONTENT_READABLE"
        elif a.get("pages") and len(a.get("pages_with_text", [])) == a["pages"]:
            content = "ALL_DECLARED_PAGES_HAVE_TEXT (content probably complete; file structure/signature tail cut)"
        else:
            content = f"PARTIAL: {len(a.get('pages_with_text', []))} of {a.get('pages')} declared pages have text"
        ms = meta.get(s, [])
        mcs = meta_cases(s)
        p1 = collapse(r.get("first_page_excerpt") or "")
        if not a.get("opens") or not p1:
            ident = "METADATA_ONLY: no readable page 1; identity rests on the crawler record (" + (";".join(mcs) or "no metadata record") + ")"
            reliable = "NOT_CONFIRMED_FROM_DOCUMENT"
        else:
            hits = []
            for mc in mcs:
                num = re.search(r"/(\d{1,6})/((?:19|20)\d{2})", mc)
                if num and re.search(rf"\b{num.group(1)}\s*/\s*{num.group(2)}\b", p1):
                    hits.append(mc)
            title_party = ""
            if ms:
                pet = (ms[0].get("parties_petitioner") or "").split("&")[0].split(" AND ")[0].strip()
                tok = [w for w in re.findall(r"[A-Za-z]{4,}", pet) if w.upper() not in ("UNION", "INDIA", "DECEASED", "THROUGH")]
                title_party = tok[0] if tok else ""
            party_hit = bool(title_party) and title_party.lower() in p1.lower()
            if hits:
                ident, reliable = f"page 1 prints the metadata case number(s) {';'.join(hits)}", "RELIABLE_FROM_PAGE_1"
            elif party_hit or (a.get("p1_cases") and mcs):
                ident = (f"page 1 readable but the metadata case number is not printed as such (page 1 numbers: {';'.join(a.get('p1_cases', [])) or 'none'}"
                         + (f"; petitioner '{title_party}' found" if party_hit else "") + "); likely a common judgment heading another matter")
                reliable = "PARTIAL_COMMON_JUDGMENT_HEADED_BY_OTHER_CASE" if party_hit or a.get("p1_cases") else "WEAK"
            else:
                ident, reliable = "page 1 readable; neither case number nor party matched", "WEAK"
        # complete copy elsewhere
        others = []
        for o, ratio in sorted(inc_links.get(s, [])):
            others.append(f"{o[:16]} (all readable pages match, first page {ratio}; {reg[o]['source_completeness']}; pages {recs[o].get('pages')})")
        ts = r.get("text_sha256")
        if ts:
            for o in by_text.get(ts, []):
                if o != s:
                    others.append(f"{o[:16]} (identical text; {reg[o]['source_completeness']})")
        same_cd = [o for o in by_cd[(court, date_of(s))] if o != s] if court and date_of(s) else []
        ctype = {m.split("/")[0] for m in mcs}
        possible = sorted(o for o in same_cd if o not in {x for x, _ in inc_links.get(s, [])} and
                          {m.split("/")[0] for m in meta_cases(o)} & ctype)
        complete_copy = [x for x in others if "COMPLETE_FILE_STRUCTURE" in x or "TAIL_CUT_AFTER_EARLIER_EOF" in x]
        if complete_copy:
            status = "COMPLETE_CONTENT_COPY_IN_CORPUS"
        elif others:
            status = "OTHER_COPIES_IN_CORPUS_ALL_INCOMPLETE"
        else:
            status = "NO_OTHER_COPY_FOUND"
        if not a.get("bytes_in_repo") and recs[s].get("extraction") == "NOT_PROCESSED_BYTES_UNAVAILABLE":
            action = "RETRIEVE_HELD_BYTES"
            source = ("the HF legal_knowledge copy at " + g["path"] + " (declared sha256 " + s[:16] + "...), or the C5 working store; "
                      "re-hash on receipt. If no held copy exists: " + OFFICIAL_SITE["SCI"])
            approval = "owner approval to download from the project's own HF dataset (CLAUDE.md working rule: ask before any real download run)"
        elif complete_copy:
            action = "USE_EXISTING_COPY_AS_CONTENT_SOURCE; KEEP_TRUNCATED_FILE_AS_RECORDED_COPY"
            source = "none needed for content: " + "; ".join(complete_copy) + ". Fresh official copy optional for a full signed file"
            approval = "legal/data owner sign-off to link the record to the existing copy (no download)"
        else:
            url = (ms[0].get("source_url") if ms else "") or ""
            action = "RE_ACQUIRE_COMPLETE_COPY"
            source = (f"official: {OFFICIAL_SITE.get(code, 'official court website')}; or a re-fetch of the recorded source URL ({url})"
                      if url else f"official: {OFFICIAL_SITE.get(code, 'official court website')}")
            approval = "owner approval for a real download run (CLAUDE.md working rule); no download was made"
        plan_rows.append({
            "sha256": s, "judgment_id": g["judgment_id"], "path": g["path"], "c10_disposition": c["disposition"],
            "source_completeness": g["source_completeness"], "court": court, "case_numbers_meta": ";".join(mcs),
            "issue_date_meta": date_of(s), "bytes": g["bytes"], "byte_state": state, "pdf_opens": a.get("opens", ""),
            "earlier_revision_check": earlier, "pages_present": present, "content_assessment": content if a.get("bytes_in_repo") else "NOT_AVAILABLE",
            "same_court_date_casetype_files_weak_lead": ";".join(o[:16] for o in possible),
            "page_1_identity": ident, "identity_reliability": reliable, "same_court_same_date_files": len(same_cd),
            "other_copies_in_corpus": " | ".join(others), "complete_copy_status": status, "recovery_action": action,
            "replacement_source": source, "approval_required": approval, "downloaded": "NO", "verification": VERIFY})

    # ---- composite bump (+1 only where the review confirmed and the second judgment is not already in the corpus)
    composite_bump = []
    for s in sorted(REVIEW_EXTRA_JUDGMENTS):
        if s not in recs:
            continue
        x = REVIEW_EXTRA_JUDGMENTS[s]
        present = sorted(o for o in shas if o != s for m in meta.get(o, []) if m["court"] == x["court"] and m["issue_date_meta"] == x["date"]
                         and re.search(rf"/{x['case_ny'][0]}/{x['case_ny'][1]}$", m["case_numbers_meta"] or ""))
        if s == "0f65307432d16f74f78ea8a4f37ad5d1d4b0e56188273575ac956eab22478d72":
            present += sorted(o for o in shas for m in meta.get(o, []) if "ADARSH" in m["title"].upper() and m["court"] == x["court"])
        composite_bump.append({"sha256": s, "judgment_key": f"JK-{s[:16]}#p{x['pages']}", "pages": x["pages"], "proceeding_key": x["proceeding"],
                               "title": x["title"], "source": x["source"], "change": 0 if present else 1,
                               "note": ("already present as " + ";".join(p[:16] for p in present)) if present else "not present elsewhere in the corpus"})
    extra_by_file = {b["sha256"]: b for b in composite_bump if b["change"] == 1}

    # ---- register
    comp_size = collections.Counter(find(s) for s in shas)
    reg_rows = []
    for s in shas:
        r, a, g = recs[s], A[s], reg[s]
        root = find(s)
        ms = meta.get(s, [])
        court = court_of(s)
        code = COURT_CODE.get(court, "SCI" if court.startswith("Supreme") else "UNK")
        pk_meta = [f"{code}:{m['case_numbers_meta']}" for m in ms if m["case_numbers_meta"]]
        pk_text = [f"{code}:{x}" for x in (a.get("cause_title_cases") or r.get("case_numbers_text_p1_3") or [])]
        # rendition class
        p = g["path"]
        if "third_party" in p:
            rend = "SECONDARY_COPY"
        elif not a.get("bytes_in_repo"):
            ex = r.get("first_page_excerpt") or ""
            rend = ("REPORTER_COPY_SCR_MIRROR" if SCR_HDR.search(ex) else "OFFICIAL_COURT_PDF_UNVERIFIED") if ex else "UNKNOWN_BYTES_UNAVAILABLE"
        elif p.startswith("data/raw/sci") and a.get("scr_reporter"):
            rend = "REPORTER_COPY_SCR_MIRROR"
        else:
            rend = "OFFICIAL_COURT_PDF"
        # version role
        if s in review_versions:
            vrole = "CONTAINS_TWO_VERSIONS_REVIEWED"
        elif a.get("strict_corr_pages") and a["strict_corr_pages"][0] <= 2:
            vrole = "CORRECTED_VERSION_CANDIDATE"
        elif g["source_completeness"] == "STORED_COPY_TAIL_CUT_AFTER_EARLIER_EOF_BASE_REVISION_PRESENT":
            vrole = "BASE_REVISION_ONLY_SIGNATURE_UPDATE_CUT"
        elif g["source_completeness"] == "STORED_COPY_TRUNCATED_CONTENT_MAY_BE_MISSING":
            vrole = "INCOMPLETE_COPY_VERSION_UNKNOWN"
        elif g["source_completeness"] == "NOT_AVAILABLE":
            vrole = "UNKNOWN_BYTES_UNAVAILABLE"
        else:
            vrole = "SINGLE_VERSION_NO_MARKER"
        if comp_size[root] == 1:
            ident = "SOLE_COPY_OF_JUDGMENT"
        elif s == root:
            ident = "REPRESENTATIVE_COPY_OF_JUDGMENT"
        else:
            ident = "ADDITIONAL_COPY_OF_JUDGMENT"
        comp_flag = "COMPOSITE_REVIEWED" if s in review_composite else ("COMPOSITE_CANDIDATE" if strong_composite(s) else "")
        if s in REVIEW_SPLIT:
            comp_flag = REVIEW_SPLIT[s]
        xb = extra_by_file.get(s)
        ev = [f"rehash={'OK' if a.get('rehash') == s else ('MISMATCH' if a.get('bytes_in_repo') else 'NO_BYTES')}"]
        if a.get("text_sha256_recomputed"):
            ev.append("text_sha256=" + ("REPRODUCED" if a["text_sha256_recomputed"] == r.get("text_sha256") else "DIFFERS"))
        if group_of.get(s):
            ev.append("group=" + group_of[s])
        if a.get("producer"):
            ev.append("producer=" + a["producer"][:40])
        if a.get("eof_offsets") and len(a["eof_offsets"]) > 1:
            ev.append(f"eof_markers={len(a['eof_offsets'])}")
        reg_rows.append({
            "sha256": s, "judgment_id_c10": g["judgment_id"], "path": p, "court": court, "doc_ids": ";".join(m["doc_id"] for m in ms),
            "issue_date_meta": date_of(s), "pages": r.get("pages") if r.get("pages") is not None else "",
            "text_quality": text_quality(s), "text_sha256": r.get("text_sha256") or "", "same_text_group": group_of.get(s, ""),
            "judgment_key": "JK-" + root[:16], "copies_of_judgment": comp_size[root], "copy_identity_role": ident,
            "proceeding_keys_meta": ";".join(pk_meta), "proceeding_keys_cause_title_partial": ";".join(pk_text),
            "additional_judgments_in_file": (f"{xb['judgment_key']} | {xb['proceeding_key']} | {xb['title']}" if xb else ""),
            "version_role": vrole, "rendition_class": rend, "source_completeness": g["source_completeness"],
            "composite_flag": comp_flag, "evidence": "; ".join(ev), "verification": VERIFY})

    # ---- summary
    n_files = len(shas)
    n_components = len({find(s) for s in shas})
    bump = sum(x["change"] for x in composite_bump)
    cls_counts = collections.Counter(g["classification"] for g in group_rows if g["scope"] == "EXACT_TEXT_SHA256")
    chg = collections.Counter()
    for g in group_rows:
        chg[g["scope"]] += g["judgment_count_change"]
    # the three scopes share files only through union-find, so the component count is authoritative; report the sum check
    summary = {
        "tool": TOOL_VERSION, "pinned_commit": COMMIT, "verification": VERIFY,
        "accounting": {"files_in_batches": n_files, "files_in_copy_register": len(reg), "register_rows": len(reg_rows),
                       "register_unique_sha256": len({r["sha256"] for r in reg_rows}),
                       "every_file_exactly_once": len(reg_rows) == n_files == len({r["sha256"] for r in reg_rows}) and set(r["sha256"] for r in reg_rows) == set(shas),
                       "bytes_in_pinned_commit": sum(1 for s in shas if A[s].get("bytes_in_repo")),
                       "rehash_matches": sum(1 for s in shas if A[s].get("rehash") == s),
                       "rehash_mismatches": sorted(s for s in shas if A[s].get("rehash_mismatch")),
                       "pdf_opens": sum(1 for s in shas if A[s].get("opens")),
                       "text_sha256_reproduced": sum(1 for s in shas if A[s].get("text_sha256_recomputed") and A[s]["text_sha256_recomputed"] == recs[s].get("text_sha256")),
                       "text_sha256_differs": text_mismatch},
        "same_text_reproduction": {"prior_finding": {"groups": PRIOR_GROUPS, "files": PRIOR_FILES},
                                   "reproduced": {"groups": len(groups), "files": n_group_files},
                                   "matches_prior": len(groups) == PRIOR_GROUPS and n_group_files == PRIOR_FILES,
                                   "groups_with_empty_text": sum(1 for v in groups if recs[v[0]]["text_sha256"] == EMPTY_SHA),
                                   "min_text_chars_in_groups": min((recs[v[0]].get("text_chars_total") or 0) for v in groups) if groups else None},
        "exact_group_classification": dict(sorted(cls_counts.items())),
        "extension_groups": {"NORMALIZED_TEXT_EXTENSION": sum(1 for g in group_rows if g["scope"] == "NORMALIZED_TEXT_EXTENSION"),
                             "INCOMPLETE_COPY_ALL_PAGE_MATCH": sum(1 for g in group_rows if g["scope"] == "INCOMPLETE_COPY_ALL_PAGE_MATCH"),
                             "SAME_WORDS_NUMBERS_DIFFER_NOT_MERGED": sum(1 for g in group_rows if g["scope"] == "SAME_WORDS_NUMBERS_DIFFER_NOT_MERGED"),
                             "SCANNED_COPY_LEAD_CASE_MATCH": sum(1 for g in group_rows if g["scope"] == "SCANNED_COPY_LEAD_CASE_MATCH"),
                             "POINTER_ORDER_TO_LEAD_JUDGMENT": sum(1 for g in group_rows if g["scope"] == "POINTER_ORDER_TO_LEAD_JUDGMENT")},
        "group_classification_all_scopes": dict(sorted(collections.Counter(f"{g['scope']}|{g['classification']}" for g in group_rows).items())),
        "distinct_judgments": {
            "c10_count_by_file": n_files,
            "change_exact_text_groups": chg["EXACT_TEXT_SHA256"],
            "change_normalized_text_extension": chg["NORMALIZED_TEXT_EXTENSION"],
            "change_incomplete_copy_all_page_match": chg["INCOMPLETE_COPY_ALL_PAGE_MATCH"],
            "change_scanned_copy_lead_case_match": chg["SCANNED_COPY_LEAD_CASE_MATCH"],
            "change_pointer_orders_linked_to_lead": chg["POINTER_ORDER_TO_LEAD_JUDGMENT"],
            "change_judgments_inside_composite_files": bump,
            "judgment_entities_from_files": n_components,
            "additional_judgment_keys": [b["judgment_key"] for b in composite_bump if b["change"] == 1],
            "revised_distinct_judgments": n_components + bump,
            "revised_without_pointer_rule": n_components + bump - chg["POINTER_ORDER_TO_LEAD_JUDGMENT"],
            "revised_exact_text_only": n_files + chg["EXACT_TEXT_SHA256"] + bump,
            "sum_check": n_files + sum(chg.values()) == n_components,
            "not_counted": {
                "automated_composite_candidates_strong": len({r["sha256"] for r in cand_rows if r["candidate_kind"] in ("COMPOSITE_CANDIDATE", "MULTI_DOCUMENT_FILE_CANDIDATE") and r["strength"] == "STRONG" and r["sha256"] not in review_composite}),
                "two_versions_in_one_file_reviewed": len(review_versions),
                "pointer_orders_lead_not_linked": sum(1 for r in pointer_rows if r["status"] != "LINKED_TO_LEAD_JUDGMENT"),
                "same_lead_case_content_match_date_differs": len(contained_rows),
                "note": "two versions or two opinions of one judgment stay one judgment; automated composite candidates change nothing until reviewed",
            },
            "composite_detail": composite_bump,
            "basis": "a judgment entity is a connected set of files linked by evidence: exact same text with byte-level or render-level "
                     "confirmation; identical letters and numbers (time stamps and quote/dash glyphs normalised) with the same court, date "
                     "and page count; an incomplete copy matching on every readable page; a scanned copy sharing the lead case "
                     "(footer, pointer or cause title), court and date, confirmed on page text or page images; or a one-page pointer "
                     "order linked to its lead judgment. Similarity alone never merges files. A judgment held inside another file "
                     "(composite) gets its own key (file sha + page range).",
        },
        "candidates": dict(sorted(collections.Counter(f"{r['candidate_kind']}|{r['strength']}" for r in cand_rows).items())),
        "incomplete_23": {"files": len(plan_rows),
                          "complete_copy_status": dict(sorted(collections.Counter(r["complete_copy_status"] for r in plan_rows).items())),
                          "recovery_action": dict(sorted(collections.Counter(r["recovery_action"] for r in plan_rows).items())),
                          "identity_reliability": dict(sorted(collections.Counter(r["identity_reliability"] for r in plan_rows).items())),
                          "earlier_complete_revision_found": sum(1 for r in plan_rows if "opens" in r["earlier_revision_check"]),
                          "downloads_made": 0},
        "routed_to_metadata_workstream": meta_issues + [
            {"files": "48e3c2db90f438ba51016ddc7b9abf6027d468a73b94ca44f069602e01ced4f3;8a0be890282d401f4dbf33093e093ac3b7dbe62a8ae4e31e2e3349dfcc25cefd",
             "issue": "neutral citation 2018 INSC 185 attached to two different Kudrat Sandhu orders (22.02.2018 and 21.08.2018) (review F11)"},
            {"files": "c1a83ee07b70 (full sha in register)", "issue": "issue_date_meta 2024-12-02 but the order prints 18.05.2015 (review F11)"}],
        "inputs_sha256": input_digests,
        "c10_duplicate_register_kinds": dict(sorted(collections.Counter(d["kind"] for d in dups).items())),
    }
    blobs.close()

    reg_fields = ["sha256", "judgment_id_c10", "path", "court", "doc_ids", "issue_date_meta", "pages", "text_quality", "text_sha256",
                  "same_text_group", "judgment_key", "copies_of_judgment", "copy_identity_role", "proceeding_keys_meta",
                  "proceeding_keys_cause_title_partial", "additional_judgments_in_file", "version_role", "rendition_class", "source_completeness", "composite_flag",
                  "evidence", "verification"]
    grp_fields = ["group_id", "scope", "n_files", "representative_sha256", "file_sha256s", "text_sha256", "text_chars", "text_quality",
                  "readable_ratio", "pages", "courts", "issue_dates_meta", "meta_records", "meta_case_numbers",
                  "meta_case_numbers_found_in_text_p1_3", "first_page_excerpt", "producers", "eof_markers_per_file", "byte_comparison",
                  "byte_diff_nature", "incomplete_members", "composite_members", "classification", "classification_basis",
                  "judgment_count_change", "verification"]
    cand_fields = ["sha256", "court", "title_meta", "pages", "candidate_kind", "strength", "detector", "evidence_page",
                   "evidence_signals", "segment_end_page", "page_1_case_numbers", "segment_case_numbers", "operative_phrase_before",
                   "operative_phrase_in_segment", "evidence_text", "review_finding", "counted_in_revised_total", "verification"]
    plan_fields = ["sha256", "judgment_id", "path", "c10_disposition", "source_completeness", "court", "case_numbers_meta",
                   "issue_date_meta", "bytes", "byte_state", "pdf_opens", "earlier_revision_check", "pages_present", "content_assessment",
                   "same_court_date_casetype_files_weak_lead", "page_1_identity",
                   "identity_reliability", "same_court_same_date_files", "other_copies_in_corpus", "complete_copy_status",
                   "recovery_action", "replacement_source", "approval_required", "downloaded", "verification"]
    return {
        "JUDGMENT_IDENTITY_REGISTER.csv": csv_text(reg_fields, reg_rows),
        "SAME_TEXT_GROUPS.csv": csv_text(grp_fields, group_rows),
        "COMPOSITE_AND_VERSION_CANDIDATES.csv": csv_text(cand_fields, cand_rows),
        "INCOMPLETE_23_RECOVERY_PLAN.csv": csv_text(plan_fields, plan_rows),
        "IDENTITY_SUMMARY.json": json.dumps(summary, indent=2, sort_keys=True) + "\n",
    }


def sums_text(files):
    return "".join(f"{sha(files[n].encode('utf-8'))}  {n}\n" for n in OUTPUT_FILES)


def verify_existing():
    """No-PyMuPDF path: checksums and accounting identity of the committed outputs."""
    problems = []
    sums = (OUT / "OUTPUT_SHA256SUMS").read_text().splitlines()
    for ln in sums:
        h, n = ln.split("  ", 1)
        if sha((OUT / n).read_bytes()) != h:
            problems.append(f"checksum differs: {n}")
    regrows = rcsv(OUT / "JUDGMENT_IDENTITY_REGISTER.csv")
    cop = rcsv(C10 / "outputs" / "HF_JUDGMENT_COPY_REGISTER.csv")
    if sorted(r["sha256"] for r in regrows) != sorted(r["sha256"] for r in cop) or len(regrows) != len({r["sha256"] for r in regrows}):
        problems.append("register does not list every file exactly once")
    return problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, help="clone of the corpus repository holding commit " + COMMIT)
    ap.add_argument("--check", action="store_true", help="rebuild and compare with outputs/ (exit 1 on any difference)")
    args = ap.parse_args()
    try:
        try:
            import pymupdf  # noqa: F401
        except ImportError:
            import fitz  # noqa: F401
        have = True
    except ImportError:
        have = False
    if not have:
        if args.check:
            probs = verify_existing()
            print("SKIP full reproduction: PyMuPDF is not installed (needed to read PDFs).")
            print("checked instead: OUTPUT_SHA256SUMS and the one-row-per-file accounting identity:",
                  "OK" if not probs else "; ".join(probs))
            sys.exit(1 if probs else 0)
        sys.exit("PyMuPDF (pymupdf) is required to build; use --check for the checksum-only verification")
    files = build(args.repo)
    files_all = dict(files)
    files_all["OUTPUT_SHA256SUMS"] = sums_text(files)
    if args.check:
        diffs = []
        for n, t in sorted(files_all.items()):
            p = OUT / n
            if not p.exists() or p.read_bytes() != t.encode("utf-8"):
                diffs.append(n)
        print("check:", "OK, all outputs reproduced byte for byte" if not diffs else "DIFFERS: " + ", ".join(diffs))
        sys.exit(1 if diffs else 0)
    OUT.mkdir(parents=True, exist_ok=True)
    for n, t in files_all.items():
        (OUT / n).write_bytes(t.encode("utf-8"))
    s = json.loads(files["IDENTITY_SUMMARY.json"])
    print(json.dumps({"accounting": s["accounting"]["every_file_exactly_once"], "same_text": s["same_text_reproduction"]["reproduced"],
                      "classification": s["exact_group_classification"], "distinct": s["distinct_judgments"]["revised_distinct_judgments"]}))


if __name__ == "__main__":
    main()
