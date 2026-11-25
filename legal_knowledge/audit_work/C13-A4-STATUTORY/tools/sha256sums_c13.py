#!/usr/bin/env python3
"""Write or check C13-A4-STATUTORY/SHA256SUMS over every file in the package (except SHA256SUMS and caches)."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]


def listing():
    out = []
    for p in sorted(PKG.rglob("*")):
        if p.is_file() and p.name != "SHA256SUMS" and "__pycache__" not in p.parts and not p.name.endswith(".pyc"):
            out.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(PKG).as_posix()}\n")
    return "".join(out)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    want = listing()
    if "--check" in argv:
        have = (PKG / "SHA256SUMS").read_text() if (PKG / "SHA256SUMS").exists() else ""
        if have != want:
            print("CHECK FAILED: SHA256SUMS out of date")
            return 1
        print(f"CHECK OK: {want.count(chr(10))} files")
        return 0
    (PKG / "SHA256SUMS").write_text(want)
    print(f"wrote {want.count(chr(10))} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
