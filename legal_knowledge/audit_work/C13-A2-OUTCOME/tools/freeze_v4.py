#!/usr/bin/env python3
"""Write outputs/FREEZE_V4.json: the frozen V4 tool hashes and the full-run output hashes.

NOT RUN by the developer. Run only after the coordinator confirms that the A0 holdout protocol (H-OUT-C13) has been
accepted and has supplied the exclusion list, and after `extract_v4.py --exclude-ids <list> run` and `--check` pass:

  python -I -B tools/freeze_v4.py --confirmation "<coordinator message reference>" --exclude-ids <list>

It refuses to write if the assembled output is stale, if FREEZE_V4.json already exists, or if the check fails."""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import extract_v4  # noqa: E402
import v4core  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--confirmation", required=True, help="reference to the coordinator's freeze confirmation")
    ap.add_argument("--exclude-ids", default="")
    ap.add_argument("--statement", default="", help="author statement file embedded in the freeze record")
    a = ap.parse_args()
    path = os.path.join(extract_v4.OUT, "FREEZE_V4.json")
    if os.path.exists(path):
        sys.exit("FREEZE_V4.json exists; a frozen extractor is never re-frozen in place")
    r = subprocess.run([sys.executable, "-I", "-B", os.path.join(HERE, "extract_v4.py"), "--exclude-ids", a.exclude_ids, "check"])
    if r.returncode != 0:
        sys.exit("check failed; not freezing")
    excl = extract_v4.read_ids(a.exclude_ids)
    head = subprocess.run(["git", "-C", HERE, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    out = {"extractor": v4core.VERSION, "status": v4core.STATUS, "frozen_at_commit_parent": head,
           "coordinator_confirmation": a.confirmation, "tool_sha256": extract_v4.tool_hashes(),
           "tool_fingerprint": extract_v4.tool_fingerprint(),
           "outputs_sha256": {n: extract_v4.sha256_bytes(open(os.path.join(extract_v4.OUT, n), "rb").read())
                              for n in ("OUTCOMES_V4.csv", "RUN_INFO_V4.json") if os.path.exists(os.path.join(extract_v4.OUT, n))},
           "exclusion_list_sha256": extract_v4.exclusion_key(set(excl)), "excluded_ids": len(excl),
           "author_statement_file": os.path.basename(a.statement) if a.statement else "",
           "author_statement_sha256": extract_v4.sha256_bytes(open(a.statement, "rb").read()) if a.statement else "",
           "author_statement": open(a.statement, encoding="utf-8").read() if a.statement else "",
           "blind_evaluation_command": "python3.11 -I -B tools/extract_v4.py ids --ids-file <H-OUT-C13 ids> --out <DIR>"}
    extract_v4.write_atomic(path, (json.dumps(out, indent=1, sort_keys=True) + "\n").encode())
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
