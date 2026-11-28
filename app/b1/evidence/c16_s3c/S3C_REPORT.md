# C16 Tranche B Stage 3, stream S3-C: offline installation, activation, rollback, retention, encrypted backup and restore

**DEVELOPMENT / TEST-DATA ONLY.** Every result here comes from development keys, fixture releases and test data on
CI runners, disposable `c16s3c_*` databases and roles, and temporary directories. Acceptance level is **FIXTURE** (SG-5).
Nothing here is a production activation, an operational migration or a change to trust or AUTH-LEDGER, and nothing
was written to HF. The local host ran only bounded unit and database tests; the system-level installation ran on CI only.

Branch `claude/c16-s3c-install`, cut from `claude/c16-cp1` at `4ba059fa`. Draft PR #88.
Final head and CI run ids: section 6.

## 1. What was built

The core library is `app/b1/src/Mimamsa.Core/Install/`. The commands are served by the activation tool
`Mimamsa.Activation`.

| Piece | File | What it does |
| --- | --- | --- |
| Path negatives (carried from CP-1 §7) | `PathSafety.cs` | Refuses: reserved device names (CON, NUL, COM0-9, LPT0-9, superscript digits, CONIN$, CONOUT$, CLOCK$; with or without an extension); trailing dot or space; alternate data streams; the 8.3 short-name shape, and a real 8.3 alias of an existing path (`GetLongPathName`); case collisions (NFC-folded, including file-versus-directory); symlinks, junctions and reparse points (reported, never followed); device and UNC paths; traversal; nested or equal roots. Applied to installation roots, release trees (`release-check`, and before `stage`) and backup archive entries. |
| Four-release layout (WD-6) | `InstallConfig.cs` | `application`, `knowledge`, `intelligence` and `site_data` roots, all configurable. Store roots must lie outside the application root and outside each other. Headroom, minimum free space and `keep_previous` (default 2, WD-13) are configurable. Production mode is refused. Install is idempotent and never deletes; each install run appends a record. The directories B06/B01 fix under the site root are recorded as not yet relocatable. |
| Measured disk preflight (D5) | `InstallPreflight.cs` | Per volume: measured payload bytes × (1 + headroom) + minimum free space, compared with the measured free space. It refuses on failure and keeps a record with the measured values. There is no fixed allocation. |
| Database setup with B03 2.1 hardening | `SiteDatabaseSetup.cs` | Creates roles `<p>web`, `<p>backup` and `<p>kr_loader` (NOSUPERUSER, NOCREATEROLE, NOCREATEDB, NOREPLICATION, NOBYPASSRLS, NOINHERIT; no memberships). Revokes CREATE on schema public, and TEMPORARY, CREATE and CONNECT on the database, from PUBLIC; revokes ALL on `site` and `knowledge`. Then grants explicitly, re-asserting on every run. Includes a probe matrix (§3). |
| I-3 migration gate (SG-2) | `SiteDatabaseSetup.cs` | Runs B03's copy-and-verify migration **only on an installer-marked CLONE**: forward, verify that the old schema is unchanged, ROLLBACK, verify, forward again. Destructive plans or SQL, non-clones and non-disposable database names are refused before any database work. |
| Production `stage` command | `InstallCli.cs` | Runs the release-path negatives, then `GenerationStaging.VerifyAndStageAsync` with the restricted loader's credentials (from the environment, never on argv). |
| Encrypted backup (WD-10) | `BackupCrypto.cs`, `SiteBackup.cs` | See below. |
| Restore (arch §10) | `SiteRestore.cs` | See below. |
| Windows service job | `Mimamsa.Activation/ServiceJob.cs` | Runs one bounded job **as a Windows service under its virtual account**. Used for the ACL probe matrix and for running the activation tool as its own identity. |
| Development installer | `app/installer/windows/*.ps1` | See below. |
| Filled-volume preflight | `Test-FilledVolumePreflight.ps1` (diskpart VHDX), `app/installer/linux/test-filled-volume.sh` (tmpfs) | Refused while full, accepted once space is freed, with the measured values in the record. |
| Real restore test | `app/b1/build/c16_s3c_restore.py` + `S3cRestoreJourneyTests` | §2 |
| CI | `.github/workflows/c16-s3c-install.yml` | Jobs `s3c-linux` and `s3c-windows` |

**Encrypted backup.**
- Encryption uses AES-256-GCM, HKDF-SHA256 and SHA-256 from `System.Security.Cryptography` (CNG / OpenSSL), arranged in the standard STREAM construction. The construction is a u64 counter plus a final-flag nonce, with the header hash bound in as associated data.
- No cryptographic primitive is hand-written.
- The `site` part contains:
  - the `pg_dump` of the site schemas, run as the BACKUP role;
  - the vault, uploads and config (secrets excluded);
  - trust and SITE_CONFIG;
  - the append-only heads observed **before** the database dump.
- The **separate** append-only part contains the journal, activation log, ExclusionStore, latch, SITE_INIT and the reader's high-water mark. It is copied under the journal guard.
- Integrity: `SHA256SUMS`, then a verification pass after every copy to media. Knowledge is never backed up.

**Restore.**
- Every part is authenticated and extracted into scratch **before** the target is touched. Only regular files are accepted, and `MANIFEST.json` must be last and exact.
- Each append-only store is taken from the newest valid candidate: the backup, newer offline copies, or the target's own. A target store is never overwritten by an older one, and the latest exclusions win.
- Refused cases:
  - stores older than the database dump, missing, diverged, or corrupt beyond a torn tail;
  - a database version mismatch;
  - pg_restore runs in one transaction from the site's own dump, with the target's pre-existing `public` entries dropped through a use-list.
- The vault is restored write-once and verified by sha256. Config conflicts are set aside, not overwritten.
- `ACTIVE` stays absent (it is a derived pointer) until `recover` derives it from the journal head. The site is left RECOVERING.

**Development installer.**
- `Install-MimamsaDev.ps1` creates services `MimamsaWeb` and `MimamsaActivation` under **virtual service accounts** (WD-5), with unrestricted service SIDs and recovery actions.
- Store roots are **owned by the activation identity**, inheritance is disabled, and the web identity gets read and execute only. The single exception is that the web identity may write `site\activation-state`, because the exclusion reader persists its high-water mark there (I-6).
- One inbound firewall rule: TCP 443.
- Evidence written: `icacls` output, `sc qc` output, the firewall rule list and the install record.
- `Uninstall-MimamsaDev.ps1` removes the services, binaries and firewall rule, and **keeps all site data**.
- `Test-MimamsaDevInstall.ps1` runs the acceptance checks (§3).

## 2. The real restore test (CI, Linux and Windows)

The driver builds four development-signed releases with B02. G1 is `cp1-fixture`; G2, G3 and G4 are the `cp1-slice` content under distinct release ids and sequences. The journey then:

1. **Install site A.**
   - Layout with the measured preflight over the four bundles.
   - Seed a source database and run the I-3 migration on a clone (with rollback).
   - db-setup with the probe matrix.
2. **Import and stage.** Each release passes `release-check` and is imported with B01 (stage-only after G1), then staged with the production `stage` command. Staging covers the B03 loader, the B04 text store and lexical index, and the reference outcome rule (ACTIVE_DEGRADED). The loader has no CREATE on `kr_2_staging`.
3. **Activate and roll back.**
   - Activate G2, G3 and G4 through the activation CLI (`--knowledge-rows`), with the web process as the authenticated pipe participant.
   - **Prune** removes only G1 (active plus two previous distinct releases).
   - **Rollback** to G3; a second prune removes nothing.
   - Exclusion **E1** withdraws the admitted copy.
4. **Back up.** Encrypted backup as the backup role, copied to media and verified.
5. **Continue after the backup.** Activate G4 and apply exclusion **E2** (the statute, by copy hash). Take a second backup to media and keep its append-only part separately.
6. **Destroy site A.** Stop the web process, drop the databases and delete every root.
7. **Prepare fresh site B.** New roots, a new database and **new roles**.
8. **Negative drills, all refused with site B untouched** (no tables, identical tree):

   | Drill | Refusal code |
   | --- | --- |
   | wrong key | `BACKUP_WRONG_KEY` |
   | tampered site part | `BACKUP_AUTH_FAILED` |
   | truncated site part | `BACKUP_TRUNCATED` |
   | partial (site part missing) | `BACKUP_PARTIAL` |
   | append-only part missing | `APPENDONLY_MISSING` |
   | newer site part with older append-only stores | `APPENDONLY_OLDER_THAN_DATABASE` |
9. **Restore.** The older backup's site part plus the separately kept **newer** append-only stores.
   - Journal and exclusions are taken from the offline copy.
   - **The journal head is followed: G4, not the backup's G3.**
   - The restored journal and exclusions are byte-identical to the destroyed site's.
   - Site data is identical to the backup by ordered dumps (accelerator tables excluded).
   - Local uploads and config are restored; the probe matrix holds on B.
   - The site is RECOVERING and serves nothing.
10. **Re-import the journal-head release (G4) from media** (stage-only).

**Result: everything above passes on both platforms**, 59 journey checks per platform.

**Cross-stream blocker found (S3C-B01-B03-REIMPORT-AFTER-EXCLUSION). It needs an owner or cross-stream decision.** Staging the re-imported G4 on site B fails:
- `KR_ROWS_REDERIVE_MISMATCH [graph_nodes]` and `[graph_edges]`;
- `OUTCOME_REFUSED REBUILD_REQUIRED` (GRAPH, KNOWLEDGE_ROWS).

The cause is an interaction between two other streams:
- The **B01 importer narrows the servable set using the site's current exclusion state at import time**. E1 and E2 withdraw copies of G4, so those copies are dropped from the generation.
- The **shipped GRAPH and KNOWLEDGE_ROWS were built centrally without site exclusions**.
- B03's re-derivation over the narrowed generation therefore differs, and staging refuses.

Any release imported or re-imported after an exclusion that touches it fails the same way, and in a disaster restore that is always the case. The site behaves correctly: it **fails closed** (recovery refuses with `KR_NOT_LOADED`, and the site never serves an unverified generation). The journey asserts both the blocker and the fail-closed state.

Fix options are for the B01/B03/B04 owners:
- (a) exclusion-independent re-derivation over the release's verified records;
- (b) B01 keeps withdrawn copies materialised but not servable, with exclusions enforced at the response boundary as the architecture specifies;
- (c) the architecture's site rebuild path for cheap accelerators (ACTIVE_AFTER_LOCAL_REBUILD).

**Not demonstrated because of this blocker:**
- serving after restore: identical responses, E1 and E2 enforced at the response boundary after restore, and rollback after a re-import.

The journey code for those checks is present and runs unchanged once staging succeeds:
- `restored_site_serves_identically` (normalised bodies of 33 requests);
- `exclusion_e1_intact_after_restore` and `exclusion_e2_intact_after_restore`;
- `rollback_to_release_not_retained_refused`;
- `rollback_after_reimport`;
- `rollback_cannot_resurrect_excluded_items`.

The file-level suite (`SiteBackupRestoreTests`, B06 fixture site) does demonstrate the full path:
- restore, then recover, giving the journal-head views;
- publication rows reconciled;
- the latest exclusion sequence applied;
- rollback to a release that is not retained is refused.

**Timings (ms; CI; fixture scale; no target is set):**

| Step | Linux | Windows |
| --- | --- | --- |
| install site A | 1340 | 2849 |
| backup | 94 | 417 |
| restore command | 358 | 1239 |
| re-import, stage attempt and recover attempt | 865 | 1233 |

## 3. Probe matrices

**Database (`SiteDatabaseSetup.ProbeAsync`).** 50 rows on site A in the journey, all ok. They combine catalogue checks with real attempts as each role inside a rolled-back transaction:

- **Every role and PUBLIC:** no CREATE on `public`, no TEMPORARY, no CREATE on the database. PUBLIC also has no CONNECT.
- **Role attributes:** every role is NOSUPERUSER, NOCREATEROLE, NOCREATEDB, NOREPLICATION, NOBYPASSRLS and NOINHERIT, with no role memberships.
- **The `site` schema:**
  - the loader has no USAGE;
  - the web role has USAGE but no CREATE;
  - the backup role has no CREATE, can SELECT and cannot DELETE;
  - the web role can SELECT and cannot DROP;
  - PUBLIC has no USAGE.
- **The `knowledge` schema:** the loader has no USAGE; the web role has no CREATE and cannot replace a view.
- **The staging schema:** the loader has no CREATE on `kr_<n>_staging`.
- **Real attempts by every role (all refused):** CREATE TABLE in public, CREATE TEMP TABLE, CREATE FUNCTION and CREATE SCHEMA.
- **Role switching:** SET ROLE to every other role is refused.

**Windows ACLs (`Test-MimamsaDevInstall.ps1`, run as each virtual account).**
- Each job reports its token name and SID, which equal `NT SERVICE\<name>` and the service SID.
- The web identity's 38 probes, write and read for each of 19 targets, all matched the expected matrix:
  - **Write allowed:** `activation-state`, `uploads`, `logs`, `scratch\web`.
  - **Write denied:** `application`, `site`, `generations`, `vault`, `journal`, `exclusions`, `activation-log`, `models`, `text_store`, `search_index`, `vectors`, `import`, `config`, `backup`, `scratch`.
  - **Read denied:** `backup` and `scratch` only.
- The activation identity writes every store and site-data root except `application` and `uploads` (the web writes Admin uploads; the activation/backup identity only reads them), and runs `install-preflight` as itself.
- Store roots are owned by `NT SERVICE\MimamsaActivation`, with inheritance disabled and no Everyone, Users or Authenticated Users entries.
- The firewall has exactly one Mimamsa inbound rule (TCP 443).
- A reinstall keeps the sentinels in site data. Uninstall removes the services, binaries and rule, and keeps the sentinels.
- Results are in the `s3c-windows` CI artifact.

## 4. Test counts

- **CI, `Mimamsa.Tests.Install`:** 72/72 passed on Linux and 72/72 on Windows. Breakdown:

  | Suite | Tests | What it covers |
  | --- | --- | --- |
  | PathSafety | 36 | 29 theory cases + 7 facts |
  | InstallLayout | 6 | |
  | BackupCrypto | 11 | |
  | SiteBackupRestore | 10 | file-level restore with the B06 journal and ExclusionStore |
  | InstalledRetention | 6 | configured limits 1, 2 and 3; pinned, recovery-target, sole and in-flight releases |
  | SiteDatabaseInstall | 2 | |
  | S3cRestoreJourney | 1 | gated; it runs inside the driver step |

  `Site_schema_backup_and_restore_onto_a_fresh_hardened_database` runs only where `MIMAMSA_PG_BIN` is set: the S3-C jobs, not app-ci.
- **Restore journey:** 59 checks per platform.
- **Local (Windows development host, bounded):** the Install suite and the database tests pass against disposable `c16s3c_` objects on the local cluster.
- **Existing suites on CI:**
  - `b1`: the full suite passes and includes the new tests.
  - `b1-windows`: 487 tests in the run on `a0e79fae`.
  - `cp1-slice` and `cp1-slice-windows`: pass.

## 5. Shared-file edits (minimal)

- `app/b1/src/Mimamsa.Core/Activation/ActivationCli.cs`, additive only:
  - a `--knowledge-rows` flag that selects `KnowledgeActivationDatabase` (kr_<n> promotion and `knowledge` views; the release sequence is read from `generation.json`);
  - when `ACTIVE` is absent after a restore, the CLI names the journal head (else the initial generation) for EnsureSchema, and `recover()` rewrites `ACTIVE`.

  Default behaviour is unchanged.
- `app/b1/src/Mimamsa.Activation/Program.cs`: routes the installer commands and `service-job`.
- `app/b1/src/Mimamsa.Activation/Mimamsa.Activation.csproj`: adds package `System.ServiceProcess.ServiceController` 10.0.15.
- No existing workflow, oracle, contract fixture or other stream's code was edited.

## 6. CI

| Workflow | Run id | Head | Result |
| --- | --- | --- | --- |
| (filled in on the final head; see the PR #88 body) | | | |

Earlier runs and the root-cause fixes they drove:

| Run | Failure | Fix |
| --- | --- | --- |
| 46104282119 | `runner` context in job env | moved to a step |
| 46104393359 | the journey's stale drill read the destroyed site's backup root | late backup kept on media |
| 46104845947 | client and server version mismatch (`transaction_timeout`) | refused up front; Linux server set to postgres:18 |
| 46104845947 | `CREATE SCHEMA public` already exists | pg_restore use-list |
| 46105222591 | the importer read a dangling `ACTIVE` | `ACTIVE` left absent until recover |
| 46106150016 | the B01×B03 blocker above | recorded and asserted |
| 46107341206 | PowerShell `$r` shadowed `$R` (names are case-insensitive) | renamed |

## 7. Open gates

| Gate | Scope |
| --- | --- |
| **S3C-B01-B03-REIMPORT-AFTER-EXCLUSION** (§2) | Blocks serving after a real restore and any import after an overlapping exclusion. Cross-stream decision needed. |
| OG-8 / FG-REAL-RESTORE-TEST | The restore on the owner's actual offline Windows host, and power-loss drills. |
| OG-1 | Target hardware and edition. The CI runner is Windows Server 2025, so the `windows-latest` results do not stand for Windows 11 Home. |
| OG-2 | Production keys and the Authenticode certificate. |
| OG-3 | Operational migration, backup media custody and policy. |
| Web role not in use | The web process still connects as the database **owner**, because the application runs DDL at start-up. The `<p>web` grants are probed but not yet used by the process. |
| Legacy tables in backups | During the I-3 compatibility window, backups also include the legacy `public` site tables (accelerators excluded), because the application still runs on `public`. |
| Prune and `kr_` schemas | Prune removes generations but not their `kr_<n>` schemas. |
| Preflight scope | The activation-time preflight (B06 `DriveDiskProbe`) measures only the site-root volume. The install preflight is per volume. |
| Relocation | Directories derived from the site root (vault, generations, journal, exclusions, ...) cannot yet be relocated separately. |
| Hard links | Not detected by the path checks. Symlinks, junctions and other reparse points are. |
