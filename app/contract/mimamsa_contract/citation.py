"""Reference legal-citation formatter (design 03 §5, finding F12).

Output follows the conventional order: case name or title; neutral citation, else reported citation; (court, date);
pinpoint (para N where the judgment prints numbered paragraphs, otherwise p. N). Internal identifiers (doc_id, sha256,
release id) never appear in the citation text; they go in a separate internal reference. Only printed or rule/crawler
metadata is used: fields whose origin is 'llm' are omitted, and absent parts are omitted, never guessed.
"""
from __future__ import annotations

from datetime import date


def _ok(doc: dict, field: str) -> bool:
    return (doc.get("field_origin") or {}).get(field) != "llm"


def _fmt_date(iso: str | None) -> str | None:
    if not iso:
        return None
    try:
        d = date.fromisoformat(iso)
    except ValueError:
        return None
    return f"{d.day} {d.strftime('%B')} {d.year}"


def format_legal_citation(doc: dict, *, page: int | None = None, paragraph_label: str | None = None) -> str:
    j = doc.get("judicial") or {}
    parts = []
    title = doc.get("title") if _ok(doc, "title") else None
    parties = j.get("parties") or {}
    if parties.get("petitioner") and parties.get("respondent") and _ok(doc, "parties"):
        name = f"{parties['petitioner']} v. {parties['respondent']}"
    else:
        name = title
    if name:
        parts.append(name)
    cite = None
    if j.get("neutral_citation") and _ok(doc, "neutral_citation"):
        cite = j["neutral_citation"]
    elif j.get("reported_citations") and _ok(doc, "reported_citations"):
        cite = j["reported_citations"][0]
    elif j.get("case_numbers") and _ok(doc, "case_numbers"):
        cite = j["case_numbers"][0]
    elif doc.get("number") and _ok(doc, "number"):
        cite = doc["number"]
    if cite:
        parts.append(cite)
    court = (j.get("court") if _ok(doc, "court") else None) or (doc.get("issuing_authority") if _ok(doc, "issuing_authority") else None)
    when = _fmt_date(doc.get("issue_date")) if _ok(doc, "issue_date") else None
    paren = ", ".join(x for x in (court, when) if x)
    text = ", ".join(parts) if parts else "[title not printed]"
    if paren:
        text += f" ({paren})"
    if paragraph_label:
        text += f", para {paragraph_label}"
    elif page:
        text += f", p. {page}"
    return text


def internal_reference(doc: dict, *, page: int | None, release_id: str | None) -> str:
    sha = (doc.get("source_copy") or {}).get("sha256", "")[:12]
    return f"[{doc.get('doc_id')} · copy {sha} · p.{page} · {release_id}]"
