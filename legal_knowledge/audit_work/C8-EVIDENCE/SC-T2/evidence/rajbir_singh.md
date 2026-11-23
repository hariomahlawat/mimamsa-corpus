# Union of India v Rajbir Singh: proposed primary copy C1, with context copies C2 and C3

Reader: AI agent (Claude Opus 5.5 subagent), not human-confirmed. Checked 2026-11-23. Renders: 150 dpi, grayscale, PyMuPDF, full page; PNG hashes in `../page_checks_sc_c8.csv`. Held file re-hashed before use: MATCH. Evidence only; no approval, no statement of legal status.

## Which copy is which (SOURCE-LIBRARY-C5/registers/source_copy_register.csv)
| Copy | sha256 | Pages | Held path(s) | Carrier/role (register) | What the file is (C8 observation) |
| --- | --- | --- | --- | --- | --- |
| **C1 (proposed primary)** | `970b96807bcbf8a1255fe16c574b575f64fe2edee1cbb271485fa7661a62c666` | 20 | independent-reviewer-B/rajbir_42379.pdf; independent-reviewer/judis_42379.pdf; judgment-auditor/rajbir_judis_42379.pdf | JUDIS_COPY; locator https://api.sci.gov.in/jonew/judis/42379.pdf | Judgment only, pp.1-20. Court layout with watermark and "Page N" footer. LibreOffice 3.5, created 2015-02-14. No signature |
| C2 (context) | `c6ec489dff7a107b630a8646190a8cda303a54e4e9f5463eaed748ae0a42a1dd` | 21 | independent-reviewer/rop_275403.pdf | SC_ROP_PATH_COPY | Judgment on pp.1-18, then Record of Proceedings dated 13/02/2015 on pp.19-21. PDF title "Record Of Proceedings_SUPREME COURT", LibreOffice 4.1 modified by iText 5.2.1, created 2015-04-29. Signature appearance "Digitally signed by Sarita Purohit, Date: 2015.04.29 16:27:19 IST" on p.1. **No row in AUTH-LEDGER/evidence/copy_structure.csv** |
| C3 (non-primary rendition) | `6b495f1483657581965b808b18aa23c09b424989e41d43226c90d35845855cde` | 15 | judgment-auditor/rajbir_bosir_2213461.pdf | OTHER_COURT_SYSTEM_COPY | GNU enscript plain-text rendition ("Enscript Output", Ghostscript 8.71, created 2017-07-12) of the **C2** content. It includes the signature appearance as text and the ROP. C2 page numbers 1-21 survive inline |

Page checks: C1 is C8-SCPIC-12, 13 and 14. C2 is C8-SCPIC-23 to 26, and C3 is C8-SCPIC-27 and 28 (context only).

## C1 readings
- Case numbers:
  - CIVIL APPEAL NO.2904 OF 2011 with 21 connected C.A. numbers, including "CIVILL APPEAL D.16394 OF 2013" as printed (p.1).
  - C.A. 1854, 1855, 1856, 1858 and 1859 of 2015 (p.2).
- Parties: "Union of India & Anr. ...Appellants Versus Rajbir Singh ...Respondent".
- Marking: REPORTABLE.
- Author: T.S. THAKUR, J. (p.2).
- Last page (p.20): para 17 "these appeals fail and are hereby dismissed without any order as to costs"; dotted signature lines for (T.S. THAKUR) and (R. BANUMATHI); "New Delhi February 13, 2015".
- No neutral or reported citation is printed.

## Comparison
- The word-level text comparison of C1 pp.1-20 with C2 pp.1-18 (`../tools/copy_diff.py`) gives a ratio of 0.995. The differences are watermark text, hyphenation, and C2's signature appearance.
- **Pinpoints are copy-specific.** The judgment ends on p.20 in C1 and on p.18 in C2.
- **Discrepancy:**
  - The C6-01 identity for C1 reads "(JUDIS 42379; rop_275403; bosir copy)".
  - rop_275403 is C2 and bosir is C3. Neither is C1.
  - The identity string therefore merges three copies.
  - An anchor must name exactly one copy (R-T2-6). The simulation names C1 as `anchor_copy_id`.
- cases_53 `DCLR-SC-2015-N09`:
  - Date and case number match.
  - `primary_source_url` is empty, `accessible_source_url` is Indian Kanoon, and `source_status` is SECONDARY_TRANSCRIPTION_AND_SC_OFFICE_RECORD.
- C2's ROP lists C.A. 4409/2011 and SLP(C) 22765/2011, which the order delinks from the batch. C1's cover does not list them.

## Classification observations
- C1 follows the same JUDIS-path pattern as Dharamvir: court layout with a watermark and a second page series.
- C2 is the only Rajbir copy with a signature appearance. Its embedded signature has not been checked (no copy_structure row).
- C3 is a derivative text rendition of C2 and must never anchor.

## Identity result
C1: **CONFIRMED**
