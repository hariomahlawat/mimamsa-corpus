# C16 Stage 3 S3-B: component verification, accelerator adoption and model compatibility (development)

- **Branch:** `claude/c16-s3b-verify` from `claude/c16-cp1` @ `4ba059fa`. Draft PR against `claude/c16-cp1`.
- **Scope:** B04 kind-specific verifiers (central and on site), lexical-index adoption, calibration *evidence*, and the
  B10 development path for model releases and vector packs.
- **Not done here (by instruction):** no production activation or trust change, no contract value calibrated, no
  AUTH-LEDGER or oracle change, no HF write, no merge, no Codex review. Development keys only.
- **Findings and closure:** [`REVIEW_CLOSURE_REGISTER.md`](REVIEW_CLOSURE_REGISTER.md). Calibration study:
  [`CALIBRATION_STUDY.md`](CALIBRATION_STUDY.md) and [`calibration.json`](calibration.json).

## 1. What was built

| Kind | Checks (all real; site = `Mimamsa.Core.ComponentVerification`, central = `KBuildVerify` in kbuild S9, reference = `mimamsa_contract.c16.verification`) |
| --- | --- |
| GRAPH | `GRAPH_DIGEST` (GraphStore digest over the shipped ids); `GRAPH_STRUCTURAL_RECHECK` over every row; `SAMPLED_REBUILD_PARITY`: a stratified sample of source documents rebuilt by `GraphBuilder.Build(g, includeSource)` (new filter; the unfiltered build is byte-identical to before) and compared row for row both ways |
| LEXICAL_INDEX | manifest/size/SHA-256/quick_check; `SOURCE_DIGEST_EQUALS_SITE`; `SAMPLED_POSTINGS_REDERIVE` (docs rows + every term of the sampled documents + a decoded vocabulary sample); `SAMPLED_QUERY_PARITY` (the real `SearchService` on the shipped index vs the same index with the sampled documents' postings rebuilt on site; identical hits, tiers and score bits) |
| LEXICAL_INDEX adoption | `SearchIndexOptions.AdoptShipped` / `Mimamsa:Search:AdoptShipped`: `development` adopts the shipped index after the inventory hash and the B04 checks; null (default) never adopts. No production value (OD gate) |
| VECTOR_PACK | streamed `VECTOR_TRAILER`; `VECTOR_KEYS_RECOMPUTED` (no foreign key, no missing passage); 2.1 `vector_pack_source_digest`; `RESULT_DIGEST`; stratified `VECTOR_SPOT_REEMBED`, **one input per embed call** |
| KNOWLEDGE_ROWS | unchanged: the B03 loader's full re-derivation |
| B10 | `ModelStaging` (dev only), `GenerationStaging.VerifyVectorPack` against the installed verified model, model `vectors_for` updated on staging, `DenseIndex.FromVerifiedPack` (never embeds passages), kbuild `build-vectors` and `build-model-release` |

**Staging (`GenerationStaging`).** Each accelerator's input state now comes from the B04 verifier. Evidence per component is
returned in `StagingReport.Verification` (not written into the generation directory, which the marker binds). In
**production** no uncalibrated sampled check runs (`NOT_RUN`), and since such a contract is uncalibrated by construction
the outcome rule refuses with `UNCALIBRATED_IN_PRODUCTION` — the 2.1 rule is unchanged and production keeps refusing.

**GRAPH design note.** The loader's full re-derivation of the graph rows is kept: it is the stronger check and costs
seconds at this scale. Switching GRAPH to the sampled check alone (to avoid the full GraphBuilder run at scale) is an
owner decision that depends on the calibration (see the study). The sampled check runs in addition today.

## 2. Shared files touched (small, listed)

| File | Change |
| --- | --- |
| `Mimamsa.Core/Activation/GenerationStaging.cs` | runs the B04 verifiers; vector pack against an installed model (`models` callback, `VerifyVectorPack`); lexical-only classification also from a degraded vector outcome; model `vectors_for` updated |
| `Mimamsa.Core/Graph/GraphBuilder.cs` | `Build(g, includeSource)` overload (null = unchanged) |
| `Mimamsa.Core/Search/IndexStore.cs`, `SearchIndex.cs` | `AdoptShipped` option and `Origin`; `LoadFile` / `OpenForVerification` / `WithPostings` internal hooks |
| `Mimamsa.Core/Mimamsa.Core.csproj` | `InternalsVisibleTo C16Calibration` (bench) |
| `Mimamsa.Hybrid/E5Embedder.cs`, `DenseIndex.cs` | `IPassageEmbedder.EmbedOne`; `FromVerifiedPack` |
| `Mimamsa.Web/Program.cs` | one line: `AdoptShipped = conf["Mimamsa:Search:AdoptShipped"]` (default null) |
| `app/kbuild/mimamsa_kbuild/stages.py` | S9 calls `verify.central_b04`; two code-digest inputs (KBuildVerify, Hybrid) |
| `app/kbuild/mimamsa_kbuild/cli.py` | `build-accel` also builds KBuildVerify; `build-vectors`, `build-model-release` |
| `app/contract/fixtures/c16/build_fixtures_2_1.py` | writes `component_verification/golden.json` |
| `docs/architecture/c16/interfaces/B04_COMPONENT_VERIFICATION.md` §6, `README.md` row 11 | 2.1 additive item 11 (flagged) |
| `C16Cp1SliceTests.cs` | two journey checks (`s3b_b04_*`) and the `component_checks_not_run` line |

New: `ComponentVerification/{B04Sampling,GraphVerifier,LexicalIndexVerifier,VectorPackVerifier}.cs`,
`Activation/ModelStaging.cs`, `c16/verification.py`, `kbuild/verify/` (KBuildVerify), `kbuild/mimamsa_kbuild/verify.py`,
`bench/C16Calibration/`, tests below.

## 3. B10 development path with the real model (`b10-real-model-evidence.json`)

Model: `intfloat/multilingual-e5-small@614241f6`, `model.onnx` sha256 `ca456c06…`, 384-d, max tokens 256; real
290-document sample (generation `R13-b1-sample-20261126-4b31855f`, 285 indexed documents, 37,558 passages, 34,918 distinct
inputs).

| Step | Result |
| --- | --- |
| Central pack (`KBuildVerify vectors`, 6 threads, below-normal) | 34,918 entries; **0 embedded** (all reused from the C15 central content-keyed cache; keys recomputed and spot-checked on site); `result_digest 7fc21d7b…`, `source_digest e3bc27c4…` (`central-vector-pack-summary.json`) |
| Intelligence release (`build-model-release`) | 12 files, MKR-1 `INTELLIGENCE`, `signing_purpose: model`, contract rules clean, DEVELOPMENT key; dev trust list with purpose `model` (not v1-schema-valid by design) (`b10-model-release-SIGNING.json`) |
| Production staging | **refused** `MODEL_TRUST_PURPOSE_NOT_AUTHORISED` before reading |
| Development staging | OK in 40.5 s: signature, inventory, manifest, install, ONNX self-test (norm 1.0000000001), pack **VERIFIED** (trailer, 34,918 keys recomputed, source and result digests, spot re-embed 32 passages, **max abs difference 0**); **33 embed calls in total** (probe + 32), never the corpus |
| `release`-purpose key | refused `MODEL_SIGNATURE` |
| Journal | K1 before the model: `NO_MODEL`; MODELS (M1, M2 waived over lexical-only L1); KNOWLEDGE (K1 met); pin `semantic_search: true` |
| Serving | `DenseIndex.FromVerifiedPack`: 37,558 passages loaded in 2.5 s, **0 embedded on site**; top-1 for a desertion query `act-air-force-1950` (0.894) |
| B04 on the real sample (dev defaults) | LEXICAL_INDEX VERIFIED (64 of 285 docs, 33,934 terms re-derived, 32 queries; 13 s); GRAPH VERIFIED (64 of 290 docs, 4,656 edges and 3,720 nodes compared; 2.4 s) |
| Outcome rule | development **ACTIVE_FULL** (uncalibrated in use: GRAPH, LEXICAL_INDEX, VECTOR_PACK); production **REFUSED `UNCALIBRATED_IN_PRODUCTION`** |
| Mismatched model (e5-base installed for the e5-small pack) | **FAILED** (model and pack mismatch) |
| Missing pack | `MISSING` → lexical-only |

KNOWLEDGE_ROWS and TEXT_STORE inputs in that outcome come from the CP-1 slice (B03 loader, `DiskTextStore.Bind`); a
real-corpus knowledge release is S3-A's. The FULL knowledge release with a VECTOR_PACK assembled by B02 S6/S7 is not
built here: the vectors ship in the intelligence release (arch §6 "model change").

## 4. Tests

| Suite | Result (local Windows host) |
| --- | --- |
| Contract (`test_c16_verification.py` 15 new + interfaces) | 159 passed (with `test_c16_interfaces.py`); 2.1 fixtures `--check` clean |
| kbuild (incl. `test_kbuild_s3b.py` 4 new) | 44 passed |
| B1 `C16S3b*` (19: verifiers, golden values, adoption, staging vector states, 4 B10) | 19 passed (CI runs them) |
| B1 `C16S3bRealModelTests` (real model; local only) | 1 passed |
| CP-1 slice (CI) | green with the new `s3b_b04_*` journey checks |

CI ids: see the PR (recorded in the final report).

## 5. Open gates

OD-C16-UNCALIBRATED-PRODUCTION (open, fails closed); FG-CALIBRATED-SAMPLES (open; proposals only); FG-MODEL-TRUST-PURPOSE
(open; no trust change). Residual risks are listed in the closure register.
