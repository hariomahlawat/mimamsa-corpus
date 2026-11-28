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
3. **Cheap accelerators (2.1, review C16-I21-02).** A failed or missing KNOWLEDGE_ROWS, GRAPH, LEXICAL_INDEX or TEXT_STORE must be rebuilt locally **and independently verified** before it is used. All four are essential.
   - **No evidence:** without rebuild evidence passing `rebuild_issues`, the result is **REFUSED, `refusal: REBUILD_REQUIRED`, NOT_SERVING**.
   - **What the evidence must hold:** `status: VERIFIED`; builder `name`, `version` and `commit`; `source_digest` and `result_digest`; and every required check of the kind as `PASS`, with no `FAIL`.
   - **Successful rebuild:** **ACTIVE_AFTER_LOCAL_REBUILD**, with the evidence recorded per component (`components[kind]`: `REBUILT_VERIFIED`). This is not normal acceptance.
   - **What this replaces:** the earlier reference labelled any FAILED or MISSING cheap component as "rebuilt" without evidence. That is the corrected bug.
2a. **Lexical-only releases (2.1, CP-1 gap 2).** A release that declares no VECTOR_PACK at `DEGRADED_LEXICAL_ONLY` needs **no model**: it activates with no model installed, or beside a model without vectors for it (B06 K2). Semantic search stays disabled. It never becomes ACTIVE_FULL. FULL still requires a verified model with verified vectors for the release (B06 K1).
4. **Uncalibrated checks (2.1, review C16-I21-01).** The calibration gate applies to the **components in use** (verified, or rebuilt and verified), at **every service level**, and **independently of the result label**.
   - **Production:** any in-use component whose contract has an `UNCALIBRATED` sample size or tolerance gives **REFUSED, `refusal: UNCALIBRATED_IN_PRODUCTION`**. This holds after a local rebuild and for lexical-only service too.
   - **Development:** activation may proceed, and the uncalibrated checks are recorded in `uncalibrated_in_use`.
   - **What this replaces:** the earlier reference tested only `result == ACTIVE_FULL`, so a rebuild relabel bypassed the check.
5. **Explicit, complete inputs (2.1).** Any of the following gives **REFUSED, `refusal: INVALID_INPUT`**:
   - `mode` is not `production` or `development`;
   - an unknown kind or state is given;
   - rebuild evidence is supplied for VECTOR_PACK (the site never embeds).

   A kind omitted from `results` is **MISSING**. Every component in use needs a **validated contract of its own kind** (`contract_issues == []`); a missing, malformed or wrong-kind contract gives **REFUSED, `refusal: CONTRACT_INVALID`**.

**Owner gate OD-C16-UNCALIBRATED-PRODUCTION (OPEN, fails closed).** The open question: may production serve lexical-only service whose LEXICAL_INDEX, GRAPH or rebuilt components were verified with **uncalibrated** sampled checks? The candidates are SAMPLED_POSTINGS_REDERIVE, SAMPLED_QUERY_PARITY and SAMPLED_REBUILD_PARITY. Policy until the owner records a decision (with named checks, the approving authority and the scope) **and** FG-CALIBRATED-SAMPLES supplies calibrated values:
- **No.** Production refuses at every service level.
- No downgrade path serves an accelerator whose correctness rests on an uncalibrated sample.
- Development mode only records the condition.
- The reference code has no approval input, so an approval cannot be injected by a caller.

**Mirror required.** The .NET activation (B06 and the CP-1 `GenerationStaging` outcome) must reproduce these refusal codes and the per-component states `VERIFIED`, `REBUILT_VERIFIED`, `REBUILD_REQUIRED` and `NOT_USED`.

## 3. CP-1 fixture vertical slice

`v2_1/cp1/` contains a fixture MKR-1 manifest and its activation record:
- **Manifest:** `declared_service_level: DEGRADED_LEXICAL_ONLY`, VECTOR_PACK `OMITTED_DEGRADED`, and pending future gates listed.
- **Activation record:** `ACTIVE_DEGRADED`, acknowledged.
- **I-2 (PR #82 clarification 4):** `graph_nodes` and `graph_edges` are `tables` of the **GRAPH** component (`accelerators/graph/graph_nodes.jsonl`, `graph_edges.jsonl`), loaded by the shared typed loader; KNOWLEDGE_ROWS lists only the five reference tables, with their real row files, and its `result_digest` is `table_rows_digest` over them. ADMISSION_REGISTER lists `registers/source_accounting.json`. The earlier CP-1 fixture listed the graph tables under KNOWLEDGE_ROWS; that came from reusing the 2.0 builder's `knowledge_manifest`, whose 2.0 fixtures stay unchanged (frozen) and are not CP-1.

CP-1 is **explicitly degraded**: it is never ACTIVE_FULL, and it closes no FG-* gate on real data. A fixture slice proves the wiring, not real-corpus acceptance.

## 4. Exact component digests (PR #82 clarification 2)

Frozen arch §5 names what each `result_digest` covers; 2.1 fixes the bytes. Where §5 is silent (line terminators, sort order, encodings), **these definitions apply**; none contradicts §5. Reference: `digests.py`. Golden vectors: `v2_1/digests/golden.json` (checked by `test_component_digest_golden_vectors`; the .NET and B02 implementations must reproduce every value). All text is UTF-8, all sorting is ordinal (code point; `StringComparer.Ordinal`), and every hash is lower-case hex SHA-256.

| Kind | `result_digest` preimage | Reference |
| --- | --- | --- |
| KNOWLEDGE_ROWS | for each table in name order: `<table>\|<row_count>\|<rows_sha256>\n`, **including a final LF**; `row_count` is decimal; `rows_sha256` = sha256 of the canonical row file bytes | `table_rows_digest` |
| GRAPH | exactly `GraphStore.Digest`: `<graph_builder_version>\|<node ids sorted, joined by ,>\|<edge ids sorted, joined by ,>`, **no** trailing LF. The `tables` entries also carry per-table `rows_sha256`, checked by SHA256_EACH_FILE and the loader; the GRAPH_DIGEST check compares this value | `graph_digest` |
| LEXICAL_INDEX | the exact bytes of `search.sqlite` (equal to ADR-0007 `MANIFEST.json` `sha256`) | `file_digest` |
| TEXT_STORE | the exact bytes of `text.sqlite` (equal to ADR-0008 `MANIFEST.json` `sha256`) | `file_digest` |
| VECTOR_PACK | for each entry sorted by key bytes: key (16 bytes, little-endian UInt128 as stored in MIMVEC01) then vector (`dim` × float32 little-endian), concatenated with no separators; the file's entry order and trailer do not enter | `vector_pack_digest` |
| ORIGINALS, TEXT_DERIVATIVES | sorted hashes joined by `\n`, **no** trailing LF, ASCII | `hashset_digest` |
| RECORDS, registers | file bytes concatenated in path order (UTF-8 byte order of the path) | `concat_digest` |

**Stream alignment.** B03's `KnowledgeRows.ComponentDigest` already matches KNOWLEDGE_ROWS. B02's `rows_component_digest` (`"\n".join(...)`, no final LF) must add the final LF; the golden file records the no-final-LF value as `wrong_no_final_lf` so the difference is caught. B02's GRAPH (`GraphStore` digest) and LEXICAL_INDEX (`file_sha256`) already match. B02's `hashset_digest` and `concat_digest` match.

## 5. Bundle-independent TEXT_STORE source digest (PR #82 clarification 5)

**Problem.** The staging `DiskTextStore.SourceDigest` hashes `generation.json`, and `generation.json` records the bundle's own `SHA256SUMS` digest. The central build cannot know that digest before the bundle exists, so a prebuilt store's source digest can never equal the site's, and B02 had to declare TEXT_STORE `SITE_BUILDS_CHEAP`.

**2.1 rule.** For SOURCE_DIGEST_EQUALS_SITE on TEXT_STORE, both sides compute `digests.text_store_source_digest(generation_id, documents, derived)`. It covers only what the store is built from:
- the format line `mimamsa-text-store-source/2.1`;
- the corpus generation id;
- each servable document's `doc_id` and copy `sha256`;
- for each derivative: its id (`source_copy_sha256`, pipeline name and version), `text_sha256` and `quoting_permitted`;
- every page's number, method, `char_count`, `low_confidence` and page `text_sha256`;
- every passage's id, page, character span, paragraph label and `text_sha256`.

It includes **no** bundle checksum and **no** `generation.json` bytes.

**Which rule applies.** Frozen arch §5 says the TEXT_STORE source digest "is ADR-0008's (format, generation, per-document derivative identity)". From 2.1, this section governs the value in the manifest. Why: §5 already names those inputs; the ADR-0008 implementation additionally hashes `generation.json`, which makes the value circular. The 2.1 digest keeps §5's inputs (format, generation, per-document derivative identity) and makes them exact, so it narrows the implementation to what §5 describes rather than changing its meaning. The exact line format is in the function's docstring, with golden values in `golden.json` (`TEXT_STORE_SOURCE`).

**Integrity is unchanged.** The digest decides only whether a shipped store may be adopted or must be rebuilt. `DiskTextStore.Bind()` re-derives and compares every document's metadata from the verified records on **every open**, and PAGE_HASH_ON_READ checks every page read, whatever the digest says. A wrong digest can therefore cause, at worst, an unnecessary rebuild or a rejected store, never served text that differs from the verified derivatives.

**Implementation.** B04 implements this in `DiskTextStore` (app code is not changed by this checkpoint). The ADR-0008 digest stays as the store's internal identity; the 2.1 digest is the one placed in `KNOWLEDGE_RELEASE.json` `source_digest` for TEXT_STORE. Once B04 lands, B02 may ship TEXT_STORE prebuilt instead of `SITE_BUILDS_CHEAP`.
