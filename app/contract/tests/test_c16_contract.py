"""Cycle 16 corpus integration contract (mimamsa-corpus-contract/2.0): schemas, fixtures, rules, adapters,
evidence byte checks and the activation reference model.

Runs in the existing CI contract job (app-ci.yml, `python -m pytest tests` in app/contract) with the pinned
jsonschema. Review findings C01-C07 of PR #77 each have positive and negative regression cases here and in
app/contract/fixtures/c16 (FIXTURES.json lists every fixture and the rule code it must raise).
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from mimamsa_contract.c16 import activation, adapters, canonical, evidence
from mimamsa_contract.c16.rules import (C15_INSTRUMENT_CODES, component_inventory_issues, exchange_issues, receipt_resolution_issues,
                                        record_issues)
from mimamsa_contract.c16.schemas import C16_DIR, KIND_TO_SCHEMA, SHARED, registry, schema, schema_errors

CONTRACT = Path(__file__).resolve().parents[1]
FIX = CONTRACT / "fixtures" / "c16"
EXCHANGE = FIX / "positive" / "exchange"
REPO = CONTRACT.parents[1]
GRAPH_MODEL = REPO / "app" / "b1" / "src" / "Mimamsa.Core" / "Graph" / "GraphModel.cs"
MANIFEST = json.loads((FIX / "FIXTURES.json").read_text(encoding="utf-8"))
GEN = "CG-20261127-tests-00000000"


def _codes(issues):
    return {i.code for i in issues}


def _load(rel):
    data = (FIX / rel).read_bytes()
    if rel.endswith(".jsonl"):
        return [json.loads(x) for x in data.decode("utf-8").splitlines() if x]
    return json.loads(data)


def _exchange_files():
    return {p.name: p.read_bytes() for p in sorted(EXCHANGE.iterdir())}


def _pop(stem):
    return [json.loads(x) for x in (EXCHANGE / f"{stem}.jsonl").read_text(encoding="utf-8").splitlines() if x]


def _ident(doc_id):
    return next(d for d in _pop("identities") if d["doc_id"] == doc_id)


# ---------------------------------------------------------------- schema self-consistency

def test_every_c16_schema_is_valid_draft_2020_12_with_local_id():
    names = sorted(p.name for p in C16_DIR.glob("*.json"))
    assert names == sorted([SHARED, *KIND_TO_SCHEMA.values()])
    for name in names:
        doc = json.loads((C16_DIR / name).read_text(encoding="utf-8"))
        assert doc["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        Draft202012Validator.check_schema(doc)
        assert doc["$id"] == f"https://contract.mimamsa.invalid/c16/{name}"
    registry()


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
        resolver = reg.resolver(f"https://contract.mimamsa.invalid/c16/{p.name}")
        for ref in _refs(json.loads(p.read_text(encoding="utf-8"))):
            resolver.lookup(ref)


def test_record_kinds_and_contract_const_agree():
    for kind, name in KIND_TO_SCHEMA.items():
        s = schema(name)
        assert s["properties"]["record_kind"] == {"const": kind}
        assert "contract" in s["required"] and "record_kind" in s["required"]
        assert s.get("additionalProperties") is False


def _cs_class(cls: str) -> str:
    text = GRAPH_MODEL.read_text(encoding="utf-8")
    return re.search(r"public static (?:partial )?class " + cls + r"\s*\{(.*?)\n\}", text, re.S).group(1)


def _cs_constants(cls: str) -> dict[str, str]:
    return dict(re.findall(r"(\w+)\s*=\s*\"([A-Z_]+)\"", _cs_class(cls)))


def test_verification_vocabulary_matches_c15_graph_model():
    shared = schema(SHARED)["$defs"]
    cs = _cs_constants("Verification")
    assert set(shared["graph_verification"]["enum"]) == set(cs.values())
    builder = re.search(r"BuilderValues\s*=\s*\{([^}]*)\}", GRAPH_MODEL.read_text(encoding="utf-8")).group(1)
    names = [x.strip() for x in builder.split(",")]
    assert set(shared["producer_verification"]["enum"]) == {cs[n] for n in names} == set(adapters.BUILDER_VERIFICATION)


def test_instrument_code_registry_matches_c15_code_list():
    codes = set(re.findall(r'\["[a-z0-9.-]+"\]\s*=\s*"([A-Z0-9-]+)"', _cs_class("GraphIds")))
    assert codes == set(C15_INSTRUMENT_CODES)


def test_edge_mapping_uses_c15_types_or_declared_proposals():
    c15 = set(_cs_constants("EdgeType").values())
    v1_relations = set(json.loads((CONTRACT / "schemas" / "v1" / "candidate.schema.json").read_text(encoding="utf-8"))
                       ["allOf"][2]["then"]["properties"]["payload"]["properties"]["relation"]["enum"])
    cats = set(schema("PROVISION_JUDGMENT_RELATIONSHIP_SCHEMA.json")["properties"]["category"]["enum"])
    assert set(adapters.CATEGORY_TO_EDGE) == cats - {"legally_validated"}
    for cat, etype in adapters.CATEGORY_TO_EDGE.items():
        assert etype in c15 or etype in adapters.PROPOSED_EDGE_TYPES, cat
    for etype in adapters.PROPOSED_EDGE_TYPES & {"INTERPRETS_PROVISION", "DISTINGUISHES_PROPOSITION"}:
        assert etype in v1_relations
    assert adapters.PROPOSED_EDGE_TYPES.isdisjoint(c15)


def test_v1_enumerations_are_supersets_where_c16_projects_into_v1():
    v1_doc = json.loads((CONTRACT / "schemas" / "v1" / "document.schema.json").read_text(encoding="utf-8"))
    v1_mimes = set(v1_doc["properties"]["source_copy"]["properties"]["mime_type"]["enum"])
    c16_mimes = set(schema("DOCUMENT_IDENTITY_SCHEMA.json")["properties"]["source_copy"]["properties"]["mime_type"]["enum"])
    assert v1_mimes <= c16_mimes
    assert c16_mimes - v1_mimes == {"application/msword", "application/rtf", "application/octet-stream"}


def test_admission_gate_enumeration_is_exactly_ten_unique_gates():
    s = schema("CORPUS_ADMISSION_SCHEMA.json")
    g = s["properties"]["gates"]
    required = {c["contains"]["properties"]["gate_id"]["const"] for c in g["allOf"]}
    assert required == set(s["$defs"]["gate_id"]["enum"]) and len(required) == 10
    assert g["minItems"] == g["maxItems"] == 10  # ten items each holding one of ten distinct ids => each exactly once


# ---------------------------------------------------------------- fixtures

def test_fixtures_are_byte_identical_to_builder_output():
    out = subprocess.run([sys.executable, "-I", str(FIX / "build_fixtures.py"), "--check"], capture_output=True, text=True)
    assert out.returncode == 0, out.stdout + out.stderr


@pytest.mark.parametrize("entry", MANIFEST["positive"], ids=lambda e: e["file"])
def test_positive_fixture_accepted(entry, register):
    if entry["kind"] == "exchange_dir":
        issues = exchange_issues(_exchange_files(), mode="strict", auth_ledger_version=entry["ledger"], register=register)
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
        issues = exchange_issues({"relationships.jsonl": (FIX / entry["file"]).read_bytes()}, mode="partial", register=register)
    elif entry["kind"] == "exchange_case":
        case = _load(entry["file"])
        issues = exchange_issues({k: v.encode("utf-8") for k, v in case["files"].items()}, mode=case["mode"],
                                 auth_ledger_version=case["ledger"], register=register)
    else:
        issues = record_issues(_load(entry["file"]), auth_ledger_version=entry["ledger"], register=register)
    assert entry["expect_code"] in _codes(issues), [str(i) for i in issues]
    if entry["schema_path_contains"]:
        assert any(entry["schema_path_contains"] in i.message for i in issues if i.code == "SCHEMA"), [str(i) for i in issues]


def test_required_fixture_coverage():
    files = {e["file"] for e in MANIFEST["positive"] + MANIFEST["negative"]}
    for must in ("positive/relationships_ar_22_23_30.jsonl", "positive/identity_word_screenshots.json",
                 "positive/identity_reconstructed_pdf.json", "positive/identity_extract_pdf.json",
                 "positive/identity_compilation_pdf.json", "positive/exchange",
                 "negative/N01_folder_classification_as_verified_finding.json",
                 "negative/N02_reconstructed_pdf_claims_original.json", "negative/N03_extract_claims_complete.json",
                 "negative/N04_missing_mandatory_sha256.json"):
        assert must in files
    kinds = {d["representation"]["representation_kind"] for d in _pop("identities")}
    assert {"NATIVE_DIGITAL_PDF", "SCANNED_PDF", "MIXED_PDF", "WORD_NATIVE_TEXT", "WORD_WITH_EMBEDDED_IMAGES",
            "RECONSTRUCTED_SEARCHABLE_PDF", "WORD_IMAGES_NOT_INVENTORIED"} <= kinds
    assert {a["locator"]["kind"] for a in _pop("anchors")} == {"SOURCE_PHYSICAL_PAGE", "RECONSTRUCTED_PAGE", "GENERATED_SEGMENT", "IMAGE_SEQUENCE"}
    codes = {e.get("expect_code") for e in MANIFEST["negative"]}
    for c in ("C16_ADMISSION_ORPHAN", "C16_ADMISSION_MISSING", "C16_GENERATION_MISMATCH", "C16_ADMISSION_FORK",
              "C16_GATE_EVIDENCE", "C16_ELIGIBLE_IDENTITY_NOT_READY", "C16_ANCHOR_PAGE_RANGE", "C16_ANCHOR_IMAGE",
              "C16_ANCHOR_DERIVATIVE", "C16_ANCHOR_MAPPING", "C16_SUBJECT_NODE_MISMATCH", "C16_COMPILATION_MEMBER",
              "C16_REVIEW_UNRESOLVED", "C16_REVIEW_BINDING", "C16_REVIEW_NOT_INDEPENDENT", "C16_TARGET_UNREGISTERED",
              "C16_RESTRICTED_IN_EXCHANGE", "C16_FINDING_ON_WEAK_ANCHOR", "C16_MANIFEST_MISMATCH", "C16_FILE_MISSING",
              "C16_DUPLICATE_KEY", "JSONL_NOT_OBJECT", "C16_FILE_NAME", "C16_KIND_MISMATCH", "KR_ACCOUNTING",
              "KR_FULL_CAPABILITY_CLAIM", "KR_PATH_OVERLAP", "KR_NAMESPACE"):
        assert c in codes, c


def test_ar_22_23_30_keeps_one_association_per_provision_and_per_path():
    rels = _load("positive/relationships_ar_22_23_30.jsonl")
    prov = [r for r in rels if r["category"] == "associated_with_provision"]
    by_path = {}
    for r in prov:
        by_path.setdefault(r["classification_provenance"]["relative_path"], set()).add(r["target"]["node_id"])
    assert sorted(by_path.values(), key=len) == [{"PROV:AR-1954:r.22"},
                                                 {"PROV:AR-1954:r.22", "PROV:AR-1954:r.23", "PROV:AR-1954:r.30"}]
    assert len({r["relationship_id"] for r in rels}) == len(rels)
    assert all(r["verification"] == "CANDIDATE" and not r["is_finding"] for r in prov)


def test_classification_can_never_be_reviewed_or_a_finding():
    base = next(r for r in _pop("relationships") if r["evidentiary_basis"] == "FOLDER_PATH")
    for patch in ({"verification": "DOCUMENTARY_CHECKED", "review_ref": "RV-FIXTURE-0009"}, {"verification": "LEGAL_REVIEWED"},
                  {"is_finding": True}, {"evidentiary_basis": "DOCUMENT_TEXT_REVIEWED"}):
        assert schema_errors(dict(copy.deepcopy(base), **patch))


# ---------------------------------------------------------------- C05 exchange robustness and validation levels

def test_strict_requires_manifest_but_partial_does_not():
    files = _exchange_files()
    files.pop("GENERATION.json")
    assert "C16_MANIFEST" in _codes(exchange_issues(files, mode="strict"))
    assert exchange_issues(files, mode="partial") == []
    with pytest.raises(ValueError):
        exchange_issues(files, mode="lenient")


def test_non_object_and_null_records_are_structured_rejections():
    assert _codes(record_issues(None)) == {"JSONL_NOT_OBJECT"}
    assert _codes(record_issues([1, 2])) == {"JSONL_NOT_OBJECT"}
    issues = exchange_issues({"taxonomy.jsonl": b"null\n{}\n"}, mode="partial")
    assert {"JSONL_NOT_OBJECT", "C16_KIND_MISMATCH"} <= _codes(issues)


def test_partial_validation_still_resolves_references_among_present_populations():
    files = {k: v for k, v in _exchange_files().items() if k in ("relationships.jsonl", "taxonomy.jsonl")}
    assert "DANGLING_ANCHOR" not in _codes(exchange_issues(files, mode="partial"))  # anchors population absent: not checked
    files["anchors.jsonl"] = canonical.dumps_jsonl(_pop("anchors")[:1])
    assert "DANGLING_ANCHOR" in _codes(exchange_issues(files, mode="partial"))


def test_taxonomy_cycle_detected():
    tax = _pop("taxonomy")
    for t in tax:
        if t["node_id"] == "SUBJ:court_martial":
            t["parent_ids"] = ["SUBJ:local:court-martial"]
        if t["node_id"] == "SUBJ:local:court-martial":
            t["parent_ids"] = ["SUBJ:court_martial"]
    assert "C16_TAXONOMY_CYCLE" in _codes(exchange_issues({"taxonomy.jsonl": canonical.dumps_jsonl(tax)}, mode="partial"))


def test_restricted_register_applies_to_c16_records(register):
    assert register.sha256s
    x = _load("positive/identity_extract_pdf.json")
    x["source_copy"]["sha256"] = sorted(register.sha256s)[0]
    x["source_copy"]["vault_path"] = f"vault/sha256/{x['source_copy']['sha256'][:2]}/{x['source_copy']['sha256']}"
    assert "RESTRICTED_MATERIAL" in _codes(record_issues(x, register=register))


# ---------------------------------------------------------------- canonical form and ids

def test_canonical_bytes_rules():
    assert canonical.canonical_bytes({"b": 1, "a": [1.5, 12.0, "x"]}) == b'{"a":[1.5,12,"x"],"b":1}'
    for bad in ({"x": float("nan")}, {"x": -0.0}, {"x": 0.12345}, {"x": "é"}, {"x": 2**60}):
        with pytest.raises(canonical.CanonicalError):
            canonical.canonical_bytes(bad)


def test_ids_are_stable_under_non_identity_changes_and_admission_ids_track_decisions():
    r = _pop("relationships")[0]
    x = copy.deepcopy(r)
    x["uncertainty"] = "reworded"
    x["source"]["rule_version"] = "9.9"
    assert canonical.relationship_id(x) == r["relationship_id"]
    a = _pop("admissions")[0]
    y = copy.deepcopy(a)
    y["decision"] = "HELD_IDENTITY_UNRESOLVED"
    assert canonical.admission_id(y) != a["admission_id"]  # a changed decision is a new revision, never an overwrite


# ---------------------------------------------------------------- C02 evidence bytes and projections

def _derived(pages: dict[int, str]) -> bytes:
    return "".join(f"[[page {n}]]\n{t}\n" for n, t in sorted(pages.items())).encode("utf-8")


def _byte_anchor(text_bytes, page, start, end, body):
    return {"locator": {"kind": "SOURCE_PHYSICAL_PAGE", "physical_page": page},
            "derivative_text_sha256": hashlib.sha256(text_bytes).hexdigest(),
            "text_span": {"char_start": start, "char_end": end, "text_sha256": hashlib.sha256(body[start:end].encode()).hexdigest()}}


def test_span_is_checked_against_derivative_bytes():
    pages = {1: "Cover page", 2: "Rule 22 was not complied with — synthetic"}
    data = _derived(pages)
    a = _byte_anchor(data, 2, 0, 7, pages[2])
    assert evidence.verify_anchor_bytes(a, data) == []
    assert evidence.verify_anchor_bytes(a, data + b"x") == ["C16_DERIVATIVE_BYTES_MISMATCH"]
    b = copy.deepcopy(a)
    b["text_span"]["char_end"] = 500
    assert evidence.verify_anchor_bytes(b, data) == ["C16_SPAN_OUT_OF_RANGE"]
    c = copy.deepcopy(a)
    c["locator"]["physical_page"] = 9
    assert evidence.verify_anchor_bytes(c, data) == ["C16_SPAN_UNIT_MISSING"]
    d = copy.deepcopy(a)
    d["text_span"]["text_sha256"] = "0" * 64
    assert evidence.verify_anchor_bytes(d, data) == ["C16_SPAN_MISMATCH"]


def test_unbound_or_unverified_anchors_never_cite_a_span():
    anchors = {a["anchor_id"]: a for a in _pop("anchors")}
    official = _ident("sc-2019-example-v-union-of-india-ca0001")
    native = next(a for a in anchors.values() if a["doc_id"] == official["doc_id"] and a["locator"]["physical_page"] == 3)
    assert adapters.anchor_to_v1_page_anchor(native) is None                      # no bound identity
    page_only = adapters.anchor_to_v1_page_anchor(native, official)
    assert page_only == {"source_copy_sha256": official["source_copy"]["sha256"], "page": 3, "paragraph_label": "12"}
    full = adapters.anchor_to_v1_page_anchor(native, official, span_verified=True)
    assert full["derivative_text_sha256"] == native["derivative_text_sha256"] and "quote" not in full  # producer quote never copied
    incorrect = dict(copy.deepcopy(native), verification={"state": "INCORRECT", "review_ref": "RV-X-001"})
    assert adapters.anchor_to_v1_page_anchor(incorrect, official) is None
    for a in anchors.values():
        if a["locator"]["kind"] in ("GENERATED_SEGMENT", "IMAGE_SEQUENCE"):
            ident = _ident(a["doc_id"])
            assert adapters.anchor_to_v1_page_anchor(a, ident, span_verified=True) is None
        if a["locator"]["kind"] == "RECONSTRUCTED_PAGE":
            out = adapters.anchor_to_v1_page_anchor(a, _ident(a["doc_id"]), span_verified=True)
            assert out["source_copy_sha256"] == a["original_sha256"] and "derivative_text_sha256" not in out


def test_graph_projection_shows_a_page_only_for_consumer_verified_anchors():
    anchors = {a["anchor_id"]: a for a in _pop("anchors")}
    r = next(x for x in _pop("relationships") if x["category"] == "refers_to_judgment")
    assert adapters.graph_projection(r, anchors)["edge"]["page"] is None
    assert adapters.graph_projection(r, anchors, usable=set(r["anchors"]))["edge"]["page"] == 7


def test_reviewed_relationship_projects_as_builder_edge_plus_review_overlay():
    r = next(x for x in _pop("relationships") if x["verification"] == "DOCUMENTARY_CHECKED")
    p = adapters.graph_projection(r)
    assert p["edge"]["verification"] == "CANDIDATE"
    assert p["review"] == {"edge_id": p["edge"]["id"], "review_state": "DOCUMENTARY_CHECKED", "review_ref": r["review_ref"]}


def test_c16_edge_ids_distinguish_same_endpoints_from_different_paths():
    rels = [r for r in _load("positive/relationships_ar_22_23_30.jsonl")
            if r["category"] == "associated_with_provision" and r["target"].get("node_id") == "PROV:AR-1954:r.22"]
    assert len(rels) == 2 and len({adapters.graph_projection(r)["edge"]["id"] for r in rels}) == 2


# ---------------------------------------------------------------- v1 adapters

def _v1_example(name):
    return json.loads((CONTRACT / "examples" / f"{name}.example.json").read_text(encoding="utf-8"))


def test_v1_document_adapts_to_valid_identity_keeping_ids():
    doc, der = _v1_example("document"), _v1_example("derived_text")
    ident = adapters.identity_from_v1_document(doc, [der], corpus_generation_id=GEN)
    assert schema_errors(ident) == [] and record_issues(ident) == []
    assert ident["doc_id"] == doc["doc_id"] and ident["source_copy"]["sha256"] == doc["source_copy"]["sha256"]
    assert ident["research_eligibility"]["whole_work_claims_permitted"] is False


def test_v1_page_anchor_round_trip_and_v1_schema():
    v = Draft202012Validator({"$ref": "https://contract.mimamsa.invalid/v1/common.schema.json#/$defs/page_anchor"}, registry=registry())
    cand = _v1_example("candidate_graph_edge")
    for pa in cand["anchors"]:
        a = adapters.anchor_from_v1_page_anchor(pa, doc_id=cand["source_doc_id"])
        assert schema_errors(a) == [] and record_issues(a) == []
        ident = copy.deepcopy(_ident("sc-2019-example-v-union-of-india-ca0001"))
        ident["doc_id"], ident["source_copy"]["sha256"] = cand["source_doc_id"], pa["source_copy_sha256"]
        back = adapters.anchor_to_v1_page_anchor(a, ident, span_verified=True)
        assert list(v.iter_errors(back)) == []
        assert (back["source_copy_sha256"], back["page"]) == (pa["source_copy_sha256"], pa["page"])


def test_v1_graph_edge_candidate_adapts_and_projects_to_c15():
    cand = _v1_example("candidate_graph_edge")
    anchors = [adapters.anchor_from_v1_page_anchor(pa, doc_id=cand["source_doc_id"]) for pa in cand["anchors"]]
    rel = adapters.relationship_from_v1_candidate(cand, subject_sha256=cand["anchors"][0]["source_copy_sha256"],
                                                  subject_node=f"JUD:{cand['source_doc_id']}", source_date="2020-01-01", anchors=anchors)
    assert rel is not None and schema_errors(rel) == [] and record_issues(rel) == []
    proj = adapters.graph_projection(rel)["edge"]
    assert proj["verification"] in adapters.BUILDER_VERIFICATION and proj["review_state"] == "UNREVIEWED"


# ---------------------------------------------------------------- C06 PR #76 adapters (revised inventory, v3)

def _row(path, sha, **kw):
    base = {"inventory_id": "L-" + hashlib.sha256(path.encode()).hexdigest()[:20], "relative_path": path,
            "filename": path.split("/")[-1], "extension": ".docx", "detected_format": "DOCX", "size_bytes": 54321, "sha256": sha,
            "page_count": 1, "text_available": True, "derivative_sha256": None, "extraction_method": "docx-xml+embedded-image-inventory",
            "derivative_withheld_reason": "ACCESS_MARKING_SCREENING_INCOMPLETE", "parsing_error": None,
            "candidate_document_type": "judgment", "ocr_required_pages": [], "ocr_required_images": [1, 2],
            "relevance": True, "restricted": False, "classification_version": 3, "extraction_methodology_version": 3,
            "embedded_images": [{"sequence": n, "occurrence_id": f"body:rId{n}:{n}", "relationship_id": f"rId{n}",
                                 "archive_path": f"word/media/image{n}.png", "image_sha256": hashlib.sha256(f"img{n}".encode()).hexdigest(),
                                 "size_bytes": 1000, "width": 800, "height": 600, "format": "PNG", "ocr_state": "REQUIRED"} for n in (1, 2)],
            "metadata_candidate": {"case_numbers": []}, "disposition": "NEW_DOCUMENT", "secondary_flags": []}
    base.update(kw)
    return base


def _pr76(rows):
    return adapters.from_pr76_inventory(rows, collection="local:owner-collection", corpus_generation_id=GEN)


def _partial_ok(out):
    files = {f"{k}.jsonl": canonical.dumps_jsonl(v) for k, v in out.items() if k != "receipts" and v}
    return exchange_issues(files, mode="partial")


def test_pr76_v3_row_maps_images_and_holds_conservatively():
    out = _pr76([_row("Army Rules/AR 22, 23, 30 - Lt Col A B Example v Union of India.docx", "ab" * 32)])
    (ident,), (adm,) = out["identities"], out["admissions"]
    assert ident["representation"]["representation_kind"] == "WORD_WITH_EMBEDDED_IMAGES"
    assert [i["location"]["occurrence_ref"] for i in ident["embedded_images"]] == ["body:rId1:1", "body:rId2:2"]
    assert ident["source_copy"]["page_count"] is None and ident["text_derivatives"] == []   # derivative withheld
    gates = {g["gate_id"]: g["result"] for g in adm["gates"]}
    assert gates["G01_HASH_VERIFIED"] == "NOT_RUN" and gates["G09_DUPLICATE_RESOLVED"] == "NOT_RUN"
    assert adm["decision"] == "HELD_ACCESS_MARKING_REVIEW" and adm["application_eligible"] is False
    provs = sorted(r["target"]["node_id"] for r in out["relationships"] if r["category"] == "associated_with_provision")
    assert provs == ["PROV:AR-1954:r.22", "PROV:AR-1954:r.23", "PROV:AR-1954:r.30"]
    assert _partial_ok(out) == []
    strict = {f"{k}.jsonl": canonical.dumps_jsonl(v) for k, v in out.items() if k != "receipts" and v}
    assert "C16_MANIFEST" in _codes(exchange_issues(strict, mode="strict"))    # adapter output is never importable as is


def test_pr76_unknown_format_is_never_a_pdf():
    out = _pr76([_row("Misc/scan.xyz", "cd" * 32, detected_format="XYZ", extension=".xyz", embedded_images=[],
                      derivative_sha256=None)])
    ident, adm = out["identities"][0], out["admissions"][0]
    assert ident["source_copy"]["detected_format"] == "UNKNOWN" and ident["source_copy"]["mime_type"] == "application/octet-stream"
    assert ident["representation"]["representation_kind"] == "UNRECOGNISED_FORMAT" and adm["decision"] == "UNSUPPORTED_FORMAT"
    assert _partial_ok(out) == []


def test_pr76_restricted_rows_leave_only_a_local_receipt():
    out = _pr76([_row("Secret/AR 22 - X v Y.docx", "ef" * 32, disposition="ACCESS_RESTRICTED", restricted=True)])
    assert out["identities"] == [] and out["admissions"] == [] and out["relationships"] == [] and out["taxonomy"] == []
    (r,) = out["receipts"]
    assert r == {"record_kind": "local_exclusion_receipt", "sha256_prefix": "ef" * 6, "reason": "ACCESS_MARKING_DETECTED", "exportable": False}
    assert "Secret" not in json.dumps(r)


def test_pr76_same_binary_merges_observations_not_classifications():
    sha = "12" * 32
    out = _pr76([_row("A/Rules/AR 22 - X v Y.docx", sha), _row("B/Rules/AR 30 - X v Y.docx", sha)])
    assert len(out["identities"]) == 1 and len(out["identities"][0]["provenance"]["observations"]) == 2
    subj = sorted(r["target"]["node_id"] for r in out["relationships"] if r["category"] == "classified_under_subject")
    assert subj == ["SUBJ:local:a__rules", "SUBJ:local:b__rules"]                 # same leaf, different parents
    provs = sorted(r["target"]["node_id"] for r in out["relationships"] if r["category"] == "associated_with_provision")
    assert provs == ["PROV:AR-1954:r.22", "PROV:AR-1954:r.30"]
    parents = {t["node_id"]: t["parent_ids"] for t in out["taxonomy"]}
    assert parents["SUBJ:local:a__rules"] == ["SUBJ:local:a"] and parents["SUBJ:local:a"] == []
    assert _partial_ok(out) == []


def test_pr76_provision_folders_ranges_and_ambiguous_abbreviations_stay_signals():
    out = _pr76([_row("AR 22/judgment one.docx", "21" * 32),
                 _row("Misc/AR 22-25 - X v Y.docx", "22" * 32),
                 _row("Misc/AFT 14 - X v Y.docx", "23" * 32),
                 _row("Misc/OA 123 of 2019 - X v Y.docx", "24" * 32)])
    by_sha = {}
    for r in out["relationships"]:
        if r["category"] == "associated_with_provision":
            by_sha.setdefault(r["subject"]["source_copy_sha256"], []).append(r)
    folder = by_sha["21" * 32][0]
    assert folder["evidentiary_basis"] == "FOLDER_PATH" and folder["target"]["node_id"] == "PROV:AR-1954:r.22"
    rng = by_sha["22" * 32][0]
    assert not rng["target"]["resolved"] and rng["target"]["unresolved"]["note"] == "PROVISION_RANGE_NOT_EXPANDED"
    assert "23" * 32 not in by_sha                                                    # bare AFT is the forum: no provision
    assert "24" * 32 not in by_sha                                                    # a case-number prefix is not a provision
    assert all(r["verification"] == "CANDIDATE" and not r["is_finding"] for rs in by_sha.values() for r in rs)
    assert _partial_ok(out) == []


def test_pr76_v2_docx_without_inventory_is_held():
    out = _pr76([_row("Misc/old.docx", "31" * 32, extraction_methodology_version=None, classification_version=2,
                      embedded_images=None, derivative_withheld_reason=None, derivative_sha256="41" * 32, extraction_method="docx-xml")])
    ident, adm = out["identities"][0], out["admissions"][0]
    assert ident["representation"]["representation_kind"] == "WORD_IMAGES_NOT_INVENTORIED"
    assert adm["decision"] == "HELD_OCR_REQUIRED" or adm["decision"] == "HELD_EXTRACTION_INCOMPLETE"
    assert _partial_ok(out) == []


def test_v7_record_adapts_to_anchored_candidates():
    text = "under Rule 22 of the Army Rules"
    rec = {"schema": "mimamsa-c14-document-candidate-v1", "doc_id": "aft-2019-example-v7", "original_sha256": "12" * 32,
           "derivative_sha256": "34" * 32, "page_count": 2, "decision_date_metadata": "2019-05-02",
           "provision_mentions": [{"page": 2, "start": 6, "end": 13, "text": text[6:13]}],
           "citation_mentions": [{"page": 1, "start": 0, "end": 5, "text": "under"}]}
    anchors, rels = adapters.from_v7_record(rec, corpus_generation_id=GEN)
    for r in (*anchors, *rels):
        assert schema_errors(r) == [] and record_issues(r) == []
    assert exchange_issues({"anchors.jsonl": canonical.dumps_jsonl(anchors), "relationships.jsonl": canonical.dumps_jsonl(rels)},
                           mode="partial") == []


# ---------------------------------------------------------------- C07 release manifests

def test_component_inventory_must_match_signed_sums():
    m = _load("positive/knowledge_release_full.json")
    sums = {f["path"]: f["sha256"] for c in m["components"] for f in c["files"]}
    assert component_inventory_issues(m, sums) == []
    sums[m["components"][0]["files"][0]["path"]] = "0" * 64
    assert "KR_INVENTORY" in _codes(component_inventory_issues(m, sums))


def test_full_and_degraded_releases_are_distinct():
    full = _load("positive/knowledge_release_full.json")
    deg = _load("positive/knowledge_release_degraded_lexical_only.json")
    assert full["capability"]["declared_service_level"] == "FULL"
    assert deg["capability"]["declared_service_level"] == "DEGRADED_LEXICAL_ONLY"
    assert any(a["status"] == "OMITTED_DEGRADED" for a in deg["capability"]["accounting"])
    ts = next(c for c in full["components"] if c["kind"] == "TEXT_STORE")
    assert ts["format"] == "mimamsa-text-store/1" and ts["binding"] == "BIND_EXACT_TO_GENERATION_RECORDS" and ts["disk_budget_bytes"]


def test_rule_pack_refused_at_ledger_v0():
    m = _load("positive/intelligence_release_model_change.json")
    acct = next(a for a in m["capability"]["accounting"] if a["kind"] == "RULE_PACK")
    acct["status"] = "SHIPPED"
    m["components"].append({"component_id": "rules", "kind": "RULE_PACK", "format": "rule-pack-1", "authority": "AUTHORITATIVE",
                            "transport": "FULL", "files": [{"path": "rule-packs/p.json", "sha256": "a" * 64, "bytes": 1}],
                            "result_digest": "b" * 64, "result_count": 1, "verify": ["SHA256_EACH_FILE"], "fallback": None})
    assert "KR_RULE_PACK_LEDGER_V0" in _codes(record_issues(m, auth_ledger_version=0))


# ---------------------------------------------------------------- C03 activation reference model

def _site(**kw):
    return activation.Site(installed=["R1", "R2", "R3"], active="R1",
                           staged_models={"M2": {"verified": True, "vectors_for": {"R1", "R2", "R3"}}}, **kw)


@pytest.mark.parametrize("crash_at", activation.STEPS)
def test_crash_at_every_boundary_recovers_to_one_consistent_generation(crash_at):
    s = _site()
    with pytest.raises(activation.Crash):
        s.transition("KNOWLEDGE", "R2", crash_after=crash_at)
    with pytest.raises(activation.Refused):
        s.pin()                                                    # nothing is served until recovery completes
    s.recover()
    expect = "R1" if crash_at == "BEGIN" else "R2"                 # DECIDED is the one commit decision
    assert s.pointers["KNOWLEDGE"] == s.db["views"] == expect
    decided = [j["txn"] for j in s.journal if j["step"] == "DECIDED"]
    assert len(s.log) == len(decided) and len(s.db["publication"]) == len(decided)
    s.recover()                                                    # idempotent
    assert len(s.log) == len(decided) and len(s.db["publication"]) == len(decided)
    p = s.pin()
    assert p["knowledge"] == expect and p["exclusion_seq"] == s.exclusions["seq"] and p["models"] == "M1"
    assert s.temp == set()                                         # scratch state cleaned on every crash path
    assert s.db["site_rows"] == {"users": 1}                       # site data untouched


def test_exclusion_arriving_mid_switch_is_applied_before_exposure():
    s = _site()
    s.transition("KNOWLEDGE", "R2", hook=lambda step: s.accept_exclusion({"doc-x"}) if step == "LOGGED" else None)
    p = s.pin()
    assert p["knowledge"] == "R2" and p["exclusion_seq"] == 1 and s.applied["R2"] == 1


def test_readers_are_pinned_and_retention_never_removes_pinned_or_rollback_targets():
    s = activation.Site(installed=["R1", "R2", "R3", "R4"], active="R1", keep_previous=1)
    g = s.pin()
    for to in ("R2", "R3", "R4"):
        s.transition("KNOWLEDGE", to)
    assert s.pointers["KNOWLEDGE"] == "R4"
    removed = s.prune()
    assert "R1" not in removed and "R3" not in removed and removed == ["R2"]  # R1 pinned, R3 rollback target
    s.unpin(g)
    assert s.prune() == ["R1"]


def test_rollback_and_model_switch_use_the_same_journal():
    s = _site()
    s.transition("KNOWLEDGE", "R2")
    s.accept_exclusion({"doc-a"})
    s.transition("KNOWLEDGE", "R1", action="ROLLBACK")
    assert s.pointers["KNOWLEDGE"] == "R1" and s.applied["R1"] == 1   # rollback cannot resurrect excluded items
    with pytest.raises(activation.Crash):
        s.transition("MODELS", "M2", crash_after="DB_APPLIED")
    s.recover()
    assert s.pointers["MODELS"] == "M2" and s.pointers["KNOWLEDGE"] == "R1"


def test_restore_keeps_journal_head_and_latest_exclusions():
    s = _site()
    backup = s.backup()                                            # taken while R1 was active
    s.transition("KNOWLEDGE", "R2")
    s.accept_exclusion({"doc-b"})
    s.restore(backup)
    assert s.pointers["KNOWLEDGE"] == s.db["views"] == "R2"         # no stale rollback to the backup's generation
    assert s.applied["R2"] == s.exclusions["seq"] == 1
    assert any(p["release"] == "R2" for p in s.db["publication"].values())


def test_transition_refused_while_recovering_and_to_unstaged_generation():
    s = _site()
    with pytest.raises(activation.Refused):
        s.transition("KNOWLEDGE", "R9")
    with pytest.raises(activation.Crash):
        s.transition("KNOWLEDGE", "R2", crash_after="POINTER_WRITTEN")
    with pytest.raises(activation.Refused):
        s.transition("KNOWLEDGE", "R3")


# ---------------------------------------------------------------- residual corrections (review 6089492803)

def test_quote_is_bound_to_the_verified_span_and_every_quotation_gate():
    official = _ident("sc-2019-example-v-union-of-india-ca0001")
    der = official["text_derivatives"][0]
    pages = {1: "Cover", 2: "Section 69 of the Army Act applies here (synthetic)."}
    data = _derived(pages)
    native = copy.deepcopy(next(a for a in _pop("anchors") if a["doc_id"] == official["doc_id"] and a["locator"]["physical_page"] == 3))
    official = copy.deepcopy(official)
    official["text_derivatives"][0]["derivative_text_sha256"] = hashlib.sha256(data).hexdigest()
    native.update(derivative_text_sha256=hashlib.sha256(data).hexdigest(), quote="Section 69")
    native["locator"]["physical_page"] = 2
    native["text_span"] = {"passage_id": None, "char_start": 0, "char_end": 10,
                           "text_sha256": hashlib.sha256(pages[2][:10].encode()).hexdigest()}
    assert evidence.verify_anchor_bytes(native, data) == []
    q = evidence.verified_quote(native, official, data)
    assert q == "Section 69"
    assert adapters.anchor_to_v1_page_anchor(native, official, span_verified=True, quote=q)["quote"] == "Section 69"
    wrong = dict(native, quote="Section 96")                                   # valid span, different quote
    assert evidence.verify_anchor_bytes(wrong, data) == ["C16_QUOTE_MISMATCH"] and evidence.verified_quote(wrong, official, data) is None
    denied = copy.deepcopy(official)
    denied["research_eligibility"]["quoting_permitted"] = False               # the identity denies quotation
    assert evidence.verified_quote(native, denied, data) is None
    assert "quote" not in adapters.anchor_to_v1_page_anchor(native, denied, span_verified=True, quote=q)
    no_der = copy.deepcopy(official)
    no_der["text_derivatives"][0]["quoting_permitted"] = False                # the derivative denies quotation
    assert evidence.verified_quote(native, no_der, data) is None
    assert evidence.verified_quote(native, official, data, page_quotable=False) is None   # the page denies quotation
    assert "quote" not in adapters.anchor_to_v1_page_anchor(native, official, span_verified=True, quote="Section 96")


def test_receipts_resolve_only_against_bundled_artefacts_future_gate():
    adm = next(a for a in _pop("admissions") if a["application_eligible"])
    assert adm["service_scope"] == "SEARCHABLE"
    arte = {g["receipt"]["receipt_sha256"]: b"x" for g in adm["gates"] if g.get("receipt")}
    assert "C16_RECEIPT_UNRESOLVED" in _codes(receipt_resolution_issues(adm, arte))  # wrong bytes
    assert "C16_RECEIPT_UNRESOLVED" in _codes(receipt_resolution_issues(adm, {}))    # missing artefacts


def test_pr76_owner_decisions_ar_and_aft():
    out = _pr76([_row("Misc/AFT Act 14 - X v Y.docx", "51" * 32), _row("Misc/AFT 14 - X v Y.docx", "52" * 32),
                 _row("Misc/s. 15 of the AFT Act - X v Y.docx", "53" * 32), _row("Misc/AR 7 - X v Y.docx", "54" * 32)])
    provs = {r["subject"]["source_copy_sha256"][:2]: r for r in out["relationships"] if r["category"] == "associated_with_provision"}
    assert provs["51"]["target"]["node_id"] == "PROV:AFT-2007:s.14" and provs["53"]["target"]["node_id"] == "PROV:AFT-2007:s.15"
    assert "52" not in provs                                                      # AFT alone is the forum
    assert provs["54"]["target"]["node_id"] == "PROV:AR-1954:r.7" and provs["54"]["verification"] == "CANDIDATE"
    assert all(not r["is_finding"] for r in provs.values())


def test_model_transition_requires_verified_staged_model_with_vectors():
    s = activation.Site(installed=["R1", "R2"], active="R1",
                        staged_models={"M2": {"verified": False, "vectors_for": {"R1"}}, "M3": {"verified": True, "vectors_for": {"R2"}}})
    with pytest.raises(activation.Refused):
        s.transition("MODELS", "M9")                                             # not staged
    with pytest.raises(activation.Refused):
        s.transition("MODELS", "M2")                                             # not verified
    with pytest.raises(activation.Refused):
        s.transition("MODELS", "M3")                                             # no vectors for the active knowledge generation


def test_reader_pinned_before_an_exclusion_never_bypasses_it():
    s = _site()
    p = s.pin()
    s.accept_exclusion({"doc-x"})
    assert s.respond(p, ["doc-x", "doc-y"]) == ["doc-y"]
    s.unpin(p)


def test_retention_selects_distinct_previous_releases_and_protects_the_recovery_target():
    s = activation.Site(installed=["R0", "R1", "R2", "R3", "R4"], active="R1", recovery_target="R0",
                        staged_models={"M1": {"verified": True, "vectors_for": {"R0", "R1", "R2", "R3", "R4"}}})
    for to in ("R2", "R1", "R2", "R3"):
        s.transition("KNOWLEDGE", to, action="ROLLBACK" if to in ("R1", "R2") else "ACTIVATE")
    assert s.previous_distinct() == ["R2", "R1"]                                  # history R1,R2,R1,R2,R3: distinct
    assert s.prune() == ["R4"] and set(s.installed) == {"R0", "R1", "R2", "R3"}  # R0 is the explicit recovery target


def test_measured_disk_preflight_refuses_activation():
    s = _site(sizes={"R1": 40, "R2": 60, "R3": 50}, free_bytes=10)
    pf = s.preflight("KNOWLEDGE", "R2")
    assert pf["result"] == "FAIL" and pf["measured_required_bytes"] == int(60 * 1.1) and "R1" in pf["retained_releases"]
    with pytest.raises(activation.Refused):
        s.transition("KNOWLEDGE", "R2")
    assert s.pointers["KNOWLEDGE"] == "R1" and s.journal == []
    ok = _site(sizes={"R1": 40, "R2": 60}, free_bytes=100)
    ok.transition("KNOWLEDGE", "R2")
    assert ok.pointers["KNOWLEDGE"] == "R2"


# ---------------------------------------------------------------- C02-R2 (final re-review): shared OCR of identical images

def _shared_image_exchange(fourth_state="DONE", fourth_image=None):
    """The Word fixture with a 4th occurrence of the SAME image as occurrence 2 (PR #76 dedup: one verified OCR
    derivative shared by identical images) and a distinct anchor on that 4th occurrence."""
    idents, anchors = _pop("identities"), _pop("anchors")
    w = next(d for d in idents if d["representation"]["representation_kind"] == "WORD_WITH_EMBEDDED_IMAGES")
    sha = w["source_copy"]["sha256"]
    img2 = next(i for i in w["embedded_images"] if i["sequence"] == 2)
    img4 = copy.deepcopy(img2)
    img4.update(sequence=4, image_sequence_id=f"IMG:{sha}:4", ocr_state=fourth_state,
                image_sha256=fourth_image or img2["image_sha256"])
    img4["location"].update(body_order=4, container_part="word/media/image2.png")
    w["embedded_images"].append(img4)
    cov = w["text_derivatives"][0]["coverage"]
    cov["images_total"] = 4
    cov["images_text_extracted"] = sum(1 for i in w["embedded_images"] if i["ocr_state"] == "DONE")
    a2 = next(a for a in anchors if a["locator"]["kind"] == "IMAGE_SEQUENCE")
    a4 = copy.deepcopy(a2)
    a4["locator"]["image_sequence_id"] = img4["image_sequence_id"]
    a4["anchor_id"] = canonical.anchor_id(a4)
    anchors.append(a4)
    files = {"identities.jsonl": canonical.dumps_jsonl(idents), "anchors.jsonl": canonical.dumps_jsonl(anchors)}
    return files, a2, a4


def test_identical_images_sharing_one_ocr_derivative_are_each_accepted():
    files, a2, a4 = _shared_image_exchange()
    assert a2["derivative_text_sha256"] == a4["derivative_text_sha256"]
    assert a2["locator"]["image_sequence_id"] != a4["locator"]["image_sequence_id"] and a2["anchor_id"] != a4["anchor_id"]
    issues = exchange_issues(files, mode="partial")
    assert [str(i) for i in issues] == []


def test_occurrence_whose_own_ocr_is_not_done_is_rejected_even_if_a_twin_is_done():
    files, _, a4 = _shared_image_exchange(fourth_state="QUEUED")
    issues = [i for i in exchange_issues(files, mode="partial") if i.where == a4["anchor_id"]]
    assert "C16_ANCHOR_IMAGE" in _codes(issues)


def test_different_image_with_anothers_ocr_derivative_is_rejected():
    files, _, a4 = _shared_image_exchange(fourth_image="9" * 64)   # a different image cannot borrow image 2's OCR
    issues = [i for i in exchange_issues(files, mode="partial") if i.where == a4["anchor_id"]]
    assert "C16_ANCHOR_IMAGE" in _codes(issues)
