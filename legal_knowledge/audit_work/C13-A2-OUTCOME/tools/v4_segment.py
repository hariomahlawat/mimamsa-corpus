"""Mimamsa C13 judicial outcome extractor V4: structural segmentation: signatures, opinion/order segments, operative cues (ported from V3; V4 layer below).

All values are AUTOMATED CANDIDATES read from a PDF text layer; nothing is legally verified."""
import bisect
import re

from v4_text import (  # noqa: F401
    _DOC_HEADER_RE,
    _CAUSE_TITLE_RE,
    _SCR_CASE_HEAD_RE)


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
    # V4: a separate opinion starts at an author line ('K. M. JOSEPH, J.') followed by a paragraph numbered 1
    for oc in opinion_cuts(mt):
        if not any(abs(oc - c[0]) < 1500 or abs(oc - c[1]) < 1500 for c in clusters) and oc not in cuts:
            cuts.append(oc)
    cuts.sort()
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



# ------------------------------------------------------------------ V4: opinions and their roles
_AUTHOR_LINE_RE = re.compile(r"(?m)^[ \t]*(?:[A-Z]\.\s?){0,3}[A-Z][A-Za-z.'\- ]{1,40}?,\s*(?:C\.?\s?J\.?I?|J)\.?[ \t]*"
                             r"(?:\(\s*(?:Partly\s+)?(?:Dissenting|Concurring|dissenting|concurring)\s*\))?[ \t:.]*$")


def opinion_cuts(mt):
    """Start positions of opinions after the first: an author line followed within 300 characters by a paragraph
    numbered 1 (paragraph numbering restarts in every opinion), once a numbered body has already begun."""
    out = []
    for m in _AUTHOR_LINE_RE.finditer(mt):
        if re.match(r"\s*(?:\[[^\]\n]{0,40}\]\s*)?1\s*\.\s", mt[m.end():m.end() + 300]) and \
                re.search(r"(?m)^[ \t]*2[ \t]*\.\s", mt[:m.start()]):
            out.append(m.start())   # a body (paragraph 2 at least) precedes it: not the main opinion's author line
    return out


_DISSENT_RE = re.compile(r"\bI\s+(?:would\s+)?(?:respectfully\s+|regret(?:fully)?\s+(?:that\s+)?(?:I\s+)?)?(?:disagree|dissent|differ)\b|"
                         r"\bI\s+(?:am|find\s+myself)\s+(?:\w+\s+){0,2}unable\s+to\s+(?:agree|concur|persuade\s+myself)|"
                         r"\(\s*(?:Partly\s+)?[Dd]issenting\s*\)|\bmy\s+dissent\b|\bpartly\s+dissenting\b", re.I)
_CONCUR_RE = re.compile(r"\bI\s+(?:fully\s+|entirely\s+|respectfully\s+)?(?:agree|concur)\b|\(\s*[Cc]oncurring\s*\)")


def opinion_role(seg_text, first):
    """'dissent' (a separate opinion that differs from the majority), 'concurring', or 'main'."""
    head = seg_text[:6000]
    if not first and _DISSENT_RE.search(seg_text):
        return "dissent"
    if not first and _CONCUR_RE.search(head):
        return "concurring"
    return "main"
