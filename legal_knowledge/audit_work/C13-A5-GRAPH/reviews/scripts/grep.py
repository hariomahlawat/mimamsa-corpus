import sys,re,pymupdf
d=pymupdf.open(sys.argv[1]); pat=sys.argv[2]; maxp=int(sys.argv[3]) if len(sys.argv)>3 else 999
for i,p in enumerate(d):
    if i>=maxp: break
    t=p.get_text()
    for m in re.finditer(pat,t):
        print(i+1, repr(t[max(0,m.start()-150):m.end()+150]))
