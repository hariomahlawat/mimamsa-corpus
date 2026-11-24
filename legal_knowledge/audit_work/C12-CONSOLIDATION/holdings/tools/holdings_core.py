"""Mimamsa C12 Workstream E: holdings-focused extraction core (pure functions, standard library only).

Input: one judgment text layer (str, with [[page N]] markers) plus small metadata.
Output: a judgment-level summary and a list of AUTOMATED CANDIDATE items:
  question_of_law, holding, reasoning, obiter_candidate, operative_direction,
  quoted_precedent, submission, lower_court_finding
Every item carries status AUTOMATED_CANDIDATE_NOT_VERIFIED. Nothing here decides what the ratio is,
and nothing here infers overruling.

Offsets (char_start, char_end) index the decoded text string exactly as read from the text layer.
`excerpt` is text[char_start:char_end] with whitespace runs squashed (verbatim otherwise);
`excerpt_clean` is the same span with layout noise (SCR margin letters, running headers, page numbers,
page markers) blanked out.

Python 3.11+ compatible.
"""
import bisect
import difflib
import hashlib
import re

VERSION = "c12-holdings/1.0.0"
STATUS = "AUTOMATED_CANDIDATE_NOT_VERIFIED"
VERIFICATION = "NOT_VERIFIED_RATIO_NOT_DETERMINED"
EXCERPT_CAP = 900

ITEM_TYPES = ["question_of_law", "holding", "reasoning", "obiter_candidate", "operative_direction",
              "quoted_precedent", "submission", "lower_court_finding"]

# Thresholds (tuned in-sample on the dev set; see DEV_EVALUATION_HOLDINGS.md)
T_HOLDING = 4
T_REASONING = 1
T_NONCOURT_EMIT = 2

PAGE_RE = re.compile(r"\[\[page (\d+)\]\]")


# ------------------------------------------------------------------ basic helpers
def squash(s, limit=None):
    s = re.sub(r"\s+", " ", s).strip()
    if limit and len(s) > limit:
        s = s[:limit].rstrip() + " ..."
    return s


def page_index(text):
    return [(m.start(), int(m.group(1))) for m in PAGE_RE.finditer(text)]


def page_at(pidx, pos):
    p = pidx[0][1] if pidx else None
    lo, hi = 0, len(pidx) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if pidx[mid][0] <= pos:
            p = pidx[mid][1]
            lo = mid + 1
        else:
            hi = mid - 1
    return p


def norm_alnum(s):
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def item_id(judgment_id, cs, ce, itype):
    return "HC12-" + hashlib.sha256(("%s:%d:%d:%s" % (judgment_id, cs, ce, itype)).encode()).hexdigest()[:14]


# ------------------------------------------------------------------ layout noise mask
_MARGIN_LINE_RE = re.compile(r"^[ \t]*[A-Ha-h~;:.,\-·'\"`_|/\\*•]{1,3}[ \t]*$")
_NUM_LINE_RE = re.compile(r"^[ \t]*[\[(]?\d{1,4}[\])]?[ \t]*$")
_SCR_HDR_RE = re.compile(r"SUPREME\s+COURT\s+REPORTS|S\.\s?C\.\s?R\.?\s*$|^\s*\[\s*(?:19|20)\d{2}\s*[\])]\s*\d{0,2}\s*(?:Suppl?\.?\s*)?S\.?\s?C\.?\s?R", re.I)
_RUNNING_HDR_RE = re.compile(r"^[^\n]{2,110}\bv\.?\s[^\n]{2,110}$|\[[A-Z][A-Za-z.\s]+,\s*(?:C\.\s*)?J\.?[\])]", re.I)
_JUDGE_HDR_RE = re.compile(r"\[\s*((?:DR\.?\s*)?[A-Z][A-Za-z.\s'\-]{2,50}?),\s*(?:C\.\s*)?J\.?\s*[\])]")


def _upper_ratio(s):
    letters = [c for c in s if c.isalpha()]
    return sum(1 for c in letters if c.isupper()) / float(len(letters)) if letters else 0.0


def noise_mask(text):
    """Return (masked_text, header_judges) where layout-noise lines are replaced by spaces (same length).

    header_judges: list of (pos, judge_name) for SCR running headers that name the opinion's author.
    """
    out = list(text)
    header_judges = []
    lines = []
    pos = 0
    for ln in text.split("\n"):
        lines.append((pos, ln))
        pos += len(ln) + 1
    # repeated short lines (running headers / footers)
    counts = {}
    for _, ln in lines:
        k = norm_alnum(ln)
        if 3 <= len(k) <= 110:
            counts[k] = counts.get(k, 0) + 1
    page_line_no = 99
    for start, ln in lines:
        blank = False
        st = ln.strip()
        if PAGE_RE.search(ln):
            page_line_no = 0
            blank = True
        elif not st:
            continue
        else:
            page_line_no += 1
            k = norm_alnum(ln)
            if _MARGIN_LINE_RE.match(ln) or _NUM_LINE_RE.match(ln):
                blank = True
            elif len(st) <= 120 and _SCR_HDR_RE.search(st):
                blank = True
            elif len(st) <= 130 and page_line_no <= 14 and _RUNNING_HDR_RE.search(st) and not st.endswith((".", ",", ";", ":")) \
                    and not re.search(r"\b(?:is|was|are|were|has|had|held|that|observed|this)\b", st) and _upper_ratio(st) >= 0.6:
                blank = True
            elif 3 <= len(k) <= 110 and counts.get(k, 0) >= 3 and len(st) <= 120 and not re.match(r"^\(?[ivx0-9]+[.)]", st):
                blank = True
            if blank:
                m = _JUDGE_HDR_RE.search(st)
                if m:
                    header_judges.append((start, squash(m.group(1)).upper()))
        if blank:
            for i in range(start, start + len(ln)):
                out[i] = " "
    return "".join(out), header_judges


# ------------------------------------------------------------------ judgment body boundaries
_START_RES = [
    ("ESCR_JUDGMENT_ORDER_BANNER", re.compile(r"Judgment\s*/\s*Order\s+of\s+the\s+Supreme\s+Court")),
    ("DELIVERED_BY", re.compile(r"(?:Judgments?|Order|following\s+(?:Judgments?|Order)s?)\s+(?:of\s+the\s+Court\s+)?(?:was|were)\s+delivered(?:\s+by)?\s*[:.\-]?", re.I)),
    ("DELIVERED_BY_LOOSE", re.compile(r"\b(?:was|were)\s+delivered\s+by\b", re.I)),
    ("JUDGMENT_HEADING", re.compile(r"(?m)^[ \t]*(?:J\s*U\s*D\s*G\s*M\s*E\s*N\s*T|JUDGMENT|O\s*R\s*D\s*E\s*R|ORDER|COMMON\s+JUDGMENT|COMMON\s+ORDER)[ \t]*[.:]?[ \t]*$")),
]
_HEADNOTE_RE = re.compile(r"\bHELD\s*[:;]|Case\s+Law\s+Reference|APPELLATE\s+JURISDICTION|ORIGINAL\s+JURISDICTION|Headnotes?\b|S\.C\.R\.|SUPREME\s+COURT\s+REPORTS", re.I)
_COUNSEL_END_RE = re.compile(r"(?:Advs?|Advocates?)\.?\s+for\s+the\s+(?:Respondents?|Appellants?|Petitioners?|parties|State|Union)[^\n]{0,60}\.?[ \t]*\n", re.I)
_END_RES = [
    re.compile(r"(?m)^[ \t]*Headnotes?\s+prepared\s+by", re.I),
    re.compile(r"(?m)^[ \t]*Result\s+of\s+the\s+case\s*:", re.I),
    re.compile(r"(?m)^[ \t]*(?:[A-Z][A-Za-z.\s]{0,40}\n[ \t]*)?(?:Civil\s+|Criminal\s+|Writ\s+|Special\s+Leave\s+|Transfer(?:red)?\s+)?(?:Appeals?|Petitions?|Writ\s+Petitions?|Cases?|Matters?|Reference)\s+(?:partly\s+|partially\s+)?(?:allowed|dismissed|disposed\s+of|answered|rejected)[^\n]{0,60}$", re.I),
]


_JURIS_RE = re.compile(r"J\s?U\s?R\s?I\s?S\s?D\s?I\s?C\s?T\s?I\s?O\s?N\s*[:;.]?")
_COUNSEL_LOOSE_RE = re.compile(r"\bfor\s+the\s+(?:Respondents?|Appellants?|Petitioners?|State|Union|parties|Interveners?|Applicants?)\b[^\n]{0,60}\.?[ \t]*\n", re.I)


def find_body(text, mt, court):
    """Return (start, end, start_method, headnote_present)."""
    n = len(mt)
    is_sc = "supreme" in (court or "").lower()
    head = mt[:min(n, 60000)]
    headnote = bool(_HEADNOTE_RE.search(head)) and is_sc
    start, method = 0, "DOCUMENT_START"
    for name, rx in _START_RES:
        m = rx.search(mt)
        if not m:
            continue
        if name == "JUDGMENT_HEADING" and m.start() < 200 and not headnote:
            # heading at the very top of a court copy: body starts after it
            start, method = m.end(), name
            break
        if name == "JUDGMENT_HEADING" and headnote:
            # in SCR renditions a bare heading may appear in the headnote; require it after the counsel block
            cm = None
            for cm in _COUNSEL_END_RE.finditer(mt[:min(n, 120000)]):
                pass
            if cm and m.start() < cm.end():
                m2 = rx.search(mt, cm.end())
                if not m2:
                    continue
                m = m2
        start, method = m.end(), name
        break
    if method == "DOCUMENT_START" and headnote:
        jm = _JURIS_RE.search(mt, 0, min(n, 150000))
        frm = jm.end() if jm else 0
        cm = None
        for cm in _COUNSEL_LOOSE_RE.finditer(mt, frm, min(n, frm + 8000 if jm else 150000)):
            pass
        if cm:
            start, method = cm.end(), "AFTER_COUNSEL_BLOCK"
        elif jm:
            nl = mt.find("\n\n", jm.end())
            start, method = (nl if nl > 0 else jm.end()), "AFTER_JURISDICTION_LINE"
        else:
            method = "HEADNOTE_SUSPECTED_NO_START_FOUND"
    end = n
    tail_from = start + int((n - start) * 0.6)
    for rx in _END_RES:
        for m in rx.finditer(mt, tail_from):
            if m.start() < end:
                end = m.start()
            break
    return start, end, method, headnote


# ------------------------------------------------------------------ opinions
_AUTHOR_LINE_RE = re.compile(
    r"(?m)^[ \t]*(?:HON'?BLE\s+)?(?:(?:MR|MRS|MS)\.?\s+)?(?:JUSTICE\s+)?"
    r"((?:DR\.?\s*)?[A-Z][A-Za-z.'\-]*(?:[ \t]+[A-Z][A-Za-z.'\-]*){0,5}?)[ \t]*,?[ \t]*(C\.?[ \t]*J\.?(?:I\.?)?|J\.?)"
    r"[ \t]*(?:\(([^)\n]{0,40})\))?[ \t]*[:.\-–]?[ \t]*$")
_AUTHOR_INLINE_RE = re.compile(r"(?m)^[ \t]*((?:DR\.?\s*)?[A-Z][A-Z.'\-]+(?:[ \t]+[A-Z][A-Z.'\-]+){0,4}),[ \t]*(C\.[ \t]*J\.|J\.)[ \t]*(?:[\-–—:][ \t]*|[ \t])(?=[A-Z\"“(])")
_NOT_NAME = re.compile(r"^(?:THE|IN|OF|AND|FOR|ON|BY|TO|AT|WITH|UNDER|SECTION|RULE|ARTICLE|PARA|NO|NOS|ADVS?|ADVOCATES?|SR|COUNSEL|"
                       r"APPELLANT|RESPONDENT|PETITIONER|UNION|STATE|INDIA|HELD|JUDGMENT|ORDER|NOTE|VERSUS|VS)\b", re.I)
_SEPARATE_CUE_RE = re.compile(r"\bI\s+have\s+had\s+the\s+(?:advantage|benefit|privilege|opportunity)|\bI\s+(?:agree|concur|entirely\s+agree|respectfully\s+agree)"
                              r"|\bmy\s+(?:learned|esteemed|noble)\s+(?:brother|sister|colleague)|\bconcurring\b|\bI\s+(?:would|wish\s+to)\s+(?:add|say)", re.I)
_DISSENT_CUE_RE = re.compile(r"\bI\s+(?:regret|am\s+unable|find\s+myself\s+unable|have\s+not\s+been\s+able)\s+to\s+(?:agree|concur|share|subscribe|persuade\s+myself)"
                             r"|\b(?:my|this)\s+dissent\b|\bdissenting\b|\bI\s+respectfully\s+(?:disagree|differ)|\bcannot\s+(?:agree|concur)\s+with\s+(?:my|the\s+majority)", re.I)
_SIGNATURE_RE = re.compile(r"(?m)^[ \t]*(?:\.{4,}|…{2,}|_{4,})[^\n]{0,30}(?:C\.?\s*)?J\.?|^[ \t]*\(\s*[A-Z][A-Za-z.\s]{3,50}\)\s*$")


def _clean_name(s):
    return squash(re.sub(r"[.,]+$", "", s)).upper()


def _same_judge(a, b):
    """Fuzzy equality of two printed judge names (OCR variants such as 'AGRA WAL'/'AGRAWAL', 'TIIOMMEN'/'THOMMEN')."""
    ta = set(w for w in re.findall(r"[A-Z]{4,}", (a or "").upper()))
    tb = set(w for w in re.findall(r"[A-Z]{4,}", (b or "").upper()))
    if ta & tb:
        return True
    na = re.sub(r"[^A-Z]", "", (a or "").upper())
    nb = re.sub(r"[^A-Z]", "", (b or "").upper())
    if not na or not nb:
        return False
    if na in nb or nb in na:
        return True
    return difflib.SequenceMatcher(None, na, nb).ratio() >= 0.75


def _header_change_opinions(ops, header_judges, start, end, page_starts):
    """SCR running headers name the author of the opinion on that page. A persistent change of name with no
    author line nearby starts a new opinion (start approximate: the beginning of the preceding page)."""
    runs = []
    for pos, name in header_judges:
        if not (start <= pos < end):
            continue
        if runs and _same_judge(runs[-1][1], name):
            runs[-1][2] += 1
        else:
            runs.append([pos, name, 1])
    out = list(ops)
    for k, (pos, name, cnt) in enumerate(runs):
        if cnt < 2 and k != len(runs) - 1:
            continue
        prev_pages = [p for p in page_starts if p < pos]
        approx = prev_pages[-2] if len(prev_pages) >= 2 else (prev_pages[-1] if prev_pages else pos)
        approx = max(approx, start)
        if any(_same_judge(o["author"], name) and o["start"] <= pos for o in out):
            continue
        if any(abs(o["start"] - pos) < 9000 for o in out):
            continue
        if not out and k == 0:
            continue
        out.append({"start": approx, "body": approx, "author": name, "method": "HEADER_JUDGE_CHANGE_APPROX_START", "note": ""})
    out.sort(key=lambda o: o["start"])
    return out


def find_opinions(mt, start, end, header_judges, page_starts=None):
    """Return list of dicts: {start, end, author, label, method, cues}."""
    cands = []
    for rx, kind in ((_AUTHOR_LINE_RE, "LINE"), (_AUTHOR_INLINE_RE, "INLINE")):
        for m in rx.finditer(mt, start, end):
            name = m.group(1).strip()
            if _NOT_NAME.match(name) or len(norm_alnum(name)) < 3:
                continue
            if kind == "LINE":
                linetxt = mt[m.start():m.end()]
                if "[" in linetxt or ".." in linetxt or "…" in linetxt:
                    continue
                # a standalone author line must be short and mostly the name
                if len(linetxt.strip()) > 70:
                    continue
            cands.append((m.start(), m.end(), _clean_name(name), kind, (m.group(3) or "") if kind == "LINE" else "", name))
    cands.sort()
    # dedupe overlapping
    ded = []
    for c in cands:
        if ded and c[0] < ded[-1][1]:
            continue
        ded.append(c)
    ops = []
    for c in ded:
        if not ops:
            if c[0] - start > min(6000, 0.25 * (end - start)):
                continue
            ops.append({"start": c[0], "body": c[1], "author": c[2], "method": "AUTHOR_" + c[3], "note": c[4]})
            continue
        prev = ops[-1]
        if c[0] - prev["body"] < 1500 or _same_judge(prev["author"], c[2]):
            continue
        before = mt[max(prev["body"], c[0] - 3000):c[0]]
        after = mt[c[1]:min(end, c[1] + 6000)]
        sig_before = bool(_SIGNATURE_RE.search(before)) or bool(re.search(r"(?m)^[ \t]*[A-Z][A-Za-z.\s]{2,40},?\s*(?:C\.\s*)?J\.?\s*$", before[-400:]))
        strong_cue = bool(_SEPARATE_CUE_RE.search(after[:3000]) or _DISSENT_CUE_RE.search(after[:3000]))
        first_person = strong_cue or bool(re.search(r"\bI\s+(?:am|have|would|think|hold|find|do|may|shall|must)\b", after[:3000]))
        letters = [ch for ch in c[5] if ch.isalpha()]
        all_caps = bool(letters) and all(ch.isupper() for ch in letters)
        scr_dash = c[3] == "INLINE" and bool(re.search(r"J\.[ \t]*[\-–—:]", mt[c[0]:c[1]]))
        if ((sig_before or c[4]) and first_person) or (c[3] == "INLINE" and (first_person or scr_dash)) or (all_caps and first_person) or strong_cue:
            ops.append({"start": c[0], "body": c[1], "author": c[2], "method": "AUTHOR_" + c[3], "note": c[4]})
    ops = _header_change_opinions(ops, header_judges, start, end, page_starts or [])
    if not ops:
        author = header_judges[0][1] if header_judges else ""
        ops = [{"start": start, "body": start, "author": author,
                "method": "HEADER_JUDGE" if author else "OPINION_NOT_IDENTIFIED", "note": ""}]
    else:
        ops[0]["start"] = start
    for i, o in enumerate(ops):
        o["end"] = ops[i + 1]["start"] if i + 1 < len(ops) else end
    if len(ops) == 1:
        ops[0]["label"] = "sole"
    else:
        for i, o in enumerate(ops):
            seg = mt[o["body"]:min(o["end"], o["body"] + 3000)]
            note = o.get("note", "").lower()
            if i == 0:
                o["label"] = "lead"
            elif "dissent" in note or _DISSENT_CUE_RE.search(seg):
                o["label"] = "dissent"
            else:
                o["label"] = "separate"
    return ops


# ------------------------------------------------------------------ paragraphs
_PARA_CAND_RE = re.compile(r"(?m)^[ \t]*\(?(\d{1,3})[ \t]*(?:\.(?!\d)|\)|(?=[ \t]+[A-Z\"“(]))[ \t]*(?:\n[ \t]*)?(?=\S)")


def find_paragraphs(mt, opinions):
    """Return sorted list of (pos, number, opinion_index). Numbered paragraphs with a sequence constraint."""
    out = []
    for oi, o in enumerate(opinions):
        last = 0
        for m in _PARA_CAND_RE.finditer(mt, o["start"], o["end"]):
            n = int(m.group(1))
            if n == last + 1 or (last == 0 and n in (1, 2)) or (last > 0 and n == last + 2 and n < 400):
                out.append((m.start(), n, oi))
                last = n
    return out


def para_at(paras, pos):
    cur = None
    lo, hi = 0, len(paras) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if paras[mid][0] <= pos:
            cur = paras[mid]
            lo = mid + 1
        else:
            hi = mid - 1
    return cur


# ------------------------------------------------------------------ section headings
_HEADING_KINDS = [
    ("ISSUES", r"ISSUES?|QUESTIONS?(?:\s+OF\s+LAW)?|POINTS?\s+FOR\s+(?:DETERMINATION|CONSIDERATION)|ISSUES?\s+(?:FOR|BEFORE|ARISING|INVOLVED|RAISED)[A-Z\s]*|QUESTIONS?\s+(?:FOR|BEFORE|ARISING|INVOLVED|REFERRED)[A-Z\s]*|THE\s+(?:REFERENCE|ISSUES?|QUESTIONS?)"),
    ("SUBMISSIONS", r"SUBMISSIONS?[A-Z\s,&]*|ARGUMENTS?[A-Z\s,&]*|CONTENTIONS?[A-Z\s,&]*|RIVAL\s+(?:SUBMISSIONS|CONTENTIONS)|(?:THE\s+)?CASE\s+OF\s+THE\s+[A-Z\s]+|STAND\s+OF\s+[A-Z\s]+"),
    ("FACTS", r"(?:THE\s+)?FACTS?[A-Z\s,&]*|(?:FACTUAL\s+)?BACKGROUND[A-Z\s]*|BRIEF\s+FACTS|PROCEDURAL\s+HISTORY|THE\s+CHALLENGE|PREFACE|INTRODUCTION"),
    ("FRAMEWORK", r"(?:THE\s+)?(?:STATUTORY|LEGAL|REGULATORY)\s+(?:FRAMEWORK|PROVISIONS|SCHEME|POSITION)[A-Z\s]*|RELEVANT\s+(?:PROVISIONS|RULES|STATUTORY)[A-Z\s]*"),
    ("ANALYSIS", r"ANALYSIS[A-Z\s,&]*|DISCUSSION[A-Z\s,&]*|CONSIDERATION[A-Z\s,&]*|REASONS?[A-Z\s,&]*|(?:OUR\s+)?(?:VIEW|FINDINGS?)[A-Z\s,&]*|EVALUATION|ADJUDICATION|ASSESSMENT|DETERMINATION|PRECEDENTS?[A-Z\s]*"),
    ("CONCLUSION", r"CONCLUSIONS?[A-Z\s,&]*|SUMMARY\s+OF\s+(?:CONCLUSIONS|FINDINGS)|RESULT|(?:OPERATIVE\s+)?DIRECTIONS?|RELIEF|EPILOGUE|BEFORE\s+PARTING|THE\s+WAY\s+FORWARD|SUMMATION"),
]
_HEADING_RES = [(k, re.compile(r"^[ \t]*(?:(?:[A-Z]|[IVXLC]+|\d{1,2})[.)][ \t]+|\([a-zA-Z0-9]{1,4}\)[ \t]+)?(?:" + p + r")[ \t]*[:.\-–]?[ \t]*$", re.I)) for k, p in _HEADING_KINDS]


_CONT_WORDS = set("of the and to in for on by with a an or that which from at as".split())
_SECTION_DECAY = {"FACTS": 6000, "SUBMISSIONS": 8000, "ISSUES": 5000, "FRAMEWORK": 8000}


def find_headings(mt, start, end):
    out = []
    pos = start
    for ln in mt[start:end].split("\n"):
        st = ln.strip()
        words = st.split()
        letters = [c for c in st if c.isalpha()]
        is_upper = bool(letters) and all(c.isupper() for c in letters)
        title_like = len(words) <= 6 and words and words[-1].lower().strip(".:") not in _CONT_WORDS \
            and all(w[0].isupper() for w in words if len(w) > 3 and w.isalpha())
        if 3 <= len(st) <= 80 and not st.endswith((",", ";")) and st[0].isupper() and (is_upper or title_like):
            for k, rx in _HEADING_RES:
                if rx.match(st):
                    out.append((pos, k, st))
                    break
        pos += len(ln) + 1
    return out


def section_at(headings, pos):
    """Section kind in force at pos. FACTS/SUBMISSIONS/ISSUES/FRAMEWORK headings lapse after a fixed distance."""
    cur = None
    for h in headings:
        if h[0] <= pos:
            cur = h
        else:
            break
    if not cur:
        return ""
    lim = _SECTION_DECAY.get(cur[1])
    if lim and pos - cur[0] > lim:
        return ""
    return cur[1]


# ------------------------------------------------------------------ quotations
_QUOTE_INTRO_RE = re.compile(
    r"(?:observed|held|holds|stated|said|opined|laid\s+down|ruled|reads?|read\s+as|as\s+under|as\s+follows|following\s+(?:terms|words|effect|"
    r"observations?|passages?|paragraphs?)|extracted|reproduced|quoted|provides?|provided|in\s+these\s+terms|runs\s+as|thus|"
    r"to\s+the\s+following\s+effect|is\s+as\s+below|below|hereunder|explained|noticed|enunciated|declared|summari[sz]ed)\s*(?:that)?\s*[:\-–—]+\s*$", re.I)
_CASE_CUE_RE = re.compile(r"\b(?:v\.|vs\.?|versus)\s|\bSCC\b|S\.\s?C\.\s?R|\bSCR\b|\bAIR\b|\bSCALE\b|\bINSC\b|\(supra\)|\bsupra\b|this\s+Court\s+(?:in|has|had|held|observed)|"
                          r"Constitution\s+Bench|(?:three|two|five|seven|nine)[\-\s]Judge|Bench\s+(?:of|in)|\bLord\b|\bJ\.\s|\bJJ\.|decision\s+in|judgment\s+in|case\s+of|"
                          r"\bin\s+[A-Z][A-Za-z.]+(?:\s+[A-Z][A-Za-z.]+){0,4}\s*\(|\bcase\b", re.I)
_STATUTE_CUE_RE = re.compile(r"\b(?:section|rule|regulation|article|clause|para(?:graph)?|sub-section|proviso|schedule|notification|act|rules|regulations|"
                             r"code|provision|policy|letter|circular|instructions?|order\s+dated|memorandum|amendment)\b", re.I)
_LOWER_CUE_RE = re.compile(r"\b(?:tribunal|AFT|High\s+Court|impugned|Single\s+Judge|Division\s+Bench|trial\s+court|court[\s\-]martial|GCM|SCM|DCM|"
                           r"medical\s+board|appellate\s+authority|competent\s+authority|confirming\s+authority|charge[\s\-]sheet|order\s+of\s+the)\b", re.I)
_SUBM_CUE_RE = re.compile(r"\b(?:counsel|submission|contended|submitted|argued|urged|written\s+submissions?|counter[\s\-]affidavit|affidavit|petition|"
                          r"grounds?\s+of\s+appeal|reply)\b", re.I)
_OPEN_Q = "“\""
_CLOSE_Q = "”\""


def _quote_kind(intro):
    """Kind of a quotation from its introduction: the cue closest to the opening wins."""
    intro = intro[-350:]
    best, kind = -1, "quoted_other"
    for rx, k in ((_STATUTE_CUE_RE, "statutory_or_document_quotation"), (_LOWER_CUE_RE, "lower_court_quotation"),
                  (_CASE_CUE_RE, "quoted_precedent"), (_SUBM_CUE_RE, "submission_quotation")):
        last = None
        for last in rx.finditer(intro):
            pass
        if last is not None and last.start() >= best:
            best, kind = last.start(), k
    return kind


def _soft_end(mt, s, limit, para_starts):
    """End of an unclosed quotation: next numbered paragraph, or a blank-line break after a sentence end."""
    hard = min(len(mt), s + limit)
    for p in para_starts:
        if s < p < hard:
            hard = p
            break
    for m in re.finditer(r"[.?!:][\"'”’)\]]*[ \t]*\n(?:[ \t]*\n)+[ \t]*(?=[A-Z])", mt[s:hard]):
        cand = s + m.end()
        if cand - s >= 60:
            return cand
    return hard


_OWN_LINE_PIVOT_RE = re.compile(
    r"\n[ \t]*(?:\(?\d{1,3}[.)][ \t]*\n?[ \t]*)?(?:We\s+(?:are|have|find|hold|do|would|may|must|agree|see|cannot|think|accordingly|therefore)\b|"
    r"In\s+(?:our|this\s+view|the\s+light|view\s+of\s+(?:the\s+)?(?:above|this|that|what|the\s+foregoing))|Thus\b|Therefore\b|Hence\b|Accordingly\b|"
    r"In\s+the\s+(?:present|instant)\s+case|Having\s+(?:regard|considered|heard)|For\s+the\s+(?:reasons|foregoing))")


def find_quotes(mt, start, end, para_starts):
    """Return sorted list of (qs, qe, kind)."""
    spans = []
    i = start
    curly_open = mt.find("“", start, end) >= 0
    while i < end:
        ch = mt[i]
        if ch == "“" or (ch == '"' and not curly_open and (i == 0 or not mt[i - 1].isalnum())):
            close_ch = "”" if ch == "“" else '"'
            depth, j = 1, i + 1
            limit = min(end, i + 12000)
            nxt_para = next((p for p in para_starts if p > i), None)
            while j < limit:
                c = mt[j]
                if ch == "“" and c == "“":
                    depth += 1
                elif c == close_ch:
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            if j < limit and (nxt_para is None or j < nxt_para + 200 or j - i < 6000):
                if j - i >= 150:
                    intro = mt[max(start, i - 500):i]
                    spans.append((i, j + 1, _quote_kind(intro), ch == "“" and j - i < 3000))
                i = j + 1
                continue
            # unclosed: treat a long block-opening quote as a quotation up to a soft end
            line_start = mt.rfind("\n", 0, i) + 1
            if mt[line_start:i].strip() == "" or _QUOTE_INTRO_RE.search(mt[max(start, i - 300):i]):
                qe = _soft_end(mt, i, 4000, para_starts)
                if qe - i >= 150:
                    spans.append((i, qe, _quote_kind(mt[max(start, i - 500):i]), False))
                    i = qe
                    continue
        i += 1
    # intro-colon blocks without quotation marks
    for m in re.finditer(r"[:\-–—][ \t]*\n", mt[start:end]):
        p = start + m.start()
        line_start = mt.rfind("\n", 0, p) + 1
        prev = mt[max(start, line_start - 400):p + 1]
        if not _QUOTE_INTRO_RE.search(prev):
            continue
        k = p + 1
        while k < end and mt[k] in " \t\n":
            k += 1
        if k < end and mt[k] in _OPEN_Q + "“‘'":
            continue
        if any(a <= k < b for a, b, _, _ in spans):
            continue
        qe = _soft_end(mt, k, 3500, para_starts)
        if qe - k >= 120:
            spans.append((k, qe, _quote_kind(prev), False))
    cut = []
    for a, b, kind, reliable in spans:
        if not reliable:
            m = _OWN_LINE_PIVOT_RE.search(mt, a + 1, b)
            if m:
                b = m.start() + 1
        if b - a >= 100:
            cut.append((a, b, kind))
    spans = cut
    spans.sort()
    merged = []
    for s in spans:
        if merged and s[0] < merged[-1][1]:
            if s[1] > merged[-1][1]:
                merged[-1] = (merged[-1][0], s[1], merged[-1][2])
            continue
        merged.append(s)
    return merged


def quote_at(spans, pos):
    lo, hi = 0, len(spans) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        a, b, k = spans[mid]
        if pos < a:
            hi = mid - 1
        elif pos >= b:
            lo = mid + 1
        else:
            return spans[mid]
    return None


# ------------------------------------------------------------------ sentences
_ABBR = set("""v vs no nos s ss r rr sec secs art arts cl cls para paras mr mrs ms dr sh smt shri hon ltd co ors anr j jj cj
sr adv advs govt dept lt col gen maj capt sub hav nk sep ex rs ld vol ch pp p viz i e eg ie cf ibid id st jr fig sl sq
wef w.e.f e.g i.e u.o.i uoi addl dy asst insp supdt cdr wg sqn fl flt offr hony retd regt bn coy inf ph nos. o.a oa m.a ma
w.p wp c.a ca s.l.p slp crl cri civ misc approx etc. al""".split())
_BOUND_RE = re.compile(r"[.?!][\"'”’)\]]*(?=\s+[\"“‘(]?[A-Z0-9(])|;\s*\n(?=\s*\(?[ivx0-9a-z]{1,4}[.)])")


def sentences(mt, start, end, forced):
    """Split mt[start:end] into (s, e) spans. `forced` is a sorted list of positions that always start a sentence."""
    cuts = set(p for p in forced if start < p < end)
    for m in _BOUND_RE.finditer(mt, start, end):
        p = m.start()
        w = re.search(r"([A-Za-z.]+)$", mt[max(start, p - 12):p])
        word = w.group(1).lower().strip(".") if w else ""
        if word in _ABBR or (len(word) == 1 and word.isalpha()):
            continue
        if re.search(r"\b(?:No|Nos|Sec|Art|para|Rule|Section)\s*$", mt[max(start, p - 10):p], re.I) and mt[p] == ".":
            continue
        cuts.add(m.end())
    # blank-line breaks before a capitalised line also end a sentence when the previous char ends a clause
    for m in re.finditer(r"[.?!:;][\"'”’)]*[ \t]*\n[ \t]*\n", mt[start:end]):
        cuts.add(start + m.end())
    pts = sorted(cuts)
    out = []
    prev = start
    for p in pts + [end]:
        s, e = prev, p
        while s < e and mt[s].isspace():
            s += 1
        while e > s and mt[e - 1].isspace():
            e -= 1
        if e - s >= 2:
            out.append((s, e))
        prev = p
    return out


# ------------------------------------------------------------------ classifiers
_SUBMISSION_RE = re.compile(
    r"(?:learned|ld\.?)\s+(?:senior\s+|additional\s+|amicus\s+)?(?:counsel|advocate|solicitor|attorney|amicus|A\.?S\.?G)"
    r"|\b(?:it\s+(?:was|is|has\s+been|had\s+been)\s+(?:also\s+)?(?:submitted|contended|urged|argued|pleaded|canvassed|pointed\s+out|stated|averred))"
    r"|\b(?:submitted|contended|urged|argued|canvassed|submits|contends|urges|argues|pleads|asserts|maintains)\s+(?:that|on|before)\b"
    r"|\bon\s+behalf\s+of\s+the\s+(?:appellants?|respondents?|petitioners?|Union|State)"
    r"|\baccording\s+to\s+(?:the\s+)?(?:learned\s+)?(?:counsel|appellants?|respondents?|petitioners?)"
    r"|\b(?:appellants?|respondents?|petitioners?|Union\s+of\s+India)(?:'s|’s)?\s+(?:contends?|submits?|argues?|urges?|pleads?|claims?|avers?|seeks?)\b"
    r"|\b(?:Additional\s+)?(?:Solicitor|Attorney)\s+General\s+(?:has\s+)?(?:submitted|contended|urged|argued|relied)"
    r"|\b(?:Mr|Ms|Mrs|Shri|Sh)\.?\s+[A-Z][A-Za-z.]+(?:\s+[A-Z][A-Za-z.]+){0,3},?\s+(?:the\s+)?(?:learned|ld|appearing|for\s+the)"
    r"|\bin\s+(?:reply|rejoinder|response),\s+(?:it|the|learned)"
    r"|^\W*(?:\d+\s*[.)]?\s*)?(?:Ld\.?\s+|The\s+)?[Cc]ounsel\s+for\s+the\s+(?:petitioners?|appellants?|respondents?|applicants?|Union|State)\b[^.]{0,60}\b(?:states?|stated|submits?|points?\s+out|contends?|urges?|argues?|prays?|seeks?|relies?|refers?)", re.I)
_PRECEDENT_REPORT_RE = re.compile(
    r"^\W*(?:\d+\s*[.)]?\s*)?(?:Later,?\s+|Again,?\s+|Similarly,?\s+|Further,?\s+|Thereafter,?\s+|Subsequently,?\s+)?(?:In\s+(?:the\s+case\s+of\s+)?[A-Z][^;:]{2,160}?(?:\bv\.|\bvs\.?|\bversus\b|\(supra\)|\d{4}\)?\s+\d+\s+SCC|\bAIR\b|\bSCR\b)[^;:]{0,120}?,\s*)"
    r"(?:the\s+|a\s+|this\s+)?(?:Hon'?ble\s+|Hon’ble\s+)?(?:Supreme\s+Court|Apex\s+Court|Court|Bench|Constitution\s+Bench|(?:two|three|five|seven|nine)[\s\-]Judge\s+Bench|Division\s+Bench|Full\s+Bench|High\s+Court|their\s+Lordships|it|Lord\s+[A-Z]\w+|[A-Z][a-z]+,?\s+J\.)\s+"
    r"(?:has\s+|had\s+|was\s+)?(?:been\s+pleased\s+to\s+)?(?:held|observed|ruled|opined|laid\s+down|reiterated|explained|considered|took|noted|found|declared|stated|said|emphasi[sz]ed|clarified|followed)"
    r"|\bthe\s+principle\s+enunciated\s+in\s+the\s+precedent\s+was\s+followed", re.I)
_REJECT_ACCEPT_RE = re.compile(
    r"\b(?:cannot|can\s*not|could\s+not)\s+be\s+(?:accepted|sustained|countenanced|upheld)|\b(?:is|are)\s+(?:without|devoid\s+of)\s+(?:any\s+)?(?:merit|substance|force)"
    r"|\bhas\s+no\s+(?:merit|force|substance|legs)|\bwe\s+(?:are\s+)?(?:unable|not\s+inclined|not\s+persuaded)\s+to\s+(?:accept|agree)|\bwe\s+(?:cannot|do\s+not)\s+(?:accept|agree)"
    r"|\b(?:is|are)\s+(?:well[\s\-]?founded|untenable|misconceived|misplaced|fallacious|not\s+tenable|tenable)|\bmust\s+(?:fail|succeed)|\bfind(?:s)?\s+(?:no\s+)?(?:force|merit|substance)"
    r"|\bliable\s+to\s+be\s+(?:rejected|accepted)|\bwe\s+(?:agree|accept|reject|concur)|\b(?:rightly|correctly|wrongly)\s+(?:submitted|contended|urged|argued|pointed)"
    r"|\bthere\s+is\s+(?:considerable\s+)?(?:force|merit|substance)\s+in"
    r"|\b(?:is|was|were|are|has\s+been|have\s+been)\s+(?:unable|not\s+able)\s+to\s+(?:establish|demonstrate|show|point|satisfy|rebut|substantiate|dispute|explain)"
    r"|\b(?:could|can)\s+not\s+(?:point|show|establish|dispute|explain)|\bfailed\s+to\s+(?:establish|show|demonstrate|point|prove|rebut)"
    r"|\bcannot\s+be\s+permitted\s+to\s+(?:contend|urge|argue|raise)|\bnot\s+possible\s+to\s+(?:accept|agree|countenance)|\bno\s+(?:merit|substance|force)\s+in\s+the\s+(?:contention|submission|argument)", re.I)
_LOWER_RE = re.compile(
    r"\b(?:the\s+)?(?:learned\s+)?(?:Armed\s+Forces\s+)?(?:Tribunal|AFT|High\s+Court|Single\s+Judge|Division\s+Bench|trial\s+court|Court[\s\-]Martial|GCM|SCM|DCM|"
    r"Medical\s+Board|Release\s+Medical\s+Board|Invaliding\s+Medical\s+Board|appellate\s+authority|competent\s+authority|confirming\s+authority|Commission|"
    r"Court\s+of\s+Inquiry|Board)\s+(?:has\s+|had\s+|in\s+its\s+[a-z\s]+\s+)?(?:held|observed|found|concluded|opined|recorded|noted|rejected|allowed|dismissed|"
    r"came\s+to|took\s+the\s+view|was\s+of\s+the\s+(?:view|opinion)|granted|declined|negatived|accepted|relied|directed|set\s+aside|upheld|reasoned|proceeded)", re.I)
_COURT_ASSESS_RE = re.compile(r"\b(?:rightly|correctly|wrongly|erroneously|erred|right\s+in|justified\s+in|not\s+justified|we\s|our\s|us\b|this\s+Court\s+(?:is|finds|holds))", re.I)
_OWN_PIVOT_RE = re.compile(r"^\W*(?:\d+\s*[.)]?\s*)?(?:We\b|In\s+our\b|In\s+(?:such|the|these)\s+circumstances|Qua\b|It\s+(?:shall|may|must|would)\s+be\s+(?:noted|noticed|seen|relevant)|"
                           r"Further,?\s+it\b|It\s+is\s+(?:also\s+)?(?:pertinent|relevant|necessary|significant|important|noteworthy|not\s+in\s+dispute|an\s+admitted)|A\s+(?:careful|bare|plain)\s+(?:reading|perusal)|"
                           r"A\s+perusal|On\s+(?:a\s+)?(?:careful\s+)?(?:perusal|reading|examination)|Having\s+(?:heard|considered|given)|This\s+Court\b|On\s+(?:a\s+)?(?:careful|consideration|perusal|analysis)|"
                           r"In\s+(?:the\s+)?(?:light|view)\s+of|Thus\b|Therefore\b|Hence\b|Accordingly\b|Consequently\b|It\s+is\s+(?:thus|therefore|clear|evident|apparent|well)|"
                           r"I\s+(?:am|have|would|think|hold|find)|Insofar|As\s+regards|So\s+far\s+as|Coming\s+to|Turning\s+to|Now\b)", re.I)

_STRONG_RE = re.compile(
    r"\bwe\s+(?:would\s+|therefore\s+|accordingly\s+|thus\s+|hence\s+)?(?:hold|declare|answer|conclude|reiterate|clarify)\b|\bit\s+is\s+(?:hereby\s+|accordingly\s+|therefore\s+)?(?:held|declared)\b"
    r"|\bwe\s+(?:are|were)\s+(?:therefore\s+|thus\s+|also\s+|clearly\s+|firmly\s+)?of\s+the\s+(?:considered\s+|clear\s+|firm\s+)?(?:view|opinion)|\bin\s+our\s+(?:considered\s+)?(?:view|opinion|judgment)"
    r"|\bwe\s+(?:have\s+)?no\s+(?:hesitation|doubt)|\bwe\s+(?:are|were)\s+(?:satisfied|convinced|persuaded|inclined|constrained|unable|not\s+inclined|not\s+persuaded)"
    r"|\bwe\s+(?:find|found|see|think|agree|accept|reject|uphold|do\s+not\s+(?:think|find|see|agree|accept)|cannot\s+(?:accept|agree|countenance|hold|say))\b"
    r"|\bit\s+(?:must|should|would|can|cannot|could\s+not)\s+(?:therefore\s+)?be\s+(?:held|said|concluded|stated|presumed|inferred|assumed)|\bit\s+cannot\s+be\s+said"
    r"|\bthe\s+answer\s+(?:to|is|must)|\bthe\s+(?:legal\s+)?(?:position|law)\s+(?:is|has\s+been)\s+(?:well[\s\-]?)?(?:settled|clear|that)|\bit\s+is\s+(?:well[\s\-]?)?settled"
    r"|\bit\s+is\s+(?:thus\s+|therefore\s+|now\s+|hence\s+)?(?:clear|evident|apparent|manifest|obvious|plain|beyond\s+doubt|axiomatic|trite)\b|\bthere\s+(?:is|can\s+be)\s+no\s+(?:doubt|dispute|merit|substance|infirmity|illegality|error|reason)"
    r"|\bfor\s+(?:all\s+)?(?:the|these)\s+(?:foregoing\s+|above\s+|aforesaid\s+)?reasons|\bin\s+(?:the\s+)?(?:light|view)\s+of\s+(?:the\s+)?(?:above|foregoing|aforesaid|discussion|what)"
    r"|\bmakes?\s+it\s+(?:abundantly\s+|amply\s+)?clear|\bleaves?\s+no\s+(?:manner\s+of\s+|room\s+for\s+)?doubt|\b(?:demonstrates?|shows?|indicates?)\s+that\b|\bit\s+is\s+the\s+duty\s+of"
    r"|\bthere\s+is\s+a\s+(?:clear\s+|marked\s+|fundamental\s+)?(?:difference|distinction)\s+between|\bdeem\s+it\s+(?:just|appropriate|fit|proper|necessary)|\bwe\s+make\s+it\s+clear"
    r"|\bin\s+(?:the\s+)?result\b|\bthe\s+(?:inevitable|only|irresistible)\s+(?:conclusion|inference)|\bwe\s+must\s+(?:hold|conclude|observe|note)|\bwe\s+(?:may|would)\s+hold", re.I)
_CONNECT_RE = re.compile(r"\b(?:therefore|thus|hence|accordingly|consequently|clearly|necessarily|in\s+other\s+words|it\s+follows)\b", re.I)
_NORMATIVE_RE = re.compile(
    r"\b(?:is|are|was|were|would\s+be|will\s+be|shall\s+be)\s+(?:not\s+|also\s+|thus\s+|therefore\s+|clearly\s+)?(?:entitled|liable|bound|required|obliged|empowered|competent|eligible|"
    r"applicable|attracted|maintainable|sustainable|vitiated|void|illegal|invalid|valid|arbitrary|unreasonable|discriminatory|ultra\s+vires|mandatory|directory|"
    r"permissible|impermissible|justified|unjustified|lawful|unlawful|binding|final|conclusive|barred|precluded|disproportionate|contrary\s+to)\b"
    r"|\b(?:cannot|can\s*not|could\s+not|must|shall|has\s+to|have\s+to|had\s+to|ought\s+to|need\s+not|would\s+not|may\s+not|should\s+not|should)\s+(?:not\s+)?(?:be|have|act|exercise|apply|"
    r"extend|override|operate|take|deny|defeat|claim|seek|insist|interfere|stand|survive|prevail|form|confer|give)\b"
    r"|\bcontrary\s+to\s+law|\bwithout\s+(?:jurisdiction|authority\s+of\s+law)|\bviolat(?:es|ed|ive|ion)|\binfring|\bset\s+aside|\bunsustainable|\bnot\s+sustainable"
    r"|\battributable\s+to|\baggravated\s+by|\bpresum(?:e|ed|ption)|\bonus\b|\bburden\s+of|\bbenefit\s+of\s+(?:the\s+)?doubt|\bdrastic|\bper\s+incuriam|\bratio\b|\bbinding\s+precedent"
    r"|\bjurisdiction\b|\bmandate\b|\bconstru(?:e|ed|ction)|\binterpret(?:ed|ation)|\bmeaning\s+of|\bscope\s+of|\bpurport\b|\bintention\s+of\s+the\s+legislature|\bwill\s+prevail"
    r"|\bought\s+(?:not\s+)?to\b|\b(?:does|do|did|would|will)\s+not\s+(?:call|qualify|constitute|apply|arise|survive|lie|entitle|confer|amount|vitiate|warrant|justify|suffer|disclose|"
    r"make\s+out|attract|get|render|absolve|affect|extend|cover|bar|preclude)\b|\bcall\s+for\s+(?:any\s+)?interference|\bno\s+(?:interference|infirmity|illegality|perversity|error|irregularity)\b"
    r"|\bfallen\s+(?:into|in)\s+(?:an?\s+)?error|\berred\b|\berror\s+(?:of\s+law|apparent)|\b(?:fully|squarely|clearly)?\s*covered\s+by|\bcannot\s+(?:be\s+)?fault"
    r"|\b(?:is|are|was|were)\s+held\b|\bheld\s+(?:to\s+be\s+)?entitled|\b(?:shall|will|would|must|can|could|may)\s+(?:not\s+)?be\s+(?:presumed|deemed|treated|construed|read|limited|terminated|"
    r"considered|regarded|invoked|exercised|dismissed|discharged|denied|granted|allowed|interfered|entertained|faulted|said|held|sustained|upheld|quashed)\b"
    r"|\bshockingly\b|\bnot\s+a\s+(?:ground|right|bar)\b|\bcannot\s+(?:now\s+)?(?:turn\s+around|challenge|claim|seek|be\s+permitted|contend|insist)|\bintelligible\s+differentia"
    r"|\binfract|\b(?:perfectly|wholly|entirely)\s+(?:legal|valid|justified|illegal)|\bestopp|\bwaive|\bacquiesc|\bno\s+cogent|\blaches|\bres[\s\-]?(?:integra|judicata)"
    r"|\b(?:is|are|was|were)\s+(?:not\s+)?(?:a\s+)?(?:right|privilege|condition\s+precedent|sine\s+qua\s+non|pre-?requisite)\b|\bconnotation|\bdefin(?:ition|ed)\b"
    r"|\bextremely\s+restricted|\blimited\s+(?:scope|jurisdiction|to\s+the\s+extent)|\bno\s+(?:case|ground)\s+(?:is\s+|has\s+been\s+)?made\s+out"
    r"|\bproportional|\bnatural\s+justice|\bdue\s+process|\bArticle\s+(?:14|16|21|33|32|136|142|226|227)\b|\bnot\s+open\s+to|\bno\s+(?:power|authority|jurisdiction)", re.I)
_STATREF_RE = re.compile(r"\b(?:section|sections|sec\.|ss?\.|rule|rules|regulation|regulations|reg\.|article|art\.|para(?:graph)?|clause|sub-section|proviso)\s*\(?\d+[A-Z]?\b"
                         r"|\b(?:Army|Air\s+Force|Navy)\s+Act\b|\bArmy\s+Rules\b|\bEntitlement\s+Rules\b|\bPension\s+Regulations\b|\bArmed\s+Forces\s+Tribunal\s+Act\b|\bAFT\s+Act\b"
                         r"|\bConstitution\b|\bRegulations\s+for\s+the\s+Army\b|\bCr\.?\s?P\.?\s?C|\bI\.?P\.?C\b|\bPenal\s+Code\b|\bEvidence\s+Act\b|\bGuide\s+to\s+Medical\s+Officers\b", re.I)
_LEGAL_CONCEPT_RE = re.compile(r"\b(?:court[\s\-]martial|summary\s+court|disability\s+(?:pension|element)|invalid(?:ed|ment)|release\s+medical|medical\s+board|"
                               r"discharge|dismissal|pension|attributab|aggravat|tribunal|jurisdiction|appeal|writ|review|sentence|punishment|confirmation|"
                               r"service|commission|promotion|seniority|reinstatement|arrears|interest|natural\s+justice|bias|evidence|charge)\b", re.I)
_FACT_RE = re.compile(r"\b(?:was|were)\s+(?:enrolled|recruited|commissioned|posted|born|married|attached|sent|detailed|admitted|hospitali[sz]ed|placed|brought|"
                      r"tried|arrested|charged|convicted|discharged|dismissed|invalided|released|promoted|transferred|granted|issued|served|convened|assembled|"
                      r"heard|examined|filed|preferred|instituted|rejected|forwarded|conducted)\b|\b(?:joined|filed|preferred|approached|submitted\s+(?:a|an|his|her)\s+"
                      r"(?:representation|application|appeal|petition))\b", re.I)
_DATE_RE = re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-](?:19|20)?\d{2}\b|\b\d{1,2}(?:st|nd|rd|th)?\s+(?:day\s+of\s+)?(?:January|February|March|April|May|June|July|August|"
                      r"September|October|November|December)[,\s]+(?:19|20)\d{2}|\b(?:January|February|March|April|May|June|July|August|September|October|November|"
                      r"December)\s+\d{1,2},?\s+(?:19|20)\d{2}", re.I)
_PROCEDURAL_RE = re.compile(r"^\W*(?:\d+\s*\.?\s*)?(?:Heard|Leave\s+granted|Admit(?:ted)?|Delay\s+condoned|Issue\s+notice|Notice\s+issued|Taken\s+on\s+board|"
                            r"Tag\s+with|List\s+(?:the|after|on)|We\s+have\s+heard|Having\s+heard|Learned\s+counsel\s+for\s+the\s+parties\s+(?:were|have\s+been)\s+heard|"
                            r"Pending\s+applications?|Interlocutory|I\.?A\.?\s+No|The\s+facts|Briefly\s+stated|The\s+brief\s+facts|Facts\s+in\s+brief)", re.I)
_OBITER_RE = re.compile(
    r"\bbefore\s+parting|\bwe\s+(?:may|must|would|should)\s+(?:also\s+)?(?:add|observe|mention|clarify|note|record|place\s+on\s+record|express)\b|\bin\s+passing\b|\bby\s+way\s+of\s+(?:an?\s+)?(?:obiter|postscript|caution)"
    r"|\bwe\s+(?:leave|keep)\s+(?:the\s+|this\s+|that\s+)?(?:question|issue|point|aspect)s?\s+open|(?:question|issue|point)s?\s+(?:is|are)\s+(?:kept|left)\s+open|\bleft\s+open\b"
    r"|\b(?:need|do)\s+not\s+(?:go\s+into|decide|express|examine|consider|dilate|enter\s+into|pronounce)|\bnot\s+necessary\s+(?:for\s+us\s+)?to\s+(?:decide|go\s+into|express|examine|consider|deal|answer|pronounce)"
    r"|\bwe\s+(?:express|expressed|have\s+expressed)\s+no\s+(?:opinion|view)|\bwithout\s+expressing\s+any\s+(?:opinion|view)|\bwe\s+(?:would\s+)?(?:like|wish)\s+to\s+(?:observe|add|emphasi[sz]e|place)"
    r"|\bwe\s+(?:hope|trust|expect|urge|recommend|commend|suggest|impress\s+upon)\b|\bit\s+is\s+(?:high\s+)?time\s+(?:that\s+)?|\bwe\s+are\s+(?:conscious|mindful|pained|constrained\s+to\s+observe)", re.I)
_OPERATIVE_RE = re.compile(
    r"\b(?:appeals?|petitions?|writ\s+petitions?|applications?|O\.?A\.?s?|review\s+petitions?|transfer\s+petitions?|reference|matters?|cases?)\s+(?:is|are|stands?|shall\s+stand|be|is\s+hereby|are\s+hereby)\s+"
    r"(?:accordingly\s+|hereby\s+|partly\s+|partially\s+|consequently\s+|therefore\s+)?(?:allowed|dismissed|disposed|rejected|answered|remitted|remanded|restored|closed)"
    r"|\bwe\s+(?:accordingly\s+|therefore\s+|hereby\s+|would\s+)?(?:allow|dismiss|set\s+aside|quash|direct|order|dispose|remit|remand|restore)\b|\bno\s+(?:order\s+as\s+to\s+)?costs\b|\bparties\s+(?:shall|to)\s+bear"
    r"|\bpending\s+(?:interlocutory\s+)?applications?|\b(?:impugned|the)\s+(?:judgment|order)s?\s+(?:of|passed|dated)[^.]{0,120}?\b(?:is|are|stands?)\s+(?:hereby\s+)?(?:set\s+aside|quashed|restored|modified|upheld|affirmed)"
    r"|\bshall\s+(?:be\s+)?(?:paid|released|reinstated|disbursed|refunded|computed|implemented|complied|considered|granted)\b|\bwithin\s+(?:a\s+period\s+of\s+)?(?:\w+\s+){1,2}(?:weeks?|months?|days?)\b"
    r"|\bthere\s+shall\s+be\s+a\s+direction|\bwe\s+direct\b|\bis\s+directed\s+to\b|\bare\s+directed\s+to\b", re.I)

_DISPOSAL_RE = re.compile(r"\bwe\s+(?:accordingly\s+|therefore\s+|hereby\s+)?(?:allow|dismiss|set\s+aside|quash|dispose\s+of|remit|remand|restore|uphold)\s+(?:the\s+|this\s+|these\s+|all\s+)?(?:appeals?|petitions?|writ|impugned|judgments?|orders?|O\.?A)"
                          r"|\b(?:appeals?|petitions?)\s+(?:is|are|stands?)\s+(?:accordingly\s+|hereby\s+|partly\s+)?(?:allowed|dismissed|disposed\s+of)", re.I)
_Q_RES = [re.compile(p, re.I) for p in [
    r"\b(?:short|sole|only|main|principal|primary|core|central|moot|neat|important|real|first|second|third|limited|substantial|following|two|three|four|several|"
    r"precise|larger|key|crucial|vital|basic|pivotal|next|other|remaining|common|legal|significant|interesting|fundamental)?\s*(?:questions?|issues?|points?|controversy)\s+"
    r"(?:of\s+law\s+)?(?:which|that)?\s*(?:arises?|arise|arising|falls?|fall|falling|requires?|require|survives?|survive|calls?|call|needs?|need|is|are|was|were|has|have|had|would|"
    r"therefore|thus|now)?\s*(?:been\s+|be\s+)?(?:for\s+(?:our\s+|the\s+)?(?:consideration|determination|decision|adjudication|resolution|answer)|to\s+be\s+(?:decided|determined|"
    r"considered|answered|examined|resolved|addressed)|involved|raised|posed|framed|referred|before\s+(?:us|this\s+Court|the\s+Court)|in\s+(?:this|these|the\s+present)\s+(?:appeals?|cases?|matters?|petitions?))",
    r"\b(?:questions?|issues?|points?|controversy|dispute)\s+(?:therefore\s+|thus\s+|now\s+|then\s+)?(?:is|are|was|were|being|remains?|boils\s+down\s+to|narrows\s+down\s+to|centres\s+(?:on|around)|revolves\s+around)\s+(?:as\s+to\s+|to\s+)?(?:whether|what|how|when|if)\b",
    r"\b(?:raises?|raised|raising|involves?|involved|involving|presents?)\s+(?:a|an|the)?\s*(?:short|substantial|important|interesting|neat|following|significant|vexed|"
    r"pure|question\s+of)?\s*(?:questions?|issues?|points?)\s+(?:of\s+(?:law|general\s+importance|public\s+importance)\s*)?(?:as\s+to|whether|of|regarding|concerning|relating|about)",
    r"\b(?:we\s+are|the\s+Court\s+is|this\s+Court\s+is)\s+(?:called\s+upon|required|asked|invited)\s+to\s+(?:decide|determine|consider|examine|answer)\s+(?:whether|the\s+question|the\s+issue|as\s+to)",
    r"\b(?:what|the\s+question\s+which)\s+(?:falls|arises|requires)\s+(?:for\s+)?(?:consideration|determination|decision)",
    r"\b(?:question|issue|point)s?\s+(?:referred|for\s+reference)\s+(?:to|for)",
]]
_Q_OPEN_RE = re.compile(r"\bwhether\b|\bas\s+to\b|\bwhat\b|\bhow\b|\?|[:\-–—]\s*$|\b(?:with\s+regard|relating|regarding|concerning|pertaining)\s+to\b|\bof\s+law\s+(?:is|was)\b", re.I)
_Q_EXCLUDE_RE = re.compile(r"\bin\s+(?:that|the\s+said)\s+case|\bwas\s+raised\s+in\b|\bno\s+(?:longer|more)\s+res[\s\-]?integra|\bdisposes?\s+of|\bconclusions?\s+reached|"
                           r"\bheld\s+as\s+under|\(supra\)|\bit\s+was\s+held|\bthe\s+Bench\s+was|\bprecedents?\s+cited|\bdifferent\s+observations|"
                           r"\b(?:United\s+States|House\s+of\s+(?:Commons|Lords))\b|\b(?:Lok|Rajya)\s+Sabha\b|\bI\s+shall\s+deal|\bmay\s+be\s+considered\.?$", re.I)
_WHETHER_ITEM_RE = re.compile(r"^\W{0,3}(?:\(?(?:[ivxlc]{1,5}|[a-h]|\d{1,2})[.)]\s*)?Whether\b", re.I)
_SUBM_QUESTION_RE = re.compile(r"\b(?:submitted|contended|urged|argued|according\s+to\s+(?:the\s+)?(?:learned\s+)?counsel)\b", re.I)

ISSUE_KEYWORDS = [
    ("court_martial", r"court[\s\-]martial|\bGCM\b|\bSCM\b|\bDCM\b|summary\s+court|summary\s+of\s+evidence|confirming\s+authority|convening"),
    ("disability_pension", r"disability\s+(?:pension|element)|attributab|aggravat|invalid(?:ed|ment)|release\s+medical\s+board|medical\s+board|entitlement\s+rules|war\s+injury"),
    ("aft_jurisdiction", r"armed\s+forces\s+tribunal|\bAFT\b|tribunal['’]?s?\s+jurisdiction|section\s+3[01]\b|article\s+226|writ\s+against"),
    ("pension_service", r"\bpension\b|gratuity|commutation|qualifying\s+service|family\s+pension|special\s+pension|liberali[sz]ed"),
    ("discipline_punishment", r"dismissal|discharge|punishment|sentence|proportional|desertion|absence\s+without|AWL|misconduct"),
    ("service_conditions", r"promotion|seniority|permanent\s+commission|selection\s+board|ACR|posting|transfer|pay\s+fixation|MACP|retirement\s+age"),
    ("constitutional_rights", r"article\s+(?:14|16|19|21|33)\b|fundamental\s+rights?|equality|discriminat|natural\s+justice"),
    ("criminal_jurisdiction", r"criminal\s+court|section\s+(?:125|126)\b|choice\s+of\s+(?:forum|jurisdiction)|ordinary\s+criminal|Cr\.?P\.?C|penal\s+code|\bIPC\b"),
    ("limitation_delay", r"limitation|delay|laches|condon"),
]
ISSUE_RES = [(k, re.compile(p, re.I)) for k, p in ISSUE_KEYWORDS]

_INSTRUMENTS = [
    ("AFT-PR-2008", r"Armed\s+Forces\s+Tribunal\s+\(Procedure\)\s+Rules|AFT\s+\(Procedure\)\s+Rules"),
    ("AFT-2007", r"Armed\s+Forces\s+Tribunal\s+Act|\bAFT\s+Act\b"),
    ("IAA-1911", r"Indian\s+Army\s+Act,?\s+1911"),
    ("AR-1954", r"\bArmy\s+Rules\b"),
    ("AA-1950", r"\b(?:Indian\s+)?Army\s+Act\b"),
    ("AFA-1950", r"\bAir\s+Force\s+Act\b"),
    ("NA-1957", r"\bNavy\s+Act\b"),
    ("RA-1987", r"\bRegulations\s+for\s+the\s+Army\b"),
    ("ENT-2008", r"Entitlement\s+Rules[^.]{0,60}?2008|2008\s+(?:Entitlement\s+)?Rules"),
    ("ENT-1982", r"Entitlement\s+Rules[^.]{0,60}?1982|1982\s+(?:Entitlement\s+)?Rules"),
    ("ENT-UNSPECIFIED", r"Entitlement\s+Rules"),
    ("PRA-2008", r"Pension\s+Regulations[^.]{0,40}?2008"),
    ("PRA-1961", r"Pension\s+Regulations[^.]{0,40}?1961"),
    ("PRA-UNSPECIFIED", r"Pension\s+Regulations"),
    ("CRPC-1973", r"Code\s+of\s+Criminal\s+Procedure|Cr\.?\s?P\.?\s?C\.?"),
    ("IPC-1860", r"Indian\s+Penal\s+Code|Penal\s+Code|\bI\.?P\.?C\.?\b"),
    ("IEA-1872", r"Evidence\s+Act"),
    ("BNSS-2023", r"Bharatiya\s+Nagarik\s+Suraksha\s+Sanhita|\bBNSS\b"),
    ("BNS-2023", r"Bharatiya\s+Nyaya\s+Sanhita|\bBNS\b"),
    ("COI", r"\bConstitution\b"),
]
_INSTR_RES = [(k, re.compile(p, re.I)) for k, p in _INSTRUMENTS]
_PROV_RE = re.compile(r"\b(sections?|secs?\.|ss?\.|rules?|r\.|regulations?|regs?\.|articles?|arts?\.|paras?(?:graphs?)?|clauses?)\s*"
                      r"(\d{1,4}[A-Z]?(?:\s*\(\s*[0-9a-z]{1,4}\s*\))*)", re.I)


def issue_keywords(s):
    return [k for k, rx in ISSUE_RES if rx.search(s)]


def statute_refs(sent):
    """Normalised statute references stated in the sentence itself."""
    inst_hits = []
    for k, rx in _INSTR_RES:
        for m in rx.finditer(sent):
            if any(a <= m.start() < b for a, b, _ in inst_hits):
                continue
            inst_hits.append((m.start(), m.end(), k))
    inst_hits.sort()
    out = []
    seen = set()
    for m in _PROV_RE.finditer(sent):
        unit = m.group(1).lower()
        prov = re.sub(r"\s+", "", m.group(2))
        kind = "art" if unit.startswith("art") else "r" if unit.startswith("r") and not unit.startswith("reg") else \
            "reg" if unit.startswith("reg") else "para" if unit.startswith("para") else "cl" if unit.startswith("cl") else "s"
        inst = None
        basis = None
        after = [h for h in inst_hits if 0 <= h[0] - m.end() <= 60 and re.match(r"^\s*(?:,|of|of\s+the|under|under\s+the|\(|read\s+with)?\s*", sent[m.end():h[0]])]
        if after and re.fullmatch(r"[\s,]*(?:of|of\s+the|under|under\s+the)?[\s,]*(?:the\s+)?(?:[A-Z][a-z]+\s+){0,3}", sent[m.end():after[0][0]]):
            inst, basis = after[0][2], "NAMED_AFTER_PROVISION"
        elif kind == "art":
            inst, basis = "COI", "ARTICLE_DEFAULTS_TO_CONSTITUTION"
        elif len(set(h[2] for h in inst_hits)) == 1:
            inst, basis = inst_hits[0][2], "ONLY_INSTRUMENT_IN_SENTENCE"
        key = (inst, kind, prov)
        if key in seen:
            continue
        seen.add(key)
        out.append({"instrument_id": inst, "provision": "%s.%s" % (kind, prov), "printed": squash(m.group(0)),
                    "basis": basis or "INSTRUMENT_NOT_RESOLVED_IN_SENTENCE"})
    for _, _, k in inst_hits:
        if not any(o["instrument_id"] == k for o in out):
            key = (k, None, None)
            if key in seen:
                continue
            seen.add(key)
            out.append({"instrument_id": k, "provision": None, "printed": None, "basis": "INSTRUMENT_MENTIONED"})
    return out


_STOP = set("""the a an of to in and or for on by with that this these those is are was were be been being it its as at from
which who whom whose not no any all such shall may can must would should could has have had do does did there their they them
he she his her we our us you your court learned said case cases also than then so if whether under upon into within out per
one two three other same said thereof therein herein hereby""".split())


def content_words(s):
    return set(w for w in re.findall(r"[a-z][a-z\-]{2,}", s.lower()) if w not in _STOP)


def jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))


_LAW_STATEMENT_RE = re.compile(r"\bprinciples?\s+of\s+law|\bsettled\s+(?:principle|law|position|proposition)|\bthe\s+law\s+(?:is|on\s+the\s+point|in\s+this\s+regard)|\benunciated|"
                               r"\blaid\s+down|\bwell[\s\-]settled|\bthe\s+test\s+(?:is|to\s+be|for)|\bres[\s\-]?integra|\bthe\s+legal\s+position|\bthe\s+proposition\s+(?:that|of)|"
                               r"\bthe\s+(?:true|correct|proper)\s+(?:test|position|interpretation|construction|meaning)|\bas\s+a\s+(?:general\s+)?rule\b|\bthe\s+rule\s+(?:is|of)", re.I)
_APPLICATION_RE = re.compile(r"\bin\s+the\s+(?:present|instant)\s+case|\bin\s+the\s+facts\s+(?:and\s+circumstances\s+)?of\s+(?:the|this)|\bon\s+the\s+facts\b|\bin\s+this\s+case\b", re.I)


# ------------------------------------------------------------------ scoring
WEIGHTS = {
    "COURT_CONCLUSION_MARKER": 3, "ACCEPTS_OR_REJECTS_CONTENTION": 3, "STATEMENT_OF_LAW": 2, "APPLICATION_TO_FACTS": 2,
    "NORMATIVE_LEGAL_PREDICATE": 1, "LEGAL_CONCEPT": 1, "INFERENTIAL_CONNECTIVE": 0, "STATUTE_REFERENCE": 0,
    "INTRODUCES_QUOTATION_OR_LIST": -3, "TOO_SHORT": -3, "VERY_LONG": -1, "NARRATIVE_FACT": -2, "DATE_HEAVY": -1,
    "PROCEDURAL_OR_FACT_INTRO": -3,
    # position / structure (court voice only)
    "LATE_IN_OPINION": 2, "VERY_LATE_IN_OPINION": 1, "EARLY_IN_OPINION": -2, "IN_FACTS_SECTION": -2, "IN_FRAMEWORK_SECTION": -1,
    "IN_ANALYSIS_SECTION": 0, "IN_CONCLUSION_SECTION": 1, "LEXICAL_LINK_TO_QUESTION": 2,
}
HOLDING_CAP_FRACTION = 0.06
HOLDING_CAP_MIN, HOLDING_CAP_MAX = 4, 25
SHORT_OPINION_SENTENCES = 25


def legal_signals(sent):
    """Propositional-content signals independent of voice."""
    sig = []
    if _STRONG_RE.search(sent):
        sig.append("COURT_CONCLUSION_MARKER")
    elif _CONNECT_RE.search(sent):
        sig.append("INFERENTIAL_CONNECTIVE")
    if _NORMATIVE_RE.search(sent):
        sig.append("NORMATIVE_LEGAL_PREDICATE")
    if _REJECT_ACCEPT_RE.search(sent):
        sig.append("ACCEPTS_OR_REJECTS_CONTENTION")
    if _LAW_STATEMENT_RE.search(sent):
        sig.append("STATEMENT_OF_LAW")
    if _APPLICATION_RE.search(sent):
        sig.append("APPLICATION_TO_FACTS")
    if sent.rstrip().endswith(":"):
        sig.append("INTRODUCES_QUOTATION_OR_LIST")
    if _STATREF_RE.search(sent):
        sig.append("STATUTE_REFERENCE")
    if _LEGAL_CONCEPT_RE.search(sent):
        sig.append("LEGAL_CONCEPT")
    n = len(sent)
    if n < 30:
        sig.append("TOO_SHORT")
    elif n > 900:
        sig.append("VERY_LONG")
    if _DATE_RE.search(sent) and _FACT_RE.search(sent) and "NORMATIVE_LEGAL_PREDICATE" not in sig:
        sig.append("NARRATIVE_FACT")
    elif len(_DATE_RE.findall(sent)) >= 2 and "COURT_CONCLUSION_MARKER" not in sig:
        sig.append("DATE_HEAVY")
    if _PROCEDURAL_RE.search(sent):
        sig.append("PROCEDURAL_OR_FACT_INTRO")
    return sig


def score_of(sig):
    return sum(WEIGHTS.get(x.split("(")[0], 0) for x in sig)


def legal_score(sent):
    sig = legal_signals(sent)
    return score_of(sig), sig


# ------------------------------------------------------------------ main analysis
def analyze(text, meta):
    """meta: judgment_id, sha256, court. Returns (summary dict, items list)."""
    jid = meta.get("judgment_id", "")
    court = meta.get("court", "")
    pidx = page_index(text)
    mt, header_judges = noise_mask(text)
    start, end, start_method, headnote = find_body(text, mt, court)
    opinions = find_opinions(mt, start, end, header_judges, [p for p, _ in pidx])
    paras = find_paragraphs(mt, opinions)
    para_starts = [p[0] for p in paras]
    headings = find_headings(mt, start, end)
    quotes = find_quotes(mt, start, end, para_starts)
    forced = sorted(set(para_starts + [h[0] for h in headings] + [q[0] for q in quotes] + [q[1] for q in quotes]
                        + [o["body"] for o in opinions]))
    sents = sentences(mt, start, end, forced)
    blocks = [m.start() for m in re.finditer(r"\n[ \t]*\n", mt, )]

    def opinion_of(pos):
        for i, o in enumerate(opinions):
            if o["start"] <= pos < o["end"]:
                return i
        return len(opinions) - 1

    # paragraph-level submission carry-over
    para_first_voice = {}
    recs = []
    issue_zone_until = -1
    for (s, e) in sents:
        raw = mt[s:e]
        sent = squash(raw)
        if len(norm_alnum(sent)) < 8:
            continue
        oi = opinion_of(s)
        op = opinions[oi]
        if s < op["body"]:
            continue  # the author line itself
        pa = para_at(paras, s)
        para_key = (pa[0] if pa and pa[2] == oi else ("b", bisect.bisect_right(blocks, s)))
        sect = section_at(headings, s)
        q = quote_at(quotes, s)
        hd = [h for h in headings if h[0] <= s]
        if hd and hd[-1][1] == "ISSUES" and s - hd[-1][0] < 4000:
            issue_zone_until = max(issue_zone_until, hd[-1][0] + 4000)
        # voice
        if q:
            voice = q[2]
        else:
            own_concl = bool(_STRONG_RE.search(sent)) and bool(re.search(r"\b(?:we|us|our|this\s+Court|I)\b", sent))
            subm = bool(_SUBMISSION_RE.search(sent)) and not _REJECT_ACCEPT_RE.search(sent) and not own_concl \
                and not re.match(r"^\W*(?:\d+\s*[.)]?\s*)?(?:We|In\s+our)\b", sent)
            lower = bool(_LOWER_RE.search(sent)) and not _COURT_ASSESS_RE.search(sent)
            if _PRECEDENT_REPORT_RE.search(sent) and not re.search(r"\b(?:we|us|our)\b", sent, re.I):
                voice = "precedent_report"
            elif subm:
                voice = "submission"
            elif lower:
                voice = "lower_court"
            else:
                voice = "court"
            first = para_first_voice.get(para_key)
            if first is None:
                para_first_voice[para_key] = voice
            elif first == "submission" and voice == "court":
                if _OWN_PIVOT_RE.search(sent) or _REJECT_ACCEPT_RE.search(sent):
                    para_first_voice[para_key] = "court"  # pivot: the rest of the paragraph is the court's
                else:
                    voice = "submission"
            if voice == "court" and sect == "SUBMISSIONS" and not (_OWN_PIVOT_RE.search(sent) or _REJECT_ACCEPT_RE.search(sent)):
                voice = "submission"
        recs.append({"s": s, "e": e, "sent": sent, "oi": oi, "para": pa[1] if pa and pa[2] == oi else None,
                     "section": sect, "voice": voice, "issue_zone": s <= issue_zone_until})

    # opinion spans in sentence counts (for relative position)
    pos_in_op = {}
    for oi in range(len(opinions)):
        idx = [i for i, r in enumerate(recs) if r["oi"] == oi]
        for k, i in enumerate(idx):
            pos_in_op[i] = (k + 1) / float(len(idx)) if idx else 0.0

    # pass 1: questions of law (court voice)
    qset = {}
    for i, r in enumerate(recs):
        sent = r["sent"]
        if r["voice"] != "court" or len(sent) < 30 or _SUBM_QUESTION_RE.search(sent):
            continue
        prev_intro = i > 0 and re.search(r"(?:questions?|issues?|points?)[^.]{0,80}[:\-]\s*$", recs[i - 1]["sent"], re.I)
        qpat = any(rx.search(sent) for rx in _Q_RES) and bool(_Q_OPEN_RE.search(sent)) and not _Q_EXCLUDE_RE.search(sent)
        if qpat or (_WHETHER_ITEM_RE.search(sent) and (
                r["issue_zone"] or r["section"] == "ISSUES" or re.search(r"\?\s*$", sent) or prev_intro)):
            qset[i] = content_words(sent)

    # pass 2: classify and score
    n_court = {}
    for r in recs:
        if r["voice"] == "court":
            n_court[r["oi"]] = n_court.get(r["oi"], 0) + 1
    items = []
    questions = []
    cand_by_op = {}
    for i, r in enumerate(recs):
        sent, voice = r["sent"], r["voice"]
        sig = legal_signals(sent)
        lsc = score_of(sig)
        itype = None
        if voice == "court":
            p = pos_in_op.get(i, 0)
            if i in qset:
                itype = "question_of_law"
                sig = sig + ["QUESTION_FRAMING"]
            elif (_OPERATIVE_RE.search(sent) and (not _STRONG_RE.search(sent[:60]) or _DISPOSAL_RE.search(sent))) and (p > 0.6 or r["section"] == "CONCLUSION"):
                itype = "operative_direction"
                sig = sig + ["OPERATIVE_WORDING"]
            elif _OBITER_RE.search(sent) and lsc >= 0:
                itype = "obiter_candidate"
                sig = sig + ["OBITER_CUE"]
            else:
                late_from = 0.4 if n_court.get(r["oi"], 0) < SHORT_OPINION_SENTENCES else 0.6
                if p >= late_from:
                    sig = sig + ["LATE_IN_OPINION"]
                if p >= 0.8:
                    sig = sig + ["VERY_LATE_IN_OPINION"]
                if p < 0.15 and "COURT_CONCLUSION_MARKER" not in sig:
                    sig = sig + ["EARLY_IN_OPINION"]
                if r["section"] in ("ANALYSIS", "CONCLUSION", "FACTS", "FRAMEWORK"):
                    sig = sig + ["IN_%s_SECTION" % r["section"]]
                cw = content_words(sent)
                best = max([jaccard(cw, qw) for qi, qw in qset.items() if qi < i and recs[qi]["oi"] == r["oi"]] or [0.0])
                if best >= 0.15:
                    sig = sig + ["LEXICAL_LINK_TO_QUESTION(%.2f)" % best]
                score = score_of(sig)
                core_sig = any(x in sig for x in ("COURT_CONCLUSION_MARKER", "NORMATIVE_LEGAL_PREDICATE", "ACCEPTS_OR_REJECTS_CONTENTION",
                                                  "STATEMENT_OF_LAW", "APPLICATION_TO_FACTS"))
                if (score >= T_REASONING + 1 and (core_sig or "STATUTE_REFERENCE" in sig or "LEGAL_CONCEPT" in sig)) or (score >= T_REASONING and core_sig):
                    itype = "reasoning"
                    if score >= T_HOLDING and core_sig:
                        cand_by_op.setdefault(r["oi"], []).append(len(items))
                lsc = score
        elif lsc >= T_NONCOURT_EMIT:
            if voice in ("quoted_precedent", "precedent_report"):
                itype = "quoted_precedent"
            elif voice in ("submission", "submission_quotation"):
                itype = "submission"
            elif voice in ("lower_court", "lower_court_quotation"):
                itype = "lower_court_finding"
        if not itype:
            continue
        it = {"rec": i, "item_type": itype, "score": lsc, "signals": sig}
        items.append(it)
        if itype == "question_of_law":
            questions.append(it)
    # per-opinion cap: the highest-scoring candidates become holdings, the rest stay reasoning
    for oi, idxs in cand_by_op.items():
        cap = int(min(HOLDING_CAP_MAX, max(HOLDING_CAP_MIN, round(HOLDING_CAP_FRACTION * n_court.get(oi, 0)))))
        ranked = sorted(idxs, key=lambda k: (-items[k]["score"], -recs[items[k]["rec"]]["s"]))
        for rank, k in enumerate(ranked):
            if rank < cap:
                items[k]["item_type"] = "holding"
            else:
                items[k]["signals"] = items[k]["signals"] + ["BELOW_OPINION_HOLDING_CAP(%d)" % cap]
    # rank of every holding/reasoning item within its opinion by score
    by_op = {}
    for k, it in enumerate(items):
        if it["item_type"] in ("holding", "reasoning"):
            by_op.setdefault(recs[it["rec"]]["oi"], []).append(k)
    for oi, idxs in by_op.items():
        for rank, k in enumerate(sorted(idxs, key=lambda k: (-items[k]["score"], -recs[items[k]["rec"]]["s"]))):
            items[k]["rank"] = rank + 1

    # link holdings to questions (lexical overlap within the same opinion)
    qwords = {id(q): content_words(recs[q["rec"]]["sent"]) for q in questions}
    out = []
    for it in items:
        r = recs[it["rec"]]
        s, e = r["s"], r["e"]
        op = opinions[r["oi"]]
        rec = {
            "item_id": item_id(jid, s, e, it["item_type"]),
            "judgment_id": jid,
            "sha256": meta.get("sha256", ""),
            "doc_id": meta.get("text_doc", ""),
            "court": court,
            "item_type": it["item_type"],
            "opinion": op["label"],
            "opinion_author": op["author"] or None,
            "opinion_index": r["oi"],
            "opinion_method": op["method"],
            "page": page_at(pidx, s),
            "page_end": page_at(pidx, e),
            "paragraph": r["para"],
            "char_start": s,
            "char_end": e,
            "excerpt": squash(text[s:e], EXCERPT_CAP),
            "excerpt_clean": squash(mt[s:e], EXCERPT_CAP),
            "voice": r["voice"],
            "section_heading": r["section"] or None,
            "holding_score": it["score"],
            "rank_in_opinion": it.get("rank"),
            "signals": it["signals"],
            "legal_issue": None,
            "legal_issue_keywords": issue_keywords(r["sent"]),
            "answers_question": None,
            "statutes": statute_refs(r["sent"]),
            "statute_links": [],
            "treatment": [],
            "status": STATUS,
            "verification": VERIFICATION,
            "extractor": VERSION,
        }
        if it["item_type"] == "question_of_law":
            m = re.search(r"\b(whether|what|how|when)\b", r["sent"], re.I)
            rec["legal_issue"] = squash(r["sent"][m.start():] if m else r["sent"], 400)
        elif it["item_type"] in ("holding", "reasoning", "obiter_candidate"):
            cw = content_words(r["sent"])
            best, bq = 0.0, None
            for q in questions:
                if recs[q["rec"]]["oi"] != r["oi"] or q["rec"] >= it["rec"]:
                    continue
                jv = jaccard(cw, qwords[id(q)])
                if jv > best:
                    best, bq = jv, q
            if bq is not None and best >= 0.15:
                rec["answers_question"] = item_id(jid, recs[bq["rec"]]["s"], recs[bq["rec"]]["e"], "question_of_law")
                rec["legal_issue"] = squash(recs[bq["rec"]]["sent"], 300)
        if op["label"] in ("separate", "dissent"):
            rec["opinion_note"] = ("NOT_THE_COURT'S_HOLDING_IF_DISSENT" if op["label"] == "dissent"
                                   else "SEPARATE_OPINION: majority/concurrence status not determined")
        elif op["label"] == "lead":
            rec["opinion_note"] = "FIRST_OPINION_IN_REPORT: majority status not determined"
        else:
            rec["opinion_note"] = None
        out.append(rec)

    counts = {}
    for r in out:
        counts[r["item_type"]] = counts.get(r["item_type"], 0) + 1
    summary = {
        "judgment_id": jid,
        "body_start": start,
        "body_end": end,
        "body_start_page": page_at(pidx, start),
        "body_start_method": start_method,
        "headnote_detected": headnote,
        "headnote_excluded_chars": start if headnote else 0,
        "n_opinions": len(opinions),
        "opinions": ";".join("%s:%s@p%s" % (o["label"], o["author"] or "?", page_at(pidx, o["start"])) for o in opinions),
        "n_numbered_paragraphs": len(paras),
        "n_quote_spans": len(quotes),
        "n_sentences": len(recs),
        "counts": counts,
    }
    if meta.get("debug"):
        summary["_recs"] = recs
    return summary, out
