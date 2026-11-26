# Confirmation review: C13 A6 at 839c33e3 (remediation of review 1b05490f)

I am the independent reviewer of 1b05490f. This pass was read-only, in the same scratch clone. I made no commits and wrote nothing to HF.

## Verdict

**CONFIRMED.**
- F01 (P2) is fixed.
- F02, F03, F04, F06, F08 and F09 are fixed.
- F05 is noted, which I accept.
- F07 is still open, as the author says.
- I found no new P1 or P2.

## Reproduction

- The only commit after 1b05490f is 839c33e3. Its diff touches only `C13-A6-FORMS/` and the A6 test file.
- C12 is unchanged: the diff on `C12-CONSOLIDATION` is empty, and `CAPABILITY_RESTRICTIONS` row `form_field_lists` still reads `NON_OPERATIONAL_RESEARCH_ONLY`.
- `build_a6.py --check` reports `CHECK OK: 10 files reproduce byte-for-byte`, and `SHA256SUMS` checks OK.
- The A6 tests and the C12 research-isolation tests give 26 passed (gov ref present).

## Findings

| ID | Status | Evidence |
| --- | --- | --- |
| F01 P2 | **FIXED** | The new `C12_FIELD_DISPOSITION.csv` has 541 rows, one for every C12 `FORM_FIELDS` field_id: 294 superseded by an official row, 20 superseded by a full official transcription (AFTPR08-F2, listed as id ranges), and 227 carried. Every carried id is present in v2. IAFD-905 now has 19 v2 rows: 5 official para 9 rows labelled `[amending text only]`, plus 14 rows labelled `CARRIED_FROM_C12: MML_ONLY_UNVERIFIED (official copy covers para 9 only…)`. Only C12 F13 and F14 are superseded, mapping to official V2-003 and V2-004. |
| F02 P3 | FIXED | P3B seq 3 is now 'Whereas a' and seq 4 is 'court-martial has been ordered to assemble at'. The page now has 956 rows. |
| F03 P3 | FIXED | p.68 seqs 70, 74 and 82 now read 'whcih', 'Reseve' and 'Service or years', as printed. (My 1b05490f note put 'Reseve' at seq 78; on re-checking, it is seq 74. The author corrected the right rows.) |
| F04 P3 | FIXED | The r.46 preamble rows of R46B, R46C and R46D are now pinned to `pdf_page` 18. |
| F05 P3 | NOTED (accepted) | The conventions and the degraded-glyph normalisations are documented in SUMMARY. Embedded blanks were not itemised retrospectively. |
| F06 P3 | FIXED | `PAGE_IMAGE_LOG` now has 74 readings, including 1965 pp.1–3, 1993 p.18, DPP p.6 and NR65-P2 pp.1 and 105. The register now says 'p.106 (text layer, Forms 25-34)'. |
| F07 INFO | OPEN | A human spot-check is required before the Document Studio 3.3 legal gate. |
| F08 INFO | FIXED | SUMMARY now cites only "RM-001 …". No output file contains `4284820e`. |
| F09 INFO | FIXED (noted) | Case S1-05 carries a note about the orphan ANSWER line. |

The only transcription rows that changed are those listed above. No other wording changed.

## Final R04 disposition, per family

R04 closes partially, and only for transcription fidelity. The capability restriction stays until legal approval.

| Family | Disposition |
| --- | --- |
| APPIII-P2, P3A, P3B, P3C, P4-DELAY | CLOSED_VERIFIED |
| APPIV-P1-F1, P1-F2 | CLOSED_VERIFIED |
| APPIV-P2-FA, FB, FC, FD, FE, FF, FG | CLOSED_VERIFIED |
| APPV-F1A, F1B, FH, FI, FJ, FK, FL | CLOSED_VERIFIED |
| **APPIII-P1D-CHAR (IAFD-905)** | **REMAINS DEFERRED**. Only para 9 (S.R.O. 17(E)/1993 item 39(a)) is held officially. The rest is MML-only until the official Appendix III Part I text is acquired. |
| 8 not-held forms (DPP Sch. I F1–F3, ISL A–D, Tolls Pass) | OUTSIDE R04. MML_ONLY_UNVERIFIED; acquisition items. |

That makes 21 families CLOSED_VERIFIED and 1 deferred. `R04_FAMILY_STATUS.r04_disposition` matches this (21 / 1 / 8 / 12 outside R04 and transcribed). The closure decision itself belongs to the coordinator.
