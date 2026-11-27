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
| PR #76 local reconciliation | `codex/c16-local-corpus-reconciliation` head `7ba91ec4` (methodology v3; read with `git show` only), outputs outside git | identities (one per binary), admissions, folder/file-name classifications, local subject taxonomy, local exclusion receipts | **implemented** `from_pr76_inventory`, `classify_path`, `local_subject_nodes` | none; output is a PARTIAL exchange, never importable as is (section 6) |
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

## 6. PR #76 local reconciliation (read-only; current head `7ba91ec4`, methodology v3)

PR #76's corrective commit `7ba91ec4` ("correct Cycle 16 image-aware reconciliation") changed the inventory:
- DOCX image occurrences are inventoried in reading order (`embedded_images[]`: sequence, `occurrence_id` `body:<rel id>:<seq>`, relationship id, archive path, image sha256, size, dimensions, format, perceptual hash as a signal only, `ocr_state: REQUIRED`);
- an ordered content hash includes the image hashes;
- normalised-text equality no longer creates `VERIFIED_ALTERNATE_COPY` (it becomes IDENTITY_UNRESOLVED);
- restriction markers are scanned over the full native text;
- derivatives are **withheld** until page and image access-marking screening completes (`derivative_withheld_reason`);
- filename provision lists are parsed as candidates, and ranges are not expanded (`filename_legal_metadata`);
- the manifest names a collection, not an absolute path.

Final counts: 1,965 files (732 PDF, 1,233 DOCX), 517 DOCX with images, 6,735 image occurrences, 579 documents needing OCR, 1 restricted hit. Nothing is application-eligible. Codex is still running OCR; this adapter neither waits for nor interferes with it.

`adapters.from_pr76_inventory(rows, collection=..., corpus_generation_id=...)` returns `{identities, admissions, relationships, taxonomy, receipts}`:

| Row field | C16 |
| --- | --- |
| `sha256` | **one identity and one admission per binary**; every row with that hash adds an `observation` (path, inventory id) |
| `detected_format` | PDF, DOCX, DOC, RTF or TXT as detected; **anything else is UNKNOWN / `application/octet-stream` / UNRECOGNISED_FORMAT / UNSUPPORTED_FORMAT, never PDF** |
| `page_count` | PDFs: the physical count; DOCX: `null` (a flow document; never page 1) |
| `embedded_images[]` (v3) | `embedded_images[]` with `image_sequence_id IMG:<sha>:<seq>`, `location.occurrence_ref` = PR #76 `occurrence_id`, relationship id, archive path, size, dimensions, mime from the format (unknown → `application/octet-stream`); `ocr_state REQUIRED` → QUEUED; DONE only with an OCR derivative hash; representation WORD_WITH_EMBEDDED_IMAGES (images present) or WORD_NATIVE_TEXT (inventoried, none) |
| v2 rows (no image inventory), DOC, RTF | WORD_IMAGES_NOT_INVENTORIED, images UNRESOLVED |
| `derivative_withheld_reason` | no text derivative; decision HELD_ACCESS_MARKING_REVIEW |
| `ocr_required_pages`, `ocr_required_images`, queued images | HELD_OCR_REQUIRED; when OCR is done, the caller passes the pinned `ocr_config` (engine, version, languages, DPI, PSM, preprocessing, config hash) and the derivative carries it |
| `filename_legal_metadata` / file name and folders | rules 1.2 (contract section 8.3): leaf-folder subject with the full hierarchy; provision folders; one candidate per listed number; AR = Army Rules 1954 in this collection (owner decision D1); bare AFT = the forum, so no provision (D2), while an explicit AFT Act reference gives `PROV:AFT-2007`; ranges kept as unresolved candidates; case-number prefixes ignored |
| `restricted` or `ACCESS_RESTRICTED` | **a local exclusion receipt only** (`{record_kind: local_exclusion_receipt, sha256_prefix, reason, exportable: false}`): no identity, path, file name, admission or classification is exported |
| integrity | DECLARED_HASH_ONLY, so **G01 NOT_RUN** (a PR #76 hash is not re-verified) |
| NEW_DOCUMENT | provisional: **G09 NOT_RUN** and decision HELD_INTEGRITY_UNVERIFIED (or a more specific hold); never ADMITTED |
| relevance `true` | **G08 NOT_RUN** (an automated signal is not an assessment); `false` → FAIL and REJECTED_NON_RELEVANT |

**Disposition to decision:**

| PR #76 disposition | Decision |
| --- | --- |
| EXACT_DUPLICATE | REJECTED_EXACT_DUPLICATE (G09 PASS with the canonical match as evidence) |
| VERIFIED_ALTERNATE_COPY (v2 only), PROBABLE_DUPLICATE, IMPROVED_SOURCE_COPY, HISTORICAL_RECOVERY_MATCH, IDENTITY_UNRESOLVED | HELD_IDENTITY_UNRESOLVED |
| NEW_DOCUMENT | HELD_ACCESS_MARKING_REVIEW, HELD_OCR_REQUIRED or HELD_EXTRACTION_INCOMPLETE as the row's evidence dictates, else HELD_INTEGRITY_UNVERIFIED |
| RELEVANCE_UNRESOLVED | HELD_RELEVANCE_UNRESOLVED |
| NON_RELEVANT | REJECTED_NON_RELEVANT |
| ACCESS_RESTRICTED | local exclusion receipt only |
| INTEGRITY_FAILURE | QUARANTINED_INTEGRITY |
| UNSUPPORTED_FORMAT, unknown format | UNSUPPORTED_FORMAT |

The adapter output validates as a **partial** exchange (`exchange_issues(..., mode="partial")`). To become a strict, importable generation the producer must:
1. add `GENERATION.json` with pinned inputs, counts and hashes;
2. merge the provision taxonomy;
3. run the gates with evidence (re-download hash verification for G01, register, marking screening including image OCR, relevance, duplicate resolution);
4. issue new admission revisions.

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
