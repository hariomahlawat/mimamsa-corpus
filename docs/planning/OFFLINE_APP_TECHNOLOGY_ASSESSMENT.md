# Mimamsa offline application: technology assessment

- **Recorded:** 2026-11-24
- **Status:** Assessment and recommendation for owner review. It is input to ADR-0005, which Cycle 13 Track B workstream B0 drafts after the proofs of concept in §16. It is not an implementation authorisation.
- **Scope:** the runtime application that serves the corpus on an air-gapped LAN, and the update path from Hugging Face to that LAN. The crawler and audit tooling are out of scope; they stay as they are.
- **Companion:** [CYCLE13_EXECUTION_PLAN.md](CYCLE13_EXECUTION_PLAN.md).

**How to read maturity claims.**
- Versions are given only as **"current stable at selection time"**. The exact versions are pinned in ADR-0005 and the lockfiles.
- Licence statements reflect the assessor's knowledge and must be **re-verified against each project's licence file at selection** (PoC P7). Several projects in this space have changed licence in recent years.
- Items marked **[PoC]** are claims this assessment is not sure of. They need measurement before they are relied on.

## 1. Requirements the stack must meet

| ID | Requirement | Source |
| --- | --- | --- |
| T-01 | **Fully air-gapped runtime**: no internet calls for search, OCR, embeddings, models, fonts, telemetry or updates. Updates arrive only as checksummed (and signed) snapshot bundles | PR-12; Architecture §9 |
| T-02 | Corpus of about 2 GB and 16k files today, growing to about **20 GB**. About 3,936 judgments plus Acts and Rules. Mostly English with some Devanagari. Many scanned PDFs | Corpus facts; HF verification C12 |
| T-03 | **PDF rendering of the original bytes** with page anchors and hit highlighting, for native PDFs and scans | PR-06; Architecture §10 |
| T-04 | **Hybrid search**: BM25-class lexical search plus local vector search, with filters and exact handling of section and rule numbers | PR-01; Architecture §8 |
| T-05 | A **graph** of instruments, provisions, judgments and proceedings with typed, evidence-anchored edges and per-edge verification state | PR-08; Architecture §5 |
| T-06 | **Exactly two roles**, Admin and User. Admin-only corpus mutation is enforced server-side. Working sessions are isolated per user | ADR-0002; ADR-0003 |
| T-07 | **Withdrawal must not leak**. A withdrawn or unpublished source disappears from every index, embedding store, graph view and cache | ADR-0002 decision 7; Ingestion §7 |
| T-08 | A **small ops team**: few services, boring components, simple backup and restore | Owner direction (capability first) |
| T-09 | **Windows or Linux LAN servers**. Clients use a browser | Brief |
| T-10 | Security baseline: parser isolation, integrity hashes, metadata-only audit, backups, prompt-injection isolation (for later LLM use) | Architecture §11 |
| T-11 | Maintainable and licence-clean for an internal government deployment. No dependence on a single vendor or model | Scenario engine §9 |
| T-12 | Offline OCR and embedding at ingestion time on CPU, with a modest GPU optional | PR-12; Ingestion §2 |

## 2. Sizing (estimates; to be confirmed in PoC P1/P2)

| Quantity | Today (about 2 GB) | At 20 GB | Basis |
| --- | --- | --- | --- |
| Extracted text | a few hundred MB | a few GB | Text is typically a small fraction of PDF bytes, and scans contribute only OCR text |
| Passages (paragraph or about 300-token chunks) | ~0.2–0.5 M | ~2–5 M | ~4k judgments × tens of pages × a few passages per page, plus statutes |
| Vectors at 768 dims, float32 / half precision | ~0.6–1.5 GB / half that | ~6–15 GB / half that | 3 KB per vector at float32 |
| Graph edges | ~10^4–10^5 (C11 alone: 11,076 statute links and 2,595 treatment candidates) | ~10^5–10^6 | Grows with citation extraction |
| Concurrent users | tens on a LAN | tens to low hundreds | Assumption; D-01 |

**Conclusion.** This is a **small-to-medium** search workload. A single well-provisioned server handles it. Distributed search clusters are not justified by size.

## 3. Recommendation at a glance

| Layer | Recommendation | Main alternative / exit path |
| --- | --- | --- |
| Backend | **Python, Django** (LTS line) with a typed JSON API layer (Django Ninja or DRF; pick in B0). Domain logic lives in framework-independent packages | FastAPI + SQLAlchemy/Alembic |
| Job execution | **PostgreSQL-backed job queue** (candidates: Procrastinate, the django-tasks database backend, or a minimal `SKIP LOCKED` table) [PoC] | Celery with Valkey |
| Database | **PostgreSQL** (current stable major) | SQLite (+FTS5, +sqlite-vec) for a single-user desktop edition only |
| Lexical search | **PostgreSQL full-text search** for the first deliverable. **[PoC]** against true BM25 (embedded Tantivy) before GB1 | Tantivy sidecar index. OpenSearch if requirements outgrow one server |
| Vector | **pgvector** (HNSW, half-precision vectors) | Qdrant (single binary) |
| Graph | **Relational edge tables + recursive CTEs** in PostgreSQL; NetworkX for offline analytics | Apache AGE (Cypher in Postgres). Neo4j Community only if graph analytics demand it (licence caveats) |
| Embeddings | **BGE / E5 / Arctic-embed class English models via ONNX Runtime on CPU**; choose by PoC P2 | Multilingual variant (e.g. bge-m3 / multilingual-e5) if Devanagari recall matters |
| Reranker | **Cross-encoder reranker** (BGE reranker class) on the top 50–100, optional per query [PoC] | None (hybrid only) |
| Local LLM | **None in Cycle 13.** Later, gated: llama.cpp-served open-weight model with a permissive licence, drafting assistance only | vLLM on a GPU server |
| OCR | **Tesseract** (already used for 944 scanned judgments), per-page confidence; PaddleOCR evaluated on low-confidence pages [PoC]; Prism if D-10 confirms it | PaddleOCR as primary if P4 shows a clear gain |
| PDF viewer | **PDF.js** (pdfjs-dist), script evaluation disabled | — |
| Frontend | **React + TypeScript + Vite**; Cytoscape.js for graphs | Server-rendered Django templates + HTMX |
| Packaging | **Docker Compose on a Linux host** (Docker Engine or Podman), images transferred as signed tarballs. On Windows hosts, a **Linux VM under Hyper-V** | Native installers (high maintenance; last resort) |
| Auth | **Local accounts** (Django auth, Argon2 hashing); optional **LDAP/AD** mapping an AD group to Admin | Kerberos SSO later |
| Updates | **Signed release bundle** from a pinned HF revision → offline verify (signature + `SHA256SUMS`) → new release generation → atomic switch → rollback | — |
| Storage | **Content-addressed filesystem vault** for originals; derivatives keyed by (sha256, pipeline version) | Object store only if multi-node (avoid MinIO licence and edition churn) |
| Reverse proxy | Caddy or nginx with an internal-CA certificate | — |

The design principle is **one database, few services.** For a small ops team, PostgreSQL carrying relational data, full-text search, vectors, the graph and the job queue means:
- one backup;
- one restore;
- one transaction boundary, which is what makes T-07 withdrawal leak-proof by construction.

A separate engine is added only when a PoC shows that PostgreSQL misses a measured requirement. This matches Architecture §8.

## 4. Backend

| Criterion | Django (+ Ninja/DRF) | FastAPI (+ SQLAlchemy, Alembic) | Others (Node/NestJS, Go, .NET) |
| --- | --- | --- | --- |
| Fit with existing code | Python: reuses pipeline, PyMuPDF/pdfplumber, ONNX Runtime and the HF tools | Python: same | Re-implements or bridges the Python pipeline; two languages |
| Auth, sessions, CSRF, password hashing | **Built in and long-audited**; Argon2 supported; django-auth-ldap exists | Assemble from libraries; more security-sensitive glue to write and review | Varies |
| Migrations / admin back office | Built in (migrations; Django admin useful for ops screens) | Alembic; no admin | Varies |
| Typed API / OpenAPI | Ninja: Pydantic-style typing; DRF: mature serialisers | **Excellent** (native Pydantic, OpenAPI) | Good |
| Async / streaming (later LLM) | ASGI and async views supported; adequate | **Native async** | Good |
| Long-term maintenance | LTS releases with a published security process | Fast-moving; fewer guarantees on long support windows | — |
| Small-team risk | Low: conventions limit design drift | Medium: more architectural choices to own | High (language split) |

**Recommendation: Django.** The decisive factors are T-06, T-08 and T-10. Two roles, server-side mutation checks, sessions, CSRF and LDAP are exactly what Django already does well, and every line of hand-written auth glue is review and attack surface. FastAPI's advantages (typing, async) matter less here: search is database-bound and OCR/embedding run in workers.

- **Risk:** coupling domain logic to the ORM.
- **Mitigation and exit path:** keep ingestion, search, provenance, release import and graph logic in plain Python packages (`mimamsa_core`) with explicit SQL or a thin repository layer. Django is then the HTTP/auth shell, and moving to FastAPI later means replacing the shell, not the core.

**Workers.** Use the same codebase, run as separate processes or containers with a different security profile (no network, read-only vault, resource limits). A PostgreSQL-backed queue avoids adding Redis or RabbitMQ. **[PoC P6]**: confirm the chosen queue library's maturity, licence and behaviour under a bulk import of about 16k files. If none is satisfactory, a 200-line `SELECT … FOR UPDATE SKIP LOCKED` job table is an acceptable fallback. Exit path: Celery with Valkey (BSD-licensed Redis fork; Redis itself changed licence in 2024, so verify).

## 5. Database

| Criterion | PostgreSQL (+FTS, +pgvector) | SQLite (+FTS5, +sqlite-vec) | Others (MySQL/MariaDB, DuckDB) |
| --- | --- | --- | --- |
| Multi-user LAN server, concurrent ingestion writes | **Strong** (MVCC) | Single writer. Fine for one user, a constraint for a server with background ingestion | MySQL is fine but weaker in FTS, vectors and recursive queries; DuckDB is analytical and single-process |
| Full-text search | Built-in tsvector/GIN; ranking is *not* BM25 (ts_rank/ts_rank_cd) | FTS5 has **BM25 built in** | — |
| Vectors | pgvector: mature, widely deployed, HNSW and IVFFlat, half-precision | sqlite-vec: pre-1.0, mainly brute force; **maturity risk** | — |
| Graph | Recursive CTEs; Apache AGE optional | Recursive CTEs | — |
| Transactions across data, FTS and vectors | **Yes** (T-07) | Yes | — |
| Backup / PITR | pg_dump; pgBackRest or WAL archiving | File copy (when quiesced) | — |
| Windows / Linux | Both | Both (embedded) | — |
| Licence | PostgreSQL licence (permissive); pgvector also PostgreSQL licence | Public domain; sqlite-vec MIT/Apache (verify) | GPL (MySQL server) |

**Recommendation: PostgreSQL.**
- SQLite's FTS5 BM25 is attractive, but a shared LAN server with background ingestion, many readers and an Admin publication workflow is PostgreSQL's home ground.
- **Exit path and secondary use:** SQLite (FTS5 + sqlite-vec) remains a credible engine for a future *single-user, laptop-only* edition built from the same release bundle. Keep the release-bundle format engine-neutral (JSONL/Parquet + PDFs) so that remains possible.

## 6. Lexical search

| Criterion | PostgreSQL FTS | Tantivy (embedded, via tantivy-py) | Meilisearch | OpenSearch |
| --- | --- | --- | --- | --- |
| Ranking | ts_rank_cd (no IDF saturation; not BM25). True BM25 needs an extension: ParadeDB pg_search, VectorChord-bm25 or pg_textsearch (verify licences; several are AGPL or source-available) | **BM25**, phrase and proximity queries, custom tokenisers | Custom relevance (typo-tolerant, bucket sort), not classic BM25 | **BM25**, mature analyzers, highlighting |
| Hybrid built in | No (fuse in app with pgvector) | No (fuse in app) | Yes (hybrid search) | Yes (k-NN + hybrid pipelines) |
| Consistency with publication state (T-07) | **Transactional** | Separate index; deletes and rebuilds must be orchestrated | Separate service; asynchronous indexing | Separate service; near-real-time refresh |
| Ops weight | None extra | Library; index files on disk | One extra service (light) | JVM cluster or single node; heap tuning; security plugin. **Heaviest** |
| Highlighting/snippets | ts_headline (adequate, can be slow on long docs; store passages) | Snippet generator | Good | Excellent |
| Licence | PostgreSQL | MIT (core and Python binding; verify) | Community edition MIT; some enterprise features under a source-available licence (verify) | Apache 2.0 |
| Maturity | Very high | Core high; **Python binding less mature [PoC]** | Medium–high | High |

**Recommendation.**
1. Start with **PostgreSQL FTS at passage level**, with a legal-aware configuration:
   - a `simple` dictionary variant so that "69", "22(3)(a)" and "s.69" survive tokenisation;
   - an English stemmed column for prose;
   - synonym normalisation for "AA" → "Army Act" and "court-martial" vs "court martial", following CLAUDE.md pipeline step 6.
2. **[PoC P1]**: compare ts_rank_cd, true BM25 (Tantivy embedded) and the hybrid of each with pgvector on the retrieval benchmark.
3. If true BM25 adds a material gain (proposed threshold: ≥5 points recall@20 on the held-out queries), adopt **Tantivy as a derived, rebuildable index** written by the worker after each publication or withdrawal. Add a consistency check that blocks search if index and DB generations differ.
4. Prefer that over a BM25 Postgres extension only if the extension's licence passes D-02.

**OpenSearch** is the exit path if the corpus or features outgrow this. Examples: hundreds of GB, many concurrent users, advanced analyzers or learning-to-rank. It is not recommended now: its ops weight is out of proportion to a 2–20 GB corpus and a small team. Elasticsearch is not preferred over OpenSearch for licence-simplicity reasons (verify current terms). Meilisearch is pleasant but its ranking model and asynchronous indexing fit legal exact-match and withdrawal semantics less well. Vespa is powerful but heavy.

## 7. Vector store

| Criterion | pgvector | Qdrant | Others (FAISS, LanceDB, Chroma, sqlite-vec, Milvus) |
| --- | --- | --- | --- |
| Scale fit (≤ ~5 M vectors) | Good with HNSW; half precision halves memory | Excellent | FAISS (library): fast, but persistence and filtering are hand-built. LanceDB: embedded, promising. Chroma: dev-oriented. Milvus: heavy |
| Filtered search (published only, court, year) | Works. HNSW + selective filters needs care (iterative scans or exact search on filtered subsets) **[PoC]** | Strong payload filtering | Varies |
| Transactions with publication state | **Yes** | No (separate service) | No |
| Ops | None extra | One service (single binary or container) | Varies |
| Licence | PostgreSQL licence | Apache 2.0 | MIT / Apache mostly |

**Recommendation: pgvector.**
- Store one embedding per passage, with the model ID and model-file hash, so that a model change triggers a re-embed generation and query/document embeddings never mix models.
- **Exit path:** Qdrant if PoC P1 shows filtered-HNSW latency or recall problems at projected scale. The embedding table is the source of truth, so migration is a re-index, not a re-embed.

## 8. Graph

| Criterion | PostgreSQL edge tables + recursive CTE | Apache AGE | Neo4j | Others (Memgraph, Kuzu) |
| --- | --- | --- | --- | --- |
| Fit to need (typed edges with evidence, verification state, temporal validity; neighbourhood and path queries; 10^5–10^6 edges) | **Good**: schema constraints, foreign keys to anchors, same transaction as publication | Cypher inside Postgres | Excellent query language and algorithms | — |
| Integrity with evidence and state axes | **Native** (FKs, CHECK constraints) | Partly (graph stored outside the relational schema) | Separate store; sync required | Separate |
| Ops | None extra | Extension; **support lags new Postgres majors [verify]** | One JVM service; separate backup | Varies |
| Licence | PostgreSQL | Apache 2.0 | Community: GPLv3 with feature limits (clustering, hot backup and fine-grained security are Enterprise, commercial). Enterprise: commercial | Memgraph: source-available licence (verify). Kuzu: upstream status changed in 2025 (verify maintenance) |

**Recommendation: relational edge tables with recursive CTEs.** The graph is an **evidence register with typed links**, not an analytics workload. Its legal value lies in the constraints: every edge has an anchor, a confidence class and a verification axis. Relational integrity enforces that best. Use NetworkX (already pinned) in offline tooling for analytics such as centrality and components. Visualise with **Cytoscape.js** (MIT) in the browser.

**Exit path:** Apache AGE if Cypher ergonomics become important. A Neo4j read replica built from the edge tables, if heavy graph algorithms are ever needed online, subject to D-02 on licence.

## 9. Local embedding and reranker models

**Constraints:**
- Fully local files, bundled with checksums.
- CPU inference; a modest GPU optional.
- Legal English with Indian military vocabulary (court martial, summary of evidence, Entitlement Rules, AFT, s.69).
- Some Devanagari.

No openly available sentence-embedding model is trained specifically on Indian military law. Indian legal-domain encoders exist (for example InLegalBERT, an MLM model), but they are **not retrieval-tuned sentence embedders** and would need fine-tuning on labelled pairs.

| Family (examples) | Size class | Licence (verify on model card) | Notes |
| --- | --- | --- | --- |
| BGE English (small / base / large) | 33M–335M | MIT | Strong general retrieval; base is a good CPU trade-off |
| E5 (base / large; multilingual-e5) | 110M–560M | MIT | Needs "query:/passage:" prefixes; the multilingual variant covers Devanagari |
| Snowflake Arctic-embed (S/M/L) | 33M–335M | Apache 2.0 | Retrieval-focused; good small models |
| nomic-embed-text | ~137M | Apache 2.0 | Long context; task prefixes |
| bge-m3 | ~568M | MIT | Multilingual, long input, dense+sparse; heavier on CPU |
| **Rerankers:** BGE reranker (base/large; v2-m3), mxbai-rerank, MS MARCO MiniLM cross-encoders | 22M–568M | MIT / Apache 2.0 | Rerank top 50–100; CPU latency is the constraint **[PoC]** |

**Runtime.**
- **ONNX Runtime** (already pinned in `requirements.txt`; MIT) with exported or quantised models avoids shipping PyTorch to the server.
- sentence-transformers is the fallback for evaluation.
- Set `HF_HUB_OFFLINE=1` and load only from the bundled model directory, whose hash is checked at startup.

**Recommendation.**
- Shortlist **one small and one base model each from BGE, E5 and Arctic-embed**, plus one multilingual model and two rerankers. Choose in **PoC P2** on the retrieval benchmark (recall@20, nDCG@10), CPU throughput (passages/sec for bulk embedding, ms/query) and memory.
- **Bulk document embeddings may be computed on the internet-connected build side** and shipped in the release bundle with the model hash. The offline server then needs only query-time embedding and embedding of Admin uploads.
- Fine-tuning on Mimamsa pairs is a later option. It needs a labelled training set kept separate from evaluation sets.

**Expected CPU throughput [PoC]:** a base-size model on a 16-core server is plausibly in the tens to low hundreds of passages per second. That would make a full re-embed of today's corpus an hours-scale job, not days. This must be measured.

## 10. Local LLM for drafting assistance (later phase, gated)

**Not in Cycle 13.** Introducing any generative model requires all of the following:
1. Legal Reviewer designation path confirmed (Document Studio §3.3).
2. Prompt-injection isolation tested: document text never acts as instructions; the model has no tools that mutate state.
3. Use limited to **drafting assistance and explanation over retrieved, cited passages**. No legal conclusions, no mandatory steps, no compliance verdicts.
4. Evaluation on a held-out drafting benchmark, reviewed independently.
5. The candidate banner and "not legal advice" labelling on every output.

| Option | Licence | Fit |
| --- | --- | --- |
| llama.cpp (GGUF, CPU or GPU) | MIT | **Recommended runtime when the time comes**: single binary, OpenAI-compatible server, works on CPU with small models and scales up with a GPU |
| vLLM | Apache 2.0 | Best throughput, needs a capable GPU |
| Ollama | MIT | Convenient packaging; less control. Avoid any auto-pull behaviour offline |
| Model families | Varies: some Qwen and Mistral sizes Apache 2.0; Phi MIT; Llama under a community licence with use restrictions; Gemma under its own terms | Prefer permissive licences (D-02). Quality on Indian legal English needs evaluation **[PoC, later]** |

**Hardware implication.** Useful drafting quality typically needs a GPU with substantial VRAM (order of 16–24 GB or more for mid-size models at reasonable speed) **[PoC]**. On CPU, only small models are practical. The owner should decide whether to provision a GPU at D-01, even though the LLM comes later.

## 11. OCR

| Criterion | Tesseract | PaddleOCR | Others |
| --- | --- | --- | --- |
| Status in project | **In use**: 944 scanned judgments (4,705 pages), English, 300 dpi, threshold 70 mean word confidence; `pipeline/ocr.py`; per-page cache | Not used | docTR (Apache 2.0, PyTorch). Surya (GPL code; model-weight terms restrict commercial use; verify). OCRmyPDF (MPL 2.0; wraps Tesseract to produce text-layer PDFs; uses Ghostscript (AGPL) for PDF/A output) |
| Quality on degraded scans and tables | Good on clean prints, weaker on noisy scans | Often stronger detection on difficult layouts **[PoC]** | — |
| Offline install, Windows/Linux | Easy (distro packages; Windows builds exist) | Heavier: PaddlePaddle framework; CPU works; Windows support exists but more fragile | — |
| Per-word boxes and confidence | Yes (TSV/hOCR) | Yes | — |
| Licence | Apache 2.0 | Apache 2.0 | — |

**Recommendation.**
- Keep **Tesseract** as the primary engine. It is proven in this corpus, light and portable.
- Store **per-word boxes and per-page confidence**. B5 needs the boxes to highlight hits on scanned pages without altering the original PDF.
- **[PoC P4]**: run PaddleOCR (and Prism, if D-10 confirms it is available offline under a known licence) on the pages below threshold and on a random sample of scanned pages. Compare word accuracy against a small hand-transcribed sample. Adopt it as a *second-pass engine for low-confidence pages* only if the gain is material.
- If text-layer PDFs are generated for viewing, they are **labelled derivatives**. The original bytes remain the cited source. Avoid Ghostscript-dependent PDF/A output unless D-02 accepts AGPL.
- **Prism OCR** has been an open question since the original brief. Treat it as unavailable until shown otherwise.

## 12. PDF viewer, frontend, packaging, auth and updates

### 12.1 PDF viewer: PDF.js

PDF.js is the only serious open-source, browser-native choice (Apache 2.0, Mozilla). Use `pdfjs-dist` with the worker bundled locally, no CDN.

- **Page anchors:** open at page N.
- **Highlighting:**
  - Native PDFs: find the passage text in the page's text layer (normalised fuzzy match).
  - Scans: draw overlay boxes from stored OCR word coordinates. **[PoC P3]**
- **Security:**
  - Set `isEvalSupported: false`. A 2024 PDF.js vulnerability (CVE-2024-4367) allowed script execution through crafted fonts when evaluation was enabled.
  - Keep PDF.js on the current patched release.
  - Disable PDF scripting.
  - Serve PDFs from the app origin with a strict Content-Security-Policy.
- **Wrapper:** React wrappers exist (for example react-pdf, MIT). Use one only if it does not hide the needed text-layer and annotation hooks.

### 12.2 Frontend: React + TypeScript (+ Vite)

| Option | For | Against |
| --- | --- | --- |
| **React + TypeScript** | Largest ecosystem for PDF viewers, graph views (Cytoscape.js, Sigma.js) and data tables (TanStack); easy to staff | npm supply-chain surface. A build step |
| Vue / Svelte + TS | Smaller bundles; pleasant | Smaller ecosystem for the specialised components |
| Django templates + HTMX | Fewest moving parts; one language | PDF viewer, graph explorer and Document Studio are rich client components; they would end up as JavaScript islands anyway |

**Recommendation: React + TypeScript + Vite**, a permissively licensed component library (for example Mantine or MUI core, both MIT; verify), TanStack Query and Table, and Cytoscape.js.

- **Air-gap rules:**
  - the build happens online from a hash-locked lockfile;
  - the output is static files served by the backend or proxy;
  - no runtime CDN, web fonts or analytics;
  - a CI check fails if the built bundle references external URLs.
- **Exit path:** HTMX for the simpler admin screens if the team prefers less JavaScript.

### 12.3 Packaging and deployment

| Option | For | Against |
| --- | --- | --- |
| **Docker Compose on a Linux host** (Docker Engine or Podman) | Reproducible images; process isolation for workers (no network, read-only mounts, resource limits); simple upgrade by image swap; Docker Engine on Linux and Podman are free and open source | Needs a Linux host. Images must be transferred offline |
| Linux VM under Hyper-V on a **Windows** server, running the same Compose stack | Windows estates keep Windows hosts; identical artefacts | VM administration; resource overhead |
| Docker Desktop on Windows | Familiar | **Subscription terms apply to larger organisations (verify for this deployment)**; not intended for Windows Server production; Linux containers depend on WSL2 |
| Native installers (MSI/DEB: Python runtime, PostgreSQL installer, Tesseract, services) | No container runtime | Highest maintenance: per-OS builds, dependency drift, weaker isolation; upgrades and rollbacks hand-built |

**Recommendation.** Ship **one Compose stack**: proxy, web/API, worker, PostgreSQL and an optional search sidecar.

- **Linux host preferred.** On Windows estates, run it in a **Hyper-V Linux VM** **[PoC P5]**.
- **Air-gapped transfer:** images are built online, scanned (SBOM and vulnerability scan), exported with `docker save`, checksummed and signed, then loaded offline. Optionally run a local registry (CNCF Distribution, Apache 2.0) on the LAN.
- **Native installers are a last-resort exit path**, not a plan.

### 12.4 Authentication

- **Local accounts:** Django auth with Argon2 password hashing, lockout, session expiry, and optional TOTP second factor (works offline; for example django-otp, verify licence).
- **LDAP/AD (optional, D-05):** django-auth-ldap (BSD) binds against the LAN directory. One AD group maps to Admin; every other admitted user is User. There are no further roles.
- **Enforcement:**
  - Every corpus-mutation and staging endpoint carries a server-side Admin check. Tests call the API directly as User.
  - Working-session objects carry an owner ID checked on every access, including downloads and job results.
- **Not built:** a Legal Reviewer function. It is a blocking open decision and fail-closed.

### 12.5 Snapshot update mechanism (HF → offline)

```
ONLINE BUILD SIDE                                  AIR-GAPPED LAN
HF dataset @ pinned revision ─┐
Track A IC-01 artefacts @ git ─┼─ build_release --check ─► release-YYYYMMDD-<hfrev>/
model bundle (hash) ──────────┤                             data/ (PDFs, text, meta, sections,
container images (hash) ──────┘                                    passages, embeddings, edges)
                                                            manifest.csv, schema_version
                                                            CHANGES.json, RELEASE.json
                                                            SHA256SUMS, SHA256SUMS.sig
                                     removable media ─────► importer:
                                                              1 verify signature (pinned public key)
                                                              2 sha256sum -c (every file)
                                                              3 schema compatibility check
                                                              4 load into NEW release generation
                                                              5 build/refresh indexes; smoke queries
                                                              6 atomic switch; keep N-1 for rollback
                                                              7 reconcile local Admin uploads (§9.1)
                                                              8 CHANGES.json → impact triggers
```

- **Signing.** Use a small, auditable tool such as minisign (ISC) or OpenSSL/GPG detached signatures, verified against a public key pinned at install. Key custody is owner decision D-05. A checksum alone proves integrity against corruption, not origin; the signature adds origin.
- **Eligibility filter at build.** The FOUO RAF 2000 copy and any access-marked or unsuitable item are excluded from app bundles by rule, whatever the HF dataset holds (ADR-0002 decision 7).
- **Incremental updates.** CHANGES.json lists the delta. The importer still verifies the *whole* bundle manifest. Deltas can ship only changed files plus a full manifest **[PoC P5]**.

### 12.6 Document storage and backup

- **Originals:** an immutable, content-addressed filesystem vault (`vault/sha256/ab/<hash>`). Workers mount it read-only, and every read can be re-verified.
- **Derivatives:** page images, OCR JSON and text-layer PDFs, under `derived/<sha256>/<pipeline_version>/`. They are disposable and rebuildable.
- **Backups:** PostgreSQL via pgBackRest or scheduled `pg_dump`; vault and local uploads via restic or rsync to rotated offline media. A restore drill is part of the B10 acceptance.
- **Object stores:** avoid them unless multi-node. MinIO's licence (AGPL) and community-edition changes make it a poor default; verify alternatives if ever needed.

## 13. Licensing summary (verify at selection, PoC P7)

| Component | Licence (as understood) | Concern |
| --- | --- | --- |
| PostgreSQL, pgvector | PostgreSQL licence | None |
| Django, django-auth-ldap | BSD | None |
| PDF.js, React, Cytoscape.js, Vite | Apache 2.0 / MIT | None |
| Tesseract, PaddleOCR, ONNX Runtime | Apache 2.0 / MIT | None |
| **PyMuPDF** (used across the existing pipeline) | **AGPL-3.0 or commercial (Artifex)** | Server-side use over a network raises AGPL obligations for the combined work. For an internal deployment this may be acceptable, but **owner decision D-02**. Permissive fallbacks: pypdfium2 (Apache/BSD), pdfminer.six and pdfplumber (MIT), both already pinned |
| Ghostscript (if pulled in by OCRmyPDF PDF/A) | AGPL or commercial | Avoid, or decide under D-02 |
| Neo4j Community | GPLv3 (Enterprise commercial) | Only if ever adopted |
| Meilisearch, Memgraph, some Postgres BM25 extensions | Mixed; some source-available or AGPL | Check before any adoption |
| Redis | Licence changed in 2024 (verify current) | Use Valkey if a cache is ever needed |
| Docker Desktop | Subscription terms for larger organisations | Use Docker Engine or Podman on Linux |
| Embedding, reranker and LLM weights | Per model card (MIT, Apache 2.0, community licences) | Record each model's licence in the model bundle |

## 14. Security posture (baseline for the first deliverable)

- **Network:**
  - no egress from any container;
  - inter-service network internal only;
  - the proxy is the only LAN-exposed port;
  - TLS with an internal CA.
- **Parsing:** PDF, DOCX and image parsing and OCR run in the worker container as a non-root user, with no network, a read-only vault, CPU, memory and time limits, and a temporary scratch directory wiped per job. Upload checks: size, magic-byte type and page-count limits.
- **Integrity:** sha256 on write and on read for cited originals; signed release bundles.
- **Audit:** metadata-only, append-only event log of logins and Admin actions. Working-document content is never logged.
- **Supply chain:**
  - hash-locked Python and npm dependencies;
  - SBOM per image;
  - vulnerability scan online before transfer;
  - a pinned base image updated each release.
- **Later (with an LLM):** retrieved text passed as quoted data, never as instructions; no tool access that mutates state; output filters for the banner and labelling.

## 15. Risks and exit paths

| Risk | Signal | Exit path |
| --- | --- | --- |
| PostgreSQL FTS ranking is too weak | P1: BM25 gain ≥5 points recall@20 | Tantivy derived index with a generation check; or an approved BM25 extension |
| pgvector filtered-search latency or recall at 20 GB | P1 at projected scale | Qdrant; re-index from the embedding table |
| Embedding quality on legal vocabulary | P2: low recall on section and term queries | Hybrid weighting toward lexical; reranker; later fine-tune on separate labelled pairs |
| OCR quality on degraded scans | P4 | PaddleOCR second pass; human review list |
| Windows-only estate | D-01 | Hyper-V Linux VM (P5); native installers last |
| AGPL concerns | P7 / D-02 | Replace PyMuPDF in the app path with pypdfium2/pdfminer; keep PyMuPDF only in offline audit tooling if accepted there |
| Django coupling | Domain code leaking into views and models | `mimamsa_core` boundary enforced by import-linter rules in CI |
| Queue library immaturity | P6 | `SKIP LOCKED` table; Celery + Valkey |
| Small team cannot run many services | Service count creeping above about 5 | One-database principle; any new service needs an ADR with a measured need |

## 16. Proofs of concept (Cycle 13, B0)

| PoC | Question | Method | Go criterion (proposed) |
| --- | --- | --- | --- |
| P1 Retrieval | Is PostgreSQL FTS + pgvector hybrid good enough? | Benchmark: fresh dev queries plus the held-out 50 golden questions; double-coded relevance; compare ts_rank_cd, Tantivy BM25, vector, and hybrids (RRF) | Hybrid recall@20 on held-out ≥ best single method. FTS within 5 points of BM25, or adopt Tantivy. p95 < 1 s at 10 concurrent queries on reference hardware |
| P2 Models | Which embedding and reranker models? | Shortlist in §9; ONNX on CPU | Best recall/latency trade-off; bulk embedding of the full corpus ≤ one overnight run; query embedding < 100 ms |
| P3 PDF anchors | Can we open at page and highlight reliably? | 100 hits, native and scanned | Page correct ≥98%; native highlight ≥90%; scanned-overlay feasibility shown |
| P4 OCR | Is a second engine worth it? | Low-confidence pages plus a random scanned sample; small hand transcription | Material word-accuracy gain at acceptable CPU cost |
| P5 Air-gapped install/update | Can a clean, network-disabled VM install, update and roll back from bundles? | Linux VM; Hyper-V Linux VM if D-01 says Windows | All B10 acceptance steps pass with networking off |
| P6 Job queue | Does a Postgres-backed queue handle bulk import and retries? | Import 16k files with injected failures and a kill/restart | No lost or duplicated jobs; resumable |
| P7 Licences | Is the dependency tree acceptable? | SBOM + licence scan + manual review of flagged items | No unresolved copyleft item without an owner decision |

## 17. Phased build order

1. **Foundation (GB1 → M-B1, the minimal first deliverable):**
   - Compose stack, PostgreSQL schema with separate status axes, content-addressed vault;
   - release importer with signature and checksum verification from a **pinned HF revision**;
   - passage extraction and OCR flags;
   - hybrid search;
   - PDF.js at page with highlight;
   - provenance panel;
   - candidate banner;
   - local Admin/User auth;
   - **one Admin upload → stage → publish → search → withdraw round trip**;
   - backup and restore;
   - network-denied test suite.
2. **Research depth (M-B2):** judgment page with per-field status chips and labelled outcome candidates; Act and section viewer; graph exploration of IC-01 candidate edges; Document Studio working-session foundation (isolation, view, export; no rules); release N→N+1 update and rollback.
3. **Hardening and operations:** LDAP/AD option, TOTP, audit review screens, restore drills, performance at simulated 20 GB, incremental bundles.
4. **Later, each behind its own gate:** reranker tuning or fine-tuned embeddings; Legal Reviewer workspace (after the designation is confirmed); template-based drafting (after T2 approvals exist); local LLM drafting assistance (after the §10 gate).

**The minimal first deliverable** is exactly item 1. A Linux VM with no network installs from signed bundles. It imports the full corpus at a pinned HF revision, verifying every checksum. Any User can then search judgments and Acts and open the original PDF at the right page with the hit highlighted. Every page carries the candidate-data banner and a provenance trail back to the HF revision. Only an Admin can upload, publish and withdraw a document, and withdrawal removes it from search immediately.

## 18. Open questions for the owner (cross-referenced to the plan's §11)

- D-01: server OS and hardware, GPU or not. Planning baseline: 16 cores, 64 GB RAM, 1 TB SSD (vault, derivatives, database, two release generations, local backups); optional GPU sized later for the LLM.
- D-02: licence posture, especially PyMuPDF (AGPL) in the server path.
- D-05: local accounts vs LDAP/AD; custody of the release-signing key.
- D-06: application code in this repository or a separate one.
- D-10: whether the Prism OCR pipeline exists as an offline, licensable module.
