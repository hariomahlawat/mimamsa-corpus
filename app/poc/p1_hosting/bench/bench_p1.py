"""P1 hosting benchmark orchestrator (Linux). Starts each server config, measures cold start, idle and
under-load RSS (whole process tree), and runs autocannon at several concurrencies per endpoint.

python bench_p1.py <config.json> <out.json>
config: {"autocannon": "...", "duration": 15, "warmup": 5, "concurrency": [1,10,50],
         "endpoints": {"search": "/api/search?q=...", ...}, "servers": [{"name","cmd","cwd","env","port"}]}
"""
import json, os, subprocess, sys, threading, time, urllib.request
from pathlib import Path

import psutil

cfg = json.loads(Path(sys.argv[1]).read_text())
out_path = Path(sys.argv[2])
SRV_PIN = cfg.get("server_cpus")      # e.g. "0-2": servers + PostgreSQL clients pinned away from the load generator
GEN_PIN = cfg.get("loadgen_cpus")     # e.g. "3"
RUNS = int(cfg.get("runs", 1))
def pin(cmd, cpus): return (["taskset", "-c", cpus] + cmd) if cpus else cmd
TOKEN = {"Authorization": "Bearer dev-token"}


def tree_rss_mb(p):
    try:
        procs = [p] + p.children(recursive=True)
        return sum(x.memory_info().rss for x in procs if x.is_running()) / 2**20
    except psutil.Error:
        return None


def get(url, headers=None, timeout=2):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        r.read(); return r.status


results = {"pinning": {"server_cpus": SRV_PIN, "loadgen_cpus": GEN_PIN}, "runs": RUNS, "host": {"cpus": os.cpu_count(), "mem_gb": round(psutil.virtual_memory().total / 2**30, 1),
                    "cpu_model": next((l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name")), None)},
           "config": cfg, "servers": {}}
for srv in cfg["servers"]:
    base = f"http://127.0.0.1:{srv['port']}"
    env = dict(os.environ, **srv.get("env", {}))
    t0 = time.perf_counter()
    proc = subprocess.Popen(pin(srv["cmd"], SRV_PIN), cwd=srv["cwd"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ps = psutil.Process(proc.pid)
    cold = None
    while time.perf_counter() - t0 < 60:
        try:
            if get(base + "/health", timeout=0.5) == 200:
                cold = time.perf_counter() - t0; break
        except Exception:
            time.sleep(0.02)
    t1 = time.perf_counter(); get(base + cfg["endpoints"]["search"], TOKEN, timeout=30); first_search = time.perf_counter() - t1
    time.sleep(2)
    r = {"cold_start_to_health_s": round(cold, 3) if cold else None, "first_search_request_s": round(first_search, 3),
         "idle_rss_mb": round(tree_rss_mb(ps), 1), "processes": 1 + len(ps.children(recursive=True)), "runs": []}
    eps = dict(cfg["endpoints"]); eps.update(srv.get("extra_endpoints", {}))
    for run_no in range(RUNS):
      for ep, spec in eps.items():
        path, extra_h = (spec, []) if isinstance(spec, str) else (spec["path"], spec.get("headers", []))
        hdrs = []
        for h in (extra_h or ["Authorization=Bearer dev-token"]): hdrs += ["-H", h]
        for c in cfg["concurrency"]:
            args = pin([cfg["autocannon"], "-j", "-c", str(c), "-d", str(cfg["duration"])] + hdrs + [base + path], GEN_PIN)
            subprocess.run(pin([cfg["autocannon"], "-c", str(c), "-d", str(cfg["warmup"])] + hdrs + [base + path], GEN_PIN),
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            peak = [0.0]; stop = threading.Event()
            def sample():
                while not stop.is_set():
                    v = tree_rss_mb(ps); peak[0] = max(peak[0], v or 0); time.sleep(0.25)
            th = threading.Thread(target=sample); th.start()
            la = os.getloadavg()
            j = json.loads(subprocess.run(args, capture_output=True, text=True).stdout)
            stop.set(); th.join()
            r["runs"].append({"run": run_no, "endpoint": ep, "concurrency": c, "rps_mean": j["requests"]["average"],
                              "lat_p50_ms": j["latency"]["p50"], "lat_p90_ms": j["latency"]["p90"], "lat_p99_ms": j["latency"]["p99"],
                              "lat_max_ms": j["latency"]["max"], "non2xx": j["non2xx"], "errors": j["errors"], "timeouts": j["timeouts"],
                              "throughput_MBps": round(j["throughput"]["average"] / 2**20, 2), "peak_rss_mb": round(peak[0], 1),
                              "loadavg_1m_at_start": round(la[0], 2)})
            print(srv["name"], ep, c, r["runs"][-1]["rps_mean"], r["runs"][-1]["lat_p50_ms"], r["runs"][-1]["lat_p99_ms"], flush=True)
    for ch in ps.children(recursive=True):
        ch.terminate()
    proc.terminate(); proc.wait(10)
    results["servers"][srv["name"]] = r
    time.sleep(2)
out_path.write_text(json.dumps(results, indent=1))
