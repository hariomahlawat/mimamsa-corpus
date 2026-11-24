# Independent review: V3 outcome-extractor holdout evaluation (C12 WS-D)

Reviewer: independent agent. I did not write the V3 extractor, the ground truth or the evaluation.
Worktree: `c12w`, branch `claude/c12-consolidation`, HEAD `cade4c99`. Read-only: I made no commits and changed no tracked files. All experiments ran under `scratchpad/rev_v3eval/`.

## Verdict: ACCEPT WITH CONDITIONS

The evaluation was pre-registered correctly, and I reproduced it exactly. It implements PROTOCOL.md faithfully, and it reports the headline honestly: neither field meets the targets. Three conditions apply.

1. **V2 comparison (P2).** Qualify or withdraw the claim "V3 90.1% vs V2 86.8% strict". The whole gap comes from ground-truth labels that V2 has no way to output.
2. **Population weighting (P2).** C11 F03 requires a population-weighted precision beside the unweighted figure, and the confirmation review (43190971) carried that requirement forward. The evaluation does not report one. Either add it, or record a deferral with a reason.
3. **Record the matcher artifacts and the residual C11 items (P3).** Note the matcher artifacts below, and state that C11 F05–F08 are only partly addressed by this evaluation, or not at all.

## Method

1. **Ordering.** I checked the commit order with `git log`:
   - `761045d5` (11:17:41) committed PROTOCOL.md and the tool.
   - `1b46e368` (11:32:58) is the V3 freeze.
   - `cade4c99` (11:33:39) holds the results.

   Running `git diff 761045d5 HEAD` over `holdout_v3_eval/` and `holdout_v3/` shows only new output files: the tool, the protocol and the ground truth are unchanged since pre-registration. The sha256 of OUTCOMES_V3.csv (`2ff4bce6…`) equals the hash in `OUTPUT_SHA256SUMS` from the freeze commit and the hash recorded in RESULTS.md.
2. **Check run.** `python3 -I -B tools/eval_v3_holdout_c12.py --check` printed "evaluation reproduces".
3. **Independent reimplementation.** I wrote `rev_v3eval/work/repro.py` from the protocol text, without importing the tool. It covers matching, scoring and the judgment-level comparison.
4. **Matcher artifacts.** I classified all 35 UNMATCHED ground-truth rows and all 11 EXTRA V3 rows, reading the judgment texts from the c7 blobs cited in `text_source`.
5. **Wrong labels.** I re-read every wrong-label row against the judgment text: all 14 rows, 17 field errors.
6. **Negative control.** I ran the tool and my code against a perturbed copy of the V3 output.
7. **Traceability.** I ran an independent check over all 144 answered V3 rows in the holdout judgments.
8. **V2 vocabulary.** I checked V2's label set (`OUTCOME_VOCAB` in `v2core.py`) against the ground-truth labels.

## Reproduced figures (all match)

| Figure | Tool | My reimplementation |
| --- | --- | --- |
| Judgments / ground-truth rows | 150 / 215 | 150 / 215 |
| Unmatched / extra | 35 / 11 | 35 / 11 |
| printed_disposal | 126/138 = 91.3%, coverage 138/213 = 64.8% | identical |
| substantive_result | 108/113 = 95.6%, coverage 113/207 = 54.6% | identical |
| Judgment level V3 | 109/121 = 90.1% strict, 112/121 family | identical |
| Judgment level V2 | 105/121 = 86.8% strict, 111/121 family | identical |
| Judgment level crawler | 84/104 = 80.8% family | identical |
| Traceability | 138/140 at offset; page 139/140 | identical on the 140 matched rows |

**Negative control.** I changed V3H001's `printed_disposal` from dismissed (correct) to allowed in a copy:
- Both the tool and my code then gave printed 125/138 = 90.6%.
- Coverage and the substantive figures were unchanged, as expected.
- `--check` against the copy reported CHECK FAILED.

## Matcher-artifact classification

Classes: (a) genuine V3 failure; (b) matcher artifact.

| Judgment | Rows | Class | Cause |
| --- | --- | --- | --- |
| V3H005 | GT CA 5151/2008 (UNMATCHED) and V3 CA 5151/2008 (EXTRA) | **(b)** | The ground-truth text "(printed as 5151-52 / 5151-5152 of 2008)" adds the key `5152-2008`, so the ground-truth key becomes `5151-2008;5152-2008`. V3 identified CA 5151/2008 correctly. |
| V3H005 | V3 CA 52/2008 (EXTRA) | (a) | V3 split "5151-52" into a spurious CA 52/2008. |
| V3H036 | GT Contempt Pet. 252/2012 "in W.P. (C) 538 of 2011" (UNMATCHED) and V3 "(CIVIL) 252/2012" (EXTRA) | **(b)** | The parent-case number gives the ground truth a second key. V3 found the proceeding, but labelled it dismissed/relief_refused. The text says "the contempt petition is closed", so the ground truth (other/no_adjudication) is right. |
| V3H015 | 4 GT rows: CA 281 and 282/2020, CA 2826 and 2827/2021 | (a) | V3 did not produce these proceedings. |
| V3H017 | 2 GT rows; V3 CA 53/2026 and CA 8452/2026 (EXTRA) | (a) | The ground truth splits by impugned order under one appeal number. V3 split by number (one split spurious) and abstained with CONFLICTING_DISPOSITIONS_WITHOUT_PROCEEDING_MAPPING. The matcher also cannot represent this split (see F06). |
| V3H018 | GT MA 2188/2018 | (a) | V3 missed the application. |
| V3H019 | V3 CA 131/2016 (EXTRA) | (a) | OCR text "I 0131" produced a spurious split. |
| V3H027 | GT Crl.A. 55/2006 | (a) | V3 missed the connected appeal. |
| V3H034 | GT TC(C) 38/2002 | (a) | V3 missed the lead case; the text reads "38 of2002". |
| V3H035 | 9 GT rows; V3 UNIDENTIFIED (EXTRA) | (a) | NO_TEXT_FILE_FOR_THIS_SHA_AT_COMMIT. Latent: the "(printed as 373-375 …)" keys would not have matched even if V3 had split correctly. |
| V3H039 | 15 GT rows; V3 UNIDENTIFIED (EXTRA) | (a) | V3 abstained for the whole judgment. Same latent "(printed as …)" key problem. |
| V3H118 | V3 OWP 764/1998 and CA 2605/2010 (EXTRA) | (a) | These are cited cases, not host proceedings. |
| V3H121 | V3 SWP 142/2005 (EXTRA) | (a) | This is the lead case of a referenced bunch. V3 attached "transferred" to it and abstained on the host SWP 2923/2015. |

Totals:
- **Class (b):** 2 unmatched ground-truth rows and 2 extra V3 rows.
- **Class (a):** 33 unmatched ground-truth rows and 9 extra V3 rows.

### POST-HOC sensitivity (not the headline; class (b) re-matched only)

| Field | Headline | Post-hoc, (b) re-matched |
| --- | --- | --- |
| printed_disposal | 126/138 = 91.3%, coverage 64.8% | **127/139 = 91.4%, coverage 139/213 = 65.3%** |
| substantive_result | 108/113 = 95.6%, coverage 54.6% | **109/115 = 94.8%, coverage 115/207 = 55.6%** |
| Unmatched / extra | 35 / 11 | 33 / 9 |

The matcher artifacts have a negligible effect, and they cut both ways. Re-matching V3H036 adds a substantive error, which moves substantive precision below 95%.

A second post-hoc figure, given for information only: if the four convention-ambiguous wrong labels (below) are counted as correct, printed precision is 128/138 = 92.8% and substantive precision is 110/113 = 97.3%. Printed precision stays below target under either lenient reading.

## Wrong-label rows re-read against the judgment text

**Count correction:** there are **14 wrong-label rows (17 field errors: 12 printed, 5 substantive)**, not 21. I re-read all of them.

| Row | Field | GT → V3 | Judgment text | Decision |
| --- | --- | --- | --- | --- |
| V3H027 | P, S | disposed_of_with_directions / partly → dismissed / refused | Para 67: "the appeals stand disposed of with the following directions". V3 took a mid-reasoning sentence on p.60 ("the same is rejected"). | GT right |
| V3H041 | P | disposed_of → disposed_of_with_directions | "disposed of, in the aforesaid terms". The terms give liberty to apply to the AFT, and the AFT "shall" take the application up. | Convention ambiguity |
| V3H055 | S | remanded_for_fresh_decision → relief_granted | Unfitness orders quashed; fresh expert board; appointment if fit; "allowed in the above terms". | Convention ambiguity |
| V3H056 | P | disposed_of_with_directions → disposed_of | "let the claim … be decided within 12 weeks … disposed of accordingly" | GT right |
| V3H059, V3H067, V3H092, V3H098, V3H113 | P | transferred → disposed_of(_with_directions) | Each order transfers the petition to the AFT, then says "disposed of". `transferred` is in the convention's printed label set. | GT right (systematic V3 weakness: 5 of 13 transfer judgments) |
| V3H068 | S | remanded_for_fresh_decision → relief_granted | "case … be re-examined and a fresh order be passed … order quashed" | GT right |
| V3H117 | P | disposed_of → disposed_of_with_directions | Contempt closed as complied; liberty only; "The petition is disposed of." | GT right |
| V3H135 | P | set_aside_and_remanded → allowed | "writ petition is allowed and the impugned order … set aside. The matter is remanded back to the Tribunal" | Convention ambiguity (leans GT) |
| V3H138 | P | disposed_of_with_directions → remanded | Mandamus with directions I–XII; "The writ petition is finally disposed of." | GT right |
| V3H138 | S | relief_partly_granted → remanded_for_fresh_decision | Para 214: "The matter is remitted to the respondents", plus substantive directions. | Convention ambiguity |
| V3H139 | P, S | allowed / granted → partly_allowed / partly | All three prayers (notice, rejection order, reassessment order) quashed; "allowed to the extent and in terms herein above". | GT right. The V3 F05 extent rule over-fires here. |

Results:
- **Ground-truth label errors confirmed: 0.** Of the 17 field errors, 13 have the ground truth right and 4 are convention ambiguities.
- I found one doubtful ground-truth label outside the scored set: V3H041 substantive `relief_refused`. The court relegated the matter to the AFT without deciding it, so `no_adjudication` is arguable. V3 abstained, so the score is unaffected.
- The ground-truth `proceeding` field departs from the coding convention ("exactly as printed"): it carries editorial "(printed as …)" text and party names. That departure causes the class (b) artifacts.

## V2 comparison

- **Same judgments:** yes. All three methods have 144 scorable judgments; MIXED and unscorable ground truth are excluded for all of them.
- **V2's single-outcome design:** handled fairly. Ground truth is reduced to a judgment label, and MIXED is excluded. V3 is reduced the same way and is, if anything, treated harshly: any row disagreement, including an abstained row, makes V3 MIXED and counts as an abstention (V3H033, V3H121).
- **Label mapping:** not fair under strict scoring. V2's `OUTCOME_VOCAB` has no `disposed_of` and no `dismissed_in_default`, but the ground truth uses them for 8 scorable judgments.
  - Restricted to ground-truth labels V2 can emit (136 judgments), V3 scores 105/115 = 91.3% and V2 scores 105/115 = 91.3%, at equal coverage.
  - The 4-judgment strict gap (V3H024, V3H030, V3H091 disposed_of; V3H150 dismissed_in_default) is entirely a vocabulary effect.
  - Family precision (92.6% vs 91.7%) is the fair comparison and shows no material difference.

## Traceability sample

- My independent check covered all 144 answered V3 rows: the 140 matched rows the tool checks, plus 4 answered EXTRA rows.
- The 2 "excerpt not at offset" failures (J-105f115e1ba19369 and J-fd4046aaacae250c) are excerpts truncated to 450 characters with "..." appended. The prefix sits exactly at `char_start`, so both are traceable in substance.
- The single page failure (J-a8ad20538fcb8515) is an excerpt that starts before a `[[page 3]]` marker. The operative words are on page 3, as V3 states.
- The 138/140 figure is therefore conservative, and the true provenance rate is 140/140. The protocol says "each answered V3 row", but the tool checks only matched rows (144 vs 140).

## Assessment of C11 extraction review findings

| C11 finding | Verdict | Reason |
| --- | --- | --- |
| F02 (single-coded holdout; no written convention) | **CLOSED_VERIFIED** | The holdout is double-coded under a written convention (CODING_CONVENTION.md). Strict agreement of 134/150 is reported, and scoring is against adjudicated truth, with a breakdown by ground-truth source. Caveats are documented in PROCESS_NOTE: coder separation rests on instructions only, and the adjudicator was not blind for 14 judgments. Printed-versus-substance ambiguity remains at the margin: 4 of 17 wrong labels. |
| F05 (partly succeeds / extent-qualified allowances) | **PARTIAL** | The rule and the tests exist, including H011 and the "To the aforesaid extent" sentence. On the holdout, both genuine partly_allowed rows are right (V3H016, V3H058). The extent rule gives a wrong partly_allowed for V3H139, where full relief was granted. The README's "or abstain" option is not used there, and the evaluation does not report F05 performance separately. |
| F06 (proposition holding recall) | **NOT_CLOSED** | V3 extracts outcomes only (README: "No propositions"), and this evaluation does not re-measure holding recall. The requirement stays open on the V2 propositions. |
| F07 (origin-label precision) | **NOT_CLOSED** | Out of scope of this evaluation; per-label origin precision is not re-measured. |
| F08 (quote-span closing; 51 rows) | **PARTIAL** | A quote-boundary fix and tests exist (`TestQuoteBoundary`, README rule 6), and no quote-related errors appear in the holdout. The required hand review of the 51 `ONLY_QUOTED_DISPOSITION_LANGUAGE_FOUND` rows, with a count of how many V3 resolves, is not reported. V3 output still carries 52 such rows, plus 40 `SECTION:` rows. |

Also outstanding from the confirmation review: the C11 F03 population-weighted precision is missing (see F02 below). The scorer makes no allowance for impugned-order proceedings such as V3H017 (see F06 below).

## Findings

| ID | Severity | Summary |
| --- | --- | --- |
| F01 | P2 | The "V3 90.1% vs V2 86.8% strict" claim is a vocabulary artifact; on comparable labels the two are tied at 91.3%. |
| F02 | P2 | The population-weighted precision required by the C11 F03 carry-over is not reported. The sample is stratified (46 of 150 judgments are batch_or_multi), so the unweighted figures are not corpus estimates. |
| F03 | P3 | Matcher artifacts: ground-truth "(printed as …)" text and parent-case numbers create compound keys. This affects 2 ground-truth and 2 V3 rows now, and would hide correct splits in V3H035 and V3H039. The protocol does not state this effect. |
| F04 | P3 | Traceability checks only 140 matched rows, not every answered V3 row (144). Truncated "..." excerpts are counted as failures. |
| F05 | P3 | C11 F05 to F08 are only partly addressed (see the table above). The V3 extent rule causes a holdout error (V3H139). |
| F06 | P3 | The scorer makes no allowance for impugned-order proceeding identity (V3H017), which the confirmation review required. There is no score impact now, because V3 abstained. |
| F07 | INFO | The count of wrong-label rows is 14 rows (17 field errors), not 21. No ground-truth label errors were confirmed; 4 errors are convention ambiguities; V3H041 substantive is doubtful but unscored. |
| F08 | INFO | V3 misses `transferred` in 5 of 13 transfer judgments. This is the largest single source of printed errors. |
