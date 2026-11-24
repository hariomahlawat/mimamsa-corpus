# Mimamsa legal knowledge architecture

**Recorded:** 2026-11-24  
**Status:** Proposed target architecture supporting the owner-confirmed product direction. **Not a decision to migrate data, deploy services or activate legal assertions.**

## 1. Architectural objectives

- Maintain **full, lawful access** to the retained judgment corpus, including unreviewed research material.
- Answer natural-language military-law situations through explicit facts, date, service status, stage and competent-authority conditions.
- Represent the law as **immutable evidence plus versioned, reviewable interpretation**, not a collection of unconstrained generated answers.
- Connect statutory provisions to individual judgments, proceedings, legal propositions and procedural lessons.
- Preserve source and review histories, contrary evidence and source-access markings while sharing **all published documents and research features** across Admin and User.
- Let **Admin alone** continuously upload, review, publish, withdraw, replace or reprocess eligible policies, SOPs and references. The offline pipeline automatically extracts and proposes graph connections, and publishes to shared search only after Admin approval.
- Allow **all admitted users** to generate/review **temporary working documents** against Admin-published, source-backed form templates; no working draft can mutate shared corpus or its knowledge graph.
- Operate entirely offline at runtime on an air-gapped LAN.

## 2. Current source-system boundaries

| System | Existing role | Target boundary |
| --- | --- | --- |
| Private Hugging Face dataset | Central corpus: raw files, metadata, sections, text, relations | Upstream controlled source snapshot, not a runtime internet dependency |
| GitHub `raw-data` | Size-limited secondary copy | Additional evidence mirror, not assumed complete |
| GitHub code and audit branches | Schemas, pipelines, registers, reviews | Versioned build and audit controls |
| Working-store downloads | Some registered sources not elsewhere preserved | Preservation priority before release |
| `SOURCE-LIBRARY-C5` | Frozen source/copy registers | Immutable historical baseline |
| `AUTH-LEDGER` | Hash-chained source authentication overlay | Keep real version zero until owner approvals; source authentication only |
| 658 KB records and 53 cases | Curated research baseline | Preserve originals, propose reviewed overlays and corrections |
| Admin uploads at offline deployment | Future local policies, SOPs, instructions and reference material | Staged and automatically enriched; explicitly Admin-published, shared, versioned research sources; no automatic legal authority |
| Document Studio sessions | User-provided drafts, scanned forms and multi-document packs | Temporary user working data outside shared source vault, index, graph and legal authority registers |
| Template Registry | Source-linked forms, specimens, administrative templates and checks | Versioned derived reference layer based on reviewed source evidence; shared templates published only via Admin |

C10 (2026-11-24) reported 4,103 distinct source-copy hashes across stores, including 48 working-store-only copies, and 3,959 judicial source files. These are **snapshot facts**, not immutable design constants. The HF hosted bytes were not directly all verified at that time.

## 3. Logical architecture

```
EXTERNAL APPROVED ACQUISITION          LOCAL IN-APP ADMIN UPLOAD
   [separate online process]              [fully offline]
                |                              |
        verified import          Admin staging + safe parsing
                |                              |
                +-------------+----------------+
                              v
IMMUTABLE EVIDENCE VAULT -> SOURCE IDENTITY + DOCUMENT VERSIONS
                |                         |
        extraction/metadata         integrity/provenance
                v                         v
DOCUMENT PARAGRAPHS / PROVISIONS -> SOURCE AUTHENTICATION + REVIEWS
                |                         |
                +------------+------------+
                             v
       TEMPORAL LEGAL KNOWLEDGE GRAPH
      provisions -- cases -- propositions
               \     |       /
                facts / treatment / lessons
                             |
                +------------+------------+
                v                         v
      FULL-CORPUS SEARCH          SCENARIO APPLICABILITY
                \                         /
                 +---- EVIDENCE RESPONSE -+
                             |
               OFFLINE AUTHORISED USER
```

The diagram is a proposed logical dependency model. It does not prescribe individual microservices.

## 4. Source preservation and immutable identities

Use content-addressed source-copy objects keyed by SHA-256, accompanied by logical source identity, copy provenance, access marking, byte completeness and carrier fidelity.

Distinct entities:
- `SourceCopy`: a single byte-level file, exact hash and storage locations;
- `AdminSubmission` / `IngestionJob`: submitting Admin, staging/eligibility decision, parsing state, publication approval, extracted anchors and processing history;
- `LegalInstrument`: one Act, Rule set, regulation, order or notification as issued;
- `InstrumentVersion` / `ProvisionVersion`: historical operative text with evidenced effective interval and chain;
- `Judgment`: one judicial decision, regardless of the number of available PDFs;
- `Proceeding`: one appeal, petition, application or case resolved in or associated with a judgment;
- `JudgmentRendition` / `Opinion`: corrected/original/reporting forms, bench opinions, editorial boundaries;
- `EvidenceAnchor`: pinpointed source passage (copy, page, paragraph, text span/hash, extraction quality);
- `LegalProposition`: reviewable legal claim, scope, qualifications and contradicting evidence;
- `TreatmentEdge`: proposition-specific later court treatment, not simply a mention;
- `Scenario` / `MaterialFact` / `ApplicabilityPredicate` / `ChecklistItem` / `LegalLesson`;
- `ReviewDecision` / `Approval`: who decided what, at which source and rules revision.
- `FormTemplate` / `TemplateVersion`: identity, prescribed/specimen/admin category, source anchors, governing dates and documented fields;
- `DocumentConstraint` / `ChecklistRequirement`: verified requirements, conditions and severity, shared by generator and auditor;
- `WorkingDocumentSession` / `DocumentAuditFinding`: temporary private-by-session inputs, generated drafts, source-referenced findings and export artefacts, none automatically admitted to the shared corpus.

A PDF may contain multiple proceedings or judgments; multiple copies may represent one judgment. Never equate file hash, judgment and proceeding ID.

## 5. Graph relation types

| Relationship | Rule |
| --- | --- |
| `CITES_PROVISION` | Mention of provision, evidence located |
| `QUOTES_PROVISION` | Actual quotation; no interpretation implied |
| `APPLIES_PROVISION` | Court applies legal text in its reasoning or order |
| `INTERPRETS_PROVISION` | Identified passage addresses meaning/scope |
| `CITES_JUDGMENT` | Citation/match only, no treatment inferred |
| `FOLLOWS_PROPOSITION` | Passage demonstrates adoption of proposition |
| `DISTINGUISHES_PROPOSITION` | Passage identifies material limiting distinction |
| `OVERRULES_OR_LIMITS_PROPOSITION` | Exact scope of later rejection or limitation recorded |
| `AMENDS_PROVISION_VERSION` | Authenticated instrument, affected provision, commencement evidence |
| `SUPPORTS_CHECKLIST_ITEM` | Reviewed legal requirement or evidenced judicial lesson |
| `SUGGESTS_SCENARIO` | Retrieval candidate, not a legal conclusion |
| `UPLOAD_REFERENCES_PROVISION` | Provisional link from user-supplied policy to a section or Rule |
| `UPLOAD_REFERENCES_CASE` | Provisional link from a policy to a judgment |
| `POSSIBLY_SUPERSEDES_DOCUMENT` | Candidate version/supersession relation; does not change authority without supporting evidence |
| `PRESCRIBES_OR_EXEMPLIFIES_FORM` | Evidence-backed source to form/template version link, distinguishing required versus specimen status |
| `TEMPLATE_REQUIREMENT_FROM_SOURCE` | Source-anchored validation/checklist requirement with scope and review status |
| `AFFECTS_FORM_OR_CHECKLIST` | Candidate impact of amendment/judgment/new policy; requires re-evaluation before updates |

All substantive edges require `source_anchor`, source rendition, claimed time/jurisdiction, extraction/review status and contrary-evidence links. An absent treatment edge never establishes that no adverse authority exists.

## 6. Independent verification dimensions

Do not use a single `verified: true` flag. Track separately:

| Dimension | Example statuses |
| --- | --- |
| Byte integrity | `BYTE_VERIFIED` / `DECLARED_HASH_ONLY` / `NOT_CHECKED` / `MISMATCH` |
| Identity/fidelity | `IDENTITY_CONFIRMED` / `PROVISIONAL` / `DISPUTED` |
| Attribution/extraction | `AUTOMATED_CANDIDATE` / `DOCUMENTARY_CHECKED` / `INCORRECT` |
| Legal proposition | `RESEARCH_CANDIDATE` / `SOURCE_SUPPORTED` / `LEGAL_VALIDATED` |
| Temporal applicability | `EVIDENCED` / `PARTIAL_CHAIN` / `UNRESOLVED` / `NOT_APPLICABLE` |
| Authority/approval | `NONE` / `REVIEWED` / `FORMALLY_AUTHORISED` |

These are **conceptual states**, not modifications to existing AUTH-LEDGER status vocabulary. A mapping/migration would require separate approval, versioned specification and compatibility tests.

## 7. Time model

Store at least:
- **legal valid time**: date interval the law/proposition is evidenced as applicable, with amendment, saving, retrospective and commencement qualifications;
- **knowledge/review time**: when Mimamsa acquired and checked evidence or recorded a decision;
- **incident/decision time**: the user's legally relevant facts and decision date.

Historical questions query the appropriate provision version. Do not silently substitute the current consolidated law. Where the commencement chain is incomplete, expose a blocker rather than guessing. For scenarios and forms, keep conduct date/interval, proceeding-initiation date, relevant procedural-action date, and preparation/review date distinct; each constraint records its controlling event/date basis, applicable interval and transitional/saving authority. Substantive law and procedure may have different controlling dates. Do not choose a universal event date. Unknown or disputed material time facts block affected determinations.

## 8. Data platform proposal, not a committed choice

**Suggested initial architecture:** PostgreSQL as canonical relational store, typed graph edge tables with integrity constraints, full-text search indexed at provision/paragraph level, JSONB only for variable metadata, and an optional entirely local embedding index for candidate retrieval. The original PDFs remain outside the RDBMS in a checksum-verifiable evidence vault.

A separate graph/search/vector engine is **not presumed necessary**. Introduce one only after measured requirements cannot be met sufficiently with the simpler implementation.

AI can rank and discover candidate links; deterministic, reviewed rules govern time, jurisdiction, authority and procedural preconditions. Neither keyword matches nor embedding similarity confer legal authority.

**Operational-use gate:** enforce the separate source-fidelity, authority, temporal applicability, legal approval, publication and dependency state axes in [Document Studio section 3.2](DOCUMENT_STUDIO_AND_TEMPLATE_REGISTRY.md#32-research-versus-operational-drafting-gate) across both advisory and document engines. Legal approval must be attributable and scoped to the exact evidence/rule revision; no formal JAG validation without its actual approval artefact. Preserve all existing evidence gates and the authorship-neutral standard. Research-only material remains searchable.

**Common change-impact control:** reverse-index exact source/version/proposition dependencies to all downstream templates, constraints, checklists and advisories. On credible material amendment, controlling judgment, source withdrawal/correction or unresolved conflict, block affected definitive outputs and mandatory check passes for the implicated scope, including cached/in-flight results, until the necessary revalidation and approval. Unverified uploads alone create candidates, not automatic legal invalidation. Preserve unaffected/historically valid scope and prior approval history. See [Document Studio section 8.1](DOCUMENT_STUDIO_AND_TEMPLATE_REGISTRY.md#81-dependency-impact-and-stale-guidance-controls).

## 9. Ingestion and release pipeline

```
External approved acquisition or **Admin-only** in-app upload
-> authenticate Admin for mutations, stage privately, check common-corpus eligibility + file safety
-> preserve exact bytes + provenance + hash
-> extract text/OCR with page anchors; quality and document identity
-> classify, analyse references, generate provisional graph relationships in staging
-> **Admin reviews processing and explicitly publishes or rejects**
-> published source, metadata, passages and candidate edges become searchable by all
-> separate source/proposition/legal review if authority is asserted
-> controlled offline release for vetted external updates, or versioned local update for Admin-published sources
```

Original sources, historical records and prior review decisions are immutable. Corrections are append-only overlays or explicitly versioned replacements under the established authorisation rules.

A release contains a reproducible manifest, source-checksums, schema/rule versions, authentication state, evidence and review records, search indexes and model dependencies needed offline. Locally Admin-submitted sources, including pending and withdrawn items, are separately manifested and recoverable, without mutating signed baseline releases. Test network-denied execution, deterministic rebuild, rollback and recovery before declaring a release ready.

**Admin-only in-app document ingestion and publication control are first-phase capability requirements**, not post-hardening enhancements. See [Continuous document ingestion](CONTINUOUS_DOCUMENT_INGESTION.md). [Document Studio](DOCUMENT_STUDIO_AND_TEMPLATE_REGISTRY.md) is a separate working-file processing path, not an exception allowing users to publish source documents.

## 10. Search and user presentation

Full accessible research corpus search must **not** be gated by legal validation. But ranking and display must separate:
1. original source content and metadata;
2. unverified extracted summaries/outcomes/candidate edges;
3. independently checked evidence;
4. formally approved legal propositions and guidance.

For each judgment recommendation display **why relevant** (matched provision, exact passage and evidence state). Avoid ranking a case as binding or current solely due to textual similarity or citation count. Show adverse and limiting authority where known.

## 11. Privacy and operational data

Preserve complete, lawfully published judicial records, including printed names, ranks, service or medical details, subject to specific binding publication restrictions and access controls.

The initial app has exactly **two functional roles: Admin and User**. Both can access every **published** document and all search/graph/advisory functionality. Only Admin can upload, review staged documents, publish, replace, withdraw or reprocess source documents; these mutation endpoints require Admin checks. No rank/JAG tiers, per-document user restrictions or advanced role matrix. Pending sources are in Admin-only staging and invisible to shared search; publication is allowed only if the source can be shared with everyone in this deployment. Preserve access markings as provenance and check eligibility before publishing any text, snippets, embeddings or graph-derived output.

Ordinary incident questions are session data, not automatic corpus contributions. Only deliberate **Admin publication** makes source documents shared; staged/failed/rejected/withdrawn material does not appear in ordinary shared research. Admin publication is not a legal-validity approval.

Both Admin and User may submit working files via WORKING_DOCUMENT_PROCESSING for creation or audit, separate from Admin-only CORPUS_INGESTION for shared-source publication. These working files must be isolated from common corpus, shared search and embeddings; not exposed as source uploads or ingest jobs; not retained indefinitely by default. A source/template intended for shared library use still requires separate Admin ingestion and publication. Protect session boundaries without introducing additional research-user roles. Enforce authenticated session ownership for files, jobs, direct links, output downloads, AI contexts and derived caches. No cross-session access through identifiers, even for Admin using ordinary Document Studio; avoid sensitive working content in shared logs and clean up temporary derivatives. Use ordinary session isolation, local storage protection and reasonable deletion/retention defaults; do not build elaborate role-based case workspaces into the initial release.

**Minimum security at launch:** offline network boundary, basic Admin/User authentication and server-side Admin-only checks for corpus writes, file size/type limits, malware and malformed-file screening appropriate to the environment, isolated/least-privilege PDF/OCR/parser workers, untrusted-document prompt-injection isolation, file integrity hashes, backups and audit logging. Advanced hardening, granular data segregation and specialised controls may follow after the core capabilities are demonstrated.

## 12. Implementation sequence and quality gates

1. Preserve the 48 vulnerable copies, reconcile HF byte integrity, close source gaps.
2. Canonicalise document/judgment/proceeding identities and version relationships.
3. Provide full-corpus offline search against original copies, clearly labelled where unreviewed, plus **Admin-only upload, staged enrichment and publication** of eligible policies/SOPs.
4. Build provision-to-judgment and Admin-published-document-to-law **candidate** links and independent evaluation datasets.
5. Establish the [Form Discovery and Coverage Register](../product/FORM_DISCOVERY_AND_COVERAGE_REGISTER.md) and source-backed Form/Template Registry; inspect statutory appendices, all eight foundational MML copies and authorised regulations; log page coverage/gaps and classify authority, fidelity, applicability and legal approval independently.
6. Pilot Document Studio with identical reviewed constraints, independent source-derived test oracles, readiness reports, controlled date and dependency gates, session-isolated working inputs and no automated legal certification or draft publication.
7. Develop proposition-level passports, actual outcome extraction and treatment edges with measured precision.
8. Add material-fact scenario knowledge and verified procedural checks.
9. Pilot date-aware, evidence-grounded commander guidance and Document Studio review with adversarial test cases.
10. Release scoped, approved offline bundles with source and legal-status audits.

Every phase has separate technical evidence and legal-adviser acceptance where warranted. No current code change or schema migration is authorised by this document.
