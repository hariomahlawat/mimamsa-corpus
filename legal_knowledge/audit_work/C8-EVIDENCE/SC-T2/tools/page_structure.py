"""Per-page text-layer structure facts for held judgment PDFs (offline, read-only).

usage: python page_structure.py <scratchpad_root> <held_manifest_csv> <out_json> <sha256> [<sha256> ...]
For each file (re-hashed first): page count, printed page markers per page ('Page X of N', 'Page X', bare footer number),
JUDIS header presence per page, positions of database-block labels (CITATION, CITATOR INFO, ACT, HEADNOTE, JUDGMENT:),
reported-report page numbers inline (bare 3-digit lines in JUDIS text), signature widgets, PDF metadata.
Text-layer facts only; they are not readings of the page image."""
import csv, hashlib, json, re, sys
from pathlib import Path
import pymupdf

LABELS = ["PETITIONER:", "RESPONDENT:", "DATE OF JUDGMENT", "BENCH:", "CITATION:", "CITATOR INFO", "ACT:", "HEADNOTE:",
          "JUDGMENT:", "CASE NO.:", "REPORTABLE", "CORRECTED", "INSC", "Signature Not Verified", "Digitally signed by",
          "RECORD OF PROCEEDINGS", "Court Master", "http://JUDIS.NIC.IN", "SCC", "AIR", "SCR"]


def main():
    root, manifest, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    paths = {}
    for r in csv.DictReader(open(manifest, newline="", encoding="utf-8")):
        paths.setdefault(r["rehashed_sha256"], []).append(r["held_path"])
    res = {}
    for sha in sys.argv[4:]:
        hp = next((p for p in paths.get(sha, []) if hashlib.sha256((root / p).read_bytes()).hexdigest() == sha), None)
        if not hp:
            res[sha] = {"error": "NO_MATCHING_HELD_FILE"}
            continue
        doc = pymupdf.open(root / hp)
        pages = []
        for i, pg in enumerate(doc, 1):
            t = pg.get_text()
            lines = [l.strip() for l in t.splitlines() if l.strip()]
            pof = re.findall(r"Page\s+(\d+)\s+of\s+(\d+)", t)
            pn = re.findall(r"^Page\s+(\d+)\s*$", t, re.M)
            widgets = [w.field_type_string for w in (pg.widgets() or [])]
            pages.append({"pdf_page": i, "chars": len(t), "page_x_of_n": pof, "page_x": pn,
                          "first_line": lines[0] if lines else "", "last_line": lines[-1] if lines else "",
                          "labels": {l: t.count(l) for l in LABELS if l in t}, "widgets": widgets,
                          "annots": [a.type[1] for a in pg.annots()] if pg.annots() else []})
        res[sha] = {"held_path": hp, "page_count": doc.page_count, "metadata": doc.metadata, "pages": pages}
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
