# ADR-0008: Persistent text and passage store

- **Status:** Technically accepted with conditions (development-stage integration, independent ChatGPT review of PR #80, comment 7220574432). The store is selectable; **the operational default stays `memory`**. Making `disk` the default, or any full-corpus deployment, needs owner authorisation and the carried-forward gates in `app/b1/evidence/c16_integration/C16A_COMPLETION_REPORT.md` §4. Since the review, every open binds the store to the generation's records (`DiskTextStore.Bind`); the cost is measured in that report, §3.
- **Date:** 2026-11-27.
- **Context:** C15 moved search postings to disk (ADR-0007) but left generation text in memory. `GenerationStore` holds every page (`DocumentRecord.Pages`) and every passage (`DocumentRecord.Passages`) as .NET strings, and each passage is a separate copy of part of its page, so text is held twice in UTF-16. C15 projected about 7 GB for this at the full corpus, the dominant memory term once the index is on disk. WP04 asks for lazy page and passage retrieval, persistent disk-backed text, bounded caches, stable passage identity, efficient snippets, generation-aware storage, integrity validation and withdrawal-aware access, with no new infrastructure and output identical to today.

## Options considered

| Option | Integrity and publication | Start-up | Integration cost | Result |
| --- | --- | --- | --- | --- |
| Keep text in memory (status quo) | Re-hash at every load | Reads and hashes all text | None | Does not fit the full corpus |
| Read pages straight from the importer's `derived/<sha>.txt` files | Already content-addressed | Still parses and hashes every file at start-up to find page offsets; nothing persisted | Low | Bounded memory, but start-up stays O(corpus) and passage anchors are re-derived every start |
| PostgreSQL table of pages | Transactional | Fast | Medium. Puts every snippet and page read on the database that sessions and policy use; network round-trips per read | Rejected: load on the shared database, and the text would leave the generation directory |
| **Chosen: generation-scoped SQLite file (Microsoft.Data.Sqlite, already a dependency since C15) in the IndexStore style** | Build directory, `fsync`, manifest with SHA-256, atomic rename, quarantine and rebuild; per-document re-hash against `text_sha256` | Opens metadata only; reads no text | Low. One abstraction behind `PageText.Text` and `Passage.Text`; no caller changes | Selected |

## Decision

Persist each accepted derivative's exact bytes (the importer's `derived/<text_sha256>.txt`) in a per-generation SQLite file, with page byte ranges, passage anchors, the text-reliability assessment and the derived-stage load issues. Keep document, page and passage **identity** in memory. Resolve **text** on demand through a per-document `DocumentText` handle behind the existing access points. The in-memory store stays the reference implementation and the default.

## Design

**Selection.** `Mimamsa:Text:Store` = `memory` (default) or `disk`. Other settings: `Dir` (default `<site>/text-store`), `CacheMb` (64), `VerifyOnOpen` (true), `RebuildOnFailure` (true), `KeepPrevious` (2).

**Access points unchanged.** `PageText` and `Passage` are still records with the same members. `Text` returns the held string (memory) or the store's verified string (disk); new `Length` members give the UTF-16 length without a read. Every caller (`ix.Passages[p].Text`, `d.Pages`, `Snippets.Build`, Toc, statute relations, the graph builder, Commander, Studio quotes, the document-text API) is unchanged apart from three `Text.Length` reads that became `Length`.

**Stable passage identity.** `(doc_id, passage_id, page, char_start, char_end, paragraph_label)` is stored in load order and attached exactly as the memory loader attaches it; permalinks, citations and the search index's passage numbering are therefore identical. Passage text is sliced from the verified page, not stored twice.

**On-disk layout.** `<root>/<generation>/text.sqlite` holds `docs` (derivative identity, `text_sha256`, assessment), `texts` (the derivative bytes, one BLOB per document), `pages` (page byte range, UTF-16 length, method, OCR fields) and `passages` (anchors), plus `meta`. `MANIFEST.json` records the format, generation, source digest, counts, file size and SHA-256.

**Build and publish.** The same verification as the memory loader (one shared `ReadDerived`), streamed one document at a time, so build memory is one document. Written to `.building-<generation>-<id>/`, flushed, hashed, manifest written, re-verified, then renamed into place. An exclusive lock file serialises processes sharing a root.

**Open.** Served only if the manifest, size, SHA-256 (`VerifyOnOpen`), `quick_check`, format, generation, counts and **source digest** all match. The digest covers `generation.json`, `derived_text.jsonl` and the loaded documents with their copies. On mismatch the directory is quarantined and rebuilt, or start-up is refused (`RebuildOnFailure=false`). Metadata is read and checked in full before anything is attached.

**Integrity at use.** On the first read of a document's text, its stored bytes are re-hashed against the generation's `text_sha256`, and a 128-bit SHA-256 prefix of every page range is taken from those verified bytes. Every later page read from disk is checked against its page hash before it is decoded or cached. A failure throws `TextIntegrityException`; that document's text stays withheld and other documents are unaffected.

**Bounded cache.** Decoded page strings go to a 16-shard LRU bounded by `CacheMb` (counted as UTF-16 bytes). Passage text is a slice of a cached page.

**Generation-aware.** One directory per generation; up to `KeepPrevious` other generations are kept for rollback and reopened without rebuilding. Retention deletes only directories whose manifest names this format.

**Withdrawal and eligibility.** Unchanged. The store has no route and no lookup by document id: text is reachable only through `DocumentRecord` objects, which every route still obtains through `Eligibility`. Search still drops hidden documents after ranking. Withdrawing a document needs no store change.

## Consequences

- **Measured outcome** (`app/b1/evidence/c16_text_store/TEXT_STORE_REPORT.md`):
  - parity: identical output in every in-process equivalence test (SYN and the real sample), 2,300 byte-identical HTTP responses on the real sample, byte-identical oracle outputs (10/14 with both stores), C# 220/220 and Playwright 81/81 with each store, and one parity hash set across all four store combinations at 290 / 1k / 4k / 10k;
  - memory at 10k: heap after load 165 MB (disk) against 728 MB (memory); with the disk search engine too, start-up ends at 217 MB heap / 441 MB working set against 1,588 / 1,933 MB today;
  - search p95 at 10 readers unchanged by the text store (10k: 558 ms against 564 ms);
  - document-text API warm p95 unchanged (≤ 0.3 ms in-process); cold p95 about 1 ms higher; cold snippets 50–85 µs p50 against about 18 µs warm;
  - start-up at 10k 26.9 s (both disk stores, reopened) against 43.2 s today; disk 1.13 × the UTF-8 derivative text.
- **Start-up with `disk`:** the generation load reads no text. Components that scan text at start-up still read it once, through the store: the in-memory search engine tokenises every passage, the disk search engine reads page 1 of each judgment for cover identifiers, and the hybrid layer hashes every passage. Memory stays bounded either way.
- **Disk:** about 1 × the UTF-8 derivative size, plus page and passage rows.
- **The evaluator (WP05) is untouched.** Its hot loops that read passage text (provision strength, reranking) now go through the cache; their cost at full scale is part of the WP05 top-k work.
