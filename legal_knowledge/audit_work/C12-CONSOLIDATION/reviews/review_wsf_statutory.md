# Independent review: C12 Workstream F (statutory citation improvement, C12F-v1)

**Verdict: ACCEPT WITH CONDITIONS.** 57 of the 63 proposed promotions are supported. Six are not, and must stay PARTIAL_MATCH before anything is applied. That changes the proposed counts from EXACT 105 / PARTIAL 589 to **EXACT 99 / PARTIAL 595**; MISSING stays at 289.

This is an AI documentary review. It is not legal validation. The reviewer did not do the work under review. All work was read-only. Experiments ran in a disposable copy (`scratchpad/rev_wsf/`), and nothing was committed.

Companion files:
- `review_wsf_statutory_promotions.csv`: one verdict per promotion (63 rows).
- `review_wsf_statutory_findings.csv`: findings F-01 to F-11.

## What was checked and how

1. **The 18 page checks.** All 18 rows in `page_evidence_c12.csv` were re-rendered from the hash-verified held copies with the venv's PyMuPDF at 110 dpi and read on the image:
   - 1954 Gazette: PDF pp.9, 10, 15, 17 and 51.
   - S.R.O. 17(E)/1993: pp.12, 14, 15, 17, 18 and 19.
   - S.R.O. 205/1961: pp.1-3 (printed pp.141-143).

   Every probe and observed excerpt matches the page. This includes the two rows that relied on earlier image checks: the 1961 printed pp.141 and 142 were re-read here. The PNG hashes WS-F recorded cannot be reproduced because the render script is not included (F-08).
2. **The 1954 pages behind the promotions.** WS-F located these from the text layer only: PDF pp.6, 7, 11, 13, 14, 16, 41, 50 and 52 (printed pp.296, 297, 301, 303-304, 306, 331, 340 and 342). Each was image-checked here, and every rule heading sits on the stated page. WS-F's own evidence for these pages is a text-layer heading index plus a register-level "ALL_IMAGE_CHECKED" assertion, which falls short of the project rule (F-03).
3. **All 63 promotions.** For each one the reviewer:
   - read the record in `records_658.jsonl` at git 21e73b83, and confirmed that the locator matches;
   - confirmed that every copy is registered with `eligible_for_exact_anchor = YES` (copies c5ef95a9, e9bf2114, 0b4c5b72, 0ff9d2fc and fe19875b, all hash-verified);
   - cross-checked the amendment coverage for each cited rule against the C9 amendment graph (cfc52d57), the C10 amendment graph (all rows UNCHANGED), the WS-A provision_change_log (107 rows) and the WS-A / WS-C open-question, gap and conflict registers.

   For the two judgments, the reviewer re-derived the paragraph-to-page maps from the text layer and confirmed them on page renders:
   - Virendra: corrected rendition pp.1-21 and original pp.22-42. Paragraphs 10 and 11 differ between renditions only in footnote numbering; paragraphs 16 and 17 really differ.
   - Parashotam: paragraphs 18-35, pp.14-26.
4. **r.135 basis correction.** 1954 p.331 and 1993 p.17 item 25 were image-checked. Item 25 reads "In rules 134, 135 and 136 of the said rules, the words 'or abstract' shall be omitted." It is legible in full. The correction is **supported**: the baseline EXACT had missed this amendment (F-09 adds a minor scope note).
5. **No MISSING item promoted; nothing else changed.** Baselines match `corpus_crosswalk.csv` for 983/983 items. The only transitions are 63 PARTIAL→EXACT; the 42 EXACT, 589 PARTIAL and 289 MISSING items keep their states. Every proposal targets a matrix item.
6. **Cross-volume and proposal samples.**
   - Cross-volume issues sampled: X002, X004, X009, X010 and X012. X004, X009 and X012 are supported (X012 confirmed: "2022" is absent from EV-016, HCE-010 and SC03; ESC-R23-2022 is present). X002 is supported except that it wrongly includes HCE-027 (F-07). X010 is supported but misses the r.15 OQ-A-10 issue (F-01).
   - 15 correction proposals sampled:
     - Promotions P0001, P0002, P0003 and P0004 (P0004 is a page-anchor addition for r.180, p.341, and is supported).
     - Page-anchor additions for r.185 (p.342), r.24 (p.300), r.39 (p.305), r.40 and r.41 (p.306) and r.178 (p.340). All were confirmed on the image.
     - P0103 and P0105 (basis corrections).
     - P0106, P0107 and P0108 (version and reserved-conflict notes). These are consistent with the images; for example, 1993 r.22 has no Explanation printed, and the 1993 r.182 omits the words.
     - P0111 (see F-07) and P0116.
7. **Reproducibility.**
   - `--check` reproduces all six outputs byte for byte and verifies the frozen originals: records_658 `9a8f0d19…` and cases_53 `8b8d53cd…`, identical in the worktree and at git 21e73b83.
   - 13/13 tests pass in the venv (Python 3.13).
   - Neither could run under python3.11, which has no pytest or pymupdf installed (F-10).
   - The WS-F files are committed (29b18490) and the worktree is clean.

## Main findings

- **F-01 (P1): r.15 promotions ignore an open alleged amendment.** Five promotions cite r.15: KB-018, ADM-006, ADM-012, ADM-032 and ADM-SC-03.
  - MML 2 p.142 prints "[or Military Secretary]" in r.15 and attributes it to S.R.O. 17(E)/1993.
  - None of that instrument's 41 items touches r.15. The source of the words is NOT_FOUND (OQ-A-10, GAP-15, XC-03, OQ-C-10, PC-14).
  - Coordination lists r.15/OQ-A-10 among the reserved items.
  - WS-F's rule 5 ("no specific alleged, unlocated … instrument naming the provision") should have blocked these promotions. The tool's blocker set never considers OQ-A-10.

  This is precisely the evidence-state inflation risk. These five must stay PARTIAL.
- **F-02 (P2): COI-021 cites a note the Gazette does not contain.** The record cites "r 180 explanatory note" taken from an annotated compilation. That note is not in the Gazette, so the citation cannot carry an exact anchor there.
- **F-03 (P2): text-layer page basis.** 36 Army Rules promotions rest on text-layer page location. The reviewer's image check confirms every page, so this is a documentation condition, not a substantive error.
- **F-04 to F-06 (P2): scope, page ranges and r.15B.**
  - The judgment-citation EXACT state must not spill over into records whose r.22 or r.182 content stays PARTIAL.
  - Record page ranges where the cited sub-rules continue onto the next page: r.179 at pp.340-341 and the 1961 r.14 at pp.141-142.
  - Add an applicability note that r.15B (2019, ineligible copy) disapplies rr.14, 15 and 15A for the CDS office.

## Conditions for acceptance

1. Withdraw 6 promotions:
   - C10Q-CW-0031 (KB-018), -0363 (ADM-006), -0369 (ADM-012), -0395 (ADM-032) and -0402 (ADM-SC-03): r.15, OQ-A-10.
   - C10Q-CW-0087 (COI-021): explanatory note.

   Then add r.15 to the specific-blocker list with a test, and regenerate the outputs and README counts.
2. Add per-page image-check rows for the 1954 pages listed in F-03; this review's renders may be cited.
3. Add the page ranges (F-05), the record-scope condition for judgment items (F-04) and the r.15B applicability note (F-06).
4. Fix the P3 items (F-07 to F-10) before the next consolidation.

Every promotion remains conditional on preserving the anchoring copies (C10 preservation risk), as WS-F itself states.
