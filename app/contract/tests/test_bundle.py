from __future__ import annotations

import json

import pytest

from mimamsa_contract.__main__ import main as cli_main
from mimamsa_contract.bundle import validate_bundle
from mimamsa_contract.devbundle import new_dev_keypair, write_bundle


@pytest.fixture
def keys():
    return new_dev_keypair()  # disposable, in memory only


@pytest.fixture
def make_bundle(tmp_path, example, register, keys):
    sk, pk = keys

    def _make(name="b", *, documents=None, derived=None, candidates=None, extra_files=None, manifest_edit=None, sign=True):
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
            extra_files=extra_files, signing_key=sk if sign else None, public_key_raw=pk)

    return _make


def codes(report):
    return {i.code for i in report.errors}


def test_clean_signed_bundle_accepted(make_bundle, keys, register):
    rep = validate_bundle(make_bundle(), trusted_public_key=keys[1], register=register)
    assert rep.ok, [str(i) for i in rep.errors]
    assert rep.signature_verified and rep.checked_records == 4


def test_unsigned_bundle_rejected_without_dev_flag(make_bundle, register):
    root = make_bundle(sign=False)
    assert "SIGNATURE_NOT_VERIFIED" in codes(validate_bundle(root, register=register))
    assert validate_bundle(root, register=register, allow_unsigned_dev=True).ok


def test_wrong_key_rejected(make_bundle, register):
    _, other_pk = new_dev_keypair()
    assert "SIGNATURE_KEY_MISMATCH" in codes(validate_bundle(make_bundle(), trusted_public_key=other_pk, register=register))


def test_tampered_byte_rejected(make_bundle, keys, register):
    root = make_bundle()
    p = root / "data" / "documents.jsonl"
    data = bytearray(p.read_bytes())
    data[10] ^= 0x01
    p.write_bytes(bytes(data))
    assert "CHECKSUM_MISMATCH" in codes(validate_bundle(root, trusted_public_key=keys[1], register=register))


def test_tampered_sums_breaks_signature(make_bundle, keys, register):
    root = make_bundle()
    s = root / "SHA256SUMS"
    s.write_text(s.read_text() + "\n")
    assert "SIGNATURE_INVALID" in codes(validate_bundle(root, trusted_public_key=keys[1], register=register))


def test_unlisted_file_rejected(make_bundle, keys, register):
    root = make_bundle()
    (root / "data" / "smuggled.pdf").write_bytes(b"%PDF-1.4")
    assert "UNLISTED_FILE" in codes(validate_bundle(root, trusted_public_key=keys[1], register=register))


def test_symlink_rejected(make_bundle, keys, register, tmp_path):
    root = make_bundle()
    target = tmp_path / "outside.txt"
    target.write_text("x")
    (root / "data" / "link").symlink_to(target)
    assert "SYMLINK_IN_BUNDLE" in codes(validate_bundle(root, trusted_public_key=keys[1], register=register))


def test_incompatible_contract_major_rejected(make_bundle, keys, register):
    def edit(m):
        m["compatibility"]["contract_major"] = 2
    assert "INCOMPATIBLE_CONTRACT" in codes(validate_bundle(make_bundle(manifest_edit=edit), trusted_public_key=keys[1], register=register))


def test_app_too_old_rejected(make_bundle, keys, register):
    rep = validate_bundle(make_bundle(), trusted_public_key=keys[1], register=register, app_version="0.0.9")
    assert "APP_TOO_OLD" in codes(rep)


def test_banner_required_while_ledger_v0(make_bundle, keys, register):
    def edit(m):
        m["candidate_banner"]["required"] = False
    assert "BANNER_REQUIRED" in codes(validate_bundle(make_bundle(manifest_edit=edit), trusted_public_key=keys[1], register=register))


def test_ledger_v0_rejects_approved_record(make_bundle, keys, register, example):
    doc = example("document")
    doc["status_axes"]["legal_approval"] = {"value": "T2_FORMAL_JAG_VALIDATED", "basis": "claimed", "approval_ref": "X"}
    rep = validate_bundle(make_bundle(documents=[doc]), trusted_public_key=keys[1], register=register)
    assert "LEDGER_V0_NO_APPROVAL" in codes(rep)


def test_dangling_candidate_rejected(make_bundle, keys, register, example):
    c = example("candidate_graph_edge")
    c["source_doc_id"] = "example-not-in-bundle"
    rep = validate_bundle(make_bundle(candidates=[c]), trusted_public_key=keys[1], register=register)
    assert "DANGLING_CANDIDATE" in codes(rep)


def test_duplicate_doc_id_rejected(make_bundle, keys, register, example):
    rep = validate_bundle(make_bundle(documents=[example("document"), example("document")]), trusted_public_key=keys[1], register=register)
    assert "DUPLICATE_DOC_ID" in codes(rep)


def test_requires_migrations_without_migrations_rejected(make_bundle, keys, register):
    def edit(m):
        m["compatibility"]["requires_migrations"] = True
    rep = validate_bundle(make_bundle(manifest_edit=edit), trusted_public_key=keys[1], register=register)
    assert "MIGRATIONS_DECLARED_MISSING" in codes(rep)


# ---- restricted-material exclusion at bundle level (register read from config/restricted_material.json) ----

def test_bundle_containing_restricted_original_bytes_rejected(make_bundle, keys, register, register_path, monkeypatch):
    """A file whose sha256 is a register hash is rejected even under an innocuous name.

    The real restricted bytes are never read or copied by this test: the validator's hash function is stubbed so
    that one innocuous file reports a register hash, exactly as the real bytes would.
    """
    import mimamsa_contract.bundle as bundle_mod

    items = json.loads(register_path.read_text())["items"]
    target_hash = items[0]["source_sha256"]
    root = make_bundle(extra_files={"originals/innocent-name.pdf": (b"%PDF-1.4 placeholder", "original")})
    real = bundle_mod.sha256_file

    def fake(p):
        return target_hash if p.name == "innocent-name.pdf" else real(p)

    # rewrite SHA256SUMS so that, apart from the restricted hash, the bundle is internally consistent
    sums = root / "SHA256SUMS"
    lines = [ln if not ln.endswith("originals/innocent-name.pdf") else f"{target_hash}  originals/innocent-name.pdf"
             for ln in sums.read_text().splitlines()]
    sums.write_text("\n".join(lines) + "\n")
    monkeypatch.setattr(bundle_mod, "sha256_file", fake)
    rep = validate_bundle(root, register=register, allow_unsigned_dev=True)
    assert "RESTRICTED_MATERIAL" in codes(rep)
    assert not rep.ok


def test_bundle_with_restricted_path_rejected(make_bundle, keys, register, register_path):
    hp = json.loads(register_path.read_text())["items"][0]["hosted_paths"][-1]
    root = make_bundle(extra_files={hp: (b"placeholder, not the restricted text", "text")})
    rep = validate_bundle(root, trusted_public_key=keys[1], register=register)
    assert "RESTRICTED_MATERIAL" in codes(rep)


def test_bundle_with_restricted_record_rejected(make_bundle, keys, register, register_path, example):
    it = json.loads(register_path.read_text())["items"][0]
    doc = example("document")
    doc["doc_id"] = it["doc_id"]
    c = example("candidate_graph_edge")
    c["source_doc_id"] = it["doc_id"]
    rep = validate_bundle(make_bundle(documents=[doc], candidates=[c]), trusted_public_key=keys[1], register=register)
    assert "RESTRICTED_MATERIAL" in codes(rep)


def test_bundle_built_against_other_register_rejected(make_bundle, keys, register):
    def edit(m):
        m["restricted_material"]["config_sha256"] = "f" * 64
    rep = validate_bundle(make_bundle(manifest_edit=edit), trusted_public_key=keys[1], register=register)
    assert "RESTRICTED_CONFIG_DRIFT" in codes(rep)


def test_bundle_not_applying_every_register_entry_rejected(make_bundle, keys, register):
    def edit(m):
        m["restricted_material"]["restriction_ids_applied"] = []
    rep = validate_bundle(make_bundle(manifest_edit=edit), trusted_public_key=keys[1], register=register)
    assert "RESTRICTED_IDS_NOT_APPLIED" in codes(rep)


def test_bundle_validation_fails_closed_without_register(make_bundle, keys, tmp_path, monkeypatch):
    root = make_bundle()
    monkeypatch.setenv("MIMAMSA_RESTRICTED_MATERIAL_CONFIG", str(tmp_path / "missing.json"))
    rep = validate_bundle(root, trusted_public_key=keys[1])
    assert "RESTRICTED_CONFIG_MISSING" in codes(rep) and not rep.ok


def test_cli_bundle_and_restricted_check(make_bundle, keys, register_path, tmp_path, capsys):
    root = make_bundle()
    keyfile = tmp_path / "trusted.pub.hex"
    keyfile.write_text(keys[1].hex())
    assert cli_main(["--register", str(register_path), "bundle", str(root), "--trusted-key", str(keyfile)]) == 0
    it = json.loads(register_path.read_text())["items"][0]
    assert cli_main(["--register", str(register_path), "restricted-check", "--sha256", it["source_sha256"]]) == 1
    assert cli_main(["--register", str(register_path), "restricted-check", "--doc-id", "example-free"]) == 0
    out = capsys.readouterr().out
    assert it["source_sha256"] not in out
