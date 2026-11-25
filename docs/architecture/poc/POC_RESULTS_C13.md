# C13 B-PoC results: technology proofs of concept for the offline application

Branch `claude/c13-b-poc`. Everything in this document is **measured** unless it is marked *estimated* or BLOCKED.
Hardware, versions and deviations are in [ENVIRONMENT_C13.md](ENVIRONMENT_C13.md). Raw data is in `data/`.
Owner direction: Windows-native deployment. Linux numbers come from a shared 4-vCPU VM. Hosted-Windows numbers come
from GitHub `windows-latest`. **Selected-host acceptance is BLOCKED until the owner's hardware is available.**

## Recommendation (evidence-backed)

| Decision | Recommendation | Main evidence |
|---|---|---|
| P1 host | **ASP.NET Core 10 (LTS) on Kestrel, as a Windows Service** (`UseWindowsService`, virtual service account, SCM recovery). IIS/ANCM (web.config provided) only if the T1 proxy topology is later proven. | Quiet-host rerun: metadata 12,689 req/s vs best Django 1,226; PDF 893 vs 639; search 99 vs 71 (DB-bound). One process of 85–135 MB RSS vs 240–270 MB for 4 Django workers. A single process uses all cores; a Django Windows Service is effectively one GIL-bound worker. R2-N01 was built and proven on Kestrel (PipeWriter handoff, cross-platform TCP-state drain probe). Both services installed, restarted and crash-recovered on hosted Windows. |
| P2 search | **Lexical BM25 (Tantivy) with abbreviation expansion and an exact-identifier layer as the primary ranker.** Add dense hybrid only after full-text vector coverage is affordable. PostgreSQL FTS stays for filters and facets, not ranking. | nDCG@10 0.72 (bm25+abbr+id) vs 0.62 (PG FTS tiered+abbr+id), 0.61 (hybrid with head-only dense) and 0.33 (dense alone). The identifier layer lifts exact-ID Target@1 from 0.53 to 0.82. Abbreviation expansion lifts abbreviation-query P@10 from 0.54 to 0.83. |
| P3 embeddings | **bge-small-en-v1.5 (MIT), int8 ONNX on CPU** if a dense layer is used. | Best dense quality among the models judged. int8 costs ≈0.03 nDCG vs fp32 and is ≈2–6× faster. Base models are 3–4× slower and 2–4× larger in memory. |
| P4 PDF | **pypdfium2** (Apache-2.0/BSD-3) for extraction and char boxes. **PDF.js with a custom authenticated range transport** for viewing. Avoid PyMuPDF (AGPL) in the shipped product. | pypdfium2 matches PyMuPDF quality, is fastest with the lowest RSS, and has no `(cid:)` artefacts, which pdfminer and pdfplumber produce. 46.8 MB PDF: near-end page using 4.2 % of the bytes. |
| P5 jobs | **PostgreSQL `SKIP LOCKED` queue with leases, advisory-lock concurrency slots and sandboxed parsing** | Every scenario demonstrated (below). |

## P1 hosting

Linux runs on the shared host, using autocannon on the same 4 vCPUs. Run 1 was taken under contention (load 9–23).
Run 2 was taken on a quieter host (load 1–11). Both are kept: `data/p1_linux_bench_run1_contended.json` and
`data/p1_linux_bench_run2.json`.

| Server (run 2) | Cold start to /health | Idle RSS | Search c=10 rps / p99 | Metadata c=50 rps / p99 | PDF 87 KB c=10 rps / p99 |
|---|---|---|---|---|---|
| ASP.NET Core 10 Kestrel (1 proc) | 0.56 s | 85 MB | 89 / 194 ms | 12,689 / 10 ms | 893 / 27 ms |
| Django 6.1 + uvicorn, 4 workers | 0.87 s | 240 MB (6 procs) | 56 / 268 ms | 778 / 130 ms | 247 / 67 ms |
| Django 6.1 + hypercorn, 4 workers | 0.85 s | 245 MB | 69 / 252 ms | 1,181 / 119 ms | 284 / 51 ms |
| Django 6.1 + uvicorn, 1 worker | 0.36 s | 51 MB | 67 / 249 ms | 425 / 233 ms | 301 / 60 ms |

Anomaly, reproduced in both runs and not root-caused: uvicorn with 4 workers shows a fixed p50 of about 45 ms at
concurrency 1. One worker or hypercorn does not.

**Hosted Windows, measured in CI.** Both services installed under `NT SERVICE\…` virtual accounts with SCM failure
actions. Smoke tests, the 401 check, search, metadata, PDF Range 206, graceful restart and crash recovery
(`Stop-Process -Force` → SCM restart with a new PID) all **passed for both ASP.NET Core and Django**. pgvector
0.8.1 built from source on the runner's PostgreSQL (step green; output in the CI artifact). Windows load numbers
are informational only (hosted runner).

| Criterion | ASP.NET Core | Django (ASGI) |
|---|---|---|
| Windows fit | Native Windows Service host, IIS/ANCM option, Windows auth available | Needs pywin32 + pythonservice.exe. psycopg async needs a SelectorEventLoop on Windows. Multi-worker inside a service is non-trivial. |
| Security isolation | Single process, virtual account, ACL-scoped folders | Same accounts possible. Larger runtime surface (interpreter + site-packages). |
| Performance (measured) | ≈10× on framework-bound endpoints | DB-bound endpoints are closer (≈1.4×) |
| Packaging | `dotnet publish` (framework-dependent or self-contained), MSI later | venv/embedded Python plus pinned wheels |
| Licences (from metadata) | MIT + PostgreSQL (Npgsql) | BSD/MIT. psycopg is LGPL-3.0 (acceptable as a replaceable dependency). |
| Local AI | ONNX Runtime has a first-class C# API; tokenizers need a .NET port or sidecar | Python ecosystem is richer for ML tooling |
| Maintainability | Static typing; R2-N01 core is a separate platform-neutral library | Faster prototyping; ORM unused in the PoC |

Python remains appropriate for **offline batch** work (corpus pipeline, embedding builds, PDF extraction) behind
the job queue. It is not appropriate for the protected-delivery host.

## R2-N01 protected delivery

Full detail: [R2N01_PROTECTED_DELIVERY_POC.md](R2N01_PROTECTED_DELIVERY_POC.md).

- Linux: 40/40 HTTP transport checks, the Serving §10 ledger oracle 7/7, and 12/12 PDF.js protected-viewer checks.
- PR #54 `transport_oracle.py` (unmodified, hash-pinned) **accepted** both Linux traces and the hosted-Windows trace. Peak charge was 196,608 B (= site cap), 0 residual. Withdrawal admit→ack took 16 ms on Linux and 10 ms on Windows.
- Hosted Windows: ledger oracle, 40/40 transport checks and the trace oracle are all green.
- The Windows PDF.js step failed on the first CI attempt with the synthetic fixture: the 300-page fixture's page tree forced a full fetch. The fixture was fixed; see the final CI run.
- Selected host: **BLOCKED (owner hardware pending)**.

## P2 search and retrieval

**Corpus.** 2,455 documents from data snapshot `ad77758d`: 2,400 judgments (all 346 SC, plus a seeded HC sample) and
55 statutes (Acts, Rules, Regulations, notifications). The restricted-material list was applied, excluding RM-001.

**Queries.** 71: 12 case names, 14 case numbers/citations, 3 AFT OA numbers, 12 statute references, 10 abbreviation
queries, 10 legal-term queries and 10 natural-language queries. Identifier targets were drawn from metadata with a
fixed seed before any system ran.

**Labels — AI-labelled.** 1,089 pooled items were judged blind to system (sha1 order, title and snippet only) for
the abbreviation, legal-term and NL categories. Pooling depth was 10 for the five headline systems, 3 for the
variants and 5 for each P3 model. Identifier and statute categories used objective rules (target doc, or exact
identifier/section string in the text, including an unpooled full-collection scan). The labeller is the same AI
that built the systems, so independent human review is needed.

| System | nDCG@10 | MRR | P@10 | CapR@10 | Exact-ID T@1 | Abbrev P@10 |
|---|---|---|---|---|---|---|
| bm25+abbr+id | **0.723** | **0.871** | **0.434** | **0.769** | **0.824** | **0.83** |
| bm25+abbr | 0.659 | 0.803 | 0.428 | 0.720 | 0.529 | 0.83 |
| bm25 | 0.611 | 0.744 | 0.389 | 0.679 | 0.529 | 0.54 |
| pg_fts_tiered+abbr+id | 0.621 | 0.785 | 0.414 | 0.720 | 0.824 | 0.73 |
| pg_fts | 0.494 | 0.651 | 0.352 | 0.588 | 0.294 | 0.44 |
| dense bge-small (FAISS, NOT pgvector; head chunks) | 0.333 | 0.595 | 0.266 | 0.351 | 0.176 | 0.56 |
| rrf(bm25+abbr, dense)+id | 0.607 | 0.785 | 0.385 | 0.671 | 0.824 | 0.73 |

**Latency.** Quiet host, in-process, 71 queries × 2. p50/p95 at concurrency 1: BM25 3.2/5.1 ms; dense including
query embedding 6.8/11.5 ms; RRF+id 12.3/27.9 ms; PG FTS 81/220 ms. At concurrency 10 tantivy-py serialised
(31 qps): a Python-binding limit to re-test with the Rust or .NET binding. PG FTS reached 71 qps and dense 137 qps.
(`data/p2_latency.json`)

**Exact identifiers are preserved** only with the identifier layer. Three identifier queries still miss: AFT OA
numbers that appear only in judgment text and are not in the metadata.

**Not done:** a pgvector measurement (BLOCKED locally because the server headers are missing; it built on hosted
Windows, but the benchmark was not run there), and the dense full-text index (compute-bound; see ENVIRONMENT).

## P3 local embeddings

All eight models were downloaded with their revisions and per-file sha256 pinned in
`app/poc/p3_embeddings/models.lock.json`. Licences come from the model cards: MIT (BGE, E5) and Apache-2.0
(Arctic, MiniLM, Nomic). int8 copies were made locally with `onnxruntime.quantization.quantize_dynamic`; they are
not hashed in the lock and are reproducible from it.

| Model (P3 subset: 3,367 chunks) | nDCG@10 dense | Hybrid nDCG@10 | Judged@10 | Index throughput (chunks/s, int8, full set) |
|---|---|---|---|---|
| bge-small fp32 | 0.333 | 0.607 | 1.00 | 2.3 (fp32, contended) |
| bge-small int8 | 0.306 | 0.607 | 0.84 | 14.6 |
| e5-small-v2 int8 | 0.273 | 0.590 | 0.67 | 14.1 |
| arctic-embed-s int8 | 0.255 | 0.609 | 0.70 | 13.1 |
| all-MiniLM-L6 int8 | 0.223 | 0.573 | 0.68 | 25.5 |

Base models (bge-base, e5-base, arctic-m, nomic) were measured on throughput, latency and memory only, in
128-chunk micro runs: 1.1–1.8 chunks/s fp32 and 2.6–4.4 chunks/s int8 under contention, with 1.3–2.8 GB peak RSS.
**Their retrieval quality was not measured** (compute budget). Models other than bge-small fp32 were pooled only at
depth 5, so their lower Judged@10 biases their scores downward; read the comparison as indicative.
Micro-run timings were taken under load 9–15, the full-set int8 runs under load 8–10.

## P4 PDF processing (`data/p4_extract.csv`, `data/p4_pdfjs.json`)

| Library | Speed (BNSS, 282 pp) | Peak RSS | Fidelity | Coordinates | Licence |
|---|---|---|---|---|---|
| pypdfium2 5.15.2 | 1.0 s | 28 MB | = PyMuPDF; no `(cid:)` | char boxes, search rects | Apache-2.0 / BSD-3 |
| PyMuPDF 2.1 | 1.3 s | 60 MB | reference | words, search_for | **AGPL-3.0** or commercial |
| pdfminer.six | 26.8 s | 51 MB | 196 `(cid:)` tokens on the OCR'd scan | LTChar boxes | MIT |
| pdfplumber 0.11 | 69.8 s | 1,645 MB | as pdfminer | words, search | MIT |

- Scanned files have almost no text layer (1 of 36 pages), so OCR is needed.
- Every library emits 171 private-use characters for the Hindi Air Force Act (legacy font encoding), so Hindi needs OCR.
- PDF.js 6.5.438 with highlight overlay works. Proportional in-item positioning is slightly off on justified text (screenshot `img/`). Use server-side char boxes or the PDF.js text layer for exact highlights.
- A static server with no initial Range support made PDF.js fetch the whole 46 MB file. The Kestrel range API fetched 1.4 MB.

## P5 background processing (`data/p5_jobs_demo.json`)

Measured on Linux. All parts were demonstrated:
- Idempotent enqueue: 24 attempted, 12 created. Results are upserted, so `runs = 1`.
- Retries with jittered exponential backoff (≈1 s, then 2 s), with a poison job ending `dead` after 4 attempts.
- **kill -9 mid-job**: a 4 s lease expired, the job was requeued and resumed from checkpoint step 4/10, then succeeded.
- Progress reporting.
- Per-kind concurrency through session advisory-lock slots: OCR at most 1, parse at most 2 observed. Slots are freed automatically when a worker dies.
- Sandboxed parsing:
  - runs as uid `nobody` in an empty network namespace;
  - `/etc/shadow` denied;
  - `RLIMIT_AS` stops a memory bomb;
  - wall timeout stops a hang;
  - `RLIMIT_CPU` stops a spin.

Windows equivalents (design only, not run):
- Job Objects (memory, time and process limits; kill on close);
- a restricted token or AppContainer;
- a firewall rule for the sandbox executable;
- the worker as a dedicated virtual-account service.

## P7 licence and security (`data/p7/`)

CycloneDX SBOMs were produced for:
- the Python venv and three candidate sets;
- npm (PDF.js app);
- .NET (CycloneDX 5.5.0 with roll-forward).

Licences were read from package metadata and model cards:
- **PyMuPDF AGPL-3.0** (avoid);
- psycopg LGPL-3.0 (acceptable as a dependency);
- pymupdf4llm/layout metadata says UNKNOWN;
- everything else MIT, BSD or Apache, plus PostgreSQL (Npgsql).

Vulnerability scans: `pip-audit`, `npm audit` and `dotnet list package --vulnerable` all found **0 known
vulnerabilities**. These are online lookups made from the connected build host, not offline scans.

## P8 (design only)

[P8_SIGNED_BUNDLE_UPDATE_DESIGN.md](P8_SIGNED_BUNDLE_UPDATE_DESIGN.md) covers the Ed25519 manifest signature,
SHA-256 pinning, atomic `active.json` swap and rollback, and the restricted-material check at build and import.
P6 and P9 are later phases.

## Still needs a Windows run (selected host)

- All of R2-N01 on the selected host: T0 with TLS, observation of the real browser session, byte-level kernel occupancy via GetPerTcpConnectionEStats, and the 25-browser / 10-query fence-latency load.
- P1 load measurements on representative hardware.
- The pgvector benchmark.
- P5 Job Object sandbox implementation.
- An MSI/service packaging trial.
