import csv, json, sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
W="/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c13/coding/H-HOLD-C13/coder_1"
from view import pages
rows=list(csv.DictReader(open(os.path.join(W,"tools","orig.csv"))))
cols=list(rows[0].keys())
codes={}
for line in open(os.path.join(W,"tools","codes.jsonl")):
    line=line.strip()
    if not line: continue
    d=json.loads(line); codes.setdefault(d["i"],[]).append(d)
norm=lambda s: re.sub(r"\s+"," ",s).strip()
bad=0
out=[]
for i,r in enumerate(rows):
    if i not in codes:
        out.append(dict(r,coder_id="coder_1")); continue
    P=dict(pages(i))
    for d in codes[i]:
        nr=dict(r); nr["coder_id"]="coder_1"
        for k in ["item_type","opinion","judge","page","para","excerpt","legal_issue","certainty","notes"]:
            nr[k]=str(d.get(k,"")) if d.get(k) is not None else ""
        if nr["excerpt"] and not d.get("img"):
            pg=int(nr["page"])
            ok=norm(nr["excerpt"]) in P.get(pg,"")
            if not ok:
                bad+=1; print("NOT FOUND", i, r["item_id"], pg, nr["excerpt"][:80])
        out.append(nr)
with open(os.path.join(W,"CODER_SHEET.csv"),"w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=["coder_id"]+cols); w.writeheader(); w.writerows(out)
print("items coded",len(codes),"rows",len(out),"bad",bad)
