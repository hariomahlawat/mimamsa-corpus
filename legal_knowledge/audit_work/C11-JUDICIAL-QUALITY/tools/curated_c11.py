#!/usr/bin/env python3
"""C11 cross-check of the 53 curated cases and the 658 research records against this cycle's verified evidence.

Read-only over the protected originals (cases_53 8b8d53cd…, records_658 9a8f0d19… at staging 21e73b83). Produces
versioned proposals only. Treatment statements used here are ONLY the dossier readings that the independent review of
the relations workstream verified verbatim on the source page (26 of 26); unreviewed treatment proposals are not used.
  python -I -B curated_c11.py --repo <full clone> [--check]"""
import argparse, csv, hashlib, io, json, re, subprocess, sys
from collections import Counter
from pathlib import Path
HERE = Path(__file__).resolve().parent
PKG = HERE.parent
OUT = PKG / "curated"
STG = "21e73b8348767d5f1524167fcec538e1aad6e732"
C10J = PKG.parent / "C10-RECONCILIATION" / "workstreams" / "judicial" / "CURATED_CASE_COPY_STATUS.csv"
PROTECTED = {"legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl": "8b8d53cd1434f7c1c6eaebe77f1fe295fb8b81b755e93276999b4b40b3c8f89a",
             "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl": "9a8f0d193065762ffa987116dc761bcb734008d2a87a946f5591741f5befcfc1"}
# Verified documentary findings (relations dossier; independent review: quotations verbatim on the stated page).
FINDINGS = {
    "Parashotam": ("Parashotam|Parshotam", "Parashotam Dass (3 Judges) para 32 (SCR p.17): Shri Kant Sharma 'does not lay down the correct law and is in conflict with judgments of the Constitution Benches'; the word 'overruled' is not used; para ends with a reservation for 'matters of self-discipline'.", "ADVISER_REVIEW: confirm the record states the High Court writ position after Parashotam, and the self-discipline reservation"),
    "Shri Kant Sharma": (r"Shri\s*Kant\s*Sharma", "See Parashotam para 32. Contrary practice preserved: J&K HC WP(C) 2370/2025 (06-10-2025) still relies on Shri Kant Sharma (pp.2-3) without citing Parashotam.", "ADVISER_REVIEW: any reliance on Shri Kant Sharma must be checked against Parashotam para 32"),
    "Tarsem": ("Tarsem", "Girish Kumar (2026 INSC 149) para 22 (p.11) distinguishes Tarsem ('is of no assistance', 'has no application to the case in hand'); not overruled. Delhi HC W.P.(C) 16771/2025 (11-03-2026) still restricts arrears by Tarsem (p.9 para 27) without citing Girish.", "ADVISER_REVIEW: conflicting treatment; record should not state the 3-year arrears limit as settled without Girish"),
    "Girish": ("Girish", "Girish Kumar (2026 INSC 149, two Judges) held; the reported clarification order of 12-10-2026 is NOT HELD and NOT CITED in the corpus (zero hits for 2026 INSC 1113).", "ACQUIRE_THEN_REVIEW: the clarification order must be obtained (approval required) before relying on Girish's scope"),
    "Ram Avtar": (r"Ram\s*Avtar", "Ram Avtar is NOT HELD; 381 citing judgments by unresolved citation string; content known only through Girish paras 13, 14, 22.", "ACQUIRE_THEN_REVIEW: source not held; record cannot be anchored to the judgment itself"),
    "Dharamvir": (r"Dharam\s*vir", "Dharamvir para 28(ii) (p.27) construes the Entitlement Rules 1982; 352 citing judgments in the corpus.", "CHECK: record should state the Rules version construed (1982) and not apply it to the 2008 Rules without the later authority"),
}


def git(repo, *a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, check=True).stdout


def build(repo):
    raw = {}
    for p, h in PROTECTED.items():
        b = git(repo, "show", f"{STG}:{p}")
        assert hashlib.sha256(b).hexdigest() == h, f"protected original changed: {p}"
        raw[p] = b
    cases = [json.loads(l) for l in raw["legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl"].decode().splitlines() if l.strip()]
    kb = [json.loads(l) for l in raw["legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl"].decode().splitlines() if l.strip()]
    c10 = {r["case_id"]: r for r in csv.DictReader(open(C10J, encoding="utf-8"))}
    scn = list(csv.DictReader(open(PKG / "scnum" / "review" / "SC_CASE_NUMBER_REVIEWED_STATUS.csv", encoding="utf-8")))
    scn_by_sha = {r["sha256"]: r for r in scn}
    prop = {r["doc_id"]: r for r in csv.DictReader(open(PKG / "scnum" / "outputs" / "SC_CASE_NUMBER_PROPOSALS.csv", encoding="utf-8"))}
    ident = {r["sha256"]: r for r in csv.DictReader(open(PKG / "identity" / "outputs" / "JUDGMENT_IDENTITY_REGISTER.csv", encoding="utf-8"))} \
        if (PKG / "identity" / "outputs" / "JUDGMENT_IDENTITY_REGISTER.csv").is_file() else {}
    rows = []
    for c in cases:
        r = c10.get(c["id"], {})
        shas = set(re.findall(r"[0-9a-f]{64}", " ".join(r.get(k, "") for k in ("hf_data_raw_paths", "github_raw_data_paths", "hf_legal_knowledge_paths"))))
        sc = [scn_by_sha[s] for s in sorted(shas) if s in scn_by_sha]
        cm = [prop[x["doc_id"]].get("curated_match", "") for x in sc if x["doc_id"] in prop]
        rows.append(dict(case_id=c["id"], title=c.get("title", "")[:120], c10_held_status=r.get("held_status_c10", ""),
                         c10_official_court_copy=r.get("official_court_copy_held", ""), c10_inconsistencies=r.get("inconsistencies", "")[:200],
                         c11_sc_case_number_status=";".join(sorted({x["application_status"] for x in sc})),
                         c11_sc_case_number_value=";".join(x["proposed_value"] for x in sc if x["proposed_value"])[:200],
                         c11_curated_number_comparison=";".join(sorted(set(cm))),
                         c11_identity_judgment_keys=";".join(sorted({ident[s].get("judgment_key", "") for s in shas if s in ident}))[:200],
                         proposal="NONE" if not sc else "SUPPLY_CASE_NUMBER_FROM_REVIEWED_PROPOSAL_IF_CURATED_EMPTY" if not c.get("case_number") else "COMPARE_ONLY",
                         status="PROPOSAL_NOT_APPLIED"))
    aff = []
    for k in kb:
        t = json.dumps(k, ensure_ascii=False)
        for name, (pat, finding, action) in FINDINGS.items():
            if re.search(pat, t, re.I):
                m = re.search(pat, t, re.I)
                aff.append(dict(record_id=k["id"], module=k.get("module", ""), title=k.get("title", "")[:120], case=name,
                                context=t[max(0, m.start() - 120):m.end() + 160].replace("\\n", " "), verified_finding=finding,
                                proposed_action=action, status="PROPOSAL_NOT_APPLIED_ADVISER_REVIEW"))
    def text(rs):
        s = io.StringIO(); w = csv.DictWriter(s, fieldnames=list(rs[0].keys()), lineterminator="\n"); w.writeheader(); w.writerows(rs); return s.getvalue()
    summ = dict(curated_cases=len(rows), c10_held_status=dict(sorted(Counter(r["c10_held_status"] for r in rows).items())),
                c10_official_court_pdf=sum(1 for r in rows if "YES_OFFICIAL_COURT_PDF" in r["c10_official_court_copy"]),
                c10_any_court_hosted_copy=sum(1 for r in rows if r["c10_official_court_copy"].startswith("YES")),
                with_c11_sc_case_number_proposal=sum(1 for r in rows if r["c11_sc_case_number_status"]),
                research_records=len(kb), affected_record_case_pairs=len(aff), affected_records=len({a["record_id"] for a in aff}),
                affected_by_case=dict(sorted(Counter(a["case"] for a in aff).items())),
                citation_coverage_baseline="983 items: 42 EXACT_ANCHOR / 652 PARTIAL_MATCH / 289 MISSING_EVIDENCE (unchanged: no registration, preservation or authentication occurred in C11)",
                protected_originals={p.split('/')[-1]: h[:8] for p, h in PROTECTED.items()})
    return {"CURATED_53_C11.csv": text(rows), "AFFECTED_RESEARCH_RECORDS.csv": text(aff), "CURATED_C11_SUMMARY.json": json.dumps(summ, indent=1, sort_keys=True) + "\n"}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--repo", required=True); ap.add_argument("--check", action="store_true"); a = ap.parse_args()
    out = build(a.repo)
    if a.check:
        bad = [k for k, v in out.items() if not (OUT / k).is_file() or (OUT / k).read_text(encoding="utf-8") != v]
        print("CHECK FAILED: " + ", ".join(bad) if bad else f"curated cross-check reproduces ({len(out)} files)"); return 1 if bad else 0
    OUT.mkdir(exist_ok=True)
    for k, v in out.items():
        (OUT / k).write_text(v, encoding="utf-8")
    print(out["CURATED_C11_SUMMARY.json"]); return 0


if __name__ == "__main__":
    sys.exit(main())
