"""CA-01A: local read-only verification of preserved original bytes.

No credentials in arguments or output. No uploads, extraction, rendering, or
registration. Run in a fresh owner-controlled directory outside the repo.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath

DATASET = "hariomahlawat/mimamsa-corpus"
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
    rows = checked_rows(json.loads(args.inventory.read_text(encoding="utf-8")))
    print("Candidates:", len(rows))
    if not args.execute_read_only:
        print("Dry run only; no network access.")
        return 0
    if args.output is None:
        parser.error("--output is required for execution")
    output = args.output.resolve()
    repo = args.inventory.resolve().parents[3]
    if output == repo or repo in output.parents:
        parser.error("output must be outside the repository")
    output.mkdir(parents=True, exist_ok=False)
    from huggingface_hub import HfApi, hf_hub_download

    api = HfApi()
    info = api.dataset_info(DATASET)
    if info.private is not True or not REV.fullmatch(info.sha or ""):
        raise RuntimeError("private dataset and full HEAD required")
    initial_head = info.sha
    report = {"dataset": DATASET, "observed_head": initial_head,
              "candidate_inventory_sha256": hashlib.sha256(
                  args.inventory.read_bytes()).hexdigest(), "records": []}
    for row in rows:
        result = {"sha256": row["sha256"], "hf_path": row["hf_path"],
                  "revision": row["hf_revision"],
                  "prior_integrity_result": row["prior_integrity_result"],
                  "eligible_for_exact_anchor": False}
        try:
            path = Path(hf_hub_download(
                repo_id=DATASET, repo_type="dataset",
                filename=row["hf_path"], revision=row["hf_revision"],
                local_dir=output / "originals", force_download=True))
            result.update(verify_bytes(path, row))
            result["status"] = ("PRESERVATION_MATCH_NOT_AUTHENTICATED"
                                if result["matches_preservation"] else "BYTE_MISMATCH_HOLD")
        except Exception as exc:
            # Exception messages may contain request details; record type only.
            result["status"] = "DOWNLOAD_OR_VERIFICATION_FAILED"
            result["error_type"] = type(exc).__name__
        report["records"].append(result)
        (output / "verification.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8")
    final = api.dataset_info(DATASET)
    report["final_observed_head"] = final.sha
    report["private_at_end"] = final.private
    report["head_unchanged"] = final.sha == initial_head
    (output / "verification.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if (final.private is True and report["head_unchanged"]
                 and all(r.get("matches_preservation") for r in report["records"])) else 1


if __name__ == "__main__":
    raise SystemExit(main())
