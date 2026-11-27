"""C16 WP04: HTTP parity and latency of the memory and disk text stores, through the real service.

  python -I text_store_http.py --site <importer site> --db-mem "<dsn>" --db-disk "<dsn>" --text-dir <dir> --out <result.json>
      [--port-mem 5660] [--port-disk 5661] [--dll <Mimamsa.Web.dll>] [--docs 0 (all)] [--engine memory|disk]

Starts two disposable TEST-mode services on the same site (one per text store, each on its own database), then:
  * parity: every document's metadata, every document-text window, sections, page citations, the search API for the
    benchmark queries, every Commander domain and the graph neighbourhood of every held statute and a sample of
    judgments are fetched from both and compared after removing timing fields;
  * withdrawal: one judgment is withdrawn on both; its text, citation and search hits must disappear on both;
  * latency: the document-text API (first window of each document; cold, warm and 10 concurrent readers) and the
    search API at 10 concurrent readers;
  * memory and start-up: /api/diag/memory (after a forced GC) and the service's own start-up phase log line.
Numbers and hashes only: no document text is written to the result.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import http.cookiejar
import json
import os
import re
import statistics
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tests"))
import b1server  # noqa: E402

Q = ["s.69 Army Act", "2013 INSC 408", "disability pension", "court martial", "summary of evidence", "AFT jurisdiction",
     "invalided out of service", "exact:\"Entitlement Rules\"", "desertion AND NOT pension", "Rule 22 Army Rules",
     "release medical board", "\"court martial\" NEAR/10 delay", "Civil Appeal No. 4949 of 2013",
     "writ petition armed forces tribunal", "field punishment", "attributable to military service",
     "sentence of dismissal", "section 302 Indian Penal Code", "Navy Act", "natural justice court of inquiry",
     "Dharamvir Singh", "section 302 IPC", "court marshal", "\"summary of evidence\"", "pension*", "title:army"]
VOLATILE = {"ms", "elapsed_ms", "took_ms"}


class Client:
    def __init__(self, base):
        self.base = base
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.csrf = None

    def call(self, path, body=None):
        req = urllib.request.Request(self.base + path, data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json", **({"X-CSRF-Token": self.csrf} if self.csrf else {})},
                                     method="GET" if body is None else "POST")
        try:
            with self.op.open(req, timeout=120) as r:
                return r.status, json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                return e.code, json.loads(raw or b"null")
            except ValueError:
                return e.code, None

    def login(self, user):
        st, s = self.call("/api/login", {"username": user, "password": f"{user}-password-1"})
        assert st == 200, (st, s)
        self.csrf = s["csrf"]


def strip(x):
    if isinstance(x, dict):
        return {k: strip(v) for k, v in x.items() if k not in VOLATILE}
    if isinstance(x, list):
        return [strip(v) for v in x]
    return x


def canon(st, body):
    return json.dumps([st, strip(body)], sort_keys=True, ensure_ascii=False)


def stats(a):
    a = sorted(a)
    if not a:
        return None
    p = lambda q: round(a[max(0, -(-len(a) * q // 100) - 1)], 2)  # noqa: E731
    return {"n": len(a), "p50": p(50), "p95": p(95), "max": round(a[-1], 2), "mean": round(statistics.fmean(a), 2)}


def timed(c, path):
    t = time.perf_counter()
    st, body = c.call(path)
    return (time.perf_counter() - t) * 1000, st, body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", required=True)
    ap.add_argument("--db-mem", required=True)
    ap.add_argument("--db-disk", required=True)
    ap.add_argument("--text-dir", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--port-mem", type=int, default=5660)
    ap.add_argument("--port-disk", type=int, default=5661)
    ap.add_argument("--dll", type=Path, default=b1server.DEFAULT_DLL)
    ap.add_argument("--docs", type=int, default=0, help="documents compared (0 = all)")
    ap.add_argument("--engine", default="memory")
    a = ap.parse_args()
    site = Path(a.site)
    gid = (site / "ACTIVE").read_text().strip()
    doc_ids = [json.loads(l)["doc_id"] for l in (site / "generations" / gid / "records" / "documents.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    if a.docs:
        step = max(1, len(doc_ids) // a.docs)
        doc_ids = doc_ids[::step][: a.docs]
    logs = a.out.parent
    procs = {}
    base_env = dict(os.environ)
    try:
        for name, port, db in (("memory", a.port_mem, a.db_mem), ("disk", a.port_disk, a.db_disk)):
            os.environ.clear(); os.environ.update(base_env)
            for k in [k for k in os.environ if k.startswith("Mimamsa__Text__")]:
                del os.environ[k]
            os.environ["Mimamsa__Diagnostics__Enabled"] = "true"
            os.environ["Mimamsa__Search__Engine"] = a.engine
            if a.engine == "disk":
                os.environ["Mimamsa__Search__IndexDir"] = str(Path(a.text_dir).parent / f"index-http-{name}")
            if name == "disk":
                os.environ["Mimamsa__Text__Store"] = "disk"
                os.environ["Mimamsa__Text__Dir"] = a.text_dir
            t = time.perf_counter()
            procs[name] = (b1server.start(str(site), db, port, a.dll, logs / f"http-{name}.log"), round(time.perf_counter() - t, 1))
        os.environ.clear(); os.environ.update(base_env)
        cl = {n: Client(f"http://127.0.0.1:{p}") for n, p in (("memory", a.port_mem), ("disk", a.port_disk))}
        ad = {n: Client(f"http://127.0.0.1:{p}") for n, p in (("memory", a.port_mem), ("disk", a.port_disk))}
        for c in cl.values():
            c.login("reader")
        for c in ad.values():
            c.login("admin")

        # ---------------- latency: document-text API (first window), cold then warm, then 10 readers; search 10 readers
        lat = {}
        for n, c in cl.items():
            cold = [timed(c, f"/api/documents/{urllib.parse.quote(d)}/text")[0] for d in doc_ids]
            warm = [timed(c, f"/api/documents/{urllib.parse.quote(d)}/text")[0] for d in doc_ids]
            def worker(k, c=c):
                cc = Client(c.base); cc.login("reader")
                return [timed(cc, f"/api/documents/{urllib.parse.quote(doc_ids[(i + k * 31) % len(doc_ids)])}/text")[0] for i in range(min(len(doc_ids), 300))]
            with cf.ThreadPoolExecutor(10) as ex:
                conc = [x for r in ex.map(worker, range(10)) for x in r]
            def sworker(k, c=c):
                cc = Client(c.base); cc.login("reader")
                return [timed(cc, "/api/search?q=" + urllib.parse.quote(q))[0] for _ in range(2) for q in Q[k % len(Q):] + Q[: k % len(Q)]]
            with cf.ThreadPoolExecutor(10) as ex:
                sconc = [x for r in ex.map(sworker, range(10)) for x in r]
            lat[n] = {"doc_text_cold_ms": stats(cold), "doc_text_warm_ms": stats(warm), "doc_text_10_readers_ms": stats(conc), "search_10_readers_ms": stats(sconc)}

        # ---------------- parity
        diffs, checked = [], 0
        digest = {n: hashlib.sha256() for n in cl}

        def compare(path, client_map=cl):
            nonlocal checked
            got = {n: canon(*c.call(path)) for n, c in client_map.items()}
            for n in got:
                digest[n].update(got[n].encode())
            checked += 1
            if got["memory"] != got["disk"]:
                diffs.append(path)

        for d in doc_ids:
            q = urllib.parse.quote(d)
            st, meta = cl["memory"].call(f"/api/documents/{q}")
            compare(f"/api/documents/{q}")
            pc = (meta or {}).get("copy", {}).get("page_count") or 0 if st == 200 else 0
            for start in range(1, max(pc, 1) + 1, 40):
                compare(f"/api/documents/{q}/text?from={start}&to={start + 39}")
            compare(f"/api/documents/{q}/sections")
            compare(f"/api/documents/{q}/relations")
            for page in sorted({1, max(1, pc // 2), max(1, pc)}):
                compare(f"/api/documents/{q}/citation?page={page}")
        for qq in Q:
            compare("/api/search?q=" + urllib.parse.quote(qq))
            compare("/api/search?q=" + urllib.parse.quote(qq) + "&page=2")
        st, doms = cl["memory"].call("/api/commander/domains")
        for dm in (doms or {}).get("domains", []):
            compare(f"/api/commander/domains/{dm['id']}")
        compare("/api/graph/stats")
        st, lib = cl["memory"].call("/api/library")
        graph_docs = [d for d in doc_ids if d.startswith(("act-", "rules-", "regulations-"))] + [d for d in doc_ids if not d.startswith(("act-", "rules-", "regulations-"))][:40]
        for d in graph_docs:
            st, r = cl["memory"].call(f"/api/graph/resolve?doc={urllib.parse.quote(d)}")
            compare(f"/api/graph/resolve?doc={urllib.parse.quote(d)}")
            if st == 200 and r and r.get("node_id"):
                compare(f"/api/graph/node?id={urllib.parse.quote(r['node_id'])}&depth=1&limit=200")

        # ---------------- withdrawal on both: text, citation and search must stop on both
        victim = next((d for d in doc_ids if not d.startswith(("act-", "rules-", "regulations-"))), doc_ids[0])
        withdrawal = {}
        for n, c in ad.items():
            st, _ = c.call("/api/admin/withdraw", {"doc_id": victim, "reason": "C16 WP04 parity check"})
            vq = urllib.parse.quote(victim)
            st_text, _ = cl[n].call(f"/api/documents/{vq}/text")
            st_cite, _ = cl[n].call(f"/api/documents/{vq}/citation?page=1")
            leaked = 0
            for qq in Q:
                _, r = cl[n].call("/api/search?q=" + urllib.parse.quote(qq))
                leaked += sum(1 for p in (r or {}).get("passages", []) if p.get("doc_id") == victim)
            withdrawal[n] = {"withdraw_status": st, "text_status": st_text, "citation_status": st_cite, "search_hits_for_withdrawn": leaked}
        for qq in Q[:6]:
            compare("/api/search?q=" + urllib.parse.quote(qq))   # post-withdrawal results identical too

        mem = {n: c.call("/api/diag/memory?gc=1")[1] for n, c in cl.items()}
        startup = {}
        for n in cl:
            txt = (logs / f"http-{n}.log").read_text(encoding="utf-8", errors="replace")
            m = re.search(r"start-up phases: generation load and re-hash (\d+) ms, index build (\d+) ms, hybrid (\d+) ms, process (\d+) ms", txt)
            startup[n] = {"health_wait_s": procs[n][1], **({"generation_load_ms": int(m[1]), "index_ms": int(m[2]), "process_ms": int(m[4])} if m else {})}
        res = {"site": str(site), "generation": gid, "documents": len(doc_ids), "search_engine": a.engine,
               "parity": {"requests_compared": checked, "differences": len(diffs), "first_differences": diffs[:20],
                          "response_digest_sha256": {n: h.hexdigest() for n, h in digest.items()}},
               "withdrawal": {"document_kind": "judgment or order" if not victim.startswith(("act-", "rules-")) else "statute", **withdrawal},
               "latency": lat, "memory_after_gc": mem, "startup": startup}
        a.out.write_text(json.dumps(res, indent=1), encoding="utf-8")
        print(json.dumps({"compared": checked, "differences": len(diffs), "withdrawal": withdrawal}, indent=1))
        return 0 if not diffs and all(w["text_status"] == 404 and w["search_hits_for_withdrawn"] == 0 for w in withdrawal.values()) else 1
    finally:
        for p, _ in procs.values():
            p.terminate()
            try:
                p.wait(20)
            except Exception:
                p.kill()


if __name__ == "__main__":
    sys.exit(main())
