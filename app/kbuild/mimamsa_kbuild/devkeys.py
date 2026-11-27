"""DEVELOPMENT signing keys only (WD-11). Operational keys are owner-held and never touch this tool (WD-12, OG-2).

A development key is a 32-byte Ed25519 seed stored as hex in a file OUTSIDE the repository (default
<out-root>/dev-keys/release-dev.key). The trust list written next to a signed bundle names it with a dev- key id and
holder DEVELOPMENT, so a production-mode site refuses it (SIGNATURE_DEV_KEY_IN_PRODUCTION). The private seed is never
copied into a stage directory, a manifest or a log.
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path

from mimamsa_contract.devbundle import trust_list_for
from mimamsa_contract.trust import fingerprint

from .errors import BuildRefused


def ensure_dev_key(path: Path) -> Path:
    """Create a random development seed if the file does not exist (development hosts and CI only)."""
    path = Path(path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as fh:
            fh.write(secrets.token_hex(32) + "\n")
    return path


def load_dev_key(path: Path | None):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    if path is None or not Path(path).is_file():
        raise BuildRefused("BUILD_DEV_KEY_MISSING", "development signing key file not found (pass --dev-key)")
    try:
        seed = bytes.fromhex(Path(path).read_text(encoding="ascii").strip())
        if len(seed) != 32:
            raise ValueError("seed must be 32 bytes")
    except (ValueError, UnicodeDecodeError) as exc:
        raise BuildRefused("BUILD_DEV_KEY_INVALID", f"development key file unreadable: {type(exc).__name__}") from exc
    sk = Ed25519PrivateKey.from_private_bytes(seed)
    pub = sk.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return sk, pub


def dev_key_id(pub: bytes) -> str:
    return "dev-" + fingerprint(pub)


def dev_trust_list(pub: bytes) -> dict:
    return trust_list_for([(pub, "DEVELOPMENT", ["release"])], sequence=1)
