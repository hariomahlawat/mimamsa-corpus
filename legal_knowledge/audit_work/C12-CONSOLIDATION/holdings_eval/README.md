# Blind evaluation of the frozen holdings extractor c12-holdings/1.0.0

Independent evaluator. Did not write the extractor or the reference set.
This README was written, and the matcher fixed, BEFORE any prediction for the 30
reference judgments was generated or looked at. Nothing below is tuned on results.

## Inputs
- Extractor: `../holdings/tools/holdings_c12.py` + `holdings_core.py` (sha256 checked before the run, recorded in `predictions/RUN_META.json`).
- Reference: `../holdings_reference/REFERENCE_HOLDINGS.csv` (245 rows; 77 question_of_law, 123 holding, 45 reasoning) for the 30 judgments in `SELECTION.csv`.
- Page convention: reference `page` is the 1-based PDF page (checked on one reference row only). Prediction `page` is compared as-is.

## Pre-registered matcher (primary)
Normalisation of an excerpt (prediction: `excerpt_clean`; reference: `excerpt`):
NFKC, lowercase, curly quotes/dashes to ASCII, every non-alphanumeric char to a space, split on whitespace.
Content tokens = tokens of length >= 2 that are not in a fixed English stopword list (in the tool), and are not pure numbers of length <= 3 (margin/para numbers). Token SETS are used.

A prediction P matches a reference item R iff
1. same `judgment_id`;
2. if both have a page: |page(P) - page(R)| <= 1 (P's span page..page_end is used: distance is 0 if R's page lies inside it);
3. containment = |C(P) ∩ C(R)| / min(|C(P)|, |C(R)|) >= 0.60, and |C(P) ∩ C(R)| >= 3.

Sensitivity variants (reported alongside, not used for headline):
- STRICT: containment >= 0.80, page distance 0.
- LOOSE: containment >= 0.40, page distance <= 1.

## Metrics
- Holding recall: reference `holding` rows matched by >= 1 prediction with `item_type == holding`.
- Court-voice recall: reference `holding` rows matched by >= 1 prediction in {question_of_law, holding, reasoning, obiter_candidate, operative_direction}. Also reported for all 245 reference rows.
- QoL recall: reference `question_of_law` rows matched by >= 1 `question_of_law` prediction.
- Precision lower bound: share of predicted `holding` items matching >= 1 reference `holding` row (and, secondary, any reference row of any type). Same for `question_of_law`.
- Pooled rates with Wilson 95% CIs; judgment-level macro averages (mean of per-judgment rates over judgments with a non-empty denominator), because items cluster within judgments and pooled Wilson CIs understate uncertainty.

## True precision (manual adjudication, blind)
Seeded sample (seed `C12-HOLD-EVAL-2026`, Python `random.Random`, sorted item_ids): 60 `holding` + 30 `question_of_law` (all, if fewer exist).
The adjudication sheet carries no reference-match information; labels are assigned before the join.
For each item the evaluator reads the page text rendered by PyMuPDF from the PDF git blob (not the extractor's text layer) and labels:
CORRECT_HOLDING (for QoL items: CORRECT_QOL) / REASONING_NOT_HOLDING / NOT_COURT_VOICE (submission, quoted precedent, lower forum; subtype noted) / OBITER / WRONG_SPAN / UNCLEAR, with a one-line reason.
True precision = CORRECT / (sample size), Wilson CI; UNCLEAR counted as not correct (also reported excluding UNCLEAR).
Origin error rates (precedent quotation / submission / lower forum) are taken from the NOT_COURT_VOICE subtypes.

## Anchoring
For every predicted court-voice item: page verified if the normalised excerpt's content tokens are >= 90% contained in the PyMuPDF text of pages page..page_end (+1 page slack for spans crossing a page break is NOT given; a span crossing pages must declare page_end).
Paragraph verified (items with `paragraph`): the last line-start paragraph marker (`N.`, `N)`, `(N)`) before the excerpt's first content tokens, searched over the claimed page and the 3 preceding pages, equals N. Lenient variant: N appears as a line-start marker anywhere in that window.

## Negative control (shuffle)
Predictions of judgment X are matched against reference rows of judgment Y for fixed cyclic shifts of the sorted judgment list (k = 1..5), with the primary matcher (page rule applied as-is) and with the page rule disabled. Spurious match rate = share of reference rows "recovered" by another judgment's predictions.

## Not evaluated / not credited
Treatment, statute links, versions, scenarios: the extractor only copies C11 rows; no credit beyond reporting counts. Overruling is never inferred.

## Reproduce
`python3.11 -I -B tools/eval_holdings_c12.py run` then `... --check` (recomputes all derived files and compares hashes).
