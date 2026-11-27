# Mimamsa data interchange contract v1

- **Version:** 1.0.0 (contract major 1), **pre-adoption revision R1** (2026-11-25) after independent review of `dc811848` (`docs/architecture/reviews/review_c13_b0_dc811848.md`). No bundle has been produced under the earlier draft, so the version number is unchanged; the revision tightens validation.
- **Revision marker:** `mimamsa_contract.CONTRACT_REVISION` (currently `R2`); with the version unchanged at 1.0.0 before adoption, a revision is pinned by this marker plus the commit.
- **Pre-adoption revision R2** (2026-11-25), reconciliation with the future intelligence architecture (PR #53 @ `6a0ae735`, which pinned R1 at `9eeb04a4`): optional span-binding fields on `page_anchor` (`pipeline_name`, `derivative_text_sha256`) and the `evidence` key projection; reserved site-only namespaces and record kinds; exclusion withdrawal rows must name a non-null identity; `ExclusionStore` acceptance record (compare-and-set, pending vs accepted). All additions are optional fields or stricter validation; no record kind or enum used by producers changed. PR #53's crosswalk should be re-pinned to this revision. See `docs/architecture/INTELLIGENCE_ARCHITECTURE_RECONCILIATION_C13.md`.
- **Status:** proposed for Cycle 13, shared by Track A (producers) and Track B (the offline application). It supersedes the outline "IC-01" table in `docs/planning/CYCLE13_EXECUTION_PLAN.md` §6.
- **Change control:** a breaking change after adoption needs a new major version, an updated validator and tests, and review by someone who is neither producer nor consumer author.

## 1. What the contract guarantees

1. **The app imports; it never edits.** Authoritative and frozen records (HF corpus, `records_658`, `cases_53`, CALIBRATION-02, AUTH-LEDGER, Track A registers) are read through release bundles. Corrections are new records or overlays in a later bundle.
2. **Content addressing.** A source copy is identified by the SHA-256 of its exact bytes and stored at `vault/sha256/<first two hex>/<sha256>`. File hash, judgment and proceeding are different identities; alternate copies are linked, never merged.
3. **Seven separate, closed status axes**: source integrity, source authenticity, evidence fidelity, legal applicability, legal approval, publication, dependency freshness. Each axis is its own closed object (no extra keys, no free-form sub-objects; `policy_v1` exists only on source authenticity). There is no single "verified" field.
4. **Raised values carry evidence.** Any value above an axis default on source integrity, source authenticity, evidence fidelity or dependency freshness must cite a `reviewed_record` in the same bundle (matching subject, axis and value). Independence is **structural**: `reviewer_id` ≠ the artefact's `author_id` (and ≠ the author recorded on a candidate), the subject must exist in the bundle, and `reviewed_commit` must be the commit that produced the subject (extractor commit for candidates; document git commit or release tools/artefact commit for documents). **Technical reviews (human or AI) can never set `legal_applicability` or `legal_approval`.** `legal_applicability` above `NOT_ESTABLISHED` needs an approval record under a Legal Reviewer appointment, and is rejected outright while AUTH-LEDGER is at v0. `source_authenticity = IDENTITY_CONFIRMED` needs a **human** review plus `authentication_evidence` (custodian certificate with `CUSTODIAN_AUTHENTICATED` fidelity and artefact hash; official-source record with official carrier and authority, page-image fidelity and source URL; or an AUTH-LEDGER entry, impossible at v0). Record-level (CLI) validation rejects raised values it cannot resolve. Contradictory combinations are rejected (for example legal approval on unverified evidence; `PUBLISHED` with integrity `MISMATCH`; `IDENTITY_CONFIRMED` with `copy_fidelity HASH_ONLY`).
5. **Legal approval needs an approval record, an appointment and an artefact.** Any `legal_approval` above `T0_RESEARCH_ONLY` must cite an `approval_record` that names a recorded `appointment_record` (not revoked, valid at the decision date, same capacity) and an artefact hash, all in the same bundle. While AUTH-LEDGER is at version 0 no approval or appointment record may appear at all, and `auth_ledger_version > 0` is accepted only with `auth_ledger_head` matching the site's trusted ledger state.
6. **Candidates stay candidates**, anchored to a page, versioned, with capability restriction and evaluation (or "not evaluated").
7. **Restricted material is excluded everywhere**, wherever a reference appears (§4).
8. **Release bundles are signed, checksummed and pinned**; signature first, nothing parsed before it verifies; production uses an owner-controlled trust list and refuses development keys (§3.2).
9. **Rollback and restore cannot resurrect excluded items**: a signed exclusion channel, independent of releases, is re-applied after every activation (§3.3).

## 2. Files

| Path | Purpose |
| --- | --- |
| `schemas/v1/common.schema.json` | sha256, doc_id, relative paths, vault path, page anchor, field origin, candidate status |
| `schemas/v1/status_axes.schema.json` | the seven closed axes |
| `schemas/v1/provenance.schema.json` | acquisition channel, URL, retrieval time, aliases, HF repo/revision/path, git location |
| `schemas/v1/restriction.schema.json` | printed access marking and eligibility decision |
| `schemas/v1/document.schema.json` | document record bound to one source copy |
| `schemas/v1/derived_text.schema.json` | derived text keyed by (sha256, pipeline version), page and passage anchors |
| `schemas/v1/candidate.schema.json` | outcome, holding, graph edge and form candidates |
| `schemas/v1/reviewed_record.schema.json` | independent documentary/technical review (layer 5) |
| `schemas/v1/appointment_record.schema.json`, `approval_record.schema.json` | Legal Reviewer appointment and legal approval (layer 6) |
| `schemas/v1/publication_record.schema.json` | append-only publication history (layer 7) |
| `schemas/v1/release_manifest.schema.json` | `RELEASE.json` |
| `schemas/v1/trust_list.schema.json` | pinned signing keys by purpose (release, register, trust_list) |
| `schemas/v1/exclusion_update.schema.json` | signed register + withdrawal update channel |
| `mimamsa_contract/` | validator: `schemas`, `rules`, `restricted`, `paths`, `bundle`, `trust`, `exclusions`, `citation`, `evidence` (PageKey/SpanKey projection), CLI |
| `mimamsa_contract/devbundle.py` | development-only bundle writer and test trust lists (disposable keys) |
| `examples/` | synthetic records (no real source, citation or provision) |
| `tests/` | contract tests run by `.github/workflows/app-ci.yml` |
| `schemas/c16/`, `mimamsa_contract/c16/`, `fixtures/c16/`, `tests/test_c16_contract.py` | **Proposed** Cycle 16 extension `mimamsa-corpus-contract/2.0` (document identity, evidence anchors, taxonomy, provision and judgment relationships, admission). Additive: v1 schemas and rules unchanged. See `docs/architecture/c16/C16_CORPUS_INTEGRATION_CONTRACT.md` |

## 3. Data layers, bundles, trust and exclusions

### 3.1 The nine data layers

| # | Layer | Contract representation | Where it lives on site | Mutability | Exchanged in bundles |
| --- | --- | --- | --- | --- | --- |
| 1 | Immutable vault (original bytes) | `document.source_copy` (sha256, vault path); `original` files | NTFS vault, content-addressed | Write-once; never modified | Yes (originals), hash-checked |
| 2 | Rebuildable derivatives | `derived_text` (pipeline version, pages, passages) | `derived\<sha256>\<pipeline_version>\` | Disposable, rebuildable | Yes |
| 3 | Provenance and versions | `provenance`, `alternate_copy_sha256`, release `pinned`, `CHANGES.json` | DB provenance tables, release generations | Append-only | Yes |
| 4 | Candidates (automated) | `candidate` | DB candidates | Replaced by new versions; never promoted in place | Yes, always labelled |
| 5 | Independently reviewed records | `reviewed_record`; axes cite `review_record_id` | DB review records | Append-only | Yes |
| 6 | Legally authenticated records | `appointment_record`, `approval_record`; `legal_approval.approval_record_id` | DB approvals | Append-only; revocation is a new state | **No, while AUTH-LEDGER is v0** (rejected) |
| 7 | Publication and access states | `status_axes.publication` (upstream release state), `publication_record`, `restriction` | DB publication history | Append-only; site acts recorded on site | Upstream records only; site acts (`RELEASE_ACTIVATION`, `SITE_ADMIN`) are rejected in bundles |
| 8 | Indexes and embeddings | manifest `embeddings` / `index_manifest` files with model id and hash; `pinned.model_bundles` | PostgreSQL FTS, pgvector, generation tables | Rebuilt per generation; purged on withdrawal/restriction | Optional (pre-computed embeddings) |
| 9 | Temporary working documents | none, by design | `sessions\<user>\`, owner-only | Deleted at TTL | **Never** (`WORKING_DOCUMENT_IN_BUNDLE`) |

**Publication semantics (ADR-0002).** In a bundle, `publication=PUBLISHED` means "released upstream for publication". The site Admin's activation of the release is the publication act; the importer then writes `publication_record`s with channel `RELEASE_ACTIVATION`. Local Admin publication writes `SITE_ADMIN` records. Neither is legal approval.

**Evidence keys (retrieval provenance).** `PageKey = (source_copy_sha256, page)` always resolves to the original page. `SpanKey` adds `pipeline_name`, `pipeline_version` and `derivative_text_sha256` and is formed only when all three are present (else page-only, warning `SPAN_UNBOUND`); a span never resolves against another derivative (`evidence.resolve_span`), and in a bundle the named derivative must be present (`DANGLING_SPAN_BINDING`). These keys are what search hits, citations, graph evidence and later evidence packs carry.

**Reserved site-only namespaces.** Bundle paths under `sessions/`, `agent/`, `private/`, `workflows/`, `claims/`, `policy/` and record kinds `working_document`, `agent_workflow`, `agent_task`, `agent_private_draft`, `final_claim`, `claim_verification`, `output_authorization`, `serving_epoch`, `policy_witness`, `rule_pack` are rejected (`WORKING_DOCUMENT_IN_BUNDLE`, `RESERVED_NAMESPACE`, `RESERVED_RECORD_KIND`). Future agent private writes and policy state therefore cannot enter the shared corpus by exchange.

**candidate_id stability.** Stable for the same (source copy, extractor name, anchor). A new extractor version that yields the same item keeps the id; a materially different item gets a new id and lists the old one in `supersedes_candidate_ids`. Pins, notes and impact triggers follow `supersedes_candidate_ids`.

### 3.2 Bundle layout, order of checks, trust

```
release-<id>/
  RELEASE.json  CHANGES.json
  data/documents.jsonl  data/derived_text.jsonl  data/candidates.jsonl
  data/reviewed_records.jsonl  data/appointments.jsonl  data/approvals.jsonl  data/publication_records.jsonl
  originals/…  text/…  embeddings/…  migrations/…
  SHA256SUMS        every file except itself and the signature
  SHA256SUMS.sig    Ed25519 detached signature over the exact bytes of SHA256SUMS
```

Order (validator = reference for the importer; the importer first copies the bundle into a private, ACL'd folder, and `SHA256SUMS` is read once, so the verified bytes are the parsed bytes): **1** signature against the trust list (purpose `release`); nothing else in the bundle is read before it verifies. **2** every checksum and path; stop on any failure. **3** manifest (duplicate JSON keys rejected), schema, signer identity (`key_id` must be the verifying key), compatibility, downgrade/replay (`release_sequence`; the active sequence is a mandatory input in production, 0 on first install, or the explicit rollback path), ledger pin (exact full-hash equality). **4** restricted register. **5** records with bundle-wide cross-references. **6** consistency. Any error rejects the whole bundle. Caps: SHA256SUMS ≤ 16 MiB, JSONL line ≤ 1 MiB, ≤ 5 M records; duplicate keys rejected (the importer in any language must apply the same rule).

**Paths** are checked for Windows and POSIX hazards: absolute/UNC/drive paths, `..`, `:` (NTFS alternate data streams), reserved device names in any segment (CON, PRN, AUX, NUL, COM0–9, LPT0–9, CONIN$, CONOUT$, any extension), trailing dot or space, invalid characters, segments > 255, paths > 200 characters, case-only duplicates, and symlinks/junctions/reparse points.

**Trust list and change authority.** Production validation requires the pinned trust list installed by the signed installer. Keys have purposes (`release`, `register`, `trust_list`) and holders (`OWNER`, `OWNER_BACKUP_CUSTODIAN`, `DEVELOPMENT`). The list changes only through a trust-list update signed by a currently trusted `trust_list` key held by the owner (or backup custodian), with a higher sequence number. A site Admin cannot add, replace or re-purpose keys. Keys past `valid_until` (judged against the site's trusted date) are not used. Development keys (`dev-` ids, holder `DEVELOPMENT`) are refused in production; this repository only creates disposable development or test keys.

### 3.3 Exclusion channel and post-activation re-application

`exclusion_update` carries the full register text (`register_json`, whose sha256 equals what bundles pin) and the current withdrawal list, signed by a `register` key, with an increasing sequence. After **every** activation, rollback or restore, the site re-applies the latest accepted exclusion state (`exclusions.items_to_suppress`) before the generation serves a request, and purges matching index rows, embeddings, derivatives and caches. For the **signed channel**, a rollback, an older retained generation or a restored backup therefore cannot resurrect a withdrawn or restricted item; withdrawals and register entries are monotone tombstones that only an explicit signed `readmissions` row (with `authority_ref`) lifts, never omission from a later list. **Local Admin withdrawals are not yet covered** (they live in the rollbackable DB; conflict X7, B2). Accepted updates are kept in an **append-only `ExclusionStore` outside the database and the release generations** (site path `D:\Mimamsa\exclusions\`, never overwritten by a restore); restore requires it and always applies the store's latest state (`state_for_restore`), refusing if the store is missing or older than the restored database. Acceptance is a compare-and-set of one `ACCEPTED` record (operation id, digest, signature digest, epoch, history) after the signed pair is stored write-once, under a single-writer lock. A pair without acceptance is *pending* (`pending()`) and can be completed (`complete_pending` or re-append of identical bytes). Staging residue is quarantined. A retry after a lost acknowledgement returns the original acknowledgement. An `ACCEPTED` record that points to a missing or altered pair halts.

**Operating notes (confirmation C1–C5).**
- **Labels.** Restrictions kept only by history (a register entry dropped from a later register) are labelled RESTRICTED, not WITHDRAWN.
- **Lifting a denial.**
  - Lifting a restriction requires `restriction_id` (RM-nnn) on the readmission row, plus a structured `authority_ref` (for example `OWNER-DECISION-0001`; no whitespace).
  - Reasons cannot be blank.
- **Operation ids.** An operation id already used for an accepted update is refused if it arrives with different bytes.
- **C1, crash between the two moves.** If a lone `.json` sits in `pairs/` that is identical to the incoming update, a re-append quarantines it and restages, so no manual repair is needed. Any other mismatch fails closed. **Manual repair procedure:** an Admin moves the stray file into `quarantine/`, records an audit entry and re-applies the signed update.
- **C4, history integrity.** `effective_state` halts in three cases: the history is not strictly increasing; its head differs from the `ACCEPTED` sequence and digest; or a stored pair within the accepted range is missing from the history. **B2 requirement:** the acceptance history must be append-only and integrity-protected (chained digest, kept under the witness custody of X4).
- **C5, stale LOCK.** A `LOCK` left by a crashed writer blocks acceptance and fails closed. **Recovery:** an Admin, after confirming that no writer process is running, removes the `LOCK` file through the documented maintenance action, which writes an audit record; the update is then re-applied (idempotent).
- **C5, re-application.** Re-application after every acceptance, activation, rollback or restore always uses `ExclusionStore.effective_state` (latest state plus tombstones), never the bare result of `accept_exclusion_update`. Withdrawal rows must name a non-null `doc_id` or `source_copy_sha256`.

## 4. Restricted-material exclusion rule

- **Source of truth:** `config/restricted_material.json` (RM register, governance workstream). On site, the register arrives and is updated only through signed exclusion updates.
- **No second list** under `app/` (test `test_no_register_value_is_hard_coded_in_app`).
- **Matching** is case-insensitive (NTFS) and applies to **every string anywhere in a record** (ids, parent ids, judgment identity, edge source/targets, raw citations, evidence text, alias URLs, paths), to every bundle file path and hash, and to the manifest. Section-level ids inherit the restriction.
- **Fail closed:** a missing or malformed register rejects everything. A record's own `restriction.eligibility` cannot override the register. Messages name the field, never the matched value.
- **Path resolution:** `$MIMAMSA_RESTRICTED_MATERIAL_CONFIG`, else `<repo>/config/restricted_material.json`; before governance integration the test fixture reads it from `claude/c13-gov` (or `origin/claude/c13-gov`). Tests fail rather than skip without it.

## 5. Rule codes

| Code | Meaning |
| --- | --- |
| `SCHEMA` | JSON Schema violation (includes closed axes, approval id required above T0, independent review required) |
| `RESTRICTED_MATERIAL`, `RESTRICTED_CONFIG_MISSING`, `RESTRICTED_CONFIG_DRIFT`, `RESTRICTED_IDS_NOT_APPLIED` | restricted-material rule |
| `RAISED_VALUE_NEEDS_REVIEW`, `REVIEW_UNRESOLVED`, `REVIEW_MISMATCH`, `REVIEW_UNRESOLVED_OUTSIDE_BUNDLE`, `REVIEW_NOT_INDEPENDENT`, `REVIEW_AUTHOR_MISMATCH`, `REVIEW_COMMIT_MISMATCH`, `AI_REVIEW_CANNOT_CONFIRM_IDENTITY`, `AUTHENTICITY_EVIDENCE_REQUIRED`, `AUTHENTICITY_EVIDENCE_INVALID`, `LEGAL_AXIS_NEEDS_APPROVAL`, `LEDGER_V0_NO_APPLICABILITY`, `AXIS_CONTRADICTION`, `PUBLISHED_TRUNCATED` (warning) | evidence for raised values; legal axes; contradictions |
| `LEDGER_V0_NO_APPROVAL`, `APPROVAL_UNRESOLVED`, `APPOINTMENT_MISSING`, `APPOINTMENT_REVOKED`, `APPOINTMENT_NOT_VALID_AT_DECISION`, `APPROVAL_CAPACITY_MISMATCH`, `APPROVAL_SUBJECT_MISMATCH`, `APPROVAL_TIER_MISMATCH`, `LEDGER_HEAD_UNVERIFIED`, `BANNER_REQUIRED` | approval gate |
| `SPAN_UNBOUND` (warning), `DANGLING_SPAN_BINDING`, `RESERVED_NAMESPACE`, `RESERVED_RECORD_KIND` | evidence keys; reserved namespaces |
| `PUBLISH_WITHOUT_ELIGIBILITY`, `MARKING_WITHOUT_DECISION`, `PUBLICATION_CHANNEL_SITE_ONLY`, `DANGLING_PUBLICATION_RECORD` | publication |
| `VAULT_PATH_MISMATCH`, `ALTERNATE_IS_SELF`, `DUPLICATE_DOC_ID` | identity |
| `OCR_QUOTING`, `PASSAGE_PAGE_UNKNOWN`, `DUPLICATE_PAGE`, `DUPLICATE_PASSAGE`, `ANCHOR_RANGE` | derived text and anchors |
| `REVIEW_REF_REQUIRED`, `RESTRICTION_REQUIRED`, `HOLDINGS_HIDDEN`, `EDGE_LEGAL_EFFECT_FLAG`, `LEGAL_EFFECT_EDGE_UNREVIEWED`, `EDGE_TARGET`, `DANGLING_CANDIDATE`, `DANGLING_ANCHOR`, `DANGLING_REVIEW` | candidates and reviews |
| `TRUST_LIST_REQUIRED`, `RELEASE_SEQUENCE_REQUIRED`, `SIGNATURE_MISSING`, `SIGNATURE_INVALID`, `SIGNATURE_DEV_KEY_IN_PRODUCTION`, `SIGNATURE_KEY_MISMATCH`, `SIGNATURE_NOT_VERIFIED`, `MODE_INVALID` | signature and trust |
| `CHECKSUM_MISMATCH`, `UNLISTED_FILE`, `MISSING_FILE`, `SYMLINK_IN_BUNDLE`, `PATH_HAZARD`, `CASE_COLLISION`, `WORKING_DOCUMENT_IN_BUNDLE`, `MANIFEST_*`, `SUMS_MALFORMED`, `SUMS_TOO_LARGE`, `CHANGES_MISSING`, `JSONL_MALFORMED`, `RECORD_TOO_LARGE`, `TOO_MANY_RECORDS` | bundle integrity |
| `INCOMPATIBLE_CONTRACT`, `APP_TOO_OLD`, `MIGRATIONS_DECLARED_MISSING`, `MIGRATION_NOT_IN_SUMS`, `DOWNGRADE_OR_REPLAY` | compatibility |
| warnings: `OCR_CONFIDENCE_MISSING`, `FIELD_ORIGIN_UNKNOWN_FIELD`, `EVALUATION_HUMAN_FLAG`, `ROLLBACK_UNSUPPORTED` | reported, not rejecting |

## 6. Use

```
pip install -r app/contract/requirements.txt
cd app/contract
python -m pytest -q tests
python -m mimamsa_contract record document examples/document.example.json
python -m mimamsa_contract bundle /path/to/release --trust-list site-trust-list.json --current-sequence N [--trusted-ledger-head H]
python -m mimamsa_contract bundle /path/to/release --mode development --trusted-key dev.pub.hex   # development only
python -m mimamsa_contract restricted-check --sha256 <hash>
```

## 7. Mapping from the existing corpus

| Corpus (`data/meta/<doc_id>.json`, schema 0.2.0) | Contract v1 |
| --- | --- |
| `sha256`, `raw_path`, `mime_type`, `page_count` | `source_copy` (vault path from sha256; HF path in `provenance.hf.path`) |
| `source_url`, `retrieved_at`, `source_aliases`, `source_record` | `provenance` |
| `status`, `status_note`, `status_as_of` | `corpus_status*`: display-only summary, never `legal_applicability` |
| `access_marking` | `restriction.access_marking`; eligibility `NOT_ASSESSED` unless decided |
| `text_method`, `ocr_confidence`, `ocr_low_confidence_pages` | document fields plus `derived_text.pages[].low_confidence` |
| `relations[]` | graph-edge candidates; `extracted`/`llm_proposed` → `AUTOMATED_CANDIDATE_NOT_VERIFIED`; `human_verified` → `DOCUMENTARY_CHECKED` only with a `reviewed_record` |
| `field_provenance` | `field_origin` |
| `[[page N]]` markers | `derived_text.page_marker`; passages carry page and offsets |

## 8. Known limits

- `date-time`/`date` formats are asserted only with the optional `rfc3339-validator`; patterns cover dates regardless.
- The validator does not open PDFs; anchors are checked for consistency, not against bytes (importer re-verifies, B1/B2).
- Section-level `ProvisionVersion` records arrive as a minor version when A-track statutory output is ready.
- Junction/reparse detection is exercised on the Linux CI host through its hook only; P6 must confirm it on Windows.
- A legal citation is formatted from metadata only (`citation.py`) and ends "(metadata not verified)" unless evidence fidelity is checked; reported citations depend on what is printed on the judgment.
