"""Load the Mimamsa JSON Schemas and validate records against them."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schema"
SCHEMAS = {
    "document": "document.schema.json",
    "section": "section.schema.json",
    "relation": "relation.schema.json",
    "correspondence": "correspondence.schema.json",
}


@lru_cache(maxsize=1)
def _registry() -> Registry:
    resources = []
    for fname in SCHEMAS.values():
        contents = json.loads((SCHEMA_DIR / fname).read_text(encoding="utf-8"))
        res = Resource.from_contents(contents)
        # Register under the $id and under the bare filename used in relative $refs.
        resources += [(contents["$id"], res), (fname, res)]
    return Registry().with_resources(resources)


@lru_cache(maxsize=None)
def validator(kind: str) -> Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / SCHEMAS[kind]).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, registry=_registry(), format_checker=FormatChecker())


def errors(kind: str, record: dict) -> list[str]:
    """Return human-readable validation errors (empty list = valid)."""
    out = []
    for e in sorted(validator(kind).iter_errors(record), key=lambda e: list(e.path)):
        path = "/".join(str(p) for p in e.path) or "<root>"
        out.append(f"{path}: {e.message}")
    # Cross-field rule the schema cannot express.
    if kind == "document":
        for i, rel in enumerate(record.get("relations", [])):
            if rel.get("source_doc_id") != record.get("doc_id"):
                out.append(f"relations/{i}/source_doc_id: must equal doc_id")
    return out
