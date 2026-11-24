# Mimamsa product and architecture documentation

These files record the **owner-confirmed product direction** of 24 November 2026 and the **proposed technical design** for subsequent review. They are not source authentication, legal approval, a release claim, or authorisation to build or deploy an application.

## Read in this order

1. [Product vision](product/PRODUCT_VISION.md): users, capabilities, boundaries and success criteria.
2. [Commander use cases](product/COMMANDER_USE_CASES.md): plain-English questions, material facts and example scenarios.
3. [Legal knowledge architecture](architecture/LEGAL_KNOWLEDGE_ARCHITECTURE.md): source vault, identities, graph, temporal law and offline release.
4. [Scenario advisory engine](architecture/SCENARIO_ADVISORY_ENGINE.md): how the system would respond safely and usefully to situational questions.
5. [Continuous document ingestion](architecture/CONTINUOUS_DOCUMENT_INGESTION.md): Admin upload, analysis, graph integration, source trust and basic offline security.
6. [Document Studio and Template Registry](architecture/DOCUMENT_STUDIO_AND_TEMPLATE_REGISTRY.md): guided document preparation, independent draft review, source-specific format and procedural checks.
7. [ADR-0001](architecture/decisions/ADR-0001-SCENARIO_DRIVEN_EVIDENCE_GROUNDED_PRODUCT.md): situation-first product direction.
8. [ADR-0002](architecture/decisions/ADR-0002-SHARED_ACCESS_AND_CONTINUOUS_INGESTION.md): shared research access, Admin-only document management and capability-first sequencing.
9. [ADR-0003](architecture/decisions/ADR-0003-DOCUMENT_STUDIO_AND_TEMPLATE_REGISTRY.md): all-user working-document drafting/review, template provenance and non-certification boundaries.
10. [Form Discovery and Coverage Register](product/FORM_DISCOVERY_AND_COVERAGE_REGISTER.md): inventory contract and pending coverage baseline; no purported verified forms.
11. [Review closure C12](product/REVIEW_CLOSURE_C12.md): how the confirmation-review findings on this blueprint were closed.

## Precedence and scope

- Existing legal evidence and source-authority policies remain controlling: [EVIDENCE_STANDARD](legal-audit/EVIDENCE_STANDARD.md) and [SOURCE_AUTHORITY_POLICY](legal-audit/SOURCE_AUTHORITY_POLICY.md).
- Original 658 KB records and 53 curated case records remain research/unapproved unless separately validated. The existing AUTH-LEDGER is version zero, with no authentication promotions.
- The full retained judgment library is a **searchable research collection**; extracted summaries, outcomes, precedential treatment and checklist items are not automatically verified.
- **Two simple functional roles:** **User** and **Admin**. Both can search, open and use all **published** legal research, graphs, checklists and advisory features. Only the Admin can upload, replace, withdraw, initiate reprocessing or publish source documents. There are no rank/JAG-based feature tiers or per-document viewing restrictions among admitted users. Pending uploads remain in an Admin-only staging area. All published material must be suitable for the entire deployment audience; retain access markings for eligibility and provenance.
- Admin-controlled uploading of policies, SOPs and other material is a core product capability. The system automatically parses and builds candidate links while the material is staged; it enters shared search and graph navigation **only after Admin publication**, visibly tagged as an unverified source. Admin publication does not authenticate the legal content or automatically supersede binding law.
- Ordinary user-incident queries never become source uploads automatically. Standard offline security, minimal Admin mutation checks and safe file processing remain necessary; extensive hardening may be staged after core capability.
- **Document Studio:** every admitted User or Admin may provide a document to a temporary drafting/review session, create an editable legal draft, obtain a source-linked compliance report and download outputs. **This does not add the document to shared legal sources**. Only Admin may ingest or publish templates and source documents into the common library. Working files are isolated from shared search/graph and subject to deletion/retention controls. CORPUS_INGESTION and WORKING_DOCUMENT_PROCESSING are separate operation classes, with authenticated session ownership for working data. Operational templates/checklists require separate source, date, legal approval and dependency gates; the readiness report shows actual checks and unknowns, not legal certification.
- **Legal approval path (proposed, blocking open decision):** legal approvals would be recorded only by a designated Legal Reviewer appointed by the competent authority, at a stated tier, or imported in a signed release. This is not a third access role, and Admin publication is never legal approval. No approval exists today; the gate fails closed. See Document Studio 3.3 and the ADR-0003 blocking decisions.
- **Scope:** tri-service military law plus IPC/CrPC/Evidence Act and BNS/BNSS/BSA (from 1 July 2024) is the target; the pilot is Army-first.
- These specifications do not authorise external acquisition, Hugging Face uploads, merges, document reclassification, real ledger entries or application implementation.

Future development work should read these documents before planning changes and record any deviations in an ADR or a reviewed amendment to this documentation.
