# ADR-0002: Shared legal research access and Admin-controlled ingestion

- **Date:** 2026-11-24
- **Decision state:** **Owner-confirmed, refined after review.** Implementation details remain proposed.
- **Scope:** Minimal functional roles, knowledge-base mutation authority, continuous Admin ingestion and publication. Not a legal validation, application-build or data-transfer authorisation.
- **Related:** [Product vision](../../product/PRODUCT_VISION.md), [Ingestion specification](../CONTINUOUS_DOCUMENT_INGESTION.md), [ADR-0001](ADR-0001-SCENARIO_DRIVEN_EVIDENCE_GROUNDED_PRODUCT.md).

## Context

Mimamsa's primary value is search of the retained judgment collection, provision/judgment links, plain-English commander guidance and a continuously improving local repository of policies and SOPs. The initial product should avoid complex user-role matrices. However, allowing every user to alter a common legal source library risks accidental publication of incorrect, obsolete, duplicated or ineligible material.

The owner therefore retains **unrestricted shared research access** while limiting **changes to the common legal library** to the Admin. This supersedes ADR-0002's earlier draft proposal allowing any user to upload; the PR is not merged and historical source/corpus states are unchanged.

## Decisions

1. **Exactly two functional roles: Admin and User.** Both can search, read, compare and analyse every **published** source and use every published graph, checklist and advisory/research feature. There are no JAG-only or rank-based research features, and no per-user/per-document viewing restrictions.
2. **Only Admin may change the source collection.** Upload, replace (as a version), withdraw/unpublish, publish, and manually initiate ingestion or reprocessing are Admin-only actions. Restrict them server-side, not merely by hiding controls in the interface.
3. **Automatic enrichment following Admin upload.** Preserve the source bytes and hash; validate format and common-audience eligibility; OCR/extract and classify; suggest statute, Rule, judgment and policy connections; and stage candidate graph edges.
4. **Explicit Admin publication gate.** Submitted files and derived search snippets, embeddings and candidate edges remain out of the ordinary user-facing corpus until the Admin reviews source eligibility, identity/metadata and extraction warnings and explicitly publishes. Admin can inspect staging and reject or retry processing.
5. **Published documents shared to all.** After Admin publication, the source and its clearly labelled research outputs appear in the same index and graph for Admin and User. The absence of rank-based restrictions is retained.
6. **Publication is not legal approval.** Admin's publication action only approves distribution within the app. It does **not** authenticate a purported order, establish legal force, prove commencement or supersession, approve legal propositions, change existing binding provisions, or activate AUTH-LEDGER entries.
7. **Deployment-wide eligibility.** If a document's marking or restrictions make it unsuitable for the whole admitted audience, do not publish it; preserve applicable provenance. Such material cannot leak via ordinary-user snippets, embeddings, graphs or generated answers.
8. **Capability first, minimum cyber hygiene from day one.** Implement usable Admin ingestion, automation, publication and full-corpus search ahead of elaborate hardening. Retain simple user admission/authentication, server-side mutation checks, safe file handling and parser isolation, integrity, audit history, backups and offline network boundary.
9. **Session-versus-source distinction.** Normal legal questions and user incident facts do not silently enter the common knowledge base. Only Admin can intentionally submit a document for publication.
10. **Document Studio working files are not shared-source uploads.** Both Admin and User may provide a prepared charge-sheet or other draft for temporary audit or generate a working form. These files are session inputs/outputs, not source records; they cannot enter the global search/graph/template registry unless separately ingested and published through the Admin pathway. See [ADR-0003](ADR-0003-DOCUMENT_STUDIO_AND_TEMPLATE_REGISTRY.md). The operation names are CORPUS_INGESTION (Admin only) and WORKING_DOCUMENT_PROCESSING (both roles, authenticated own-session scope). Distinguish endpoints, jobs, storage and caches. Admin publication remains distinct from competent legal approval; credible material source changes require downstream scoped revalidation.

## Functional access matrix

| Operation | Admin | User |
| --- | --- | --- |
| Search/open all published judgments, policies, SOPs and legal sources | Yes | Yes |
| Ask legal questions, examine graphs, summaries, lessons and checklists | Yes | Yes | 
| Create working documents, upload an existing draft for temporary audit and download a reviewed version | Yes | Yes |
| Upload a new source for ingestion | Yes | No |
| Inspect staged, rejected or failed source-ingestion jobs | Yes | No |
| Retry or manually reprocess a source | Yes | No |
| Publish a staged source to the shared collection | Yes | No |
| Replace by uploading a new version | Yes | No |
| Withdraw/unpublish source material | Yes | No |
| Grant legal authentication/validation by publication alone | No | No |

A withdrawn source should remain available in the Admin audit trail and preserved source vault as required; it must not remain visible to ordinary users via shared indexes or cached answer material. Publishing a changed copy does not overwrite old source bytes or their hashes.

## Alternatives rejected

- General-user uploads into the shared legal corpus.
- Treating temporary working-document review as equivalent to publishing legal source material.
- Granular rank/JAG-based permissions or per-document user viewing rules.
- Treating publication as automatic legal authentication or validity.
- Hand-authoring all graph relationships and search indexes for each upload.
- Delaying basic capabilities until an elaborate security hardening programme completes.

## Not decided

Exact authentication mechanism, backup retention, storage limits, whether publication itself requires dual control, future advanced security, and additional specialised deployments. They require separate design decisions.

The legal-validation approval workflow is now a **blocking open decision in ADR-0003**. Its proposed path (a recorded Legal Reviewer designation, approval tiers, artefact channels and fail-closed behaviour) is in [Document Studio 3.3](../DOCUMENT_STUDIO_AND_TEMPLATE_REGISTRY.md#33-legal-approval-path-on-an-air-gapped-site-proposed-blocking-open-decision). That designation would not be a third access role and would not change decisions 1 to 6: Admin publication remains distinct from legal approval. Reconciliation of release bundles with local uploads is specified in [Architecture 9.1](../LEGAL_KNOWLEDGE_ARCHITECTURE.md#91-release-updates-and-local-sources).

No application implementation, outside-source acquisition, Hugging Face write, original corpus alteration, real ledger activation or PR merge is authorised by this ADR.
