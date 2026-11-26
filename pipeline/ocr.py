"""Stage 'ocr': Tesseract OCR for documents the extract stage marked needs_ocr.

Every page is rendered from the raw PDF and read with Tesseract. Per-page results are cached in
data/ocr/<doc_id>/page-NNNN.json, so a killed run resumes where it stopped. Pages whose mean word
confidence is below the threshold are listed in the metadata and in reports/ocr_review.md for a
human to check; they are not silently trusted.
"""
from __future__ import annotations

import csv
import io
import json
import os
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pymupdf

from .common import Paths, require_corpus_writes, write_json
from .extract import MARKING, devanagari_share

LANGS = "hin+eng"
DPI = 300
MAX_SIDE_PX = 4000               # scans with huge page boxes are rendered down to this
CONF_THRESHOLD = 70.0            # mean word confidence (0-100) below this = page listed for review
WATERMARK_WORDS = {"indiacode", "india code"}


def tesseract_version() -> str | None:
    exe = shutil.which("tesseract")
    if not exe:
        return None
    out = subprocess.run([exe, "--version"], capture_output=True, text=True)
    return (out.stdout or out.stderr).splitlines()[0].strip()


def render_png(page, dpi: int = DPI) -> bytes:
    zoom = dpi / 72
    longest = max(page.rect.width, page.rect.height) * zoom
    if longest > MAX_SIDE_PX:
        zoom *= MAX_SIDE_PX / longest
    return page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), colorspace=pymupdf.csGRAY).tobytes("png")


def parse_words(tsv: str) -> list[dict]:
    """Words from Tesseract's TSV output, with line key, box and confidence."""
    words = []
    for row in csv.DictReader(io.StringIO(tsv), delimiter="\t", quoting=csv.QUOTE_NONE):
        text = (row.get("text") or "").strip()
        try:
            conf = float(row.get("conf", -1))
        except ValueError:
            conf = -1
        if not text or conf < 0 or text.lower() in WATERMARK_WORDS:
            continue
        x, y, w, h = (int(row[k]) for k in ("left", "top", "width", "height"))
        words.append({"text": text, "conf": conf, "box": (x, y, x + w, y + h),
                      "line": (int(row["block_num"]), int(row["par_num"]), int(row["line_num"]))})
    return words


def words_to_text(words: list[dict]) -> tuple[str, float | None, int]:
    """(text, mean word confidence, number of words)."""
    lines: dict[tuple, list[str]] = {}
    for w in words:
        lines.setdefault(w["line"], []).append(w["text"])
    out, prev = [], None
    for key in sorted(lines):
        if prev is not None and key[:2] != prev[:2]:
            out.append("")
        out.append(" ".join(lines[key]))
        prev = key
    confs = [w["conf"] for w in words]
    return "\n".join(out), (sum(confs) / len(confs) if confs else None), len(confs)


def parse_tsv(tsv: str) -> tuple[str, float | None, int]:
    return words_to_text(parse_words(tsv))


def _overlap(a: tuple, b: tuple) -> float:
    """Intersection over union of two boxes."""
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union else 0.0


def _digits(s: str) -> int:
    return sum(ch.isdigit() and ch.isascii() for ch in s)


def merge_numbers(base: list[dict], alt: list[dict]) -> int:
    """Hindi-first Tesseract reads Hindi words well but drops or misreads the digit 1 ("2010" -> "200",
    "31" -> "3]"); English-first reads numbers correctly but garbles some Hindi words. So the
    Hindi-first pass is the base, and a word is replaced by the English-first reading of the same
    box when that reading has more digits (or the same digits and the base has none of its own
    letters left to protect). Returns the number of words replaced."""
    replaced = 0
    for w in base:
        best, score = None, 0.6
        for a in alt:
            if abs(a["box"][1] - w["box"][1]) > 60:        # not on the same text line
                continue
            s = _overlap(w["box"], a["box"])
            if s > score:
                best, score = a, s
        if best is None or best["text"] == w["text"]:
            continue
        if _digits(best["text"]) > _digits(w["text"]):
            w["text"], w["conf"] = best["text"], min(w["conf"], best["conf"])
            replaced += 1
    return replaced


def ocr_page(pdf_path: Path, index: int, cache: Path, langs: str, dpi: int) -> dict:
    require_corpus_writes("OCR")
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    with pymupdf.open(pdf_path) as pdf:
        png = render_png(pdf[index], dpi)
    def read(order: str) -> list[dict]:
        proc = subprocess.run(["tesseract", "stdin", "stdout", "-l", order, "--psm", "3", "tsv"], input=png,
                              capture_output=True, env={**os.environ, "OMP_THREAD_LIMIT": "1"})
        if proc.returncode != 0:
            raise RuntimeError(f"tesseract failed on page {index + 1}: {proc.stderr.decode(errors='replace')[:300]}")
        return parse_words(proc.stdout.decode("utf-8", errors="replace"))

    base = read(langs)
    number_fixes = 0
    parts = langs.split("+")
    if len(parts) == 2:                                    # second pass with the languages swapped
        number_fixes = merge_numbers(base, read(f"{parts[1]}+{parts[0]}"))
    text, conf, words = words_to_text(base)
    res = {"page": index + 1, "text": text, "confidence": conf, "words": words, "langs": langs, "dpi": dpi,
           "number_fixes": number_fixes}
    cache.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache.with_suffix(".part")
    tmp.write_text(json.dumps(res, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, cache)
    return res


def run(paths: Paths, only: list[str] | None = None, *, workers: int = 4, langs: str = LANGS, dpi: int = DPI,
        threshold: float = CONF_THRESHOLD, redo: bool = False) -> dict:
    require_corpus_writes("OCR")
    version = tesseract_version()
    if not version:
        return {"error": "tesseract is not installed", "documents": 0}
    stats = {"tesseract": version, "documents": 0, "pages": 0, "low_confidence_pages": 0, "errors": [], "docs": {}}
    review: list[str] = []
    for path in sorted(paths.meta.glob("*.json")):
        meta = json.loads(path.read_text(encoding="utf-8"))
        wanted = meta.get("needs_ocr") or (redo and meta.get("text_method") == "ocr")
        if not wanted or (only and meta["doc_id"] not in only) or meta.get("mime_type") != "application/pdf":
            continue
        doc_id = meta["doc_id"]
        pdf_path = paths.raw_file(meta["raw_path"])
        with pymupdf.open(pdf_path) as pdf:
            n = len(pdf)
        cache_dir = paths.data / "ocr" / doc_id
        if redo and cache_dir.exists():
            shutil.rmtree(cache_dir)
        try:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                pages = list(pool.map(lambda i: ocr_page(pdf_path, i, cache_dir / f"page-{i + 1:04d}.json", langs, dpi),
                                      range(n)))
        except Exception as e:
            stats["errors"].append(f"{doc_id}: {type(e).__name__}: {e}")
            continue
        confs = [p["confidence"] for p in pages if p["confidence"] is not None]
        low = [p["page"] for p in pages if p["confidence"] is not None and p["confidence"] < threshold]
        blank = [p["page"] for p in pages if p["words"] == 0]
        full = "\n".join(f"[[page {p['page']}]]\n{p['text']}\n" for p in pages)
        target = paths.text / f"{doc_id}.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(full, encoding="utf-8")
        deva = devanagari_share("\n".join(p["text"] for p in pages))
        marking = MARKING.search("\n".join(p["text"] for p in pages[:2]))
        meta.update({
            "page_count": n, "text_method": "ocr", "text_path": f"data/text/{doc_id}.txt", "needs_ocr": False,
            "ocr_confidence": round(sum(confs) / len(confs), 1) if confs else None,
            "ocr_low_confidence_pages": low, "pages_without_text": blank,
            "text_quality": "ok" if confs and not low else "suspect",
            "access_marking": marking.group(1) if marking else None,
        })
        prov = meta.setdefault("field_provenance", {})
        prov["text_method"] = "rule"
        if meta.get("language") is None and (deva >= 0.6 or deva <= 0.05):
            meta["language"] = "hi" if deva >= 0.6 else "en"       # mixed-script documents stay null
            prov["language"] = "rule"
        write_json(path, meta)
        stats["documents"] += 1
        stats["pages"] += n
        stats["low_confidence_pages"] += len(low)
        stats["docs"][doc_id] = {"pages": n, "mean_confidence": meta["ocr_confidence"], "low_confidence_pages": len(low),
                                 "blank_pages": len(blank), "devanagari_share": round(deva, 2),
                                 "language": meta.get("language")}
        if low:
            review.append(f"## {doc_id} — {meta['title']}\n\nMean confidence {meta['ocr_confidence']}; "
                          f"{len(low)} of {n} pages below {threshold:.0f}:\n\n"
                          + ", ".join(f"p.{p['page']} ({p['confidence']:.0f})" for p in pages if p["page"] in low) + "\n")
    paths.reports.mkdir(parents=True, exist_ok=True)
    (paths.reports / "ocr_review.md").write_text(
        "# OCR pages to review\n\n"
        f"Tesseract ({version}), languages {langs}, {dpi} dpi. A page is listed when its mean word confidence is "
        f"below {threshold:.0f}. The text of listed pages is kept but must be checked before it is relied on.\n\n"
        + ("\n".join(review) if review else "No pages below the threshold in this run.\n"), encoding="utf-8")
    return stats
