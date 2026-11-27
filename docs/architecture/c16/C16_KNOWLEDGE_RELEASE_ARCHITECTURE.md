# C16 knowledge release architecture (WP06)

- **Status:** proposed design, Cycle 16 Tranche A. For ChatGPT review. Not implemented.
- **Builds on:**
  - contract v1 signed bundles (`release_manifest`, `trust_list`, `exclusion_update`, `app/contract/README.md` §3);
  - the release importer (`app/importer`: vault, generations, atomic `ACTIVE`);
  - [P8 signed-bundle design](../poc/P8_SIGNED_BUNDLE_UPDATE_DESIGN.md);
  - [SECURITY_AND_DEPLOYMENT_ARCHITECTURE](../SECURITY_AND_DEPLOYMENT_ARCHITECTURE.md) §2.1 and §8;
  - ADR-0006 (graph in PostgreSQL, per-generation publication);
  - ADR-0007 (persistent lexical index per generation);
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
| 2 | **Knowledge release** | Originals, extracted and OCR text, records (v1 and C16), research aids, integrity and admission registers (all **authoritative**), plus **accelerators**: a PostgreSQL data archive, persistent lexical index, vector packs for the installed models, prebuilt graph | Owner Ed25519 key, purpose `release`, over `SHA256SUMS` (v1, unchanged) | Release drop folder (v1) | What is known and searchable. Never code, never models |
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
  KNOWLEDGE_RELEASE.json           component manifest (this design; listed in SHA256SUMS)
  data/*.jsonl                     v1 records (documents, derived_text, candidates, reviews, publication)
  corpus-v2/*.jsonl                C16 records (identities, anchors, relationships, taxonomy, admissions)
  originals/<sha256>               vault objects to add (delta: only those not already in the base)
  text/<text_sha256>.txt           [[page N]] derivatives to add
  research/*.jsonl                 signed research aids (A4 provision versions, abbreviation lexicon)
  registers/integrity.jsonl        per-copy integrity results (BYTE_VERIFIED evidence, re-download receipts)
  accelerators/knowledge.pgdump    pg_dump -Fc --data-only of the knowledge schema (no DDL, no site tables)
  accelerators/graph_*.jsonl       prebuilt graph rows + digest
  accelerators/search-index/       ADR-0007 search.sqlite + MANIFEST.json
  accelerators/vectors/<model>.mimvec   MIMVEC01 vectors for the installed embedder (delta: new keys only)
  SHA256SUMS  SHA256SUMS.sig       v1 signature over SHA256SUMS
```

- **Signature.** The v1 validator verifies the signature, checksums, paths, the restricted register and records **before anything is parsed**, exactly as today. The new files are `kind: other` (later explicit kinds, a v1 minor version).
- **`KNOWLEDGE_RELEASE.json`** lists each component with: kind, format, authority (AUTHORITATIVE or ACCELERATOR), transport (FULL or DELTA), files, `result_digest`, `result_count`, the source digest and builder (for accelerators), the model hash (for vectors), the checks the site must run, and the fallback.
- **The rule that makes deltas safe.** Every component declares the digest of the **full state after applying**, so a delta changes only what travels, never what is verified.

## 4. Authoritative versus accelerator components

| Component | Authority | Why shipped | Site verification | If unusable |
| --- | --- | --- | --- | --- |
| Originals | authoritative | Evidence | sha256 per object, size, detected type, page count (importer step 2) | refuse release |
| Text derivatives | authoritative | No OCR on site | sha256; pages and passages hash; `[[page N]]` format (importer step 3) | item UNRESOLVED (quarantined), as today |
| Records (v1 + C16) | authoritative | Source of truth for everything derived | v1 validator + `c16.rules.exchange_issues`; restricted register on every string | refuse release |
| Research aids | authoritative (research, not evidence) | A4, lexicon | register re-check per line (importer `_research_files`) | file rejected, as today |
| Integrity register | authoritative | Byte-verification evidence (re-download at pinned HF commit) | schema; hashes equal the vault | refuse release |
| Admission register | authoritative | Why each item is or is not here | C16 schema and rules; every served item has an ADMITTED decision, `application_eligible=true` | refuse release |
| PostgreSQL knowledge data | **accelerator** | Avoid re-deriving candidate, graph and taxonomy tables row by row | restore into a staging schema; row counts; content digest per table equals the digest the site computes from the records | rebuild from records (cheap: minutes, no OCR or embedding) |
| Graph | **accelerator** | No graph rebuild | `GraphStore.VerifyAsync` digest; builder version equals the app's `GraphBuilder.Version`; source digest equals the site's | rebuild with the app's `GraphBuilder` (1.45 s for 290 docs; minutes at full scale; no model) |
| Lexical index | **accelerator** | No full tokenisation | ADR-0007 open checks (manifest, size, sha256, `quick_check`, format, generation, source digest, counts) | incremental local build through the forward cache (tokenises only new or changed docs) |
| Vector pack | **accelerator** | No embedding | MIMVEC01 trailer; every key recomputed from the site's **verified** passage text and model sha (keys are content-addressed, so a vector cannot be attached to the wrong text); `VECTOR_SPOT_REEMBED`: a deterministic sample of N vectors re-embedded on site within tolerance | **serve lexical only** for passages without a vector; never embed the full corpus on an ordinary deployment |

**Invariant.** An accelerator is a pure function of authoritative components and a versioned builder. It is never needed for correctness, only for speed. It never carries eligibility: withdrawal, restriction and per-request visibility are applied at query time (ADR-0006 §4, ADR-0007, VectorStore). A corrupt or substituted accelerator can therefore at worst slow the site down or degrade ranking. It cannot surface an excluded item, because exclusion is applied downstream of every accelerator.

## 5. Component digests (`result_digest`)

| Kind | Digest definition |
| --- | --- |
| ORIGINALS, TEXT_DERIVATIVES | sha256 of the sorted, LF-joined list of object hashes in the resulting set |
| RECORDS, registers | sha256 of the concatenated canonical JSONL files of the resulting set, files in path order |
| PG_KNOWLEDGE_DATA | sha256 over `table name \| row count \| sha256(rows in primary-key order, canonical text)` per table, tables in name order; computed by the same SQL on both sides |
| GRAPH | the GraphStore content digest (existing) |
| LEXICAL_INDEX | the ADR-0007 `MANIFEST.json` sha256 of `search.sqlite` |
| VECTOR_PACK | sha256 of the sorted (key, vector bytes) pairs of the resulting store for that model |

`source_digest` (accelerators) is the digest of the authoritative inputs:
- the index: the ADR-0007 source digest;
- the graph: its input records and builder version;
- vectors: the sorted key set.

The site recomputes the source digest from its own verified generation and uses the accelerator only if they are equal (`SOURCE_DIGEST_EQUALS_SITE`).

## 6. Version compatibility

| Axis | Declared in | Rule |
| --- | --- | --- |
| Application ↔ knowledge | `compatibility.min_app_version` / `max_app_version`, `knowledge_format`, `pg_knowledge_schema_version` | The app refuses a release outside its window (v1 `APP_TOO_OLD`). Knowledge DDL ships with the app; a release whose DDL version the app does not have is refused, never migrated by data |
| Contracts | `compatibility.contracts.v1`, `.corpus` | Unknown major refused (v1 `INCOMPATIBLE_CONTRACT`; C16 consumer rule) |
| Graph builder | `graph_builder_version` | Equal: use the prebuilt graph. Different: rebuild locally (declared `ONLY_IF_BUILDER_VERSION_DIFFERS`) |
| Index format | `index_format` | Equal: use. Different: incremental local build |
| Vectors ↔ models | `required_models[].sha256` = `VECTOR_PACK.model_sha256` = installed model hash | A knowledge release never changes a model. Vectors for a model not installed are kept unused. Missing vectors → lexical only for those passages |
| Model change | intelligence release | Ships the model **and** a FULL vector pack for it, built upstream. Activation switches model and vectors together (section 8.3) |
| Application upgrade | installer | Upgrades code and DDL; the active knowledge release must fall inside the new app's window, or the installer refuses (pre-flight check against `KNOWLEDGE_RELEASE.json` of the active generation) |

## 7. Site layout and PostgreSQL separation

```
D:\Mimamsa\
  vault\sha256\<aa>\<sha>                 add-only, shared by all generations (v1)
  generations\<release_id>\               one per knowledge release (v1 importer layout, plus:)
      generation.json  records\  derived\  research\  corpus-v2\  release\RELEASE.json  release\KNOWLEDGE_RELEASE.json
  search-index\<release_id>\              ADR-0007 (search.sqlite + MANIFEST.json), KeepPrevious = 2
  vectors\<model sha>.mimvec              VectorStore per model (content-keyed, shared across generations, bounded)
  models\<model sha>\                     installed by intelligence releases
  exclusions\                             ExclusionStore (append-only; never restored from backup)
  ACTIVE                                  commit point: active knowledge release id (atomic rename)
  MODELS_ACTIVE                           commit point: active intelligence release id (atomic rename)
  activation-log\                         knowledge_activation_record chain (site-only)
PostgreSQL
  schema kr_<release_sequence>            knowledge tables for one generation (graph, candidates, taxonomy, C16 relationships …)
  schema knowledge                        views only, pointing at the active kr_<n>
  schema site                             users, sessions, audit_log, withdrawals, local uploads, studio_*, credit_*,
                                          serving_policy: never touched by a release, never in a knowledge archive
```

**Two consequences:**
- The knowledge archive is a **data-only** dump of one `kr_` schema whose DDL comes from the application. `pg_restore` runs into a fresh staging schema created by trusted application code, so the archive cannot carry DDL or functions.
- Site tables live in their own schema and their own backups (section 10).

## 8. Import, atomic activation and rollback

### 8.1 Import (staging; nothing user-visible changes)

1. **Copy and verify (v1 steps 1–5).** Copy the bundle from the drop folder into the private work folder and run the v1 validator: signature, checksums, paths, manifest, compatibility, replay, ledger pin, restricted register, records. Then validate `KNOWLEDGE_RELEASE.json` against its schema and the C16 rules. For DELTA: the base must be the ACTIVE release, and `base_manifest_sha256` must equal the active `KNOWLEDGE_RELEASE.json` sha256.
2. **Vault.** Write the new originals to the vault (write-once; existing importer).
3. **Generation.** Materialise records, derivatives, research and `corpus-v2/` into `generations/.tmp-<id>/` (existing importer, fsync).
4. **Apply deltas.** Rebuild each component's resulting state (base plus delta) in staging and check `result_digest`. Any mismatch refuses the release.
5. **Accelerators**, each verified (section 4) or falling back:
   - `pg_restore` into `kr_<n>_staging`;
   - the index into `search-index/.building-<id>`, then renamed;
   - vectors merged into a temporary copy of `vectors/<model>.mimvec`, published atomically (the existing VectorStore discipline);
   - graph rows loaded into the staging schema.
6. **Smoke test** on the staged generation: fixed queries, citation resolution, graph stats, and the activation self-test of the P8 design.
7. **Rename** `generations/.tmp-<id>` to `generations/<id>`. **Not yet active.** A crash at any point leaves the previous release serving, and the leftovers are quarantined at the next start (existing importer rules).

### 8.2 Activation (one commit point)

Activation is a site Admin act: the publication act of ADR-0002, recorded as RELEASE_ACTIVATION publication records.

1. In one PostgreSQL transaction:
   - rename `kr_<n>_staging` to `kr_<n>`;
   - `CREATE OR REPLACE VIEW knowledge.* AS SELECT … FROM kr_<n>.*`;
   - insert the publication records.
2. Atomically replace `ACTIVE` (temp file, flush, rename). **This is the commit point.**
3. Run the existing post-activation steps before serving:
   - re-apply the ExclusionStore effective state, which purges index rows, vectors in use, graph edges and derivatives of suppressed items;
   - re-attach local uploads (architecture §9.1).
4. Append a `knowledge_activation_record`: per-component results (used, rebuilt or degraded), the exclusion state applied, and the previous record's hash.

**Recovery rule.** `ACTIVE` decides. At start, the app makes the `knowledge` views point at the `kr_` schema of the ACTIVE release (an idempotent repoint) and verifies the graph digest and index manifest (existing start-up verification). A crash between steps 1 and 2 therefore resolves to the previous release, with its schema still intact.

### 8.3 Model change (intelligence release)

1. Stage the model files (hash-checked; the ONNX load self-test).
2. Merge the FULL vector pack into `vectors/<new model>.mimvec`, verified as in section 4.
3. Atomically replace `MODELS_ACTIVE`.

The embedder and its vectors switch together. Vectors for the old model are retained (bounded), so a model rollback needs no re-embedding. A model whose vector pack does not verify is not activated, and the site keeps the old model rather than embedding on site.

### 8.4 Rollback

- **Knowledge rollback.** Re-activate a retained release through the explicit rollback path (v1 `rollback=True`):
  - repoint the views to its retained `kr_` schema;
  - replace `ACTIVE`;
  - the index for it is retained (ADR-0007 `KeepPrevious`), and vectors are content-keyed (the old keys are retained);
  - **always re-apply the ExclusionStore** (monotone tombstones: a rollback cannot resurrect a withdrawn or restricted item);
  - record the rollback.
- **Model rollback.** Replace `MODELS_ACTIVE` with the previous model.
- **Application rollback.** The installer's own rollback. It must not cross a knowledge DDL version (pre-flight check).

Retention: two previous knowledge releases (schemas, generation directories and indexes). The vault is never trimmed by a release.

## 9. Incremental updates

| Component | Delta transport | Site work |
| --- | --- | --- |
| Originals | new objects only | hash and write |
| Text | new derivatives only | hash and page checks |
| Records | full canonical JSONL **or** additions and tombstones keyed by the sort key, with `result_digest` of the full set | merge, canonicalise, digest |
| PG knowledge data | full archive (small relative to text), or rebuilt from records | restore or rebuild (no model) |
| Graph | full rows (small) | load and digest; or rebuild if the builder version differs |
| Lexical index | full prebuilt file, **or** none (the site builds incrementally from the forward cache) | open checks; or tokenise only changed documents |
| Vectors | new keys only, for the installed model | trailer, key recomputation, spot re-embed of a sample |
| Withdrawals and restrictions | **not in releases.** Signed exclusion updates, an independent channel (v1 §3.3) | re-apply at once |

Every delta names its base. A delta whose base is not the ACTIVE release is refused, and a FULL release is then needed. Builds are deterministic from pinned inputs (HF revision, git commits, register sha256, model hashes; C16 producer rules D1–D7), so the same inputs always produce the same component digests. That makes "rebuild locally" and "use the shipped accelerator" provably equivalent when the source digests match.

**Compute budget for an ordinary knowledge update** (no model change, same builder versions): hashing, signature verification, `pg_restore` of the data archive, SQLite `quick_check`, vector-key recomputation plus a small re-embed sample, and exclusion re-application. No OCR, no full embedding and no graph rebuild (the manifest's `heavy_compute_on_site`).

## 10. Local installation data, backup and restore

- **Never written by a release:** users, sessions, audit, local uploads and their publication records, local withdrawals, Document Studio, credits, serving policy, config, TLS keys, the activation log. A bundle path or record kind for any of these is refused: the v1 reserved namespaces and record kinds, plus `knowledge_activation_record`.
- **Backup** (existing §8.3) covers the `site` schema, the vault, local uploads and config. The knowledge schemas and accelerators are **not** backed up. They are re-derivable from the retained releases, or re-imported from the owner's offline media, which keeps backups small.
- **Restore:**
  1. clean install (application release);
  2. restore the `site` schema and the vault;
  3. re-import the last knowledge release from media, with accelerators, so there is no heavy compute;
  4. re-apply the ExclusionStore (never restored from backup; refuse if missing or older);
  5. verify the activation-log chain.

## 11. Security properties kept

- **Nothing parsed before the signature verifies.** Production refuses development keys. The trust list changes only by an owner-signed update (v1 §3.2, unchanged).
- **Restricted material:**
  - authoritative components are register-checked line by line;
  - accelerators never carry eligibility;
  - exclusion is re-applied after every activation, rollback and restore, so an older release or a restored backup cannot resurrect an item.
- **The knowledge archive** is data-only into application-created DDL. It runs no SQL functions, carries no roles and touches no site schema.
- **Admission, activation and publication are not legal approval.** `legal_approval` axes and AUTH-LEDGER are untouched. An intelligence release carrying a rule pack is refused at AUTH-LEDGER v0 (DETERMINISTIC_LEGAL_ENGINE §10; the ADR-0006 gate).

## 12. Open questions for review

| # | Question |
| --- | --- |
| O1 | Prebuilt lexical index in every release (fast activation, +1× text size per release) or only in FULL releases, with incremental local builds for deltas? |
| O2 | A separate trust-list purpose `model` for intelligence releases (a v1 minor change to `trust_list.schema.json`), or the existing `release` key with `release_class`? |
| O3 | Knowledge schema per release (`kr_<n>`, simple rollback, 2–3× DB size) versus one schema with a generation column (smaller, slower rollback)? This design proposes per-release schemas, as P8 suggested |
| O4 | `VECTOR_SPOT_REEMBED` sample size and tolerance; and whether the site may embed **new** passages from a local Admin upload (small, bounded) while never re-embedding the corpus |
| O5 | Should release `CHANGES.json` drive C16 dependency-freshness triggers (REVALIDATION_REQUIRED) for templates and checklists, as architecture §8.2 step 7 intends? |
| O6 | Retention: two previous knowledge releases, or tied to disk budget? |
