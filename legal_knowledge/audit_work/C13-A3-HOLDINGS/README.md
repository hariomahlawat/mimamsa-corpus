# C13-A3: holdings and legal-proposition extraction, redesign (`c13-holdings`)

**Status: candidate, PREPARED BUT NOT FROZEN.** Freeze waits for the coordinator's confirmation that A0 (H-HOLD-C13) is accepted (`FREEZE_CANDIDATE.json`).
Every item is `AUTOMATED_CANDIDATE_NOT_VERIFIED` / `NOT_VERIFIED_RATIO_NOT_DETERMINED`. No item is a verified ratio. No overruling or other treatment is inferred. This is not legal validation.

## Headline (read this first)

| | c12-holdings/1.0.0 | c13 (this work) | Basis |
| --- | --- | --- | --- |
| Holding precision | 41.7% (blind, adjudicated) | **about 50% (20/40, Wilson 35-65%)** | Developer hand-check of a seeded sample of 40 holdings from 158 SC-scope judgments **not** used in training and not in the fresh set. Taken before the last veto fixes. Not independent |
| Holding recall | 29.3% (blind) | **about 51-60%** | Out-of-fold (grouped 5-fold by judgment) recall of C12-reference and C11-GT holdings at T = 0.6 / 0.5 (`dev_eval/`) |
| Holding recall, in-sample full fit | n/a | 79.7% (C12 ref), 91.0% (C11 GT) | Inflated: the model was trained on these rows |
| Opinion misattribution (items presented as the Court's holding that are from a dissent, minority or split opinion) | 32.6% (159/488) | **6.4% (6/94)** | Developer-built gold for 15 multi-opinion judgments (in-sample) |

**The interim milestone (≥80% precision and ≥60% recall on the fresh set) is not expected to be met.** The best honest estimates are about 50% precision and 50-60% recall. The independent evaluation on H-HOLD-C13 is the only valid test.

## Architecture

```
text layer (c7 @ ad77758d)
  -> layout mask, body, paragraphs, raw quote spans, sentences      (C12 holdings_core.py, reused read-only)
  -> c13_segment.py   hierarchical segmentation
       opinions: e-SCR "Judgment / Name J." cues, author lines, SCR inline / dash forms (incl. mixed case),
                 square-bracket AND parenthesised running headers (judge-name runs), closing ORDER of the court;
                 body start/end corrected from header runs and trailing author lines (multi-opinion reports);
                 roles sole / lead_majority / lead / concurring / separate / dissent / split_opinion / court_order;
                 dissent cues in an opinion's opening OR closing 4,000 chars ("respectful inability to concur",
                 "I am differing", "in view of the majority decision", ...), opposite disposal to the first opinion,
                 split verdicts (two opinions + reference to the Chief Justice / divergent opinions)
       quoted blocks: kind (precedent / statute or document / lower forum / submission) + source attribution
                 (case name, provision, forum) from the introduction
       zones: submissions vs the court's analysis ("We have heard ...", ANALYSIS headings)
       voice per sentence: quotation:<kind> | precedent_report | submission | lower_forum | court
                 (new: "the issue for consideration before this Court was", "There the question was",
                 "The question before this court was", past-tense reports after a case citation, paragraph
                 carry-over until the court pivots, "This submission is clearly misconceived" = court voice,
                 "It was submitted ... that we hold" = submission)
  -> c13_features.py  sparse contextual features (words, bigrams, opening words, C12 signals, voice, opinion role,
                      section, position, distance from end, analysis zone, paragraph position, neighbours)
  -> c13_extract.py   passage classes for EVERY body sentence:
       material_fact | question_of_law | holding | supporting_reasoning | obiter | party_submission |
       quoted_judgment | statutory_quotation | lower_forum_material | operative_direction
       learned heads (holding, question_of_law) for court-voice sentences; deterministic rules for operative
       directions, obiter cues, material facts; post-model vetoes (operative wording, question framing,
       precedent reports, factual recitals, bare rejections); per-opinion floor (best candidate if none)
       item types: holding (court-side opinions), dissent_holding_candidate, split_opinion_holding_candidate,
       question_of_law, obiter, operative_direction; each with opinion_id/author/role/court_status and an anchor
       (page, page_end, char offsets; paragraph only where the opinion has >= 5 numbered paragraphs)
```

No per-opinion cap or rank cut-off (the C12 cap pushed 44 true holdings into `reasoning`).

### Model (`model/`)

- L2 logistic regression (liblinear, class-balanced), binary sparse features, two heads. Chosen C by grouped 5-fold out-of-fold average precision: holding 0.214 (C = 0.03), question_of_law 0.051 (C = 0.01). Positive-unlabelled setting: the references are not exhaustive; explicit negatives (adjudicated / hand-checked non-holdings, reference QoL/reasoning rows) are weighted 3.
- Trained only on spent sets: C12 holdings reference (30), C12 adjudication sample (86), C12 dev hand-check (115), C11 GT A/B. 137 judgments, 52,261 court-voice sentences, 380 positive holding sentences. C10 review_A/B are paraphrases without verbatim excerpts and were not used for training.
- Exported to JSON (`c13_holdings_model.json`, sha256 `fb28209c39a3a215d019ade5ff1356713306005606dd5223a182bd2db631e30a`); extraction needs only the Python standard library. Training: Python 3.11.18, scikit-learn 1.6.1, numpy 2.2.6, scipy 1.15.3, all BSD-3-Clause (`model/requirements-train.txt`). The weights are derived from project data only; no pretrained model is used. Nothing is sent to any external service.
- Thresholds (`model/THRESHOLDS.json`): holding 0.6, question_of_law 0.6, opinion floor 0.3. Chosen from the out-of-fold table as a precision/recall balance; at T = 0.8 the labelled-proxy precision rises only from 76% to 81% while recall falls from 51% to 32%.
- `TRAINING_REPORT.json` (hashes of every label file, the exclusion list, CV grid); `OOF_PREDICTIONS*.jsonl.gz` (out-of-fold probabilities and the sentence texts used by the dev evaluation).

## Fresh-set isolation

`exclusions/EXCLUDE_H_HOLD_C13.txt`: H-HOLD-C13 SAMPLE (75) + RESERVE (38) from `claude/c13-a0-eval@5e07e010` → 111 judgment_ids (see `exclusions/EXCLUSION_NOTE.md` for the mapping and for prior automated contact). No overlap with any training or development set. The exclusion list is passed to training and to the full run. The 28 fresh judgments in SC scope therefore carry `text_status = EXCLUDED` in `outputs/`. The evaluator extracts them with `ids` and no `--exclude-ids`.

## Results

### In-sample development evaluation (`dev_eval/DEV_EVALUATION_C13.md`)

All rows below trained the model, so every figure is in-sample.

| C12 reference (30), primary matcher | c12 (blind for C12) | c13 (in-sample) |
| --- | --- | --- |
| Holding recall | 29.3% (36/123) | 79.7% (98/123); 87.8% including dissent/split candidates |
| QoL recall | 9.1% (7/77) | 61.0% (47/77) |
| Holding precision lower bound vs reference holdings | 18.7% (39/209) | 42.6% (133/312) |
| C12-adjudicated non-holdings still emitted as holding | 35 of 35 (C12 emitted all of them) | 8 of 35; all 25 adjudicated-correct holdings kept |
| C11 GT (134) holding recall, primary matcher | 45.5% | 91.0% |

Out-of-fold sentence-level estimate (vetoes applied; opinion floor not emulated):

| T | per judgment | Proxy precision (labelled sentences only) | Recall of reference holdings |
| --- | --- | --- | --- |
| 0.5 | 10.3 | 74.2% | 59.9% (154/257) |
| 0.6 | 7.3 | 76.2% | 51.0% (131/257) |
| 0.8 | 3.1 | 80.6% | 31.9% (82/257) |

The proxy precision scores only selected sentences that match a labelled row (about 24%). The developer hand-check below is the better precision estimate.

### Developer hand-check on unseen judgments (`selfcheck/SELFCHECK_SAMPLE.csv`)

- 40 holdings, seed `C13-A3-SELFCHECK-UNSEEN`, drawn from 1,397 holdings in 158 SC-scope judgments that are outside training and the fresh set. Labelled under the C12 adjudication rule (court's own determination; operative lines, recitals, restatements and reasoning steps are not holdings).
- **20/40 correct (50%)**. Errors:
  - operative directions or disposals: 6;
  - non-court material (precedent or lower-forum report, undetected statute quotation): 5;
  - facts: 3;
  - restatements or general observations: 3;
  - reasoning step: 1;
  - span defects: 2.
- The vetoes for operative wording, "In X, this Court held", "the learned judge observed" and costs were then added from this sample. After the fixes, 8 of its 20 errors are no longer emitted and all 20 correct items remain (20/32 on the same sample). That figure is in-sample and is **not** an estimate. Single AI rater, not independent.

### Opinion attribution (`opinion_check/OPINION_ATTRIBUTION_C13.md`)

Gold covers 15 multi-opinion SC judgments, built by the developer (`gold/OPINION_GOLD_C13.csv`, with evidence per row; not independent): Bommai, NJAC, Maneka Gandhi, Supriyo, Sriharan, Aadhaar, Joseph Shine, demonetisation, Madras Bar, Gene Campaign, R.P. Yadav, Dhingra and others.

- Opinions located: 47/48.
- Binding class (court-side vs dissent/minority/split) correct: 39/47.
- Item level: author correct 86.2% (C12 83.2%); presented as the Court's holding although the gold opinion is dissent, minority or split: **6.4% (6/94)**, against C12 32.6% (159/488).

Remaining errors:
- minority opinions with no textual dissent cue (Supriyo CJI/Kaul; Bommai Verma/Ahmadi; demonetisation Nagarathna J; Sriharan Lalit J);
- a concurrence read as a dissent (Supriyo, Narasimha J);
- Sapre J's short opinion missed;
- Aadhaar Chandrachud J not locatable, because the text layer interleaves two opinions' headers.

The A2 plan target of <5% is not met in-sample. In benches of 3 or more, "lead" means the first opinion, with majority status not determined (`court_status = FIRST_OPINION_MAJORITY_NOT_DETERMINED`).

### Full SC-scope run (`outputs/`)

- Scope: 284 judgments (C12 `SCOPE_C12.csv`).
  - 252 read;
  - 28 excluded (fresh set);
  - 4 have no text layer.
- Items: 3,268 in total.

| Item type | Count |
| --- | --- |
| holding | 2,176 |
| question_of_law | 424 |
| operative_direction | 500 |
| obiter | 144 |
| dissent_holding_candidate | 14 |
| split_opinion_holding_candidate | 10 |

- Passages: 97,538 sentences classified into the 10 classes (`PASSAGES_C13.tsv.gz`).
- `holdings_c13.py check` passes under Python 3.11 and 3.13, with byte-identical outputs.

## Commands (Python 3.11+, standard library)

| Command | Purpose |
| --- | --- |
| `python3.11 -I -B tools/holdings_c13.py run --exclude-ids exclusions/EXCLUDE_H_HOLD_C13.txt` | SC-scope run into `outputs/` |
| `python3.11 -I -B tools/holdings_c13.py check` | Tool and model hashes plus byte-identical re-extraction |
| `python3.11 -I -B tools/holdings_c13.py ids --ids-file F --out-dir D [--exclude-ids X] [--all-passages]` | Blind-evaluation entry point |
| `<train venv>/python -B tools/c13_train.py --exclude-ids exclusions/EXCLUDE_H_HOLD_C13.txt` | Retrain (about 25 min on 4 CPUs) |
| `python3.11 -I -B tools/eval_dev_c13.py --pred-ref dev_eval/pred_c12_reference --pred-gt dev_eval/pred_c11_gt --oof model/OOF_PREDICTIONS.jsonl.gz --texts model/OOF_PREDICTIONS_TEXTS.jsonl.gz --out dev_eval/DEV_EVALUATION_C13.md` | In-sample dev evaluation |
| `python3.11 -I -B tools/opinion_check_c13.py --pred opinion_check/pred_opinion_gold --out opinion_check/OPINION_ATTRIBUTION_C13.md` | Opinion attribution check |
| `python3.11 -B -m unittest discover -s tests -p "test_legal_audit_c13_holdings_*.py"` | 17 tests (run from the repo root) |

Suggested scoring for the evaluator: use `item_type == "holding"` for holdings. Report `dissent_holding_candidate` and `split_opinion_holding_candidate` separately: they are never the Court's holding. Compare against `excerpt_clean`.

## Known limitations

- Precision is the main shortfall, at about 50% estimated. Operative directions phrased as entitlements ("shall be entitled ..."), statute text that is not marked as a quotation, and recitals remain the largest error sources.
- The holding labels are positive-unlabelled and come from single annotators. The QoL head is weak (out-of-fold AP 0.05) because reference QoL excerpts are often anchor sentences rather than questions.
- Majority determination in large benches is heuristic, and minority opinions without a textual cue are missed.
- The rules and vetoes were written while reading the spent sets and the self-check sample. All dev figures are in-sample.
- C11 F06 (proposition recall) and F07 (origin labels) are addressed in design. Closure needs the independent fresh-set measurement.
