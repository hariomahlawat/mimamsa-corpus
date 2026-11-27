# C16 Tranche A: completion report (WP04 text store, WP05 evaluator), PR #80

- **Branch:** `claude/c16-integration`, from staging baseline `c8fa5290a7f03ed47f57ba82cc57503005e11d48` (the Cycle 15 merge).
- **Merged here:** WP04 (`claude/c16-text-store`, draft PR #78) and WP05 (`claude/c16-evaluator`, draft PR #79).
- **Not here:** the contract checkpoint (PR #77) is a separate review.
- **Review history:**
  - Independent ChatGPT review 6088057215: REWORK, with findings R01–R03 (two P1, one P2). All three were fixed; see `PR80_REVIEW_DISPOSITION.md`.
  - Closeout comment 7220574432: **ACCEPT WITH CONDITIONS** (development-stage integration).
- **Not authorised:** this technical acceptance conveys no merge authorisation; owner authorisation is still required.

## 1. What this branch delivers

| Work package | Result | Evidence |
| --- | --- | --- |
| WP04 persistent text and passage store (ADR-0008) | **Store:** a verified, generation-scoped SQLite store with lazy pages and passages, a bounded cache and atomic publication.<br>**Binding:** on every open it is bound to the generation's records (`Bind`); the store can never grant quoting or alter evidence.<br>**Parity:** output is identical to the in-memory store. | `c16_text_store/TEXT_STORE_REPORT.md`, `PR80_REVIEW_DISPOSITION.md` |
| WP05 search evaluator | Exact optimisations. At 10k (synthetic), 10-reader p95 fell from 633 to 81 ms (memory engine) and from 461 to 58 ms (disk engine). Results are byte-identical to Cycle 15 across 2,062 cases at 290, 1k, 4k and 10k. | `c16_evaluator/EVALUATOR_REPORT.md` |
| Review fixes R01–R03 | Bind to the authoritative records; a failed document never serves cached pages; availability is recomputed on reopen. | `PR80_REVIEW_DISPOSITION.md` |
| Connection-exhaustion fix | **Cause:** sign-in held one pooled connection and requested a second for the audit write (hold-and-wait), and every closed HTTP connection ran a ledger drain under the site lock.<br>**Fix:** connections are scoped per statement group, and pools that never reserved skip the drain.<br>**Result:** 0 errors at 290 real and at 10k synthetic, with pool 8 and 10 clients. | `PR80_REVIEW_DISPOSITION.md`, `raw/pool_probe_*.txt` |

## 2. Acceptance conditions (comment 7220574432) and their status

| # | Condition | Status |
| --- | --- | --- |
| 1 | Benchmark start-up and reopen after `Bind()`, reporting cold build and warm reopen separately with integrity verification on, with actual timing and memory, and without implying that synthetic results mean real-corpus acceptance | **Done**: §3 |
| 2 | Keep the separate disk-backed CI leg | **Retained**: the "Disk configuration" steps in `.github/workflows/app-ci.yml`, Linux `b1` job |
| 3 | Carry forward full-corpus gates as mandatory before full-corpus deployment | **Recorded**: §4 |
| 4 | Update the completion report and ADR status; confirm the final head, the staging baseline and final green CI | **Done**:<ul><li>this report;</li><li>ADR-0007 and ADR-0008 status updated;</li><li>baseline above;</li><li>final head and CI are confirmed in the PR comment that publishes this commit.</li></ul> |
| 5 | Keep operational defaults memory/memory; no production activation or corpus admission; no oracle or AUTH-LEDGER change; no Codex review | **Held** |

## 3. Start-up and reopen after `Bind()` (condition 1)

**Method:** `IndexBench --build-only` (script: `app/b1/bench/local/c16_startup_bind_bench.ps1`). Each row is a fresh process; the four rows of a site ran in the order listed.
- **"Disk":** disk text store and disk search engine, with `VerifyOnOpen=true` (whole-file SHA-256 and `quick_check`) and `Bind` (re-derivation from the generation's records and source files) on every open.
- **Cold build:** no store and no index on disk.
- **Warm reopen:** the store and index built by the cold run are opened again.

**Load** is generation load, which includes re-hashing the originals in the vault (a cost every configuration shares), plus the text store's open or build and its `Bind`. **Memory** is measured after a forced GC at the end of start-up.

**Host:** Intel i7-10750H (12 logical CPUs), 15.8 GB RAM, Windows 11, local NVMe. PostgreSQL was idle; no other benchmark was running.

| Site | Run | Load ms | of which `Bind` ms | Index ms | Process total ms | Managed heap MB | Working set MB |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 290 real sample | memory baseline | 8,512 | — | 2,974 | 12,555 | 309.0 | 569.0 |
| 290 real sample | disk, cold build | 5,079 | — (store built) | 8,908 | 14,450 | 115.7 | 532.1 |
| 290 real sample | disk, warm reopen 1 | 4,364 | 1,352 | 1,519 | 6,237 | 66.5 | 173.7 |
| 290 real sample | disk, warm reopen 2 | 4,172 | 1,328 | 1,426 | 5,929 | 66.5 | 149.0 |
| 10k **synthetic** | memory baseline | 135,666 | — | 19,056 | 156,666 | 1,587.7 | 1,953.8 |
| 10k **synthetic** | disk, cold build | 30,825 | — (store built) | 32,455 | 64,027 | 259.5 | 1,206.9 |
| 10k **synthetic** | disk, warm reopen 1 | 23,282 | 8,746 | 10,612 | 34,551 | 226.1 | 459.7 |
| 10k **synthetic** | disk, warm reopen 2 | 21,488 | 8,873 | 8,276 | 30,330 | 226.1 | 472.4 |

**Store size:** `text.sqlite` is 29.5 MB at 290 and 168.1 MB at 10k. The cold build of the text store itself took 2.6 s at 290 and 14.6 s at 10k (from the store's own log); the rest of the cold-run index time is the index build.

**Reading the numbers:**
- **`Bind` cost.**
  - It is the price of making the store an untrusted accelerator: about 1.3 s for 290 real documents (27.7 MB of text) and about 8.8 s for 10k synthetic documents (148.5 MB). That is roughly 4.6 ms per real document and 0.9 ms per synthetic one.
  - It reads and hashes every source derivative once and builds one document's metadata at a time, so memory stays bounded: about 66 MB heap at 290 and 226 MB at 10k after start-up.
  - It grows with total text bytes and passage count, not with the cache.
- **The 10k memory baseline's 135.7 s load** includes reading 1.89 GB of originals and all derivative text from a cold OS cache: it ran first, right after the site was built. Later rows benefit from the OS file cache. The cold-versus-warm difference in the disk rows is therefore partly OS caching, not only store work.
- **Synthetic sites reuse 220 base texts**, so the cache and dictionary behaviour flatter them. These rows are start-up measurements of the mechanism, **not full-corpus acceptance**. A real-corpus projection is not made here; it is a carried-forward gate (§4).

Raw rows: `raw/startup_bind_bench.json`.

## 4. Mandatory gates carried forward before full-corpus deployment (condition 3)
None of these is claimed as met by this branch:

1. **Real full-corpus HTTP and concurrency:** search, document text, citations and sign-in under realistic concurrency on the real corpus, not the synthetic 10k. This includes the connection-pool sizing that the corpus and site actually need.
2. **Memory and disk budget:**
   - measured heap, working set, text store, index, vectors and PostgreSQL at full-corpus scale;
   - measured `Bind` and start-up at full scale;
   - a measured disk-budget preflight that refuses activation when it fails.
3. **Store-root ownership:** text-store and index roots outside the site directory, owned by the service account, not writable by readers, with a defined backup and exclusion policy.
4. **Generation lifecycle:** behaviour when a new generation becomes active while readers hold the old one (pinning, draining, closing the old store).
5. **Retention:** the active release plus two previous distinct, verified releases, with configurable limits. Never prune an active, pinned, in-flight or sole-recovery generation (owner decision; the C16 contract, PR #77).
6. **Crash-consistent activation and rollback:** a journal with one commit decision, exclusions re-applied before exposure, and recovery that refuses to serve until it completes. These are specified in PR #77 and must be implemented and proven on the site.
7. **Calibrated correctness checks** for accelerators (index, graph, vectors) against real-corpus evidence.

## 5. Defaults and scope (condition 5)
- **Defaults:** `Mimamsa:Text:Store=memory` and `Mimamsa:Search:Engine=memory`. Switching to `disk` remains an owner decision.
- **Not done:** no production activation, no corpus admission, no change to the oracle (unchanged at 10/14 with hybrid off and 12/14 with hybrid on) or the AUTH-LEDGER, and no Codex review.
- **Local commissioned app:** the one on port 5199 still runs the Cycle 15 build; it is not updated by this branch.

## 6. Verification summary

| Check | Default (memory/memory) | Disk text + disk engine |
| --- | --- | --- |
| C# (243 tests) | 243/243 | 243/243 (local, and in the CI disk leg) |
| Playwright (SYN and real sample) | 81/81 | 81/81 (local; SYN in the CI disk leg) |

- **Retrieval oracle:** 10/14 with hybrid off and 12/14 with hybrid on, in both configurations.
- **Evaluator parity at 290:** identical to the Cycle 15 baseline signature in all engine and store combinations.
- **CI on `7ae64cbb`:** all 16 checks green, including the disk leg. The final head's CI is confirmed in the publishing PR comment.
