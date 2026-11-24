# ADR-0001: Scenario-driven, evidence-grounded Mimamsa product direction

- **Date:** 2026-11-24
- **Decision state:** Product direction **owner-confirmed**; target architecture **proposed** and subject to implementation, security and legal review.
- **Scope:** Product capability and architecture intent only. This ADR does not approve specific legal propositions, applications, source acquisitions or PR merges.
- **Related:** [Vision](../../product/PRODUCT_VISION.md), [Use cases](../../product/COMMANDER_USE_CASES.md), [Architecture](../LEGAL_KNOWLEDGE_ARCHITECTURE.md), [Advisory design](../SCENARIO_ADVISORY_ENGINE.md).

## Context

A conventional keyword database requires unit commanders to know the Act, Rule or case first. Real users ask questions such as “a sepoy was drunk on duty”, “a JCO refuses to sign a charge-sheet” and “a jawan has a second marriage”. The corpus already contains thousands of judicial source files, but automated outcomes and candidate holdings have shown material errors. Restricting search to the curated cases would discard useful research breadth; treating all extracted data as validated would create serious risk.

The product must run on an air-gapped LAN. Source integrity, applicable legal versions, binding precedent, factual conditions and competent authority cannot safely be determined from embedding similarity or generative text alone.

## Direction adopted

1. **Make all legally accessible retained judgment sources searchable**, even when their metadata, summary or legal conclusions are unreviewed. Clearly label status and restrictions.
2. **Build a connected statute–judgment–proposition knowledge graph** with versioned statutory provisions, judgment/proceeding identities, source-anchored relationships and subsequent treatment.
3. **Support plain-English, situation-first commander queries** with material-fact questions and stage-aware, evidence-linked ways forward, checklists, lessons and source access.
3a. **Allow every admitted app user to upload eligible new policies, SOPs and reference material**, with automatic offline extraction, provisional indexing and suggested graph connections; all accepted documents and features are shared with all app users.
4. **Separate source search, candidate research enrichment and approved legal propositions/procedures**; never silently promote one level to another.
5. **Preserve complete lawfully published judicial originals** without masking names, ranks, service or medical details solely due to their presence in court documents, subject to binding restrictions and access controls.
6. **Keep ordinary real-incident query text separate** from the shared legal corpus; intentionally uploaded source material is explicitly shared with every app user.
7. **Operate fully offline at runtime** with auditable import and release controls.
8. **Preserve existing evidence governance:** frozen 658 research records and 53 cases, AUTH-LEDGER genesis/version zero and established source-authority policy remain unchanged without separate approval.

## Proposed implementation, not yet adopted

A content-addressed evidence vault, canonical entity/relationship tables (PostgreSQL initially proposed), optional local semantic retrieval, deterministic dated applicability engine, model-assisted language understanding and answer explanation, and controlled source/review overlays. Engine selection, schemas, deployment admission controls and specific pilot routes require separate design review. No role-based user access tiers are proposed.

## Alternatives considered

| Option | Reason not selected as the main product model |
| --- | --- |
| Only the original 53 curated cases | Insufficient searchable breadth; thousands of retained judgments remain useful as research material |
| Generic LLM answering directly from PDFs | Poor attribution, temporal applicability, procedure and legal-proposition reliability |
| Document search only | No fact-dependent steps, checklist provenance or treatment analysis |
| Fully prewritten Q&A catalogue | Brittle for changing facts, law versions and unusual cases |
| Separate graph, vector and search infrastructure from day one | Unnecessary complexity before benchmarks justify multiple stores |

## Consequences and controls

- More complex canonical identity and review schemas are necessary; this must be designed incrementally.
- Existing candidate outcomes and legal-proposition extraction cannot be treated as authoritative.
- Every mandatory checklist element and treatment claim needs a reviewable source trail.
- Scenario outputs must be conditional, minimise decisive follow-up questions and abstain/escalate on unresolved law.
- Evaluation must include independent, adversarial legal-data tests and temporal variants, not merely passing software tests.
- Source preservation takes precedence over enriching endangered or unavailable files.
- In-app uploads must retain original bytes and provenance; automatic links, supersession and legal claims remain candidates until evidenced and reviewed.
- All accepted documents are shared equally with all app users; eligibility checks happen before shared ingestion. Standard offline cyber security is baseline, with more advanced hardening deferred.

## Not decided

**Clarifying decision:** [ADR-0002](ADR-0002-SHARED_ACCESS_AND_CONTINUOUS_INGESTION.md) fixes the shared-access and continuous-upload requirements, without authorising application code or source promotions.

No PR merge, data migration, PostgreSQL schema, graph engine, model selection, HF upload, real ledger entry, source acquisition, operational advice template or legal conclusion is authorised by this ADR. Future changes need explicit scope, evidence and review. Formal legal/JAG validation remains required where applicable.

## Revisit triggers

Revisit this ADR if independent evaluation shows the proposed scenario model is insufficient, evidence/review controls cannot enforce safe legal applicability, corpus access restrictions materially change the search scope, or offline benchmarks warrant a different data architecture.
