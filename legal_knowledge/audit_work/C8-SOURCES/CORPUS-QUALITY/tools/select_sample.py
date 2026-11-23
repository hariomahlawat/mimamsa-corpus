#!/usr/bin/env python3
"""Deterministic high-risk sample selection for C8/WS-E (offline, stdlib, read-only).

Usage: python3 select_sample.py <repo_root> <out_csv> [per_domain=3]

Method (documented in HIGH_RISK_REVIEW.md):
 1. Each KB record is assigned to zero or more of nine legal-consequence domains by
    fixed keyword rules on title+body+references (DOMAINS below).
 2. Risk score = 3*prior_P0P1 + 2*min(missing_evidence_rows,3) + 2*date_dependency
                 + 1*cites_case + 1*status_not_source_reviewed
    prior_P0P1          : count of P0/P1 rows naming the record in PILOT-01 corrections_register
                          or CALIBRATION-02 correction_proposals (known uncertainty)
    missing_evidence    : corpus_crosswalk rows for the record with evidence_status MISSING_EVIDENCE
    date_dependency     : text mentions an amendment year / 2023-2024 transition / 'omitted' /
                          'substituted' / ER or PRA version
    cites_case          : text names a judgment (' v ' pattern or 'INSC')
 3. Top <per_domain> records per domain by (score desc, id asc), de-duplicated in domain order.
 4. Three case records (cases_53) with recorded negative/qualifying later treatment in
    WS-B case_relations.csv are added for the overruling/conflicting-precedent domain.
"""
import csv
import json
import os
import re
import sys
from collections import defaultdict

DOMAINS = [
    ("disciplinary_authority", r"summary (?:punishment|disposal|award)|punishments? without court-martial|(?:AA|Army Act)[^;|]{0,12}(?:§§?|ss?\.? ?)8[0-5]\b|Section 8[0-5]\b|Rule 2[2-6]\b|\br 2[2-6]\b"),
    ("court_martial_jurisdiction", r"court-martial|court martial|\bSCM\b|\bGCM\b|\bDCM\b"),
    ("statutory_complaints", r"statutory complaint|(?:AA|Army Act)[^;|]{0,12}(?:§§?|ss?\.? ?)2[67]\b|Section 2[67] (?:of the Army Act|complaint)"),
    ("administrative_remedies", r"representation|redress|censure|administrative (?:action|termination)|Rule 1[45]\b|\br 1[45]\b|AFT Act[^;|]{0,8}s ?21|§21\(2\)"),
    ("pension_disability", r"pension|disability|invalid|Entitlement Rules|\bER 20|broad-band"),
    ("procedural_time_limits", r"limitation|time bar|(?:AA|Army Act)[^;|]{0,12}(?:§§?|ss?\.? ?)12[23]\b|Section 12[23]\b|s ?22\(|§22|30-day|90-day"),
    ("competing_provisions", r"concurrent jurisdiction|choice between|(?:§§?|ss? ?)12[56]\b|BNSS|\bBNS\b|\bBSA\b|s ?133\b|Evidence Act"),
    ("statutory_amendments", r"omitted|substituted|S\.R\.O|\bSRO\b|Amendment\) (?:Act|Rules)|Act 37 of 1992"),
    ("judicial_overruling", r"overrul|not good law|clarif|later treatment|subsequent treatment|Parashotam|Shri Kant|Girish|Isaac|Dharamvir|Shafhi|Navjot"),
]


def rcsv(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main(repo, out, per=3):
    per = int(per)
    lk = os.path.join(repo, "legal_knowledge")
    aw = os.path.join(lk, "audit_work")
    kb = [json.loads(l) for l in open(os.path.join(lk, "curated_originals/knowledge_base/v0.9/records_658.jsonl"),
                                     encoding="utf-8")]
    corr = rcsv(os.path.join(aw, "PILOT-01/registers/corrections_register.csv"))
    cp2 = rcsv(os.path.join(aw, "CALIBRATION-02/proposals/correction_proposals.csv"))
    xw = rcsv(os.path.join(aw, "SOURCE-LIBRARY-C5/registers/corpus_crosswalk.csv"))
    rel = rcsv(os.path.join(aw, "WS-B-JUDGMENTS/case_relations.csv"))
    prior = defaultdict(int)
    for r in corr:
        if r["severity"] in ("P0", "P1"):
            prior[r["record_id"]] += 1
    for r in cp2:
        if r["severity"] in ("P0", "P1"):
            prior[r["record_id"]] += 1
    miss = defaultdict(int)
    for r in xw:
        if r["knowledge_base_record_id"] and r["evidence_status"] == "MISSING_EVIDENCE":
            miss[r["knowledge_base_record_id"]] += 1
    datedep = re.compile(r"19[5-9]\d|20[0-2]\d|omitted|substituted|transition|ER 20|PRA|commencement", re.I)
    case = re.compile(r" v | INSC ")
    scored = []
    for r in kb:
        txt = r["title"] + " " + r["body"] + " " + r["references"]
        doms = [d for d, p in DOMAINS if re.search(p, txt, re.I)]
        s = (3 * prior[r["id"]] + 2 * min(miss[r["id"]], 3) + 2 * bool(datedep.search(txt))
             + bool(case.search(txt)) + (r["status"] != "SOURCE_REVIEWED_JAG_APPROVAL_PENDING"))
        scored.append((r, doms, s))
    picked, seen = [], set()
    for d, _ in DOMAINS:
        cands = sorted([(s, r["id"], r) for r, doms, s in scored if d in doms], key=lambda x: (-x[0], x[1]))
        n = 0
        for s, i, r in cands:
            if i in seen:
                continue
            picked.append(dict(domain=d, record_id=i, record_type="KB", score=s, prior_P0P1=prior[i],
                               missing_evidence_rows=miss[i], title=r["title"]))
            seen.add(i)
            n += 1
            if n == per:
                break
    neg = re.compile(r"OVERRULED|NOT_GOOD_LAW|QUALIFIED|DISTINGUISHED|LIMITED", re.I)
    tg = sorted({e["to_id"] for e in rel if neg.search(e["relation_or_treatment"]) and e["to_id"].startswith("DCLR")})
    for t in tg[:3]:
        picked.append(dict(domain="judicial_overruling", record_id=t, record_type="CASE", score="", prior_P0P1="",
                           missing_evidence_rows="", title="(cases_53)"))
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(picked[0].keys()))
        w.writeheader()
        w.writerows(picked)
    print(len(picked), "selected")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
