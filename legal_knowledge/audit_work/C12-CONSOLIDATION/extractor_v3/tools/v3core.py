"""Mimamsa C12 judicial outcome extraction, version 3: core (pure functions, no I/O).

Evolved from the frozen C11 comparator c11-extract-v2/1.0.0 (v2core.py). Every value produced here is an
AUTOMATED CANDIDATE read from a PDF text layer. Nothing is legally verified.

v3 emits one row per PROCEEDING (normalised host case number) with two outcome fields:
  printed_disposal    the literal disposal the court prints for that proceeding (allowed, dismissed, disposed_of, ...)
  substantive_result  what the disposal means for the relief sought (relief_granted, relief_refused, no_adjudication,
                      remanded_for_fresh_decision, interim_only, ...), read from the operative part
Either field is OUTCOME_UNVERIFIED (with abstain_reason) when the text does not determine it.

Pipeline (structural):
  1. mask boilerplate (offset-preserving); split into opinion/order segments at signature blocks; composite files;
  2. host proceedings from the cause title (excluding 'arising out of', impugned and lower-forum numbers) and
     crawler metadata, normalised to TYPE NUM/YEAR;
  3. batch judgments: per-proceeding SECTIONS headed by a host case number are analysed separately;
  4. operative part: disposition clauses (verb form, tense, subject class, case numbers, party descriptors),
     quotation tracking that ends at the closing quote;
  5. per-proceeding aggregation; generic dispositions expand to the host proceedings of the matching type;
     explicit abstention rules.
"""
import bisect
import re

VERSION = "c12-extract-v3/1.0.0"
STATUS = "AUTOMATED_CANDIDATE_NOT_VERIFIED"
UNVERIFIED = "OUTCOME_UNVERIFIED"
OUTCOME_VOCAB = ["allowed", "partly_allowed", "dismissed", "dismissed_as_withdrawn", "dismissed_as_infructuous",
                 "disposed_of_with_directions", "remanded", "set_aside_and_remanded", "transferred", "not_final",
                 UNVERIFIED]   # internal (v2) clause classes
PRINTED_VOCAB = ["allowed", "partly_allowed", "dismissed", "dismissed_as_withdrawn", "dismissed_as_infructuous",
                 "dismissed_in_default", "disposed_of", "disposed_of_with_directions", "remanded", "set_aside_and_remanded",
                 "transferred", "not_final", UNVERIFIED]
SUBST_VOCAB = ["relief_granted", "relief_partly_granted", "relief_refused", "no_adjudication",
               "remanded_for_fresh_decision", "interim_only", UNVERIFIED]

PAGE_RE = re.compile(r"\[\[page (\d+)\]\]")

# ------------------------------------------------------------------ boilerplate masking
_MASK_LINE_RES = [re.compile(p, re.I) for p in [
    r"^\s*[A-H]\s*$",                                   # S.C.R. margin letters
    r"^\s*[-–]?\s*\d{1,4}\s*[-–]?\s*$",                 # bare page numbers
    r"^\s*\[\s*\d{1,3}\s*\]\s*$",                        # [2]
    r"^\s*-\s*\d{1,3}\s*-\s*$",
    r"^\s*SUPREME COURT REPORTS\s*$",
    r"^\s*\[\d{4}\]\s*(?:Supp\.?\s*)?\(?\d*\)?\s*S\.\s*C\.\s*R\.?\s*(?:\d+)?\s*$",
    r"^\s*\d+\s+\[\d{4}\].{0,20}S\.C\.R\.?\s*$",
    r"Digitally\s+Signed", r"^\s*By\s*:", r"Signing\s+Da", r"Signature\s+Not\s+Verified",
    r"^\s*\d{2}:\d{2}(:\d{2})?\s*$", r"^\s*\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}", r"I attest", r"authenticity of this",
    r"integrity of this", r"I am the author of this", r"^\s*document\s*$", r"Page\s+\d+\s+of\s+\d+",
    r"Neutral\s+Citation", r"VERDICTUM", r"Whether\s+(speaking|reasoned|reportable|approved|to be referred)",
    r"^\s*(Yes|No)\s*/\s*(Yes|No)\s*$", r"^\s*(Yes|No)\s*$", r"^\s*:\s*$", r"Uploaded\s+on", r"Downloaded\s+on",
    r"^\s*\$\s*~", r"^\s*[*+]\s*$", r"^\s*\.{0,3}\s*$",
    r"\[[A-Z][A-Z .,'()-]{2,60},\s*(?:C\.?\s*)?J\.?\s*\]\s*$",  # S.C.R. running head [NAME, J.]
    r"^\s*\(?\s*Assisted by\s*:",
]]


_SIGN_BLOCK_RE = re.compile(r"Signed\s*By|Signing\s+Da|Signature\s+Not\s+Verified|Digitally\s+Signed|^\s*Signed\s*$", re.I)
_SIGN_TAIL_RE = re.compile(r"^[ \t]*[A-Z][A-Z .:'-]{0,38}[ \t]*$|^[ \t]*[\d.:/ -]{4,25}[ \t]*$")


def mask_boilerplate(text):
    """Replace boilerplate lines with spaces (length preserved so offsets stay valid). v3: the short upper-case
    name/date lines that follow a digital-signature stamp ('Signed By:AMIT KUMAR' / 'SHARMA') are masked too."""
    out = []
    tail = 0
    for line in text.splitlines(True):
        body = line.rstrip("\n")
        if body and (any(r.search(body) for r in _MASK_LINE_RES) or _SIGN_BLOCK_RE.search(body)):
            out.append(" " * len(body) + line[len(body):])
            tail = 3 if _SIGN_BLOCK_RE.search(body) else tail
        elif body and tail and _SIGN_TAIL_RE.match(body):
            out.append(" " * len(body) + line[len(body):])
            tail -= 1
        else:
            out.append(line)
            if body.strip():
                tail = 0
    return "".join(out)


def mask_page_markers(text):
    return PAGE_RE.sub(lambda m: " " * len(m.group(0)), text)


def page_index(text):
    starts, nums = [], []
    for m in PAGE_RE.finditer(text):
        starts.append(m.start())
        nums.append(int(m.group(1)))
    return starts, nums


def page_at(pidx, pos):
    starts, nums = pidx
    if not starts:
        return 1
    i = bisect.bisect_right(starts, pos) - 1
    return nums[i] if i >= 0 else nums[0]


def squash(s, limit=None):
    s = " ".join(s.split())
    if limit and len(s) > limit:
        s = s[:limit - 3].rstrip() + "..."
    return s


# ------------------------------------------------------------------ sentences
_ABBR = set("""no nos v vs mr mrs ms dr hon ltd co st sr jr j jj art arts sec secs s ss r rr cl para paras crl cr w p c a m
misc appl viz i e g etc rs lt col gen maj capt brig sub hav nk sep smt sh shri govt pvt inc o u ex ors anr vol pp ibid
supra cf ch sl dt dated nb l k b d f h n t y x z civ spl crim wp cwp lpa slp ca ia cm ma oa ta sc scc scr air hc rtd retd
regt bn coy hq pb adv sr. addl asst dy jt ld sri km""".split())


def sentences(text, start, end):
    """Yield (s, e) sentence spans inside text[start:end]. Splits at . ? ! ; : followed by whitespace,
    except after common legal abbreviations and single letters; also at blank-line breaks."""
    spans = []
    s = start
    for m in re.finditer(r"[.?!;:][\u201d\u2019\"']?(?=\s)", text[start:end]):
        p = start + m.end()
        ch = m.group(0)[0]
        if ch == ".":
            j = start + m.start()
            k = j
            while k > start and (text[k - 1].isalnum() or text[k - 1] == "."):
                k -= 1
            tok = text[k:j].lower().strip(".")
            if tok in _ABBR or (len(tok) == 1 and tok.isalpha()) or re.fullmatch(r"(?:[a-z]\.){1,4}[a-z]", tok):
                continue   # v3: initials ('B.D. Khunte') do not end a sentence
            nxt = text[p:p + 30].lstrip()
            if nxt[:1].islower() or nxt[:1].isdigit() and tok in ("no", "nos"):
                continue
        if text[s:p].strip():
            spans.append((s, p))
        s = p
    if text[s:end].strip():
        spans.append((s, end))
    return spans


# ------------------------------------------------------------------ quotes
_QUOTE_INTRO_RE = re.compile(
    r"\b(held|observed|opined|stated|noted|remarked|reads?|read|laid\s+down|provides?|extracted|reproduced|quoted|"
    r"said|ruled|directed|recorded|is\s+as\s+follows|as\s+under|as\s+follows|thus|in\s+the\s+following\s+words|"
    r"which\s+is\s+as\s+under)\b[^.:\n]{0,80}?:\s*[-–]?", re.I)
_OWN_ORDER_BEFORE_RE = re.compile(r"(we|court)\s+(hereby\s+)?(pass|issue|make|direct|order)|following\s+(order|directions?)"
                                  r"|we\s+order|in\s+the\s+result|accordingly", re.I)


_RESUME_RE = re.compile(
    r"\n[ \t]*\n[ \t]*(?:\d{1,3}\s*\.\s*)?(?=(?:For\s+the\s+(?:foregoing|aforesaid|above|reasons)|In\s+view\s+of|Accordingly|In\s+the\s+result|"
    r"Resultantly|Consequently|Hence|Thus,|Therefore,|In\s+the\s+(?:facts|light|instant|present)|We\s+(?:are|have|find|do|may|would|"
    r"therefore|accordingly|hold|see|also|now)|This\s+(?:petition|appeal|writ)|The\s+(?:petition|appeal|writ\s+petition)\s+is|"
    r"Applying|Having\s+regard|Coming\s+to|Reverting|Adverting|Admittedly|In\s+our\s+(?:view|opinion|considered)|Now,?|So\s+far)\b)")


def quote_spans(text, para_starts_fn=None):
    """Return sorted list of (start, end, kind, intro_start) quoted spans.
    kind: 'marked' (curly or straight quotation marks) or 'intro_block' (unmarked block after 'held as under:')."""
    spans = []
    i = 0
    n = len(text)
    while True:
        o = text.find("“", i)
        if o < 0:
            break
        c = text.find("”", o + 1)
        if c < 0 or c - o > 15000:
            i = o + 1
            continue
        spans.append((o, c + 1, "marked"))
        i = c + 1
    # straight quotes: decide opening/closing from the neighbouring characters, then pair open -> next close
    opened = None
    for m in re.finditer('"', text):
        p = m.start()
        prv = text[p - 1] if p > 0 else " "
        nxt = text[p + 1] if p + 1 < n else " "
        is_open = (prv.isspace() or prv in "([:-\u2014") and not nxt.isspace()
        is_close = (not prv.isspace()) and (nxt.isspace() or nxt in ".,;:)-\u2014")
        if is_open and not is_close:
            opened = p
        elif is_close and opened is not None:
            if p - opened <= 8000:
                spans.append((opened, p + 1, "marked"))
            opened = None
    # v3: some text layers carry the curly quotes as '<' (open) and '=' (close); pair them when that encoding is
    # evident (several '<Word' openings and 'word=' closings) and no curly quotes are present
    if "\u201c" not in text and len(re.findall(r"(?:^|\s)<\s?[A-Za-z0-9]", text)) >= 2 and \
            len(re.findall(r"[A-Za-z0-9.,;)]=(?=\s|$)", text)) >= 2:
        i = 0
        while True:
            mo = re.compile(r"(?:^|(?<=\s))<(?=\s?[A-Za-z0-9])").search(text, i)
            if not mo:
                break
            mc = re.compile(r"(?<=[A-Za-z0-9.,;)?!])=(?=\s|$)").search(text, mo.end())
            mo2 = re.compile(r"(?:^|(?<=\s))<(?=\s?[A-Za-z0-9])").search(text, mo.end(), mc.start() if mc else mo.end())
            if not mc or mc.start() - mo.start() > 4000 or mo2 or \
                    re.search(r"\n[ \t]*\d{1,3}[ \t]*\.[ \t]+[A-Z]", text[mo.end():mc.start()]):
                i = mo.end()
                continue
            spans.append((mo.start(), mc.end(), "marked"))
            i = mc.end()
    spans.sort()
    merged = []
    for s, e, kd in spans:
        if merged and s < merged[-1][1]:
            if e > merged[-1][1]:
                merged[-1] = (merged[-1][0], e, kd)
            continue
        merged.append((s, e, kd))
    out = [(s, e, kd, max(0, s - 300)) for s, e, kd in merged if e - s >= 60]
    # unmarked blocks introduced by 'held as under:' etc.
    for m in _QUOTE_INTRO_RE.finditer(text):
        after = text[m.end():m.end() + 60]
        if re.match(r"\s*[“\"'‘]", after):
            continue
        before = text[max(0, m.start() - 120):m.end()]
        if _OWN_ORDER_BEFORE_RE.search(before):
            continue
        bs = m.end()
        be = para_starts_fn(bs) if para_starts_fn else None
        if be is None:
            be = min(n, bs + 2500)
        be = min(be, bs + 6000)
        # v3: an unmarked block also ends where the court resumes in its own voice after a paragraph break
        mr = _RESUME_RE.search(text, bs + 20, be)
        if mr:
            be = mr.start()
        if be - bs >= 20:
            out.append((bs, be, "intro_block", max(0, m.start() - 300)))
    out.sort()
    return out


def in_spans(spans, starts, pos):
    i = bisect.bisect_right(starts, pos) - 1
    while i >= 0:
        s, e = spans[i][0], spans[i][1]
        if s <= pos < e:
            return spans[i]
        if i > 0 and spans[i - 1][1] > pos:
            i -= 1
            continue
        break
    return None


# ------------------------------------------------------------------ paragraph numbers
_PARA_CAND_RE = re.compile(r"(?m)^[ \t]*(\d{1,3})[ \t]*\.(?=\s)")


def host_paragraphs(text, start, end, quote_list, qstarts):
    """Longest +1/+2 chain of line-initial paragraph numbers (outside marked quotes). Returns [(pos, n)]."""
    cands = []
    for m in _PARA_CAND_RE.finditer(text, start, end):
        q = in_spans(quote_list, qstarts, m.start()) if quote_list else None
        if q and q[2] == "marked":
            continue
        cands.append((m.start(), int(m.group(1))))
    if not cands:
        return []
    L = len(cands)
    dp = [1] * L
    prev = [-1] * L
    for i in range(L):
        ni = cands[i][1]
        best, bj = 0, -1
        for j in range(i - 1, max(-1, i - 80), -1):
            d = ni - cands[j][1]
            if d in (1, 2, 3) and dp[j] - (0.25 * (d - 1)) > best:
                best, bj = dp[j] - (0.25 * (d - 1)), j
        if bj >= 0:
            dp[i] = best + 1
            prev[i] = bj
        elif ni > 3:
            dp[i] = 0.5
    i = max(range(L), key=lambda k: (dp[k], k))
    chain = []
    while i >= 0:
        chain.append(cands[i])
        i = prev[i]
    chain.reverse()
    if len(chain) < 2 and chain and chain[0][1] != 1:
        return []
    return chain


def para_at(chain, pos):
    if not chain:
        return None
    lo = bisect.bisect_right([c[0] for c in chain], pos) - 1
    return chain[lo][1] if lo >= 0 else None


# ------------------------------------------------------------------ case numbers
_NUMGROUP = r"((?:\d{1,6}(?:\s*[-–]\s*\d{1,6})?\s*(?:,|and|&)\s*)*\d{1,6}(?:\s*[-–]\s*\d{1,6})?)"
_CASENO_RE = re.compile(_NUMGROUP + r"\s*(?:of|/|-)\s*((?:19|20)\d{2})\b", re.I)
_TYPE_BEFORE_RE = re.compile(r"([A-Za-z][A-Za-z.()&\s\-]{0,45}?)\s*(?:Nos?\s*\.?|Numbers?|D\.?\s*No\.?)?\s*[:.\-\u2013]?\s*$")


def _expand(group):
    nums = set()
    for part in re.split(r"\s*(?:,|and|&)\s*", group):
        part = part.strip()
        if not part:
            continue
        m = re.match(r"(\d+)\s*[-–]\s*(\d+)$", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if 0 <= b - a <= 60:
                nums.update(range(a, b + 1))
            else:
                nums.update([a, b])
        elif part.isdigit():
            nums.add(int(part))
    return nums


def ptype(t):
    t = (t or "").lower()
    t = re.sub(r"[^a-z]", "", t)
    if not t:
        return ""
    for key, pat in [("ia", r"(^|[^a-z])?(ia|interlocutoryapplication)$"), ]:
        pass
    table = [
        ("misc", r"(cmappl|cmapp|crlmappl|crlma|^cm$|cmno|cmp|^ia$|interlocutory|application|appl|^ma$|miscellaneous|misc|exemption|stay|caveat)"),
        ("lower", r"(^oa$|originalapplication|^ta$|transferapplication|complaint|fir|suit$|^cs$|courtmartial|^gcm$|^scm$|^dcm$)"),
        ("tc", r"(transferredcase|^tc|transfercase)"),
        ("slp", r"(slp|specialleave)"),
        ("lpa", r"(lpa|letterspatent)"),
        ("crla", r"(criminalappeal|crla|crlapp|^cra$)"),
        ("ca", r"(civilappeal|^ca$|^cas$)"),
        ("wp", r"(writpetition|^wp|cwp|owp|^swp|writa|writc|^writ|wpc|wpcrl|wps|wpcrl|^wri[ac]$|crwp|crlwp|wpil)"),
        ("spla", r"(specialappeal|spla)"),
        ("rp", r"(review|^rp$|^rplpa$)"),
        ("cont", r"(contempt|cocp|conc|coc)"),
        ("rev", r"(revision|crr|crrev)"),
        ("appeal", r"(appeal|^rsa$|^fao$|^capl$|^laapp$|^macapp$|^crr$|^cr$)"),
        ("petition", r"(petition)"),
    ]
    for key, pat in table:
        if re.search(pat, t):
            return key
    return "other"


def find_case_numbers(s):
    """Return list of dicts {type, ptype, nums, year, label, pos}."""
    out = []
    for m in _CASENO_RE.finditer(s):
        pre = s[max(0, m.start() - 50):m.start()]
        tm = _TYPE_BEFORE_RE.search(pre)
        typ = tm.group(1).strip() if tm else ""
        typ = re.sub(r"^.*\b(?:in|of|and|with|the|from|by|vide|under|to)\s+", "", typ, flags=re.I).strip()
        km = list(_TYPE_KEY_RE.finditer(typ))
        if km:
            typ = typ[km[-1].start():].strip()
        elif typ.split():
            typ = typ.split()[-1]
        label = squash((typ + " " + s[m.start():m.end()]) if typ else s[m.start():m.end()])
        out.append({"type": typ, "ptype": ptype(typ), "nums": _expand(m.group(1)), "year": int(m.group(2)),
                    "label": label, "pos": m.start()})
    for m in re.finditer(r"\b([A-Z][A-Za-z.()]{1,20})[-/ ](\d{1,6})[-/]((?:19|20)\d{2})\b", s):
        if any(o["pos"] <= m.start() < o["pos"] + 30 for o in out):
            continue
        if re.sub(r"[^a-z]", "", m.group(1).lower()) in ("no", "nos", "number", "dated", "dt") or \
                any(o["year"] == int(m.group(3)) and int(m.group(2)) in o["nums"] and abs(o["pos"] - m.start()) < 30 for o in out):
            continue
        out.append({"type": m.group(1), "ptype": ptype(m.group(1)), "nums": {int(m.group(2))},
                    "year": int(m.group(3)), "label": m.group(0), "pos": m.start()})
    out.sort(key=lambda o: o["pos"])
    return out


def meta_case_numbers(s):
    out = []
    for part in (s or "").split(";"):
        part = part.strip()
        m = re.match(r"(.+?)/(\d+)/((?:19|20)\d{2})$", part)
        if m:
            out.append({"type": m.group(1), "ptype": ptype(m.group(1)), "nums": {int(m.group(2))},
                        "year": int(m.group(3)), "label": part, "pos": -1})
    return out


# ------------------------------------------------------------------ disposition clause parsing
_AUX = {"is", "are", "stands", "stand", "stood", "already", "kindly", "be", "been", "being", "was", "were", "shall", "hereby", "accordingly", "also",
        "consequently", "therefore", "thus", "resultantly", "herewith", "thereby", "hence", "hereunder", "has", "have",
        "had", "will", "would", "should", "must", "may", "might", "can", "cannot", "could", "not", "to", "deserves",
        "deserve", "liable", "ought", "partly", "partially", "liberty", "also", "summarily", "finally", "consequentially",
        "as", "such", "herein", "in", "limine", "rightly", "wholly", "entirely", "fully"}
_PAST = {"was", "were", "been", "being", "had", "has", "have", "stood"}
_MODAL_WEAK = {"deserves", "deserve", "liable", "ought", "must", "should", "to"}
_MODAL_COND = {"would", "may", "might", "can", "cannot", "could", "not", "will"}

_PASSIVE_VERB_RE = re.compile(
    r"\b(partly\s+allowed|partially\s+allowed|allowed\s+in\s+part|allowed\s+partly|partly\s+accepted|"
    r"accepted\s+in\s+part|allowed|accepted|dismissed|rejected|disposed\s+of+|disposed\s+off|disposed|withdrawn|"
    r"remanded|remitted|transferred|set\s*-?\s*aside|quashed|closed|discharged|made\s+absolute|"
    r"consigned(?=\s+to\s+(?:the\s+)?records?)|transmitted(?=\s+to\s+the\s+(?:Armed|AFT|Tribunal)))\b", re.I)
_ACTIVE_RE = re.compile(
    r"\b(?:we|this\s+court|the\s+court)\b[\s,\-]*(?:(?:accordingly|therefore|hence|hereby|thus|consequently|would|"
    r",|also|partly|partially|,)\s*)*\b(allow|dismiss|dispose\s+of|dispose\s+off|remand|remit|accept|reject|"
    r"set\s+aside|quash|transfer)\b", re.I)
_COORD_ACTIVE_RE = re.compile(
    r"\band\s+(?:as\s+a\s+consequence\s+|consequently\s+|accordingly\s+|hence\s+|therefore\s+|thus\s+)?"
    r"(dismiss|allow|dispose\s+of|remand|remit)\s+(?=(?:the|this|these|both|all|it|present|instant)\b)", re.I)
_DEEM_RE = re.compile(r"\b(?:deems?|consider|considers|find|finds|think|thinks)\s+it\s+(?:fit|proper|appropriate|expedient|just)\s+"
                      r"(?:and\s+(?:proper|appropriate)\s+)?to\s+(transfer|remit|remand|allow|dismiss|dispose\s+of|quash|set\s+aside)\b", re.I)
_PARTY_STMT_RE = re.compile(r"\b(?:counsel|Counsel|Advocate|advocate|A\.?S\.?G\.?I?|C\.?G\.?S\.?C|petitioners?|appellants?|respondents?|"
                            r"applicants?)\b[^.;]{0,250}?\b(?:submits?|submitted|states?|stated|prays?|prayed|requests?|requested|"
                            r"contends?|contended|urges?|urged|seeks?|sought|agrees?|agreed|concedes?|conceded|fairly\s+states)\b")
_ADOPT_RE = re.compile(r"^\W*(?:\d+\s*\.\s*)?(?:ordered\s+accordingly|order\s+accordingly|prayer\s+(?:is\s+)?(?:accepted|allowed|granted)|"
                       r"request\s+(?:is\s+)?(?:accepted|acceded\s+to|allowed)|(?:dismissed|disposed\s+of|allowed)\s+as\s+prayed(?:\s+for)?)\b", re.I)
_INTRANS_RE = re.compile(r"\b(succeeds?|fails?)\b", re.I)

_CLAUSE_BOUND_RE = re.compile(r";|:|\b[Ww]hereas\b|\b[Ww]hile\b|,\s*and\b|\band\s+the\b|\band\s+that\b|"
                              r"\band\s+(?=(?:[A-Z][A-Za-z.()]*\s+){0,3}Nos?\b)|\band\s+(?=(?:these|this|all|both|such|its|his|her|their)\b)|"
                              r"\band\s+that\b|\b[Bb]ut\b|\b[Hh]owever\b|"
                              r"\bwith\s+the\s+result\s+that\b")
_COND_RE = re.compile(r"\b(if|in\s+case|failing\s+which|in\s+the\s+event|otherwise|unless|whether|lest|till|until|"
                      r"would\s+be|shall\s+be\s+deemed)\b", re.I)

# subject noun classes, scanned left to right; the first match decides
_NOUN_RES = [
    ("misc", re.compile(r"\b(applications?|appl\.?|i\.\s?a\.?(?=\s*(?:no|\d))|ia(?=\s*(?:no|\d))|c\.?\s?m\.?(?=\s*(?:appl|no|\d|\(|$))|"
                        r"crl\.?\s?m\.?\s?a\.?|m\.\s?a\.(?=\s*(?:no|\d))|ma(?=\s*(?:no\.?|\d))|miscellaneous|misc\.?|interlocutory|exemption|stay|"
                        r"condonation|delay|impleadment|caveat|interim|vacate|amendment|prayers?|requests?|costs?|"
                        r"objections?|contentions?|submissions?|pleas?|claims?|grounds?|issues?|questions?)\b", re.I)),
    ("lower_proc", re.compile(r"\b(o\.\s?a\.?|oa|original\s+applications?|t\.\s?a\.?|ta(?=\s*no)|complaints?|f\.?i\.?r\.?|"
                              r"suits?|court[\s-]+martial|g\.?c\.?m\.?|s\.?c\.?m\.?|d\.?c\.?m\.?|trial|inquiry|enquiry)\b", re.I)),
    ("lower_decision", re.compile(r"\b(impugned|orders?|judgments?|awards?|sentences?|convictions?|findings?|punishments?|"
                                  r"decisions?|proceedings|penalty|penalties|charge[-\s]?sheets?|notices?|communications?|"
                                  r"verdicts?|show\s+cause)\b", re.I)),
    ("main", re.compile(r"\b(appeals?|petitions?|writs?|w\.?\s?p\.?(?=\s*[\(\s\d]|\s*no)|c\.?w\.?p\.?|l\.?p\.?a\.?|s\.?l\.?p\.?|"
                        r"c\.?a\.?(?=\s*nos?\.?\s*\d)|crl\.?\s?a\.?|t\.?c\.?(?=\s*\()|transferred\s+cases?|revisions?|references?|"
                        r"cases?|matters?|contempt\s+(?:petitions?|cases?|appeals?)|reviews?|rule|lis|cwp|owp|lpa|slp|spla)\b", re.I)),
    ("pronoun", re.compile(r"^\s*(?:\(?[ivx]+\)|\(?[a-z]\)|\d+\.)?\s*(it|they|(?:the\s+)?same|both|all|all\s+of\s+them|these|"
                           r"this|which|(?:the\s+)?said)\s*$", re.I)),
]


_ALONG_WITH_RE = re.compile(r"[,\s]*\b(?:along\s*with|together\s+with|as\s+also|with)\s+(?:all\s+)?(?:the\s+)?(?:pending|connected|"
                            r"interim|miscellaneous|accompanying)?\s*(?:applications?|application\(s\)|C\.?M\.?s?|C\.?M\.?\s*APPL\S*|I\.?A\.?s?|"
                            r"misc\.?\s+applications?)\b[^,;]*,?", re.I)


def classify_subject(subj):
    s = _ALONG_WITH_RE.sub(" ", subj).strip()   # v3: 'The said writ petitions, along with all pending applications
    if "," in s:
        # v3: the comma-separated chunk nearest to the verb that names something decides
        # ('In view of our order ... No.242 of 2012, this appeal, filed by the appellant, also fails')
        for chunk in reversed(s.split(",")):
            r = _classify_subject(chunk)
            if r[0] not in ("unknown", "elided"):
                return r
    return _classify_subject(s)


def _classify_subject(subj):
    s = subj.strip()
    s2 = re.sub(r"^\s*(?:\(?[ivxlc]+\)|\(?[a-z]\)|[A-Z]\.|\d+\s*\.)\s*", "", s)
    if not re.search(r"[A-Za-z]{2,}", s2):
        return "elided", None
    best = None
    for cls, rx in _NOUN_RES:
        m = rx.search(s2)
        if m and (best is None or m.start() < best[1]):
            best = (cls, m.start())
    if best is None:
        return "unknown", None
    return best


_EXTENT_AFTER_RE = re.compile(r"\s*(?:\S+\s+){0,4}?(?:only\s+)?(?:to|in)\s+(?:the|that|this|such|a)?\s*(?:[a-z]+\s+){0,2}extent\b", re.I)
_EXTENT_BEFORE_RE = re.compile(r"\b(?:to|in)\s+(?:the|that|this|such)\s+(?:[a-z]+\s+){0,2}extent\b|\binsofar\s+as\b|\bin\s+so\s+far\s+as\b", re.I)


def verb_class(v, ctx_after):
    v = re.sub(r"\s+", " ", v.lower())
    after = ctx_after.lower()
    if v in ("withdrawn",) or re.match(r"\s*(?:as\s+)?(?:having\s+been\s+)?(?:withdrawn|not\s+pressed)", after) and \
            v in ("dismissed", "disposed of", "disposed", "closed", "dismiss", "dispose of"):
        return "dismissed_as_withdrawn"
    if v in ("allowed", "accepted") and re.match(r"\s*to\s+(be\s+)?withdraw", after):
        return "dismissed_as_withdrawn"
    if re.match(r"\s*(?:as\s+|being\s+)?(?:having\s+(?:been\s+)?(?:become|rendered)\s+|rendered\s+|become\s+)?infructuous", after) and \
            v in ("dismissed", "disposed of", "disposed", "closed", "dismiss", "dispose of"):
        return "dismissed_as_infructuous"
    if v in ("partly allowed", "partially allowed", "allowed in part", "allowed partly", "partly accepted",
             "accepted in part"):
        return "partly_allowed"
    if v in ("allowed", "accepted", "allow", "accept", "made absolute", "succeeds", "succeed"):
        if re.match(r"\s*(?:only\s+)?(?:partly|partially|in\s+part|to\s+(?:a\s+)?limited\s+extent)", after):
            return "partly_allowed"
        if _EXTENT_AFTER_RE.match(after):
            return "partly_allowed_extent"   # v3: 'allowed to the (above|aforesaid|limited) extent', 'to that extent'
        if re.match(r"\s*to\s+(?!the\s+extent|a\s+limited)", after):
            return None   # 'allowed to join/continue' etc.
        return "allowed"
    if v in ("dismissed", "rejected", "dismiss", "reject", "fails", "fail", "discharged"):
        if re.match(r"\s*(?:\w+\s+){0,2}?(?:except|save|but\s+only)\s+(?:to\s+the\s+extent|as\s+(?:indicated|mentioned|stated))", after):
            return "extent_qualified"
        return "dismissed"
    if v in ("disposed of", "disposed off", "disposed", "dispose of", "dispose off", "closed", "consigned"):
        if re.match(r"\s*(?:of\s+)?as\s+allowed\b", after):
            return "allowed"
        if re.match(r"\s*(?:of\s+)?as\s+dismissed\b", after):
            return "dismissed"
        return "disposed_of_with_directions"
    if v in ("remanded", "remitted", "remand", "remit"):
        return "remanded"
    if v in ("transferred", "transfer", "transmitted"):
        if re.match(r"\s*(?:back\s+)?to\b", after) or True:
            return "transferred"
    if v in ("set aside", "set-aside", "setaside", "set - aside", "quashed", "quash"):
        return "set_aside"
    return None


def _aux_chain(text, vstart, cstart):
    """Words immediately before the verb that belong to the auxiliary chain."""
    seg = text[cstart:vstart]
    words = re.findall(r"[A-Za-z]+|,", seg)
    chain = []
    for w in reversed(words):
        lw = w.lower()
        if lw == "," or lw in _AUX:
            chain.append(lw)
        else:
            break
    chain.reverse()
    k = len(seg)
    # position where the chain begins (to cut the subject)
    for w in reversed(words[len(words) - len(chain):] if chain else []):
        k = seg.rfind(w, 0, k)
    return [c for c in chain if c != ","], cstart + (k if chain else len(seg))


def parse_dispositions(text, s, e):
    """Disposition clauses in sentence text[s:e]. Returns list of dicts."""
    sent = text[s:e]
    out = []
    bounds = [0] + [m.end() for m in _CLAUSE_BOUND_RE.finditer(sent)]

    def clause_start(rel):
        i = bisect.bisect_right(bounds, rel) - 1
        return bounds[max(i, 0)]

    def clause_end(rel):
        i = bisect.bisect_right(bounds, rel)
        nb = [b for b in bounds if b > rel]
        return (nb[0] if nb else len(sent))

    found_spans = []
    # passive / standalone
    for m in _PASSIVE_VERB_RE.finditer(sent):
        v = m.group(1)
        if re.match(r"\s*(?:\([A-Za-z.]+\)\s*)?(?:cases?|petitions?|applications?)\b", sent[m.end():m.end() + 30], re.I):
            continue
        if v.lower() == "withdrawn" and re.search(r"(?:dismissed|disposed\s+of+|closed|rejected)\s+as\s+(?:having\s+been\s+)?$",
                                                  sent[max(0, m.start() - 40):m.start()], re.I):
            continue   # second half of 'dismissed as withdrawn' (already parsed with its verb)
        cs = clause_start(m.start())
        # v3: 'The present petition and all pending applications are disposed of' is one coordinated subject
        if cs > 0 and re.match(r"\s*(?:all\s+)?(?:the\s+)?(?:pending|connected|interim|miscellaneous|accompanying)\s+(?:civil\s+)?"
                               r"(?:misc\w*\s+)?applications?|\s*(?:all\s+)?(?:the\s+)?applications?\b", sent[cs:m.start()], re.I) and \
                re.search(r"\band\s*$", sent[:cs]):
            cs = clause_start(max(0, cs - 5))
        chain, subj_end = _aux_chain(sent, m.start(), cs)
        subj = sent[cs:subj_end - 0] if chain else sent[cs:m.start()]
        after = sent[m.end():m.end() + 60]
        cls = verb_class(v, after)
        if cls is None:
            continue
        stripped_sent = re.sub(r"^[\s\d.()ivx]*", "", sent).strip()
        standalone = stripped_sent.lower().startswith(re.sub(r"\s+", " ", v.lower())[:6]) and \
            not re.search(r"[A-Za-z]{2,}", re.sub(r"^[\s\d.()ivx]*", "", sent[:m.start()]))
        if not chain and not standalone:
            # elliptical coordination 'X is quashed and OA No. 1/2020 dismissed' -> only with a case number
            if not find_case_numbers(subj):
                continue
            chain = ["(ellipsis)"]
        tense = "present"
        if chain[-2:] in (["will", "stand"], ["will", "be"]) and not ({"not", "would", "may", "can", "cannot"} & set(chain)):
            chain = ["shall"] + chain[-1:]   # v3: operative 'will stand dismissed' / 'will be disposed of'
        if any(c in _PAST for c in chain):
            tense = "past"
        elif any(c in _MODAL_COND for c in chain):
            tense = "conditional"
        elif any(c in _MODAL_WEAK for c in chain) and not ("shall" in chain):
            tense = "weak"
        elif chain and chain[0] == "be" and "shall" not in chain:
            tense = "weak"   # subjunctive 'that the petition be transferred'
        pre_sent = sent[:m.start()]
        if _PARTY_STMT_RE.search(pre_sent):
            tense = "party_statement"
        if cls == "allowed" and _EXTENT_BEFORE_RE.search(pre_sent[-160:]):
            cls = "partly_allowed_extent"   # 'To the aforesaid extent, the petition is allowed'
        if cls == "allowed" and re.search(r"\b(?:partly|partially)\s*$", pre_sent):
            cls = "partly_allowed"
        out.append({"verb": v, "cls": cls, "subject": subj, "tense": tense, "rel": m.start(),
                    "standalone": standalone, "form": "passive", "clause": sent[cs:clause_end(m.end())]})
        found_spans.append((m.start(), m.end()))
    for m in _ACTIVE_RE.finditer(sent):
        v = m.group(1)
        obj_end = clause_end(m.end())
        obj = sent[m.end():min(obj_end, m.end() + 160)]
        obj = re.split(r",|;|\band\s+(?=[a-z]+\s+(?:the|this|that|his|her|its|their)\b)", obj)[0]   # v3: object of THIS verb only
        cls = verb_class(v, obj)
        if v.lower() in ("allow", "accept") and re.match(r"\s*(?:the\s+)?(?:learned\s+)?(?:petitioners?|appellants?|applicants?|"
                                                       r"respondents?|him|her|them|counsel|parties)\b", obj, re.I):
            cls = "dismissed_as_withdrawn" if re.search(r"\bwithdraw", obj, re.I) else None
        if cls is None:
            continue
        pre = sent[clause_start(m.start()):m.start()]
        tense = "present"
        between = sent[m.start():m.start(1)].lower()
        if cls == "allowed" and re.search(r"partly|partially", between):
            cls = "partly_allowed"
        if cls == "allowed" and (_EXTENT_AFTER_RE.match(obj) or re.search(r"\bto\s+(?:the|that)\s+(?:[a-z]+\s+){0,2}extent\b|"
                                                                           r"\bin\s+part\b", obj, re.I)):
            cls = "partly_allowed_extent"
        if _PARTY_STMT_RE.search(sent[:m.start()]):
            tense = "party_statement"
        if re.search(r"\bwould\b", between) or _COND_RE.search(pre):
            tense = "conditional"
        out.append({"verb": v, "cls": cls, "subject": obj, "tense": tense, "rel": m.start(1), "standalone": False,
                    "form": "active", "clause": sent[clause_start(m.start()):obj_end]})
    for m in _COORD_ACTIVE_RE.finditer(sent):
        # v3: 'we uphold the judgment ... and as a consequence dismiss this petition'
        if any(abs(x["rel"] - m.start(1)) < 3 for x in out):
            continue
        we = list(re.finditer(r"\b(?:we|this\s+court)\b", sent[:m.start()], re.I))
        if we:
            between = sent[we[-1].end():m.start()]
        else:
            # the sentence may have been split after an abbreviation ('the GP. Secretary'): look back 300 chars,
            # ignoring periods after short capitalised tokens
            back = re.sub(r"\b([A-Z][A-Za-z]{0,3})\.", r"\1 ", text[max(0, s - 300):s] + sent[:m.start()])
            mw = list(re.finditer(r"\b(?:we|this\s+court)\b[^.;:?!]*$", back, re.I))
            if not mw:
                continue
            between = back[mw[-1].start() + 2:]
        if re.search(r"[;:]|\bthat\b|\bwhich\b|\bwho\b", between):
            continue
        v = m.group(1)
        obj_end = clause_end(m.end())
        obj = sent[m.end():min(obj_end, m.end() + 160)]
        obj = re.split(r",|;|\band\s+(?=[a-z]+\s+(?:the|this|that|his|her|its|their)\b)", obj)[0]
        cls = verb_class(v, obj)
        if cls is None:
            continue
        tense = "present"
        if re.search(r"\b(?:would|may|might|could|cannot|can|not|to|shall\s+not)\b", between, re.I) or \
                _COND_RE.search(sent[:m.start()]):
            tense = "conditional"
        if _PARTY_STMT_RE.search(sent[:m.start()]):
            tense = "party_statement"
        out.append({"verb": v, "cls": cls, "subject": obj, "tense": tense, "rel": m.start(1), "standalone": False,
                    "form": "coordinated_active", "clause": sent[m.start():obj_end]})
    for m in _DEEM_RE.finditer(sent):
        v = m.group(1)
        obj_end = clause_end(m.end())
        obj = sent[m.end():min(obj_end, m.end() + 160)]
        cls = verb_class(v, obj)
        if cls is None:
            continue
        out.append({"verb": v, "cls": cls, "subject": obj, "tense": "present", "rel": m.start(1), "standalone": False,
                    "form": "deem_proper", "clause": sent[clause_start(m.start()):obj_end]})
    for m in _INTRANS_RE.finditer(sent):
        cs = clause_start(m.start())
        subj = sent[cs:m.start()]
        c, _ = classify_subject(subj)
        if c not in ("main", "misc", "lower_proc", "pronoun"):
            continue
        pre_words = re.findall(r"[A-Za-z]+", subj.lower())[-3:]
        tense = "present"
        if any(w in ("would", "must", "may", "cannot", "will", "not", "to") for w in pre_words):
            tense = "conditional"
        cls = "allowed" if m.group(1).lower().startswith("succeed") else "dismissed"
        if cls == "allowed" and (re.search(r"\b(?:partly|partially)\s*$", subj, re.I) or
                                 re.match(r"\s*(?:only\s+)?(?:partly|partially|in\s+part)\b", sent[m.end():m.end() + 30], re.I)):
            cls = "partly_allowed"   # v3: 'the appeal partly succeeds'
        elif cls == "allowed" and _EXTENT_AFTER_RE.match(sent[m.end():m.end() + 60]):
            cls = "partly_allowed_extent"
        out.append({"verb": m.group(1), "cls": cls, "subject": subj, "tense": tense, "rel": m.start(),
                    "standalone": False, "form": "intransitive", "clause": sent[cs:clause_end(m.end())]})
    # v3: a closing quotation mark with no opening mark before it in the sentence quotes only what precedes it;
    # the court's own words after the closing mark are not quoted
    mq = re.search(r"^[^\u201c]*?\u201d", sent)
    close_rel = mq.end() if mq else -1
    ends_in_quote = bool(re.match(r"\s*[\u201d\"]", text[e:e + 3]))
    for d in out:
        d["pos"] = s + d["rel"]
        pre = re.sub(r"\bif\s+any\b|\bif\s+not\s+already\b", " ", text[s + clause_start(d["rel"]):d["pos"]], flags=re.I)
        d["conditional_context"] = bool(_COND_RE.search(pre))
        d["closes_quote"] = ends_in_quote or (close_rel >= 0 and d["rel"] < close_rel)
        d["sentence"] = (s, e)
    out.sort(key=lambda d: d["rel"])
    return out


_NOT_FINAL_RE = re.compile(
    r"(?:^\s*|[.;:]\s+|^\s*\d+\s*\.\s*)(?:List|Re-?\s?list|Re-?\s?notify|Renotify|Issue\s+notice|Put\s+up|Stand\s+over|"
    r"Adjourned|To\s+be\s+listed)\b|\b(?:be\s+(?:re-?)?listed|be\s+put\s+up|stands?\s+adjourned|is\s+adjourned|"
    r"next\s+date\s+of\s+hearing|till\s+the\s+next\s+date|part[-\s]heard)\b")
_OPERATIVE_CUE_RE = re.compile(
    r"\b(in\s+the\s+(?:final\s+)?result|for\s+(?:all\s+)?the\s+(?:foregoing|aforesaid|above|said|reasons)|for\s+(?:all\s+)?the(?:se)?\s+reasons|"
    r"for\s+the\s+reasons\s+(?:stated|recorded|given|aforesaid|mentioned)|in\s+view\s+of\s+(?:the\s+)?(?:above|aforesaid|foregoing|what\s+has|the\s+discussion|the\s+facts)|"
    r"in\s+the\s+light\s+of\s+(?:the\s+)?(?:above|aforesaid|foregoing)|resultantly|as\s+a\s+result|in\s+these\s+circumstances|"
    r"in\s+the\s+(?:facts\s+and\s+)?circumstances|consequently|we,?\s+therefore|accordingly|hence|thus|"
    r"we\s+pass\s+the\s+following\s+order|following\s+order|in\s+conclusion|to\s+sum\s+up|in\s+sum|"
    r"we\s+find\s+no\s+(?:merit|substance|ground|reason)|there\s+is\s+no\s+(?:merit|substance)|devoid\s+of\s+(?:any\s+)?merit|"
    r"we\s+are\s+not\s+inclined|no\s+ground\s+for\s+interference)\b", re.I)
_ORDER_HEADING_RE = re.compile(r"(?m)^[ \t]*(?:O\s*R\s*D\s*E\s*R|ORDER|FINAL\s+ORDER|CONCLUSION|RESULT)[ \t]*['.:]?[ \t]*$")
_JUDGMENT_START_RE = re.compile(
    r"(?m)^[ \t]*(?:J\s*U\s*D\s*G\s*M\s*E\s*N\s*T|JUDGMENT|COMMON\s+JUDGMENT|JUDGMENT\s*(?:&|AND)\s*ORDER|O\s*R\s*D\s*E\s*R|ORDER|"
    r"ORAL\s+JUDGMENT|COMMON\s+ORDER)[ \t]*[:.]?[ \t]*$|delivered\s+by\s*:?|The\s+Judgment\s+of\s+the\s+Court|"
    r"(?m:^[ \t]*[A-Z][A-Z. ]{3,60},\s*(?:C\.?J\.?|J\.?)\s*(?:\(\s*(?:ORAL|Oral)\s*\))?\s*[:.]?)|"
    r"(?m:^[ \t]*[A-Z][A-Z. ]{3,60}\.\s?J\.?[ \t]*\n?[ \t]*\(\s*(?:ORAL|Oral)\s*\))", re.I)
_SIG_RES = [
    re.compile(r"\(\s*[A-Z][A-Za-z.\s']{2,60}\)\s*(?:\(?[A-Z][A-Za-z.\s']{2,60}\)?\s*)?(?:Acting\s+)?(?:Chief\s+)?(?:JUDGE|Judge|J\.)"),
    re.compile(r"(?m)^[ \t]*\.{3}[ \t.]*,?[ \t]*(?:C\.?J\.?I?\.?|J\.?)[ \t]*$"),
    re.compile(r"(?m)^[ \t]*\[?\(?[A-Z][A-Z.']+(?:\s+[A-Z][A-Z.']*){0,5}\)?\]?\s*,\s*(?:C\.?\s?J\.?|A\.?C\.?J\.?|J\.?)\s*$"),
    re.compile(r"(?m)^[ \t]*(?:JUDGE|Judge)[ \t]*$"),
    re.compile(r"(?m)^[ \t]*(?:NEW\s+DELHI|New\s+Delhi|CHANDIGARH|Chandigarh|JAMMU|Jammu|SRINAGAR|Srinagar|ALLAHABAD|Allahabad|"
               r"LUCKNOW|Lucknow)[ \t]*[;,.:]?[ \t]*(?:\n|$)"),
]
_DOC_HEADER_RE = re.compile(r"^[ \t]*\*?[ \t]*(?:IN[ \t]+THE[ \t]+(?:HIGH[ \t]+COURT|SUPREME[ \t]+COURT)|HIGH[ \t]+COURT[ \t]+OF[ \t]+[A-Z]|"
                            r"REPORTABLE|SUPREME[ \t]+COURT[ \t]+OF[ \t]+INDIA)", re.M)
_CAUSE_TITLE_RE = re.compile(r"\b(?:versus|Versus|VERSUS|Vs\.?|VS\.?|V/[Ss]|Petitioners?|PETITIONERS?|Appellants?|APPELLANTS?|"
                             r"Respondents?|RESPONDENTS?)\b")


_SCR_CASE_HEAD_RE = re.compile(r"\bv\.\s[\s\S]{0,250}?\(\s*(?:Civil|Criminal|Writ|Special|Transferred|Original|Review|Contempt)"
                               r"(?:[^()]|\([^()]*\)){0,120}?No(?:[^()]|\([^()]*\)){0,80}\)\s*"
                               r"(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+\d{1,2},?\s+"
                               r"(?:19|20)\d{2}", re.I)


def is_doc_header(mt, pos, span=900):
    """A court header followed by a cause title, or an S.C.R. case head ('X v. Y (Civil Appeal No. ..) MONTH DD, YYYY')."""
    m = _DOC_HEADER_RE.search(mt, pos, pos + span)
    if m and _CAUSE_TITLE_RE.search(mt, m.end(), m.end() + 1500):
        return True
    return bool(_SCR_CASE_HEAD_RE.search(mt, pos, pos + min(span, 700)))
_SCR_RE = re.compile(r"S\.\s?C\.\s?R\.|SUPREME\s+COURT\s+REPORTS|\bHELD\s*:|Headnote|Case\s+Law\s+Reference")
_EDITORIAL_TAIL_RE = re.compile(
    r"(?m)^[ \t]*(?:Result\s+of\s+the\s+case\s*:.*|Headnotes?\s+prepared\s+by.*|"
    r"(?:(?:Civil|Criminal|Writ|Special\s+Leave|Transferred|Review|Contempt)\s+)?(?:Appeals?|Petitions?|Cases?|Writ\s+Petitions?|"
    r"S\.?L\.?P\.?s?|References?|Transferred\s+Cases?)(?:\s*\([A-Za-z.]+\))?(?:\s+Nos?\.?\s*[\d,\s&A-Za-z-]{1,60}?of\s+\d{4})?\s+"
    r"(?:(?:are|is|partly|partially)\s+)?"
    r"(?:allowed|dismissed|disposed\s+of|partly\s+allowed|allowed\s+in\s+part|remitted|answered|dismis\S*)[^\n]{0,60})$")


_DATE_NEAR_RE = re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-](?:19|20)\d{2}\b|\b(?:January|February|March|April|May|June|July|August|"
                           r"September|October|November|December|JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|"
                           r"OCTOBER|NOVEMBER|DECEMBER)\s+\d{1,2},?\s+(?:19|20)\d{2}|\b\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|"
                           r"March|April|May|June|July|August|September|October|November|December),?\s+(?:19|20)\d{2}")


def find_signatures(t):
    """Signature clusters (start, end, n_hits). Author lines ('NAME, J.' followed by the judgment) and place
    names inside quoted letters are not signatures: a 'NAME, J.' line or a place line counts only when
    corroborated by another signature mark, a date close after it, or the end of the text."""
    hits = []
    for ti, rx in enumerate(_SIG_RES):
        for m in rx.finditer(t):
            hits.append((m.start(), m.end(), ti))
    hits.sort()
    n = len(t)
    kept = []
    for i, (s, e, ti) in enumerate(hits):
        others = [h for j, h in enumerate(hits) if j != i and abs(h[0] - s) <= 400 and h[2] not in (4,)]
        if ti == 4:
            if not others:
                continue
        elif ti == 2:
            near_end = len(t[e:].strip()) < 500
            if not (others or near_end or _DATE_NEAR_RE.search(t, e, min(n, e + 300))):
                continue
            if re.match(r"\s*(?:\(\s*ORAL\s*\))?\s*[:.]?\s*(?:1\s*\.\s|[A-Z][a-z]+\s+[a-z]|[A-Z][a-z]+\s*,)", t[e:e + 80]) or \
                    re.search(r"(?m)^[ \t]*1[ \t]*\.\s", t[e:e + 600]):
                continue   # author line: the judgment text (paragraph 1) follows
        kept.append((s, e))
    clusters = []
    for s, e in kept:
        if clusters and s - clusters[-1][1] <= 400:
            clusters[-1] = (clusters[-1][0], max(e, clusters[-1][1]), clusters[-1][2] + 1)
        else:
            clusters.append((s, e, 1))
    return clusters


# ------------------------------------------------------------------ host proceedings (v3)
_CANON = [
    (r"^(?:civilappeals?|cas?|civilappealnos?|civilappealno)$", "CA"),
    (r"^(?:criminalappeals?|crlas?|crlapp|cras?|criminalappealnos?)$", "CRLA"),
    (r"^(?:criminalappeal|crla|crlapp)\((s|db|sj)\)$", "CRLA(%s)"),
    (r"^(?:writpetition|writpetitions|wp|wps)\((c|civil)\)$", "WP(C)"),
    (r"^(?:writpetition|writpetitions|wp|wps)\((crl|criminal)\)$", "WP(CRL)"),
    (r"^(?:writpetition|writpetitions|wp|wps)$", "WP"),
    (r"^wpc$", "WP(C)"),
    (r"^(?:specialleavepetitions?|slps?)\((c|civil)\)$", "SLP(C)"),
    (r"^(?:specialleavepetitions?|slps?)\((crl|criminal)\)$", "SLP(CRL)"),
    (r"^(?:specialleavepetitions?|slps?)$", "SLP"),
    (r"^(?:transferredcases?|tcs?)\((c|civil)\)$", "TC(C)"),
    (r"^(?:transferredcases?|tcs?)$", "TC"),
    (r"^(?:specialappeals?|splas?)$", "SPLA"),
    (r"^(?:specialappeal)\((d|defective)\)$", "SPLA(D)"),
    (r"^(?:regularsecondappeals?|rsas?)$", "RSA"),
    (r"^(?:sa)$", "SA"),
    (r"^(?:lettersppatentappeals?|letterspatentappeals?|lpas?)$", "LPA"),
    (r"^(?:reviewpetitions?|rps?|reviewapplications?)$", "RP"),
    (r"^(?:civilwritpetitions?|cwps?|cwpnos?)$", "CWP"),
    (r"^(?:criminalwritpetitions?|crwps?|crlwps?)$", "CRWP"),
    (r"^(?:servicewritpetitions?|swps?)$", "SWP"),
    (r"^(?:otherwritpetitions?|owps?)$", "OWP"),
    (r"^(?:writa|writ\-?a|wria)$", "WRIT-A"),
    (r"^(?:writc|writ\-?c|wric)$", "WRIT-C"),
    (r"^(?:mattersunderarticle(?:227)?)$", "MATTERS-U/A-227"),
    (r"^(?:contemptpetitions?|contemptpetition\(c\)|cocp|conc|coc|contemptcases?)$", "CONT"),
]


_TYPE_KEY_RE = re.compile(
    r"(?<![A-Za-z])(civil\s+appeal|criminal\s+appeal|crl\.?\s*a(?:ppeal)?\.?(?:\s*\((?:s|db|sj)\))?|writ\s+petitions?(?:\s*\((?:civil|c|criminal|crl)\))?|"
    r"special\s+leave\s+petitions?(?:\s*\((?:civil|c|criminal|crl)\))?|s\.?\s*l\.?\s*p\.?(?:\s*\((?:civil|c|criminal|crl)\))?|"
    r"transferred\s+cases?(?:\s*\((?:civil|c)\))?|t\.?\s*c\.?\s*\((?:civil|c)\)|special\s+appeal(?:\s*\((?:d|defective)\))?|"
    r"regular\s+second\s+appeal|letters?\s+patent\s+appeal|l\.?\s*p\.?\s*a\.?|review\s+(?:petition|application)|r\.?\s*p\.?|"
    r"civil\s+writ\s+petition|c\.?\s*w\.?\s*p\.?|cr\.?\s*w\.?\s*p\.?|criminal\s+writ\s+petition|s\.?\s*w\.?\s*p\.?|o\.?\s*w\.?\s*p\.?|"
    r"writ\s*-\s*[ac]\b|writ\s+[ac]\b|matters\s+under\s+article\s+227|contempt\s+(?:petition|case)s?(?:\s*\((?:civil|c)\))?|"
    r"w\.?\s*p\.?\s*\((?:c|civil|crl|criminal|s)\)|w\.\s*p\.|wp|c\.\s*a\.|r\.\s*s\.\s*a\.|rsa)(?![A-Za-z])", re.I)


def canon_type(raw):
    """Normalised proceeding type for a printed case-type string ('Civil Appeal' -> CA, 'W.P.(C)' -> WP(C)).
    The right-most recognised type phrase in the string wins (cause-title noise before it is ignored)."""
    raw = raw or ""
    ms = list(_TYPE_KEY_RE.finditer(raw))
    cand = [raw]
    if ms:
        cand = [ms[-1].group(0)] + cand
    for c0 in cand:
        t = c0.lower()
        t = re.sub(r"\b(?:nos?|numbers?|in|the|of|and|with|d)\b\.?", " ", t) if c0 is raw else t
        t = re.sub(r"[^a-z()]", "", t)
        t = t.replace("()", "")
        for pat, out in _CANON:
            m = re.match(pat, t)
            if m:
                return out % m.group(1).upper() if "%s" in out else out
    t2 = re.sub(r"[^A-Za-z()\-]", "", raw.split()[-1] if raw.split() else "").upper()
    return t2[:20] or "CASE"


def norm_label(c, n=None):
    """'TYPE NUM/YEAR' for one number of a case-number dict."""
    n = min(c["nums"]) if n is None else n
    return "%s %d/%d" % (canon_type(c.get("type", "")), n, c["year"])


_NOT_HOST_BEFORE_RE = re.compile(
    r"(?:arising\s+(?:out\s+)?(?:of|from)|@|\bagainst\b|impugned|passed\s+in|(?:order|judgment)\s+dated|decided\s+on|dated\s+\d|"
    r"\bin\s+(?:the\s+)?(?:O\.?\s?A|T\.?\s?A|R\.?\s?A|M\.?\s?A|Original\s+Application|Transferred\s+Application|"
    r"Writ\s+Petition|W\.?\s?P|C\.?\s?W\.?\s?P|Civil\s+Writ|LPA|S\.?\s?W\.?\s?P|O\.?\s?W\.?\s?P|Crl|Criminal|Civil|case\s+of)|"
    r"High\s+Court\s+(?:of\s+[A-Za-z&\s]{3,40}\s+)?in|Tribunal\s+(?:[A-Za-z,\s]{0,40}\s+)?in|\bin\s+(?:CWP|SWP|OWP|WP|LPA)\b|"
    r"\bwith\s+reference\s+to|\bcited\b|\breported\s+in|(?:passed|rendered|delivered)\s+by\b|"
    r"(?-i:\bin)\s+(?:the\s+)?(?:Writ|Special\s+Appeal|Spl|First\s+Appeal|Second\s+Appeal|Review|Contempt|Transfer|Misc|"
    r"Matters|Application|Petition|Case|SLP|S\.?\s?L\.?\s?P|C\.?\s?A\b|Civil\s+Appeal|Criminal\s+Appeal))(?:(?!\bWITH\b|\bWith\b|\n[ \t]*with[ \t]*\n|\n[ \t]*\n)[^;]){0,70}$", re.I)
_FROM_MARK_RE = re.compile(r"\bFrom\s+the\b|\bArising\s+(?:out\s+)?(?:of|from)\b|\bAgainst\s+the\b|\b(?:Judgment|Order)\s+(?:and|&)\s+"
                           r"(?:Order|Judgment)\b|\bdated\b", re.I)
_WITH_MARK_RE = re.compile(r"\bWITH\b|\bWith\b|\n[ \t]*with[ \t]*\n|\n[ \t]*and\s+(?=Civil|Criminal|C\.A|Writ|SLP|Special|Transferred)|\bAND\b|\bAlong\s+with\b|\(\s*(?=(?:Civil|Criminal|Writ|Special|Transferred))")


def _after_from_marker(zt, pos):
    """True when the number follows a 'From the judgment ...'/'arising out of' marker with no 'WITH' in between
    (S.C.R. jurisdiction lines: 'Civil Appeal No. 1 of 1997. From the ... High Court in C.W.P. No. 2 of 1993. WITH ...')."""
    pre = zt[max(0, pos - 400):pos]
    fm = list(_FROM_MARK_RE.finditer(pre))
    if not fm:
        return False
    wm = [m for m in _WITH_MARK_RE.finditer(pre) if m.start() > fm[-1].start()]
    return not wm


_PARA1_RE = re.compile(r"(?m)^[ \t]*1[ \t]*\.[ \t]*(?:\n[ \t]*)?[A-Z][a-z]+\s")


def _host_numbers(mt, js, case_numbers_meta, scr, page2=None):
    """Host proceedings: crawler metadata case numbers plus main-proceeding numbers printed in the cause title.
    Numbers introduced as the source of the appeal ('arising out of', 'against', 'impugned', 'in O.A.') are not
    hosts; a bare number list after a typed number inherits its type ('WP(C) Nos. 233, ... of 2024 and 540 of 2025')."""
    hosts = meta_case_numbers(case_numbers_meta)
    for h in hosts:
        h["src"] = "meta"
    if scr:
        zone_end = 2500
        mh = _SCR_CASE_HEAD_RE.search(mt, 0, 9000)
        mj = re.search(r"(?:CIVIL|CRIMINAL|ORIGINAL)\s+[A-Z ]{0,16}JURISDICTION", mt[:min(len(mt), 80000)])
        extra = []
        if mh:
            extra.append((mh.start(), min(len(mt), mh.end() + 50)))
        if mj:
            je = min(len(mt), mj.start() + 700)
            mstop = re.search(r"for\s+the\s+(?:Appellant|Petitioner|Respondent)|The\s+Judgment\s+of\s+the\s+Court|delivered\s+by|"
                              r"(?m:^[ \t]*1\s*\.\s)", mt[mj.start():je])
            extra.append((mj.start(), mj.start() + mstop.start() if mstop else je))
        zones = [(0, zone_end)] + extra
    else:
        zone_end = js if 150 <= js <= 6000 else max(min(js, 6000), 1500)
        if 6000 < js <= 60000 and len(_CAUSE_TITLE_RE.findall(mt, 0, js)) >= 4 and \
                sum(1 for c in find_case_numbers(mt[:js]) if c["ptype"] not in ("misc", "lower", "", "other")) >= 4:
            zone_end = js   # long cause title of a batch (every connected matter listed before the judgment starts)
            mp = _PARA1_RE.search(mt, 200, js)
            if mp:
                zone_end = max(1500, mp.start())   # ... but never past the first paragraph of the judgment
        elif js < 150 and page2 is not None and 200 < page2 < zone_end:
            zone_end = page2
        zones = [(0, zone_end)]
    prev = None
    for z0, z1 in zones:
        zt = mt[z0:z1]
        for c in find_case_numbers(zt):
            pre = zt[max(0, c["pos"] - 90):c["pos"]]
            pt = c["ptype"]
            if pt in ("", "other") and prev is not None and re.match(r"^[\s,&]*(?:and|&|,)?[\s,&]*$", zt[prev[1]:c["pos"]] or " ") \
                    and c["pos"] - prev[1] <= 12:
                c["type"], c["ptype"] = prev[0]["type"], prev[0]["ptype"]
                pt = c["ptype"]
            prev = (c, c["pos"] + _case_span_len(zt, c["pos"]))
            if pt in ("misc", "lower", "", "other"):
                continue
            if _NOT_HOST_BEFORE_RE.search(pre) or _after_from_marker(zt, c["pos"]):
                continue
            c["src"] = "cause_title"
            hosts.append(c)
    # one host per (number, year)
    out, seen = [], set()
    for h in hosts:
        for n in sorted(h["nums"]):
            k = (n, h["year"])
            if k in seen:
                continue
            seen.add(k)
            hh = dict(h)
            hh["nums"] = {n}
            hh["label_norm"] = norm_label(h, n)
            out.append(hh)
    return out


def _match_host(c, hosts):
    for h in hosts:
        if h["year"] == c["year"] and (h["nums"] & c["nums"]):
            return h
    return None


def _case_span_len(s, pos):
    m = _CASENO_RE.match(s, pos)
    return (m.end() - pos) if m else 0


_PAREN_LONG_RE = re.compile(r"\([^()]{13,}\)")
_PARTY_RE = re.compile(r"(?:filed|preferred|instituted|moved)\s+(?:on\s+behalf\s+of|by)\s+(?:the\s+)?(.{3,60}?)(?=\s+(?:are|is|stand|stands|be|"
                       r"have|has|respectively|shall)\b|,|$)|\bof\s+the\s+(appellants?|respondents?|petitioners?|accused|Union\s+of\s+India|"
                       r"State|officer|applicant)s?\b", re.I)


def _heading_scope(mt, seg_start, pos):
    """Most recent short case-number heading line before pos (Delhi-style 'CM APPL. 123/2023 (exemption)')."""
    window = mt[max(seg_start, pos - 4000):pos]
    last = None
    for m in re.finditer(r"(?m)^[ \t]*([A-Z][A-Za-z.()\s&]{1,30}?\s*(?:Nos?\.?\s*)?\d{1,6}\s*(?:/|of)\s*(?:19|20)\d{2}[^\n]{0,60})$", window):
        line = m.group(1)
        if len(line) <= 110:
            last = line
    if not last:
        return None
    cs = find_case_numbers(last)
    return cs[0] if cs else None


_BLOCK_HEAD_RE = re.compile(r"(?m)^[ \t]*((?:[A-Z][A-Za-z.()&\s]{1,40}?)\s*(?:Nos?\.?\s*)?\d{1,6}(?:\s*[-/]\s*\d{1,6})?\s*(?:/|of|-)\s*(?:19|20)\d{2}[^\n]{0,50})[ \t]*\n(?=\s*1\s*\.\s)")


def block_headings(mt, s0, s1):
    """Case-number heading lines immediately followed by paragraph '1.' (a common order with separately
    numbered blocks per proceeding). Returns [(pos, case_number_dict)]."""
    out = []
    for m in _BLOCK_HEAD_RE.finditer(mt, s0, s1):
        cs = find_case_numbers(m.group(1))
        if cs and len(m.group(1)) <= 110:
            out.append((m.start(), cs[0]))
    return out


def _reduce(classes):
    C = set(classes)
    if not C:
        return None
    if C <= {"dismissed", "dismissed_as_withdrawn", "disposed_of_with_directions"} and "dismissed_as_withdrawn" in C:
        return "dismissed_as_withdrawn"
    if C <= {"dismissed", "dismissed_as_infructuous", "disposed_of_with_directions"} and "dismissed_as_infructuous" in C:
        return "dismissed_as_infructuous"
    if "partly_allowed" in C and C <= {"allowed", "partly_allowed", "disposed_of_with_directions", "remanded"}:
        return "partly_allowed"
    if "allowed" in C and C <= {"allowed", "disposed_of_with_directions", "remanded"}:
        return "allowed"
    if "dismissed" in C and C <= {"dismissed", "disposed_of_with_directions"}:
        return "dismissed"
    if "transferred" in C and C <= {"transferred", "disposed_of_with_directions"}:
        return "transferred"
    if "remanded" in C and C <= {"remanded", "disposed_of_with_directions"}:
        return "remanded"
    if C == {"disposed_of_with_directions"}:
        return "disposed_of_with_directions"
    return None


_WITHDRAW_CTX_RE = re.compile(r"\b(?:seeks?|sought|prays?|prayed|requests?|requested|permission|leave)\s+(?:of\s+this\s+(?:Court|Bench)\s+)?"
                              r"(?:for\s+)?(?:permission\s+|leave\s+)?(?:to\s+)?withdraw|\bwithdraw(?:s|n)?\s+the\s+(?:present\s+|instant\s+)?"
                              r"(?:writ\s+)?(?:petition|appeal)\b|\bnot\s+press(?:ing)?\s+the\s+(?:petition|appeal)", re.I)


def mask_running_headers(text, pidx):
    """Mask lines that open at least 3 pages (2 in files of up to 5 pages; and 30% of pages) with the same words:
    running headers such as (only where they open a page, so the same words elsewhere stay readable)
    'WP(C) No.3173/2023 along with connected matters' or 'CWP No. 13553 of 2009 -2-'. Offsets are preserved."""
    starts = pidx[0]
    if len(starts) < 3:
        return text
    count = {}
    for ps in starts:
        seen = set()
        for line in text[ps:ps + 400].splitlines()[1:6]:
            k = re.sub(r"\s+", " ", re.sub(r"\d{1,4}\s*$|^\s*-?\s*\d{1,4}\s*-?\s*", "", line)).strip()
            if len(k) >= 8 and k not in seen:
                seen.add(k)
                count[k] = count.get(k, 0) + 1
    need = 2 if len(starts) <= 5 else 3
    heads = set(k for k, c in count.items() if c >= need and c >= 0.3 * len(starts))
    if not heads:
        return text
    chars = list(text)
    for ps in starts[1:]:
        pos = ps
        for k_line, line in enumerate(text[ps:ps + 400].splitlines(True)[:6]):
            body = line.rstrip("\n")
            if k_line > 0:
                k = re.sub(r"\s+", " ", re.sub(r"\d{1,4}\s*$|^\s*-?\s*\d{1,4}\s*-?\s*", "", body)).strip()
                if k in heads:
                    for i in range(pos, pos + len(body)):
                        chars[i] = " "
            pos += len(line)
    return "".join(chars)


class Doc:
    def __init__(self, text, meta):
        self.text = text
        self.meta = meta
        self.pidx = page_index(text)
        self.mt = mask_page_markers(mask_running_headers(mask_boilerplate(text), self.pidx))
        self.qspans = []
        self.qstarts = []


def _segment_doc(d):
    mt = d.mt
    clusters = find_signatures(mt)
    segs = []
    cur = 0
    for s, e, k in clusters:
        segs.append([cur, s, e])
        cur = e
    # a page that opens with a court header starts a new document (composite files)
    starts, nums = d.pidx
    cuts = []
    for ps in starts[1:]:
        if is_doc_header(mt, ps, 700) and not any(abs(ps - c[0]) < 1500 or abs(ps - c[1]) < 1500 for c in clusters):
            cuts.append(ps)
    if cuts:
        bounds = sorted([(s, e) for s, e, k in clusters] + [(c, c) for c in cuts])
        segs, cur = [], 0
        for s, e in bounds:
            if s <= cur:
                continue
            segs.append([cur, s, e])
            cur = e
    rem = mt[cur:]
    after_cut = bool(cuts) and cur in cuts
    if len(re.sub(r"\s", "", rem)) > 1200 or not segs or (_ORDER_HEADING_RE.search(rem) and len(re.sub(r"\s", "", rem)) > 60) or \
            (after_cut and len(re.sub(r"\s", "", rem)) > 200):
        segs.append([cur, len(mt), len(mt)])
    elif segs:
        segs[-1][2] = len(mt)
    merged = []
    for sg in segs:
        if merged and len(re.sub(r"\s", "", mt[merged[-1][0]:merged[-1][1]])) < 600:
            merged[-1] = [merged[-1][0], sg[1], sg[2]]
        else:
            merged.append(sg)
    return merged


def _alpha_ratio(s):
    words = s.split()
    if not words:
        return 0.0
    good = len(re.findall(r"[A-Za-z]{3,}", s))
    return good / len(words)


def _new_res(s0, s1):
    return {"seg": (s0, s1), "status": "none", "rows": [], "reason": "", "excluded": {"quoted": 0, "misc": 0, "lower": 0,
            "past": 0, "conditional": 0}, "zone": None, "method_zone": "", "js": s0, "headnote": None, "tail": None,
            "signals": [], "chain": []}


_REF_BEFORE_NUM_RE = re.compile(r"(?:\b(?:order|judgment|judgement|decision|view)\b[^,;]{0,60}\b(?:in|of)\s+(?:the\s+)?"
                                r"(?:[.]?[A-Z][A-Za-z.()]*\s*){0,4}(?:Nos?\.?\s*)?$)|\b(?:as\s+in|similar\s+to|like|following)\s+[^,;]{0,40}$", re.I)


def _has_main_disposition(mt, a, b, qs, qst):
    for (x, y) in sentences(mt, a, b):
        for dd in parse_dispositions(mt, x, y):
            if dd["tense"] != "present" or dd["conditional_context"] or dd.get("closes_quote") or in_spans(qs, qst, dd["pos"]):
                continue
            if dd["cls"] in ("set_aside",):
                continue
            c = "elided" if dd["standalone"] else classify_subject(_PAREN_LONG_RE.sub(" ", dd["subject"]))[0]
            if c in ("main", "pronoun", "elided"):
                return True
    return False


def analyze_segment(d, seg, hosts, scr, is_first, section=False):
    mt = d.mt
    s0, s1 = seg[0], seg[1]
    res = _new_res(s0, s1)
    # judgment start / editorial headnote
    lim = s0 + min(max(int((s1 - s0) * 0.5), 3000), 80000)
    hs = s0
    if scr and is_first:
        mh = re.search(r"\bHELD\s*:|\bHeld\s*:", mt[s0:lim])
        if mh:
            hs = s0 + mh.end()
    js = s0
    mj = None
    for m in _JUDGMENT_START_RE.finditer(mt, hs, lim):
        mj = m
        break
    if mj:
        js = mj.start()
        if scr and is_first and js > s0:
            res["headnote"] = (s0, js)
    elif scr and is_first:
        mj2 = re.search(r"(?:CIVIL|CRIMINAL|ORIGINAL)\s+(?:APPELLATE\s+|ORIGINAL\s+)?JURISDICTION", mt[s0:lim])
        if mj2:
            js = s0 + mj2.start()
            res["headnote"] = (s0, js)
    res["js"] = js
    # editorial reporter's note at the end (S.C.R. renditions only)
    body_end = s1
    if scr:
        tail_from = max(js, s1 - 1500)
        mts = list(_EDITORIAL_TAIL_RE.finditer(mt, tail_from, s1))
        if mts:
            body_end = mts[0].start()
            prev_nl = mt.rfind("\n", js, max(js, body_end - 1))
            prev_line = mt[prev_nl + 1:body_end].strip() if prev_nl >= 0 else ""
            if prev_line and len(prev_line) < 60 and not re.search(r"[.;:,]\s*$", prev_line):
                body_end = prev_nl + 1
            res["tail"] = (body_end, s1)
    L = body_end - js
    if L <= 0 or not mt[js:body_end].strip():
        res["reason"] = "EMPTY_SEGMENT"
        return res
    qs, qst = d.qspans, d.qstarts
    chain = host_paragraphs(mt, js, body_end, qs, qst)
    res["chain"] = chain
    win_start = max(js, body_end - (max(3500, min(int(0.6 * L), 9000)) if section else max(3500, min(int(0.12 * L), 9000))))
    short = len(re.sub(r"\s", "", mt[js:body_end])) < 4000
    cue = None
    for m in _OPERATIVE_CUE_RE.finditer(mt, win_start, body_end):
        if in_spans(qs, qst, m.start()):
            continue
        cue = m
        break
    order_heads = [m for m in _ORDER_HEADING_RE.finditer(mt, win_start, body_end) if not in_spans(qs, qst, m.start())]
    if order_heads:
        cue = order_heads[-1]
    last_para = None
    if chain and chain[-1][0] >= win_start:
        last_para = chain[-1][0]
    if short:
        zs, method_zone = js, "short_order_whole_body"
    elif cue is not None:
        ls = mt.rfind("\n", js, cue.start()) + 1
        zs = max(js, ls)
        if last_para is not None and not order_heads:
            zs = min(zs, last_para)
        method_zone = "operative_cue" if not order_heads else "order_heading"
    elif last_para is not None and body_end - last_para < 1200:
        zs, method_zone = last_para, "final_paragraph_no_cue"
    else:
        res["status"] = "abstain"
        res["reason"] = "NO_OPERATIVE_CUE_IN_FINAL_PART"
        return res
    if chain and method_zone in ("operative_cue", "order_heading"):
        ppos = [p for p, _ in chain]
        k = bisect.bisect_right(ppos, zs) - 1
        steps = 0
        while k >= 1 and steps < 4:
            pa, pb = ppos[k - 1], ppos[k]
            if pa < js or not _has_main_disposition(mt, pa, pb, qs, qst):
                break
            zs = pa
            k -= 1
            steps += 1
        if steps:
            method_zone += ";extended_back_%d_paras" % steps
    res["zone"] = (zs, body_end)
    res["method_zone"] = method_zone
    if _alpha_ratio(mt[zs:body_end]) < 0.45:
        res["status"] = "abstain"
        res["reason"] = "GARBLED_TEXT_IN_OPERATIVE_PART"
        return res
    disps = []
    notfinal = False
    blocks = block_headings(mt, s0, body_end)
    bpos = [p for p, _ in blocks]
    if len(blocks) >= 2:
        # common order: each block is its own operative part; look at the whole body
        zs = min(zs, blocks[0][0])
        res["zone"] = (zs, body_end)
        res["method_zone"] = method_zone = method_zone + ";common_order_blocks"
    pending_party = []
    nf_sents = []
    for (a, b) in sentences(mt, zs, body_end):
        if pending_party and _ADOPT_RE.search(mt[a:b]):
            for pp in pending_party:
                pp["tense"] = "present"
                pp["adopted"] = True
            pending_party_adopt = pending_party
            pending_party = []
        else:
            pending_party_adopt = []
        for dd in pending_party_adopt + parse_dispositions(mt, a, b):
            if dd["tense"] == "party_statement":
                if not in_spans(qs, qst, dd["pos"]):
                    pending_party.append(dd)
                res["excluded"]["party_statement"] = res["excluded"].get("party_statement", 0) + 1
                continue
            if in_spans(qs, qst, dd["pos"]) or dd.get("closes_quote"):
                res["excluded"]["quoted"] += 1
                continue
            if dd["tense"] == "past":
                res["excluded"]["past"] += 1
                continue
            if dd["tense"] == "conditional" or dd["conditional_context"]:
                res["excluded"]["conditional"] += 1
                continue
            subj = _PAREN_LONG_RE.sub(" ", dd["subject"])
            if re.search(r"\b(?:except|save\s+(?:for|to)|other\s+than|barring)\b", mt[dd["sentence"][0]:dd["pos"]], re.I):
                res["status"] = "abstain"
                res["reason"] = "DISPOSITION_WITH_EXCEPTION_OR_CARVE_OUT"
                return res
            if dd["standalone"]:
                scls = "elided"
            else:
                scls, _ = classify_subject(subj)
            if scls == "elided":
                h = _heading_scope(mt, s0, dd["pos"])
                if h is not None and h["ptype"] == "misc":
                    res["excluded"]["misc"] += 1
                    continue
            host_types = set(h["ptype"] for h in hosts)
            if scls == "main" and host_types and not (host_types & {"wp", "petition", "other", "rp", "cont", "tc"}) and \
                    re.search(r"\bwrit\s+petitions?\b|\bW\.?\s?P\.?\s*\(", subj, re.I) and not find_case_numbers(subj):
                scls = "lower_proc"   # e.g. 'the writ petition filed by the respondent shall stand dismissed' in an appeal
            if scls == "main" and re.search(r"\bwrit\s+petitions?\b", subj, re.I) and \
                    re.search(r"(?:filed|preferred|instituted)\s+by\s+the\s+respondents?\b", subj, re.I):
                scls = "lower_proc"   # the respondent's writ petition is the proceeding below, not this appeal
            if scls == "misc":
                res["excluded"]["misc"] += 1
                continue
            if scls == "lower_proc":
                res["excluded"]["lower"] += 1
                continue
            if dd["cls"] == "set_aside":
                if scls in ("lower_decision", "main", "pronoun", "elided") and dd["tense"] == "present":
                    res["signals"].append(("set_aside", dd))   # v3: 'prays that ... be set aside' is not an order
                continue
            if scls == "lower_decision":
                if dd["cls"] == "remanded":
                    res["signals"].append(("remand", dd))
                else:
                    res["excluded"]["lower"] += 1
                continue
            if scls == "unknown":
                continue
            key, label = "ALL", ""
            # v3: numbers cited as the reason ('in view of our order passed in Criminal Appeal No. 242 of 2012, this
            # appeal also fails') are references, not the subject of the disposition
            nums = [c_ for c_ in find_case_numbers(subj) if not _REF_BEFORE_NUM_RE.search(subj[max(0, c_["pos"] - 90):c_["pos"]])]
            if not nums and len(blocks) >= 2:
                bi = bisect.bisect_right(bpos, dd["pos"]) - 1
                if bi >= 0:
                    nums = [blocks[bi][1]]
            multi = []
            for c_ in nums:
                if c_["ptype"] in ("misc", "lower"):
                    continue
                for n_ in sorted(c_["nums"]):
                    h_ = _match_host({"nums": {n_}, "year": c_["year"]}, hosts)
                    if h_ is not None and h_ not in multi:
                        multi.append(h_)
            if len(multi) >= 2:
                # v3: one disposition naming several host proceedings ('W.P.(C) 1/2025, W.P.(C) 2/2025 ... stand disposed of')
                if dd["cls"] == "remanded":
                    res["signals"].append(("remand", dd))
                for h_ in multi:
                    d2 = dict(dd)
                    d2["host"] = h_
                    d2["key"], d2["label"] = "N:%d:%d" % (min(h_["nums"]), h_["year"]), h_["label_norm"]
                    disps.append(d2)
                continue
            if nums:
                c = nums[0]
                h = _match_host(c, hosts)
                if h is not None:
                    key, label = "N:%s:%d" % (min(h["nums"] & c["nums"]), c["year"]), c["label"]
                    dd["host"] = h
                elif c["ptype"] == "misc":
                    res["excluded"]["misc"] += 1
                    continue
                elif c["ptype"] == "lower":
                    res["excluded"]["lower"] += 1
                    continue
                else:
                    key, label = "N:%s:%d" % (min(c["nums"]) if c["nums"] else 0, c["year"]), c["label"]
                    dd["case"] = c
            else:
                pm = _PARTY_RE.search(subj)
                if pm:
                    who = squash(pm.group(1) or pm.group(2), 60)
                    key, label = "P:" + who.lower(), "proceedings by/of " + who
            if dd["cls"] == "remanded":
                res["signals"].append(("remand", dd))
            dd["key"], dd["label"] = key, label
            disps.append(dd)
        if _NOT_FINAL_RE.search(mt[a:b]) and not in_spans(qs, qst, a):
            notfinal = True
            nf_sents.append((a, b))
    if not disps:
        sa = [x for t, x in res["signals"] if t == "set_aside"]
        rm = [x for t, x in res["signals"] if t == "remand"]
        sa_text = " ".join(mt[x["sentence"][0]:x["sentence"][1]] for x in sa)
        if sa and rm:
            res["status"] = "final"
            res["rows"] = [("ALL", "", "set_aside_and_remanded", rm[-1], "set_aside_plus_remand")]
        elif rm:
            res["status"] = "final"
            res["rows"] = [("ALL", "", "remanded", rm[-1], "remand_only")]
        elif sa and re.search(r"impugned|(?:order|judgment|judgement|award|decision)s?\s+(?:dated\s+[\d.\-/]+\s+)?(?:passed\s+)?(?:of|by)\s+the\s+"
                              r"(?:learned\s+)?(?:Armed\s+Forces\s+)?(?:Tribunal|AFT|High\s+Court|Single\s+Judge|Division\s+Bench)",
                              sa_text, re.I) and not re.search(r"to\s+the\s+extent|partly|partially|modif|insofar|in\s+so\s+far", sa_text, re.I):
            res["status"] = "final"
            res["rows"] = [("ALL", "", "allowed", sa[-1], "inferred_from_set_aside_of_impugned_decision")]
        elif notfinal:
            # v3: a listing direction that names case numbers applies to those proceedings only
            named = [c for a_, b_ in nf_sents for c in find_case_numbers(mt[a_:b_]) if c["ptype"] not in ("misc", "lower")]
            if named:
                rows_nf = []
                for c in named:
                    h = _match_host(c, hosts)
                    if h is None:
                        res["status"] = "abstain"
                        res["reason"] = "NOT_FINAL_DIRECTION_FOR_A_CASE_NOT_MAPPED_TO_A_HOST:" + norm_label(c)
                        return res
                    a_, b_ = next((x for x in nf_sents if c["label"] in squash(mt[x[0]:x[1]]) or True), nf_sents[-1])
                    ev = {"sentence": (a_, b_), "pos": a_, "host": h, "subject": mt[a_:b_]}
                    rows_nf.append(("N:%d:%d" % (min(h["nums"] & c["nums"]), c["year"]), c["label"], "not_final", ev,
                                    "listing_direction_names_this_case"))
                res["status"] = "not_final"
                res["rows"] = rows_nf
                return res
            ev = {"sentence": nf_sents[-1], "pos": nf_sents[-1][0], "subject": ""} if nf_sents else None
            res["status"] = "not_final"
            res["rows"] = [("ALL", "", "not_final", ev, "listing_or_adjournment_cue")]
        else:
            res["status"] = "none"
            ex = res["excluded"]
            if ex["misc"] and not (ex["quoted"] or ex["lower"]):
                res["reason"] = "ONLY_MISC_APPLICATION_DISPOSAL_FOUND"
            elif ex["quoted"]:
                res["reason"] = "ONLY_QUOTED_DISPOSITION_LANGUAGE_FOUND"
            elif ex["lower"]:
                res["reason"] = "ONLY_LOWER_FORUM_DISPOSITION_FOUND"
            elif ex["conditional"] or ex["past"]:
                res["reason"] = "ONLY_PAST_OR_CONDITIONAL_DISPOSITION_FOUND"
            else:
                res["reason"] = "NO_DISPOSITION_IN_OPERATIVE_PART"
        return res
    if any(x["tense"] == "present" for x in disps):
        disps = [x for x in disps if x["tense"] == "present"]
    keys = {}
    for dd in disps:
        keys.setdefault(dd["key"], []).append(dd)
    has_sa = any(t == "set_aside" for t, _ in res["signals"])
    outk = {}
    for k, lst in keys.items():
        strong = [x for x in lst if x["tense"] == "present"]
        use = strong or lst
        for x in use:
            if x["cls"] == "partly_allowed_extent":
                x["cls"], x["extent"] = "partly_allowed", True
        if any(x["cls"] == "extent_qualified" for x in use):
            res["status"] = "abstain"
            res["reason"] = "EXTENT_QUALIFIED_ALLOWANCE_ALLOWED_OR_PARTLY_ALLOWED_UNDETERMINED"
            return res
        o = _reduce([x["cls"] for x in use])
        if o == "remanded" and has_sa:
            o = "set_aside_and_remanded"
        if o is None:
            res["status"] = "abstain"
            res["reason"] = ("CONFLICTING_DISPOSITIONS_WITHOUT_PROCEEDING_MAPPING" if k == "ALL"
                             else "CONFLICTING_DISPOSITIONS_FOR_ONE_PROCEEDING")
            res["conflict"] = sorted(set(x["cls"] for x in use))
            return res
        ev = [x for x in use if x["cls"] == o] or use
        note = "" if strong else "modal_only"
        if ev[-1].get("adopted"):
            note = "party_prayer_adopted_by_ordered_accordingly"
        ev_txt = mt[ev[-1]["sentence"][0]:ev[-1]["sentence"][1]]
        if o == "dismissed" and not re.search(r"non[-\s]?prosecution|default|merit|limine|maintainable", ev_txt, re.I) and \
                _WITHDRAW_CTX_RE.search(mt[zs:body_end]) and \
                not in_spans(qs, qst, _WITHDRAW_CTX_RE.search(mt[zs:body_end]).start() + zs):
            o, note = "dismissed_as_withdrawn", "withdrawal_sought_in_operative_part"
        outk[k] = (o, ev[-1], note)
    res["status"] = "final"
    res["rows"] = [(k, keys[k][-1]["label"], v[0], v[1], v[2]) for k, v in sorted(outk.items(), key=lambda kv: kv[1][1]["pos"])]
    return res


# ------------------------------------------------------------------ v3: batch sections
_SECTION_HEAD_RE = re.compile(
    r"(?m)^[ \t]*(?:\(?\d{1,3}[ \t]*[.)][ \t]*)?((?:[A-Z][A-Za-z.()&/ \t-]{0,40}?)[ \t]*(?:Nos?\.?[ \t]*)?\d{1,6}[ \t]*(?:/|[Oo][Ff]|-)[ \t]*(?:19|20)\d{2})"
    r"[ \t]*(?:\([^)\n]{0,40}\))?[ \t]*(?:(?:&|and|with)\b[^\n]{0,90})?[ \t]*[:.\-]?[ \t]*$")


def find_sections(d, js, s1, hosts):
    """Per-proceeding sections of a batch judgment: heading lines that consist of a HOST case number (optionally
    numbered '25.'), after the judgment start. Returns [(start, end, host, unsafe_reason)] or [].
    A jump in the printed serial numbers ('25.' then '27.') marks the section before the jump unsafe, because a
    heading may have been missed and its disposition would be attributed to the wrong proceeding."""
    mt = d.mt
    if len(hosts) < 2:
        return []
    found = {}
    for m in _SECTION_HEAD_RE.finditer(mt, js, s1):
        cs = find_case_numbers(m.group(1))
        if not cs or cs[0]["ptype"] in ("misc", "lower", "", "other"):
            continue
        h = _match_host(cs[0], hosts)
        if h is None or h["label_norm"] in found:
            continue
        ms = re.match(r"[ \t]*\(?(\d{1,3})[ \t]*[.)]", mt[m.start():m.end()])
        found[h["label_norm"]] = (m.start(), h, int(ms.group(1)) if ms else None)
    heads = sorted(found.values(), key=lambda x: x[0])
    missing = [h for h in hosts if h["label_norm"] not in found]
    if heads and len(missing) == 1 and len(re.sub(r"\s", "", mt[js:heads[0][0]])) >= 800:
        # lead case discussed first without a heading, connected case(s) under their own headings
        heads = [(js, missing[0], None)] + heads
    if len(heads) < 2:
        return []
    serials = [x[2] for x in heads]
    use_serial = sum(1 for x in serials if x is not None) >= 0.8 * len(serials)
    secs = []
    for i, (a, h, sn) in enumerate(heads):
        e = heads[i + 1][0] if i + 1 < len(heads) else s1
        unsafe = ""
        if use_serial and i + 1 < len(heads):
            nx = heads[i + 1][2]
            if sn is None or nx is None or nx != sn + 1:
                unsafe = "SECTION_SERIAL_GAP_POSSIBLE_UNDETECTED_PROCEEDING"
        secs.append((a, e, h, unsafe))
    big = [x for x in secs if len(re.sub(r"\s", "", mt[x[0]:x[1]])) >= 800]
    if not big or len(big) < 0.5 * len(secs):
        return []
    return secs


# ------------------------------------------------------------------ v3: printed disposal and substantive result
_DIRECTIONS_RE = re.compile(
    r"\b(?:in\s+(?:the\s+)?(?:above|following|aforesaid|aforementioned|said|these|terms\s+of)|with\s+(?:the\s+)?(?:above|following|aforesaid|"
    r"said)?\s*(?:directions?|observations?|liberty)|with\s+liberty|in\s+terms\s+of|as\s+under|in\s+the\s+light\s+of|with\s+a\s+direction|"
    r"with\s+directions?|subject\s+to)\b", re.I)
_DIRECTIVE_RE = re.compile(r"\b(?:is|are|stand|be)\s+(?:hereby\s+)?directed\b|\bwe\s+(?:hereby\s+|have\s+)?direct(?:ed)?\b|\bby\s+directing\b|"
                           r"\bit\s+is\s+(?:hereby\s+)?directed\b|\bshall\s+(?!stand\b|also\s+stand\b|not\s+stand\b)[a-z]+|\bliberty\b|"
                           r"\bopen\s+to\s+the\s+(?:petitioner|appellant|respondent)|\b(?:is|stands?)\s+modified\b", re.I)
_REMAND_RE = re.compile(
    r"\b(?:remand\w*|remit(?:s|ted|ting)?|sen[dt]\s+back|restored?\s+to\s+(?:the\s+)?(?:file|board)|relegat\w*)\b[^.;]{0,120}?"
    r"\b(?:to\s+the\s+|before\s+the\s+)(?:learned\s+)?(?:AFT|Armed\s+Forces|Tribunal|High\s+Court|Single\s+Judge|authorit|competent|"
    r"respondent|appellate|trial|disciplinary|Board|Court|concerned|Commission|Controller|PCDA|Government|Union)|"
    r"\bfor\s+(?:fresh|de\s+novo)\s+(?:decision|consideration|adjudication|hearing|determination)|\bfor\s+reconsideration\b|"
    r"\b(?:decide|consider|adjudicate|examine|hear)\s+(?:the\s+(?:matter|case|claim|issue|application|O\.?A\.?|appeal|petition)\s+)?"
    r"(?:afresh|de\s+novo)|\bpass\s+(?:a\s+)?(?:fresh|afresh)\s+(?:speaking\s+|reasoned\s+)?order|\b(?:remanded|remitted)\s+back\b", re.I)
_FWD_DECISION_RE = re.compile(
    r"\b(?:take|pass|render|make)\s+(?:a\s+)?fresh\s+(?:decision|order|look)|\b(?:Tribunal|authorit\w*|respondents?|Board|"
    r"Government|Union)\s+(?:will|shall)\s*,?\s+(?:[\w,/]+\s+){0,24}?(?:decide|re-?consider|arrive\s+at|take\s+a\s+(?:fresh\s+|final\s+)?decision|"
    r"pass\s+(?:a\s+)?(?:fresh|appropriate)\s+order|re-?examine)\b", re.I)
_IN_TERMS_RELIEF_RE = re.compile(r"\bin\s+terms\s+of\s+(?:the\s+)?(?:aforesaid|above|said|earlier)?\s*(?:judgment|judgement|order|decision)[^.]{0,200}"
                                 r"|(?:same|similar)\s+relief|entitled\s+to\s+the\s+(?:same|similar)\s+(?:relief|benefit)", re.I)
_RELIEF_GRANT_RE = re.compile(r"\b(?:shall|is|are)\s+(?:be\s+)?(?:hereby\s+)?(?:entitled|reinstated|granted|released|paid)\b|\bshall\s+(?:pay|"
                              r"release|grant|reinstate)\b", re.I)
_LEAVE_WITHDRAW_RE = re.compile(r"\bleave\s+(?:as\s+prayed\s+(?:for\s+)?)?(?:is\s+)?granted\b|\bwithdrawn\b|\bwithdrawal\b|\bnot\s+pressed\b|"
                                r"\bliberty\s+to\s+withdraw|\bpermission\s+to\s+withdraw", re.I)
_PARTY_SPEC_RE = re.compile(r"\b(?:qua|in\s+regard\s+to|insofar\s+as|in\s+so\s+far\s+as|so\s+far\s+as|as\s+regards|in\s+respect\s+of|in\s+favour\s+of|"
                            r"against)\s+(?:the\s+)?(?:(?:appellant|respondent|petitioner|accused|applicant)s?\s*(?:Nos?\.?\s*)?[\d,\sand&]*|"
                            r"Union\s+of\s+India|State)\b[^.;]{0,40}", re.I)
_NO_MERITS_RE = re.compile(r"\brelegated\b|\bnot\s+expressed\s+any\s+opinion\s+on\s+the\s+merits|\bwithout\s+(?:going\s+into|expressing\s+any\s+"
                           r"opinion\s+on|entering\s+into)\s+the\s+merits|\bnot\s+(?:gone|entered)\s+into\s+the\s+merits", re.I)
_CONSIGN_RE = re.compile(r"\b(?:is|are|stands?)\s+(?:hereby\s+|accordingly\s+|,\s*)*consigned\s+to\s+(?:the\s+)?records?\b", re.I)
_TRANSMIT_RE = re.compile(r"\b(?:is|are|be|shall\s+stand)\s+(?:hereby\s+|accordingly\s+)*(?:transmitted|sent)\s+to\s+the\s+(?:Armed|AFT|Tribunal)", re.I)

DEFAULT_SUBST = {"allowed": "relief_granted", "partly_allowed": "relief_partly_granted", "dismissed": "relief_refused",
                 "dismissed_as_withdrawn": "no_adjudication", "dismissed_as_infructuous": "no_adjudication",
                 "dismissed_in_default": "no_adjudication", "transferred": "no_adjudication",
                 "remanded": "remanded_for_fresh_decision", "set_aside_and_remanded": "remanded_for_fresh_decision",
                 "not_final": "interim_only"}


def _court_voice_matches(d, rx, a, b):
    """Matches of rx in [a, b) that are outside quotations and outside party statements."""
    out = []
    for m in rx.finditer(d.mt, a, b):
        if in_spans(d.qspans, d.qstarts, m.start()):
            continue
        ls = max(d.mt.rfind(".", a, m.start()), a)
        if _PARTY_STMT_RE.search(d.mt[ls:m.start()]):
            continue
        out.append(m)
    return out


def two_fields(d, cls, ev, note, zone, signals):
    """(printed_disposal, substantive_result, reasons, method_note) for one proceeding's reduced clause class."""
    mt = d.mt
    zs, ze = zone if zone else (0, 0)
    sent = mt[ev["sentence"][0]:ev["sentence"][1]] if ev is not None else ""
    reasons = []
    printed, subst = cls, DEFAULT_SUBST.get(cls, UNVERIFIED)
    if note == "inferred_from_set_aside_of_impugned_decision":
        printed = UNVERIFIED
        reasons.append("printed:NO_DISPOSAL_WORDS_PRINTED_IMPUGNED_DECISION_SET_ASIDE")
    if cls == "dismissed" and re.search(r"\bin\s+default\b|\bnon[-\s]*prosecution\b|\bwant\s+of\s+prosecution\b|\b[ft]or\s+default\b",
                                        sent, re.I):
        printed, subst = "dismissed_in_default", "no_adjudication"
    if cls == "disposed_of_with_directions":
        if _CONSIGN_RE.search(sent):
            printed = "disposed_of"
        elif _DIRECTIONS_RE.search(sent) or (zone and _court_voice_matches(d, _DIRECTIVE_RE, zs, ze)):
            printed = "disposed_of_with_directions"
        else:
            printed = "disposed_of"
        subst = UNVERIFIED
        zt_ok = bool(zone)
        wd = zt_ok and (_court_voice_matches(d, _WITHDRAW_CTX_RE, zs, ze) or _court_voice_matches(d, _LEAVE_WITHDRAW_RE, zs, ze))
        sa = [x for t, x in signals if t == "set_aside"]
        rm = [x for t, x in signals if t == "remand"] or (zt_ok and (_court_voice_matches(d, _REMAND_RE, zs, ze) or
                                                                     _court_voice_matches(d, _FWD_DECISION_RE, zs, ze)))
        modified = zt_ok and _court_voice_matches(d, re.compile(r"\b(?:is|are|stands?|be)\s+(?:hereby\s+)?modified\b|"
                                                                    r"\bwith\s+the\s+(?:aforesaid|above)\s+modification", re.I), zs, ze)
        if wd and not sa and modified:
            subst = UNVERIFIED
            reasons.append("substantive:WITHDRAWAL_WITH_MODIFICATION_OF_THE_IMPUGNED_ORDER")
        elif wd and not sa:
            subst = "no_adjudication"
        elif re.search(r"infructuous", sent, re.I):
            subst = "no_adjudication"
        elif _CONSIGN_RE.search(sent) and re.search(r"\b(?:liberty|open|avail|remedy)\b", mt[zs:ze], re.I):
            subst = "no_adjudication"
        elif not sa and zt_ok and _court_voice_matches(d, _NO_MERITS_RE, zs, ze):
            subst = "no_adjudication"
        elif sa and rm:
            subst = "remanded_for_fresh_decision"
        elif sa:
            sa_txt = " ".join(mt[x["sentence"][0]:x["sentence"][1]] for x in sa)
            if re.search(r"to\s+the\s+extent|partly|partially|in\s+part|insofar|modif", sa_txt, re.I):
                subst = UNVERIFIED
                reasons.append("substantive:PARTIAL_SET_ASIDE_EXTENT_UNDETERMINED")
            else:
                subst = "relief_granted"
        elif zt_ok and _court_voice_matches(d, _IN_TERMS_RELIEF_RE, zs, ze) and _court_voice_matches(d, re.compile(
                r"\b(?:entitled|same\s+relief|similar\s+relief|benefit)\b", re.I), zs, ze):
            subst = "relief_granted"
        if subst == UNVERIFIED and not reasons:
            reasons.append("substantive:DISPOSED_OF_WITHOUT_DETERMINABLE_RESULT")
    elif cls == "allowed":
        rs = max(zs, ev["sentence"][0] - 400) if ev is not None else zs
        rms = _court_voice_matches(d, _REMAND_RE, rs, ze) if zone else []
        rms = [m for m in rms if not re.search(r"\bliberty\b|\bopen\s+to\b|\bif\s+so\s+advised\b",
                                                mt[max(rs, mt.rfind(".", rs, m.start())):m.end()], re.I)]
        if rms:
            subst = "remanded_for_fresh_decision"
    elif cls in ("remanded", "set_aside_and_remanded"):
        subst = "remanded_for_fresh_decision"
    elif cls == "partly_allowed" and ev is not None and _REMAND_RE.search(sent):
        subst = "remanded_for_fresh_decision"   # 'allowed in part and ... the matter is remitted to the Tribunal for fresh adjudication'
    if ev is not None and ev.get("extent"):
        reasons.append("note:EXTENT_QUALIFIED_ALLOWANCE_READ_AS_PARTLY_ALLOWED")
    return printed, subst, reasons


def _zone_party_note(d, zone):
    """Party-specific relief stated in the operative part ('sustain ... in regard to respondents 2 and 3 but reverse
    ... in regard to respondent 1'); used only to annotate a partly-allowed result."""
    ms = _court_voice_matches(d, _PARTY_SPEC_RE, zone[0], zone[1]) if zone else []
    return "; ".join(squash(m.group(0), 80) for m in ms[:3])


def _party_note(ev, d):
    if ev is None:
        return ""
    sent = d.mt[ev["sentence"][0]:ev["sentence"][1]]
    m = _PARTY_SPEC_RE.search(sent)
    return squash(m.group(0), 120) if m else ""


def _subject_ptypes(subj):
    s = subj.lower()
    out = set()
    if re.search(r"\bappeals?\b|\bc\.?a\.?\b|\bcrl\.?\s?a", s):
        out.add("appeal")
    if re.search(r"\bpetitions?\b|\bwrits?\b|\bw\.?p\b|\bcwp|\bswp|\bowp|\bslp", s):
        out.add("petition")
    if re.search(r"\btransferred\s+cases?\b|\bt\.?c\.?\b", s):
        out.add("tc")
    if re.search(r"\breview\b", s):
        out.add("rp")
    return out


_PLURAL_RE = re.compile(r"\b(?:petitions|appeals|matters|cases|applications|references|all|both|these|those|they|them|each|every|"
                        r"connected|batch)\b", re.I)
_SINGULAR_RE = re.compile(r"\b(?:this|the|present|instant|said|same|it)\b", re.I)


def _is_singular(subj, ev, d):
    """A generic disposition whose subject is singular ('the present petition', 'the same', 'it')."""
    if ev is None:
        return False
    sj = subj if subj.strip() else d.mt[ev["sentence"][0]:ev["pos"]]
    sj = _ALONG_WITH_RE.sub(" ", sj)
    if _PLURAL_RE.search(sj):
        return False
    return bool(_SINGULAR_RE.search(sj) or ev.get("standalone"))


_PT_FAMILY = {"ca": "appeal", "crla": "appeal", "lpa": "appeal", "spla": "appeal", "appeal": "appeal", "wp": "petition",
              "slp": "petition", "petition": "petition", "cont": "petition", "rev": "petition", "tc": "tc", "rp": "rp"}


def _host_family(h):
    return _PT_FAMILY.get(h.get("ptype", ""), "other")


def resolve_proceedings(d, res, hosts):
    """Turn a segment/section result into per-proceeding decisions.
    Returns (decisions, abstain_reason) where decisions = [(host_or_None, label_norm, cls, ev, note, party)]."""
    rows = res["rows"]
    keyed = [r for r in rows if r[0].startswith("N:")]
    generic = [r for r in rows if r[0] == "ALL"]
    party = [r for r in rows if r[0].startswith("P:")]
    main_hosts = [h for h in hosts if h.get("ptype") not in ("misc", "lower")]
    out = []
    covered = set()
    for k, label, cls, ev, note in keyed:
        h = ev.get("host") if ev is not None else None
        if h is None:
            c = ev.get("case") if ev is not None else None
            if c is None:
                return [], "UNMAPPED_CASE_NUMBER_IN_DISPOSITION"
            # a disposition naming a main-type number that is not a host of this judgment
            return [], "DISPOSITION_NAMES_NON_HOST_CASE_NUMBER:" + norm_label(c)
        covered.add(h["label_norm"])
        out.append((h, h["label_norm"], cls, ev, note, _party_note(ev, d)))
    if party:
        vals = set(r[2] for r in party)
        uncovered = [h for h in main_hosts if h["label_norm"] not in covered]
        if len(vals) > 1:
            return [], "PARTY_SPECIFIC_DISPOSITIONS_NOT_MAPPED_TO_CASE_NUMBERS"
        if generic and set(r[2] for r in generic) != vals:
            return [], "PARTY_SPECIFIC_DISPOSITION_CONFLICTS_WITH_GENERIC_DISPOSITION"
        if not generic:
            if len(uncovered) > 1:
                return [], "PARTY_SPECIFIC_DISPOSITION_NOT_MAPPED_TO_ONE_OF_SEVERAL_PROCEEDINGS"
            k, label, cls, ev, note = party[-1]
            generic = [("ALL", label, cls, ev, note)]
    if generic:
        if len(generic) > 1:
            o = _reduce([r[2] for r in generic])
            if o is None:
                return [], "CONFLICTING_GENERIC_DISPOSITIONS"
            g = [r for r in generic if r[2] == o][-1]
        else:
            g = generic[0]
        k, label, cls, ev, note = g
        pnote = _party_note(ev, d)
        if party:
            pnote = (pnote + "; " if pnote else "") + "disposition stated for proceedings by/of " + party[-1][0][2:]
        rest = [h for h in main_hosts if h["label_norm"] not in covered]
        subj = ev.get("subject", "") if ev is not None else ""
        fams = _subject_ptypes(subj)
        if fams and len(set(_host_family(h) for h in main_hosts)) > 1:
            # 'the present appeals are allowed' in a judgment hosting appeals and a special leave petition
            same = [h for h in rest if _host_family(h) in fams or _host_family(h) == "other"]
            if same and any(_host_family(h) in fams for h in main_hosts):
                rest = same
        if out:
            kvals = set(r[2] for r in out)
            restrict = re.search(r"\b(?:remaining|other|rest|connected|all\s+other)\b", subj, re.I)
            if kvals != {cls} and not (kvals <= {"not_final"} or restrict or fams):
                return [], "GENERIC_DISPOSITION_CONFLICTS_WITH_PROCEEDING_SPECIFIC_DISPOSITION"
        if len(rest) > 1 and _is_singular(subj, ev, d) and not out:
            return [], "SINGULAR_DISPOSITION_IN_MULTI_PROCEEDING_JUDGMENT"
        if out and rest and _is_singular(subj, ev, d):
            rest = []   # a singular 'this appeal is dismissed' beside numbered dispositions: which proceeding is unknown
        if not rest and not out:
            out.append((None, "UNIDENTIFIED", cls, ev, note, pnote))
        for h in rest:
            out.append((h, h["label_norm"], cls, ev, note, pnote))
    return out, ""


# ------------------------------------------------------------------ v3: main entry
ROW_COLS = ["judgment_id", "sha256", "doc_ids", "court", "proceeding", "file_case_role", "printed_disposal",
            "substantive_result", "party_specific", "final_or_interim", "page", "paragraph", "char_start", "char_end",
            "excerpt", "abstain_reason", "notes", "method", "flags"]


def _choose(results, mt, flags):
    """v2 segment choice (unchanged). Returns (chosen_result_or_None, abstain_reason)."""
    subst = [r for r in results if r["reason"] != "EMPTY_SEGMENT"]
    finals = [r for r in subst if r["status"] == "final"]
    last = subst[-1] if subst else None
    if last is not None and last["status"] == "final" and len(subst) > 1:
        seg_txt = mt[last["seg"][0]:last["seg"][1]]
        if len(re.sub(r"\s", "", seg_txt)) < 4000 and re.search(r"majority|^\s*ORDER", seg_txt, re.I | re.M):
            flags.append("FINAL_ORDER_AFTER_SEPARATE_OPINIONS")
            return last, ""
    if last is not None and last["status"] == "final" and "order_heading" in last["method_zone"] and \
            re.search(r"majority", mt[last["zone"][0]:last["zone"][1]], re.I):
        flags.append("FINAL_ORDER_PER_MAJORITY")
        return last, ""
    if not finals:
        nf = [r for r in subst if r["status"] == "not_final"]
        if nf and nf[-1] is last:
            return nf[-1], ""
        reasons = [r["reason"] for r in subst if r["reason"]]
        return None, (reasons[-1] if reasons else "NO_DISPOSITION_FOUND")
    if last is not finals[-1]:
        if last["status"] == "not_final":
            return None, "INTERIM_ORDER_AFTER_FINAL_DISPOSITION"
        if last["status"] == "abstain" or len(re.sub(r"\s", "", mt[last["seg"][0]:last["seg"][1]])) > 3000:
            return None, "LAST_SEGMENT_UNRESOLVED_AFTER_EARLIER_DISPOSITION:" + (last["reason"] or "NONE")
        return finals[-1], ""
    sigs = set(tuple(sorted(row[2] for row in r["rows"])) for r in finals)
    if len(sigs) == 1:
        if len(finals) > 1:
            flags.append("MULTIPLE_SEGMENTS_AGREE")
        return finals[-1], ""
    return None, "SEPARATE_OPINIONS_OR_ORDERS_WITH_DIFFERING_DISPOSITIONS"


def analyze(text, meta):
    """Return (rows, diag). meta: judgment_id, sha256, doc_ids, case_numbers_meta, court."""
    base = {"judgment_id": meta.get("judgment_id", ""), "sha256": meta.get("sha256", ""),
            "doc_ids": ";".join(meta.get("doc_ids", [])), "court": meta.get("court", "")}
    own = set()
    for c in meta_case_numbers(meta.get("case_numbers_meta", "")):
        for n in c["nums"]:
            own.add("%d/%d" % (n, c["year"]))

    def role(label):
        if not own:
            return "UNKNOWN_NO_METADATA_CASE_NUMBER"
        m = re.search(r"(\d+)/(\d{4})$", label or "")
        if m and "%d/%s" % (int(m.group(1)), m.group(2)) in own:
            return "OWN_CASE"
        return "CONNECTED_CASE" if m else "UNMATCHED"

    def row(label, printed, subst, reason, flags, ev=None, chain=None, zone=None, method="abstain", party="",
            text_=None):
        r = dict(base)
        parts = [x for x in (reason or "").split(";") if x]
        notes = ";".join(x[5:] for x in parts if x.startswith("note:"))
        reason = ";".join(x for x in parts if not x.startswith("note:"))
        r.update({"proceeding": label, "file_case_role": role(label), "printed_disposal": printed, "notes": notes,
                  "substantive_result": subst, "party_specific": party,
                  "final_or_interim": ("interim" if printed == "not_final" or subst == "interim_only" else
                                       "" if printed == UNVERIFIED and subst == UNVERIFIED else "final"),
                  "page": "", "paragraph": "", "char_start": "", "char_end": "", "excerpt": "",
                  "abstain_reason": reason, "method": method, "flags": "|".join(flags)})
        if ev is not None and text_ is not None:
            a, b = ev["sentence"]
            r.update({"page": page_at(d.pidx, ev["pos"]), "paragraph": para_at(chain or [], ev["pos"]),
                      "char_start": a, "char_end": b, "excerpt": squash(text_[a:b], 450)})
        elif zone is not None and text_ is not None:
            zs, ze = zone
            r.update({"page": page_at(d.pidx, ze - 1), "char_start": zs, "char_end": ze,
                      "excerpt": squash(text_[max(zs, ze - 450):ze], 450)})
        if r["paragraph"] is None:
            r["paragraph"] = ""
        return r

    if not text or len(re.sub(r"\s|\[\[page \d+\]\]", "", text)) < 200:
        labels = sorted(own) or ["UNIDENTIFIED"]
        return [row(_own_label(meta, l), UNVERIFIED, UNVERIFIED, "NO_TEXT_LAYER_OR_TOO_SHORT", []) for l in labels], {}
    d = Doc(text, meta)
    mt = d.mt
    scr = bool(_SCR_RE.search(mt[:8000]))
    segs = _segment_doc(d)
    cand_pos = [m.start() for m in _PARA_CAND_RE.finditer(mt)]

    def next_para(pos):
        i = bisect.bisect_right(cand_pos, pos + 5)
        return cand_pos[i] if i < len(cand_pos) else None
    d.qspans = quote_spans(mt, next_para)
    d.qstarts = [q[0] for q in d.qspans]
    js0 = 0
    mj = _JUDGMENT_START_RE.search(mt, 0, min(len(mt), 60000))
    if mj:
        js0 = mj.start()
    hosts = _host_numbers(mt, js0, meta.get("case_numbers_meta", ""), scr, d.pidx[0][1] if len(d.pidx[0]) > 1 else None)
    main_hosts = [h for h in hosts if h.get("ptype") not in ("misc", "lower")]
    flags = []
    if scr:
        flags.append("SCR_RENDITION")
    use = []
    for i, sg in enumerate(segs):
        if i > 0:
            head = mask_page_markers(d.text[sg[0]:sg[0] + 1500])   # raw text: running headers carry the case number
            if is_doc_header(mt, sg[0], 900):
                cs = find_case_numbers(head)
                if hosts and not any(_match_host(c, hosts) for c in cs):
                    flags.append("COMPOSITE_FILE_FOREIGN_DOCUMENT_IGNORED_FROM_P%d" % page_at(d.pidx, sg[0]))
                    break
                flags.append("SUCCESSIVE_DOCUMENT_SAME_CASE_P%d" % page_at(d.pidx, sg[0]))
        use.append(sg)
    results = [analyze_segment(d, sg, hosts, scr, i == 0) for i, sg in enumerate(use)]
    if len(results) > 1:
        flags.append("SEGMENTS_%d" % len(results))
    if len(main_hosts) > 1:
        flags.append("HOSTS_%d" % len(main_hosts))
    rows = []
    # ---- batch judgments: per-proceeding sections
    best = None
    for res in results:
        if res["reason"] == "EMPTY_SEGMENT":
            continue
        secs = find_sections(d, res["js"], res["seg"][1], main_hosts)
        if secs and len(secs) < 0.6 * len(main_hosts):
            flags.append("PARTIAL_SECTIONS_IGNORED_%d_OF_%d" % (len(secs), len(main_hosts)))
            secs = []
        if secs and (best is None or len(secs) > len(best[1])):
            best = (res, secs)
    if best is not None:
        brows, n_ok, last_plural = _batch_rows(d, best[1], main_hosts, row, text)
        if n_ok >= max(2, 0.5 * len(best[1])) and not last_plural:
            flags.append("BATCH_SECTIONS_%d" % len(best[1]))
            for r in brows:
                r["flags"] = "|".join(flags)
            return _finish(brows, own, meta), {"flags": flags, "hosts": [h["label_norm"] for h in hosts]}
        # headed sections that do not each carry their own disposition (facts per petition, then one common order)
        flags.append("BATCH_SECTIONS_REJECTED_%d_OF_%d_DECIDED%s" % (n_ok, len(best[1]), "_COMMON_ORDER" if last_plural else ""))
    # ---- single decision for the judgment
    chosen, reason = _choose(results, mt, flags)
    labels = [h["label_norm"] for h in main_hosts] or ["UNIDENTIFIED"]
    if chosen is None:
        rows = [row(l, UNVERIFIED, UNVERIFIED, reason, flags) for l in labels]
        return _finish(rows, own, meta), {"flags": flags, "hosts": labels}
    dec, why = resolve_proceedings(d, chosen, main_hosts)
    if not dec:
        rows = [row(l, UNVERIFIED, UNVERIFIED, why, flags) for l in labels]
        return _finish(rows, own, meta), {"flags": flags, "hosts": labels}
    got = set()
    multi_ev = len(set(x[3]["sentence"] for x in dec if x[3] is not None)) >= 2
    for h, label, cls, ev, note, party in dec:
        zone_i, sig_i = chosen["zone"], chosen["signals"]
        if multi_ev and ev is not None:
            zone_i = _local_zone(chosen, ev)
            sig_i = [(t, x) for t, x in chosen["signals"] if zone_i[0] <= x["pos"] < zone_i[1]]
        printed, subst, reasons = two_fields(d, cls, ev, note, zone_i, sig_i)
        if not party and printed == "partly_allowed":
            party = _zone_party_note(d, zone_i)
        meth = ";".join(x for x in [chosen["method_zone"], note] if x)
        rows.append(row(label, printed, subst, ";".join(reasons), flags, ev=ev, chain=chosen["chain"],
                        zone=chosen["zone"], method=meth, party=party, text_=text))
        got.add(label)
    for l in labels:
        if l not in got and l != "UNIDENTIFIED":
            rows.append(row(l, UNVERIFIED, UNVERIFIED, "NO_DISPOSITION_MAPPED_TO_THIS_PROCEEDING", flags))
    return _finish(rows, own, meta), {"flags": flags, "hosts": labels}


def _batch_rows(d, secs, main_hosts, row, text):
    """Analyse each batch section on its own. Returns (rows, number of sections decided, whether the last section's
    disposition is a plural/common one such as 'all the writ petitions are allowed')."""
    rows, done, n_ok, last_plural = [], set(), 0, False
    for i, (a, e, h, unsafe) in enumerate(secs):
        done.add(h["label_norm"])
        if unsafe:
            rows.append(row(h["label_norm"], UNVERIFIED, UNVERIFIED, "SECTION:" + unsafe, [], zone=(a, e), text_=text))
            continue
        sres = analyze_segment(d, [a, e, e], [h], False, False, section=True)
        dec, why = ([], sres["reason"] or "NO_DISPOSITION_IN_SECTION")
        if sres["status"] in ("final", "not_final"):
            dec, why = resolve_proceedings(d, sres, [dict(h)])
        dec = [x for x in dec if x[1] == h["label_norm"]]
        if not dec:
            rows.append(row(h["label_norm"], UNVERIFIED, UNVERIFIED, "SECTION:" + (why or "NO_DISPOSITION_FOR_SECTION_HOST"),
                            [], zone=(a, e), text_=text))
            continue
        n_ok += 1
        hh, label, cls, ev, note, party = dec[-1]
        if i == len(secs) - 1 and ev is not None and re.search(
                r"\b(?:all|both|these|the(?:se)?\s+(?:writ\s+)?(?:petitions|appeals|matters|cases))\b|\b(?:petitions|appeals)\b",
                ev.get("subject", "") + " " + d.mt[ev["sentence"][0]:ev["sentence"][1]], re.I):
            last_plural = True
        printed, subst, reasons = two_fields(d, cls, ev, note, sres["zone"], sres["signals"])
        meth = ";".join(x for x in ["batch_section@p%d" % page_at(d.pidx, a), sres["method_zone"], note] if x)
        rows.append(row(label, printed, subst, ";".join(reasons), [], ev=ev, chain=sres["chain"], zone=sres["zone"],
                        method=meth, party=party, text_=text))
    for h in main_hosts:
        if h["label_norm"] not in done:
            rows.append(row(h["label_norm"], UNVERIFIED, UNVERIFIED, "BATCH_PROCEEDING_WITHOUT_OWN_SECTION", []))
    return rows, n_ok, last_plural


def _local_zone(res, ev):
    """The host paragraph holding the evidence sentence (used when one operative part disposes of different
    proceedings in different sentences, so that a set-aside or withdrawal in one paragraph is not read into another)."""
    zs, ze = res["zone"]
    chain = res.get("chain") or []
    pos = ev["sentence"][0]
    starts = [p for p, _ in chain if zs <= p < ze]
    a = max([p for p in starts if p <= pos] or [max(zs, pos - 600)])
    b = min([p for p in starts if p > pos] or [min(ze, ev["sentence"][1] + 600)])
    return (a, b)


def _own_label(meta, key):
    for c in meta_case_numbers(meta.get("case_numbers_meta", "")):
        for n in c["nums"]:
            if "%d/%d" % (n, c["year"]) == key:
                return norm_label(c, n)
    return key


def _finish(rows, own, meta):
    """Stable order; a file whose own (metadata) case number is not among the proceedings gets an explicit
    abstention row for it."""
    labels = set()
    for r in rows:
        m = re.search(r"(\d+)/(\d{4})$", r["proceeding"])
        if m:
            labels.add("%d/%s" % (int(m.group(1)), m.group(2)))
    for k in sorted(own - labels):
        r = dict(rows[0]) if rows else {}
        r.update({"proceeding": _own_label(meta, k), "file_case_role": "OWN_CASE", "printed_disposal": UNVERIFIED,
                  "substantive_result": UNVERIFIED, "party_specific": "", "final_or_interim": "", "page": "",
                  "paragraph": "", "char_start": "", "char_end": "", "excerpt": "",
                  "abstain_reason": "OWN_CASE_NUMBER_NOT_MAPPED_TO_A_PROCEEDING", "notes": "", "method": "abstain"})
        rows.append(r)
    for r in rows:
        r["status"] = STATUS
        r["extractor"] = VERSION
    return rows
