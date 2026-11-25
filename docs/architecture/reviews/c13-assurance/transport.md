# R2-N01 protected delivery assurance

**Selected Windows/TLS acceptance remains open.** The Python reference establishes bounded request and revocation behavior on synthetic loopback. The applicable existing P1/P4/P5/P8 acceptance work must verify the selected Windows topology. The independent checker tests trace consistency and the accompanying fixtures define expected and prohibited results for N01-01 through N01-08. [R3.1 serving and revocation contract, §§6, 9 and 10](https://github.com/hariomahlawat/mimamsa-corpus/pull/53) · [Independent R3 review](https://github.com/hariomahlawat/mimamsa-corpus/blob/e97b3de2656000712bb1cd061d88a78dd86cb8b0/docs/architecture/reviews/intelligence_pr53_r3_05cd3bf.md#3-serving-and-recovery--condition-on-r2-n01) · [Case catalog and trace fixtures](transport-fixtures.json)

## Reference results

| Evidence | Environment | Observation |
|---|---|---|
| Independent HTTP client, N01-03 and N01-05 through N01-08 | Commit `fbeda3745b21047278b3477a7db3d701d69994bf`, Linux 6.18.57 x86-64, Python 3.12.14, cleartext loopback | Authenticated metadata correctly pinned the 396,871-byte PDF. Exact eligible ranges 0–131,071 and 396,614–396,870 returned 206 with matching headers and bytes. Thirteen authorization, identity, range and conditional controls passed. An active 64 KiB range ended early after the in-memory withdrawal and delivered exactly 16,384 bytes, of which 4,096 were received before the fixture called withdrawal. Three fresh metadata or range requests received generic 404, including both valid and invalid range syntax relative to the copy length. |
| Reference suite, N01-01 through N01-03, N01-05 and N01-06 | Same commit and Linux environment | Nine tests passed. The budget, partial and unknown results used adapter callbacks. The HTTP cases used real loopback sockets. |
| Prior independent Chromium runner, N01-05 | Same reference harness and viewer blobs as the prior Linux run, Chromium 156.0.8078.79 and PDF.js 5.4.624 | Pages 1 and 12 rendered. Seven authorized 206 requests covered the 396,871-byte PDF through bounded ranges. The first request was 0–65,535 and the first near-end request was 393,216–396,870. This run exercised eligible navigation. |
| Prior Linux loopback benchmark, N01-04 | Same reference harness and benchmark blobs, Linux 6.18.57 and Python 3.12.14 | Each sample completed 80 requests at concurrency 10 and retained 5,258,720 wire bytes. Across three samples, p95 was 14.495–20.628 ms, maximum 25.959–1,032.756 ms and throughput 77.02–957.46 requests/s. The workload stopped before the retained credit exhausted the site cap. |
| Hosted Windows reference CI, N01-01 through N01-03, N01-05 and N01-06 | Same commit, Windows Server 2025 build 26100, Python 3.12.10 | Nine synthetic tests passed in 0.396 s. The 80-request loopback sample at concurrency 10 retained 5,258,720 wire bytes and measured 7.359 ms p50, 27.238 ms p95, 519.935 ms maximum and 143.92 requests/s. |
| Trace checker vectors, N01-01 through N01-07 | Constructed normalized inputs, Python 3.12.14 | One consistent vector and 16 deliberately inconsistent variants behaved as expected. These inputs verify checker behavior. |

The black-box client records headers, bytes and early EOF independently of the server's logs. It uses the harness's documented pause hook to order one transfer relative to an in-memory withdrawal. It does not independently observe real socket acceptance, kernel occupancy, a durable CAS or a browser cancellation. The short benchmarks report request durations with credit retained in the reference process. They do not measure sustained throughput, slow-client backpressure, drain or valid-update-to-durable-fence latency. The Windows job establishes portability of the synthetic reference and provides no evidence about the selected Windows service, browser session, TLS stack or storage. [Pinned reference commit](https://github.com/hariomahlawat/mimamsa-corpus/commit/fbeda3745b21047278b3477a7db3d701d69994bf) · [Hosted Windows job](https://github.com/hariomahlawat/mimamsa-corpus/actions/runs/45638259239/job/139289469656)

## Selected Windows acceptance procedure

1. Record exact service, framework, Windows build, TLS and socket adapter, storage and witness custody, browser and PDF.js versions. Declare T0 or the exact tested proxy topology. Use a distinct synthetic affected PDF, unrelated eligible PDF, known authorized and unauthenticated requests, and a deterministic fixture identity/offset map. Keep protected fixture content and credentials out of trace artifacts.
2. Capture reservation and settlement records from the ledger. Independently observe exact byte-slice ownership transfer at the terminal boundary, including protected headers and metadata. Capture downstream residual occupancy and verified drain or termination across the framework/TLS/kernel and any proxy. Record retransmitted physical bytes separately from unique residual payload. Collect the durable witness CAS from an independent storage probe and client receipt from a separate HTTP/browser capture. Application logs can correlate operation, epoch, reservation and stream IDs.
3. Run both cap races with synchronized contenders, including two attempts for the final 64 KiB on one connection and on distinct connections. Force 16 KiB acceptance of a 64 KiB attempt, conclusive zero acceptance, ambiguous completion with possible partial transfer, duplicate completion, route reset and restart. Compare charged reservations against observed residual occupancy throughout. Release unresolved charge only on independently verified drain, termination or reconciliation.
4. Hold real slow readers and blocked writers under the target mix of 25 browser sessions and 10 queries. Run withdrawal while present and record valid-update admission, durable CAS, acknowledgment and affected stream cancellation. Check zero affected post-fence terminal acceptance, bounded occupancy and the proposed p95 ≤1 s and maximum ≤5 s admission-to-acknowledgment targets. Retain timed-out or uncertain runs and report their outcome. Test an unaffected eligible route for each denial or cancellation scenario.
5. Load an eligible PDF above 256 KiB in the selected authenticated browser, render the first page and jump near the end. Collect metadata and every request from the first byte fetch, assert the pinned copy and exact bounded single range 206 headers and bodies, then repeat with withdrawal between chunks. Confirm cancellation and application-controlled viewer invalidation, fresh generic denial and unaffected viewer rendering. Run the unauthorized, stale identity, no-range, malformed, oversized, multiple, duplicate-header and conditional controls.
6. Inject process and storage faults around durably prepared policy and witness CAS. Compare prepared-only state, acknowledged committed state, lost acknowledgment, corrupt current state, and missing independent current witness. Confirm that only exact current authenticated witness state can reopen delivery and unresolved bytes remain charged until proof. Repeat active-stream cancel and reattach, including ambiguous offsets and unrelated controls.
7. Preserve the independent source evidence, ordered normalized events, pinned fixture expectations, environment and measurement methodology with each N01 case ID. Review source ordering around every pause point, itemized physical downstream capacity and unobserved gaps before recording selected-platform passage. A within-cap sample with no independently observed terminal or witness evidence cannot close the gate.

## Running the checker

Run from the repository root. The reference mode loads only the two Git blobs from the pinned commit into a temporary directory and binds the test server to loopback. A repository with that Git object may be supplied in place of `.`. The generated session credential remains inside the fixture.

```sh
python -B docs/architecture/reviews/c13-assurance/transport_oracle.py --self-test
python -B docs/architecture/reviews/c13-assurance/transport_oracle.py --reference .
python -B docs/architecture/reviews/c13-assurance/transport_oracle.py --trace normalized.json --http-cases expected-http.json
```

### Normalized trace

Use the `vector` object in [transport-fixtures.json](transport-fixtures.json) as the input format. Fix the site and connection limits in charged wire bytes and set `initial_witness` from verified current custody. Each event has `seq`, `kind`, the asserted evidence `source`, and the fields below. `seq` is a strictly increasing order derived from synchronized probes and deterministic barriers. It represents the terminal ownership transition and durable witness acceptance at their actual boundaries. During review, verify independent provenance and ordering against the raw capture.

| Kind | Source tag | Additional fields |
|---|---|---|
| `reserve` | `ledger` | Unique `attempt`, `connection`, `stream`, `copy`, `epoch`, byte `offset` and worst-case charged `size`. A stream is one contiguous response with independent wire offsets. |
| `enter` | `policy_probe` | `attempt` for a fresh successful recheck while holding the handoff guard. A prior reservation alone does not permit terminal acceptance. |
| `accept` | `terminal` | `attempt`, exact accepted prefix `offset` and `size` in the same wire unit. |
| `settle` | `ledger` | `attempt` and `outcome` of `accepted`, `zero` or `uncertain`. For an accepted outcome add exact `size`. |
| `occupancy` | `drain_probe` | Independent unique deliverable wire-byte counts in `connections` and total `site`. Record separate raw physical occupancy and retransmit metrics. |
| `prove_release` | `drain_probe` | `attempt` and confirmed `proof` of `drain`, `termination` or `reconciliation`, with raw proof retained. |
| `admit` | `policy_probe` | Valid withdrawal `operation`, exact synthetic `copy` and `monotonic_ms`. |
| `fence` | `witness` | `operation`, `copy`, next `epoch` and exact committed `digest`. The case manifest must specify the full affected dependency scope. |
| `ack` | `client` | `operation`, `epoch`, `digest` and `monotonic_ms` on the admission clock. Report first admitted-to-ack latency separately from retry latency. |
| `cancel` or `receive` | `client` | `stream` for cancellation. `attempt` and received `size` for receipt, correlated to the terminal capture. |
| `restart` or `recover` | `fault_driver` or `witness`, respectively | No additional fields for a restart. Exact current `epoch` and `digest` for recovery. |
| `http` | `client` | Named `case` and the fields in the separate pre-pinned HTTP case dictionary. Use `authenticated`, `copy`, `status`, `length`, `content_range` and applicable `range`, `conditional`, `phase` or synthetic body digest fields. |

The command reports observed event counts, peak and remaining wire charge, HTTP case IDs, authority state and admission-to-ack samples. A successful exit means the supplied events are consistent with these invariants. Reviewers must verify source provenance, interval coverage, current custody, crash outcomes, browser behavior, elapsed-time distributions and every case's required evidence before updating the case status. The script does not acquire production probes and source tags alone do not establish independence.
