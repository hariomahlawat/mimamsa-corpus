# D6. Cycle 6 readiness report (C6-01 complete as proposals; C6-02 to C6-05 prepared)

## C6-01 status
- **Scope:** 34 sources, 36 copies. Denominators kept separate: 67 unique binaries, 93 held paths and 54 undocumented copies in Cycle 5.
- **Outcomes:**
  - 33 copies are proposed PROVENANCE_DOCUMENTED, all at FULL strength and all with identity verified;
  - 3 are PROVENANCE_PARTIALLY_DOCUMENTED (TRA 2026, Delhi HC rules chapter, Act 13/1975);
  - none are NO_RECOVERABLE_PROVENANCE or AUTHENTICATION_PENDING;
  - Isaac is out of scope and unchanged.
- **Proposals (D2):** 33 additions for the CALIBRATION-02 register: 21 primary Gazette facsimiles, 9 primary SC court copies and 3 non-primary. None is incorporated.
- **Coverage if incorporated (D4):** cases with an exact anchor rise from 6 to 13 of 53. KB citation items are unchanged (42 exact). Documented-primary copies rise from 12 to 42.
- **Independent verification (D3):** see `reports/D3_INDEPENDENT_VERIFICATION.md` and `review/`.

## What C6-01 cannot fix (and what can)
| Gap | Why C6-01 cannot close it | What can |
| --- | --- | --- |
| KB exact anchors stay at 42 of 1,060 items | KB citations resolve to Acts whose held copies are compilations | **C6-02** (Gazette texts of the Army Act, AFT Act, BNSS and BSA), then register rows and page checks |
| TRA 2026 and Delhi HC rules: partial | no page-image identity check | a page-image identity check with a render hash. **No download is needed**: the files are held. This is ordinary non-destructive work for the next step. |
| Act 13/1975: partial | the download record gives an identifier, not a URL or date | an approved re-acquisition from India Code once its robots policy is established (C5 batch F) |
| 18 compilation and manual copies | outside the C6-01 scope | compilations stay compilations; the MML needs a custodian authentication route (WS-C) |
| Pension module (75 of 96 PEN records missing evidence) | sources not held | **C6-03** (DESW) |
| Regulations for the Army / RMSAF / Army Orders | not publicly located | **C6-04** custodian route |

## Decision points for the owner (each needs explicit approval)
1. **Incorporate the C6-01 proposals.** Approving D2, after D3, as a reviewed addendum to `CALIBRATION-02/registers/source_authentication_register.csv` (an addition, not an in-place edit) would lift 7 case records to exact anchors.
2. **A-C5-1, C6-02 Batch A download.** 20 archive.org files, 18 of them pinned. None is configured in PR #8, #17 or #23. It needs a separate crawler-config PR.
3. **A-C5-2, C6-03 DESW download.** It needs a DESW allow-list extension beyond PR #9. desw.gov.in robots returned 403 in Cycle 5, so a readable robots policy must be established first (fail-closed).
4. **A-C5-3, C6-04 custodian route.** Send no request until the owner approves the request text and the handling of any access marking. The owner must also decide whether the archived CDA copies (C5-ACQ-26) may be examined.
5. **The India Code robots exception** in the staging crawler config: keep, narrow or withdraw (C5-CRAWL-01). This is unchanged by this work.
6. **Legal adviser (C6-05):** 13 topics, 29 escalations, the reserved items and 13 WS-B inconsistencies. No determination is made here.
7. **Cycle 6 PR:** this branch is pushed. It will not be merged without separate approval.
