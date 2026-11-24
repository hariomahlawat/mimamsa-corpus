# V3 holdout: process note and corrections (Cycle 12)

This note corrects earlier wording. It responds to independent review C12-tools F04 and its confirmation (`reviews/review_c12_coordinator_tools_25723740.md`, confirmation record of 43190971).

## Who coded what

| Role | Who | What it was shown | How separation was achieved |
| --- | --- | --- | --- |
| Coder A, coder B (segments 1–3) | Separate AI agent instances, one per coder and segment | The sample rows, `CODING_CONVENTION.md` and the judgment text | Each coder's instructions named only its own output file and forbade reading the other coder's files. **No technical isolation was enforced** (shared file system), and no access log exists. "Blind to each other" therefore rests on instructions, not on verifiable controls. |
| Adjudicator, original 14 judgments | A third AI agent instance, independent of both coders and of the extractor | Both codings **labelled A and B**, plus the judgment text | Not blind to the competing codings or to coder identity. The reasons in `ADJUDICATION.csv` refer to A and B. |
| Adjudicator, V3H015 and V3H017 (added after review F02) | A further AI agent instance | Both codings **anonymised as X and Y**, plus the judgment text | The coordinator held the X/Y → B/A mapping outside the adjudicator's working directory and applied it afterwards; this is recorded in each row's reason. |

## Corrections

- Commit `ed5362e5` and the original docstring of `tools/holdout_v3_truth_c12.py` described the adjudicator as a "blind third coder". That is inaccurate. The adjudicator was independent, but it saw the competing codings. The docstring was corrected in `499b89ac`; this note records the correction in the holdout folder. Git history keeps the original wording.
- The figure of 136/150 agreed judgments used a lenient comparison: label sets and row count only. Under the strict proceeding-level comparison, **134/150** agree (`AGREEMENT_SUMMARY.json`). `GROUND_TRUTH_V3.csv` covers all 150 judgments in 215 rows. Of these, 46 rows (from 16 judgments) come from adjudication; the rest are rows on which both coders agreed under the strict comparison.

## Limits

All coders and adjudicators were AI agents. The ground truth is a technical reference for measuring the extractor. It is not a legal determination of any outcome.
