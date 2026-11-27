# C16 Tranche B implementation plan: importer, central build pipeline, release components, offline installation

- **Status:** plan **accepted with implementation conditions** by independent review 6091110910 (PR #81), for development on fixtures and isolated sites. This is revision 2: the conditions and the owner's working decisions are applied (§0), and the sequencing follows the owner's stages 1–5 (§4).
  - **Not authorised:** production release, merge or legal acceptance.
  - Planning only: **no application code is written or changed by this document**.
- **Target:** Mimamsa Knowledge Release 1 (**MKR-1**), built centrally and installed on an offline Windows site that consumes a pre-populated PostgreSQL and prebuilt stores.
- **Base:** `legal-knowledge/v2.5-staging` at `5bdc8e68`. That is PR #77 merged on top of `28cd346d` (PR #80). Tranche A is recorded in [C16_TRANCHE_A_COMPLETION.md](C16_TRANCHE_A_COMPLETION.md).
- **Normative inputs (read only, not reopened).** Contract `mimamsa-corpus-contract/2.0`, **frozen** at reviewed head `80527921` and merged as `5bdc8e68`. Any change is a versioned, separately reviewed change (for example 2.1).
  - Documents in `docs/architecture/c16/`:
    - [C16_CORPUS_INTEGRATION_CONTRACT.md](C16_CORPUS_INTEGRATION_CONTRACT.md), cited below as **contract §n**;
    - [C16_COMPATIBILITY_MATRIX.md](C16_COMPATIBILITY_MATRIX.md);
    - [C16_PRODUCER_REQUIREMENTS.md](C16_PRODUCER_REQUIREMENTS.md);
    - [C16_CONSUMER_REQUIREMENTS.md](C16_CONSUMER_REQUIREMENTS.md), cited below as **I1–I9, C1–C9, G1–G7**;
    - [C16_KNOWLEDGE_RELEASE_ARCHITECTURE.md](C16_KNOWLEDGE_RELEASE_ARCHITECTURE.md), cited below as **arch §n**.
  - Schemas: `app/contract/schemas/c16/`.
  - Reference code: `app/contract/mimamsa_contract/c16/` (`canonical.py`, `rules.py`, `evidence.py`, `adapters.py`, `activation.py`).

- **Carried-forward gates:** PR #80 report `app/b1/evidence/c16_integration/C16A_COMPLETION_REPORT.md` §4. They are numbered **CG-1 … CG-7** below.
- **Producer:** Codex, PR #76, branch `codex/c16-local-corpus-reconciliation`, head `7ba91ec4`. It was read with `git show` only. The plan treats Codex as an independent producer and never depends on the timing of its OCR work.

---

## 0. Review conditions, owner working decisions and safeguards

### 0.1 Conditions of review 6091110910 and where they are applied

| # | Condition | Applied in |
| --- | --- | --- |
| RC-1 | **I-1.** Typed receipt artefacts come as a **separate additive contract 2.1 interface PR** with independent review. The signed importer fails closed and verifies **payload semantics**, not only byte hashes | §2.5 I-1, B01, Stage 1 (§4) |
| RC-2 | **I-2.** The GRAPH component has a single owner, with a shared typed loader | §2.5 I-2, B03, B04 |
| RC-3 | **I-3.** The first migration is **additive, or copy-and-verify, on a cloned database**. All site data and the old schema are preserved until rollback and compatibility are verified. No destructive migration of the operational localhost database or of production | §2.5 I-3, B03, B07, SG-2 |
| RC-4 | **I-4.** Single writer plus a **local authenticated** control channel. Test loss of a participant, locks, stale processes, a torn journal, an actual crash, and current exclusions at the response boundary | §2.5 I-4, B06 |
| RC-5 | **I-5.** Legacy compatibility is limited to **independently established v1-eligible copies**. Absence or removal of a C16 sidecar never bypasses a hold, withdrawal, incomplete provenance or admission. v7 candidates and other unadmitted originals cannot be relabelled v1 to be served. Admission is accounted explicitly per source | §2.5 I-5, B01, B02, B05, SG-1 |
| RC-6 | **I-6.** The exclusion reader is read-only and signature-verified, checks that the state only moves forward (monotone), and fails closed when the store is missing or stale | §2.5 I-6, B06 |
| RC-7 | **CP-1** may be explicitly degraded, not ACTIVE_FULL, and claims **no FG closure on real data** from fixtures | §7 |
| RC-8 | Preserve the existing oracles and all site data | §1.2 N-9, §5.6, SG-2 |
| RC-9 | Bounded concurrency and a shared-host resource budget while Codex runs | SG-6, B02, B09 |
| RC-10 | Ordinary deployment never embeds missing vectors, **even as a silent fallback** | SG-4, B04 |
| RC-11 | The current machine is a provisional development and build host only, with no paid infrastructure. Target hardware, production keys, operational migration, backup and restore, and final real-corpus scope remain owner gates. Virtual accounts and configurable paths and headroom are development defaults, not final production decisions | §0.2, §0.3 |
| RC-12 | Continue the B01, B02, B03 and B06 foundations, the independently reviewed interface PR and CP-1. No waiting on Codex. No unauthorised HF upload or trust change | §4, §2.6 |

### 0.2 Owner working decisions (recorded; they replace earlier open items)

| # | Working decision | Effect on this plan |
| --- | --- | --- |
| WD-1 | The typed gate-receipt artefact schema is a separately reviewed, additive contract 2.1 extension | I-1; Stage 1 interface PR |
| WD-2 | The existing development machine is the **provisional** central build and test host | §2.1; B02 and B09 run there, sharing the host with Codex (SG-6) |
| WD-3 | The private Hugging Face dataset remains the canonical corpus repository (ADR-0004) | §2.6; B02 S1 fetches pinned revisions only |
| WD-4 | Windows is the primary deployment platform; Linux portability is preserved | B06–B08 run on Windows and Linux CI; no Windows-only data formats |
| WD-5 | Virtual service accounts for the development installer and test environment | B07 |
| WD-6 | Storage paths, disk headroom and retention limits are configurable and based on measured requirements | B07 preflight; no fixed numbers |
| WD-7 | Memory defaults stay until real-corpus disk-mode acceptance | N-8 |
| WD-8 | MKR-1 targets the **maximum independently established eligible** corpus | B09 and Stage 5; per-source admission accounting (SG-1) |
| WD-9 | Do not wait for every corpus acquisition or OCR task before building the build and deploy infrastructure | Stages 1–4 proceed on fixtures, synthetic data and the eligible canonical corpus |
| WD-10 | Build encrypted offline backup and restore, exercised with test data | B08 |
| WD-11 | Development signing keys and certificates for development and CI | B05, B07, B10 development path |
| WD-12 | Operational signing-key provisioning and production trust-list changes are deferred | B10 production path; OG-2 |
| WD-13 | Retain the active release plus two previous distinct verified releases (D4) | B06 retention |
| WD-14 | No paid infrastructure | N-4 |

### 0.3 Owner gates that remain open (not final production decisions)

| # | Owner gate | Blocks |
| --- | --- | --- |
| OG-1 | Target deployment hardware and Windows edition | Production meaning of B07 and B09 results |
| OG-2 | Production signing keys: release key ceremony, `model` purpose key (FG-MODEL-TRUST-PURPOSE), Authenticode certificate, production trust-list changes | B10 production path; any production-mode rehearsal |
| OG-3 | Operational migration, backup and restore: applying the schema migration to the operational localhost database or production, backup media custody and policy | Anything beyond cloned databases and test data |
| OG-4 | Final real-corpus scope for MKR-1, including the owner's relevance direction for gate G08 | Production MKR-1 content |
| OG-5 | Acceptance of calibrated sample sizes and tolerances (FG-CALIBRATED-SAMPLES) | Closure of that gate |
| OG-6 | Acceptance of contract 2.1, independently reviewed | FG-RECEIPTS on real producer data |
| OG-7 | Whether MKR-1 release bundles and build records are preserved on HF. No HF upload happens until this is confirmed | B02 artefact retention |
| OG-8 | An actual offline Windows host for the real restore test, and consent for power-loss drills | FG-REAL-RESTORE-TEST, host-level FG-JOURNAL-DURABILITY |

### 0.4 Safeguards (binding on every work package)

| # | Safeguard | Enforced by |
| --- | --- | --- |
| SG-1 | **No v1-compatibility bypass.** A copy is served on the v1 path only if it is an independently established v1-eligible copy: a signed v1 document record, verified bytes, complete provenance and every v1 gate. Any C16 identity or admission for the same (`doc_id`, `sha256`) or the same bytes, **in this or any retained generation**, governs: a hold, restriction, withdrawal or non-eligible effective admission denies service, whether or not a sidecar is present. Removing a sidecar in a later release never lifts a C16 hold. v7 candidates and other unadmitted originals are never emitted as v1 servable records | B01 (import check), B02 S2 and S4 (build refuses relabelling), B05 (per-source admission accounting in the release), adversarial tests in §5.2 |
| SG-2 | **Migrations run first on isolated cloned databases**, additive or copy-and-verify, with rollback demonstrated. The old schema and all site data are kept until verified. Never destructive on the operational localhost database or production | B03, B07 |
| SG-3 | **No full-corpus OCR, embedding or unconditional graph rebuild** in a normal installation | B04, B06 (`heavy_compute_on_site` checked against the outcome) |
| SG-4 | **Missing vectors never trigger site embedding.** Site mode has no corpus-embedding code path enabled. A missing or rejected vector means lexical-only for those passages, recorded as ACTIVE_DEGRADED with Admin acknowledgement. There is no silent fallback, and no configuration switch enables it in ordinary deployment | B04, with a test asserting zero embedder calls on passages during activation and serving |
| SG-5 | **Three separate acceptance levels**, never merged in reporting: **fixture** acceptance (contract fixtures, synthetic producer exchange); **synthetic-scale** acceptance (10k synthetic sites, mechanism and timing only); **actual full-corpus** acceptance (real releases on the real host). An FG or CG gate is closed only at the level its definition requires | §5.4, §7, every evidence report |
| SG-6 | **Coordinate with Codex's local corpus processing.** Heavy CPU or disk jobs (B02 S1, S3 and S6, B09 runs) use bounded concurrency (configured worker and thread limits, a disk-I/O cap where supported). They are scheduled to avoid overlapping Codex's OCR where possible and are paused or deferred when that work is running. Resource use is recorded in the build record. Nothing reads or writes Codex's worktree, `E:\Judgements` or its evidence root | B02, B09 |

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
| N-8 | **Changing the defaults** `Mimamsa:Text:Store=memory` and `Mimamsa:Search:Engine=memory` (ADR-0007 and ADR-0008 status: owner authorisation). The installer **supports** `disk` and the B09 runs use it. Memory defaults stay until real-corpus disk-mode acceptance (WD-7) |
| N-9 | **Changing the acceptance oracles** (retrieval oracle, contract fixtures, the activation reference tests, importer DA cases). See §5.6 |
| N-10 | **Local Admin upload processing** (CONTINUOUS_DOCUMENT_INGESTION). Tranche B only guarantees coexistence: releases never write `site` data, and local uploads survive activation, rollback and restore (arch §10) |

---

## 2. Component architecture

### 2.1 Two hosts, four releases

| Host | Role | Network | Runs |
| --- | --- | --- | --- |
| **Central build host** (the existing development machine, **provisional**: WD-2; shared with Codex's corpus processing: SG-6) | Builds MKR-1 knowledge releases and, later, intelligence releases | Online (HF and git) during the fetch stage only; every later stage runs with no network use | B02 pipeline: fetch → validate → text → reference import → accelerators → assemble → verify-as-site. The owner signs `SHA256SUMS` **offline** (arch §11) |
| **Offline site** (Windows; reference topology in SECURITY_AND_DEPLOYMENT_ARCHITECTURE §2) | Serves users | None. Releases arrive on removable media in `D:\Mimamsa\import\` | Installer (application release), release-import service (verify and stage), activation tool (journal), web service, backup task |

The four releases follow arch §2 and are unchanged.

| Release | Built by | Signed by | Installed by | Tranche B package |
| --- | --- | --- | --- | --- |
| Application | CI (`dotnet publish`, Python wheels, web assets) packaged on the build host | Authenticode; a development certificate in Tranche B (WD-11; the production certificate is OG-2) | Installer (B07) | B07 |
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
| **FG-CALIBRATED-SAMPLES** | site verification of accelerators | Deterministic samples (postings re-derivation, query parity, graph rebuild parity, vector spot re-embed) whose **sizes and tolerances come from measurement** (decision O4) | Calibration report from real-corpus runs, accepted by the owner (OG-5) | B04 (mechanism), B09 (calibration) |
| **FG-REAL-RESTORE-TEST** | backup task and restore procedure | arch §10 restore steps 1–6 | Full restore on an actual offline Windows host, plus corruption drills | B08 |
| **FG-DISK-PREFLIGHT** | activation tool, step 5 | Measured bytes still to materialise, plus the configurable headroom fraction, compared with measured free space while the retained set stays on disk; refusal is recorded in the activation record `preflight` | Refusal and acceptance runs on real releases and a filled volume | B07 (mechanism), B09 (real releases) |
| **FG-MODEL-TRUST-PURPOSE** | trust list, release-import | `signing_purpose: model` verified against an owner-authorised `model` key; refused until one exists | Blocked on OG-2 | B10 |
| CG-1 real full-corpus HTTP and concurrency | web service | Load harness over the real corpus | B09 report | B09 |
| CG-2 memory and disk budget | web service, activation tool | Measured heap, working set, stores, vectors and PostgreSQL; two generations open during a switch | B09 report; preflight inputs | B09 (B07) |
| CG-3 store-root ownership | installer | Roots outside the site directory, owned by the service identity, readers not writers, ACLs recorded | ACL verification script on the host | B07 |
| CG-4 generation lifecycle | web service | Pinning, draining, closing the old store after the last unpin | B06 concurrency tests | B06 |
| CG-5 retention | activation tool | Active plus two previous **distinct** verified releases (D4); never prune protected generations (D6) | `Site.previous_distinct` and `Site.protected` conformance | B06 |
| CG-6 crash-safe rollback | activation tool | Rollback is a journal transaction (arch §8.4); exclusions are monotone | Crash during rollback at every boundary; no resurrection | B06, B08 |
| CG-7 calibrated accelerator checks | as FG-CALIBRATED-SAMPLES | | | B04, B09 |

### 2.5 Implementation readings, accepted with conditions (review 6091110910)

These are implementation readings of the frozen contract. None changes a decision. Each was accepted by the plan review, subject to the conditions given in the last column.

| # | Point | Accepted reading | Review condition, now binding |
| --- | --- | --- | --- |
| I-1 | **FG-RECEIPTS needs a typed artefact.** The contract types the receipt *reference* (`$defs/receipt`) but not the artefact it hashes | A separate **additive contract 2.1 interface PR** (WD-1, part of the Stage 1 interface PR, drafted by another stream) adds `GATE_RECEIPT_ARTEFACT_SCHEMA.json` under contract §12 change control. Artefacts travel at `registers/receipts/<receipt_sha256>.json`, owned by the ADMISSION_REGISTER component. They carry `receipt_kind`, `gate_id`, `subject_sha256`, `doc_id`, `corpus_generation_id`, `derivative_sha256`, `rule_id`, `rule_version`, `config_sha256`, `register_sha256`, `outcome` and a kind-specific typed `payload`. Contract 2.0 itself is not edited | Independent review of 2.1 (OG-6). The signed importer **fails closed** until 2.1 is accepted and implemented. It verifies **payload semantics**: field equality with the admission, and recomputation where the site can. A matching byte hash is never sufficient |
| I-2 | **Graph rows versus KNOWLEDGE_ROWS.** Arch §3 puts graph rows under `accelerators/graph/`, while arch §7 lists `graph_nodes` and `graph_edges` on the rows allowlist. `KR_PATH_OVERLAP` forbids one file in two components | The GRAPH component is the **single owner** of `accelerators/graph/graph_nodes.jsonl`, `graph_edges.jsonl` and the digest. KNOWLEDGE_ROWS owns the other seven tables under `accelerators/rows/`. Both are loaded by **one shared typed loader** (B03) | Single ownership; one loader implementation with per-table typed readers |
| I-3 | **Schemas `site`, `kr_<n>` and `knowledge`** (arch §7) do not exist today. Site tables (`app_users`, `app_sessions`, `audit_log`, `withdrawals`, `serving_policy`, `studio_*`, `credit_*`) and `graph_*` live in the default schema, with `generation_id` columns | An application-release migration introduces `site`, `kr_<n>` and `knowledge`. GraphStore queries go through `knowledge` views. `graph_edge_reviews` rows come from the separate audited review-import step (G3) | **The first migration is additive, or copy-and-verify, on a cloned database** (SG-2). The old schema and all site data stay in place and the application stays compatible until rollback is demonstrated. Nothing destructive runs on the operational localhost database or production; applying it there is OG-3 |
| I-4 | **Activation ownership.** The architecture names one journal writer and a service that enters SWITCHING | The activation tool (import service identity, DB role `mimamsa_activator` with view-replacement rights on schema `knowledge` only) is the **single journal writer**. The single-writer lock is a PostgreSQL advisory lock plus an exclusive journal file lock, also taken by exclusion acceptance. The web process is a **participant** on a **local, authenticated** control channel. It enters SWITCHING (503 for new requests), acknowledges once admission has stopped, keeps pinned requests on the old `AppServices`, and swaps at OPEN. After a crash it refuses to serve until the journal shows no in-flight transaction and its loaded generation equals the journal head | Channel: local only, ACL'd to the two service identities, each message authenticated (a per-install secret readable only by those identities) and replay-protected. Tests (B06): loss of the participant mid-switch, lock contention and lock loss, stale processes (a web process still serving an old generation, or a second activation tool), a torn journal tail, an actual process crash, and the **current** exclusion state applied at the response boundary |
| I-5 | **Documents with v1 records and no C16 sidecar** (the HF canonical corpus through `build_sample.py`) | Served under the unchanged v1 rules **only when they are independently established v1-eligible copies** (SG-1) | A missing or removed C16 sidecar never bypasses a hold, withdrawal, incomplete provenance or admission. v7 candidates and other unadmitted originals cannot be relabelled v1 to be served. Every release carries **per-source admission accounting** (B05): counts by source, path (v1 or C16) and effective decision, served or not served |
| I-6 | **The .NET app does not read the signed ExclusionStore yet** (PolicyStore comment, conflict X7) | B06 adds a .NET reader of the Python ExclusionStore's latest effective state. Pins capture its sequence | **Read-only**; signature-verified against the trust list; checks that the sequence only moves forward and that the state never shrinks except by a signed update (monotone); **fails closed** when the store is missing, unreadable, behind the site's recorded sequence or stale |

### 2.6 Producer handoff (Codex)

The handoff is an **interface, not a date**. Tranche B never waits on Codex (WD-9). Codex's collection is incorporated in Stage 5 once its outputs meet the contract and admission requirements.

| Item | Producer delivers (C16_PRODUCER_REQUIREMENTS §1–§5) | Central build consumes |
| --- | --- | --- |
| Exchange | A strict exchange directory: `GENERATION.json`, `identities`, `anchors`, `relationships`, `taxonomy`, `admissions` and, when bindings exist, `reviewed_records` JSONL, plus derivatives and image OCR derivatives | Pinned by `GENERATION.json` sha256 and HF revision in the build spec (S0) |
| Preservation | Preserved to the private HF dataset, the canonical corpus repository (WD-3, ADR-0004): versioned, re-download verified, commit id recorded in git | S1 fetches by revision and re-hashes; never from Codex's worktree or `E:\` paths |
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
  10. **No v1-compatibility bypass (SG-1, I-5).** A v1 document is served without a C16 effective admission only when it is an independently established v1-eligible copy. The importer keeps a site-side **C16 decision index** across generations, keyed by `doc_id`, `sha256` and bytes. A copy with any C16 hold, restriction, withdrawal or non-eligible effective admission there is not servable, even if a later bundle omits its sidecar. Lifting a hold needs a new eligible admission revision.
  11. **Per-source admission accounting:** the import report and the generation record counts by source (HF canonical revision, producer generation), path (v1 or C16) and effective decision, served or not.
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
  - **SG-1 bypass attempts:**
    - a later bundle drops the sidecar of a HELD item;
    - a v7 candidate or unadmitted original emitted as a v1 record;
    - a v1 record for bytes that carry a C16 restriction under another `doc_id`;
    - a v1 record with incomplete provenance.

    Each must not serve;
  - crash at each existing importer crash point, with C16 files present;
  - runs on Linux CI (`importer` job) and on Windows (`windows-latest`).
- **Closes:** FG-RECEIPTS. FG-SITE-IMPORTER is closed jointly with B03, B04 and B06, end to end in B09.
- **Risks:**
  - I-1 needs contract 2.1 review and producer adoption. Mitigation: fail closed, so the importer ships before Codex adopts.
  - Strict validation cost at full scale is unmeasured. Measure it in B09 and stream the JSONL.
  - Divergence between `rules.py` and the importer. Mitigation: the importer **calls** the reference validator, never re-implements it.
- **Size:** L. **Depends on:** the frozen contract 2.0 (merged in `5bdc8e68`); the Stage 1 interface PR (contract 2.1 receipt schema) for the typed-receipt part; until 2.1 is accepted, B01 refuses every C16 admission that claims eligibility (fail closed).

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
  - No HF upload of release bundles or build records until OG-7 is decided. Fetches use only pinned revisions of the canonical dataset (WD-3).
  - The build host is shared with Codex (SG-6). Stages S1, S3 and S6 take configured worker and thread limits, record their resource use, and are scheduled to avoid overlapping Codex's OCR; a running Codex job defers them.
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
  - Schema migration I-3 (with B07), under SG-2:
    - additive, or copy-and-verify: new schemas are created and site rows **copied**, never moved;
    - verified by ordered dumps and row counts;
    - the old tables are left untouched and the application can still run against them;
    - developed and proven **only on cloned databases** (a fresh `pg_dump` and restore of a test site, or a CI database);
    - rollback (switch back to the old schema and drop the new copies) is demonstrated before anything else depends on it;
    - no step runs on the operational localhost database or production (OG-3).
- **Acceptance tests:** the eight arch §7 failure tests (unknown table, extra column, wrong type, duplicate key, count mismatch, digest mismatch, row not derivable, interrupted load). Each runs against a live PostgreSQL in CI and on Windows, and asserts `site` and the active `kr_` schema byte-identical by ordered dumps. In addition:
  - privilege probes: the loader role cannot touch `site`, create a function or trigger, or `SET ROLE`;
  - a hostile row value (SQL text, NUL, non-NFC, oversized) is inert or rejected;
  - the .NET canonical bytes equal Python `canonical.dumps_jsonl` on the fixture corpus;
  - **migration on a cloned database:** forward migration, then verification that all site data are equal (ordered dumps), then rollback to the old schema with site data again equal; repeated with a crash mid-migration;
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
  - **Embedding policy change** in `DenseIndex` (SG-4): in site mode the corpus-embedding path is **absent**, not merely switched off. Passages without a usable vector are served lexical-only and the outcome is ACTIVE_DEGRADED with Admin acknowledgement (arch §4). No silent fallback exists, and no configuration value enables corpus embedding in ordinary deployment. Query-time embedding of the user's query is unaffected. Local-upload embedding stays a separate, bounded, optional path (O4) and never runs as a fallback for release passages.
  - Failure paths follow arch §4: GRAPH, LEXICAL_INDEX and TEXT_STORE rebuild locally (ACTIVE_AFTER_LOCAL_REBUILD); VECTOR_PACK degrades to lexical (ACTIVE_DEGRADED); an authoritative failure refuses.
  - Central builders call the same code with `build` verbs in `mimamsa-knowledge`.
- **Acceptance tests:**
  - Per kind, a tampered accelerator **whose source digest still matches** must be caught by the correctness check (N43 behaviour at site level): flipped postings, a swapped vector for another passage, a graph edge with an unresolvable anchor, a text page byte change.
  - A mismatched builder version triggers a local rebuild with the outcome recorded.
  - A missing, partial or rejected vector pack gives lexical-only service plus a degraded record, **with zero embedder calls on passages** during import, activation, start-up and serving (instrumented counter asserted).
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
  - **Per-source admission accounting (I-5):** a signed `registers/admission-accounting.json`, owned by the ADMISSION_REGISTER component so the frozen manifest schema is unchanged. It holds counts by source (HF canonical revision, producer generation), path (v1 or C16) and effective decision, served or not. The site recomputes it at import and refuses the release on a mismatch. The assembler refuses to emit a v1 servable record for any v7 candidate or unadmitted original (SG-1).
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
  - **Control-channel and lock tests (I-4):**
    - the participant (web process) dies during SWITCHING and after the acknowledgement;
    - an unauthenticated or replayed control message is rejected;
    - lock contention between activation and exclusion acceptance;
    - lock loss (database session dropped) mid-transaction;
    - a stale web process still holding an old generation;
    - a second activation tool instance;
    - a torn journal tail;
    - an actual process crash (`TerminateProcess`, not only injected exceptions).
  - **Exclusion reader (I-6):** a missing store, an unreadable store, a store with a bad signature, a store behind the recorded sequence, or a state that shrinks without a signed update all **fail closed** (no serving). A newer signed state is applied at the response boundary of requests already pinned.
  - A MODELS switch interrupted after DB_APPLIED.
  - A transition refused while recovering or towards an unstaged generation.
  - The web service refuses to serve while a transaction is in flight.
  - Concurrent readers during a switch never see a mixed generation (load test with a generation marker in every response).
  - Retention selects distinct previous releases and never prunes protected generations.
  - All of the above run on `windows-latest` and on Linux.
- **Closes:** FG-JOURNAL-DURABILITY (protocol and process-crash level; host-level proof in B07 and B09), CG-4, CG-5, CG-6.
- **Risks:**
  - Power-loss durability cannot be proven in CI. The offline-host drill is optional and needs the owner's consent (OG-8). The report says exactly which crash classes were exercised.
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
  - Service identities: **virtual service accounts** for the development installer and test environment (WD-5; not a final production decision); PostgreSQL account; roles `mimamsa_web`, `mimamsa_import`, `mimamsa_activator`, `mimamsa_kr_loader`, `mimamsa_backup`.
  - **Configurable paths (WD-6):** every root (vault, generations, stores, vectors, journal, backup) is a configuration value. The arch §7 layout is the development default.
  - **Store-root ownership (CG-3):** text-store, search-index, vectors and models roots outside the application directory, owned by the import identity, read-only for the web identity, with inheritance disabled; the result is recorded with `icacls` output.
  - **Measured disk preflight (FG-DISK-PREFLIGHT, D5):** bytes still to materialise (measured at staging) plus the **configurable** headroom fraction, compared with free space measured while the retained set stays on disk. Refusal is recorded in the activation record `preflight`; there is no fixed allocation.
  - Application-upgrade preflight against the active `KNOWLEDGE_RELEASE.json` window (arch §6).
  - Uninstall preserves `site` data, the vault and the append-only stores.
  - The I-3 migration ships as an **additive or copy-and-verify** step and is exercised on cloned databases only (SG-2). Running it on the operational localhost database or production is OG-3.
  - Offline: no runtime internet dependency (security architecture §11 checklist).
- **Acceptance tests:**
  - a clean install on `windows-latest` and on the offline host (OG-8);
  - an ACL probe matrix: each identity tries every forbidden write, and it fails;
  - the web identity cannot write store roots;
  - the loader role cannot reach `site`;
  - preflight refuses on a deliberately filled volume (a VHD or a quota) and accepts after space is freed, with the record showing measured values;
  - an upgrade outside the knowledge window is refused;
  - a reinstall keeps site data;
  - the firewall leaves only 443 inbound.
- **Closes:** CG-3, the FG-DISK-PREFLIGHT mechanism, O-4 (layout), host-level FG-JOURNAL-DURABILITY drills (with B06).
- **Risks:**
  - Windows 11 Home versus Server differences: local policy tools and IIS availability. The target hardware and edition are owner gate OG-1.
  - Production Authenticode certificate (OG-2). Development certificates are used (WD-11), and production refuses them.
  - Choice of MSI toolchain (free only, N-4).
- **Size:** L. **Depends on:** B06 (activation tool to install), B03 (roles and DDL).

### B08 Backup and restore, and the real restore test

- **Inputs:** an installed site with an active release, a retained release, local site data (users, audit, Studio documents, local uploads) and exclusions.
- **Outputs:**
  - a backup task and procedure, **encrypted** for offline media (WD-10; free tooling, key handling documented, test keys only in Tranche B; production media custody is OG-3): `pg_dump` of **schema `site` only**, plus the vault, local uploads and config to offline media; the journal, activation log and ExclusionStore copied separately to offline media and never overwritten by a restore; checksums verified after copy (arch §10, security architecture §8.3);
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
  8. **Encryption:** a backup cannot be read without its key; a tampered encrypted backup is detected before restore; all drills use **test data only**.
- **Closes:** FG-REAL-RESTORE-TEST, CG-6 (restore part).
- **Risks:**
  - Owner media and host availability (OG-3, OG-8).
  - At-rest encryption of backup media is an owner policy decision.
  - Restore duration at full scale is unknown.
- **Size:** M. **Depends on:** B06, B07.

### B09 Full-corpus acceptance (HTTP and concurrency, memory and disk budget, calibrated samples)

B09 is Stage 5 (real-corpus commissioning). It integrates the corpus **progressively**, targeting the maximum independently established eligible corpus (WD-8). Codex's collection is added when its outputs meet the contract and admission requirements.

- **Inputs:**
  - a real MKR-1 built by B02 from:
    - the eligible part of the HF canonical corpus at its pinned revision: only independently established v1-eligible copies (I-5, SG-1);
    - plus whatever local-collection items have **eligible** effective admissions at that producer generation (possibly none);
  - the offline host;
  - the existing benchmarks: `app/b1/bench` (`IndexBench`, `HybridBench`, `run_scale_bench.py`, `text_store_http.py`, `pool_probe.py`) and `app/b1/tests/measure_search_latency.py`.
- **Outputs:** the evidence pack `app/b1/evidence/c16_tranche_b/`:
  - **CG-1:** search, document text, citation and sign-in latency and error rates under realistic concurrency on the real corpus, including the connection-pool sizing the corpus needs. The concurrency levels are agreed with the owner before the run.
  - **CG-2:** measured heap, working set, text store, index, vectors and PostgreSQL (including per-`kr_<n>` size), `Bind` and start-up at full scale, and memory with two generations open during a switch.
  - **FG-DISK-PREFLIGHT:** measured preflight on real releases.
  - **FG-CALIBRATED-SAMPLES and CG-7:** a calibration report. For each sampled check, the sample size chosen from measured cost versus detection power on **seeded faults** (injected postings errors, swapped vectors, graph mutations), and, for vectors, the tolerance from measured cross-host and cross-run drift of the pinned model and runtime. These are proposed configuration values for owner acceptance (OG-5), never invented numbers.
  - **Per-source admission accounting** for every real release (I-5): served and not-served counts by source, path and decision.
  - **Shared-host resource record (SG-6):** concurrency limits used, overlap with Codex jobs, and any deferrals.
  - **FG-SITE-IMPORTER end to end:** import, verify and activate the real release on the offline host as ACTIVE_FULL; reproduce ACTIVE_AFTER_LOCAL_REBUILD and ACTIVE_DEGRADED by fault injection.
  - **Oracles:** retrieval oracle and journeys unchanged on the real-corpus site where applicable; golden-set coverage against the CLAUDE.md golden test set, generated **read-only** (the `reports/golden_coverage.md` path named in CLAUDE.md does not exist on staging yet).
- **Closes:** CG-1, CG-2, CG-7, FG-CALIBRATED-SAMPLES (on acceptance), and FG-SITE-IMPORTER and FG-DISK-PREFLIGHT (real releases).
- **Risks:**
  - The eligible C16 population may be small or empty while Codex's OCR and receipts are pending. The report must state the measured population exactly. **No extrapolation is presented as acceptance**, and measurements are repeated when the population changes materially.
  - The host may not match the deployment target (OG-1).
  - Heavy runs on the shared development host can disturb Codex's OCR. Mitigation: SG-6 scheduling and limits.
  - Results are **actual full-corpus acceptance** only for the population and host measured (SG-5).
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
- **Blocked on:** OG-2 (deferred by WD-12). The `model` trust purpose needs an owner-authorised key and an owner-signed trust-list update. Until then, the site refuses INTELLIGENCE releases in production (D3).
- **Can be done before unblocking, in development mode only:**
  - the development-key path;
  - the refusal tests: a model release signed with a `release` key is refused; a knowledge release signed with a `model` key is refused; a new model without its full vector pack is refused (REFUSE_RELEASE); a MODELS transition without verified vectors for the active knowledge generation is refused.
- **Closes:** FG-MODEL-TRUST-PURPOSE, only after OG-2 and a production-mode test with the authorised key.
- **Size:** M (development path); S additional after OG-2. **Depends on:** B04, B06; OG-2.

---

## 4. Sequencing: owner stages, parallel streams and interfaces

### 4.1 Owner stages

| Stage | Content | Work packages | Exit criterion |
| --- | --- | --- | --- |
| **Stage 1: interface checkpoint** | Typed receipt schema (contract 2.1, additive); producer and consumer interfaces (IF-1); central build specification (IF-4); knowledge-row format and allowlist (IF-2, I-2); activation journal and control-channel interface (IF-6, I-4); component verification contracts (IF-3); site layout and identities (IF-7). Drafted in a separate PR by another stream, the **"Stage 1 interface PR"**, and published for independent review | Interfaces for B01–B07 | Independent review of the Stage 1 interface PR; contract 2.1 accepted or explicitly pending (the site fails closed meanwhile) |
| **Stage 2: site safety core** | B01, B03, the B06 core and the B02 skeleton; the CP-1 vertical slice on **isolated development and CI sites** | B01, B03, B06 core, B02 skeleton | CP-1 review (§7) |
| **Stage 3: central knowledge build** | The full resumable pipeline: records, derivatives, knowledge rows, text store, lexical index, vectors, graph and taxonomy, admission and integrity registers | B02 complete, B04 | Reproducible builds (§5.5); fixture and synthetic-scale acceptance (SG-5) |
| **Stage 4: release assembly and offline deployment** | Signed assembly, installation, activation, incremental (delta) updates, rollback, retention, encrypted backup and restore | B05, B06 integrated, B07, B08; B10 development path | Install, activate, update, roll back and restore on Windows CI and, when available, the offline host (OG-8) with test data |
| **Stage 5: real-corpus commissioning** | Progressive integration of the eligible canonical corpus; Codex's collection once its outputs meet contract and admission requirements | B09 | Actual full-corpus evidence for the population measured; owner gates OG-1, OG-4 and OG-5 for production meaning |

No stage waits on Codex or on every acquisition and OCR task (WD-9). Stages 3 and 4 can overlap once Stage 2's interfaces are stable.

### 4.2 Streams

| Stream | Work packages | Language and tools | Interface it owns |
| --- | --- | --- | --- |
| **S-A Site import** | B01 | Python (`app/importer`, `app/contract`) | **IF-1 staged generation:** `generations/.tmp-*` → renamed generation with `corpus-v2/`, the receipts register, the C16 decision index (SG-1) and the import report with per-source accounting |
| **S-B Knowledge data** | B03, then B04 | .NET (`Mimamsa.Knowledge`, `Mimamsa.KnowledgeTool`) | **IF-2 rows format and allowlist** (knowledge schema version; one shared typed loader); **IF-3 accelerator directories and verify results** (`mimamsa-knowledge verify-* --generation <dir>` returns a typed outcome JSON) |
| **S-C Build and release** | B02, B05 | Python orchestration plus .NET CLI calls | **IF-4 build spec and build record schema**, including resource limits (SG-6); **IF-5 assembled bundle** (MKR-1 manifest and per-source accounting) |
| **S-D Activation** | B06 | .NET plus web participant | **IF-6 activation tool CLI** (`activate`, `rollback`, `recover`, `preflight`, `prune`) and the authenticated local control channel |
| **S-E Windows operations** | B07, then B08 | PowerShell, MSI toolchain, Windows CI | **IF-7 site layout, identities and roles** (configurable; one versioned table) |
| **S-F Acceptance** | B09 | Benchmarks | Consumes every interface |
| Blocked | B10 production path | | |

Each stream codes against fixtures of the other streams' Stage 1 interfaces, never against their code.

### 4.3 Dependency graph and integration order

```
Stage 1 interface PR ─┬─► B01 ─────────────┬──────────────► B02 S5 ──┐
 (incl. contract 2.1) ├─► B03 ──► B04 ─────┤                          ├─► B02 complete ─► B09 (Stage 5)
                      ├─► B06 core ────────┴─► B06 integrated ─► B07 ─► B08 ───────────────┘
                      └─► B02 skeleton (S0-S4 on fixtures) ─► B05 ─────┘
        Stage 2: B01 + B03 + B06 core + B02 skeleton = CP-1
B10: development path after B04 + B06; production path after OG-2
```

**Integration order:**
1. B01 with B03, giving a staged generation whose rows load into `kr_<n>_staging` (Stage 2).
2. Add the B06 core: activation of that generation, with the crash suite. CP-1.
3. B04 joins: accelerators verified and adopted; ACTIVE_FULL on fixtures and at synthetic scale (Stage 3).
4. B02 and B05 end to end: a built release passes S9.
5. B07: install on Windows CI, then the offline host (Stage 4).
6. B08: encrypted backup and restore drill with test data.
7. B09: real corpus, progressively (Stage 5).

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
- **Compatibility level (SG-1):** a dropped sidecar on a held item; a v7 candidate or unadmitted original relabelled as v1; a v1 record for restricted bytes under another `doc_id`; a v1 record with incomplete provenance. None may serve.
- **Database level:** hostile rows; privilege escalation probes by `mimamsa_kr_loader` and `mimamsa_web`; migration rollback on a cloned database (SG-2).
- **Control level:** unauthenticated or replayed control messages; a stale or duplicate process; lock loss (I-4); a missing, stale, regressing or unsigned exclusion store (I-6).
- **Vector level:** a missing or rejected pack never causes embedding (SG-4).
- **Serving level:** excluded item via search, graph, text, citation, permalink and Studio quote paths after activation, after rollback and after restore; a response produced after an exclusion accepted mid-request.

### 5.3 Crash injection

- **Python importer:** the existing `_crashpoint` mechanism, extended to the C16 materialisation and receipt steps.
- **.NET activation:** named crash points at every journal boundary and inside each step's effect. They are triggered by environment variable in test builds only and compiled out of release builds (verified by a test that greps the release binary configuration).
- **Real kills:** a harness that `TerminateProcess`es the activation tool and the web service at random offsets during a switch, loads the site, and repeats over N seeded runs. N is reported, not claimed as exhaustive.
- **Differential oracle:** each scenario trace runs through `activation.py` (the reference) and the .NET implementation. The state comparison is the pass criterion, so the reference model remains the single source of truth.

### 5.4 Acceptance levels and real-corpus runs

Every report labels each result with exactly one acceptance level (SG-5):

| Level | Data | What it can close |
| --- | --- | --- |
| **Fixture** | Contract fixtures; synthetic producer exchange at small scale | Protocol and refusal behaviour; FG-RECEIPTS and FG-ROW-LOADER **on fixtures only** |
| **Synthetic scale** | 10k synthetic sites (`build_scale_site.py`) | Mechanism and timing only; never a real-corpus gate |
| **Actual full corpus** | Real releases built by B02 from the eligible corpus, on the real host | CG-1, CG-2, CG-7, FG-CALIBRATED-SAMPLES, FG-DISK-PREFLIGHT and FG-SITE-IMPORTER end to end, for the population and host measured |

Real-corpus runs happen only in B02 (build) and B09 (acceptance), on the provisional build host and the offline host, with development keys and no production activation. They respect the shared-host limits (SG-6). Each run records:
- the build spec;
- the build record;
- the host specification;
- the population measured, with per-source admission accounting: v1-path eligible, C16 eligible, C16 held, not served;
- resource limits used and any overlap with Codex jobs;
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
| Golden 50-question coverage | `reports/golden_coverage.md` as specified in CLAUDE.md (not present on staging at `5bdc8e68`). If it is produced, it is generated read-only and never edited to pass |
| AUTH-LEDGER | unchanged at v0 |

---

## 6. Owner decisions and blockers

The owner's working decisions WD-1 … WD-14 (§0.2) replace most of the earlier open items. The remaining owner gates are OG-1 … OG-8 (§0.3).

| Former item (revision 1) | Status now |
| --- | --- |
| OD-0 contract freeze and merge | **Done**: contract 2.0 frozen at `80527921`, merged as `5bdc8e68` |
| OD-1 model signing key and `model` purpose | Deferred (WD-12); remains owner gate OG-2 |
| OD-2 contract 2.1 receipt artefacts | Decided as a separately reviewed additive extension (WD-1); acceptance of the reviewed 2.1 is OG-6 |
| OD-3 central build host | The existing development machine, provisionally (WD-2) |
| OD-4 deployment target host | Remains owner gate OG-1. Windows is the primary platform with Linux portability (WD-4) |
| OD-5 service-account policy | Virtual service accounts for development and test (WD-5); production policy remains in OG-1 and OG-3 |
| OD-6 disk headroom and retention limits | Configurable and measured (WD-6); retention is active plus two previous distinct releases (WD-13) |
| OD-7 default engines | Memory defaults until real-corpus disk-mode acceptance (WD-7) |
| OD-8 MKR-1 content scope | Target the maximum independently established eligible corpus (WD-8); the final scope remains OG-4 |
| OD-9 Legal Reviewer appointment | Not needed in Tranche B: no legal approval is written (N-2, N-3) |
| OD-10 backup media and policy | Encrypted backup and restore built with test data (WD-10); operational custody is OG-3 |
| OD-11 offline Windows host | Remains OG-8 |
| OD-12 calibration acceptance | Remains OG-5 |
| OD-13 Authenticode certificate | Development certificates (WD-11); production is OG-2 |
| OD-14 HF preservation of release artefacts | Remains OG-7. The HF dataset stays canonical for the corpus (WD-3); no upload of release bundles until decided |
| OD-15 production signing ceremony | Deferred (WD-12); part of OG-2 |

## 7. First checkpoint (CP-1) for independent review

**Scope: the "site safety core", a thin vertical slice on fixtures and synthetic data.** It contains:
- the **Stage 1 interface PR** (§4.1; drafted separately and reviewed on its own), which CP-1 builds against;
- **B01** complete (strict import, receipts with typed resolution, I1–I9, AR/AFT recomputation);
- **B03** complete (rows writer and derivation, restricted-role loader, the eight failure tests, privilege probes);
- **B06 core** (journal, recovery, pins, response-boundary exclusions, rollback, retention) with the differential conformance suite against `activation.py` and process-kill crash tests;
- a **B02 skeleton** that builds a development-signed MKR-1 from the contract fixtures plus the synthetic producer exchange, carrying authoritative components and KNOWLEDGE_ROWS only, with accelerators accounted SITE_BUILDS_CHEAP or OMITTED_DEGRADED and declared honestly. It activates on **isolated development and CI sites only**. The expected outcome is **explicitly degraded** (for example ACTIVE_DEGRADED with lexical-only service and no vectors), **not ACTIVE_FULL**, and **zero embedder calls** (SG-4).

**What CP-1 claims:**
- a signed fixture release imports, loads its rows and activates through the journal on Linux CI and `windows-latest`;
- every negative in §5.2 that belongs to B01, B03 or B06 refuses with site state unchanged;
- the .NET journal matches `activation.py` on every scenario trace;
- killed processes recover before serving;
- the SG-1 bypass attempts and I-4 and I-6 failure cases refuse or fail closed;
- the existing oracles are unchanged (§5.6), and cloned-database migration tests leave site data identical (SG-2).

All claims are **fixture-level** acceptance (SG-5).

**What CP-1 does not claim:**
- accelerators adopted prebuilt (B04);
- full-corpus behaviour;
- Windows installer, ACLs or preflight on a real host;
- restore;
- calibration;
- the model purpose.

None of FG-JOURNAL-DURABILITY (host level), FG-DISK-PREFLIGHT, FG-CALIBRATED-SAMPLES, FG-REAL-RESTORE-TEST or FG-MODEL-TRUST-PURPOSE is closed at CP-1. FG-RECEIPTS and FG-ROW-LOADER are demonstrated **on fixtures only**. FG-RECEIPTS also depends on the reviewed contract 2.1 (OG-6). **No FG or CG gate is claimed closed on real data at CP-1.**

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
