# Response to the independent review of adb5e32e (REVIEW_R2N01_POC.md)

The review found 2 P1, 6 P2 and 6 P3 issues. This file gives the disposition of each, with evidence: what was fixed, what was relabelled, and what is still open. Linux evidence is in `data/r2n01/`; the hosted-Windows CI run id is recorded below. The selected host remains **BLOCKED (owner hardware pending)**.

| ID | Sev | Disposition | Change | Evidence |
|---|---|---|---|---|
| F01 | P1 | **FIXED** | The sha is canonicalised (lowercase, 64 hex). An invalid sha gets 400 `invalid_copy_identity`. An unknown copy gets 404 `unknown_copy` and the epoch does not change. A repeat withdrawal returns 200 `already_withdrawn` and the epoch does not change. Inside the CAS, the epoch is bumped only when exactly one row moves from `eligible` to `withdrawn`; otherwise the transaction rolls back and `Pending` is cleared. | `test_r2n01.py`: `F01_withdraw_unknown_copy_404_typed_no_epoch_bump`, `F01_withdraw_unknown_doc_404_no_epoch_bump`, `F01_withdraw_invalid_sha_400`, `withdraw_admin_ok` (an uppercase sha withdraws the right copy, and range then returns 404), `F01_repeat_withdraw_idempotent_no_epoch_bump`. `test_service_r2n01.py`: `svc_F01_unknown_copy_404_no_epoch_bump`. |
| F02 | P1 | **FIXED** | `minAgeSec` is gone. Releasing a previous instance's charge now needs two things: (a) a server-side minimum heartbeat age of at least 30 s in production (configurable only in test mode), and (b) positive OS socket evidence for the exact port pair recorded on each reservation. On Linux that is `/proc/net/tcp` `tx_queue = 0` or the socket gone; elsewhere it is the TCP state FIN_WAIT_2, TIME_WAIT or CLOSED, or the socket gone. A pool without port information keeps its charge. An evidence-gated loop reconciles every second. | Linux D scenario, default buffers, stalled reader, kill -9: after restart and the minimum age, `reconcile` returned `drained:0` while the orphaned socket still held bytes, and the charge stayed at 134,144. The client then read 131,367 B. After that the charge went to 0, with reason `prior instance reconciled: linux /proc/net/tcp …`. Checks: `F02_no_release_while_orphan_socket_may_deliver`, `F02_release_only_after_os_socket_evidence`. Service mode: `svc_F02_*`. |
| F03 | P2 | **FIXED, with a stated bound** | (1) At FENCE, every active stream of the withdrawn copy is reset (SO_LINGER 0 + abort, so kernel-queued bytes are discarded) **before** the withdrawal is acknowledged. The count is reported as `reset_streams`. (2) The default listen SO_SNDBUF is 32 KiB requested, which is 64 KiB effective on Linux. **Bound:** after the ack, egress for a withdrawn copy is 0 from active streams. A response the server had already finished can still have at most the effective SO_SNDBUF queued in the server kernel. Bytes already in the client's receive queue were delivered before the ack. | Linux E scenario, default client buffers, no pause hook: the client queue at ack was 127,783 B; **2,560 B** left the server after the ack (bound 65,536). Trace W stream, paused between slices: 3,808 B received in total (previously 64,512–129,024). |
| F04 | P2 | **FIXED** | `SeedFile` is refused unless `Mimamsa:Test:Enabled=true`. Seeding upserts with `ON CONFLICT DO NOTHING` and never changes copy state. Only an explicit test-mode reset truncates. | `F04_seed_on_restart_does_not_revert_withdrawal` and `svc_F04_withdrawal_survives_restart_with_seed` (under the Windows Service in CI). |
| F05 | P2 | **FIXED** | Test-only header hooks (`X-Mimamsa-Test-Pause: after-first-slice / before-enter`, honoured only in test mode). Killed-connection trials no longer pause, so a blocked flush followed by a client RST produces a real UNCERTAIN. | Linux: 7 UNCERTAIN rows over HTTP (`F05_real_uncertain_transfer_over_http`). The oracle traces now contain `accepted:16, uncertain:1, zero:1` and are **ACCEPTED** by the unmodified PR #54 oracle for both drain probes. Windows: `svc_F05_uncertain_transfer_recorded` under the service, plus the same transport tests. |
| F06 | P2 | **FIXED** | New CI step: the installed `MimamsaPocApi` service under `NT SERVICE\MimamsaPocApi`, in test mode with an ACL-scoped vault, runs `test_service_r2n01.py`. That covers exact 206 and near-end ranges, negatives, a concurrent search control, F01, F05, withdrawal, **SCM crash restart** (TerminateProcess, then a new PID from the SCM failure action), charge survival, F04 and evidence-gated release. The console-process steps remain and are labelled as console. | CI run in the table below |
| F07 | P2 | **OPEN** (selected host) | Server events are still the application's own instrumentation, cross-checked against the ledger rows. Independent terminal and witness probes (ETW/EStats, a storage probe) are needed on the selected host before oracle-based closure. | — |
| F08 | P2 | **ADDRESSED; indicative only** | Re-run with taskset: servers on CPUs 0–2, autocannon on CPU 3. 3 runs, 3 s warm-up, 10 s runs. uvicorn uses uvloop + httptools. The waitress (WSGI) attempt failed because the async views and async pool are not WSGI-compatible without rework (recorded as such). The protected path was measured with a connection-per-request client, because autocannon mis-measures `Connection: close`. | `data/p1_linux_bench_v3_pinned.json`, `data/p1_protected_path_linux.json` |
| F09 | P3 | **FIXED** | Exit codes of `node` and the checker are captured and thrown. The transport-test and service-test exits are enforced. | workflow |
| F10 | P3 | **FIXED (constraint enforced)** | A session advisory lock `mimamsa-serving-instance` is held for the life of the process. A second instance on the same database refuses to start. Single-instance is documented as a hard deployment constraint. `Pending` remains global, which is acceptable at a measured 9–16 ms per fence. | `Program.cs` |
| F11 | P3 | **FIXED** | The slot and a per-session cap (default 4) are taken before any vault read. `MaxConcurrentConnections` defaults to 1000. | `ProtectedDelivery.cs` |
| F12 | P3 | **FIXED (docs)** | The recommendation rows now carry "AI-labelled, not human-verified; same labeller built the systems; unequal pool depth". "Blind" is changed to "blind to system identity at labelling time". | `POC_RESULTS_C13.md` |
| F13 | P3 | **FIXED (docs)** | "4/8 uncertain" was nondeterministic; it is replaced by the deterministic F05 result. The Windows admit→ack is quoted from the cited run. The Windows PDF.js labels are qualified as synthetic files. | docs |
| F14 | P3 | **PARTIAL** | The service mode runs a v1 search control on the same instance. A concurrent search/metadata mix during the cap race and the withdrawal, at 25 browsers / 10 queries, is still owed on the selected host. | — |

## P1 benchmark (F08). Indicative only: one VM, synthetic data

Medians of 3 runs. The load generator was pinned to its own core. Run with `taskset -c 0-2` for the servers and
`-c 3` for autocannon.

| Endpoint, concurrency | ASP.NET Core 10 | Django uvicorn ×4 (uvloop) | Django hypercorn ×4 | Django uvicorn ×1 |
|---|---|---|---|---|
| metadata, c=16 (rps) | 14,329 | 1,286 | 1,383 | 919 |
| search, c=16 (rps, DB-bound) | 117 | 77 | 77 | 81 |
| PDF 87 KB, c=16 (rps) | 1,114 | 785 | 601 | 520 |
| idle RSS | 93 MB | 254 MB | 245 MB | 55 MB |

The uvicorn 4-worker 45 ms anomaly disappeared with uvloop/httptools: metadata at c=1 went from 22 to 656 rps.

Protected path (ASP.NET only; Django has no R2-N01 implementation), 64 KiB ranges, connection per request, ledger
active, 3 runs:

| Concurrency | 206 responses/s | p50 | p95 |
|---|---|---|---|
| 1 | 102–138 (6–8.5 MiB/s) | 3.5–6 ms | 15–32 ms |
| 16 | 83–106 (5–6.5 MiB/s) | 58–95 ms | 408–468 ms |

At c=16, 99–247 responses were retried after 503. This is credit and slot backpressure: about 4 PostgreSQL
transactions per slice plus drain-gated slots. It is the main throughput cost of R2-N01 and needs a selected-host
measurement against the 25-browser target.

## Hosted Windows CI

Run **(see final report)** on `windows-latest`. Steps: services install, smoke, restart and crash; ledger oracle;
console transport tests; console trace with the PR #54 oracle; console PDF.js; **service-mode R2-N01 checks**.
