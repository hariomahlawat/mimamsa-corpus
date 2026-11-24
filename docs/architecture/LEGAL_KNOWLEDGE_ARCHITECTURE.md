# Mimamsa legal knowledge architecture

**Recorded:** 2026-11-24  
**Status:** Proposed target architecture supporting the owner-confirmed product direction. **Not a decision to migrate data, deploy services or activate legal assertions.**

## 1. Architectural objectives

- Maintain **full, lawful access** to the retained judgment corpus, including unreviewed research material.
- Answer natural-language military-law situations through explicit facts, date, service status, stage and competent-authority conditions.
- Represent the law as **immutable evidence plus versioned, reviewable interpretation**, not a collection of unconstrained generated answers.
- Connect statutory provisions to individual judgments, proceedings, legal propositions and procedural lessons.
- Preserve source and review histories, contrary evidence and source-access restrictions.
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

C10 (2026-11-24) reported 4,103 distinct source-copy hashes across stores, including 48 working-store-only copies, and 3,959 judicial source files. These are **snapshot facts**, not immutable design constants. The HF hosted bytes were not directly all verified at that time.

## 3. Logical architecture

`
EXTERNAL RESEARCH / APPROVED ACQUISITION  [internet-connected, separate]
                |
          verified import package
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
`

The diagram is a proposed logical dependency model. It does not prescribe individual microservices.

## 4. Source preservation and immutable identities

Use content-addressed source-copy objects keyed by SHA-256, accompanied by logical source identity, copy provenance, access marking, byte completeness and carrier fidelity.

Distinct entities:
- `SourceCopy`: a single byte-level file, exact hash and storage locations;
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

Historical questions query the appropriate provision version. Do not silently substitute the current consolidated law. Where the commencement chain is incomplete, expose a blocker rather than guessing.

## 8. Data platform proposal, not a committed choice

**Suggested initial architecture:** PostgreSQL as canonical relational store, typed graph edge tables with integrity constraints, full-text search indexed at provision/paragraph level, JSONB only for variable metadata, and an optional entirely local embedding index for candidate retrieval. The original PDFs remain outside the RDBMS in a checksum-verifiable evidence vault.

A separate graph/search/vector engine is **not presumed necessary**. Introduce one only after measured requirements cannot be met sufficiently with the simpler implementation.

AI can rank and discover candidate links; deterministic, reviewed rules govern time, jurisdiction, authority and procedural preconditions. Neither keyword matches nor embedding similarity confer legal authority.

## 9. Ingestion and release pipeline

`
Acquire (approval) -> preserve bytes -> verify identity/hash -> extract text
-> quality/relevance -> candidate relationships -> source review
-> proposition and temporal review -> approval where required
-> signed/checksummed offline release -> controlled LAN import
`

Original sources, historical records and prior review decisions are immutable. Corrections are append-only overlays or explicitly versioned replacements under the established authorisation rules.

A release contains a reproducible manifest, source-checksums, schema/rule versions, authentication state, evidence and review records, search indexes and model dependencies needed offline. Test network-denied execution, deterministic rebuild, rollback and recovery before declaring a release ready.

## 10. Search and user presentation

Full accessible research corpus search must **not** be gated by legal validation. But ranking and display must separate:
1. original source content and metadata;
2. unverified extracted summaries/outcomes/candidate edges;
3. independently checked evidence;
4. formally approved legal propositions and guidance.

For each judgment recommendation display **why relevant** (matched provision, exact passage and evidence state). Avoid ranking a case as binding or current solely due to textual similarity or citation count. Show adverse and limiting authority where known.

## 11. Privacy and operational data

Preserve complete, lawfully published judicial records, including printed names, ranks, service or medical details, subject to specific binding publication restrictions and access controls.

Separate actual unit incident facts and users' queries into role-controlled case/session storage, protected from the shared index, telemetry and model training by default. Apply retention, access audits and need-to-know controls independently of public-source preservation policy.

## 12. Implementation sequence and quality gates

1. Preserve the 48 vulnerable copies, reconcile HF byte integrity, close source gaps.
2. Canonicalise document/judgment/proceeding identities and version relationships.
3. Provide full-corpus offline search against original copies, clearly labelled where unreviewed.
4. Build provision-to-judgment **candidate** links and independent evaluation datasets.
5. Develop proposition-level passports, actual outcome extraction and treatment edges with measured precision.
6. Add material-fact scenario knowledge and verified procedural checks.
7. Pilot date-aware, evidence-grounded commander guidance with adversarial test cases.
8. Release scoped, approved offline bundles with source and legal-status audits.

Every phase has separate technical evidence and legal-adviser acceptance where warranted. No current code change or schema migration is authorised by this document.
