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

## 7. Executable approval binding (INT-F06)

R1 approval/appointment scope is free text, approval subject excludes executable rule-pack revision, and its reference validation cannot establish runtime authority. Trusted AUTH-LEDGER state is necessary under the current contract, never sufficient. No real approval or rule is added here. Before a post-v0 feature, obtain competent-authority agreement on a versioned typed binding and adopt through canonical contract change control.

Proposed binding: signed or otherwise independently authenticated approval artefact bytes/hash and attributable decision ID, verified approver identity/capacity, appointment artefact/ID, approval tier, exact allowed output classes, service(s), jurisdiction(s), person/status class, procedure/stage, controlling dates and approved applicability intervals, exact pack/template revision and content digest, rule semantics version and dependency manifest digest. Include explicit limitations, decision timestamp, grant effective interval, expiry/revocation state and trusted authority/verification path. Scope fields are closed typed values with explicit ALL only if approved; empty/unknown is not wildcard. Resolve artefact bytes and authenticity under existing approval policy; do not trust a declared hash or signer label. For decision-time verify appointment capacity and validity at recorded decision, and at use-time enforce current approval, scope, appointment revocation/expiry, policy and dependency gates as controlling Document Studio requires. Historical approval evidence is not permission for current use.

A request scope must be a subset of every relevant grant dimension (not merely nonempty overlap). If unknown or partially outside, do not execute definitive checks for that part. Match exact executable pack/template digest, semantic version and dependency digest; validate required approval tier and live serving revision. A conflicting or revoked approval blocks affected scope; an approval cannot be inherited by a new digest. No model or Admin publication can issue a grant.

Synthetic example only: grant G covers service X, procedure Y, output class CHECK, pack hash H1, semantics S1, dependency D1, dates [d1,d2). Request X/Y/CHECK/H1/S1/D1 at an in-scope date and valid appointment may pass mechanics on an inert fixture. H2, different service, wider jurisdiction, missing artifact, lower tier, changed D2, expired/revoked appointment, or ledger v0 fails closed. No fixture is a real legal approval.

## 8. Composition and procedural state (INT-F07)

Use typed decision tables for predicates and a versioned finite-state transition model for procedural routes. Each table declares input types, controlling date type, explicit interval boundaries, hit policy (unique, mutually exclusive, or explicitly approved collect/priority semantics), exception/precedence rules and outputs. Default to unique: overlapping contradictory rows reject the pack unless an independently approved composition rule resolves them. No implicit rule order, latest-date preference or model-selected precedence. Alternative routes are distinct approved transitions with prerequisites, authority and dependencies; evaluate each without inventing a route.

Preserve fact state ABSENT/ALLEGED/DISPUTED/CONFIRMED/UNKNOWN separately from predicate truth TRUE/FALSE/UNKNOWN and output state. Conflicting or unconfirmed material facts cannot be treated as confirmed absent. Use strong Kleene logic for pure predicates (NOT unknown=unknown; AND false dominates, otherwise unknown if any unknown; OR true dominates, otherwise unknown if any unknown); required unresolved authority, date, exception or conflict still independently blocks definitive use. An exception is applied only under the approved table; unknown exception prevents an unconditional pass. Explicitly model sequential/repeated procedure events with stable occurrence IDs, prior state, authorized transition, relevant event date and evidence. Never overwrite historical events when facts are revised.

Synthetic truth-table oracle: prerequisites P and Q are conjunctive and exception E overrides only when established. P=T,Q=T,E=F → local check pass; E=U → unknown; Q=F,E=F → local check fail; E=T → not applicable under this synthetic approved rule; conflicting two applicable rows without approved priority → pack rejected. A blocked policy gate → not checked regardless of inputs. Distinguish alternative branches (P OR Q) from cumulative requirements; unknown date cannot select a version.

Record deterministic trace of rule/semantics/dependency digests, fact revisions, source and provenance, exact predicate inputs, intermediate truth values, exception and hit-policy decisions, prior/next state and blockers. Replaying same canonical inputs must reproduce typed output. Evaluate independent tables in varied order when order is immaterial; test overlapping scopes, disputed/absent facts, alternative prerequisites, repeated events, boundary dates, saving/transition rules, conflicting authority, changed template and narrower grant. A bounded constraint solver may be trialled for complex interdependencies only with transparent witnesses and equivalent independent oracles.

## 9. Shared impact service (INT-F15)

Application publication/dependency service owns append-only impact records, not individual agents. Index direct reverse dependencies and scope keys (issuer/instrument/provision, service, jurisdiction, date basis/interval, procedure and template). On new or changed eligible source, check both direct revisions and scope-overlap candidates, including newly discovered conflicts without a prior reverse edge. Apply the existing credible/material criteria; unknown-source leads remain review leads, scoped holds require the controlling policy, and only the authorized designated process may lift them. Record affected scopes and exact evidence; re-evaluate after local/release reconciliation. Test credible new conflict without reverse link, uncorroborated upload, unrelated change and late local upload during release swap. Unaffected research remains available. All operational rendering uses the typed evaluator result under the final claim and serving contracts; never let a model rewrite a pass/fail, date or mandatory requirement.
