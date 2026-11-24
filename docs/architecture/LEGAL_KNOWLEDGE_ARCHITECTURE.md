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

C10 (2026-11-24) reported 4,103 distinct source-copy hashes across stores, including 48 working-store-only copies, and 3,959 judicial source files. These are **snapshot facts** from the C10 reconciliation records, which are not an ancestor of this branch's base. They are not immutable design constants. The HF hosted bytes were not directly all verified at that time.

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
- `ReviewDecision` / `Approval` / `Appointment`: who decided what, in which capacity and approval tier, under which recorded appointment, at which source and rules revision (Document Studio 3.3).
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
| `UPLOAD_REFERENCES_PROVISION` | Provisional link from an Admin-published policy or SOP to a section or Rule |
| `UPLOAD_REFERENCES_CASE` | Provisional link from a policy to a judgment |
| `POSSIBLY_SUPERSEDES_DOCUMENT` | Candidate version/supersession relation; does not change authority without supporting evidence |
| `PRESCRIBES_OR_EXEMPLIFIES_FORM` | Evidence-backed source to form/template version link, distinguishing required versus specimen status |
| `TEMPLATE_REQUIREMENT_FROM_SOURCE` | Source-anchored validation/checklist requirement with scope and review status |
| `AFFECTS_FORM_OR_CHECKLIST` | Candidate impact of amendment/judgment/new policy; requires re-evaluation before updates |
| `REPEALS_INSTRUMENT` / `REPEALS_PROVISION` | Repealing instrument and provision, the repealed instrument or provision, and commencement evidence |
| `OMITS_PROVISION` | Amending instrument omits a section, sub-section or Rule; the provision keeps its historical versions and has no operative text after commencement, even though the parent Act is in force |
| `SUBSTITUTES_PROVISION_TEXT` / `INSERTS_PROVISION` | Amending instrument replaces or inserts text; creates a new `ProvisionVersion` with its own interval |
| `RE_ENACTED_AS` | Correspondence between a repealed provision and its successor in a re-enacting instrument (for example IPC to BNS, CrPC to BNSS, Evidence Act to BSA), at provision level, with the correspondence source. Correspondence is not textual or legal equivalence: differences must be anchored separately |
| `COMMENCES` | Commencement notification or provision bringing an instrument or provision into force on a date, possibly for part of it only |
| `SAVES_OR_TRANSITIONS` | Saving, transitional or repeal-and-savings provision continuing prior law for a stated scope (pending proceedings, prior conduct, acts done), with conditions |
| `IMPLEMENTS` | Rules, regulations or notifications made under, or implementing, a stated Act or provision, with the enabling-power citation |
| `SUPERSEDES_INSTRUMENT` | Evidenced instrument-level replacement (for example one set of Rules replacing an earlier set) with the date and scope; distinct from the candidate `POSSIBLY_SUPERSEDES_DOCUMENT` |

The table is **not exhaustive**. These edge types are required for the time model in section 7. Further types need the same anchor and review fields. Edges with legal effect (every row except the citation, quotation, scenario-suggestion and upload-reference rows) are candidates until verified under the evidence policy, and the gate requires Legal Reviewer verification (Document Studio 3.3) before an output relies on them.

**Mapping from the existing corpus relation vocabulary** (`relations.jsonl` types in the root `CLAUDE.md` brief). Corpus edges are imported as **candidates**, keeping their `evidence`, `effective_date` and `confidence`. The corpus confidence values map onto review status: `extracted` and `llm_proposed` become `CANDIDATE`, and `human_verified` becomes `DOCUMENTARY_CHECKED`. A corpus `human_verified` mark does not by itself amount to a Legal Reviewer approval.

| Corpus type | Graph relation(s) |
| --- | --- |
| `amends` / `amended_by` | `AMENDS_PROVISION_VERSION`; refine to `SUBSTITUTES_PROVISION_TEXT`, `INSERTS_PROVISION` or `OMITS_PROVISION` when the footnote or instrument specifies. Stored once and rendered in both directions |
| `supersedes` / `superseded_by` | `SUPERSEDES_INSTRUMENT` when evidenced, otherwise `POSSIBLY_SUPERSEDES_DOCUMENT` |
| `repeals` | `REPEALS_INSTRUMENT` / `REPEALS_PROVISION`, plus `RE_ENACTED_AS` and `SAVES_OR_TRANSITIONS` where the repealing instrument re-enacts or saves |
| `overrules` / `overruled_by` | `OVERRULES_OR_LIMITS_PROPOSITION`, scoped to the proposition. A judgment-level "overruled" status is a derived view, never asserted wholesale |
| `follows` | `FOLLOWS_PROPOSITION` |
| `distinguishes` | `DISTINGUISHES_PROPOSITION` |
| `cites` | `CITES_JUDGMENT` or `CITES_PROVISION` |
| `implements` | `IMPLEMENTS` |

The corpus document `status` values (`in_force`, `amended`, `partly_repealed`, `repealed`, `superseded`, `overruled`, `unknown`) are displayed as a derived summary computed from these edges for a stated date. They do not override the provision-level graph.

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

Two further dimensions are used in section 8 and in Document Studio: **Publication** (`STAGED` / `PUBLISHED` / `WITHDRAWN`) and **Dependency freshness** (`CURRENT_FOR_CHECKED_SCOPE` / `REVALIDATION_REQUIRED` / `BLOCKED`).

These are **conceptual states**, not modifications to existing AUTH-LEDGER status vocabulary. A mapping/migration would require separate approval, versioned specification and compatibility tests.

**Vocabulary reconciliation.** One table relates the three blueprint vocabularies to the controlling SOURCE_AUTHORITY_POLICY v1 fields. Statuses that recur across axes are always qualified by their axis in data and UI, for example `ingestion.REVIEW_REQUIRED`, `approval.REVIEW_REQUIRED` and `freshness.BLOCKED`. A value on one axis never sets another.

| Concern | Architecture 6 dimension | Document Studio 3 axis | Ingestion 4 axis | Policy v1 field |
| --- | --- | --- | --- | --- |
| Who issued the document and what kind of authority it is | Authority/approval (authority part) | Form authority/type (registry-specific) | Source authority | `document_authority` |
| How the copy reached us | Byte integrity, plus provenance | (inherited from source) | Source authority (carrier) | `carrier_provenance` |
| Copy faithfulness | Identity/fidelity | Discovery/reproduction fidelity | Documentary authentication state | `copy_fidelity`, `instrument_identity` |
| Temporal chain | Temporal applicability | Applicability | Temporal applicability | `amendment_chain_status` |
| Extraction and edges | Attribution/extraction | (not applicable) | Extracted graph relationships | (none; review records) |
| Legal approval | Legal proposition; Authority/approval (approval part) | Legal approval (tiers T0 to T2, Document Studio 3.3) | (not set by ingestion) | (none; AUTH-LEDGER and approval artefacts) |
| Distribution | Publication | Publication | Ingestion/publication | (none) |
| Downstream currency | Dependency freshness | Dependency/release freshness | (triggers only) | (none) |

Every in-app `SourceDocument` carries the four v1 fields and `authority_rationale`. Initial values for an Admin upload are `carrier_provenance=USER_SUPPLIED` (the policy's value for a locally supplied copy, whoever uploads it), `document_authority=UNKNOWN`, `copy_fidelity=HASH_ONLY` and `amendment_chain_status=NOT_CHECKED`. A value is raised only on recorded evidence under the policy. Release-bundle sources carry the values recorded upstream.

## 7. Time model

Store at least:
- **legal valid time**: date interval the law/proposition is evidenced as applicable, with amendment, saving, retrospective and commencement qualifications;
- **knowledge/review time**: when Mimamsa acquired and checked evidence or recorded a decision;
- **incident/decision time**: the user's legally relevant facts and decision date.

Historical questions query the appropriate provision version. Do not silently substitute the current consolidated law. Where the commencement chain is incomplete, expose a blocker rather than guessing. For scenarios and forms, keep conduct date/interval, proceeding-initiation date, relevant procedural-action date, and preparation/review date distinct; each constraint records its controlling event/date basis, applicable interval and transitional/saving authority. Substantive law and procedure may have different controlling dates. Do not choose a universal event date. Unknown or disputed material time facts block affected determinations.

### 7.1 Named temporal acceptance cases

The model must be able to **express** each of the following cases. These are representational tests, not legal conclusions. Each fixture must take instrument identities, section numbers, commencement dates and holdings from verified sources under the evidence policy. The descriptions below come from the root `CLAUDE.md` brief and are unverified until then.

| ID | Case (as recorded in the brief) | The system must be able to |
| --- | --- | --- |
| TA-01 | Army Act ss.75 and 76 (field punishment), recorded as omitted in 1992 | Represent `OMITS_PROVISION` from the evidenced amending instrument with a `COMMENCES` date. Return the historical text for an as-of date before commencement and "omitted, no operative text" after it, while the Army Act stays in force. Block a checklist or template constraint that depends on these sections for post-commencement dates |
| TA-02 | Army Act s.127, recorded as omitted in 1992 | Same as TA-01 at section level, with the section-level record (`act-army-1950#s127`) carrying its own amendment history |
| TA-03 | IPC to BNS, CrPC to BNSS, Evidence Act to BSA, from 1 July 2024 | Represent `REPEALS_INSTRUMENT`, provision-level `RE_ENACTED_AS` correspondence, `COMMENCES` and `SAVES_OR_TRANSITIONS`. Resolve substantive and procedural controlling dates separately (conduct before and proceeding after commencement). Surface or block on the saving provision when it is unresolved. Never present correspondence as identical wording |
| TA-04 | Dharamvir Singh (entitlement under the 1982 Rules) and the later Supreme Court authority on the 2008 Rules recorded in the brief | Represent the two Rules sets as separate instruments with `SUPERSEDES_INSTRUMENT` and `IMPLEMENTS` only as evidenced. Scope each judgment's propositions to the Rules version it construed. Return different authorities for claims governed by each version. Do not treat the earlier judgment as wholly overruled unless a scoped `OVERRULES_OR_LIMITS_PROPOSITION` edge is verified |
| TA-05 | Parashotam (Supreme Court, 2023) on High Court writ jurisdiction against AFT orders | Represent a proposition about forum and jurisdiction with treatment edges to earlier authorities, dated by the judgment. Surface it, with its verification state, in a scenario about challenging an AFT order. Show adverse or limiting authority when known |

For each case, an `llm_proposed` or unverified edge must not change a definitive output, and the absence of an edge must not be reported as absence of adverse authority.

## 8. Data platform proposal, not a committed choice

**Suggested initial architecture:** PostgreSQL as canonical relational store, typed graph edge tables with integrity constraints, full-text search indexed at provision/paragraph level, JSONB only for variable metadata, and an optional entirely local embedding index for candidate retrieval. The original PDFs remain outside the RDBMS in a checksum-verifiable evidence vault.

A separate graph/search/vector engine is **not presumed necessary**. Introduce one only after measured requirements cannot be met sufficiently with the simpler implementation.

AI can rank and discover candidate links; deterministic, reviewed rules govern time, jurisdiction, authority and procedural preconditions. Neither keyword matches nor embedding similarity confer legal authority.

**Operational-use gate:** enforce the separate source-fidelity, authority, temporal applicability, legal approval, publication and dependency state axes in [Document Studio section 3.2](DOCUMENT_STUDIO_AND_TEMPLATE_REGISTRY.md#32-research-versus-operational-drafting-gate) across both advisory and document engines. Legal approval must be attributable, recorded at the tier required for the output class through the approval path in [Document Studio 3.3](DOCUMENT_STUDIO_AND_TEMPLATE_REGISTRY.md#33-legal-approval-path-on-an-air-gapped-site-proposed-blocking-open-decision), and scoped to the exact evidence/rule revision; no formal JAG validation without its actual approval artefact. Preserve all existing evidence gates and the authorship-neutral standard. Research-only material remains searchable.

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

A release contains a reproducible manifest, source-checksums, schema/rule versions, authentication state, evidence and review records, search indexes and model dependencies needed offline. Locally Admin-submitted sources, including pending and withdrawn items, are separately manifested and recoverable, without mutating signed baseline releases. Section 9.1 defines how releases and local sources are reconciled. Test network-denied execution, deterministic rebuild, rollback and recovery before declaring a release ready.

### 9.1 Release updates and local sources

A deployment receives changes through two channels: **verified external release bundles** and **local Admin uploads**. The rules below reconcile them.

1. **Import verification.** Verify the bundle manifest signature and every checksum offline before changing anything. Any failure rejects the whole bundle. Imports are atomic and can be rolled back to the prior state.
2. **Identity and de-duplication.** `SourceCopy` identity is the SHA-256 of the bytes. If a bundle contains bytes already uploaded locally, keep one `SourceCopy`, record both provenances (bundle record and `AdminSubmission`) as aliases, and do not duplicate it in search.
3. **Collision.** Different bytes claiming the same logical identity (same instrument, version or judgment) are preserved as alternate copies or version candidates and linked as possible duplicates. Never auto-merge them. The Admin resolves descriptive identity. Legal identity and fidelity follow the source authority policy.
4. **Precedence.** Verified bundle records (authentication states, reviewed edges, signed approvals) take precedence over local *candidate* states for the same item. An import never deletes or silently rewrites local submissions, local publication decisions or local review records; a conflict is queued for Admin and, where legal, for Legal Reviewer decision. A bundle withdrawal of a source withdraws the bundle's publication. If the same bytes were also published locally, the Admin is prompted and the item is flagged until decided.
5. **Local legislation and judgments.** A locally uploaded amending Act, Rule, notification or judgment, once Admin-published, creates candidate `LegalInstrument`/`InstrumentVersion`/`ProvisionVersion` or `Judgment`/`Proceeding` nodes. These have identity `PROVISIONAL`, temporal state `UNRESOLVED` and v1 fields as in section 6, with candidate edges such as `AMENDS_PROVISION_VERSION`, `OMITS_PROVISION`, `COMMENCES` or `CITES_JUDGMENT`. They are searchable and navigable as research. They never change the operative timeline used for definitive outputs until documentary and fidelity verification is recorded and, for edges with legal effect, a Legal Reviewer verifies them (Document Studio 3.3). That can happen on site or through a later signed release. Meanwhile they can still raise impact triggers under the credibility criteria in Document Studio 3.3.
6. **Edge re-derivation.** After an import or local publication, re-run candidate link derivation deterministically over the merged graph, recording the extractor version. Reviewed or verified edges are never deleted or changed automatically. Candidate edges are replaced by new versions. Edges whose anchor revision changed are marked for re-review.
7. **Pinned approvals and bindings.** Approvals and template bindings pin exact revisions and never carry forward to a new revision. A template bound to an old revision keeps that binding, and its freshness becomes `REVALIDATION_REQUIRED` if a dependency changed. A new revision starts unapproved unless the bundle carries a signed approval for it.
8. **Change lists drive impact assessment.** Every bundle carries a change list (added, updated, newly superseded, withdrawn, status changed). Each entry, and each local publication, replacement or withdrawal, is an impact trigger for [Document Studio 8.1](DOCUMENT_STUDIO_AND_TEMPLATE_REGISTRY.md#81-dependency-impact-and-stale-guidance-controls): affected scopes are blocked, and caches and compiled rule sets are invalidated before the next response or export.

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

Both Admin and User may submit working files via WORKING_DOCUMENT_PROCESSING for creation or audit, separate from Admin-only CORPUS_INGESTION for shared-source publication. These working files must be isolated from common corpus, shared search and embeddings; not exposed as source uploads or ingest jobs; not retained indefinitely by default. A source/template intended for shared library use still requires separate Admin ingestion and publication. Protect session boundaries without introducing additional research-user roles. Enforce authenticated session ownership for files, jobs, direct links, output downloads, AI contexts and derived caches. No cross-session access through identifiers, even for Admin using ordinary Document Studio; avoid sensitive working content in shared logs and clean up temporary derivatives. The audit log holds metadata only, never working content. Working-session data is excluded from backups by default, or, if backed up, kept under the same ownership, retention and deletion rules. Use ordinary session isolation, local storage protection and reasonable deletion/retention defaults; do not build elaborate role-based case workspaces into the initial release.

**Minimum security at launch:** offline network boundary, basic Admin/User authentication and server-side Admin-only checks for corpus writes, file size/type limits, malware and malformed-file screening appropriate to the environment, isolated/least-privilege PDF/OCR/parser workers, untrusted-document prompt-injection isolation, file integrity hashes, backups (of the shared corpus and state; working sessions as above) and metadata-only audit logging. Advanced hardening, granular data segregation and specialised controls may follow after the core capabilities are demonstrated.

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
