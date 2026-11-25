"""Mimamsa C13 judicial outcome extractor V4: per-proceeding reduction, printed/substantive fields, segment choice (ported from V3; V4 changes marked V4).

All values are AUTOMATED CANDIDATES read from a PDF text layer; nothing is legally verified."""
import bisect
import re

import v4_relief

from v4_text import (  # noqa: F401
    squash,
    UNVERIFIED)
from v4_quotes import (  # noqa: F401
    in_spans)
from v4_proceedings import (  # noqa: F401
    ptype,
    norm_label,
    _subject_ptypes,
    _host_family)
from v4_clauses import (  # noqa: F401
    _PARTY_STMT_RE,
    _ALONG_WITH_RE,
    _WITHDRAW_CTX_RE)


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



# ------------------------------------------------------------------ v3: printed disposal and substantive result
_DIRECTIONS_RE = re.compile(
    r"\b(?:in\s+(?:the\s+)?(?:above|following|aforesaid|aforementioned|said|these|terms\s+of)|with\s+(?:the\s+)?(?:above|following|aforesaid|"
    r"said)?\s*(?:directions?|observations?|liberty)|with\s+liberty|in\s+terms\s+of|as\s+under|in\s+the\s+light\s+of|with\s+a\s+direction|"
    r"with\s+directions?|subject\s+to)\b", re.I)
_DIRECTIVE_RE = re.compile(r"\b(?:is|are|stand|be)\s+(?:hereby\s+)?directed\b|\bwe\s+(?:hereby\s+|have\s+)?direct(?:ed)?\b|\bby\s+directing\b|"
                           r"\bit\s+is\s+(?:hereby\s+)?directed\b|\b(?:respondents?|petitioners?|appellants?|applicants?|authorit(?:y|ies)|Tribunal|Government|Union|State|Board|Bench|"
                           r"competent\s+\w+|they|he|she|officers?|Department|Registry|Commission|Controller|PCDA|CDA|employer)\b"
                           r"(?:\s+[\w.,()/-]+){0,6}?\s+shall\s+(?!stand\b|also\s+stand\b|not\s+stand\b|be\s+at\s+liberty\b|be\s+open\b)[a-z]+|"
                           r"\blet\s+(?:the|a|his|her|their)\s+[^.;]{0,80}?\bbe\s+(?:decided|considered|re-?considered|examined|passed|paid|"
                           r"released|granted|processed|disposed\s+of)\b|\b(?:is|stands?)\s+modified\b", re.I)
# V4: liberty to seek another remedy is not a direction ('they are at liberty to agitate this aspect')
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
    if ev is not None and ev.get("extent") and cls in ("allowed", "partly_allowed"):
        # V4 (C11 F05): an extent phrase is resolved from the operative directions, not read as partly_allowed
        p_, s_, why = v4_relief.extent_resolution(d, ev, zone)
        if p_ is None:
            return UNVERIFIED, UNVERIFIED, ["printed:" + why, "substantive:" + why]
        printed, subst, cls = p_, s_, p_
        reasons.append(why)
    if cls in ("disposed_of_with_directions", "transferred") and note != "transfer_direction_only":
        tm = v4_relief.transfer_direction(d, zone)
        if tm is not None or cls == "transferred":
            # V4: the court sends the proceeding itself to the Tribunal and then disposes of it here
            return "transferred", "no_adjudication", (["note:TRANSFER_DIRECTION_IN_OPERATIVE_PART"] if cls != "transferred" else [])
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
        elif ev is not None and v4_relief.referenced_remand(d, ev, zone) is not None:
            subst = "remanded_for_fresh_decision"   # V4: 'allowed in the aforesaid terms', the terms being a fresh decision
            reasons.append("note:ALLOWED_IN_TERMS_OF_FRESH_DECISION_DIRECTION")
    elif cls in ("remanded", "set_aside_and_remanded"):
        subst = "remanded_for_fresh_decision"
    elif cls == "partly_allowed" and ev is not None and _REMAND_RE.search(sent):
        subst = "remanded_for_fresh_decision"   # 'allowed in part and ... the matter is remitted to the Tribunal for fresh adjudication'
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



_PLURAL_RE = re.compile(r"\b(?:petition|appeal|case)\s+and\s+the\b|\b(?:petitions|appeals|matters|cases|applications|references|all|both|these|those|they|them|each|every|"
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
        if len(vals) > 1 and len(main_hosts) <= 1 and not generic and not out and \
                vals <= {"allowed", "partly_allowed", "dismissed"} and "dismissed" in vals:
            # V4: one proceeding, relief granted to some parties and refused to others -> partly allowed, with the
            # party-specific outcomes stated ('appeal of the Union allowed; appeal of respondent 2 dismissed')
            ev = party[-1][3]
            pnote = "; ".join("%s for %s" % (r[2], r[0][2:]) for r in party)
            h = main_hosts[0] if main_hosts else None
            return [(h, h["label_norm"] if h else "UNIDENTIFIED", "partly_allowed", ev, "party_specific_mixed_outcome",
                     squash(pnote, 200))], ""
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
        all_generic = bool(re.search(r"^\W*(?:all|both)\s+(?:the\s+|these\s+)?(?:petitions|matters|cases)\b", subj.strip(), re.I)) and not out
        if fams and len(set(_host_family(h) for h in main_hosts)) > 1 and not all_generic:
            # V4: 'All the petitions dismissed' covers every proceeding of the group (transferred cases included)
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
