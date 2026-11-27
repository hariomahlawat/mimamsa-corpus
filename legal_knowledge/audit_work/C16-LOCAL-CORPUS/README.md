# Cycle 16 local corpus reconciliation

This directory contains the deterministic, read-only reconciliation tool and tests. Large inputs, derivatives, document bodies, and full machine-readable outputs remain outside Git at `E:\Mimamsa-Data\local-corpus-reconciliation`.

Pinned baselines:

- Git: `9837bb3827c091d823ea0bfa28448b9343b69a2d`
- Hugging Face canonical: `f8a46dfaec55a13f2aaac2fde4139ca0acd5cff9`
- Hugging Face `cycle15-candidates`: `217020dbd969e14c2373697f4094fa00557962a6`

Run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest -v legal_knowledge\audit_work\C16-LOCAL-CORPUS\test_c16_reconcile.py
.\.venv\Scripts\python.exe legal_knowledge\audit_work\C16-LOCAL-CORPUS\c16_reconcile.py `
  --source 'E:\Judgements' `
  --output 'E:\Mimamsa-Data\local-corpus-reconciliation' `
  --repo . `
  --refresh-canonical
```

The run is restartable through `inventory-checkpoint.jsonl`. It does not upload, ingest, approve, or promote any document. Exact normalized-text identity selects one deterministic primary while retaining every path and subject tag in the inventory. Similarity or metadata signals do not establish legal identity.

Known limits:

- Hindi Tesseract data is absent; OCR-required pages are queued, not fabricated.
- Legacy canonical paths without trusted SHA-256 cannot prove absence.
- Canonical derivatives were not downloaded, so cross-corpus normalized-text matching is not complete.
- Automated metadata and relevance values are candidates and are not legal findings.

