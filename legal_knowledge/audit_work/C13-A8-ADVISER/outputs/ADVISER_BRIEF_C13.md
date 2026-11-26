# Mimamsa Cycle 13: consolidated legal-adviser package (A8)

**PREPARED BY AUTOMATED AGENTS. EVERY QUESTION IS NOT LEGALLY REVIEWED.** This package draws no legal conclusion, changes no record, status, edge or register, and invents no citation. Each question is one the Cycle 12 or Cycle 13 workstreams already raised. Readings of source pages were made by AI agents and are not human-confirmed. AUTH-LEDGER stays at version 0.

Restricted material RM-001 (see `config/restricted_material.json`) is excluded from every question, anchor and file in this package. It is referred to here by its restriction id only.

## 1. How to use this package

- `outputs/ADVISER_QUESTIONS_C13.csv` is the register: one row per de-duplicated question. Record your answer in the columns `adviser_answer_status` (AWAITING_ADVISER, ANSWERED, DEFERRED_BY_ADVISER or WITHDRAWN), `adviser_answer`, `adviser_role`, `answer_date` and `answer_reference`. Every row starts as `AWAITING_ADVISER`, with `legal_review_status` = `NOT LEGALLY REVIEWED`.
- `outputs/ADVISER_ANCHORS_C13.csv` gives the exact source anchors of each question: `doc_id`, the sha256 of the held copy, and the page. `page_kind` says which page numbering is meant (`TEXT_LAYER_PAGE_ad77758d` is the `[[page N]]` marker in `data/text/<doc_id>.txt` at raw-data commit ad77758d; `PDF_PAGE` is the PDF page of the copy; `PRINTED_PAGE` is the page number printed on it; `PAGE_AS_STATED_IN_SOURCE` is a bare 'p.N' in the originating artefact; `NOT_STATED_IN_SOURCE` means the artefact gives no page). `RECORD` anchors point to the originating audit row, hash-pinned to that workstream's SHA256SUMS. Every anchor resolves to a register that binds the doc_id to the sha256 and records a stored path (`binding_registers`, `stored_path`).
- `outputs/DEDUP_MAP_C13.csv` maps every originating question id to the A8 question that carries it.
- Applying any answer is a separate, reviewed change with owner approval. Do not edit this package to record decisions other than in the status columns of the register.

## 2. Priorities

Priorities are a triage order by operational impact, set by the coordinator; the adviser sets the final priority. Originating priorities are kept in `origin_priorities`.

| Priority | Rule | Questions |
| --- | --- | ---: |
| P0 | Answer controls the wording of a procedural safeguard that would be put to an accused (operative text in direct conflict between held copies). | 1 |
| P1 | Answer controls whether a military-law authority or provision is current, binding or in force on a date (overruling/relation, commencement, temporal axis, repealed-code cross-references), the operative text of a rule used in court-martial or court-of-inquiry procedure, the pension-rules version, a form that blocks R04 closure or every template, or who may approve operational use. | 34 |
| P2 | Everything else: citation-level evidence promotions, own-voice overruling leads outside military law, relevance-scope decisions, documentary verification (case numbers), form text discrepancies, source authority ranking, acquisition and historical-window questions. | 169 |
| **Total** | | **204** |

## 3. Sources and de-duplication

| Source | Origin items | Carried in |
| --- | ---: | --- |
| C12 adviser package (59) | 59 | see DEDUP_MAP_C13.csv |
| A5 treatment candidates and case numbers | 14 | see DEDUP_MAP_C13.csv |
| A4 adviser packet (96) | 96 | see DEDUP_MAP_C13.csv |
| A6 forms (register, README, review F07) | 12 | see DEDUP_MAP_C13.csv |
| A1 MANUAL_REVIEW (6) and UNCERTAIN queue | 52 | see DEDUP_MAP_C13.csv |

29 origin items were merged into another question because they ask the same thing (C12/A4 pairs that cross-reference each other, five identical A4 CrPC cross-reference rows, 12 A5 overruling/disapproval candidates on passages C12 already asks about, and A6 review F07, which is the C12 'who confirms AI page readings' question). A7's dispositions contain no legal question (`BUILD_INFO.json` `a7_scan`).

## 4. Questions by priority

### P0 (1)

**A8-Q034** (TEXT_CONFLICT; from C12:AQ-STA-01, A4:A4-ADV-068)  
*Disputed statutory edges and commencement | A4 Army Rule 23(3) caution wording (C-01)*  
Does the adviser accept the archival facsimile of the Gazette of 27-11-1954 (S.R.O. 484, printed p.300) as evidence of the notified text of r.23(3) pending a certified copy; is the amendment search sufficient given the remaining gaps; may the interim wording C9-CP-B01 to B06 (which quotes both versions and adopts neither) be displayed; and is the accused's right not to make a statement secured independently of r.23(3) (for example by Art. 20(3)), which C9 has not checked?  
Anchors (6): rules-army-rules-1954 48f52219121b p.41; C5-SRC-P0-ARMY-RULES-1954 c5ef95a9d553 p.10  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

### P1 (34)

**A8-Q001** (STATUS_RELATION; from C12:AQ-HCW-01, A5:GT-ba24ae19e50b1234)  
*High Court writs vs AFT (Parashotam Dass / Shri Kant Sharma)*  
Which typed relation, if any, should the corpus record from Union of India v Parashotam Dass (2023 INSC 265, three Judges) to Union of India v Maj Gen Shri Kant Sharma ((2015) 6 SCC 773, two Judges): overrules / overruled_by, "declared not good law", "disapproved", or another label?  
Anchors (9): sc-2023-union-of-india-ors-2023insc265 483b70cbbe27 p.17; sc-2023-union-of-india-ors-2023insc265 483b70cbbe27 p.18; sc-2023-union-of-india-ors-2023insc265 483b70cbbe27 p.4; sc-2023-union-of-india-ors-2023insc265 483b70cbbe27 p.1; C5-SRC-J-SC-2023-PARASHOTAM fe19875b19ed p.22; sc-2015-union-of-india-ors-2015insc206 86de3643e66e p.1  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q002** (STATUS_RELATION; from C12:AQ-HCW-02)  
*High Court writs vs AFT (Parashotam Dass / Shri Kant Sharma)*  
Does any limb of Shri Kant Sharma survive Parashotam para 32, in particular the alternative-remedy guidance in para 34(iii)-(iv), given that the J&K High Court relied on Shri Kant Sharma on 06-10-2025 without citing Parashotam?  
Anchors (8): sc-2023-union-of-india-ors-2023insc265 483b70cbbe27 p.17; sc-2023-union-of-india-ors-2023insc265 483b70cbbe27 p.18; sc-2015-union-of-india-ors-2015insc206 86de3643e66e p.47; sc-2015-union-of-india-ors-2015insc206 86de3643e66e p.49; sc-2015-union-of-india-ors-2015insc206 86de3643e66e p.33; hc-jkl-2025-wp-c-2370-2025-jkhc010050362025-1-2025-10-06 7be94c187e5d p.2; +1 more  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q004** (STATUS_RELATION; from C12:AQ-HCW-04)  
*High Court writs vs AFT (Parashotam Dass / Shri Kant Sharma)*  
Do the 13 research records that depend on Parashotam state the High Court writ position correctly in the light of para 32, and may the C9 pinpoint and holding corrections (F-JUD-017; C9-CP-E01 to E06) be applied?  
Anchors (5): sc-2023-union-of-india-ors-2023insc265 483b70cbbe27 p.17; sc-2023-union-of-india-ors-2023insc265 483b70cbbe27 p.18; C5-SRC-J-SC-2023-PARASHOTAM fe19875b19ed p.22; sc-2023-union-of-india-ors-2023insc1074 c510f143147a p.16  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q006** (STATUS_RELATION; from C12:AQ-PEN-01)  
*Pension arrears and entitlement (Tarsem / Girish / unheld clarification / Ram Avtar / Dharamvir)*  
After Union of India v Sgt Girish Kumar (2026 INSC 149) para 22, may the AFT and High Courts still restrict arrears to three years under Union of India v Tarsem Singh ((2008) 8 SCC 648) for claims outside Girish's two grounds (for example initial-grant rather than re-computation disability-pension claims)?  
Anchors (11): sc-2008-union-of-india-ors-2008insc930 f8a14181e47c p.5; sc-2008-union-of-india-ors-2008insc930 f8a14181e47c p.6; sc-2026-union-of-india-through-its-sec-2026insc149 da0304734666 p.11; sc-2026-union-of-india-through-its-sec-2026insc149 da0304734666 p.2; sc-2026-union-of-india-through-its-sec-2026insc149 da0304734666 p.1; C5-SRC-J-SC-2026-MULLIKOTE 10e1954f2e39 p.27; +4 more  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q007** (STATUS_RELATION; from C12:AQ-PEN-02)  
*Pension arrears and entitlement (Tarsem / Girish / unheld clarification / Ram Avtar / Dharamvir)*  
Which relation should be recorded from Girish to Tarsem ("distinguishes" is proposed; the documents are recorded as supporting no stronger edge), and may the warning wording in C9-CP-A01 to A04 (which states that Tarsem is not recorded as overruled) be applied?  
Anchors (3): sc-2026-union-of-india-through-its-sec-2026insc149 da0304734666 p.11; sc-2026-union-of-india-through-its-sec-2026insc149 da0304734666 p.1  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q008** (SOURCE_AUTHORITY; from C12:AQ-PEN-03)  
*Pension arrears and entitlement (Tarsem / Girish / unheld clarification / Ram Avtar / Dharamvir)*  
Until an official copy of the reported 12-10-2026 order (reported as 2026 INSC 1113) is obtained and read, may the corpus state its content at all (and if so only with an "UNVERIFIED SOURCE" flag)? Will the owner/adviser authorise acquisition of an official copy, or confirm that it does not exist?  
Anchors (1): legal_knowledge/audit_work/C12-CONSOLIDATION/adviser_package/ADVISER_QUESTIONS.csv [id=AQ-PEN-03]  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q009** (STATUS_RELATION; from C12:AQ-PEN-04)  
*Pension arrears and entitlement (Tarsem / Girish / unheld clarification / Ram Avtar / Dharamvir)*  
Is the corpus framing of the February 2026 Girish judgment as a "case-specific arrears award" supported by the judgment itself?  
Anchors (3): sc-2026-union-of-india-through-its-sec-2026insc149 da0304734666 p.11; hc-ph-2026-cwp-7955-2026-phhc010370702026-1-2026-03-17 4184df8b2caa p.3  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q011** (STATUS_RELATION; from C12:AQ-PEN-06)  
*Pension arrears and entitlement (Tarsem / Girish / unheld clarification / Ram Avtar / Dharamvir)*  
How far does Union of India v Col N C Isaac (2026 INSC 993; paras 34-35, 39) limit the Dharamvir Singh presumption for claims under the Entitlement Rules 2008, and which pension research records need a rules-version or limitation note?  
Anchors (4): sc-2013-dharamvir-singh-2013insc408 a9ccc45cd8c4 p.27; C5-SRC-J-SC-2026-ISAAC 3f49a31464fe p.91; C5-SRC-J-SC-2026-ISAAC 3f49a31464fe p.93  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q036** (TEXT_CONFLICT; from C12:AQ-STA-03)  
*Disputed statutory edges and commencement*  
Which text of r.168(2) is current: the India Code compilation, which still prints the field-punishment words, or S.R.O. 17(E)/1993 item 31, which omits them? (Owner first to register the conflict.)  
Anchors (2): rules-army-rules-1954 48f52219121b p.189  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q039** (COMMENCEMENT_TEMPORAL; from C12:AQ-STA-06, C12:AQ-STA-11, A4:A4-ADV-077)  
*Disputed statutory edges and commencement | A4 Instruments that print no commencement clause (S.R.O. 484/1954 and 13 amending S.R.O.s; Army (Amendment) Act 1992)*  
What is the commencement date of the Army (Amendment) Act 1992 (37 of 1992), which prints no commencement clause (AQ-05: effect of an Act with no commencement clause), and therefore of the 18 Army Act provisions it changed (including the omission of field punishment, ss.75-76, and of s.127)?  
Anchors (6): act-army-1950 e47a4265813e p.27; act-army-1950 e47a4265813e p.36; act-army-1950 e47a4265813e p.48  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q040** (LEGAL_INTERPRETATION; from C12:AQ-STA-07)  
*Disputed statutory edges and commencement*  
Is "Apply the earliest relevant knowledge rule in Section 122(1)" a P1 misdescription or a P2 drafting ambiguity, and may the statute-tracking wording C9-CP-D01 replace it? Do s.122 and s.123(2) apply cumulatively to a person who has ceased to be subject to the Act? Which version applies where the offence or cessation preceded Act 37 of 1992?  
Anchors (1): legal_knowledge/audit_work/C12-CONSOLIDATION/adviser_package/ADVISER_QUESTIONS.csv [id=AQ-STA-07]  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q043** (COMMENCEMENT_TEMPORAL; from C12:AQ-STA-10, A4:A4-ADV-079)  
*Disputed statutory edges and commencement | A4 AFT Act s.9A (2017 insertion, 2021 amendment deemed 04-04-2021, 2026 substitution)*  
From what date does AFT Act s.9A operate in its 2017 inserted form and in its 2026 substituted form, given that both amending Acts commence by notification (not held) and the compilation gives "w.e.f." dates; and what is the effect of the TRA 2026 repeal of the TRA 2021 with savings?  
Anchors (10): act-armed-forces-tribunal-2007 665863d1abb8 p.7; act-the-finance-act-2017 7a5551bab085 p.53; act-the-tribunals-reforms-act-2026 be619533e457 p.1; act-the-finance-act-2017 7a5551bab085 p.64; act-the-tribunals-reforms-act-2021 0c2f4e9e023d p.1; act-the-tribunals-reforms-act-2021 0c2f4e9e023d p.13  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q044** (TEXT_CONFLICT; from C12:AQ-STA-12, A4:A4-ADV-069)  
*Disputed statutory edges and commencement | A4 Army Rule 182 as substituted in 1993 (SC4-01)*  
Which text of r.182 (proceedings of a court of inquiry not admissible) is operative: the 1993 substitution (S.R.O. 17(E)/1993 item 36) or the 1954 notified text, as compared with the compilation and MML 2?  
Anchors (4): rules-army-rules-1954 48f52219121b p.197; C5-SRC-P0-AR-AMD-AR-029 e9bf2114ab63 p.18  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q045** (TEXT_CONFLICT; from C12:AQ-STA-13, A4:A4-ADV-071)  
*Disputed statutory edges and commencement | A4 Army Rule 192 proviso (C-02)*  
Which text of the r.192 proviso is operative (amending instrument vs official consolidation vs manual; manual footnote cites S.R.O. 215)?  
Anchors (3): C5-SRC-P0-AR-AMD-AR-011 be7fefc96676 page not stated  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q046** (TEXT_CONFLICT; from C12:AQ-STA-14, A4:A4-ADV-070)  
*Disputed statutory edges and commencement | A4 Army Rule 177(1)-(2) (C-03)*  
Which text of r.177(1)-(2) is operative? The conflict is CONFLICTING pending text comparison and legal review.  
Anchors (3): C5-SRC-P0-AR-AMD-AR-031 ca5d79c25a98 page not stated  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q047** (TEXT_CONFLICT; from C12:AQ-STA-15, C12:AQ-STA-16, A4:A4-ADV-072)  
*Disputed statutory edges and commencement | A4 Army Rules 193/194 prescribed officer (C-04, C-08, C-09)*  
Does r.193 cover s.90(i) as well as s.91(i), and which instrument gives the current text ("an Army" vs "the Army")?  
Anchors (8): rules-army-rules-1954 48f52219121b p.209; C5-SRC-P0-AR-AMD-AR-023 4392f326c1b9 page not stated; C5-SRC-P0-AR-AMD-AR-025 31fedb68e25a page not stated; C5-SRC-P0-AR-AMD-AR-029 e9bf2114ab63 p.19  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q050** (COMMENCEMENT_TEMPORAL; from C12:AQ-STA-19, A4:A4-ADV-080)  
*Disputed statutory edges and commencement | A4 BNS/BNSS/BSA commencement and the BNS s.106(2) exception*  
On what evidence is the 01-07-2024 commencement of the BNS, BNSS and BSA to be recorded (notifications not held), and how do Army Act and Army Rules references to the CrPC (e.g. r.133(3) to CrPC s.340) and rules made under the CrPC (CCCM Rules 1978) read after BNSS s.531 and its saving s.531(2)(b)?  
Anchors (6): act-bnss-2023 572c79880b9f p.174; act-bns-2023 d4449e9995b2 p.16; act-bnss-2023 572c79880b9f page not stated; act-bsa-2023 554b2b4ae3d9 p.10  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q051** (CROSS_REFERENCE; from C12:AQ-STA-20, A4:A4-ADV-096)  
*Disputed statutory edges and commencement | A4 evidence provisions applied at courts-martial (e.g. electronic records) -> IEA 1872*  
From what date, and for which pending proceedings, is AA s.133's reference to the Indian Evidence Act 1872 to be read as a reference to the BSA (General Clauses Act s.8; BSA s.170(2))?  
Anchors (5): act-army-1950 e47a4265813e p.37; act-bsa-2023 554b2b4ae3d9 p.10; act-bsa-2023 554b2b4ae3d9 p.51  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q055** (ROLE_PROCESS; from C12:AQ-ROL-01)  
*Legal-approval role (PR #46 F-01)*  
For each output class (authoritative template, mandatory constraint, procedural checklist, definitive advisory), is a designated legal-adviser decision sufficient, or is formal JAG validation required? How does an approval artefact reach an air-gapped deployment (signed release import only, or Admin transcription of an external artefact with the artefact attached, recording not being approving)?  
Anchors (1): legal_knowledge/audit_work/C12-CONSOLIDATION/adviser_package/ADVISER_QUESTIONS.csv [id=AQ-ROL-01]  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q057** (ROLE_PROCESS; from C12:AQ-ROL-03, A6:review_c13_a6_1b05490f/F07)  
*Legal-approval role (PR #46 F-01)*  
Who on the legal side reviews the proposed supersession, overruling and amendment edges in this package (an open question in the project brief), and who performs the human or reviewer-attested confirmation of AI page readings that option B2 of C9 decision P-B (recommended, not adopted) would require before an entry can create an anchor?  
Anchors (2): legal_knowledge/audit_work/C12-CONSOLIDATION/adviser_package/ADVISER_QUESTIONS.csv [id=AQ-ROL-03]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [all 21 R04_CLOSURE_RECOMMENDED families (r04_status)]  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q125** (LEGAL_INTERPRETATION; from A4:A4-ADV-073)  
*SCOPE | Army Rule 135 'or abstract' omission (S.R.O. 17(E)/1993 item 25; C12F F-09)*  
Does item 25 omit 'or abstract' at both places in r.135 ('summary or abstract of evidence given to the accused'; 'such notice or abstract having been given') and with what effect on the notice/abstract procedure described in V9-WF-10 and V9-SC-14?  
Anchors (3): C5-SRC-P0-ARMY-RULES-1954 c5ef95a9d553 p.41; C5-SRC-P0-AR-AMD-AR-029 e9bf2114ab63 p.17  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q127** (TEXT_CONFLICT; from A4:A4-ADV-075)  
*ALLEGED_AMENDMENT | Army Rule 15 '[or Military Secretary]' (OQ-A-10 / GAP-15)*  
Should the r.15 text be read with or without '[or Military Secretary]' until the source instrument is located?  
Anchors (3): C5-SRC-P0-ARMY-RULES-1954 c5ef95a9d553 p.297; C5-SRC-P0-AR-AMD-AR-006 0b4c5b72ea3d p.142  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q128** (TEXT_CONFLICT; from A4:A4-ADV-076)  
*ALLEGED_AMENDMENT | Army Rule 22 and S.R.O. 258/2002 (AR-030)*  
Pending location of S.R.O. 258/2002, should r.22 be treated as the 1993 substituted text only?  
Anchors (3): C5-SRC-P0-AR-AMD-AR-029 e9bf2114ab63 p.14; C5-SRC-P0-AR-AMD-AR-029 e9bf2114ab63 p.12  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q130** (SOURCE_AUTHORITY; from A4:A4-ADV-082)  
*VERSION_IDENTITY | Entitlement Rules 2008: two non-identical versions recorded*  
Which ER 2008 text is the notified one?  
Anchors (1): legal_knowledge/audit_work/C13-A4-STATUTORY/outputs/ADVISER_REVIEW_PACKET_A4.csv [packet_id=A4-ADV-082]  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q131** (COMMENCEMENT_TEMPORAL; from A4:A4-ADV-083)  
*TEMPORAL_AXIS | Army Rules 1954 (all versions)*  
Which date selects the governing version of a rule: the date of the alleged conduct, the date proceedings commenced, the date of the specific procedural act (e.g. hearing of charge, recording of SoE, CoI sitting), or the date a document was prepared/reviewed?  
Anchors (1): legal_knowledge/audit_work/C13-A4-STATUTORY/outputs/ADVISER_REVIEW_PACKET_A4.csv [packet_id=A4-ADV-083]  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q132** (COMMENCEMENT_TEMPORAL; from A4:A4-ADV-084)  
*TEMPORAL_AXIS | Army Act 1950*  
Which date (conduct, proceedings, procedural act or document preparation/review) selects the governing version of an Army Act section, e.g. s.122 limitation as substituted by Act 37/1992, or ss.75-76 and 127 omitted by Act 37/1992?  
Anchors (1): legal_knowledge/audit_work/C13-A4-STATUTORY/outputs/ADVISER_REVIEW_PACKET_A4.csv [packet_id=A4-ADV-084]  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q133** (COMMENCEMENT_TEMPORAL; from A4:A4-ADV-085)  
*TEMPORAL_AXIS | AFT Act 2007 / AFT Procedure Rules*  
Which date governs AFT jurisdiction and limitation questions across S.O. 14(E)/2008, the 2008 RDO, TRA 2021 (deemed 04-04-2021) and TRA 2026?  
Anchors (1): legal_knowledge/audit_work/C13-A4-STATUTORY/outputs/ADVISER_REVIEW_PACKET_A4.csv [packet_id=A4-ADV-085]  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q134** (COMMENCEMENT_TEMPORAL; from A4:A4-ADV-086)  
*TEMPORAL_AXIS | IPC 1860 -> BNS 2023*  
For an offence alleged before the BNS commencement but tried or charged after it, which date governs the applicable substantive law, given BNS s.358(2)-(3) as printed in the compilation?  
Anchors (1): legal_knowledge/audit_work/C13-A4-STATUTORY/outputs/ADVISER_REVIEW_PACKET_A4.csv [packet_id=A4-ADV-086]  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q135** (COMMENCEMENT_TEMPORAL; from A4:A4-ADV-087)  
*TEMPORAL_AXIS | CrPC 1973 -> BNSS 2023*  
For proceedings pending on, or steps taken after, the BNSS commencement, which date governs the applicable procedure, given BNSS s.531(2) as printed in the compilation?  
Anchors (1): legal_knowledge/audit_work/C13-A4-STATUTORY/outputs/ADVISER_REVIEW_PACKET_A4.csv [packet_id=A4-ADV-087]  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q136** (COMMENCEMENT_TEMPORAL; from A4:A4-ADV-088)  
*TEMPORAL_AXIS | IEA 1872 -> BSA 2023*  
For evidence produced/recorded after the BSA commencement in proceedings begun earlier, which date governs admissibility, given BSA s.170(2) as printed in the compilation?  
Anchors (1): legal_knowledge/audit_work/C13-A4-STATUTORY/outputs/ADVISER_REVIEW_PACKET_A4.csv [packet_id=A4-ADV-088]  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q138** (CROSS_REFERENCE; from A4:A4-ADV-090, A4:A4-ADV-091, A4:A4-ADV-092, A4:A4-ADV-093, A4:A4-ADV-094)  
*CROSS_REFERENCE | Army Act references to CrPC 1973 (s.137, s.139, s.151, s.174, s.152)*  
After the repeal of the CrPC 1973, how is this reference in the Army Act to be read, and is there a provision-level correspondence to the successor code? (asked identically for AA s.137, s.139, s.151, s.174, s.152)  
Anchors (5): legal_knowledge/audit_work/C13-A4-STATUTORY/outputs/ADVISER_REVIEW_PACKET_A4.csv [packet_id=A4-ADV-090]; legal_knowledge/audit_work/C13-A4-STATUTORY/outputs/ADVISER_REVIEW_PACKET_A4.csv [packet_id=A4-ADV-091]; legal_knowledge/audit_work/C13-A4-STATUTORY/outputs/ADVISER_REVIEW_PACKET_A4.csv [packet_id=A4-ADV-092]; legal_knowledge/audit_work/C13-A4-STATUTORY/outputs/ADVISER_REVIEW_PACKET_A4.csv [packet_id=A4-ADV-093]; legal_knowledge/audit_work/C13-A4-STATUTORY/outputs/ADVISER_REVIEW_PACKET_A4.csv [packet_id=A4-ADV-094]  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q139** (CROSS_REFERENCE; from A4:A4-ADV-095)  
*CROSS_REFERENCE | AA s.3 / s.69 / s.70 (civil offence; offences triable by criminal courts) -> IPC 1860*  
After the repeal of the IPC 1860, how is this reference in the Army Act to be read, and is there a provision-level correspondence to the successor code?  
Anchors (1): legal_knowledge/audit_work/C13-A4-STATUTORY/outputs/ADVISER_REVIEW_PACKET_A4.csv [packet_id=A4-ADV-095]  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q140** (FORM_TEXT; from A6:FF-AR54-APPIII-P1D-CHAR)  
*Forms | IAFD-905 (Appendix III Part I, statement as to character and particulars of service)*  
Only para 9 of IAFD-905, as substituted by S.R.O. 17(E)/1993 item 39(a) (AR-AMD-1993 p.19), is held in an official copy; the Appendix III Part I base text is not printed in the held 1954 Gazette (p.72 passes from Appendix I to Appendix III Part II). Which official instrument is to be treated as prescribing the IAFD-905 base text, and may the 14 field rows held only from MML copies be shown at all (and if so with what label) until an official copy is held (A6-ACQ-02)?  
Anchors (3): C5-SRC-P0-AR-AMD-AR-029 e9bf2114ab63 p.19; C5-SRC-P0-ARMY-RULES-1954 c5ef95a9d553 p.72  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q141** (LEGAL_INTERPRETATION; from A6:FORM_REGISTER_C13/AR-4(1))  
*Forms | Interaction of the form-prescribing rules with Army Rule 4(1)*  
The A6 register records, for each Army Rules form family listed, 'Interaction between any specific rule quoted here and AR 4(1) not determined (legal review). Competent legal review required before any template or checklist use.' How does AR 4(1) bear on the use of these forms?  
Anchors (44): legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPI-F1]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPI-F2]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPII-P1]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPII-P2]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPII-P3]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPII-P4]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPIII-AR36]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPIII-MOCERT]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPIII-P1A]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPIII-P1B]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPIII-P1C-GCMDCM]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPIII-P1D-CHAR]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPIII-P1D-SCHED]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPIII-P2]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPIII-P3A]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPIII-P3B]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPIII-P3C]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPIII-P4-DELAY]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPIII-SCM]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPIII-SGCM]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPIV-P1-F1]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPIV-P1-F2]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPIV-P2-FA]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPIV-P2-FB]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPIV-P2-FC]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPIV-P2-FD]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPIV-P2-FE]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPIV-P2-FF]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPIV-P2-FG]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPV-F1A]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPV-F1B]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPV-FH]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPV-FI]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPV-FJ]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPV-FK]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-APPV-FL]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-R109-SCM]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-R140-WITNESS]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-R45-MEMBER]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-R46A-JA]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-R46B-INSTR]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-R46C-SHW]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-R46D-INTERP]; legal_knowledge/audit_work/C13-A6-FORMS/outputs/FORM_REGISTER_C13.csv [form_id=FF-AR54-R9-ATTEST]  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

### P2 (169)

| Group | Questions | Ids |
| --- | ---: | --- |
| High Court writs vs AFT (Parashotam Dass / Shri Kant Sharma) | 2 | A8-Q003, A8-Q005 |
| Pension arrears and entitlement (Tarsem / Girish / unheld clarification / Ram Avtar / Dharamvir) | 1 | A8-Q010 |
| Own-voice overruling leads (C11 adviser queue) | 22 | A8-Q012 to A8-Q033 (all 22 in this group are P2) |
| Disputed statutory edges and commencement | 8 | A8-Q035, A8-Q037, A8-Q038, A8-Q041, A8-Q042, A8-Q048, A8-Q049, A8-Q052 |
| Authority ranking of copies (RR-04) | 2 | A8-Q053, A8-Q054 |
| Legal-approval role (PR #46 F-01) | 1 | A8-Q056 |
| PROMOTION_C12F | 57 | A8-Q058 to A8-Q114 (all 57 in this group are P2) |
| PROMOTION_C13 | 10 | A8-Q115, A8-Q116, A8-Q117, A8-Q118, A8-Q119, A8-Q120, A8-Q121, A8-Q122, A8-Q123, A8-Q124 |
| APPLICABILITY | 1 | A8-Q126 |
| RETROSPECTIVITY | 1 | A8-Q129 |
| TEMPORAL_AXIS | 1 | A8-Q137 |
| Forms | 9 | A8-Q142, A8-Q143, A8-Q144, A8-Q145, A8-Q146, A8-Q147, A8-Q148, A8-Q149, A8-Q150 |
| SC case numbers | 2 | A8-Q151, A8-Q152 |
| Relevance scope | 52 | A8-Q153 to A8-Q204 (all 52 in this group are P2) |

P2 questions are listed in full in the CSV. Selected P2 questions with source page anchors:

**A8-Q003** (STATUS_RELATION; from C12:AQ-HCW-03)  
*High Court writs vs AFT (Parashotam Dass / Shri Kant Sharma)*  
What is the scope of the last sentence of Parashotam para 32 ("However, in respect of matters of self-discipline, the principles already stand enunciated."), and must research records that state the High Court writ position carry it?  
Anchors (5): sc-2023-union-of-india-ors-2023insc265 483b70cbbe27 p.17; sc-2023-union-of-india-ors-2023insc265 483b70cbbe27 p.18; C5-SRC-J-SC-2023-PARASHOTAM fe19875b19ed p.22; hc-allahabad-2026-wria-2923-2026-uphc011159512026-1-2026-04-02 c748c1a9cb3c p.5  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q005** (DOCUMENTARY_VERIFICATION; from C12:AQ-HCW-05)  
*High Court writs vs AFT (Parashotam Dass / Shri Kant Sharma)*  
Should official copies of L. Chandra Kumar and S.R. Dhingra be re-acquired for the curated records? Both were in the crawler's SC selection but were removed as "no military keyword". L. Chandra Kumar is one of the Constitution Bench decisions named in Parashotam para 32.  
Anchors (2): sc-2023-union-of-india-ors-2023insc265 483b70cbbe27 p.17  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q010** (DOCUMENTARY_VERIFICATION; from C12:AQ-PEN-05)  
*Pension arrears and entitlement (Tarsem / Girish / unheld clarification / Ram Avtar / Dharamvir)*  
May the identity resolution be approved (Ram Avtar = SC order of 10-12-2014 in C.A. 418/2012 and connected appeals; the curated URL, which is the S P Rathore judgment, to be relabelled)? After an official copy of S P Rathore is held, may its limitation be propagated to the broad-banding records? Is Girish's "in rem" reading of Ram Avtar binding beyond broad-banding?  
Anchors (6): sc-2026-union-of-india-through-its-sec-2026insc149 da0304734666 p.11; sc-2026-union-of-india-through-its-sec-2026insc149 da0304734666 p.9; sc-2019-g-h-union-of-india-ors-2019insc1359 2f89730f3d0a p.4; sc-2019-g-h-union-of-india-ors-2019insc1359 2f89730f3d0a p.5; C5-SRC-J-SC-2026-GIRISH-FEB 4f7ea3a451c6 p.10  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q012** (STATUS_RELATION; from C12:AQ-OVR-01, A5:GT-5658e76a4b335e0d)  
*Own-voice overruling leads (C11 adviser queue)*  
Is the quoted sentence (sc-1987-ajmer-singh-etc-etc-1987insc142, p.9) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The tool proposes OVERRULES for review only; the target binding is not established.  
Anchors (3): sc-1987-ajmer-singh-etc-etc-1987insc142 b6e706e3cea4 p.9  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q013** (STATUS_RELATION; from C12:AQ-OVR-02, A5:GT-4f617d291a6063e7)  
*Own-voice overruling leads (C11 adviser queue)*  
Is the quoted sentence (sc-1996-mafatlal-industries-ltd-etc-et-1996insc1514, p.105) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The tool proposes OVERRULES for review only; the target binding is not established.  
Anchors (3): sc-1996-mafatlal-industries-ltd-etc-et-1996insc1514 d6ae2d509c6e p.105  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q014** (STATUS_RELATION; from C12:AQ-OVR-03, A5:GT-28a981e23cf66dd7)  
*Own-voice overruling leads (C11 adviser queue)*  
Is the quoted sentence (sc-1996-mafatlal-industries-ltd-etc-et-1996insc1514, p.133) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The tool proposes OVERRULES for review only; the target binding is not established.  
Anchors (3): sc-1996-mafatlal-industries-ltd-etc-et-1996insc1514 d6ae2d509c6e p.133  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q015** (STATUS_RELATION; from C12:AQ-OVR-04, A5:GT-ead10597f5f39d43)  
*Own-voice overruling leads (C11 adviser queue)*  
Is the quoted sentence (sc-1996-mafatlal-industries-ltd-etc-et-1996insc1514, p.133) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The tool proposes OVERRULES for review only; the target binding is not established.  
Anchors (3): sc-1996-mafatlal-industries-ltd-etc-et-1996insc1514 d6ae2d509c6e p.133  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q016** (STATUS_RELATION; from C12:AQ-OVR-05)  
*Own-voice overruling leads (C11 adviser queue)*  
Confirm that candidate row(s) TC-9b500dbe0d15 are noise and should be disregarded (C11 disposition V13-01), so that no treatment edge is recorded from this sentence.  
Anchors (2): sc-2000-union-of-india-and-anr-2000insc231 9edf9d95a342 p.19  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q017** (STATUS_RELATION; from C12:AQ-OVR-06)  
*Own-voice overruling leads (C11 adviser queue)*  
Confirm that candidate row(s) TC-e8e740a5df2f are noise and should be disregarded (C11 disposition V13-01), so that no treatment edge is recorded from this sentence.  
Anchors (2): sc-2014-shatrughan-chauhan-anr-2014insc46 e6c5b2e2a8c3 p.54  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q018** (STATUS_RELATION; from C12:AQ-OVR-07)  
*Own-voice overruling leads (C11 adviser queue)*  
Confirm that candidate row(s) TC-8eee72cd601c are noise and should be disregarded (C11 disposition V13-01), so that no treatment edge is recorded from this sentence.  
Anchors (2): sc-2015-supreme-court-advocates-on-rec-2015insc285 09c67ba85add p.783  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q019** (STATUS_RELATION; from C12:AQ-OVR-08)  
*Own-voice overruling leads (C11 adviser queue)*  
Confirm that candidate row(s) TC-741f5ae7f6ab are noise and should be disregarded (C11 disposition V13-01), so that no treatment edge is recorded from this sentence.  
Anchors (2): sc-2015-supreme-court-advocates-on-rec-2015insc285 09c67ba85add p.802  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q020** (STATUS_RELATION; from C12:AQ-OVR-09, A5:GT-d04ccb04c0e7e6fa)  
*Own-voice overruling leads (C11 adviser queue)*  
Is the quoted sentence (sc-2015-union-of-india-2015insc886, p.99) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The tool proposes OVERRULES for review only; the target binding is not established.  
Anchors (3): sc-2015-union-of-india-2015insc886 936a4cbfa08e p.99  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q021** (STATUS_RELATION; from C12:AQ-OVR-10, A5:GT-2c7770c7657753d3)  
*Own-voice overruling leads (C11 adviser queue)*  
Is the quoted sentence (sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801, p.167) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The tool proposes OVERRULES for review only; the target binding is not established.  
Anchors (3): sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801 447d33506394 p.167  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q022** (STATUS_RELATION; from C12:AQ-OVR-11)  
*Own-voice overruling leads (C11 adviser queue)*  
Is the quoted sentence (sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801, p.167) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The tool proposes OVERRULES for review only; the target binding is not established.  
Anchors (2): sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801 447d33506394 p.167  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q023** (STATUS_RELATION; from C12:AQ-OVR-12, A5:GT-d26cd0d0a8deb09a)  
*Own-voice overruling leads (C11 adviser queue)*  
Is the quoted sentence (sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801, p.275) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The tool proposes OVERRULES for review only; the target binding is not established.  
Anchors (3): sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801 447d33506394 p.275  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q024** (STATUS_RELATION; from C12:AQ-OVR-13, A5:GT-a1b1e75b33e03f5e)  
*Own-voice overruling leads (C11 adviser queue)*  
Is the quoted sentence (sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801, p.276) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The tool proposes OVERRULES for review only; the target binding is not established.  
Anchors (3): sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801 447d33506394 p.276  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q025** (STATUS_RELATION; from C12:AQ-OVR-14, A5:GT-60cda48a60cca1cf)  
*Own-voice overruling leads (C11 adviser queue)*  
Is the quoted sentence (sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801, p.432) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The tool proposes OVERRULES for review only; the target binding is not established.  
Anchors (3): sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801 447d33506394 p.432  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q026** (STATUS_RELATION; from C12:AQ-OVR-15)  
*Own-voice overruling leads (C11 adviser queue)*  
Is the quoted sentence (sc-2018-justice-k-s-puttaswamy-retd-2018insc880, p.705) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The sentence sits in a separate or dissenting opinion, so the tool made no proposal.  
Anchors (2): sc-2018-justice-k-s-puttaswamy-retd-2018insc880 a7adc9ef9135 p.705  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q027** (STATUS_RELATION; from C12:AQ-OVR-16)  
*Own-voice overruling leads (C11 adviser queue)*  
Is the quoted sentence (sc-2018-justice-k-s-puttaswamy-retd-2018insc880, p.820) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The sentence sits in a separate or dissenting opinion, so the tool made no proposal.  
Anchors (2): sc-2018-justice-k-s-puttaswamy-retd-2018insc880 a7adc9ef9135 p.820  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q028** (STATUS_RELATION; from C12:AQ-OVR-17)  
*Own-voice overruling leads (C11 adviser queue)*  
Is the quoted sentence (sc-2018-justice-k-s-puttaswamy-retd-2018insc880, p.1065) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The sentence sits in a separate or dissenting opinion, so the tool made no proposal.  
Anchors (2): sc-2018-justice-k-s-puttaswamy-retd-2018insc880 a7adc9ef9135 p.1065  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q029** (STATUS_RELATION; from C12:AQ-OVR-18, A5:GT-3ba9f9117abe58e3, A5:GT-4f7f5f2a23de4afc)  
*Own-voice overruling leads (C11 adviser queue)*  
Is the quoted sentence (sc-2018-joseph-shine-2018insc898, p.74) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The tool proposes OVERRULES for review only; the target binding is not established.  
Anchors (3): sc-2018-joseph-shine-2018insc898 3130322b6f53 p.74  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q030** (STATUS_RELATION; from C12:AQ-OVR-19)  
*Own-voice overruling leads (C11 adviser queue)*  
Is the quoted sentence (sc-2018-joseph-shine-2018insc898, p.100) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The sentence sits in a separate or dissenting opinion, so the tool made no proposal.  
Anchors (2): sc-2018-joseph-shine-2018insc898 3130322b6f53 p.100  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q031** (STATUS_RELATION; from C12:AQ-OVR-20)  
*Own-voice overruling leads (C11 adviser queue)*  
Is the quoted sentence (sc-2018-joseph-shine-2018insc898, p.109) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The sentence sits in a separate or dissenting opinion, so the tool made no proposal.  
Anchors (2): sc-2018-joseph-shine-2018insc898 3130322b6f53 p.109  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q032** (STATUS_RELATION; from C12:AQ-OVR-21)  
*Own-voice overruling leads (C11 adviser queue)*  
Is the quoted sentence (sc-2018-joseph-shine-2018insc898, p.154) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The sentence sits in a separate or dissenting opinion, so the tool made no proposal.  
Anchors (2): sc-2018-joseph-shine-2018insc898 3130322b6f53 p.154  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q033** (STATUS_RELATION; from C12:AQ-OVR-22)  
*Own-voice overruling leads (C11 adviser queue)*  
Is the quoted sentence (sc-2018-joseph-shine-2018insc898, p.186) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The sentence sits in a separate or dissenting opinion, so the tool made no proposal.  
Anchors (2): sc-2018-joseph-shine-2018insc898 3130322b6f53 p.186  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q035** (DOCUMENTARY_VERIFICATION; from C12:AQ-STA-02)  
*Disputed statutory edges and commencement*  
Can the adviser confirm that the earlier research statement "r.23 amended 2022" is not to be relied on, and decide what search is needed to close it?  
Anchors (1): legal_knowledge/audit_work/C12-CONSOLIDATION/adviser_package/ADVISER_QUESTIONS.csv [id=AQ-STA-02]  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q037** (DOCUMENTARY_VERIFICATION; from C12:AQ-STA-04)  
*Disputed statutory edges and commencement*  
After the June-July 1963 Gazette issues are searched: is the held S.R.O. 34 of 05-01-1963 (a r.188(e) declaration) the instrument that later notes list among amendments as "SRO 34 dated 5 Jun 63", and does that affect the amendment chain? Which date of S.R.O. 240/1955 is correct (low consequence)?  
Anchors (1): legal_knowledge/audit_work/C12-CONSOLIDATION/adviser_package/ADVISER_QUESTIONS.csv [id=AQ-STA-04]  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q038** (DOCUMENTARY_VERIFICATION; from C12:AQ-STA-05, A4:A4-ADV-081)  
*Disputed statutory edges and commencement | A4 CCCM Rules amendment S.O. 4010 (1986)*  
Which date is that of the 1986 MHA notification S.O. 4010 amending the Criminal Courts and Court-Martial (Adjustment of Jurisdiction) Rules 1978? (Owner decision after a page check of the record copy.)  
Anchors (3): C5-SRC-P2-RS-PAPERS-LAID-1987 fa51a4b132c4 page not stated  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q041** (COMMENCEMENT_TEMPORAL; from C12:AQ-STA-08)  
*Disputed statutory edges and commencement*  
How do the AFT Act s.1(2) commencement (compilation footnote: 15-06-2008 by S.O. 14(E) of 13-06-2008, notification not held) and the establishment of the Tribunal w.e.f. 10-08-2009 (S.R.O. 9(E) of 07-08-2009, held) relate?  
Anchors (1): legal_knowledge/audit_work/C12-CONSOLIDATION/adviser_package/ADVISER_QUESTIONS.csv [id=AQ-STA-08]  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q042** (COMMENCEMENT_TEMPORAL; from C12:AQ-STA-09)  
*Disputed statutory edges and commencement*  
May the AFT Procedure Rules 2008, Amendment Rules 2011 and Practice Rules 2009 (held, unregistered) be registered, and on what evidence is the Practice Rules 2009 commencement ("from the date of publication in the official gazette") to be fixed, given that the publication date is not on the held pages?  
Anchors (1): legal_knowledge/audit_work/C12-CONSOLIDATION/adviser_package/ADVISER_QUESTIONS.csv [id=AQ-STA-09]  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q048** (DOCUMENTARY_VERIFICATION; from C12:AQ-STA-17)  
*Disputed statutory edges and commencement*  
Which instrument was the last amendment of the Army Rules before S.R.O. 17(E)/2019? (Documentary; owner decision.)  
Anchors (1): legal_knowledge/audit_work/C12-CONSOLIDATION/adviser_package/ADVISER_QUESTIONS.csv [id=AQ-STA-17]  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q049** (COMMENCEMENT_TEMPORAL; from C12:AQ-STA-18)  
*Disputed statutory edges and commencement*  
From what dates do the Commanders-in-Chief (Change in Designation) Act 1955 (commencement by notification) and the Air Force and Army Laws (Amendment) Act 1975 (no commencement section; s.4(2) saving refers to 25-01-1975) take effect for the Army Act provisions they changed?  
Anchors (1): legal_knowledge/audit_work/C12-CONSOLIDATION/adviser_package/ADVISER_QUESTIONS.csv [id=AQ-STA-18]  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q052** (LEGAL_INTERPRETATION; from C12:AQ-STA-21)  
*Disputed statutory edges and commencement*  
May "explicitly directs complaint to next superior" in ADM-022 be replaced by the permissive statutory wording (C9-CP-C01, superseding E8-CP-08)? The adviser need only confirm the wording.  
Anchors (2): act-army-1950 e47a4265813e p.16  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q053** (SOURCE_AUTHORITY; from C12:AQ-AUT-01)  
*Authority ranking of copies (RR-04)*  
Is the authority-matrix order correct that places open-data bulk copies of Supreme Court judgments (tier 4: e.g. the AWS S3 buckets that supplied all 346 data/raw/sci and 3,605 data/raw/hc files) above law-report renditions including SCR (tier 5), under a heading that says a lower tier never overrides a higher one on content, and that keeps bulk copies at tier 2 for High Courts? If not settled, should the order be marked "not settled pending legal-side review"?  
Anchors (1): legal_knowledge/audit_work/C12-CONSOLIDATION/adviser_package/ADVISER_QUESTIONS.csv [id=AQ-AUT-01]  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q054** (SOURCE_AUTHORITY; from C12:AQ-AUT-02)  
*Authority ranking of copies (RR-04)*  
May the raw-store SCR-format copies (AWS mirror of e-SCR) be registered as reported-version comparators (AP-C9-02), and may e-SCR report pages be cited as locators? They are not signed court originals.  
Anchors (2): sc-2023-union-of-india-ors-2023insc265 483b70cbbe27 p.17  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q056** (ROLE_PROCESS; from C12:AQ-ROL-02)  
*Legal-approval role (PR #46 F-01)*  
Who decides that new material is "credible" enough to mark an affected scope REVALIDATION_REQUIRED/BLOCKED, and who may re-enable it? Is the Vision's "Legal review workspace" Admin-operated, or deferred?  
Anchors (1): legal_knowledge/audit_work/C12-CONSOLIDATION/adviser_package/ADVISER_QUESTIONS.csv [id=AQ-ROL-02]  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q126** (LEGAL_INTERPRETATION; from A4:A4-ADV-074)  
*APPLICABILITY | Army Rule 15B (S.R.O. 17(E)/2019) disapplying rr.14, 15, 15A for the office of the Chief of Defence Staff*  
From 28-12-2019, how does r.15B limit the application of rr.14, 15 and 15A, given that the AR-034 copy is not registered as eligible?  
Anchors (2): C5-SRC-P0-AR-AMD-AR-034 138c1da0d3d9 page not stated  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q129** (COMMENCEMENT_TEMPORAL; from A4:A4-ADV-078)  
*RETROSPECTIVITY | Retrospective deemed omission by S.R.O. 216/1988 (r.2 clauses and r.16A Explanation deemed from 04-06-1979)*  
What is the legal effect of the deemed retrospective operation for the period 04-06-1979 to 17-09-1988?  
Anchors (2): C5-SRC-P0-AR-AMD-AR-024 1d67bddd3720 page not stated  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q137** (COMMENCEMENT_TEMPORAL; from A4:A4-ADV-089)  
*TEMPORAL_AXIS | Regulations, pension instruments, CCCM, ISO Act*  
These instruments are not held and are modelled only at instrument level: which date (event, claim, decision or review) governs the applicable edition?  
Anchors (1): legal_knowledge/audit_work/C13-A4-STATUTORY/outputs/ADVISER_REVIEW_PACKET_A4.csv [packet_id=A4-ADV-089]  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

**A8-Q142** (FORM_TEXT; from A6:FF-AR54-APPIII-P3C)  
*Forms | Summons to witnesses (c): designation IAFD-919C vs IAFD-919A*  
The S.R.O. 17(E)/1993 printing of summons form (c) reads 'IAFD-919C'; MML 2 p.303 shows 'IAFD 919 C' at the heading and 'IAFD-919A' after the signature block. Which designation is the prescribed one?  
Anchors (3): C5-SRC-P0-AR-AMD-AR-029 e9bf2114ab63 p.19; C5-SRC-P2-MML-MML-2-PDF db2119182ed2 p.303  
Status: NOT LEGALLY REVIEWED; adviser answer: AWAITING_ADVISER

## 5. Limits

- AI readings only; no human has confirmed any page reading or excerpt in this package.
- A8 phrased the A6, A5 case-number and A1 relevance questions from what those artefacts record as open. All other question text is verbatim from the originating artefact.
- Some anchors carry no page because the originating artefact gives none (`NOT_STATED_IN_SOURCE`); they are listed so the adviser can see which copy the question concerns.
- The C12 package's excerpt checks are not repeated here; see `C12-CONSOLIDATION/adviser_package/EXCERPT_VERIFICATION.csv`.

Built by `tools/build_adviser_c13.py` (C13-A8-v1); validated by `tools/validate_adviser_c13.py`.
