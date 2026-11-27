# C16 Tranche B Stage 1: interface checkpoint (contract 2.1)

- **Status:** proposed interfaces, for independent review **before** Stage 2 integrates. Nothing here is site code. No application, v1, AUTH-LEDGER or oracle change.
- **Base:** `legal-knowledge/v2.5-staging` at `5bdc8e68`, where contract 2.0 is merged and **frozen**.
- **Plan:** [C16_TRANCHE_B_IMPLEMENTATION_PLAN](../C16_TRANCHE_B_IMPLEMENTATION_PLAN.md) (PR #81, `claude/c16-tranche-b-plan`), accepted with conditions (review 6091110910: I-1 … I-6, CP-1, shared-host budget, no site embedding).

## Versioning

Every interface here is an **additive contract 2.1** item:
- **New record kinds and schemas only:** no 2.0 schema, rule or fixture changes meaning.
- **Version field.** New records carry `contract: "mimamsa-corpus-contract/2.1"`. A 2.1 exchange declares `"mimamsa-corpus-contract/2.1"` in `GENERATION.json`; 2.0 records inside it are unchanged.
- **Compatibility statement:**
  - a 2.0 exchange stays valid under 2.0 rules;
  - it carries no receipt artefacts, so **it is never importable with eligible admissions** (`C16_RECEIPTS_REQUIRE_2_1`, fail closed);
  - its held, rejected and ineligible items remain importable, and are not served.

## Index

| Item | Document | Schemas (`app/contract/schemas/c16/`) | Reference code (`app/contract/mimamsa_contract/c16/`) | Fixtures (`app/contract/fixtures/c16/v2_1/`) |
| --- | --- | --- | --- | --- |
| 1. Typed gate-receipt artefacts (I-1, FG-RECEIPTS interface) | [CONTRACT_2_1_GATE_RECEIPTS.md](CONTRACT_2_1_GATE_RECEIPTS.md) | `GATE_RECEIPT_ARTEFACT_SCHEMA.json` | `receipts.py` | `exchange/`, `registers/receipts/`, `site_facts.json`, `negative_receipts/NR01–NR18` |
| 2. Producer/consumer interface (B01; I-5) | [B01_PRODUCER_CONSUMER_INTERFACE.md](B01_PRODUCER_CONSUMER_INTERFACE.md) | 2.0 schemas plus the receipt schema | `rules.py` (2.0), `receipts.py`, `legacy.py` (I-5 establishment, per-source accounting) | `exchange/` |
| 3. Central build spec (B02) | [B02_CENTRAL_BUILD_SPEC.md](B02_CENTRAL_BUILD_SPEC.md) | `BUILD_SPEC_SCHEMA.json`, `BUILD_STAGE_MANIFEST_SCHEMA.json` | `build_spec.py` | `build/spec.json`, `build/stages/S0–S9.json` |
| 4. Knowledge-row format (B03; I-2, I-3) | [B03_KNOWLEDGE_ROWS.md](B03_KNOWLEDGE_ROWS.md) | `KNOWLEDGE_ROWS_SCHEMA.json` | `knowledge_rows.py` | `knowledge_rows/allowlist.json`, `knowledge_rows/rows/*.jsonl` |
| 5. Activation journal (B06; I-4, I-6) | [B06_ACTIVATION_JOURNAL.md](B06_ACTIVATION_JOURNAL.md) | `ACTIVATION_JOURNAL_RECORD_SCHEMA.json`, `ACTIVATION_SCENARIO_SCHEMA.json`, `ACTIVATION_SCENARIO_OUTCOMES_SCHEMA.json` | `activation.py` (2.0 model; one 2.1 additive extension, item 10, inert under the 2.0 defaults), `scenarios.py` | `activation_scenarios/SC01–SC25` and `.expected.json` |
| 6. Component verification (B04; CP-1) | [B04_COMPONENT_VERIFICATION.md](B04_COMPONENT_VERIFICATION.md) | `COMPONENT_VERIFICATION_SCHEMA.json` | `components.py` | `component_contracts/*.json`, `cp1/` |
| 7. Per-source accounting register (B01, B02; PR #82 clarification 1) | [B01 §5a](B01_PRODUCER_CONSUMER_INTERFACE.md) | `SOURCE_ADMISSION_ACCOUNTING_SCHEMA.json` | `accounting.py` | `accounting/declared.json`, `recomputed.json`, `negative/NA01–NA10`, `NC01–NC04` |
| 8. Exact component digests and the text-store source digest (PR #82 clarifications 2, 5) | [B04 §4–5](B04_COMPONENT_VERIFICATION.md) | none | `digests.py` | `digests/golden.json` |
| 9. v7 candidate-set files (CP-1 gap 1) | [B01 §5a](B01_PRODUCER_CONSUMER_INTERFACE.md) | none (plain-text file; bound by `candidate_set_sha256`) | `accounting.candidate_set_issues` | `accounting/registers/candidate_sets/`, `accounting/candidate_set_negative/CS01–CS13` |
| 10. Lexical-only releases and model compatibility (CP-1 gap 2) | [B06](B06_ACTIVATION_JOURNAL.md), [B04 §2](B04_COMPONENT_VERIFICATION.md) | `ACTIVATION_SCENARIO_SCHEMA.json`, `ACTIVATION_SCENARIO_OUTCOMES_SCHEMA.json` (both widened additively) | `activation.Site.model_gate`, `semantic_search_enabled`; `scenarios.py` | `activation_scenarios/SC26–SC31` |

## Where 2.1 governs over frozen 2.0 prose (PR #82)

No 2.0 schema, fixture or document is edited. The only 2.0 code touched is `activation.py`, extended additively for item 10: the gate moved into `model_gate`, with new optional `lexical_only` and `models=None` inputs. With the 2.0 defaults the behaviour is identical, and SC01–SC25 and the frozen 2.0 activation tests are byte- and result-identical. Where 2.0 prose differs from 2.1, the 2.1 rule applies to 2.1 producers, builds and sites, for the stated reason. Each is a tightening or a byte-level precision, never a relaxation.

| Frozen 2.0 text | 2.1 rule | Why | Where |
| --- | --- | --- | --- |
| arch §7.3: the staging schema is owned by `mimamsa_kr_loader`, with CREATE on it | the activator creates and owns staging; the loader gets USAGE and INSERT only, no DDL; the site DB revokes TEMPORARY, and CREATE on `public`, from PUBLIC | CREATE would let the loader plant objects the activator later touches | [B03 §4](B03_KNOWLEDGE_ROWS.md) |
| arch §5: KNOWLEDGE_ROWS digest "over `table \| row_count \| rows_sha256`" (terminator unstated) | one LF-terminated line per table, including the last | §5 left the bytes open; B02 and B03 differed | [B04 §4](B04_COMPONENT_VERIFICATION.md) |
| arch §5: the TEXT_STORE source digest is ADR-0008's | bundle-independent `text_store_source_digest` over the same named inputs | the ADR-0008 implementation hashes `generation.json`, which contains the bundle's own checksum (circular) | [B04 §5](B04_COMPONENT_VERIFICATION.md) |
| B01 interface §5.4: per-source accounting "recorded" (format open) | one register: `registers/source_accounting.json`, kind `source_admission_accounting` | B01 and B02 had diverged | [B01 §5a](B01_PRODUCER_CONSUMER_INTERFACE.md) |
| arch §8: "a KNOWLEDGE transition needs the active model's vectors for the target" | unchanged for every release except a lexical-only one (no VECTOR_PACK, DEGRADED_LEXICAL_ONLY), which needs no model; semantic search stays off; FULL is unchanged | a lexical-only release has no vectors by construction; the old wording forced placeholder models | [B06](B06_ACTIVATION_JOURNAL.md) |
| B01 §5a register (2.1): v7 carries only `candidate_set_sha256` | plus `registers/candidate_sets/<name>.txt`, the exact preimage | the I-5 relabel check needs the hashes | [B01 §5a](B01_PRODUCER_CONSUMER_INTERFACE.md) |
| 2.0 fixture `knowledge_manifest` lists graph tables under KNOWLEDGE_ROWS | CP-1 (2.1) lists them under GRAPH (I-2) | the 2.0 fixture predates I-2; it is frozen and is not CP-1 | [B04 §3](B04_COMPONENT_VERIFICATION.md) |

**Tests:**
- `app/contract/tests/test_c16_interfaces.py`, in the existing CI contract job.
- `build_fixtures_2_1.py --check` (2.1 fixtures).
- The frozen 2.0 tests run unchanged.

## What Stage 1 does not do

- **No closed gates.** No FG-* gate is closed by this checkpoint.
- **Not implemented here:** the site importer, row loader, journal, accelerator verification and build pipeline (Stage 2: B01–B06).
- **Calibration.** Sample sizes and tolerances stay `UNCALIBRATED` (FG-CALIBRATED-SAMPLES).
- **Not changed:** trust keys and trust lists (D3, FG-MODEL-TRUST-PURPOSE).
- **Not done:** HF writes, ingestion, admission decisions, Codex review.
