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
    """Legacy mutable extraction suspended; use shadow_assessment.assess."""
    raise RuntimeError("C14 corpus mutation hold: legacy extraction is suspended")


def run(paths: Paths, only: list[str] | None = None, redo: bool = False, workers: int = 4) -> dict:
    """Do not replace or remove prior text and metadata during C14 adoption."""
    raise RuntimeError("C14 corpus mutation hold: legacy extraction is suspended")
