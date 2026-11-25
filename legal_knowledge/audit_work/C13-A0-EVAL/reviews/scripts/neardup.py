"""Reviewer: near-duplicate judgments across distinct judgment_keys (text shingles), focusing on holdout vs spent."""
import csv, sys, os, re, subprocess, hashlib, json
from collections import defaultdict
SRC, ADD, OUTP = sys.argv[1], sys.argv[2], sys.argv[3]
A0 = f"{SRC}/legal_knowledge/audit_work/C13-A0-EVAL/outputs"
R = lambda p: list(csv.DictReader(open(p, encoding="utf-8", newline="")))
recs = R(f"{A0}/frame/FRAME_RECORDS.csv")
excl = {r["judgment_key"] for r in R(f"{A0}/exclusions/EXCLUDED_JUDGMENTS.csv")}
hold = defaultdict(set)
for h in ("H-OUT-C13", "H-HOLD-C13", "H-REL-C13"):
    for r in R(f"{A0}/holdouts/{h}/SAMPLE.csv"): hold[r["judgment_key"]].add(h)
for r in R(f"{A0}/holdouts/H-HOLD-C13/RESERVE.csv"): hold[r["judgment_key"]].add("RESERVE")
p = subprocess.Popen(["git", "-C", "/home/user/c7", "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
def blob(path):
    p.stdin.write(f"ad77758d:{path}\n".encode()); p.stdin.flush()
    h = p.stdout.readline().decode()
    if h.endswith("missing\n"): return None
    n = int(h.split()[2]); d = p.stdout.read(n); p.stdout.read(1); return d
def text(doc):
    b = blob(f"data/text/{doc}.txt")
    if b is None:
        f = os.path.join(ADD, "text", doc + ".txt")
        b = open(f, "rb").read() if os.path.exists(f) else b""
    return b.decode("utf-8", "replace")
def shingles(t):
    w = re.sub(r"\[\[page \d+\]\]", " ", t.lower())
    w = re.findall(r"[a-z]{3,}", w)
    return {hashlib.md5(" ".join(w[i:i+8]).encode()).digest()[:8] for i in range(0, max(0, len(w) - 8), 1)}
sh = {}
for r in recs:
    k = r["judgment_key"]
    if k in hold or k in excl:
        s = shingles(text(r["doc_id"]))
        sh[(k, r["doc_id"])] = s
idx = defaultdict(set)
for key, s in sh.items():
    if key[0] in excl:
        for x in s: idx[x].add(key)
res = []
for key, s in sh.items():
    if key[0] not in hold or not s: continue
    cnt = defaultdict(int)
    for x in s:
        for o in idx.get(x, ()):
            if o[0] != key[0]: cnt[o] += 1
    for o, c in cnt.items():
        cont = c / min(len(s), len(sh[o]) or 1)
        if cont >= 0.5:
            res.append(dict(holdout_key=key[0], holdout_doc=key[1], holdouts=";".join(sorted(hold[key[0]])), spent_key=o[0], spent_doc=o[1], containment=round(cont, 3), shared=c, n_h=len(s), n_s=len(sh[o])))
res.sort(key=lambda r: -r["containment"])
with open(OUTP, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(res[0].keys()) if res else ["none"]); w.writeheader(); [w.writerow(r) for r in res]
print("texts", len(sh), "pairs>=0.5", len(res))
for r in res[:30]: print(r)
