"""C13 A4: evidence improvement on the 983 citation items, packets, restricted material and reproducibility."""
import csv
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "legal_knowledge" / "audit_work" / "C13-A4-STATUTORY"
OUT = PKG / "outputs"
sys.path.insert(0, str(PKG / "tools"))
import c13a4_common as C  # noqa: E402


def rows(name):
    return list(csv.DictReader(open(OUT / name, encoding="utf-8")))


def test_frozen_originals_unchanged():
    for rel, pin in C.FROZEN.items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == pin


def test_before_after_matrix():
    m = rows("EVIDENCE_MATRIX_C13.csv")
    assert len(m) == 983
    assert Counter(r["baseline_state"] for r in m) == Counter({"PARTIAL_MATCH": 652, "MISSING_EVIDENCE": 289, "EXACT_ANCHOR": 42})
    assert Counter(r["c12f_state_proposed"] for r in m) == Counter({"PARTIAL_MATCH": 595, "MISSING_EVIDENCE": 289, "EXACT_ANCHOR": 99})
    assert Counter(r["c13_state_proposed"] for r in m) == Counter({"PARTIAL_MATCH": 585, "MISSING_EVIDENCE": 289, "EXACT_ANCHOR": 109})


def test_only_partial_to_exact_moves_and_every_move_rests_on_image_checked_pages():
    m = rows("EVIDENCE_MATRIX_C13.csv")
    pe = {e["evidence_id"]: e for e in csv.DictReader(open(PKG / "inputs/page_evidence_c13.csv", encoding="utf-8"))}
    moved = [r for r in m if r["c13_state_proposed"] != r["c12f_state_proposed"]]
    assert len(moved) == 10
    for r in moved:
        assert (r["c12f_state_proposed"], r["c13_state_proposed"]) == ("PARTIAL_MATCH", "EXACT_ANCHOR")
        assert r["source_id"] == "C5-SRC-P0-ARMY-RULES-1954" and r["c13_gate"].startswith("C13_GATE_PASSED")
        assert r["blockers_c13"] == ""
        ids = [i for i in r["new_page_evidence_ids"].split(";") if i]
        assert ids and all(pe[i]["check_type"] == "C13_IMAGE_CHECK" for i in ids)
    assert not [r for r in m if r["baseline_state"] == "MISSING_EVIDENCE" and r["c13_state_proposed"] != "MISSING_EVIDENCE"]
    assert all(r["c13_state_proposed"] == "EXACT_ANCHOR" for r in m if r["c12f_state_proposed"] == "EXACT_ANCHOR")
    # tier-A blockers untouched: no r.22 / r.23 / r.15 item is promoted
    for r in m:
        if r["source_id"] == "C5-SRC-P0-ARMY-RULES-1954" and "#" in r["provision_id"]:
            toks = set(r["provision_id"].split("#")[1].split(","))
            if toks & {"r22", "r23", "r15", "r177", "r182"}:
                assert r["c13_state_proposed"] == r["c12f_state_proposed"]


def test_proposals_are_traceable_and_not_applied():
    p = rows("EVIDENCE_PROPOSALS_C13.csv")
    assert len(p) == 10
    for r in p:
        assert r["status"] == "PROPOSED_NOT_APPLIED"
        assert "c5ef95a9d553685aa655f041b71d8360d6272e2775a19a3d6e7273c6cbd0aca6" in r["copy_sha256"]
        assert "PDF p." in r["instrument_edition_pages"] and "printed p." in r["instrument_edition_pages"]
        assert r["page_evidence_ids"] and r["render_png_sha256"]


def test_page_evidence_rows_well_formed():
    pe = list(csv.DictReader(open(PKG / "inputs/page_evidence_c13.csv", encoding="utf-8")))
    assert len(pe) == 21
    for e in pe:
        assert len(e["sha256"]) == 64 and len(e["render_png_sha256"]) == 64 and e["probe"] and e["observed_on_image"]
        if e["copy_id"].startswith("C5-SRC-P0-ARMY-RULES-1954"):
            assert int(e["printed_page"]) == int(e["pdf_page"]) + 290


def test_adviser_packet_states_questions_not_conclusions():
    a = rows("ADVISER_REVIEW_PACKET_A4.csv")
    cats = Counter(r["category"] for r in a)
    assert cats["PROMOTION_C12F"] == 57 and cats["PROMOTION_C13"] == 10
    for r in a:
        assert r["status"] == "FOR_LEGAL_ADVISER_NO_CONCLUSION_DRAWN"
        assert r["exact_question"].rstrip().endswith("?"), r["packet_id"]
        assert r["evidence"] and r["competing_readings"] and r["decision_required"]
    subjects = " ".join(r["subject"] for r in a)
    for s in ("C-01", "SC4-01", "C-03", "r.15B", "S.R.O. 258/2002", "Military Secretary"):
        assert s in subjects or s in " ".join(r["exact_question"] + r["cross_refs"] for r in a), s


def test_acquisition_requests_cover_named_gaps_and_are_not_executed():
    q = rows("ACQUISITION_REQUESTS_A4.csv")
    text = " ".join(r["target_instrument"] for r in q)
    for s in ("S.R.O. 258", "Military Secretary", "S.O. 14(E)", "S.O. 848(E)", "S.R.O. 120", "Tribunals Reforms Act 2026"):
        assert s in text, s
    assert {r["status"] for r in q} == {"REQUESTED_FOR_A7_NOT_EXECUTED"}
    assert "aftjabalpur" not in json.dumps(q).replace("never aftjabalpur.in", "")


def test_no_restricted_material_in_any_package_file():
    for p in PKG.rglob("*"):
        if p.is_file() and p.suffix in (".csv", ".json", ".jsonl", ".md") and "reviews" not in p.parts:  # review records quote the denylist
            C.assert_no_restricted(p.name, p.read_bytes())


def _held():
    return (C.HF_ANCHOR / "legal_knowledge/preservation/c5_working_store").exists()


@pytest.mark.skipif(not _held(), reason="HF preservation copies not downloaded locally (see README)")
@pytest.mark.parametrize("tool", ["build_evidence_c13.py", "build_versions_c13.py", "build_packets_c13.py", "validate_versions_c13.py", "sha256sums_c13.py"])
def test_tools_check(tool):
    r = subprocess.run([sys.executable, str(PKG / "tools" / tool), "--check"], capture_output=True, text=True, cwd=str(PKG / "tools"), env=dict(os.environ))
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.skipif(not _held(), reason="HF preservation copies not downloaded locally (see README)")
def test_page_renders_reproduce():
    r = subprocess.run([sys.executable, str(PKG / "tools/render_pages_c13.py"), "--verify"], capture_output=True, text=True, cwd=str(PKG / "tools"))
    assert r.returncode == 0, r.stdout + r.stderr
