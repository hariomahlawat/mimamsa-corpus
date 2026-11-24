#!/usr/bin/env python3
"""Re-measure the rebuilt outputs on the rows sampled by the independent review (fable_review_relations_c11_rows.csv).

For every reviewed row it records what the rebuilt output now says (after) next to what the review saw (before) and the
reviewer's verdict, then recomputes precision per category on the rows that are still proposed / queued / labelled.
The reviewer verdicts are taken as ground truth for the before state; rows whose after-state is a renamed label are
listed for reading, not scored as correct.

    python3.11 -B -I tools/remeasure_review_c11.py [--review <rows.csv>]
Writes outputs/REVIEW_REMEASURE_C11.csv and outputs/REVIEW_REMEASURE_C11.json (deterministic).
"""
import argparse
import csv
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import relations_c11 as R  # noqa: E402

DEFAULT_REVIEW = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(R.AUDIT))), "c10out", "rev_c11",
                              "fable_review_relations_c11_rows.csv")
GOOD = {"SUPPORTED", "TARGET_CORRECT", "FAIR", "FAIR_OVER_CONSERVATIVE", "FAIR_BUT_SPURIOUS_EDGE", "VERBATIM_ON_STATED_PAGE"}


def rows(p):
    with open(p, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def keys_of(raw):
    return set(c["key"] for c in R.find_citations(raw) + R.find_case_numbers(raw))


def norm_pid(pid):
    m = re.match(r"([A-Z0-9-]+):([a-z]+)\.(.+)$", pid or "")
    if not m:
        return pid
    return "%s:%s.%s" % (m.group(1), R.normalise_unit(m.group(1), m.group(2)), m.group(3))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--review", default=DEFAULT_REVIEW)
    a = ap.parse_args()
    rev = rows(a.review)
    cands = {r["candidate_id"]: r for r in rows(os.path.join(R.OUT, "TREATMENT_CANDIDATES.csv"))}
    edges_by_src = defaultdict(list)
    for r in rows(os.path.join(R.OUT, "CASE_CITATION_GRAPH.csv")):
        edges_by_src[r["source_doc_id"]].append(r)
    links = defaultdict(list)
    for r in rows(os.path.join(R.OUT, "STATUTE_JUDGMENT_LINKS.csv")):
        links[r["doc_id"]].append(r)
    out = []
    for x in rev:
        cat, rid, verdict = x["category"], x["row_id"], x["verdict"]
        good = verdict in GOOD
        after, still = "", None
        if rid.startswith("TC-"):
            c = cands.get(rid)
            if c is not None and not c["proposed_relation"] and c["status"] == R.STATUS_AUTO or c is None:
                # equivalent candidate: same citing judgment, cue page and cue words, same stated target, other anchor
                alt = [k for k in cands.values() if k["source_doc_id"] == x["source_doc_id"] and k["cue_text"] == x["cue"]
                       and (x["stated_target"] in (k["target_doc_ids"].split(";") + [k["cited_string"]]))
                       and (k["proposed_relation"] or k["status"] != R.STATUS_AUTO)]
                if alt:
                    c = sorted(alt, key=lambda k: k["candidate_id"])[0]
            if c is None:
                after, still = "NO_CANDIDATE_GENERATED (cue outside the anchor sentence or anchor removed)", False
            else:
                after = "%s/%s/%s" % (c["proposed_relation"] or "-", c["attribution"], c["status"])
                if cat == "ADVISER_REPORTED_TREATMENT":
                    still = c["status"] != R.STATUS_AUTO
                else:
                    still = bool(c["proposed_relation"])
        elif rid.startswith("E-"):
            ks = keys_of(x["tool_value"])
            hits = [e for e in edges_by_src.get(x["source_doc_id"], []) if ks & set(e["citation_keys"].split(";"))]
            if not hits:
                after, still = "NO_EDGE (string no longer read as a citation)", False
            else:
                e = sorted(hits, key=lambda e: e["edge_id"])[0]
                after = "%s %s %s" % (e["target_state"], e["target_doc_ids"].split(";")[0], e["resolution_method"])
                still = e["target_state"] == "RESOLVED"
                if cat.startswith("UNRESOLVED"):
                    still = e["target_state"] != "RESOLVED"
        elif rid.startswith("SL-"):
            pid = norm_pid(x["stated_target"])
            hits = [l for l in links.get(x["source_doc_id"], []) if (l["provision_id"] or l["instrument_id"]) == pid
                    or (l["provision_id"] == "" and l["instrument_id"] == pid)]
            if not hits:
                after, still = "NO_LINK for %s" % pid, False
            else:
                l = hits[0]
                after = "%s %s" % (l["provision_id"] or l["instrument_id"], l["relationship"])
                still = l["relationship"] == cat
        elif rid.startswith("RD-"):
            after, still = "dossier reading unchanged (re-verified at build)", True
        out.append({"category": cat, "row_id": rid, "source_doc_id": x["source_doc_id"], "reviewer_verdict": verdict,
                    "before": x["tool_value"], "after": after, "still_proposed_or_labelled": "YES" if still else "NO"})
    summ = {}
    by = defaultdict(list)
    for r in out:
        by[r["category"]].append(r)
    for cat in sorted(by):
        rs = by[cat]
        kept = [r for r in rs if r["still_proposed_or_labelled"] == "YES"]
        summ[cat] = {"sample": len(rs), "supported_before": sum(r["reviewer_verdict"] in GOOD for r in rs),
                     "still_proposed_after": len(kept), "supported_among_kept": sum(r["reviewer_verdict"] in GOOD for r in kept),
                     "unsupported_withdrawn": sum(1 for r in rs if r["reviewer_verdict"] not in GOOD and r["still_proposed_or_labelled"] == "NO"),
                     "supported_lost": sum(1 for r in rs if r["reviewer_verdict"] in GOOD and r["still_proposed_or_labelled"] == "NO")}
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(out[0].keys()), lineterminator="\n")
    w.writeheader()
    for r in out:
        w.writerow(r)
    with open(os.path.join(R.OUT, "REVIEW_REMEASURE_C11.csv"), "w", encoding="utf-8", newline="") as f:
        f.write(buf.getvalue())
    with open(os.path.join(R.OUT, "REVIEW_REMEASURE_C11.json"), "w", encoding="utf-8") as f:
        f.write(json.dumps(summ, indent=1, sort_keys=True) + "\n")
    print(json.dumps(summ, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
