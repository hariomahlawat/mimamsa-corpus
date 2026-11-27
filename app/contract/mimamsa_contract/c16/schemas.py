"""Local registry for the C16 corpus integration schemas (mimamsa-corpus-contract/2.0).

The C16 schemas reuse contract v1 primitives by relative reference (../v1/...), so the registry holds both schema
sets. No network retrieval: an unknown reference raises.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

SCHEMA_ROOT = Path(__file__).resolve().parents[2] / "schemas"
V1_DIR = SCHEMA_ROOT / "v1"
C16_DIR = SCHEMA_ROOT / "c16"
BASE = "https://contract.mimamsa.invalid/"

CONTRACT_ID = "mimamsa-corpus-contract/2.0"

KIND_TO_SCHEMA = {
    "document_identity": "DOCUMENT_IDENTITY_SCHEMA.json",
    "taxonomy_node": "LEGAL_TAXONOMY_SCHEMA.json",
    "corpus_relationship": "PROVISION_JUDGMENT_RELATIONSHIP_SCHEMA.json",
    "evidence_anchor": "OCR_EVIDENCE_ANCHOR_SCHEMA.json",
    "corpus_admission": "CORPUS_ADMISSION_SCHEMA.json",
    "corpus_generation_manifest": "CORPUS_GENERATION_MANIFEST_SCHEMA.json",
    # WP06 knowledge release architecture
    "knowledge_release_manifest": "KNOWLEDGE_RELEASE_MANIFEST_SCHEMA.json",
    "knowledge_activation_record": "KNOWLEDGE_ACTIVATION_RECORD_SCHEMA.json",
    # contract 2.1 (additive, Tranche B interfaces)
    "gate_receipt_artefact": "GATE_RECEIPT_ARTEFACT_SCHEMA.json",
    "mkr_build_spec": "BUILD_SPEC_SCHEMA.json",
    "build_stage_manifest": "BUILD_STAGE_MANIFEST_SCHEMA.json",
    "knowledge_rows_allowlist": "KNOWLEDGE_ROWS_SCHEMA.json",
    "activation_journal_record": "ACTIVATION_JOURNAL_RECORD_SCHEMA.json",
    "activation_scenario": "ACTIVATION_SCENARIO_SCHEMA.json",
    "activation_scenario_outcomes": "ACTIVATION_SCENARIO_OUTCOMES_SCHEMA.json",
    "component_verification_contract": "COMPONENT_VERIFICATION_SCHEMA.json",
}
SHARED = "C16_SHARED_DEFINITIONS_SCHEMA.json"


def _no_remote(uri: str):
    raise LookupError(f"remote schema retrieval refused (offline contract): {uri}")


def schema_files() -> list[Path]:
    return sorted(C16_DIR.glob("*.json"))


@lru_cache(maxsize=1)
def registry() -> Registry:
    resources = []
    for sub, pattern in (("v1", "*.schema.json"), ("c16", "*.json")):
        for p in sorted((SCHEMA_ROOT / sub).glob(pattern)):
            doc = json.loads(p.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(doc)
            expected = f"{BASE}{sub}/{p.name}"
            if doc.get("$id") != expected:
                raise ValueError(f"{sub}/{p.name}: $id must be {expected}")
            resources.append((expected, Resource.from_contents(doc, default_specification=DRAFT202012)))
    return Registry(retrieve=_no_remote).with_resources(resources)


def schema(name: str) -> dict:
    return registry().contents(f"{BASE}c16/{name}")


@lru_cache(maxsize=None)
def validator(kind: str) -> Draft202012Validator:
    return Draft202012Validator(schema(KIND_TO_SCHEMA[kind]), registry=registry(), format_checker=FormatChecker())


def schema_errors(record: dict) -> list[str]:
    """Schema errors for one record, selected by its record_kind. Messages give the JSON path, never a value."""
    if not isinstance(record, dict):
        return ["$: record is not a JSON object"]
    kind = record.get("record_kind")
    if kind not in KIND_TO_SCHEMA:
        return ["$.record_kind: unknown C16 record kind"]
    out = []
    for err in sorted(validator(kind).iter_errors(record), key=lambda e: (list(e.absolute_path), e.validator)):
        path = "$" + "".join(f"[{p}]" if isinstance(p, int) else f".{p}" for p in err.absolute_path)
        out.append(f"{path}: {err.validator} violated")
    return out
