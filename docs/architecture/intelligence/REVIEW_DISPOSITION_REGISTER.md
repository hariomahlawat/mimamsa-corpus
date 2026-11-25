# PR #53 independent review disposition register (R2)

**Date:** 25 November 2026. **Historical R2 status:** all 17 findings accepted and corrections proposed. R3 current disposition below supersedes the R2 all-pending state. No runtime implementation or legal approval is claimed.

Original Codex review: [47b102883aff297a6bbcbd884ddf9335fba19bcc](https://github.com/hariomahlawat/mimamsa-corpus/blob/47b102883aff297a6bbcbd884ddf9335fba19bcc/docs/architecture/reviews/intelligence_pr53_f1682c66.md), reviewed PR head `f1682c664d564aa7ad1c317065fafb302afe4ccc`, app comparison `9eeb04a457b532563d80610777d873ab24b52da5`. Original review branch preserved. Review reported 181 contract tests passed, one skipped, 109 design tests passed on Linux; those tests were not rerun by the revision author and are not evidence of Windows/runtime implementation.

## Dispositions

| Finding | Severity | Proposed architectural correction / location | Acceptance evidence required | Implementation phase |
|---|---|---|---|---|
| INT-F01 | P1 | [Serving contract](SERVING_AND_REVOCATION_CONTRACT.md) §§1–3/5; agent/tool/runtime integration; durable fence and bounded final handoff, all dependent delivery surfaces, honest prior-byte limit | REV-01–04/07–08, INT-09/10/14/19; actual transport race oracle | Existing B1/B2 publication/restore, every later AI/Studio delivery |
| INT-F02 | P1 | [Final claim contract](FINAL_CLAIM_VERIFICATION_CONTRACT.md) §§2–5; pre-authorize class, post-synthesis claim/scope/qualifier check, frozen content binding, typed evaluator output and source-only fallback | CLAIM-01–08, INT-11/12/19; rendered/exported claim oracle | Before any generated research, then every operative output |
| INT-F03 | P2 | [Crosswalk](DATA_CONTRACT_CROSSWALK.md) §§1–2; exact R1 record fields, R/O/U/F, page vs derivative span, site vs upstream, no invented axes | Collision/page-only/OCR/hidden/eligibility fixtures, INT-06/19 | B0/B1/B3 reconciliation, future enriched projections |
| INT-F04 | P2 | Crosswalk §3; typed relation matrix, inverse labels, valid time vs transaction/event time, proposition/proceeding granularity; Retrieval §7 | INT-03/04/05; same-name, duplicate report, split treatment, cyclic/competing/unknown version fixtures | A4/A5 and B3 mapping; before GraphRAG activation |
| INT-F05 | P2 | Retrieval §7 claim-specific coverage and independently budgeted adverse search, weakest-segment path, missing-links reporting | INT-03/04; incomplete graph, wrong linked version, text-only adverse result oracle | B3 browsing gaps, later GraphRAG answers |
| INT-F06 | P2 | Engine §7 and crosswalk §4; exact typed scope subset, artifact/signer, pack/semantics/dependency digest, time validity; R1 gap explicit | INT-18/14/11, synthetic wrong digest/narrow grant/missing artifact/revocation | Before post-v0 rule/template use |
| INT-F07 | P2 | Engine §8 typed hit policy, three-valued composition, separate fact states, finite-state procedural transitions and deterministic trace | INT-13; independent synthetic table, permutations, boundary dates, conflicting/overlapping rows | Before approved rule packs |
| INT-F08 | P2 | Agentic §7/task DAG, lease fence and CAS, cumulative budget, private write idempotency; tool §7 | INT-16; kill before/after completion, stale fact revision, duplicate write, cancel | Later persistent workflows; reuse current jobs |
| INT-F09 | P2 | Tool §7, Runtime §6; operation domains, private delegation, context cache partition/reset, normalized errors, safe rendering | INT-07/08/17; alternating-owner synthetic canary, logs/streams/export/restore | Existing parser/session boundaries; before model activation |
| INT-F10 | P2 | Runtime §7; future scoped signer, artifact manifest/evaluation binding, staged vetted loader, compatible index swap, revocation/rollback | INT-15/20; wrong signer, corrupted weights, incompatible vectors, interrupted swap, revoke | Existing P6/P7/P8 principles; later model gate |
| INT-F11 | P2 | Evaluation §6 preregistered fixtures/oracles for all 20 IDs, release metrics/denominators, negative controls and workload | All INT-01..20 + REV/CLAIM, independent oracle and actual feature runs | Existing PoCs where compatible; later release gates |
| INT-F12 | P2 | Serving §4; durable serialized acceptance marker/high-water independent of rollback, explicit crash recovery | REV-05/06, INT-10; interrupt at each persistence step, missing current state safe halt | Existing B2/P8 restore |
| INT-F13 | P3 | Retrieval §7 structured identifiers, alias history, multilingual/OCR variants, rare-subissue quotas | INT-01/02/06, per-family retrieval and qualifier recall | Existing P2/P3 benchmark where compatible; later tuning |
| INT-F14 | P3 | Agentic §7 typed progress, owner workspace snapshot, invalidation/reconnect and keyboard journeys | INT-08/09/16; actual UI and task-success benchmark | B1/B3 workspace; later durable agent event API |
| INT-F15 | P3 | Engine §9 shared impact service, direct + scope dependencies and credible/material hold policy | New conflict without reverse edge, unrelated upload, local/release swap; unaffected access | B2 publication; later legal holds |
| INT-F16 | P3 | Runtime §8 resource admission/queue isolation, CPU fallback and mixed-load benchmarks | INT-15/20; model outage, fairness, disk pressure and non-AI SLO | Existing baseline PoCs, later inference pilot |
| INT-F17 | P4 | README R2, crosswalk §4, roadmap phase split; R1 pre-adoption supersedes IC-01; B0 proposed not deployed | Independent doc/phase reconciliation, no new GB gate or canonical schema change | C13 closeout coordination |

At the original R2 submission all rows had status CORRECTION_PROPOSED_AWAITING_INDEPENDENT_CONFIRMATION. Current independent R2 results and R3 proposed corrections are recorded below; implementation evidence remains NOT_RUN. Counts: P1 2, P2 10, P3 4, P4 1. Do not conflate this register with the corpus findings register or alter its counts.

## Review handoff

Review exact new PR head, compare against original f1682c66 and pinned Codex review. Confirm each finding independently; challenge the final handoff linearization under real framework/proxy buffering, crash durability/restore high-water, claim inventory completeness and renderer/export binding, typed scope and relation mapping. If a correction remains underspecified, record a new finding or retain original open. Verify no conflict with current application branch, canonical R1 or successor, existing legal tiers, eligibility, v0 fail-closed controls and actual B0/B1/B2/B3 ownership. Reconcile changes with Claude without adding new Cycle 13 gates. No claims of legal approval, feature activation or implementation acceptance.

Suggested conclusion: independent reviewer determines ACCEPT / ACCEPT WITH CONDITIONS / REVISE AND RE-REVIEW / REJECT; the author does not preselect it. No staging/main merge without owner direction.

## R3 consolidated disposition (26 findings)

Independent confirmation report: [ef2b5f2c6a4d94b63c4eeacba567fa9871feacc8](https://github.com/hariomahlawat/mimamsa-corpus/blob/ef2b5f2c6a4d94b63c4eeacba567fa9871feacc8/docs/architecture/reviews/intelligence_pr53_r2_0c05d5a.md), reviewed R2 head 0c05d5a00542588cd7bea75f4962837cdde22bdd. Preserve its nine confirmed architectural closures; eight partial originals and nine new P2s are addressed in R3 pending independent confirmation. New findings refine residuals and must not be double-counted as distinct critical incidents.

| ID | Severity | Independent R2 disposition | R3 action / required evidence |
|---|---|---|---|
| INT-F01 | P1 | PARTIALLY ADDRESSED | Serving §§6–9, N01–03; concrete topology/handoff/precedence/witness, REV tests |
| INT-F02 | P1 | PARTIALLY ADDRESSED | Final Claim §7, N04; trusted issuer, semantic tree and fallback, CLAIM tests |
| INT-F03 | P2 | PARTIALLY ADDRESSED | Crosswalk §§6–8, N06; R1 review/quote and null withdrawal semantics, fixtures |
| INT-F04 | P2 | PARTIALLY ADDRESSED | Crosswalk §6, N05; producer mappings and scope, adapter oracle |
| INT-F05 | P2 | CLOSED-CONFIRMED AT ARCHITECTURE LEVEL | Preserve; final-scope contrary search clarification, future blind tests |
| INT-F06 | P2 | PARTIALLY ADDRESSED | Engine §10, N07; correlated grants and separate evaluation/delivery, synthetic membership |
| INT-F07 | P2 | CLOSED-CONFIRMED AT ARCHITECTURE LEVEL | Preserve; later rule composition and transition oracle |
| INT-F08 | P2 | PARTIALLY ADDRESSED | Agentic §8, N08; first visible write and budget reservations |
| INT-F09 | P2 | CLOSED-CONFIRMED AT ARCHITECTURE LEVEL | Preserve; session/retention epoch cache refinement |
| INT-F10 | P2 | CLOSED-CONFIRMED AT ARCHITECTURE LEVEL | Preserve; later model package/rotation proof |
| INT-F11 | P2 | PARTIALLY ADDRESSED | Evaluation §7, N09; three-stage metrics and independent egress/presentation oracle |
| INT-F12 | P2 | PARTIALLY ADDRESSED | Serving §8, N02; witness commit and recovery authority |
| INT-F13 | P3 | CLOSED-CONFIRMED AT ARCHITECTURE LEVEL | Preserve; later multilingual retrieval tests |
| INT-F14 | P3 | CLOSED-CONFIRMED AT ARCHITECTURE LEVEL | Preserve; bounded polling and future UI proof |
| INT-F15 | P3 | CLOSED-CONFIRMED AT ARCHITECTURE LEVEL | Preserve; scoped impact tests |
| INT-F16 | P3 | CLOSED-CONFIRMED AT ARCHITECTURE LEVEL | Preserve; measured mixed-load and non-AI SLA |
| INT-F17 | P4 | CLOSED-CONFIRMED AT ARCHITECTURE LEVEL | Preserve; residual IC-01 reference corrected to R1 and producer formats |
| R2-N01 | P2 | NEW | Serving §6/9: T0/T1 boundary, partial acceptance, caps, SLO, range/headers/polling; independent Windows transport tests |
| R2-N02 | P2 | NEW | Serving §8/9: prepare/witness CAS/install/ack, recovery and lost custody; crash/restore oracle |
| R2-N03 | P2 | NEW | Serving §7: independently versioned state, scoped denial precedence, CAS rebase, explicit re-admission, aggregate invalidation |
| R2-N04 | P2 | NEW | Final Claim §7, revised Agentic diagram: server-owned issuer store, canonical semantic tree, renderer/accessible/export and fixed fallback |
| R2-N05 | P2 | NEW | Crosswalk §6/8, Retrieval §8: pinned A4/A5→R1/service mapping, all 28 A5 types, no stronger inference, synthetic adapter fixtures |
| R2-N06 | P2 | NEW | Crosswalk §7/8: actual reviewed_record binding, derivative-wide OCR restriction, semantic withdrawal rejection/escalation |
| R2-N07 | P2 | NEW | Engine §10, Final Claim §2: exact tuple/predicate membership, uncertainty evaluation vs definitive output, v0 fail closed |
| R2-N08 | P2 | NEW | Agentic §8 and Tools §8: staged private write, atomic fenced activation/receipt, expiry and reserve/settle ledger |
| R2-N09 | P2 | NEW | Evaluation §7: candidate/verifier/delivered metrics, zero known unsupported/unbound delivery, positive coverage, independent observers |

**Current architectural status:** 9 CLOSED-CONFIRMED from independent R2; 17 CORRECTION_PROPOSED_AWAITING_INDEPENDENT_CONFIRMATION (8 original partial + 9 new). Severity inventory 2 P1, 19 P2, 4 P3, 1 P4. Of the pending 17: 2 P1 and 15 P2. All 26 implementation-evidence statuses NOT_RUN for this documentation revision, including independently confirmed designs. Existing Linux contract/design test results remain historical, not rerun here.

Review R3 only for substantive residuals and regressions; preserve accepted findings unless specific contrary evidence. Actual Windows topology/buffer behavior, witness custody/storage durability, executable adapters, semantic rendering, rule/agent implementation and legal approval are explicitly future proof at existing milestones. Do not demand production implementation as proof of a purely prospective design, but retain measurable release tests and refuse enabling unsupported paths. Confirm no new C13 gate, no canonical schema changes, no ledger activation, no changes to Claude work. Reconcile with then-current A4/A5/R1 at normal producer/consumer handoff. No merge until independent conclusion and owner direction.
