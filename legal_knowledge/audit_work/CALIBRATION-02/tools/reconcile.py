"""CALIBRATION-02 coordinator reconciliation (stdlib, deterministic). Run only after reviews A-D are committed.

Inputs: propositions.csv and reviews/{A,B,C,D}/findings.csv (validated by check_calibration02.py).
Outputs (reconciliation/ and proposals/):
- proposition_matrix.csv: one row per proposition, giving each reviewer's worst severity and evidence states, and the agreement class.
- disagreements.csv: propositions where reviewers' severities differ by >= 1 band with at least one P1/P2, or one
  reviewer marks VERIFIED while another marks UNSUPPORTED/CONTRADICTORY. Escalated, never resolved by majority.
- correction_proposals.csv: every P1/P2 finding with a proposed correction, keeping the original verbatim text, the
  proposed text, the reviewer, the evidence (source sha256 + locator) and corroboration by other reviewers.
  support_status:
    EVIDENCE_SUPPORTED: a held-source sha256 and locator back the correction, and no other reviewer marks the
      same proposition CONTRADICTORY_EVIDENCE;
    EVIDENCE_GAP: the correction rests on missing evidence or no held source;
    DISPUTED_ESCALATED: the proposition is in reviewer DISAGREE (a reviewer positively assessed it with no defect);
    SOURCE_CONFLICT_OPEN: some reviewer records CONTRADICTORY_EVIDENCE between sources for the proposition (kept OPEN).
- record_scorecard.csv and scorecard.json: per-record and overall counts.
Agreement is reported, not used to decide legal questions. The legal-advisor questions are collected verbatim with their reviewer attribution."""
import csv, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

C2 = Path(__file__).resolve().parents[1]
REVIEWERS = ["A", "B", "C", "D"]
RANK = {"P1": 3, "P2": 2, "P3": 1, "NONE": 0}
NEG = {"UNSUPPORTED", "CONTRADICTORY_EVIDENCE"}
GAP = {"SOURCE_NOT_HELD", "HISTORICAL_VERSION_UNRESOLVED"}
POSITIVE = {"VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY"}


def read(p):
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write(p, cols, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main():
    props = read(C2 / "propositions.csv")
    F = {r: read(C2 / "reviews" / r / "findings.csv") for r in REVIEWERS}
    by = defaultdict(lambda: defaultdict(list))
    for r, rows in F.items():
        for x in rows:
            by[x["proposition_id"]][r].append(x)
    matrix, dis, props_out, questions = [], [], [], []
    for p in props:
        pid = p["proposition_id"]
        row = {"record_id": p["record_id"], "proposition_id": pid, "text_verbatim": p["text_verbatim"]}
        sev, states = {}, {}
        for r in REVIEWERS:
            xs = by[pid][r]
            sev[r] = max((x["severity"] for x in xs), key=lambda s: RANK[s]) if xs else "NONE"
            states[r] = sorted({x["evidence_state"] for x in xs})
            row[f"{r}_worst_severity"] = sev[r]
            row[f"{r}_states"] = ";".join(states[r])
        allst = set().union(*states.values())
        legal = allst - {"NOT_A_LEGAL_PROPOSITION", "NOT_YET_REVIEWED"}
        worst = max(sev.values(), key=lambda s: RANK[s])
        raisers = sorted(r for r in REVIEWERS if RANK[sev[r]] >= 2)
        # a reviewer "found it fine" only if it assessed the proposition positively and raised nothing material
        fine = sorted(r for r in REVIEWERS if r not in raisers and any(
            x["evidence_state"] in POSITIVE for x in by[pid][r]) and all(x["severity"] == "NONE" for x in by[pid][r]))
        lower = sorted(r for r in REVIEWERS if r not in raisers and sev[r] == "P3")
        # VERIFIED counts against a negative finding only when it verified the proposition as stated (severity NONE)
        verified_ok = any(x["evidence_state"] == "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE" and x["severity"] == "NONE" for r in REVIEWERS for x in by[pid][r])
        verified_vs_neg = verified_ok and bool(allst & NEG)
        if not legal and not raisers:
            agree = "ALL_NON_LEGAL_OR_OUT_OF_SCOPE"
        elif verified_vs_neg or (raisers and fine):
            agree = "DISAGREE"
        elif raisers and lower and len(raisers) == 1:
            agree = "SEVERITY_SPLIT"
        elif len(raisers) >= 2:
            agree = "CORROBORATED_DEFECT"
        elif len(raisers) == 1:
            agree = "SINGLE_REVIEWER_DEFECT"
        else:
            agree = "NO_MATERIAL_DEFECT_RAISED"
        row["defect_raised_by"] = ";".join(raisers)
        row["assessed_supported_by"] = ";".join(fine)
        row["rated_minor_by"] = ";".join(lower)
        row["worst_severity"] = worst
        row["agreement"] = agree
        row["any_verified"] = "YES" if "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE" in allst else "NO"
        row["any_source_gap"] = "YES" if allst & GAP else "NO"
        matrix.append(row)
        if agree in ("DISAGREE", "SEVERITY_SPLIT"):
            dis.append({"record_id": p["record_id"], "proposition_id": pid,
                        **{f"{r}_worst_severity": sev[r] for r in REVIEWERS},
                        **{f"{r}_states": ";".join(states[r]) for r in REVIEWERS},
                        "kind": agree, "reason": ("VERIFIED vs UNSUPPORTED/CONTRADICTORY" if verified_vs_neg else (f"P1/P2 raised by {';'.join(raisers)}; positively assessed with no defect by {';'.join(fine)}" if fine else f"P1/P2 raised by {';'.join(raisers)}; rated P3 by {';'.join(lower)}")),
                        "disposition": "ESCALATED (not resolved by majority)"})
        for r in REVIEWERS:
            for x in by[pid][r]:
                if x["legal_advisor_question"].strip():
                    questions.append({"record_id": p["record_id"], "proposition_id": pid, "reviewer": r,
                                      "finding_id": x["finding_id"], "question": x["legal_advisor_question"].strip(),
                                      "context_finding": x["finding"][:400]})
                if x["severity"] in ("P1", "P2"):
                    others = {o: by[pid][o] for o in REVIEWERS if o != r}
                    contra = any(y["evidence_state"] == "CONTRADICTORY_EVIDENCE" for ys in by[pid].values() for y in ys)
                    corro = sorted(o for o, ys in others.items() if any(RANK[y["severity"]] >= 2 for y in ys))
                    none_others = sorted(o for o, ys in others.items() if ys and all(y["severity"] == "NONE" and y["evidence_state"] not in ("NOT_A_LEGAL_PROPOSITION",) for y in ys))
                    has_ev = bool(re.fullmatch(r"[0-9a-f]{64}", x["source_sha256"])) and bool(x["locator"].strip())
                    if agree == "DISAGREE":
                        st = "DISPUTED_ESCALATED"
                    elif contra:
                        st = "SOURCE_CONFLICT_OPEN"
                    elif x["proposed_correction"].strip() and has_ev:
                        st = "EVIDENCE_SUPPORTED"
                    else:
                        st = "EVIDENCE_GAP"
                    props_out.append({
                        "proposal_id": f"CP2-{x['finding_id']}", "record_id": p["record_id"], "proposition_id": pid,
                        "original_text_verbatim": p["text_verbatim"], "proposed_text_or_action": x["proposed_correction"],
                        "severity": x["severity"], "defect_class": x["defect_class"], "dimension": x["dimension"],
                        "reviewer": r, "finding_id": x["finding_id"], "source_identity": x["source_identity"],
                        "source_sha256": x["source_sha256"], "locator": x["locator"], "rationale": x["rationale"],
                        "missing_evidence": x["missing_evidence"], "corroborated_by_reviewers": ";".join(corro),
                        "reviewers_marking_no_defect": ";".join(none_others), "support_status": st,
                        "incorporation_state": "PROPOSED_NOT_INCORPORATED (original record unchanged)"})
    mcols = ["record_id", "proposition_id", "text_verbatim"] + [f"{r}_{k}" for r in REVIEWERS for k in ("worst_severity", "states")] + ["worst_severity", "agreement", "defect_raised_by", "assessed_supported_by", "rated_minor_by", "any_verified", "any_source_gap"]
    write(C2 / "reconciliation/proposition_matrix.csv", mcols, matrix)
    write(C2 / "reconciliation/disagreements.csv", ["record_id", "proposition_id"] + [f"{r}_worst_severity" for r in REVIEWERS] + [f"{r}_states" for r in REVIEWERS] + ["kind", "reason", "disposition"], dis)
    pcols = ["proposal_id", "record_id", "proposition_id", "original_text_verbatim", "proposed_text_or_action", "severity", "defect_class", "dimension", "reviewer", "finding_id", "source_identity", "source_sha256", "locator", "rationale", "missing_evidence", "corroborated_by_reviewers", "reviewers_marking_no_defect", "support_status", "incorporation_state"]
    write(C2 / "proposals/correction_proposals.csv", pcols, sorted(props_out, key=lambda d: (d["record_id"], d["proposition_id"], d["proposal_id"])))
    write(C2 / "reconciliation/legal_advisor_questions_raw.csv", ["record_id", "proposition_id", "reviewer", "finding_id", "question", "context_finding"], questions)
    # record scorecard
    recs = defaultdict(list)
    for m in matrix:
        recs[m["record_id"]].append(m)
    rs = []
    for rid in sorted(recs, key=lambda k: [p["calibration_rank"] for p in props if p["record_id"] == k][0].zfill(3)):
        ms = recs[rid]
        legal = [m for m in ms if m["agreement"] != "ALL_NON_LEGAL_OR_OUT_OF_SCOPE"]
        worst = max((m["worst_severity"] for m in ms), key=lambda s: RANK[s])
        fully = bool(legal) and all(m["any_verified"] == "YES" and RANK[m["worst_severity"]] <= 1 and m["any_source_gap"] == "NO" for m in legal)
        if not legal:
            cls = "NO_LEGAL_PROPOSITIONS"
        elif RANK[worst] >= 2:
            cls = "SUBSTANTIVE_DEFECT_FOUND"
        elif fully:
            cls = "FULLY_EVIDENCE_SUPPORTED"
        elif any(m["any_verified"] == "YES" for m in legal):
            cls = "PARTIALLY_SUPPORTED"
        else:
            cls = "UNSUPPORTED_OR_SOURCE_GAP"
        sevs = Counter()
        for r in REVIEWERS:
            for pid in [m["proposition_id"] for m in ms]:
                for x in by[pid][r]:
                    sevs[x["severity"]] += 1
        rs.append({"record_id": rid, "propositions": len(ms), "legal_propositions": len(legal),
                   "worst_severity": worst, "classification": cls,
                   "source_gap_propositions": sum(m["any_source_gap"] == "YES" for m in legal),
                   "disagreements": sum(m["agreement"] in ("DISAGREE", "SEVERITY_SPLIT") for m in ms),
                   "P1_findings": sevs["P1"], "P2_findings": sevs["P2"], "P3_findings": sevs["P3"],
                   "review_state": "REVIEWED (not legally approved)"})
    write(C2 / "reconciliation/record_scorecard.csv", list(rs[0].keys()), rs)
    allf = [x for r in REVIEWERS for x in F[r]]
    sc = {
        "records_reviewed": len(rs), "of": 46, "propositions": len(props),
        "record_classification": dict(sorted(Counter(r["classification"] for r in rs).items())),
        "findings_by_reviewer": {r: len(F[r]) for r in REVIEWERS},
        "findings_by_severity": dict(sorted(Counter(x["severity"] for x in allf).items())),
        "findings_by_evidence_state": dict(sorted(Counter(x["evidence_state"] for x in allf).items())),
        "findings_by_defect_class_P1_P2": dict(sorted(Counter(x["defect_class"] for x in allf if x["severity"] in ("P1", "P2")).items())),
        "proposition_agreement": dict(sorted(Counter(m["agreement"] for m in matrix).items())),
        "disagreements": sum(d["kind"] == "DISAGREE" for d in dis), "severity_splits": sum(d["kind"] == "SEVERITY_SPLIT" for d in dis),
        "correction_proposals": len(props_out),
        "correction_proposals_by_support": dict(sorted(Counter(p["support_status"] for p in props_out).items())),
        "legal_advisor_questions_raw": len(questions),
        "unsupported_propositions": sum(1 for m in matrix if "UNSUPPORTED" in ";".join(m[f"{r}_states"] for r in REVIEWERS)),
        "historical_version_findings": sum(1 for x in allf if x["evidence_state"] == "HISTORICAL_VERSION_UNRESOLVED" or x["defect_class"] == "HISTORICAL_VERSION"),
        "judicial_relationship_findings": sum(1 for x in allf if x["defect_class"] in ("MISLINKED_CASE_OR_CODE",) or (x["dimension"] == "JUDICIAL" and x["defect_class"] == "OMISSION")),
        "cross_volume_findings": sum(1 for x in allf if x["dimension"] == "CROSS_VOLUME" or x["defect_class"] == "CROSS_VOLUME_INCONSISTENCY"),
        "records_with_source_gap_propositions": sum(1 for r in rs if r["source_gap_propositions"]),
        "records_unable_to_progress_missing_primary_sources": sum(1 for r in rs if r["classification"] == "UNSUPPORTED_OR_SOURCE_GAP"),
        "note": "REVIEWED is not LEGAL_APPROVED. Agreement statistics are descriptive; legal disputes are escalated, not decided.",
    }
    (C2 / "reconciliation/scorecard.json").write_text(json.dumps(sc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(sc, sort_keys=True))


if __name__ == "__main__":
    main()
