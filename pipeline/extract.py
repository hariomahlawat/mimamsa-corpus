"""Stage 'extract': text from PDFs, with page markers, into data/text/<doc_id>.txt.

Uses the PDF's text layer only. A document without a usable text layer is marked needs_ocr and gets
no text file (bad text is never kept silently); the OCR stage will handle those. A text layer that
exists but does not read as the expected language is kept and marked text_quality = suspect.

Slanted text is dropped: India Code stamps a diagonal "IndiaCode" watermark on every page at
download, and legal text is never set at an angle.
"""
from __future__ import annotations

import json
import re

import pymupdf

from .common import Paths, write_json

MIN_CHARS_PER_PAGE = 80          # fewer printable characters than this = the page has no usable text
OCR_SHARE = 0.5                  # more than half the pages without text = the document needs OCR
COMMON_EN = {"the", "of", "and", "to", "in", "or", "any", "be", "by", "a", "is", "shall", "for", "such", "under"}
# A marking counts only when it stands alone on a line of the first two pages, not as a word in a sentence.
MARKING = re.compile(r"^[ \t]*(for official use only|restricted|confidential|secret)[ \t]*$", re.I | re.M)


def page_text(page) -> tuple[str, int]:
    """(text of horizontal lines, characters dropped as slanted)."""
    kept, dropped = [], 0
    for block in page.get_text("dict").get("blocks", []):
        lines = []
        for line in block.get("lines", []):
            text = "".join(s["text"] for s in line["spans"])
            dx, dy = line["dir"]
            if abs(dy) > 0.2 and abs(dx) > 0.2:          # diagonal: watermark
                dropped += len(text.strip())
                continue
            if text.strip():
                lines.append(text.rstrip())
        if lines:
            kept.append("\n".join(lines))
    return "\n\n".join(kept), dropped


def reads_as_english(text: str) -> bool:
    words = re.findall(r"[A-Za-z]+", text.lower())
    if len(words) < 50:
        return False
    return sum(w in COMMON_EN for w in words) / len(words) >= 0.12


def devanagari_share(text: str) -> float:
    letters = [ch for ch in text if ch.isalpha()]
    return sum("ऀ" <= ch <= "ॿ" for ch in letters) / len(letters) if letters else 0.0


def extract_document(paths: Paths, meta: dict) -> dict:
    """Extract one document; returns the fields to merge into its metadata."""
    with pymupdf.open(paths.raw_file(meta["raw_path"])) as pdf:
        pages, dropped = [], 0
        for page in pdf:
            text, d = page_text(page)
            pages.append(text)
            dropped += d
    n = len(pages)
    empty = [i + 1 for i, t in enumerate(pages) if len(re.sub(r"\s", "", t)) < MIN_CHARS_PER_PAGE]
    out = {"page_count": n or None, "pages_without_text": empty, "watermark_chars_dropped": dropped}
    if n == 0 or len(empty) / n > OCR_SHARE:
        return {**out, "text_method": None, "text_path": None, "text_quality": None, "needs_ocr": True,
                "access_marking": None}
    full = "\n".join(f"[[page {i + 1}]]\n{t}\n" for i, t in enumerate(pages))
    sample = "\n".join(pages)
    lang = meta.get("language")
    deva = devanagari_share(sample)
    if lang == "hi":
        quality = "ok" if deva >= 0.5 else "suspect"
    elif reads_as_english(sample):
        quality = "ok"
    else:
        quality = "ok" if (lang is None and deva >= 0.5) else "suspect"
    rel = f"data/text/{meta['doc_id']}.txt"
    target = paths.text / f"{meta['doc_id']}.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(full, encoding="utf-8")
    marking = MARKING.search("\n".join(pages[:2]))
    return {**out, "text_method": "pdf_text", "text_path": rel, "text_quality": quality, "needs_ocr": False,
            "access_marking": marking.group(1) if marking else None, "devanagari_share": round(deva, 2)}


def _extract_one(args):
    paths, meta = args
    try:
        return meta["doc_id"], extract_document(paths, meta), None
    except Exception as e:                           # a damaged PDF must not stop the run
        return meta["doc_id"], None, f"{meta['doc_id']}: {type(e).__name__}: {e}"


def run(paths: Paths, only: list[str] | None = None, redo: bool = False, workers: int = 4) -> dict:
    stats = {"extracted": 0, "unchanged": 0, "needs_ocr": 0, "kept_ocr": 0, "suspect": 0, "not_pdf": 0, "errors": [],
             "marked": [], "watermark_chars_dropped": 0}
    todo: dict[str, tuple] = {}
    for path in sorted(paths.meta.glob("*.json")):
        meta = json.loads(path.read_text(encoding="utf-8"))
        if only and meta["doc_id"] not in only:
            continue
        if meta.get("mime_type") != "application/pdf":
            stats["not_pdf"] += 1
            continue
        if meta.get("text_method") == "ocr":         # already read by the OCR stage; do not undo that
            stats["kept_ocr"] += 1
            continue
        done = meta.get("needs_ocr") is not None and (meta.get("needs_ocr") or
                                                       (meta.get("text_path") and (paths.data.parent / meta["text_path"]).exists()))
        if done and not redo:                        # same file already extracted (records resets these on a new file)
            stats["unchanged"] += 1
            continue
        todo[meta["doc_id"]] = (path, meta)
    jobs = [(paths, meta) for _, meta in todo.values()]
    def outcomes():
        """Results as they are ready, so each record is saved at once and an interrupted run loses nothing."""
        if len(jobs) > 20 and workers > 1:           # many documents: use several processes
            from concurrent.futures import ProcessPoolExecutor
            with ProcessPoolExecutor(max_workers=workers) as pool:
                yield from pool.map(_extract_one, jobs, chunksize=8)
        else:
            for j in jobs:
                yield _extract_one(j)

    for doc_id, res, err in outcomes():
        path, meta = todo[doc_id]
        if err:
            stats["errors"].append(err)
            continue
        stats["watermark_chars_dropped"] += res.pop("watermark_chars_dropped", 0)
        res.pop("devanagari_share", None)
        stale = paths.text / f"{meta['doc_id']}.txt"
        if res["needs_ocr"] and stale.exists():
            stale.unlink()
        meta.update(res)
        prov = meta.setdefault("field_provenance", {})
        prov["page_count"] = "rule"
        if res["text_method"]:
            prov["text_method"] = "rule"
        if res["access_marking"]:
            prov["access_marking"] = "rule"
            stats["marked"].append(f"{meta['doc_id']}: {res['access_marking']}")
        write_json(path, meta)
        stats["extracted" if res["text_method"] else "needs_ocr"] += 1
        stats["suspect"] += res["text_quality"] == "suspect"
    return stats
