# Union of India v Balakrishnan Mullikote, 2026 INSC 286 (copy C5-SRC-J-SC-2026-MULLIKOTE~C1)

Reader: AI agent (Claude Opus 5.5 subagent), not human-confirmed. Checked 2026-11-23. Renders: 150 dpi, grayscale, PyMuPDF, full page; PNG hashes in `../page_checks_sc_c8.csv`. Held file re-hashed before use: MATCH. Evidence only; no approval, no statement of legal status.

**Copy:** sha256 `10e1954f2e39916ea0f0e8e759c3823581becf752dd6ad2e9058569a1fd97444`, 730,763 bytes, 62 pages.
- Recorded locator: `https://api.sci.gov.in/supremecourt/2023/27246/27246_2023_14_1501_69641_Judgement_24-Mar-2026.pdf`.
- pdftk 2.02, then iText 5.2.1; **created 2026-04-04 10:09:20, modified 10:11:55 +05:30**.
- Signature byte range [0 721447 726255 4508] spans the file. This is structural only; the signature has not been validated.

## What the pages show
| Item | Reading | Source |
| --- | --- | --- |
| Markings | **CORRECTED**, REPORTABLE, **2026 INSC 286**, QR code | C8-SCPIC-19 p.1 |
| Case number | "CIVIL APPEAL NO ____ OF 2026 (Arising out of Diary No(s). 27246/2023)". The lead appeal number is **blank**; most connected appeal numbers are blank; one is CIVIL APPEAL NO.5199 OF 2023 | p.1 |
| Parties | UNION OF INDIA & ORS. v BALAKRISHNAN MULLIKOTE (EX HAV **2568912 M**) | p.1 |
| Signature appearance | "Signature Not Verified / Digitally signed by KAVITA PAHUJA / Date: 2026.04.04 10:11:55 IST / Reason:". The name is partly obscured in the render and was read in full from the text layer | p.1 |
| Running footer | "Civil Appeal No.____of 2026 arising out of Diary No.27246/2023 & connected matters Page X of 62", pages 1-62 complete | all pages |
| End of first version | Para **51**, CONCLUSION: "The Appeals are accordingly dismissed"; [MANOJ MISRA,J], [MANMOHAN,J]; "New Delhi; March 24, 2026" | C8-SCPIC-20 p.31 |
| Second cover | REPORTABLE (no CORRECTED, no INSC, no QR, no signature appearance); respondent "EX HAV **256812 M**" | C8-SCPIC-21 p.32 |
| End of file | The same conclusion as para **99**, with the same judges and date | C8-SCPIC-22 p.62 |

## Two versions in one file
- Text-layer comparison of pp.1-31 against pp.32-62 (`../tools/half_diff.py`, output in `../tools/mullikote_half_diff.txt`): word similarity 0.993.
- The only differences are:
  - the cover markings (CORRECTED, INSC, signature appearance);
  - the service number, 2568912 M against 256812 M;
  - one spelling, "Balakrishnan" against "Balakrishanan";
  - continued automatic numbering in the second half: paragraphs 52-99 for 1-51, list letters C/D for A/B, footnote 2 for 1.
- That pattern fits a corrected version that was concatenated with an earlier version in one word-processing document. The file does not say which change was the correction.
- This is already recorded as WS-B open_inconsistencies_cycle3.csv#OI-03 (OPEN). WS-B cites render 1f23da6a... for p.31; the C8 render hash differs because the render settings differ.

## Comparison with corpus identity
- The C6-01 identity ("2026 INSC 286 (corrected)") and cases_53 `DCLR-SC-2026-N16` (2026-03-24; 2026 INSC 286; Diary 27246/2023) both match the pp.1-31 version.
- The cases_53 pinpoint "Paras 33-44, 51" fits the pp.1-31 numbering, and `source_note` flags the duplication.
- **Open points:**
  - Which version the court's corrected judgment consists of: the file's own p.1 marks pp.1-31 as CORRECTED.
  - The correction date is not printed. The signing and creation date (2026-04-04) is later than the judgment date, and the URL can be re-served (Fable F-15).
  - The C6-01 statement "full judgment file held" holds, but "Page 1 of 62" overstates the judgment length: the judgment is 31 pages, held twice.

## Identity result
- **CONFIRMED** for case identity, from pp.1 and 31.
- **PARTIAL** for the pp.32-62 version.
- Recommendation: any anchor or pinpoint should name pp.1-31 explicitly.
