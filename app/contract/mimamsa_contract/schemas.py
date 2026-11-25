"""Local schema registry. No network retrieval: unknown references raise."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas" / "v1"
BASE = "https://contract.mimamsa.invalid/v1/"

KIND_TO_SCHEMA = {
    "document": "document.schema.json",
    "derived_text": "derived_text.schema.json",
    "candidate": "candidate.schema.json",
    "release_manifest": "release_manifest.schema.json",
    "status_axes": "status_axes.schema.json",
    "provenance": "provenance.schema.json",
    "restriction": "restriction.schema.json",
}


def _no_remote(uri: str):
    raise LookupError(f"remote schema retrieval refused (offline contract): {uri}")


@lru_cache(maxsize=1)
def registry() -> Registry:
    resources = []
    for p in sorted(SCHEMA_DIR.glob("*.schema.json")):
        doc = json.loads(p.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(doc)
        expected = BASE + p.name
        if doc.get("$id") != expected:
            raise ValueError(f"{p.name}: $id must be {expected}")
        resources.append((expected, Resource.from_contents(doc, default_specification=DRAFT202012)))
    return Registry(retrieve=_no_remote).with_resources(resources)


@lru_cache(maxsize=None)
def validator(kind: str) -> Draft202012Validator:
    name = KIND_TO_SCHEMA[kind]
    schema = registry().contents(BASE + name)
    return Draft202012Validator(schema, registry=registry(), format_checker=FormatChecker())
