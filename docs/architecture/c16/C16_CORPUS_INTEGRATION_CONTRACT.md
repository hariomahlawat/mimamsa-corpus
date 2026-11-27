# C16 corpus integration contract (`mimamsa-corpus-contract/2.0`)

- **Status:** proposed, Cycle 16 Tranche A checkpoint (WP01–WP03), **revised after the independent review of `4d476fab`** (findings C01–C07; disposition in section 15). For re-review. Not adopted, not frozen, not merged.
- **Base:** `legal-knowledge/v2.5-staging` at `c8fa5290`.
- **Scope:** the corpus-to-application exchange of document identity, evidence anchors, taxonomy, provision and judgment relationships, and admission decisions.
- **Not changed:** contract v1 (`app/contract/schemas/v1`), its validator, AUTH-LEDGER, acceptance oracles, corpus bytes, the B1 application.

| Artefact | Path |
| --- | --- |
| Schemas (draft 2020-12) | `app/contract/schemas/c16/`: `C16_SHARED_DEFINITIONS_SCHEMA.json`, `DOCUMENT_IDENTITY_SCHEMA.json`, `OCR_EVIDENCE_ANCHOR_SCHEMA.json`, `LEGAL_TAXONOMY_SCHEMA.json`, `PROVISION_JUDGMENT_RELATIONSHIP_SCHEMA.json`, `CORPUS_ADMISSION_SCHEMA.json` |
| Validator, canonical form, rules, adapters | `app/contract/mimamsa_contract/c16/` (`schemas.py`, `canonical.py`, `rules.py`, `adapters.py`) |
| Fixtures (synthetic) and their deterministic builder | `app/contract/fixtures/c16/` (`FIXTURES.json`, `positive/`, `negative/`, `build_fixtures.py`) |
| Test (runs in the existing CI contract job) | `app/contract/tests/test_c16_contract.py` |
| Compatibility matrix | [C16_COMPATIBILITY_MATRIX.md](C16_COMPATIBILITY_MATRIX.md) |
| Producer (Codex) requirements | [C16_PRODUCER_REQUIREMENTS.md](C16_PRODUCER_REQUIREMENTS.md) |
| Consumer (B1 application) requirements | [C16_CONSUMER_REQUIREMENTS.md](C16_CONSUMER_REQUIREMENTS.md) |
| Knowledge release architecture (WP06) | [C16_KNOWLEDGE_RELEASE_ARCHITECTURE.md](C16_KNOWLEDGE_RELEASE_ARCHITECTURE.md); schemas `KNOWLEDGE_RELEASE_MANIFEST_SCHEMA.json`, `KNOWLEDGE_ACTIVATION_RECORD_SCHEMA.json` |

## 1. Why a second contract version, and why it is an extension

Contract v1 binds one logical document (`doc_id`) to one source copy (`sha256`). It carries page and passage anchors, candidates and seven status axes. It was designed for crawled official PDFs. The owner's local collection (PR #76: 1,965 files, 732 PDFs and 1,233 non-PDFs) brings in kinds of evidence that v1 cannot describe honestly:

- Word documents whose judgment text is in pasted screenshots;
- locally reconstructed searchable PDFs;
- partial extracts and multi-judgment compilations;
- flow documents with no physical pages;
- classification by folder and file name, such as "AR 22, 23, 30 – …".

The legal graph (C15, ADR-0006) also needs a typed, provenance-bearing feed for taxonomy and provision associations.

Contract 2.0 is **additive**:
- every v1 record, id and rule stays valid;
- C16 records are **sidecars** keyed by v1 identities (`doc_id`, `source_copy.sha256`, `derivative_id`, `passage_id`);
- a v1-only importer ignores them.

Where a v1 field cannot carry a C16 fact (for example `PARTIAL_EXTRACT`), the v1 projection takes the **more conservative** value, and the fact lives in the sidecar (section 12).

## 2. Identity layers

```
 legal work           judgment_id / instrument_code  -> C15 node JUD:<doc_id> | INST:<family> (via INSTCODE:<code>)
   rendition          ISSUED_ORIGINAL | CORRECTED | REPORTED | TRANSLATION | CONSOLIDATION | GAZETTE_FACSIMILE
     corpus document  doc_id (v1, stable)                                    -- document_identity.doc_id
       binary copy    sha256 of exact bytes (v1 source_copy, vault path)     -- document_identity.source_copy
         representation  kind, origin, scope, completeness                    -- document_identity.representation
         embedded image  image_sha256 (content) + IMG:<copy sha>:<seq> (position)
         text derivative <doc_id>@<pipeline>/<version> + derivative_text_sha256
           passage        p<page>-<n> within one derivative (v1)
             anchor       ANC-<24 hex>: original, representation, derivative, image, locator, span, bbox, method, quality
```

Each layer is a different identity. **Never** equate:
- a file hash with a judgment;
- a `doc_id` with a judgment;
- a judgment with a proceeding;
- a reconstruction with its original;
- a page of a reconstructed PDF with a page of the source.

### 2.1 Where each required item lives

| Contract item | Representation | Field status |
| --- | --- | --- |
| Original document identity | `work_identity.rendition` (issued form) plus `representation.origin_status` (whether these bytes claim to be the carrier-issued copy) | rendition OPTIONAL; origin_status MANDATORY |
| Binary copy identity | `source_copy.sha256`, `bytes`, `detected_format`, `vault_path` (v1 identity, unchanged) | MANDATORY |
| Legal instrument and judgment identity | `work_identity.work_kind`, `judgment_id`, `instrument_code`, `graph_node_ref`, `identity_basis`, `identity_verification` | MANDATORY; ids UNRESOLVABLE |
| Complete versus partial | `representation.content_scope` (WHOLE_WORK, EXTRACT, COMPILATION, UNDETERMINED), `completeness`, `extract_scope`, `members` | MANDATORY |
| Original versus reconstructed | `representation.origin_status`, `representation_kind`, `reconstructed_from_sha256`, `reconstruction_method`, `page_mapping` | MANDATORY; reconstruction fields conditional |
| Text derivative identity | `text_derivatives[].derivative_id` (`<doc_id>@<pipeline>/<version>`, as importer and GenerationStore), `derivative_text_sha256`, `pagination_basis`, `methods`, `ocr_config` | MANDATORY (array may be empty) |
| Embedded image identity | `embedded_images[]`: `image_sha256` (content) and `image_sequence_id` `IMG:<container sha256>:<seq>` (position), `location`, `ocr_state` | UNRESOLVABLE |
| Physical page and image-sequence anchors | `evidence_anchor.locator` (kinds SOURCE_PHYSICAL_PAGE, RECONSTRUCTED_PAGE, GENERATED_SEGMENT, IMAGE_SEQUENCE, TEXT_FLOW) | MANDATORY |
| Passage identity | v1 `passage_id` within one derivative; the full key is (source sha256, pipeline name, pipeline version, derivative sha256, passage_id), i.e. v1 SpanKey | OPTIONAL in `text_span` |
| Legal taxonomy | `taxonomy_node` records | section 8 |
| Statutory provision associations | `corpus_relationship` with categories `associated_with_provision`, `cites_provision`, `interprets_provision` | section 7 |
| Judicial citation relationships | categories `refers_to_judgment`, `follows`, `distinguishes`, `overrules` | section 7 |
| Provenance and processing history | `provenance.acquisition` (the v1 provenance object), `carrier_provenance`, `observations[]` (every path the bytes were seen at), `processing_history[]` (operation, tool, config hash, input and output hashes) | MANDATORY |
| Integrity and access restrictions | `integrity.source_integrity` (v1 axis values), `restriction` (the v1 object); the RM register overrides both | MANDATORY |
| Research eligibility | `research_eligibility`: `state`, `quoting_permitted`, `source_page_citation_permitted`, `whole_work_claims_permitted`, `graph_evidence_permitted`, `basis[]` | MANDATORY |
| Legal verification and approval states | `status_axes` (the seven v1 axes, unchanged); relationship `verification` (C15 vocabulary); `legally_validated` overlays citing an `AP-` approval | see section 7.3 |
| Corpus generation and release identity | `corpus_generation_id` `CG-<yyyymmdd>-<label>-<8 hex>` (producer side); v1 `release_id` and `release_sequence` (bundle and site side); `contract` `mimamsa-corpus-contract/2.<minor>` | MANDATORY |

## 3. Field status: MANDATORY, OPTIONAL, UNRESOLVABLE

- **MANDATORY:** present and resolved.
- **OPTIONAL:** may be absent.
- **UNRESOLVABLE:** must be present, holding either a value or the explicit marker `{"unresolved": "<REASON>", "note": …}`. The reasons are `NOT_DETERMINED`, `CONFLICTING_EVIDENCE`, `SOURCE_UNAVAILABLE`, `NOT_YET_PROCESSED` and `AMBIGUOUS_REFERENCE`.

**`null` vs UNRESOLVED.** `null` means **not applicable or not printed**. For example, `page_count` is `null` for a DOCX, and `printed_page_label` is `null` when none is printed. `null` never means "unknown"; unknown is UNRESOLVED.

This refines the v1 rule ("fields the producer cannot fill are null, never guessed"). v1 fields keep their v1 meaning.

The schemas mark every field in its `description` and through `required`. The tables below summarise them (M = MANDATORY, O = OPTIONAL, U = UNRESOLVABLE, C = conditionally mandatory).

### 3.1 `document_identity`

| Field | Status | Notes |
| --- | --- | --- |
| `contract`, `record_kind`, `doc_id`, `corpus_generation_id` | M | `doc_id` is the v1 id. New local items get `local-<sha256 first 16 hex>` until a readable id is assigned; a later readable id lists the old one in `previous_doc_ids` (O) |
| `source_copy.{sha256, bytes, mime_type, detected_format, physical_pagination}` | M | Format detected from the bytes, never from the extension |
| `source_copy.page_count` | U | `null` for flow documents |
| `source_copy.vault_path` | O | v1 pattern |
| `representation.{representation_kind, origin_status, content_scope, completeness}` | M | |
| `representation.completeness_basis` | C | Required when COMPLETE |
| `representation.reconstructed_from_sha256`, `reconstruction_method`, `page_mapping` | C | Required when LOCALLY_RECONSTRUCTED |
| `representation.extract_scope` | C | Required for EXTRACT |
| `representation.members` | C | Two or more for COMPILATION; none otherwise |
| `work_identity.{work_kind, graph_node_ref, identity_basis, identity_verification}` | M | `graph_node_ref` U |
| `work_identity.judgment_id` | C, U | Required for JUDGMENT/ORDER |
| `work_identity.instrument_code` | C, U | Required for INSTRUMENT/NOTIFICATION |
| `work_identity.rendition`, `proceeding_numbers_as_printed`, `identity_review_ref` | O | `identity_review_ref` C when DOCUMENTARY_CHECKED |
| `embedded_images` | M, U | Array, possibly empty, or UNRESOLVED (WORD_IMAGES_NOT_INVENTORIED) |
| `text_derivatives` | M | Array, possibly empty |
| `alternate_copies`, `status_axes` | O | `status_axes` is M on the v1 document record |
| `provenance.{acquisition, observations, processing_history}` | M | `carrier_provenance` C when CARRIER_ISSUED_COPY_CLAIMED |
| `restriction`, `integrity`, `research_eligibility` | M | |

### 3.2 `evidence_anchor`

| Field | Status | Notes |
| --- | --- | --- |
| `contract`, `record_kind`, `anchor_id`, `doc_id`, `original_sha256`, `representation_sha256`, `locator.kind`, `extraction.{method, pipeline_name, pipeline_version}`, `quality.{text_reliability, low_confidence}`, `verification.state`, `quoting_permitted` | M | |
| `quality.ocr_mean_confidence` | U | Required non-null for OCR; `null` otherwise |
| `locator.physical_page` / `reconstructed_page` / `generated_segment` / `image_sequence_id` / `paragraph_index` | C | By locator kind |
| `locator.citable_as_source_page` | C | |
| `page_mapping_basis` | C | Required for RECONSTRUCTED_PAGE |
| `extraction.ocr_config` | C | Required for OCR methods (engine, version, languages, DPI, PSM, preprocessing, `config_sha256`) |
| `image_sha256` | C | Required for OCR_EMBEDDED_IMAGE |
| `derivative_text_sha256` | C | Required with a `text_span` |
| `text_span`, `bbox`, `printed_page_label`, `paragraph_label`, `quote`, `verification.review_ref` | O | `review_ref` C when DOCUMENTARY_CHECKED or INCORRECT |

### 3.3 `taxonomy_node`, `corpus_relationship`, `corpus_admission`

See sections 7, 8 and 10. Every record kind is closed (`additionalProperties: false`).

## 4. Prohibited assumptions

A producer must never emit, and a consumer must never derive, any of the following. Where the schema can enforce one, the negative fixture is named.

| # | Prohibited assumption | Enforcement |
| --- | --- | --- |
| P1 | A folder or file-name classification is a judicial or legal finding | FOLDER_PATH/FILENAME_PATTERN relationships are limited to CANDIDATE or CURATED_NAVIGATION, `is_finding=false`, no review or approval ref (N01, N13) |
| P2 | A locally reconstructed PDF is a court- or authority-issued original | `RECONSTRUCTED_SEARCHABLE_PDF` ⇒ `LOCALLY_RECONSTRUCTED`; it needs `reconstructed_from_sha256` (N02, N14) |
| P3 | An extract is a complete judgment, or supports a statement about the whole work (outcome, absence of a passage) | EXTRACT ⇒ PARTIAL_EXTRACT and `whole_work_claims_permitted=false` (N03, N18) |
| P4 | A compilation's title, date or outcome is a member judgment's | `members[]` each carry their own work reference (N12) |
| P5 | A Word document with pasted screenshots carries the court's issued text | Its origin cannot be CARRIER_ISSUED_COPY_CLAIMED (N21); image OCR is never quotable |
| P6 | A Word document whose images were not inventoried has complete text | WORD_IMAGES_NOT_INVENTORIED ⇒ `embedded_images` UNRESOLVED and no full eligibility; an empty list means "inventoried, none found" (N10) |
| P7 | A generated segment or a reconstructed-PDF page is a source page | `citable_as_source_page=false` unless SOURCE_PHYSICAL_PAGE, or a hash-checked one-to-one mapping (N11) |
| P8 | OCR text can be quoted as printed text | OCR anchors and derivatives have `quoting_permitted=false` (N05) |
| P9 | SHA-256 proves authenticity, currency or correctness | `integrity` is byte integrity only; authenticity stays on the v1 `source_authenticity` axis |
| P10 | Two files with identical normalised text are the same legal document | They are an alternate-copy link (NORMALIZED_TEXT_IDENTICAL, verification CANDIDATE), never a merge |
| P11 | Deduplicating bytes deduplicates classifications | One relationship per (path, label, target). The AR 22 example keeps both of its paths |
| P12 | An abbreviation in a label has one reading | `abbreviation_expansion` records the reading and the alternatives, and forces CANDIDATE |
| P13 | An absent citation or treatment relationship means no such authority exists | Consumer rule (consumer requirements C9) |
| P14 | Admission, publication or a documentary check is legal approval | Admission has `publication_effect=NONE` and `legal_effect=NONE`; `legally_validated` needs an `AP-` approval and is refused at AUTH-LEDGER v0 (N06, N07) |
| P15 | A candidate is a finding | `is_finding=true` needs DOCUMENTARY_CHECKED or LEGAL_REVIEWED (N22) |
| P16 | Owner-collection files came from an official carrier | Local items are ACQUIRED_COPY_ORIGIN_UNDETERMINED with carrier `USER_SUPPLIED`, unless acquisition evidence says otherwise |
| P17 | An `order` or `judgment` type guessed from a file name is the document type | `identity_basis=METADATA_CANDIDATE` or `FOLDER_OR_FILENAME_LABEL`, verification CANDIDATE |

## 5. Document classes (WP03)

| Class | `representation_kind` | `origin_status` (typical) | Pagination | Text methods | Quoting / page citation |
| --- | --- | --- | --- | --- | --- |
| Official PDF from a court or ministry site | NATIVE_DIGITAL_PDF | CARRIER_ISSUED_COPY_CLAIMED (needs carrier ISSUING_AUTHORITY or GOVERNMENT_HOSTED_COPY and a source URL) | PHYSICAL_PAGES | NATIVE_TEXT_LAYER | yes / yes, if text is reliable |
| Native-text document (DOCX, TXT, HTML) | WORD_NATIVE_TEXT, PLAIN_TEXT, HTML_PAGE | usually THIRD_PARTY_REPRODUCTION or undetermined | NONE_FLOW_DOCUMENT → GENERATED_SEGMENT | DOCX_XML, PLAIN_TEXT, HTML | yes if reliable / **no** (no physical page) |
| Scan | SCANNED_PDF | as acquired | PHYSICAL_PAGES | OCR_PAGE_IMAGE | **no** / yes |
| Word with embedded screenshots | WORD_WITH_EMBEDDED_IMAGES | THIRD_PARTY_REPRODUCTION or undetermined; never carrier-issued | NONE_FLOW_DOCUMENT; images by IMAGE_SEQUENCE | DOCX_XML + OCR_EMBEDDED_IMAGE | **no** / **no**; anchors point at `IMG:<sha>:<seq>` |
| Word, images not inventoried | WORD_IMAGES_NOT_INVENTORIED | as acquired | NONE_FLOW_DOCUMENT | DOCX_XML only | **no** / **no**; held for extraction (G07) |
| Mixed (some pages text, some images) | MIXED_PDF | as acquired | PHYSICAL_PAGES | NATIVE_TEXT_LAYER + OCR_PAGE_IMAGE | **no** for the derivative (any OCR) / yes |
| Locally reconstructed searchable PDF | RECONSTRUCTED_SEARCHABLE_PDF | LOCALLY_RECONSTRUCTED | its own pages = RECONSTRUCTED_PDF | OCR (added layer) | **no** / only through a hash-checked one-to-one `page_mapping`, and then the citation names the **original** copy |
| Partial extract | any kind, `content_scope=EXTRACT` | as acquired | as kind | as kind | as kind / yes, but `whole_work_claims_permitted=false`; `extract_scope.work_pages` records the work's pages, and `printed_page_label` keeps the printed number |
| Compilation of several judgments | any kind, `content_scope=COMPILATION` | as acquired | as kind | as kind | per member; relationships name `subject.compilation_member_seq` |

### 5.1 Original versus reconstructed

A reconstruction is a **separate copy** with its own `sha256` and `doc_id`. It links to its original:
- `alternate_copies` on the original (`RECONSTRUCTION_OF_THIS`);
- `alternate_copies` on the reconstruction (`THIS_RECONSTRUCTED_FROM`);
- `reconstructed_from_sha256` on the reconstruction.

It is admitted **beside** the original (`ADMITTED_AS_ALTERNATE_COPY`, relation `RECONSTRUCTION_OF`), never in place of it. Evidence found in a reconstruction is anchored with:
- `original_sha256` = the original;
- `representation_sha256` = the reconstruction;
- locator RECONSTRUCTED_PAGE.

**Page mapping.** Only `page_mapping.basis = ONE_TO_ONE_PAGE_HASH_CHECKED` (page images re-hashed one to one) lets the anchor carry `physical_page` and be cited, and then always as the original's page.

**Spans.** A span measured on a reconstruction never binds to the original's derivative (`adapters.anchor_to_v1_page_anchor`).

## 6. Evidence anchors (WP03)

### 6.1 Three page notions and the image sequence

| Notion | Field | Meaning | Shown to users as |
| --- | --- | --- | --- |
| Source pagination | `locator.physical_page` (with SOURCE_PHYSICAL_PAGE) | 1-based physical page of `original_sha256`; v1 `page_anchor.page` | "page N" (and the printed label when known) |
| Printed page | `locator.printed_page_label` | Number as printed; never inferred | "printed p. X" |
| Reconstructed-PDF pagination | `locator.reconstructed_page` | Page of a locally built PDF | Never as a source page; only through a checked mapping |
| Generated segment | `locator.generated_segment` | Segment of a flow document (the `[[page N]]` markers of its derivative) | "segment N", never "page N" |
| Image sequence | `locator.image_sequence_id` `IMG:<container sha256>:<seq>` | n-th embedded image in reading order | "image N in the document" |

### 6.2 Completeness, and the v1 mapping

C16 `completeness` is about the **work**: whether these bytes carry the whole judgment or instrument. v1 `source_copy.completeness` is about **bytes against the carrier** (download not truncated).

The adapter therefore maps:
- v1 `COMPLETE` → C16 `NOT_CHECKED`, with `completeness_basis` recording the v1 value;
- `TRUNCATED_AT_SOURCE` and `UNOPENABLE` pass through unchanged.

A producer writes C16 `COMPLETE` only with evidence, for example a printed page sequence matching the physical pages, or a carrier statement. In the v1 direction, `PARTIAL_EXTRACT` projects to v1 `NOT_CHECKED`.

### 6.3 Anchor contents

Each anchor holds:
- **hashes:** `original_sha256`, `representation_sha256`, `derivative_text_sha256` and `image_sha256`;
- **location:** the locator (physical or generated page, image sequence id, paragraph), `text_span` (code-point offsets, as v1, counted after the `[[page N]]` marker line, plus the span hash) and `bbox` (unit PDF_POINT, IMAGE_PIXEL or NORMALIZED; space SOURCE_PAGE, RECONSTRUCTED_PAGE or IMAGE);
- **extraction:** method, pipeline and `ocr_config` (engine, version, languages, DPI, PSM, preprocessing, `config_sha256`);
- **quality:** reliability, mean OCR confidence, low-confidence flag;
- **verification:** AUTOMATED_CANDIDATE_NOT_VERIFIED, DOCUMENTARY_CHECKED or INCORRECT, with a review ref.

`anchor_id` is deterministic over the location fields only (section 9.2), so re-reviewing an anchor keeps its id.

### 6.4 Projection to v1 PageKey and SpanKey

`adapters.anchor_to_v1_page_anchor(anchor, identity, span_verified=...)` gives:
- `PageKey = (original_sha256, physical_page)` only when the anchor is bound to its identity (same `doc_id` and copy), the locator is a citable source page within the copy's page count, the copy permits page citation, and the anchor is not INCORRECT;
- the SpanKey fields (`pipeline_name`, `pipeline_version`, `derivative_text_sha256`, offsets, `passage_id`, `text_sha256`) and any quote only when the span was **byte-verified** against the derivative (section 6.6) and was measured on the original.

Without an identity it returns nothing. Anchors with no source page (generated segments, image sequences, text flow, unmapped reconstructions) **do not project**: v1 has no way to hold them, and inventing page 1 is prohibited. The consumer serves them through the C16 sidecar (consumer requirements C4).

### 6.5 Quoting and eligibility gates

The existing application gates still apply: `DocumentRecord.QuotingPermitted`, `TextQuality` reliability, unreliable text excluded from search, and the quoting gate on graph edges (Api.Graph). C16 adds three permissions in `research_eligibility`:
- `source_page_citation_permitted`;
- `whole_work_claims_permitted`;
- `graph_evidence_permitted`.

Constraints:
- OCR, unreliable text or low confidence ⇒ `quoting_permitted=false`, at derivative, anchor and document level;
- `RESTRICTED` or a byte MISMATCH ⇒ `NOT_ELIGIBLE`;
- `NOT_ASSESSED` or `NOT_ELIGIBLE` ⇒ no quoting and no graph evidence.

The consumer must AND the C16 permissions with its own gates and never OR them.

### 6.6 Evidence binding (review finding C02)

A shape-valid anchor is not evidence. Two layers of checks apply before an anchor can locate a citation or a graph edge.

**Cross-record binding** (`rules.exchange_issues`, every mode):

| Check | Code |
| --- | --- |
| `(doc_id, original_sha256)` is a document identity in the exchange | `C16_DANGLING_SUBJECT` |
| `representation_sha256` is the original, or a held identity that is `LOCALLY_RECONSTRUCTED` from it | `C16_ANCHOR_REPRESENTATION` |
| `derivative_text_sha256` is a derivative of that representation (or the OCR derivative of one of its images), with the same pipeline name and version | `C16_ANCHOR_DERIVATIVE` |
| `image_sequence_id` is an occurrence in the identity's image inventory and `image_sha256` equals that occurrence's hash | `C16_ANCHOR_IMAGE` |
| a source page lies within the copy's physical pages; a reconstructed page within the reconstruction; a segment within the derivative | `C16_ANCHOR_PAGE_RANGE` |
| a reconstructed page uses the reconstruction's own `page_mapping` basis, and is citable only through `ONE_TO_ONE_PAGE_HASH_CHECKED` with `physical_page = reconstructed_page + offset` | `C16_ANCHOR_MAPPING` |
| every anchor of a relationship is on the subject's own copy; none is INCORRECT; in a compilation the anchor lies within the member's pages | `C16_ANCHOR_SUBJECT`, `C16_ANCHOR_INCORRECT`, `C16_COMPILATION_MEMBER` |
| the relationship's subject node equals the identity's `graph_node_ref` (or the member's `work_ref` when `compilation_member_seq` is given); evidence in a compilation must name its member | `C16_SUBJECT_NODE_MISMATCH`, `C16_COMPILATION_MEMBER` |
| a DOCUMENTARY_CHECKED relationship rests on at least one DOCUMENTARY_CHECKED, bound, non-low-confidence anchor | `C16_FINDING_ON_WEAK_ANCHOR` |

**Byte binding** (`evidence.verify_anchor_bytes`, consumer side): the derivative bytes must hash to `derivative_text_sha256`, the unit (page, reconstructed page or segment) must exist in the `[[page N]]` text, the code-point offsets must lie inside it, and the slice must hash to `text_sha256`. `evidence.usable_for_citation` and `evidence.usable_as_graph_evidence` accept an anchor only if it is not INCORRECT, its copy permits the use, and its span (if any) has been byte-verified. `adapters.graph_projection(rel, anchors, usable)` shows a page on an edge only for anchors in the consumer-verified `usable` set. Low-confidence OCR may locate a candidate; it never supports a raised verification. Nothing in these checks promotes an anchor.

## 7. Provision and judgment relationships, and the C15 graph mapping (WP02)

### 7.1 Categories, evidence and verification

| Category | Allowed bases | Anchors | `has_legal_effect` | Verification allowed | C15 edge type | C15 status |
| --- | --- | --- | --- | --- | --- | --- |
| `classified_under_subject` | FOLDER_PATH, FILENAME_PATTERN, OWNER_CATALOGUE, AUTOMATED_CLASSIFIER, DOCUMENT_TEXT_* | 0+ | false | label bases: CANDIDATE, CURATED_NAVIGATION | `CLASSIFIED_UNDER_SUBJECT` | **proposed** |
| `classified_under_chapter` | same | 0+ | false | same | `CLASSIFIED_UNDER_CHAPTER` | **proposed** |
| `associated_with_provision` | same | 0+ | false | same; FILENAME_PATTERN and any abbreviation reading ⇒ CANDIDATE | `ASSOCIATED_WITH_PROVISION` | **proposed** |
| `cites_provision` | DOCUMENT_TEXT_EXTRACTED, DOCUMENT_TEXT_REVIEWED | ≥ 1 | false | CANDIDATE; DOCUMENTARY_CHECKED with `RV-` | `CITES_PROVISION` | existing |
| `interprets_provision` | same | ≥ 1 | true | same | `INTERPRETS_PROVISION` | in architecture §5 and the v1 candidate enum; **proposed for C15** |
| `refers_to_judgment` | same | ≥ 1 | false | same | `CITES_JUDGMENT` | existing |
| `follows` | same | ≥ 1, plus `proposition_ref` | true | same | `FOLLOWS_PROPOSITION` | existing |
| `distinguishes` | same | ≥ 1, plus `proposition_ref` | true | same | `DISTINGUISHES_PROPOSITION` | in architecture §5 and the v1 enum; **proposed for C15** |
| `overrules` | same | ≥ 1, plus `proposition_ref` | true | same | `OVERRULES_OR_LIMITS_PROPOSITION` | existing |
| `legally_validated` | LEGAL_REVIEW only | 0+ | true | LEGAL_REVIEWED only, with `AP-` approval and `validates_relationship_id` | no edge: a `graph_edge_reviews` row on the validated edge | review table exists (ADR-0006), no write path yet |

**Every relationship carries:**
- `evidentiary_basis`;
- `source` (producer tool, rule id and version, author);
- `classification_provenance` (for label bases: collection, relative path, path component, matched text, abbreviation reading and alternatives);
- `anchors`, `verification`, and `review_ref` / `approval_ref`;
- `temporal_scope` (`from`, `from_status`, `to`, `to_status`, aligned with C15 `TemporalFrom`/`TemporalFromStatus`/…);
- `has_legal_effect`, `is_finding` and `uncertainty` (shown with the edge, as C15 `Uncertainty`).

**Temporal scope by category:**
- classification relationships: `NOT_APPLICABLE`;
- citations and treatments: `AS_OF_SOURCE_DATE` (or `NOT_RECORDED` when the source date is unknown);
- legal-effect intervals: need evidence for each bound.

Treatment is **proposition-scoped**. A judgment-level "overruled" status is a derived view and is never asserted (architecture §5, TA-04).

### 7.2 Node mapping

| C16 reference | C15 node | Notes |
| --- | --- | --- |
| `JUD:<doc_id>`, `JUD:JG-<12 hex>` | `judgment` | Same ids as GraphIds.Judgment and A5 targets |
| `PROV:<code>:<s/r/reg>.<base>` | `provision` | Same as GraphIds.Provision. The number is the BaseSection (1–3 digits and up to 2 capitals); sub-provisions go in `taxonomy_node.provision.sub_provision`, not into the id |
| `INSTCODE:<code>` | `instrument` (`INST:<family key>`) | Resolved by the consumer through the code registry (GraphIds.CodeByPrimaryDoc, InstrumentCatalog.FamilyKey); producers never build `INST:` ids |
| `REF:<16 hex>` | `unresolved_reference` | Same as GraphIds.Reference(raw); the consumer computes it from `target.raw_reference` |
| `SUBJ:<topic>`, `SUBJ:local:<slug>` | **new kind `subject`** | `<topic>` is the controlled list in `schema/document.schema.json` |
| `CHAP:<code>:<label>` | **new kind `chapter`** | From tables of contents (EXTRACTED_STRUCTURE) |

No parallel graph is created. C16 relationships become edges in the same `graph_node` / `graph_edge` tables, built by `GraphBuilder` from the active generation, with origins `C16_FOLDER_PATH`, `C16_FILENAME_PATTERN`, `C16_OWNER_CATALOGUE`, `C16_AUTOMATED_CLASSIFIER` and `C16_DOCUMENT_TEXT`.

### 7.3 Verification mapping

| Source vocabulary | C15 `Verification` | `graph_edge_reviews` |
| --- | --- | --- |
| C16 CANDIDATE / v1 AUTOMATED_CANDIDATE_NOT_VERIFIED / corpus `extracted`, `llm_proposed` / A5 AUTOMATED_CANDIDATE_NOT_VERIFIED | CANDIDATE | none |
| C16 EXTRACTED_STRUCTURE (tables of contents, chapters) | EXTRACTED_STRUCTURE | none |
| C16 CURATED_NAVIGATION (owner folders, controlled subjects) | CURATED_NAVIGATION | none |
| C16 DOCUMENTARY_CHECKED / v1 DOCUMENTARY_CHECKED (with `RV-`) / corpus `human_verified` with a reviewed_record | edge stays **CANDIDATE** | row `DOCUMENTARY_CHECKED` with review_ref |
| C16 `legally_validated` (LEGAL_REVIEWED, with `AP-`) | edge unchanged | row `LEGAL_REVIEWED` with approval_ref; **refused at AUTH-LEDGER v0** |
| v1 REJECTED_ON_REVIEW / anchor INCORRECT | not built | |

**Review binding.** A raised value (relationship or anchor DOCUMENTARY_CHECKED, identity `identity_verification` DOCUMENTARY_CHECKED) needs a `review_binding`: the exact contract-v1 `reviewed_record` id, the sha256 of its canonical bytes, the reviewed commit, the reviewer id and kind, and the author id. The reviewed_record must be in the exchange (`reviewed_records.jsonl`), unchanged (hash), about exactly this subject (`{kind: candidate, id: <relationship or anchor id>}`, or `{kind: document, id: <doc_id>}`), on axis `evidence_fidelity` with `to_value` DOCUMENTARY_CHECKED, with the same reviewer, author and commit, and the reviewer must not be the author (and, for relationships, the author and commit must be the relationship's own `source.author_id` and producer commit). Codes `C16_REVIEW_UNRESOLVED`, `C16_REVIEW_BINDING`, `C16_REVIEW_NOT_INDEPENDENT`. Classification relationships can never carry DOCUMENT_TEXT_REVIEWED, DOCUMENTARY_CHECKED, LEGAL_REVIEWED or `is_finding=true` (schema). AUTH-LEDGER v0 stays closed: `legally_validated` is refused (`LEDGER_V0_NO_APPROVAL`).

This keeps the ADR-0006 invariant: `GraphStore.PublishAsync` refuses any edge value other than the three builder values, and reviews live only in the review table. A5's `REVIEWED_AI_DOCUMENTARY_NOT_LEGAL_VALIDATION` maps to a DOCUMENTARY_CHECKED review row only where the v1 `reviewed_record` rules hold: an independent reviewer and a matching commit. Otherwise it stays CANDIDATE.

### 7.4 Edge ids

C15 `GraphIds.EdgeId` hashes (type, from, to, origin, source doc, page, quote prefix). Two classification relationships with the same endpoints and no page or quote, such as one judgment filed under "AR 22" in two folders, would collide, and `edges.TryAdd` would drop one.

C16-origin edges therefore use `E + 20 hex of sha256("type|from|to|origin|relationship_id")` (`adapters.c16_edge_id`). The relationship id is the discriminator, so classifications are never merged. Existing origins keep their ids.

## 8. Legal taxonomy (WP02)

### 8.1 Hierarchy

Subject > statute > chapter > provision. Each node is a `taxonomy_node`.

| Level | `node_id` | Parents | Source basis | Verification |
| --- | --- | --- | --- | --- |
| SUBJECT | `SUBJ:<topic>` or `SUBJ:local:<slug>` | subjects (0+) | CONTROLLED_TOPIC_LIST, OWNER_FOLDER | CURATED_NAVIGATION |
| STATUTE | `INSTCODE:<code>` | ≥ 1 subject | GRAPH_INSTRUMENT | producer value |
| CHAPTER | `CHAP:<code>:<label>` | exactly its statute | TABLE_OF_CONTENTS (doc and page) | EXTRACTED_STRUCTURE |
| PROVISION | `PROV:<code>:<prefix>.<base>` | its statute or one of its chapters | TABLE_OF_CONTENTS, GRAPH_PROVISION | producer value |

### 8.2 Many-to-many

- **Hierarchy:** a DAG (cycle check `C16_TAXONOMY_CYCLE`). A statute may sit under several subjects.
- **Owner subjects:** a `SUBJ:local:*` subject may propose `maps_to_subject` on the controlled list. This is a candidate mapping and is never applied automatically.
- **Documents:** attach to any number of subjects, chapters and provisions through relationships, and each relationship has its own provenance.

**Deduplicating bytes does not deduplicate classifications.** In the fixture `positive/relationships_ar_22_23_30.jsonl`, one Word file seen at two paths yields:
- two subject classifications (two folders);
- three provision associations from the first file name (r.22, r.23, r.30);
- one more r.22 association from the second file name.

That is four distinct provision associations on one `source_copy_sha256`.

### 8.3 Filename and folder classification rules

Rules version 1.1 (`adapters.classify_path`, `adapters.local_subject_nodes`):

| Rule | Input | Output |
| --- | --- | --- |
| `C16-FOLDER-SUBJECT` | the full folder path of the file | one `classified_under_subject` to the **leaf** folder node `SUBJ:local:<slug of every folder from the root, joined by '__'>` (CURATED_NAVIGATION); one taxonomy SUBJECT node per folder prefix, each parented by the folder above. `A/Rules` and `B/Rules` are different nodes |
| `C16-FOLDER-PROVLIST` | a folder named like a provision list (`AR 22`) | candidate `associated_with_provision`, basis FOLDER_PATH (decision Q4) |
| `C16-FN-PROVLIST` | a file name beginning `<ABBR> <n>[, <n>…] –` | one candidate `associated_with_provision` per number, basis FILENAME_PATTERN |

**Signals are preserved, never expanded or guessed.**
- A range (`AR 22-25`) or an unparsed label yields one **unresolved** association with the label as `raw_reference` and the note `PROVISION_RANGE_NOT_EXPANDED` or `UNPARSED_PROVISION_LABEL`.
- An abbreviation with more than one reading yields an unresolved association listing the alternatives.
- A prefix with no repository-recorded statutory reading (OA, WP, CA … are case-number prefixes) yields no association.
- The same binary seen at several paths is one identity with several `observations`; every path keeps its own classifications.

**Abbreviation readings 1.1** (decision Q3): only readings already recorded in this repository, from `Mimamsa.Core/Identifiers/LegalIdentifierResolver.cs` (Aliases) and the B1/P2 supplement in `app/b1/build/build_sample.py`. Owner confirmation remains open.

| Abbreviation | Reading | Target | Alternatives |
| --- | --- | --- | --- |
| AA | Army Act | `PROV:AA-1950:s.<n>` | none recorded |
| AR | Army Rules | `PROV:AR-1954:r.<n>` | none recorded |
| AFA | Air Force Act | `PROV:AFA-1950:s.<n>` | none recorded |
| NA | Navy Act | `PROV:NA-1957:s.<n>` | none recorded |
| AFT | Armed Forces Tribunal (the forum) | **unresolved** | "Armed Forces Tribunal Act, 2007, section <n>"; "the forum; the number is not a provision". The tribunal is kept distinct from the Act |

**Paths.** Relative to a registered collection (`local:<name>`), NFC, with POSIX separators. The drive root is never written.

## 9. Exchange formats and determinism

### 9.1 Files and canonical serialisation

- **One JSONL file per record kind:**
  - `identities.jsonl`
  - `anchors.jsonl`
  - `relationships.jsonl`
  - `taxonomy.jsonl`
  - `admissions.jsonl`
- **Single records:** may be exchanged as `.json` (any formatting), for review and fixtures.
- **Canonical JSON** (`canonical.canonical_bytes`):
  - UTF-8 with no BOM;
  - keys sorted by code point (ASCII keys, so this equals RFC 8785 order);
  - separators `,` and `:` with no whitespace;
  - `ensure_ascii=false`;
  - every string already NFC (non-NFC is rejected, never silently normalised);
  - integers within ±(2^53−1);
  - floats only where the schema allows a number: finite, never −0, at most 4 decimal places, written as an integer when integral (so `12.0` becomes `12`), so no exponent form occurs.
- **JSONL:**
  - one canonical record per line, LF, final LF;
  - records sorted by the kind's sort key (`canonical.SORT_KEYS`);
  - no duplicate keys.

  | Kind | Sort key |
  | --- | --- |
  | identities | (`doc_id`, `sha256`) |
  | anchors | `anchor_id` |
  | relationships | `relationship_id` |
  | taxonomy | (level rank, `node_id`) |
  | admissions | `admission_id` |

  The same input therefore always produces the same bytes, and the file's SHA-256 is a stable checksum (C16_JSONL rejects anything else).
- **Arrays:**
  - set-like arrays (`parent_ids`, `anchors`, `basis`, `secondary_flags`) are sorted and unique;
  - order-bearing arrays (`members`, `embedded_images`, `processing_history`) are numbered 1..n in order (rule C16_SEQUENCE).
- **Timestamps:** UTC with a trailing `Z`. Wall-clock values (`observed_at`, `decided_at`, `retrieved_at`) are informational and never part of an identity, so a re-run on the same inputs is byte-identical when they are null or pinned.

### 9.2 Deterministic identifiers

`<PREFIX>-<first 24 hex of sha256(canonical JSON of [PREFIX, …identity tuple])>` (`canonical.stable_id`).

| Id | Identity tuple (and only this) |
| --- | --- |
| `REL-` | category, subject doc_id, subject sha256, compilation member, target (`node_id`, or `["raw", raw_reference]`), evidentiary basis, rule id, discriminator. The discriminator is `["path", collection, relative_path, path_component, matched_text]` for label bases, `["anchors", sorted anchor ids]` for text bases, or `["validates", validated id, approval ref]` for `legally_validated` |
| `ANC-` | doc_id, original sha256, representation sha256, derivative sha256, image sha256, locator (kind, physical page, reconstructed page, generated segment, image sequence id, paragraph index), span (start, end, text hash), bbox |
| `ADM-` | corpus generation id, doc_id, sha256, **revision, superseded admission id**, rule-set id and version, **decision and sorted gate results**. A changed decision is therefore a new id and must be a new revision |

Verification, quality, wording, rule version and timestamps are excluded, so a re-review or a new pipeline run that finds the same item keeps the id. This is the v1 `candidate_id` stability rule. A different item gets a new id. Rule C16_ID_MISMATCH rejects an id that does not recompute.

### 9.3 Validation levels and the generation manifest (review finding C05)

| Level | Call | Requires | Use |
| --- | --- | --- | --- |
| Record | `rules.record_issues(rec)` | one JSON object (anything else is `JSONL_NOT_OBJECT`, never an exception) | review tooling, adapters |
| **Partial** exchange | `rules.exchange_issues(files, mode="partial")` | canonical file names; every present record valid; references resolved **among the populations present** | adapter output, work in progress. **Never importable** |
| **Strict** exchange (default) | `rules.exchange_issues(files, mode="strict")` | `GENERATION.json`; every declared file present with matching sha256 and record count, no undeclared file; all five populations (identities, anchors, relationships, taxonomy, admissions; `reviewed_records` when any binding exists); one generation; registries | producer hand-over |
| Signed import | importer | a signed v1 bundle **and** a strict exchange inside it | site |

In every mode:
- **File names** are canonical (`identities.jsonl`, `anchors.jsonl`, `relationships.jsonl`, `taxonomy.jsonl`, `admissions.jsonl`, `reviewed_records.jsonl`) or declared shards `<stem>.<nnnn>.jsonl`; a record of another kind in a file is `C16_KIND_MISMATCH`.
- **Keys are globally unique across files and shards** (`C16_DUPLICATE_KEY`): identity `doc_id` and (doc_id, sha256), anchor, relationship, taxonomy, admission and review ids.
- **Schema-invalid records are excluded** from every cross-record map, so a malformed record can never satisfy or crash a reference check.
- **One generation**: every identity and admission carries the manifest's `corpus_generation_id` (`C16_GENERATION_MISMATCH`).
- **There is no implicit bypass**: an empty or missing population is an error in strict mode; partial mode skips only checks whose population is absent, and says so in its name.

`GENERATION.json` (`CORPUS_GENERATION_MANIFEST_SCHEMA.json`) pins the inputs (any number of immutable HF revisions, each with its purpose: decision Q8; full git commits; local collections with their inventory hash and file count; the restricted-register sha256; tools), lists every file with kind, sha256 and record count, and declares the **registries** against which identifiers resolve: `instrument_codes` (the C15 code list plus declared `DOC-` codes; the test checks the C15 list against `GraphModel.cs`) and `external_judgments` (`JUD:JG-…` targets that are not held). In strict mode every `PROV:`, `CHAP:` and `SUBJ:` target must be a taxonomy node, every `JUD:<doc_id>` target a held identity, and every `JUD:JG-` target a declared external judgment (`C16_TARGET_UNREGISTERED`).

## 10. Admission gates (review finding C01)

**Shape (schema).** Exactly ten gate results, one per gate id (ten items, each of the ten ids present: hence each exactly once). Every PASS carries an `evidence_ref`. NOT_APPLICABLE is allowed only for G06 and G07. An eligible admission (`application_eligible=true`) must be ADMITTED, with G01–G05 and G08–G10 PASS, and G06/G07 PASS or NOT_APPLICABLE.

| Gate | PASS means | NOT_APPLICABLE only when |
| --- | --- | --- |
| G01_HASH_VERIFIED | the identity's integrity is **BYTE_VERIFIED** (re-hashed against an independently held manifest at a pinned revision); a declared hash is NOT_RUN | never |
| G02_FORMAT_DETECTED | the format is detected from the bytes (never UNKNOWN) | never |
| G03_RESTRICTED_REGISTER | the register was checked against hash, doc_id, path and every record string; no match | never |
| G04_ACCESS_MARKING_REVIEWED | printed and image markings looked for; restriction eligibility decided (not NOT_ASSESSED) | never |
| G05_IDENTITY_RECORD_VALID | the identity validates (schema and rules) | never |
| G06_TEXT_DERIVATIVE_VERIFIED | at least one derivative, re-hashed, covering its units, in the page format | the copy has no derivative by design |
| G07_EMBEDDED_IMAGES_ACCOUNTED | every image inventoried, and read (DONE) or decorative | the image list is inventoried and **empty** |
| G08_RELEVANCE_ASSESSED | relevance decided as the owner directs (an automated signal alone is NOT_RUN) | never |
| G09_DUPLICATE_RESOLVED | byte and text duplicates resolved to a primary or an alternate | never |
| G10_SCHEMA_VALID | the whole strict exchange validates | never |

**Cross-record rules** (`rules.exchange_issues`):
- **Binding:** every admission names an identity in the same exchange (`C16_ADMISSION_ORPHAN`) and generation (`C16_GENERATION_MISMATCH`); every identity has a decision (`C16_ADMISSION_MISSING`).
- **Append-only revisions:** revision 1 supersedes nothing; revision n supersedes revision n−1 of the same (generation, doc_id, sha256). Superseding an unknown, foreign or own admission is `C16_ADMISSION_SUPERSESSION`; two revisions superseding the same one, or anything other than one linear chain, is `C16_ADMISSION_FORK`. The **effective decision** is the single chain head.
- **Gate evidence** (`C16_GATE_EVIDENCE`): each PASS and NOT_APPLICABLE above is checked against the bound identity.
- **Eligibility** (`C16_ELIGIBLE_IDENTITY_NOT_READY`): an eligible effective admission needs an identity with restriction ELIGIBLE_ALL_USERS, integrity BYTE_VERIFIED, research state ELIGIBLE_FULL or SEARCH_ONLY, an inventoried and fully read image list, and a representation other than WORD_IMAGES_NOT_INVENTORIED or UNRECOGNISED_FORMAT.
- **Duplicates** (`C16_DUPLICATE_UNRESOLVED`): ADMITTED_AS_ALTERNATE_COPY only as RECONSTRUCTION_OF an original held in the exchange and named in `reconstructed_from_sha256` (normalised-text equality never admits: PR #76 v3); REJECTED_EXACT_DUPLICATE names its own bytes and where they are already held.
- **Restricted items never appear in an exportable exchange** (`C16_RESTRICTED_IN_EXCHANGE`). They exist only as minimal local exclusion receipts (`{sha256_prefix, reason, exportable: false}`), with no identity, path, file name or classification.

**Consumer rule.** The application serves a C16 copy only when its **effective admission in the active generation is eligible** (consumer requirement I7). Admission never publishes (`publication_effect=NONE`) and never approves (`legal_effect=NONE`).

## 11. Rule codes (in addition to the v1 codes)

| Code | Meaning |
| --- | --- |
| `SCHEMA` | JSON Schema violation (message is the JSON path and keyword, never a value) |
| `C16_NOT_CANONICAL`, `C16_JSONL` | canonical form or JSONL order |
| `C16_ID_MISMATCH` | REL/ANC/ADM id does not recompute |
| `C16_RECONSTRUCTED_SELF`, `C16_PAGE_MAPPING_ORIGIN` | reconstruction names itself, or maps to a copy it was not built from |
| `C16_PAGE_RANGE`, `C16_SEQUENCE`, `C16_IMAGE_SEQUENCE_ID`, `C16_DERIVATIVE_ID`, `C16_COVERAGE` | structural consistency of members, images and derivatives |
| `C16_PAGE_CITATION`, `C16_QUOTING` | an eligibility permission not backed by a derivative |
| `C16_ANCHOR_REPRESENTATION`, `C16_ANCHOR_SUBJECT` | a locator measured on the wrong copy; an anchor not of the relationship's subject |
| `C16_TAXONOMY_ID`, `C16_TAXONOMY_PARENT`, `C16_TAXONOMY_CYCLE`, `C16_DANGLING_TAXONOMY`, `C16_DANGLING_SUBJECT` | taxonomy and cross-record integrity |
| `C16_GRAPH_PROJECTION_MISMATCH` | the producer's echoed graph projection differs from section 7 |
| `LEDGER_V0_NO_APPROVAL` | `legally_validated` while AUTH-LEDGER is v0 |
| `C16_ADMISSION_ORPHAN`, `C16_ADMISSION_MISSING`, `C16_ADMISSION_SUPERSESSION`, `C16_ADMISSION_FORK`, `C16_GATE_EVIDENCE`, `C16_ELIGIBLE_IDENTITY_NOT_READY`, `C16_DUPLICATE_UNRESOLVED`, `C16_RESTRICTED_IN_EXCHANGE` | admission binding and gates (section 10) |
| `C16_ANCHOR_DERIVATIVE`, `C16_ANCHOR_IMAGE`, `C16_ANCHOR_PAGE_RANGE`, `C16_ANCHOR_MAPPING`, `C16_ANCHOR_INCORRECT`, `C16_SUBJECT_NODE_MISMATCH`, `C16_COMPILATION_MEMBER`, `C16_FINDING_ON_WEAK_ANCHOR` | evidence binding (section 6.6) |
| `C16_REVIEW_BINDING`, `C16_REVIEW_UNRESOLVED`, `C16_REVIEW_NOT_INDEPENDENT` | review binding (section 7.3) |
| `C16_MANIFEST`, `C16_MANIFEST_MISMATCH`, `C16_FILE_MISSING`, `C16_FILE_NAME`, `C16_KIND_MISMATCH`, `C16_DUPLICATE_KEY`, `C16_GENERATION_MISMATCH`, `C16_TARGET_UNREGISTERED`, `JSONL_NOT_OBJECT` | exchange validation (section 9.3) |
| `C16_ELIGIBILITY_UNSUPPORTED` | full research eligibility with images not inventoried or not read |
| `C16_SPAN_UNBOUND`, `C16_DERIVATIVE_BYTES_MISMATCH`, `C16_DERIVATIVE_MARKERS_MALFORMED`, `C16_SPAN_UNIT_MISSING`, `C16_SPAN_OUT_OF_RANGE`, `C16_SPAN_MISMATCH` | consumer byte checks (`evidence.verify_anchor_bytes`) |
| `KR_*` | knowledge release manifests (architecture section 4a) |
| `DANGLING_ANCHOR`, `DANGLING_VALIDATION`, `EDGE_TARGET`, `ANCHOR_RANGE`, `OCR_QUOTING`, `RESTRICTED_MATERIAL`, `JSONL_MALFORMED` | as in v1 |

## 12. Versioning and backward compatibility

- **Version identifier.** `contract: "mimamsa-corpus-contract/2.<minor>"`. A minor version adds optional fields or enum values that consumers may treat as unknown-and-refuse. A breaking change needs major 3, an updated validator and tests, and review by someone who is neither producer nor consumer author (the v1 change-control rule).
- **v1 is unchanged.** C16 records reference v1 `doc_id`, `sha256`, `vault_path`, `derivative_id`, `passage_id`, `RV-` and `AP-` ids and reuse the v1 `provenance`, `restriction` and `status_axes` schemas by `$ref`.
- **The v1 document record stays the served record.** A C16 identity for the same (doc_id, sha256) adds facts; it never replaces v1 fields. Where they could disagree, the conservative value wins (section 6.2, and consumer requirements C3).
- **B1 generation format unchanged.** `generation.json`, `records/*.jsonl`, `derived/<sha>.txt` and `research/*.jsonl` keep their layout. C16 files arrive under `corpus-v2/` (section 13) and are materialised to `generations/<id>/corpus-v2/` by a C16-aware importer.
- **Graph ids unchanged** for existing origins. New origins use the C16 edge id (section 7.4).
- **Formats v1 cannot carry** (`.doc`, `.rtf`, image-only Word): a C16 identity may exist without a v1 document record until a v1-compatible representation exists. That means either an extended v1 mime list (a v1 minor version, open question Q1), or a locally reconstructed PDF admitted as an alternate copy. The original is still preserved and hashed.

## 13. Transport inside a v1 release bundle

During transition, C16 JSONL files travel in an ordinary signed v1 bundle as:
- files of kind `other`;
- under `corpus-v2/` (for example `corpus-v2/relationships.jsonl`);
- listed in `SHA256SUMS` and covered by the signature.

The v1 validator accepts them unchanged: paths and hashes are still checked against the restricted register, and `corpus-v2/` is not a reserved namespace. A C16-aware importer:
- validates them with `rules.exchange_issues`, including the restricted register on every record;
- refuses the whole bundle on any error, as v1 does.

Contract 2.0 proper adds explicit file kinds (`identities_jsonl` and the others) to `release_manifest`. That is a v1 minor version, deferred to review.

## 14. Adopted working decisions (owner-overridable)

The reviewer's proposed decisions are adopted as **working defaults**. Each can be overridden by the owner; none is a legal approval.

| # | Decision |
| --- | --- |
| Q1 | DOC, DOCX and RTF originals are preserved as evidence (hashed, never executed; no macro execution, no guessed MIME). v1 serving uses a safe, locally reconstructed PDF admitted beside the original (`ADMITTED_AS_ALTERNATE_COPY`, RECONSTRUCTION_OF). Unknown formats are UNRECOGNISED_FORMAT / `application/octet-stream` |
| Q2 | The graph gets `subject` and `chapter` nodes; facets are derived from the same taxonomy (no second classification store) |
| Q3 | AA, AR, AFA, NA and AFT readings come only from the repository (section 8.3). The AFT tribunal is distinct from the AFT Act; ambiguous signals stay candidates with alternatives. Owner confirmation pending |
| Q4 | Provision-named folders generate candidate associations only (rule C16-FOLDER-PROVLIST) |
| Q5 | Owner filing labels are CURATED_NAVIGATION; parsed provision claims are CANDIDATE; never findings |
| Q6 | COMPLETE needs copy- and work-specific evidence and an independent documentary check; it implies no legal approval |
| Q7 | Raw OCR is never quotable. A separately verified transcription may become a future explicit policy; it is never an automatic override |
| Q8 | A corpus generation may pin several immutable HF inputs, each with per-source provenance, in one composite `GENERATION.json` |

Knowledge release decisions O1–O6 are recorded in the architecture (section 12).

## 15. Review disposition (independent review of `4d476fab`)

| Finding | Resolution | Where | Regression tests |
| --- | --- | --- | --- |
| C01 admission binding and gates | exactly ten unique gates, evidence-specific N/A, mandatory PASS for eligibility, PASS evidence refs, append-only revision chain, cross-record binding, consumer rule I7 | `CORPUS_ADMISSION_SCHEMA.json`, `rules._admission_exchange`, `canonical.admission_identity`, section 10 | N08, N20, N29–N32; X01–X08, X18 |
| C02 evidence binding and finding promotion | cross-record anchor binding, byte/span checks, conservative projections, subject/member binding, reviewed-record binding, classification never a finding | `rules._anchor_exchange`, `_relationship_exchange`, `_resolve_review`, `evidence.py`, `adapters.anchor_to_v1_page_anchor`, `graph_projection`, sections 6.6 and 7.3 | N01, N13, N22, N33–N35; X09–X16, X19; byte-check and projection tests |
| C03 crash-consistent activation | activation journal state machine (architecture section 8) with an executable reference model | `activation.py`, architecture section 8 | crash at every boundary, mid-switch exclusion, pinned readers, retention, rollback, model switch, restore |
| C04 PostgreSQL restore boundary | no archive restore: allowlisted KNOWLEDGE_ROWS loaded by application code | `KNOWLEDGE_RELEASE_MANIFEST_SCHEMA.json`, architecture section 7 | N38, N39 |
| C05 exchange robustness | strict / partial / signed levels, manifest with counts and hashes, canonical names, global uniqueness, one generation, registries, structured rejection | `rules.exchange_issues`, `CORPUS_GENERATION_MANIFEST_SCHEMA.json`, section 9.3 | X17, X20–X26; strict/partial tests |
| C06 producer adapters | no fabricated format or gate passes, PR #76 v3 images and holds, restricted receipts, merged observations, hierarchical folders, provision folders, ranges and ambiguity preserved | `adapters.from_pr76_inventory`, `classify_path`, section 8.3, compatibility matrix section 6 | N36; PR #76 adapter tests |
| C07 release completeness | TEXT_STORE component, capability accounting, signed file inventory, namespaces and overlaps, kind-specific correctness checks, distinct degraded and rebuilt outcomes | `KNOWLEDGE_RELEASE_MANIFEST_SCHEMA.json`, `KNOWLEDGE_ACTIVATION_RECORD_SCHEMA.json`, `rules._release_manifest`, architecture sections 3–4a | N23–N28, N37, N40–N45; inventory, capability and rule-pack tests |

