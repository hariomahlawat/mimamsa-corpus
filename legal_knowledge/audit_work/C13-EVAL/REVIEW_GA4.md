# REVIEW_GA4: independent review of RESULTS_C13 (A2 Outcome V4, A3 Holdings, A5 relations)

- **Reviewer:** the GA4 independent reviewer, an AI agent instance. I built no extractor, did no coding or reference adjudication, did no scoring and did not write RESULTS_C13. I am not a human and not a legal reviewer.
- **Date:** 2026-11-25.
- **Reviewed:** `scratchpad/c13/eval/RESULTS_C13.md` and everything under `eval/`, against `PROTOCOL_C13.md` v1.1 (A0 `f1d61f71`, file sha256 matching A0 `SHA256SUMS`), `tools/c13_score.py`, `c13_stats.py`, `c13_sensitivity.py`, `coding/ASSIGNMENT_LOG.md`, `coding/truth/`, and the frozen predictions at `9cdd5008` (A2), `a520aa3a` (A3) and `e15af208` (A5).
- **Changes made:** none to any branch, truth, prediction, protocol or evaluator file. Nothing was committed and nothing was written to HF. Everything I produced is in `scratchpad/c13/reviews/eval/`. That covers `repro/` (my scoring outputs, rebuilt truth and agreement files, the independent estimator check `indep_check.py`, the sub-adjudication sample and labels, the downloaded PDFs) and `tools/view.py`, my blind viewer.
- **Status of every figure:** `AUTOMATED_CANDIDATE_NOT_VERIFIED`.

## A. What I re-did and what matched

| Check | Result |
| --- | --- |
| `c13_score.py --check` | self-test OK |
| `c13_coding.py verify eval/store` | store OK |
| Truth files: store copies vs `coding/truth/` | identical sha256 (H-OUT `59847e94…`, H-HOLD `bb726f95…`, H-REL `eef7b104…`) |
| Truth rebuilt from coder sheets and adjudication (`c13_coding.py truth`) | byte-identical ×3 |
| Agreement rebuilt (`c13_coding.py agree`) vs sealed `AGREEMENT.json` | byte-identical ×3; H-HOLD `span_f1` = 0.5661 confirmed |
| `leakcheck --completed` on the 6 returned sheets (with `--other-coder`) | OK ×6 |
| Prediction files: working copy vs `git show <freeze>:<path>` | identical (A2 `45c5a332…`, A3 `3894ecbf…`, A5 `c53ea96a…`) |
| Ancestry: `git merge-base --is-ancestor` of `d3a1bb0a` (adds `HOLDOUT_REGISTRATION.json` and the samples), `5e07e010` (last registration change), `06340486` and `f1d61f71` into each freeze | OK for all 12 pairs |
| Harness and design hashes (`c13_score` `3144aafc…`, `c13_stats` `36229c63…`, `c13_sensitivity` `1dd92da5…`, `c13_coding` `9ebf01f4…`, `PRE_EXPOSED_SUBSET.csv` `a7c71139…`, `HOLDOUT_REGISTRATION.json` `f87364df…`, reserve decision `593b485f…`) | match A0 `SHA256SUMS` and the protocol |
| **Scoring re-run** (same commands, my own out-dir) | **byte-identical**: RESULTS.json H-OUT `fd83220a…`, H-HOLD `089d64a8…`, H-REL `ada85555…`, restatement sensitivity `350152f5…`; ROWS.csv `0f198469…`, `9297f8d4…`, `a3ae4b41…` |
| Independent re-implementation of the HT ratio, Kish and Korn–Graubard n_eff, and the CP interval (my own beta quantile by numerical integration, from ROWS.csv) | identical to 4 dp for all four A2 headline cells and for A3 true precision (0.3648 [0.2414, 0.5026], n_eff 57.2) |
| H-HOLD reserve (FULL_OPEN) | 113 items (75 + 38), per-cell n_h recomputed (for example HC_DEL\|MEDIUM 21+12 = 33, weight 544/33 = 16.485), weight = N_h/n_h, as s.3.1 requires |
| Pre-exposed exclusion | PRIMARY = all categories except CASE_NUMBER_REVIEWED (`c13_sensitivity.PRIMARY`); items excluded: H-OUT 35, H-HOLD 8, H-REL 8 (7 judgments); `headline_status` = worse of full and without-PRIMARY (`_worse`), as s.4.4 and s.6 require |
| Abstention and coverage | answered = not in {"", ABSTAIN, ABSTAINED, OUTCOME_UNVERIFIED, unclear}; determinable = gold not unclear/other; extras and predictions on undeterminable units count as incorrect; UNCODABLE items are out of the denominators and reported, with a second coverage figure for keyed tasks. This matches s.4.5 and s.5 |
| Met rule | `target_status` implements s.6.4 exactly (weighted and unweighted points for MET_POINT_ONLY; plus design-CP lower bound for MET_LOWER_BOUND) |
| A3 precision sample | re-drawn from the rules (574-row frame, lowest `sha256("C13-GA4-HHOLD-PRED-ADJ\|"+pred_id)`): identical to `SAMPLE_PRED_IDS.csv` |

**Reproduction verdict: MATCHED.** Every reported headline number reproduces exactly from the stored inputs. The estimators are the pre-registered ones and are correctly applied.

## B. Findings

### F1 (P1): H-HOLD is presented as a pre-registered FAIL, but under protocol s.4 item 6 it is not scorable

**Evidence.**
- PROTOCOL s.4 item 6: "Holdings: if span F1 between annotators is below 0.6, the guideline is revised and re-annotated before scoring." The rule has no exception and no owner-override clause.
- Measured span F1 is 0.5661. Neither revision nor re-annotation happened.
- A second precondition also failed (PD-01). Interim guide v1.1 forbade annotation until a substantive guideline existed.
- The working definition the adjudicator, and later the evaluator, applied was written after the A3 freeze. It is effectively a revised guideline, but it was never re-annotated by two coders.
- The coordinator's decision to score anyway changes the protocol in effect. It was made without a new version or a s.10 entry. Under the protocol header, such a change cannot produce a pre-registered headline.
- RESULTS s.1 is titled "Headline (pre-registered rule, PROTOCOL s.6)". Its table s.1.3 nevertheless gives H-HOLD "Status NOT_MET, Target **FAIL**", and s.9 and "Overall" repeat FAIL as a protocol outcome.
- D-7 discloses the breach well. But it says the figures were "scored as instructed", and the headline still carries a protocol status.

**What the protocol says.** H-HOLD has no pre-registered status in C13. The figures may be reported only as **descriptive results obtained under a protocol deviation**, that is post-hoc. This covers both recall and the true precision from blind adjudication: the s.4 item 6 rule gates "scoring", not just recall. A3's precision is still clearly below 0.80 descriptively: the CP upper bound is 0.50, and my sub-adjudication (F5) points slightly lower. That is a factual statement, not a protocol FAIL. Recall (0.52 [0.42, 0.61]) is uninformative against 0.60 because it depends on the definition (s.5.1).

**Required fix.**
1. In s.1.3, s.9 and "Overall", replace the H-HOLD status with `NOT SCORABLE UNDER PROTOCOL v1.1 (s.4 item 6: span F1 0.566 < 0.6, no re-annotation; PD-01)`.
2. Move the H-HOLD table out of the "pre-registered" headline into a section labelled "Descriptive, protocol deviation (not a protocol result)". Keep the numbers and intervals.
3. Reword the conclusion along these lines: "A3: no protocol verdict is possible. Descriptively, adjudicated precision is 0.36 [0.24, 0.50], far below the 0.80 milestone, and recall cannot be interpreted against 0.60."
4. Reword "Overall" to: "A2 NOT_MET on all four targets. A3 not scorable under the protocol. A5 descriptive (no target)."
5. Record a protocol-deviation entry for the owner. Achieving a scorable H-HOLD needs a committed substantive guideline and two fresh coders before the next A3 freeze.

### F2 (P2): the composition of H-HOLD gold is not disclosed: most gold holdings are one AI adjudicator's own coding under the post-freeze definition

**Evidence.**
- `ADJUDICATION_RESULT.csv` `agrees_with`: NEITHER 55, X 14, Y 10 of 79 adjudicated items.
- Among the 183 scored gold `holding` units:
  - 113 (62%) come from items where the adjudicator matched **neither** coder;
  - 42 from X/Y choices;
  - only 28 from items on which both coders agreed.
- `ASSIGNMENT_LOG.md` records the counts. RESULTS never mentions NEITHER, and D-1/D-2 do not state the consequence: the recall reference is mainly a single AI instance's annotation under a definition neither coder used.

**Required fix.** Add to D-2 (or s.4.2) the NEITHER count and the 113/183 share. State that H-HOLD recall is measured mostly against single-annotator gold.

### F3 (P2): the A5 author's text exposure on four H-REL judgments is not disclosed or analysed

**Evidence.**
- `C13-A5-GRAPH/freeze/FREEZE_RECORD_C13_A5.md` statement item 3: during the review fixes the A5 author printed or saw text from other pages of JK-f7c70c98230234f6, JK-4d86990aad309acd, JK-88a22c0473110afc and JK-aac99e3e5fbad324. The holdout page itself was not viewed.
- Only JK-4d86990aad309acd is in `PRE_EXPOSED_SUBSET.csv` (as NEAR_IDENTICAL_SPENT_SIBLING).
- RESULTS D-3 reports A5 reading identifier columns, but not this text exposure. The coordinator's log also omits it.
- My sensitivity run with the harness (PRIMARY plus these four, 11 items excluded) gives relation_type precision 0.341 [0.151, 0.579] (56/167) and target precision 0.616. Compare 0.340 full and 0.347 without PRIMARY. The difference is not material.

**Required fix.**
1. Add the exposure to D-3 and the log, with the sensitivity figures above.
2. Ask A0 to register these judgments as author-exposed for future cycles. The registered subset is not changed retroactively.

### F4 (P2): A5 per-type recall is not reported with intervals; the rare-type label is misapplied

**Evidence.**
- PROTOCOL s.1 says, for relations: "Precision and recall per edge type with intervals are reported". s.8 says "per type for relations".
- RESULTS gives per-gold-type recall only as unweighted counts, labelled "supplementary". That includes `follows` (154 gold units) and `cites` (105), which are the common types, not rare ones.
- The rare-type rule (s.3: "Rare types (overrules, distinguishes) get counts only") names `overrules` and `distinguishes`, not `follows`.
- RESULTS calls predicted `follows` (6 answered) "Counts only: rare type" while also printing a weighted estimate and CP interval for it. That is internally inconsistent and not what the rule says.
- The protocol is otherwise met:
  - `overrules` (none coded or predicted) and `distinguishes` (0/53) are correctly counts-only;
  - a descriptive-only A5 report is correct, because there is no owner target and the harness emits `NO_TARGET`.

**Required fix.**
1. Report recall for each gold type except `overrules` and `distinguishes`: the weighted estimate and design-CP interval from the harness estimator, plus the unweighted figure with its Wilson interval. Label all of them descriptive; weighted recall is descriptive only because the Kish design effect is 7.5.
2. Drop "rare type" from `follows`. Note instead that only 6 units were predicted, which is why the interval is wide.

### F5 (P3): A3 true precision rests on a single AI adjudicator; my sub-adjudication

**Evidence.**
- **Sample.** I drew 25 of the 100 sampled predictions by the lowest `sha256("C13-GA4-REVIEW-SUBADJ|"+pred_id)` (`repro/SUBSAMPLE_IDS.txt`). They come from 20 judgments.
- **Source.** I downloaded the 20 source PDFs from HF `hariomahlawat/mimamsa-corpus` at `5524c3d99b6a…` (all 20 were present there) and sha256-verified each against `rep_sha256`.
- **Labelling.** I labelled each prediction blind to the evaluator's per-row labels, under `DEFINITION_APPLIED.md` and `ADJUDICATION_RULES.md`. I had seen only the evaluator's aggregate counts.
- **Agreement:** 21/25 = 0.84 (Wilson 95% about [0.65, 0.94]); Cohen's kappa 0.57.
  - Both CORRECT: 4. Both INCORRECT: 17.
  - All 4 disagreements are cases I had flagged as borderline before comparing:
    - #3: a back-wages relief determination;
    - #12: a bare "Question No. 5 is answered in the negative";
    - #17: "it has been held in Bijender Singh… relevant paras are as under";
    - #13: a statement of certiorari limits.
  - In 3 of the 4, the evaluator said CORRECT where I said INCORRECT.
- **Effect.** On this subsample the evaluator found 7 correct and I found 5. Substituting my labels would lower unweighted precision by about 0.02, to about 0.34. The conclusion is unchanged.
- **Labels file:** `repro/SUBADJ_GA4_REVIEW.csv`.
- **Hand-check of the remaining 21.** Fact-finding, operative, recital and fragment rejections were all clear-cut in the source.

**Required fix.**
1. Report this second-adjudicator agreement (0.84, kappa 0.57, n = 25) beside the A3 precision.
2. State that the borderline categories (relief determinations, bare answers to framed questions, precedent statements introducing a quotation) are where adjudicators diverge.
3. Before any A3 figure is used beyond research, have all 100 double-adjudicated, preferably by a human.

### F6 (P3): the explanation of unweighted 0.623 vs weighted 0.833 coverage is incomplete

**Evidence.**
- RESULTS s.4.1: "Three batch judgments … account for 101 of them. … Because of this, unweighted coverage (0.62) is far below weighted coverage (0.83)."
- Concentration explains why the unweighted figure is low. The gap itself comes from the **design weights**:
  - the three items are in oversampled cells: HO13-0c887610a7 is SC, weight 1.43; HO13-a1438df4ca is PH BATCH, 5.14; HO13-ee7912d06f is DEL BATCH, 3.57;
  - by contrast, many single-proceeding DEL/PH items carry weights of 21.6–27.9;
  - the three items hold 23.6% of unweighted determinable units but only 9.3% of weighted ones.
- Removing them leaves a gap of 0.911 (weighted) vs 0.801 (unweighted). The rest comes mainly from the Supreme Court, which is oversampled (weights 1.0–2.1) and has coverage of 0.39. Excluding SC as well gives 0.925 vs 0.859.
- This matters because the s.6.4 met rule requires **both** figures to reach the target.

**Required fix.** Rewrite the sentence to say the following.
1. The weighted figure down-weights the oversampled batch and SC cells, where most misses fall.
2. The unweighted figure reflects the sample composition, not the population.
3. Both figures are binding for status.

Give the numbers above.

### F7 (P3): the "PASS" rule in s.1.1 misstates the protocol

**Evidence.**
- RESULTS s.1.1: "a target passes only at `MET_LOWER_BOUND`".
- PROTOCOL s.6.4 and s.1 define three statuses and leave it to the owner whether `MET_POINT_ONLY` is enough for candidate display. The protocol defines no "PASS".
- No status changes, because every A2 cell is NOT_MET, so "FAIL" for NOT_MET is fair.

**Required fix.**
1. Describe the outcome as "status NOT_MET (target not met)".
2. Remove the PASS definition, or state that sufficiency of `MET_POINT_ONLY` is an owner decision.

### F8 (P3): "the precision failure holds under every definition tried" is overstated

**Evidence.**
- Variants S0–S4 in s.5.1 are reference-match precisions, which are lower bounds by construction (s.5) and so cannot show failure.
- Adjudicated precision was measured under one definition only, plus the restatement sensitivity.
- The conclusion is probably right: the upper bound is 0.50, and F5 agrees. But the wording claims more than was tested.

**Required fix.** Say: "Adjudicated precision under the applied definition is 0.36 [0.24, 0.50]. Counting restatements as incorrect gives 0.36. Reference-match lower bounds are 0.16–0.33 under all gold variants."

### F9 (P3): minor wording and accuracy points

1. **s.4.1, without CASE_NUMBER_REVIEWED.** "All four are NOT_MET, because the unweighted coverage of 0.733 is below target." That reason applies to printed_disposal coverage only. The precision cells are NOT_MET because the point estimates are below 0.95.
2. **D-3.** "Exposure is to identity and design-cell membership only." The freeze records show identifier columns only: `judgment_key`, `rep_sha256`, `rep_doc_id` and `page`, plus A5's `ITEM_MAP.csv`. The exposure is holdout membership and item mapping, not design cells.
3. **s.4.5 second-coverage figure.** RESULTS.json carries it for H-REL, but RESULTS_C13.md does not report it. The harness has no counterpart for holdings recall; note it as not produced.

**Fix:** correct the wording.

### F10 (P3, for the A0 owner; not an evaluator error)

**Evidence.**
- `aggregate()` and `aggregate_holdings()` drop UNCODABLE and sensitivity-excluded items from the unit list instead of keeping them as zero-domain clusters.
- `linearized_ratio_variance` then computes N_h = w·n_h from the reduced count, so the FPC and the between-cluster variance are slightly off.
- The coverage simulation did not include this case. The effect is small: n_eff is capped by Kish in most cells.

**Required fix.** For the next protocol version, keep excluded items as zero rows for the variance, or validate the current behaviour in `c13_ci_sim.py`.

## C. Answers to the specific questions

1. **Reproduction.** Matched byte-for-byte for all three holdouts and the restatement sensitivity, with identical input hashes. All three freezes descend from the registration commits `d3a1bb0a` and `5e07e010`, and from `f1d61f71`.
2. **Protocol compliance.**
   - Weighting, the design-effect CP interval and the lower-bound met rule are correct.
   - The reserve rule (FULL_OPEN, 113, recomputed weights) is correct.
   - The pre-exposed exclusion and the worse-of headline are correct.
   - Abstention and coverage definitions are correct.
   - **H-HOLD should not have a protocol status.** Under s.4 item 6 it is not scorable. The figures are descriptive or post-hoc only (F1).
3. **A3 sub-adjudication.** 21/25 = 84% agreement, kappa 0.57. The disagreements are all borderline. My labels would give slightly lower precision (F5).
4. **Honest reporting.**
   - Measured and estimated figures are kept apart (s.8), and the post-hoc analyses are labelled.
   - The deviations disclosed are thorough, with two exceptions: the gold provenance (F2) and the A5 text exposure (F3).
   - The H-HOLD "FAIL" overstates the protocol standing (F1), and "every definition" overstates the test (F8).
   - The coverage-gap explanation is incomplete (F6).
   - A2 conclusions are accurate and neither overstated nor understated.
5. **A5.** A descriptive-only report is correct under s.1. The rare-type rule is correctly applied to `overrules` and `distinguishes`. Per-type recall with intervals is missing, and `follows` is mislabelled as a rare type (F4).

## D. Verdict

**ACCEPT WITH CONDITIONS.**
- The A2 results are reproduced exactly, are protocol-compliant, and stand: NOT_MET on all four targets.
- The A5 descriptive results stand.

Conditions before RESULTS_C13 is final:
- **F1 (P1):** re-label H-HOLD as not scorable under protocol v1.1, with its figures reported as descriptive results under a deviation.
- **F2–F4 (P2):** disclose the gold provenance and the A5 exposure, and add A5 per-type recall with intervals.
- **F5–F9 (P3):** fix where convenient.

The descriptive finding that A3 precision is far below 0.80 is robust to my independent check.
