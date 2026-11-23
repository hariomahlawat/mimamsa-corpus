# CALIBRATION-02, Reviewer C: Military legal procedure

**DATABASE ONLY. This is an evidence review, not legal approval.** Nothing here is legal-advisor or JAG validation.

The reserved states are unchanged:
- r.23(3) is CONFLICTING. Its caution wording was not re-read or quoted.
- r.193 is C-08 OPEN.
- r.194 is C-09 PROPOSAL.
- r.15, r.187(1) and s.129 are OPEN. s.129 appears on page C-PIC-12 but was not assessed.

This review was written without reading the outputs of reviewers A, B, D or E.

## Files
| File | Content |
| --- | --- |
| `findings.csv` | 383 rows covering all 382 propositions in the 46 records. COI-003#P6 has two rows. The header is exactly the `COLS` list in `tools/check_calibration02.py`. |
| `page_image_checks_C.csv` | 19 new renders, C-PIC-01..19. Each row gives the document SHA-256, page, render DPI, render PNG SHA-256 and what was observed. |
| `build_findings_C.py` | Deterministic generator for both CSVs (stdlib only). Rerunning it rewrites them byte-identically. |

## Method
1. I read every proposition in `propositions.csv` and assessed the procedure dimension:
   - competent authority;
   - initiation and investigation;
   - safeguards and hearing;
   - disciplinary versus administrative route;
   - evidence;
   - time limits;
   - review, appeal and remedies;
   - exceptions.
2. Each legal proposition was compared with the held text of the Army Act, Army Rules or AFT Act. Where relevant it was also compared with the held SC judgments and the MML.
3. **Wording relied on was read from page images** rendered with PyMuPDF 2.1 (C-PIC-01..19). Where only a text layer was available, the row says so in `method` or `uncertainty`, and the evidence state is never VERIFIED.
4. **Evidence states were assigned as follows:**
   - `VERIFIED_AGAINST_HELD_PRIMARY_SOURCE` is used only for primary documents read from a page image: the 1954 Army Rules Gazette facsimile, the S.R.O. 17(E)/1993 Gazette, or an official SC judgment PDF.
   - Readings from India Code compilations (Army Act, Army Rules, AFT Act) are `SUPPORTED_BY_SECONDARY_SOURCE_ONLY`, even when image-checked. This follows SOURCE_AUTHORITY_POLICY v1: compilations are comparison text.
   - The MML was used only for comparison (C-PIC-17). It is never authority, and its editions are unverified.
5. Design, heading and workflow statements are classed `NOT_A_LEGAL_PROPOSITION`. Where such a statement carries procedural content, the finding text still records whether it is consistent.
6. **Dates:** publication, commencement and any retrospective deemed effect are kept separate.
   - S.R.O. 17(E)/1993 commencement "on publication" is taken from ARMY-RULES-CHAIN-01 AR-029.
   - The compilation's "w.e.f." notes for Act 37 of 1992 are recorded as printed but not adopted; WS-A has its commencement as NOT_DETERMINED.
   - No effective date was inferred from publication.

## Sources (SHA-256; paths relative to the session scratchpad)
| Source | SHA-256 |
| --- | --- |
| Army Rules 1954 Gazette, 27-11-1954 (`downloads/discovery/ia_in.gazette.central.w.1954-11-27.103686.pdf`) | c5ef95a9d553685aa655f041b71d8360d6272e2775a19a3d6e7273c6cbd0aca6 |
| S.R.O. 17(E)/1993 Gazette (`downloads/independent-reviewer-D/amend/.../16490.pdf`) | e9bf2114ab633716ea954db6e100be858e45949384f9fc0667364308bff46912 |
| Army Act 1950, India Code compilation (`downloads/independent-reviewer-A/army-act.pdf`; = origin/raw-data raw file) | e47a4265813e95b491a24926428ed306cfeaae9013e7edb928cefef6e69a7c08 |
| Army Rules 1954, India Code compilation (`downloads/independent-reviewer-A/army-rules.pdf`) | 48f52219121bf74d070bc832e4573f2f512b239e0a0441ba96b1daca2983a727 |
| AFT Act 2007, India Code compilation (`downloads/independent-reviewer-A/aft.pdf`) | 665863d1abb802f7488eb75f776946e30e72ccec16962da8e2b3ee8f2e023e3b |
| MML 2.pdf (`mml_x/originals`) | db2119182ed2e4ccca22dd225d955327f6398ee98303e1c94615ba85b4396f65 |
| Virendra Kumar (SC 2020) | 0ff9d2fc8ef36dfebe862739e517b5ec51f4fff9b4f9b3f7b86beece5d85e819 |
| P S Gill (SC 2019) | 7c32b8e87984c9f3dd52218f9030dffad3ea5aedc98d256744fd5e97d044a0ac |
| Parashotam Dass (SC 2023), text layer only | fe19875b19ed5a4efa257273cd2fb1f1cbb57c4f383117cc40e9a90046568377 |
| Arjun Panditrao (SC 2020), text layer only | 9c3d7880471fe22f5be2a501bbff40d5b93e32670a37903e04af4dcd92b4aebc |
| BSA 2023 / BNSS 2023 India Code PDFs, text layer only | 554b2b4a…16d5 / 572c7988…0562 (full values in `findings.csv`) |

I also used origin/raw-data `data/text/act-army-1950.txt` (88a9f1dc…) and `rules-army-rules-1954.txt` (94b46401…), but only to locate text. The WS-C-MML registers (PC-04, PC-19, PG-04, PG-07, PG-10, PG-11) and the ARMY-RULES-CHAIN-01 chronology are cited by ID.

## Counts (denominator: 383 rows / 382 propositions / 46 records)
- **Severity:**
  - P1: 0
  - P2: 10
  - P3: 53
  - NONE: 320
- **Evidence state:**
  - NOT_A_LEGAL_PROPOSITION: 206
  - SUPPORTED_BY_SECONDARY_SOURCE_ONLY: 72
  - SOURCE_NOT_HELD: 48
  - VERIFIED_AGAINST_HELD_PRIMARY_SOURCE: 33
  - HISTORICAL_VERSION_UNRESOLVED: 8
  - UNSUPPORTED: 8 (missing pinpoints)
  - INTERPRETATION_REQUIRES_LEGAL_ADVICE: 7
  - CONTRADICTORY_EVIDENCE: 1
  - NOT_YET_REVIEWED: 0
- **Defect class:**
  - OMISSION: 26
  - HISTORICAL_VERSION: 10
  - WORDING_ERROR: 8
  - CITATION_ERROR: 8
  - MISSING_EXCEPTION: 3
  - UNSUPPORTED_GENERALISATION: 1
  - METADATA_OR_TRANSCRIPTION: 1
  - NONE: 326

## Principal findings (P2)
1. **COI-003#P6:** r.182 is understated. "Not all" CoI statements being admissible implies that some are. r.182 as substituted by S.R.O. 17(E)/1993 item 36 bars them against the person, except at a trial for wilfully giving false evidence. They may be used only for cross-examination.
2. **COI-003#P6 (EVIDENCE_QUALITY):** new wording conflict.
   - The S.R.O. 17(E)/1993 Gazette image prints r.182 without the words "evidence against a person subject to the Act," (C-PIC-03).
   - The 1954 Gazette, MML 2 p.222 and the India Code compilation all carry those words.
   - Corrigendum not searched. Escalated as a legal-advisor question.
3. **COI-003#P5:** Virendra Kumar paras 12(d)-13 are omitted. An r.180 objection must be raised at the r.22 hearing or the summary of evidence. It cannot be raised after the final court-martial order.
4. **HCE-016#P2:** the record says s.80 "primarily" covers persons other than officers, JCOs and WOs. In fact s.80 applies only to them.
5. **HCE-016#P3:**
   - The s.83/84/85 authorities are blurred: s.85 covers JCOs only, and the s.85 proviso applies.
   - The s.84(a) right to elect trial by court-martial is omitted.
   - The AR r.26 safeguards are omitted: summary of evidence delivered at least 24 hours before disposal, and evidence heard in the accused's presence.
6. **ADM-CL-02#P1:** the r.14 precondition is omitted, namely satisfaction that court-martial trial is inexpedient or impracticable. The show-cause exceptions are also omitted.
7. **CM-028#P5:** AA ss.145-146 and AR r.145 (unsoundness of mind / incapable of making a defence) are omitted from a fitness-to-stand-trial note.
8. **AFT-003#P2:** the s.3(o) description is imprecise:
   - Exclusion (i) covers AA s.18 orders.
   - Exclusion (iv) excludes SCMs except where the punishment is dismissal or imprisonment for more than three months.
   - Inclusion (iii), summary disposal where dismissal is awarded, is omitted.
9. **CM-026#P1 and #P2:** the statutory electronic-record certificate is omitted. This is IEA s.65B(4) per Arjun Panditrao, and BSA 2023 s.63 from 1 July 2024, applied to courts-martial through AA s.133. The transitional position is put to the legal advisor.

## Relevant earlier WS-C MML divergences
These are not re-decided here.
- **PC-09:** the MML's s.85 proviso omits "or such other officer". This is relevant to HCE-016.
- **PC-04:** the MML DOC text of r.36 is stale. This is relevant to HCE-001 and CM-001.
- **PC-19:** the MML DOC text of r.177 predates 2003. This is relevant to COI-003.
- **PG-10 and PG-11:** r.145 and r.186(1) are said to have been substituted in 1993 but are not itemised. This is relevant to CM-028 and COI-031.

MML 2 agrees with the 1993 Gazette on r.182 and r.179(5A). As above, that agreement is evidence only.

## Limitations
- **Army Act and AFT Act wording:** read only from India Code compilations. No enactment Gazette for either Act is held, so no Army Act or AFT Act proposition is VERIFIED.
- **Text-layer readings only:**
  - Army Rules r.13, r.14, r.15, r.177 and the compilation notes;
  - AA ss.20, 145-146 and 164;
  - AFT ss.14(5) and 30-31;
  - BSA, BNSS, Arjun Panditrao and Parashotam Dass.
  The rows concerned say so.
- **Amendment chains:** only the ARMY-RULES-CHAIN-01 chronology was used. No full chain was checked for rr.180, 182, 185 or 186. The current text of r.186(1) and r.14(4)-(5) is unresolved.
- **Not held:** pension regulations, DESW instruments, censure and CR policies, the Army Orders and four judgments (Kuldeep Yadav, Santosh Lohar, Som Datt Datta, Pooja Pal). These rows are SOURCE_NOT_HELD.
- **AFT appeal limitation:** the AFT (Procedure) Rules 2008 held file is poor OCR, so the time limit for appeals was not read.
- **Single reader:** every image reading was made once by one reviewer. Consequential readings, especially C-PIC-03, need an independent second reading.
