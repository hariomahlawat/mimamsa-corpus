#!/usr/bin/env python3
"""C13-A5 deliverable 2: passage-level judicial-treatment classification (local, CPU, standard library).

Improves on C11 (rev. 1.3) by classifying the whole anchored passage rather than a single cue word:
  * passages = every C11 citation-graph anchor in the judgment body (one per edge) + every C11 treatment-candidate
    passage (cue rows and adviser leads), located in the full text at ad77758d;
  * the passage is the sentence carrying the anchor plus the next sentence when it opens with a back-reference;
  * voice gate (court's own voice vs quotation, submission, report of another forum, reporter matter), interrogative,
    negation, binding (one authority in the clause or explicit back-reference), opinion (separate/dissent) and
    competence (who may overrule) are tested before a type is assigned;
  * types: FOLLOWS, APPLIES, DISTINGUISHES, CONSIDERS, EXPLAINS, DOUBTS, DISAPPROVES, OVERRULES; otherwise CITES only;
  * C11 V13-01..V13-04 are addressed: plea/objection/argument subjects, straight-quote and "held thus:" quotations,
    rhetorical questions and "no one has said" negations never yield a treatment; unbound leads keep the target as
    raw text plus the preceding sentences for demonstratives, and never adopt a page-header candidate as target;
    several cues in one sentence give one passage.
OVERRULES is never inferred from criticism, adverse discussion or distinguishing: it needs explicit overruling words
("overrule(d)") in the court's own voice, bound to the authority, from a Supreme Court judgment, outside a separate or
dissenting opinion. Even then it is a candidate (AUTOMATED_CANDIDATE_NOT_VERIFIED). Declaratory wording without
"overrule" ("does not lay down the correct law") is DISAPPROVES with overruling_language=DECLARATORY_ONLY.

Development: in-sample against the C11 reviewed rows (review rounds 1-3; DEV labels in treatment/DEV_LABELS_C13.csv).
A0's fresh sample (H-REL-C13, branch claude/c13-a0-eval @5e07e010): only its identifier columns (rep_doc_id,
rep_sha256, page) are read, to flag those pages and keep them out of development scoring; no passage is read.
The extractor is not frozen.

  python -I -B treatment_c13.py [--repo /home/user/c7] [--check]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_c13 as C  # noqa: E402

C11DIR = C.AUDIT / "C11-JUDICIAL-QUALITY"
REL = C11DIR / "relations" / "outputs"
OUT = C.PKG / "treatment"
VERSION = "treatment-c13/0.9.0-dev"   # not frozen: awaiting coordinator confirmation that A0 is accepted

_spec = importlib.util.spec_from_file_location("relations_c11", C11DIR / "relations" / "tools" / "relations_c11.py")
R11 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R11)

TYPES = ["OVERRULES", "DISAPPROVES", "DOUBTS", "DISTINGUISHES", "FOLLOWS", "APPLIES", "EXPLAINS", "CONSIDERS"]
I = re.I
LEX = {
    "OVERRULES": [r"\b(?:is|are|was|were|be|been|stands?|hereby\s+stands?)\s+(?:hereby\s+|accordingly\s+|therefore\s+|thus\s+|consequently\s+|also\s+)?over-?\s?ruled\b",
                  r"\bwe\s+(?:[a-z]+\s+){0,2}overrule\b", r"\boverrule\s+the\s+(?:same|said|decision|judgment|view)"],
    "DISAPPROVES": [r"\bdo(?:es)?\s+not\s+lay\s+down\s+(?:the\s+|a\s+)?(?:correct|good|right)\s+(?:law|position|proposition)",
                    r"\b(?:is|are)\s+(?:no\s+longer|not)\s+(?:a\s+)?good\s+law", r"\bwrongly\s+decided\b|\bdecided\s+wrongly\b",
                    r"\bdisapprov(?:e|ed|ing)\b", r"\bwe\s+(?:are\s+)?(?:unable|not\s+able)\s+to\s+(?:agree|subscribe|accept)\b",
                    r"\b(?:we\s+are\s+)?(?:,\s*)?(?:therefore\s*,?\s*)?not\s+in\s+agreement\s+with\b",
                    r"\bcannot\s+be\s+(?:accepted|regarded|treated)\s+as\s+(?:laying\s+down\s+)?(?:the\s+)?(?:correct|good)\s+law"],
    "DOUBTS": [r"\bdoubt(?:ed)?\s+the\s+correctness\s+of\s+(?:the\s+)?(?:said\s+|aforesaid\s+|above\s+)?(?:decision|judgment|view|ratio|law\s+laid\s+down|dictum|proposition)\b", r"\bcorrectness\s+of\s+[^.;]{0,80}\bdoubted\b", r"\b(?:requires?|needs?|merits?)\s+reconsideration\b",
               r"\b(?:is|are)\s+(?:clearly\s+|thus\s+|therefore\s+)?per\s+incuriam\b", r"\bnot\s+(?:entirely\s+)?free\s+from\s+doubt\b",
               ],
    "DISTINGUISHES": [r"\bdistinguishable\b", r"\b(?:is|are|was|were|be|been|clearly|easily)\s+(?:clearly\s+|easily\s+)?distinguished\b",
                      r"\bwe\s+(?:[a-z]+\s+){0,2}distinguish\b",
                      r"\b(?:is|are|was|would\s+be)\s+of\s+no\s+(?:assistance|help|avail)\b",
                      r"\bdoes\s+not\s+(?:apply|help|assist|come\s+to\s+the\s+(?:aid|rescue))\b", r"\bhas\s+no\s+application\b",
                      r"\b(?:would|will)\s+not\s+(?:apply|be\s+applicable)\b",
                      r"\breliance\s+(?:placed\s+)?(?:by\s+[^;]{0,40}\s+)?(?:on|upon)\s+[^;]{0,160}?\bis\s+(?:grossly\s+|wholly\s+|totally\s+|clearly\s+)?(?:misplaced|misconceived|of\s+no\s+(?:assistance|help))",
                      r"\bcannot\s+place\s+reliance\s+on\s+the\s+same\b", r"\btherefore\s+not\s+applicable\b", r"\bnot\s+applicable\s+to\s+the\s+(?:facts|present|case)",
                      r"\bfacts\s+(?:of\s+(?:that|the\s+said)\s+case\s+)?(?:were|are)\s+(?:entirely\s+|completely\s+|quite\s+)?(?:different|distinguishable)",
                      r"\bon\s+(?:its\s+own\s+)?(?:different\s+)?facts\b[^.;]{0,30}\bdistinguish"],
    "FOLLOWS": [r"\bwe\s+(?:[a-z]+\s+){0,2}follow\b", r"\bwe\s+have\s+(?:consistently\s+|always\s+)?followed\s+the\s+(?:law|ratio|decision|judgment|view)", r"\b(?:is|are|be)\s+(?:respectfully\s+)?followed\b(?!\s+by\b)",
                r"\bwe\s+(?:respectfully\s+)?(?:agree|concur)\s+with\b", r"\b(?:squarely|fully|clearly)?\s*covered\s+by\b",
                r"\bgoverned\s+by\s+the\s+(?:decision|judgment|ratio|law)", r"\bwe\s+are\s+bound\s+by\b", r"\bbinding\s+(?:on|upon)\s+(?:us|this\s+(?:Court|Bench|Tribunal))",
                r"\b(?:in\s+view\s+of|in\s+the\s+light\s+of|in\s+terms\s+of)\s+the\s+(?:law\s+laid\s+down|ratio|decision|judgment|dictum)\s+(?:in|of)\b",
                r"\bno\s+longer\s+res\s+integra\b", r"\b(?:is|has\s+been|stands|was)\s+(?:already\s+|now\s+)?settled\s+by\b",
                r"\bsettled\s+by\s+the\s+(?:decision|judgment)"],
    "APPLIES": [r"\bapplying\s+the\s+(?:ratio|principles?|test|law|dictum)\b", r"\b(?:ratio|principles?|law)\s+(?:laid\s+down|enunciated)\s+in\s+[^.;]{0,120}\bappl(?:y|ies|ied)\b",
                r"\b(?:appl(?:y|ies)|applicable)\s+(?:with\s+full\s+force|on\s+all\s+fours|squarely)\b", r"\bon\s+all\s+fours\b",
                r"\bthe\s+(?:same|said)\s+(?:principle|ratio)\s+(?:would\s+)?appl(?:y|ies)\b"],
    # EXPLAINS = the citing court explains the authority. "X has been explained in <case>" says the authority explains a
    # principle, which is CONSIDERS (review F03, T37-T40).
    "EXPLAINS": [r"\bwe\s+(?:have\s+)?(?:already\s+)?explained\s+the\s+(?:ratio|scope|import)\s+of\b",
                 r"\b(?:the\s+)?ratio\s+(?:of|in)\s+[^.;]{0,80}\b(?:is|was)\s+(?:only\s+)?that\b", r"\bwhat\s+was\s+(?:held|decided)\s+in\b"],
    "CONSIDERS": [r"\bthis\s+Court\s+(?:has\s+)?(?:held|observed|ruled|opined|considered|examined|dealt)\b",
                  r"\b(?:has|have|was|were)\s+been\s+(?:explained|clarified)\s+(?:in|by)\b|\b(?:was|were)\s+(?:explained|clarified)\s+in\b",
                  r"\b(?:it|the\s+Court)\s+was\s+(?:held|observed)\b", r"\breference\s+may\s+(?:also\s+)?be\s+made\s+to\b",
                  r"\b(?:we\s+(?:have\s+)?(?:considered|noticed|referred|perused|examined))\b", r"\b(?:considered|noticed|examined)\s+(?:in|the\s+decision)\b"],
}
LEXC = {t: [re.compile(p, I) for p in ps] for t, ps in LEX.items()}

PLEA_SUBJECT = re.compile(r"\b(?:objections?|pleas?|contentions?|arguments?|submissions?|preliminary|prayer|application|request)\b[^.;]{0,60}$", I)
INTERROG = re.compile(r"\?\s*$")
NO_ONE_SAID = re.compile(r"\bno\s+one\s+(?:has\s+)?(?:said|suggested|held|contended)\b|\bit\s+cannot\s+be\s+said\s+that\b|\bnor\s+can\s+it\s+be\s+said\b", I)
STRAIGHT_LEADIN = re.compile(r"(?:held|observed|said|ruled|stated)\s+(?:thus|as\s+(?:under|follows))\s*:", I)
BACKREF = re.compile(r"^\s*(?:In\s+(?:that|the\s+said)\s+(?:case|decision|judgment)|There(?:in)?,?|That\s+(?:decision|judgment|case)|"
                     r"The\s+said\s+(?:decision|judgment)|This\s+(?:decision|judgment)|The\s+(?:ratio|principle)\s+(?:of|in)\s+(?:that|the\s+said))", I)
DEMONSTRATIVE = re.compile(r"\b(?:these|those|the\s+said|both\s+the|the\s+above|the\s+aforesaid)\s+(?:two\s+|three\s+|four\s+)?(?:decisions|judgments|cases|authorities)\b", I)
SEPARATE = {"SEPARATE_OPINION", "DISSENT"}
STRONG = {"OVERRULES", "DISAPPROVES", "DOUBTS"}
COURT_REJECTS_RELIANCE = re.compile(r"\breliance\s+(?:placed|sought\s+to\s+be\s+placed)\b[^;]{0,200}?\b(?:misplaced|misconceived|of\s+no\s+(?:assistance|help|avail)|does\s+not\s+help)|"
                                    r"\b(?:is|are)\s+(?:apparently\s+|clearly\s+)?distinguishable\b|\bcannot\s+place\s+reliance\b", I)
PARA_START = re.compile(r"(?:^|\s)\d{1,3}\s?\.\s(?=[A-Z\u201c\"(])")
SUBMIT_LEAD = re.compile(r"\b(?:submitted|contended|argued|urged|pleaded|canvassed)\s+(?:before\s+us\s+)?that\b|\bsubmission\s+(?:of|on\s+behalf\s+of)\b|"
                         r"\bit\s+is\s+the\s+case\s+of\s+the\b|\baccording\s+to\s+(?:the\s+)?learned\s+counsel\b", I)
REPORTED_AFTER = re.compile(r"^[\s,]*(?:by|in)\s+(?:the\s+)?(?:(?:case|judgment|decision)s?\s+(?:of|in)\s+)?(?:[A-Z(\[]|this\s+Court|a\s+(?:larger|Constitution))")
REPORTED_TREATMENT = re.compile(r"\b(?:over-?\s?ruled|disapproved|doubted|distinguished|followed|explained|affirmed|reversed)\s+(?:in|by)\s+(?:the\s+)?(?:(?:case|judgment|decision)s?\s+(?:of|in)\s+)?(?:[A-Z(\[]|this\s+Court|a\s+(?:larger|Constitution))")


A0_COMMIT = "5e07e010"   # claude/c13-a0-eval head carrying H-REL-C13 (identifiers only are read)
A0_SAMPLE = "legal_knowledge/audit_work/C13-A0-EVAL/outputs/holdouts/H-REL-C13/SAMPLE.csv"
HOLDOUT_ID_COLUMNS = ("rep_doc_id", "rep_sha256", "page")


def holdout_pages():
    """(doc_id, page) and (sha256, page) keys of the A0 relation holdout. Only identifier columns are parsed; the sample
    file has no passage text, and no passage of those pages is read for development. Returns (keys, provenance)."""
    import csv as _csv
    import io as _io
    try:
        raw = C.git(C.WT, "show", "%s:%s" % (A0_COMMIT, A0_SAMPLE))
    except Exception:  # branch not present: fail closed for scoring but allow the build
        return None, dict(available=False)
    keys = set()
    for r in _csv.DictReader(_io.StringIO(raw.decode("utf-8"))):
        r = {k: r[k] for k in HOLDOUT_ID_COLUMNS}
        keys.add(("doc", r["rep_doc_id"], str(r["page"])))
        keys.add(("sha", r["rep_sha256"], str(r["page"])))
    return keys, dict(available=True, commit=A0_COMMIT, path=A0_SAMPLE, sha256=C.sha256_bytes(raw), id_columns_read=list(HOLDOUT_ID_COLUMNS),
                      pages=len(keys) // 2)


QUOTE_LEADIN_X = re.compile(r"(?:reproduced|extracted|quoted|set\s+out)\s+(?:here\s*)?(?:in\s*)?(?:below|hereunder|hereinbelow|hereinafter|as\s+under|as\s+follows)\s*[:\-]|"
                            r"(?:which\s+)?reads?\s+as\s+(?:under|follows)\s*[:\-]|(?:observed|held|stated|opined|ruled)\s+(?:thus|as\s+(?:under|follows)|in\s+the\s+following\s+(?:terms|words))\s*[:\-]|"
                            r"in\s+(?:para(?:graph)?s?\s*[\d,\s&and-]+\s+of\s+)?(?:the\s+said|that)\s+(?:judgment|decision)[^.:]{0,60}:\s*[\-\u2013]?", I)
PARTY_LEAD = re.compile(r"\b(?:the\s+)?(?:petitioners?|appellants?|respondents?|applicants?|claimants?|learned\s+counsel|counsel)\s+(?:had\s+)?(?:primarily\s+|mainly\s+|also\s+|further\s+)?"
                        r"(?:contended|contented|submitted|argued|urged|pleaded|relied|placed\s+reliance|canvassed|asserted)\b", I)
FN_GLUED = re.compile(r"(?:(?<=[A-Za-z\)])|(?<=[A-Za-z]\.))(\d{1,3})(?=[\s,;:)]|\.(?!\d)|$)")
STATUTORY_SUBJECT = re.compile(r"\b(?:Article|Section|Rule|Regulation|Order|Para(?:graph)?|amendment|provision|circular|policy|notification|"
                               r"Act|Rules|Regulations|clause|proviso|Schedule|letter|order)\b", I)
FOOTNOTE_ZONE = re.compile(r"\u201d,\s*hereinafter|\bhereinafter\b\s+\d{1,3}\s|Digitally\s+Signed|Signature\s+Not\s+Verified", I)
NOT_A_MARKER = re.compile(r"(?:\b(?:Nos?|no|nos|Para|para|paras|Rule|rule|r|rr|Art|Arts|Sec|sec|S|s|ss|Vol|vol|p|pp|Ex|Sr|Annexure|Annex|OA|O\.A|CWP|WP|SLP|CA|Item|item|Clause|cl|Reg|Regn|Appendix|Form)\.?\s?)$")
SC_REPORT = re.compile(r"\bAIR\s+\d{4}\s+SC\b|\bSCC\b|\bS\.?C\.?R\.?\b|\bINSC\b|\bSCALE\b", I)
NAMED_CASES = re.compile(r"\b[A-Z][A-Za-z.]+(?:\s+[A-Z][A-Za-z.]+){0,3}(?:'s)?\s+case\b")
PAST_PASSIVE = re.compile(r"\b(?:was|were|had\s+been)\s+(?:also\s+|duly\s+|subsequently\s+)?(?:distinguished|followed|explained|overruled|doubted|applied)\b", I)


def quoted_across_paragraphs(t, s0, s1):
    """Quotation state tracked across paragraphs and pages (review F02): an unclosed curly quote within 6,000 characters
    before the sentence, a reproduction lead-in with no closing quote since, or a closing quote shortly after the sentence
    with no opening quote in between (the sentence ends a reproduced passage)."""
    look = t[max(0, s0 - 6000):s0]
    if look.count("\u201c") > look.count("\u201d"):
        return True, "more opening than closing curly quotation marks in the preceding 6,000 characters (cross-paragraph)"
    el = None
    for m in re.finditer(r"\b(?:xx+\s+){2}xx+\b|\bx\s+x\s+x\b", t[max(0, s0 - 3000):s0], I):
        el = m
    def still_open(seg):   # a closing quote only ends the reproduction if it is unbalanced (inner quoted words are balanced)
        return seg.count("\u201d") <= seg.count("\u201c") and seg.count('"') % 2 == 0
    if el is not None and still_open(t[max(0, s0 - 3000) + el.end():s0]):
        return True, "follows an elision marker ('xx xx xx') of a reproduced passage with no closing quotation mark"
    lead = None
    for m in QUOTE_LEADIN_X.finditer(t, max(0, s0 - 3000), s0):
        lead = m
    if lead is not None and still_open(t[lead.end():s0]):
        return True, "follows a reproduction lead-in ('%s') with no closing quotation mark" % lead.group(0)[:40]
    fwd = t[s1:s1 + 400]
    c, o = fwd.find("\u201d"), fwd.find("\u201c")
    if 0 <= c < 60 and (o < 0 or o > c) and "\u201d" not in t[s0:s1] and "\u201c" not in t[s0:s1]:
        return True, "a closing quotation mark follows the sentence: it ends a reproduced passage"
    return False, ""


class OffsetMap:
    """Map offsets in the whitespace-collapsed text back to the original data/text file, page-relative (review F06).
    char_start/char_end count from the character after the page's '[[page N]]' marker in data/text at ad77758d."""

    def __init__(self, orig):
        import bisect as _b
        self._b = _b
        self.orig = orig
        self.cstart, self.astart, self.removed, self.length = [], [], [], []
        rem = 0
        for m in re.finditer(r"\s+", orig):
            self.cstart.append(m.start() - rem)
            self.astart.append(m.start())
            self.removed.append(rem)
            self.length.append(m.end() - m.start())
            rem += m.end() - m.start() - 1
        self.marks = [(m.end(), int(m.group(1))) for m in re.finditer(r"\[\[page (\d+)\]\]", orig)]
        self.mark_pos = [x[0] for x in self.marks]

    def orig_offset(self, c):
        i = self._b.bisect_right(self.cstart, c) - 1
        if i < 0:
            return c
        if c == self.cstart[i]:
            return self.astart[i]
        return c + self.removed[i] + self.length[i] - 1

    def page_relative(self, cs, ce):
        os_, oe = self.orig_offset(cs), self.orig_offset(ce)
        j = self._b.bisect_right(self.mark_pos, os_) - 1
        if j < 0:
            return None, os_, oe
        base, page = self.marks[j]
        return page, os_ - base, oe - base


def clean_raw_target(raw):
    """Drop a leading word fragment cut by the C11 clip ('isposed of in ...' -> '… of in ...') (review F08)."""
    raw = (raw or "").strip()
    if raw and raw[0].islower() and " " in raw:
        return "\u2026 " + raw.split(" ", 1)[1]
    return raw


def collapse(t):
    return re.sub(r"\s+", " ", t)


def sentence(t, s, e, lo=0, hi=None):
    hi = len(t) if hi is None else hi
    return R11.sentence_bounds(t, s, e, lo, hi)


def count_authorities(t, s, e):
    return len(R11.find_citations(t, s, e))


def classify(t, court, anchor_s, anchor_e, opinion, zone, target_court, marker_bound=False):
    """Return dict(relation, voice, reasons, cue, s0, s1, evidence)."""
    s0, s1 = sentence(t, anchor_s, anchor_e)
    sent = t[s0:s1]
    nxt0, nxt1 = sentence(t, min(len(t) - 1, s1 + 1), min(len(t), s1 + 2))
    nxt = t[nxt0:nxt1] if nxt0 >= s1 else ""
    window_end = nxt1 if (nxt and BACKREF.search(nxt)) else s1
    passage = t[s0:window_end]
    reasons = []
    if zone == "REPORTER_EDITORIAL":
        return dict(relation="CITES", voice="REPORTER_EDITORIAL", reasons="reporter headnote or case-law list; not the court's words",
                    cue="", s0=s0, s1=window_end)
    para_lo = max(0, s0 - 4000)
    for m in PARA_START.finditer(t, para_lo, s0 + 1):
        para_lo = m.start()
    q, why = R11.in_quotation(t, s0 + 1, para_lo)
    if not q:
        look = t[max(para_lo, s0 - 1500):anchor_s]
        lead = None
        for m in STRAIGHT_LEADIN.finditer(look):
            lead = m
        if lead is not None and not re.search(r"[”\"]", look[lead.end():]):
            q, why = True, "follows a 'held thus:' lead-in with no closing quotation mark (V13-01)"
    if not q:
        q, why = quoted_across_paragraphs(t, s0, s1)
    if q:
        return dict(relation="CITES", voice="QUOTED_PASSAGE", reasons=why, cue="", s0=s0, s1=window_end)
    lead = t[max(para_lo, s0 - 700):s0]
    counsel_verb = re.search(r"\b(?:would\s+)?(?:submit(?:s|ted)?|contend(?:s|ed)?|argue[sd]?|urge[sd]?)\b|\blearned\s+(?:senior\s+)?(?:panel\s+)?counsel\b", sent, I)
    sub_sent = R11.SUBMISSION2.search(sent) and (not COURT_REJECTS_RELIANCE.search(sent) or counsel_verb)
    sub_lead = SUBMIT_LEAD.search(lead) and not R11.COURT_VOICE2.search(lead[SUBMIT_LEAD.search(lead).end():] if SUBMIT_LEAD.search(lead) else "")
    sub_party = PARTY_LEAD.search(sent) and not COURT_REJECTS_RELIANCE.search(sent)
    if sub_sent or sub_lead or sub_party:
        return dict(relation="CITES", voice="PARTY_SUBMISSION",
                    reasons="submission or party's case in the sentence" if sub_sent else "submission lead earlier in the paragraph",
                    cue="", s0=s0, s1=window_end)
    # find cues in the passage, strongest type first
    found = []
    for typ in TYPES:
        for rx in LEXC[typ]:
            for m in rx.finditer(passage):
                found.append((TYPES.index(typ), m.start(), typ, m))
    if not found:
        return dict(relation="CITES", voice="NO_TREATMENT_CUE", reasons="no treatment wording bound in the passage", cue="",
                    s0=s0, s1=window_end)
    found.sort(key=lambda x: (x[0], abs((s0 + x[1]) - anchor_s)))
    for _, off, typ, m in found:
        cpos, cend = s0 + m.start(), s0 + m.end()
        local = t[max(s0, cpos - 120):cpos]
        if t[s0:s1].rstrip().endswith("?") or re.match(r"[^.;!?]*\?", t[cend:s1]):
            reasons.append("interrogative sentence (V13-01)")
            continue
        if NO_ONE_SAID.search(t[s0:cend]):
            reasons.append("negated report ('no one has said that') (V13-01)")
            continue
        if typ == "OVERRULES" and PLEA_SUBJECT.search(t[max(s0, cpos - 80):cpos]):
            reasons.append("subject of 'overruled' is a plea, objection or argument (V13-01)")
            continue
        if typ == "DOUBTS" and R11.negation_in_scope(t, s0, cpos, cend, m.group(0)):
            reasons.append("negation governs the doubts cue")
            continue
        if typ in STRONG and not court.startswith("Supreme") and re.search(r"\[\s*\(\d{4}\)\s*\d+\s*SCC\s*\d+\s*:", passage):
            reasons.append("SCC editorial bracket citation in a High Court passage: quoted Supreme Court text")
            continue
        if typ in ("OVERRULES", "DOUBTS"):
            negated = re.search(r"\b(?:not|never)\s+(?:been\s+|be\s+)?(?:over-?\s?ruled|doubted)", t[max(s0, cpos - 40):cend], I)
        elif typ in ("DISTINGUISHES", "DISAPPROVES"):
            negated = False
        else:
            negated = R11.negation_in_scope(t, s0, cpos, cend, m.group(0))
        if negated:
            reasons.append("negation governs the %s cue" % typ)
            continue
        after = t[cend:cend + 120]
        if typ in ("OVERRULES", "DISAPPROVES", "DOUBTS", "DISTINGUISHES", "FOLLOWS", "EXPLAINS") and (
                REPORTED_AFTER.match(t[cend:cend + 120]) or re.search(r"\bhaving\s+been\s*$", t[max(s0, cpos - 30):cpos], I)):
            reasons.append("treatment of the authority by another decision is reported (agent follows the cue)")
            continue
        if PAST_PASSIVE.search(t[max(s0, cpos - 25):cend]) and typ not in ("CONSIDERS",):
            reasons.append("past passive ('was distinguished/followed'): reported treatment, usually in a list of earlier decisions (F03)")
            continue
        w0 = max(s0, cpos - 200)
        fns = [f for f in FN_GLUED.finditer(t[w0:min(s1, cend + 160)]) if not NOT_A_MARKER.search(t[max(0, w0 + f.start() - 12):w0 + f.start()])]
        fn = min(fns, key=lambda f: abs((w0 + f.start()) - cpos)) if fns else None
        fn_bound = False
        if fn and not marker_bound:
            mk = fn.group(1)
            after_marker = max(cend, w0 + fn.end())
            fm = re.search(r"(?<![\d/.:,])%s\s+(?=\S)" % mk, t[after_marker:after_marker + 4000])
            f_lo = after_marker + fm.start() if fm else None
            if f_lo is None or not (f_lo <= anchor_s < f_lo + 250):
                reasons.append("cue bound to footnote %s; this anchor is not footnote %s's citation (F03)" % (mk, mk))
                continue
            fn_bound = True   # the body marker binds the cue to this footnote citation
        elif not marker_bound and re.search(r"(?:^|\s)\d{1,3}\s*$", t[max(0, anchor_s - 8):anchor_s]) and anchor_s > s0 + 20 \
                and FOOTNOTE_ZONE.search(t[s0:s1]):
            reasons.append("the anchor is a footnote entry and no body marker binds the cue to it (F03)")
            continue
        rep = R11.LOWER_FORUM.search(local) or R11.HIGH_COURT_ACT.search(local)
        if rep and not court.startswith("Supreme") and "High Court" not in rep.group(0):
            reasons.append("report of the lower forum's treatment")
            continue
        if rep and court.startswith("Supreme"):
            reasons.append("report of the High Court or Tribunal's treatment")
            continue
        if not court.startswith("Supreme") and re.match(r"this\s+Court", m.group(0), I) and SC_REPORT.search(t[s0:s1]):
            reasons.append("'this Court' with a Supreme Court report in a High Court judgment: the Supreme Court's words, quoted (F02)")
            continue
        n_auth = max(count_authorities(t, s0, s1), len(NAMED_CASES.findall(t[s0:s1])))
        if cpos <= anchor_s and anchor_e <= cend:   # the cue span contains the anchor ("Reliance placed on X is misplaced")
            between, n_between = "", 0
        elif anchor_s >= cend:
            between, n_between = t[cend:anchor_s], count_authorities(t, cend, anchor_s)
        else:
            between, n_between = t[anchor_e:cpos], count_authorities(t, anchor_e, cpos)
        if fn_bound:
            between, n_between = "", 0
        if n_between > 0:
            reasons.append("another authority lies between the anchor and the cue")
            continue
        if len(between) > 260 and not (window_end > s1 and cpos >= s1):
            reasons.append("cue too far from the anchor (%d chars)" % len(between))
            continue
        if typ in STRONG and (re.search(r"\b(?:referring\s+Bench|the\s+Bench|a\s+Bench|Division\s+Bench|learned\s+(?:Single\s+)?Judges?|"
                                        r"the\s+High\s+Court|the\s+Tribunal|the\s+Full\s+Bench)\b[^.;]{0,50}$", local, I)
                              or re.search(r"\bwhether\b[^.;]{0,120}$", local, I)):
            reasons.append("the %s wording is another bench's view or an open question ('whether')" % typ.lower())
            continue
        if typ == "DISTINGUISHES" and not re.search(r"distinguish", m.group(0), I) and not COURT_REJECTS_RELIANCE.search(m.group(0)) \
                and ((anchor_s < cpos and STATUTORY_SUBJECT.search(t[anchor_e:cpos])) or STATUTORY_SUBJECT.search(t[max(s0, cpos - 60):cpos])):
            reasons.append("a statute, rule or instrument stands between the authority and '%s': it is the subject (F03)" % m.group(0))
            continue
        if typ == "DISTINGUISHES" and not re.search(r"distinguish", m.group(0), I) and not COURT_REJECTS_RELIANCE.search(m.group(0)) \
                and anchor_s > cpos:
            reasons.append("'%s' precedes the authority: the authority is not its subject (statute or rule held inapplicable)" % m.group(0))
            continue
        if typ == "DISTINGUISHES" and cpos > anchor_e and re.search(r"\b(?:that|whether|where)\b", t[anchor_e:cpos], I):
            reasons.append("the cue governs a proposition reported from the authority, not the authority itself")
            continue
        if typ in STRONG and opinion in SEPARATE:
            return dict(relation="CITES", voice="SEPARATE_OR_DISSENT_OPINION", cue=m.group(0), s0=s0, s1=window_end,
                        reasons="%s wording in a %s opinion: no proposal" % (typ.lower(), opinion.lower()))
        if n_auth > 1 and typ not in STRONG and typ != "DISTINGUISHES" and not fn_bound:
            if typ in ("FOLLOWS", "APPLIES"):
                reasons.append("several authorities in the sentence; FOLLOWS/APPLIES not bound to one")
                continue
        if typ == "OVERRULES":
            if opinion in SEPARATE:
                return dict(relation="CITES", voice="SEPARATE_OR_DISSENT_OPINION", cue=m.group(0), s0=s0, s1=window_end,
                            reasons="overruling words in a %s opinion: no proposal" % opinion.lower())
            if not court.startswith("Supreme"):
                return dict(relation="CITES", voice="HIGH_COURT_OVERRULING_WORDS_NOT_ROUTED", cue=m.group(0), s0=s0, s1=window_end,
                            reasons="overruling words in a High Court/Tribunal judgment: competence and bench strength not established; "
                                    "not routed (C11 probe and v13 review found no High Court own-voice overruling)")
        res = dict(relation=typ, voice="COURT_OWN_VOICE", cue=m.group(0), s0=s0, s1=window_end, reasons="; ".join(reasons[-2:]))
        if typ == "DISAPPROVES" and re.search(r"lay\s+down|good\s+law|wrongly", m.group(0), I):
            res["overruling_language"] = "DECLARATORY_ONLY_NOT_EXPLICIT_OVERRULING"
        if typ == "OVERRULES":
            res["overruling_language"] = "EXPLICIT"
        return res
    return dict(relation="CITES", voice="CUES_REJECTED", reasons="; ".join(sorted(set(reasons)))[:300], cue="", s0=s0, s1=window_end)


def locate(t, excerpt):
    """Offset in t where the C11 excerpt starts (excerpts are whitespace-collapsed and may be clipped with an ellipsis)."""
    ex = (excerpt or "").rstrip("\u2026").strip()
    if len(ex) < 30:
        return -1
    for a, b in ((0, len(ex)), (0, 160), (20, 140), (max(0, len(ex) - 120), len(ex))):
        k = ex[a:b]
        if len(k) < 30:
            continue
        i = t.find(k)
        if i >= 0:
            return max(0, i - a)
    return -1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=C.DEFAULT_REPO)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--dev-only", action="store_true", help="classify only the labelled passages, print the in-sample score, write nothing")
    a = ap.parse_args()
    restricted = C.Restricted()
    graph = C.read_csv(REL / "CASE_CITATION_GRAPH.csv")
    tcs = C.read_csv(REL / "TREATMENT_CANDIDATES.csv")
    if a.dev_only:
        lab_ids = {l["row_id"] for l in dev_labels()}
        tcs = [r for r in tcs if r["candidate_id"] in lab_ids]
        lab_edges = {r["edge_id"] for r in tcs}
        graph = [r for r in graph if r["edge_id"] in lab_edges]
    docs = sorted({r["source_doc_id"] for r in graph} | {r["source_doc_id"] for r in tcs})
    assert not any(restricted.hit(doc_id=d) for d in docs)
    blobs = C.cat_blobs(a.repo, ["%s:data/text/%s.txt" % (C.TEXT_COMMIT, d) for d in docs])
    orig = {d: blobs["%s:data/text/%s.txt" % (C.TEXT_COMMIT, d)].decode("utf-8", "replace")
            for d in docs if blobs["%s:data/text/%s.txt" % (C.TEXT_COMMIT, d)] is not None}
    text = {d: collapse(v) for d, v in orig.items()}
    omaps = {}
    edges = {r["edge_id"]: r for r in graph}
    opinion_by_edge = {}
    for r in tcs:
        if r["opinion"]:
            opinion_by_edge.setdefault(r["edge_id"], r["opinion"].split(" ")[0])

    passages, unlocated = [], Counter()
    # (1) one anchored passage per citation edge (C11 anchor excerpt)
    for r in graph:
        t = text.get(r["source_doc_id"])
        if t is None:
            unlocated["no_text"] += 1
            continue
        i = locate(t, r["excerpt"])
        if i < 0:
            unlocated["edge_excerpt_not_found"] += 1
            continue
        j, cs = -1, ""
        for cand in re.split(r"\s*\|\|?\s*", r["cited_strings"] or ""):   # C11 joins parallel strings with ' || '
            if cand and t.find(cand, i, i + 400) >= 0:
                cs, j = cand, t.find(cand, i, i + 400)
                break
        s, e = (j, j + len(cs)) if j >= 0 else (i + len(r["excerpt"]) // 2, i + len(r["excerpt"]) // 2 + 1)
        passages.append(dict(pid="PE-" + r["edge_id"][2:], origin="C11_EDGE_ANCHOR", edge_id=r["edge_id"], candidate_id="",
                             doc_id=r["source_doc_id"], s=s, e=e, zone=r["zone"], court=r["source_court"],
                             opinion=opinion_by_edge.get(r["edge_id"], "OPINION_NOT_IDENTIFIED"), target_court=r["target_court"]))
    # (2) every C11 treatment-candidate passage (cue rows, adviser leads)
    for r in tcs:
        t = text.get(r["source_doc_id"])
        if t is None:
            unlocated["no_text"] += 1
            continue
        i = locate(t, r["excerpt"])
        if i < 0:
            unlocated["tc_excerpt_not_found"] += 1
            continue
        cs = r["cited_string"]
        j = t.find(cs, max(0, i - 200), i + 600) if cs else -1
        k = t.find(r["cue_text"], i, i + 600) if r["cue_text"] else -1
        if r["anchor"] in ("FOOTNOTE_MARKER", "NAME_REFERENCE") and k >= 0:
            j, cs = k, "x"   # C11 bound the cue to a body marker or name reference; the printed citation sits elsewhere
        elif j < 0:
            j = k if k >= 0 else i + 10
            cs = cs or r["cue_text"] or "x"
        passages.append(dict(pid="PT-" + r["candidate_id"][3:], origin="C11_TREATMENT_CANDIDATE", edge_id=r["edge_id"],
                             candidate_id=r["candidate_id"], doc_id=r["source_doc_id"], s=j, e=j + max(1, len(cs)),
                             zone="REPORTER_EDITORIAL" if r["attribution"] == "REPORTER_EDITORIAL" else "BODY",
                             court=r["source_court"], opinion=(r["opinion"] or "OPINION_NOT_IDENTIFIED").split(" ")[0],
                             target_court=(edges.get(r["edge_id"]) or {}).get("target_court", ""),
                             lead_target_raw=r["lead_target_raw"], c11_attribution=r["attribution"],
                             marker_bound=(r["anchor"] in ("FOOTNOTE_MARKER", "NAME_REFERENCE") and k >= 0) or bool(r["lead_target_raw"])))

    hkeys, hprov = holdout_pages()
    out, seen, docobj = [], {}, {}
    for p in passages:
        t = text[p["doc_id"]]
        res = classify(t, p["court"], p["s"], p["e"], p["opinion"], p["zone"], p["target_court"], p.get("marker_bound", False))
        key = (p["doc_id"], res["s0"], p["edge_id"])
        e = edges.get(p["edge_id"]) or {}
        raw_target = clean_raw_target(p.get("lead_target_raw") or "")
        if res["relation"] in ("DISAPPROVES", "OVERRULES") and res.get("cue"):
            cpos = t.find(res["cue"], res["s0"], res["s1"])
            sub = re.search(r"\b(?:the\s+)?subsequent\s+decisions\b[^.;]{0,120}", t[res["s0"]:cpos]) if cpos > 0 else None
            if sub:   # the passage treats later decisions that followed the anchored authority, not the authority itself (F08)
                raw_target = "%s (decisions following the authority cited at this anchor; not the authority itself)" % sub.group(0).strip()
        ctx = ""
        if raw_target and DEMONSTRATIVE.search(raw_target):  # V13-04: carry the preceding sentences
            b0, _ = sentence(t, max(0, res["s0"] - 2), max(1, res["s0"] - 1))
            b00, _ = sentence(t, max(0, b0 - 2), max(1, b0 - 1))
            ctx = t[b00:res["s0"]][-700:]
        pg = docobj.setdefault(p["doc_id"], R11.Doc(p["doc_id"], t, p["court"])).page_at(res["s0"])
        in_ho = bool(hkeys) and (("doc", p["doc_id"], str(pg)) in hkeys)
        row = dict(passage_id=p["pid"], origin=p["origin"], edge_id=p["edge_id"], candidate_id=p["candidate_id"],
                   source_doc_id=p["doc_id"], source_court=p["court"], source_date=e.get("source_date", ""),
                   target_state=e.get("target_state", ""), target_doc_ids=e.get("target_doc_ids", ""),
                   target_raw=raw_target, target_raw_context=ctx, page=pg, in_a0_holdout_page="YES" if in_ho else "NO",
                   opinion=p["opinion"], relation=res["relation"], voice=res["voice"], cue=res.get("cue", ""),
                   overruling_language=res.get("overruling_language", ""), reasons=res["reasons"],
                   passage=t[res["s0"]:res["s1"]][:900], passage_sha256=C.sha256_bytes(t[res["s0"]:res["s1"]].encode()),
                   c11_attribution=p.get("c11_attribution", ""), status="AUTOMATED_CANDIDATE_NOT_VERIFIED", extractor=VERSION)
        row["merged_candidate_ids"] = p["candidate_id"]
        exported = row["passage"][:600]
        row["passage_export_sha256"] = C.sha256_bytes(exported.encode())
        row["passage_truncated"] = "YES" if len(t[res["s0"]:res["s1"]]) > 600 else "NO"
        row["char_page"], row["char_start"], row["char_end"] = "", "", ""
        if res["relation"] != "CITES":
            om = omaps.setdefault(p["doc_id"], OffsetMap(orig[p["doc_id"]]))
            pgx, cs, ce = om.page_relative(res["s0"], res["s1"])
            row["char_page"], row["char_start"], row["char_end"] = pgx or "", cs, ce
        prev = seen.get(key)
        if prev is not None:  # V13-04 second half: several cues in one sentence -> one passage; keep the typed one
            kept = out[prev]
            ids = sorted({x for x in (kept["merged_candidate_ids"] + ";" + p["candidate_id"]).split(";") if x})
            if kept["relation"] == "CITES" and row["relation"] != "CITES":
                out[prev] = row
            out[prev]["merged_candidate_ids"] = ";".join(ids)
            continue
        seen[key] = len(out)
        out.append(row)
    out.sort(key=lambda r: (r["source_doc_id"], r["passage_id"]))
    counts = Counter(r["relation"] for r in out)
    voices = Counter(r["voice"] for r in out)

    # ---------------------------------------------------------------- in-sample development evaluation
    labels = dev_labels()
    tc_ids = {r["candidate_id"] for r in C.read_csv(REL / "TREATMENT_CANDIDATES.csv")}
    by_cid = {}
    for r in out:
        for cid in r["merged_candidate_ids"].split(";"):
            if cid:
                by_cid[cid] = r
    ev_rows, tally = [], Counter()
    for lab in labels:
        pr = by_cid.get(lab["row_id"])
        if lab["row_id"] not in tc_ids:
            ev_rows.append(dict(row_id=lab["row_id"], source=lab["source"], c11_category=lab["category"], reviewer_verdict=lab["verdict"],
                                truth_family=lab["truth_family"], predicted="", predicted_family="", outcome="EXCLUDED_ROW_NOT_IN_C11_REV13",
                                voice="", reasons="candidate withdrawn before C11 rev. 1.3; no passage in the current input"))
            tally["EXCLUDED"] += 1
            continue
        if pr and pr.get("in_a0_holdout_page") == "YES":
            ev_rows.append(dict(row_id=lab["row_id"], source=lab["source"], c11_category=lab["category"], reviewer_verdict=lab["verdict"],
                                truth_family=lab["truth_family"], predicted="", predicted_family="", outcome="EXCLUDED_IN_A0_HOLDOUT_PAGE",
                                voice="", reasons="page belongs to H-REL-C13; kept out of development"))
            tally["EXCLUDED_HOLDOUT"] += 1
            continue
        pred = pr["relation"] if pr else "NOT_LOCATED"
        fam_pred = family(pred)
        fam_truth = lab["truth_family"]
        if pred in ("CITES", "CONSIDERS", "NOT_LOCATED"):
            outcome = "NO_TYPED_TREATMENT_" + ("CORRECT_REJECTION" if fam_truth == "NONE" else "MISSED")
        else:
            outcome = "TP" if fam_pred == fam_truth else "FP"
        tally[outcome] += 1
        ev_rows.append(dict(row_id=lab["row_id"], source=lab["source"], c11_category=lab["category"], reviewer_verdict=lab["verdict"],
                            truth_family=fam_truth, predicted=pred, predicted_family=fam_pred, outcome=outcome,
                            voice=pr["voice"] if pr else "", reasons=(pr["reasons"] if pr else "")[:200]))
    tp, fp = tally["TP"], tally["FP"]
    missed = tally["NO_TYPED_TREATMENT_MISSED"]
    ev = dict(tp=tp, fp=fp, precision=round(tp / (tp + fp), 4) if tp + fp else None,
              missed_supported=missed, recall_on_supported=round(tp / (tp + missed + sum(1 for r in ev_rows if r["outcome"] == "FP" and r["truth_family"] != "NONE")), 4) if tp + missed else None,
              correct_rejections=tally["NO_TYPED_TREATMENT_CORRECT_REJECTION"], labelled_rows=len(labels),
              excluded_rows_not_in_rev13=tally["EXCLUDED"], excluded_rows_in_a0_holdout=tally["EXCLUDED_HOLDOUT"],
              note="IN-SAMPLE: the rules were developed on these C11 reviewed rows; this is not an independent measure. "
                   "Independent precision/recall awaits A0's H-REL-C13 evaluation (only its identifiers are read, to exclude it).")
    summary = dict(tool=VERSION, frozen=False, passages=len(out), unlocated=dict(unlocated), relation_counts=dict(sorted(counts.items())),
                   voice_counts=dict(sorted(voices.items())), dev_eval_in_sample=ev,
                   inputs={str((REL / f).relative_to(C.WT)): C.sha256_file(REL / f) for f in ("CASE_CITATION_GRAPH.csv", "TREATMENT_CANDIDATES.csv")},
                   text_commit=C.TEXT_COMMIT, restricted_register=restricted.provenance,
                   a0_holdout=hprov, a0_passages_read=False,
                   passages_on_a0_holdout_pages=sum(1 for r in out if r["in_a0_holdout_page"] == "YES"))
    files = {"TREATMENT_PASSAGES_C13.csv.gz": C.to_csv(out), "DEV_EVAL_ROWS_C13.csv": C.to_csv(ev_rows),
             "DEV_LABELS_C13.csv": C.to_csv(labels), "TREATMENT_SUMMARY_C13.json": C.dumps(summary)}
    if a.dev_only:
        print(json.dumps(ev, indent=1))
        for r in ev_rows:
            if r["outcome"] in ("FP", "NO_TYPED_TREATMENT_MISSED"):
                pr = by_cid.get(r["row_id"]) or {}
                print(r["outcome"], r["row_id"], r["truth_family"], r["predicted"], pr.get("voice"), "|", (pr.get("reasons") or "")[:150],
                      "|", (pr.get("passage") or "")[:300])
        return 0
    rc = C.write_or_check(files, OUT, a.check)
    if not a.check:
        print(json.dumps(dict(relation_counts=summary["relation_counts"], dev=ev, unlocated=dict(unlocated)), indent=1))
    return rc


def family(rel):
    return {"FOLLOWS": "FOLLOWS_APPLIES", "APPLIES": "FOLLOWS_APPLIES", "DISTINGUISHES": "DISTINGUISHES",
            "OVERRULES": "OVERRULES_OR_DECLARATORY", "DISAPPROVES": "OVERRULES_OR_DECLARATORY", "DOUBTS": "DOUBTS",
            "EXPLAINS": "EXPLAINS"}.get(rel, "NONE")


# v13 review (fable_review_relations_c11_v13.md, section 2): 30 adviser rows; four are not overrulings (V13-01).
V13_NOISE = {"TC-9b500dbe0d15", "TC-e8e740a5df2f", "TC-8eee72cd601c", "TC-741f5ae7f6ab"}


def dev_labels():
    """Truth families from the three C11 review rounds. Only treatment rows with a reviewer verdict are used."""
    rv = C11DIR / "review"
    labs = []
    fam_of_cat = {"SAMPLE_APPLIES_FOLLOWS": "FOLLOWS_APPLIES", "APPLIES_FOLLOWS": "FOLLOWS_APPLIES",
                  "SAMPLE_DISTINGUISHES": "DISTINGUISHES", "DISTINGUISHES": "DISTINGUISHES",
                  "ADVISER_PROPOSED_OVERRULES_QUESTIONS": "OVERRULES_OR_DECLARATORY", "ADVISER_OVERRULES": "OVERRULES_OR_DECLARATORY",
                  "ADVISER_REPORTED_TREATMENT": "NONE", "REPORTED_TREATMENT_DOC_CHECK": "NONE"}
    for f, src in (("fable_review_relations_c11_rows.csv", "C11_REVIEW_R1"), ("fable_review_relations_c11_v11_rows.csv", "C11_REVIEW_R2")):
        for r in C.read_csv(rv / f):
            if r["check"] != "2_TREATMENT" or not r["row_id"].startswith("TC-"):
                continue
            cat, v = r["category"], r["verdict"]
            if cat == "RECALL_PROBE_OVERRULES":
                continue
            fam = fam_of_cat.get(cat, "NONE")
            if fam != "NONE" and v != "SUPPORTED":
                fam = "NONE"     # NOT_COURTS_OWN_WORDS, WRONG_TARGET, WEAKER_RELATION -> no typed treatment of this target
            labs = [l for l in labs if l["row_id"] != r["row_id"]]   # one label per row: the later review round wins
            labs.append(dict(row_id=r["row_id"], source=src, category=cat, verdict=v, truth_family=fam,
                             basis="reviewer verdict on the stated target; reported treatment carries no own-voice proposal"))
    tcs = {r["candidate_id"]: r for r in C.read_csv(REL / "TREATMENT_CANDIDATES.csv")}
    for cid, r in tcs.items():
        if r["status"] != "LEGAL_INTERPRETATION_ADVISER_REVIEW":
            continue
        if any(l["row_id"] == cid for l in labs):
            continue
        sep = r["attribution"] in ("SEPARATE_OPINION_LEAD", "DISSENT_OPINION_LEAD")
        fam = "NONE" if (cid in V13_NOISE or sep) else "OVERRULES_OR_DECLARATORY"
        labs.append(dict(row_id=cid, source="C11_REVIEW_R3_V13", category="ADVISER_" + r["attribution"],
                         verdict="NOT_AN_OVERRULING" if cid in V13_NOISE else ("SEPARATE_OR_DISSENT_NO_PROPOSAL" if sep else "REAL_OWN_VOICE_OVERRULING"),
                         truth_family=fam, basis="v13 review section 2 (26 of 30 real; separate/dissent rows carry no proposal)"))
    labs.sort(key=lambda x: (x["source"], x["row_id"]))
    return labs


if __name__ == "__main__":
    sys.exit(main())
