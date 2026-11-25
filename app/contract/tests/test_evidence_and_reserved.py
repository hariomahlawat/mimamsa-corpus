"""PR #53 reconciliation: retrieval provenance keys, span binding, reserved site-only namespaces."""
from __future__ import annotations

import pytest

from mimamsa_contract.evidence import PageKey, evidence_keys, resolve_span
from mimamsa_contract.rules import record_issues
from test_bundle import codes, make_bundle, owner_keys, prod, trust  # noqa: F401  (fixtures)


def _codes(issues, sev="error"):
    return {i.code for i in issues if i.severity == sev}


def test_page_only_anchor_gives_page_key(example):
    a = {"source_copy_sha256": "a" * 64, "page": 7}
    page, span, why = evidence_keys(a)
    assert page == PageKey("a" * 64, 7) and span is None and why is None


def test_unbound_span_degrades_to_page_only(example, register):
    c = example("candidate_graph_edge")
    c["anchors"][0]["derivative_text_sha256"] = None
    page, span, why = evidence_keys(c["anchors"][0])
    assert span is None and "page-only" in why
    assert "SPAN_UNBOUND" in _codes(record_issues("candidate", c, register, "x"), "warning")


def test_span_resolves_only_against_exact_derivative(example):
    d1 = example("derived_text")
    d2 = example("derived_text")
    d2["text_sha256"] = "f" * 64          # newer derivative with same passage ids
    a = example("candidate_graph_edge")["anchors"][0]
    _, span, _ = evidence_keys(a)
    assert resolve_span(span, [d2]) is None
    assert resolve_span(span, [d2, d1])["passage_id"] == "p2-1"


def test_bundle_rejects_span_bound_to_missing_derivative(make_bundle, trust, register, example):  # noqa: F811
    c = example("candidate_graph_edge")
    c["anchors"][0]["derivative_text_sha256"] = "e" * 64
    assert "DANGLING_SPAN_BINDING" in codes(prod(make_bundle(candidates=[c]), trust, register))


@pytest.mark.parametrize("kind", ["agent_workflow", "agent_private_draft", "final_claim", "serving_epoch", "policy_witness", "rule_pack"])
def test_reserved_record_kinds_never_exchanged(register, kind):
    assert "RESERVED_RECORD_KIND" in _codes(record_issues("document", {"record_kind": kind}, register, "x"))


@pytest.mark.parametrize("path", ["agent/u1/draft.json", "private/u1/x.txt", "workflows/w1.json", "claims/c1.json", "policy/witness.json"])
def test_reserved_paths_never_in_bundle(make_bundle, trust, register, path):  # noqa: F811
    assert "RESERVED_NAMESPACE" in codes(prod(make_bundle(extra_files={path: (b"x", "other")}), trust, register))


def test_resolve_span_checks_offsets_without_passage_id(example):
    """Review F06: with passage_id null, offsets must lie inside a passage; out-of-range offsets resolve to None."""
    d = example("derived_text")
    a = dict(example("candidate_graph_edge")["anchors"][0], passage_id=None, char_start=10, char_end=90)
    _, span, _ = evidence_keys(a)
    assert resolve_span(span, [d])["passage_id"] == "p2-1"
    a.update(char_start=340, char_end=900)  # beyond p2-1 (0..350)
    _, span, _ = evidence_keys(a)
    assert resolve_span(span, [d]) is None


def test_contract_revision_marker():
    """Review F09: R2 is machine-detectable."""
    from mimamsa_contract import CONTRACT_REVISION, CONTRACT_VERSION
    assert CONTRACT_VERSION == "1.0.0" and CONTRACT_REVISION == "R2"
