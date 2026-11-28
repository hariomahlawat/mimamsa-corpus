"""B04 component verification (contract 2.1 interface): contract rules and the activation-outcome decision.

The decision below is the reference for the site: authoritative failure refuses; a failed cheap accelerator is served
only after a local rebuild that is independently verified with recorded evidence (ACTIVE_AFTER_LOCAL_REBUILD), else
the release does not serve (REBUILD_REQUIRED); missing or failed vectors give lexical-only service (ACTIVE_DEGRADED,
Admin acknowledgement) and NEVER site embedding; in production, no component in use may rely on an UNCALIBRATED
sampled check at any service level (fail closed; review C16-I21-01/02). A fixture slice (CP-1) is explicitly degraded.
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


ACCELERATOR_KINDS = ("GRAPH", "KNOWLEDGE_ROWS", "LEXICAL_INDEX", "TEXT_STORE", "VECTOR_PACK")
STATES = ("VERIFIED", "FAILED", "MISSING")
MODES = ("production", "development")
# Owner gate (recorded, OPEN): may PRODUCTION serve lexical-only on accelerators verified with UNCALIBRATED sampled
# checks? Until the owner decides (and FG-CALIBRATED-SAMPLES supplies calibrated values), the answer is NO: production
# refuses any in-use component whose contract still has an UNCALIBRATED sample, at EVERY service level.
OWNER_GATE_UNCALIBRATED_PRODUCTION = "OD-C16-UNCALIBRATED-PRODUCTION"
_HEX64 = frozenset("0123456789abcdef")


def _sha_ok(v) -> bool:
    return isinstance(v, str) and len(v) == 64 and set(v) <= _HEX64


def rebuild_issues(kind: str, rec) -> list[str]:
    """Evidence that a cheap accelerator was rebuilt locally AND independently verified. Required shape:
    {status: VERIFIED, builder: {name, version, commit} (non-empty strings), source_digest, result_digest (64-hex),
     checks: {check_id: PASS | FAIL}} with every required check of the kind present and PASS and none FAIL.
    Anything else (absent record, status FAILED, missing provenance or checks) is not a successful rebuild."""
    if kind not in CHEAP:
        return ["only cheap accelerators are rebuilt on site (vectors never: site_embedding NEVER)"]
    if not isinstance(rec, dict):
        return ["no rebuild evidence"]
    out = []
    if rec.get("status") != "VERIFIED":
        out.append("rebuild not verified")
    b = rec.get("builder")
    if not (isinstance(b, dict) and all(isinstance(b.get(k), str) and b.get(k) for k in ("name", "version", "commit"))):
        out.append("rebuild provenance (builder name, version, commit) incomplete")
    if not (_sha_ok(rec.get("source_digest")) and _sha_ok(rec.get("result_digest"))):
        out.append("rebuild source_digest/result_digest missing or malformed")
    checks = rec.get("checks")
    if not isinstance(checks, dict) or any(v not in ("PASS", "FAIL") for v in checks.values()):
        out.append("rebuild check results missing or malformed")
    else:
        if REQUIRED_CHECKS[kind] - {k for k, v in checks.items() if v == "PASS"}:
            out.append("a required check did not pass on the rebuilt component")
        if any(v == "FAIL" for v in checks.values()):
            out.append("a check failed on the rebuilt component")
    return out


def activation_outcome(results: dict, contracts: dict, *, mode: str, rebuilds: dict | None = None) -> dict:
    """Activation decision over the five accelerator kinds (authoritative components were verified before this point
    or the release refused). Contract 2.1 (review C16-I21-01/02):
    - Inputs are explicit and complete: mode in MODES; results maps kinds to VERIFIED | FAILED | MISSING, an omitted
      kind is MISSING, an unknown kind or state refuses (INVALID_INPUT).
    - Every component IN USE (verified, or rebuilt and verified) needs a validated contract of its kind
      (contract_issues == []), else refused (CONTRACT_INVALID).
    - A FAILED or MISSING cheap accelerator is in use only with rebuild evidence passing rebuild_issues; otherwise the
      release does not serve (REFUSED, refusal REBUILD_REQUIRED). All four cheap kinds are essential.
    - Vectors that are not VERIFIED give DEGRADED_LEXICAL_ONLY (never site embedding).
    - Calibration is gated on the COMPONENTS IN USE, at every service level and whatever the result label: in
      production any in-use contract with an UNCALIBRATED sample refuses (UNCALIBRATED_IN_PRODUCTION), including after
      a rebuild and for lexical-only service (owner gate OD-C16-UNCALIBRATED-PRODUCTION, OPEN, fails closed).
    Returns {result, service_level, site_embedding, refusal, reasons, components, uncalibrated_in_use}."""
    rebuilds = rebuilds or {}

    def refuse(code, why, comps=None, uncal=None):
        return {"result": "REFUSED", "service_level": "NOT_SERVING", "site_embedding": "NEVER", "refusal": code,
                "reasons": why, "components": comps or {}, "uncalibrated_in_use": uncal or []}
    if mode not in MODES:
        return refuse("INVALID_INPUT", ["unknown mode"])
    if not isinstance(results, dict) or set(results) - set(ACCELERATOR_KINDS):
        return refuse("INVALID_INPUT", ["unknown component kind in results"])
    if set(rebuilds) - set(CHEAP):
        return refuse("INVALID_INPUT", ["rebuild evidence for a kind that is never rebuilt on site"])
    states = {k: results.get(k, "MISSING") for k in ACCELERATOR_KINDS}
    if any(v not in STATES for v in states.values()):
        return refuse("INVALID_INPUT", ["unknown component state"])
    comps, reasons, missing_rebuild = {}, [], []
    for k in ACCELERATOR_KINDS:
        if states[k] == "VERIFIED":
            comps[k] = {"state": "VERIFIED"}
        elif k in CHEAP:
            why = rebuild_issues(k, rebuilds.get(k))
            if why:
                comps[k] = {"state": "REBUILD_REQUIRED", "input_state": states[k], "why": why}
                missing_rebuild.append(k)
            else:
                r = rebuilds[k]
                comps[k] = {"state": "REBUILT_VERIFIED", "input_state": states[k], "builder": r["builder"],
                            "source_digest": r["source_digest"], "result_digest": r["result_digest"], "checks": r["checks"]}
        else:
            comps[k] = {"state": "NOT_USED", "input_state": states[k]}
    in_use = sorted(k for k, c in comps.items() if c["state"] in ("VERIFIED", "REBUILT_VERIFIED"))
    bad = sorted(k for k in in_use if not isinstance(contracts.get(k), dict) or contracts[k].get("kind") != k
                 or contract_issues(contracts[k]))
    if bad:
        return refuse("CONTRACT_INVALID", ["missing or invalid verification contract: " + ", ".join(bad)], comps)
    if missing_rebuild:
        return refuse("REBUILD_REQUIRED", ["cheap accelerator failed or missing and not rebuilt and verified: " + ", ".join(missing_rebuild)], comps)
    level = "FULL" if comps["VECTOR_PACK"]["state"] == "VERIFIED" else "DEGRADED_LEXICAL_ONLY"
    if level != "FULL":
        reasons.append("vectors missing or failed: lexical-only service, no site embedding")
    rebuilt = sorted(k for k, c in comps.items() if c["state"] == "REBUILT_VERIFIED")
    if rebuilt:
        reasons.append("rebuilt locally and verified: " + ", ".join(rebuilt))
    uncal = sorted(k for k in in_use if uncalibrated(contracts[k]))
    if uncal and mode == "production":
        return refuse("UNCALIBRATED_IN_PRODUCTION", reasons + [f"uncalibrated sampled checks in use in production ({OWNER_GATE_UNCALIBRATED_PRODUCTION} open): " + ", ".join(uncal)], comps, uncal)
    if uncal:
        reasons.append("uncalibrated sampled checks (development only): " + ", ".join(uncal))
    result = "ACTIVE_DEGRADED" if level != "FULL" else ("ACTIVE_AFTER_LOCAL_REBUILD" if rebuilt else "ACTIVE_FULL")
    return {"result": result, "service_level": level, "site_embedding": "NEVER", "refusal": None, "reasons": reasons,
            "components": comps, "uncalibrated_in_use": uncal}


def manifest_verify_ids() -> set[str]:
    return set(schema("KNOWLEDGE_RELEASE_MANIFEST_SCHEMA.json")["$defs"]["component"]["properties"]["verify"]["items"]["enum"])
