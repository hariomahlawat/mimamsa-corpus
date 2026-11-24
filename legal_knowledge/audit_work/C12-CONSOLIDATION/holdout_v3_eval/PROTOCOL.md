# V3 outcome extractor: holdout evaluation protocol (pre-registered)

The coordinator wrote and committed this protocol and `tools/eval_v3_holdout_c12.py` **before** the V3 extractor was frozen and before any V3 holdout prediction was scored. The coordinator is not the extractor's author. Before the freeze the coordinator saw only the label marginals of interim V3 output on holdout ids (a format check). No holdout information was passed to the extractor agent.

## Inputs
- Ground truth: `holdout_v3/GROUND_TRUTH_V3.csv`. It has 215 proceeding rows in 150 judgments, double-coded, with 16 judgments adjudicated (see `holdout_v3/PROCESS_NOTE.md`).
- V3 predictions: `extractor_v3/outputs/OUTCOMES_V3.csv` at the frozen hash recorded in the results. Rows are restricted to the 150 holdout judgment ids.
- Comparators: V2 = `C11-JUDICIAL-QUALITY/extraction/outputs/OUTCOMES_V2.csv` (frozen in C11). The crawler figures use the `crawler_outcome` column of the same V2 file.

## Proceeding matching (V3)
- Case numbers are normalised to `number-year` keys with the same regex as `tools/holdout_v3_agreement_c12.py`.
- A judgment with one ground-truth row and one V3 row matches directly.
- Otherwise each ground-truth row matches the V3 row with the same key. A ground-truth row coded `ALL` matches a single V3 row if V3 produced exactly one.
- A ground-truth row with no matching V3 row is **UNMATCHED**: it counts against coverage and is reported as a proceeding-mapping failure.
- A V3 row that matches no ground-truth row is **EXTRA** and is reported (over-splitting or wrong proceeding).

## Scoring per field (`printed_disposal`, `substantive_result`)
- A ground-truth label of `unclear` or `other` is **not scorable** for that field. The count is reported.
- A V3 value of `OUTCOME_UNVERIFIED`, a blank value, or an UNMATCHED row counts as **abstained**.
- **Strict precision** = exact label equal ÷ answered scorable rows.
- **Coverage** = answered scorable rows ÷ scorable rows.
- **Family precision** is reported secondarily. Families:
  - ALLOWED = allowed
  - PARTLY = partly_allowed
  - DISMISSED = dismissed, dismissed_as_withdrawn, dismissed_as_infructuous, dismissed_in_default
  - DISPOSED = disposed_of, disposed_of_with_directions, disposed
  - REMANDED = remanded, set_aside_and_remanded
  - TRANSFERRED = transferred
  - The substantive label is its own family.
- **Targets (directive):** strict precision ≥ 95% and coverage ≥ 85%, for each field separately.
- **Intervals:** Wilson 95% intervals. A judgment-cluster bootstrap (2,000 resamples, seed `c12-v3-eval`) is also given, because rows within a judgment are not independent.

## Breakdowns
- By court and by stratum, using `HOLDOUT_V3_SAMPLE.csv`.
- By ground-truth source: BOTH_CODERS_AGREE vs ADJUDICATED.
- Every error and abstention is listed in `ERRORS.csv`, with a failure category assigned by rule:
  - `PROCEEDING_UNMATCHED`
  - `ABSTAINED`
  - `WRONG_LABEL_SAME_FAMILY`
  - `WRONG_FAMILY`
- Hard cases are not removed.

## Traceability
For each answered V3 row, the tool checks that `excerpt` occurs in the cited text blob (`text_source`, read from `/home/user/c7`) and that `page` is consistent with the page marker preceding `char_start`. It reports the rate.

## Comparison with V2 and the crawler (judgment level, printed field only)
V2 and the crawler give one outcome per judgment and have no substantive field.
- The ground-truth judgment label is the unique `printed_disposal` across that judgment's rows, or `MIXED`.
- Each method's judgment label is its single value. For V3 it is the unique value across V3 rows, or `MIXED`.
- `MIXED` ground truth is not scorable at judgment level.
- V2 is scored strict and by family. The crawler is scored by family only, because its vocabulary differs.
- All three methods are scored on the same judgments.

## Status
All V3 outputs remain `AUTOMATED_CANDIDATE_NOT_VERIFIED`. Meeting a target is a technical measurement, not legal validation.
