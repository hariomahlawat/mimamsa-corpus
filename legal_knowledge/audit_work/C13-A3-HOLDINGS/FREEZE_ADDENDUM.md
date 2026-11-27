# Freeze addendum: c13-holdings/1.0.0 (post-freeze, documentation only)

`FREEZE.json` (freeze commit `a520aa3a`) is immutable. This addendum supplements it. No extractor, model, configuration or prediction file has changed since the freeze. `holdings_c13.py check` still verifies the frozen hashes, and the frozen prediction sha256 stays `3894ecbfb3c3c6d0bae8ab275f905d0c812c2d018dd3b63fb3eeeb348758e164`.

## 1. Blind GA4 result (C13-EVAL `RESULTS_C13.md` s.1.3, s.4.2, s.9)

- **H-HOLD-C13 is NOT SCORABLE under protocol v1.1.**
  - Inter-coder span F1 is 0.566, below the 0.6 threshold.
  - PD-01: annotation began without a substantive guideline.
  - A3 has no protocol verdict in C13.
- **Descriptive only:**
  - precision 0.365 [0.241, 0.503];
  - recall 0.517 [0.424, 0.608].
- The `targets_and_estimates` entry in `FREEZE.json` ("about 50% precision") is a pre-freeze developer estimate and is **superseded**.

## 2. Additional exposure disclosure (pre-integration review finding A3-02)

The author statement in `FREEZE.json` covered H-HOLD only. It omitted the following:

- The developer self-check (`selfcheck/SELFCHECK_SAMPLE.csv`, 40 holdings read in context and labelled) included rows from 15 judgments that belong to the H-OUT and/or H-REL holdouts.
- The opinion gold (`gold/OPINION_GOLD_C13.csv`) was built from the text of one of them, J-28f88d53cdcab798.
- Vetoes were written from the self-check errors.
- The list, with holdout membership as identified by the reviewer, is in `exclusions/DEV_EXPOSURE_HOUT_HREL.csv`:
  - 9 in H-OUT;
  - 10 in H-REL;
  - 4 in both.
- Two self-check rows are on a page adjacent to a coded H-REL page:
  - J-28f88d53: p.20, against coded p.19;
  - J-47dffe7e: p.21, against coded p.22.
- The earlier scope-wide automated scans processed all SC-scope texts, which include H-OUT and H-REL judgments. They printed no text from them.
- No H-HOLD judgment appears in any A3 development or training artifact.
- The A3 author is a separate agent instance from the A2 and A5 authors.
- Registering this exposure in the A0 exposure register is left to the coordinator or A0. This branch does not edit A0 files.

## 3. Other review notes

- **A3-01:** the README now opens with the GA4 addendum. Development estimates are labelled superseded, and "unseen" is corrected to mean "outside training and outside H-HOLD".
- **A2-06:** the RM-001 guard is hardcoded in `c13_corpus.py`. Reading `config/restricted_material.json` is deferred to the next version, because the frozen tools are unchanged.
- **X-01:** whether `frozen_predictions/PRED_H-HOLD-C13.csv` (excerpts of H-HOLD text) goes into staging is a coordinator decision. The coordinator has since recorded H-HOLD-C13 as spent (D-HHOLD).
