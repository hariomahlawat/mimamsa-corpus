"""Compute P2/P3 metrics from runs + qrels.

python -I metrics.py <qrels.json> <out_prefix> <runs_dir> [<runs_dir> ...]
Writes <out_prefix>.csv (system x category) and <out_prefix>_per_query.csv.

Recall@10        = relevant in top 10 / all known relevant (pooled + full-collection scan for objective categories)
CapRecall@10     = relevant in top 10 / min(10, |relevant|)   (meaningful when hundreds of docs cite a section)
P@10, MRR (first doc with grade>=1), nDCG@10 (gains 0/1/2, ideal from all known labels)
ExactID@1 / @10  = identifier queries (case_number, citation) whose target doc is at rank 1 / in top 10
KnownItem@1/@10  = same for case_name
Judged@10        = share of top-10 docs that carry a label (unjudged count as non-relevant)
"""
import csv, json, math, sys
from collections import defaultdict
from pathlib import Path

qrels = json.loads(Path(sys.argv[1]).read_text())
out = Path(sys.argv[2])
queries = {q["qid"]: q for q in json.load(open(Path(__file__).resolve().parent / "queries.json"))}
runs = {}
for d in sys.argv[3:]:
    for f in sorted(Path(d).glob("*.json")):
        j = json.loads(f.read_text()); runs[j["system"]] = j["run"]


def per_query(run, qid):
    lab = {d: v["grade"] for d, v in qrels.get(qid, {}).items()}
    top = [d for d, _s in run.get(qid, [])[:10]]
    rel = {d for d, g in lab.items() if g >= 1}
    hits = [d for d in top if lab.get(d, 0) >= 1]
    rr = 0.0
    for i, d in enumerate(run.get(qid, [])[:100]):
        if lab.get(d, 0) >= 1:
            rr = 1.0 / (i + 1); break
    dcg = sum((2 ** lab.get(d, 0) - 1) / math.log2(i + 2) for i, d in enumerate(top))
    ideal = sorted(lab.values(), reverse=True)[:10]
    idcg = sum((2 ** g - 1) / math.log2(i + 2) for i, g in enumerate(ideal))
    q = queries[qid]
    m = dict(P10=len(hits) / 10, R10=(len(hits) / len(rel)) if rel else 0.0,
             CapR10=(len(hits) / min(10, len(rel))) if rel else 0.0, MRR=rr,
             nDCG10=dcg / idcg if idcg else 0.0, Judged10=sum(d in lab for d in top) / max(1, len(top)), nrel=len(rel))
    if q.get("target"):
        m["Target@1"] = float(bool(top) and top[0] == q["target"])
        m["Target@10"] = float(q["target"] in top)
    return m


rows, pq = [], []
for s, run in runs.items():
    agg = defaultdict(lambda: defaultdict(list))
    for qid in queries:
        m = per_query(run, qid)
        cat = queries[qid]["category"]
        pq.append(dict(system=s, qid=qid, category=cat, **{k: round(v, 4) for k, v in m.items()}))
        for k, v in m.items():
            agg[cat][k].append(v); agg["ALL"][k].append(v)
            if cat in ("case_number", "citation"):
                agg["identifier"][k].append(v)
    for cat, d in agg.items():
        row = dict(system=s, category=cat, n=len(d["MRR"]))
        for k in ("P10", "R10", "CapR10", "MRR", "nDCG10", "Judged10", "Target@1", "Target@10"):
            if d.get(k):
                row[k] = round(sum(d[k]) / len(d[k]), 4)
        rows.append(row)

fields = ["system", "category", "n", "P10", "R10", "CapR10", "MRR", "nDCG10", "Target@1", "Target@10", "Judged10"]
with open(f"{out}.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
with open(f"{out}_per_query.csv", "w", newline="") as f:
    keys = ["system", "qid", "category", "P10", "R10", "CapR10", "MRR", "nDCG10", "Judged10", "nrel", "Target@1", "Target@10"]
    w = csv.DictWriter(f, fieldnames=keys); w.writeheader(); w.writerows(pq)
for r in rows:
    if r["category"] in ("ALL",):
        print(f"{r['system']:45s} nDCG10={r.get('nDCG10')} MRR={r.get('MRR')} P10={r.get('P10')} CapR10={r.get('CapR10')} judged={r.get('Judged10')}")
