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


def R(fam, prov, date):
    return V.resolve_at(RECS, fam, prov, date)


def ids(res, key="candidates"):
    return [c["version_id"] for c in res[key]]


def test_resolver_never_assumes_latest_text():
    assert ids(R("AR1954", "r.22", "2000-01-01")) == ["AR1954/r.22/v02"]
    r = R("AR1954", "r.22", "1990-01-01")  # 1954 commencement not stated (AQ-05): no candidate, v01 only possible
    assert r["status"] == "UNDETERMINED" and r["candidates"] == [] and ids(r, "possible_versions") == ["AR1954/r.22/v01"]
    r = R("AR1954", "r.15", "2000-01-01")  # S.R.O. 205/1961 prints no commencement: both possible, none definite
    assert r["status"] == "UNDETERMINED" and ids(r, "possible_versions") == ["AR1954/r.15/v01", "AR1954/r.15/v02"]
    for res in (R("AR1954", "r.15", "2000-01-01"), R("AR1954", "r.22", "2000-01-01")):
        assert res["governing_axis"].startswith("NOT_DETERMINED")


# ---- review R-01: pre-commencement / not yet created
@pytest.mark.parametrize("fam,prov,date", [
    ("BNS2023", "whole", "1990-01-01"), ("BNS2023", "s.358", "1990-01-01"), ("BNSS2023", "s.531", "2000-01-01"),
    ("AFT2007", "s.9A", "1950-01-01"), ("AFT2007", "s.9A", "2010-01-01"), ("AA1950", "s.169A", "1950-01-01"),
    ("AA1950", "s.169A", "1990-01-01"), ("AR1954", "r.59A", "1950-01-01"), ("AR1954", "r.13A", "1950-01-01"),
    ("AR1954", "r.15A", "1950-01-01"), ("AR1954", "r.16A", "1978-01-01"), ("AR1954", "r.22", "1954-11-26")])
def test_r01_not_yet_in_force(fam, prov, date):
    r = R(fam, prov, date)
    assert r["status"] == "NOT_YET_IN_FORCE" and r["candidates"] == [] and r["reason"]


@pytest.mark.parametrize("fam,prov", [("BNS2023", "whole"), ("BNS2023", "s.358"), ("BNSS2023", "s.531"), ("BSA2023", "s.170")])
def test_r01_1_july_2024_boundary_is_undetermined_not_a_candidate(fam, prov):
    for d in ("2024-06-30", "2024-07-01"):
        r = R(fam, prov, d)
        assert r["status"] == "UNDETERMINED" and r["candidates"] == []
    assert "after this date" in json.dumps(R(fam, prov, "2024-06-30")["possible_versions"])
    assert "after this date" not in json.dumps(R(fam, prov, "2024-07-01")["possible_versions"])


def test_r01_negative_controls_stated_commencement_gives_candidates():
    r = R("AR1954", "r.16A", "1980-01-01")  # S.R.O. 188/1979 stated start 28-07-1979 (v03 is also deemed from 04-06-1979)
    assert r["status"] == "IN_FORCE_CANDIDATES" and ids(r) == ["AR1954/r.16A/v01", "AR1954/r.16A/v03"]
    assert ids(R("AR1954", "r.16A", "1986-01-01")) == ["AR1954/r.16A/v02", "AR1954/r.16A/v03"]
    assert R("AR1954", "r.22", "1954-11-27")["status"] == "UNDETERMINED"  # instrument exists from this date; commencement unstated
    assert ids(R("AFT2007", "s.9A", "2022-01-01")) == ["AFT2007/s.9A/v02"]  # TRA 2021 deemed 04-04-2021
    r = R("AR1954", "r.25", "2000-01-01")
    assert r["status"] == "NO_VERSION_IN_FORCE" and r["ceased_by"]["version_id"] == "AR1954/r.25/v02"
    assert ids(R("AR1954", "r.25", "1993-12-05"), "possible_versions") == ["AR1954/r.25/v01"]


# ---- review R-02: retrospective deemed effect
def test_r02_retrospective_deemed_versions_included_in_deemed_window():
    assert "AR1954/r.16A/v03" in ids(R("AR1954", "r.16A", "1985-01-01"))
    assert "AR1954/r.2/v03" in ids(R("AR1954", "r.2", "1985-01-01"))
    c = next(x for x in R("AR1954", "r.16A", "1985-01-01")["candidates"] if x["version_id"] == "AR1954/r.16A/v03")
    assert "retrospective deemed effect" in c["reason"] and "AQ-06" in c["reason"]


def test_n01_deemed_window_before_the_rule_itself_was_inserted():
    for d in ("1979-06-04", "1979-07-01", "1979-07-27"):
        r = R("AR1954", "r.16A", d)
        assert r["status"] == "IN_FORCE_CANDIDATES" and ids(r) == ["AR1954/r.16A/v03"], d
    r = R("AR1954", "r.16A", "1979-06-03")
    assert r["status"] == "NOT_YET_IN_FORCE" and "retrospective" in r["reason"]


def test_n02_inferred_masthead_qualifier_kept_in_reason():
    r = R("AFTPR2008", "whole", "2009-01-01")
    assert any("INFERRED_MASTHEAD" in c["reason"] for c in r["candidates"])
    assert not any("INFERRED_MASTHEAD" in c["reason"] for c in R("AR1954", "r.22", "2000-01-01")["candidates"])


def test_r02_negative_controls_outside_deemed_window():
    assert "AR1954/r.16A/v03" not in ids(R("AR1954", "r.16A", "1979-06-03"))
    assert "AR1954/r.2/v03" not in ids(R("AR1954", "r.2", "1979-01-01"))
    assert ids(R("AR1954", "r.16A", "1990-01-01")) == ["AR1954/r.16A/v03"]


# ---- review R-03: the creating instrument's date is an exclusion floor
@pytest.mark.parametrize("prov", ["s.75", "s.76", "s.127"])
def test_r03_1992_omissions_not_before_the_1992_act(prov):
    for d in ("1960-01-01", "1992-09-05"):
        r = R("AA1950", prov, d)
        allv = ids(r) + ids(r, "possible_versions")
        assert f"AA1950/{prov}/v02" not in allv
    assert "AA1950/Chapter XVI/v02" not in ids(R("AA1950", "Chapter XVI", "1960-01-01"), "possible_versions")
    assert "IPC1860/whole/v02" not in ids(R("IPC1860", "whole", "1990-01-01"), "possible_versions")


@pytest.mark.parametrize("prov", ["s.75", "s.76", "s.127"])
def test_r03_negative_controls_after_the_act_both_remain_open(prov):
    r = R("AA1950", prov, "2000-01-01")
    assert r["status"] == "UNDETERMINED" and ids(r, "possible_versions") == [f"AA1950/{prov}/v01", f"AA1950/{prov}/v02"]


def test_floor_is_lowered_only_by_a_stated_retrospective_date():
    v = by("AR1954", "r.16A")[2]
    assert V.instrument_floor(v) == "1979-06-04"
    assert V.instrument_floor(by("AA1950", "s.127")[1]) == "1992-09-06"


def test_inferred_masthead_dates_are_qualified():
    v = by("AFTPR2008", "whole")[0]
    assert v["effective_from"]["status"] == "STATED_IN_INSTRUMENT_DATE_FROM_INFERRED_MASTHEAD"


def test_multi_page_rule_lists_every_page_row():
    e = by("AR1954", "r.58")[0]["text_evidence"][0]
    assert "C13PE-1954-313-R57-R58" in e["evidence_ids"] and "C13PE-1954-314-R59-R62" in e["evidence_ids"]


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
