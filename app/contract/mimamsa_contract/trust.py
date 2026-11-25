"""Pinned trust list for Ed25519 signing keys, and the owner-only trust-list update channel.

Change authority: the trust list is installed by the signed installer and can be changed only by a trust-list update
signed by a key currently trusted for purpose 'trust_list' and held by the OWNER (or the OWNER_BACKUP_CUSTODIAN).
Site Admins have no path to add, replace or re-purpose keys. In production mode keys whose holder is DEVELOPMENT or
whose key_id starts with 'dev-' are never used.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date

from .schemas import validator

OWNER_HOLDERS = {"OWNER", "OWNER_BACKUP_CUSTODIAN"}


class TrustError(ValueError):
    pass


def fingerprint(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class TrustedKey:
    key_id: str
    raw: bytes
    holder: str
    purposes: frozenset
    revoked: bool
    valid_until: str | None = None

    @property
    def is_dev(self) -> bool:
        return self.holder == "DEVELOPMENT" or self.key_id.startswith("dev-")


@dataclass(frozen=True)
class TrustList:
    sequence: int
    keys: tuple

    def usable(self, purpose: str, mode: str = "production", today: date | None = None):
        """today must come from the site's trusted time source; keys past valid_until are never used."""
        today_s = (today or date.today()).isoformat()
        for k in self.keys:
            if k.revoked or purpose not in k.purposes:
                continue
            if k.valid_until and k.valid_until < today_s:
                continue
            if mode == "production" and k.is_dev:
                continue
            yield k


def parse_trust_list(data: dict) -> TrustList:
    errs = list(validator("trust_list").iter_errors(data))
    if errs:
        raise TrustError(f"trust list invalid: {errs[0].message[:200]}")
    keys = []
    for k in data["keys"]:
        raw = bytes.fromhex(k["public_key_hex"])
        if k["key_id"].removeprefix("dev-") != fingerprint(raw):
            raise TrustError("trust list key_id does not match its public key")
        if k["key_id"].startswith("dev-") != (k["holder"] == "DEVELOPMENT"):
            raise TrustError("dev- key ids are exactly the DEVELOPMENT holder keys")
        keys.append(TrustedKey(k["key_id"], raw, k["holder"], frozenset(k["purposes"]), k["revoked"], k.get("valid_until")))
    return TrustList(data["sequence"], tuple(keys))


def verify_detached(data: bytes, signature: bytes, trust: TrustList, purpose: str, mode: str = "production",
                    today: date | None = None):
    """Return the TrustedKey that verifies, or None."""
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    for k in trust.usable(purpose, mode, today):
        try:
            Ed25519PublicKey.from_public_bytes(k.raw).verify(signature, data)
            return k
        except (InvalidSignature, ValueError):
            continue
    return None


def apply_trust_list_update(current: TrustList, update_bytes: bytes, signature: bytes, mode: str = "production") -> TrustList:
    signer = verify_detached(update_bytes, signature, current, "trust_list", mode)
    if signer is None:
        raise TrustError("trust-list update not signed by a currently trusted trust_list key")
    if mode == "production" and signer.holder not in OWNER_HOLDERS:
        raise TrustError("trust-list updates must be signed by an owner-held key")
    try:
        new = parse_trust_list(json.loads(update_bytes.decode("utf-8")))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TrustError(f"trust-list update unreadable: {exc}") from exc
    if new.sequence <= current.sequence:
        raise TrustError("trust-list update sequence must increase (replay/downgrade refused)")
    if not any(True for _ in new.usable("trust_list", mode)):
        raise TrustError("update would leave no usable trust_list key")
    return new
