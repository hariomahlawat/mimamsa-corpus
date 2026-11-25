"""ASR-E06 (review E7-E9): citation navigation never substitutes the current copy, and never discloses why a
cited copy is unavailable."""
from __future__ import annotations

import csv
import json
from pathlib import Path

D = Path(__file__).resolve().parents[1]
POLICY = json.loads((D / "policies" / "citation_resolution.json").read_text(encoding="utf-8"))
REPO = D.parents[1]
GENERIC = "The cited copy is not available in this installation."


def test_invariants():
    inv = POLICY["invariants"]
    assert inv["auto_substitute_current_copy"] is False and inv["page_number_applied_to_other_copy"] is False
    assert inv["content_from_unavailable_copy"] is False and inv["citation_keeps_original_copy_hash_and_page"] is True
    assert inv["prefix_must_resolve_to_exactly_one_full_hash"] is True and inv["unavailable_reasons_indistinguishable_to_users"] is True


def test_eligible_states_open_the_cited_copy_and_offer_current_separately():
    for state in ("CITED_COPY_ELIGIBLE", "CITED_COPY_ELIGIBLE_NOT_CURRENT"):
        assert POLICY["states"][state]["opens"] == "cited_copy_at_cited_page"
    assert "open_current_edition_if_eligible" in POLICY["states"]["CITED_COPY_ELIGIBLE_NOT_CURRENT"]["actions"]


def test_unavailable_is_one_generic_state_with_no_hints():
    s = POLICY["states"]
    assert sorted(s["CITED_COPY_UNAVAILABLE"]["covers"]) == ["not held", "restricted", "withdrawn"]
    assert s["CITED_COPY_UNAVAILABLE"]["notice"] == GENERIC and s["CITED_COPY_UNAVAILABLE"]["actions"] == []
    for old in ("CITED_COPY_WITHDRAWN", "CITED_COPY_RESTRICTED", "CITED_COPY_NOT_HELD"):
        assert old not in s
    for word in ("withdrawn", "restricted", "date", "{"):
        assert word not in s["CITED_COPY_UNAVAILABLE"]["notice"].lower()


def test_e9_states_have_notice_and_no_content():
    for state in ("CITED_PAGE_NOT_IN_COPY", "AMBIGUOUS_REFERENCE", "REFERENCE_MISMATCH"):
        assert POLICY["states"][state]["opens"] is None and POLICY["states"][state]["notice"]


def test_design_and_security_docs_agree():
    ia = (D / "02_INFORMATION_ARCHITECTURE.md").read_text(encoding="utf-8")
    states = (D / "06_RESPONSIVE_AND_STATES.md").read_text(encoding="utf-8")
    sec = (REPO / "docs/architecture/SECURITY_AND_DEPLOYMENT_ARCHITECTURE.md").read_text(encoding="utf-8")
    assert "resolves to the current copy" not in ia
    assert "exact cited source copy and physical page" in ia and "never substituted" in ia and GENERIC in ia
    assert "never applied to a different copy" in states and GENERIC in states
    assert "withdrawn from the library on {date}" not in states
    assert GENERIC in sec


def test_matrix_cap_rw_04_matches():
    rows = {r["capability_id"]: r for r in csv.DictReader((REPO / "docs/architecture/CAPABILITY_TRACEABILITY_MATRIX.csv").open(encoding="utf-8"))}
    row = rows["CAP-RW-04"]
    assert "cited copy" in row["evidence_approval_gates"] and "never substitut" in row["evidence_approval_gates"]
    assert "UX-12" in row["acceptance_tests"]
