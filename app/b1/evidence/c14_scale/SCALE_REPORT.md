# C14 S4: scale benchmarks and memory analysis

**Status:** measured on 2026-11-26. Every number below comes from `app/b1/bench/run_scale_bench.py`; the raw JSON is in `E:\Mimamsa-Data\c14s4\bench\*.json` (outside git) and is reproduced in `bench_results/` alongside this report. Nothing is estimated unless it says so.

## 1. Test conditions

| Item | Value |
| --- | --- |
| Host | Intel i7-10750H (6 cores / 12 threads), 16 GB RAM, Windows 11, NVMe E: |
| Service | Mimamsa.Web Release build from `claude/c14-scale-hybrid` (`fcf0e8d7` plus the MinSimilarity wiring); console process; HTTP loopback port 5443; **not** test mode; hybrid **off**; `Mimamsa:Diagnostics:Enabled=true` (numbers-only memory endpoint) |
| Database | Private PostgreSQL 18.6, 127.0.0.1:55499, `shared_buffers` 256 MB. A fresh database `c14s4_bench` per run, pool size 10 |
| Client | Python `urllib` on the same host. 20 queries: identifier, citation, case number, phrase, NEAR, Boolean and plain. Readers are separate signed-in sessions |
| Contention | Other Cycle 14 streams may have run builds or tests on the same machine during these runs (not controlled). One run per configuration, so figures are indicative, not statistical |
| Runs | 2026-11-26 21:50–22:01 IST, strictly sequential |

**Bench sites.** `app/b1/bench/build_scale_site.py` clones committed-sample documents (a pool of 220) under synthetic ids. Each clone has unique original bytes (a trailer after `%%EOF`). They go through the real path: contract dev bundle, then `import_release` with every hash verified. The 290 scale is the real sample. **Synthetic clones have fewer passages per document than the real mix:** 1k has 24,195 passages, fewer than the 290-document sample's 38,445. Compare scales by **passage count**, not document count.

| Scale | Documents | Passages | Site size | Bundle write | Import (verify + activate) |
| --- | --- | --- | --- | --- | --- |
| 290 (real sample) | 290 | 38,445 | 0.42 GB originals | — | — (commissioning build) |
| 1,000 | 1,000 | 24,195 | 0.19 GB | 34.5 s | 25.8 s |
| 4,000 | 4,000 | 99,113 | 0.76 GB | 265.8 s | 145.7 s |
| 10,000 | 10,000 | 247,538 | 1.89 GB | 553.1 s | 396.6 s |

All bench imports activated with 0 refused and 0 unresolved.

## 2. Results (Server GC, the .NET default)

| Scale | Start-up to healthy | Load + re-hash | Index build | First search | Search 1 reader p50 / p95 | 10 readers p50 / p95 (req/s) | 25 readers p50 / p95 (req/s) | 64 KiB range p50 / p95 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 290 | 9.2 s | 5.2 s | 2.3 s | 161 ms | 20 / 84 ms | 66 / 187 ms (118) | 133 / 243 ms (153) | 7.8 / 16.8 ms |
| 1,000 | 17.5 s | 13.6 s | 2.5 s | 185 ms | 18 / 87 ms | 52 / 175 ms (152) | 137 / 222 ms (173) | 6.2 / 11.0 ms |
| 4,000 | 55.9 s (cold cache) | 48.0 s | 6.3 s | 518 ms | 46 / 158 ms | 164 / 653 ms (45) | 466 / 1,051 ms (49) | 6.6 / 10.2 ms |
| 10,000 | 131.3 s | 113.2 s | 15.1 s | 1,156 ms | 86 / 548 ms | 404 / 2,252 ms (13.6) | 1,281 / 4,679 ms (13.6) | 6.4 / 12.5 ms |

The second and third 4,000 runs (GC comparison, §4) started in 18–20 s with load and re-hash at about 10 s. The first run paid a **cold OS file cache**. Re-hashing every original at start-up is I/O-bound: about 12 s per GB cold and about 13 s per 4,000 documents warm.

## 3. Memory: GC retention vs leaks

Each scale ran 5 load cycles. Each cycle is 25 readers × 200 searches, sampled before and after a forced, blocking, compacting full GC (`/api/diag/memory?gc=1`).

| Scale | Live managed heap after forced GC, cycles 1→5 (MB) | Working set before GC (MB) | Working set after GC (MB) | GC committed after GC (MB) |
| --- | --- | --- | --- | --- |
| 290 | 313 · 310 · 311 · 319 · 311 | 978–1,118 | 847–914 | 720–777 |
| 1,000 | 166 · 166 · 169 · 169 · 168 | 740–767 | 622–645 | 503–529 |
| 4,000 | 648 · 648 · 648 · 648 · 647 | 1,808–1,976 | 1,206–1,351 | 1,225–1,454 |
| 10,000 | 1,589 · 1,589 · 1,589 · 1,589 · 1,588 | 3,229–3,600 | 2,509–2,774 | 2,624–2,848 |

**Conclusion:**
- **No leak was observed.** The live heap after a forced GC is flat to within ±3% across cycles at every scale.
- **Growth in working set under load is GC retention.** Server GC keeps freed segments committed (heap before GC is 2–2.5× the live set) and does not return them promptly. A forced compacting GC releases 15–30% of the working set.
- **This revises the C14 walkthrough's F14 observation** (0.73 → 1.34 GB, "not returned"): that is retention, not a leak.

**The real constraint is the live set itself.** It grows linearly with passages: about 6.4–8.1 KB of managed heap per passage (290: 8.1 KB; 4k: 6.5 KB; 10k: 6.4 KB).

> Estimate, not measured: the full corpus is about 20 GB of originals. At the real sample's density (38,445 passages per 0.42 GB) that is roughly 1.8 M passages, so about 12 GB of live heap for the in-memory index alone. That **does not fit** a 16 GB host alongside PostgreSQL, the OS and GC headroom.

**PostgreSQL** (working set of all processes of the private cluster): 340–430 MB at service start, 550–640 MB after the 25-reader load. It is flat across scales, because B1 keeps only sessions, credits and policy in PostgreSQL.

## 4. GC configuration (4,000 documents, same site, consecutive runs, warm cache)

| Mode | Start-up | Working set after start / after load | 10 readers p50 / p95 (req/s) | 25 readers p50 / p95 (req/s) |
| --- | --- | --- | --- | --- |
| Server, default (DATAS on) | 55.9 s (cold) | 944 / 1,820 MB | 164 / 653 ms (45) | 466 / 1,051 ms (49) |
| Server, DATAS off (`DOTNET_GCDynamicAdaptationMode=0`) | 18.3 s | 1,654 / 2,358 MB | 155 / 604 ms (47) | 387 / 855 ms (54) |
| Workstation (`DOTNET_gcServer=0`) | 20.5 s | 786 / 2,389 MB | 283 / 1,017 ms (26) | 870 / 2,303 ms (24) |

**Recommendation:** keep the default Server GC with DATAS.
- Workstation GC halves throughput and still reaches the same peak working set.
- DATAS-off buys about 10–20% latency for about 700 MB more resident memory.
- None of the three changes the live set.
- Memory headroom must come from the index design (§5), not GC flags.

## 5. Persistent, bounded and incremental indexing: evaluation

| Option | Evidence | Verdict |
| --- | --- | --- |
| Serialise the in-memory index per generation (load instead of rebuild) | Index build is 2.3 s at 290, 6.3 s at 4k and 15.1 s at 10k: 11–15% of start-up. Load and re-hash dominates at 79–86% | **Low value for start-up.** It saves at most about 15 s at 10k and does nothing for memory. Not implemented |
| **Disk-backed (memory-mapped) postings** for the lexical index | The live heap is about 6.5 KB per passage, so about 12 GB at full corpus (estimate, §3). Search latency at 10k with 10 readers (p95 2.25 s) shows the in-memory scan is CPU-bound as postings grow | **Required before the full-corpus import.** Recommended design: per-generation immutable segment files (term dictionary, delta-encoded postings, positions, a stored-fields offset table) opened with `MemoryMappedFile`. The OS page cache then becomes the bounded cache, and managed heap holds only the term dictionary. The P2 evidence measured Tantivy for the same method. A C# segment format keeps the in-process, offline, single-binary property. **Not implemented in C14 S4:** it is a substantial component and needs its own review |
| Bounded caches | No unbounded cache was observed in the request path. Growth is GC retention (§3). Passage text is held once in the index | Nothing to bound today. Introduce bounded LRU caches only with the disk-backed postings (snippets, stored fields) |
| Incremental indexing | Generations are immutable and activated atomically; the importer re-verifies everything | Keep **per-generation** builds. Incremental means a new segment per added release, merged offline. That follows naturally from segment files and should not be added to the in-memory design |
| Start-up re-hash cost | 113 s at 10k (about 1.9 GB); about 12 s per GB cold | Keep re-hash (it is an integrity guarantee, F01/importer). Consider parallel hashing across files and caching (size, mtime, hash), verified per generation, for warm restarts. The decision belongs to the security owner |

## 6. Bottlenecks in order

1. **Live index memory** at full corpus (about 12 GB estimated): disk-backed postings.
2. **Concurrent search latency at 10k and above:** p95 2.25 s at 10 readers and 4.7 s at 25, at 13.6 req/s. Postings scan and scoring are CPU-bound. The disk-backed design should add skip lists and top-k pruning (WAND/MaxScore).
3. **Start-up re-hash** grows linearly: about 2 min at 10k, so tens of minutes at full corpus on a cold cache.
4. PDF delivery is **not** a bottleneck: 64 KiB range p95 is 10–17 ms at every scale.

## 7. Not measured

- Scales beyond 10,000.
- Hybrid search at bench scales (embedding 247k passages on CPU is about 5.6 h at the measured 12 passages/s; see HYBRID_REPORT).
- More than 25 readers.
- Readers on other machines.
- The Windows Service host.
- Repeated runs for confidence intervals.
- A cold-cache start for scales other than 4k-first.
