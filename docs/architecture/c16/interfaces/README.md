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
| 5. Activation journal (B06; I-4, I-6) | [B06_ACTIVATION_JOURNAL.md](B06_ACTIVATION_JOURNAL.md) | `ACTIVATION_JOURNAL_RECORD_SCHEMA.json`, `ACTIVATION_SCENARIO_SCHEMA.json`, `ACTIVATION_SCENARIO_OUTCOMES_SCHEMA.json` | `activation.py` (2.0, unchanged), `scenarios.py` | `activation_scenarios/SC01–SC25` and `.expected.json` |
| 6. Component verification (B04; CP-1) | [B04_COMPONENT_VERIFICATION.md](B04_COMPONENT_VERIFICATION.md) | `COMPONENT_VERIFICATION_SCHEMA.json` | `components.py` | `component_contracts/*.json`, `cp1/` |

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
