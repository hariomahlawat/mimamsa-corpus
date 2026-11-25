# Deterministic legal engine and operational eligibility

**Status:** future design only. No operative legal rules or legal interpretations are supplied. [Precedence](README.md). Existing Scenario Advisory Engine and Document Studio §§3.2–3.3, 4.1 and 8.1 remain controlling.

## 1. Purpose

The engine evaluates explicitly approved, versioned constraints against explicit facts and date bases. It complements, rather than replaces, legal judgement. Models may extract candidate facts or propose research leads; only a validated rule pack may generate a mandatory source-supported check, and only inside its approved scope. The same evaluator serves the future Commander Assistant and Document Studio; generation and scrutiny must not rely on different legal logic.

No rules are executable in Cycle 13. At AUTH-LEDGER v0 the current data contract rejects legal applicability promotions and appointment/approval records. The future engine fails closed until the existing approval process, trusted ledger state and relevant release gates permit it. No synthetic demonstration changes the legal state.

## 2. Rule pack model

Proposed logical fields (map to canonical entities before implementation): rule identity and immutable revision; output class; exact source-copy/provision-version and evidence anchors; legal interpretation and authority; defined scope (service, jurisdiction, rank/status, procedure, document class, other predicates); controlling event-date type and effective interval; commencement/savings/transitional chain; explicit prerequisite and exception predicates; applicable template version where relevant; competent authority only if established; dependency IDs; required approval tier; approval artefact and appointment/authority references; freshness and revision constraints; approved test cases and counterexamples.

Do not embed arbitrary model-generated Python/SQL or scripts in rule packs. Evaluate a typed, declarative, bounded expression model with deterministic operators, explicit unknowns, no external I/O, schema validation and versioned semantics. Consider decision tables or a constrained DSL after testing. No automatic compilation of extracted text into operative law.

Facts carry type, value or UNKNOWN, provenance (user assertion, extracted working field, verified source), confirmation state, applicable date and conflict state. Preserve allegation versus established fact. Missing facts are not false, empty dates are not today's date, unknown exceptions do not become absent.

## 3. Evaluation

1. Resolve approved rule revision and complete dependency set for the requested output class.
2. Check active publication, deployment eligibility, trusted ledger state, source authenticity/fidelity, scope and temporal applicability, required approval tier, attributable artefact and valid appointment, no revocation/expiry, and absence of blocking material conflict.
3. Determine the legally controlling event date for each predicate using the rule's evidenced date basis; apply effective intervals and saving/transitional provisions. Do not select the latest text automatically.
4. Evaluate prerequisites and exceptions with explicit three-valued predicate logic TRUE/FALSE/UNKNOWN. Conflicting material facts remain unresolved, not overwritten.
5. Produce conditional route/check results, source refs, required missing facts, exceptions and precise blockers. Do not infer an unapproved rule from analogous cases or from a graph path.
6. Verify the same gate again at display/export. A changed exclusion, source, appointment, approval, dependency or applicable revision invalidates a cached operational result.

The existing scenario transitions AVAILABLE, BLOCKED, CONDITIONAL, UNKNOWN are retained. Document Readiness Report separately distinguishes passed, failed, unknown, missing, not applicable and not checked. No overall validity score or legal certification.

Synthetic decision-table example (no real legal requirement):

| Preconditions | Exception | Gate | Result |
|---|---|---|---|
| true | false | eligible | prerequisite check passes |
| true | unknown | eligible | unknown / clarification |
| false | false | eligible | check fails, with scope and evidence |
| true | true | eligible | not applicable if approved exception defines this |
| any | any | blocked | not checked; research only |

The actual rule definition, not this example, determines outcomes and exception semantics.

## 4. Approval and authority boundaries

Retain Document Studio tiers T0_RESEARCH_ONLY, T1_LEGAL_ADVISER_REVIEWED, T2_FORMAL_JAG_VALIDATED and its competent-authority tier table. No new approval tier or role. Legal Reviewer is a designation on an existing account, not an extra research role. Admin publication is not authentication, applicability or legal approval. Where the tier table is missing use the existing fail-closed default, not a model judgement.

No agent can create a real appointment, approval, AUTH-LEDGER entry or authenticated legal promotion. The engine validates records already accepted through the authorised process; it cannot manufacture evidence or resolve substantive disputed legal interpretations. Only the competent designated process may lift relevant legal holds, and only within approved scope. Historical approvals remain traceable; not automatically transferable to new revisions.

## 5. Dependency and change control

Maintain reverse links from source copy/provision version, legal proposition, form, approval and rule pack to affected scopes and outputs. Reuse the existing credible/material trigger criteria in Document Studio §§3.3/8.1. Unknown-authority leads are review candidates, not automatic legal invalidation. A qualifying trigger blocks affected operational use; preserve historical research where eligible. Withdrawn/restricted sources are removed from all user/model surfaces regardless of previous release. An active exclusion channel remains effective on rollback.

On updates, compare exact dependency revisions and scope, invalidate affected cached results, regenerate candidate impact reports, require competent reapproval before reactivation where required. Do not automatically carry approvals forward or silently substitute evidence.

## 6. Tests

Independent source-derived oracles must cover boundary dates, savings, unknown facts, alternative scopes, conflicting sources, exception precedence, wrong template version, wrong approval tier, expired or revoked appointment, changed evidence hash, withdrawal mid-session, stale dependencies, and ledger v0. Include negative controls proving that a model assertion, Admin publication or technical review cannot unlock operational checks. Verify generator/checker consistency against independent reference cases, not against each other's output. Never use synthetic examples as actual legal rules.
