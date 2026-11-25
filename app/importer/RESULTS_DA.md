# PR #54 data-assurance cases through the importer (ASR-E05)

- **Implementation:**
  - `app/importer/mimamsa_importer/importer.py`, branch `claude/c13-b-app`; this file was committed together with the importer;
  - contract R2 (`CONTRACT_REVISION = "R2"`).
- **Oracle and fixtures:** PR #54 `pr54` = `703d98cb`, `docs/architecture/reviews/c13-assurance/data_oracle.py` and `data-fixtures.json`. **Not modified.**
- **Environment:** x86-64 Linux (container); Python 3.13.18; jsonschema 4.26.0, referencing 0.37.0, cryptography 50.0.2, pypdfium2 5.15.2; local filesystem (not NTFS); development-mode bundle keys (disposable). Run 2026-11-25.
- **Status vocabulary:** PR #54 README §4 (Passed, Failed, Blocked, Not implemented, Not executed, Not applicable).

## 1. Oracle run as documented

`python -B data_oracle.py --repo /home/user/mimamsa-corpus` exited 0. It printed "Pinned R1 and producer probes matched the recorded expectations, including open gaps." It reproduces at the pinned R1 (`9eeb04a4`) that DA-01-unbound-original, DA-01-missing-original, DA-04-outside-page and DA-35-cross-bound-anchor are **accepted by R1**. That is the gap ASR-E05 assigns to the importer.

## 2. Importer observations, compared with PR #54's comparator

- **Commands:**
  - `python da_cases.py --observations obs.json`;
  - then `python -B data_oracle.py --adapter-observations obs.json`.
- **Comparator outcome:** exit non-zero with 63 mismatch lines.
  - All of them are fields **missing** for cases or surfaces the importer does not implement.
  - **No observed value contradicted an expected value.**
  - DA-01 and DA-35 have zero mismatch lines.
- **Fixture conditions:** the same as the oracle's (fixture texts verbatim; record shapes from its builders), with one deliberate difference. A real derived-text file (`[[page 1]]\n<source>\n`) is bundled, because the importer verifies derivative bytes; the oracle's bundles carry no text file.

| Case | Expected (PR #54 `adapter_expected_evidence`) | Observed (importer) | Status | Scope and limits |
| --- | --- | --- | --- | --- |
| **DA-01** exact bytes, SHA-256, vault key | original_bytes_equal true; sha256_equal true; vault_key_matches true | true; true; true | **Passed** | Control case through the vault. **Negative cases, all refused, with the previous generation and vault unchanged** (`test_da01_mismatch_refuses_activation_and_keeps_previous`): unbound-original (ALT bytes bundled, SOURCE claimed); missing-original; size mismatch; page-count mismatch. A first import refused leaves nothing servable. PDF page count is measured from bytes (pypdfium2) |
| **DA-03** corruption and incomplete source | corrupt_rejected, active_generation_unchanged, prior_original_unchanged, allowed_truncation_warning_visible, unopenable_source_rejected all true | true, true, true, **missing**, true | **Passed** (4 fields); **Not implemented** (truncation warning) | The truncation warning is a UI surface; no UI exists. The unopenable source was a fake PDF, refused before activation |
| **DA-04** OCR, page and passage anchoring | ocr_warning_visible true; ocr_quote_enabled false; page_image_match true; out_of_range_anchor_rejected true | missing; false; missing; true | **Passed** (2 fields); **Not implemented** (OCR warning UI); **Not executed** (page-image match: no page images or OCR pipeline in this run) | Out-of-page offset (end = len + 1), char_count mismatch, passage hash, text hash, wrong declared source, page outside physical pages and missing text file are each quarantined UNRESOLVED and never servable. A span bound to a quarantined derivative is also quarantined |
| **DA-35** anchor and original provenance | source_copy_hash_verified, page_anchor_verified, producing_commit_retained, passage_hash_retained, broken_binding_rejected all true | all true | **Passed** | The cross-bound anchor (another document's bundled copy, page 99) is quarantined with both reasons: wrong copy and non-physical page. Page 99 on the document's own copy is also rejected |
| DA-05 explicit unknown metadata | null issuer and date; NOT_ESTABLISHED | missing | **Not implemented** | No metadata store or display yet |
| DA-02, DA-06 to DA-10 | site deduplication, review trace, restricted surfaces, publication, withdrawal, incremental update | missing | **Not implemented** | Need DB, index, publication and withdrawal services (B1/B2). Restricted material: the RM-001 document is refused before any write (`test_rm001_document_never_imported`), but DA-07's surface checks need the site |
| DA-21 to DA-24, DA-31 to DA-34 | A4/A5 adapter evidence | missing | **Blocked** | No A4/A5 adapter; R1/R2 has no provision-version or graph-node kind (reconciliation X6) |

**Counts (importer scope):**
- Passed: 2 cases fully (DA-01, DA-35) and 2 in part (DA-03, DA-04).
- Not implemented: 8 (DA-02, DA-05 to DA-10), plus the UI fields of DA-03 and DA-04.
- Not executed: 1 field (DA-04 page_image_match).
- Blocked: 8 (A4/A5).
- Failed: 0.

These are observations on a Linux test host, not Windows site acceptance.
