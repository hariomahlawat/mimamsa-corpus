"""B03 knowledge rows (contract 2.1 interface): typed allowlist, canonical row files and the re-derivation check.

Rows are data, never SQL. A row file is canonical JSONL: one object per row with EXACTLY the allowlisted columns,
sorted by primary key, LF line ends, final LF. The site loader (.NET, restricted role mimamsa_kr_loader) applies
the same checks before COPY, recounts and re-hashes after the load, and re-derives every row from the authoritative
records (ROWS_REDERIVE_COMPARE). For the five C16 tables this module is the reference derivation the .NET writer
must match byte for byte; candidates, provision_versions and the graph tables are derived by Mimamsa.Knowledge.
"""
from __future__ import annotations

import hashlib
import json

from jsonschema import Draft202012Validator

from ..issues import Issue
from . import canonical
from .schemas import registry, schema, schema_errors

SCHEMA_NAME = "KNOWLEDGE_ROWS_SCHEMA.json"
MAX_ROW_BYTES = 1 << 20


def _e(code, msg, where=""):
    return Issue(code, msg, where)


def allowlist_issues(doc) -> list[Issue]:
    issues = [_e("SCHEMA", m, "knowledge_rows_allowlist") for m in schema_errors(doc)]
    if issues:
        return issues
    seen = set()
    for t in doc["tables"]:
        if t["table"] in seen:
            issues.append(_e("KR_ROWS_ALLOWLIST", "table listed twice", t["table"]))
        seen.add(t["table"])
        if t["row_schema"] != f"#/$defs/{t['table']}_row":
            issues.append(_e("KR_ROWS_ALLOWLIST", "row schema does not name the table's own row definition", t["table"]))
        cols = set(schema(SCHEMA_NAME)["$defs"][f"{t['table']}_row"]["properties"])
        if not set(t["primary_key"]) <= cols:
            issues.append(_e("KR_ROWS_ALLOWLIST", "primary key column not in the row definition", t["table"]))
        if (t["table"] in ("graph_nodes", "graph_edges")) != (t["owner_component"] == "GRAPH"):
            issues.append(_e("KR_ROWS_ALLOWLIST", "graph tables are owned by GRAPH, all others by KNOWLEDGE_ROWS (I-2)", t["table"]))
    return issues


GRAPH_TABLES = ("graph_edges", "graph_nodes")


def manifest_table_owner_issues(manifest: dict) -> list[Issue]:
    """I-2 on a knowledge release manifest (2.1 clarification): graph_nodes and graph_edges are declared only by the
    GRAPH component (files under accelerators/graph/, loaded by the same typed loader into kr_<n>_staging); every
    other row table only by KNOWLEDGE_ROWS. No other component kind may declare row tables."""
    out = []
    for c in manifest.get("components", []):
        for t in c.get("tables", []):
            owner = "GRAPH" if t["table"] in GRAPH_TABLES else "KNOWLEDGE_ROWS"
            if c["kind"] != owner:
                out.append(_e("KR_ROWS_ALLOWLIST", f"table {t['table']} belongs to the {owner} component (I-2)", c["component_id"]))
    return out


def _row_validator(table: str) -> Draft202012Validator:
    s = {"$ref": f"https://contract.mimamsa.invalid/c16/{SCHEMA_NAME}#/$defs/{table}_row"}
    return Draft202012Validator(s, registry=registry())


def row_file_bytes(rows: list[dict], primary_key: list[str]) -> bytes:
    ordered = sorted(rows, key=lambda r: tuple(r[k] for k in primary_key))
    return b"".join(canonical.canonical_bytes(r) + b"\n" for r in ordered)


def rows_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def row_file_issues(table: str, data: bytes, allowlist: dict) -> list[Issue]:
    """What the loader checks before COPY: allowlisted table, typed rows with exactly the allowlisted columns, no
    oversized row, unique primary key, canonical bytes in primary-key order. Any issue rejects the component."""
    spec = next((t for t in allowlist["tables"] if t["table"] == table), None)
    if spec is None:
        return [_e("KR_ROWS_TABLE_NOT_ALLOWLISTED", "table not on the application's allowlist", table)]
    issues, rows = [], []
    v = _row_validator(table)
    for n, line in enumerate(data.split(b"\n"), 1):
        if not line:
            continue
        if len(line) > MAX_ROW_BYTES:
            issues.append(_e("KR_ROWS_OVERSIZED", "row exceeds the size limit", f"{table}:{n}"))
            continue
        try:
            row = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            issues.append(_e("KR_ROWS_MALFORMED", "row is not UTF-8 JSON", f"{table}:{n}"))
            continue
        if not isinstance(row, dict):
            issues.append(_e("KR_ROWS_MALFORMED", "row is not a JSON object", f"{table}:{n}"))
            continue
        errs = list(v.iter_errors(row))
        if errs:
            issues.append(_e("KR_ROWS_TYPE", "row violates its typed definition (unknown, missing or mistyped column)", f"{table}:{n}"))
            continue
        rows.append(row)
    keys = [tuple(r[k] for k in spec["primary_key"]) for r in rows]
    if len(keys) != len(set(keys)):
        issues.append(_e("KR_ROWS_DUPLICATE_KEY", "duplicate primary key", table))
    if not issues:
        try:
            if row_file_bytes(rows, spec["primary_key"]) != data:
                issues.append(_e("KR_ROWS_NOT_CANONICAL", "rows not canonical or not in primary-key order", table))
        except canonical.CanonicalError as exc:
            issues.append(_e("KR_ROWS_NOT_CANONICAL", str(exc), table))
    return issues


# ------------------------------------------------------------------ reference derivation (C16 tables)

def derive_rows(pop: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """The PYTHON_REFERENCE derivation from a strict C16 exchange population."""
    adms = pop.get("admissions", [])
    superseded = {a.get("supersedes_admission_id") for a in adms}
    gref = lambda x: x if isinstance(x, str) else None  # noqa: E731  (UNRESOLVED objects become NULL)
    return {
        "document_identities": [{
            "doc_id": d["doc_id"], "source_copy_sha256": d["source_copy"]["sha256"], "corpus_generation_id": d["corpus_generation_id"],
            "representation_kind": d["representation"]["representation_kind"], "work_kind": d["work_identity"]["work_kind"],
            "graph_node_ref": gref(d["work_identity"]["graph_node_ref"]), "research_state": d["research_eligibility"]["state"],
            "quoting_permitted": d["research_eligibility"]["quoting_permitted"], "record_sha256": canonical.record_sha256(d)}
            for d in pop.get("identities", [])],
        "evidence_anchors": [{
            "anchor_id": a["anchor_id"], "doc_id": a["doc_id"], "original_sha256": a["original_sha256"],
            "representation_sha256": a["representation_sha256"], "derivative_text_sha256": a.get("derivative_text_sha256"),
            "locator_kind": a["locator"]["kind"], "physical_page": a["locator"].get("physical_page"),
            "image_sequence_id": a["locator"].get("image_sequence_id"), "verification_state": a["verification"]["state"],
            "quoting_permitted": a["quoting_permitted"], "record_sha256": canonical.record_sha256(a)}
            for a in pop.get("anchors", [])],
        "corpus_relationships": [{
            "relationship_id": r["relationship_id"], "category": r["category"], "subject_doc_id": r["subject"]["doc_id"],
            "subject_sha256": r["subject"]["source_copy_sha256"],
            "target_node_id": r["target"].get("node_id") if r["target"]["resolved"] else None,
            "target_raw_reference": None if r["target"]["resolved"] else r["target"].get("raw_reference"),
            "evidentiary_basis": r["evidentiary_basis"], "verification": r["verification"],
            "has_legal_effect": r["has_legal_effect"], "record_sha256": canonical.record_sha256(r)}
            for r in pop.get("relationships", [])],
        "taxonomy_nodes": [{
            "node_id": t["node_id"], "level": t["level"], "label": t["label"],
            "parent_ids_json": canonical.canonical_bytes(sorted(t["parent_ids"])).decode("utf-8"),
            "instrument_code": t.get("instrument_code"), "verification": t["verification"], "record_sha256": canonical.record_sha256(t)}
            for t in pop.get("taxonomy", [])],
        "corpus_admissions": [{
            "admission_id": a["admission_id"], "doc_id": a["subject"]["doc_id"], "source_copy_sha256": a["subject"]["source_copy_sha256"],
            "revision": a["revision"], "decision": a["decision"], "application_eligible": a["application_eligible"],
            "service_scope": a.get("service_scope", "NONE"), "is_effective": a["admission_id"] not in superseded,
            "record_sha256": canonical.record_sha256(a)}
            for a in adms],
    }


def rederive_compare(table: str, shipped: bytes, pop: dict, allowlist: dict) -> list[Issue]:
    """ROWS_REDERIVE_COMPARE: the shipped file must equal the rows re-derived from the authoritative records."""
    spec = next((t for t in allowlist["tables"] if t["table"] == table), None)
    if spec is None or spec["derivation"] != "PYTHON_REFERENCE":
        return [_e("KR_ROWS_NOT_DERIVABLE_HERE", "table is derived by the .NET writer (DOTNET_B03)", table)]
    want = row_file_bytes(derive_rows(pop)[table], spec["primary_key"])
    if want != shipped:
        return [_e("KR_ROWS_REDERIVE_MISMATCH", "shipped rows differ from rows re-derived from the records", table)]
    return []
