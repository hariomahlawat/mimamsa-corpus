# raw-data branch

Raw files downloaded by the crawler on 2026-11-21 from https://indiacode.gov.in (8 Acts, 81 files, 246 MB).
They are kept off `main` so normal clones stay small.

- `data/raw/indiacode/<yyyy>/<sha256>.<ext>`: files exactly as served, never modified. `0000` = year not
  known at download time. `.json` files are API pages holding the section records.
- `data/raw_manifest.csv`: one row per file: source URL, retrieval time, Act it belongs to, category,
  title and original file name.
- `data/SHA256SUMS`: verify with `sha256sum -c data/SHA256SUMS`.

The site watermarks PDFs at download, so they differ from the MD5 in its own listing (`listed_md5`).

## Processed records (added by the Phase 2 pipeline, 2026-11-21)

- `data/meta/<doc_id>.json`: one metadata record per document (61).
- `data/sections/<doc_id>/<key>.json`: one record per section (1,707), with text and amendment notes.
- `data/text/<doc_id>.txt`: extracted text with `[[page N]]` markers (57 documents; 4 scans wait for OCR).
- `data/relations.jsonl`, `data/manifest.csv`.

All of these can be rebuilt from the raw files with `python -m pipeline all` on `main`.
