"""OCR engine adapters for C13 A1 (run inside the engine's own venv; see README).

    python -I ocr_engines.py bench  --engine rapidocr|paddle_v6_medium|paddle_v5_mobile|paddle_hi --gt-manifest M --out DIR
    python -I ocr_engines.py ocr    --engine rapidocr --pdf FILE --out-json FILE [--pages 1,2] [--dpi 200]

Each adapter returns, per page, the recognised lines in reading order (lines grouped by vertical
overlap, then left to right) plus engine confidence (recorded but never used for decisions), and the
wall-clock seconds for recognition alone (model load excluded, reported separately).
No network access is needed once the model files are present; PaddleOCR model files are fetched once
from huggingface.co (PADDLE_PDX_MODEL_SOURCE=huggingface) into a local cache.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

THREADS = int(os.environ.get("C13_OCR_THREADS", "2"))   # brief: at most 2 heavy processes on 4 cores


def render(pdf_path: str, page_no: int, dpi: int):
    import numpy as np
    import pymupdf
    pymupdf.TOOLS.mupdf_display_errors(False)
    with pymupdf.open(pdf_path) as doc:
        pix = doc[page_no - 1].get_pixmap(dpi=dpi, colorspace=pymupdf.csRGB, alpha=False)
        return np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3).copy()


def to_lines(items):
    """items: [(box4pts, text, conf)] -> list of line strings in reading order."""
    rows = []
    for box, text, conf in items:
        ys = [p[1] for p in box]
        xs = [p[0] for p in box]
        rows.append({"y0": min(ys), "y1": max(ys), "x": min(xs), "t": text, "c": conf})
    rows.sort(key=lambda r: ((r["y0"] + r["y1"]) / 2, r["x"]))
    lines, cur = [], []
    for r in rows:
        if cur:
            h = max(1.0, min(r["y1"] - r["y0"], cur[-1]["y1"] - cur[-1]["y0"]))
            mid = (r["y0"] + r["y1"]) / 2
            cmid = sum((c["y0"] + c["y1"]) / 2 for c in cur) / len(cur)
            if abs(mid - cmid) <= 0.5 * h:
                cur.append(r)
                continue
            lines.append(cur)
        cur = [r]
    if cur:
        lines.append(cur)
    return [" ".join(x["t"] for x in sorted(l, key=lambda r: r["x"])) for l in lines], \
           [x["c"] for l in lines for x in l]


class RapidOCREngine:
    name = "rapidocr"

    def __init__(self):
        from rapidocr_onnxruntime import RapidOCR
        self.eng = RapidOCR(intra_op_num_threads=THREADS, inter_op_num_threads=1)

    def page(self, img):
        res, _ = self.eng(img)
        items = [(r[0], r[1], float(r[2])) for r in (res or [])]
        return to_lines(items)


class PaddleEngine:
    def __init__(self, variant: str):
        os.environ.setdefault("PADDLE_PDX_MODEL_SOURCE", "huggingface")
        from paddleocr import PaddleOCR
        kw = dict(use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False,
                  enable_mkldnn=False, cpu_threads=THREADS)
        if variant == "paddle_v5_mobile":
            kw.update(text_detection_model_name="PP-OCRv5_mobile_det", text_recognition_model_name="en_PP-OCRv5_mobile_rec")
        elif variant == "paddle_hi":
            kw.update(lang="hi")
        else:
            kw.update(lang="en")
        self.name = variant
        self.eng = PaddleOCR(**kw)

    def page(self, img):
        r = self.eng.predict(img[:, :, ::-1])[0]          # PaddleOCR expects BGR
        items = [(poly.tolist(), t, float(s)) for poly, t, s in zip(r["rec_polys"], r["rec_texts"], r["rec_scores"])]
        return to_lines(items)


def make(engine: str):
    return RapidOCREngine() if engine == "rapidocr" else PaddleEngine(engine)


def cmd_bench(a):
    t0 = time.time()
    eng = make(a.engine)
    load = time.time() - t0
    out = Path(a.out) / a.engine
    out.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(a.gt_manifest, encoding="utf-8")))
    timing = []
    for r in rows:
        img = render(r["local_pdf"], int(r["page"]), a.dpi)
        t = time.time()
        lines, confs = eng.page(img)
        dt = time.time() - t
        (out / f"{r['gt_id']}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
        timing.append({"gt_id": r["gt_id"], "seconds": round(dt, 2), "lines": len(lines),
                       "mean_engine_conf": round(sum(confs) / len(confs), 3) if confs else None})
        print(a.engine, r["gt_id"], round(dt, 1), file=sys.stderr)
    json.dump({"engine": a.engine, "dpi": a.dpi, "threads": THREADS, "model_load_seconds": round(load, 2),
               "pages": timing}, open(out / "timing.json", "w"), indent=1)


def cmd_ocr(a):
    import pymupdf
    pymupdf.TOOLS.mupdf_display_errors(False)
    eng = make(a.engine)
    with pymupdf.open(a.pdf) as d:
        n = d.page_count
    pages = [int(p) for p in a.pages.split(",")] if a.pages else list(range(1, n + 1))
    res = []
    for p in pages:
        t = time.time()
        lines, confs = eng.page(render(a.pdf, p, a.dpi))
        res.append({"page": p, "text": "\n".join(lines), "seconds": round(time.time() - t, 2),
                    "engine_conf_mean": round(100 * sum(confs) / len(confs), 1) if confs else None,
                    "lines": len(lines)})
    tmp = a.out_json + ".part"
    json.dump({"engine": a.engine, "dpi": a.dpi, "threads": THREADS, "pages": res}, open(tmp, "w"), ensure_ascii=False)
    os.replace(tmp, a.out_json)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("bench")
    b.add_argument("--engine", required=True)
    b.add_argument("--gt-manifest", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--dpi", type=int, default=200)
    o = sub.add_parser("ocr")
    o.add_argument("--engine", default="rapidocr")
    o.add_argument("--pdf", required=True)
    o.add_argument("--out-json", required=True)
    o.add_argument("--pages")
    o.add_argument("--dpi", type=int, default=200)
    a = ap.parse_args()
    {"bench": cmd_bench, "ocr": cmd_ocr}[a.cmd](a)


if __name__ == "__main__":
    main()
