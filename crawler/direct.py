"""Explicitly listed documents: a source whose `documents` are fetched by address, nothing else.

Used for official copies on other government hosts and for hand-made lists (e.g. a list of
judgment PDFs). Discovery makes no requests: it only checks each address against the allow-list
and queues it. Every descriptive field comes from the list in sources.yaml and is carried along
so the pipeline can mark it as curated, not read from the document.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

from .config import Config, url_host
from .http import PoliteClient
from .state import StateDB

REQUIRED = ("doc_id", "url", "title", "doc_type")


@dataclass
class TargetResult:
    doc_id: str
    title: str
    status: str                      # queued | already_known | refused | invalid
    reason: str | None = None
    url: str | None = None
    warnings: list[str] = field(default_factory=list)


def discover(cfg: Config, db: StateDB, client: PoliteClient | None, source: str, *,
             only: list[str] | None = None, refresh: bool = False) -> list[TargetResult]:
    docs = cfg.source(source).get("documents") or []
    if only:
        unknown = set(only) - {d.get("doc_id") for d in docs}
        if unknown:
            raise KeyError(f"not a document of {source}: {', '.join(sorted(unknown))}")
        docs = [d for d in docs if d.get("doc_id") in only]
    out = []
    for d in docs:
        missing = [k for k in REQUIRED if not d.get(k)]
        if missing:
            out.append(TargetResult(d.get("doc_id", "?"), d.get("title", "?"), "invalid",
                                    reason=f"missing {', '.join(missing)}"))
            continue
        ok, why = cfg.is_url_allowed(source, d["url"])
        if not ok:
            out.append(TargetResult(d["doc_id"], d["title"], "refused", reason=why, url=d["url"]))
            continue
        name = unquote(PurePosixPath(urlsplit(d["url"]).path).name) or None
        is_new = db.enqueue(d["url"], source, url_host(d["url"]), "document", doc_id_hint=d["doc_id"], priority=10,
                            meta={"category": d["doc_type"], "title": d["title"], "year": str(d["year"]) if d.get("year") else None,
                                  "parent_doc_id": d.get("parent_doc_id") or d["doc_id"], "filename": name,
                                  "direct": {k: v for k, v in d.items() if k != "url"}})
        if not is_new and refresh:
            db.requeue(d["url"])
        out.append(TargetResult(d["doc_id"], d["title"], "queued" if (is_new or refresh) else "already_known", url=d["url"]))
    return out


def results_to_markdown(results: list[TargetResult]) -> str:
    lines = []
    for r in results:
        lines.append(f"- {r.doc_id}: {r.status}" + (f" ({r.reason})" if r.reason else "") + (f" — {r.url}" if r.url else ""))
    return "\n".join(lines) + "\n"
