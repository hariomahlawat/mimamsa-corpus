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
    integrity_checks(batch, records, ids, strict, manifest, errors)
    relations = relation_checks(batch, records, ids, errors)
    counts = {k: len(v) for k, v in records.items()}
    if relations is not None:
        counts["relation"] = relations
    print(json.dumps({"batch": str(batch), "counts": counts,
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



# v1 authority-policy compatibility: legacy PILOT-01 entries remain unchanged,
# but newly classified sources must declare BOTH underlying legal authority
# and the provenance/fidelity of the specific copy. This checks metadata claims
# only: it cannot authenticate the document or certify the law in force.
AUTHORITY_META_FIELDS = ("document_authority", "carrier_provenance",
                         "copy_fidelity", "amendment_chain_status")


def authority_provenance_checks(label, source, errors, require_full=False):
    auth = source.get("authenticity")
    has_policy_fields = any(key in source for key in AUTHORITY_META_FIELDS)
    needs_policy = require_full or has_policy_fields or auth in (
        "ARCHIVAL_FACSIMILE_OF_OFFICIAL", "MANUAL_EDITION_CORROBORATED")
    if not needs_policy:
        return  # frozen earlier records; never invent a classification
    for key in AUTHORITY_META_FIELDS:
        if not source.get(key):
            errors.append(f"{label}: source authority policy missing {key}")
    if not source.get("authority_rationale"):
        errors.append(f"{label}: source authority policy requires authority_rationale")

    doc = source.get("document_authority")
    carrier = source.get("carrier_provenance")
    fidelity = source.get("copy_fidelity")
    kind = source.get("source_type")

    if auth == "ARCHIVAL_FACSIMILE_OF_OFFICIAL" or carrier == "THIRD_PARTY_ARCHIVAL_FACSIMILE":
        # A scanned original Government Gazette is primary in *content* but
        # archival in *carrier*. Do not collapse the two into SECONDARY.
        if not (auth == "ARCHIVAL_FACSIMILE_OF_OFFICIAL"
                and carrier == "THIRD_PARTY_ARCHIVAL_FACSIMILE"
                and doc == "ENACTED_OR_NOTIFIED_PRIMARY"
                and kind == "GAZETTE"):
            errors.append(
                f"{label}: official Gazette facsimile must have GAZETTE type, "
                "primary document authority and third-party archival provenance")
        if not source.get("instrument_identity"):
            errors.append(f"{label}: archival Gazette facsimile lacks complete instrument_identity")
        if not source.get("sha256"):
            errors.append(f"{label}: archival Gazette facsimile lacks SHA-256")
        if not source.get("pinpoint"):
            errors.append(f"{label}: archival Gazette facsimile lacks pinpoint")
        if source.get("content_role") not in (None, "GAZETTE_TEXT"):
            errors.append(f"{label}: archival Gazette facsimile must be GAZETTE_TEXT")
        if (source.get("verification_state") == "SOURCE_VERIFIED"
                and fidelity not in ("PAGE_IMAGE_CHECKED", "CUSTODIAN_AUTHENTICATED")):
            errors.append(
                f"{label}: archival Gazette SOURCE_VERIFIED requires page-image "
                "inspection or custodian authentication; HASH_ONLY is insufficient")
    if fidelity == "PAGE_IMAGE_CHECKED" and not source.get("page_image_check_id"):
        errors.append(f"{label}: PAGE_IMAGE_CHECKED requires a page_image_check_id")
    if fidelity == "CUSTODIAN_AUTHENTICATED" and not source.get("custodian_evidence_ref"):
        errors.append(f"{label}: CUSTODIAN_AUTHENTICATED requires custodian_evidence_ref")
    if carrier == "THIRD_PARTY_ARCHIVAL_FACSIMILE" and auth == "ORIGINAL_OFFICIAL":
        errors.append(f"{label}: a third-party hosted facsimile is not an issuing-authority copy")

    if kind == "MANUAL" and doc in (
            "ENACTED_OR_NOTIFIED_PRIMARY", "OFFICIAL_JUDICIAL_DECISION"):
        errors.append(f"{label}: manual text cannot be labelled enacted law or a court holding")
    if doc in ("UNVERIFIED_MANUAL", "GOVERNMENT_ISSUED_MANUAL") and kind != "MANUAL":
        errors.append(f"{label}: manual document authority requires source_type MANUAL")
    if auth == "MANUAL_EDITION_CORROBORATED" or doc == "GOVERNMENT_ISSUED_MANUAL":
        if not (auth == "MANUAL_EDITION_CORROBORATED"
                and doc == "GOVERNMENT_ISSUED_MANUAL"
                and source.get("edition_authority_ref")):
            errors.append(
                f"{label}: claiming official manual edition requires independent "
                "publisher/edition authentication reference")

def extended_checks(records, ids, strict, manifest, errors):
    mml = load_mml_manifest()
    policy = read_json(manifest).get("source_authority_policy_version") if manifest else None
    if policy not in (None, "v1"):
        errors.append(f"Unknown source_authority_policy_version {policy}")
    require_source_policy = strict and policy == "v1"
    # (1) MML provenance and version differentiation
    for label, s in records["source"]:
        if not isinstance(s, dict):
            continue
        if s.get("verification_state") == "SOURCE_VERIFIED" and not s.get("pinpoint"):
            errors.append(f"{label}: SOURCE_VERIFIED source without pinpoint")
        authority_provenance_checks(label, s, errors, require_full=require_source_policy)
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
        # Claims of CURRENT law need a documented amendment chain. This does
        # not assert that a declared 'checked' chain is in fact exhaustive.
        asserted = f.get("asserted_law_status")
        if asserted == "SOURCE_CONFLICT" and vs != "CONFLICTING":
            errors.append(f"{label}: SOURCE_CONFLICT may not be treated as resolved")
        if asserted == "CURRENT_IN_FORCE":
            if vs != "SOURCE_VERIFIED":
                errors.append(f"{label}: CURRENT_IN_FORCE requires SOURCE_VERIFIED evidence")
            if not any(x.get("source_type") in PRIMARY_TYPES
                       and x.get("amendment_chain_status") == "CHECKED_FOR_RELEVANT_PERIOD"
                       and x.get("verification_state") == "SOURCE_VERIFIED"
                       for x in linked):
                errors.append(
                    f"{label}: CURRENT_IN_FORCE requires a verified primary "
                    "source with a checked relevant-period amendment chain")

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
            elif (exact or revs[own].get("require_exact_retrieved_by")) and rb != own:
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


# ---------------------------------------------------------------------------
# WS-D integrity controls (issue #14). Structural/traceability checks only; they
# never certify legal correctness, authenticity or the law in force.
#
# Two tiers:
#  * ALWAYS-ON rules: hold for every batch, including frozen PILOT-01 and
#    R23-VERIFY-01 (both verified to pass unchanged when these rules were added).
#    Several only fire when a newer optional field is present, so legacy entries
#    are never retro-classified.
#  * CONTROLS v2 (opt-in): a NEW batch declares "audit_controls_version": "v2"
#    in its frozen manifest and is validated with --strict. v2 implies source
#    authority policy v1. Unknown versions fail closed. Frozen batches are not
#    migrated silently: their manifests do not carry the flag (a migration would
#    be a separate, reviewed proposal).
CONTROLS_VERSIONS = (None, "v2")
HUMAN_ROLES = {"LEGAL_ADVISOR", "PROJECT_DIRECTOR", "FORMAL_AUTHORITY"}
AGENT_ID = re.compile(r"(-auditor$|^orchestrator|^independent-reviewer|agent|claude|^ws-[a-z])", re.I)
WEAK_PROOF = {"OCR_TEXT", "SEARCH_RESULT_ONLY", "METADATA_ONLY"}
ISO_IN_TEXT = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")
LEADING_DATE = re.compile(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?(?=$|[\s;(,])")
PIC_TOKEN = re.compile(r"PIC-\d+")
STATED = "STATED_IN_INSTRUMENT"
AUDIT_WORK = ROOT / "legal_knowledge" / "audit_work"
KB_FILE = ROOT / "legal_knowledge" / "curated_originals" / "knowledge_base" / "v0.9" / "records_658.jsonl"
CASES_FILE = ROOT / "legal_knowledge" / "curated_originals" / "case_law" / "v0.9" / "cases_53.jsonl"


def known_page_image_checks(batch: Path):
    """check_id values from every page_image_checks*.csv register in the batch and under audit_work."""
    import csv
    ids = set()
    roots = {batch, AUDIT_WORK}
    for root in roots:
        if not root.is_dir():
            continue
        for p in root.rglob("page_image_checks*.csv"):
            with p.open(encoding="utf-8", newline="") as fh:
                ids |= {r.get("check_id", "") for r in csv.DictReader(fh)}
    ids.discard("")
    return ids


def corpus_ids():
    out = set()
    for p in (KB_FILE, CASES_FILE):
        if p.is_file():
            for line in p.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    out.add(json.loads(line).get("id"))
    return out


def _valid_iso_dates(text, label, key, errors):
    for y, m, d in ISO_IN_TEXT.findall(text):
        try:
            datetime.date(int(y), int(m), int(d))
        except ValueError:
            errors.append(f"{label}: {key} contains impossible calendar date {y}-{m}-{d}")


def _leading_date(text):
    m = LEADING_DATE.match(text or "")
    if not m:
        return None
    y, mo, d = m.group(1), m.group(2) or "01", m.group(3) or "01"
    try:
        return datetime.date(int(y), int(mo), int(d))
    except ValueError:
        return None


def source_integrity(label, s, v2, pics, errors):
    kind, doc = s.get("source_type"), s.get("document_authority")
    carrier, fid, auth = s.get("carrier_provenance"), s.get("copy_fidelity"), s.get("authenticity")
    # (a) document authority vs carrier provenance: two independent dimensions (policy v1),
    #     but some combinations are self-contradictory.
    if doc == "OFFICIAL_JUDICIAL_DECISION" and kind not in ("JUDGMENT", "ORDER"):
        errors.append(f"{label}: OFFICIAL_JUDICIAL_DECISION requires source_type JUDGMENT or ORDER")
    if doc == "ENACTED_OR_NOTIFIED_PRIMARY" and kind not in ("STATUTE", "RULE", "GAZETTE", "REGULATION", "OTHER_PRIMARY"):
        errors.append(f"{label}: ENACTED_OR_NOTIFIED_PRIMARY requires a statutory/notified source_type")
    if doc == "THIRD_PARTY_COMMENTARY" and kind != "SECONDARY":
        errors.append(f"{label}: THIRD_PARTY_COMMENTARY requires source_type SECONDARY")
    if doc == "GOVERNMENT_COMPILATION" and auth in ("ORIGINAL_OFFICIAL", "ARCHIVAL_FACSIMILE_OF_OFFICIAL"):
        errors.append(f"{label}: a government compilation is not the original issued instrument")
    if carrier == "USER_SUPPLIED" and fid == "CUSTODIAN_AUTHENTICATED":
        errors.append(f"{label}: a user-supplied copy cannot be custodian-authenticated without a custodian copy")
    if auth == "ORIGINAL_OFFICIAL" and carrier in ("USER_SUPPLIED", "THIRD_PARTY_TRANSCRIPTION", "UNKNOWN"):
        errors.append(f"{label}: ORIGINAL_OFFICIAL is inconsistent with carrier {carrier}")
    # (b) proof type: how the relied-on passage was read. OCR/search/metadata never establish wording.
    proof = s.get("proof_type")
    if proof in WEAK_PROOF and s.get("verification_state") == "SOURCE_VERIFIED":
        errors.append(f"{label}: proof_type {proof} cannot support SOURCE_VERIFIED (read the page image or text)")
    if proof == "PAGE_IMAGE_READING":
        if not s.get("page_image_check_id"):
            errors.append(f"{label}: PAGE_IMAGE_READING requires page_image_check_id")
        if not s.get("render_sha256"):
            errors.append(f"{label}: PAGE_IMAGE_READING requires render_sha256")
    # (c) register cross-reference: every PIC-n cited must exist in a page-image register.
    pic = s.get("page_image_check_id") or ""
    for tok in PIC_TOKEN.findall(pic):
        if tok not in pics:
            errors.append(f"{label}: page_image_check_id cites {tok}, absent from every page_image_checks register")
    # (d) dates: publication, commencement as printed and effective date are distinct (owner rule).
    for key in ("version_or_decision_date", "effective_date", "publication_date", "commencement_as_printed"):
        if isinstance(s.get(key), str):
            _valid_iso_dates(s[key], label, key, errors)
    status = s.get("effective_date_status")
    eff = s.get("effective_date")
    if status is not None:
        if eff and not status.startswith(STATED):
            errors.append(f"{label}: effective_date set but effective_date_status is not {STATED}")
        if status.startswith(STATED) and not (isinstance(eff, str) and ISO_IN_TEXT.search(eff)):
            errors.append(f"{label}: {STATED} requires an ISO effective_date")
    pub = s.get("publication_date")
    if pub and eff and _leading_date(pub) and _leading_date(pub) == _leading_date(eff) and not (status or "").startswith(STATED):
        errors.append(f"{label}: effective_date equals publication_date without a stated commencement")
    if kind in ("JUDGMENT", "ORDER"):
        dd, ro = _leading_date(s.get("version_or_decision_date") or ""), _leading_date(s.get("retrieved_on") or "")
        if dd and ro and dd > ro:
            errors.append(f"{label}: decision date is after retrieved_on")
    if v2:
        if not proof:
            errors.append(f"{label}: controls v2 requires proof_type")
        if kind in DATED_TYPES:
            if status is None:
                errors.append(f"{label}: controls v2 requires effective_date_status on {kind} sources")
            if not _leading_date(s.get("version_or_decision_date") or ""):
                errors.append(f"{label}: controls v2 requires version_or_decision_date to start with an ISO date")
        if fid == "PAGE_IMAGE_CHECKED" and s.get("page_image_check_id") not in pics:
            errors.append(f"{label}: controls v2 requires page_image_check_id to be exactly a registered check_id")


def integrity_checks(batch, records, ids, strict, manifest, errors):
    man = read_json(manifest) if manifest else {}
    version = man.get("audit_controls_version")
    if version not in CONTROLS_VERSIONS:
        errors.append(f"Unknown audit_controls_version {version}")
        return
    v2 = strict and version == "v2"
    if version == "v2" and man.get("source_authority_policy_version") != "v1":
        errors.append("audit_controls_version v2 requires source_authority_policy_version v1")
    pics = known_page_image_checks(batch)
    for label, s in records["source"]:
        if isinstance(s, dict):
            source_integrity(label, s, v2, pics, errors)
    # cross-record relations
    known_records = corpus_ids() | {r.get("record_id") for r in man.get("records", [])}
    for label, f in records["finding"]:
        if not isinstance(f, dict):
            continue
        both = set(f.get("source_ids", [])) & set(f.get("contrary_source_ids", []) or [])
        if both:
            errors.append(f"{label}: source(s) {sorted(both)} listed as both supporting and contrary")
        if man.get("batch_id") and f.get("batch_id") != man["batch_id"]:
            errors.append(f"{label}: batch_id {f.get('batch_id')} differs from manifest batch_id {man['batch_id']}")
        if manifest:
            for rid in f.get("related_record_ids", []) or []:
                if rid not in known_records:
                    errors.append(f"{label}: related_record_id {rid} not found in KB, cases or manifest")
        if v2:
            if not f.get("legal_review_state"):
                errors.append(f"{label}: controls v2 requires legal_review_state on every finding")
            if f.get("review_state") == "ACCEPTED_FOR_CANDIDATE" and not any(
                    isinstance(r, dict) and r.get("finding_id") == f.get("finding_id")
                    and r.get("reviewer_role") in ("LEGAL_ADVISOR", "PROJECT_DIRECTOR")
                    and r.get("decision") == "ACCEPTED_FOR_CANDIDATE" for _, r in records["review"]):
                errors.append(f"{label}: controls v2: ACCEPTED_FOR_CANDIDATE needs a human acceptance review")
    # legal-review-state separation: an agent can never hold a human legal role
    idpath = batch / "reviewer_identities.json"
    cfg = read_json(idpath) if idpath.is_file() else {}
    agents = set(cfg.get("first_pass_agents", [])) | set(cfg.get("reviewers", {}))
    humans = cfg.get("human_reviewers", {})
    for hid, h in humans.items():
        if hid in agents or AGENT_ID.search(hid):
            errors.append(f"reviewer_identities: human reviewer '{hid}' is an agent identity")
        if h.get("role") not in HUMAN_ROLES or not h.get("binding_evidence"):
            errors.append(f"reviewer_identities: human reviewer '{hid}' needs a human role and binding_evidence")
    for label, r in records["review"]:
        if not isinstance(r, dict):
            continue
        f = ids["finding"].get(r.get("finding_id"), {})
        if r.get("reviewed_original_sha256") and f.get("original_sha256") and r["reviewed_original_sha256"] != f["original_sha256"]:
            errors.append(f"{label}: reviewed_original_sha256 differs from the finding's original_sha256")
        if r.get("reviewer_role") in HUMAN_ROLES:
            rid = r.get("reviewer_id", "")
            if rid in agents or AGENT_ID.search(rid) or rid == f.get("agent"):
                errors.append(f"{label}: agent identity '{rid}' cannot assert human role {r.get('reviewer_role')}")
            if v2:
                if humans.get(rid, {}).get("role") != r.get("reviewer_role"):
                    errors.append(f"{label}: controls v2: '{rid}' not bound as {r.get('reviewer_role')} in human_reviewers")
                if r.get("decision") in ("ACCEPTED_FOR_CANDIDATE", "FORMALLY_APPROVED") and not r.get("approval_artifact"):
                    errors.append(f"{label}: controls v2: acceptance/approval requires an approval_artifact")


# ---------------------------------------------------------------------------
# Optional KB relation layer (WS-C CC-13; coordinator approval, WS-D cycle 2).
# A batch MAY contain relations/*.json validated against relation.schema.json.
# 'manual_supported' is a retrieval/support link to a page-image-checked MML
# locator. It is never statutory or judicial authority: it cannot be cited as a
# finding source, cannot share an ID with a source, and must declare
# legal_effect NOT_STATUTORY_AUTHORITY (schema enum). Batches without the
# directory are unaffected.
def page_image_renders(batch: Path):
    """{check_id: has 64-hex render_png_sha256} from every page-image register."""
    import csv
    out = {}
    for root in {batch, AUDIT_WORK}:
        if not root.is_dir():
            continue
        for p in list(root.rglob("page_image_checks*.csv")) + list(root.rglob("identity_transcription_register*.csv")):
            with p.open(encoding="utf-8", newline="") as fh:
                for r in csv.DictReader(fh):
                    cid = (r.get("check_id") or "").strip()
                    if cid:
                        out[cid] = out.get(cid, False) or bool(SHA.fullmatch((r.get("render_png_sha256") or "").strip()))
    return out


def relation_checks(batch, records, ids, errors):
    d = batch / "relations"
    if not d.is_dir():
        return None
    schema = read_json(SCHEMAS / "relation.schema.json")
    rels = read_kind(d, errors)
    mml = load_mml_manifest()
    renders = page_image_renders(batch)
    known = corpus_ids()
    seen = {}
    for label, r in rels:
        validate_record("relation", label, r, schema, errors)
        if not isinstance(r, dict):
            continue
        rid = r.get("relation_id")
        if rid in seen:
            errors.append(f"{label}: duplicate relation ID: {rid}")
        seen[rid] = r
        if rid in ids["source"]:
            errors.append(f"{label}: relation ID {rid} collides with a source ID")
        if mml is None or r.get("mml_file") not in mml:
            errors.append(f"{label}: mml_file is not one of the MML manifest originals")
        elif r.get("mml_file_sha256") != mml[r["mml_file"]]:
            errors.append(f"{label}: mml_file_sha256 does not match the MML manifest")
        if not renders.get(r.get("page_image_check_id")):
            errors.append(f"{label}: page_image_check_id must resolve to a page-image register row with a render hash")
        if r.get("from_record_id") not in known:
            errors.append(f"{label}: from_record_id {r.get('from_record_id')} not in the frozen KB/cases")
        if r.get("document_authority") == "GOVERNMENT_ISSUED_MANUAL" and not r.get("edition_authority_ref"):
            errors.append(f"{label}: GOVERNMENT_ISSUED_MANUAL requires edition_authority_ref")
    for label, f in records["finding"]:
        if not isinstance(f, dict):
            continue
        for sid in (f.get("source_ids") or []) + (f.get("contrary_source_ids") or []) + (f.get("mml_anchor_ids") or []):
            if sid in seen:
                errors.append(f"{label}: manual_supported relation {sid} cannot be cited as finding evidence (not statutory authority)")
    for label, r in records["review"]:
        if isinstance(r, dict):
            for sid in (r.get("source_ids") or []) + (r.get("independent_source_ids") or []):
                if sid in seen:
                    errors.append(f"{label}: relation {sid} cannot be cited as review evidence")
    return len(rels)


def schema_check():
    rel = read_json(SCHEMAS / "relation.schema.json")
    assert rel["type"] == "object" and rel.get("additionalProperties") is False
    assert set(rel["required"]) <= set(rel["properties"])
    assert rel["properties"]["legal_effect"]["enum"] == ["NOT_STATUTORY_AUTHORITY"]
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
