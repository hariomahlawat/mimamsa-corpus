#!/usr/bin/env python3
"""Audit-work structural/evidence validator; NOT a legal correctness verifier.

Usage:
  python tools/legal_audit/validate.py --schema-check
  python tools/legal_audit/validate.py --batch legal_knowledge/audit_work/PILOT_ID --strict

Requires Python >=3.10 and standard library only.
"""
from __future__ import annotations
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "docs" / "legal-audit" / "schemas"
KINDS = {"source": ("sources", "source_id"),
         "finding": ("findings", "finding_id"),
         "review": ("reviews", "review_id")}
SHA = re.compile(r"^[0-9a-f]{64}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_kind(directory: Path, errors: list[str]):
    out = []
    if not directory.is_dir():
        errors.append(f"Missing required directory: {directory}")
        return out
    paths = sorted(directory.glob("*.json")) + sorted(directory.glob("*.jsonl"))
    for p in paths:
        try:
            if p.suffix == ".jsonl":
                rows = [(n, json.loads(s)) for n, s in enumerate(
                    p.read_text(encoding="utf-8").splitlines(), 1) if s.strip()]
            else:
                obj = read_json(p)
                rows = [(1, r) for r in obj] if isinstance(obj, list) else [(1, obj)]
            for n, record in rows:
                out.append((f"{p}:{n}", record))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"{p}: unreadable/invalid JSON: {exc}")
    return out


def match_type(value, spec):
    choices = spec.get("type", [])
    if isinstance(choices, str):
        choices = [choices]
    if not choices:
        return True
    tests = {
        "string": lambda v: isinstance(v, str),
        "null": lambda v: v is None,
        "boolean": lambda v: type(v) is bool,
        "integer": lambda v: type(v) is int,
        "number": lambda v: type(v) in (int, float),
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list)
    }
    return any(tests[t](value) for t in choices if t in tests)


def validate_record(kind, label, obj, schema, errors):
    if not isinstance(obj, dict):
        errors.append(f"{label}: expected JSON object")
        return
    fields = schema["properties"]
    for key in schema["required"]:
        if key not in obj:
            errors.append(f"{label}: missing {key}")
    if schema.get("additionalProperties") is False:
        for key in set(obj) - set(fields):
            errors.append(f"{label}: unsupported field {key}")
    for key, val in obj.items():
        if key not in fields:
            continue
        spec = fields[key]
        if not match_type(val, spec):
            errors.append(f"{label}: {key} has wrong type")
            continue
        if "enum" in spec and val not in spec["enum"]:
            errors.append(f"{label}: {key} not in enum")
        if isinstance(val, str):
            if len(val.strip()) < spec.get("minLength", 0):
                errors.append(f"{label}: blank {key}")
            if "pattern" in spec and not re.fullmatch(spec["pattern"], val):
                errors.append(f"{label}: {key} pattern mismatch")
            if spec.get("format") == "date":
                try:
                    assert DATE.fullmatch(val)
                    datetime.date.fromisoformat(val)
                except (AssertionError, ValueError):
                    errors.append(f"{label}: invalid ISO date {key}")
        if isinstance(val, list):
            if spec.get("uniqueItems") and len(set(map(str, val))) != len(val):
                errors.append(f"{label}: duplicate values in {key}")
            inner = spec.get("items", {})
            if any(not match_type(item, inner) for item in val):
                errors.append(f"{label}: invalid array element in {key}")
    if kind == "finding":
        if obj.get("severity") in ("P0", "P1") and obj.get("requires_legal_review") is not True:
            errors.append(f"{label}: P0/P1 MUST require legal review")
        if obj.get("verification_state") == "SOURCE_VERIFIED" and not obj.get("source_ids"):
            errors.append(f"{label}: SOURCE_VERIFIED without evidence link")
    if kind == "review":
        if obj.get("decision") == "FORMALLY_APPROVED":
            if obj.get("reviewer_role") != "FORMAL_AUTHORITY" or not obj.get("approval_artifact"):
                errors.append(f"{label}: invalid formal-approval claim")
        if obj.get("decision") == "ACCEPTED_FOR_CANDIDATE" and obj.get("reviewer_role") not in ("LEGAL_ADVISOR", "PROJECT_DIRECTOR"):
            errors.append(f"{label}: unsupported candidate acceptance role")


def validate_batch(batch: Path, strict: bool = False):
    errors = []
    schemas = {kind: read_json(SCHEMAS / f"{kind}.schema.json") for kind in KINDS}
    records = {kind: read_kind(batch / directory, errors)
               for kind, (directory, _) in KINDS.items()}
    ids = {kind: {} for kind in KINDS}
    for kind, items in records.items():
        for label, obj in items:
            validate_record(kind, label, obj, schemas[kind], errors)
            if not isinstance(obj, dict):
                continue
            ident = obj.get(KINDS[kind][1])
            if isinstance(ident, str):
                if ident in ids[kind]:
                    errors.append(f"{label}: duplicate {kind} ID: {ident}")
                ids[kind][ident] = obj
    for label, f in records["finding"]:
        if not isinstance(f, dict):
            continue
        all_src = f.get("source_ids", []) + f.get("contrary_source_ids", [])
        if not isinstance(all_src, list):
            continue
        for sid in all_src:
            if sid not in ids["source"]:
                errors.append(f"{label}: dangling source ID: {sid}")
        if f.get("verification_state") == "SOURCE_VERIFIED":
            for sid in f.get("source_ids", []):
                src = ids["source"].get(sid, {})
                if src.get("verification_state") != "SOURCE_VERIFIED" or not src.get("pinpoint"):
                    errors.append(f"{label}: claimed verified but {sid} lacks source verification/pinpoint")
        if strict and f.get("review_state") == "ACCEPTED_FOR_CANDIDATE":
            if f.get("verification_state") != "SOURCE_VERIFIED":
                errors.append(f"{label}: candidate without verified source")
            if f.get("requires_legal_review"):
                approved = any(r.get("finding_id") == f.get("finding_id")
                               and r.get("reviewer_role") == "LEGAL_ADVISOR"
                               and r.get("decision") == "ACCEPTED_FOR_CANDIDATE"
                               for _, r in records["review"] if isinstance(r, dict))
                if not approved:
                    errors.append(f"{label}: candidate has no legal advisor acceptance")
    for label, r in records["review"]:
        if not isinstance(r, dict):
            continue
        if r.get("finding_id") not in ids["finding"]:
            errors.append(f"{label}: dangling finding ID")
        for sid in r.get("source_ids", []):
            if sid not in ids["source"]:
                errors.append(f"{label}: dangling review source ID: {sid}")
    if strict and not records["finding"]:
        errors.append("Strict validation requires at least one finding, including no-issue finding if applicable")
    print(json.dumps({"batch": str(batch), "counts": {k: len(v) for k, v in records.items()},
                      "strict": strict, "errors": errors}, indent=2))
    return not errors


def schema_check():
    for kind in KINDS:
        p = SCHEMAS / f"{kind}.schema.json"
        schema = read_json(p)
        assert schema["type"] == "object"
        assert schema.get("additionalProperties") is False
        assert set(schema["required"]) <= set(schema["properties"])
    print("Audit schema files readable and internally consistent (not legal verification).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=Path)
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--schema-check", action="store_true")
    args = ap.parse_args()
    try:
        if args.schema_check:
            schema_check()
        if args.batch is None and not args.schema_check:
            ap.error("Provide --batch or --schema-check")
        if args.batch and not validate_batch(args.batch, args.strict):
            return 1
        return 0
    except (OSError, ValueError, json.JSONDecodeError, AssertionError) as exc:
        print(f"VALIDATION ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
