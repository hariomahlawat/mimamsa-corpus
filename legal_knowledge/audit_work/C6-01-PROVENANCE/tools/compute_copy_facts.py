"""C6-01 local fact capture (run once where the held binaries are available; read-only on them).

For every held copy in the C6-01 scope (sources whose Cycle 5 holding_state is *_PROVENANCE_UNDOCUMENTED) it records
sha256 (re-hashed), md5, sha1, bytes, page count and the first ~400 characters of page-1 text (whitespace
normalised) to inputs/held_copy_facts.csv. The p.1 text is a text-layer identity aid only; it is not an image check.
Usage: python compute_copy_facts.py --held-root <dir>"""
import argparse, csv, hashlib, re, sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
AW = PKG.parent
SCOPE = ("HELD_OFFICIAL_PUBLICATION_PROVENANCE_UNDOCUMENTED", "HELD_OFFICIAL_COURT_COPY_PROVENANCE_UNDOCUMENTED")


def read(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--held-root", required=True)
    a = ap.parse_args()
    root = Path(a.held_root)
    master = {r["source_id"]: r for r in read(AW / "SOURCE-LIBRARY-C5/registers/source_master_register.csv")}
    rows = []
    for c in read(AW / "SOURCE-LIBRARY-C5/registers/source_copy_register.csv"):
        if master[c["source_id"]]["holding_state"] not in SCOPE:
            continue
        p = root / c["held_paths"].split(";")[0]
        b = p.read_bytes()
        if hashlib.sha256(b).hexdigest() != c["sha256"]:
            print("HASH MISMATCH", p, file=sys.stderr)
            return 2
        pages, text = "", ""
        try:
            import pymupdf
            d = pymupdf.open(p)
            pages = str(d.page_count)
            text = re.sub(r"\s+", " ", d[0].get_text("text")).strip()[:400]
        except Exception as e:  # noqa: BLE001
            text = f"TEXT_NOT_EXTRACTED ({type(e).__name__})"
        rows.append({"copy_id": c["copy_id"], "source_id": c["source_id"], "sha256": c["sha256"], "md5": hashlib.md5(b).hexdigest(),
                     "sha1": hashlib.sha1(b).hexdigest(), "bytes": str(len(b)), "pages": pages, "p1_text_excerpt": text})
    rows.sort(key=lambda r: r["copy_id"])
    with open(PKG / "inputs/held_copy_facts.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"copies={len(rows)} sources={len({r['source_id'] for r in rows})}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
