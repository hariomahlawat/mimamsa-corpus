"""python -m pipeline <stage>

  records    metadata + section records + relations from what the crawler saved
  extract    text from PDFs (data/text/), page markers kept
  validate   every record against its schema; exit 1 on any error
  report     data/manifest.csv and reports/phase2_report.md
  all        the four stages in order

Each stage reads the previous stage's output and can be re-run alone.
"""
from __future__ import annotations

import argparse
import json
import sys

from . import extract, records, report, validate
from .common import ROOT, Paths


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m pipeline")
    p.add_argument("stage", choices=["records", "extract", "validate", "report", "all"])
    p.add_argument("--root", default=str(ROOT))
    p.add_argument("--only", action="append", metavar="DOC_ID", help="extract: limit to these documents")
    args = p.parse_args(argv)
    paths = Paths.default(args.root)
    extra: dict = {}
    rc = 0
    if args.stage in ("records", "all"):
        res = records.build_indiacode(paths)
        extra["problems"] = res["problems"]
        print("records:", json.dumps(res, indent=1))
    if args.stage in ("extract", "all"):
        res = extract.run(paths, args.only)
        extra["extract_errors"] = res["errors"]
        print("extract:", json.dumps(res, indent=1))
    if args.stage in ("validate", "all"):
        res = validate.run(paths)
        print(f"validate: {res['documents']} documents, {res['sections']} sections, {res['relations']} relations, "
              f"{len(res['errors'])} error(s)")
        for e in res["errors"][:40]:
            print("  ERROR", e)
        if res["errors"]:
            rc = 1
    if args.stage in ("report", "all"):
        res = report.run(paths, extra)
        print("report:", json.dumps(res), "-> reports/phase2_report.md, data/manifest.csv")
    return rc


if __name__ == "__main__":
    sys.exit(main())
