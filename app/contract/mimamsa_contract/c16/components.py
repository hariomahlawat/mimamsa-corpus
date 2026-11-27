"""B04 component verification (contract 2.1 interface): contract rules and the activation-outcome decision.

The decision below is the reference for the site: authoritative failure refuses; a failed cheap accelerator is
rebuilt locally (ACTIVE_AFTER_LOCAL_REBUILD); missing or failed vectors give lexical-only service (ACTIVE_DEGRADED,
Admin acknowledgement) and NEVER site embedding; a sampled check that is still UNCALIBRATED can never yield
ACTIVE_FULL in production mode (fail closed). A fixture vertical slice (CP-1) is explicitly degraded.
"""
from __future__ import annotations

from ..issues import Issue
from .schemas import schema, schema_errors

CHEAP = {"KNOWLEDGE_ROWS", "GRAPH", "LEXICAL_INDEX", "TEXT_STORE"}
REQUIRED_CHECKS = {   # the manifest schema's per-kind verify sets (KNOWLEDGE_RELEASE_MANIFEST_SCHEMA)
    "KNOWLEDGE_ROWS": {"ROW_COUNTS", "ROWS_ALLOWLIST_AND_TYPES", "ROWS_REDERIVE_COMPARE"},
    "GRAPH": {"GRAPH_DIGEST", "GRAPH_STRUCTURAL_RECHECK", "SAMPLED_REBUILD_PARITY"},
    "LEXICAL_INDEX": {"SQLITE_QUICK_CHECK", "SAMPLED_POSTINGS_REDERIVE", "SAMPLED_QUERY_PARITY"},
    "TEXT_STORE": {"SQLITE_QUICK_CHECK", "TEXT_STORE_BIND_EXACT", "PAGE_HASH_ON_READ"},
    "VECTOR_PACK": {"VECTOR_TRAILER", "VECTOR_KEYS_RECOMPUTED", "VECTOR_SPOT_REEMBED"},
}
SAMPLED = {"SAMPLED_REBUILD_PARITY", "SAMPLED_POSTINGS_REDERIVE", "SAMPLED_QUERY_PARITY", "VECTOR_SPOT_REEMBED"}


def _e(code, msg, where=""):
    return Issue(code, msg, where)


def contract_issues(c) -> list[Issue]:
    issues = [_e("SCHEMA", m, "component_verification_contract") for m in schema_errors(c)]
    if issues:
        return issues
    ids = {x["check_id"] for x in c["checks"]}
    for missing in sorted(REQUIRED_CHECKS[c["kind"]] - ids):
        issues.append(_e("KR_VERIFY_CONTRACT", f"required check {missing} missing", c["kind"]))
    for x in c["checks"]:
        if x["check_id"] in SAMPLED and x["sample"]["selection"] == "FULL":
            issues.append(_e("KR_VERIFY_CONTRACT", "a sampled check must use a deterministic seeded sample", x["check_id"]))
        if x["check_id"] not in SAMPLED and x["sample"]["selection"] != "FULL":
            issues.append(_e("KR_VERIFY_CONTRACT", "an exhaustive check must run on the full component", x["check_id"]))
    return issues


def uncalibrated(c: dict) -> bool:
    return any(x["sample"]["size"] == "UNCALIBRATED" or x["sample"]["tolerance"] == "UNCALIBRATED" for x in c["checks"])


def activation_outcome(results: dict[str, str], contracts: dict[str, dict], *, mode: str) -> dict:
    """results: {component kind: VERIFIED | FAILED | MISSING} for the accelerators (authoritative components have
    already been verified or the release refused). Returns {result, service_level, site_embedding, reasons}."""
    reasons, result, level = [], "ACTIVE_FULL", "FULL"
    if results.get("VECTOR_PACK", "MISSING") != "VERIFIED":
        result, level = "ACTIVE_DEGRADED", "DEGRADED_LEXICAL_ONLY"
        reasons.append("vectors missing or failed: lexical-only service, no site embedding")
    rebuilt = sorted(k for k in CHEAP if results.get(k) in ("FAILED", "MISSING"))
    if rebuilt and result == "ACTIVE_FULL":
        result = "ACTIVE_AFTER_LOCAL_REBUILD"
    if rebuilt:
        reasons.append("rebuilt locally: " + ", ".join(rebuilt))
    used_uncal = sorted(k for k, v in results.items() if v == "VERIFIED" and k in contracts and uncalibrated(contracts[k]))
    if used_uncal and mode == "production" and result == "ACTIVE_FULL":
        result, level = "REFUSED", "NOT_SERVING"
        reasons.append("uncalibrated sampled checks cannot support ACTIVE_FULL in production: " + ", ".join(used_uncal))
    elif used_uncal:
        reasons.append("uncalibrated sampled checks (development only): " + ", ".join(used_uncal))
    return {"result": result, "service_level": level, "site_embedding": "NEVER", "reasons": reasons}


def manifest_verify_ids() -> set[str]:
    return set(schema("KNOWLEDGE_RELEASE_MANIFEST_SCHEMA.json")["$defs"]["component"]["properties"]["verify"]["items"]["enum"])
