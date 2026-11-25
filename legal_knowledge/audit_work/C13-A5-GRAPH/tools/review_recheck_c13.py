#!/usr/bin/env python3
"""C13-A5 review F01/F02/F03: re-check the independent reviewer's 54-edge sample (f915ac11) against the revised extractor.

The reviewer's verdicts are taken as truth for each sampled edge. The sampled edges are located in the f915ac11 graph
(git object) to find their passage ids, and the current passage classification is read from treatment/.
This is NOT an independent measurement of the revised extractor: the revisions were made after reading these
verdicts. It shows which reviewer-found errors are removed and which correct edges were lost.

  python -I -B review_recheck_c13.py [--check]
"""
from __future__ import annotations

import gzip
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common_c13 as C  # noqa: E402

REVIEWED_COMMIT = "f915ac11"
OLD = "legal_knowledge/audit_work/C13-A5-GRAPH/graph/edges_candidate.jsonl.gz"


def main():
    check = "--check" in sys.argv[1:]
    old = {}
    for line in gzip.decompress(C.git(C.WT, "show", "%s:%s" % (REVIEWED_COMMIT, OLD))).decode().splitlines():
        e = json.loads(line)
        old[e["edge_id"]] = e
    cur = {r["passage_id"]: r for r in C.read_csv(C.PKG / "treatment" / "TREATMENT_PASSAGES_C13.csv.gz")}
    rows, tally = [], Counter()
    for v in C.read_csv(C.PKG / "reviews" / "treatment_sample_verdicts.csv"):
        pid = old[v["edge_id"]]["attributes"]["passage_id"]
        r = cur.get(pid) or {}
        now = r.get("relation", "NOT_PRESENT")
        ok = v["fully_correct"] == "Y"
        if now == "CITES":
            outcome = "WITHDRAWN_REVIEWER_FOUND_ERROR" if not ok else "WITHDRAWN_LOST_CORRECT_EDGE"
        elif now == v["edge_type"]:
            outcome = "KEPT_CORRECT" if ok else "KEPT_STILL_FLAGGED"
        else:
            outcome = "RETYPED_%s_TO_%s" % (v["edge_type"], now)
        if outcome == "KEPT_STILL_FLAGGED" and v["edge_type"] == "DISAPPROVES" and "subsequent decisions" in (r.get("target_raw") or ""):
            outcome = "KEPT_TARGET_CORRECTED"
        tally[outcome] += 1
        rows.append(dict(sid=v["sid"], edge_type_reviewed=v["edge_type"], reviewer_fully_correct=v["fully_correct"],
                         reviewer_note=v["note"][:160], passage_id=pid, current_relation=now, current_voice=r.get("voice", ""),
                         current_target_raw=(r.get("target_raw") or "")[:120], current_reasons=(r.get("reasons") or "")[:200],
                         outcome=outcome))
    summary = dict(reviewed_commit=REVIEWED_COMMIT, sample=len(rows), outcomes=dict(sorted(tally.items())),
                   note="Not independent: the extractor was revised after reading these verdicts. Independent figures await A0 (H-REL-C13).")
    files = {"REVIEW_SAMPLE_RECHECK_C13.csv": C.to_csv(rows), "REVIEW_SAMPLE_RECHECK_C13.json": C.dumps(summary)}
    rc = C.write_or_check(files, C.PKG / "treatment", check)
    if not check:
        print(json.dumps(summary, indent=1))
    return rc


if __name__ == "__main__":
    sys.exit(main())
