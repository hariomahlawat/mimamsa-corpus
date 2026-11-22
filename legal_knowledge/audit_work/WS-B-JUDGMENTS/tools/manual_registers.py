#!/usr/bin/env python3
"""Hand-reviewed WS-B registers (data entered by the WS-B agent after reading the copies named in each row).

Writes: holdings_register.csv, statutes_cited_effective_dates.csv, subsequent_treatment.csv,
        adverse_conflict_queue.csv, pending_source_queue.csv, open_questions.csv
All rows are RESEARCH PROPOSALS. technical review is the highest state an agent can reach; legal-advisor
adjudication and JAG validation are separate states and are NOT_STARTED for every row.
Page numbers are 1-based PDF pages of the copy whose SHA-256 is given. Paragraph numbers are as printed.
"""
import csv, os

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ------------------------------------------------------------------ copies relied on
C = {
 'ISAAC': ('https://api.sci.gov.in/supremecourt/2025/129/129_2025_4_1501_74249_Judgement_15-Sep-2026.pdf', '3f49a31464fec174cdbff5d9e194fa888ca00529b6246eacdc8ac2368eab4653', 'OFFICIAL_COURT_COPY'),
 'NAVJOT': ('https://api.sci.gov.in/jonew/judis/27092.pdf', '3b75354869ffb928f73532f475f5f920e2f2a1f8817163caba2f7fb5e1eb215d', 'OFFICIAL_COURT_COPY'),
 'ANVAR': ('https://api.sci.gov.in/jonew/judis/41931.pdf', '06f77a701073bc32f91ab4a67331cb4747f61214a6f3d2e6408196355dac449b', 'OFFICIAL_COURT_COPY'),
 'ARJUN': ('https://api.sci.gov.in/supremecourt/2017/39058/39058_2017_34_1501_22897_Judgement_14-Jul-2020.pdf', '9c3d7880471fe22f5be2a501bbff40d5b93e32670a37903e04af4dcd92b4aebc', 'OFFICIAL_COURT_COPY'),
 'PARASHOTAM': ('https://api.sci.gov.in/supremecourt/2014/17311/17311_2014_2_1501_42904_Judgement_21-Mar-2023.pdf', 'fe19875b19ed5a4efa257273cd2fb1f1cbb57c4f383117cc40e9a90046568377', 'OFFICIAL_COURT_COPY'),
 'VIRENDRA': ('https://api.sci.gov.in/supremecourt/2018/10621/10621_2018_11_1501_19310_Judgement_07-Jan-2020.pdf', '0ff9d2fc8ef36dfebe862739e517b5ec51f4fff9b4f9b3f7b86beece5d85e819', 'OFFICIAL_COURT_COPY'),
 'PS_GILL': ('https://api.sci.gov.in/supremecourt/2012/26169/26169_2012_11_1501_18538_Judgement_27-Nov-2019.pdf', '7c32b8e87984c9f3dd52218f9030dffad3ea5aedc98d256744fd5e97d044a0ac', 'OFFICIAL_COURT_COPY'),
 'DHARAMVIR': ('https://api.sci.gov.in/jonew/judis/40493.pdf', '3056712cc7614399f72ee19f529f91990e70dba8a317dd3bd07e76e4ac546b75', 'OFFICIAL_COURT_COPY'),
 'RAJBIR': ('https://api.sci.gov.in/jonew/judis/42379.pdf', '970b96807bcbf8a1255fe16c574b575f64fe2edee1cbb271485fa7661a62c666', 'OFFICIAL_COURT_COPY'),
 'NS_YADAV': ('https://api.sci.gov.in/supremecourt/2017/27850/27850_2017_9_1502_17253_Judgement_03-Oct-2019.pdf', '3c50cdb7f30d1a84b488a72052bdf1868cea18ec4e02aee292cf1e97ebf5bbe6', 'OFFICIAL_COURT_COPY'),
 'GIRISH_MAIN': ('https://api.sci.gov.in/supremecourt/2018/21811/21811_2018_6_1501_68439_Judgement_12-Feb-2026.pdf', '4f7ea3a451c6f9a11d7e4dd96822e68cd9cd7a01d8dc74cf46ad34e79029b86c', 'OFFICIAL_COURT_COPY'),
 'MULLIKOTE': ('https://api.sci.gov.in/supremecourt/2023/27246/27246_2023_14_1501_69641_Judgement_24-Mar-2026.pdf', '10e1954f2e39916ea0f0e8e759c3823581becf752dd6ad2e9058569a1fd97444', 'OFFICIAL_COURT_COPY'),
 'JASBIR': ('https://api.sci.gov.in/supremecourt/2020/4409/4409_2020_34_1501_33024_Judgement_01-Feb-2022.pdf', 'c23ce0e334252849ccf1d85949fc482e33071d4a04db5ae3e83c60c16a05faa2', 'OFFICIAL_COURT_COPY'),
 'RANJIT': ('https://api.sci.gov.in/jonew/judis/8566.pdf', 'ed7cf31fd8fbe50822e0a60f80b96ed1187dcd465dc4ae2649424c58001ff399', 'OFFICIAL_COURT_COPY'),
 'PPS_BEDI': ('https://api.sci.gov.in/jonew/judis/9884.pdf', '211dbaf4e20371cc476d09c158e41b976786d57f67336ff6fc802170178b3cca', 'OFFICIAL_COURT_COPY'),
 'SN_MUKHERJEE': ('https://api.sci.gov.in/judgment/judis/7439.pdf', 'eb4420801e978469e9c7407f8c079273f9cd483ad45a4427daa53e3d229969cc', 'OFFICIAL_COURT_COPY'),
 # intern mirror copies (AWS Open Data e-SCR mirror; raw-data ad77758d); not court-hosted bytes
 'MANJEET': ('https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com (intern doc sc-2015-union-of-india-ors-2015insc402)', 'c2f51fac25017d104cf5040bfc4eeac88b9111f5ea1f514eddb11d81465741dc', 'INTERN_MIRROR_SCR'),
 'ANGAD': ('https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com (intern doc sc-2015-union-of-india-ors-2015insc150)', '77919f00c20215f08db90327b55431559a291f171d001dcdfe789d04b150daf1', 'INTERN_MIRROR_SCR'),
 'BALJIT': ('https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com (intern doc sc-1996-union-of-india-and-anr-1996insc1198)', '05e9484593272fe057eef0c133d815b97998c42d12e09c4e012aab1dfbb86646', 'INTERN_MIRROR_SCR'),
 'BALACHANDRAN': ('https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com (intern doc sc-2005-controller-of-defence-accounts-2005insc515)', 'f696a5541cd41d4712aeb94c86d993f364f76e37de7008507cc1c8597548716a', 'INTERN_MIRROR_SCR'),
 'SURINDER_RATHORE': ('https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com (intern doc sc-2008-union-of-india-ors-2008insc357)', 'c295f22913ef898ebc2c8815e2fb1c9c645d462a05619b9701da8a8ca1fd7bdf', 'INTERN_MIRROR_SCR'),
 'KESHAR': ('https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com (intern doc sc-2007-union-of-india-and-ors-2007insc446)', '89eb15de4987dc7b46c2acf1c2c448d38528e066b3d2479146b2154f3df8676a', 'INTERN_MIRROR_SCR'),
 'NAGA': ('https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com (intern doc sc-1997-naga-people-s-movement-of-huma-1997insc763)', '00a6512e374c880e113494dfc51e085bb91d0fc134a0aa2cb09daa739e278531', 'INTERN_MIRROR_SCR'),
 'KULDEEP': ('https://indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com (intern doc sc-2019-union-of-india-ors-2019insc1083)', 'b35f7f9e73f850351ed2779f17c3f0b68044a472f3a0a14fc0e68a865e36422a', 'INTERN_MIRROR_SCR'),
}
CASE = {
 'ISAAC': ('', 'Union of India v Col N.C. Isaac (Retd), 2026 INSC 993', '2026-09-15'),
 'NAVJOT': ('DCLR-SC-2005-L01', 'State (NCT of Delhi) v Navjot Sandhu @ Afsan Guru', '2005-08-04'),
 'ANVAR': ('DCLR-SC-2014-N12', 'Anvar P.V. v P.K. Basheer, CA 4226/2012', '2014-09-18'),
 'ARJUN': ('DCLR-SC-2020-N13', 'Arjun Panditrao Khotkar v Kailash Kushanrao Gorantyal', '2020-07-14'),
 'PARASHOTAM': ('DCLR-SC-2023-009', 'Union of India v Parashotam Dass, CA 447/2023', '2023-03-21'),
 'VIRENDRA': ('DCLR-SC-2020-002', 'Union of India v Ex Sep Virendra Kumar, CA 9267/2019', '2020-01-07'),
 'PS_GILL': ('', 'Union of India v P.S. Gill, Crl.A 404/2013', '2019-11-27'),
 'DHARAMVIR': ('DCLR-SC-2013-N08', 'Dharamvir Singh v Union of India, CA 4949/2013', '2013-07-02'),
 'RAJBIR': ('DCLR-SC-2015-N09', 'Union of India v Rajbir Singh, CA 2904/2011', '2015-02-13'),
 'NS_YADAV': ('', 'Ex Cfn Narsingh Yadav v Union of India, CA 7672/2019', '2019-10-03'),
 'GIRISH_MAIN': ('DCLR-SC-2026-007', 'Union of India v Sgt Girish Kumar, CA 6820-6824/2018, 2026 INSC 149', '2026-02-12'),
 'MULLIKOTE': ('DCLR-SC-2026-N16', 'Union of India v Balakrishnan Mullikote (Ex Hav), 2026 INSC 286', '2026-03-24'),
 'JASBIR': ('DCLR-SC-2022-004', 'State of Sikkim v Jasbir Singh, Crl.A 85/2022', '2022-02-01'),
 'RANJIT': ('DCLR-SC-1987-R01', 'Ranjit Thakur v Union of India, CA 2630/1987', '1987-10-15'),
 'PPS_BEDI': ('DCLR-SC-1982-001', 'Lt Col Prithi Pal Singh Bedi v Union of India', '1982-08-25'),
 'SN_MUKHERJEE': ('DCLR-SC-1990-N02', 'S.N. Mukherjee v Union of India (Constitution Bench)', '1990-08-28'),
 'MANJEET': ('DCLR-SC-2015-L02', 'Union of India v Manjeet Singh, CA 4357-4358/2015', '2015-05-12'),
 'ANGAD': ('DCLR-SC-2015-L03', 'Union of India v Angad Singh Titaria, CA 11208/2011', '2015-02-24'),
 'BALJIT': ('DCLR-SC-1996-L07', 'Union of India v Baljit (printed "Baltit") Singh', '1996-10-11'),
 'BALACHANDRAN': ('DCLR-SC-2005-L08', 'CDA (Pension) v S. Balachandran Nair', '2005-10-21'),
 'SURINDER_RATHORE': ('DCLR-SC-2008-L09', 'Union of India v Surinder Singh Rathore, CA 1960/2008', '2008-03-13'),
 'KESHAR': ('DCLR-SC-2007-L10', 'Union of India v Keshar Singh', '2007-04-20'),
 'KULDEEP': ('DCLR-SC-2019-003', 'Union of India v Lt Col Kuldeep Yadav, CA 7603/2019', '2019-09-25'),
 'NAGA': ('DCLR-SC-1997-L11', "Naga People's Movement of Human Rights v Union of India (Constitution Bench)", '1997-11-27'),
}
REND = {  # page renders viewed by WS-B (110 dpi PNG of the official PDF page; render SHA-256)
 ('ISAAC', '93'): '40b08feb27d3b552f2311ac26279c074ab0a5529c3c02cbe4e615aa1550f0191',
 ('ISAAC', '91'): 'e7f23a58e72f0d5385b19ced695113ae8220652ca5f7908a4cde4191df5553ad',
 ('ANVAR', '18'): 'a5d0bd53bb3d416b7d3006f568e2fb2bb003c62bde6e4cb66761d1f557a4663f',
 ('ARJUN', '81'): 'bf48b8d895540cf34e7540101a8fdfc3d2cf8c6db472cc3a8234ec865a06be47',
 ('PARASHOTAM', '22'): '0973bb4d84292cbcedee80e8b7cf29224947b25cf8e9c96ca69a17848bc24700',
 ('VIRENDRA', '21'): 'aa92d37a77b21f1b645b8c5fb569ab22d67dd362441133a139b1f2c8bedb5694',
}

# (spec, pdf_page, para, passage_type, ws_b_paraphrase, anchor_quote(<=30 words, verbatim from copy), curated_comparison, kb_ids, uncertainty)
H = [
 ('ISAAC','93','39(i), 40','OPERATIVE_DISPOSITION','The batch of Union appeals/SLPs was dismissed on delay and on merits, with the clarifications in 39(ii)-(iii).','They are accordingly dismissed on the grounds of delay as well as on merits.','NOT_IN_CASES53','PEN-043;PEN-017;PEN-044;PEN-045;PEN-J-01;PEN-J-02','Dismissal of a batch; the binding reach of the clarifications vs the disposition needs legal review.'),
 ('ISAAC','93','39(ii)','OPERATIVE_DIRECTION_ADOPTING_PARTY_SUBMISSION','Court accepted the AG submission that the Medical Board opinion deserves due weight and should not be substituted merely because another view is possible; in pending matters the Tribunal must scrutinise the Board\'s opinion and reasons in detail.','the opinion of the Medical Board deserves to be given due weight and ought not to be substituted by a Court merely because another view is possible','NOT_IN_CASES53','PEN-043;PEN-017;PEN-044;PEN-045;CIV-019;CIV-036;CIV-037','HIGH RISK: does not say Medical Board opinion is conclusive; read with Dharamvir/Rajbir line (reasons requirement). Proposal only.'),
 ('ISAAC','93','39(iii)','OPERATIVE_DIRECTION','Where a claimant approaches the forum more than fifteen years later, the principle in Rule 7 of the Entitlement Rules 2008 applies and the onus shifts to the applicant.','If a claimant approaches the relevant forum after a period of fifteen years, the principle in Rule 7 of the Entitlement Rules 2008 applies and the burden shifts.','NOT_IN_CASES53','PEN-043;PEN-017;PEN-044;PEN-045','HIGH RISK: legal effect of ER 2008 itself expressly left open (para 34); start point of the 15 years (discharge vs claim) should be read with paras 30.4, 33-35.'),
 ('ISAAC','91','34','RATIO_EXPRESSLY_QUALIFIED','ER 2008, assuming they have legal effect, substantially reproduce the 1982 scheme (causal connection, onus, attributability/aggravation) subject only to the Rule 7 proviso. The Court did not decide that ER 2008 have legal force.','In our view the Entitlement Rules 2008, assuming they otherwise have legal effect, substantially reproduce the 1982 scheme','NOT_IN_CASES53','PEN-043;PEN-017;PEN-044;PEN-045','Any KB text stating ER 2008 are in force, or that ER 1982 are repealed, is not supported by this paragraph.'),
 ('ISAAC','73-74','22','COURT_OBSERVATION_ON_RECORD','The Union could not fully demonstrate the source, time and method by which ER 2008 were brought into force by repealing or superseding ER 1982; AG said they were issued by letter dated 18.01.2010 as a compilation of policy.','the Union was unable to demonstrate fully the source, the time and the method by which the said Entitlement Rules 2008 were brought into force','NOT_IN_CASES53','PEN-043;PEN-017','Observation, not a declaration of invalidity. Text layer only (no page render).'),
 ('ISAAC','81','28','OBITER_EXHORTATION','ER 2008 appear to be a collation of modified executive instructions; the Court urged authoritative formulation and notification by the competent authority.','It appears that the Entitlement Rules 2008 is a collation of the modified executive instructions','NOT_IN_CASES53','PEN-043','Not a holding. Text layer only.'),
 ('ISAAC','69','19.4','PARTY_ARGUMENT_SUMMARISED_BY_COURT','Respondents (ex-servicemen) submitted that since the 1982 and 2008 rules are substantially similar, Dharamvir, Rajbir and Angad continue to hold the field.','Since, the Entitlement Rules are substantially similar, Dharamvir Singh, Rajbir, Angad Singh Titaria continue to hold the field.','NOT_IN_CASES53','PEN-J-01;PEN-J-02;PEN-043','Must never be cited as the Court\'s holding (agrees with v3.5 gate file 06). Text layer only.'),
 ('ISAAC','91','35','COURT_OBSERVATION','Where AFT/HC routinely allowed claims by applying the presumption or Dharamvir without detailed examination of evidence, there is a case for revisiting; it is for the Union to identify such cases.','there is certainly a case for revisiting those decisions. It is for the Union to identify such cases','NOT_IN_CASES53','PEN-J-01;PEN-J-02;PEN-043','Observation; no direction reopening concluded cases. Proposal for legal review.'),
 ('NAVJOT','49','Part 15 (Call records); reporter para 150 per Anvar p16','COURT_HOLDING_LATER_OVERRULED_IN_PART','Printouts of call records could be proved as secondary evidence under ss.63/65 Evidence Act irrespective of compliance with s.65B.','Irrespective of the compliance of the requirements of Section 65B ... there is no bar to adducing secondary evidence under the other provisions','CURATED_HOLDING_EMPTY','EV-*;V9-JD-01;V9-JD-02 (lexical; see crosswalk)','Overruled to that extent by Anvar (para 22). JUDIS copy has no numbered paras; para 150 is the SCC numbering quoted in Anvar. Evidence Act 1872 superseded by BSA 2023 from 1 Jul 2024.'),
 ('ANVAR','18','22','HOLDING_OVERRULING','Sections 63/65 do not apply to secondary evidence by electronic record, which is governed wholly by ss.65A/65B; Navjot Sandhu overruled to that extent; secondary electronic evidence inadmissible without a s.65B certificate.','does not lay down the correct legal position. It requires to be overruled and we do so.','CONSISTENT_WITH_CURATED (curated: s.65B special route, later clarified by Arjun)','V9-JD-02;V9-S05 users','Historical Evidence Act provision; for proceedings after 1 Jul 2024 BSA 2023 s.63 governs (statutes register).'),
 ('ARJUN','80-81','72(a)','HOLDING','Anvar as clarified is the law on s.65B; Tomaso Bruno per incuriam; Shafhi Mohammad (SLP(Crl) 9431/2011 and order reported (2018) 5 SCC 311) overruled.','do not lay down the law correctly and are therefore overruled.','CONSISTENT_WITH_CURATED (A10 marked overruled)','V9-JD-01;V9-S04 users','Three-judge bench reference answer.'),
 ('ARJUN','81','72(b)','HOLDING_CLARIFICATION','s.65B(4) certificate unnecessary if the original document itself is produced (owner proves the device); where a system/network cannot be brought to court, s.65B(1) with certificate is the only route.','the required certificate under Section 65B(4) is unnecessary if the original document itself is produced','CONSISTENT_WITH_CURATED','V9-JD-01','Historical Evidence Act; BSA 2023 s.63 carries a different certificate scheme (Schedule) - statutes register.'),
 ('PARASHOTAM','22','32','HOLDING','Shri Kant Sharma does not lay down the correct law; there is no per se restriction on High Court power under Art.226 against AFT orders; in self-discipline matters the principles already stand enunciated.','does not lay down the correct law and is in conflict with judgments of the Constitution Benches','CURATED_NARROWER (curated describes Art.226/227 distinction; omits that Shri Kant Sharma was held not to lay down correct law)','V7-JD-02;V7-JD-03;V7-S08 users;V7-S09 users;V7-WF-08','Bench of three judges; KB records citing Shri Kant Sharma as current law need treatment flag.'),
 ('PARASHOTAM','20-21','29-30','RATIO','HC can exercise Art.226 jurisdiction where there is denial of a fundamental right, jurisdictional error or error apparent; Court declined to carve out exceptions; HC is not to re-appreciate evidence as a second appeal.','if there is a denial of a fundamental right under Part III of the Constitution or there is a jurisdictional error or error apparent on the face of the record','CURATED_PINPOINT_DIFFERS (curated 11-16; reasoning at 24-32)','V7-JD-03;V7-WF-08','Text layer for pp.20-21.'),
 ('VIRENDRA','16-17','12(a)-(d)','RATIO_SYNTHESIS_OF_PRECEDENT','CoI is a fact-finding pre-investigation stage; accused entitled to full Rule 180 opportunity; irregularities at earlier stages cannot be a basis to set aside a court-martial order after trial; if raised at charge/SoE stage the authorities must rectify, Rule 180 compliance being obligatory.','compliance of the procedure prescribed in Rule 180 is obligatory','CONSISTENT_WITH_CURATED','J-02;CM-JD-04;SC02;V9-JD-04;HCE-032','Official PDF holds two versions: pp.1-21 marked CORRECTED and pp.22-42 uncorrected; same para 12 text in both (second at pp.37-38).'),
 ('VIRENDRA','20','15','HOLDING','AFT may direct retrial only on the grounds in s.16(2) AFT Act and only by court martial; no power to remand to a stage before the court martial; non-compliance with Rule 180 is not a ground for retrial.','Non-compliance of Rule 180 cannot be a ground for ordering a re-trial.','CONSISTENT_WITH_CURATED','J-02;CM-JD-04;V7-S01 users','Heading in the copy reads "Section 16 of the Army Act, 1950" but the section quoted is s.16 AFT Act 2007 - copy-internal labelling error noted, not corrected.'),
 ('VIRENDRA','21','16-17 (CORRECTED version)','OPERATIVE_DISPOSITION','Appeal allowed; corrected version adds that the respondent shall not be sentenced to imprisonment, having undergone more than 10 years.','the Respondent shall not be sentenced to any imprisonment in view of his having already undergone the sentence of more than 10 years.','CURATED_SILENT_ON_CORRECTION','J-02;CM-JD-04','Uncorrected version (pp.22-42) ends at para 16 "The Appeal is accordingly allowed". Cite the corrected version.'),
 ('PS_GILL','17','14','HOLDING','Appeal under s.15 AFT Act lies only against an order, decision, finding or sentence of a court martial; an order convening a GCM is not such, so s.15 appeal is not maintainable.','an appeal under Section 15 per se is not maintainable.','NOT_IN_CASES53','J-03;HCE-032;SC13','Text layer only.'),
 ('PS_GILL','17-19','15-19','HOLDING','s.14 AFT Act "service matters" (s.3(o)) to be given wide construction; proceedings that may lead to termination relate to conditions of service; challenge to GCM convening entertainable under s.14.','Section 14 of the Act which confers jurisdiction over service matters of the Army personnel should receive wide construction.','NOT_IN_CASES53','J-03;HCE-032;SC13','Facts record s.123 Army Act invoked after retirement (p.3) but s.123 was not decided; SC13 should not cite P S Gill for a s.123 proposition.'),
 ('PS_GILL','20','21-22','OPERATIVE_DISPOSITION','Tribunal\'s finding of no prima facie case not interfered with; Union appeal dismissed.','Accordingly, the Appeal is dismissed.','NOT_IN_CASES53','J-03','Fact-specific.'),
 ('DHARAMVIR','30-31','28(i)-(vii), 29','RATIO','Under Pension Regulations Reg 173 and Entitlement Rules 1982 (with GMO 2002): presumption of sound health at entry absent a note; onus on employer; Medical Board must state reasons if it says the disease could not be detected at entry; Court answered both referred questions for the appellant.','We, accordingly, answer both the questions in affirmative in favour of the appellant','CURATED_VAGUER (curated: "examined the entry-health presumption")','PEN-J-01;V6-S14 users','1982 rules framework; see Isaac 2026 paras 30-35 and 39 for later qualification. Para numbering in JUDIS copy matches SCC 28/29 as quoted in Rajbir/NS Yadav.'),
 ('DHARAMVIR','32-36','30-34','APPLICATION_AND_DISPOSITION','No note at entry; Board gave no reasons; presumption of service connection not rebutted; Division Bench order set aside, Single Judge order restored, appeal allowed.','accordingly the appeal is allowed','CONSISTENT','PEN-J-01','Fact-specific.'),
 ('RAJBIR','18-19','15','RATIO','Burden lies heavily on employer to show disease neither attributable to nor aggravated by service; a soldier cannot be asked to prove it; the least required is a statement of reasons by the Board.','For the employer to say so, the least that is required is a statement of reasons supporting that view.','CURATED_VAGUER','PEN-J-02;V6-S15 users','1982 rules framework; Isaac 2026 39(ii)-(iii).'),
 ('RAJBIR','19-20','16-17','APPLICATION_AND_DISPOSITION','Presumption unrebutted, disability over 20%; Union appeals fail.','In the result these appeals fail','CONSISTENT','PEN-J-02','A second Rajbir copy (bosir order 2213461, sha 6b495f14...) exists in the scratchpad; not used here.'),
 ('NS_YADAV','12-15','15-21','RATIO_DISTINGUISHING','The presumption is not applied mechanically; mental disorders such as schizophrenia may escape detection at enrolment; posting at a peace station; courts not to dispute Medical Board opinion absent strong medical evidence.','it is not mechanical application of the principle that any disorder not mentioned at the time of enrolment is presumed','NOT_IN_CASES53','PEN-J-03;PEN-CS-07;V6-S16 users','Adverse to broad readings of Dharamvir; ER 1982 cl.14(d) as amended 1996 applied (para 20).'),
 ('NS_YADAV','15','22','OPERATIVE_DISPOSITION','Claimant\'s appeal dismissed.','we do not find any merit in the present appeal, accordingly, the same is dismissed.','NOT_IN_CASES53','PEN-J-03','Fact-specific.'),
 ('GIRISH_MAIN','15-16','22','RATIO','Tarsem Singh of no assistance: Ram Avtar (three judges, 10.12.2014) decided the broad-banding issue in rem; right to approach the Tribunal accrued on 10.12.2014; s.22(1)(c) AFT Act bar not applicable to re-computation claims.','the decision in Tarsem Singh (supra) has no application to the case in hand','CONSISTENT','PEN-J-05;PEN-CS-09;V6-S18 users;V7-JD-04','Treatment of Tarsem Singh = distinguished (subsequent_treatment). Text layer only.'),
 ('GIRISH_MAIN','16-17','23','OPERATIVE_DISPOSITION','Union appeals dismissed; ex-servicemen\'s appeals allowed: arrears with broad-banding from 01.01.1996 or 01.01.2006 as the case may be, interest 6%.','held entitled to disability pension including the benefit of broad banding, due to them, with effect from 01.01.1996 or 01.01.2006','CONSISTENT','PEN-J-05;PEN-CS-09','Clarification order 12.10.2026 (2026 INSC 1113) NOT held - pending queue.'),
 ('MULLIKOTE','61-62','97-99','RATIO_AND_DISPOSITION','Ex Sep Chattar Pal distinguished (DSC personnel not on voluntary discharge; condonation discretionary under paras 125/44 of Pension Regulations 1961/2008); issue settled by repeated pronouncements; Union appeals dismissed.','The Appeals are accordingly dismissed, with no order as to costs.','CURATED_NOT_CHECKED (curated paras 33-44 and 51 not read in this pass)','PEN-J-07;V6-S20 users','Official PDF contains two versions (CORRECTED first copy pp.1-31 and a second copy pp.32-62); the paras cited here are at pp.61-62; first-copy position not mapped.'),
 ('JASBIR','42','51-52','HOLDING_AND_DISPOSITION','Sessions Judge was competent; HC erred in holding court martial alone had jurisdiction; appeal allowed; accused to be transferred from military to civil custody; trial to proceed from the stage reached.','The respondent-accused shall be transferred from military custody to civil custody to face trial.','CONSISTENT','V8-JD-01;V8-S07 users','Concurrent jurisdiction ss.125-126 Army Act; Criminal Courts and Court-Martial (Adjustment of Jurisdiction) Rules not held. Text layer only.'),
 ('RANJIT','8-9','9-10 (SCR pp.523-524)','RATIO_AND_DISPOSITION','Doctrine of proportionality forms part of judicial review; a court-martial sentence so disproportionate as to shock the conscience is not immune; SCM proceedings and sentence quashed, reinstatement with benefits.','The doctrine of proportionality, as part of the concept of judicial review','CONSISTENT','KB-016;KB-027;SRC-RANJIT users','Bias / s.130 reasoning (pp.5-7) not re-read in this pass. JUDIS copy partially numbered.'),
 ('PPS_BEDI','34-35','unnumbered (SCR pp.438-439)','RATIO','No provision requires a CoI before a GCM trial; Rule 180 does not make a CoI a sine qua non; it obliges full participation when a CoI is held and character/military reputation is likely to be affected.','Rule 180 merely makes it obligatory that whenever a court of inquiry is set up','CONSISTENT (curated pinpoint "40","14" cannot be mapped to the unnumbered JUDIS copy)','J-01;CM-JD-01;SC_PPS users','Pre-1993 Army Rules (r.22 substituted 1993; r.25 omitted 1993 per ARMY-RULES-CHAIN seed).'),
 ('SN_MUKHERJEE','20','unnumbered conclusion','HOLDING_TEMPORAL','Under the Act and Rules as they then stood, reasons were not required for confirmation of court-martial findings/sentence or for rejection of a post-confirmation petition under s.164(2).','reasons are not required to be recorded for an order passed by the confirming authority','CONSISTENT (curated already notes later r.62(1))','V7-JD-07;V7-S10 users','Temporal: later amendment of Army Rules r.62 not verified by WS-B (WS-A scope).'),
 ('MANJEET','27','25-26','DISPOSITION_ON_MIRROR','Court endorsed Dharamvir/Rajbir and sustained the Tribunal; Union appeals dismissed.','we hereby sustain the impugned judgment and order. The appeals are dismissed.','CURATED_HOLDING_EMPTY','PEN-* (v3.4 impact queue)','MIRROR copy only (SCR via AWS); official copy pending. Pinpoint provisional.'),
 ('ANGAD','16','17-18','DISPOSITION_ON_MIRROR','Tribunal award of disability pension (60% from discharge, 10% interest) sustained; Union appeal dismissed; IAF Pension Regulations 1961 Reg 153.','the Tribunal had not committed any error in awarding disability pension to the respondent for 60% disability','CURATED_HOLDING_EMPTY','PEN-* (v3.4 impact queue)','MIRROR only. IAF regulation; Isaac 2026 p.61 describes the regulation as Army (v3.5 file 05 conflict).'),
 ('BALJIT','3','unnumbered final para','DISPOSITION_ON_MIRROR','Claim must be affirmatively established as due to/aggravated by service; HC "not totally correct", but appeal dismissed on facts.','The appeal is accordingly dismissed with the above findings.','CURATED_HOLDING_EMPTY','PEN-*','MIRROR only; printed name "Baltit".'),
 ('BALACHANDRAN','8','unnumbered final para','DISPOSITION_ON_MIRROR','Board opinion that illness not attributable to service accepted; respondent not entitled; no recovery of amounts paid; Union appeal allowed.','The respondent is not entitled to disability pension.','CURATED_HOLDING_EMPTY','PEN-*','MIRROR only.'),
 ('SURINDER_RATHORE','10','8-10','DISPOSITION_ON_MIRROR','Board opinion accepted; not entitled; no recovery; Union appeal allowed; relies on Keshar Singh.','The respondent is not entitled to disability pension.','CURATED_HOLDING_EMPTY','PEN-*','MIRROR only.'),
 ('KESHAR','8','10-11','DISPOSITION_ON_MIRROR','Board opinion (schizophrenia not attributable) accepted; not entitled; no recovery; Union appeal allowed; relies on Balachandran Nair.','The respondent is not entitled to disability pension.','CURATED_HOLDING_EMPTY','PEN-*','MIRROR only.'),
 ('KULDEEP','18-19','22-23','RATIO_ON_MIRROR','Tribunal may interfere with punishment in departmental action only in exceptional and rare cases (shocks the conscience / no reasonable person); not as a court of appeal; may direct reconsideration or, rarely, impose punishment with cogent reasons.','It can be invoked only in exceptional and rare cases, when the punishment awarded by the disciplinary authority shocks the conscience','CONSISTENT (curated pinpoint 22-26, 34; KB ADM-JD-01 refs "paras 22-26, 34" resolve to this judgment - OQ-D-004)','ADM-JD-01;ADM-013;ADM-026;ADM-031;ADM-SC-14','MIRROR (SCR) only; SCR para numbers; official copy pending.'),
 ('KULDEEP','19-20','24-26','APPLICATION_ON_MIRROR','Past record had been considered by the authorities; Tribunal misdirected itself on the 23 Apr 2007 censure policy.','The Tribunal also erroneously assumed that the competent authority opted to resort to administrative action','CONSISTENT','ADM-JD-01;ADM-026','MIRROR only.'),
 ('KULDEEP','23','34-35','DISPOSITION_ON_MIRROR','AFT order quashed; Government decision of 30 Apr 2014 and GOC-in-C order of 10 May 2013 restored; Union appeal allowed.','this appeal must succeed. The impugned judgment and order of the Armed Forces Tribunal is quashed and set aside.','CONSISTENT','ADM-JD-01','MIRROR only.'),
 ('NAGA','','','NOT_REVIEWED_THIS_PASS','Constitution Bench AFSPA judgment; operative directions not re-read by WS-B in this pass.','','CURATED_PRESENT','V8-S15 users','Pending: official copy and full reading of conclusions.'),
]

def holdings():
    hdr = ['row_id','spec_key','case53_id','judgment','decision_date','copy_url','copy_sha256','copy_role','carrier_provenance',
           'wording_read_from','page_render_sha256','pdf_page','para_pinpoint','passage_type','ws_b_paraphrase','anchor_quote_verbatim',
           'comparison_with_curated','affected_kb_ids','uncertainty','technical_review_state','legal_advisor_state','jag_validation_state']
    rows = []
    for i, (k, pg, para, typ, para_, q, cmp_, kb, unc) in enumerate(H, 1):
        url, sha, role = C[k]; cid, name, d = CASE[k]
        rsha = REND.get((k, pg.split('-')[-1] if pg else ''), '') or REND.get((k, pg), '')
        prov = 'ISSUING_AUTHORITY' if role == 'OFFICIAL_COURT_COPY' else 'THIRD_PARTY_ARCHIVAL_FACSIMILE'
        read = 'PAGE_IMAGE' if rsha else ('PDF_TEXT_LAYER' if pg else 'NOT_READ')
        if role == 'OFFICIAL_COURT_COPY':
            tstate = 'PASSAGE_LOCATED_OFFICIAL_COPY' + ('_PAGE_IMAGE_CHECKED' if rsha else '_TEXT_LAYER')
        elif pg:
            tstate = 'PASSAGE_LOCATED_MIRROR_COPY_ONLY_NOT_OFFICIAL'
        else:
            tstate = 'NOT_REVIEWED'
        rows.append([f'WSB-H-{i:03d}', k, cid, name, d, url, sha, role, prov, read, rsha, pg, para, typ, para_, q, cmp_, kb, unc,
                     tstate, 'NOT_STARTED', 'NOT_STARTED'])
    return hdr, rows

# ------------------------------------------------------------------ statutes cited + effective dates
# Owner rule (22 Nov 2026): publication, commencement and effective dates are distinct; never infer an effective
# date from a Gazette publication date; unresolved effective dates stay empty with an explicit status.
S = [
 # spec, provision, version applied by the court / instrument, publication_date, commencement_date, effective_date, effective_status, applied_at_judgment_date, later_change, flag, source_of_dates
 ('ISAAC','Entitlement Rules for Casualty Pensionary Awards 1982 (Appendix II, Pension Regulations Army 1961)','1982 rules as discussed paras 21, 30','','','','NOT_DETERMINED','DISCUSSED_AS_ESTABLISHED_REGIME (para 21)','ER 2008; ER 2023 (MoD letter 21 Sep 2023 per KB V6-S04; not held)','TEMPORAL_SCHEME_SELECTION_REQUIRED','Isaac paras 21-22; no Gazette/letter held by WS-B'),
 ('ISAAC','Entitlement Rules for Casualty Pensionary Awards to the Armed Forces Personnel 2008','issued by letter dated 18.01.2010 per AG submission (para 22)','','','','NOT_DETERMINED (Court: Union could not fully demonstrate source/time/method; legal effect assumed, not decided, para 34)','APPLIED_HYPOTHETICALLY (para 34) and Rule 7 proviso applied (para 39(iii))','ER 2023','HIGH_RISK_LEGAL_EFFECT_UNRESOLVED','Isaac paras 22, 34, 39(iii)'),
 ('ISAAC','Entitlement Rules 2008 Rule 7 proviso (claims after 15 years)','as in ER 2008','','','','NOT_DETERMINED','APPLIED (para 39(iii))','ER 2023 equivalent not checked','START_POINT_OF_15_YEARS_TO_CONFIRM','Isaac paras 30.4, 33, 35, 39(iii)'),
 ('DHARAMVIR','Pension Regulations for the Army 1961 Reg 173; Entitlement Rules 1982 rr.5, 9, 14; GMO (Military Pensions) 2002','1961 Regs / 1982 Rules / GMO 2002','','','','NOT_DETERMINED','APPLIED','Pension Regulations for the Army 2008 (KB V6-S01; not held); ER 2008; ER 2023; Isaac 2026','TEMPORAL_SCHEME_SELECTION_REQUIRED','Dharamvir paras 28-29'),
 ('RAJBIR','Pension Regulations 1961 Reg 173; Entitlement Rules 1982','as Dharamvir','','','','NOT_DETERMINED','APPLIED','as Dharamvir','TEMPORAL_SCHEME_SELECTION_REQUIRED','Rajbir paras 13-16'),
 ('NS_YADAV','Entitlement Rules 1982 cl.14(d) as amended 1996','1982 rules with 1996 amendment','','','','NOT_DETERMINED (1996 amendment instrument not held)','APPLIED (para 20)','ER 2008/2023','AMENDMENT_INSTRUMENT_NOT_HELD','NS Yadav para 20'),
 ('ANGAD','Pension Regulations for the Indian Air Force 1961 Reg 153','IAF 1961 Regs','','','','NOT_DETERMINED','APPLIED (mirror copy cover)','Isaac 2026 p.61 labels it Army Reg 153','CROSS_SERVICE_LABEL_CONFLICT','Angad mirror p.1; v3.5 file 05'),
 ('MANJEET','Pension Regulations for the Army 1961 Reg 173; Army Rules 1954 rr.5, 9, 14 (as printed in SCR headnote)','1961 Regs','','','','NOT_DETERMINED','APPLIED (mirror)','Isaac 2026','HEADNOTE_LABEL_NOT_EVIDENCE','Manjeet mirror p.1 headnote (editorial) - not evidence of what was applied'),
 ('KESHAR','Pension Regulations 1961 Reg 423, App II para 7(b),(c)','1961 Regs','','','','NOT_DETERMINED','APPLIED (mirror headnote)','Isaac 2026 (no express citation)','HEADNOTE_LABEL_NOT_EVIDENCE','Keshar mirror p.1'),
 ('NAVJOT','Indian Evidence Act 1872 ss.63, 65, 65B','1872 Act (s.65B inserted by IT Act 2000)','','','','NOT_DETERMINED','APPLIED','Repealed and replaced by Bharatiya Sakshya Adhiniyam 2023 (47 of 2023); BSA electronic-record certificate in s.63','IEA_TO_BSA_TRANSITION (commencement of BSA 1 Jul 2024 per programme brief; commencement notification not held by WS-B: KB code V8-S11 GAP)','Navjot p.49'),
 ('ANVAR','Indian Evidence Act 1872 ss.59, 63, 65, 65A, 65B','1872 Act','','','','NOT_DETERMINED','APPLIED','BSA 2023 s.63 (not compared by WS-B)','IEA_TO_BSA_TRANSITION','Anvar p.18'),
 ('ARJUN','Indian Evidence Act 1872 s.65B(4)','1872 Act','','','','NOT_DETERMINED','APPLIED','BSA 2023 s.63 and Schedule certificate (not compared)','IEA_TO_BSA_TRANSITION','Arjun pp.80-81'),
 ('JASBIR','Army Act 1950 ss.69, 70, 71, 125, 126; Indian Penal Code 1860 offence(s)','Army Act as on 2022; IPC 1860','','','','NOT_DETERMINED','APPLIED','IPC replaced by Bharatiya Nyaya Sanhita 2023; CrPC by BNSS 2023 (commencement 1 Jul 2024 per brief; notification not held)','IPC_TO_BNS_TRANSITION; ss.69/125 Army Act refer to "civil offence" - BNS mapping needed','Jasbir pp.41-42'),
 ('PARASHOTAM','Armed Forces Tribunal Act 2007 ss.30, 31; Constitution Arts.226, 227(4)','AFT Act 2007 (India Code compilation e.g. sha 665863d1abb8... via PILOT-01)','','','','NOT_DETERMINED','APPLIED','Tribunals Reforms Act 2021 amendments to AFT Act not checked by WS-B','AMENDMENT_CHAIN_NOT_CHECKED','Parashotam paras 18-32'),
 ('PS_GILL','AFT Act 2007 ss.3(o), 14, 15; Army Rules 1954 rr.22, 23, 180; Army Act s.123','AFT Act 2007; Army Rules as amended (r.22 substituted by S.R.O. 17(E)/1993 per chain seed)','1993-12-06 (S.R.O. 17(E)/1993, r.22)','','','NOT_DETERMINED (chain seed: r.22 v1993 effective date NOT_DETERMINED)','APPLIED','possible S.R.O. 258/2002 for r.22 (chain seed GAP)','ARMY_RULES_CHAIN_OPEN','PS Gill pp.2-3, 17-19; ARMY-RULES-CHAIN-01 seed @11ce905e'),
 ('VIRENDRA','Army Rules 1954 r.180; AFT Act 2007 s.16','Army Rules as amended; AFT Act 2007','','','','NOT_DETERMINED','APPLIED','r.177 substituted by S.R.O. 8(E)/2003 per chain seed (C-03 PROPOSAL); r.180 version not in seed','ARMY_RULES_CHAIN_OPEN','Virendra paras 12-15'),
 ('PPS_BEDI','Army Rules 1954 rr.22-25, 37, 40, 44, 180; Army Act ss.21, 130; Constitution Arts.21, 33','pre-1993 Army Rules (1954 text as amended to 1982)','1954-11-27 (S.R.O. 484, base text)','','','NOT_DETERMINED (r.22 later substituted and r.25 omitted by S.R.O. 17(E)/1993, publication 1993-12-06, effective NOT_DETERMINED)','APPLIED (pre-1993 text)','S.R.O. 17(E)/1993 (r.22 substituted; r.25 omitted) per chain seed; r.23(3) is conflict C-01 CONFLICTING','PROVISION_VERSION_CHANGED_AFTER_JUDGMENT','PPS Bedi cover; ARMY-RULES-CHAIN-01 seed @11ce905e'),
 ('SN_MUKHERJEE','Army Act 1950 s.164; Army Rules 1954 (then operative, re reasons)','1990 text','','','','NOT_DETERMINED','APPLIED','Army Rules r.62(1) later requires brief reasons (per curated note; instrument not verified by WS-B)','PROVISION_VERSION_CHANGED_AFTER_JUDGMENT (to verify, WS-A)','SN Mukherjee p.20'),
 ('RANJIT','Army Act 1950 ss.41, 130; Army Rules 1954 rr.106-133','1987 text','','','','NOT_DETERMINED','APPLIED','not checked','AMENDMENT_CHAIN_NOT_CHECKED','Ranjit JUDIS p.1 headnote (editorial) and pp.5-9'),
 ('GIRISH_MAIN','AFT Act 2007 s.22(1)(c); MoD instructions 31.01.2001 and 18.04.2016 (broad-banding)','AFT Act 2007; executive instructions','','','','NOT_DETERMINED','APPLIED','Clarification order 12.10.2026 not held','EXECUTIVE_INSTRUCTION_NOT_STATUTE','Girish paras 21-23'),
 ('MULLIKOTE','Pension Regulations for the Army 1961 para 125 and 2008 para 44 (condonation of shortfall)','1961 and 2008 Regs','','','','NOT_DETERMINED','APPLIED','not checked','TEMPORAL_SCHEME_SELECTION_REQUIRED','Mullikote para 97'),
]

def statutes():
    hdr = ['row_id','spec_key','case53_id','judgment','decision_date','provision_cited','version_applied_by_court','publication_date',
           'commencement_date','effective_date','effective_date_status','applied_at_judgment_date','later_change_or_successor','flag',
           'evidence_pointer','technical_review_state','legal_advisor_state','jag_validation_state']
    rows = []
    for i, s in enumerate(S, 1):
        k = s[0]; cid, name, d = CASE[k]
        rows.append([f'WSB-S-{i:03d}', k, cid, name, d] + list(s[1:]) + ['DATES_NOT_RESOLVED_BY_WS_B', 'NOT_STARTED', 'NOT_STARTED'])
    return hdr, rows

# ------------------------------------------------------------------ subsequent treatment
T = [
 # earlier (spec/case), proposition, later judgment, later copy sha, page, para, treatment, scope, kb, uncertainty
 ('NAVJOT','DCLR-SC-2005-L01','Secondary evidence of electronic records via ss.63/65 irrespective of s.65B','ANVAR','18','22','OVERRULED_IN_PART','Only the s.65B/secondary electronic evidence proposition; not the whole judgment','V9-JD-01;V9-JD-02;EV-*','Page image checked. Later 2024/2025 treatments (Ravishankar Tandon, Chandrabhan) recorded in v3.2/v3.3 not re-read by WS-B.'),
 ('ANVAR','DCLR-SC-2014-N12','s.65B is a complete code for secondary electronic evidence; certificate mandatory','ARJUN','80-81','72(a)-(b)','AFFIRMED_WITH_CLARIFICATION','Last sentence of Anvar read without "under Section 62 of the Evidence Act"','V9-JD-01;V9-JD-02','Page image p.81 checked.'),
 ('SHAFHI','DCLR-SC-2018-A10','Relaxation of s.65B(4) certificate where party not in control of device','ARJUN','81','72(a)','OVERRULED','Whole proposition on certificate relaxation','V9-* (see crosswalk)','Shafhi judgment itself not held (pending queue); treatment read from Arjun page image.'),
 ('SHRI_KANT','DCLR-SC-2015-N06','Ss.30-31 AFT Act bar/limit Art.226 writs against AFT orders','PARASHOTAM','22','32','DECLARED_NOT_GOOD_LAW (held "does not lay down the correct law")','Art.226 maintainability against AFT orders','V7-JD-02;V7-S09 users','Page image checked. Bench strength of Shri Kant Sharma (two judges per SCR cover in intern mirror) vs Parashotam (three judges).'),
 ('TARSEM','DCLR-SC-2008-N10','Arrears limited where claim based on continuing wrong (delay)','GIRISH_MAIN','15-16','22','DISTINGUISHED','Tarsem held of no assistance for broad-banding re-computation claims after Ram Avtar (in rem)','V7-JD-04;PEN-CS-09','Text layer only.'),
 ('DHARAMVIR','DCLR-SC-2013-N08','Entry-health presumption; onus on employer; Board must give reasons','NS_YADAV','12-15','14-21','DISTINGUISHED / LIMITED (not mechanical; undetectable mental disorders)','Presumption for diseases escaping detection at enrolment','PEN-J-01;PEN-J-03','Text layer only.'),
 ('DHARAMVIR','DCLR-SC-2013-N08','Entry-health presumption; onus on employer','ISAAC','91;93','34-35;39(ii)-(iii)','QUALIFIED_FOR_LATER_REGIME (ER 2008 Rule 7 proviso; due weight to Medical Board); NOT_OVERRULED','Claims after 15 years; scrutiny of Board reasons in pending matters','PEN-J-01;PEN-043;PEN-017','Page images checked. Respondents\' para 19.4 "continue to hold the field" is argument, not treatment.'),
 ('RAJBIR','DCLR-SC-2015-N09','Burden on employer; statement of reasons required','ISAAC','91;93','34-35;39(ii)-(iii)','QUALIFIED_FOR_LATER_REGIME; NOT_OVERRULED','as above','PEN-J-02','as above'),
 ('ANGAD','DCLR-SC-2015-L03','Unreasoned NANA label insufficient','ISAAC','61;69','16.4;19.4','REFERRED (court narrative p.61); argued as holding field (p.69, respondents)','see v3.5 file 04/05','PEN-*','WS-B did not re-read p.61; relies on v3.5 file 04 for the p.61 reference (not independently verified).'),
 ('MANJEET','DCLR-SC-2015-L02','Unexplained Board NANA cannot displace presumption','ISAAC','60-61','—','REFERRED (per v3.5 file 04; not re-read by WS-B)','—','PEN-*','Not independently verified in this pass.'),
 ('BALJIT;BALACHANDRAN;SURINDER_RATHORE','DCLR-SC-1996-L07;DCLR-SC-2005-L08;DCLR-SC-2008-L09','Pre-Dharamvir Board-deference line','ISAAC','49-51','—','REFERRED_HISTORICAL (per v3.5 file 04; not re-read by WS-B)','—','PEN-*','Not independently verified in this pass; no express overruling found by v3.5.'),
 ('KESHAR','DCLR-SC-2007-L10','Board opinion accepted; no entitlement','SURINDER_RATHORE','10','8','FOLLOWED','Board deference','PEN-*','Mirror copy of Surinder (SCR) p.10 "The above position was again highlighted in ... Keshar Singh". Isaac does not name Keshar (v3.5).'),
 ('BALACHANDRAN','DCLR-SC-2005-L08','Board opinion accepted; no entitlement','KESHAR','8','10','FOLLOWED','Board deference','PEN-*','Mirror copy of Keshar p.8.'),
 ('DHARAMVIR;RAJBIR','DCLR-SC-2013-N08;DCLR-SC-2015-N09','Presumption/onus','MANJEET','27','25-26','FOLLOWED','—','PEN-*','Mirror copy of Manjeet.'),
 ('DHARAMVIR;RAJBIR','DCLR-SC-2013-N08;DCLR-SC-2015-N09','Presumption/onus','ANGAD','16','17','FOLLOWED','—','PEN-*','Mirror copy of Angad.'),
 ('SN_MUKHERJEE;CHANDRA_KUMAR','DCLR-SC-1990-N02;DCLR-SC-1997-N07','No per se restriction on Art.226 review incl. courts-martial','PARASHOTAM','20-22','29-32','FOLLOWED / APPLIED','Art.226 against AFT orders','V7-JD-01;V7-JD-07;V7-JD-03','Page image p.22 checked.'),
 ('RANJIT','DCLR-SC-1987-R01','Proportionality and bias in court-martial','RANJIT_REVIEW','','','REVIEW_ORDER_NOT_HELD','Review Petition 43/1988 (10.08.1988) curated source is Indian Kanoon only','KB-016;KB-027','Treatment of the 1987 judgment by its own review order unknown; pending queue.'),
]

def treatment():
    hdr = ['row_id','earlier_spec_keys','earlier_case53_ids','proposition','later_judgment','later_copy_url','later_copy_sha256',
           'later_copy_role','pdf_page','para','treatment','scope','affected_kb_ids','uncertainty','exhaustiveness',
           'technical_review_state','legal_advisor_state','jag_validation_state']
    rows = []
    for i, t in enumerate(T, 1):
        later = t[3]
        if later in C:
            url, sha, role = C[later]; lname = CASE[later][1]
        else:
            url, sha, role, lname = '', '', 'NOT_HELD', later
        rows.append([f'WSB-T-{i:03d}', t[0], t[1], t[2], lname, url, sha, role, t[4], t[5], t[6], t[7], t[8], t[9],
                     'NOT_EXHAUSTIVE: absence of other treatment rows is NOT proof of no treatment',
                     ('PASSAGE_LOCATED_OFFICIAL_COPY' if role == 'OFFICIAL_COURT_COPY' else 'NOT_VERIFIED_ON_OFFICIAL_COPY'), 'NOT_STARTED', 'NOT_STARTED'])
    return hdr, rows

# ------------------------------------------------------------------ adverse / conflict queue
A = [
 ('A-01','P0','ISAAC','DCLR-SC-2013-N08;DCLR-SC-2015-N09;DCLR-SC-2015-L02;DCLR-SC-2015-L03','PEN-043;PEN-017;PEN-044;PEN-045;PEN-J-01;PEN-J-02','Isaac 2026 paras 34, 39(ii)-(iii): legal effect of ER 2008 assumed not decided; due weight to Medical Board; Rule 7 burden shift after 15 years. KB pension guidance resting on Dharamvir/Rajbir presumption needs date-of-claim qualification.','Isaac pp.91, 93 (page images e7f23a58..., 40b08feb...)','Legal advisor: how to state current law for claims (i) within 15 years, (ii) after 15 years, (iii) where ER 2008 legal effect is disputed.'),
 ('A-02','P0','ISAAC','—','PEN-J-01;PEN-J-02;PEN-043','Isaac p.69 para 19.4 ("continue to hold the field") is the respondents\' submission. Any KB/derived text presenting it as the Court\'s holding is wrong.','Isaac p.69 (text layer)','None - block such wording.'),
 ('A-03','P1','PARASHOTAM','DCLR-SC-2015-N06','V7-JD-02;V7-S09 users','Shri Kant Sharma held not to lay down the correct law (Parashotam para 32). Curated N06 treatment field says NOT_EXHAUSTIVELY_CHECKED and caveat only says "later jurisprudence must be displayed"; it should carry an explicit adverse-treatment flag (proposal; original not edited).','Parashotam p.22 (page image 0973bb4d...)','Confirm wording of the adverse flag.'),
 ('A-04','P1','NS_YADAV','DCLR-SC-2013-N08','PEN-J-01;PEN-J-03;PEN-CS-07','NS Yadav (2019) declines mechanical application of the entry-health presumption for mental disorders; KB PEN-J-03 cites NS Yadav - check it is not presented as supporting the presumption.','NS Yadav pp.12-15 paras 15-21','Legal advisor review of PEN-J-03 wording.'),
 ('A-05','P1','VIRENDRA','DCLR-SC-2020-002','J-02;CM-JD-04;SC02;V9-JD-04','Official Virendra PDF carries a CORRECTED version (pp.1-21, extra para 16: no imprisonment) and an uncorrected version (pp.22-42). Citations of the disposition must use the corrected version.','Virendra p.21 (page image aa92d37a...)','None; data hygiene.'),
 ('A-06','P1','VIRENDRA','DCLR-SC-2020-002','J-02;CM-JD-04','Official copy heading reads "Section 16 of the Army Act, 1950" above a quotation of s.16 AFT Act 2007. KB should cite s.16 AFT Act; do not reproduce the heading.','Virendra p.18/39','None.'),
 ('A-07','P1','ANGAD','DCLR-SC-2015-L03','PEN-*','IAF Pension Regulations Reg 153 (Angad cover) vs Isaac p.61 description as Army Reg 153 (v3.5 file 05). Cross-service statement blocked.','Angad mirror p.1; v3.5/05','Specialist review.'),
 ('A-08','P1','MULLIKOTE','DCLR-SC-2026-N16','PEN-J-07','Official Mullikote PDF also holds two versions (CORRECTED + second copy); curated pinpoints "33-44, 51" unmapped to either copy.','Mullikote pp.1, 32, 61-62','None; pinpoint mapping.'),
 ('A-09','P2','PPS_BEDI','DCLR-SC-1982-001','J-01;CM-JD-01','Curated pinpoints "40","14" cannot be located in the unnumbered JUDIS copy; Rule 180 passage is at JUDIS pp.34-35 (SCR 438-439). PPS Bedi applies pre-1993 rr.22-25 (r.22 substituted, r.25 omitted by S.R.O. 17(E)/1993 per chain seed).','PPS Bedi pp.34-35','WS-A to confirm r.22/r.25 chain; legal advisor: present-day relevance.'),
 ('A-10','P1','INTAKE','—','—','Intern keyword "invalided" also matches "invalidation": 243 kept documents (33 marked relevant) are kept only by that word; 288 documents show no military signal in WS-B re-check. Intern topic "invalidment" over-assigned.','intake_manifest.csv flags; pipeline/judgments.py KEYWORDS (main)','Owner/intern: tighten keyword list; re-run relevance.'),
 ('A-11','P1','INTAKE','DCLR-SC-1997-N07;DCLR-SC-2008-L05','V7-JD-01','Intern filter removed L. Chandra Kumar (1997-03-18) and S.R. Dhingra (2007-12-14) as "no military keyword"; L. Chandra Kumar is relied on by KB V7-JD-01 and by Parashotam para 32. Filter false negative for AFT-jurisdiction precedent.','data/excluded_judgments.jsonl (sha a59ab09d..., c42a5be2...)','Owner: allow-list of cited precedents irrespective of keywords.'),
 ('A-12','P2','INTAKE','—','—','Intern corpus has NO AFT judgments (AFT crawl blocked) although the brief rates AFT as priority 1 with largest volume.','raw-data ad77758d data/meta (0 aft-* judgment records)','Owner decision on lawful AFT route (no bare-IP HTTP, no CAPTCHA bypass).'),
 ('A-13','P2','RANJIT_REVIEW','DCLR-SC-1988-R02','KB-016;KB-027','Curated primary_source_url for the review order is Indian Kanoon (commercial) - not evidence.','cases_53 R02','Acquire official copy (pending queue).'),
 ('A-14','P2','SANTOSH_LOHAR','—','V7-JD-05','KB date 4 Oct 2023 / 2023:PHHC:127834 vs intern CWP/3118/2023 dated 2023-10-03; intern text font-garbled.','identity_resolution.csv','Official P&H copy needed.'),
 ('A-15','P2','INTAKE','—','—','Intern judgment counts on raw-data (4,259 records: 2,871 relevant/1,341 borderline/47 not_checked) differ from main PROGRESS.md (2,331/1,035/47). Which snapshot is canonical?','raw-data ad77758d vs main PROGRESS.md 2026-11-22','Owner: confirm canonical snapshot (HF dataset).'),
]

def adverse():
    hdr = ['item_id','severity','source_spec','affected_case53_ids','affected_kb_ids','issue','evidence_pointer','question_for_reviewer',
           'state','technical_review_state','legal_advisor_state','jag_validation_state']
    return hdr, [list(a) + ['OPEN', 'TECHNICAL_REVIEW_COMPLETED' if a[0] in ('A-05','A-06','A-10','A-11','A-12','A-15') else 'PROPOSAL', 'NOT_STARTED', 'NOT_STARTED'] for a in A]

# ------------------------------------------------------------------ pending source queue (no downloads made)
P = [
 ('PQ-001','RAM_SARUP','DCLR-SC-1964-A11','Supreme Court of India','W.P. 166 of 1963 (per v3.2 NDLI lead)','1963-12-12','HF legal_knowledge/judgment_originals/sci/historical/v3.3/ram_sarup_1963.pdf (sha 88f84411...) per issue #3; not in repo/scratchpad','P0','Read HF-held JUDIS copy; not in intern corpus (intern has a different 1983 Ram Sarup case, excluded).'),
 ('PQ-002','MANI_RAM','DCLR-SC-2016-L04','Supreme Court of India','C.A. 4409 of 2011 (per v3.2 office-report lead)','2016-02-11','Court-hosted signed order (case-status record); only third-party copy cce64004... exists on HF','P0','Original SC order needed for byte parity.'),
 ('PQ-003','DHINGRA_SR','DCLR-SC-2008-L05','Supreme Court of India','T.C.(C) 106 of 2006 (per v3.2 NDLI lead)','2007-12-14','Intern downloaded then removed it (excluded log sha c42a5be2...); AWS e-SCR mirror URL in excluded log','P3','Civilian/Railways comparator; acquire only if retained.'),
 ('PQ-004','MANJEET','DCLR-SC-2015-L02','Supreme Court of India','C.A. 4357-4358 of 2015','2015-05-12','unknown (sci.gov.in judgment search has CAPTCHA; do not bypass)','P0','Official copy needed; intern holds mirror only.'),
 ('PQ-005','ANGAD','DCLR-SC-2015-L03','Supreme Court of India','C.A. 11208 of 2011','2015-02-24','unknown','P0','as above'),
 ('PQ-006','BALJIT','DCLR-SC-1996-L07','Supreme Court of India','C.A. 13272 of 1996','1996-10-11','unknown','P0','as above'),
 ('PQ-007','BALACHANDRAN','DCLR-SC-2005-L08','Supreme Court of India','case no. not on mirror cover','2005-10-21','unknown','P0','as above'),
 ('PQ-008','SURINDER_RATHORE','DCLR-SC-2008-L09','Supreme Court of India','C.A. 1960 of 2008','2008-03-13','unknown','P0','as above'),
 ('PQ-009','KESHAR','DCLR-SC-2007-L10','Supreme Court of India','case no. not on mirror cover','2007-04-20','unknown','P0','as above'),
 ('PQ-010','NAGA','DCLR-SC-1997-L11','Supreme Court of India','W.P.(Crl.) 550 of 1982 and connected (to confirm)','1997-11-27','unknown','P0','as above; case number to confirm from official copy'),
 ('PQ-011','GIRISH_CLAR','DCLR-SC-2026-008','Supreme Court of India','M.A. in C.A. 6820-6824/2018 (2026 INSC 1113)','2026-10-12','unknown; KB PEN-J-06 cites Indian Kanoon only','P1','Not in intern corpus.'),
 ('PQ-012','RANJIT_REVIEW','DCLR-SC-1988-R02','Supreme Court of India','Review Petition 43 of 1988','1988-08-10','unknown; curated cites Indian Kanoon only','P2',''),
 ('PQ-013','INDER_JIT','DCLR-SC-1997-N03','Supreme Court of India','not recorded','1997-03-20','unknown','P1','Not in intern corpus or excluded log.'),
 ('PQ-014','CHANDRA_KUMAR','DCLR-SC-1997-N07','Supreme Court of India','C.A. 481 of 1989 and connected (to confirm)','1997-03-18','Intern downloaded then removed (excluded log sha a59ab09d...)','P1','Restore via intake allow-list rather than new collection.'),
 ('PQ-015','SODHI','DCLR-SC-1990-A01','Supreme Court of India','W.P.(Crl.) 478 of 1989','1990-11-30','unknown','P2',''),
 ('PQ-016','RAVINDER','DCLR-SC-2012-A05','Supreme Court of India','C.A. 1837 of 2009','2012-05-23','https://api.sci.gov.in/jonew/bosir/orderpdf/1525127.pdf (curated record; not fetched)','P2',''),
 ('PQ-017','RAM_AVTAR','DCLR-SC-2014-A08','Supreme Court of India','C.A. 418 of 2012 and connected','2014-12-10','unknown (KB PEN-J-04 cites an office report HTML, not the order)','P1','Girish 2026 para 22 relies on it as in rem.'),
 ('PQ-018','ROJER;PRAFUL;SHAFHI;ANVAR;ARJUN','DCLR-SC-2019-A04;DCLR-SC-2003-A06;DCLR-SC-2018-A10','Supreme Court of India','see cases_53','various','Anvar and Arjun official copies already held (scratchpad); Rojer, Praful, Shafhi not held','P3','Non-military; outside intern filter by design.'),
 ('PQ-019','SOM_DATT;BALBIR;ADG_CBI;SONU','','Supreme Court of India','AIR 1969 SC 414; (1995) 1 SCC 90; (2012) 6 SCC 228; Sonu (2017)','various','Som Datt in intern corpus (mirror); others not held','P2','KB 87-code register cases.'),
 ('PQ-020','SANDEEP_SHARMA','','High Court of Delhi','not recorded (KB SRC-SANDEEP)','2024','unknown; intern has no match','P2',''),
 ('PQ-021','SANTOSH_LOHAR','','High Court of Punjab and Haryana','CWP 3118 of 2023 (intern) / 2023:PHHC:127834 (KB)','2023-10-03 or 2023-10-04','P&H HC official copy','P2','Date conflict.'),
 ('PQ-022','NALIN;POOJA_PAL;JOGINDER_HP','','Supreme Court / High Court (unknown)','not recorded','unknown','unknown','P2','KB ADM-JD-03/05, V8-JD-06 cases with no identity data.'),
]

def pending():
    hdr = ['queue_id','spec_key','case53_id','court','case_number','decision_date','official_url_or_holder_if_known','priority','note',
           'action','downloaded_by_ws_b']
    return hdr, [list(p) + ['ACQUISITION_REQUEST_ONLY', 'NO'] for p in P]

# ------------------------------------------------------------------ open questions
Q = [
 ('OQ-01','Which intern snapshot is canonical for intake: raw-data ad77758d (4,259 judgment records) or the HF dataset / main PROGRESS.md figures (3,413)?','Owner'),
 ('OQ-02','Are AWS Open Data mirror PDFs (e-SCR / eCourts copies) acceptable as carrier for holdings pending court-hosted copies, or must every holding be re-pinned to a court-hosted copy? (Policy v1 suggests mirror = THIRD_PARTY_ARCHIVAL_FACSIMILE with HASH_ONLY fidelity.)','Owner / legal advisor'),
 ('OQ-03','SCR copies carry editorial headnotes; should the intake strip/flag headnote pages so they are never quoted as holdings?','Owner / WS-D'),
 ('OQ-04','Legal effect of Entitlement Rules 2008 after Isaac para 34 ("assuming they otherwise have legal effect"): how should KB state the operative scheme by date of discharge/claim?','Legal advisor'),
 ('OQ-05','For Isaac para 39(iii), is the 15-year period measured from discharge/invalidment/release to the claim (para 33) or to approaching the forum (para 39(iii))?','Legal advisor'),
 ('OQ-06','Should 87-code KB records citing Shri Kant Sharma (V7-S09) be flagged as relying on a decision held not to lay down correct law?','Legal advisor'),
 ('OQ-07','Is there a lawful, non-CAPTCHA official route for Supreme Court judgments by case number (for the P0 official copies)?','Owner'),
 ('OQ-08','The intern keyword filter removed L. Chandra Kumar and S.R. Dhingra; should cited precedents (53 cases + KB-cited) be allow-listed regardless of keywords?','Owner / intern'),
 ('OQ-09','Which BSA 2023 / BNS 2023 provisions correspond to Evidence Act s.65B and IPC offences in Jasbir for KB current-law notes? (correspondence tables on raw-data are unverified)','WS-A / legal advisor'),
 ('OQ-D-004','ADM-JD-01/03/04/05 paragraph pinpoints with no case named in references. WS-B resolution: ADM-JD-01 -> Kuldeep Yadav (SC 25 Sep 2019, CA 7603/2019; intern mirror doc sc-2019-union-of-india-ors-2019insc1083): paras 22-26 and 34 exist and match the digest topic (holdings WSB-H Kuldeep rows; mirror only, official copy pending). ADM-JD-03 -> Brig Nalin Kumar Bhatia v UoI: no copy in intern corpus or scratchpad - paras 6-15 NOT VERIFIED. ADM-JD-04 -> "MA 1913/2022, Nitisha implementation" (a miscellaneous application in the Nitisha matter; date/court record not identified): NOT VERIFIED; the 25 Mar 2021 Nitisha judgment (sc-2021-lt-col-nitisha-ors-2021insc210) is a different document. ADM-JD-05 -> Lt Col Pooja Pal v UoI: not in intern corpus; excluded log holds an SC "POOJA PAL versus UNION OF INDIA" dated 2016-01-22 (lead only, identity not established). Recommendation (proposal): references should name the authority they pinpoint.','WS-D / owner'),
 ('OQ-D-008','31/53 curated cases have no KB link (WS-D) and 10 have an empty holding. WS-B crosswalk adds case53_kb_link_count and case53_holding_empty columns; empty-holding cases are flagged NOT_CITABLE_AS_AUTHORITY_HOLDING_EMPTY in crosswalk (WS-B counts in intake_stats.json; WS-B lexical leads may differ from WS-D strict count).','WS-D / owner'),
 ('OQ-D-009','DCLR-SC-2020-002 (Virendra) lists DCLR-SC-1982-001 (PPS Bedi) as related but not the reverse. Evidence: the official Virendra PDF cites Prithi Pal Singh Bedi (PDF pp.11 and 32, one per version), so a one-way cites edge Virendra -> Bedi is supported; all other related_cases pairs in cases_53 are reciprocal. Proposal: treat as directional "cites" (intended) rather than adding a reverse link; originals not edited.','Owner / WS-D'),
 ('OQ-D-012','None of the 53 curated URLs equals an intern source_url (URL equality). WS-B mapped by identity (cover-page parties/date/case no.): see identity_resolution.csv columns intern_doc_ids and intern_sha256 (34 of 53 mapped; count in intake_stats.json key case53_mapped_to_intern_doc). Intern copies are AWS mirror bytes, so their SHA-256 is not the court copy SHA.','WS-D / owner'),
 ('OQ-10','Virendra and Mullikote official PDFs contain two versions; which version is the authoritative signed judgment?','Owner (court record)'),
]

def questions():
    hdr = ['question_id', 'question', 'owner', 'state']
    return hdr, [list(q) + ['OPEN'] for q in Q]

def write(name, hr):
    hdr, rows = hr
    with open(os.path.join(WS, name), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, lineterminator='\n'); w.writerow(hdr)
        for r in rows:
            assert len(r) == len(hdr), (name, r[:2], len(r), len(hdr))
            w.writerow(r)
    print(name, len(rows))

if __name__ == '__main__':
    write('holdings_register.csv', holdings())
    write('statutes_cited_effective_dates.csv', statutes())
    write('subsequent_treatment.csv', treatment())
    write('adverse_conflict_queue.csv', adverse())
    write('pending_source_queue.csv', pending())
    write('open_questions.csv', questions())
