#!/usr/bin/env python3
"""Render held-copy pages for C12 WS-F image checks (reproducible render hashes; review finding F-08).

Usage:
  render_pages_c12.py COPY_ID PDF_PAGE[,PDF_PAGE...] [--dpi 110] [--out DIR]
  render_pages_c12.py --verify            # re-render every page_evidence_c12.csv row that records a
                                          # render_script of this file and compare the PNG sha256

The copy is resolved through the C5 source_copy_register held_paths (relative to C12F_HELD_BASE, default the
parent of the repository) and hash-verified before rendering; nothing is written next to the held copy.

Render parameters (fixed; part of the reproducibility contract):
  pymupdf Page.get_pixmap(dpi=DPI, colorspace=RGB, alpha=False), whole page, no clip, no rotation;
  PNG bytes from Pixmap.tobytes("png"). The sha256 is of those PNG bytes.
PNG bytes are deterministic for a given PyMuPDF/MuPDF version (recorded in the output); a different
MuPDF build may produce different bytes for the same page, so the version is recorded with each hash.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_c12f as b  # noqa: E402

SCRIPT_ID = "tools/render_pages_c12.py"


def render(copy_id: str, pages, dpi: int = 110, out: Path | None = None):
    import pymupdf  # noqa: PLC0415

    held = b.HeldCopies(b.read_csv(b.INPUTS["c5_copy"]))
    p = held.path(copy_id)
    if p is None:
        raise SystemExit(f"{copy_id}: not held at any registered path with the registered sha256")
    res = []
    with pymupdf.open(str(p)) as d:
        for n in pages:
            pix = d[n - 1].get_pixmap(dpi=dpi, colorspace=pymupdf.csRGB, alpha=False)
            png = pix.tobytes("png")
            h = hashlib.sha256(png).hexdigest()
            if out:
                out.mkdir(parents=True, exist_ok=True)
                (out / f"{copy_id.replace('~', '_')}_p{n}_{dpi}.png").write_bytes(png)
            res.append({"copy_id": copy_id, "copy_sha256": held.rows[copy_id]["sha256"], "pdf_page": n, "dpi": dpi,
                        "png_sha256": h, "width": pix.width, "height": pix.height, "pymupdf": pymupdf.VersionBind})
    return res


def verify():
    rows = b.read_csv(b.INPUTS["page_evidence"])
    bad = 0
    n = 0
    for e in rows:
        if e.get("render_script") != SCRIPT_ID:
            continue
        n += 1
        got = render(e["copy_id"], [int(e["pdf_page"])], int(e["render_dpi"]))[0]["png_sha256"]
        if got != e["render_png_sha256"]:
            bad += 1
            print(f"MISMATCH {e['evidence_id']}: {got} != {e['render_png_sha256']}")
    print(f"render verify: {n - bad}/{n} rows reproduce")
    return 1 if bad else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("copy_id", nargs="?")
    ap.add_argument("pages", nargs="?")
    ap.add_argument("--dpi", type=int, default=110)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args(argv)
    if a.verify:
        return verify()
    if not (a.copy_id and a.pages):
        ap.error("COPY_ID and PDF_PAGE list required (or --verify)")
    w = csv.DictWriter(sys.stdout, fieldnames=["copy_id", "copy_sha256", "pdf_page", "dpi", "png_sha256", "width", "height", "pymupdf"],
                       lineterminator="\n")
    w.writeheader()
    for r in render(a.copy_id, [int(x) for x in a.pages.split(",")], a.dpi, a.out):
        w.writerow(r)
    return 0


if __name__ == "__main__":
    sys.exit(main())
