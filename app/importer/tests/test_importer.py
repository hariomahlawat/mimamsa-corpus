"""Importer source-fidelity tests (ASR-E05), feeding the PR #54 DA-01/03/04/35 fixture conditions."""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from da_cases import (ALT, DOC_ID, SOURCE, Harness, candidate, derived, document, h, observations,  # noqa: E402
                      text_file)
from mimamsa_importer import active_generation, servable  # noqa: E402

DERIV = f"{DOC_ID}@synthetic-extract/0.0.1"


@pytest.fixture
def hn(tmp_path):
    return Harness(tmp_path)


def vault_files(site):
    v = site / "vault"
    return sorted(p.name for p in v.rglob("*") if p.is_file()) if v.exists() else []


# ---- DA-01 exact bytes, SHA-256, size, vault key, page count
def test_da01_control_activates_and_stores_exact_bytes(hn, tmp_path):
    site = tmp_path / "site"
    r = hn.run(hn.bundle(cands=[candidate()]), site)
    assert r.activated, r.refused_reasons
    stored = site / "vault/sha256" / h(SOURCE)[:2] / h(SOURCE)
    assert stored.read_bytes() == SOURCE
    assert servable(site, "documents", DOC_ID) and servable(site, "derived_text", DERIV) and servable(site, "candidates", "toy:edge:001")


@pytest.mark.parametrize("case", ["unbound-original", "missing-original", "size-mismatch", "page-count-mismatch"])
def test_da01_mismatch_refuses_activation_and_keeps_previous(hn, tmp_path, case):
    site = tmp_path / "site"
    assert hn.run(hn.bundle(), site).activated
    before, vault_before = (site / "ACTIVE").read_text(), vault_files(site)
    if case == "unbound-original":
        b = hn.bundle(copies=[ALT])
    elif case == "missing-original":
        b = hn.bundle(copies=[])
    elif case == "size-mismatch":
        d = document()
        d["source_copy"]["bytes"] = len(SOURCE) + 5
        b = hn.bundle(docs=[d])
    else:
        d = document(page_count=2)
        b = hn.bundle(docs=[d])
    r = hn.run(b, site)
    assert not r.activated and r.refused_reasons
    assert (site / "ACTIVE").read_text() == before and vault_files(site) == vault_before
    assert any(u["kind"] == "document" for u in r.unresolved)


def test_da01_first_import_refused_leaves_nothing_servable(hn, tmp_path):
    site = tmp_path / "site"
    r = hn.run(hn.bundle(copies=[ALT]), site)
    assert not r.activated and active_generation(site) is None and vault_files(site) == []
    assert not servable(site, "documents", DOC_ID)


def _pdf(pages: int) -> bytes:
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument.new()
    for _ in range(pages):
        doc.new_page(200, 200)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_pdf_page_count_measured_from_bytes(hn, tmp_path):
    pdf = _pdf(2)
    ok = hn.run(hn.bundle(docs=[document(pdf, mime="application/pdf", page_count=2)], copies=[pdf],
                          derived_recs=[], texts={}), tmp_path / "s1")
    assert ok.activated, ok.refused_reasons
    bad = hn.run(hn.bundle(docs=[document(pdf, mime="application/pdf", page_count=3)], copies=[pdf],
                           derived_recs=[], texts={}), tmp_path / "s2")
    assert not bad.activated and "page count mismatch" in bad.refused_reasons[0]


# ---- DA-03 corruption and unopenable source
def test_da03_corrupt_bundle_refused_previous_generation_serves(hn, tmp_path):
    site = tmp_path / "site"
    assert hn.run(hn.bundle(), site).activated
    before = (site / "ACTIVE").read_text()
    r = hn.run(hn.bundle(flip=True), site)
    assert not r.activated and "CHECKSUM_MISMATCH" in r.contract_errors
    assert (site / "ACTIVE").read_text() == before and servable(site, "documents", DOC_ID)


def test_da03_unopenable_pdf_refused(hn, tmp_path):
    junk = b"%PDF-1.7 not really a pdf"
    r = hn.run(hn.bundle(docs=[document(junk, mime="application/pdf")], copies=[junk], derived_recs=[], texts={}),
               tmp_path / "site")
    assert not r.activated and "cannot be verified" in r.refused_reasons[0]


# ---- DA-04 derivative identity, page and passage bounds
@pytest.mark.parametrize("mutate,reason", [
    (lambda d: d["passages"][0].__setitem__("char_end", len(SOURCE) + 1), "offsets outside its page"),
    (lambda d: d["pages"][0].__setitem__("char_count", len(SOURCE) - 1), "char_count"),
    (lambda d: d["passages"][0].__setitem__("text_sha256", "0" * 64), "text hash mismatch"),
    (lambda d: d.__setitem__("text_sha256", "0" * 64), "SHA-256 mismatch"),
    (lambda d: d.__setitem__("source_copy_sha256", h(ALT)), "declared source"),
], ids=["outside-page", "char-count", "passage-hash", "text-hash", "wrong-source"])
def test_da04_derivative_mismatch_quarantined_not_served(hn, tmp_path, mutate, reason):
    d = derived()
    mutate(d)
    site = tmp_path / "site"
    r = hn.run(hn.bundle(derived_recs=[d]), site)
    assert r.activated  # sources verified; only the derivative is quarantined
    q = [u for u in r.unresolved if u["kind"] == "derived_text"]
    assert q and any(reason in x for x in q[0]["reasons"])
    assert not servable(site, "derived_text", DERIV)
    assert active_generation(site)["quarantine"]


def test_da04_page_outside_physical_pages(hn, tmp_path):
    d = derived()
    d["pages"].append({"page": 2, "method": "ocr", "char_count": 0, "low_confidence": True})
    r = hn.run(hn.bundle(derived_recs=[d]), tmp_path / "site")
    assert any("not a physical page" in x for u in r.unresolved for x in u["reasons"])


def test_da04_missing_text_file(hn, tmp_path):
    r = hn.run(hn.bundle(texts={}), tmp_path / "site")
    assert any("not bundled" in x for u in r.unresolved for x in u["reasons"])


def test_bound_span_to_quarantined_derivative_is_quarantined(hn, tmp_path):
    d = derived()
    d["passages"][0]["char_end"] = len(SOURCE) + 1
    site = tmp_path / "site"
    r = hn.run(hn.bundle(derived_recs=[d], cands=[candidate()]), site)
    assert "toy:edge:001" not in r.verified["candidates"] and not servable(site, "candidates", "toy:edge:001")


# ---- DA-35 anchor binding
def test_da35_cross_bound_anchor_quarantined(hn, tmp_path):
    cross = candidate(bound=False)
    cross["anchors"][0].update(page=99, source_copy_sha256=h(ALT))
    site = tmp_path / "site"
    r = hn.run(hn.bundle(docs=[document(), document(ALT, "toy-blue-form-alternate")], copies=[SOURCE, ALT],
                         cands=[cross]), site)
    reasons = [x for u in r.unresolved if u["id"] == "toy:edge:001" for x in u["reasons"]]
    assert "anchor copy is not the source document's copy" in reasons
    assert any("not a physical page" in x for x in reasons)
    assert not servable(site, "candidates", "toy:edge:001")


def test_da35_page_beyond_copy_rejected_even_on_own_copy(hn, tmp_path):
    c = candidate(bound=False)
    c["anchors"][0]["page"] = 99
    r = hn.run(hn.bundle(cands=[c]), tmp_path / "site")
    assert "toy:edge:001" not in r.verified["candidates"]


def test_da35_retains_producing_commit_and_passage_hash(hn, tmp_path):
    site = tmp_path / "site"
    hn.run(hn.bundle(cands=[candidate()]), site)
    ev = active_generation(site)["candidate_evidence"]["toy:edge:001"]
    assert ev["artefact_commit"] and ev["anchors"][0]["text_sha256"] == h(SOURCE)


# ---- restricted material and never-serve-unverified
def test_restricted_material_refused_before_any_write(hn, tmp_path):
    site = tmp_path / "site"
    r = hn.run(hn.bundle(docs=[document(doc_id="toy-excluded-id")]), site)
    assert not r.activated and "RESTRICTED_MATERIAL" in r.contract_errors and vault_files(site) == []


def test_unknown_items_never_servable(tmp_path):
    assert not servable(tmp_path / "nosite", "documents", DOC_ID)


def test_observation_record_matches_pr54_expected_fields(tmp_path):
    """Observed fields equal PR #54 adapter_expected_evidence for the fields this importer can observe."""
    expected = {
        "DA-01": {"original_bytes_equal": True, "sha256_equal": True, "vault_key_matches": True},
        "DA-03": {"corrupt_rejected": True, "active_generation_unchanged": True, "prior_original_unchanged": True,
                  "unopenable_source_rejected": True},
        "DA-04": {"ocr_quote_enabled": False, "out_of_range_anchor_rejected": True},
        "DA-35": {"source_copy_hash_verified": True, "page_anchor_verified": True, "producing_commit_retained": True,
                  "passage_hash_retained": True, "broken_binding_rejected": True},
    }
    assert observations(tmp_path) == expected


def _real_register(tmp_path):
    """RM register from config/restricted_material.json (repo copy, $MIMAMSA_RESTRICTED_MATERIAL_CONFIG or the
    governance branch before integration). Fails rather than skips when unavailable."""
    import os
    import subprocess
    from mimamsa_contract.restricted import load_register, repository_root
    env = os.environ.get("MIMAMSA_RESTRICTED_MATERIAL_CONFIG")
    repo = repository_root() / "config" / "restricted_material.json"
    if env:
        return load_register(env)
    if repo.is_file():
        return load_register(repo)
    for ref in ("claude/c13-gov", "origin/claude/c13-gov", "origin/legal-knowledge/v2.5-staging"):
        try:
            data = subprocess.run(["git", "-C", str(repository_root()), "show", f"{ref}:config/restricted_material.json"],
                                  check=True, capture_output=True).stdout
            p = tmp_path / "rm.json"
            p.write_bytes(data)
            return load_register(p)
        except subprocess.CalledProcessError:
            continue
    pytest.fail("restricted-material register unavailable")


def test_rm001_document_never_imported(hn, tmp_path):
    reg = _real_register(tmp_path)
    rm = json.loads(reg.config_path.read_text())["items"][0]
    site = tmp_path / "site"
    r = hn.run(hn.bundle(docs=[document(doc_id=rm["doc_id"])]), site, register=reg)
    assert not r.activated and "RESTRICTED_MATERIAL" in r.contract_errors
    assert vault_files(site) == [] and active_generation(site) is None
