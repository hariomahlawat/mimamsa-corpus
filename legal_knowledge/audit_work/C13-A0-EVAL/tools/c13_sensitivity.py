#!/usr/bin/env python3
"""C13-A0 v1.1: pre-exposed holdout subsets (GA0 review F04, F06). Holdouts are NOT changed.

Categories (a judgment can carry several):
  CURATED_KB_CONTENT            holdout judgment with curated / knowledge-base content (C11 curated 53, C12 curated
                                holdings scope, WS-B holdings register). Developers must not consult that content.
  NEAR_IDENTICAL_SPENT_SIBLING  shingle containment >= 0.90 against a spent judgment, or >= 0.80 with the same decision
                                date (template sibling orders), from the GA0 reviewer's comparison
                                (inputs/neardup_holdout_vs_spent.csv).
  REVIEW_TEXT_EXPOSED           review-scratch text quoting the judgment (including its disposal) was committed to the
                                branch at a4865e76 and remains in git history (confirmation finding C01).
  AUTHOR_DEV_SNIPPET_VIEWED     the A0 author viewed a short cue snippet of the judgment while developing the
                                stratum cue, before the draw (disclosed in EXPOSURE_REGISTER.md).
  CASE_NUMBER_REVIEWED          case numbers independently reviewed in C11 (SCNUM_INDEPENDENT_REVIEW.csv); exposure is
                                limited to case-number fields.
Every headline is reported with and without PRIMARY (every category except CASE_NUMBER_REVIEWED), and the outcome
headline also without CASE_NUMBER_REVIEWED. A pass must hold without PRIMARY (PROTOCOL_C13 v1.1 s.4.4, s.6).

  python -I -B c13_sensitivity.py [--check]
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from c13_common import AW, OUT, PKG, read_csv, render_csv, sha256_file, write_or_check, argv_check  # noqa: E402
from c13_exclusions import identity_maps, scan  # noqa: E402

CURATED_FILES = ["C11-JUDICIAL-QUALITY/curated/CURATED_53_C11.csv",
                 "C12-CONSOLIDATION/holdings/outputs/CURATED_SCOPE_C12.csv",
                 "WS-B-JUDGMENTS/holdings_register.csv"]
SCNUM_FILE = "C11-JUDICIAL-QUALITY/scnum/review/SCNUM_INDEPENDENT_REVIEW.csv"
NEARDUP = PKG / "inputs" / "neardup_holdout_vs_spent.csv"   # GA0 reviewer evidence (keys and scores only)
EVENTS = PKG / "inputs" / "EXPOSURE_EVENTS.csv"            # C01 exposure events (EXPOSURE_REGISTER.md)
PRIMARY = {"CURATED_KB_CONTENT", "NEAR_IDENTICAL_SPENT_SIBLING", "REVIEW_TEXT_EXPOSED", "AUTHOR_DEV_SNIPPET_VIEWED"}
HOLDOUTS = ("H-OUT-C13", "H-HOLD-C13", "H-REL-C13")
DATE = re.compile(r"(\d{4}-\d{2}-\d{2})$")


def holdout_membership():
    mem = defaultdict(set)
    for h in HOLDOUTS:
        for r in read_csv(OUT / "holdouts" / h / "SAMPLE.csv"):
            mem[r["judgment_key"]].add(h)
    for r in read_csv(OUT / "holdouts" / "H-HOLD-C13" / "RESERVE.csv"):
        mem[r["judgment_key"]].add("H-HOLD-C13-RESERVE")
    return mem


def build():
    maps = identity_maps()
    mem = holdout_membership()
    cats = defaultdict(dict)       # key -> {category: evidence}
    for rel in CURATED_FILES:
        for k in scan((AW / rel).read_text(encoding="utf-8"), maps):
            if k in mem:
                cats[k]["CURATED_KB_CONTENT"] = rel.rsplit("/", 1)[-1]
    for k in scan((AW / SCNUM_FILE).read_text(encoding="utf-8"), maps):
        if k in mem:
            cats[k]["CASE_NUMBER_REVIEWED"] = SCNUM_FILE.rsplit("/", 1)[-1]
    for r in read_csv(NEARDUP):
        k, c = r["holdout_key"], float(r["containment"])
        dh, ds = DATE.search(r["holdout_doc"]), DATE.search(r["spent_doc"])
        same_date = bool(dh and ds and dh.group(1) == ds.group(1))
        if k in mem and (c >= 0.90 or (c >= 0.80 and same_date)):
            prev = cats[k].get("NEAR_IDENTICAL_SPENT_SIBLING", "")
            ev = f"{r['spent_key']} containment {c:.3f}{' same date' if same_date else ''}"
            cats[k]["NEAR_IDENTICAL_SPENT_SIBLING"] = (prev + "; " if prev else "") + ev
    for r in read_csv(EVENTS):
        if r["judgment_key"] in mem:
            cats[r["judgment_key"]][r["category"]] = r["evidence"]
    rows = []
    for k in sorted(cats):
        c = cats[k]
        rows.append(dict(judgment_key=k, holdouts=";".join(sorted(mem[k])),
                         categories=";".join(sorted(c)),
                         primary_sensitivity=bool(PRIMARY & set(c)),
                         developer_restriction=("do not consult curated/KB content for this judgment"
                                                if "CURATED_KB_CONTENT" in c else ""),
                         evidence=" | ".join(f"{a}: {b}" for a, b in sorted(c.items()))))
    srcs = "".join(f"# source {p}: {sha256_file(AW / p)}\n" for p in CURATED_FILES + [SCNUM_FILE])
    return {"holdouts/PRE_EXPOSED_SUBSET.csv": render_csv(rows),
            "holdouts/PRE_EXPOSED_SOURCES.txt": srcs + f"# source inputs/neardup_holdout_vs_spent.csv: "
                                                       f"{sha256_file(NEARDUP)}\n# source inputs/EXPOSURE_EVENTS.csv: "
                                                       f"{sha256_file(EVENTS)}\n"}


def load_subset(holdout):
    """judgment_key -> set of categories, for one holdout (reserve items count for H-HOLD)."""
    p = OUT / "holdouts" / "PRE_EXPOSED_SUBSET.csv"
    out = {}
    for r in read_csv(p):
        hs = set(r["holdouts"].split(";"))
        if holdout in hs or (holdout == "H-HOLD-C13" and "H-HOLD-C13-RESERVE" in hs):
            out[r["judgment_key"]] = set(r["categories"].split(";"))
    return out


def main():
    return write_or_check(build(), OUT, argv_check(), "c13_sensitivity")


if __name__ == "__main__":
    sys.exit(main())
