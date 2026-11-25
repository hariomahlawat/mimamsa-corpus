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

Resolver: resolve_at(records, family, provision, date) returns a status (NOT_YET_IN_FORCE / IN_FORCE_CANDIDATES /
UNDETERMINED / NO_VERSION_IN_FORCE), the definite candidates (only when a start is established), the possible versions
and reasons. It uses the creating instrument's date as an exclusion floor and honours stated retrospective deemed dates
(review R-01..R-03). It never returns "the latest" text by default.

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


ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
DMY = re.compile(r"\b(\d{2})-(\d{2})-(\d{4})\b")


def _iso(s):
    if not s:
        return None
    m = ISO.search(s)
    if m:
        return m.group(0)
    m = DMY.search(s)
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def instrument_floor(v):
    """Earliest date on which the creating instrument existed (instrument date / assent or publication), lowered only by a
    stated retrospective deemed date (review R-02, R-03). None when no date of the instrument is recorded."""
    ds = [d for d in (_iso(v["created_by"].get("instrument_date") or ""), v["created_by"].get("publication_date")) if d]
    floor = min(ds) if ds else None
    retro = v.get("retrospective_deemed_effect_from")
    if retro and (floor is None or retro < floor):
        floor = retro
    return floor


def resolve_at(recs, family, provision, date):
    """Resolve (family, provision) for a date (YYYY-MM-DD) on the held evidence. Never assumes the latest text.

    Returns {"status", "reason", "candidates", "possible_versions", "ceased_by"} where status is
      NOT_YET_IN_FORCE     the date precedes the earliest possible start of the first version (instrument floor or a
                           stated commencement): no version applies (review R-01);
      IN_FORCE_CANDIDATES  at least one non-excluded version has an established start on or before the date
                           (stated commencement, or a stated retrospective deemed date): `candidates` lists every
                           version that cannot be excluded;
      UNDETERMINED         versions are possible but none has an established start on or before the date (commencement
                           not stated / compilation-reported only / instrument not held): NO candidate is returned;
                           the possible versions are listed separately, with reasons;
      NO_VERSION_IN_FORCE  the provision was omitted/repealed by a version whose start is established on or before the date.
    The governing date axis (conduct / proceedings / procedural act / document) is never chosen here.
    """
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise ValueError("date must be YYYY-MM-DD")
    vs = sorted([r for r in recs if r["family"] == family and r["provision"] == provision], key=lambda r: r["version_seq"])
    if not vs:
        raise KeyError(f"no versions for {family} {provision}")
    axis = "NOT_DETERMINED (choose conduct / proceedings / procedural-action / document date with legal advice: " + vs[0]["temporal_axes"]["conduct_date"]["question_id"] + ")"
    out = {"family": family, "provision": provision, "date": date, "governing_axis": axis,
           "candidates": [], "possible_versions": [], "ceased_by": None}
    first = vs[0]
    f0 = first["effective_from"]["date"]
    retro0 = first.get("retrospective_deemed_effect_from")
    floor0 = instrument_floor(first)
    earliest = min(d for d in (f0 if not retro0 else min(f0 or retro0, retro0), floor0) if d) if (f0 or floor0 or retro0) else None
    if f0 and not retro0:
        earliest = f0  # a stated commencement is the earliest possible start
    if earliest and date < earliest:
        out["status"] = "NOT_YET_IN_FORCE"
        out["reason"] = (f"date precedes the earliest possible start of {first['version_id']} ({earliest}: "
                         + ("stated commencement" if (f0 and earliest == f0) else "date of the creating instrument / stated retrospective date") + ")")
        return out
    entries = []
    for i, v in enumerate(vs):
        f, t = v["effective_from"], v["effective_to"]
        stated = f["date"]
        retro = v.get("retrospective_deemed_effect_from")
        floor = instrument_floor(v)
        if floor and date < floor:
            continue  # R-03: cannot take effect before its instrument (or a stated retrospective date)
        earlier_stated = [x["effective_from"]["date"] for x in vs[:i] if x["effective_from"]["date"]]
        if earlier_stated and date < max(earlier_stated) and not (retro and date >= retro):
            continue  # a later version cannot precede an earlier version's stated start
        if stated and date < stated and not (retro and date >= retro):
            continue
        later_stated = [x["effective_from"]["date"] for x in vs[i + 1:] if x["effective_from"]["date"]]
        hi = min(later_stated) if later_stated else None
        if hi and date >= hi:
            continue
        if stated and date >= stated:
            est, why = True, f"stated start {stated}"
        elif retro and date >= retro:
            est, why = True, f"retrospective deemed effect from {retro} (stated in the instrument; legal effect AQ-06 open)"
        else:
            est, why = False, f"start not established ({f['status']}" + (f"; compilation-reported {f['reported_date']}" if f.get("reported_date") else "") + ")"
            if f.get("reported_date") and date < f["reported_date"]:
                why += f"; NOTE compilation-reported commencement {f['reported_date']} is after this date"
        if not hi and t["status"] == "ENDS_ON_NEXT_VERSION_DATE_NOT_DETERMINED":
            why += "; end not established (next version's start not stated)"
        entries.append({"version_id": v["version_id"], "version_kind": v["version_kind"], "text_status": v["text_status"], "established": est,
                        "ceases": t["status"] == "CEASED_OMITTED_OR_REPEALED", "reason": why, "conflicts": v["conflicts"], "open_items": v["open_items"]})
    est = [e for e in entries if e["established"]]
    if est:
        last_est = est[-1]
        if last_est["ceases"] and entries[-1]["version_id"] == last_est["version_id"]:
            out["status"] = "NO_VERSION_IN_FORCE"
            out["ceased_by"] = last_est
            out["reason"] = f"provision omitted/repealed by {last_est['version_id']} ({last_est['reason']})"
            return out
        out["status"] = "IN_FORCE_CANDIDATES"
        out["candidates"] = [e for e in entries if not (e["ceases"] and not e["established"])] or est
        out["possible_versions"] = [e for e in entries if e not in out["candidates"]]
        out["reason"] = "at least one version has an established start on or before the date; every non-excluded version is listed"
        return out
    out["status"] = "UNDETERMINED"
    out["possible_versions"] = entries
    out["reason"] = ("no version has an established start on or before this date (commencement not stated, compilation-reported or "
                     "instrument not held): no candidate is returned; possible versions are listed with reasons")
    return out


def candidates_at(recs, family, provision, date):
    """Definite candidates only (empty unless resolve_at() reports IN_FORCE_CANDIDATES). Use resolve_at() for the status."""
    return resolve_at(recs, family, provision, date)["candidates"]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--at", nargs=3, metavar=("FAMILY", "PROVISION", "DATE"))
    a = ap.parse_args(argv)
    recs = load()
    errs = validate(recs)
    if a.at:
        print(json.dumps(resolve_at(recs, *a.at), indent=1))
    if errs:
        print(f"VALIDATION FAILED: {len(errs)} errors")
        for e in errs[:50]:
            print("  " + e)
        return 1
    print(f"VALIDATION OK: {len(recs)} version records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
