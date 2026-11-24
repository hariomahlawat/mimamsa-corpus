# DEV_EVALUATION_HOLDINGS (C12 Workstream E, part 1)

**ALL FIGURES ARE IN-SAMPLE.** The dev rows below were read while the rules and thresholds of `holdings_core.py` were written and tuned. They are not an estimate of performance on unseen judgments; the blind reference set is the only valid test.

Matcher: same page within one, and at least 40 common characters after normalising to lower-case letters and digits (the rule used in the C11 extraction review). Baseline: C11 `PROPOSITIONS_V2.jsonl` scored with the same matcher on the same rows.

Ground truth: 134 distinct reviewer holdings in 52 judgments from C11 `ground_truth_A.csv`/`ground_truth_B.csv` (single-coded; see C11 review F02).

## Recall: All dev judgments (SC + HC) (134 holdings, 52 judgments)

| Matched to | C12 recall (Wilson 95%) |
| --- | --- |
| holding | 60/134 = 44.8% (36.6-53.2) |
| holding+question_of_law | 60/134 = 44.8% (36.6-53.2) |
| court-voice set (question, holding, reasoning, obiter, operative) | 115/134 = 85.8% (78.9-90.7) |
| any emitted item | 117/134 = 87.3% (80.6-91.9) |
| C11 baseline: COURT_HOLDING or COURT_REASONING candidate | 13/134 = 9.7% (5.8-15.9) |
| C11 baseline: candidate of any origin | 50/134 = 37.3% (29.6-45.7) |
| top-3 holding/reasoning items per judgment by holding_score | 47/134 = 35.1% (27.5-43.5) |
| top-5 holding/reasoning items per judgment by holding_score | 65/134 = 48.5% (40.2-56.9) |
| top-10 holding/reasoning items per judgment by holding_score | 90/134 = 67.2% (58.8-74.5) |

## Recall: Supreme Court judgments (60 holdings, 20 judgments)

| Matched to | C12 recall (Wilson 95%) |
| --- | --- |
| holding | 26/60 = 43.3% (31.6-55.9) |
| holding+question_of_law | 26/60 = 43.3% (31.6-55.9) |
| court-voice set (question, holding, reasoning, obiter, operative) | 50/60 = 83.3% (72.0-90.7) |
| any emitted item | 51/60 = 85.0% (73.9-91.9) |
| C11 baseline: COURT_HOLDING or COURT_REASONING candidate | 4/60 = 6.7% (2.6-15.9) |
| C11 baseline: candidate of any origin | 14/60 = 23.3% (14.4-35.4) |
| top-3 holding/reasoning items per judgment by holding_score | 15/60 = 25.0% (15.8-37.2) |
| top-5 holding/reasoning items per judgment by holding_score | 21/60 = 35.0% (24.2-47.6) |
| top-10 holding/reasoning items per judgment by holding_score | 36/60 = 60.0% (47.4-71.4) |

## Recall: Judgments in the C12 scope set (51 holdings, 17 judgments)

| Matched to | C12 recall (Wilson 95%) |
| --- | --- |
| holding | 25/51 = 49.0% (35.9-62.3) |
| holding+question_of_law | 25/51 = 49.0% (35.9-62.3) |
| court-voice set (question, holding, reasoning, obiter, operative) | 46/51 = 90.2% (79.0-95.7) |
| any emitted item | 46/51 = 90.2% (79.0-95.7) |
| C11 baseline: COURT_HOLDING or COURT_REASONING candidate | 3/51 = 5.9% (2.0-15.9) |
| C11 baseline: candidate of any origin | 13/51 = 25.5% (15.5-38.9) |
| top-3 holding/reasoning items per judgment by holding_score | 15/51 = 29.4% (18.7-43.0) |
| top-5 holding/reasoning items per judgment by holding_score | 20/51 = 39.2% (27.0-52.9) |
| top-10 holding/reasoning items per judgment by holding_score | 34/51 = 66.7% (53.0-78.0) |

## Recall: High Court judgments (outside the C12 scope; tool still run on them) (74 holdings, 32 judgments)

| Matched to | C12 recall (Wilson 95%) |
| --- | --- |
| holding | 34/74 = 45.9% (35.1-57.2) |
| holding+question_of_law | 34/74 = 45.9% (35.1-57.2) |
| court-voice set (question, holding, reasoning, obiter, operative) | 65/74 = 87.8% (78.5-93.5) |
| any emitted item | 66/74 = 89.2% (80.1-94.4) |
| C11 baseline: COURT_HOLDING or COURT_REASONING candidate | 9/74 = 12.2% (6.5-21.5) |
| C11 baseline: candidate of any origin | 36/74 = 48.6% (37.6-59.8) |
| top-3 holding/reasoning items per judgment by holding_score | 32/74 = 43.2% (32.6-54.6) |
| top-5 holding/reasoning items per judgment by holding_score | 44/74 = 59.5% (48.1-69.9) |
| top-10 holding/reasoning items per judgment by holding_score | 54/74 = 73.0% (61.9-81.8) |

## GT-matched precision (lower bound)

Reviewers recorded at most three holdings per judgment, so an emitted holding that matches none of them is not necessarily wrong. These figures are lower bounds on precision, not precision.

| Item type | Items in dev judgments with GT holdings | Matching a GT holding |
| --- | --- | --- |
| question_of_law | 17 | 0/17 = 0.0% (0.0-18.4) |
| holding | 326 | 60/326 = 18.4% (14.6-23.0) |
| reasoning | 2245 | 55/2245 = 2.4% (1.9-3.2) |
| obiter_candidate | 20 | 1/20 = 5.0% (0.9-23.6) |
| operative_direction | 102 | 3/102 = 2.9% (1.0-8.3) |
| quoted_precedent | 184 | 0/184 = 0.0% (-0.0-2.0) |
| submission | 113 | 4/113 = 3.5% (1.4-8.7) |
| lower_court_finding | 78 | 1/78 = 1.3% (0.2-6.9) |

## Hand-checked precision (sampled items)

Each sampled item was read with about 300 characters of preceding context by the developing agent (an AI, not a lawyer). CORRECT for `holding` means the bench's own voice stating a legal conclusion or a decisive ruling on an issue (including a separate opinion's own conclusion); for `question_of_law` a question the court itself frames for decision; for `obiter_candidate` an observation not needed for the decision. Samples are the lowest sha256 of a salt plus item_id. The developer is not independent of the rules, so these are optimistic. Labels were made on pre-freeze builds; `type_in_frozen_output` shows what the frozen build emits for the same item. The question-of-law exclusion rules were written after this sample was read, so the frozen-output column for questions is in-sample and biased upward; the first column is the honest pre-fix figure.

| Sample | Type | Labelled CORRECT | Own-voice errors | Same type in frozen output: CORRECT / all |
| --- | --- | --- | --- | --- |
| dev5 (in-sample dev judgments) | holding | 28/40 = 70.0% (54.6-81.9) | 4/40 | 28/37 = 75.7% (59.9-86.6) |
| scope minus dev (pre-freeze build) | holding | 25/40 = 62.5% (47.0-75.8) | 5/40 | 25/40 = 62.5% (47.0-75.8) |
| scope minus dev (pre-freeze build) | question_of_law | 13/20 = 65.0% (43.3-81.9) | - | 13/14 = 92.9% (68.5-98.7) |
| scope minus dev (pre-freeze build) | obiter_candidate | 11/15 = 73.3% (48.0-89.1) | - | 11/15 = 73.3% (48.0-89.1) |

## C10 review_A/B: principal issue and answer (page level)

For each reviewed judgment with a page pinpoint, does the tool emit a holding (or question of law) on one of the pinpointed pages? Page-level only; the reviewers paraphrased rather than excerpted.

| Subset | Judgments with page pinpoints | Holding on a pinpointed page | Holding or question on a pinpointed page |
| --- | --- | --- | --- |
| all | 30 | 26/30 = 86.7% (70.3-94.7) | 26/30 = 86.7% (70.3-94.7) |
| sc_all | 23 | 21/23 = 91.3% (73.2-97.6) | 21/23 = 91.3% (73.2-97.6) |
| hc | 7 | 5/7 = 71.4% (35.9-91.8) | 5/7 = 71.4% (35.9-91.8) |

## Volume on dev judgments

| Item type | Items | Per judgment |
| --- | --- | --- |
| question_of_law | 66 | 0.8 |
| holding | 722 | 9.0 |
| reasoning | 6327 | 79.1 |
| obiter_candidate | 61 | 0.8 |
| operative_direction | 168 | 2.1 |
| quoted_precedent | 443 | 5.5 |
| submission | 319 | 4.0 |
| lower_court_finding | 199 | 2.5 |

## Misses from the court-voice set (19)

| GT | Page | Matched as (non-court types) | Page-ignored match | Excerpt (first 140 chars) |
| --- | --- | --- | --- | --- |
| H006 J-c219dc9e50c145f9 | 173 | - | N | an additional threshold be erected for exercising the right under Section 7, certainly, it cannot suffer a constitutional veto at the hands  |
| H007 J-477651e6cc382094 | 20 | - | N | the Courts/Tribunals will only play a secondary role while the primary judgment as to reasonableness will remain with the executive or admin |
| H008 J-41e4cd15e831fd32 | 21 | - | N | The power and discretion vested in the President of India by virtue of Pension Regulation 16(a), to forfeit and deny the pension in full or  |
| H009 J-cb3aa7cfabf6806b | 24 | - | N | It is rather not possible to accept the contention that a General Court Martial and confirming authorities imposing punishments can debar th |
| H012 J-81a996f5fc5a3566 | 8 | submission | Y | the view taken by the High Court and the contentions advanced on behalf of the State that the said document is a 'private document' would be |
| H013 J-6f92473b87b41a26 | 14 | - | N | there were seven hours which period was sufficient for the appellant to cool down. |
| H018 J-46155cc20adbc191 | 173 | - | N | The vacuum in the case of Article 324 (2) is the absence of the law which Parliament was contemplated to enact. |
| H018 J-46155cc20adbc191 | 175 | - | N | we are of the considered view that the time is ripe for the Court to lay down norms. |
| H018 J-46155cc20adbc191 | 180 | - | N | We are of the view that in the context of the provision, the words 'provided further' cannot be perceived as an additional protection to the |
| H019 J-4872f6c07059de30 | 127 | - | N | The experiment contained in the Code, judged by the generality of its provisions and not by so-called crudities and inequities that have bee |
| H026 J-25d56e6a918d4b63 | None | - | N | she seeks permission to withdraw the present petition while reserving the right of the petitioner to approach the Armed Force Tribunal. [... |
| H027 J-a7038ae7aa02d0f8 | 3 | - | N | Strictly read, therefore, the approval accorded by Brigadier DSC would be only for LMC (P) cases for ADS. |
| H029 J-d3845af43a1ee881 | 6 | lower_court_finding | Y | by treating the said disability attributable to the military service keeping in view the settled principle of law noticed hereinbefore, cann |
| H031 J-b8d58c1ad94db0df | 7 | - | N | respondent No.1 has rightly been held to be entitled to disability pension by rounding off the disability element from 20% to 50% w.e.f. 01. |
| H031 J-b8d58c1ad94db0df | 5 | - | N | Learned counsel for the petitioners has not been able to rebut that in that case respondent No.1 is held entitled for the grant of disabilit |
| H031 J-b8d58c1ad94db0df | 8 | - | N | in the absence of any perversity being pointed out in the impugned order dated 18.11.2024 (Annexure P-1) either on the basis of the facts or |
| H034 J-edd9b3e010b4678e | 1 | - | N | It is not in dispute that the issue involved in the present writ petition is squarely covered by a judgement of this Court passed in CWP No. |
| H040 J-99f81d5d90c41d57 | 4 | - | N | A recurring cause of action cannot, by itself, substitute proof where the foundational record is admittedly unavailable. |
| H040 J-99f81d5d90c41d57 | 4 | - | N | Mere non-reference to every judgment cited by a party does not, by itself, constitute an error apparent on the face of the record. |

