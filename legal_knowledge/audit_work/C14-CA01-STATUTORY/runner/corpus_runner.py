"""C14 local corpus runner. Offline by default; only HF read operations are implemented."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DATASET = "hariomahlawat/mimamsa-corpus"
ENDPOINT = "https://huggingface.co"
BASELINE = "c1e4d461e208bf961fd6bc51584dad01df220e61"
PRESERVATION = "9e3cf9868a5d553cd6218ed5ac51c383560bbf0b"
INVENTORY_BLOB = "5be838d109b9d785fcd092977e04c56f808c7034"
LAST_RECORDED_HEAD = "f4e6ba443ec9c0b89b2c5d21d0b5cda38f55d2dc"
PREFIX = "legal_knowledge/preservation/c13_a7_acquired/"
HERE = Path(__file__).resolve().parent


def utc():
    return datetime.now(timezone.utc).isoformat()


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def load_inventory(path):
    raw = path.read_bytes()
    if git_blob(raw) != INVENTORY_BLOB:
        # Windows Git may check out CRLF; verify canonical LF bytes, not arbitrary edits.
        raw = raw.replace(b"\r\n", b"\n")
    if git_blob(raw) != INVENTORY_BLOB:
        raise ValueError("inventory blob mismatch")
    d = json.loads(raw)
    if d["baseline"] != BASELINE or len(d["records"]) != 15:
        raise ValueError("inventory scope mismatch")
    seen = set()
    for row in d["records"]:
        sha = row["sha256"]
        if not re.fullmatch(r"[0-9a-f]{64}", sha) or sha in seen:
            raise ValueError("invalid or duplicate SHA-256")
        seen.add(sha)
        pattern = re.escape(PREFIX + sha[:2] + "/" + sha + "/") + r"[A-Za-z0-9_-]+\.pdf"
        if (not re.fullmatch(pattern, row["hf_path"])
                or row["hf_revision"] != PRESERVATION
                or not re.fullmatch(r"[0-9a-f]{32}", row["md5"])
                or type(row["bytes"]) is not int or not 0 < row["bytes"] <= 200_000_000
                or row["eligible_for_exact_anchor"] is not False
                or row["legal_status"] != "AUTOMATED_CANDIDATE_NOT_VERIFIED"):
            raise ValueError("candidate outside approved read-only scope")
    return d["records"], hashlib.sha256(raw).hexdigest()


def digest(path):
    s = hashlib.sha256()
    m = hashlib.md5(usedforsecurity=False)
    n = 0
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            s.update(chunk)
            m.update(chunk)
            n += len(chunk)
    return s.hexdigest(), m.hexdigest(), n


def metadata(api):
    info = api.dataset_info(DATASET, revision="main")
    if info.private is not True or not re.fullmatch(r"[0-9a-f]{40}", info.sha or ""):
        raise RuntimeError("private dataset and full main revision required")
    return info.sha


def write_report(path, report):
    # Atomic replacement is limited to our own derived report, never source files.
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def execute(rows, inventory_sha, output, api, download):
    output.mkdir(parents=True, exist_ok=False)
    report_path = output / "verification.json"
    report = {"dataset": DATASET, "started_utc": utc(), "inventory_sha256": inventory_sha,
              "expected_previous_head": LAST_RECORDED_HEAD, "preservation_revision": PRESERVATION,
              "records": [], "status": "INCOMPLETE", "legal_promotions": 0, "hf_writes": 0}
    write_report(report_path, report)
    try:
        head = metadata(api)
        report["observed_head"] = head
        report["head_differs_from_recorded"] = head != LAST_RECORDED_HEAD
        files = api.list_repo_files(DATASET, repo_type="dataset", revision=head)
        if len(files) != len(set(files)):
            raise RuntimeError("duplicate paths in remote listing")
        report["observed_file_count"] = len(files)
        file_set = set(files)
        for row in rows:
            item = {"target_id": row["a7_target_id"], "hf_path": row["hf_path"],
                    "revision": PRESERVATION, "expected_sha256": row["sha256"],
                    "prior_integrity_result": row["prior_integrity_result"],
                    "registration_state": row["registration_state"],
                    "present_at_observed_head": row["hf_path"] in file_set,
                    "eligible_for_exact_anchor": False}
            try:
                path = Path(download(repo_id=DATASET, repo_type="dataset", endpoint=ENDPOINT,
                                     filename=row["hf_path"], revision=PRESERVATION,
                                     local_dir=output / "originals", force_download=True))
                expected_path = output / "originals" / row["hf_path"]
                if path.resolve() != expected_path.resolve() or not path.resolve().is_relative_to(output.resolve()):
                    raise RuntimeError("download outside job scope")
                sha, md5, size = digest(path)
                item.update(actual_sha256=sha, actual_md5=md5, actual_bytes=size,
                            matches_preservation=(sha, md5, size) == (row["sha256"], row["md5"], row["bytes"]))
                item["status"] = "PRESERVATION_MATCH_NOT_AUTHENTICATED" if item["matches_preservation"] else "BYTE_MISMATCH_HOLD"
            except Exception as exc:
                item.update(status="DOWNLOAD_OR_VERIFICATION_FAILED", error_type=type(exc).__name__)
            report["records"].append(item)
            write_report(report_path, report)
        report["final_observed_head"] = metadata(api)
        report["head_unchanged"] = report["final_observed_head"] == head
        good = (report["head_unchanged"] and len(report["records"]) == len(rows)
                and all(i.get("matches_preservation") and i["present_at_observed_head"] for i in report["records"]))
        report["status"] = "BYTE_CHECK_COMPLETE_NOT_LEGALLY_VERIFIED" if good else "REVIEW_REQUIRED"
    except Exception as exc:
        report.update(status="REVIEW_REQUIRED", error_type=type(exc).__name__)
    report["finished_utc"] = utc()
    write_report(report_path, report)
    print("Status:", report["status"])
    print("Report:", report_path)
    return 0 if report["status"] == "BYTE_CHECK_COMPLETE_NOT_LEGALLY_VERIFIED" else 1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--execute-read-only", action="store_true")
    p.add_argument("--output", type=Path)
    p.add_argument("--expected-commit")
    a = p.parse_args()
    rows, inv = load_inventory(HERE.parent / "COPY_REGISTRATION_CANDIDATES.json")
    print("Scope: CA-01A;", len(rows), "PDFs;", sum(r["bytes"] for r in rows), "bytes")
    if not a.execute_read_only:
        print("Dry run: no network or file writes.")
        return 0
    if not a.output or not re.fullmatch(r"[0-9a-f]{40}", a.expected_commit or ""):
        p.error("execution requires --output and --expected-commit")
    repo = Path(subprocess.check_output(["git", "-C", str(HERE), "rev-parse", "--show-toplevel"], text=True).strip()).resolve()
    head = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    status = subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain"], text=True)
    if head != a.expected_commit or status.strip():
        p.error("worktree must be clean and at the reviewed commit")
    out = a.output.resolve()
    if out.exists() or out == repo or repo in out.parents or out in repo.parents:
        p.error("fresh output directory outside worktree required")
    parent = out.parent
    while not parent.exists():
        parent = parent.parent
    if shutil.disk_usage(parent).free < max(250_000_000, 3 * sum(r["bytes"] for r in rows)):
        p.error("insufficient free space")
    try:
        from huggingface_hub import HfApi, hf_hub_download
    except ImportError:
        p.error("huggingface_hub not installed in selected Python; no automatic installation")
    return execute(rows, inv, out, HfApi(endpoint=ENDPOINT), hf_hub_download)


if __name__ == "__main__":
    sys.exit(main())
