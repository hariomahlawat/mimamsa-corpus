"""C15 S3 graph and reasoning probe against a running B1 (read-only).

Records graph statistics, sample neighbourhoods, paths and research assessments, and latency (p50/p95) for each route,
sequential and with 10 concurrent readers. Usage:
  B1_URL=http://127.0.0.1:5530 B1_USER=reader B1_PASSWORD=... python graph_probe.py out.json
"""
import concurrent.futures as cf
import http.cookiejar
import json
import os
import sys
import time
import urllib.parse
import urllib.request

base = os.environ["B1_URL"].rstrip("/")


def client():
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    op.open(urllib.request.Request(base + "/api/login", method="POST", headers={"Content-Type": "application/json", "Origin": base},
                                   data=json.dumps({"username": os.environ["B1_USER"], "password": os.environ["B1_PASSWORD"]}).encode()))
    return op


def get(op, path, **q):
    url = base + path + ("?" + urllib.parse.urlencode(q) if q else "")
    t = time.perf_counter()
    try:
        r = op.open(url); body = json.loads(r.read()); status = r.status
    except urllib.error.HTTPError as e:
        body = json.loads(e.read() or b"{}"); status = e.code
    return (time.perf_counter() - t) * 1000, status, body


def pct(a, p):
    a = sorted(a); return round(a[max(0, int(round(p / 100 * len(a))) - 1)], 1)


op = client()
out = {"base": base}
_, _, out["stats"] = get(op, "/api/graph/stats")
nid = lambda doc, sec=None: get(op, "/api/graph/resolve", doc=doc, **({"section": sec} if sec else {}))[2]["node_id"]
ids = {"AA s.69": nid("act-army-1950", "69"), "AA s.75": nid("act-army-1950", "75"), "IPC s.302": nid("act-ipc-1860", "302"),
       "BNS s.103": nid("act-bns-2023", "103"), "Army Act": nid("act-army-1950"), "Dharamvir Singh": nid("sc-2013-dharamvir-singh-2013insc408")}
out["resolved"] = ids
samples = {}
for k, v in ids.items():
    _, st, body = get(op, "/api/graph/node", id=v, depth=1)
    edges = body.get("edges", [])
    samples[k] = {"status": st, "node": body.get("node"), "edge_count": len(edges), "truncated": body.get("truncated"),
                  "by_type": {t: sum(1 for e in edges if e["type"] == t) for t in sorted({e["type"] for e in edges})}}
out["neighbourhoods"] = samples
_, _, out["path_ipc302_bns103"] = get(op, "/api/graph/path", **{"from": ids["IPC s.302"], "to": ids["BNS s.103"], "max_depth": 2})
_, _, out["path_dharamvir_aa"] = get(op, "/api/graph/path", **{"from": ids["Dharamvir Singh"], "to": ids["Army Act"], "max_depth": 3})
out["assessments"] = {
    "temporal AA s.75 @2000-01-01": get(op, "/api/reasoning/assess", kind="temporal", doc="act-army-1950", section="75", as_of="2000-01-01")[2],
    "succession IPC s.302 conduct 2023-12-01": get(op, "/api/reasoning/assess", kind="succession", doc="act-ipc-1860", section="302", conduct_date="2023-12-01")[2],
    "procedure Summary court-martial": get(op, "/api/reasoning/assess", kind="procedure", task="Summary court-martial")[2],
    "conflicts AA s.127": get(op, "/api/reasoning/assess", kind="conflicts", doc="act-army-1950", section="127")[2],
}
_, _, out["rule_gate"] = get(op, "/api/reasoning/rule-gate")

routes = [("node depth1 provision", "/api/graph/node", {"id": ids["AA s.69"], "depth": 1}),
          ("node depth2 provision", "/api/graph/node", {"id": ids["IPC s.302"], "depth": 2}),
          ("node depth1 judgment", "/api/graph/node", {"id": ids["Dharamvir Singh"], "depth": 1}),
          ("path depth3", "/api/graph/path", {"from": ids["Dharamvir Singh"], "to": ids["Army Act"], "max_depth": 3}),
          ("stats", "/api/graph/stats", {}),
          ("assess succession", "/api/reasoning/assess", {"kind": "succession", "doc": "act-ipc-1860", "section": "302", "conduct_date": "2023-12-01"}),
          ("assess temporal", "/api/reasoning/assess", {"kind": "temporal", "doc": "act-army-1950", "section": "75", "as_of": "2000-01-01"})]
lat = {}
for name, path, q in routes:
    for _ in range(3): get(op, path, **q)
    seq = [get(op, path, **q)[0] for _ in range(30)]
    ops = [client() for _ in range(10)]
    with cf.ThreadPoolExecutor(10) as ex:
        par = list(ex.map(lambda i: get(ops[i % 10], path, **q)[0], range(100)))
    lat[name] = {"sequential": {"n": len(seq), "p50": pct(seq, 50), "p95": pct(seq, 95)}, "concurrent10": {"n": len(par), "p50": pct(par, 50), "p95": pct(par, 95)}}
out["latency_ms"] = lat
json.dump(out, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({"stats": {k: out["stats"][k] for k in ("nodes", "edges", "edges_by_verification")}, "latency": lat,
                  "overall": {k: v.get("overall") for k, v in out["assessments"].items()}}, indent=1))
