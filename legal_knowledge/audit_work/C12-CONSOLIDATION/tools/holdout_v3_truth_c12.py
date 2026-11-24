#!/usr/bin/env python3
"""C12: final V3 holdout ground truth = coder rows where both blind coders fully agree (coder A's rows, identical labels),
adjudicated rows (blind third coder) for the 14 DISAGREE judgments.  python -I -B holdout_v3_truth_c12.py [--check]"""
import csv, io, sys
from collections import defaultdict
from pathlib import Path
PKG = Path(__file__).resolve().parent.parent
H = PKG / "holdout_v3"
COLS = ["holdout_id", "judgment_id", "proceeding", "printed_disposal", "substantive_result", "party_specific", "final_or_interim",
        "page", "para", "excerpt", "confidence", "source"]


def main():
    agree = {r["holdout_id"]: r["status"] for r in csv.DictReader(open(H / "AGREEMENT.csv", encoding="utf-8"))}
    A = defaultdict(list)
    for seg in (1, 2, 3):
        for r in csv.DictReader(open(H / "coding" / f"coder_A_seg{seg}.csv", encoding="utf-8")):
            A[r["holdout_id"]].append(r)
    adj = defaultdict(list)
    for r in csv.DictReader(open(H / "ADJUDICATION.csv", encoding="utf-8")):
        adj[r["holdout_id"]].append(r)
    out = []
    for h in sorted(agree):
        src = (adj[h], "ADJUDICATED") if agree[h] == "DISAGREE" else (A[h], "BOTH_CODERS_AGREE")
        assert src[0], h
        for r in src[0]:
            out.append({**{c: r.get(c, "") for c in COLS[:-1]}, "source": src[1]})
    s = io.StringIO(); w = csv.DictWriter(s, fieldnames=COLS, lineterminator="\n"); w.writeheader(); w.writerows(out)
    t = H / "GROUND_TRUTH_V3.csv"
    if "--check" in sys.argv[1:]:
        ok = t.read_text(encoding="utf-8") == s.getvalue(); print("ground truth reproduces" if ok else "CHECK FAILED"); return 0 if ok else 1
    t.write_text(s.getvalue(), encoding="utf-8")
    print(len(out), "rows;", len({r["holdout_id"] for r in out}), "judgments;", sum(1 for r in out if r["source"] == "ADJUDICATED"), "adjudicated rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
