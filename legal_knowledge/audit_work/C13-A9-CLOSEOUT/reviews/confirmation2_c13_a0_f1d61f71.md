# C13-A0 GA0 review: confirmation 2 (C01 fix at f1d61f71) (copy)

> **Copy note (C13-A9).** The "Confirmation 2" section of the reviewer's original `scratchpad/c13/reviews/a0/review_c13_a0_5e07e010.md`, copied without changes. The committed copy in `C13-A0-EVAL/reviews/` is a redacted earlier version without this section. This section quotes no judgment text.

## Confirmation 2: C01 fix at `f1d61f71` (2026-11-25)

- **Scope:** read-only, on a scratch export at `reviews/a0/src3`. The mutation tests ran in a separate copy, `src3_mut`. I made no commits.
- **Result: C01 CLOSED. GA0 ACCEPTED** for freezing A2, A3 and A5. There is no open P1 or P2. Three new P3s are listed at the end of this section.

### 1. No holdout text in the tree

- The text-bearing scratch (`reviews/frame_sample/*.txt`, `party_ppv.txt`, leak CSVs and other scratch) is `git rm`-ed. `reviews/` now holds only the review, findings and confirmation documents.
- It is still in history at `a4865e76` and `06340486`, with no rewrite; this is disclosed in `EXPOSURE_REGISTER.md`.
- I scanned all 69 files the A0 branch adds or modifies against `a4c0c382`. For each file I built **every** (unsampled) 8-word shingle and compared it with the 455 holdout representative texts, after removing shingles found in 3 or more corpus judgments. **No file shares 3 or more distinctive shingles with any holdout.**
- I also took 264 exact 80-character snippets from my own retained scratch excerpts (the 18 judgments) and searched for them in the committed files: **0 found**.

### 2. Pre-exposed subset and binding rule

`PRE_EXPOSED_SUBSET.csv` has 68 judgments:

| Category | Judgments |
| --- | --- |
| REVIEW_TEXT_EXPOSED | 19 (my 18 plus 1 sibling-text case found by the guard) |
| AUTHOR_DEV_SNIPPET_VIEWED | 10 (author's own disclosure; 6 overlap) |
| CURATED_KB_CONTENT | 4 |
| NEAR_IDENTICAL_SPENT_SIBLING | 16 |
| CASE_NUMBER_REVIEWED | 27 |

- All 18 of my judgments are present with `primary_sensitivity=true`, and so are the 4 from F04.
- PROTOCOL_C13 s.4.4 and s.6 make the rule **binding**: "A pass must hold without it", and the headline is the worse of the two statuses.
- `c13_score.run` computes `headline_status = _worse(full, without_PRIMARY)`.
- `main()` always loads the subset. Without it the harness reports `INCOMPLETE` and gives no pass.
- The reserve decision wording is corrected. The decision itself is unchanged.

### 3. Mutation check of the leak guard (scratch copy)

| Planted item | Guard hits (threshold 5) | Detected? |
| --- | --- | --- |
| 600-character H-OUT disposal excerpt | 17 | Yes |
| 600-character H-HOLD reserve disposal | 8 | Yes |
| 40-word quote, upper-cased, double spaces | 2 | **No** |
| 20-word quote | 0 | **No** |
| Generic non-holdout document | 0 | Correctly passes |
| 600-character excerpt in `tests/` | 17 when given explicitly | Not scanned by default |

- On the mutated copy, `c13_check_all` reports `leak guard scan: FAILED … CHECK FAILED`.
- On the mutated copy, `test_no_holdout_text_under_c13_a0_eval` fails.
- On the clean copy, `c13_check_all` reports ALL CHECKS OK and `leak guard scan: OK`.

### 4. Draw unchanged

These files are byte-identical to `06340486`, and therefore to the registration at `5e07e010`:
- the H-OUT, H-REL and H-HOLD `SAMPLE.csv` files, `RESERVE.csv`, the `DESIGN.json` files and the item maps;
- `HOLDOUT_REGISTRATION.json`;
- the frame and the exclusions;
- all six coder sheets.

There is no redraw. The only additions are the documented ones: exposure register, leak guard, fingerprint and pre-exposed rows.

### 5. Tests

- **80 passed, 1 skipped.** The C13 suite, including the leak-guard test, plus C12 research isolation.
- The skipped test needs commit `a4865e76`, which is not in my `git archive` export.

### New P3s

- **L01 (P3), guard sensitivity:** quotes of up to about 40 words are not detected (0 and 2 hits against a threshold of 5). A typical disposal sentence is that length, but the docstring says about 16 words are enough. **Requested action:** correct the docstring to say reliable detection needs about 50 words or more; consider MIN_HITS=3 or a denser sample.
- **L02 (P3), guard scope:** the default scan covers `C13-A0-EVAL/` only. **Requested action:** before each freeze, scan every file the A2, A3 and A5 branches add.
- **L03 (P3), membership oracle:** the fingerprint lets anyone test whether a text is a holdout judgment. This adds nothing new, because `SAMPLE.csv` already names the holdouts in the repo. **Requested action:** none needed; note it in the register.
