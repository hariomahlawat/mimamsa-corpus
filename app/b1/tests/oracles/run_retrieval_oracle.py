"""Run the PR #54 retrieval oracle (docs/architecture/reviews/c13-assurance/retrieval_oracle.py, UNMODIFIED) against the
real B1 search service on the synthetic SYN site (app/b1/build/build_fixture_site.py).

Requires B1_URL (see app/b1/tests/b1server.py) and --map <out>/fixture_map.json. Steps: Admin withdraws the
V-WITHDRAWN canary through the real Admin API (serving fence); the User runs all 14 RET inputs exactly as written;
each returned passage is mapped back to its fixture passage id (unmapped ids are kept as UNMAPPED:<doc>#<passage>,
which the oracle counts as failures); the oracle scores the observations. Writes observations, the oracle output
and an expected-vs-observed table.
"""
import argparse
import hashlib
import http.cookiejar
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
ORACLE = REPO / "docs/architecture/reviews/c13-assurance/retrieval_oracle.py"
FIXTURE = REPO / "docs/architecture/reviews/c13-assurance/retrieval-dev-fixture.json"


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
            with self.op.open(req) as r:
                return r.status, json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"null")

    def login(self, user):
        st, s = self.call("/api/login", {"username": user, "password": f"{user}-password-1"})
        assert st == 200, (st, s)
        self.csrf = s["csrf"]


def git_blob(path: Path) -> str:
    return subprocess.run(["git", "-C", str(REPO), "rev-parse", f"HEAD:{path.relative_to(REPO).as_posix()}"], capture_output=True, text=True, encoding="utf-8").stdout.strip()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--expected-failures", default="RET-06,RET-07,RET-09,RET-10",
                    help="recorded baseline: cases known to fail (hybrid mode, B1 is lexical). Any OTHER failing case fails the run.")
    a = ap.parse_args()
    base = os.environ["B1_URL"]
    m = json.loads(a.map.read_text(encoding="utf-8"))
    rev = {tuple(v): k for k, v in m["map"].items()}
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    # oracle and fixture must be byte-identical to the committed (frozen) versions
    for f in (ORACLE, FIXTURE):
        # git hash-object applies the checkout's clean filters (CRLF on Windows), so this compares content with HEAD
        blob = subprocess.run(["git", "-C", str(REPO), "hash-object", str(f)], capture_output=True, text=True, encoding="utf-8").stdout.strip()
        if blob != git_blob(f):
            sys.exit(f"{f.name} differs from the committed version: refusing to run")
    admin = Client(base); admin.login("admin")
    st, w = admin.call("/api/admin/withdraw", {"doc_id": m["doc_ids"]["V-WITHDRAWN"], "reason": "PR #54 withdrawal canary (synthetic)"})
    assert st == 200 and w.get("status") in ("withdrawn", "already_withdrawn"), (st, w)
    user = Client(base); user.login("reader")
    obs, rows = {}, []
    for case in fixture["queries"]:
        st, r = user.call("/api/search?" + urllib.parse.urlencode({"q": case["input"]}))
        ranking = []
        for p in (r.get("passages") or [])[:20]:
            ranking.append(rev.get((p["doc_id"], p["passage_id"]), f"UNMAPPED:{p['doc_id']}#{p['passage_id']}"))
        obs[case["id"]] = {"mode": r.get("mode"), "state": r.get("state"), "ranking": ranking}
        rows.append({"id": case["id"], "input": case["input"], "expected_mode": case["mode"],
                     "expected_state": case.get("exclusive_state") or ("empty" if case.get("empty") else "results"),
                     "observed_mode": r.get("mode"), "observed_state": r.get("state"), "observed_top5": ranking[:5],
                     "chips": [c["text"] for c in r.get("chips") or []]})
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "observations.json").write_text(json.dumps(obs, indent=1, ensure_ascii=False), encoding="utf-8")
    proc = subprocess.run([sys.executable, "-B", str(ORACLE), "--observations", str(a.out / "observations.json")], capture_output=True,
                          text=True, encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    (a.out / "oracle_output.json").write_text(proc.stdout or proc.stderr, encoding="utf-8")
    try:
        res = json.loads(proc.stdout)
    except ValueError:
        print(proc.stdout, proc.stderr)
        return 2
    for row in rows:
        errs = res["cases"][row["id"]]["errors"]
        row["oracle_errors"] = errs
        row["status"] = "Passed" if not errs else "Failed"
        row["metrics"] = res["cases"][row["id"]]["metrics"]
    summary = {"oracle_exit": proc.returncode, "passed": res["passed"], "total": res["total"], "aggregate": res["aggregate"],
               "oracle_blob": git_blob(ORACLE), "fixture_blob": git_blob(FIXTURE), "withdrawal": w, "cases": rows}
    (a.out / "RESULTS.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    for row in rows:
        print(f"{row['id']}: {row['status']:7} mode {row['observed_mode']} (exp {row['expected_mode']}) state {row['observed_state']} top {row['observed_top5'][:3]} {'; '.join(row['oracle_errors'])}")
    print(f"oracle: {res['passed']}/{res['total']} cases without hard-assertion errors (exit {proc.returncode})")
    expected = {x for x in a.expected_failures.split(",") if x}
    regressions = [r["id"] for r in rows if r["oracle_errors"] and r["id"] not in expected]
    if regressions:
        print(f"REGRESSION against the recorded baseline: {regressions}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
