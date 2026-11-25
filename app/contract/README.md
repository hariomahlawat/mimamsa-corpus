# Mimamsa data interchange contract v1

- **Version:** 1.0.0 (contract major 1). Status: **proposed for Cycle 13**, shared by Track A (producers) and Track B (the offline application). It supersedes the outline "IC-01" table in `docs/planning/CYCLE13_EXECUTION_PLAN.md` §6, which now points here.
- **Owner of changes:** a breaking change needs a new major version, an updated validator and tests, and review by someone who is neither the producer nor the consumer author.

## 1. What the contract guarantees

1. **The app imports; it never edits.** Authoritative and frozen records (the HF corpus, `records_658`, `cases_53`, CALIBRATION-02, AUTH-LEDGER, Track A registers) are read through release bundles. Nothing in the application writes back to them. Corrections are new records or overlays in a later bundle.
2. **Content addressing.** A source copy is identified by the SHA-256 of its exact bytes and stored at `vault/sha256/<first two hex>/<sha256>`. File hash, judgment and proceeding are different identities; alternate copies are linked, never merged.
3. **Separate status axes.** Seven axes, each with a value and a basis: source integrity, source authenticity, evidence fidelity, legal applicability, legal approval, publication, dependency freshness. There is no single "verified" field (the schema rejects one). A value on one axis never sets another.
4. **Candidates stay candidates.** Every automated output (outcome, holding, graph edge, form) is anchored to a page of a source copy, names its extractor version and artefact commit, carries its capability restriction from `C12-CONSOLIDATION/CAPABILITY_RESTRICTIONS.csv` and its evaluation report (or `null`, shown as "not evaluated").
5. **No legal approval while AUTH-LEDGER is at version 0.** A bundle with `auth_ledger_version: 0` may only carry `legal_approval = T0_RESEARCH_ONLY` and must require the candidate banner.
6. **Restricted material is excluded everywhere.** See §4.
7. **Release bundles are signed, checksummed and pinned** (HF revision, tools commit, Track A artefact commits, model bundle hashes), with compatibility, migrations and rollback declared.

## 2. Files

| Path | Purpose |
| --- | --- |
| `schemas/v1/common.schema.json` | sha256, doc_id, safe relative paths, vault path, page anchor, field origin, candidate status |
| `schemas/v1/status_axes.schema.json` | the seven axes (with SOURCE_AUTHORITY_POLICY v1 fields under source authenticity) |
| `schemas/v1/provenance.schema.json` | acquisition channel, URL, retrieval time, aliases, HF repo/revision/path, git location |
| `schemas/v1/restriction.schema.json` | printed access marking and eligibility decision |
| `schemas/v1/document.schema.json` | document record bound to one source copy; judicial cover-page fields |
| `schemas/v1/derived_text.schema.json` | derived text keyed by (sha256, pipeline version) with page and passage anchors |
| `schemas/v1/candidate.schema.json` | outcome, holding, graph edge and form candidates |
| `schemas/v1/release_manifest.schema.json` | `RELEASE.json` of a release bundle |
| `mimamsa_contract/` | validator: schema registry (offline), semantic rules, restricted-material register loader, bundle validator, CLI |
| `mimamsa_contract/devbundle.py` | development-only bundle writer with disposable keys (tests and dry runs) |
| `examples/` | synthetic, obviously fake records (no real source, citation or provision) |
| `tests/` | contract tests run by `.github/workflows/app-ci.yml` |

## 3. Bundle layout

```
release-<id>/
  RELEASE.json            manifest (release_manifest.schema.json)
  CHANGES.json            added, updated, newly_superseded, withdrawn, status_changed
  data/documents.jsonl    one document record per line
  data/derived_text.jsonl
  data/candidates.jsonl
  originals/…, text/…     optional payload files (every one listed in SHA256SUMS)
  migrations/…            optional, each listed in RELEASE.json and SHA256SUMS
  SHA256SUMS              every file except itself and the signature
  SHA256SUMS.sig          Ed25519 detached signature over the exact bytes of SHA256SUMS
```

The importer and this validator apply the same order: signature against a pinned public key, every checksum, manifest schema and compatibility, restricted-material register, every record, cross-record consistency. **Any error rejects the whole bundle.** Production signing keys are owner-held; this repository only ever creates disposable development keys (`key_id` prefixed `dev-`).

## 4. Restricted-material exclusion rule

- **Source of truth:** `config/restricted_material.json` at the repository root (register entries `RM-nnn`, introduced by the governance workstream). Each entry lists the source sha256, derived sha256s, doc_id and hosted paths. The register currently holds RM-001.
- **No second list.** Nothing under `app/` contains a register hash or doc_id; `tests/test_restricted_material.py::test_no_register_value_is_hard_coded_in_app` enforces this.
- **Matching** follows `scripts/restricted_material.py::is_restricted`: exact sha256 (case-insensitive), doc_id (section-level `#s…` ids inherit), hosted path, or any path containing a register hash or doc_id. After integration a parity test asserts both guards agree.
- **Where it applies:** document records (own copy, alternate copies, HF path), derived text (copy, text hash, text path), candidates (source doc, every anchor), every file and path in a bundle, and the manifest (it must name the register's sha256 and apply every register id).
- **Fail closed.** A missing or malformed register rejects everything (`RESTRICTED_CONFIG_MISSING`). A record's own `restriction.eligibility` cannot override the register. Issue messages never echo the matched value.
- **Path resolution:** `$MIMAMSA_RESTRICTED_MATERIAL_CONFIG`, otherwise `<repo>/config/restricted_material.json`. Before the governance branch is integrated, the test fixture reads the same file with `git show claude/c13-gov:config/restricted_material.json`; with neither available the tests fail instead of skipping.

## 5. Rule codes

| Code | Meaning |
| --- | --- |
| `SCHEMA` | JSON Schema violation |
| `RESTRICTED_MATERIAL`, `RESTRICTED_CONFIG_MISSING`, `RESTRICTED_CONFIG_DRIFT`, `RESTRICTED_IDS_NOT_APPLIED` | restricted-material rule (§4) |
| `LEDGER_V0_NO_APPROVAL`, `APPROVAL_REF_REQUIRED`, `BANNER_REQUIRED` | approval gate fails closed |
| `PUBLISH_WITHOUT_ELIGIBILITY`, `MARKING_WITHOUT_DECISION` | publication needs a recorded audience-eligibility decision |
| `VAULT_PATH_MISMATCH`, `ALTERNATE_IS_SELF`, `DUPLICATE_DOC_ID` | identity |
| `OCR_QUOTING`, `PASSAGE_PAGE_UNKNOWN`, `DUPLICATE_PAGE`, `DUPLICATE_PASSAGE`, `ANCHOR_RANGE` | derived text and anchors |
| `REVIEW_REF_REQUIRED`, `RESTRICTION_REQUIRED`, `HOLDINGS_HIDDEN`, `EDGE_LEGAL_EFFECT_FLAG`, `LEGAL_EFFECT_EDGE_UNREVIEWED`, `EDGE_TARGET`, `DANGLING_CANDIDATE`, `DANGLING_ANCHOR` | candidates |
| `SIGNATURE_*`, `CHECKSUM_MISMATCH`, `UNLISTED_FILE`, `MISSING_FILE`, `SYMLINK_IN_BUNDLE`, `UNSAFE_PATH`, `MANIFEST_*`, `SUMS_MALFORMED`, `CHANGES_MISSING` | bundle integrity |
| `INCOMPATIBLE_CONTRACT`, `APP_TOO_OLD`, `MIGRATIONS_DECLARED_MISSING`, `MIGRATION_NOT_IN_SUMS` | compatibility |
| warnings: `OCR_CONFIDENCE_MISSING`, `FIELD_ORIGIN_UNKNOWN_FIELD`, `EVALUATION_HUMAN_FLAG`, `ROLLBACK_UNSUPPORTED` | reported, not rejecting |

## 6. Use

```
pip install -r app/contract/requirements.txt
cd app/contract
python -m pytest -q tests
python -m mimamsa_contract record document examples/document.example.json
python -m mimamsa_contract bundle /path/to/release --trusted-key owner-release-key.pub.hex
python -m mimamsa_contract restricted-check --sha256 <hash>
```

## 7. Mapping from the existing corpus

| Corpus (`data/meta/<doc_id>.json`, schema 0.2.0) | Contract v1 |
| --- | --- |
| `sha256`, `raw_path`, `mime_type`, `page_count` | `source_copy` (vault path recomputed from sha256; HF path kept in `provenance.hf.path`) |
| `source_url`, `retrieved_at`, `source_aliases`, `source_record` | `provenance` |
| `status`, `status_note`, `status_as_of` | `corpus_status*`: display-only summary, never `legal_applicability` |
| `access_marking` | `restriction.access_marking`; eligibility starts `NOT_ASSESSED` unless decided |
| `text_method`, `ocr_confidence`, `ocr_low_confidence_pages` | document fields plus `derived_text.pages[].low_confidence` |
| `relations[]` | graph-edge candidates; `extracted`/`llm_proposed` → `AUTOMATED_CANDIDATE_NOT_VERIFIED`, `human_verified` → `DOCUMENTARY_CHECKED` with a review ref (Architecture §5) |
| `field_provenance` | `field_origin` |
| `[[page N]]` markers in `data/text` | `derived_text.page_marker`; passages carry page and character offsets |

## 8. Known limits (v1)

- `date-time` and `date` formats are asserted only when the optional `rfc3339-validator` package is installed; patterns cover dates regardless.
- The validator does not open PDFs; page counts and anchors are checked for consistency, not against the bytes. Track B's importer re-verifies anchors after loading (B1/B2 acceptance).
- Section-level `ProvisionVersion` records are not yet in v1; they arrive as a minor version when A-track statutory output (provision versions with valid-time intervals) is ready.
