"""Mimamsa C13 judicial outcome extractor V4: V4 pipeline: segment analysis and main entry.

All values are AUTOMATED CANDIDATES read from a PDF text layer; nothing is legally verified."""
import bisect
import re

import v4_relief

from v4_text import VERSION, STATUS, UNVERIFIED, OUTCOME_VOCAB, PRINTED_VOCAB, SUBST_VOCAB  # noqa: F401
from v4_decide import DEFAULT_SUBST  # noqa: F401
from v4_text import (  # noqa: F401
    mask_page_markers,
    page_at,
    squash,
    sentences,
    Doc,
    _alpha_ratio,
    VERSION,
    STATUS,
    UNVERIFIED)
from v4_quotes import (  # noqa: F401
    quote_spans,
    in_spans)
from v4_proceedings import (  # noqa: F401
    _PARA_CAND_RE,
    host_paragraphs,
    para_at,
    ptype,
    find_case_numbers,
    meta_case_numbers,
    norm_label,
    _host_numbers,
    _match_host,
    _PAREN_LONG_RE,
    _PARTY_RE,
    _heading_scope,
    block_headings,
    find_sections)
from v4_clauses import (  # noqa: F401
    _ADOPT_RE,
    classify_subject,
    parse_dispositions,
    _WITHDRAW_CTX_RE,
    _REF_BEFORE_NUM_RE)
from v4_segment import opinion_role  # noqa: F401
from v4_segment import (  # noqa: F401
    _NOT_FINAL_RE,
    _OPERATIVE_CUE_RE,
    _ORDER_HEADING_RE,
    _JUDGMENT_START_RE,
    is_doc_header,
    _SCR_RE,
    _EDITORIAL_TAIL_RE,
    _segment_doc)
from v4_decide import (  # noqa: F401
    _reduce,
    two_fields,
    _zone_party_note,
    resolve_proceedings,
    _choose)


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


def _final_sentences_zone(d, js, body_end, span=1600):
    """Start of the closing passage (about the last `span` non-blank characters, from a line start) when it holds a
    court-voice main disposition; else None."""
    mt = d.mt
    k, n = body_end, 0
    while k > js and n < span:
        k -= 1
        if not mt[k].isspace():
            n += 1
    ls = mt.rfind("\n", js, k) + 1
    a = max(js, ls)
    return a if _has_main_disposition(mt, a, body_end, d.qspans, d.qstarts) else None


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
    elif _final_sentences_zone(d, js, body_end) is not None:
        # V4: no cue and no numbered final paragraph (old S.C.R. renditions, short unnumbered orders): the closing
        # sentences are the operative part when they hold a present-tense, court-voice disposition of a main proceeding
        zs, method_zone = _final_sentences_zone(d, js, body_end), "final_sentences_no_cue"
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
        elif v4_relief.transfer_direction(d, (zs, body_end)) is not None:
            tm = v4_relief.transfer_direction(d, (zs, body_end))
            a_ = max(zs, mt.rfind(".", zs, tm.start()) + 1)
            b_ = mt.find(".", tm.end())
            b_ = body_end if b_ < 0 or b_ > body_end else b_ + 1
            res["status"] = "final"
            res["rows"] = [("ALL", "", "transferred", {"sentence": (a_, b_), "pos": tm.start(), "subject": ""},
                            "transfer_direction_only")]
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
                x["cls"], x["extent"] = "allowed", True   # V4: resolved later from the operative directions
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




# ------------------------------------------------------------------ v3: main entry
ROW_COLS = ["judgment_id", "sha256", "doc_ids", "court", "proceeding", "file_case_role", "printed_disposal",
            "substantive_result", "party_specific", "final_or_interim", "page", "paragraph", "char_start", "char_end",
            "excerpt", "abstain_reason", "notes", "method", "flags"]



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
    # V4: opinion roles. A dissenting separate opinion never supplies the disposition when another opinion or order
    # disposes of the case; if only dissenting opinions carry a disposition, abstain.
    for i, r_ in enumerate(results):
        r_["role"] = opinion_role(mt[r_["seg"][0]:r_["seg"][1]], i == 0)
    if any(r_["role"] == "dissent" for r_ in results) and len(results) > 1:
        keep = [r_ for r_ in results if r_["role"] != "dissent"]
        if any(r_["status"] == "final" for r_ in keep):
            flags.append("DISSENTING_OPINION_EXCLUDED")
            results = keep
        elif any(r_["status"] == "final" for r_ in results):
            labels = [h["label_norm"] for h in main_hosts] or ["UNIDENTIFIED"]
            rows = [row(l, UNVERIFIED, UNVERIFIED, "ONLY_A_DISSENTING_OPINION_STATES_A_DISPOSITION", flags) for l in labels]
            return _finish(rows, own, meta), {"flags": flags, "hosts": labels}
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
