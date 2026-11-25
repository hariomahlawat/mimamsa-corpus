"""POST-HOC definitional sensitivity for H-HOLD-C13 (GA4 evaluator). Not a headline figure.
Uses the pre-registered estimator (c13_score.estimate: weighted HT ratio + design-effect CP) on alternative
reference definitions built from the adjudicator's borderline tags and the coders' own units."""
import csv, json, re, sys
from collections import defaultdict
sys.path.insert(0, sys.argv[1]); S = sys.argv[2]
from c13_score import load_design, estimate, score_holdings, aggregate_holdings
from c13_tasks import TASKS
from c13_coding import group
from c13_sensitivity import load_subset, PRIMARY
task = TASKS["holdings"]
design = load_design("H-HOLD-C13", reserve_open="all")
for d in design.values(): d.setdefault("cluster", d["cluster"])
rd = lambda p: list(csv.DictReader(open(p, encoding="utf-8")))
truth = rd(S + "/eval/store/H-HOLD-C13/v001/H-HOLD-C13.csv")
pred = rd(S + "/a3-holdings/legal_knowledge/audit_work/C13-A3-HOLDINGS/frozen_predictions/PRED_H-HOLD-C13.csv")
c1 = rd(S + "/coding/H-HOLD-C13/coder_1/CODER_SHEET.csv"); c2 = rd(S + "/coding/H-HOLD-C13/coder_2/CODER_SHEET.csv")
adj = rd(S + "/coding/H-HOLD-C13/adjudicator/ADJUDICATION_RESULT.csv")
TAGS = ["GRANULARITY_SPLIT", "SCOPE", "OBITER", "FACT_FINDING", "QUOTED_PRECEDENT", "COUNSEL_VOICE"]
tagged = defaultdict(set)
for r in adj:
    for t in TAGS:
        if re.search(r"\b" + t + r"\b", r["notes"] or ""): tagged[t].add(r["item_id"])
any_tag = set().union(*tagged.values())
G = group(truth)
unc = {i for i, rs in G.items() if rs and all(task.is_uncodable_row(r) for r in rs)}
items = [i for i in sorted(design) if i not in unc]
prim = {k for k, c in load_subset("H-HOLD-C13").items() if c & PRIMARY}
def U(vals, its):  # vals: item -> (y, x)
    return [(design[i]["cluster"], design[i]["cell"], design[i]["weight"], *vals.get(i, (0, 0))) for i in its]
def hold(rows): return [r for r in rows if (r.get("item_type") or "").strip() == "holding"]
GH = {i: hold(G.get(i, [])) for i in items}
PH = {i: hold([r for r in pred if r["item_id"] == i]) for i in items}
C = {i: hold([r for r in c1 + c2 if r["item_id"] == i]) for i in items}
def official(its, label):
    trows = [r for r in truth if not task.is_uncodable_row(r)]
    for k, r in enumerate(pred): r.setdefault("pred_id", f"P{k+1:05d}")
    rows = score_holdings(task, trows, pred, design, {}, None)
    a = aggregate_holdings(task, rows, design, None, label, items=its, uncodable=unc)["holding"]
    return dict(recall=a["recall"], precision_reference_match_LOWER_BOUND=a["precision_reference_match_LOWER_BOUND"])
def many_to_one(its, accept, label, count_tagged_gold_as_recalled=False):
    rec, prc = {}, {}
    for i in its:
        acc = accept(i)
        prc[i] = (sum(any(task.spans_match(p, g) for g in acc) for p in PH[i]), len(PH[i]))
        rec[i] = (sum((count_tagged_gold_as_recalled and i in any_tag) or any(task.spans_match(g, p) for p in PH[i])
                      for g in GH[i]), len(GH[i]))
    return dict(recall=estimate(U(rec, its), f"posthoc|{label}|r"),
                precision_reference_match_LOWER_BOUND=estimate(U(prc, its), f"posthoc|{label}|p"))
out = {"note": "POST-HOC definitional sensitivity (specified after the headline was computed). Not a headline figure. "
               "Recall vs adjudicated gold unless stated; true (adjudicated) precision does not depend on the gold.",
       "tag_items": {t: len(v) for t, v in tagged.items()}, "items_with_any_tag": len(any_tag & set(items)),
       "scored_items": len(items)}
out["S0_official_reproduced"] = official(items, "S0")
out["S1_exclude_items_with_any_borderline_tag"] = official([i for i in items if i not in any_tag], "S1")
out["S2_exclude_items_tagged_GRANULARITY_SPLIT"] = official([i for i in items if i not in tagged["GRANULARITY_SPLIT"]], "S2")
out["S3_many_to_one_vs_adjudicated_gold"] = many_to_one(items, lambda i: GH[i], "S3")
out["S4_lenient_gold_union_adjudicated_and_both_coders"] = many_to_one(items, lambda i: GH[i] + C[i], "S4")
out["S5_lenient_union_and_tagged_gold_counted_recalled"] = many_to_one(items, lambda i: GH[i] + C[i], "S5", True)
out["S4_without_primary_pre_exposed"] = many_to_one([i for i in items if design[i]["cluster"] not in prim],
                                                    lambda i: GH[i] + C[i], "S4p")
json.dump(out, open(sys.argv[3], "w"), indent=1, sort_keys=True)
for k, v in out.items():
    if isinstance(v, dict) and "recall" in v:
        r, p = v["recall"], v["precision_reference_match_LOWER_BOUND"]
        print(f"{k}: recall w={r['weighted']} CP{r['weighted_design_cp95']} unw={r['unweighted']} ({r['k']}/{r['n']}) | "
              f"refmatch-prec w={p['weighted']} CP{p['weighted_design_cp95']} unw={p['unweighted']} ({p['k']}/{p['n']})")
print({k: v for k, v in out.items() if not isinstance(v, dict) or "recall" not in v})
