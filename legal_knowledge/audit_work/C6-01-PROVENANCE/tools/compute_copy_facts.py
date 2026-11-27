"""C6-01 local fact capture (run where the held binaries are available; read-only on them; no network).

For every held copy in the C6-01 scope (sources whose Cycle 5 holding_state is *_PROVENANCE_UNDOCUMENTED):
- inputs/held_copy_facts.csv: sha256 (re-hashed at EVERY held path; any mismatch stops the run), md5, sha1, bytes,
  page count and the first ~400 characters of page-1 text (whitespace normalised). The p.1 text is a text-layer
  identity aid only; it is not an image check. A text-extraction failure stops the run (Fable review F-21).
- inputs/copy_structure_c6.csv: structural facts used by the class rule for born-digital copies (Fable review F-04/F-12):
  producer, %%EOF count (incremental updates), embedded-signature /ByteRange values and whether the signed range
  covers the whole file, embedded image count and text characters. Structural observation only: no signature is
  cryptographically validated.
Usage: python compute_copy_facts.py --held-root <dir>"""
import argparse, csv, hashlib, re, sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
AW = PKG.parent
SCOPE = ("HELD_OFFICIAL_PUBLICATION_PROVENANCE_UNDOCUMENTED", "HELD_OFFICIAL_COURT_COPY_PROVENANCE_UNDOCUMENTED")
BR = re.compile(rb"/ByteRange\s*\[\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*\]")


def read(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main():
    import pymupdf  # required: a missing dependency must fail, not write blank facts
    ap = argparse.ArgumentParser()
    ap.add_argument("--held-root", required=True)
    a = ap.parse_args()
    root = Path(a.held_root)
    master = {r["source_id"]: r for r in read(AW / "SOURCE-LIBRARY-C5/registers/source_master_register.csv")}
    rows, struct = [], []
    for c in read(AW / "SOURCE-LIBRARY-C5/registers/source_copy_register.csv"):
        if master[c["source_id"]]["holding_state"] not in SCOPE:
            continue
        paths = [x.strip() for x in c["held_paths"].split(";") if x.strip()]
        b = None
        for rel in paths:
            bb = (root / rel).read_bytes()
            if hashlib.sha256(bb).hexdigest() != c["sha256"]:
                print("HASH MISMATCH", rel, file=sys.stderr)
                return 2
            b = bb
        d = pymupdf.open(root / paths[0])
        text = re.sub(r"\s+", " ", d[0].get_text("text")).strip()[:400]
        rows.append({"copy_id": c["copy_id"], "source_id": c["source_id"], "sha256": c["sha256"], "md5": hashlib.md5(b).hexdigest(),
                     "sha1": hashlib.sha1(b).hexdigest(), "bytes": str(len(b)), "pages": str(d.page_count), "p1_text_excerpt": text})
        ranges = [tuple(int(x) for x in m) for m in BR.findall(b)]
        off = b.find(b"%PDF")  # byte offsets in /ByteRange count from the PDF header; a host may prepend bytes (JUDIS quirk)
        if not ranges:
            covers = "NO_SIGNATURE"
        elif any(r[0] == 0 and r[2] + r[3] == len(b) for r in ranges):
            covers = "YES"
        elif off > 0 and any(r[0] == 0 and r[2] + r[3] == len(b) - off for r in ranges):
            covers = "YES_AFTER_PREFIX"
        else:
            covers = "NO"
        struct.append({"copy_id": c["copy_id"], "sha256": c["sha256"], "bytes": str(len(b)), "producer": ((d.metadata or {}).get("producer", "") or "").encode("ascii", "replace").decode("ascii"),
                       "eof_markers": str(b.count(b"%%EOF")), "pdf_header_offset": str(off), "signature_byte_ranges": " ".join("[%d %d %d %d]" % r for r in ranges),
                       "signed_range_covers_file": covers, "embedded_images": str(sum(len(pg.get_images()) for pg in d)),
                       "text_chars": str(sum(len(pg.get_text()) for pg in d))})
    rows.sort(key=lambda r: r["copy_id"])
    struct.sort(key=lambda r: r["copy_id"])
    write(PKG / "inputs/held_copy_facts.csv", rows)
    write(PKG / "inputs/copy_structure_c6.csv", struct)
    print(f"copies={len(rows)} sources={len({r['source_id'] for r in rows})} paths_hashed={sum(len([x for x in r['held_paths'].split(';') if x.strip()]) for r in read(AW / 'SOURCE-LIBRARY-C5/registers/source_copy_register.csv') if master[r['source_id']]['holding_state'] in SCOPE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
