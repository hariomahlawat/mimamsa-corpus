"""Crawl state in SQLite: URL queue, fetch status, retries, ETags, file dedupe, request audit.

Every state change is committed immediately, so killing the crawler at any point
loses at most the request in flight (its URL simply stays `queued`).
"""
from __future__ import annotations

import json
import random
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

SCHEMA_VERSION = 1

URL_STATUSES = ("queued", "fetched", "failed", "skipped")
URL_KINDS = ("listing", "document", "robots")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS urls (
    url              TEXT PRIMARY KEY,
    source           TEXT NOT NULL,
    host             TEXT NOT NULL,
    kind             TEXT NOT NULL CHECK (kind IN ('listing','document','robots')),
    status           TEXT NOT NULL CHECK (status IN ('queued','fetched','failed','skipped')),
    doc_id_hint      TEXT,
    discovered_from  TEXT,
    priority         INTEGER NOT NULL DEFAULT 100,
    attempts         INTEGER NOT NULL DEFAULT 0,
    next_attempt_at  TEXT,
    last_attempt_at  TEXT,
    last_status_code INTEGER,
    last_error       TEXT,
    skip_reason      TEXT,
    etag             TEXT,
    last_modified    TEXT,
    sha256           TEXT,
    bytes            INTEGER,
    content_type     TEXT,
    first_seen_at    TEXT NOT NULL,
    fetched_at       TEXT
);
CREATE INDEX IF NOT EXISTS urls_queue ON urls (source, status, next_attempt_at, priority);

CREATE TABLE IF NOT EXISTS files (
    sha256        TEXT PRIMARY KEY,
    raw_path      TEXT NOT NULL,
    first_url     TEXT NOT NULL,
    bytes         INTEGER NOT NULL,
    content_type  TEXT,
    retrieved_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS aliases (
    sha256   TEXT NOT NULL REFERENCES files(sha256),
    url      TEXT NOT NULL,
    seen_at  TEXT NOT NULL,
    PRIMARY KEY (sha256, url)
);

CREATE TABLE IF NOT EXISTS runs (
    run_id      TEXT PRIMARY KEY,
    mode        TEXT NOT NULL,
    sources     TEXT NOT NULL,
    args        TEXT,
    started_at  TEXT NOT NULL,
    ended_at    TEXT,
    outcome     TEXT,
    summary     TEXT
);

CREATE TABLE IF NOT EXISTS requests (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT,
    ts          TEXT NOT NULL,
    method      TEXT NOT NULL,
    url         TEXT NOT NULL,
    status_code INTEGER,
    bytes       INTEGER,
    elapsed_ms  INTEGER,
    error       TEXT
);
CREATE INDEX IF NOT EXISTS requests_run ON requests (run_id);
"""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def backoff_delay(attempts: int, base: float, cap: float = 3600.0, jitter: bool = True) -> float:
    """Exponential backoff for the `attempts`-th failure (1-based), with up to 25% jitter."""
    delay = min(cap, base * (2 ** max(0, attempts - 1)))
    return delay * (1 + random.uniform(0, 0.25)) if jitter else delay


@dataclass
class QueuedURL:
    url: str
    source: str
    kind: str
    doc_id_hint: str | None
    attempts: int
    etag: str | None
    last_modified: str | None


class StateDB:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        if str(path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), isolation_level=None)  # autocommit; explicit txns below
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA busy_timeout=10000")
        self._migrate()

    # ------------------------------------------------------------------ setup
    def _migrate(self) -> None:
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        if version > SCHEMA_VERSION:
            raise RuntimeError(f"{self.path} has schema v{version}; this code knows v{SCHEMA_VERSION}")
        if version < 1:
            self.conn.executescript(_SCHEMA)
            self.conn.execute(f"PRAGMA user_version={SCHEMA_VERSION}")

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "StateDB":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _tx(self):
        return _Tx(self.conn)

    # ------------------------------------------------------------------- runs
    def start_run(self, mode: str, sources: list[str], args: dict[str, Any] | None = None) -> str:
        run_id = utcnow().strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
        self.conn.execute(
            "INSERT INTO runs (run_id, mode, sources, args, started_at) VALUES (?,?,?,?,?)",
            (run_id, mode, ",".join(sources), json.dumps(args or {}), iso(utcnow())),
        )
        return run_id

    def end_run(self, run_id: str, outcome: str, summary: dict[str, Any] | None = None) -> None:
        self.conn.execute(
            "UPDATE runs SET ended_at=?, outcome=?, summary=? WHERE run_id=?",
            (iso(utcnow()), outcome, json.dumps(summary or {}), run_id),
        )

    def last_runs(self, limit: int = 5) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM runs ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()

    # ------------------------------------------------------------------ queue
    def enqueue(self, url: str, source: str, host: str, kind: str, *, doc_id_hint: str | None = None,
                discovered_from: str | None = None, priority: int = 100) -> bool:
        """Add a URL if unseen. Returns True if newly queued. Never resurrects fetched/failed/skipped URLs."""
        if kind not in URL_KINDS:
            raise ValueError(f"bad kind {kind!r}")
        cur = self.conn.execute(
            """INSERT OR IGNORE INTO urls
               (url, source, host, kind, status, doc_id_hint, discovered_from, priority, first_seen_at)
               VALUES (?,?,?,?, 'queued', ?,?,?,?)""",
            (url, source, host, kind, doc_id_hint, discovered_from, priority, iso(utcnow())),
        )
        return cur.rowcount == 1

    def requeue(self, url: str) -> None:
        """Explicitly put a URL back in the queue (refresh runs). Keeps ETag/Last-Modified."""
        self.conn.execute(
            "UPDATE urls SET status='queued', attempts=0, next_attempt_at=NULL, last_error=NULL, skip_reason=NULL "
            "WHERE url=?", (url,),
        )

    def due(self, source: str, *, limit: int = 100, now: datetime | None = None,
            kind: str | None = None) -> list[QueuedURL]:
        now_s = iso(now or utcnow())
        sql = ("SELECT * FROM urls WHERE source=? AND status='queued' "
               "AND (next_attempt_at IS NULL OR next_attempt_at<=?)")
        params: list[Any] = [source, now_s]
        if kind:
            sql += " AND kind=?"
            params.append(kind)
        sql += " ORDER BY priority, first_seen_at LIMIT ?"
        params.append(limit)
        return [QueuedURL(r["url"], r["source"], r["kind"], r["doc_id_hint"], r["attempts"],
                          r["etag"], r["last_modified"])
                for r in self.conn.execute(sql, params)]

    def get(self, url: str) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM urls WHERE url=?", (url,)).fetchone()

    def mark_fetched(self, url: str, *, status_code: int, sha256: str | None, nbytes: int | None,
                     content_type: str | None, etag: str | None = None,
                     last_modified: str | None = None) -> None:
        now = iso(utcnow())
        self.conn.execute(
            """UPDATE urls SET status='fetched', attempts=attempts+1, last_attempt_at=?, fetched_at=?,
               last_status_code=?, last_error=NULL, next_attempt_at=NULL,
               sha256=COALESCE(?, sha256), bytes=COALESCE(?, bytes), content_type=COALESCE(?, content_type),
               etag=COALESCE(?, etag), last_modified=COALESCE(?, last_modified)
               WHERE url=?""",
            (now, now, status_code, sha256, nbytes, content_type, etag, last_modified, url),
        )

    def mark_attempt_failed(self, url: str, *, error: str, status_code: int | None, max_retries: int,
                            backoff_base: float, retryable: bool = True,
                            now: datetime | None = None) -> str:
        """Record a failed attempt. Returns the new status: 'queued' (will retry) or 'failed' (gave up)."""
        now = now or utcnow()
        with self._tx():
            row = self.conn.execute("SELECT attempts FROM urls WHERE url=?", (url,)).fetchone()
            if row is None:
                raise KeyError(url)
            attempts = row["attempts"] + 1
            give_up = (not retryable) or attempts >= max_retries
            status = "failed" if give_up else "queued"
            nxt = None if give_up else iso(now + timedelta(seconds=backoff_delay(attempts, backoff_base)))
            self.conn.execute(
                """UPDATE urls SET status=?, attempts=?, last_attempt_at=?, last_status_code=?,
                   last_error=?, next_attempt_at=? WHERE url=?""",
                (status, attempts, iso(now), status_code, error[:2000], nxt, url),
            )
        return status

    def mark_skipped(self, url: str, reason: str) -> None:
        self.conn.execute(
            "UPDATE urls SET status='skipped', skip_reason=?, next_attempt_at=NULL WHERE url=?",
            (reason[:2000], url),
        )

    # ------------------------------------------------------------------ files
    def record_file(self, *, sha256: str, raw_path: str, url: str, nbytes: int,
                    content_type: str | None) -> bool:
        """Register downloaded bytes. Returns True if new; False if a duplicate (URL stored as alias)."""
        now = iso(utcnow())
        with self._tx():
            existing = self.conn.execute("SELECT first_url FROM files WHERE sha256=?", (sha256,)).fetchone()
            if existing is None:
                self.conn.execute(
                    "INSERT INTO files (sha256, raw_path, first_url, bytes, content_type, retrieved_at) "
                    "VALUES (?,?,?,?,?,?)", (sha256, raw_path, url, nbytes, content_type, now))
                return True
            if existing["first_url"] != url:
                self.conn.execute("INSERT OR IGNORE INTO aliases (sha256, url, seen_at) VALUES (?,?,?)",
                                  (sha256, url, now))
            return False

    def has_file(self, sha256: str) -> bool:
        return self.conn.execute("SELECT 1 FROM files WHERE sha256=?", (sha256,)).fetchone() is not None

    def aliases(self, sha256: str) -> list[str]:
        return [r["url"] for r in self.conn.execute(
            "SELECT url FROM aliases WHERE sha256=? ORDER BY seen_at", (sha256,))]

    # --------------------------------------------------------------- requests
    def log_request(self, *, run_id: str | None, method: str, url: str, status_code: int | None,
                    nbytes: int | None, elapsed_ms: int | None, error: str | None = None,
                    ts: datetime | None = None) -> None:
        self.conn.execute(
            "INSERT INTO requests (run_id, ts, method, url, status_code, bytes, elapsed_ms, error) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (run_id, iso(ts or utcnow()), method, url, status_code, nbytes, elapsed_ms, error),
        )

    # ----------------------------------------------------------------- report
    def counts(self, source: str | None = None) -> dict[str, dict[str, int]]:
        """{source: {status: n}} including zero rows for every status."""
        sql = "SELECT source, status, COUNT(*) n FROM urls"
        params: tuple = ()
        if source:
            sql += " WHERE source=?"
            params = (source,)
        out: dict[str, dict[str, int]] = {}
        for r in self.conn.execute(sql + " GROUP BY source, status", params):
            out.setdefault(r["source"], {s: 0 for s in URL_STATUSES})[r["status"]] = r["n"]
        return out

    def failures(self, source: str | None = None, limit: int = 20) -> Iterator[sqlite3.Row]:
        sql = "SELECT url, attempts, last_status_code, last_error FROM urls WHERE status='failed'"
        params: list[Any] = []
        if source:
            sql += " AND source=?"
            params.append(source)
        return self.conn.execute(sql + " ORDER BY last_attempt_at DESC LIMIT ?", (*params, limit))


class _Tx:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def __enter__(self):
        self.conn.execute("BEGIN IMMEDIATE")

    def __exit__(self, exc_type, *_):
        self.conn.execute("ROLLBACK" if exc_type else "COMMIT")
