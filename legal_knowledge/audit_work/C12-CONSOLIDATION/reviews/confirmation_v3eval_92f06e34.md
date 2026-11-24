# Confirmation of review_v3_holdout_eval F01 and F02 in commit 92f06e34 (c12w)

Reviewer: the same independent reviewer. I worked read-only: no commits, and every experiment ran in scratchpad/rev_v3eval/.

**Checks run**
- `eval_v3_holdout_c12.py --check` at 92f06e34 prints "evaluation reproduces".
- The headline figures are unchanged: 126/138 and 108/113, with 35 unmatched and 11 extra.
- The diff from cade4c99 touches only the post-hoc sections of the tool, plus the results files and the review copies. PROTOCOL.md and the ground truth are untouched.

## F01 (P2): V3's strict lead over V2 is a vocabulary artifact. Verdict: CLOSED_VERIFIED

- The tool now derives V2's vocabulary from V2's outputs. The derived set equals `OUTCOME_VOCAB` in v2core.py, minus `OUTCOME_UNVERIFIED`.
- The restricted comparison gives V3 105/115 = 91.3% and V2 105/115 = 91.3%, each with 136 scorable judgments. This is identical to my independent figure.
- RESULTS.md states plainly that V3's strict lead comes from labels V2 cannot express.
- Residual (INFO): the cade4c99 commit message still quotes "90.1% vs 86.8%". Commit history cannot be edited, so no action is needed. Downstream summaries should cite the qualified figure.

## F02 (P2): population-weighted precision missing. Verdict: PARTIAL

- I reproduced the court-weighted figures independently:
  - printed: precision 0.8929, coverage 0.8482
  - substantive: precision 0.9476, coverage 0.6586 (the tool reports 0.6587; this is rounding)
- **Gap 1 (main).** The holdout was sampled by court × stratum (holdout_v3_sample_c12.py). Within each court, fixed stratum shares were used: batch_or_multi 30%, disagreement 25%, pension_or_disciplinary 25%, other about 20%. Weighting by court alone corrects the court quotas but not the stratum over-sampling, and that over-sampling is the main departure from the population. A population-weighted estimate needs court × stratum cell weights.
  - The population cell counts can be derived from the sampler's own inputs. The cells are small (5 to 13 judgments), so the result should be presented as indicative.
- **Gap 2 (minor).** Precision is weighted by court share alone. Population precision should weight each court by its share times its coverage, which is the answered mass. With that weighting, I get printed 88.7% and substantive 94.5%. The effect is small.
- **Requested action:** add court × stratum weighting (cell share × coverage for precision), or record in RESULTS.md that the weighting covers court only and that stratum over-sampling is not corrected.
- Neither gap changes the conclusion that the targets are not met.
