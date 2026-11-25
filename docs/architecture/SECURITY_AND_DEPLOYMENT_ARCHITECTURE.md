# Security and deployment architecture (Windows-native, offline LAN)

- **Recorded:** 2026-11-25 (Cycle 13, workstream B0). **Status:** PROPOSED design for independent security review. It authorises no deployment, key generation or installation.
- **Applies to:** whichever stack ADR-0005 selects (ASP.NET Core or Django web host; Python workers; PostgreSQL). Stack-specific items are marked **[A]** (ASP.NET Core) or **[B]** (Django).
- **Related:** [ADR-0005](decisions/ADR-0005-APPLICATION-STACK.md), [technology assessment](../planning/OFFLINE_APP_TECHNOLOGY_ASSESSMENT.md), [data contract v1](../../app/contract/README.md), Architecture §11, Ingestion §6–7, Document Studio §2 and §11, ADR-0002, ADR-0003, `docs/governance/CORPUS_REPOSITORY_GOVERNANCE.md`.

## 1. Principles

1. **Capability first, basic hygiene from day one** (ADR-0002 d.8): server-side mutation checks, safe parsing, integrity, backups, metadata-only audit and the offline boundary are launch requirements; advanced hardening follows.
2. **Zero runtime internet dependency.** Nothing at runtime reaches outside the LAN: no updates, telemetry, CRL/OCSP fetches, NuGet/PyPI/npm, model hubs, fonts or time servers outside the site.
3. **Least privilege per process.** Every service has its own identity and only the file, database and network rights it needs.
4. **Untrusted documents are hostile input.** Every uploaded or imported file is parsed in an isolated worker, never in the web process.
5. **Fail closed.** Missing register, bad signature, unknown role, missing appointment, unverified approval: the answer is "no" with a visible reason.
6. **Authorisation lives in the backend.** The UI hides controls for usability only.

## 2. Deployment topology

```
 Browsers (LAN, HTTPS only)
        |
        v  443/tcp (only inbound port on the server)
 +----------------------------------------------------------------------------+
 | Windows Server (reference: 16 cores, 64 GB, 1 TB SSD; GPU optional)        |
 |                                                                            |
 |  IIS site (TLS) ──or── App Windows Service (own TLS)     svc identity: W   |
 |      └─ Web/API (modular monolith) ─┐                                     |
 |                                      │ loopback 5432 only                  |
 |  PostgreSQL service ◄────────────────┤                    svc identity: D  |
 |                                      │                                     |
 |  Workers (Windows Services, no inbound ports, outbound blocked):          |
 |    ingest-parse  (P)   ingest-ocr (O)   embed (E)   index (I)              |
 |    release-import (R)                                                      |
 |                                                                            |
 |  D:\Mimamsa\vault      immutable originals (content-addressed)             |
 |  D:\Mimamsa\derived    rebuildable derivatives                             |
 |  D:\Mimamsa\staging    Admin uploads awaiting review (quarantine)          |
 |  D:\Mimamsa\sessions   Document Studio working files (per-user, TTL)       |
 |  D:\Mimamsa\releases   imported bundles, generations N and N-1             |
 |  D:\Mimamsa\pgdata     database cluster                                    |
 |  D:\Mimamsa\backup     local backup staging (copied to offline media)      |
 +----------------------------------------------------------------------------+
```

## 3. Windows service identities

| Service | Identity (proposed) | Notes |
| --- | --- | --- |
| Web/API | `IIS AppPool\Mimamsa` **[IIS]** or `NT SERVICE\MimamsaWeb` (virtual account) | No interactive logon; no admin rights |
| PostgreSQL | dedicated local account `svc-mimamsa-pg` (not `NetworkService`) | Owns `pgdata` only |
| ingest-parse | `NT SERVICE\MimamsaParse` | Reads staging/vault, writes its derived subfolder and scratch |
| ingest-ocr | `NT SERVICE\MimamsaOcr` | As parse; runs Tesseract child processes |
| embed | `NT SERVICE\MimamsaEmbed` | Reads derived text and models; writes vectors through DB only |
| index | `NT SERVICE\MimamsaIndex` | DB only |
| release-import | `NT SERVICE\MimamsaImport` | Only identity allowed to create files in `vault` and `releases` |
| Backup task | `svc-mimamsa-backup` via Task Scheduler | Read on vault/derived, `pg_dump` role |

Database roles mirror this: `mimamsa_web` (DML on app tables, **no** DDL, **no** UPDATE/DELETE on audit or release tables), `mimamsa_worker_*` (only the tables each worker writes), `mimamsa_import` (generation tables), `mimamsa_backup` (read). The PostgreSQL superuser password is set at install, held by the site administrator, and not stored by the app. `pg_hba.conf` allows only `host … 127.0.0.1/32 scram-sha-256` and `::1/128`.

## 4. NTFS ACLs

| Path | Web | Parse/OCR | Embed/Index | Import | Admins (site) | Everyone/Users |
| --- | --- | --- | --- | --- | --- | --- |
| `C:\Program Files\Mimamsa\` | R/X | R/X | R/X | R/X | Full | none |
| `vault\` | R (streaming originals to viewer) | R | — | Create files, no modify/delete | R (modify only through break-glass procedure) | none |
| `derived\` | R | Modify own subfolders | R | — | Full | none |
| `staging\` | Write new upload files (no read of others' ids by path) | R | — | — | Full | none |
| `sessions\<user-id>\` | Modify (owner checks in app) | R/W only for job folder handed over | — | — | Full | none |
| `releases\` | R | — | — | Full | Full | none |
| `pgdata\` | — | — | — | — | Full | none (PG account only) |
| `models\`, `tesseract\` | — | R | R | — | Full | none |
| logs `D:\Mimamsa\logs\` | Append | Append | Append | Append | R | none |

Vault files are written once, set read-only, and their SHA-256 is verified on write and before serving a cited original. Inheritance is disabled on the root folders; the installer applies ACLs with `icacls` and records the result.

## 5. Network and firewall

- **Inbound:** TCP 443 only, from the LAN subnets the site names; RDP/WinRM per site policy, not opened by the installer.
- **Outbound:** Windows Firewall outbound block rules scoped to each Mimamsa service SID; loopback to 5432 allowed for the services that need the database. PostgreSQL listens on loopback only.
- **No egress by design:** no update checks (.NET, Python, npm, model hubs), no telemetry (`DOTNET_CLI_TELEMETRY_OPTOUT=1` and equivalents set; no Application Insights) and no CRL/OCSP calls that would fail-slow (internal CA certificates issued without external AIA/CDP, or with internal endpoints only).
- **Network-denied test:** the full test suite runs with outbound blocked at the host; any attempted connection is a failure (§9 T-NET-*).

## 6. Process isolation of parsers

- Parsing (PDF, DOCX, images) and OCR run **only** in worker services, never in the web process.
- Each document job runs in a **child process inside a Windows Job Object** with: memory limit (e.g. 2 GB), CPU rate cap, wall-clock timeout, no child-process breakaway, kill-on-close. A crash, hang or memory blow-up kills that job only; the job is marked `FAILED` with a reason.
- The child gets a per-job scratch folder, wiped at job end, and the input as a read-only file handle; no access to `sessions\` of other users or to the vault beyond the job's input.
- Optional hardening for B3: run parser children under a restricted token or an AppContainer profile **[PoC P9]**.
- Text extracted from documents is **data**. No component interprets document text as instructions (there is no model in the loop in Cycle 13; the parser path is still tested with prompt-injection text, T-INJ-01).

## 7. Local TLS, sessions, CSRF and server-side authorisation

### 7.1 TLS

- Server certificate issued by the site's **internal CA** (or AD CS), installed in the LocalMachine store, private key non-exportable, ACL'd to the web identity. TLS 1.2+ only (TLS 1.3 where the OS supports it); HSTS on; HTTP redirects to HTTPS or is closed.
- No self-signed certificates in production; the installer refuses to finish without a certificate thumbprint, or marks the deployment "not production" in the banner.

### 7.2 Sessions and CSRF

- Server-side session or encrypted auth cookie: `Secure`, `HttpOnly`, `SameSite=Strict`; idle timeout (proposed 30 min) and absolute timeout (proposed 12 h); rotation on login and on privilege-relevant change.
- CSRF tokens on every state-changing request **[A]** antiforgery, **[B]** CSRF middleware; JSON APIs additionally require a custom header and same-origin `Origin`/`Referer`.
- Lockout after repeated failures (proposed 10 in 15 min), with Admin unlock; password policy per site (length-based; framework-default strong hashing: **[A]** PBKDF2 with high iteration count, **[B]** Argon2id).
- **[A]** Data Protection key ring stored under `D:\Mimamsa\keys`, protected with DPAPI-NG/machine scope, ACL'd to the web identity.
- Optional AD: Negotiate/Kerberos **[A]** or LDAPS bind **[B]**; one AD group → Admin, one → User; nobody else admitted.

### 7.3 Server-side authorisation model

| Check | Rule | Enforced where |
| --- | --- | --- |
| Role | Exactly `ADMIN` or `USER`. Unknown role → deny | Policy/decorator on every endpoint; default-deny router |
| Corpus mutation | Upload, stage review, publish, withdraw, replace, reprocess, release import, metadata correction → `ADMIN` only | Endpoint policy **and** service-layer guard (defence in depth) |
| Ownership | Document Studio sessions, working files, job ids, exports, notes and research workspaces carry `owner_id`; every read/write/download checks `owner_id == current user` (Admin included; ADR-0003) | Resource-based handler; repository queries always filter by owner |
| Visibility | Users see only `publication=PUBLISHED` items; staging visible to Admin only | Query layer: published view; staging tables not reachable from User endpoints |
| Legal Reviewer designation | A row in `designations` tied to an account and an `Appointment`. **No endpoint records an approval in Cycle 13.** The designation flag is inert; any approval endpoint returns 403 `GATE_CLOSED` | Feature gate + data check (`auth_ledger_version == 0` ⇒ closed) |
| Gated features | Commander assistant, legal-rule checks, readiness reports, template filling → disabled by configuration that cannot be enabled while the reasoning-feature gate is closed | Startup config validation + per-request gate check |
| Opaque ids | Ids are random (UUIDv4/ULID); knowing an id grants nothing | All of the above |

## 8. Signing-key custody and signed offline updates

### 8.1 Keys

| Key | Holder | Where | Notes |
| --- | --- | --- | --- |
| **Release-signing key** (Ed25519) | **Owner** (D-05), with a named backup custodian | Offline: hardware token or encrypted removable media kept in a safe; never on the build machine's disk unencrypted, never in GitHub, HF or CI | Signs `SHA256SUMS` of each release bundle. Public key pinned in the installer |
| Installer code-signing certificate | Organisation PKI | Per organisation policy | Optional but recommended |
| TLS server key | Server LocalMachine store, non-exportable | Server | Issued by internal CA |
| **Development keys** | Agents/developers | Generated in memory or scratch per test run (`app/contract/mimamsa_contract/devbundle.py`), `key_id` prefixed `dev-` | Disposable. A production importer rejects `dev-` key ids unless started in explicit development mode |

Key rotation: a new public key is delivered in a bundle **signed by the old key** plus an out-of-band fingerprint check by the site Admin. Compromise: the owner issues a revocation notice through the same channel; the site Admin removes the old key from the trust list.

### 8.2 Update flow (online → offline)

```
ONLINE BUILD SIDE                                         OFFLINE SITE
HF dataset @ pinned 40-char revision ┐
Track A artefacts @ git commits ──────┼─ build_release --check ─► release bundle (contract v1)
restricted register (sha256) ─────────┤   (filters RM-* items)     RELEASE.json, CHANGES.json, data/…,
model bundle hashes ──────────────────┘                            SHA256SUMS, SHA256SUMS.sig
             owner signs SHA256SUMS offline ─────────────────► removable media (scanned per site policy)
                                                                     │
                                                    release-import service:
                                                      1 signature (pinned key; dev- keys refused)
                                                      2 every checksum; no unlisted files, reparse points, unsafe paths
                                                      3 contract major + min app version; signed migrations only
                                                      4 restricted register re-applied; any hit rejects
                                                      5 schema + semantic rules on every record
                                                      6 load into NEW generation; build indexes; smoke queries
                                                      7 atomic switch; keep N-1
                                                      8 reconcile local uploads; CHANGES.json → impact triggers
```

Any failure in 1–6 rejects the whole bundle and changes nothing. The validator in `app/contract` implements 1–5 and is the reference for the importer.

### 8.3 Backup and restore

- Nightly `pg_dump` (custom format) plus weekly `pg_basebackup`; vault, local uploads and configuration copied with robocopy or restic to rotated offline media; checksums verified after copy.
- **Working sessions are excluded** from backups by default (Document Studio §2); if a site includes them, the same ownership, retention and deletion rules apply to the backup.
- **Restore drill** (acceptance): clean server → installer → restore DB and vault → hash-verify vault against the DB → smoke queries return identical results to a recorded fixed query set → rollback to the previous generation works.

## 9. Threat-test list

Tests run against the API directly (not only the UI) and in a network-denied environment. This list consolidates Ingestion §7, Document Studio §11, the Cycle 13 plan (B2, B7, B9, B10, B12) and the owner directive's emphasis on server-side authorisation, ownership, parsers and offline updates. **The coordinator should reconcile it line by line with the directive's own threat list**, which is not reproduced in the repository.

| ID | Threat | Test | Expected |
| --- | --- | --- | --- |
| T-AUTH-01 | User calls Admin endpoints | As User: upload source, create ingestion job, list staging, publish, withdraw, replace, reprocess, import release, edit metadata | 403; no state change (DB diff empty) |
| T-AUTH-02 | Forged role | Tamper cookie/claims to claim Admin | 401/403; session invalidated |
| T-AUTH-03 | Unknown role / no role | Account with no role mapping (AD group missing) | Not admitted |
| T-AUTH-04 | Legal Reviewer misuse | Account with designation flag but no appointment; Admin attempting approval | 403 `GATE_CLOSED`; no approval row |
| T-AUTH-05 | CSRF | State-changing request without token / cross-origin | Rejected |
| T-AUTH-06 | Session fixation / reuse | Reuse pre-login session id; use expired session | Rotated / rejected |
| T-AUTH-07 | Brute force | Repeated bad passwords | Lockout; audit event |
| T-OWN-01 | Cross-session access (IDOR) | User B requests User A's session, file, job, export, note, workspace by id | 404/403; nothing leaked in error |
| T-OWN-02 | Admin reads User working session | Admin via ordinary Document Studio endpoints | Denied (ADR-0003) |
| T-OWN-03 | Working file leaks to shared index | Upload to Document Studio, then search, graph, embeddings, template registry | No trace anywhere |
| T-VIS-01 | Staged content leak | Search/snippet/graph/suggest for a staged item as User | Absent |
| T-VIS-02 | Withdrawal leak | Withdraw a published item; query FTS, vector, suggestions, graph, caches, exports | Absent within the same transaction/job |
| T-RM-01 | Restricted material in bundle | Bundle contains a register hash, doc_id or hosted path | Bundle rejected |
| T-RM-02 | Restricted material via Admin upload | Admin uploads bytes whose sha256 is in the register | Quarantined; cannot be published; not indexed or embedded |
| T-RM-03 | Register missing | Remove/corrupt `config/restricted_material.json` | Import and publication refuse (fail closed) |
| T-PARSE-01 | Malformed PDF | Fuzzed/corrupt PDFs, decompression bombs, deep object graphs | Job fails within limits; web unaffected |
| T-PARSE-02 | Type confusion | `.pdf` that is an executable/HTML/zip; polyglots | Rejected by content sniffing |
| T-PARSE-03 | Oversized input | Exceed size/page limits | Rejected before parsing |
| T-PARSE-04 | Path traversal / reparse points | Filenames with `..`, ADS (`file:stream`), device names (`CON`, `NUL`), junctions in archives or bundles | Rejected; stored by hash only |
| T-PARSE-05 | DOCX external references | DOCX with remote template/image links, macros | No fetch; macros never executed |
| T-INJ-01 | Prompt-injection text | Document containing instruction-like text | No effect on any behaviour or state |
| T-PDFJS-01 | Malicious PDF in viewer | Crafted font/JS PDFs (CVE-2024-4367 class) | No script execution (`isEvalSupported:false`, scripting off, CSP) |
| T-XSS-01 | Stored XSS via metadata/notes | Titles, notes, filenames containing markup | Escaped everywhere |
| T-UPD-01 | Tampered bundle | Flip one byte; edit SHA256SUMS; swap signature; wrong key; `dev-` key in production | Rejected, nothing changed |
| T-UPD-02 | Downgrade / incompatible | Older release id, other contract major, app too old | Rejected or requires explicit Admin rollback path |
| T-UPD-03 | Rollback | N→N+1 then rollback | Identical results on fixed query set |
| T-NET-01 | Runtime egress | Run all services and tests with outbound blocked; monitor connection attempts | Zero attempts outside loopback |
| T-LOG-01 | Sensitive content in logs | Search queries, working-file text, passwords in logs | Absent (see §10) |
| T-LEDGER-01 | Approval while AUTH-LEDGER v0 | Bundle or API sets `legal_approval` above T0 | Rejected |
| T-GATE-01 | Gated feature switched on | Configure commander assistant/legal rules on | Startup refuses; banner still mandatory |
| T-BKP-01 | Restore | Full restore drill | Passes; vault re-hash clean |

## 10. Logging without sensitive content

- **Audit log (append-only table + Event Log copy):** actor, role, action, object type and id, time, outcome, client IP, hashes and sizes. **Never** document text, search query text, working-file content, notes content, passwords or tokens.
- **Operational logs:** structured, rotated, ACL'd; request paths with ids only; query strings stripped of search terms (logged as length and hash if needed for debugging).
- **Search analytics:** none in Cycle 13.
- Restricted-material hits are logged by restriction id only, never by matched value.
- The web identity cannot update or delete audit rows (DB role); a hash chain over audit rows is optional for B3.

## 11. Zero runtime internet dependency checklist

- All JavaScript, CSS, fonts (system font stacks, see `app/design`), PDF.js worker and icons are served locally; CI fails on external URLs in the built bundle.
- Models load from the bundled folder with hash verification; `HF_HUB_OFFLINE=1`; no auto-download paths.
- No package manager runs on the server; Python wheels and .NET runtime are laid down by the installer.
- Certificate validation does not depend on external CRL/OCSP.
- Time from the site's internal time source.
- Network-denied CI job and on-site test (T-NET-01).

## 12. Safe parsing summary

| Stage | Control |
| --- | --- |
| Receive | Size limit; filename discarded for storage (sha256 name); content sniffing (magic bytes) against an allow-list (PDF, DOCX, PNG, JPEG, TIFF, plain text) |
| Quarantine | Stored in `staging\` with no execute rights; not indexed |
| Screen | Malformed-file checks; optional on-site antivirus scan if the site provides one offline |
| Parse | Worker child process in a Job Object; permissive libraries (pypdfium2/pdfminer/pdfplumber; python-docx without external fetch); Tesseract subprocess |
| Persist | Original bytes to vault by sha256 (Import/Parse service only per ACL); derivatives under `derived\<sha256>\<pipeline_version>\` |
| Publish | Admin action; restricted register re-checked; eligibility recorded |

## 13. Open items for security review

1. AppContainer/restricted-token sandboxing for parser children (B3) **[PoC P9]**.
2. Whether IIS is mandated by site policy (affects §3, §7.1).
3. Antivirus availability and update channel on the air-gapped site.
4. The site's internal CA and certificate lifecycle.
5. Reconciliation of §9 with the directive's threat list.
