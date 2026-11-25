"""Assert R2-N01 PDF.js protected-bootstrap expectations on run_protected.cjs output. Exit 1 on any failure."""
import json, sys

d = json.load(open(sys.argv[1]))
R = {r["label"]: r for r in d["results"]}
checks = []
def chk(name, ok): checks.append({"name": name, "pass": bool(ok)}); print(("PASS " if ok else "FAIL ") + name)
for label, r in R.items():
    s = r["summary"]
    chk(f"[{label}] every range request authenticated and bounded", s["all_range_requests_authenticated"] and s["all_range_requests_have_range_header"]
        and s["max_range_bytes"] <= 131072 and not s["any_request_without_range_to_pdf"])
pos = [r for l, r in R.items() if "near-end" in l or "positive control" in l]
for r in pos:
    chk(f"[{r['label']}] first page rendered and target page rendered, partial fetch", r["first_page"]["error"] is None and r["goto"]["ok"]
        and set(r["summary"]["statuses"]) == {"206"} and r["summary"]["fraction_of_file_fetched"] < 0.5)
for l, r in R.items():
    if "forged" in l: chk("forged token: no range request, viewer error", r["summary"]["range_requests"] == 0 and "401" in (r["first_page"]["error"] or ""))
    if "another user" in l: chk("other user's session: no range request, 404", r["summary"]["range_requests"] == 0 and "404" in (r["first_page"]["error"] or ""))
    if "withdraw between" in l:
        chk("withdrawal between chunks: zero post-fence 206, viewer invalidated", r["summary"]["post_fence_206"] == 0 and r["goto"]["ok"] is False
            and r["withdraw"]["status"] == 200)
ok = all(c["pass"] for c in checks)
json.dump({"all_pass": ok, "checks": checks}, open(sys.argv[2], "w"), indent=1)
sys.exit(0 if ok else 1)
