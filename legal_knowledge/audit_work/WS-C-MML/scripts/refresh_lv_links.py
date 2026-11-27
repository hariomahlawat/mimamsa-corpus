#!/usr/bin/env python3
"""Recompute the derived link columns of crosswalk_locator_verification.csv (crosswalk_rows_upgraded,
kb_records_citing, calibration_records) from the current crosswalk, inventory and calibration sample.
Image-check columns are untouched. Stdlib; deterministic. Run from repo root."""
import csv
from pathlib import Path

W = Path(__file__).resolve().parent.parent
xw = list(csv.DictReader(open(W / "mml_provision_crosswalk.csv", encoding="utf-8")))
inv = list(csv.DictReader(open(W / "kb658_source_coverage_inventory.csv", encoding="utf-8")))
cal = {r["record_id"] for r in csv.DictReader(open(W / "calibration_sample_ranked.csv", encoding="utf-8"))}
rows = list(csv.DictReader(open(W / "crosswalk_locator_verification.csv", encoding="utf-8")))
for r in rows:
    pv = r["provision"]; n = pv[2:]; col = "aa_sections" if pv.startswith("s.") else "ar_rules"
    recs = [x["record_id"] for x in inv if n in x[col].split(";")]
    r["crosswalk_rows_upgraded"] = ";".join(x["xw_id"] for x in xw if x["provision"] == pv and x["mml_file"] == "MML 2.pdf")
    r["kb_records_citing"] = ";".join(recs)
    r["calibration_records"] = ";".join(i for i in recs if i in cal)
with open(W / "crosswalk_locator_verification.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print("LV rows refreshed:", len(rows))
