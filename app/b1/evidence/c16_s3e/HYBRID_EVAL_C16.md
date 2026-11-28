# C16 Stage 3 S3-E: RET-07 / RET-10 without weakening the oracle

**Branch** `claude/c16-s3e-hybrid` from `claude/c16-cp1` (`2541aec3`). Declarations are in `../c15_hybrid/DECLARATIONS.md`, section *C16 S3-E* (D1–D6). Git history shows each declaration committed before the oracle run it governs.

## 1. Outcome

| Item | Result |
| --- | --- |
| Oracle, hybrid **off** | **10/14** in every run (B0, B1 and each O-run's off pass), unchanged |
| Lexical parity (`IndexBench --parity`, real sample with the 43 walkthrough queries, and SYN) | **Byte-identical** to the base commit: sample `9CC23A42…`, SYN `4460F2ED…` |
| Defaults | Unchanged: hybrid off; every new setting defaults to the C15 behaviour (`Admission=floor`, `Pooling=mean`, e5 prefixes, `PassageContext=none`, `Batch=16`) |
| Best declared hybrid configuration | **13/14**: bge-m3 int8, `gate_rank` K = 10, gate 0.5197 (O4b). **RET-07 passes** (J1-MAJ at rank exactly 10); **RET-10 still fails** (J2-MAJ at rank 12) |
| 14/14 | **Not reached.** Not pursued by tuning on oracle cases |
| Independence | **None of the oracle results is independent evidence.** The author had read the C15 report, which quotes RET-07/RET-10 and their diagnosis, and saw every case's top 3 in the baseline run. Only the blind holdout (never accessed) can confirm anything |
| Blind holdout | Not accessed |

## 2. Approaches and results

Dev = synthetic development set (`dev/dev_set.json`, committed before any result): 16 "semantic" queries that share no content-word stem with their answer, 5 lexical controls and 8 out-of-domain queries, plus seeded real-sample distractors. Columns: semantic@10 (answer in fused top 10), out-of-domain (OOD) gate opening, lexical controls in top 3. Unless marked, dev numbers use 500 distractors (stride 6), the common stride all models were run at. Oracle: hybrid on (off is 10/14 in every run).

### 2.1 Admission and fusion (calibrated fusion)

| Rule | What it does | Dev e5-small | Dev bge-m3 | Oracle | Verdict |
| --- | --- | --- | --- | --- | --- |
| `floor` (C14/C15) | admit every dense candidate ≥ floor | 4/16, OOD 0/8 | 10/16, OOD 0/8 | 12/14 with every model | Baseline |
| `gate_rank` K=10 (new) | the floor gates the **query** (best candidate); then the top 10 dense candidates by rank, RRF as before. Mode decision identical to `floor` for every query (unit-tested) | 6/16, OOD 0/8 | **11/16**, OOD 0/8 | 12/14 (e5-small, arctic, e5-large), **13/14 (bge-m3)** | Small, consistent dev gain. Implemented as an option |
| `gate_rank` K=20 | same, 20 by rank | 4/16 (stride 3) | — | not run | Worse: more dense-only hits push answers out of the top 10 |
| z-score vs background | admit if (cos − μ_q)/σ_q ≥ z*, μ, σ over the real-passage background, z* by the C14 rule in z units | 2/16, **OOD 7/8** | — (arctic: 10/16 but **OOD 5/8**; e5-large OOD 8/8) | not run | **Rejected**: per-query normalisation opens the gate on nonsense queries, because every query has *some* passage several σ above its own mean |
| No floor | all top 100 | 0–2/16, OOD 8/8 | — | not run | Rejected (every query becomes "hybrid") |

Failure exposed by O3b: with a strong model and a tiny corpus, `gate_rank` can admit low-similarity passages. On SYN it admitted a published passage outside the oracle's catalogue in RET-06 (`syn-x-stagedearly`), which the oracle correctly counts as an error. On the real sample it admits about 6 dense passages per open query (walkthrough, dev harness).

### 2.2 Passage representation

| Variant | Dev (e5-small) | Verdict |
| --- | --- | --- |
| Plain (`passage: ` + text) | floor 4/16, gate_rank 6/16 | Baseline |
| Title context (`passage: <document title>. <text>`) | floor **0/16**, gate_rank 3/16 | **Worse.** Judgment titles are party names and add noise. Implemented as option `PassageContext=title` (key derivation stays recomputable from verified text and title), not recommended |
| Windows (about 90 words, half overlap, max over windows) | floor 4/16, gate_rank 6/16 (no change; the buried answer D08 is still not found) | No gain; not wired into the service. Not applicable to RET-07/10 anyway: their passages are single short paragraphs |
| Query/passage instruction formats | e5 `query:`/`passage:` (asymmetric), arctic `query:` only, bge-m3 none: each model's documented format was used | No further variant tried: e5-large-instruct (instruction-tuned) has only a 2.2 GB fp32 ONNX, which the shared host's RAM could not hold |

### 2.3 Models (all MIT / Apache-2.0, pinned, local, read-only fetch, `hybrid/manifests/*.json`, `hybrid/fetch_models_c16.py`)

| Model | File (sha256) | Size | Dev floor / gate_rank | OOD | Query embed p50 (C#, OCR load) | Passage embed (256 tok, 1 per call) | Working set Δ | Oracle floor / gate_rank |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| multilingual-e5-small `614241f6` (MIT) | fp32 `ca456c06…` | 470 MB | 4 / 6 | 0/8 | 86 ms | 204 ms | +531 MB | 12 / 12 (O1a/O1b, gate 0.8548) |
| multilingual-e5-base `d1287505` (MIT) | fp32 | 1.1 GB | 8 / 8 | **3/8** | 427 ms | 651 ms | +1,096 MB | not run (fails the OOD constraint) |
| snowflake-arctic-embed-m-v2.0 `95c27414` (Apache-2.0) | owner int8 `03d923bb…` | 311 MB | 7 / 8 | 0/8 | 47 ms | 443 ms | +668 MB | 12 / 12 (O2a/O2b, gate 0.3994) |
| multilingual-e5-large `3d7cfbda` (MIT) | owner qint8 `46f5d13d…` | 562 MB | 7 / 8 | 0/8 | 217 ms | 1,106 ms | +555 MB | 12 / 12 (O3a; O3b: RET-10 passes, RET-06 fails) |
| **bge-m3** (BAAI, MIT; Xenova int8 conversion `4de13258`) | int8 `a206e10e…` | 568 MB | **10 / 11** | 0/8 | 187 ms | 929 ms | +621 MB | 12 / **13** (O4a/O4b, gate 0.5197) |

Measured with `HybridBench qlat` (`runs/qlat_under_ocr_load.jsonl`). The host was saturated by the concurrent OCR job throughout, so all timings are upper bounds. Each model adds one query embedding per search; vectors are 1,024-d for bge-m3/e5-large, so a real-sample store is about 154 MB (52 MB for e5-small).

**int8 caveats** (D4):
- **Dynamic quantisation is batch-dependent.** Padding in a batch changes vectors (cosine 0.96–0.99), so int8 passages must be embedded one text per call (`Mimamsa:Hybrid:Batch=1`). The central VECTOR_PACK build must do the same.
- **C# and Python vectors differ slightly.** C# (ORT 1.31.1) vs Python (ORT 1.32) and the graph-optimisation level give cosine 0.985–0.995 for the same text, whereas fp32 e5-small matches to 1.000000.
- **Consequences:**
  - A VECTOR_PACK spot re-embed tolerance (`VECTOR_SPOT_REEMBED`, still UNCALIBRATED) must be calibrated per model and runtime.
  - Central build and site must pin the same ONNX Runtime build.
  - Gates calibrated in Python transfer to the service only approximately.

## 3. Why RET-07 and RET-10 are hard (post-hoc diagnosis, run after every declared oracle run)

Dense rank on the SYN site of the passage each case needs (`scripts/posthoc_probe.py`, `runs/posthoc_probe.txt`; query texts as quoted in the C15 report):

| Model | RET-07 → J1-MAJ | RET-10 → J2-MAJ |
| --- | --- | --- |
| e5-small | 11/21 (cos 0.8230) | 8/21 |
| e5-base | 7/21 | 5/21 |
| arctic-m2 | 11/21 | 9/21 |
| e5-large | 9/21 | 5/21 |
| bge-m3 | 8/21 | 9/21 |

**Mechanism:**
1. **No model puts either passage near the top**, out of 21 passages. Both answer by **contrast** (J1-MAJ: notice *was* given, application dismissed) or **paraphrase** ("written charge" for "allegation"). Bi-encoders trained on web QA measure topical similarity, not whether a passage *decides* the question.
2. **The development set shows the same thing** independently of the oracle. Under bge-m3, the dev answers that are contrary or conditional (S05 rank 170, S09 rank 113 of 528), buried in a long paragraph (S08, 40), or loosely paraphrased (S02, 17) are not found. Every plain paraphrase is found at rank 1–2.
3. **Monotone fusion cannot rescue a passage at dense rank r.** With RRF, a dense-only passage at rank r scores 1/(60+r). Every lexical hit above rank r, and every dense hit above it, outranks it.
   - RET-10: J2-MAJ's best dense rank is 5 (e5-base, e5-large). The query's lexical hits (J1-SUB, J1-SHORT, L-EN, …) fill the remaining top places, so it lands at 9–12 depending on the model.
   - e5-large O3b passed RET-10 (rank 9) but broke RET-06.
   - bge-m3 O4b passed RET-07 with J1-MAJ at **exactly rank 10**. With the int8 numerical drift noted above, that is a knife-edge pass, not a margin.
4. **What would pass RET-10 legitimately is not available here.** That would need a model that ranks the contrary or paraphrased holding in the top 2–3: a domain-adapted (legal) bi-encoder, or a cross-encoder trained on legal QA. No permissively licensed one is available locally, and C15 measured the generic multilingual cross-encoder at 1.4–4.6 s per query with no gain. Anything else (raising K, weighting dense above lexical, per-query constants) would be fitted to these two cases.

## 4. Recommendation

1. **Keep the default: hybrid off.** All gates are unchanged.
2. **Keep the new options**, all inert by default:
   - `Mimamsa:Hybrid:Admission`/`AdmitK`
   - `Pooling`, `OnnxFile`, `QueryPrefix`/`PassagePrefix`, `SentencePieceModel`
   - `Batch`, `PassageContext`
3. **Candidate for the independent holdout** (not adoption): bge-m3 int8 + `gate_rank` K = 10 + the D2 gate rule.
   - Best dev result (11/16 vs 6/16 for the current e5-small hybrid), OOD 0/8, lexical controls intact; oracle 13/14.
   - Before any adoption:
     - (a) The holdout procedure (`hybrid/HOLDOUT_PROCEDURE.md`) is run by the independent evaluator.
     - (b) The gate is recomputed over the full real sample, not the 500-passage stride used here.
     - (c) Vectors are produced centrally into a VECTOR_PACK, one text per call, with the ONNX Runtime build pinned identically on build and site. At the 0.93 s per passage measured here under load, 37,558 passages would take about 10 h, so it must not be done on site.
     - (d) Query-latency and memory budgets are re-measured on a quiet host: +0.6 GB working set and about 0.2 s per query under load.
   - **Licence and provenance:** BAAI/bge-m3 is MIT; the int8 file is a third-party (Xenova) conversion. If provenance matters, export and quantise centrally from the BAAI fp32 ONNX instead.
4. **Do not adopt:**
   - z-score / per-query normalisation (opens on nonsense)
   - title context (hurts)
   - windowing (no gain)
   - e5-base (opens on nonsense)
   - K = 20 (hurts)

## 5. Not achievable here, and why

- **RET-10 at 14/14** under any declared configuration. No evaluated model ranks J2-MAJ above 5th of 21. Monotone fusion with the query's lexical hits then leaves it outside the top 10, except where a weaker admission also lets in uncatalogued text (O3b).
- **A margin on RET-07.** It passes only at rank 10 with bge-m3, with no margin.
- **Making any of this independent.** The S3-E author had read the oracle diagnosis, so the oracle cannot validate these choices. The holdout must.

## 6. Reproduction

| What | Where |
| --- | --- |
| Oracle | `app/b1/bench/local/c16s3e_oracle_hybrid.ps1`: disposable database `c16s3e_oracle`, dropped after each run; vector caches in `E:\Mimamsa-Data\c16s3e` |
| Oracle outputs | `oracle/<run>__*`: B0 (baseline), B1 (off after the change), O1a–O4b |
| Dev | `scripts/dev_eval.py embed|eval <model> <repr>` with `C16_DISTRACTOR_STRIDE`; results in `dev/results/*.json` and `runs/dev_queue.log` |
| Models | `python -I hf_ipv4.py app/b1/hybrid/fetch_models_c16.py E:\Mimamsa-Data\models` (read-only; verifies Hub SHA-256 per file) |
