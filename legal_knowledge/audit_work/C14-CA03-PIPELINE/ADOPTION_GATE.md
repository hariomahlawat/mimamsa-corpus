# CA-03 fail-closed adoption gate (proposal, 26 Nov 2026)

Baseline: c1e4d461e208bf961fd6bc51584dad01df220e61. No application or live pipeline changes in this branch.

## Confirmed gaps at baseline

- pipeline/judgments.py::run deletes raw, text and metadata on the legacy keyword rejection path. It can erase a shared raw hash used by another document.
- pipeline/records.py skips any SHA in the historical exclusion ledger before checking whether a recovered raw file exists. Its stale-output cleanup can also delete metadata/text. Changing judgments.run alone is insufficient.
- pipeline/relevance_states.py exists and is tested, but its decision is not connected to production run. Its positive evidence path can return RELEVANT even for truncated sources. Relevance is not source integrity, release or ingestion eligibility.
- pipeline/text_quality.py uses PyMuPDF; current application stack and licensing constraints must remain separate. Detector accepts Devanagari by script share; known shaping defects remain. Treat unsupported/uncertain language as review, not negative evidence.
- pipeline/report.py describes every no-keyword case as removed. tests/test_pipeline.py explicitly expects deletion and must be revised alongside integration. Preserve historical exclusions as a historical event ledger, not a current eligibility oracle.
- Existing extracted/OCR files contain physical page markers. A scalar mean OCR confidence is insufficient; absent page-level proof cannot support IRRELEVANT.

## Adoption sequence

1. Freeze hash of baseline exclusion ledger, data manifest, raw and text inventories; no active corpus run until backup verified or isolated disposable fixture/working snapshot used. No destructive migration.
2. Introduce an append-only, versioned assessment overlay with source SHA, text SHA, physical page count, each page verdict, extraction/OCR method and evidence, classifier version, reasons and independent integrity/relevance/eligibility dimensions. Preserve all eight states. Reassessment references earlier assessment. Keep old ledger immutable.
3. Validate raw bytes and path containment, physical count, exact page markers and text-to-raw binding. Missing, malformed, duplicated, inconsistent or unread pages cannot be negative evidence. Do not treat a PDF with missing EOF or page errors as import-ready even with positive keywords. Gate OCR by page-level evidence; missing metrics abstain. Retain all originals and derived files including IRRELEVANT. No calls to unlink in relevance path. No automatic removal or automatic inclusion based on a legacy status.
4. Integrate into judgments.run on isolated working snapshot; maintain compatible legacy relevance mapping only for readers and add separate explicit research eligibility. Do not publish non-final or irrelevant records as ordinary corpus candidates; coordinate contract mapping separately, without changing B1/B2 during commissioning.
5. Update records.run to recognise recovered originals despite historical exclusions and retain missing/previous artifacts without deletion. Preserve historical exclusion counts; separate current dispositions, review queue, and recovered identities. Audit graph/citation/report paths and stale outputs; no stale derived assertion may gain eligibility. Preserve original derived records, supersede by version.
6. Update report and tests; validate schema, raw/text SHA invariance, shared-byte aliases, idempotence, complete accounting, deterministic rerun, and exclusion history invariance. Existing C13 A1 unit tests retained.
7. Run independent Codex review and targeted integration tests; report P1/P2, no merge or real corpus run until explicit acceptance. CA-02 recovery runs require separately scoped owner approval.

## Regression acceptance matrix

| ID | Fixture | Required invariant |
|---|---|---|
| R01 | No text path | raw and metadata retained; OCR_REQUIRED or EXTRACTION_FAILED; never irrelevant |
| R02 | Garbled text with English signature | retained; not irrelevant |
| R03 | Image-only page / mixed readable pages | retained; OCR required or insufficient |
| R04 | Truncated raw with positive keywords | relevant may be recorded, but source incomplete and no ingestion eligibility |
| R05 | Clean civil text across every page | may classify irrelevant; raw and derived text never removed |
| R06 | Missing or mismatched page count / marker / text hash | abstain, no negative or ingestion decision |
| R07 | Low OCR confidence on one page despite high mean | abstain |
| R08 | AFT in title; generic body | candidate relevance, separate integrity check |
| R09 | Two doc IDs share one raw hash | both preserved, no alias loss |
| R10 | Previously excluded SHA now recovered | history preserved, recovery assessed and not skipped |
| R11 | Previously excluded SHA still absent | historical-only; no phantom active document |
| R12 | Repeat same run and input | deterministic assessment identity, no duplicate event or history rewrite |
| R13 | Corrupt file, missing raw file or path traversal | fail closed, no file mutation outside scope |
| R14 | Missing/unknown Hindi text quality | review or OCR; never negative based on script share alone |
| R15 | Existing citations followed by invalidated text | derived data retained but no stale eligibility |
| R16 | Importer/retrieval boundary | research access respects current eligibility; no candidate promotion |

Executable initial acceptance tests in this audit directory intentionally target future non-deletion semantics. They are not in default CI; expected to expose legacy behaviour. Independent review has not yet occurred.
