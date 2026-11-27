# Independent implementation review: C13 Track B PoC, R2-N01 protected delivery

- **Reviewer:** independent implementation reviewer. I did not author any code under review.
- **Date:** 2026-11-25.
- **Under review:** branch `claude/c13-b-poc` at head `adb5e32e`, worktree `scratchpad/c13/b-poc`. Covers `app/poc/*`, `docs/architecture/poc/POC_RESULTS_C13.md` and `docs/architecture/poc/R2N01_PROTECTED_DELIVERY_POC.md`.
- **Hosted CI:** run 45689265895 (`app-windows-poc.yml`), job 139470052654.
- **Verdict (detail in section 7):** **CHANGES REQUIRED. R2-N01 cannot be closed on this evidence.** The Linux implementation is substantially sound and the independent probes reproduce most claims. However, there are 2 P1 defects, the hosted-Windows evidence is weaker than claimed for 5 of 8 items, and selected-host acceptance is BLOCKED.

## 1. What I did

| Step | Result |
|---|---|
| Built `app/poc/p1_hosting/aspnet` from `git archive adb5e32e` with my own user-space .NET SDK 10.0.404 into a fresh publish directory | Build OK |
| Started my own PostgreSQL 16 cluster (`/var/tmp/c13-review-pg`, 127.0.0.1:56901). All servers bound to 127.0.0.1 on ports 56911–56922 | — |
| Ran the author's ledger oracle (`--ledger-oracle`) | `allPass: true` (7/7) |
| Ran the author's `test_r2n01.py` | **ALL PASS 40/40**. Killed-connection UNCERTAIN count was **0/8** (the author reports 4/8; see F13) |
| Ran the author's `trace_n01.py`, then the staging `transport_oracle.py` against the new trace | ACCEPTED: 104 events, peak 196,608, residual 0, admit→ack 12 ms |
| Re-ran the oracle on the archived Windows and Linux traces | All 3 ACCEPTED. Self-test passes (1 positive, 16 rejected vectors) |
| Wrote and ran my own black-box probes, outside the author's harness, with my own seed, tokens and random-byte fixtures: `reviews/b-poc/probes/probe_r2n01.py` (sha256 `69b0823c…`) and `probe_postack.py` (`5297b497…`) | **61/66 pass.** The 5 failures are analysed below. Results are in `reviews/b-poc/work/probe_work/probe_results.json` and `postack_result.json` |
| Read the CI job steps and full logs through the GitHub MCP | See section 4 |
| Inspected the code for races: `CreditLedger.cs`, `Serving.cs`, `ProtectedDelivery.cs`, `Program.cs`, `DrainProbe.cs`, `Seed.cs` | See section 3 |
| Reviewed P1 benchmark fairness, the P2/P3 labelling and RM-001 exclusion | See sections 5–6 |

**Oracle byte identity.** The staging copies at `origin/legal-knowledge/v2.5-staging` (`dbe40b4f`) are byte-identical to the PoC pins and to PR #54 head `703d98cb`:

| File | sha256 | Status |
|---|---|---|
| `transport_oracle.py` | `fcb4806d07ce…41a0` | identical |
| `transport-fixtures.json` | `b8377355551d…c85d` | identical |
| `transport.md` | `df476056…76bc` | identical to `703d98cb`; not hash-pinned by the PoC |

**CI provenance.** Run 45689265895 built `b8aa304b`, not `adb5e32e`. I checked `git diff b8aa304b adb5e32e`: it touches only docs and archived evidence. No code changed, so the run applies to the reviewed head.

**Oracle interface limits.** The oracle accepts only a normalised trace. My black-box probes produce HTTP and ledger observations, not normalised traces, so I could not feed them to it. What I did feed it: a fresh Linux trace captured with the author's trace driver (accepted), and the archived traces (accepted). In all three accepted traces every `settle` outcome is `accepted` (16/16). None contains a `zero` or `uncertain` settlement. Oracle acceptance therefore says nothing about uncertain-outcome handling (see F05).

## 2. Black-box probe results (Linux, my harness)

| Area | Probes | Result |
|---|---|---|
| Authentication | none, forged, empty, lowercase `bearer`, `Basic`, token-hash-as-token, 5,000-char token, duplicate `Authorization` headers | All 401 with zero bytes |
| Authorisation | other user's session; copy of another document; uppercase sha; unauthorised out-of-bounds request | All 404 with no `Content-Range`, so no length is leaked |
| Ranges, rejected | out of bounds at start and at end (416 `*/len`, authorised caller); overlapping `0-100,50-150`; multi-range; trailing comma; suffix; open-ended; inner whitespace; `+`; 20-digit overflow; negative; `Bytes=`; hex; `max+1`; Unicode digits; empty; duplicate `Range` header | All rejected (400 or 416) with zero bytes |
| Ranges, accepted | exact 128 KiB; leading zeros; last single byte | Exact 206 with matching `Content-Range`/`Content-Length` and exact bytes |
| Methods and protocol | HEAD and POST | 405 with no body |
| | HTTP/1.0 | Exact 206 |
| | `Accept-Encoding` | No compression |
| | date `If-Range` | Still an exact 206 |
| | h2c prior knowledge | GOAWAY: no multiplexing |
| | Pipelined second request | Not served |
| Range after withdrawal | owner, other user, out-of-bounds and malformed range on a withdrawn copy | All a generic 404 with zero bytes. Metadata 404. The unrelated document still returns 206 |
| Restart, then range on withdrawn content | graceful stop, and kill -9, both followed by restart with no seed | Range 404, metadata 404, unrelated document 206. **PASS** |
| Restart with the seed file configured | — | Withdrawn copy is **served again (206)**. See F04 |
| Withdrawal with a non-matching sha (uppercase) or an unknown copy | — | **200 with a new epoch and digest, and the copy is still served.** See F01 |
| Concurrency over the credit cap | site cap = 3 × 134,144; slot gate on; 24 synchronised slow readers of 128 KiB | 3 × 206 and 21 × 503. Maximum site outstanding 402,432 = cap. 0 violations in about 32k samples. No short 206. Ledger at 0 at the end. **PASS** |
| Stall then cancel: RST, 4 KiB send buffer | — | While stalled: ACCEPTED 65,536 + RESERVED 65,536 held, kernel `tx_queue` 8,192. After RST the second attempt became **UNCERTAIN with the full 65,536 charged**. DRAINED only after the socket was gone. 0 refunds. **PASS** |
| Stall then cancel: FIN, 4 KiB send buffer | — | RESERVED row charged in full at drain ("treated as uncertain"). 0 refunds. **PASS** |
| Stall then cancel: RST, default buffers | — | All 3 slices ACCEPTED (134,144 charged). Kernel `tx_queue` 123,174 ≤ charge. Released only after the socket was gone. **PASS** |
| Crash mid-transfer, restart, reconcile | — | Charge survived the restart (134,144). An orphaned kernel socket still held **127,270 bytes (FIN_WAIT1)**. `reconcile-prior?minAgeSec=0` released everything, and 129,365 bytes were then delivered to the client. See F02 |
| Post-ack residual, default buffers, no pause hook | — | Withdrawal ack 200. **129,360 of 131,072 body bytes reached the client after the ack.** A fresh request then gets 404. See F03 |
| Token with a trailing space | — | 206. Informational only: Kestrel trims header optional whitespace per RFC 9110, so this is the same token. Not a finding |

## 3. Code inspection: atomicity and the fence

These parts are correct as built:

- **Reservation is atomic.** `TryReserveAsync` runs one transaction:
  1. lock the `site` row `FOR UPDATE`;
  2. upsert the connection pool and lock both rows;
  3. check the caps;
  4. run the policy recheck (`serving_policy FOR SHARE` plus the in-memory read guard);
  5. update and insert;
  6. commit.

  `CHECK (reserved + charged <= cap)` backstops it. The lock order is fixed (site first), so it cannot deadlock. I found no time-of-check/time-of-use gap.

- **Withdrawal commit versus fence check.** ADMIT sets `Pending=true` and adds the copy to `_withdrawn` under the write lock **before** the durable CAS. Every handoff (`enter`/`accept`) rechecks `!Pending && !withdrawn && Epoch == resEpoch` under the read lock. So once ADMIT returns, no further slice of that copy can enter Kestrel's pipe.
  - A reservation that committed just before the CAS (the CAS's `FOR UPDATE` waits for the `FOR SHARE`) fails its handoff recheck and is settled `zero`.
  - Nothing becomes servable between the durable commit and FENCE.
  - After a restart, the withdrawn set and the epoch are loaded from PostgreSQL before `app.Run()` starts listening.
  - `AuthorizedCopyAsync` also filters `state='eligible'` in the database.

  The fence is sound **for valid input** (but see F01).

- **Settlement.** Settlement is single-shot (`WHERE state='RESERVED'`). A duplicate is a counted no-op. An UNCERTAIN result charges the full amount. `DrainConnectionAsync` charges unsettled RESERVED rows in full before draining. The connection middleware's `finally` runs only after the request handler completes, so drain cannot overlap settle.

Weaknesses (findings below):

- **F01:** the admin CAS does not check how many rows it updated.
- **F02:** reconciliation trusts the caller.
- **F03:** the fence stops new terminal acceptance but does not abort in-flight sockets.
- **F10:** the fence is in-memory and single-process.

## 4. Hosted Windows: what actually ran

All steps were green. Steps 15–18 are R2-N01.

| Step | What it ran | Enforced? | Observed in log |
|---|---|---|---|
| 11 ASP.NET service smoke | **v1 endpoints only** (401, search, metadata, v1 PDF Range `0-7`), restart, `Stop-Process -Force` | throw on failure | PASS. Account `NT SERVICE\MimamsaPocApi`; restart 1.08 s; crash recovery 2.7 s |
| 15 Ledger oracle | Synthetic, no HTTP | throw on `!allPass` | allPass |
| 16 `test_r2n01.py` | **Console `MimamsaPocApi.exe` started by Python, not the Windows Service or virtual account** | last command, so the exit code counts | ALL PASS 40. **UNCERTAIN count 0/8** |
| 17 Trace and PR #54 oracle | Console exe; oracle fetched from `pull/54/head` and hash-checked | throw on oracle rc | ACCEPTED: 100 events, **no occupancy events**, all 16 settles `accepted`, admit→ack **9 ms** |
| 18 PDF.js (Playwright) | Console exe; synthetic 6.1 MB / 300-page fixtures labelled "46MB rules" and "BNSS" | **Not enforced.** `node` and `check_pdfjs_protected.py` are not the last command (`Start-Service` is), and pwsh propagates only the last exit code | Log shows 12/12 PASS. Withdraw case: 2 × 206, 1 aborted, 0 post-fence 206 |

Conclusion: "hosted Windows PASS for every item" is **not supported as stated**:

- Concurrent caps and the basic protected-delivery path are supported.
- The UNCERTAIN path never executed over HTTP on Windows.
- Slow drain is TCP-state only, with no occupancy events.
- Range-after-restart was checked only through metadata.
- No R2-N01 code ran under the Windows Service account.

## 5. P1 benchmark fairness

| Criterion | Assessment |
|---|---|
| Same workload | Mostly. Same SQL, same data, the same fixed-token stub, and comparable pools (Npgsql 32; psycopg 8 × 4 workers). The PDF path is asymmetric: Kestrel `Results.File` (sendfile) against Django `StreamingHttpResponse` with `asyncio.to_thread` reads. |
| Same hardware | Same 4-vCPU VM, but **autocannon runs on the same 4 vCPUs**. That penalises multi-process Django more than Kestrel. |
| Warm-up | 4 s of autocannon per endpoint and concurrency. Adequate. |
| Quietness | The run labelled "quiet" had a 1-minute load of **7.85–10.8** on 4 vCPUs during Kestrel's metadata runs, and 3–11 overall. One run per configuration, with no repeats or variance. |
| Django configuration | `DEBUG=False`, minimal middleware, no ORM. Reasonable. But uvicorn runs **without uvloop or httptools** (not installed), and the uvicorn 4-worker run has an unexplained fixed 45 ms p50 at c=1, which suggests that configuration is broken. No WSGI baseline (waitress on Windows). |
| Scope | The headline 12,689 vs 1,226 req/s is a trivial JSON-row endpoint (Kestrel at c=50 against hypercorn's best at c=10). DB-bound search is 99 vs 71 (about 1.4×). **The protected-delivery path, about 4 DB transactions per 64 KiB slice, was not benchmarked on either stack.** |

My view: the recommendation of ASP.NET Core 10 / Kestrel as a Windows Service is **reasonable on grounds of fit**:
- native SCM hosting, demonstrated;
- a single multi-core process;
- lower RSS;
- R2-N01 built and passing on Kestrel.

The roughly 10× throughput figure should be presented as an indicative microbenchmark, not as evidence of capacity for the protected path (F08).

## 6. P2/P3 labelling and RM-001

- **P2.** The body correctly says "AI-labelled" and notes that the labeller built the systems. The qrels are tagged `ai_manual_blind_snippet`. However, the **Recommendation table** states nDCG 0.72 / 0.62 / 0.61 / 0.33 with no AI-label caveat, and "judged blind to system" overstates blindness given the labeller built the systems (F12).
- **P3.** Base models are explicitly "throughput, latency and memory only; quality not measured". Correct. The recommendation row "best dense quality among the models judged" rests on AI labels with unequal pool depth. The body discloses this; the recommendation row does not (F12).
- **RM-001 is excluded.** I checked the committed docs and data, the P2 manifest (no 4284820e…, doc_id or derived sha), the P1 fixture, the scratch corpora (`corpus.jsonl`, `chunks.jsonl`, `vchunks.jsonl`, `p3chunks.jsonl`, `micro128.jsonl`: 0 doc_id or sha hits) and `bpoc_work/pdfstore` (no 4284820e file). The only occurrences of the phrase "Regulations for the Air Force" are citations inside public SC/HC judgments. `p2_corpus_stats.json` records the exclusion against restricted-list commit `dfce9140`. Its list content is identical to `ea282cbd`; the gov head `72fe7a75` adds only audit metadata for the same single item. All R2-N01 and Windows fixtures are synthetic.

## 7. Findings

### F01 — P1 — A withdrawal is acknowledged although nothing was withdrawn

**Evidence.**
- `Program.cs` `/admin/withdraw` runs `UPDATE vault_copies … WHERE doc_id=$1 AND copy_sha256=$2` without checking the row count. It still bumps the epoch and digest and returns 200.
- The in-memory key uses the caller's string, so an uppercase sha does not match the eligibility check, which uses the lowercase database value.
- Probe results:
  - withdrawing `rv-doc2` with the uppercase sha gave **200 (epoch 5)**, then the range request gave **206**;
  - withdrawing an unknown copy gave **200 (epoch 6)**.
- An operator receives a durable fence acknowledgement for content that keeps being served.

**Required fix.**
- Canonicalise the sha to lowercase and validate it as 64 hex characters.
- Require exactly one `eligible`→`withdrawn` row transition, or an idempotent already-withdrawn result, inside the CAS transaction. Otherwise roll back, do not bump the epoch, clear `Pending` and return 404/409.
- Add a negative test for this.

### F02 — P1 — Post-crash reconciliation releases charge without transport evidence

**Evidence.**
- `ReconcilePriorInstancesAsync` releases every prior-instance row whose heartbeat is older than a **caller-supplied** `minAgeSec`, which may be 0. No OS socket evidence is checked.
- Probe: after kill -9, the orphaned server socket held **127,270 B in FIN_WAIT1**. `minAgeSec=0` returned `drained:3` and set the site to 0, and **129,365 B were then delivered** to the client.
- This contradicts "release only on independently verified drain/termination/reconciliation" (transport.md step 3) and the owner's requirement that charge is kept on restart.
- The author's test passes only because it uses a 4 KiB send buffer and a 3 s grace.

**Required fix.**
- Enforce a server-side minimum grace.
- Before releasing, require OS evidence that no non-LISTEN socket remains on the service port from before the boot: on Linux `/proc/net/tcp`, on Windows `GetTcpTable2`, by port and age or by PID.
- Otherwise keep the charge.
- Add a test with default buffers and a stalled reader.

### F03 — P2 — "No post-fence bytes served" holds only at the terminal-acceptance boundary

**Evidence.**
- With default kernel buffers and no pause hook, a slow reader received **129,360 B after the withdrawal ack**. Kestrel had accepted and flushed the whole 128 KiB into the kernel before ADMIT.
- This is consistent with the oracle's model, but it is not "no post-fence bytes" on the wire.
- The author's between-chunks tests use `ListenSendBufferBytes=4096` plus `PauseAfterFirstSliceMs`, and PDF.js counts post-fence **206 responses**, not bytes.

**Required fix.**
- State the residual bound explicitly: up to `MaxRange` plus header per active stream.
- Either abort affected in-flight connections on FENCE (RST via linger 0) or cap `SO_SNDBUF` in production.
- Add a default-configuration test measuring post-ack wire bytes.

### F04 — P2 — A test seeding path in the shipped binary reverts withdrawals

**Evidence.**
- `Seed.ApplyAsync` runs `TRUNCATE poc_sessions, poc_grants, vault_copies` whenever `Mimamsa:SeedFile` is set.
- Probe: restarting with the seed configured made the withdrawn copy return **206**.
- The epoch survives but the withdrawn state does not.

**Required fix.**
- Compile out or refuse seeding outside an explicit test mode, and refuse when `vault_copies` contains withdrawn rows.
- Never make copy state depend on startup configuration.

### F05 — P2 — Uncertain-outcome evidence is thin on Windows, and absent from every oracle trace

**Evidence.**
- Windows `C_killed_connections.uncertain_count = 0`.
- All archived and reproduced traces have 16/16 `accepted` settles.
- The UNCERTAIN HTTP path is covered on Windows only by the synthetic ledger oracle.
- On Linux I observed UNCERTAIN in my own probe, but the author's suite gave 0/8 in my rerun.

**Required fix.** Make the UNCERTAIN path deterministic: for example, a fault hook that cancels `FlushAsync` after a partial write. Assert it on both OSes, and include `uncertain` and `zero` settlements in the oracle trace.

### F06 — P2 — No R2-N01 test ran under the Windows Service or virtual account

**Evidence.** Steps 16–18 start the console exe from Python or `Start-Process`, and step 18 stops the service first. The service ran v1 smoke only.

**Required fix.** Run the transport tests, trace and PDF.js against the installed service (`NT SERVICE\…`, ACL-scoped vault), or relabel the Windows column as "console process on hosted Windows".

### F07 — P2 — Server-side trace events are self-instrumented

**Evidence.**
- `DeliveryTrace.cs` (author-disclosed). transport.md: "A within-cap sample with no independently observed terminal or witness evidence cannot close the gate."
- The Linux occupancy events come from the author's client reading `/proc`. On Windows there are none.

**Required fix.** On the selected host, add an independent terminal or socket probe (ETW or EStats) and an independent storage probe for the witness CAS before claiming oracle-based closure.

### F08 — P2 — P1 benchmark fairness

**Evidence.** See section 5: co-located load generator, load 8–11 in the run labelled "quiet", a single run, uvicorn without uvloop or httptools, an unexplained anomaly, an asymmetric PDF path, and no benchmark of the protected path.

**Required fix.**
- Re-run with the load generator on separate cores (taskset) or a separate host.
- Do at least 3 repeats and report medians and spread.
- Use `uvicorn[standard]` and a waitress baseline.
- Benchmark `/api/v2/.../range` under the credit ledger.
- Label the 10× figure as indicative.

### F09 — P3 — The Windows PDF.js step does not fail on check failure

**Evidence.** pwsh propagates only the last exit code, which here is `Start-Service`.

**Required fix.** Add `if ($LASTEXITCODE) { throw }` after `node` and after the checker.

### F10 — P3 — The in-memory fence is single-process

**Evidence.**
- A second or overlapping instance (for example an IIS overlapped recycle) never reloads the epoch.
- On `dbEpoch != state.Epoch` it loops 2 s and aborts **every** request forever. This fails closed, but is an availability trap.
- `Pending` is global, so every copy stalls during any withdrawal. The fence measured 9–16 ms.

**Required fix.** Document single-instance as a hard deployment constraint (enforce it with an advisory lock at boot), or reload policy on epoch mismatch.

### F11 — P3 — Resource bounds before admission and per user

**Evidence.**
- `ReadSliceAsync` stages up to 128 KiB **before** `slots.TryAcquire`, so memory is unbounded across concurrent authenticated requests.
- There is no per-user or per-session cap, so one user can hold all N slots. Zero-window orphan sockets can hold a slot for minutes.
- In the author's B2 run on my host, 392/400 requests got 503 with N = 7.

**Required fix.** Acquire the slot before staging. Add per-session concurrency caps. Set `MaxConcurrentConnections`.

### F12 — P3 — Labelling in the recommendation table

**Evidence.**
- The P2 and P3 recommendation rows give nDCG and "best dense quality" without the AI-label, same-labeller and unequal-pool caveats.
- "Judged blind to system" overstates blindness, given the labeller built the systems and queries.

**Required fix.** Add "AI-labelled, not human-verified" to those rows and soften "blind".

### F13 — P3 — Documentation accuracy

**Evidence.**
- The claim of 4/8 UNCERTAIN in the killed-connection tests was not reproduced: I got 0/8, so the result is nondeterministic.
- The Windows admit→ack in the cited run is 9 ms; the doc says 10 ms from an earlier run.
- The Windows PDF.js labels "46MB rules" and "BNSS" refer to 6.1 MB synthetic files. The author discloses this, but the archived JSON still carries the misleading labels.

**Required fix.** Correct or qualify these statements.

### F14 — P3 — The "useful ordinary research" positive control is narrow

**Evidence.**
- The positive control is one unrelated PDF range after withdrawal and restart.
- No search or metadata traffic ran concurrently with protected delivery or withdrawal.
- The 25-browser / 10-query target mix was not run (author-disclosed).

**Required fix.** Add a concurrent search and metadata control during the cap race and during withdrawal on the selected host.

**Counts: P1 = 2, P2 = 6, P3 = 6.**

## 8. R2-N01 per-item status

| R2-N01 item | Linux (independent) | Hosted Windows | Selected host |
|---|---|---|---|
| Protected delivery (authentication, authorisation, vault, exact 206) | **PASS** (my probes, 61/66; the failures are F01, F02, F04 and one benign optional-whitespace case) | **PASS** (40/40, console process) | BLOCKED |
| Atomic reservation before the terminal call; uncertain keeps the full charge, no refund on timeout, cancel, restart or duplicate | **PARTIAL** (atomicity, cancel and duplicate pass; restart refund via F02) | **PARTIAL** (ledger oracle only; 0 HTTP uncertain, F05; F02 applies) | BLOCKED |
| Durable withdrawal surviving restart, with a durable fence | **PARTIAL** (valid withdrawal survives graceful stop and kill -9; F01 false ack; F04) | **PARTIAL** (after restart only metadata 404 was checked; F01 and F04 apply) | BLOCKED |
| Authenticated, bounded large-PDF viewing: exact 206 from the first fetch, near-end jump, withdrawal between chunks, no post-fence bytes | **PARTIAL** (exact and bounded ranges and the near-end range pass; post-ack wire residual F03; I did not re-run PDF.js myself) | **PARTIAL** (12/12 in the log but not exit-enforced, F09; 6.1 MB synthetic; F03 applies) | BLOCKED |
| Concurrent caps | **PASS** (24 contenders, maximum = cap, 0 violations) | **PASS** | BLOCKED |
| Slow drain | **PASS** (charge ≥ kernel `tx_queue`; release only after the socket is gone) | **PARTIAL** (TCP state only; no occupancy events) | BLOCKED |
| Crash and cancel | **PARTIAL** (cancel RST and FIN pass; crash reconcile F02) | **PARTIAL** (same code; test masks F02) | BLOCKED |
| Useful ordinary research as positive control | **PARTIAL** (unrelated PDF passes; no concurrent search, F14) | **PARTIAL** (service smoke search only) | BLOCKED |

## 9. Verdict

**CHANGES REQUIRED. Do not close R2-N01.**

The core design reproduces under independent probing:
- atomic two-pool reservation with a database backstop;
- a writer-priority fence admitted before the durable CAS;
- strict single-range parsing;
- uniform 404 denial;
- full-charge retention on cancel.

To close R2-N01:
- Fix F01 and F02, with regression tests.
- Address F03 and F04.
- Make the UNCERTAIN path deterministic on both OSes (F05).
- Run R2-N01 under the installed Windows Service (F06).

Selected-host acceptance remains BLOCKED pending owner hardware, TLS and independent probes (F07).

The P1 host recommendation (ASP.NET Core 10 / Kestrel as a Windows Service) is acceptable as a direction on fit grounds. Its throughput figures are indicative only (F08).

## Artefacts (reviewer, scratch, not committed)

| Artefact | Path |
|---|---|
| Probes | `scratchpad/c13/reviews/b-poc/probes/probe_r2n01.py`, `probe_postack.py` |
| Probe results | `scratchpad/c13/reviews/b-poc/work/probe_work/probe_results.json`, `postack_result.json` |
| Author suite rerun | `work/author_tests_linux.json` |
| Ledger oracle rerun | `work/ledger_oracle_review.json` |
| Fresh trace | `work/trace_linux_review/` |
| Staging oracle copies | `work/oracle_staging/` |
| CI log extract | `work/ci_log.txt` |

---

## 10. Confirmation review of the fixes (head `edcea6c7`, CI run 45699091315)

- **Date:** 2026-11-25.
- **Scope:** `git log adb5e32e..edcea6c7`, which contains `ae44bff4`, `52aa5219` and `edcea6c7`. `git diff 52aa5219 edcea6c7 -- app .github` is empty, so CI run 45699091315, which built `52aa5219`, covers the reviewed code.
- **Branch:** not modified.

### 10.1 What I re-ran (Linux, my own build of `edcea6c7`, loopback only)

| Run | Result |
|---|---|
| My original 66 probes (`probes/probe_r2n01_v2.py`). The checks are unchanged. The only change is setting `Test:Enabled=true`, which seeding now requires | **65/66.** The F01, F04 and F02 reproductions now pass. The single failure is the benign trailing-whitespace token case (RFC 9110 optional-whitespace trimming), as before |
| New production-mode attacks (`probes/probe_v2_extra.py`): no test flag; `Reconcile:MinAgeSec=1` and `Test:ReconcileMinAgeSec=0` set as an attempted bypass | **6/6** (detail in 10.2) |
| Author's `test_r2n01.py` | ALL PASS 48. F05: 5 UNCERTAIN rows over HTTP |
| Author's `trace_n01.py`, then the staging oracle | ACCEPTED: 116 events, peak 196,608, residual 0, ack 23 ms. **Settle outcomes in my run: `accepted` 17, `zero` 1, `uncertain` 0.** The author's trace contained 1 uncertain, so its presence in the trace is nondeterministic (N5) |

### 10.2 Attacks on the new F02 rule (production mode)

| Attack | Observation | Result |
|---|---|---|
| kill -9 with a stalled reader; the orphaned socket holds 47,105 B (FIN_WAIT1); reconcile called every 0.5 s from the moment of restart | Every call returned `drained:0` with `min_age_s:30`. The configured overrides were ignored: clamped to 30 in production. The charge of 131,072 was held until the client drained and the socket reached `tx=0` (FIN_WAIT2). Release came at +29.2 s after the kill, roughly 30 s after the last heartbeat. **No release while bytes were in flight** | Holds |
| Client RST immediately after the kill, so the socket is gone at once | Release still came only at +29.2 s | Server-side 30 s minimum holds |
| `SeedFile` set without test mode | Process refuses to start (exit −6) | F04 enforced |

Robustness of the "OS evidence":

- **Linux path:** sound. `tx_queue` is summed over every matching socket, and "gone" is a valid proof because a reset discards queued bytes.
- **Non-Linux TCP-state path:** matches on port pair only and returns the **first** match. On a multi-client host, another connection with the same ports from a different IP could mask the orphan (N2).
- **Rows without recorded ports** (written before the upgrade) are never released (N3).
- **Test mode** is a configuration flag and bypasses the 30 s clamp. The Windows service CI ran in test mode (N4).

### 10.3 F03 bound under slow readers (production defaults: SO_SNDBUF 32 KiB requested, effective about 46–64 KiB)

| Case | Server egress after the ack (client-queued bytes excluded) | Result |
|---|---|---|
| Active 128 KiB stream, 4 KiB receive window | **0 B** (`reset_streams:1`) | Holds |
| Finished 60 KiB response, stalled reader | **57,631 B** (≤ 65,536) | Holds |
| 8 finished 60 KiB responses, 2 sessions | ≤ 57,631 B per stream, **461,089 B in total** | Per-stream bound holds; aggregate scales with stream count (N1) |

### 10.4 Hosted Windows, run 45699091315

All 22 steps are green. Every R2-N01 step now throws on a non-zero exit, including PDF.js, so **F09 is closed**.

| Step | Result |
|---|---|
| Console transport tests | **48/48**: F05 with 7 UNCERTAIN rows; F01, F02 and F03 checks pass |
| Trace | ACCEPTED: 122 events, settles `accepted` 19 + `zero` 1, **no uncertain** |
| Service-mode step 19 | **16/16** against the installed `MimamsaPocApi` (same SCM install as step 11, account `NT SERVICE\MimamsaPocApi`, ACL-scoped vault) |

Step 19 details:

- **Covered:** SCM crash restart (PID 1404 → 7700 in 2.67 s); `svc_F05` (1 uncertain, 0 released); F02 charge survives the crash (134,144); F04; F01; a search positive control.
- **Configuration:** test mode with `ListenSendBufferBytes=4096` and `ReconcileMinAgeSec=3`, **not production defaults** (N4).
- **F02 on Windows:** TerminateProcess left no bytes to deliver (`bytes_after_crash:0`), so the release came from "socket gone". **The orphan-holds-bytes case therefore cannot occur, and was not exercised, on Windows.**

### 10.5 Dispositions

| ID | Status | Note |
|---|---|---|
| F01 | **CLOSED** | Canonical sha; 400/404 typed; idempotent; the epoch moves only on a 1-row transition. Re-probed |
| F02 | **CLOSED** for hosted scope | Evidence-gated, with the server clamp at 30 s. Residual hardening in N2–N4 |
| F03 | **CLOSED**, with a stated per-stream bound | N1 for the aggregate |
| F04 | **CLOSED** | — |
| F05 | **CLOSED** at the HTTP level on both OSes | Oracle-trace uncertain is nondeterministic (N5) |
| F06 | **CLOSED** | Service-mode run confirmed in the log |
| F07 | **OPEN** | Selected host |
| F08 | **CLOSED** (indicative) | Not re-run by me |
| F09 | **CLOSED** | — |
| F10 | **CLOSED** | Advisory instance lock in code |
| F11 | **CLOSED** | Slot and per-session cap taken before the vault read |
| F12 | **CLOSED** | — |
| F13 | **CLOSED** | — |
| F14 | **PARTIAL** | Service search control only |

### 10.6 New findings (all P3; no new P1 or P2)

| ID | Finding | Required fix |
|---|---|---|
| N1 | Responses that finished but have not drained are not reset at FENCE. Aggregate post-ack egress is about streams × SO_SNDBUF (461 KB for 8 streams). | Also RST the pending-drain connections that served the copy, or state the aggregate bound |
| N2 | The TCP-state `SocketSafe` path matches on port only, first match wins. | Record and match the full 4-tuple |
| N3 | Charges without port information are retained forever. | Document an operator reconciliation procedure |
| N4 | The Windows service evidence uses test mode. The production clamp, 32 KiB send buffer and seed refusal were verified only by me, on Linux. | Add one production-configuration service run |
| N5 | Uncertain settlements in the oracle trace are nondeterministic. | Make deterministic, or qualify in the docs |

### 10.7 Updated R2-N01 table

| Item | Linux (independent) | Hosted Windows | Selected host |
|---|---|---|---|
| Protected delivery | PASS | PASS (service + console) | BLOCKED |
| Reservation / uncertain / no refund | PASS | PASS | BLOCKED |
| Durable withdrawal + fence | PASS | PASS | BLOCKED |
| Large-PDF viewing | PASS (per-stream bound; N1) | PASS (synthetic 6.1 MB) | BLOCKED |
| Concurrent caps | PASS | PASS | BLOCKED |
| Slow drain | PASS | PARTIAL (TCP state only, no occupancy) | BLOCKED |
| Crash and cancel | PASS | PASS (orphan-bytes case not applicable) | BLOCKED |
| Ordinary-research control | PARTIAL (F14) | PARTIAL (F14) | BLOCKED |

### 10.8 Updated verdict

**R2-N01 may be closed for the hosted-Windows PoC scope, with two recorded exceptions:**
- slow drain on Windows is shown by TCP state only, with no byte-level occupancy;
- F14 is partial.

**Selected-host acceptance stays BLOCKED** on F07 (independent probes), TLS, the 25-browser / 10-query mix and owner hardware. The P1 and P2 findings are resolved. The P3 items N1–N5 should be carried into the selected-host plan.
