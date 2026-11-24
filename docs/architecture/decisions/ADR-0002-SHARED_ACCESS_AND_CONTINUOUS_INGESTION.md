# ADR-0002: Shared application access and continuous in-app document ingestion

- **Date:** 2026-11-24
- **Decision state:** **Owner-confirmed product policy.** Implementation specifics remain proposed.
- **Scope:** Access model, capability sequencing and source-ingestion architecture. Not a legal validation decision, application-build authorisation or corpus transfer approval.
- **Related:** [Product vision](../../product/PRODUCT_VISION.md), [Ingestion specification](../CONTINUOUS_DOCUMENT_INGESTION.md), [ADR-0001](ADR-0001-SCENARIO_DRIVEN_EVIDENCE_GROUNDED_PRODUCT.md).

## Context

Mimamsa must prioritise actual useful capabilities: search of the retained judgment collection, connected legal references, plain-English commander questions and continuous addition of new policies/SOPs. A role-based access matrix and elaborate hardening before capabilities exist would introduce complexity without directly improving legal usefulness.

However, a shared knowledge graph can be contaminated by unverified uploads, and a document may have access markings incompatible with all possible users. Essential upload safety and provenance therefore remain necessary.

## Decisions

1. **No RBAC.** Once a person has access to the offline Mimamsa installation, they can use **every feature** and access **every admitted document**. There are no privileged feature tiers, per-user document lists, private libraries or JAG-only research screens. Views may differ by user preference, not permissions.
2. **Deployment-wide source eligibility.** Only documents that may be shared with the installation's entire admitted audience can enter the common vault, search index, embeddings and graph. Source markings are recorded and checked at import; if incompatible, reject from the shared corpus instead of hiding from selected users.
3. **Continuous upload by any user.** Users can add eligible policies, SOPs, orders, instructions, manuals and reference material in the application, without requiring a developer, crawler operator or internet connection.
4. **Automatic enrichment.** Preserve exact bytes, extract/OCR, classify, identify issuers/versions/dates, generate searchable passages, analyse references, suggest conflicts, and build candidate edges to statutes, Rules, cases, policies and scenarios. Make accepted content discoverable with unverified status.
5. **No automatic legal promotion.** A user upload does not become binding law, supersede existing documents, alter the AUTH-LEDGER or create mandatory checklist items simply by being uploaded. Legal reliability is a separate evidence/review matter, not a user permission.
6. **Capability-first development.** Prioritise usable upload, search, graph and advisory functions. Preserve basic local cyber hygiene, admission controls, safe file parsing, integrity, backup, untrusted-text isolation and audit records from the first release; deeper hardening may follow.
7. **Query-versus-upload separation.** Conversational incident facts remain outside the shared corpus unless explicitly submitted as a document. The user is informed that an intentional accepted upload is shared with everyone on the installation.

## Consequences

- Simpler UX and operations with one shared legal corpus.
- No RBAC or feature-permission matrix in initial schemas.
- No promise of private user document stores; eligible uploaded data is shared across the deployment.
- Source-eligibility decisions must occur **before** indexing or derived-content publication.
- Research ingestion can be rapid and automated; authoritative legal recommendations remain evidence-dependent.
- Maintain stable IDs, version relationships and source hashes so later reviews cannot silently rewrite original materials.
- The offline deployment's perimeter controls and file-processing isolation are necessary even without fine-grained permissions.

## Alternatives declined

- Per-document role restrictions or JAG-only features.
- Mandatory human approval **before research indexing** of each eligible upload.
- Treat all uploaded material as equally authoritative.
- Delay in-app upload and graph enrichment until an extensive hardening project is complete.

## Not decided

File-format support beyond an initial safe subset, user admission/authentication implementation, document-size/storage limits, advanced security controls, technical stack, review/signature authority, and whether other isolated deployments with different source eligibility will be supported.

No application code, external restricted-source acquisition, Hugging Face upload, protected record change or real authentication-ledger promotion is authorised by this ADR.
