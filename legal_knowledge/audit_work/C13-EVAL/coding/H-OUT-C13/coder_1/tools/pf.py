import sys,re,os,csv
T=os.path.dirname(os.path.abspath(__file__))
m={r['item_id']:r['rep_sha256'] for r in csv.DictReader(open(os.path.join(T,'CODER_SHEET.orig.csv')))}
iid=sys.argv[1]; pats=sys.argv[2:]
txt=open(os.path.join(T,'txt',m[iid]+'.txt')).read()
pages=re.split(r'\n=====PAGE \d+=====\n',txt)[1:]
for p in pats:
    hits=[i+1 for i,pg in enumerate(pages) if re.sub(r'\s+',' ',p).lower() in re.sub(r'\s+',' ',pg).lower()]
    print(iid,repr(p[:40]),hits,'of',len(pages))
