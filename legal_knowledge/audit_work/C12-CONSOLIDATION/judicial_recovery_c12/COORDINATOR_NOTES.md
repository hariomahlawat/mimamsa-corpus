# Judicial recovery: coordinator notes (not generated)

## Coordinator additivity check (independent of this workstream's author)
The coordinator compared the full HF trees at `5524c3d9` and `15bd03cc`:
- 55 paths added;
- 0 removed;
- 1 changed: `.gitattributes`.

HF appends LFS tracking rules to `.gitattributes` automatically when binaries are added; it grew from 401,428 to 402,898 bytes. No source or record file was modified. The dataset is still private.

## Preservation of the 7 excluded acquisitions (review R50-09)
**Upload**
- HF commit `3864faf3bb24edef4bfb18fa0916cc788eb68d79`, parent `15bd03cc`.
- Path: `legal_knowledge/preservation/c12_acquired_not_ingested/<sha[:2]>/<sha>/`, holding each PDF with a `.meta.json` sidecar, plus `PACKAGE_SHA256SUMS`.

**Verification**
- Revision-pinned re-download: 14/14 package sums pass.
- The 7 PDF hashes equal those in `INGESTION_LOG.csv`.
- Tree diff against `15bd03cc`: 15 added, 0 removed; the only change is `.gitattributes`, which HF updates automatically.

**Status:** these are preserved for reproducibility only. They are **not ingested** into the corpus, carry no restriction markings, and come from a public SC judgments mirror (an allow-listed host).
