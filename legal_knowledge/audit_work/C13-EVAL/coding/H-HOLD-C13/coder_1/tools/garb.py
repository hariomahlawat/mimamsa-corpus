import sys,re
sys.path.insert(0,'.')
from view import pages
for i in range(113):
    P=pages(i); bad=[]
    for n,t in P:
        if not t: bad.append((n,0)); continue
        words=re.findall(r"[A-Za-z]{3,}",t)
        ratio=sum(len(w) for w in words)/max(1,len(t))
        if ratio<0.6 or len(t)<200: bad.append((n,round(ratio,2)))
    if bad: print(i,len(P),bad)
