"""C13-A3 passage classification and proposition items.

Every sentence of the judgment body gets exactly one passage class:
  material_fact | question_of_law | holding | supporting_reasoning | obiter | party_submission |
  quoted_judgment | statutory_quotation | lower_forum_material | operative_direction
Deterministic structure decides the non-court classes (quotations by kind, precedent reports, submissions,
lower-forum reports). Among court-voice sentences, two learned heads (holding, question_of_law) decide, with
deterministic rules for operative directions, obiter cues and material facts.

Opinion attribution: a holding-class sentence becomes item_type `holding` only in an opinion whose role is
sole / lead_majority / lead / concurring / separate / court_order. In a dissent it becomes
`dissent_holding_candidate`; in a split verdict `split_opinion_holding_candidate` (never the Court's holding).

Every item: status AUTOMATED_CANDIDATE_NOT_VERIFIED, anchor (page, page_end, char offsets into the text layer,
paragraph only when the opinion has numbered paragraphs) and opinion id / author / role / court_status.
"""
import hashlib
import re

import c13_features as cf
import c13_segment as sg

c12 = sg.c12
VERSION = "c13-holdings/0.9.0-candidate"
STATUS = "AUTOMATED_CANDIDATE_NOT_VERIFIED"
VERIFICATION = "NOT_VERIFIED_RATIO_NOT_DETERMINED"
EXCERPT_CAP = 900

PASSAGE_CLASSES = ["material_fact", "question_of_law", "holding", "supporting_reasoning", "obiter", "party_submission",
                   "quoted_judgment", "statutory_quotation", "lower_forum_material", "operative_direction"]
ITEM_CLASSES = ("question_of_law", "holding", "obiter", "operative_direction")
HOLDING_ROLES = ("sole", "lead_majority", "lead", "concurring", "separate", "court_order")


def item_id(jid, s, e, t):
    return "HC13-" + hashlib.sha256(("%s|%d|%d|%s" % (jid, s, e, t)).encode()).hexdigest()[:14]


def classify(seg, model):
    """Assign passage classes. Returns list of dicts parallel to seg['recs']."""
    recs = seg["recs"]
    ops = seg["opinions"]
    th = model.d["thresholds"]

    def role_of(oi):
        return ops[oi]["role"]

    out = []
    for i, r in enumerate(recs):
        v = r["voice"]
        res = {"p_holding": None, "p_issue": None, "basis": r["voice_basis"]}
        if v.startswith("quotation:"):
            kind = v.split(":", 1)[1]
            res["cls"] = {"precedent": "quoted_judgment", "statute_or_document": "statutory_quotation", "lower_forum": "lower_forum_material",
                          "submission": "party_submission"}.get(kind, "statutory_quotation" if kind == "other" else "quoted_judgment")
            if kind == "other":
                res["cls"] = "quoted_judgment" if sg._CASE_REF_RE.search(r.get("quote_source") or "") else "statutory_quotation"
        elif v == "precedent_report":
            res["cls"] = "quoted_judgment"
        elif v == "submission":
            res["cls"] = "party_submission"
        elif v == "lower_forum":
            res["cls"] = "lower_forum_material"
        else:
            feats = cf.features(seg, i, role_of)
            ph = model.prob("holding", feats)
            pi = model.prob("issue", feats)
            res["p_holding"], res["p_issue"] = round(ph, 4), round(pi, 4)
            sig = r["_sig"]
            late = r.get("pos_in_op", 0) > 0.6 or r["section"] == "CONCLUSION"
            if pi >= th["issue"] and pi >= ph:
                res["cls"] = "question_of_law"
            elif ("DISPOSAL" in sig or ("OPERATIVE" in sig and "COURT_CONCLUSION_MARKER" not in sig)) and late and ph < th["holding_over_operative"]:
                res["cls"] = "operative_direction"
            elif ph >= th["holding"]:
                res["cls"] = "holding"
            elif "OBITER" in sig:
                res["cls"] = "obiter"
            elif ("FACTY" in sig or "NARRATIVE_FACT" in sig or ("DATE" in sig and "NORMATIVE_LEGAL_PREDICATE" not in sig)
                  or (not r.get("in_analysis_zone") and not (sig & {"COURT_CONCLUSION_MARKER", "NORMATIVE_LEGAL_PREDICATE", "STATEMENT_OF_LAW",
                                                                     "ACCEPTS_OR_REJECTS_CONTENTION"}))):
                res["cls"] = "material_fact"
            else:
                res["cls"] = "supporting_reasoning"
        out.append(res)
    # per-opinion floor: an opinion in a court role with enough text but no holding gets its best candidate
    best = {}
    for i, (r, res) in enumerate(zip(recs, out)):
        if res["p_holding"] is None:
            continue
        if role_of(r["oi"]) not in HOLDING_ROLES + ("dissent", "split_opinion"):
            continue
        if res["cls"] in ("question_of_law", "operative_direction"):
            continue
        b = best.get(r["oi"])
        if b is None or res["p_holding"] > out[b]["p_holding"]:
            best[r["oi"]] = i
    for oi, i in best.items():
        has = any(res["cls"] == "holding" for r, res in zip(recs, out) if r["oi"] == oi)
        ncourt = recs[i].get("n_court_in_op", 0)
        if not has and ncourt >= th["floor_min_court_sentences"] and out[i]["p_holding"] >= th["holding_floor"]:
            out[i]["cls"] = "holding"
            out[i]["basis"] += "+OPINION_FLOOR"
    return out


def analyze(text, meta, model, all_passages=False):
    jid = meta.get("judgment_id", "")
    seg = sg.segment(text, meta)
    cls = classify(seg, model)
    recs, ops, pidx, mt = seg["recs"], seg["opinions"], seg["pidx"], seg["mt"]
    para_ok = {}
    for oi in range(len(ops)):
        para_ok[oi] = sum(1 for p in seg["paras"] if p[2] == oi) >= 5
    items, passages = [], []
    qlist = []
    for i, (r, c) in enumerate(zip(recs, cls)):
        op = ops[r["oi"]]
        page, page_end = c12.page_at(pidx, r["s"]), c12.page_at(pidx, r["e"])
        passages.append((r["s"], r["e"], page, op["opinion_id"], c["cls"], c["p_holding"], c["p_issue"]))
        if c["cls"] not in ITEM_CLASSES and not all_passages:
            continue
        itype = c["cls"]
        if itype == "holding" and op["role"] == "dissent":
            itype = "dissent_holding_candidate"
        elif itype == "holding" and op["role"] == "split_opinion":
            itype = "split_opinion_holding_candidate"
        rec = {
            "item_id": item_id(jid, r["s"], r["e"], itype),
            "judgment_id": jid,
            "sha256": meta.get("sha256", ""),
            "doc_id": meta.get("text_doc", ""),
            "court": meta.get("court", ""),
            "item_type": itype,
            "passage_class": c["cls"],
            "voice": r["voice"],
            "voice_basis": c["basis"],
            "opinion_id": op["opinion_id"],
            "opinion_role": op["role"],
            "opinion_role_basis": op["role_basis"],
            "opinion_author": op["author"] or None,
            "opinion_method": op["method"],
            "court_status": sg.court_status(op["role"]),
            "anchor": {"page": page, "page_end": page_end, "char_start": r["s"], "char_end": r["e"],
                       "paragraph": r["para"] if para_ok.get(r["oi"]) else None,
                       "paragraph_basis": "NUMBERED_PARAGRAPHS" if para_ok.get(r["oi"]) else "NOT_GIVEN_UNNUMBERED_OR_UNRELIABLE"},
            "page": page,
            "page_end": page_end,
            "char_start": r["s"],
            "char_end": r["e"],
            "excerpt": c12.squash(text[r["s"]:r["e"]], EXCERPT_CAP),
            "excerpt_clean": c12.squash(mt[r["s"]:r["e"]], EXCERPT_CAP),
            "section_heading": r["section"] or None,
            "in_analysis_zone": bool(r.get("in_analysis_zone")),
            "quote_source": r.get("quote_source"),
            "p_holding": c["p_holding"],
            "p_issue": c["p_issue"],
            "legal_issue": None,
            "answers_question": None,
            "statutes": c12.statute_refs(r["sent"]),
            "status": STATUS,
            "verification": VERIFICATION,
            "extractor": VERSION,
        }
        if itype == "question_of_law":
            qlist.append((i, rec, c12.content_words(r["sent"])))
            m = re.search(r"\b(whether|what|how|when)\b", r["sent"], re.I)
            rec["legal_issue"] = c12.squash(r["sent"][m.start():] if m else r["sent"], 400)
        items.append(rec)
    for rec in items:
        if rec["passage_class"] != "holding":
            continue
        cw = c12.content_words(rec["excerpt_clean"])
        bestj, bq = 0.0, None
        for qi, q, qw in qlist:
            if q["opinion_id"] != rec["opinion_id"] or q["char_start"] >= rec["char_start"]:
                continue
            j = c12.jaccard(cw, qw)
            if j > bestj:
                bestj, bq = j, q
        if bq is not None and bestj >= 0.15:
            rec["answers_question"] = bq["item_id"]
            rec["legal_issue"] = bq["legal_issue"]
    counts = {}
    for p in passages:
        counts[p[4]] = counts.get(p[4], 0) + 1
    summary = {
        "judgment_id": jid,
        "body_start_page": c12.page_at(pidx, seg["start"]),
        "body_start_method": seg["start_method"],
        "n_opinions": len(ops),
        "opinions": ";".join("%s:%s:%s@p%s-%s" % (o["opinion_id"], o["role"], o["author"] or "?", c12.page_at(pidx, o["start"]),
                                                   c12.page_at(pidx, max(o["start"], o["end"] - 1))) for o in ops),
        "n_numbered_paragraphs": len(seg["paras"]),
        "n_quote_spans": len(seg["quotes"]),
        "n_sentences": len(recs),
        "counts": counts,
    }
    return summary, items, passages, seg
