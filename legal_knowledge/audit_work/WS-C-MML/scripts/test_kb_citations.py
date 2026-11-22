#!/usr/bin/env python3
"""Regression check for kb_citations.py (review fix 2026-11-22, PR #20 Codex findings). Stdlib; run from repo root:
    python3 legal_knowledge/audit_work/WS-C-MML/scripts/test_kb_citations.py
Exits non-zero on any failure. Kept inside WS-C-MML (tests/ is under the WS-D lease)."""
import csv, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent; W = HERE.parent; ROOT = W.parents[2]
sys.path.insert(0, str(HERE))
import kb_citations as K

recs = {json.loads(l)["id"]: json.loads(l) for l in (ROOT / "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
ids = set(recs)
fails = []


def check(cond, msg):
    if not cond:
        fails.append(msg)


p = lambda i: K.parse(recs[i], ids)
# (1) letter suffixes
check(p("ADM-007")["ar"] == ["15A"], f"ADM-007 r15-A -> {p('ADM-007')['ar']}")
check(p("ADM-008")["ar"] == ["13A"], f"ADM-008 r13-A -> {p('ADM-008')['ar']}")
check("169A" in p("CM-038")["aa"], f"CM-038 169A missing: {p('CM-038')['aa']}")
check("169A" in p("CM-CL-11")["aa"], f"CM-CL-11 169A missing: {p('CM-CL-11')['aa']}")
# (2) list continuation
check(p("SC03")["ar"] == ["23", "24"], f"SC03 -> {p('SC03')['ar']}")
check("23" in p("HCE-029")["ar"] and "22" in p("HCE-029")["ar"] and "182" in p("HCE-029")["ar"], f"HCE-029 -> {p('HCE-029')['ar']}")
check("181" in p("COI-032")["ar"], f"COI-032 -> {p('COI-032')['ar']}")
# unchanged controls
check(p("KB-003")["aa"] == ["79", "80", "81", "82"] and p("KB-003")["ar"] == ["22"], "KB-003 control changed")
check(p("EV-001")["aa"] == ["133"] and p("EV-001")["ar"] == ["177", "182"], "EV-001 control changed")
check(p("CIV-006")["aa"] == ["121"], "CIV-006 control changed (V8-S01 must not yield s.01)")
# (3) short case titles recognised
for i, key in (("SC13", "P S Gill"), ("CM-009", "Vishav Priya Singh"), ("CM-009", "Randhir Singh"), ("CM-SC-05", "Prithi Pal Singh Bedi")):
    check(p(i)["case_pattern"] and key in [k for k, _, _ in p(i)["case_names"]], f"{i}: case '{key}' not detected")
# inventory: never FULL while a case reference is unresolved
inv = {r["record_id"]: r for r in csv.DictReader(open(W / "kb658_source_coverage_inventory.csv", encoding="utf-8"))}
for i in ("SC13", "CM-009", "CM-SC-05"):
    check(inv[i]["coverage_state"] != "FULL", f"{i} still FULL")
for r in inv.values():
    if r["coverage_state"] == "FULL" and ("CASE_NAME_WITHOUT_CODE" in r["broken_or_unresolved_flags"] or "PLAIN_CASE" in r["broken_or_unresolved_flags"]):
        fails.append(f"{r['record_id']} FULL with unresolved case reference")
check("HCE-029" in inv and "23" in inv["HCE-029"]["ar_rules"].split(";"), "HCE-029 r.23 missing in inventory")
xw = list(csv.DictReader(open(W / "mml_provision_crosswalk.csv", encoding="utf-8")))
check(any(r["provision"] == "r.23" and "HCE-029" in r["kb_record_ids_new"].split(";") for r in xw), "HCE-029 missing from r.23 crosswalk")
check(len(inv) == 658, "inventory row count != 658")
print("FAIL\n" + "\n".join(fails) if fails else "OK test_kb_citations: all checks passed")
sys.exit(1 if fails else 0)
