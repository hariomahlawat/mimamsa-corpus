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
    for w in data["withdrawals"]:
        if not (w.get("doc_id") or w.get("source_copy_sha256")):
            raise ExclusionError("withdrawal row names neither a doc_id nor a source copy hash; update rejected")
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
    """Append-only store of accepted, signed exclusion updates, kept OUTSIDE the database and the release generations
    (site path D:\\Mimamsa\\exclusions\\, excluded from restore). Restore cannot remove or roll it back.

    Acceptance protocol (reference for PR #53 Serving §4/§8, single writer):
      1 stage the payload and signature together under staging/<seq>/ and flush;
      2 move the complete pair into pairs/<seq:08d>.{json,sig} (write-once);
      3 accept by compare-and-set of the ACCEPTED record (expected prior sequence + digest -> new sequence + digest),
        written to a temporary file, flushed and atomically replaced. The ACCEPTED record is the sole acceptance point.
    A pair without a matching ACCEPTED record is pending, never accepted; load_latest uses only the ACCEPTED record and
    halts if it references a missing or altered pair. Durability on the actual Windows storage is proven in P8/B2;
    custody of an independent copy of the ACCEPTED record (the "witness") is an owner decision.
    """

    def __init__(self, directory):
        from pathlib import Path
        self.dir = Path(directory)
        self.pairs = self.dir / "pairs"
        self.accepted = self.dir / "ACCEPTED.json"

    def _read_accepted(self):
        if not self.accepted.exists():
            return None
        return json.loads(self.accepted.read_text(encoding="utf-8"), object_pairs_hook=_no_dupes)

    @staticmethod
    def _fsync_write(path, data: bytes, exclusive: bool = False):
        import os
        with open(path, "xb" if exclusive else "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())

    def append(self, update_bytes: bytes, signature: bytes, trust: TrustList, mode: str = "production",
               expected_sequence: int | None = None) -> ExclusionState:
        import os
        acc = self._read_accepted()
        current = acc["sequence"] if acc else 0
        if expected_sequence is not None and expected_sequence != current:
            raise ExclusionError("compare-and-set failed: accepted sequence changed (concurrent update)")
        state = accept_exclusion_update(update_bytes, signature, trust, current, mode)
        self.pairs.mkdir(parents=True, exist_ok=True)
        stem = self.pairs / f"{state.sequence:08d}"
        jp, sp = stem.with_suffix(".json"), stem.with_suffix(".sig")
        if jp.exists() or sp.exists():
            raise ExclusionError("exclusion update already stored; the store is append-only")
        staging = self.dir / "staging" / f"{state.sequence:08d}"
        staging.mkdir(parents=True, exist_ok=False)
        self._fsync_write(staging / "u.json", update_bytes, True)
        self._fsync_write(staging / "u.sig", signature, True)
        os.replace(staging / "u.json", jp)
        os.replace(staging / "u.sig", sp)
        staging.rmdir()
        record = {"sequence": state.sequence, "digest": hashlib.sha256(update_bytes).hexdigest(),
                  "previous_sequence": current, "previous_digest": acc["digest"] if acc else None}
        tmp = self.dir / "ACCEPTED.json.tmp"
        self._fsync_write(tmp, json.dumps(record, sort_keys=True).encode())
        if (self._read_accepted() or {}).get("sequence", 0) != current:
            raise ExclusionError("compare-and-set failed at acceptance")
        os.replace(tmp, self.accepted)
        return state

    def load_latest(self, trust: TrustList, mode: str = "production") -> ExclusionState:
        """Re-verify the accepted update. Missing ACCEPTED record => ExclusionError (restore must not proceed)."""
        acc = self._read_accepted()
        if not acc:
            raise ExclusionError("exclusion store has no accepted state: restore/activation refused until it is present")
        stem = self.pairs / f"{acc['sequence']:08d}"
        try:
            data, sig = stem.with_suffix(".json").read_bytes(), stem.with_suffix(".sig").read_bytes()
        except OSError as exc:
            raise ExclusionError("accepted exclusion pair missing: halt protected delivery and recover") from exc
        if hashlib.sha256(data).hexdigest() != acc["digest"]:
            raise ExclusionError("accepted exclusion pair altered: halt and recover")
        return accept_exclusion_update(data, sig, trust, acc["sequence"] - 1, mode)

    def pending(self) -> list[int]:
        """Sequences present as pairs or staging but not accepted (reported as pending/failed, never as accepted)."""
        acc = (self._read_accepted() or {}).get("sequence", 0)
        seqs = [int(p.stem) for p in self.pairs.glob("*.json") if p.stem.isdigit()] if self.pairs.exists() else []
        st = [int(p.name) for p in (self.dir / "staging").glob("*") if p.name.isdigit()] if (self.dir / "staging").exists() else []
        return sorted({s for s in seqs + st if s > acc})


def state_for_restore(store: ExclusionStore, trust: TrustList, restored_db_sequence: int, mode: str = "production") -> ExclusionState:
    """The exclusion state applied after a restore is always the store's latest, never the restored database's copy."""
    latest = store.load_latest(trust, mode)
    if latest.sequence < restored_db_sequence:
        raise ExclusionError("exclusion store is older than the restored database: store tampered or lost; refuse")
    return latest
