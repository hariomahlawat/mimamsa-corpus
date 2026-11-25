#!/usr/bin/env python3
"""Corpus-wide comparison of the V4 full run with the frozen V3 run (aggregates only; no judgment text is read).

Writes outputs/CORPUS_COMPARISON_V4_V3.json and .md. Counts are measured on the extractor outputs; they say nothing
about correctness (see dev_eval for in-sample precision, and the independent H-OUT-C13 evaluation)."""
import csv
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
import extract_v4  # noqa: E402

V3 = os.path.join(extract_v4.AUDIT, "C12-CONSOLIDATION", "extractor_v3", "outputs", "OUTCOMES_V3.csv")
V4 = os.path.join(extract_v4.OUT, "OUTCOMES_V4.csv")
U = "OUTCOME_UNVERIFIED"


def stats(path, drop=frozenset()):
    rows = [r for r in csv.DictReader(open(path, encoding="utf-8")) if r["judgment_id"] not in drop]
    js = {}
    for r in rows:
        js.setdefault(r["judgment_id"], []).append(r)
    out = {"rows": len(rows), "judgments": len(js)}
    for f in ("printed_disposal", "substantive_result"):
        out[f] = {"row_answered": sum(r[f] != U for r in rows),
                  "judgment_any_answered": sum(any(r[f] != U for r in v) for v in js.values()),
                  "labels": dict(Counter(r[f] for r in rows).most_common())}
    out["abstain_reasons_both_fields"] = dict(Counter(r["abstain_reason"].split(":")[0] for r in rows
                                                      if r["printed_disposal"] == U and r["substantive_result"] == U).most_common())
    out["by_court_judgment_printed_coverage"] = {}
    for c in sorted(set(r["court"] for r in rows)):
        v = [x for x in js.values() if x[0]["court"] == c]
        out["by_court_judgment_printed_coverage"][c or "(none)"] = "%d/%d" % (sum(any(r["printed_disposal"] != U for r in x) for x in v), len(v))
    if "confidence" in rows[0]:
        out["confidence"] = dict(Counter(r["confidence"] for r in rows if r["printed_disposal"] != U or r["substantive_result"] != U))
        out["notes_v4"] = dict(Counter(n.split(":")[0] for r in rows for n in r["notes"].split(";") if n).most_common())
    return out


def main():
    # judgments excluded from the V4 development run (fresh holdout) are dropped from BOTH sides
    drop = frozenset(r["judgment_id"] for r in csv.DictReader(open(V4, encoding="utf-8"))
                     if r["abstain_reason"] == extract_v4.EXCLUDED_REASON)
    s = {"V3": stats(V3, drop), "V4": stats(V4, drop), "MEASURED_ON_OUTPUTS_ONLY": True, "excluded_judgments_dropped": len(drop)}
    extract_v4.write_atomic(os.path.join(extract_v4.OUT, "CORPUS_COMPARISON_V4_V3.json"),
                            (json.dumps(s, indent=1, sort_keys=True) + "\n").encode())
    L = ["# V4 full-corpus run compared with frozen V3 (output counts only, not correctness)", "",
         "Judgments excluded from the V4 development run (H-OUT-C13 and copies): %d, dropped from both columns." % len(drop), "",
         "| Measure | V3 | V4 |", "| --- | --- | --- |"]
    for k in ("rows", "judgments"):
        L.append("| %s | %d | %d |" % (k, s["V3"][k], s["V4"][k]))
    for f in ("printed_disposal", "substantive_result"):
        for k in ("row_answered", "judgment_any_answered"):
            L.append("| %s %s | %d | %d |" % (f, k, s["V3"][f][k], s["V4"][f][k]))
    for reason in ("ONLY_QUOTED_DISPOSITION_LANGUAGE_FOUND", "NO_OPERATIVE_CUE_IN_FINAL_PART", "EXTENT_QUALIFIED_ALLOWANCE_ALLOWED_OR_PARTLY_ALLOWED_UNDETERMINED"):
        L.append("| abstain %s | %d | %d |" % (reason, s["V3"]["abstain_reasons_both_fields"].get(reason, 0),
                                                s["V4"]["abstain_reasons_both_fields"].get(reason, 0)))
    L += ["", "Judgment-level printed coverage by court:", "", "| Court | V3 | V4 |", "| --- | --- | --- |"]
    for c in sorted(set(s["V3"]["by_court_judgment_printed_coverage"]) | set(s["V4"]["by_court_judgment_printed_coverage"])):
        L.append("| %s | %s | %s |" % (c, s["V3"]["by_court_judgment_printed_coverage"].get(c, ""), s["V4"]["by_court_judgment_printed_coverage"].get(c, "")))
    L += ["", "V4 printed labels: " + json.dumps(s["V4"]["printed_disposal"]["labels"]),
          "", "V3 printed labels: " + json.dumps(s["V3"]["printed_disposal"]["labels"]),
          "", "V4 confidence tiers (answered rows): " + json.dumps(s["V4"].get("confidence", {})),
          "", "V4 notes: " + json.dumps(s["V4"].get("notes_v4", {}))]
    extract_v4.write_atomic(os.path.join(extract_v4.OUT, "CORPUS_COMPARISON_V4_V3.md"), ("\n".join(L) + "\n").encode())
    print("\n".join(L))


if __name__ == "__main__":
    main()
