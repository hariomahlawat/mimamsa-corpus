# Blind holdout procedure (independent evaluator only)

The blind holdout is under custody. The development team has **not** read it, and these tools never require it to enter git.

## Prerequisites

- A checkout at the commit under evaluation.
- .NET 10 SDK.
- The project Python environment (`app/importer/requirements.txt`).
- The pinned embedding model: `python -I app/b1/hybrid/fetch_model.py <models-root>` (add `--verify-only` to check an existing copy against `MODEL_MANIFEST.json`).
- A disposable PostgreSQL database.

## Steps

1. **Build a synthetic site from the holdout fixture:**
   ```
   python -I app/b1/build/build_fixture_site.py --fixture <holdout.json> --out <work>/holdout
   ```
   The builder's F01 eligibility extras and the R2 cover-number edit refer to dev-fixture ids such as `J-ALLOW`. If the holdout lacks those ids, record the builder output; it does not affect retrieval scoring.

2. **Start the service in test mode.** Pick one of the two configurations below and set its variables before starting:
   ```
   python app/b1/tests/b1server.py --site <work>/holdout/site --port <port> --db "<dsn>" -- \
     python -I app/b1/hybrid/run_holdout.py --fixture <holdout.json> --map <work>/holdout/fixture_map.json --out <work>/holdout-<config>
   ```
   - **Lexical baseline:** no extra variables.
   - **Hybrid:**
     ```
     Mimamsa__Hybrid__Enabled=true
     Mimamsa__Hybrid__ModelDir=<models-root>/multilingual-e5-small/614241f622f53c4eeff9890bdc4f31cfecc418b3
     Mimamsa__Hybrid__ModelSha256=ca456c06b3a9505ddfd9131408916dd79290368331e7d76bb621f1cba6bc8665
     Mimamsa__Hybrid__CacheDir=<work>/embcache
     ```
     Leave every other `Mimamsa__Hybrid__*` setting at its default. Any non-default value must be reported.

3. **Collect the results.** `run_holdout.py` writes `HOLDOUT_RESULTS.json`, containing:
   - the holdout fixture's SHA-256;
   - the oracle's git blob (checked against HEAD before running);
   - per-case errors and aggregate metrics.

   Report both configurations and the commit.

## Rules

- Do not change the oracle, the fixture or any hybrid parameter after seeing holdout results.
- If a change is made later, the next holdout run is not independent evidence for it.

## C15 configurations (added by C15 S2; run each separately)

**Correction to step 2.** The C14 hybrid result (12/14 on the development fixture) was measured with `Mimamsa__Hybrid__MinSimilarity=0.8579`. The list above says to leave every other setting at its default, which would give a floor of 0. Set the floor explicitly, as below.

All configurations need the C15 build (`claude/c15-hybrid` or later). The provision-heading boost (`Mimamsa__Search__ProvisionHeadings`) is **on by default** in every configuration.

**H-L: lexical + heading boost (default product configuration)**
- No extra variables.

**H-E5S: hybrid, e5-small**
```
Mimamsa__Hybrid__Enabled=true
Mimamsa__Hybrid__ModelDir=<models-root>/multilingual-e5-small/614241f622f53c4eeff9890bdc4f31cfecc418b3
Mimamsa__Hybrid__ModelSha256=ca456c06b3a9505ddfd9131408916dd79290368331e7d76bb621f1cba6bc8665
Mimamsa__Hybrid__CacheDir=<work>/vectors
Mimamsa__Hybrid__MinSimilarity=0.8579
```

**H-E5B: hybrid, e5-base**
- Fetch with `python -I hf_ipv4.py app/b1/hybrid/fetch_models_c15.py <models-root> multilingual-e5-base`.
```
Mimamsa__Hybrid__Enabled=true
Mimamsa__Hybrid__ModelDir=<models-root>/multilingual-e5-base/d128750597153bb5987e10b1c3493a34e5a4502a
Mimamsa__Hybrid__ModelSha256=<onnx/model.onnx sha256 from app/b1/hybrid/manifests/multilingual-e5-base.json>
Mimamsa__Hybrid__ModelLabel=multilingual-e5-base@d1287505
Mimamsa__Hybrid__CacheDir=<work>/vectors
Mimamsa__Hybrid__MinSimilarity=0.8339
```

**H-RR: hybrid, e5-small candidates with cross-encoder rerank (declared configuration)**
- Set the H-E5S variables, plus:
```
Mimamsa__Hybrid__Reranker__Enabled=true
Mimamsa__Hybrid__Reranker__ModelDir=<models-root>/mmarco-mMiniLMv2-L12-H384-v1/1427fd652930e4ba29e8149678df786c240d8825
Mimamsa__Hybrid__Reranker__Sha256=<onnx/model.onnx sha256 from app/b1/hybrid/manifests/mmarco-mMiniLMv2-L12-H384-v1.json>
```
- Leave `Pool` at 30 and `Admit` at 0.

Report every configuration separately, with any non-default value.
