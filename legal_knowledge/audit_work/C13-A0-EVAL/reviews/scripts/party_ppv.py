import csv, json, random, re, subprocess, sys
sys.path.insert(0, sys.argv[1]); import c13_features as F
A0 = sys.argv[2]
js = [r for r in csv.DictReader(open(f"{A0}/frame/FRAME_JUDGMENTS.csv")) if r["party_specific"] == "CANDIDATE"]
rng = random.Random("reviewer-party"); smp = rng.sample(js, min(25, len(js)))
p = subprocess.Popen(["git", "-C", "/home/user/c7", "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
def blob(path):
    p.stdin.write(f"ad77758d:{path}\n".encode()); p.stdin.flush()
    h = p.stdout.readline().decode()
    if h.endswith("missing\n"): return None
    n = int(h.split()[2]); d = p.stdout.read(n); p.stdout.read(1); return d
print("candidates", len(js))
for r in smp:
    t = (blob(f"data/text/{r['rep_doc_id']}.txt") or b"").decode("utf-8", "replace")
    tail = t[-max(int(len(t) * 0.35), 6000):]
    ms = [m for m in F.PARTY_RE.finditer(tail)]
    print("=====", r["judgment_key"], r["court"], r["stratum"], r["rep_doc_id"][:60])
    for m in ms[:2]:
        print("  CUE:", re.sub(r"\s+", " ", tail[max(0, m.start() - 150): m.end() + 150]))
    print("  END:", re.sub(r"\s+", " ", t[-600:]))
