#!/usr/bin/env python3
"""C8 Workstream B: re-hash held Gazette PDFs and render selected pages.

Offline only. Usage:
  python -I rehash_and_render.py --scratch <scratchpad> --manifest <held_binaries_manifest.csv>
         --plan <render_plan.csv> --out <renders_dir> --log <render_log.csv> [--dpi 150]

render_plan.csv columns: tranche_id,sha256,pdf_page,purpose
For each plan row the held file (held_path from the manifest, relative to --scratch)
is re-hashed; if the sha256 differs from the expected one the row is logged as
HASH_MISMATCH and NOT rendered. Otherwise the 1-based pdf_page is rendered with
pymupdf get_pixmap(dpi=<dpi>, colorspace=csGRAY, alpha=False) and written as PNG.
The PNG sha256 is logged. Full-page renders only; any crops are made by crop_png.py.
"""
import argparse, csv, hashlib, os, sys
import pymupdf


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scratch', required=True)
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--plan', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--log', required=True)
    ap.add_argument('--dpi', type=int, default=150)
    a = ap.parse_args()
    paths = {}
    for r in csv.DictReader(open(a.manifest, newline='')):
        paths.setdefault(r['rehashed_sha256'], []).append(r['held_path'])
    os.makedirs(a.out, exist_ok=True)
    hashed = {}
    rows = []
    for r in csv.DictReader(open(a.plan, newline='')):
        sha = r['sha256']
        held = paths.get(sha, [])
        if not held:
            rows.append(dict(r, held_path='', rehash='', hash_check='NOT_IN_MANIFEST', pdf_pages='', png='', png_sha256='', width='', height='', render_settings=''))
            continue
        hp = held[0]
        full = os.path.join(a.scratch, hp)
        if full not in hashed:
            hashed[full] = sha256_file(full)
        got = hashed[full]
        if got != sha:
            rows.append(dict(r, held_path=hp, rehash=got, hash_check='HASH_MISMATCH', pdf_pages='', png='', png_sha256='', width='', height='', render_settings=''))
            continue
        doc = pymupdf.open(full)
        pno = int(r['pdf_page'])
        page = doc[pno - 1]
        pix = page.get_pixmap(dpi=a.dpi, colorspace=pymupdf.csGRAY, alpha=False)
        name = f"{r['tranche_id']}_p{pno:02d}_{a.dpi}dpi_gray.png"
        outp = os.path.join(a.out, name)
        pix.save(outp)
        settings = (f"PyMuPDF {pymupdf.VersionBind} (MuPDF {pymupdf.VersionFitz}); page.get_pixmap(dpi={a.dpi}, "
                    f"colorspace=csGRAY, alpha=False); full page, no clip, no rotation override; PNG via Pixmap.save")
        rows.append(dict(r, held_path=hp, rehash=got, hash_check='MATCH', pdf_pages=len(doc), png=name,
                         png_sha256=sha256_file(outp), width=pix.width, height=pix.height, render_settings=settings))
        doc.close()
    fields = ['tranche_id', 'sha256', 'pdf_page', 'purpose', 'held_path', 'rehash', 'hash_check', 'pdf_pages',
              'png', 'png_sha256', 'width', 'height', 'render_settings']
    with open(a.log, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in fields})
    bad = [r for r in rows if r['hash_check'] != 'MATCH']
    print(f"rows={len(rows)} rendered={len(rows)-len(bad)} problems={len(bad)}")
    for r in bad:
        print('PROBLEM', r['tranche_id'], r['hash_check'])
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
