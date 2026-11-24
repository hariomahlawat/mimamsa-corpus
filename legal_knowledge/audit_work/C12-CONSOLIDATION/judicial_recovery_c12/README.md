# C12 judicial corpus recovery and controlled ingestion

Run on 2026-11-24 under the standing owner instruction (`docs/governance/CORPUS_REPOSITORY_GOVERNANCE.md`). Every HF write was additive (new paths only), had `parent_commit` pinned, and was byte-verified by re-downloading at the new commit. Nothing on HF was overwritten or deleted. Visibility was not changed. No restricted material was found or published.

**Status: AUTOMATED, NOT LEGALLY VERIFIED.** Relevance decisions on keyword-rejected texts, and the fields read from page images, come from an LLM (Claude) review. They are not a human or legal review.

## Results

| Item | Outcome |
| --- | --- |
| 4 HF-held SC originals | All 4 re-hash equal to their sidecars and are complete: they open, end with `%%EOF`, and every page has a usable text layer. Derived page-marked text and metadata were written to the new path `legal_knowledge/judgment_originals_derived/c12/{text,meta}/` (HF commit A). |
| 25 first-tier files | **18 ingested**: 6 Supreme Court and 12 Punjab and Haryana High Court. **0 duplicates.** **7 excluded as not relevant.** **0 excluded for markings.** All 18 are in one commit (HF commit B). |
| HF commit A | `af7f9d069e71314879c1756f914943d9d2ab777a` (parent `5524c3d9…`). 8 files. |
| HF commit B | `15bd03ccce7241b1294176fa7c19ab1c5dc109cb` (parent `af7f9d06…`). 47 files. |
| Verification | 55 of 55 files re-downloaded at their pinned commit match `STAGED_MANIFEST.csv`. For each commit, the tree diff against its parent shows only the staged paths added and nothing removed. |
| Validation | 18 of 18 new `data/meta` records validate against `schema/document.schema.json`. The 4 held-original records are valid except `raw_path` (see Conventions). |
| Acquisition | egazette TLS still fails verification (`ssl_verify_result=20`), so the run stopped there, fail-closed. Nothing else was attempted (`ACQUISITION_C12B.csv`). |

### Task 1: the 4 HF-only Supreme Court binaries

| doc_id | Source tier | Pages | Keyword relevance | Earlier record |
| --- | --- | --- | --- | --- |
| `sc-2025-chandrabhan-sudam-sanap-2025insc116` | official SC PDF (api.sci.gov.in) | 113 | rejected (0 hits); curated evidence-law source | none |
| `sc-2024-ravishankar-tandon-2024insc299` | official SC PDF | 24 | rejected (0 hits); curated evidence-law source | none |
| `sc-1963-ram-sarup-judis-3387` | official JUDIS typed rendition | 10 | relevant (78 hits) | complete page text at `legal_knowledge/full_text_working/v3.5/pages/DCLR-SC-1964-A11.jsonl`, 10/10 pages, not truncated |
| `sc-2016-ex-hav-mani-ram-bhaira-ca4409-2011` | **third-party mirror** (virendersinghkadian.com), parity with the official copy not tested | 15 | relevant (26 hits) | complete page text at `.../DCLR-SC-2016-L04.jsonl`, 15/15 pages |

None of the 4 had a `data/meta` or `data/text` record. They were matched by sha256, doc_id, neutral citation and case number.

### Task 2: the 25 first-tier files (`INGESTION_LOG.csv`)

Every file passed the following checks:
- **SHA-256** equals both the acquisition manifest and the crawler-logged value.
- **Host** is allow-listed.
- **URL** equals the crawler's `source_url`.
- **Request log** has one HTTP 200 row for it.
- **Structure**: the file opens and ends with `%%EOF`.

**Duplicate detection.** Nothing matched. The comparison ran against all 4,327 `data/meta` records at `ad77758d` and the full HF hash ledger at `5524c3d9`, using:
- sha256;
- doc_id;
- neutral citation;
- normalised case number;
- court, date and party name.

So no aliases were registered. The three Union of India writs of 21-22 Nov 2024 (CWP-16812, 16371, 16643/2024) are separate judgments: they have different case numbers, service facts and PHHC citation numbers.

**Relevance**, applying `CLAUDE.md` stage 3:
- All 25 have 0 keyword hits. The crawler had excluded each of them for this reason.
- **13 SC.** Each has a readable text layer. An LLM review of the text kept 6 that concern armed-forces service law:
  - J. Kumar: seniority;
  - Parthasarathy: premature retirement;
  - Satbir Singh: discharge;
  - Khajoor Singh: Art. 226 jurisdiction;
  - Avtar Singh Sekhon: promotion;
  - D.D. Joshi: Army Instruction 78/78.

  It excluded 7:
  - civilian employees: V.K. Rajan, Gopalakrishna Pillai, J.N. Sinha;
  - general Government-accommodation rules: Hingorani;
  - a criminal trial under the IPC and the PC Act: I.C. Lala;
  - Income-tax cadre seniority: Ashok Kumar Sawhney;
  - a book-publishing arbitration: Man Mohan Sharma.

  The reasons are in `inputs/REVIEW_DECISIONS.csv`. The ingested 6 carry `relevance.status = relevant`, `hits = 0`, a note, and `field_provenance.relevance = llm`.
- **12 P&H.** The text layer is unusable: under 10% of the non-space characters are letters, because the font has no Unicode map. Every page was read from page images instead. Each file is a Division Bench writ petition against an Armed Forces Tribunal order, which is within the brief's scope ("Writs against AFT orders"). Their records say `relevance.status = not_checked`, `needs_ocr = true`, `text_quality = suspect`, and no text file was written. This follows the brief: bad text is never kept.

**Markings.**
- **Text-layer scan:** used the C12 term list and line heuristic. The only hits were in running text: "secret sources" in Chandrabhan, and "Annual Confidential Reports" in J. Kumar.
- **Visual check:**
  - all 77 pages of the 12 P&H files, on contact sheets, plus page 1 at about 94 dpi;
  - page 3 of Man Mohan Sharma, which has no text layer.

  No access marking was found. **Limit:** a very faint marking could be missed on the low-resolution contact sheets.

### Finding: crawler false negatives

`pipeline.extract.reads_as_english` accepts the P&H files because their e-signature block ("I attest to the accuracy…") is English. The relevance stage then rejected their garbled text as "no military keyword" and **deleted** them. All 12 P&H T1 files here are such false negatives. The 562 P&H T1 titles, and the 75 corpus records that already need OCR or have suspect text, are probably affected the same way. This tool adds a per-page letter-share test (< 0.5 = no usable text). The pipeline itself was not changed. A fix belongs in `pipeline/extract.py` and `pipeline/judgments.py`, so that "not_checked" is used instead of deletion.

## Coverage before and after (`COVERAGE_BEFORE_AFTER.csv`, overlay `RECONCILIATION_UPDATE_C12.csv`)

| Indicator | Before | After |
| --- | --- | --- |
| Judgment metadata records | 4,259 | 4,277 |
| — SC / P&H / Delhi / J&K / Allahabad | 368 / 1,215 / 1,957 / 410 / 309 | 374 / 1,227 / 1,957 / 410 / 309 |
| Distinct judgment files | 3,951 | 3,969 |
| Distinct judgments (C11 identity + new, automated) | 3,625 | 3,643 |
| Complete / incomplete judgment files in `data/` | 3,932 / 19 | 3,950 / 19 |
| C11 INCOMPLETE_23 list unresolved | 23 | 19 (4 held SC originals resolved) |
| Records needing OCR or with suspect text | 75 | 87 |
| T1 titles held (of 1,790) | 0 | 18 (SC 6 of 47; P&H 12 of 562) |
| T1 titles acquired and reviewed | 0 | 25 (7 not relevant) |

The frozen C10 and C11 outputs were not edited. `RECONCILIATION_UPDATE_C12.csv` is an overlay with one status change per file.

## Conventions used and why

- **Manifests.** Additive files are in `data/manifest_additions/`:
  - `c12_2026-11-24_manifest.csv` and `_raw_manifest.csv` (same columns as the base files);
  - `_SHA256SUMS`;
  - `_excluded_overrides.jsonl`, which lists the 18 sha256 values in `data/excluded_judgments.jsonl` that are now ingested;
  - a `README.md` that defines the view: base file plus additions, applied in date order.

  `pipeline/records.py` rewrites the manifests on every local run. That is not a non-destructive HF update, and no snapshot or change-list mechanism exists on HF yet. The additive convention therefore follows the governance rule directly: never rewrite in place. No `_relations.jsonl` was written because no new `cites` edges were found.
- **Held originals.** Their derived files were written beside the held-original layer, not into `data/`, for three reasons:
  1. The instruction allowed uploading only derived files. A `data/` record needs its bytes under `data/raw/` (schema pattern on `raw_path`).
  2. Two of the four fail the corpus keyword filter. They are curated evidence-law sources.
  3. One is a non-official mirror.

  Their `raw_path` points to the HF held original. This is the only schema deviation, and `VALIDATION.csv` checks every other field. Registering them in `data/` needs an owner decision to copy the held bytes to `data/raw/sci/<yyyy>/` (no new content).
- **Raw path year and doc_id.** Both follow the crawler: the year is the open-data partition year from the URL, and the doc_id is the crawler-logged one. For SC, the neutral citation comes from the crawler-logged doc_id (`…1982insc33` → `1982 INSC 33`). For P&H, the neutral citation (2023-2024 only), judges and bench were read from page images and marked `llm`. Outcome is `null` throughout.

## Tool and records

```
python -I -B tools/judicial_recovery_c12.py build            # stage files + write records (no network)
python -I -B tools/judicial_recovery_c12.py --check          # rebuild and compare records byte for byte; check VERIFICATION vs STAGED/HF_COMMITS; SHA256SUMS
python -I -B tools/judicial_recovery_c12.py --check --online # also re-download every recorded path at its pinned commit
python -I -B tools/judicial_recovery_c12.py upload --commit A|B
python -I -B tools/judicial_recovery_c12.py verify           # writes VERIFICATION.csv
```

| File | Content |
| --- | --- |
| `INGESTION_LOG.csv` | 29 rows: the 4 held originals plus the 25 files, with every check and the action taken |
| `STAGED_MANIFEST.csv` | Every HF path written, with SHA-256 and bytes. This is the independent git manifest. |
| `HF_COMMITS.csv` | Commit ids, parents, file counts |
| `VERIFICATION.csv` | Per-file re-download hash at the pinned commit, plus the tree diff |
| `VALIDATION.csv` | Schema validation of every new metadata record |
| `COVERAGE_BEFORE_AFTER.csv`, `RECONCILIATION_UPDATE_C12.csv` | Coverage indicators and the overlay |
| `ACQUISITION_C12B.csv` | Task 5 network attempts |
| `inputs/REVIEW_DECISIONS.csv` | LLM relevance decisions and the fields read from page images |
| `inputs/held_original_sidecars/` | Copies of the 4 HF sidecars at `5524c3d9` |

**Inputs.**
- C12 acquisition: manifest, request log and `sources.yaml` snapshot.
- C11 `RE_ACQUISITION_MANIFEST.csv`, `EXCLUDED_RANK_SUMMARY.json`, `IDENTITY_SUMMARY.json` and `INCOMPLETE_23_RECOVERY_PLAN.csv`.
- C12 HF ledger and candidates.
- Corpus `ad77758d` from `/home/user/c7`.
- Bytes in the session scratchpad (`c12_acquired/`, `hf_retrieved_c12/`).

**Reused code:**
- `pipeline.extract`: page text, language test, marking rule;
- `pipeline.judgments`: keywords, classification, statute references;
- `pipeline.schemas`.

**Versions:** Python 3.13.18, PyMuPDF 2.1, huggingface_hub 0.36.0 (the venv version; `requirements.txt` pins 2.4.0), jsonschema 4.26.0, PyYAML 6.0.4. Worktree base `dfe733e6`.

`--check` needs the scratchpad bytes. If they are cleared, the source PDFs can be re-obtained from HF commit B (`data/raw/...`) and the held originals from their HF paths.

## Open items for the owner

1. OCR the 12 P&H files: no Tesseract is installed, and no system package was installed. Then run the keyword pass.
2. Re-check the crawler's deleted P&H and Delhi exclusions for garbled text layers.
3. Decide whether to register the 4 held originals in `data/`.
4. A legal adviser should confirm the 6 LLM-kept and 7 LLM-excluded SC relevance decisions.
5. egazette TLS chain; archive.org storage-node allow-listing.

## Coordinator additivity check (independent of this workstream's author)
The coordinator compared the full HF trees at `5524c3d9` and `15bd03cc`:
- 55 paths added;
- 0 removed;
- 1 changed: `.gitattributes`.

HF appends LFS tracking rules to `.gitattributes` automatically when binaries are added; it grew from 401,428 to 402,898 bytes. No source or record file was modified. The dataset is still private.
