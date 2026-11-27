# C16 Tranche B implementation plan: importer, central build pipeline, release components, offline installation

- **Status:** proposed plan, for independent review. Planning only: **no application code is written or changed by this document**.
- **Target:** Mimamsa Knowledge Release 1 (**MKR-1**), built centrally and installed on an offline Windows site that consumes a pre-populated PostgreSQL and prebuilt stores.
- **Base:** `legal-knowledge/v2.5-staging` at `28cd346d` (PR #80 merged: persistent text store, ADR-0008, and evaluator optimisation).
- **Normative inputs (read only, not reopened).** The C16 contract and release architecture in PR #77, branch `claude/c16-contract`, head `80527921`. This head includes the C02-R2 validator fix: the selected image occurrence is validated directly, not the first occurrence with the same hash.
  - Documents in `docs/architecture/c16/`:
    - [C16_CORPUS_INTEGRATION_CONTRACT.md](C16_CORPUS_INTEGRATION_CONTRACT.md), cited below as **contract §n**;
    - [C16_COMPATIBILITY_MATRIX.md](C16_COMPATIBILITY_MATRIX.md);
    - [C16_PRODUCER_REQUIREMENTS.md](C16_PRODUCER_REQUIREMENTS.md);
    - [C16_CONSUMER_REQUIREMENTS.md](C16_CONSUMER_REQUIREMENTS.md), cited below as **I1–I9, C1–C9, G1–G7**;
    - [C16_KNOWLEDGE_RELEASE_ARCHITECTURE.md](C16_KNOWLEDGE_RELEASE_ARCHITECTURE.md), cited below as **arch §n**.
  - Schemas: `app/contract/schemas/c16/`.
  - Reference code: `app/contract/mimamsa_contract/c16/` (`canonical.py`, `rules.py`, `evidence.py`, `adapters.py`, `activation.py`).

  These links resolve once PR #77 merges. Until then, read them with `git show origin/claude/c16-contract:<path>`.
- **Carried-forward gates:** PR #80 report `app/b1/evidence/c16_integration/C16A_COMPLETION_REPORT.md` §4. They are numbered **CG-1 … CG-7** below.
- **Producer:** Codex, PR #76, branch `codex/c16-local-corpus-reconciliation`, head `7ba91ec4`. It was read with `git show` only. The plan treats Codex as an independent producer and never depends on the timing of its OCR work.

---

## 1. Objectives and non-goals

### 1.1 Objectives

| # | Objective | Done when |
| --- | --- | --- |
| O-1 | **Site importer for `mimamsa-corpus-contract/2.0`.** It consumes a signed v1 bundle carrying a strict C16 exchange (contract §9.3 and §13) and produces a B1 generation with `corpus-v2/` materialised (I1–I9) | FG-SITE-IMPORTER and FG-RECEIPTS closed (§2.4) |
| O-2 | **Centralised knowledge build.** One deterministic, per-stage resumable command turns pinned inputs into a signed-ready MKR-1 knowledge release. OCR, text, lexical index, text store, embeddings, graph and knowledge rows are all built centrally | B02 reproducibility test passes (two builds give identical `SHA256SUMS`, with vectors handled as in §5.5) |
| O-3 | **Prebuilt release components.** KNOWLEDGE_ROWS, TEXT_STORE (ADR-0008), LEXICAL_INDEX (ADR-0007), VECTOR_PACK, GRAPH, the integrity and admission registers, and a signed manifest with `SHA256SUMS` and the component inventory (arch §3–§5) | A dev-signed MKR-1 activates as **ACTIVE_FULL** on a clean site with no OCR, no corpus embedding and no graph rebuild |
| O-4 | **Offline installation architecture on Windows.** Four separate releases (application, knowledge, intelligence/model, local site data; arch §2), activation through the journal, rollback, retention, backup and restore | FG-JOURNAL-DURABILITY, FG-DISK-PREFLIGHT and FG-REAL-RESTORE-TEST closed on an actual offline Windows host |
| O-5 | **Close the carried-forward gates** CG-1 … CG-7 with real-corpus evidence | B09 evidence pack accepted |

**Invariant.** An ordinary deployment never runs full-corpus OCR, full-corpus embedding, or an unconditional graph rebuild (arch §1 and §9, `heavy_compute_on_site`). The site may still rebuild locally, on a **failed-accelerator path only**, the components the architecture classes as cheap: KNOWLEDGE_ROWS, GRAPH, LEXICAL_INDEX and TEXT_STORE. Those outcomes are recorded as ACTIVE_AFTER_LOCAL_REBUILD.

### 1.2 Non-goals (binding on every work package)

| # | Not in Tranche B |
| --- | --- |
| N-1 | **Production activation.** Every activation in Tranche B happens on development, CI or test sites, with development-signed releases (`--mode development`). Production mode keeps refusing development keys (`SIGNATURE_DEV_KEY_IN_PRODUCTION`) |
| N-2 | **Legal authority promotion.** Admission, activation and publication remain `publication_effect=NONE` and `legal_effect=NONE` (contract P14). No relationship, anchor or edge is raised by any tool in this plan |
| N-3 | **AUTH-LEDGER change.** The ledger stays at v0. `legally_validated` stays refused (`LEDGER_V0_NO_APPROVAL`) and rule packs stay refused (`KR_RULE_PACK_LEDGER_V0`) |
| N-4 | **New paid infrastructure.** The plan uses the owner's existing machines, the existing GitHub Actions runners (including `windows-latest`, already used by `app-windows-poc.yml`), the existing private HF dataset under ADR-0004, and free or open-source tooling only |
| N-5 | **Trust-key or trust-list changes** without owner authorisation. In particular, no `model`-purpose key and no change to `trust.py` purposes in operational trust lists (FG-MODEL-TRUST-PURPOSE; B10 is blocked) |
| N-6 | **Contract redesign.** The decisions in PR #77 stand. The only contract additions proposed are additive minor items (§2.5, I-1), and they go through contract §12 change control |
| N-7 | **Corpus admission decisions.** The plan never sets a gate to PASS, never writes an admission, and never touches Codex's worktree, `E:\Judgements`, or Codex's evidence root |
| N-8 | **Changing the defaults** `Mimamsa:Text:Store=memory` and `Mimamsa:Search:Engine=memory` (ADR-0007 and ADR-0008 status: owner authorisation). The installer **supports** `disk` and the B09 runs use it; flipping the shipped default is owner decision OD-7 |
| N-9 | **Changing the acceptance oracles** (retrieval oracle, contract fixtures, the activation reference tests, importer DA cases). See §5.6 |
| N-10 | **Local Admin upload processing** (CONTINUOUS_DOCUMENT_INGESTION). Tranche B only guarantees coexistence: releases never write `site` data, and local uploads survive activation, rollback and restore (arch §10) |

---

## 2. Component architecture

### 2.1 Two hosts, four releases

| Host | Role | Network | Runs |
| --- | --- | --- | --- |
| **Central build host** (owner's existing machine; OD-3) | Builds MKR-1 knowledge releases and, later, intelligence releases | Online (HF and git) during the fetch stage only; every later stage runs with no network use | B02 pipeline: fetch → validate → text → reference import → accelerators → assemble → verify-as-site. The owner signs `SHA256SUMS` **offline** (arch §11) |
| **Offline site** (Windows; reference topology in SECURITY_AND_DEPLOYMENT_ARCHITECTURE §2) | Serves users | None. Releases arrive on removable media in `D:\Mimamsa\import\` | Installer (application release), release-import service (verify and stage), activation tool (journal), web service, backup task |

The four releases follow arch §2 and are unchanged.

| Release | Built by | Signed by | Installed by | Tranche B package |
| --- | --- | --- | --- | --- |
| Application | CI (`dotnet publish`, Python wheels, web assets) packaged on the build host | Authenticode (OD-13); a test certificate in Tranche B | Installer (B07) | B07 |
| Knowledge (MKR-1) | B02 | Owner Ed25519, purpose `release`; development key in Tranche B | release-import (B01) plus activation (B06) | B01–B06 |
| Intelligence / model | B10 | Owner Ed25519, purpose `model` (**blocked**: FG-MODEL-TRUST-PURPOSE) | release-import plus a MODELS journal transaction | B10 |
| Local site data | Site only | Never signed | Never written by a release; backed up (B08) | B07, B08 |

### 2.2 Data flow: producer exchange to activated generation

```
PRODUCERS (independent)                          CENTRAL BUILD HOST (B02, one command: mkr build --spec <spec>)
 Codex local collection ── strict C16 exchange ─┐  S0 spec        pinned inputs: GENERATION.json sha256s, HF 40-hex revisions,
   (GENERATION.json + JSONL, preserved to HF    │                  git commits, register sha256, contract version, models, tools
    at a pinned revision, ADR-0004)             │  S1 fetch       HF revisions -> content-addressed cache; re-hash everything
 HF canonical corpus (v1 path, build_sample     ├─►S2 validate    v1 validator; rules.exchange_issues(mode="strict"); register
   mapping; v7 re-derived to [[page N]])        │  S3 text        verify producer derivatives; central OCR/re-derivation only for
 Contract fixtures / synthetic producer ────────┘                 pinned v1-path items (never promotes a C16 held item)
   (development and CI)                            S4 bundle      v1 bundle: data/, corpus-v2/, originals/, text/, research/, registers/
                                                   S5 ref-import  B01 importer into a scratch REFERENCE SITE -> generation identical to a site's
                                                   S6 accelerate  .NET mimamsa-knowledge, same code as the site, against the reference generation:
                                                                  rows | graph | text-store | search-index | vectors (embedding: the only heavy step)
                                                   S7 assemble    KNOWLEDGE_RELEASE.json, accounting, inventory, SHA256SUMS
                                                                  (rules._release_manifest + component_inventory_issues)
                                                   S8 sign        owner offline (dev key in Tranche B)
                                                   S9 verify      fresh scratch site: B01 + B03 + B04 + B06 must reach ACTIVE_FULL
                                                          │
                                             removable media (signed bundle)
                                                          ▼
OFFLINE SITE
 release-import service (Python, NT SERVICE\MimamsaImport)                 activation tool (.NET, same identity)      web service (.NET)
  arch §8.1 steps 1-4:                                                      arch §8.1 steps 5-6, §8.2:                 serves the pinned generation
  1 copy to work folder; signature; checksums; v1 validator;                5 measured disk preflight (FG-DISK-PREFLIGHT)  · SWITCHING -> 503 for new requests
    MKR-1 rules; inventory vs SHA256SUMS; strict C16 (I1, I2)               6 smoke test; rename staging into place        · in-flight pinned requests drain
  2 disk budget (declared sizes)                                            journal: BEGIN -> DECIDED -> DB_APPLIED ->     · at OPEN: load the new generation,
  3 vault write-once; generation .tmp; corpus-v2/ (I3-I6);                    POINTER_WRITTEN -> EXCLUSIONS_APPLIED ->       release the old one once unpinned
    receipts resolved (FG-RECEIPTS)                                           LOGGED -> OPEN (FG-JOURNAL-DURABILITY)       · every response filtered by the
  4 components: result digests; accelerators verified into staging         recover() at every start, before serving        CURRENT exclusion state
    (rows -> kr_<n>_staging by mimamsa_kr_loader, FG-ROW-LOADER;           retention / prune (D4, D6)
     graph, index, text store, vectors -> .building-* / temp copy)
```

### 2.3 Process and language placement

The plan keeps the ADR-0005 split: an ASP.NET Core web layer and Python workers, with the release importer in Python. Anything that must run **the same code as the serving app** is placed in .NET.

| Concern | Placement | Why |
| --- | --- | --- |
| Bundle verification, vault, generation materialisation, C16 strict validation, receipt resolution | **Python**: `app/importer` extended, reusing `app/contract` | Existing reviewed importer (steps 0–5, DA cases); `rules.exchange_issues` is the reference validator |
| Knowledge-row derivation, row writer, restricted-role row loader | **.NET**: new library `app/b1/src/Mimamsa.Knowledge` | Rows must be re-derived on site by the code that serves them (`ROWS_REDERIVE_COMPARE`); Npgsql binary COPY is already a dependency |
| Accelerator build and verification (text store, index, graph, vectors) | **.NET**: `Mimamsa.Knowledge`, reusing `Mimamsa.Core` (TextStore, IndexStore, GraphBuilder, GraphStore) and `Mimamsa.Hybrid` (VectorStore, E5Embedder) | Prebuilt accelerators are verified by sampled re-derivation with the **site's** builder. Building them centrally with the same assembly removes builder skew |
| Activation journal, recovery, rollback, retention, preflight | **.NET**: `Mimamsa.Knowledge/Activation` plus the CLI `app/b1/src/Mimamsa.KnowledgeTool` (`mimamsa-knowledge`) | It must coordinate with the .NET web process (pins, SWITCHING, response boundary) and PostgreSQL views |
| Build orchestration | **Python**: new package `app/knowledge_build` (`python -m mimamsa_kbuild`) | It drives fetch, the v1 bundle tools (`build_sample.py`, `devbundle.write_bundle`) and the importer, and shells out to `mimamsa-knowledge` for .NET stages |
| Installer, service accounts, ACLs, backup and restore scripts | `app/installer/` (PowerShell plus a free MSI toolchain; reuse `app/poc/p1_hosting/windows/*.ps1`) | P6 (offline installer) is PENDING in ADR-0005; B07 delivers it |

### 2.4 Where each gate is enforced

| Gate | Enforced in | Mechanism | Closing evidence | WP |
| --- | --- | --- | --- | --- |
| **FG-SITE-IMPORTER** | release-import (Python) | arch §8.1 steps 1–4; I1–I9; refuse the whole bundle on any error (I2) | Adversarial import suite (§5.2) on Linux and Windows CI; real-corpus import in B09 | B01 (with B03, B04, B06) |
| **FG-RECEIPTS** | release-import, inside I2 | Typed receipt **content** resolved per gate. The artefact is found by `receipt_sha256` among the signed files, parsed against a typed schema, and its gate, copy, derivative, rule, config, register and outcome compared field by field with the admission's receipt **and** with site-recomputable facts. Hash existence alone never passes (PR #77 final review) | Negative receipts N-R01 … N-R12 (B01) | B01 |
| **FG-ROW-LOADER** | activation tool (.NET), role `mimamsa_kr_loader` | arch §7 steps 1–6: rows not SQL; typed reader; isolated `kr_<n>_staging`; parameterised COPY; recount, `rows_sha256` and re-derive-compare; drop on failure | The eight arch §7 failure tests, each proving `site` and the active `kr_` schema byte-identical by ordered dumps | B03 |
| **FG-JOURNAL-DURABILITY** | activation tool plus web service | Append-only journal with `FlushFileBuffers` per entry (arch §8.2); single-writer lock; recovery before serving | Crash injection at every boundary with real process kills; concurrency tests; differential conformance to `activation.py` (§5.3); repeated on the offline host | B06 (proof on host in B07 and B09) |
| **FG-CALIBRATED-SAMPLES** | site verification of accelerators | Deterministic samples (postings re-derivation, query parity, graph rebuild parity, vector spot re-embed) whose **sizes and tolerances come from measurement** (decision O4) | Calibration report from real-corpus runs, accepted by the owner (OD-12) | B04 (mechanism), B09 (calibration) |
| **FG-REAL-RESTORE-TEST** | backup task and restore procedure | arch §10 restore steps 1–6 | Full restore on an actual offline Windows host, plus corruption drills | B08 |
| **FG-DISK-PREFLIGHT** | activation tool, step 5 | Measured bytes still to materialise, plus the configurable headroom fraction, compared with measured free space while the retained set stays on disk; refusal is recorded in the activation record `preflight` | Refusal and acceptance runs on real releases and a filled volume | B07 (mechanism), B09 (real releases) |
| **FG-MODEL-TRUST-PURPOSE** | trust list, release-import | `signing_purpose: model` verified against an owner-authorised `model` key; refused until one exists | Blocked on OD-1 | B10 |
| CG-1 real full-corpus HTTP and concurrency | web service | Load harness over the real corpus | B09 report | B09 |
| CG-2 memory and disk budget | web service, activation tool | Measured heap, working set, stores, vectors and PostgreSQL; two generations open during a switch | B09 report; preflight inputs | B09 (B07) |
| CG-3 store-root ownership | installer | Roots outside the site directory, owned by the service identity, readers not writers, ACLs recorded | ACL verification script on the host | B07 |
| CG-4 generation lifecycle | web service | Pinning, draining, closing the old store after the last unpin | B06 concurrency tests | B06 |
| CG-5 retention | activation tool | Active plus two previous **distinct** verified releases (D4); never prune protected generations (D6) | `Site.previous_distinct` and `Site.protected` conformance | B06 |
| CG-6 crash-safe rollback | activation tool | Rollback is a journal transaction (arch §8.4); exclusions are monotone | Crash during rollback at every boundary; no resurrection | B06, B08 |
| CG-7 calibrated accelerator checks | as FG-CALIBRATED-SAMPLES | | | B04, B09 |

### 2.5 Interpretations to confirm at checkpoint review

These are implementation readings of the accepted contract. None changes a decision. Each is listed so the reviewer can reject it before code depends on it.

| # | Point | Proposed reading |
| --- | --- | --- |
| I-1 | **FG-RECEIPTS needs a typed artefact.** The contract types the receipt *reference* (`$defs/receipt`) but not the artefact it hashes | Add an optional, additive `GATE_RECEIPT_ARTEFACT_SCHEMA.json` as `mimamsa-corpus-contract/2.1`, under contract §12 change control, with independent review by someone who is neither producer nor consumer author. Artefacts travel at `registers/receipts/<receipt_sha256>.json`, owned by the ADMISSION_REGISTER component (namespace `registers/`, arch §3). They are canonical JSON with `receipt_kind`, `gate_id`, `subject_sha256`, `doc_id`, `corpus_generation_id`, `derivative_sha256`, `rule_id`, `rule_version`, `config_sha256`, `register_sha256`, `outcome` and a kind-specific `payload` (for example HASH_REDOWNLOAD: HF repo, revision, path and measured sha256; REGISTER_CHECK: register sha256 and the matched-fields count). Codex adopts it at the producer's pace; until then, eligible admissions cannot pass the site gate (fail closed) |
| I-2 | **Graph rows versus KNOWLEDGE_ROWS.** Arch §3 places graph rows under `accelerators/graph/`, while arch §7 lists `graph_nodes` and `graph_edges` on the rows allowlist. `KR_PATH_OVERLAP` forbids one file in two components | The GRAPH component owns `accelerators/graph/graph_nodes.jsonl`, `graph_edges.jsonl` and the digest. It is loaded by the **same** allowlisted row loader (B03) into `kr_<n>_staging` and verified with GRAPH checks. KNOWLEDGE_ROWS owns the remaining seven tables under `accelerators/rows/` |
| I-3 | **Schemas `site`, `kr_<n>` and `knowledge`** (arch §7) do not exist today. Site tables (`app_users`, `app_sessions`, `audit_log`, `withdrawals`, `serving_policy`, `studio_*`, `credit_*`) and `graph_*` live in the default schema, with `generation_id` columns | An **application-release** migration (B07) moves site tables into `site` and drops the shared `graph_*` tables for `kr_<n>` per release. GraphStore queries go through `knowledge` views. `graph_edge_reviews` rows come from the separate audited review-import step (G3) into `kr_<n>` |
| I-4 | **Activation ownership.** The architecture names one journal writer and a service that enters SWITCHING | The activation tool (import service identity, DB role `mimamsa_activator` with view-replacement rights on schema `knowledge` only) is the single journal writer. The single-writer lock is a PostgreSQL advisory lock plus an exclusive journal file lock, also taken by exclusion acceptance. The web process is a **participant**: it is signalled through a local control channel to enter SWITCHING (503 for new requests), acknowledges once admission has stopped, keeps pinned requests on the old `AppServices`, and swaps at OPEN. After a crash, the web process refuses to serve until the journal shows no in-flight transaction and its loaded generation equals the journal head (§8.2 "refuses service until it finishes") |
| I-5 | **Documents with v1 records and no C16 sidecar** (the HF canonical corpus through `build_sample.py`) | Served under the unchanged v1 rules (contract §12: "absent C16 data means today's behaviour", C1). I7 governs **C16 copies**. MKR-1 can therefore carry the v1-path canonical corpus and C16 local items side by side. Both are register-checked, and both are AND-gated by the existing eligibility |
| I-6 | **The .NET app does not read the signed ExclusionStore yet** (PolicyStore comment, conflict X7) | B06 adds a read-only .NET reader of the Python ExclusionStore's latest effective state: signature-verified, sequence-pinned and fail-closed, as `servable()` is. Pins capture its sequence |

### 2.6 Producer handoff (Codex)

The handoff is an **interface, not a date**. Tranche B never waits on Codex.

| Item | Producer delivers (C16_PRODUCER_REQUIREMENTS §1–§5) | Central build consumes |
| --- | --- | --- |
| Exchange | A strict exchange directory: `GENERATION.json`, `identities`, `anchors`, `relationships`, `taxonomy`, `admissions` and, when bindings exist, `reviewed_records` JSONL, plus derivatives and image OCR derivatives | Pinned by `GENERATION.json` sha256 and HF revision in the build spec (S0) |
| Preservation | Preserved to the HF dataset under ADR-0004: versioned, re-download verified, commit id recorded in git | S1 fetches by revision and re-hashes; never from Codex's worktree or `E:\` paths |
| Validation proof | `exchange_issues(mode="strict", auth_ledger_version=0, register=…)` with no errors; determinism re-run; coverage report (producer §3) | S2 re-runs strict validation; it never trusts the producer's report |
| Receipts | Gate receipt artefacts (I-1) once 2.1 is accepted | B01 resolves them. Without them no admission is site-eligible, and the release still builds (held items carried, not served) |
| Held items | Word screenshots still in OCR are HELD_OCR_REQUIRED with `embedded_images` QUEUED | Carried as identities, never served or indexed (I7). A later producer generation with new admission revisions arrives as a new release |

**Development without Codex.** B02 and B01 run against:
- (a) the contract fixtures (`app/contract/fixtures/c16/positive`, `negative`);
- (b) a **synthetic full-shape producer exchange**: a new generator beside `build_fixtures.py`, deterministic and covering every document class in contract §5 at a configurable scale;
- (c) `adapters.from_pr76_inventory` output on a synthetic inventory. That output is a **partial** exchange and must be refused by S2 and by B01, which is itself a test.

The real Codex generation is a spec-file swap.

---

## 3. Work packages

Sizes are rough engineering-effort estimates, not commitments: **S** is up to about 3 days, **M** about 1–2 weeks, **L** about 2–4 weeks. "Depends" lists hard dependencies only.

### B01 Site importer for contract 2.0 (strict, partial and signed-import validation; receipts)

- **Inputs:**
  - a signed v1 bundle with `corpus-v2/` and `GENERATION.json` (contract §13);
  - the site trust list, register and exclusion store;
  - the active generation.
- **Outputs:**
  - `generations/<id>/corpus-v2/*.jsonl` and `generation.json` `materialized.corpus_v2` (I5);
  - an import report with per-item outcomes (`C16_SUBJECT_NOT_SERVABLE` counts, I6);
  - a resolved-receipts register in the generation;
  - a refusal leaves the site untouched.
- **Reuses:**
  - `app/importer/mimamsa_importer/importer.py` (steps 0–5, crash points, quarantine, latch);
  - `mimamsa_contract` (`bundle.py`, `trust.py`, `restricted.py`, `exclusions.py`);
  - `mimamsa_contract.c16.rules.exchange_issues`, `receipt_resolution_issues` as the starting point, `evidence.verify_anchor_bytes`;
  - PR #76's `safe_archive_member` rules, re-implemented in the importer (never imported from Codex's branch).
- **Work:**
  1. Strict-only import (I2). Partial mode is refused by construction, with a test.
  2. v1 cross-check (I3).
  3. Importer byte checks (I4): DOCX image hashes through safe zip reading, page counts, and reconstructed-page mapping hashes where page images are bundled.
  4. Materialisation inside the temporary generation before the rename (I5).
  5. Servable filter (I6) and effective-admission head (I7).
  6. Review-binding resolution against bundled `reviewed_records` (I9).
  7. **FG-RECEIPTS** typed resolution (I-1): parse the artefact against its schema; require `gate_id`, `subject_sha256`, `doc_id`, generation, `derivative_sha256`, `rule_id@version`, `config_sha256` and `outcome` to equal the admission's receipt and gate result; `register_sha256` must equal `GENERATION.json` and the site's pinned register. Where the site can recompute the fact, it does and compares: G01 hash, G02 format, G03 register scan, G05 and G10 schema validity, G06 derivative re-hash and coverage, G07 image inventory. The rest (G04, G08, G09) is checked for typed consistency and binding only, and recorded as asserted-and-bound, never as site-verified.
  8. Independent recomputation of label-based relationships from `classification_provenance` with the pinned rules version (`adapters.classify_path`, rules 1.2). A mismatch is refused, so a producer reading bare `AFT` as the Act (D2) or `AR` other than Army Rules 1954 in the local collection (D1) cannot pass.
  9. Unknown contract major or record kind refused (consumer §4).
- **Acceptance tests:**
  - every positive fixture imports;
  - every negative fixture N01–N54 and X01–X35 refuses the **whole bundle**, with site state compared byte for byte before and after;
  - partial exchange refused;
  - new receipt negatives:
    - N-R01 artefact missing;
    - N-R02 hash matches but the kind differs;
    - N-R03 another copy;
    - N-R04 another derivative;
    - N-R05 stale register revision;
    - N-R06 outcome FAIL under a PASS gate;
    - N-R07 rule version differs;
    - N-R08 config hash differs;
    - N-R09 artefact for another gate reused;
    - N-R10 HASH_REDOWNLOAD whose measured hash is not the copy's;
    - N-R11 an artefact outside `registers/receipts/`;
    - N-R12 an artefact not in the component inventory;
  - adversarial AR/AFT reading;
  - crash at each existing importer crash point, with C16 files present;
  - runs on Linux CI (`importer` job) and on Windows (`windows-latest`).
- **Closes:** FG-RECEIPTS. FG-SITE-IMPORTER is closed jointly with B03, B04 and B06, end to end in B09.
- **Risks:**
  - I-1 needs contract 2.1 review and producer adoption. Mitigation: fail closed, so the importer ships before Codex adopts.
  - Strict validation cost at full scale is unmeasured. Measure it in B09 and stream the JSONL.
  - Divergence between `rules.py` and the importer. Mitigation: the importer **calls** the reference validator, never re-implements it.
- **Size:** L. **Depends on:** the PR #77 freeze and merge (OD-0) for the merge; development can pin `80527921`.

### B02 Central build pipeline (deterministic, reproducible, one command, per-stage resumable)

- **Inputs:** a build spec (JSON, committed in git) pinning:
  - producer `GENERATION.json` sha256 and HF revisions (decision Q8: several inputs allowed);
  - git commits;
  - the register sha256;
  - the contract version;
  - model files by sha256 (`app/b1/hybrid/MODEL_MANIFEST.json`);
  - tool versions;
  - `release_id`, `release_sequence` and base;
  - a pinned build time (no wall clock in any output).
- **Outputs:** an unsigned MKR-1 bundle directory ready for S8 signing, plus a build record: per-stage input and output digests, tool versions, and timings for preflight inputs.
- **Reuses:**
  - `app/b1/build/build_sample.py` (HF meta → v1 records);
  - `mimamsa_contract.devbundle.write_bundle` (bundle and `SHA256SUMS`; development signing in Tranche B);
  - `app/importer` (S5 reference import);
  - `adapters.from_v7_record` for the v7 re-derivation path;
  - `canonical.dumps_jsonl`;
  - B03 and B04 tools for S6.
- **Work:**
  - The stages S0–S9 of §2.2, each with a receipt `{stage, input_digest, output_digest, tool}` under `build/<build_id>/<stage>/`.
  - **Resume rule:** a stage reruns only if its input digest changed or its output fails re-verification. A killed stage leaves only a `.partial` directory, discarded on restart.
  - The single entry point is `python -m mimamsa_kbuild build --spec <file>`, plus `--from <stage>` and `--dry-run`. Dry run lists what would be fetched or built, with counts per source (CLAUDE.md crawler dry-run spirit).
  - Network use is confined to S1; later stages run with network access disabled for the process where the OS allows, and are tested offline.
  - **S3 rule:** the central build never promotes a held C16 item. For v1-path items it may re-derive `[[page N]]` derivatives (the v7 caveat in the compatibility matrix §7) with a pinned `ocr_config`. OCR remains Codex's responsibility for the local collection (producer R3 and R4).
- **Acceptance tests:**
  - **Reproducibility:** two clean builds from the same spec on the same host give byte-identical `SHA256SUMS`, apart from VECTOR_PACK if measurement shows ONNX non-determinism (§5.5). A third build on a second machine, if available, is reported.
  - Kill at each stage boundary and mid-stage, then resume: identical output.
  - A changed pin re-runs exactly the dependent stages.
  - A partial exchange input is refused at S2.
  - S9 reaches ACTIVE_FULL on a scratch site.
  - The build record lists every input revision.
  - The spec and record validate.
- **Closes:** O-2. It supplies the real releases for FG-DISK-PREFLIGHT and FG-CALIBRATED-SAMPLES in B09.
- **Risks:**
  - Build-host disk and time at full scale are **unmeasured**. Measure them during the first real-corpus S6.
  - The reference-site generation must equal a site's generation byte for byte. If `generation.json` carries site-specific values, accelerator source digests diverge; this is tested explicitly.
  - HF availability. Mitigation: a content-addressed cache with re-hash.
  - Any HF write of build artefacts follows ADR-0004 (OD-14).
- **Size:** L. **Depends on:** B01 (S5); B03, B04 and B05 (S6–S7) to complete; the skeleton can start at once.

### B03 KNOWLEDGE_ROWS writer and the site restricted-role loader

- **Inputs:** an imported generation (records, `corpus-v2/`, research aids); the application's knowledge schema version (DDL plus allowlist with column types).
- **Outputs:**
  - **Central:** `accelerators/rows/<table>.jsonl`, canonical, in primary-key order, with per-table `rows_sha256` and the component digest (arch §5). Tables: `taxonomy_nodes`, `corpus_relationships`, `evidence_anchors`, `document_identities`, `corpus_admissions`, `candidates`, `provision_versions`, plus GRAPH's two tables under I-2.
  - **Site:** a populated, verified `kr_<n>_staging`, renamed or adopted as `kr_<n>` at DB_APPLIED.
- **Reuses:**
  - `GraphStore` DDL (moved into `kr_<n>`);
  - Npgsql (already referenced);
  - canonical JSON rules (`canonical.py`), ported to .NET with a cross-language golden test;
  - `PolicyStore` and `Identity` patterns for the role setup.
- **Work:**
  - `KnowledgeRows.Derive(generation)` is the **one** derivation used centrally (writer) and on site (`ROWS_REDERIVE_COMPARE`).
  - Typed per-table readers: unknown table or column, missing column, type error, oversized value or duplicate primary key rejects the component.
  - Application DDL creates `kr_<n>_staging`, owned for load by `mimamsa_kr_loader` (`NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS`): CREATE on that schema only, INSERT on its tables, no access to `site`, `knowledge` or other `kr_` schemas, no functions, triggers or rules.
  - Parameterised binary `COPY … FROM STDIN` into named allowlisted tables only.
  - Recount, recompute `rows_sha256` from an ordered canonical export, then re-derive-compare.
  - On any failure, drop the staging schema.
  - Schema migration I-3 (with B07).
- **Acceptance tests:** the eight arch §7 failure tests (unknown table, extra column, wrong type, duplicate key, count mismatch, digest mismatch, row not derivable, interrupted load). Each runs against a live PostgreSQL in CI and on Windows, and asserts `site` and the active `kr_` schema byte-identical by ordered dumps. In addition:
  - privilege probes: the loader role cannot touch `site`, create a function or trigger, or `SET ROLE`;
  - a hostile row value (SQL text, NUL, non-NFC, oversized) is inert or rejected;
  - the .NET canonical bytes equal Python `canonical.dumps_jsonl` on the fixture corpus;
  - N38 and N39 stay refused.
- **Closes:** FG-ROW-LOADER; the KNOWLEDGE_ROWS part of O-3.
- **Risks:**
  - Loading time and PostgreSQL size at full scale are unmeasured (B09).
  - Per-release `kr_<n>` schemas multiply disk use (O3 working default, "subject to disk and restore tests"). Measure in B09 and report to the owner; never change the decision silently.
  - Interaction with existing queries that assume the default schema (I-3).
- **Size:** L. **Depends on:** B01 (generation with `corpus-v2/`). It can start on contract fixtures immediately.

### B04 Prebuilt TEXT_STORE, lexical index, vectors and graph: packaging and kind-specific verification

- **Inputs:** a reference generation (central) or a staged generation (site); installed model files; B03 rows for the graph.
- **Outputs:**
  - **Central:**
    - `accelerators/text-store/` (`text.sqlite` and `MANIFEST.json`, `mimamsa-text-store/1`);
    - `accelerators/search-index/` (`search.sqlite` and `MANIFEST.json`);
    - `accelerators/vectors/<model>.mimvec` (MIMVEC01);
    - `accelerators/graph/` (rows and digest);
    - for each, `result_digest`, `source_digest`, `disk_budget_bytes` and the `verify` set.
  - **Site:** a per-component verification outcome (VERIFIED_USED, REBUILT_LOCALLY or DEGRADED) for the activation record.
- **Reuses:**
  - `TextStore.cs` (`DiskTextStore.Bind`, build, manifest, quarantine, KeepPrevious);
  - `IndexStore.cs`, `SqlitePostingTable`, `ForwardCache` (incremental local build);
  - `VectorStore.cs` (trailer, `Key`), `DenseIndex.cs`, `E5Embedder.cs`;
  - `GraphBuilder.cs`, `GraphStore.Digest` and `VerifyAsync`.
- **Work:**
  - **Adopt-prebuilt** open paths. A shipped directory is renamed into `text-store\<release_id>\` and `search-index\<release_id>\` only after the existing open checks (manifest, size, sha256, `quick_check`, format, generation, counts, source digest recomputed from the site's own verified generation), **plus**:
    - TEXT_STORE: `TEXT_STORE_BIND_EXACT` and `PAGE_HASH_ON_READ`, unchanged ADR-0008 behaviour.
    - LEXICAL_INDEX: `SAMPLED_POSTINGS_REDERIVE` (deterministic document sample re-tokenised and compared) and `SAMPLED_QUERY_PARITY` against the memory evaluator.
    - GRAPH: `GRAPH_DIGEST`, `GRAPH_STRUCTURAL_RECHECK` (endpoints exist, evidence anchors resolve to verified pages, builder-only verification values) and `SAMPLED_REBUILD_PARITY` with the app's `GraphBuilder` on a deterministic sample of source records.
    - VECTOR_PACK: `VECTOR_TRAILER`, `VECTOR_KEYS_RECOMPUTED` (every key recomputed from verified passage text and model sha256) and `VECTOR_SPOT_REEMBED` (deterministic stratified sample re-embedded on site, within the calibrated tolerance).
  - **Sample selection** is seeded from the release id and is deterministic. Sample sizes and tolerances are **configuration values with no defaults that pretend to be calibrated**: until B09 calibrates them, the configuration records `UNCALIBRATED` and an activation using them cannot be ACTIVE_FULL in production mode (fail closed).
  - **Embedding policy change** in `DenseIndex`: a site-mode switch that **never embeds the corpus**. Passages without a usable vector are served lexical-only and the outcome is ACTIVE_DEGRADED with Admin acknowledgement (arch §4). Query-time embedding of the user's query is unaffected. Local-upload embedding stays a separate, bounded, optional path (O4).
  - Failure paths follow arch §4: GRAPH, LEXICAL_INDEX and TEXT_STORE rebuild locally (ACTIVE_AFTER_LOCAL_REBUILD); VECTOR_PACK degrades to lexical (ACTIVE_DEGRADED); an authoritative failure refuses.
  - Central builders call the same code with `build` verbs in `mimamsa-knowledge`.
- **Acceptance tests:**
  - Per kind, a tampered accelerator **whose source digest still matches** must be caught by the correctness check (N43 behaviour at site level): flipped postings, a swapped vector for another passage, a graph edge with an unresolvable anchor, a text page byte change.
  - A mismatched builder version triggers a local rebuild with the outcome recorded.
  - A missing vector pack gives lexical-only service plus a degraded record.
  - The 10/14 and 12/14 retrieval oracle results are identical with the prebuilt index and store versus a site-built one.
  - Accelerators never surface an excluded item: an item withdrawn after the build is hidden in search, graph and text.
- **Closes:** TEXT_STORE, LEXICAL_INDEX, VECTOR_PACK and GRAPH of O-3; the mechanism half of FG-CALIBRATED-SAMPLES and CG-7.
- **Risks:**
  - Sampled checks cost site time. Measure in B09; that is the calibration input.
  - ONNX numeric drift across CPUs (§5.5).
  - GraphBuilder may depend on load order, breaking parity. Tested.
- **Size:** L. **Depends on:** B03 (graph rows), B01 (staged generation).

### B05 Signed knowledge release assembly: manifest, SHA256SUMS, inventory

- **Inputs:** the bundle tree from B02 S4 and B03/B04 outputs; the base release for a DELTA.
- **Outputs:**
  - `KNOWLEDGE_RELEASE.json` (MKR-1): components, signed file inventory, accounting, `declared_service_level`, `required_models`, `pending_future_gates`, `heavy_compute_on_site`, `signing_purpose: release`;
  - `RELEASE.json`, `CHANGES.json`, `SHA256SUMS`;
  - a detached signature (development key in Tranche B).
- **Reuses:**
  - `devbundle.write_bundle`, `bundle.py`;
  - `rules._release_manifest`, `component_inventory_issues`;
  - the schema `KNOWLEDGE_RELEASE_MANIFEST_SCHEMA.json`.
- **Work:**
  - The assembler computes every `result_digest` per arch §5 and the full-state digests for deltas.
  - It refuses to emit a manifest that fails the reference rules (`KR_*`).
  - `pending_future_gates` lists exactly the gates not yet closed **at build time**. It is read from a committed gate-status file, never hand-typed.
  - FULL transport first. DELTA support covers records and registers (additions and tombstones), originals and text (additions) and vectors (new keys); KNOWLEDGE_ROWS, GRAPH, LEXICAL_INDEX and TEXT_STORE are FULL-only (decision O1).
  - Owner signing procedure document: offline, `SHA256SUMS` only, never the build machine's disk unencrypted (SECURITY_AND_DEPLOYMENT_ARCHITECTURE §8.1).
- **Acceptance tests:**
  - the manifest validates against the schema and `_release_manifest`;
  - inventory against `SHA256SUMS`;
  - N23–N28, N37 and N40–N54 reproduced from assembler output by mutation;
  - a delta whose base is not active is refused at the site;
  - a FULL service claim without vectors is refused;
  - the signature covers every component file;
  - reserved namespaces cannot be emitted.
- **Closes:** the signed-manifest part of O-3.
- **Risks:** low. The rules exist. The risk is accounting drift between the assembler and the site; the site re-runs the same rules.
- **Size:** M. **Depends on:** B03 and B04 output formats (not their completion).

### B06 Site activation journal: durable implementation of `activation.py`, crash and recovery tests

- **Inputs:** a staged, verified generation from B01, B03 and B04; the ExclusionStore; the web service.
- **Outputs:**
  - `journal\` (append-only, one fsync per entry);
  - the pointer files `ACTIVE` and `MODELS_ACTIVE`;
  - RELEASE_ACTIVATION publication rows keyed by transaction;
  - `activation-log\` records (`KNOWLEDGE_ACTIVATION_RECORD_SCHEMA.json`, hash-chained);
  - views in `knowledge`.
- **Reuses:**
  - `activation.py` as the **executable specification**: steps BEGIN … OPEN, `recover`, `pin`, `respond`, `accept_exclusion`, `preflight`, `previous_distinct`, `protected`, `prune`, `restore`;
  - the importer's `_write_atomic` and fsync discipline (P8: NTFS durability without directory fsync);
  - `ServingState` (withdrawal fence), `Eligibility`, `DrainProbe.cs`;
  - `app/poc/p1_hosting/windows/smoke-and-recovery.ps1`.
- **Work:**
  - `ActivationJournal` in `Mimamsa.Knowledge`, with `FlushFileBuffers` per entry and a torn-tail-tolerant reader (a partial last line is treated as absent).
  - Transaction steps exactly as arch §8.2; `recover()` runs at every start of the activation tool and is awaited by the web service before it serves (I-4).
  - Single-writer lock (I-4), shared with exclusion acceptance.
  - Pins capture knowledge generation, model generation and exclusion sequence. The response boundary filters every response by the **current** exclusion state (I-6).
  - Generation lifecycle: the old `AppServices` stays alive until its last pin is released, then its stores close (CG-4).
  - Rollback is `action ROLLBACK` to a retained release.
  - Retention and prune run only while OPEN.
  - Scratch cleanup on OPEN, on abort and in recovery.
- **Acceptance tests:**
  - **Differential conformance.** A scenario corpus (JSON traces of actions and crash points) is run against `activation.py` and against the .NET implementation, and the observable state must be equal after each step: pointers, views, publication rows, log chain, exclusions, pins, retained set.
  - **Real process kills** (`TerminateProcess`) at each of the seven boundaries and inside each step, then restart; recovery is idempotent (run twice).
  - An exclusion arriving mid-switch.
  - Readers pinned before an exclusion never bypass it.
  - Rollback cannot resurrect an excluded item.
  - A MODELS switch interrupted after DB_APPLIED.
  - A transition refused while recovering or towards an unstaged generation.
  - The web service refuses to serve while a transaction is in flight.
  - Concurrent readers during a switch never see a mixed generation (load test with a generation marker in every response).
  - Retention selects distinct previous releases and never prunes protected generations.
  - All of the above run on `windows-latest` and on Linux.
- **Closes:** FG-JOURNAL-DURABILITY (protocol and process-crash level; host-level proof in B07 and B09), CG-4, CG-5, CG-6.
- **Risks:**
  - Power-loss durability cannot be proven in CI. The offline-host drill is optional and needs the owner's consent (OD-11). The report says exactly which crash classes were exercised.
  - Two generations in memory during a switch (CG-2). Measured in B09.
  - The control channel between processes is a new attack surface: local only, ACL'd, and accepts only the activation tool's identity.
- **Size:** L. **Depends on:** B01, B03 (DB_APPLIED); B04 for verified-component inputs. The core can start against `activation.py` immediately.

### B07 Offline installer and four-release layout on Windows (service accounts, store-root ownership, disk preflight)

- **Inputs:**
  - the application build;
  - the bundled trust list (development in Tranche B; production unchanged until owner action);
  - SECURITY_AND_DEPLOYMENT_ARCHITECTURE §2–§5;
  - the arch §7 site layout.
- **Outputs:**
  - an offline installer (MSI or bootstrapper, test Authenticode signature) that:
    - lays down binaries, Python runtime and wheels, and models (none in Tranche B production paths);
    - creates the `D:\Mimamsa\` layout of arch §7 (`vault`, `generations`, `search-index`, `text-store`, `vectors`, `models`, `exclusions`, `journal`, `activation-log`, `import`, `backup`, `logs`);
    - creates service identities and database roles;
    - applies ACLs;
    - runs DDL migrations, including I-3;
  - an `mimamsa-knowledge preflight` command;
  - an install verification report.
- **Reuses:**
  - `app/poc/p1_hosting/windows/install-aspnet-service.ps1`, `smoke-and-recovery.ps1`, `web.config`;
  - the `app-windows-poc.yml` workflow;
  - the security architecture §3 identity table and §4 ACL table.
- **Work:**
  - Service identities: virtual accounts or dedicated local accounts (OD-5); PostgreSQL account; roles `mimamsa_web`, `mimamsa_import`, `mimamsa_activator`, `mimamsa_kr_loader`, `mimamsa_backup`.
  - **Store-root ownership (CG-3):** text-store, search-index, vectors and models roots outside the application directory, owned by the import identity, read-only for the web identity, with inheritance disabled; the result is recorded with `icacls` output.
  - **Measured disk preflight (FG-DISK-PREFLIGHT, D5):** bytes still to materialise (measured at staging) plus the **configurable** headroom fraction, compared with free space measured while the retained set stays on disk. Refusal is recorded in the activation record `preflight`; there is no fixed allocation.
  - Application-upgrade preflight against the active `KNOWLEDGE_RELEASE.json` window (arch §6).
  - Uninstall preserves `site` data, the vault and the append-only stores.
  - Offline: no runtime internet dependency (security architecture §11 checklist).
- **Acceptance tests:**
  - a clean install on `windows-latest` and on the offline host (OD-11);
  - an ACL probe matrix: each identity tries every forbidden write, and it fails;
  - the web identity cannot write store roots;
  - the loader role cannot reach `site`;
  - preflight refuses on a deliberately filled volume (a VHD or a quota) and accepts after space is freed, with the record showing measured values;
  - an upgrade outside the knowledge window is refused;
  - a reinstall keeps site data;
  - the firewall leaves only 443 inbound.
- **Closes:** CG-3, the FG-DISK-PREFLIGHT mechanism, O-4 (layout), host-level FG-JOURNAL-DURABILITY drills (with B06).
- **Risks:**
  - Windows 11 Home versus Server differences: local policy tools and IIS availability. The target edition is owner decision OD-4.
  - Authenticode certificate availability (OD-13). Mitigation: a test certificate, with production refusing it.
  - Choice of MSI toolchain (free only, N-4).
- **Size:** L. **Depends on:** B06 (activation tool to install), B03 (roles and DDL).

### B08 Backup and restore, and the real restore test

- **Inputs:** an installed site with an active release, a retained release, local site data (users, audit, Studio documents, local uploads) and exclusions.
- **Outputs:**
  - a backup task and procedure: `pg_dump` of **schema `site` only**, plus the vault, local uploads and config to offline media; the journal, activation log and ExclusionStore copied separately to offline media and never overwritten by a restore; checksums verified after copy (arch §10, security architecture §8.3);
  - a restore procedure and script following arch §10 steps 1–6.
- **Reuses:** `activation.Site.backup` and `restore` (semantics), B06 `recover()`, B07 installer, and the importer's re-import of the release named by the journal head.
- **Note.** The `site` restore uses only **the site's own** dump. Knowledge is never restored from any archive: it is re-imported from release media (arch §7 decision).
- **Acceptance tests (FG-REAL-RESTORE-TEST, on an actual offline Windows host):**
  1. Full disaster restore onto a clean install. Pointers and views follow the **journal head**, not the backup; publication rows are reconciled; the latest exclusion state is re-applied; the activation-log chain is verified.
  2. Restore with an older database than the journal (stale rollback impossible).
  3. Restore refused when the journal, log or ExclusionStore is missing or older than the database.
  4. A release not retained is re-imported from media.
  5. Corruption drills: truncated journal tail, corrupt text store, corrupt index, corrupt `kr_` schema, missing vault object. Each leads to quarantine or rebuild, or a refusal, never a silent serve.
  6. Local uploads, users, audit and Studio data are intact after rollback and after restore.
  7. Time to restore is measured and reported (no target invented).
- **Closes:** FG-REAL-RESTORE-TEST, CG-6 (restore part).
- **Risks:**
  - Owner media and host availability (OD-10, OD-11).
  - At-rest encryption of backup media is an owner policy decision.
  - Restore duration at full scale is unknown.
- **Size:** M. **Depends on:** B06, B07.

### B09 Full-corpus acceptance (HTTP and concurrency, memory and disk budget, calibrated samples)

- **Inputs:**
  - a real MKR-1 built by B02 from:
    - the HF canonical corpus at its pinned revision through the v1 path (I-5);
    - plus whatever local-collection items have **eligible** effective admissions at that producer generation (possibly none);
  - the offline host;
  - the existing benchmarks: `app/b1/bench` (`IndexBench`, `HybridBench`, `run_scale_bench.py`, `text_store_http.py`, `pool_probe.py`) and `app/b1/tests/measure_search_latency.py`.
- **Outputs:** the evidence pack `app/b1/evidence/c16_tranche_b/`:
  - **CG-1:** search, document text, citation and sign-in latency and error rates under realistic concurrency on the real corpus, including the connection-pool sizing the corpus needs. The concurrency levels are agreed with the owner before the run.
  - **CG-2:** measured heap, working set, text store, index, vectors and PostgreSQL (including per-`kr_<n>` size), `Bind` and start-up at full scale, and memory with two generations open during a switch.
  - **FG-DISK-PREFLIGHT:** measured preflight on real releases.
  - **FG-CALIBRATED-SAMPLES and CG-7:** a calibration report. For each sampled check, the sample size chosen from measured cost versus detection power on **seeded faults** (injected postings errors, swapped vectors, graph mutations), and, for vectors, the tolerance from measured cross-host and cross-run drift of the pinned model and runtime. These are proposed configuration values for owner acceptance (OD-12), never invented numbers.
  - **FG-SITE-IMPORTER end to end:** import, verify and activate the real release on the offline host as ACTIVE_FULL; reproduce ACTIVE_AFTER_LOCAL_REBUILD and ACTIVE_DEGRADED by fault injection.
  - **Oracles:** retrieval oracle and journeys unchanged on the real-corpus site where applicable; golden-set coverage against the CLAUDE.md golden test set, generated **read-only** (the `reports/golden_coverage.md` path named in CLAUDE.md does not exist on staging yet).
- **Closes:** CG-1, CG-2, CG-7, FG-CALIBRATED-SAMPLES (on acceptance), and FG-SITE-IMPORTER and FG-DISK-PREFLIGHT (real releases).
- **Risks:**
  - The eligible C16 population may be small or empty while Codex's OCR and receipts are pending. The report must state the measured population exactly. **No extrapolation is presented as acceptance**, and measurements are repeated when the population changes materially.
  - The host may not match the deployment target (OD-4).
- **Size:** L. **Depends on:** B01–B08.

### B10 Model release and the model signing purpose (**blocked**)

- **Inputs:** a pinned embedder (`multilingual-e5-small`, model sha256 from `MODEL_MANIFEST.json`), the cross-encoder and OCR models as applicable, and a FULL vector pack for a new embedder built by B02/B04.
- **Outputs:**
  - an INTELLIGENCE release with `signing_purpose: model`;
  - staging of models (hash check, ONNX load self-test `ONNX_LOAD_SELFTEST`);
  - vectors merged into `vectors\<model sha>.mimvec`;
  - a MODELS journal transaction (arch §8.3);
  - old-model vectors retained, so a model rollback needs no re-embedding.
- **Reuses:** B04 vector verification, B06 journal (target MODELS), `E5Embedder` and `CrossEncoder` load paths, `trust.py`.
- **Blocked on:** OD-1. The `model` trust purpose needs an owner-authorised key and an owner-signed trust-list update. Until then, the site refuses INTELLIGENCE releases in production (D3).
- **Can be done before unblocking, in development mode only:**
  - the development-key path;
  - the refusal tests: a model release signed with a `release` key is refused; a knowledge release signed with a `model` key is refused; a new model without its full vector pack is refused (REFUSE_RELEASE); a MODELS transition without verified vectors for the active knowledge generation is refused.
- **Closes:** FG-MODEL-TRUST-PURPOSE, only after OD-1 and a production-mode test with the authorised key.
- **Size:** M (development path); S additional after OD-1. **Depends on:** B04, B06; OD-1.

---

## 4. Parallelisation plan

### 4.1 Streams

| Stream | Work packages | Language and tools | Interface it owns |
| --- | --- | --- | --- |
| **S-A Site import** | B01 | Python (`app/importer`, `app/contract`) | **IF-1 staged generation:** `generations/.tmp-*` → renamed generation with `corpus-v2/`, the receipts register and the import report (JSON schema committed with B01) |
| **S-B Knowledge data** | B03, then B04 | .NET (`Mimamsa.Knowledge`, `Mimamsa.KnowledgeTool`) | **IF-2 rows format and allowlist** (knowledge schema version); **IF-3 accelerator directories and verify results** (`mimamsa-knowledge verify-* --generation <dir>` returns a typed outcome JSON) |
| **S-C Build and release** | B02, B05 | Python orchestration plus .NET CLI calls | **IF-4 build spec and build record schema**; **IF-5 assembled bundle** (MKR-1 manifest) |
| **S-D Activation** | B06 | .NET plus web participant | **IF-6 activation tool CLI** (`activate`, `rollback`, `recover`, `preflight`, `prune`) and the web control channel |
| **S-E Windows operations** | B07, then B08 | PowerShell, MSI toolchain, Windows CI | **IF-7 site layout, identities and roles** (one table, versioned) |
| **S-F Acceptance** | B09 | Benchmarks | Consumes every interface |
| Blocked | B10 | | |

### 4.2 Interfaces first

Before parallel coding starts, one short **interface pull request** commits:
- IF-1 … IF-7 as schemas or tables;
- the I-1 receipt artefact schema proposal;
- the knowledge schema DDL draft and allowlist (I-2, I-3);
- the activation scenario-trace format (§5.3).

Each stream then codes against fixtures of the other streams' interfaces, never against their code.

### 4.3 Dependency graph and integration order

```
interface PR ──┬─► B01 ─────────────┬──────────────► B02 S5 ──┐
               ├─► B03 ──► B04 ─────┤                          ├─► B02 complete ─► B09
               ├─► B06 core ────────┴─► B06 integrated ─► B07 ─► B08 ──────────────┘
               └─► B02 skeleton (S0-S4 on fixtures) ─► B05 ─────┘
B10: dev path after B04 + B06; production path after OD-1
```

**Integration order:**
1. B01 with B03, giving a staged generation whose rows load into `kr_<n>_staging`. This is the core of **CP-1** (§7).
2. Add B06: activation of that generation, with crash suite.
3. B04 joins: accelerators verified and adopted; ACTIVE_FULL on fixtures and synthetic scale.
4. B02 and B05 end to end: a built release passes S9.
5. B07: install on Windows CI and the offline host.
6. B08: restore drill.
7. B09: real corpus.

---

## 5. Test and evidence strategy

### 5.1 Fixtures

| Fixture | Source | Used by |
| --- | --- | --- |
| Contract positives and negatives (N01–N54, X01–X35) | `app/contract/fixtures/c16/` (PR #77), unchanged | B01, B05 |
| Synthetic full-shape producer exchange | New deterministic generator beside `build_fixtures.py` (every class in contract §5; configurable scale; synthetic text only) | B01, B02, B03, B04 |
| Synthetic scale sites (10k) | `app/b1/bench/build_scale_site.py` | B04, B06 (mechanism timing only; never acceptance) |
| Real 290-document sample | `app/b1/build/build_sample.py`, `app/b1/sample` | B04 parity, B02 |
| Receipt negatives N-R01–N-R12, row-loader negatives, accelerator tamper set, activation scenario traces | New, committed with their work packages | B01, B03, B04, B06 |
| Real corpus | HF canonical at its pinned revision plus eligible C16 items | B09 only |

### 5.2 Adversarial tests

- **Bundle level:**
  - signature or checksum mismatch;
  - unlisted file;
  - reparse point and case-colliding paths;
  - reserved namespace;
  - component path overlap;
  - inventory mismatch;
  - DELTA on a wrong base;
  - unknown contract major;
  - restricted register hit in any string, including inside receipt artefacts and row files.
- **Exchange level:** every C16 negative; partial exchange; a forged receipt (§3 B01); a producer reading AR or AFT contrary to D1 and D2.
- **Accelerator level:** tampered content with a matching source digest (per kind); builder version skew; vectors keyed to other text.
- **Database level:** hostile rows; privilege escalation probes by `mimamsa_kr_loader` and `mimamsa_web`.
- **Serving level:** excluded item via search, graph, text, citation, permalink and Studio quote paths after activation, after rollback and after restore; a response produced after an exclusion accepted mid-request.

### 5.3 Crash injection

- **Python importer:** the existing `_crashpoint` mechanism, extended to the C16 materialisation and receipt steps.
- **.NET activation:** named crash points at every journal boundary and inside each step's effect. They are triggered by environment variable in test builds only and compiled out of release builds (verified by a test that greps the release binary configuration).
- **Real kills:** a harness that `TerminateProcess`es the activation tool and the web service at random offsets during a switch, loads the site, and repeats over N seeded runs. N is reported, not claimed as exhaustive.
- **Differential oracle:** each scenario trace runs through `activation.py` (the reference) and the .NET implementation. The state comparison is the pass criterion, so the reference model remains the single source of truth.

### 5.4 Real-corpus runs

These happen only in B02 (build) and B09 (acceptance), on the build host and the offline host, with development keys and no production activation. Each run records:
- the build spec;
- the build record;
- the host specification;
- the population measured: v1-path documents, C16 eligible, C16 held;
- raw measurements under `app/b1/evidence/c16_tranche_b/raw/`.

No document text is committed (CLAUDE.md, ADR-0004).

### 5.5 Determinism

- Every component except VECTOR_PACK must be byte-identical across two builds from one spec.
- For VECTOR_PACK, B02 first **measures** whether the pinned ONNX runtime on CPU, with fixed thread settings, is bit-identical across runs and hosts.
  - If it is, vectors join the byte-identical set.
  - If it is not, reproducibility of vectors is judged with the same calibrated tolerance as `VECTOR_SPOT_REEMBED` (FG-CALIBRATED-SAMPLES). The build record names the deviation.

### 5.6 Oracles that stay unchanged

None of these is edited by Tranche B. Any change goes through their own change control.

| Oracle | Location |
| --- | --- |
| Retrieval oracle (10/14 with hybrid off, 12/14 with hybrid on) | `app/b1/tests/oracles/run_retrieval_oracle.py` |
| C16 contract tests and fixtures, including the activation reference tests | `app/contract/tests/test_c16_contract.py`, `app/contract/fixtures/c16/` |
| Activation reference model | `app/contract/mimamsa_contract/c16/activation.py` |
| v1 contract tests | `app/contract/tests/` |
| Importer tests and PR #54 DA cases | `app/importer/tests/`, `app/importer/da_cases.py` |
| B1 journeys and C# suite | `app/b1/e2e`, `app/b1/tests/Mimamsa.Tests` |
| Golden 50-question coverage | `reports/golden_coverage.md` as specified in CLAUDE.md (not present on staging at `28cd346d`). If it is produced, it is generated read-only and never edited to pass |
| AUTH-LEDGER | unchanged at v0 |

---

## 6. Owner decisions and blockers

| # | Decision or blocker | Blocks | Default until decided |
| --- | --- | --- | --- |
| OD-0 | **Freeze and merge the C16 contract** (PR #77 at `80527921` or its successor) | Merging B01, B03 and B05 into staging. Development can pin the head | Work pinned to `80527921`; nothing merged that depends on an unfrozen contract |
| OD-1 | **Model signing key and `model` trust purpose** (D3, FG-MODEL-TRUST-PURPOSE): key generation and custody, an owner-signed trust-list update adding the purpose | B10 production path | INTELLIGENCE releases refused in production; development path only |
| OD-2 | **Accept contract 2.1 receipt artefacts** (I-1), with independent review per contract §12 | FG-RECEIPTS for real producer data | Site fails closed: no C16 admission is site-eligible without resolvable typed receipts |
| OD-3 | **Central build host:** which machine, disk, optional GPU; whether online fetch from it is acceptable (CLAUDE.md open question) | B02 real runs, B09 | Development on fixtures and the 290 sample |
| OD-4 | **Deployment target host and edition** (Windows Server versus 11; CPU, RAM, disk) for acceptance | B07 and B09 acceptance meaning | Measurements labelled with the host actually used; no claim for another host |
| OD-5 | **Service-account policy:** virtual accounts versus dedicated local or domain accounts; who holds the PostgreSQL superuser credential | B07 | Virtual accounts as in security architecture §3 (proposed there) |
| OD-6 | **Disk budget headroom fraction** (D5: configurable, preflight measured) and retention storage limits | B07 and B09 production configuration | Configurable value required at install; installer refuses to guess |
| OD-7 | **Default engines `disk`** for text store and index (ADR-0007 and ADR-0008) | Shipping defaults only | `memory` defaults kept; B09 runs `disk` explicitly |
| OD-8 | **MKR-1 content scope:** which HF canonical revision and which producer generations; owner relevance direction for G08 | B09 real release | Development release from pinned candidates; nothing activated in production |
| OD-9 | **Legal Reviewer appointment** (Document Studio 3.3) | Nothing in Tranche B: no legal approval is written (N-2, N-3). It matters only if a later tranche imports `legally_validated` above ledger v0 | Not required; `legally_validated` refused |
| OD-10 | **Backup media and policy:** offline media, rotation, at-rest encryption, who holds it | B08 production procedure | Test media for the restore drill |
| OD-11 | **An actual offline Windows host** for B07, B08 and B09, and consent for power-loss drills | FG-REAL-RESTORE-TEST, host-level FG-JOURNAL-DURABILITY | CI `windows-latest` evidence only, explicitly labelled as not closing these gates |
| OD-12 | **Acceptance of calibrated sample sizes and tolerances** from the B09 calibration report | FG-CALIBRATED-SAMPLES closure | `UNCALIBRATED`; production mode cannot reach ACTIVE_FULL |
| OD-13 | **Authenticode signing certificate** for the application release | Production installer | Test certificate; production refuses it |
| OD-14 | **Preservation of MKR-1 build artefacts on HF:** whether release bundles and build records are preserved under ADR-0004 or kept on owner media only | B02 artefact retention | Kept locally and on owner media; no HF write of release bundles without confirmation |
| OD-15 | **Production signing ceremony** for a real MKR-1 (owner release key) | Any production-mode rehearsal | Development keys only (N-1) |

---

## 7. First checkpoint (CP-1) for independent review

**Scope: the "site safety core", a thin vertical slice on fixtures and synthetic data.** It contains:
- the interface PR (§4.2), including the I-1 receipt-artefact proposal and I-2, I-3 and I-4 readings;
- **B01** complete (strict import, receipts with typed resolution, I1–I9, AR/AFT recomputation);
- **B03** complete (rows writer and derivation, restricted-role loader, the eight failure tests, privilege probes);
- **B06 core** (journal, recovery, pins, response-boundary exclusions, rollback, retention) with the differential conformance suite against `activation.py` and process-kill crash tests;
- a **B02 skeleton** that builds a development-signed MKR-1 from the contract fixtures plus the synthetic producer exchange, carrying authoritative components and KNOWLEDGE_ROWS only (accelerators accounted SITE_BUILDS_CHEAP or OMITTED_DEGRADED, declared honestly), and activates it on a scratch site.

**What CP-1 claims:**
- a signed fixture release imports, loads its rows and activates through the journal on Linux CI and `windows-latest`;
- every negative in §5.2 that belongs to B01, B03 or B06 refuses with site state unchanged;
- the .NET journal matches `activation.py` on every scenario trace;
- killed processes recover before serving.

**What CP-1 does not claim:**
- accelerators adopted prebuilt (B04);
- full-corpus behaviour;
- Windows installer, ACLs or preflight on a real host;
- restore;
- calibration;
- the model purpose.

None of FG-JOURNAL-DURABILITY (host level), FG-DISK-PREFLIGHT, FG-CALIBRATED-SAMPLES, FG-REAL-RESTORE-TEST or FG-MODEL-TRUST-PURPOSE is closed at CP-1. FG-RECEIPTS and FG-ROW-LOADER are closed on fixtures, pending OD-0 and OD-2.

**Evidence pack:** `app/b1/evidence/c16_tranche_b/CP1_REPORT.md`, with:
- test inventory and CI run ids;
- the scenario-trace corpus;
- ordered-dump comparisons for the loader negatives;
- crash-point matrix;
- a list of every contract rule code exercised.

The review is requested from an independent reviewer who did not write the code; no Codex review is requested.

---

## Appendix A. Traceability: consumer requirements to work packages

| Requirement | WP | Requirement | WP |
| --- | --- | --- | --- |
| I1 signature before parse | B01 | C1 `corpus-v2` in GenerationStore | B01 (materialise), B04 (load) |
| I2 strict exchange, whole-bundle refusal | B01 | C2 segment semantics | B04 (TextStore labels; existing app) |
| I3 v1 cross-check | B01 | C3 AND of gates | B04, B06 |
| I4 importer byte checks | B01 | C4 page-less anchors served from the sidecar | B03 (`evidence_anchors` rows) |
| I5 materialise `corpus-v2/` | B01 | C5 reconstructed pages via checked mapping | B01 (checks), existing citation route |
| I6 non-servable counted | B01 | C6 extract and compilation display | out of Tranche B UI scope; data carried by B03 |
| I7 effective admission eligible | B01, B03 (`corpus_admissions`) | C7 Word screenshots never quoted | B04 (index), existing quoting gates |
| I8 verified quotes only | B04 (graph structural recheck), existing gates | C8 index digest includes C16 eligibility | B04 |
| I9 review binding before review rows | B01, B03 | C9 absence notices | unchanged app behaviour |
| G1–G7 graph | B04 (GraphBuilder step 7 rows and parity), B03 (load) | arch §8.1–§8.4, §10 | B06, B07, B08 |

G1–G7 builder changes (C16 step 7, subject and chapter nodes) are a prerequisite of a GRAPH accelerator that carries C16 edges. If they are not landed before B04, MKR-1 GRAPH carries the existing origins only and the accounting says so. No C16 edge is invented outside `GraphBuilder`.
