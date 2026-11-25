# R2-N01 protected delivery PoC (ASP.NET Core) — C13 B-PoC

Scope: PR #53 Serving §6 and §10, review condition R2-N01. The implementation lives in `app/poc/p1_hosting/`. The
platform-neutral rules are in `core/` (class library, no ASP.NET or OS dependency). The OS and host adapters are
in `aspnet/`.

**Status labels.** "Linux" means measured on the shared Linux VM described in ENVIRONMENT_C13.md. "Hosted
Windows" means GitHub `windows-latest` (Windows Server 2025 runner) running `.github/workflows/app-windows-poc.yml`.
**Selected-host acceptance is BLOCKED: the owner's hardware is pending.** A hosted runner is not the production
host, and no Windows measurement here should be carried over to the selected host.

## Design

| Concern | Implementation | File |
|---|---|---|
| Atomic credit | Every attempt (at most 64 KiB charged: payload ≤ 63 KiB + 1 KiB header allowance) is reserved on both the connection pool and the site pool in one PostgreSQL transaction. The `site` row is locked first, so every reservation passes through one serialisation point and the lock order makes the protocol deadlock-free. `CHECK (reserved + charged <= cap)` makes overcommit impossible even if the application logic is wrong. | `core/CreditLedger.cs` |
| Policy authority at reservation | Inside the same transaction: `serving_policy` is read FOR SHARE, then the in-memory epoch, the pending flag and copy eligibility are rechecked under the read guard. No reservation can commit under a stale epoch, or between withdrawal admission and the durable fence. | `aspnet/ProtectedDelivery.cs` |
| Handoff | Under the read guard: a fresh recheck (`enter`), then the exact staged slice is copied into Kestrel's `PipeWriter` and `Advance()` is called (`accept`). `FlushAsync`, which can block on a slow client, runs outside the guard. `MaxResponseBufferSize` is 64 KiB. | same |
| Settlement | ACCEPTED(k) after a successful flush. RELEASED only when zero transfer is established (the recheck failed before any byte). UNCERTAIN on a lost completion (flush cancelled or reset), which keeps the full reservation. A duplicate settlement is a counted no-op. A stream is never retried. | `core/CreditLedger.cs` |
| Drain or release | Release happens only on transport evidence. Linux: `/proc/net/tcp` `tx_queue = 0` (two samples) or the socket gone. Windows and other OSes: the OS TCP table state of the exact socket is FIN_WAIT_2, TIME_WAIT or CLOSED, or the socket is gone. The server is the active closer, so this means every byte including FIN was ACKed. Nothing is released on timeout. After a crash, release needs an explicit reconciliation call with evidence, and only once the old instance's heartbeat is stale. | `aspnet/DrainProbe.cs`, `aspnet/Program.cs` |
| Durable withdrawal | (1) Write lock: pending, route closed, ADMIT. (2) Durable CAS: `serving_policy.epoch + 1`, a new digest and `vault_copies.state = 'withdrawn'` in one transaction, then read back on a fresh connection. (3) Write lock: the new epoch and FENCE. If (2) fails, the route stays closed. After a restart the epoch, digest and withdrawn set are reloaded from PostgreSQL. | `core/Serving.cs`, `aspnet/Program.cs` |
| Bounded range | Only a single explicit `bytes=a-b` is accepted, with a maximum of 128 KiB. Missing, multi, open-ended, suffix or malformed ranges get 400. Out-of-bounds ranges get 416 with `*/len` (the caller is authorised). The response is an exact 206 Content-Range/Content-Length with `no-store`, no ETag or Last-Modified, no compression and `Connection: close`. There is never a full-body fallback. | `core/Serving.cs` |
| Authentication | Every request checks a hashed bearer token in PostgreSQL, then the user→document grant, then the eligible copy pinned by sha256 in the URL. A missing grant, an unknown copy and a withdrawn copy all get the same 404. | `core/Serving.cs` |
| Vault | Content-addressed `<root>/<aa>/<sha256>.pdf`. Content is verified against the address on import. There is no static route. | `core/Serving.cs` |
| Liveness | At most N concurrent protected responses run, where N × the maximum response size ≤ the site cap. A slot is returned only after drain, so per-slice reservation cannot deadlock started responses. | `aspnet/ProtectedDelivery.cs` |
| Trace | In-process instrumentation emits `reserve/enter/accept/settle/admit/fence/prove_release/boot` in the PR #54 normalised format. The client emits `http/cancel/ack/restart`. Linux occupancy comes from `/proc/net/tcp` read by the client process. | `aspnet/DeliveryTrace.cs`, `r2n01/trace_n01.py` |
| PDF.js | A metadata bootstrap, then `PDFDataRangeTransport`. No URL is ever given to PDF.js, so no unbounded GET is possible. Each range is ≤ 128 KiB, authenticated and pinned to the copy sha. 503 is retried. 401 or 404 destroys the document (viewer invalidation). | `app/poc/p4_pdf/pdfjs/src/protected.js` |

## Results per owner item

| Item | Linux (measured) | Hosted Windows (measured, CI) | Selected host |
|---|---|---|---|
| Protected delivery with an ordinary positive control | PASS. 40/40 transport checks. An unrelated eligible document still gets 206 after the withdrawal and after the restart. | PASS. 40/40 (final run 45689265895). Both Windows Services (virtual accounts) passed restart (1.1 s) and crash recovery (2.7 s). | BLOCKED (owner hardware pending) |
| Reservation before the terminal call; uncertain keeps the full charge; no refund on timeout, cancel, restart or duplicate | PASS. Serving §10 ledger oracle 7/7 (`data/r2n01/ledger_oracle_linux.json`). Killed connections: 8/8 kept the charge until transport evidence, 0 RELEASED. A duplicate settlement is a no-op. | PASS. Ledger oracle allPass. Transport killed-connection checks pass. | BLOCKED |
| Durable withdrawal survives a restart with a durable fence | PASS. Epoch/digest CAS. `withdrawn_meta_after_restart = 404`. Oracle: fence before ack, recover with the exact epoch and digest. | PASS. Oracle accepted the Windows trace. | BLOCKED |
| Authenticated large-PDF viewing: exact bounded 206 from the first fetch, near-end jump, withdrawal between chunks | PASS. 46.8 MB PDF: page 1 then page 47/47 using 4.2 % of the file, all requests ≤ 128 KiB, authenticated, 206. BNSS 282 pages: page 1 then page 280. Withdrawal between chunks: 0 post-fence 206 and the viewer is invalidated. Forged-token and other-user viewers make no range request. | PASS (run 45689265895, Chromium via Playwright). Synthetic 6.1 MB / 300-page fixtures (case labels reuse the Linux names): page 1 then page 47 using 2.7 % of the file, page 280 using 3.7 %, all requests 206 and ≤ 64.5 KiB. Withdrawal between chunks: 0 post-fence 206 and the viewer is invalidated. Forged-token and other-user viewers make no range request. | BLOCKED |
| Concurrent caps | PASS. 200/200 ledger races at the site cap and 100/100 at the connection cap. HTTP: 40 contenders for one 64 KiB of site credit → exactly 1 × 206. 400 requests at a 1 MiB cap: maximum outstanding 1,048,454 ≤ 1,048,576, 0 violations in about 76k samples. | PASS (same tests) | BLOCKED |
| Slow drain | PASS. The slow reader held its charge. Kernel occupancy (6,144 B) ≤ charge. Released only after `tx_queue = 0`. | PASS via the TCP-state probe (no byte-level occupancy on Windows) | BLOCKED |
| Crash and cancel | PASS. kill -9 mid-transfer: the charge survives the restart, no release before the grace, an explicit reconciliation releases it with evidence. A client RST gives no further attempt on the stream. | PASS | BLOCKED |

### Independent oracle (PR #54, unmodified)

`transport_oracle.py` (sha256 `fcb4806d…`) and `transport-fixtures.json` (sha256 `b8377355…`) were taken unmodified
from PR #54 head `703d98cb`. The self-test passes (1 positive vector, 16 rejected vectors). HTTP expectations were
pinned in `r2n01/n01_http_cases.json`, committed (c86f66ed) before any trace was captured.

| Trace | Result | Events | Peak / remaining wire charge | Withdrawal admit→ack |
|---|---|---|---|---|
| Linux, /proc tx_queue probe | ACCEPTED | 104 | 196,608 (= site cap) / 0 | 16 ms |
| Linux, TCP-state probe (the Windows code path) | ACCEPTED | 104 | 196,608 / 0 | measured in file |
| Hosted Windows (CI run 45689265895, Windows Server 2025 build 26100, 2 vCPU) | ACCEPTED | see `data/r2n01/windows_ci_run_45689265895/` | 196,608 / 0 | 10 ms (earlier run 45649488168) |

Earlier traces that the oracle rejected are recorded honestly in the commit history. They exposed three real
defects, all fixed:
1. A reservation was emitted on a stream the client had already cancelled. Fix: check `RequestAborted` before each attempt.
2. Credit was released on app-level connection end while bytes were still queued in the kernel. Fix: kernel/TCP evidence drain probes.
3. The oracle requires site ≥ connection limits; the configuration was corrected.

**Limits of this evidence (not hidden).**
- Server-side events come from the application's own instrumentation, not from independent probes. The exporter cross-checks reserve and settle against the PostgreSQL ledger rows: 0 mismatches.
- The terminal boundary is Kestrel's PipeWriter. Bytes in that pipe (≤ 64 KiB) are charged but not separately observed.
- Kernel occupancy is byte-level only on Linux. Windows uses TCP state.
- No TLS: T0 requires TLS, so TLS-buffer accounting is untested.
- No browser cancellation probe beyond the viewer's own transport.
- The uncertain outcome appears in the transport tests (4 of 8 killed connections) and the ledger oracle, but not in the final oracle traces, because with the pause hook the client reset is detected before the next attempt.
- One response per connection (`Connection: close`), so the connection-cap race over HTTP cannot happen on one connection. It is covered by the ledger oracle.

## Reuse of the Codex reference PoC (`codex/c13-n01-poc` @ fbeda374)

| Component | Reused? | Reason |
|---|---|---|
| `harness.py::make_pdf` (396,871-byte synthetic PDF) | **Reused verbatim** in `r2n01/codex_fixture.py`, digest-verified | The PR #54 oracle fixtures and the reference evidence describe exactly these bytes. |
| Slice/range bounds (64 KiB slice, 128 KiB range), uniform denial for withdrawn copies, pause hook between slices | **Reused as conventions** | Matching them keeps the traces comparable with the reference and the oracle. |
| `delivery.py`, `harness.py` server | Not reused | Python stdlib reference. The host decision is ASP.NET Core / Kestrel, so the adapter has to be measured on that stack. The reference README says terminal transport, drain proof and recovery belong in the host adapter. |
| `test_n01.py`, `benchmark.py` | Not reused | Coupled to the Python reference API. Equivalent coverage is in `r2n01/test_r2n01.py` (HTTP black box + ledger reads) and the C# ledger oracle. |
| `viewer.html`, `browser_check.mjs` (PDF.js 5.4.624) | Not reused | `pdfjs/src/protected.js` and `run_protected.cjs` already existed on PDF.js 6.5.438 with a custom range transport and network capture. |
| `app-ci.yml` | Not reused | `app-windows-poc.yml` adds Windows-service installation, PostgreSQL and the oracle run. |

The Codex results are reference evidence only. They were not used as acceptance for this implementation.

## Reproduce (Linux)

```sh
dotnet publish app/poc/p1_hosting/aspnet -c Release -o <pub>
dotnet <pub>/MimamsaPocApi.dll --ledger-oracle "Host=...;Database=poc_oracle"
python app/poc/p1_hosting/r2n01/test_r2n01.py --server-cmd "dotnet MimamsaPocApi.dll" --server-cwd <pub> --db ... --npgsql ... --big <pdf> --small <pdf> --out out.json
python app/poc/p1_hosting/r2n01/trace_n01.py --server-cmd ... --server-cwd <pub> --db ... --npgsql ... --out-dir <dir>
python -B transport_oracle.py --trace <dir>/normalized_trace.json --http-cases app/poc/p1_hosting/r2n01/n01_http_cases.json
```
