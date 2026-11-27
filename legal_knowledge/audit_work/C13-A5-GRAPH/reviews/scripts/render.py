import sys, pymupdf
pdf, page, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
dpi = int(sys.argv[4]) if len(sys.argv)>4 else 120
d = pymupdf.open(pdf); p = d[page-1]
clip=None
if len(sys.argv)>5:
    y0,y1=[float(x) for x in sys.argv[5].split(',')]
    r=p.rect; clip=pymupdf.Rect(r.x0, r.y0+r.height*y0, r.x1, r.y0+r.height*y1)
p.get_pixmap(dpi=dpi, clip=clip).save(out)
print(len(d), p.rect)
