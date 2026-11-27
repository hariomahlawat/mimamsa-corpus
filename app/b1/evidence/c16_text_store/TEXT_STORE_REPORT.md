# C16 WP04: persistent text and passage store, report

- **Branch:** `claude/c16-text-store`, based on staging `c8fa5290`.
- **Decision:** ADR-0008 (`docs/architecture/decisions/ADR-0008-PERSISTENT_TEXT_STORE.md`; renumber at integration if needed).
- **Store selection:** `Mimamsa:Text:Store` = `memory` (default, the reference) or `disk`. Other settings: `Dir` (default `<site>/text-store`), `CacheMb` (64), `VerifyOnOpen` (true), `RebuildOnFailure` (true), `KeepPrevious` (2).
- **Default not switched.** Parity is complete and the memory saving is large, but switching is an owner decision, and the cold-read costs below should be seen on the real corpus first. Recommendation: switch to `disk` together with the `disk` search engine once the owner accepts ADR-0007 and ADR-0008.

## 1. Summary

| Requirement | Status | Evidence |
| --- | --- | --- |
| Lazy page and passage retrieval | **Done.** `PageText.Text` and `Passage.Text` resolve on demand through a per-document `DocumentText` handle; opening a store reads no text | `OpeningReadsNoTextAndReadsAreVerifiedAndCached` |
| Persistent disk-backed text | **Done.** One SQLite file per generation (Microsoft.Data.Sqlite, already a dependency). No new infrastructure | §4 |
| Bounded caches | **Done.** 16-shard LRU of decoded pages, bounded by `CacheMb` | `TheCacheStaysWithinItsBudgetAndOutputIsUnchanged`; `text_store_stats` in raw JSON |
| Stable passage identity | **Done.** Ids, pages, offsets and labels are attached in load order exactly as in memory mode; passage numbering, permalinks and citations are identical | §2 |
| Efficient snippet retrieval | **Done.** A passage is a slice of a cached page; warm snippet cost equals memory mode | §3 |
| Generation-aware storage | **Done.** One directory per generation, source digest, `KeepPrevious` retention, reopen without rebuild | `RetentionKeepsTheNewestOtherGenerationStores`, `AChangedDerivativeRecordIsRebuiltNotServed` |
| Integrity validation | **Done.** Manifest SHA-256 and `quick_check` on open; each document re-hashed against the generation's `text_sha256` on first use; every later page read checked against a page hash taken from the verified bytes | §5 |
| Withdrawal-aware access | **Done, unchanged.** No new route or lookup; text is reached only through `DocumentRecord`s obtained via `Eligibility`. Verified through HTTP on both stores | §2, §5 |
| Equivalence tests for both stores | **Done.** Search and snippets, document-text API, citations and permalinks, Studio quotes, graph quotes, Commander excerpts, Toc and statute relations | §2 |
| Memory engine kept as reference | **Yes.** Default `memory`; the disk build runs the same `ReadDerived` verification code | — |

## 2. Parity (identical output from both stores)

| Check | Result |
| --- | --- |
| In-process equivalence (`TextStoreTests`): every derivative field, text assessment, load issue (in order), page (order, fields, text) and passage (order, identity, text); document-text API projection for every document; citation, permalink, internal reference and Studio quote for every passage; 18 queries with full hit signatures **and snippets** (text, highlights, truncation) for the first 60 hits, chips, facets; Toc of every statute; every Commander domain item; the full `GraphBuilder` graph (all edge quotes); statute relations | **Identical** on the SYN site (freshly built and reopened) and on the **real 290-document sample** |
| HTTP, real sample, two services side by side (`bench/text_store_http.py`): every document's metadata, every 40-page text window, sections, relations, citations (first, middle and last page), 26 queries (pages 1 and 2), every Commander domain, graph stats, graph resolve and node for every statute and 40 judgments; repeated after a withdrawal | **2,300 responses byte-identical** after removing the timing field `ms` (one response digest `c5d3ef25…` for both) |
| Withdrawal through HTTP (a judgment, both services) | Text **404**, citation **404**, **0** search hits, on both |
| IndexBench parity hashes (26-query signatures, document-text API for every sampled document, snippets of the first 20 hits of each query) | **One hash set per scale across all four configurations** (text memory/disk × search engine memory/disk) at 290, 1k, 4k and 10k |
| Unchanged retrieval oracle, hybrid off (oracle blob `3884f86c`, 0 oracle files changed) | **10/14 with both stores** (RET-06, 07, 09, 10, the recorded hybrid cases). `RESULTS.json`, `observations.json` and `oracle_output.json` are **byte-identical** between the stores |
| C# suite (`dotnet test -c Release Mimamsa.B1.slnx`) | Memory: **220/220** (207 existing + 13 new). Disk (`MIMAMSA_TEST_TEXT_STORE=disk` for in-process loads and `Mimamsa__Text__Store=disk` for every spawned service): **220/220** |
| Playwright (SYN and real sample, Chromium, 1 worker, ports 5660/5661) | Memory: **81/81**. Disk: **81/81** |

## 3. Benchmarks (measured)

**Conditions.**
- Host: 12 logical CPUs, 16 GB RAM, Windows 11. In-process `IndexBench` (Server GC), one process per configuration, run one after another.
- **The host was shared with other Cycle 16 streams** (their builds, tests and Playwright runs were active). Latencies are noisy; memory figures are after a forced full GC and are stable.
- Synthetic sites were regenerated with `bench/build_scale_site.py` (clones of sample documents with unique originals, through the real importer) under `E:\Mimamsa-Data\bench\c16b\`, then deleted.
- Query set: the 26 C15 queries. Sequential = 3 repeats; 10 readers = 10 threads × 6 passes.
- Document-text API = the `/api/documents/{id}/text` default window (pages 1–40) projected and serialised as the route does, for 290 or 300 sampled documents. *Cold* = first use after start-up; *warm* = the same documents again.
- Snippet = `Snippets.Build` for the first 20 hits of each query (as the search API does), in microseconds.
- Configurations: **A** text memory + search memory (today's default); **B** text disk + search memory; **C** text memory + search disk (C15 option); **D** text disk + search disk. Disk stores were built once beforehand; the rows are reopen runs.

### 3a. Memory (managed heap / working set, MB, after forced GC)

| Scale (passages; derivative text) | Config | After generation load | After index (start-up done) | End of run |
| --- | --- | --- | --- | --- |
| 290 real (37,558; 27.7 MB) | A | 138 / 259 | 301 / 542 | 313 / 798 |
| | B | **39** / 122 | 252 / 462 | 265 / 778 |
| | C | 138 / 272 | 157 / 284 | 176 / 566 |
| | D | **39** / 124 | **58 / 150** | 96 / 379 |
| 1k (24,030; 14.4 MB) | A | 72 / 191 | 161 / 364 | 171 / 540 |
| | D | **17** / 97 | **27 / 123** | 52 / 283 |
| 4k (98,486; 59.5 MB) | A | 292 / 416 | 644 / 923 | 682 / 1,347 |
| | B | 69 / 211 | 488 / 839 | 523 / 2,163 |
| | C | 295 / 462 | 310 / 477 | 363 / 980 |
| | D | **69** / 177 | **94 / 233** | 194 / 725 |
| 10k (246,020; 148.5 MB) | A | 728 / 946 | 1,588 / 1,933 | 1,682 / 2,673 |
| | B | **165** / 351 | 1,093 / 1,587 | 1,186 / 2,695 |
| | C | 728 / 1,047 | 755 / 1,058 | 896 / 2,321 |
| | D | **165** / 406 | **217 / 441** | 400 / 1,504 |

At 10k the text store removes **563 MB of heap** at load (728 → 165 MB). With both disk stores (D), start-up ends at **217 MB heap and 441 MB working set**, against 1,588 / 1,933 MB today (A) and 755 / 1,058 MB with only the search index on disk (C). "End of run" includes transient query and cache memory after the 10-reader load.

### 3b. Start-up, latency, snippets, disk

| Scale | Config | Start-up (load + index), s | Search seq p95, ms | **Search p95, 10 readers**, ms | Doc-text API cold p50 / p95, ms | Doc-text API warm p50 / p95, ms | Doc-text API 10 readers p50 / p95, ms | Snippet cold p50 / p95, µs | Snippet warm p50 / p95, µs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 290 | A | 3.7 + 3.2 = 6.8 | 19 | 77 | 0.1 / 1.3 | 0.1 / 1.3 | 0.2 / 2.6 | 19 / 40 | 18 / 37 |
| | B | 2.4 + 5.3 = 7.6 | 23 | 86 | 0.1 / 1.1 | 0.1 / 1.2 | 0.2 / 5.1 | 25 / 50 | 22 / 43 |
| | C | 3.6 + 1.2 = 4.9 | 20 | 58 | 0.1 / 1.3 | 0.1 / 1.5 | 0.1 / 4.0 | 32 / 66 | 30 / 55 |
| | D | 2.4 + 1.2 = **3.6** | 32 | 68 | 0.4 / 6.1 | 0.1 / 1.6 | 0.2 / 3.6 | 54 / 240 | 39 / 69 |
| 1k | A | 2.9 + 2.7 = 5.6 | 15 | 53 | 0.0 / 0.4 | 0.0 / 0.3 | 0.1 / 0.6 | 20 / 54 | 18 / 40 |
| | D | 1.5 + 2.2 = **3.7** | 19 | 44 | 0.2 / 1.5 | 0.0 / 0.4 | 0.1 / 0.7 | 35 / 183 | 25 / 43 |
| 4k | A | 9.2 + 7.9 = 17.1 | 87 | 416 | 0.1 / 0.2 | 0.1 / 0.3 | 0.1 / 0.5 | 17 / 61 | 16 / 57 |
| | B | 4.6 + 9.2 = 13.7 | 56 | 275 | 0.1 / 1.1 | 0.1 / 0.2 | 0.1 / 0.5 | 40 / 179 | 24 / 53 |
| | C | 7.7 + 3.0 = 10.8 | 65 | 166 | 0.1 / 0.2 | 0.1 / 0.2 | 0.1 / 0.5 | 20 / 51 | 19 / 45 |
| | D | 6.4 + 3.7 = **10.1** | 70 | 172 | 0.3 / 1.6 | 0.1 / 0.3 | 0.1 / 0.6 | 84 / 174 | 19 / 53 |
| 10k | A | 26.7 + 16.6 = 43.2 | 146 | 1,283 | 0.1 / 0.3 | 0.1 / 0.2 | 0.1 / 0.5 | 17 / 51 | 16 / 41 |
| | B | 18.7 + 23.0 = 41.7 | 174 | 1,131 | 0.2 / 1.8 | 0.0 / 0.2 | 0.1 / 0.4 | 73 / 178 | 14 / 41 |
| | C | 25.8 + 6.4 = 32.2 | 137 | 564 | 0.1 / 0.2 | 0.0 / 0.2 | 0.1 / 0.5 | 19 / 60 | 17 / 53 |
| | D | 18.8 + 8.1 = **26.9** | 135 | **558** | 0.3 / 1.1 | 0.1 / 0.2 | 0.1 / 0.5 | 80 / 159 | 15 / 36 |

| Disk | 290 | 1k | 4k | 10k |
| --- | --- | --- | --- | --- |
| Derivative text (UTF-8, per document) | 27.7 MB | 14.4 MB | 59.5 MB | 148.5 MB |
| `text.sqlite` | 29.5 MB | 16.4 MB | 67.4 MB | 168.1 MB (1.13 ×) |
| `search.sqlite` (C15, for comparison) | 12.2 MB | 6.5 MB | 25.4 MB | 62.3 MB |
| First build of the text store (from the build log) | 2.3 s | — | — | 11.8 s |

**Findings.**
1. **Memory:** the generation's text heap is gone. At 10k the managed heap after load is 165 MB with the disk store against 728 MB in memory; with both disk stores the service starts at 217 MB heap.
2. **Search latency is unchanged by the text store.** At 10k and 10 readers, p95 is 558 ms (D) against 564 ms (C); at 4k 172 against 166 ms. The 10-reader target still depends on the evaluator (WP05).
3. **Document-text API:** warm p50/p95 equals memory mode (≤ 0.3 ms in-process). Cold p95 rises by about 1 ms (verification of the derivative and page reads). Over HTTP on the real sample the route's cost is dominated by serialising up to 40 pages and is the same for both stores (§3c).
4. **Snippets:** warm cost equals memory mode (15–40 µs p50). A cold snippet costs 50–85 µs p50 and up to 240 µs p95 (one page read from SQLite and, for a document's first use, its verification).
5. **Start-up:** with both disk stores the service is ready in 26.9 s at 10k against 43.2 s today; most of what remains is the existing re-hash of originals in the vault. The first start of a generation builds the text store (11.8 s at 10k, streamed one document at a time).
6. **Disk:** 1.13 × the UTF-8 derivative text.

### 3c. Through the service (HTTP, two services side by side, pool 8, shared host)

| Site | Store | Doc-text API cold p50 / p95, ms | warm p50 / p95, ms | 10 readers p50 / p95, ms | Search 10 readers p50 / p95, ms | Heap / working set after GC, MB | Start-up (load + index), s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 290 real, search engine memory | memory | 3.6 / 29.0 | 3.5 / 31.6 | 9.8 / 297 | 28 / 570 | 325 / 1,450 | 3.2 + 3.0 |
| | disk | 3.3 / 34.3 | 3.1 / 33.7 | 10.3 / 334 | 30 / 642 | 277 / 1,560 | 2.3 + 5.5 |

HTTP latencies include authentication against PostgreSQL (connection pool 8, because other streams were using the 50-connection instance) and JSON serialisation of up to 40 pages per response, so they are much higher than the in-process numbers, and they are the same order for both stores. The two services ran on the same host at the same time.

An HTTP run at 10k (300 documents, disk search engine, pool 8) was attempted twice and **did not complete**: the first time the services ran out of PostgreSQL connections (the instance is shared and capped at 50); the second time ten concurrent logins and searches on the **memory-store** service stopped answering within the 120 s client timeout after the document-text phase had finished (3,600 text requests answered on both services). The disk-store service was not the one that stalled, but the cause was not isolated and the run was not repeated; 10k figures in this report are in-process only.

## 4. Design in brief

- `<root>/<generation>/text.sqlite`: `docs` (derivative id, `text_sha256`, pipeline, quoting flag, text assessment), `texts` (the exact derivative bytes, one BLOB per document), `pages` (byte range, UTF-16 length, method, OCR fields, in load order), `passages` (id, page, UTF-16 offsets, label, in load order), `meta` (format, generation, source digest, derived-stage load issues). `MANIFEST.json`: format, generation, source digest, counts, file size, SHA-256.
- **Build:** `GenerationStore.ReadDerived` (shared with memory mode) yields one verified derivative at a time; build memory is one document. Written to `.building-*`, flushed, hashed, manifest written, re-verified, renamed into place, under an exclusive lock file.
- **Open:** manifest, size, SHA-256, `quick_check`, format, generation, counts and source digest (`generation.json`, `derived_text.jsonl`, loaded documents and copies). Metadata is read and checked in full before anything is attached. Any failure: quarantine and rebuild, or refuse (`RebuildOnFailure=false`).
- **Read path:** cache → (first use of the document: whole derivative re-hashed against `text_sha256`, 128-bit page hashes taken) → page byte range read with incremental BLOB I/O → page hash checked → decoded → cached. Passage text is sliced from the page.
- **Code touched:** `Generation/Models.cs` (`PageText`, `Passage` lazy text and `Length`), `Generation/GenerationStore.cs` (`ReadDerived`, store selection), new `Generation/TextStore.cs`, `Web/Program.cs` (configuration, log line, numbers-only stats in `/api/diag/memory`), `Web/Api.cs` (document `pages[].chars` uses `Length`).
- **Search/* files touched (for WP05 integration):** only `Search/IndexStore.cs` (1 line: `SourceDigest` uses `p.Length` instead of `p.Text.Length`) and `Search/ForwardCache.cs` (2 lines: the same in `Encode` and `TryDecode`). The values are identical, so index digests and forward-cache entries are unchanged; it only avoids reading every passage's text at index open. `SearchService`, `SearchIndex`, `PostingTable`, `Snippets` and the evaluator are **not modified**.

## 5. Integrity and recovery tests (automated, `TextStoreTests`, 13)

| Test | Result |
| --- | --- |
| Disk store equals memory store on the SYN site, freshly built and reopened (all surfaces in §2) | Pass |
| Same on the real 290-document sample | Pass |
| Opening reads no text; first use verifies the document once; repeated reads come from the cache | Pass |
| An 8 KB cache stays within budget while every page and passage is read twice; output identical | Pass |
| Withdrawn and ineligible documents stay hidden (search, `Eligibility.Visible`) | Pass |
| Bytes changed inside a stored derivative (whole-file check off) are detected at first use against `text_sha256`; the document stays withheld; other documents are unaffected | Pass |
| 64 bytes flipped in the store file: SHA-256 mismatch, quarantined, rebuilt, identical | Pass |
| Truncated store with rebuild disabled: start-up refused | Pass |
| Interrupted build (crash after 2 documents): never served; `.building-*` removed at the next start; rebuilt store identical | Pass |
| A changed `derived_text.jsonl`: source digest differs, rebuilt, identical to memory mode | Pass |
| A tampered derivative file: the same `DERIVATIVE_TEXT_HASH_MISMATCH` load issue and identical text in both stores | Pass |
| 8 concurrent readers over a 128 KB cache get identical text | Pass |
| Retention keeps the newest `KeepPrevious` other generations and never deletes a directory without a text-store manifest | Pass |

## 6. Open issues and limitations

- **Default stays `memory`** (owner decision). Recommended to switch together with the disk search engine.
- **Components that scan text at start-up still read it once through the store:** the in-memory search engine tokenises every passage (configuration B is therefore no faster to start than A), the disk search engine reads page 1 of every judgment for cover identifiers, and the hybrid layer hashes every passage. Memory stays bounded; start-up time could be cut further by persisting cover identifiers in the search index (WP05 territory).
- **Evaluator hot loops** (`Identifiers.ProvisionStrength` over candidate passages, reranking) now read text through the cache. No regression was measured, but on the real corpus a cold cache adds page reads to the first query; the 64 MB default should be revisited with real query logs.
- **Synthetic sites re-use 220 sample texts**, so the cache hit rate at 1k–10k is optimistic; the page-read and verification costs per miss are real.
- **Residual heap with the disk store** (document records, candidates, page and passage identity) is about 165 MB at 10k (≈0.67 KB per passage, an upper bound because document metadata is included). A linear projection to about 2.5 M passages is about 1.7 GB, against about 7 GB of text held today. This is a projection, not a measurement.
- **A text-integrity failure surfaces as a 500 for that document's request** (fail closed). It is logged by the store's exception message; no alerting exists yet.
- **No HTTP measurement at 10k** (§3c): the attempted run stalled on the memory-store service under 10 concurrent logins and searches with an 8-connection pool; not isolated. Worth repeating on a quiet host with a larger pool.
- Linux was not executed (Microsoft.Data.Sqlite ships linux-x64 natives, as for C15).
- `VerifyOnOpen` hashes the whole store file at start-up (about 1 s per GB; the 10k file is 168 MB); it can be turned off because each document is still verified against `text_sha256` before use.

## 7. Raw evidence (`raw/`)

- `bench-<scale>-text_<store>-engine_<engine>.json`: IndexBench results (memory, start-up, latencies, snippets, cache statistics, parity hashes). `build-<scale>.json`/`.log`: first-build runs.
- `site-build-<n>.json`: synthetic site builds.
- `http-290.json`: HTTP parity, withdrawal, latency, memory and start-up.
- `oracle-memory/`, `oracle-disk/`: unchanged-oracle outputs for each store.
