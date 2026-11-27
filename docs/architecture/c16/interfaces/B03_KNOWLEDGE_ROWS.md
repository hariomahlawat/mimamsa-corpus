# B03 knowledge-row format and loader contract

**Schema:** `KNOWLEDGE_ROWS_SCHEMA.json`. **Reference:** `knowledge_rows.py`. **Fixtures:** `v2_1/knowledge_rows/`.

## 1. Allowlist (ships with the application, never in a release)

The allowlist document (`record_kind knowledge_rows_allowlist`, `knowledge_schema_version`) lists every loadable table with its owner, primary key, typed row definition (`$defs/<table>_row`) and derivation.

| Table | Owner (I-2) | Primary key | Derivation |
| --- | --- | --- | --- |
| document_identities | KNOWLEDGE_ROWS | doc_id | PYTHON_REFERENCE |
| evidence_anchors | KNOWLEDGE_ROWS | anchor_id | PYTHON_REFERENCE |
| corpus_relationships | KNOWLEDGE_ROWS | relationship_id | PYTHON_REFERENCE |
| taxonomy_nodes | KNOWLEDGE_ROWS | node_id | PYTHON_REFERENCE |
| corpus_admissions | KNOWLEDGE_ROWS | admission_id | PYTHON_REFERENCE |
| candidates | KNOWLEDGE_ROWS | candidate_id | DOTNET_B03 |
| provision_versions | KNOWLEDGE_ROWS | version_id | DOTNET_B03 |
| graph_nodes | GRAPH | id | DOTNET_B03 |
| graph_edges | GRAPH | id | DOTNET_B03 |

**Graph tables (I-2).** GRAPH owns `accelerators/graph/graph_nodes.jsonl` and `graph_edges.jsonl`. They are loaded by the **same** loader into `kr_<n>_staging` and verified with the GRAPH checks (B04). `allowlist_issues` rejects moving them to KNOWLEDGE_ROWS.

**Graph edge rows** accept builder verification values only, and `review_state` must be `UNREVIEWED`. Reviews arrive only through the separate audited review import (G3).

## 2. Row files

Row files are **canonical JSONL**:
- one object per row, with exactly the allowlisted columns;
- canonical JSON (contract §9.1);
- sorted by primary key;
- LF line endings and a final LF.

They are never SQL. `rows_sha256` is the sha256 of the file bytes, and the component digest is as in arch §5.

`row_file_issues` checks, **before COPY**, rejecting the whole component on any issue:

| Check | Code |
| --- | --- |
| table not on the allowlist | `KR_ROWS_TABLE_NOT_ALLOWLISTED` |
| malformed line | `KR_ROWS_MALFORMED` |
| unknown, missing or mistyped column | `KR_ROWS_TYPE` |
| oversized row | `KR_ROWS_OVERSIZED` |
| duplicate primary key | `KR_ROWS_DUPLICATE_KEY` |
| not canonical, or not in primary-key order | `KR_ROWS_NOT_CANONICAL` |

**Hostile values.** SQL text inside a value is inert data. The loader never interpolates values, and the canonical-order check catches reordering.

## 3. Re-derivation check (ROWS_REDERIVE_COMPARE)

`derive_rows(pop)` is the **one** reference derivation for the five C16 tables. The .NET writer (`KnowledgeRows.Derive`) must match it byte for byte: a cross-language golden test on the 2.1 fixtures.

**On site, after the load:**
1. Recount the rows.
2. Recompute `rows_sha256` from an ordered canonical export.
3. Re-derive every row from the authoritative records.
4. Compare (`KR_ROWS_REDERIVE_MISMATCH`).

A well-formed row that is not true (for example a flipped `application_eligible`) fails here.

## 4. Restricted loader and the staging-schema contract

The schema fixes the loader contract, so no allowlist can widen it.

**Role.** `mimamsa_kr_loader`, created `NOSUPERUSER NOCREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS NOINHERIT`.

**Grants:** only `USAGE ON SCHEMA kr_<n>_staging` and `INSERT ON ALL TABLES IN SCHEMA kr_<n>_staging`.

**Forbidden:**
- access to `site`, `knowledge` or other `kr_` schemas;
- CREATE FUNCTION, TRIGGER, RULE or EXTENSION;
- SET ROLE;
- any DDL.

**Staging schema.** `kr_<n>_staging` (pattern `^kr_[0-9]{1,9}_staging$`) is created by **application DDL** under the activator role. Its tables have no triggers and no rules.

**Load.** Parameterised `COPY … FROM STDIN` into named allowlisted tables only.

**Failure.** Any failure drops the staging schema, and `site` and the active `kr_` schema stay byte-identical (proved by ordered dumps).

**Commit.** At DB_APPLIED (B06), `kr_<n>_staging` is renamed to `kr_<n>` and the views in `knowledge` are repointed, in one transaction by the activator.

## 5. Migrations (I-3)

1. **Additive or copy-and-verify only.** New schemas (`site`, `kr_<n>`, `knowledge`) are created beside the existing default-schema tables. Data is **copied** into them and verified by ordered dumps and row counts. Old tables are kept, unused, until a verified rollback and compatibility window has passed. Nothing is dropped in the same release.
2. **Cloned databases first.** Every migration runs first on a cloned database (pg_dump/restore of a copy) in CI and on the development host. It runs on the operational localhost only after the clone passes, and never destructively.
3. **Site data preserved.** Users, sessions, audit, studio, withdrawals, credits and serving policy are all preserved; the migration test compares them before and after.
4. **Application releases only.** Schema versions move only with **application** releases. A knowledge release whose `knowledge_schema_version` the app lacks is refused.

## 6. Fixtures and tests

- **Positive:** the allowlist and five derived row files, which pass `row_file_issues` and `rederive_compare`.
- **Negatives:**
  - a table not on the allowlist;
  - an extra column;
  - a mistyped value;
  - a duplicate key;
  - reordered rows;
  - a non-object line;
  - SQL text in a value (rejected as non-canonical order here, and inert in any case);
  - a row that is well-formed but not derivable;
  - a widened loader grant (schema);
  - graph tables moved to KNOWLEDGE_ROWS.
