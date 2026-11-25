"""Blind viewer for predicted-holding adjudication: shows only pointer, page, opinion, excerpt and source context."""
import csv, json, re, sys, collections
sys.path.insert(0, sys.argv[1])
from c13_score import load_design
S = sys.argv[2]; lo, hi = int(sys.argv[3]), int(sys.argv[4]); B = int(sys.argv[5]) if len(sys.argv) > 5 else 1100
design = load_design("H-HOLD-C13")
pred = {r["pred_id"]: r for r in csv.DictReader(open(S + "/a3-holdings/legal_knowledge/audit_work/C13-A3-HOLDINGS/frozen_predictions/PRED_H-HOLD-C13.csv"))}
samp = list(csv.DictReader(open(S + "/eval/H-HOLD-C13/pred_adjudication/SAMPLE_PRED_IDS.csv")))
need = {design[s["item_id"]]["sha256"] for s in samp}
pages = collections.defaultdict(dict)
for line in open(S + "/eval/work/PAGES.jsonl", encoding="utf-8"):
    o = json.loads(line)
    if o["sha256"] in need: pages[o["sha256"]][o["page"]] = o["text"]
def nw(s): return re.sub(r"\s+", " ", s or "").strip()
for s in samp[lo - 1:hi]:
    p = pred[s["pred_id"]]; sha = design[s["item_id"]]["sha256"]; pg = pages[sha]
    full = " ".join(nw(pg[k]) for k in sorted(pg))
    ex = nw(p["excerpt"]); i = full.find(ex[:80])
    n = max(pg)
    print(f"\n######## #{s['order']} {s['pred_id']} item={s['item_id']} court={design[s['item_id']]['court']} page={p['page']}/{n} opinion={p['opinion']} judge={p['judge']}")
    print("EXCERPT:", ex[:700])
    if i < 0: print("  [excerpt not found verbatim in text]"); i = full.find(ex[:30])
    print("CONTEXT:", full[max(0, i - B): i + len(ex) + 500] if i >= 0 else "(none)")
    print("START:", full[:350]); print("END:", full[-450:])
