#!/usr/bin/env python3
"""Combine the automated SC case-number proposals with the independent documentary review (Fable 5.2).
Every one of the 368 records gets one application status; the review reading takes precedence over the parser.
  APPLY_CANDIDATE_REVIEWED_CORRECT      reviewer read the page; proposal equals it
  APPLY_CANDIDATE_USE_REVIEWER_READING  reviewer corrected the proposal (PARTLY_CORRECT); use reviewer_normalised
  DO_NOT_APPLY_UNRESOLVED               reviewer UNVERIFIABLE, or a source-level conflict needing the official record
  APPLY_CANDIDATE_UNREVIEWED_CONFIRMED  parser CONFIRMED, not in any review sample, no risk flag
  RECHECK_LOWER_COURT_TYPE_IN_HOST      parser CONFIRMED, unreviewed, host list holds a lower-court style type (RP/OA/TA/MA without parent):
                                        the shape of the Baksish Ahmad error found by the review
Nothing is applied: every status is a proposal awaiting owner approval.  python -I -B scnum_reconcile_c11.py [--check]"""
import argparse, csv, io, json, re, sys
from collections import Counter
from pathlib import Path
HERE = Path(__file__).resolve().parent
PKG = HERE.parent
LOWER = re.compile(r"(?:^|;)\s*(?:RP|OA|TA|MA|UNK)-", re.I)


def build():
    props = list(csv.DictReader(open(PKG / "outputs" / "SC_CASE_NUMBER_PROPOSALS.csv", encoding="utf-8")))
    rev = {r["doc_id"]: r for r in csv.DictReader(open(PKG / "review" / "SCNUM_INDEPENDENT_REVIEW.csv", encoding="utf-8"))}
    assert len(props) == 368
    out = []
    for p in props:
        r = rev.get(p["doc_id"])
        if r:
            v = r["verdict"].upper()
            st = ("APPLY_CANDIDATE_REVIEWED_CORRECT" if v == "CORRECT" else
                  "APPLY_CANDIDATE_USE_REVIEWER_READING" if v.startswith("PARTLY") else "DO_NOT_APPLY_UNRESOLVED")
            if st == "APPLY_CANDIDATE_USE_REVIEWER_READING" and not r["reviewer_normalised"].strip():
                st = "DO_NOT_APPLY_UNRESOLVED"
            value = r["reviewer_normalised"] if st == "APPLY_CANDIDATE_USE_REVIEWER_READING" else p["host_case_numbers_normalised"] if st.startswith("APPLY") else ""
        elif p["classification"].startswith("CONFIRMED"):
            st = "RECHECK_LOWER_COURT_TYPE_IN_HOST" if LOWER.search(p["host_case_numbers_normalised"]) else "APPLY_CANDIDATE_UNREVIEWED_CONFIRMED"
            value = p["host_case_numbers_normalised"] if st.startswith("APPLY") else ""
        else:
            st, value = "DO_NOT_APPLY_UNRESOLVED", ""
        out.append(dict(doc_id=p["doc_id"], judgment_id=p["judgment_id"], sha256=p["sha256"], parser_classification=p["classification"],
                        parser_value=p["host_case_numbers_normalised"], review_sample=(r or {}).get("sample_set", ""),
                        review_verdict=(r or {}).get("verdict", ""), reviewer_value=(r or {}).get("reviewer_normalised", ""),
                        reviewer_note=((r or {}).get("note", ""))[:300], application_status=st, proposed_value=value,
                        status="PROPOSAL_NOT_APPLIED_OWNER_APPROVAL_REQUIRED"))
    s = io.StringIO(); w = csv.DictWriter(s, fieldnames=list(out[0].keys()), lineterminator="\n"); w.writeheader(); w.writerows(out)
    summ = dict(records=len(out), application_status=dict(sorted(Counter(x["application_status"] for x in out).items())),
                reviewed=sum(1 for x in out if x["review_sample"]),
                review_precision={"CONFIRMED_FROM_SOURCE": "14/14 (one-sided 95% lower bound 80.7%)",
                                  "CONFIRMED_MULTIPLE_CONNECTED": "35/36 (one-sided 95% lower bound 87.5%)",
                                  "uncertain_48": "24 correct, 23 partly correct, 0 wrong, 1 unverifiable"})
    return {"SC_CASE_NUMBER_REVIEWED_STATUS.csv": s.getvalue(), "SC_CASE_NUMBER_REVIEWED_SUMMARY.json": json.dumps(summ, indent=1, sort_keys=True) + "\n"}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    out = build(); d = PKG / "review"
    if a.check:
        bad = [k for k, v in out.items() if not (d / k).is_file() or (d / k).read_text(encoding="utf-8") != v]
        print("CHECK FAILED: " + ", ".join(bad) if bad else f"reconciliation reproduces ({len(out)} files)"); return 1 if bad else 0
    for k, v in out.items():
        (d / k).write_text(v, encoding="utf-8")
    print(out["SC_CASE_NUMBER_REVIEWED_SUMMARY.json"]); return 0


if __name__ == "__main__":
    sys.exit(main())
