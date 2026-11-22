#!/usr/bin/env python3
"""Build the legal-advisor review packet (markdown + CSV) from the validated PILOT-01 batch. Read-only on findings."""
import csv, glob, json
from pathlib import Path

B = Path(__file__).resolve().parent
L = lambda k: [x for p in sorted(glob.glob(str(B / k / "*.json"))) for x in json.load(open(p))]
S = {s["source_id"]: s for s in L("sources")}
F = L("findings"); R = L("reviews")
disp = {r["finding_id"]: r for r in csv.DictReader(open(B / "post_review" / "post_review_dispositions.csv"))}
recal = {r["finding_id"]: r for r in csv.DictReader(open(B / "post_review" / "severity_recalibration_proposals.csv"))}
pic = list(csv.DictReader(open(B / "registers" / "page_image_checks.csv")))
first = [f for f in F if f["workstream"] != "INDEPENDENT_REVIEW" and f["agent"] != "orchestrator" and f["requires_legal_review"]]
supp = [f for f in F if f["agent"] == "orchestrator"]
SEV = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}

def prov(f):
    fid = f["finding_id"]
    if fid in disp: return disp[fid]["provisional_severity"], disp[fid]["disposition"]
    if fid in recal: return recal[fid]["proposed"], "SEVERITY_RECALIBRATION_PROPOSED"
    return f["severity"], "NO_CHANGE_PROPOSED"

def group(f):
    p, _ = prov(f)
    if f["severity"] == "P0" or p.startswith("P0"): return "A. P0 issues"
    if f["verification_state"] == "CONFLICTING" or f["examination_outcome"] in ("CONFLICTING_SOURCES", "BLOCKED"):
        return "B. Unresolved statutory / source conflicts and blocked authority"
    if f["workstream"] in ("STATUTORY", "PROCEDURE", "MANUAL"): return "C. Other P1 statutory, procedural and manual issues"
    if f["workstream"] == "JUDGMENT": return "D. Judicial holdings and later treatment"
    return "E. Cross-volume consistency"

def src_line(sid):
    s = S.get(sid, {})
    return f'{sid}: {s.get("title","?")[:70]} — {s.get("pinpoint","")} [{s.get("authenticity")}, {s.get("source_type")}]'

items = sorted(first, key=lambda f: (group(f), SEV[f["severity"]], f["record_id"]))
rows, md = [], []
md.append("# Legal-advisor review packet — PILOT-01 (FINAL v1.0, 2026-11-22)\n")
md.append("| Status layer | Meaning | Who | State in this packet |\n|---|---|---|---|\n"
          "| Source verification | A cited source exists and reads as stated at the pinpoint | audit agents | recorded per item |\n"
          "| Independent review / disposition | Adversarial technical challenge by a separate agent; orchestrator's provisional disposition | independent-reviewer A/B/C, orchestrator | recorded per item — **NOT legal approval** |\n"
          "| Substantive legal decision | Professional legal judgement on the proposition and proposed correction | nominated legal advisor | **blank — advisor not nominated** |\n"
          "| Formal validation | Attributable JAG/formal authority approval | formal authority | **none** |\n")
md.append("**Status: FOR ADVISOR DECISION. Advisor not yet nominated. No item is advisor-approved or JAG-validated.** "
          "Agent findings are research proposals; independent-agent reviews are challenges, not legal sign-off. "
          "Originals (658 records, 53 cases, 8 MML files) are unchanged; every correction is a proposal.\n")
md.append("**How to decide each item:** mark one of ACCEPT_PROPOSAL / ACCEPT_WITH_AMENDMENT / REJECT / NEEDS_MORE_EVIDENCE, "
          "confirm or set severity, and answer the listed question(s). Record name, role, date and a signature/approval reference "
          "so that the decision can be entered as a LEGAL_ADVISOR review record (`reviews/*.json`).\n")
md.append(f"Items: {len(items)} queued first-pass findings (P0 first), plus an annex of {len(supp)} supplementary remediation findings. "
          "Page-image evidence: `registers/page_image_checks.csv`. Dispositions: `post_review/`.\n")
cur = None
for n, f in enumerate(items, 1):
    g = group(f)
    if g != cur:
        md.append(f"\n## {g}\n"); cur = g
    p, d = prov(f)
    rv = [r for r in R if r["finding_id"] == f["finding_id"]]
    pics = [x["check_id"] for x in pic if f["finding_id"] in x["related_findings"]]
    md.append(f"### Item {n}: {f['finding_id']} — {f['record_id']} — first pass {f['severity']} / provisional {p}\n")
    md.append(f"- **Outcome / evidence state:** {f['examination_outcome']} / {f['verification_state']}; agent: {f['agent']}")
    md.append(f"- **Record text tested:** {f['original_location']}: “{f['original_text'][:300]}”")
    md.append(f"- **Finding:** {f['claim'][:700]}")
    if f.get("proposed_text"): md.append(f"- **Proposed correction (not applied):** {f['proposed_text'][:500]}")
    md.append(f"- **Temporal scope:** {f.get('temporal_scope') or '—'}")
    md.append("- **Evidence:** " + ("; ".join(src_line(s) for s in f["source_ids"]) or "none"))
    if f.get("contrary_source_ids"): md.append("- **Contrary evidence:** " + "; ".join(src_line(s) for s in f["contrary_source_ids"]))
    if f.get("mml_anchor_ids"): md.append("- **MML anchors (secondary, not proof):** " + ", ".join(f["mml_anchor_ids"][:6]))
    if pics: md.append("- **Page-image checks:** " + ", ".join(pics))
    if f.get("limitations"): md.append("- **Limitations:** " + "; ".join(f["limitations"])[:400])
    md.append("\n> **Independent review and disposition — technical challenge, NOT legal approval**")
    for r in rv: md.append(f"> - {r['review_id']} ({r['reviewer_id']}, {r['reviewer_role']}): **{r['decision']}** — {r['rationale'][:450]}")
    if not rv: md.append("> - No independent review recorded.")
    md.append(f"> - Orchestrator provisional disposition: {d}; provisional severity {p} (proposal only; original finding unchanged)\n")
    md.append("**Substantive legal decision — for the nominated legal advisor (blank)**")
    for q in f.get("advisor_questions", []): md.append(f"- Question: {q}")
    md.append("- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____")
    md.append("- Name / role / date / approval reference: ______________ (entered later as a LEGAL_ADVISOR review record; agents may not fill this)\n")
    rows.append([n, g, f["finding_id"], f["record_id"], f["severity"], p, f["examination_outcome"],
                 "; ".join(f"{r['reviewer_id']}:{r['decision']}" for r in rv), d, " | ".join(f.get("advisor_questions", [])), "", "", "", ""])
md.append("\n## Annex: supplementary remediation findings (orchestrator-authored; independently reviewed by independent-reviewer-C)\n")
for f in supp:
    rv = [r for r in R if r["finding_id"] == f["finding_id"]]
    md.append(f"### {f['finding_id']} — {f['record_id']} — {f['severity']} — {f['examination_outcome']}\n- {f['claim'][:700]}\n"
              f"- Evidence: " + "; ".join(src_line(s) for s in f["source_ids"] + f.get("contrary_source_ids", [])) + "\n")
    md.append("> **Independent review — technical challenge, NOT legal approval**")
    for r in rv: md.append(f"> - {r['review_id']} ({r['reviewer_id']}): **{r['decision']}** — {r['rationale'][:600]}")
    if not rv: md.append("> - Not yet independently reviewed.")
    md.append("\n**Substantive legal decision — for the nominated legal advisor (blank)**")
    for q in f.get("advisor_questions", []): md.append(f"- Question: {q}")
    md.append("- Decision: ☐ ACCEPT_PROPOSAL ☐ ACCEPT_WITH_AMENDMENT ☐ REJECT ☐ NEEDS_MORE_EVIDENCE — severity: ____ — name/role/date/approval ref: ________\n")
(B / "ADVISOR_REVIEW_PACKET.md").write_text("\n".join(md) + "\n", encoding="utf-8")
with open(B / "advisor_review_packet.csv", "w", newline="") as fh:
    w = csv.writer(fh)
    w.writerow(["item", "group", "finding_id", "record_id", "first_pass_severity", "provisional_severity", "outcome",
                "TECHNICAL_independent_review_NOT_legal_approval", "TECHNICAL_orchestrator_disposition_NOT_legal_approval", "questions",
                "LEGAL_advisor_decision", "LEGAL_advisor_severity", "LEGAL_advisor_name_role_date", "LEGAL_approval_reference"])
    w.writerows(rows)
print(len(items), "items;", len(supp), "annex")
from collections import Counter; print(Counter(group(f) for f in items))
