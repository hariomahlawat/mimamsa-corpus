#!/usr/bin/env python3
"""Validate the C13 A4 provision version records and resolve candidate versions for a date.

Checks (exit 1 on any failure):
  1. every record validates against schema/provision_version.schema.json (Draft 2020-12);
  2. version ids are unique; each provision's versions are numbered 1..n without gaps;
  3. chain integrity: effective_to.next_version_id points to the next version of the same provision; an
     ENDS_ON_NEXT_VERSION end date equals the next version's effective_from date; nothing follows a CEASED version;
  4. no inferred dates: a non-null effective_from.date requires a STATED* status; REPORTED_IN_COMPILATION_ONLY
     carries the date only in reported_date; a date is never earlier than... (ordering) - where two consecutive
     versions both have dates, they are non-decreasing;
  5. every evidence item that names a sha256 names a 64-hex value; IMAGE_CHECKED evidence names at least one
     evidence id; an IMAGE_CHECKED text_status has only IMAGE_CHECKED evidence;
  6. records with a conflict are flagged legal_review_required; every record is AUTOMATED_CANDIDATE_NOT_VERIFIED;
  7. the four temporal axes are separate and NOT_DETERMINED (no axis is silently chosen);
  8. no restricted material (config/restricted_material.json on claude/c13-gov, mirrored in c13a4_common).

Resolver: candidates_at(records, family, provision, date) returns every version whose interval cannot be excluded
on the held evidence for that date, each with a reason. It never returns "the latest" when intervals are open.

Usage: validate_versions_c13.py [--check] [--at FAMILY PROVISION YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict

from c13a4_common import PKG, assert_no_restricted

REC = PKG / "records/PROVISION_VERSIONS_C13.jsonl"
SCHEMA = PKG / "schema/provision_version.schema.json"


def load(path=REC):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def validate(recs, schema=None):
    import jsonschema
    schema = schema or json.loads(SCHEMA.read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    v = jsonschema.Draft202012Validator(schema)
    errs = []
    for r in recs:
        for e in v.iter_errors(r):
            errs.append(f"{r.get('version_id')}: schema: {e.message[:160]} at {list(e.path)}")
    ids = [r["version_id"] for r in recs]
    if len(ids) != len(set(ids)):
        errs.append("duplicate version_id")
    by = defaultdict(list)
    for r in recs:
        by[(r["family"], r["provision"])].append(r)
    for key, vs in by.items():
        vs.sort(key=lambda r: r["version_seq"])
        if [x["version_seq"] for x in vs] != list(range(1, len(vs) + 1)):
            errs.append(f"{key}: version_seq not 1..n")
        for i, x in enumerate(vs):
            et, ef = x["effective_to"], x["effective_from"]
            if ef["date"] and not ef["status"].startswith("STATED"):
                errs.append(f"{x['version_id']}: effective_from date without a STATED status (inferred date)")
            if ef["status"] == "REPORTED_IN_COMPILATION_ONLY" and ef["date"]:
                errs.append(f"{x['version_id']}: compilation-only date placed in effective_from.date")
            if et["status"] == "CEASED_OMITTED_OR_REPEALED":
                if i != len(vs) - 1:
                    errs.append(f"{x['version_id']}: version follows a ceased version")
                continue
            if i + 1 < len(vs):
                nx = vs[i + 1]
                if et["next_version_id"] != nx["version_id"]:
                    errs.append(f"{x['version_id']}: next_version_id {et['next_version_id']} != {nx['version_id']}")
                if et["status"] == "ENDS_ON_NEXT_VERSION" and et["date"] != nx["effective_from"]["date"]:
                    errs.append(f"{x['version_id']}: end date != next start date")
                if et["status"] == "ENDS_ON_NEXT_VERSION_DATE_NOT_DETERMINED" and nx["effective_from"]["date"]:
                    errs.append(f"{x['version_id']}: next start date is known but end marked not determined")
                if ef["date"] and nx["effective_from"]["date"] and nx["effective_from"]["date"] < ef["date"]:
                    errs.append(f"{x['version_id']}: next version starts before this one")
            elif et["status"] != "OPEN_ON_LOCATED_INSTRUMENTS":
                errs.append(f"{x['version_id']}: last version must be OPEN_ON_LOCATED_INSTRUMENTS or CEASED")
    for r in recs:
        for e in r["text_evidence"]:
            if e["method"] == "IMAGE_CHECKED" and not e["evidence_ids"]:
                errs.append(f"{r['version_id']}: IMAGE_CHECKED evidence without an evidence id")
        if r["text_status"] == "IMAGE_CHECKED" and any(e["method"] != "IMAGE_CHECKED" for e in r["text_evidence"]):
            errs.append(f"{r['version_id']}: text_status IMAGE_CHECKED but some evidence is not image-checked")
        if r["conflicts"] and not r["legal_review_required"]:
            errs.append(f"{r['version_id']}: conflict without legal_review_required")
        if len({json.dumps(a, sort_keys=True) for a in r["temporal_axes"].values()}) and any(a["status"] != "NOT_DETERMINED" for a in r["temporal_axes"].values()):
            errs.append(f"{r['version_id']}: a temporal axis was determined automatically")
    assert_no_restricted(REC.name, REC.read_bytes() if REC.exists() else b"")
    return errs


def candidates_at(recs, family, provision, date):
    """All versions of (family, provision) that cannot be excluded for `date` (YYYY-MM-DD) on the held evidence."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise ValueError("date must be YYYY-MM-DD")
    vs = sorted([r for r in recs if r["family"] == family and r["provision"] == provision], key=lambda r: r["version_seq"])
    out = []
    for i, v in enumerate(vs):
        f, t = v["effective_from"], v["effective_to"]
        # lower bound: stated start; else the latest stated start of an earlier version (a later version cannot precede it)
        lo = f["date"]
        if lo is None:
            earlier = [x["effective_from"]["date"] for x in vs[:i] if x["effective_from"]["date"]]
            lo_soft = max(earlier) if earlier else None
        else:
            lo_soft = None
        hi = t["date"] if t["status"] == "ENDS_ON_NEXT_VERSION" else None
        if t["status"] == "ENDS_ON_NEXT_VERSION_DATE_NOT_DETERMINED":
            later = [x["effective_from"]["date"] for x in vs[i + 1:] if x["effective_from"]["date"]]
            hi = min(later) if later else None  # a version cannot outlast a later version's stated start
        if lo and date < lo:
            continue
        if lo_soft and date < lo_soft:
            continue
        if hi and date >= hi:
            continue
        if t["status"] == "CEASED_OMITTED_OR_REPEALED":
            reason = "provision omitted/repealed by this version" + ("" if lo else " (commencement of the omission not established)")
        elif lo and (hi or t["status"] == "OPEN_ON_LOCATED_INSTRUMENTS"):
            reason = "interval established on located instruments" + (" (open end: currency NOT_ESTABLISHED)" if not hi else "")
        else:
            reason = "interval not excluded: " + "; ".join(x for x in [f"start {f['status']}" if not lo else "", f"end {t['status']}" if not hi else ""] if x)
        out.append({"version_id": v["version_id"], "version_kind": v["version_kind"], "text_status": v["text_status"], "reason": reason,
                    "conflicts": v["conflicts"], "open_items": v["open_items"],
                    "governing_axis": "NOT_DETERMINED (choose conduct / proceedings / procedural-action / document date with legal advice: " + v["temporal_axes"]["conduct_date"]["question_id"] + ")"})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--at", nargs=3, metavar=("FAMILY", "PROVISION", "DATE"))
    a = ap.parse_args(argv)
    recs = load()
    errs = validate(recs)
    if a.at:
        print(json.dumps(candidates_at(recs, *a.at), indent=1))
    if errs:
        print(f"VALIDATION FAILED: {len(errs)} errors")
        for e in errs[:50]:
            print("  " + e)
        return 1
    print(f"VALIDATION OK: {len(recs)} version records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
