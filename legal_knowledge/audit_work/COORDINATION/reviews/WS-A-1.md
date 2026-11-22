# Coordinator review: WS-A hand-off 1 (issue #11), 2026-11-22

**Reviewed:** `claude/ws-a-statutory` commit 84196221, plus merge 74530be9 of `claude/next-stage-proposal` (PR #16). No agent file was edited.

## Checks performed
| Check | Result |
| --- | --- |
| Paths changed only under `WS-A-STATUTORY/` | PASS |
| No source downloads | PASS: `network_requests_log.tsv` has 88 requests (archive.org 81, indiacode 5, egazette 2), all search, metadata or HTML; no PDF or `/download/` URL |
| TLS not bypassed | PASS: egazette TLS failure recorded, not bypassed |
| Gates after merge with PR #16 | PASS: audit tests OK; PILOT-01 and R23 strict OK; `check_registers.py` 0 errors; WS-A CSVs well formed |
| **Independent image check of the consequential finding (C-08)** | **CONFIRMED.** Own render of S.R.O. 17(E)/1993 PDF p.19 (file sha e9bf2114…; render 120 dpi, sha a02cbb5f0307a09bb0d0b03ac270a1df8e9b038a43a193ebf4c5d28c1e9a6f3b). Item 38 reads: "For rule 193 of the said rules, the following rule shall be substituted, namely:— '193. Prescribed Officer under Section 90(i) and 91(i).—The prescribed officer for the purposes of clause (i) of section 90 and clause (i) of section 91 shall be the Chief of the Army Staff or the officer commanding the Army'." |
| Independent image check of the 1954 base text | **CONFIRMED.** Own render of the 1954 Gazette PDF p.56 / printed p.346 (file sha c5ef95a9…; render sha 124cf90955f4d54e332346319853e8c83dc44af1b18b6b39dd96ef3272ff35b0). r.193: "...clause (i) of section 91 shall be the Commander-in-Chief." r.194: "...in the case of an officer, the Commander-in-Chief and, in the case of a person other than an officer, the officer empowered to convene a court-martial for his trial." |

## Assessment
- **C-08 (r.193).** The chronology is now complete on the located instruments: 1954 (s.91(i), C-in-C) → S.R.O. 302/1987 (s.91(i), "Officer Commanding an Army") → S.R.O. 17(E)/1993 item 38 (s.90(i) and s.91(i), "officer commanding the Army"). The India Code compilation text matches the 1993 substitution. The earlier discrepancy U-04 is therefore **explained** on the located evidence.
  - Remaining uncertainties: instruments not located (E-7/1960, S.R.O. 258/2002, after 2022, unverified hints); the "an Army" vs "the Army" wording (OQ-A-02); and legal effect.
  - **State stays OPEN** pending legal review. Any correction is a proposal for the advisor (AQ-03).
- **C-09 (r.194).** No 1993 item touches r.194. The compilation equals the 1954 text with only the title updated, lacking the 1989 words. Stays a PROPOSAL.
- **New commencement evidence:** S.R.O. 17(E)/1993 r.1(2) is in force on publication (06-12-1993). S.R.O. 484 has no commencement clause.
- **New register hints:** 6 Army Rules amendment hints beyond AR-012/013/015, all LOCATED_UNVERIFIED; ACQ-03 requests proposed, not executed.

## Coordinator follow-ups (coordinator-owned paths, separate commit on PR #16)
- ARMY-RULES-CHAIN-01: AR-029 itemisation and commencement from PCL-93-*; AR-000 commencement; C-08 evidence item (4) superseded by PCL-193-1993 and this review. r.193 remains OPEN.

## Disposition
Accepted as a review proposal. PR opened against `claude/next-stage-proposal`. Not merged. Technical review only.
