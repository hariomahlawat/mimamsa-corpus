"""Interleaved A/B latency: each query alternates between two servers (A = this branch, B = baseline build), 7 rounds,
so machine-load drift affects both equally. Server-side run.elapsed_ms is compared per query (median).
usage: B1_USER=.. B1_PASSWORD=.. python latency_ab.py <url A> <url B> out.json"""
import json, os, statistics, sys, urllib.parse, urllib.request, http.cookiejar
def client(base):
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    op.open(urllib.request.Request(base + "/api/login", method="POST", data=json.dumps({"username": os.environ["B1_USER"], "password": os.environ["B1_PASSWORD"]}).encode(),
            headers={"Content-Type": "application/json", "Origin": base}))
    return lambda q: json.loads(op.open(base + "/api/search?" + urllib.parse.urlencode({"q": q})).read())["run"]["elapsed_ms"]
A, B = client(sys.argv[1]), client(sys.argv[2])
Q = ["s.69 Army Act", "2013 INSC 408", "disability pension", "court martial", "summary of evidence", "AFT jurisdiction",
     "invalided out of service", "exact:\"Entitlement Rules\"", "desertion AND NOT pension", "Rule 22 Army Rules",
     "release medical board", "\"court martial\" NEAR/10 delay", "Civil Appeal No. 4949 of 2013",
     "writ petition armed forces tribunal", "field punishment", "attributable to military service",
     "sentence of dismissal", "section 302 Indian Penal Code", "Navy Act", "natural justice court of inquiry"]
for q in Q: A(q); B(q)
res = {}
for q in Q:
    a, b = [], []
    for _ in range(7): a.append(A(q)); b.append(B(q))
    res[q] = {"a_median": statistics.median(a), "b_median": statistics.median(b)}
am = [v["a_median"] for v in res.values()]; bm = [v["b_median"] for v in res.values()]
out = {"queries": len(Q), "rounds": 7, "sum_of_medians_ms": {"a": round(sum(am), 1), "b": round(sum(bm), 1)},
       "median_of_medians_ms": {"a": statistics.median(am), "b": statistics.median(bm)}, "per_query": res}
json.dump(out, open(sys.argv[3], "w", encoding="utf-8"), indent=1)
print(json.dumps({k: out[k] for k in ("sum_of_medians_ms", "median_of_medians_ms")}))
print(json.dumps(sorted(((q, v["a_median"], v["b_median"]) for q, v in res.items()), key=lambda x: x[2] - x[1])[:5]))
