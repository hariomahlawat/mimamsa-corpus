"""python -m pipeline <stage>

  records    metadata + section records + relations from what the crawler saved
  extract    text from PDFs (data/text/), page markers kept
  split      section records cut from the PDF, for Acts with no section records at the source
  ocr        Tesseract OCR for documents marked needs_ocr (slow; resumable; not part of `all`)
  validate   every record against its schema; exit 1 on any error
  report     data/manifest.csv and reports/phase2_report.md
  correspondence  official new-code/old-code comparison tables into data/correspondence/
  relevance  keyword pass and statute references for judgments; reports/relevance.csv
  all        records, extract, split, correspondence, relevance, validate, report

Each stage reads the previous stage's output and can be re-run alone.
"""
from __future__ import annotations

import argparse
import json
import sys

from . import correspondence, extract, judgments, ocr, records, report, split_pdf, validate
from .common import ROOT, Paths


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m pipeline")
    p.add_argument("stage", choices=["records", "extract", "split", "correspondence", "relevance", "ocr", "validate", "report", "all"])
    p.add_argument("--root", default=str(ROOT))
    p.add_argument("--only", action="append", metavar="DOC_ID", help="extract/ocr: limit to these documents")
    p.add_argument("--workers", type=int, default=4, help="ocr: pages read in parallel")
    p.add_argument("--redo", action="store_true", help="extract/ocr: process again even if already done")
    args = p.parse_args(argv)
    paths = Paths.default(args.root)
    extra: dict = {}
    rc = 0
    if args.stage in ("records", "all"):
        res = records.build_indiacode(paths)
        extra["problems"] = res["problems"]
        print("records:", json.dumps(res, indent=1))
    if args.stage in ("extract", "all"):
        res = extract.run(paths, args.only, redo=args.redo and args.stage == "extract")
        extra["extract_errors"] = res["errors"]
        print("extract:", json.dumps(res, indent=1))
    if args.stage in ("split", "all"):
        res = split_pdf.run(paths, args.only if args.stage == "split" else None)
        extra["split"] = res
        for doc_id, st in res.items():
            print(f"split: {doc_id}: {st['found']} of {st['toc_sections']} sections in its table, "
                  f"{st['amendment_notes']} amendment notes, " + ("written" if st["written"] else f"NOT written: {st['reason']}"))
    if args.stage in ("correspondence", "all"):
        res = correspondence.run(paths)
        extra["correspondence"] = res
        for key, st in res.items():
            print(f"correspondence: {key}: {st['rows']} rows" + (f" ({st['reason']})" if st.get("reason") else ""))
    if args.stage in ("relevance", "all"):
        res = judgments.run(paths)
        extra["relevance"] = res
        print("relevance:", json.dumps(res))
    if args.stage == "ocr":
        res = ocr.run(paths, args.only, workers=args.workers, redo=args.redo)
        print("ocr:", json.dumps(res, indent=1, ensure_ascii=False))
        if res.get("error") or res.get("errors"):
            rc = 1
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
