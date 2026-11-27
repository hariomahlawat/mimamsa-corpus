"""Bundle-tree writing, component digests, the integrity and admission registers, and the SG-1 legacy check.

Formats proposed here (Stage 2, flagged as candidate contract 2.1 ADDITIONS; nothing in the frozen 2.0 contract or
the 2.1 interface schemas is changed):
- registers/integrity.jsonl: one canonical row per shipped original copy
      {record_kind: "integrity_entry", sha256, bytes, media_type, page_count, doc_ids[], source}
- registers/admission-accounting.json: per-source admission accounting (plan B05 / I-5), canonical JSON
      {record_kind: "admission_accounting", format, release_id, sources[], reconciled}
  owned by the ADMISSION_REGISTER component, so the frozen manifest schema is unchanged.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from mimamsa_contract.c16 import canonical

from .fsutil import files_under, sha256_bytes, write_bytes

ACCOUNTING_FORMAT = "mimamsa-kbuild-admission-accounting/0 (proposed contract 2.1 addition; not yet in the contract)"
INTEGRITY_FORMAT = "mimamsa-kbuild-integrity-register/0 (proposed contract 2.1 addition; not yet in the contract)"
V1_PAYLOADS = [("data/documents.jsonl", "documents_jsonl", "documents"), ("data/derived_text.jsonl", "derived_text_jsonl", "derived_text"),
               ("data/candidates.jsonl", "candidates_jsonl", "candidates"), ("data/reviewed_records.jsonl", "reviewed_records_jsonl", "reviewed_records"),
               ("data/appointments.jsonl", "appointments_jsonl", "appointments"), ("data/approvals.jsonl", "approvals_jsonl", "approvals"),
               ("data/publication_records.jsonl", "publication_records_jsonl", "publication_records")]
SUMS, SIG = "SHA256SUMS", "SHA256SUMS.sig"


def v1_jsonl(records) -> bytes:
    """The v1 writer's serialisation (devbundle._jsonl): sorted keys, UTF-8, LF. Deterministic."""
    return "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in records).encode("utf-8")


def parse_jsonl(data: bytes) -> list[dict]:
    return [json.loads(x) for x in data.decode("utf-8").split("\n") if x.strip()]


# ------------------------------------------------------------------ SG-1 (I-5) and admissions

def effective_admissions(adms: list[dict]) -> list[dict]:
    superseded = {a.get("supersedes_admission_id") for a in adms}
    return [a for a in adms if a["admission_id"] not in superseded]


def legacy_issues(v1_docs: list[dict], identities: list[dict], admissions: list[dict], hf_pins: set[tuple[str, str]],
                  v7_shas: set[str] | None = None) -> list[dict]:
    """SG-1: a copy is served on the v1 path only if independently established. Any C16 identity or admission for the
    same bytes governs it (no eligible effective admission = refused, sidecar or not); v7 candidates and unadmitted
    originals are never relabelled v1; a v1 record without pinned provenance is not established."""
    out = []
    eff = effective_admissions(admissions)
    eligible_shas = {a["subject"]["source_copy_sha256"] for a in eff if a.get("application_eligible") is True}
    c16_shas = {i["source_copy"]["sha256"] for i in identities} | {a["subject"]["source_copy_sha256"] for a in admissions}
    for d in v1_docs:
        h, did = d["source_copy"]["sha256"], d["doc_id"]
        if h in c16_shas and h not in eligible_shas:
            out.append({"code": "C16_LEGACY_NOT_ESTABLISHED", "doc_id": did,
                        "reason": "v1 record names a copy governed by C16 without an eligible effective admission"})
        if v7_shas and h in v7_shas:
            out.append({"code": "C16_LEGACY_NOT_ESTABLISHED", "doc_id": did, "reason": "v7 candidate original relabelled as a v1 document"})
        prov = d.get("provenance") or {}
        hf = prov.get("hf") or {}
        if (hf.get("repo"), hf.get("revision")) not in hf_pins and not prov.get("acquisition_record_ref"):
            out.append({"code": "C16_LEGACY_NOT_ESTABLISHED", "doc_id": did,
                        "reason": "v1 record without provenance pinned to a build input (HF revision or acquisition record)"})
    return out


def v1_servable_reason(d: dict) -> str | None:
    pub = (((d.get("status_axes") or {}).get("publication") or {}).get("value"))
    elig = (d.get("restriction") or {}).get("eligibility")
    if pub != "PUBLISHED":
        return f"PUBLICATION_{pub or 'UNKNOWN'}"
    if elig != "ELIGIBLE_ALL_USERS":
        return f"RESTRICTION_{elig or 'UNKNOWN'}"
    return None


def admission_accounting(*, release_id: str, v1_source: dict, v1_docs: list[dict], generations: list[dict],
                         shipped_original_shas: set[str]) -> dict:
    """generations: [{corpus_generation_id, generation_manifest_sha256, hf_repo, hf_revision, identities, admissions,
    receipts_unresolved}]. A C16 copy is declared servable only with an eligible effective admission whose receipts
    resolve and whose original ships in this release; the site importer re-decides (and may only narrow) this."""
    sources = []
    not_serv = Counter()
    served = 0
    for d in v1_docs:
        why = v1_servable_reason(d)
        if why is None and d["source_copy"]["sha256"] not in shipped_original_shas:
            why = "ORIGINAL_NOT_IN_RELEASE"
        if why:
            not_serv[why] += 1
        else:
            served += 1
    sources.append({"source": "v1_canonical", "path": "v1", **v1_source, "documents": len(v1_docs), "declared_servable": served,
                    "not_servable": dict(sorted(not_serv.items())), "reconciled": served + sum(not_serv.values()) == len(v1_docs)})
    for g in generations:
        eff = effective_admissions(g["admissions"])
        by_decision = Counter(a["decision"] for a in eff)
        nots = Counter()
        served = 0
        eff_by_key = {(a["subject"]["doc_id"], a["subject"]["source_copy_sha256"]): a for a in eff}
        for i in g["identities"]:
            a = eff_by_key.get((i["doc_id"], i["source_copy"]["sha256"]))
            if a is None:
                nots["NO_EFFECTIVE_ADMISSION"] += 1
            elif a.get("application_eligible") is not True:
                nots[a["decision"]] += 1
            elif a["admission_id"] in g.get("receipts_unresolved", ()):
                nots["ELIGIBLE_RECEIPTS_UNRESOLVED"] += 1
            elif i["source_copy"]["sha256"] not in shipped_original_shas:
                nots["ELIGIBLE_ORIGINAL_NOT_IN_RELEASE"] += 1
            else:
                served += 1
        n = len(g["identities"])
        sources.append({"source": "c16_producer_generation", "path": "c16", "corpus_generation_id": g["corpus_generation_id"],
                        "generation_manifest_sha256": g["generation_manifest_sha256"], "hf_repo": g["hf_repo"], "hf_revision": g["hf_revision"],
                        "identities": n, "admissions": len(g["admissions"]), "effective_admissions": len(eff),
                        "effective_by_decision": dict(sorted(by_decision.items())),
                        "eligible": sum(1 for a in eff if a.get("application_eligible") is True),
                        "declared_servable": served, "not_servable": dict(sorted(nots.items())),
                        "reconciled": served + sum(nots.values()) == n})
    sources.append({"source": "v7_candidates", "path": "v7", "status": "REFERENCE_ONLY_NEVER_SERVED", "documents": 0, "declared_servable": 0,
                    "not_servable": {}, "reconciled": True, "note": "not an input of this build"})
    sources.append({"source": "local_admin_uploads", "path": "site", "status": "SITE_ONLY_NEVER_IN_A_RELEASE", "documents": 0,
                    "declared_servable": 0, "not_servable": {}, "reconciled": True})
    return {"record_kind": "admission_accounting", "format": ACCOUNTING_FORMAT, "release_id": release_id, "sources": sources,
            "reconciled": all(s["reconciled"] for s in sources)}


def integrity_rows(v1_docs: list[dict], originals: dict[str, bytes], source: str) -> bytes:
    by_sha: dict[str, list[str]] = {}
    for d in v1_docs:
        by_sha.setdefault(d["source_copy"]["sha256"], []).append(d["doc_id"])
    rows = []
    for d in sorted(v1_docs, key=lambda x: x["source_copy"]["sha256"]):
        h = d["source_copy"]["sha256"]
        if h not in originals or any(r["sha256"] == h for r in rows):
            continue
        rows.append({"record_kind": "integrity_entry", "format": INTEGRITY_FORMAT, "sha256": h, "bytes": len(originals[h]),
                     "media_type": d["source_copy"]["mime_type"], "page_count": d["source_copy"]["page_count"],
                     "doc_ids": sorted(by_sha[h]), "source": source, "verified_sha256": sha256_bytes(originals[h]) == h})
    return b"".join(canonical.canonical_bytes(r) + b"\n" for r in rows)


# ------------------------------------------------------------------ bundle tree

def write_release_tree(root: Path, *, release_manifest_template: dict, spec: dict, defaults: dict, register, key_id: str,
                       v1_source: dict, records: dict[str, list[dict]], originals: dict[str, bytes], texts: dict[str, bytes],
                       research: dict[str, bytes], c16_files: dict[str, bytes]) -> dict:
    """Write the unsigned bundle tree (no SHA256SUMS). Returns the v1 RELEASE.json written.
    originals: {sha256: bytes}; texts: {text_path: bytes}; research: {research/...: bytes};
    c16_files: {corpus-v2/... or registers/...: bytes} (verbatim)."""
    files = []
    payloads: dict[str, tuple[bytes, str | None]] = {}
    for path, kind, key in V1_PAYLOADS:
        payloads[path] = (v1_jsonl(records.get(key, [])), kind)
    changes = {"added": sorted(d["doc_id"] for d in records.get("documents", [])), "updated": [], "newly_superseded": [],
               "withdrawn": [], "status_changed": []}
    payloads["CHANGES.json"] = (json.dumps(changes, indent=1).encode(), "changes")
    for h in sorted(originals):
        payloads[f"originals/{h}.pdf"] = (originals[h], "original")
    for p in sorted(texts):
        payloads[p] = (texts[p], "text")
    for p in sorted(research):
        payloads[p] = (research[p], "report")
    for rel, (data, kind) in payloads.items():
        write_bytes(root / rel, data)
        files.append({"path": rel, "sha256": sha256_bytes(data), "bytes": len(data), "kind": kind})
    for rel in sorted(c16_files):
        write_bytes(root / rel, c16_files[rel])
    m = json.loads(json.dumps(release_manifest_template))
    m.update(release_id=spec["release"]["release_id"], release_sequence=spec["release"]["release_sequence"],
             created_at=spec["pinned_build_time"], auth_ledger_version=defaults["auth_ledger_version"], auth_ledger_head=None)
    m["pinned"].update(hf_repo=v1_source["hf_repo"], hf_revision=v1_source["hf_revision"], tools_commit=spec["inputs"]["git"][0]["commit"])
    m["compatibility"].update(min_app_version=defaults["min_app_version"], max_app_version=defaults["max_app_version"], previous_release_id=None, delta=False)
    m["restricted_material"].update(config_path="config/restricted_material.json", config_sha256=register.config_sha256,
                                    restriction_ids_applied=sorted(register.restriction_ids))
    m["signature"] = dict(m["signature"], key_id=key_id)
    m["candidate_banner"] = {"required": True, "text": defaults["candidate_banner"]}
    m["files"] = sorted(files, key=lambda f: f["path"])
    write_bytes(root / "RELEASE.json", json.dumps(m, indent=1, sort_keys=True).encode())
    return m


def sums_bytes(root: Path) -> bytes:
    lines = []
    for p in files_under(root):
        rel = p.relative_to(root).as_posix()
        if rel in (SUMS, SIG):
            continue
        lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {rel}\n")
    return "".join(lines).encode("utf-8")


# ------------------------------------------------------------------ component digests (architecture section 5)

def hashset_digest(hashes) -> str:
    return sha256_bytes("\n".join(sorted(hashes)).encode("ascii"))


def concat_digest(root: Path, paths: list[str]) -> str:
    h = hashlib.sha256()
    for p in sorted(paths, key=lambda x: x.encode("utf-8")):
        h.update((root / p).read_bytes())
    return h.hexdigest()


def rows_component_digest(tables: list[dict]) -> str:
    """sha256 over `table|row_count|rows_sha256`, tables in name order, LF-joined (joining convention proposed here)."""
    lines = [f"{t['table']}|{t['row_count']}|{t['rows_sha256']}" for t in sorted(tables, key=lambda t: t["table"])]
    return sha256_bytes("\n".join(lines).encode("utf-8"))


def file_entries(root: Path, prefix: str) -> list[dict]:
    base = root / prefix
    out = []
    for p in files_under(base) if base.is_dir() else ([base] if base.is_file() else []):
        rel = p.relative_to(root).as_posix()
        out.append({"path": rel, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "bytes": p.stat().st_size})
    return out
