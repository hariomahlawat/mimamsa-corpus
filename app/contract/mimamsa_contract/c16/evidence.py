"""Consumer-side evidence checks for C16 anchors (contract section 6.6).

Cross-record binding (rules.exchange_issues) proves that an anchor names an existing copy, representation,
derivative, image occurrence and page. It cannot prove that the span is really in the derivative. These functions
check the bytes: the derivative must hash to the anchor's derivative_text_sha256, the unit (page, reconstructed page
or generated segment) must exist in the [[page N]] text, and the code-point slice must hash to text_sha256.

Only anchors that pass are usable for citation or as graph evidence; nothing here promotes an anchor.
"""
from __future__ import annotations

import hashlib
import re

MARKER = re.compile(r"^\[\[page (\d+)\]\]\n", re.M)


def split_pages(text: str) -> dict[int, str] | None:
    """Importer page format (app/importer _split_pages): page N is the text after its marker line up to the next
    marker line, without the single newline before the next marker or the end. None when malformed."""
    marks = list(MARKER.finditer(text))
    if not marks or marks[0].start() != 0:
        return None
    pages: dict[int, str] = {}
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


def _unit(anchor: dict) -> int | None:
    loc = anchor["locator"]
    return {"SOURCE_PHYSICAL_PAGE": loc.get("physical_page"), "RECONSTRUCTED_PAGE": loc.get("reconstructed_page"),
            "GENERATED_SEGMENT": loc.get("generated_segment")}.get(loc["kind"])


def verify_anchor_bytes(anchor: dict, derivative_bytes: bytes) -> list[str]:
    """Problems with an anchor's span against the exact derivative bytes (empty list = verified)."""
    if anchor.get("derivative_text_sha256") is None or not anchor.get("text_span"):
        return ["C16_SPAN_UNBOUND"]
    if hashlib.sha256(derivative_bytes).hexdigest() != anchor["derivative_text_sha256"]:
        return ["C16_DERIVATIVE_BYTES_MISMATCH"]
    try:
        text = derivative_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return ["C16_DERIVATIVE_NOT_UTF8"]
    span = anchor["text_span"]
    unit = _unit(anchor)
    if unit is None:
        # image-sequence or text-flow anchors: offsets count into the whole derivative (one image OCR text)
        body = text
    else:
        pages = split_pages(text)
        if pages is None:
            return ["C16_DERIVATIVE_MARKERS_MALFORMED"]
        if unit not in pages:
            return ["C16_SPAN_UNIT_MISSING"]
        body = pages[unit]
    s, e = span["char_start"], span["char_end"]
    if not 0 <= s <= e <= len(body):  # Python str offsets are code points, as the contract
        return ["C16_SPAN_OUT_OF_RANGE"]
    if hashlib.sha256(body[s:e].encode("utf-8")).hexdigest() != span["text_sha256"]:
        return ["C16_SPAN_MISMATCH"]
    return []


def usable_for_citation(anchor: dict, identity: dict, span_verified: bool) -> bool:
    """A page citation may rest on this anchor: a citable source page (or checked mapping), a copy whose research
    eligibility permits page citation, not judged INCORRECT, and either page-only or with a byte-verified span."""
    loc = anchor["locator"]
    return bool(loc.get("citable_as_source_page")
                and identity["research_eligibility"]["source_page_citation_permitted"]
                and anchor["verification"]["state"] != "INCORRECT"
                and (anchor.get("text_span") is None or span_verified))


def usable_as_graph_evidence(anchor: dict, identity: dict, span_verified: bool) -> bool:
    """An edge may show this anchor as its evidence location: the copy permits graph evidence, the anchor is not
    INCORRECT, and a span (if any) is byte-verified. Low-confidence OCR may locate a candidate but never supports a
    raised verification (rules C16_FINDING_ON_WEAK_ANCHOR)."""
    return bool(identity["research_eligibility"]["graph_evidence_permitted"]
                and anchor["verification"]["state"] != "INCORRECT"
                and (anchor.get("text_span") is None or span_verified))
