"""CALIBRATION-02 coordinator reconciliation (stdlib, deterministic). Run only after reviews A-D are committed.

Inputs: propositions.csv and reviews/{A,B,C,D}/findings.csv (validated by check_calibration02.py).
Outputs (reconciliation/ and proposals/):
- proposition_matrix.csv: one row per proposition, giving each reviewer's worst severity and evidence states, and the agreement class.
- disagreements.csv: escalations, never resolved by majority:
    DISAGREE: a reviewer raised P1/P2 while another positively assessed the proposition with no defect, or classed it as
      not a legal proposition; or a VERIFIED-as-stated row (severity NONE) faces UNSUPPORTED/CONTRADICTORY;
    SEVERITY_SPLIT: reviewers who rated a defect gave different severities (P1/P2/P3), including corroborated defects.
- correction_proposals.csv: every P1/P2 finding with a proposed correction, keeping the original verbatim text, the
  proposed text, the reviewer, the evidence (source sha256 + locator) and corroboration by other reviewers.
  support_status:
    PRIMARY_EVIDENCE_SUPPORTED: the raising finding's EFFECTIVE status (shared rule, evidence_classification.py) is
      EFFECTIVE_PRIMARY_VERIFIED, i.e. source-specific provenance documented in registers/source_authentication_register.csv;
    AUTHENTICATION_PENDING: the finding claims primary verification but the source's authentication is pending or its
      provenance is unknown (the claim is preserved; it is not counted as primary);
    SECONDARY_EVIDENCE_ONLY: a hash and locator are given but the evidence is secondary (compilation, mirror, derived text);
    EVIDENCE_GAP: the correction rests on missing evidence or no cited source;
  Precedence: SOURCE_CONFLICT_OPEN > DISPUTED_ESCALATED > PRIMARY > AUTHENTICATION_PENDING > SECONDARY > GAP.
- effective_evidence.csv: every finding with its claimed state and its effective status under the shared rule.
    DISPUTED_ESCALATED: the proposition is in reviewer DISAGREE (a reviewer positively assessed it with no defect);
    SOURCE_CONFLICT_OPEN: some reviewer records CONTRADICTORY_EVIDENCE between sources for the proposition (kept OPEN).
- record_scorecard.csv and scorecard.json: per-record and overall counts.
Agreement is reported, not used to decide legal questions. The legal-advisor questions are collected verbatim with their reviewer attribution."""
import csv, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evidence_classification as EC  # noqa: E402  shared rule with check_calibration02.py

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


EV = None  # evidence_classification.Evidence, set in main()


def is_primary_finding(x):
    return EV.counts_as_primary(x)


def main():
    global EV
    EV = EC.Evidence.from_dir(C2)
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
        # a reviewer that classed the proposition as non-legal while another raised P1/P2 is a dissent, not silence
        nonlegal = sorted(r for r in REVIEWERS if r not in raisers and by[pid][r] and all(x["evidence_state"] == "NOT_A_LEGAL_PROPOSITION" for x in by[pid][r]))
        rated = [sev[r] for r in raisers + lower]
        spread = len(set(rated)) > 1
        # VERIFIED counts against a negative finding only when it verified the proposition as stated (severity NONE)
        verified_ok = any(x["evidence_state"] == "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE" and x["severity"] == "NONE" for r in REVIEWERS for x in by[pid][r])
        verified_vs_neg = verified_ok and bool(allst & NEG)
        if not legal and not raisers:
            agree = "ALL_NON_LEGAL_OR_OUT_OF_SCOPE"
        elif verified_vs_neg or (raisers and (fine or nonlegal)):
            agree = "DISAGREE"
        elif raisers and spread and len(raisers) == 1:
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
        row["classed_non_legal_by"] = ";".join(nonlegal) if raisers else ""
        row["severity_spread"] = "YES" if (raisers and spread) else "NO"
        row["worst_severity"] = worst
        row["agreement"] = agree
        row["any_verified"] = "YES" if any(EV.counts_as_primary(x) for r in REVIEWERS for x in by[pid][r]) else "NO"  # effective primary only
        row["any_verified_claim"] = "YES" if "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE" in allst else "NO"
        row["any_source_gap"] = "YES" if allst & GAP else "NO"
        matrix.append(row)
        escalate_spread = agree == "CORROBORATED_DEFECT" and spread
        if agree in ("DISAGREE", "SEVERITY_SPLIT") or escalate_spread:
            dis.append({"record_id": p["record_id"], "proposition_id": pid,
                        **{f"{r}_worst_severity": sev[r] for r in REVIEWERS},
                        **{f"{r}_states": ";".join(states[r]) for r in REVIEWERS},
                        "kind": "SEVERITY_SPLIT" if escalate_spread else agree,
                        "reason": ("VERIFIED vs UNSUPPORTED/CONTRADICTORY" if verified_vs_neg else
                                   f"P1/P2 raised by {';'.join(raisers)}"
                                   + (f"; positively assessed with no defect by {';'.join(fine)}" if fine else "")
                                   + (f"; classed as not a legal proposition by {';'.join(nonlegal)}" if nonlegal and agree == "DISAGREE" else "")
                                   + (f"; severities differ ({', '.join(f'{r}={sev[r]}' for r in raisers + lower)})" if spread else "")),
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
                    eff_status = EV.classify_finding(x)[0]
                    primary = eff_status == EC.EFFECTIVE_PRIMARY
                    if contra:  # an open conflict between sources takes precedence (QC-07)
                        st = "SOURCE_CONFLICT_OPEN"
                    elif agree == "DISAGREE":
                        st = "DISPUTED_ESCALATED"
                    elif x["proposed_correction"].strip() and primary:
                        st = "PRIMARY_EVIDENCE_SUPPORTED"
                    elif x["proposed_correction"].strip() and eff_status in EC.NOT_EFFECTIVE_PRIMARY:
                        st = "AUTHENTICATION_PENDING"
                    elif x["proposed_correction"].strip() and has_ev:
                        st = "SECONDARY_EVIDENCE_ONLY"
                    else:
                        st = "EVIDENCE_GAP"
                    props_out.append({
                        "proposal_id": f"CP2-{x['finding_id']}", "record_id": p["record_id"], "proposition_id": pid,
                        "original_text_verbatim": p["text_verbatim"], "proposed_text_or_action": x["proposed_correction"],
                        "severity": x["severity"], "defect_class": x["defect_class"], "dimension": x["dimension"],
                        "reviewer": r, "finding_id": x["finding_id"], "source_identity": x["source_identity"],
                        "source_sha256": x["source_sha256"], "locator": x["locator"], "rationale": x["rationale"],
                        "missing_evidence": x["missing_evidence"], "corroborated_by_reviewers": ";".join(corro),
                        "reviewers_marking_no_defect": ";".join(none_others), "claimed_evidence_state": x["evidence_state"],
                        "effective_evidence_status": eff_status, "support_status": st,
                        "incorporation_state": "PROPOSED_NOT_INCORPORATED (original record unchanged)"})
    mcols = ["record_id", "proposition_id", "text_verbatim"] + [f"{r}_{k}" for r in REVIEWERS for k in ("worst_severity", "states")] + ["worst_severity", "agreement", "defect_raised_by", "assessed_supported_by", "rated_minor_by", "classed_non_legal_by", "severity_spread", "any_verified", "any_verified_claim", "any_source_gap"]
    write(C2 / "reconciliation/proposition_matrix.csv", mcols, matrix)
    write(C2 / "reconciliation/disagreements.csv", ["record_id", "proposition_id"] + [f"{r}_worst_severity" for r in REVIEWERS] + [f"{r}_states" for r in REVIEWERS] + ["kind", "reason", "disposition"], dis)
    pcols = ["proposal_id", "record_id", "proposition_id", "original_text_verbatim", "proposed_text_or_action", "severity", "defect_class", "dimension", "reviewer", "finding_id", "source_identity", "source_sha256", "locator", "rationale", "missing_evidence", "corroborated_by_reviewers", "reviewers_marking_no_defect", "claimed_evidence_state", "effective_evidence_status", "support_status", "incorporation_state"]
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
        BLOCK = {"INTERPRETATION_REQUIRES_LEGAL_ADVICE", "UNSUPPORTED", "CONTRADICTORY_EVIDENCE", "SOURCE_NOT_HELD", "HISTORICAL_VERSION_UNRESOLVED"}
        fully = bool(legal) and all(m["any_verified"] == "YES" and RANK[m["worst_severity"]] <= 1 and not (BLOCK & set(";".join(m[f"{r}_states"] for r in REVIEWERS).split(";"))) for m in legal)
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
    eff_rows = []
    for x in allf:
        st, detail = EV.classify_finding(x)
        reg = EV.register.get(x["source_sha256"], {})
        eff_rows.append({"finding_id": x["finding_id"], "reviewer": x["reviewer"], "record_id": x["record_id"], "proposition_id": x["proposition_id"],
                         "claimed_evidence_state": x["evidence_state"], "effective_evidence_status": st, "classification_basis": detail,
                         "source_sha256": x["source_sha256"], "locator": x["locator"], "source_class_in_register": reg.get("effective_source_class", ""),
                         "provenance_references": reg.get("provenance_references", "")})
    write(C2 / "reconciliation/effective_evidence.csv", list(eff_rows[0].keys()),
          sorted(eff_rows, key=lambda d: (d["reviewer"], d["finding_id"])))
    sc = {
        "records_reviewed": len(rs), "of": 46, "propositions": len(props),
        "record_classification": dict(sorted(Counter(r["classification"] for r in rs).items())),
        "findings_by_reviewer": {r: len(F[r]) for r in REVIEWERS},
        "findings_by_severity": dict(sorted(Counter(x["severity"] for x in allf).items())),
        "findings_by_evidence_state": dict(sorted(Counter(x["evidence_state"] for x in allf).items())),
        "findings_by_evidence_state_note": "claimed reviewer states, preserved exactly as submitted",
        "verified_claims_by_effective_status": dict(sorted(Counter(e["effective_evidence_status"] for e in eff_rows if e["claimed_evidence_state"] == EC.VERIFIED).items())),
        "effective_primary_findings": sum(e["effective_evidence_status"] == EC.EFFECTIVE_PRIMARY for e in eff_rows),
        "findings_by_defect_class_P1_P2": dict(sorted(Counter(x["defect_class"] for x in allf if x["severity"] in ("P1", "P2")).items())),
        "proposition_agreement": dict(sorted(Counter(m["agreement"] for m in matrix).items())),
        "disagreements": sum(d["kind"] == "DISAGREE" for d in dis), "severity_splits_escalated": sum(d["kind"] == "SEVERITY_SPLIT" for d in dis),
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
