"""Independent holdout run for the B1 retrieval oracle (for the evaluator who holds the blind holdout).

Same observation loop as app/b1/tests/oracles/run_retrieval_oracle.py, but the fixture is a parameter: the holdout file
never enters git and is never read by the development team. Scoring uses the UNMODIFIED PR #54 oracle
(docs/architecture/reviews/c13-assurance/retrieval_oracle.py --fixture <holdout>); its git blob is checked against HEAD.

  B1_URL=http://127.0.0.1:<port> python run_holdout.py --fixture <holdout.json> --map <site>/fixture_map.json --out <dir>
Users 'admin' and 'reader' must exist (b1server.py test mode creates them). See HOLDOUT_PROCEDURE.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.parse
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "app/b1/tests/oracles"))
from run_retrieval_oracle import ORACLE, Client, git_blob  # noqa: E402  (same client and blob check as the dev runner)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", type=Path, required=True)
    ap.add_argument("--map", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    blob = subprocess.run(["git", "-C", str(REPO), "hash-object", str(ORACLE)], capture_output=True, text=True, encoding="utf-8").stdout.strip()
    if blob != git_blob(ORACLE):
        sys.exit("retrieval_oracle.py differs from the committed version: refusing to run")
    fixture_bytes = a.fixture.read_bytes()
    fixture = json.loads(fixture_bytes.decode("utf-8"))
    m = json.loads(a.map.read_text(encoding="utf-8"))
    rev = {tuple(v): k for k, v in m["map"].items()}
    base = os.environ["B1_URL"]
    if "V-WITHDRAWN" in m.get("doc_ids", {}):
        admin = Client(base); admin.login("admin")
        admin.call("/api/admin/withdraw", {"doc_id": m["doc_ids"]["V-WITHDRAWN"], "reason": "holdout withdrawal canary (synthetic)"})
    user = Client(base); user.login("reader")
    obs = {}
    for case in fixture["queries"]:
        st, r = user.call("/api/search?" + urllib.parse.urlencode({"q": case["input"]}))
        ranking = [rev.get((p["doc_id"], p["passage_id"]), f"UNMAPPED:{p['doc_id']}#{p['passage_id']}") for p in (r.get("passages") or [])[:20]]
        obs[case["id"]] = {"mode": r.get("mode"), "state": r.get("state"), "ranking": ranking}
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "observations.json").write_text(json.dumps(obs, indent=1, ensure_ascii=False), encoding="utf-8")
    proc = subprocess.run([sys.executable, "-B", str(ORACLE), "--fixture", str(a.fixture), "--observations", str(a.out / "observations.json")],
                          capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    (a.out / "oracle_output.json").write_text(proc.stdout or proc.stderr, encoding="utf-8")
    res = json.loads(proc.stdout)
    summary = {"fixture_sha256": hashlib.sha256(fixture_bytes).hexdigest(), "oracle_blob": git_blob(ORACLE), "passed": res["passed"],
               "total": res["total"], "aggregate": res["aggregate"],
               "failed": {k: v["errors"] for k, v in res["cases"].items() if v["errors"]}}
    (a.out / "HOLDOUT_RESULTS.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"holdout: {res['passed']}/{res['total']} (fixture sha256 {summary['fixture_sha256'][:12]})")
    return 0 if res["passed"] == res["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
