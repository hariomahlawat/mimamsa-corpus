# Mimamsa offline application: technology assessment (Windows-native revision)

- **Recorded:** 2026-11-24. **Revised:** 2026-11-25 (Cycle 13 workstream B0) to apply the owner's Cycle 13 directive.
- **Status:** Assessment for owner review and input to [ADR-0005](../architecture/decisions/ADR-0005-APPLICATION-STACK.md) (status PROPOSED). It is not an implementation authorisation. Claims marked **[PoC Pn]** need proof-of-concept evidence from workstream B-PoC (branch `claude/c13-b-poc`) before anyone relies on them.
- **Scope:** the runtime application on an air-gapped Windows LAN, and the update path from Hugging Face to that LAN. The crawler and audit tooling stay as they are.
- **Companions:** [CYCLE13_EXECUTION_PLAN.md](CYCLE13_EXECUTION_PLAN.md), [Security and deployment architecture](../architecture/SECURITY_AND_DEPLOYMENT_ARCHITECTURE.md), [Capability traceability matrix](../architecture/CAPABILITY_TRACEABILITY_MATRIX.md), [data contract v1](../../app/contract/README.md), [UI/UX specification](../../app/design/README.md).

## 0. What this revision changes

| Earlier position (2026-11-24) | Status | Replacement |
| --- | --- | --- |
| Packaging: Docker Compose on a Linux host; on Windows estates a Hyper-V Linux VM | **SUPERSEDED** by the directive | Native Windows: IIS or Windows Services; offline Windows installer; no Docker, WSL, Hyper-V or Linux VM in production (§12) |
| Backend recommendation: Django, decided on Linux-centric grounds | **REOPENED** | ASP.NET Core LTS compared with Django on Windows-specific criteria; decision after P1/P8/P9 (§4) |
| Worker isolation via containers (no network, read-only mounts, cgroups limits) | **SUPERSEDED** | Separate Windows Services with low-privilege virtual accounts, NTFS ACLs, Windows Firewall rules, Job Objects for CPU/memory/time limits (§5, Security architecture §3–4) |
| Reverse proxy Caddy or nginx | **SUPERSEDED** | IIS (with ASP.NET Core Module or URL Rewrite/ARR) or the app's own TLS endpoint as a Windows Service (§4.2) |
| Real-time: not specified | **ADDED** | SignalR (if ASP.NET Core) or Server-Sent Events (if Django), for job progress only |
| Auth: Django auth + django-auth-ldap | **GENERALISED** | Local accounts plus optional AD, under either framework (§11) |
| PoCs P1–P7 | **RENUMBERED** to P1–P9 aligned with B-PoC (§16) | |
| Hardware baseline as planning assumption under D-01 | **CONFIRMED PROVISIONALLY** by the directive | 16 cores, 64 GB, 1 TB SSD; GPU optional, never mandatory |

Everything not listed (one-database principle, transactional withdrawal, content-addressed vault, signed bundles, FOUO exclusion, no LLM in Cycle 13) is retained.

## 1. Requirements the stack must meet

| ID | Requirement | Source |
| --- | --- | --- |
| T-01 | **Zero runtime internet dependency**: no calls for search, OCR, embeddings, models, fonts, telemetry, licence checks, certificate revocation fetches or updates. Updates arrive only as signed, checksummed snapshot bundles | PR-12; Architecture §9; directive |
| T-02 | Corpus ~2 GB / ~16k files today (HF head `3864faf3`; 4,121 distinct source copies; 4,277 judicial records), growing to ~20 GB. Mostly English, some Devanagari. Many scans | C12 report; HF verification |
| T-03 | PDF rendering of the **original bytes** with page anchors and hit highlighting, native and scanned | PR-06; Architecture §10 |
| T-04 | Hybrid search: BM25-class lexical plus local vectors, filters, exact handling of section and rule numbers | PR-01; Architecture §8 |
| T-05 | Graph of instruments, provisions, judgments and proceedings with typed, anchored edges and per-edge verification state | PR-08; Architecture §5 |
| T-06 | Exactly two roles (Admin, User); Legal Reviewer a designation, inactive until appointed; server-side authorisation and ownership checks | ADR-0002; ADR-0003; directive |
| T-07 | Withdrawal never leaks: removed from every index, embedding store, graph view and cache | ADR-0002 d.7; Ingestion §7 |
| T-08 | Small operations team: few services, Windows-standard administration, simple backup and restore | Directive |
| T-09 | **Windows-native production** (Windows Server; IIS or Windows Services); browser clients on the LAN | Directive (replaces "Windows or Linux") |
| T-10 | Security baseline: parser isolation, integrity hashes, metadata-only audit, backups, prompt-injection isolation (for later LLM use) | Architecture §11 |
| T-11 | Licence-clean for an internal government deployment; permissive preferred; no single vendor or model lock-in | Directive; Scenario engine §9 |
| T-12 | Offline OCR and embeddings on CPU; GPU optional, never mandatory | Directive; PR-12 |
| T-13 | Modular monolith with isolated workers; keep the existing Python corpus pipeline | Directive |
| T-14 | Restricted material (register `config/restricted_material.json`, RM-001 = FOUO RAF 2000 copy and derivatives) never enters any bundle, index, embedding or external call | Directive; ADR-0002 d.7 |

## 2. Sizing (estimates; to be confirmed in P2/P3)

| Quantity | Today (~2 GB) | At 20 GB | Basis |
| --- | --- | --- | --- |
| Extracted text | a few hundred MB | a few GB | Text is a small fraction of PDF bytes |
| Passages (~300 tokens) | ~0.2–0.5 M | ~2–5 M | ~4k judgments × tens of pages × a few passages per page, plus statutes |
| Vectors at 768 dims (float32 / half) | ~0.6–1.5 GB / half | ~6–15 GB / half | 3 KB per float32 vector |
| Graph edges | 10^4–10^5 (C11: 11,076 statute links, 2,595 treatment candidates) | 10^5–10^6 | Citation extraction growth |
| Concurrent users | tens | tens to low hundreds | Assumption; confirm with owner |
| Disk (1 TB) | vault ~2 GB ×(1 + derivatives ~2–3×) + DB with indexes + two release generations + local backups | ~20 GB vault → ~150–250 GB total with two generations and backups | Estimate; fits 1 TB with headroom |

**Conclusion:** a single well-provisioned Windows server handles this workload. A distributed search cluster is not justified.

## 3. Candidates at a glance

Every row is a **candidate**. The decision is ADR-0005 after the PoCs.

| Layer | Primary candidate | Compared against / exit path | Evidence |
| --- | --- | --- | --- |
| Web/API | **ASP.NET Core LTS** or **Django LTS** (head-to-head) | FastAPI (exit only) | P1, P8, P9 |
| Hosting | IIS front end, or app as a Windows Service with its own TLS | — | P1, P8 |
| Workers | Python processes as **Windows Services**, PostgreSQL-backed job table (`SKIP LOCKED`) | A Python queue library, if P5 shows one is mature on Windows | P5 |
| Database | **PostgreSQL** (Windows build) | SQL Server (licence/edition limits) | P2, P8 |
| Lexical search | PostgreSQL FTS at passage level with legal-aware configuration | BM25 index (e.g. Tantivy) as a derived, rebuildable index if P2 shows ≥5 pts recall@20 gain | P2 |
| Vectors | **pgvector** (HNSW, half precision) | Qdrant (Windows binary) | P2, P8 |
| Graph | Relational edge tables + recursive CTEs | Apache AGE (Windows build availability uncertain) | P2 |
| Embeddings | Local **ONNX Runtime** on CPU; BGE / E5 / Arctic-embed class model | Multilingual variant if Devanagari recall matters | P3 |
| OCR | **Tesseract** (Windows build) | PaddleOCR or docTR as second pass | P6 |
| PDF text (app path) | **pypdfium2** / pdfminer.six / pdfplumber (permissive) | PyMuPDF (AGPL) only if D-02 accepts | P7 |
| PDF viewer | **PDF.js** | — | P4 |
| Frontend | **React + TypeScript**, built online, static files | — | P7 |
| Real-time | **SignalR** (ASP.NET) or **SSE** (Django) | Polling | P1 |
| Auth | Local accounts + optional AD (Negotiate or LDAPS) | — | P9 |
| Installer | Offline **MSI** (WiX Toolset, MS-RL; verify) or equivalent bootstrapper | Scripted PowerShell installer (fallback) | P8 |
| Updates | Ed25519-signed snapshot bundles, contract v1 | — | P8; `app/contract` tests |
| Storage | Content-addressed NTFS vault `vault\sha256\ab\<hash>` | — | P8 |

## 4. Web/API layer: ASP.NET Core vs Django on Windows

### 4.1 Comparison

| Criterion | ASP.NET Core (LTS) | Django (LTS) |
| --- | --- | --- |
| Windows production hosting | **Native**: ASP.NET Core Module for IIS (in-process or out-of-process); `UseWindowsService()` hosting; Event Log logging; Data Protection keys can be protected with DPAPI | Works, but no first-party Windows server. Options: Waitress (pure Python WSGI) or Uvicorn/Hypercorn (ASGI) wrapped as a Windows Service (pywin32 service or a service wrapper), behind IIS URL Rewrite + ARR or HttpPlatformHandler **[PoC P1]** |
| AD integration | Negotiate/Kerberos and NTLM built in; LDAP via `System.DirectoryServices.Protocols` | django-auth-ldap (needs python-ldap; Windows wheels availability to verify) or ldap3 (pure Python) **[PoC P9]** |
| Auth, sessions, CSRF, password hashing | ASP.NET Core Identity: PBKDF2 by default (iterations configurable), lockout, antiforgery tokens, cookie auth | Built in and long audited; Argon2 via `argon2-cffi`; CSRF middleware; lockout via a maintained package |
| Server-side authorisation | Policy-based authorisation (`[Authorize(Policy=…)]`), resource-based handlers for ownership | Permission checks and decorators; object-level checks hand-written or via a package |
| Real-time job progress | **SignalR** built in | Django Channels (adds a channel layer) or SSE (simplest) |
| Reuse of Python pipeline | Through workers and the data contract only (no in-process reuse) | In-process reuse possible, but workers are isolated anyway, so the benefit is smaller than it looks |
| Typed API | Strong; OpenAPI generation; TypeScript client generation | Django Ninja (Pydantic) or DRF |
| Migrations / admin back office | EF Core migrations (or SQL migrations); no generic admin | Built-in migrations and admin |
| Support window | .NET LTS: three years per release (verify current) | Django LTS: about three years (verify current) |
| Staffing | Unknown in the owner's team (Q-3) | Python already used by the project |

### 4.2 IIS vs native Windows Service

| Aspect | IIS front end | App as Windows Service (no IIS) |
| --- | --- | --- |
| TLS | Certificate bound in IIS from the Windows certificate store | App loads the certificate from the store (Kestrel supports this) or from a protected file |
| Static files, request limits, filtering | IIS request filtering, `maxAllowedContentLength`, static-file caching | Configured in the app |
| Windows authentication | IIS handles Negotiate, passes identity | Kestrel Negotiate (ASP.NET); for Django, an LDAP bind form instead |
| Process recycling and recovery | Application pool recycling, rapid-fail protection | Service Control Manager recovery actions |
| Admin familiarity | High in Windows estates | Moderate |
| Footprint | IIS role + modules (URL Rewrite, ARR for Django) | Minimal |

**Assessment.** For ASP.NET Core, either mode is first-class; IIS is the default if the site's administrators expect it. For Django, IIS acts only as a reverse proxy and adds two modules; a Windows Service with its own TLS may be simpler. **[PoC P1]** must run both modes for both frameworks and record install steps, recovery behaviour and latency.

### 4.3 Provisional view

Neither framework is presumed. B0's provisional reading of the documentary evidence: **ASP.NET Core is the lower-risk Windows production host** (K1, K2), and **Django is the lower-friction development path** (K5). The weighted scoring sheet in ADR-0005 §6 settles it with P1/P8/P9 evidence.

## 5. Python workers on Windows

- **Process model:** each worker class (`ingest-parse`, `ingest-ocr`, `embed`, `index`, `release-import`) runs as its own Windows Service with a **virtual service account** (`NT SERVICE\MimamsaOcr` style) or a dedicated low-privilege local account. No inbound ports.
- **Runtime:** an embedded, pinned CPython (python.org Windows embeddable package or a full installer laid down by the MSI) with a hash-locked wheel set installed offline. The app path standardises **one Python version** (C12 noted a 3.11/3.13 split; the plan's A9 closes it).
- **Service wrapper:** pywin32 `win32serviceutil` (PSF licence) or a small, auditable service wrapper. Verify licence of any third-party wrapper. **[PoC P5]**
- **Queue:** a PostgreSQL job table with `SELECT … FOR UPDATE SKIP LOCKED`, leases and heartbeats; retries with backoff; idempotent steps keyed by (sha256, pipeline version). **[PoC P5]**: 16k-file import, injected failures, service kill and restart, no lost or duplicated jobs.
- **Limits:** Windows Job Objects per task for CPU rate, memory and wall-clock limits; parser runs in a child process so a crash or hang kills only that job. **[PoC P5]**
- **Network:** Windows Firewall outbound block rules scoped to each worker service SID (only loopback to PostgreSQL allowed). **[PoC P8]**

## 6. Database on Windows

| Item | Assessment |
| --- | --- |
| PostgreSQL on Windows | Supported platform; official Windows binaries exist (EDB-built installers and zip archives). Runs as a Windows Service under `NT AUTHORITY\NetworkService` by default; the installer should create a dedicated account instead **[PoC P8]** |
| pgvector on Windows | No official Windows binary from the project. Options: build with Visual Studio Build Tools against the exact PostgreSQL major (documented upstream), or obtain a vetted binary. The build must be reproducible and signed into the installer **[PoC P2, P8]** |
| FTS | Built in; custom text search configuration (simple dictionary for identifiers, English stemmer for prose, synonym dictionary for "AA" → "Army Act", "court-martial" ↔ "court martial") **[PoC P2]** |
| Backup | `pg_dump` / `pg_basebackup` scheduled by Task Scheduler; WAL archiving optional. pgBackRest is not supported on Windows; do not plan on it |
| Upgrades | Major upgrades via `pg_upgrade` or dump/restore, inside the installer's upgrade path, with pgvector rebuilt for the new major **[PoC P8]** |
| Alternative | SQL Server: Windows-native, but Express caps database size and vector features depend on version; licence cost for Standard. Not preferred |

## 7. Lexical, vector and graph search

The one-database principle stands: relational data, FTS, vectors, the graph and the job queue in PostgreSQL give one backup, one restore and **one transaction boundary**, which makes withdrawal leak-proof by construction (T-07).

- **Lexical:** passage-level `tsvector` columns (identifier-preserving and stemmed). `ts_rank_cd` is not BM25. **[PoC P2]** compares it with a true BM25 index. Adopt a BM25 derived index only if the recall gain is material (≥5 points recall@20 on held-out queries), with a generation check that blocks search when the index and the database disagree.
- **Vector:** pgvector HNSW on half-precision vectors; one embedding per passage with model id and model-file hash. **[PoC P2]**: filtered HNSW recall and latency (published-only, court, year).
- **Graph:** relational edge tables (typed, anchored, with axis states) and recursive CTEs; Cytoscape.js in the browser. Apache AGE on Windows is uncertain; not planned.
- **Ranking rule (all options):** no "binding" or "current" ranking signal; results show why they matched (passage, page, statute).
- **Retrieval benchmark hygiene:** dev queries written fresh by an agent who has not seen the golden set; the 50-question golden set is held out for evaluation only; relevance double-coded.

## 8. Local embeddings and reranker

Unchanged in substance from the earlier assessment, now with Windows notes.

- **Runtime:** ONNX Runtime (MIT) CPU execution provider; Windows wheels exist. DirectML or CUDA providers are optional and never required (T-12).
- **Shortlist:** one small and one base model each from BGE, E5 and Arctic-embed, plus one multilingual model and two cross-encoder rerankers; licences per model card (MIT/Apache-2.0) recorded in the model bundle.
- **Bulk embedding** may run on the internet-connected build side and ship in the bundle with the model hash; the server embeds only queries and Admin uploads.
- **Offline loading:** `HF_HUB_OFFLINE=1`; load only from the bundled model directory whose hash is checked at service start.
- **Targets [PoC P3]:** query embedding < 100 ms; bulk embedding of today's corpus within one overnight run on the reference CPU.

## 9. Local LLM (later, gated; not in Cycle 13)

No generative model is installed in Cycle 13. The gate (Legal Reviewer designation confirmed, prompt-injection isolation tested, drafting-only use, held-out evaluation, banner on every output) is unchanged. If later approved, llama.cpp (MIT) has native Windows builds and runs on CPU; a GPU remains optional.

## 10. OCR on Windows

| Engine | Windows status | Licence | Notes |
| --- | --- | --- | --- |
| **Tesseract** | Windows builds are available (for example the UB Mannheim builds); bundle the executable and `eng` traineddata in the installer; invoke from the worker via subprocess (no network) | Apache-2.0 | Already used for 944 scanned judgments (4,705 pages) at 300 dpi with threshold 70. Produces TSV/hOCR word boxes and confidence |
| PaddleOCR | Python package on PaddlePaddle; Windows CPU wheels exist but version pinning is fragile **[PoC P6]** | Apache-2.0 | Often stronger on difficult layouts; heavier |
| docTR | PyTorch or ONNX backends | Apache-2.0 | Alternative second pass |
| OCRmyPDF | Runs on Windows with Tesseract and Ghostscript | MPL-2.0 (Ghostscript AGPL) | Avoid Ghostscript-dependent output unless D-02 accepts AGPL; not needed for search |
| Windows built-in OCR (Windows.Media.Ocr) | Available on Windows 10/11 and Server with Desktop Experience **[verify]** | OS component | No per-word confidence comparable to Tesseract; not recommended as primary |
| Prism | Unknown availability (D-10) | Unknown | Treated as unavailable until shown otherwise |

**Assessment:** Tesseract primary; per-page confidence and per-word boxes stored for B5 highlighting; pages below threshold flagged for review and labelled after publication; OCR text is for search, not quotation (contract rule `OCR_QUOTING`). **[PoC P6]** decides whether a second engine is worth its weight.

## 11. PDF viewer, frontend, real-time and authentication

- **PDF.js:** `pdfjs-dist` with the worker bundled locally; `isEvalSupported:false` (CVE-2024-4367 class), scripting disabled, current patched release; PDFs served from the app origin under a strict CSP. Native highlighting by text-layer matching; scans by overlay boxes from OCR word coordinates. **[PoC P4]**
- **Frontend:** React + TypeScript built online from a hash-locked lockfile; output is static files; no runtime CDN, web fonts or analytics; CI fails if the bundle references an external URL. Component library: permissive (verify), or a small in-house set following `app/design`.
- **Real-time:** job and import progress only, via SignalR or SSE; never used to push legal content.
- **Authentication:** local accounts (framework-default strong hashing, lockout, session expiry, CSRF); optional AD maps one AD group to Admin and admits a second group as User; there are no further roles. The **Legal Reviewer designation** is a separate registry row on an existing account, inert until an appointment record exists; the app has no code path that records a legal approval in Cycle 13. **[PoC P9]**

## 12. Packaging, installer and updates (Windows)

### 12.1 Offline installer

One signed installer set, built online, transferred on removable media:

| Component | Packaging |
| --- | --- |
| App (ASP.NET Core self-contained publish, or Python app + embedded CPython) | MSI feature; files under `C:\Program Files\Mimamsa\` (read-only to service accounts) |
| PostgreSQL + pgvector (exact major, reproducible build) | MSI feature or chained installer; data directory on a dedicated volume (e.g. `D:\Mimamsa\pgdata`) |
| Workers + Python wheels (hash-locked) | MSI feature |
| Tesseract + traineddata; ONNX models (hashed) | MSI features; models under `D:\Mimamsa\models\` |
| Windows Services, firewall rules, NTFS ACLs, certificate binding | Installer custom actions (PowerShell, logged) |
| SBOM and licence inventory | Shipped alongside |

Authoring candidates: WiX Toolset (verify licence; MS-RL historically), or a scripted PowerShell installer as fallback. Code-signing of the MSI with an organisation certificate is recommended; the update bundles are signed independently (§12.2). **[PoC P8]**: clean Windows Server, networking disabled, install, uninstall, reinstall, upgrade.

### 12.2 Snapshot update flow

Data contract v1 (`app/contract`) defines the bundle. The importer (a worker service):

1. verifies the Ed25519 signature over `SHA256SUMS` against the public key pinned at install;
2. verifies every checksum; rejects unlisted files, symlinks/reparse points and unsafe paths;
3. checks contract compatibility and minimum app version; runs declared migrations only if signed and listed;
4. re-applies the restricted-material register (`config/restricted_material.json`) and rejects any hit;
5. loads into a **new release generation**, builds indexes, runs smoke queries;
6. switches atomically; keeps N-1 (configurable) for rollback;
7. reconciles local Admin uploads (Architecture §9.1) and turns `CHANGES.json` into impact triggers.

Any failure rejects the whole bundle with nothing changed. **[PoC P8]**

### 12.3 Storage and backup

- **Vault:** content-addressed on NTFS, `D:\Mimamsa\vault\sha256\ab\<hash>`; files set read-only and ACL'd so worker accounts can read, only the import service can create, nobody can modify. Re-hash on read for cited originals.
- **Derivatives:** `D:\Mimamsa\derived\<sha256>\<pipeline_version>\`; disposable.
- **Backups:** scheduled `pg_dump`/`pg_basebackup` plus robocopy or restic (BSD) of vault and local uploads to rotated offline media; Windows Server Backup or VSS snapshots optional. Restore drill is part of acceptance.

## 13. Licensing summary (verify at selection, P7)

| Component | Licence (as understood) | Concern |
| --- | --- | --- |
| .NET / ASP.NET Core runtime and libraries | MIT | None |
| Django, django-auth-ldap, ldap3 | BSD / BSD / LGPL-3.0 (ldap3, verify) | LGPL needs a note if ldap3 used |
| PostgreSQL, pgvector | PostgreSQL licence | None |
| PDF.js, React, Cytoscape.js, Vite | Apache-2.0 / MIT | None |
| Tesseract, PaddleOCR, docTR, ONNX Runtime | Apache-2.0 / MIT | None |
| pypdfium2, pdfminer.six, pdfplumber | Apache-2.0 or BSD / MIT / MIT | None |
| **PyMuPDF** | **AGPL-3.0 or commercial** | Keep out of the app path; keep in offline audit tooling only if D-02 accepts |
| Ghostscript | AGPL or commercial | Avoid |
| pywin32 | PSF | None |
| WiX Toolset | MS-RL (verify current) | Build-time only; check obligations |
| cryptography (Python), libsodium/minisign | Apache-2.0/BSD; ISC | None |
| SQL Server Express/Standard | Proprietary | Only if chosen |
| Model weights | Per model card | Record per model in the bundle |

## 14. Security posture

Moved to [SECURITY_AND_DEPLOYMENT_ARCHITECTURE.md](../architecture/SECURITY_AND_DEPLOYMENT_ARCHITECTURE.md): service identities, NTFS ACLs, firewall, parser isolation, local TLS, sessions/CSRF, server-side authorisation, signing-key custody, safe parsing, threat tests, logging without sensitive content, zero runtime internet dependency, signed update and restore.

## 15. Risks and exit paths

| Risk | Signal | Exit path |
| --- | --- | --- |
| Python web serving on Windows is fragile (if Django) | P1 recovery or latency failures | ASP.NET Core host with Python workers |
| C# capacity absent in the team (if ASP.NET Core) | Owner answer to Q-3 | Django on Windows if P1 passes |
| pgvector cannot be built reproducibly for the Windows PostgreSQL major | P2/P8 | Qdrant Windows binary with a generation check; or vectors in a worker-owned index |
| PostgreSQL FTS ranking too weak | P2: BM25 gain ≥5 points recall@20 | BM25 derived index with generation check |
| OCR second engine fragile on Windows | P6 | Tesseract only, with review list |
| Installer complexity | P8 failures | Scripted PowerShell installer with signed payloads |
| AGPL in the app path | P7 | pypdfium2/pdfminer in the app path |
| Service count creeping above ~6 | Design review | One-database principle; any new service needs an ADR with a measured need |

## 16. Proofs of concept (B-PoC owns the evidence)

Placeholders keyed to **P1–P9**. B0 has measured nothing here. Folder names for P1–P5 and P7 match the B-PoC branch; **P6, P8 and P9 keys are B0's proposal for coordinator confirmation**.

| PoC | Question | Go criterion (proposed) | Evidence | Status |
| --- | --- | --- | --- | --- |
| P1 Hosting | ASP.NET Core vs Django; IIS vs Windows Service; recovery; SignalR/SSE | Both modes install and recover unattended; metadata p95 < 300 ms at 25 users | `app/poc/p1_hosting/` | PENDING |
| P2 Search | FTS vs BM25 vs vector vs hybrid; identifiers; withdrawal consistency | Hybrid recall@20 ≥ best single; FTS within 5 pts of BM25 or adopt BM25; p95 < 1 s at 10 concurrent | `app/poc/p2_search/` | PENDING |
| P3 Embeddings | Model choice; CPU throughput | Query < 100 ms; full corpus overnight | `app/poc/p3_embeddings/` | PENDING |
| P4 PDF | Page anchoring and highlight | Page ≥ 98%; native highlight ≥ 90%; scanned overlay shown | `app/poc/p4_pdf/` | PENDING |
| P5 Jobs | PG job table + Windows Service workers | No lost/duplicated jobs over 16k import with kills | `app/poc/p5_jobs/` | PENDING |
| P6 OCR | Tesseract vs PaddleOCR/alternative on Windows | Material accuracy gain at acceptable cost | `app/poc/p6_ocr/` | PENDING |
| P7 Licences | SBOM + licence scan, both options | No unresolved copyleft without D-02 | `app/poc/p7_sbom/` | PENDING |
| P8 Installer/update | Offline MSI; signed import; N→N+1; rollback; networking off | All pass; tampered bundle rejected unchanged | `app/poc/p8_installer/` | PENDING |
| P9 Identity/security | Local + AD; CSRF; authorisation; ownership; threat subset | Security architecture §9 subset passes | `app/poc/p9_security/` | PENDING |

The B-PoC host is Linux (4 cores, 15 GB, no .NET, no Tesseract). P1, P5, P6, P8 and P9 therefore need **a Windows host** for final evidence; Linux-host measurements may stand in for algorithmic questions (P2, P3, P4) only, and must be labelled with the hardware actually used.

## 17. Phased build (after GB1)

1. **B1 Foundation:** installer skeleton, services, PostgreSQL schema with separate axes, vault, contract-v1 import with signature and checksum verification, passage extraction and OCR flags, hybrid search, PDF.js at page with highlight, provenance panel, candidate banner, local Admin/User auth, one Admin upload → stage → publish → search → withdraw round trip, backup and restore, network-denied tests.
2. **B2 Research depth:** research workspace (tabs, panes, notes), judgment intelligence view with per-field axes and labelled outcome candidates, statutory explorer, graph exploration of candidate edges, Document Studio working sessions (no rules), release N→N+1 and rollback.
3. **B3 Hardening and administration:** AD option, knowledge administration screens, audit review, restore drills, performance at simulated 20 GB, incremental bundles, Windows-specific hardening.
4. **Later, each behind its own gate:** commander assistant, legal-rule features, Legal Reviewer workspace, template drafting, local LLM.

## 18. Open questions for the owner

- **Q-1 / D-01:** confirm Windows Server edition and version, the volume layout, and the expected number of concurrent users.
- **Q-2 / D-02:** licence posture for PyMuPDF (AGPL) and any LGPL/MS-RL build-time items.
- **Q-3:** in-house skills for C# vs Python maintenance (affects K9 and the ASP.NET/Django choice).
- **Q-4 / D-05:** local accounts vs AD; AD group names; custody of the release-signing key (owner) and a backup custodian.
- **Q-5:** is IIS mandated by local policy, or is a Windows Service acceptable?
- **Q-6:** Windows host for P1/P5/P6/P8/P9 evidence (none is available to the agents).
- **Q-7 / D-10:** Prism OCR availability.
