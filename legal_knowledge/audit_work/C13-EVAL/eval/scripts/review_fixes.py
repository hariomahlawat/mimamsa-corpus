"""GA4 review fixes (F2-F4): A5 per-gold-type recall with intervals; A5 exposure sensitivity; H-HOLD gold provenance."""
import csv, json, sys
from collections import defaultdict, Counter
sys.path.insert(0, sys.argv[1]); S = sys.argv[2]
from c13_score import load_design, run, aggregate, estimate
from c13_tasks import TASKS
from c13_coding import group
from c13_sensitivity import load_subset, PRIMARY
import c13_stats as ST
rd = lambda p: list(csv.DictReader(open(p, encoding="utf-8")))
out = {"note": "Added after the GA4 review (post-hoc, descriptive). Same harness estimator."}
# --- A5 per gold type recall
task = TASKS["relations"]; design = load_design("H-REL-C13")
truth = rd(f"{S}/eval/store/H-REL-C13/v001/H-REL-C13.csv")
pred = rd(f"{S}/a5-graph/legal_knowledge/audit_work/C13-A5-GRAPH/freeze/H-REL-C13_PREDICTIONS.csv")
res, rows = run("relations", "H-REL-C13", truth, pred, design)
G = group(truth); unc = {i for i, rs in G.items() if rs and all(task.is_uncodable_row(r) for r in rs)}
items = [i for i in sorted(design) if i not in unc]
rec = {}
for t in ("cites", "follows", "applies", "not_followed", "distinguishes"):
    per = defaultdict(lambda: [0, 0])
    for r in rows:
        if r["item_id"] in unc or r.get("relation_type__gold") != t: continue
        per[r["item_id"]][1] += 1; per[r["item_id"]][0] += r.get("relation_type__pred") == t
    units = [(design[i]["cluster"], design[i]["cell"], design[i]["weight"], *per.get(i, (0, 0))) for i in items]
    e = estimate(units, f"review|rel_recall|{t}"); k, n = sum(v[0] for v in per.values()), sum(v[1] for v in per.values())
    e["unweighted_wilson95_check"] = [ST.rnd(x) for x in ST.wilson(k, n)]
    rec[t] = e
    print(t, f"k={e['k']} n={e['n']} unw={e['unweighted']} W{e['unweighted_wilson95']} w={e['weighted']} CP{e['weighted_design_cp95']} neff={e['weighted_design_cp_n_eff']}")
out["A5_recall_by_gold_type"] = rec
# --- A5 author text exposure sensitivity
dk = {i: d["cluster"] for i, d in design.items()}
prim = {k for k, c in load_subset("H-REL-C13").items() if c & PRIMARY}
a5x = {"JK-f7c70c98230234f6", "JK-4d86990aad309acd", "JK-88a22c0473110afc", "JK-aac99e3e5fbad324"}
keep = [i for i in sorted(design) if dk[i] not in prim | a5x]
a = aggregate(task, rows, design, "review|a5x", items=keep, uncodable=sorted(unc))
out["A5_without_primary_and_author_exposed"] = {"items_excluded": len(design) - len(keep),
    "in_design": sorted(a5x & set(dk.values())), **{f: {m: a[f][m] for m in ("strict_precision", "coverage")} for f in a}}
for f in a:
    sp = a[f]["strict_precision"]; print("A5x", len(design) - len(keep), f, sp["weighted"], sp["weighted_design_cp95"], f"{sp['k']}/{sp['n']}")
# --- H-HOLD gold provenance
th = rd(f"{S}/eval/store/H-HOLD-C13/v001/H-HOLD-C13.csv")
adj = {r["item_id"]: r["agrees_with"] for r in rd(f"{S}/coding/H-HOLD-C13/adjudicator/ADJUDICATION_RESULT.csv")}
print("adj items", Counter(adj.values()))
Gh = group(th); uh = {i for i, rs in Gh.items() if all(TASKS["holdings"].is_uncodable_row(r) for r in rs)}
prov = Counter()
for r in th:
    if r["item_id"] in uh or r["item_type"] != "holding": continue
    prov[adj.get(r["item_id"], "BOTH_CODERS_AGREE")] += 1
print("gold holdings by provenance", prov, sum(prov.values()))
out["H_HOLD_gold_provenance"] = {"adjudicated_items_agrees_with": dict(Counter(adj.values())), "scored_gold_holdings_by_source": dict(prov)}
json.dump(out, open(sys.argv[3], "w"), indent=1, sort_keys=True)
