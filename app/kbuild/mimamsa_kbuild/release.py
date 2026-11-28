"""Bundle-tree writing, component digests, the integrity and admission registers, and the SG-1 legacy check.

- registers/source_accounting.json: the per-source admission accounting register of contract 2.1 (PR #82
  clarification 1; SOURCE_ADMISSION_ACCOUNTING_SCHEMA.json, reference mimamsa_contract.c16.accounting), scope
  DECLARED_BY_BUILD, canonical JSON plus a final LF, owned by the ADMISSION_REGISTER component.
- Component digests are the 2.1 byte-exact definitions in mimamsa_contract.c16.digests (PR #82 clarification 2).
Format still proposed here (Stage 2, flagged as a candidate contract 2.1 ADDITION; nothing in the frozen 2.0 contract
or the 2.1 interface schemas is changed):
- registers/integrity.jsonl: one canonical row per shipped original copy
      {record_kind: "integrity_entry", sha256, bytes, media_type, page_count, doc_ids[], source}
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from mimamsa_contract.c16 import canonical, digests

from .fsutil import files_under, link_or_copy, sha256_bytes, sha256_file, write_bytes

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
        return f"PUBLICATION_{pub or 'UNKNOWN'}".upper().replace("-", "_")
    if elig != "ELIGIBLE_ALL_USERS":
        return f"RESTRICTION_{elig or 'UNKNOWN'}".upper().replace("-", "_")
    return None


def _v1_source_id(d: dict) -> str:
    """Source id the site importer uses for a v1 document (B01 `_v1_source`): its pinned HF revision, else its channel."""
    prov = d.get("provenance") or {}
    hf = prov.get("hf") or {}
    if hf.get("repo") and hf.get("revision"):
        return f"v1:hf:{hf['repo']}@{hf['revision']}"
    return f"v1:{prov.get('acquisition_channel') or 'UNKNOWN'}"


def _row(src: str, path: str, provenance: dict) -> dict:
    return {"source": src, "path": path, "provenance": provenance, "input": 0, "identities": 0, "effective_admissions": 0,
            "by_decision": {}, "held": 0, "rejected": 0, "quarantined": 0, "eligible": 0, "served": 0, "not_served_reasons": Counter()}


def source_accounting(*, release_id: str, v1_docs: list[dict], generations: list[dict], shipped_original_shas: set[str],
                      v1_not_established: dict[str, str] | None = None, v7_sets: dict[str, list[str]] | None = None) -> dict:
    """The ONE per-source admission accounting register (contract 2.1, PR #82 clarification 1;
    SOURCE_ADMISSION_ACCOUNTING_SCHEMA.json, scope DECLARED_BY_BUILD), written to registers/source_accounting.json.

    generations: [{corpus_generation_id, generation_manifest_sha256, hf_repo, hf_revision, identities, admissions,
    receipts_unresolved}]. Every C16 identity is bucketed exactly as the site importer buckets it (HELD*, REJECTED*,
    eligible, otherwise quarantined); an eligible copy is declared eligible only if its receipts resolve at build time
    (facts only the site can recompute are deferred: the site may narrow) and served only if it also has a v1 record
    and its original ships. v1 documents with a C16 identity for the same (doc_id, sha256) are counted on the C16 path
    only; the others on their v1 source, eligible and served unless the build's SG-1 check or v1 servability says
    otherwise (`v1_not_established`: doc_id -> reason). `v7_sets` (name -> candidate hashes, from the pinned revision's
    v7/candidate_sets/) become V7_REFERENCE sources. Local Admin uploads never appear in a declared register (R7)."""
    from mimamsa_contract.c16 import accounting
    rows: dict[str, dict] = {}
    c16_keys = set()
    v1_keys = {(d["doc_id"], d["source_copy"]["sha256"]) for d in v1_docs}
    for g in generations:
        src = f"c16:{g['corpus_generation_id']}"
        r = rows.setdefault(src, _row(src, "C16", {"generation_manifest_sha256": g["generation_manifest_sha256"], "hf_repo": g["hf_repo"],
                                                   "hf_revision": g["hf_revision"], "candidate_set_sha256": None}))
        eff = {(a["subject"]["doc_id"], a["subject"]["source_copy_sha256"]): a for a in effective_admissions(g["admissions"])}
        r["effective_admissions"] = len(eff)
        r["by_decision"] = dict(sorted(Counter(a["decision"] for a in eff.values()).items()))
        for i in g["identities"]:
            key = (i["doc_id"], i["source_copy"]["sha256"])
            c16_keys.add(key)
            a = eff.get(key)
            r["input"] += 1
            r["identities"] += 1
            if a is None:
                r["quarantined"] += 1
                r["not_served_reasons"]["NO_EFFECTIVE_ADMISSION"] += 1
            elif a["decision"].startswith("HELD"):
                r["held"] += 1
                r["not_served_reasons"]["HELD"] += 1
            elif a["decision"].startswith("REJECTED"):
                r["rejected"] += 1
                r["not_served_reasons"]["REJECTED"] += 1
            elif a.get("application_eligible") is not True:
                r["quarantined"] += 1
                r["not_served_reasons"]["NOT_ELIGIBLE"] += 1
            elif a["admission_id"] in g.get("receipts_unresolved", ()):
                r["quarantined"] += 1
                r["not_served_reasons"]["RECEIPTS_UNRESOLVED"] += 1
            else:
                r["eligible"] += 1
                if key not in v1_keys:
                    r["not_served_reasons"]["C16_ONLY_NOT_SERVABLE"] += 1
                elif key[1] not in shipped_original_shas:
                    r["not_served_reasons"]["ORIGINAL_NOT_IN_RELEASE"] += 1
                else:
                    r["served"] += 1
    for d in v1_docs:
        key = (d["doc_id"], d["source_copy"]["sha256"])
        if key in c16_keys:
            continue
        hf = (d.get("provenance") or {}).get("hf") or {}
        pinned = bool(hf.get("repo") and hf.get("revision"))
        src = _v1_source_id(d)
        r = rows.setdefault(src, _row(src, "V1", {"generation_manifest_sha256": None, "hf_repo": hf.get("repo") if pinned else None,
                                                  "hf_revision": hf.get("revision") if pinned else None, "candidate_set_sha256": None}))
        r["input"] += 1
        r["identities"] += 1
        why = (v1_not_established or {}).get(d["doc_id"]) or v1_servable_reason(d)
        if why is None and key[1] not in shipped_original_shas:
            why = "ORIGINAL_NOT_IN_RELEASE"
        if why:
            r["quarantined"] += 1
            r["not_served_reasons"][why] += 1
        else:
            r["eligible"] += 1
            r["served"] += 1
    for name, hashes in sorted((v7_sets or {}).items()):
        # V7_REFERENCE (2.1, CS1-CS5): reference only, never eligible or served; the candidate set ships as
        # registers/candidate_sets/<name>.txt, whose bytes are the preimage of candidate_set_sha256
        n = len(set(hashes))
        r = rows.setdefault(f"v7:{name}", _row(f"v7:{name}", "V7_REFERENCE", {
            "generation_manifest_sha256": None, "hf_repo": None, "hf_revision": None,
            "candidate_set_sha256": hashlib.sha256(accounting.candidate_set_bytes(hashes)).hexdigest()}))
        r["input"] = r["identities"] = r["held"] = n
        if n:
            r["not_served_reasons"]["V7_REFERENCE_ONLY"] = n
    for r in rows.values():
        r["not_served_reasons"] = dict(sorted(r["not_served_reasons"].items()))
    reg = {"contract": "mimamsa-corpus-contract/2.1", "record_kind": "source_admission_accounting", "release_id": release_id,
           "scope": "DECLARED_BY_BUILD", "sources": [rows[k] for k in sorted(rows)]}
    issues = accounting.accounting_issues(reg)
    if issues:
        raise ValueError("source accounting does not reconcile: " + "; ".join(f"{i.code} {i.where} {i.message}" for i in issues))
    return reg


def integrity_rows(v1_docs: list[dict], originals: dict, source: str) -> bytes:
    """originals: {sha256: bytes or Path} (a Path is hashed by streaming: bounded memory, C16 Stage 3)."""
    by_sha: dict[str, list[str]] = {}
    for d in v1_docs:
        by_sha.setdefault(d["source_copy"]["sha256"], []).append(d["doc_id"])
    rows = []
    for d in sorted(v1_docs, key=lambda x: x["source_copy"]["sha256"]):
        h = d["source_copy"]["sha256"]
        if h not in originals or any(r["sha256"] == h for r in rows):
            continue
        o = originals[h]
        size, got = (o.stat().st_size, sha256_file(o)) if isinstance(o, Path) else (len(o), sha256_bytes(o))
        rows.append({"record_kind": "integrity_entry", "format": INTEGRITY_FORMAT, "sha256": h, "bytes": size,
                     "media_type": d["source_copy"]["mime_type"], "page_count": d["source_copy"]["page_count"],
                     "doc_ids": sorted(by_sha[h]), "source": source, "verified_sha256": got == h})
    return b"".join(canonical.canonical_bytes(r) + b"\n" for r in rows)


# ------------------------------------------------------------------ bundle tree

def write_release_tree(root: Path, *, release_manifest_template: dict, spec: dict, defaults: dict, register, key_id: str,
                       v1_source: dict, records: dict[str, list[dict]], originals: dict[str, bytes], texts: dict[str, bytes],
                       research: dict[str, bytes], c16_files: dict[str, bytes]) -> dict:
    """Write the unsigned bundle tree (no SHA256SUMS). Returns the v1 RELEASE.json written.
    originals: {sha256: bytes or Path}; texts: {text_path: bytes or Path}; research: {research/...: bytes};
    a Path is hard-linked (or copied) and hashed by streaming, never read into memory (C16 Stage 3);
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
        if isinstance(data, Path):
            link_or_copy(data, root / rel)
            files.append({"path": rel, "sha256": sha256_file(root / rel), "bytes": (root / rel).stat().st_size, "kind": kind})
            continue
        write_bytes(root / rel, data)
        files.append({"path": rel, "sha256": sha256_bytes(data), "bytes": len(data), "kind": kind})
    for rel in sorted(c16_files):
        # B01 transport rule: corpus-v2/ and registers/ files travel as RELEASE.json files of kind 'other'
        write_bytes(root / rel, c16_files[rel])
        files.append({"path": rel, "sha256": sha256_bytes(c16_files[rel]), "bytes": len(c16_files[rel]), "kind": "other"})
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
        lines.append(f"{sha256_file(p)}  {rel}\n")
    return "".join(lines).encode("utf-8")


# ------------------------------------------------------------------ component digests (architecture section 5)

def hashset_digest(hashes) -> str:
    """ORIGINALS / TEXT_DERIVATIVES: `digests.hashset_digest` (2.1 byte definition)."""
    return digests.hashset_digest(list(hashes))


def concat_digest(root: Path, paths: list[str]) -> str:
    """RECORDS and registers: `digests.concat_digest` over the files' bytes."""
    return digests.concat_digest({p: (root / p).read_bytes() for p in paths})


def rows_component_digest(tables: list[dict]) -> str:
    """KNOWLEDGE_ROWS: `digests.table_rows_digest` (one LF-terminated line per table, final LF included)."""
    return digests.table_rows_digest([(t["table"], t["row_count"], t["rows_sha256"]) for t in tables])


def file_entries(root: Path, prefix: str) -> list[dict]:
    base = root / prefix
    out = []
    for p in files_under(base) if base.is_dir() else ([base] if base.is_file() else []):
        rel = p.relative_to(root).as_posix()
        out.append({"path": rel, "sha256": sha256_file(p), "bytes": p.stat().st_size})
    return out
