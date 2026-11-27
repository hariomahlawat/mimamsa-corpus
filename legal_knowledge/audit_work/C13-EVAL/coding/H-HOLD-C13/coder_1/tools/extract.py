import csv, os, sys, fitz
W = sys.argv[1]
rows = list(csv.DictReader(open(os.path.join(W, "CODER_SHEET.csv"))))
for i,r in enumerate(rows):
    sha=r["rep_sha256"]; src=os.path.join(W,"src",sha+".pdf")
    try:
        d=fitz.open(src)
    except Exception as e:
        print(i,r["item_id"],"OPENFAIL",e); continue
    out=[]; tot=0
    for n,pg in enumerate(d,1):
        t=pg.get_text(); tot+=len(t.strip())
        out.append("\n=== PAGE %d ===\n%s"%(n,t))
    open(os.path.join(W,"txt","%03d_%s.txt"%(i,r["item_id"])),"w").write("".join(out))
    print(i,r["item_id"],d.page_count,tot,round(tot/max(1,d.page_count)))
