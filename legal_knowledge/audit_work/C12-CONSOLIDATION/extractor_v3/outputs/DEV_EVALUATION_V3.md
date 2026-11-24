# Development evaluation: `c12-extract-v3/1.0.0`, with frozen v2 on the same rows

**Read this first: these results are IN-SAMPLE.** Every judgment in the development gold was available to the v3 developer, and v3 rules were written while looking at them:
- the C10 review sets;
- the spent C11 holdout and its ground truth;
- the C11 reviewer's 30 disagreement items.

The 100% development precision below **does not estimate** blind precision. Only the fresh, double-coded `holdout_v3`, which this workstream never opened, can measure that.

The two developer spot checks outside the development set (section 5) are small and read by the developer. The first of them was used to change rules.

Reproduce: `python3.11 -I -B tools/eval_dev_v3.py --write`. This writes `DEV_EVALUATION_V3_ROWS.csv`, `DEV_EVALUATION_V3_SUMMARY.json` and `DEV_BATCH_COPIES_V3.csv`.

## 1. Development gold (`tools/dev_gold_v3.json`, built by `tools/build_dev_gold_v3.py`)

| Set | Judgments | Source | Gold per proceeding |
| --- | --- | --- | --- |
| C10 | 50 | C10 `review_A/B.csv` and `WS_REVIEW_SAMPLE20`, mapped in C11 `dev_gold.json` | 6 mixed judgments carry per-proceeding gold; the rest are judgment-level |
| C11H | 56 | spent C11 holdout, `ground_truth_A/B.csv` (120 proceeding rows) | one row per proceeding |
| C11R | 30 | C11 reviewer's confirmed printed dispositions (section 4 items) | judgment-level |

- The C11 ground truth has one label per proceeding. Reviewer A coded substance and reviewer B coded printed words.
- This workstream split each label into a `printed` value and a `subst` value from the reviewers' excerpts and notes. The basis is recorded per row, for example:
  - H021 printed `disposed_of_with_directions`, substance `relief_granted`;
  - H048 printed `allowed`, substance `remanded_for_fresh_decision`;
  - H042 WP(C) 2301/2024: no disposal word printed, so printed is not scored; substance is `relief_granted` or `remanded_for_fresh_decision`.
- Ambiguous readings accept every defensible label. For example, H010 accepts the closing words `disposed_of` for all three appeals.
- Undeterminable fields are not scored. **This split is itself a development-side reading. It is not independent ground truth.**

**Scoring** (unit: the judgment, per field):
- CORRECT: every non-abstained row maps to gold proceeding(s) and carries an accepted label.
- WRONG: any non-abstained row carries an unaccepted label, or names a proceeding that is not in the gold. The second case is strict.
- ABSTAIN: every row of the field is `OUTCOME_UNVERIFIED`.

Two further measures:
- **Pair** is correct when no field is wrong and at least one is correct.
- **Proceeding completeness** is the share of gold proceedings covered by a non-abstained row, over predicted judgments.

**How v2 is scored:**
- v2 has one label. It is scored as `printed_disposal` as-is.
- For `substantive_result`, v2's label goes through the default mapping. `disposed_of_with_directions` then has no substance and counts as an abstention.
- A v2 row that is not per-proceeding counts as covering all proceedings. This is lenient to v2, and is why v2 completeness is near 1.0.

## 2. Results (in-sample)

| Set | Field | v3 correct / wrong / abstain | v3 precision | v3 coverage | v2 correct / wrong / abstain | v2 precision | v2 coverage |
| --- | --- | --- | --- | --- | --- | --- | --- |
| All 136 | printed | 121 / 0 / 14 | 100% | 89.6% | 112 / 5 / 18 | 95.7% | 86.7% |
| All 136 | substantive | 114 / 0 / 15 | 100% | 88.4% | 100 / 5 / 24 | 95.2% | 81.4% |
| All 136 | pair | 123 / 0 / 13 | 100% | 90.4% | 111 / 6 / 19 | 94.9% | 86.0% |
| C11H (56) | printed | 50 / 0 / 5 | 100% | 90.9% | 41 / 4 / 10 | 91.1% | 81.8% |
| C11H (56) | substantive | 46 / 0 / 8 | 100% | 85.2% | 33 / 4 / 17 | 89.2% | 68.5% |
| C10 (50) | printed | 41 / 0 / 9 | 100% | 82.0% | 41 / 1 / 8 | 97.6% | 84.0% |
| C11R (30) | printed | 30 / 0 / 0 | 100% | 100% | 30 / 0 / 0 | 100% | 100% |

- **Proceeding completeness (v3):** printed 97.8% and substantive 97.7% of gold proceedings in predicted judgments. For C11H it is 96.4%.
- **Not scorable:** 1 judgment for printed, 7 for substantive.
- **Batch copies.** The 36 stored copies of the two C11 multi-petition batch texts in the gold were scored on each copy's own petition (`OWN_CASE` row against that petition's gold, `DEV_BATCH_COPIES_V3.csv`): **33 correct, 0 wrong, 3 abstain.** v2 gave every copy the batch's last printed disposal (C11 finding F01).
- **Coverage loss against v2:** one judgment, J-dc60fe00. It prints no disposal word ("impugned order quashed; OA infructuous"), so v3 abstains on `printed_disposal` but gives `relief_granted`.

## 3. Per-error analysis: v2 errors on these rows and what v3 does

| Judgment | v2 (wrong) | Cause in v2 | v3 |
| --- | --- | --- | --- |
| H042 J&K batch (45 petitions; copy J-a09b2abf) | one row `dismissed` for all | per-petition sections not split | 45 sections split by heading. 43 decided and all correct against GT, including 1319, 1708 and 1007 `allowed` and 1653 `partly_allowed`. 2301 has printed abstained with substance `relief_granted`. 1694 abstains (quote pairing). |
| H012 SC J-81a996f5 | `not_final` for all | "List ... separately" plus an unparsed "allow the present appeals to the above limited extent" split by "GP." | 7 CAs `partly_allowed`. SLP(C) 16441 is not given the appeals' outcome (the generic is restricted to appeals) and abstains. |
| H011 SC J-d29ce9d4 | `allowed` | intransitive "partly succeeds" | `partly_allowed` / `relief_partly_granted` |
| H010 SC J-625ab315 | `disposed_of_with_directions`, one row | party-specific outcomes per appeal not mapped | **Not solved.** Rows for CA 127, 128 and 606 carry the literal closing `disposed_of`, with substance abstained. Counted correct only because the gold accepts the closing words. |
| H048 Allahabad | substance (naive) `relief_granted` | remand plus "allowed" | `allowed` / `remanded_for_fresh_decision` |
| J-a8793e00 SC (C10 mixed) | per-party rows with swapped labels | Diary-number mapping | abstains (`DISPOSITION_NAMES_NON_HOST_CASE_NUMBER`) |

**New coverage over v2 on these rows**, all correct in-sample:

| Judgment | What v3 now reads |
| --- | --- |
| H002 | "allow the appeal, set aside ..., and dismiss the writ petition" |
| H006 | "will stand dismissed" |
| H014 and J-b159ba17 | "allowed to the above extent" |
| H034 | court sentence after a closing quote |
| H049 | "consigned to records" |
| H007 | substance only, from the set-aside of the Tribunal's order |

**Remaining development abstentions (14 printed), all honest:**

| Reason | Judgments |
| --- | --- |
| No text file at the commit | 2 |
| Garbled text layer | H031 |
| Separate concurring opinion last | H018 |
| Composite or carve-out SC dispositions | J-3a4ed1ab, J-76a1a41c |
| Unparsed forms | "transmitted" after "but" (H055); nominal "prayer is for transfer ... Ordered accordingly" (H047); "we do not deem it ... and dismiss" (J-8a2bafba) |
| No disposal phrase | J-eb24633d, J-db5d2083, H024, J-dc60fe00 |
| Diary-number mapping | J-a8793e00 |

## 4. Corpus run (3,936 judgments, 13,553 proceeding rows)

Coverage below is per judgment, on the copy's `OWN_CASE` row where one exists.

| Court | Judgments | printed decided | substantive decided | v2 non-abstained (for reference) |
| --- | --- | --- | --- | --- |
| Allahabad | 309 | 273 (88.3%) | 232 (75.1%) | 240 (77.7%) |
| Delhi | 1,659 | 1,451 (87.5%) | 1,145 (69.0%) | 1,452 (87.5%) |
| J&K | 410 | 328 (80.0%) | 278 (67.8%) | 342 (83.4%) |
| P&H | 1,208 | 1,042 (86.3%) | 898 (74.3%) | 1,015 (84.0%) |
| Supreme Court | 346 | 264 (76.3%) | 236 (68.2%) | 260 (75.1%) |
| No metadata | 4 | 0 | 0 | 0 |
| **All** | **3,936** | **3,358 (85.3%)** | **2,789 (70.9%)** | 3,309 (84.1%) |

- **Multi-row judgments:** 550 judgments have more than one proceeding row.
- **Shared batch texts:** 62 text blobs are shared by 292 judgment_ids. 219 of their 291 own-case rows are decided, each from that copy's own proceeding.
- **J&K coverage is below v2's.** v2's J&K figure included the replicated batch outcome; v3 abstains instead of copying it.

**Label counts (rows):**

| `printed_disposal` | Rows | `substantive_result` | Rows |
| --- | --- | --- | --- |
| dismissed | 4,215 | relief_refused | 4,215 |
| disposed_of_with_directions | 3,113 | relief_granted | 1,489 |
| partly_allowed | 778 | relief_partly_granted | 775 |
| allowed | 756 | no_adjudication | 609 |
| disposed_of | 286 | interim_only | 52 |
| transferred | 241 | remanded_for_fresh_decision | 49 |
| dismissed_as_withdrawn | 163 | | |
| not_final | 52 | | |
| set_aside_and_remanded | 12 | | |
| remanded | 9 | | |
| dismissed_in_default | 8 | | |
| dismissed_as_infructuous | 3 | | |
| OUTCOME_UNVERIFIED | 3,917 | OUTCOME_UNVERIFIED | 6,364 |

## 5. Developer spot checks outside the development set (`DEV_SPOTCHECK_V3.csv`)

- **Sample:** 30 judgments per check, drawn by the lowest sha256(salt + judgment_id), one per distinct text, excluding all development judgments.
- **Method:** the developer read each copy's own row(s) against the final part of the text layer. This is an AI developer reading, not legal validation and not independent.
- **Overlap risk:** these judgments may overlap `holdout_v3`. Its ids are unknown to this workstream.

| Check | When | Used to change rules? | printed: decided / OK / debatable / error | substantive: decided / OK / debatable / error |
| --- | --- | --- | --- | --- |
| A (salt C12-SPOT) | before the first freeze | yes: dismissed-for-non-prosecution OCR tolerance; partly allowed plus remit | 22 / 21 / 0 / 1 | 19 / 17 / 1 / 1 |
| B (C12-SPOT-B) | after a first freeze | **yes**: "petition and all pending applications"; directions detection; withdrawal with modification | 27 / 24 / 2 / 1 (88.9% strict) | 24 / 22 / 0 / 2 (91.7%) |
| C (C12-SPOT-C) | **after the final freeze**, on the frozen `v3core.py` | no | 26 / 25 / 1 / 0 (96.2% strict, Wilson 95% 81.1% to 99.3%) | 24 / 22 / 2 / 0 (91.7% strict, 74.2% to 97.7%) |

Spot C coverage is 26/30 printed and 24/30 substantive.

**The debatable items are convention questions.** They count as errors in the strict figures:
- "disposed of as not pressed" was read as `dismissed_as_withdrawn`;
- `relief_granted` against `remanded_for_fresh_decision` where an AFT order is set aside and an authority must re-examine;
- `relief_partly_granted` against remand for a partly allowed appeal whose sentence is remitted to the Court Martial.

## 6. Honest expectation for the blind evaluation

**`printed_disposal`:**
- Strict precision around or somewhat below 95% is plausible. The likely failure modes are convention mismatches (`disposed_of` against `disposed_of_with_directions`; extent-qualified allowance; "not pressed") and Supreme Court multi-appeal or party-specific judgments.
- Judgment coverage should be near 85% for the High Courts and lower for the Supreme Court.

**`substantive_result`:**
- Expect lower precision, likely around 90%. Its errors concentrate in "disposed of with directions" orders, where relief granted, remand to an authority and no adjudication blur.
- Expect lower coverage, about 70%.

**Do not suppress hard cases to reach precision.** v3 abstains only where the text does not determine the field.
