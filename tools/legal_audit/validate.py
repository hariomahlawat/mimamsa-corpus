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


def validate_batch(batch: Path, strict: bool = False, manifest: Path | None = None):
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
        # Manual passage authentication and binding-law verification are different.
        # A statutory, judicial or procedural legal conclusion cannot be marked
        # SOURCE_VERIFIED solely because an MML manual/secondary text corroborates it.
        if (f.get("verification_state") == "SOURCE_VERIFIED"
                and f.get("workstream") in ("STATUTORY", "JUDGMENT", "PROCEDURE")):
            legal_primary_types = {"STATUTE", "RULE", "GAZETTE", "REGULATION",
                                   "JUDGMENT", "ORDER", "OTHER_PRIMARY"}
            linked = [ids["source"].get(sid, {}) for sid in f.get("source_ids", [])]
            if not any(src.get("source_type") in legal_primary_types
                       and src.get("verification_state") == "SOURCE_VERIFIED"
                       and src.get("pinpoint") for src in linked):
                errors.append(
                    f"{label}: legal conclusion marked SOURCE_VERIFIED without "
                    "pinpointed verified primary legal authority (manual-only inadequate)"
                )
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
    extended_checks(records, ids, strict, manifest, errors)
    identity_checks(batch, records, ids, strict, errors)
    print(json.dumps({"batch": str(batch), "counts": {k: len(v) for k, v in records.items()},
                      "strict": strict, "errors": errors}, indent=2))
    return not errors


# ---------------------------------------------------------------------------
# Extended controls (PILOT-01). Structural/traceability checks only; they never
# certify legal correctness.
MML_MANIFEST = ROOT / "legal_knowledge" / "manual_sources" / "MML_Originals_Manifest.csv"
PRIMARY_TYPES = {"STATUTE", "RULE", "GAZETTE", "REGULATION", "JUDGMENT", "ORDER", "OTHER_PRIMARY"}
DATED_TYPES = {"STATUTE", "RULE", "GAZETTE", "REGULATION"}
MANUAL_AUTH = {"USER_SUPPLIED_REFERENCE", "MANUAL_EDITION_CORROBORATED", "SECONDARY", "UNCONFIRMED"}


def load_mml_manifest():
    import csv
    if not MML_MANIFEST.is_file():
        return None
    with MML_MANIFEST.open(encoding="utf-8") as fh:
        return {r["filename"]: r["sha256"] for r in csv.DictReader(fh)}


def load_pilot_manifest(path: Path):
    """{record_id: sha256}. Accepts {'records': [{'record_id','original_sha256'|'original_line_sha256'}]}."""
    obj = read_json(path)
    out = {}
    for r in obj.get("records", []):
        out[r["record_id"]] = r.get("original_sha256") or r.get("original_line_sha256")
    return out


def extended_checks(records, ids, strict, manifest, errors):
    mml = load_mml_manifest()
    # (1) MML provenance and version differentiation
    for label, s in records["source"]:
        if not isinstance(s, dict):
            continue
        if s.get("verification_state") == "SOURCE_VERIFIED" and not s.get("pinpoint"):
            errors.append(f"{label}: SOURCE_VERIFIED source without pinpoint")
        if s.get("source_type") == "MANUAL":
            where = f"{s.get('local_path') or ''} {s.get('locator') or ''}"
            names = [n for n in (mml or {}) if n in where]
            # prefer the longest match ("MML vol 2(AA).pdf" contains no shorter alias issues)
            names = sorted(names, key=len, reverse=True)[:1]
            if mml is None:
                errors.append(f"{label}: MML manifest unavailable; manual provenance cannot be checked")
            elif not names:
                errors.append(f"{label}: MANUAL source does not name one of the eight MML originals")
            elif s.get("sha256") != mml[names[0]]:
                errors.append(f"{label}: MANUAL source sha256 does not match manifest for '{names[0]}'")
            if not s.get("pinpoint"):
                errors.append(f"{label}: MANUAL source lacks page/paragraph pinpoint")
            if s.get("authenticity") not in MANUAL_AUTH:
                errors.append(f"{label}: MANUAL source cannot carry official authenticity '{s.get('authenticity')}'")
            if s.get("content_role") not in (None, "MANUAL_REPRODUCED_LEGAL_TEXT", "MANUAL_COMMENTARY"):
                errors.append(f"{label}: MANUAL source content_role must distinguish reproduced text vs commentary")
            if strict and not s.get("content_role"):
                errors.append(f"{label}: strict: MANUAL source must state content_role")
    # (2) findings: manifest integrity, states, traceability
    pm = load_pilot_manifest(manifest) if manifest else None
    covered = set()
    for label, f in records["finding"]:
        if not isinstance(f, dict):
            continue
        rid, vs, out = f.get("record_id"), f.get("verification_state"), f.get("examination_outcome")
        if pm is not None:
            if rid not in pm:
                errors.append(f"{label}: record_id {rid} not in pilot manifest")
            elif f.get("original_sha256") != pm[rid]:
                errors.append(f"{label}: original_sha256 does not match frozen input hash for {rid}")
            elif out and f.get("workstream") != "INDEPENDENT_REVIEW":
                covered.add(rid)
        linked = [ids["source"].get(x, {}) for x in f.get("source_ids", [])]
        # manual-only verification blocked for every legal workstream (DATA_QUALITY exempt)
        if vs == "SOURCE_VERIFIED" and f.get("workstream") != "DATA_QUALITY":
            if not any(x.get("source_type") in PRIMARY_TYPES and x.get("verification_state") == "SOURCE_VERIFIED"
                       and x.get("pinpoint") for x in linked):
                errors.append(f"{label}: SOURCE_VERIFIED needs a pinpointed verified primary authority (manual/secondary alone inadequate)")
        # pinpoint + effective-date traceability
        if vs in ("SOURCE_VERIFIED", "CONFLICTING"):
            for x in linked + [ids["source"].get(y, {}) for y in f.get("contrary_source_ids", [])]:
                if not x:
                    continue
                if x.get("source_type") in PRIMARY_TYPES and not x.get("pinpoint"):
                    errors.append(f"{label}: cited primary source {x.get('source_id')} lacks pinpoint")
                if x.get("source_type") in DATED_TYPES and not (x.get("effective_date") or x.get("version_or_decision_date")):
                    errors.append(f"{label}: cited {x.get('source_type')} {x.get('source_id')} lacks version/effective date")
                if x.get("source_type") in ("JUDGMENT", "ORDER") and not x.get("version_or_decision_date"):
                    errors.append(f"{label}: cited judgment {x.get('source_id')} lacks decision date")
            if strict and not f.get("temporal_scope"):
                errors.append(f"{label}: strict: verified/conflicting finding lacks temporal_scope")
        # separation of verified / conflicting / unverified / legally reviewed states
        if strict and not out:
            errors.append(f"{label}: strict: examination_outcome missing")
        if out == "NO_ISSUE_FOUND" and vs != "SOURCE_VERIFIED":
            errors.append(f"{label}: NO_ISSUE_FOUND requires SOURCE_VERIFIED evidence")
        if (out == "CONFLICTING_SOURCES") != (vs == "CONFLICTING"):
            errors.append(f"{label}: CONFLICTING outcome and verification_state must agree")
        if out in ("UNVERIFIED", "BLOCKED") and vs == "SOURCE_VERIFIED":
            errors.append(f"{label}: {out} outcome cannot carry SOURCE_VERIFIED")
        if out == "BLOCKED" and f.get("review_state") != "BLOCKED":
            errors.append(f"{label}: BLOCKED outcome requires review_state BLOCKED")
        if (f.get("severity") in ("P0", "P1") or vs == "CONFLICTING") and not f.get("requires_legal_review"):
            errors.append(f"{label}: P0/P1/conflict must require legal review")
        lrs = f.get("legal_review_state")
        if f.get("requires_legal_review") and lrs == "NOT_REQUIRED":
            errors.append(f"{label}: legal_review_state NOT_REQUIRED contradicts requires_legal_review")
        if lrs == "ADVISOR_REVIEWED" and not any(
                isinstance(r, dict) and r.get("finding_id") == f.get("finding_id")
                and r.get("reviewer_role") == "LEGAL_ADVISOR" for _, r in records["review"]):
            errors.append(f"{label}: ADVISOR_REVIEWED claimed without a LEGAL_ADVISOR review record")
        if strict and f.get("requires_legal_review") and not lrs:
            errors.append(f"{label}: strict: legal_review_state missing")
        for a in f.get("mml_anchor_ids", []):
            if ids["source"].get(a, {}).get("source_type") != "MANUAL":
                errors.append(f"{label}: mml_anchor_id {a} is not a registered MANUAL source")
    if pm is not None and strict:
        for rid in sorted(set(pm) - covered):
            errors.append(f"pilot manifest: {rid} has no first-pass finding with an examination_outcome")
    # (3) independent reviewer evidence
    for label, r in records["review"]:
        if not isinstance(r, dict) or r.get("reviewer_role") != "INDEPENDENT_AGENT":
            continue
        if r.get("decision") in ("ACCEPTED_FOR_CANDIDATE", "FORMALLY_APPROVED"):
            errors.append(f"{label}: independent agent cannot accept or approve")
        if r.get("decision") in ("SUPPORTS", "DISPUTES"):
            own = r.get("independent_source_ids") or []
            fsrc = set(ids["finding"].get(r.get("finding_id"), {}).get("source_ids", []))
            good = [x for x in own if x in ids["source"]
                    and str(ids["source"][x].get("retrieved_by", "")).startswith("independent-reviewer")
                    and ids["source"][x].get("pinpoint") and x not in fsrc]
            if not good:
                errors.append(f"{label}: SUPPORTS/DISPUTES without reviewer-retrieved, pinpointed independent evidence")
            for x in own:
                if x not in r.get("source_ids", []):
                    errors.append(f"{label}: independent_source_ids must also appear in source_ids")


def identity_checks(batch, records, ids, strict, errors):
    """Reviewer identity controls (remediation R4). Uses batch/reviewer_identities.json:
    {"first_pass_agents": [...], "require_exact_retrieved_by": bool,
     "reviewers": {"<reviewer_id>": {"stage": "blind"|"adversarial", "source_prefixes": [...], "finding_prefixes": [...]}}}"""
    path = batch / "reviewer_identities.json"
    has_indep = any(isinstance(r, dict) and r.get("reviewer_role") == "INDEPENDENT_AGENT" for _, r in records["review"]) or any(
        isinstance(f, dict) and f.get("workstream") == "INDEPENDENT_REVIEW" for _, f in records["finding"])
    if not path.is_file():
        if strict and has_indep:
            errors.append("strict: independent review present but reviewer_identities.json missing")
        return
    cfg = read_json(path)
    revs = cfg.get("reviewers", {})
    first = set(cfg.get("first_pass_agents", []))
    exact = cfg.get("require_exact_retrieved_by", False)
    owner_of = lambda sid: next((rid for rid, c in revs.items() for p in c.get("source_prefixes", []) if sid.startswith(p)), None)
    fowner_of = lambda fid: next((rid for rid, c in revs.items() for p in c.get("finding_prefixes", []) if fid.startswith(p)), None)
    if set(revs) & first:
        errors.append("reviewer_identities: a reviewer is also declared as a first-pass agent")
    for label, s in records["source"]:
        if not isinstance(s, dict):
            continue
        rb, sid = s.get("retrieved_by", ""), s.get("source_id", "")
        own = owner_of(sid)
        if rb.startswith("independent-reviewer"):
            if own is None:
                errors.append(f"{label}: reviewer-retrieved source {sid} not bound to any declared reviewer prefix")
            elif exact and rb != own:
                errors.append(f"{label}: retrieved_by '{rb}' must equal reviewer id '{own}'")
        elif own is not None:
            errors.append(f"{label}: source {sid} uses reviewer {own}'s prefix but retrieved_by is '{rb}'")
    for label, f in records["finding"]:
        if not isinstance(f, dict):
            continue
        fid = f.get("finding_id", "")
        if f.get("workstream") == "INDEPENDENT_REVIEW":
            fo = fowner_of(fid)
            if fo is None:
                errors.append(f"{label}: INDEPENDENT_REVIEW finding {fid} not bound to a declared reviewer")
            for sid in f.get("source_ids", []) + f.get("contrary_source_ids", []):
                if fo and owner_of(sid) not in (fo,) and sid in ids["source"] and ids["source"][sid].get("retrieved_by") in first:
                    errors.append(f"{label}: blind/independent finding relies on first-pass source {sid}")
        else:
            for sid in f.get("source_ids", []) + f.get("contrary_source_ids", []):
                if owner_of(sid):
                    errors.append(f"{label}: first-pass finding cites reviewer source {sid} (independence leak)")
    for label, r in records["review"]:
        if not isinstance(r, dict) or r.get("reviewer_role") != "INDEPENDENT_AGENT":
            continue
        rid = r.get("reviewer_id")
        if rid not in revs:
            errors.append(f"{label}: reviewer_id '{rid}' not declared in reviewer_identities.json")
            continue
        f = ids["finding"].get(r.get("finding_id"), {})
        if f.get("agent") == rid or fowner_of(f.get("finding_id", "")) == rid:
            errors.append(f"{label}: reviewer {rid} is reviewing its own finding")
        if r.get("blind") and revs[rid].get("stage") != "blind":
            errors.append(f"{label}: blind=true but reviewer {rid} is not a blind-stage reviewer")
        for sid in r.get("independent_source_ids") or []:
            if owner_of(sid) != rid:
                errors.append(f"{label}: independent source {sid} does not belong to reviewer {rid}")


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
    ap.add_argument("--manifest", type=Path, help="pilot manifest JSON with frozen record hashes")
    args = ap.parse_args()
    try:
        if args.schema_check:
            schema_check()
        if args.batch is None and not args.schema_check:
            ap.error("Provide --batch or --schema-check")
        if args.batch and not validate_batch(args.batch, args.strict, args.manifest):
            return 1
        return 0
    except (OSError, ValueError, json.JSONDecodeError, AssertionError) as exc:
        print(f"VALIDATION ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
