# B04 component verification contracts

**Schema:** `COMPONENT_VERIFICATION_SCHEMA.json`. **Reference:** `components.py`. **Fixtures:** `v2_1/component_contracts/`, `v2_1/cp1/`.

## 1. Per kind

Every accelerator is verified before use. A matching source digest is necessary but never sufficient (arch §4).

| Kind | Check | What | How | Sample |
| --- | --- | --- | --- | --- |
| KNOWLEDGE_ROWS | SHA256_EACH_FILE, ROW_COUNTS, ROWS_ALLOWLIST_AND_TYPES, ROWS_REDERIVE_COMPARE, SOURCE_DIGEST_EQUALS_SITE | rows are the signed bytes, typed, counted and **true** | B03 checks; full re-derivation | FULL |
| TEXT_STORE | SHA256_EACH_FILE, SQLITE_QUICK_CHECK, TEXT_STORE_BIND_EXACT, PAGE_HASH_ON_READ, SOURCE_DIGEST_EQUALS_SITE | metadata equals the generation's records; every page read is the verified bytes | `DiskTextStore.Bind` on every open; per-page hash (ADR-0008) | FULL |
| LEXICAL_INDEX | SHA256_EACH_FILE, SQLITE_QUICK_CHECK, SAMPLED_POSTINGS_REDERIVE, SAMPLED_QUERY_PARITY, SOURCE_DIGEST_EQUALS_SITE | postings equal fresh tokenisation; ranking equals the memory evaluator | re-tokenise a seeded document sample; run a seeded query sample against both engines | **UNCALIBRATED** sizes; EXACT |
| VECTOR_PACK | SHA256_EACH_FILE, VECTOR_TRAILER, VECTOR_KEYS_RECOMPUTED, VECTOR_SPOT_REEMBED, SOURCE_DIGEST_EQUALS_SITE | every key belongs to a verified passage and the pinned model; sampled vectors equal a fresh embedding | recompute every key; re-embed a stratified seeded sample | **UNCALIBRATED** size and tolerance |
| GRAPH | SHA256_EACH_FILE, GRAPH_DIGEST, GRAPH_STRUCTURAL_RECHECK, SAMPLED_REBUILD_PARITY, SOURCE_DIGEST_EQUALS_SITE | digest; endpoints and evidence resolve; builder-only values; sampled rebuild identical | GraphStore.VerifyAsync; full structural pass; GraphBuilder on a seeded sample | **UNCALIBRATED** size; EXACT |

**Samples.** Every sample is deterministic and seeded by the release id. Sizes and tolerances are **placeholders** (`UNCALIBRATED`) until FG-CALIBRATED-SAMPLES supplies measured values with a calibration report accepted by the owner (OD-12). None is invented here.

## 2. Outcome rules (`activation_outcome`)

1. **Authoritative failure.** The release is refused before this point.
2. **Vectors.** Vectors that are missing or fail verification give **ACTIVE_DEGRADED, lexical-only**, with Admin acknowledgement. The site **never** embeds passages (`site_embedding: NEVER`, which is a schema constant). Query-time embedding of the user's query is not affected.
3. **Cheap accelerators.** A failed KNOWLEDGE_ROWS, GRAPH, LEXICAL_INDEX or TEXT_STORE is rebuilt locally: **ACTIVE_AFTER_LOCAL_REBUILD**, which is not normal acceptance.
4. **Uncalibrated checks.** An activation relying on an **UNCALIBRATED** sampled check can never be ACTIVE_FULL in **production** mode; the result is REFUSED (fail closed). In development mode it may proceed, but the uncalibrated checks are recorded.

## 3. CP-1 fixture vertical slice

`v2_1/cp1/` contains a fixture MKR-1 manifest and its activation record:
- **Manifest:** `declared_service_level: DEGRADED_LEXICAL_ONLY`, VECTOR_PACK `OMITTED_DEGRADED`, and pending future gates listed.
- **Activation record:** `ACTIVE_DEGRADED`, acknowledged.

CP-1 is **explicitly degraded**: it is never ACTIVE_FULL, and it closes no FG-* gate on real data. A fixture slice proves the wiring, not real-corpus acceptance.
