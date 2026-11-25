"""Release bundle validation. Read-only and fail-closed: any error rejects the whole bundle.

Order (mirrors the offline importer, Security and Deployment Architecture §8.2):
  1 signature over the exact SHA256SUMS bytes, against the pinned trust list (purpose 'release'); nothing else in the
    bundle is read or parsed before this succeeds
  2 every checksum, every path (Windows and POSIX hazards, case collisions, links/reparse points); stop on failure
  3 manifest (duplicate keys rejected), schema, signer identity, compatibility, downgrade/replay, ledger pin
  4 restricted-material register
  5 every record against its schema and semantic rules, with bundle-wide cross-references
  6 cross-record consistency
Production mode (default) requires a trust list and refuses development keys. Development mode accepts a bare
trusted public key, dev- key ids and (with allow_unsigned_dev) an unsigned bundle.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from . import CONTRACT_MAJOR
from .issues import Issue, ValidationReport
from .paths import case_collisions, is_link_or_reparse, path_hazard
from .restricted import RestrictedConfigError, RestrictedRegister, load_register
from .rules import BundleContext, record_issues, schema_issues
from .trust import TrustList, TrustedKey, fingerprint, verify_detached

SUMS = "SHA256SUMS"
SIG = "SHA256SUMS.sig"
MANIFEST = "RELEASE.json"
CHANGES = "CHANGES.json"
KIND_FOR_FILE = {
    "documents_jsonl": "document", "derived_text_jsonl": "derived_text", "candidates_jsonl": "candidate",
    "reviewed_records_jsonl": "reviewed_record", "appointments_jsonl": "appointment_record",
    "approvals_jsonl": "approval_record", "publication_records_jsonl": "publication_record",
}
# Context records are loaded first so that documents and candidates can resolve their references.
LOAD_ORDER = ["appointment_record", "approval_record", "reviewed_record", "document", "derived_text", "candidate", "publication_record"]
_SUM_LINE = re.compile(r"^([0-9a-f]{64}) [ *](.+)$")
MAX_SUMS_BYTES = 16 * 1024 * 1024
MAX_LINE_BYTES = 1024 * 1024
MAX_RECORDS = 5_000_000


class DuplicateKeyError(ValueError):
    pass


def _no_dupes(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise DuplicateKeyError(f"duplicate key {k!r}")
        d[k] = v
    return d


def strict_loads(text: str):
    return json.loads(text, object_pairs_hook=_no_dupes)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def key_fingerprint(public_key_raw: bytes) -> str:
    return fingerprint(public_key_raw)


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


def _signature_step(root: Path, report: ValidationReport, *, trust_list: TrustList | None, trusted_public_key: bytes | None,
                    mode: str, allow_unsigned_dev: bool) -> TrustedKey | None | bool:
    """Returns the verifying key, True for an accepted unsigned dev bundle, or None on failure (already reported)."""
    sums_bytes = (root / SUMS).read_bytes()
    sig_path = root / SIG
    if mode == "production":
        if trust_list is None:
            report.add(Issue("TRUST_LIST_REQUIRED", "production validation needs the pinned trust list", SIG))
            return None
        trust = trust_list
    else:
        if trust_list is not None:
            trust = trust_list
        elif trusted_public_key is not None:
            fp = fingerprint(trusted_public_key)
            trust = TrustList(0, (TrustedKey("dev-" + fp, trusted_public_key, "DEVELOPMENT", frozenset({"release"}), False),))
        elif allow_unsigned_dev:
            report.add(Issue("SIGNATURE_NOT_VERIFIED", "no trusted key supplied; development mode only", SIG, "warning"))
            return True
        else:
            report.add(Issue("SIGNATURE_NOT_VERIFIED", "a trusted key or trust list is required", SIG))
            return None
    if not sig_path.is_file():
        report.add(Issue("SIGNATURE_MISSING", "SHA256SUMS.sig absent", SIG))
        return None
    signer = verify_detached(sums_bytes, sig_path.read_bytes(), trust, "release", mode)
    if signer is None:
        # Distinguish a dev key presented in production, for a clear message.
        if mode == "production" and verify_detached(sums_bytes, sig_path.read_bytes(), trust, "release", "development"):
            report.add(Issue("SIGNATURE_DEV_KEY_IN_PRODUCTION", "bundle signed with a development key; refused in production", SIG))
        else:
            report.add(Issue("SIGNATURE_INVALID", "signature does not verify over SHA256SUMS with any trusted release key", SIG))
        return None
    report.signature_verified = True
    return signer


def validate_bundle(root: Path | str, *, trust_list: TrustList | None = None, trusted_public_key: bytes | None = None,
                    mode: str = "production", allow_unsigned_dev: bool = False,
                    register: RestrictedRegister | None = None, app_version: str | None = None,
                    current_release_sequence: int | None = None, rollback: bool = False,
                    trusted_ledger_head: str | None = None) -> ValidationReport:
    root = Path(root)
    report = ValidationReport()
    if mode not in ("production", "development"):
        report.add(Issue("MODE_INVALID", "mode must be production or development"))
        return report
    if allow_unsigned_dev and mode != "development":
        report.add(Issue("MODE_INVALID", "allow_unsigned_dev is only valid in development mode"))
        return report
    try:
        reg = register or load_register()
    except RestrictedConfigError as exc:
        report.add(Issue("RESTRICTED_CONFIG_MISSING", str(exc)))
        return report

    sums_path, manifest_path = root / SUMS, root / MANIFEST
    if not sums_path.is_file() or not manifest_path.is_file():
        report.add(Issue("BUNDLE_INCOMPLETE", "RELEASE.json and SHA256SUMS are both required"))
        return report
    if sums_path.stat().st_size > MAX_SUMS_BYTES:
        report.add(Issue("SUMS_TOO_LARGE", "SHA256SUMS exceeds size cap", SUMS))
        return report

    # 1 signature: before anything else in the bundle is read
    signer = _signature_step(root, report, trust_list=trust_list, trusted_public_key=trusted_public_key, mode=mode,
                             allow_unsigned_dev=allow_unsigned_dev)
    if signer is None:
        return report

    # 2 checksums and paths: stop on any failure, no record is parsed
    entries, bad = parse_sums(sums_path.read_text(encoding="utf-8", errors="replace"))
    for b in bad:
        report.add(Issue("SUMS_MALFORMED", b, SUMS))
    on_disk = set()
    for p in root.rglob("*"):
        rel = p.relative_to(root).as_posix()
        if is_link_or_reparse(p):
            report.add(Issue("SYMLINK_IN_BUNDLE", "symbolic links, junctions and reparse points are not allowed", rel))
            continue
        if p.is_file() and rel not in (SUMS, SIG):
            on_disk.add(rel)
    for rel in sorted(set(entries) | on_disk):
        reason = path_hazard(rel)
        if reason:
            report.add(Issue("PATH_HAZARD", f"unsafe path ({reason})", rel))
        if rel.casefold().startswith("sessions/"):
            report.add(Issue("WORKING_DOCUMENT_IN_BUNDLE", "working-session files (layer 9) are never exchanged", rel))
    for a, b in case_collisions(sorted(set(entries) | on_disk)):
        report.add(Issue("CASE_COLLISION", "paths differ only by case (alias on NTFS)", f"{a} | {b}"))
    for rel in sorted(on_disk - set(entries)):
        report.add(Issue("UNLISTED_FILE", "file present but not in SHA256SUMS", rel))
    for rel, digest in sorted(entries.items()):
        fp = root / rel
        if path_hazard(rel) or not fp.is_file():
            if not path_hazard(rel):
                report.add(Issue("MISSING_FILE", "listed in SHA256SUMS but absent", rel))
            continue
        report.checked_files += 1
        if sha256_file(fp) != digest:
            report.add(Issue("CHECKSUM_MISMATCH", "sha256 differs from SHA256SUMS", rel))
    if MANIFEST not in entries:
        report.add(Issue("MANIFEST_NOT_COVERED", "RELEASE.json must be listed in SHA256SUMS", MANIFEST))
    if CHANGES not in entries:
        report.add(Issue("CHANGES_MISSING", "CHANGES.json must be present and listed", CHANGES))
    if report.errors:
        return report

    # 3 manifest
    try:
        manifest = strict_loads(manifest_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, DuplicateKeyError) as exc:
        report.add(Issue("MANIFEST_UNREADABLE", str(exc)[:200], MANIFEST))
        return report
    report.extend(schema_issues("release_manifest", manifest, MANIFEST))
    declared = (manifest.get("signature") or {}).get("key_id", "")
    if isinstance(signer, TrustedKey):
        if declared.removeprefix("dev-") != signer.key_id.removeprefix("dev-"):
            report.add(Issue("SIGNATURE_KEY_MISMATCH", "manifest key_id is not the key that verified the signature", MANIFEST))
    if mode == "production" and declared.startswith("dev-"):
        report.add(Issue("SIGNATURE_DEV_KEY_IN_PRODUCTION", "dev- key id refused in production", MANIFEST))
    compat = manifest.get("compatibility") or {}
    if compat.get("contract_major") != CONTRACT_MAJOR:
        report.add(Issue("INCOMPATIBLE_CONTRACT", f"bundle contract major {compat.get('contract_major')} != {CONTRACT_MAJOR}", MANIFEST))
    if app_version and compat.get("min_app_version") and _ver(app_version) < _ver(compat["min_app_version"]):
        report.add(Issue("APP_TOO_OLD", f"app {app_version} < min_app_version {compat['min_app_version']}", MANIFEST))
    if compat.get("requires_migrations") and not manifest.get("migrations"):
        report.add(Issue("MIGRATIONS_DECLARED_MISSING", "requires_migrations is true but no migrations listed", MANIFEST))
    seq = manifest.get("release_sequence")
    if current_release_sequence is not None and isinstance(seq, int) and seq <= current_release_sequence and not rollback:
        report.add(Issue("DOWNGRADE_OR_REPLAY", f"release_sequence {seq} not newer than active {current_release_sequence}; use the rollback path", MANIFEST))
    ledger = manifest.get("auth_ledger_version")
    if isinstance(ledger, int) and ledger > 0:
        head = manifest.get("auth_ledger_head")
        pinned = bool(head and trusted_ledger_head and (trusted_ledger_head.startswith(head) or head.startswith(trusted_ledger_head)))
        if not pinned:
            report.add(Issue("LEDGER_HEAD_UNVERIFIED", "auth_ledger_version > 0 requires auth_ledger_head matching the site's trusted ledger state", MANIFEST))
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

    # 4 restricted-material register
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
    hit = reg.deep_match(manifest)
    if hit:
        report.add(Issue("RESTRICTED_MATERIAL", f"manifest field {hit[0]} refers to restricted material", MANIFEST))

    # 5 records
    banner = manifest.get("candidate_banner") or {}
    if ledger == 0 and banner.get("required") is not True:
        report.add(Issue("BANNER_REQUIRED", "candidate banner must be required while AUTH-LEDGER is at version 0", MANIFEST))
    by_kind: dict[str, list[tuple[str, dict]]] = {k: [] for k in LOAD_ORDER}
    total = 0
    for rel, f in sorted(listed.items()):
        kind = KIND_FOR_FILE.get(f.get("kind"))
        if not kind or not (root / rel).is_file() or path_hazard(rel):
            continue
        with (root / rel).open("rb") as fh:
            for n, raw in enumerate(fh, 1):
                where = f"{rel}:{n}"
                if len(raw) > MAX_LINE_BYTES:
                    report.add(Issue("RECORD_TOO_LARGE", "JSONL line exceeds size cap", where))
                    continue
                if not raw.strip():
                    continue
                total += 1
                if total > MAX_RECORDS:
                    report.add(Issue("TOO_MANY_RECORDS", "record count cap exceeded", rel))
                    break
                try:
                    rec = strict_loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError, DuplicateKeyError) as exc:
                    report.add(Issue("JSONL_MALFORMED", str(exc)[:200], where))
                    continue
                by_kind[kind].append((where, rec))
    ctx = BundleContext(ledger_version=ledger if isinstance(ledger, int) else None)
    for _, r in by_kind["appointment_record"]:
        ctx.appointments[r.get("appointment_id")] = r
    for _, r in by_kind["approval_record"]:
        ctx.approvals[r.get("approval_record_id")] = r
    for _, r in by_kind["reviewed_record"]:
        ctx.reviews[r.get("review_record_id")] = r
    for _, r in by_kind["document"]:
        ctx.doc_ids.add(r.get("doc_id"))
        ctx.copy_shas.add((r.get("source_copy") or {}).get("sha256"))
    for _, r in by_kind["candidate"]:
        ctx.candidate_ids.add(r.get("candidate_id"))
    seen_docs: set = set()
    for kind in LOAD_ORDER:
        for where, rec in by_kind[kind]:
            report.checked_records += 1
            report.extend(record_issues(kind, rec, reg, where, ctx.ledger_version, ctx))
            if kind == "document":
                did = rec.get("doc_id")
                if did in seen_docs:
                    report.add(Issue("DUPLICATE_DOC_ID", f"{did} appears twice", where))
                seen_docs.add(did)
            elif kind == "candidate":
                if rec.get("source_doc_id") not in ctx.doc_ids:
                    report.add(Issue("DANGLING_CANDIDATE", "candidate refers to a document not in this bundle", where))
                for a in rec.get("anchors", []):
                    if a.get("source_copy_sha256") not in ctx.copy_shas:
                        report.add(Issue("DANGLING_ANCHOR", "anchor refers to a source copy not in this bundle", where))
    return report


def _ver(v: str) -> tuple[int, int, int]:
    core = v.split("-", 1)[0].split(".")
    return tuple(int(x) for x in (core + ["0", "0", "0"])[:3])  # type: ignore[return-value]
