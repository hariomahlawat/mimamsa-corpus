"""C14 walkthrough: run the persona query set against a running B1 and record what the API returned.

Observations only. Relevance judgements are added by the auditor in SEARCH_EVALUATION.json ("assessment"),
never computed here. Usage:
  B1_URL=http://127.0.0.1:5199 B1_USER=user B1_PASSWORD=... python search_eval.py queries.json out.json
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import http.cookiejar

base = os.environ["B1_URL"].rstrip("/")
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
op.open(urllib.request.Request(base + "/api/login", method="POST",
        data=json.dumps({"username": os.environ["B1_USER"], "password": os.environ["B1_PASSWORD"]}).encode(),
        headers={"Content-Type": "application/json", "Origin": base}))

titles = {}


def title(doc_id):
    if doc_id not in titles:
        try:
            d = json.loads(op.open(base + "/api/documents/" + urllib.parse.quote(doc_id)).read())
            titles[doc_id] = (d.get("title") or (d.get("document") or {}).get("title") or "")[:140]
        except Exception as e:  # noqa: BLE001 - record, do not hide
            titles[doc_id] = f"<title unavailable: {e}>"
    return titles[doc_id]


queries = json.load(open(sys.argv[1], encoding="utf-8"))
out = []
for q in queries:
    url = base + "/api/search?" + urllib.parse.urlencode({"q": q["query"], **q.get("params", {})})
    t = time.perf_counter()
    r = json.loads(op.open(url).read())
    client_ms = round((time.perf_counter() - t) * 1000, 1)
    passages = r.get("passages") or []
    seen, top_docs = set(), []
    for p in passages:
        if p["doc_id"] not in seen:
            seen.add(p["doc_id"])
            top_docs.append(p["doc_id"])
    out.append({
        **q,
        "observed": {
            "state": r.get("state"), "mode": r.get("mode"), "error": r.get("error"),
            "chips": [c.get("text") for c in r.get("chips") or []],
            "total_documents": r.get("total_documents"), "total_passages": r.get("total_passages"),
            "shown_passages": r.get("shown_passages"),
            "server_ms": (r.get("run") or {}).get("ms"), "client_ms": client_ms,
            "top_documents": [{"rank": i + 1, "doc_id": d, "title": title(d)} for i, d in enumerate(top_docs[:5])],
            "top_passages": [{"rank": i + 1, "doc_id": p["doc_id"], "page": p.get("page"), "tier": p.get("tier"),
                              "reasons": p.get("reasons"), "snippet": (p.get("snippet") or "")[:220]}
                             for i, p in enumerate(passages[:3])],
            "notes": r.get("notes"),
        },
    })
json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{len(out)} queries recorded")
