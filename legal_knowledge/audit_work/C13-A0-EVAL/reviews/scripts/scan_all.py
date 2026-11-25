import csv, os, re, sys, gzip
from collections import defaultdict
SRC = sys.argv[1]; AW = f"{SRC}/legal_knowledge/audit_work"; A0 = f"{AW}/C13-A0-EVAL/outputs"
R = lambda p: list(csv.DictReader(open(p, encoding="utf-8", newline="")))
recs = R(f"{A0}/frame/FRAME_RECORDS.csv")
tok2k = {}
for r in recs:
    tok2k[r["sha256"]] = r["judgment_key"]; tok2k[r["doc_id"]] = r["judgment_key"]
    tok2k["J-" + r["sha256"][:16]] = r["judgment_key"]; tok2k[r["judgment_key"]] = r["judgment_key"]
hold = defaultdict(set)
for h in ("H-OUT-C13", "H-HOLD-C13", "H-REL-C13"):
    for r in R(f"{A0}/holdouts/{h}/SAMPLE.csv"): hold[r["judgment_key"]].add(h)
for r in R(f"{A0}/holdouts/H-HOLD-C13/RESERVE.csv"): hold[r["judgment_key"]].add("RESERVE")
TOK = re.compile(r"JK-[0-9a-f]{16}|J-[0-9a-f]{16}|[0-9a-f]{64}|(?:sc|hc)-[a-z0-9][a-z0-9.\-]{8,}[a-z0-9]")
rows = []
for root, ds, fs in os.walk(AW):
    if "C13-A0-EVAL" in root or "__pycache__" in root: continue
    for f in fs:
        p = os.path.join(root, f)
        if not f.endswith((".csv", ".json", ".jsonl", ".txt", ".md", ".py")): continue
        if os.path.getsize(p) > 60_000_000: continue
        t = open(p, encoding="utf-8", errors="replace").read()
        ks = {tok2k[m] for m in TOK.findall(t) if m in tok2k}
        hk = ks & set(hold)
        if ks:
            rows.append((os.path.relpath(p, AW), len(ks), len(hk)))
rows.sort(key=lambda r: (r[1]))
with open(sys.argv[2], "w") as o:
    for r in rows: o.write(f"{r[1]}\t{r[2]}\t{r[0]}\n")
print(len(rows))
