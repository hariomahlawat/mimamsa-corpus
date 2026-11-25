"""Restricted-material exclusion rule (owner directive; register RM-001 onwards in config/restricted_material.json).

Every value used here is read from the register at test time. Nothing in app/ may hard-code a register entry:
test_no_register_value_is_hard_coded_in_app enforces that.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from mimamsa_contract.restricted import RestrictedConfigError, load_register, repository_root
from mimamsa_contract.rules import record_issues

APP_DIR = Path(__file__).resolve().parents[2]


def codes(issues):
    return {i.code for i in issues if i.severity == "error"}


def _items(register_path):
    return json.loads(Path(register_path).read_text(encoding="utf-8"))["items"]


def test_register_loads_and_is_not_empty(register):
    assert register.restriction_ids and register.sha256s and register.doc_ids
    assert all(rid.startswith("RM-") for rid in register.restriction_ids)


def test_missing_register_fails_closed(tmp_path):
    with pytest.raises(RestrictedConfigError):
        load_register(tmp_path / "absent.json")


def test_malformed_register_fails_closed(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text('{"items": [{"restriction_id": "RM-999", "source_sha256": "not-a-hash"}]}')
    with pytest.raises(RestrictedConfigError):
        load_register(p)
    p.write_text('{"items": []}')
    with pytest.raises(RestrictedConfigError):
        load_register(p)


def test_every_register_hash_doc_id_and_path_is_matched(register, register_path):
    for it in _items(register_path):
        assert register.is_restricted(sha256=it["source_sha256"])
        assert register.is_restricted(sha256=it["source_sha256"].upper())
        for d in it.get("derived_sha256", []):
            assert register.is_restricted(sha256=d)
        assert register.is_restricted(doc_id=it["doc_id"])
        assert register.is_restricted(doc_id=it["doc_id"] + "#s1")  # section-level records inherit the restriction
        for hp in it.get("hosted_paths", []):
            assert register.is_restricted(path=hp)
            assert register.is_restricted(path="./" + hp)
            assert register.is_restricted(path=hp.replace("/", "\\"))
        # a path that merely embeds the hash (e.g. a vault or derivative path) is caught too
        s = it["source_sha256"]
        assert register.is_restricted(path=f"vault/sha256/{s[:2]}/{s}")
        assert register.is_restricted(path=f"derived/{s}/v1/page-0001.png")


def test_unrelated_items_not_restricted(register, example):
    doc = example("document")
    assert not register.is_restricted(sha256=doc["source_copy"]["sha256"], doc_id=doc["doc_id"],
                                      path=doc["provenance"]["hf"]["path"])


def _restricted_doc(example, it):
    s = it["source_sha256"]
    doc = example("document")
    doc["source_copy"].update(sha256=s, vault_path=f"vault/sha256/{s[:2]}/{s}")
    return doc


def test_document_with_restricted_sha_rejected_even_if_flag_claims_eligible(example, register, register_path):
    for it in _items(register_path):
        doc = _restricted_doc(example, it)
        assert doc["restriction"]["eligibility"] == "ELIGIBLE_ALL_USERS"  # producer mislabelled it
        assert "RESTRICTED_MATERIAL" in codes(record_issues("document", doc, register, "x"))


def test_document_with_restricted_doc_id_rejected(example, register, register_path):
    for it in _items(register_path):
        doc = example("document")
        doc["doc_id"] = it["doc_id"]
        assert "RESTRICTED_MATERIAL" in codes(record_issues("document", doc, register, "x"))


def test_restricted_alternate_copy_or_hf_path_rejected(example, register, register_path):
    for it in _items(register_path):
        doc = example("document")
        doc["alternate_copy_sha256"] = [it["source_sha256"]]
        assert "RESTRICTED_MATERIAL" in codes(record_issues("document", doc, register, "x"))
        for hp in it.get("hosted_paths", []):
            doc = example("document")
            doc["provenance"]["hf"]["path"] = hp
            assert "RESTRICTED_MATERIAL" in codes(record_issues("document", doc, register, "x"))


def test_derived_text_of_restricted_copy_rejected(example, register, register_path):
    for it in _items(register_path):
        dt = example("derived_text")
        dt["source_copy_sha256"] = it["source_sha256"]
        assert "RESTRICTED_MATERIAL" in codes(record_issues("derived_text", dt, register, "x"))
        for d in it.get("derived_sha256", []):
            dt = example("derived_text")
            dt["text_sha256"] = d
            assert "RESTRICTED_MATERIAL" in codes(record_issues("derived_text", dt, register, "x"))


def test_candidate_anchored_in_restricted_copy_rejected(example, register, register_path):
    for it in _items(register_path):
        c = example("candidate_graph_edge")
        c["anchors"][0]["source_copy_sha256"] = it["source_sha256"]
        assert "RESTRICTED_MATERIAL" in codes(record_issues("candidate", c, register, "x"))
        c = example("candidate_graph_edge")
        c["source_doc_id"] = it["doc_id"]
        assert "RESTRICTED_MATERIAL" in codes(record_issues("candidate", c, register, "x"))


def test_self_declared_restricted_record_rejected(example, register):
    doc = example("document")
    doc["restriction"].update(eligibility="RESTRICTED", restriction_id="RM-999")
    assert "RESTRICTED_MATERIAL" in codes(record_issues("document", doc, register, "x"))


def test_issue_messages_do_not_echo_restricted_values(example, register, register_path):
    it = _items(register_path)[0]
    issues = record_issues("document", _restricted_doc(example, it), register, "x")
    for i in issues:
        assert it["source_sha256"] not in i.message and it["doc_id"] not in i.message


def test_no_register_value_is_hard_coded_in_app(register):
    """Single source of truth: no file under app/ may contain a register hash or doc_id."""
    needles = set(register.sha256s) | set(register.doc_ids)
    offenders = []
    for p in APP_DIR.rglob("*"):
        if not p.is_file() or "__pycache__" in p.parts or p.suffix in {".pyc"}:
            continue
        try:
            text = p.read_text(encoding="utf-8").lower()
        except UnicodeDecodeError:
            continue
        for n in needles:
            if n.lower() in text:
                offenders.append(p.relative_to(APP_DIR).as_posix())
    assert offenders == [], f"register values hard-coded in: {sorted(set(offenders))}"


def test_parity_with_repository_guard_when_integrated(register, register_path):
    """After integration scripts/restricted_material.py exists; both guards must agree on every register item."""
    guard = repository_root() / "scripts" / "restricted_material.py"
    if not guard.is_file():
        pytest.skip("scripts/restricted_material.py not on this branch yet (governance branch not integrated)")
    spec = importlib.util.spec_from_file_location("repo_restricted_material", guard)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for it in _items(register_path):
        probes = [dict(sha256=it["source_sha256"]), dict(doc_id=it["doc_id"])] + \
                 [dict(path=hp) for hp in it.get("hosted_paths", [])] + [dict(sha256="0" * 64), dict(doc_id="act-x")]
        for kw in probes:
            assert mod.is_restricted(**kw) == register.is_restricted(**kw), kw
