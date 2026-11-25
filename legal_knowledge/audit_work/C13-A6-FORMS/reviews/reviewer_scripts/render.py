# Independent renderer: reads HF-downloaded bytes (sha verified separately), renders gray PNG halves.
import sys, pymupdf, os
src, pages, dpi, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
doc = pymupdf.open(os.path.join("hf_src", src + ".pdf"))
os.makedirs(out, exist_ok=True)
for p in [int(x) for x in pages.split(",")]:
    pg = doc[p-1]; r = pg.rect
    for tag, (a, b) in {"top": (0, 0.55), "bot": (0.45, 1.0)}.items():
        clip = pymupdf.Rect(r.x0, r.y0 + a*r.height, r.x1, r.y0 + b*r.height)
        pix = pg.get_pixmap(dpi=dpi, clip=clip, colorspace=pymupdf.csGRAY)
        fn = f"{out}/{src}_p{p:03d}_{tag}.png"; pix.save(fn); print(fn, pix.width, pix.height)
