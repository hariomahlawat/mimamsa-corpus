"""Mimamsa C13 workstream A3: hierarchical segmentation of a judgment.

Judgment -> opinions (sole / majority-lead / concurring / dissent / split / court order, author from judge-name cues)
         -> parts (section headings) and paragraphs
         -> quoted blocks (precedent / statute or document / lower forum / submission, each with a source attribution)
         -> zones (submissions vs the court's analysis)
         -> sentences, each with a deterministic voice.

Layout masking, body detection, paragraph numbering, raw quotation spans and sentence splitting are reused from the
frozen C12 module `holdings_core.py` (imported read-only). Opinion detection, quotation source attribution, precedent-
report carry-over, the submission/analysis zoning and the voice rules are new in C13.

Standard library only. Python 3.11+.
"""
import bisect
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
C12_TOOLS = os.path.normpath(os.path.join(HERE, "..", "..", "C12-CONSOLIDATION", "holdings", "tools"))
if C12_TOOLS not in sys.path:
    sys.path.insert(0, C12_TOOLS)
import holdings_core as c12  # noqa: E402  (frozen C12 module, read-only reuse)

squash = c12.squash
norm_alnum = c12.norm_alnum

# ------------------------------------------------------------------ opinions
# e-SCR (2023+) renditions: "Judgment\n\nSanjay Karol J." / "Judgment\n\nNagarathna, J."
_ESCR_AUTHOR_RE = re.compile(
    r"(?m)^[ \t]*(?:Judgment|JUDGMENT|J\s?U\s?D\s?G\s?M\s?E\s?N\s?T|Order|ORDER)[ \t]*\n(?:[ \t]*\n){0,3}[ \t]*"
    r"((?:Dr\.?\s*|DR\.?\s*)?[A-Z][A-Za-z.'\-]*(?:[ \t]+[A-Z][A-Za-z.'\-]*){0,5}?)[ \t]*,?[ \t]*(C\.?[ \t]*J\.?(?:I\.?)?|J\.?)[ \t]*$")
# old SCR inline author with dash, mixed case allowed ("BosE J.-With great respect ...")
_AUTHOR_DASH_RE = re.compile(r"(?m)^[ \t]*((?:[A-Z][A-Za-z.'\-]+[ \t]+){0,3}[A-Z][A-Za-z'\-]+),?[ \t]*(C\.[ \t]*J\.|J\.)[ \t]*[\-–—:][ \t]*(?=[A-Z\"“(])")
# older SCR running headers with the author in parentheses: "MANEKA GANDHI v. UNION (Kailasam, J.)"
_PAREN_HDR_RE = re.compile(r"^[^\n]{3,90}?\bv[\.,]?\s*[^\n]{0,70}?\(\s*((?:DR\.?\s*)?[A-Z][A-Za-z.\s'\-]{2,40}?)\s*[,)]\s*(?:C\.\s*)?J\s*[.,]?\s*\)\s*$")


def header_judges_c13(text, mt, header_judges):
    """C12 square-bracket header judges plus parenthesised SCR headers (positions in the unmasked text)."""
    extra = []
    pos = 0
    for ln in text.split("\n"):
        if len(ln) < 200 and "(" in ln and "J" in ln and ")" in ln:
            m = _PAREN_HDR_RE.match(ln)
            if m:
                extra.append((pos, squash(m.group(1)).upper()))
        pos += len(ln) + 1
    if not extra:
        return header_judges
    return sorted(set(header_judges) | set(extra))


_DELIVERED_RE = re.compile(r"(?:Judgment|Order)s?\s+of\s+the\s+Court\s+(?:was|were)\s+delivered\s+by\s*[:\-]?\s*"
                           r"((?:DR\.?\s*)?[A-Z][A-Za-z.'\-]*(?:\s+[A-Z][A-Za-z.'\-]*){0,5}?)\s*,?\s*(?:C\.?\s*J\.?|J\.?)", re.I)
_DELIVERED_SEVERAL_RE = re.compile(r"The\s+following\s+Judgments?\s+(?:of\s+the\s+Court\s+)?were\s+delivered", re.I)
_DISSENT_ANY_RE = re.compile(
    r"\bI\s+(?:regret|am\s+unable|find\s+myself\s+unable|have\s+not\s+been\s+able|am\s+not\s+able)\s+to\s+(?:agree|concur|share|subscribe|persuade\s+myself|accept)"
    r"|\b(?:respectful\s+)?inability\s+to\s+(?:concur|agree)|\bI\s+am\s+differing\b|\bdiffering\s+with\s+the\s+views?|\bI\s+(?:respectfully\s+)?(?:disagree|differ)\b|\b(?:With\s+(?:great|due|the\s+greatest)\s+respect,?\s+)?I\s+(?:cannot|am\s+unable\s+to)\s+agree\s+that"
    r"|\b(?:my|this)\s+dissent(?:ing)?\b|\bI\s+dissent\b|\bdissenting\s+(?:opinion|judgment|note|view)|\bcannot\s+(?:agree|concur)\s+with\s+(?:my|the\s+majority|the\s+view|the\s+conclusion)"
    r"|\bI\s+(?:do\s+not|cannot)\s+(?:agree|concur|subscribe)\s+(?:with|to)\s+(?:the\s+)?(?:view|opinion|conclusion|reasoning|judgment)"
    r"|\bunable\s+to\s+(?:agree|concur|persuade\s+myself\s+to\s+agree)\s+with\s+(?:my|the)\s+(?:learned|esteemed|noble|majority|view)", re.I)
_CONCUR_ANY_RE = re.compile(
    r"\bI\s+(?:entirely\s+|fully\s+|respectfully\s+|wholly\s+)?(?:agree|concur)\b|\bI\s+have\s+had\s+the\s+(?:advantage|benefit|privilege|opportunity)(?:\s+and\s+\w+)?\s+of\s+(?:reading|going\s+through|perusing)"
    r"|\bwhile\s+(?:I\s+)?(?:agreeing|concurring)|\bconcurring\s+(?:opinion|judgment)|\bI\s+(?:would|wish\s+to)\s+(?:add|supplement|say\s+a\s+few\s+words)"
    r"|\bin\s+agreement\s+with\s+(?:my|the)\s+(?:learned|esteemed|noble)", re.I)
_SPLIT_RE = re.compile(
    r"\bin\s+view\s+of\s+the\s+(?:divergent|differing|difference\s+of|split|conflicting)\s+(?:opinions?|views?|verdict)|\bdifference\s+of\s+opinion\b"
    r"|\bplace(?:d)?\s+(?:the\s+)?(?:matter|papers|record|case)\s+before\s+(?:Hon[’']?ble\s+)?(?:the\s+)?(?:Hon[’']?ble\s+)?Chief\s+Justice"
    r"|\bsplit\s+verdict|\blarger\s+Bench\b.{0,80}\b(?:difference|divergent|differing)", re.I | re.S)
_MAJORITY_ORDER_RE = re.compile(r"\bin\s+(?:view|terms|accordance)\s+(?:of|with)\s+the\s+(?:majority|opinion\s+of\s+the\s+majority)|\bby\s+majority\b|\bmajority\s+(?:view|opinion|judgment|decision)", re.I)
_ORDER_HEADING_RE = re.compile(r"(?m)^[ \t]*(?:O\s?R\s?D\s?E\s?R(?:\s+OF\s+THE\s+COURT)?|Order\s+of\s+the\s+Court|PER\s+CURIAM|Per\s+Curiam|FINAL\s+ORDER)[ \t]*[.:]?[ \t]*$")
_DISPOSAL_ALLOW_RE = re.compile(r"\b(?:appeals?|petitions?|writ\s+petitions?)\s+(?:is|are|stands?|must\s+be|should\s+be|shall\s+stand|be)\s+(?:accordingly\s+|hereby\s+|partly\s+)?allowed|\b(?:I|we)\s+(?:would\s+)?(?:accordingly\s+|therefore\s+)?allow\b", re.I)
_DISPOSAL_DISMISS_RE = re.compile(r"\b(?:appeals?|petitions?|writ\s+petitions?)\s+(?:is|are|stands?|must\s+be|should\s+be|shall\s+stand|be)\s+(?:accordingly\s+|hereby\s+)?dismissed|\b(?:I|we)\s+(?:would\s+)?(?:accordingly\s+|therefore\s+|for\s+all\s+these\s+reasons\s+)?dismiss\b", re.I)


def _disposal_direction(seg):
    """'allow' / 'dismiss' / '' from the last disposal wording of an opinion."""
    tail = seg[-6000:]
    a = [m.start() for m in _DISPOSAL_ALLOW_RE.finditer(tail)]
    d = [m.start() for m in _DISPOSAL_DISMISS_RE.finditer(tail)]
    if not a and not d:
        return ""
    return "allow" if (a and (not d or a[-1] > d[-1])) else "dismiss"


def same_judge(a, b):
    """C12 fuzzy judge-name equality plus a surname check robust to OCR splits ('S.R. P ANDIAN' / 'S. RATNAVEL PANDIAN')."""
    if c12._same_judge(a, b):
        return True
    la = re.sub(r"[^A-Z]", "", (a or "").upper())
    lb = re.sub(r"[^A-Z]", "", (b or "").upper())
    if len(la) < 5 or len(lb) < 5:
        return False
    return la[-6:] == lb[-6:]


def _header_runs(header_judges, start, end):
    """Merged runs of SCR running-header judge names: [first_pos, last_pos, name, count]."""
    runs = []
    for pos, name in header_judges:
        if pos >= end or pos < start:
            continue
        if runs and same_judge(runs[-1][2], name):
            runs[-1][1] = pos
            runs[-1][3] += 1
        else:
            runs.append([pos, pos, name, 1])
    # absorb one-off OCR variants sandwiched inside a run of the same judge
    merged = []
    for r in runs:
        if merged and same_judge(merged[-1][2], r[2]):
            merged[-1][1] = r[1]
            merged[-1][3] += r[3]
        else:
            merged.append(list(r))
    return merged


def _window_cue(rx, seg, w=4000):
    """A cue in the opening or closing window of an opinion (not in the middle, where judges discuss other views)."""
    return rx.search(seg[:w]) or rx.search(seg[-w:])


def find_opinions(text, mt, start, end, header_judges, page_starts):
    """Opinion segmentation. Returns (opinions, body_start). Each opinion:
    {start, body, end, author, method, role, role_basis, opinion_id}. Roles:
      sole | lead_majority | lead | concurring | dissent | split_opinion | court_order | separate
    """
    def page_start_before(pos, back=1):
        prev = [p for p in page_starts if p <= pos]
        if not prev:
            return pos
        return prev[-1 - back] if len(prev) > back else prev[0]

    # body end correction: C12 cuts the body at the first disposal line in the last 40%; in multi-opinion reports a
    # later opinion (often the dissent) follows it. A sustained header run of another judge after `end` extends it.
    late = [r for r in _header_runs(header_judges, end, len(mt)) if r[0] >= end and r[3] >= 3]
    if late:
        new_end = len(mt)
        for rx in c12._END_RES[:2]:
            m = rx.search(mt, late[-1][1])
            if m:
                new_end = min(new_end, m.start())
        end = new_end
    # same correction without running headers (older SCR): an author line with a concurrence/dissent cue after `end`
    for rx in (c12._AUTHOR_LINE_RE, c12._AUTHOR_INLINE_RE, _AUTHOR_DASH_RE):
        for m in rx.finditer(mt, end, len(mt)):
            name = m.group(1).strip()
            if c12._NOT_NAME.match(name) or len(norm_alnum(name)) < 3 or len(mt[m.start():m.end()].strip()) > 60:
                continue
            after = mt[m.end():m.end() + 1500]
            if _DISSENT_ANY_RE.search(after) or _CONCUR_ANY_RE.search(after) or re.search(r"\bI\s+cannot\s+agree\b", after):
                new_end = len(mt)
                for rx2 in c12._END_RES:
                    m2 = rx2.search(mt, m.end() + 3000)
                    if m2:
                        new_end = min(new_end, m2.start())
                end = max(end, new_end)
                break
    runs = [r for r in _header_runs(header_judges, 0, end) if r[3] >= 2 and r[0] >= start]
    # body start correction: a sustained header-judge run before the detected body start means the body began earlier
    early = [r for r in _header_runs(header_judges, 0, start) if r[3] >= 3]
    if early:
        start = max(0, page_start_before(early[0][0], 1))
        runs = [r for r in _header_runs(header_judges, start, end) if r[3] >= 2]
    cands = []
    for m in _ESCR_AUTHOR_RE.finditer(mt, start, end):
        name = m.group(1).strip()
        if c12._NOT_NAME.match(name) or len(norm_alnum(name)) < 3:
            continue
        cands.append({"start": m.start(), "body": m.end(), "author": c12._clean_name(name), "method": "ESCR_JUDGMENT_AUTHOR", "strong": True, "note": ""})
    for m in c12._AUTHOR_LINE_RE.finditer(mt, start, end):
        name = m.group(1).strip()
        linetxt = mt[m.start():m.end()]
        if c12._NOT_NAME.match(name) or len(norm_alnum(name)) < 3 or len(linetxt.strip()) > 60 or "[" in linetxt or ".." in linetxt or "…" in linetxt:
            continue
        after = mt[m.end():m.end() + 3000]
        before = mt[max(start, m.start() - 3000):m.start()]
        first = m.start() - start < 6000
        cue = _CONCUR_ANY_RE.search(after) or _DISSENT_ANY_RE.search(after) or re.search(r"\bI\s+(?:have|am|would|wish|think|propose|hold|find)\b", after[:1500])
        sig = bool(c12._SIGNATURE_RE.search(before))
        if first or cue or sig or m.group(3):
            cands.append({"start": m.start(), "body": m.end(), "author": c12._clean_name(name), "method": "AUTHOR_LINE", "strong": bool(cue or first), "note": (m.group(3) or "")})
    for m in list(c12._AUTHOR_INLINE_RE.finditer(mt, start, end)) + list(_AUTHOR_DASH_RE.finditer(mt, start, end)):
        name = m.group(1).strip()
        if c12._NOT_NAME.match(name) or len(norm_alnum(name)) < 3:
            continue
        after = mt[m.end():m.end() + 3000]
        scr_dash = bool(re.search(r"J\.[ \t]*[\-–—:]", mt[m.start():m.end()]))
        first = m.start() - start < 6000
        cue = _CONCUR_ANY_RE.search(after) or _DISSENT_ANY_RE.search(after) or re.match(r"\s*(?:\(?On\s+behalf|I\s)", after)
        if first or cue or scr_dash:
            cands.append({"start": m.start(), "body": m.end(), "author": c12._clean_name(name), "method": "AUTHOR_INLINE", "strong": True, "note": ""})
    cands.sort(key=lambda c: c["start"])
    ops = []
    for c in cands:
        if ops and (c["start"] - ops[-1]["body"] < 1500 or same_judge(ops[-1]["author"], c["author"])):
            continue
        if ops and not c["strong"]:
            continue
        if not ops and c["start"] - start > max(6000, 0.25 * (end - start)) and not runs:
            continue
        ops.append(dict(c))
    # header runs: every sustained run whose judge has no opinion starting near it starts one (approximate start)
    for r in runs:
        if any(same_judge(o["author"], r[2]) and o["start"] <= r[0] + 2000 and r[0] - o["start"] < max(60000, r[1] - r[0] + 60000) for o in ops):
            continue
        near = [c for c in cands if same_judge(c["author"], r[2]) and r[0] - 25000 <= c["start"] <= r[0]]
        if near:
            c = dict(near[0])
            c["method"] += "+HEADER_RUN"
        else:
            ap = max(start, page_start_before(r[0], 1))
            c = {"start": ap, "body": ap, "author": c12._clean_name(r[2]), "method": "HEADER_JUDGE_RUN_APPROX_START", "strong": False, "note": ""}
        ops.append(c)
    ops.sort(key=lambda o: o["start"])
    ded = []
    for o in ops:
        if ded and (o["start"] - ded[-1]["start"] < 1500 or same_judge(ded[-1]["author"], o["author"])):
            continue
        ded.append(o)
    ops = ded
    if not ops:
        author = header_judges[0][1] if header_judges else ""
        ops = [{"start": start, "body": start, "author": c12._clean_name(author) if author else "",
                "method": "HEADER_JUDGE" if author else "OPINION_NOT_IDENTIFIED", "strong": False, "note": ""}]
    if ops[0]["start"] - start > 20000:
        # long unattributed text before the first detected opinion: its own opinion (author from headers if any)
        hn = [n for p, n in header_judges if start <= p < ops[0]["start"]]
        ops.insert(0, {"start": start, "body": start, "author": c12._clean_name(hn[0]) if hn else "",
                       "method": "TEXT_BEFORE_FIRST_AUTHOR_CUE", "strong": False, "note": ""})
    ops[0]["start"] = start
    # closing order of the court after several opinions
    court_order = None
    if len(ops) >= 2:
        last_body = ops[-1]["body"]
        for m in _ORDER_HEADING_RE.finditer(mt, last_body, end):
            if m.start() > last_body + 3000 and (end - m.start()) < 20000:
                court_order = {"start": m.start(), "body": m.end(), "author": "", "method": "CLOSING_ORDER_HEADING", "strong": True, "note": ""}
        if court_order is None:
            tail_from = max(last_body, end - 8000)
            mm = _MAJORITY_ORDER_RE.search(mt, tail_from, end) or (_SPLIT_RE.search(mt, tail_from, end))
            if mm and re.search(r"\b(?:we|the\s+Bench|Registry)\b", mt[max(tail_from, mm.start() - 300):mm.end() + 300]):
                p = mt.rfind("\n\n", tail_from, mm.start())
                if p > last_body + 3000:
                    court_order = {"start": p, "body": p, "author": "", "method": "CLOSING_ORDER_MAJORITY_OR_SPLIT_CUE", "strong": True, "note": ""}
    if court_order:
        ops.append(court_order)
    for i, o in enumerate(ops):
        o["end"] = ops[i + 1]["start"] if i + 1 < len(ops) else end
    # roles
    if len(ops) == 1:
        ops[0]["role"], ops[0]["role_basis"] = "sole", "SINGLE_OPINION_DETECTED"
    else:
        judicial = [o for o in ops if not o["method"].startswith("CLOSING_ORDER")]
        dirs = {id(o): _disposal_direction(mt[o["body"]:o["end"]]) for o in judicial}
        lead_dir = dirs.get(id(judicial[0]), "")
        tail_text = mt[max(start, end - 12000):end]
        split = bool(_SPLIT_RE.search(tail_text)) and not _MAJORITY_ORDER_RE.search(tail_text)
        for k, o in enumerate(ops):
            seg = mt[o["body"]:o["end"]]
            if o["method"].startswith("CLOSING_ORDER"):
                o["role"] = "court_order"
                o["role_basis"] = "SPLIT_CUE_IN_ORDER" if split else "CLOSING_ORDER_AFTER_OPINIONS"
                continue
            if len(judicial) == 1:
                o["role"], o["role_basis"] = "sole", "SINGLE_OPINION_PLUS_CLOSING_ORDER"
                continue
            dis = _window_cue(_DISSENT_ANY_RE, seg)
            con = _window_cue(_CONCUR_ANY_RE, seg)
            if split and len(judicial) == 2:
                o["role"], o["role_basis"] = "split_opinion", "TWO_OPINIONS_WITH_SPLIT_OR_REFERENCE_CUE"
            elif k == 0:
                o["role"], o["role_basis"] = "lead", "FIRST_OPINION"
            elif dis or "dissent" in (o.get("note") or "").lower():
                o["role"], o["role_basis"] = "dissent", ("DISSENT_CUE:" + squash(dis.group(0), 60)) if dis else "DISSENT_NOTE"
            elif lead_dir and dirs.get(id(o)) and dirs[id(o)] != lead_dir:
                o["role"], o["role_basis"] = "dissent", "DISPOSAL_OPPOSES_FIRST_OPINION(%s vs %s)" % (dirs[id(o)], lead_dir)
            elif con:
                o["role"], o["role_basis"] = "concurring", "CONCUR_CUE:" + squash(con.group(0), 60)
            else:
                o["role"], o["role_basis"] = "separate", "LATER_OPINION_NO_CUE"
        if ops[0]["role"] == "lead":
            later = [o for o in judicial[1:]]
            if later and all(o["role"] == "concurring" for o in later):
                ops[0]["role"], ops[0]["role_basis"] = "lead_majority", "ALL_LATER_OPINIONS_CONCUR"
            elif len(judicial) == 2 and later[0]["role"] == "dissent":
                ops[0]["role"], ops[0]["role_basis"] = "lead_majority", "TWO_OPINIONS_SECOND_DISSENTS"
    for i, o in enumerate(ops):
        o["opinion_id"] = "OP%d" % (i + 1)
    return ops, start, end


COURT_ROLES = ("sole", "lead_majority", "lead", "court_order", "concurring")


def court_status(role):
    """How an item from an opinion with this role relates to the court's decision."""
    return {
        "sole": "OPINION_OF_THE_COURT",
        "lead_majority": "MAJORITY_OPINION_CANDIDATE",
        "lead": "FIRST_OPINION_MAJORITY_NOT_DETERMINED",
        "court_order": "ORDER_OF_THE_COURT",
        "concurring": "CONCURRING_OPINION_NOT_NECESSARILY_THE_COURT",
        "separate": "SEPARATE_OPINION_STATUS_NOT_DETERMINED",
        "dissent": "DISSENT_NOT_THE_COURT",
        "split_opinion": "SPLIT_VERDICT_NO_MAJORITY",
    }.get(role, "UNKNOWN")


# ------------------------------------------------------------------ quotation source attribution
_CASE_NAME_RE = re.compile(r"((?:[A-Z][\w.&'’\-]*\s+){0,6}[A-Z][\w.&'’\-]*\s+(?:v\.|vs\.?|versus)\s+(?:[A-Z][\w.&'’\-]*\s*){1,6})")
_SUPRA_RE = re.compile(r"\b(?:in\s+)?([A-Z][\w.&'’\-]*(?:\s+[A-Z][\w.&'’\-]*){0,4})\s*\(\s*supra\s*\)", re.I)
_STATUTE_SRC_RE = re.compile(r"((?:Section|Sections|Rule|Rules|Regulation|Regulations|Article|Articles|Para(?:graph)?|Clause|Order|Notification|Policy|Letter|Circular)\s*[\w().\-]*"
                             r"(?:\s+(?:of|to|under)\s+the\s+[A-Z][\w\s,()]{2,80}?(?:Act|Rules|Regulations|Constitution|Code|Order|Instructions?)(?:,?\s+\d{4})?)?)", re.I)
_LOWER_SRC_RE = re.compile(r"\b((?:the\s+)?(?:learned\s+)?(?:Armed\s+Forces\s+)?(?:Tribunal|AFT|High\s+Court|Single\s+Judge|Division\s+Bench|trial\s+court|Court[\s\-]Martial|"
                           r"General\s+Court\s+Martial|Summary\s+Court\s+Martial|Medical\s+Board|Release\s+Medical\s+Board|Court\s+of\s+Inquiry|appellate\s+authority|confirming\s+authority))", re.I)

QUOTE_KIND_MAP = {
    "quoted_precedent": "precedent",
    "statutory_or_document_quotation": "statute_or_document",
    "lower_court_quotation": "lower_forum",
    "submission_quotation": "submission",
    "quoted_other": "other",
}


def quote_source(mt, qs, kind, start):
    intro = squash(mt[max(start, qs - 450):qs])
    src = ""
    if kind == "quoted_precedent":
        ms = list(_CASE_NAME_RE.finditer(intro)) or list(_SUPRA_RE.finditer(intro))
        if ms:
            src = squash(ms[-1].group(1), 120)
    elif kind == "statutory_or_document_quotation":
        ms = list(_STATUTE_SRC_RE.finditer(intro))
        if ms:
            src = squash(ms[-1].group(1), 120)
    elif kind == "lower_court_quotation":
        ms = list(_LOWER_SRC_RE.finditer(intro))
        if ms:
            src = squash(ms[-1].group(1), 80)
    elif kind == "submission_quotation":
        src = "party submission / pleading"
    return src or None, intro[-160:]


# ------------------------------------------------------------------ voice rules (C13 additions)
_PRECEDENT_QUESTION_RE = re.compile(
    r"\b(?:the\s+)?(?:issue|question|point|controversy)s?\s+(?:for\s+consideration\s+|that\s+arose\s+|which\s+arose\s+|involved\s+|raised\s+)?(?:before|in)\s+(?:this|the|that)\s+(?:Court|Bench)\s+(?:in\s+that\s+case\s+)?(?:was|were)\b"
    r"|^\W*There,?\s+the\s+(?:question|issue|point)\b|\bThe\s+question\s+before\s+(?:this|the)\s+(?:court|Court)\s+was\b|\bin\s+that\s+case\b|\bthe\s+Court\s+came\s+to\s+the\s+conclusion"
    r"|\bthe\s+(?:issue|question)\s+(?:for\s+consideration\s+)?(?:there|then)\s+was\b|\bthe\s+(?:facts|appellant|respondent)\s+(?:in\s+that\s+case|there)\b", re.I)
_PRECEDENT_PAST_RE = re.compile(
    r"\b(?:this\s+Court|the\s+Court|the\s+Bench|their\s+Lordships|the\s+Constitution\s+Bench|(?:two|three|five|seven|nine)[\s\-]Judge\s+Bench|the\s+Privy\s+Council|the\s+House\s+of\s+Lords|his\s+Lordship|it)\s+"
    r"(?:had\s+|has\s+)?(?:held|observed|ruled|opined|laid\s+down|reiterated|explained|noted|found|declared|stated|said|emphasi[sz]ed|clarified|followed|took\s+the\s+view|was\s+of\s+the\s+view|came\s+to)"
    r"|\bit\s+was\s+(?:held|observed|ruled|laid\s+down|declared)\b", re.I)
_CASE_REF_RE = re.compile(r"\b(?:v\.|vs\.?|versus)\s+[A-Z]|\(\s*supra\s*\)|\b\d{4}\)?\s*\d+\s+SCC\b|\bAIR\s+\d{4}|\bSCR\b|\bINSC\b|\bSCALE\b", re.I)
_OWN_MARK_RE = re.compile(r"\b(?:we|us|our|I|my)\b|\bin\s+the\s+(?:present|instant)\s+case\b|\bthe\s+present\s+(?:appeal|case|petition)\b", re.I)
_REJECT_EXTRA_RE = re.compile(r"\b(?:this|the|that|such)\s+(?:submission|contention|argument|plea|stand)\s+(?:is|was)\s+(?:clearly\s+|wholly\s+|totally\s+|entirely\s+|thoroughly\s+)?"
                              r"(?:misconceived|untenable|misplaced|fallacious|without\s+(?:any\s+)?(?:merit|substance|force)|devoid\s+of|not\s+tenable|well[\s\-]?founded|correct|sound|acceptable|unacceptable)", re.I)
_ANALYSIS_START_RE = re.compile(
    r"^\W*(?:\d+\s*[.)]?\s*)?(?:We\s+have\s+(?:heard|considered|given|carefully|bestowed|perused|gone\s+through|examined)|Having\s+(?:heard|considered|given|perused|gone\s+through)|"
    r"We\s+have\s+given\s+our|I\s+have\s+(?:heard|considered|given)|We\s+shall\s+now\s+(?:consider|examine|deal)|Let\s+us\s+(?:now\s+)?(?:consider|examine)|Now,?\s+coming\s+to|"
    r"(?:Analysis|Discussion|Consideration)\b)", re.I)


_SUBM_LEAD_RE = re.compile(r"^\W*(?:\d+\s*[.)]?\s*)?(?:It\s+(?:was|is|has\s+been|had\s+been)\s+(?:also\s+|further\s+)?(?:submitted|contended|urged|argued|canvassed|pleaded)"
                           r"|(?:The\s+)?(?:learned|ld\.?)\s+(?:senior\s+|additional\s+)?(?:counsel|advocate|solicitor|attorney)|(?:Mr|Ms|Mrs|Shri|Sh)\.?\s+[A-Z]|Counsel\s+for\s+the)", re.I)


def classify_voice(sent, quote, prev_voice_in_para, para_has_case_ref, section):
    """Deterministic voice. Returns (voice, basis)."""
    if quote is not None:
        return "quotation:" + QUOTE_KIND_MAP.get(quote[2], "other"), "INSIDE_QUOTED_BLOCK"
    own = bool(_OWN_MARK_RE.search(sent))
    rej = bool(c12._REJECT_ACCEPT_RE.search(sent) or _REJECT_EXTRA_RE.search(sent))
    strong = bool(c12._STRONG_RE.search(sent)) and own
    if (c12._PRECEDENT_REPORT_RE.search(sent) or _PRECEDENT_QUESTION_RE.search(sent)) and not re.search(r"\b(?:we|us|our)\b", sent, re.I):
        return "precedent_report", "PRECEDENT_REPORT_PATTERN"
    if _PRECEDENT_PAST_RE.search(sent) and (_CASE_REF_RE.search(sent) or para_has_case_ref) and not own and not rej:
        return "precedent_report", "PAST_TENSE_REPORT_AFTER_CASE_CITATION"
    subm_lead = bool(_SUBM_LEAD_RE.match(sent))
    subm = bool(c12._SUBMISSION_RE.search(sent)) and not rej and (subm_lead or not strong) and not re.match(r"^\W*(?:\d+\s*[.)]?\s*)?(?:We|In\s+our|I)\b", sent)
    if subm:
        return "submission", "SUBMISSION_PATTERN"
    if c12._LOWER_RE.search(sent) and not c12._COURT_ASSESS_RE.search(sent):
        return "lower_forum", "LOWER_FORUM_REPORT_PATTERN"
    if prev_voice_in_para in ("submission", "precedent_report"):
        pivot = bool(c12._OWN_PIVOT_RE.search(sent)) or rej or own
        if not pivot:
            return prev_voice_in_para, "CARRIED_FROM_PARAGRAPH_" + prev_voice_in_para.upper()
    if section == "SUBMISSIONS" and not (c12._OWN_PIVOT_RE.search(sent) or rej or strong):
        return "submission", "IN_SUBMISSIONS_SECTION"
    return "court", ("COURT_REJECTS_OR_ACCEPTS" if rej else "DEFAULT_COURT")


# ------------------------------------------------------------------ main segmentation
def segment(text, meta):
    """Return a dict with opinions, paragraphs, headings, quotes and sentence records."""
    court = meta.get("court", "")
    pidx = c12.page_index(text)
    page_starts = [p for p, _ in pidx]
    mt, header_judges = c12.noise_mask(text)
    header_judges = header_judges_c13(text, mt, header_judges)
    start, end, start_method, headnote = c12.find_body(text, mt, court)
    opinions, start, end = find_opinions(text, mt, start, end, header_judges, page_starts)
    c12ops = [{"start": o["start"], "end": o["end"]} for o in opinions]
    paras = c12.find_paragraphs(mt, c12ops)
    para_starts = [p[0] for p in paras]
    headings = c12.find_headings(mt, start, end)
    quotes = c12.find_quotes(mt, start, end, para_starts)
    qinfo = []
    for (a, b, k) in quotes:
        src, intro = quote_source(mt, a, k, start)
        qinfo.append({"start": a, "end": b, "kind": QUOTE_KIND_MAP.get(k, "other"), "source": src, "intro_tail": intro})
    forced = sorted(set(para_starts + [h[0] for h in headings] + [q[0] for q in quotes] + [q[1] for q in quotes]
                        + [o["body"] for o in opinions] + [o["start"] for o in opinions]))
    spans = c12.sentences(mt, start, end, forced)
    blocks = [m.start() for m in re.finditer(r"\n[ \t]*\n", mt)]
    op_starts = [o["start"] for o in opinions]

    def opinion_of(pos):
        i = bisect.bisect_right(op_starts, pos) - 1
        return max(0, i)

    recs = []
    para_voice = {}
    para_case = {}
    analysis_started = {}
    for (s, e) in spans:
        sent = squash(mt[s:e])
        if len(norm_alnum(sent)) < 8:
            continue
        oi = opinion_of(s)
        op = opinions[oi]
        if s < op["body"] and op["body"] - s < 200:
            continue
        pa = c12.para_at(paras, s)
        pkey = (pa[0] if pa and pa[2] == oi else ("b", bisect.bisect_right(blocks, s)))
        sect = c12.section_at(headings, s)
        q = c12.quote_at(quotes, s)
        voice, basis = classify_voice(sent, q, para_voice.get(pkey), para_case.get(pkey, False), sect)
        if q is None:
            if _CASE_REF_RE.search(sent):
                para_case[pkey] = True
            if voice in ("submission", "precedent_report", "court"):
                para_voice[pkey] = voice
        if voice == "court" and (_ANALYSIS_START_RE.search(sent) or sect in ("ANALYSIS", "CONCLUSION")):
            analysis_started.setdefault(oi, s)
        qd = None
        if q is not None:
            qd = next((x for x in qinfo if x["start"] == q[0]), None)
        recs.append({
            "s": s, "e": e, "sent": sent, "oi": oi, "para": pa[1] if pa and pa[2] == oi else None, "para_key": pkey,
            "section": sect or "", "voice": voice, "voice_basis": basis,
            "quote_kind": qd["kind"] if qd else None, "quote_source": qd["source"] if qd else None,
            "in_analysis_zone": oi in analysis_started and s >= analysis_started[oi],
        })
    # position features
    by_op = {}
    for i, r in enumerate(recs):
        by_op.setdefault(r["oi"], []).append(i)
    for oi, idx in by_op.items():
        n = len(idx)
        court_idx = [i for i in idx if recs[i]["voice"] == "court"]
        for k, i in enumerate(idx):
            recs[i]["pos_in_op"] = (k + 1) / float(n)
        for k, i in enumerate(court_idx):
            recs[i]["court_rank_from_end"] = len(court_idx) - k
        recs_n = len(court_idx)
        for i in idx:
            recs[i]["n_court_in_op"] = recs_n
    # paragraph position
    pk_members = {}
    for i, r in enumerate(recs):
        pk_members.setdefault((r["oi"], r["para_key"]), []).append(i)
    for members in pk_members.values():
        for k, i in enumerate(members):
            recs[i]["para_first"] = k == 0
            recs[i]["para_last"] = k == len(members) - 1
            recs[i]["para_len"] = len(members)
    numbered = len(paras) >= 5
    return {
        "mt": mt, "pidx": pidx, "start": start, "end": end, "start_method": start_method, "headnote": headnote,
        "opinions": opinions, "paras": paras, "numbered_paragraphs": numbered, "headings": headings,
        "quotes": qinfo, "recs": recs,
    }
