import pymupdf,sys,os
src,page,out=sys.argv[1],int(sys.argv[2]),sys.argv[3]
d=pymupdf.open(src); p=d[page-1]; p.get_pixmap(dpi=int(sys.argv[4]) if len(sys.argv)>4 else 80).save(out)
