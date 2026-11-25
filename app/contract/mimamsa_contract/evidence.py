"""Stable evidence keys for retrieval provenance (reference projection for search, viewer, graph and later
evidence packs; PR #53 Crosswalk §2).

PageKey = (source_copy_sha256, page). SpanKey adds the exact derivative binding and is returned only when every
component is present; otherwise the anchor is page-only and the reason is reported. A span never resolves against a
different (e.g. newer) derivative. No new anchor identifier is invented: the keys are deterministic tuples.
"""
from __future__ import annotations

from typing import NamedTuple


class PageKey(NamedTuple):
    source_copy_sha256: str
    page: int


class SpanKey(NamedTuple):
    page: PageKey
    pipeline_name: str
    pipeline_version: str
    derivative_text_sha256: str
    passage_id: str | None
    char_start: int | None
    char_end: int | None


def evidence_keys(anchor: dict) -> tuple[PageKey, SpanKey | None, str | None]:
    page = PageKey(anchor["source_copy_sha256"], int(anchor["page"]))
    has_span = anchor.get("passage_id") is not None or anchor.get("char_start") is not None or anchor.get("char_end") is not None
    if not has_span:
        return page, None, None
    missing = [k for k in ("pipeline_name", "pipeline_version", "derivative_text_sha256") if not anchor.get(k)]
    if missing:
        return page, None, "span not bound to a derivative (missing " + ", ".join(missing) + "): page-only"
    return page, SpanKey(page, anchor["pipeline_name"], anchor["pipeline_version"], anchor["derivative_text_sha256"],
                         anchor.get("passage_id"), anchor.get("char_start"), anchor.get("char_end")), None


def resolve_span(span: SpanKey, derived_records) -> dict | None:
    """Return the passage only from the exact derivative (copy + pipeline name/version + text hash); else None."""
    for d in derived_records:
        if (d.get("source_copy_sha256") == span.page.source_copy_sha256
                and (d.get("pipeline") or {}).get("name") == span.pipeline_name
                and (d.get("pipeline") or {}).get("version") == span.pipeline_version
                and d.get("text_sha256") == span.derivative_text_sha256):
            for p in d.get("passages", []):
                if p.get("page") == span.page.page and (span.passage_id is None or p.get("passage_id") == span.passage_id):
                    return p
    return None
