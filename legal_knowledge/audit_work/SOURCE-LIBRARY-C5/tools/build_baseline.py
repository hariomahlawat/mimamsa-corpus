"""Cycle 5 frozen baseline (run locally; needs the held-source root). Read-only on every input.

Writes:
- baseline/held_binaries_manifest.csv: every held pdf/doc/docx listed in CALIBRATION-02's held-source index, re-hashed
  from disk, with byte size, page count (pdf only; via pymupdf if importable), text-layer class and a mismatch flag.
- baseline/existing_register_index.csv: every CSV under legal_knowledge/audit_work at the baseline commit (path,
  data rows, header, sha256), so later cycles can detect edits to earlier registers.
- baseline/frozen_baseline_manifest.json: staging commit, original-corpus hashes, totals.

Usage: python build_baseline.py --held-root <dir> --staging-sha <sha> [--prs-json <file>]"""
import argparse, csv, hashlib, json, sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
REPO = PKG.parents[2]
ORIGINALS = {
    "records_658": "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl",
    "cases_53": "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl",
}
EXPECTED = {
    "records_658": "9a8f0d193065762ffa987116dc761bcb734008d2a87a946f5591741f5befcfc1",
    "cases_53": "8b8d53cd1434f7c1c6eaebe77f1fe295fb8b81b755e93276999b4b40b3c8f89a",
}
HELD_INDEX = REPO / "legal_knowledge/audit_work/CALIBRATION-02/registers/held_sources_scratchpad.csv"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def pdf_profile(p):
    try:
        import pymupdf
    except ImportError:
        return "", "NOT_CHECKED"
    try:
        d = pymupdf.open(p)
        n = d.page_count
        chars = [len(d[i].get_text("text").strip()) for i in range(n)]
        imgs = [len(d[i].get_images()) for i in range(n)]
    except Exception as e:  # damaged file: report, do not guess
        return "", f"OPEN_FAILED:{type(e).__name__}"
    texty = sum(1 for c in chars if c >= 200)
    scanned = sum(1 for c, i in zip(chars, imgs) if c >= 200 and i)
    if n == 0:
        cls = "EMPTY"
    elif texty == 0:
        cls = "IMAGE_ONLY_NO_TEXT_LAYER" if any(imgs) else "NO_TEXT_NO_IMAGES"
    elif scanned == texty == n:
        cls = "SCANNED_IMAGE_WITH_TEXT_LAYER_ALL_PAGES"  # text layer is OCR or overlay; not born-digital
    elif scanned == 0 and texty == n:
        cls = "TEXT_LAYER_NO_IMAGES_ALL_PAGES"  # consistent with born-digital or retyped; not proof of either
    else:
        cls = f"MIXED_TEXT_{texty}_SCANNED_{scanned}_OF_{n}"
    return str(n), cls


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--held-root", required=True)
    ap.add_argument("--staging-sha", required=True)
    ap.add_argument("--prs-json")
    a = ap.parse_args()
    root = Path(a.held_root)
    orig = {k: sha(REPO / v) for k, v in ORIGINALS.items()}
    if orig != EXPECTED:
        print("ORIGINAL HASH MISMATCH", orig, file=sys.stderr)
        return 2
    rows = []
    for r in csv.DictReader(open(HELD_INDEX, newline="", encoding="utf-8")):
        rel = r["scratchpad_relative_path"]
        if not rel.lower().endswith((".pdf", ".doc", ".docx")):
            continue
        p = root / rel
        if not p.exists():
            rows.append({"held_path": rel, "indexed_sha256": r["sha256"], "rehashed_sha256": "", "bytes": "", "hash_check": "FILE_MISSING",
                         "pages": "", "text_layer_class": "NOT_CHECKED"})
            continue
        h = sha(p)
        pages, cls = pdf_profile(p) if rel.lower().endswith(".pdf") else ("", "WORD_BINARY_NOT_PROFILED")
        rows.append({"held_path": rel, "indexed_sha256": r["sha256"], "rehashed_sha256": h, "bytes": str(p.stat().st_size),
                     "hash_check": "MATCH" if h == r["sha256"] else "MISMATCH", "pages": pages, "text_layer_class": cls})
    rows.sort(key=lambda d: d["held_path"])
    out = PKG / "baseline"
    with open(out / "held_binaries_manifest.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader(); w.writerows(rows)
    reg = []
    for p in sorted((REPO / "legal_knowledge/audit_work").rglob("*.csv")):
        if PKG in p.parents:
            continue
        with open(p, newline="", encoding="utf-8") as f:
            rd = list(csv.reader(f))
        reg.append({"path": str(p.relative_to(REPO)), "data_rows": str(max(len(rd) - 1, 0)), "header": "|".join(rd[0]) if rd else "", "sha256": sha(p)})
    with open(out / "existing_register_index.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["path", "data_rows", "header", "sha256"], lineterminator="\n")
        w.writeheader(); w.writerows(reg)
    uniq = {r["rehashed_sha256"] for r in rows if r["rehashed_sha256"]}
    man = {
        "cycle": "C5", "baseline_staging_commit": a.staging_sha, "original_corpus_sha256": orig,
        "held_binary_paths": len(rows), "held_binary_unique_sha256": len(uniq),
        "hash_check": {k: sum(1 for r in rows if r["hash_check"] == k) for k in ("MATCH", "MISMATCH", "FILE_MISSING")},
        "existing_csv_registers": len(reg),
        "held_root_note": "held binaries live outside git in the session scratchpad; this manifest freezes their hashes",
        "open_prs_at_baseline": json.load(open(a.prs_json)) if a.prs_json else None,
    }
    (out / "frozen_baseline_manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: man[k] for k in ("held_binary_paths", "held_binary_unique_sha256", "hash_check", "existing_csv_registers")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
