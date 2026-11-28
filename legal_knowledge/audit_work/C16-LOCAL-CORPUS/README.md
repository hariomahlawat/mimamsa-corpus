# Cycle 16 local corpus reconciliation

Deterministic, read-only inventory, OCR, conversion-evidence and reconciliation tooling for the owner's local corpus. Source documents are read from `E:\Judgements`; generated text, page renders, searchable PDFs and full registers remain outside Git under `E:\Mimamsa-Data\local-corpus-reconciliation\generation-v5`.

## Pinned authorities

- Git comparison base: `9837bb3827c091d823ea0bfa28448b9343b69a2d`
- Hugging Face canonical: `f8a46dfaec55a13f2aaac2fde4139ca0acd5cff9`
- Hugging Face cycle15: `217020dbd969e14c2373697f4094fa00557962a6`
- accepted contract 2.0: `8052792186b822881508e0e4b95f586df6772a25`
- contract merge: `5bdc8e68abf564f7a1c1765f0319d4f4e90738ab`
- additive Contract 2.1 producer interface: `1e3060def474d8486d853b62bd5a25d9bc04372b`

The producer exchange adapter remains separate from OCR state, so Contract 2.1 receipts, accounting and package regeneration do not repeat OCR or conversion. Its output is checked by the pinned Contract 2.1 strict reference validator.

## Reproducibility

Use the existing external environment and official pinned Hindi model. OCR state is immutable and namespaced by a SHA-256 of engine version, traineddata hashes, TSV configuration, PSMs and preprocessing.

```powershell
$py = 'E:\Mimamsa-Data\venv\Scripts\python.exe'
$root = 'E:\Mimamsa-Data\local-corpus-reconciliation\generation-v5'
$models = 'E:\Mimamsa-Data\tessdata-c16'
$tool = 'legal_knowledge\audit_work\C16-LOCAL-CORPUS\c16_ocr.py'

& $py $tool --mode second-pass --source 'E:\Judgements' `
  --inventory "$root\inventory-checkpoint.jsonl" `
  --primary-register "$root\ocr-images-v2\OCR_PROCESSING_REGISTER-11b3323a9665.jsonl" `
  --output "$root\ocr-images-second-pass-v2" --tessdata $models --workers 2

& $py $tool --mode pdf-pages --source 'E:\Judgements' `
  --inventory "$root\inventory-checkpoint.jsonl" `
  --output "$root\ocr-pdf-pages-v2" --tessdata $models --workers 8
```

Successful hashes/page keys are skipped on restart. Empty OCR is always `HELD_UNREADABLE_OR_PROCESSING_ERROR`; small dimensions only nominate decorative review and never clear content.

After all three registers exist, generate the document/derivative access register with `--mode access-register`, supplying the primary image, second-pass image and PDF-page registers plus the accepted configuration hashes through repeatable `--image-config` and `--pdf-config` arguments. Clean evidence from any other configuration cannot release a document. Any missing, unreadable, failed or marked component holds the containing document and all derivatives; a positive marking in any attempt survives later clean attempts.

Run `c16_exchange_v21.py` only after access propagation. It consumes the inventory, legal-identity assessment, v2 OCR evidence, access holds and taxonomy registers; emits canonical Contract 2.1 exchange populations, grouped OCR derivatives, per-source accounting, exact source/export candidate sets and the local hold register; and invokes the pinned strict validator. All admissions remain ineligible unless independent gate receipts and legal validation establish otherwise.

The Word conversion script is intentionally targeted. It verifies source hashes, disables macros and link updates, requires every embedded image to be cleared, preserves originals, and labels PDFs as locally reconstructed reference copies.

## Governance boundaries

- No local document is uploaded, admitted, approved or promoted.
- Exact binary identity is distinct from normalized-text similarity, derivative hashes and LFS object identity.
- Filename provisions, relevance and legal-work identity remain candidates pending legal validation.
- Every source path and all 5,294 classification relationships are preserved locally. Relationships belonging to restricted documents remain only in the external hold evidence and are never exported.
- OCR, conversion and access registers are evidence inputs to the modular exchange adapter, not core admission decisions.
