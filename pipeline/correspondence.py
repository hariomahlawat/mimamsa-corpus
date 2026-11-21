"""Stage 'correspondence': read official comparison tables (new code <-> old code) into records.

Input : reference PDFs listed in sources.yaml with a `correspondence` block naming the two Acts
        and the order of the table's four columns.
Output: data/correspondence/<key>.jsonl, one row per table row, cells as printed, plus the section
        numbers read from the cells. Rows are `extracted`: a person should verify them before the
        app relies on a mapping.
"""
from __future__ import annotations

import json
import re

import pdfplumber
import yaml

from .common import SCHEMA_VERSION, Paths
from .records import section_key

HEADER_WORDS = re.compile(r"^(sections?|subsections?|sections?/|subject|summary of compar\w+|bnss?|bsa|ipc|crpc|iea|ons)$", re.I)


def clean(cell: str | None) -> str:
    return re.sub(r"\s+", " ", (cell or "").replace(" ", " ")).strip()


def clean_ref(cell: str | None) -> str:
    """'2(r )' -> '2(r)', '103 (1)' -> '103(1)'. Cells naming several sections are left as printed."""
    ref = clean(cell)
    if re.match(r"^\d", ref) and not re.search(r"[&,]|\band\b", ref):
        ref = re.sub(r"\s+\)", ")", re.sub(r"\s*\(\s*", "(", ref))
    return ref


def section_numbers(ref: str) -> list[str]:
    """Section numbers in a reference cell: '68 & 69' -> ['68','69']; '2(1)(t)' -> ['2']; 'New' -> []."""
    bare = re.sub(r"\([^)]*\)", " ", ref)
    out = []
    for n in re.findall(r"(?<![A-Za-z0-9])(\d{1,3}[A-Z]{0,2})(?![a-z0-9])", bare):
        if n not in out:
            out.append(n)
    return out


def read_table(pdf_path, columns: list[str]) -> list[dict]:
    """Rows as {new, old, subject, summary, page}; continuation rows are folded into the row above."""
    rows: list[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        for pno, page in enumerate(pdf.pages, 1):
            for table in page.extract_tables():
                for raw in table:
                    if len(raw) != len(columns):
                        continue
                    cell = {name: raw[i] for i, name in enumerate(columns)}
                    new, old = clean_ref(cell["new"]), clean_ref(cell["old"])
                    subject, summary = clean(cell["subject"]), clean(cell["summary"])
                    if all(not c or HEADER_WORDS.match(c) for c in (new, old, subject, summary)) or \
                            (HEADER_WORDS.match(subject or "x") and HEADER_WORDS.match(summary or "x")):
                        continue                                   # table header
                    if not new and not old and rows:               # continuation of the row above
                        for k, v in (("subject", subject), ("summary", summary)):
                            if v:
                                rows[-1][k] = (rows[-1][k] + " " + v).strip()
                        continue
                    if not new:
                        continue
                    rows.append({"new": new, "old": old, "subject": subject, "summary": summary, "page": pno})
    return rows


def run(paths: Paths, config_path=None) -> dict:
    config_path = config_path or paths.root / "config" / "sources.yaml"
    if not config_path.exists():
        return {}
    cfg = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    results: dict = {}
    out_dir = paths.data / "correspondence"
    for src in cfg.get("sources", {}).values():
        for doc in src.get("documents") or []:
            spec = doc.get("correspondence")
            if not spec:
                continue
            meta_path = paths.meta / f"{doc['doc_id']}.json"
            if not meta_path.exists():
                results[spec["key"]] = {"rows": 0, "reason": f"{doc['doc_id']} is not in the corpus (not downloaded?)"}
                continue
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            rows = read_table(paths.raw_file(meta["raw_path"]), spec["columns"])
            records = []
            for r in rows:
                m = re.match(r"^(\d{1,3}[A-Z]{0,2})", r["new"])
                is_new = bool(re.search(r"\bnew\b", r["old"], re.I))
                records.append({
                    "schema_version": SCHEMA_VERSION,
                    "new_doc_id": spec["new"], "new_ref_raw": r["new"], "new_section": m.group(1) if m else None,
                    "old_doc_id": spec["old"], "old_ref_raw": r["old"] or None,
                    "old_sections": [] if is_new else section_numbers(r["old"]), "is_new": is_new,
                    "subject": r["subject"] or None, "summary": r["summary"] or None,
                    "source_doc_id": doc["doc_id"], "page": r["page"], "confidence": "extracted"})
            out_dir.mkdir(parents=True, exist_ok=True)
            with (out_dir / f"{spec['key']}.jsonl").open("w", encoding="utf-8") as fh:
                for rec in records:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

            def known(doc_id: str, number: str) -> bool:
                return (paths.sections / doc_id / f"{section_key(number)}.json").exists()
            have_new = (paths.sections / spec["new"]).exists()
            have_old = (paths.sections / spec["old"]).exists()
            new_secs = {r["new_section"] for r in records if r["new_section"]}
            old_secs = {n for r in records for n in r["old_sections"]}
            results[spec["key"]] = {
                "rows": len(records), "source_doc_id": doc["doc_id"], "new": spec["new"], "old": spec["old"],
                "new_provisions": sum(r["is_new"] for r in records),
                "rows_without_old_reference": sum(1 for r in records if not r["is_new"] and not r["old_sections"]),
                "new_sections_named": len(new_secs), "old_sections_named": len(old_secs),
                "new_sections_not_in_corpus": sorted(n for n in new_secs if not known(spec["new"], n)) if have_new else None,
                "old_sections_not_in_corpus": sorted(n for n in old_secs if not known(spec["old"], n)) if have_old else None,
            }
    return results
