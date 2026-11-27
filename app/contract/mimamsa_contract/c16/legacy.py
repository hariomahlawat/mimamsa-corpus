"""I-5 legacy (v1-path) establishment and per-source admission accounting (contract 2.1 interface, B01).

v1 compatibility covers only copies INDEPENDENTLY established as v1-eligible. A missing or removed C16 sidecar never
bypasses a hold, withdrawal, provenance gap or admission; v7 candidates and other unadmitted originals can never be
relabelled v1 to be served.
"""
from __future__ import annotations

from ..issues import Issue


def _e(code, msg, where=""):
    return Issue(code, msg, where)


def legacy_issues(doc: dict, *, c16_governed: set[tuple[str, str]], eligible_c16: set[tuple[str, str]],
                  candidate_shas: set[str], excluded: set[str]) -> list[Issue]:
    """doc: a v1 document record without a C16 sidecar in this bundle.
    c16_governed: every (doc_id, sha256) that ANY current or retained generation holds a C16 identity or admission for.
    eligible_c16: (doc_id, sha256) whose effective C16 admission is eligible.
    candidate_shas: hashes appearing in candidate packages (v7 and others) or C16 exchanges.
    excluded: doc_ids and hashes withdrawn or restricted by the monotone exclusion channel."""
    key = (doc["doc_id"], doc["source_copy"]["sha256"])
    out = []
    if key in c16_governed and key not in eligible_c16:
        out.append(_e("C16_LEGACY_NOT_ESTABLISHED", "copy is governed by C16 rules; dropping its sidecar does not revert it to v1", key[0]))
    if key[1] in candidate_shas and key not in eligible_c16:
        out.append(_e("C16_LEGACY_NOT_ESTABLISHED", "a candidate or unadmitted original cannot be relabelled as a v1 document", key[0]))
    if key[0] in excluded or key[1] in excluded:
        out.append(_e("C16_LEGACY_NOT_ESTABLISHED", "withdrawn or restricted by the exclusion channel", key[0]))
    prov = doc.get("provenance") or {}
    if not (prov.get("hf") or {}).get("revision") and not prov.get("acquisition_record_ref"):
        out.append(_e("C16_LEGACY_NOT_ESTABLISHED", "v1 provenance incomplete (no pinned HF revision or acquisition record)", key[0]))
    if (doc.get("status_axes", {}).get("publication", {}).get("value") != "PUBLISHED"
            or doc.get("restriction", {}).get("eligibility") != "ELIGIBLE_ALL_USERS"):
        out.append(_e("C16_LEGACY_NOT_ESTABLISHED", "not v1-eligible (publication or restriction)", key[0]))
    return out


def accounting_issues(sources: list[dict]) -> list[Issue]:
    """Per-source accounting: input count = held + rejected + quarantined + eligible; served <= eligible.
    sources: [{source, input, identities, held, rejected, quarantined, eligible, served}]."""
    out = []
    for s in sources:
        if s["identities"] != s["input"] or s["held"] + s["rejected"] + s["quarantined"] + s["eligible"] != s["input"] \
                or s["served"] > s["eligible"]:
            out.append(_e("C16_SOURCE_ACCOUNTING", "per-source admission counts do not reconcile", s["source"]))
        if s["source"].startswith("v7") and s["served"]:
            out.append(_e("C16_SOURCE_ACCOUNTING", "v7 candidates are reference only and are never served", s["source"]))
    return out
