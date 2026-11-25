from __future__ import annotations

import json

import pytest

import mimamsa_contract.bundle as bundle_mod
from mimamsa_contract.__main__ import main as cli_main
from mimamsa_contract.bundle import validate_bundle
from mimamsa_contract.devbundle import new_dev_keypair, trust_list_for, write_bundle
from mimamsa_contract.trust import parse_trust_list


@pytest.fixture
def owner_keys():
    # Disposable test key standing in for an owner-held key. No production key exists in this repository.
    return new_dev_keypair()


@pytest.fixture
def trust(owner_keys):
    return parse_trust_list(trust_list_for([(owner_keys[1], "OWNER", ["release", "register", "trust_list"])]))


@pytest.fixture
def make_bundle(tmp_path, example, register, owner_keys):
    sk, pk = owner_keys

    def _make(name="b", *, documents=None, derived=None, candidates=None, extra_files=None, manifest_edit=None,
              sign=True, dev_key=False, signing_key=None, **records):
        m = example("release_manifest")
        m["restricted_material"]["config_sha256"] = register.config_sha256
        m["restricted_material"]["restriction_ids_applied"] = sorted(register.restriction_ids)
        if manifest_edit:
            manifest_edit(m)
        return write_bundle(
            tmp_path / name, m,
            documents=[example("document")] if documents is None else documents,
            derived=[example("derived_text")] if derived is None else derived,
            candidates=[example("candidate_graph_edge"), example("candidate_outcome")] if candidates is None else candidates,
            extra_files=extra_files, signing_key=(signing_key or sk) if sign else None, public_key_raw=pk,
            dev_key=dev_key, **records)

    return _make


def codes(report):
    return {i.code for i in report.errors}


def prod(root, trust, register, **kw):
    if "current_release_sequence" not in kw and not kw.get("rollback"):
        kw["current_release_sequence"] = 0  # first installation
    return validate_bundle(root, trust_list=trust, register=register, **kw)


# ---- positive controls
def test_clean_signed_bundle_accepted_in_production(make_bundle, trust, register):
    rep = prod(make_bundle(), trust, register)
    assert rep.ok, [str(i) for i in rep.errors]
    assert rep.signature_verified and rep.checked_records == 4


def test_development_mode_with_bare_key(make_bundle, owner_keys, register):
    rep = validate_bundle(make_bundle(dev_key=True), trusted_public_key=owner_keys[1], mode="development", register=register)
    assert rep.ok, [str(i) for i in rep.errors]


# ---- F05 signature trust
def test_production_requires_trust_list(make_bundle, owner_keys, register):
    rep = validate_bundle(make_bundle(), trusted_public_key=owner_keys[1], register=register, current_release_sequence=0)
    assert "TRUST_LIST_REQUIRED" in codes(rep)


def test_production_rejects_dev_key_id(make_bundle, trust, register):
    rep = prod(make_bundle(dev_key=True), trust, register)
    assert "SIGNATURE_DEV_KEY_IN_PRODUCTION" in codes(rep)


def test_production_rejects_development_holder_key(make_bundle, owner_keys, register):
    t = parse_trust_list(trust_list_for([(owner_keys[1], "DEVELOPMENT", ["release"])]))
    rep = prod(make_bundle(dev_key=True), t, register)
    assert "SIGNATURE_DEV_KEY_IN_PRODUCTION" in codes(rep) and not rep.signature_verified


def test_unsigned_rejected_and_dev_flag_only_in_development(make_bundle, trust, register):
    root = make_bundle(sign=False)
    assert "SIGNATURE_MISSING" in codes(prod(root, trust, register))
    assert "MODE_INVALID" in codes(validate_bundle(root, trust_list=trust, register=register, allow_unsigned_dev=True, current_release_sequence=0))
    assert validate_bundle(root, register=register, mode="development", allow_unsigned_dev=True).ok


def test_wrong_key_rejected(make_bundle, trust, register):
    other_sk, _ = new_dev_keypair()
    assert "SIGNATURE_INVALID" in codes(prod(make_bundle(signing_key=other_sk), trust, register))


def test_key_not_trusted_for_release_purpose_rejected(make_bundle, owner_keys, register):
    t = parse_trust_list(trust_list_for([(owner_keys[1], "OWNER", ["register"])]))
    assert "SIGNATURE_INVALID" in codes(prod(make_bundle(), t, register))


def test_fail_fast_no_record_parsed_after_bad_signature(make_bundle, trust, register):
    root = make_bundle()
    p = root / "SHA256SUMS.sig"
    b = bytearray(p.read_bytes())
    b[0] ^= 1
    p.write_bytes(bytes(b))
    rep = prod(root, trust, register)
    assert "SIGNATURE_INVALID" in codes(rep)
    assert rep.checked_records == 0 and rep.checked_files == 0


def test_fail_fast_no_record_parsed_after_checksum_failure(make_bundle, trust, register):
    root = make_bundle()
    p = root / "data" / "documents.jsonl"
    data = bytearray(p.read_bytes())
    data[10] ^= 0x01
    p.write_bytes(bytes(data))
    rep = prod(root, trust, register)
    assert "CHECKSUM_MISMATCH" in codes(rep) and rep.checked_records == 0


def test_tampered_sums_breaks_signature(make_bundle, trust, register):
    root = make_bundle()
    s = root / "SHA256SUMS"
    s.write_text(s.read_text() + "\n")
    assert "SIGNATURE_INVALID" in codes(prod(root, trust, register))


def test_manifest_key_id_must_be_verifying_key(tmp_path, example, register, owner_keys, trust):
    m = example("release_manifest")
    m["restricted_material"]["config_sha256"] = register.config_sha256
    m["restricted_material"]["restriction_ids_applied"] = sorted(register.restriction_ids)
    m["signature"]["key_id"] = "a" * 64  # declares a key other than the one that signs
    root = write_bundle(tmp_path / "km", m, documents=[example("document")], derived=[], candidates=[],
                        signing_key=owner_keys[0], public_key_raw=None)
    assert "SIGNATURE_KEY_MISMATCH" in codes(prod(root, trust, register))


# ---- integrity and paths (F04)
def test_unlisted_file_rejected(make_bundle, trust, register):
    root = make_bundle()
    (root / "data" / "smuggled.pdf").write_bytes(b"%PDF-1.4")
    assert "UNLISTED_FILE" in codes(prod(root, trust, register))


def test_symlink_rejected(make_bundle, trust, register, tmp_path):
    root = make_bundle()
    target = tmp_path / "outside.txt"
    target.write_text("x")
    (root / "data" / "link").symlink_to(target)
    assert "SYMLINK_IN_BUNDLE" in codes(prod(root, trust, register))


def test_reparse_point_rejected(make_bundle, trust, register, monkeypatch):
    """Junctions cannot be created on the Linux CI host; the reparse detector is exercised through its hook."""
    root = make_bundle()
    real = bundle_mod.is_link_or_reparse
    monkeypatch.setattr(bundle_mod, "is_link_or_reparse", lambda p: p.name == "documents.jsonl" or real(p))
    assert "SYMLINK_IN_BUNDLE" in codes(prod(root, trust, register))


@pytest.mark.parametrize("bad", [
    "data/notes.txt:hidden",          # NTFS alternate data stream
    "data/CON.txt", "data/nul", "data/com1.json", "data/LPT9.txt", "data/aux",   # device names
    "data/documents.jsonl.", "data/trailing ",                                  # trailing dot / space aliases
    "data/" + "x" * 230,                                                        # overlong
    "data/a?b.txt", "data/a|b.txt",                                             # invalid characters
])
def test_windows_path_hazards_rejected(make_bundle, trust, register, bad):
    root = make_bundle(extra_files={bad: (b"x", "other")})
    assert "PATH_HAZARD" in codes(prod(root, trust, register)), bad


def test_case_collision_rejected(make_bundle, trust, register):
    root = make_bundle(extra_files={"data/Readme.txt": (b"a", "other"), "data/README.txt": (b"b", "other")})
    assert "CASE_COLLISION" in codes(prod(root, trust, register))


def test_unc_and_absolute_rejected_by_path_rule():
    from mimamsa_contract.paths import path_hazard
    for bad in ["//server/share/x", "\\\\server\\share", "/abs", "C:/x", "a/../b", "a/./b", "a//b"]:
        assert path_hazard(bad), bad
    assert path_hazard("data/documents.jsonl") is None


def test_working_session_files_never_in_bundle(make_bundle, trust, register):
    root = make_bundle(extra_files={"sessions/u1/draft.pdf": (b"%PDF", "other")})
    assert "WORKING_DOCUMENT_IN_BUNDLE" in codes(prod(root, trust, register))


# ---- parsing hardening (F15)
def test_duplicate_json_keys_rejected(make_bundle, trust, register, example, tmp_path):
    root = make_bundle(extra_files={"data/extra_docs.jsonl": (b'{"doc_id":"a","doc_id":"b"}\n', "documents_jsonl")})
    m = json.loads((root / "RELEASE.json").read_text())
    assert any(f["path"] == "data/extra_docs.jsonl" for f in m["files"])
    assert "JSONL_MALFORMED" in codes(prod(root, trust, register))


def test_oversized_line_rejected(make_bundle, trust, register, monkeypatch):
    monkeypatch.setattr(bundle_mod, "MAX_LINE_BYTES", 100)
    assert "RECORD_TOO_LARGE" in codes(prod(make_bundle(), trust, register))


# ---- compatibility, downgrade (F16), ledger pin (F14)
def test_incompatible_contract_major_rejected(make_bundle, trust, register):
    def edit(m):
        m["compatibility"]["contract_major"] = 2
    assert "INCOMPATIBLE_CONTRACT" in codes(prod(make_bundle(manifest_edit=edit), trust, register))


def test_app_too_old_rejected(make_bundle, trust, register):
    assert "APP_TOO_OLD" in codes(prod(make_bundle(), trust, register, app_version="0.0.9"))


def test_downgrade_or_replay_rejected_unless_rollback(make_bundle, trust, register):
    root = make_bundle()
    assert "DOWNGRADE_OR_REPLAY" in codes(prod(root, trust, register, current_release_sequence=1))
    assert prod(root, trust, register, current_release_sequence=1, rollback=True).ok


def test_self_asserted_ledger_version_rejected_without_trusted_head(make_bundle, trust, register):
    def edit(m):
        m["auth_ledger_version"] = 1
        m["auth_ledger_head"] = LEDGER_HEAD
    root = make_bundle(manifest_edit=edit)
    assert "LEDGER_HEAD_UNVERIFIED" in codes(prod(root, trust, register))
    assert "LEDGER_HEAD_UNVERIFIED" in codes(prod(root, trust, register, trusted_ledger_head="d" * 40))
    assert "LEDGER_HEAD_UNVERIFIED" in codes(prod(root, trust, register, trusted_ledger_head=LEDGER_HEAD[:12]))  # no prefix matching


def test_banner_required_while_ledger_v0(make_bundle, trust, register):
    def edit(m):
        m["candidate_banner"]["required"] = False
    assert "BANNER_REQUIRED" in codes(prod(make_bundle(manifest_edit=edit), trust, register))


def test_requires_migrations_without_migrations_rejected(make_bundle, trust, register):
    def edit(m):
        m["compatibility"]["requires_migrations"] = True
    assert "MIGRATIONS_DECLARED_MISSING" in codes(prod(make_bundle(manifest_edit=edit), trust, register))


def test_dangling_candidate_rejected(make_bundle, trust, register, example):
    c = example("candidate_graph_edge")
    c["source_doc_id"] = "example-not-in-bundle"
    assert "DANGLING_CANDIDATE" in codes(prod(make_bundle(candidates=[c]), trust, register))


def test_duplicate_doc_id_rejected(make_bundle, trust, register, example):
    rep = prod(make_bundle(documents=[example("document"), example("document")]), trust, register)
    assert "DUPLICATE_DOC_ID" in codes(rep)


# ---- F01/F02/F09: approvals and reviews must resolve inside the bundle
def _approval_doc(example):
    d = example("document")
    d["status_axes"]["legal_approval"] = {"value": "T1_LEGAL_ADVISER_REVIEWED", "basis": "claimed", "approval_record_id": "AP-0001"}
    return d


def test_ledger_v0_rejects_approved_record(make_bundle, trust, register, example):
    assert "LEDGER_V0_NO_APPROVAL" in codes(prod(make_bundle(documents=[_approval_doc(example)]), trust, register))


def _appt(**kw):
    a = {"contract_version": "1.0.0", "record_kind": "appointment_record", "appointment_id": "APPT-0001",
         "appointing_authority": "Synthetic competent authority", "appointee": "Synthetic adviser",
         "capacity": "DESIGNATED_LEGAL_ADVISER", "scope": "synthetic test scope", "valid_from": "2026-01-01",
         "valid_until": None, "artefact_sha256": "b" * 64, "revoked": False}
    a.update(kw)
    return a


def _ap(**kw):
    a = {"contract_version": "1.0.0", "record_kind": "approval_record", "approval_record_id": "AP-0001",
         "appointment_id": "APPT-0001", "approver": "Synthetic adviser", "capacity": "DESIGNATED_LEGAL_ADVISER",
         "tier": "T1_LEGAL_ADVISER_REVIEWED", "scope": "synthetic", "subject": {"kind": "document", "id": "example-synthetic-judgment-0001"},
         "pinned_revision": "0000000", "artefact_sha256": "c" * 64, "decided_at": "2026-06-01T00:00:00Z", "status": "ACTIVE"}
    a.update(kw)
    return a


LEDGER_HEAD = "443c4bdf" + "0" * 32  # synthetic full-length head for tests


def _ledger1(m):
    m["auth_ledger_version"] = 1
    m["auth_ledger_head"] = LEDGER_HEAD


def test_approval_without_appointment_rejected_even_with_trusted_ledger(make_bundle, trust, register, example):
    root = make_bundle(documents=[_approval_doc(example)], approvals=[_ap()], manifest_edit=_ledger1)
    c = codes(prod(root, trust, register, trusted_ledger_head=LEDGER_HEAD))
    assert "APPOINTMENT_MISSING" in c


def test_approval_without_record_rejected(make_bundle, trust, register, example):
    root = make_bundle(documents=[_approval_doc(example)], manifest_edit=_ledger1)
    assert "APPROVAL_UNRESOLVED" in codes(prod(root, trust, register, trusted_ledger_head=LEDGER_HEAD))


def test_revoked_appointment_rejected(make_bundle, trust, register, example):
    root = make_bundle(documents=[_approval_doc(example)], approvals=[_ap()], appointments=[_appt(revoked=True)], manifest_edit=_ledger1)
    assert "APPOINTMENT_REVOKED" in codes(prod(root, trust, register, trusted_ledger_head=LEDGER_HEAD))


def test_approval_contradicting_unverified_evidence_rejected(make_bundle, trust, register, example):
    """Even with a valid appointment and artefact, approval on AUTOMATED_CANDIDATE evidence is contradictory."""
    root = make_bundle(documents=[_approval_doc(example)], approvals=[_ap()], appointments=[_appt()], manifest_edit=_ledger1)
    c = codes(prod(root, trust, register, trusted_ledger_head=LEDGER_HEAD))
    assert "AXIS_CONTRADICTION" in c and "APPOINTMENT_MISSING" not in c


def _review(**kw):
    r = {"contract_version": "1.0.0", "record_kind": "reviewed_record", "review_record_id": "RV-0001",
         "subject": {"kind": "document", "id": "example-synthetic-judgment-0001"}, "axis": "evidence_fidelity",
         "from_value": "AUTOMATED_CANDIDATE_NOT_VERIFIED", "to_value": "DOCUMENTARY_CHECKED",
         "reviewer": {"reviewer_id": "reviewer-b", "name_or_role": "independent reviewer", "kind": "AI_AGENT"},
         "reviewed_artefact": {"author_id": "author-a", "reviewed_commit": "0000000"},
         "method": "compared metadata fields against page 1 image", "anchors": [], "decided_at": "2026-11-25T00:00:00Z",
         "record_location": {"path": "legal_knowledge/audit_work/EXAMPLE/review.md", "commit": "0000000"}}
    r.update(kw)
    return r


def _raised_doc(example, rid="RV-0001"):
    d = example("document")
    d["status_axes"]["evidence_fidelity"] = {"value": "DOCUMENTARY_CHECKED", "basis": "see review", "review_record_id": rid}
    return d


def test_raised_value_resolves_to_review_in_bundle(make_bundle, trust, register, example):
    rep = prod(make_bundle(documents=[_raised_doc(example)], reviews=[_review()]), trust, register)
    assert rep.ok, [str(i) for i in rep.errors]


def test_raised_value_with_missing_review_rejected(make_bundle, trust, register, example):
    rep = prod(make_bundle(documents=[_raised_doc(example)]), trust, register)
    assert "REVIEW_UNRESOLVED" in codes(rep)


def test_raised_value_with_review_of_other_axis_rejected(make_bundle, trust, register, example):
    rep = prod(make_bundle(documents=[_raised_doc(example)], reviews=[_review(axis="legal_applicability")]), trust, register)
    assert "REVIEW_MISMATCH" in codes(rep)


def test_review_independence_is_structural_not_declared(make_bundle, trust, register, example):
    """F02: reviewer_id equal to author_id is rejected; a self-declared independence flag no longer exists."""
    rep = prod(make_bundle(documents=[_raised_doc(example)],
                           reviews=[_review(reviewer={"reviewer_id": "Author-A", "name_or_role": "x y", "kind": "AI_AGENT"})]), trust, register)
    assert "REVIEW_NOT_INDEPENDENT" in codes(rep)
    rep = prod(make_bundle("b2", documents=[_raised_doc(example)], reviews=[_review(independent_of_author=True)]), trust, register)
    assert "SCHEMA" in codes(rep)


def test_review_must_cite_the_reviewed_commit(make_bundle, trust, register, example):
    rep = prod(make_bundle(documents=[_raised_doc(example)],
                           reviews=[_review(reviewed_artefact={"author_id": "author-a", "reviewed_commit": "abcdef1"})]), trust, register)
    assert "REVIEW_COMMIT_MISMATCH" in codes(rep)


def test_review_must_reference_existing_subject(make_bundle, trust, register, example):
    rep = prod(make_bundle(documents=[_raised_doc(example)], reviews=[_review(subject={"kind": "document", "id": "example-absent"})]), trust, register)
    assert "DANGLING_REVIEW" in codes(rep)


def test_candidate_review_by_its_own_author_rejected(make_bundle, trust, register, example):
    c = example("candidate_graph_edge")
    c["extractor"]["author_id"] = "extractor-agent-1"
    c["status"] = "DOCUMENTARY_CHECKED"
    c["review_ref"] = "RV-0002"
    rv = _review(review_record_id="RV-0002", subject={"kind": "candidate", "id": c["candidate_id"]},
                 reviewer={"reviewer_id": "EXTRACTOR-AGENT-1", "name_or_role": "same agent", "kind": "AI_AGENT"},
                 reviewed_artefact={"author_id": "someone-else", "reviewed_commit": "0000000"})
    c2 = codes(prod(make_bundle(candidates=[c], reviews=[rv]), trust, register))
    assert "REVIEW_NOT_INDEPENDENT" in c2 and "REVIEW_AUTHOR_MISMATCH" in c2


def test_candidate_review_must_cite_extractor_commit_not_release_commit(make_bundle, trust, register, example):
    c = example("candidate_graph_edge")
    c["extractor"]["artefact_commit"] = "1111111"
    c["status"] = "DOCUMENTARY_CHECKED"
    c["review_ref"] = "RV-0003"
    rv = _review(review_record_id="RV-0003", subject={"kind": "candidate", "id": c["candidate_id"]},
                 reviewed_artefact={"author_id": "author-a", "reviewed_commit": "0000000"})  # tools_commit, not extractor
    assert "REVIEW_COMMIT_MISMATCH" in codes(prod(make_bundle(candidates=[c], reviews=[rv]), trust, register))


def test_ai_review_cannot_raise_legal_applicability_at_ledger_v0(make_bundle, trust, register, example):
    """F02 reviewer probe: AI review record raising legal_applicability to EVIDENCED is rejected (schema and rules)."""
    d = example("document")
    d["status_axes"]["legal_applicability"] = {"value": "EVIDENCED", "basis": "AI review", "approval_record_id": None}
    rv = _review(axis="legal_applicability", from_value="NOT_ESTABLISHED", to_value="EVIDENCED")
    c = codes(prod(make_bundle(documents=[d], reviews=[rv]), trust, register))
    assert {"LEDGER_V0_NO_APPLICABILITY", "LEGAL_AXIS_NEEDS_APPROVAL", "SCHEMA"} <= c


def test_legal_applicability_needs_approval_even_when_ledger_supports_it(make_bundle, trust, register, example):
    d = example("document")
    d["status_axes"]["legal_applicability"] = {"value": "EVIDENCED", "basis": "claimed"}
    c = codes(prod(make_bundle(documents=[d], manifest_edit=_ledger1), trust, register, trusted_ledger_head=LEDGER_HEAD))
    assert "LEGAL_AXIS_NEEDS_APPROVAL" in c and "LEDGER_V0_NO_APPLICABILITY" not in c


def _identity_doc(example, evidence=None, fidelity="PAGE_IMAGE_CHECKED"):
    d = example("document")
    sa = d["status_axes"]["source_authenticity"]
    sa.update(value="IDENTITY_CONFIRMED", review_record_id="RV-0004", authentication_evidence=evidence)
    sa["policy_v1"].update(document_authority="OFFICIAL_JUDICIAL_DECISION", copy_fidelity=fidelity)
    return d


def _identity_review(kind):
    return _review(review_record_id="RV-0004", axis="source_authenticity", from_value="UNKNOWN", to_value="IDENTITY_CONFIRMED",
                   reviewer={"reviewer_id": "reviewer-b", "name_or_role": "x y", "kind": kind})


OFFICIAL = {"kind": "OFFICIAL_SOURCE_RECORD", "ref": "official listing record", "artefact_sha256": None,
            "official_source_url": "https://example.invalid/official"}


def test_ai_review_cannot_confirm_identity(make_bundle, trust, register, example):
    c = codes(prod(make_bundle(documents=[_identity_doc(example, OFFICIAL)], reviews=[_identity_review("AI_AGENT")]), trust, register))
    assert "AI_REVIEW_CANNOT_CONFIRM_IDENTITY" in c


def test_identity_confirmed_needs_verifiable_evidence(make_bundle, trust, register, example):
    c = codes(prod(make_bundle(documents=[_identity_doc(example, None)], reviews=[_identity_review("HUMAN")]), trust, register))
    assert "AUTHENTICITY_EVIDENCE_REQUIRED" in c


def test_identity_via_auth_ledger_impossible_at_v0(make_bundle, trust, register, example):
    ev = {"kind": "AUTH_LEDGER_ENTRY", "ref": "BIND-0001", "artefact_sha256": None, "official_source_url": None}
    c = codes(prod(make_bundle(documents=[_identity_doc(example, ev)], reviews=[_identity_review("HUMAN")]), trust, register))
    assert "AUTHENTICITY_EVIDENCE_INVALID" in c


def test_custodian_evidence_needs_custodian_fidelity_and_hash(make_bundle, trust, register, example):
    ev = {"kind": "CUSTODIAN_CERTIFICATE", "ref": "certificate", "artefact_sha256": None, "official_source_url": None}
    c = codes(prod(make_bundle(documents=[_identity_doc(example, ev)], reviews=[_identity_review("HUMAN")]), trust, register))
    assert "AUTHENTICITY_EVIDENCE_INVALID" in c


def test_identity_confirmed_positive_with_human_review_and_official_record(make_bundle, trust, register, example):
    rep = prod(make_bundle(documents=[_identity_doc(example, OFFICIAL)], reviews=[_identity_review("HUMAN")]), trust, register)
    assert rep.ok, [str(i) for i in rep.errors]


def test_site_publication_act_cannot_be_carried_in_bundle(make_bundle, trust, register, example):
    pr = {"contract_version": "1.0.0", "record_kind": "publication_record", "publication_record_id": "PB-0001",
          "subject": {"doc_id": "example-synthetic-judgment-0001", "source_copy_sha256": example("document")["source_copy"]["sha256"]},
          "action": "PUBLISHED", "channel": "SITE_ADMIN", "actor_role": "ADMIN", "at": "2026-11-25T00:00:00Z", "reason": "synthetic"}
    assert "PUBLICATION_CHANNEL_SITE_ONLY" in codes(prod(make_bundle(publication_records=[pr]), trust, register))
    pr["channel"], pr["action"], pr["actor_role"] = "UPSTREAM_RELEASE", "RELEASED_FOR_PUBLICATION", "RELEASE_BUILDER"
    assert prod(make_bundle("b2", publication_records=[pr]), trust, register).ok


# ---- restricted material at bundle level
def test_bundle_containing_restricted_original_bytes_rejected(make_bundle, register, register_path, monkeypatch):
    """A file whose sha256 is a register hash is rejected under an innocuous name. The real restricted bytes are
    never read or copied: the hash function is stubbed so one innocuous file reports a register hash."""
    items = json.loads(register_path.read_text())["items"]
    target_hash = items[0]["source_sha256"]
    root = make_bundle(sign=False, extra_files={"originals/innocent-name.pdf": (b"%PDF-1.4 placeholder", "original")})
    real = bundle_mod.sha256_file
    sums = root / "SHA256SUMS"
    lines = [ln if not ln.endswith("originals/innocent-name.pdf") else f"{target_hash}  originals/innocent-name.pdf"
             for ln in sums.read_text().splitlines()]
    sums.write_text("\n".join(lines) + "\n")
    monkeypatch.setattr(bundle_mod, "sha256_file", lambda p: target_hash if p.name == "innocent-name.pdf" else real(p))
    rep = validate_bundle(root, register=register, mode="development", allow_unsigned_dev=True)
    assert "RESTRICTED_MATERIAL" in codes(rep)


def test_bundle_with_restricted_path_rejected(make_bundle, trust, register, register_path):
    hp = json.loads(register_path.read_text())["items"][0]["hosted_paths"][-1]
    assert "RESTRICTED_MATERIAL" in codes(prod(make_bundle(extra_files={hp: (b"placeholder", "text")}), trust, register))


def test_bundle_with_upper_cased_restricted_path_rejected(make_bundle, trust, register, register_path):
    """F13: NTFS is case-insensitive; an upper-cased doc_id path with re-extracted bytes must still be caught."""
    did = json.loads(register_path.read_text())["items"][0]["doc_id"]
    root = make_bundle(extra_files={f"data/text/{did.upper()}.txt": (b"re-extracted", "text")})
    assert "RESTRICTED_MATERIAL" in codes(prod(root, trust, register))


def test_bundle_with_restricted_record_rejected(make_bundle, trust, register, register_path, example):
    it = json.loads(register_path.read_text())["items"][0]
    doc = example("document")
    doc["doc_id"] = it["doc_id"]
    c = example("candidate_graph_edge")
    c["source_doc_id"] = it["doc_id"]
    assert "RESTRICTED_MATERIAL" in codes(prod(make_bundle(documents=[doc], candidates=[c]), trust, register))


def test_bundle_with_edge_targeting_restricted_doc_rejected(make_bundle, trust, register, register_path, example):
    """F03: reference to the restricted item through a graph edge target."""
    it = json.loads(register_path.read_text())["items"][0]
    c = example("candidate_graph_edge")
    c["payload"]["target"] = {"resolved": True, "node_id": it["doc_id"], "raw_reference": None}
    assert "RESTRICTED_MATERIAL" in codes(prod(make_bundle(candidates=[c]), trust, register))


def test_bundle_built_against_other_register_rejected(make_bundle, trust, register):
    def edit(m):
        m["restricted_material"]["config_sha256"] = "f" * 64
    assert "RESTRICTED_CONFIG_DRIFT" in codes(prod(make_bundle(manifest_edit=edit), trust, register))


def test_bundle_not_applying_every_register_entry_rejected(make_bundle, trust, register):
    def edit(m):
        m["restricted_material"]["restriction_ids_applied"] = []
    assert "RESTRICTED_IDS_NOT_APPLIED" in codes(prod(make_bundle(manifest_edit=edit), trust, register))


def test_bundle_validation_fails_closed_without_register(make_bundle, trust, tmp_path, monkeypatch):
    root = make_bundle()
    monkeypatch.setenv("MIMAMSA_RESTRICTED_MATERIAL_CONFIG", str(tmp_path / "missing.json"))
    rep = validate_bundle(root, trust_list=trust, current_release_sequence=0)
    assert "RESTRICTED_CONFIG_MISSING" in codes(rep) and not rep.ok


def test_cli_bundle_and_restricted_check(make_bundle, owner_keys, register_path, tmp_path, capsys):
    root = make_bundle()
    tl = tmp_path / "trust.json"
    tl.write_text(json.dumps(trust_list_for([(owner_keys[1], "OWNER", ["release"])])))
    assert cli_main(["--register", str(register_path), "bundle", str(root), "--trust-list", str(tl), "--current-sequence", "0"]) == 0
    assert cli_main(["--register", str(register_path), "bundle", str(root), "--trust-list", str(tl)]) == 1  # sequence mandatory
    keyfile = tmp_path / "k.hex"
    keyfile.write_text(owner_keys[1].hex())
    assert cli_main(["--register", str(register_path), "bundle", str(root), "--trusted-key", str(keyfile)]) == 1  # production needs a trust list
    it = json.loads(register_path.read_text())["items"][0]
    assert cli_main(["--register", str(register_path), "restricted-check", "--sha256", it["source_sha256"]]) == 1
    assert cli_main(["--register", str(register_path), "restricted-check", "--doc-id", "example-free"]) == 0
    out = capsys.readouterr().out
    assert it["source_sha256"] not in out


# ---- confirmation P3s
@pytest.mark.parametrize("bad", ["data/DOCUME~1.JSO", "data/progra~2/x.txt", "data/RELEAS~1"])
def test_windows_short_name_alias_rejected(make_bundle, trust, register, bad):
    """C02: 8.3 short-name aliases."""
    assert "PATH_HAZARD" in codes(prod(make_bundle(extra_files={bad: (b"x", "other")}), trust, register))


def test_release_sequence_mandatory_in_production(make_bundle, trust, register):
    """C04: the downgrade check cannot be skipped by omitting the active sequence."""
    rep = validate_bundle(make_bundle(), trust_list=trust, register=register)
    assert "RELEASE_SEQUENCE_REQUIRED" in codes(rep) and rep.checked_records == 0


def test_expired_release_key_rejected(make_bundle, owner_keys, register):
    """C03: keys past valid_until are not used (date from the site's trusted time source)."""
    from datetime import date
    tl = trust_list_for([(owner_keys[1], "OWNER", ["release"])])
    tl["keys"][0]["valid_until"] = "2026-01-01"
    t = parse_trust_list(tl)
    assert "SIGNATURE_INVALID" in codes(prod(make_bundle(), t, register, today=date(2026, 11, 25)))
    assert prod(make_bundle("b2"), t, register, today=date(2025, 12, 31)).ok


def test_sums_read_once(make_bundle, trust, register, monkeypatch):
    """C05: SHA256SUMS is read exactly once; the verified bytes are the parsed bytes."""
    from pathlib import Path
    root = make_bundle()
    reads = []
    real = Path.read_bytes

    def counting(self):
        if self.name == "SHA256SUMS":
            reads.append(1)
        return real(self)
    monkeypatch.setattr(Path, "read_bytes", counting)
    monkeypatch.setattr(Path, "read_text", lambda self, *a, **k: (_ for _ in ()).throw(AssertionError("SUMS re-read as text"))
                        if self.name == "SHA256SUMS" else real(self).decode(k.get("encoding") or "utf-8"))
    assert prod(root, trust, register).ok
    assert len(reads) == 1
