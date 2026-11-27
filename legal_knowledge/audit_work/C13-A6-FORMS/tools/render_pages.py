"""Render page images of hash-verified official copies for visual transcription (C13 A6).

Usage:
  python -I render_pages.py SOURCE_KEY PAGES [--dpi N] [--clip x0,y0,x1,y1] [--out DIR]
PAGES is 1-based, e.g. 73 or 59-65. --clip is in fractions of the page (0..1).
The source bytes are read through a6_common.read_source (sha256 verified before use).
Renders are scratch files; they are not part of the deliverable. Every render
is reproducible from (copy sha256, page, clip, renderer version, dpi), which
the transcription records carry.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a6_common as C  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("pages")
    ap.add_argument("--dpi", type=int, default=150)
    ap.add_argument("--clip", default="")
    ap.add_argument("--out", default=os.environ.get("A6_RENDER_DIR", "a6_render"))
    a = ap.parse_args()
    import pymupdf
    doc = C.open_pdf(a.source)
    lo, _, hi = a.pages.partition("-")
    hi = hi or lo
    os.makedirs(a.out, exist_ok=True)
    for p in range(int(lo), int(hi) + 1):
        page = doc[p - 1]
        r = page.rect
        clip = None
        tag = ""
        if a.clip:
            x0, y0, x1, y1 = (float(v) for v in a.clip.split(","))
            clip = pymupdf.Rect(r.x0 + x0 * r.width, r.y0 + y0 * r.height, r.x0 + x1 * r.width, r.y0 + y1 * r.height)
            tag = "_" + a.clip.replace(",", "-")
        pix = page.get_pixmap(dpi=a.dpi, clip=clip, colorspace=pymupdf.csGRAY)
        fn = os.path.join(a.out, f"{a.source}_p{p:03d}_{a.dpi}{tag}.png")
        pix.save(fn)
        print(fn, pix.width, pix.height, "pymupdf", pymupdf.VersionBind)


if __name__ == "__main__":
    main()
