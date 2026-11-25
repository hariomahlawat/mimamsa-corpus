# RESULTS_C13: GA4 independent evaluation of Outcome V4 (A2), Holdings (A3) and relations (A5)

- **Evaluator:** the C13 GA4 evaluator, an AI agent instance. It wrote no extractor, did no coding and did no adjudication of the reference sets. It is not a human and not a legal reviewer.
- **Date:** 2026-11-25.
- **Protocol:** `PROTOCOL_C13.md` v1.1 at `claude/c13-a0-eval` `f1d61f71` (sha256 `9d6f04ed…`).
- **Status of every figure:** `AUTOMATED_CANDIDATE_NOT_VERIFIED`. The figures are scored against AI-coded reference sets. Two separate agent instances coded each holdout and a third adjudicated it. No human annotator took part.
- **Independent review:** this document still needs one (protocol s.7, GA4).
- **Changes made:** no branch, prediction, truth or protocol file was changed. Nothing was committed and nothing was written to HF.
- **Outputs:** everything is in `scratchpad/c13/eval/`.

## 1. Headline (pre-registered rule, PROTOCOL s.6)

### 1.1 How to read the tables

- **w:** the weighted Horvitz–Thompson point estimate.
- **CP95:** the validated design-effect Clopper–Pearson 95% interval (the pass rule).
- **unw:** the unweighted pooled proportion, with its counts.
- **Status:** the harness `headline_status`. It is the worse of the full-sample status and the status without the PRIMARY pre-exposed subset.
- **PASS:** a target passes only at `MET_LOWER_BOUND`, meaning the validated lower bound is at or above the target, both with and without PRIMARY.
- **MET_POINT_ONLY:** the point estimates reach the target but the lower bound does not. It is shown where it occurs.

### 1.2 Outcome V4 (A2), H-OUT-C13

| Field | Metric (target) | w | CP95 | unw (k/n) | Without PRIMARY: w [CP95] | Status | Target |
| --- | --- | --- | --- | --- | --- | --- | --- |
| printed_disposal | strict precision (≥ 0.95) | 0.898 | [0.838, 0.941] | 0.825 (254/308) | 0.889 [0.824, 0.936] | NOT_MET | **FAIL** |
| printed_disposal | coverage (≥ 0.85) | 0.833 | [0.743, 0.902] | 0.623 (283/454) | 0.826 [0.727, 0.901] | NOT_MET | **FAIL** |
| substantive_result | strict precision (≥ 0.95) | 0.882 | [0.815, 0.932] | 0.831 (221/266) | 0.880 [0.809, 0.932] | NOT_MET | **FAIL** |
| substantive_result | coverage (≥ 0.85) | 0.760 | [0.671, 0.835] | 0.577 (252/437) | 0.751 [0.653, 0.832] | NOT_MET | **FAIL** |

### 1.3 Holdings (A3), H-HOLD-C13 (interim research milestone)

These figures are interim-guide gold, and the inter-coder agreement was low (see sections 3 and 5).

| Metric (target) | w | CP95 | unw (k/n) | Without PRIMARY: w [CP95] | Status | Target |
| --- | --- | --- | --- | --- | --- | --- |
| holding precision, true (blind adjudication, seeded sample of 100) (≥ 0.80) | 0.365 | [0.241, 0.503] | 0.364 (36/99) | 0.365 [0.238, 0.508] | NOT_MET | **FAIL** |
| holding recall (≥ 0.60) | 0.517 | [0.424, 0.608] | 0.492 (90/183) | 0.535 [0.439, 0.630] | NOT_MET | **FAIL** |
| holding precision, reference-match (lower bound only) | 0.156 | [0.124, 0.192] | 0.157 (90/574) | 0.162 [0.129, 0.200] | (lower bound) | — |

### 1.4 Relations (A5), H-REL-C13

The owner set no target, so these figures are descriptive (protocol s.1).

| Predicted type | Field | Precision w [CP95], unw (k/n) | Coverage of units of that predicted type |
| --- | --- | --- | --- |
| all | relation_type | 0.340 [0.161, 0.560], 0.330 (58/176) | overall coverage w 0.260 [0.109, 0.471], unw 0.502 (159/317) |
| all | target | 0.620 [0.467, 0.758], 0.619 (109/176) | w 0.261 [0.109, 0.471], unw 0.500 (161/322) |
| `cites` (170 answered) | relation_type | 0.336 [0.156, 0.561], 0.312 (53/170) | — |
| `follows` (6 answered) | relation_type | 0.526 [0.061, 0.956], 0.833 (5/6). Counts only: rare type | — |

Per gold type recall is supplementary: unweighted counts from `H-REL-C13/ROWS.csv`, excluding uncodable items.

| Gold type | Gold units | Predicted `follows` | Predicted `cites` | No prediction | Recall |
| --- | --- | --- | --- | --- | --- |
| `follows` | 154 | 5 | 69 | 80 | 5/154 = 3% |
| `cites` | 105 | 1 | 53 | 51 | 53/105 = 50% |
| `distinguishes` | 53 | 0 | 31 | 22 | 0/53 |
| `applies` | 3 | 0 | 0 | 3 | 0/3 |
| `not_followed` | 2 | 0 | 0 | 2 | 0/2 |

No `overrules` was coded or predicted. Weighted overall recall and coverage are **descriptive only** (Kish design effect 7.5, s.3.1): the large-weight NO_DETECTED_CITATION pages pull weighted coverage (0.26) far below unweighted (0.50).

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
- Because of this, unweighted coverage (0.62) is far below weighted coverage (0.83).

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
- All four are NOT_MET, because the unweighted coverage of 0.733 is below target.

**Material difference with and without PRIMARY.** None. Every point estimate moves by less than its validated half-width.

### 4.2 Holdings (A3)

**Design.** FULL_OPEN reserve decision (`593b485f…`): 75 registered judgments plus 38 reserve judgments, 113 in total, with weights recomputed per cell (`--reserve-open all`, which is also the harness default).

**Uncodable items.** 24 items (21.2%), all OUT_OF_SCOPE. The extractor made 209 prediction rows on them. 89 items are scored.

**Gold count.** There are **183** adjudicated gold `holding` units and 24 `question_of_law` units in the scored items. The size calculation assumed 234 holdings (s.3).

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
- **Pre-specified restatement sensitivity:** counting the 2 RESTATEMENT rows as incorrect gives 0.356 [0.234, 0.495] (`sens_restatement_as_incorrect/`). Still NOT_MET.
- **Post-hoc consistency check against the reference.**
  - Of the 15 sampled predictions that match a reference span, 14 were labelled CORRECT.
  - Of the 84 that do not match, 22 were labelled CORRECT. These are mostly restatements or secondary steps that the adjudicator's one-row-per-issue convention leaves out of the gold.

**Per court** (true precision w; recall w).

| Court | True precision w | Recall w |
| --- | --- | --- |
| SC | 0.409 (9/22) | 0.445 |
| DEL | 0.317 | 0.426 |
| PH | 0.547 | 0.630 |
| JK | 0.232 (1/5) | 0.737 (7/9) |
| ALL | 0.330 (2/9) | 0.739 (4/5) |

PH, JK and ALL show `MET_POINT_ONLY` for recall. These rest on very small counts and are not headline claims.

**Sensitivity without CASE_NUMBER_REVIEWED.** True precision 0.364, recall 0.518. NOT_MET.

### 4.3 Relations (A5)

- **Uncodable items:** 41 of 160 items (25.6%), all OUT_OF_SCOPE. The extractor made 137 prediction rows on them.
- **Abstentions:** 1 item abstained with `NO_TEXT`. There are 0 ABSTAINED units.
- **Categories (relation_type).** CORRECT 58, WRONG_FAMILY 101, MISSED 158, EXTRA_UNIT_NO_GOLD 15, PRED_ON_UNDETERMINABLE 2, GOLD_UNDETERMINABLE_NO_PRED 3.
- **Dominant error:** the extractor labels as `cites` units that the coders labelled `follows` (69) or `distinguishes` (31).
- **Evidence anchors:** 304 OK, 1 NO_ANCHOR.
- **Without PRIMARY** (8 items excluded): relation_type precision 0.347 [0.162, 0.575], target precision 0.612.
- **Without CASE_NUMBER_REVIEWED:** relation_type precision 0.436, target precision 0.624.
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
- **Precision stays far below 0.80 under every definition.** Even the most lenient reference (S4, 0.33) is not close, and the true adjudicated precision of 0.36 does not depend on the gold.

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

**D-3. A3 SAMPLE/RESERVE disclosure.**
- On the coordinator's instruction, the A3 author read the key columns (`judgment_key`, `rep_sha256`, `rep_doc_id`) of H-HOLD `SAMPLE.csv` and `RESERVE.csv`, which are evaluator-only (s.4), to build a training-exclusion list. That list holds ids only (commit `f7155167`).
- A3's freeze statement also discloses that two early scope-wide scans printed 2 fresh ids with an opinion count and the cue word "dissent".
- Related disclosures found by the evaluator in the freeze records, not listed in the coordinator's log:
  - The A2 author read the `judgment_key` and `rep_sha256` columns of H-OUT `SAMPLE.csv` to build an exclusion list.
  - The A5 author read the identifier columns of H-REL `SAMPLE.csv` and `ITEM_MAP.csv` to build its predictions.
- None of these files carries labels, strata outcomes or text. The exposure is to identity and design-cell membership only.

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
- The H-HOLD figures were scored as instructed, but **under a protocol precondition that was not met**. They must be headlined with this and with the low agreement (strict item agreement 0.30, kappa including unmatched below 0).
- A3 is far below target on precision under every definition, so this deviation does not change the conclusion about A3. It does make the recall figure definition-dependent.

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

## 8. Measured versus estimated

- **Measured:** the unweighted counts on the coded holdouts (k/n above). These are agreement with AI-coded reference sets, and, for holdings precision, with one AI evaluator's blind adjudication.
- **Estimated:** the weighted figures and design-CP intervals. They extrapolate to the eligible frame through design weights.
- **Not legal facts:** neither kind of figure is a legal fact or verified knowledge.

## 9. Conclusions (plain language)

**A2, Outcome V4: FAIL on all four pre-registered targets.**
- When it answers, it is right about 88–90% of the time (weighted): printed disposal 0.90 [0.84, 0.94], substantive result 0.88 [0.82, 0.93]. That is short of the 95% strict-precision target, and even the upper ends of the intervals are below 0.95.
- Coverage is 0.83 and 0.76 weighted, but only 0.62 and 0.58 unweighted. The extractor often gives one disposition for a whole batch judgment when the reference has a row for each proceeding, and it abstains on several kinds of multi-proceeding text.
- It is weakest on Supreme Court judgments: precision 0.58 and coverage 0.39 for printed disposal.
- Delhi and P&H are close to target on precision.
- Results do not depend on the pre-exposed items.
- The party-specific requirement could not be tested: no gold party-specific units.

**A3, Holdings: FAIL on both interim milestones.**
- Blind adjudication of a seeded sample of 100 predicted holdings found about 36% to be holdings: 0.36 [0.24, 0.50] against a target of 0.80. Most false positives are findings of fact, quotations of precedent, bare operative lines and narrative sentences.
- Recall is 0.52 [0.42, 0.61] against 0.60.
- The gold has serious limits:
  - interim guide only, with no substantive definition at coding time (PD-01);
  - adjudicated under a definition written after the freeze;
  - very low coder agreement, with span F1 0.57, below the protocol's re-annotation threshold.
- Recall therefore depends on the definition: about 0.67–0.69 on items without borderline disputes, post-hoc. The precision failure holds under every definition tried.
- This matches the A3 author's own pre-freeze estimate (about 50% precision, 51–60% recall).

**A5, relations: no target, descriptive only.**
- The extractor almost always predicts `cites`. As a citation detector it agrees with the coders on the cited target about 62% of the time when it predicts.
- It rarely captures treatment. Of 154 coder-labelled `follows` units it labelled 5 as `follows`, and it identified none of the 53 `distinguishes`.
- Relation-type precision is 0.34 [0.16, 0.56]. Weighted coverage is 0.26, which is descriptive because of extreme weights.
- Every non-`cites` edge must remain `llm_proposed` or `extracted` pending human decision, as the protocol requires.

**Overall.** None of the three frozen extractors meets a pre-registered target. Targets were not changed and nothing was tuned. All post-hoc analyses are labelled as such and leave the headline unchanged.
