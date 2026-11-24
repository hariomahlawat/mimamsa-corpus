"""Mimamsa C11 structured outcome and legal-proposition extraction: core (pure functions, no I/O).

Every value produced here is an AUTOMATED CANDIDATE read from a PDF text layer. Nothing is legally verified.
No proposition is ever labelled a verified holding or ratio.

Design (structural, not keyword lists):
  1. mask boilerplate lines (same length, so character offsets stay valid against the source text file);
  2. find signature blocks and split the file into opinion/order segments; detect composite files and
     separate opinions;
  3. inside a segment find zones: cause title, editorial headnote (S.C.R. renditions), quoted blocks
     (quotation marks, and unmarked blocks after 'held as under:' up to the next host paragraph),
     the operative part (cue near the end, up to the signature), editorial reporter's note;
  4. in the operative part, parse each disposition clause: verb form (tense/modality), grammatical
     subject (main proceeding / miscellaneous application / lower-forum proceeding / impugned decision),
     case numbers in the subject (mapped to host case numbers) and party descriptors;
  5. aggregate per proceeding, with an explicit ABSTAIN rule (OUTCOME_UNVERIFIED + reason).
"""
import bisect
import re

VERSION = "c11-extract-v2/1.0.0"
STATUS = "AUTOMATED_CANDIDATE_NOT_VERIFIED"
UNVERIFIED = "OUTCOME_UNVERIFIED"
OUTCOME_VOCAB = ["allowed", "partly_allowed", "dismissed", "dismissed_as_withdrawn", "dismissed_as_infructuous",
                 "disposed_of_with_directions", "remanded", "set_aside_and_remanded", "transferred", "not_final",
                 UNVERIFIED]
ORIGINS = ["COURT_HOLDING_CANDIDATE", "COURT_REASONING_CANDIDATE", "QUOTED_PRECEDENT", "PARTY_SUBMISSION",
           "LOWER_COURT_FINDING", "EDITORIAL_HEADNOTE", "STATUTORY_QUOTATION", "OTHER_OR_UNCERTAIN"]

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


def mask_boilerplate(text):
    """Replace boilerplate lines with spaces (length preserved so offsets stay valid)."""
    out = []
    for line in text.splitlines(True):
        body = line.rstrip("\n")
        if body and any(r.search(body) for r in _MASK_LINE_RES):
            out.append(" " * len(body) + line[len(body):])
        else:
            out.append(line)
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
    for m in re.finditer(r"[.?!;:](?=\s)", text[start:end]):
        p = start + m.end()
        ch = m.group(0)
        if ch == ".":
            j = start + m.start()
            k = j
            while k > start and (text[k - 1].isalnum() or text[k - 1] == "."):
                k -= 1
            tok = text[k:j].lower().strip(".")
            if tok in _ABBR or (len(tok) == 1 and tok.isalpha()):
                continue
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
_TYPE_BEFORE_RE = re.compile(r"([A-Za-z][A-Za-z.()&\s]{0,45}?)\s*(?:Nos?\s*\.?|Numbers?|D\.?\s*No\.?)?\s*[:.]?\s*$")


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
        ("wp", r"(writpetition|^wp|cwp|owp|^swp|writa|writc|^writ|wpc|wpcrl|wps|wpcrl)"),
        ("spla", r"(specialappeal|spla)"),
        ("rp", r"(review)"),
        ("cont", r"(contempt|cocp|conc|coc)"),
        ("rev", r"(revision|crr|crrev)"),
        ("appeal", r"(appeal)"),
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
        label = squash((typ + " " + s[m.start():m.end()]) if typ else s[m.start():m.end()])
        out.append({"type": typ, "ptype": ptype(typ), "nums": _expand(m.group(1)), "year": int(m.group(2)),
                    "label": label, "pos": m.start()})
    for m in re.finditer(r"\b([A-Z][A-Za-z.()]{1,20})[-/ ](\d{1,6})[-/]((?:19|20)\d{2})\b", s):
        if any(o["pos"] <= m.start() < o["pos"] + 30 for o in out):
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
    r"remanded|remitted|transferred|set\s*-?\s*aside|quashed|closed|discharged|made\s+absolute)\b", re.I)
_ACTIVE_RE = re.compile(
    r"\b(?:we|this\s+court|the\s+court)\b[\s,\-]*(?:(?:accordingly|therefore|hence|hereby|thus|consequently|would|"
    r",|also|partly|partially|,)\s*)*\b(allow|dismiss|dispose\s+of|dispose\s+off|remand|remit|accept|reject|"
    r"set\s+aside|quash|transfer)\b", re.I)
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


def classify_subject(subj):
    s = subj.strip()
    if "," in s:
        tail = s.rsplit(",", 1)[1]
        r = _classify_subject(tail)
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
        if re.match(r"\s*(?:only\s+)?to\s+the\s+extent", after):
            return "extent_qualified"
        if re.match(r"\s*to\s+(?!the\s+extent|a\s+limited)", after):
            return None   # 'allowed to join/continue' etc.
        return "allowed"
    if v in ("dismissed", "rejected", "dismiss", "reject", "fails", "fail", "discharged"):
        if re.match(r"\s*(?:\w+\s+){0,2}?(?:except|save|but\s+only)\s+(?:to\s+the\s+extent|as\s+(?:indicated|mentioned|stated))", after):
            return "extent_qualified"
        return "dismissed"
    if v in ("disposed of", "disposed off", "disposed", "dispose of", "dispose off", "closed"):
        return "disposed_of_with_directions"
    if v in ("remanded", "remitted", "remand", "remit"):
        return "remanded"
    if v in ("transferred", "transfer"):
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
        out.append({"verb": v, "cls": cls, "subject": subj, "tense": tense, "rel": m.start(),
                    "standalone": standalone, "form": "passive", "clause": sent[cs:clause_end(m.end())]})
        found_spans.append((m.start(), m.end()))
    for m in _ACTIVE_RE.finditer(sent):
        v = m.group(1)
        obj_end = clause_end(m.end())
        obj = sent[m.end():min(obj_end, m.end() + 160)]
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
        if _PARTY_STMT_RE.search(sent[:m.start()]):
            tense = "party_statement"
        if re.search(r"\bwould\b", between) or _COND_RE.search(pre):
            tense = "conditional"
        out.append({"verb": v, "cls": cls, "subject": obj, "tense": tense, "rel": m.start(1), "standalone": False,
                    "form": "active", "clause": sent[clause_start(m.start()):obj_end]})
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
        out.append({"verb": m.group(1), "cls": cls, "subject": subj, "tense": tense, "rel": m.start(),
                    "standalone": False, "form": "intransitive", "clause": sent[cs:clause_end(m.end())]})
    closes_quote = bool(re.search(r"^[^\u201c]*\u201d", sent)) or bool(re.match(r"\s*[\u201d\"]", text[e:e + 3]))
    for d in out:
        d["pos"] = s + d["rel"]
        pre = re.sub(r"\bif\s+any\b|\bif\s+not\s+already\b", " ", text[s + clause_start(d["rel"]):d["pos"]], flags=re.I)
        d["conditional_context"] = bool(_COND_RE.search(pre))
        d["closes_quote"] = closes_quote
        d["sentence"] = (s, e)
    out.sort(key=lambda d: d["rel"])
    return out


_NOT_FINAL_RE = re.compile(
    r"(?:^\s*|[.;:]\s+|^\s*\d+\s*\.\s*)(?:List|Re-?\s?list|Re-?\s?notify|Renotify|Issue\s+notice|Put\s+up|Stand\s+over|"
    r"Adjourned|To\s+be\s+listed)\b|\b(?:be\s+(?:re-?)?listed|be\s+put\s+up|stands?\s+adjourned|is\s+adjourned|"
    r"next\s+date\s+of\s+hearing|till\s+the\s+next\s+date|part[-\s]heard)\b")
_OPERATIVE_CUE_RE = re.compile(
    r"\b(in\s+the\s+(?:final\s+)?result|for\s+the\s+(?:foregoing|aforesaid|above|reasons)|for\s+(?:all\s+)?the(?:se)?\s+reasons|"
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
    r"(?m:^[ \t]*[A-Z][A-Z. ]{3,60},\s*(?:C\.?J\.?|J\.?)\s*(?:\(\s*(?:ORAL|Oral)\s*\))?\s*[:.]?)", re.I)
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


# ------------------------------------------------------------------ legal issue keywords (for proposition tagging)
ISSUE_RES = [(k, re.compile(p, re.I)) for k, p in [
    ("court_martial", r"court[\s-]+martial|\bG\.?C\.?M\b|\bS\.?C\.?M\b|\bD\.?C\.?M\b|summary\s+of\s+evidence"),
    ("disability_pension", r"disability\s+(?:pension|element)|invalid(?:ed|ment)\s+(?:out|pension)|release\s+medical\s+board"),
    ("attributability_aggravation", r"attributab|aggravat|entitlement\s+rules"),
    ("aft_jurisdiction", r"armed\s+forces\s+tribunal|\bA\.?F\.?T\.?\b|section\s+(?:14|15|30|31)\s+of\s+the\s+(?:AFT|Armed)"),
    ("writ_jurisdiction", r"article\s+(?:226|227|32)\b|writ\s+jurisdiction|alternative\s+(?:and\s+efficacious\s+)?remedy"),
    ("article_33", r"article\s+33\b"),
    ("natural_justice", r"natural\s+justice|audi\s+alteram|show\s+cause|\bbias\b"),
    ("delay_limitation", r"\bdelay\b|laches|limitation|condonation"),
    ("desertion_absence", r"desert(?:ion|er)|absent\s+without\s+leave|\bAWL\b|illegal\s+absence"),
    ("pension_service", r"\bpension|gratuity|service\s+element|qualifying\s+service|arrears"),
    ("promotion_selection", r"promotion|selection\s+board|permanent\s+commission|seniority"),
    ("discharge_dismissal", r"discharg|dismiss(?:al)?\s+from\s+service|termination|cashier"),
    ("army_act", r"army\s+act|air\s+force\s+act|navy\s+act|army\s+rules|regulations\s+for\s+the\s+army"),
    ("evidence_confession", r"confession|evidence\s+act|section\s+25\b|admissib"),
    ("double_jeopardy_s121", r"double\s+jeopardy|section\s+121\b|article\s+20\b"),
    ("reasons_requirement", r"record(?:ing)?\s+(?:of\s+)?reasons|speaking\s+order|reasoned\s+order"),
]]
_STAT_REF_RE = re.compile(r"\b(?:section|sec\.|rule|regulation|article|art\.)\s*(\d+[A-Z]?(?:\s*\(\w+\))*)"
                          r"(?:\s+of\s+the\s+((?:[A-Z][A-Za-z()]*\s*){1,6}(?:Act|Rules|Regulations)(?:,?\s*\d{4})?))?", re.I)

_COURT_VOICE_RE = re.compile(
    r"\b(we\s+(?:are\s+of\s+the\s+(?:considered\s+|firm\s+)?(?:view|opinion)|hold|find|are\s+satisfied|are\s+unable|do\s+not\s+find|"
    r"have\s+no\s+hesitation|agree|disagree|are\s+inclined|are\s+not\s+inclined|reject|accept|answer|declare|conclude|"
    r"see\s+no|have\s+considered|are\s+afraid|cannot\s+accept|are\s+in\s+agreement)|in\s+our\s+(?:considered\s+)?(?:view|opinion)|"
    r"this\s+court\s+(?:is\s+of\s+the|finds|holds|is\s+satisfied|is\s+unable)|it\s+is\s+(?:thus\s+|therefore\s+|hence\s+)?(?:clear|evident|"
    r"well[-\s]settled|settled|apparent|manifest)|the\s+(?:law|position)\s+is\s+(?:well[-\s])?settled|"
    r"(?:cannot|can\s*not)\s+be\s+(?:sustained|faulted|countenanced|accepted)|is\s+not\s+sustainable|is\s+(?:not\s+)?maintainable)\b", re.I)
_HOLDING_MARK_RE = re.compile(r"\b(we\s+(?:hold|answer|declare|conclude)|it\s+is\s+(?:hereby\s+)?held|we\s+are\s+of\s+the\s+"
                              r"(?:considered\s+)?(?:view|opinion)\s+that|the\s+(?:question|issue|reference)\s+is\s+answered)\b", re.I)
_SUBMISSION_RE = re.compile(
    r"\b(learned\s+(?:senior\s+|additional\s+|standing\s+)?(?:counsel|advocate|A\.?S\.?G|C\.?G\.?S\.?C|solicitor)|counsel\s+for\s+the|"
    r"it\s+(?:is|was|has\s+been)\s+(?:submitted|contended|argued|urged|pleaded|averred|stated\s+on\s+behalf)|"
    r"(?:the\s+)?(?:petitioner|appellant|respondent|applicant)s?\s+(?:has|have|had)?\s*(?:submitted|contended|argued|urged|pleaded|averred)|"
    r"the\s+(?:case|contention|submission|stand|plea|argument)s?\s+of\s+the|on\s+behalf\s+of\s+the\s+(?:petitioner|appellant|respondent|"
    r"Union|applicant))", re.I)
_SUBM_VERB_RE = re.compile(r"\b(submit|contend|argue|urge|plead|aver|point|state|rel(?:y|ied)|place)\w*", re.I)
_LOWER_RE = re.compile(
    r"\b(the\s+(?:learned\s+)?(?:Armed\s+Forces\s+)?Tribunal|the\s+(?:learned\s+)?AFT|the\s+learned\s+Single\s+Judge|the\s+(?:learned\s+)?"
    r"(?:trial\s+court|appellate\s+court|District\s+Judge|Single\s+Bench)|the\s+High\s+Court|the\s+(?:General|Summary|District)\s+Court\s+Martial|"
    r"the\s+(?:GCM|SCM|DCM)|the\s+Court\s+of\s+(?:Inquiry|Enquiry)|the\s+(?:Medical|Selection|Review)\s+Board|the\s+impugned\s+"
    r"(?:order|judgment))\s+(?:has\s+|had\s+|have\s+)?(?:also\s+|rightly\s+|wrongly\s+|erroneously\s+)?(held|observed|found|concluded|recorded|"
    r"opined|dismissed|allowed|rejected|noted|came\s+to|declined|granted|directed|accepted)\b", re.I)
_CITATION_RE = re.compile(r"\b(?:v\.|vs\.?|versus)\s|\bSCC\b|S\.C\.R|\bAIR\b|\bSCALE\b|\bINSC\b|\bSLJ\b|\bSLR\b|\(supra\)|"
                          r"in\s+the\s+case\s+of|Constitution\s+Bench|Full\s+Bench|Larger\s+Bench|this\s+Court\s+in", re.I)
_STATUTE_INTRO_RE = re.compile(r"\b(section|rule|regulation|article|para(?:graph)?|clause|notification|policy|act|"
                               r"letter|order\s+dated|reads?|provides?|provision)\b", re.I)
_CASE_NAME_RE = re.compile(r"([A-Z][A-Za-z.&'()]*(?:\s+(?:[A-Z][A-Za-z.&'()]*|of|and|&)){0,7})\s+(?:v\.|vs\.?|versus)\s+"
                           r"([A-Z][A-Za-z.&'()]*(?:\s+(?:[A-Z][A-Za-z.&'()]*|of|and|&)){0,7})")
_SUPRA_RE = re.compile(r"([A-Z][A-Za-z.&']+(?:\s+[A-Z][A-Za-z.&']+){0,4})(?:'s)?\s+(?:case\s+)?\(supra\)")


def issue_keywords(s):
    tags = [k for k, rx in ISSUE_RES if rx.search(s)]
    stats = []
    for m in _STAT_REF_RE.finditer(s):
        ref = squash(m.group(0), 80)
        if ref not in stats:
            stats.append(ref)
        if len(stats) >= 4:
            break
    return tags, stats


# ------------------------------------------------------------------ main analysis
def _host_numbers(mt, js, case_numbers_meta, scr, page2=None):
    """Host proceedings: crawler metadata case numbers plus numbers printed in the cause title (first page only)."""
    hosts = meta_case_numbers(case_numbers_meta)
    if scr:
        zone = mt[:2500]
    else:
        zone = mt[:max(min(js, 4000), 1500)]
    if page2 is not None and page2 < len(zone) and page2 > 200:
        zone = zone[:page2]
    for c in find_case_numbers(zone):
        if c["ptype"] in ("misc", "lower", "", "other"):
            continue
        hosts.append(c)
    return hosts


def _match_host(c, hosts):
    for h in hosts:
        if h["year"] == c["year"] and (h["nums"] & c["nums"]):
            return h
    return None


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


class Doc:
    def __init__(self, text, meta):
        self.text = text
        self.meta = meta
        self.pidx = page_index(text)
        self.mt = mask_page_markers(mask_boilerplate(text))
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


def analyze_segment(d, seg, hosts, scr, is_first):
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
    win_start = max(js, body_end - max(3500, min(int(0.12 * L), 9000)))
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
                if scls in ("lower_decision", "main", "pronoun", "elided"):
                    res["signals"].append(("set_aside", dd))
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
            nums = find_case_numbers(subj)
            if not nums and len(blocks) >= 2:
                bi = bisect.bisect_right(bpos, dd["pos"]) - 1
                if bi >= 0:
                    nums = [blocks[bi][1]]
            if nums:
                c = nums[0]
                h = _match_host(c, hosts)
                if h is not None:
                    key, label = "N:%s:%d" % (min(h["nums"] & c["nums"]), c["year"]), c["label"]
                elif c["ptype"] == "misc":
                    res["excluded"]["misc"] += 1
                    continue
                elif c["ptype"] == "lower":
                    res["excluded"]["lower"] += 1
                    continue
                else:
                    key, label = "N:%s:%d" % (min(c["nums"]) if c["nums"] else 0, c["year"]), c["label"]
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
        elif sa and re.search(r"impugned", sa_text, re.I) and not re.search(r"to\s+the\s+extent|partly|partially|modif", sa_text, re.I):
            res["status"] = "final"
            res["rows"] = [("ALL", "", "allowed", sa[-1], "inferred_from_set_aside_of_impugned_decision")]
        elif notfinal:
            res["status"] = "not_final"
            res["rows"] = [("ALL", "", "not_final", None, "listing_or_adjournment_cue")]
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
    spec = {k: v for k, v in outk.items() if k != "ALL"}
    if not spec:
        o, ev, note = outk["ALL"]
        res["status"] = "final"
        res["rows"] = [("ALL", "", o, ev, note)]
        return res
    vals = set(v[0] for v in spec.values())
    if "ALL" in outk:
        o_all = outk["ALL"][0]
        if o_all == "disposed_of_with_directions" and len(vals) > 1:
            pass
        elif len(vals) == 1 and _reduce([o_all] + list(vals)) is not None:
            res["status"] = "final"
            res["rows"] = [("ALL", "", _reduce([o_all] + list(vals)), outk["ALL"][1], outk["ALL"][2])]
            return res
        else:
            res["status"] = "abstain"
            res["reason"] = "GENERIC_DISPOSITION_CONFLICTS_WITH_PROCEEDING_SPECIFIC_DISPOSITION"
            return res
    host_keys = set()
    for h in hosts:
        for n_ in h["nums"]:
            host_keys.add("N:%d:%d" % (n_, h["year"]))
    covers_hosts = bool(host_keys) and all(k.startswith("N:") for k in spec) and \
        host_keys <= set(spec) | set(k for k in host_keys if any(k == x for x in spec))
    if len(vals) == 1 and (covers_hosts or len(host_keys) <= 1 or not all(k.startswith("N:") for k in spec)):
        k0 = sorted(spec)[0]
        res["status"] = "final"
        res["rows"] = [("ALL", "", spec[k0][0], spec[k0][1], "all_numbered_proceedings_agree")]
        return res
    res["status"] = "final"
    res["rows"] = [(k, keys[k][-1]["label"], v[0], v[1], "per_proceeding_mapping" + (";" + v[2] if v[2] else ""))
                   for k, v in sorted(spec.items(), key=lambda kv: kv[1][1]["pos"])]
    return res


def analyze(text, meta):
    """Return (outcome_rows, propositions, diag). meta: judgment_id, sha256, doc_ids, case_numbers_meta, court."""
    base = {"judgment_id": meta.get("judgment_id", ""), "sha256": meta.get("sha256", ""),
            "doc_ids": ";".join(meta.get("doc_ids", [])), "court": meta.get("court", "")}

    def abstain(reason, flags=""):
        r = dict(base)
        r.update({"proceeding": "ALL", "outcome": UNVERIFIED, "page": "", "paragraph": "", "char_start": "",
                  "char_end": "", "excerpt": "", "method": "abstain", "abstain_reason": reason, "flags": flags})
        return r

    if not text or len(re.sub(r"\s|\[\[page \d+\]\]", "", text)) < 200:
        return [abstain("NO_TEXT_LAYER_OR_TOO_SHORT")], [], {}
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
    flags = []
    if scr:
        flags.append("SCR_RENDITION")
    use = []
    for i, sg in enumerate(segs):
        if i > 0:
            head = mt[sg[0]:sg[0] + 1500]
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
    chosen = None
    rows = []
    subst = [r for r in results if r["reason"] != "EMPTY_SEGMENT"]
    finals = [r for r in subst if r["status"] == "final"]
    last = subst[-1] if subst else None
    if last is not None and last["status"] == "final" and len(subst) > 1:
        seg_txt = mt[last["seg"][0]:last["seg"][1]]
        if len(re.sub(r"\s", "", seg_txt)) < 4000 and re.search(r"majority|^\s*ORDER", seg_txt, re.I | re.M):
            chosen = last
            flags.append("FINAL_ORDER_AFTER_SEPARATE_OPINIONS")
    if chosen is None and last is not None and last["status"] == "final" and "order_heading" in last["method_zone"] and \
            re.search(r"majority", mt[last["zone"][0]:last["zone"][1]], re.I):
        chosen = last
        flags.append("FINAL_ORDER_PER_MAJORITY")
    if chosen is None and not rows:
        if not finals:
            nf = [r for r in subst if r["status"] == "not_final"]
            if nf and nf[-1] is last:
                chosen = nf[-1]
            else:
                reasons = [r["reason"] for r in subst if r["reason"]]
                rows = [abstain(reasons[-1] if reasons else "NO_DISPOSITION_FOUND", "|".join(flags))]
        elif last is not finals[-1]:
            if last["status"] == "not_final":
                rows = [abstain("INTERIM_ORDER_AFTER_FINAL_DISPOSITION", "|".join(flags))]
            elif last["status"] == "abstain" or len(re.sub(r"\s", "", mt[last["seg"][0]:last["seg"][1]])) > 3000:
                rows = [abstain("LAST_SEGMENT_UNRESOLVED_AFTER_EARLIER_DISPOSITION:" + (last["reason"] or "NONE"), "|".join(flags))]
            else:
                chosen = finals[-1]
        if chosen is None and not rows:
            sigs = set(tuple(sorted(row[2] for row in r["rows"])) for r in finals)
            if len(sigs) == 1:
                chosen = finals[-1]
                if len(finals) > 1:
                    flags.append("MULTIPLE_SEGMENTS_AGREE")
            else:
                rows = [abstain("SEPARATE_OPINIONS_OR_ORDERS_WITH_DIFFERING_DISPOSITIONS", "|".join(flags))]
    if chosen is not None:
        host_label = "; ".join(sorted(set(h["label"] for h in hosts)))[:300] or "ALL"
        for key, label, outcome, ev, note in chosen["rows"]:
            r = dict(base)
            if ev is not None:
                a, b = ev["sentence"]
                r.update({"page": page_at(d.pidx, ev["pos"]), "paragraph": para_at(chosen["chain"], ev["pos"]),
                          "char_start": a, "char_end": b, "excerpt": squash(text[a:b], 450)})
            else:
                zs, ze = chosen["zone"]
                r.update({"page": page_at(d.pidx, ze - 1), "paragraph": None, "char_start": zs, "char_end": ze,
                          "excerpt": squash(text[max(zs, ze - 450):ze], 450)})
            r["paragraph"] = "" if r["paragraph"] is None else r["paragraph"]
            r.update({"proceeding": host_label if key == "ALL" else label, "outcome": outcome,
                      "method": ";".join(x for x in [chosen["method_zone"], note] if x), "abstain_reason": "",
                      "flags": "|".join(flags)})
            rows.append(r)
    props = extract_propositions(d, use, results, chosen, rows)
    diag = {"segments": len(segs), "used": len(use), "flags": flags, "excluded": [r["excluded"] for r in results]}
    return rows, props, diag


def _speaker_from_intro(intro):
    names = list(_CASE_NAME_RE.finditer(intro))
    if names:
        return squash(names[-1].group(0), 120)
    sp = list(_SUPRA_RE.finditer(intro))
    if sp:
        return squash(sp[-1].group(0), 120)
    st = list(_STAT_REF_RE.finditer(intro))
    if st:
        return squash(st[-1].group(0), 120)
    return ""


def extract_propositions(d, segs, results, chosen, out_rows, cap=25):
    mt, text = d.mt, d.text
    qs, qst = d.qspans, d.qstarts
    outcome_summary = ";".join(sorted(set("%s=%s" % (r["proceeding"][:40], r["outcome"]) for r in out_rows)))[:300]
    cands = []
    for si, (sg, res) in enumerate(zip(segs, results)):
        s0, s1 = sg[0], sg[1]
        chain = res.get("chain") or host_paragraphs(mt, s0, s1, qs, qst)
        head, zone, tail = res.get("headnote"), res.get("zone"), res.get("tail")
        cur_para, para_subm = None, False
        for (a, b) in sentences(mt, s0, s1):
            sent = mt[a:b]
            if len(sent.strip()) < 60 or len(sent) > 4000:
                continue
            pn = para_at(chain, a)
            first_sentence = pn != cur_para
            if first_sentence:
                cur_para, para_subm = pn, False
            q = in_spans(qs, qst, a + len(sent) - len(sent.lstrip()))
            tags, stats = issue_keywords(sent)
            voice = _COURT_VOICE_RE.search(sent)
            subm = bool(_SUBMISSION_RE.search(sent) and _SUBM_VERB_RE.search(sent))
            lower = _LOWER_RE.search(sent)
            if subm and first_sentence:
                para_subm = True
            if voice and not subm:
                para_subm = False
            origin, speaker, relation = "OTHER_OR_UNCERTAIN", "", "UNDETERMINED"
            in_head = head is not None and head[0] <= a < head[1]
            in_tail = tail is not None and tail[0] <= a < tail[1]
            if in_head or in_tail:
                origin, speaker, relation = "EDITORIAL_HEADNOTE", "law reporter (editorial)", "EDITORIAL_NOT_PART_OF_JUDGMENT"
            elif q:
                intro = mt[q[3]:q[0]]
                relation = "QUOTED_MATERIAL_NOT_COURT_VOICE"
                if _CITATION_RE.search(intro):
                    origin, speaker = "QUOTED_PRECEDENT", _speaker_from_intro(intro)
                elif _STATUTE_INTRO_RE.search(intro):
                    origin, speaker = "STATUTORY_QUOTATION", _speaker_from_intro(intro)
                elif _LOWER_RE.search(intro) or re.search(r"Tribunal|Single\s+Judge|impugned|AFT", intro):
                    origin, speaker = "LOWER_COURT_FINDING", "lower forum (quoted)"
                elif _SUBMISSION_RE.search(intro):
                    origin, speaker = "PARTY_SUBMISSION", "party (quoted)"
                else:
                    origin, speaker = "OTHER_OR_UNCERTAIN", "quoted source undetermined"
            elif subm or (para_subm and not voice):
                origin, relation = "PARTY_SUBMISSION", "ATTRIBUTED_TO_PARTY"
                sm = re.search(r"(?:for|on\s+behalf\s+of)\s+the\s+(petitioners?|appellants?|respondents?|applicants?|Union\s+of\s+India|State|accused)", sent, re.I)
                speaker = ("counsel for the " + sm.group(1)) if sm else "party/counsel"
            elif lower and not voice:
                origin, relation = "LOWER_COURT_FINDING", "ATTRIBUTED_TO_LOWER_FORUM"
                speaker = squash(lower.group(1), 60)
            elif voice:
                in_zone = zone is not None and zone[0] <= a < zone[1]
                origin = "COURT_HOLDING_CANDIDATE" if (in_zone or _HOLDING_MARK_RE.search(sent)) else "COURT_REASONING_CANDIDATE"
                speaker = "court (this bench)"
                if chosen is not None and res is chosen:
                    relation = "WITHIN_OPERATIVE_PART" if in_zone else "PRECEDES_OPERATIVE_PART_SAME_SEGMENT"
                elif chosen is not None:
                    relation = "OTHER_SEGMENT_OR_SEPARATE_OPINION"
                else:
                    relation = "OPERATIVE_DECISION_UNVERIFIED"
            if not tags and not stats and (origin == "OTHER_OR_UNCERTAIN" or not voice):
                continue
            prio = {"COURT_HOLDING_CANDIDATE": 0, "COURT_REASONING_CANDIDATE": 1}.get(origin, 2)
            cands.append((prio, a, b, origin, speaker, relation, tags, stats, pn, si))
    court = sorted([c for c in cands if c[0] < 2], key=lambda c: (c[0], -len(c[6]), c[1]))
    others = sorted([c for c in cands if c[0] == 2], key=lambda c: (-len(c[6]) - len(c[7]), c[1]))
    sel = court[:12] + others[:cap - min(12, len(court))]
    sel.sort(key=lambda c: c[1])
    out = []
    meta = d.meta
    for prio, a, b, origin, speaker, relation, tags, stats, pn, si in sel:
        out.append({
            "judgment_id": meta.get("judgment_id", ""), "sha256": meta.get("sha256", ""),
            "doc_id": (meta.get("doc_ids") or [""])[0], "page": page_at(d.pidx, a), "paragraph": pn,
            "char_start": a, "char_end": b, "segment": si, "origin": origin, "attributed_to": speaker,
            "legal_issue_keywords": tags, "statutory_references": stats, "relation_to_operative_decision": relation,
            "judgment_outcome_v2": outcome_summary, "excerpt": squash(text[a:b], 700),
            "verification": "NOT_VERIFIED_NOT_A_HOLDING", "status": STATUS, "extractor": VERSION})
    return out
