# Central progress register (programme #10)

Updated by the coordinator only. State is persisted here so work can resume after interruption.

## Workstreams
All four agents were launched 2026-11-22 from base commit 2a7ae7af, each in its own worktree and branch. Agents commit locally only; the coordinator reviews, pushes and opens one PR per workstream (base `claude/audit-pilot-01`).
Resume procedure: read each `WS-*/STATUS.md` on its branch (`git -C /home/user/ws-X log`), then continue from the 'next' items.

| WS | Issue | Agent | Branch / worktree | State | Last integrated commit | CI | Integration |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A Statutory & Gazette | #11 | launched 2026-11-22 | claude/ws-a-statutory · /home/user/ws-a | RUNNING (base 2a7ae7af) | – | – | awaiting first hand-off |
| B Judgments | #12 | launched 2026-11-22 | claude/ws-b-judgments · /home/user/ws-b | RUNNING (base 2a7ae7af) | – | – | awaiting first hand-off |
| C MML & procedure | #13 | launched 2026-11-22 | claude/ws-c-mml · /home/user/ws-c | RUNNING (base 2a7ae7af) | – | – | awaiting first hand-off |
| D Data quality & CI | #14 | Agent D (general-purpose subagent) | claude/ws-d-quality · /home/user/ws-d | COMPLETED hand-off 1 | 5df7ac95 (merged with #16) | local gate green; 113 tests | PR #18 → claude/next-stage-proposal; review WS-D-1 |

## PRs (owner review; none merged)
| PR | Branch → base | Content | Approval scope |
| --- | --- | --- | --- |
| #15 | claude/hf-sync-guard-staging → legal-knowledge/v2.5-staging | Job-level HF safeguard: general corpus upload is manual-dispatch only, with approval input; abbreviation job unchanged | Merge before any staging merge (A3) |
| #16 | claude/next-stage-proposal → claude/audit-pilot-01 | Next-stage proposal (fd01b234 + b20843d6) with owner corrections: distinct dates, continuation-page image checks PIC-30..36, C-08 (r.193) / C-09 (r.194) split | Review proposal |
| #17 | claude/acq-02-config → claude/acq-01-config | ACQ-02 crawler config, source `archive_acq02` (16 URLs with expected hashes), disabled | Config approval, then a separate download approval (ACQ-02 scope only) |
| #18 | claude/ws-d-quality → claude/next-stage-proposal | WS-D: hash reproduction, 87-code test, scores, plain-text index, relation graph, coverage scorecard, validator controls, 4 CI steps | Review proposal |
| WS-A..C | claude/ws-*-* → claude/next-stage-proposal | Opened after review of each hand-off | Review proposals |

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
