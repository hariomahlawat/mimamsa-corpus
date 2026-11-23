"""Re-hash held Supreme Court copies and render the pages a human reviewer must open (offline; read-only on inputs).

usage: python -I render_c9.py <scratchpad_root> <held_manifest_csv> <render_dir> <out_jsonl> <c8_render_facts_jsonl> [--check]
Page list is fixed in PAGES below (copy key -> sha256 -> pages). For every copy the held file is re-hashed first; on a
mismatch the copy is reported and not rendered. Each PNG is written to <render_dir> (never committed) and one JSON line
per page records sha256, held path, page, PNG name and sha256, size, render settings, and the C8 PNG sha256 for the same
page where C8 rendered it (reproduction check). Page text is never emitted (privacy: judgments carry personal data).
--check recomputes and compares with the existing <out_jsonl> (exit 1 on difference; PNGs are re-rendered)."""
import csv, hashlib, json, sys
from pathlib import Path
import pymupdf

DPI = 150
SETTINGS = f"PyMuPDF {pymupdf.VersionBind}; dpi={DPI}; colorspace=GRAY; alpha=False; annots=True; full page (MediaBox/CropBox default)"
PAGES = [  # (copy key, sha256, pages); 'last' = final page
    ("RANJIT", "ed7cf31fd8fbe50822e0a60f80b96ed1187dcd465dc4ae2649424c58001ff399", "1,3,4,last"),
    ("SNM", "eb4420801e978469e9c7407f8c079273f9cd483ad45a4427daa53e3d229969cc", "1,3,4,last"),
    ("NAVJOT", "3b75354869ffb928f73532f475f5f920e2f2a1f8817163caba2f7fb5e1eb215d", "1,2,last"),
    ("DHARAMVIR", "3056712cc7614399f72ee19f529f91990e70dba8a317dd3bd07e76e4ac546b75", "1,last"),
    ("RAJBIR_C1", "970b96807bcbf8a1255fe16c574b575f64fe2edee1cbb271485fa7661a62c666", "1,2,last"),
    ("RAJBIR_C2", "c6ec489dff7a107b630a8646190a8cda303a54e4e9f5463eaed748ae0a42a1dd", "1,18,19,21"),
    ("RAJBIR_C3", "6b495f1483657581965b808b18aa23c09b424989e41d43226c90d35845855cde", "1,last"),
    ("NSY", "3c50cdb7f30d1a84b488a72052bdf1868cea18ec4e02aee292cf1e97ebf5bbe6", "1,last"),
    ("GIRISH", "4f7ea3a451c6f9a11d7e4dd96822e68cd9cd7a01d8dc74cf46ad34e79029b86c", "1,3,last"),
    ("MULLIKOTE", "10e1954f2e39916ea0f0e8e759c3823581becf752dd6ad2e9058569a1fd97444", "1,4,31,32,35,last"),
    ("PPS_BEDI", "211dbaf4e20371cc476d09c158e41b976786d57f67336ff6fc802170178b3cca", "1,7,last"),
]


def main():
    argv = [a for a in sys.argv[1:] if a != "--check"]
    check = "--check" in sys.argv[1:]
    root, manifest, rdir, out, c8 = (Path(a) for a in argv[:5])
    rdir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for r in csv.DictReader(open(manifest, newline="", encoding="utf-8")):
        paths.setdefault(r["rehashed_sha256"], []).append(r["held_path"])
    c8h = {}
    for line in open(c8, encoding="utf-8"):
        o = json.loads(line)
        c8h[(o["sha256"], o["pdf_page"])] = o["png_sha256"]
    lines = []
    for key, sha, pages in PAGES:
        held, checked = None, []
        for hp in sorted(paths.get(sha, [])):
            got = hashlib.sha256((root / hp).read_bytes()).hexdigest()
            checked.append(f"{hp}={'MATCH' if got == sha else 'MISMATCH ' + got}")
            if got == sha and held is None:
                held = hp
        if not held:
            lines.append({"copy_key": key, "sha256": sha, "error": "NO_MATCHING_HELD_FILE", "rehash": checked})
            continue
        doc = pymupdf.open(root / held)
        n = doc.page_count
        for p in pages.split(","):
            pn = n if p == "last" else int(p)
            pix = doc[pn - 1].get_pixmap(dpi=DPI, colorspace=pymupdf.csGRAY, alpha=False)
            f = rdir / f"{sha[:8]}_p{pn:03d}.png"
            pix.save(f)
            ph = hashlib.sha256(f.read_bytes()).hexdigest()
            prev = c8h.get((sha, pn), "")
            lines.append({"copy_key": key, "sha256": sha, "held_path": held, "rehash": checked, "page_count": n, "pdf_page": pn,
                          "png": f.name, "png_sha256": ph, "width": pix.width, "height": pix.height, "render_settings": SETTINGS,
                          "c8_png_sha256": prev, "c8_reproduced": ("YES" if prev == ph else "NO") if prev else "NOT_RENDERED_IN_C8"})
    text = "".join(json.dumps(x, sort_keys=True) + "\n" for x in lines)
    if check:
        ok = out.is_file() and out.read_text(encoding="utf-8") == text
        print("CHECK", "OK" if ok else "DIFFERS")
        sys.exit(0 if ok else 1)
    out.write_text(text, encoding="utf-8")
    print(f"{len(lines)} rows; rehash mismatches: {sum('MISMATCH' in ' '.join(x.get('rehash', [])) for x in lines)}; "
          f"C8 reproduced: {sum(x.get('c8_reproduced') == 'YES' for x in lines)}; differs: {sum(x.get('c8_reproduced') == 'NO' for x in lines)}")


if __name__ == "__main__":
    main()
