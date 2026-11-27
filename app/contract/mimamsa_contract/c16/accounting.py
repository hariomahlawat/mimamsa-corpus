"""Per-source admission accounting register (I-5; contract 2.1): reconciliation and declared-vs-site comparison.

One format for the central build (B02, writes DECLARED_BY_BUILD) and the site importer (B01, writes
RECOMPUTED_BY_SITE): SOURCE_ADMISSION_ACCOUNTING_SCHEMA.json, file registers/source_accounting.json.
"""
from __future__ import annotations

import hashlib

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


CANDIDATE_SET_PREFIX = "registers/candidate_sets/"
_HEX = frozenset("0123456789abcdef")


def candidate_set_path(source: str) -> str:
    """`v7:<name>` -> `registers/candidate_sets/<name>.txt` (name as in the source id pattern)."""
    return f"{CANDIDATE_SET_PREFIX}{source.split(':', 1)[1]}.txt"


def candidate_set_bytes(hashes) -> bytes:
    """The exact file bytes and the exact preimage of `provenance.candidate_set_sha256`: the unique lower-case
    sha256 hex strings, sorted, joined by LF, NO final LF, ASCII. An empty set is the empty file. Equal to
    digests.hashset_digest's preimage."""
    return "\n".join(sorted(set(hashes))).encode("ascii")


def candidate_set_issues(declared: dict, files: dict[str, bytes], admission_inventory: set[str]) -> tuple[set[str], list[Issue]]:
    """v7 candidate-set files (2.1, CP-1 gap 1). For each V7_REFERENCE source of the DECLARED register:
    CS1 the file candidate_set_path(source) exists and is listed in the ADMISSION_REGISTER inventory;
    CS2 sha256(file bytes) == provenance.candidate_set_sha256;
    CS3 the bytes are canonical: candidate_set_bytes(parsed) == bytes (lower-case 64-hex, sorted, unique, LF, no
        final LF, no CR, no BOM, no blank line);
    CS4 the number of hashes == the source's input.
    CS5 every file under registers/candidate_sets/ belongs to a declared V7_REFERENCE source (no orphans) and is in
        the ADMISSION_REGISTER inventory.
    Any issue refuses the bundle (fail closed). Returns the union of candidate hashes for the I-5 relabel check
    (legacy_issues candidate_shas) only when there is no issue."""
    issues, shas = [], set()
    v7 = {candidate_set_path(s["source"]): s for s in declared["sources"] if s["path"] == "V7_REFERENCE"}
    for p in sorted(x for x in set(files) | admission_inventory if x.startswith(CANDIDATE_SET_PREFIX)):
        if p not in v7:
            issues.append(_e("C16_SOURCE_ACCOUNTING", "candidate-set file without a declared V7_REFERENCE source (CS5)", p))
        elif p not in admission_inventory:
            issues.append(_e("C16_SOURCE_ACCOUNTING", "candidate-set file is not in the ADMISSION_REGISTER inventory (CS1)", p))
    for p, s in sorted(v7.items()):
        b = files.get(p)
        if b is None:
            issues.append(_e("C16_SOURCE_ACCOUNTING", "v7 candidate-set file missing (CS1)", p))
            continue
        if hashlib.sha256(b).hexdigest() != (s["provenance"] or {}).get("candidate_set_sha256"):
            issues.append(_e("C16_SOURCE_ACCOUNTING", "candidate-set bytes do not hash to provenance.candidate_set_sha256 (CS2)", p))
            continue
        try:
            hs = b.decode("ascii").split("\n") if b else []
        except UnicodeDecodeError:
            hs = None
        if hs is None or not all(len(h) == 64 and set(h) <= _HEX for h in hs) or candidate_set_bytes(hs) != b:
            issues.append(_e("C16_SOURCE_ACCOUNTING", "candidate-set file is not canonical (CS3)", p))
            continue
        if len(hs) != s["input"]:
            issues.append(_e("C16_SOURCE_ACCOUNTING", "candidate-set size differs from the source's input (CS4)", p))
            continue
        shas |= set(hs)
    return (set() if issues else shas), issues


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
