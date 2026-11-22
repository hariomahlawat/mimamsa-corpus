# Central progress register (programme #10)

Updated by the coordinator only. State is persisted here so work can resume after interruption.

## Workstreams
| WS | Issue | Agent | Branch / worktree | State | Last integrated commit | CI | Integration |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A Statutory & Gazette | #11 | (pending launch) | claude/ws-a-statutory · /home/user/ws-a | NOT STARTED | – | – | – |
| B Judgments | #12 | (pending launch) | claude/ws-b-judgments · /home/user/ws-b | NOT STARTED | – | – | – |
| C MML & procedure | #13 | (pending launch) | claude/ws-c-mml · /home/user/ws-c | NOT STARTED | – | – | – |
| D Data quality & CI | #14 | (pending launch) | claude/ws-d-quality · /home/user/ws-d | NOT STARTED | – | – | – |

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
