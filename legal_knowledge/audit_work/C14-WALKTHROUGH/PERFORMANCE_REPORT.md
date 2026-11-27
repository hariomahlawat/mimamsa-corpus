# B1 walkthrough: performance (C14)

## Test conditions

- **Host:** Intel i7-10750H (6 cores / 12 threads), 16 GB RAM, Windows 11 Home 26200, AC power, normal desktop load (browser and IDE open).
- **Service:** Mimamsa.Web, Release build, published from `ee17b066`. Console process (not a Windows Service), HTTP on loopback, .NET 10.
- **Database:** PostgreSQL 18.6 private instance, 127.0.0.1:55499, `shared_buffers` 256 MB.
- **Data:** release `R13-b1-sample-20261126-4b31855f`: 290 documents, 11,352 pages, 0.42 GB of originals, 38,445 indexed passages.
- **Clients:** run on the same host.
  - API: Python `urllib`, `scripts/perf.py`.
  - UI: headless Chromium (Playwright), `scripts/walkthrough.cjs`.
  - Client and server compete for the same CPU, so the concurrent figures are conservative.
- **Repeat runs:** one run per measurement (no repeat runs); treat the figures as indicative.

## Results

| Measure | Result | Source |
| --- | --- | --- |
| Start-up to healthy, first start after publish | 10.1 s | `b1-start.ps1` (polls `/health` every 250 ms) |
| Start-up, warm (second start) | 6.5 s | same |
| Start-up, second instance in parallel (audit) | 7.2 s | same |
| Start-up work | Loads the generation, **re-hashes all 290 originals and derivatives**, builds the in-memory index of 38,445 passages | service log |
| First search after start | 36.7 ms | perf.py |
| Search, sequential (100 queries, 20 distinct) | p50 10.1 ms · p95 43.5 ms · max 65.1 ms | perf.py |
| Search, 10 concurrent readers (200) | p50 47.4 ms · p95 172 ms · max 358 ms · 147 req/s | perf.py |
| Search, 25 concurrent readers (500) | p50 125 ms · p95 326 ms · max 432 ms · 165 req/s | perf.py |
| Search as seen in the UI (Enter → results rendered) | 120–310 ms | walkthrough J03, J07, J08 |
| Session check (one PostgreSQL round trip) | p50 1.1 ms · p95 1.5 ms | perf.py |
| Document metadata | p50 1.6 ms · p95 2.2 ms | perf.py |
| Text, 40 pages | p50 1.6 ms · p95 2.0 ms | perf.py |
| pdf-meta | p50 1.4 ms | perf.py |
| Protected 64 KiB range read | p50 7.4 ms · p95 17.0 ms · max 61.6 ms | perf.py |
| PDF: click result → first page canvas | 940 ms (Army Act, 0.7 MB) · 829 ms (SC judgment, 0.9 MB) | walkthrough J03, J04 |
| Go to page 30 | ≤ 1.4 s, including a fixed 0.9 s wait | walkthrough J03 |
| Withdrawal: click → refreshed admin page | 840 ms | walkthrough J13 |
| Searches during the withdrawal (20 sequential) | median 47 ms · max 157 ms | walkthrough J13 |
| Recovery after restart (UI usable again) | 10.6 s from the restart command (includes start-up) | walkthrough J15 (rerun) |
| Sign-in (UI) | 448 ms | walkthrough J01 |

**Database latency** was measured through the API (the session check is a single indexed `SELECT`). Server-side query statistics (`pg_stat_statements`) are not enabled on the private instance and were not added for this audit.

## Memory and CPU (service process)

| Point | Working set | CPU time (cumulative) | Threads |
| --- | --- | --- | --- |
| Idle after start and walkthrough | 729 MB | 27.3 s | 35 |
| After sequential searches | 925 MB | 31.2 s | 38 |
| After 10 concurrent readers | 1,060 MB | 43.6 s | 55 |
| After 25 concurrent readers | 1,335 MB | 77.9 s | 68 |
| End (after PDF and metadata probes) | 1,338 MB | 79.6 s | 68 |

**Observations:**
- The 25-reader phase used about 34 s of CPU in about 3 s of wall time, so the service used most of the 12 logical cores.
- Memory was not returned after load (F14).
- The private PostgreSQL instance's own memory was not sampled.

## Assessment

- **Single user:** everything is fast. Search p95 is under 50 ms, PDF first page in under 1 s, and every metadata or text call is under 3 ms.
- **Ten concurrent readers:** comfortable (p95 172 ms). At 25, p95 is 326 ms, still acceptable for research, with CPU the limit.
- **Risk:** memory scale. A 729 MB baseline for 0.42 GB of originals and 38k passages, growing to 1.3 GB under load, does not demonstrate that the full corpus (~20 GB) fits on this 16 GB machine alongside PostgreSQL and other workloads. This needs a measured full-corpus run before any full import (WP8).
- **Start-up** is dominated by re-hashing every original. That is linear in corpus size: about 6–10 s for 0.42 GB here, so minutes at 20 GB. That's acceptable for a service, but worth stating to operators.

## Not measured

- Cold start after a reboot (OS file cache flushed).
- Behaviour with the service installed as a Windows Service.
- More than 25 concurrent readers, or readers on other machines (LAN).
- PostgreSQL CPU and memory.
- PDF delivery under concurrent viewers.
- Large-PDF time to first page (the largest PDF opened in the walkthrough was 6.4 MB, Navy Pension Regulations, J09; not timed separately).
