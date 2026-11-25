"""P5 demo: idempotency, retries/backoff, crash recovery (kill -9 mid-job), resumable checkpoints, progress,
per-kind concurrency limits and sandboxed untrusted parsing. Writes an evidence JSON.

python demo.py run <pdf_dir> <out.json>
python demo.py worker <name>            (internal: a worker process)
"""
import glob, json, os, signal, subprocess, sys, threading, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jobqueue import Queue, Retryable, Fatal, run_worker  # noqa: E402
from sandbox import run_sandboxed  # noqa: E402

KINDS = {"parse_pdf": dict(max_concurrency=2, max_attempts=3, lease_seconds=30),
         "flaky": dict(max_concurrency=2, max_attempts=4, lease_seconds=10),
         "long_index": dict(max_concurrency=1, max_attempts=5, lease_seconds=4),
         "ocr": dict(max_concurrency=1, max_attempts=3, lease_seconds=10)}


def h_parse(q, jid, p, attempt, ckpt):
    r = run_sandboxed(p["path"], timeout_s=p.get("timeout_s", 20), mem_mb=p.get("mem_mb", 768), mode=p.get("mode", "parse"))
    if r.get("timeout"):
        raise Fatal("sandbox timeout")                       # hostile/hanging input: do not retry
    if r["returncode"] != 0:
        raise Fatal(f"sandbox failed rc={r['returncode']} {r.get('stderr_tail', '')[-80:]!r}")
    # idempotent output: upsert keyed by input sha, so a re-run after a crash cannot duplicate results
    q.conn.execute("""INSERT INTO parse_results(input_key, pages, sandbox) VALUES (%s,%s,%s)
                      ON CONFLICT (input_key) DO UPDATE SET pages = EXCLUDED.pages, runs = parse_results.runs + 1""",
                   (p["key"], r["result"]["pages"], json.dumps(r["result"]["sandbox"])))
    return {"pages": r["result"]["pages"], "sandbox": r["result"]["sandbox"]}


def h_flaky(q, jid, p, attempt, ckpt):
    if attempt <= p["fail_times"]:
        raise Retryable(f"transient failure on attempt {attempt}")
    return {"ok_on_attempt": attempt}


def h_long(q, jid, p, attempt, ckpt):
    start = (ckpt or {}).get("next_step", 0)
    q.event(jid, "resume_from", step=start, attempt=attempt)
    for step in range(start, p["steps"]):
        time.sleep(p["step_s"])                               # one unit of work (e.g. 500 chunks embedded)
        if not q.heartbeat(jid, progress=(step + 1) / p["steps"], checkpoint={"next_step": step + 1}):
            raise Retryable("lease lost")
        q.event(jid, "step_done", step=step)
    return {"steps": p["steps"], "started_at_step": start}


def h_ocr(q, jid, p, attempt, ckpt):
    q.event(jid, "ocr_start")
    time.sleep(p["s"])
    q.event(jid, "ocr_end")
    return {}


HANDLERS = {"parse_pdf": h_parse, "flaky": h_flaky, "long_index": h_long, "ocr": h_ocr}


def spawn_worker(name, idle=12.0):
    return subprocess.Popen([sys.executable, __file__, "worker", name, str(idle)])


def main():
    if sys.argv[1] == "worker":
        run_worker(HANDLERS, idle_exit_s=float(sys.argv[3]), worker=sys.argv[2])
        return
    pdf_dir, out = Path(sys.argv[2]), Path(sys.argv[3])
    q = Queue(worker="demo-controller")
    q.conn.execute("DROP TABLE IF EXISTS jobs, job_events, job_kinds, parse_results CASCADE")
    q.init(KINDS)
    q.conn.execute("CREATE TABLE parse_results(input_key text PRIMARY KEY, pages int, sandbox jsonb, runs int DEFAULT 1)")
    ev = {}

    # 1. idempotent enqueue: 12 PDFs, each enqueued twice with the same key
    pdfs = sorted(glob.glob(str(pdf_dir / "*.pdf")), key=os.path.getsize)[:12]
    ids = [q.enqueue("parse_pdf", {"path": f, "key": Path(f).stem}, key=f"parse:{Path(f).stem}") for f in pdfs * 2]
    ev["idempotent_enqueue"] = {"attempted": len(ids), "created": sum(i is not None for i in ids)}
    # hostile inputs
    q.enqueue("parse_pdf", {"path": pdfs[0], "key": "bomb", "mode": "memory_bomb", "mem_mb": 512}, key="parse:bomb")
    q.enqueue("parse_pdf", {"path": pdfs[0], "key": "hang", "mode": "hang", "timeout_s": 3}, key="parse:hang")
    # 2. retries with backoff
    q.enqueue("flaky", {"fail_times": 2}, key="flaky:2")
    q.enqueue("flaky", {"fail_times": 9}, key="flaky:poison")      # exceeds max_attempts -> dead
    # 3. long resumable job
    q.enqueue("long_index", {"steps": 10, "step_s": 0.6}, key="long:1", priority=1)
    # 4. concurrency-limited kind
    for i in range(4):
        q.enqueue("ocr", {"s": 0.8}, key=f"ocr:{i}")

    # sample running counts per kind to prove limits hold
    samples, stop = [], threading.Event()
    def sampler():
        sq = Queue(worker="sampler")
        while not stop.is_set():
            rows = dict(sq.conn.execute("SELECT kind, count(*) FROM jobs WHERE state='running' GROUP BY kind").fetchall())
            prog = sq.conn.execute("SELECT progress FROM jobs WHERE idempotency_key='long:1'").fetchone()[0]
            samples.append({"t": round(time.time(), 2), **rows, "long_progress": prog}); time.sleep(0.1)
    th = threading.Thread(target=sampler); th.start()

    w1, w2 = spawn_worker("w1"), spawn_worker("w2")
    # kill the worker that holds the long job once it has done ~4 steps
    victim = None
    t0 = time.time()
    while time.time() - t0 < 60:
        row = q.conn.execute("SELECT locked_by, progress FROM jobs WHERE idempotency_key='long:1'").fetchone()
        if row[0] and row[1] >= 0.4:
            victim = row[0]; break
        time.sleep(0.05)
    proc = {"w1": w1, "w2": w2}[victim]
    proc.send_signal(signal.SIGKILL); proc.wait()
    killed_at = q.conn.execute("SELECT progress, checkpoint FROM jobs WHERE idempotency_key='long:1'").fetchone()
    ev["crash"] = {"killed_worker": victim, "signal": "SIGKILL", "progress_at_kill": killed_at[0], "checkpoint_at_kill": killed_at[1]}
    w3 = spawn_worker("w3")
    for w in (w1, w2, w3):
        w.wait(timeout=180)
    stop.set(); th.join()

    jobs = q.conn.execute("""SELECT idempotency_key, kind, state, attempts, last_error, result FROM jobs ORDER BY id""").fetchall()
    ev["jobs"] = [dict(key=k, kind=kd, state=s, attempts=a, last_error=(e or "")[:120], result=r) for k, kd, s, a, e, r in jobs]
    events = q.conn.execute("""SELECT j.idempotency_key, e.worker, e.event, e.detail, e.at FROM job_events e JOIN jobs j ON j.id=e.job_id
                               WHERE j.idempotency_key IN ('long:1','flaky:2','flaky:poison') ORDER BY e.id""").fetchall()
    ev["events_long_and_flaky"] = [dict(key=k, worker=w, event=x, detail=d, at=str(t)) for k, w, x, d, t in events]
    ev["max_running_ocr"] = max((s.get("ocr", 0) for s in samples), default=0)
    ev["max_running_parse_pdf"] = max((s.get("parse_pdf", 0) for s in samples), default=0)
    ev["max_running_long_index"] = max((s.get("long_index", 0) for s in samples), default=0)
    ev["parse_results_rows"] = q.conn.execute("SELECT count(*), max(runs) FROM parse_results").fetchone()
    ev["final_states"] = q.stats()
    ev["progress_samples_long"] = [s["long_progress"] for s in samples[::5]]
    out.write_text(json.dumps(ev, indent=1, default=str))
    print(json.dumps({k: ev[k] for k in ("idempotent_enqueue", "crash", "max_running_ocr", "max_running_parse_pdf", "parse_results_rows", "final_states")}, default=str))


if __name__ == "__main__":
    main()
