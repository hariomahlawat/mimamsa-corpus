import csv,sys,re,os
W=sys.argv[1]; a,b=int(sys.argv[2]),int(sys.argv[3]); H=int(sys.argv[4]) if len(sys.argv)>4 else 1400; T=int(sys.argv[5]) if len(sys.argv)>5 else 2000
rows=list(csv.DictReader(open(os.path.join(W,'tools','CODER_SHEET.orig.csv'))))
for i in range(a,min(b,len(rows))):
    r=rows[i]; t=open(os.path.join(W,'tools','txt',r['rep_sha256']+'.txt')).read()
    t=re.sub(r'[ \t]+',' ',t); t=re.sub(r'\n\s*\n+','\n',t)
    print(f"\n######## [{i}] {r['item_id']} {r['rep_raw_path'].split('/')[2]} len={len(t)}")
    if len(t)<=H+T+200: print(t)
    else: print(t[:H]); print(' ..... '); print(t[-T:])
