"""Exact, expiring owner approval for one WP1 read-only operation."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

from hf_inventory_metadata import HEX40, HEX64, REPO, STORES
from hf_inventory_provider import ENDPOINT

PLAN_NAME = "WP1_METADATA_COMMISSIONING_PLAN.json"
GIT_PATH = "legal_knowledge/audit_work/C14-CA01-STATUTORY/"
RUNTIME_PATHS = (
    "config/restricted_material.json",
    "scripts/restricted_material.py",
    GIT_PATH + PLAN_NAME,
    *(GIT_PATH + "runner/" + name + ".py" for name in (
        "hf_inventory_metadata", "hf_inventory_provider", "inventory_coverage",
        "hf_metadata_approval", "hf_metadata_credential", "hf_metadata_job",
        "hf_metadata_transport", "hf_metadata_windows",
    )),
)
MAX_APPROVAL_BYTES = 16_384
PINS = ("revision", "code_commit", "runtime_sha256", "plan_sha256", "register_blob", "guard_blob", "jobs_root_sha256")


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")


def bounded(path, limit):
    with Path(path).open("rb") as stream:
        data = stream.read(limit + 1)
    if not 0 < len(data) <= limit:
        raise ValueError("invalid input size")
    return data


def snapshot_runtime(root):
    files = {}
    for relative in RUNTIME_PATHS:
        path = root / relative
        if path.resolve(strict=True) != path or not path.is_file():
            raise ValueError("runtime must use a canonical standalone checkout")
        files[relative] = bounded(path, 1_000_000)
    return files


def approval_payload(*, revision, code_commit, runtime_sha256, plan_sha256, register_blob,
                     guard_blob, jobs_root_sha256, job_name, now, deployment_sha256=None):
    pins = dict(zip(PINS, (revision, code_commit, runtime_sha256, plan_sha256,
                          register_blob, guard_blob, jobs_root_sha256), strict=True))
    for name, value in pins.items():
        pattern = HEX64 if name.endswith("sha256") else HEX40
        if not isinstance(value, str) or not pattern.fullmatch(value):
            raise ValueError("invalid immutable approval pin")
    if deployment_sha256 is not None:
        if not isinstance(deployment_sha256, str) or not HEX64.fullmatch(deployment_sha256):
            raise ValueError("invalid cloud deployment pin")
        pins["deployment_sha256"] = deployment_sha256
    now = now.astimezone(timezone.utc).replace(microsecond=0)
    return {
        "schema": ("c14-wp1-isolated-cloud-owner-approval-v1" if deployment_sha256 is not None
                   else "c14-wp1-metadata-owner-approval-v1"),
        "operation": "METADATA_GET_ONLY",
        "endpoint": ENDPOINT,
        "repository": REPO,
        "repo_type": "dataset",
        "roots": list(STORES),
        "credential_scope_attested": True,
        "job_name": job_name,
        "issued_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_utc": (now + timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        **pins,
    }


def strict_json(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("duplicate JSON key")
            value[key] = item
        return value

    def nonfinite(_):
        raise ValueError("nonfinite JSON value")

    return json.loads(raw, object_pairs_hook=unique, parse_constant=nonfinite)


def verify_approval(raw, signature, public, fingerprint, *, expected, now):
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    if not 0 < len(raw) <= MAX_APPROVAL_BYTES or len(signature) != 64 or len(public) > 4096:
        raise ValueError("invalid approval input size")
    key = load_pem_public_key(public)
    if not isinstance(key, Ed25519PublicKey) or sha256(key.public_bytes_raw()) != fingerprint:
        raise ValueError("owner key pin mismatch")
    try:
        key.verify(signature, raw)
    except InvalidSignature:
        raise ValueError("invalid owner approval signature") from None
    payload = strict_json(raw)
    template = approval_payload(**expected, now=now)
    if not isinstance(payload, dict) or set(payload) != set(template):
        raise ValueError("invalid approval shape")
    for name in set(template) - {"issued_utc", "expires_utc"}:
        if canonical(payload[name]) != canonical(template[name]):
            raise ValueError("approval scope mismatch")
    issued = datetime.strptime(payload["issued_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    expires = datetime.strptime(payload["expires_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    if not issued <= now < expires or expires - issued > timedelta(hours=4):
        raise ValueError("owner approval expired or outside validity")
