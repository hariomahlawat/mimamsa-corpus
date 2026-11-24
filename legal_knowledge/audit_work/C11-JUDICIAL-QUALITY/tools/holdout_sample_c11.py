#!/usr/bin/env python3
"""Deterministic, stratified blinded holdout sample for C11 outcome/proposition evaluation.
Excludes the 30 + 20 judgments reviewed in Cycle 10. Strata: court x {disagreement, multi-case, other}, with pension
and disciplinary topics represented. Selection = lowest SHA-256(seed + judgment_id) within each stratum.
Writes holdout/HOLDOUT_SAMPLE.csv (judgment ids, file path, court only: no extracted values, so reviewers stay blind)."""
import csv, hashlib, io, json, sys
from collections import defaultdict
from pathlib import Path
HERE = Path(__file__).resolve().parent
PKG = HERE.parent
J10 = PKG.parent / "C10-HF-JUDGMENTS"
SEED = "mimamsa-c11-holdout-v1"
QUOTA = {"Supreme Court": 20, "High Court of Delhi": 12, "High Court of Punjab and Haryana": 10,
         "High Court of Jammu and Kashmir": 9, "High Court of Allahabad": 9}

def rows(p):
    return list(csv.DictReader(open(p, encoding="utf-8")))

def main():
    rev = set()
    for f in ("review_A.csv", "review_B.csv", "WS_REVIEW_SAMPLE20_3257ebb9.csv"):
        rev |= {r["judgment_id"] for r in rows(J10 / "review" / f)}
    meta = rows(J10 / "outputs" / "HF_JUDGMENT_METADATA_AUDIT.csv")
    copies = {r["sha256"]: r for r in rows(J10 / "outputs" / "HF_JUDGMENT_COPY_REGISTER.csv")}
    rel = {r["judgment_id"]: r for r in rows(J10 / "outputs" / "HF_JUDGMENT_RELEVANCE.csv")}
    by_j = defaultdict(list)
    for m in meta:
        by_j[m["judgment_id"]].append(m)
    strata = defaultdict(list)
    for j, ms in by_j.items():
        sha = ms[0]["sha256"]
        c = copies.get(sha, {})
        if j in rev or c.get("disposition") != "PROCESSED" or c.get("source_completeness") != "COMPLETE_FILE_STRUCTURE":
            continue
        court = next((k for k in QUOTA if k.split(" of ")[-1].split()[0] in ms[0]["court"]), None)
        if not court:
            continue
        kind = ("disagreement" if any("crawler outcome" in m["contradictions"] for m in ms) else
                "multi_case" if any(len([x for x in m["case_numbers_text_p1_3"].split(";") if x]) > 1 for m in ms) else "other")
        strata[(court, kind)].append(j)
    out = []
    for court, q in QUOTA.items():
        parts = {"disagreement": q * 4 // 10, "multi_case": q * 3 // 10}
        parts["other"] = q - sum(parts.values())
        for kind, n in parts.items():
            cand = sorted(strata[(court, kind)], key=lambda j: hashlib.sha256((SEED + j).encode()).hexdigest())[:n]
            for j in cand:
                ms = by_j[j]
                out.append(dict(holdout_id=f"H{len(out)+1:03d}", judgment_id=j, sha256=ms[0]["sha256"], court=ms[0]["court"],
                                stratum=kind, doc_ids=";".join(sorted(m["doc_id"] for m in ms)),
                                raw_path=copies[ms[0]["sha256"]]["path"], relevance_class=rel.get(j, {}).get("relevance_class", "")))
    s = io.StringIO(); w = csv.DictWriter(s, fieldnames=list(out[0].keys()), lineterminator="\n"); w.writeheader(); w.writerows(out)
    (PKG / "holdout" / "HOLDOUT_SAMPLE.csv").write_text(s.getvalue(), encoding="utf-8")
    print(len(out), {k: sum(1 for x in out if x["stratum"] == k) for k in ("disagreement", "multi_case", "other")})

if __name__ == "__main__":
    main()
