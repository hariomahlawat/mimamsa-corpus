"""CLI: python -m mimamsa_contract {record,bundle,restricted-check} ...  Exit status 0 = valid, 1 = rejected, 2 = usage."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .bundle import validate_bundle
from .issues import Issue, ValidationReport
from .restricted import RestrictedConfigError, load_register
from .rules import record_issues
from .schemas import KIND_TO_SCHEMA


def _print(report: ValidationReport, as_json: bool) -> int:
    if as_json:
        print(json.dumps({
            "ok": report.ok,
            "checked_records": report.checked_records,
            "checked_files": report.checked_files,
            "signature_verified": report.signature_verified,
            "issues": [i.__dict__ for i in report.issues],
        }, indent=1))
    else:
        for i in report.issues:
            print(i)
        print(f"{'VALID' if report.ok else 'REJECTED'}: records={report.checked_records} files={report.checked_files} "
              f"signature_verified={report.signature_verified} errors={len(report.errors)}")
    return 0 if report.ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="mimamsa_contract")
    ap.add_argument("--register", help="path to config/restricted_material.json (default: repository copy)")
    ap.add_argument("--json", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record", help="validate a JSON record or JSONL file")
    r.add_argument("kind", choices=sorted(KIND_TO_SCHEMA))
    r.add_argument("path")
    r.add_argument("--ledger-version", type=int, default=0)
    b = sub.add_parser("bundle", help="validate a release bundle directory")
    b.add_argument("path")
    b.add_argument("--trust-list", help="pinned trust list JSON (required in production mode)")
    b.add_argument("--mode", choices=["production", "development"], default="production")
    b.add_argument("--trusted-key", help="development mode only: file holding an Ed25519 public key as 64 hex characters")
    b.add_argument("--allow-unsigned-dev", action="store_true", help="development mode only: accept a missing signature")
    b.add_argument("--current-sequence", type=int)
    b.add_argument("--rollback", action="store_true")
    b.add_argument("--trusted-ledger-head")
    b.add_argument("--app-version")
    c = sub.add_parser("restricted-check", help="ask the register whether an item is restricted")
    c.add_argument("--sha256")
    c.add_argument("--doc-id")
    c.add_argument("--path")
    a = ap.parse_args(argv)

    report = ValidationReport()
    try:
        reg = load_register(a.register)
    except RestrictedConfigError as exc:
        report.add(Issue("RESTRICTED_CONFIG_MISSING", str(exc)))
        return _print(report, a.json)

    if a.cmd == "restricted-check":
        hit = reg.match(sha256=a.sha256, doc_id=a.doc_id, path=a.path)
        print("RESTRICTED: " + hit if hit else "not restricted")
        return 1 if hit else 0
    if a.cmd == "bundle":
        from .trust import TrustError, parse_trust_list
        key = bytes.fromhex(Path(a.trusted_key).read_text().strip()) if a.trusted_key else None
        trust = None
        if a.trust_list:
            try:
                trust = parse_trust_list(json.loads(Path(a.trust_list).read_text(encoding="utf-8")))
            except (TrustError, json.JSONDecodeError) as exc:
                report.add(Issue("TRUST_LIST_INVALID", str(exc)[:200]))
                return _print(report, a.json)
        return _print(validate_bundle(a.path, trust_list=trust, trusted_public_key=key, mode=a.mode,
                                      allow_unsigned_dev=a.allow_unsigned_dev, register=reg, app_version=a.app_version,
                                      current_release_sequence=a.current_sequence, rollback=a.rollback,
                                      trusted_ledger_head=a.trusted_ledger_head), a.json)
    p = Path(a.path)
    text = p.read_text(encoding="utf-8")
    recs = [json.loads(text)] if p.suffix == ".json" else [json.loads(x) for x in text.splitlines() if x.strip()]
    for n, rec in enumerate(recs, 1):
        report.checked_records += 1
        report.extend(record_issues(a.kind, rec, reg, f"{p.name}:{n}", a.ledger_version))
    return _print(report, a.json)


if __name__ == "__main__":
    sys.exit(main())
