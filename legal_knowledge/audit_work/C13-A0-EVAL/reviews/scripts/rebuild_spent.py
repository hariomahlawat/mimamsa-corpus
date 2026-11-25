"""Independent spent-set rebuild (reviewer). Uses the frame (FRAME_RECORDS) as identity source, not the author's maps."""
import csv, json, re, sys, os, glob
from collections import defaultdict
SRC = sys.argv[1]  # repo root of scratch copy
AW = os.path.join(SRC, "legal_knowledge/audit_work")
A0 = os.path.join(AW, "C13-A0-EVAL/outputs")
R = lambda p: list(csv.DictReader(open(p, encoding="utf-8", newline="")))
recs = R(f"{A0}/frame/FRAME_RECORDS.csv")
sha2k, jid2k, doc2k = {}, {}, {}
for r in recs:
    sha2k[r["sha256"]] = r["judgment_key"]; doc2k[r["doc_id"]] = r["judgment_key"]
    if r["judgment_id"]: jid2k[r["judgment_id"]] = r["judgment_key"]
    jid2k.setdefault("J-" + r["sha256"][:16], r["judgment_key"])
# also all copies from C11 identity register (non-frame copies)
for r in R(f"{AW}/C11-JUDICIAL-QUALITY/identity/outputs/JUDGMENT_IDENTITY_REGISTER.csv"):
    sha2k.setdefault(r["sha256"], r["judgment_key"]); jid2k.setdefault(r["judgment_id_c10"], r["judgment_key"])
    for d in r["doc_ids"].split(";"):
        if d: doc2k.setdefault(d, r["judgment_key"])
JID = re.compile(r"J-[0-9a-f]{16}"); SHA = re.compile(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])")
JK = re.compile(r"JK-[0-9a-f]{16}")
DOC = re.compile(r"(?:sc|hc)-[a-z0-9][a-z0-9.\-]{8,}[a-z0-9]")
keys_frame = {r["judgment_key"] for r in recs}
def scan(path):
    t = open(path, encoding="utf-8", errors="replace").read()
    hits, unmapped = set(), set()
    for m in JID.findall(t):
        (hits.add(jid2k[m]) if m in jid2k else unmapped.add(m))
    for m in JK.findall(t):
        (hits.add(m) if m in keys_frame else unmapped.add(m))
    for m in SHA.findall(t):
        if m in sha2k: hits.add(sha2k[m])
    for m in DOC.findall(t):
        if m in doc2k: hits.add(doc2k[m])
    return hits, unmapped
sets = {
 "C11_HOLDOUT_56": ["C11-JUDICIAL-QUALITY/holdout/HOLDOUT_SAMPLE.csv", "C11-JUDICIAL-QUALITY/evaluation/holdout_predictions/HOLDOUT_IDS.txt"],
 "C11_DEV_GOLD": ["C11-JUDICIAL-QUALITY/extraction/tools/dev_gold.json", "C11-JUDICIAL-QUALITY/extraction/outputs/DEV_EVALUATION_ROWS.csv"],
 "C12_V3_HOLDOUT": ["C12-CONSOLIDATION/holdout_v3/HOLDOUT_V3_SAMPLE.csv", "C12-CONSOLIDATION/holdout_v3/ADJUDICATION.csv"] + sorted(glob.glob(f"{AW}/C12-CONSOLIDATION/holdout_v3/coding/*.csv")),
 "C12_HOLD_REF": ["C12-CONSOLIDATION/holdings_reference/SELECTION.csv", "C12-CONSOLIDATION/holdings_reference/REFERENCE_HOLDINGS.csv", "C12-CONSOLIDATION/holdings_eval/EVALUATION_ROWS.csv"],
 "C12_DEV_GOLD_V3": ["C12-CONSOLIDATION/extractor_v3/tools/dev_gold_v3.json"],
 "C12_HOLD_DEV_IDS": ["C12-CONSOLIDATION/holdings/outputs/dev_predictions/DEV_IDS.txt"],
}
out = {}
for s, fs in sets.items():
    allh = set()
    for f in fs:
        p = f if f.startswith("/") else os.path.join(AW, f)
        h, u = scan(p); allh |= h
        print(f"{s}\t{os.path.relpath(p, AW)}\thits={len(h)}\tunmapped={len(u)} {sorted(u)[:5]}")
    out[s] = allh
# dev_gold_v3 keys explicitly
d = json.load(open(f"{AW}/C12-CONSOLIDATION/extractor_v3/tools/dev_gold_v3.json"))
miss = [k for k in d if k not in jid2k]
print("dev_gold_v3 keys", len(d), "unmapped", miss, [str(d[k])[:80] for k in miss])
d = json.load(open(f"{AW}/C11-JUDICIAL-QUALITY/extraction/tools/dev_gold.json"))
print("C11 dev_gold keys", len([k for k in d if k.startswith("J-")]), "unmapped", [k for k in d if k.startswith("J-") and k not in jid2k])
json.dump({k: sorted(v) for k, v in out.items()}, open(sys.argv[2], "w"), indent=1)
