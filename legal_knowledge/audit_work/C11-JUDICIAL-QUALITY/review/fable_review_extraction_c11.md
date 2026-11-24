# Review of C11 extraction v2 and the blinded-holdout scoring

Reviewer: Fable 5.2 (claude-fable-5-2). AI documentary review, not legal validation.
Date: 2026-11-24. Scope: `C11-JUDICIAL-QUALITY/extraction/`, `evaluation/`, `holdout/`, `tools/eval_holdout_c11.py` at commit b6340e20. Source texts: `/home/user/c7` at ad77758d.
Nothing under the reviewed tree was changed and nothing was committed. Working files are in `scratchpad/rev_ext/`.

## Verdict

**ACCEPT the evaluation's conclusion; do not accept the outputs for unreviewed use.**

- The coordinator's verdict is right: outcome precision is below the 95% bar under every reading of the ground truth. Outcomes stay `AUTOMATED_CANDIDATE_NOT_VERIFIED`.
- The 84.1% figure is arithmetically right, but it is unweighted, single-coded, and compared with baselines on an unfair rule. Corrected figures are below.
- One P1: batch judgments stored under many judgment_ids carry one replicated outcome, and at least four of those rows are wrong for the petition they are filed under.
- Propositions are verbatim and correctly pinpointed, but they find about one in eight of the holdings a blind reviewer picked, and origin labels are not precise enough to filter on.

## 1. Reproducibility

| Check | Result |
| --- | --- |
| `python3.11 -I tools/extract_v2.py check` | CHECK PASS: 3,936 judgments, 3,948 rows, 51,250 propositions; batches 0 and 19 re-extracted byte-identical |
| `python3.11 -I -B -m unittest discover -s tests` | 25 tests pass |
| `python -I -B tools/eval_holdout_c11.py --check` | both evaluation files reproduce |
| Tool hashes in the report | `3b48c768…` = `v2core.py`, `7311513f…` = `extract_v2.py`; both match the files and `OUTPUT_SHA256SUMS` |
| Re-extraction of the 56 holdout ids into a temp dir | `OUTCOMES_V2.csv` byte-identical to `evaluation/holdout_predictions/`; the 56 rows also equal the corpus-run rows |
| Holdout leakage into tools | no holdout judgment_id, sha or doc_id in tools, tests or `dev_gold.json` |

The freeze-before-prediction and never-opened-the-holdout claims cannot be proved from the artifacts (F09). File times are consistent with them (tools last edited 05:04 and 05:11, predictions written 05:18), but the ground truth had existed since 02:23 and everything is in one commit.

## 2. Holdout scoring

### The count

My independent re-score from the ground truth and predictions gives the same result on all 56 judgments: 37 correct, 7 incorrect, 11 abstained, 1 not scorable.

| Measure | Value | 95% interval |
| --- | --- | --- |
| Strict, as reported | 37/44 = 84.1% | one-sided lower 73.1%; two-sided 70.6% to 92.1% |
| Printed-words convention (H021, H026, H027 counted correct) | 40/44 = 90.9% | 78.8% to 96.4% |
| Outcome-family level | 38/44 = 86.4% | 73.3% to 93.6% |
| Post-stratified to the 3,862-judgment population | about 78.9% | cells of 2 to 8, indicative only |
| Coverage | 45/56 = 80.4% unweighted; about 87% weighted | |

### Source checks

- **The 7 errors:** all confirmed against the text. Four are extractor errors on any convention (H010, H011, H012, H042). Three depend on whether the label follows the printed words or the substance (H021, H026, H027).
- **10 sampled CORRECT rows** (lowest sha256 of `C11-OUT-REV` + holdout id: H003, H004, H016, H017, H025, H037, H043, H045, H052, H056): 10/10 confirmed. I also read H005, H008, H013 and H019.
- **The 11 abstentions:** all are real `OUTCOME_UNVERIFIED` rows. In six the text prints a plain disposing sentence that v2 declined to use (H002, H006, H014, H034, H047, H055); the rest have no formal disposal words, a garbled text layer, or a separate opinion at the end.

### Problems with the evaluation

1. **Single-coded ground truth (F02).** Reviewer A did H001 to H028 and reviewer B did H029 to H056. No judgment was read twice, so there are no reviewer disagreements to report and no agreement rate. The two reviewers also coded differently: A coded substance where the court printed only "disposed of"; B coded the printed words (H034).
2. **Unweighted sample (F03).** The Supreme Court is 36% of the sample and 8% of the population; Delhi is 14% of the sample and 42% of the population, and Delhi scored 4/7.
3. **Unfair baselines (F04).** The baseline rule needs an exact label match, which the crawler's four-word vocabulary can never give for `disposed_of_with_directions` or `transferred`. By outcome family the crawler is 33/44 = 75.0% (not 63.6%) and the Cycle 10 extractor 31/48 = 64.6% (not 52.1%), against 38/44 = 86.4% for v2. v2 is still ahead, but the intervals overlap.
4. **Proceeding labels are not tested (F10)** when all proceedings were decided alike. H013 has a row for one of two appeals.

### Ground-truth rows I would query

None is changed, and none moves the count off 37/44 unless the convention changes (F12): H027, H021, H026 (convention), H010 (two appeals coded differently under one sentence), H012 (an appeal coded partly allowed while its merits stay pending), H019 (coded "other" though the court prints "disposed of in terms of this judgment").

## 3. Propositions (new measurement)

### Verbatim and pinpoint

All 51,250 excerpts equal the text at `char_start`-`char_end` (whitespace squashed, 700-character cap), and every `page` equals the page marker in force at `char_start`. 6,543 spans cross a page break and can carry running headers or signature stamps.

### Origin-label precision

Sample: 100 candidates from judgments outside the 50 dev judgments and the 56 holdout judgments, lowest sha256 of `C11-PROP-REV` + candidate id. The file has no candidate id, so I used `judgment_id:char_start-char_end`, which is unique. "Correct" means the sentence really has that origin when read in its paragraph.

| Label | Correct | Precision | Wilson 95% |
| --- | --- | --- | --- |
| COURT_HOLDING_CANDIDATE | 37/40 | 92.5% | 80.1% to 97.4% |
| COURT_REASONING_CANDIDATE | 17/20 | 85.0% | 64.0% to 94.8% |
| QUOTED_PRECEDENT | 11/15 | 73.3% | 48.0% to 89.1% |
| PARTY_SUBMISSION | 8/10 | 80.0% | 49.0% to 94.3% |
| EDITORIAL_HEADNOTE | 10/10 | 100% | 72.2% to 100% |
| LOWER_COURT_FINDING | 3/5 | 60.0% | 23.1% to 88.2% |

- For the two court labels "correct" means this bench's own voice. It does not mean the sentence is a holding: CHC29 is "We have considered the submissions", and CHC19 and CHC37 sit in separate opinions.
- The six wrong court labels: three are inside quotations (CHC02, CHC20, CRC12), one is headnote text (CRC10), one is a party statement (CRC16), one is a cover block (CHC26).
- Six of the 40 holding candidates come from one 260-page J&K batch text stored under several judgment_ids, and two are the same span (CHC36, CHC39). The effective sample is smaller than 40.
- `attributed_to` was wrong or garbled in 4 of the 5 QUOTED_PRECEDENT rows that had a value.

### Recall against the blind ground-truth holdings

133 distinct holdings recorded by the reviewers in 52 holdout judgments; 130 can be located in the text layer. A match needs the same page (within one) and at least 40 characters of common text.

| Matched to | Recall | Wilson 95% |
| --- | --- | --- |
| a COURT_HOLDING or COURT_REASONING candidate | 16/133 = 12.0% | 7.5% to 18.6% |
| a candidate of any origin | 50/133 = 37.6% | 29.8% to 46.1% |

Ignoring the page condition moves the first figure to 17/133. Only 14 of 52 judgments have any holding matched. Most misses are plain declarative sentences with none of the court-voice phrases the extractor looks for; 29 were captured but labelled OTHER_OR_UNCERTAIN.

## 4. Outcomes beyond the holdout

Sample from `CRAWLER_DISAGREEMENT_ANALYSIS.csv`, excluding dev and holdout, lowest sha256 of `C11-DIS-REV` + doc_id.

| v2 sides with | Checked | v2 matches the printed disposition |
| --- | --- | --- |
| crawler | 20 | 20 |
| old extractor | 10 | 10 |

This is narrower than it looks: 18 of the 20 crawler-side rows are P&H orders, most on one template, where the old extractor picked up "pending applications disposed of". DO06 prints "allowed" with restricted relief, so the crawler's `partly_allowed` is defensible on substance.

The check also surfaced the P1. The J&K batch judgment of 03.11.2025 (H042) is stored once per petition. v2 gives 34 of those copies `dismissed`, including the copies filed under WP(C) 1319/2024 and 1708/2024 (allowed), 1653/2024 (partly allowed) and 2301/2024 (AFT order set aside). In all, 62 text blobs are shared by 292 judgment_ids.

## Findings

| Id | Severity | Finding |
| --- | --- | --- |
| F01 | P1 | Batch text stored under many judgment_ids gets one replicated outcome; at least 4 rows wrong; holdout counts a batch once |
| F02 | P2 | Ground truth is single-coded; reviewers A and B used different conventions |
| F03 | P2 | 84.1% is unweighted; about 79% when weighted to the population |
| F04 | P2 | Baselines scored on exact labels their vocabulary cannot produce |
| F05 | P2 | "Partly succeeds" read as allowed; one extent-qualified allowance not abstained |
| F06 | P2 | Holding recall 12.0% against blind ground truth |
| F07 | P2 | Origin labels not precise enough to filter on; `attributed_to` unreliable |
| F08 | P2 | Court's own sentence after a closing quote treated as quoted |
| F09 | P3 | Blinding and freeze not verifiable from artifacts; no leakage found |
| F10 | P3 | Proceeding labels unreliable and untested |
| F11 | P3 | Some abstain reasons and excerpts are inaccurate or noisy |
| F12 | P3 | Six ground-truth rows to adjudicate |
| F13 | INFO | Reproducibility holds |
| F14 | INFO | Strict figure and scoring confirmed |
| F15 | INFO | 30/30 on sampled disagreements |
| F16 | INFO | All excerpts verbatim at their offsets |

Evidence and requested actions are in the findings CSV.

## Files

- `fable_review_extraction_c11_findings.csv`: id, severity, statement, evidence, requested action.
- `fable_review_extraction_c11_items.csv`: 186 per-item rows (56 holdout judgments, 100 propositions, 30 disagreement rows).
- `fable_review_extraction_c11_recall_rows.csv`: the 133 ground-truth holdings with match result.

## Limits of this review

- One AI reviewer; no legal validation. Outcome checks compare labels with the printed operative words in the text layer; PDFs were not opened.
- For 24 of the 56 holdout judgments I re-scored from ground truth and prediction only, without opening the source.
- Proposition labels were judged from about 500 characters of context on each side, and the two small classes (10 and 5 items) have wide intervals.
- The recall matcher is textual; a holding paraphrased by the reviewer rather than excerpted would be missed. 130 of 133 excerpts were found verbatim in the text layer, so this is a small effect.
