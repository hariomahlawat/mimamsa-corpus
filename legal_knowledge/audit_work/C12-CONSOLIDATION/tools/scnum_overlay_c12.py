#!/usr/bin/env python3
"""C12 Workstream I: versioned metadata-correction overlay for Supreme Court case numbers.

Originals are never modified (crawler data/meta at ad77758d stays as it is). The overlay records, per doc_id, the
proposed case_numbers with evidence and review provenance:
  * the 73 APPLY_CANDIDATE_REVIEWED_CORRECT records (C11 independent review read the page; value = proposal);
  * the 24 reviewer-reading and 4 lower-court-recheck records ONLY where the C12 independent page-image
    reconfirmation is CONFIRMED or NEEDS_CHANGE (value = reconfirmed value);
  * nothing for UNRESOLVED records or the 266 unreviewed candidates (not applied in bulk).
Entries not in TYPE-NUMBER-YEAR form are kept verbatim in `unnormalised_references`, never forced into a code.
  python -I -B scnum_overlay_c12.py [--check]"""
import csv, json, re, sys
from pathlib import Path
PKG = Path(__file__).resolve().parent.parent
C11 = PKG.parent / "C11-JUDICIAL-QUALITY" / "scnum"
NORM = re.compile(r"^[A-Z]+(?:DIARY)?-\d+[A-Z]?-\d{4}$")


def split(v):
    good, other = [], []
    for x in [t.strip() for t in re.split(r";", v or "") if t.strip()]:
        (good if NORM.match(x) else other).append(x)
    return good, other


def main():
    status = {r["doc_id"]: r for r in csv.DictReader(open(C11 / "review" / "SC_CASE_NUMBER_REVIEWED_STATUS.csv", encoding="utf-8"))}
    recon = {r["doc_id"]: r for r in csv.DictReader(open(PKG / "metadata" / "SCNUM_RECONFIRMATION_C12.csv", encoding="utf-8"))}
    out, tally = [], {}
    for d, s in sorted(status.items()):
        st = s["application_status"]
        if st == "APPLY_CANDIDATE_REVIEWED_CORRECT":
            val, basis = s["proposed_value"], "C11 independent page review: CORRECT"
        elif d in recon and recon[d]["verdict"] in ("CONFIRMED", "NEEDS_CHANGE"):
            val, basis = recon[d]["reconfirmed_value"], f"C12 independent page-image reconfirmation: {recon[d]['verdict']}"
        else:
            tally["NOT_APPLIED_" + (recon[d]["verdict"] if d in recon else st)] = tally.get("NOT_APPLIED_" + (recon[d]["verdict"] if d in recon else st), 0) + 1
            continue
        good, other = split(val)
        if not good:
            tally["NOT_APPLIED_NO_NORMALISED_VALUE"] = tally.get("NOT_APPLIED_NO_NORMALISED_VALUE", 0) + 1
            continue
        tally["STAGED"] = tally.get("STAGED", 0) + 1
        out.append(dict(overlay_version="C12-v1", doc_id=d, judgment_id=s["judgment_id"], sha256=s["sha256"], field="case_numbers",
                        original_value=[], proposed_value=good, unnormalised_references=other, evidence_basis=basis,
                        parser_value=s["parser_value"], status="CORRECTION_STAGED_DERIVATIVE_OVERLAY_ORIGINAL_UNCHANGED",
                        verification="AI_DOCUMENTARY_REVIEW_NOT_LEGAL_VALIDATION"))
    text = "".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in out)
    summ = json.dumps(dict(records=len(status), tally=dict(sorted(tally.items()))), indent=1, sort_keys=True) + "\n"
    files = {"SC_CASE_NUMBER_OVERLAY_C12.jsonl": text, "SC_CASE_NUMBER_OVERLAY_SUMMARY.json": summ}
    d = PKG / "metadata"
    if "--check" in sys.argv[1:]:
        bad = [k for k, v in files.items() if (d / k).read_text(encoding="utf-8") != v]
        print("CHECK FAILED" if bad else "overlay reproduces"); return 1 if bad else 0
    for k, v in files.items():
        (d / k).write_text(v, encoding="utf-8")
    print(summ); return 0


if __name__ == "__main__":
    sys.exit(main())
