"""Tests for the C12 Workstream G forms registry (run with the scratchpad venv: pytest -q tests/)."""
import csv
import json
import os
import re
import subprocess
import sys

import pytest

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(WS, "tools")
OUT = os.path.join(WS, "outputs")
sys.path.insert(0, TOOLS)

import build_forms_registry as b  # noqa: E402
import spec_forms  # noqa: E402
import spec_sources  # noqa: E402


def rows(name):
    with open(os.path.join(OUT, name), newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


@pytest.fixture(scope="module")
def reg():
    return rows("FORM_DISCOVERY_REGISTER.csv")


@pytest.fixture(scope="module")
def fields():
    return rows("FORM_FIELDS.csv")


@pytest.fixture(scope="module")
def cov():
    return rows("SOURCE_COVERAGE.csv")


@pytest.fixture(scope="module")
def summary():
    with open(os.path.join(OUT, "SUMMARY.json"), encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------- reproducibility
def test_check_mode_reproduces_outputs_byte_for_byte():
    p = subprocess.run([sys.executable, "-I", os.path.join(TOOLS, "build_forms_registry.py"), "--check"], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert "CHECK OK" in p.stdout


def test_check_mode_detects_drift(tmp_path):
    for name in ("FORM_DISCOVERY_REGISTER.csv", "FORM_FIELDS.csv", "SOURCE_COVERAGE.csv", "SUMMARY.json"):
        data = open(os.path.join(OUT, name), encoding="utf-8").read()
        if name == "FORM_FIELDS.csv":
            assert "Date offence was discovered" in data
            data = data.replace("Date offence was discovered", "Date offence was invented", 1)
        (tmp_path / name).write_text(data, encoding="utf-8")
    p = subprocess.run([sys.executable, "-I", os.path.join(TOOLS, "build_forms_registry.py"), "--check", "--out", str(tmp_path)],
                       capture_output=True, text=True)
    assert p.returncode == 1
    assert "FORM_FIELDS.csv" in p.stderr


# ---------------------------------------------------------------- register integrity
def test_every_row_is_discovery_only(reg, fields, cov):
    for r in reg + fields + cov:
        assert r["verification_status"] == "DISCOVERED_FROM_SOURCE_NOT_LEGALLY_APPROVED"
    for r in reg:
        assert r["legal_approval_state"] == "RESEARCH_ONLY"
        assert r["applicability_state"] == "NOT_ESTABLISHED"
        assert r["fidelity_state"] in b.FIDELITY and r["fidelity_state"] != "FIDELITY_VERIFIED"


def test_vocabularies(reg, cov):
    for r in reg:
        assert r["form_authority_type_candidate"] in b.AUTHORITY_TYPES
        assert r["status_category"] in b.STATUS_CATEGORIES
    for r in cov:
        assert r["coverage_state"] in b.COVERAGE_STATES


def test_one_primary_per_family_and_unique_ids(reg):
    ids = [r["candidate_id"] for r in reg]
    assert len(ids) == len(set(ids))
    fams = {}
    for r in reg:
        fams.setdefault(r["form_family_id"], []).append(r["occurrence_role"])
    for f, roles in fams.items():
        assert roles.count("PRIMARY") == 1, f
    assert len(fams) == len(spec_forms.FAMILIES)


def test_alternate_links_resolve(reg):
    ids = {r["candidate_id"] for r in reg}
    fam_of = {r["candidate_id"]: r["form_family_id"] for r in reg}
    for r in reg:
        for a in filter(None, r["alternate_occurrences"].split(";")):
            assert a in ids
            assert fam_of[a] == r["form_family_id"]


def test_primary_anchor_and_hash_recorded(reg):
    for r in reg:
        assert re.fullmatch(r"[0-9a-f]{64}", r["source_copy_sha256"])
        if r["occurrence_role"] == "PRIMARY":
            assert r["anchor_match"] == "EXACT" or r["anchor_match"].startswith("FUZZY:")
            assert r["locator_start"] != ""


def test_page_locators_inside_documents(reg, summary):
    for r in reg:
        if r["locator_type"] == "PDF_PAGE":
            assert 1 <= int(r["locator_start"]) <= int(r["locator_end"])


# ---------------------------------------------------------------- fields: transcribe only what is printed
def test_fields_belong_to_families_and_match_primary(reg, fields):
    fam = {r["form_family_id"] for r in reg}
    exact_sources = {k for k, v in spec_sources.SOURCES.items() if v["match_mode"] == "exact"}
    prim_src = {r["candidate_id"]: r["source_key"] for r in reg if r["occurrence_role"] == "PRIMARY"}
    for f in fields:
        assert f["form_family_id"] in fam
        src = prim_src[f["transcription_candidate_id"]]
        if src in exact_sources:
            assert f["primary_match"] == "EXACT", f["field_id"]
        else:
            assert f["primary_match"] == "EXACT" or f["primary_match"].startswith("FUZZY:"), f["field_id"]


def test_fabricated_label_is_rejected_by_matcher():
    st = b.Store(b.DEFAULT_SCRATCH, b.DEFAULT_C7)
    rec = st.load("MML2")
    tn = b.page_text_n(rec, 304, 304)  # Form of Delay Report page
    assert b.match("Date offence was discovered", tn, "exact")[0] == "EXACT"
    assert b.match("Blood group of the accused", tn, "exact")[0] == "NOT_FOUND"
    assert b.match("Signature of Judge Advocate General", tn, "exact")[0] != "EXACT"


def test_whole_word_containment():
    assert not b.contains(b.norm("FORM I"), b.norm("this Form is redundant"))
    assert b.contains(b.norm("FORM I"), b.norm("FORM I Warrant to obtain"))
    assert b.norm("Officer’s  Certificate") == "officer s certificate"


def test_sha256_mismatch_is_fatal(monkeypatch):
    bad = dict(spec_sources.SOURCES["RA87-CH5"])
    bad["sha256"] = "0" * 64
    monkeypatch.setitem(spec_sources.SOURCES, "RA87-CH5", bad)
    st = b.Store(b.DEFAULT_SCRATCH, b.DEFAULT_C7)
    with pytest.raises(SystemExit):
        st.load("RA87-CH5")


# ---------------------------------------------------------------- coverage
def test_coverage_consistency(cov, reg):
    ids = {r["candidate_id"] for r in reg}
    for r in cov:
        if r["coverage_state"] == "INSPECTED_NO_FORMS_FOUND":
            assert r["candidate_occurrences_found"] == "0"
        for c in filter(None, r["candidate_ids"].split(";")):
            assert c in ids
        if r["holding"] == "NOT_HELD":
            assert r["coverage_state"] == "INACCESSIBLE"
    # every held source used by an occurrence has at least one coverage row
    used = {r["source_key"] for r in reg}
    assert used <= {r["source_key"] for r in cov}


def test_known_gaps_are_recorded(cov):
    text = " ".join(r["pages_missing_unreadable_or_unexamined"] + " " + r["segment_label"] for r in cov)
    assert "Appendix II (Form of Charges)" in text           # not located in the 1954 Gazette copy
    assert "does not print the Appendices" in text            # India Code compilation
    assert "Regulations for the Army (Revised Edition) 1987" in text


# ---------------------------------------------------------------- summary
def test_summary_counts_match(summary, reg, fields, cov):
    c = summary["counts"]
    assert c["unique_form_families"] == len({r["form_family_id"] for r in reg})
    assert c["occurrences_total"] == len(reg)
    assert c["fields_recorded"] == len(fields)
    assert c["coverage_rows"] == len(cov)
    assert summary["verification_status_all_rows"] == "DISCOVERED_FROM_SOURCE_NOT_LEGALLY_APPROVED"
    assert "percent" not in json.dumps(summary["counts"]).lower()
