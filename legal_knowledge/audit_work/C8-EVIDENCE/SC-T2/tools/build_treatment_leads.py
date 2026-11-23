"""Write c8out/C/subsequent_treatment_leads.csv: research questions per judgment, with what the corpus currently records.
usage: python build_treatment_leads.py <out_dir_C>. Every row is RESEARCH_LEAD_UNVERIFIED; nothing here states that a judgment is or
is not good law. Sources: WS-B-JUDGMENTS/subsequent_treatment.csv (WSB-T-*), subsequent_treatment_cycle3.csv (WSB-T3-*),
case_relations.csv, open_inconsistencies_cycle3.csv (OI-*), identity_resolution_cycle3.csv, cases_53.jsonl (by id#field), and C8 page checks."""
import csv, sys
from pathlib import Path

C53 = "curated_originals/case_law/v0.9/cases_53.jsonl"
L = [
    ("RANJIT-1", "DCLR-SC-1987-R01", "C5-SRC-J-SC-1987-RANJIT-THAKUR~C1", "Ranjit Thakur v UOI (15-10-1987)",
     "Effect of the review order dated 10-08-1988 on the s.130 reasoning (point 1.3) and on the rest of the judgment",
     f"{C53}#DCLR-SC-1987-R01.holding/scope_and_caveats say the s.130 reasoning was deleted on review; {C53}#DCLR-SC-1988-R02 (Review Petition 43/1988, (1989) 2 SCC 438) sourced from Indian Kanoon only; WSB-T-017 REVIEW_ORDER_NOT_HELD; identity_resolution_cycle3 RANJIT_REVIEW UNRESOLVED",
     "Held copy p.3 (C8-SCPIC-02) carries an editorial note: '(Note: on point 1.3 the finding is to be read with and subject to the subsequent order dated 10.8.88)'. The review order itself is not held; obtain an official copy before relying on either record"),
    ("RANJIT-2", "DCLR-SC-1987-R01", "C5-SRC-J-SC-1987-RANJIT-THAKUR~C1", "Ranjit Thakur v UOI (15-10-1987)",
     "Later treatment of the bias and proportionality propositions (followed / distinguished / limited)",
     "WS-B holdings WSB-H3-018 (p.6, SCR 519-520) records the holding; no WS-B treatment row other than WSB-T-017; cases_53 post_decision_treatment_status NOT_EXHAUSTIVELY_CHECKED",
     "JUDIS CITATOR INFO on p.1 lists R 1988 SC1099; D 1991 SC1617; R 1992 SC 188; R 1992 SC 417 - database material, unverified, not a treatment finding"),
    ("RANJIT-3", "DCLR-SC-1987-R01", "C5-SRC-J-SC-1987-RANJIT-THAKUR~C1", "Ranjit Thakur v UOI (15-10-1987)",
     "Statutory change affecting the holding: amendments to Army Act ss.41, 130, 164 and Army Rules governing SCM since 1987; AFT Act 2007 forum for review",
     "cases_53 provisions list Army Act s.41(2), s.116, s.130, Art.226; no amendment-chain link recorded for this case", "Statutory currency is a separate question from copy provenance"),
    ("SNM-1", "DCLR-SC-1990-N02", "C5-SRC-J-SC-1990-SN-MUKHERJEE~C1", "S N Mukherjee v UOI (28-08-1990, five judges)",
     "Effect of the later Army Rule 62(1) amendment (reasons for findings) on the 1990 statement that court-martial findings need not be reasoned",
     f"{C53}#DCLR-SC-1990-N02.v07_review_note: 'TIME-BOUND LAW: post-amendment Army Rule 62(1) expressly requires brief reasons on each charge'; scope_and_caveats cite 'post-1993' amendment",
     "Date and text of the Rule 62(1) amendment to be confirmed from the statutory corpus (WS-A), not from the case record"),
    ("SNM-2", "DCLR-SC-1990-N02", "C5-SRC-J-SC-1990-SN-MUKHERJEE~C1", "S N Mukherjee v UOI (28-08-1990)",
     "Subsequent treatment of the duty-to-give-reasons and Art.226 review propositions",
     "WSB-T-016 / case_relations: Parashotam Dass (CA 447/2023) FOLLOWED / APPLIED (pp.20-22, paras 29-32; Art.226 against AFT orders); NOT_EXHAUSTIVE",
     "JUDIS CITATOR INFO p.1: RF 1991 SC 564; R 1992 SC1256 (database material, unverified)"),
    ("SNM-3", "DCLR-SC-1990-N02", "C5-SRC-J-SC-1990-SN-MUKHERJEE~C1", "S N Mukherjee v UOI (28-08-1990)",
     "Applicability under current law of the holding on s.164(2) post-confirmation petitions (no reasons) given later rule changes and AFT jurisdiction",
     f"{C53}#DCLR-SC-1990-N02.scope_and_caveats: whether confirmation or s.164(2) rejection needs reasons today is a distinct question requiring updated case-law review", ""),
    ("NAVJOT-1", "DCLR-SC-2005-L01", "C5-SRC-J-SC-2005-NAVJOT~C1", "State (NCT of Delhi) v Navjot Sandhu (04-08-2005)",
     "Extent of overruling of the electronic-evidence (ss.63/65 vs s.65B Evidence Act) proposition",
     "WSB-T-001 / case_relations: Anvar P.V. v P.K. Basheer (CA 4226/2012) OVERRULED_IN_PART (p.18 para 22), scope 'only the s.65B/secondary electronic evidence proposition'; cases_53 v09_treatment_note cites Arjun (2020) and Sundar (2023); v09_suppress_from_current_guidance true",
     "WS-B notes later 2024/2025 treatments (Ravishankar Tandon, Chandrabhan) not re-read. OI-11: JUDIS copy has no paragraph numbers; Anvar quotes SCC para 150"),
    ("NAVJOT-2", "DCLR-SC-2005-L01", "C5-SRC-J-SC-2005-NAVJOT~C1", "State (NCT of Delhi) v Navjot Sandhu (04-08-2005)",
     "Statutory change: Indian Evidence Act 1872 replaced by Bharatiya Sakshya Adhiniyam 2023 (from 01-07-2024); IPC (s.123 conviction on p.107) replaced by BNS; POTA 2002 repealed (2004) - applicability of any proposition under current law",
     "cases_53 provisions empty; record_type CITATION_LEAD; holding empty; WS-B crosswalk citability NOT_CITABLE_AS_AUTHORITY_HOLDING_EMPTY", "Transitional application to pre-2024 trials needs separate legal research"),
    ("NAVJOT-3", "DCLR-SC-2005-L01", "C5-SRC-J-SC-2005-NAVJOT~C1", "State (NCT of Delhi) v Navjot Sandhu (04-08-2005)",
     "Other subsequent citations (relied on / distinguished) of Navjot Sandhu",
     "WSB-T3-046: cited in intern doc 2016 INSC 527 (p.11) 'relied on', CITED_TREATMENT_NOT_CLASSIFIED; NOT_EXHAUSTIVE", ""),
    ("DHARAMVIR-1", "DCLR-SC-2013-N08", "C5-SRC-J-SC-2013-DHARAMVIR~C1", "Dharamvir Singh v UOI (02-07-2013)",
     "Entitlement Rules 1982 (applied) versus Entitlement Rules 2008 and the 2023 entitlement framework: which regime governs a given claim, and whether the presumption/onus reasoning carries over",
     f"{C53}#DCLR-SC-2013-N08.v04_verified_caveat: 'applies the older Pension Regulations and Entitlement Rules, 1982 ... Do not mechanically apply ... to claims governed by the 2023 entitlement framework'; WSB-T-007 / case_relations: N.C. Isaac (2026 INSC 993) QUALIFIED_FOR_LATER_REGIME (ER 2008 Rule 7 proviso), NOT_OVERRULED (pp.91, 93)",
     "Project brief refers to a September 2026 SC ruling on the 2008 Rules; the corpus links this to Isaac (judgment URL dated 15-Sep-2026). Whether Isaac is that ruling, and its exact effect, is a legal question"),
    ("DHARAMVIR-2", "DCLR-SC-2013-N08", "C5-SRC-J-SC-2013-DHARAMVIR~C1", "Dharamvir Singh v UOI (02-07-2013)",
     "Distinguishing/limitation for diseases not detectable at enrolment (e.g. mental disorders)",
     "WSB-T-006 / case_relations: Ex Cfn Narsingh Yadav (CA 7672/2019) DISTINGUISHED / LIMITED (pp.12-15, paras 14-21), text layer only", "N S Yadav copy (3c50cdb7) is itself a primary candidate; its treatment passage was not page-image checked in C8"),
    ("DHARAMVIR-3", "DCLR-SC-2013-N08", "C5-SRC-J-SC-2013-DHARAMVIR~C1", "Dharamvir Singh v UOI (02-07-2013)",
     "Followed in later SC judgments", "WSB-T-014 Manjeet Singh FOLLOWED; WSB-T-015 Angad Singh Titaria FOLLOWED (both intern mirror copies, NOT_VERIFIED_ON_OFFICIAL_COPY)", ""),
    ("RAJBIR-1", "DCLR-SC-2015-N09", "C5-SRC-J-SC-2015-RAJBIR~C1", "UOI v Rajbir Singh (13-02-2015)",
     "Applicability under the 2008 Entitlement Rules / 2023 framework of the burden-and-reasons approach",
     "WSB-T-008 / case_relations: N.C. Isaac QUALIFIED_FOR_LATER_REGIME; NOT_OVERRULED; cases_53 scope_and_caveats warn against extension to the 2023 framework", ""),
    ("RAJBIR-2", "DCLR-SC-2015-N09", "C5-SRC-J-SC-2015-RAJBIR~C1", "UOI v Rajbir Singh (13-02-2015)",
     "Followed in later judgments", "WSB-T-014, WSB-T-015 FOLLOWED (intern mirror copies)", "Pinpoints must name the copy: C1 judgment ends p.20, C2 ends p.18"),
    ("NSY-1", "(not in cases_53)", "C5-SRC-J-SC-2019-NS-YADAV~C1", "Ex Cfn Narsingh Yadav v UOI (03-10-2019)",
     "Subsequent treatment of the holding on undetectable diseases and Review Medical Boards; effect of 2008/2023 entitlement regimes",
     "No WS-B row has N S Yadav as the earlier judgment; it appears only as the later judgment in WSB-T-006", "No case record exists; consider whether one is needed (identity label 'N S Yadav' vs printed 'Narsingh Yadav')"),
    ("GIRISH-1", "DCLR-SC-2026-007", "C5-SRC-J-SC-2026-GIRISH-FEB~C1", "UOI v Sgt Girish Kumar, 2026 INSC 149 (12-02-2026)",
     "Effect of the 12-10-2026 clarification order on the arrears holding",
     f"{C53}#DCLR-SC-2026-007.scope_and_caveats: 'Read together with the Supreme Court clarification dated 12 October 2026'; DCLR-SC-2026-008 identity UNRESOLVED (identity_resolution_cycle3 GIRISH_CLAR; no copy in hand); WS-B crosswalk notes PEN-J-06 is 2026 INSC 1113",
     "Clarification not held; content unverified"),
    ("GIRISH-2", "DCLR-SC-2026-007", "C5-SRC-J-SC-2026-GIRISH-FEB~C1", "UOI v Sgt Girish Kumar (12-02-2026)",
     "Later treatment, incl. Mullikote's reference to Girish on limitation", "WSB-T3-003: Mullikote (2026 INSC 286) pp.26-27 para 43 quotes Girish reaffirmation; question left open; case_relations: Girish DISTINGUISHED Tarsem (N10), FOLLOWED A08", ""),
    ("MULLIKOTE-1", "DCLR-SC-2026-N16", "C5-SRC-J-SC-2026-MULLIKOTE~C1", "UOI v Balakrishnan Mullikote, 2026 INSC 286 (24-03-2026, corrected)",
     "Which text is authoritative: the CORRECTED pp.1-31 or the pp.32-62 version; what the correction changed",
     "OI-03 OPEN (two versions, service no. 2568912 M vs 256812 M); WSB-H3-013 supersedes cycle-1 WSB-H-030 for citation; cases_53 source_note flags duplication",
     "C8 text comparison: only cover markings, service number, one name spelling and auto-numbering differ"),
    ("MULLIKOTE-2", "DCLR-SC-2026-N16", "C5-SRC-J-SC-2026-MULLIKOTE~C1", "UOI v Balakrishnan Mullikote (24-03-2026)",
     "Court statement vs quoted regulation (condonation 'twelve months' vs quoted 'upto six months' in para 125 of 1961 Regulations)", "OI-04 OPEN; holdings WSB-H3-009", "Legal reading required"),
    ("MULLIKOTE-3", "DCLR-SC-2026-N16", "C5-SRC-J-SC-2026-MULLIKOTE~C1", "UOI v Balakrishnan Mullikote (24-03-2026)",
     "Subsequent treatment and any review/curative proceedings; interaction with Pension Regulations 2008 amendments", "cases_53 post_decision_treatment_status NOT_EXHAUSTIVELY_CHECKED; no WS-B row with Mullikote as earlier judgment", ""),
]


def main():
    out = Path(sys.argv[1])
    cols = ["lead_id", "case53_id", "copy_id", "judgment", "question_requiring_examination", "corpus_currently_says", "c8_note", "status"]
    with open(out / "subsequent_treatment_leads.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(cols)
        for r in L:
            w.writerow(list(r) + ["RESEARCH_LEAD_UNVERIFIED"])
    print(len(L))


if __name__ == "__main__":
    main()
