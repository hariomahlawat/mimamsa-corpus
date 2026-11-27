#!/usr/bin/env python3
"""C13 A7: build a byte index (sha256, md5, size) of the corpus source copies, offline.

Inputs (read-only, no network):
  * GitHub raw-data snapshot ad77758d (object store /home/user/c7): every blob under data/raw/ (4,039 files);
  * the HF byte-verification mirror of revision 5524c3d9 (scratchpad/hf_verify_5524c3d9): every file under
    legal_knowledge/ (judgment originals, MML originals, the 48 preserved C5 working-store copies).
The 16 baseline HF_ONLY copies (8 SC/third-party judgments, 8 MML originals) and the later HF additions (15bd03cc:
18 HC/SC judgments; 3864faf3: 7 excluded judgments) are not in the local mirror; they are listed from the C12
registers (copy_verification_c12) with sha256 only (md5 column empty). None is a Gazette/Rules/DESW copy.

Output: pr_review/CORPUS_BYTE_INDEX.csv.gz (deterministic: sorted, gzip mtime 0).

Usage:  python -I corpus_md5_index.py          # build
        python -I corpus_md5_index.py --check  # rebuild in memory and compare with the committed file
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE.parent
OUT = OUT_DIR / "pr_review" / "CORPUS_BYTE_INDEX.csv.gz"
C7 = Path("/home/user/c7")
RAW_COMMIT = "ad77758d"
HF_MIRROR = Path("/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/hf_verify_5524c3d9")
C12 = OUT_DIR.parent / "C12-CONSOLIDATION" / "copy_verification_c12"


def raw_rows():
    ls = subprocess.run(["git", "-C", str(C7), "ls-tree", "-r", RAW_COMMIT, "--", "data/raw"],
                        check=True, capture_output=True, text=True).stdout.splitlines()
    entries = []
    for line in ls:
        meta, path = line.split("\t", 1)
        _, typ, oid = meta.split()
        if typ == "blob":
            entries.append((oid, path))
    p = subprocess.Popen(["git", "-C", str(C7), "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    for oid, path in entries:
        p.stdin.write(oid.encode() + b"\n")
        p.stdin.flush()
        header = p.stdout.readline().split()
        size = int(header[2])
        data = p.stdout.read(size)
        p.stdout.read(1)
        yield {"origin": f"github-raw-data@{RAW_COMMIT}", "path": path, "bytes": size,
               "sha256": hashlib.sha256(data).hexdigest(), "md5": hashlib.md5(data).hexdigest()}
    p.stdin.close()
    p.wait()


def hf_mirror_rows():
    for f in sorted((HF_MIRROR / "legal_knowledge").rglob("*")):
        if f.is_file() and f.suffix.lower() == ".pdf":
            data = f.read_bytes()
            yield {"origin": "hf@5524c3d9", "path": str(f.relative_to(HF_MIRROR)), "bytes": len(data),
                   "sha256": hashlib.sha256(data).hexdigest(), "md5": hashlib.md5(data).hexdigest()}


def c12_addition_rows():
    p = C12 / "CANONICAL_INVENTORY_ADDITIONS_C12.csv"
    for r in csv.DictReader(open(p, encoding="utf-8")):
        if r["addition_group"].startswith("C12_ACQUISITION_25"):
            yield {"origin": "hf@15bd03cc/3864faf3 (C12 register; sha256 only)", "path": r["hosted_path"],
                   "bytes": "", "sha256": r["sha256"], "md5": ""}
    m = C12 / "COPY_VERIFICATION_MANIFEST.csv"
    for r in csv.DictReader(open(m, encoding="utf-8")):
        if r["baseline_segment"] == "HF_ONLY":
            yield {"origin": "hf@5524c3d9 HF_ONLY (C12 register; sha256 only)", "path": r["hosted_path"],
                   "bytes": r["actual_size"], "sha256": r["computed_sha256"], "md5": ""}


def build() -> bytes:
    rows = list(raw_rows()) + list(hf_mirror_rows()) + list(c12_addition_rows())
    rows.sort(key=lambda r: (r["origin"], r["path"], r["sha256"]))
    s = io.StringIO()
    w = csv.DictWriter(s, ["origin", "path", "bytes", "sha256", "md5"], lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0, filename="") as g:
        g.write(s.getvalue().encode())
    return buf.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    data = build()
    if a.check:
        ok = OUT.exists() and gzip.decompress(OUT.read_bytes()) == gzip.decompress(data)
        print("CHECK", "OK" if ok else "FAIL", OUT.name)
        return 0 if ok else 1
    OUT.write_bytes(data)
    n = gzip.decompress(data).decode().count("\n") - 1
    print(f"wrote {OUT} ({n} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
