# C16 knowledge release architecture (WP06)

- **Status:** proposed design, Cycle 16 Tranche A, **revised after the independent review of `4d476fab`** (findings C03, C04, C07). For re-review. Not implemented, not frozen.
- **Builds on:**
  - contract v1 signed bundles (`release_manifest`, `trust_list`, `exclusion_update`, `app/contract/README.md` §3);
  - the release importer (`app/importer`: vault, generations, atomic `ACTIVE`);
  - [P8 signed-bundle design](../poc/P8_SIGNED_BUNDLE_UPDATE_DESIGN.md);
  - [SECURITY_AND_DEPLOYMENT_ARCHITECTURE](../SECURITY_AND_DEPLOYMENT_ARCHITECTURE.md) §2.1 and §8;
  - ADR-0006 (graph in PostgreSQL, per-generation publication);
  - ADR-0007 (persistent lexical index per generation);
  - ADR-0008 (persistent text store, `mimamsa-text-store/1`; PR #80, branch `claude/c16-integration` at `e0d5cb55`, `DiskTextStore.Bind`);
  - C15 WP2 `VectorStore` (MIMVEC01, content-keyed vectors);
  - [the C16 corpus contract](C16_CORPUS_INTEGRATION_CONTRACT.md).
- **Schemas:**
  - `app/contract/schemas/c16/KNOWLEDGE_RELEASE_MANIFEST_SCHEMA.json` (`KNOWLEDGE_RELEASE.json`);
  - `KNOWLEDGE_ACTIVATION_RECORD_SCHEMA.json` (site-only activation log).

  Fixtures are in `app/contract/fixtures/c16/positive/` (full, delta and model-change releases and an activation record) and `negative/N23`–`N28`. The tests are in `test_c16_contract.py`.

## 1. Problem

Today one contract-v1 bundle carries originals, text and records. The site then rebuilds everything derived (search index, embeddings, graph) inside the generation it activates.

At full-corpus scale this fails three ways:
- it makes an ordinary update depend on hours of tokenising, embedding and graph building on a 16 GB Windows host;
- it mixes code, data and model changes into one risk;
- it leaves no clear line between what the owner signs and what the site produces locally.

The goal: an ordinary deployment needs **no OCR, no embedding and no full graph rebuild** on site, while keeping every existing trust and exclusion guarantee.

## 2. Four separately versioned things

| # | Release | What it contains | Signed by | Channel | Changes what |
| --- | --- | --- | --- | --- | --- |
| 1 | **Application release** | Installer (MSI/bootstrapper), .NET binaries, web assets, application-owned DB migrations (DDL for site tables **and** the knowledge-schema DDL), the bundled trust list, default config | Authenticode (installer, every binary); trust list inside | Installer channel (separate media or path) | Code and DDL only. Never corpus content |
| 2 | **Knowledge release** | Originals, extracted and OCR text, records (v1 and C16), research aids, integrity and admission registers (all **authoritative**), plus **accelerators**: allowlisted knowledge-table rows (no PostgreSQL archive; section 7), the persistent text store, the persistent lexical index, vector packs for the installed models and the prebuilt graph | Owner Ed25519 key, purpose `release`, over `SHA256SUMS` (v1, unchanged) | Release drop folder (v1) | What is known and searchable. Never code, never models |
| 3 | **Intelligence and model release** | ONNX models and tokenizers (embedder, cross-encoder, OCR models), and later rule packs (gated: none exist; refused at AUTH-LEDGER v0) and agent configuration; plus **full vector packs** for a new embedder | Owner Ed25519 key, purpose `release` (a `model` purpose is open question O2) | Release drop folder, `release_class = INTELLIGENCE` | Which models run. Never corpus content |
| 4 | **Local installation data** | Users, sessions, audit log, local Admin uploads and their publication records, local withdrawals, Document Studio working documents and versions, credit ledger, serving policy, the exclusion store, site config, TLS keys, the activation log | Never signed upstream; owned by the site | Never leaves the site, except backups | Site state. **Never** written by a release |

**Why separate.**
- A data update cannot change code (the P8 recommendation).
- A model change invalidates vectors, so it is shipped together with their replacement.
- A rollback of knowledge cannot touch a user's work.
- Each stream has its own compatibility window (section 6).

## 3. Knowledge release layout

A knowledge release **is** a v1 bundle, with additional files:

```
release-<id>/
  RELEASE.json                     v1 manifest (unchanged schema; release_id, release_sequence, pinned HF revision, ledger pin)
  CHANGES.json                     v1 change list (added, updated, newly superseded, withdrawn upstream)
  KNOWLEDGE_RELEASE.json           MKR-1 component manifest and signed component file inventory (listed in SHA256SUMS)
  data/*.jsonl                     v1 records (documents, derived_text, candidates, reviews, publication)
  corpus-v2/*.jsonl, GENERATION.json   C16 strict exchange (identities, anchors, relationships, taxonomy, admissions, reviews)
  originals/<sha256>               vault objects to add (delta: only those not already in the base)
  text/<text_sha256>.txt           [[page N]] derivatives to add
  research/*.jsonl                 signed research aids (A4 provision versions, abbreviation lexicon)
  registers/integrity.jsonl        per-copy integrity results (BYTE_VERIFIED evidence, re-download receipts)
  accelerators/rows/<table>.jsonl  KNOWLEDGE_ROWS: allowlisted knowledge-table rows as canonical JSONL (never SQL)
  accelerators/graph/              prebuilt graph rows + digest
  accelerators/search-index/       ADR-0007 search.sqlite + MANIFEST.json
  accelerators/text-store/         ADR-0008 text.sqlite + MANIFEST.json (mimamsa-text-store/1)
  accelerators/vectors/<model>.mimvec   MIMVEC01 vectors for the installed embedder (delta: new keys only)
  SHA256SUMS  SHA256SUMS.sig       v1 signature over SHA256SUMS
```

**Signature and parsing order.** The v1 validator verifies the signature, checksums, paths, the restricted register and records **before anything is parsed**, exactly as today. The new files are `kind: other` (later explicit kinds, a v1 minor version).

**Signed component inventory.** Every file a component owns is listed in `KNOWLEDGE_RELEASE.json` with its path, sha256 and size. The consumer checks (`rules.component_inventory_issues`) that every listed file is in the verified `SHA256SUMS` with the same hash. Rule `KR_PATH_OVERLAP` rejects:
- a path that belongs to two components;
- a path that repeats;
- a path that is a directory prefix of another.

Rule `KR_NAMESPACE` rejects:
- a path outside its kind's namespace (`originals/`, `text/`, `data/` or `corpus-v2/`, `research/`, `registers/`, `accelerators/<kind>/`, `models/`, `rule-packs/`);
- a path in a reserved site namespace (`sessions/`, `agent/`, `private/`, `workflows/`, `claims/`, `policy/`, `site/`, `exclusions/`, `activation-log/`) or a manifest file.

**Full-state digests.** Every component declares the digest of the **full state after applying**, so a delta changes only what travels, never what is verified.

## 4. Authoritative versus accelerator components

| Component | Authority | Kind-specific acceptance checks (all required by the schema) | If it fails |
| --- | --- | --- | --- |
| ORIGINALS | authoritative | sha256 per object, size, detected type, page count (importer step 2); result digest; restricted register | refuse release |
| TEXT_DERIVATIVES | authoritative | sha256; pages and passages hash; `[[page N]]` format (importer step 3) | item UNRESOLVED (quarantined), as today |
| RECORDS (v1 + C16) | authoritative | v1 validator, then **strict** C16 validation (`exchange_issues(mode="strict")`); restricted register on every string | refuse release |
| RESEARCH_AIDS | authoritative (research, not evidence) | register re-check per line | file rejected, as today |
| INTEGRITY_REGISTER | authoritative | schema; hashes equal the vault | refuse release |
| ADMISSION_REGISTER | authoritative | strict C16 validation; every served copy has an eligible effective admission (consumer I7) | refuse release |
| KNOWLEDGE_ROWS | accelerator | row counts; every table and column on the allowlist with its declared type (`ROWS_ALLOWLIST_AND_TYPES`); **every row re-derived from the authoritative records and compared** (`ROWS_REDERIVE_COMPARE`) | rebuild from records (cheap; no model) |
| GRAPH | accelerator | GraphStore digest; **structural recheck** (every endpoint exists, every evidence anchor resolves to a verified page, builder-only verification values); **sampled rebuild parity** (deterministic sample of source records rebuilt by the app's `GraphBuilder` and compared) | rebuild with the app's `GraphBuilder` (seconds to minutes; no model). Recorded as ACTIVE_AFTER_LOCAL_REBUILD |
| LEXICAL_INDEX | accelerator | ADR-0007 open checks (manifest, size, sha256, `quick_check`, format, generation, source digest, counts); **sampled postings re-derivation** (a deterministic sample of documents re-tokenised and their postings compared); **sampled query parity** against the memory evaluator | incremental local build through the forward cache (tokenises only new or changed documents) |
| TEXT_STORE | accelerator (ADR-0008, PR #80 `e0d5cb55`) | format `mimamsa-text-store/1`; `quick_check`; **bound to the generation's authoritative records on every open** (`DiskTextStore.Bind`: derivative id, text hash, pipeline, quoting flag, pages, passages, text assessment and load issues re-derived and required to match exactly); page hash checked on every read | quarantine and rebuild from the generation, or refuse (`RebuildOnFailure=false`); the memory store is always a correct fallback. The store can never grant quoting or alter evidence |
| VECTOR_PACK | accelerator | MIMVEC01 trailer; **every key recomputed** from the site's verified passage text and model sha (`VECTOR_KEYS_RECOMPUTED`; a vector cannot attach to the wrong text); **deterministic stratified spot re-embed** within a tolerance calibrated per model and platform (decision O4) | **serve lexical only** for passages without a usable vector (ACTIVE_DEGRADED, Admin acknowledgement); never embed the full corpus on an ordinary deployment |

**What a matching source digest proves.** A matching source digest only shows that an accelerator was built from the same inputs, not that it is correct. That is why each accelerator kind also requires its correctness checks (rule: the schema's per-kind `verify` sets; negative fixture N43).

**What an accelerator can and cannot do.** An accelerator is a pure function of authoritative components and a versioned builder. It is never needed for correctness, only for speed. It never carries eligibility: withdrawal, restriction and per-request visibility are applied at query time (ADR-0006 §4, ADR-0007, ADR-0008, VectorStore). At worst, a corrupt accelerator that passes its checks degrades ranking or speed; it cannot surface an excluded item or change evidence.

### 4a. Capability accounting and outcomes (review finding C07)

**Accounting.** `capability.accounting` lists every MKR-1 component kind once, with its status:
- SHIPPED;
- UNCHANGED_FROM_BASE (delta only);
- SITE_BUILDS_CHEAP (graph, lexical index, text store, knowledge rows only);
- OMITTED_DEGRADED (accelerators only, never authoritative kinds);
- NOT_APPLICABLE.

**Service level and its rules (`rules._release_manifest`):**
- **FULL.** `declared_service_level` FULL requires nothing OMITTED_DEGRADED, and a vector pack for every required embedder (`KR_FULL_CAPABILITY_CLAIM`).
- **Degraded.** A degraded level must account for what is degraded.
- **Model compatibility.** `required_models[]` pins every model hash. A vector pack for a model the release does not require is `KR_MODEL_NOT_REQUIRED`.
- **Rule packs** are refused at AUTH-LEDGER v0 (`KR_RULE_PACK_LEDGER_V0`).
- **Graph delivery.** `heavy_compute_on_site.graph_rebuild` must match how the graph is delivered: ONLY_IF_ACCELERATOR_REJECTED when shipped, SITE_BUILDS_CHEAP when not.

**Activation outcomes** (`KNOWLEDGE_ACTIVATION_RECORD_SCHEMA.json`) are distinct:

| Result | Meaning |
| --- | --- |
| ACTIVE_FULL | every component VERIFIED_USED or reused from a retained release; normal acceptance |
| ACTIVE_AFTER_LOCAL_REBUILD | at least one accelerator was rejected and rebuilt cheaply on site; full service, but **not** normal acceptance (the producer's artefact failed) |
| ACTIVE_DEGRADED | an accelerator is degraded (for example lexical-only search); requires `degradation_acknowledged_by` (an Admin) |
| REFUSED | nothing changed |

**Delta rules by kind:**

| Kind | Delta allowed |
| --- | --- |
| ORIGINALS | add-only (no tombstones; removal is the exclusion channel's job) |
| TEXT_DERIVATIVES | additions |
| RECORDS, registers | additions and tombstones by sort key, with the full-set digest |
| VECTOR_PACK | new keys only |
| KNOWLEDGE_ROWS, GRAPH, LEXICAL_INDEX, TEXT_STORE | **FULL transport only** (full replacements; decision O1) |

## 5. Component digests (`result_digest`)

| Kind | Digest definition |
| --- | --- |
| ORIGINALS, TEXT_DERIVATIVES | sha256 of the sorted, LF-joined list of object hashes in the resulting set |
| RECORDS, registers | sha256 of the concatenated canonical JSONL files of the resulting set, files in path order |
| KNOWLEDGE_ROWS | per table, `rows_sha256` = sha256 of its canonical JSONL rows in primary-key order; the component digest is sha256 over `table \| row_count \| rows_sha256`, tables in name order |
| GRAPH | the GraphStore content digest (existing) |
| LEXICAL_INDEX | the ADR-0007 `MANIFEST.json` sha256 of `search.sqlite` |
| TEXT_STORE | the ADR-0008 `MANIFEST.json` sha256 of `text.sqlite`; its source digest is ADR-0008's (format, generation, per-document derivative identity) |
| VECTOR_PACK | sha256 of the sorted (key, vector bytes) pairs of the resulting store for that model |

The site recomputes each accelerator's source digest from its own verified generation. A mismatch means the accelerator is not used; a match is necessary but not sufficient (section 4).

## 6. Version compatibility

| Axis | Declared in | Rule |
| --- | --- | --- |
| Application ↔ knowledge | `compatibility.min_app_version` / `max_app_version`, `knowledge_format`, `knowledge_schema_version` | The app refuses a release outside its window (v1 `APP_TOO_OLD`). Knowledge DDL and the KNOWLEDGE_ROWS allowlist ship with the app; a release whose schema version the app does not have is refused, never migrated by data |
| Contracts | `compatibility.contracts.v1`, `.corpus` | Unknown major refused |
| Graph builder | `graph_builder_version` | Equal: the prebuilt graph may be used, after its checks. Different: rebuild locally (ACTIVE_AFTER_LOCAL_REBUILD) |
| Index and text store formats | `index_format`, `text_store_format` | Equal: use, after checks. Different: build locally |
| Vectors ↔ models | `required_models[].sha256` = `VECTOR_PACK.model_sha256` = installed model hash | A knowledge release never changes a model. Missing vectors → lexical only for those passages, declared as degraded |
| Model change | intelligence release | Ships the model **and** a FULL vector pack for it, built upstream; the vector pack's fallback is REFUSE_RELEASE (a new model without its vectors is not activated) |
| Application upgrade | installer | Pre-flight check against the active `KNOWLEDGE_RELEASE.json`; the installer refuses if the active release falls outside the new app's window |

## 7. Site layout and the PostgreSQL trust boundary (review finding C04)

```
D:\Mimamsa\
  vault\sha256\<aa>\<sha>                 add-only, shared by all generations (v1)
  generations\<release_id>\               one per knowledge release (v1 importer layout, plus corpus-v2\ and KNOWLEDGE_RELEASE.json)
  search-index\<release_id>\              ADR-0007, KeepPrevious = 2
  text-store\<release_id>\                ADR-0008, KeepPrevious = 2
  vectors\<model sha>.mimvec              VectorStore per model (content-keyed, shared across generations, bounded)
  models\<model sha>\                     installed by intelligence releases
  exclusions\                             ExclusionStore (append-only; never restored from backup)
  journal\                                activation journal (append-only, fsync'd; section 8)
  activation-log\                         knowledge_activation_record chain (site-only)
  ACTIVE, MODELS_ACTIVE                   derived pointers, rewritten from the journal by reconciliation
PostgreSQL
  schema kr_<release_sequence>            knowledge tables for one generation (DDL from the application)
  schema knowledge                        views only, pointing at the active kr_<n>
  schema site                             users, sessions, audit_log, withdrawals, local uploads, studio_*, credit_*, serving_policy
```

**Decision: there is no PostgreSQL archive restore.** A data-only `pg_restore` is not a sandbox. The archive's table of contents decides which statements run and into which schema, and a hostile or corrupt archive can address other objects. Rather than demonstrating a safe archive restore, MKR-1 removes the archive entirely: the schema has no PG archive kind (negative fixture N38). Knowledge tables are filled by a **deterministic, validated row load**:

1. **Rows, not SQL.** KNOWLEDGE_ROWS ships canonical JSONL rows per allowlisted table (`graph_nodes`, `graph_edges`, `taxonomy_nodes`, `corpus_relationships`, `evidence_anchors`, `document_identities`, `corpus_admissions`, `candidates`, `provision_versions`). The allowlist and the column types are part of the application's knowledge schema version, not of the release (N39).
2. **Parsing.** The application parses each row with its typed reader. Unknown tables, unknown or missing columns, type errors, oversized values and duplicate primary keys reject the whole component.
3. **Isolated staging.** A fresh staging schema `kr_<n>_staging` is created by application DDL. It is owned by a dedicated non-superuser role `mimamsa_kr_loader`:
   - privileges: CREATE on that schema only, plus INSERT on its tables;
   - no privileges on `site`, `knowledge` or other `kr_` schemas;
   - no CREATE on the database, no extensions, no functions;
   - `NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS`.
4. **Load.** Rows are loaded with parameterised `COPY … FROM STDIN` (binary or text) into the named, allowlisted table only. The DDL creates no triggers and no rules, and the loader cannot create them.
5. **Content verification.** Row counts and `rows_sha256` per table are recomputed from the database (ordered canonical export). Every row is re-derived from the authoritative records and compared (`ROWS_REDERIVE_COMPARE`).
6. **Failure.** Any failure drops the staging schema; nothing else is touched. Tests to implement in the site importer: an unknown table, an extra column, a wrong type, a duplicate key, a count mismatch, a digest mismatch, a row not derivable from the records, and an interrupted load. Each must leave `site` and the active `kr_` schema byte-identical (compared by ordered dumps).

Because the rows are re-derived from records, KNOWLEDGE_ROWS is purely an accelerator: the site can always rebuild them from records (SITE_BUILDS_CHEAP).

## 8. Import, activation journal, rollback and restore (review finding C03)

### 8.1 Import (staging; nothing user-visible changes)

1. **Verify.** Copy the bundle into the private work folder. Run the v1 validator, the MKR-1 schema and rules, the component inventory check against `SHA256SUMS`, and strict C16 validation. For DELTA, the base must be the ACTIVE release, and `base_manifest_sha256` must equal the active manifest's sha256.
2. **Disk budget.** Check free space against the components' `disk_budget_bytes` plus the vault additions.
3. **Vault and generation.** Write originals write-once to the vault, and materialise records into `generations/.tmp-<id>/` (existing importer).
4. **Components.** Apply deltas and check every `result_digest`. Build or verify every accelerator (section 4) into staging locations (`kr_<n>_staging`, `.building-*` directories, a temporary vector-store copy). Record each component's outcome.
5. **Smoke test and rename.** Run the smoke test, then rename staging directories into place. **The new generation is staged and verified but not active.** A crash here leaves the previous release serving, and the leftovers are quarantined at the next start (existing rules).

### 8.2 The activation journal: one authoritative commit decision

PostgreSQL, the pointer files and the activation log are separate commit domains, so none of them can be the commit point. The **activation journal** (`journal\`, append-only, every entry fsync'd before the next step) is the single authority. The executable reference model is `app/contract/mimamsa_contract/c16/activation.py`, and its tests in `test_c16_contract.py` are the acceptance oracle for the site implementation.

| Step | Effect | Recovery after a crash here |
| --- | --- | --- |
| `BEGIN {txn, target KNOWLEDGE or MODELS, from, to, action}` | the service enters SWITCHING: **new requests are refused (503)**, pinned in-flight requests finish on their generation | ABORTED: nothing user-visible was touched |
| `DECIDED` | **the commit decision** | roll forward |
| `DB_APPLIED` | views → `kr_<to>`; RELEASE_ACTIVATION publication rows inserted **keyed by txn** (idempotent) | roll forward |
| `POINTER_WRITTEN` | `ACTIVE` / `MODELS_ACTIVE` atomically replaced | roll forward |
| `EXCLUSIONS_APPLIED` | the ExclusionStore's latest effective state, read now, is applied to the target generation | roll forward |
| `LOGGED` | `knowledge_activation_record` appended **keyed by txn** (idempotent; hash-chained) | roll forward |
| `OPEN` | if the ExclusionStore advanced since EXCLUSIONS_APPLIED, the newer state is re-applied; then serving resumes | (complete) |

**Recovery (`recover`, run at every start and after any failure).** Recovery is idempotent and refuses service until it finishes:
- aborts transactions without DECIDED;
- rolls DECIDED transactions forward through the remaining steps;
- reconciles derived state from the journal: pointers and views to the last OPEN transaction per target, a publication row for every committed transaction, the latest exclusion state on every retained generation.

Only then does the service accept requests. The same machine drives activation, rollback (`action ROLLBACK`, target a retained release), restore and model switches (target MODELS).

**Readers and exclusions:**
- **Pinning.** Each request pins one generation and one exclusion sequence (`pin`). Its whole result comes from that generation, so readers never see a mix.
- **Exclusions during a switch.** Exclusion acceptance takes the same single-writer lock. An update accepted while a switch is in progress is applied before OPEN; when the site is serving, it is applied at once to the active and every retained generation.

**Covered by tests:**
- a crash at each of the seven boundaries;
- an exclusion arriving mid-switch;
- pinned readers during switches;
- rollback cannot resurrect an excluded item;
- a model switch interrupted after DB_APPLIED;
- restore;
- a transition refused while recovering or towards an unstaged generation.

### 8.3 Model change (intelligence release)

1. Stage the model files (hash-checked, ONNX load self-test) and merge the FULL vector pack into `vectors/<new model>.mimvec`, verified as in section 4.
2. Run a MODELS journal transaction: the embedder and its vectors switch together at OPEN.

Vectors for the old model are retained (bounded), so a model rollback needs no re-embedding. A model whose vector pack does not verify is refused (fallback REFUSE_RELEASE).

### 8.4 Rollback and retention

**Rollback** is a journal transaction to a retained release:
- repoint views and pointers;
- reuse its retained index, text store and `kr_` schema;
- re-apply the exclusion state, which is monotone: tombstones never lift by omission, so a rollback cannot resurrect a withdrawn or restricted item;
- record it.

**Retention** (decision O6): keep the active release plus two previous verified releases when the disk budget permits. Retention **never** deletes:
- the active generation;
- a rollback target;
- the target of an in-flight (BEGIN without OPEN or ABORTED) transaction;
- a generation pinned by a reader;
- the sole remaining recovery copy.

Pruning happens only when the service is OPEN. Reference: `Site.protected`, `Site.prune`.

## 9. Incremental updates

| Component | Delta transport | Site work |
| --- | --- | --- |
| Originals | new objects only | hash and write |
| Text | new derivatives only | hash and page checks |
| Records | full canonical JSONL **or** additions and tombstones keyed by the sort key, with `result_digest` of the full set | merge, canonicalise, digest, strict validation |
| Knowledge rows, graph, lexical index, text store | full replacement, or not shipped (SITE_BUILDS_CHEAP) | load and verify, or build locally (no model) |
| Vectors | new keys only, for the installed model | trailer, key recomputation, stratified spot re-embed |
| Withdrawals and restrictions | **not in releases.** Signed exclusion updates on an independent channel (v1 §3.3) | applied at once, or before OPEN during a switch |

- **Base check.** Every delta names its base. A delta whose base is not the ACTIVE release is refused, and a FULL release is then needed.
- **Determinism.** Builds are deterministic from pinned inputs.
- **No heavy compute.** An ordinary knowledge update needs no OCR, no full embedding and no unconditional graph rebuild (`heavy_compute_on_site`).

## 10. Local installation data, backup and restore

- **Never written by a release:** users, sessions, audit, local uploads and their publication records, local withdrawals, Document Studio, credits, serving policy, config, TLS keys, the journal, the activation log and the exclusion store. A bundle path in these namespaces is refused (`KR_NAMESPACE`, v1 reserved namespaces).
- **Backups.** The `site` schema, the vault, local uploads and config. The journal, activation log and ExclusionStore are append-only stores **copied separately** to offline media and **never overwritten by a restore**. Knowledge schemas and accelerators are re-derivable from retained releases or the owner's media, so they are not backed up.
- **Restore** (reference: `Site.restore`):
  1. Clean install.
  2. Restore the `site` schema and the vault.
  3. Keep, or recover from offline media, the newest journal, activation log and ExclusionStore. Refuse if they are missing or older than the restored database.
  4. Re-import the release named by the journal head from media, if it is not retained.
  5. Run `recover()`: pointers and views follow the **journal head**, not the backup, so there is no stale rollback. Publication rows are reconciled, the latest exclusion state is re-applied, and the activation-log chain is verified.
  6. Serve.

## 11. Security properties kept

- **Signature first.** Nothing is parsed before the signature verifies. Production refuses development keys. The trust list changes only by an owner-signed update (v1 §3.2, unchanged).
- **Signed inventory.** Every component file is in the signed inventory and in `SHA256SUMS`; no overlaps, no reserved namespaces.
- **Restricted material:**
  - authoritative components are register-checked line by line;
  - accelerators never carry eligibility;
  - exclusion is re-applied before every exposure.
- **No SQL from a release.** There is no archive restore; rows are loaded through allowlisted, typed, parameterised COPY by a restricted role into an isolated staging schema.
- **No legal effect.** Admission, activation and publication are not legal approval. A rule pack is refused at AUTH-LEDGER v0.

## 12. Adopted working decisions (owner-overridable)

| # | Decision |
| --- | --- |
| O1 | A FULL release ships the text derivatives, the text store and the lexical index. A delta may ship full replacements of the index and text store, or let the site build them incrementally; both are recorded in the accounting |
| O2 | A separate trust-list purpose `model` for intelligence releases is recommended. Until the owner approves a trust-list migration, intelligence releases use the existing `release` purpose, and no trust change is made by this design |
| O3 | Per-release isolated `kr_<n>` schemas initially, subject to disk and restore tests at full scale |
| O4 | Vector spot re-embed: a deterministic, stratified sample with a tolerance calibrated from actual model and platform evidence. No acceptance threshold is invented here. Bounded embedding of local Admin uploads is optional and separate, never a corpus re-embed |
| O5 | `CHANGES.json` drives dependency-freshness (REVALIDATION_REQUIRED) flags only, never legal approval |
| O6 | Retain the active release plus two previous verified releases when the disk budget permits; never prune a pinned reader's generation, a rollback target, an in-flight target or the sole recovery copy |

**Remaining limits:**
- The site importer, the row loader and the restore role are specified, and their tests listed, but not implemented here: no application code changed.
- The activation journal is proven only on the reference model.
- Real offline restore, corruption recovery on real artefacts and full-scale disk measurements remain to be demonstrated in the site implementation.
