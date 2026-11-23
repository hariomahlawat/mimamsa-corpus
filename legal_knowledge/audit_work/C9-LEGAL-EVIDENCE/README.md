# C9-LEGAL-EVIDENCE: statutory evidence packages, amendment graph, corrections, synthetic transaction and decision matrix (Cycle 9)

**Status:** preparation only.
- **Nothing is approved, applied or authenticated.** The AUTH-LEDGER stays at version 0 (`0 443c4bdf…6c6b6b`), and rule version 1 stays in force.
- **Originals:** no original corpus record changes. Every correction is `PROPOSAL_NOT_APPLIED`.
- **No legal determination:** no legal status, commencement date, applicability or precedent treatment is determined.
- **No external action:** nothing was downloaded, no network was used, and no correspondence was sent.
- **Who read the pages:** every page reading is an AI-agent reading (Claude Opus 5.5 subagents) with a render hash. None is human-confirmed.

## Contents
| Path | What it is | Rebuild |
| --- | --- | --- |
| `STATUTORY/` | One structured record per instrument (111): Army Act 1950, Army Rules 1954, AFT Act 2007 with its Procedure and Practice Rules, BNS/BNSS/BSA with commencement, repeal and savings, PRA 2008, ER 2008/2023, GMO 2023. Also the amendment graph (116 edges; publication and commencement kept separate; disputed readings preserved), the acquisition reconciliation of the PR #8, #9, #17 and #23 stacks, the ready manifest (existing approval only), the approval packages, the unresolved matters and the baseline metrics | `python -I STATUTORY/tools/build_stat_c9.py <repo> --evidence-repo <tree with C8-EVIDENCE> --check` (123 outputs) |
| `CORRECTIONS/` | High-risk corrections A–E: consolidated finding register (23), correction proposals v2 (40), record impact (47), wording, and the legal-adviser escalation list ESC-01..09 | `python -I CORRECTIONS/tools/build_corr.py <repo> --check` (`--verify-held <dir>` re-hashes 8 held copies and finds 33 anchors) |
| `TXN-DEMO/` | Synthetic first ledger transaction (ADD, BIND, CORRECTION, WITHDRAW, re-ADD, `--as-of` 0..8, negatives) run through the real CLI in a temporary repository, against the integrated code | `python -I TXN-DEMO/tools/synthetic_transaction_demo.py --check` (43 values plus the transcript) |
| `DECISION_MATRIX_C9.md` | Owner decision matrix: A3, B2, C2, born-digital P-D2/P-D2a/P-D2b, JUDIS P-D3, O-1..O-5, PRIV-01/02, RAW-01, acquisitions, escalations, TXN tooling gaps | — |

The Supreme Court eight-copy package is on the clean evidence branch (draft PR #40, `C9-EVIDENCE-CLEAN/SC-C9/`). It holds the human page-verification pack, the JUDIS policy paper and the joint anchor simulations.

## Principal results
- **Raw store missed in C8.** The `raw-data` branch (`ad77758d`) holds 67 statutory PDFs from the approved India Code run. They include the AFT Act 2007 Gazette, the AFT Procedure Rules 2008 and Amendment Rules 2011, the Practice Rules 2009, the Finance Act 2017 and the Tribunals Reforms Act 2021.
  - Ten C8 "not held" statements are superseded. These copies need registration (AP-C9-02), not acquisition.
  - Their authenticity is not established.
- **Commencement.** The BNS, BNSS and BSA commencement notifications are distinct (S.O. 850(E), 848(E) and 849(E), dated 23-02-2024 per the footnotes). None is held.
  - Act 37/1992 has no commencement clause. The compilation prints "w.e.f. 6-9-1992" only against ss.75-76, s.127 and Chapter XVI. This stays with the legal adviser (AQ-05).
- **Unresolved, with both readings kept:**
  - S.R.O. 34/1963 (January declaration against the June listing);
  - the r.23 "2022 amendment", for which no register gives support;
  - S.O. 4010/1986 dates;
  - a new r.168(2) conflict: the India Code compilation keeps words that S.R.O. 17(E)/1993 item 31 omits.
- **Corrections.**
  - Girish Kumar (2026 INSC 149) para 22 distinguishes Tarsem Singh on two grounds. On the documents held, Tarsem is not overruled.
  - The r.23(3) caution conflict (P0) is confined to one sentence.
  - s.26 is permissive except s.26(3).
  - Parashotam pinpoints and the Ram Avtar URL are wrong.
- **Synthetic transaction.** The full lifecycle works through the real CLI on the integrated code. The real ledger was untouched.

## Tests and checks
- **Reconciliation tool** (`C8-SOURCES/CORPUS-QUALITY/tools/`): BOM handling and field-type validation added, with 54 tests (7 new, each failing against the previous tool).
- **AUTH-LEDGER:** 190 tests, including the new F-01 test.
- **Builders:** every one above reproduces with `--check`.
