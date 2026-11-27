# Reproducing MML text extraction and page references (private environments only)

**Database work only.** Complete extracted manual text is **not** committed or uploaded until licensing, access markings and redistribution restrictions have been reviewed (owner instruction, 2026-11-22).
What may be committed: file hashes, locator formats, page and line counts, tool versions and derived-file hashes (`legal_knowledge/audit_work/PILOT-01/mml_derived_manifest.json`).

## 1. Obtain the originals inside an authorised private environment
- **Canonical source:** the private HF dataset `hariomahlawat/mimamsa-corpus`, path `legal_knowledge/manual_sources/originals/` (8 files), downloaded with an authorised read token.
- **Alternative used in PILOT-01:** the transfer ZIP is still reconstructible from the base64 parts in the history of `legal-knowledge/v2.5-staging`, at the parent of commit `0240341` (`.mml_transfer/part_*.b64`). The ZIP SHA-256 is `9d82b9c5…f31c`.
  - **Owner decision needed:** these parts sit in the private GitHub history. If that repository's visibility ever changes, the manuals would be exposed.
- Either way, the tool checks every file against `legal_knowledge/manual_sources/MML_Originals_Manifest.csv` before extracting anything.

## 2. Extract
```bash
python tools/legal_audit/mml_extract.py --originals /secure/mml/originals --out /secure/mml/derived --verify legal_knowledge/audit_work/PILOT-01/mml_derived_manifest.json
```
- The tool **refuses** any `--out` path inside the repository.
- It needs poppler-utils (pdftotext/pdfinfo/pdftoppm) and LibreOffice. LibreOffice runs with an isolated, empty profile so that user settings cannot change the output.
- PILOT-01 baseline: pdftotext 24.02.0 and LibreOffice 24.2.7.2. Other versions may give different bytes; `--verify` reports MATCH or MISMATCH for each file.

## 3. Locator formats (stable; pilot findings depend on them)
- **PDF:** `=== PDF_PAGE n / file=<name> ===` before each page. The locator is the PDF page; the printed page is recorded separately where it is visible on the page.
- **DOC:** `Lnnnnn| text`. The locator is the derived line. A DOC file has no page images, so DOC passages cannot be image-checked; check them in the original application if consequential.

## 4. Determinism evidence (2026-11-22)
- Two independent runs produced byte-identical output for all 8 files (`--verify`: 8/8 MATCH).
- The three PDF layers are byte-identical to the layer the pilot agents used.
- The five DOC layers keep **identical line counts and line numbers** (every pilot DOC locator stays valid). They differ only in characters: the pilot layer came from a non-isolated LibreOffice profile that wrote four files in cp1252 and lost ellipses ("…" became "?"), soft hyphens and dashes. The isolated-profile output (UTF-8) is now the reproducible baseline.

## 5. Page-image checks for legally consequential passages
```bash
python tools/legal_audit/mml_extract.py --originals … --out /secure/mml/derived --render "MML 2.pdf:152"
```
- Images stay in the private output directory. Only the render SHA-256 and the observation are recorded, in `PILOT-01/registers/page_image_checks.csv`.
- Required for negations, numbers, dates, amendment footnotes, and every P0/P1 pinpoint.
