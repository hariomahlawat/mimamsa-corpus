"""DEVELOPMENT-ONLY bundle writer used by the contract tests and Track A dry runs.

Keys created here are disposable, live only in memory or a scratch directory, and are marked 'dev-' in the
manifest. Production signing keys are owner-held and never generated, stored or used by this repository.
This writer does not consult the restricted-material register on purpose: tests use it to build hostile bundles
and prove the validator rejects them. A real build_release tool must filter with the register before writing.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .bundle import CHANGES, MANIFEST, SIG, SUMS, key_fingerprint


def new_dev_keypair():
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    sk = Ed25519PrivateKey.generate()
    pk_raw = sk.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    return sk, pk_raw


def trust_list_for(keys, *, sequence=1):
    """Build a trust-list dict from [(public_key_raw, holder, purposes)]. Test use only; keys are disposable."""
    out = []
    for raw, holder, purposes in keys:
        fp = key_fingerprint(raw)
        out.append({"key_id": ("dev-" if holder == "DEVELOPMENT" else "") + fp, "public_key_hex": raw.hex(),
                    "holder": holder, "purposes": list(purposes), "valid_until": None, "revoked": False})
    return {"contract_version": "1.0.0", "record_kind": "trust_list", "sequence": sequence,
            "issued_at": "2026-11-25T00:00:00Z", "keys": out}


def _jsonl(records) -> bytes:
    return "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in records).encode("utf-8")


def write_bundle(root: Path, manifest: dict, *, documents=(), derived=(), candidates=(), extra_files=None,
                 changes=None, signing_key=None, public_key_raw: bytes | None = None, dev_key: bool = True,
                 reviews=(), approvals=(), appointments=(), publication_records=()) -> Path:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    payloads: dict[str, tuple[bytes, str]] = {
        "data/documents.jsonl": (_jsonl(documents), "documents_jsonl"),
        "data/derived_text.jsonl": (_jsonl(derived), "derived_text_jsonl"),
        "data/candidates.jsonl": (_jsonl(candidates), "candidates_jsonl"),
        "data/reviewed_records.jsonl": (_jsonl(reviews), "reviewed_records_jsonl"),
        "data/appointments.jsonl": (_jsonl(appointments), "appointments_jsonl"),
        "data/approvals.jsonl": (_jsonl(approvals), "approvals_jsonl"),
        "data/publication_records.jsonl": (_jsonl(publication_records), "publication_records_jsonl"),
        CHANGES: (json.dumps(changes or {"added": [], "updated": [], "newly_superseded": [], "withdrawn": [], "status_changed": []}, indent=1).encode(), "changes"),
    }
    for rel, (data, kind) in (extra_files or {}).items():
        payloads[rel] = (data, kind)
    files = []
    for rel, (data, kind) in payloads.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        files.append({"path": rel, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data), "kind": kind})
    manifest = dict(manifest)
    manifest["files"] = files
    if public_key_raw is not None:
        manifest["signature"] = dict(manifest["signature"], key_id=("dev-" if dev_key else "") + key_fingerprint(public_key_raw))
    mbytes = json.dumps(manifest, indent=1, sort_keys=True).encode()
    (root / MANIFEST).write_bytes(mbytes)
    lines = []
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if p.is_file() and rel not in (SUMS, SIG):
            lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {rel}\n")
    sums = "".join(lines).encode()
    (root / SUMS).write_bytes(sums)
    if signing_key is not None:
        (root / SIG).write_bytes(signing_key.sign(sums))
    return root
