"""Cross-field and cross-record rules of mimamsa-corpus-contract/2.0 that JSON Schema cannot express.

Record rules run on one record; exchange rules run on a whole exchange (every JSONL file of one corpus generation).
Rule codes are listed in C16_CORPUS_INTEGRATION_CONTRACT.md section 11. Messages name fields, never values.
"""
from __future__ import annotations

import re

from ..issues import Issue
from . import canonical
from .schemas import KIND_TO_SCHEMA, schema_errors

PROV = re.compile(r"^PROV:(?P<code>[^:]+):(?P<p>[a-z]+)\.(?P<n>.+)$")
CHAP = re.compile(r"^CHAP:(?P<code>[^:]+):")


def _e(code, msg, where=""):
    return Issue(code, msg, where)


def record_issues(rec: dict, *, auth_ledger_version: int = 0, register=None) -> list[Issue]:
    where = f"{rec.get('record_kind')}"
    issues = [_e("SCHEMA", m, where) for m in schema_errors(rec)]
    if issues:
        return issues
    kind = rec["record_kind"]
    try:
        canonical.canonical_bytes(rec)
    except canonical.CanonicalError as exc:
        issues.append(_e("C16_NOT_CANONICAL", str(exc), where))
    if register is not None:
        hit = register.deep_match(rec)
        if hit:
            issues.append(_e("RESTRICTED_MATERIAL", f"field {hit[0]} matches the restricted-material register", where))
    if kind == "document_identity":
        issues += _identity(rec)
    elif kind == "evidence_anchor":
        issues += _anchor(rec)
    elif kind == "corpus_relationship":
        issues += _relationship(rec, auth_ledger_version)
    elif kind == "taxonomy_node":
        issues += _taxonomy(rec)
    elif kind == "corpus_admission":
        if rec["admission_id"] != canonical.admission_id(rec):
            issues.append(_e("C16_ID_MISMATCH", "admission_id is not the deterministic id of its identity tuple", where))
    elif kind == "knowledge_release_manifest":
        issues += _release_manifest(rec)
    return issues


def _release_manifest(m):
    out = []
    ids = [c["component_id"] for c in m["components"]]
    if len(ids) != len(set(ids)):
        out.append(_e("KR_DUPLICATE_COMPONENT", "component ids must be unique"))
    models = {r["sha256"] for r in m["compatibility"]["required_models"]}
    for c in m["components"]:
        if c["kind"] == "VECTOR_PACK" and m["release_class"] == "KNOWLEDGE" and c["model_sha256"] not in models:
            out.append(_e("KR_MODEL_NOT_REQUIRED", "a vector pack names a model the release does not require"))
        if c["kind"] in ("ORIGINALS",) and c["transport"] == "DELTA" and any(f.endswith(".tombstones.jsonl") for f in c["files"]):
            out.append(_e("KR_VAULT_ADD_ONLY", "originals are add-only; removal is the exclusion channel's job"))
    if m["release_class"] == "KNOWLEDGE":
        kinds = {c["kind"] for c in m["components"]}
        for must in ("RECORDS", "INTEGRITY_REGISTER", "ADMISSION_REGISTER"):
            if must not in kinds:
                out.append(_e("KR_COMPONENT_MISSING", f"a knowledge release must carry a {must} component"))
    return out


def _identity(r):
    out, sha = [], r["source_copy"]["sha256"]
    rep = r["representation"]
    if sha in rep.get("reconstructed_from_sha256", []):
        out.append(_e("C16_RECONSTRUCTED_SELF", "reconstructed_from_sha256 names the record's own copy"))
    pm = rep.get("page_mapping") or {}
    if pm and pm.get("original_sha256") == sha:
        out.append(_e("C16_RECONSTRUCTED_SELF", "page_mapping.original_sha256 names the record's own copy"))
    if pm and pm.get("original_sha256") not in rep.get("reconstructed_from_sha256", []):
        out.append(_e("C16_PAGE_MAPPING_ORIGIN", "page_mapping.original_sha256 is not one of reconstructed_from_sha256"))
    for m in rep.get("members", []):
        pr = m.get("pages")
        if isinstance(pr, dict) and "from_page" in pr and pr["to_page"] < pr["from_page"]:
            out.append(_e("C16_PAGE_RANGE", "member page range ends before it starts"))
    seqs = [m["member_seq"] for m in rep.get("members", [])]
    if seqs != list(range(1, len(seqs) + 1)):
        out.append(_e("C16_SEQUENCE", "compilation members must be numbered 1..n in order"))
    imgs = r["embedded_images"] if isinstance(r["embedded_images"], list) else None
    if imgs is not None:
        if [i["sequence"] for i in imgs] != list(range(1, len(imgs) + 1)):
            out.append(_e("C16_SEQUENCE", "embedded images must be numbered 1..n in reading order"))
        for i in imgs:
            if i["image_sequence_id"] != f"IMG:{sha}:{i['sequence']}":
                out.append(_e("C16_IMAGE_SEQUENCE_ID", "image_sequence_id must be IMG:<container sha256>:<sequence>"))
    pc = r["source_copy"]["page_count"]
    for d in r["text_derivatives"]:
        if not d["derivative_id"].startswith(r["doc_id"] + "@") or d["derivative_id"] != f"{r['doc_id']}@{d['pipeline_name']}/{d['pipeline_version']}":
            out.append(_e("C16_DERIVATIVE_ID", "derivative_id must be <doc_id>@<pipeline_name>/<pipeline_version>"))
        cov = d["coverage"]
        if cov["units_with_text"] > cov["units_total"]:
            out.append(_e("C16_COVERAGE", "units_with_text exceeds units_total"))
        if isinstance(cov["images_total"], int):
            if cov["images_text_extracted"] > cov["images_total"]:
                out.append(_e("C16_COVERAGE", "images_text_extracted exceeds images_total"))
            if imgs is not None and cov["images_total"] != len(imgs):
                out.append(_e("C16_COVERAGE", "images_total differs from the embedded image inventory"))
        elif imgs is not None:
            out.append(_e("C16_COVERAGE", "images_total is unresolved although the images are inventoried"))
        if d["pagination_basis"] == "SOURCE_PHYSICAL" and isinstance(pc, int) and cov["units_total"] != pc:
            out.append(_e("C16_COVERAGE", "a SOURCE_PHYSICAL derivative must cover every physical page"))
    re_ = r["research_eligibility"]
    if re_["source_page_citation_permitted"] and not any(
            d["pagination_basis"] == "SOURCE_PHYSICAL" for d in r["text_derivatives"]) and not (
            pm.get("basis") == "ONE_TO_ONE_PAGE_HASH_CHECKED"):
        out.append(_e("C16_PAGE_CITATION", "source page citation permitted without a source-paginated derivative or checked mapping"))
    if re_["quoting_permitted"] and not any(d["quoting_permitted"] for d in r["text_derivatives"]):
        out.append(_e("C16_QUOTING", "quoting permitted although no derivative permits quoting"))
    return out


def _anchor(a):
    out = []
    if a["anchor_id"] != canonical.anchor_id(a):
        out.append(_e("C16_ID_MISMATCH", "anchor_id is not the deterministic id of its identity tuple"))
    kind = a["locator"]["kind"]
    if kind in ("SOURCE_PHYSICAL_PAGE",) and a["representation_sha256"] != a["original_sha256"]:
        out.append(_e("C16_ANCHOR_REPRESENTATION", "a source-page locator must be measured on the original copy"))
    if kind == "RECONSTRUCTED_PAGE" and a["representation_sha256"] == a["original_sha256"]:
        out.append(_e("C16_ANCHOR_REPRESENTATION", "a reconstructed-page locator must name the reconstruction as its representation"))
    s = a.get("text_span")
    if s and s["char_end"] < s["char_start"]:
        out.append(_e("ANCHOR_RANGE", "char_end before char_start"))
    b = a.get("bbox")
    if b and (b["x1"] < b["x0"] or b["y1"] < b["y0"]):
        out.append(_e("ANCHOR_RANGE", "bbox corners out of order"))
    if b and b["unit"] == "NORMALIZED" and max(b["x0"], b["y0"], b["x1"], b["y1"]) > 1:
        out.append(_e("ANCHOR_RANGE", "normalised bbox outside 0..1"))
    if a["quoting_permitted"] and a["extraction"]["method"] in ("OCR_PAGE_IMAGE", "OCR_EMBEDDED_IMAGE"):
        out.append(_e("OCR_QUOTING", "OCR text is quotable only after documentary check; use the original page"))
    return out


def _relationship(r, ledger):
    out = []
    if r["relationship_id"] != canonical.relationship_id(r):
        out.append(_e("C16_ID_MISMATCH", "relationship_id is not the deterministic id of its identity tuple"))
    if r["category"] == "legally_validated" and ledger == 0:
        out.append(_e("LEDGER_V0_NO_APPROVAL", "a legally_validated relationship cannot exist while AUTH-LEDGER is at version 0"))
    tgt = r["target"]
    if tgt["resolved"] and r["category"] != "legally_validated":
        nid = tgt["node_id"]
        ok = {"classified_under_subject": nid.startswith("SUBJ:"), "classified_under_chapter": nid.startswith("CHAP:"),
              "associated_with_provision": nid.startswith("PROV:"), "cites_provision": nid.startswith("PROV:"),
              "interprets_provision": nid.startswith("PROV:")}.get(r["category"], nid.startswith("JUD:"))
        if not ok:
            out.append(_e("EDGE_TARGET", "target node kind does not match the relationship category"))
    proj = r.get("graph_projection")
    if proj:
        from .adapters import graph_projection
        expect = graph_projection(r)
        if expect is None or proj != {"edge_type": expect["edge"]["type"], "origin": expect["edge"]["origin"]}:
            out.append(_e("C16_GRAPH_PROJECTION_MISMATCH", "graph_projection differs from the contract mapping"))
    return out


def _taxonomy(t):
    out = []
    lvl, nid, code = t["level"], t["node_id"], t.get("instrument_code")
    if lvl == "STATUTE" and nid != f"INSTCODE:{code}":
        out.append(_e("C16_TAXONOMY_ID", "statute node_id must be INSTCODE:<instrument_code>"))
    if lvl == "CHAPTER" and (not CHAP.match(nid) or CHAP.match(nid)["code"] != code or t["parent_ids"] != [f"INSTCODE:{code}"]):
        out.append(_e("C16_TAXONOMY_ID", "chapter node must name its instrument code and have that statute as parent"))
    if lvl == "PROVISION":
        p = t["provision"]
        if nid != f"PROV:{code}:{p['prefix']}.{p['number']}":
            out.append(_e("C16_TAXONOMY_ID", "provision node_id must be PROV:<instrument_code>:<prefix>.<number>"))
        for parent in t["parent_ids"]:
            if not (parent == f"INSTCODE:{code}" or (CHAP.match(parent) and CHAP.match(parent)["code"] == code)):
                out.append(_e("C16_TAXONOMY_PARENT", "a provision's parent must be its own instrument or a chapter of it"))
    if t["parent_ids"] != sorted(t["parent_ids"]):
        out.append(_e("C16_NOT_CANONICAL", "parent_ids must be sorted"))
    return out


def exchange_issues(files: dict[str, bytes], *, auth_ledger_version: int = 0, register=None) -> list[Issue]:
    """Validate one exchange: {file name: JSONL bytes}. One record kind per file."""
    import json
    issues, by_kind = [], {k: [] for k in KIND_TO_SCHEMA}
    for name in sorted(files):
        data = files[name]
        for p in canonical.jsonl_problems(data):
            issues.append(_e("C16_JSONL", p, name))
        for n, line in enumerate(data.decode("utf-8", "replace").split("\n"), 1):
            if not line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                issues.append(_e("JSONL_MALFORMED", "line is not JSON", f"{name}:{n}"))
                continue
            for i in record_issues(rec, auth_ledger_version=auth_ledger_version, register=register):
                issues.append(Issue(i.code, i.message, f"{name}:{n}", i.severity))
            if rec.get("record_kind") in by_kind:
                by_kind[rec["record_kind"]].append(rec)
    anchors = {a["anchor_id"]: a for a in by_kind["evidence_anchor"]}
    rels = {r["relationship_id"]: r for r in by_kind["corpus_relationship"]}
    idents = {(d["doc_id"], d["source_copy"]["sha256"]): d for d in by_kind["document_identity"]}
    tax = {t["node_id"]: t for t in by_kind["taxonomy_node"]}
    for r in rels.values():
        for aid in r["anchors"]:
            a = anchors.get(aid)
            if a is None:
                issues.append(_e("DANGLING_ANCHOR", "relationship names an anchor not in the exchange", r["relationship_id"]))
            elif a["original_sha256"] != r["subject"]["source_copy_sha256"] or a["doc_id"] != r["subject"]["doc_id"]:
                issues.append(_e("C16_ANCHOR_SUBJECT", "anchor belongs to a different copy than the relationship subject", r["relationship_id"]))
        if r["category"] == "legally_validated" and r["validates_relationship_id"] not in rels:
            issues.append(_e("DANGLING_VALIDATION", "legally_validated names a relationship not in the exchange", r["relationship_id"]))
        if idents and (r["subject"]["doc_id"], r["subject"]["source_copy_sha256"]) not in idents:
            issues.append(_e("C16_DANGLING_SUBJECT", "relationship subject has no document identity record", r["relationship_id"]))
        tid = r["target"].get("node_id") if r["target"]["resolved"] else None
        if tax and tid and tid.split(":")[0] in ("SUBJ", "CHAP") and tid not in tax:
            issues.append(_e("C16_DANGLING_TAXONOMY", "classification target is not a taxonomy node in the exchange", r["relationship_id"]))
    for t in tax.values():
        for p in t["parent_ids"]:
            if p not in tax:
                issues.append(_e("C16_TAXONOMY_PARENT", "parent node not in the exchange", t["node_id"]))
    # cycle check (taxonomy must be a DAG)
    state: dict[str, int] = {}

    def visit(n):
        if state.get(n) == 1:
            return True
        if state.get(n) == 2 or n not in tax:
            return False
        state[n] = 1
        cyc = any(visit(p) for p in tax[n]["parent_ids"])
        state[n] = 2
        return cyc
    if any(visit(n) for n in sorted(tax)):
        issues.append(_e("C16_TAXONOMY_CYCLE", "taxonomy parent links form a cycle"))
    for a in anchors.values():
        if idents and not any(k[1] == a["original_sha256"] and k[0] == a["doc_id"] for k in idents):
            issues.append(_e("C16_DANGLING_SUBJECT", "anchor's original copy has no document identity record", a["anchor_id"]))
    return issues
