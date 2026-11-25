"""F05 trust-list change authority and F06 exclusion channel / post-activation re-application."""
from __future__ import annotations

import hashlib
import json

import pytest

from mimamsa_contract.devbundle import new_dev_keypair, trust_list_for
from mimamsa_contract.exclusions import ExclusionError, accept_exclusion_update, items_to_suppress
from mimamsa_contract.trust import TrustError, apply_trust_list_update, parse_trust_list


@pytest.fixture
def owner():
    return new_dev_keypair()


@pytest.fixture
def trust(owner):
    return parse_trust_list(trust_list_for([(owner[1], "OWNER", ["release", "register", "trust_list"])]))


def _signed(sk, obj):
    b = json.dumps(obj).encode()
    return b, sk.sign(b)


# ---- trust list
def test_owner_signed_trust_list_update_accepted(owner, trust):
    _, newpk = new_dev_keypair()
    upd = trust_list_for([(owner[1], "OWNER", ["trust_list"]), (newpk, "OWNER", ["release"])], sequence=2)
    b, sig = _signed(owner[0], upd)
    new = apply_trust_list_update(trust, b, sig)
    assert new.sequence == 2 and len(new.keys) == 2


def test_trust_list_update_signed_by_untrusted_key_rejected(trust):
    attacker_sk, attacker_pk = new_dev_keypair()
    upd = trust_list_for([(attacker_pk, "OWNER", ["release", "trust_list"])], sequence=2)
    b, sig = _signed(attacker_sk, upd)
    with pytest.raises(TrustError):
        apply_trust_list_update(trust, b, sig)


def test_trust_list_update_signed_by_release_only_key_rejected(owner):
    rel_sk, rel_pk = new_dev_keypair()
    t = parse_trust_list(trust_list_for([(owner[1], "OWNER", ["trust_list"]), (rel_pk, "OWNER", ["release"])]))
    b, sig = _signed(rel_sk, trust_list_for([(rel_pk, "OWNER", ["release", "trust_list"])], sequence=2))
    with pytest.raises(TrustError):
        apply_trust_list_update(t, b, sig)


def test_trust_list_update_by_development_key_rejected_in_production():
    dev_sk, dev_pk = new_dev_keypair()
    t = parse_trust_list(trust_list_for([(dev_pk, "DEVELOPMENT", ["trust_list", "release"])]))
    b, sig = _signed(dev_sk, trust_list_for([(dev_pk, "DEVELOPMENT", ["trust_list"])], sequence=2))
    with pytest.raises(TrustError):
        apply_trust_list_update(t, b, sig)


def test_trust_list_replay_rejected(owner, trust):
    b, sig = _signed(owner[0], trust_list_for([(owner[1], "OWNER", ["trust_list"])], sequence=1))
    with pytest.raises(TrustError):
        apply_trust_list_update(trust, b, sig)


def test_trust_list_key_id_must_match_key(owner):
    tl = trust_list_for([(owner[1], "OWNER", ["release"])])
    tl["keys"][0]["key_id"] = "a" * 64
    with pytest.raises(TrustError):
        parse_trust_list(tl)


def test_dev_prefix_reserved_for_development_holder(owner):
    tl = trust_list_for([(owner[1], "OWNER", ["release"])])
    tl["keys"][0]["key_id"] = "dev-" + tl["keys"][0]["key_id"]
    with pytest.raises(TrustError):
        parse_trust_list(tl)


# ---- exclusion channel
def _update(register_path, *, sequence=2, withdrawals=()):
    text = register_path.read_text(encoding="utf-8")
    return {"contract_version": "1.0.0", "record_kind": "exclusion_update", "sequence": sequence,
            "issued_at": "2026-11-25T00:00:00Z", "register_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "register_json": text, "withdrawals": list(withdrawals)}


def test_exclusion_update_accepted_and_register_sha_matches_release_pin(owner, trust, register_path, register):
    b, sig = _signed(owner[0], _update(register_path))
    st = accept_exclusion_update(b, sig, trust, current_sequence=1)
    assert st.register.config_sha256 == register.config_sha256


def test_exclusion_update_wrong_signer_rejected(trust, register_path):
    sk, _ = new_dev_keypair()
    b, sig = _signed(sk, _update(register_path))
    with pytest.raises(ExclusionError):
        accept_exclusion_update(b, sig, trust, current_sequence=1)


def test_exclusion_update_requires_register_purpose(owner, register_path):
    t = parse_trust_list(trust_list_for([(owner[1], "OWNER", ["release"])]))
    b, sig = _signed(owner[0], _update(register_path))
    with pytest.raises(ExclusionError):
        accept_exclusion_update(b, sig, t, current_sequence=1)


def test_exclusion_update_replay_rejected(owner, trust, register_path):
    b, sig = _signed(owner[0], _update(register_path, sequence=3))
    with pytest.raises(ExclusionError):
        accept_exclusion_update(b, sig, trust, current_sequence=3)


def test_exclusion_update_hash_mismatch_rejected(owner, trust, register_path):
    u = _update(register_path)
    u["register_sha256"] = "0" * 64
    b, sig = _signed(owner[0], u)
    with pytest.raises(ExclusionError):
        accept_exclusion_update(b, sig, trust, current_sequence=1)


def test_rollback_cannot_resurrect_withdrawn_or_restricted(owner, trust, register_path, example):
    """F06: an older generation (rollback/restore) that still contains a since-withdrawn document and a document now
    on the register must have both suppressed by the post-activation re-application."""
    it = json.loads(register_path.read_text())["items"][0]
    withdrawn = example("document")
    withdrawn["doc_id"] = "example-withdrawn-later"
    restricted = example("document")
    restricted["doc_id"] = it["doc_id"]
    keep = example("document")
    b, sig = _signed(owner[0], _update(register_path, withdrawals=[{"doc_id": "example-withdrawn-later", "reason": "upstream withdrawal"}]))
    st = accept_exclusion_update(b, sig, trust, current_sequence=1)
    out = dict(items_to_suppress([withdrawn, restricted, keep], st))
    assert out == {"example-withdrawn-later": "WITHDRAWN", it["doc_id"]: "RESTRICTED"}


# ---- C06: exclusion state kept outside the restorable database/release
from mimamsa_contract.exclusions import ExclusionStore, state_for_restore  # noqa: E402


def test_store_is_append_only_and_monotonic(owner, trust, register_path, tmp_path):
    store = ExclusionStore(tmp_path / "exclusions")
    b2, s2 = _signed(owner[0], _update(register_path, sequence=2))
    store.append(b2, s2, trust)
    b1, s1 = _signed(owner[0], _update(register_path, sequence=1))
    with pytest.raises(ExclusionError):
        store.append(b1, s1, trust)          # older update refused
    ack = store.append(b2, s2, trust)        # replay of the accepted update is idempotent (same acknowledgement)
    assert ack["sequence"] == 2 and store.load_latest(trust).sequence == 2


def test_restore_uses_store_not_restored_database(owner, trust, register_path, tmp_path, example):
    store = ExclusionStore(tmp_path / "exclusions")
    b, s = _signed(owner[0], _update(register_path, sequence=5,
                                      withdrawals=[{"doc_id": "example-withdrawn-later", "reason": "withdrawn after backup"}]))
    store.append(b, s, trust)
    st = state_for_restore(store, trust, restored_db_sequence=3)   # backup predates the withdrawal
    d = example("document")
    d["doc_id"] = "example-withdrawn-later"
    assert dict(items_to_suppress([d], st)) == {"example-withdrawn-later": "WITHDRAWN"}


def test_restore_refused_without_store(trust, tmp_path):
    with pytest.raises(ExclusionError):
        state_for_restore(ExclusionStore(tmp_path / "missing"), trust, restored_db_sequence=1)


def test_restore_refused_if_store_older_than_database(owner, trust, register_path, tmp_path):
    store = ExclusionStore(tmp_path / "exclusions")
    b, s = _signed(owner[0], _update(register_path, sequence=2))
    store.append(b, s, trust)
    with pytest.raises(ExclusionError):
        state_for_restore(store, trust, restored_db_sequence=4)


def test_tampered_stored_update_rejected_on_load(owner, trust, register_path, tmp_path):
    store = ExclusionStore(tmp_path / "exclusions")
    b, s = _signed(owner[0], _update(register_path, sequence=2))
    store.append(b, s, trust)
    p = tmp_path / "exclusions" / "pairs" / "00000002.json"
    p.write_bytes(p.read_bytes().replace(b'"sequence": 2', b'"sequence": 2 '))
    with pytest.raises(ExclusionError):
        store.load_latest(trust)


# ---- PR #53 reconciliation: acceptance record, pending pairs, null withdrawal rows
def test_unaccepted_pair_is_pending_not_accepted(owner, trust, register_path, tmp_path):
    store = ExclusionStore(tmp_path / "exclusions")
    b2, s2 = _signed(owner[0], _update(register_path, sequence=2))
    store.append(b2, s2, trust)
    # simulate a crash after the pair was written but before acceptance of sequence 3
    b3, s3 = _signed(owner[0], _update(register_path, sequence=3))
    (store.pairs / "00000003.json").write_bytes(b3)
    (store.pairs / "00000003.sig").write_bytes(s3)
    assert store.load_latest(trust).sequence == 2
    assert store.pending() == [3]


def test_accepted_record_pointing_to_missing_pair_halts(owner, trust, register_path, tmp_path):
    store = ExclusionStore(tmp_path / "exclusions")
    b, s = _signed(owner[0], _update(register_path, sequence=2))
    store.append(b, s, trust)
    (store.pairs / "00000002.sig").unlink()
    with pytest.raises(ExclusionError):
        store.load_latest(trust)


def test_compare_and_set_rejects_stale_writer(owner, trust, register_path, tmp_path):
    store = ExclusionStore(tmp_path / "exclusions")
    b2, s2 = _signed(owner[0], _update(register_path, sequence=2))
    store.append(b2, s2, trust, expected_sequence=0)
    b3, s3 = _signed(owner[0], _update(register_path, sequence=3))
    with pytest.raises(ExclusionError):
        store.append(b3, s3, trust, expected_sequence=0)   # prepared against an old accepted state


@pytest.mark.parametrize("row", [{"doc_id": None, "reason": "x y z"}, {"source_copy_sha256": None, "reason": "x y z"},
                                 {"doc_id": None, "source_copy_sha256": None, "reason": "x y z"}])
def test_null_only_withdrawal_row_rejected(owner, trust, register_path, row):
    """PR #53 Crosswalk §7: a withdrawal row with no actionable identity cannot be enforced; reject the update."""
    b, sig = _signed(owner[0], _update(register_path, withdrawals=[row]))
    with pytest.raises(ExclusionError):
        accept_exclusion_update(b, sig, trust, current_sequence=1)


# ---- review of PR #53 reconciliation: F03 restart cases and lost acknowledgement (reviewer probes a, b)
def test_pending_pair_can_be_completed_after_crash(owner, trust, register_path, tmp_path):
    """Probe (a): pair written, crash before ACCEPTED; re-appending the identical update or complete_pending accepts it."""
    store = ExclusionStore(tmp_path / "exclusions")
    b2, s2 = _signed(owner[0], _update(register_path, sequence=2))
    store.pairs.mkdir(parents=True)
    (store.pairs / "00000002.json").write_bytes(b2)
    (store.pairs / "00000002.sig").write_bytes(s2)
    assert store.pending() == [2]
    ack = store.complete_pending(2, trust)
    assert ack["sequence"] == 2 and store.pending() == [] and store.load_latest(trust).sequence == 2


def test_resume_by_reappending_identical_bytes(owner, trust, register_path, tmp_path):
    store = ExclusionStore(tmp_path / "exclusions")
    b2, s2 = _signed(owner[0], _update(register_path, sequence=2))
    store.pairs.mkdir(parents=True)
    (store.pairs / "00000002.json").write_bytes(b2)
    (store.pairs / "00000002.sig").write_bytes(s2)
    assert store.append(b2, s2, trust)["sequence"] == 2


def test_different_bytes_for_stored_sequence_rejected(owner, trust, register_path, tmp_path):
    store = ExclusionStore(tmp_path / "exclusions")
    b2, s2 = _signed(owner[0], _update(register_path, sequence=2))
    store.pairs.mkdir(parents=True)
    (store.pairs / "00000002.json").write_bytes(b"other bytes")
    (store.pairs / "00000002.sig").write_bytes(b"x")
    with pytest.raises(ExclusionError):
        store.append(b2, s2, trust)


def test_staging_residue_is_quarantined_not_raw_error(owner, trust, register_path, tmp_path):
    """Probe (b): leftover staging/<seq> no longer raises FileExistsError; it is moved to quarantine and never accepted."""
    store = ExclusionStore(tmp_path / "exclusions")
    st = store.dir / "staging" / "00000002"
    st.mkdir(parents=True)
    (st / "u.json").write_bytes(b"partial")
    b2, s2 = _signed(owner[0], _update(register_path, sequence=2))
    assert store.append(b2, s2, trust)["sequence"] == 2
    assert not st.exists() and any((store.dir / "quarantine").iterdir())


def test_lost_ack_retry_returns_original_ack(owner, trust, register_path, tmp_path):
    store = ExclusionStore(tmp_path / "exclusions")
    b2, s2 = _signed(owner[0], _update(register_path, sequence=2))
    first = store.append(b2, s2, trust, operation_id="op-123")
    again = store.append(b2, s2, trust, operation_id="op-123")
    assert first == again and first["operation_id"] == "op-123" and first["epoch"] == 1
    with pytest.raises(ExclusionError):
        store.append(b2, s2, trust, operation_id="op-other")


def test_single_writer_lock(owner, trust, register_path, tmp_path):
    store = ExclusionStore(tmp_path / "exclusions")
    store.dir.mkdir(parents=True)
    store.lockfile.write_text("held")
    b2, s2 = _signed(owner[0], _update(register_path, sequence=2))
    with pytest.raises(ExclusionError):
        store.append(b2, s2, trust)


def test_io_failure_is_typed(owner, trust, register_path, tmp_path, monkeypatch):
    import os as _os
    store = ExclusionStore(tmp_path / "exclusions")
    b2, s2 = _signed(owner[0], _update(register_path, sequence=2))
    monkeypatch.setattr(_os, "replace", lambda *a, **k: (_ for _ in ()).throw(PermissionError("denied")))
    with pytest.raises(ExclusionError):
        store.append(b2, s2, trust)


# ---- F02: monotone tombstones; omission never re-admits
def test_omission_from_later_list_does_not_readmit(owner, trust, register_path, tmp_path, example):
    store = ExclusionStore(tmp_path / "exclusions")
    w = [{"doc_id": "example-withdrawn-later", "reason": "withdrawn"}]
    for seq, rows in ((2, w), (3, [])):
        b, s = _signed(owner[0], _update(register_path, sequence=seq, withdrawals=rows))
        store.append(b, s, trust)
    d = example("document")
    d["doc_id"] = "example-withdrawn-later"
    assert dict(items_to_suppress([d], store.effective_state(trust))) == {"example-withdrawn-later": "WITHDRAWN"}
    st = state_for_restore(store, trust, restored_db_sequence=1)
    assert dict(items_to_suppress([d], st)) == {"example-withdrawn-later": "WITHDRAWN"}


def test_explicit_signed_readmission_lifts_denial(owner, trust, register_path, tmp_path, example):
    store = ExclusionStore(tmp_path / "exclusions")
    b, s = _signed(owner[0], _update(register_path, sequence=2, withdrawals=[{"doc_id": "example-x", "reason": "withdrawn"}]))
    store.append(b, s, trust)
    u = _update(register_path, sequence=3)
    u["readmissions"] = [{"doc_id": "example-x", "reason": "error corrected", "authority_ref": "OWNER-DECISION-0001"}]
    b, s = _signed(owner[0], u)
    store.append(b, s, trust)
    d = example("document")
    d["doc_id"] = "example-x"
    assert items_to_suppress([d], store.effective_state(trust)) == []


def test_readmission_needs_authority_and_identity(owner, trust, register_path):
    u = _update(register_path)
    u["readmissions"] = [{"doc_id": "example-x", "reason": "no authority"}]
    b, s = _signed(owner[0], u)
    with pytest.raises(ExclusionError):
        accept_exclusion_update(b, s, trust, current_sequence=1)
    u["readmissions"] = [{"doc_id": None, "reason": "x y z", "authority_ref": "A-1"}]
    b, s = _signed(owner[0], u)
    with pytest.raises(ExclusionError):
        accept_exclusion_update(b, s, trust, current_sequence=1)
