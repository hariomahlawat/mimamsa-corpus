import sys, fitz
W,sha,page=sys.argv[1],sys.argv[2],int(sys.argv[3])
clip=None
if len(sys.argv)>4:
    y0,y1=float(sys.argv[4]),float(sys.argv[5])
d=fitz.open(f'{W}/src/{sha}.pdf'); p=d[page-1]
r=p.rect
if len(sys.argv)>4: clip=fitz.Rect(r.x0, r.y0+r.height*y0, r.x1, r.y0+r.height*y1)
pix=p.get_pixmap(dpi=110 if clip is None else 160, clip=clip)
out=f'{W}/img/{sha[:12]}_p{page}.png'; pix.save(out); print(out)
