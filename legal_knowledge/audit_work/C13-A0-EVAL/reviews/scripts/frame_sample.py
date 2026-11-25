import csv, json, random, re, subprocess, sys, os, hashlib
SRC, ADD, OUTD = sys.argv[1:4]
A0 = f"{SRC}/legal_knowledge/audit_work/C13-A0-EVAL/outputs"
recs = list(csv.DictReader(open(f"{A0}/frame/FRAME_RECORDS.csv", encoding="utf-8")))
rng = random.Random("reviewer-a0-frame-sample")
pick = []
pick += rng.sample(recs, 22)
pick += rng.sample([r for r in recs if r["text_quality"] != "USABLE"], 6)
pick += rng.sample([r for r in recs if r["stratum"] == "PARTY_SPECIFIC"], 6)
pick += rng.sample([r for r in recs if r["stratum"] == "BATCH_OR_MULTI"], 6)
seen=set(); P=[]
for r in pick:
    if r["doc_id"] not in seen: seen.add(r["doc_id"]); P.append(r)
p = subprocess.Popen(["git", "-C", "/home/user/c7", "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
def blob(path):
    p.stdin.write(f"ad77758d:{path}\n".encode()); p.stdin.flush()
    h = p.stdout.readline().decode()
    if h.endswith("missing\n"): return None
    n = int(h.split()[2]); d = p.stdout.read(n); p.stdout.read(1); return d
os.makedirs(OUTD, exist_ok=True)
rows = []
for i, r in enumerate(P):
    d = r["doc_id"]
    mb = blob(f"data/meta/{d}.json") or (open(f"{ADD}/meta/{d}.json","rb").read() if os.path.exists(f"{ADD}/meta/{d}.json") else b"{}")
    meta = json.loads(mb)
    tb = blob(meta.get("text_path") or f"data/text/{d}.txt")
    if tb is None and os.path.exists(f"{ADD}/text/{d}.txt"): tb = open(f"{ADD}/text/{d}.txt","rb").read()
    t = (tb or b"").decode("utf-8", "replace")
    pages = re.split(r"\[\[page \d+\]\]", t); pages = [x for x in pages if x.strip()]
    good = 0; L = NS = 0
    for pg in pages:
        l = sum(c.isalpha() for c in pg); ns = sum(not c.isspace() for c in pg); L += l; NS += ns
        if l >= 200 and ns and l / ns >= 0.5: good += 1
    # independent court guess from text head
    head = t[:3000].upper()
    court_txt = ("SC" if "SUPREME COURT" in head and "HIGH COURT" not in head[:600] else "DEL" if "DELHI" in head else
                 "PH" if "PUNJAB" in head or "CHANDIGARH" in head else "JK" if "JAMMU" in head or "KASHMIR" in head or "LADAKH" in head else
                 "ALL" if "ALLAHABAD" in head or "LUCKNOW" in head else "?")
    rows.append(dict(i=i+1, doc_id=d, frame_court=r["court"], meta_court=meta.get("court"), text_court_guess=court_txt,
        frame_tq=r["text_quality"], tq_basis=r["text_quality_basis"], my_pages=len(pages), my_usable=good, my_letters=L,
        my_share=round(L / NS, 3) if NS else 0, text_method=meta.get("text_method"), frame_stratum=r["stratum"],
        meta_case_numbers=";".join(meta.get("case_numbers") or []), records_for_file=r["meta_records_for_file"],
        connected=r["connected_matter_cues"], party_cues=r["party_specific_cues"], judgment_key=r["judgment_key"]))
    with open(f"{OUTD}/{i+1:02d}_{d[:60]}.txt", "w") as f:
        f.write(json.dumps(rows[-1], indent=1) + "\n=== HEAD ===\n" + t[:1800] + "\n=== TAIL ===\n" + t[-2500:])
with open(f"{OUTD}/SAMPLE.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); [w.writerow(x) for x in rows]
print(len(rows))
for x in rows: print(x["i"], x["frame_court"], x["meta_court"][:25] if x["meta_court"] else None, x["text_court_guess"], x["frame_tq"], x["my_pages"], x["my_usable"], x["my_share"], x["text_method"], x["frame_stratum"], x["records_for_file"], len(x["meta_case_numbers"].split(";")) if x["meta_case_numbers"] else 0, x["connected"], x["party_cues"])
