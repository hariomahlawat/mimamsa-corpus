"""Cycle 16 corpus integration contract (mimamsa-corpus-contract/2.0): schemas, fixtures, rules and adapters.

Runs in the existing CI contract job (app-ci.yml, `python -m pytest tests` in app/contract) with the pinned
jsonschema. It checks:
- schema self-consistency (draft 2020-12 meta-schema, $id layout, every $ref resolvable offline, enumerations that
  must agree with contract v1 and with the C15 graph model in the B1 application);
- every positive fixture is accepted (schema and rules, single records and whole exchanges);
- every negative fixture is rejected for its intended reason;
- the fixtures are byte-identical to the deterministic builder output and canonical;
- the backward-compatible adapters (v1, C15 graph, PR #76 inventory rows, v7 candidate records).
"""
from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from mimamsa_contract.c16 import adapters, canonical
from mimamsa_contract.c16.rules import exchange_issues, record_issues
from mimamsa_contract.c16.schemas import C16_DIR, KIND_TO_SCHEMA, SHARED, registry, schema, schema_errors
from mimamsa_contract.restricted import load_register
from mimamsa_contract.schemas import validator as v1_validator

CONTRACT = Path(__file__).resolve().parents[1]
FIX = CONTRACT / "fixtures" / "c16"
REPO = CONTRACT.parents[1]
GRAPH_MODEL = REPO / "app" / "b1" / "src" / "Mimamsa.Core" / "Graph" / "GraphModel.cs"
MANIFEST = json.loads((FIX / "FIXTURES.json").read_text(encoding="utf-8"))


def _codes(issues):
    return {i.code for i in issues}


def _load(rel):
    data = (FIX / rel).read_bytes()
    if rel.endswith(".jsonl"):
        return [json.loads(x) for x in data.decode("utf-8").splitlines() if x]
    return json.loads(data)


# ---------------------------------------------------------------- schema self-consistency

def test_every_c16_schema_is_valid_draft_2020_12_with_local_id():
    names = sorted(p.name for p in C16_DIR.glob("*.json"))
    assert names == sorted([SHARED, *KIND_TO_SCHEMA.values()])
    for name in names:
        doc = json.loads((C16_DIR / name).read_text(encoding="utf-8"))
        assert doc["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        Draft202012Validator.check_schema(doc)
        assert doc["$id"] == f"https://contract.mimamsa.invalid/c16/{name}"
    registry()  # loads v1 + c16 and re-checks every $id


def _refs(node):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "$ref":
                yield v
            else:
                yield from _refs(v)
    elif isinstance(node, list):
        for v in node:
            yield from _refs(v)


def test_every_ref_resolves_offline():
    reg = registry()
    for p in C16_DIR.glob("*.json"):
        base = f"https://contract.mimamsa.invalid/c16/{p.name}"
        resolver = reg.resolver(base)
        for ref in _refs(json.loads(p.read_text(encoding="utf-8"))):
            resolver.lookup(ref)  # raises on an unknown or remote reference


def test_record_kinds_and_contract_const_agree():
    for kind, name in KIND_TO_SCHEMA.items():
        s = schema(name)
        assert s["properties"]["record_kind"] == {"const": kind}
        assert "contract" in s["required"] and "record_kind" in s["required"]
        assert s.get("additionalProperties") is False


def _cs_constants(cls: str) -> dict[str, str]:
    text = GRAPH_MODEL.read_text(encoding="utf-8")
    body = re.search(r"public static class " + cls + r"\s*\{(.*?)\n\}", text, re.S).group(1)
    return dict(re.findall(r"(\w+)\s*=\s*\"([A-Z_]+)\"", body))


def test_verification_vocabulary_matches_c15_graph_model():
    shared = schema(SHARED)["$defs"]
    cs = _cs_constants("Verification")
    assert set(shared["graph_verification"]["enum"]) == set(cs.values())
    builder = re.search(r"BuilderValues\s*=\s*\{([^}]*)\}", GRAPH_MODEL.read_text(encoding="utf-8")).group(1)
    names = [x.strip() for x in builder.split(",")]
    assert set(shared["producer_verification"]["enum"]) == {cs[n] for n in names}
    assert set(adapters.BUILDER_VERIFICATION) == {cs[n] for n in names}


def test_edge_mapping_uses_c15_types_or_declared_proposals():
    c15 = set(_cs_constants("EdgeType").values())
    v1_relations = set(json.loads((CONTRACT / "schemas" / "v1" / "candidate.schema.json").read_text(encoding="utf-8"))
                       ["allOf"][2]["then"]["properties"]["payload"]["properties"]["relation"]["enum"])
    cats = set(schema("PROVISION_JUDGMENT_RELATIONSHIP_SCHEMA.json")["properties"]["category"]["enum"])
    assert set(adapters.CATEGORY_TO_EDGE) == cats - {"legally_validated"}
    for cat, etype in adapters.CATEGORY_TO_EDGE.items():
        assert etype in c15 or etype in adapters.PROPOSED_EDGE_TYPES, cat
    for etype in adapters.PROPOSED_EDGE_TYPES & {"INTERPRETS_PROVISION", "DISTINGUISHES_PROPOSITION"}:
        assert etype in v1_relations  # already in the contract v1 vocabulary; only C15 lacks them
    assert adapters.PROPOSED_EDGE_TYPES.isdisjoint(c15)


def test_v1_enumerations_are_supersets_where_c16_projects_into_v1():
    v1_doc = json.loads((CONTRACT / "schemas" / "v1" / "document.schema.json").read_text(encoding="utf-8"))
    v1_mimes = set(v1_doc["properties"]["source_copy"]["properties"]["mime_type"]["enum"])
    c16_mimes = set(schema("DOCUMENT_IDENTITY_SCHEMA.json")["properties"]["source_copy"]["properties"]["mime_type"]["enum"])
    assert v1_mimes <= c16_mimes  # every v1 copy can be described; extra C16 formats need a v1 adapter (matrix)
    assert c16_mimes - v1_mimes == {"application/msword", "application/rtf"}
    v1_compl = set(v1_doc["properties"]["source_copy"]["properties"]["completeness"]["enum"])
    c16_compl = set(schema("DOCUMENT_IDENTITY_SCHEMA.json")["properties"]["representation"]["properties"]["completeness"]["enum"])
    assert c16_compl - v1_compl == {"PARTIAL_EXTRACT"}


def test_admission_gate_enumeration_and_required_gates_agree():
    s = schema("CORPUS_ADMISSION_SCHEMA.json")
    required = {c["contains"]["properties"]["gate_id"]["const"] for c in s["properties"]["gates"]["allOf"]}
    assert required == set(s["$defs"]["gate_id"]["enum"])


# ---------------------------------------------------------------- fixtures

def test_fixtures_are_byte_identical_to_builder_output():
    out = subprocess.run([sys.executable, "-I", str(FIX / "build_fixtures.py"), "--check"], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr


@pytest.mark.parametrize("entry", MANIFEST["positive"], ids=lambda e: e["file"])
def test_positive_fixture_accepted(entry, register):
    if entry["kind"] == "exchange_set":
        files = {f: (FIX / f).read_bytes() for f in [entry["file"], *entry["with"]]}
        issues = exchange_issues(files, auth_ledger_version=entry["ledger"], register=register)
    elif entry["kind"] == "jsonl":
        data = (FIX / entry["file"]).read_bytes()
        assert canonical.jsonl_problems(data) == []
        issues = [i for r in _load(entry["file"]) for i in record_issues(r, auth_ledger_version=entry["ledger"], register=register)]
    else:
        issues = record_issues(_load(entry["file"]), auth_ledger_version=entry["ledger"], register=register)
    assert [str(i) for i in issues] == []


@pytest.mark.parametrize("entry", MANIFEST["negative"], ids=lambda e: e["file"])
def test_negative_fixture_rejected_for_intended_reason(entry, register):
    if entry["kind"] == "jsonl":
        issues = exchange_issues({entry["file"]: (FIX / entry["file"]).read_bytes()}, register=register)
    else:
        rec = _load(entry["file"])
        issues = record_issues(rec, auth_ledger_version=entry["ledger"], register=register)
    assert entry["expect_code"] in _codes(issues), [str(i) for i in issues]
    if entry["schema_path_contains"]:
        assert any(entry["schema_path_contains"] in i.message for i in issues if i.code == "SCHEMA"), [str(i) for i in issues]


def test_required_fixture_coverage():
    """The brief's mandatory fixture cases are present."""
    files = {e["file"] for e in MANIFEST["positive"] + MANIFEST["negative"]}
    for must in ("positive/relationships_ar_22_23_30.jsonl", "positive/identity_word_screenshots.json",
                 "positive/identity_reconstructed_pdf.json", "positive/identity_extract_pdf.json",
                 "positive/identity_compilation_pdf.json",
                 "negative/N01_folder_classification_as_verified_finding.json",
                 "negative/N02_reconstructed_pdf_claims_original.json", "negative/N03_extract_claims_complete.json",
                 "negative/N04_missing_mandatory_sha256.json"):
        assert must in files
    kinds = {json.loads(x)["representation"]["representation_kind"]
             for x in (FIX / "positive" / "identities.jsonl").read_text(encoding="utf-8").splitlines()}
    assert {"NATIVE_DIGITAL_PDF", "SCANNED_PDF", "MIXED_PDF", "WORD_NATIVE_TEXT", "WORD_WITH_EMBEDDED_IMAGES",
            "RECONSTRUCTED_SEARCHABLE_PDF", "WORD_IMAGES_NOT_INVENTORIED"} <= kinds
    anchors = {json.loads(x)["locator"]["kind"] for x in (FIX / "positive" / "anchors.jsonl").read_text(encoding="utf-8").splitlines()}
    assert anchors == {"SOURCE_PHYSICAL_PAGE", "RECONSTRUCTED_PAGE", "GENERATED_SEGMENT", "IMAGE_SEQUENCE"}


def test_ar_22_23_30_keeps_one_association_per_provision_and_per_path():
    rels = _load("positive/relationships_ar_22_23_30.jsonl")
    prov = [r for r in rels if r["category"] == "associated_with_provision"]
    by_path = {}
    for r in prov:
        by_path.setdefault(r["classification_provenance"]["relative_path"], set()).add(r["target"]["node_id"])
    assert sorted(by_path.values(), key=len) == [{"PROV:AR-1954:r.22"},
                                                 {"PROV:AR-1954:r.22", "PROV:AR-1954:r.23", "PROV:AR-1954:r.30"}]
    assert len({r["relationship_id"] for r in rels}) == len(rels)  # the second r.22 association is not merged away
    assert all(r["verification"] == "CANDIDATE" and not r["is_finding"] for r in prov)
    assert all(r["subject"]["source_copy_sha256"] == prov[0]["subject"]["source_copy_sha256"] for r in rels)  # one copy


def test_folder_classification_alone_cannot_become_a_finding():
    base = next(r for r in _load("positive/relationships.jsonl") if r["evidentiary_basis"] == "FOLDER_PATH")
    for ver in ("DOCUMENTARY_CHECKED", "LEGAL_REVIEWED"):
        x = copy.deepcopy(base)
        x.update(verification=ver, review_ref="RV-FIXTURE-0009" if ver == "DOCUMENTARY_CHECKED" else None)
        assert schema_errors(x)


# ---------------------------------------------------------------- canonical serialisation and ids

def test_canonical_bytes_rules():
    assert canonical.canonical_bytes({"b": 1, "a": [1.5, 12.0, "x"]}) == b'{"a":[1.5,12,"x"],"b":1}'
    for bad in ({"x": float("nan")}, {"x": -0.0}, {"x": 0.12345}, {"x": "é"}, {"x": 2**60}):
        with pytest.raises(canonical.CanonicalError):
            canonical.canonical_bytes(bad)


def test_ids_are_stable_under_non_identity_changes():
    r = _load("positive/relationships.jsonl")[0]
    x = copy.deepcopy(r)
    x["uncertainty"] = "reworded"
    x["source"]["rule_version"] = "9.9"
    assert canonical.relationship_id(x) == r["relationship_id"]
    x["subject"]["source_copy_sha256"] = "0" * 64
    assert canonical.relationship_id(x) != r["relationship_id"]
    a = _load("positive/anchors.jsonl")[0]
    y = copy.deepcopy(a)
    y["verification"] = {"state": "DOCUMENTARY_CHECKED", "review_ref": "RV-FIXTURE-0003"}
    assert canonical.anchor_id(y) == a["anchor_id"]


def test_exchange_detects_dangling_anchor_and_taxonomy_cycle(register):
    rels = _load("positive/relationships.jsonl")
    tax = _load("positive/taxonomy.jsonl")
    files = {"relationships.jsonl": canonical.dumps_jsonl(rels), "taxonomy.jsonl": canonical.dumps_jsonl(tax)}
    assert "DANGLING_ANCHOR" in _codes(exchange_issues(files, register=register))
    cyc = copy.deepcopy(tax)
    for t in cyc:
        if t["node_id"] == "SUBJ:court_martial":
            t["parent_ids"] = ["SUBJ:local:court-martial"]
        if t["node_id"] == "SUBJ:local:court-martial":
            t["parent_ids"] = ["SUBJ:court_martial"]
    assert "C16_TAXONOMY_CYCLE" in _codes(exchange_issues({"taxonomy.jsonl": canonical.dumps_jsonl(cyc)}, register=register))


def test_restricted_register_applies_to_c16_records(register):
    """A C16 record naming a registered copy is rejected (fail closed); the record's own flags cannot override it."""
    assert register.sha256s, "the register lists no copy; the exclusion rule cannot be shown to work"
    x = _load("positive/identity_extract_pdf.json")
    x["source_copy"]["sha256"] = sorted(register.sha256s)[0]
    x["source_copy"]["vault_path"] = f"vault/sha256/{x['source_copy']['sha256'][:2]}/{x['source_copy']['sha256']}"
    assert "RESTRICTED_MATERIAL" in _codes(record_issues(x, register=register))


# ---------------------------------------------------------------- adapters

def _v1_example(name):
    return json.loads((CONTRACT / "examples" / f"{name}.example.json").read_text(encoding="utf-8"))


def test_v1_document_adapts_to_valid_identity_keeping_ids():
    doc, der = _v1_example("document"), _v1_example("derived_text")
    ident = adapters.identity_from_v1_document(doc, [der], corpus_generation_id="CG-20261127-v1-adapter-00000000")
    assert schema_errors(ident) == []
    assert record_issues(ident) == []
    assert ident["doc_id"] == doc["doc_id"] and ident["source_copy"]["sha256"] == doc["source_copy"]["sha256"]
    assert ident["text_derivatives"][0]["derivative_id"] == f"{der['doc_id']}@{der['pipeline']['name']}/{der['pipeline']['version']}"
    assert ident["research_eligibility"]["whole_work_claims_permitted"] is False  # v1 never established work completeness


def test_v1_page_anchor_round_trip_and_v1_schema():
    page_anchor_schema = {"$ref": "https://contract.mimamsa.invalid/v1/common.schema.json#/$defs/page_anchor"}
    v = Draft202012Validator(page_anchor_schema, registry=registry())
    cand = _v1_example("candidate_graph_edge")
    for pa in cand["anchors"]:
        a = adapters.anchor_from_v1_page_anchor(pa, doc_id=cand["source_doc_id"])
        assert schema_errors(a) == [] and record_issues(a) == []
        back = adapters.anchor_to_v1_page_anchor(a)
        assert list(v.iter_errors(back)) == []
        assert (back["source_copy_sha256"], back["page"]) == (pa["source_copy_sha256"], pa["page"])


def test_anchors_without_source_page_do_not_project_to_v1():
    for a in _load("positive/anchors.jsonl"):
        out = adapters.anchor_to_v1_page_anchor(a)
        if a["locator"]["kind"] in ("GENERATED_SEGMENT", "IMAGE_SEQUENCE"):
            assert out is None
        if a["locator"]["kind"] == "RECONSTRUCTED_PAGE":
            assert out["source_copy_sha256"] == a["original_sha256"] and "derivative_text_sha256" not in out


def test_v1_graph_edge_candidate_adapts_and_projects_to_c15():
    cand = _v1_example("candidate_graph_edge")
    anchors = [adapters.anchor_from_v1_page_anchor(pa, doc_id=cand["source_doc_id"]) for pa in cand["anchors"]]
    rel = adapters.relationship_from_v1_candidate(cand, subject_sha256=cand["anchors"][0]["source_copy_sha256"],
                                                  subject_node=f"JUD:{cand['source_doc_id']}", source_date="2020-01-01",
                                                  anchors=anchors)
    if rel is None:
        assert cand["payload"]["relation"] not in adapters.V1_RELATION_TO_CATEGORY
        return
    assert schema_errors(rel) == [] and record_issues(rel) == []
    proj = adapters.graph_projection(rel, {a["anchor_id"]: a for a in anchors})["edge"]
    assert proj["type"] == cand["payload"]["relation"] or proj["type"] in adapters.PROPOSED_EDGE_TYPES
    assert proj["verification"] in adapters.BUILDER_VERIFICATION and proj["review_state"] == "UNREVIEWED"


def test_reviewed_relationship_projects_as_builder_edge_plus_review_overlay():
    r = next(x for x in _load("positive/relationships.jsonl") if x["verification"] == "DOCUMENTARY_CHECKED")
    p = adapters.graph_projection(r)
    assert p["edge"]["verification"] == "CANDIDATE"  # GraphStore refuses reviewed values on edges (ADR-0006)
    assert p["review"] == {"edge_id": p["edge"]["id"], "review_state": "DOCUMENTARY_CHECKED", "review_ref": r["review_ref"]}


def test_c16_edge_ids_distinguish_same_endpoints_from_different_paths():
    rels = [r for r in _load("positive/relationships_ar_22_23_30.jsonl")
            if r["category"] == "associated_with_provision" and r["target"].get("node_id") == "PROV:AR-1954:r.22"]
    edges = {adapters.graph_projection(r)["edge"]["id"] for r in rels}
    assert len(rels) == 2 and len(edges) == 2


SYNTH_ROW = {
    "inventory_id": "L-" + "1" * 20, "relative_path": "Army Rules\\AR 22, 23, 30 - Lt Col A B Example v Union of India.docx",
    "filename": "AR 22, 23, 30 - Lt Col A B Example v Union of India.docx", "extension": ".docx", "detected_format": "DOCX",
    "size_bytes": 54321, "sha256": "ab" * 32, "page_count": 1, "language": "en", "text_available": True,
    "normalized_text_sha256": "cd" * 32, "derivative_sha256": "ef" * 32, "extraction_method": "docx-xml",
    "encrypted": False, "parsing_error": None, "candidate_document_type": "judgment", "ocr_required_pages": [],
    "relevance": True, "restricted": False, "classification_version": 2,
    "metadata_candidate": {"case_numbers": [], "citations": [], "dates": []}, "disposition": "NEW_DOCUMENT",
    "secondary_flags": [],
}


def test_pr76_inventory_row_adapts_conservatively():
    ident, adm, rels = adapters.from_pr76_inventory_row(SYNTH_ROW, collection="local:owner-collection",
                                                        corpus_generation_id="CG-20261127-pr76-adapter-00000000")
    for rec in (ident, adm, *rels):
        assert schema_errors(rec) == [], schema_errors(rec)
        assert record_issues(rec) == []
    assert ident["representation"]["representation_kind"] == "WORD_IMAGES_NOT_INVENTORIED"
    assert ident["source_copy"]["page_count"] is None  # a docx "page_count 1" is not a physical page count
    assert adm["decision"] == "HELD_EXTRACTION_INCOMPLETE" and adm["application_eligible"] is False
    provs = sorted(r["target"]["node_id"] for r in rels if r["category"] == "associated_with_provision")
    assert provs == ["PROV:AR-1954:r.22", "PROV:AR-1954:r.23", "PROV:AR-1954:r.30"]
    subj = [r for r in rels if r["category"] == "classified_under_subject"]
    assert [r["target"]["node_id"] for r in subj] == ["SUBJ:local:army-rules"]
    files = {"identities.jsonl": canonical.dumps_jsonl([ident]), "admissions.jsonl": canonical.dumps_jsonl([adm]),
             "relationships.jsonl": canonical.dumps_jsonl(rels)}
    assert exchange_issues(files) == []


def test_pr76_dispositions_all_map_and_never_publish():
    for disp in ("EXACT_DUPLICATE", "VERIFIED_ALTERNATE_COPY", "PROBABLE_DUPLICATE", "NEW_DOCUMENT", "IMPROVED_SOURCE_COPY",
                 "HISTORICAL_RECOVERY_MATCH", "IDENTITY_UNRESOLVED", "RELEVANCE_UNRESOLVED", "NON_RELEVANT",
                 "ACCESS_RESTRICTED", "INTEGRITY_FAILURE", "UNSUPPORTED_FORMAT"):
        row = dict(SYNTH_ROW, disposition=disp, detected_format="PDF", extension=".pdf", page_count=3,
                   extraction_method="pymupdf-native", relative_path="Subject/file.pdf", filename="file.pdf")
        ident, adm, _ = adapters.from_pr76_inventory_row(row, collection="local:owner-collection",
                                                         corpus_generation_id="CG-20261127-pr76-adapter-00000000",
                                                         primary_sha256="cd" * 32)
        assert schema_errors(ident) == [] and schema_errors(adm) == [], (disp, schema_errors(adm))
        assert adm["application_eligible"] is False and adm["publication_effect"] == "NONE"


def test_v7_record_adapts_to_anchored_candidates():
    text = "under Rule 22 of the Army Rules"
    rec = {"schema": "mimamsa-c14-document-candidate-v1", "doc_id": "aft-2019-example-v7", "original_sha256": "12" * 32,
           "derivative_sha256": "34" * 32, "page_count": 2, "decision_date_metadata": "2019-05-02",
           "provision_mentions": [{"page": 2, "start": 6, "end": 13, "text": text[6:13]}],
           "citation_mentions": [{"page": 1, "start": 0, "end": 5, "text": "under"}]}
    anchors, rels = adapters.from_v7_record(rec, corpus_generation_id="CG-20261127-v7-adapter-00000000")
    for rec_ in (*anchors, *rels):
        assert schema_errors(rec_) == [] and record_issues(rec_) == []
    assert {r["category"] for r in rels} == {"cites_provision", "refers_to_judgment"}
    assert all(not r["target"]["resolved"] and r["verification"] == "CANDIDATE" for r in rels)
    assert exchange_issues({"anchors.jsonl": canonical.dumps_jsonl(anchors), "relationships.jsonl": canonical.dumps_jsonl(rels)}) == []
