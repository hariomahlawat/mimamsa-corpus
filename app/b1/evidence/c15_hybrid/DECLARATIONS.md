# C15 S2: pre-declared evaluation choices (committed before the reranker or heading boost was run on the oracle)

This file exists so that reviewers can check, from git history, what was fixed **before** any result below was seen.

## What the author had seen before these declarations

- **Retrieval oracle, all cases:** the text and relevance of RET-07 and RET-10, read to diagnose why they fail. Every case's pass/fail under hybrid off/on was seen in C14 and re-run here as the baseline (10/14 off, 12/14 on).
- **SYN dense ranking:** for the RET-07 and RET-10 query texts (multilingual-e5-small, bench `probe`). Seen: J1-MAJ at rank 11 (cosine 0.8230) for RET-07, J2-MAJ at rank 8 (0.8223) for RET-10. The best cosine for RET-07 is 0.8573, below the C14 floor of 0.8579.
- **Not seen:** the blind holdout, which has never been accessed.

## Declared configuration (no value below was chosen from oracle results)

| Choice | Value | Basis |
| --- | --- | --- |
| Reranker | `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` @ `1427fd65`, fp32 `onnx/model.onnx` (Apache-2.0) | The only permissively licensed multilingual cross-encoder with published ONNX that fits CPU on this host (bge-reranker-v2-m3 and gte publish no ONNX; bge-m3 is 2.3 GB) |
| Rerank admission of dense-only candidates | logit ≥ **0** (sigmoid 0.5) | The model's native decision boundary from its training. Not calibrated on any project data |
| Rerank pool | **30** lexical + **30** dense candidates | Round default for CPU latency; not varied on the oracle |
| Dense candidates when reranking | No similarity floor | With a reranker, admission is the reranker's decision; the C14 floor remains for the no-reranker hybrid mode |
| Reranker max tokens | 256 | Same as passage embedding |
| Provision-heading boost | Rule in `ProvisionHeadings.cs`: fixed cue list, ≥ 2 matched stems, coverage ≥ 0.6, at most 5, contents-list passages skipped | Designed from the real headings of Army Act ss.38, 39, 80, 101, 102, 108, 116, 118 and 120 and the C14 walkthrough queries; never from oracle text |

## Rules for any later change

- Any later change to a value above is reported as a change **after** results were seen, with the result before and after. Such a change is not counted as independent evidence.
- RET-07 and RET-10 are reported with this disclosure whatever the outcome.

## Later changes and declarations (in commit order)

1. **Provision-heading boost: query coverage ≥ 0.5 added.**
   - *When:* after the C14 walkthrough queries were observed with the first rule. These are development data, not the oracle.
   - *Why:* Q22 ("can high court entertain writ against armed forces tribunal order") had two generic heading words ("high", "court") pull BNSS and AFT Act provisions above the High Court judgments the question is about.
   - *After the change:* Q01 and Q13 improved; Q22 is unchanged from the no-boost baseline.
   - *Status:* a development-tuned rule, not independent evidence.
2. **e5-base similarity floor, declared before it is computed.**
   - *Rule:* the same rule as C14: the median over the 43 walkthrough queries of each query's 99.9th-percentile cosine.
   - *Bounded variant:* the percentile is taken over a **seeded uniform random sample of 3,000 passages** of the real 290-document sample (seed 15), not over all 37,558. Embedding everything with e5-base takes hours on this CPU.
   - *Fixed:* the value obtained is used as-is for the oracle run.
3. **Heading tier in hybrid and rerank modes.**
   - *When:* after the 43 walkthrough queries showed that the boost had no effect in hybrid mode (development data, not the oracle).
   - *Why:* rank fusion dilutes a boosted lexical score.
   - *Change:* matched provisions are placed before fused or reranked hits, after the identifier, case-name and title tiers.
   - *Oracle with hybrid on:* unchanged at 12/14 (R2b).
   - *Status:* a development-tuned rule, not independent evidence.
