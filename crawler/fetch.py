"""Download queued documents into data/raw/<source>/<yyyy>/<sha256>.<ext>. Raw files are never modified."""
from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from urllib.parse import urlsplit

from .config import Config
from .http import Blocked, CrawlError, FetchError, FetchResult, PoliteClient, is_pdf_url
from .state import StateDB

log = logging.getLogger("mimamsa.fetch")
EXT_BY_TYPE = {"application/pdf": ".pdf", "text/html": ".html"}


def _ext(r: FetchResult, url: str) -> str:
    if r.content.startswith(b"%PDF"):
        return ".pdf"
    suffix = Path(urlsplit(url).path).suffix.lower()
    return EXT_BY_TYPE.get(r.content_type or "") or (suffix if suffix.isascii() and 1 < len(suffix) <= 6 else ".bin")


def fetch_documents(cfg: Config, db: StateDB, client: PoliteClient, source: str, root: Path, *,
                    limit: int = 50) -> dict[str, int]:
    stats = {"downloaded": 0, "duplicate": 0, "not_modified": 0, "retry_later": 0, "failed": 0,
             "skipped": 0, "bytes": 0, "blocked": 0}
    retry = dict(max_retries=cfg.setting(source, "max_retries"),
                 backoff_base=cfg.setting(source, "backoff_base_seconds"))
    for q in db.due(source, kind="document", limit=limit):
        headers = {}
        if q.etag:
            headers["If-None-Match"] = q.etag
        if q.last_modified:
            headers["If-Modified-Since"] = q.last_modified
        try:
            r = client.get(q.url, headers=headers)
        except Blocked as e:
            db.mark_skipped(q.url, f"blocked: {e}")
            stats["blocked"] += 1
            log.error("BLOCKED, stopping %s: %s", source, e)
            break
        except FetchError as e:
            status = db.mark_attempt_failed(q.url, error=str(e), status_code=e.status_code,
                                            retryable=e.retryable, **retry)
            stats["retry_later" if status == "queued" else "failed"] += 1
            log.warning("%s: %s (%s)", q.url, e, status)
            continue
        except CrawlError as e:
            db.mark_skipped(q.url, str(e))
            stats["skipped"] += 1
            continue

        if r.status == 304:
            db.mark_fetched(q.url, status_code=304, sha256=None, nbytes=None, content_type=None)
            stats["not_modified"] += 1
            continue
        problem = None
        if r.status != 200:
            problem = f"HTTP {r.status}"
        elif not r.content:
            problem = "empty body"
        elif is_pdf_url(q.url) and not r.content.startswith(b"%PDF"):
            problem = f"expected a PDF, got {r.content_type or 'unknown type'} (possible block or error page)"
        if problem:
            db.mark_attempt_failed(q.url, error=problem, status_code=r.status, retryable=False, **retry)
            stats["failed"] += 1
            log.warning("%s: %s", q.url, problem)
            continue

        sha = hashlib.sha256(r.content).hexdigest()
        year = str(q.meta.get("year") or "0000")          # 0000 = year not known at download time
        rel = Path("data") / "raw" / source / year / f"{sha}{_ext(r, q.url)}"
        if db.has_file(sha):
            stats["duplicate"] += 1
        else:
            dest = root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                tmp = dest.with_suffix(dest.suffix + ".part")
                tmp.write_bytes(r.content)
                os.replace(tmp, dest)
            stats["downloaded"] += 1
            stats["bytes"] += len(r.content)
        db.record_file(sha256=sha, raw_path=rel.as_posix(), url=q.url, nbytes=len(r.content),
                       content_type=r.content_type)
        db.mark_fetched(q.url, status_code=200, sha256=sha, nbytes=len(r.content), content_type=r.content_type,
                        etag=r.headers.get("etag"), last_modified=r.headers.get("last-modified"))
    return stats
