"""CA-01A offline page-image review preparation; no OCR, text extraction or network."""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
from pathlib import Path

from corpus_runner import load_inventory, digest, PRESERVATION, HERE

RECEIPT_SHA = "156d0dfde8fad89fbdad31e34fdd973ef65df4014de3000d971c2fce68c34b9f"
HEAD = "f4e6ba443ec9c0b89b2c5d21d0b5cda38f55d2dc"
DPI = 150
MAX_PAGES_PER_PDF = 200
MAX_PIXELS = 12_000_000
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
    job = job.resolve()
    inputs = verify_inputs(job)
    print("Verified local originals:", len(inputs))
    if not execute:
        print("Dry run: no writes, no network.")
        return 0
    import pymupdf
    out = job / "page-review"
    if out.exists():
        raise ValueError("review directory already exists; preserve it")
    if shutil.disk_usage(job).free < 2_000_000_000:
        raise ValueError("at least 2 GB free space required")
    out.mkdir()
    report = {"status": "INCOMPLETE", "receipt_sha256": RECEIPT_SHA,
              "dpi": DPI, "renderer_version": pymupdf.VersionBind,
              "access_marking_review": "PENDING_VISUAL_REVIEW",
              "eligible_for_exact_anchor": False, "records": []}
    manifest = out / "page_manifest.json"

    def save():
        tmp = manifest.with_suffix(".tmp")
        tmp.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        tmp.replace(manifest)

    save()
    for row, path in inputs:
        rec = {"target_id": row["a7_target_id"], "source_sha256": row["sha256"],
               "registration_state": row["registration_state"], "pages": [],
               "access_marking_review": "PENDING_VISUAL_REVIEW",
               "identity_review": "PENDING_VISUAL_REVIEW", "eligible_for_exact_anchor": False}
        report["records"].append(rec)
        try:
            with pymupdf.open(path) as doc:
                if doc.needs_pass or not doc.is_pdf or not 0 < doc.page_count <= MAX_PAGES_PER_PDF:
                    raise ValueError("encrypted, invalid or oversized page count")
                rec["physical_pages"] = doc.page_count
                rec["renderer_repaired_pdf"] = bool(doc.is_repaired)
                if doc.is_repaired:
                    raise ValueError("PDF required repair")
                folder = out / row["sha256"]
                folder.mkdir()
                for i, page in enumerate(doc):
                    width = page.rect.width * DPI / 72
                    height = page.rect.height * DPI / 72
                    if width <= 0 or height <= 0 or (width + 2) * (height + 2) > MAX_PIXELS:
                        raise ValueError("page exceeds render limit")
                    pix = page.get_pixmap(dpi=DPI, colorspace=pymupdf.csRGB, alpha=False)
                    target = folder / ("page-%04d.png" % (i + 1))
                    pix.save(target)
                    rec["pages"].append({"physical_page": i + 1,
                        "image": target.relative_to(out).as_posix(),
                        "image_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                        "access_marking_review": "PENDING",
                        "printed_page": None, "identity_or_anchor": None})
                    save()
            if digest(path) != (row["sha256"], row["md5"], row["bytes"]):
                raise ValueError("source changed during render")
            rec["status"] = "RENDERED_NOT_REVIEWED"
        except Exception as exc:
            rec["status"] = "REVIEW_REQUIRED"
            rec["error_type"] = type(exc).__name__
        save()
    good = all(x["status"] == "RENDERED_NOT_REVIEWED" for x in report["records"])
    report["status"] = "RENDERED_NOT_REVIEWED" if good else "REVIEW_REQUIRED"
    save()
    print("Status:", report["status"])
    print("Physical pages rendered:", sum(len(x["pages"]) for x in report["records"]))
    print("Manifest:", manifest)
    return 0 if good else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--job", type=Path, required=True)
    p.add_argument("--render-local", action="store_true")
    args = p.parse_args()
    raise SystemExit(prepare(args.job, args.render_local))
