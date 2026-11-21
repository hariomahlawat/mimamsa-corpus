import copy
import json
from pathlib import Path

import pytest

from pipeline.schemas import errors, validator

FIX = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("kind", ["document", "section", "relation"])
def test_schemas_are_valid_jsonschema(kind):
    validator(kind)


@pytest.mark.parametrize(
    "kind,fixture",
    [
        ("document", "doc_act_army_1950.json"),
        ("document", "doc_judgment_sc.json"),
        ("section", "section_army_1950_s75.json"),
        ("relation", "relation_unresolved.json"),
    ],
)
def test_fixtures_validate(kind, fixture):
    assert errors(kind, load(fixture)) == []


def test_judgment_requires_judgment_fields():
    rec = load("doc_judgment_sc.json")
    del rec["case_numbers"]
    assert any("case_numbers" in e for e in errors("document", rec))


def test_act_must_not_carry_judgment_fields():
    rec = load("doc_act_army_1950.json")
    rec["judges"] = ["X"]
    assert errors("document", rec)


def test_missing_values_are_null_not_absent():
    rec = load("doc_act_army_1950.json")
    del rec["effective_date"]
    assert any("effective_date" in e for e in errors("document", rec))


def test_bad_doc_id_rejected():
    rec = load("doc_act_army_1950.json")
    rec["doc_id"] = "Army Act 1950"
    assert errors("document", rec)


def test_ocr_confidence_only_with_ocr():
    rec = load("doc_act_army_1950.json")
    rec["ocr_confidence"] = 80.0  # text_method is pdf_text
    assert errors("document", rec)


def test_relation_needs_target_or_raw():
    rel = load("relation_unresolved.json")
    rel["target_ref_raw"] = None
    assert errors("relation", rel)


def test_human_verified_needs_reviewer():
    rel = load("relation_unresolved.json")
    rel["confidence"] = "human_verified"
    assert errors("relation", rel)
    rel["reviewed_by"] = "HA"
    assert errors("relation", rel) == []


def test_relation_source_must_match_doc():
    rec = load("doc_judgment_sc.json")
    rec = copy.deepcopy(rec)
    rec["relations"][0]["source_doc_id"] = "act-army-1950"
    assert any("must equal doc_id" in e for e in errors("document", rec))


def test_bad_dates_rejected():
    rec = load("doc_act_army_1950.json")
    rec["issue_date"] = "20-05-1950"
    assert errors("document", rec)


def test_unknown_topic_rejected():
    rec = load("doc_judgment_sc.json")
    rec["topics"] = ["made_up_topic"]
    assert errors("document", rec)


def test_format_checks_are_active():
    # Guards against rfc3339-validator / rfc3987 silently going missing.
    rec = load("doc_act_army_1950.json")
    rec["retrieved_at"] = "yesterday"
    rec["source_url"] = "not a url"
    errs = errors("document", rec)
    assert any("retrieved_at" in e for e in errs)
    assert any("source_url" in e for e in errs)
