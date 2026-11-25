"""Resumable OCR of the recovery population with RapidOCR (run in the OCR venv, see README).

    python -I ocr_population.py --jobs JOBS.json --cache DIR [--early-stop] [--max-pages N]

JOBS.json: [{"doc_id", "sha256", "path", "pages": [1, 2, ...]}], processed in the given order.
Each page result is cached as DIR/<sha256>/page-NNNN.json (atomic write), so a killed run resumes.
The input file's SHA-256 is checked against the job before any page is read; restricted material
(config snapshot in ../inputs/restricted_material.snapshot.json) is refused.

--early-stop: stop a document as soon as its OCR text passes the brief's keyword test as `relevant`.
This only shortens documents that will be RELEVANT anyway; any document that is not stopped early is
OCR'd in full, so an IRRELEVANT decision is never taken on partial OCR. Skipped pages are recorded.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO))

from ocr_engines import make, render  # noqa: E402

from pipeline.judgments import classify, keyword_counts  # noqa: E402


ENGINE_LABEL = {
    "rapidocr": "rapidocr-onnxruntime 1.2.3 (PP-OCRv3 det/rec, bundled)",
    "paddle_v5_mobile": "paddleocr 3.7.0 / paddlepaddle 3.3.1, PP-OCRv5_mobile_det + en_PP-OCRv5_mobile_rec",
    "paddle_v6_medium": "paddleocr 3.7.0 / paddlepaddle 3.3.1, PP-OCRv6_medium_det + PP-OCRv6_medium_rec",
}


def restricted():
    cfg = json.loads((HERE.parent / "inputs" / "restricted_material.snapshot.json").read_text(encoding="utf-8"))
    shas, ids = set(), set()
    for it in cfg["items"]:
        shas.add(it["source_sha256"])
        shas.update(it.get("derived_sha256", []))
        ids.add(it["doc_id"])
    return shas, ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jobs", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--early-stop", action="store_true")
    ap.add_argument("--max-pages", type=int, default=0, help="stop the whole run after this many new pages (0 = no limit)")
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--engine", default="rapidocr", help="rapidocr | paddle_v5_mobile | paddle_v6_medium")
    a = ap.parse_args()
    jobs = json.load(open(a.jobs, encoding="utf-8"))
    rshas, rids = restricted()
    eng = make(a.engine)
    label = ENGINE_LABEL.get(a.engine, a.engine)
    cache = Path(a.cache)
    done_new = 0
    for j in jobs:
        if j["sha256"] in rshas or j["doc_id"] in rids:
            print(f"REFUSED restricted {j['doc_id']}", file=sys.stderr)
            continue
        if hashlib.sha256(open(j["path"], "rb").read()).hexdigest() != j["sha256"]:
            print(f"HASH MISMATCH {j['doc_id']}", file=sys.stderr)
            continue
        d = cache / j["sha256"]
        d.mkdir(parents=True, exist_ok=True)
        text_so_far = ""
        for p in j["pages"]:
            f = d / f"page-{p:04d}.json"
            if f.exists():
                text_so_far += "\n" + json.loads(f.read_text(encoding="utf-8"))["text"]
            else:
                if a.max_pages and done_new >= a.max_pages:
                    print("max-pages reached", file=sys.stderr)
                    return
                t = time.time()
                lines, confs = eng.page(render(j["path"], p, a.dpi))
                rec = {"page": p, "text": "\n".join(lines), "seconds": round(time.time() - t, 2),
                       "engine_conf_mean": round(100 * sum(confs) / len(confs), 1) if confs else None,
                       "lines": len(lines), "engine": label,
                       "dpi": a.dpi, "load1": round(os.getloadavg()[0], 2)}
                tmp = f.with_suffix(".part")
                tmp.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
                os.replace(tmp, f)
                done_new += 1
                text_so_far += "\n" + rec["text"]
                print(j["doc_id"][:50], p, rec["seconds"], file=sys.stderr, flush=True)
            if a.early_stop and classify(keyword_counts(text_so_far)) == "relevant":
                rest = [q for q in j["pages"] if q > p]
                (d / "early_stop.json").write_text(json.dumps({"stopped_after_page": p, "pages_not_ocrd": rest}),
                                                   encoding="utf-8")
                break


if __name__ == "__main__":
    main()
