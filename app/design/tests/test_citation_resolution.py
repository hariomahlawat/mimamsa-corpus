"""ASR-E06: citation navigation never substitutes the current copy for the cited copy."""
from __future__ import annotations

import csv
import json
from pathlib import Path

D = Path(__file__).resolve().parents[1]
POLICY = json.loads((D / "policies" / "citation_resolution.json").read_text(encoding="utf-8"))
REPO = D.parents[1]


def test_invariants():
    inv = POLICY["invariants"]
    assert inv["auto_substitute_current_copy"] is False and inv["page_number_applied_to_other_copy"] is False
    assert inv["content_from_unavailable_copy"] is False and inv["citation_keeps_original_copy_hash_and_page"] is True


def test_eligible_states_open_the_cited_copy_and_offer_current_separately():
    for state in ("CITED_COPY_ELIGIBLE", "CITED_COPY_ELIGIBLE_SUPERSEDED"):
        assert POLICY["states"][state]["opens"] == "cited_copy_at_cited_page"
    assert "open_current_edition" in POLICY["states"]["CITED_COPY_ELIGIBLE_SUPERSEDED"]["actions"]


def test_unavailable_states_show_notice_and_no_content():
    for state in ("CITED_COPY_WITHDRAWN", "CITED_COPY_RESTRICTED", "CITED_COPY_NOT_HELD"):
        s = POLICY["states"][state]
        assert s["opens"] is None and s["notice"]
        assert all(a.endswith("_if_eligible") for a in s["actions"] if a.startswith("open_current"))


def test_design_docs_agree_no_current_copy_resolution():
    ia = (D / "02_INFORMATION_ARCHITECTURE.md").read_text(encoding="utf-8")
    states = (D / "06_RESPONSIVE_AND_STATES.md").read_text(encoding="utf-8")
    assert "resolves to the current copy" not in ia
    assert "exact cited source copy and physical page" in ia and "never substituted" in ia
    assert "never applied to a different copy" in states and "never taken there automatically" in states


def test_matrix_cap_rw_04_matches():
    rows = {r["capability_id"]: r for r in csv.DictReader((REPO / "docs/architecture/CAPABILITY_TRACEABILITY_MATRIX.csv").open(encoding="utf-8"))}
    row = rows["CAP-RW-04"]
    assert "cited copy" in row["evidence_approval_gates"] and "never substitut" in row["evidence_approval_gates"]
    assert "UX-12" in row["acceptance_tests"]
