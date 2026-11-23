#!/usr/bin/env python3
"""Reviewer C (procedure) - CALIBRATION-02. Builds findings.csv and page_image_checks_C.csv (stdlib only).

Deterministic: rerunning rewrites both files byte-identically. Every proposition in propositions.csv gets at
least one row; propositions without a specific assessment below get an explicit default row whose state is
stated (never silently VERIFIED). Evidence states follow the CALIBRATION-02 README. Compilations (India Code)
are comparison text: a reading taken from them is SUPPORTED_BY_SECONDARY_SOURCE_ONLY even when page-image
checked. VERIFIED_AGAINST_HELD_PRIMARY_SOURCE is used only for Gazette facsimiles (Army Rules 1954; S.R.O.
17(E)/1993) or an official judgment PDF, read from a page image listed in page_image_checks_C.csv.
DATABASE ONLY. Evidence review, not legal approval.
"""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
C2 = HERE.parents[1]
COLS = ["finding_id", "reviewer", "record_id", "proposition_id", "dimension", "evidence_state", "defect_class",
        "severity", "source_identity", "source_sha256", "locator", "version_or_date_note", "finding",
        "proposed_correction", "rationale", "missing_evidence", "legal_advisor_question", "uncertainty", "method"]

# ---------------------------------------------------------------- held sources (scratchpad-relative path; sha256)
S = {
    "AA": ("Army Act 1950, India Code compilation PDF 'as on 21-07-2025' (downloads/independent-reviewer-A/army-act.pdf; GOVERNMENT_COMPILATION, comparison text only)",
           "e47a4265813e95b491a24926428ed306cfeaae9013e7edb928cefef6e69a7c08"),
    "AR54": ("Army Rules 1954 as notified, Gazette of India Pt II s.4, 27-11-1954 (downloads/discovery/ia_in.gazette.central.w.1954-11-27.103686.pdf; archival facsimile of official Gazette)",
             "c5ef95a9d553685aa655f041b71d8360d6272e2775a19a3d6e7273c6cbd0aca6"),
    "SRO93": ("S.R.O. 17(E)/1993, Gazette of India Extraordinary Pt II s.4, 06-12-1993 (downloads/independent-reviewer-D/amend/in.gazette.central.e.1993-12-06.16490/16490.pdf)",
              "e9bf2114ab633716ea954db6e100be858e45949384f9fc0667364308bff46912"),
    "ARIC": ("Army Rules 1954, India Code compilation PDF with annotated notes (downloads/independent-reviewer-A/army-rules.pdf; GOVERNMENT_COMPILATION, comparison text only)",
             "48f52219121bf74d070bc832e4573f2f512b239e0a0441ba96b1daca2983a727"),
    "AFT": ("Armed Forces Tribunal Act 2007, India Code compilation PDF (downloads/independent-reviewer-A/aft.pdf; GOVERNMENT_COMPILATION, comparison text only)",
            "665863d1abb802f7488eb75f776946e30e72ccec16962da8e2b3ee8f2e023e3b"),
    "MML2": ("MML 2.pdf (mml_x/originals; UNVERIFIED_MANUAL, edition unverified; never authority)",
             "db2119182ed2e4ccca22dd225d955327f6398ee98303e1c94615ba85b4396f65"),
    "VK": ("Union of India v Ex Sep Virendra Kumar, SC CA 9267/2019, 07-01-2020 (downloads/procedure-auditor/sc_2020_virendra_kumar_ca9267-2019.pdf)",
           "0ff9d2fc8ef36dfebe862739e517b5ec51f4fff9b4f9b3f7b86beece5d85e819"),
    "GILL": ("Union of India v P S Gill, SC Crl.A 404/2013, 27-11-2019 (downloads/citation-codes/psgill_2019.pdf)",
             "7c32b8e87984c9f3dd52218f9030dffad3ea5aedc98d256744fd5e97d044a0ac"),
    "PD": ("Union of India v Parashotam Dass, SC 2023 (downloads/independent-reviewer-B/parashotam_2023.pdf)",
           "fe19875b19ed5a4efa257273cd2fb1f1cbb57c4f383117cc40e9a90046568377"),
    "ARJ": ("Arjun Panditrao Khotkar v Kailash Kushanrao Gorantyal, SC 2020 (downloads/judgment-auditor/arjun_2020.pdf)",
            "9c3d7880471fe22f5be2a501bbff40d5b93e32670a37903e04af4dcd92b4aebc"),
    "BSA": ("Bharatiya Sakshya Adhiniyam 2023, India Code PDF (downloads/independent-reviewer-B/bsa_2023.pdf; compilation)",
            "554b2b4ae3d9f09bf31e6e1ba2b2cb8a4e7f4f5ffd6f3156736752cbbce116d5"),
    "BNSS": ("Bharatiya Nagarik Suraksha Sanhita 2023, India Code PDF (downloads/independent-reviewer-A/bnss.pdf; compilation)",
             "572c79880b9f8effc8fa6e39b864101835a0fb5d85b194b90a99d170121a0562"),
    "PPS": ("Lt Col Prithi Pal Singh Bedi v Union of India, SC (downloads/citation-codes/ppsbedi_judis9884.pdf)",
            "211dbaf4e20371cc476d09c158e41b976786d57f67336ff6fc802170178b3cca"),
    "NONE": ("none held", ""),
}

# ---------------------------------------------------------------- page-image checks made by Reviewer C (new renders)
PIC = [
    ("C-PIC-01", "SRO93", "PDF p.14 (printed p.14)", "full page", "r.22 as substituted (item 5) incl. proviso to (1) on r.180, (3)(a)-(d) and 'or' between proviso conditions (a)/(b); r.25 omitted (item 6); r.26(1) words omitted (item 7)", 110, "d8cfe8126086f554faf4c790422e196b1886c830b88f6afc2efb2aa6ea9f4218",
     "Item 5 substitutes r.22: (1) hearing by CO in presence of accused, full liberty to cross-examine, call witnesses, make statement; proviso: where charge arises from a court of inquiry in which r.180 complied with for that accused, CO may dispense with sub-rule (1); (2) dismissal duty and proviso re s.120(2); (3) 'within a reasonable time' (a) s.80 per Appendix III, (b) refer to proper superior military authority, (c) adjourn for evidence to be reduced to writing, (d) if accused below rank of warrant officer, SCM, proviso conditions (a) '...without any reference to that officer; or' (b) grave reason; (4) fresh charges on evidence. Item 6: r.25 omitted. Item 7(i): words 'or (in the case of an officer where there is no summary of evidence) an abstract of the evidence to be adduced' omitted from r.26(1)."),
    ("C-PIC-02", "SRO93", "PDF p.18 (printed p.18)", "full page", "Item 36 substitution of r.182; item 35 insertion of r.179(5A); item 34 omission of rr.172-176 (field punishment)", 110, "15dca9c3e09d93a568c4f5c98e4e5669047d81081d57a93ae545f66b0bc29b11",
     "Item 34: heading 'SECTION 7 - Field Punishment' and rr.172-176 omitted. Item 35: r.179(5A) inserted (witness summons by officer assembling the court). Item 36: r.182 substituted, with proviso 'Provided that nothing in this rule shall prevent the proceedings from being used by the prosecution or the defence for the purpose of cross-examining any witness'."),
    ("C-PIC-03", "SRO93", "PDF p.18, right column lower part", "crop x 50-100%, y 72-100%", "Exact wording of substituted r.182 as printed (second reading at 300 dpi)", 300, "93de727d0a11922f9d556d302267e095dcc16afcefa06cb75ee3d807523951bd",
     "As printed: '...or answer to a question made or given at a court of inquiry, shall not be admissible in nor shall any evidence respecting the proceedings of the court be given against any such person except upon the trial of such person for wilfully giving false evidence before the court;' The words 'evidence against a person subject to the Act,' (present in the 1954 r.182, MML 2 p.222 and the India Code compilation p.197) do not appear on the Gazette image. Corrigendum not searched."),
    ("C-PIC-04", "AR54", "PDF p.10 (printed p.300)", "full page", "r.23(1)-(6) and r.24 as notified 1954", 110, "d0ec32fe41d3a3fa8061afb495921a432c3cbb00319f6e12eb62697ff5dad950",
     "r.23(1) evidence of witnesses present before CO 'whether against or for the accused' and other relevant persons taken down in writing in presence and hearing of accused before CO or such officer as he directs; (2) cross-examination; (3) read over, signed; caution wording (reserved CONFLICTING item, not re-read here); (4) English, interpreted; (5) if a person cannot be compelled to attend or attendance cannot in the opinion of the officer taking the summary (to be certified by him in writing) be readily procured, a written statement purporting to be signed by him may be read to the accused and included in the summary; (6) summons. r.24(1)(a)-(c) remand / refer / re-hear; (2) assemble SCM or apply to convene without unnecessary delay."),
    ("C-PIC-05", "AR54", "PDF p.11 (printed p.301)", "full page", "r.25 (later omitted), r.26 summary disposal of officers/JCOs/WOs, r.27 delay reports as notified 1954", 110, "9436eecf6521ca16667ec55b5d00b675b4b9e8b71530c80f0ea9b632096bd12a",
     "r.26(1): where officer/JCO/WO remanded for disposal by authority empowered under s.83, 84 or 85, summary of evidence (or abstract) delivered free with copy of charge as soon as practicable and in any case not less than twenty-four hours before the disposal; (2) authority shall, unless he dismisses the charge or accused consented in writing to dispense with attendance of witnesses, hear the evidence in presence of accused; full liberty to cross-examine, call witnesses, make statement; (3) record per Appendix IV, forward with conduct sheet etc. to superior military authority (s.88). r.27 eight-day delay reports; copy to DJAG from 48th day."),
    ("C-PIC-06", "AR54", "PDF p.51 (printed p.341)", "full page", "r.179(3)-(6), r.180, r.181, r.182 as notified 1954", 110, "c167908345a920debd69d737add5e579bf131d8db44699eca23428049fb26618",
     "r.180 full opportunity to be present throughout, make statement, give evidence, cross-examine witnesses affecting character or military reputation, produce witnesses; presiding officer to ensure notice. r.182 (1954) bars CoI proceedings/confession/statement/answer as evidence against a person subject to the Act except on trial for wilfully giving false evidence; NO proviso in the 1954 text."),
    ("C-PIC-07", "AR54", "PDF p.52 (printed p.342)", "full page", "r.183(2)-(5), r.184 (1954), r.185, r.186(1) as notified 1954", 110, "54274be6293e5c46edf34a8b176783d961b7a363351999dfc89d4c5905f44299",
     "r.185(1): whenever weapon/part forming part of equipment of a squadron, battery, company or similar unit, in respect of which a fine may be imposed under r.186, is lost or stolen, a court of inquiry 'shall be assembled, under the orders of the officer commanding the army, army corps, division or independent brigade'; (2) record opinion. r.186(1) (1954 text) formation commander records opinion and may impose collective fines on JCOs, WOs, NCOs and men."),
    ("C-PIC-08", "AA", "PDF p.27 (printed p.27)", "full page", "ss.75-80 (s.79 pathways; s.80 persons other than officers/JCOs/WOs)", 110, "d1a781db436a6cc6d6dc2edd9670c38c38bd997fb0559eef1c6be2be07be0f13",
     "s.75, s.76 shown omitted by Act 37 of 1992 (compilation note 'w.e.f. 6-9-1992' recorded as printed, not adopted). s.79: punishments without court-martial 'in the manner stated in sections 80, 83, 84 and 85'. s.80: CO or officer specified by COAS with Central Government consent may proceed against a person subject to the Act 'otherwise than as an officer, junior commissioned officer or warrant officer'; clauses (a)-(i); cl.(j) omitted by Act 37 of 1992."),
    ("C-PIC-09", "AA", "PDF p.28 (printed p.28)", "full page", "ss.81-85 limits and authorities for officers/JCOs/WOs", 110, "18fed6b23bb53812ee7013c014b61ec1026987e52ccacfd56bf2e34de1001477",
     "s.81(1) omitted (Act 37/1992); (2) sequencing; (3) aggregate 42 days; (4) (a),(b),(c) not to NCO or person who was NCO at time of offence; (5) reprimand not below NCO. s.82 COAS may specify other punishments. s.83 brigade-level commander etc.: officer below field officer, JCO, WO - reprimand, stoppage. s.84 area-level commander or GCM-convening officer etc.: officer below Lt Col, JCO, WO - (a) forfeiture of seniority 'subject to the right of the accused previous to the award to elect to be tried by a court-martial', (b), (c). s.85 CO etc. may proceed against a junior commissioned officer (only)."),
    ("C-PIC-10", "AA", "PDF p.34 (printed p.34)", "full page", "ss.113-120 composition, dissolution, DCM and SCM powers", 110, "e95a3e19ac8453d49c383528e6684602cee10bf53c325cbec5ec4e5bd3f2da2f",
     "s.117(2) dissolution where illness of judge advocate or accused 'before the finding' makes continuation impossible; s.119 DCM: any person other than officer or JCO; no death, transportation, imprisonment over two years; proviso: no imprisonment of a warrant officer. s.120(2) reference requirement (ss.34, 37, 69, offence against officer holding court); (3) excludes officer, JCO, WO; (4)-(5) one year if Lt Col and upwards, three months if below."),
    ("C-PIC-11", "AA", "PDF p.35 (printed p.35)", "full page", "ss.121-123 bar, limitation, post-cessation liability", 110, "2096197700a4375cd53131f5b396129a49c9759f6b84fb298b464ab419ea376e",
     "s.121 second trial bar includes persons dealt with under ss.80, 83, 84, 85. s.122(1) three years; commencement (a)-(c) as substituted by Act 37 of 1992 s.9; (2) desertion, fraudulent enrolment, s.37 excepted; (3) exclusions; (4). s.123(1)-(4); (2) three years after ceasing to be subject (substituted by Act 37 of 1992 s.10) with exclusions; proviso for desertion, fraudulent enrolment, s.37 offences and criminal-court jurisdiction."),
    ("C-PIC-12", "AA", "PDF p.36 (printed p.36)", "full page", "ss.124-131 (s.125 choice of forum; s.126; s.127 omitted; s.130 challenges)", 110, "65bf8be6845689b1ccfcc661b8a7734e3a32bf446dc7be2f1c1657908af62b28",
     "s.125 discretion of officer commanding the army, army corps, division or independent brigade in which accused is serving or such other officer as may be prescribed; s.126 written notice by criminal court; reference to Central Government final; s.127 shown omitted by Act 37 of 1992 s.11. (s.129 visible on page; reserved OPEN item, not assessed.)"),
    ("C-PIC-13", "AFT", "PDF p.6 (printed p.6)", "full page", "s.3(o) service matters: inclusions and exclusions", 110, "a094d662ba7bc6c8b442bf8794b88c5cb81e3aba5f18f9decc6b80b0fe87a6d2",
     "s.3(o) includes (i) remuneration, pension; (ii) tenure incl. termination, penal deductions; (iii) 'summary disposal and trials where the punishment of dismissal is awarded'; (iv) any other matter; excludes (i) orders under AA s.18; (ii) transfers and postings; (iii) leave; (iv) 'summary court-martial except where the punishment is of dismissal or imprisonment for more than three months'."),
    ("C-PIC-14", "AFT", "PDF p.11 (printed p.11)", "full page", "ss.21-22 exhaustion and limitation for applications", 110, "4d9c8b97aabd4679e1e88e74989c3b4791e0a8025d7a2aec4a4e28d189f700ee",
     "s.21(1) Tribunal shall not ordinarily admit an 'application' unless remedies under the Act/rules/regulations availed; (2)(a) final order rejecting petition/representation, (b) six months without final order. s.22(1)(a)-(c) six months from final order etc.; (2) condonation for sufficient cause."),
    ("C-PIC-15", "ARIC", "PDF p.197", "full page", "r.180 end, r.181, r.182 opening in compilation", 110, "d3c0297f9c285001cde57721a104584f67b1eea51d778c331160293fc7d65476",
     "Compilation r.182 reads '...shall not be admissible in evidence against a person subject to the Act, nor shall any evidence respecting the proceedings ... before the courts:-' (no amendment note on the page)."),
    ("C-PIC-16", "ARIC", "PDF p.198", "full page", "r.182 proviso in compilation", 110, "533c6bde8bd324939dc10e6c8334ee8e97029f5f7e2e0da081f480aa63d7f8f4",
     "Compilation prints the proviso on use for cross-examining any witness; note 'See AA.s. 60'."),
    ("C-PIC-17", "MML2", "PDF p.222 (printed 222)", "full page", "MML comparison of r.179(5A), r.180, r.182", 120, "8a85c32be1f9c0f60e3dd4241dca2bed19119e5b9901270efe1803afbaf83489",
     "MML 2 brackets r.179(5A) with note 'Inserted by SRO 17(E), dated 6th December, 1993' and r.182 with note 'Subs by SRO 17(E), dated 6th December, 1993'; MML r.182 includes 'in evidence against a person subject to the Act,' and the proviso. Footer '2188-D (Comm PM7)'. Manual, not authority."),
    ("C-PIC-18", "VK", "PDF p.17 (printed 17)", "full page", "Virendra Kumar paras 12(b)-(d) and 13 on r.180 objections", 110, "a2b2217af7c37c196cfb51c0e7535929e9a5af3b84cf075ccd7041b7d4bb65ce",
     "Para 12(c): conviction on full CM trial; earlier-stage irregularities cannot be the basis for setting aside; 12(d): if accused raises r.180 non-compliance during framing of charge or recording of summary of evidence, authorities have to rectify; para 13: not raised at charge, SoE or CM stage, cannot be raised after final CM order."),
    ("C-PIC-19", "GILL", "PDF p.17 (printed 17)", "full page", "P S Gill paras 13-14: s.15 not maintainable against convening order", 110, "794223b6bb51936e7cd4b223486080f0586c952001e3199b67d1ead82d985267",
     "Para 14: order convening GCM is not an order, decision, finding or sentence by a court-martial; 'an appeal under Section 15 per se is not maintainable'. Para 15 begins: s.14 application in any service matter. Quotes s.3(o) exclusion (iv)."),
]
PICD = {p[0]: p for p in PIC}


def loc(pic, extra=""):
    p = PICD[pic]
    return f"{p[2]}; render {pic} sha256 {p[6]}" + (f"; {extra}" if extra else "")


M_IMG = "Wording read from page-image render listed in page_image_checks_C.csv (PyMuPDF 2.1); compared with the record text"
M_TXT = "Text layer of held file used to locate only; wording not relied on beyond what is stated"
M_AN = "Reviewer procedural analysis of the record text against held Act/Rules readings cited; no new wording relied on"
M_NA = "Classified from record text; design, heading or workflow statement"

rows = {}


def F(pid, state, defect, sev, src="NONE", locator="", ver="", finding="", corr="", rat="", miss="", laq="", unc="", method=M_AN, dim="PROCEDURE"):
    rows.setdefault(pid, []).append(dict(dimension=dim, evidence_state=state, defect_class=defect, severity=sev,
                                         source_identity=S[src][0], source_sha256=S[src][1], locator=locator,
                                         version_or_date_note=ver, finding=finding, proposed_correction=corr,
                                         rationale=rat, missing_evidence=miss, legal_advisor_question=laq,
                                         uncertainty=unc, method=method))


def NA(pid, note="Design, heading, question or workflow statement for the eventual application; no procedural legal content to assess."):
    F(pid, "NOT_A_LEGAL_PROPOSITION", "NONE", "NONE", finding=note, method=M_NA)


def SNH(pid, what, note="", sev="NONE", defect="NONE", corr="", miss=""):
    F(pid, "SOURCE_NOT_HELD", defect, sev, finding=f"Procedure cannot be checked: {what} not held in the CALIBRATION-02 held-source index. {note}".strip(),
      corr=corr, miss=miss or f"Authenticated copy of {what}", method="Held-source index (registers/held_sources_scratchpad.csv) searched by name; not found")


V93 = "S.R.O. 17(E)/1993 published 06-12-1993; commencement as printed: on publication (r.1(2), per WS-A/ARMY-RULES-CHAIN-01 AR-029); effective date not inferred by Reviewer C"
V54 = "Army Rules 1954 as notified 27-11-1954; later amendment chain for this rule per ARMY-RULES-CHAIN-01 only (31 instruments examined; gaps AR-001, AR-030, AR-036)"
VAA = "Compilation 'as on 21-07-2025'; amendment notes as printed in compilation; Act 37/1992 commencement NOT_DETERMINED (WS-A); compilation 'w.e.f.' notes not adopted"
VAFT = "AFT Act compilation (India Code); in force 15-06-2008 per compilation footnote (S.O. 14(E)/2008), not independently verified; Tribunals Reforms Act 2026 (No.17/2026) amends s.9A only (tra2026, text layer)"

# =============================================================== record-by-record assessment
# 1 HCE-033
for p in ["P1", "P2", "P5", "P6", "P7", "P8", "P9", "P10"]:
    NA(f"HCE-033#{p}")
F("HCE-033#P3", "NOT_A_LEGAL_PROPOSITION", "UNSUPPORTED_GENERALISATION", "P3", "AA", loc("C-PIC-09"), VAA,
  "Acceptable as an application design rule, but it must not be read as a statutory precondition: summary powers vest in the authorities named in AA ss.80, 83, 84, 85 (and officers specified by COAS with Central Government consent); JAG advice is not a statutory condition of a valid award.",
  "High-risk decisions remain with the competent authority under the Army Act (ss.80, 83-85, 109-112, 125); seek JAG advice as a matter of policy.",
  "Avoid implying that an award is invalid without JAG advice, or valid because JAG advised.", method=M_IMG)
F("HCE-033#P4", "NOT_A_LEGAL_PROPOSITION", "NONE", "NONE", "AA", loc("C-PIC-09"), VAA,
  "Design rule is procedurally sound: rank at offence matters (AA s.81(4) bars s.80(a)-(c) for a person who was an NCO at the time of the offence) and forum/authority depend on present rank (ss.80, 83-85, 119, 120(3)).", method=M_IMG)
F("HCE-033#REF", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "HISTORICAL_VERSION", "P3", "SRO93", loc("C-PIC-01", "item 6"), V93,
  "Reference range 'AR: rr 22-26' includes r.25, which S.R.O. 17(E)/1993 item 6 omitted; r.22 was wholly substituted by item 5. '[AO]' is an unresolved code (not held).",
  "[AA: ss 79-88]; [AR: rr 22-24, 26 (r.22 as substituted and r.25 omitted by S.R.O. 17(E)/1993)]; [AO: identify instrument]", method=M_IMG)

# 2 HCE-001
F("HCE-001#P1", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "NONE", "NONE", "SRO93", loc("C-PIC-01", "r.22(3)(a)-(d)"), V93,
  "Consistent: r.22(3) as substituted separates summary disposal (s.80), reference to superior authority, adjournment for summary of evidence and SCM; AA s.79 recognises non-CM pathways (C-PIC-08).", method=M_IMG)
F("HCE-001#P2", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-08"), VAA,
  "Consistent with AA s.80 (person other than officer/JCO/WO; CO or specified officer), ss.83-85 (authority by rank of accused and of awarding officer).", method=M_IMG)
F("HCE-001#P3", "NOT_A_LEGAL_PROPOSITION", "NONE", "NONE", finding="Correct caution; consistent with SOURCE_AUTHORITY_POLICY v1 (manual/notes are not authority).", method=M_NA)
F("HCE-001#P4", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-09"), VAA,
  "Consistent: rank at offence and present rank both matter (s.81(4); ss.83-85; s.120(3)).", method=M_IMG)
F("HCE-001#P5", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-11"), VAA,
  "Consistent: 'date of act/knowledge' matches s.122(1)(a)-(c) (knowledge and identity triggers, as substituted by Act 37 of 1992 s.9).", method=M_IMG)
F("HCE-001#P6", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "OMISSION", "P3", "SRO93", loc("C-PIC-01", "proviso to r.22(1)"), V93,
  "Correct that a CoI is not a prerequisite. Omits the linkage in the substituted r.22(1) proviso: where the charge arises from a CoI in which r.180 was complied with for that accused, the CO may dispense with the r.22(1) hearing; where a CoI affects character or military reputation, r.180 participation is obligatory (Virendra Kumar para 12(b),(d)).",
  "Add: 'If a CoI was held and r.180 was complied with for the accused, the CO may dispense with the r.22(1) hearing (r.22(1) proviso); if r.180 was not complied with, the hearing cannot be dispensed with on that basis.'", method=M_IMG)
F("HCE-001#P7", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-08"), VAA,
  "Consistent: ss.80, 83, 84, 85 extend summary power to 'such other officer as is, with the consent of the Central Government, specified by the Chief of the Army Staff', so current specifications/delegations must be checked.", method=M_IMG)
NA("HCE-001#P8", "Risk label; consistent with r.22 (hearing of charge) vs court-martial trial. No defect.")
NA("HCE-001#P9", "Risk label; consistent with source-authority policy. No defect.")
F("HCE-001#P10", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "OMISSION", "P3", "AA", loc("C-PIC-09"), VAA,
  "Risk label is right but states no positive rule. A CO may award s.80 punishments only to persons other than officers/JCOs/WOs, and under s.85 may deal only with a JCO (and not award reprimand if below Colonel - s.85 proviso, Act 37/1992 s.6); officers and WOs are dealt with under ss.83/84 by brigade/area-level or specified authorities.",
  "Replace with: 'A CO's summary powers are limited to s.80 (below JCO/WO) and s.85 (JCOs); officers and warrant officers are dealt with summarily only under ss.83-84.'", method=M_IMG)
F("HCE-001#REF", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "NONE", "P3", "SRO93", loc("C-PIC-01"), V93,
  "References usable. Note: r.36 list was amended by S.R.O. 17(E)/1993 item 9 (figure 25 omitted) per WS-C PC-04; vol 2(AR) DOC text of r.36 must not be used.", method=M_IMG)

# 3 ADM-013
SNH("ADM-013#P1", "the Army censure policy (authenticated version)", "Procedure note: censure is an administrative action, not an award under AA ss.80-85 or s.71; redress lies by statutory complaint (AA ss.26-27) and then AFT s.14 subject to s.21/s.22.")
SNH("ADM-013#P2", "Kuldeep Yadav (SC 2019) judgment", "Holding is a Reviewer B matter.")
F("ADM-013#P3", "SOURCE_NOT_HELD", "OMISSION", "P3", "AFT", loc("C-PIC-14"), VAFT,
  "Checklist is procedurally sensible. It should name the statutory-complaint route (AA ss.26-27 for officers; text not image-checked here) and the AFT s.21 exhaustion and s.22 six-month limitation from the final order on that complaint, which drive the timing of any challenge.",
  "Add: 'Record date of final order on statutory complaint; AFT s.21/s.22 run from it (s.22(2) condonation).'", method=M_IMG)
SNH("ADM-013#REF", "the censure policy instrument")

# 4 ADM-026
F("ADM-026#P1", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "MISSING_EXCEPTION", "P3", "AFT", "AFT Act s.14(5), compilation PDF p.9 (text layer locator only)", VAFT,
  "Restraint on proportionality review is a Reviewer B question (Kuldeep Yadav not held). Procedurally, the statement that the Tribunal 'is not an ordinary merits appeal' should be reconciled with AFT s.14(5): the Tribunal 'shall decide both questions of law and facts'. Over-stating restraint could mislead a practitioner framing an OA.",
  "Add: 'AFT s.14(5) requires the Tribunal to decide questions of fact and law; the restraint described concerns substitution of penalty gradation.'",
  unc="s.14(5) wording read from text layer only.", method=M_TXT)
F("ADM-026#P2", "NOT_A_LEGAL_PROPOSITION", "NONE", "NONE", finding="Assessment checklist is procedurally sound (competent authority, show-cause, application of mind, complaint and AFT record).", method=M_NA)
SNH("ADM-026#REF", "Kuldeep Yadav (2019) judgment")

# 5 CM-001
F("CM-001#P1", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "ARIC", "r.177(1) compilation PDF p.194 (text layer locator only)", "r.177 substituted by S.R.O. 8(E)/2003 (ARMY-RULES-CHAIN-01 AR-031); DOC r.177 pre-2003 (WS-C PC-19)",
  "Consistent: CoI collects evidence and reports (r.177); hearing of charge r.22; summary punishment AA ss.80-85; court-martial ss.108ff.", method=M_TXT)
F("CM-001#P2", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-10"), VAA,
  "Consistent with ss.118-120 (forum limits by rank and command) and s.122/s.123 time limits (C-PIC-11).", method=M_IMG)
NA("CM-001#P3", "Record-keeping step; consistent with s.123 (status at offence and at cessation). No defect.")
F("CM-001#P4", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "OMISSION", "P3", "AA", loc("C-PIC-12"), VAA,
  "'Considering civil-offence jurisdiction' should name the decision rule: where a criminal court and court-martial both have jurisdiction, the forum choice rests with the officer under s.125 (formation commander or prescribed officer), subject to s.126; s.70 restricts court-martial trial of certain civil offences (text not image-checked here).",
  "Add: 'apply AA ss.69-70 and the s.125/s.126 forum decision (not a unit CO decision)'.", method=M_IMG)
NA("CM-001#P5", "Step consistent with ss.109-112 convening powers and s.120(2) reference. No defect.")
F("CM-001#P6", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "NONE", "NONE", "SRO93", loc("C-PIC-02", "item 36"), V93,
  "Consistent. Add for completeness that CoI statements are inadmissible against the person except as r.182 (substituted 1993) allows (perjury trial; cross-examination use).", method=M_IMG)
F("CM-001#P7", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "HISTORICAL_VERSION", "P3", "AA", loc("C-PIC-12"), VAA,
  "Range 'AA ss.108-127' includes s.127, shown omitted by Act 37 of 1992 s.11 in the compilation.",
  "AA ss.2, 108-126 (s.127 omitted by Act 37 of 1992)", method=M_IMG)
F("CM-001#P8", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "NONE", "P3", "SRO93", loc("C-PIC-01"), V93,
  "Usable, but rr.33(7) and 36 were amended by S.R.O. 17(E)/1993 (abstract-of-evidence words and figure 25 omitted; WS-C PC-03/PC-04); MML vol 2(AR) DOC readings of r.36 must not be used.", method=M_IMG)
NA("CM-001#P9", "Reference fragment 'AFT s.15'; correct statutory appeal pointer. No defect.")
F("CM-001#REF", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "HISTORICAL_VERSION", "P3", "AA", loc("C-PIC-12"), VAA,
  "Same as P7: s.127 omitted by Act 37 of 1992.", "AA ss.2, 108-126; AR rr.33-36 (as amended 1993); AFT s.15", method=M_IMG)

# 6 CM-040
for p in ["P1", "P2", "P3", "P4", "P5", "P6"]:
    NA(f"CM-040#{p}")
for p in ["P7", "P8", "REF"]:
    SNH(f"CM-040#{p}", "the cited Army Order / information-security regulations ([AO not acquired], [VERIFY])")

# 7 EV-011
NA("EV-011#P1", "Heading 'CORE PRINCIPLE:'.")
F("EV-011#P2", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "NONE", "NONE", "AR54", loc("C-PIC-04", "r.23(5)"), V54 + "; r.23: NO AMENDMENT LOCATED (chain); r.23(3) CONFLICTING reserved, not assessed",
  "Consistent with r.23(5): a written statement 'purporting to be signed' may be read to the accused and included where the person cannot be compelled to attend or attendance cannot, in the certified written opinion of the officer taking the summary, be readily procured.", method=M_IMG)
F("EV-011#P3", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "ARIC", "r.23 note 10, compilation PDF p.43 (text layer)", "Compilation note, not rule text",
  "Consistent with the compilation note that such a witness must attend in person at the trial, and with AA ss.135, 137-138 (summons, commissions). Note is commentary, not law.", method=M_TXT)
NA("EV-011#P4", "Heading 'ASSESSMENT:'.")
F("EV-011#P5", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "WORDING_ERROR", "P3", "AR54", loc("C-PIC-04", "r.23(5)"), V54,
  "'Provide statement to accused as required' is vague: r.23(5) requires the statement to be read to the accused and included in the summary; the certificate is the opinion of the officer taking the summary, in writing.",
  "'record the certified written opinion of the officer taking the summary; read the signed statement to the accused and include it in the summary (r.23(5))'", method=M_IMG)
NA("EV-011#P6", "Records list. No defect.")
F("EV-011#P7", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "NONE", "NONE", "AR54", loc("C-PIC-04", "r.23(5)"), V54,
  "Consistent: r.23(5) requires a statement 'purporting to be signed by him'; an unsigned officer summary does not meet it.", method=M_IMG)
F("EV-011#REF", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "NONE", "NONE", "AR54", loc("C-PIC-04"), V54, "Pinpoint r.23(5) is correct.", method=M_IMG)

# 8 KB-030
NA("KB-030#P1")
NA("KB-030#P2")
F("KB-030#P3", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "NONE", "NONE", "VK", loc("C-PIC-18"), "Judgment 07-01-2020; later treatment is a Reviewer B matter",
  "Escalation list is procedurally sound. Supporting point: under Virendra Kumar paras 12(d)-13 an r.180 objection raised at hearing of charge or summary of evidence obliges the authorities to rectify; this is time-critical and justifies escalation.", method=M_IMG)
NA("KB-030#P4")
NA("KB-030#REF", "Reference list (SRC-AA ss.2, 79-85, 108-130; SRC-AR rr.22, 180; SRC-AFT ss.14-15); appropriate pointers. s.129 within range is a reserved OPEN item, not assessed.")

# 9 CM-026
F("CM-026#P1", "INTERPRETATION_REQUIRES_LEGAL_ADVICE", "OMISSION", "P2", "ARJ", "Conclusion paras (text layer); BSA s.63 and s.170 (bsa text layer)", "AA s.133 applies the Indian Evidence Act 1872 'subject to the provisions of this Act'; IEA repealed by BSA 2023 s.170 from 1 July 2024",
  "Omits the existing statutory condition for electronic records: in proceedings governed by the IEA, a s.65B(4) certificate is a condition precedent to admissibility (Arjun Panditrao, affirming Anvar); BSA 2023 s.63 is the successor provision. A court-martial applies the evidence law through AA s.133. 'Independent proof of authenticity, custody' without the certificate could lead to inadmissible evidence.",
  "Add: 'Electronic records require the statutory certificate (IEA s.65B(4) for proceedings to which the IEA applies; BSA 2023 s.63 thereafter), applied to courts-martial through AA s.133, plus custody evidence.'",
  miss="Page-image reading of Arjun Panditrao conclusion; BSA s.63/s.170 page image; transitional position for courts-martial",
  laq="From what date, and for which pending proceedings, does AA s.133 read as a reference to BSA 2023 (General Clauses Act s.8; BSA s.170 savings)?",
  unc="Judgment and BSA wording read from text layer only.", method=M_TXT, dim="PROCEDURE")
F("CM-026#P2", "INTERPRETATION_REQUIRES_LEGAL_ADVICE", "WORDING_ERROR", "P2", "BSA", "BSA s.63 (text layer line 1802)", "BSA 2023 in force 1 July 2024 (not re-verified here)",
  "'Not invent new statutory certification rules' is correct in intent but misleading: a statutory certification rule already exists (IEA s.65B(4) / BSA s.63) and must be recorded, not treated as best practice.",
  "'...record evidentiary steps as best practice and identify the existing statutory certificate requirement (IEA s.65B(4) / BSA s.63) rather than inventing any further rule.'",
  miss="Page image of BSA s.63", unc="Text layer only.", method=M_TXT)
NA("CM-026#P3", "Preservation step; sound practice. No defect.")
NA("CM-026#P4", "Preservation step; sound practice. No defect.")
F("CM-026#P5", "INTERPRETATION_REQUIRES_LEGAL_ADVICE", "NONE", "NONE", "ARJ", "text layer", "",
  "'Applicable certification' points in the right direction; see P1 for the specific statutory certificate.", method=M_TXT)
NA("CM-026#P6", "Documentation step; sound practice. No defect.")
F("CM-026#P7", "INTERPRETATION_REQUIRES_LEGAL_ADVICE", "HISTORICAL_VERSION", "P3", "BSA", "BSA s.170 (text layer)", "IEA repealed by BSA 2023 s.170",
  "'AA s.133; applicable evidence law [VERIFY]' should name the instrument by period: IEA 1872 (via AA s.133) for proceedings before 1 July 2024 subject to savings; BSA 2023 thereafter.",
  "AA s.133; IEA 1872 s.65B / BSA 2023 s.63 (by date, subject to BSA s.170 savings)", method=M_TXT)
F("CM-026#P8", "UNSUPPORTED", "CITATION_ERROR", "P3", finding="'AR witness/exhibit procedure' has no pinpoint.", corr="Cite specific rules (e.g. AR rr.134-143 for evidence at trial, after verification).", method=M_AN)
F("CM-026#REF", "INTERPRETATION_REQUIRES_LEGAL_ADVICE", "HISTORICAL_VERSION", "P3", "BSA", "BSA s.170 (text layer)", "", "As P7.", "As P7.", method=M_TXT)

# 10 CM-JD-01
F("CM-JD-01#P1", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-12", "s.130"), VAA,
  "Procedurally consistent: composition (ss.113-115, C-PIC-10), challenge procedure s.130 (C-PIC-12) and eligibility rules (r.39/r.40, not image-checked) govern. Case holding is a Reviewer B matter (PPS Bedi PDF held, not read for wording).", method=M_IMG)
NA("CM-JD-01#P2", "Caution statement; appropriate. No defect.")
F("CM-JD-01#REF", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "PPS", "not read", "",
  "Reference to r.40 and s.130 is apt; 'verify official PDF pages' remains open. s.129 not referenced (reserved item untouched).", method=M_AN)

# 11 COI-003
F("COI-003#P1", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "ARIC", "r.177(1) compilation PDF p.194 (text layer)", "r.177 substituted by S.R.O. 8(E)/2003 (AR-031)",
  "Consistent with r.177(1) ('directed to collect evidence, and, if so required, to report').", method=M_TXT)
NA("COI-003#P2", "Consistent with r.177 and Virendra Kumar para 12(a). No defect.")
F("COI-003#P3", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "OMISSION", "P3", "SRO93", loc("C-PIC-01", "r.22(1) proviso"), V93,
  "Stages are different, but the substituted r.22(1) proviso links them: where the charge arises from a CoI in which r.180 was complied with for the accused, the CO may dispense with the r.22(1) hearing.",
  "Add the r.22(1) proviso.", method=M_IMG)
NA("COI-003#P4", "Consistent with r.182 and r.177. No defect.")
F("COI-003#P5", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "OMISSION", "P2", "VK", loc("C-PIC-18"), "Judgment 07-01-2020",
  "Record cites Virendra Kumar paras 10-13 only for the 'fact-finding character' of a CoI. It omits the procedural rule in paras 12(d)-13 that matters to practitioners: an r.180 non-compliance objection must be raised at the hearing of charge or summary of evidence, where the authorities must rectify it; if not raised before the court-martial concludes, it cannot be raised afterwards. Para 15 (not image-checked) adds that the AFT cannot remand to the CoI stage.",
  "Add: 'If r.180 was not complied with, the objection should be raised at the r.22 hearing or the summary of evidence; the authorities must then rectify. After a final court-martial order the objection cannot be raised (Virendra Kumar paras 12(d), 13).'",
  rat="A defending officer or legal practitioner relying on the record could lose the objection.", method=M_IMG)
F("COI-003#P6", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "WORDING_ERROR", "P2", "SRO93", loc("C-PIC-02", "item 36; second reading C-PIC-03"), V93,
  "'Do not treat all CoI witness statements as admissible substantive evidence' understates r.182: CoI proceedings and any confession, statement or answer are not admissible against a person subject to the Act, and no evidence of the proceedings may be given against him, except on a trial for wilfully giving false evidence; the 1993 proviso permits use by prosecution or defence only to cross-examine a witness. 'Not all' implies some are admissible as substantive evidence.",
  "'CoI proceedings and statements are not admissible as evidence against a person subject to the Act, except on a trial for wilfully giving false evidence before the court; they may be used only to cross-examine a witness (r.182 as substituted by S.R.O. 17(E)/1993).'", method=M_IMG)
F("COI-003#P6", "CONTRADICTORY_EVIDENCE", "WORDING_ERROR", "P2", "SRO93", loc("C-PIC-03"), V93 + "; corrigendum not searched",
  "Wording conflict in r.182 as substituted: the Gazette image of S.R.O. 17(E)/1993 prints 'shall not be admissible in nor shall any evidence...' without 'evidence against a person subject to the Act,'; the 1954 Gazette (C-PIC-06), MML 2 p.222 (C-PIC-17) and the India Code compilation p.197 (C-PIC-15) carry the words. Not registered in ARMY-RULES-CHAIN-01 or WS-A as far as Reviewer C found.",
  "", miss="Corrigendum search for S.R.O. 17(E)/1993 (Gazette Pt II s.4, Dec 1993 - 1994); independent second reading of PDF p.18",
  laq="Is the operative r.182 the text with 'evidence against a person subject to the Act' (per 1954 text and compilation), the Gazette print being a printing omission, or is a corrigendum required?",
  unc="Possible printing slip; no legal effect is asserted.", method=M_IMG, dim="EVIDENCE_QUALITY")
F("COI-003#REF", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "OMISSION", "P3", "SRO93", loc("C-PIC-02"), V93,
  "References omit r.180 (central to the CoI/trial interface) and the 1993 substitution of r.182; r.177 is the 2003 substituted text.",
  "[SRC-AR: rr 177 (as substituted 2003), 180, 182 (as substituted 1993), 22-24]; [SRC-VIR: paras 10-13, 15]", method=M_IMG)

# 12 HCE-008
F("HCE-008#P1", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "NONE", "NONE", "SRO93", loc("C-PIC-01", "r.22(3)(c)"), V93,
  "Consistent: r.22(3)(c) adjournment; r.23(1) adjourned hearing (C-PIC-04).", method=M_IMG)
F("HCE-008#P2", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "NONE", "NONE", "AR54", loc("C-PIC-04", "r.23(1)"), V54 + "; r.23: NO AMENDMENT LOCATED",
  "Consistent with r.23(1) wording as notified.", method=M_IMG)
F("HCE-008#P3", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "ARIC", "r.23 note 1, compilation PDF p.42 (text layer)", "Compilation note, not rule text",
  "Consistent with r.22(3)(c)/r.23(1) and the compilation note that SoE can be ordered only by the accused's CO.", method=M_TXT)
NA("HCE-008#P4", "Workflow step; consistent with r.23. No defect.")
NA("HCE-008#P5", "Workflow step; consistent with r.23(1),(3) (prosecution and defence witnesses). No defect.")
F("HCE-008#P6", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "OMISSION", "P3", "AR54", loc("C-PIC-04", "r.23(2),(4),(5)"), V54,
  "'Effective participation' should name the specific safeguards: right to cross-examine (r.23(2)), interpretation where English not understood (r.23(4)), statement and defence witnesses (r.23(3)), the r.23(5) certificate route. r.23(3) caution wording is the reserved CONFLICTING item and must not be quoted from any single source.",
  "List r.23(2)-(5) safeguards; flag r.23(3) caution text as CONFLICTING.", method=M_IMG)
NA("HCE-008#P7", "Risk label; consistent with compilation note 1 to r.23 (SoE ordered by accused's CO). Note: Virendra Kumar para 10 (Sodhi) applies a prejudice test to r.22/23 non-compliance. No defect.")
NA("HCE-008#P8", "Risk label; consistent with r.23(1). No defect.")
NA("HCE-008#P9", "Risk label; consistent with compilation note 2 to r.23. No defect.")
F("HCE-008#REF", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "NONE", "NONE", "SRO93", loc("C-PIC-01"), V93, "Pinpoints r.22(3)(c) (as substituted 1993) and r.23(1) correct; VK para 10 exists.", method=M_IMG)

# 13 PEN-006
for p in ["P1", "P2", "P3", "P6", "P11"]:
    NA(f"PEN-006#{p}", "Heading/label.")
for p in ["P4", "P5", "P7", "P8", "P9", "P10", "P12", "P13", "P14", "P15", "REF"]:
    SNH(f"PEN-006#{p}", "Pension Regulations for the Army (Part I) (V6-S01 / V6-S02)", "No procedural defect identified on the face of the text.")

# 14 PEN-WF-03
NA("PEN-WF-03#P1", "Numbering fragment.")
for p in ["P2", "P3", "P5", "P6", "REF"]:
    SNH(f"PEN-WF-03#{p}", "DESW FAQ / PBOR scheme instruments (V6-S05, V6-S06)", "No procedural defect identified on the face of the text.")
SNH("PEN-WF-03#P4", "medical-board and first/second appeal instructions (V6-S05)",
    "Procedure note: before AFT, AFT s.21 requires available departmental remedies (first/second appeal against rejection) to be availed or six months to elapse; the workflow should record appeal dates.",
    sev="P3", defect="OMISSION", corr="Add a step: record departmental appeal decisions/dates (AFT s.21(2), s.22).")

# 15 ADM-001
F("ADM-001#P1", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "ARIC", "r.14 note 5, compilation PDF p.20 (text layer)", "Compilation note, not rule text",
  "Consistent with the compilation note that dismissal under r.14 is not a punishment under AA s.71.", method=M_TXT)
NA("ADM-001#P2", "Classification step; sound. No defect.")
F("ADM-001#P3", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "OMISSION", "P3", "AA", "AA s.20 (compilation, text layer)", VAA,
  "Checklist omits AA s.20 (dismissal, removal or reduction by COAS and other officers) as a distinct route with its own rule-based safeguards (r.17, not checked here), and the AA s.121 bar for persons already dealt with summarily (C-PIC-11).",
  "Add AA s.20 / r.17 route and s.121 bar to the classification list.", method=M_TXT)
F("ADM-001#REF", "HISTORICAL_VERSION_UNRESOLVED", "HISTORICAL_VERSION", "P3", finding="'AR rr13-18' spans rules with open or post-MML changes: r.14(4)-(5) 1993 itemisation lead (WS-C PG-04), r.15 reserved OPEN, r.15B inserted 2019 and r.16A amended 2019/2022 (WS-C PG-07/PG-08).",
  corr="Pin each rule to its version and date; keep r.15 OPEN.", miss="WS-A itemisation of S.R.O. 17(E)/1993 for r.14", method=M_AN)

# 16 ADM-CL-02
F("ADM-CL-02#P1", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "OMISSION", "P2", "ARIC", "rr.14-15, compilation PDF pp.17-21 (text layer); r.14 1961 Gazette PIC-30 (ARMY-RULES-CHAIN-01)", "r.14 substituted S.R.O. 205/1961; r.14(4)-(5) 1993 itemisation lead (PG-04); r.15 reserved OPEN",
  "Checklist omits the r.14(2) precondition that the Central Government or COAS be satisfied that trial by court-martial is inexpedient or impracticable (and further retention undesirable) before misconduct termination; omits the show-cause exceptions (r.14(1) proviso: criminal conviction; Central Government satisfaction that notice is not expedient) and the COAS power to withhold adverse reports on security grounds. r.15 covers inefficiency or physical disability per its text, while the compilation note points physical disability to r.15-A.",
  "Add: 'r.14: record CG/COAS satisfaction that court-martial is inexpedient or impracticable; show-cause and disclosure subject to r.14(1) proviso and r.14(2) security proviso; final decision Central Government (r.14(5)). r.15 (reserved OPEN as to authority wording): inefficiency; physical disability - check r.15-A.'",
  rat="Using r.14 without the inexpediency/impracticability satisfaction is a recognised ground of invalidity.", miss="Page-image reading of current r.14 after S.R.O. 17(E)/1993 itemisation", unc="Rule text read from compilation text layer.", method=M_TXT)
F("ADM-CL-02#REF", "UNSUPPORTED", "CITATION_ERROR", "P3", finding="'See linked module provisions' gives no pinpoint.", corr="AR rr.14, 15 (r.15 OPEN), 15-A; AA ss.18-19", method=M_AN)

# 17 ADM-CL-03
F("ADM-CL-03#P1", "HISTORICAL_VERSION_UNRESOLVED", "NONE", "P3", "ARIC", "r.13 table, compilation (text layer)", "r.13 table amended S.R.O. 351/1960, 116/1965, 22/2010 (AR-004, AR-010, AR-032); r.13(2A) inserted 1964 (AR-009)",
  "Checklist is sound and rightly requires an authenticated current table; the table has three recorded amendments and its current form is not verified here. Statutory basis AA s.22 should be named.",
  "Add 'AA s.22; AR r.13 table as amended to date (2010 last recorded)'.", method=M_TXT)
F("ADM-CL-03#REF", "UNSUPPORTED", "CITATION_ERROR", "P3", finding="No pinpoint.", corr="AA s.22; AR r.13 (with amendment chain).", method=M_AN)

# 18 ADM-CL-07
F("ADM-CL-07#P1", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "MISSING_EXCEPTION", "P3", "AFT", loc("C-PIC-14"), VAFT,
  "AFT s.21 (exhaustion) and s.22 (limitation) apply to 'applications' (s.14 service matters). A s.15 appeal against a court-martial is filed within the time prescribed by rules (s.15(2)); the checklist applies s.21/s.22 indiscriminately.",
  "'For s.14 applications: s.21 exhaustion and s.22 limitation (condonation s.22(2)); for s.15 appeals: time prescribed by the AFT procedure rules.'",
  miss="Page-image reading of the AFT (Procedure) Rules 2008 appeal limitation rule (held file is poor OCR)", method=M_IMG)
F("ADM-CL-07#REF", "UNSUPPORTED", "CITATION_ERROR", "P3", finding="No pinpoint.", corr="AFT Act ss.3(o), 14, 15, 21, 22; AFT (Procedure) Rules 2008.", method=M_AN)

# 19 ADM-SC-02
NA("ADM-SC-02#P1", "Scenario framing.")
NA("ADM-SC-02#P2", "Scenario framing.")
F("ADM-SC-02#P3", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "ARIC", "r.14(2), compilation PDF p.18 (text layer); note 2 p.19", "r.14 1961 substitution; 1993 itemisation lead (PG-04)",
  "Consistent with r.14(2) (satisfaction that court-martial trial is inexpedient or impracticable). The compilation note adds 'for reasons other than probable failure to establish the charge' - commentary, not rule text.", method=M_TXT)
NA("ADM-SC-02#P4", "Fragment; consistent with r.14(5) (Central Government decision). No defect.")
F("ADM-SC-02#P5", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "ARIC", "r.14(1)-(5), compilation (text layer)", "",
  "Consistent: COAS informs officer with adverse reports (withholding allowed on security grounds), written explanation, COAS recommendation (dismiss/remove/compulsorily retire), Central Government decision.", method=M_TXT)
F("ADM-SC-02#REF", "HISTORICAL_VERSION_UNRESOLVED", "HISTORICAL_VERSION", "P3", finding="'AR r14(1)-(5)': sub-rules (4)-(5) were substituted in 1993 per MML 2 p.141 (WS-C PG-04, LEAD); the operative text should be pinned after itemisation.",
  miss="WS-A itemisation of S.R.O. 17(E)/1993 item for r.14", method=M_AN)

# 20 AFT-039
for p in ["P1", "P4", "P5", "P6", "P7", "P8", "P9", "P10", "P11", "P12", "P13", "P14", "P15", "P16"]:
    NA(f"AFT-039#{p}")
NA("AFT-039#P2", "Correct statement of precedent hierarchy (no procedural defect).")
NA("AFT-039#P3", "Correct caution. No defect.")
F("AFT-039#P17", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "PD", "para 32 (text layer)", "Judgment 2023",
  "Consistent: Parashotam Dass para 32 holds Shri Kant Sharma (2015) does not lay down correct law; no per se restriction on Art 226 against AFT orders, subject to self-restraint principles.", unc="Text layer only; holding is a Reviewer B matter.", method=M_TXT)
SNH("AFT-039#REF", "V7-S07/V7-S08/V7-S16 secondary sources")

# 21 CM-007
for p, t in [("P1", "s.119: DCM may try any person other than an officer or a JCO."), ("P2", "s.119: no death, transportation or imprisonment exceeding two years."), ("P3", "s.119 proviso: DCM shall not sentence a warrant officer to imprisonment.")]:
    F(f"CM-007#{p}", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-10"), VAA, "Consistent with " + t, method=M_IMG)
NA("CM-007#P4", "Step; consistent. No defect.")
NA("CM-007#P5", "Step; consistent with s.119 ('any offence made punishable therein'). No defect.")
NA("CM-007#P6", "Step; consistent. No defect.")
F("CM-007#P7", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "OMISSION", "P3", "AA", loc("C-PIC-10"), VAA,
  "Escalation step should also name the convening competence for a DCM (AA s.110, not image-checked) and the r.22-r.24 pre-trial steps (SoE ordinarily required before DCM, compilation note 9 to r.22).",
  "Add convening authority and pre-trial SoE check.", method=M_IMG)
F("CM-007#P8", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-10"), VAA, "Pinpoint correct.", method=M_IMG)
F("CM-007#REF", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-10"), VAA, "Pinpoint correct.", method=M_IMG)

# 22 CM-008
F("CM-008#P1", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-10"), VAA, "Consistent with s.120(3).", method=M_IMG)
F("CM-008#P2", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-10"), VAA, "Consistent with s.120(4)-(5).", method=M_IMG)
NA("CM-008#P3", "Step; consistent with s.120(3). No defect.")
NA("CM-008#P4", "Step; consistent with s.120(3) and r.22(3)(d) ('below the rank of warrant officer'). No defect.")
NA("CM-008#P5", "Step; consistent with s.120(5). No defect.")
F("CM-008#P6", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "OMISSION", "P3", "SRO93", loc("C-PIC-01", "r.22(2) proviso and r.22(3) proviso"), V93,
  "Correct. The record could add that r.22(2) proviso and the r.22(3) proviso mirror s.120(2) (no dismissal of, or SCM order for, a s.120(2) case without reference, save grave reason), and that the AFT reviews an SCM only where punishment is dismissal or imprisonment over three months (AFT s.3(o) exclusion (iv); s.15 interface is reserved to legal advice).",
  "Add r.22(2)/(3) provisos and the AFT s.3(o)(iv) note.", method=M_IMG)
F("CM-008#P7", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-10"), VAA, "Pinpoint correct.", method=M_IMG)
F("CM-008#REF", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-10"), VAA, "Pinpoint correct.", method=M_IMG)

# 23 CM-012
F("CM-012#P1", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-11"), VAA, "Consistent with s.123(1)-(2) and proviso (three years after cessation; exclusions for absconding/injunction; exceptions for desertion, fraudulent enrolment, s.37).", method=M_IMG)
F("CM-012#P2", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-11"), VAA, "Consistent: s.122 and s.123 operate together.", method=M_IMG)
NA("CM-012#P3", "Step; consistent. No defect.")
F("CM-012#P4", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-11"), VAA + "; s.122(1) commencement clauses and s.123(2) substituted by Act 37 of 1992 ss.9-10 - for offences/cessation straddling that Act, version applies by date (legal advice)",
  "Consistent. Temporal note: s.122(1)(a)-(c) and s.123(2) are the 1992 substituted text.", laq="Which version of s.122/s.123 governs where offence or cessation preceded the commencement of Act 37 of 1992?", method=M_IMG)
NA("CM-012#P5", "Step; consistent. No defect.")
NA("CM-012#P6", "Policy escalation step. No defect.")
F("CM-012#P7", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-11"), VAA, "Pinpoint correct.", method=M_IMG)
F("CM-012#REF", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-11"), VAA, "Pinpoint correct.", method=M_IMG)

# 24 CM-028
NA("CM-028#P1", "General caution; sound. No defect.")
F("CM-028#P2", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "WORDING_ERROR", "P3", "AA", loc("C-PIC-10"), VAA,
  "s.117(2) applies only where illness of the judge advocate or accused occurs 'before the finding' and makes continuation impossible; the court-martial 'shall' then be dissolved; s.117(4) allows retrial.",
  "'s.117(2): if illness of the judge advocate or the accused before the finding makes continuation impossible, the court-martial shall be dissolved; the accused may be tried again (s.117(4)).'", method=M_IMG)
NA("CM-028#P3", "Step; sound. No defect.")
NA("CM-028#P4", "Step; sound. No defect.")
F("CM-028#P5", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "OMISSION", "P2", "AA", "AA ss.145-146, compilation PDF pp.39-40 (text layer locator)", VAA + "; AR r.145 substituted 1993 per MML 2 p.210 (WS-C PG-10, LEAD; not itemised)",
  "A note on fitness to stand trial omits the specific statutory route: AA s.145 (court records a finding where the accused is by reason of unsoundness of mind incapable of making his defence; report to confirming officer; possible retrial) and s.146 (subsequent fitness), with AR r.145. Relying only on adjournment/dissolution under s.117 could produce a flawed procedure.",
  "Add: 'Where unsoundness of mind makes the accused incapable of making his defence, apply AA s.145 (finding, report to confirming officer) and s.146, with AR r.145 (version to be itemised); s.117(2) covers illness before finding.'",
  miss="Page image of AA ss.145-146 and current AR r.145", unc="s.145 wording from text layer only.", method=M_TXT)
NA("CM-028#P6", "Step; sound. No defect.")
F("CM-028#P7", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-10"), VAA, "Pinpoint s.117(2) exists.", method=M_IMG)
F("CM-028#P8", "UNSUPPORTED", "CITATION_ERROR", "P3", finding="'AR rr56, adjournment provisions [exact rule verify]' is a placeholder.", corr="Replace with verified rule pinpoints, and add AA ss.145-146 / AR r.145.", method=M_AN)
F("CM-028#REF", "UNSUPPORTED", "CITATION_ERROR", "P3", finding="As P8.", corr="As P8.", method=M_AN)

# 25 COI-018
NA("COI-018#P1", "General statement; sound. No defect.")
F("COI-018#P2", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-12"), VAA, "Consistent: forum choice is under s.125 (formation commander or prescribed officer), subject to s.126; a CoI does not decide it.", method=M_IMG)
NA("COI-018#P3", "Command guidance; sound. No defect.")
NA("COI-018#P4", "Checklist; sound. No defect.")
F("COI-018#REF", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "OMISSION", "P3", "BNSS", "BNSS s.521 (text layer line 10501)", "BNSS in force 1 July 2024 (not re-verified); CrPC s.475 historical",
  "References omit the criminal-procedure side of the interface (CrPC s.475 and the 1978 adjustment-of-jurisdiction rules historically; BNSS s.521 for later matters). [SRC-AO] unresolved.",
  "Add BNSS s.521 / CrPC s.475 (by date) and the applicable rules, subject to verification.", method=M_TXT)

# 26 COI-031
F("COI-031#P1", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "WORDING_ERROR", "P3", "AR54", loc("C-PIC-07", "r.185(1)"), V54 + "; no amendment to r.185 in ARMY-RULES-CHAIN-01 chronology",
  "'Potentially a special-rule inquiry' understates r.185(1): where the weapon or part forms part of unit equipment for which a fine may be imposed under r.186, a CoI 'shall be assembled' under the orders of the formation commander.",
  "'...and, where r.185(1) applies, a mandatory court of inquiry under the orders of the officer commanding the army, army corps, division or independent brigade.'", method=M_IMG)
F("COI-031#P2", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "NONE", "NONE", "AR54", loc("C-PIC-07", "r.185(1)"), V54, "Consistent with r.185(1).", method=M_IMG)
F("COI-031#P3", "HISTORICAL_VERSION_UNRESOLVED", "OMISSION", "P3", "AR54", loc("C-PIC-07", "r.186(1) 1954"), "r.186(1) substituted by S.R.O. 17(E)/1993 per MML 2 p.224 (WS-C PG-11, LEAD; not itemised)",
  "Statutory basis AA s.89 (collective fines) is not cited; r.186(1) was reportedly substituted in 1993 and the operative text is not settled.",
  "Cite AA s.89 and r.186 (version pending itemisation).", miss="Itemisation of S.R.O. 17(E)/1993 for r.186(1)", method=M_IMG)
F("COI-031#P4", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "NONE", "NONE", "AR54", loc("C-PIC-07", "r.186(1) 1954"), V54 + "; 1993 substitution of r.186(1) unresolved (PG-11)",
  "Consistent: on the 1954 text, the power rests with the formation commander, not the CO. Re-check against the 1993 text.", method=M_IMG)
NA("COI-031#P5", "Checklist; sound and consistent with rr.185-186. No defect.")
F("COI-031#REF", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "OMISSION", "P3", "AR54", loc("C-PIC-07"), V54, "Add AA s.89.", "[AA s.89]; [AR r.185]; [AR r.186 (version pending)]", method=M_IMG)

# 27 EV-017
NA("EV-017#P1", "Heading.")
F("EV-017#P2", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "METADATA_OR_TRANSCRIPTION", "P3", "ARIC", "r.23 note 2, compilation PDF p.42 (text layer)", "Compilation note, not rule text",
  "Substance consistent (note 2 to r.23: SoE cannot be taken on oath or affirmation). The held copy is an India Code-hosted compilation with annotated notes; 'MoD-hosted' carrier description is not supported by the held file. The note is commentary, not rule text.",
  "'The annotated notes in the government compilation of the Army Rules (India Code copy held) state...'", method=M_TXT)
F("EV-017#P3", "UNSUPPORTED", "CITATION_ERROR", "P3", finding="'Treatment during trial is regulated' has no pinpoint for the prior-statement/contradiction rule (evidence law via AA s.133: IEA s.145 / BSA equivalent; AR rules on trial evidence).", corr="Add verified pinpoints.", method=M_AN)
NA("EV-017#P4", "Consistent with AA s.131(2) (witnesses sworn at trial; C-PIC-12). No defect.")
NA("EV-017#P5", "Heading.")
NA("EV-017#P6", "Checklist; sound. No defect.")
NA("EV-017#P7", "Records list. No defect.")
NA("EV-017#P8", "Risk labels; consistent. No defect.")
F("EV-017#REF", "HISTORICAL_VERSION_UNRESOLVED", "NONE", "P3", finding="'Army Rule 23' includes r.23(3), reserved CONFLICTING; any quotation of the caution must carry that state.", method=M_AN)

# 28 HCE-016
F("HCE-016#P1", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-08"), VAA, "Consistent with s.79 ('in the manner stated in sections 80, 83, 84 and 85').", method=M_IMG)
F("HCE-016#P2", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "WORDING_ERROR", "P2", "AA", loc("C-PIC-08"), VAA,
  "'Primarily addresses' is wrong: s.80 applies only to a person subject to the Act 'otherwise than as an officer, junior commissioned officer or warrant officer'. Reading 'primarily' as permitting s.80 awards to JCOs or WOs would produce an unlawful award.",
  "'Section 80 applies only to persons other than officers, JCOs and warrant officers.'", method=M_IMG)
F("HCE-016#P3", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "OMISSION", "P2", "AA", loc("C-PIC-09"), VAA + "; s.85 proviso inserted by Act 37 of 1992 s.6",
  "Over-general. s.83 (brigade-level): officers below field rank, JCOs, WOs - reprimand/stoppage; s.84 (area-level or GCM-convening officer): officers below Lt Col, JCOs, WOs - forfeiture of seniority subject to the accused's right to elect trial by court-martial before the award, reprimand, stoppage; s.85 (CO): JCOs only, and no reprimand if the CO is below Colonel. Warrant officers are not within s.85. Omits the s.84(a) election right and the AR r.26 procedure (summary of evidence delivered not less than 24 hours before disposal; hearing of evidence in presence of accused unless written consent; record per Appendix IV).",
  "State the three authorities separately with the s.84(a) election right and the s.85 proviso; add 'Procedure: AR r.26 (SoE and charge delivered >= 24 hours before; evidence heard unless written consent; Appendix IV; s.86 transmission).'", method=M_IMG)
NA("HCE-016#P4", "Step; consistent. No defect.")
NA("HCE-016#P5", "Step; consistent. No defect.")
F("HCE-016#P6", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-09"), VAA, "Consistent; caps in s.80(a)-(h), s.81(2)-(5), s.82.", method=M_IMG)
F("HCE-016#P7", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "NONE", "NONE", "AR54", loc("C-PIC-05", "r.26(3)"), V54 + "; r.26(1) words omitted by S.R.O. 17(E)/1993 item 7 (C-PIC-01)",
  "Consistent: s.86 transmission to superior military authority (s.88); r.26(3) forwarding.", method=M_IMG)
NA("HCE-016#P8", "Risk label; consistent. No defect.")
F("HCE-016#P9", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-08"), VAA, "Consistent: s.80 excludes officers.", method=M_IMG)
F("HCE-016#REF", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "OMISSION", "P3", "AR54", loc("C-PIC-05"), V54, "References omit AR rr.22 and 26 and AA ss.86-88.", "[AA: ss 79-88]; [AR: rr 22 (as substituted 1993), 26 (as amended 1993)]", method=M_IMG)

# 29 HCE-031
for p in ["P1", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10"]:
    NA(f"HCE-031#{p}", "Quality-assurance or record-keeping statement; procedurally sound. No defect.")
F("HCE-031#P2", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "NONE", "NONE", "SRO93", loc("C-PIC-01", "r.22(3)(a) 'Appendix III'"), V93, "Consistent: prescribed forms (Appendix III for s.80 disposal; Appendix IV for r.26) are mandatory references.", method=M_IMG)
F("HCE-031#REF", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "NONE", "NONE", "SRO93", loc("C-PIC-01"), V93, "References usable; [AO] unresolved.", method=M_IMG)

# 30 J-03
F("J-03#P1", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "OMISSION", "P3", "GILL", loc("C-PIC-19", "paras 13-15"), "Judgment 27-11-2019",
  "Consistent, but the route matters: P S Gill held a s.15 appeal 'per se is not maintainable' against a GCM convening order and upheld jurisdiction under s.14 (service matter). The record should name s.14.",
  "'Under AFT s.14 (not s.15), AFT jurisdiction can reach...'", method=M_IMG)
NA("J-03#P2", "Caution; appropriate. No defect.")
F("J-03#REF", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "NONE", "P3", "GILL", loc("C-PIC-19"), "", "Add paras 19-21 (conclusion; text layer).", method=M_IMG)

# 31 KB-004
NA("KB-004#P1", "Question.")
F("KB-004#P2", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-09"), VAA, "Consistent with s.81(2)-(5).", method=M_IMG)
F("KB-004#P3", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-09"), VAA, "Consistent; note s.81(1) omitted by Act 37 of 1992 s.5.", method=M_IMG)
NA("KB-004#P4", "Design rule; consistent. No defect.")
F("KB-004#P5", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-09"), VAA, "Checklist consistent (s.81(4) rank at offence; s.81(3) 42-day aggregate; s.82 additional punishments).", method=M_IMG)
F("KB-004#REF", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-09"), VAA, "Pinpoint correct.", method=M_IMG)

# 32 KB-018
NA("KB-018#P1", "Question.")
NA("KB-018#P2", "Correct general distinction. No defect.")
F("KB-018#P3", "HISTORICAL_VERSION_UNRESOLVED", "NONE", "NONE", finding="Consistent; r.15 is reserved OPEN (authority wording) and r.14(4)-(5) has a 1993 itemisation lead.", method=M_AN)
F("KB-018#P4", "INTERPRETATION_REQUIRES_LEGAL_ADVICE", "NONE", "NONE", "ARIC", "r.14 note 2, compilation (text layer)", "Compilation note",
  "Consistent with the compilation note to r.14 (inexpediency must be for reasons other than probable failure to establish the charge). Note is not rule text.", method=M_TXT)
NA("KB-018#P5", "Reference fragment; appropriate. No defect.")
NA("KB-018#P6", "Checklist; sound. No defect.")
NA("KB-018#REF", "References appropriate; r.15 OPEN.")

# 33 PEN-003
for p in ["P1", "P2", "P3", "P6", "P10"]:
    NA(f"PEN-003#{p}", "Heading/label.")
NA("PEN-003#P4", "Correct general statement. No defect.")
NA("PEN-003#P5", "Correct. No defect.")
F("PEN-003#P7", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AFT", loc("C-PIC-14"), VAFT,
  "Sound. AFT s.21(2)/s.22 make the date of final order on any petition/representation (or six months after filing) the limitation trigger; 'rejection communication, appeal' covers it.", method=M_IMG)
NA("PEN-003#P8", "Step; sound. No defect.")
NA("PEN-003#P9", "Step; sound. No defect.")
for p in ["P11", "P12", "P13", "P14"]:
    NA(f"PEN-003#{p}", "Records/risk list. No procedural defect.")
F("PEN-003#REF", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AFT", loc("C-PIC-14"), VAFT, "V6-S21 ss.21-22 maps to AFT Act ss.21-22 (exist). Other codes not held.", method=M_IMG)

# 34 PEN-024
for p in ["P1", "P2", "P3", "P6", "P11"]:
    NA(f"PEN-024#{p}", "Heading/label.")
for p in ["P4", "P5", "P7", "P8", "P9", "P10", "P12", "P13", "P14", "REF"]:
    SNH(f"PEN-024#{p}", "DESW FAQ and the 16 July 2020 Government letter (V6-S08), Pension Regulations regs 58-61", "No procedural defect identified on the face of the text.")

# 35 PEN-CL-06
F("PEN-CL-06#P1", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AFT", loc("C-PIC-14"), VAFT, "Checklist sound; exhaustion (s.21) and limitation/condonation (s.22(2)) exist as stated.", method=M_IMG)
F("PEN-CL-06#REF", "UNSUPPORTED", "CITATION_ERROR", "P3", finding="No pinpoint.", corr="AFT Act ss.14, 21, 22; relevant ER/GMO edition.", method=M_AN)

# 36 SC13
NA("SC13#P1", "Scenario framing.")
F("SC13#P2", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-11"), VAA, "Consistent with s.123(1)-(2).", method=M_IMG)
NA("SC13#P3", "Step; consistent with s.122. No defect.")
F("SC13#P4", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "OMISSION", "P3", "GILL", loc("C-PIC-19"), "Judgment 27-11-2019",
  "P S Gill records that s.123 was invoked after retirement (para 3, text layer) but decides AFT s.14 jurisdiction and the absence of a prima facie case; it is not authority on s.123 itself.",
  "'Check P S Gill on AFT jurisdiction (s.14) at the pre-trial stage; it does not decide s.123.'", method=M_IMG)
NA("SC13#P5", "Correct caution. No defect.")
F("SC13#REF", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-11"), VAA, "References appropriate.", method=M_IMG)

# 37 V7-JD-05
F("V7-JD-05#P1", "SOURCE_NOT_HELD", "NONE", "NONE", "AFT", loc("C-PIC-13"), VAFT,
  "Santosh Lohar judgment not held. The described interface is procedurally coherent with the texts: s.3(o) exclusion (iv) limits s.14 for SCMs; s.15(1)-(2) is framed for any court-martial. Interpretation reserved.",
  miss="Judgment 2023:PHHC:127834", laq="Does an SCM award excluded from s.3(o) by exclusion (iv) remain appealable under s.15?", method=M_IMG)
NA("V7-JD-05#P2", "Caution; appropriate. No defect.")
SNH("V7-JD-05#REF", "V7-S12 (Santosh Lohar judgment)")

# 38 ADM-014
SNH("ADM-014#P1", "Army CR policy / AO 45/2001")
SNH("ADM-014#P2", "Army CR policy and Pooja Pal (2026)")
SNH("ADM-014#P3", "AO and MS circulars", "Procedure note: redress against CR entries runs through statutory complaint and AFT s.21/s.22; the checklist could record complaint and final-order dates.",
    sev="P3", defect="OMISSION", corr="Add complaint/final-order dates for AFT s.21/s.22.")
SNH("ADM-014#REF", "Army CR policy; Pooja Pal (2026)")

# 39 AFT-001
NA("AFT-001#P1", "Question.")
F("AFT-001#P2", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "GILL", loc("C-PIC-19", "para 15 quoting s.14"), VAFT, "Consistent with s.14(1)-(2).", method=M_IMG)
F("AFT-001#P3", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "NONE", "NONE", "GILL", loc("C-PIC-19", "para 14"), "Judgment 27-11-2019", "Consistent; s.15 appeal lies against an order, decision, finding or sentence of a court-martial (and not a convening order).", method=M_IMG)
F("AFT-001#P4", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "PD", "para 32 (text layer)", "Judgment 2023", "Consistent with Parashotam Dass.", unc="Text layer only.", method=M_TXT)
NA("AFT-001#P5", "Heading.")
NA("AFT-001#P6", "Step; sound. No defect.")
F("AFT-001#P7", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AFT", loc("C-PIC-13"), VAFT, "Consistent: s.3(o) inclusions/exclusions; s.2 applicability incl. retired personnel (s.2(2), text layer).", method=M_IMG)
F("AFT-001#P8", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "OMISSION", "P3", "AFT", "AFT ss.30-31 (text layer)", VAFT,
  "Remedy mapping stops at the AFT. Further remedies: appeal to the Supreme Court under ss.30-31 (with leave), and Art 226 per Parashotam Dass.",
  "Add 'onward remedies: AFT ss.30-31; Art 226 (Parashotam Dass)'.", method=M_TXT)
F("AFT-001#P9", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "MISSING_EXCEPTION", "P3", "AFT", loc("C-PIC-14"), VAFT,
  "s.21/s.22 govern 'applications' (s.14). For a s.15 appeal the time limit is prescribed by rules (s.15(2)); whether s.21-type exhaustion (e.g. an AA s.164 petition) is required before a s.15 appeal is not stated in s.15.",
  "Split: 's.14 application: s.21, s.22; s.15 appeal: rules-prescribed time.'", laq="Is an AA s.164 petition a precondition to an AFT s.15 appeal?", method=M_IMG)
NA("AFT-001#P10", "Policy step. No defect.")
for p in ["P11", "P12", "P13", "P14", "P15", "P16", "P17"]:
    NA(f"AFT-001#{p}", "Documentation/risk label; consistent. No defect.")
F("AFT-001#P18", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "WORDING_ERROR", "P3", "AA", "AA s.164 (compilation PDF pp.43-44, text layer)", VAA,
  "'A petition against a GCM conviction engages s.15' conflates two remedies: AA s.164 'petition' (to confirming authority, then Central Government/COAS/prescribed officer) and AFT s.15 'appeal'.",
  "'...a challenge to a GCM conviction is an appeal under AFT s.15; a petition under AA s.164 is a separate departmental remedy.'", method=M_TXT)
SNH("AFT-001#REF", "V7-S01/V7-S08/V7-S13 secondary sources", "Statutory pinpoints themselves exist in the AFT Act.")

# 40 AFT-003
NA("AFT-003#P1", "Question.")
F("AFT-003#P2", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "OMISSION", "P2", "AFT", loc("C-PIC-13"), VAFT + "; exclusions (ii)-(iv) also quoted in P S Gill para 12 (C-PIC-19)",
  "Imprecise on the two points the question asks about. Exclusion (i) is 'orders issued under section 18 of the Army Act' (not Presidential orders generally). Exclusion (iv) excludes SCMs 'except where the punishment is of dismissal or imprisonment for more than three months'. Inclusion (iii) brings in 'summary disposal and trials where the punishment of dismissal is awarded'; the record omits it, so it does not answer whether a summary punishment reaches the AFT.",
  "'Section 3(o) includes ... (iii) summary disposals and trials where dismissal is awarded; it excludes (i) orders under AA s.18, (ii) transfers and postings, (iii) leave, and (iv) SCMs except where the punishment is dismissal or imprisonment for more than three months.'",
  rat="A commander or practitioner could treat every summary award as within, or outside, AFT jurisdiction.", method=M_IMG)
NA("AFT-003#P3", "Correct caution. No defect.")
NA("AFT-003#P4", "Heading.")
for p in ["P5", "P6", "P7", "P8", "P9"]:
    NA(f"AFT-003#{p}", "Assessment step; sound. No defect.")
for p in ["P10", "P11", "P12", "P13", "P14", "P15"]:
    NA(f"AFT-003#{p}", "Documentation/risk label; consistent. No defect.")
F("AFT-003#P16", "INTERPRETATION_REQUIRES_LEGAL_ADVICE", "NONE", "NONE", "AFT", loc("C-PIC-13"), VAFT, "Interpretive (s.3(o)(iv) vs s.15); appropriately framed as a risk.", laq="As V7-JD-05#P1.", method=M_IMG)
NA("AFT-003#P17", "Example; sound. No defect.")
F("AFT-003#REF", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AFT", loc("C-PIC-13"), VAFT, "Statutory pinpoints exist; V7 codes not held.", method=M_IMG)

# 41 CIV-011
for p in ["P1", "P2", "P7", "P12", "P13", "P14", "P15", "P16"]:
    NA(f"CIV-011#{p}", "Heading/label/records list.")
F("CIV-011#P3", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "HISTORICAL_VERSION", "P3", "BNSS", "BNSS s.521 (text layer line 10501)", "CrPC 1973 s.475 replaced by BNSS 2023 s.521 from 1 July 2024 (date not re-verified); status of 1978 Rules under BNSS savings not determined",
  "The 1978 Rules were made under CrPC s.475; the record should state that the parent provision is now BNSS s.521 and that continuance of the 1978 Rules depends on BNSS savings (legal advice).",
  laq="Do the 1978 adjustment-of-jurisdiction rules continue under BNSS s.531 savings, or have new rules been made under BNSS s.521?", method=M_TXT)
SNH("CIV-011#P4", "the Criminal Courts and Court-Martial (Adjustment of Jurisdiction) Rules 1978")
NA("CIV-011#P5", "Correct caution. No defect.")
NA("CIV-011#P6", "Command guidance; sound. No defect.")
for p in ["P8", "P9", "P10", "P11"]:
    NA(f"CIV-011#{p}", "Assessment step; sound. No defect.")
NA("CIV-011#P17", "Risk label; sound. No defect.")
NA("CIV-011#P18", "Risk label; sound. No defect.")
F("CIV-011#P19", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-12"), VAA, "Consistent: s.125 discretion lies with the officer commanding the army, army corps, division or independent brigade or a prescribed officer, not a unit CO.", method=M_IMG)
F("CIV-011#REF", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-12"), VAA, "s.125 pinpoint exists; V8-S03 not held.", method=M_IMG)

# 42 CIV-039
for p in ["P1", "P2", "P3", "P8", "P9", "P10", "P11", "P12", "P13", "P14", "P15", "P16", "P17", "P18", "P19", "P20"]:
    NA(f"CIV-039#{p}", "Heading, assessment step, records or risk label; procedurally sound. No defect.")
F("CIV-039#P4", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-12"), VAA, "ss.125-126 pinpoints exist.", method=M_IMG)
NA("CIV-039#P5", "Correct general statement. No defect.")
F("CIV-039#P6", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "NONE", "NONE", "AA", loc("C-PIC-12"), VAA, "Consistent with s.125 (forum choice reserved to formation commander/prescribed officer).", method=M_IMG)
NA("CIV-039#P7", "Design rule; sound. No defect.")
SNH("CIV-039#REF", "V8-S03 historic rule 2", "s.125-126 pinpoints exist in the Act.")

# 43 KB-029
NA("KB-029#P1", "Question.")
NA("KB-029#P2", "Correct general statement. No defect.")
F("KB-029#P3", "VERIFIED_AGAINST_HELD_PRIMARY_SOURCE", "NONE", "NONE", "SRO93", loc("C-PIC-02", "item 36 r.182; item 35 r.179(5A)"), V93, "Consistent; CoI material is governed by r.182 (as substituted 1993) and r.184 (substituted 1985, AR-018).", method=M_IMG)
NA("KB-029#P4", "Label.")
F("KB-029#P5", "HISTORICAL_VERSION_UNRESOLVED", "HISTORICAL_VERSION", "P3", "SRO93", loc("C-PIC-02"), V93,
  "Range rr.177-184 spans rules substituted after 1954: r.177 (2003), r.179(5A) inserted and r.182 substituted (1993), r.184 (1985). r.182 wording conflict in the 1993 Gazette print (see COI-003#P6). r.23(3) within rr.22-24 is reserved CONFLICTING.",
  "Pin versions: r.177 (S.R.O. 8(E)/2003), r.182 (S.R.O. 17(E)/1993), r.184 (S.R.O. 44/1985).", method=M_IMG)
F("KB-029#REF", "HISTORICAL_VERSION_UNRESOLVED", "HISTORICAL_VERSION", "P3", "SRO93", loc("C-PIC-02"), V93, "As P5.", "As P5.", method=M_IMG)

# 44 V8-JD-02
F("V8-JD-02#P1", "SOURCE_NOT_HELD", "NONE", "P3", "AA", loc("C-PIC-12"), VAA,
  "Som Datt Datta not held. Procedurally, ss.125-126 as described are consistent with the current text; s.127 (successive trials) has since been omitted by Act 37 of 1992, which affects the older analysis.",
  miss="Judgment AIR 1969 SC 414", method=M_IMG)
NA("V8-JD-02#P2", "Caution; appropriate. No defect.")
SNH("V8-JD-02#REF", "V8-S08 (Som Datt Datta judgment) / V8-S07")

# 45 KB-001
NA("KB-001#P1", "Question.")
NA("KB-001#P2", "Correct. No defect.")
F("KB-001#P3", "SUPPORTED_BY_SECONDARY_SOURCE_ONLY", "OMISSION", "P3", "AA", loc("C-PIC-11"), VAA,
  "Correct caution, but retired personnel can remain liable for offences committed while subject to the Act under s.123 (within three years of cessation, with exceptions), and persons sentenced remain subject under s.123(3)-(4).",
  "Add: 'Retired or discharged persons may still be tried for earlier offences under s.123.'", method=M_IMG)
NA("KB-001#P4", "Step; sound. No defect.")
SNH("KB-001#P5", "the Inter-Services Organisations (Command, Control and Discipline) Act 2023 (SRC-ISO)", "AA s.2 text not image-checked here.")
NA("KB-001#REF", "References appropriate; SRC-ISO not held.")

# 46 KB-002
NA("KB-002#P1", "Question.")
NA("KB-002#P2", "Correct. No defect.")
NA("KB-002#P3", "Correct (rules must trace to AA s.191; administrative instructions cannot override). No procedural defect.")
NA("KB-002#P4", "Correct; consistent with SOURCE_AUTHORITY_POLICY v1. No defect.")
NA("KB-002#P5", "Checklist; sound. No defect.")
NA("KB-002#REF", "References appropriate.")


def main():
    props = list(csv.DictReader(open(C2 / "propositions.csv", newline="", encoding="utf-8")))
    pid2rec = {p["proposition_id"]: p["record_id"] for p in props}
    unknown = sorted(set(rows) - set(pid2rec))
    if unknown:
        raise SystemExit(f"unknown proposition ids: {unknown}")
    out, n = [], 0
    for p in props:
        pid = p["proposition_id"]
        rs = rows.get(pid) or [dict(dimension="PROCEDURE", evidence_state="NOT_YET_REVIEWED", defect_class="NONE", severity="NONE",
                                   source_identity=S["NONE"][0], source_sha256="", locator="", version_or_date_note="",
                                   finding="No specific procedural assessment made.", proposed_correction="", rationale="",
                                   missing_evidence="", legal_advisor_question="", uncertainty="", method=M_NA)]
        for r in rs:
            n += 1
            out.append(dict(finding_id=f"C-{n:04d}", reviewer="C", record_id=pid2rec[pid], proposition_id=pid, **r))
    with open(HERE / "findings.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(out)
    pcols = ["check_id", "document", "document_sha256", "page", "region", "purpose", "render_method", "render_dpi",
             "render_png_sha256", "observed_on_image", "related_proposition_ids"]
    rel = {}
    for r in out:
        for cid in PICD:
            if cid + " " in r["locator"] or r["locator"].endswith(cid):
                rel.setdefault(cid, []).append(r["proposition_id"])
    with open(HERE / "page_image_checks_C.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(pcols)
        for cid, src, page, region, purpose, dpi, png, obs in PIC:
            w.writerow([cid, S[src][0], S[src][1], page, region, purpose, "pymupdf 2.1 get_pixmap", dpi, png, obs,
                        ";".join(sorted(set(rel.get(cid, []))))])
    print(f"rows={len(out)} propositions={len(props)} assessed={len(set(rows))}")


if __name__ == "__main__":
    main()
