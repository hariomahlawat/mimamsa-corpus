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


# ---------------------------------------------------------------- C12 remediation of review WSG-R01..R15
import copy  # noqa: E402


def prim_rows(reg):
    return {r["form_family_id"]: r for r in reg if r["occurrence_role"] == "PRIMARY"}


def test_wsg_r01_aft_form3_pinned_to_rule_27(reg):
    rows3 = [r for r in reg if r["form_family_id"] == "FF-AFTPR08-F3"]
    assert rows3
    for r in rows3:
        assert "(see rule 27)" in r["printed_title"]
        assert r["prescribing_provision"].startswith("r.27(3)")
        assert r["requirement_language_as_printed"].startswith("r.27(3) [AFTPR08-C7 p.38]")
        for col in ("printed_title", "prescribing_provision", "requirement_language_as_printed"):
            assert not re.search(r"(rule|r\.)\s*17\b", r[col]), col
        assert "VC-AFT-P46" in r["visual_check_refs"]
    vc = {v["id"]: v for v in spec_forms.VISUAL_CHECKS}
    assert "27" in vc["VC-AFT-P46"]["rule_numbers"] and "27" in vc["VC-AFT-P37"]["rule_numbers"] and "27" in vc["VC-AFT-P38"]["rule_numbers"]


def test_wsg_r01_guard_rejects_unconfirmed_ocr_rule_numbers():
    assert b.rule_number_guard(spec_forms.FAMILIES, spec_forms.VISUAL_CHECKS, spec_sources.SOURCES) == []
    fams = copy.deepcopy(spec_forms.FAMILIES)
    f3 = [f for f in fams if f["family_id"] == "FF-AFTPR08-F3"][0]
    f3["title"] = f3["title"].replace("rule 27", "rule 17")   # the original OCR misreading
    errs = b.rule_number_guard(fams, spec_forms.VISUAL_CHECKS, spec_sources.SOURCES)
    assert any("rule number 17 in FF-AFTPR08-F3" in e for e in errs)
    # removing the recorded image checks makes every hand-entered AFT rule number fail
    no_aft = [v for v in spec_forms.VISUAL_CHECKS if v["src"] != "AFTPR08-C7"]
    errs = b.rule_number_guard(spec_forms.FAMILIES, no_aft, spec_sources.SOURCES)
    assert {"FF-AFTPR08-F1", "FF-AFTPR08-F2", "FF-AFTPR08-F3"} <= {e.split(" in ")[1].split(" ")[0] for e in errs}


def test_wsg_r08_quote_verifier_rejects_non_verbatim_quotes():
    st = b.Store(b.DEFAULT_SCRATCH, b.DEFAULT_C7)
    fam = copy.deepcopy([f for f in spec_forms.FAMILIES if f["family_id"] == "FF-AR54-R46A-JA"][0])
    assert b.verify_quotes(fam, st) == []
    fam["requirement_quote"] = fam["requirement_quote"].replace("in such of the following forms as shall be appropriate", "in one of the following forms")
    assert b.verify_quotes(fam, st)


def test_wsg_r08_oath_quotes_per_rule(reg):
    p = prim_rows(reg)
    assert "as shall be appropriate" in p["FF-AR54-R46A-JA"]["requirement_language_as_printed"]
    assert "if so required by the Act" in p["FF-AR54-R140-WITNESS"]["requirement_language_as_printed"]
    assert p["FF-AR54-R9-ATTEST"]["requirement_language_as_printed"].startswith("AR 9(1) [AR54-IC p.4]")


def test_wsg_r02_r12_shall_rule_applied_mechanically(reg, summary):
    for fid, r in prim_rows(reg).items():
        if r["form_authority_type_candidate"] == "STATUTORY_PRESCRIBED":
            assert "shall" in r["requirement_language_as_printed"], fid
    p = prim_rows(reg)
    for fid in ("FF-AR54-APPV-FH", "FF-AFTPR08-F2", "FF-DPPR53-S2"):
        assert p[fid]["form_authority_type_candidate"] == "OTHER_OR_UNDETERMINED", fid
    assert p["FF-AR54-APPV-FH"]["status_category"] == "PERMISSIVE_USE_SPECIFIC_RULE"
    assert p["FF-DPPR53-S2"]["status_category"] == "MANDATORY_DOCUMENT_LIST"
    assert {x["family"] for x in summary["reclassified_in_remediation"]} >= {"FF-AR54-APPV-FH", "FF-AFTPR08-F2", "FF-DPPR53-S2"}


def test_wsg_r03_no_hierarchy_wording_and_ar4_caveat(reg):
    for name in ("FORM_DISCOVERY_REGISTER.csv", "FORM_FIELDS.csv", "SOURCE_COVERAGE.csv", "SUMMARY.json"):
        assert "permissive unless a specific rule" not in open(os.path.join(OUT, name), encoding="utf-8").read()
    for r in reg:
        if r["instrument"] == "Army Rules, 1954" and r["appendix_part_or_schedule"].startswith("Appendix"):
            assert "a deviation from such forms shall not, by reason only of such deviation, render invalid any charge" in r["cross_cutting_caveat_as_printed"]
        else:
            assert r["cross_cutting_caveat_as_printed"] == ""


def test_wsg_r04_r05_source_basis_and_mml_labels(reg, fields, summary):
    p = prim_rows(reg)
    for fid, r in p.items():
        assert r["source_basis"] in b.SOURCE_BASIS
        if r["source_basis"] == "MML_ONLY":
            assert r["field_set_version"] == "MML_ONLY_UNVERIFIED"
            if r["form_authority_type_candidate"] == "STATUTORY_PRESCRIBED":
                assert r["statutory_confirmation_status"].startswith("NOT_CONFIRMED_FROM_OFFICIAL_COPY"), fid
        if b.is_mml(r["source_key"]) and r["source_basis"] == "BOTH":
            assert r["field_set_version"].startswith("MML_VERSION_UNVERIFIED"), fid
    c = summary["counts"]
    assert sum(c["families_by_source_basis"].values()) == c["unique_form_families"]
    assert c["families_by_source_basis"]["MML_ONLY"] == sum(1 for r in p.values() if r["source_basis"] == "MML_ONLY")
    assert set(c["statutory_prescribed_mml_only_not_confirmed"]) == {fid for fid, r in p.items() if r["statutory_confirmation_status"].startswith("NOT_CONFIRMED")}
    f13 = [f for f in fields if f["field_id"] == "FF-AR54-APPIII-P2#F13"][0]
    assert f13["field_label_as_printed"] == "Findings" and "ABSENT_IN_OFFICIAL_COPY_PAGE_IMAGE" in f13["official_copy_presence"]
    assert any(q.startswith("FF-AR54-APPIII-P2#F13") for q in summary["field_divergence_queue"])


def test_wsg_r06_no_unconfirmed_negative_and_aft_2011_recorded(cov, reg):
    for r in cov:
        if r["coverage_state"] == "INSPECTED_NO_FORMS_FOUND":
            assert r["pages_visually_inspected"] and not r["pages_visually_inspected"].startswith("NONE"), r["coverage_id"]
        if r["coverage_method_limitation"].endswith("NOT_VISUALLY_CONFIRMED"):
            assert r["coverage_state"] == "PARTIAL"
    assert any(r["source_key"] == "AFTPRA11-C7" for r in cov)
    dep = prim_rows(reg)["FF-AFTPR08-F1"]["procedural_dependencies"]
    assert "12A" in dep and "NOT DETERMINED" in dep


def test_wsg_r07_scope_stated_and_air_force_navy_listed(cov, summary):
    assert "Army-first" in summary["scope_statement"]
    oos = [r for r in cov if r["scope_this_cycle"].startswith("OUT_OF_SCOPE")]
    assert any("Air Force Rules, 1969" in r["segment_label"] and r["holding"] == "NOT_HELD" for r in oos)
    assert any("Navy" in r["scope_this_cycle"] and r["holding"] == "NOT_HELD" for r in oos)
    readme = open(os.path.join(WS, "README.md"), encoding="utf-8").read()
    assert "Army-first" in readme


def test_wsg_r09_pinpoints(reg):
    p = prim_rows(reg)
    assert p["FF-AR54-APPIII-P2"]["prescribing_provision"].startswith("AR 22(3)(a)")
    assert p["FF-AR54-APPV-FI"]["requirement_language_as_printed"].startswith("AR 170B(1) [AR54-IC p.192]")
    assert p["FF-AR54-APPIII-SGCM"]["status_category"] == "PERMISSIVE_USE_SPECIFIC_RULE"


def test_wsg_r10_doc_ranges_bounded(reg):
    st = b.Store(b.DEFAULT_SCRATCH, b.DEFAULT_C7)
    for r in reg:
        if r["locator_type"] == "DOC_DERIVED_LINE" and r["locator_end"]:
            assert int(r["locator_end"]) <= st.load(r["source_key"])["line_count"], r["candidate_id"]
            assert r["locator_end_basis"] in ("END_OF_FILE", "NEXT_REGISTERED_OCCURRENCE_START_MINUS_1") or r["locator_end_basis"].startswith("CAPPED_AT_")


def test_wsg_r11_generic_labels_marked(fields):
    by_label = {f["field_label_as_printed"]: f for f in fields}
    assert by_label["Name"]["generic_label"] == "YES"
    assert by_label["Date offence was discovered"]["generic_label"] == "NO"
    assert all(f["match_method"].startswith("normalised whole-word match") for f in fields)
