# C16 application consumer requirements (B1 application, Claude)

**Applies to:** the release importer (`app/importer`) and the B1 application (`Mimamsa.Core`: Generation, Graph, Statutes, Citation, Search; Mimamsa.Web: graph, statutes, workspace and citation routes).

**Normative references:** [C16_CORPUS_INTEGRATION_CONTRACT.md](C16_CORPUS_INTEGRATION_CONTRACT.md) and its schemas.

**Status:** this is a design specification, not implemented in this checkpoint.

## 1. Import (importer)

| # | Requirement |
| --- | --- |
| I1 | C16 files arrive in a signed v1 bundle as `other` files under `corpus-v2/` (contract section 13). They are verified by signature and SHA256SUMS **before** parsing, exactly as v1 |
| I2 | Validate the whole exchange **strictly** with `mimamsa_contract.c16.rules.exchange_issues(files, mode="strict", auth_ledger_version=<manifest>, register=<site register>)`; a partial exchange is never imported. Any error refuses the **whole bundle** (v1 rule), and nothing is written. The site's exclusion store is applied after activation as today |
| I3 | Cross-check against the bundle's v1 records. Every identity's (`doc_id`, `sha256`) must equal a v1 document's, or be a declared C16-only item (contract section 12). `RV-` and `AP-` refs must resolve under v1 rules. Every anchor's `original_sha256` must be a verified copy in the generation |
| I4 | Byte checks the importer can do, it does. An embedded image's `image_sha256` must be present in the container when the original is a DOCX (open the zip safely, with the PR #76 `safe_archive_member` rules). Page counts must match. Hashes of reconstructed-page mappings must match where page images are bundled. A failed item is UNRESOLVED (quarantined), never served |
| I5 | Materialise the verified C16 records to `generations/<id>/corpus-v2/*.jsonl`, written into the temporary generation before the atomic rename (existing discipline). Record them in `generation.json` `materialized.corpus_v2` |
| I6 | An item not in `servable` (v1) has its C16 records ignored, and the reason is counted (`C16_SUBJECT_NOT_SERVABLE`) |
| I7 | **A C16 copy is served only when its effective admission (the head of its revision chain) in the active generation is `application_eligible`.** Held, rejected, quarantined or missing decisions mean not served, whatever the v1 record says |
| I8 | **Display only quotations derived from verified bytes** (`evidence.verified_quote`, every quotation gate ANDed; the producer's quote field is never shown). **Byte-check every anchor before use** (`evidence.verify_anchor_bytes` against the verified derivative bytes). Only anchors that pass `usable_for_citation` / `usable_as_graph_evidence` may produce a page citation, a SpanKey, a quote or an edge location; the others are shown page-free as "location not verified" |
| I9 | Resolve every `review_binding` against the bundle's reviewed_records (exact record, canonical hash, commit, reviewer distinct from author) before writing any `graph_edge_reviews` row; AUTH-LEDGER v0 keeps `legally_validated` refused |

## 2. GenerationStore, the text store and eligibility

| # | Requirement |
| --- | --- |
| C1 | `GenerationStore.Load` reads `corpus-v2/` when present and attaches identity facts to `DocumentRecord`: representation kind, origin status, content scope, completeness, the image inventory and the research eligibility flags. Absent C16 data means today's behaviour, unchanged |
| C2 | Page semantics: for `pagination_basis = GENERATED_SEGMENT` derivatives, label `[[page N]]` units as "segment N" and never "page N". Page citations (`LegalCitation.Format`, permalinks, `cite()`) are refused for such documents (`source_page_citation_permitted=false`) |
| C3 | Eligibility is the AND of: the existing single eligibility decision (publication, restriction, exclusion store); `TextQuality` (unreliable text is not indexed); v1 `quoting_permitted`; and C16 `research_eligibility` (`quoting_permitted`, `graph_evidence_permitted`, state). C16 never relaxes an existing gate |
| C4 | Anchors with no source page (image sequence, generated segment, unmapped reconstruction) are served from `corpus-v2/anchors.jsonl` as "image N" or "segment N". They are never converted to a v1 `ServedAnchor` with an invented page |
| C5 | Reconstructed pages are cited only through a checked mapping, and always as the **original's** page and hash. The reconstruction is offered as a readable aid labelled "searchable copy made locally; not the issued document" |
| C6 | Extracts and compilations: show "extract: pages X–Y of the judgment" or "one of N judgments in this file". Outcome and absence statements (`EvidenceAssessor` findings, holdings, workspace summaries) must not rest on a copy with `whole_work_claims_permitted=false` |
| C7 | Word files with screenshots: OCR text is searchable (subject to TextQuality) but never quoted. The UI points to the image ("see image 2 in the document"). `WORD_IMAGES_NOT_INVENTORIED` items are labelled "text may be incomplete: images not read" |
| C8 | Following ADR-0007, the persistent index's source digest includes C16 eligibility flags that change indexing (search-only versus not indexed), so a change re-indexes deterministically |
| C9 | The absence of a relationship is never shown as an absence of authority (contract P13). Lists that may be empty show the existing `absence` notice |

## 3. Graph (GraphBuilder, GraphStore, API)

| # | Requirement |
| --- | --- |
| G1 | Add a `GraphBuilder` step 7, "C16 corpus relationships". For each served relationship, build exactly the edge `adapters.graph_projection` describes: type, from, to, origin, temporal fields, uncertainty, `has_legal_effect`, and a builder verification value. The id comes from `c16_edge_id` (a .NET port, `GraphIds.C16EdgeId`) |
| G2 | Add node kinds `subject` (`SUBJ:`) and `chapter` (`CHAP:`) from `taxonomy.jsonl`. Taxonomy hierarchy edges are SUBJECT→STATUTE, STATUTE→CHAPTER and CHAPTER→PROVISION, using the existing `CONTAINS_PROVISION` for chapter→provision and the new types for the rest (pending Q2). `INSTCODE:<code>` resolves to `INST:<family key>` through `GraphIds.CodeByPrimaryDoc`/`InstrumentCatalog.FamilyKey`. An unresolvable code becomes a reference node, never a guessed instrument |
| G3 | `GraphStore.PublishAsync` keeps refusing any edge verification outside `BuilderValues`. DOCUMENTARY_CHECKED relationships publish as CANDIDATE edges plus a `graph_edge_reviews` row with the `RV-` ref. `legally_validated` overlays are **refused at AUTH-LEDGER v0**, and above v0 they need the v1 approval gate (appointment, artefact). Neither is written by the builder: review rows come from a separate, audited import step |
| G4 | The graph digest includes C16 edges, so start-up republishes when they change (existing mechanism) |
| G5 | Eligibility stays per request (ADR-0006 §4). C16 edges whose subject document is hidden disappear with it, as do classification edges. Taxonomy nodes are never hidden, because they name no document |
| G6 | API display rules: label the origins C16_FOLDER_PATH and C16_FILENAME_PATTERN as "Owner's filing label (not a finding)". Show the abbreviation reading and its alternatives. Never present ASSOCIATED_WITH_PROVISION as "interprets" or "applies" |
| G7 | `/api/graph/stats` reports `edges_by_origin`, including the C16 origins. `/api/reasoning/assess` must not treat classification edges as evidence: they are navigation only |

## 4. What the consumer must refuse

| Refuse | Code |
| --- | --- |
| Any C16 file outside a signed, checksummed bundle, or failing `exchange_issues` | bundle rejected |
| `legally_validated` at AUTH-LEDGER v0, or without a resolvable approval | `LEDGER_V0_NO_APPROVAL`, `APPROVAL_UNRESOLVED` |
| A label-based relationship marked DOCUMENTARY_CHECKED, LEGAL_REVIEWED or `is_finding` | `SCHEMA` |
| A reconstruction claiming carrier-issued origin; an extract claiming COMPLETE | `SCHEMA` |
| A page citation into a generated segment or an unmapped reconstruction | refused at the citation route |
| A quote from OCR text (any method OCR_*) | `OCR_QUOTING`; the quote is never returned |
| An identity or anchor whose copy is not a verified copy of the generation | quarantined (`C16_SUBJECT_NOT_SERVABLE`) |
| Any record matching the restricted register | bundle rejected (`RESTRICTED_MATERIAL`) |
| An unknown contract major (`mimamsa-corpus-contract/3.*`) or an unknown record kind | bundle rejected |
| Graph edges whose recomputed projection differs from `graph_projection` echoed by the producer | `C16_GRAPH_PROJECTION_MISMATCH` |
