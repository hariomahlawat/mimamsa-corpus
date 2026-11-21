"""Logging: human log (console + state/logs/crawl.log) and the request audit trail.

Every HTTP request goes through `AuditLog.request(...)`, which writes one JSON line to
state/logs/requests-YYYYMMDD.jsonl AND a row in the `requests` table of crawl.sqlite.
The JSONL copy survives even if the database is lost or rebuilt.
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from datetime import datetime, timezone
from pathlib import Path

from .state import StateDB, iso, utcnow

LOG_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"


def setup_logging(log_dir: Path, *, verbose: bool = False, console: bool = True) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger("mimamsa")
    root.setLevel(logging.DEBUG)
    for h in list(root.handlers):
        root.removeHandler(h)
        h.close()
    fh = logging.handlers.RotatingFileHandler(log_dir / "crawl.log", maxBytes=20_000_000, backupCount=10,
                                              encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(LOG_FORMAT))
    root.addHandler(fh)
    if console:
        ch = logging.StreamHandler(sys.stderr)
        ch.setLevel(logging.DEBUG if verbose else logging.INFO)
        ch.setFormatter(logging.Formatter("%(levelname)-7s %(message)s"))
        root.addHandler(ch)
    root.propagate = False
    return root


class AuditLog:
    def __init__(self, log_dir: Path, db: StateDB, run_id: str | None):
        self.log_dir = log_dir
        self.db = db
        self.run_id = run_id
        log_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, ts: datetime) -> Path:
        return self.log_dir / f"requests-{ts.strftime('%Y%m%d')}.jsonl"

    def request(self, *, method: str, url: str, status_code: int | None, nbytes: int | None,
                elapsed_ms: int | None, error: str | None = None, source: str | None = None) -> None:
        ts = utcnow()
        line = {"ts": iso(ts), "run_id": self.run_id, "source": source, "method": method, "url": url,
                "status": status_code, "bytes": nbytes, "elapsed_ms": elapsed_ms, "error": error}
        with self._path(ts).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")
        self.db.log_request(run_id=self.run_id, method=method, url=url, status_code=status_code,
                            nbytes=nbytes, elapsed_ms=elapsed_ms, error=error, ts=ts)
        logging.getLogger("mimamsa.http").debug("%s %s -> %s (%s B, %s ms)%s", method, url, status_code,
                                                 nbytes, elapsed_ms, f" ERROR {error}" if error else "")


def read_audit(log_dir: Path, day: datetime | None = None) -> list[dict]:
    p = log_dir / f"requests-{(day or datetime.now(timezone.utc)).strftime('%Y%m%d')}.jsonl"
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
