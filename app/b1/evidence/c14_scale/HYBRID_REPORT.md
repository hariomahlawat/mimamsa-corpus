# C14 S4: hybrid retrieval proof of concept

**Status:** a PoC behind `Mimamsa:Hybrid:Enabled` (default **off**). With it off, B1 behaviour is byte-for-byte unchanged (tests `FlagOffIsIdenticalToB1` and the full suites below). Measured 2026-11-26. Similarity scores describe wording only; they say nothing about legal relevance or authority. No generative AI.

## 1. Model and runtime

| Item | Value |
| --- | --- |
| Model | `intfloat/multilingual-e5-small`, **MIT** licence, 384-dim, multilingual (covers English and Hindi) |
| Pinned revision | `614241f622f53c4eeff9890bdc4f31cfecc418b3`. `onnx/model.onnx` SHA-256 `ca456c06…6bc8665` (470,268,510 bytes); all files are pinned in `app/b1/hybrid/MODEL_MANIFEST.json` |
| Acquisition | One read-only Hugging Face download with the owner-verified IPv4 client (`app/b1/hybrid/fetch_model.py`), stored in `E:\Mimamsa-Data\models` (not in git). **Run time is fully offline.** The service checks the model SHA-256 at start-up and refuses to start on a mismatch |
| Runtime | ONNX Runtime 1.31.1 (CPU) in-process in C#. XLM-R SentencePiece tokenisation via Microsoft.ML.Tokenizers 2.0.1, verified token-for-token against the model's `tokenizer.json` (`TokenizerMatchesTheModelsTokenizerJson`) |
| Passage vectors | Embedded once per generation, cached as `<generation>.<model sha12>.<passage fingerprint>.emb`. A cache with a different key or size is ignored and rebuilt. Real sample: 38,445 × 384 float32 = 56.3 MB |
| Retrieval | Exact brute-force cosine (no ANN), deterministic (ties by passage index) |
| Fusion | Reciprocal-rank fusion (k = 60) of BM25 (depth 200) and dense (depth 100). Only for plain, non-exact queries. **Identifier and title tiers are placed before fusion and never re-ranked.** Mode is reported as `hybrid` only when the dense layer contributed. Dense-only hits carry "similarity is not legal relevance" |

## 2. CPU vs GPU

| Device | Passage embedding (256 tokens, batch 16) | Query embedding | Notes |
| --- | --- | --- | --- |
| CPU (i7-10750H, ORT default threads) | 82 ms per passage, 12.2 passages/s | 5–8 ms | Full sample (38,445 passages) took **44 min**, once per generation |
| DirectML GPU (GTX 1650 Ti 4 GB, ORT 1.24.4 DirectML; bench tool only) | 107 ms per passage, 9.3 passages/s | 186–201 ms (3.2 s first call) | Slower than CPU: DirectML needs fixed-length padding to 256 tokens and recompiles per shape |
| CUDA | not tested | — | Needs the CUDA toolkit or cuDNN on the host (system packages, not installed). `Mimamsa:Hybrid:Cuda` exists and falls back to CPU, labelled as such |

**Conclusion:** CPU is the right default on this host. Passage embedding is an offline, per-generation cost. Query-time cost is the 5–8 ms query embedding plus an exact scan (§4).

## 3. Similarity floor (calibrated without oracle data)

**The rule was fixed before any calibration numbers were seen:** floor = the median, over the 43 C14 walkthrough queries on the real 290-document sample, of each query's 99.9th-percentile cosine similarity across all 38,445 passages. A passage may enter through the dense layer alone only if it is more similar than the top 0.1% of passages typically are for a real query.

**Calibration** (`HybridBench calibrate`, `calibration.json`):

| Measure | Value |
| --- | --- |
| Queries / passages | 43 / 38,445 |
| Mean p99 | 0.8373 |
| Max p99 | 0.8949 |
| **floor = median p999** | **0.8579** |
| Median similarity of the lexical top hit | 0.8572 (for comparison only, not used) |

The floor is configured as `Mimamsa:Hybrid:MinSimilarity=0.8579`. **It was not adjusted after the oracle run.**

## 4. Retrieval oracle (unchanged, SYN development fixture)

The oracle and fixture are unedited: oracle blob `ef822772fc63`, fixture blob `7c0a9f28b562` (identical to the C13 runs). Run via `b1server.py` on port 5441 against the SYN site.

| Case | Expected mode | Hybrid off | Hybrid on, floor 0.8579 |
| --- | --- | --- | --- |
| RET-01 | identifier | Passed | Passed |
| RET-02 | lexical | Passed | Passed |
| RET-03 | identifier | Passed | Passed |
| RET-04 | identifier | Passed | Passed |
| RET-05 | lexical | Passed | Passed |
| RET-06 `BHT hearing tribunal` | hybrid | Failed (mode lexical) | **Passed** |
| RET-07 `Can someone challenge a hearing when nobody told them the allegation beforehand?` | hybrid | Failed (lexical; J1-MAJ missing) | **Failed**: no passage reaches the floor, so the mode stays lexical; J1-MAJ missing at rank 10 |
| RET-08 | lexical | Passed | Passed |
| RET-09 `सुनवाई से पहले लिखित सूचना` | hybrid | Failed (mode lexical) | **Passed** (L-HI, L-EN) |
| RET-10 `late warning invalidates hearing without notice` | hybrid | Failed (lexical; J2-MAJ missing) | **Failed**: hybrid; J1-MAJ now found, but J2-MAJ missing at rank 10 |
| RET-11 | lexical (empty) | Passed | Passed |
| RET-12 | lexical | Passed | Passed |
| RET-13 | parser_error | Passed | Passed |
| RET-14 | lexical | Passed | Passed |
| **Total** | | **10/14** | **12/14** |

| Aggregate | Off | On |
| --- | --- | --- |
| nDCG@10 | 0.835 | 0.859 |
| recall@10 | 0.792 | 0.819 |
| MRR@20 | 1.000 | 1.000 |

**Independence:**
- An earlier PoC run without a floor (before this calibration) also scored 10/14. The dense layer admitted an unrelated published SYN document and the oracle flagged it as an unmapped passage.
- The floor rule was then fixed from walkthrough data and calibrated on the real sample. **No change was made after seeing the 12/14 result.** RET-07 and RET-10 remain open; reaching 14/14 would need a stronger model or passage-level reranking, not floor tuning on these cases.
- The **blind holdout has not been accessed.** `app/b1/hybrid/HOLDOUT_PROCEDURE.md` and `run_holdout.py` let the independent evaluator run it with the unchanged oracle.

## 5. Real sample: identifier priority, effect and cost

Same build, same site, hybrid off vs on (vectors from cache, floor 0.8579). The 43 C14 walkthrough queries were run through the API (`hyb-sample-off.json`, `hyb-sample-on.json`).

**Identifier priority.** All 13 queries resolved in identifier mode (sections, rules, neutral citation, case number) have the **same mode and the same top passage** with hybrid on. Hybrid never displaces a pinned identifier.

**Effect.** 24 of 43 queries are unchanged. The 19 that changed are all plain-language, keyword or misspelling queries, which now run in `hybrid` mode. These are observations, not relevance judgements:

| Query | Lexical top 3 → hybrid top 3 |
| --- | --- |
| Q21 disability pension attributable to military service | Dharamvir Singh moves from rank 4 to **rank 1** |
| Q25 `dharamveer singh` (misspelling) | Dharamvir Singh from rank 35 to **rank 1** |
| Q05 punishments a commanding officer can award | Army Act rises from 3rd to 2nd |
| Q01 how to hold a summary court martial | **Army Act drops out of the top 3** (an SC judgment leads) |
| Q13 absence without leave punishment | Army Act still absent from the top 3 |
| Q35 AFT jurisdiction | Bench notifications partly replaced by recruitment rules and an SC judgment; still no AFT Act ss.14–15 |

**Cost** (real sample, same host, one run):

| Measure | Hybrid off | Hybrid on |
| --- | --- | --- |
| Start-up to healthy | 6.5 s | 11.0 s (+4.3 s: model load and 56 MB vector cache) |
| Working set / managed heap after the run | 1,367 / 569 MB | 1,991 / 632 MB (ONNX model and native runtime ≈ +600 MB) |
| Search, sequential p50 / p95 | 18.6 / 96.6 ms | 45.1 / 106 ms |
| 10 readers p50 / p95 (req/s) | 39 / 191 ms (148) | 121 / 274 ms (77) |
| 25 readers p50 / p95 | 157 / 367 ms | 334 / 667 ms |

## 6. Scale outlook

- **Embedding.** Measured CPU throughput is 12 passages/s. The 10k bench (247,538 passages) would need about 5.6 h, and the full corpus (about 1.8 M passages, estimated in SCALE_REPORT §3) about 41 h, once per generation. Feasible offline, but it argues for incremental per-release embedding with the cache keyed per passage.
- **Vectors.** About 1.5 KB per passage, so about 2.8 GB at full corpus.
- **Search.** An exact scan of 1.8 M × 384 per query is about 0.7 G multiply-adds; it would need an ANN index (HNSW) or int8 quantisation.
- **Status:** none of this was measured at bench scale.

## 7. Recommendation

1. **Keep hybrid off by default.** Offer it as an opt-in "plain-language" mode only after the independent holdout evaluation.
2. **Keep the deterministic identifier tier.** It is proven unaffected.
3. **Next step:** passage-level reranking or a stronger multilingual model (RET-07, RET-10, Q01), evaluated on the holdout. ANN and quantisation before full-corpus scale.
4. **Treat the floor as a calibrated parameter.** Re-calibrate only by the same documented rule on non-oracle data.

## 8. Tests

- **C#:** 97/97 on the branch build, including the real-model tokenizer and embedding tests (`MIMAMSA_HYBRID_MODEL` set).
- **New floor tests:** 2 tests covering `MinSimilarity` (`FloorAboveEveryScoreLeavesLexicalResultsUnchanged`, `FloorAdmitsOnlyPassagesAtOrAboveIt`). They run in the final verification (§9).
- **Playwright:** 30/30 with hybrid off (21 SYN, 9 sample).
- **Design:** 117/117; `gen_tokens --check` shows no drift.

## 9. Final verification

See the S4 PR description for the counts on the final commit.
