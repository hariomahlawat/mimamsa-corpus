"""CA-01A offline page-image review preparation; no OCR, text extraction or network."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from corpus_runner import load_inventory, digest, PRESERVATION, HERE

RECEIPT_SHA = "156d0dfde8fad89fbdad31e34fdd973ef65df4014de3000d971c2fce68c34b9f"
HEAD = "f4e6ba443ec9c0b89b2c5d21d0b5cda38f55d2dc"
from _page_review_worker import DPI, MAX_INPUT_BYTES


MAX_JOB_DECODED_BYTES = 2_000_000_000
MAX_JOB_WALL_SECONDS = 120
FIRST = ("C13-G1-AA-ENACTED-1950", "C13-G1-BSA-COMM-252352",
         "C13-G1-BNS-COMM-252353", "C13-G1-BNSS-COMM-252354")


def verify_inputs(job):
    rows, inv = load_inventory(HERE.parent / "COPY_REGISTRATION_CANDIDATES.json")
    raw = (job / "verification.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != RECEIPT_SHA:
        raise ValueError("receipt hash mismatch; use successful original job")
    report = json.loads(raw)
    if (report["inventory_sha256"] != inv or report["preservation_revision"] != PRESERVATION
            or report["observed_head"] != HEAD or report["final_observed_head"] != HEAD
            or report["status"] != "BYTE_CHECK_COMPLETE_NOT_LEGALLY_VERIFIED"
            or report["hf_writes"] != 0 or report["legal_promotions"] != 0
            or len(report["records"]) != len(rows)):
        raise ValueError("receipt outside frozen scope")
    by_id = {x["target_id"]: x for x in report["records"]}
    originals = (job / "originals").resolve()
    result = []
    for row in rows:
        rec = by_id[row["a7_target_id"]]
        path = originals / row["hf_path"]
        expected = (row["sha256"], row["md5"], row["bytes"])
        if (rec["hf_path"] != row["hf_path"] or rec["revision"] != PRESERVATION
                or rec["registration_state"] != row["registration_state"]
                or rec["eligible_for_exact_anchor"] is not False
                or rec["matches_preservation"] is not True
                or (rec["actual_sha256"], rec["actual_md5"], rec["actual_bytes"]) != expected
                or not path.resolve().is_relative_to(originals)
                or path.resolve() != path
                or digest(path) != expected):
            raise ValueError("original or receipt mismatch: " + row["a7_target_id"])
        result.append((row, path))
    return sorted(result, key=lambda v: FIRST.index(v[0]["a7_target_id"])
                  if v[0]["a7_target_id"] in FIRST else len(FIRST))


def prepare(job, execute=False):
    if execute:
        print("Render held pending native process isolation and independent acceptance.")
        return 2
    inputs = verify_inputs(job.resolve())
    print("Verified local originals:", len(inputs))
    print("Dry run: no writes, no network.")
    return 0


def render_candidate_images(inputs, out, *, wall_seconds=MAX_JOB_WALL_SECONDS,
                            decoded_byte_limit=MAX_JOB_DECODED_BYTES):
    """Exercise bounded rendering in a disposable fixture workspace."""
    if (not math.isfinite(wall_seconds) or not 0 < wall_seconds <= MAX_JOB_WALL_SECONDS
            or type(decoded_byte_limit) is not int
            or not 0 < decoded_byte_limit <= MAX_JOB_DECODED_BYTES):
        raise ValueError("invalid render budget")
    hashes = [row["sha256"] for row, _ in inputs]
    if len(hashes) != len(set(hashes)) or not 0 < len(hashes) <= 15:
        raise ValueError("invalid fixture scope")
    if any(not re.fullmatch(r"[0-9a-f]{64}", sha) for sha in hashes):
        raise ValueError("invalid source hash")

    deadline = time.monotonic() + wall_seconds
    out.mkdir()
    report = {
        "status": "INCOMPLETE",
        "scope": "DISPOSABLE_FIXTURE_ONLY",
        "render": {"dpi": DPI, "colorspace": "RGB", "alpha": False, "annots": True},
        "budget": {"wall_seconds": wall_seconds, "decoded_bytes": decoded_byte_limit},
        "access_marking_review": "PENDING_VISUAL_REVIEW",
        "eligible_for_exact_anchor": False,
        "records": [],
    }
    manifest = out / "page_manifest.json"

    def save():
        tmp = manifest.with_suffix(".tmp")
        tmp.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        tmp.replace(manifest)

    save()
    consumed = 0
    child_env = {"SYSTEMROOT": os.environ["SYSTEMROOT"]} if "SYSTEMROOT" in os.environ else {}
    for row, path in inputs:
        rec = {
            "target_id": row["a7_target_id"],
            "source_sha256": row["sha256"],
            "registration_state": row["registration_state"],
            "pages": [],
            "access_marking_review": "PENDING_VISUAL_REVIEW",
            "identity_review": "PENDING_VISUAL_REVIEW",
            "eligible_for_exact_anchor": False,
            "status": "INCOMPLETE",
        }
        report["records"].append(rec)
        save()
        try:
            if type(row["bytes"]) is not int or not 0 < row["bytes"] <= MAX_INPUT_BYTES:
                raise ValueError("invalid source size")
            with path.open("rb") as original:
                raw = original.read(row["bytes"] + 1)
            if (len(raw) != row["bytes"]
                    or hashlib.sha256(raw).hexdigest() != row["sha256"]
                    or hashlib.md5(raw, usedforsecurity=False).hexdigest() != row["md5"]):
                raise ValueError("fixture bytes failed source verification")
            folder = out / row["sha256"]
            folder.mkdir()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired("page review worker", wall_seconds)
            result = subprocess.run(
                [sys.executable, "-I", "-B", str(HERE / "_page_review_worker.py"),
                 str(decoded_byte_limit - consumed)],
                input=raw, cwd=folder, env=child_env, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, check=True, timeout=remaining,
            )
            evidence = json.loads(result.stdout)
            consumed += evidence["decoded_bytes"]
            for page in evidence["pages"]:
                original_image_name = page["image"]
                page["image"] = (Path(row["sha256"]) / original_image_name).as_posix()
            rec.update(evidence)
            rec["status"] = "RENDERED_NOT_REVIEWED"
        except (subprocess.SubprocessError, OSError, ValueError) as exc:
            rec["status"] = "REVIEW_REQUIRED"
            rec["error_type"] = type(exc).__name__
            # A failed worker may have written some images. Hold the whole remaining job.
            break
        finally:
            save()

    good = len(report["records"]) == len(inputs) and all(
        record["status"] == "RENDERED_NOT_REVIEWED" for record in report["records"]
    )
    report["decoded_bytes_for_completed_records"] = consumed
    report["status"] = "RENDERED_NOT_REVIEWED" if good else "REVIEW_REQUIRED"
    save()
    return 0 if good else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--job", type=Path, required=True)
    p.add_argument("--render-local", action="store_true")
    args = p.parse_args()
    raise SystemExit(prepare(args.job, args.render_local))
