# Confirmation review: PR #46 (Mimamsa product blueprint) at c69eee41

- **Reviewer:** Fable 5.2 (`claude-fable-5-2`), independent confirmation review. Technical and documentary review only; **not legal validation**.
- **Reviewed:** `origin/docs/mimamsa-product-blueprint-2026-11-24` at `c69eee41fc872797949de82a2b51a337dfd69d2e`, against base `legal-knowledge/v2.5-staging` `21e73b83`. 12 files, +1,270 lines, documentation only. Read-only; nothing committed, pushed or posted.
- **Date:** 2026-11-24

## Verdict: ACCEPT WITH CONDITIONS

All eight cold-review findings are closed at the design-contract level. Three new P2 gaps remain in the architecture (legal-approval write path, update-channel reconciliation, graph vocabulary for repeal/saving). Each is a documentation addition, and each fails closed today, so none blocks recording the blueprint. They should be closed, or recorded as blocking open decisions, before any implementation planning relies on these documents.

Counts: P1 0, P2 3, P3 7, INFO 3.

## 1. Closure of previous findings

The original cold-review text is not in the diff, the branch, the PR comments or the scratchpad. The only record is the disposition table in the PR body and the body of commit `debf44ed`. Closure was judged against those eight remediation statements (see F-13).

| Finding | Status | Closing text (file, section) | Residual |
| --- | --- | --- | --- |
| P2-01 approval and status separation | CLOSED | Studio 3.2: "release an authoritative template, mandatory constraint, procedural checklist or definitive advisory only for the explicitly approved scope, with source identity/fidelity, applicability and requisite legal approval independently established, published eligibility and no blocking dependency conflict." Also: "A form is not operationally approved merely because a source passage or template was independently verified." | "Requisite legal approval" names no tier and no actor (F-01) |
| P2-02 corpus versus working-file operations | CLOSED | Studio 2: "CORPUS_INGESTION is Admin-only and writes to shared-source staging; WORKING_DOCUMENT_PROCESSING is available to both roles and writes only to that user's temporary session. Distinct endpoints, storage namespaces, job types, output retrieval, and publication paths must enforce these semantics server-side." `c69eee41` aligned Scenario engine 2 to the same terms. | Stale "user-upload" wording in four places (F-04) |
| P2-03 controlling dates | CLOSED | Studio 4.1: "Each legal constraint records which event date(s) control, legal basis for that selection, applicable intervals, and transitional/saving/retrospective qualifications. Substantive offence law and procedural requirements can use different controlling events. Never assume that today, the incident date, or the date typed on a document governs all requirements." Mirrored in Architecture 7 and Scenario engine 4. | PR-10 still says "the incident date" (F-05) |
| P2-04 dependency invalidation | CLOSED | Studio 8.1: "immediately mark that affected scope REVALIDATION_REQUIRED/BLOCKED and prevent definitive advice, authoritative generation, or a passing mandatory-check result based on the affected requirement; unaffected scopes and evidenced historical use remain available." And: "Invalidate affected active caches and compiled rule sets; re-check before export or response, including already-open sessions." | Who judges "credible material" is undefined (F-01) |
| P2-05 session ownership | CLOSED | Studio 2: "Use simple authenticated session ownership checks for all working inputs, job IDs, file URLs, reports, exports and model-context retrieval; an opaque identifier alone is insufficient. User A (including an Admin acting as another user) has no general Document Studio access to User B's session." Test in Studio 11. | Backups and audit logs not covered (F-07) |
| P3-01 independent axes | CLOSED | Studio 3, six-axis table, and: "A label on one axis cannot promote another." | Three unreconciled vocabularies (F-06) |
| P3-02 discovery coverage | CLOSED | Register 2: all five queue rows `NOT_ASSESSED_IN_THIS_REGISTER`; Register 3: "Do not calculate aggregate coverage across unknown denominators or count copies as distinct forms." | Army-only queue (F-09) |
| P3-03 independent oracle | CLOSED | Studio 11: "an answer key constructed directly against the original forms, governing dated provisions and approval evidence, **without deriving the oracle from generator output, shared validation logic or the same rule-authoring process**. Keep blinded holdouts" | None |

`c69eee41` itself: both edits are consistent with the rest. One small tension is introduced with Studio 9.2 (F-08).

No closure introduces a contradiction that reopens a finding. Residuals are listed as new findings below.

## 2. Capability assessment

| # | Capability | Rating | Where | Note |
| --- | --- | --- | --- | --- |
| 1 | Commander-centric legal research and scenario assistance | SUPPORTED | Scenario engine 2 to 7; Use cases 2, 5; Vision PR-03 to PR-05 | Fact dialogue, conditional transitions, abstention as a correct outcome |
| 2 | Comprehensive searchable judicial and statutory material | SUPPORTED | Architecture 10, 12 steps 1 to 3; ADR-0001 item 1; Vision 5 | Search is not gated on validation. No tri-service or BNS/BNSS/BSA scope statement (F-09) |
| 3 | Version-aware legal knowledge graphs | PARTIAL | Architecture 4, 5, 7 | Entities are versioned; relation table cannot express repeal, re-enactment, commencement or saving (F-03) |
| 4 | Common access to published research for all admitted users | SUPPORTED | ADR-0002 decisions 1, 5 and matrix; Ingestion 1; Vision PR-01, PR-15 | Consistent across all 12 files |
| 5 | Admin-controlled source and template publication | SUPPORTED | Ingestion 2; ADR-0002 decisions 2, 4, 6; Studio 2 | Server-side enforcement and staging stated everywhere |
| 6 | Continuous incorporation of new legislation, judgments and policies | PARTIAL | Ingestion 2, 3; Architecture 9 | Policies and SOPs covered. Release-bundle updates versus local uploads, and promotion of an uploaded amendment or judgment, are unspecified (F-02) |
| 7 | Document Studio for preparation and scrutiny | SUPPORTED | Studio 5, 6, 7, 9; ADR-0003 | Non-certifying, original preserved, unsigned exports |
| 8 | Source-backed prescribed forms and procedural rules | SUPPORTED | Studio 3, 4; Register 2 to 5; ADR-0003 decisions 2, 6 | No form is claimed as verified. Usable output depends on F-01 |
| 9 | Temporal applicability and transitional provisions | PARTIAL | Studio 4.1; Architecture 7; Scenario engine 4 | Rule-level model is sound; the graph has no saving or transitional edge (F-03); PR-10 is stale (F-05) |
| 10 | Dependency invalidation and revalidation | SUPPORTED | Studio 8.1; Architecture 8; Ingestion 2 step 11; Vision PR-28 | Decider for "credible material" and re-enable is open (F-01) |
| 11 | Isolation of temporary working documents | SUPPORTED | Studio 2, 9.2, 11; Architecture 11; ADR-0003 decision 13 | Backups and audit logs not addressed (F-07) |
| 12 | Fully offline air-gapped operation | SUPPORTED | Vision PR-12; Architecture 1, 9; Ingestion 2 (closing line), 7 | Model, OCR, embeddings and index all local; network-denied test required |

Nothing is MISSING.

## 3. Consistency with the existing corpus

Checked against `docs/legal-audit/EVIDENCE_STANDARD.md`, `SOURCE_AUTHORITY_POLICY.md` and `legal_knowledge/audit_work/AUTH-LEDGER/README.md` at the PR head.

- **AUTH-LEDGER:** consistent. Blueprint says "version zero, with no authentication promotions"; ledger README says "version zero only ... no ledger entries, no approvals and no authentication promotions."
- **658 records and 53 cases research/unapproved:** consistent with EVIDENCE_STANDARD, Explicit blockers.
- **Eight MML files:** consistent. Blueprint keeps them as "edition-unverified practical references" and `UNVERIFIED_MANUAL`, matching the policy.
- **No automatic legal validation, JAG artefact rule, authorship-neutral tests:** consistent, and repeated in every file.
- **Candidate versus verified:** consistent in substance. The vocabulary is parallel to, not mapped onto, the policy v1 fields (F-06).
- **Offline model use:** consistent. No external inference, telemetry or runtime Hugging Face dependency.
- **C10 figures (4,103 / 48 / 3,959 / 4,259 / 3,936):** all match the C10 reconciliation records, but those records are not on this PR's base (F-11).
- **Golden test set:** the blueprint correctly says to locate it. `PROGRESS.md:224` records that it has not been given to the pipeline.

## 4. Findings

| ID | Sev | Statement | Location | Requested action |
| --- | --- | --- | --- | --- |
| F-01 | P2 | The operational-use gate depends on an "attributable competent legal approval" artefact, but no role, operation or channel can record one. Only Admin and User exist, User has no shared writes, and Admin action is explicitly not legal approval. The Vision still lists a "Researcher/content reviewer" needing a "correction and review queue" and a "Legal review workspace" mode with "review decisions". The gate does not say whether a designated legal-adviser decision suffices or formal JAG validation is required, though the controlling policy treats them as separate gates. The same gap covers who decides that a change is "credible material" and who re-enables a blocked scope. Result: fail-closed, so no template or advisory can become operational on an air-gapped site. | Studio 3.2 and 8.1; Vision 2 (line 21) and 6 (line 92); ADR-0002 "Not decided"; ADR-0003 "Outstanding" | State the approval tier required per output class. State how an approval artefact reaches a deployment (signed release import only, or Admin transcription of an external artefact with the artefact attached) and that recording is not approving. Name who decides credibility and re-enable. Mark the review workspace as Admin-operated or deferred. If undecided, list it as a blocking open decision in ADR-0003. |
| F-02 | P2 | Two update channels exist (external release bundle; local Admin upload) with one sentence on how they coexist. Unspecified: de-duplication and identity collision when a release contains a source already published locally; re-derivation of candidate edges; fate of local approvals and template bindings pinned to old revisions; whether an imported change list triggers the Studio 8.1 impact assessment. The ingestion design is policy/SOP-shaped: an Admin-uploaded amending Act or new judgment stays an `ADMIN_PUBLISHED_UNVERIFIED` source, and no path turns it into a `ProvisionVersion` or `Judgment` node on site, since `AMENDS_PROVISION_VERSION` needs an authenticated instrument. | Architecture 9; Ingestion 2 and 3 | Add a short "release update and local sources" section: import verification, sha256 de-duplication and aliasing, precedence, edge re-derivation, change list feeding the 8.1 trigger, and the route (or explicit absence of one) for promoting uploaded legislation and judgments. |
| F-03 | P2 | The relation table has `AMENDS_PROVISION_VERSION` only. It cannot express repeal, omission of a section, repeal-and-re-enactment correspondence (IPC to BNS, CrPC to BNSS, Evidence Act to BSA from 1 July 2024), commencement notifications, saving/transitional provisions, rules implementing an Act, or instrument-level supersession. The time model requires all of these. The existing corpus relation types (`amends`, `supersedes`, `repeals`, `overrules`, `implements`, ...) are not mapped. None of the project's known supersession cases is named as an acceptance case. | Architecture 5 and 7; Studio 4.1 | Add the missing edge types (or state the table is non-exhaustive and list them as required), a mapping note to the existing relations vocabulary, and the known supersession cases as named temporal acceptance tests. |
| F-04 | P3 | Stale wording contradicts the Admin-only decision: "the new in-app user-upload capability"; "uploading local user documents requires no internet"; "Provisional link from user-supplied policy"; `USER_SUPPLIED_UNVERIFIED` beside `ADMIN_PUBLISHED_UNVERIFIED`. "Upload/edit/publish a source manual" also reads as editing an immutable source. | CLAUDE.md:184; Vision PR-12; Architecture 5; Ingestion 4 versus 2 step 8; Studio 2 table (line 22) | Replace with Admin-upload wording, pick one label, and limit "edit" to metadata and template definitions. |
| F-05 | P3 | Single-date wording survives the P2-03 fix: PR-10 "Resolve the law applicable to the incident date"; Studio 9.2 stores "applicable legal date" (singular). | Vision PR-10 (line 38); Studio 9.2 (line 152) | Reword to controlling event date(s) per constraint. |
| F-06 | P3 | Three status vocabularies are not reconciled: Architecture 6 (six dimensions, no publication or freshness dimension although section 8 refers to them), Studio 3 (six axes) and Ingestion 4. `REVIEW_REQUIRED` and `BLOCKED` each appear on several axes. None is mapped to the controlling policy v1 fields (`document_authority`, `carrier_provenance`, `copy_fidelity`, `amendment_chain_status`), which the policy makes mandatory for every new source entry; the ingestion entities do not carry them. | Architecture 6; Studio 3; Ingestion 3 and 4 | Add one mapping table and state that in-app `SourceDocument` records carry the v1 fields (for example `carrier_provenance=USER_SUPPLIED`, `document_authority=UNKNOWN` until evidenced). |
| F-07 | P3 | Working-session isolation does not cover backups or the audit log. Both are launch-minimum controls and could retain working files past deletion or outside session ownership. | Architecture 11; Studio 2; Ingestion 6 | State that working-session data is excluded from backups, or backed up under the same ownership and retention, and that the audit log holds metadata only. |
| F-08 | P3 | Studio 9.2 promises a report can be re-run "against the same published corpus revision"; the test added in `c69eee41` says withdrawn content "must not leak through ... old report replay". 9.2 does not say replay may be impossible after withdrawal. | Studio 9.2 (line 154) versus Studio 11 (withdraw test) | Add the qualification to 9.2. |
| F-09 | P3 | The blueprint describes "Indian military-law" but every statute, form source and discovery queue is Army-only. Air Force Act, Navy Act, AFT Act and BNS/BNSS/BSA appear nowhere in the 12 files, though the project brief collects them. | Register 2 (FDQ-01 to 05); Studio 3; all files | State the scope: Army-first pilot with tri-service and general criminal law in or out of the target. |
| F-10 | P3 | Section structure defect: the heading "4. Required scenario record contract" is followed by the "UC-24 to UC-28" subsection, and the contract list comes after it. One contract bullet trails a full stop. | Use cases lines 121 to 147 | Move the UC-24 to UC-28 subsection above the section 4 heading. |
| F-11 | INFO | The C10 figures cited are correct, but the C10 reconciliation records are not an ancestor of base `21e73b83`, so the citation cannot be resolved on this branch. "C10 also found high outcome-extraction error rates" was not verified in this review. | Architecture 2; Vision 5 | Cite the branch or commit, or soften to "reported". |
| F-12 | INFO | "Credible material" is used as the blocking threshold in six files without criteria. | Studio 8.1 and mirrors | Covered by F-01; add criteria when the decider is named. |
| F-13 | INFO | No review record for the cold review exists in the repository, PR comments or review threads. Closure can be checked only against the author's own summary of the findings. | PR #46 body | Commit the cold-review record alongside this one. |

## 5. Limits of this review

Documents only; no code exists to test. Legal correctness of scenarios and form sources was not assessed. C10 figures were checked against the C10 branch review records, not recomputed.
