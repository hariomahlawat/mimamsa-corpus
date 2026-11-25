"""Signed exclusion updates (restricted register + withdrawal list) and post-activation re-application.

Independent of releases. Rule: after every activation, rollback or restore, the site re-applies the latest accepted
exclusion state to the active generation, so a rollback, an older generation or a restored backup can never resurrect
a withdrawn or restricted item.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from .restricted import RestrictedRegister, register_from_bytes
from .schemas import validator
from .trust import TrustList, verify_detached


class ExclusionError(ValueError):
    pass


def _no_dupes(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise ExclusionError(f"duplicate key {k!r}")
        d[k] = v
    return d


@dataclass(frozen=True)
class ExclusionState:
    sequence: int
    register: RestrictedRegister
    withdrawn_doc_ids: frozenset = field(default_factory=frozenset)
    withdrawn_shas: frozenset = field(default_factory=frozenset)


def accept_exclusion_update(update_bytes: bytes, signature: bytes, trust: TrustList, current_sequence: int,
                            mode: str = "production") -> ExclusionState:
    if verify_detached(update_bytes, signature, trust, "register", mode) is None:
        raise ExclusionError("exclusion update not signed by a trusted register key")
    data = json.loads(update_bytes.decode("utf-8"), object_pairs_hook=_no_dupes)
    errs = list(validator("exclusion_update").iter_errors(data))
    if errs:
        raise ExclusionError(f"exclusion update invalid: {errs[0].message[:200]}")
    if data["sequence"] <= current_sequence:
        raise ExclusionError("exclusion update sequence must increase (replay/downgrade refused)")
    reg_bytes = data["register_json"].encode("utf-8")
    if hashlib.sha256(reg_bytes).hexdigest() != data["register_sha256"]:
        raise ExclusionError("register_sha256 does not match register_json")
    reg = register_from_bytes(reg_bytes, "exclusion_update")
    return ExclusionState(
        sequence=data["sequence"], register=reg,
        withdrawn_doc_ids=frozenset(w["doc_id"] for w in data["withdrawals"] if w.get("doc_id")),
        withdrawn_shas=frozenset(w["source_copy_sha256"] for w in data["withdrawals"] if w.get("source_copy_sha256")),
    )


def items_to_suppress(items, state: ExclusionState) -> list[tuple[str, str]]:
    """items: iterable of document records (or dicts with doc_id and source_copy.sha256) in the generation being
    activated. Returns (doc_id, reason) for every item that must be removed from search, vectors, graph, caches and
    exports before the generation serves any request."""
    out = []
    for it in items:
        did = it.get("doc_id")
        sha = (it.get("source_copy") or {}).get("sha256") or it.get("sha256")
        if state.register.deep_match(it):
            out.append((did, "RESTRICTED"))
        elif did in state.withdrawn_doc_ids or sha in state.withdrawn_shas:
            out.append((did, "WITHDRAWN"))
    return out


class ExclusionStore:
    """Append-only on-disk store of accepted, signed exclusion updates, kept OUTSIDE the database and the release
    generations (site path D:\\Mimamsa\\exclusions\\, excluded from restore). A database or release restore cannot
    remove or roll it back; restore requires it (load_latest) and re-applies its latest state.
    Files: <seq:08d>.json + <seq:08d>.sig, written once; lower or equal sequences and overwrites are refused."""

    def __init__(self, directory):
        from pathlib import Path
        self.dir = Path(directory)

    def _seqs(self):
        return sorted(int(p.stem) for p in self.dir.glob("*.json") if p.stem.isdigit())

    def append(self, update_bytes: bytes, signature: bytes, trust: TrustList, mode: str = "production") -> ExclusionState:
        self.dir.mkdir(parents=True, exist_ok=True)
        seqs = self._seqs()
        state = accept_exclusion_update(update_bytes, signature, trust, seqs[-1] if seqs else 0, mode)
        j, s = self.dir / f"{state.sequence:08d}.json", self.dir / f"{state.sequence:08d}.sig"
        if j.exists() or s.exists():
            raise ExclusionError("exclusion update already stored; the store is append-only")
        with open(j, "xb") as fh:
            fh.write(update_bytes)
        with open(s, "xb") as fh:
            fh.write(signature)
        return state

    def load_latest(self, trust: TrustList, mode: str = "production") -> ExclusionState:
        """Re-verify the newest stored update. Missing store => ExclusionError (restore must not proceed)."""
        seqs = self._seqs()
        if not seqs:
            raise ExclusionError("exclusion store empty or missing: restore/activation refused until it is present")
        n = seqs[-1]
        return accept_exclusion_update((self.dir / f"{n:08d}.json").read_bytes(), (self.dir / f"{n:08d}.sig").read_bytes(),
                                       trust, n - 1, mode)


def state_for_restore(store: ExclusionStore, trust: TrustList, restored_db_sequence: int, mode: str = "production") -> ExclusionState:
    """The exclusion state applied after a restore is always the store's latest, never the restored database's copy."""
    latest = store.load_latest(trust, mode)
    if latest.sequence < restored_db_sequence:
        raise ExclusionError("exclusion store is older than the restored database: store tampered or lost; refuse")
    return latest
