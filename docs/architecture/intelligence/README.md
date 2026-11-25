# Mimamsa intelligence architecture extension

**Date:** 25 November 2026  
**Status:** owner-confirmed product direction; proposed architecture for independent technical review and reconciliation. No implementation, legal approval, deployment or scope expansion is authorised by this document.

## Purpose

Mimamsa is to evolve from an offline legal research application into an evidence-grounded agentic military legal intelligence platform. Functionality comes first; professional research UX, legal accuracy, security and Windows-native offline operation are non-negotiable. The intelligence architecture combines hybrid retrieval, evidence-grounded graph retrieval, bounded agentic workflows and a deterministic legal rule evaluator. These components serve complementary purposes, not competing products.

This package is deliberately additive. It was prepared in parallel with Cycle 13 on staging `9ed152af0df8e89335fbc6a52a4ccab30e6e5c55`, with the active application branch `claude/c13-b-app` inspected at `9eeb04a457b532563d80610777d873ab24b52da5`. PR #52 was open. No existing product/architecture files, active branches, code, schemas, corpus data or legal ledger are changed. The application branch's proposed ADR-0005 and data contract v1 R1 were considered, not assumed merged or accepted.

## Read in this order

1. [Agentic architecture and product workflows](AGENTIC_AI_ARCHITECTURE.md).
2. [Hybrid retrieval and legal GraphRAG](RETRIEVAL_AND_GRAPHRAG.md).
3. [Agent tool contracts and integration](AGENT_TOOL_CONTRACTS.md).
4. [Deterministic legal engine and operational gate](DETERMINISTIC_LEGAL_ENGINE.md).
5. [Local inference, security and operations](LOCAL_AI_SECURITY_AND_RUNTIME.md).
6. [Evaluation and phased delivery](EVALUATION_AND_ROADMAP.md).

The package extends rather than replaces [Product Vision](../../product/PRODUCT_VISION.md), [Legal Knowledge Architecture](../LEGAL_KNOWLEDGE_ARCHITECTURE.md), [Scenario Advisory Engine](../SCENARIO_ADVISORY_ENGINE.md), [Continuous Ingestion](../CONTINUOUS_DOCUMENT_INGESTION.md) and [Document Studio](../DOCUMENT_STUDIO_AND_TEMPLATE_REGISTRY.md). Existing ADRs 0001–0004, evidence standards, source-authority policy and applicable AUTH-LEDGER controls prevail over any ambiguity here. No new legal status vocabulary is created. ADR-0005 is reserved for the active application stack decision; assign the next available ADR number only after reconciliation.

## Integration constraints

- Cycle 13 remains research-only, approximately 70:30 corpus/application effort. No new implementation acceptance gate is added mid-cycle. No local generative model, live agent endpoint, rule execution or GraphRAG answer generation is required for Cycle 13.
- Preserve existing IC-01/data contract v1 R1. The agent-facing contracts in this package are proposed **service** contracts, not competing release schemas. Use adapters to map the canonical record vocabulary. Changes to the canonical contract follow its own version and review process.
- All admitted Users and Admins share published research. Admin-only diagnostics and staged source work do not constitute an extra research role. Working documents and agent sessions never become shared corpus data.
- Publication, authentication, applicability, legal approval and freshness remain separate. At AUTH-LEDGER v0 the operational gate is closed. The existing contract rejects legal applicability promotions, appointment and approval records at v0; the proposed future design does not override that restriction.
- A model cannot appoint a reviewer, approve a legal rule, alter an AUTH-LEDGER entry, publish or withdraw a source, or select or execute disciplinary action.
- Hugging Face remains the private corpus master with non-destructive versioned writes by authorised build-side processes only. No runtime model/agent has cloud credentials or network access.

## Reconciliation checklist (Cycle 13 closeout or earlier if non-disruptive)

| Existing area | Proposed extension | Integration action |
|---|---|---|
| PR-01/06/07/08/10/11, legal knowledge architecture §§4–10 | Hybrid ranking, entity-seeded traversal, source-grounded context | Compare with B0 search/graph API and IC-01; reuse, do not duplicate |
| PR-03/04/05, scenario engine §§2–9 | Bounded workflow orchestration and material-fact dialogue | Add cross-link and future tool IDs after independent review |
| PR-12/13/16–20, ingestion architecture | Local runtime, privilege separation, candidate enrichment | Reconcile with Windows service/security architecture and ADR-0005 |
| Document Studio §§2–4, 8–11 | Shared rule evaluator, private working context and claim-level evidence | Preserve existing tiers, readiness report and dependency rules |
| Capability traceability matrix on active app branch | Agentic future capability mapping | Add references and proposed tests after branch owner agrees; no duplicate capability IDs |
| Cycle 13 planning | Later milestones and release gates | Carry forward only compatible low-cost interfaces; no retrospective change of current exit criteria |

Independent reviewer: verify against the **then-current** staging, application contract, restriction/withdrawal channels, approved ADRs and scenario/document specifications. Resolve mismatches before proposing integration. Keep this package a draft until reviewed. No merge to main or staging is authorised by this package itself.
