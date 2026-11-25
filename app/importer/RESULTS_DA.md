# PR #54 data-assurance cases through the importer (ASR-E05)

- **Implementation:**
  - `app/importer/mimamsa_importer/importer.py`, branch `claude/c13-b-app`; this file was committed together with the importer;
  - contract R2 (`CONTRACT_REVISION = "R2"`).
- **Oracle and fixtures:** PR #54 `pr54` = `703d98cb`, `docs/architecture/reviews/c13-assurance/data_oracle.py` and `data-fixtures.json`. **Not modified.**
- **Environment:** x86-64 Linux (container); Python 3.13.18; jsonschema 4.26.0, referencing 0.37.0, cryptography 50.0.2, pypdfium2 5.15.2; local filesystem (not NTFS); development-mode bundle keys (disposable). Run 2026-11-25.
- **Status vocabulary:** PR #54 README §4 (Passed, Failed, Blocked, Not implemented, Not executed, Not applicable).

## 1. Oracle run as documented

`python -B data_oracle.py --repo /home/user/mimamsa-corpus` exited 0. It printed "Pinned R1 and producer probes matched the recorded expectations, including open gaps." It reproduces at the pinned R1 (`9eeb04a4`) that DA-01-unbound-original, DA-01-missing-original, DA-04-outside-page and DA-35-cross-bound-anchor are **accepted by R1**. That is the gap ASR-E05 assigns to the importer.

## 2. Importer observations, compared with PR #54's comparator (revised after review E1–E10)

- **Commands:**
  - `python da_cases.py --observations obs.json`;
  - then `python -B data_oracle.py --adapter-observations obs.json`.
- **Comparator outcome:** exit non-zero with 64 mismatch lines.
  - All of them are **missing** fields for surfaces the importer does not implement.
  - **No observed value contradicts an expected value.**
  - DA-01 and DA-35 have zero mismatch lines.
- **Fixture conditions:** the same as the oracle's (fixture texts verbatim; record shapes from its builders), with one deliberate difference. A real derived-text file (`[[page 1]]\n<source>\n`) is bundled, because the importer verifies derivative bytes; the oracle's bundles carry no text file.

**What revision 2 changed in the evidence:**
- DA-04 `ocr_quote_enabled` is **no longer reported**. The earlier value was read from the input fixture, not observed (review E6).
- DA-35 `passage_hash_retained` is now the hash the importer **recomputes** from the verified derivative page text. It is no longer a copy of the declared value (review E2).
- Anchor offsets are range-checked against the page or passage, with or without a passage id (review E1).
- Content type is detected from bytes (review E3).
- Replay is refused using the site's own active sequence; generations are never rewritten (review E4).
- `servable()` applies the exclusion state (review E5).
- Unbound spans are stripped from served evidence (review E10).

| Case | Expected (PR #54 `adapter_expected_evidence`) | Observed (importer) | Status | Scope and limits |
| --- | --- | --- | --- | --- |
| **DA-01** exact bytes, SHA-256, vault key | original_bytes_equal true; sha256_equal true; vault_key_matches true | true; true; true | **Passed** | Control case through the vault. **Refused, with the previous generation and vault unchanged:** unbound original, missing original, size mismatch, page-count mismatch, PDF declared as text and text declared as PDF. A first import that is refused leaves nothing servable. PDF page count is measured with pypdfium2 |
| **DA-03** corruption and incomplete source | corrupt_rejected, active_generation_unchanged, prior_original_unchanged, allowed_truncation_warning_visible, unopenable_source_rejected all true | true, true, true, **missing**, true | **Passed** (4 fields); **Not implemented** (truncation warning: no UI) | The unopenable source is a fake PDF, refused before activation |
| **DA-04** OCR, page and passage anchoring | ocr_warning_visible true; ocr_quote_enabled false; page_image_match true; out_of_range_anchor_rejected true | missing; **missing**; missing; true | **Passed** (out_of_range_anchor_rejected); **Not implemented** (OCR warning UI; quotation surface); **Not executed** (page-image match: no page images or OCR pipeline in this run) | **Quarantined UNRESOLVED and never servable:** derivative out-of-page offsets, char_count, passage hash, text hash, wrong source, non-physical page, missing text file. **Anchors quarantined:** offsets beyond the page or passage (start only, end only or both, with or without a passage id) |
| **DA-35** anchor and original provenance | source_copy_hash_verified, page_anchor_verified, producing_commit_retained, passage_hash_retained, broken_binding_rejected all true | all true | **Passed** | Passage hash recomputed from verified bytes; a wrong anchor `text_sha256` is quarantined. The cross-bound anchor (another document's copy, page 99) is quarantined. An unbound span is served page-only, with its fields stripped |
| DA-05 explicit unknown metadata | null issuer and date; NOT_ESTABLISHED | missing | **Not implemented** | No metadata store or display yet |
| DA-02, DA-06 to DA-10 | site deduplication, review trace, restricted surfaces, publication, withdrawal, incremental update | missing | **Not implemented** | **Partial building blocks, not credited:** `servable()` honours withdrawal and restriction from the exclusion store (tests `test_e5_*`); the RM-001 document is refused before any write. Full DA-07/DA-09 surfaces need the site |
| DA-21 to DA-24, DA-31 to DA-34 | A4/A5 adapter evidence | missing | **Blocked** | No A4/A5 adapter; R1/R2 has no provision-version or graph-node kind (reconciliation X6) |

**Counts (importer scope):**
- Passed: 2 cases fully (DA-01, DA-35) and 2 in part (DA-03: 4 of 5 fields; DA-04: 1 of 4).
- Not implemented: 8 cases (DA-02, DA-05 to DA-10), plus 1 field of DA-03 and 2 of DA-04.
- Not executed: 1 field (DA-04 page_image_match).
- Blocked: 8 (A4/A5).
- Failed: 0.

**ASR-E06 / UX-12 support (importer `cite()`)**
- A cited copy replaced in a later release remains openable exactly: `CITED_COPY_ELIGIBLE_NOT_CURRENT`. The prior copy is retained in the vault and the append-only held-copies index (test `test_e8_*`).
- Withdrawn, restricted and not-held copies give one indistinguishable state (`test_e7_*`).

**Fail-closed and crash recovery (confirmation N1–N3).**
- The exclusion guard denies on every `None` path except the explicitly installed and recorded `none` mode.
- Copies become held only after activation.
- Crash-and-retry is tested at three points.
- Excluded copies are filtered out before prefix disambiguation.

These are observations on a Linux test host, not Windows site acceptance.
