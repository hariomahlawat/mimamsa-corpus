# ADR-0003: Document Studio and source-backed Form/Template Registry

- **Date:** 2026-11-24
- **Decision state:** **Owner-confirmed product direction** for document preparation, checking and review. Detailed architecture, form selection and specific legal checks remain proposed pending source/technical/legal review.
- **Scope:** All-user temporary working-document assistance, source-backed templates and procedural checklists. Does **not** authorise operational issuance, code changes, corpus transfers or legal validation.
- **Related:** [Document Studio specification](../DOCUMENT_STUDIO_AND_TEMPLATE_REGISTRY.md), [Product vision](../../product/PRODUCT_VISION.md), [ADR-0001](ADR-0001-SCENARIO_DRIVEN_EVIDENCE_GROUNDED_PRODUCT.md), [ADR-0002](ADR-0002-SHARED_ACCESS_AND_CONTINUOUS_INGESTION.md).

## Context

Commanders and staff require help not only locating the applicable Army Act/Rules and judgments but also preparing and reviewing legally significant documents. Prescribed forms and authoritative specimens may be published in Army Rules and appendices, the Manual of Military Law, Defence Service Regulations and applicable instructions. Versions, competent signatories, mandatory contents and procedural conditions can change. Free-form AI drafting without exact-source fidelity risks generating an incorrect form, incomplete charge or misleading declaration of legal compliance.

A separate issue is access: the owner has restricted **source-library ingestion and publication** to Admin but wants **every app user** to create/review working documents. These are different classes of file operation.

## Decisions

1. **Introduce Document Studio** as a core product capability for creating, reviewing, correcting and downloading legal/procedural working documents, and for checking complete procedural-document packs where applicable.
2. **Introduce a versioned Form/Template Registry** keyed to exact source identities and page/appendix/paragraph anchors, including prescribed forms, official specimens, official service templates and historical/unverified research candidates.
3. **Share generator/auditor requirements.** The same reviewed versioned field definitions, legal conditions, temporal applicability rules and procedural checklist items must drive guided document creation and independent draft audits.
4. **Both Admin and User may submit a temporary draft for review** and generate a working document from published template sources. This is not a source-corpus upload. No user working-file input can mutate the global source vault, search, knowledge graph, AUTH-LEDGER or shared template registry by default.
5. **Admin alone manages shared sources and templates.** Publishing or changing prescribed forms, MML copies, policies or template definitions remains governed by the Admin ingestion/publication boundary. Admin publication does not itself verify legal authority or legal adequacy.
6. **Source quality takes precedence.** Unknown MML edition/authenticity, statutory version conflicts, imprecise form identity and incomplete amendments must block claims that a template is currently mandatory or legally compliant. Do not infer a template solely from model training knowledge.
7. **Audits are finding reports, not certificates.** The system may detect missing fields, inconsistent dates, possible charge defects or missing supporting records, with exact sources. It must differentiate verified errors, possible legal issues and facts not verifiable from the document; it cannot certify a lawful or complete proceeding.
8. **Safe, practical drafts.** Exports remain editable and unsigned; do not forge a signature, imply service/receipt occurred, invent a hearing or issue an order on behalf of a competent authority. Human review and the actual legal procedure remain necessary.
9. **Capability-first offline design.** Basic safe parsing, session separation, cleanup, authenticity/provenance and secure local export from day one. Do not let complex document-management roles or elaborate security architecture delay the pilot.
10. **Impact analysis.** New or amended source law/policy should flag affected template versions, validation rules and checklists for examination, without automatically rewriting them.
11. **Independent status axes and operational-use gate.** Record form type, fidelity, temporal applicability, legal approval, publication and dependency state independently. Require an attributable competent legal approval artefact, at the tier required for the output class, for operational scope; no formal JAG status without its formal evidence. Admin capacity never records legal approval (Document Studio 3.3). Credible material contrary authority blocks affected authoritative templates, checks and guidance until revalidated, not unrelated/historically supported use. An unverified upload alone is not legal invalidation.
12. **Controlling dates and readiness.** Track conduct, proceeding commencement, procedural-action and preparation/review dates distinctly with source-supported governing-date and transitional rules per constraint. Report actual check outcomes and outstanding human verification without a compliance score.
13. **Distinct operation classes and session ownership.** CORPUS_INGESTION (Admin only) is separate from WORKING_DOCUMENT_PROCESSING (both roles). Enforce authenticated ownership for temporary files, job outputs, URLs, context and caches, avoid sensitive log contents and clean up derivatives.
14. **Coverage and independent validation.** Maintain a source/page discovery coverage register; use source-derived independently prepared answer keys and blinded defective/correct test documents, not generator/auditor agreement alone.

## Relationship to ADR-0002

| Operation | Admin | User |
| --- | --- | --- |
| Open/use published templates and published legal sources | Yes | Yes |
| Generate draft, review existing PDF/DOCX/scan, check temporary document pack | Yes | Yes |
| Download draft/audit report | Yes | Yes |
| Submit new source/template into shared legal library | Yes | No |
| Publish, replace, withdraw or reprocess shared legal sources/template registry | Yes | No |

There are still only two roles. Distinguish **temporary working-file submission** from **Admin source publication** at the endpoint, data and UI level. Do not expose one through the other.

## Alternatives rejected

- Free-form LLM generation of purported prescribed documents without identifying the actual form.
- A document generator and reviewer driven by separate, inconsistent legal check sets.
- Automatically rejecting all uploaded drafts as invalid merely because some surrounding facts are unknown.
- Uploading user drafts to the common legal library or making them accessible across all users.
- Creating a detailed rank/JAG permission system merely to enable document drafting.
- Treating a machine-generated compliance score as legal approval.

## Outstanding design and legal decisions

**Blocking open decisions.** No operational template, mandatory constraint or definitive advisory can be enabled until these are decided. Until then the gate fails closed:

1. Owner confirmation of the proposed Legal Reviewer designation ([Document Studio 3.3](../DOCUMENT_STUDIO_AND_TEMPLATE_REGISTRY.md#33-legal-approval-path-on-an-air-gapped-site-proposed-blocking-open-decision)) as a recorded authorisation alongside the two access roles.
2. Identity of the competent authority who appoints Legal Reviewers, and the first recorded appointments with their scope and capacity (designated legal adviser or formal JAG approver).
3. The tier-requirement table (T1 or T2 per output class). Until it is recorded, the proposed fail-closed defaults in 3.3 apply.
4. Which approval artefact channels a deployment accepts (signed release import, local Legal Reviewer decision, confirmed transcription), and the offline signing-key custody for release approvals.
5. Who on the legal side reviews proposed supersession, repeal, re-enactment and overruling edges (the root `CLAUDE.md` open question), which is the same designation.

No approval, appointment or approval artefact exists today.

**Other outstanding decisions:** precisely which forms are current and prescribed; authenticated source editions; field/rendering rules; format standards; record retention period; scanner/OCR quality thresholds; storage and export formats; versioning of local administrative templates; whether future case-file persistence is needed; and confirmation of the Army-first pilot and tri-service target scope (Product vision 1).

No approved source forms, operational templates, signed legal documents or software implementations are created by this ADR.
