import sys,fitz
W,sha,pg,out=sys.argv[1],sys.argv[2],int(sys.argv[3]),sys.argv[4]
d=fitz.open(f"{W}/src/{sha}.pdf"); d[pg-1].get_pixmap(dpi=int(sys.argv[5]) if len(sys.argv)>5 else 80).save(out)
