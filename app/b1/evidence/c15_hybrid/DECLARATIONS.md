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

## C16 S3-E (Tranche B Stage 3): declarations for RET-07 / RET-10 work

Branch `claude/c16-s3e-hybrid` from `claude/c16-cp1` (`2541aec3`). Entries are appended in commit order; git history shows that each one precedes the oracle run it governs.

### What the S3-E author had seen before these declarations

- The C15 report (`HYBRID_EVAL.md`), which quotes RET-07 and RET-10 (query text, the required passage's wording, e5-small/e5-base dense ranks and cosines) and the C15 diagnosis.
- The oracle's assertion types (`retrieval_oracle.py`: state, mode, forbidden, top1, must_at), read to understand what a hybrid run must not break. The fixture file itself was not opened.
- The baseline re-run on this branch (`E:\Mimamsa-Data\c16s3e\oracle\b0-baseline`): hybrid off 10/14, C15 hybrid (e5-small, floor 0.8579) 12/14, identical to C15. Its printed lines show every case's mode and top-3 fixture ids.
- **Not seen:** the blind holdout (never accessed).

Consequence: nothing S3-E reports on RET-07/RET-10 is independent evidence. Only the holdout procedure can supply that.

### D1. Development data (committed in `c4764e08`, before any development result)

- `app/b1/evidence/c16_s3e/dev/dev_set.json`: 28 synthetic passages, 16 "semantic" queries (no shared content-word stem with the answer; paraphrase, contrary or conditional answers, one answer buried in a long paragraph), 5 lexical controls, 8 out-of-domain queries. Topics avoid the RET-07/RET-10 subject.
- Distractors: 3,000 real-sample passages, seeded uniform (seed 16), from `HybridBench dump`.
- The 43 C14 walkthrough queries, unlabelled, for gate firing rates only.

### D2. Rules fixed before any development or oracle result of S3-E

| Choice | Value |
| --- | --- |
| Gate / floor value for any model or representation | The C14 rule: median over the 43 walkthrough queries of each query's 99.9th-percentile cosine, over the 3,000 seeded real passages (C15 `calsub` variant). Computed by `dev_eval.py`; used as-is in the oracle run |
| Admission rules evaluated | `floor` (C14/C15), `gate_rank` (the same value gates the query by its best candidate; then the top **K = 10** dense candidates by rank), a z-score variant against the real-passage background (dev only unless it wins) |
| K for `gate_rank` | **10**, a round default fixed now; K = 20 is reported on dev only |
| Model selection | Highest dev semantic@10, subject to out-of-domain gate opening 0/8 and lexical-control top-3 no worse than e5-small `floor`; ties to the smaller model. Candidates: multilingual-e5-small, -base, -large (owner's int8 ONNX), bge-m3 (int8 ONNX), snowflake-arctic-embed-m-v2.0 (owner's int8 ONNX) |
| Representation | `plain` unless `title` (document title prefixed) gains on dev semantic@10 without losing the constraints above |
| Oracle runs | Only configurations declared below, each with hybrid off too; each result is reported whatever it is and is not followed by retuning |

### D3. First oracle runs (declared after e5-small, e5-base and a first arctic dev result; before any S3-E hybrid-on oracle run)

Dev results so far (1,000-distractor stride, `dev/out/*_s3.json`): e5-small `floor` 4/16, `gate_rank` K=10 5/16, both with out-of-domain gate 0/8; e5-base `floor` 7/16, `gate_rank` 8/16 but out-of-domain gate 2/8 (fails the D2 constraint); z-score rules open the gate on 7-8/8 out-of-domain queries and are **dropped**. The int8 models are being re-embedded one text per call (see D4 note below), so their earlier batched numbers are void.

| Run | Model | Admission | Gate / floor | Other |
| --- | --- | --- | --- | --- |
| O1a | multilingual-e5-small `614241f6` | `floor` | **0.8548** (D2 rule over the 3,000-passage seeded sample, `dev/out/e5-small_plain_s1.json`) | plain passages, batch 16 |
| O1b | same | `gate_rank`, K = 10 | 0.8548 | same |

Both are run once, hybrid off as well, and reported whatever the outcome.

### D4. int8 batching note, and the arctic oracle runs (declared after its dev result, before running them)

- **int8 note.** Dynamically quantised ONNX models compute activation scales per call, so padding in a batch changes every vector (arctic int8: cosine 0.96-0.99 batched vs single). All int8 models are therefore embedded one text per call (`dev_eval.py`; `Mimamsa:Hybrid:Batch=1` in the app). C# (ORT 1.31.1) and Python (ORT 1.32) vectors of the same int8 model still differ slightly (cosine 0.985-0.995), whereas e5-small fp32 matches exactly (1.000000). A gate calibrated in Python therefore transfers to the app only approximately; this is disclosed, not corrected.
- **Dev result (1,000 distractors, one text per call):** snowflake-arctic-embed-m-v2.0 int8, `floor` 6/16, `gate_rank` K=10 7/16, out-of-domain gate 0/8, lexical controls 5/5. Best of the models meeting the D2 constraints so far (e5-large and bge-m3 still embedding).
- **Deviation from D2:** the gate is computed over the 1,000-passage stride sample, not 3,000 (the host is saturated by OCR; this embedder runs starved at below-normal priority). Value **0.3994** (`dev/out/arctic-m2_plain_s3.json`).

| Run | Model | Admission | Gate | Other |
| --- | --- | --- | --- | --- |
| O2a | Snowflake/snowflake-arctic-embed-m-v2.0 `95c27414`, `onnx/model_int8.onnx` sha256 `03d923bb…`, CLS pooling, query prefix `query: `, no passage prefix, XLM-R SentencePiece of e5-small (ids verified identical) | `floor` | 0.3994 | batch 1, plain passages |
| O2b | same | `gate_rank`, K = 10 | 0.3994 | same |

### D5. e5-large oracle runs (declared after its dev result, before running them)

- **Dev, 500 distractors (stride 6; all models re-evaluated at this stride, `dev/out/*_s6.json`):** e5-small 4 / 6 of 16 (`floor` / `gate_rank`), e5-base 8 / 8 but out-of-domain gate 3/8 (excluded by D2), arctic-embed-m-v2.0 7 / 8, multilingual-e5-large int8 7 / 8, all others 0/8 out-of-domain and 5/5 lexical controls.
- Under D2, arctic and e5-large tie, so arctic (smaller) remains the selection (O2). e5-large is run as well because the brief asks for stronger models to be evaluated; this is **not** a selection made from oracle results, and whichever result it gives does not change the D2 selection.
- **Deviation from D2:** gate computed over the 500-passage stride-6 sample (host saturated): **0.8234**.

| Run | Model | Admission | Gate | Other |
| --- | --- | --- | --- | --- |
| O3a | intfloat/multilingual-e5-large `3d7cfbda`, `onnx/model_qint8_avx512_vnni.onnx` sha256 `46f5d13d…`, mean pooling, `query: ` / `passage: ` | `floor` | 0.8234 | batch 1 |
| O3b | same | `gate_rank`, K = 10 | 0.8234 | batch 1 |

### D6. bge-m3 oracle runs (declared after its dev result, before running them)

- **Dev, stride 6:** bge-m3 int8 (Xenova conversion of BAAI/bge-m3, MIT) `floor` **10/16**, `gate_rank` K=10 **11/16**, out-of-domain gate 0/8, lexical controls 5/5. Under D2 this is now the **selected model** (highest dev semantic@10 meeting the constraints), replacing arctic.
- Gate (D2 rule over the stride-6 sample, same deviation as D5): **0.5197** (`dev/out/bge-m3_plain_s6.json`).

| Run | Model | Admission | Gate | Other |
| --- | --- | --- | --- | --- |
| O4a | Xenova/bge-m3 `4de13258`, `onnx/model_int8.onnx` sha256 `a206e10e…`, CLS pooling, no prefixes | `floor` | 0.5197 | batch 1 |
| O4b | same | `gate_rank`, K = 10 | 0.5197 | batch 1 |
