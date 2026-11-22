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
| D Data quality & CI | #14 | launched 2026-11-22 | claude/ws-d-quality · /home/user/ws-d | RUNNING (base 2a7ae7af) | – | – | awaiting first hand-off |

## Completed deliverables (coordinator, before launch)
| Deliverable | Location | Evidence status |
| --- | --- | --- |
| ACQ-02 supplement (16 PDFs / 17 instruments) | ACQ-02/ | Integrity 16/16; identity and operative page image-checked (PIC-12..29) |
| Instrument register (37), chronology (46), note discrepancies (10), version seed (11) | ARMY-RULES-CHAIN-01/ | `check_registers.py`: 0 errors |
| r.193 unresolved discrepancy | SOURCE-CONFLICTS-01 update c, U-04 | OPEN; chronology to be completed by WS-A before any correction |

## Fixed determinations
- r.23(3) CONFLICTING
- r.194 PROPOSAL (legal review)
- r.193 OPEN

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
| A10/A11 | DESW, AFT HTTPS route, Regulations for the Army copy; MML base64 history | Respective items |

## Unresolved legal questions
See NEXT_STAGE_PLAN.md §6 (AQ-01..AQ-10) and each workstream's open-questions register.

## Inter-agent dependencies
- C may consume A's provision change log when it is available; it is not blocked meanwhile.
- D validates A, B and C registers read-only.
- Only D edits the validator, schemas and CI.
