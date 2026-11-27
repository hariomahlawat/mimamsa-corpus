"""POST-HOC item-exclusion sensitivities for keyed tasks (GA4 evaluator). Not headline figures."""
import csv, json, re, sys
from collections import defaultdict, Counter
sys.path.insert(0, sys.argv[1]); S = sys.argv[2]; task_name, holdout, pred_path, out_path = sys.argv[3:7]
from c13_score import load_design, run, aggregate
from c13_tasks import TASKS
from c13_coding import group
task = TASKS[task_name]
rd = lambda p: list(csv.DictReader(open(p, encoding="utf-8")))
design = load_design(holdout)
truth = rd(f"{S}/eval/store/{holdout}/v001/{holdout}.csv"); pred = rd(pred_path)
res, rows = run(task_name, holdout, truth, pred, design)
G = group(truth)
unc = sorted(i for i, rs in G.items() if rs and all(task.is_uncodable_row(r) for r in rs))
pat = re.compile(r"\b(CAPF|CRPF|BSF|ITBP|CISF|SSB|Sashastra Seema|Assam Rifles|Border Security Force|Central Reserve Police|Indo-Tibetan|para-?military|Coast Guard|NSG)\b", re.I)
txt = defaultdict(str)
for r in truth: txt[r["item_id"]] += " " + (r.get("notes") or "")
for sub in ("coder_1", "coder_2"):
    for r in rd(f"{S}/coding/{holdout}/{sub}/CODER_SHEET.csv"): txt[r["item_id"]] += " " + (r.get("notes") or "")
for r in rd(f"{S}/coding/{holdout}/adjudicator/ADJUDICATION_RESULT.csv"):
    txt[r["item_id"]] += " " + (r.get("notes") or "") + " " + (r.get("reason") or "")
capf = {i for i, t in txt.items() if pat.search(t)}
store_main = {i for i, t in txt.items() if "HF@main" in t}
ngold = Counter(r["item_id"] for r in truth if not task.is_uncodable_row(r))
big = {i for i, n in ngold.items() if n >= 13}
allitems = sorted(design)
variants = {"exclude_capf_mention_items": capf, "exclude_store_pointer_HF_main_items": store_main,
            f"exclude_items_with_13plus_gold_units": big}
out = {"note": "POST-HOC (specified after the headline was computed); not headline figures; same estimator as the harness.",
       "sets": {k: sorted(v) for k, v in variants.items()}}
for k, ex in variants.items():
    a = aggregate(task, rows, design, "posthoc|" + k, items=[i for i in allitems if i not in ex], uncodable=unc)
    out[k] = {f: {m: a[f][m] for m in ("strict_precision", "coverage")} for f in task.scored_fields}
json.dump(out, open(out_path, "w"), indent=1, sort_keys=True)
for k in variants:
    print(k, len(variants[k]), "items")
    for f, v in out[k].items():
        sp, cv = v["strict_precision"], v["coverage"]
        print(f"   {f}: SP w={sp['weighted']} CP{sp['weighted_design_cp95']} unw={sp['unweighted']} ({sp['k']}/{sp['n']}) | "
              f"COV w={cv['weighted']} CP{cv['weighted_design_cp95']} unw={cv['unweighted']} ({cv['k']}/{cv['n']})")
