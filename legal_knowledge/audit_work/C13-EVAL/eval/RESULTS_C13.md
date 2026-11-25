# RESULTS_C13: GA4 independent evaluation of Outcome V4 (A2), Holdings (A3) and relations (A5)

- **Evaluator:** the C13 GA4 evaluator, an AI agent instance. It wrote no extractor, did no coding and did no adjudication of the reference sets. It is not a human and not a legal reviewer.
- **Date:** 2026-11-25.
- **Protocol:** `PROTOCOL_C13.md` v1.1 at `claude/c13-a0-eval` `f1d61f71` (sha256 `9d6f04ed…`).
- **Status of every figure:** `AUTOMATED_CANDIDATE_NOT_VERIFIED`. The figures are scored against AI-coded reference sets. Two separate agent instances coded each holdout and a third adjudicated it. No human annotator took part.
- **Independent review:** `reviews/eval/REVIEW_GA4.md`, verdict ACCEPT WITH CONDITIONS. The reproduction matched byte for byte. This revision addresses F1–F9 (section 10). No number was changed; only disclosures, intervals and status labels were added or corrected.
- **Changes made:** no branch, prediction, truth or protocol file was changed. Nothing was committed and nothing was written to HF.
- **Outputs:** everything is in `scratchpad/c13/eval/`.

## 1. Headline (pre-registered rule, PROTOCOL s.6)

### 1.1 How to read the tables

- **w:** the weighted Horvitz–Thompson point estimate.
- **CP95:** the validated design-effect Clopper–Pearson 95% interval (the interval the met rule uses).
- **unw:** the unweighted pooled proportion, with its counts.
- **Status:** the harness `headline_status`. It is the worse of the full-sample status and the status without the PRIMARY pre-exposed subset.
- **Statuses (s.6.4):** `MET_LOWER_BOUND` (weighted and unweighted points and the validated lower bound reach the target), `MET_POINT_ONLY` (both points reach it, the lower bound does not), `NOT_MET`. The protocol defines no "PASS"; whether `MET_POINT_ONLY` is enough for candidate display is an owner decision. No headline cell reaches either met status, so that decision does not arise for the headline. Some per-court breakdown cells are `MET_POINT_ONLY` (section 4.1).

### 1.2 Outcome V4 (A2), H-OUT-C13

| Field | Metric (target) | w | CP95 | unw (k/n) | Without PRIMARY: w [CP95] | Status | Target met? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| printed_disposal | strict precision (≥ 0.95) | 0.898 | [0.838, 0.941] | 0.825 (254/308) | 0.889 [0.824, 0.936] | NOT_MET | no |
| printed_disposal | coverage (≥ 0.85) | 0.833 | [0.743, 0.902] | 0.623 (283/454) | 0.826 [0.727, 0.901] | NOT_MET | no |
| substantive_result | strict precision (≥ 0.95) | 0.882 | [0.815, 0.932] | 0.831 (221/266) | 0.880 [0.809, 0.932] | NOT_MET | no |
| substantive_result | coverage (≥ 0.85) | 0.760 | [0.671, 0.835] | 0.577 (252/437) | 0.751 [0.653, 0.832] | NOT_MET | no |

### 1.3 Holdings (A3), H-HOLD-C13: NOT SCORABLE UNDER PROTOCOL v1.1

**No protocol status.** Protocol s.4 item 6 says that if span F1 between annotators is below 0.6, the guideline is revised and re-annotated **before scoring**. It has no exception. Measured span F1 is 0.566, and no revision or re-annotation took place. A second precondition also failed (PD-01: annotation began without a substantive guideline). H-HOLD therefore has **no pre-registered result in C13**.

**Re-annotation is required.** A scorable H-HOLD needs a substantive holdings guideline, written independently of A3 and committed with a version and sha256, and two fresh coders re-annotating under it, all before the next A3 freeze (D-12).

The figures below are **DESCRIPTIVE ONLY, obtained under a protocol deviation (not a protocol result)**. They carry no PASS, FAIL or met status. The numbers are unchanged from the first version of this report. Most of the gold holdings (113 of 183) are a single AI adjudicator's own coding (D-2).

| Metric (owner milestone, for context only) | w | CP95 | unw (k/n) | Without PRIMARY: w [CP95] | Status |
| --- | --- | --- | --- | --- | --- |
| holding precision, adjudicated (blind, seeded sample of 100; milestone 0.80) | 0.365 | [0.241, 0.503] | 0.364 (36/99) | 0.365 [0.238, 0.508] | DESCRIPTIVE ONLY |
| holding recall (milestone 0.60) | 0.517 | [0.424, 0.608] | 0.492 (90/183) | 0.535 [0.439, 0.630] | DESCRIPTIVE ONLY |
| holding precision, reference-match (lower bound by construction) | 0.156 | [0.124, 0.192] | 0.157 (90/574) | 0.162 [0.129, 0.200] | DESCRIPTIVE ONLY |

- **Precision.** Descriptively, adjudicated precision is far below 0.80; the upper end of its interval is 0.50. The GA4 reviewer's blind sub-adjudication of 25 of the 100 agreed on 21 (0.84, kappa 0.57) and would lower it slightly (section 4.2).
- **Recall** cannot be interpreted against 0.60, because it depends on how the gold is defined (section 5.1).

### 1.4 Relations (A5), H-REL-C13

The owner set no target, so these figures are descriptive (protocol s.1).

| Predicted type | Field | Precision w [CP95], unw (k/n) | Coverage of units of that predicted type |
| --- | --- | --- | --- |
| all | relation_type | 0.340 [0.161, 0.560], 0.330 (58/176) | overall coverage w 0.260 [0.109, 0.471], unw 0.502 (159/317) |
| all | target | 0.620 [0.467, 0.758], 0.619 (109/176) | w 0.261 [0.109, 0.471], unw 0.500 (161/322) |
| `cites` (170 answered) | relation_type | 0.336 [0.156, 0.561], 0.312 (53/170) | — |
| `follows` (6 answered) | relation_type | 0.526 [0.061, 0.956], 0.833 (5/6). Only 6 units were predicted, so the interval is wide | — |

**Recall per gold type** (protocol s.1 and s.8). Descriptive. A unit counts as recalled when the predicted type equals the gold type. Uncodable items are excluded. Weighted recall uses the harness estimator (`eval/REVIEW_FIXES.json`, `scripts/review_fixes.py`). It is descriptive only: the Kish design effect is 7.5 and n_eff is small.

| Gold type | Gold units | Predicted `follows` | Predicted `cites` | No prediction | Recall unw (k/n) [Wilson 95] | Recall w [CP95] (n_eff) |
| --- | --- | --- | --- | --- | --- | --- |
| `follows` | 154 | 5 | 69 | 80 | 0.032 (5/154) [0.014, 0.074] | 0.004 [0.000, 0.204] (16.9) |
| `cites` | 105 | 1 | 53 | 51 | 0.505 (53/105) [0.411, 0.599] | 0.449 [0.136, 0.796] (8.7) |
| `applies` | 3 | 0 | 0 | 3 | 0.000 (0/3) [0.000, 0.562] | 0.000 [0.000, 0.832] (2.1) |
| `not_followed` | 2 | 0 | 0 | 2 | 0.000 (0/2) [0.000, 0.658] | 0.000 [0.000, 0.842] (2.0) |
| `distinguishes` (rare type under s.3: counts only) | 53 | 0 | 31 | 22 | 0/53 | — |

- `follows` and `cites` are the common types, not rare ones. The s.3 rare-type rule (counts only) covers `overrules` and `distinguishes`.
- No `overrules` was coded or predicted.
- **Why weighted and unweighted coverage differ** (0.26 against 0.50): the 20 NO_DETECTED_CITATION pages carry very large design weights. On those pages the extractor detects few of the citations the coders found, so the weighted figure is dominated by them, while the unweighted figure reflects the sample's composition. Weighted overall recall and coverage are descriptive only (s.3.1).

## 2. Inputs, hashes, ancestry and store

### 2.1 Reference sets

All three were verified, then rebuilt byte-identical with `c13_coding.py truth` from the coder sheets and the adjudication result.

| File | sha256 |
| --- | --- |
| coding/truth/H-OUT-C13.csv | `59847e945f928ab3aafa60369ecd53bcfbec66ae5f9d2add5ce6fd4c3ec257ee` |
| coding/truth/H-REL-C13.csv | `eef7b10487b2b5681ea2bb689f277f1ff5f6eb06dc176cea2c065ba673d875dd` |
| coding/truth/H-HOLD-C13.csv | `bb726f95e7e92b622486a838a1291ee076d075e99170b479c07e54f02006a701` |

**Coding inputs.**

| Holdout | coder_1 sheet | coder_2 sheet | Adjudication result |
| --- | --- | --- | --- |
| H-OUT | `afc74c9b…` | `c506078e…` | `d6396ef0…` |
| H-HOLD | `03fc6bfe…` | `15ce16ef…` | `d6dc91c7…` |
| H-REL | `32b4b75b…` | `a79d2105…` | `7290ea00…` |

- **Sealed AGREEMENT.json:** H-OUT `f5f32658…`, H-HOLD `436e9c6c…`, H-REL `b5233073…`. Each was re-computed byte-identical with `c13_coding.py agree`.
- **Leak checks:** `leakcheck --completed` passes on all 6 returned sheets. The sheets' `coder_id` column holds the slot names `coder_1` and `coder_2`, so the check passes with those ids. The instance ids are mapped in `ASSIGNMENT_LOG.md`.

### 2.2 Frozen predictions

In each case the file at the freeze commit (`git show <freeze>:<path>`) has the same sha256 as the working file.

| Extractor | Freeze commit | Predictions sha256 | `--is-ancestor f1d61f71` | `--is-ancestor d3a1bb0a` (registration added) | `--is-ancestor 5e07e010` (last registration change) |
| --- | --- | --- | --- | --- | --- |
| A2 Outcome V4 `c13-extract-v4/1.0.0` | `9cdd500812bf…` | `45c5a3321d22e2948e2783c2ba6a6857d51f1c705e7b90993ddc3a68ad239b69` | OK | OK | OK |
| A3 `c13-holdings/1.0.0` | `a520aa3a2217…` | `3894ecbfb3c3c6d0bae8ab275f905d0c812c2d018dd3b63fb3eeeb348758e164` | OK | OK | OK |
| A5 `treatment-c13/0.9.0-dev` | `e15af20848d1…` | `c53ea96a4c387d4d7d802d643e62b9fd3ee0b90d5ce3f8d98e5cb02640718bc3` | OK | OK | OK |

### 2.3 Harness and design files

All match A0 `SHA256SUMS`.

| File | sha256 prefix |
| --- | --- |
| `c13_score.py` | `3144aafc…` |
| `c13_coding.py` | `9ebf01f4…` |
| `c13_stats.py` | `36229c63…` |
| `c13_tasks.py` | `2c68665c…` |
| `c13_sensitivity.py` | `1dd92da5…` |
| `PRE_EXPOSED_SUBSET.csv` | `a7c71139…` |
| `HOLDOUT_REGISTRATION.json` | `f87364df…` |
| H-HOLD reserve decision | `593b485f…` (FULL_OPEN; the protocol's version-2 hash) |

### 2.4 Annotation store

- **Location:** `eval/store/`. Each holdout is stored as version `v001`, created 2026-11-25T19:47:08Z by `c13_coding.store_version`. `c13_coding.py verify eval/store` reports `store OK`.
- **Manifests:**
  - H-OUT `80492b8a…`: coder ids C13-COD-OUT-1, C13-COD-OUT-2, C13-ADJ-OUT.
  - H-HOLD `0906efbb…`: C13-COD-HOLD-1, C13-COD-HOLD-2, C13-ADJ-HOLD. The manifest note records PD-01.
  - H-REL `c675fd08…`: C13-COD-REL-1, C13-COD-REL-2, C13-ADJ-REL.

### 2.5 Pages file

- **File:** `eval/work/PAGES.jsonl`, sha256 `f77e88416fa38c7621cfa26ad2cdd2c8c90c045ac6fc6451339b180d508116c7`.
- **Content:** 455 distinct representative files, the union of the three designs. Each was sha256-verified against `rep_sha256` before use, with 0 missing and 0 mismatched.
- **Source of the files:** the sha-verified copies already fetched by the coders and adjudicators (from HF `5524c3d9`, or HF `main` for the store-pointer items). No new HF download was needed.
- **Text:** PyMuPDF 2.1 (MuPDF 1.28.6) text layer, pages numbered from 1.
- **FOUO:** the FOUO Air Force Regulations sha (`4284820e…`) is not among them.
- **Choice of text:** the anchor check uses this text layer, not the c7 `ad77758d` text the extractors read. A few `ANCHOR_NOT_FOUND` results may be text-layer differences.

## 3. Inter-coder agreement (before scoring; sealed AGREEMENT.json, re-computed identical)

| Holdout | Items AGREE | Strict item | Strict unit | Kappa incl. unmatched | Kappa matched | Krippendorff α | Span F1 | Uncodable (both / one coder) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| H-OUT | 251/300 | 0.837 | 0.793 | pd 0.808; sr 0.785 | pd 0.933; sr 0.912 | 0.933; 0.912 | — | 28 / 6 |
| H-HOLD | 34/113 | **0.301** | **0.450** | item_type −0.113; opinion −0.187 | 1.0; 1.0 | 1.0 | **0.566** | 21 / 3 |
| H-REL | 89/160 | 0.556 | 0.468 | relation_type 0.743; target 0.482 | 0.918; 0.557 | 0.918; 0.556 | — | 40 / 1 |

**H-HOLD span F1 is 0.566, below 0.6.** Protocol s.4 item 6 says: "if span F1 between annotators is below 0.6, the guideline is revised and re-annotated before scoring". That was not done. See D-7.

## 4. Detailed results

### 4.1 Outcome (A2): failure taxonomy, abstentions, uncodable, anchors

**Uncodable items.**
- 34 of 300 items (11.3%) are uncodable, all `OUT_OF_SCOPE`.
- They are excluded from the denominators and never replaced.
- The extractor made 115 prediction rows on them.

**Coverage counting each uncodable item as not covered.**
- printed_disposal: w 0.799 [0.713, 0.869], unw 0.580 (283/488).
- substantive_result: w 0.728 [0.643, 0.803].

**Gold units that are undeterminable:** printed_disposal 1, substantive_result 18.

**Failure categories (scored items).**

| Field | CORRECT | WRONG_LABEL_SAME_FAMILY | WRONG_FAMILY | EXTRA_UNIT_NO_GOLD | ABSTAINED | MISSED | EXTRA_UNIT_ABSTAINED | GOLD_UNDETERMINABLE_NO_PRED |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| printed_disposal | 254 | 14 | 15 | 25 | 42 | 129 | 14 | 1 |
| substantive_result | 221 | 0 | 31 | 14 | 70 | 115 | 25 | 18 |

**Family precision.** printed_disposal w 0.941 [0.890, 0.973], unw 0.870. substantive_result is the same as strict, because its families are 1:1.

**Abstentions.** 77 `OUTCOME_UNVERIFIED` rows. They include the 5 items with no text (`NO_JUDGMENT_ID_FOR_ITEM_SHA`). These are exactly the 5 store-pointer-defect SC items, whose files post-date the c7 text layer the extractor used.

**Where MISSED comes from.**
- MISSED is concentrated: 129 missed printed_disposal units fall in 13 items.
- Three batch judgments with 61, 27 and 13 gold proceeding units account for 101 of them.
- One of these, HO13-0c887610a7 with 62 units, is a BSF (CAPF) batch.
- **Why unweighted coverage (0.62) is far below weighted coverage (0.83).** The gap comes from the design weights.
  - The three batch items sit in oversampled cells, with small weights: HO13-0c887610a7 (SC, weight 1.43), HO13-a1438df4ca (PH BATCH, 5.14) and HO13-ee7912d06f (DEL BATCH, 3.57). Many single-proceeding DEL and PH items carry weights of 21.6–27.9.
  - The three items hold 23.6% of the unweighted determinable units but only 9.3% of the weighted ones.
  - Without them the gap is 0.911 (weighted) against 0.801 (unweighted). Most of the rest comes from the oversampled Supreme Court cells (weights 1.0–2.1, coverage 0.39); excluding SC as well gives 0.925 against 0.859. (Figures from the GA4 review, reproduced from ROWS.csv.)
  - So the weighted figure down-weights the oversampled batch and SC cells, where most misses fall. The unweighted figure reflects the sample's composition, not the population.
  - **Both figures are binding:** the met rule (s.6.4) requires the weighted and the unweighted point estimate to reach the target.

**Evidence anchors.** ANCHOR_OK 403, ANCHOR_NOT_FOUND 2, NO_ANCHOR 75 (mostly abstention rows). The OK rate over all prediction rows is 0.840 [0.804, 0.870].

**Per court.**

| Court | printed_disposal SP w [CP95] | printed_disposal coverage w [CP95] | substantive_result SP w [CP95] | substantive_result coverage w [CP95] |
| --- | --- | --- | --- | --- |
| SC | 0.576 [0.389, 0.749] (40/72) | 0.391 [0.226, 0.577] (47/139) | 0.667 [0.411, 0.867] | 0.387 [0.223, 0.573] |
| DEL | 0.920 [0.790, 0.982] (60/65) | 0.906 [0.790, 0.970] (65/96) | 0.960 [0.838, 0.997] | 0.840 [0.702, 0.932] |
| PH | 0.953 [0.861, 0.992] (84/87) | 0.813 [0.591, 0.945] (87/124) | 0.844 [0.706, 0.934] | 0.771 [0.565, 0.912] |
| JK | 0.800 [0.622, 0.919] (37/44) | 0.923 [0.782, 0.986] (44/51) | 0.961 [0.808, 0.999] | 0.769 [0.597, 0.893] |
| ALL | 0.848 [0.688, 0.945] (33/40) | 0.897 [0.759, 0.971] (40/44) | 0.724 [0.519, 0.877] | 0.681 [0.514, 0.820] |

**Per-court statuses.** No court reaches `MET_LOWER_BOUND` for either field. There are four `MET_POINT_ONLY` cells:
- PH printed_disposal strict precision;
- JK substantive_result strict precision;
- JK printed_disposal coverage;
- ALL printed_disposal coverage.

Breakdown statuses are not headline claims (s.6.6).

**Per stratum.** The weighted estimates are in `H-OUT-C13/RESULTS.json`.
- PENSION_OR_DISCIPLINARY is strongest: printed_disposal SP 0.944 and coverage 0.943.
- BATCH_OR_MULTI is weakest on coverage: printed_disposal 0.467.

**Proceeding-specific subset (gold multi-proceeding).**
- printed_disposal: SP w 0.873 [0.682, 0.971] (73/92), coverage w 0.388 [0.217, 0.581] (77/229). Status NOT_MET.
- substantive_result: SP 0.786, coverage 0.417. Status NOT_MET.

**Party-specific subset.** No gold unit carries `party_specific`, so there are 0 units. The breakdown is DESCRIPTIVE_ONLY, and the owner's party-specific requirement stays **not demonstrated**.

**Sensitivity without CASE_NUMBER_REVIEWED** (18 items excluded).
- printed_disposal: SP 0.899 [0.839, 0.942], coverage 0.861 [0.765, 0.928] (point estimate above 0.85, lower bound below).
- substantive_result: SP 0.882, coverage 0.785.
- All four are NOT_MET. The precision cells are NOT_MET because both point estimates are below 0.95. printed_disposal coverage is NOT_MET because its unweighted point (0.733) is below 0.85, although the weighted point is above it. substantive_result coverage is below 0.85 on both points.

**Material difference with and without PRIMARY.** None. Every point estimate moves by less than its validated half-width.

### 4.2 Holdings (A3): descriptive only, protocol deviation (see section 1.3)

**Design.** FULL_OPEN reserve decision (`593b485f…`): 75 registered judgments plus 38 reserve judgments, 113 in total, with weights recomputed per cell (`--reserve-open all`, which is also the harness default).

**Uncodable items.** 24 items (21.2%), all OUT_OF_SCOPE. The extractor made 209 prediction rows on them. 89 items are scored.

**Gold count.** There are **183** adjudicated gold `holding` units and 24 `question_of_law` units in the scored items. The size calculation assumed 234 holdings (s.3).

**Where the gold comes from** (`REVIEW_FIXES.json`). The adjudicator's `agrees_with` was NEITHER on 55 of the 79 adjudicated items, X on 14 and Y on 10. Of the 183 scored gold holdings:
- 113 (62%) come from items where the adjudicator matched neither coder;
- 42 come from items where the adjudicator chose one coder's coding (X 24, Y 18);
- 28 come from items on which both coders agreed.

So H-HOLD recall is measured mostly against **single-annotator gold**: one AI adjudicator coding under a definition that neither coder used.

**Second-coverage figure (s.4.5).** The harness produces no holdings recall that counts uncodable items as missed; it computes this figure for keyed tasks only. It is therefore not produced for H-HOLD.

**Categories.** CORRECT 98, UNMATCHED_PREDICTION 525, MISSED 105, WRONG_TYPE 4.

**Recall.**
- Pooled weighted: 0.517 [0.424, 0.608].
- Macro, unweighted per judgment: 0.47.
- Strict recall, with type and opinion family matched: identical to pooled recall.

**question_of_law.** Recall w 0.450 [0.175, 0.750] (8/24). Reference-match precision 0.157 (8/50).

**Evidence anchors.** OK 815, NOT_FOUND 18, NO_ANCHOR 3, so the OK rate is 0.975.

**True precision: the blind adjudication of predicted holdings** (protocol s.5).
- **Rules:** fixed in `H-HOLD-C13/pred_adjudication/ADJUDICATION_RULES.md` (sha `f76d48fb…`), written before the sample was drawn and before any holdings score was computed.
- **Frame:** 574 predicted `holding` rows on non-uncodable items.
- **Sample:** a seeded equal-probability sample of 100, the lowest values of `sha256("C13-GA4-HHOLD-PRED-ADJ|"+pred_id)`. The list is `SAMPLE_PRED_IDS.csv` (`143e12ef…`), covering 53 judgments.
- **Method:** the evaluator read each predicted excerpt in context on the sha-verified page text, with the opening and closing of the judgment shown, without seeing the reference or the match status. It applied the H-HOLD adjudicator's definition (`DEFINITION_APPLIED.md`).
- **Labels** (`PRED_ADJUDICATION.csv`, `cf4ee094…`):
  - 36 CORRECT;
  - 63 INCORRECT: FACT_FINDING 26, QUOTED_PRECEDENT 11, OPERATIVE 9, OTHER 7, PROCEDURAL_OR_NARRATIVE 5, SCOPE 2, COUNSEL_VOICE 2, OBITER 1;
  - 1 UNCLEAR, excluded by the harness.
- **Pre-specified restatement sensitivity:** counting the 2 RESTATEMENT rows as incorrect gives 0.356 [0.234, 0.495] (`sens_restatement_as_incorrect/`). Descriptive only.
- **Post-hoc consistency check against the reference.**
  - Of the 15 sampled predictions that match a reference span, 14 were labelled CORRECT.
  - Of the 84 that do not match, 22 were labelled CORRECT. These are mostly restatements or secondary steps that the adjudicator's one-row-per-issue convention leaves out of the gold.
- **Second adjudicator (GA4 review, F5).**
  - The reviewer blind-labelled 25 of the 100, drawn by lowest `sha256("C13-GA4-REVIEW-SUBADJ|"+pred_id)`, from sha-verified PDFs.
  - Agreement was 21/25 = 0.84 (Wilson about [0.65, 0.94]), Cohen's kappa 0.57. On those 25 the evaluator found 7 correct and the reviewer 5.
  - Using the reviewer's labels would lower unweighted precision by about 0.02, to about 0.34.
  - All 4 disagreements fall in borderline categories, where adjudicators diverge: a relief (back-wages) determination, a bare answer to a framed question, a precedent statement introducing a quotation, and a statement of the limits of certiorari.
  - Before any A3 figure is used beyond research, all 100 should be double-adjudicated, preferably by a human.

**Per court** (true precision w; recall w).

| Court | True precision w | Recall w |
| --- | --- | --- |
| SC | 0.409 (9/22) | 0.445 |
| DEL | 0.317 | 0.426 |
| PH | 0.547 | 0.630 |
| JK | 0.232 (1/5) | 0.737 (7/9) |
| ALL | 0.330 (2/9) | 0.739 (4/5) |

These breakdowns are descriptive only, like the overall H-HOLD figures. The harness labels PH, JK and ALL recall `MET_POINT_ONLY`, but those labels have no standing under the protocol here, and JK and ALL rest on very small counts.

**Sensitivity without CASE_NUMBER_REVIEWED.** Adjudicated precision 0.364, recall 0.518. Descriptive only.

### 4.3 Relations (A5)

- **Uncodable items:** 41 of 160 items (25.6%), all OUT_OF_SCOPE. The extractor made 137 prediction rows on them.
- **Abstentions:** 1 item abstained with `NO_TEXT`. There are 0 ABSTAINED units.
- **Categories (relation_type).** CORRECT 58, WRONG_FAMILY 101, MISSED 158, EXTRA_UNIT_NO_GOLD 15, PRED_ON_UNDETERMINABLE 2, GOLD_UNDETERMINABLE_NO_PRED 3.
- **Dominant error:** the extractor labels as `cites` units that the coders labelled `follows` (69) or `distinguishes` (31).
- **Evidence anchors:** 304 OK, 1 NO_ANCHOR.
- **Without PRIMARY** (8 items excluded): relation_type precision 0.347 [0.162, 0.575], target precision 0.612.
- **Without CASE_NUMBER_REVIEWED:** relation_type precision 0.436, target precision 0.624.
- **Without PRIMARY and the 4 A5-author-exposed judgments** (D-3; 11 items excluded): relation_type precision 0.341 [0.151, 0.579] (56/167), target precision 0.616 [0.455, 0.761]. This is not materially different from 0.340 (full) and 0.347 (without PRIMARY). Source: `REVIEW_FIXES.json`, matching the reviewer's independent run.
- **Coverage counting each uncodable item as not covered (s.4.5):** relation_type w 0.205 [0.083, 0.386], unw 0.444 (159/358); target w 0.205 [0.083, 0.386], unw 0.444 (161/363).
- **Per stratum.** relation_type precision is 0.29 on TREATMENT_CUE pages and 0.57 on UNRESOLVED_CITATION_ONLY pages. Target precision is 0.70 and 0.90.
- **Per court.** Per-court figures are in `H-REL-C13/RESULTS.json`. SC and HC cells have wide intervals.
- **Reading the target field:** coder agreement on `target` was low (kappa 0.48), so target precision measures agreement with a noisy normalisation.

## 5. Definitional and other sensitivity analyses (POST-HOC, not headline)

All of these were specified after the headline figures were computed. They use the harness estimator. They are context only and never replace a headline figure.

### 5.1 H-HOLD, using the adjudicator's borderline tags

Source: `H-HOLD-C13/POSTHOC_DEFINITIONAL_SENSITIVITY.json`.

- **Tags in adjudication notes:** GRANULARITY_SPLIT 49 rows (46 items), OBITER 11, FACT_FINDING 11, SCOPE 10, QUOTED_PRECEDENT 3, COUNSEL_VOICE 1.
- 56 of the 89 scored items carry at least one tag.

| Variant | Recall w [CP95], unw (k/n) | Reference-match precision w [CP95] |
| --- | --- | --- |
| S0 official (reproduced) | 0.517 [0.424, 0.608], 0.492 (90/183) | 0.156 [0.124, 0.192] |
| S1 exclude items with any tag (33 items left) | 0.694 [0.551, 0.814], 0.672 (45/67) | 0.238 [0.173, 0.313] |
| S2 exclude GRANULARITY_SPLIT items | 0.670 [0.536, 0.787], 0.663 (57/86) | 0.201 [0.152, 0.258] |
| S3 many-to-one matching (restatements of a gold holding count as matched) | 0.517 | 0.190 [0.155, 0.229] |
| S4 lenient gold = adjudicated ∪ both coders' holding units | 0.517 | 0.331 [0.288, 0.376] |
| S5 = S4, and every gold unit in a tagged item counted as recalled (upper bound, not an estimate) | 0.881 [0.806, 0.935] | 0.331 |

**Reading.**
- **Recall depends on how the gold is defined.** On items without borderline disputes it is about 0.67–0.69 (S1, S2). Those items are a selected subset, so this is not a population estimate.
- **Precision.** Adjudicated precision was measured under one definition, the one applied: 0.36 [0.24, 0.50]. Counting restatements as incorrect gives 0.36. The reference-match figures (S0–S4, 0.16–0.33) are lower bounds by construction, so they cannot by themselves show a shortfall. Adjudicated precision does not depend on the gold.

### 5.2 H-OUT, item exclusions

Source: `H-OUT-C13/POSTHOC_SENSITIVITY.json`.

| Exclusion | printed_disposal SP w [CP95] | printed_disposal coverage w [CP95], unw | substantive_result SP w | substantive_result coverage w |
| --- | --- | --- | --- | --- |
| 10 CAPF-mention items | 0.898 [0.838, 0.942] | 0.860 [0.764, 0.928], 0.725 | 0.887 | 0.785 |
| 5 store-pointer (HF@main) items | 0.898 | 0.838, 0.642 | 0.882 | 0.765 |
| 3 items with ≥ 13 gold units | 0.898 | 0.911 [0.857, 0.950], 0.801 | 0.882 | 0.818 |

Precision is unaffected by any exclusion. Coverage moves mainly with the three large batch judgments.

### 5.3 H-REL, excluding CAPF-mention items

relation_type precision 0.432, target precision 0.635.

## 6. Deviations and limitations (all must be read with the results)

**D-1. PD-01 (coordinator's error, H-HOLD).**
- The interim coding guide v1.1 forbade annotation until a substantive Holdings V2 guideline existed. None exists, and both coders coded under v1.1, which does not define "holding".
- H-HOLD gold is therefore **interim-guide gold, with no substantive guideline, not legally reviewed**.

**D-2. PD-01 addendum.**
- The H-HOLD adjudicator worked from a coordinator working definition, standard ratio-decidendi wording, written after the A3 freeze. The coordinator states it was written without reference to A3 output.
- The evaluator's blind adjudication of predicted holdings used the same definition, for consistency.
- Because the definition post-dates the freeze, A3 could not have targeted it. The definitional sensitivity is in section 5.1.
- **Gold provenance (GA4 review F2).** The adjudicator matched neither coder on 55 of 79 adjudicated items, and those items supply 113 of the 183 scored gold holdings (62%). Most of the H-HOLD gold is therefore one AI instance's coding under a definition neither coder used. It was never re-annotated by two coders.

**D-3. A3 SAMPLE/RESERVE disclosure.**
- On the coordinator's instruction, the A3 author read the key columns (`judgment_key`, `rep_sha256`, `rep_doc_id`) of H-HOLD `SAMPLE.csv` and `RESERVE.csv`, which are evaluator-only (s.4), to build a training-exclusion list. That list holds ids only (commit `f7155167`).
- A3's freeze statement also discloses that two early scope-wide scans printed 2 fresh ids with an opinion count and the cue word "dissent".
- Related disclosures found by the evaluator in the freeze records, not listed in the coordinator's log:
  - The A2 author read the `judgment_key` and `rep_sha256` columns of H-OUT `SAMPLE.csv` to build an exclusion list.
  - The A5 author read the identifier columns of H-REL `SAMPLE.csv` and `ITEM_MAP.csv` to build its predictions.
- These files hold identifier columns only: `judgment_key`, `rep_sha256`, `rep_doc_id` and `page`, plus A5's `ITEM_MAP.csv`. They carry no labels or text. The exposure is to holdout membership and the item mapping.
- **A5 author text exposure (GA4 review F3; recorded in A5's freeze statement, item 3, but not in the coordinator's log or the first version of this report).**
  - During the review fixes, the A5 author printed or saw text from other pages of four H-REL judgments: JK-f7c70c98230234f6, JK-4d86990aad309acd, JK-88a22c0473110afc and JK-aac99e3e5fbad324. The coded holdout page itself was not viewed.
  - Only JK-4d86990aad309acd is in `PRE_EXPOSED_SUBSET.csv` (as NEAR_IDENTICAL_SPENT_SIBLING).
  - Excluding PRIMARY plus these four (11 items) gives relation_type precision 0.341 [0.151, 0.579] (56/167) against 0.340 full. The difference is not material.
  - Recommendation for A0: register these judgments as author-exposed for future cycles. The registered subset is not changed retroactively.

**D-4. Store-pointer defect.**
- Five H-OUT SC files are absent at HF `5524c3d9` and present at HF `main` with matching LFS sha256: HO13-5f043e05ca, 299e337653, c123b2ef4d, b3ece22f38 and c7541dbf29.
- Coders coded them from `main`. coder_2 first returned them as FILE_UNAVAILABLE and was asked to code them.
- A2 had no text for them and abstained. They hold 13 gold units, which count against coverage. Excluding them (section 5.2) changes no conclusion.

**D-5. Excerpts in A5's predictions.**
- The A5 prediction file contains verbatim holdout excerpts, needed for the anchor check.
- No coder or adjudicator received predictions. The A2, A3 and A5 branches remain unpushed.
- This evaluation file quotes no holdout text. The H-HOLD adjudication labels file has short reason phrases only.

**D-6. Coordinator coding-brief errors.**
- PD-01: the precondition was not checked.
- The coordinator's H-OUT brief told coders "do not add rows". That was wrong: the guide requires one row per proceeding. Coders followed the guide.
- The H-HOLD coder_1 NO_HOLDING note format was fixed after the first return, with no change of meaning.

**D-7. H-HOLD agreement below the protocol threshold (s.4 item 6).**
- Span F1 between coders is 0.566, below the 0.6 at which the protocol requires guideline revision and re-annotation **before scoring**.
- The coordinator rejected re-coding this cycle, because the extractor was already frozen and a guideline written afterwards risks fitting the gold to the extractor.
- The rule has no exception and no owner-override clause. **H-HOLD is therefore NOT SCORABLE under protocol v1.1**, and A3 has no protocol verdict in C13 (GA4 review F1, P1).
- The coordinator's decision to score anyway amounts to a protocol change made without a new version or a s.10 entry, so it cannot yield a pre-registered headline. The H-HOLD figures were computed as instructed and are reported **as descriptive results under a deviation only**, with the low agreement alongside (strict item agreement 0.30, kappa including unmatched below 0).
- The rule gates "scoring", so it covers both recall and the adjudicated precision.

**D-8. Borderline scope of CAPF matters.**
- About 10 items per holdout concern CAPF forces (BSF, CRPF, Assam Rifles and others). Coders and adjudicators treated them as in scope; only one H-REL CAPF-mention item is uncodable, for a civilian matter.
- The scope rule ("armed-forces service or military-law matter") is not explicit for CAPF.
- Separately, a large share of items were coded `UNCODABLE:OUT_OF_SCOPE`: H-OUT 11%, H-HOLD 21%, H-REL 26%. These are general constitutional, tax and civil matters drawn from the eligible frame (frame scope flag from C10 automated relevance).
- Those items are excluded from every denominator and never replaced. The extractors made 115, 209 and 137 prediction rows on them. Population figures exclude them by construction.

**D-9. No human annotators.**
- Every reference set was coded and adjudicated by AI agent instances.
- The recommended human second coding of 20% of H-OUT (D-07) was not available.
- No legal adviser reviewed the guidelines, the definition or the gold.

**D-10. Evaluator-side notes.**
- **Adjudication of predicted holdings.** The evaluator, a single AI instance, adjudicated the predicted holdings, as the brief allowed. A second blind adjudicator would strengthen the estimate.
- **Incidental exposure.** While inspecting file formats before the sample was drawn, the evaluator printed the first truth row of H-HOLD, a holding of HH13-0240ac10da. One sampled prediction (#48) is from that judgment. It was labelled INCORRECT (an adjoining "we agree" sentence), so the exposure could only have lowered precision.
- **Text layer.** Anchors use the PyMuPDF text layer, not the extractors' c7 text.
- **Bytecode.** Running a viewer script wrote ignored `.pyc` files into `a0-eval/.../tools/__pycache__/`. The path is gitignored and nothing tracked changed.

**D-12. Protocol-deviation entry for the owner (H-HOLD).**
- H-HOLD-C13 was scored although s.4 item 6 (span F1 0.566 < 0.6) and the interim guide's precondition (PD-01) were not met. No protocol version or s.10 entry authorised it.
- Effect: no A3 protocol verdict in C13.
- What a scorable H-HOLD needs:
  - a substantive holdings guideline, written independently of A3 and its outputs, committed with a version and sha256 and recorded in the store manifest, and marked "not legally reviewed" unless a legal adviser reviews it;
  - re-annotation of H-HOLD by two fresh coders under that guideline, with agreement reported before scoring;
  - all of this before the next A3 freeze.

**D-13. Note for the A0 owner (GA4 review F10; not an evaluator error).**
- `aggregate()` and `aggregate_holdings()` drop UNCODABLE and sensitivity-excluded items from the unit list instead of keeping them as zero rows. The stratified variance then computes N_h from the reduced count, so the FPC and the between-cluster variance are slightly off.
- The effect is small, because Kish caps n_eff in most cells. It was not covered by the coverage simulation.
- For the next protocol version: keep excluded items as zero rows for the variance, or validate the current behaviour in `c13_ci_sim.py`.

**D-11. Population.**
- Weights extrapolate only to the eligible, non-spent, USABLE-text frame.
- The 89 non-usable judgments are excluded, including the 26 OCR-only judgments, excluded by rule 5 and not because they are unreadable.
- The spent judgments (about 19%) are not represented.

## 7. Commands (venv Python 3.13; T = a0-eval/legal_knowledge/audit_work/C13-A0-EVAL/tools)

```
# rebuild and check inputs
python -I -B $T/c13_coding.py truth --task <task> --a coding/<H>/coder_1/CODER_SHEET.csv --b coding/<H>/coder_2/CODER_SHEET.csv \
    --adjudicated coding/<H>/adjudicator/ADJUDICATION_RESULT.csv --out eval/rebuild/<H>.csv     # cmp == truth: identical x3
python -I -B $T/c13_coding.py agree --task <task> --a ... --b ... --out eval/rebuild/AGREEMENT_<H>.json   # cmp == sealed: identical x3
python -I -B $T/c13_coding.py leakcheck <returned sheet> --task <task> --completed --coder coder_N --packet <A0 packet> --other-coder coder_M
# store
store_version(eval/store, <H>, 1, [C13-COD-<K>-1, C13-COD-<K>-2, C13-ADJ-<K>], [coding/truth/<H>.csv], ...)   # x3
python -I -B $T/c13_coding.py verify eval/store                                          # store OK
# pages
python -I eval/scripts/build_pages.py <c13> eval/work/need_shas.txt eval/work/PAGES.jsonl  # 455 verified
# scoring
python -I -B $T/c13_score.py --check                                                      # self-test OK
python -I -B $T/c13_score.py --task outcome --holdout H-OUT-C13 --truth eval/store/H-OUT-C13/v001/H-OUT-C13.csv \
    --pred <A2 predictions> --store eval/store --pages eval/work/PAGES.jsonl --out-dir eval/H-OUT-C13
python -I -B $T/c13_score.py --task relations --holdout H-REL-C13 --truth eval/store/H-REL-C13/v001/H-REL-C13.csv \
    --pred <A5 predictions> --store eval/store --pages eval/work/PAGES.jsonl --out-dir eval/H-REL-C13
python -I -B $T/c13_score.py --task holdings --holdout H-HOLD-C13 --truth eval/store/H-HOLD-C13/v001/H-HOLD-C13.csv \
    --pred <A3 predictions> --store eval/store --pages eval/work/PAGES.jsonl --reserve-open all \
    --pred-adjudication eval/H-HOLD-C13/pred_adjudication/PRED_ADJUDICATION.csv --out-dir eval/H-HOLD-C13
#   (same with PRED_ADJUDICATION_RESTATEMENT_AS_INCORRECT.csv -> eval/H-HOLD-C13/sens_restatement_as_incorrect)
# post-hoc
python -I -B eval/scripts/posthoc_hhold.py $T <c13> eval/H-HOLD-C13/POSTHOC_DEFINITIONAL_SENSITIVITY.json
python -I -B eval/scripts/posthoc_keyed.py $T <c13> outcome H-OUT-C13 <A2 pred> eval/H-OUT-C13/POSTHOC_SENSITIVITY.json
python -I -B eval/scripts/posthoc_keyed.py $T <c13> relations H-REL-C13 <A5 pred> eval/H-REL-C13/POSTHOC_SENSITIVITY.json
# after the GA4 review (F2-F4)
python -I -B eval/scripts/review_fixes.py $T <c13> eval/REVIEW_FIXES.json
```

### Output hashes

**Scoring outputs.**

| Holdout | RESULTS.json | ROWS.csv |
| --- | --- | --- |
| H-OUT | `fd83220a…` | `0f198469…` |
| H-HOLD | `089d64a8…` | `9297f8d4…` |
| H-REL | `ada85555…` | `a3ae4b41…` |

The restatement sensitivity RESULTS.json is `350152f5…`.

**Post-hoc outputs.**

| File | sha256 prefix |
| --- | --- |
| H-OUT-C13/POSTHOC_SENSITIVITY.json | `52a3a070…` |
| H-REL-C13/POSTHOC_SENSITIVITY.json | `034b62f4…` |
| H-HOLD-C13/POSTHOC_DEFINITIONAL_SENSITIVITY.json | `881b1d72…` |
| REVIEW_FIXES.json (post-review) | `05a0759c…` |

**Adjudication files.**

| File | sha256 prefix |
| --- | --- |
| `labels_raw.txt` | `fbce0fca…` |
| `PRED_ADJUDICATION_RESTATEMENT_AS_INCORRECT.csv` | `d2dccea2…` |

**Evaluator scripts.**

| Script | sha256 prefix |
| --- | --- |
| `build_pages.py` | `dc24c330…` |
| `blind_view.py` | `4c7854c7…` |
| `posthoc_hhold.py` | `a77d5b25…` |
| `posthoc_keyed.py` | `6f0d3344…` |
| `show.py` | `5334b0de…` |
| `review_fixes.py` | `1c3889fc…` |

## 8. Measured versus estimated

- **Measured:** the unweighted counts on the coded holdouts (k/n above). These are agreement with AI-coded reference sets, and, for holdings precision, with one AI evaluator's blind adjudication.
- **Estimated:** the weighted figures and design-CP intervals. They extrapolate to the eligible frame through design weights.
- **Not legal facts:** neither kind of figure is a legal fact or verified knowledge.

## 9. Conclusions (plain language)

**A2, Outcome V4: status NOT_MET (target not met) on all four pre-registered targets.**
- When it answers, it is right about 88–90% of the time (weighted): printed disposal 0.90 [0.84, 0.94], substantive result 0.88 [0.82, 0.93]. That is short of the 95% strict-precision target, and even the upper ends of the intervals are below 0.95.
- Coverage is 0.83 and 0.76 weighted, but only 0.62 and 0.58 unweighted. The extractor often gives one disposition for a whole batch judgment when the reference has a row for each proceeding, and it abstains on several kinds of multi-proceeding text.
- It is weakest on Supreme Court judgments: precision 0.58 and coverage 0.39 for printed disposal.
- Delhi and P&H are close to target on precision.
- Results do not depend on the pre-exposed items.
- The party-specific requirement could not be tested: no gold party-specific units.

**A3, Holdings: no protocol verdict is possible. H-HOLD is not scorable under protocol v1.1** (s.4 item 6: span F1 0.566 < 0.6, no re-annotation; PD-01).
- Descriptively, adjudicated precision is 0.36 [0.24, 0.50], far below the 0.80 milestone. A second, independent adjudication of 25 of the 100 agreed on 84% (kappa 0.57) and points slightly lower. Most false positives are findings of fact, quotations of precedent, bare operative lines and narrative sentences.
- Recall (0.52 [0.42, 0.61]) cannot be interpreted against 0.60. It depends on the definition: about 0.67–0.69 on items without borderline disputes, post-hoc. It is also measured mostly against single-annotator gold (113 of 183 holdings).
- Counting restatements as incorrect, precision is 0.36. Reference-match lower bounds are 0.16–0.33 under all gold variants.
- This is consistent with the A3 author's own pre-freeze estimate (about 50% precision, 51–60% recall).
- Re-annotation under an independent substantive guideline is required before any A3 protocol result (D-12).

**A5, relations: no target, descriptive only.**
- The extractor almost always predicts `cites`. As a citation detector it agrees with the coders on the cited target about 62% of the time when it predicts.
- It rarely captures treatment. Of 154 coder-labelled `follows` units it labelled 5 as `follows` (recall 0.03 [0.01, 0.07] unweighted), and it identified none of the 53 `distinguishes`.
- Results are unchanged when the 4 judgments the A5 author partly saw are excluded (0.341).
- Relation-type precision is 0.34 [0.16, 0.56]. Weighted coverage is 0.26, which is descriptive because of extreme weights.
- Every non-`cites` edge must remain `llm_proposed` or `extracted` pending human decision, as the protocol requires.

**Overall.**
- A2: NOT_MET on all four targets.
- A3: not scorable under the protocol. Descriptive figures only, with precision far below the milestone.
- A5: descriptive, with no target.

Targets were not changed and nothing was tuned. All post-hoc analyses are labelled as such and leave the headline unchanged.

## 10. Response to the GA4 review (`reviews/eval/REVIEW_GA4.md`, ACCEPT WITH CONDITIONS)

| Finding | Change in this revision |
| --- | --- |
| F1 (P1) H-HOLD not scorable | H-HOLD re-labelled NOT SCORABLE UNDER PROTOCOL v1.1; all A3 figures DESCRIPTIVE ONLY with no PASS/FAIL (s.1.3, s.4.2, s.9); re-annotation under an independent substantive guideline required (D-7, D-12) |
| F2 (P2) gold provenance | NEITHER 55 of 79 items; 113 of 183 gold holdings (s.4.2, D-2) |
| F3 (P2) A5 author text exposure | Disclosed (D-3); sensitivity 0.341 [0.151, 0.579] (s.4.3) |
| F4 (P2) per-type recall | Per-gold-type recall with Wilson and design-CP intervals; `follows` no longer called rare (s.1.4) |
| F5 (P3) single adjudicator | Second-adjudicator agreement 0.84, kappa 0.57, n = 25 reported (s.1.3, s.4.2) |
| F6 (P3) coverage gap | Explanation rewritten around the design weights; both figures binding (s.4.1) |
| F7 (P3) "PASS" | PASS definition removed; MET_POINT_ONLY sufficiency stated as an owner decision (s.1.1); A2 cells read "NOT_MET / not met" |
| F8 (P3) "every definition" | Wording corrected (s.5.1, s.9) |
| F9 (P3) wording | CASE_NUMBER_REVIEWED reasons corrected (s.4.1); exposure scope corrected (D-3); s.4.5 second coverage reported for H-REL, noted as not produced for H-HOLD |
| F10 (P3, A0) | Recorded for the A0 owner (D-13) |

The pre-review version of this file is kept at `eval/work/RESULTS_C13.pre_review.md`.
