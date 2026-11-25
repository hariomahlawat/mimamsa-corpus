import csv, os, sys, fitz, re
W=sys.argv[1]
rows=list(csv.DictReader(open(os.path.join(W,'CODER_SHEET.csv'))))
os.makedirs(os.path.join(W,'full'),exist_ok=True)
for i,r in enumerate(rows):
    d=fitz.open(os.path.join(W,'src',r['rep_sha256']+'.pdf'))
    txt=''.join(f"\n=====PAGE {k+1}=====\n"+d[k].get_text() for k in range(d.page_count))
    open(os.path.join(W,'full',f"{i:03d}.txt"),'w').write(txt)
    low=txt.lower()
    kw=sum(low.count(k) for k in ['army','armed forces','court martial','court-martial','air force','navy','military','naval','soldier'])
    first=re.sub(r'\s+',' ',d[0].get_text())[:160]
    print(f"{i:03d} kw={kw:4d} | {first}")
