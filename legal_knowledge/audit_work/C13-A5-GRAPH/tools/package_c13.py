#!/usr/bin/env python3
"""C13-A5 packaging: SHA256SUMS over every file in C13-A5-GRAPH/ (except SHA256SUMS itself and hf/staged/, whose
three files are covered by hf/STAGED_MANIFEST.csv). Files are hashed as stored (gz files as their bytes).

  python -I -B package_c13.py [--check]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_c13 as C  # noqa: E402


def build():
    lines = []
    for p in sorted(C.PKG.rglob("*")):
        rel = p.relative_to(C.PKG).as_posix()
        if not p.is_file() or rel == "SHA256SUMS" or rel.startswith("hf/staged/") or "__pycache__" in rel:
            continue
        lines.append("%s  %s\n" % (C.sha256_file(p), rel))
    return "".join(lines)


def main():
    text = build()
    r = C.Restricted()
    assert not r.hit(text=text)
    return C.write_or_check({"SHA256SUMS": text}, C.PKG, "--check" in sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
