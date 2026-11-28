"""S3 `[[page N]]` re-derivation from EXISTING text with a pinned configuration (B02 S3 rule; no OCR is run).

The importer's page format (mimamsa_importer.importer._split_pages): the text starts with `[[page N]]` on its own
line, each page body follows its marker, one LF separates a body from the next marker, and page numbers are unique.
Derivatives in another form are re-derived deterministically by `render`, which is the exact inverse of
`_split_pages`, so `_split_pages(render(pages)) == pages` for every page map (tested).

Sources this module accepts (selected by the pinned config's `sources`):
- PAGE_LIST: an explicit {physical page: text} map, e.g. Cycle 15 v7 `pages.jsonl.gz` rows [doc_id, page, text];
- FORM_FEED: one text whose pages are separated by U+000C (page 1 first), the common pdftotext layout.
Nothing else is guessed: a derivative that is in neither form is not re-derived (the item stays unresolved).

The pinned config (app/kbuild/config/page_rederive.json) is a committed input whose sha256 the build spec pins as the
`config_sha256` of the tool `mimamsa_kbuild.page_rederive`; it records `ocr: NONE` (re-derivation only).
"""
from __future__ import annotations

import hashlib
import json
import re

TOOL = "mimamsa_kbuild.page_rederive"
MARKER = re.compile(r"^\[\[page (\d+)\]\]\n", re.M)   # the importer's _MARKER, exactly


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def load_config(data: bytes) -> dict:
    cfg = json.loads(data)
    if cfg.get("record_kind") != "kbuild_page_rederive_config" or cfg.get("ocr") != "NONE":
        raise ValueError("page re-derivation config must be kbuild_page_rederive_config with ocr NONE")
    if cfg.get("page_marker") != "[[page N]]" or cfg.get("normalisation") != "NONE":
        raise ValueError("page re-derivation config: only the [[page N]] marker without normalisation is supported")
    return cfg


def render(pages: dict[int, str]) -> str:
    """{page: body} -> importer page-format text (inverse of _split_pages)."""
    if not pages:
        raise ValueError("no pages")
    out = []
    for n in sorted(pages):
        if not isinstance(n, int) or n < 1:
            raise ValueError("page numbers are positive integers")
        out.append(f"[[page {n}]]\n{pages[n]}\n")
    return "".join(out)


def split(text: str) -> dict[int, str] | None:
    """Same reading as the importer's _split_pages (kept here so S3 runs without the importer's private helper)."""
    marks = list(MARKER.finditer(text))
    if not marks or marks[0].start() != 0:
        return None
    pages = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = text[m.end():end]
        if body.endswith("\n"):
            body = body[:-1]
        n = int(m.group(1))
        if n in pages:
            return None
        pages[n] = body
    return pages


def from_form_feed(text: str) -> dict[int, str] | None:
    if "\f" not in text or MARKER.search(text):
        return None
    parts = text.split("\f")
    if parts and parts[-1] in ("", "\n"):
        parts = parts[:-1]
    return {i: p for i, p in enumerate(parts, 1)} if parts else None


def rederive(text: str | None = None, *, page_list: dict[int, str] | None = None, config: dict) -> tuple[bytes, dict[int, str], str]:
    """Return (page-format bytes, {page: body}, source kind). Raises ValueError when not re-derivable under `config`."""
    allowed = set(config.get("sources", []))
    if page_list is not None:
        if "PAGE_LIST" not in allowed:
            raise ValueError("PAGE_LIST re-derivation not enabled by the pinned config")
        pages, kind = dict(page_list), "PAGE_LIST"
    else:
        pages = from_form_feed(text or "") if "FORM_FEED" in allowed else None
        kind = "FORM_FEED"
        if pages is None:
            raise ValueError("derivative is not in a re-derivable form (no [[page N]] markers and no form feeds)")
    out = render(pages)
    if split(out) != pages:   # the inverse property, checked per item
        raise ValueError("page bodies cannot round-trip through the [[page N]] format (a body contains a marker line)")
    return out.encode("utf-8"), pages, kind
