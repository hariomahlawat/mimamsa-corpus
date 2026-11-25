# ADR-0005: Offline application stack (Windows-native)

- **Status: PROPOSED.** Options and decision criteria only. The decision row in §6 is completed after the proof-of-concept evidence P1–P9 (workstream B-PoC, branch `claude/c13-b-poc`) has been independently reviewed, and the owner accepts it at gate **GB1**.
- **Date:** 2026-11-25 (Cycle 13, workstream B0)
- **Supersedes:** the planned "ADR-0005-OFFLINE_APP_STACK" named in the Cycle 13 plan §5 B0. That draft assumed Docker Compose on Linux or a Hyper-V Linux VM; the owner's Cycle 13 directive replaces that assumption.
- **Revised 2026-11-25 (R2):** owner direction *Windows-first, not Windows-only* (portable core, replaceable OS adapters) and reconciliation with the future intelligence architecture in PR #53 (branch `docs/mimamsa-intelligence-architecture-2026-11-25` @ `6a0ae735`); see [reconciliation](../INTELLIGENCE_ARCHITECTURE_RECONCILIATION_C13.md). Still PROPOSED.
- **Related:** [Technology assessment (revised)](../../planning/OFFLINE_APP_TECHNOLOGY_ASSESSMENT.md), [Security and deployment architecture](../SECURITY_AND_DEPLOYMENT_ARCHITECTURE.md), [Capability traceability matrix](../CAPABILITY_TRACEABILITY_MATRIX.md), [Data contract v1](../../../app/contract/README.md), ADR-0001 to ADR-0004.

## 1. Context

The owner's Cycle 13 directive fixes these constraints:

| # | Constraint |
| --- | --- |
| C-1 | **Windows-native production**: IIS or a native Windows Service; browsers on an offline LAN. Do **not** assume Docker, WSL, Hyper-V or a Linux VM |
| C-2 | Provisional reference hardware: 16 cores, 64 GB RAM, 1 TB SSD. GPU optional, never mandatory |
| C-3 | Start as a **modular monolith with isolated workers** |
| C-4 | Two roles, Admin and User. Legal Reviewer is a designation on an existing account, inactive until appointed. Ownership checks are enforced in the backend |
| C-5 | No legal reasoning or compliance logic in Cycle 13 |
| C-6 | Zero runtime internet dependency; signed offline snapshot updates; offline Windows installer |
| C-7 | Keep the existing Python corpus pipeline; prefer permissively licensed dependencies (PyMuPDF is AGPL) |
| C-8 | **Windows-first, not Windows-only** (owner, 2026-11-25): native Windows is the primary development, deployment and acceptance target; the application core stays platform-independent behind replaceable OS-specific infrastructure adapters. No Linux production support is claimed in Cycle 13. Do not trade functionality, accuracy or UX for speculative portability |
| C-9 | The foundation must accept the future intelligence capabilities (hybrid RAG, legal GraphRAG, deterministic legal engine, bounded agents; PR #53) later **without fundamental redevelopment**. None of them is implemented now |

The directive names preferred candidates, **to be evaluated, not presumed**: ASP.NET Core LTS compared with Django; React + TypeScript; PostgreSQL with FTS (or a benchmarked better alternative), pgvector and a relational graph; PDF.js; Python workers; Windows Services; Tesseract, PaddleOCR or alternatives; local ONNX embeddings; SignalR; local accounts with optional AD; an offline Windows installer; signed snapshot updates.

## 2. Decision drivers (weighted criteria)

Weights are proposed by B0 for owner confirmation. Each option is scored 1–5 per criterion **from PoC measurements where a PoC exists**, otherwise from documented evidence, and the source of each score is cited in §6.

| ID | Criterion | Weight | Evidence |
| --- | --- | --- | --- |
| K1 | Runs natively on Windows Server as IIS site or Windows Service, with clean start/stop/recovery and service identity | 15 | P1, P6 |
| K2 | Security built in: authentication, session, CSRF, password hashing, AD integration, server-side authorisation patterns, patch cadence | 15 | P1, P7, vendor security policy |
| K3 | Search and retrieval quality and latency on this corpus (legal identifiers such as "s.69", "rule 22(3)(a)") | 15 | P2, P3 |
| K4 | Withdrawal and publication consistency (one transaction across text, vectors and graph) | 10 | P2 |
| K5 | Reuse of the Python pipeline and Track A tools without re-implementation | 10 | P5 |
| K6 | Offline install, signed update, rollback and restore on a clean Windows host with networking off | 10 | P6, P8 |
| K7 | Licence posture (permissive preferred; any copyleft item needs owner decision D-02) | 10 | P7 |
| K8 | Operability by a small team: number of services, backup and restore, monitoring with Windows tools | 10 | P1, P6, P8 |
| K9 | Long-term support window and staffing availability | 5 | vendor lifecycle pages |
| K10 | **Protected delivery and portability fit**: one process can own protected egress (single delivery gateway, bounded range responses, no static/sendfile/proxy buffering of protected bytes; PR #53 Serving §6 T0), and the framework runs on Windows now and on Linux later without changing the core | 10 | P1, P4 (R2-N01), P6 |

Weights sum to 110 after adding K10; the scoring sheet normalises to 100. K10 can disqualify a hosting mode: a topology that cannot keep protected routes inside a proven delivery adapter (for example IIS + ARR reverse proxy in front of Django, unless its buffering is proven) is acceptable only with those routes disabled, which fails functionality.

## 3. Options

### 3.1 Web/API host (the main choice)

| Option | Shape | Strengths | Risks to measure |
| --- | --- | --- | --- |
| **A. ASP.NET Core (LTS)** + Python workers | Kestrel behind IIS (ASP.NET Core Module, in-process or out-of-process) or Kestrel as a Windows Service. Workers are separate Python processes under their own service identities, fed from a PostgreSQL job table | First-class on Windows: IIS integration, Windows Services hosting, Windows authentication/Negotiate for AD, Data Protection API, Event Log. SignalR is native. Strong typing end to end with generated TypeScript clients | Two languages (C# web, Python workers). Domain logic split must be disciplined. The team's C# capacity is unknown (owner question Q-3) |
| **B. Django (LTS)** + Python workers | Django under a Windows-native ASGI/WSGI server (e.g. Waitress or Uvicorn as a Windows Service), with IIS as reverse proxy (URL Rewrite + ARR) or HttpPlatformHandler. Same language as workers | One language with the pipeline. Mature auth, CSRF, admin, migrations. django-auth-ldap for AD | Production Python web serving on Windows is less trodden than on Linux: process model, worker recycling, service wrappers and IIS reverse-proxy behaviour must be proven (P1). Real-time push needs Django Channels or SSE instead of SignalR |
| C. FastAPI | As B | Typing, async | More security glue to write; not shortlisted by the directive. Kept as exit path only |

### 3.2 Hosting model on Windows

| Option | Notes |
| --- | --- |
| **IIS** as front end (TLS termination, static files, request limits, Windows auth), app behind it | Familiar to Windows administrators; certificate binding in IIS; request filtering. Adds IIS configuration to the installer |
| **Native Windows Service** for the app (Kestrel or Python ASGI) with its own TLS | Fewer moving parts; no IIS role needed. TLS, request limits and static-file serving are configured in the app |
| Workers | Always native Windows Services (one per worker class), separate low-privilege identities, no inbound ports |

### 3.3 Data, search and graph

| Option | Notes |
| --- | --- |
| **PostgreSQL** (Windows build, current supported major) with built-in FTS, **pgvector** and relational edge tables | One database, one backup, one transaction boundary (K4). pgvector on Windows must be built or obtained as a signed binary for the exact PostgreSQL major (P2, P6) |
| PostgreSQL + a BM25 index outside the database (e.g. Tantivy embedded in a worker) | Adopt only if P2 shows a material recall gain (proposed: at least 5 points recall@20 on held-out queries) and a generation-consistency check is in place |
| SQL Server (Express/Standard) full-text + vector | Windows-native; licence cost and edition limits (Express database size cap); vector support version-dependent. Listed for completeness; not preferred by the directive |
| OpenSearch | JVM service; heavy for a 2–20 GB corpus. Exit path only |

### 3.4 Other layers (expected to be uncontroversial; still verified)

| Layer | Candidate | Verify in |
| --- | --- | --- |
| Frontend | React + TypeScript, built online from a hash-locked lockfile, served as static files | P7 (licences), bundle external-URL check |
| PDF viewer | PDF.js (`pdfjs-dist`), `isEvalSupported:false`, scripting off | P4 |
| Embeddings | Local ONNX Runtime on CPU; model chosen by measurement | P3 |
| OCR | Tesseract (Windows build) primary; PaddleOCR or alternatives as second pass if measured gain (quality: Track A1) | P4, P6 |
| Text extraction in the app path | pypdfium2 (Apache/BSD) or pdfminer.six/pdfplumber (MIT); PyMuPDF (AGPL) only in offline audit tooling unless D-02 accepts it | P7 |
| Real-time updates | SignalR (option A) or Server-Sent Events (option B) for job progress only | P1 |
| Auth | Local accounts (Argon2id or PBKDF2 per framework default), optional AD (Negotiate/LDAP) mapping one group to Admin | P1, P7 |
| Packaging | Offline Windows installer (MSI via WiX Toolset, or an equivalent) bundling runtime, PostgreSQL, extensions, models, OCR, services and firewall rules | P6 |
| Updates | Signed snapshot bundles (Ed25519 over `SHA256SUMS`), import to a new generation, atomic switch, rollback | P8; contract tests in `app/contract` |

## 4. Architecture common to every option

- **Modular monolith** with internal modules: `catalogue` (documents, copies, provenance), `search`, `viewer`, `graph`, `research` (workspaces, notes), `studio` (working sessions, no rules), `admin` (ingestion, publication, releases), `identity` (accounts, roles, designation registry), `audit`.
- **Isolated workers** as separate Windows Services: `ingest-parse` (file sniffing, text extraction), `ingest-ocr`, `embed`, `index`, `release-import`. Workers have no inbound ports, no outbound network, read-only access to the vault, write access only to their scratch and derivative folders.
- **Shared contract.** All corpus data enters through `app/contract` v1 bundles; the app never writes to authoritative records. The nine data layers (contract README §3.1) map to separate stores whatever stack is chosen.
- **Signed everything.** Installer and payloads Authenticode-signed (mandatory); data bundles and exclusion updates Ed25519-signed by owner-held keys under an owner-controlled trust list.
- **Gates off by configuration and by data.** The commander assistant and any legal-rule feature are architected (routes, module boundaries, data model hooks) but **disabled**; enabling requires the reasoning-feature gate (Cycle 13 plan §7), which cannot open while AUTH-LEDGER is at version 0 and no Legal Reviewer is appointed.

## 4a. Windows-first portable core and adapter boundaries

**Principle.** One platform-independent application core (domain modules, search/graph/catalogue services, contract validation, evidence semantics, UI and API, PostgreSQL schema, corpus formats). Host-specific behaviour sits behind a small number of narrow infrastructure interfaces with a Windows adapter now. A Linux adapter is a later, separately accepted delivery. Dependencies point inward: the core never imports an OS-specific module. Portable libraries are the default; an OS-specific dependency needs a recorded benefit and its seam. No abstraction is added to ordinary portable code without need (owner directive 3).

| # | Adapter boundary (interface) | Windows adapter (primary, C13) | What the core sees | Linux later (not claimed) |
| --- | --- | --- | --- | --- |
| AD-1 | **Service host and lifecycle** | Windows Service (SCM recovery) or IIS-hosted app per P1 | start/stop/health hooks, configuration object | systemd unit |
| AD-2 | **Filesystem layout and path policy** | `D:\Mimamsa\…` roots from configuration; NTFS case-insensitive rules | logical store roots; contract-relative POSIX paths validated by `app/contract/mimamsa_contract/paths.py` (already rejects Windows and POSIX hazards on every OS) | configured roots; same validator |
| AD-3 | **Access control on stores** | NTFS ACLs set by installer (`icacls`), virtual service accounts | "store X is read-only for this process" assertions checked at start | POSIX ownership/ACLs |
| AD-4 | **Process isolation for untrusted parsing** | child process in a Job Object (memory, CPU, time, kill-on-close); restricted token/AppContainer later | `run_isolated(job, limits) -> result | failure` | cgroups/namespaces |
| AD-5 | **Network egress policy** | Windows Firewall outbound block per service SID | assertion only (core makes no outbound calls) | nftables/systemd sandboxing |
| AD-6 | **Protected delivery transport** (PR #53 Serving §6) | in-process gateway adapter on the selected host (T0: app service, no proxy on protected routes), bounded byte slices, credit ledger | `try_accept(artifact, offset, n, state)` and polling progress | equivalent adapter with its own proof |
| AD-7 | **Durable policy state / witness store** | protected folder outside DB and release generations; flush semantics proven on NTFS in P8 | `ExclusionStore`-style acceptance record (`app/contract/mimamsa_contract/exclusions.py`) | same contract, separate proof |
| AD-8 | **Secrets and key store** | DPAPI/LocalMachine certificate store; trust list from signed installer | key handles, trust list object | file/keyring with OS protection |
| AD-9 | **OCR, embedding and (later) inference runtimes** | pinned Windows builds (Tesseract, ONNX Runtime; llama.cpp later) | typed capability interfaces (ocr, embed, rerank) with model/file hashes | pinned Linux builds |
| AD-10 | **Installer, update and backup tooling** | Authenticode-signed MSI, Task Scheduler, robocopy/VSS, BitLocker | none (outside the core) | separate signed packages |

Rules: release bundles and the contract never contain drive letters, absolute paths or OS separators; database migration between hosts is by logical backup and signed bundles, not copying data directories or witness state; Windows measurements are never reused as evidence for another OS. The existing Linux CI already runs the portable contract and design tests; a Windows runner is added when the B1 code exists (P6), not in B0.

## 4b. Hooks reserved now for the later intelligence layer (no implementation)

- **Typed read services callable without an LLM:** search, catalogue, viewer, graph and evidence resolution are ordinary B1/B3 services; a later broker calls them, never SQL or the filesystem directly.
- **Stable evidence keys:** PageKey/SpanKey with exact derivative binding (`app/contract/mimamsa_contract/evidence.py`, contract `page_anchor.pipeline_name` / `derivative_text_sha256`).
- **Candidate vs verified separation:** already structural in contract v1 (candidate status, capability restriction, resolvable review and approval records, legal axes closed at AUTH-LEDGER v0). A future engine or GraphRAG consumes these without reinterpretation.
- **Reserved site-only namespaces:** bundle paths `agent/`, `private/`, `workflows/`, `claims/`, `policy/` and record kinds for workflows, private drafts, final claims, output authorisations, serving epochs, policy witnesses and rule packs are rejected in exchange, so private agent writes can never enter the shared corpus by bundle.
- **Single delivery gateway and serving fence:** every protected response goes through one gateway that checks current publication/exclusion state at hand-off (security architecture §7.4).
- **Execution domains:** PUBLISHED_RESEARCH, STAGED_ADMIN_PROCESSING and PRIVATE_WORKING_SESSION map to the existing layers 7, staging and 9; they are not roles.

## 5. Consequences (to be confirmed with the decision)

- Option A means a C# web layer and Python workers; a contract-first API (OpenAPI) and the data contract keep them aligned.
- Option B means one language but a less common Windows production profile, which P1 and P6 must de-risk.
- Either way, the Linux/Docker packaging in the earlier assessment is withdrawn for production. Containers may still be used **on developer machines only**, never as a production dependency.

## 6. Evidence table (to be completed after P1–P9)

Status values: `PENDING` (no evidence yet), `MEASURED` (raw measurements committed), `REVIEWED` (independent reviewer confirmed). B0 has **not** measured anything below; every row is pending.

| PoC (directive) | Question | Go criterion (proposed by B0) | Evidence location | Result | Status |
| --- | --- | --- | --- | --- | --- |
| P1 Windows hosting | ASP.NET Core vs Django under native Windows hosting: install, service lifecycle, concurrency, database integration, process recovery | Both hosting modes install and recover unattended; metadata p95 < 300 ms at 25 users | `app/poc/p1_hosting/` | _to fill_ | PENDING |
| P2 Search and retrieval | PostgreSQL FTS, BM25-class engines, vector, hybrid: Recall@K, Precision@K, MRR, nDCG, exact citation retrieval, abbreviation handling, latency, concurrency | Search p95 < 1 s at 10 concurrent queries on reference hardware (16 cores, 64 GB, 1 TB SSD) without sacrificing accuracy; hybrid Recall@20 ≥ best single method; sized for ~20 GB | `app/poc/p2_search/` | _to fill_ | PENDING |
| P3 Local embeddings | BGE, E5, Arctic and others: quality, CPU latency, memory, throughput, licence | Query embedding < 100 ms; full corpus overnight on CPU; permissive licence | `app/poc/p3_embeddings/` | _to fill_ | PENDING |
| P4 Document processing and PDF navigation | Native, scanned, garbled, bilingual PDFs; page coordinates; highlighting; OCR boxes; large documents; pypdfium2 / pdfminer.six / pdfplumber as PyMuPDF alternatives | Page ≥ 98%; native highlight ≥ 90%; scanned overlay shown; permissive extractor adequate | `app/poc/p4_pdf/` | _to fill_ | PENDING |
| P5 Background processing | Durable queues, idempotency, retries, recovery, termination/restart, resumability, progress, resource limits, untrusted-parser isolation | No lost or duplicated jobs over a 16k import with kills; limits enforced; parser crash contained | `app/poc/p5_jobs/` | _to fill_ | PENDING |
| P6 Offline Windows installation | Clean Windows machine, no internet; runtimes, pgvector, Python libraries, frontend assets, OCR and embedding models; reproducible | Offline install succeeds; rebuild reproduces identical hashes | `app/poc/p6_installer/` | _to fill_ | PENDING |
| P7 Security and licence review | Dependency inventory, SBOM, licences from actual versions and model artefacts, parser isolation, vulnerabilities | No unresolved copyleft without D-02; no unmitigated high/critical vulnerability; threat tests pass | `app/poc/p7_sbom/` | _to fill_ | PENDING |
| P8 Offline update and restoration | Signed snapshot, checksums, DB and document updates, atomic activation, rollback, backup, full restore | Tampered bundle rejected unchanged; N→N+1, rollback and full restore pass offline | `app/poc/p8_update/` | _to fill_ | PENDING |
| P9 UI/UX functional prototype | Real research workflows on actual data: rendering, efficiency, hierarchy, responsiveness, readability, failure states | `app/design` 10-task walkthrough passes at the four target viewports | `app/poc/p9_ui/` | _to fill_ | PENDING |

PoC keys and scopes are the directive's (confirmed by the coordinator 2026-11-25). Evidence folder names for P6, P8 and P9 are placeholders until B-PoC commits them.

### Scoring sheet (to fill)

| Criterion (weight) | Option A ASP.NET Core | Option B Django | Source |
| --- | --- | --- | --- |
| K1 (15) | _ | _ | P1, P6 |
| K2 (15) | _ | _ | P1, P7 |
| K3 (15) | _ | _ | P2, P3 (same for both; database-bound) |
| K4 (10) | _ | _ | P2 |
| K5 (10) | _ | _ | P5 |
| K6 (10) | _ | _ | P6, P8 |
| K7 (10) | _ | _ | P7 |
| K8 (10) | _ | _ | P1, P6, P8 |
| K9 (5) | _ | _ | lifecycle pages |
| K10 (10) | _ | _ | P1, P4 (R2-N01), P6 |
| **Weighted total** | _ | _ | |

## 7. Decision

_Not yet taken._ To be written after §6 is complete: chosen web host, hosting mode, search configuration, OCR engine(s), embedding model, installer technology; reasons; risks; exit paths; owner acceptance (GB1) with date.

## 8. Exit paths (kept whatever is chosen)

- Domain logic in framework-independent modules with explicit SQL or thin repositories, so the HTTP shell can be replaced.
- Engine-neutral release bundles (JSONL + originals), so the database or search engine can change without changing Track A outputs.
- Embeddings stored with model id and model-file hash; a model change is a re-embed generation, never a mix.
