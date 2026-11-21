"""Stage 'validate': every metadata, section and relation record against its schema, plus
cross-checks the schemas cannot express. Any error fails the run."""
from __future__ import annotations

import hashlib
import json

from .common import Paths
from .schemas import errors


def run(paths: Paths, check_files: bool = True) -> dict:
    errs: list[str] = []
    doc_ids: set[str] = set()
    counts = {"documents": 0, "sections": 0, "relations": 0}

    for path in sorted(paths.meta.glob("*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        counts["documents"] += 1
        errs += [f"meta/{path.name}: {e}" for e in errors("document", rec)]
        if rec.get("doc_id") != path.stem:
            errs.append(f"meta/{path.name}: doc_id {rec.get('doc_id')!r} does not match the file name")
        doc_ids.add(rec.get("doc_id"))
        if check_files:
            raw = paths.raw_file(rec["raw_path"])
            if not raw.exists():
                errs.append(f"meta/{path.name}: raw file missing: {rec['raw_path']}")
            elif hashlib.sha256(raw.read_bytes()).hexdigest() != rec["sha256"]:
                errs.append(f"meta/{path.name}: raw file does not match its sha256")
            if rec.get("text_path") and not (paths.data.parent / rec["text_path"]).exists():
                errs.append(f"meta/{path.name}: text file missing: {rec['text_path']}")

    section_ids: set[str] = set()
    for path in sorted(paths.sections.glob("*/*.json")):
        rec = json.loads(path.read_text(encoding="utf-8"))
        counts["sections"] += 1
        errs += [f"sections/{path.parent.name}/{path.name}: {e}" for e in errors("section", rec)]
        if rec.get("section_id") != f"{path.parent.name}#{path.stem}":
            errs.append(f"sections/{path.parent.name}/{path.name}: section_id does not match the path")
        if rec.get("parent_doc_id") not in doc_ids:
            errs.append(f"sections/{path.parent.name}/{path.name}: parent {rec.get('parent_doc_id')!r} has no metadata")
        section_ids.add(rec.get("section_id"))

    known = doc_ids | section_ids
    rel_path = paths.data / "relations.jsonl"
    if rel_path.exists():
        for i, line in enumerate(rel_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            rel = json.loads(line)
            counts["relations"] += 1
            errs += [f"relations.jsonl:{i}: {e}" for e in errors("relation", rel)]
            if rel.get("source_doc_id") not in known:
                errs.append(f"relations.jsonl:{i}: unknown source {rel.get('source_doc_id')!r}")
            if rel.get("target_doc_id") and rel["target_doc_id"] not in known:
                errs.append(f"relations.jsonl:{i}: unknown target {rel['target_doc_id']!r}")
    for d in sorted(doc_ids):
        rec = json.loads((paths.meta / f"{d}.json").read_text(encoding="utf-8"))
        if rec.get("parent_doc_id") and rec["parent_doc_id"] not in doc_ids:
            errs.append(f"meta/{d}.json: parent_doc_id {rec['parent_doc_id']!r} has no metadata")
    return {**counts, "errors": errs}
