# PROTOCOL_C13: binding evaluation protocol for Outcome V4, Holdings V2 and graph relations

- **Version:** 1.1 (C13-A0, after the GA0 independent review of `5e07e010`: ACCEPT WITH CONDITIONS; the review is in `reviews/`). Committed before any coding starts and before any C13 extractor is frozen. The holdouts are unchanged; v1.1 changes no draw.
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

**Known limitation for the owner (v1.1; not a target change).** The outcome target stays strict precision ≥ 95% and coverage ≥ 85%. With H-OUT-C13 (300 judgments, weighted n_eff about 127), the stronger status `MET_LOWER_BOUND`, meaning the validated 95% lower bound is itself at least 0.95, is practically reachable only if the true precision is about 0.99 or higher. The simulated probability is about 0.49 at a true precision of 0.98 and about 0.83 at 0.99. A true precision of 0.95–0.97 cannot be distinguished from the target with this sample. Results are therefore reported as `MET_POINT_ONLY`, `MET_LOWER_BOUND` or `NOT_MET`, with the lower bound shown (section 6). This is a limit of what the sample can show; it does not lower or alter the target.

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

  Non-usable records are listed in `outputs/frame/NON_USABLE_POPULATION.csv` and reported as a separate population. **Evaluation results apply to USABLE-text judgments only.** They are never extrapolated to the 89 non-usable judgments (2.4%). Reports must say that the 26 OCR-only (`IMAGE_ONLY`) judgments are excluded **by rule 5, not because they are unreadable**: some have readable OCR text (GA0 F15).
- **Structural strata (sampling stratum, in priority order):**
  - `BATCH_OR_MULTI`: more than one record per judgment or per file, more than one proceeding key in the metadata or cause title, or a connected-matter cue on the first 4,000 characters.
  - `PARTY_SPECIFIC`: a party-differentiated cue in the last 35% of the text. This is a noisy *candidate* signal.
  - `PENSION_OR_DISCIPLINARY`: a C10 topic mentioned at least twice, from the pension or disciplinary sets in `c13_frame.py`.
  - `OTHER`.

  Subject (`PENSION`, `DISCIPLINARY`, `PENSION_AND_DISCIPLINARY`, `OTHER`), year band and `stratum_v3` (the C12 V3 rule reproduced for comparison) are recorded as further columns.

  **Measured accuracy (GA0 review, 40 records read against the texts):** court 40/40, text quality 40/40, structural stratum 24/38 = 63% (95% CI 47–77%; random part 16/22). The errors are:
  - 7 false `PARTY_SPECIFIC`;
  - 3 pension matters labelled `OTHER`;
  - 2 SC multi-proceeding judgments missed, because SC metadata carries no case numbers;
  - 2 false `BATCH_OR_MULTI`, from the AFT OA number in the cause title.

  **The party-specific cue is flagged as noise:** its positive predictive value is about 11% (3/27; 95% CI 4–28%). Strata only define sampling cells, so the weights stay correct for any partition, and every subset result uses gold labels; validity is unaffected and efficiency is lower. The cue and the frame are kept as registered, because the frame hash is part of the holdout provenance. Improved rules are for future frames only.
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
- Overlap between them is allowed and reported: H-OUT/H-HOLD 21, H-OUT/H-REL 32, H-HOLD/H-REL 15 judgments (`HOLDOUT_REGISTRATION.json`; v1.0 said 14 in error).
- Each holdout is coded only for its own task.

**Size justification.**
v1.0 figures, unweighted. Section 3.1 restates them for the weighted headline.

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
  - **Reserve rule:** see section 3.1 (v1.1). Under `GOLD_COUNT_RULE`, at GA2, after both annotators finish and before any extractor output is scored, the reserve opens in rank order, stratum by stratum, only if adjudicated gold holdings are below 234. Inclusion probabilities are then recomputed from the opened `n_h`.
- **H-REL:** coders record every citation on each page, so precision and recall come from the same units. 140 citing pages give about 400 citation instances. v1.0 said common types get about ±7pp at p = 0.8; the weighted figure is about ±9pp (section 3.1). The registered `DESIGN.json` names the types in upper case (`APPLIES, CITES`); the coding vocabulary is lower case (`applies`, `cites`). Rare types (`overrules`, `distinguishes`) get counts only.

### 3.1 What the samples can and cannot show (v1.1, weighted; GA0 F02)

The v1.0 size justification above was unweighted. The headline estimators are weighted, so they carry the Kish design effect of the design weights. All figures below are in `outputs/holdouts/SIZE_RESTATEMENT_V1_1.json` (`tools/c13_power.py`), and the simulated figures are in `outputs/ci_validation/` (`tools/c13_ci_sim.py`). **The sizes are unchanged.**

**H-OUT-C13 (300 judgments).**
- The Kish design effect is 2.00, so the effective n of covered judgments is about 127, not 255.
- The validated 95% interval half-width is about ±3.7pp at a true precision of 0.95 and about ±2.5pp at 0.98 (simulated, uniform precision).
- Per court, the Kish-Wilson half-widths at p = 0.95 are about ±6.1pp (SC), ±7.2–7.8pp (P&H, Delhi), ±8.3pp (Allahabad) and ±9.2pp (J&K).
- **Can show:** the weighted point estimates per field with validated intervals, and whether those point estimates reach 95% and 85% (`MET_POINT_ONLY`).
- **Cannot show (stated to the owner before coding):** `MET_LOWER_BOUND`, meaning a validated lower bound of at least 0.95, is practically reachable only when the true precision is about 0.99 or higher. The simulated probability is about 0.49 at a true 0.98 and about 0.83 at 0.99 under uniform precision, and lower under heterogeneity (0.12–0.14). A true precision of 0.95–0.97 cannot be told apart from the target.
- The v1.0 power figure (253 covered decisions for 80% power at 0.98 against 0.95) holds only for the **unweighted** one-sided test.

**H-HOLD-C13 (75 judgments).**
- The combined design effect is 1.87: Kish 1.49 from the weights times 1.26 from clustering.
- The recall half-width at 0.60 is about ±8.5pp, not ±7pp (simulated mean ±8.4pp).
- Opening the full registered reserve gives 113 judgments and about ±6.7pp (simulated).

**H-REL-C13 (160 pages).**
- The overall Kish design effect is 7.5. The 20 no-detected-citation pages carry very large weights, so weighted overall recall is **descriptive only**.
- Per-type precision on treatment-cue pages is about ±9pp at p = 0.8 (Kish design effect 1.66).

**Pre-registered H-HOLD reserve decision (replaces the v1.0 GA2 gold-count rule only if FULL_OPEN is chosen).**
1. Before the first H-HOLD packet is sent, the coordinator commits `C13-A0-EVAL/decisions/H-HOLD_RESERVE_DECISION.json` with either `FULL_OPEN` or `GOLD_COUNT_RULE`, and the date. This happens before anyone has seen any coding.
   - `FULL_OPEN`: the 38 reserve judgments are coded together with the 75, from packets `outputs/packets/H-HOLD-C13-RESERVE/` (already built). The design becomes 113, with weights recomputed per cell (`load_design(..., reserve_open="all")`, `c13_score.py --reserve-open all`).
   - `GOLD_COUNT_RULE`: the v1.0 rule applies, so the reserve opens at GA2, in rank order per stratum, only if adjudicated gold holdings fall below 234. The opened counts are recorded, and weights are recomputed with `reserve_open={cell: k}`.
2. If no decision is committed before the first packet goes out, `GOLD_COUNT_RULE` applies.

**Recorded decision: `FULL_OPEN`.**
- **File:** `decisions/H-HOLD_RESERVE_DECISION.json`, sha256 `d6d9a96a6695dfd12ed650ae64092d1adf1d239e64bec4845efdbafeb878bc15`.
- **Decided by:** the coordinator, on 2026-11-25.
- **Effect:** H-HOLD-C13 is the 75 registered sample judgments plus all 38 registered reserve judgments, 113 in total. Per-cell n_h, inclusion probabilities and weights are recomputed. The harness applies this by default.
- **Rationale:** the pre-registered precision target of about ±6.7pp. Nothing had been coded or viewed.
- **Timing:** the decision was made before any H-HOLD packet was issued, before any H-HOLD item was coded or read, and before any extractor output on H-HOLD-C13 existed.
- The H-HOLD packets were regenerated with 113 items per coder. The separate reserve packets were withdrawn.
- `GOLD_COUNT_RULE` no longer applies, and no further H-HOLD items can be added.
3. No item is ever added after any coded result or extractor output has been seen, except under `GOLD_COUNT_RULE` as written.

**Party-specific gold units in H-OUT (GA0 F03).**
- 22 H-OUT judgments are in the `PARTY_SPECIFIC` stratum. At the measured PPV, about 2.4 true party-differentiated judgments are expected among them (range 0.9–6.2), plus an unknown, probably small, number from other strata.
- **The party-specific breakdown is therefore DESCRIPTIVE ONLY**: counts and point estimates with intervals, and no pass or fail claim (the harness emits `DESCRIPTIVE_ONLY`).
- The owner's party-specific requirement stays **not demonstrated** by this holdout. This is a stated shortfall, not a met target.

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
4. v1.1 (GA0 F08):
   - the returned-sheet check also scans free-text fields (notes, excerpt, legal issue) for model-only tokens;
   - the other coder's id is mandatory (`--other-coder`).

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
1. `c13_coding.py adjsheet` lists only the items that differ. The codings are shown as X and Y. v1.1 (GA0 F09): which coder is X comes from a **secret per-run seed**, written only into the sealed `ADJUDICATION_KEY.csv`, so the assignment cannot be recomputed from the code.
2. The adjudicator reads the source and decides. `c13_coding.py truth` asserts that the adjudicated items are exactly the differing items (F09).
3. Agreed items take labels from both coders, which are identical. Their page, paragraph and excerpt come from coder A, recorded in `non_label_fields_from` (F03).
4. The reference annotations are stored with `store_version`, giving a versioned directory with coder IDs and a sha256 manifest. `verify` must pass.
5. The scoring harness refuses a truth file that is not in a verified store (`--store`).

### 4.4 Pre-exposed holdout judgments (v1.1; GA0 F04, F06)

`outputs/holdouts/PRE_EXPOSED_SUBSET.csv` (`tools/c13_sensitivity.py`) registers the holdout judgments with prior exposure. A judgment can carry several categories:

| Category | Judgments | Handling |
| --- | --- | --- |
| `CURATED_KB_CONTENT` | 4: JK-76ec35cd7ab232b5, JK-88f84411abdb3028 and JK-05e9484593272fe0 (H-OUT); JK-16dcc07543999d26 (H-HOLD and H-REL) | **Developers of A2/A3/A5 must not consult the curated or KB content (C11 curated 53, C12 curated scope, WS-B holdings register, KB records) for these judgments.** Coders get only the blinded packet |
| `NEAR_IDENTICAL_SPENT_SIBLING` | 16 (shingle containment ≥ 0.90, or ≥ 0.80 on the same date, against a spent judgment) | Template leakage via sibling orders |
| `CASE_NUMBER_REVIEWED` | 27 (C11 SCNUM independent review) | Exposure limited to case-number fields |

**PRIMARY** means `CURATED_KB_CONTENT` or `NEAR_IDENTICAL_SPENT_SIBLING`.
- Every headline figure is reported with and without the PRIMARY subset.
- The outcome headline is also reported without `CASE_NUMBER_REVIEWED`. The harness does both automatically.
- The registered headline is the full-sample figure. A material difference (point estimate moving by more than the validated half-width) is reported as a finding.
- No judgment is dropped or replaced.

### 4.5 Items found uncodable during coding (v1.1; GA0 F05)

1. A coder or the adjudicator who cannot code an item returns one row with `notes = UNCODABLE:<CODE>` and the other coding fields blank. The codes are fixed in `c13_tasks.UNCODABLE_CODES` and the coding guides: SHA_MISMATCH, FILE_UNAVAILABLE, UNREADABLE, CONTENT_MISSING_TRUNCATED, NOT_A_JUDGMENT, MISIDENTIFIED_DOCUMENT, OUT_OF_SCOPE, PAGE_ABSENT, OTHER.
2. The two coders agree on an uncodable item only when both give the same code. Any other combination goes to adjudication.
3. An item whose reference is UNCODABLE **stays in the sample, is never replaced** (the H-HOLD reserve opens only under section 3.1), and is excluded from the scored denominators.
4. It is reported:
   - as the number and share of uncodable items and their codes;
   - as predictions made on uncodable items;
   - in a second coverage figure that counts each uncodable item as one determinable unit not covered (`coverage_counting_uncodable_items_as_not_covered`).
5. Gold `unclear` / `other` units are counted and reported beside coverage as `gold_units_undeterminable`.

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

**Clusters (v1.1, GA0 F10).** The cluster for intervals is always the judgment (`judgment_key`). H-REL pages from one judgment are summed into one cluster within their design cell before variance estimation. Known limitation: H-REL page classing used representative-copy citation records only, so a citation recorded on another copy classes a page `NO_DETECTED_CITATION`. This affects efficiency only.

**Store (v1.1, GA0 F07).** `--store` is mandatory for every real scoring run. Only `--check` runs without it.

**Breakdowns.** Every figure is reported:
- overall;
- per court;
- per structural stratum;
- for outcome, also for gold multi-proceeding judgments (proceeding-specific) and gold party-specific units;
- for relations, also per predicted relation type.

## 6. Estimators, intervals and the "met" rule (v1.1)

1. **Weighted (headline):** the Horvitz–Thompson ratio estimator Σ w·y / Σ w·x, with design weight w = N_h/n_h for the design cell. Domain estimates (per court, per stratum, subsets) keep every sampled item, with zeros outside the domain.
2. **Validated interval (pass rule):** the **design-effect Clopper–Pearson interval** (`c13_stats.design_cp`).
   - It is the exact binomial interval at an effective sample size n_eff = min(Kish n_eff of the denominator; Korn–Graubard n_eff = p̂(1−p̂)/V̂, where V̂ is the Taylor-linearised stratified variance of the ratio, with clusters as PSUs and finite-population correction; n), with k_eff = p̂·n_eff.
   - **Coverage was demonstrated by simulation** (`tools/c13_ci_sim.py`; `outputs/ci_validation/`). The simulation used the registered H-OUT and H-HOLD designs, 1,000 replicates per scenario, multi-unit and all-or-nothing clusters, and uniform and heterogeneous precision.
   - Coverage was ≥ 0.965 for every true precision from 0.90 to 0.99 for outcome, and ≥ 0.954 in every scenario including holdings. The Monte Carlo standard error is 0.007.
   - The v1.0 weighted percentile bootstrap covered only 0.83 at p ≈ 0.98 (GA0 F01). It is still reported, labelled as secondary and **not used for any pass decision**. The Kish-Wilson interval (coverage as low as 0.92 in the simulation) is also reported as secondary only.
3. **Unweighted (alongside):** the pooled proportion with its Wilson 95% interval and an unweighted cluster-bootstrap interval.
4. **Met rule (fixed now):**
   - `MET_POINT_ONLY`: the weighted and the unweighted point estimates both reach the target;
   - `MET_LOWER_BOUND`: also, the **validated design-CP lower bound** reaches the target;
   - otherwise `NOT_MET`.

   Reports show the lower bound beside the point estimate. Section 3.1 states what each status is realistically able to show. The owner decides whether `MET_POINT_ONLY` is enough for candidate display.
5. **Party-specific breakdown:** `DESCRIPTIVE_ONLY`, with no pass status (section 3.1).
6. **Breakdowns (GA0 F12):** the headline status is the overall status per field. A status is also emitted per court, per stratum, for the proceeding-specific subset and for each sensitivity analysis. Whether the target must also be met per court or per breakdown is an **owner decision**. Until the owner decides, breakdown statuses are reported and are not headline claims.
7. What was measured (the coded holdout) is kept separate from what was estimated (population-weighted figures). The weights extrapolate only to the eligible, non-spent, USABLE-text population of section 2.

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
- the target status from section 6, overall and per breakdown;
- the uncodable count and share, the undeterminable gold units, and the sensitivity results without the pre-exposed subsets;
- for H-HOLD, the recorded reserve decision and the design used;
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

### 9.1 Disposition of the GA0 review findings (`reviews/review_c13_a0_5e07e010_findings.csv`)

| Finding | v1.1 handling |
| --- | --- |
| F01 (P2) bootstrap under-coverage | Pass rule moved to the design-effect Clopper–Pearson interval; coverage ≥ 0.95 shown by simulation for p = 0.90–0.99 (section 6); simulation tests in the suite |
| F02 (P2) unweighted size justification | Section 3.1 restates every holdout for the weighted estimators; what the samples cannot show is stated; pre-registered reserve decision; sizes unchanged |
| F03 (P2) party-specific | Breakdown is DESCRIPTIVE_ONLY (harness enforces); cue PPV about 11% recorded and flagged; expected gold count stated |
| F04 (P2) curated/KB pre-exposure | `PRE_EXPOSED_SUBSET.csv`, developer restriction, with/without reporting (section 4.4) |
| F05 (P2) uncodable items | UNCODABLE disposition, never replaced, reported in denominators (section 4.5); guides v1.1 |
| F06 (P3) near-identical siblings | Included in the PRIMARY sensitivity subset |
| F07 (P3) store optional | `--store` mandatory |
| F08 (P3) free-text tokens; optional other coder | Free text scanned; other coder required |
| F09 (P3) recomputable X/Y key | Secret per-run seed in the sealed key |
| F10 (P3) H-REL clusters | Judgment clusters; classing limitation documented |
| F11 (P3) reserve not implemented | `load_design(reserve_open=...)`, reserve packets and item map, tests |
| F12 (P3) breakdown status | Status per breakdown; owner decision recorded as open (section 6.6) |
| F13 (P3) documentation | Overlap 15 and type case corrected (section 3) |
| F14 (P3) stratum accuracy | Measured accuracy recorded (section 2) |
| F15 (P3) OCR-only exclusion | Reporting statement required (section 2) |
| F16 (P3) env var | README states `MIMAMSA_C12_ADDITIONS` is required outside the worktree layout |

## 10. Change log

- 1.0 (2026-11-25): initial version (C13-A0).
- 1.1 (2026-11-25, amended the same day before any coding): H-HOLD reserve decision FULL_OPEN recorded (section 3.1); owner-facing limitation on `MET_LOWER_BOUND` stated in section 1.
- 1.1 (2026-11-25): GA0 review conditions F01–F05 and P3 F06–F16 (section 9.1). Validated interval and met rule; weighted size restatement; party-specific descriptive; pre-exposed subsets; UNCODABLE rule; reserve decision rule; harness and leak-check hardening. No holdout redrawn. Committed before any coding.
