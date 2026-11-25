import sys; sys.path.insert(0,'.')
from view import pages
i=int(sys.argv[1]); s=sys.argv[2]
for n,t in pages(i):
    k=t.find(s)
    if k>=0: print(n, repr(t[max(0,k-50):k+len(s)+250]))
