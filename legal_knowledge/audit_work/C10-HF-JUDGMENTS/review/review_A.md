# Review A - independent check of C10-HF-JUDGMENTS audit, sample rows 1-15

Reviewer model: Fable 5.2 (claude-fable-5-2)
Date: 2026-11-24. Output: `review_A.csv` (15 rows). Review only; nothing outside `c10out/jrev_A/` was written, git was used read-only (`cat-file blob`), no network.

## Method
1. Took data rows 1-15 of `REVIEW_SAMPLE.csv`.
2. Bytes: `data/raw/...` paths read from `git -C /home/user/c7 cat-file blob ad77758d:<path>`; the two `legal_knowledge/...` paths (rows 9, 11) resolved through `byte_source` in `HF_JUDGMENT_COPY_REGISTER.csv` to the working store. sha256 recomputed for every file before reading: 15/15 match.
3. Text read from the PDF text layer with pymupdf (`txt/NN.txt`, page markers = PDF page index, which is what the audit's page numbers use). No page had to be rendered to an image; the text layers were legible (rows 2, 5, 7, 8 are OCR of scanned S.C.R. pages with minor noise).
4. For each judgment I read the cover page(s), the page carrying the extracted proposition, and the closing/operative pages; short judgments (rows 4, 12, 13, 15) were read in full. `pages_read` in the CSV lists exactly what was read.
5. "Principal issue and answer" is my reading of the document, labelled "reviewer reading, not legal advice".

## Conventions used in the CSV
- identity_result = CORRECTED whenever a populated value was wrong OR a blank value had to be supplied; `identity_correction` starts with MISSING_SUPPLIED / PARTIAL / WRONG_VALUE / ALL IDENTITY FIELDS BLANK so the two kinds can be separated. Only row 12 has a wrong populated value (decision date); rows 1-8 lack case numbers; rows 9 and 11 lack everything; row 10 lacks one of two writ numbers.
- outcome_result = CORRECTED also where the candidate was NOT_FOUND, where the label matched but came from the wrong text (row 3), and where a multi-appeal judgment has mixed results (rows 7, 8).
- Relevance: I applied DIRECT_MILITARY_LAW to decisions that construe or apply the Army/Air Force/Navy Acts and Rules, the AFT Act, or court-martial law; MILITARY_ADMIN_SERVICE_PENSION to promotion, discharge, pension and similar service disputes of armed-forces personnel decided without construing those provisions; GENERAL_LAW_POTENTIALLY_APPLICABLE where the question decided is general public law or concerns a non-armed-forces body. Rows 1, 4 and 15 are borderline and say so.

## Main findings
- Row 3: one PDF contains two unrelated reported judgments; the outcome evidence came from the second (non-military) one.
- Row 9: one PDF contains a CORRECTED copy and the earlier copy of the same judgment; extraction mixes them.
- Rows 9, 11: Supreme Court judgments filed under an HC stratum with court = "HF_LEGAL_KNOWLEDGE_ONLY" and no identity metadata.
- Row 14: CRPF Act case classed as DIRECT_MILITARY_LAW; outcome "remanded" is a false positive from a narrative sentence.
- Rows 7, 8: mixed disposal across appeals; a single outcome value misstates the lead appeal.
- Propositions: 4 of 13 extracted sentences are quotations from other courts/tribunals (rows 3, 8, 10, 11), one is truncated at a dot inside a date (row 6), and row 2's sentence is the general rule whose court-martial exception is the actual holding. Page numbers were right in all 13; the paragraph number was missing in 7 (rows 1, 3, 6, 7, 9, 11, 14); rows 2 and 12 have no paragraph numbers in the judgment.
- `decision_date_candidates`: every candidate that differs from the printed decision date is a date from the facts, an order under appeal or a cited case (rows 1-4, 6, 10, 15); in row 12 the candidate is right and `issue_date_meta` is wrong.

## Limits
- Long judgments were not read in full (rows 1, 2, 7, 8, 10, 11, 14 especially); the issue statements rest on the headnote/conclusion and operative paragraphs read, and the CSV says where intermediate reasoning was not read.
- For S.C.R. reported files the headnote was used as a guide to locate holdings but pinpoints are to the judgment paragraphs.
- Subsequent history (overruling, later benches) cannot be verified from the documents. The one status flag raised (row 8) is from general knowledge and is marked as unverified.
- OCR text layers: names and numerals were cross-checked within the document where they looked doubtful (e.g. row 7 respondent name, row 2 date line) but not against any external source.
- No check was made of the `statutes` column beyond incidental remarks (rows 3, 9, 15).
