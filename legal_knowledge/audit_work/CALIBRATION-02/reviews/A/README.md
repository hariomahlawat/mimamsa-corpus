# CALIBRATION-02 Reviewer A: statutory verification

**This is an evidence review, not legal approval.** No state in this folder is legal-advisor or JAG validation. Reserved states are unchanged and were not re-assessed:
- r.23(3) CONFLICTING
- r.193 C-08 OPEN
- r.194 C-09 PROPOSAL
- r.15, r.187(1) and s.129 OPEN
- AQ-05, AQ-06 and OQ-A-13 reserved

Reviewer A worked without reading reviews B-E.

## Files
| File | Content |
| --- | --- |
| `findings.csv` | 384 rows covering all 382 propositions in 46 records. Columns are exactly `tools/check_calibration02.py` COLS. Two propositions have a second row for a distinct issue: COI-003#P6 and CM-012#P1. |
| `page_image_checks_A.csv` | 43 new renders, A-PIC-01..43 (PyMuPDF, 110 dpi grayscale), each with document SHA-256, page, PNG SHA-256 and observation. Each row says whether the page was inspected visually or only its born-digital text layer was read. |

## Method
1. I read every proposition and classified it as one of:
   - a statutory claim;
   - a citation (REF);
   - a judicial claim, for which only the statutory frame was checked (holdings are Reviewer B's task);
   - a policy claim;
   - a design, workflow or heading statement (NOT_A_LEGAL_PROPOSITION).
2. Statutory claims were compared with the best held source:
   - **Army Rules 1954:** the notified text, S.R.O. 484 (Gazette 27-11-1954, archive.org facsimile), plus each located amending Gazette instrument. These are S.R.O. 205/1961, S.R.O. 17(E)/1993 and S.R.O. 8(E)/2003. I checked them against the ARMY-RULES-CHAIN-01 chronology and the WS-A provision change log (PCL-93-*).
   - **Army Act 1950:** no Gazette copy of the 1950 Act is held. Its wording comes from the India Code compilation, which is comparison text only, so claims resting on it are SUPPORTED_BY_SECONDARY_SOURCE_ONLY. The exception is the 1992 amendments: these were read on the Gazette of the Army (Amendment) Act 1992 (37 of 1992), Gazette Extraordinary No.59 of 07-09-1992, and those claims are VERIFIED.
   - **AFT Act 2007, BSA 2023 and BNSS 2023:** India Code compilations only, so SUPPORTED_BY_SECONDARY_SOURCE_ONLY.
   - **Entitlement Rules 2023:** the MoD (DESW) letter of 21-09-2023 with Appendix-I, which is an executive instrument.
3. Legally significant wording was read on a rendered page image. Existing checks were reused where they cover the point: PIC-13, PIC-16, PIC-19, PIC-30, PIC-37 and PIC-07. A-PIC-29 reproduced the PIC-13 render hash exactly.
4. Absence in a search is recorded as NOT_FOUND. I kept publication, commencement and retrospective deemed effect separate. Every Army Rules row carries the caveat that the amendment chain is PARTIAL: AR-001 and AR-030 were not found, AR-036 (after 06-06-2022) was not searched, and 13 hint rows are unopened. So VERIFIED means "matches the held primary instrument at the locator". It does not mean the rule is currently operative.

## Sources used (SHA-256)
| Source | SHA-256 |
| --- | --- |
| Gazette 27-11-1954, S.R.O. 484 (Army Rules as notified) | c5ef95a9d553685aa655f041b71d8360d6272e2775a19a3d6e7273c6cbd0aca6 |
| Gazette 22-07-1961, S.R.O. 205/1961 | 0b4c5b72ea3de650a97d573af317ed6147c62539a1890a64c5797eaf4f60da6d |
| Gazette Extraordinary 06-12-1993, S.R.O. 17(E)/1993 | e9bf2114ab633716ea954db6e100be858e45949384f9fc0667364308bff46912 |
| Gazette Extraordinary 24-06-2003, S.R.O. 8(E)/2003 | ca5d79c25a985c119d13ec1264bff36e7089618604c4cf7d818fc53f7fe606bf |
| Gazette Extraordinary No.59, 07-09-1992, Act 37 of 1992 | f11d443ebfdada41780974c25612d85f7f62853bc552a38e1e2750a209067185 |
| India Code Army Act 1950 (comparison) | e47a4265813e95b491a24926428ed306cfeaae9013e7edb928cefef6e69a7c08 |
| India Code Army Rules 1954 (comparison) | 48f52219121bf74d070bc832e4573f2f512b239e0a0441ba96b1daca2983a727 |
| India Code AFT Act 2007, as on 01-09-2026 (comparison) | 665863d1abb802f7488eb75f776946e30e72ccec16962da8e2b3ee8f2e023e3b |
| India Code BSA 2023 (comparison) | 554b2b4ae3d9f09bf31e6e1ba2b2cb8a4e7f4f5ffd6f3156736752cbbce116d5 |
| India Code BNSS 2023 (comparison) | 572c79880b9f8effc8fa6e39b864101835a0fb5d85b194b90a99d170121a0562 |
| DESW letter 21-09-2023, Entitlement Rules 2023 | 29f6fa2cfcd961aadce490679a686b5a3b7b2e683a0eaceb42bc2cd2ebb70dad |
| P S Gill 2019, PPS Bedi, Parashotam Dass 2023 (statutory frame only) | 7c32b8e8…, 211dbaf4…, fe19875b… (full values in findings.csv) |

## Counts (384 rows)
| Evidence state | Rows |
| --- | --- |
| NOT_A_LEGAL_PROPOSITION | 177 |
| SUPPORTED_BY_SECONDARY_SOURCE_ONLY | 89 |
| VERIFIED_AGAINST_HELD_PRIMARY_SOURCE | 52 |
| SOURCE_NOT_HELD | 37 |
| INTERPRETATION_REQUIRES_LEGAL_ADVICE | 13 |
| HISTORICAL_VERSION_UNRESOLVED | 10 |
| UNSUPPORTED | 5 |
| CONTRADICTORY_EVIDENCE | 1 |

| Severity | Rows |
| --- | --- |
| P1 | 0 |
| P2 | 8 |
| P3 | 42 |
| NONE | 334 |

## Main findings
**P2 findings:**
- **CM-028 P7, P8 and REF:** the record cites "AR rr56" for fitness and adjournment, which is the wrong rule. r.56 concerns the accused's application to adjourn for non-compliance with the defence-preparation rules. The correct rules are r.82 (adjournment), r.83 (suspension on dissolution) and r.84 (illness of accused). The record also omits AA ss.145-146 (unsoundness of mind and subsequent fitness).
- **CM-026 P2, P7 and REF:** the record says there is no statutory certification rule for electronic evidence. In fact BSA s.63(4) requires a certificate in the Schedule form, and IEA s.65B applies to proceedings pending on 01-07-2024 (BSA s.170(2)). The governing evidence statute is left as "[VERIFY]". AA s.133 still names the IEA 1872, which raises a reading question for the legal advisor.
- **CIV-011 P3:** the record omits that the parent provision of the 1978 Adjustment of Jurisdiction Rules changed from CrPC s.475 to BNSS s.521. From 01-07-2024 the Rules continue under BNSS s.531(2)(b), but the 1978 Rules themselves are not held.
- **COI-003 P6 (new source conflict):** on the Gazette image, r.182 as substituted by S.R.O. 17(E)/1993 omits the words "evidence against a person subject to the Act," after "admissible in". The India Code compilation prints them. Recommended action: log this in SOURCE-CONFLICTS-01, run a corrigendum search and get a second page-image reading.

**Recurring P3 findings:**
- Citation ranges include omitted provisions: s.127 (omitted 1992) and r.25 (omitted 1993).
- Rules substituted in 1993 and 2003 are cited without version tags: rr.22, 182, 186(1) and 177.
- Records omit the amendments made by Act 37 of 1992: ss.80(j), 81(1), 81(4) and 85.
- The IPC to BNS change from 01-07-2024 is not noted.
- Records omit that s.15 appeals have their own time limit, prescribed under the AFT (Procedure) Rules, not s.22.
- Some citations give no locator ("See linked module provisions").

## Limitations
- **Army Act and AFT Act wording:** no Gazette copy is held for the Army Act 1950, the AFT Act 2007, BSA or BNSS, so their wording is comparison text only. Commencement of BSA and BNSS (S.O. 849(E) and S.O. 848(E)) rests on India Code footnotes.
- **Army Rules currency:** the amendment chain is incomplete, so no Army Rules provision is established as currently operative.
- **Instruments not held:**
  - Pension Regulations (edition unstated in the records)
  - censure and CR policies, Army Orders, the DESW FAQ and the 16-07-2020 letter
  - the 1952 and 1978 Adjustment of Jurisdiction Rules
  - the Inter-Services Organisations Act 2023
  - the Santosh Lohar, Kuldeep Yadav, Som Datt Datta and Pooja Pal judgments
- **AFT (Procedure) Rules 2008:** only an OCR-derived text is held, so the time limit for appeals was not verified.
- **Pages not visually inspected:** compilation pages were rendered and hashed but most were read from their born-digital text layer. Each such page is labelled in `page_image_checks_A.csv`.
- **Judicial content:** holdings, ratio and later treatment were not assessed (Reviewer B).
- **Second reading:** the new r.182 discrepancy rests on one reviewer's reading. It needs an independent second reading.
