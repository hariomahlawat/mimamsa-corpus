"""C13 A4: provision-level temporal version model - schema, chain invariants, no inferred dates, date resolver."""
import copy
import json
import sys
from pathlib import Path

import pytest

PKG = Path(__file__).resolve().parents[1] / "legal_knowledge" / "audit_work" / "C13-A4-STATUTORY"
sys.path.insert(0, str(PKG / "tools"))
jsonschema = pytest.importorskip("jsonschema")
import validate_versions_c13 as V  # noqa: E402

RECS = V.load()


def by(fam, prov):
    return sorted([r for r in RECS if r["family"] == fam and r["provision"] == prov], key=lambda r: r["version_seq"])


def test_all_records_validate():
    assert V.validate(RECS) == []


def test_every_record_is_an_unverified_candidate_with_separate_undetermined_axes():
    for r in RECS:
        assert r["determination_state"] == "AUTOMATED_CANDIDATE_NOT_VERIFIED"
        assert set(r["temporal_axes"]) == {"conduct_date", "proceedings_date", "procedural_action_date", "document_preparation_review_date"}
        assert {a["status"] for a in r["temporal_axes"].values()} == {"NOT_DETERMINED"}


def test_priority_rules_are_modelled():
    for p in ("r.15", "r.22", "r.23", "r.24", "r.25", "r.180"):
        assert by("AR1954", p), p
    assert [v["version_kind"] for v in by("AR1954", "r.22")] == ["as_notified", "substitution"]
    assert by("AR1954", "r.22")[1]["effective_from"]["date"] == "1993-12-06"
    assert by("AR1954", "r.25")[-1]["version_kind"] == "omission"
    assert by("AR1954", "r.25")[-1]["effective_to"]["status"] == "CEASED_OMITTED_OR_REPEALED"


def test_reserved_conflicts_and_open_alleged_amendments_stay_explicit():
    r23 = by("AR1954", "r.23")
    assert len(r23) == 1 and "C-01" in r23[0]["conflicts"] and r23[0]["text_status"] == "CONFLICTING"
    assert any("AR-030" in o for o in by("AR1954", "r.22")[-1]["open_items"])
    assert any("GAP-15" in o for o in by("AR1954", "r.15")[-1]["open_items"])
    assert all(v["legal_review_required"] for v in r23)


def test_r15b_exception_is_not_attached_to_versions_that_ended_before_2019():
    r14 = by("AR1954", "r.14")
    ended = [v for v in r14 if v["effective_to"]["date"] and v["effective_to"]["date"] <= "2019-12-28"]
    assert ended and all(not v["applicability_exceptions"] for v in ended)
    assert by("AR1954", "r.15")[-1]["applicability_exceptions"][0]["instrument_id"] == "AR-034"


def test_no_inferred_commencement_dates():
    for r in RECS:
        if r["effective_from"]["date"]:
            assert r["effective_from"]["status"].startswith("STATED"), r["version_id"]
    v1 = by("AR1954", "r.22")[0]
    assert v1["effective_from"]["date"] is None and v1["effective_from"]["status"] == "NOT_STATED_PENDING_ADVICE"
    bns = by("BNS2023", "whole")[0]
    assert bns["effective_from"]["date"] is None and bns["effective_from"]["reported_date"] == "2024-07-01"
    assert bns["applicability_exceptions"][0]["provision"] == "s.106(2)"


def test_criminal_law_transition_repeals_and_savings():
    for fam, rep in (("IPC1860", "s.358"), ("CRPC1973", "s.531"), ("IEA1872", "s.170")):
        vs = by(fam, "whole")
        assert vs[-1]["version_kind"] == "repeal_with_savings"
        assert vs[-1]["savings_transitional"] and vs[-1]["savings_transitional"][0]["provision"].startswith(rep)
        assert vs[-1]["effective_to"]["status"] == "CEASED_OMITTED_OR_REPEALED"


def test_resolver_never_assumes_latest_text():
    assert [c["version_id"] for c in V.candidates_at(RECS, "AR1954", "r.22", "1990-01-01")] == ["AR1954/r.22/v01"]
    assert [c["version_id"] for c in V.candidates_at(RECS, "AR1954", "r.22", "2000-01-01")] == ["AR1954/r.22/v02"]
    # r.15: the 1961 substitution prints no commencement, so for 2000 both versions remain candidates
    assert [c["version_id"] for c in V.candidates_at(RECS, "AR1954", "r.15", "2000-01-01")] == ["AR1954/r.15/v01", "AR1954/r.15/v02"]
    for c in V.candidates_at(RECS, "AR1954", "r.15", "2000-01-01"):
        assert c["governing_axis"].startswith("NOT_DETERMINED")
    # Army Act s.127 omitted by Act 37/1992 (no commencement clause): both remain candidates in 2000
    assert len(V.candidates_at(RECS, "AA1950", "s.127", "2000-01-01")) == 2


def test_validator_rejects_an_inferred_date_and_a_broken_chain():
    bad = copy.deepcopy(RECS)
    v = next(r for r in bad if r["version_id"] == "AR1954/r.22/v01")
    v["effective_from"]["date"] = "1954-11-27"  # publication date treated as commencement
    errs = V.validate(bad)
    assert any("inferred date" in e for e in errs)
    bad = copy.deepcopy(RECS)
    v = next(r for r in bad if r["version_id"] == "AR1954/r.22/v01")
    v["effective_to"]["next_version_id"] = "AR1954/r.22/v09"
    assert any("next_version_id" in e for e in V.validate(bad))
    bad = copy.deepcopy(RECS)
    next(r for r in bad if r["version_id"] == "AR1954/r.23/v01")["legal_review_required"] = False
    assert V.validate(bad)


def test_every_image_checked_version_points_to_a_copy_page_and_check():
    for r in RECS:
        for e in r["text_evidence"]:
            if e["method"] == "IMAGE_CHECKED":
                assert e["evidence_ids"], r["version_id"]
            if e["sha256"]:
                assert len(e["sha256"]) == 64
    v = by("AR1954", "r.52")[-1]
    shas = {e["sha256"] for e in v["text_evidence"]}
    assert "c5ef95a9d553685aa655f041b71d8360d6272e2775a19a3d6e7273c6cbd0aca6" in shas
    assert "e9bf2114ab633716ea954db6e100be858e45949384f9fc0667364308bff46912" in shas
