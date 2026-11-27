# C16 compatibility matrix: existing corpus sources → `mimamsa-corpus-contract/2.0`

Companion to [C16_CORPUS_INTEGRATION_CONTRACT.md](C16_CORPUS_INTEGRATION_CONTRACT.md).

**Adapters.** Those marked **implemented** are in `app/contract/mimamsa_contract/c16/adapters.py` and tested in `app/contract/tests/test_c16_contract.py`. All adapters are pure and deterministic. None promotes a state: unknown values become UNRESOLVED or the most conservative value.

## 1. Summary

| Source | Where | Maps to | Adapter | Breaking changes |
| --- | --- | --- | --- | --- |
| Contract v1 `document` | `app/contract/schemas/v1/document.schema.json`; bundles `data/documents.jsonl` | `document_identity` (sidecar, same `doc_id` and `sha256`) | **implemented** `identity_from_v1_document` | none |
| Contract v1 `derived_text` | `derived_text.schema.json` | `document_identity.text_derivatives[]` (same `derivative_id` form) | **implemented** (inside the above) | none |
| Contract v1 `page_anchor` (PageKey/SpanKey) | `common.schema.json#/$defs/page_anchor` | `evidence_anchor`, and back | **implemented** `anchor_from_v1_page_anchor`, `anchor_to_v1_page_anchor` (round trip tested against the v1 schema) | none; anchors without a source page do not project (by design) |
| Contract v1 `candidate` (graph_edge) | `candidate.schema.json` | `corpus_relationship` for 6 relations; others stay v1 | **implemented** `relationship_from_v1_candidate` | none |
| B1 generations and the sample site | `app/importer`; `generations/<id>/generation.json`, `records/*.jsonl`, `derived/`, `research/`; `app/b1/sample/SAMPLE_MANIFEST.json` | unchanged; C16 files join by (doc_id, sha256) under `generations/<id>/corpus-v2/` | importer extension (consumer requirements I1–I6); no record adapter needed | none |
| C15 graph | `app/b1/src/Mimamsa.Core/Graph/*`, ADR-0006, `C15_GRAPH_API.md` | relationships → edges in the same tables; taxonomy → nodes | **implemented** projection `graph_projection`, `c16_edge_id`; .NET builder step is consumer work (G1–G7) | additive: 2 node kinds and 5 edge types proposed |
| C13 A5 graph (native) | `legal_knowledge/audit_work/C13-A5-GRAPH/schema/graph_*.schema.json`, `graph/` | via its contract-v1 export (`contract_v1/candidates_graph_edges.jsonl.gz`) → v1 candidate → relationship | **implemented** (two steps); native-format direct adapter not needed | none |
| C13 A4 statutory | `C13-A4-STATUTORY/schema/provision_version.schema.json`, `records/PROVISION_VERSIONS_C13.jsonl` | unchanged as signed research aids (`research/a4_provision_versions.jsonl`); provision ids feed `taxonomy_node` (GRAPH_PROVISION) | mapping rule (section 4); no record conversion | none |
| AUTH-LEDGER | `legal_knowledge/audit_work/AUTH-LEDGER/schema/ledger_entry.schema.json` | **not mapped.** `legally_validated` needs an `AP-` approval and is refused at ledger v0 | none (deliberately) | none |
| Root corpus schemas (data/meta 0.2.0) | `schema/document.schema.json`, `relation.schema.json`, `section.schema.json`, `correspondence.schema.json`; HF `data/meta/<doc_id>.json` | via the existing v1 mapping (contract README §7, `app/b1/build/build_sample.py`) then `identity_from_v1_document`; `topics` → `classified_under_subject` (AUTOMATED_CLASSIFIER) | composition of existing mapping + **implemented** adapter; topics adapter **not implemented** (small) | none |
| PR #76 local reconciliation | `codex/c16-local-corpus-reconciliation:legal_knowledge/audit_work/C16-LOCAL-CORPUS/c16_reconcile.py` (outputs outside git) | identity + admission + folder/file-name classifications | **implemented** `from_pr76_inventory_row`, `classify_path` | none; outputs conservative (see section 6) |
| Cycle 15 candidate package v7 | HF dataset branch `cycle15-candidates`, namespace `legal_knowledge/candidates/cycle15/v7`, revision `217020db…`; receipt in git (section 7) | anchors + unresolved citation/provision relationships; identity via HF meta | **implemented** `from_v7_record` | none |
| HF dataset metadata | `hariomahlawat/mimamsa-corpus` (private), `data/meta/*.json`, `data/raw/<source>/<yyyy>/<sha>.<ext>`, `data/text/<doc_id>.txt` | `provenance.acquisition.hf` (repo, revision, path); identities via v1 | v1 path (above) | none |

## 2. Contract v1 and the B1 generation format

| v1 field | C16 field | Rule |
| --- | --- | --- |
| `doc_id` | `doc_id` | identical; never renamed in place (`previous_doc_ids` for later readable ids) |
| `source_copy.{sha256, bytes, vault_path}` | `source_copy.*` | identical |
| `source_copy.mime_type` | `source_copy.mime_type` + `detected_format` | C16 adds `application/msword`, `application/rtf` (v1 cannot carry; open question Q1) |
| `source_copy.page_count` | `source_copy.page_count` | `null` for flow documents in C16 (v1 may hold a generated count) |
| `source_copy.completeness` COMPLETE / TRUNCATED_AT_SOURCE / UNOPENABLE / NOT_CHECKED | `representation.completeness` | COMPLETE → NOT_CHECKED (byte vs work completeness, contract 6.2); others pass through. C16 PARTIAL_EXTRACT → v1 NOT_CHECKED |
| `text_method` pdf_text / ocr / mixed / html | `representation_kind` NATIVE_DIGITAL_PDF / SCANNED_PDF / MIXED_PDF / HTML_PAGE | v1 DOCX → WORD_IMAGES_NOT_INVENTORIED until inventoried |
| `judicial.judgment_identity_id` | `work_identity.judgment_id` | null → UNRESOLVED |
| `judicial.case_numbers` | `work_identity.proceeding_numbers_as_printed` | as printed |
| `provenance` | `provenance.acquisition` | same object (`$ref` to v1 schema) |
| `status_axes` | `status_axes` (optional copy), `integrity.source_integrity` | `source_authenticity.policy_v1.carrier_provenance` → `provenance.carrier_provenance` |
| `restriction` | `restriction` | same object |
| derived_text `pipeline.{name,version}`, `text_sha256` | `text_derivatives[].{pipeline_name, pipeline_version, derivative_text_sha256}`; `derivative_id = <doc_id>@<name>/<version>` | same form as importer `did()` and `GenerationStore` |
| derived_text `pages[].method` | `methods[]` (pdf_text → NATIVE_TEXT_LAYER, ocr → OCR_PAGE_IMAGE, html → HTML) | |
| derived_text `quoting_permitted` | `quoting_permitted` | AND with C16 OCR/reliability rules; the adapter emits false until TextQuality has assessed the text |
| derived_text `passages[].passage_id` | `evidence_anchor.text_span.passage_id` | same pattern `p<page>-<n>` |
| `page_anchor` | `evidence_anchor` | PageKey ⇄ SOURCE_PHYSICAL_PAGE; SpanKey fields kept only when bound (v1 SPAN_UNBOUND rule) |
| candidate `graph_edge` relations CITES_PROVISION, INTERPRETS_PROVISION, CITES_JUDGMENT, FOLLOWS_PROPOSITION, DISTINGUISHES_PROPOSITION, OVERRULES_OR_LIMITS_PROPOSITION | categories cites_provision, interprets_provision, refers_to_judgment, follows, distinguishes, overrules | status AUTOMATED_CANDIDATE_NOT_VERIFIED → CANDIDATE; DOCUMENTARY_CHECKED (+`review_ref`) → DOCUMENTARY_CHECKED; REJECTED_ON_REVIEW → not converted |
| other candidate relations (AMENDS_*, OMITS_*, REPEALS_*, RE_ENACTED_AS, COMMENCES, SAVES_OR_TRANSITIONS, IMPLEMENTS, SUPERSEDES_*, UPLOAD_*, PRESCRIBES_*) | none (stay v1 candidates / A4 / C14 inputs to GraphBuilder) | out of C16 relationship scope; unchanged |
| `reviewed_record` (`RV-`), `approval_record` (`AP-`) | `review_ref`, `approval_ref` | resolved by the consumer against the same bundle (v1 rules) |
| release `release_id`, `release_sequence` | unchanged; C16 adds `corpus_generation_id` (producer build) | a release pins one or more corpus generations (producer requirement D5) |
| generation `item_document`, `servable`, `candidate_evidence` | unchanged | C16 records for items not servable are ignored |

## 3. C15 graph

| C15 item | C16 |
| --- | --- |
| `NodeKind` instrument / provision / judgment / unresolved_reference | `INSTCODE:` / `PROV:` / `JUD:` / `REF:` (same ids; INSTCODE resolved to `INST:<family>` by the consumer) |
| `NodeKind` provision_version, procedural_requirement, form, competent_authority | not produced by C16 (A4, C14, reserved) |
| new | `subject` (`SUBJ:`), `chapter` (`CHAP:`): **proposed** |
| `EdgeType` CITES_PROVISION, CITES_JUDGMENT, FOLLOWS_PROPOSITION, OVERRULES_OR_LIMITS_PROPOSITION | reused |
| new | CLASSIFIED_UNDER_SUBJECT, CLASSIFIED_UNDER_CHAPTER, ASSOCIATED_WITH_PROVISION, INTERPRETS_PROVISION, DISTINGUISHES_PROPOSITION: **proposed** (the last two are already in architecture §5 and the v1 enum) |
| `Verification` (5 values), `BuilderValues` (3) | identical enumerations (`graph_verification`, `producer_verification`); test parses `GraphModel.cs` and fails on drift |
| `ReviewState` UNREVIEWED; `graph_edge_reviews` | DOCUMENTARY_CHECKED and LEGAL_REVIEWED become review rows, never edge values |
| `GraphEdge.Temporal*` | `temporal_scope` (same four fields) |
| `GraphEdge.Uncertainty`, `HasLegalEffect` | `uncertainty`, `has_legal_effect` |
| `GraphIds.EdgeId` | unchanged for existing origins; C16 origins use `c16_edge_id` (relationship id discriminator) |
| `GraphIds.Reference(raw)` | identical (`c15_reference_id`, tested formula) |
| `GraphIds.BaseSection` | provision numbers in `PROV:` ids are base numbers (pattern enforced) |

## 4. C13 A4 / A5 and older root schemas

| Source | Rule |
| --- | --- |
| A5 native node ids `INS:`, `PROV:`, `PV:`, `JUD:`, `REF:` … | A5 is imported only through its contract-v1 export (README 1a), whose targets already use C15 forms (`PROV:AA-1950:s.69`, `JUD:JG-<12 hex>`). The native `INS:` prefix is **not** C15 `INST:` and is not accepted directly |
| A5 `verification_state` AUTOMATED_CANDIDATE_NOT_VERIFIED / REVIEWED_AI_DOCUMENTARY_NOT_LEGAL_VALIDATION / PROPOSED_NOT_APPLIED | CANDIDATE / DOCUMENTARY_CHECKED review row only with an independent v1 `reviewed_record`, otherwise CANDIDATE / not converted |
| A4 `provision_version` (family `AA1950`, provision `s.75`) | taxonomy PROVISION `PROV:<GraphIds.CodeFromA4Family(family)>:<prefix>.<base>`, basis GRAPH_PROVISION; versions remain research aids |
| root `relation.schema.json` types amends / supersedes / repeals / overrules / follows / distinguishes / cites / implements; confidence extracted / llm_proposed / human_verified | as architecture §5: follows → follows, distinguishes → distinguishes, overrules → overrules (proposition-scoped, `proposition_ref` UNRESOLVED), cites → cites_provision / refers_to_judgment; statutory types stay outside C16. extracted, llm_proposed → CANDIDATE; human_verified → DOCUMENTARY_CHECKED **only** with a reviewed_record |
| root `section.schema.json` (`act-army-1950#s69`, `amendment_history`) | taxonomy PROVISION (`PROV:AA-1950:s.69`) and A4; section `doc_id` (`#s69`) remains the v1 section-level id |
| root `document.schema.json` `topics[]` | `classified_under_subject` → `SUBJ:<topic>`, basis AUTOMATED_CLASSIFIER, CANDIDATE (adapter not implemented; small) |
| root `document.schema.json` `status` | display-only `corpus_status` (v1); never a legal axis, never a relationship |
| `correspondence.schema.json` | C14 correspondence → existing `RE_ENACTED_AS` (unchanged) |

## 5. HF dataset metadata

| HF item | C16 |
| --- | --- |
| `data/raw/<source>/<yyyy>/<sha256>.<ext>` | `source_copy.sha256`; `provenance.acquisition.hf.{repo, revision, path}` (40-hex revision) |
| `data/meta/<doc_id>.json` (schema 0.2.0) | v1 document (existing mapping) → `identity_from_v1_document` |
| `data/text/<doc_id>.txt` (`[[page N]]`) | `text_derivatives[]` with pagination SOURCE_PHYSICAL |
| `cycle15-candidates` branch | section 7 |
| Receipts in git (`*-hf-receipt.json`) | `processing_history` ACQUIRE/VALIDATE steps with the receipt path as `note` |

HF is read only through pinned revisions, and no token is printed. This checkpoint read nothing from HF: the matrix rests on committed receipts, manifests and code.

## 6. PR #76 local reconciliation (read-only via `git show`)

**Output files** (outside git, at `E:\Mimamsa-Data\local-corpus-reconciliation`):
- `LOCAL_INVENTORY.jsonl` (one row per file);
- `SUBJECT_CLASSIFICATION.jsonl`;
- dispositions and CSV reports;
- `CANDIDATE_PACKAGE_MANIFEST.json` (`application_eligible=false`).

**Field mapping:**

| Row field | C16 |
| --- | --- |
| `sha256`, `size_bytes`, `detected_format` | `source_copy` (format from magic bytes; `.doc` and `.rtf` need Q1) |
| `page_count` | PDFs: physical count. **DOCX: ignored**; PR #76 sets 1 for a DOCX, which is not a physical page |
| `relative_path`, `inventory_id` | `provenance.observations[]` (NFC, POSIX, collection `local:<name>`, never the drive root) |
| `original_folder_classification` | one `classified_under_subject` per folder component (C16-FOLDER-SUBJECT) |
| file name `AR 22, 23, 30 – …` | `associated_with_provision` per number (C16-FN-PROVLIST, CANDIDATE, abbreviation reading recorded) |
| `derivative_sha256`, `extraction_method` | `text_derivatives[]`: `pymupdf-native` → NATIVE_TEXT_LAYER, `docx-xml` → DOCX_XML; reliability `not_assessed`, quoting false |
| `ocr_required_pages` | PDF kind SCANNED_PDF / MIXED_PDF; admission HELD_OCR_REQUIRED |
| `candidate_document_type` | `work_kind` (identity_basis METADATA_CANDIDATE, CANDIDATE) |
| `metadata_candidate.case_numbers` | `proceeding_numbers_as_printed` (candidate) |
| `restricted` (marker text found) | admission HELD_ACCESS_MARKING_REVIEW, gate G04 FAIL. A detected marking is not an RM register entry; EXCLUDED_RESTRICTED needs an RM id |
| `normalized_text_sha256` groups | `alternate_copies` NORMALIZED_TEXT_IDENTICAL (CANDIDATE); never a merge |
| `source_provenance` "owner local collection; external source unverified" | `origin_status` ACQUIRED_COPY_ORIGIN_UNDETERMINED, carrier USER_SUPPLIED, integrity DECLARED_HASH_ONLY |

**Disposition to admission decision:**

| PR #76 disposition | C16 admission decision |
| --- | --- |
| EXACT_DUPLICATE | REJECTED_EXACT_DUPLICATE |
| VERIFIED_ALTERNATE_COPY | ADMITTED_AS_ALTERNATE_COPY (NORMALIZED_TEXT_IDENTICAL; needs the primary's sha, else HELD_IDENTITY_UNRESOLVED) |
| PROBABLE_DUPLICATE, IMPROVED_SOURCE_COPY, HISTORICAL_RECOVERY_MATCH, IDENTITY_UNRESOLVED | HELD_IDENTITY_UNRESOLVED |
| NEW_DOCUMENT | ADMITTED_AS_PRIMARY, but HELD_EXTRACTION_INCOMPLETE for Word files and HELD_OCR_REQUIRED where OCR is pending |
| RELEVANCE_UNRESOLVED | HELD_RELEVANCE_UNRESOLVED |
| NON_RELEVANT | REJECTED_NON_RELEVANT |
| ACCESS_RESTRICTED | HELD_ACCESS_MARKING_REVIEW |
| INTEGRITY_FAILURE | QUARANTINED_INTEGRITY |
| UNSUPPORTED_FORMAT | UNSUPPORTED_FORMAT |

Every PR #76 row maps to `application_eligible=false`. G03 (register), G05, G06 and G10 are NOT_RUN until the producer runs them.

**Known gap.** The independent review found that PR #76 never extracted or OCR'd Word documents with embedded screenshots. C16 represents this directly:
- every PR #76 Word file becomes `WORD_IMAGES_NOT_INVENTORIED`;
- its `embedded_images` is UNRESOLVED;
- gate G07 is NOT_RUN;
- the admission is HELD_EXTRACTION_INCOMPLETE.

Codex's separate fix should emit the image inventory (`embedded_images[]` with `image_sha256`, `IMG:` ids, OCR state) and OCR anchors. That turns these items into `WORD_WITH_EMBEDDED_IMAGES` or `WORD_NATIVE_TEXT`. No work is duplicated here.

## 7. Cycle 15 candidate package v7: found

**Where it is:**
- **Receipt:** `legal_knowledge/audit_work/C15-CORPUS-ENGINEERING/candidate-v7-hf-receipt.json`, on `origin/corpus/c14-collection-discovery-20261126` (`9837bb38`) and also carried by PR #76's branch.
- **HF location:** dataset branch `cycle15-candidates`, namespace `legal_knowledge/candidates/cycle15/v7`, revision `217020dbd969e14c2373697f4094fa00557962a6`, corpus snapshot `f8a46dfaec55…`.
- **Status:** `verified: true`, `application_eligible: false`.
- **Reconstruction counts:** 2,383 documents, 10,739 pages, 411 citation mentions.

**Contents:**
- `records.jsonl` (schema `mimamsa-c14-document-candidate-v1`, built by `build_candidates_v6.py`);
- `pages.jsonl.gz`;
- `search.sqlite` (FTS5);
- the repair artefacts.

| v7 field | C16 |
| --- | --- |
| `doc_id`, `original_sha256`, `derivative_sha256`, `hf_revision`, `page_count` | identity keys; `provenance.acquisition.hf.revision` |
| `page_text_sha256[]` | per-page check when re-deriving into the `[[page N]]` format |
| `citation_mentions[]`, `provision_mentions[]` `{page, start, end, text}` | `evidence_anchor` (SOURCE_PHYSICAL_PAGE, code-point offsets, the same convention as v1) + unresolved `refers_to_judgment` / `cites_provision` CANDIDATE relationships (implemented) |
| `case_number_mentions`, `coram_heading_mentions`, `disposition_phrase_mentions` | candidate cover metadata (not relationships); `final_disposition` null in v7 |
| `extraction_quality.state`, `empty_pages`, `derivative_lineage.out_of_scope_pages` | `text_derivatives[].coverage`; research basis COMPLETENESS_NOT_CHECKED |
| `relevance: unassessed`, `legal_authority: unreviewed`, `application_eligible: false` | admission HELD_RELEVANCE_UNRESOLVED; no promotion |
| `search.sqlite` | **not imported.** The app's index is rebuilt from verified derivatives (ADR-0007); see the knowledge release architecture |

**Derivative format caveat.** v7 derivatives are split by `\n\f\n`, or use `physical-page-v1` for repaired items. They are not the importer page format. A producer must re-emit `[[page N]]` derivatives whose per-page hashes match `page_text_sha256` before anchors become served SpanKeys. Until then, anchors bind to the v7 derivative hash and the consumer serves them page-only.
