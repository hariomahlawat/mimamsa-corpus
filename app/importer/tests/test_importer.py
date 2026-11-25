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
from mimamsa_importer import active_generation, cite, held_copies, servable  # noqa: E402


def sv(*a):
    return servable(*a, exclusions=None)

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
    assert sv(site, "documents", DOC_ID) and sv(site, "derived_text", DERIV) and sv(site, "candidates", "toy:edge:001")


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
    assert not sv(site, "documents", DOC_ID)


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
    assert (site / "ACTIVE").read_text() == before and sv(site, "documents", DOC_ID)


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
    assert not sv(site, "derived_text", DERIV)
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
    assert "toy:edge:001" not in r.verified["candidates"] and not sv(site, "candidates", "toy:edge:001")


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
    assert not sv(site, "candidates", "toy:edge:001")


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
    assert not sv(tmp_path / "nosite", "documents", DOC_ID)


def test_observation_record_matches_pr54_expected_fields(tmp_path):
    """Observed fields equal PR #54 adapter_expected_evidence for the fields this importer can observe."""
    expected = {
        "DA-01": {"original_bytes_equal": True, "sha256_equal": True, "vault_key_matches": True},
        "DA-03": {"corrupt_rejected": True, "active_generation_unchanged": True, "prior_original_unchanged": True,
                  "unopenable_source_rejected": True},
        "DA-04": {"out_of_range_anchor_rejected": True},
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


# ================= review E1-E10 =================
from da_cases import REGISTER_TEXT, REPLACEMENT  # noqa: E402


def _bound(**kw):
    c = candidate()
    c["anchors"][0].update(kw)
    return c


@pytest.mark.parametrize("kw", [
    {"passage_id": None, "char_start": 10000, "char_end": 20000},   # E1 reviewer probe
    {"passage_id": None, "char_start": None, "char_end": 9999},     # end only
    {"passage_id": None, "char_start": 60, "char_end": None},       # start only, beyond page
    {"char_start": 5, "char_end": len(SOURCE) + 3},                 # with passage, beyond passage
])
def test_e1_bound_offsets_range_checked_with_or_without_passage(hn, tmp_path, kw):
    site = tmp_path / "site"
    r = hn.run(hn.bundle(cands=[_bound(**kw)]), site)
    assert "toy:edge:001" not in r.verified["candidates"] and not sv(site, "candidates", "toy:edge:001")


def test_e1_valid_offsets_without_passage_accepted_and_hash_recomputed(hn, tmp_path):
    site = tmp_path / "site"
    r = hn.run(hn.bundle(cands=[_bound(passage_id=None, char_start=0, char_end=10, text_sha256=h(SOURCE[:10]))]), site)
    assert "toy:edge:001" in r.verified["candidates"]
    a = active_generation(site)["candidate_evidence"]["toy:edge:001"]["anchors"][0]
    assert a["text_sha256"] == h(SOURCE[:10]) and a["page_only"] is False


def test_e2_anchor_text_hash_must_match_derivative(hn, tmp_path):
    site = tmp_path / "site"
    r = hn.run(hn.bundle(cands=[_bound(text_sha256="e" * 64)]), site)
    assert any("anchor text hash" in x for u in r.unresolved for x in u["reasons"])
    assert not sv(site, "candidates", "toy:edge:001")


def test_e3_pdf_declared_as_text_refused(hn, tmp_path):
    from test_importer import _pdf
    pdf = _pdf(1) + b"\f\f\f\f"
    r = hn.run(hn.bundle(docs=[document(pdf, mime="text/plain", page_count=5)], copies=[pdf], derived_recs=[], texts={}),
               tmp_path / "site")
    assert not r.activated and "content type mismatch" in r.refused_reasons[0]


def test_e3_text_declared_as_pdf_refused(hn, tmp_path):
    r = hn.run(hn.bundle(docs=[document(mime="application/pdf")]), tmp_path / "site")
    assert not r.activated and "content type mismatch" in r.refused_reasons[0]


def test_e4_older_release_replay_refused_using_site_sequence(hn, tmp_path):
    site = tmp_path / "site"
    old = hn.bundle()          # sequence 1
    new = hn.bundle()          # sequence 2
    assert hn.run(new, site).activated
    r = hn.run(old, site)      # caller supplies no sequence: the importer reads the site's
    assert not r.activated and "DOWNGRADE_OR_REPLAY" in r.contract_errors
    assert active_generation(site)["release_sequence"] == 2


def test_e4_identical_reimport_is_noop_and_never_rewrites(hn, tmp_path):
    site = tmp_path / "site"
    b = hn.bundle()
    assert hn.run(b, site).activated
    gen_file = site / "generations" / active_generation(site)["release_id"] / "generation.json"
    before = (gen_file.read_bytes(), gen_file.stat().st_mtime_ns)
    r = hn.run(b, site)
    assert r.noop and not r.activated and (gen_file.read_bytes(), gen_file.stat().st_mtime_ns) == before


def test_e4_same_release_id_different_content_refused(hn, tmp_path):
    site = tmp_path / "site"
    assert hn.run(hn.bundle(release="R13-asr-toy-20900101-0000ffff"), site).activated
    r = hn.run(hn.bundle(release="R13-asr-toy-20900101-0000ffff", cands=[candidate()]), site)
    assert not r.activated and "never rewritten" in r.refused_reasons[0]


def test_e4_no_temporary_generation_left_behind(hn, tmp_path):
    site = tmp_path / "site"
    hn.run(hn.bundle(), site)
    assert not list((site / "generations").glob(".tmp-*")) and not (site / "ACTIVE.tmp").exists()


def _store_with(tmp_path, site, *, withdrawals=(), register_text=REGISTER_TEXT):
    import hashlib as _hl
    from mimamsa_contract.devbundle import new_dev_keypair, trust_list_for
    from mimamsa_contract.exclusions import ExclusionStore
    from mimamsa_contract.trust import parse_trust_list
    sk, pk = new_dev_keypair()
    trust = parse_trust_list(trust_list_for([(pk, "OWNER", ["register"])]))
    u = {"contract_version": "1.0.0", "record_kind": "exclusion_update", "sequence": 1, "issued_at": "2090-01-01T00:00:00Z",
         "register_sha256": _hl.sha256(register_text.encode()).hexdigest(), "register_json": register_text,
         "withdrawals": list(withdrawals)}
    b = json.dumps(u).encode()
    store = ExclusionStore(site / "exclusions")
    store.append(b, sk.sign(b), trust)
    return store.effective_state(trust)


def test_e5_servable_honours_withdrawal(hn, tmp_path):
    site = tmp_path / "site"
    hn.run(hn.bundle(cands=[candidate()]), site)
    state = _store_with(tmp_path, site, withdrawals=[{"doc_id": DOC_ID, "reason": "withdrawn upstream"}])
    for kind, item in (("documents", DOC_ID), ("derived_text", DERIV), ("candidates", "toy:edge:001")):
        assert not servable(site, kind, item, exclusions=state)
    assert not servable(site, "documents", DOC_ID, exclusions=None)  # store exists: None fails closed


def test_e5_servable_honours_restriction(hn, tmp_path):
    site = tmp_path / "site"
    hn.run(hn.bundle(), site)
    reg = json.dumps({"items": [{"restriction_id": "RM-998", "source_sha256": h(SOURCE), "doc_id": "toy-other",
                                 "hosted_paths": []}]})
    state = _store_with(tmp_path, site, register_text=reg)
    assert not servable(site, "documents", DOC_ID, exclusions=state)


def test_e6_da04_quote_flag_not_reported_as_observed(tmp_path):
    assert "ocr_quote_enabled" not in observations(tmp_path)["DA-04"]


# ---- E7/E8/E9 citation resolution through the importer's held copies
def _two_releases(hn, site):
    r1 = hn.run(hn.bundle(), site)
    repl = document(REPLACEMENT)  # same doc_id, new copy (different bytes/pagination)
    r2 = hn.run(hn.bundle(docs=[repl], copies=[REPLACEMENT], derived_recs=[], texts={}), site)
    assert r1.activated and r2.activated
    return h(SOURCE), h(REPLACEMENT)


def test_e8_cited_copy_superseded_in_later_release_still_opens_exactly(hn, tmp_path):
    site = tmp_path / "site"
    old, new = _two_releases(hn, site)
    res = cite(site, old[:12], DOC_ID, 1, exclusions=None)
    assert res == {"state": "CITED_COPY_ELIGIBLE_NOT_CURRENT", "copy": old, "page": 1, "current_copy": new}
    assert (site / "vault/sha256" / old[:2] / old).read_bytes() == SOURCE  # retained across generations
    assert cite(site, new[:12], DOC_ID, 1, exclusions=None)["state"] == "CITED_COPY_ELIGIBLE"


def test_e7_withdrawn_restricted_and_not_held_are_indistinguishable(hn, tmp_path):
    site = tmp_path / "site"
    old, _ = _two_releases(hn, site)
    withdrawn = cite(site, old[:12], DOC_ID, 1, exclusions=_store_with(tmp_path, site, withdrawals=[{"doc_id": DOC_ID, "reason": "withdrawn"}]))
    site2 = tmp_path / "site2"
    old2, _ = _two_releases(Harness(tmp_path / "h2"), site2)
    reg = json.dumps({"items": [{"restriction_id": "RM-998", "source_sha256": old2, "doc_id": "toy-other", "hosted_paths": []}]})
    restricted = cite(site2, old2[:12], DOC_ID, 1, exclusions=_store_with(tmp_path, site2, register_text=reg))
    not_held = cite(site, "f" * 12, DOC_ID, 1, exclusions=None)
    assert withdrawn == restricted == not_held == {"state": "CITED_COPY_UNAVAILABLE", "copy": None, "page": None}


def test_e9_page_beyond_copy_mismatch_and_ambiguity(hn, tmp_path):
    site = tmp_path / "site"
    old, new = _two_releases(hn, site)
    assert cite(site, old[:12], DOC_ID, 7, exclusions=None)["state"] == "CITED_PAGE_NOT_IN_COPY"
    assert cite(site, old[:12], "toy-some-other-doc", 1, exclusions=None)["state"] == "REFERENCE_MISMATCH"
    import mimamsa_importer.importer as imp
    held = held_copies(site)
    fake = dict(held)
    fake[old[:12] + "0" * 52] = dict(held[old])   # synthetic second copy sharing the 12-character prefix
    imp_held = imp.held_copies
    try:
        imp.held_copies = lambda s: fake
        assert cite(site, old[:12], DOC_ID, 1, exclusions=None)["state"] == "AMBIGUOUS_REFERENCE"
    finally:
        imp.held_copies = imp_held


def test_e10_unbound_span_fields_not_served(hn, tmp_path):
    site = tmp_path / "site"
    c = candidate(bound=False)
    c["anchors"][0].update(passage_id="p9-9", char_start=5000, char_end=6000)
    hn.run(hn.bundle(cands=[c]), site)
    a = active_generation(site)["candidate_evidence"]["toy:edge:001"]["anchors"][0]
    assert a["page_only"] is True and "passage_id" not in a and "char_start" not in a and a["text_sha256"] is None
    assert "span_stripped" in a


# ================= confirmation N1-N3 =================
import mimamsa_importer.importer as imp  # noqa: E402
from mimamsa_importer import ImporterError  # noqa: E402


def _active_site(hn, tmp_path, channel):
    site = tmp_path / f"site-{channel}"
    assert hn.run(hn.bundle(), site, channel=channel).activated
    return site


def test_n1_signed_channel_none_state_denies(hn, tmp_path):
    site = _active_site(hn, tmp_path, "signed")
    assert not servable(site, "documents", DOC_ID, exclusions=None)
    assert cite(site, h(SOURCE)[:12], DOC_ID, 1, exclusions=None)["state"] == "CITED_COPY_UNAVAILABLE"


def test_n1_unconfigured_site_denies(hn, tmp_path):
    site = tmp_path / "site"
    assert hn.run(hn.bundle(), site, channel=None).activated   # no SITE_CONFIG: default is "signed"
    assert not servable(site, "documents", DOC_ID, exclusions=None)
    assert cite(site, h(SOURCE)[:12], DOC_ID, 1, exclusions=None)["state"] == "CITED_COPY_UNAVAILABLE"


@pytest.mark.parametrize("store_state", ["empty_dir", "pending_only", "accepted_lost"])
def test_n1_store_without_accepted_state_denies_even_in_none_mode(hn, tmp_path, store_state):
    site = _active_site(hn, tmp_path, "none")
    assert servable(site, "documents", DOC_ID, exclusions=None)  # positive control: explicit none mode, no store
    (site / "exclusions").mkdir()
    if store_state == "pending_only":
        (site / "exclusions" / "pairs").mkdir()
        (site / "exclusions" / "pairs" / "00000001.json").write_text("{}")
    if store_state == "accepted_lost":
        (site / "exclusions" / "LOCK").write_text("stale")
    assert not servable(site, "documents", DOC_ID, exclusions=None)
    assert cite(site, h(SOURCE)[:12], DOC_ID, 1, exclusions=None)["state"] == "CITED_COPY_UNAVAILABLE"


def test_n1_generation_must_record_none_mode(hn, tmp_path):
    site = tmp_path / "site"
    assert hn.run(hn.bundle(), site, channel="signed").activated
    imp.configure_site(site, exclusion_channel="none")       # flipped after the generation was written
    assert not servable(site, "documents", DOC_ID, exclusions=None)


def test_n1_non_state_object_denies(hn, tmp_path):
    site = _active_site(hn, tmp_path, "none")
    assert not servable(site, "documents", DOC_ID, exclusions={"withdrawn": []})
    assert cite(site, h(SOURCE)[:12], DOC_ID, 1, exclusions="nothing")["state"] == "CITED_COPY_UNAVAILABLE"


def test_n1_cite_honours_withdrawal_with_store(hn, tmp_path):
    site = _active_site(hn, tmp_path, "signed")
    state = _store_with(tmp_path, site, withdrawals=[{"doc_id": DOC_ID, "reason": "withdrawn"}])
    assert cite(site, h(SOURCE)[:12], DOC_ID, 1, exclusions=state)["state"] == "CITED_COPY_UNAVAILABLE"
    assert cite(site, h(SOURCE)[:12], DOC_ID, 1, exclusions=None)["state"] == "CITED_COPY_UNAVAILABLE"


class _Crash(Exception):
    pass


def _crash_at(monkeypatch, point):
    def hook(name):
        if name == point:
            raise _Crash(name)
    monkeypatch.setattr(imp, "_crashpoint", hook)


@pytest.mark.parametrize("point", ["after_vault_object", "before_rename", "before_active"])
def test_n2_crash_then_retry_succeeds_and_nothing_held_early(hn, tmp_path, monkeypatch, point):
    site = tmp_path / "site"
    assert hn.run(hn.bundle(), site).activated                     # generation 1 (SOURCE)
    b2 = hn.bundle(docs=[document(REPLACEMENT)], copies=[REPLACEMENT], derived_recs=[], texts={})
    _crash_at(monkeypatch, point)
    with pytest.raises(_Crash):
        hn.run(b2, site)
    # never-activated copy is not held, not citable, and generation 1 still serves
    assert active_generation(site)["release_sequence"] == 1
    assert h(REPLACEMENT) not in held_copies(site)
    assert cite(site, h(REPLACEMENT)[:12], DOC_ID, 1, exclusions=None)["state"] == "CITED_COPY_UNAVAILABLE"
    assert sv(site, "documents", DOC_ID)
    monkeypatch.setattr(imp, "_crashpoint", lambda name: None)
    r = hn.run(b2, site)                                            # retry of the identical bundle
    assert r.activated and active_generation(site)["release_sequence"] == 2
    assert r.resumed == (point == "before_active")
    assert h(REPLACEMENT) in held_copies(site)
    assert not list((site / "generations").glob(".tmp-*"))
    if point == "before_rename":
        assert any((site / "quarantine" / "generations").iterdir())  # stale temp dir quarantined, not deleted


def test_n2_different_bundle_after_crash_quarantines_pending_generation(hn, tmp_path, monkeypatch):
    site = tmp_path / "site"
    assert hn.run(hn.bundle(), site).activated
    b2 = hn.bundle(docs=[document(REPLACEMENT)], copies=[REPLACEMENT], derived_recs=[], texts={})
    _crash_at(monkeypatch, "before_active")
    with pytest.raises(_Crash):
        hn.run(b2, site)
    monkeypatch.setattr(imp, "_crashpoint", lambda name: None)
    b3 = hn.bundle(docs=[document(REPLACEMENT)], copies=[REPLACEMENT], derived_recs=[], texts={})
    r = hn.run(b3, site)
    assert r.activated and not r.resumed and any((site / "quarantine" / "generations").iterdir())


def test_n2_storage_failure_is_typed(hn, tmp_path, monkeypatch):
    site = tmp_path / "site"
    assert hn.run(hn.bundle(), site).activated
    b2 = hn.bundle(docs=[document(REPLACEMENT)], copies=[REPLACEMENT], derived_recs=[], texts={})
    real = imp.os.replace

    def failing(src, dst):
        if str(dst).endswith("ACTIVE"):
            raise PermissionError("denied")
        return real(src, dst)
    monkeypatch.setattr(imp.os, "replace", failing)
    with pytest.raises(ImporterError):
        hn.run(b2, site)


def test_n3_ambiguity_ignores_excluded_copies(hn, tmp_path, monkeypatch):
    site = _active_site(hn, tmp_path, "signed")
    old = h(SOURCE)
    other = old[:12] + "0" * 52
    held = dict(held_copies(site))
    held[other] = {"doc_id": "toy-excluded-other", "page_count": 1, "first_release": "x"}
    monkeypatch.setattr(imp, "held_copies", lambda s: held)
    state = _store_with(tmp_path, site, withdrawals=[{"source_copy_sha256": other, "reason": "withdrawn"}])
    assert cite(site, old[:12], DOC_ID, 1, exclusions=state)["state"] == "CITED_COPY_ELIGIBLE"
