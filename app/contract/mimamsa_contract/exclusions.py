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
    readmitted_doc_ids: frozenset = field(default_factory=frozenset)
    readmitted_shas: frozenset = field(default_factory=frozenset)
    # Monotone tombstones folded over the accepted history (see ExclusionStore.effective_state):
    tombstone_doc_ids: frozenset = field(default_factory=frozenset)
    tombstone_shas: frozenset = field(default_factory=frozenset)
    restricted_tombstone_doc_ids: frozenset = field(default_factory=frozenset)
    restricted_tombstone_shas: frozenset = field(default_factory=frozenset)


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
    for w in data["withdrawals"] + data.get("readmissions", []):
        if not (w.get("doc_id") or w.get("source_copy_sha256")):
            raise ExclusionError("withdrawal/readmission row names neither a doc_id nor a source copy hash; update rejected")
    reg_bytes = data["register_json"].encode("utf-8")
    if hashlib.sha256(reg_bytes).hexdigest() != data["register_sha256"]:
        raise ExclusionError("register_sha256 does not match register_json")
    reg = register_from_bytes(reg_bytes, "exclusion_update")
    return ExclusionState(
        sequence=data["sequence"], register=reg,
        withdrawn_doc_ids=frozenset(w["doc_id"] for w in data["withdrawals"] if w.get("doc_id")),
        withdrawn_shas=frozenset(w["source_copy_sha256"] for w in data["withdrawals"] if w.get("source_copy_sha256")),
        readmitted_doc_ids=frozenset(w["doc_id"] for w in data.get("readmissions", []) if w.get("doc_id")),
        readmitted_shas=frozenset(w["source_copy_sha256"] for w in data.get("readmissions", []) if w.get("source_copy_sha256")),
    )


def items_to_suppress(items, state: ExclusionState) -> list[tuple[str, str]]:
    """items: iterable of document records (or dicts with doc_id and source_copy.sha256) in the generation being
    activated. Returns (doc_id, reason) for every item that must be removed from search, vectors, graph, caches and
    exports before the generation serves any request."""
    out = []
    for it in items:
        did = it.get("doc_id")
        sha = (it.get("source_copy") or {}).get("sha256") or it.get("sha256")
        if (state.register.deep_match(it) or did in state.restricted_tombstone_doc_ids
                or sha in state.restricted_tombstone_shas):
            out.append((did, "RESTRICTED"))
        elif (did in state.withdrawn_doc_ids or sha in state.withdrawn_shas
              or did in state.tombstone_doc_ids or sha in state.tombstone_shas):
            out.append((did, "WITHDRAWN"))
    return out


class ExclusionStore:
    """Append-only store of accepted, signed exclusion updates, kept OUTSIDE the database and the release generations
    (site path D:\\Mimamsa\\exclusions\\, excluded from restore). Restore cannot remove or roll it back.

    Protocol (reference for PR #53 Serving §4/§8; single writer enforced by an exclusive LOCK file):
      1 stage payload + signature under staging/<seq>/ and flush;
      2 move the complete pair write-once into pairs/<seq:08d>.{json,sig};
      3 accept by compare-and-set of ACCEPTED.json (expected prior sequence + digest), flushed and atomically replaced.
        ACCEPTED is the sole acceptance point; it records operation id, sequence, digest, signature digest, epoch and
        the accepted history (sequence, digest) used to fold monotone tombstones.
    Restart cases: a stored pair without acceptance is pending and can be completed (complete_pending or re-append of
    the identical bytes); staging residue is moved to quarantine/ (never deleted, never accepted); a retry after a lost
    acknowledgement with the same operation id and digest returns the original acknowledgement; different bytes for an
    already stored sequence are rejected. All filesystem failures surface as ExclusionError.
    Durability on the actual Windows storage is proven in P8/B2; custody of an independent witness copy is an owner
    decision. Local Admin withdrawals are NOT in this store yet (conflict X7).
    """

    def __init__(self, directory):
        from pathlib import Path
        self.dir = Path(directory)
        self.pairs = self.dir / "pairs"
        self.accepted = self.dir / "ACCEPTED.json"
        self.lockfile = self.dir / "LOCK"

    # -- helpers
    def _read_accepted(self):
        if not self.accepted.exists():
            return None
        try:
            return json.loads(self.accepted.read_text(encoding="utf-8"), object_pairs_hook=_no_dupes)
        except (OSError, ValueError) as exc:
            raise ExclusionError("ACCEPTED record unreadable: halt and recover") from exc

    @staticmethod
    def _fsync_write(path, data: bytes, exclusive: bool = False):
        import os
        with open(path, "xb" if exclusive else "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())

    def _lock(self):
        import os
        self.dir.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.lockfile, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise ExclusionError("exclusion store is locked by another writer (or a stale LOCK needs recovery)") from exc
        os.close(fd)

    def _unlock(self):
        try:
            self.lockfile.unlink()
        except OSError:
            pass

    def _quarantine_staging(self, seq: int):
        import os
        import time
        st = self.dir / "staging" / f"{seq:08d}"
        if st.exists():
            q = self.dir / "quarantine"
            q.mkdir(parents=True, exist_ok=True)
            os.replace(st, q / f"{seq:08d}-{time.time_ns()}")

    def _accept(self, acc, state, update_bytes, signature, operation_id):
        import os
        digest = hashlib.sha256(update_bytes).hexdigest()
        history = list((acc or {}).get("history", [])) + [[state.sequence, digest, operation_id or f"seq-{state.sequence}-{digest[:16]}"]]
        record = {"operation_id": operation_id or f"seq-{state.sequence}-{digest[:16]}",
                  "sequence": state.sequence, "digest": digest,
                  "signature_sha256": hashlib.sha256(signature).hexdigest(),
                  "epoch": (acc or {}).get("epoch", 0) + 1,
                  "previous_sequence": (acc or {}).get("sequence", 0), "previous_digest": (acc or {}).get("digest"),
                  "history": history}
        tmp = self.dir / "ACCEPTED.json.tmp"
        self._fsync_write(tmp, json.dumps(record, sort_keys=True).encode())
        if (self._read_accepted() or {}).get("sequence", 0) != (acc or {}).get("sequence", 0):
            raise ExclusionError("compare-and-set failed at acceptance")
        os.replace(tmp, self.accepted)
        return self._ack(record)

    @staticmethod
    def _ack(record):
        return {k: record[k] for k in ("operation_id", "sequence", "digest", "epoch")}

    # -- operations
    def append(self, update_bytes: bytes, signature: bytes, trust: TrustList, mode: str = "production",
               expected_sequence: int | None = None, operation_id: str | None = None) -> dict:
        """Store and accept one signed update. Returns the acknowledgement {operation_id, sequence, digest, epoch}."""
        import os
        self._lock()
        try:
            acc = self._read_accepted()
            current = acc["sequence"] if acc else 0
            digest = hashlib.sha256(update_bytes).hexdigest()
            if operation_id:
                for entry in (acc or {}).get("history", []):
                    if len(entry) > 2 and entry[2] == operation_id and entry[1] != digest:
                        raise ExclusionError("operation id already used for a different update; refuse")
            if acc and acc["digest"] == digest:  # lost acknowledgement: idempotent retry
                if operation_id and operation_id != acc["operation_id"]:
                    raise ExclusionError("same update already accepted under a different operation id")
                return self._ack(acc)
            if expected_sequence is not None and expected_sequence != current:
                raise ExclusionError("compare-and-set failed: accepted sequence changed (concurrent update)")
            state = accept_exclusion_update(update_bytes, signature, trust, current, mode)
            self.pairs.mkdir(parents=True, exist_ok=True)
            stem = self.pairs / f"{state.sequence:08d}"
            jp, sp = stem.with_suffix(".json"), stem.with_suffix(".sig")
            if jp.exists() and not sp.exists() and jp.read_bytes() == update_bytes:
                # Crash between the two moves: the lone payload is quarantined and the pair restaged (C1).
                q = self.dir / "quarantine"
                q.mkdir(parents=True, exist_ok=True)
                os.replace(jp, q / f"{state.sequence:08d}-lone-{digest[:12]}.json")
            if jp.exists() or sp.exists():
                # Pending pair from an interrupted earlier attempt: resume only if it is byte-identical.
                if not (jp.exists() and sp.exists() and jp.read_bytes() == update_bytes and sp.read_bytes() == signature):
                    raise ExclusionError("different bytes already stored for this sequence; refuse (investigate)")
                return self._accept(acc, state, update_bytes, signature, operation_id)
            self._quarantine_staging(state.sequence)
            staging = self.dir / "staging" / f"{state.sequence:08d}"
            staging.mkdir(parents=True)
            self._fsync_write(staging / "u.json", update_bytes, True)
            self._fsync_write(staging / "u.sig", signature, True)
            os.replace(staging / "u.json", jp)
            os.replace(staging / "u.sig", sp)
            staging.rmdir()
            return self._accept(acc, state, update_bytes, signature, operation_id)
        except OSError as exc:
            raise ExclusionError(f"exclusion store I/O failure: {type(exc).__name__}") from exc
        finally:
            self._unlock()

    def complete_pending(self, sequence: int, trust: TrustList, mode: str = "production",
                         operation_id: str | None = None) -> dict:
        """Revalidate a stored but unaccepted pair and accept it (restart case 'verified pair durable, not accepted')."""
        stem = self.pairs / f"{sequence:08d}"
        try:
            data, sig = stem.with_suffix(".json").read_bytes(), stem.with_suffix(".sig").read_bytes()
        except OSError as exc:
            raise ExclusionError("pending pair incomplete or missing; cannot complete") from exc
        return self.append(data, sig, trust, mode, operation_id=operation_id)

    def load_latest(self, trust: TrustList, mode: str = "production") -> ExclusionState:
        """Re-verify the accepted update. Missing ACCEPTED record => ExclusionError (restore must not proceed)."""
        acc = self._read_accepted()
        if not acc:
            raise ExclusionError("exclusion store has no accepted state: restore/activation refused until it is present")
        data, sig = self._pair(acc["sequence"], acc["digest"])
        return accept_exclusion_update(data, sig, trust, acc["sequence"] - 1, mode)

    def _pair(self, seq, digest):
        stem = self.pairs / f"{seq:08d}"
        try:
            data, sig = stem.with_suffix(".json").read_bytes(), stem.with_suffix(".sig").read_bytes()
        except OSError as exc:
            raise ExclusionError("accepted exclusion pair missing: halt protected delivery and recover") from exc
        if hashlib.sha256(data).hexdigest() != digest:
            raise ExclusionError("accepted exclusion pair altered: halt and recover")
        return data, sig

    def effective_state(self, trust: TrustList, mode: str = "production") -> ExclusionState:
        """Latest verified state plus monotone tombstones folded over the accepted history: anything ever withdrawn or
        restricted stays denied unless a later accepted update readmits that exact identity. Earlier entries are
        checked by their recorded digest (their signing keys may since have rotated)."""
        latest = self.load_latest(trust, mode)
        acc = self._read_accepted()
        hist = acc.get("history", [])
        seqs = [h[0] for h in hist]
        if (not hist or seqs != sorted(set(seqs)) or hist[-1][0] != acc["sequence"] or hist[-1][1] != acc["digest"]):
            raise ExclusionError("acceptance history inconsistent (order or head mismatch): halt and recover")
        on_disk = {int(q.stem) for q in self.pairs.glob("*.json") if q.stem.isdigit() and int(q.stem) <= acc["sequence"]}
        if not on_disk <= set(seqs):
            raise ExclusionError("stored pair within the accepted range is missing from the history: halt and recover")
        docs, shas, rdocs, rshas = set(), set(), set(), set()
        for entry in hist:
            seq, digest = entry[0], entry[1]
            data = json.loads(self._pair(seq, digest)[0].decode("utf-8"), object_pairs_hook=_no_dupes)
            for w in data.get("readmissions", []):
                docs.discard(w.get("doc_id"))
                shas.discard(w.get("source_copy_sha256"))
                if w.get("restriction_id"):  # lifting a restriction needs the explicit restriction id
                    rdocs.discard(w.get("doc_id"))
                    rshas.discard(w.get("source_copy_sha256"))
            for w in data["withdrawals"]:
                if w.get("doc_id"):
                    docs.add(w["doc_id"])
                if w.get("source_copy_sha256"):
                    shas.add(w["source_copy_sha256"])
            reg = register_from_bytes(data["register_json"].encode("utf-8"), "history")
            lifted = {w.get(k) for w in data.get("readmissions", []) if w.get("restriction_id")
                      for k in ("doc_id", "source_copy_sha256")}
            rdocs |= {d for d in reg.doc_ids if d not in lifted}
            rshas |= {h for h in reg.sha256s if h not in lifted}
        return ExclusionState(latest.sequence, latest.register, latest.withdrawn_doc_ids, latest.withdrawn_shas,
                              latest.readmitted_doc_ids, latest.readmitted_shas, frozenset(docs), frozenset(shas),
                              frozenset(rdocs), frozenset(rshas))

    def pending(self) -> list[int]:
        """Sequences present as pairs or staging but not accepted (reported as pending/failed, never as accepted)."""
        acc = (self._read_accepted() or {}).get("sequence", 0)
        seqs = [int(p.stem) for p in self.pairs.glob("*.json") if p.stem.isdigit()] if self.pairs.exists() else []
        st = [int(p.name) for p in (self.dir / "staging").glob("*") if p.name.isdigit()] if (self.dir / "staging").exists() else []
        return sorted({x for x in seqs + st if x > acc})


def state_for_restore(store: ExclusionStore, trust: TrustList, restored_db_sequence: int, mode: str = "production") -> ExclusionState:
    """The exclusion state applied after a restore is always the store's latest, never the restored database's copy."""
    latest = store.effective_state(trust, mode)
    if latest.sequence < restored_db_sequence:
        raise ExclusionError("exclusion store is older than the restored database: store tampered or lost; refuse")
    return latest
