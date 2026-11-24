# Continuous Admin-controlled document ingestion

**Recorded:** 2026-11-24  
**Status:** Owner-confirmed Admin-only source mutation and equal published-corpus access; detailed pipeline is a proposed design.  
**Related:** [ADR-0002](decisions/ADR-0002-SHARED_ACCESS_AND_CONTINUOUS_INGESTION.md), [Legal architecture](LEGAL_KNOWLEDGE_ARCHITECTURE.md).

## 1. Functional boundaries

There are exactly **two functional app roles**:

- **User:** full search, reading and use of every **published** document, summary, knowledge graph, checklist and commander-advisory feature. No document-management write permissions.
- **Admin:** all User capabilities plus document upload, staging review, publication, version replacement, withdrawal/unpublication and reprocessing.

There is no rank-based or JAG-only research access, private user-library model or per-document viewer restriction within the published corpus. **Only published material is shared.** Pending, rejected, quarantined, failed and withdrawn source materials are Admin-managed and not exposed to ordinary users.

**Exception explicitly not considered a source upload:** every admitted User and Admin may submit an existing charge-sheet, draft form or procedural file to a *temporary Document Studio review session*. Such working files do not enter the source vault, common search index, embedding store, shared graph or template registry. The Admin-only policy applies to **persistent shared-source publication and management**, not ordinary temporary working-file processing. See [Document Studio](DOCUMENT_STUDIO_AND_TEMPLATE_REGISTRY.md).

Only sources suitable for the entire deployment audience may be published. Source markings must be retained for provenance and assessed before publication. This is not a request to acquire restricted sources.

## 2. Admin ingestion and publication lifecycle

1. **Admin opens Add Document.** The app checks Admin privilege server-side for all upload and management endpoints. An ordinary User cannot submit even through direct API calls.
2. **Submit files into staging.** Initial supported formats may include PDF (including scans), DOCX, plain text and images for OCR where safe. Record file name, size, format, submitting Admin, upload time and optional declared issuer/title; do not trust claimed metadata as fact.
3. **Validate and quarantine.** Apply type/size controls, content-based format checks, malware/malformed-content screening suited to an offline installation, and deployment-wide source eligibility checks. Reject ineligible or dangerous files without exposing their data through shared search.
4. **Preserve exact bytes.** Compute SHA-256, store immutable original copy and provenance, detect exact duplicates and possible alternate versions.
5. **Automatically extract and analyse.** Perform local text extraction/OCR with page and paragraph anchors; collect extraction warnings; propose issuer, document type, issue/effective dates, version and legal subject; retain unknowns and source completeness.
6. **Construct provisional knowledge.** Detect mentions/quotations of Acts, Rules, judgments, policies, older SOPs and scenarios. Create anchored candidate edges, identify possible contradictions and supersession claims. Do not silently modify existing verified graph edges.
7. **Admin staging review.** Present original copy, extracted text, safety/eligibility result, metadata candidates, OCR completeness and suggested graph links. Admin may correct descriptive metadata, reject, retry or accept for publication.
8. **Admin explicitly publishes.** Only now do the source, extracted passages, snippets, embeddings and candidate graph links enter the **common published index** for all Users and Admin. Show source label `ADMIN_PUBLISHED_UNVERIFIED` (or a separately evidenced stronger status) and processing/quality flags.
9. **Ongoing changes.** Admin may upload a changed version, request reprocessing or withdraw a publication. Preserve historical original bytes, revision and audit history; remove withdrawn content from ordinary-user search, graph presentations and caches, including source-derived text. Avoid partial publication states.
10. **Independent legal review as required.** Admin publishing a document is not proof of authenticity, legal force, operative date or binding interpretation. Promote legal claims, mandatory checklist items or supersession relations only under the separate evidence and legal-review rules.

The entire workflow, including OCR, graph processing and search-index update, must work **offline on the LAN**, without cloud OCR, remote embeddings or online APIs.

## 3. Source and ingestion entities (proposed)

| Entity | Required concepts |
| --- | --- |
| `AdminSubmission` | Submitter, submission time, SHA-256, staging and publication decisions |
| `IngestionJob` | Job state, parser/model version, retry history, errors |
| `SourceCopy` | Immutable exact bytes, hash, completeness and provenance |
| `SourceDocument` | Identity and version candidates, issuer, kind, date, access marking |
| `ExtractedPassage` | Page/paragraph span, OCR confidence/quality, source hash |
| `CandidateRelationship` | Source and target IDs, relation type, exact quoted evidence, verification status |
| `PublicationRecord` | Admin identifier, publication/withdrawal time, version and eligible audience decision |
| `ReviewRecord` | Separate evidence/technical/legal reviewer findings and authority, if present |

A changed SOP is a new source copy and **version candidate**. A replacement must not destroy or rewrite the older original. Similarly, withdrawal changes what users can search; it does not erase the audit trail.

## 4. Distinct status axes

**Ingestion/publication:** `STAGED`, `PROCESSING`, `REVIEW_REQUIRED`, `REJECTED`, `FAILED`, `PUBLISHED`, `WITHDRAWN`.

**Source authority:** `USER_SUPPLIED_UNVERIFIED`, documentary authentication state, actual issuer/authority status, and temporal applicability as separately supported.

**Extracted graph relationships:** `CANDIDATE`, `DOCUMENTARY_CHECKED`, `LEGAL_REVIEWED`, etc., according to established governance.

These are design-level candidate vocabularies, **not** changes to the existing AUTH-LEDGER. Publication approval and legal authentication must never share a boolean field.

## 5. Graph enrichment and source trust

The system should generate candidate links such as:

- Admin-published SOP cites Army Rule 22: `UPLOAD_REFERENCES_PROVISION`.
- Policy names a judgment: `UPLOAD_REFERENCES_CASE`.
- Circular appears to concern a scenario: `RELATES_TO_SCENARIO`.
- New SOP claims to supersede an older order: `POSSIBLY_SUPERSEDES_DOCUMENT`.
- Published policy conflicts with a Rule: `POSSIBLE_CONFLICT_WITH_PROVISION`, with supporting excerpts.

Every edge records source copy, passage, parsing method, version and review state. User-facing graph navigation must distinguish a **reference** from an actual interpretation, current authority or judicial treatment. The system should flag possible issues, not decide legal conflicts automatically.

## 6. Baseline security and capability priority

Keep the product simple. **Do not build a large RBAC matrix.** Implement two roles and restrict *all* source-mutation and staging endpoints to Admin.

Minimum controls necessary before supporting uploads: offline deployment boundary, safe file-type/size checks, isolated low-privilege document processing, untrusted-PDF/OCR text isolation from model instructions, original-file hashes, backups, basic event audit and user admission/authentication.

Once baseline controls are in place, prioritise **working upload → automated extraction → graph linking → Admin publication → shared search**. More advanced cyber-hardening can be planned after useful capability is established.

## 7. Acceptance tests

- An ordinary User can open every published judgment, SOP and summary, use all research/advisory features and inspect published candidate graph links.
- A User can submit a temporary draft for Document Studio audit, but cannot turn that draft into an Admin source-ingestion job, even by API manipulation.
- A User cannot upload, create jobs, review staged files, publish, withdraw, replace or reprocess through UI or direct API; attempted writes have no effect.
- Admin uploads a valid SOP; the original and candidate graph relationships are processed and reviewable in staging but not publicly searchable.
- Admin publishes after reviewing quality/eligibility; the source and labelled candidate links appear consistently to all users.
- An Admin-uploaded revised SOP preserves both versions; a claimed supersession does not automatically invalidate an older source.
- Withdrawing a publication removes that source and its snippets/embeddings/derived links from ordinary research results without deleting the original audit evidence.
- An incomplete OCR result is shown to Admin before publication and retains a completeness warning afterward if published.
- Admin uploads a maliciously worded document; its contents cannot invoke instructions or secretly promote legal authority.
- An access-marked source unsuitable for all app users is not published or exposed indirectly.
- Admin publication does not change authenticated law, authoritative procedural obligations or AUTH-LEDGER state.
- Restart an interrupted job; recover safely and preserve the original bytes.
- Run all stages offline without internet connectivity or external service dependencies.

## 8. Scope and sequencing

This is a **core early product capability**, alongside full-corpus search, provision/judgment graph development and the commander scenario experience. No app code, corpus publication, new source acquisition or legal-status promotion is authorised solely by this document.
