"""Re-check every judgment that was removed as not military, after a change to the filter.

Step 1 (once): the removal log is saved as state/excluded_before_recheck.jsonl, emptied, and the
addresses of the removed files are queued again. Step 2 (resumable): download in batches from the
open-data buckets, extract, filter; files that fail the filter again are removed and logged again.

    python scripts/recheck_removed.py            # start, or continue after an interruption
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from collect_judgments import PY, checkpoint, process, run, say   # noqa: E402

LOG = ROOT / "data" / "excluded_judgments.jsonl"
SAVED = ROOT / "state" / "excluded_before_recheck.jsonl"
BATCH = 6000


def queued(conn) -> dict:
    return dict(conn.execute("SELECT source, count(*) FROM urls WHERE kind='document' AND status='queued' "
                             "AND source IN ('sci','hc') GROUP BY 1").fetchall())


def main() -> int:
    conn = sqlite3.connect(ROOT / "state" / "crawl.sqlite", timeout=60)
    if not SAVED.exists():
        entries = [json.loads(l) for l in LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
        conn.execute("CREATE TEMP TABLE again (sha256 TEXT PRIMARY KEY, url TEXT)")     # one pass, not one scan per file
        conn.executemany("INSERT OR IGNORE INTO again VALUES (?, ?)", [(e["sha256"], e["source_url"]) for e in entries])
        conn.execute("CREATE INDEX temp.again_url ON again (url)")
        conn.execute("DELETE FROM files WHERE sha256 IN (SELECT sha256 FROM again)")
        conn.execute("UPDATE urls SET status='queued', etag=NULL, last_modified=NULL, attempts=0, next_attempt_at=NULL "
                     "WHERE kind='document' AND (sha256 IN (SELECT sha256 FROM again) OR url IN (SELECT url FROM again))")
        shutil.copy2(LOG, SAVED)                         # saved only once the queue is ready to be committed
        conn.commit()
        LOG.write_text("", encoding="utf-8")
        say(f"recheck: {len(entries)} removed judgments queued again")
    before = None
    while True:
        left = queued(conn)
        if not left or left == before or (ROOT / "state" / "collect.stop").exists():
            break                                        # nothing left, nothing moved (waiting on retries), or stop asked
        before = left
        for source in left:
            rc, out = run("crawler", "fetch", "--source", source, "--yes-download", "--limit", str(BATCH), "--workers", "8")
            if rc != 0:
                say(f"recheck: fetch {source} failed: {out[-300:]}")
                return 1
        stats = process("recheck")
        say(f"recheck: left {sum(queued(conn).values())}; relevant={stats.get('relevant')} "
            f"borderline={stats.get('borderline')} removed={stats.get('removed_as_not_military_total')}")
    run("pipeline", "ocr", "--langs", "eng")             # scans come back unread; their pages are in the OCR cache
    rc, out = run("pipeline", "all")
    say(f"recheck finished; pipeline all rc={rc}; " + " | ".join(l for l in out.splitlines() if l.startswith(("relevance:", "validate:")))[:400])
    checkpoint("re-check of removed judgments")
    return 0


if __name__ == "__main__":
    sys.exit(main())
