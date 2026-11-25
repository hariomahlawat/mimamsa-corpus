"""Release bundle validation. Read-only and fail-closed: any error rejects the whole bundle.

Order of checks mirrors the offline importer (Security and Deployment Architecture, update flow):
  1 signature over SHA256SUMS (Ed25519, pinned trusted key)   2 every checksum
  3 manifest schema and compatibility                          4 restricted-material register
  5 every record against its schema and semantic rules         6 cross-record consistency
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from . import CONTRACT_MAJOR
from .issues import Issue, ValidationReport
from .restricted import RestrictedConfigError, RestrictedRegister, load_register
from .rules import record_issues, schema_issues

SUMS = "SHA256SUMS"
SIG = "SHA256SUMS.sig"
MANIFEST = "RELEASE.json"
CHANGES = "CHANGES.json"
KIND_FOR_FILE = {"documents_jsonl": "document", "derived_text_jsonl": "derived_text", "candidates_jsonl": "candidate"}
_SUM_LINE = re.compile(r"^([0-9a-f]{64}) [ *](.+)$")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def key_fingerprint(public_key_raw: bytes) -> str:
    return hashlib.sha256(public_key_raw).hexdigest()


def parse_sums(text: str) -> tuple[dict[str, str], list[str]]:
    entries, bad = {}, []
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        m = _SUM_LINE.match(line)
        if not m:
            bad.append(f"line {n}")
            continue
        digest, rel = m.group(1), m.group(2)
        if rel in entries:
            bad.append(f"duplicate {rel}")
        entries[rel] = digest
    return entries, bad


def _safe_rel(rel: str) -> bool:
    if not rel or rel.startswith(("/", "\\")) or "\\" in rel or re.match(r"^[A-Za-z]:", rel):
        return False
    return ".." not in rel.split("/")


def verify_signature(root: Path, manifest: dict, trusted_public_key: bytes | None, report: ValidationReport,
                     allow_unsigned_dev: bool) -> None:
    sig_path = root / SIG
    if trusted_public_key is None:
        if allow_unsigned_dev:
            report.add(Issue("SIGNATURE_NOT_VERIFIED", "no trusted key supplied; development mode only", SIG, "warning"))
        else:
            report.add(Issue("SIGNATURE_NOT_VERIFIED", "a pinned trusted public key is required to accept a bundle", SIG))
        return
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError:  # pragma: no cover - dependency pinned in requirements.txt
        report.add(Issue("SIGNATURE_TOOLING_MISSING", "cryptography package unavailable", SIG))
        return
    declared = (manifest.get("signature") or {}).get("key_id", "")
    fp = key_fingerprint(trusted_public_key)
    if declared.removeprefix("dev-") != fp:
        report.add(Issue("SIGNATURE_KEY_MISMATCH", "manifest key_id does not match the pinned trusted key", SIG))
        return
    if not sig_path.is_file():
        report.add(Issue("SIGNATURE_MISSING", "SHA256SUMS.sig absent", SIG))
        return
    try:
        Ed25519PublicKey.from_public_bytes(trusted_public_key).verify(sig_path.read_bytes(), (root / SUMS).read_bytes())
    except (InvalidSignature, ValueError):
        report.add(Issue("SIGNATURE_INVALID", "signature does not verify over SHA256SUMS", SIG))
        return
    report.signature_verified = True


def validate_bundle(root: Path | str, *, trusted_public_key: bytes | None = None, allow_unsigned_dev: bool = False,
                    register: RestrictedRegister | None = None, app_version: str | None = None) -> ValidationReport:
    root = Path(root)
    report = ValidationReport()
    try:
        reg = register or load_register()
    except RestrictedConfigError as exc:
        report.add(Issue("RESTRICTED_CONFIG_MISSING", str(exc)))
        return report

    sums_path, manifest_path = root / SUMS, root / MANIFEST
    if not sums_path.is_file() or not manifest_path.is_file():
        report.add(Issue("BUNDLE_INCOMPLETE", "RELEASE.json and SHA256SUMS are both required"))
        return report

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        report.add(Issue("MANIFEST_UNREADABLE", str(exc)[:200], MANIFEST))
        return report

    # 1 signature (before trusting anything the manifest says beyond the key id)
    verify_signature(root, manifest, trusted_public_key, report, allow_unsigned_dev)

    # 2 checksums: every file on disk is listed, every listed file matches, no symlinks or traversal
    entries, bad = parse_sums(sums_path.read_text(encoding="utf-8", errors="replace"))
    for b in bad:
        report.add(Issue("SUMS_MALFORMED", b, SUMS))
    on_disk = set()
    for p in root.rglob("*"):
        rel = p.relative_to(root).as_posix()
        if p.is_symlink():
            report.add(Issue("SYMLINK_IN_BUNDLE", "symbolic links are not allowed", rel))
            continue
        if p.is_file() and rel not in (SUMS, SIG):
            on_disk.add(rel)
    for rel in sorted(on_disk - set(entries)):
        report.add(Issue("UNLISTED_FILE", "file present but not in SHA256SUMS", rel))
    for rel, digest in sorted(entries.items()):
        if not _safe_rel(rel):
            report.add(Issue("UNSAFE_PATH", "path traversal or absolute path in SHA256SUMS", rel))
            continue
        fp = root / rel
        if not fp.is_file():
            report.add(Issue("MISSING_FILE", "listed in SHA256SUMS but absent", rel))
            continue
        report.checked_files += 1
        if sha256_file(fp) != digest:
            report.add(Issue("CHECKSUM_MISMATCH", "sha256 differs from SHA256SUMS", rel))
    if MANIFEST not in entries:
        report.add(Issue("MANIFEST_NOT_COVERED", "RELEASE.json must be listed in SHA256SUMS", MANIFEST))
    if CHANGES not in entries:
        report.add(Issue("CHANGES_MISSING", "CHANGES.json must be present and listed", CHANGES))

    # 3 manifest schema and compatibility
    report.extend(schema_issues("release_manifest", manifest, MANIFEST))
    compat = manifest.get("compatibility") or {}
    if compat.get("contract_major") != CONTRACT_MAJOR:
        report.add(Issue("INCOMPATIBLE_CONTRACT", f"bundle contract major {compat.get('contract_major')} != {CONTRACT_MAJOR}", MANIFEST))
    if app_version and compat.get("min_app_version"):
        if _ver(app_version) < _ver(compat["min_app_version"]):
            report.add(Issue("APP_TOO_OLD", f"app {app_version} < min_app_version {compat['min_app_version']}", MANIFEST))
    if compat.get("requires_migrations") and not manifest.get("migrations"):
        report.add(Issue("MIGRATIONS_DECLARED_MISSING", "requires_migrations is true but no migrations listed", MANIFEST))
    rb = manifest.get("rollback") or {}
    if rb.get("supported") is False:
        report.add(Issue("ROLLBACK_UNSUPPORTED", "bundle declares rollback unsupported; importer must refuse without owner override", MANIFEST, "warning"))
    listed = {}
    for f in manifest.get("files", []):
        rel = f.get("path", "")
        listed[rel] = f
        if entries.get(rel) and entries[rel] != f.get("sha256"):
            report.add(Issue("MANIFEST_SUMS_DISAGREE", "manifest sha256 differs from SHA256SUMS", rel))
        if rel not in entries:
            report.add(Issue("MANIFEST_FILE_NOT_IN_SUMS", "manifest lists a file not covered by SHA256SUMS", rel))
    for m in manifest.get("migrations", []):
        if m.get("path") not in entries:
            report.add(Issue("MIGRATION_NOT_IN_SUMS", "migration script not covered by SHA256SUMS", m.get("path", "")))

    # 4 restricted-material register: config identity, coverage, and every path and hash in the bundle
    rm = manifest.get("restricted_material") or {}
    if rm.get("config_sha256") != reg.config_sha256:
        report.add(Issue("RESTRICTED_CONFIG_DRIFT", "bundle was built against a different restricted-material register", MANIFEST))
    missing_ids = reg.restriction_ids - set(rm.get("restriction_ids_applied", []))
    if missing_ids:
        report.add(Issue("RESTRICTED_IDS_NOT_APPLIED", f"register entries not applied: {sorted(missing_ids)}", MANIFEST))
    for rel, digest in entries.items():
        reason = reg.match(sha256=digest, path=rel)
        if reason:
            report.add(Issue("RESTRICTED_MATERIAL", f"bundle file must be excluded ({reason})", rel))

    # 5 records, 6 cross-record consistency
    ledger = manifest.get("auth_ledger_version")
    banner = manifest.get("candidate_banner") or {}
    if ledger == 0 and banner.get("required") is not True:
        report.add(Issue("BANNER_REQUIRED", "candidate banner must be required while AUTH-LEDGER is at version 0", MANIFEST))
    doc_ids: set[str] = set()
    copy_shas: set[str] = set()
    pending_candidates: list[tuple[str, dict]] = []
    for rel, f in sorted(listed.items()):
        kind = KIND_FOR_FILE.get(f.get("kind"))
        if not kind or not (root / rel).is_file() or not _safe_rel(rel):
            continue
        with (root / rel).open("r", encoding="utf-8") as fh:
            for n, line in enumerate(fh, 1):
                if not line.strip():
                    continue
                where = f"{rel}:{n}"
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError as exc:
                    report.add(Issue("JSONL_MALFORMED", str(exc)[:200], where))
                    continue
                report.checked_records += 1
                report.extend(record_issues(kind, rec, reg, where, ledger))
                if kind == "document":
                    did = rec.get("doc_id")
                    if did in doc_ids:
                        report.add(Issue("DUPLICATE_DOC_ID", f"{did} appears twice", where))
                    doc_ids.add(did)
                    copy_shas.add((rec.get("source_copy") or {}).get("sha256"))
                elif kind == "candidate":
                    pending_candidates.append((where, rec))
    for where, rec in pending_candidates:
        if rec.get("source_doc_id") not in doc_ids:
            report.add(Issue("DANGLING_CANDIDATE", "candidate refers to a document not in this bundle", where))
        for a in rec.get("anchors", []):
            if a.get("source_copy_sha256") not in copy_shas:
                report.add(Issue("DANGLING_ANCHOR", "anchor refers to a source copy not in this bundle", where))
    return report


def _ver(v: str) -> tuple[int, int, int]:
    core = v.split("-", 1)[0].split(".")
    return tuple(int(x) for x in (core + ["0", "0", "0"])[:3])  # type: ignore[return-value]
