# Review of the C11 judgment-identity workstream

Reviewer: Fable 5.2 (claude-fable-5-2), AI documentary review. Not a legal verification.
Date: 2026-11-24. Reviewed at worktree commit f479c332 (identity folder clean), bytes from `/home/user/c7` at `ad77758d`, every blob re-hashed before use.
Nothing in the reviewed worktree was changed; experiments ran in a disposable copy under `scratchpad/rev_id/`. The `holdout/` folder was not opened. Nothing was downloaded.

## Verdict

**REVISE.** Everything the workstream merged is right, but the headline count of 3,664 distinct judgments is too high.

- All 12 normalised-text merges, all 5 incomplete-copy merges, the +1 composite and the 15 sampled duplicate groups are the same judgment in each case. I found no wrong merge.
- The count misses duplicates the tool cannot see or chose to hold apart. Corrected count on what I verified against the PDFs: **3,631** (33 fewer).
- 3,631 is an upper bound. My search for scanned duplicates only compared files with the same court and metadata date.

## Corrected count

| Step | Change | Count |
| --- | --- | --- |
| Claimed distinct judgments | | 3,664 |
| Delhi HC 08.07.2011, LA.APP 784/2005 & connected: 20 scanned files, one judgment (F1) | -19 | |
| Delhi HC 18.05.2011, W.P.(C) 3024/2011 & connected: 4 files, one judgment (F1) | -3 | |
| Delhi HC 20.11.2008, WP(C) 5946/2007 & connected: 6 scanned files, one judgment (F1) | -5 | |
| 081a8b226793 also holds a separate order of 13.11.2009 (F1) | +1 | |
| Seven copies of one Delhi HC order of 20.04.2026, held apart (F2) | -6 | |
| J&K 260-page judgment, 34 + 10 copies held apart (F3) | -1 | |
| **Corrected distinct judgments** | **-33** | **3,631** |

Not included: up to 6 one-page pointer orders ("For orders, see ...") whose lead judgment is in the corpus (F7). Whether they count is a rule the owner should set.

## What I checked

1. **Reproducibility: confirmed.**
   - `--check` in the venv: "OK, all outputs reproduced byte for byte", exit 0, 4m20s.
   - Tests: 11 run, OK, 1 skipped by design, on both the venv and python3.11.
   - Without PyMuPDF, `--check` prints the skip reason and verifies checksums and the one-row-per-file accounting.

2. **The 12 normalised-text merges (-61): all correct.**
   - I read the full text of all 97 files. Within each group the text is identical once the per-download time stamp is masked or the quote and dash glyphs are mapped.
   - None is a boilerplate order repeated across cases. Each is one document whose cause title lists every member case, and every file's crawler case number is printed in it.
   - Per-group verdicts are in the items CSV.

3. **Incomplete copies, composite, split verdict: all correct.**
   - The five incomplete-copy merges match on every readable page, not just page 1. In two groups the only difference is the signature stamp missing from the tail-cut copies.
   - Vijaynath Jha: pp.16-25 are *Adarsh Cooperative Housing Society Ltd. v. Union of India*, W.P.(C) 129/2018, Supreme Court, 16.02.2018, [2018] 4 SCR 575. The C10 note calling it a Delhi HC case is wrong; the workstream's correction is right. Both reports in the file are complete.
   - b64df349c9f5: pp.1-193 Rajiv Shakdher J., pp.194-393 C. Hari Shankar J., same cases, date and neutral citation. One judgment.

4. **15 sampled duplicate groups: all the same judgment.**
   - Raw text is identical across copies in each group. Two groups have an unreadable text layer; I read page 1 of one from a page render and it lists exactly the four member cases.
   - Proceedings are kept distinct: all 3,823 (court, case number) pairs in the C10 metadata are in the register, and no file loses a number.
   - Proceedings with no stored file are only partly listed (F6).

5. **Held-apart candidates: two should be merged, the rest are right.**
   - Wrong to hold apart: the seven Delhi files (F2) and the J&K 34 + 10 (F3).
   - Right to hold apart: the two P&H "not pressed" orders in different cases, the inner orders of the 81-page record, the five unreadable LA.APP files, and the four C10 same-case / same-citation pairs (each is two different orders on different dates).

6. **23-file recovery plan: confirmed.**
   - Sample of 8 (lowest hash): 4 have no bytes in the commit, as stated; the other 4 match the plan on bytes, `%%EOF` count, opens / does not open, and pages with text. I also checked the remaining 15 files with bytes; all match.
   - d992ac2bb73a → 9809fac1c661: the base revision of 9809 (up to the first `%%EOF`) opens without repair as a complete 12-page judgment ending in the operative order, and matches d992 page for page.
   - No acquisition: 23 of 23 rows say NO, the tool has no network code, and the corpus clone is unchanged.

7. **87 correction-marker flags: 86 are ordinary wording.**
   - Sample of 10: 9 ordinary, 1 is Virendra Kumar, the genuine two-version file. I then read all 87: 49 are only the Delhi "Click here to check corrigendum" link, 37 are ordinary wording, 1 is Virendra Kumar (F4).

## Findings

| ID | Severity | Finding | Requested action |
| --- | --- | --- | --- |
| F1 | P1 | Scanned copies of a common judgment are counted once per file. Three sets found (30 files, 3 judgments), plus one undetected composite. Net -26. | Add a scan-aware identity step, merge the three sets, record the composite, restate the count. |
| F2 | P2 | STGX-48cde9cce413 is one order of 20.04.2026 in seven copies, not "a judgment whose crawler dates differ". The 2025 dates are metadata errors. -6. | Merge; fix the README; send the seven dates to the metadata workstream. |
| F3 | P2 | The J&K 34 + 10 sets are one judgment; the only differences are quote glyphs read as digits. -1. | Map the glyph substitutions before the number guard, merge, rerun. |
| F4 | P3 | "The 87 flags are ordinary words" is wrong for one: Virendra Kumar. | Reword to 86 of 87. |
| F5 | P3 | The second judgment in the Vijaynath Jha file has no key, row or proceeding key. | Key each judgment inside a composite; correct the C10 note. |
| F6 | P3 | Proceedings without their own file are listed only from pp.1-3: 6 of 46 for the J&K judgment. | Label the column partial or parse the full cause title. |
| F7 | P3 | One-page pointer orders are counted as separate judgments (up to 6). | Set the rule and link them to the lead judgment. |
| F8 | P3 | The first-page 0.95 rule is unsafe in general: 567 pairs of different-case orders share at least 90% of their text. The five merges made with it are correct. | Require equal case numbers or an all-page match. |
| F9 | P3 | The split-verdict file is not flagged as two opinions with no majority. | Add a flag with page ranges. |
| F10 | INFO | Reproducibility, merges, sample, plan and no-acquisition claims confirmed. | None. |
| F11 | INFO | Two metadata defects seen in passing (2018 INSC 185 on two different Kudrat Sandhu orders; c1a83ee07b70 date). | Route to metadata. |

## Evidence for F1

Each scanned file is a one-page sheet for its own case reading "For orders, see <lead case>", followed by the same common judgment with the lead-case footer on every page.

| Set | Files | Evidence |
| --- | --- | --- |
| Delhi HC 08.07.2011, *Jamna v. UoI*, LA.APP 784/2005 & connected | all 20 Delhi files of that date, 20 pages each | Footer "LA.APP.784/2005 & connected Page 1..19 of 19"; page thumbnails of pp.2, 11, 20 correlate 0.65-0.99 with a reference copy (control -0.1); two pages of a copy with no text layer were read as images |
| Delhi HC 18.05.2011, *Bikram Singh v. UoI*, W.P.(C) 3024/2011 & connected | 75f7c670 (born-digital, 19 pp), 455c9c75, 6069c60f, b95440b8 (scans, 20 pp) | "For orders, see W.P.(C) No.3024/2011"; "Page 19 of 19"; same operative paragraph 36 and judges |
| Delhi HC 20.11.2008, WP(C) 5946/2007 & connected (Sub Puttan Lal batch) | 3b347f95, 664ecaf6, 781f346a, 79dfb85b, 90a7bf5a (8 pp), 081a8b22 (10 pp) | Same case list on p.1, "WP (C) No.5946 of 2007 and other connected matters Page 8 of 8", 20.11.2008; 081a8b22 pp.9-10 are an order of 13.11.2009 refusing modification |

The README mentions the 2010-2011 Delhi scans only as weak "cover sheet" boundary candidates. The Puttan Lal judgment is a substantive military-law decision, so its identity matters for the citation graph as well as the count.

## Limits of this review

- The search for scanned duplicates compared only files with the same court and metadata date (584 buckets, 2,157 files), using shared word sequences on the first six and last two pages plus pointer-line and footer patterns. Scans with poor OCR or wrong metadata dates could still be missed.
- Items 4, 6 and 7 used the deterministic samples asked for; I extended 6 and 7 to all files, but item 4 covers 15 of 59 groups.
- I did not verify any judgment against an official court source.

## Files

- `fable_review_identity_c11.md` (this file)
- `fable_review_identity_c11_items.csv` (per-item verdicts)
- `fable_review_identity_c11_findings.csv` (findings: id, severity, statement, evidence, requested action)
