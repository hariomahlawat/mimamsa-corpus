# C13 blind coding assignment log (coordinator)
Packets copied from claude/c13-a0-eval f1d61f71 `outputs/packets/<H>/<slot>/CODER_SHEET.csv` + `packets/CODING_GUIDE_<task>.md`.
leakcheck (blank packets): OK for all 6 sheets, 2026-11-25.
Each slot is a separate, freshly spawned agent instance with no prior context. They receive only their workdir (sheet and guide), the store pointer (HF@5524c3d9), and the protocol's uncodable codes. They are not given strata, weights, extractor output, or the other coder's work.
| Holdout | Slot | Instance | Workdir | Started |
|---|---|---|---|---|
| H-OUT-C13 | coder_1 | C13-COD-OUT-1 (agent instance a160253e) | coding/H-OUT-C13/coder_1 | 2026-11-25 |
| H-OUT-C13 | coder_2 | C13-COD-OUT-2 (agent instance aa7d2a15) | coding/H-OUT-C13/coder_2 | 2026-11-25 |
| H-HOLD-C13 | coder_1 | C13-COD-HOLD-1 (agent instance a71a3782) | coding/H-HOLD-C13/coder_1 | 2026-11-25 |
| H-HOLD-C13 | coder_2 | C13-COD-HOLD-2 (agent instance a12fbe57) | coding/H-HOLD-C13/coder_2 | 2026-11-25 |
| H-REL-C13 | coder_1 | C13-COD-REL-1 (agent instance acdf18e5) | coding/H-REL-C13/coder_1 | 2026-11-25 |
| H-REL-C13 | coder_2 | C13-COD-REL-2 (agent instance a1dbc275) | coding/H-REL-C13/coder_2 | 2026-11-25 |
Human legal-assistant second coding (D-07, 20% of H-OUT): NOT AVAILABLE. No qualified human annotator has been provided; reported separately as an owner decision.

## Freeze records (for the GA4 evaluator)
- A2 Outcome V4 is frozen at `9cdd5008` (claude/c13-a2-outcome). It descends from f1d61f71. Predictions sha `45c5a332…`: 300 items, 480 rows, 5 abstentions where there was no text.
- A3 c13-holdings/1.0.0 is frozen at `a520aa3a` (claude/c13-a3-holdings). It descends from f1d61f71 via `59abf9a7`. Predictions sha `3894ecbf…`: 113 items, 837 rows.
  - DISCLOSURE: the A3 author read key columns of the H-HOLD SAMPLE/RESERVE files, which the protocol marks evaluator-only. The coordinator instructed this so the fresh set's item ids could be excluded from training (commit f7155167). The evaluator must report this as a protocol deviation. The training exclusion list contains ids only.

## Process events
- **Store-pointer defect.** Five H-OUT Supreme Court files are absent at HF `5524c3d9`: HO13-5f043e05ca, 299e337653, c123b2ef4d, b3ece22f38 and c7541dbf29. Each is present at HF `main` with a matching LFS sha256; they were added in the later C12 ingestion commits. Coordinator instruction to all running coders: when a file is absent at 5524c3d9, fetch it at revision `main` and code it only if its sha256 matches, recording `store=HF@main` in the notes. coder_2 (H-OUT) returned these 5 as FILE_UNAVAILABLE and was asked to code them.
- **A5 freeze `e15af208`.** The prediction file contains verbatim excerpts from holdout pages, because the scorer's anchor check needs them. A2, A3 and A5 branches stay UNPUSHED and unintegrated until GA4 scoring is complete. Coders and adjudicators must not receive any predictions.
- **PROTOCOL DEVIATION PD-01 (H-HOLD-C13): coordinator's error.** CODING_GUIDE_holdings.md v1.1 (interim) says annotation must not start until the Holdings V2 substantive guideline (`annotation_guideline_holdings.md`) is committed with a version and sha256. That guideline does not exist in any branch. The coordinator's coder brief did not check this precondition, and both H-HOLD coders started under the interim guide v1.1, which fixes the layout and vocabulary but does not define "holding". coder_1 completed under v1.1; coder_2 continues under v1.1 for consistency.
  - Disposition: H-HOLD gold is reported as "interim-guide gold (v1.1), no substantive guideline, not legally reviewed". The A3 precision and recall figures carry this qualification. The evaluator must also report the definitional sensitivity (the disagreement categories from adjudication).
  - Writing a guideline now and re-coding was rejected for this cycle, because the extractor is already frozen and a guideline written after the fact risks fitting the gold to the extractor. This is recorded for the owner.
- H-REL: both sheets passed `leakcheck --completed`. Agreement: 89 AGREE / 71 DISAGREE items; strict unit agreement 0.468. The adjudication sheet holds 71 items. The key is sealed in `_sealed/`. The adjudicator (C13-ADJ-REL, agent instance afafacf1) started 2026-11-25.
- H-OUT: both sheets pass `leakcheck --completed`. Items: 251 AGREE / 49 DISAGREE. Coders produced several rows per item where an item has several proceedings; that is per the guide, and the coordinator's "do not add rows" brief was wrong on this point.
- H-HOLD: coder_2 passes leakcheck. coder_1 fails on 2 NO_HOLDING rows because notes carry extra text; the format fix has been sent to coder_1. There is no semantic change.
- H-HOLD: both sheets pass leakcheck (coder_1 after the NO_HOLDING notes format fix). Agreement is poor: items 34 AGREE / 79 DISAGREE, strict item agreement 0.301, strict unit agreement 0.450, kappa including unmatched below 0. This is consistent with PD-01, since no substantive definition existed.
  - PD-01 addendum: the H-HOLD adjudicator was given a coordinator working definition, standard ratio decidendi wording, written without reference to any A3 output, rules or predictions. Its borderline categories feed the sensitivity analysis. This is an additional deviation, disclosed here: the definition post-dates the A3 freeze. H-HOLD results must be headlined with the low inter-coder agreement.
- Adjudicators: H-OUT C13-ADJ-OUT (agent instance ac8b4624); H-HOLD C13-ADJ-HOLD (agent instance ae234b4e).
- H-REL adjudication complete: 71 items, 256 rows; X 110 / Y 143 / NEITHER 3; 1 UNCODABLE:OUT_OF_SCOPE. truth built: truth/H-REL-C13.csv (372 rows). Store versioning and scoring are left to the GA4 evaluator.
- H-OUT adjudication complete: 49 items, 96 rows; X 23 / Y 25 / NEITHER 1; 6 OUT_OF_SCOPE. truth/H-OUT-C13.csv built.
- H-HOLD adjudication complete: 79 items, 185 rows; X 14 / Y 10 / NEITHER 55; 3 NO_HOLDING, 3 OUT_OF_SCOPE. Borderline tags: GRANULARITY_SPLIT 49, SCOPE 13, OBITER 12, FACT_FINDING 11, QUOTED_PRECEDENT 3, COUNSEL_VOICE 1. truth/H-HOLD-C13.csv built.
- H-HOLD truth built after NO_HOLDING format fix: truth/H-HOLD-C13.csv sha bb726f95…
- GA4 evaluator (C13-EVAL, agent instance aeca2409) found that the A2 and A5 freeze statements also disclose reading evaluator-only identifier columns, which this log had omitted. Added here. Results: eval/RESULTS_C13.md. All targets FAIL. An independent GA4 review has been requested.
- Pre-integration review (REVIEW_A2_A3_A5_INTEGRATION.md) found that A3's self-check and opinion gold used 15 judgments from the H-OUT and H-REL holdouts. The A3 author is not the A2 or A5 author, so this does not affect the scoring of A2 or A5. It is disclosed here, and A3 has been asked to list the items.
- COORDINATOR DECISION D-HHOLD (the owner may override): **H-HOLD-C13 is treated as SPENT.** It has been coded, adjudicated and scored, even if only descriptively, and its labels and predictions will be in GitHub. A future holdings evaluation must use a FRESH draw from the A0 frame under an independently written holdings guideline. The same 113 items are not to be re-annotated. This keeps future evaluation blind and avoids keeping H-HOLD material out of staging.
