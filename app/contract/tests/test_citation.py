"""F12: citation copy outputs a legal citation, never internal identifiers."""
from __future__ import annotations

from mimamsa_contract.citation import format_legal_citation, internal_reference


def _doc(example):
    d = example("document")
    d["judicial"].update(court="Synthetic Tribunal", parties={"petitioner": "A. Example", "respondent": "Union of Example"},
                         neutral_citation="2099 EXAMPLE 1")
    d["issue_date"] = "2099-01-15"
    return d


def test_legal_citation_format(example):
    s = format_legal_citation(_doc(example), page=12, paragraph_label="7")
    assert s == "A. Example v. Union of Example, 2099 EXAMPLE 1 (Synthetic Tribunal, 15 January 2099), para 7"


def test_page_pinpoint_when_no_paragraph(example):
    assert format_legal_citation(_doc(example), page=12).endswith(", p. 12")


def test_no_internal_ids_in_citation(example):
    d = _doc(example)
    s = format_legal_citation(d, page=3)
    assert d["doc_id"] not in s and d["source_copy"]["sha256"][:12] not in s and "R13-" not in s


def test_llm_derived_fields_excluded(example):
    d = _doc(example)
    d["field_origin"]["neutral_citation"] = "llm"
    assert "2099 EXAMPLE 1" not in format_legal_citation(d, page=1)


def test_missing_parts_omitted_not_guessed(example):
    d = example("document")
    d["title"] = None
    d["judicial"]["case_numbers"] = []
    d["number"] = None
    assert format_legal_citation(d, page=2) == "[title not printed], p. 2"


def test_internal_reference_is_separate(example):
    d = _doc(example)
    r = internal_reference(d, page=3, release_id="R13-example-20261125-00000000")
    assert d["doc_id"] in r and "R13-" in r
