#!/usr/bin/env python3
"""procedure_crosswalk.csv: procedural step -> Army Act section(s) -> Army Rule(s) with version events
(ARMY-RULES-CHAIN-01 chronology + WS-A provision_change_log; publication date, commencement as printed and
effective date kept distinct; a chain retrospective_deemed_effect_from value is carried in its own column) -> MML locators (MML 2 page, image-verified where in crosswalk_locator_verification.csv;
MML 1 Part I paras citing the provisions; vol 2 DOC locators) -> KB records citing the provisions; and a flag where
MML text predates an amendment. Stdlib; deterministic. Coverage/locator work only; no legal determination.
Usage (repo root): python3 .../build_procedure_crosswalk.py <path to WS-A provision_change_log.csv>"""
import csv, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent; W = HERE.parent; ROOT = W.parents[2]
PCL = Path(sys.argv[1])
CHRON = ROOT / "legal_knowledge/audit_work/ARMY-RULES-CHAIN-01/army_rules_provision_chronology.csv"

# step, AA sections, AR rules, MML-currency notes (each note cites its evidence)
STEPS = [
 ("ARREST_CUSTODY", "Custody of accused; 48-hour investigation; 8-day delay report", "101;102;103", "27", "AA ss.101-103 and r.27 time limits image-checked in MML 2 (LV rows). No amendment to r.27 located in AR chain."),
 ("HEARING_OF_CHARGE", "Hearing of charge by CO / disposal", "80;83;84;85", "22", "r.22 substituted by S.R.O. 17(E)/1993 (PCL-93-5). MML 2 p.150 reflects 1993 text plus a 2002 Explanation (AR-030 NOT_FOUND). MML 1 Part I Ch III paras 12-13 PREDATE 1993 (PG-14). vol 2(AR) DOCs omit 'or' in r.22(3) (FID-05)."),
 ("SUMMARY_OF_EVIDENCE", "Summary of evidence; caution; remand", "", "23;24", "r.23: no amendment located; r.23(3) CONFLICTING (fixed). MML 1 Ch III paras 13-16 cite r.25 (omitted 1993) and are pre-1993."),
 ("ABSTRACT_OF_EVIDENCE_OFFICERS", "Former officer procedure / abstract of evidence (omitted 1993)", "", "25;33;37;54;134;135;136;160", "S.R.O. 17(E)/1993 omitted r.25 and the 'or abstract' words (PCL-93-6, 8, 10, 13, 25, 29). MML 2 reflects the omissions (XC-07..11); vol 2(AR) DOCs still carry 'or abstract' in r.26(3) and r.37(4) (FID-07, FID-08). MML 1 PREDATES."),
 ("SUMMARY_DISPOSAL_OFFICERS_JCO_WO", "Summary disposal of charges against officers, JCOs, WOs", "83;84;85", "26", "r.26(1),(3) words omitted 1993 (PCL-93-7); DOCs not updated (FID-08). vol 2(AA) s.85 proviso omits 'or such other officer' (FID-02)."),
 ("SUMMARY_PUNISHMENT_NCO_OR", "Summary punishment of persons other than officers, JCOs, WOs", "79;80;81;82", "192", "s.80(j) omitted by Act 37/1992 (PIC-07, WSC-PIC-25); r.192 proviso inserted 1965 (AR-011; PIC-04). MML 1 Ch II paras 13-14 PREDATE 1992 (pilot version diffs)."),
 ("FIELD_PUNISHMENT_ABOLISHED", "Field punishment (abolished)", "75;76;77", "168;172;173;174;175;176", "AA ss.75-76 omitted by Act 37/1992 s.2 (PIC-07); AR rr.172-176 and Section 7 heading omitted, r.168(2) words omitted by S.R.O. 17(E)/1993 (PCL-93-31, 34). MML 1 Ch II para 13 (field punishment; cites rr.172-176) PREDATES both. MML 2 reflects (WSC-PIC-23, 24)."),
 ("SUSPENSION_OF_RULES", "Suspension of rules on military exigency", "", "36", "Figure '25' omitted 1993 (PCL-93-9); MML 2 reflects; vol 2(AR) DOCs still list 25 (FID-06)."),
 ("CONVENING_AND_PRE_TRIAL", "Convening; documents to court; warning of accused (96 hours)", "108;109;110;111", "33;34;37", "r.34(7) 96-hour notice image-checked in MML 2 (LV). r.33(7), r.37(4) amended 1993 (PCL-93-8, 10); DOCs not updated for r.37(4) (FID-07)."),
 ("PLEA_AND_TRIAL", "Plea, plea in bar, no case, examination of accused, addresses, findings", "", "52;53;57;58;59;59A;62", "All substituted/amended 1993 (PCL-93-11..18). MML 2 notes present (XC-12). vol 2(AR) DOCs: r.58(1)(a)(ii) 'or before' for 'and before' (FID-09); r.62(3) 'may' omitted (FID-10)."),
 ("LIMITATION", "Limitation for trial; ex-service offenders", "122;123", "53", "s.122(1) three years image-checked (LV); s.123(2) bracketed text noted as substituted by Act 37/1992 in MML 2; vol 2(AA) omits 'day' (FID-04). r.53(1)(c) substituted 1993 (PCL-93-12)."),
 ("SUMMARY_COURT_MARTIAL", "SCM powers, finding and transmission", "116;120;161;162", "", "s.120(5) limits image-checked in MML 2 (LV)."),
 ("CONFIRMATION_AND_REVISION", "Confirmation, mitigation, revision", "153;154;158;160", "68;69;71", "r.68 Revision substituted 1993 (PCL-93-19); MML 2 reflects (XC-12)."),
 ("PETITIONS_AND_REMEDIES", "Petitions against finding/sentence; death-sentence petitions; AFT", "164;165", "170;170A;170B", "rr.170-170B substituted/inserted 1993 (PCL-93-32, 33). ALL MML files PREDATE the Armed Forces Tribunal Act 2007 (latest MML amendment note 2003): no MML guidance on AFT appeals/applications."),
 ("SECOND_TRIAL", "Prohibition of second trial", "121;127", "", "s.127 omitted by Act 37/1992 (MML 2 p.92 fn; vol 2(AA) bare 'Omitted'; pilot). MML 2 s.121 carries a note-deletion footnote (MoD letter 28 Aug 2001; pilot PIC-05)."),
 ("COURT_OF_INQUIRY", "Court of inquiry; character involved; evidence; admissibility; copies", "106", "177;178;179;180;181;182;183;184;185", "r.177 substituted 2003 (AR-031) - vol 2(AR) DOCs pre-2003 (pilot); r.179(5A) inserted and r.182 substituted 1993 (PCL-93-35, 36); r.184 substituted 1985 (AR-018). s.106 30-day trigger image-checked (LV)."),
 ("COLLECTIVE_FINES", "Collective fines for lost/stolen arms", "89", "185;186", "r.186(1) substituted 1993 (PCL-93-37); vol 2(AR).doc retains pre-decimal price table (FID-11)."),
 ("DISMISSAL_EFFECTIVE_DATE", "When cashiering/dismissal takes effect", "", "168", "r.168(2) words omitted 1993 (PCL-93-31); MML 2 reflects (WSC-PIC-23)."),
 ("OFFICER_TERMINATION_RETIREMENT", "Termination/retirement of officers by Central Government", "18;19;20", "13A;14;15;15A;15B;16A;16B", "r.14(4)-(5) and r.16A substituted 1993 (PCL-93-2, 3); r.16A amended 2019 (AR-034) and 2022 (AR-035); r.15B inserted 2019 (AR-034). ALL MML PREDATE 2019/2022 (PG-07, PG-08). MML note on r.15 (17(E)/1993) not supported by WS-A (XC-03)."),
 ("PRESCRIBED_OFFICERS_PENAL_DEDUCTIONS", "Prescribed officers for penal deductions / forfeitures", "90;91;93", "193;194", "r.193: 1954 -> 1987 (AR-023) -> 1993 (PCL-93-38) - C-08 OPEN; r.194: 1989 (AR-025) - C-09 PROPOSAL. MML 2 p.227 (WSC-PIC-08..10); doc-1 TOC stale (WSC-PIC-11)."),
]


def nums(spec):
    return [x for x in spec.split(";") if x]


def main():
    chron = list(csv.DictReader(open(CHRON, encoding="utf-8")))
    pcl = list(csv.DictReader(open(PCL, encoding="utf-8")))
    inv = list(csv.DictReader(open(W / "kb658_source_coverage_inventory.csv", encoding="utf-8")))
    idx = {r["provision"]: r for r in csv.DictReader(open(W / "provision_index.csv", encoding="utf-8"))}
    lv = {r["provision"]: r for r in csv.DictReader(open(W / "crosswalk_locator_verification.csv", encoding="utf-8"))}
    m1 = list(csv.DictReader(open(W / "mml1_para_index.csv", encoding="utf-8")))
    cal = {r["record_id"] for r in csv.DictReader(open(W / "calibration_sample_ranked.csv", encoding="utf-8"))}

    def rule_hits(prov_field, n):
        toks = set(re.findall(r"\d{1,3}[A-Z]?", prov_field))
        rng = re.findall(r"(\d+)\s*(?:-|to)\s*(\d+)", prov_field)
        for a, b in rng:
            toks |= {str(i) for i in range(int(a), int(b) + 1)}
        return n in toks

    rows = []
    for sid, desc, aa, ar, note in STEPS:
        evs = []
        for n in nums(ar):
            for c in chron:
                if c["instrument_id"] and c["instrument_id"] != "AR-029" and rule_hits(c["provision"], n):
                    evs.append((f"r.{n}", c["instrument_id"], c["instrument"], c["event"], c["publication_date"], c["commencement_as_printed"], c["effective_date"], c["effective_date_status"], c.get("retrospective_deemed_effect_from", "")))
            for p in pcl:
                if p["change_id"].startswith("PCL-93-") and p["change_id"] != "PCL-93-N" and rule_hits(p["provision"], n):
                    evs.append((f"r.{n}", "AR-029 " + p["change_id"], "S.R.O. 17(E)/1993", p["change_type"], p["publication_date"], p["commencement_as_printed"][:40], p["effective_date"], p["effective_date_status"][:40], ""))
        seen, ev2 = set(), []
        for e in evs:
            if e[:4] not in seen:
                seen.add(e[:4]); ev2.append(e)
        provs = ["s." + x for x in nums(aa)] + ["r." + x for x in nums(ar)]
        mml2 = []
        for pv in provs:
            if pv in idx:
                tag = "img" if pv in lv else "txt"
                mml2.append(f"{pv} p.{idx[pv]['mml2_pdf_page']}({tag})")
            else:
                mml2.append(f"{pv} NOT_IN_MML_INDEX")
        doc = []
        for pv in provs:
            if pv in idx:
                for col in ("MML vol 2(AA).doc.doc", "MML vol 2(AR).doc.doc", "MML vol 2(AR).doc-1.doc"):
                    if idx[pv].get(col):
                        doc.append(f"{pv} {col.replace('MML vol 2','v2').replace('.doc.doc','.doc').replace('.doc-1.doc','.doc-1')} {idx[pv][col]}")
        m1p = sorted({f"Ch {p['chapter']} para {p['para']}" for p in m1 for pv in provs
                      if pv in (["s." + x for x in p["aa_sections_cited"].replace("s.", "").split(";") if x] + ["r." + x for x in p["ar_rules_cited"].replace("r.", "").split(";") if x])})
        recs = sorted({x["record_id"] for x in inv for pv in provs
                       if pv[2:] in x["aa_sections" if pv.startswith("s.") else "ar_rules"].split(";")})
        # MML 1 latest internal year 1976 (ES-01); MML 2 latest amendment note 2003 (ES-02); vol 2 DOCs latest 1993 (ES-03..06)
        years = sorted({e[4][:4] for e in ev2 if e[4]})
        parts = []
        if [y for y in years if y > "1976"]:
            parts.append("MML 1 (latest internal year 1976) predates " + ",".join(sorted({y for y in years if y > "1976"})))
        if [y for y in years if y > "1993"]:
            parts.append("vol 2 DOCs (latest note 1993) predate " + ",".join(sorted({y for y in years if y > "1993"})))
        if [y for y in years if y > "2003"]:
            parts.append("ALL MML incl. MML 2 (latest note 2003) predate " + ",".join(sorted({y for y in years if y > "2003"})))
        flag = "; ".join(parts) if parts else ("no rule change dated after 1976 located" if years else "no rule events located (Act-only or unamended rules)")
        rows.append({"step_id": f"PX-{len(rows) + 1:02d}", "step": sid, "description": desc,
                     "army_act_sections": ";".join("s." + x for x in nums(aa)), "army_rules": ";".join("r." + x for x in nums(ar)),
                     "rule_version_events": " | ".join(f"{e[0]} {e[1]} {e[3]}" for e in ev2),
                     "publication_dates": " | ".join(f"{e[0]}:{e[4] or 'n/a'}" for e in ev2),
                     "commencement_as_printed": " | ".join(f"{e[0]}:{e[5] or 'n/a'}" for e in ev2),
                     "effective_dates": " | ".join(f"{e[0]}:{e[6] or ''}" for e in ev2),
                     "effective_date_status": " | ".join(f"{e[0]}:{e[7] or 'n/a'}" for e in ev2),
                     # separate field, never merged into effective dates (ARMY-RULES-CHAIN-01 column added by PR #28)
                     "retrospective_deemed_effect_from": " | ".join(f"{e[0]}:{e[1]}:{e[8]}" for e in ev2 if e[8]),
                     "mml2_locators": "; ".join(mml2), "mml1_paras": "; ".join(m1p), "vol2_doc_locators": "; ".join(doc[:30]),
                     "mml_currency_flag": flag, "mml_currency_notes": note,
                     "kb_record_ids": ";".join(recs), "n_kb_records": len(recs), "calibration_records": ";".join(r for r in recs if r in cal),
                     "evidence_level": "Locators text-layer unless marked (img) = heading image-checked; dates from AR chain / WS-A PCL; MML-currency notes cite their own evidence ids",
                     "state": "RESEARCH ONLY; FOR INDEPENDENT COORDINATOR CHECK"})
    with open(W / "procedure_crosswalk.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(len(rows), "steps;", len({r for x in rows for r in x["kb_record_ids"].split(";") if r}), "distinct KB records")


if __name__ == "__main__":
    main()
