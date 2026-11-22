#!/usr/bin/env python3
"""Generic CSV well-formedness check for audit registers (stdlib only; structural, not legal).

Default scope: every *.csv under legal_knowledge/audit_work/. For each file:
  * decodes as UTF-8 (a UTF-8 BOM is reported as an error: it corrupts the first header name);
  * contains no NUL bytes;
  * has a header row whose names are non-blank and unique;
  * every data row has exactly as many fields as the header (no ragged rows);
  * parses with the csv module in strict mode (no unterminated quotes);
  * at least one data row.
Usage: python3 tools/legal_audit/check_csv.py [PATH ...]   Exit 1 on any error.
"""
from __future__ import annotations
import csv, io, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / "legal_knowledge" / "audit_work"


def check_file(path: Path) -> list[str]:
    errs = []
    raw = path.read_bytes()
    name = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    if raw.startswith(b"\xef\xbb\xbf"):
        errs.append(f"{name}: UTF-8 BOM present")
    if b"\x00" in raw:
        errs.append(f"{name}: NUL byte present")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        return errs + [f"{name}: not UTF-8 ({exc})"]
    try:
        rows = list(csv.reader(io.StringIO(text, newline=""), strict=True))
    except csv.Error as exc:
        return errs + [f"{name}: CSV parse error: {exc}"]
    rows = [r for r in rows if r]  # csv yields [] for blank lines; blank lines are tolerated
    if not rows:
        return errs + [f"{name}: empty file"]
    header = rows[0]
    if any(not h.strip() for h in header):
        errs.append(f"{name}: blank header name")
    dup = sorted({h for h in header if header.count(h) > 1})
    if dup:
        errs.append(f"{name}: duplicate header names {dup}")
    if len(rows) < 2:
        errs.append(f"{name}: header only, no data rows")
    for n, r in enumerate(rows[1:], 2):
        if len(r) != len(header):
            errs.append(f"{name}: row {n} has {len(r)} fields, header has {len(header)}")
    return errs


def iter_paths(args):
    if not args:
        yield from sorted(DEFAULT.rglob("*.csv"))
    for a in args:
        p = Path(a)
        yield from (sorted(p.rglob("*.csv")) if p.is_dir() else [p])


def main(argv=None):
    paths = list(iter_paths(sys.argv[1:] if argv is None else argv))
    errs = [e for p in paths for e in check_file(p)]
    print(f"csv_files={len(paths)} errors={len(errs)}")
    for e in errs:
        print("ERROR", e)
    return 1 if errs or not paths else 0


if __name__ == "__main__":
    sys.exit(main())
