from __future__ import annotations

import json

import pytest

from mimamsa_contract import CONTRACT_VERSION
from mimamsa_contract.rules import record_issues
from mimamsa_contract.schemas import KIND_TO_SCHEMA, SCHEMA_DIR, registry, validator


def codes(issues):
    return {i.code for i in issues if i.severity == "error"}


def test_all_schemas_are_valid_and_offline():
    reg = registry()
    for name in KIND_TO_SCHEMA.values():
        assert reg.contents("https://contract.mimamsa.invalid/v1/" + name)
    for p in SCHEMA_DIR.glob("*.json"):
        text = p.read_text()
        # every $ref is local (relative file or fragment); nothing points at a real host
        for line in text.splitlines():
            if '"$ref"' in line:
                assert "http" not in line, f"{p.name}: remote $ref"


def test_remote_reference_is_refused():
    with pytest.raises(Exception):
        registry().get_or_retrieve("https://example.org/remote.schema.json")


def test_contract_version_matches_schema_pattern():
    assert validator("document").schema  # loads
    v = json.loads((SCHEMA_DIR / "common.schema.json").read_text())["$defs"]["contract_version"]["pattern"]
    import re
    assert re.match(v, CONTRACT_VERSION)


@pytest.mark.parametrize("name,kind", [
    ("document", "document"), ("derived_text", "derived_text"),
    ("candidate_graph_edge", "candidate"), ("candidate_outcome", "candidate"),
])
def test_examples_are_valid(example, register, name, kind):
    assert codes(record_issues(kind, example(name), register, name, ledger_version=0)) == set()


def test_manifest_example_schema_valid(example):
    errs = list(validator("release_manifest").iter_errors(example("release_manifest")))
    assert errs == []


def test_no_single_verified_flag(example, register):
    doc = example("document")
    doc["verified"] = True
    assert "SCHEMA" in codes(record_issues("document", doc, register, "x"))  # additionalProperties false


def test_all_seven_axes_required(example, register):
    for axis in ["source_integrity", "source_authenticity", "evidence_fidelity", "legal_applicability",
                 "legal_approval", "publication", "dependency_freshness"]:
        doc = example("document")
        del doc["status_axes"][axis]
        assert "SCHEMA" in codes(record_issues("document", doc, register, axis)), axis


def test_axis_value_needs_basis(example, register):
    doc = example("document")
    doc["status_axes"]["publication"]["basis"] = ""
    assert "SCHEMA" in codes(record_issues("document", doc, register, "x"))


def test_publication_axis_cannot_carry_approval_value(example, register):
    doc = example("document")
    doc["status_axes"]["publication"]["value"] = "T2_FORMAL_JAG_VALIDATED"
    assert "SCHEMA" in codes(record_issues("document", doc, register, "x"))


def test_ledger_v0_blocks_any_legal_approval(example, register):
    doc = example("document")
    doc["status_axes"]["legal_approval"] = {"value": "T1_LEGAL_ADVISER_REVIEWED", "basis": "claimed", "approval_record_id": "AP-0001"}
    assert "LEDGER_V0_NO_APPROVAL" in codes(record_issues("document", doc, register, "x", ledger_version=0))


def test_approval_outside_bundle_never_accepted(example, register):
    """F01: an approval can only be accepted with its approval record, appointment and artefact in the same bundle."""
    doc = example("document")
    doc["status_axes"]["legal_approval"] = {"value": "T2_FORMAL_JAG_VALIDATED", "basis": "claimed", "approval_record_id": "AP-0001"}
    assert "APPROVAL_UNRESOLVED" in codes(record_issues("document", doc, register, "x", ledger_version=5))


def test_approval_needs_record_id(example, register):
    doc = example("document")
    doc["status_axes"]["legal_approval"] = {"value": "T2_FORMAL_JAG_VALIDATED", "basis": "claimed"}
    assert "SCHEMA" in codes(record_issues("document", doc, register, "x", ledger_version=5))
    doc["status_axes"]["legal_approval"] = {"value": "T0_RESEARCH_ONLY", "basis": "ok", "approval_record_id": "AP-0001"}
    assert "SCHEMA" in codes(record_issues("document", doc, register, "x"))


@pytest.mark.parametrize("axis", ["publication", "source_integrity", "evidence_fidelity", "legal_applicability",
                                  "legal_approval", "dependency_freshness"])
def test_policy_object_cannot_be_smuggled_into_other_axes(example, register, axis):
    """F01 negative control (reviewer probe P13)."""
    doc = example("document")
    doc["status_axes"][axis]["policy_v1"] = {"legal_approval": "T2_FORMAL_JAG_VALIDATED", "verified": True}
    assert "SCHEMA" in codes(record_issues("document", doc, register, "x"))


@pytest.mark.parametrize("axis", ["publication", "source_integrity", "evidence_fidelity"])
def test_unknown_keys_rejected_on_every_axis(example, register, axis):
    doc = example("document")
    doc["status_axes"][axis]["legal_approval"] = "T1_LEGAL_ADVISER_REVIEWED"
    assert "SCHEMA" in codes(record_issues("document", doc, register, "x"))


def test_approval_ref_free_string_not_accepted(example, register):
    doc = example("document")
    doc["status_axes"]["legal_approval"] = {"value": "T1_LEGAL_ADVISER_REVIEWED", "basis": "x x", "approval_ref": "anything"}
    assert "SCHEMA" in codes(record_issues("document", doc, register, "x", ledger_version=3))


@pytest.mark.parametrize("axis,value", [("evidence_fidelity", "FIDELITY_VERIFIED"),
                                        ("source_authenticity", "IDENTITY_CONFIRMED"), ("dependency_freshness", "CURRENT_FOR_CHECKED_SCOPE")])
def test_raised_values_need_review_record(example, register, axis, value):
    """F02 negative controls (reviewer probes P01-P03)."""
    doc = example("document")
    doc["status_axes"][axis]["value"] = value
    doc["status_axes"][axis]["basis"] = "trust me"
    assert "RAISED_VALUE_NEEDS_REVIEW" in codes(record_issues("document", doc, register, "x"))


def test_identity_confirmed_contradicts_hash_only(example, register):
    doc = example("document")
    doc["status_axes"]["source_authenticity"].update(value="IDENTITY_CONFIRMED", review_record_id="RV-0001")
    assert "AXIS_CONTRADICTION" in codes(record_issues("document", doc, register, "x"))


@pytest.mark.parametrize("integrity", ["MISMATCH", "NOT_CHECKED"])
def test_published_with_bad_integrity_rejected(example, register, integrity):
    """F02 (reviewer probe P15)."""
    doc = example("document")
    doc["status_axes"]["source_integrity"] = {"value": integrity, "basis": "see report"}
    assert "AXIS_CONTRADICTION" in codes(record_issues("document", doc, register, "x"))


def test_byte_verified_needs_evidence_ref(example, register):
    doc = example("document")
    doc["status_axes"]["source_integrity"]["evidence_ref"] = None
    assert "RAISED_VALUE_NEEDS_REVIEW" in codes(record_issues("document", doc, register, "x"))


def test_working_document_record_rejected(register):
    assert "WORKING_DOCUMENT_IN_BUNDLE" in codes(record_issues("document", {"record_kind": "working_document"}, register, "x"))


def test_candidate_review_ref_must_be_review_id(example, register):
    c = example("candidate_graph_edge")
    c["status"] = "DOCUMENTARY_CHECKED"
    c["review_ref"] = "free text"
    assert "SCHEMA" in codes(record_issues("candidate", c, register, "x"))


def test_vault_path_must_match_hash(example, register):
    doc = example("document")
    doc["source_copy"]["vault_path"] = "vault/sha256/00/" + "0" * 64
    assert "VAULT_PATH_MISMATCH" in codes(record_issues("document", doc, register, "x"))


def test_published_requires_eligibility(example, register):
    doc = example("document")
    doc["restriction"]["eligibility"] = "NOT_ASSESSED"
    assert "PUBLISH_WITHOUT_ELIGIBILITY" in codes(record_issues("document", doc, register, "x"))


def test_marking_needs_recorded_basis(example, register):
    doc = example("document")
    doc["restriction"]["access_marking"] = "SOME PRINTED MARKING"
    assert "MARKING_WITHOUT_DECISION" in codes(record_issues("document", doc, register, "x"))


def test_unsafe_relative_paths_rejected(example, register):
    for bad in ["../etc/passwd", "/abs/path", "C:/x", "a\\b", "a/../../b"]:
        dt = example("derived_text")
        dt["text_path"] = bad
        assert "SCHEMA" in codes(record_issues("derived_text", dt, register, bad)), bad


def test_ocr_text_cannot_be_quoted(example, register):
    dt = example("derived_text")
    dt["pages"][1]["method"] = "ocr"
    assert "OCR_QUOTING" in codes(record_issues("derived_text", dt, register, "x"))
    dt["quoting_permitted"] = False
    assert "OCR_QUOTING" not in codes(record_issues("derived_text", dt, register, "x"))


def test_passage_must_point_to_known_page(example, register):
    dt = example("derived_text")
    dt["passages"][0]["page"] = 9
    assert "PASSAGE_PAGE_UNKNOWN" in codes(record_issues("derived_text", dt, register, "x"))


def test_candidate_requires_anchor_and_page(example, register):
    c = example("candidate_graph_edge")
    c["anchors"] = []
    assert "SCHEMA" in codes(record_issues("candidate", c, register, "x"))
    c = example("candidate_graph_edge")
    del c["anchors"][0]["page"]
    assert "SCHEMA" in codes(record_issues("candidate", c, register, "x"))


def test_candidate_cannot_claim_legal_validity(example, register):
    c = example("candidate_graph_edge")
    c["status"] = "LEGAL_VALIDATED"
    assert "SCHEMA" in codes(record_issues("candidate", c, register, "x"))


def test_documentary_check_needs_review_ref(example, register):
    c = example("candidate_graph_edge")
    c["status"] = "DOCUMENTARY_CHECKED"
    assert "REVIEW_REF_REQUIRED" in codes(record_issues("candidate", c, register, "x"))


@pytest.mark.parametrize("relation,flag", [("CITES_JUDGMENT", True), ("OVERRULES_OR_LIMITS_PROPOSITION", False),
                                           ("OMITS_PROVISION", False)])
def test_edge_legal_effect_flag_enforced(example, register, relation, flag):
    c = example("candidate_graph_edge")
    c["payload"]["relation"] = relation
    c["payload"]["has_legal_effect"] = flag
    assert "EDGE_LEGAL_EFFECT_FLAG" in codes(record_issues("candidate", c, register, "x"))


def test_legal_effect_edge_human_verified_needs_review(example, register):
    c = example("candidate_graph_edge")
    c["payload"].update(relation="SUPERSEDES_INSTRUMENT", has_legal_effect=True, confidence="human_verified")
    assert "LEGAL_EFFECT_EDGE_UNREVIEWED" in codes(record_issues("candidate", c, register, "x"))


def test_unresolved_edge_keeps_raw_reference(example, register):
    c = example("candidate_graph_edge")
    c["payload"]["target"]["raw_reference"] = None
    assert "EDGE_TARGET" in codes(record_issues("candidate", c, register, "x"))


def test_holdings_hidden_and_restricted(example, register):
    c = example("candidate_outcome")
    c["candidate_type"] = "holding"
    c["payload"] = {"item_type": "holding", "voice": "court", "opinion": "sole"}
    assert "HOLDINGS_HIDDEN" in codes(record_issues("candidate", c, register, "x"))
    c["capability_restriction"] = "HIDDEN_FROM_USERS"
    assert codes(record_issues("candidate", c, register, "x")) == set()


def test_outcome_must_carry_restriction(example, register):
    c = example("candidate_outcome")
    c["capability_restriction"] = "NONE_RECORDED"
    assert "RESTRICTION_REQUIRED" in codes(record_issues("candidate", c, register, "x"))


def test_form_template_never_usable(example, register):
    c = example("candidate_outcome")
    c["candidate_type"] = "form"
    c["payload"] = {"family_id": "F-EX", "field_set_version": "MML_DERIVED", "form_authority_candidate": "OTHER_OR_UNDETERMINED",
                    "usable_as_template": True}
    assert "SCHEMA" in codes(record_issues("candidate", c, register, "x"))


@pytest.mark.parametrize("value", ["UNRESOLVED", "PARTIAL_CHAIN", "EVIDENCED", "CONFLICTING", "NOT_APPLICABLE"])
def test_legal_applicability_never_raised_at_ledger_v0(example, register, value):
    """F02: legal applicability is a legal determination; no record may carry it above NOT_ESTABLISHED at ledger v0."""
    doc = example("document")
    doc["status_axes"]["legal_applicability"] = {"value": value, "basis": "technical review"}
    c = codes(record_issues("document", doc, register, "x", ledger_version=0))
    assert "LEDGER_V0_NO_APPLICABILITY" in c and "LEGAL_AXIS_NEEDS_APPROVAL" in c


def test_legal_applicability_cannot_cite_review_record(example, register):
    doc = example("document")
    doc["status_axes"]["legal_applicability"] = {"value": "EVIDENCED", "basis": "x y", "review_record_id": "RV-0001"}
    assert "SCHEMA" in codes(record_issues("document", doc, register, "x"))


def test_reviewed_record_cannot_target_legal_axes(register):
    base = {"contract_version": "1.0.0", "record_kind": "reviewed_record", "review_record_id": "RV-0001",
            "subject": {"kind": "document", "id": "d1"}, "from_value": "a", "to_value": "b",
            "reviewer": {"reviewer_id": "r-1", "name_or_role": "x y", "kind": "HUMAN"},
            "reviewed_artefact": {"author_id": "a-1", "reviewed_commit": "0000000"}, "method": "method text here",
            "decided_at": "2026-11-25T00:00:00Z", "record_location": {"path": "x/y.md", "commit": "0000000"}}
    for axis in ("legal_applicability", "legal_approval"):
        assert "SCHEMA" in codes(record_issues("reviewed_record", dict(base, axis=axis), register, "x"))


def test_raised_value_outside_bundle_is_an_error(example, register):
    """C01: record-level (CLI) validation cannot accept a raised value whose review it cannot resolve."""
    doc = example("document")
    doc["status_axes"]["evidence_fidelity"] = {"value": "DOCUMENTARY_CHECKED", "basis": "x y", "review_record_id": "RV-0001"}
    assert "REVIEW_UNRESOLVED_OUTSIDE_BUNDLE" in codes(record_issues("document", doc, register, "x"))
