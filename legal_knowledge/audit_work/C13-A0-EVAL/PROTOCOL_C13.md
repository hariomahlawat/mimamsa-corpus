# PROTOCOL_C13: binding evaluation protocol for Outcome V4, Holdings V2 and graph relations

- **Version:** 1.0 (C13-A0). Committed before any C13 extractor is frozen.
- **Binds:** workstreams A2 (Outcome V4), A3 (Holdings V2) and A5 (graph relations). A0 must be independently accepted (gate GA0) before any formal A2 or A3 evaluation.
- **Status of everything scored under this protocol:** `AUTOMATED_CANDIDATE_NOT_VERIFIED`. Meeting a target does not make an output a legal fact or verified knowledge. No result under this protocol authorises an advisory function, BIND, or a legal-status change.
- **Changing this protocol.** Any change needs a new version number, a dated entry in section 10, and a commit that comes **before** the freeze of the extractor it affects. A change made after a freeze applies only to the next freeze. Changes after an evaluator has seen any score are reported as post-hoc and never replace the pre-registered headline figure.

## 1. Targets (as stated by the owner)

| Task | Target | Nature |
| --- | --- | --- |
| Outcome (A2) | **Strict precision ≥ 95% and coverage ≥ 85%, per field** (`printed_disposal`, `substantive_result`). Results must be given court-specific, proceeding-specific, party-specific, with evidence-anchor results, and weighted. | Owner target for candidate display (labelled with measured figures) |
| Holdings (A3) | **Precision ≥ 80% and recall ≥ 60%** on `holding` items | **Interim research milestone only. It is not operational acceptance.** Holdings stay hidden from Users unless the owner decides otherwise (D-08). |
| Relations (A5) | No owner target. Precision and recall per edge type with intervals are reported | Descriptive. Every non-`cites` edge stays `llm_proposed`/`extracted` until a human decision |

Targets are never lowered, re-defined or re-scoped after the holdout is drawn. A shortfall is reported as a shortfall.

## 2. Population and classification frame

- **Frame:** every judicial record in the corpus: the 4,259 judgment records at corpus commit `ad77758d`, the 18 judgments ingested in C12 (HF `15bd03cc`) and the 4 C12 held-original derived records (HF `af7f9d06`). That is **4,281 records, 3,973 files and 3,637 judgments**, built by `tools/c13_features.py` (stage 1, reads the texts) and `tools/c13_frame.py` (stage 2, committed inputs only).
- **Unit of analysis:** the judgment (`judgment_key`, C11 identity register). All copies and records of one judgment are one cluster. Each judgment has one representative copy, chosen deterministically: best text quality, then a valid raw path, then official rendition, then lowest sha256.
- **Text quality (explicit states, nothing dropped):** each state is assigned by the first rule that matches.
  1. `UNREADABLE`: the PDF does not open or its bytes are unavailable.
  2. `TRUNCATED`: the stored copy is truncated and content may be missing.
  3. `GARBLED`: the C12 ingestion test found the text layer unusable.
  4. `IMAGE_ONLY`: no text, or fewer than 200 letters.
  5. `IMAGE_ONLY`: the corpus text is OCR of an image-only PDF.
  6. `GARBLED`: the letter share is below 0.5, or C11 marked the file `NON_READABLE_TEXT_LAYER`, or fewer than 50% of pages are usable. A page is usable when it has at least 200 letters and letters are at least 50% of its non-space characters.
  7. `USABLE`: everything else.

  Non-usable records are listed in `outputs/frame/NON_USABLE_POPULATION.csv` and reported as a separate population. **Evaluation results apply to USABLE-text judgments only.** They are never extrapolated to the 89 non-usable judgments (2.4%).
- **Structural strata (sampling stratum, in priority order):**
  - `BATCH_OR_MULTI`: more than one record per judgment or per file, more than one proceeding key in the metadata or cause title, or a connected-matter cue on the first 4,000 characters.
  - `PARTY_SPECIFIC`: a party-differentiated cue in the last 35% of the text. This is a noisy *candidate* signal.
  - `PENSION_OR_DISCIPLINARY`: a C10 topic mentioned at least twice, from the pension or disciplinary sets in `c13_frame.py`.
  - `OTHER`.

  Subject (`PENSION`, `DISCIPLINARY`, `PENSION_AND_DISCIPLINARY`, `OTHER`), year band and `stratum_v3` (the C12 V3 rule reproduced for comparison) are recorded as further columns.
- **In-scope flag:** `OUT_OF_SCOPE` when C10 relevance is `NOT_RELEVANT_CURRENT_SCOPE`; `UNCERTAIN` for `RELEVANCE_UNCERTAIN_REVIEW`; otherwise `IN_SCOPE`.
- **Eligible for fresh holdouts:** all of the following must hold:
  - USABLE text;
  - raw path valid in a pinned store (the C12 HF hash ledger at `5524c3d9`, or the C12 staged manifest at `15bd03cc`);
  - not `OUT_OF_SCOPE`;
  - not spent;
  - no access marking;
  - court resolved.

  2,812 judgments are eligible. Each ineligible judgment carries its reasons in `FRAME_JUDGMENTS.csv`.
- **Spent sets (`outputs/exclusions/`):** these may be used as development data only.
  - C10 review sets;
  - C11 holdout (56);
  - C11 dev and review item sets;
  - C12 V3 holdout (150);
  - C12 holdings reference (30);
  - C12 extractor dev gold and dev rows (`dev_gold_v3.json` and related);
  - C12 holdings dev (`DEV_IDS.txt` and related).

  In total, 682 judgment keys (679 in the frame) are excluded from every fresh holdout. **Limitation:** the evaluated population is the non-spent eligible frame. The spent judgments, about 19% of the frame, are not represented.

## 3. Fresh holdouts (drawn in A0, not coded, texts not read)

| Holdout | Unit | Size | Design |
| --- | --- | --- | --- |
| **H-OUT-C13** | judgment | **300** | court × structural stratum; SC 70, Delhi 70, P&H 70, J&K 45, Allahabad 45 |
| **H-HOLD-C13** | judgment | **75** (+38 reserve) | SC (multi-opinion cue: all 7 taken; long ≥ 15 pp; shorter) and HC court × length (≥ 15 pp; 5–14 pp) |
| **H-REL-C13** | citing page | **160 pages** | SC/HC × page class: treatment cue 50, resolved citation 50, unresolved-only 40, no detected citation 20 |

**Selection and records.**
- Within each design cell, the lowest `SHA-256(seed|unit)` units are taken. Seeds are fixed in `c13_sampler.py`.
- Each sampled row carries `N_h`, `n_h`, inclusion probability `n_h/N_h` and design weight `N_h/n_h`.
- Shortfalls and reallocations are written into `DESIGN.json` (C12 tools F07). Examples: SC and J&K have one party-specific candidate each; Allahabad has none; J&K and Allahabad have few batch judgments.

**Independence of the three holdouts.**
- The three holdouts are independent probability samples of the same eligible frame.
- Overlap between them is allowed and reported: H-OUT/H-HOLD 21, H-OUT/H-REL 32, H-HOLD/H-REL 14 judgments.
- Each holdout is coded only for its own task.

**Size justification.**
- **H-OUT:** with 85% coverage, 300 judgments give 255 covered judgments.
  - The unweighted Wilson half-width at p = 0.95 is ±2.7pp.
  - Court oversampling gives a Kish design effect of 2.0, so the weighted half-width is ±4.0pp.
  - 253 covered decisions give 80% power to reject precision ≤ 0.95 when the true precision is 0.98 (one-sided, α = 0.05).
  - Per-court unweighted half-widths at p = 0.95: SC/DEL/PH ±6.0pp, J&K/ALL ±7.8pp.
  - Precision close to 0.95 cannot be shown to be ≥ 0.95 by any feasible holdout. Section 6 states how "met" is decided.
- **H-HOLD:**
  - Recall needs an effective n of 185 for ±7pp at 0.60; precision needs 124 for ±7pp at 0.80.
  - The design effect is 1 + (m̄ − 1)·ICC = 1.26, using an ICC of 0.12 estimated on the C12 reference (dev data) and m̄ = 3.14 holdings per judgment.
  - m̄ combines 4.1 per SC judgment, measured on the C12 reference, with 2.5 per HC judgment. **The HC figure is an assumption: no HC holdings reference exists.**
  - This gives 234 gold holdings, about 75 judgments, 40% of them SC.
  - **Reserve rule:** at GA2, after both annotators finish and before any extractor output is scored, the reserve opens in rank order, stratum by stratum, only if adjudicated gold holdings are below 234. Inclusion probabilities are then recomputed from the opened `n_h`.
- **H-REL:** coders record every citation on each page, so precision and recall come from the same units. 140 citing pages give about 400 citation instances. Common types get about ±7pp at p = 0.8. Rare types (`overrules`, `distinguishes`) get counts only.

**Registration.** `outputs/holdouts/HOLDOUT_REGISTRATION.json` and `SHA256SUMS` record the sample hashes. **An extractor freeze commit must be a descendant of the commit that adds these files.** The evaluator verifies this with `git merge-base --is-ancestor <registration commit> <freeze commit>` and reports the result.

## 4. Coding, agreement and adjudication

**Coders.**
1. There are two independent coders per holdout and one adjudicator, all separate instances.
2. Recommended (owner decision D-07): a human legal assistant second-codes a random 20% of H-OUT. The subsample is the first 60 items in coder 1's sheet order.
3. Coders receive only `outputs/packets/<holdout>/<coder_slot>/CODER_SHEET.csv` and the coding guide in `packets/`. The sheet holds opaque item ids, file sha256, raw path, store, the pages to code, and blank fields.
4. Coders never receive strata, weights, inclusion probabilities, court weights, selection reasons, model or extractor output, or the other coder's work.
5. `SAMPLE.csv`, `DESIGN.json` and `ITEM_MAP.csv` are evaluator-only.

**Leakage checks.**
1. `c13_coding.py leakcheck` must pass on every packet before it is sent, and on every returned sheet with `--completed --coder <id> --packet <sheet> --other-coder <id>`.
2. A failure stops the evaluation. Off-vocabulary or blank required labels fail validation; exact labels only (C12 tools F10).
3. Identical long notes between the two coders are reported as evidence on independence (F04). They are not proof either way.

**Agreement.** `c13_coding.py agree` generalises C12 `holdout_v3_agreement_c12.py` and fixes F02.
1. Outcome rows are aligned per proceeding by the C12 `key()`. A unit left unmatched counts as a disagreement.
2. An item is AGREE only when every unit is aligned and every scored field is identical.
3. The tool reports:
   - strict item agreement;
   - strict unit agreement;
   - Cohen's kappa, with and without unmatched units;
   - Krippendorff's alpha (nominal);
   - span F1, for holdings.
4. On the C12 V3 codings, its item-level statuses equal C12 `AGREEMENT.csv` for all 149 locatable items.
5. Agreement is reported **before** any extractor output is scored.
6. Holdings: if span F1 between annotators is below 0.6, the guideline is revised and re-annotated before scoring. This is the plan's proposed threshold.

**Adjudication and reference.**
1. `c13_coding.py adjsheet` lists only the items that differ. The codings are shown as X and Y; which coder is X is decided per item by a seeded hash, and the key is sealed.
2. The adjudicator reads the source and decides. `c13_coding.py truth` asserts that the adjudicated items are exactly the differing items (F09).
3. Agreed items take labels from both coders, which are identical. Their page, paragraph and excerpt come from coder A, recorded in `non_label_fields_from` (F03).
4. The reference annotations are stored with `store_version`, giving a versioned directory with coder IDs and a sha256 manifest. `verify` must pass.
5. The scoring harness refuses a truth file that is not in a verified store (`--store`).

## 5. Scoring (pre-registered harness `tools/c13_score.py`)

**Outcome and relations** (keyed units).
1. Gold and predicted units are aligned per item:
   - outcome: proceeding key; a single row on each side aligns directly;
   - relations: page plus normalised citation key.
2. For each scored field:
   - **answered** means the prediction is non-empty and not in {ABSTAIN, ABSTAINED, OUTCOME_UNVERIFIED, unclear};
   - **determinable** means the gold label is not `unclear` or `other`.
3. Strict precision is the number of answered units whose label equals gold, divided by all answered units. A prediction on an extra unit with no gold, or on an undeterminable gold unit, counts as incorrect.
4. Family precision is the same with C12 label families. Coverage is the number of determinable gold units answered, divided by all determinable gold units.
5. Failure categories:
   - CORRECT;
   - WRONG_LABEL_SAME_FAMILY;
   - WRONG_FAMILY;
   - PRED_ON_UNDETERMINABLE;
   - EXTRA_UNIT_NO_GOLD;
   - MISSED;
   - ABSTAINED;
   - GOLD_UNDETERMINABLE_NO_PRED.

**Holdings** (spans).
- Spans are matched with the C12 primary matcher: at least 3 shared content tokens, overlap/min ≥ 0.60, and pages no more than 1 apart.
- Recall counts gold `holding` spans matched by a `holding` prediction. It is reported pooled and as a judgment-level macro figure.
- **True precision comes from blind adjudication** of all predicted `holding` items, or a seeded sample of at least 100, in H-HOLD.
- Reference-match precision is reported only as a LOWER BOUND.
- Strict scoring also requires the item type to match and the opinion family (majority vs other opinion) to match.

**Evidence anchors.** The predicted excerpt (whitespace and quotes normalised; first 120 characters) must occur on the predicted page of the representative copy. The statuses are ANCHOR_OK, ANCHOR_WRONG_PAGE, ANCHOR_NOT_FOUND and NO_ANCHOR.

**Breakdowns.** Every figure is reported:
- overall;
- per court;
- per structural stratum;
- for outcome, also for gold multi-proceeding judgments (proceeding-specific) and gold party-specific units;
- for relations, also per predicted relation type.

## 6. Estimators, intervals and the "met" rule

- **Weighted (headline):** Horvitz–Thompson ratio estimator, Σ w·y / Σ w·x, with the design weight w = N_h/n_h for the court × stratum design cell. Intervals:
  - stratified judgment-cluster bootstrap: clusters resampled within design cells, 2,000 replicates, seeded, percentile 95%;
  - Wilson interval using the Kish effective n.
- **Unweighted (alongside):** pooled proportion with a Wilson 95% interval and an unweighted cluster-bootstrap interval.
- **Met rule (fixed now):**
  - `MET_POINT_ONLY`: the weighted and the unweighted point estimates both reach the target;
  - `MET_LOWER_BOUND`: also, the weighted bootstrap lower bound reaches the target;
  - otherwise `NOT_MET`.

  Reports state the status and show the lower bound beside the point estimate. The owner decides whether `MET_POINT_ONLY` is enough for candidate display.
- What was measured (coded holdout) is kept separate from what was estimated (population-weighted figures). The weights extrapolate only to the eligible, non-spent, USABLE-text population of section 2.

## 7. Sequence (gates)

1. **GA0:** A0 infrastructure is independently accepted. No formal A2 or A3 sampling or evaluation happens before this.
2. **GA1:** the A2, A3 and A5 task protocols (this file plus any task addendum) and the scoring tool are committed. The holdouts are registered (done in A0).
3. **GA2:**
   - coding is complete;
   - leak checks pass;
   - agreement is reported;
   - adjudication is done;
   - the reference is stored and versioned;
   - the H-HOLD reserve decision is recorded.
4. **GA3:** the extractor is frozen, with the tool and output hashes recorded. The freeze commit descends from the holdout registration.
5. **GA4:** an independent evaluator, not the extractor author and not a coder, runs `c13_score.py` on the frozen predictions and writes RESULTS. An independent reviewer checks it.

Holdout texts are never read for development. Extractor authors work only on dev and spent sets. Any suspected contamination is reported and the affected items are listed. They are not silently dropped.

## 8. Reporting requirements

Every RESULTS file must give:
- strict and family precision, coverage or recall, abstentions, and the failure taxonomy;
- weighted and unweighted figures, each with its intervals;
- per court, per stratum, the proceeding-specific and party-specific subsets for outcome, and per type for relations;
- evidence-anchor rates;
- the target status from section 6;
- the input hashes (truth, predictions, harness);
- the annotation store version and coder IDs;
- the freeze and registration commits.

Shortfalls are stated plainly. No post-hoc change is made to headline figures.

## 9. Disposition of C12 coordinator-tools findings in A0 (for independent confirmation)

| Finding | A0 handling |
| --- | --- |
| F02 proceeding-level agreement | `agreement()` aligns per proceeding; unmatched units disagree; test with a swapped-labels case and the C12 data |
| F03 unadjudicated agreed rows; source of non-label fields | `build_truth()` uses AGREE only on strict unit agreement; documents `non_label_fields_from` |
| F04 coder independence not evidenced | Packets have per-coder order; `leakcheck --completed` refuses cross-coder content; `independence_report()` flags identical notes. Independence still rests on process: separate instances and assignment logs must be kept by the coordinator |
| F05 text layer not enforced | `assert_drawable()` refuses non-USABLE units (tests) |
| F06 raw_path not validated | Raw path validated against pinned stores; `NOT_FOUND` units refused (tests) |
| F07 stratum hint in coder view; silent reallocation | Coder sheets carry no stratum or weight (leak check and tests); reallocations recorded in `DESIGN.json` |
| F08 scnum reconfirmation branch | **Not addressed in A0.** It concerns `scnum_overlay_c12.py` (C12 frozen tool, SC case-number overlay), not evaluation tooling. It needs a disposition by its owner (A4/A5 identity work) |
| F09 adjudication coverage | `build_truth()` asserts set equality (tests) |
| F10 lenient labels | Exact vocabularies; blank or off-vocabulary labels fail (tests) |

## 10. Change log

- 1.0 (2026-11-25): initial version (C13-A0).
