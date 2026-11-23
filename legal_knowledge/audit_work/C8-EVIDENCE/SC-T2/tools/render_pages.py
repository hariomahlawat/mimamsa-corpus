"""Render selected PDF pages at a fixed resolution in grayscale and record hashes (offline; read-only on inputs).

usage: python render_pages.py <scratchpad_root> <held_manifest_csv> <out_dir> <sha256>:<pages>[,<pages>...] ...
  <pages> is a comma list of 1-based page numbers or 'last'.
Re-hashes each held file before use; a mismatch is reported and the file is not rendered.
Writes <out_dir>/<sha8>_p<NNN>.png and prints one JSON line per page: render facts plus the sha256 and length of the page text
layer. The text layer itself is not emitted: page text can carry personal data and is not committed (C8 review B-03)."""
import csv, hashlib, json, sys
from pathlib import Path
import pymupdf

DPI = 150
SETTINGS = f"PyMuPDF {pymupdf.VersionBind}; dpi={DPI}; colorspace=GRAY; alpha=False; annots=True; full page (MediaBox/CropBox default)"


def main():
    root, manifest, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    paths = {}
    for r in csv.DictReader(open(manifest, newline="", encoding="utf-8")):
        paths.setdefault(r["rehashed_sha256"], []).append(r["held_path"])
    for spec in sys.argv[4:]:
        sha, _, pages = spec.partition(":")
        held = None
        for hp in paths.get(sha, []):
            data = (root / hp).read_bytes()
            got = hashlib.sha256(data).hexdigest()
            if got == sha:
                held = hp
                break
            print(json.dumps({"sha256": sha, "held_path": hp, "error": f"HASH_MISMATCH got {got}"}))
        if not held:
            print(json.dumps({"sha256": sha, "error": "NO_MATCHING_HELD_FILE"}))
            continue
        doc = pymupdf.open(root / held)
        n = doc.page_count
        for p in pages.split(","):
            pn = n if p == "last" else int(p)
            pg = doc[pn - 1]
            pix = pg.get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY, alpha=False)
            f = out / f"{sha[:8]}_p{pn:03d}.png"
            pix.save(f)
            print(json.dumps({"sha256": sha, "held_path": held, "page_count": n, "pdf_page": pn, "png": f.name,
                              "png_sha256": hashlib.sha256(f.read_bytes()).hexdigest(), "width": pix.width, "height": pix.height,
                              "render_settings": SETTINGS, "text_layer_sha256": hashlib.sha256(pg.get_text().encode("utf-8")).hexdigest(),
                              "text_layer_chars": len(pg.get_text())}))


if __name__ == "__main__":
    main()
