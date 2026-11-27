# ADR-0006: Persistent search index

- **Status:** Proposed (C15 WP1). The engine is selectable; the default stays `memory` until the owner accepts this ADR.
- **Date:** 2026-11-27.
- **Context:** C14 S4 measured about 6.5 KB of live heap per passage with the B1 in-process index. That projects to roughly 12 GB at the full corpus, which does not fit a 16 GB host with PostgreSQL. Search p95 was 2.25 s at 10 readers on 10,000 documents. WP1 asks for a disk-backed index with bounded memory, incremental indexing, atomic publication and rollback, crash recovery and integrity verification. It must keep identifier priority and exact citations, enforce withdrawal, run natively on Windows, port to Linux, and need no external service.

## Options considered

| Option | Licence and packaging | Memory model | Atomic publish, crash safety, integrity | Result parity with B1 | Integration cost |
| --- | --- | --- | --- | --- | --- |
| **Lucene.NET 4.8** | Apache-2.0, pure .NET. Still versioned `4.8.0-beta` | MMapDirectory; segments; small heap | Commit points, `CheckIndex` | **No.** BM25 uses a lossy one-byte length norm and its own IDF, so scores and order differ. The B1 query language (phrases, `NEAR/n`, `exact:`, fields, identifier tiers, abbreviation expansion, reasons) would need re-implementing as Lucene queries | High. Rewrites the evaluator and re-validates every tier and oracle case |
| **SQLite FTS5** | Public domain; bundled with Microsoft.Data.Sqlite (MIT) | Disk B-tree with page cache | Transactions, WAL, `integrity-check` | **No.** Its tokeniser, phrase/NEAR semantics and bm25 IDF (`log((N-n+0.5)/(n+0.5))`) differ from B1 | Medium-high. Same evaluator rewrite as Lucene |
| **Tantivy via native binding** | MIT, Rust native library | mmap | Segments, commits | No; different scorer. P2's Tantivy figures don't transfer | High. Native build and maintenance on Windows, with no maintained .NET binding |
| **PostgreSQL full-text** | Already deployed | Server-side | Transactional | No. P2 measured weaker nDCG (0.62 against 0.72) | Medium. It also moves search load onto the database that sessions and policy use |
| **Custom on-disk BM25 (own file format)** | — | mmap | Hand-built: WAL, checksums, recovery | Yes | High. Reinvents storage, transactions and crash safety |
| **Chosen: B1 evaluator + postings in SQLite tables** | Microsoft.Data.Sqlite 10.0.15 (MIT) with SQLitePCLRaw e_sqlite3 (Apache-2.0 / public domain). Native win-x64 and linux-x64 included. Offline | Vocabulary in memory; posting lists on disk, read on demand through a bounded LRU cache | SQLite's transactional engine and `quick_check`, plus a file manifest with SHA-256, plus atomic directory rename | **Yes, bit-for-bit.** The same posting lists in the same vocabulary order feed the unchanged evaluator | Low. One storage abstraction (`PostingTable`); the evaluator is untouched apart from performance fixes |

## Decision

Keep the B1 evaluator, which is the validated behaviour: identifier, case-name, title and mention tiers, BM25 scores, phrases, `NEAR`, fields, reasons and facets. Persist its postings in **SQLite used as a storage engine**: a mature, embedded, transactional, crash-safe store. SQLite's FTS5 scorer is **not** used.

This avoids re-implementing storage and transactions ourselves (custom format), and avoids changing retrieval semantics (Lucene, FTS5, Tantivy).

## Design

**Engine selection**
- `Mimamsa:Search:Engine`: `memory` (B1) or `disk`. The other settings are `IndexDir` (default `<site>/search-index`), `CacheMb` (128), `VerifyOnOpen` (true), `RebuildOnFailure` (true) and `KeepPrevious` (2).
- `PostingTable` has two implementations, memory and SQLite. Both give the same vocabulary order (first occurrence, which prefix expansion depends on) and identical lists.

**On-disk layout**
- `<root>/<generation>/search.sqlite` holds three tables:
  - `terms(ord, term, df, postings)`: varint-delta encoded;
  - `docs(di, doc_id, derivative_id, service, lens)`;
  - `meta`.
- `<root>/<generation>/MANIFEST.json` records the format, generation, source digest, counts, file size and SHA-256.

**Build and publish**
1. Tokenise. For incremental builds, reuse the forward cache (below).
2. Write to `.building-<generation>-<id>/`.
3. `VACUUM`, then `fsync`.
4. Hash the file, then write the manifest (fsync, rename).
5. Re-verify.
6. `Directory.Move` to `<generation>/`. That is an atomic rename on the same volume, so a reader sees a complete index or none.

**Open**
- An index is served only if all of these match the generation being served: manifest, size, SHA-256 (`VerifyOnOpen`), `PRAGMA quick_check`, format, generation, the **source digest** of the indexed documents (doc ids, derivative ids, copy hashes, passage anchors), and the counts.
- On any mismatch the directory is moved to `.quarantine-*`. It is then rebuilt from the verified generation, or start-up is refused (`RebuildOnFailure=false`).

**Crash recovery**
- Interrupted builds leave only a `.building-*` directory. That is never opened, and it is deleted at the next start.

**Rollback**
- Published indexes of up to `KeepPrevious` other generations are retained. If the ACTIVE generation is rolled back, its verified index is reopened without rebuilding.

**Incremental indexing**
- `forward-cache.sqlite` caches each document's passage tokens under `(doc_id, derivative_id, format)`. A build tokenises only new or changed documents.
- An entry whose passage anchors differ is ignored. An unreadable cache is recreated. Stale entries are pruned after a build.
- The postings produced are identical either way.

**Withdrawal and eligibility**
- Unchanged and enforced at query time. Hits whose document is hidden (withdrawn, ineligible, restricted) are removed after ranking, before facets, counts and paging. That is the same as the memory engine and covers every tier.
- No index component returns a hidden document, and the index content does not need rewriting on withdrawal.

**Text-reliability exclusion**
- Unchanged: unreliable documents are not indexed by either engine. The exclusion is part of the source digest's document list.

**Hybrid**
- Unchanged. `ISemanticScorer` and `DenseIndex` read `SearchIndex.Passages`, which both engines provide.

## Evaluator performance (both engines)

There are three output-preserving changes:
- `PhraseOccurrences` is a merge join over the passage-ordered lists, with binary search on positions. Previously every posting went into a dictionary of HashSets.
- `Spans` (`NEAR`) uses binary search, not linear scans.
- `Reasons` strings are built lazily, only for hits that are read (the displayed page).

Each was verified against signatures captured before the change. Every hit's passage, tier and score, the reasons of the first 100 hits, chips, facets and highlight terms were all identical, on the real sample and on the 1,000- and 4,000-document sites. At 10,000 documents no pre-change baseline was captured; there the two engines were compared with each other, and their results were identical (see INDEX_REPORT).

## Measured outcome (details in app/b1/evidence/c15_index/INDEX_REPORT.md)

- **Exactness:**
  - identical results between the engines on 26 bench queries at 290 / 1k / 4k / 10k;
  - identical on the 43 walkthrough queries through the HTTP service;
  - byte-identical oracle observations (10/14 with both engines);
  - C# 170/170 and Playwright 58/58 with each engine.
- **Index heap removed:**

  | Scale | Disk engine | Memory engine |
  | --- | --- | --- |
  | 4k | 309 MB | 646 MB |
  | 10k | 752 MB | 1,585 MB |
  | 2.46M-passage stress | 1.2 GB | ≈ 9 GB projected |

- **Bounded build:** 100k-passage runs.
- **Recovery:** interrupted-build and corruption recovery verified, automatically and manually.
- **Latency target (p95 ≤ 300 ms at 10 readers, 10k documents): not met.**
  - 4k: met (208 ms).
  - 10k: 1.2–1.5 s with either engine, on a host shared with other streams.
  - The cost is the evaluator's per-hit work, not storage (§ Consequences).

## Consequences

- The index heap is removed; postings live on disk with a bounded cache. The vocabulary stays in memory.
- **The generation's passage and page text is still held in memory by `GenerationStore`, outside WP1.** At full scale that text, not the index, becomes the dominant memory term (INDEX_REPORT §4). A follow-up should give `GenerationStore` a lazy, disk-backed text store. It touches about 70 call sites across Statutes, Toc, Api and others, and is recommended as the next step.
- **Start-up:** an existing verified index is reopened without tokenising. Hashing the file costs about 1 s per GB; it can be disabled (`VerifyOnOpen=false` still checks size, format, digest and counts).
- **Disk:** about 1 × the text size for the index, plus about 1–1.5 × for the forward cache.
