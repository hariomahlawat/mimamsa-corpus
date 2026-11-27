"""Per-source admission accounting register (I-5; contract 2.1): reconciliation and declared-vs-site comparison.

One format for the central build (B02, writes DECLARED_BY_BUILD) and the site importer (B01, writes
RECOMPUTED_BY_SITE): SOURCE_ADMISSION_ACCOUNTING_SCHEMA.json, file registers/source_accounting.json.
"""
from __future__ import annotations

from ..issues import Issue
from . import canonical
from .schemas import schema_errors

FILE = "registers/source_accounting.json"


def _e(code, msg, where=""):
    return Issue(code, msg, where)


def register_bytes(reg: dict) -> bytes:
    return canonical.canonical_bytes(reg) + b"\n"


def accounting_issues(reg) -> list[Issue]:
    """Schema plus reconciliation:
    R1 identities == input; R2 held + rejected + quarantined + eligible == input; R3 served <= eligible and
    served + sum(not_served_reasons) == input; R4 C16: sum(by_decision) == effective_admissions == identities;
    R5 V7_REFERENCE never eligible or served (schema); R6 sources unique and sorted; R7 no SITE_ONLY source in a
    declared (bundle) register (schema)."""
    issues = [_e("SCHEMA", m, "source_admission_accounting") for m in schema_errors(reg)]
    if issues:
        return issues
    ids = [s["source"] for s in reg["sources"]]
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        issues.append(_e("C16_SOURCE_ACCOUNTING", "sources must be unique and sorted by source id"))
    for s in reg["sources"]:
        w = s["source"]
        if s["identities"] != s["input"]:
            issues.append(_e("C16_SOURCE_ACCOUNTING", "identities differ from input (R1)", w))
        if s["held"] + s["rejected"] + s["quarantined"] + s["eligible"] != s["input"]:
            issues.append(_e("C16_SOURCE_ACCOUNTING", "held + rejected + quarantined + eligible differ from input (R2)", w))
        if s["served"] > s["eligible"] or s["served"] + sum(s["not_served_reasons"].values()) != s["input"]:
            issues.append(_e("C16_SOURCE_ACCOUNTING", "served and not-served reasons do not reconcile with input (R3)", w))
        if s["path"] == "C16" and not (sum(s["by_decision"].values()) == s["effective_admissions"] == s["identities"]):
            issues.append(_e("C16_SOURCE_ACCOUNTING", "C16 decisions do not reconcile with effective admissions and identities (R4)", w))
    return issues


def compare_declared(declared: dict, recomputed: dict) -> list[Issue]:
    """The site's recomputation against the signed declaration: the same sources; input, identities, held, rejected,
    effective admissions and decisions equal; eligible and served may only be lower at the site (narrowing);
    quarantined may only be higher."""
    issues = []
    if declared.get("scope") != "DECLARED_BY_BUILD" or recomputed.get("scope") != "RECOMPUTED_BY_SITE":
        issues.append(_e("C16_SOURCE_ACCOUNTING", "declared and recomputed registers have the wrong scopes"))
    if declared["release_id"] != recomputed["release_id"]:
        issues.append(_e("C16_SOURCE_ACCOUNTING", "registers are for different releases"))
    d = {s["source"]: s for s in declared["sources"]}
    r = {s["source"]: s for s in recomputed["sources"] if s["path"] != "SITE_ONLY"}
    if set(d) != set(r):
        issues.append(_e("C16_SOURCE_ACCOUNTING", "the site sees different sources than the build declared"))
    for k in sorted(set(d) & set(r)):
        a, b = d[k], r[k]
        for f in ("input", "identities", "held", "rejected", "effective_admissions", "by_decision"):
            if a[f] != b[f]:
                issues.append(_e("C16_SOURCE_ACCOUNTING", f"site {f} differs from the declaration", k))
        if b["eligible"] > a["eligible"] or b["served"] > a["served"]:
            issues.append(_e("C16_SOURCE_ACCOUNTING", "the site may only narrow eligibility and service", k))
        if b["quarantined"] < a["quarantined"]:
            issues.append(_e("C16_SOURCE_ACCOUNTING", "the site may not un-quarantine what the build declared quarantined", k))
    return issues
