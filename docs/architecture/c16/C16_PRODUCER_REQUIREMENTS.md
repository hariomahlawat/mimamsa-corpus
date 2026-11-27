# C16 corpus producer requirements (Codex)

**Applies to:** any tool that emits `mimamsa-corpus-contract/2.0` records, such as the PR #76 reconciliation successor, the Word image extraction fix and the v7 re-derivation.

**Normative references:** [C16_CORPUS_INTEGRATION_CONTRACT.md](C16_CORPUS_INTEGRATION_CONTRACT.md), the schemas in `app/contract/schemas/c16/`, and the reference validator `mimamsa_contract.c16.rules.exchange_issues`.

## 1. What to emit, per corpus generation

| File | Record kind | Required content |
| --- | --- | --- |
| `identities.jsonl` | `document_identity` | One record per (`doc_id`, `sha256`) admitted to the generation **or held**. Every observed path goes in `provenance.observations[]` |
| `anchors.jsonl` | `evidence_anchor` | Every anchor that a relationship cites, plus OCR anchors of embedded images |
| `relationships.jsonl` | `corpus_relationship` | Folder and file-name classifications (one per path and label); text-evidenced citations and treatments |
| `taxonomy.jsonl` | `taxonomy_node` | Every subject, statute, chapter and provision node a relationship targets, with all its parents |
| `admissions.jsonl` | `corpus_admission` | One decision per identity, listing all ten gates |
| `reviewed_records.jsonl` | contract-v1 `reviewed_record` | Every review a `review_binding` names (subject `{kind: candidate, id}` or `{kind: document, id}`, axis evidence_fidelity) |
| `GENERATION.json` | `corpus_generation_manifest` | `corpus_generation_id`; pinned inputs (every HF revision with its purpose, full git commits, local collections with inventory hash and count, register sha256, tools); every file with kind, sha256 and record count; registries (`instrument_codes`, `external_judgments`). Shards are `<stem>.<nnnn>.jsonl` and must be declared |

## 2. Content rules

| # | Requirement |
| --- | --- |
| R1 | Hash every original from its bytes (G01). Detect the format from magic bytes (G02). Never trust the extension |
| R2 | Never write an absolute or drive path. Paths are relative to a registered collection (`local:<name>`), NFC, with POSIX separators |
| R3 | **Word documents:** inventory every embedded image (`word/media/*` in body order) with `image_sha256` and `IMG:<sha>:<seq>`. OCR each one, or mark it `NOT_REQUIRED_DECORATIVE` with a reason. Until that is done, emit `WORD_IMAGES_NOT_INVENTORIED` and `embedded_images` UNRESOLVED, and hold the item (G07 NOT_RUN) |
| R4 | **Scans and mixed PDFs:** OCR per page with a recorded `ocr_config` (engine, version, languages, DPI, PSM, preprocessing, config hash). Store per-page mean confidence and flag low-confidence pages. OCR text is never quotable |
| R5 | **Reconstructions** (searchable PDFs, conversions): emit them as a separate copy with `LOCALLY_RECONSTRUCTED`, `reconstructed_from_sha256` and `page_mapping`. Use `ONE_TO_ONE_PAGE_HASH_CHECKED` only after re-hashing page images one to one. Never put the reconstruction's sha256 into the original's identity |
| R6 | **Extracts and compilations:** set `content_scope`. For an extract, give `extract_scope` with the work's pages (or UNRESOLVED). For a compilation, give `members[]` with page ranges, and attribute relationships with `compilation_member_seq` |
| R7 | Write `COMPLETE` only with evidence (`completeness_basis`). Otherwise use `NOT_CHECKED` |
| R8 | Classification rules are versioned (`C16-FOLDER-SUBJECT 1.0`, `C16-FN-PROVLIST 1.0`). A new reading, such as a new abbreviation, is a new rule version, and the owner confirms it before it is used (contract Q3) |
| R9 | Label-based relationships are never DOCUMENTARY_CHECKED, LEGAL_REVIEWED or `is_finding`. Evidence relationships need ≥ 1 anchor in the same exchange, on the subject's own copy |
| R10 | Emit only the producer verification values CANDIDATE, EXTRACTED_STRUCTURE and CURATED_NAVIGATION. DOCUMENTARY_CHECKED needs an independent v1 `reviewed_record` (`RV-`, reviewer ≠ author, matching commit). Never emit `legally_validated` while AUTH-LEDGER is at version 0 |
| R11 | Run the restricted-material register (`config/restricted_material.json`) on hashes, doc_ids, paths and every record string (G03). A matched item is EXCLUDED_RESTRICTED, with its RM id, and nothing else about it is emitted. A detected printed marking without a register entry is HELD_ACCESS_MARKING_REVIEW |
| R12 | Keep UNRESOLVED distinct from `null`. Never guess a judgment id, instrument code, date, page count or provision |
| R13 | Do not copy document text into records except in an anchor's `quote`, and only when `quoting_permitted` is true (native, reliable text) |
| R14 | **No gate passes without evidence.** G01 PASS only for BYTE_VERIFIED copies (re-downloaded at a pinned revision and re-hashed); a declared hash is NOT_RUN. G09 PASS only after duplicates are resolved. G08 PASS only for an assessed relevance, not an automated signal. Every PASS carries an `evidence_ref`. NOT_APPLICABLE only for G06 (no derivative by design) and G07 (inventoried, empty image list) |
| R15 | **Admissions are append-only revisions.** A changed decision or gate result is revision n+1 superseding revision n; never rewrite or fork. Every identity has exactly one effective decision per generation |
| R16 | **Restricted items leave the exportable exchange entirely**: keep only a local exclusion receipt (hash prefix, reason, `exportable: false`) outside the exchange |
| R17 | **Never fabricate a format.** Unknown bytes are UNRECOGNISED_FORMAT / `application/octet-stream` |
| R18 | **Bind every raised verification to an independent reviewed_record** (`review_binding`: exact id, canonical sha256, commit, reviewer distinct from author). Bind anchors to identities: page within the copy, image occurrence in the inventory, derivative of the measured representation |
| R19 | Merge observations of the same binary into one identity, but keep one classification per path and label (full folder hierarchy; contract section 8.3) |

## 3. Validation gates (the producer must pass these before handing over a generation)

1. `rules.exchange_issues(files, mode="strict", auth_ledger_version=0, register=load_register())` returns no errors: manifest counts and hashes, canonical names, global uniqueness, one generation, schema, ids, admission binding and gates, anchor and review binding, registries, taxonomy DAG and restricted register. `mode="partial"` is for work in progress only and is never a hand-over.
2. Every `admission` lists G01–G10. `application_eligible=true` only with all gates PASS or NOT_APPLICABLE.
3. Coverage report:
   - counts per representation kind, decision and gate result;
   - Word files with images not yet OCR'd;
   - OCR pages below threshold;
   - reconstructions without a checked mapping.
4. Re-run determinism: building twice from the same pinned inputs gives byte-identical JSONL files (compare sha256).
5. Fixture self-check: `python -I app/contract/fixtures/c16/build_fixtures.py --check` and `pytest app/contract/tests/test_c16_contract.py` pass at the contract commit the producer pins.

## 4. Determinism rules

| # | Rule |
| --- | --- |
| D1 | Canonical JSONL: contract section 9.1. Use `canonical.dumps_jsonl`, or reproduce it byte for byte |
| D2 | Ids from `canonical.relationship_id`, `anchor_id` and `admission_id`; never random or sequence-based |
| D3 | No wall-clock values in identity fields. `observed_at` and `decided_at` are null or pinned to the generation's declared build time |
| D4 | Pinned inputs: HF 40-hex revision, git commit, register sha256 and tool versions, all recorded in `GENERATION.json`. OCR models are pinned by file hash |
| D5 | `corpus_generation_id = CG-<yyyymmdd>-<label>-<first 8 hex of sha256(canonical GENERATION inputs)>` |
| D6 | Sort every set-like array; number every order-bearing array from 1 |
| D7 | NFC every string at the source. Reject non-NFC rather than normalising silently inside records |

## 5. Preservation and HF

- Originals and derivatives are preserved to the HF dataset under the standing instruction (ADR-0004):
  - versioned and non-destructive;
  - SHA-256 verified by re-download at the pinned commit;
  - the commit id recorded in git.
- C16 JSONL files are preserved the same way, alongside their `GENERATION.json`.
- Admission records never delete or overwrite an original. A changed decision is a new record with `supersedes_admission_id`.
