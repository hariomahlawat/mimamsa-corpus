# H-HOLD-C13 blind adjudication of predicted holdings (GA4 evaluator) — rules fixed before the sample was drawn

Written 2026-11-25 before drawing the sample and before running any holdings scoring or looking at any
reference-match status of any prediction.

**Why.** PROTOCOL_C13 v1.1 s.5: true holdings precision comes from blind adjudication of all predicted `holding`
items, or a seeded sample of at least 100, in H-HOLD-C13. Reference-match precision is only a lower bound.

**Who.** The GA4 evaluator (AI agent; not a coder, not the H-HOLD adjudicator, not the A3 author). Not a human,
not legally reviewed.

**Sample.** Frame = every prediction row with `item_type = holding` in the frozen file (sha256 3894ecbf…), excluding
rows on items whose reference is UNCODABLE (those are outside the scored denominators by protocol s.4.5; this uses
only the item-level UNCODABLE flag, nothing about any holding). Order the frame by
`sha256("C13-GA4-HHOLD-PRED-ADJ|" + pred_id)` ascending and take the first 100 (seed string
`C13-GA4-HHOLD-PRED-ADJ`). Equal selection probability for every frame row, so the harness's item-weighted ratio
estimator stays unbiased (the constant subsampling factor cancels in the ratio). Clusters remain judgments.

**Blinding.** While adjudicating, the evaluator sees only: item id, page, predicted opinion, predicted excerpt, the
page text (sha256-verified representative copy, PyMuPDF text layer) and neighbouring pages / the closing page for
the disposal. Not shown: the reference annotations, the reference-match status, the extractor's `legal_issue`,
`certainty` and `notes`.

**Definition.** The H-HOLD adjudicator's applied definition (coding/H-HOLD-C13/adjudicator/DEFINITION_APPLIED.md):
a holding is a proposition of law, or of law applied to the material facts, that the court itself states and that
is necessary to its decision on an issue before it; court's own voice; not counsel's submissions, lower-forum
summaries or quoted precedent unless adopted; not obiter; not pure findings of fact; operative directions (costs,
compliance time limits, bare "dismissed") are not holdings.

**Labels (harness vocabulary).**
- `CORRECT`: the predicted span, read in context, states a holding under the definition (the span may be partial,
  but its core must be the holding proposition).
- `INCORRECT`: it does not (tag the reason: FACT_FINDING, COUNSEL_VOICE, SCOPE (lower forum / recital),
  QUOTED_PRECEDENT, OBITER, OPERATIVE, PROCEDURAL_OR_NARRATIVE, OTHER).
- `UNCLEAR`: cannot be decided from the text (excluded by the harness from the adjudicated denominator; counted).
- Extra tag `RESTATEMENT` on a CORRECT row when the span restates a holding the court states more clearly elsewhere.
  **Primary:** restatements count as CORRECT (they are holding statements). **Pre-specified sensitivity:**
  RESTATEMENT rows count as INCORRECT (the adjudicator's one-row-per-issue unit convention).
- Opinion: if the span is a holding but in a different opinion family than predicted (majority vs separate/dissent),
  it is labelled INCORRECT with tag WRONG_OPINION (protocol strict scoring requires the opinion family to match).
