# C16 Stage 3 S3-B: findings and closure register

**Scope.** B04 component verification and accelerator adoption; B10 model and knowledge release compatibility
(development path only). Development keys only; disposable directories; no operational trust or activation change, no
AUTH-LEDGER or oracle change, no HF write, no merge, no Codex review. Report: [`S3B_REPORT.md`](S3B_REPORT.md).
Calibration evidence: [`CALIBRATION_STUDY.md`](CALIBRATION_STUDY.md), [`calibration.json`](calibration.json).

| Item | Was (CP-1 report §7, item 5 and blockers) | Status after S3-B | Evidence (tests) |
| --- | --- | --- | --- |
| **S3B-01** GRAPH verifier | GRAPH verified only by the loader's full re-derivation; no structural recheck, no sampled rebuild parity | **Built** (Python reference + .NET site + central S9): GRAPH_DIGEST, full GRAPH_STRUCTURAL_RECHECK, SAMPLED_REBUILD_PARITY over source documents (`GraphBuilder.Build(g, includeSource)`). The loader's full re-derivation is **kept** (stronger; see report §3) | `C16S3bVerificationTests`: clean, non-builder value, dangling edge, unresolved page, rewritten edge/node/dropped edge with matching digest, residual risk outside the sample; `test_c16_verification.py::test_graph_structural_recheck`; `test_kbuild_s3b.py`; CP-1 slice `s3b_b04_graph_structural_and_sampled_rebuild_*` |
| **S3B-02** LEXICAL_INDEX verifier | file hash and `quick_check` only | **Built**: manifest and SHA-256, quick_check, SOURCE_DIGEST_EQUALS_SITE, SAMPLED_POSTINGS_REDERIVE (docs rows, every term of the sampled documents, a decoded vocabulary sample), SAMPLED_QUERY_PARITY (real `SearchService` on the shipped index vs the same index with the sampled documents' postings rebuilt on site) | dropped/shifted postings, altered lengths and service with a re-pinned manifest, a byte flip, a wrong source digest; CP-1 slice `s3b_b04_lexical_postings_and_query_parity_*`; `test_kbuild_s3b.py` (posting rewritten with matching manifest refused centrally) |
| **S3B-03** Lexical index adoption | rebuilt by the app at every start (not adopted); only TEXT_STORE adopted | **Built, development only**: `Mimamsa:Search:AdoptShipped=development` adopts the shipped index after the B04 checks (inventory hash first); default null never adopts; no production value while OD-C16-UNCALIBRATED-PRODUCTION is open (production builds its own, exact index) | `AVerifiedShippedIndexIsAdoptedWithoutARebuildAndATamperedOneIsRebuilt` (adopted index gives the memory engine's results; tampered one is rebuilt) |
| **S3B-04** VECTOR_PACK verifier | a shipped pack was FAILED (not verifiable) | **Built**: streamed trailer, every key recomputed, 2.1 vector source digest, result digest, stratified spot re-embed (one input per call; the site never embeds the corpus) | clean (embeds exactly the sample), swapped vectors with matching digest, noise, foreign/missing keys, truncated/flipped file, mismatched model and pack, no model (NOT_RUN, not verified); Python reference tests |
| **S3B-05** Calibration | sizes and tolerances UNCALIBRATED; no evidence | **Evidence produced, gate NOT flipped**: measured study on the real 290-document sample and synthetic scale; proposals for owner decision. Contracts unchanged; production refuses | `CALIBRATION_STUDY.md`; `test_every_contract_sampled_check_stays_uncalibrated_and_production_never_runs_it`; `ProductionNeverRunsAnUncalibratedSampledCheck...` |
| **S3B-06** B10 model release (development) | no model staging; a placeholder model was the only path | **Built, development only**: `ModelStaging` (signature under purpose `model`, inventory, manifest, install, ONNX self-test, packs verified, REFUSE_RELEASE), M1/M2/K1 through the journal, `DenseIndex.FromVerifiedPack` (never embeds passages). Production refuses (`MODEL_TRUST_PURPOSE_NOT_AUTHORISED`). Real e5-small run recorded | `C16S3bModelTests` (4), `C16S3bRealModelTests` (local, real model), `b10-real-model-evidence.json` |
| **S3B-07** Central side | B02 S9: full rebuild parity only | S9 also runs the site's B04 verifiers centrally (`b04_central` in VERIFY.json; refusal BUILD_B04_CENTRAL); `build-vectors` and `build-model-release` commands; KBuildVerify and Mimamsa.Hybrid added to the stage code digests | `test_kbuild_s3b.py` (4) |

## Open (not closed by S3-B)

- **OD-C16-UNCALIBRATED-PRODUCTION** (owner gate): OPEN, fails closed. **FG-CALIBRATED-SAMPLES**: OPEN (proposals only).
- **FG-MODEL-TRUST-PURPOSE**: OPEN. No trust key or trust list was added or changed; the development model trust list is not
  v1-schema-valid by design.
- Residual risks: sampled checks bound systematic corruption only (a single tampered unit outside the sample passes; the
  signed inventory, not the sample, protects against post-signing tampering); query parity is weak against single-passage
  corruption (postings re-derivation carries the lexical check); GRAPH sampled-only mode is not enabled (the loader's full
  re-derivation still runs); the web hybrid path (`Mimamsa:Hybrid`) still embeds missing passages at start and is not
  wired to `FromVerifiedPack` under activation (S3-D surfaces); real-corpus FULL knowledge release with vectors through
  B02 S6/S7 is not built here (vectors ship in the intelligence release).
