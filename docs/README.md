# Mimamsa product and architecture documentation

These files record the **owner-confirmed product direction** of 24 November 2026 and the **proposed technical design** for subsequent review. They are not source authentication, legal approval, a release claim, or authorisation to build or deploy an application.

## Read in this order

1. [Product vision](product/PRODUCT_VISION.md): users, capabilities, boundaries and success criteria.
2. [Commander use cases](product/COMMANDER_USE_CASES.md): plain-English questions, material facts and example scenarios.
3. [Legal knowledge architecture](architecture/LEGAL_KNOWLEDGE_ARCHITECTURE.md): source vault, identities, graph, temporal law and offline release.
4. [Scenario advisory engine](architecture/SCENARIO_ADVISORY_ENGINE.md): how the system would respond safely and usefully to situational questions.
5. [ADR-0001](architecture/decisions/ADR-0001-SCENARIO_DRIVEN_EVIDENCE_GROUNDED_PRODUCT.md): rationale, scope and decisions still open.

## Precedence and scope

- Existing legal evidence and source-authority policies remain controlling: [EVIDENCE_STANDARD](legal-audit/EVIDENCE_STANDARD.md) and [SOURCE_AUTHORITY_POLICY](legal-audit/SOURCE_AUTHORITY_POLICY.md).
- Original 658 KB records and 53 curated case records remain research/unapproved unless separately validated. The existing AUTH-LEDGER is version zero, with no authentication promotions.
- The full retained judgment library is a **searchable research collection**; extracted summaries, outcomes, precedential treatment and checklist items are not automatically verified.
- Source access restrictions and user-incident confidentiality are separate from the rule not to mask faithfully reproduced, lawfully published judicial text merely because it contains personal details.
- These specifications do not authorise external acquisition, Hugging Face uploads, merges, document reclassification, real ledger entries or application implementation.

Future development work should read these documents before planning changes and record any deviations in an ADR or a reviewed amendment to this documentation.
