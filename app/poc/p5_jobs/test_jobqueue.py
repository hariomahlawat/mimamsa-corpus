"""Lease-safety tests for the PostgreSQL job queue (needs a scratch database; POC_DSN selects it).

POC_DSN="host=127.0.0.1 port=55432 user=poc dbname=poc_jobs_test" python -m unittest -v test_jobqueue
"""
import time
import unittest

from jobqueue import Queue

KINDS = {"k": dict(max_concurrency=4, max_attempts=2, lease_seconds=1)}


class LeaseSafety(unittest.TestCase):
    def setUp(self):
        self.admin = Queue(worker="admin")
        self.admin.conn.execute("DROP TABLE IF EXISTS jobs, job_events, job_kinds CASCADE")
        self.admin.init(KINDS)

    def state(self, jid):
        return self.admin.conn.execute("SELECT state, attempts, locked_by, result FROM jobs WHERE id=%s", (jid,)).fetchone()

    def stall_and_reclaim(self, a, b):
        """Worker a claims, stalls past its lease, the reaper requeues, worker b claims the new attempt."""
        jid = self.admin.enqueue("k", {"x": 1}, key=f"j{time.time_ns()}")
        self.assertEqual(a.claim()[0], jid)
        time.sleep(1.3)                                   # lease (1 s) expires while a is stalled
        self.assertEqual(b.reap(), 1)
        a.release_slot()
        row = b.claim()
        self.assertEqual(row[0], jid)
        return jid

    def test_stale_retryable_failure_cannot_requeue_new_owner(self):
        a, b = Queue(worker="w-a"), Queue(worker="w-b")
        jid = self.stall_and_reclaim(a, b)
        self.assertFalse(a.fail(jid, "late transient error", retryable=True))      # stale owner resumes
        st, attempts, locked_by, _ = self.state(jid)
        self.assertEqual((st, locked_by), ("running", "w-b"))                     # b keeps its lease
        self.assertTrue(b.heartbeat(jid))
        self.assertTrue(b.complete(jid, {"ok": True}))
        self.assertEqual(self.state(jid)[0], "succeeded")
        ev = [e for (e,) in self.admin.conn.execute("SELECT event FROM job_events WHERE job_id=%s ORDER BY id", (jid,)).fetchall()]
        self.assertIn("stale_failure_ignored", ev)
        self.assertNotIn("retry_scheduled", ev)

    def test_stale_terminal_failure_cannot_overwrite_later_success(self):
        a, b = Queue(worker="w-a"), Queue(worker="w-b")
        jid = self.stall_and_reclaim(a, b)
        self.assertTrue(b.complete(jid, {"ok": True}))
        self.assertFalse(a.fail(jid, "late fatal error", retryable=False))
        st, _, _, result = self.state(jid)
        self.assertEqual(st, "succeeded"); self.assertEqual(result, {"ok": True})

    def test_same_worker_name_still_fenced_by_attempt_token(self):
        a, a2 = Queue(worker="same"), Queue(worker="same")       # e.g. a restarted process reusing its name
        jid = self.stall_and_reclaim(a, a2)
        self.assertFalse(a.complete(jid, {"stale": True}))
        self.assertFalse(a.heartbeat(jid))
        self.assertEqual(self.state(jid)[0], "running")
        self.assertTrue(a2.complete(jid, {"fresh": True}))
        self.assertEqual(self.state(jid)[3], {"fresh": True})

    def test_reaper_enforces_max_attempts(self):
        w = Queue(worker="w-poison")
        jid = self.admin.enqueue("k", {"poison": True}, key="poison")
        for attempt in (1, 2):                              # max_attempts = 2: each attempt "crashes" (lease expires)
            row = w.claim(); self.assertEqual((row[0], row[3]), (jid, attempt))
            time.sleep(1.3); w.release_slot(); w.reap()
        st, attempts, _, _ = self.state(jid)
        self.assertEqual((st, attempts), ("dead", 2))
        self.assertIsNone(w.claim())                        # never claimed again


if __name__ == "__main__":
    unittest.main()
