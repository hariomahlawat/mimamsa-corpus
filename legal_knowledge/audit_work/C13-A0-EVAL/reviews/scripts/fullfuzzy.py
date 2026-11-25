"""Reviewer: frame-wide identity-duplicate search (MinHash LSH) across distinct judgment_keys."""
import csv, sys, os, re, subprocess, hashlib, random
from collections import defaultdict
SRC, ADD, OUTP = sys.argv[1:4]
A0 = f"{SRC}/legal_knowledge/audit_work/C13-A0-EVAL/outputs"
R = lambda p: list(csv.DictReader(open(p, encoding="utf-8", newline="")))
recs = R(f"{A0}/frame/FRAME_RECORDS.csv")
p = subprocess.Popen(["git", "-C", "/home/user/c7", "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
def blob(path):
    p.stdin.write(f"ad77758d:{path}\n".encode()); p.stdin.flush()
    h = p.stdout.readline().decode()
    if h.endswith("missing\n"): return None
    n = int(h.split()[2]); d = p.stdout.read(n); p.stdout.read(1); return d
def text(doc):
    b = blob(f"data/text/{doc}.txt")
    if b is None:
        f = os.path.join(ADD, "text", doc + ".txt"); b = open(f, "rb").read() if os.path.exists(f) else b""
    return b.decode("utf-8", "replace")
K = 64; rng = random.Random(1); A = [rng.randrange(1, 2**61 - 1) for _ in range(K)]; B = [rng.randrange(0, 2**61 - 1) for _ in range(K)]
M = 2**61 - 1
sig, size = {}, {}
for r in recs:
    w = re.findall(r"[a-z]{3,}", re.sub(r"\[\[page \d+\]\]", " ", text(r["doc_id"]).lower()))
    sh = {int.from_bytes(hashlib.md5(" ".join(w[i:i+8]).encode()).digest()[:8], "big") for i in range(max(0, len(w) - 8))}
    if len(sh) < 30: continue
    sig[(r["judgment_key"], r["doc_id"], r["issue_date"])] = [min((a * x + b) % M for x in sh) for a, b in zip(A, B)]
    size[r["doc_id"]] = len(sh)
buckets = defaultdict(set)
for k, s in sig.items():
    for band in range(16):
        buckets[(band, tuple(s[band*4:band*4+4]))].add(k)
pairs = set()
for v in buckets.values():
    v = sorted(v)
    for i in range(len(v)):
        for j in range(i + 1, len(v)):
            if v[i][0] != v[j][0]: pairs.add((v[i], v[j]))
out = []
for a, b in pairs:
    est = sum(x == y for x, y in zip(sig[a], sig[b])) / K
    if est >= 0.8: out.append(dict(key_a=a[0], doc_a=a[1], date_a=a[2], key_b=b[0], doc_b=b[1], date_b=b[2], jaccard_est=est, same_date=a[2] == b[2]))
out.sort(key=lambda r: -r["jaccard_est"])
with open(OUTP, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["key_a", "doc_a", "date_a", "key_b", "doc_b", "date_b", "jaccard_est", "same_date"]); w.writeheader(); [w.writerow(r) for r in out]
print("texts", len(sig), "pairs>=0.8", len(out), ">=0.95", sum(r["jaccard_est"] >= 0.95 for r in out))
