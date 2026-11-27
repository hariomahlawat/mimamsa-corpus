#!/usr/bin/env python3
"""Rebuild the scorer-format H-OUT-C13 prediction file from the frozen V4 raw output (POST-FREEZE ADDITION).

This tool performs no extraction and does not affect V4's rules or outputs. It maps the frozen extractor's raw
proceeding rows (raw/OUTCOMES_V4.csv in the predictions folder, produced by `extract_v4.py ids`) onto the item
pointers (ITEM_POINTERS.csv in the same folder: item_id, rep_sha256, judgment_id) in the column format of the A0 harness
c13_score.py. It is the same mapping that produced the file GA4 scored (sha256 45c5a332...), committed after the freeze
on review finding A2-03.

  python -I -B tools/predict_holdout_v4.py [--out FILE]    # writes the predictions file (default: alongside raw/)
  python -I -B tools/predict_holdout_v4.py --check         # rebuilds in memory and compares with the frozen sha256

Items whose rep_sha256 has no judgment_id (not in the c7 text layer V4 reads) get one UNIDENTIFIED abstention row
(NO_JUDGMENT_ID_FOR_ITEM_SHA). pred_id is V4P + running number over output rows, in item order."""
import argparse
import csv
import hashlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PDIR = os.path.join(os.path.dirname(HERE), "predictions_H-OUT-C13")
FROZEN_SHA256 = "45c5a3321d22e2948e2783c2ba6a6857d51f1c705e7b90993ddc3a68ad239b69"
COLS = ["item_id", "proceeding", "host_case_numbers", "printed_disposal", "substantive_result", "party_specific",
        "final_or_interim", "page", "para", "excerpt", "confidence", "notes", "pred_id"]
NO_ID = dict(proceeding="UNIDENTIFIED", printed_disposal="OUTCOME_UNVERIFIED", substantive_result="OUTCOME_UNVERIFIED",
             party_specific="", final_or_interim="", page="", paragraph="", excerpt="", confidence="",
             abstain_reason="NO_JUDGMENT_ID_FOR_ITEM_SHA")


def build(pdir=PDIR):
    items = [(r["item_id"], r["judgment_id"]) for r in csv.DictReader(open(os.path.join(pdir, "ITEM_POINTERS.csv"), encoding="utf-8"))]
    byj = {}
    for r in csv.DictReader(open(os.path.join(pdir, "raw", "OUTCOMES_V4.csv"), encoding="utf-8")):
        byj.setdefault(r["judgment_id"], []).append(r)
    out, n = [], 0
    for item, j in items:
        rs = byj.get(j) if j else None
        rs = rs or [dict(NO_ID)]
        hosts = ";".join(r["proceeding"] for r in rs if r["proceeding"] != "UNIDENTIFIED")
        for r in rs:
            n += 1
            out.append(dict(item_id=item, proceeding=r["proceeding"], host_case_numbers=hosts,
                            printed_disposal=r["printed_disposal"], substantive_result=r["substantive_result"],
                            party_specific=r["party_specific"], final_or_interim=r["final_or_interim"], page=r["page"],
                            para=r.get("paragraph", ""), excerpt=r["excerpt"], confidence=r.get("confidence", ""),
                            notes=";".join(x for x in [r.get("abstain_reason", ""), r.get("notes", "")] if x),
                            pred_id="V4P%05d" % n))
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS, lineterminator="\n")
    w.writeheader()
    w.writerows(out)
    return buf.getvalue().encode("utf-8"), len(items), len(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--out", default=os.path.join(PDIR, "PREDICTIONS_OUTCOME_V4_H-OUT-C13.csv"))
    a = ap.parse_args()
    data, n_items, n_rows = build()
    h = hashlib.sha256(data).hexdigest()
    print("items %d, prediction rows %d, sha256 %s" % (n_items, n_rows, h))
    if a.check:
        ok = h == FROZEN_SHA256
        print("CHECK", "PASS: reproduces the frozen predictions file" if ok else "FAIL: differs from " + FROZEN_SHA256)
        sys.exit(0 if ok else 1)
    with open(a.out, "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()
