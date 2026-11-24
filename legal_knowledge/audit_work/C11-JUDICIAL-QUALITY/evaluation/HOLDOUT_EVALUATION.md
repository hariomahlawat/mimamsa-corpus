# Blinded holdout evaluation of the outcome extractor `c11-extract-v2/1.0.0`

**Verdict: below the promotion bar. Outcome fields remain `AUTOMATED_CANDIDATE_NOT_VERIFIED`.** The bar was at least 95% precision on independently reviewed, representative outcomes.

## Design
- **Holdout:** 56 judgments, drawn deterministically and stratified by court (SC 20, Delhi 8, P&H 10, J&K 9, Allahabad 9) and by stratum (crawler/extractor disagreement 18, multi-case 16, other 22). The 50 judgments reviewed in Cycle 10, which were the development set, are excluded (`tools/holdout_sample_c11.py`).
  - Delhi has no disagreement-stratum records, because its crawler metadata carries no outcome. Its quota therefore fell to 8.
- **Ground truth:** two independent Fable 5.2 (claude-fable-5-2) reviewers read the PDFs blind. They saw no extractor code or output, and recorded one row per proceeding: 120 proceeding rows, every SHA-256 verified (`holdout/ground_truth_A.csv`, `ground_truth_B.csv`).
- **Blinding:** the extractor was frozen (tool hashes `3b48c768…`, `7311513f…`) before any holdout prediction was made. Its developer never opened the holdout folder.
- **Predictions:** `evaluation/holdout_predictions/OUTCOMES_V2.csv` (command in the file header of `tools/eval_holdout_c11.py`).
- **Scoring rules** are fixed in `tools/eval_holdout_c11.py` (`--check` reproduces). The unit is the judgment. A single outcome given for proceedings that were decided differently is INCORRECT_MIXED.
- **Scorer corrections:** the scoring rules were corrected twice while scoring, and both changes are recorded here:
  1. A case-number format bug (hyphens and ranges) wrongly failed three correct predictions.
  2. A leniency bug counted a one-row prediction over 45 differently decided proceedings (H042) as correct. It is now INCORRECT_MIXED.

## Results
| Measure | Value |
| --- | --- |
| Judgments | 56 |
| Abstained (OUTCOME_UNVERIFIED) | 11 (coverage 80.4%) |
| Ground truth not scorable ('other') | 1 |
| **Precision, strict** | **37 / 44 = 84.1% (one-sided 95% lower bound 73.1%)** |
| Precision, lenient (remanded = set aside and remanded) | 37 / 44 (no change) |
| Baseline: crawler outcome, same rules (exact label; family scoring under Qualifications; *note added in Cycle 12*) | 28 / 44 = 63.6% (lower bound 51.2%) |
| Baseline: Cycle 10 extractor, same rules (exact label; family scoring under Qualifications; *note added in Cycle 12*) | 25 / 48 = 52.1% (lower bound 40.4%) |

**By court (strict):**

| Court | Correct | Coverage |
| --- | --- | --- |
| Allahabad | 7/7 | 78% |
| J&K | 7/8 | 89% |
| P&H | 8/8 | 80% |
| Supreme Court | 11/14 | 75% |
| Delhi | 4/7 | 88% |

## The seven errors
| Holdout | Ground truth | Predicted | Cause |
| --- | --- | --- | --- |
| H010 (SC) | three appeals: allowed / dismissed / set aside and remanded | one outcome, disposed of with directions | multi-proceeding judgment not split |
| H012 (SC) | seven appeals partly allowed; one SLP not final | one appeal, not final | wrong proceeding mapping |
| H042 (J&K) | 45 petitions, each disposed separately (40 dismissed, 3 allowed, 1 partly allowed, 1 other) | one row, one outcome | per-petition sections not split |
| H011 (SC) | partly allowed (reinstatement set aside, dismissal reduced to discharge) | allowed | modified relief read as full relief |
| H021, H026, H027 (Delhi) | allowed / dismissed as withdrawn / set aside and remanded, **coded on substance** | disposed of with directions | **labelling convention**: the order prints "disposed of" |

## What this means
- **The automated outcome is not reliable enough** for unreviewed use. That is especially true for multi-proceeding Supreme Court and batch judgments.
- **Even on the extractor's own labelling convention** (the literal operative phrase), precision would be 40/44 = 90.9%, still below the bar.
- ~~v2 is substantially better than both baselines~~ *(corrected in Cycle 12 after confirmation review of C11 F04)*: by outcome family on identical ground truth, v2 scored 38/44 (86.4%) against 33/44 (75.0%) for the crawler and 31/48 (64.6%) for the Cycle 10 extractor; the 95% intervals overlap, so the margin is not established as large on this sample. The 627 corpus-wide abstentions and every multi-proceeding judgment should go to human review first.
- **A proposed v3 needs two things:**
  - splitting batch judgments into per-proceeding sections (H042 pattern) and mapping multi-appeal operative paragraphs (H010, H012);
  - an explicit two-field outcome: `printed_disposal` (literal) and `substantive_result` (requires reading).

  It must then be measured on a **new** holdout. This holdout is now spent for tuning purposes.

## Independent review of this evaluation (Fable 5.2, `review/fable_review_extraction_c11.md`)
The reviewer re-scored all 56 judgments independently: 37 correct, 7 incorrect, 11 abstained, 1 not scorable. **84.1% is arithmetically correct** (two-sided 95% interval 70.6% to 92.1%). All 7 errors and a sample of 10 correct rows were confirmed against the source, and all 11 abstentions are genuine.

**Qualifications to the headline:**
- **Single-coded ground truth (F02).** Reviewer A coded H001–H028 and reviewer B coded H029–H056, with no overlap. A coded the substance of the outcome; B coded the printed words. Inter-rater agreement is therefore unknown. **A future holdout must be double-coded under one written convention.**
- **Unweighted headline (F03).** The Supreme Court is 36% of the sample but 8% of the corpus, and Delhi is 14% of the sample but 42%. Population-weighted precision is about **79%**; the cells are small, so this is indicative only.
- **Baselines (F04).** The exact-label rule disadvantages the crawler, whose vocabulary has no `disposed_of_with_directions` or `transferred`. Scored by outcome family instead:

  | Method | Correct | Precision |
  | --- | --- | --- |
  | v2 | 38/44 | 86.4% (Wilson 95% 73.3–93.6%) |
  | crawler | 33/44 | 75.0% (Wilson 95% 60.6–85.4%) |
  | Cycle 10 extractor | 31/48 | 64.6% (Wilson 95% 50.4–76.6%) |

  **The intervals overlap**, so ~~v2's advantage is real but not large on this sample~~ v2 has the higher point estimate, but its advantage is not established on this sample *(corrected in Cycle 12, review R50-07)*.
