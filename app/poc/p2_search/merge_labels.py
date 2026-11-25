"""Merge blind manual labels (entered by sheet index) into qrels. Unlisted sheet items are explicit grade 0.
python -I merge_labels.py <qrels.json> <sheets/_mapping.json> <manual_labels.json>"""
import json, sys
qrels = json.load(open(sys.argv[1])); mapping = json.load(open(sys.argv[2])); labels = json.load(open(sys.argv[3]))
n = 0
for qid, order in mapping.items():
    lab = labels.get(qid)
    if lab is None:
        continue
    for i, d in enumerate(order):
        if d in qrels.setdefault(qid, {}) and qrels[qid][d]["by"] != "pending":
            continue
        qrels[qid][d] = {"grade": int(lab.get(str(i), 0)), "by": "ai_manual_blind_snippet"}
        n += 1
json.dump(qrels, open(sys.argv[1], "w"), indent=0, sort_keys=True)
print("merged", n)
