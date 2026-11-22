#!/usr/bin/env python3
"""Rank KB records for the legal advisor's calibration sample. SELECTION ONLY: no record is audited here.
Deterministic (stdlib). Inputs: kb658_source_coverage_inventory.csv, procedure_gap_conflict_register.csv,
records_658.jsonl (titles/bodies for consequence keywords). Output: calibration_sample_ranked.csv.
Score = consequence + coverage risk + flag risk + near-approval status + not-yet-piloted (weights below)."""
import csv, json, re
from pathlib import Path

HERE = Path(__file__).resolve().parent; W = HERE.parent; ROOT = W.parents[2]
KB = ROOT / "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl"
P0_KW = re.compile(r"\b(punish\w*|custody|arrest|court[- ]martial|sentence|dismiss\w*|cashier\w*|jurisdiction|limitation|"
                   r"confirm\w*|appeal|tribunal|summary of evidence|hearing of charge|caution|detention|imprison\w*|"
                   r"termination|discharge|disability pension|forfeit\w*|fine)\b", re.I)
COV = {"UNRESOLVED": 3, "SOURCE_GAP": 2, "NO_CITATION": 2, "PARTIAL": 1, "FULL": 0}
NEAR = {"SOURCE_REVIEWED_JAG_APPROVAL_PENDING": 2, "JAG_APPROVAL_PENDING": 2}
LOWKIND = {"TEMPLATE", "DRAFTING_AID"}
TARGET, PER_MODULE_MIN, PER_MODULE_CAP = 40, 2, 8


def main():
    recs = {json.loads(l)["id"]: json.loads(l) for l in KB.read_text(encoding="utf-8").splitlines() if l.strip()}
    inv = list(csv.DictReader(open(W / "kb658_source_coverage_inventory.csv", encoding="utf-8")))
    pg_ids = {}
    for g in csv.DictReader(open(W / "procedure_gap_conflict_register.csv", encoding="utf-8")):
        for i in re.findall(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-\d+\b|\bSC\d{2}\b", g["affected_kb_records"]):
            if i in recs:
                pg_ids.setdefault(i, []).append(g["pg_id"])
    rows = []
    for x in inv:
        r = recs[x["record_id"]]
        hits = sorted({m.group(1).lower() for m in P0_KW.finditer(r["title"] + " " + r["body"])})
        comp = {"consequence": 3 if len(hits) >= 2 else (1 if hits else 0),
                "coverage": COV[x["coverage_state"]] if not (x["coverage_state"] == "NO_CITATION" and x["kind"] in LOWKIND) else 0,
                "flags": (2 if "PLACEHOLDER" in x["broken_or_unresolved_flags"] else 0)
                         + (1 if x["broken_or_unresolved_flags"] and "PLACEHOLDER" not in x["broken_or_unresolved_flags"] else 0)
                         + (2 if "SHOWN_OMITTED" in x["info_flags"] else 0) + (1 if x["duplicate_claim_flags"] else 0),
                "conflict_provision": (3 if "23" in x["ar_rules"].split(";") else 0) + (2 if x["record_id"] in pg_ids else 0),
                "near_approval": NEAR.get(x["status_as_recorded"], 0),
                "not_piloted": 1 if x["in_pilot01"] == "NO" else 0,
                "kind_adjust": -1 if x["kind"] in LOWKIND else 0}
        rows.append({"record_id": x["record_id"], "module": x["module"], "kind": x["kind"], "status_as_recorded": x["status_as_recorded"],
                     "record_sha256": x["record_sha256"], "coverage_state": x["coverage_state"], "in_pilot01": x["in_pilot01"],
                     "score": sum(comp.values()), **{"s_" + k: v for k, v in comp.items()},
                     "consequence_keywords": ";".join(hits[:8]), "linked_pg": ";".join(pg_ids.get(x["record_id"], [])),
                     "flags_summary": (x["broken_or_unresolved_flags"] + " " + x["info_flags"]).strip()[:200]})
    pool = sorted([r for r in rows if r["in_pilot01"] == "NO"], key=lambda r: (-r["score"], r["record_id"]))
    chosen, per = [], {}
    for r in pool:
        if len(chosen) >= TARGET:
            break
        if per.get(r["module"], 0) < PER_MODULE_CAP:
            chosen.append(r); per[r["module"]] = per.get(r["module"], 0) + 1
    for m in sorted({r["module"] for r in rows}):
        have = sum(1 for r in chosen if r["module"] == m)
        for r in [p for p in pool if p["module"] == m and p not in chosen][:max(0, PER_MODULE_MIN - have)]:
            r["_fill"] = True; chosen.append(r)
    chosen.sort(key=lambda r: (-r["score"], r["record_id"]))
    out = []
    for i, r in enumerate(chosen, 1):
        r = dict(r); fill = r.pop("_fill", False)
        out.append({"rank": i, "selection_basis": "MODULE_MIN_FILL" if fill else "TOP_SCORE (cap 8 per module)", **r,
                    "audit_state": "NOT_AUDITED (selection only)"})
    with open(W / "calibration_sample_ranked.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    print("selected", len(out), "of", len(pool), "non-pilot records (denominator 658; 25 pilot excluded)")


if __name__ == "__main__":
    main()
