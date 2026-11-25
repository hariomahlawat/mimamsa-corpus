import csv,re,sys,os,fitz
W=sys.argv[1]
rows=list(csv.DictReader(open(os.path.join(W,'CODER_SHEET.csv'))))
orig=list(csv.DictReader(open(os.path.join(W,'scripts','CODER_SHEET.orig.csv'))))
idx={r['item_id']:i for i,r in enumerate(orig)}
norm=lambda s: re.sub(r"[^a-z0-9]","",re.sub(r"(?<=\s)[A-HcoO0-9]{1}(?=\s)"," "," "+s.lower().replace("-\n","")+" ")) if False else re.sub(r"[^a-z0-9]","",re.sub(r"\s[a-hA-H0]\s"," ",re.sub(r"\s[a-hA-H0]\s"," "," "+s+" ")).lower())
cache={}
bad=0
for r in rows:
    e=r['excerpt']
    if not e: continue
    i=idx[r['item_id']]; p=int(r['pages_to_code'])
    if i not in cache:
        d=fitz.open(os.path.join(W,'src',orig[i]['rep_sha256']+'.pdf'))
        t=''.join(d[k].get_text() for k in range(max(0,p-2),min(d.page_count,p+1)))
        cache[i]=norm(t)
    T=cache[i]
    for piece in [x.strip(' .;–-') for x in e.split('...')]:
        if len(piece)<8: continue
        if norm(piece) not in T:
            bad+=1; print(i,r['item_id'],'|',piece[:90]); break
print('bad',bad)
