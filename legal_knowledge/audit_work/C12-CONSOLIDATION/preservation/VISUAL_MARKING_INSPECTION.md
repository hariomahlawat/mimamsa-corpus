# Visual marking inspection: pages without a text layer

Date: 2026-11-24. This is a record of what was seen on the pages. It does not decide how any document should be classified for access.

## Scope and method
- Input: `c11.../C11-JUDICIAL-QUALITY/preservation/PRESERVATION_INVENTORY.csv`, 48 copies. Of these, 17 copies have `pages_without_text_layer > 0`, covering 73 pages.
- PyMuPDF selected the pages whose text layer has fewer than 20 characters. The count was exactly 73, matching the inventory. Each page was rendered at 110 dpi to `scratchpad/c12_visual/<copy_id with "~" replaced by "_">/p<N>.png`, and every PNG was opened and looked at.
- Before rendering, each source file was re-hashed. All 17 match the inventory sha256. No source file was modified.
- Faint text along page edges was re-rendered at 250 dpi and checked again: Entitlement Rules (ER) pp.20, 29, 32, 35 and AR-011 p.4. The crops are in `scratchpad/c12_visual/_zoom/`.

## Result
- **Pages inspected: 73. Restriction or access markings found: 0. Copies affected: 0.**
- None of the pages shows "For Official Use Only", "Restricted", "Confidential", "Secret", "Not to be published" or any security grading stamp.

## What the pages are
- **Blank pages (7):** AR-006 p4, AR-008 p8, AR-010 p4, AR-011 p4, AR-021 p36, AR-022 p8, AR-029 p22. These are trailing or separator pages of the Gazette scans.
- **Hindi Gazette pages (29):** Gazette of India Part II Sec 4, from AR-016 through AR-029 (1979-1993). These are the Hindi halves of bilingual notifications: recruitment-rule schedules and the 1993 Army Rules amendments. The Devanagari has no extractable text. All are legible; AR-023 p23 is faded.
- **AR-031 (2003 Extraordinary Gazette, S.R.O. 8(E), Army Rule 177):** a scanned two-page image. The masthead reads "PUBLISHED BY AUTHORITY" and "REGD. NO. D. L.-33004/99", and a handwritten "5" sits in the top-left corner. Neither is a restriction marking.
- **RS-PAPERS-LAID-1987:** a scanned Rajya Sabha "Papers Laid on the Table" page, cols 207-208. No marking.
- **ER-2023-HELD-13MB (35 pages, all scanned):**
  - DESW covering letter of 21.09.2023 and the Entitlement Rules 2023 text (pp.1-19).
  - Photocopied annexures:
    - Annexure-I: the 1946 GHQ "Wartime Rules" memorandum (pp.20-27).
    - Annexure-II: Classification of Diseases and the Emergency entitlement rules (pp.28-31).
    - Annexure-III: the 1996 MoD ex-gratia letter for cadets (pp.32-35).
  - The annexure labels are handwritten.
  - Along the bottom edges, text bleeds through from sheets underneath, for example "...dated 28 Jan 1972 addressed to DPsMS." and "...Rule and the Draft R...". The 250 dpi crops confirm these are copying artefacts, not stamps. The annexures are legible but noisy, rated "fair".

## Caveats
- A marking that is too faint to see at 110 dpi, or one that was cropped off when the page was scanned, cannot be ruled out. This inspection covers only the 73 image-only pages. Pages that have a text layer were covered by the earlier text scan (`printed_marking_scan`).

Per-page detail: `VISUAL_MARKING_INSPECTION.csv`.
