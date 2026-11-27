"""Cross-field and cross-record rules of mimamsa-corpus-contract/2.0 that JSON Schema cannot express.

Three validation levels (contract section 9.3):
- record_issues(rec):              one record, schema and record rules (adapter outputs, review tooling);
- exchange_issues(files, mode="partial"): an explicitly PARTIAL exchange: every present record is checked and every
  reference among present populations is resolved, but missing populations, the generation manifest and registry
  completeness are not required. Partial results are never importable;
- exchange_issues(files, mode="strict") (the default): a complete corpus generation: GENERATION.json, canonical file
  names (or declared shards), every population, counts and hashes, one generation, global key uniqueness, every
  cross-reference and registry. Signed import = a signed v1 bundle + strict validation (consumer requirement I2).
Messages name fields and keys, never values.
"""
from __future__ import annotations

import hashlib
import json
import re

from ..issues import Issue
from . import canonical
from .schemas import KIND_TO_SCHEMA, schema_errors

PROV = re.compile(r"^PROV:(?P<code>[^:]+):(?P<p>[a-z]+)\.(?P<n>.+)$")
CHAP = re.compile(r"^CHAP:(?P<code>[^:]+):")

# GraphIds.CodeByPrimaryDoc values (C15). The test checks this list against GraphModel.cs.
C15_INSTRUMENT_CODES = ("AA-1950", "AR-1954", "AFA-1950", "NA-1957", "AFT-2007", "AFT-PR-2008", "IPC-1860",
                        "CRPC-1973", "IEA-1872", "BNS-2023", "BNSS-2023", "BSA-2023")

FILE_KINDS = {"identities": "document_identity", "anchors": "evidence_anchor", "relationships": "corpus_relationship",
              "taxonomy": "taxonomy_node", "admissions": "corpus_admission", "reviewed_records": "reviewed_record"}
REQUIRED_POPULATIONS = ("identities", "anchors", "relationships", "taxonomy", "admissions")
FILE_NAME = re.compile(r"^(?P<stem>identities|anchors|relationships|taxonomy|admissions|reviewed_records)(\.[0-9]{4})?\.jsonl$")
MANIFEST = "GENERATION.json"

EVIDENCE_CATEGORIES = ("cites_provision", "interprets_provision", "refers_to_judgment", "follows", "distinguishes", "overrules")
ELIGIBLE_RESEARCH = ("ELIGIBLE_FULL", "SEARCH_ONLY")
ACCOUNTED_IMAGE_STATES = ("DONE", "NOT_REQUIRED_DECORATIVE")


def _e(code, msg, where=""):
    return Issue(code, msg, where)


# ===================================================================================== single records

def record_issues(rec, *, auth_ledger_version: int = 0, register=None) -> list[Issue]:
    if not isinstance(rec, dict):
        return [_e("JSONL_NOT_OBJECT", "record is not a JSON object")]
    where = f"{rec.get('record_kind')}"
    if rec.get("record_kind") == "reviewed_record":
        from ..schemas import validator as v1_validator
        errs = [f"$.{'.'.join(map(str, e.absolute_path))}: {e.validator} violated" for e in v1_validator("reviewed_record").iter_errors(rec)]
        return [_e("SCHEMA", m, where) for m in errs]
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
    issues += {"document_identity": _identity, "evidence_anchor": _anchor, "taxonomy_node": _taxonomy,
               "corpus_admission": _admission, "knowledge_release_manifest": lambda r: _release_manifest(r, auth_ledger_version),
               "knowledge_activation_record": lambda r: [], "corpus_generation_manifest": lambda r: [],
               "corpus_relationship": lambda r: _relationship(r, auth_ledger_version)}[kind](rec)
    return issues


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
        pc = r["source_copy"]["page_count"]
        if isinstance(pr, dict) and "to_page" in pr and isinstance(pc, int) and pr["to_page"] > pc:
            out.append(_e("C16_PAGE_RANGE", "member page range exceeds the copy's page count"))
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
        if d["derivative_id"] != f"{r['doc_id']}@{d['pipeline_name']}/{d['pipeline_version']}":
            out.append(_e("C16_DERIVATIVE_ID", "derivative_id must be <doc_id>@<pipeline_name>/<pipeline_version>"))
        cov = d["coverage"]
        if cov["units_with_text"] > cov["units_total"]:
            out.append(_e("C16_COVERAGE", "units_with_text exceeds units_total"))
        if isinstance(cov["images_total"], int):
            if cov["images_text_extracted"] > cov["images_total"]:
                out.append(_e("C16_COVERAGE", "images_text_extracted exceeds images_total"))
            if imgs is not None and cov["images_total"] != len(imgs):
                out.append(_e("C16_COVERAGE", "images_total differs from the embedded image inventory"))
            if imgs is not None and cov["images_text_extracted"] != sum(1 for i in imgs if i["ocr_state"] == "DONE"):
                out.append(_e("C16_COVERAGE", "images_text_extracted differs from the images whose OCR is DONE"))
        elif imgs is not None:
            out.append(_e("C16_COVERAGE", "images_total is unresolved although the images are inventoried"))
        if d["pagination_basis"] in ("SOURCE_PHYSICAL", "RECONSTRUCTED_PDF") and isinstance(pc, int) and cov["units_total"] != pc:
            out.append(_e("C16_COVERAGE", "a physically paginated derivative must cover every page"))
    re_ = r["research_eligibility"]
    if re_["source_page_citation_permitted"] and not any(
            d["pagination_basis"] == "SOURCE_PHYSICAL" for d in r["text_derivatives"]) and not (
            pm.get("basis") == "ONE_TO_ONE_PAGE_HASH_CHECKED"):
        out.append(_e("C16_PAGE_CITATION", "source page citation permitted without a source-paginated derivative or checked mapping"))
    if re_["quoting_permitted"] and not any(d["quoting_permitted"] for d in r["text_derivatives"]):
        out.append(_e("C16_QUOTING", "quoting permitted although no derivative permits quoting"))
    if re_["state"] == "ELIGIBLE_FULL" and (imgs is None or any(i["ocr_state"] not in ACCOUNTED_IMAGE_STATES for i in imgs)):
        out.append(_e("C16_ELIGIBILITY_UNSUPPORTED", "full eligibility although embedded images are not inventoried or not read"))
    wi = r["work_identity"]
    if wi.get("identity_verification") == "DOCUMENTARY_CHECKED":
        b = wi.get("identity_review_binding") or {}
        if b.get("review_record_id") != wi.get("identity_review_ref"):
            out.append(_e("C16_REVIEW_BINDING", "identity_review_binding names a different review record"))
        if b and b["reviewer_id"] == b["author_id"]:
            out.append(_e("C16_REVIEW_NOT_INDEPENDENT", "identity reviewer is the author"))
    return out


def _anchor(a):
    out = []
    if a["anchor_id"] != canonical.anchor_id(a):
        out.append(_e("C16_ID_MISMATCH", "anchor_id is not the deterministic id of its identity tuple"))
    kind = a["locator"]["kind"]
    if kind == "SOURCE_PHYSICAL_PAGE" and a["representation_sha256"] != a["original_sha256"]:
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
        out.append(_e("OCR_QUOTING", "OCR text is never quotable; use the original page"))
    v = a["verification"]
    if v["state"] == "DOCUMENTARY_CHECKED":
        bnd = v.get("review_binding") or {}
        if bnd.get("review_record_id") != v.get("review_ref"):
            out.append(_e("C16_REVIEW_BINDING", "review_binding names a different review record"))
        if bnd and bnd["reviewer_id"] == bnd["author_id"]:
            out.append(_e("C16_REVIEW_NOT_INDEPENDENT", "anchor reviewer is the author"))
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
    if r["verification"] == "DOCUMENTARY_CHECKED":
        b = r.get("review_binding") or {}
        if b.get("review_record_id") != r.get("review_ref"):
            out.append(_e("C16_REVIEW_BINDING", "review_binding names a different review record"))
        if b:
            if b["reviewer_id"] == b["author_id"]:
                out.append(_e("C16_REVIEW_NOT_INDEPENDENT", "reviewer is the author of the reviewed relationship"))
            if b["author_id"] != r["source"].get("author_id"):
                out.append(_e("C16_REVIEW_BINDING", "review binding author differs from the relationship's author"))
            if b["reviewed_commit"] != (r["source"]["producer"].get("commit") or ""):
                out.append(_e("C16_REVIEW_BINDING", "reviewed commit differs from the producer commit of the relationship"))
    proj = r.get("graph_projection")
    if proj:
        from .adapters import graph_projection
        expect = graph_projection(r)
        if expect is None or expect["edge"] is None or proj != {"edge_type": expect["edge"]["type"], "origin": expect["edge"]["origin"]}:
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


def _admission(a):
    out = []
    if a["admission_id"] != canonical.admission_id(a):
        out.append(_e("C16_ID_MISMATCH", "admission_id is not the deterministic id of its revision tuple"))
    if a.get("supersedes_admission_id") == a["admission_id"]:
        out.append(_e("C16_ADMISSION_SUPERSESSION", "an admission cannot supersede itself"))
    return out


# ===================================================================================== release manifests

KIND_NAMESPACE = {
    "ORIGINALS": ("originals/",), "TEXT_DERIVATIVES": ("text/",), "RECORDS": ("data/", "corpus-v2/"),
    "RESEARCH_AIDS": ("research/",), "INTEGRITY_REGISTER": ("registers/",), "ADMISSION_REGISTER": ("corpus-v2/admissions", "registers/"),
    "KNOWLEDGE_ROWS": ("accelerators/rows/",), "GRAPH": ("accelerators/graph/",), "LEXICAL_INDEX": ("accelerators/search-index/",),
    "TEXT_STORE": ("accelerators/text-store/",), "VECTOR_PACK": ("accelerators/vectors/",), "MODEL_FILE": ("models/",),
    "RULE_PACK": ("rule-packs/",),
}
RESERVED = ("sessions/", "agent/", "private/", "workflows/", "claims/", "policy/", "site/", "exclusions/", "activation-log/")
KNOWLEDGE_KINDS = ("ORIGINALS", "TEXT_DERIVATIVES", "RECORDS", "RESEARCH_AIDS", "INTEGRITY_REGISTER", "ADMISSION_REGISTER",
                   "KNOWLEDGE_ROWS", "GRAPH", "LEXICAL_INDEX", "TEXT_STORE", "VECTOR_PACK")
AUTHORITATIVE_KINDS = ("ORIGINALS", "TEXT_DERIVATIVES", "RECORDS", "RESEARCH_AIDS", "INTEGRITY_REGISTER", "ADMISSION_REGISTER")
CHEAP_KINDS = ("KNOWLEDGE_ROWS", "GRAPH", "LEXICAL_INDEX", "TEXT_STORE")
# C07-R1: mandatory payloads versus legitimately empty kinds
MANDATORY_KINDS = ("ORIGINALS", "TEXT_DERIVATIVES", "RECORDS", "INTEGRITY_REGISTER", "ADMISSION_REGISTER")
OPTIONAL_EMPTY_KINDS = ("RESEARCH_AIDS",)


def _release_manifest(m, ledger=0):
    out = []
    comps = m["components"]
    ids = [c["component_id"] for c in comps]
    if len(ids) != len(set(ids)):
        out.append(_e("KR_DUPLICATE_COMPONENT", "component ids must be unique"))
    seen: dict[str, str] = {}
    for c in comps:
        for f in c["files"]:
            p = f["path"]
            key = p.casefold()
            if key in seen:
                out.append(_e("KR_PATH_OVERLAP", "a file path belongs to more than one component (or repeats)", c["component_id"]))
            seen[key] = c["component_id"]
            if p.casefold().startswith(RESERVED) or p in ("RELEASE.json", "SHA256SUMS", "SHA256SUMS.sig", "KNOWLEDGE_RELEASE.json", "CHANGES.json"):
                out.append(_e("KR_NAMESPACE", "component file in a reserved or manifest namespace", c["component_id"]))
            elif not p.startswith(KIND_NAMESPACE[c["kind"]]):
                out.append(_e("KR_NAMESPACE", "component file outside its kind's namespace", c["component_id"]))
        listed = {f["path"] for f in c["files"]}
        for t in c.get("tables", []):
            if t["file"] not in listed:
                out.append(_e("KR_INVENTORY", "a knowledge-rows table file is not in the component inventory", c["component_id"]))
        if c["kind"] == "ORIGINALS" and any(f["path"].endswith(".tombstones.jsonl") for f in c["files"]):
            out.append(_e("KR_VAULT_ADD_ONLY", "originals are add-only; removal is the exclusion channel's job"))
    paths = sorted(seen)
    for a, b in zip(paths, paths[1:]):
        if b.startswith(a.rstrip("/") + "/"):
            out.append(_e("KR_PATH_OVERLAP", "a component file path is a directory prefix of another"))
    models = {r["sha256"] for r in m["compatibility"]["required_models"] if r["role"] == "EMBEDDER"}
    acct = m["capability"]["accounting"]
    akinds = [a["kind"] for a in acct]
    if len(akinds) != len(set(akinds)):
        out.append(_e("KR_ACCOUNTING", "a component kind is accounted more than once"))
    shipped = {c["kind"] for c in comps}
    expected = KNOWLEDGE_KINDS if m["release_class"] == "KNOWLEDGE" else ("MODEL_FILE", "VECTOR_PACK", "RULE_PACK")
    for k in expected:
        if k not in akinds:
            out.append(_e("KR_ACCOUNTING", f"no accounting entry for {k}"))
    for a in acct:
        k, st = a["kind"], a["status"]
        if (st == "SHIPPED") != (k in shipped):
            out.append(_e("KR_ACCOUNTING", f"{k} accounting status does not match the shipped components"))
        if st == "SITE_BUILDS_CHEAP" and k not in CHEAP_KINDS:
            out.append(_e("KR_ACCOUNTING", f"{k} cannot be built cheaply on site"))
        if st == "OMITTED_DEGRADED" and k in AUTHORITATIVE_KINDS:
            out.append(_e("KR_ACCOUNTING", f"authoritative {k} cannot be omitted"))
        if k == "RULE_PACK" and st == "SHIPPED" and ledger == 0:
            out.append(_e("KR_RULE_PACK_LEDGER_V0", "no rule pack may be released while AUTH-LEDGER is at version 0"))
    degraded = [a for a in acct if a["status"] == "OMITTED_DEGRADED"]
    status = {a["kind"]: a["status"] for a in acct}
    delta = m["base"]["mode"] == "DELTA"
    semantic = m["capability"]["semantic_search_promised"]
    if m["release_class"] == "KNOWLEDGE":
        # mandatory payloads: always present (full transport) or unchanged from the verified base (delta)
        for k in MANDATORY_KINDS:
            if status.get(k) not in (("SHIPPED", "UNCHANGED_FROM_BASE") if delta else ("SHIPPED",)):
                out.append(_e("KR_MANDATORY_COMPONENT", f"{k} is mandatory in every knowledge release"))
        # legitimately empty kinds may be NOT_APPLICABLE; accelerators may not (they are shipped, built or degraded)
        for k, st in status.items():
            if st == "NOT_APPLICABLE" and k not in OPTIONAL_EMPTY_KINDS and not (k == "VECTOR_PACK" and not semantic):
                out.append(_e("KR_ACCOUNTING", f"{k} cannot be NOT_APPLICABLE in a knowledge release"))
        if delta is False and any(st == "UNCHANGED_FROM_BASE" for st in status.values()):
            out.append(_e("KR_ACCOUNTING", "a full-transport release cannot rely on a base"))
    if semantic and not models:
        out.append(_e("KR_FULL_CAPABILITY_CLAIM", "semantic search promised without a declared embedder"))
    if m["capability"]["declared_service_level"] == "FULL":
        if degraded:
            out.append(_e("KR_FULL_CAPABILITY_CLAIM", "FULL service declared although a component is omitted with degradation"))
        if m["release_class"] == "KNOWLEDGE":
            if not models:
                out.append(_e("KR_FULL_CAPABILITY_CLAIM", "FULL service declared without an embedder"))
            packs = {c["model_sha256"] for c in comps if c["kind"] == "VECTOR_PACK"}
            if models - packs and not (delta and status.get("VECTOR_PACK") == "UNCHANGED_FROM_BASE"):
                out.append(_e("KR_FULL_CAPABILITY_CLAIM", "FULL service declared without vectors for every required embedder"))
            if any(status.get(k) not in ("SHIPPED", "UNCHANGED_FROM_BASE") for k in MANDATORY_KINDS):
                out.append(_e("KR_FULL_CAPABILITY_CLAIM", "FULL service declared with a mandatory payload missing"))
    elif not degraded:
        out.append(_e("KR_ACCOUNTING", "a degraded service level is declared but nothing is accounted as degraded"))
    for c in comps:
        if c["kind"] == "VECTOR_PACK" and m["release_class"] == "KNOWLEDGE" and c["model_sha256"] not in models:
            out.append(_e("KR_MODEL_NOT_REQUIRED", "a vector pack names a model the release does not require"))
    graph = next((a["status"] for a in acct if a["kind"] == "GRAPH"), None)
    gr = m["heavy_compute_on_site"]["graph_rebuild"]
    if m["release_class"] == "KNOWLEDGE" and ((graph == "SHIPPED" and gr != "ONLY_IF_ACCELERATOR_REJECTED")
                                              or (graph == "SITE_BUILDS_CHEAP" and gr != "SITE_BUILDS_CHEAP")):
        out.append(_e("KR_GRAPH_REBUILD_DECLARATION", "graph_rebuild must match how the graph is delivered"))
    return out


def component_inventory_issues(manifest: dict, sums: dict[str, str]) -> list[Issue]:
    """Consumer check: every component file is listed in the verified SHA256SUMS with the same hash."""
    out = []
    for c in manifest["components"]:
        for f in c["files"]:
            if sums.get(f["path"]) != f["sha256"]:
                out.append(_e("KR_INVENTORY", "component file missing from SHA256SUMS or hash differs", c["component_id"]))
    return out


# ===================================================================================== exchanges

def exchange_issues(files: dict[str, bytes], *, mode: str = "strict", auth_ledger_version: int = 0, register=None) -> list[Issue]:
    if mode not in ("strict", "partial"):
        raise ValueError("mode must be 'strict' or 'partial'")
    strict = mode == "strict"
    issues: list[Issue] = []
    manifest = None
    if MANIFEST in files:
        try:
            manifest = json.loads(files[MANIFEST].decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            issues.append(_e("C16_MANIFEST", "GENERATION.json is not JSON", MANIFEST))
        if manifest is not None:
            m_issues = record_issues(manifest, register=register)
            if manifest.get("record_kind") != "corpus_generation_manifest" if isinstance(manifest, dict) else True:
                m_issues.append(_e("C16_MANIFEST", "GENERATION.json is not a corpus_generation_manifest"))
            issues += [Issue(i.code, i.message, MANIFEST, i.severity) for i in m_issues]
            if m_issues:
                manifest = None
    elif strict:
        issues.append(_e("C16_MANIFEST", "strict validation needs GENERATION.json"))

    valid: dict[str, list[dict]] = {k: [] for k in FILE_KINDS.values()}
    present_stems: set[str] = set()
    for name in sorted(files):
        if name == MANIFEST:
            continue
        m = FILE_NAME.match(name)
        if not m:
            issues.append(_e("C16_FILE_NAME", "not a canonical exchange file name or shard", name))
            continue
        stem = m["stem"]
        present_stems.add(stem)
        expected_kind = FILE_KINDS[stem]
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
            if not isinstance(rec, dict):
                issues.append(_e("JSONL_NOT_OBJECT", "line is not a JSON object", f"{name}:{n}"))
                continue
            if rec.get("record_kind") != expected_kind:
                issues.append(_e("C16_KIND_MISMATCH", "record kind does not match the file name", f"{name}:{n}"))
                continue
            ri = record_issues(rec, auth_ledger_version=auth_ledger_version, register=register)
            issues += [Issue(i.code, i.message, f"{name}:{n}", i.severity) for i in ri]
            if not any(i.code == "SCHEMA" for i in ri):
                valid[expected_kind].append(rec)

    # manifest: declared files, hashes, counts
    if manifest is not None:
        declared = {f["path"]: f for f in manifest["files"]}
        for name in files:
            if name != MANIFEST and name not in declared:
                issues.append(_e("C16_MANIFEST_MISMATCH", "file not declared in GENERATION.json", name))
        for path, f in declared.items():
            if path not in files:
                issues.append(_e("C16_FILE_MISSING", "declared file is absent", path))
                continue
            if FILE_KINDS.get(FILE_NAME.match(path)["stem"]) != f["record_kind"]:
                issues.append(_e("C16_MANIFEST_MISMATCH", "declared record kind does not match the file name", path))
            if hashlib.sha256(files[path]).hexdigest() != f["sha256"]:
                issues.append(_e("C16_MANIFEST_MISMATCH", "file sha256 differs from GENERATION.json", path))
            if sum(1 for x in files[path].split(b"\n") if x) != f["records"]:
                issues.append(_e("C16_MANIFEST_MISMATCH", "record count differs from GENERATION.json", path))
    if strict:
        for stem in REQUIRED_POPULATIONS:
            if stem not in present_stems:
                issues.append(_e("C16_FILE_MISSING", f"strict exchange lacks the {stem} population"))

    idents, anchors, rels = valid["document_identity"], valid["evidence_anchor"], valid["corpus_relationship"]
    tax, adms, reviews = valid["taxonomy_node"], valid["corpus_admission"], valid["reviewed_record"]
    has = {stem: (stem in present_stems) for stem in FILE_KINDS}

    # global key uniqueness (across files and shards)
    def unique(records, key, label):
        seen = set()
        for r in records:
            k = key(r)
            if k in seen:
                issues.append(_e("C16_DUPLICATE_KEY", f"duplicate {label} across the exchange", str(k)[:80]))
            seen.add(k)
    unique(idents, lambda r: r["doc_id"], "identity doc_id")
    unique(idents, lambda r: (r["doc_id"], r["source_copy"]["sha256"]), "identity key")
    unique(anchors, lambda r: r["anchor_id"], "anchor_id")
    unique(rels, lambda r: r["relationship_id"], "relationship_id")
    unique(tax, lambda r: r["node_id"], "taxonomy node_id")
    unique(adms, lambda r: r["admission_id"], "admission_id")
    unique(reviews, lambda r: r["review_record_id"], "review_record_id")

    # one generation
    gens = {r["corpus_generation_id"] for r in idents + adms}
    gen = manifest["corpus_generation_id"] if manifest else (next(iter(gens)) if len(gens) == 1 else None)
    for r in idents + adms:
        if gen is not None and r["corpus_generation_id"] != gen:
            issues.append(_e("C16_GENERATION_MISMATCH", "record belongs to another corpus generation", r.get("doc_id") or r["subject"]["doc_id"]))
    if gen is None and len(gens) > 1:
        issues.append(_e("C16_GENERATION_MISMATCH", "records from more than one corpus generation"))

    id_by_key = {(d["doc_id"], d["source_copy"]["sha256"]): d for d in idents}
    id_by_sha: dict[str, list[dict]] = {}
    for d in idents:
        id_by_sha.setdefault(d["source_copy"]["sha256"], []).append(d)
    anc_by_id = {a["anchor_id"]: a for a in anchors}
    rel_by_id = {r["relationship_id"]: r for r in rels}
    tax_by_id = {t["node_id"]: t for t in tax}
    rev_by_id = {r["review_record_id"]: r for r in reviews}
    check_idents = strict or has["identities"]
    registry_codes = set(manifest["registries"]["instrument_codes"]) if manifest else set(C15_INSTRUMENT_CODES)
    external_jud = set(manifest["registries"]["external_judgments"]) if manifest else None

    register_sha = manifest["pinned_inputs"]["restricted_register_sha256"] if manifest else None
    issues += _admission_exchange(adms, id_by_key, id_by_sha, strict, has, check_idents, register_sha)
    issues += _anchor_exchange(anchors, id_by_key, id_by_sha, check_idents)
    issues += _relationship_exchange(rels, id_by_key, anc_by_id, rel_by_id, tax_by_id, rev_by_id, strict, has,
                                     check_idents, external_jud)
    issues += _review_binding_exchange(idents, anchors, rev_by_id, strict, has)

    # taxonomy: parents, cycles, registry codes
    for t in tax:
        for p in t["parent_ids"]:
            if p not in tax_by_id:
                issues.append(_e("C16_TAXONOMY_PARENT", "parent node not in the exchange", t["node_id"]))
        if t.get("instrument_code") and (strict or manifest) and t["instrument_code"] not in registry_codes:
            issues.append(_e("C16_TARGET_UNREGISTERED", "instrument code not in the declared registry", t["node_id"]))
    state: dict[str, int] = {}

    def visit(n):
        if state.get(n) == 1:
            return True
        if state.get(n) == 2 or n not in tax_by_id:
            return False
        state[n] = 1
        cyc = any(visit(p) for p in tax_by_id[n]["parent_ids"])
        state[n] = 2
        return cyc
    if any(visit(n) for n in sorted(tax_by_id)):
        issues.append(_e("C16_TAXONOMY_CYCLE", "taxonomy parent links form a cycle"))
    for d in idents:
        code = d["work_identity"].get("instrument_code")
        if isinstance(code, str) and (strict or manifest) and code not in registry_codes:
            issues.append(_e("C16_TARGET_UNREGISTERED", "identity instrument code not in the declared registry", d["doc_id"]))
    return issues


GATE_RECEIPT = {"G01_HASH_VERIFIED": "HASH_REDOWNLOAD", "G02_FORMAT_DETECTED": "FORMAT_DETECTION",
                "G03_RESTRICTED_REGISTER": "REGISTER_CHECK", "G04_ACCESS_MARKING_REVIEWED": "MARKING_SCREEN",
                "G05_IDENTITY_RECORD_VALID": "IDENTITY_VALIDATION", "G06_TEXT_DERIVATIVE_VERIFIED": "DERIVATIVE_VERIFICATION",
                "G07_EMBEDDED_IMAGES_ACCOUNTED": "IMAGE_ACCOUNTING", "G08_RELEVANCE_ASSESSED": "RELEVANCE_DECISION",
                "G09_DUPLICATE_RESOLVED": "DUPLICATE_RESOLUTION", "G10_SCHEMA_VALID": "SCHEMA_VALIDATION"}


def receipt_resolution_issues(admission: dict, artefacts: dict[str, bytes]) -> list[Issue]:
    """FUTURE SITE GATE FG-RECEIPTS (reference only; the site importer does not exist yet): every receipt of an
    eligible admission must resolve to an artefact carried in the signed bundle whose bytes hash to receipt_sha256."""
    import hashlib as _h
    out = []
    for g in admission["gates"]:
        r = g.get("receipt")
        if not r:
            continue
        data = artefacts.get(r["receipt_sha256"])
        if data is None or _h.sha256(data).hexdigest() != r["receipt_sha256"]:
            out.append(_e("C16_RECEIPT_UNRESOLVED", "gate receipt artefact missing from the bundle or altered", g["gate_id"]))
    return out


def _admission_exchange(adms, id_by_key, id_by_sha, strict, has, check_idents, register_sha=None):
    out = []
    groups: dict[tuple, list[dict]] = {}
    for a in adms:
        if a["decision"] == "EXCLUDED_RESTRICTED":
            out.append(_e("C16_RESTRICTED_IN_EXCHANGE", "restricted items never appear in an exportable exchange (local exclusion receipt only)", a["admission_id"]))
            continue
        key = (a["corpus_generation_id"], a["subject"]["doc_id"], a["subject"]["source_copy_sha256"])
        groups.setdefault(key, []).append(a)
        if check_idents and (a["subject"]["doc_id"], a["subject"]["source_copy_sha256"]) not in id_by_key:
            out.append(_e("C16_ADMISSION_ORPHAN", "admission has no document identity in the exchange", a["admission_id"]))
    effective = {}
    for key, recs in groups.items():
        by_id = {r["admission_id"]: r for r in recs}
        superseded: dict[str, int] = {}
        for r in recs:
            s = r.get("supersedes_admission_id")
            if s is None:
                continue
            if s == r["admission_id"] or s not in by_id:
                out.append(_e("C16_ADMISSION_SUPERSESSION", "supersedes an unknown, foreign or own admission", r["admission_id"]))
                continue
            if by_id[s]["revision"] != r["revision"] - 1:
                out.append(_e("C16_ADMISSION_SUPERSESSION", "revision must be exactly one more than the superseded revision", r["admission_id"]))
            superseded[s] = superseded.get(s, 0) + 1
        if any(n > 1 for n in superseded.values()):
            out.append(_e("C16_ADMISSION_FORK", "two admissions supersede the same revision", key[1]))
        roots = [r for r in recs if r["revision"] == 1]
        heads = [r for r in recs if r["admission_id"] not in superseded]
        if len(roots) != 1 or len(heads) != 1:
            out.append(_e("C16_ADMISSION_FORK", "the admission history is not one linear chain", key[1]))
            continue
        effective[(key[1], key[2])] = heads[0]
    if strict or has["admissions"]:
        for k in id_by_key:
            if k not in effective and not any(g[1:] == k for g in groups):
                out.append(_e("C16_ADMISSION_MISSING", "document identity has no admission decision", k[0]))
    for (doc, sha), a in effective.items():
        ident = id_by_key.get((doc, sha))
        if ident is None:
            continue
        gates = {g["gate_id"]: g["result"] for g in a["gates"]}
        imgs = ident["embedded_images"] if isinstance(ident["embedded_images"], list) else None
        evid = []
        if gates["G01_HASH_VERIFIED"] == "PASS" and ident["integrity"]["source_integrity"] != "BYTE_VERIFIED":
            evid.append("G01 PASS needs BYTE_VERIFIED integrity")
        if gates["G02_FORMAT_DETECTED"] == "PASS" and ident["source_copy"]["detected_format"] == "UNKNOWN":
            evid.append("G02 PASS with an unknown format")
        if gates["G03_RESTRICTED_REGISTER"] == "PASS" and ident["restriction"]["eligibility"] == "RESTRICTED":
            evid.append("G03 PASS on a restricted copy")
        if gates["G04_ACCESS_MARKING_REVIEWED"] == "PASS" and ident["restriction"]["eligibility"] == "NOT_ASSESSED":
            evid.append("G04 PASS while eligibility is not assessed")
        if gates["G06_TEXT_DERIVATIVE_VERIFIED"] == "NOT_APPLICABLE" and ident["text_derivatives"]:
            evid.append("G06 NOT_APPLICABLE although derivatives exist")
        if gates["G06_TEXT_DERIVATIVE_VERIFIED"] == "PASS" and not ident["text_derivatives"]:
            evid.append("G06 PASS without a derivative")
        if gates["G07_EMBEDDED_IMAGES_ACCOUNTED"] == "NOT_APPLICABLE" and imgs != []:
            evid.append("G07 NOT_APPLICABLE needs an inventoried, empty image list")
        if gates["G07_EMBEDDED_IMAGES_ACCOUNTED"] == "PASS" and (imgs is None or any(i["ocr_state"] not in ACCOUNTED_IMAGE_STATES for i in imgs)):
            evid.append("G07 PASS with images not inventoried or not read")
        if gates["G06_TEXT_DERIVATIVE_VERIFIED"] == "NOT_APPLICABLE" and ident["research_eligibility"]["state"] in ELIGIBLE_RESEARCH:
            out.append(_e("C16_SEARCH_WITHOUT_COVERAGE", "a searchable identity cannot treat its text derivative gate as not applicable", a["admission_id"]))
        for msg in evid:
            out.append(_e("C16_GATE_EVIDENCE", msg, a["admission_id"]))
        # typed receipts: asserted evidence_ref strings are not receipts; receipts must bind to this copy and outcome
        for g in a["gates"]:
            r = g.get("receipt")
            if not r:
                continue
            bad = []
            if r["receipt_kind"] != GATE_RECEIPT[g["gate_id"]]:
                bad.append("receipt kind does not match the gate")
            if r["subject_sha256"] != sha:
                bad.append("receipt is about another copy")
            if r["outcome"] != g["result"]:
                bad.append("receipt outcome differs from the gate result")
            if g["gate_id"] == "G03_RESTRICTED_REGISTER" and register_sha is not None and r["register_sha256"] != register_sha:
                bad.append("register receipt names another register revision")
            if g["gate_id"] == "G03_RESTRICTED_REGISTER" and r["register_sha256"] is None:
                bad.append("register receipt names no register revision")
            if g["gate_id"] == "G06_TEXT_DERIVATIVE_VERIFIED" and r["derivative_sha256"] not in {d["derivative_text_sha256"] for d in ident["text_derivatives"]}:
                bad.append("derivative receipt names no derivative of this copy")
            for b in bad:
                out.append(_e("C16_RECEIPT_MISMATCH", b, f"{a['admission_id']}:{g['gate_id']}"))
        scope = a.get("service_scope")
        if scope == "SEARCHABLE":
            ders = ident["text_derivatives"]
            if not ders or not any(d["coverage"]["units_with_text"] > 0 for d in ders) or ident["research_eligibility"]["state"] not in ELIGIBLE_RESEARCH:
                out.append(_e("C16_SEARCH_WITHOUT_COVERAGE", "searchable admission needs a verified, non-empty derivative and a searchable identity", a["admission_id"]))
            if imgs and any(i["ocr_state"] != "DONE" and not (i["ocr_state"] == "NOT_REQUIRED_DECORATIVE" and i.get("decorative_basis")) for i in imgs):
                out.append(_e("C16_SEARCH_WITHOUT_COVERAGE", "searchable admission with images neither read nor justified as decorative", a["admission_id"]))
        if scope == "NAVIGATION_ONLY" and ident["research_eligibility"]["state"] != "NAVIGATION_ONLY":
            out.append(_e("C16_SERVICE_SCOPE", "navigation-only admission for an identity whose research state is not NAVIGATION_ONLY", a["admission_id"]))
        dup = a.get("duplicate_of") or {}
        if a["decision"] == "ADMITTED_AS_ALTERNATE_COPY":
            if dup.get("sha256") not in id_by_sha or dup.get("sha256") not in ident["representation"].get("reconstructed_from_sha256", []):
                out.append(_e("C16_DUPLICATE_UNRESOLVED", "an alternate copy must name the original it was reconstructed from, held in the exchange", a["admission_id"]))
        if a["decision"] == "REJECTED_EXACT_DUPLICATE" and dup.get("sha256") != sha:
            out.append(_e("C16_DUPLICATE_UNRESOLVED", "an exact duplicate must name its own bytes as held elsewhere", a["admission_id"]))
        if a["application_eligible"]:
            why = []
            if ident["restriction"]["eligibility"] != "ELIGIBLE_ALL_USERS":
                why.append("restriction")
            if ident["integrity"]["source_integrity"] != "BYTE_VERIFIED":
                why.append("integrity")
            if ident["research_eligibility"]["state"] not in ELIGIBLE_RESEARCH + ("NAVIGATION_ONLY",):
                why.append("research eligibility")
            if ident["representation"]["representation_kind"] in ("WORD_IMAGES_NOT_INVENTORIED", "UNRECOGNISED_FORMAT"):
                why.append("representation")
            if imgs is None or any(i["ocr_state"] not in ACCOUNTED_IMAGE_STATES for i in imgs):
                why.append("image coverage")
            if gates["G06_TEXT_DERIVATIVE_VERIFIED"] == "PASS" and not ident["text_derivatives"]:
                why.append("text coverage")
            for w in why:
                out.append(_e("C16_ELIGIBLE_IDENTITY_NOT_READY", f"eligible admission but the identity fails: {w}", a["admission_id"]))
    return out


def _anchor_exchange(anchors, id_by_key, id_by_sha, check_idents):
    out = []
    for a in anchors:
        aid = a["anchor_id"]
        ident = id_by_key.get((a["doc_id"], a["original_sha256"]))
        if ident is None:
            if check_idents:
                out.append(_e("C16_DANGLING_SUBJECT", "anchor's original copy has no document identity", aid))
            continue
        if a["representation_sha256"] == a["original_sha256"]:
            rep = ident
        else:
            rep = next((d for d in id_by_sha.get(a["representation_sha256"], [])
                        if d["representation"]["origin_status"] == "LOCALLY_RECONSTRUCTED"
                        and a["original_sha256"] in d["representation"].get("reconstructed_from_sha256", [])), None)
            if rep is None:
                out.append(_e("C16_ANCHOR_REPRESENTATION", "representation is not a held reconstruction of the original", aid))
                continue
        imgs = ident["embedded_images"] if isinstance(ident["embedded_images"], list) else []
        dsha = a.get("derivative_text_sha256")
        loc = a["locator"]
        seq_id = loc.get("image_sequence_id")
        occ = next((i for i in imgs if i["image_sequence_id"] == seq_id), None) if seq_id else None
        method = a["extraction"]["method"]
        if seq_id and (occ is None or (a.get("image_sha256") and occ["image_sha256"] != a["image_sha256"])):
            out.append(_e("C16_ANCHOR_IMAGE", "image occurrence not in the identity or image hash differs", aid))
        if dsha is not None:
            der = next((d for d in rep["text_derivatives"] if d["derivative_text_sha256"] == dsha), None)
            owner = next((i for i in imgs if i.get("ocr_derivative_sha256") == dsha), None)
            if der is None and owner is None:
                out.append(_e("C16_ANCHOR_DERIVATIVE", "derivative is not a derivative of the anchored representation", aid))
            elif der is not None:
                if (der["pipeline_name"], der["pipeline_version"]) != (a["extraction"]["pipeline_name"], a["extraction"]["pipeline_version"]):
                    out.append(_e("C16_ANCHOR_DERIVATIVE", "anchor pipeline differs from the derivative's pipeline", aid))
                if method not in der["methods"]:
                    out.append(_e("C16_ANCHOR_DERIVATIVE", "anchor extraction method is not a method of the derivative", aid))
            else:
                # an image OCR derivative belongs to exactly one occurrence: the one the locator names
                if occ is None or owner["image_sequence_id"] != occ["image_sequence_id"]:
                    out.append(_e("C16_ANCHOR_IMAGE", "image OCR derivative belongs to another image occurrence", aid))
                if method != "OCR_EMBEDDED_IMAGE":
                    out.append(_e("C16_ANCHOR_DERIVATIVE", "an image OCR derivative needs extraction method OCR_EMBEDDED_IMAGE", aid))
        if loc["kind"] == "IMAGE_SEQUENCE" and a.get("text_span"):
            # offsets on an image anchor count into that occurrence's own OCR text only
            if occ is None or occ.get("ocr_state") != "DONE" or dsha is None or dsha != occ.get("ocr_derivative_sha256"):
                out.append(_e("C16_ANCHOR_SPAN_NOT_PERMITTED", "a span on an image anchor must count into that occurrence's OCR derivative", aid))
        if a["quoting_permitted"]:
            der_q = next((d for d in rep["text_derivatives"] if d["derivative_text_sha256"] == dsha), None)
            if not ident["research_eligibility"]["quoting_permitted"] or der_q is None or not der_q["quoting_permitted"] \
                    or a["quality"]["low_confidence"] or a["verification"]["state"] == "INCORRECT":
                out.append(_e("C16_QUOTE_NOT_PERMITTED", "anchor permits quoting but the identity, derivative or anchor quality denies it", aid))
        pc = ident["source_copy"]["page_count"]
        if loc["kind"] == "SOURCE_PHYSICAL_PAGE":
            if ident["source_copy"]["physical_pagination"] != "PHYSICAL_PAGES" or not isinstance(pc, int) or loc["physical_page"] > pc:
                out.append(_e("C16_ANCHOR_PAGE_RANGE", "physical page outside the copy's physical pages", aid))
        if loc["kind"] == "RECONSTRUCTED_PAGE":
            pm = rep["representation"].get("page_mapping") or {}
            rpc = rep["source_copy"]["page_count"]
            if pm.get("basis") != a.get("page_mapping_basis") or pm.get("original_sha256") != a["original_sha256"]:
                out.append(_e("C16_ANCHOR_MAPPING", "anchor mapping basis differs from the reconstruction's page mapping", aid))
            if isinstance(rpc, int) and loc["reconstructed_page"] > rpc:
                out.append(_e("C16_ANCHOR_PAGE_RANGE", "reconstructed page outside the reconstruction", aid))
            if loc.get("citable_as_source_page"):
                if pm.get("basis") != "ONE_TO_ONE_PAGE_HASH_CHECKED" or loc.get("physical_page") != loc["reconstructed_page"] + pm.get("offset", 0) \
                        or not isinstance(pc, int) or loc["physical_page"] > pc:
                    out.append(_e("C16_ANCHOR_MAPPING", "citable reconstructed page without a checked, in-range mapping", aid))
        if loc["kind"] == "GENERATED_SEGMENT" and dsha is not None:
            der = next((d for d in rep["text_derivatives"] if d["derivative_text_sha256"] == dsha), None)
            if der is not None and loc["generated_segment"] > der["coverage"]["units_total"]:
                out.append(_e("C16_ANCHOR_PAGE_RANGE", "generated segment outside the derivative", aid))
    return out


def _relationship_exchange(rels, id_by_key, anc_by_id, rel_by_id, tax_by_id, rev_by_id, strict, has, check_idents, external_jud):
    out = []
    for r in rels:
        rid = r["relationship_id"]
        subj = r["subject"]
        ident = id_by_key.get((subj["doc_id"], subj["source_copy_sha256"]))
        if ident is None and check_idents:
            out.append(_e("C16_DANGLING_SUBJECT", "relationship subject has no document identity", rid))
        member = None
        if ident is not None:
            members = ident["representation"].get("members", [])
            seq = subj.get("compilation_member_seq")
            if seq is not None:
                member = next((m for m in members if m["member_seq"] == seq), None)
                if member is None:
                    out.append(_e("C16_COMPILATION_MEMBER", "compilation member not in the identity", rid))
                elif subj["graph_node_ref"] != member["work_ref"]:
                    out.append(_e("C16_SUBJECT_NODE_MISMATCH", "subject node differs from the member's work reference", rid))
            else:
                if ident["representation"]["content_scope"] == "COMPILATION" and r["category"] in EVIDENCE_CATEGORIES:
                    out.append(_e("C16_COMPILATION_MEMBER", "evidence in a compilation must name the member it belongs to", rid))
                if subj["graph_node_ref"] != ident["work_identity"]["graph_node_ref"]:
                    out.append(_e("C16_SUBJECT_NODE_MISMATCH", "subject node differs from the identity's work node", rid))
        weak = True
        for aid in r["anchors"]:
            a = anc_by_id.get(aid)
            if a is None:
                if strict or has["anchors"]:
                    out.append(_e("DANGLING_ANCHOR", "relationship names an anchor not in the exchange", rid))
                continue
            if a["original_sha256"] != subj["source_copy_sha256"] or a["doc_id"] != subj["doc_id"]:
                out.append(_e("C16_ANCHOR_SUBJECT", "anchor belongs to a different copy than the relationship subject", rid))
            if a["verification"]["state"] == "INCORRECT":
                out.append(_e("C16_ANCHOR_INCORRECT", "an anchor judged INCORRECT cannot support a relationship", rid))
            pr = member.get("pages") if member else None
            pg = a["locator"].get("physical_page")
            if isinstance(pr, dict) and "from_page" in pr and pg and not pr["from_page"] <= pg <= pr["to_page"]:
                out.append(_e("C16_COMPILATION_MEMBER", "anchor page lies outside the member's pages", rid))
            if member is not None and r["verification"] == "DOCUMENTARY_CHECKED" and not (isinstance(pr, dict) and "from_page" in pr and pg):
                # an unresolved member range or a page-less anchor never establishes membership by default
                out.append(_e("C16_COMPILATION_MEMBER", "reviewed compilation evidence needs a resolved member range and a page anchor", rid))
            if a["verification"]["state"] == "DOCUMENTARY_CHECKED" and not a["quality"]["low_confidence"] \
                    and a.get("derivative_text_sha256") and a.get("text_span"):
                weak = False
        if r["verification"] == "DOCUMENTARY_CHECKED" and r["category"] in EVIDENCE_CATEGORIES and weak and (strict or has["anchors"]):
            out.append(_e("C16_FINDING_ON_WEAK_ANCHOR", "a checked relationship needs a checked, bound, confident anchor", rid))
        if r["category"] == "legally_validated" and r["validates_relationship_id"] not in rel_by_id:
            out.append(_e("DANGLING_VALIDATION", "legally_validated names a relationship not in the exchange", rid))
        if r["verification"] == "DOCUMENTARY_CHECKED":
            out += _resolve_review(r.get("review_binding") or {}, rid, rev_by_id, "candidate", strict, has)
        tid = r["target"].get("node_id") if r["target"]["resolved"] else None
        if tid and r["category"] != "legally_validated":
            # partial exchanges resolve their own subject/chapter nodes; provision targets resolve against the full
            # taxonomy registry, which only a strict exchange is required to carry
            kind_ = tid.split(":")[0]
            if ((kind_ in ("SUBJ", "CHAP") and (strict or has["taxonomy"])) or (kind_ == "PROV" and strict)) and tid not in tax_by_id:
                out.append(_e("C16_TARGET_UNREGISTERED", "target is not a taxonomy node in the exchange", rid))
            if tid.startswith("JUD:"):
                held = any(k[0] == tid[4:] for k in id_by_key)
                if not held and (tid.startswith("JUD:JG-") and external_jud is not None and tid not in external_jud
                                 or not tid.startswith("JUD:JG-") and (strict or has["identities"])):
                    out.append(_e("C16_TARGET_UNREGISTERED", "judgment target is neither held nor a declared external judgment", rid))
    return out


def _resolve_review(b, subject_id, rev_by_id, subject_kind, strict, has):
    out = []
    rec = rev_by_id.get(b.get("review_record_id"))
    if rec is None:
        if strict or has["reviewed_records"]:
            out.append(_e("C16_REVIEW_UNRESOLVED", "review binding names no reviewed_record in the exchange", subject_id))
        return out
    if canonical.record_sha256(rec) != b["review_record_sha256"]:
        out.append(_e("C16_REVIEW_BINDING", "reviewed_record bytes differ from the bound sha256", subject_id))
    if rec["subject"] != {"kind": subject_kind, "id": subject_id}:
        out.append(_e("C16_REVIEW_BINDING", "reviewed_record is about another subject", subject_id))
    if rec["axis"] != "evidence_fidelity" or rec["to_value"] != "DOCUMENTARY_CHECKED":
        out.append(_e("C16_REVIEW_BINDING", "reviewed_record does not raise evidence fidelity to DOCUMENTARY_CHECKED", subject_id))
    if rec["reviewer"]["reviewer_id"] != b["reviewer_id"] or rec["reviewer"]["kind"] != b["reviewer_kind"]:
        out.append(_e("C16_REVIEW_BINDING", "reviewer differs from the binding", subject_id))
    if rec["reviewed_artefact"]["author_id"] != b["author_id"] or rec["reviewed_artefact"]["reviewed_commit"] != b["reviewed_commit"]:
        out.append(_e("C16_REVIEW_BINDING", "reviewed author or commit differs from the binding", subject_id))
    if rec["reviewer"]["reviewer_id"] == rec["reviewed_artefact"]["author_id"]:
        out.append(_e("C16_REVIEW_NOT_INDEPENDENT", "reviewer is the author", subject_id))
    return out


def _review_binding_exchange(idents, anchors, rev_by_id, strict, has):
    out = []
    for a in anchors:
        if a["verification"]["state"] == "DOCUMENTARY_CHECKED":
            out += _resolve_review(a["verification"].get("review_binding") or {}, a["anchor_id"], rev_by_id, "candidate", strict, has)
    for d in idents:
        if d["work_identity"]["identity_verification"] == "DOCUMENTARY_CHECKED":
            out += _resolve_review(d["work_identity"].get("identity_review_binding") or {}, d["doc_id"], rev_by_id, "document", strict, has)
    return out
