"""C16 (PR #80 connection-exhaustion investigation): 10 concurrent clients sign in as the seeded test reader and call
   the search API for SECS seconds, either keeping one HTTP connection per client ("keepalive") or opening a new one per
   request ("close"). Prints counts, latency percentiles and a status histogram (numbers only).

  python -I app/b1/tests/b1server.py --site <site> --db "<dsn; e.g. Maximum Pool Size=8>" --port 5872 -- \
      python -I app/b1/bench/pool_probe.py keepalive|close [SECS]
"""
import http.client, json, os, statistics, sys, threading, time, urllib.parse
U = urllib.parse.urlparse(os.environ["B1_URL"]); HOST, PORT = U.hostname, U.port
MODE = sys.argv[1]; SECS = float(sys.argv[2]) if len(sys.argv) > 2 else 30
Q = ["court martial", "disability pension", "s.69 Army Act", "summary of evidence", "Dharamvir Singh", "invalided out of service"]
def login():
    c = http.client.HTTPConnection(HOST, PORT, timeout=60)
    c.request("POST", "/api/login", json.dumps({"username": "reader", "password": "reader-password-1"}),
              {"Content-Type": "application/json", "Origin": f"http://{HOST}:{PORT}"})
    r = c.getresponse(); r.read()
    ck = "; ".join(h.split(";")[0] for k, h in r.getheaders() if k.lower() == "set-cookie"); c.close()
    return ck
lat, errs, lock = [], [], threading.Lock()
status = {}
def worker(i, stop):
    ck = login(); conn = None
    while not stop.is_set():
        q = urllib.parse.quote(Q[i % len(Q)])
        t = time.perf_counter()
        try:
            if MODE == "close" or conn is None: conn = http.client.HTTPConnection(HOST, PORT, timeout=60)
            conn.request("GET", f"/api/search?q={q}", headers={"Cookie": ck, **({"Connection": "close"} if MODE == "close" else {})})
            r = conn.getresponse(); r.read()
            if MODE == "close": conn.close(); conn = None
            ok = r.status == 200; st = r.status
        except Exception as e:
            ok = False; conn = None; st = type(e).__name__
        with lock:
            status[st] = status.get(st, 0) + 1
            (lat if ok else errs).append((time.perf_counter() - t) * 1000)
        i += 1
stop = threading.Event(); ts = [threading.Thread(target=worker, args=(k, stop)) for k in range(10)]
t0 = time.time(); [t.start() for t in ts]; time.sleep(SECS); stop.set(); [t.join(120) for t in ts]
lat.sort()
p = lambda f: round(lat[min(len(lat) - 1, int(f * len(lat)))], 1) if lat else None
print(json.dumps({"mode": MODE, "seconds": SECS, "ok": len(lat), "errors": len(errs), "qps": round(len(lat) / (time.time() - t0), 1),
                  "p50_ms": p(.5), "p95_ms": p(.95), "max_ms": round(lat[-1], 1) if lat else None, "error_max_ms": round(max(errs), 1) if errs else None, "status": {str(k): v for k, v in status.items()}}))
