# C13-A3 development evaluation (IN-SAMPLE) - c13-holdings vs c12-holdings/1.0.0

**Every figure on this page is in-sample.** The C12 reference (30 judgments), the C12 adjudication sample, the C12 dev hand-check and the C11 GT trained the C13 classifier and were read while the C13 rules were written. The C12 figures on the same rows are the frozen C12 predictions re-scored with the same matcher; for C12 these rows were blind (reference) or in-sample (C11 GT). The comparison therefore flatters C13. The only valid test is the fresh A0 set scored by an independent evaluator.

Status of all items: `AUTOMATED_CANDIDATE_NOT_VERIFIED`. Not legal validation.

## 1. C12 holdings reference (30 judgments), C12 pre-registered primary matcher

| Metric | c12-holdings (frozen, blind for C12) | c13 (in-sample) |
| --- | --- | --- |
| Holding recall (`holding`) | 29.3% (36/123; 95% CI 22.0-37.8); macro 33.9% | 79.7% (98/123; 95% CI 71.7-85.8); macro 83.4% |
| Holding recall incl. dissent/split candidates | n/a | 87.8% (108/123; 95% CI 80.9-92.5) |
| QoL recall | 9.1% (7/77; 95% CI 4.5-17.6) | 61.0% (47/77; 95% CI 49.9-71.2) |
| Predicted `holding` items | 209 | 312 |
| Holding precision, reference-match lower bound (vs ref holdings) | 18.7% (39/209; 95% CI 14.0-24.5) | 42.6% (133/312; 95% CI 37.3-48.2) |
| Holding precision, lower bound (vs any ref item) | 28.2% (59/209; 95% CI 22.6-34.7) | 46.2% (144/312; 95% CI 40.7-51.7) |
| Predicted QoL items | 26 | 104 |
| QoL precision lower bound | 30.8% (8/26; 95% CI 16.5-50.0) | 52.9% (55/104; 95% CI 43.4-62.2) |

## 2. The 60 C12 holdings the blind evaluator adjudicated: does C13 still emit them as `holding`?

| C12 adjudication label | emitted by C13 as holding | not emitted |
| --- | --- | --- |
| CORRECT_HOLDING | 25 | 0 |
| NOT_COURT_VOICE:dissent | 0 | 4 |
| NOT_COURT_VOICE:quoted_precedent | 0 | 3 |
| NOT_COURT_VOICE:split_verdict_individual_opinion | 0 | 5 |
| REASONING_NOT_HOLDING:factual_recital | 2 | 5 |
| REASONING_NOT_HOLDING:justificatory_remark | 0 | 1 |
| REASONING_NOT_HOLDING:operative_disposal | 1 | 1 |
| REASONING_NOT_HOLDING:question_framing | 0 | 1 |
| REASONING_NOT_HOLDING:reasoning_step | 2 | 2 |
| REASONING_NOT_HOLDING:statute_restatement | 1 | 4 |
| WRONG_SPAN | 2 | 1 |

Of the C12 holding-sample items C13 still emits as holdings, 25/33 were adjudicated CORRECT_HOLDING (C12: 25/60). This is a biased direction indicator only: it covers C13 holdings that coincide with C12's adjudicated sample, not C13's new items. It is not a precision estimate.

## 3. C11 holdout ground truth (134 holdings, 52 judgments)

| Matcher | c12 `holding` (in-sample for C12) | c13 `holding` (in-sample) |
| --- | --- | --- |
| C12 primary (>=60% containment, page +-1) | 45.5% (61/134; 95% CI 37.3-54.0); macro 47.1% | 91.0% (122/134; 95% CI 85.0-94.8); macro 92.3% |
| C12 dev rule (40 common chars, page +-1) | 44.8% (60/134; 95% CI 36.6-53.2); macro 46.5% | 88.1% (118/134; 95% CI 81.5-92.5); macro 88.1% |
| Predicted `holding` items | 722 | 361 |

## 4. Out-of-fold classifier estimate (grouped 5-fold by judgment; holding head only)

Sentence-level: court-voice sentences whose out-of-fold probability is at or above T and that pass the deterministic holding vetoes (`c13_extract.holding_veto`; the opinion floor and operative/QoL precedence of the full extractor are not emulated). 'Labelled positive' = the sentence matches a positive holding label (C12 reference, C11 GT, adjudicated or hand-checked correct). 'Explicitly labelled' = it matches any labelled row (positive or negative). The share among explicitly labelled sentences is a precision proxy restricted to labelled material; unlabelled selected sentences are not scored. Recall: positive holding labels from the C12 reference and C11 GT with at least one matching sentence selected.

| T | selected | per judgment | labelled positive | explicitly labelled | proxy precision | label recall (C12 ref + C11 GT) |
| --- | --- | --- | --- | --- | --- | --- |
| 0.50 | 1405 | 10.3 | 210 | 283 | 74.2% (210/283; 95% CI 68.8-79.0) | 59.9% (154/257; 95% CI 53.8-65.7) |
| 0.60 | 1001 | 7.3 | 179 | 235 | 76.2% (179/235; 95% CI 70.3-81.2) | 51.0% (131/257; 95% CI 44.9-57.0) |
| 0.70 | 677 | 4.9 | 150 | 192 | 78.1% (150/192; 95% CI 71.8-83.4) | 43.2% (111/257; 95% CI 37.3-49.3) |
| 0.80 | 429 | 3.1 | 112 | 139 | 80.6% (112/139; 95% CI 73.2-86.3) | 31.9% (82/257; 95% CI 26.5-37.8) |
| 0.85 | 314 | 2.3 | 94 | 113 | 83.2% (94/113; 95% CI 75.2-89.0) | 28.4% (73/257; 95% CI 23.2-34.2) |
| 0.90 | 187 | 1.4 | 67 | 81 | 82.7% (67/81; 95% CI 73.1-89.4) | 19.8% (51/257; 95% CI 15.4-25.1) |
| 0.95 | 90 | 0.7 | 35 | 44 | 79.5% (35/44; 95% CI 65.5-88.8) | 10.1% (26/257; 95% CI 7.0-14.4) |

## 5. Per-judgment (C12 reference, primary matcher)

| judgment_id | ref holdings | c12 recovered | c13 recovered | c12 predicted | c13 predicted |
| --- | --- | --- | --- | --- | --- |
| J-0af19b8f3bae094c | 5 | 0 | 5 | 8 | 13 |
| J-0d73f180300fe935 | 3 | 2 | 3 | 4 | 6 |
| J-0e53c23530089091 | 3 | 0 | 1 | 3 | 4 |
| J-0f00b90f46307309 | 4 | 3 | 3 | 11 | 5 |
| J-10dc5626da5e9a02 | 4 | 0 | 4 | 4 | 19 |
| J-13846cd0a8f63fff | 3 | 2 | 3 | 3 | 4 |
| J-1bf3c164fc10c22d | 2 | 1 | 1 | 5 | 8 |
| J-2d33465ae5d25d91 | 3 | 0 | 2 | 4 | 9 |
| J-35e75ee438d9ca89 | 2 | 2 | 2 | 4 | 11 |
| J-3bad0eb6bfcf37cb | 3 | 0 | 2 | 4 | 9 |
| J-5c1c23b8ad57146f | 8 | 2 | 1 | 25 | 1 |
| J-5c8aecc8bec91cf2 | 4 | 2 | 4 | 4 | 16 |
| J-6d6c013692653e54 | 4 | 2 | 4 | 7 | 19 |
| J-73d6fd19e0c9aa51 | 5 | 0 | 4 | 6 | 10 |
| J-74ed92b68f7e0ffa | 3 | 0 | 3 | 1 | 4 |
| J-8eadd78cab5591be | 5 | 2 | 5 | 9 | 18 |
| J-a7f4d2780e93a902 | 4 | 1 | 4 | 8 | 19 |
| J-afe374e31d19a1d2 | 2 | 1 | 2 | 2 | 5 |
| J-b6eb34d5717f2c89 | 4 | 1 | 3 | 8 | 12 |
| J-c1ecdaeebf16bd67 | 4 | 2 | 4 | 5 | 15 |
| J-c295f22913ef898e | 2 | 2 | 2 | 4 | 6 |
| J-c6dd21359a7e3cbd | 5 | 2 | 3 | 7 | 14 |
| J-d0a1137f5387aff1 | 4 | 1 | 4 | 4 | 12 |
| J-d1f5aada95949bbf | 9 | 1 | 7 | 24 | 12 |
| J-d82320a8d262a3a0 | 3 | 2 | 3 | 4 | 11 |
| J-d9470d72b572e71d | 6 | 1 | 1 | 14 | 6 |
| J-e44fa1a569510458 | 4 | 0 | 4 | 4 | 11 |
| J-e61dc95c5ab477fb | 2 | 1 | 2 | 3 | 4 |
| J-f8651c212d771235 | 4 | 0 | 4 | 5 | 10 |
| J-fc15feb56e7eaba8 | 9 | 3 | 8 | 15 | 19 |

