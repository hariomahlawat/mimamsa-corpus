# C15 S2: hybrid retrieval and procedural ranking (WP2, WP7 item)

**Branch** `claude/c15-hybrid` from staging `e10a8647`. Read `DECLARATIONS.md` first: it fixes what was chosen before results were seen and discloses every later change.

## 1. Outcome

| Item | Result |
| --- | --- |
| Unchanged retrieval oracle, hybrid **off** (lexical + heading boost) | **10/14**, unchanged from staging (the 4 hybrid cases fail by design) |
| Oracle, best hybrid configuration | **12/14**. RET-07 and RET-10 still fail under every evaluated configuration. **14/14 not reached**, and not pursued by tuning on oracle text |
| Default | Hybrid stays **off** (not all acceptance holds). The **provision-heading boost is on** (WP7). In hybrid modes, matched provisions form their own tier ahead of fused results; this fixes the C14 Q01 hybrid regression |
| Persistent vectors | Incremental per-passage store, SHA-256 trailer, atomic publish, checkpoints; **interrupted embedding resumed at 16,000/37,558** after a hard kill |
| Withdrawal | Eligibility applied inside the dense scan and before the rerank pool; withdrawn passages never returned and never use up depth (tests) |
| Blind holdout | **Not accessed.** The procedure for the independent evaluator is updated in `app/b1/hybrid/HOLDOUT_PROCEDURE.md` §C15 |

## 2. Baseline, re-run first, before any change

On staging `e10a8647` with this branch's storage-only change; ranking code was unchanged at that point.

| Configuration | Oracle | RET-06 | RET-07 | RET-09 | RET-10 |
| --- | --- | --- | --- | --- | --- |
| Hybrid off | 10/14 | fail (lexical) | fail (lexical; J1-MAJ missing) | fail (lexical) | fail (lexical; J2-MAJ missing) |
| e5-small, floor 0.8579 (C14) | 12/14 | pass | fail (lexical, J1-MAJ missing) | pass | fail (hybrid, J2-MAJ missing) |

This reproduces the C14 S4 report exactly (`runs/` and `E:\Mimamsa-Data\c15s2\eval\baseline-oracle`).

## 3. RET-07 and RET-10: failure mechanism (diagnosis; oracle text read, disclosed)

| Case | Needed in top 10 | Lexical overlap with the query | e5-small dense rank / cosine | e5-base rank / cosine | Cross-encoder rank / logit |
| --- | --- | --- | --- | --- | --- |
| RET-07 "Can someone challenge a hearing when nobody told them the allegation beforehand?" | J1-MAJ ("…Advance written notice was given and no opportunity to respond was lost. Application dismissed.") | none | 11th / 0.8230 | 7th / 0.8066 | below 12th / < −7.6 |
| RET-10 "late warning invalidates hearing without notice" | J2-MAJ ("The failure to furnish a written charge beforehand deprived the member of an opportunity to answer…") | none | 8th / 0.8223 | 5th / 0.8222 | 11th / −5.54 |

**Mechanisms:**
1. **No lexical path.** Neither passage shares a content word with its query, so only the dense layer can admit it.
2. **Compressed cosines and a length-dependent floor.** e5 models place unrelated and related text in a narrow cosine band (0.75–0.87 on the SYN site). A floor calibrated on 256-token real passages (0.8579 for e5-small, 0.8339 for e5-base) sits above these short passages. For RET-07 even the best passage (0.8573) is below the e5-small floor.
3. **Contrary authority is not "similar" or "relevant" to these models.** Both missing passages answer the question by *disagreeing* (J1-MAJ: notice was given, nothing lost) or by restating it in other words (J2-MAJ: "written charge" for "allegation"). A web-QA cross-encoder scores them as non-answers.
4. **Passage granularity** is not the cause: each needed passage is a single short paragraph in the fixture.

**Conclusion:** reaching 14/14 would need either a domain-adapted model (legal paraphrase and contrary-holding retrieval) or a floor and fusion tuned to these two cases. The second would be tuning on the oracle and is not done.

## 4. Configurations evaluated on the unchanged oracle

| # | Configuration | Oracle | Notes |
| --- | --- | --- | --- |
| R1 | Lexical + provision-heading boost (default) | 10/14 | Identical cases to staging; no regression |
| R2 | R1 + e5-small, RRF k=60, floor 0.8579 | 12/14 | As C14 |
| R3 | R1 + e5-small candidates + cross-encoder rerank (fp32, pool 30+30, admit logit ≥ 0) | 12/14 | RET-07 now in hybrid mode, J1-MAJ still missing; RET-10 J2-MAJ missing. Declared configuration, unchanged after the run |
| R5 | R1 + e5-base, RRF k=60, floor 0.8339 (declared rule on a seeded 3,000-passage sample) | 12/14 | Same two failures |
| R2b | R2 with the heading tier (final C15 hybrid) | 12/14 | Unchanged from R2 |

Run outputs (summaries and RESULTS JSON) are committed under `oracle/` (`<run>__oracle-<mode>.txt`, `<run>__<mode>__*RESULTS*.json`). `oracle_identity.txt` records the oracle git blob, which is identical to staging.

## 5. Models (all local, pinned, permissive)

| Model | Role | Licence | Revision | Key file SHA-256 | Size | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| intfloat/multilingual-e5-small | dense | MIT | `614241f6` | `onnx/model.onnx` `ca456c06…` | 470 MB | **Keep** as the optional hybrid model |
| intfloat/multilingual-e5-base | dense | MIT | `d1287505` | see `hybrid/manifests/multilingual-e5-base.json` | 1.1 GB | Evaluated; no oracle gain; ~3× slower embedding (CPU); **not adopted** |
| cross-encoder/mmarco-mMiniLMv2-L12-H384-v1 | reranker | Apache-2.0 | `1427fd65` | see `hybrid/manifests/mmarco-…json` (fp32 and AVX2 quint8) | 471 / 119 MB | Implemented and tested; **not adopted**: no oracle gain and multi-second CPU latency (§7) |
| BAAI/bge-m3 (MIT), bge-reranker-v2-m3 (Apache-2.0), gte-multilingual-base (Apache-2.0) | — | — | — | — | 2.3 GB / no ONNX / no ONNX | Excluded: no published ONNX, or too large for CPU query latency on this host |

**Acquisition:** read-only, through `hybrid/fetch_models_c15.py` (owner-verified IPv4 client). Each LFS file is checked against the Hub's published SHA-256 for the pinned revision. Models stay outside git; the loaders refuse a mismatching file.

## 6. WP7: provision-level procedural ranking (heading boost)

**Rule:** `ProvisionHeadings.cs`, declared in `DECLARATIONS.md`. The query-coverage clause was added after walkthrough observation; this is disclosed.

**C14 walkthrough queries, lexical, boost off vs on** (`runs/lexical_headings_off.json`, `runs/lexical_headings_on.json`). 40 of 43 queries are unchanged.

| Query | Off: top document / passage | On: top document / passage |
| --- | --- | --- |
| Q01 how to hold a summary court martial | Army Act (passage without the provision) | **Army Act s.116 *Summary court-martial*** passage (with s.114) |
| Q13 absence without leave punishment | SC judgment (Madan Prasad) | **s.39 *Absence without leave*** (Air Force Act, then Army Act) |
| Q05 punishments a commanding officer can award | Navy Regulations II | Navy Regulations II; Navy Act's punishment provision now 3rd |

**With service = Army:**
- **Q01:** Army Act s.116.
- **Q13:** Army Act s.39.
- **Q05:** Army Act s.87 (s.80 is not reachable: the held text's TOC finds its heading only in the contents list).
- **Q07** (arrest): BNS still first. "Arrest" vs s.101 "Custody of offenders" needs semantics.

**Residual deficiency:** Q05 → s.80 and Q07 → ss.101–102 remain open (§8).

**Hybrid on the real sample (43 queries):** see §9.

## 7. Latency, memory and storage

See §9 (measured after the sample embedding, with the host otherwise as quiet as possible).

Reranker cost under load: during this stream, concurrent sample embedding and other streams' benchmarks shared the CPU.

| Measure | Result |
| --- | --- |
| fp32 | 315 ms per pair, i.e. 11–33 s for a 60-pair pool |
| AVX2 quint8 | 181 ms per pair, i.e. 9–12 s for a 60-pair pool |

Even at a fraction of these figures when uncontended, a 60-pair pool is multi-second per query on this CPU.

## 8. Open issues

1. **RET-07 and RET-10 (oracle):** need a domain-adapted model or a learned reranker trained on legal paraphrase and contrary holdings; not available locally under a permissive licence today. Evaluate on the independent holdout before adopting anything.
2. **Q05 → Army Act s.80:** the TOC (`Generation/Toc.cs`) does not find s.80's body heading. A text-extraction or TOC issue, outside this stream.
3. **Q07 (arrest → custody):** needs a vocabulary bridge (statutory synonym list, reviewed) or semantics. Not added: a hand-made synonym list is a legal-content decision.
4. **Reranker:** kept as an opt-in seam (`Mimamsa:Hybrid:Reranker:*`) for a future smaller or GPU model. Not recommended on this host.

## 9. Real sample results

### 9.1 43 walkthrough queries

| Q | Query | Staging lexical | C15 lexical (+headings) | C14-style hybrid | C15 hybrid (+heading tier) |
| --- | --- | --- | --- | --- | --- |
| Q01 | how to hold a summary court martial | act:army-1950 | act:army-1950 | SC 1991 ex-havildar-rat-an | act:army-1950 |
| Q13 | absence without leave punishment | SC 2023 ex-sepoy-madan-pra | act:air-force-1950 | act:navy-1957 | act:air-force-1950 |
| Q21 | disability pension attributable to military service | SC 2015 union-of-india-anr | SC 2015 union-of-india-anr | SC 2013 dharamvir-singh-20 | SC 2013 dharamvir-singh-20 |
| Q22 | can high court entertain writ against armed forces tribunal order | HC allahabad 2023 | HC allahabad 2023 | HC jkl 2019 | HC jkl 2019 |
| Q23 | court martial set aside violation of natural justice | SC 2019 union-of-india-thr | SC 2019 union-of-india-thr | SC 1973 captain-harish-upp | SC 1973 captain-harish-upp |
| Q25 | dharamveer singh | SC 2023 dr-jaya-thakur-202 | SC 2023 dr-jaya-thakur-202 | SC 2013 dharamvir-singh-20 | SC 2013 dharamvir-singh-20 |
| Q35 | AFT jurisdiction | notif:aft-kolkata | notif:aft-kolkata | rules:aft-group-b-rrs | rules:aft-group-b-rrs |
| Q43 | सेना अधिनियम | act:bnss-2023-alt-60d145 | act:bnss-2023-alt-60d145 | act:bns-2023-alt-d163e7 | act:bns-2023-alt-d163e7 |

Top-1 document per configuration; only the 8 of 43 queries where any configuration differs are listed. The full runs (top 5 documents, top 3 passages, timings) are in `runs/*.json`.

**Readings** (observations, not relevance judgements):
- **Q01 and Q13:** the C15 configurations lead with the statutory provision. In C14-style hybrid, Q01 had lost the Army Act from the top (two SC judgments led).
- **Q21 and Q25:** hybrid brings Dharamvir Singh to the top, including for the misspelling.
- **Q22, Q23 and Q35:** hybrid changes the lead without a clear gain.
- **Q43:** the Hindi query still leads with BNS/BNSS alternate copies.
- **Identifier queries (13):** the same top passage and mode in every configuration.
- **Unchanged:** 35 queries keep the same top document in all four configurations.

### 9.2 Latency, memory and storage

- **Conditions:** quiet host (CPU 6–7% before the run), i7-10750H, 16 GB, client on the same host. Real sample of 290 documents and 37,558 indexed passages (the unreliable Hindi texts are excluded from search). Tool: `scripts/perf.py`. One run each.

| Configuration | Sequential p50 / p95 | 10 readers p50 / p95 | 25 readers p95 | Working set idle → after load | Start-up |
| --- | --- | --- | --- | --- | --- |
| Lexical + heading boost (default) | 13.5 / 80 ms | 40 / 152 ms | 260 ms | 597 → 1,207 MB | ~6.5 s |
| Hybrid e5-small + heading tier | 39 / 75 ms | 155 / 339 ms | 637 ms | 1,428 → 1,789 MB | +1.2 s to load 37,558 vectors from the store |
| Rerank fp32, pool 30+30 (declared) | p50 4.6 s; p95 788 s (one 13-minute outlier, unexplained) | not run | not run | 2,299 MB | |
| Rerank AVX2 quint8, pool 10+10 | p50 1.4 s; p95 2.2 s | not run | not run | 1,694 MB | |

**Storage:**

| Item | Size |
| --- | --- |
| e5-small vector store | 51.7 MB |
| SYN store | < 0.2 MB |
| e5-small model | 0.47 GB |
| e5-base model | 1.1 GB |
| Reranker (fp32 + quint8) | 0.59 GB |
| **Total models** | **2.08 GB** (budget 8 GB) |

**Embedding:**
- e5-small on CPU: 37,558 passages in about 2 h 10 min. It shared the CPU with other streams' benchmarks; C14 measured 12 passages/s uncontended.
- A hard kill at 16,000 resumed from the checkpoint: 16,000 reused, 21,558 embedded.
- After that, no embedding was needed on later starts.