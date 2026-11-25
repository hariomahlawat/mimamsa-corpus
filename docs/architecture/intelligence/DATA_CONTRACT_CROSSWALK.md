# Data contract crosswalk: R1 to future intelligence services

**R2 — INT-F03/F04/F06/F17. Proposed mapping for independent review.** Inspected application commit `9eeb04a457b532563d80610777d873ab24b52da5`, pre-adoption data contract v1.0.0 R1. It supersedes IC-01 outline, but is not merged or assumed accepted here. Canonical schemas remain unchanged. [Pinned contract](https://github.com/hariomahlawat/mimamsa-corpus/tree/9eeb04a457b532563d80610777d873ab24b52da5/app/contract) and [R1 limits](https://github.com/hariomahlawat/mimamsa-corpus/blob/9eeb04a457b532563d80610777d873ab24b52da5/app/contract/README.md#8-known-limits) govern current capabilities. Any future field or record kind requires established version/validator/review change control.

## 1. Record-kind field mapping

R = required in R1 (value may be null where schema allows); O = optional; U = not established by R1 / future enrichment; F = forbidden inference. These are service projections, not a competing bundle schema.

| Projection / service | R1 exact field(s) | Availability and handling |
|---|---|---|
| Source identity, get_document | document.doc_id; source_copy.sha256/bytes/mime_type/vault_path | R; copy ≠ document ≠ judgment; vault path never returned as arbitrary access capability |
| Alternate copies | document.alternate_copy_sha256; parent_doc_id | O; links only, no destructive deduplication or identity merge |
| Document descriptive fields | title, number, issuing_authority, issue_date, effective_date, doc_type, corpus_status, corpus_status_note, field_origin | R; nullable fields remain unknown; corpus_status display-only, F as legal applicability |
| Language/extraction/completeness | language, ocr_confidence, source_copy.page_count/completeness, text_method | O except text_method R; missing completeness not COMPLETE |
| Judgment identity | judicial.judgment_identity_id, court, bench, case_numbers, neutral_citation, reported_citations, parties, judges | O; metadata candidate per field_origin; unresolved identity remains unresolved; proceeding/opinion/proposition canonical records U |
| Source provenance | document.provenance, restriction | R; expose permitted provenance only, no access bypass; aliases evaluated against restriction register |
| Seven axes | document.status_axes.source_integrity/source_authenticity/evidence_fidelity/legal_applicability/legal_approval/publication/dependency_freshness | R on document only; cannot copy them to an edge or derivative as its own; v0 gate preserved |
| Upstream vs site publication | document.status_axes.publication; publication_record.subject.doc_id/source_copy_sha256, action/channel/actor_role/at/reason | Upstream status not site visibility; publication_record R fields where record present; site activation/local publication plus current exclusions determine eligibility; no automatic approval |
| Active exclusions | exclusion_update.sequence, issued_at, register_sha256, register_json, withdrawals[].doc_id/source_copy_sha256/reason | R envelope; at least one withdrawal identifier by schema; site accepted epoch U, implement serving contract; old signature not proof of latest |
| Page reference | common.page_anchor.source_copy_sha256 + page (1-based) | R; resolve exact immutable original page; R1 validator does not open PDF, importer/viewer must verify |
| Optional span | page_anchor.passage_id, char_start/end, paragraph_label, text_sha256, pipeline_version, quote | O; no durable global anchor ID; absent field means page-only, not precise span; paragraph labels only if source prints them |
| Derivative identity | derived_text.source_copy_sha256, doc_id, pipeline.name/version, text_path/text_sha256, page_marker | R; service key includes copy + pipeline name/version + derivative hash; never substitute newest derivative silently |
| Page quality | derived_text.pages[].page/method/char_count; ocr_engine/ocr_mean_confidence/low_confidence/has_word_boxes/text_sha256 | first three R, rest O; word boxes existence not coordinates guarantee; no confidence-to-fidelity promotion |
| Passage | derived_text.passages[].passage_id/page/char_start/char_end/text_sha256; paragraph_label/kind | first five R, rest O; offsets are within derivative page; validate bounds/hash; text_sha256 refers to passage as defined by schema |
| Quote permission | derived_text.quoting_permitted, evidence_fidelity; page_anchor.quote | first two R, quote O; quoting_permitted alone not proof of original verbatim fidelity; check against original/review as applicable |
| Candidate state | candidate.candidate_id/type (schema uses candidate_type), source_doc_id, anchors, extractor.name/version/artefact_commit, status, capability_restriction, evaluation_ref, payload | R; evaluation_ref nullable; status/restriction govern visibility; no inherited document axes or authority |
| Candidate review | candidate.review_ref, extractor.author_id/artefact_sha256, deferred_findings, supersedes_candidate_ids | O (conditionally required by validation); preserve provenance and restrictions; DOCUMENTARY_CHECKED is not legal approval |
| Graph relation | candidate.payload.relation/source_node/target.resolved/confidence/has_legal_effect; target.node_id/raw_reference; effective_date/evidence_text | first five R for graph_edge; remaining O/conditional; source_node string and resolved target do not guarantee typed semantic endpoints, version interval or scope; U see matrix |
| Provision versions | section-level ProvisionVersion | U per R1 known limits; document.effective_date/corpus_status not substitute; future minor/major per contract rules |
| Approval | approval_record.approval_record_id/appointment_id/approver/capacity/tier/scope/subject.kind/id/pinned_revision/artefact_sha256/decided_at/status | R if record exists, prohibited at v0; scope free text and no executable pack subject kind; F to infer typed grant |
| Appointment | appointment_record.appointment_id/appointing_authority/appointee/capacity/scope/valid_from/valid_until/artefact_sha256/revoked | R if record exists, prohibited at v0; scope free text; F to infer signing authority or execution scope |
| Working session | none in bundle by design | U site-only owner-scoped state; F to import/export into shared bundle or index |
| Agent workflow, final claim, serving epoch | none in R1 | U future service state; no fabricated canonical record or legal status |

## 2. Stable evidence projection and examples

PageKey = (source_copy_sha256, page_1based). SpanKey = (PageKey, pipeline name, pipeline version, derivative text SHA-256, passage ID, start/end, passage SHA-256) only when all needed components resolve unambiguously. Derivative pipeline identity may be resolved from the referenced derivative record; if anchor lacks sufficient binding to distinguish versions, return page-only with ambiguity rather than guessing. No invented anchor ID: a deterministic service reference may encode this tuple, with access checks on resolution. Original printed page labels and paragraph numbers are optional metadata, not substitutes for physical page index. A checked quote has separate verification record and actual source fidelity; OCR text is labelled derived.

Synthetic copy H, page 7 has derivative D1 with passage p7-1 at offsets 0..20, and D2 with same passage ID but changed text/offsets. PageKey remains (H,7). A D1 span resolves as explicitly historical if still permitted, or unavailable; it never resolves to D2 as current. An anchor with only H and page 7 opens the original page without fabricated highlight. An OCR-only hit with quoting_permitted=false is displayed as an OCR-derived search lead, not a verified quotation. If original page cannot be checked, report fidelity limitation.

Upstream PUBLISHED plus site not activated = not visible. Site published plus current signed exclusion covering the hash = denied. Candidate HIDDEN_FROM_USERS remains Admin diagnostics only even if document is published. Document axes may be provided as related source context, clearly named source_document_status, not candidate own approval. Missing field/state stays missing or explicitly UNESTABLISHED in the service projection; never invent values that appear canonical.

## 3. Typed relation policy (future adapter)

R1 graph_edge relation enum is reproduced below; typed endpoint/interval/scope fields are proposed enrichments, not R1 guarantees. Define conceptual kinds: I instrument/version as appropriate; P provision identity; V provision version; J judgment; C proceeding; O opinion; L scoped legal proposition; D source document; F form family/version. Resolution requires canonical mapping and review; unresolved raw references remain leads. Direction shown source → target; inverse navigation is a UI label, not an inferred inverse legal assertion. Every relationship needs supporting copy/page; precise span when available and required for material treatment; exact assertion provenance. Legal-effect flag per R1 is descriptive, not approval.

| R1 relation(s) | Proposed allowed endpoints / inverse label | Evidence and temporal policy |
|---|---|---|
| CITES_PROVISION, QUOTES_PROVISION | J/C/O/L/D → P or V; cited/quoted by | Mention/quote evidence; V may be unresolved; no applicability |
| APPLIES_PROVISION, INTERPRETS_PROVISION | C/O/L (J only discovery) → V or unresolved P; applied/interpreted by | Court voice, relevant issue and provision version/date; unresolved only lead |
| CITES_JUDGMENT | J/C/O/L/D → J/C; cited by | Actual citation; no treatment inference |
| FOLLOWS_PROPOSITION, DISTINGUISHES_PROPOSITION, OVERRULES_OR_LIMITS_PROPOSITION | L/O scoped to C → L with target opinion/proceeding; followed/distinguished/limited by | Exact material proposition and scope, competent court/opinion, evidence of treatment, legal effect/date when established; no case-wide generalization |
| AMENDS_PROVISION_VERSION, SUBSTITUTES_PROVISION_TEXT | I → V (new/affected version link resolved separately); amended/substituted by | Exact instrument, affected text and commencement; date unknown blocks applicability |
| INSERTS_PROVISION, OMITS_PROVISION | I → P/V; inserted/omitted by | Instrument and affected text, effective date/transition evidence |
| REPEALS_INSTRUMENT | I → I; repealed by | Exact repeal and commencement; savings separate |
| REPEALS_PROVISION | I → P/V; repealed by | Scope, repeal and commencement; savings separate |
| RE_ENACTED_AS | I/P/V → like-kind successor (explicit mapping); re-enactment of | Source-backed continuity, distinct versions, savings not inferred |
| COMMENCES | I → I/V; commenced by | Official commencement evidence and effective interval/date basis |
| SAVES_OR_TRANSITIONS | I/V → I/V with scoped saved rule/event basis; saved/transitioned under | Exact saving provision and conditions; no generic overlap inference |
| IMPLEMENTS | I/D → I/P/V; implemented by | Source authority and implementation scope; not automatic binding |
| SUPERSEDES_INSTRUMENT | I → I; superseded by | Explicit scope, authority and dates |
| POSSIBLY_SUPERSEDES_DOCUMENT | D → D; possible supersession by | Candidate discovery only |
| UPLOAD_REFERENCES_PROVISION, UPLOAD_REFERENCES_CASE | D → P/V or J/C respectively; referenced by upload | Staged/eligible publication controls, no legal authority by upload |
| PRESCRIBES_OR_EXEMPLIFIES_FORM | I/V/D → F; prescribed/exemplified by | Exact source and mandatory/specimen distinction, applicable version and approval |

These endpoint families are design proposals to reconcile with A4/A5 and B3 before implementation. Preserve raw R1 names; do not introduce new enum values in this PR. An adapter that cannot establish required endpoint types or dates exposes research-only unresolved lead, not a validated path. Record legal valid time separately from acquisition/review time and incident/procedural event dates. Future assertions require identity/revision, source proof, date basis/interval, scope and conflicting alternative assertions. Traverse only allow-listed, eligible directed relationships; inverse navigation does not reverse legal meaning. Path strength cannot exceed weakest material segment. Generic citation may target unresolved version. Synthetic split treatment: B follows A1 while distinguishing A2, no whole-case FOLLOWS. Same-name proceedings or alternate PDF reports never collapse without identity evidence. Test inverse, cycles, superseded versions, two competing date bases and incomplete graph plus independent adverse search.

## 4. Approval gap and phase mapping

R1 scope fields are text; approval subject kind is document/candidate/provision_version/template_version. There is no rule-pack digest binding. No typed executable grant may be inferred, even if reference validator accepts a future non-v0 record. Deterministic Engine §7 specifies the future typed binding, with synthetic tests and separate contract adoption/competent approval before activation.

B0 proposed design/PoCs (not deployed API); B1 CAP-US-01..07 and relevant CAP-RW source/search work uses copy/page mapping, current eligibility and explicit missing states. B2 full corpus/import/publication uses existing CAP-KA lifecycle and serving/restore semantics. B3 CAP-JI/CAP-SE/CAP-KG/CAP-RW/CAP-DS research depth uses typed candidate endpoint mapping where available and scoped session references. No new capability ID, schema change or Cycle 13 gate. Later tools in Agent Tool Contracts map to these services; approval/rule/agent/output artifacts remain future. Confirm exact actual service names and contract revision at reconciliation.

## 5. Verification required

Use actual R1 synthetic fixtures and independent oracle: validate page-only, derivative collision, OCR-only, unknown version, candidate hidden, upstream-vs-site visibility, source alias withdrawal, graph endpoint ambiguity and conflicting treatment, and rejection of inferred approval scope. No executable adapter or R1 validation run is claimed by this documentation. Reconcile with then-current application schema and revised contract before adoption.