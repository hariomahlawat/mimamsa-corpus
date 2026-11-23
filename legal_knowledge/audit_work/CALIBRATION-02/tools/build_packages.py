"""CALIBRATION-02 package builder (stdlib, deterministic). Run after reconcile.py.

Outputs:
- registers/cross_volume_register.csv: reviewer D's cross_volume_register.csv plus every CROSS_VOLUME /
  CROSS_VOLUME_INCONSISTENCY finding from any reviewer (attributed, not merged or re-judged).
- proposals/proposed_versions.jsonl: one object per calibration record that has P1/P2 proposals, with the original
  record ID and canonical SHA-256, the original proposition text and each proposal with its support_status. Originals are
  never edited; incorporation_state is PROPOSED_NOT_INCORPORATED.
- adviser/legal_adviser_questions.csv: the reviewers' legal-advisor questions, clustered by topic with a fixed keyword
  table into LAQ topics. Every source question is kept verbatim with its reviewer and finding ID. The reserved items are
  appended as their own rows, states unchanged."""
import csv, json, re
from collections import defaultdict
from pathlib import Path

C2 = Path(__file__).resolve().parents[1]
TOPICS = [  # (topic id, title, regex on question+proposition) - first match wins
    ("LAQ-01", "AA s.133 reference to the Indian Evidence Act after BSA 2023; electronic-record certificate (IEA s.65B / BSA s.63) in courts-martial", r"s\.?133|BSA|65B|electronic|Anvar|Arjun"),
    ("LAQ-02", "Army Rule 182 as substituted by S.R.O. 17(E)/1993: printed omission of 'evidence against a person subject to the Act'", r"r\.?182|COI-003#P6"),
    ("LAQ-04", "Effect of Col. N.C. Isaac (2026 INSC 993) on Dharamvir Singh / Rajbir in pending and future claims", r"Isaac|Dharamvir"),
    ("LAQ-03", "Selection of Entitlement Rules (1982 / 2008 / 2023): trigger date", r"\bER (?:19|20)\d\d\b|Entitlement Rules|(?i:trigger date)"),
    ("LAQ-05", "Army Act ss.122/123 limitation: versions before/after Act 37/1992 and cumulative operation", r"s\.?12[23]|Act 37"),
    ("LAQ-06", "Appealability to AFT under s.15 of SCM sentences excluded by s.3(o)(iv); s.164 petition as a precondition", r"s\.?3\(o\)|SCM|s\.?164|AFT s\.?15"),
    ("LAQ-07", "1978 Adjustment of Jurisdiction Rules after BNSS s.521/s.531", r"1978|BNSS s\.?5[23]1|adjustment"),
    ("LAQ-08", "AA s.89(2) percentage of pay vs AR r.186(1) 'current official prices' for collective fines", r"s\.?89|r\.?186"),
    ("LAQ-09", "Meaning of 'transportation' in AA ss.69, 119-120", r"transportation"),
    ("LAQ-10", "Administrative termination: s.19/r.14 after acquittal; stigma test; r.15 text (reserved r.15 OPEN)", r"r\.?14|r\.?15|s\.?19|stigma|termination"),
    ("LAQ-11", "PPS Bedi r.40 'practicability' and GCM composition under current r.40", r"r(ule)? ?40|Bedi"),
    ("LAQ-12", "Pooja Pal (2026): holding on CR communication (not held)", r"Pooja"),
    ("LAQ-13", "Transitional application of IPC vs BNS to offences before 1 July 2024", r"IPC|BNS"),
]
RESERVED = [
    ("RES-r23(3)", "Army Rule 23(3) accused-statement caution: negation present in MML/1954 text vs absent in compilations", "CONFLICTING (unchanged)"),
    ("RES-C-08", "Rule 193 prescribed officer (s.90(i)/91(i)) chronology", "OPEN (unchanged)"),
    ("RES-C-09", "Rule 194 as substituted by S.R.O. 332/1989 vs compilation", "PROPOSAL (unchanged)"),
    ("RES-r15", "Rule 15 'or Military Secretary' amendment-source discrepancy", "OPEN (unchanged)"),
    ("RES-r187(1)", "Rule 187(1) footnote 'SRO 1 dated 12 March 1964'", "OPEN (unchanged)"),
    ("RES-s129", "Army Act s.129 wording", "OPEN (unchanged)"),
    ("RES-AQ-05", "Commencement where an instrument is silent", "RESERVED (unchanged)"),
    ("RES-AQ-06", "Legal consequences of retrospective deemed effect (e.g. S.R.O. 216/1988 from 1979-06-04)", "RESERVED (unchanged)"),
    ("RES-OQ-A-13", "Provisions affected by Act 19/1955", "OPEN (unchanged)"),
]


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
    props = {p["proposition_id"]: p for p in read(C2 / "propositions.csv")}
    # cross-volume
    xv = []
    for r in read(C2 / "reviews/D/cross_volume_register.csv"):
        xv.append({"source": "D/cross_volume_register.csv", "id": r["link_id"], "record_id": r["record_id"], "other_record_ids": r["other_record_ids"],
                   "relation": r["relation"], "severity": r["severity"], "evidence_or_finding": r["evidence"]})
    for rv in "ABCD":
        for x in read(C2 / "reviews" / rv / "findings.csv"):
            if x["dimension"] == "CROSS_VOLUME" or x["defect_class"] == "CROSS_VOLUME_INCONSISTENCY":
                ids = sorted(set(re.findall(r"\b(?:[A-Z]{1,4}(?:-[A-Z]{2})?-\d{2,3}|V\d-[A-Z]{2}-\d{2}|SC\d{2}|J-\d{2}|KB-\d{3})\b", x["finding"])) - {x["record_id"]})
                xv.append({"source": f"{rv}/findings.csv", "id": x["finding_id"], "record_id": x["record_id"], "other_record_ids": ";".join(ids),
                           "relation": x["defect_class"], "severity": x["severity"], "evidence_or_finding": x["finding"][:600]})
    write(C2 / "registers/cross_volume_register.csv", ["source", "id", "record_id", "other_record_ids", "relation", "severity", "evidence_or_finding"],
          sorted(xv, key=lambda d: (d["record_id"], d["source"], d["id"])))
    # proposed versions
    cps = read(C2 / "proposals/correction_proposals.csv")
    byrec = defaultdict(list)
    for c in cps:
        byrec[c["record_id"]].append(c)
    with open(C2 / "proposals/proposed_versions.jsonl", "w", encoding="utf-8") as f:
        for rid in sorted(byrec):
            items = sorted(byrec[rid], key=lambda c: (c["proposition_id"], c["proposal_id"]))
            obj = {"original_record_id": rid, "original_record_canonical_sha256": props[items[0]["proposition_id"]]["record_canonical_sha256"],
                   "relation": "PROPOSED_CORRECTION_OF", "incorporation_state": "PROPOSED_NOT_INCORPORATED",
                   "legal_status": "NOT_LEGALLY_APPROVED",
                   "changes": [{"proposition_id": c["proposition_id"], "original_text_verbatim": c["original_text_verbatim"],
                                "proposed_text_or_action": c["proposed_text_or_action"], "severity": c["severity"],
                                "support_status": c["support_status"], "proposal_id": c["proposal_id"], "reviewer": c["reviewer"],
                                "source_sha256": c["source_sha256"], "locator": c["locator"]} for c in items]}
            f.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")
    # adviser questions
    rows, seen = [], defaultdict(list)
    raw = read(C2 / "reconciliation/legal_advisor_questions_raw.csv")
    qtext = defaultdict(str)
    for q in raw:
        qtext[q["proposition_id"]] += " " + q["question"]
    for q in raw:
        hay = q["question"] + " " + q["proposition_id"] + " " + props[q["proposition_id"]]["text_verbatim"]
        for ref in re.findall(r"[A-Z][A-Z0-9-]*#(?:P\d+|REF)", q["question"]):  # 'As CM-026#P2' cross-references
            if ref in props:
                hay += " " + ref + " " + props[ref]["text_verbatim"] + " " + qtext[ref]
        tid = next((t for t, _, rx in TOPICS if re.search(rx, hay)), "LAQ-99")
        seen[tid].append(q)
    titles = {t: ti for t, ti, _ in TOPICS} | {"LAQ-99": "Other"}
    for tid in sorted(seen):
        for q in sorted(seen[tid], key=lambda q: (q["proposition_id"], q["reviewer"], q["finding_id"])):
            rows.append({"topic_id": tid, "topic": titles[tid], "record_id": q["record_id"], "proposition_id": q["proposition_id"],
                         "reviewer": q["reviewer"], "finding_id": q["finding_id"], "question_verbatim": q["question"], "state": "FOR_LEGAL_ADVICE (no determination made)"})
    for rid, title, state in RESERVED:
        rows.append({"topic_id": rid, "topic": title, "record_id": "", "proposition_id": "", "reviewer": "coordinator (reserved list)",
                     "finding_id": "", "question_verbatim": title, "state": state})
    write(C2 / "adviser/legal_adviser_questions.csv", ["topic_id", "topic", "record_id", "proposition_id", "reviewer", "finding_id", "question_verbatim", "state"], rows)
    print(json.dumps({"cross_volume_rows": len(xv), "records_with_proposals": len(byrec), "adviser_rows": len(rows),
                      "topics": {t: len(v) for t, v in sorted(seen.items())}}, sort_keys=True))


if __name__ == "__main__":
    main()
