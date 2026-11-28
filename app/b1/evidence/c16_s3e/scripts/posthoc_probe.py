"""C16 S3-E post-hoc diagnosis (run AFTER every declared oracle run): dense rank of the passages RET-07/RET-10 need,
per model, on the SYN site. Query texts as quoted in the C15 report. Nothing is tuned from this output."""
import json, sys
import numpy as np
sys.path.insert(0, sys.argv[1])
import dev_eval as d
m = json.load(open(r"E:\Mimamsa-Data\syn\fixture_map.json", encoding="utf-8"))
rev = {tuple(v): k for k, v in m["map"].items()}
rows = [json.loads(l) for l in open(r"E:\Mimamsa-Data\c16s3e\syn_passages.jsonl", encoding="utf-8")]
ids = [rev.get((r["doc_id"], r["passage_id"]), "UNCAT:" + r["doc_id"]) for r in rows]
cases = {"RET-07": ("Can someone challenge a hearing when nobody told them the allegation beforehand?", "J1-MAJ"),
         "RET-10": ("late warning invalidates hearing without notice", "J2-MAJ")}
for model in ["e5-small", "e5-base", "arctic-m2", "e5-large", "bge-m3"]:
    e = d.Embedder(model)
    P = e.embed([e.pp + r["text"] for r in rows], 256)
    for c, (q, need) in cases.items():
        s = P @ e.embed([e.qp + q], 128)[0]
        order = list(np.argsort(-s, kind="stable"))
        cat = [i for i in order if not ids[i].startswith("UNCAT")]
        k = ids.index(need)
        print(f"{model:9} {c} {need}: rank {order.index(k)+1}/{len(rows)} (catalogued {cat.index(k)+1}/{len(cat)}) cos {s[k]:.4f}; best {s[order[0]]:.4f}; uncatalogued above it: {sum(1 for i in order[:order.index(k)] if ids[i].startswith('UNCAT'))}")
