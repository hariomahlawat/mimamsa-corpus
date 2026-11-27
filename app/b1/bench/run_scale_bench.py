"""C14 S4 scale benchmark: one service run per (site, GC mode) on a fresh database; numbers only.

  python -I run_scale_bench.py --site <importer site> --label 1000 --gc server|server-nodatas|workstation \
      --dll <Mimamsa.Web.dll> --register <file> --port 5443 --out <result.json> [--cycles 5]
Needs PGPASSWORD for the superuser (mimamsa_su) and MIMAMSA_APP_PW for the app role in the environment; neither is
printed. Creates/drops database c14s4_bench. Starts the service with Mimamsa:Diagnostics:Enabled=true (numbers-only
memory endpoint) and NOT in test mode; a benchmark account is created through the documented --add-user CLI.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import http.cookiejar
import json
import os
import re
import secrets
import statistics
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

PSQL = r"C:\Program Files\PostgreSQL\18\bin\psql.exe"
PGDATA = Path(r"E:\Mimamsa-Data\pg\data")
Q = ["s.69 Army Act", "2013 INSC 408", "disability pension", "court martial", "summary of evidence", "AFT jurisdiction",
     "invalided out of service", "exact:\"Entitlement Rules\"", "desertion AND NOT pension", "Rule 22 Army Rules",
     "release medical board", "\"court martial\" NEAR/10 delay", "Civil Appeal No. 4949 of 2013",
     "writ petition armed forces tribunal", "field punishment", "attributable to military service",
     "sentence of dismissal", "section 302 Indian Penal Code", "Navy Act", "natural justice court of inquiry"]
GC = {"server": {}, "server-nodatas": {"DOTNET_GCDynamicAdaptationMode": "0"}, "workstation": {"DOTNET_gcServer": "0"}}


def psql(sql, db="postgres"):
    subprocess.run([PSQL, "-h", "127.0.0.1", "-p", "55499", "-U", "mimamsa_su", "-d", db, "-q", "-c", sql], check=True,
                   capture_output=True)


def ps(cmd):
    return subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True).stdout.strip()


def pg_memory_mb():
    pid = int((PGDATA / "postmaster.pid").read_text().split()[0])
    out = ps(f"$k=Get-CimInstance Win32_Process -Filter 'ParentProcessId={pid} or ProcessId={pid}'; "
             f"'{{0}}|{{1}}' -f (($k | % {{ (Get-Process -Id $_.ProcessId -EA SilentlyContinue).WorkingSet64 }} | Measure-Object -Sum).Sum), "
             f"(($k | % {{ (Get-Process -Id $_.ProcessId -EA SilentlyContinue).PrivateMemorySize64 }} | Measure-Object -Sum).Sum)")
    ws, pv = out.split("|")
    return {"pg_working_set_mb": round(int(ws) / 2**20, 1), "pg_private_mb": round(int(pv) / 2**20, 1)}


def stats(a):
    a = sorted(a)
    p = lambda q: round(a[max(0, int(round(q / 100 * len(a))) - 1)], 1)  # noqa: E731
    return {"n": len(a), "p50": p(50), "p95": p(95), "max": round(a[-1], 1), "mean": round(statistics.mean(a), 1)}


def main():
    ap = argparse.ArgumentParser()
    for k in ("--site", "--label", "--gc", "--dll", "--register", "--out"):
        ap.add_argument(k, required=True)
    ap.add_argument("--port", type=int, default=5443)
    ap.add_argument("--cycles", type=int, default=5)
    a = ap.parse_args()
    base = f"http://127.0.0.1:{a.port}"
    app_pw = os.environ["MIMAMSA_APP_PW"]
    dsn = f"Host=127.0.0.1;Port=55499;Username=mimamsa;Password={app_pw};Database=c14s4_bench;Maximum Pool Size=10"
    psql("DROP DATABASE IF EXISTS c14s4_bench;")
    psql("CREATE DATABASE c14s4_bench OWNER mimamsa;")
    user_pw = secrets.token_urlsafe(18)
    env = dict(os.environ, Mimamsa__Db=dsn, MIMAMSA_NEW_PASSWORD=user_pw)
    subprocess.run(["dotnet", a.dll, "--add-user", "bench", "User"], env=env, check=True, capture_output=True)
    env = dict(os.environ, ASPNETCORE_URLS=base, Mimamsa__Site=a.site, Mimamsa__Db=dsn, Mimamsa__RestrictedRegister=a.register,
               Mimamsa__Diagnostics__Enabled="true", **GC[a.gc])
    env.pop("MIMAMSA_NEW_PASSWORD", None)
    log = Path(a.out).with_suffix(".service.log")
    pg_before = pg_memory_mb()
    t0 = time.perf_counter()
    proc = subprocess.Popen(["dotnet", a.dll], cwd=str(Path(a.dll).parent), env=env, stdout=open(log, "w", encoding="utf-8"), stderr=subprocess.STDOUT)
    res = {"label": a.label, "gc_mode": a.gc, "site": a.site}
    try:
        while True:
            try:
                urllib.request.urlopen(base + "/health", timeout=2)
                break
            except Exception:
                if proc.poll() is not None:
                    raise RuntimeError("service exited; see " + str(log))
                if time.perf_counter() - t0 > 1800:
                    raise RuntimeError("start-up timeout")
                time.sleep(0.25)
        res["startup_to_healthy_s"] = round(time.perf_counter() - t0, 2)
        text = log.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"generation load and re-hash (\d+) ms, index build (\d+) ms, hybrid (\d+) ms", text)
        if m:
            res["startup_phases_ms"] = {"load_and_rehash": int(m[1]), "index_build": int(m[2]), "hybrid": int(m[3])}
        m = re.search(r"(\d+) documents, (\d+) passages indexed", text)
        if m:
            res["documents"], res["passages"] = int(m[1]), int(m[2])

        def client():
            op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
            op.open(urllib.request.Request(base + "/api/login", method="POST", data=json.dumps({"username": "bench", "password": user_pw}).encode(),
                                           headers={"Content-Type": "application/json", "Origin": base}))
            return op

        def timed(op, url, headers=None):
            t = time.perf_counter()
            op.open(urllib.request.Request(base + url, headers=headers or {})).read()
            return (time.perf_counter() - t) * 1000

        diag = lambda gc=False: json.loads(urllib.request.urlopen(base + "/api/diag/memory" + ("?gc=1" if gc else "")).read())  # noqa: E731
        res["memory_after_start"] = diag()
        res["pg_memory_before_start"] = pg_before
        res["pg_memory_after_start"] = pg_memory_mb()
        op = client()
        res["first_search_ms"] = round(timed(op, "/api/search?" + urllib.parse.urlencode({"q": Q[0]})), 1)
        for q in Q:
            timed(op, "/api/search?" + urllib.parse.urlencode({"q": q}))
        res["search_1"] = stats([timed(op, "/api/search?" + urllib.parse.urlencode({"q": q})) for _ in range(3) for q in Q])
        clients = {n: [client() for _ in range(n)] for n in (10, 25)}
        for n in (10, 25):
            jobs = [(clients[n][i % n], q) for i, q in enumerate(Q * (n if n == 10 else 10))]
            t = time.perf_counter()
            with cf.ThreadPoolExecutor(n) as ex:
                lat = list(ex.map(lambda j: timed(j[0], "/api/search?" + urllib.parse.urlencode({"q": j[1]})), jobs))
            res[f"search_{n}"] = {**stats(lat), "throughput_rps": round(len(lat) / (time.perf_counter() - t), 1)}
        res["memory_after_load"] = diag()
        res["pg_memory_after_load"] = pg_memory_mb()
        # PDF ranges on a few documents
        sr = json.loads(op.open(base + "/api/search?q=army").read())
        docs = list(dict.fromkeys(p["doc_id"] for p in sr["passages"]))[:5]
        rl = []
        for d in docs:
            meta = json.loads(op.open(base + f"/api/v2/documents/{urllib.parse.quote(d)}/pdf-meta").read())
            for i in range(6):
                s = min(i * 65536, max(0, meta["length"] - 65536))
                rl.append(timed(op, f"/api/v2/documents/{urllib.parse.quote(d)}/copies/{meta['copy_sha256']}/range", {"Range": f"bytes={s}-{s + 65535}"}))
        res["pdf_range_64k"] = stats(rl)
        # retention vs leak: repeated 25-reader cycles, sampled without and with a forced compacting GC
        cyc = []
        for c in range(a.cycles):
            jobs = [(clients[25][i % 25], q) for i, q in enumerate(Q * 10)]
            with cf.ThreadPoolExecutor(25) as ex:
                list(ex.map(lambda j: timed(j[0], "/api/search?" + urllib.parse.urlencode({"q": j[1]})), jobs))
            before, after = diag(), diag(gc=True)
            cyc.append({"cycle": c + 1, "working_set_mb": before["working_set_mb"], "gc_heap_mb": before["gc_heap_size_mb"],
                        "committed_mb": before["gc_committed_mb"], "after_forced_gc_managed_mb": after["managed_heap_mb"],
                        "after_forced_gc_working_set_mb": after["working_set_mb"], "after_forced_gc_committed_mb": after["gc_committed_mb"]})
        res["leak_cycles"] = cyc
        res["memory_end"] = diag()
    finally:
        proc.kill()
        proc.wait()
        time.sleep(1)
        psql("DROP DATABASE IF EXISTS c14s4_bench WITH (FORCE);")
    Path(a.out).write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: res[k] for k in res if k in ("label", "gc_mode", "startup_to_healthy_s", "startup_phases_ms", "passages", "search_1", "search_10", "search_25")}))


if __name__ == "__main__":
    main()
