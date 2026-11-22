# Coordinator review: WS-C hand-off 1 (issue #13), 2026-11-22

**Reviewed:** `claude/ws-c-mml` commits 28de184c..f95bc261, plus merge a4c68cf2 of `claude/next-stage-proposal` (PR #16, including the WS-A baseline update cee610f9). No agent file was edited.

## Checks performed
| Check | Result |
| --- | --- |
| Paths changed only under `WS-C-MML/` | PASS |
| No complete derived MML text committed | PASS: indices hold locators only (longest field in provision_index 17 chars, mml1_para_index 89, crosswalk 215). The longest field anywhere (1,479 chars, `mml_edition_status.csv`) is descriptive notes. |
| 658 inventory reproducible | PASS: `scripts/build_kb658_inventory.py` re-run gives byte-identical output |
| Gates after merge | PASS: audit tests OK; PILOT-01 and R23 strict OK; `check_registers.py` 0 errors; CSVs well formed; records_658 sha unchanged |
| No correctness verdicts on the 658 | PASS: coverage states only; FULL means resolvable to a held source with a pinpoint, not verified |
| Edition claims | PASS: all 8 files stay UNVERIFIED_MANUAL; imprint readings flagged unverified (OQ-C-01/02) |

## Assessment
- **MML 2 p.227 (WSC-PIC-08..10)** agrees with WS-A's S.R.O. 17(E)/1993 item 38: r.193 is bracketed for s.90(i) and s.91(i), with footnote "Substituted by SRO 17 (E), dated 6th December, 1993". r.194 includes "or the officer commanding an Army" (the 1989 words). This is corroborative manual evidence only. C-08 stays OPEN and C-09 stays PROPOSAL.
- **The 658 inventory** (denominator 658): FULL 379, PARTIAL 131, SOURCE_GAP 56, UNRESOLVED 14, NO_CITATION 78. No record names the MML (0/658); 293 can be linked through the crosswalks. Co-citation-only codes cannot give FULL.
- **Leads, not proof:** MML footnotes attribute 1993 changes to rr.14(4)-(5), 15, 16B(1), 145, 164, 168(2), 186(1) and 193. Several were outside the old AR-029 list but are now covered by WS-A's 41-item itemisation, which is merged into the baseline.
- **Possible unregistered instrument:** MML 2 p.225, "Substituted by SRO 1, dated 12th March, 1964" for r.187(1). Coordinator note: the register has S.R.O. 1 of 22-12-1961 amending r.187(1) (AR-007, image-checked) and S.R.O. 126 of 12-03-1964 (r.13(2A), AR-009). The MML footnote may conflate the two, but that is unverified. It is recorded as an open lead for WS-A's next cycle, not resolved.
- **Obsolete guidance flagged (PG-07, -08, -14, -15, -17)** and **internal MML inconsistencies (PG-05, -16)** are proposals only (14 candidate corrections, none applied).

## Routing
- WS-A: the 1964 r.187(1) footnote lead (OQ-C-06).
- WS-B: the official copy for V9-JD-03 (CC-09) and case identities for 13 records (CC-11).
- WS-D: the proposed "manual_supported" relation type (CC-13), which needs the schema lease.
- Owner: OQ-C-01..04, 07, 08.

## Disposition
Accepted as a review proposal. PR opened against `claude/next-stage-proposal`. Not merged. Technical review only.
