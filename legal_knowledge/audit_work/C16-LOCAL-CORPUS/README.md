# Cycle 16 local corpus reconciliation

Deterministic, read-only inventory, OCR, conversion-evidence and reconciliation tooling for the owner's local corpus. Source documents are read from `E:\Judgements`; generated text, page renders, searchable PDFs and full registers remain outside Git under `E:\Mimamsa-Data\local-corpus-reconciliation\generation-v5`.

## Pinned authorities

- Git comparison base: `9837bb3827c091d823ea0bfa28448b9343b69a2d`
- Hugging Face canonical: `f8a46dfaec55a13f2aaac2fde4139ca0acd5cff9`
- Hugging Face cycle15: `217020dbd969e14c2373697f4094fa00557962a6`
- accepted contract 2.0: `8052792186b822881508e0e4b95f586df6772a25`
- contract merge: `5bdc8e68abf564f7a1c1765f0319d4f4e90738ab`

Contract verification at the accepted head is 160 passing tests. The exchange adapter remains separate from OCR state so additive 2.1 receipt artifacts do not repeat OCR or conversion.

## Reproducibility

Use the existing external environment and official pinned Hindi model. OCR state is immutable and namespaced by a SHA-256 of engine version, traineddata hashes, TSV configuration, PSMs and preprocessing.

```powershell
$py = 'E:\Mimamsa-Data\venv\Scripts\python.exe'
$root = 'E:\Mimamsa-Data\local-corpus-reconciliation\generation-v5'
$models = 'E:\Mimamsa-Data\local-corpus-reconciliation\models\tessdata-c16-87416418657359cb625c412a48b6e1d6d41c29bd'
$tool = 'legal_knowledge\audit_work\C16-LOCAL-CORPUS\c16_ocr.py'

& $py $tool --mode second-pass --source 'E:\Judgements' `
  --inventory "$root\inventory-checkpoint.jsonl" `
  --primary-register "$root\ocr-images\OCR_PROCESSING_REGISTER-18299e9143c2.jsonl" `
  --output "$root\ocr-images-second-pass" --tessdata $models --workers 2

& $py $tool --mode pdf-pages --source 'E:\Judgements' `
  --inventory "$root\inventory-checkpoint.jsonl" `
  --output "$root\ocr-pdf-pages" --tessdata $models --workers 4
```

Successful hashes/page keys are skipped on restart. Empty OCR is always `HELD_UNREADABLE_OR_PROCESSING_ERROR`; small dimensions only nominate decorative review and never clear content.

After both registers exist, generate the document/derivative access register with `--mode access-register`, supplying the primary image, second-pass image and PDF-page registers. Any missing, unreadable, failed or marked component holds the containing document and all derivatives.

The Word conversion script is intentionally targeted. It verifies source hashes, disables macros and link updates, requires every embedded image to be cleared, preserves originals, and labels PDFs as locally reconstructed reference copies.

## Governance boundaries

- No local document is uploaded, admitted, approved or promoted.
- Exact binary identity is distinct from normalized-text similarity, derivative hashes and LFS object identity.
- Filename provisions, relevance and legal-work identity remain candidates pending legal validation.
- Every source path and all 5,294 folder-classification relationships are preserved.
- OCR, conversion and access registers are evidence inputs to the modular exchange adapter, not core admission decisions.
