# PR #80: disposition of the independent ChatGPT review (pullrequestreview-6088057215)

- **Reviewed head:** `891a1c76`. All findings were accepted and fixed with targeted regression tests.
- **Defaults unchanged:** text store `memory`, search engine `memory`.
- **Not changed:** the oracle, AUTH-LEDGER, or PR #77.
- **Reviews:** no Codex review was requested, per owner instruction.

## P1: reopened cache metadata bound to the authoritative generation records
**The problem:** on reopen the store attached its own derivative hash, quoting flag, page ranges and passage metadata. These were checked only against a locally writable manifest and digest, and first-use verification used the store's own `text_sha256`.

**The fix** (`Generation/TextStore.cs`, `DiskTextStore.Bind`):
- Every reopen re-derives each document from the generation's records and source derivative files, using the same `ReadDerived` rule as the memory store, one document at a time, so memory stays bounded.
- The stored metadata must match that derivation exactly:
  - derivative id, `text_sha256` and pipeline;
  - `quoting_permitted`;
  - every page (number, byte range, length, method, confidence);
  - every passage (id, page, offsets, paragraph label);
  - the text assessment;
  - the ordered load issues.
- Any difference quarantines the store and rebuilds it from source, or refuses it when `RebuildOnFailure=false`. This holds whatever `VerifyOnOpen` is set to; `VerifyOnOpen` now governs only the whole-file SHA-256 and `quick_check`.
- First-use verification therefore hashes the stored bytes against a `text_sha256` that has been bound to the records.
- The cache can no longer grant quoting or change legal evidence.

**Tests:** `TextStoreTests.ReopenedMetadataIsBoundToTheGenerationRecords`, 8 cases: {quoting flag, page range, paragraph label, substituted text plus its own hash} × VerifyOnOpen {true, false}.
- Each alteration is paired with a regenerated, self-consistent manifest.
- Each case asserts refusal with rebuilding disabled, then quarantine, rebuild, quoting equal to memory, and every text fact equal to memory.
- On the pre-fix code, 6 of the 8 fail. The two page-range cases were already rejected by the existing anchor sanity check.

## P1: a failed document never serves cached pages
**The fix** (`DiskDocumentText`):
- `_failed` is volatile, published before the document's cached pages are removed, and checked before and after every cache hit and after each read.
- A `TextIntegrityException` reaching a route now gives a controlled, content-free `503 {state: "integrity_failure"}` (`Program.cs` middleware) instead of an unhandled 500.

**Test:** `TextStoreTests.AFailedDocumentNeverServesItsCachedPages`.
- Warm page A is cached, then cold page B is corrupted in place. Six concurrent readers read A in a loop while B fails.
- Asserted: zero reads that started after the failure was published return text; A and its passages then throw; other documents are unaffected.
- It fails on the pre-fix code.

## P2: derivative availability and load issues after reopen
**The fix:** the same binding recomputes availability from the source files on every reopen. Defined recovery semantics, now identical to the memory store:
- a derivative restored after the build is served, without the earlier load issue;
- a derivative removed or corrupted after the build (same length) is withheld with `DERIVATIVE_TEXT_MISSING` or `DERIVATIVE_TEXT_HASH_MISMATCH`.

In both cases the store is rebuilt from source; it is never patched.

**Tests:**
- `ADerivativeRestoredAfterTheBuildIsAvailableAfterReopen`, with VerifyOnOpen true and false.
- `ADerivativeRemovedOrCorruptedAfterTheBuildIsNotServedAfterReopen`, covering remove and same-length corrupt, each with VerifyOnOpen true and false.

All 6 cases fail on the pre-fix code.

## Database connection exhaustion during the 10k web benchmark: cause and fix
**Reproduction:** `app/b1/bench/pool_probe.py` on the real 290-document sample, pool 8, 10 clients. The stall does not depend on corpus size:
- with keep-alive, 12,765 of 14,564 requests were refused, because sign-ins failed with Npgsql "connection pool has been exhausted" and the surviving ones took 15,140 ms, the pool timeout;
- with a new connection per request, 21 requests completed in 20 s.

The raw figures are in `raw/pool_probe_290.txt`.

**Causes:**
1. **Hold-and-wait in sign-in.** `IdentityStore.LoginDetailedAsync` held a pooled connection through the PBKDF2 hash (600,000 iterations), then called `AuditAsync`, which opens a second connection. Once concurrent sign-ins reached the pool size, each held one connection and waited for another until the pool timed out. `UnlockAsync` had the same pattern.
2. **A drain transaction on every closed HTTP connection.** Each one ran a ledger drain (`CreditLedger.DrainConnectionAsync`, which takes the site-wide credit lock), even when that connection had never reserved credit.

**Fixes:**
1. Sign-in and unlock hold a connection only for the statements that need it, never across the hash or the audit write.
2. A pool that never attempted a reservation in this instance skips the drain; only `TryReserveAsync` writes rows with a `conn_pool`, so it has nothing to drain. Pools are marked before the reservation transaction begins, so every committed reservation is still drained. Prior instances are still reconciled at start-up.

**Tests:** `ConnectionPoolTests`.
- 24 concurrent sign-ins (successful, wrong password and unknown user) on a pool of 2. This fails on the pre-fix code with the original exhaustion error.
- A drain for a pool that never reserved touches no database. This is proven with a data source pointed at a closed port.
- A drain for a pool that did reserve still reaches the database.

**After the fix**, same host and method, pool 8, 10 clients, 0 errors and 0 pool errors in every run:

| Site | Configuration | Client connections | Requests | p50 / p95 (ms) |
| --- | --- | --- | --- | --- |
| 290 sample | memory | keep-alive / new per request | 19,257 / 4,859 in 20 s | 9.6/19.9 · 16.5/86.7 |
| 10k synthetic | memory text + memory engine | keep-alive / new per request | 9,613 / 6,850 in 60 s | 48.6/134.4 · 66.9/207.3 |
| 10k synthetic | disk text + disk engine | keep-alive / new per request | 10,556 / 6,937 in 60 s | 47.3/118.5 · 62.3/242.1 |

The raw figures are in `raw/pool_probe_10k_after.txt`.

**Limits:**
- The 10k site is synthetic: 220 base texts are reused and the vocabulary is small. This is a stability measurement of the web path under pool pressure, **not a claim of 10k real-corpus HTTP acceptance**.
- PostgreSQL runs on the same host.
- These figures include sign-in, session checks and JSON serialisation.

## Regression on the corrected head

| Suite | Default (memory/memory) | Disk text + disk engine |
| --- | --- | --- |
| C# | 243/243 | 243/243 |
| Playwright (SYN and real sample) | 81/81 | 81/81 |

- **Retrieval oracle (unchanged files):** 10/14 with hybrid off, 12/14 with hybrid on, as on staging.
- **Evaluator parity:** unaffected, because no evaluator code changed. The 290-document signature from `891a1c76` (`9cc23a42…`) still applies.

## Not addressed here (recorded for release activation)
- **Retention, store-root ownership and concurrent live-generation lifecycle:** the review lists these as items to review before release activation, not as proven defects. They belong to WP06 activation design (PR #77).
- **CI:** it runs both suites in the default configuration. The disk configuration is exercised locally (above) and by the disk-mode C# tests in `TextStoreTests`; it is not yet a separate CI matrix leg.
