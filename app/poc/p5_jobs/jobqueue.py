"""Durable PostgreSQL job queue (FOR UPDATE SKIP LOCKED) with leases, retries with exponential backoff,
idempotency keys, checkpoints for resumability, per-kind concurrency limits and a lease reaper.

Windows mapping (design, not run here): worker = Windows Service under a dedicated virtual account;
sandbox subprocess = Job Object with JOB_OBJECT_LIMIT_PROCESS_MEMORY + JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE,
restricted token / AppContainer, no network via Windows Firewall rule scoped to the sandbox executable.
"""
from __future__ import annotations

import json
import os
import random
import socket
import time

import psycopg
from psycopg.types.json import Jsonb

DSN = os.environ.get("POC_DSN", "host=127.0.0.1 port=55432 user=poc dbname=poc")

SCHEMA = """
CREATE TABLE IF NOT EXISTS job_kinds(kind text PRIMARY KEY, max_concurrency int NOT NULL DEFAULT 2,
                                     max_attempts int NOT NULL DEFAULT 5, lease_seconds int NOT NULL DEFAULT 30);
CREATE TABLE IF NOT EXISTS jobs(
  id bigserial PRIMARY KEY,
  kind text NOT NULL REFERENCES job_kinds(kind),
  idempotency_key text UNIQUE,
  payload jsonb NOT NULL,
  state text NOT NULL DEFAULT 'queued' CHECK (state IN ('queued','running','succeeded','failed','dead')),
  priority int NOT NULL DEFAULT 100,
  attempts int NOT NULL DEFAULT 0,
  run_after timestamptz NOT NULL DEFAULT now(),
  locked_by text, lease_expires_at timestamptz, lease_token uuid,
  checkpoint jsonb, progress real NOT NULL DEFAULT 0,
  last_error text, result jsonb,
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now());
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS lease_token uuid;
CREATE INDEX IF NOT EXISTS jobs_ready ON jobs(priority, id) WHERE state = 'queued';
CREATE TABLE IF NOT EXISTS job_events(id bigserial PRIMARY KEY, job_id bigint, at timestamptz DEFAULT clock_timestamp(),
                                      worker text, event text, detail jsonb);
"""

CLAIM = """
WITH cand AS (
  SELECT id FROM jobs WHERE state = 'queued' AND kind = %(kind)s AND run_after <= now()
  ORDER BY priority, id FOR UPDATE SKIP LOCKED LIMIT 1)
UPDATE jobs j SET state = 'running', locked_by = %(w)s, attempts = j.attempts + 1, updated_at = now(),
       lease_token = gen_random_uuid(),
       lease_expires_at = now() + make_interval(secs => (SELECT lease_seconds FROM job_kinds k WHERE k.kind = j.kind))
FROM cand WHERE j.id = cand.id
RETURNING j.id, j.kind, j.payload, j.attempts, j.checkpoint, j.lease_token
"""
# Per-kind concurrency: a worker must hold one of N session-level advisory locks ("slots") for the kind while it
# runs a job of that kind. Session locks vanish when the worker's connection dies, so a crashed worker never
# leaks a slot. The job row itself is claimed with FOR UPDATE SKIP LOCKED, so claimers never block each other.


class Retryable(Exception):
    pass


class Fatal(Exception):
    pass


class Queue:
    def __init__(self, dsn: str = DSN, worker: str | None = None):
        self.conn = psycopg.connect(dsn, autocommit=True)
        self.worker = worker or f"{socket.gethostname()}:{os.getpid()}"
        self.tokens = {}   # job_id -> lease token of the attempt this worker currently owns

    def init(self, kinds: dict[str, dict]):
        self.conn.execute(SCHEMA)
        for k, v in kinds.items():
            self.conn.execute("""INSERT INTO job_kinds(kind, max_concurrency, max_attempts, lease_seconds)
                                 VALUES (%s,%s,%s,%s) ON CONFLICT (kind) DO UPDATE SET max_concurrency = EXCLUDED.max_concurrency,
                                 max_attempts = EXCLUDED.max_attempts, lease_seconds = EXCLUDED.lease_seconds""",
                              (k, v.get("max_concurrency", 2), v.get("max_attempts", 5), v.get("lease_seconds", 30)))

    def event(self, job_id, event, **detail):
        self.conn.execute("INSERT INTO job_events(job_id, worker, event, detail) VALUES (%s,%s,%s,%s)",
                          (job_id, self.worker, event, Jsonb(detail)))

    def enqueue(self, kind, payload, key=None, priority=100) -> int | None:
        row = self.conn.execute("""INSERT INTO jobs(kind, payload, idempotency_key, priority) VALUES (%s,%s,%s,%s)
                                   ON CONFLICT (idempotency_key) DO NOTHING RETURNING id""",
                                (kind, Jsonb(payload), key, priority)).fetchone()
        return row[0] if row else None

    def claim(self):
        self.release_slot()
        kinds = self.conn.execute("""SELECT k.kind, k.max_concurrency FROM job_kinds k
                                     WHERE EXISTS (SELECT 1 FROM jobs j WHERE j.kind = k.kind AND j.state = 'queued'
                                                   AND j.run_after <= now()) ORDER BY k.kind""").fetchall()
        for kind, limit in kinds:
            for slot in range(limit):
                if not self.conn.execute("SELECT pg_try_advisory_lock(hashtext(%s), %s)", (kind, slot)).fetchone()[0]:
                    continue
                row = self.conn.execute(CLAIM, {"w": self.worker, "kind": kind}).fetchone()
                if row:
                    self.slot = (kind, slot)
                    self.tokens[row[0]] = row[5]          # attempt-specific lease token
                    row = row[:5]
                    self.event(row[0], "claimed", attempt=row[3], checkpoint=row[4], slot=slot)
                    return row
                self.conn.execute("SELECT pg_advisory_unlock(hashtext(%s), %s)", (kind, slot))
                break
        return None

    def release_slot(self):
        if getattr(self, "slot", None):
            self.conn.execute("SELECT pg_advisory_unlock(hashtext(%s), %s)", self.slot)
            self.slot = None

    # Every owner-side transition is conditional on the attempt-specific lease token: a stale worker whose lease was
    # reaped (and possibly re-claimed, even by a worker with the same name) cannot extend, complete, requeue or fail
    # the new attempt. Events are emitted only when the conditional update actually changed the row.
    def heartbeat(self, job_id, progress=None, checkpoint=None):
        """Extend the lease; persist progress and a resumable checkpoint. Returns False if the lease was lost."""
        r = self.conn.execute("""UPDATE jobs SET lease_expires_at = now() + make_interval(secs => (SELECT lease_seconds FROM job_kinds k WHERE k.kind = jobs.kind)),
                                 progress = coalesce(%s, progress), checkpoint = coalesce(%s, checkpoint), updated_at = now()
                                 WHERE id = %s AND state = 'running' AND lease_token = %s""",
                              (progress, Jsonb(checkpoint) if checkpoint is not None else None, job_id, self.tokens.get(job_id)))
        return r.rowcount == 1

    def complete(self, job_id, result) -> bool:
        r = self.conn.execute("""UPDATE jobs SET state='succeeded', result=%s, progress=1, locked_by=NULL, lease_expires_at=NULL,
                                 lease_token=NULL, updated_at=now() WHERE id=%s AND state='running' AND lease_token=%s""",
                              (Jsonb(result), job_id, self.tokens.pop(job_id, None)))
        if r.rowcount == 1:
            self.event(job_id, "succeeded")
            return True
        self.event(job_id, "stale_completion_ignored")
        return False

    def fail(self, job_id, err: str, retryable: bool, base_s=1.0, cap_s=60.0) -> bool:
        token = self.tokens.pop(job_id, None)
        row = self.conn.execute("""SELECT j.attempts, k.max_attempts FROM jobs j JOIN job_kinds k USING(kind)
                                   WHERE id=%s AND state='running' AND lease_token=%s""", (job_id, token)).fetchone()
        if row is None:
            self.event(job_id, "stale_failure_ignored", error=err)
            return False
        attempts, max_attempts = row
        if retryable and attempts < max_attempts:
            delay = min(cap_s, base_s * 2 ** (attempts - 1)) * (0.8 + 0.4 * random.random())  # full backoff with jitter
            r = self.conn.execute("""UPDATE jobs SET state='queued', run_after=now() + make_interval(secs => %s), last_error=%s,
                                     locked_by=NULL, lease_expires_at=NULL, lease_token=NULL, updated_at=now()
                                     WHERE id=%s AND state='running' AND lease_token=%s""", (delay, err, job_id, token))
            if r.rowcount == 1:
                self.event(job_id, "retry_scheduled", attempt=attempts, delay_s=round(delay, 2), error=err)
                return True
        else:
            state = "dead" if retryable else "failed"
            r = self.conn.execute("""UPDATE jobs SET state=%s, last_error=%s, locked_by=NULL, lease_expires_at=NULL, lease_token=NULL,
                                     updated_at=now() WHERE id=%s AND state='running' AND lease_token=%s""", (state, err, job_id, token))
            if r.rowcount == 1:
                self.event(job_id, state, attempt=attempts, error=err)
                return True
        self.event(job_id, "stale_failure_ignored", error=err)
        return False

    def reap(self) -> int:
        """Crash recovery: running jobs whose lease expired lose their lease token. The attempt was already counted at
        claim time, so a job whose attempts reached max_attempts goes to 'dead' instead of being requeued forever."""
        rows = self.conn.execute("""UPDATE jobs j SET
                                      state = CASE WHEN j.attempts >= k.max_attempts THEN 'dead' ELSE 'queued' END,
                                      locked_by=NULL, lease_expires_at=NULL, lease_token=NULL,
                                      last_error='lease expired (worker lost)', updated_at=now()
                                    FROM job_kinds k
                                    WHERE k.kind = j.kind AND j.state='running' AND j.lease_expires_at < now()
                                    RETURNING j.id, j.state""").fetchall()
        for jid, st in rows:
            self.event(jid, "lease_expired_dead" if st == "dead" else "lease_expired_requeued")
        return len(rows)

    def stats(self):
        return dict(self.conn.execute("SELECT state, count(*) FROM jobs GROUP BY state").fetchall())


def run_worker(handlers: dict, idle_exit_s: float = 3.0, poll_s: float = 0.2, worker: str | None = None):
    q = Queue(worker=worker)
    idle_since = time.monotonic()
    while True:
        q.reap()
        job = q.claim()
        if not job:
            if time.monotonic() - idle_since > idle_exit_s:
                return
            time.sleep(poll_s); continue
        idle_since = time.monotonic()
        jid, kind, payload, attempt, checkpoint = job
        try:
            result = handlers[kind](q, jid, payload, attempt, checkpoint)
            q.complete(jid, result)
        except Retryable as e:
            q.fail(jid, str(e), retryable=True)
        except Fatal as e:
            q.fail(jid, str(e), retryable=False)
        except Exception as e:  # unknown errors are retried; poison jobs end as 'dead' after max_attempts
            q.fail(jid, f"{type(e).__name__}: {e}", retryable=True)
