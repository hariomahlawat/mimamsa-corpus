#!/usr/bin/env python3
"""Consolidate PILOT-01 batch into registers, advisor queue and scorecard. Read-only on findings/sources/reviews."""
import csv, collections, glob, json, hashlib
from pathlib import Path

B = Path(__file__).resolve().parent
ROOT = B.parents[2]
load = lambda kind: [x for p in sorted(glob.glob(str(B / kind / "*.json"))) for x in json.load(open(p))]
S, F, R = load("sources"), load("findings"), load("reviews")
man = json.load(open(B / "pilot-manifest.json"))
M = {r["record_id"]: r for r in man["records"]}
fp = [f for f in F if f["workstream"] != "INDEPENDENT_REVIEW"]
blind = [f for f in F if f["workstream"] == "INDEPENDENT_REVIEW"]
rev_by = collections.defaultdict(list)
for r in R: rev_by[r["finding_id"]].append(r)
SEV = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
OUTRANK = ["CONFLICTING_SOURCES", "BLOCKED", "DISCREPANCY", "UNVERIFIED", "NO_ISSUE_FOUND"]

def revs(fid):
    return "; ".join(f'{r["reviewer_id"]}:{r["decision"]}' for r in rev_by.get(fid, [])) or "NOT_REVIEWED"

# ---- per-record examination outcome (worst outcome, highest severity)
per = {}
for rid, m in M.items():
    fs = [f for f in fp if f["record_id"] == rid]
    outs = sorted({f["examination_outcome"] for f in fs}, key=OUTRANK.index)
    sev = min((f["severity"] for f in fs), key=SEV.get) if fs else None
    per[rid] = {"record_id": rid, "kind": m["kind"], "n_findings": len(fs), "worst_outcome": outs[0] if outs else "NOT_EXAMINED",
                "outcomes": "|".join(outs), "highest_severity": sev,
                "agents": "|".join(sorted({f["agent"] for f in fs})),
                "mml_anchor": None, "legal_review_required": any(f["requires_legal_review"] for f in fs),
                "disputed_by_reviewer": any(r["decision"] == "DISPUTES" for f in fs for r in rev_by.get(f["finding_id"], []))}
xw = list(csv.DictReader(open(B / "registers" / "mml_crosswalk_pilot.csv")))
for rid in per:
    st = {r["link_status"] for r in xw if r["record_id"] == rid}
    per[rid]["mml_anchor"] = ("EXACT_PASSAGE" if "EXACT_PASSAGE" in st else "RELATED_PASSAGE" if "RELATED_PASSAGE" in st
                              else "NO_MML_COVERAGE" if st else ("PACKET" if M[rid]["kind"] == "MML_PROVISION" else "N/A"))
with open(B / "record_outcomes.csv", "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=list(next(iter(per.values())).keys())); w.writeheader(); w.writerows(per.values())

# ---- corrections register (proposals only)
with open(B / "registers" / "corrections_register.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["finding_id", "record_id", "agent", "severity", "issue_type", "examination_outcome", "verification_state",
                "claim", "proposed_text", "independent_review", "legal_review_state", "status"])
    for f in sorted(fp, key=lambda f: (SEV[f["severity"]], f["record_id"])):
        if f["examination_outcome"] in ("DISCREPANCY", "CONFLICTING_SOURCES") or f.get("proposed_text"):
            w.writerow([f["finding_id"], f["record_id"], f["agent"], f["severity"], f["issue_type"], f["examination_outcome"],
                        f["verification_state"], f["claim"][:400], (f.get("proposed_text") or "")[:600], revs(f["finding_id"]),
                        f.get("legal_review_state"), "PROPOSAL_NOT_APPLIED"])

# ---- advisor queue
with open(B / "advisor_queue.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["queue_no", "finding_id", "record_id", "severity", "outcome", "claim", "advisor_questions", "independent_review", "decision_required"])
    q = sorted([f for f in fp if f["requires_legal_review"]], key=lambda f: (SEV[f["severity"]], f["record_id"]))
    for n, f in enumerate(q, 1):
        w.writerow([n, f["finding_id"], f["record_id"], f["severity"], f["examination_outcome"], f["claim"][:300],
                    " | ".join(f.get("advisor_questions", []))[:700], revs(f["finding_id"]),
                    "Advisor (not yet nominated): accept / reject / amend proposal; confirm severity"])

# ---- unresolved legal questions register (from advisor questions + standing UQs)
with open(B / "registers" / "unresolved_questions_register.csv", "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["uq_id", "source", "priority", "question"])
    n = 0
    for f in sorted(fp, key=lambda f: SEV[f["severity"]]):
        if f["severity"] in ("P0", "P1") or f["examination_outcome"] in ("CONFLICTING_SOURCES", "BLOCKED"):
            for qx in f.get("advisor_questions", []):
                n += 1; w.writerow([f"UQ-P{n:03d}", f'{f["finding_id"]} ({f["record_id"]})', f["severity"], qx])

# ---- scorecard
c = lambda it, k: dict(collections.Counter(x[k] for x in it))
kb = [p for p in per.values() if p["kind"] == "KB_RECORD"]
src_primary = [s for s in S if s["source_type"] in ("STATUTE", "RULE", "GAZETTE", "REGULATION", "JUDGMENT", "ORDER", "OTHER_PRIMARY")]
hi = [f for f in fp if f["severity"] in ("P0", "P1") or f["verification_state"] == "CONFLICTING"]
dec = collections.Counter(r["decision"] for r in R)
hi_reviewed = [f for f in hi if rev_by.get(f["finding_id"])]
hi_disputed = [f for f in hi if any(r["decision"] == "DISPUTES" for r in rev_by.get(f["finding_id"], []))]
bvf = list(csv.DictReader(open(B / "registers" / "blind_vs_firstpass.csv"))) if (B / "registers" / "blind_vs_firstpass.csv").exists() else []
orig = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in
        ["legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl", "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl"]}
sc = {
    "batch_id": "PILOT-01", "nature": "Structural/process scorecard. NOT a legal accuracy percentage (no advisor-adjudicated reference set yet).",
    "originals_unchanged": orig == {"legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl": man["input_snapshot"]["kb_file_sha256"],
                                    "legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl": man["input_snapshot"]["cases_file_sha256"]},
    "coverage": {"manifest_items": len(M), "items_with_explicit_outcome": sum(1 for p in per.values() if p["n_findings"]),
                 "kb_records": len(kb), "kb_with_outcome": sum(1 for p in kb if p["n_findings"]),
                 "kb_worst_outcome": c(kb, "worst_outcome"), "all_items_worst_outcome": c(per.values(), "worst_outcome"),
                 "kb_mml_anchor": c(kb, "mml_anchor")},
    "findings": {"first_pass": len(fp), "blind": len(blind), "by_outcome": c(fp, "examination_outcome"), "by_severity": c(fp, "severity"),
                 "by_verification_state": c(fp, "verification_state"), "by_agent": c(fp, "agent"),
                 "requires_legal_review": sum(1 for f in fp if f["requires_legal_review"])},
    "sources": {"total": len(S), "by_type": c(S, "source_type"), "by_authenticity": c(S, "authenticity"),
                "primary_with_sha256": sum(1 for s in src_primary if s.get("sha256")), "primary_total": len(src_primary),
                "gazette_originals": sum(1 for s in S if s["source_type"] == "GAZETTE")},
    "independent_review": {"reviews": len(R), "by_decision": dict(dec), "p0_p1_conflict_findings": len(hi),
                           "p0_p1_conflict_reviewed": len(hi_reviewed), "p0_p1_conflict_disputed": len(hi_disputed),
                           "dispute_rate_on_reviewed_high": round(len(hi_disputed) / len(hi_reviewed), 3) if hi_reviewed else None,
                           "blind_vs_firstpass": dict(collections.Counter(r["agreement"] for r in bvf))},
    "legal_review": {"advisor_nominated": False, "advisor_reviewed_findings": 0, "formally_approved": 0},
}
json.dump(sc, open(B / "scorecard.json", "w"), indent=2)
print(json.dumps(sc, indent=1))
