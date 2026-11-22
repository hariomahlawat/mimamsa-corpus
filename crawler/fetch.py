"""Download queued documents into data/raw/<source>/<yyyy>/<sha256>.<ext>. Raw files are never modified."""
from __future__ import annotations

import hashlib
import re
import json
import logging
import os
from pathlib import Path
from urllib.parse import urlsplit

from .config import Config
from .http import Blocked, CrawlError, FetchError, FetchResult, PoliteClient, is_pdf_url
from .state import StateDB

log = logging.getLogger("mimamsa.fetch")
EXT_BY_TYPE = {"application/pdf": ".pdf", "text/html": ".html", "application/json": ".json",
               "application/hal+json": ".json"}


def _ext(r: FetchResult, url: str) -> str:
    if r.content.startswith(b"%PDF"):
        return ".pdf"
    suffix = Path(urlsplit(url).path).suffix.lower()
    return EXT_BY_TYPE.get(r.content_type or "") or (suffix if suffix.isascii() and 1 < len(suffix) <= 6 else ".bin")


def _is_json(content: bytes) -> bool:
    try:
        json.loads(content)
        return True
    except ValueError:
        return False



_NOTE_MD5_SIZE = re.compile(r"expected md5 ([0-9a-f]{32}),\s*([0-9]+) bytes")


def integrity_problem(content: bytes, direct: dict | None) -> str | None:
    """Pinned-document integrity check, applied BEFORE a file is stored or marked fetched.

    Enforced: expected_sha256, expected_md5, expected_bytes (ACQ-02/ACQ-03 archive.org), the ACQ-01 `note` form
    "expected md5 <hex>, <n> bytes", and expected_served_sha256 (a reviewed pin of a host-watermarked file).
    Not enforced: listing_md5 / listing_bytes (India Code listing values describe the stored bitstream, not the
    served, watermarked bytes; served_bytes_policy HOST_WATERMARKS_PDF)."""
    if not direct:
        return None
    exp = {}
    if direct.get("expected_sha256"):
        exp["sha256"] = str(direct["expected_sha256"]).lower()
    if direct.get("expected_md5"):
        exp["md5"] = str(direct["expected_md5"]).lower()
    if direct.get("expected_bytes"):
        exp["bytes"] = int(direct["expected_bytes"])
    m = _NOTE_MD5_SIZE.search(str(direct.get("note") or ""))
    if m:
        exp.setdefault("md5", m.group(1))
        exp.setdefault("bytes", int(m.group(2)))
    if direct.get("expected_served_sha256"):
        exp["served_sha256"] = str(direct["expected_served_sha256"]).lower()
    bad = []
    if "sha256" in exp and hashlib.sha256(content).hexdigest() != exp["sha256"]:
        bad.append("sha256")
    if "served_sha256" in exp and hashlib.sha256(content).hexdigest() != exp["served_sha256"]:
        bad.append("served sha256")
    if "md5" in exp and hashlib.md5(content).hexdigest() != exp["md5"]:
        bad.append("md5")
    if "bytes" in exp and len(content) != exp["bytes"]:
        bad.append(f"size ({len(content)} != {exp['bytes']})")
    return ("integrity check failed: " + ", ".join(bad) + " differ from the pinned values") if bad else None

def fetch_documents(cfg: Config, db: StateDB, client: PoliteClient, source: str, root: Path, *,
                    limit: int = 50, workers: int = 1) -> dict[str, int]:
    """`workers` > 1 downloads in parallel and is honoured only for `open_data_bucket` sources."""
    stats = {"downloaded": 0, "duplicate": 0, "not_modified": 0, "retry_later": 0, "failed": 0,
             "skipped": 0, "bytes": 0, "blocked": 0, "checksum_differs_from_listing": 0}
    retry = dict(max_retries=cfg.setting(source, "max_retries"),
                 backoff_base=cfg.setting(source, "backoff_base_seconds"))
    queue = db.due(source, kind="document", limit=limit)
    parallel = workers > 1 and bool(cfg.source(source).get("open_data_bucket"))

    def outcomes():
        if not parallel:
            for q in queue:
                headers = {}
                if q.etag:
                    headers["If-None-Match"] = q.etag
                if q.last_modified:
                    headers["If-Modified-Since"] = q.last_modified
                try:
                    yield q, client.get(q.url, headers=headers)
                except CrawlError as e:
                    yield q, e
            return
        for i in range(0, len(queue), 200):                # in batches, so memory stays bounded
            batch = queue[i:i + 200]
            yield from zip(batch, client.get_many([q.url for q in batch], workers))

    for q, got in outcomes():
        try:
            if isinstance(got, Exception):
                raise got
            r = got
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
        elif ((is_pdf_url(q.url) or str(q.meta.get("filename") or "").lower().endswith(".pdf"))
              and not r.content.startswith(b"%PDF")):
            problem = f"expected a PDF, got {r.content_type or 'unknown type'} (possible block or error page)"
        elif q.meta.get("category") == "linked_records" and not _is_json(r.content):
            problem = f"expected JSON records, got {r.content_type or 'unknown type'}"
        if not problem:
            problem = integrity_problem(r.content, q.meta.get("direct"))
        if problem:
            db.mark_attempt_failed(q.url, error=problem, status_code=r.status, retryable=False, **retry)
            stats["failed"] += 1
            log.warning("%s: %s", q.url, problem)
            continue

        # India Code lists an MD5 for each stored file but stamps an "India Code" watermark onto PDFs as
        # they are downloaded, so the bytes served differ from the listing (seen 2026-11-21: same bytes
        # on repeat downloads, larger than the listed size). A difference is counted, not treated as damage.
        if q.meta.get("md5") and hashlib.md5(r.content).hexdigest() != str(q.meta["md5"]).lower():
            stats["checksum_differs_from_listing"] += 1
            log.info("%s: served file differs from the listed MD5 (expected for watermarked PDFs)", q.url)

        sha = hashlib.sha256(r.content).hexdigest()
        year = str(q.meta.get("year") or "")
        if not (len(year) == 4 and year.isdigit()):
            year = "0000"                                  # 0000 = year not known at download time
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
