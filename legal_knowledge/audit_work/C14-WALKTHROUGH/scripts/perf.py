"""C14 walkthrough performance probe against a running B1 (read-only).

Measures, from a client on the same host: search latency (sequential and with 10 and 25 concurrent readers, each a
separate signed-in session), session check (one PostgreSQL round trip per request), document metadata, text pages,
pdf-meta, and 64 KiB protected range reads. Samples the service process (working set, CPU time) around each phase
when B1_PID is given. Usage:
  B1_URL=... B1_USER=... B1_PASSWORD=... [B1_PID=...] python perf.py out.json
"""
import concurrent.futures as cf
import http.cookiejar
import json
import os
import statistics
import subprocess
import sys
import time
import urllib.parse
import urllib.request

base = os.environ["B1_URL"].rstrip("/")
pid = os.environ.get("B1_PID")
Q = ["s.69 Army Act", "2013 INSC 408", "disability pension", "court martial", "summary of evidence", "AFT jurisdiction",
     "invalided out of service", "exact:\"Entitlement Rules\"", "desertion AND NOT pension", "Rule 22 Army Rules",
     "release medical board", "\"court martial\" NEAR/10 delay", "Civil Appeal No. 4949 of 2013",
     "writ petition armed forces tribunal", "field punishment", "attributable to military service",
     "sentence of dismissal", "section 302 Indian Penal Code", "Navy Act", "natural justice court of inquiry"]


def client():
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    op.open(urllib.request.Request(base + "/api/login", method="POST",
            data=json.dumps({"username": os.environ["B1_USER"], "password": os.environ["B1_PASSWORD"]}).encode(),
            headers={"Content-Type": "application/json", "Origin": base}))
    return op


def timed(op, url, headers=None):
    t = time.perf_counter()
    r = op.open(urllib.request.Request(base + url, headers=headers or {}))
    body = r.read()
    return (time.perf_counter() - t) * 1000, body


def stats(a):
    a = sorted(a)
    p = lambda q: round(a[max(0, int(round(q / 100 * len(a))) - 1)], 1)  # noqa: E731
    return {"n": len(a), "p50": p(50), "p95": p(95), "max": round(a[-1], 1), "mean": round(statistics.mean(a), 1)}


def proc():
    if not pid:
        return None
    ps = ("$p=Get-Process -Id %s; '{0}|{1}|{2}' -f $p.WorkingSet64,$p.TotalProcessorTime.TotalSeconds,$p.Threads.Count" % pid)
    ws, cpu, th = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout.strip().split("|")
    return {"working_set_mb": round(int(ws) / 2**20, 1), "cpu_s": round(float(cpu), 2), "threads": int(th)}


out = {"base": base, "host_note": "client and service on the same host (i7-10750H, 16 GB, Windows 11)", "phases": {}}
op = client()
out["process_idle"] = proc()

# warm-up (first query pays JIT and index page-in)
first, _ = timed(op, "/api/search?" + urllib.parse.urlencode({"q": Q[0]}))
out["phases"]["first_search_after_start_ms"] = round(first, 1)
for q in Q:
    timed(op, "/api/search?" + urllib.parse.urlencode({"q": q}))

seq = [timed(op, "/api/search?" + urllib.parse.urlencode({"q": q}))[0] for _ in range(5) for q in Q]
out["phases"]["search_sequential"] = stats(seq)
out["process_after_sequential"] = proc()

for n in (10, 25):
    ops = [client() for _ in range(n)]
    jobs = [(ops[i % n], q) for i, q in enumerate(Q * n)]
    t = time.perf_counter()
    with cf.ThreadPoolExecutor(n) as ex:
        lat = list(ex.map(lambda j: timed(j[0], "/api/search?" + urllib.parse.urlencode({"q": j[1]}))[0], jobs))
    wall = time.perf_counter() - t
    out["phases"][f"search_concurrent_{n}"] = {**stats(lat), "throughput_rps": round(len(lat) / wall, 1)}
    out[f"process_after_concurrent_{n}"] = proc()

out["phases"]["session_check_db_roundtrip"] = stats([timed(op, "/api/session")[0] for _ in range(50)])
docs = ["act-army-1950", "sc-2013-dharamvir-singh-2013insc408", "rules-army-rules-1954", "act-bnss-2023", "regs-regulations-for-the-navy-part-i"]
out["phases"]["document_metadata"] = stats([timed(op, f"/api/documents/{d}")[0] for d in docs for _ in range(5)])
out["phases"]["text_40_pages"] = stats([timed(op, f"/api/documents/{d}/text?from=1&to=40")[0] for d in docs for _ in range(3)])
meta_lat, range_lat = [], []
for d in docs:
    ms, body = timed(op, f"/api/v2/documents/{d}/pdf-meta")
    meta_lat.append(ms)
    m = json.loads(body)
    sha = m["copy_sha256"]
    for i in range(8):
        start = min(i * 65536, max(0, m["length"] - 65536))
        range_lat.append(timed(op, f"/api/v2/documents/{d}/copies/{sha}/range", {"Range": f"bytes={start}-{start + 65535}"})[0])
out["phases"]["pdf_meta"] = stats(meta_lat)
out["phases"]["pdf_range_64k"] = stats(range_lat)
out["process_end"] = proc()
json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), indent=1)
print(json.dumps(out, indent=1))
