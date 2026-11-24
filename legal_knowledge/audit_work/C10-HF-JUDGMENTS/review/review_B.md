# Review B - REVIEW_SAMPLE.csv rows 16-30 (15 Supreme Court judgments)

Reviewer model: Fable 5.2 (claude-fable-5-2). Date: 2026-11-24. Output: `review_B.csv` (same folder).
Everything here is a reviewer reading of the documents, not legal advice and not legal verification.

## Method
- Bytes: `git -C /home/user/c7 cat-file blob ad77758d:<path>` for each row (all 15 paths are under `data/raw/sci/`; no `legal_knowledge/` paths in this half, so the copy register was not needed). Read-only; no network.
- SHA-256 of the bytes was recomputed and compared with the sample's `sha256` before reading: 15 of 15 match.
- Text read from the PDF text layer with PyMuPDF. All 15 files have a usable text layer. One page image was rendered (S.P. Gupta p1, to confirm the printed date); it is in `render/`. Extracted PDFs and text are in `pdf/` and `txt/`; helper scripts in `tools/`. Nothing was written outside `c10out/jrev_B/`.
- Page numbers are PDF page numbers (1-based), the same convention the audit uses; SCR page numbers are added where paragraphs are unnumbered.
- For each judgment I read the cover/headnote pages, the 'case arising from' block, the page carrying the extracted proposition (with the surrounding paragraphs), and the closing pages with the operative order. The `pages_read` column lists exactly what was read.

## Conventions used in the result columns
- `identity_result`: CONFIRMED = court and `issue_date_meta` match the print and there was no conflicting date candidate. CORRECTED = `issue_date_meta` matches the print but the audit's `decision_date_candidates` are wrong (each is the date of an impugned order, a cited case or a fact in the narrative). `case_numbers_meta` is blank on all 15 rows, so the printed case numbers are given in `identity_correction` for every row; that gap alone was not counted as CORRECTED.
- `outcome_result`: compared with the Court's own operative paragraph first, the reporter's end-note second. AMBIGUOUS is used where those two differ in a way that changes the label.
- `proposition_assessment`: (a) court's own holding/reasoning, (b) recital of argument or of a cited case/order, (c) misleading out of context, (d) not a proposition.
- `relevance`: the audit gives no written definitions for the five classes, only term-count rules. I applied: DIRECT_MILITARY_LAW = the decision turns on the service Acts, the Rules under them, court-martial law or the AFT's powers; MILITARY_ADMIN_SERVICE_PENSION = pension, promotion, pay, commission and similar service matters of armed-forces personnel decided under regulations or policy; GENERAL_LAW_POTENTIALLY_APPLICABLE = non-military case stating general doctrine usable in military cases. Four of my six disagreements (the pension/pay cases) are boundary calls between the first two classes; those judgments are in scope either way.

## Limits
- Long judgments were not read in full: S.P. Gupta (about 20 of 1,093 pages; headnote and final order only - the seven opinions were not read), Nitisha (about 17 of 138), Dilip Paul (about 11 of 100), S.P. Sharma (about 12 of 68), Prithi Pal Singh Bedi (about 10 of 52), and parts of Sandeep Kumar, Sahni, Metri, Shivendra Bikaram Singh, Satyanand Singh and Bijender Singh. Where the issue statement leans on the reporter's headnote rather than the body, the `concerns` column says so.
- Headnotes in SCR are editorial. Where a pinpoint is to a headnote it is labelled as such.
- The 1982-1983 reports (Bedi, S.P. Gupta) are scans with a noisy OCR text layer; wording quoted from them should be checked against the page image before reuse.
- I did not check the metadata JSON records themselves, only the fields carried in the sample row.
- Whether a judgment has since been overruled, distinguished or followed was not examined, except that Metri (row 30) on its face explains Sandeep Kumar (row 21).
- One remark rests on recollection rather than the document and is marked as such: S.P. Gupta is often cited with a 30 December 1981 date, while this PDF prints 28 December 1981.

## Patterns worth acting on
1. Outcome extractor picks the last 'disposed of' sentence (pending applications) over the operative sentence: rows 18 and 28.
2. In cross-appeal or appeal-plus-transferred-case judgments a single outcome label is wrong or reversed for the titled party: rows 21, 27, 30. These need a per-case-number outcome.
3. Outcome phrase matched inside quoted rule text: row 24 ('remanded' from Army Rule 25).
4. 'accepted' is not recognised as an allowing phrase: row 16.
5. Propositions are often quotations of other judgments or orders, or headnote text: 8 of the 14 extracted. Row 22 would state the opposite of the holding. The 'para' value is the nearest preceding number, which inside a block quote is the quoted judgment's paragraph (rows 17, 21).
6. `decision_date_candidates` was wrong on all 5 rows where it was populated; `issue_date_meta` was right on all 15.
7. `case_numbers_meta` is blank on all 15 although every document prints its case number(s) on p1 or the case-details page.
