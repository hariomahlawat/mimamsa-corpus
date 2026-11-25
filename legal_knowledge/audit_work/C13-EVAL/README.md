# C13-EVAL: blind evaluation of the Cycle 13 frozen extractors (GA1–GA4)

This folder records the double coding, adjudication, reference sets, scoring and independent review for the three fresh A0 holdouts. It follows `C13-A0-EVAL/PROTOCOL_C13.md` v1.1. The holdouts are now **spent**.

| Item | Location |
|---|---|
| Results (final, after review) | `eval/RESULTS_C13.md` |
| Independent GA4 review (reproduced byte for byte) | `REVIEW_GA4.md` |
| Coordinator process log: assignments and deviations PD-01 etc. | `coding/ASSIGNMENT_LOG.md` |
| Coder sheets, adjudication sheets and results | `coding/<holdout>/` |
| Agreement statistics and X/Y keys (unsealed after scoring) | `coding/_sealed/` |
| Reference sets (adjudicated truth) | `coding/truth/` (also versioned in `eval/store/`) |
| Scorer outputs and post-hoc sensitivity | `eval/<holdout>/` |

**Headline.**
- **A2 outcome V4:** NOT_MET on all four pre-registered targets.
- **A3 holdings:** H-HOLD is not scorable under the protocol, because inter-coder span F1 is 0.566, below the 0.6 threshold. The figures are descriptive only, and re-annotation under an independent guideline is required.
- **A5 relations:** descriptive only, as the protocol provides.

Every figure is AUTOMATED_CANDIDATE_NOT_VERIFIED. All coders, adjudicators and evaluators were separate AI instances; no qualified human annotator was available.

**Excluded from this folder:** source PDFs, page images and extracted judgment text. Sources are identified by sha256 and can be re-fetched from the private HF dataset at revision `5524c3d9`, or at `main` for 5 SC files.
