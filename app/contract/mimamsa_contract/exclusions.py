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
