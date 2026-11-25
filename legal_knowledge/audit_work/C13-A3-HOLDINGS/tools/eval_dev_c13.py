#!/usr/bin/env python3
"""C13-A3 IN-SAMPLE development evaluation against the spent references, compared with c12-holdings/1.0.0.

  python -I -B eval_dev_c13.py --pred-ref D1 --pred-gt D2 --oof ../model/OOF_PREDICTIONS.jsonl.gz --texts ../model/OOF_PREDICTIONS_TEXTS.jsonl.gz --out ../dev_eval/DEV_EVALUATION_C13.md

D1: `holdings_c13.py ids` output on the 30 C12 reference judgments; D2: on the C11 GT judgments.
Every figure is IN-SAMPLE: these references trained the classifier and were read while rules were written.
The out-of-fold (grouped 5-fold by judgment) section is the least optimistic in-sample estimate available here;
it still shares rules, features and thresholds that were chosen on the same data.
Matchers: the C12 pre-registered primary matcher (same judgment, page +-1, >=60% containment of the shorter
excerpt's content tokens, >=3 shared) for the C12 reference; for the C11 GT also the C12-dev rule (page +-1, >=40
common normalised characters).
"""
import argparse
import gzip
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c13_labels as cl  # noqa: E402
import c13_extract as cx  # noqa: E402

ev = cl.ev
C12H = os.path.join(cl.C12, "holdings")
C12_PRED_REF = os.path.join(cl.C12, "holdings_eval", "predictions", "HOLDINGS_C12.jsonl")
C12_PRED_DEV = os.path.join(C12H, "outputs", "dev_predictions", "HOLDINGS_C12.jsonl")
HOLDING_TYPES_C13 = {"holding"}
ALL_HOLDING_C13 = {"holding", "dissent_holding_candidate", "split_opinion_holding_candidate"}


def _open(p):
    return gzip.open(p, "rt", encoding="utf-8") if p.endswith(".gz") else open(p, encoding="utf-8")


def fmt(k, n):
    return ev.fmt(k, n)


def load_pred(path):
    out = []
    with open(path, encoding="utf-8") as f:
        for ln in f:
            p = json.loads(ln)
            p["_c"] = cl.content(p.get("excerpt_clean") or p.get("excerpt") or "")
            out.append(p)
    return out


def ref_rows():
    ref = []
    for r in cl._csv(cl.FILES["c12_reference"]):
        r["_c"] = cl.content(r["excerpt"])
        r["_page"] = int(r["page"]) if r["page"].strip().isdigit() else None
        ref.append(r)
    return ref


def adjudicated():
    rows = []
    for r in cl._csv(cl.FILES["c12_adjudication"]):
        r["_c"] = cl.content(r["excerpt_clean"])
        r["_page"] = int(r["page"]) if str(r["page"]).isdigit() else None
        rows.append(r)
    return rows


def macro(per):
    vals = [k / n for k, n in per.values() if n]
    return "%.1f%%" % (100 * sum(vals) / len(vals)) if vals else "n/a"


def score_ref(preds, ref, htypes, qtypes=("question_of_law",)):
    """Recall/precision-LB on the 30-judgment C12 reference with the primary matcher."""
    thr, pd = ev.VARIANTS["primary"]
    H = [p for p in preds if p["item_type"] in htypes]
    Q = [p for p in preds if p["item_type"] in qtypes]
    refH = [r for r in ref if r["item_type"] == "holding"]
    refQ = [r for r in ref if r["item_type"] == "question_of_law"]
    byj = collections.defaultdict(list)
    for p in H:
        byj[p["judgment_id"]].append(p)
    byjq = collections.defaultdict(list)
    for p in Q:
        byjq[p["judgment_id"]].append(p)
    rec = sum(1 for r in refH if any(ev.match(p, r, thr, pd) for p in byj[r["judgment_id"]]))
    perj = collections.defaultdict(lambda: [0, 0])
    for r in refH:
        perj[r["judgment_id"]][1] += 1
        if any(ev.match(p, r, thr, pd) for p in byj[r["judgment_id"]]):
            perj[r["judgment_id"]][0] += 1
    recq = sum(1 for r in refQ if any(ev.match(p, r, thr, pd) for p in byjq[r["judgment_id"]]))
    refj = collections.defaultdict(list)
    for r in ref:
        refj[r["judgment_id"]].append(r)
    plb = sum(1 for p in H if any(ev.match(p, r, thr, pd) for r in refj[p["judgment_id"]] if r["item_type"] == "holding"))
    plb_any = sum(1 for p in H if any(ev.match(p, r, thr, pd) for r in refj[p["judgment_id"]]))
    qlb = sum(1 for p in Q if any(ev.match(p, r, thr, pd) for r in refj[p["judgment_id"]] if r["item_type"] == "question_of_law"))
    return {"rec": (rec, len(refH)), "rec_macro": macro({k: tuple(v) for k, v in perj.items()}), "recq": (recq, len(refQ)),
            "plb": (plb, len(H)), "plb_any": (plb_any, len(H)), "qlb": (qlb, len(Q)), "nH": len(H), "nQ": len(Q),
            "per_j": {k: tuple(v) for k, v in perj.items()}}


def adjudicated_proxy(preds, adj, htypes):
    """Predicted holdings that coincide (primary matcher, both directions) with an item the C12 blind evaluator
    adjudicated in its holding sample: share labelled CORRECT_HOLDING. A biased proxy (the adjudicated items
    were C12's own holding candidates), reported only as a direction indicator."""
    thr, pd = ev.VARIANTS["primary"]
    H = [p for p in preds if p["item_type"] in htypes]
    adjH = [a for a in adj if a["item_type"] == "holding"]
    hit = collections.Counter()
    for p in H:
        for a in adjH:
            if a["judgment_id"] != p["judgment_id"]:
                continue
            aa = {"_c": a["_c"], "_page": a["_page"], "judgment_id": a["judgment_id"]}
            if ev.match(p, aa, thr, pd):
                hit[a["label"]] += 1
                break
    # adjudicated non-holdings that C13 no longer emits as holding
    kept_bad = sum(v for k, v in hit.items() if k != "CORRECT_HOLDING")
    return hit, kept_bad


def adjudicated_rejections(preds, adj, htypes):
    """For each C12 adjudicated holding-sample item: is it emitted by C13 as a holding?"""
    thr, pd = ev.VARIANTS["primary"]
    H = collections.defaultdict(list)
    for p in preds:
        if p["item_type"] in htypes:
            H[p["judgment_id"]].append(p)
    tab = collections.Counter()
    for a in adj:
        if a["item_type"] != "holding":
            continue
        aa = {"_c": a["_c"], "_page": a["_page"], "judgment_id": a["judgment_id"]}
        emitted = any(ev.match(p, aa, thr, pd) for p in H[a["judgment_id"]])
        tab[(a["label"] + (":" + a["subtype"] if a.get("subtype") else ""), emitted)] += 1
    return tab


def norm40(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def lcs_len(a, b):
    import difflib
    m = difflib.SequenceMatcher(None, a, b, autojunk=False).find_longest_match(0, len(a), 0, len(b))
    return m.size


def score_gt(preds, gt, htypes, rule):
    byj = collections.defaultdict(list)
    for p in preds:
        if p["item_type"] in htypes:
            byj[p["judgment_id"]].append(p)
    k = 0
    perj = collections.defaultdict(lambda: [0, 0])
    for g in gt:
        ok = False
        for p in byj[g["judgment_id"]]:
            if g["page"] is not None and not (p["page"] - 1 <= g["page"] <= (p.get("page_end") or p["page"]) + 1):
                continue
            if rule == "primary":
                inter = len(p["_c"] & g["_c"])
                if inter >= 3 and p["_c"] and g["_c"] and inter / min(len(p["_c"]), len(g["_c"])) >= 0.6:
                    ok = True
                    break
            else:
                if lcs_len(norm40(p.get("excerpt_clean") or p.get("excerpt")), norm40(g["excerpt"])) >= 40:
                    ok = True
                    break
        perj[g["judgment_id"]][1] += 1
        if ok:
            k += 1
            perj[g["judgment_id"]][0] += 1
    return (k, len(gt)), macro({a: tuple(b) for a, b in perj.items()})


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred-ref", required=True)
    ap.add_argument("--pred-gt", required=True)
    ap.add_argument("--oof", required=True)
    ap.add_argument("--texts", default="", help="optional: JSONL of {judgment_id, s, e, sent} used for OOF label matching")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    ref = ref_rows()
    adj = adjudicated()
    p13 = load_pred(os.path.join(a.pred_ref, "HOLDINGS_C13.jsonl"))
    p12 = load_pred(C12_PRED_REF)
    s13 = score_ref(p13, ref, HOLDING_TYPES_C13)
    s13all = score_ref(p13, ref, ALL_HOLDING_C13)
    s12 = score_ref(p12, ref, {"holding"})
    L = []
    L.append("# C13-A3 development evaluation (IN-SAMPLE) - c13-holdings vs c12-holdings/1.0.0\n")
    L.append("**Every figure on this page is in-sample.** The C12 reference (30 judgments), the C12 adjudication sample, the C12 dev "
             "hand-check and the C11 GT trained the C13 classifier and were read while the C13 rules were written. The C12 figures on the "
             "same rows are the frozen C12 predictions re-scored with the same matcher; for C12 these rows were blind (reference) or in-sample "
             "(C11 GT). The comparison therefore flatters C13. The only valid test is the fresh A0 set scored by an independent evaluator.\n")
    L.append("Status of all items: `AUTOMATED_CANDIDATE_NOT_VERIFIED`. Not legal validation.\n")
    L.append("## 1. C12 holdings reference (30 judgments), C12 pre-registered primary matcher\n")
    L.append("| Metric | c12-holdings (frozen, blind for C12) | c13 (in-sample) |\n| --- | --- | --- |")
    L.append("| Holding recall (`holding`) | %s; macro %s | %s; macro %s |" % (fmt(*s12["rec"]), s12["rec_macro"], fmt(*s13["rec"]), s13["rec_macro"]))
    L.append("| Holding recall incl. dissent/split candidates | n/a | %s |" % fmt(*s13all["rec"]))
    L.append("| QoL recall | %s | %s |" % (fmt(*s12["recq"]), fmt(*s13["recq"])))
    L.append("| Predicted `holding` items | %d | %d |" % (s12["nH"], s13["nH"]))
    L.append("| Holding precision, reference-match lower bound (vs ref holdings) | %s | %s |" % (fmt(*s12["plb"]), fmt(*s13["plb"])))
    L.append("| Holding precision, lower bound (vs any ref item) | %s | %s |" % (fmt(*s12["plb_any"]), fmt(*s13["plb_any"])))
    L.append("| Predicted QoL items | %d | %d |" % (s12["nQ"], s13["nQ"]))
    L.append("| QoL precision lower bound | %s | %s |" % (fmt(*s12["qlb"]), fmt(*s13["qlb"])))
    L.append("")
    tab = adjudicated_rejections(p13, adj, HOLDING_TYPES_C13)
    L.append("## 2. The 60 C12 holdings the blind evaluator adjudicated: does C13 still emit them as `holding`?\n")
    L.append("| C12 adjudication label | emitted by C13 as holding | not emitted |\n| --- | --- | --- |")
    labs = sorted(set(k[0] for k in tab))
    tot_e = tot_n = good_e = 0
    for lb in labs:
        e, n = tab[(lb, True)], tab[(lb, False)]
        L.append("| %s | %d | %d |" % (lb, e, n))
        tot_e += e
        tot_n += n
        if lb.startswith("CORRECT_HOLDING"):
            good_e = e
    L.append("")
    L.append("Of the C12 holding-sample items C13 still emits as holdings, %d/%d were adjudicated CORRECT_HOLDING (C12: 25/60). "
             "This is a biased direction indicator only: it covers C13 holdings that coincide with C12's adjudicated sample, not C13's new "
             "items. It is not a precision estimate.\n" % (good_e, tot_e))
    gt = [r for r in cl.load_labels() if r["src"] == "c11_gt" and r["kind"] == "holding"]
    p13g = load_pred(os.path.join(a.pred_gt, "HOLDINGS_C13.jsonl"))
    p12g = load_pred(C12_PRED_DEV)
    gt_ids = set(p["judgment_id"] for p in p13g) | set(cl.c11_gt_ids())
    gt = [g for g in gt if g["judgment_id"] in gt_ids]
    L.append("## 3. C11 holdout ground truth (%d holdings, %d judgments)\n" % (len(gt), len(set(g["judgment_id"] for g in gt))))
    L.append("| Matcher | c12 `holding` (in-sample for C12) | c13 `holding` (in-sample) |\n| --- | --- | --- |")
    for rule, name in (("primary", "C12 primary (>=60% containment, page +-1)"), ("dev40", "C12 dev rule (40 common chars, page +-1)")):
        (k12, n12), m12 = score_gt(p12g, gt, {"holding"}, rule)
        (k13, n13), m13 = score_gt(p13g, gt, HOLDING_TYPES_C13, rule)
        L.append("| %s | %s; macro %s | %s; macro %s |" % (name, fmt(k12, n12), m12, fmt(k13, n13), m13))
    n12h = sum(1 for p in p12g if p["item_type"] == "holding")
    n13h = sum(1 for p in p13g if p["item_type"] == "holding")
    L.append("| Predicted `holding` items | %d | %d |" % (n12h, n13h))
    L.append("")
    # OOF
    rows = [json.loads(l) for l in _open(a.oof)]
    L.append("## 4. Out-of-fold classifier estimate (grouped 5-fold by judgment; holding head only)\n")
    L.append("Sentence-level: court-voice sentences whose out-of-fold probability is at or above T and that pass the deterministic holding vetoes (`c13_extract.holding_veto`; the opinion floor and operative/QoL precedence of the full extractor are not emulated). 'Labelled positive' = the sentence "
             "matches a positive holding label (C12 reference, C11 GT, adjudicated or hand-checked correct). 'Explicitly labelled' = it "
             "matches any labelled row (positive or negative). The share among explicitly labelled sentences is a precision proxy restricted "
             "to labelled material; unlabelled selected sentences are not scored. Recall: positive holding labels from the C12 reference and "
             "C11 GT with at least one matching sentence selected.\n")
    labels = [r for r in cl.load_labels() if r["kind"] == "holding" and r["polarity"] > 0 and r["src"] in ("c12_reference", "c11_gt")]
    ids = set(r["judgment_id"] for r in rows)
    labels = [r for r in labels if r["judgment_id"] in ids]
    sents = {}
    if a.texts:
        for ln in _open(a.texts):
            t = json.loads(ln)
            sents[(t["judgment_id"], t["s"])] = cl.content(t["sent"])
    by_j = collections.defaultdict(list)
    for r in rows:
        by_j[r["judgment_id"]].append(r)
    L.append("| T | selected | per judgment | labelled positive | explicitly labelled | proxy precision | label recall (C12 ref + C11 GT) |\n| --- | --- | --- | --- | --- | --- | --- |")
    stext = {}
    if a.texts:
        for ln in _open(a.texts):
            t = json.loads(ln)
            stext[(t["judgment_id"], t["s"])] = t["sent"]
    for r in rows:
        r["_veto"] = bool(cx.holding_veto(stext.get((r["judgment_id"], r["s"]), "")))
    for T in (0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95):
        sel = [r for r in rows if r["oof_holding"] >= T and not r["_veto"]]
        pos = sum(1 for r in sel if r["y_holding"] == 1)
        expl = sum(1 for r in sel if r["srcs"])
        rec = 0
        if sents:
            for lab in labels:
                for r in by_j[lab["judgment_id"]]:
                    if r["oof_holding"] < T or r["_veto"]:
                        continue
                    c = sents.get((r["judgment_id"], r["s"]))
                    if c is not None and cl.sentence_matches(c, r["page"], r["page_end"], lab):
                        rec += 1
                        break
        L.append("| %.2f | %d | %.1f | %d | %d | %s | %s |" % (T, len(sel), len(sel) / max(1, len(ids)), pos, expl,
                                                             fmt(pos, expl) if expl else "n/a", fmt(rec, len(labels)) if sents else "n/a"))
    L.append("")
    L.append("## 5. Per-judgment (C12 reference, primary matcher)\n")
    L.append("| judgment_id | ref holdings | c12 recovered | c13 recovered | c12 predicted | c13 predicted |\n| --- | --- | --- | --- | --- | --- |")
    c12n = collections.Counter(p["judgment_id"] for p in p12 if p["item_type"] == "holding")
    c13n = collections.Counter(p["judgment_id"] for p in p13 if p["item_type"] == "holding")
    for j in sorted(s13["per_j"]):
        L.append("| %s | %d | %d | %d | %d | %d |" % (j, s13["per_j"][j][1], s12["per_j"].get(j, (0, 0))[0], s13["per_j"][j][0], c12n[j], c13n[j]))
    L.append("")
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    summary = {"c13_ref": {k: v for k, v in s13.items() if k != "per_j"}, "c12_ref": {k: v for k, v in s12.items() if k != "per_j"}}
    with open(os.path.splitext(a.out)[0] + ".json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=1, sort_keys=True, default=list)
        f.write("\n")
    print("\n".join(L[:20]))


if __name__ == "__main__":
    main()
