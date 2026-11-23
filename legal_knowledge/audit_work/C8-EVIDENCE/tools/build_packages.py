"""C8 approval-ready packages (Gazette package 1, Supreme Court package 2) built from the committed C8 evidence registers.

PREPARATION ONLY. Each candidate gets its own evidence summary and an UNSIGNED proposed decision template. The template
deliberately contains no decision, no decided_by and no entry digest (the digest is computed only when the owner's
decision is entered at conversion), so it can never pass AUTH-LEDGER record checks as it stands. Nothing here is an owner
approval, a ledger entry or a BIND line, and nothing changes legal status.

  python build_packages.py           write GAZETTE-T1/APPROVAL_PACKAGE.md, SC-T2/APPROVAL_PACKAGE.md and the per-candidate templates
  python build_packages.py --check   fail if any committed output differs from a rebuild

The limitations line of each template is copied from the register column (GAZETTE-T1/eligibility_recommendations.csv
'limitations'; SC-T2/sc_copy_evidence_register.csv 'limitations'), which carries the decisive limitations (review
5212a95b, B-02). No text is truncated (B-08)."""
import argparse, csv, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # C8-EVIDENCE
AW = ROOT.parent
G, C = ROOT / "GAZETTE-T1", ROOT / "SC-T2"


def rows(p):
    with open(p, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


TEMPLATE = """# Proposed decision record — UNSIGNED TEMPLATE ({cid})

**Not a decision.** This template is prepared evidence for the owner. It carries no decision, no `decided_by`, and no
entry digest, and it fails AUTH-LEDGER record checks as written. If the owner decides, a real record `D-vNNNN*.md` is
written at conversion with the ledger `entry_id=sha256:entry_digest`, alongside a separate independent review record
`R-vNNNN*.md`, in a reviewed PR; the version becomes effective only after a verified BIND line.

- candidate: {cid}
- sha256: {sha}
- source_id: {src}
- proposed_class: {cls}
- recommendation (preparer, not a decision): {rec}
- evidence file: {evf}
- C8 page checks: {checks}
- limitations to be recorded verbatim in the entry: {lim}
- {ctx_label}: {ctx}
- scope if decided: AUTHENTICATION_PROVENANCE_ONLY
- legal_approval: NOT_GIVEN
- decision: <owner to complete: APPROVED | WITHHELD | REJECTED>
- decided_by: <owner to complete; a person, not an AI agent>
- date: <owner to complete>
"""


def gazette():
    rec = {r["tranche_id"]: r for r in rows(G / "eligibility_recommendations.csv")}
    ev = {r["tranche_id"]: r for r in rows(G / "gazette_evidence_register.csv")} if (G / "gazette_evidence_register.csv").is_file() else {}
    checks = {}
    for r in rows(G / "page_image_checks_c8.csv"):
        checks.setdefault(r["tranche_id"], []).append(f"{r['check_id']}({r['identity_result']})")
    out, files = [], {}
    out.append("# Package 1: Gazette tranche 1 — approval-ready evidence (NOT approved, NOT active)\n")
    out.append("Built by `../tools/build_packages.py` from `eligibility_recommendations.csv`, `page_image_checks_c8.csv` and the evidence files. "
               "Page readings are AI-agent readings with render hashes (not human-confirmed). Synthetic approvals were used only in temporary "
               "simulation directories. No owner decision exists; the per-candidate files in `approval_package/` are UNSIGNED templates.\n")
    out.append("| Candidate | sha256 | Recommendation | C8 checks | Evidence |\n| --- | --- | --- | --- | --- |")
    for tid in sorted(rec):
        r = rec[tid]
        evf = f"evidence/{tid}.md"
        out.append(f"| {tid} | `{r['sha256'][:12]}` | {r['recommendation']} | {', '.join(checks.get(tid, []))} | `{evf}` |")
        files[f"approval_package/{tid}_proposed_decision_TEMPLATE.md"] = TEMPLATE.format(
            cid=tid, sha=r["sha256"], src=r["source_id"], cls="PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE", rec=r["recommendation"],
            evf=evf, checks=", ".join(checks.get(tid, [])) or "none", lim=r["limitations"],
            ctx_label="contradiction-register entries for this candidate (contradiction_register_c8.csv)", ctx=ev.get(tid, {}).get("contradictions") or "none")
    counts = {}
    for r in rec.values():
        counts[r["recommendation"]] = counts.get(r["recommendation"], 0) + 1
    out.append("\n**Counts:** " + "; ".join(f"{k}: {v}" for k, v in sorted(counts.items())) + ".\n")
    out.append("**Owner decisions needed before conversion:** per-candidate decision (APPROVED / WITHHELD / REJECTED); P-D2 for T1-19; "
               "for T1-20, whether a copy whose embedded CMS signature fails verification may be primary at all (recommended: no, until an "
               "independent official copy is obtained under an approved acquisition). Conversion is a separate reviewed PR followed by a BIND line.\n")
    return "\n".join(out) + "\n", files


def court():
    reg = {r["copy_id"]: r for r in rows(C / "sc_copy_evidence_register.csv")}
    sim = json.loads((C / "exact_anchor_simulation.json").read_text(encoding="utf-8"))
    v0 = sim["version0"]["exact_anchor_case_count"]
    keep_partial = {"C5-SRC-J-SC-2005-NAVJOT~C1": "classification depends on P-D3; first-class record SOURCE_LOCATED only; case record lacks date and case number",
                    "C5-SRC-J-SC-2026-MULLIKOTE~C1": "file holds two versions (pp.1-31 CORRECTED, pp.32-62 unmarked); any anchor must name pp.1-31; WS-B OI-03 open"}
    judis = {"C5-SRC-J-SC-1987-RANJIT-THAKUR~C1", "C5-SRC-J-SC-1990-SN-MUKHERJEE~C1", "C5-SRC-J-SC-2005-NAVJOT~C1"}
    out, files = [], {}
    out.append("# Package 2: Supreme Court tranche 2 — approval-ready evidence (NOT approved, NOT active)\n")
    out.append(f"Built by `../tools/build_packages.py` from `sc_copy_evidence_register.csv` and `exact_anchor_simulation.json` "
               f"({sim['label']}). Exact-anchor cases at version 0: {v0}; all 8 jointly: {sim['joint_all_8']['summary']['exact_anchor_case_count']}. "
               "Identity readings are AI-agent readings with render hashes. No judicial authentication entry is active, and provenance never "
               "makes a holding current or binding.\n")
    out.append("| Copy | Identity | Anchors alone (v0 → after) | Depends on | Preparer recommendation |\n| --- | --- | --- | --- | --- |")
    for cid in sorted(reg):
        r = reg[cid]
        s = sim["single"].get(cid, {})
        after = s.get("summary", {}).get("exact_anchor_case_count", "n/a") if isinstance(s.get("summary"), dict) else "n/a"
        dep = []
        if cid in judis:
            dep.append("P-D3 (JUDIS rendition class)")
        dep.append("B2 (CONFIRMED image check for anchor-creating entries)")
        recm = ("KEEP PARTIAL: " + keep_partial[cid]) if cid in keep_partial else (
            "READY FOR OWNER CONSIDERATION after P-D3 and P-B" if cid in judis else "READY FOR OWNER CONSIDERATION after P-B")
        if after == v0:
            recm += " (no case record: no anchor effect)"
        out.append(f"| {cid} | {r['identity_result']} | {v0} → {after} | {'; '.join(dep)} | {recm} |")
        files[f"approval_package/{cid.replace('~', '_')}_proposed_decision_TEMPLATE.md"] = TEMPLATE.format(
            cid=cid, sha=r["sha256"], src=r["source_id"], cls="PRIMARY_OFFICIAL_COURT_COPY", rec=recm,
            evf="sc_copy_evidence_register.csv; evidence/", checks=r["page_check_ids"], lim=r["limitations"],
            ctx_label="discrepancies recorded by C8 (sc_copy_evidence_register.csv 'discrepancies')", ctx=r["discrepancies"])
    out.append("\n**Owner decisions needed:** P-D3 (JUDIS renditions), P-B (B2), and per-copy decisions. Corpus corrections proposed by "
               "the evidence (case numbers, neutral citations, the N S Yadav name, the Rajbir C1 identity string) are separate correction "
               "proposals and are not applied.\n")
    return "\n".join(out) + "\n", files


def outputs():
    res = {}
    for base, fn in ((G, gazette), (C, court)):
        text, files = fn()
        res[base / "APPROVAL_PACKAGE.md"] = text
        for rel, t in files.items():
            res[base / rel] = t
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    res = outputs()
    if a.check:
        bad = [str(p.relative_to(ROOT)) for p, t in res.items() if not p.is_file() or p.read_text(encoding="utf-8") != t]
        if bad:
            print(f"C8 PACKAGE CHECK FAILED: {bad[:5]}", file=sys.stderr)
            return 1
        print(f"C8 packages reproduce ({len(res)} files)")
        return 0
    for p, t in res.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(t, encoding="utf-8")
    print(f"wrote {len(res)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
