"""Contract 2.1 (additive): typed gate-receipt artefacts and their fail-closed resolution at signed import.

Contract 2.0 (frozen) types the receipt REFERENCE on an admission gate (CORPUS_ADMISSION_SCHEMA $defs/receipt). 2.1
types the ARTEFACT it hashes (GATE_RECEIPT_ARTEFACT_SCHEMA.json) and defines how the signed importer resolves it:

1. locate:   registers/receipts/<sha256>.json, listed in the ADMISSION_REGISTER component inventory, bytes hash to
             the name and are canonical JSON;
2. parse:    the artefact validates against its schema and its own payload semantics (artefact_issues);
3. bind:     gate, kind, copy, generation, derivative, rule id and version, config, register revision and outcome
             equal the admission's receipt and gate result; the artefact is the head of its revision chain;
4. relate:   the payload agrees with the exchange (hash = copy, identity record hash, derivative and coverage,
             image inventory, copy-records digest);
5. recompute: for SITE_RECOMPUTABLE kinds the site's own recomputed facts must be supplied and must agree;
             ASSERTED_BOUND kinds (G04, G08, G09) are recorded as asserted-and-bound, never as site-verified.

Fail closed: a missing, unparseable, unbound or unverifiable receipt makes the admission ineligible, and an eligible
admission in a 2.0 exchange (no artefacts) is never importable as eligible. Hash existence alone never passes.
"""
from __future__ import annotations

import hashlib
import json
import re

from ..issues import Issue
from . import canonical
from .schemas import schema_errors

RECEIPT_PATH = re.compile(r"^registers/receipts/(?P<sha>[0-9a-f]{64})\.json$")
SITE_RECOMPUTABLE = {"HASH_REDOWNLOAD", "FORMAT_DETECTION", "REGISTER_CHECK", "IDENTITY_VALIDATION",
                     "DERIVATIVE_VERIFICATION", "IMAGE_ACCOUNTING", "SCHEMA_VALIDATION"}
CONTRACT_2_1 = "mimamsa-corpus-contract/2.1"


def _e(code, msg, where=""):
    return Issue(code, msg, where)


def artefact_bytes(a: dict) -> bytes:
    return canonical.canonical_bytes(a)


def artefact_sha256(a: dict) -> str:
    return hashlib.sha256(artefact_bytes(a)).hexdigest()


def artefact_path(a: dict) -> str:
    return f"registers/receipts/{artefact_sha256(a)}.json"


def copy_records_digest(identity: dict, anchors: list[dict], relationships: list[dict]) -> str:
    """G10 scope: the copy's own non-admission records, canonical and sorted (identity, its anchors, its
    relationships). Binding to GENERATION.json would be circular (it hashes the admissions file)."""
    key = (identity["doc_id"], identity["source_copy"]["sha256"])
    mine_a = sorted((a for a in anchors if (a["doc_id"], a["original_sha256"]) == key), key=lambda a: a["anchor_id"])
    mine_r = sorted((r for r in relationships if (r["subject"]["doc_id"], r["subject"]["source_copy_sha256"]) == key),
                    key=lambda r: r["relationship_id"])
    return hashlib.sha256(canonical.canonical_bytes([identity, mine_a, mine_r])).hexdigest()


def artefact_issues(a) -> list[Issue]:
    """Schema plus internal payload semantics (an outcome must follow from its own payload)."""
    if not isinstance(a, dict):
        return [_e("JSONL_NOT_OBJECT", "receipt artefact is not a JSON object")]
    errs = [_e("SCHEMA", m, "gate_receipt_artefact") for m in schema_errors(a)]
    if errs:
        return errs
    p, k, ok = a["payload"], a["receipt_kind"], a["outcome"] == "PASS"
    bad = None
    if k == "HASH_REDOWNLOAD" and ok != (p["measured_sha256"] == a["subject"]["source_copy_sha256"]):
        bad = "hash receipt outcome does not follow from the measured hash"
    elif k == "REGISTER_CHECK" and ok != (p["matches"] == 0):
        bad = "register receipt outcome does not follow from the match count"
    elif k in ("IDENTITY_VALIDATION", "SCHEMA_VALIDATION") and ok != (p["issues"] == 0):
        bad = "validation receipt outcome does not follow from the issue count"
    elif k == "DERIVATIVE_VERIFICATION" and (len(p["unit_text_sha256"]) != p["units_total"] or p["units_with_text"] > p["units_total"]
                                             or (ok and p["units_with_text"] == 0)):
        bad = "derivative receipt coverage is inconsistent or empty"
    elif k == "IMAGE_ACCOUNTING" and (ok != all(o["ocr_state"] in ("DONE", "NOT_REQUIRED_DECORATIVE") for o in p["occurrences"])
                                      or any(o["ocr_state"] == "DONE" and not o["ocr_derivative_sha256"] for o in p["occurrences"])):
        bad = "image receipt outcome does not follow from the occurrence states"
    elif k == "MARKING_SCREEN" and ok and p["markings_found"]:
        bad = "marking screen passed although markings were found"
    if bad:
        return [_e("C16_RECEIPT_PAYLOAD", bad, a["gate_id"])]
    try:
        canonical.canonical_bytes(a)
    except canonical.CanonicalError as exc:
        return [_e("C16_RECEIPT_NOT_CANONICAL", str(exc), a["gate_id"])]
    return []


def _index_artefacts(artefacts: dict[str, bytes], inventory_paths: set[str] | None) -> tuple[dict, list[Issue]]:
    out, issues = {}, []
    for path in sorted(artefacts):
        data = artefacts[path]
        m = RECEIPT_PATH.match(path)
        if not m:
            issues.append(_e("C16_RECEIPT_PATH", "receipt artefact outside registers/receipts/<sha256>.json", path))
            continue
        if inventory_paths is not None and path not in inventory_paths:
            issues.append(_e("C16_RECEIPT_NOT_IN_INVENTORY", "receipt artefact not in the ADMISSION_REGISTER component inventory", path))
            continue
        if hashlib.sha256(data).hexdigest() != m["sha"]:
            issues.append(_e("C16_RECEIPT_HASH", "receipt artefact bytes do not hash to its name", path))
            continue
        try:
            obj = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            issues.append(_e("C16_RECEIPT_UNPARSEABLE", "receipt artefact is not UTF-8 JSON", path))
            continue
        ai = artefact_issues(obj)
        if ai:
            issues += [Issue(i.code, i.message, path, i.severity) for i in ai]
            continue
        if artefact_bytes(obj) != data:
            issues.append(_e("C16_RECEIPT_NOT_CANONICAL", "receipt artefact is not in canonical form", path))
            continue
        out[m["sha"]] = obj
    return out, issues


def _chain_heads(arts: dict[str, dict]) -> tuple[set[str], list[Issue]]:
    """Per (generation, copy, gate): one linear revision chain; returns the head hashes."""
    issues, heads = [], set()
    groups: dict[tuple, dict[str, dict]] = {}
    for sha, a in arts.items():
        groups.setdefault((a["corpus_generation_id"], a["subject"]["source_copy_sha256"], a["gate_id"]), {})[sha] = a
    for key, g in groups.items():
        superseded = {}
        for sha, a in g.items():
            s = a["supersedes_receipt_sha256"]
            if s is None:
                continue
            if s == sha or s not in g or g[s]["revision"] != a["revision"] - 1:
                issues.append(_e("C16_RECEIPT_SUPERSESSION", "supersedes an unknown, foreign or own receipt, or skips a revision", sha))
                continue
            superseded[s] = superseded.get(s, 0) + 1
        roots = [s for s, a in g.items() if a["revision"] == 1]
        hd = [s for s in g if s not in superseded]
        if any(n > 1 for n in superseded.values()) or len(roots) != 1 or len(hd) != 1:
            issues.append(_e("C16_RECEIPT_SUPERSESSION", "receipt history is not one linear chain", key[2]))
            continue
        heads.add(hd[0])
    return heads, issues


def resolve_receipts(*, admissions: list[dict], identities: list[dict], anchors: list[dict], relationships: list[dict],
                     artefacts: dict[str, bytes], exchange_contract: str, manifest_register_sha256: str | None,
                     site_register_sha256: str | None, site_facts: dict | None, inventory_paths: set[str] | None = None,
                     ) -> tuple[list[Issue], dict]:
    """Signed-import receipt resolution for every ELIGIBLE effective admission (the 2.0 chain head).

    site_facts: {(source_copy_sha256, receipt_kind): {...recomputed fact...}} from the site's own bytes; for
    SITE_RECOMPUTABLE kinds a missing fact is C16_RECEIPT_UNVERIFIABLE (fail closed).
    Returns (issues, verification): verification maps admission_id -> {gate_id: SITE_VERIFIED|ASSERTED_BOUND}."""
    issues: list[Issue] = []
    arts, idx_issues = _index_artefacts(artefacts, inventory_paths)
    issues += idx_issues
    heads, chain_issues = _chain_heads(arts)
    issues += chain_issues
    ids = {(d["doc_id"], d["source_copy"]["sha256"]): d for d in identities}
    superseded = {a.get("supersedes_admission_id") for a in admissions}
    effective = [a for a in admissions if a["admission_id"] not in superseded]
    verification: dict[str, dict] = {}
    for adm in effective:
        if not adm["application_eligible"]:
            continue
        aid = adm["admission_id"]
        if exchange_contract != CONTRACT_2_1:
            issues.append(_e("C16_RECEIPTS_REQUIRE_2_1", "an eligible admission needs contract 2.1 receipt artefacts; 2.0 exchanges are never importable as eligible", aid))
            continue
        sha, doc = adm["subject"]["source_copy_sha256"], adm["subject"]["doc_id"]
        ident = ids.get((doc, sha))
        if ident is None:
            issues.append(_e("C16_ADMISSION_ORPHAN", "eligible admission has no identity", aid))
            continue
        verification[aid] = {}
        for g in adm["gates"]:
            if g["result"] != "PASS":
                continue
            where = f"{aid}:{g['gate_id']}"
            r = g.get("receipt")
            if not r:
                issues.append(_e("C16_RECEIPT_UNRESOLVED", "PASS gate of an eligible admission has no receipt", where))
                continue
            art = arts.get(r["receipt_sha256"])
            if art is None:
                issues.append(_e("C16_RECEIPT_UNRESOLVED", "receipt artefact missing, unreadable or invalid", where))
                continue
            if r["receipt_sha256"] not in heads:
                issues.append(_e("C16_RECEIPT_SUPERSEDED", "admission references a superseded receipt revision", where))
            mism = [f for f, want, got in (
                ("gate", g["gate_id"], art["gate_id"]), ("kind", r["receipt_kind"], art["receipt_kind"]),
                ("copy", sha, art["subject"]["source_copy_sha256"]), ("doc", doc, art["subject"]["doc_id"]),
                ("generation", adm["corpus_generation_id"], art["corpus_generation_id"]),
                ("derivative", r["derivative_sha256"], art["derivative_sha256"]),
                ("rule", r["rule_id"], art["rule"]["id"]), ("rule_version", r["rule_version"], art["rule"]["version"]),
                ("config", r["config_sha256"], art["config_sha256"]), ("register", r["register_sha256"], art["register_sha256"]),
                ("outcome", g["result"], art["outcome"]), ("receipt_outcome", r["outcome"], art["outcome"])) if want != got]
            if mism:
                issues.append(_e("C16_RECEIPT_FIELD_MISMATCH", "artefact differs from the admission receipt: " + ", ".join(mism), where))
                continue
            if art["receipt_kind"] == "REGISTER_CHECK" and (art["register_sha256"] != manifest_register_sha256
                                                            or art["register_sha256"] != site_register_sha256):
                issues.append(_e("C16_RECEIPT_REGISTER", "register receipt is not for the generation's and the site's register revision", where))
                continue
            pi = _payload_vs_exchange(art, ident, anchors, relationships)
            if pi:
                issues.append(_e("C16_RECEIPT_PAYLOAD", pi, where))
                continue
            if art["verification_class"] == "ASSERTED_BOUND":
                verification[aid][g["gate_id"]] = "ASSERTED_BOUND"
                continue
            fact = (site_facts or {}).get((sha, art["receipt_kind"]))
            if fact is None:
                issues.append(_e("C16_RECEIPT_UNVERIFIABLE", "the site supplied no recomputed fact for a site-recomputable receipt", where))
                continue
            sm = _site_mismatch(art, fact)
            if sm:
                issues.append(_e("C16_RECEIPT_SITE_MISMATCH", sm, where))
                continue
            verification[aid][g["gate_id"]] = "SITE_VERIFIED"
    return issues, verification


def _payload_vs_exchange(art, ident, anchors, relationships) -> str | None:
    p, k = art["payload"], art["receipt_kind"]
    if k == "HASH_REDOWNLOAD" and (p["measured_sha256"] != ident["source_copy"]["sha256"] or p["measured_bytes"] != ident["source_copy"]["bytes"]):
        return "re-download hash or size is not the copy's"
    if k == "FORMAT_DETECTION" and (p["detected_format"] != ident["source_copy"]["detected_format"] or p["mime_type"] != ident["source_copy"]["mime_type"]):
        return "detected format differs from the identity"
    if k == "IDENTITY_VALIDATION" and p["identity_record_sha256"] != canonical.record_sha256(ident):
        return "identity receipt is about another identity record"
    if k == "DERIVATIVE_VERIFICATION":
        der = next((d for d in ident["text_derivatives"] if d["derivative_text_sha256"] == art["derivative_sha256"]), None)
        if der is None or der["coverage"]["units_total"] != p["units_total"] or der["coverage"]["units_with_text"] != p["units_with_text"]:
            return "derivative receipt does not match the identity's derivative and coverage"
    if k == "IMAGE_ACCOUNTING":
        inv = ident["embedded_images"] if isinstance(ident["embedded_images"], list) else None
        want = None if inv is None else [{"image_sequence_id": i["image_sequence_id"], "image_sha256": i["image_sha256"],
                                          "ocr_state": i["ocr_state"], "ocr_derivative_sha256": i.get("ocr_derivative_sha256")} for i in inv]
        if want != p["occurrences"]:
            return "image receipt occurrences differ from the identity's inventory"
    if k == "SCHEMA_VALIDATION" and p["copy_records_sha256"] != copy_records_digest(ident, anchors, relationships):
        return "schema receipt is about other records"
    return None


def _site_mismatch(art, fact) -> str | None:
    p, k = art["payload"], art["receipt_kind"]
    fields = {"HASH_REDOWNLOAD": [("sha256", "measured_sha256"), ("bytes", "measured_bytes")],
              "FORMAT_DETECTION": [("detected_format", "detected_format"), ("magic_hex", "magic_hex")],
              "REGISTER_CHECK": [("matches", "matches")], "IDENTITY_VALIDATION": [("issues", "issues")],
              "DERIVATIVE_VERIFICATION": [("unit_text_sha256", "unit_text_sha256")],
              "IMAGE_ACCOUNTING": [("occurrences", "occurrences")], "SCHEMA_VALIDATION": [("issues", "issues")]}[k]
    checks = [(name, p[field]) for name, field in fields]
    diff = [name for name, claimed in checks if fact.get(name) != claimed]
    return ("site recomputation differs: " + ", ".join(diff)) if diff else None


def recompute_site_facts(*, original: bytes, derivative: bytes | None = None, register_matches: int | None = None,
                         identity_issues: int | None = None, exchange_issues: int | None = None,
                         occurrences: list[dict] | None = None) -> dict:
    """Reference recomputation from the site's own verified bytes (the .NET/Python importer does the same)."""
    from .evidence import split_pages
    magic = original[:8]
    fmt = ("PDF" if magic.startswith(b"%PDF-") else "DOCX" if magic.startswith(b"PK\x03\x04") else
           "PNG" if magic.startswith(b"\x89PNG") else "JPEG" if magic.startswith(b"\xff\xd8\xff") else "UNKNOWN")
    facts = {("HASH_REDOWNLOAD"): {"sha256": hashlib.sha256(original).hexdigest(), "bytes": len(original)},
             ("FORMAT_DETECTION"): {"detected_format": fmt, "magic_hex": original[:5].hex()}}
    if derivative is not None:
        pages = split_pages(derivative.decode("utf-8")) or {}
        facts["DERIVATIVE_VERIFICATION"] = {"unit_text_sha256": [hashlib.sha256(pages[n].encode("utf-8")).hexdigest() for n in sorted(pages)]}
    if register_matches is not None:
        facts["REGISTER_CHECK"] = {"matches": register_matches}
    if identity_issues is not None:
        facts["IDENTITY_VALIDATION"] = {"issues": identity_issues}
    if exchange_issues is not None:
        facts["SCHEMA_VALIDATION"] = {"issues": exchange_issues}
    if occurrences is not None:
        facts["IMAGE_ACCOUNTING"] = {"occurrences": occurrences}
    return facts
