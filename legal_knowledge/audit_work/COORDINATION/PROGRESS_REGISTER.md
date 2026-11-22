# Central progress register (programme #10)

Updated by the coordinator only. State is persisted here so work can resume after interruption.

## Workstreams
All four agents were launched 2026-11-22 from base commit 2a7ae7af, each in its own worktree and branch. Agents commit locally only; the coordinator reviews, pushes and opens one PR per workstream (base `claude/audit-pilot-01`).
Resume procedure: read each `WS-*/STATUS.md` on its branch (`git -C /home/user/ws-X log`), then continue from the 'next' items.

| WS | Issue | Agent | Branch / worktree | State | Last integrated commit | CI | Integration |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A Statutory & Gazette | #11 | Agent A (completed) | claude/ws-a-statutory · /home/user/ws-a | COMPLETED hand-off 1 | 74530be9 | local gate green | PR #19; review WS-A-1 (C-08 image re-confirmed) |
| B Judgments | #12 | Agent B (completed) | claude/ws-b-judgments · /home/user/ws-b | COMPLETED hand-off 1 | 68290bae | local gate green | PR #21; review WS-B-1 (A-03 spot-checked) |
| C MML & procedure | #13 | Agent C (completed) | claude/ws-c-mml · /home/user/ws-c | COMPLETED hand-off 1 | a4c68cf2 | local gate green | PR #20; review WS-C-1 |
| D Data quality & CI | #14 | Agent D (completed) | claude/ws-d-quality · /home/user/ws-d | COMPLETED hand-off 1 | 1be2a2e1 (re-merged with #16 cee610f9) | local gate green; 113 tests | PR #18; review WS-D-1 |

## PRs (owner review; none merged)
| PR | Branch → base | Content | Approval scope |
| --- | --- | --- | --- |
| #15 | claude/hf-sync-guard-staging → legal-knowledge/v2.5-staging | Job-level HF safeguard: general corpus upload is manual-dispatch only, with approval input; abbreviation job unchanged | Merge before any staging merge (A3) |
| #16 | claude/next-stage-proposal → claude/audit-pilot-01 | Next-stage proposal (fd01b234 + b20843d6) with owner corrections: distinct dates, continuation-page image checks PIC-30..36, C-08 (r.193) / C-09 (r.194) split | Review proposal |
| #17 | claude/acq-02-config → claude/acq-01-config | ACQ-02 crawler config, source `archive_acq02` (16 URLs with expected hashes), disabled | Config approval, then a separate download approval (ACQ-02 scope only) |
| #18 | claude/ws-d-quality → claude/next-stage-proposal | WS-D: hash reproduction, 87-code test, scores, plain-text index, relation graph, coverage scorecard, validator controls, 4 CI steps | Review proposal |
| #19 | claude/ws-a-statutory → claude/next-stage-proposal | WS-A: S.R.O. 17(E)/1993 itemised (41 items), r.193/194 chronology, Army Act chain, ACQ-03 requests | Review proposal; ACQ-03 needs separate approvals |
| #20 | claude/ws-c-mml → claude/next-stage-proposal | WS-C: MML edition status, crosswalk, 658 coverage inventory, calibration sample (selection only) | Review proposal |
| #21 | claude/ws-b-judgments → claude/next-stage-proposal | WS-B: intern intake manifest, 53-case identity, holdings, treatment, adverse queue | Review proposal |

Approval scopes are documented separately:
- ACQ-01 = PR #8 (14 URLs).
- ACQ-02 = PR #17 (16 URLs).
- ACQ-03+ = WS-A acquisition requests (not configured).

## Completed deliverables (coordinator)
| Deliverable | Location | Evidence status |
| --- | --- | --- |
| ACQ-02 supplement (16 PDFs / 17 instruments) | ACQ-02/ | Integrity 16/16; identity and operative page image-checked (PIC-12..29) |
| Instrument register (37), chronology (46), note discrepancies (10), version seed (11) | ARMY-RULES-CHAIN-01/ | `check_registers.py`: 0 errors |
| r.193 unresolved discrepancy | SOURCE-CONFLICTS-01 update c (U-04) and update d (C-08) | OPEN; leading candidate S.R.O. 17(E)/1993 (MML 2 p.227 footnote); chronology to be completed by WS-A before any correction |
| r.194 | update d (C-09) | PROPOSAL pending legal review |
| Owner corrections (dates, continuation pages, conflict split) | PR #16 commit 11ce905e | check_registers 0 errors; 54 tests; strict validation OK |

## Fixed determinations
- r.23(3) CONFLICTING
- r.194 PROPOSAL (legal review)
- r.193 OPEN (C-08)
- r.194 PROPOSAL (C-09)

## CI
- PR #6 audit CI green on 2a7ae7af and 3b708245 (2026-11-22).

## Owner decisions required (blockers; other work continues)
| ID | Decision | Blocks |
| --- | --- | --- |
| A1/A2 | PR #7 merge; PR #8 approval and download run (14 URLs) | ACQ-01 record copies |
| A3 | HF sync guard before any staging merge | Stack A merge |
| A4/A5 | ACQ-02 config PR; ACQ-03 discovery downloads | Record copies; image checks of 5 OCR-only instruments |
| A6 | Indian-network egazette search (E-7/1960, S.R.O. 258/2002, post-2022) | Chain gaps |
| A7 | Custodian letter signature | Certified copies |
| A9 | Legal advisor nomination | All advisor items |
| OQ-D-003/006/007/014/015 | WS-D questions: v4 register fix; migration of frozen effective dates; human reviewer nomination; fresh PILOT-01 validation record; exact reviewer IDs | WS-D follow-ups |
| A10/A11 | DESW, AFT HTTPS route, Regulations for the Army copy; MML base64 history | Respective items |

## Unresolved legal questions
See NEXT_STAGE_PLAN.md §6 (AQ-01..AQ-10) and each workstream's open-questions register.

## Inter-agent dependencies
- C may consume A's provision change log when it is available; it is not blocked meanwhile.
- D validates A, B and C registers read-only.
- Only D edits the validator, schemas and CI.

## Coordinating reviewer
The orchestrator reviews each workstream hand-off and records its review in `COORDINATION/reviews/<WS>-<n>.md`. It never edits agent outputs. High-risk findings get an additional independent reviewer agent before a PR is opened.

## Agent messages sent
- 2026-11-22: owner corrections relayed to agents A–D (date semantics, page-image rule, C-08/C-09, base branch `claude/next-stage-proposal`).
- 2026-11-22: WS-D questions routed: OQ-D-004/008/009/012 → WS-B; OQ-D-005 → WS-A.

## Cycle 1 release-readiness scorecard (2026-11-22)
| Exit condition (#10) | A | B | C | D |
| --- | --- | --- | --- | --- |
| Frozen input scope / manifest | ✔ registers with file SHA-256 | ✔ raw-data@ad77758d, held_copies | ✔ input_manifest.json | ✔ hash_reproduction.json |
| Evidence register | ✔ identity_transcription (33 PIC) | ✔ holdings and identity registers | ✔ 28 PIC | ✔ scores and graph |
| Change proposal | ✔ PCL, ACQ-03 | ✔ adverse queue, crosswalk | ✔ 14 candidate corrections | ✔ validator, CI, defects |
| Validation outcome | ✔ gates | ✔ gates + check_ws_b | ✔ gates, reproducible | ✔ 113 tests |
| Gaps register / next action | ✔ | ✔ | ✔ | ✔ |
| Coordinator independent check | C-08 re-rendered | A-03 on official copy | scope, reproducibility | clean-tree CI |

- **Combined check:** #16 plus all four branches merge with no conflicts. With all combined: 113 tests OK; PILOT-01 and R23 strict OK; `check_registers` 0 errors; 74 CSVs OK; relation graph OK.
- **Originals:** unchanged (9a8f0d19…, 8b8d53cd…).
- **No unverified authority promoted.** Highest state reached: technical review. Advisor and JAG states are NOT_STARTED.
- **Legal states:** r.23(3) CONFLICTING; r.193 (C-08) OPEN, now explained on located evidence by S.R.O. 17(E)/1993 item 38; r.194 (C-09) PROPOSAL.

## Next cycle (no approval needed; not started)
- WS-A: the 1964 r.187(1) footnote lead (OQ-C-06); image-check the six new hints once bytes are approved.
- WS-B: the remaining unresolved cases; identities for the 13 KB records (CC-11).
- WS-D: the "manual_supported" relation type (CC-13, schema lease).
- Cross-stream: reconcile WS-C's 658 inventory (FULL 379) with WS-D's scorecard (279/658 coded-searchable); the definitions differ and both carry explicit denominators.
