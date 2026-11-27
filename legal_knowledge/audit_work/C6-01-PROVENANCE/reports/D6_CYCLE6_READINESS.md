# D6. Cycle 6 readiness report (C6-01 complete as proposals; C6-02 to C6-05 prepared)

## C6-01 status
- **Scope:** 34 sources, 36 copies: 26 publication/record sources with 26 copies, and 8 judgment sources with 10 copies. Denominators kept separate: 67 unique binaries, 93 held paths and 54 undocumented copies in Cycle 5.
- **Outcomes after the Fable 5.2 review:**
  - 32 copies are proposed PROVENANCE_DOCUMENTED, all at FULL strength and all with identity verified;
  - 4 are PROVENANCE_PARTIALLY_DOCUMENTED:
    - the Delhi HC rules chapter (image check PARTIAL; currency UNKNOWN);
    - Act 13/1975 (identifier only, no URL or date);
    - the Rajya Sabha papers-laid record (its retrieval record disclaims authenticity; also **WITHHELD** by owner instruction; its S.O. 4010 date is DISPUTED);
    - Rajbir copy C2 (its only locator is a mention in C1's record);
  - none are NO_RECOVERABLE_PROVENANCE or AUTHENTICATION_PENDING;
  - Isaac is out of scope and unchanged.
- **Proposals (D2):** 32 additions, none incorporated:
  - 20 primary Gazette facsimiles;
  - 8 primary SC court copies;
  - 4 non-primary: TRA 2026 and the 2022 archive.org derivative e-Gazette, both under the uniform copy-fidelity rule; ER 2023 13 MB; and the Rajbir rendition.
- **Coverage if incorporated (D4):**
  - documented-primary copies 12 to 40, and sources 12 to 40;
  - cases with an exact anchor 6 to 13 of 53;
  - KB citation items unchanged (42 exact).
  - Incorporation would use the overlay design (`addendum/INTEGRATION_ARCHITECTURE.md`, revision 2): no Cycle 4 or Cycle 5 file is edited, and no holding state is changed by hand.
- **Independent verification (D3):**
  - final review of e7a10e27: ACCEPT WITH CONDITIONS;
  - re-review of c3235312: ACCEPT;
  - Fable 5.2 review of a165b0f3: ACCEPT WITH CONDITIONS, with 9 P2 findings, all addressed, and a re-review of the corrections. See `reports/D3_INDEPENDENT_VERIFICATION.md` and `review/`.

## What C6-01 cannot fix (and what can)
| Gap | Why C6-01 cannot close it | What can |
| --- | --- | --- |
| KB exact anchors stay at 42 of 1,060 items | KB citations resolve to Acts whose held copies are compilations | **C6-02** (Gazette texts of the Army Act, AFT Act, BNSS and BSA), then register rows and page checks |
| Delhi HC rules chapter: partial | the image check is PARTIAL: the copy prints no court name, volume or date | the printed rules volume, or a court-registry confirmation of the file (TRA 2026 was resolved by its image check) |
| Act 13/1975: partial | the download record gives an identifier, not a URL or date | a retrieval record for these bytes; a re-acquisition creates a new copy and needs an equivalence test (`reports/EVIDENCE_RECOVERY_REQUIREMENTS.md`) |
| RS papers-laid; Rajbir C2: partial | disclaimed retrieval record; sibling-copy locator | `reports/EVIDENCE_RECOVERY_REQUIREMENTS.md` sections 3 and 4 |
| 18 compilation and manual copies | outside the C6-01 scope | compilations stay compilations; the MML needs a custodian authentication route (WS-C) |
| Pension module (75 of 96 PEN records missing evidence) | sources not held | **C6-03** (DESW) |
| Regulations for the Army / RMSAF / Army Orders | not publicly located | **C6-04** custodian route |

## Decision points for the owner (each needs explicit approval)
1. **Incorporate the C6-01 proposals.**
   - First, approve the overlay design (`addendum/INTEGRATION_ARCHITECTURE.md` revision 2, with PR 1 carrying zero entries).
   - Then approve tranches of entries, each with its own review. This would lift 7 case records to exact anchors.
   - Also to decide: the uniform copy-fidelity class rule for born-digital Gazette copies (TRA 2026 and the 2022 derivative; `reports/TRA2026_CLASS_COMPARISON.md`).
   - The RS papers-laid record is WITHHELD and is not an entry.
2. **A-C5-1, C6-02 Batch A download.** 20 archive.org files, 18 of them pinned. None is configured in PR #8, #17 or #23. It needs a separate crawler-config PR.
3. **A-C5-2, C6-03 DESW download.** It needs a DESW allow-list extension beyond PR #9. desw.gov.in robots returned 403 in Cycle 5, so a readable robots policy must be established first (fail-closed).
4. **A-C5-3, C6-04 custodian route.** Send no request until the owner approves the request text and the handling of any access marking. The owner must also decide whether the archived CDA copies (C5-ACQ-26) may be examined.
5. **The India Code robots exception** in the staging crawler config: keep, narrow or withdraw (C5-CRAWL-01). This is unchanged by this work.
6. **Legal adviser (C6-05):** 13 topics, 29 escalations, the reserved items and 13 WS-B inconsistencies. No determination is made here.
7. **Cycle 6 PR:** this branch is pushed. It will not be merged without separate approval.
