"""C14 S1 latency check: the walkthrough's 20 perf queries (plus S1 cases), 5 sequential rounds after one warm-up.
Reports server-side elapsed_ms (API run.elapsed_ms) and client ms.  B1_URL, B1_USER, B1_PASSWORD; argv[1] = out.json"""
import json, os, sys, time, urllib.parse, urllib.request, http.cookiejar, statistics
base = os.environ["B1_URL"].rstrip("/")
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
op.open(urllib.request.Request(base + "/api/login", method="POST", data=json.dumps({"username": os.environ["B1_USER"], "password": os.environ["B1_PASSWORD"]}).encode(),
        headers={"Content-Type": "application/json", "Origin": base}))
Q = ["s.69 Army Act", "2013 INSC 408", "disability pension", "court martial", "summary of evidence", "AFT jurisdiction",
     "invalided out of service", "exact:\"Entitlement Rules\"", "desertion AND NOT pension", "Rule 22 Army Rules",
     "release medical board", "\"court martial\" NEAR/10 delay", "Civil Appeal No. 4949 of 2013",
     "writ petition armed forces tribunal", "field punishment", "attributable to military service",
     "sentence of dismissal", "section 302 Indian Penal Code", "Navy Act", "natural justice court of inquiry",
     "section 302 IPC", "Dharamvir Singh", "court marshal", "disabilty pension", "(2013) 7 SCC 316"]
def run(q):
    t = time.perf_counter(); r = json.loads(op.open(base + "/api/search?" + urllib.parse.urlencode({"q": q})).read())
    return r["run"]["elapsed_ms"], (time.perf_counter() - t) * 1000
warm = {q: run(q)[0] for q in Q}
srv, cli, per = [], [], {}
for _ in range(5):
    for q in Q:
        s, c = run(q); srv.append(s); cli.append(c); per.setdefault(q, []).append(s)
pct = lambda a, p: round(sorted(a)[max(0, int(round(p / 100 * len(a))) - 1)], 1)
out = {"queries": len(Q), "n": len(srv), "server_ms": {"p50": pct(srv, 50), "p95": pct(srv, 95), "max": round(max(srv), 1)},
       "client_ms": {"p50": pct(cli, 50), "p95": pct(cli, 95)}, "first_call_server_ms": warm,
       "slowest_median": sorted(((q, round(statistics.median(v), 1)) for q, v in per.items()), key=lambda x: -x[1])[:6]}
json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), indent=1); print(json.dumps({k: out[k] for k in ("server_ms", "client_ms", "slowest_median")}))
