#!/usr/bin/env python3
"""C13-A0 exclusion manifests: every spent set (holdouts, references, dev and review sets of C10, C11 and C12).

Each source file is scanned for judgment ids (J-<16 hex>), file sha256 values, corpus doc_ids and C11 edge /
treatment-candidate ids; every hit is mapped to its judgment_key (C11 identity register, all copies of a judgment).
A judgment named in ANY spent set is excluded from EVERY fresh C13 holdout (H-OUT, H-HOLD, H-REL). Spent sets may
be used as development data only. The source files and their sha256 are recorded so the manifest can be audited.

  python -I -B c13_exclusions.py [--check]
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from c13_common import (AW, C10, C11, C12, OUT, read_csv, render_csv, render_json, sha256_file,  # noqa: E402
                        write_or_check, argv_check)

SPENT_SETS = [
    # (set_id, description, [files relative to legal_knowledge/audit_work])
    ("C10_REVIEW", "C10 independent review samples (review A/B, WS sample 20, REVIEW_SAMPLE)", [
        "C10-HF-JUDGMENTS/review/review_A.csv", "C10-HF-JUDGMENTS/review/review_B.csv",
        "C10-HF-JUDGMENTS/review/WS_REVIEW_SAMPLE20_3257ebb9.csv", "C10-HF-JUDGMENTS/review/REVIEW_SAMPLE.csv"]),
    ("C11_HOLDOUT_56", "C11 outcome holdout (56) with its ground truth and evaluation rows", [
        "C11-JUDICIAL-QUALITY/holdout/HOLDOUT_SAMPLE.csv", "C11-JUDICIAL-QUALITY/holdout/ground_truth_A.csv",
        "C11-JUDICIAL-QUALITY/holdout/ground_truth_B.csv",
        "C11-JUDICIAL-QUALITY/evaluation/HOLDOUT_EVALUATION_ROWS.csv"]),
    ("C11_DEV_AND_REVIEW", "C11 extraction dev rows and C11 review item sets (extraction, recall, relations)", [
        "C11-JUDICIAL-QUALITY/extraction/outputs/DEV_EVALUATION_ROWS.csv",
        "C11-JUDICIAL-QUALITY/review/fable_review_extraction_c11_items.csv",
        "C11-JUDICIAL-QUALITY/review/fable_review_extraction_c11_recall_rows.csv",
        "C11-JUDICIAL-QUALITY/review/fable_review_relations_c11_rows.csv",
        "C11-JUDICIAL-QUALITY/review/fable_review_relations_c11_v11_rows.csv",
        "C11-JUDICIAL-QUALITY/relations/outputs/REVIEW_REMEASURE_C11.csv"]),
    ("C12_V3_HOLDOUT_150", "C12 outcome V3 holdout (150)", ["C12-CONSOLIDATION/holdout_v3/HOLDOUT_V3_SAMPLE.csv"]),
    ("C12_HOLDINGS_REFERENCE_30", "C12 holdings reference (30 SC judgments)", [
        "C12-CONSOLIDATION/holdings_reference/SELECTION.csv",
        "C12-CONSOLIDATION/holdings_reference/REFERENCE_HOLDINGS.csv"]),
    ("C12_EXTRACTOR_DEV", "C12 extractor V3 dev gold and dev evaluation / spot-check / batch copies", [
        "C12-CONSOLIDATION/extractor_v3/tools/dev_gold_v3.json",
        "C12-CONSOLIDATION/extractor_v3/outputs/DEV_EVALUATION_V3_ROWS.csv",
        "C12-CONSOLIDATION/extractor_v3/outputs/DEV_SPOTCHECK_V3.csv",
        "C12-CONSOLIDATION/extractor_v3/outputs/DEV_BATCH_COPIES_V3.csv"]),
    ("C12_HOLDINGS_DEV", "C12 holdings dev predictions ids, dev evaluation, precision hand-check, eval adjudication", [
        "C12-CONSOLIDATION/holdings/outputs/dev_predictions/DEV_IDS.txt",
        "C12-CONSOLIDATION/holdings/outputs/DEV_EVALUATION_ROWS.csv",
        "C12-CONSOLIDATION/holdings/outputs/PRECISION_HANDCHECK_C12.csv",
        "C12-CONSOLIDATION/holdings_eval/ADJUDICATION_SAMPLE.csv",
        "C12-CONSOLIDATION/holdings_eval/predictions/ids.txt"]),
]

JID = re.compile(r"\bJ-[0-9a-f]{16}\b")
SHA = re.compile(r"\b[0-9a-f]{64}\b")
EDGE = re.compile(r"\b(?:E|TC|SL)-[0-9a-f]{12}\b")
TOKEN = re.compile(r"\b[a-z0-9][a-z0-9.\-]{12,}[a-z0-9]\b")


def identity_maps():
    reg = read_csv(C11 / "identity" / "outputs" / "JUDGMENT_IDENTITY_REGISTER.csv")
    sha2key = {r["sha256"]: r["judgment_key"] for r in reg}
    jid2key = {r["judgment_id_c10"]: r["judgment_key"] for r in reg}
    doc2key = {}
    for r in reg:
        for d in r["doc_ids"].split(";"):
            if d:
                doc2key[d] = r["judgment_key"]
    for r in read_csv(C10 / "outputs" / "HF_JUDGMENT_METADATA_AUDIT.csv"):
        doc2key.setdefault(r["doc_id"], sha2key.get(r["sha256"]))
    edge2key = {}
    rel = C11 / "relations" / "outputs"
    for r in read_csv(rel / "CASE_CITATION_GRAPH.csv"):
        edge2key[r["edge_id"]] = jid2key.get(r["source_judgment_id"])
    for r in read_csv(rel / "TREATMENT_CANDIDATES.csv"):
        edge2key[r["candidate_id"]] = jid2key.get(r["source_judgment_id"])
    for r in read_csv(rel / "STATUTE_JUDGMENT_LINKS.csv"):
        edge2key[r["link_id"]] = jid2key.get(r["judgment_id"])
    return sha2key, jid2key, doc2key, edge2key


def scan(text, maps):
    sha2key, jid2key, doc2key, edge2key = maps
    hits = defaultdict(set)   # judgment_key -> {matched_by}
    for m in JID.findall(text):
        if m in jid2key:
            hits[jid2key[m]].add("judgment_id")
    for m in SHA.findall(text):
        if m in sha2key:
            hits[sha2key[m]].add("file_sha256")
    for m in EDGE.findall(text):
        if edge2key.get(m):
            hits[edge2key[m]].add("c11_edge_id")
    for m in TOKEN.findall(text):
        if doc2key.get(m):
            hits[doc2key[m]].add("doc_id")
    return hits


def build(maps=None):
    maps = maps or identity_maps()
    rows, summary, union = [], {"sets": {}}, defaultdict(set)
    for set_id, desc, files in SPENT_SETS:
        keys = defaultdict(set)
        srcs = []
        for rel in files:
            p = AW / rel
            text = p.read_text(encoding="utf-8")
            if p.suffix == ".json":   # dev gold: keys are judgment ids
                text += "\n" + "\n".join(json.loads(text).keys())
            h = scan(text, maps)
            srcs.append({"file": rel, "sha256": sha256_file(p), "judgments_matched": len(h)})
            for k, how in h.items():
                keys[k] |= {f"{rel.rsplit('/', 1)[-1]}:{x}" for x in how}
        for k in sorted(keys):
            rows.append(dict(set_id=set_id, judgment_key=k, matched_in=";".join(sorted(keys[k]))))
            union[k].add(set_id)
        summary["sets"][set_id] = {"description": desc, "judgments": len(keys), "sources": srcs}
    summary["union_judgments_excluded"] = len(union)
    summary["rule"] = ("A judgment_key named in any spent set is excluded from every C13 fresh holdout "
                       "(H-OUT-C13, H-HOLD-C13, H-REL-C13). Spent sets may be used as development data only.")
    union_rows = [dict(judgment_key=k, spent_sets=";".join(sorted(v))) for k, v in sorted(union.items())]
    return {"exclusions/SPENT_SET_MEMBERS.csv": render_csv(rows),
            "exclusions/EXCLUDED_JUDGMENTS.csv": render_csv(union_rows),
            "exclusions/EXCLUSION_SUMMARY.json": render_json(summary)}


def load_excluded():
    """judgment_key -> spent set ids, from the committed manifest."""
    return {r["judgment_key"]: r["spent_sets"] for r in read_csv(OUT / "exclusions" / "EXCLUDED_JUDGMENTS.csv")}


def main():
    return write_or_check(build(), OUT, argv_check(), "c13_exclusions")


if __name__ == "__main__":
    sys.exit(main())
