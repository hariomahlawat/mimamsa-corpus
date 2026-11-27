"""Historical CA-01A candidate inventory dry run."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath

PREFIX = "legal_knowledge/preservation/c13_a7_acquired/"
HEX = re.compile(r"[0-9a-f]{64}\Z")
REV = re.compile(r"[0-9a-f]{40}\Z")


def checked_rows(doc):
    rows = doc["records"]
    seen = set()
    for row in rows:
        sha = row["sha256"]
        path = row["hf_path"]
        p = PurePosixPath(path)
        if (not HEX.fullmatch(sha) or sha in seen
                or not REV.fullmatch(row["hf_revision"])
                or not path.startswith(PREFIX)
                or p.as_posix() != path or ".." in p.parts
                or "\\" in path or "%" in path
                or p.parent.name != sha or p.suffix.lower() != ".pdf"
                or type(row["bytes"]) is not int or row["bytes"] <= 0
                or row["eligible_for_exact_anchor"] is not False
                or row["legal_status"] != "AUTOMATED_CANDIDATE_NOT_VERIFIED"):
            raise ValueError("invalid or duplicate candidate")
        seen.add(sha)
    if len(rows) != 15:
        raise ValueError("expected the frozen 15-candidate batch")
    return rows


def verify_bytes(path, row):
    sha = hashlib.sha256()
    md5 = hashlib.md5(usedforsecurity=False)
    n = 0
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            n += len(chunk)
            sha.update(chunk)
            md5.update(chunk)
    return {"actual_sha256": sha.hexdigest(), "actual_md5": md5.hexdigest(),
            "actual_bytes": n,
            "matches_preservation": (sha.hexdigest() == row["sha256"]
                                     and md5.hexdigest() == row["md5"]
                                     and n == row["bytes"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--execute-read-only", action="store_true")
    args = parser.parse_args()
    if args.execute_read_only:
        parser.error("C14 historical verifier is offline only")
    rows = checked_rows(json.loads(args.inventory.read_text(encoding="utf-8")))
    print("Candidates:", len(rows))
    print("Dry run only; no network access.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
