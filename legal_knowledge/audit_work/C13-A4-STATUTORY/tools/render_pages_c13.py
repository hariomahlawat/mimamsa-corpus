#!/usr/bin/env python3
"""Render held-copy pages for C13 A4 image checks and verify recorded render hashes.

Usage:
  render_pages_c13.py COPY_ID PDF_PAGE[,PDF_PAGE...] --out DIR   # render PNGs for an image check
  render_pages_c13.py --verify                                   # re-render every inputs/page_evidence_c13.csv row

Render contract (identical to C12 render_pages_c12.py): PyMuPDF Page.get_pixmap(dpi=110, colorspace=RGB,
alpha=False), whole page; sha256 of Pixmap.tobytes("png"). The copy is resolved through the C13 held base
(HF preservation copy where available) and its sha256 is checked against the C5 copy register first.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from c13a4_common import C5_COPY, HELD_BASE, PKG, prepare_held_base, read_csv, require_env, sha256_bytes, sha256_file


def held_path(copy_id):
    prepare_held_base()
    for c in read_csv(C5_COPY):
        if c["copy_id"] == copy_id:
            p = HELD_BASE / c["held_paths"].split(";")[0]
            if p.exists() and sha256_file(p) == c["sha256"]:
                return p, c["sha256"]
    raise SystemExit(f"{copy_id}: not held with the registered sha256")


def render(copy_id, pages, dpi=110, out: Path | None = None):
    import pymupdf
    p, sha = held_path(copy_id)
    res = []
    with pymupdf.open(str(p)) as d:
        for n in pages:
            png = d[n - 1].get_pixmap(dpi=dpi, colorspace=pymupdf.csRGB, alpha=False).tobytes("png")
            if out:
                out.mkdir(parents=True, exist_ok=True)
                (out / f"{copy_id.replace('~', '_')}_p{n}_{dpi}.png").write_bytes(png)
            res.append((n, sha256_bytes(png)))
    return sha, res


def verify():
    rows = read_csv(PKG / "inputs/page_evidence_c13.csv")
    bad = []
    for e in rows:
        sha, [(n, h)] = render(e["copy_id"], [int(e["pdf_page"])], int(e["render_dpi"]))
        if sha != e["sha256"] or h != e["render_png_sha256"]:
            bad.append(e["evidence_id"])
    print(f"{len(rows) - len(bad)}/{len(rows)} C13 page renders reproduce" + (f"; DRIFT: {bad}" if bad else ""))
    return 1 if bad else 0


def main(argv=None):
    require_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("copy_id", nargs="?")
    ap.add_argument("pages", nargs="?")
    ap.add_argument("--dpi", type=int, default=110)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args(argv)
    if a.verify:
        return verify()
    sha, res = render(a.copy_id, [int(x) for x in a.pages.split(",")], a.dpi, a.out)
    for n, h in res:
        print(a.copy_id, sha[:12], n, h)
    return 0


if __name__ == "__main__":
    sys.exit(main())
