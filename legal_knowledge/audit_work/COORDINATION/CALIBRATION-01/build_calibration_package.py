#!/usr/bin/env python3
"""Assemble the CALIBRATION-01 evidence package for the 46-record calibration sample (deterministic, stdlib only).

Collects, per sample record, the evidence already held in the audit registers. It makes NO legal determination:
`proposed_determination` and the reviewer and advisor fields are emitted empty, with the state NOT_ADJUDICATED.
Coverage and searchability are never legal correctness.

  python3 legal_knowledge/audit_work/COORDINATION/CALIBRATION-01/build_calibration_package.py
"""
import csv, hashlib, json, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
AW = HERE.parents[1]
ROOT = AW.parents[1]
KB = ROOT / "legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl"
KB_SHA = "9a8f0d193065762ffa987116dc761bcb734008d2a87a946f5591741f5befcfc1"


def rows(rel):
    p = AW / rel
    return list(csv.DictReader(open(p, newline="", encoding="utf-8"))) if p.is_file() else []


def ids_in(text):
    return set(re.findall(r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+", text or ""))


def rule_key(r):
    m = re.match(r"r\.?\s*(\d+[A-Z]?)", (r or "").strip())
    return m.group(1) if m else None


def main():
    kb_bytes = KB.read_bytes()
    assert hashlib.sha256(kb_bytes).hexdigest() == KB_SHA, "frozen KB hash changed"
    kb = {json.loads(l)["id"]: json.loads(l) for l in kb_bytes.decode("utf-8").splitlines() if l.strip()}
    sample = rows("WS-C-MML/calibration_sample_ranked.csv")
    inv = {r["record_id"]: r for r in rows("WS-C-MML/kb658_source_coverage_inventory.csv")}
    chron = rows("ARMY-RULES-CHAIN-01/army_rules_provision_chronology.csv")
    vers = rows("ARMY-RULES-CHAIN-01/statutory_version_register_seed.csv")
    pcl = rows("WS-A-STATUTORY/provision_change_log.csv")
    xw = rows("WS-C-MML/mml_provision_crosswalk.csv")
    cases = rows("WS-B-JUDGMENTS/crosswalk_cases53_kb658.csv")
    hold = rows("WS-B-JUDGMENTS/holdings_register.csv")
    treat = rows("WS-B-JUDGMENTS/subsequent_treatment.csv")
    adverse = rows("WS-B-JUDGMENTS/adverse_conflict_queue.csv")
    pg = rows("WS-C-MML/procedure_gap_conflict_register.csv")
    conflict_rules = {"23": "C-01 r.23(3) CONFLICTING", "193": "C-08 r.193 OPEN", "194": "C-09 r.194 PROPOSAL"}
    out = []
    for s in sorted(sample, key=lambda r: int(r["rank"])):
        rid = s["record_id"]
        rec = kb[rid]
        i = inv.get(rid, {})
        ar = [x for x in (i.get("ar_rules") or "").split(";") if x]
        aa = [x for x in (i.get("aa_sections") or "").split(";") if x]
        chron_hits = [f"r.{c['provision']}|{c['event']}|{c['instrument']}|pub {c['publication_date']}|eff {c['effective_date'] or 'null'} ({c['effective_date_status']})"
                      for c in chron if rule_key(c["provision"]) in ar]
        pcl_hits = sorted({p["change_id"] for p in pcl if rule_key(p["provision"]) in ar})
        ver_hits = [f"{v['provision']} {v['version']} [{v['determination_state']}]" for v in vers if rule_key(v["provision"]) in ar]
        mml = [f"{x['provision']}@{x['mml_file']}:{x['mml_locator']} ({x['verification_state']})" for x in xw
               if rid in (x.get("kb_record_ids_new", "") + ";" + x.get("kb_record_ids_pilot_covered", "")).split(";")][:8]
        case_links = [f"{c['case53_id'] or c['spec_key']} [{c['identity_state']}; {c['citability_flag']}]" for c in cases if c["kb_record_id"] == rid]
        holds = [f"{h['row_id']} {h['judgment']} para {h['para_pinpoint']} ({h['passage_type']}; {h['wording_read_from']})" for h in hold if rid in ids_in(h["affected_kb_ids"])]
        treats = [f"{t['row_id']} {t['treatment']} by {t['later_judgment']}" for t in treat if rid in ids_in(t["affected_kb_ids"])]
        contra = [f"{a['item_id']} ({a['severity']}): {a['issue'][:160]}" for a in adverse if rid in ids_in(a["affected_kb_ids"])]
        contra += [f"{p['pg_id']} ({p['severity']}): {p['gap_or_conflict']} {p['provision']}" for p in pg if rid in ids_in(p["affected_kb_records"])]
        fixed = [conflict_rules[r] for r in ar if r in conflict_rules]
        questions = []
        if fixed:
            questions.append("Record relies on a disputed provision (" + "; ".join(fixed) + "): which text and version applies on the record's relevant date?")
        if any("NOT_STATED" in c or "NOT_DETERMINED" in c for c in chron_hits):
            questions.append("Effective date of an amending instrument is not stated (AQ-05): what date governs?")
        if contra:
            questions.append("Resolve the listed adverse or contradictory evidence before any determination.")
        out.append({
            "rank": s["rank"], "record_id": rid, "module": s["module"], "kind": s["kind"], "record_sha256": s["record_sha256"],
            "status_as_recorded": s["status_as_recorded"], "selection_basis": s["selection_basis"],
            "original_title": rec.get("title", ""), "exact_claim": (rec.get("body") or "").strip(),
            "references_as_recorded": rec.get("references", "") if isinstance(rec.get("references"), str) else json.dumps(rec.get("references", ""), ensure_ascii=False),
            "relevant_date_as_recorded": "",
            "army_act_sections": ";".join(aa), "army_rules": ";".join(ar), "other_statutes": i.get("other_statutes_plain", ""),
            "citation_codes": i.get("codes", ""), "coverage_state_wsc": i.get("coverage_state", ""), "coverage_flags": i.get("broken_or_unresolved_flags", ""),
            "amendment_commencement_chronology": " || ".join(chron_hits), "ws_a_change_log_ids": ";".join(pcl_hits),
            "version_register_rows": " || ".join(ver_hits), "fixed_dispute_states": "; ".join(fixed),
            "mml_locators_manual_not_authority": " || ".join(mml),
            "linked_cases": " || ".join(case_links), "holdings_with_pinpoints": " || ".join(holds), "subsequent_treatment": " || ".join(treats),
            "contradictory_or_adverse_evidence": " || ".join(contra),
            "proposed_determination": "", "uncertainty": "",
            "independent_reviewer_assessment": "", "questions_reserved_for_legal_advisor": " | ".join(questions),
            "adjudication_state": "NOT_ADJUDICATED", "legal_advisor_state": "NOT_STARTED", "jag_validation_state": "NOT_STARTED",
        })
    cols = list(out[0])
    with open(HERE / "calibration_package.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(out)
    summary = {"records": len(out), "kb_sha256": KB_SHA,
               "with_disputed_provision": sum(bool(r["fixed_dispute_states"]) for r in out),
               "with_chronology": sum(bool(r["amendment_commencement_chronology"]) for r in out),
               "with_linked_cases": sum(bool(r["linked_cases"]) for r in out),
               "with_holdings": sum(bool(r["holdings_with_pinpoints"]) for r in out),
               "with_adverse_evidence": sum(bool(r["contradictory_or_adverse_evidence"]) for r in out),
               "adjudicated": 0}
    (HERE / "calibration_package_summary.json").write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
