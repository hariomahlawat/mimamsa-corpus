# C15 S1 / WP1: persistent search index, report

- **Branch:** `claude/c15-search-index`, based on staging `e10a8647`.
- **Decision:** ADR-0006. The B1 evaluator stays; postings move to SQLite (Microsoft.Data.Sqlite 10.0.15).
- **Engine selection:** `Mimamsa:Search:Engine` (`memory` by default, or `disk`). The default is **not** switched in this branch: the p95 latency target is not met (§3), and switching is an owner decision.

## 1. Summary

| Requirement (WP1) | Status | Evidence |
| --- | --- | --- |
| Persistent lexical postings and document metadata | **Done** | `search.sqlite`: `terms`, `docs`, `meta` |
| Bounded-memory architecture | **Done for the index.** Postings are on disk behind a 128 MB LRU, and the vocabulary is in memory. **Not done for generation text** (outside the index; ADR-0006 Consequences) | §3, §4 |
| Incremental indexing and generation management | **Done.** Per-document forward cache, chunked runs, one directory per generation | Tests; §2 |
| Atomic publication and rollback | **Done.** Build to `.building-*`, verify, then rename; `KeepPrevious` retained | Tests |
| Crash recovery and integrity verification | **Done.** Manifest, SHA-256, `quick_check`, digest and counts; quarantine and rebuild, or refuse | §5 |
| Withdrawal and reinstatement across all index components | **Done.** Query-time eligibility, after ranking and before facets, counts and paging, for every tier | Test; C# and Playwright suites with the disk engine |
| Deterministic identifier priority and exact citations | **Preserved bit-for-bit** | §2 |
| Windows-native, Linux-portable, no external service | **Yes.** Bundled e_sqlite3 for win-x64 and linux-x64. Linux not executed here | — |
| p95 ≤ 300 ms at 10 readers, 10k documents | **Not met** (§3) | — |
| Interrupted-import and corruption-recovery tests | **Done** | §5 |

## 2. Equivalence (no retrieval, provenance or withdrawal regressions)

| Check | Result |
| --- | --- |
| Result signatures, 26 queries: every hit's passage, tier and score; reasons of the first 100 hits; chips; facets; highlight terms | **Identical** to the pre-change baseline for the memory engine after the evaluator changes (290, 1k, 4k). Identical between the disk and memory engines (290 built, 290 reopened, 10k reopened) |
| Unchanged retrieval oracle (0 oracle files changed) | **10/14 with both engines** (the same 4 hybrid cases). `observations.json` is byte-identical between the engines |
| C14 walkthrough's 43 real-sample queries, run through the HTTP service | **43/43 identical** between the engines, including all 15 identifier, citation, case-number and party queries (same top-5 documents) |
| C# suite | Memory: **170/170** (160 existing + 10 new). Disk (every spawned service on the disk engine): **170/170** on the final run. An earlier run hit 1 harness time-out (§6) |
| Playwright journeys | **58/58 with the memory engine, 58/58 with the disk engine.** The SYN and sample indexes were built and published by the test servers |

## 3. Benchmarks

**Test conditions**
- Host: i7-10750H (6 cores / 12 threads), 16 GB RAM, Windows 11. In-process `IndexBench`, Server GC.
- Query set: 26 queries. Sequential = 3 repeats each. Concurrent = N threads × 6 passes over the set.
- **The host was shared with three other Cycle 15 streams** (embedding generation, builds and tests). Generation load times varied from 38 s to 946 s for the same 10k site. Latencies are therefore pessimistic and noisy, and the engines were not measured simultaneously.
- Memory figures are taken after a forced full GC.

| Scale (passages) | Engine | Index build or open | Managed heap after index | Working set after index | Seq p50 / p95 | 10 readers p95 | 25 readers p95 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 290 real sample (37,558) | memory | 4.2 s build | 309 MB | 592 MB | 4.3 / 35.8 ms | 78 ms | 94 ms |
| 290 real sample (37,558) | disk | 7.0 s open/build (12.2 MB file) | 165 MB | 561 MB | 3.8 / 35.3 ms | 77 ms | 81 ms |
| 1000 (24,030) | memory | 3.4 s build | 162 MB | 359 MB | 6.8 / 34.2 ms | 62 ms | 66 ms |
| 1000 (24,030) | disk | 5.6 s open/build (6.5 MB file) | 80 MB | 354 MB | 4.8 / 26.3 ms | 61 ms | 59 ms |
| 4000 (98,486) | memory | 10.9 s build | 646 MB | 1,047 MB | 20 / 94.5 ms | 308 ms | 402 ms |
| 4000 (98,486) | disk | 15.1 s open/build (25.4 MB file) | 309 MB | 1,022 MB | 17.7 / 93.1 ms | 208 ms | 256 ms |
| 10k (246,020) | memory | 24.1 s build | 1,585 MB | 2,301 MB | 57 / 320 ms | 1,494 ms | 1,636 ms |
| 10k (246,020) | disk | 17.0 s open (verify included) / 44.2 s first build | 752 MB | 1,001 MB | 83 / 487 ms | 1,166 ms | 1,312 ms |
| **Stress ×10 (2,460,200)** | disk | 406 s build (25 runs, no forward cache) | **1,212 MB** | 2,062 MB | 635 / 3,725 ms | 11,480 ms | — |
| Stress ×10 | memory (extrapolated, not run) | — | ≈ 8.6 GB index + ≈ 0.7 GB | — | — | — | — |

**Index sizes**
- 290: see the rows above (`index_file_mb` in the raw JSON).
- 10k: 62 MB.
- ×10 stress: 579 MB.
- The synthetic 1k–10k sites re-use sample text, so their vocabulary is small (19,477 terms) and their postings compress well. The real corpus will have a larger vocabulary and larger files. The vocabulary is the one index component kept in memory.

**Stress-test method**
- `--replicate 10` clones every document of the 10k site under synthetic ids. The passage-text **strings are shared**, so the stress isolates index scaling: postings, runs and merge, query cost. It does not multiply text memory.
- 2.46M passages is within the ~2–3M projection, so it was reached in full.

**Findings**
1. **Memory: met for the index.** The disk engine removes the index heap: 10k is 752 MB against 1,585 MB, and at 2.46M passages the heap is 1.2 GB against a projected 9 GB or more.
2. **Build memory is bounded by the chunk.** At 100k passages per run, the ×10 build never held more than one chunk of postings.
3. **Latency: target not met.** p95 at 10 readers and 10k documents was 1.2–1.5 s with either engine on the contended host. At ×10 it is about 11 s. Latency is the same order for both engines because **storage is not the bottleneck**. The B1 evaluator is O(matching passages): for a common term at 10k it builds dictionaries and sorts over about 150k–250k hits per query. At full scale that cost grows linearly.
   - What was improved in this branch, with output identical: phrase merge join, `NEAR` binary search, lazy reasons, per-display match counts, cached provision patterns, per-document eligibility memo. Sequential p95 at 10k went from 690 to 320–487 ms.
   - The remaining step is a **top-k evaluator**: array accumulators, MaxScore/WAND-style pruning for ranked tiers, and counts and facets computed without materialising every hit. It changes how results are produced, so it needs its own exactness or acceptance argument for tie-breaking and counts. It is recommended as WP1b and is not attempted here.

## 4. Memory budget at full scale (projection)

| Component | 10k measured (disk engine) | Full corpus, about 2.5M passages |
| --- | --- | --- |
| Generation text and metadata (`GenerationStore`, outside WP1) | ~725 MB | **~7 GB** (linear in text). Dominant; needs a lazy text store |
| Index: vocabulary, per-passage ints, doc tables | ~30 MB | ~0.3–0.6 GB, depending on vocabulary size |
| Posting-list cache | ≤ 128 MB (setting) | ≤ 128 MB |
| Query working memory (transient, GC-retained) | 0.1–1.4 GB working set under load | Grows with matches until top-k (§3) |
| PostgreSQL (private instance, `shared_buffers` 256 MB) | Not sampled in-process | Unchanged by WP1 |

**Conclusion:** the index is no longer what stops the full corpus fitting in 16 GB. Two follow-ups are needed: generation text on disk, and top-k evaluation.

## 5. Recovery and integrity tests (automated, `PersistentIndexTests`, 10)

| Test | Result |
| --- | --- |
| Disk engine equals memory engine, freshly built and reopened (11 queries, full signatures) | Pass |
| A chunked build (3-passage runs, rebasing merge) gives the same postings | Pass |
| Withdrawn documents are never returned (all queries) | Pass |
| An interrupted build (simulated crash after 10 terms) is never served; `.building-*` is removed at the next start; the rebuilt index is identical | Pass |
| A corrupted index file (64 bytes flipped) is detected by SHA-256, quarantined, rebuilt and identical | Pass |
| A truncated index with rebuild disabled and verification off is refused (size mismatch) | Pass |
| A changed source digest is rebuilt, not served | Pass |
| An unreadable forward cache is recreated, not trusted | Pass |
| A rebuild from a warm cache reuses all documents with identical results | Pass |
| Retention keeps the newest `KeepPrevious` other generations | Pass |

### 5a. Manual runs (1k site, real importer output)

1. **Kill during build**
   - Started the disk build (forward cache off) and killed the process 1.5 s after its `.building-*` directory appeared (7 s in).
   - What remained was only `.building-…` and `.lock`; nothing was published.
   - On restart the log read "removing interrupted build", then the index was rebuilt and published.
   - The 26-query signatures were **identical** to the baseline.
2. **Corruption**
   - XORed 256 bytes at 60% of the published 6.5 MB index.
   - On restart the log read "failed verification: index file SHA-256 differs from manifest"; the index was quarantined to `.quarantine-…` and rebuilt from the forward cache (995 documents reused, 0 tokenised).
   - Signatures **identical** to the baseline.

## 6. Issues and limitations

- **One disk-engine C# run failed** `RegisterStartupTests.ServiceRefusesARegisterThatDoesNotMatchTheRelease` with the harness's 60 s "still running". That refusal happens **before** the index is opened, so the engine is not involved; the service was slow to load the generation under host contention. The test passed in 3 of 3 re-runs (9 s, 94 s, 12 s).
- The vocabulary is held in memory. That is acceptable for natural vocabularies, but unmeasured on the real full corpus (OCR noise inflates it).
- `VerifyOnOpen` hashes the whole index file at start-up: about 1 s per GB. It can be turned off; size, format, digest and counts are still checked.
- Linux was not executed. The native SQLite library for linux-x64 ships in the package.
- The ADR number (0006) may collide with other Cycle 15 streams. The coordinator should renumber at integration.
