"""Stage 'report': data/manifest.csv and reports/phase2_report.md from the records on disk."""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict

from .common import Paths

# Supersession cases the brief names, checkable from statute records alone.
KNOWN_CASES = [
    ("act-army-1950#s75", "omitted", "Field punishment (s.75) omitted in 1992"),
    ("act-army-1950#s76", "omitted", "Field punishment (s.76) omitted in 1992"),
    ("act-army-1950#s127", "omitted", "s.127 omitted in 1992"),
]


def run(paths: Paths, extra: dict | None = None) -> dict:
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(paths.meta.glob("*.json"))]
    secs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(paths.sections.glob("*/*.json"))]
    rel_path = paths.data / "relations.jsonl"
    rels = [json.loads(l) for l in rel_path.read_text(encoding="utf-8").splitlines() if l.strip()] \
        if rel_path.exists() else []

    paths.data.mkdir(parents=True, exist_ok=True)
    with (paths.data / "manifest.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["doc_id", "type", "status", "source_url", "sha256", "retrieved_at"])
        for d in docs:
            w.writerow([d["doc_id"], d["doc_type"], d["status"], d["source_url"], d["sha256"], d["retrieved_at"]])

    by_id = {s["section_id"]: s for s in secs}
    per_act: dict[str, Counter] = defaultdict(Counter)
    for s in secs:
        per_act[s["parent_doc_id"]][s["status"]] += 1
    children: dict[str, Counter] = defaultdict(Counter)
    for d in docs:
        if d.get("parent_doc_id"):
            children[d["parent_doc_id"]][d["doc_type"]] += 1
    acts = [d for d in docs if d["doc_type"] == "act" and not d.get("parent_doc_id")]

    L = ["# Phase 2 report: statutes from India Code", "",
         f"{len(docs)} documents, {len(secs)} section records, {len(rels)} relations.", "",
         "## Acts", "",
         "| Act | Number | Enacted | In force from | Status | Sections | Changed sections | Other documents |",
         "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for a in acts:
        t = per_act[a["doc_id"]]
        changed = ", ".join(f"{v} {k}" for k, v in sorted(t.items()) if k != "in_force") or "none"
        other = ", ".join(f"{v} {k}" for k, v in sorted(children[a["doc_id"]].items())) or "none"
        L.append(f"| {a['title']} | {a['number'] or ''} | {a['issue_date'] or ''} | {a['effective_date'] or ''} | "
                 f"{a['status']} | {sum(t.values())} | {changed} | {other} |")

    L += ["", "## Text extraction", "",
          "| Result | Documents |", "| --- | --- |"]
    c = Counter("needs OCR" if d.get("needs_ocr") else
                ("text, suspect" if d.get("text_quality") == "suspect" else
                 ("text, ok" if d.get("text_method") else "not processed")) for d in docs)
    L += [f"| {k} | {v} |" for k, v in sorted(c.items())]
    for label, pick in (("Needs OCR (no usable text layer; no text kept)", lambda d: d.get("needs_ocr")),
                        ("Text layer present but suspect (kept, flagged)", lambda d: d.get("text_quality") == "suspect"),
                        ("Some pages without text", lambda d: d.get("text_method") and d.get("pages_without_text"))):
        rows = [d for d in docs if pick(d)]
        if rows:
            L += ["", f"### {label}", "", "| doc_id | Type | Pages | Pages without text | Title |",
                  "| --- | --- | --- | --- | --- |"]
            L += [f"| {d['doc_id']} | {d['doc_type']} | {d.get('page_count') or ''} | "
                  f"{len(d.get('pages_without_text') or [])} | {d['title'][:70]} |" for d in rows]
    marked = [d for d in docs if d.get("access_marking")]
    if marked:
        L += ["", "### Access markings found (review before use)", ""]
        L += [f"- {d['doc_id']}: '{d['access_marking']}' ({d['title'][:60]})" for d in marked]

    L += ["", "## Known supersession cases (from the brief)", ""]
    for sid, want, label in KNOWN_CASES:
        s = by_id.get(sid)
        ok = bool(s) and s["status"] == want
        L.append(f"- [{'x' if ok else ' '}] {label}: " + (f"`{sid}` is `{s['status']}`. {s['status_note'] or ''}" if s
                                                         else f"`{sid}` not in the corpus"))
    L += ["- [ ] IPC to BNS from 1 July 2024: BNS, BNSS and BSA are in the corpus; IPC, CrPC and the Evidence Act "
          "are not (no central copy on India Code), so the supersedes edges cannot be built yet.",
          "- [ ] Dharamvir Singh / 2026 ruling / 2023 ruling on writs: judgments, Phase 4."]

    undated = [h for s in secs for h in s["amendment_history"] if h.get("effective_date_raw")]
    L += ["", "## Amendment notes", "",
          f"{sum(len(s['amendment_history']) for s in secs)} amendment notes read from "
          f"{sum(1 for s in secs if s['amendment_history'])} sections; "
          f"{sum(1 for r in rels if r['type'] == 'amended_by')} `amended_by` edges, none resolved to a document yet "
          "(the amending Acts are not in the corpus).", ""]
    if undated:
        L += ["Dates printed in the source that could not be read as dates (kept as printed, not corrected):", ""]
        L += [f"- {s['section_id']}: `{h['effective_date_raw']}`" for s in secs for h in s["amendment_history"]
              if h.get("effective_date_raw")]
    L += ["", "## Not done / gaps", "",
          "- Golden test set: not available to the pipeline, so `reports/golden_coverage.md` is not produced.",
          "- IPC 1860, CrPC 1973, Evidence Act 1872, Regulations for the Army 1987: no source yet.",
          "- Air Force Rules 1969: India Code has the record but no file.",
          "- Chapters are not recorded on section records (the source records carry no chapter field).",
          "- Relations other than `cites` need human verification before the app relies on them."]
    for k in ("problems", "extract_errors"):
        if extra and extra.get(k):
            L += ["", f"## {k.replace('_', ' ').title()}", ""] + [f"- {p}" for p in extra[k]]
    paths.reports.mkdir(parents=True, exist_ok=True)
    (paths.reports / "phase2_report.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    return {"documents": len(docs), "sections": len(secs), "relations": len(rels)}
