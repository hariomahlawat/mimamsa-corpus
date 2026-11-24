# Legal-adviser review package, Cycle 12 (Mimamsa)

**PREPARED BY AUTOMATED AGENTS. TECHNICAL AND DOCUMENTARY REVIEW ONLY. NO LEGAL VALIDATION.** Nothing in this package is a legal conclusion, a status change or an approval. Every reading of a source page was made by an AI agent from a text layer and is not human-confirmed. Questions are for a qualified legal adviser (or JAG, where the controlling policy requires it).

Built by `tools/build_adviser_package.py` from existing artefacts only (see `PROVENANCE_C12.md`). No source file was modified; no record, register, edge or status was changed.

## 1. How to use this package

- **What it is.** One register of every open question that earlier cycles (C9, C10, C11) and the PR #46 review escalated to the legal side, with the source wording and exact pinpoints, the readings already recorded in the artefacts, the research records affected, and the evidence still missing. It answers none of the questions.
- **Where to start.** Section 2 lists every question with its priority. P0 and P1 mark the items the source artefacts treat as most consequential. Each question in sections 3-8 has the same parts: question, sources, excerpts with pinpoints, competing readings, affected records, missing evidence.
- **Pinpoints.** `p.` is the PDF page of the text layer at raw-data commit `ad77758d` of `/home/user/c7` (`data/text/<doc_id>.txt`, `[[page N]]` markers). Many Supreme Court copies there are SCR renditions from the AWS e-SCR mirror, not signed court originals; their page numbers can differ from the official copy (for example Parashotam para 32 is SCR p.17 but official p.22). `para` is the printed paragraph number. Copies named `official copy wt:<sha>` are in the C5 working store and are not in the text layer.
- **Excerpt checks.** Every quoted excerpt was re-checked by this build, whitespace-insensitive and verbatim, on the stated page of the `ad77758d` text file where one exists. Results are shown next to each excerpt and in `EXCERPT_VERIFICATION.csv`. Excerpts from copies that are not in the text layer are marked "not re-verifiable here" and carry the earlier cycle's check.
- **Verification summary.** 77 excerpts: NO_TEXT_FILE_AT_ad77758d 7, VERIFIED_ON_STATED_PAGE 70.
- **Voice.** Excerpts are labelled COURT_VOICE (the court's own words), LATER_RELIANCE (a later court's words), EDITORIAL (reporter matter; never the court's treatment), BENCH, STATUTE_COMPILATION (India Code compilation; a compiler's "w.e.f." note is a compiler statement only) or STATUTE_GAZETTE.
- **Priorities.** Where the source artefact states a priority (C9 binding scale: P0 r.23(3); P1 Tarsem/Girish, Parashotam, s.133) it is carried. Otherwise the priority is a triage order for sequencing only. The adviser sets the final priority.
- **Known noise.** Four of the 30 C11 adviser rows are known noise (C11 disposition V13-01): TC-9b500dbe0d15 (C.S. Gill p.19), TC-e8e740a5df2f (Shatrughan Chauhan p.54), TC-8eee72cd601c and TC-741f5ae7f6ab (SCAORA). They are kept and marked **DISREGARD (V13-01)**, so the adviser can confirm the withdrawal.
- **Recording a decision.** Record each answer against its question id, outside this package (a decision record or the AUTH-LEDGER process). Applying any decision is a separate reviewed change with owner approval. This package is not edited to record decisions.

## 2. Question register

| Topic | Questions |
| --- | --- |
| High Court writs vs AFT (Parashotam Dass / Shri Kant Sharma) | 5 |
| Pension arrears and entitlement (Tarsem / Girish / unheld clarification / Ram Avtar / Dharamvir) | 6 |
| Own-voice overruling leads (C11 adviser queue) | 22 |
| Disputed statutory edges and commencement | 21 |
| Authority ranking of copies (RR-04) | 2 |
| Legal-approval role (PR #46 F-01) | 3 |
| **Total** | **59** |

| Id | Priority | Topic | Question (short) |
| --- | --- | --- | --- |
| AQ-HCW-01 | P1 | High Court writs vs AFT | Typed relation from Parashotam Dass to Shri Kant Sharma |
| AQ-HCW-02 | P1 | High Court writs vs AFT | Which limbs of Shri Kant Sharma survive Parashotam para 32 |
| AQ-HCW-03 | P2 | High Court writs vs AFT | Scope of the "self-discipline" reservation in Parashotam para 32 |
| AQ-HCW-04 | P1 | High Court writs vs AFT | Research records on the High Court writ route; pinpoint and holding corrections |
| AQ-HCW-05 | P3 | High Court writs vs AFT | Re-acquire L. Chandra Kumar and S.R. Dhingra |
| AQ-PEN-01 | P1 | Pension arrears and entitlement | Does Tarsem's three-year arrears limit survive outside Girish's grounds |
| AQ-PEN-02 | P1 | Pension arrears and entitlement | Relation type Girish -> Tarsem and the C9 warning wording |
| AQ-PEN-03 | P1 | Pension arrears and entitlement | The unheld 12-10-2026 "clarification" of Girish Kumar |
| AQ-PEN-04 | P1 | Pension arrears and entitlement | Is Girish a "case-specific arrears award"? |
| AQ-PEN-05 | P2 | Pension arrears and entitlement | Ram Avtar identity, the S P Rathore limitation and the reach of "in rem" |
| AQ-PEN-06 | P2 | Pension arrears and entitlement | Dharamvir (1982 Rules) and N C Isaac (2008 Rules) |
| AQ-OVR-01 | P3 | Own-voice overruling leads | sc-1987-ajmer-singh-etc-etc-1987insc142 p.9: "do not lay down the correct law" |
| AQ-OVR-02 | P3 | Own-voice overruling leads | sc-1996-mafatlal-industries-ltd-etc-et-1996insc1514 p.105: "must be held to have been decided wrongly" |
| AQ-OVR-03 | P3 | Own-voice overruling leads | sc-1996-mafatlal-industries-ltd-etc-et-1996insc1514 p.133: "have also been wrongly decided" |
| AQ-OVR-04 | P3 | Own-voice overruling leads | sc-1996-mafatlal-industries-ltd-etc-et-1996insc1514 p.133: "wrongly decided" |
| AQ-OVR-05 | P3 (disregard pending withdrawal) | Own-voice overruling leads | sc-2000-union-of-india-and-anr-2000insc231 p.19: "is overruled" |
| AQ-OVR-06 | P3 (disregard pending withdrawal) | Own-voice overruling leads | sc-2014-shatrughan-chauhan-anr-2014insc46 p.54: "stands overruled" |
| AQ-OVR-07 | P3 (disregard pending withdrawal) | Own-voice overruling leads | sc-2015-supreme-court-advocates-on-rec-2015insc285 p.783: "stand overruled" |
| AQ-OVR-08 | P3 (disregard pending withdrawal) | Own-voice overruling leads | sc-2015-supreme-court-advocates-on-rec-2015insc285 p.802: "does not lay down the correct law" |
| AQ-OVR-09 | P3 | Own-voice overruling leads | sc-2015-union-of-india-2015insc886 p.99: "overrule" |
| AQ-OVR-10 | P3 | Own-voice overruling leads | sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801 p.167: "We also overrule" |
| AQ-OVR-11 | P3 | Own-voice overruling leads | sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801 p.167: "must be and is accordingly overruled" |
| AQ-OVR-12 | P3 | Own-voice overruling leads | sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801 p.275: "is overruled" |
| AQ-OVR-13 | P3 | Own-voice overruling leads | sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801 p.276: "is overruled" |
| AQ-OVR-14 | P3 | Own-voice overruling leads | sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801 p.432: "stands over-ruled" |
| AQ-OVR-15 | P3 | Own-voice overruling leads | sc-2018-justice-k-s-puttaswamy-retd-2018insc880 p.705: "does not lay down the correct law" |
| AQ-OVR-16 | P3 | Own-voice overruling leads | sc-2018-justice-k-s-puttaswamy-retd-2018insc880 p.820: "are overruled" |
| AQ-OVR-17 | P3 | Own-voice overruling leads | sc-2018-justice-k-s-puttaswamy-retd-2018insc880 p.1065: "are accordingly overruled" |
| AQ-OVR-18 | P3 | Own-voice overruling leads | sc-2018-joseph-shine-2018insc898 p.74: "stand overruled" |
| AQ-OVR-19 | P3 | Own-voice overruling leads | sc-2018-joseph-shine-2018insc898 p.100: "we overrule" |
| AQ-OVR-20 | P3 | Own-voice overruling leads | sc-2018-joseph-shine-2018insc898 p.109: "is overruled" |
| AQ-OVR-21 | P3 | Own-voice overruling leads | sc-2018-joseph-shine-2018insc898 p.154: "are overruled" |
| AQ-OVR-22 | P3 | Own-voice overruling leads | sc-2018-joseph-shine-2018insc898 p.186: "hereby stand overruled" |
| AQ-STA-01 | P0 | Disputed statutory edges and commencement | Army Rule 23(3) caution wording |
| AQ-STA-02 | P2 | Disputed statutory edges and commencement | Unsupported statement that r.23 was amended in 2022 |
| AQ-STA-03 | P2 | Disputed statutory edges and commencement | Army Rule 168(2) field-punishment words |
| AQ-STA-04 | P3 | Disputed statutory edges and commencement | S.R.O. 34 of 1963 identity and the S.R.O. 240/1955 date |
| AQ-STA-05 | P3 | Disputed statutory edges and commencement | S.O. 4010/1986 (CCCM Rules amendment) date |
| AQ-STA-06 | P1 | Disputed statutory edges and commencement | Commencement of Army (Amendment) Act 37 of 1992 |
| AQ-STA-07 | P1 | Disputed statutory edges and commencement | Army Act ss.122-123 limitation (CM-011, CM-012) |
| AQ-STA-08 | P2 | Disputed statutory edges and commencement | AFT Act commencement vs establishment of the Tribunal |
| AQ-STA-09 | P3 | Disputed statutory edges and commencement | AFT procedural rules commencement |
| AQ-STA-10 | P2 | Disputed statutory edges and commencement | AFT s.9A under the Finance Act 2017 and the Tribunals Reforms Act 2026 |
| AQ-STA-11 | P2 | Disputed statutory edges and commencement | Army Rules amending instruments with no commencement clause (AQ-05) |
| AQ-STA-12 | P2 | Disputed statutory edges and commencement | Army Rule 182 as substituted by S.R.O. 17(E)/1993 item 36 |
| AQ-STA-13 | P3 | Disputed statutory edges and commencement | Army Rule 192 proviso (reduction in pay grade) |
| AQ-STA-14 | P3 | Disputed statutory edges and commencement | Army Rule 177(1)-(2) (Court of Inquiry) |
| AQ-STA-15 | P2 | Disputed statutory edges and commencement | Army Rule 193 (prescribed officer, AA s.90(i) and s.91(i)) |
| AQ-STA-16 | P2 | Disputed statutory edges and commencement | Army Rule 194 (prescribed officer, AA s.93) |
| AQ-STA-17 | P3 | Disputed statutory edges and commencement | Last amendment before S.R.O. 17(E)/2019 (footnote discrepancy) |
| AQ-STA-18 | P3 | Disputed statutory edges and commencement | Commencement of Acts 19 of 1955 and 13 of 1975 (Army Act amendments) |
| AQ-STA-19 | P1 | Disputed statutory edges and commencement | IPC, CrPC and Evidence Act repeal by BNS, BNSS and BSA: commencement evidence and references in military law |
| AQ-STA-20 | P1 | Disputed statutory edges and commencement | Army Act s.133 and the Bharatiya Sakshya Adhiniyam 2023 |
| AQ-STA-21 | P2 | Disputed statutory edges and commencement | ADM-022 and Army Act s.26(2) (wording confirmation) |
| AQ-AUT-01 | P2 | Authority ranking of copies | Relative order of open-data bulk copies and law-report (SCR) renditions |
| AQ-AUT-02 | P2 | Authority ranking of copies | SCR-format renditions as comparators and locators |
| AQ-ROL-01 | P1 | Legal-approval role | Approval tier and channel for operational use |
| AQ-ROL-02 | P2 | Legal-approval role | Who decides "credible material" and who re-enables a blocked scope |
| AQ-ROL-03 | P1 | Legal-approval role | Who reviews proposed supersession and overruling edges, and who confirms AI page readings |

## 3. High Court writs vs AFT (Parashotam Dass / Shri Kant Sharma)

Affected-record basis: C11 `AFFECTED_RESEARCH_RECORDS.csv` (13 Parashotam rows, 2 Shri Kant Sharma rows; status PROPOSAL_NOT_APPLIED_ADVISER_REVIEW).

### AQ-HCW-01: Typed relation from Parashotam Dass to Shri Kant Sharma

**Priority:** P1. **Origin:** C9 ESC-06 (P1); C10 ESC-C10-03; C11 TC-222df5c885ad.

**Question.** Which typed relation, if any, should the corpus record from Union of India v Parashotam Dass (2023 INSC 265, three Judges) to Union of India v Maj Gen Shri Kant Sharma ((2015) 6 SCC 773, two Judges): overrules / overruled_by, "declared not good law", "disapproved", or another label?

**Sources.**
- C11 TREATMENT_CANDIDATES.csv TC-222df5c885ad (only BOUND row of the 30; proposed OVERRULES at LEGAL_INTERPRETATION_ADVISER_REVIEW)
- C11 PRIORITY_TREATMENT_DOSSIER.md, sections "Union of India v. Major General Shri Kant Sharma" and "Union of India v. Parashotam Dass"
- C10 JUDICIAL_TREATMENT_C10.csv R-SHRIKANT-T1 (classification OVERRULED in documentary wording), P-SHRIKANT
- C10 ADVISER_ESCALATIONS_C10.csv ESC-C10-03 (second sentence)
- C9 LEGAL_ADVISER_ESCALATION.md ESC-06 (a)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| LEAD-TC-222df5c885ad | sc-2023-union-of-india-ors-2023insc265 p.17, para 32 | COURT_VOICE_OR_OPINION | "in concluding that the judgment in Major General Shri Kant Sharma & Anr.24 case does not lay down the correct law and is in conflict with judgments of the Constitution Bench" | verified (stated page) |
| RD-PARASHOTAM-T1 | sc-2023-union-of-india-ors-2023insc265 p.17, para 32 | COURT_VOICE | "We have, thus, no hesitation in concluding that the judgment in" | verified (stated page) |
| RD-PARASHOTAM-T2 | sc-2023-union-of-india-ors-2023insc265 p.17, para 32 | COURT_VOICE | "Shri Kant Sharma & Anr.24 case does not lay down the correct law and is in conflict with judgments of the Constitution" ('24' is a footnote marker; the word 'overruled' is not used) | verified (stated page) |
| C12-PARASHOTAM-LCK | sc-2023-union-of-india-ors-2023insc265 p.17, para 32 | COURT_VOICE | "including in L. Chandra Kumar25 case, S.N. Mukherjee26 case, and Rojer Mathew27 case making it abundantly clear that there is no per se restriction on the exercise of" | verified (stated page) |
| RD-PARASHOTAM-T3 | sc-2023-union-of-india-ors-2023insc265 p.18, para 32 | COURT_VOICE | "power under Article 226 of the Constitution by the High Court. However, in respect of matters of self-discipline, the principles already stand enunciated." | verified (stated page) |
| RD-PARASHOTAM-ED | sc-2023-union-of-india-ors-2023insc265 p.4 | EDITORIAL | "& Anr. (2015) 6 SCC 773 : [2015] 4 SCR 676 – held not correct law." (reporter case-law entry; never the court's treatment) | verified (stated page) |
| RD-PARASHOTAM-BENCH | sc-2023-union-of-india-ors-2023insc265 p.1 | BENCH | "[SANJAY KISHAN KAUL, B. V. NAGARATHNA AND ABHAY S. OKA, JJ.]" | verified (stated page) |
| RD-SHRIKANT-BENCH | sc-2015-union-of-india-ors-2015insc206 p.1 | BENCH | "[SUDHANSU JYOTI MUKHOPADHAYA AND" (two-Judge Bench (with N.V. Ramana J., next line)) | verified (stated page) |
| R-PARASH-H1 | official copy wt:fe19875b p.22, para 32 | COURT_VOICE | "case does not lay down the correct law and is in conflict with judgments of the Constitution Benches" (official SC copy in the C5 working store; not in the text layer) | not re-verifiable here (no text file at ad77758d; carried from C10 JUDICIAL_TREATMENT_C10.csv (quote_check VERBATIM_FOUND)); same words found in the SCR rendition (sc-2023-union-of-india-ors-2023insc265 p.1,4,17); such hits can include reporter headnote pages, which are not court voice |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) overrules / overruled_by: explicit wording "does not lay down the correct law" by a three-Judge Bench against a two-Judge decision (C10 R-SHRIKANT-T1 classifies it OVERRULED in documentary wording; C11 tool proposes OVERRULES for review only).
- (b) "declared not good law" / "disapproved": the word "overruled" is not used in para 32 (C11 dossier; WS-B label WSB-T-004 cited by C9 ESC-06).
- The reporter case-law entry ("held not correct law", p.4) is editorial matter and is not evidence of the court's treatment.

**Affected research records.** KB-025; KB-028; AFT-001; AFT-033; AFT-035; AFT-036; AFT-039; AFT-044; V7-WF-08; V7-SC-18; V7-CL-10; V7-JD-02; V7-JD-03; DCLR-SC-2023-009; DCLR-SC-2015-N06

**Evidence still missing.**
- Human confirmation of the AI readings (P-B / B2 in the C9 decision matrix).
- The official-copy locator (wt:fe19875b p.22) was read in C10 but not re-read in C11; it is outside the ad77758d text layer.
- No signed or official copy of Shri Kant Sharma is held (SCR rendition only).

### AQ-HCW-02: Which limbs of Shri Kant Sharma survive Parashotam para 32

**Priority:** P1. **Origin:** C10 ESC-C10-03; C9 ESC-06.

**Question.** Does any limb of Shri Kant Sharma survive Parashotam para 32, in particular the alternative-remedy guidance in para 34(iii)-(iv), given that the J&K High Court relied on Shri Kant Sharma on 06-10-2025 without citing Parashotam?

**Sources.**
- C11 dossier, Shri Kant Sharma "Open questions and uncertainty"
- C10 ESC-C10-03 (first sentence)
- C10 R-SHRIKANT-H1, R-SHRIKANT-T2
- C11 AFFECTED_RESEARCH_RECORDS.csv rows for "Shri Kant Sharma"

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| RD-SHRIKANT-H3 | sc-2015-union-of-india-ors-2015insc206 p.33, para 25 | COURT_VOICE | "judicial review vested in the High Court under Article 226 is one of the basic essential features of theConstitution" | verified (stated page) |
| RD-SHRIKANT-H1 | sc-2015-union-of-india-ors-2015insc206 p.47, para 34(iv) | COURT_VOICE | "226 of the Constitution if an effective alternative remedy is available to the aggrieved person or the statute" (same words also occur on p.44 inside a quotation of an earlier judgment) | verified (stated page) |
| RD-SHRIKANT-H2 | sc-2015-union-of-india-ors-2015insc206 p.49, para 38 | COURT_VOICE | "we are of the view that Delhi High Court was not" (continues: 'justified in entertaining the petition under Article 226') | verified (stated page) |
| RD-PARASHOTAM-T2 | sc-2023-union-of-india-ors-2023insc265 p.17, para 32 | COURT_VOICE | "Shri Kant Sharma & Anr.24 case does not lay down the correct law and is in conflict with judgments of the Constitution" ('24' is a footnote marker; the word 'overruled' is not used) | verified (stated page) |
| C12-PARASHOTAM-LCK | sc-2023-union-of-india-ors-2023insc265 p.17, para 32 | COURT_VOICE | "including in L. Chandra Kumar25 case, S.N. Mukherjee26 case, and Rojer Mathew27 case making it abundantly clear that there is no per se restriction on the exercise of" | verified (stated page) |
| RD-PARASHOTAM-T3 | sc-2023-union-of-india-ors-2023insc265 p.18, para 32 | COURT_VOICE | "power under Article 226 of the Constitution by the High Court. However, in respect of matters of self-discipline, the principles already stand enunciated." | verified (stated page) |
| RD-JKHC-SKS | hc-jkl-2025-wp-c-2370-2025-jkhc010050362025-1-2025-10-06 p.2, para 6 | LATER_RELIANCE | "Since the Apex Court in case titled as “Union of India vs. Shri Kant Sharma (2015) 6 SCC 773 has specifically provided that High Court" (J&K HC 06-10-2025; Parashotam not cited in this order) | verified (stated page) |
| RD-JKHC-SKS2 | hc-jkl-2025-wp-c-2370-2025-jkhc010050362025-1-2025-10-06 p.3, para 6 | LATER_RELIANCE | "should refrain from entertaining petitions under Article 226 if alternative or effective remedy is available" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Parashotam rejects the proposition in paras 37-38 (that the High Court should not entertain writs against AFT orders); paras 34(i)-(ii) (Art. 226 a basic feature; due regard to legislative intent) are consistent with Parashotam (C11 dossier).
- (b) Whether para 34(iii)-(iv) (alternative remedy) survives as a discretionary rule is recorded as open (C11 dossier; C10 ESC-C10-03).
- Later practice preserved as found: J&K HC WP(C) 2370/2025 (06-10-2025) relies on Shri Kant Sharma for the alternative-remedy point; the order concerned an original petition, not a writ against an AFT order (C11 dossier note).

**Affected research records.** AFT-035; V7-JD-02

**Evidence still missing.**
- Whether the J&K HC order of 06-10-2025 was appealed or later considered (not searched).
- Human confirmation of the AI readings; official copy of Shri Kant Sharma.

### AQ-HCW-03: Scope of the "self-discipline" reservation in Parashotam para 32

**Priority:** P2. **Origin:** C11 AFFECTED_RESEARCH_RECORDS.csv; C11 dossier.

**Question.** What is the scope of the last sentence of Parashotam para 32 ("However, in respect of matters of self-discipline, the principles already stand enunciated."), and must research records that state the High Court writ position carry it?

**Sources.**
- C11 dossier, Parashotam "Open questions and uncertainty" (scope not defined in the paragraph)
- C11 AFFECTED_RESEARCH_RECORDS.csv (13 Parashotam rows; proposed_action asks about the self-discipline reservation)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| RD-PARASHOTAM-T3 | sc-2023-union-of-india-ors-2023insc265 p.18, para 32 | COURT_VOICE | "power under Article 226 of the Constitution by the High Court. However, in respect of matters of self-discipline, the principles already stand enunciated." | verified (stated page) |
| C12-PARASHOTAM-LCK | sc-2023-union-of-india-ors-2023insc265 p.17, para 32 | COURT_VOICE | "including in L. Chandra Kumar25 case, S.N. Mukherjee26 case, and Rojer Mathew27 case making it abundantly clear that there is no per se restriction on the exercise of" | verified (stated page) |
| R-PARASH-H2 | official copy wt:fe19875b p.22, para 32 | COURT_VOICE | "there is no per se restriction on the exercise of power under Article 226 of the Constitution by the High Court" (in the SCR rendition the court-voice sentence runs from p.17 to p.18 with footnotes and margin letters between (C12-PARASHOTAM-LCK, RD-PARASHOTAM-T3)) | not re-verifiable here (no text file at ad77758d; carried from C10 JUDICIAL_TREATMENT_C10.csv (quote_check VERBATIM_FOUND)); same words found in the SCR rendition (sc-2023-union-of-india-ors-2023insc265 p.4); such hits can include reporter headnote pages, which are not court voice |
| R-PARASH-T2 | hc-allahabad-2026-wria-2923-2026-uphc011159512026-1-2026-04-02 p.5, para 18 | LATER_RELIANCE | "in the case of Parashotam Dass (Supra), the only issue before the Hon'ble Supreme Court was maintainability of writ petition" (territorial-jurisdiction question; Parashotam held inapplicable by the HC) | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- No competing readings of the reservation are recorded in the artefacts. The artefacts record only that the paragraph does not define its scope (C11 dossier).
- Related later treatment: Allahabad HC WRIA 2923/2026 treats Parashotam as deciding only maintainability of a writ petition (R-PARASH-T2), on a territorial-jurisdiction question.

**Affected research records.** KB-025; KB-028; AFT-001; AFT-033; AFT-035; AFT-036; AFT-039; AFT-044; V7-WF-08; V7-SC-18; V7-CL-10; V7-JD-02; V7-JD-03

**Evidence still missing.**
- Any held judgment construing the reservation (not searched for in C10/C11).
- Human confirmation of the readings.

### AQ-HCW-04: Research records on the High Court writ route; pinpoint and holding corrections

**Priority:** P1. **Origin:** C9 ESC-06 (b); C11 AFFECTED_RESEARCH_RECORDS.csv.

**Question.** Do the 13 research records that depend on Parashotam state the High Court writ position correctly in the light of para 32, and may the C9 pinpoint and holding corrections (F-JUD-017; C9-CP-E01 to E06) be applied?

**Sources.**
- C11 AFFECTED_RESEARCH_RECORDS.csv (Parashotam: 13 rows)
- C9 LEGAL_ADVISER_ESCALATION.md ESC-06 (b) and "What the corpus says now"
- C9 LEGAL_ADVISER_ESCALATION.md Part 3 (C9-CP-E03, E05, E06)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| RD-PARASHOTAM-T2 | sc-2023-union-of-india-ors-2023insc265 p.17, para 32 | COURT_VOICE | "Shri Kant Sharma & Anr.24 case does not lay down the correct law and is in conflict with judgments of the Constitution" ('24' is a footnote marker; the word 'overruled' is not used) | verified (stated page) |
| RD-PARASHOTAM-T3 | sc-2023-union-of-india-ors-2023insc265 p.18, para 32 | COURT_VOICE | "power under Article 226 of the Constitution by the High Court. However, in respect of matters of self-discipline, the principles already stand enunciated." | verified (stated page) |
| R-PARASH-H1 | official copy wt:fe19875b p.22, para 32 | COURT_VOICE | "case does not lay down the correct law and is in conflict with judgments of the Constitution Benches" (official SC copy in the C5 working store; not in the text layer) | not re-verifiable here (no text file at ad77758d; carried from C10 JUDICIAL_TREATMENT_C10.csv (quote_check VERBATIM_FOUND)); same words found in the SCR rendition (sc-2023-union-of-india-ors-2023insc265 p.1,4,17); such hits can include reporter headnote pages, which are not court voice |
| R-PARASH-T1 | sc-2023-union-of-india-ors-2023insc1074 p.16, para (SCR p.1041) | LATER_RELIANCE | "This position stood restated, recently, in Union of India v Parashotam Dass" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- C9 records: DCLR-SC-2023-009 pinpoint "11-16" points into the private parties' submissions; its holding omits the para 32 ratio; its scope_and_caveats says the official PDF was not retrieved although it is held; KB-025 cites para 18 (Union's pleas); KB-028 omits para 32; V7-JD-02 and AFT-035 already caveat the treatment.
- C9 classification: pinpoints are incorrect citations (documentary); the holding is incomplete, not wrong; the relation type is a characterisation reserved for a human.

**Affected research records.** KB-025; KB-028; AFT-001; AFT-033; AFT-035; AFT-036; AFT-039; AFT-044; V7-WF-08; V7-SC-18; V7-CL-10; V7-JD-02; V7-JD-03; DCLR-SC-2023-009; DCLR-SC-2015-N06

**Evidence still missing.**
- Adviser decision on AQ-HCW-01 (relation type) before the wording can be finalised.

### AQ-HCW-05: Re-acquire L. Chandra Kumar and S.R. Dhingra

**Priority:** P3. **Origin:** C10 ESC-C10-06.

**Question.** Should official copies of L. Chandra Kumar and S.R. Dhingra be re-acquired for the curated records? Both were in the crawler's SC selection but were removed as "no military keyword". L. Chandra Kumar is one of the Constitution Bench decisions named in Parashotam para 32.

**Sources.**
- C10 ADVISER_ESCALATIONS_C10.csv ESC-C10-06
- WS-B identity statuses CITATION_METADATA_CORROBORATED_BY_OFFICIAL_RECORD_NO_COPY / UNRESOLVED_NO_COPY_IN_HAND (as cited by ESC-C10-06)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| C12-PARASHOTAM-LCK | sc-2023-union-of-india-ors-2023insc265 p.17, para 32 | COURT_VOICE | "including in L. Chandra Kumar25 case, S.N. Mukherjee26 case, and Rojer Mathew27 case making it abundantly clear that there is no per se restriction on the exercise of" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- No competing readings: this is an acquisition decision. Under CLAUDE.md any real download run needs approval first.

**Affected research records.** (curated records for L. Chandra Kumar and S.R. Dhingra; ids not listed in ESC-C10-06)

**Evidence still missing.**
- Copies of both judgments; approval for a download run.

## 4. Pension arrears and entitlement (Tarsem / Girish / unheld clarification / Ram Avtar / Dharamvir)

Affected-record basis: C11 `AFFECTED_RESEARCH_RECORDS.csv` (Tarsem 6, Girish 9, Ram Avtar 4, Dharamvir 3 rows). The 12-10-2026 clarification order is NOT HELD and NOT CITED in any held judgment: its content is unknown.

### AQ-PEN-01: Does Tarsem's three-year arrears limit survive outside Girish's grounds

**Priority:** P1. **Origin:** C9 ESC-01 (P1); C10 ESC-C10-01.

**Question.** After Union of India v Sgt Girish Kumar (2026 INSC 149) para 22, may the AFT and High Courts still restrict arrears to three years under Union of India v Tarsem Singh ((2008) 8 SCC 648) for claims outside Girish's two grounds (for example initial-grant rather than re-computation disability-pension claims)?

**Sources.**
- C11 dossier, Tarsem and Girish sections
- C10 ESC-C10-01; JUDICIAL_TREATMENT_C10.csv R-TARSEM-*, R-GIRISH-*
- C9 LEGAL_ADVISER_ESCALATION.md ESC-01 (a)
- C11 TREATMENT_CANDIDATES.csv TC-0befe2825ad3, TC-206496479449 (Girish -> Tarsem DISTINGUISHES, DOCUMENTARY_CHECK_REQUIRED)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| RD-TARSEM-H1 | sc-2008-union-of-india-ors-2008insc930 p.5, para 5 | COURT_VOICE | "will restrict the consequential relief relating to arrears normally" (SCR rendition [2008] 12 SCR 104; OCR noise in the continuation) | verified (stated page) |
| RD-TARSEM-H2 | sc-2008-union-of-india-ors-2008insc930 p.6, para 6 | COURT_VOICE | "It ought to have restricted the relief relating to ar- rears to only three years before the date of writ petition" | verified (stated page) |
| RD-GIRISH-T1 | sc-2026-union-of-india-through-its-sec-2026insc149 p.11, para 22 | COURT_VOICE | "The reliance placed by the appellant on the decision of a two-Judge Bench of this Court in Tarsem Singh (supra) is of no assistance to it, as the legal landscape did not remain static after decision in Tarsem Singh." | verified (stated page) |
| RD-GIRISH-T2 | sc-2026-union-of-india-through-its-sec-2026insc149 p.11, para 22 | COURT_VOICE | "the decision in Tarsem Singh (supra) has no application to the case in hand as ex-servicemen in the instant appeals are already in receipt of disability pension" | verified (stated page) |
| RD-GIRISH-T3 | sc-2026-union-of-india-through-its-sec-2026insc149 p.11, para 22 | COURT_VOICE | "decided the issue of applicability of instruction dated 31.01.2001 and the aforesaid decision is in rem." | verified (stated page) |
| RD-GIRISH-H1 | sc-2026-union-of-india-through-its-sec-2026insc149 p.11, para 22 | COURT_VOICE | "Therefore, the bar contained in Section 22(1)(c) of the Act has no application to the" (continues on p.12: 'claims filed by the ex-servicemen before the Tribunal.') | verified (stated page) |
| RD-GIRISH-BENCH | sc-2026-union-of-india-through-its-sec-2026insc149 p.1 | BENCH | "[Pamidighantam Sri Narasimha and Alok Aradhe,* JJ.]" | verified (stated page) |
| R-TARSEM-T3 | official copy wt:10e1954f (Mullikote, 2026 INSC 286) p.27, para 43 | COURT_VOICE | "In any event, the said question of law is left open." (Mullikote is not in the ad77758d text layer) | not re-verifiable here (no text file at ad77758d; carried from C10 JUDICIAL_TREATMENT_C10.csv (quote_check VERBATIM_FOUND)) |
| RD-DHC-TARSEM-A | hc-delhi-2026-w-p-c-16771-2025-dlhc010862002025-1-2026-03-11 p.9, para 27 | LATER_RELIANCE | "view the law laid down by Supreme Court in Union of India & Ors v. Tarsem Singh8 , the arrears will be restricted to three years prior the OA," (Delhi HC 11-03-2026, after Girish; Girish not mentioned in the passage) | verified (stated page) |
| RD-DHC-TARSEM-D | hc-delhi-2026-w-p-c-2053-2026-dlhc010054682026-1-2026-04-20 p.3, para 10 | LATER_RELIANCE | "The reliance placed on Tarsem Singh (supra) is misconceived." | verified (stated page) |
| R-GIRISH-T1 | hc-ph-2026-cwp-7955-2026-phhc010370702026-1-2026-03-17 p.3 | LATER_RELIANCE | "has been settled by the Hon’ble Supreme Court of India in a recently passed judgment in Civil Appeal Nos. 6820-6824 of 2018" (P&H HC reads Girish as settling the arrears question for a non-party claimant) | verified (stated page) |
| R-TARSEM-T6 | hc-jkl-2026-wp-c-1426-2026-jkhc020026572026-1-2026-05-19 p.4, para (quoting Girish para 22) | LATER_RELIANCE | "For, yet another reason, the decision in Tarsem Singh (supra) has no application to the case in hand" (words are Girish's, reproduced by the HC (QUOTED_PASSAGE)) | verified (stated page) |
| RD-GIRISH-ED | sc-2026-union-of-india-through-its-sec-2026insc149 p.2 | EDITORIAL | "Tarsem Singh [2008] 12 SCR 104 : (2008) 8 SCC 648 – held inapplicable." (reporter matter; never the court's treatment) | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Narrow, or question open: Girish para 22 gives the re-computation ground expressly (RD-GIRISH-T2); Mullikote para 43 left the question open (R-TARSEM-T3); Delhi HC 11-03-2026, after Girish, still restricts arrears by Tarsem (RD-DHC-TARSEM-A); Girish and Tarsem are both two-Judge Benches.
- (b) Broader: Girish's first ground ("legal landscape did not remain static", RD-GIRISH-T1) is tied to Ram Avtar being in rem (RD-GIRISH-T3); C9 records para 20 (official p.14) as a "consistent line of decisions" against curtailing disability pension to three years; P&H HC 17-03-2026 reads Girish as settling the arrears question for a non-party claimant (R-GIRISH-T1).
- Delhi HC 20-04-2026 calls reliance on Tarsem "misconceived" on a fact-based distinction (ACP upgradation), not a statement about Tarsem's authority (RD-DHC-TARSEM-D).

**Affected research records.** AFT-013; AFT-014; V7-SC-02; V7-SC-14; V7-SC-16; V7-JD-04; PEN-048; DCLR-SC-2008-N10

**Evidence still missing.**
- Official court copy of Tarsem (only an unregistered SCR-format rendition is held; C9 ESC-04).
- Mullikote (2026 INSC 286) and the official Girish copy are outside the ad77758d text layer; C10 readings not re-read in C11.
- The 12-10-2026 clarification order (see AQ-PEN-03).
- Human confirmation of the AI readings.

### AQ-PEN-02: Relation type Girish -> Tarsem and the C9 warning wording

**Priority:** P1. **Origin:** C9 ESC-01 (b)-(c).

**Question.** Which relation should be recorded from Girish to Tarsem ("distinguishes" is proposed; the documents are recorded as supporting no stronger edge), and may the warning wording in C9-CP-A01 to A04 (which states that Tarsem is not recorded as overruled) be applied?

**Sources.**
- C9 LEGAL_ADVISER_ESCALATION.md ESC-01 (b), (c)
- C10 C9_FINDING_STATUS_C10.csv C9-F-A01/A02 (UNCHANGED_EVIDENCE_ADDED)
- C11 TREATMENT_CANDIDATES.csv TC-0befe2825ad3, TC-206496479449

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| RD-GIRISH-T1 | sc-2026-union-of-india-through-its-sec-2026insc149 p.11, para 22 | COURT_VOICE | "The reliance placed by the appellant on the decision of a two-Judge Bench of this Court in Tarsem Singh (supra) is of no assistance to it, as the legal landscape did not remain static after decision in Tarsem Singh." | verified (stated page) |
| RD-GIRISH-T2 | sc-2026-union-of-india-through-its-sec-2026insc149 p.11, para 22 | COURT_VOICE | "the decision in Tarsem Singh (supra) has no application to the case in hand as ex-servicemen in the instant appeals are already in receipt of disability pension" | verified (stated page) |
| RD-GIRISH-BENCH | sc-2026-union-of-india-through-its-sec-2026insc149 p.1 | BENCH | "[Pamidighantam Sri Narasimha and Alok Aradhe,* JJ.]" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) distinguishes (C9 proposal; C10 and C11 both record the wording as distinguishing, not overruling).
- (b) Whether a coordinate (two-Judge) Bench could do more, and what relation to record, is expressly left to the adviser (C9 review LG-09); no artefact proposes a stronger edge.

**Affected research records.** AFT-013; AFT-014; V7-SC-02; V7-SC-14; V7-SC-16; V7-JD-04

**Evidence still missing.**
- Decision on AQ-PEN-01.

### AQ-PEN-03: The unheld 12-10-2026 "clarification" of Girish Kumar

**Priority:** P1. **Origin:** C9 ESC-02 (a), ESC-04; C10 ESC-C10-02.

**Question.** Until an official copy of the reported 12-10-2026 order (reported as 2026 INSC 1113) is obtained and read, may the corpus state its content at all (and if so only with an "UNVERIFIED SOURCE" flag)? Will the owner/adviser authorise acquisition of an official copy, or confirm that it does not exist?

**Sources.**
- C11 dossier, "Union of India v. Sgt Girish Kumar (reported clarification order, 12-10-2026)" (deterministic search: 0 held judgments cite 2026 INSC 1113)
- C10 ESC-C10-02
- C9 LEGAL_ADVISER_ESCALATION.md ESC-02 (a) and ESC-04
- C11 AFFECTED_RESEARCH_RECORDS.csv (Girish: 9 rows, ACQUIRE_THEN_REVIEW)

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Seven records state the clarification's content as fact (C9): PEN-045 "The Supreme Court clarified on 12 October 2026 ..."; PEN-048 "squarely rejects universalisation"; DCLR-SC-2026-007 scope_and_caveats "expressly prevents mechanical extension"; DCLR-SC-2026-008 holding; PEN-J-06; and by reference PEN-WF-08, PEN-CS-09, PEN-J-05.
- (b) The order is NOT HELD, its identity is UNRESOLVED, no held judgment cites it, and the only URL is a commercial database (a discovery lead, not a source, under CLAUDE.md). The C11 dossier says: do not treat Girish as modified or unmodified on this evidence.

**Affected research records.** PEN-023; PEN-044; PEN-045; PEN-048; PEN-049; PEN-WF-08; PEN-CS-09; PEN-J-05; PEN-J-06; DCLR-SC-2026-007; DCLR-SC-2026-008

**Evidence still missing.**
- An official copy of the order. The official lookup earlier met a CAPTCHA; CLAUDE.md requires stopping and reporting, not bypassing.
- Approval for a download run (CLAUDE.md).

### AQ-PEN-04: Is Girish a "case-specific arrears award"?

**Priority:** P1. **Origin:** C9 ESC-02 (b).

**Question.** Is the corpus framing of the February 2026 Girish judgment as a "case-specific arrears award" supported by the judgment itself?

**Sources.**
- C9 LEGAL_ADVISER_ESCALATION.md ESC-02 (b)
- C10 R-GIRISH-T1/T2/T3, P-GIRISH (24 held HC judgments apply Girish after 12-02-2026; 4 read)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| RD-GIRISH-T3 | sc-2026-union-of-india-through-its-sec-2026insc149 p.11, para 22 | COURT_VOICE | "decided the issue of applicability of instruction dated 31.01.2001 and the aforesaid decision is in rem." | verified (stated page) |
| RD-GIRISH-H1 | sc-2026-union-of-india-through-its-sec-2026insc149 p.11, para 22 | COURT_VOICE | "Therefore, the bar contained in Section 22(1)(c) of the Act has no application to the" (continues on p.12: 'claims filed by the ex-servicemen before the Tribunal.') | verified (stated page) |
| R-GIRISH-T1 | hc-ph-2026-cwp-7955-2026-phhc010370702026-1-2026-03-17 p.3 | LATER_RELIANCE | "has been settled by the Hon’ble Supreme Court of India in a recently passed judgment in Civil Appeal Nos. 6820-6824 of 2018" (P&H HC reads Girish as settling the arrears question for a non-party claimant) | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Supports "case-specific": operative para 23 (official pp.16-17) quashes the three-year restriction and grants arrears to the appellants in the listed appeals (C9).
- (b) Points the other way: para 18 (official p.13) describes the Government order of 18.04.2016 "to confer upon all eligible pensioners the benefit of arrears of disability pension"; para 22 describes Ram Avtar as in rem (RD-GIRISH-T3); High Courts have applied Girish to non-party claimants (C10 R-GIRISH-T1, T2).
- C9 notes that the "not universal" framing currently rests on the unheld clarification (AQ-PEN-03).

**Affected research records.** PEN-023; PEN-044; PEN-045; PEN-048; PEN-049; PEN-WF-08; PEN-CS-09; PEN-J-05; PEN-J-06; DCLR-SC-2026-007

**Evidence still missing.**
- Official Girish copy pages 13 and 16-17 are outside the ad77758d text layer (paras 18 and 23 not re-verified here).
- The clarification order.

### AQ-PEN-05: Ram Avtar identity, the S P Rathore limitation and the reach of "in rem"

**Priority:** P2. **Origin:** C9 ESC-08; C11 dossier.

**Question.** May the identity resolution be approved (Ram Avtar = SC order of 10-12-2014 in C.A. 418/2012 and connected appeals; the curated URL, which is the S P Rathore judgment, to be relabelled)? After an official copy of S P Rathore is held, may its limitation be propagated to the broad-banding records? Is Girish's "in rem" reading of Ram Avtar binding beyond broad-banding?

**Sources.**
- C9 LEGAL_ADVISER_ESCALATION.md ESC-08
- C10 R-RAMAVTAR-H1, R-RAMAVTAR-T1, R-SPRATHORE-H1, P-RAMAVTAR
- C11 dossier, Ram Avtar section
- C11 AFFECTED_RESEARCH_RECORDS.csv (Ram Avtar: 4 rows, ACQUIRE_THEN_REVIEW)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| RD-GIRISH-R1 | sc-2026-union-of-india-through-its-sec-2026insc149 p.9, para 14 | COURT_VOICE | "The legal position continued to be uncertain until it was settled by a three-Judge bench of this Court in Union of India & Others v. Ram Avtar (supra)." | verified (stated page) |
| R-RAMAVTAR-H1 | official copy wt:4f7ea3a4 (Girish) p.10, para 13 | COURT_VOICE | "by an order dated 10.12.2014 dismissed more than 800 appeals" | not re-verifiable here (no text file at ad77758d; carried from C10 JUDICIAL_TREATMENT_C10.csv (quote_check VERBATIM_FOUND)); same words found in the SCR rendition (sc-2026-union-of-india-through-its-sec-2026insc149 p.9); such hits can include reporter headnote pages, which are not court voice |
| RD-GIRISH-T3 | sc-2026-union-of-india-through-its-sec-2026insc149 p.11, para 22 | COURT_VOICE | "decided the issue of applicability of instruction dated 31.01.2001 and the aforesaid decision is in rem." | verified (stated page) |
| R-RAMAVTAR-T1 | sc-2019-g-h-union-of-india-ors-2019insc1359 p.4, para 8 | COURT_VOICE | "This Court in Ram Avtar (supra), while approving the judgment of the Armed Forces Tribunal only held that the principle of rounding off" (S P Rathore, SCR rendition [2019] 18 S.C.R. 990; no official copy held) | verified (stated page) |
| R-SPRATHORE-H1 | sc-2019-g-h-union-of-india-ors-2019insc1359 p.5, para 9 | COURT_VOICE | "If a person is not entitled to the disability pension, there would be no question of rounding off." | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Girish treats Ram Avtar as in rem (RD-GIRISH-T3) and as settling the position (RD-GIRISH-R1).
- (b) S P Rathore para 8 reads Ram Avtar as holding "only" that the principle of rounding off applies, and para 9 states that without entitlement there is no rounding off (R-RAMAVTAR-T1, R-SPRATHORE-H1; SCR rendition only).
- C11 dossier records whether the "in rem" reading reaches beyond broad-banding as an open question.

**Affected research records.** PEN-023; PEN-044; PEN-WF-08; PEN-J-04

**Evidence still missing.**
- The Ram Avtar order itself (NOT HELD in any store; all citations UNRESOLVED; C9 ESC-04).
- An official copy of S P Rathore (C.A. 10870/2018); the limitation now rests on an SCR rendition and an intern mirror (WSB-T-024).
- PEN-J-04's source URL is an SC office report, which corroborates listing metadata only.

### AQ-PEN-06: Dharamvir (1982 Rules) and N C Isaac (2008 Rules)

**Priority:** P2. **Origin:** C10 ESC-C10-04.

**Question.** How far does Union of India v Col N C Isaac (2026 INSC 993; paras 34-35, 39) limit the Dharamvir Singh presumption for claims under the Entitlement Rules 2008, and which pension research records need a rules-version or limitation note?

**Sources.**
- C10 ESC-C10-04; R-DHARAMVIR-T1, R-ISAAC-H1, P-DHARAMVIR
- C11 dossier, Dharamvir section (Isaac not re-read in C11)
- C11 AFFECTED_RESEARCH_RECORDS.csv (Dharamvir: 3 rows)
- CLAUDE.md quality check: "Dharamvir Singh (1982 Rules) vs the Sept 2026 SC ruling on 2008 Rules"

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| RD-DHARAMVIR-H1 | sc-2013-dharamvir-singh-2013insc408 p.27, para 28(ii) | COURT_VOICE | "A member is to be presumed in sound physical and mental condition upon entering service if there is no note or record at the time of entrance." (read with para 28(i): Entitlement Rules 1982) | verified (stated page) |
| R-DHARAMVIR-T1 | official copy wt:3f49a314 (N C Isaac, 2026 INSC 993) p.91, para 34 | COURT_VOICE | "substantially reproduce the 1982 scheme of causal connection, onus, and attributability/aggravation subject only to the limited qualification introduced by the proviso to Rule 7" (Isaac is not in the ad77758d text layer; authentication pending) | not re-verifiable here (no text file at ad77758d; carried from C10 JUDICIAL_TREATMENT_C10.csv (quote_check VERBATIM_FOUND)) |
| R-ISAAC-H1 | official copy wt:3f49a314 (N C Isaac, 2026 INSC 993) p.93, para 39(iii) | COURT_VOICE | "the principle in Rule 7 of the Entitlement Rules 2008 applies and the burden shifts" | not re-verifiable here (no text file at ad77758d; carried from C10 JUDICIAL_TREATMENT_C10.csv (quote_check VERBATIM_FOUND)) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Isaac para 34 records that the 2008 Rules "substantially reproduce the 1982 scheme ... subject only to the limited qualification introduced by the proviso to Rule 7" (R-DHARAMVIR-T1).
- (b) C10 notes Isaac para 35 (decisions that followed Dharamvir "without a detailed examination of the evidence" may be revisited) and para 39(iii) (Rule 7 of the 2008 Rules applies and the burden shifts, R-ISAAC-H1). Dharamvir is resolved as cited by 352 held judgments (C11 graph); the statute-link table never infers the Rules version.

**Affected research records.** PEN-043; PEN-CS-07; PEN-J-01; DCLR-SC-2013-N08

**Evidence still missing.**
- Isaac is outside the ad77758d text layer; its copy is AUTHENTICATION_PENDING (C10).
- Which citing judgments concern 2008-Rules claimants (ENT-UNSPECIFIED rows).

## 5. Own-voice overruling leads (C11 adviser queue)

The C11 relations tool queued 30 rows at LEGAL_INTERPRETATION_ADVISER_REVIEW (GRAPH_SUMMARY.json `treatment.adviser_rows`). They are grouped below into source sentences. One row (TC-222df5c885ad, Parashotam -> Shri Kant Sharma) is BOUND and is handled as AQ-HCW-01. The other 29 rows form 22 leads, AQ-OVR-01 to AQ-OVR-22. No target in these 29 rows is resolved to a held document (target_state UNRESOLVED). C12 name scan of records_658.jsonl (658 records) for the source and target names of these leads (Ajmer Singh, Subramanian, Anand Singh Bisht, Mafatlal, Kanhaiyalal, Charanjit, C S Gill, C.S. Gill, Shatrughan, Vatheeswaran, Triveniben, Advocates-on-Record, Advocates on Record, SCAORA, Samsher, Sriharan, Puttaswamy, Jabalpur, Bhanudas, Kharak, M P Sharma, MP Sharma, M.P. Sharma, Joseph Shine, Sowmithri, Revathi, Rewathi, Kalyani, Saeed Siddiqui, Yogendra Kumar, Teri Oat): no match. Not in AFFECTED_RESEARCH_RECORDS.csv.

Opinion labels come from SCR page headers. Per the C11 method, wording in a separate or dissenting opinion is sent as a lead with no proposal, because such an opinion "does not itself overrule". Known label errors are listed in the caveat column (C11 disposition V13-02 to V13-04).

**All 30 adviser rows.**

| Row | Question | Source (date) | Cue p./para | Cue | Opinion (attribution) | Candidate target (anchor p.) | Binding status | Proposal | Noise / caveat |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TC-4289a1bc33bc | AQ-OVR-01 | sc-1987-ajmer-singh-etc-etc-1987insc142 (1987-04-29) | 9/- | do not lay down the correct law | SOLE_OPINION (ERADI) (COURT_OWN_VOICE_UNBOUND_LEAD) | We hold that these two decisions (p.9) | LEAD (NO_CITATION_ANCHOR (target given as raw text only)) | OVERRULES | V13-04: "these two decisions" are named in the preceding sentences: Kerala HC (Subramanian) and Calcutta HC (Anand Singh Bisht). |
| TC-204093fae39f | AQ-OVR-02 | sc-1996-mafatlal-industries-ltd-etc-et-1996insc1514 (1996-12-19) | 105/70 | must be held to have been decided wrongly | LEAD_OPINION (AHMADI; first opinion in the report) (COURT_OWN_VOICE_UNBOUND_LEAD) | The decisions of this Court saying to the contrary (p.105) | LEAD (NO_CITATION_ANCHOR (target given as raw text only)) | OVERRULES | V13-02: the Mafatlal p.105 author is not Ahmadi CJ (opinion label wrong; proposal unchanged). |
| TC-8111df7aac52 | AQ-OVR-02 | sc-1996-mafatlal-industries-ltd-etc-et-1996insc1514 (1996-12-19) | 105/70 | are accordingly overruled herewith | LEAD_OPINION (AHMADI; first opinion in the report) (COURT_OWN_VOICE_UNBOUND_LEAD) | The decisions of this Court saying to the contrary must be held to have been decided wrongly and (p.105) | LEAD (NO_CITATION_ANCHOR (target given as raw text only)) | OVERRULES | V13-02: the Mafatlal p.105 author is not Ahmadi CJ (opinion label wrong; proposal unchanged). |
| TC-900ee3f8d5c6 | AQ-OVR-03 | sc-1996-mafatlal-industries-ltd-etc-et-1996insc1514 (1996-12-19) | 133/99 | have also been wrongly decided | LEAD_OPINION (AHMADI; first opinion in the report) (COURT_OWN_VOICE_UNBOUND_LEAD) | [1959] S.C.R. 1350 (p.133) | LEAD (CITATION_IN_PRECEDING_SENTENCE (back-reference 'E It must equally be held that the subse')) | OVERRULES | V13-02: the Mafatlal p.133 author is not Ahmadi CJ (opinion label wrong; proposal unchanged). |
| TC-cd1cb49fedd0 | AQ-OVR-04 | sc-1996-mafatlal-industries-ltd-etc-et-1996insc1514 (1996-12-19) | 133/99 | wrongly decided | LEAD_OPINION (AHMADI; first opinion in the report) (COURT_OWN_VOICE_UNBOUND_LEAD) | [1959] S.C.R. 1350 (p.133) | LEAD (binding not established: CUE_NOT_BOUND_TO_TARGET) | OVERRULES | V13-02: the Mafatlal p.133 author is not Ahmadi CJ (opinion label wrong; proposal unchanged). |
| TC-9b500dbe0d15 | AQ-OVR-05 | sc-2000-union-of-india-and-anr-2000insc231 (2000-04-24) | 19/8 | is overruled | SOLE_OPINION (SETHI) (COURT_OWN_VOICE_UNBOUND_LEAD) | If the objection regarding such plea (p.19) | LEAD (NO_CITATION_ANCHOR (target given as raw text only)) | OVERRULES | **DISREGARD (V13-01)** V13-01: C.S. Gill p.19 is a description of court-martial procedure ("If the objection regarding such plea is overruled"): proposal to be withdrawn. |
| TC-e8e740a5df2f | AQ-OVR-06 | sc-2014-shatrughan-chauhan-anr-2014insc46 (2014-01-21) | 54/34 | stands overruled | LEAD_OPINION (P. SATHASIVAM; first opinion in the report) (COURT_OWN_VOICE_UNBOUND_LEAD) | (1983) 2 SCC 68 (p.5) | LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.5)) | OVERRULES | **DISREGARD (V13-01)** V13-01: Shatrughan Chauhan p.54 sits inside a quotation from Triveniben: proposal to be withdrawn. |
| TC-8eee72cd601c | AQ-OVR-07 | sc-2015-supreme-court-advocates-on-rec-2015insc285 (2015-10-16) | 783/261 | stand overruled | SEPARATE_OPINION (MADAN B. LOKUR; concurring or separate, page-header based) (SEPARATE_OPINION_LEAD) | (2010) 5 SCC 538 (p.747) | LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.747)) | (none) | **DISREGARD (V13-01)** V13-01: SCAORA separate-opinion row is a rhetorical question: to be dropped. |
| TC-741f5ae7f6ab | AQ-OVR-08 | sc-2015-supreme-court-advocates-on-rec-2015insc285 (2015-10-16) | 802/287 | does not lay down the correct law | SEPARATE_OPINION (MADAN B. LOKUR; concurring or separate, page-header based) (SEPARATE_OPINION_LEAD) | AIR 1974 SC 2192 (p.217) | LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.217)) | (none) | **DISREGARD (V13-01)** V13-01: SCAORA separate-opinion row is a negated statement ("no one has said ... that it does not lay down the correct law"): to be dropped. |
| TC-c0a555a4670d | AQ-OVR-09 | sc-2015-union-of-india-2015insc886 (2015-12-02) | 99/105 | overrule | LEAD_OPINION (FAKKIR MOHAMED IBRAHIM KALIFULLA; first opinion in the report) (COURT_OWN_VOICE_UNBOUND_LEAD) | 2013 (2) SCC 452 (p.99) | LEAD (binding not established: CUE_NOT_BOUND_TO_TARGET; NEGATION_WORD_IN_CLAUSE) | OVERRULES |  |
| TC-bd05dc37276a | AQ-OVR-10 | sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801 (2017-08-24) | 167/121 | We also overrule | LEAD_OPINION (DR. D. Y. CHANDRACHUD; first opinion in the report) (COURT_OWN_VOICE_UNBOUND_LEAD) | (1977) 1 SCC 834 (p.21) | LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.21)) | OVERRULES |  |
| TC-bf39eab314cf | AQ-OVR-11 | sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801 (2017-08-24) | 167/121 | must be and is accordingly overruled | LEAD_OPINION (DR. D. Y. CHANDRACHUD; first opinion in the report) (COURT_OWN_VOICE_UNBOUND_LEAD) | (1976) 2 SCC 521 (p.167) | LEAD (NEAREST_CITATION_IN_PARAGRAPH (448 chars; may be another authority)) | OVERRULES |  |
| TC-7321756415bb | AQ-OVR-12 | sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801 (2017-08-24) | 275/185 | is overruled | LEAD_OPINION (DR. D. Y. CHANDRACHUD; first opinion in the report) (COURT_OWN_VOICE_UNBOUND_LEAD) | AIR 1954 SC 300 (p.304) | LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.304)) | OVERRULES |  |
| TC-a073b2e4fab8 | AQ-OVR-13 | sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801 (2017-08-24) | 276/185 | is overruled | LEAD_OPINION (DR. D. Y. CHANDRACHUD; first opinion in the report) (COURT_OWN_VOICE_UNBOUND_LEAD) | (1964) 1 SCR 332 (p.113) | LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.113)) | OVERRULES |  |
| TC-44e4cead92b0 | AQ-OVR-14 | sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801 (2017-08-24) | 432/185 | stands over-ruled | ORDER_OF_THE_COURT (COURT_OWN_VOICE_UNBOUND_LEAD) | 1954 SCR 1077 (p.379) | LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.379)) | OVERRULES |  |
| TC-09b5d373b025 | AQ-OVR-15 | sc-2018-justice-k-s-puttaswamy-retd-2018insc880 (2018-09-26) | 705/448 | does not lay down the correct law | SEPARATE_OPINION (ASHOK BHUSHAN; concurring or separate, page-header based) (SEPARATE_OPINION_LEAD) | (2004) 2 SCC 130 (p.641) | LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.641,90)) | (none) | V13-03: the candidate for Mohd. Saeed Siddiqui is wrong; (2004) 2 SCC 130 is Teri Oat Estates. Match on the party name in the sentence. |
| TC-b2a42bfe7a34 | AQ-OVR-15 | sc-2018-justice-k-s-puttaswamy-retd-2018insc880 (2018-09-26) | 705/448 | does not lay down the correct law | SEPARATE_OPINION (ASHOK BHUSHAN; concurring or separate, page-header based) (SEPARATE_OPINION_LEAD) | (2016) 3 SCC 183 (p.90) | LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.641,90)) | (none) |  |
| TC-50aa07ffde85 | AQ-OVR-16 | sc-2018-justice-k-s-puttaswamy-retd-2018insc880 (2018-09-26) | 820/448 | are overruled | DISSENT (DR. D. Y. CHANDRACHUD) (DISSENT_OPINION_LEAD) | (2014) 11 SCC 415 (p.703) | LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.703,90)) | (none) |  |
| TC-60023f729c47 | AQ-OVR-16 | sc-2018-justice-k-s-puttaswamy-retd-2018insc880 (2018-09-26) | 820/448 | are overruled | DISSENT (DR. D. Y. CHANDRACHUD) (DISSENT_OPINION_LEAD) | (2016) 3 SCC 183 (p.90) | LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.703,90)) | (none) |  |
| TC-19f0e5a3af63 | AQ-OVR-17 | sc-2018-justice-k-s-puttaswamy-retd-2018insc880 (2018-09-26) | 1065/448 | are accordingly overruled | SEPARATE_OPINION (ASHOK BHUSHAN; concurring or separate, page-header based) (SEPARATE_OPINION_LEAD) | (2016) 3 SCC 183 (p.90) | LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.703,90)) | (none) | V13-02: p.1065 is Chandrachud J.'s dissent, not Bhushan J.'s opinion (bracketed footer preferred to running header). |
| TC-bd7606d4e30b | AQ-OVR-17 | sc-2018-justice-k-s-puttaswamy-retd-2018insc880 (2018-09-26) | 1065/448 | are accordingly overruled | SEPARATE_OPINION (ASHOK BHUSHAN; concurring or separate, page-header based) (SEPARATE_OPINION_LEAD) | (2014) 11 SCC 415 (p.703) | LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.703,90)) | (none) | V13-02: p.1065 is Chandrachud J.'s dissent, not Bhushan J.'s opinion (bracketed footer preferred to running header). |
| TC-3c0fb3f2e38a | AQ-OVR-18 | sc-2018-joseph-shine-2018insc898 (2018-09-27) | 74/57 | stand overruled | LEAD_OPINION (DIPAK MISRA; first opinion in the report) (COURT_OWN_VOICE_UNBOUND_LEAD) | 1985 Supp SCC 137 (p.27) | LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.27,36)) | OVERRULES |  |
| TC-8682d402357c | AQ-OVR-18 | sc-2018-joseph-shine-2018insc898 (2018-09-27) | 74/57 | stand overruled | LEAD_OPINION (DIPAK MISRA; first opinion in the report) (COURT_OWN_VOICE_UNBOUND_LEAD) | (1988) 2 SCC 72 (p.36) | LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.27,36)) | OVERRULES |  |
| TC-29a337ba9c11 | AQ-OVR-19 | sc-2018-joseph-shine-2018insc898 (2018-09-27) | 100/58 | we overrule | SEPARATE_OPINION (R. F. NARIMAN; concurring or separate, page-header based) (SEPARATE_OPINION_LEAD) | 1985 Supp SCC 137 (p.27) | LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.27)) | (none) |  |
| TC-a272984ee636 | AQ-OVR-20 | sc-2018-joseph-shine-2018insc898 (2018-09-27) | 109/58 | is overruled | SEPARATE_OPINION (DR. D. Y. CHANDRACHUD; concurring or separate, page-header based) (SEPARATE_OPINION_LEAD) | 1985 Supp SCC 137 (p.27) | LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.27)) | (none) |  |
| TC-235c7582ce78 | AQ-OVR-21 | sc-2018-joseph-shine-2018insc898 (2018-09-27) | 154/67 | are overruled | SEPARATE_OPINION (DR. D. Y. CHANDRACHUD; concurring or separate, page-header based) (SEPARATE_OPINION_LEAD) | (1988) 2 SCC 72 (p.36) | LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.27,36)) | (none) |  |
| TC-387c984f74dc | AQ-OVR-21 | sc-2018-joseph-shine-2018insc898 (2018-09-27) | 154/67 | are overruled | SEPARATE_OPINION (DR. D. Y. CHANDRACHUD; concurring or separate, page-header based) (SEPARATE_OPINION_LEAD) | 1985 Supp SCC 137 (p.27) | LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.27,36)) | (none) |  |
| TC-0b27a3830ff7 | AQ-OVR-22 | sc-2018-joseph-shine-2018insc898 (2018-09-27) | 186/67 | hereby stand overruled | SEPARATE_OPINION (INDU MALHOTRA; concurring or separate, page-header based) (SEPARATE_OPINION_LEAD) | 1985 Supp SCC 137 (p.27) | LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.27,36)) | (none) |  |
| TC-48e2ff70f085 | AQ-OVR-22 | sc-2018-joseph-shine-2018insc898 (2018-09-27) | 186/67 | hereby stand overruled | SEPARATE_OPINION (INDU MALHOTRA; concurring or separate, page-header based) (SEPARATE_OPINION_LEAD) | (2012) 1 SCC 358 (p.36) | LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.27,36)) | (none) |  |
| TC-222df5c885ad | AQ-HCW-01 | sc-2023-union-of-india-ors-2023insc265 (2023-03-21) | 17/32 | does not lay down the correct law | SOLE_OPINION (SANJAY KISHAN KAUL) (COURT_OWN_VOICE) | Shri Kant (p.17) -> sc-2015-union-of-india-ors-2015insc206 | BOUND | OVERRULES |  |

### AQ-OVR-01: sc-1987-ajmer-singh-etc-etc-1987insc142 p.9: "do not lay down the correct law"

**Priority:** P3. **Origin:** C11 adviser queue (30 rows).

**Question.** Is the quoted sentence (sc-1987-ajmer-singh-etc-etc-1987insc142, p.9) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The tool proposes OVERRULES for review only; the target binding is not established.

**Sources.**
- C11 TREATMENT_CANDIDATES.csv TC-4289a1bc33bc
- C11 GRAPH_SUMMARY.json treatment.adviser_rows
- C11 DISPOSITIONS_relations_c11.md (round 4 P3s)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| LEAD-TC-4289a1bc33bc | sc-1987-ajmer-singh-etc-etc-1987insc142 p.9 | COURT_VOICE_OR_OPINION | "merely followed B the aforesaid ruling of the Single Judge of the High Court of Kerala. We hold that these two decisions do not lay down the correct law. -..:\: It follows from the foregoing discussion that these appeals are ~ devoid of merits" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Tool reading: own-voice wording "do not lay down the correct law"; attribution COURT_OWN_VOICE_UNBOUND_LEAD; opinion SOLE_OPINION (ERADI); proposal OVERRULES.
- (b) Binding: LEAD (NO_CITATION_ANCHOR (target given as raw text only)). Candidate target(s): We hold that these two decisions (anchor at p.9). Raw target text: "We hold that these two decisions"
- V13-04: "these two decisions" are named in the preceding sentences: Kerala HC (Subramanian) and Calcutta HC (Anand Singh Bisht).

**Affected research records.** None identified. C12 name scan of records_658.jsonl (658 records) for the source and target names of these leads (Ajmer Singh, Subramanian, Anand Singh Bisht, Mafatlal, Kanhaiyalal, Charanjit, C S Gill, C.S. Gill, Shatrughan, Vatheeswaran, Triveniben, Advocates-on-Record, Advocates on Record, SCAORA, Samsher, Sriharan, Puttaswamy, Jabalpur, Bhanudas, Kharak, M P Sharma, MP Sharma, M.P. Sharma, Joseph Shine, Sowmithri, Revathi, Rewathi, Kalyani, Saeed Siddiqui, Yogendra Kumar, Teri Oat): no match. Not in AFFECTED_RESEARCH_RECORDS.csv.

**Evidence still missing.**
- Human confirmation of the reading on the page image (text-layer copy; not a signed court copy).
- Resolution of the target citation to a held document (target_state UNRESOLVED).

### AQ-OVR-02: sc-1996-mafatlal-industries-ltd-etc-et-1996insc1514 p.105: "must be held to have been decided wrongly"

**Priority:** P3. **Origin:** C11 adviser queue (30 rows).

**Question.** Is the quoted sentence (sc-1996-mafatlal-industries-ltd-etc-et-1996insc1514, p.105) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The tool proposes OVERRULES for review only; the target binding is not established.

**Sources.**
- C11 TREATMENT_CANDIDATES.csv TC-204093fae39f, TC-8111df7aac52
- C11 GRAPH_SUMMARY.json treatment.adviser_rows
- C11 DISPOSITIONS_relations_c11.md (round 4 P3s)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| LEAD-TC-204093fae39f | sc-1996-mafatlal-industries-ltd-etc-et-1996insc1514 p.105, para 70 | COURT_VOICE_OR_OPINION | "of Hidayatullah, CJ. in Tilokchand Motichand extracted in Para 37). The decisions of this Court saying to the contrary must be held to have been decided wrongly and are accordingly overruled herewith. E 71. Re. : (III) : For the purpose of" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Tool reading: own-voice wording "must be held to have been decided wrongly"; attribution COURT_OWN_VOICE_UNBOUND_LEAD; opinion LEAD_OPINION (AHMADI; first opinion in the report); proposal OVERRULES.
- (b) Binding: LEAD (NO_CITATION_ANCHOR (target given as raw text only)). Candidate target(s): The decisions of this Court saying to the contrary (anchor at p.105); The decisions of this Court saying to the contrary must be held to have been decided wrongly and (anchor at p.105). Raw target text: "The decisions of this Court saying to the contrary"
- V13-02: the Mafatlal p.105 author is not Ahmadi CJ (opinion label wrong; proposal unchanged).

**Affected research records.** None identified. C12 name scan of records_658.jsonl (658 records) for the source and target names of these leads (Ajmer Singh, Subramanian, Anand Singh Bisht, Mafatlal, Kanhaiyalal, Charanjit, C S Gill, C.S. Gill, Shatrughan, Vatheeswaran, Triveniben, Advocates-on-Record, Advocates on Record, SCAORA, Samsher, Sriharan, Puttaswamy, Jabalpur, Bhanudas, Kharak, M P Sharma, MP Sharma, M.P. Sharma, Joseph Shine, Sowmithri, Revathi, Rewathi, Kalyani, Saeed Siddiqui, Yogendra Kumar, Teri Oat): no match. Not in AFFECTED_RESEARCH_RECORDS.csv.

**Evidence still missing.**
- Human confirmation of the reading on the page image (text-layer copy; not a signed court copy).
- Resolution of the target citation to a held document (target_state UNRESOLVED).

### AQ-OVR-03: sc-1996-mafatlal-industries-ltd-etc-et-1996insc1514 p.133: "have also been wrongly decided"

**Priority:** P3. **Origin:** C11 adviser queue (30 rows).

**Question.** Is the quoted sentence (sc-1996-mafatlal-industries-ltd-etc-et-1996insc1514, p.133) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The tool proposes OVERRULES for review only; the target binding is not established.

**Sources.**
- C11 TREATMENT_CANDIDATES.csv TC-900ee3f8d5c6
- C11 GRAPH_SUMMARY.json treatment.adviser_rows
- C11 DISPOSITIONS_relations_c11.md (round 4 P3s)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| LEAD-TC-900ee3f8d5c6 | sc-1996-mafatlal-industries-ltd-etc-et-1996insc1514 p.133, para 99 | COURT_VOICE_OR_OPINION | "be held that the subsequent decisions of this Court follow- F ing and applying the said propositions in Kanhaiyalal have also been wrongly decided to the above extent. This declaration - or the law laid down in Propositions (i) to (vii)" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Tool reading: own-voice wording "have also been wrongly decided"; attribution COURT_OWN_VOICE_UNBOUND_LEAD; opinion LEAD_OPINION (AHMADI; first opinion in the report); proposal OVERRULES.
- (b) Binding: LEAD (CITATION_IN_PRECEDING_SENTENCE (back-reference 'E It must equally be held that the subse')). Candidate target(s): [1959] S.C.R. 1350 (anchor at p.133). Raw target text: "have been wrongly decided insofar as it lays down or is understood to have laid down propositions contrary to the propositions enunciated in (i) to (vii) above. / E It must equally be held that the subsequent decisions of this Court follow- F ing and applying the said propositions in Kanhaiyalal"
- V13-02: the Mafatlal p.133 author is not Ahmadi CJ (opinion label wrong; proposal unchanged).

**Affected research records.** None identified. C12 name scan of records_658.jsonl (658 records) for the source and target names of these leads (Ajmer Singh, Subramanian, Anand Singh Bisht, Mafatlal, Kanhaiyalal, Charanjit, C S Gill, C.S. Gill, Shatrughan, Vatheeswaran, Triveniben, Advocates-on-Record, Advocates on Record, SCAORA, Samsher, Sriharan, Puttaswamy, Jabalpur, Bhanudas, Kharak, M P Sharma, MP Sharma, M.P. Sharma, Joseph Shine, Sowmithri, Revathi, Rewathi, Kalyani, Saeed Siddiqui, Yogendra Kumar, Teri Oat): no match. Not in AFFECTED_RESEARCH_RECORDS.csv.

**Evidence still missing.**
- Human confirmation of the reading on the page image (text-layer copy; not a signed court copy).
- Resolution of the target citation to a held document (target_state UNRESOLVED).

### AQ-OVR-04: sc-1996-mafatlal-industries-ltd-etc-et-1996insc1514 p.133: "wrongly decided"

**Priority:** P3. **Origin:** C11 adviser queue (30 rows).

**Question.** Is the quoted sentence (sc-1996-mafatlal-industries-ltd-etc-et-1996insc1514, p.133) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The tool proposes OVERRULES for review only; the target binding is not established.

**Sources.**
- C11 TREATMENT_CANDIDATES.csv TC-cd1cb49fedd0
- C11 GRAPH_SUMMARY.json treatment.adviser_rows
- C11 DISPOSITIONS_relations_c11.md (round 4 P3s)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| LEAD-TC-cd1cb49fedd0 | sc-1996-mafatlal-industries-ltd-etc-et-1996insc1514 p.133, para 99 | COURT_VOICE_OR_OPINION | "Tax Officer Benaras v. Kanhaiyalal Mukundlal Saraf, [1959] S.C.R. 1350 must be held to have been wrongly decided insofar as it lays down or is understood to have laid down" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Tool reading: own-voice wording "wrongly decided"; attribution COURT_OWN_VOICE_UNBOUND_LEAD; opinion LEAD_OPINION (AHMADI; first opinion in the report); proposal OVERRULES.
- (b) Binding: LEAD (binding not established: CUE_NOT_BOUND_TO_TARGET). Candidate target(s): [1959] S.C.R. 1350 (anchor at p.133). No raw target text recorded.
- V13-02: the Mafatlal p.133 author is not Ahmadi CJ (opinion label wrong; proposal unchanged).

**Affected research records.** None identified. C12 name scan of records_658.jsonl (658 records) for the source and target names of these leads (Ajmer Singh, Subramanian, Anand Singh Bisht, Mafatlal, Kanhaiyalal, Charanjit, C S Gill, C.S. Gill, Shatrughan, Vatheeswaran, Triveniben, Advocates-on-Record, Advocates on Record, SCAORA, Samsher, Sriharan, Puttaswamy, Jabalpur, Bhanudas, Kharak, M P Sharma, MP Sharma, M.P. Sharma, Joseph Shine, Sowmithri, Revathi, Rewathi, Kalyani, Saeed Siddiqui, Yogendra Kumar, Teri Oat): no match. Not in AFFECTED_RESEARCH_RECORDS.csv.

**Evidence still missing.**
- Human confirmation of the reading on the page image (text-layer copy; not a signed court copy).
- Resolution of the target citation to a held document (target_state UNRESOLVED).

### AQ-OVR-05: sc-2000-union-of-india-and-anr-2000insc231 p.19: "is overruled" [DISREGARD (V13-01)]

**Priority:** P3 (disregard pending withdrawal). **Origin:** C11 adviser queue (30 rows).

**Question.** Confirm that candidate row(s) TC-9b500dbe0d15 are noise and should be disregarded (C11 disposition V13-01), so that no treatment edge is recorded from this sentence.

**Sources.**
- C11 TREATMENT_CANDIDATES.csv TC-9b500dbe0d15
- C11 GRAPH_SUMMARY.json treatment.adviser_rows
- C11 DISPOSITIONS_relations_c11.md (round 4 P3s)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| LEAD-TC-9b500dbe0d15 | sc-2000-union-of-india-and-anr-2000insc231 p.19, para 8 | COURT_VOICE_OR_OPINION | "to the jurisdiction of the court and if he does so, the court shall decide A it. If the objection regarding such plea is overruled, the court shall proceed with the trial and if such plea is allowed, the court is required to record its reason" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) The tool flagged own-voice overruling wording (is overruled).
- (b) V13-01: C.S. Gill p.19 is a description of court-martial procedure ("If the objection regarding such plea is overruled"): proposal to be withdrawn.

**Affected research records.** None identified. C12 name scan of records_658.jsonl (658 records) for the source and target names of these leads (Ajmer Singh, Subramanian, Anand Singh Bisht, Mafatlal, Kanhaiyalal, Charanjit, C S Gill, C.S. Gill, Shatrughan, Vatheeswaran, Triveniben, Advocates-on-Record, Advocates on Record, SCAORA, Samsher, Sriharan, Puttaswamy, Jabalpur, Bhanudas, Kharak, M P Sharma, MP Sharma, M.P. Sharma, Joseph Shine, Sowmithri, Revathi, Rewathi, Kalyani, Saeed Siddiqui, Yogendra Kumar, Teri Oat): no match. Not in AFFECTED_RESEARCH_RECORDS.csv. The source judgment corresponds to curated case DCLR-SC-2000-N14 (Charanjit S Gill) per CURATED_53_C11.csv title; disregarding the row does not change that record.

**Evidence still missing.**
- Human confirmation of the reading on the page image (text-layer copy; not a signed court copy).
- Resolution of the target citation to a held document (target_state UNRESOLVED).
- Withdrawal of the row in the follow-up change (V13-01).

### AQ-OVR-06: sc-2014-shatrughan-chauhan-anr-2014insc46 p.54: "stands overruled" [DISREGARD (V13-01)]

**Priority:** P3 (disregard pending withdrawal). **Origin:** C11 adviser queue (30 rows).

**Question.** Confirm that candidate row(s) TC-e8e740a5df2f are noise and should be disregarded (C11 disposition V13-01), so that no treatment edge is recorded from this sentence.

**Sources.**
- C11 TREATMENT_CANDIDATES.csv TC-e8e740a5df2f
- C11 GRAPH_SUMMARY.json treatment.adviser_rows
- C11 DISPOSITIONS_relations_c11.md (round 4 P3s)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| LEAD-TC-e8e740a5df2f | sc-2014-shatrughan-chauhan-anr-2014insc46 p.54, para 34 | COURT_VOICE_OR_OPINION | "to this extent the decision in Vatheeswaran case cannot be said to lay down the correct law and therefore to that extent stands overruled." 35. While giving full reasons which is reported in Smt. Triveniben vs. State of Gujarat, (1989) 1 SCC" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) The tool flagged own-voice overruling wording (stands overruled).
- (b) V13-01: Shatrughan Chauhan p.54 sits inside a quotation from Triveniben: proposal to be withdrawn.

**Affected research records.** None identified. C12 name scan of records_658.jsonl (658 records) for the source and target names of these leads (Ajmer Singh, Subramanian, Anand Singh Bisht, Mafatlal, Kanhaiyalal, Charanjit, C S Gill, C.S. Gill, Shatrughan, Vatheeswaran, Triveniben, Advocates-on-Record, Advocates on Record, SCAORA, Samsher, Sriharan, Puttaswamy, Jabalpur, Bhanudas, Kharak, M P Sharma, MP Sharma, M.P. Sharma, Joseph Shine, Sowmithri, Revathi, Rewathi, Kalyani, Saeed Siddiqui, Yogendra Kumar, Teri Oat): no match. Not in AFFECTED_RESEARCH_RECORDS.csv.

**Evidence still missing.**
- Human confirmation of the reading on the page image (text-layer copy; not a signed court copy).
- Resolution of the target citation to a held document (target_state UNRESOLVED).
- Withdrawal of the row in the follow-up change (V13-01).

### AQ-OVR-07: sc-2015-supreme-court-advocates-on-rec-2015insc285 p.783: "stand overruled" [DISREGARD (V13-01)]

**Priority:** P3 (disregard pending withdrawal). **Origin:** C11 adviser queue (30 rows).

**Question.** Confirm that candidate row(s) TC-8eee72cd601c are noise and should be disregarded (C11 disposition V13-01), so that no treatment edge is recorded from this sentence.

**Sources.**
- C11 TREATMENT_CANDIDATES.csv TC-8eee72cd601c
- C11 GRAPH_SUMMARY.json treatment.adviser_rows
- C11 DISPOSITIONS_relations_c11.md (round 4 P3s)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| LEAD-TC-8eee72cd601c | sc-2015-supreme-court-advocates-on-rec-2015insc285 p.783, para 261 | COURT_VOICE_OR_OPINION | "3 leamed judges found no error in that decision? Would a decision rendered unanimously by a Bench of 5 learned judges stand overruled by the decision of 4 learned judges in a subsequent Bench of B 7 learned judges? Pradeep Kumar Biswas" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) The tool flagged own-voice overruling wording (stand overruled).
- (b) V13-01: SCAORA separate-opinion row is a rhetorical question: to be dropped.

**Affected research records.** None identified. C12 name scan of records_658.jsonl (658 records) for the source and target names of these leads (Ajmer Singh, Subramanian, Anand Singh Bisht, Mafatlal, Kanhaiyalal, Charanjit, C S Gill, C.S. Gill, Shatrughan, Vatheeswaran, Triveniben, Advocates-on-Record, Advocates on Record, SCAORA, Samsher, Sriharan, Puttaswamy, Jabalpur, Bhanudas, Kharak, M P Sharma, MP Sharma, M.P. Sharma, Joseph Shine, Sowmithri, Revathi, Rewathi, Kalyani, Saeed Siddiqui, Yogendra Kumar, Teri Oat): no match. Not in AFFECTED_RESEARCH_RECORDS.csv.

**Evidence still missing.**
- Human confirmation of the reading on the page image (text-layer copy; not a signed court copy).
- Resolution of the target citation to a held document (target_state UNRESOLVED).
- Withdrawal of the row in the follow-up change (V13-01).

### AQ-OVR-08: sc-2015-supreme-court-advocates-on-rec-2015insc285 p.802: "does not lay down the correct law" [DISREGARD (V13-01)]

**Priority:** P3 (disregard pending withdrawal). **Origin:** C11 adviser queue (30 rows).

**Question.** Confirm that candidate row(s) TC-741f5ae7f6ab are noise and should be disregarded (C11 disposition V13-01), so that no treatment edge is recorded from this sentence.

**Sources.**
- C11 TREATMENT_CANDIDATES.csv TC-741f5ae7f6ab
- C11 GRAPH_SUMMARY.json treatment.adviser_rows
- C11 DISPOSITIONS_relations_c11.md (round 4 P3s)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| LEAD-TC-741f5ae7f6ab | sc-2015-supreme-court-advocates-on-rec-2015insc285 p.802, para 287 | COURT_VOICE_OR_OPINION | "decided by a Bench of seven learned judges and no one has said that that decision requires F reconsideration or that it does not lay down the correct law. The Second Judges case merely reiterates the 'last word' view in a limited sense. 288." | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) The tool flagged own-voice overruling wording (does not lay down the correct law).
- (b) V13-01: SCAORA separate-opinion row is a negated statement ("no one has said ... that it does not lay down the correct law"): to be dropped.

**Affected research records.** None identified. C12 name scan of records_658.jsonl (658 records) for the source and target names of these leads (Ajmer Singh, Subramanian, Anand Singh Bisht, Mafatlal, Kanhaiyalal, Charanjit, C S Gill, C.S. Gill, Shatrughan, Vatheeswaran, Triveniben, Advocates-on-Record, Advocates on Record, SCAORA, Samsher, Sriharan, Puttaswamy, Jabalpur, Bhanudas, Kharak, M P Sharma, MP Sharma, M.P. Sharma, Joseph Shine, Sowmithri, Revathi, Rewathi, Kalyani, Saeed Siddiqui, Yogendra Kumar, Teri Oat): no match. Not in AFFECTED_RESEARCH_RECORDS.csv.

**Evidence still missing.**
- Human confirmation of the reading on the page image (text-layer copy; not a signed court copy).
- Resolution of the target citation to a held document (target_state UNRESOLVED).
- Withdrawal of the row in the follow-up change (V13-01).

### AQ-OVR-09: sc-2015-union-of-india-2015insc886 p.99: "overrule"

**Priority:** P3. **Origin:** C11 adviser queue (30 rows).

**Question.** Is the quoted sentence (sc-2015-union-of-india-2015insc886, p.99) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The tool proposes OVERRULES for review only; the target binding is not established.

**Sources.**
- C11 TREATMENT_CANDIDATES.csv TC-c0a555a4670d
- C11 GRAPH_SUMMARY.json treatment.adviser_rows
- C11 DISPOSITIONS_relations_c11.md (round 4 P3s)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| LEAD-TC-c0a555a4670d | sc-2015-union-of-india-2015insc886 p.99, para 105 | COURT_VOICE_OR_OPINION | "of 20 or 25 years or without any remission as not permissible is not in consonance with the law and we specifically overrule the same. 106. With that we come to the next important question, C namely: "Whether the Appropriate Government is perm" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Tool reading: own-voice wording "overrule"; attribution COURT_OWN_VOICE_UNBOUND_LEAD; opinion LEAD_OPINION (FAKKIR MOHAMED IBRAHIM KALIFULLA; first opinion in the report); proposal OVERRULES.
- (b) Binding: LEAD (binding not established: CUE_NOT_BOUND_TO_TARGET; NEGATION_WORD_IN_CLAUSE). Candidate target(s): 2013 (2) SCC 452 (anchor at p.99). No raw target text recorded.

**Affected research records.** None identified. C12 name scan of records_658.jsonl (658 records) for the source and target names of these leads (Ajmer Singh, Subramanian, Anand Singh Bisht, Mafatlal, Kanhaiyalal, Charanjit, C S Gill, C.S. Gill, Shatrughan, Vatheeswaran, Triveniben, Advocates-on-Record, Advocates on Record, SCAORA, Samsher, Sriharan, Puttaswamy, Jabalpur, Bhanudas, Kharak, M P Sharma, MP Sharma, M.P. Sharma, Joseph Shine, Sowmithri, Revathi, Rewathi, Kalyani, Saeed Siddiqui, Yogendra Kumar, Teri Oat): no match. Not in AFFECTED_RESEARCH_RECORDS.csv.

**Evidence still missing.**
- Human confirmation of the reading on the page image (text-layer copy; not a signed court copy).
- Resolution of the target citation to a held document (target_state UNRESOLVED).

### AQ-OVR-10: sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801 p.167: "We also overrule"

**Priority:** P3. **Origin:** C11 adviser queue (30 rows).

**Question.** Is the quoted sentence (sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801, p.167) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The tool proposes OVERRULES for review only; the target binding is not established.

**Sources.**
- C11 TREATMENT_CANDIDATES.csv TC-bd05dc37276a
- C11 GRAPH_SUMMARY.json treatment.adviser_rows
- C11 DISPOSITIONS_relations_c11.md (round 4 P3s)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| LEAD-TC-bd05dc37276a | sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801 p.167, para 121 | COURT_VOICE_OR_OPINION | "in a concentration camp solely because of his Japanese ancestry. ADM J1;1balpur must be and is accordingly overruled. We also overrule the decision in Union oflndia v Bhanudas Krishna Gawde213, which followed ADM Jabalpur. B · 122. In IR" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Tool reading: own-voice wording "We also overrule"; attribution COURT_OWN_VOICE_UNBOUND_LEAD; opinion LEAD_OPINION (DR. D. Y. CHANDRACHUD; first opinion in the report); proposal OVERRULES.
- (b) Binding: LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.21)). Candidate target(s): (1977) 1 SCC 834 (anchor at p.21). Raw target text: "Union oflndia v Bhanudas Krishna Gawde213"

**Affected research records.** None identified. C12 name scan of records_658.jsonl (658 records) for the source and target names of these leads (Ajmer Singh, Subramanian, Anand Singh Bisht, Mafatlal, Kanhaiyalal, Charanjit, C S Gill, C.S. Gill, Shatrughan, Vatheeswaran, Triveniben, Advocates-on-Record, Advocates on Record, SCAORA, Samsher, Sriharan, Puttaswamy, Jabalpur, Bhanudas, Kharak, M P Sharma, MP Sharma, M.P. Sharma, Joseph Shine, Sowmithri, Revathi, Rewathi, Kalyani, Saeed Siddiqui, Yogendra Kumar, Teri Oat): no match. Not in AFFECTED_RESEARCH_RECORDS.csv.

**Evidence still missing.**
- Human confirmation of the reading on the page image (text-layer copy; not a signed court copy).
- Resolution of the target citation to a held document (target_state UNRESOLVED).

### AQ-OVR-11: sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801 p.167: "must be and is accordingly overruled"

**Priority:** P3. **Origin:** C11 adviser queue (30 rows).

**Question.** Is the quoted sentence (sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801, p.167) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The tool proposes OVERRULES for review only; the target binding is not established.

**Sources.**
- C11 TREATMENT_CANDIDATES.csv TC-bf39eab314cf
- C11 GRAPH_SUMMARY.json treatment.adviser_rows
- C11 DISPOSITIONS_relations_c11.md (round 4 P3s)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| LEAD-TC-bf39eab314cf | sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801 p.167, para 121 | COURT_VOICE_OR_OPINION | "upholding the imprisonment of a citizen in a concentration camp solely because of his Japanese ancestry. ADM J1;1balpur must be and is accordingly overruled. We also overrule the decision in Union oflndia v Bhanudas Krishna Gawde213, which" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Tool reading: own-voice wording "must be and is accordingly overruled"; attribution COURT_OWN_VOICE_UNBOUND_LEAD; opinion LEAD_OPINION (DR. D. Y. CHANDRACHUD; first opinion in the report); proposal OVERRULES.
- (b) Binding: LEAD (NEAREST_CITATION_IN_PARAGRAPH (448 chars; may be another authority)). Candidate target(s): (1976) 2 SCC 521 (anchor at p.167). Raw target text: "ADM J1;1balpur"

**Affected research records.** None identified. C12 name scan of records_658.jsonl (658 records) for the source and target names of these leads (Ajmer Singh, Subramanian, Anand Singh Bisht, Mafatlal, Kanhaiyalal, Charanjit, C S Gill, C.S. Gill, Shatrughan, Vatheeswaran, Triveniben, Advocates-on-Record, Advocates on Record, SCAORA, Samsher, Sriharan, Puttaswamy, Jabalpur, Bhanudas, Kharak, M P Sharma, MP Sharma, M.P. Sharma, Joseph Shine, Sowmithri, Revathi, Rewathi, Kalyani, Saeed Siddiqui, Yogendra Kumar, Teri Oat): no match. Not in AFFECTED_RESEARCH_RECORDS.csv.

**Evidence still missing.**
- Human confirmation of the reading on the page image (text-layer copy; not a signed court copy).
- Resolution of the target citation to a held document (target_state UNRESOLVED).

### AQ-OVR-12: sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801 p.275: "is overruled"

**Priority:** P3. **Origin:** C11 adviser queue (30 rows).

**Question.** Is the quoted sentence (sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801, p.275) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The tool proposes OVERRULES for review only; the target binding is not established.

**Sources.**
- C11 TREATMENT_CANDIDATES.csv TC-7321756415bb
- C11 GRAPH_SUMMARY.json treatment.adviser_rows
- C11 DISPOSITIONS_relations_c11.md (round 4 P3s)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| LEAD-TC-7321756415bb | sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801 p.275, para 185 | COURT_VOICE_OR_OPINION | "that privacy is not a right guaranteed by the Indian Constitution is not reflective of the correct position. MP Sharma is overruled to the extent to .which it indicates to the contrary. 2 Kharak Singh has correctly held that the content of" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Tool reading: own-voice wording "is overruled"; attribution COURT_OWN_VOICE_UNBOUND_LEAD; opinion LEAD_OPINION (DR. D. Y. CHANDRACHUD; first opinion in the report); proposal OVERRULES.
- (b) Binding: LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.304)). Candidate target(s): AIR 1954 SC 300 (anchor at p.304). Raw target text: "MP Sharma"

**Affected research records.** None identified. C12 name scan of records_658.jsonl (658 records) for the source and target names of these leads (Ajmer Singh, Subramanian, Anand Singh Bisht, Mafatlal, Kanhaiyalal, Charanjit, C S Gill, C.S. Gill, Shatrughan, Vatheeswaran, Triveniben, Advocates-on-Record, Advocates on Record, SCAORA, Samsher, Sriharan, Puttaswamy, Jabalpur, Bhanudas, Kharak, M P Sharma, MP Sharma, M.P. Sharma, Joseph Shine, Sowmithri, Revathi, Rewathi, Kalyani, Saeed Siddiqui, Yogendra Kumar, Teri Oat): no match. Not in AFFECTED_RESEARCH_RECORDS.csv.

**Evidence still missing.**
- Human confirmation of the reading on the page image (text-layer copy; not a signed court copy).
- Resolution of the target citation to a held document (target_state UNRESOLVED).

### AQ-OVR-13: sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801 p.276: "is overruled"

**Priority:** P3. **Origin:** C11 adviser queue (30 rows).

**Question.** Is the quoted sentence (sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801, p.276) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The tool proposes OVERRULES for review only; the target binding is not established.

**Sources.**
- C11 TREATMENT_CANDIDATES.csv TC-a073b2e4fab8
- C11 GRAPH_SUMMARY.json treatment.adviser_rows
- C11 DISPOSITIONS_relations_c11.md (round 4 P3s)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| LEAD-TC-a073b2e4fab8 | sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801 p.276, para 185 | COURT_VOICE_OR_OPINION | "Maneka. Kharak Singh to the extent that it holds that the right to privacy is not protected under the Indian Constitution is overruled. 3 (A) Life and personal liberty are inalienable rights. These are rights which are inseparable from a" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Tool reading: own-voice wording "is overruled"; attribution COURT_OWN_VOICE_UNBOUND_LEAD; opinion LEAD_OPINION (DR. D. Y. CHANDRACHUD; first opinion in the report); proposal OVERRULES.
- (b) Binding: LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.113)). Candidate target(s): (1964) 1 SCR 332 (anchor at p.113). Raw target text: "Kharak Singh to the extent that it holds that the right to privacy is not protected under the Indian Constitution"

**Affected research records.** None identified. C12 name scan of records_658.jsonl (658 records) for the source and target names of these leads (Ajmer Singh, Subramanian, Anand Singh Bisht, Mafatlal, Kanhaiyalal, Charanjit, C S Gill, C.S. Gill, Shatrughan, Vatheeswaran, Triveniben, Advocates-on-Record, Advocates on Record, SCAORA, Samsher, Sriharan, Puttaswamy, Jabalpur, Bhanudas, Kharak, M P Sharma, MP Sharma, M.P. Sharma, Joseph Shine, Sowmithri, Revathi, Rewathi, Kalyani, Saeed Siddiqui, Yogendra Kumar, Teri Oat): no match. Not in AFFECTED_RESEARCH_RECORDS.csv.

**Evidence still missing.**
- Human confirmation of the reading on the page image (text-layer copy; not a signed court copy).
- Resolution of the target citation to a held document (target_state UNRESOLVED).

### AQ-OVR-14: sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801 p.432: "stands over-ruled"

**Priority:** P3. **Origin:** C11 adviser queue (30 rows).

**Question.** Is the quoted sentence (sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801, p.432) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The tool proposes OVERRULES for review only; the target binding is not established.

**Sources.**
- C11 TREATMENT_CANDIDATES.csv TC-44e4cead92b0
- C11 GRAPH_SUMMARY.json treatment.adviser_rows
- C11 DISPOSITIONS_relations_c11.md (round 4 P3s)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| LEAD-TC-44e4cead92b0 | sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801 p.432, para 185 | COURT_VOICE_OR_OPINION | "terms: (i) The decision in M P Sharma which holds that the right to privacy is not protected by the Constitution stands over-ruled; (ii) The decision in Kharak Singh to the extent that it holds that the right to privacy is not protected" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Tool reading: own-voice wording "stands over-ruled"; attribution COURT_OWN_VOICE_UNBOUND_LEAD; opinion ORDER_OF_THE_COURT; proposal OVERRULES.
- (b) Binding: LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.379)). Candidate target(s): 1954 SCR 1077 (anchor at p.379). Raw target text: "isposed of in the following terms: (i) The decision in M P Sharma which holds that the right to privacy is not protected by the Constitution"

**Affected research records.** None identified. C12 name scan of records_658.jsonl (658 records) for the source and target names of these leads (Ajmer Singh, Subramanian, Anand Singh Bisht, Mafatlal, Kanhaiyalal, Charanjit, C S Gill, C.S. Gill, Shatrughan, Vatheeswaran, Triveniben, Advocates-on-Record, Advocates on Record, SCAORA, Samsher, Sriharan, Puttaswamy, Jabalpur, Bhanudas, Kharak, M P Sharma, MP Sharma, M.P. Sharma, Joseph Shine, Sowmithri, Revathi, Rewathi, Kalyani, Saeed Siddiqui, Yogendra Kumar, Teri Oat): no match. Not in AFFECTED_RESEARCH_RECORDS.csv.

**Evidence still missing.**
- Human confirmation of the reading on the page image (text-layer copy; not a signed court copy).
- Resolution of the target citation to a held document (target_state UNRESOLVED).

### AQ-OVR-15: sc-2018-justice-k-s-puttaswamy-retd-2018insc880 p.705: "does not lay down the correct law"

**Priority:** P3. **Origin:** C11 adviser queue (30 rows).

**Question.** Is the quoted sentence (sc-2018-justice-k-s-puttaswamy-retd-2018insc880, p.705) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The sentence sits in a separate or dissenting opinion, so the tool made no proposal.

**Sources.**
- C11 TREATMENT_CANDIDATES.csv TC-09b5d373b025, TC-b2a42bfe7a34
- C11 GRAPH_SUMMARY.json treatment.adviser_rows
- C11 DISPOSITIONS_relations_c11.md (round 4 P3s)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| LEAD-TC-09b5d373b025 | sc-2018-justice-k-s-puttaswamy-retd-2018insc880 p.705, para 448 | COURT_VOICE_OR_OPINION | "(RETD) v. UNION OF INDIA [ASHOK BHUSHAN, J.] Judge Bench judgment of this Court in Yogendra Kumar Jaiswal (supra) does not lay down the correct law. We, thus, conclude that the decision of the Speaker certifying the Aadhaar Bill as Money" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Tool reading: own-voice wording "does not lay down the correct law"; attribution SEPARATE_OPINION_LEAD; opinion SEPARATE_OPINION (ASHOK BHUSHAN; concurring or separate, page-header based); proposal none.
- (b) Binding: LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.641,90)). Candidate target(s): (2004) 2 SCC 130 (anchor at p.641); (2016) 3 SCC 183 (anchor at p.90). Raw target text: "705 JUSTICE K S PUTTASWAMY (RETD) v. UNION OF INDIA [ASHOK BHUSHAN, J.] Judge Bench judgment of this Court in Yogendra Kumar Jaiswal (supra)"
- (c) Per the C11 method, wording in a separate or dissenting opinion "does not itself overrule"; whether the bench majority adopted it is not determined by the tool.
- V13-03: the candidate for Mohd. Saeed Siddiqui is wrong; (2004) 2 SCC 130 is Teri Oat Estates. Match on the party name in the sentence.

**Affected research records.** None identified. C12 name scan of records_658.jsonl (658 records) for the source and target names of these leads (Ajmer Singh, Subramanian, Anand Singh Bisht, Mafatlal, Kanhaiyalal, Charanjit, C S Gill, C.S. Gill, Shatrughan, Vatheeswaran, Triveniben, Advocates-on-Record, Advocates on Record, SCAORA, Samsher, Sriharan, Puttaswamy, Jabalpur, Bhanudas, Kharak, M P Sharma, MP Sharma, M.P. Sharma, Joseph Shine, Sowmithri, Revathi, Rewathi, Kalyani, Saeed Siddiqui, Yogendra Kumar, Teri Oat): no match. Not in AFFECTED_RESEARCH_RECORDS.csv.

**Evidence still missing.**
- Human confirmation of the reading on the page image (text-layer copy; not a signed court copy).
- Resolution of the target citation to a held document (target_state UNRESOLVED).

### AQ-OVR-16: sc-2018-justice-k-s-puttaswamy-retd-2018insc880 p.820: "are overruled"

**Priority:** P3. **Origin:** C11 adviser queue (30 rows).

**Question.** Is the quoted sentence (sc-2018-justice-k-s-puttaswamy-retd-2018insc880, p.820) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The sentence sits in a separate or dissenting opinion, so the tool made no proposal.

**Sources.**
- C11 TREATMENT_CANDIDATES.csv TC-50aa07ffde85, TC-60023f729c47
- C11 GRAPH_SUMMARY.json treatment.adviser_rows
- C11 DISPOSITIONS_relations_c11.md (round 4 P3s)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| LEAD-TC-50aa07ffde85 | sc-2018-justice-k-s-puttaswamy-retd-2018insc880 p.820, para 448 | COURT_VOICE_OR_OPINION | "[2018] 8 S.C.R. The three judge Bench decision in Mohd Saeed Siddiqui and the two judge Bench decision in Yogendra Kumar are overruled. 83. Barring judicial review of the Lok Sabha Speaker’s decision would render a certification of a Bill as a" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Tool reading: own-voice wording "are overruled"; attribution DISSENT_OPINION_LEAD; opinion DISSENT (DR. D. Y. CHANDRACHUD); proposal none.
- (b) Binding: LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.703,90)). Candidate target(s): (2014) 11 SCC 415 (anchor at p.703); (2016) 3 SCC 183 (anchor at p.90). Raw target text: "PREME COURT REPORTS [2018] 8 S.C.R. The three judge Bench decision in Mohd Saeed Siddiqui and the two judge Bench decision in Yogendra Kumar"
- (c) Per the C11 method, wording in a separate or dissenting opinion "does not itself overrule"; whether the bench majority adopted it is not determined by the tool.

**Affected research records.** None identified. C12 name scan of records_658.jsonl (658 records) for the source and target names of these leads (Ajmer Singh, Subramanian, Anand Singh Bisht, Mafatlal, Kanhaiyalal, Charanjit, C S Gill, C.S. Gill, Shatrughan, Vatheeswaran, Triveniben, Advocates-on-Record, Advocates on Record, SCAORA, Samsher, Sriharan, Puttaswamy, Jabalpur, Bhanudas, Kharak, M P Sharma, MP Sharma, M.P. Sharma, Joseph Shine, Sowmithri, Revathi, Rewathi, Kalyani, Saeed Siddiqui, Yogendra Kumar, Teri Oat): no match. Not in AFFECTED_RESEARCH_RECORDS.csv.

**Evidence still missing.**
- Human confirmation of the reading on the page image (text-layer copy; not a signed court copy).
- Resolution of the target citation to a held document (target_state UNRESOLVED).

### AQ-OVR-17: sc-2018-justice-k-s-puttaswamy-retd-2018insc880 p.1065: "are accordingly overruled"

**Priority:** P3. **Origin:** C11 adviser queue (30 rows).

**Question.** Is the quoted sentence (sc-2018-justice-k-s-puttaswamy-retd-2018insc880, p.1065) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The sentence sits in a separate or dissenting opinion, so the tool made no proposal.

**Sources.**
- C11 TREATMENT_CANDIDATES.csv TC-19f0e5a3af63, TC-bd7606d4e30b
- C11 GRAPH_SUMMARY.json treatment.adviser_rows
- C11 DISPOSITIONS_relations_c11.md (round 4 P3s)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| LEAD-TC-19f0e5a3af63 | sc-2018-justice-k-s-puttaswamy-retd-2018insc880 p.1065, para 448 | COURT_VOICE_OR_OPINION | "Articles 110(3) and 199(3) is not immune from judicial review. The decisions in Mohd Saeed Siddiqui and Yogendra Kumar are accordingly overruled. (d) The existence of and the role of the Rajya Sabha, as an institution of federal bicameralism" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Tool reading: own-voice wording "are accordingly overruled"; attribution SEPARATE_OPINION_LEAD; opinion SEPARATE_OPINION (ASHOK BHUSHAN; concurring or separate, page-header based); proposal none.
- (b) Binding: LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.703,90)). Candidate target(s): (2016) 3 SCC 183 (anchor at p.90); (2014) 11 SCC 415 (anchor at p.703). Raw target text: "The decisions in Mohd Saeed Siddiqui and Yogendra Kumar"
- (c) Per the C11 method, wording in a separate or dissenting opinion "does not itself overrule"; whether the bench majority adopted it is not determined by the tool.
- V13-02: p.1065 is Chandrachud J.'s dissent, not Bhushan J.'s opinion (bracketed footer preferred to running header).

**Affected research records.** None identified. C12 name scan of records_658.jsonl (658 records) for the source and target names of these leads (Ajmer Singh, Subramanian, Anand Singh Bisht, Mafatlal, Kanhaiyalal, Charanjit, C S Gill, C.S. Gill, Shatrughan, Vatheeswaran, Triveniben, Advocates-on-Record, Advocates on Record, SCAORA, Samsher, Sriharan, Puttaswamy, Jabalpur, Bhanudas, Kharak, M P Sharma, MP Sharma, M.P. Sharma, Joseph Shine, Sowmithri, Revathi, Rewathi, Kalyani, Saeed Siddiqui, Yogendra Kumar, Teri Oat): no match. Not in AFFECTED_RESEARCH_RECORDS.csv.

**Evidence still missing.**
- Human confirmation of the reading on the page image (text-layer copy; not a signed court copy).
- Resolution of the target citation to a held document (target_state UNRESOLVED).

### AQ-OVR-18: sc-2018-joseph-shine-2018insc898 p.74: "stand overruled"

**Priority:** P3. **Origin:** C11 adviser queue (30 rows).

**Question.** Is the quoted sentence (sc-2018-joseph-shine-2018insc898, p.74) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The tool proposes OVERRULES for review only; the target binding is not established.

**Sources.**
- C11 TREATMENT_CANDIDATES.csv TC-3c0fb3f2e38a, TC-8682d402357c
- C11 GRAPH_SUMMARY.json treatment.adviser_rows
- C11 DISPOSITIONS_relations_c11.md (round 4 P3s)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| LEAD-TC-3c0fb3f2e38a | sc-2018-joseph-shine-2018insc898 p.74, para 57 | COURT_VOICE_OR_OPINION | "the same path. 57. In view of the foregoing analysis, the decisions in Sowmithri Vishnu (supra) and V. Revathi (supra) stand overruled and any other judgment following precedents also stands overruled. 58. Consequently, the writ petition is" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Tool reading: own-voice wording "stand overruled"; attribution COURT_OWN_VOICE_UNBOUND_LEAD; opinion LEAD_OPINION (DIPAK MISRA; first opinion in the report); proposal OVERRULES.
- (b) Binding: LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.27,36)). Candidate target(s): 1985 Supp SCC 137 (anchor at p.27); (1988) 2 SCC 72 (anchor at p.36). Raw target text: "In view of the foregoing analysis, the decisions in Sowmithri Vishnu (supra) and V. Revathi (supra)"

**Affected research records.** None identified. C12 name scan of records_658.jsonl (658 records) for the source and target names of these leads (Ajmer Singh, Subramanian, Anand Singh Bisht, Mafatlal, Kanhaiyalal, Charanjit, C S Gill, C.S. Gill, Shatrughan, Vatheeswaran, Triveniben, Advocates-on-Record, Advocates on Record, SCAORA, Samsher, Sriharan, Puttaswamy, Jabalpur, Bhanudas, Kharak, M P Sharma, MP Sharma, M.P. Sharma, Joseph Shine, Sowmithri, Revathi, Rewathi, Kalyani, Saeed Siddiqui, Yogendra Kumar, Teri Oat): no match. Not in AFFECTED_RESEARCH_RECORDS.csv.

**Evidence still missing.**
- Human confirmation of the reading on the page image (text-layer copy; not a signed court copy).
- Resolution of the target citation to a held document (target_state UNRESOLVED).

### AQ-OVR-19: sc-2018-joseph-shine-2018insc898 p.100: "we overrule"

**Priority:** P3. **Origin:** C11 adviser queue (30 rows).

**Question.** Is the quoted sentence (sc-2018-joseph-shine-2018insc898, p.100) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The sentence sits in a separate or dissenting opinion, so the tool made no proposal.

**Sources.**
- C11 TREATMENT_CANDIDATES.csv TC-29a337ba9c11
- C11 GRAPH_SUMMARY.json treatment.adviser_rows
- C11 DISPOSITIONS_relations_c11.md (round 4 P3s)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| LEAD-TC-29a337ba9c11 | sc-2018-joseph-shine-2018insc898 p.100, para 58 | COURT_VOICE_OR_OPINION | "have seen that marital stability is not the object for which this provision was enacted. On all these counts, therefore, we overrule the judgment in Sowmithri Vishnu (supra). Equally, the judgment in V. Revathi (supra), which upheld the" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Tool reading: own-voice wording "we overrule"; attribution SEPARATE_OPINION_LEAD; opinion SEPARATE_OPINION (R. F. NARIMAN; concurring or separate, page-header based); proposal none.
- (b) Binding: LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.27)). Candidate target(s): 1985 Supp SCC 137 (anchor at p.27). Raw target text: "Sowmithri Vishnu"
- (c) Per the C11 method, wording in a separate or dissenting opinion "does not itself overrule"; whether the bench majority adopted it is not determined by the tool.

**Affected research records.** None identified. C12 name scan of records_658.jsonl (658 records) for the source and target names of these leads (Ajmer Singh, Subramanian, Anand Singh Bisht, Mafatlal, Kanhaiyalal, Charanjit, C S Gill, C.S. Gill, Shatrughan, Vatheeswaran, Triveniben, Advocates-on-Record, Advocates on Record, SCAORA, Samsher, Sriharan, Puttaswamy, Jabalpur, Bhanudas, Kharak, M P Sharma, MP Sharma, M.P. Sharma, Joseph Shine, Sowmithri, Revathi, Rewathi, Kalyani, Saeed Siddiqui, Yogendra Kumar, Teri Oat): no match. Not in AFFECTED_RESEARCH_RECORDS.csv.

**Evidence still missing.**
- Human confirmation of the reading on the page image (text-layer copy; not a signed court copy).
- Resolution of the target citation to a held document (target_state UNRESOLVED).

### AQ-OVR-20: sc-2018-joseph-shine-2018insc898 p.109: "is overruled"

**Priority:** P3. **Origin:** C11 adviser queue (30 rows).

**Question.** Is the quoted sentence (sc-2018-joseph-shine-2018insc898, p.109) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The sentence sits in a separate or dissenting opinion, so the tool made no proposal.

**Sources.**
- C11 TREATMENT_CANDIDATES.csv TC-a272984ee636
- C11 GRAPH_SUMMARY.json treatment.adviser_rows
- C11 DISPOSITIONS_relations_c11.md (round 4 P3s)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| LEAD-TC-a272984ee636 | sc-2018-joseph-shine-2018insc898 p.109, para 58 | COURT_VOICE_OR_OPINION | "decision in Sowmithri Vishnu cannot be regarded as a correct exposition of the constitutional position. Sowmithri Vishnu is overruled. 12. The decision of a two judge Bench in V Revathi v Union of India17 involved a challenge to Section 497" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Tool reading: own-voice wording "is overruled"; attribution SEPARATE_OPINION_LEAD; opinion SEPARATE_OPINION (DR. D. Y. CHANDRACHUD; concurring or separate, page-header based); proposal none.
- (b) Binding: LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.27)). Candidate target(s): 1985 Supp SCC 137 (anchor at p.27). Raw target text: "Sowmithri Vishnu"
- (c) Per the C11 method, wording in a separate or dissenting opinion "does not itself overrule"; whether the bench majority adopted it is not determined by the tool.

**Affected research records.** None identified. C12 name scan of records_658.jsonl (658 records) for the source and target names of these leads (Ajmer Singh, Subramanian, Anand Singh Bisht, Mafatlal, Kanhaiyalal, Charanjit, C S Gill, C.S. Gill, Shatrughan, Vatheeswaran, Triveniben, Advocates-on-Record, Advocates on Record, SCAORA, Samsher, Sriharan, Puttaswamy, Jabalpur, Bhanudas, Kharak, M P Sharma, MP Sharma, M.P. Sharma, Joseph Shine, Sowmithri, Revathi, Rewathi, Kalyani, Saeed Siddiqui, Yogendra Kumar, Teri Oat): no match. Not in AFFECTED_RESEARCH_RECORDS.csv.

**Evidence still missing.**
- Human confirmation of the reading on the page image (text-layer copy; not a signed court copy).
- Resolution of the target citation to a held document (target_state UNRESOLVED).

### AQ-OVR-21: sc-2018-joseph-shine-2018insc898 p.154: "are overruled"

**Priority:** P3. **Origin:** C11 adviser queue (30 rows).

**Question.** Is the quoted sentence (sc-2018-joseph-shine-2018insc898, p.154) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The sentence sits in a separate or dissenting opinion, so the tool made no proposal.

**Sources.**
- C11 TREATMENT_CANDIDATES.csv TC-235c7582ce78, TC-387c984f74dc
- C11 GRAPH_SUMMARY.json treatment.adviser_rows
- C11 DISPOSITIONS_relations_c11.md (round 4 P3s)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| LEAD-TC-235c7582ce78 | sc-2018-joseph-shine-2018insc898 p.154, para 67 | COURT_VOICE_OR_OPINION | "to Article 21 of the Constitution; and 4) Section 497 is unconstitutional. The decisions in Sowmithri Vishnu and Revathi are overruled. INDU MALHOTRA, J. 1. The present Writ Petition has been filed to challenge the constitutional validity of" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Tool reading: own-voice wording "are overruled"; attribution SEPARATE_OPINION_LEAD; opinion SEPARATE_OPINION (DR. D. Y. CHANDRACHUD; concurring or separate, page-header based); proposal none.
- (b) Binding: LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.27,36)). Candidate target(s): (1988) 2 SCC 72 (anchor at p.36); 1985 Supp SCC 137 (anchor at p.27). Raw target text: "The decisions in Sowmithri Vishnu and Revathi"
- (c) Per the C11 method, wording in a separate or dissenting opinion "does not itself overrule"; whether the bench majority adopted it is not determined by the tool.

**Affected research records.** None identified. C12 name scan of records_658.jsonl (658 records) for the source and target names of these leads (Ajmer Singh, Subramanian, Anand Singh Bisht, Mafatlal, Kanhaiyalal, Charanjit, C S Gill, C.S. Gill, Shatrughan, Vatheeswaran, Triveniben, Advocates-on-Record, Advocates on Record, SCAORA, Samsher, Sriharan, Puttaswamy, Jabalpur, Bhanudas, Kharak, M P Sharma, MP Sharma, M.P. Sharma, Joseph Shine, Sowmithri, Revathi, Rewathi, Kalyani, Saeed Siddiqui, Yogendra Kumar, Teri Oat): no match. Not in AFFECTED_RESEARCH_RECORDS.csv.

**Evidence still missing.**
- Human confirmation of the reading on the page image (text-layer copy; not a signed court copy).
- Resolution of the target citation to a held document (target_state UNRESOLVED).

### AQ-OVR-22: sc-2018-joseph-shine-2018insc898 p.186: "hereby stand overruled"

**Priority:** P3. **Origin:** C11 adviser queue (30 rows).

**Question.** Is the quoted sentence (sc-2018-joseph-shine-2018insc898, p.186) the court's own treatment of a prior decision, which decision(s) does it refer to, and should any typed edge (overrules / partly overrules / none) be recorded? The sentence sits in a separate or dissenting opinion, so the tool made no proposal.

**Sources.**
- C11 TREATMENT_CANDIDATES.csv TC-0b27a3830ff7, TC-48e2ff70f085
- C11 GRAPH_SUMMARY.json treatment.adviser_rows
- C11 DISPOSITIONS_relations_c11.md (round 4 P3s)

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| LEAD-TC-0b27a3830ff7 | sc-2018-joseph-shine-2018insc898 p.186, para 67 | COURT_VOICE_OR_OPINION | "of Adultery under Section 497. (iii) The decisions in Sowmithri Vishnu (supra), V. Rewathi(supra) and W. Kalyani(supra) hereby stand overruled. Kalpana K. Tripathy Writ Petition allowed." | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Tool reading: own-voice wording "hereby stand overruled"; attribution SEPARATE_OPINION_LEAD; opinion SEPARATE_OPINION (INDU MALHOTRA; concurring or separate, page-header based); proposal none.
- (b) Binding: LEAD (RAW_NAME_MATCHES_CITATION_ELSEWHERE_IN_JUDGMENT (p.27,36)). Candidate target(s): 1985 Supp SCC 137 (anchor at p.27); (2012) 1 SCC 358 (anchor at p.36). Raw target text: "(iii) The decisions in Sowmithri Vishnu (supra), V. Rewathi(supra) and W. Kalyani(supra)"
- (c) Per the C11 method, wording in a separate or dissenting opinion "does not itself overrule"; whether the bench majority adopted it is not determined by the tool.

**Affected research records.** None identified. C12 name scan of records_658.jsonl (658 records) for the source and target names of these leads (Ajmer Singh, Subramanian, Anand Singh Bisht, Mafatlal, Kanhaiyalal, Charanjit, C S Gill, C.S. Gill, Shatrughan, Vatheeswaran, Triveniben, Advocates-on-Record, Advocates on Record, SCAORA, Samsher, Sriharan, Puttaswamy, Jabalpur, Bhanudas, Kharak, M P Sharma, MP Sharma, M.P. Sharma, Joseph Shine, Sowmithri, Revathi, Rewathi, Kalyani, Saeed Siddiqui, Yogendra Kumar, Teri Oat): no match. Not in AFFECTED_RESEARCH_RECORDS.csv.

**Evidence still missing.**
- Human confirmation of the reading on the page image (text-layer copy; not a signed court copy).
- Resolution of the target citation to a held document (target_state UNRESOLVED).

## 6. Disputed statutory edges and commencement

Basis: C10 `amendment_graph_c10.csv` (116 edges: DISPUTED_PRESERVE_BOTH 15, EVIDENCED 17, NOT_LOCATED 41, UNRESOLVED_COMMENCEMENT 43), C10 `escalation_matters_c10.csv` (9 matters), and the C9 escalation files. All 15 DISPUTED_PRESERVE_BOTH edges and all 43 UNRESOLVED_COMMENCEMENT edges are covered by AQ-STA-01 to AQ-STA-21 (see the coverage table at the end of this section). Readings are preserved, not resolved. A compilation "w.e.f." note is a compiler statement, and a publication date is never assumed to be a commencement date (C10 evidence rule).

### AQ-STA-01: Army Rule 23(3) caution wording

**Priority:** P0. **Origin:** C9 ESC-03 (P0, reserved RES-r23(3)); C10 ESC-R23-3.

**Question.** Does the adviser accept the archival facsimile of the Gazette of 27-11-1954 (S.R.O. 484, printed p.300) as evidence of the notified text of r.23(3) pending a certified copy; is the amendment search sufficient given the remaining gaps; may the interim wording C9-CP-B01 to B06 (which quotes both versions and adopts neither) be displayed; and is the accused's right not to make a statement secured independently of r.23(3) (for example by Art. 20(3)), which C9 has not checked?

**Sources.**
- C10 amendment_graph_c10.csv C9-AG-RES-C-01, C9-AG-RES-U-01
- C10 escalation_matters_c10.csv ESC-R23-3 (status: ESCALATED_TO_LEGAL_ADVISER (conflict C-01 CONFLICTING, retained until legal review))
- C9 LEGAL_ADVISER_ESCALATION.md ESC-03
- C9 UNRESOLVED_MATTERS.md U-2
- Edge statuses (C10): DISPUTED_PRESERVE_BOTH. Decision owner: qualified legal adviser. Edges: C9-AG-RES-C-01, C9-AG-RES-U-01.

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| C9R-R23-GAZ | Gazette 27-11-1954 (S.R.O. 484) archival facsimile c5ef95a9, PDF p.10, r.23(3) | STATUTE_GAZETTE | "You are not obliged to say anything unless you wish to do so" (printed p.300; facsimile is working-store only; not in the text layer) | not re-verifiable here (no text file at ad77758d; carried from C9 ESC-03 / C10 ESC-R23-3) |
| C9R-R23-COMP | rules-army-rules-1954 p.41, r.23(3) | STATUTE_COMPILATION | "You are obliged to say anything unless you wish to do so" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Gazette of 27-11-1954 (facsimile c5ef95a9, printed p.300) and MML copies: "You are not obliged to say anything unless you wish to do so".
- (b) India Code compilation (48f52219) p.41: "You are obliged to say anything unless you wish to do so".
- C9 records the omission of "not" as a probable transcription discrepancy, not a determined fact; the procedure limbs of r.23(3) read the same in both. Remaining gaps: E-7 of 17-06-1960, 17 S.R.O.s of 1960-1991 not located, S.R.O. 258/2002, S.R.O. 2(E)/2018, anything after 06-06-2022.

**Affected research records.** HCE-010; V9-SC-19; EV-016; KB-006; V9-CL-04; V9-WF-05

**Evidence still missing.**
- A certified copy of S.R.O. 484/1954; the gap instruments, image-checked (C9 ESC-04; U-2).
- The Gazette facsimile is working-store only (PRESERVATION_RISK, C10).

### AQ-STA-02: Unsupported statement that r.23 was amended in 2022

**Priority:** P2. **Origin:** C10 ESC-R23-2022; C9 U-2.

**Question.** Can the adviser confirm that the earlier research statement "r.23 amended 2022" is not to be relied on, and decide what search is needed to close it?

**Sources.**
- C10 amendment_graph_c10.csv (no edge)
- C10 escalation_matters_c10.csv ESC-R23-2022 (status: OPEN_UNSUPPORTED: not to be relied on; closure needs the post-06-06-2022 S.R.O.s (10 pinned candidates), E-7/1960, S.R.O. 258/2002 and the AR hints image-checked; legal adviser on C-01)
- C9 UNRESOLVED_MATTERS.md U-2

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Registers: no instrument amends r.23 (31 instruments 1960-2022); S.R.O. 6(E)/2022 amends r.16A(4) only; C8 review RC-01 removed the claim from EV-016, HCE-010 and SC03.
- (b) The earlier statement (no supporting instrument ever identified). Status OPEN_UNSUPPORTED.

**Affected research records.** EV-016; HCE-010; SC03

**Evidence still missing.**
- The post-06-06-2022 S.R.O.s (10 pinned candidates), E-7/1960, S.R.O. 258/2002 and the AR hints, image-checked.
- No held copy in HF/GitHub of any post-2022 Army Rules instrument (C10).

### AQ-STA-03: Army Rule 168(2) field-punishment words

**Priority:** P2. **Origin:** C10 ESC-R168-2; C9 U-5.

**Question.** Which text of r.168(2) is current: the India Code compilation, which still prints the field-punishment words, or S.R.O. 17(E)/1993 item 31, which omits them? (Owner first to register the conflict.)

**Sources.**
- C10 amendment_graph_c10.csv C9-AG-AR168
- C10 escalation_matters_c10.csv ESC-R168-2 (status: OWNER_TO_REGISTER_CONFLICT then LEGAL_ADVISER (not in any conflict register))
- C9 UNRESOLVED_MATTERS.md U-5
- Edge statuses (C10): DISPUTED_PRESERVE_BOTH. Decision owner: owner (register as conflict) then legal adviser. Edges: C9-AG-AR168.

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| C9R-AR-01 | rules-army-rules-1954 p.189, r.168(2) | STATUTE_COMPILATION | "or until the completion of the field punishment, unless such field punishment is remitted by a competent authority" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) S.R.O. 17(E)/1993 item 31 omits the words [C9R-AR-02 [held sha256 e9bf2114ab633716 p.17]]
- (b) compilation r.168(2) still prints them [C9R-AR-01 [held sha256 48f52219121bf74d p.189]]
- Context recorded in C9 U-5: field punishment (AA ss.75-76) was omitted by Act 37/1992 (see AQ-STA-06). Not in any conflict register.

**Affected research records.** (none listed in the C9/C10 artefacts)

**Evidence still missing.**
- The 1993 Gazette copy is working-store only (PRESERVATION_RISK).
- S.R.O. 331/1960 (also r.168(2)) is LOCATED_NOT_ACQUIRED.

### AQ-STA-04: S.R.O. 34 of 1963 identity and the S.R.O. 240/1955 date

**Priority:** P3. **Origin:** C10 ESC-SRO34-1963; C9 U-1.

**Question.** After the June-July 1963 Gazette issues are searched: is the held S.R.O. 34 of 05-01-1963 (a r.188(e) declaration) the instrument that later notes list among amendments as "SRO 34 dated 5 Jun 63", and does that affect the amendment chain? Which date of S.R.O. 240/1955 is correct (low consequence)?

**Sources.**
- C10 amendment_graph_c10.csv C9-AG-AR-008, C9-AG-SRO240-1955
- C10 escalation_matters_c10.csv ESC-SRO34-1963 (status: OWNER_DISCOVERY_APPROVAL_PENDING (AP-C9-05: June-July 1963 Part II-S4 issues) then LEGAL_ADVISER)
- C9 UNRESOLVED_MATTERS.md U-1
- Edge statuses (C10): DISPUTED_PRESERVE_BOTH. Decision owner: owner / legal adviser after the 1963 Gazette issues are searched. Edges: C9-AG-AR-008, C9-AG-SRO240-1955.

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) held S.R.O. 34 dated 05-01-1963 is a r.188(e) declaration (C8-PIC-03)
- (b) Gazette-printed NOTEs list 'SRO 34 dated 5 Jun 63' among amendments of the Rules (C8-CR-02); S.R.O. 2(E)/2018 lists 'S.R.O. 34 dated 05th January, 1963'
- S.R.O. 240/1955: (a) S.R.O. 34/1963 recites 'SRO 240, dated the 25th June, 1955' vs (b) S.R.O. 2(E)/2018 Note lists 'S.R.O. 240 dated 05th June, 1955'

**Affected research records.** (none listed in the C9/C10 artefacts)

**Evidence still missing.**
- Part II-S4 issues of June-July 1963 (discovery approval AP-C9-05).
- Held copy 4acdb1a8 is working-store only.

### AQ-STA-05: S.O. 4010/1986 (CCCM Rules amendment) date

**Priority:** P3. **Origin:** C10 ESC-SO4010-1986; C9 U-4.

**Question.** Which date is that of the 1986 MHA notification S.O. 4010 amending the Criminal Courts and Court-Martial (Adjustment of Jurisdiction) Rules 1978? (Owner decision after a page check of the record copy.)

**Sources.**
- C10 amendment_graph_c10.csv C9-AG-CCCM-SO4010
- C10 escalation_matters_c10.csv ESC-SO4010-1986 (status: OWNER_ACQUISITION_EXECUTION_PENDING (AP-C9-01, PR #8 authorised scope) then page check)
- C9 UNRESOLVED_MATTERS.md U-4
- Edge statuses (C10): DISPUTED_PRESERVE_BOTH. Decision owner: owner after PR #8 record copy is image-checked. Edges: C9-AG-CCCM-SO4010.

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) RS papers-laid record: 'S.O. No. 4010, dated the 6th December, 1986' [C9R-RS-01 [held sha256 fa51a4b132c409ed p.1; render sha256 88cf5a512f6d8446]]
- (b) PILOT-01 T5-02 / ACQ-01: notification dated 24-11-1986, Gazette 06-12-1986 pp.4881-82 (archive item read during discovery; not held)
- (c) C5 RV-01 transcription '8 Dec 1986' (contradicted by the C9 page-image read; human re-check)

**Affected research records.** (none listed in the C9/C10 artefacts)

**Evidence still missing.**
- The notification itself (PR #8 scope, AP-C9-01); a page-image check of the record copy.

### AQ-STA-06: Commencement of Army (Amendment) Act 37 of 1992

**Priority:** P1. **Origin:** C10 ESC-ACT37-1992; C9 U-3; CLAUDE.md known supersession cases (field punishment, s.127).

**Question.** What is the commencement date of the Army (Amendment) Act 1992 (37 of 1992), which prints no commencement clause (AQ-05: effect of an Act with no commencement clause), and therefore of the 18 Army Act provisions it changed (including the omission of field punishment, ss.75-76, and of s.127)?

**Sources.**
- C10 amendment_graph_c10.csv C9-AG-AA-08-s2, C9-AG-AA-08-s3, C9-AG-AA-08-s4, C9-AG-AA-08-s5, C9-AG-AA-08-s6, C9-AG-AA-08-s7, C9-AG-AA-08-s8, C9-AG-AA-08-s9, C9-AG-AA-08-s10, C9-AG-AA-08-s11, C9-AG-AA-08-s12, C9-AG-AA-08-s13, C9-AG-AA-08-s14, C9-AG-AA-08-s15, C9-AG-AA-08-s16, C9-AG-AA-08-s17, C9-AG-AA-08-s18, C9-AG-AA-08-s19
- C10 escalation_matters_c10.csv ESC-ACT37-1992 (status: ESCALATED_TO_LEGAL_ADVISER (AQ-05: effect of an Act without a commencement clause); optional 1992 Gazette check)
- C9 UNRESOLVED_MATTERS.md U-3
- C10 STATUTORY_C10_FINDINGS.md (ESCALATED_TO_LEGAL_ADVISER (AQ-05))
- Edge statuses (C10): UNRESOLVED_COMMENCEMENT. Decision owner: legal adviser (AQ-05). Edges: C9-AG-AA-08-s2, C9-AG-AA-08-s3, C9-AG-AA-08-s4, C9-AG-AA-08-s5, C9-AG-AA-08-s6, C9-AG-AA-08-s7, C9-AG-AA-08-s8, C9-AG-AA-08-s9, C9-AG-AA-08-s10, C9-AG-AA-08-s11, C9-AG-AA-08-s12, C9-AG-AA-08-s13, C9-AG-AA-08-s14, C9-AG-AA-08-s15, C9-AG-AA-08-s16, C9-AG-AA-08-s17, C9-AG-AA-08-s18, C9-AG-AA-08-s19.

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| C9R-AA-03a | act-army-1950 p.27, ss.75-76 | STATUTE_COMPILATION | "Omitted by the Army (Amendment) Act, 1992 (37 of 1992), s. 2 (w.e.f. 6-9-1992)." (compiler statement only; Act 37/1992 prints no commencement clause) | verified (stated page) |
| C9R-AA-03b | act-army-1950 p.36, s.127 | STATUTE_COMPILATION | "Omitted by the Army (Amendment) Act, 1992 (37 of 1992), s. 11 (w.e.f. 6-9-1992)" | verified (stated page) |
| C9R-AA-03c | act-army-1950 p.48, Ch XVI | STATUTE_COMPILATION | "Omitted by the Army (Amendment) Act, 1992 (37 of 1992), s. 19 (w.e.f. 6-9-1992)." | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Gazette scan f11d443e: assent 06-09-1992, Gazette No.59 of 07-09-1992, no commencement clause.
- (b) The compilation prints "w.e.f. 6-9-1992" only at ss.75-76, s.127 and Ch XVI; the other provisions carry undated footnotes. Compiler statements only; no date inferred.

**Affected research records.** CM-011; CM-012 (version notes; see AQ-STA-07)

**Evidence still missing.**
- Adviser answer to AQ-05; optionally a check of the 1992 Gazette for any notification or corrigendum.
- All three Act 37/1992 copies are working-store only (PRESERVATION_RISK).

### AQ-STA-07: Army Act ss.122-123 limitation (CM-011, CM-012)

**Priority:** P1. **Origin:** C9 ESC-05 (LAQ-05, AQ-05).

**Question.** Is "Apply the earliest relevant knowledge rule in Section 122(1)" a P1 misdescription or a P2 drafting ambiguity, and may the statute-tracking wording C9-CP-D01 replace it? Do s.122 and s.123(2) apply cumulatively to a person who has ceased to be subject to the Act? Which version applies where the offence or cessation preceded Act 37 of 1992?

**Sources.**
- C10 amendment_graph_c10.csv (no edge)
- C9 LEGAL_ADVISER_ESCALATION.md ESC-05

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) F-PROC-006 first pass: P1 misdescription.
- (b) Reviewer A (adopted provisionally, PILOT-01 D-05): P2 drafting ambiguity.
- C9 reads compilation e47a4265 p.35: s.122(1)(a) is the default starting point; (b) and (c) are conditional with "whichever is earlier" within each; s.123(2) sets three years after cessation with exclusions; footnotes record substitution by Act 37/1992 ss.9-10. CM-011 omits s.123(2) (F-PROC-007, P1, upheld).

**Affected research records.** CM-011; CM-012

**Evidence still missing.**
- Decision on AQ-STA-06 (Act 37/1992 commencement).

### AQ-STA-08: AFT Act commencement vs establishment of the Tribunal

**Priority:** P2. **Origin:** C10 ESC-AFT-COMMENCEMENT.

**Question.** How do the AFT Act s.1(2) commencement (compilation footnote: 15-06-2008 by S.O. 14(E) of 13-06-2008, notification not held) and the establishment of the Tribunal w.e.f. 10-08-2009 (S.R.O. 9(E) of 07-08-2009, held) relate?

**Sources.**
- C10 amendment_graph_c10.csv C9-AG-AFT-00, C9-AG-AFTSRO9E2009
- C10 escalation_matters_c10.csv ESC-AFT-COMMENCEMENT (status: OWNER_DISCOVERY_APPROVAL_PENDING (AP-C9-05) for S.O. 14(E)/2008; LEGAL_ADVISER on the relationship of the two dates)
- Edge statuses (C10): EVIDENCED, NOT_LOCATED. Decision owner: owner (discovery) then legal adviser. Edges: C9-AG-AFT-00, C9-AG-AFTSRO9E2009.

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Compilation footnote to s.1(2): commencement 15-06-2008 vide S.O. 14(E) dated 13-06-2008 (notification not held)
- (b) S.R.O. 9(E) of 07-08-2009 establishes the Tribunal w.e.f. 10-08-2009 (held 8d774f1f, 03961b02); a different event, not s.1(2) commencement
- C10: S.R.O. 14(E) of 21-10-2009 (bench jurisdiction) is a number collision, not the s.1(2) notification. Both readings preserved.

**Affected research records.** (none listed in the C9/C10 artefacts)

**Evidence still missing.**
- S.O. 14(E)/2008 (discovery approval AP-C9-05).

### AQ-STA-09: AFT procedural rules commencement

**Priority:** P3. **Origin:** C10 ESC-AFT-PROC-RULES.

**Question.** May the AFT Procedure Rules 2008, Amendment Rules 2011 and Practice Rules 2009 (held, unregistered) be registered, and on what evidence is the Practice Rules 2009 commencement ("from the date of publication in the official gazette") to be fixed, given that the publication date is not on the held pages?

**Sources.**
- C10 amendment_graph_c10.csv C9-AG-AFTPRAC2009, C9-AG-AFT-05
- C10 escalation_matters_c10.csv ESC-AFT-PROC-RULES (status: OWNER_REGISTRATION_DECISION_PENDING (AP-C9-02, revised) and optional ACQ03-032 masthead; no inference of publication date from the notification date)
- Edge statuses (C10): UNRESOLVED_COMMENCEMENT. Decision owner: owner (registration). Edges: C9-AG-AFTPRAC2009, C9-AG-AFT-05.

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Procedure Rules 2008 (S.R.O. 26(E), Gazette 17-09-2008) and Amendment Rules 2011 (S.R.O. 05(E), 29-07-2011): EVIDENCED in C9 from held Gazette pages
- (b) Practice Rules 2009 (S.R.O. 6(E) dated 11-05-2009): commence "from the date of publication in the official gazette"; publication date not on the held pages
- No inference of the publication date from the notification date (C9/C10).

**Affected research records.** (none listed in the C9/C10 artefacts)

**Evidence still missing.**
- Optional ACQ03-032 masthead; owner registration decision (AP-C9-02, revised).

### AQ-STA-10: AFT s.9A under the Finance Act 2017 and the Tribunals Reforms Act 2026

**Priority:** P2. **Origin:** C10 ESC-TRA2026-COMMENCEMENT; C9 U-5.

**Question.** From what date does AFT Act s.9A operate in its 2017 inserted form and in its 2026 substituted form, given that both amending Acts commence by notification (not held) and the compilation gives "w.e.f." dates; and what is the effect of the TRA 2026 repeal of the TRA 2021 with savings?

**Sources.**
- C10 amendment_graph_c10.csv C9-AG-AFT-01, C9-AG-AFT-03, C9-AG-AFT-04, C9-AG-TRA2021-REPEAL
- C10 escalation_matters_c10.csv ESC-TRA2026-COMMENCEMENT (status: OWNER_DISCOVERY_APPROVAL_PENDING (TRA 2026 notifications; no candidate))
- C9 UNRESOLVED_MATTERS.md U-5
- Edge statuses (C10): UNRESOLVED_COMMENCEMENT. Decision owner: owner (discovery) then legal adviser. Edges: C9-AG-AFT-01, C9-AG-AFT-03, C9-AG-AFT-04, C9-AG-TRA2021-REPEAL.

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| C9R-RD-FIN17-02 | act-the-finance-act-2017 p.53, s.156 | STATUTE_COMPILATION | "The provisions of this Part shall come into force on such date as the Central Government may, by notification in the Official Gazette, appoint" | verified (stated page) |
| C9R-AFT-05 | act-armed-forces-tribunal-2007 p.7, s.9A fn | STATUTE_COMPILATION | "Ins. by Act 7 of 2017, s. 181 (w.e.f. 26-5-2017)." (compiler statement only) | verified (stated page) |
| C9R-TRA-02 | act-the-tribunals-reforms-act-2026 p.1, s.1(2) | STATUTE_COMPILATION | "It shall come into force on such date as the Central Government may, by notification in the Official Gazette, appoint; and different dates may be appointed for different provisions of this Act" | verified (stated page) |
| C9R-AFT-06 | act-armed-forces-tribunal-2007 p.7, s.9A fn | STATUTE_COMPILATION | "Subs by Act 17 of 2026, s. 18 and Sch. II for section 9A (w.e.f. 25-08-2026)." (compiler statement only) | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Act: Part XIV by notification [C9R-RD-FIN17-02 [corpus raw store sha256 7a5551bab08518a7 p.53]] || (b) (b) compilation: 'w.e.f. 26-5-2017' [C9R-AFT-05 [held sha256 665863d1abb802f7 p.7]]
- (a) TRA 2026: commencement by notification [C9R-TRA-02 [held sha256 be619533e45739bf p.1]] || (b) (b) compilation: s.9A 'w.e.f. 25-08-2026' [C9R-AFT-06 [held sha256 665863d1abb802f7 p.7]]

**Affected research records.** (none listed in the C9/C10 artefacts)

**Evidence still missing.**
- The Finance Act 2017 Part XIV notification and the TRA 2026 commencement notification(s) (no candidate located).

### AQ-STA-11: Army Rules amending instruments with no commencement clause (AQ-05)

**Priority:** P2. **Origin:** C10 amendment_graph_c10.csv (AQ-05); C10 CORPUS_AUTHORITY_MATRIX.md section 3.

**Question.** On what date do the Army Rules 1954 (S.R.O. 484) and the amending S.R.O.s that print no commencement clause take effect (AQ-05)? Commencement is preserved as NOT_STATED_PENDING_ADVICE; no date is inferred.

**Sources.**
- C10 amendment_graph_c10.csv C9-AG-AR-000, C9-AG-AR-006, C9-AG-AR-007, C9-AG-AR-009, C9-AG-AR-010, C9-AG-AR-011, C9-AG-AR-014, C9-AG-AR-017, C9-AG-AR-018, C9-AG-AR-019, C9-AG-AR-020, C9-AG-AR-022, C9-AG-AR-023, C9-AG-AR-025
- Edge statuses (C10): UNRESOLVED_COMMENCEMENT. Decision owner: legal adviser (AQ-05). Edges: C9-AG-AR-000, C9-AG-AR-006, C9-AG-AR-007, C9-AG-AR-009, C9-AG-AR-010, C9-AG-AR-011, C9-AG-AR-014, C9-AG-AR-017, C9-AG-AR-018, C9-AG-AR-019, C9-AG-AR-020, C9-AG-AR-022, C9-AG-AR-023, C9-AG-AR-025.

**Competing readings (as recorded in the artefacts; no view is taken).**
- No competing readings recorded: each edge records "commencement not evidenced" (NOT_STATED_PENDING_ADVICE, AQ-05); the authority matrix states that a publication date is never assumed to be the commencement date (an evidence rule, not a statement of law).

**Affected research records.** (none listed in the C9/C10 artefacts)

**Evidence still missing.**
- Adviser answer to AQ-05.

### AQ-STA-12: Army Rule 182 as substituted by S.R.O. 17(E)/1993 item 36

**Priority:** P2. **Origin:** C10 amendment_graph_c10.csv; C5 conflict SC4-01.

**Question.** Which text of r.182 (proceedings of a court of inquiry not admissible) is operative: the 1993 substitution (S.R.O. 17(E)/1993 item 36) or the 1954 notified text, as compared with the compilation and MML 2?

**Sources.**
- C10 amendment_graph_c10.csv C9-AG-RES-SC4-01
- Edge statuses (C10): DISPUTED_PRESERVE_BOTH. Decision owner: qualified legal adviser (conflict register: legal_adviser_required). Edges: C9-AG-RES-SC4-01.

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| C12-AR182-COMP | rules-army-rules-1954 p.197, r.182 | STATUTE_COMPILATION | "nor shall any evidence respecting the proceedings of the court be given against any such person except upon the trial or such person for wilfully giving" (text layer prints 'trial or such person') | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Gazette of India Extraordinary Pt II s.4, 06-12-1993 (S.R.O. 17(E)/1993; archival facsimile) sha256=e9bf2114ab633716ea954db6e100be858e45949384f9fc0667364308bff46912 PDF p.18 (printed p.18) item 36: '...shall not be admissible in nor shall any evidence respecting the proceedings of the court be given against any such person except upon the trial of such person for wilfully giving false evidence ...
- (b) Army Rules 1954 as notified (S.R.O. 484/1954, Gazette 27-11-1954; archival facsimile); also India Code compilation p.197 and MML 2 p.222 (comparison only) sha256=c5ef95a9d553685aa655f041b71d8360d6272e2775a19a3d6e7273c6cbd0aca6 PDF p.51 (printed p.341) r.182: '...shall not be admissible in evidence against a person subject to the Act...' (no proviso in 1954) ...
- Status: OPEN (no corrigendum searched or located). C10 review CL-01 notes this edge does hold quoted readings.

**Affected research records.** (none listed in the C9/C10 artefacts)

**Evidence still missing.**
- A corrigendum search for S.R.O. 17(E)/1993.

### AQ-STA-13: Army Rule 192 proviso (reduction in pay grade)

**Priority:** P3. **Origin:** C10 amendment_graph_c10.csv; C5 conflict C-02.

**Question.** Which text of the r.192 proviso is operative (amending instrument vs official consolidation vs manual; manual footnote cites S.R.O. 215)?

**Sources.**
- C10 amendment_graph_c10.csv C9-AG-RES-C-02
- Edge statuses (C10): DISPUTED_PRESERVE_BOTH. Decision owner: qualified legal adviser (conflict register: legal_adviser_required). Edges: C9-AG-RES-C-02.

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) (a) Central Govt amending instrument; (b) official consolidation; (c) manual
- (b) (a) archival reproduction, identity/integrity checked by reviewer D (S-REVD-004); (b) as C-01; (c) user-supplied manual (footnote cites S.R.O. 215)

**Affected research records.** (none listed in the C9/C10 artefacts)

**Evidence still missing.**
- Itemised readings are not in the C5 conflict register; S.R.O. 215/1965 has no commencement clause (C9-AG-AR-011).

### AQ-STA-14: Army Rule 177(1)-(2) (Court of Inquiry)

**Priority:** P3. **Origin:** C10 amendment_graph_c10.csv; C5 conflict C-03.

**Question.** Which text of r.177(1)-(2) is operative? The conflict is CONFLICTING pending text comparison and legal review.

**Sources.**
- C10 amendment_graph_c10.csv C9-AG-RES-C-03
- Edge statuses (C10): DISPUTED_PRESERVE_BOTH. Decision owner: qualified legal adviser (conflict register: legal_adviser_required). Edges: C9-AG-RES-C-03.

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) (a) amending instrument; (b) consolidation; (c) manual
- (b) (a) archival reproduction, identity checked by reviewer D (S-REVD-008); (b) as C-01; (c) user-supplied manual

**Affected research records.** (none listed in the C9/C10 artefacts)

**Evidence still missing.**
- Text comparison (not yet done).

### AQ-STA-15: Army Rule 193 (prescribed officer, AA s.90(i) and s.91(i))

**Priority:** P2. **Origin:** C10 amendment_graph_c10.csv; C5 conflicts C-08, U-04, U-07.

**Question.** Does r.193 cover s.90(i) as well as s.91(i), and which instrument gives the current text ("an Army" vs "the Army")?

**Sources.**
- C10 amendment_graph_c10.csv C9-AG-RES-C-08, C9-AG-RES-U-04, C9-AG-RES-U-07
- Edge statuses (C10): DISPUTED_PRESERVE_BOTH. Decision owner: qualified legal adviser (conflict register: legal_adviser_required). Edges: C9-AG-RES-C-08, C9-AG-RES-U-04, C9-AG-RES-U-07.

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| C12-AR193-COMP | rules-army-rules-1954 p.209, r.193 | STATUTE_COMPILATION | "The prescribed officer for the purposes of clause (i) of section 90 and clause (i) of section 91 shall be the Chief of the Army Staff or the officer commanding the Army." | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) S.R.O. 302/1987 substitutes r.193 for s.91(i) only ("Chief of the Army Staff or the Officer Commanding an Army") (C-08 evidence 1).
- (b) India Code compilation p.209 extends r.193 to s.90(i) and s.91(i), "officer commanding the Army" (C-08 evidence 2).
- U-04: the extension to s.90(i) is not supported by any located instrument; either an unlocated instrument added it or the compilation is in error (not determined). U-07: the compilation matches the 1993 substitution on the located evidence; open points remain.

**Affected research records.** (none listed in the C9/C10 artefacts)

**Evidence still missing.**
- Itemisation of S.R.O. 17(E)/1993 by WS-A and transcription of the 1954 base text; unlocated instruments (E-7/1960, S.R.O. 258/2002, post-2022).

### AQ-STA-16: Army Rule 194 (prescribed officer, AA s.93)

**Priority:** P2. **Origin:** C10 amendment_graph_c10.csv; C5 conflicts C-09, U-08 (AQ-02).

**Question.** Is the operative r.194 the 1989 substituted text (S.R.O. 332/1989, which adds "or the Officer Commanding an Army" for officers)? This is a PROPOSAL pending legal review (AQ-02).

**Sources.**
- C10 amendment_graph_c10.csv C9-AG-RES-C-09, C9-AG-RES-U-08
- Edge statuses (C10): DISPUTED_PRESERVE_BOTH. Decision owner: qualified legal adviser (conflict register: legal_adviser_required). Edges: C9-AG-RES-C-09, C9-AG-RES-U-08.

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| C12-AR194-COMP | rules-army-rules-1954 p.209, r.194 | STATUTE_COMPILATION | "Prescribed officer for the purpose of section 93 shall be, in the case of an officer, the Chief of the Army Staff" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) S.R.O. 332/1989 (Gazette 02-12-1989 p.736) and MML 2 p.227 carry the added words.
- (b) The India Code compilation p.209 lacks the added words.
- No later instrument affecting r.194 located (31 instruments; gaps AR-001, AR-030, AR-036).

**Affected research records.** (none listed in the C9/C10 artefacts)

**Evidence still missing.**
- The gap instruments.

### AQ-STA-17: Last amendment before S.R.O. 17(E)/2019 (footnote discrepancy)

**Priority:** P3. **Origin:** C10 amendment_graph_c10.csv; C8-CR-14.

**Question.** Which instrument was the last amendment of the Army Rules before S.R.O. 17(E)/2019? (Documentary; owner decision.)

**Sources.**
- C10 amendment_graph_c10.csv C9-AG-LASTAMD-2019
- Edge statuses (C10): DISPUTED_PRESERVE_BOTH. Decision owner: owner (documentary). Edges: C9-AG-LASTAMD-2019.

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Hindi footnote: last amended by S.R.O. 2(अ) of 20-02-2018
- (b) English footnote: 'last amended in 2018', no instrument named; S.R.O. 2(E)/2018 is on its face a r.188(e) declaration

**Affected research records.** (none listed in the C9/C10 artefacts)

**Evidence still missing.**
- None identified beyond owner review; S.R.O. 17(E)/2019 born-digital signature fails (P-D2a).

### AQ-STA-18: Commencement of Acts 19 of 1955 and 13 of 1975 (Army Act amendments)

**Priority:** P3. **Origin:** C10 amendment_graph_c10.csv; C9 U-6 (OQ-A-04).

**Question.** From what dates do the Commanders-in-Chief (Change in Designation) Act 1955 (commencement by notification) and the Air Force and Army Laws (Amendment) Act 1975 (no commencement section; s.4(2) saving refers to 25-01-1975) take effect for the Army Act provisions they changed?

**Sources.**
- C10 amendment_graph_c10.csv C9-AG-AA-01, C9-AG-AA-06
- C9 UNRESOLVED_MATTERS.md U-6
- Edge statuses (C10): UNRESOLVED_COMMENCEMENT. Decision owner: legal adviser (AQ-05 / OQ-A-04). Edges: C9-AG-AA-01, C9-AG-AA-06.

**Competing readings (as recorded in the artefacts; no view is taken).**
- C9-AG-AA-01: s.1(2): date to be appointed by notification; India Code fn: 7th May 1955 vide S.R.O. 2(E) of 07-05-1955 (text only)
- C9-AG-AA-06: (a) Act 13/1975: no commencement clause [C9R-A13-03 [held sha256 8358d2b3882b2a74; absent on all pages]]; s.4(2) 'as if this Act had come into force on the 25th day of January, 1975' for actions under the Ordinance [C9R-A13-02 [held sha256 8358d2b3882b2a74 p.2]] || (b) compilation 'w.e.f. 25-1-1975' [C9R-AA-09 [held sha256 e47a4265813e95b4 p.11;26]]
- C9 U-6 carries Act 13/1975 "w.e.f. 25-1-1975" as OQ-A-04.

**Affected research records.** (none listed in the C9/C10 artefacts)

**Evidence still missing.**
- The Act 19/1955 commencement notification.

### AQ-STA-19: IPC, CrPC and Evidence Act repeal by BNS, BNSS and BSA: commencement evidence and references in military law

**Priority:** P1. **Origin:** C9 U-5; C10 amendment_graph_c10.csv; CLAUDE.md known supersession case (IPC to BNS from 1 July 2024).

**Question.** On what evidence is the 01-07-2024 commencement of the BNS, BNSS and BSA to be recorded (notifications not held), and how do Army Act and Army Rules references to the CrPC (e.g. r.133(3) to CrPC s.340) and rules made under the CrPC (CCCM Rules 1978) read after BNSS s.531 and its saving s.531(2)(b)?

**Sources.**
- C10 amendment_graph_c10.csv C9-AG-BNS-REPEAL, C9-AG-BNSS-REPEAL, C9-AG-BSA-REPEAL
- C9 UNRESOLVED_MATTERS.md U-5
- Edge statuses (C10): UNRESOLVED_COMMENCEMENT. Decision owner: legal adviser (interpretation); owner (acquisition). Edges: C9-AG-BNS-REPEAL, C9-AG-BNSS-REPEAL, C9-AG-BSA-REPEAL.

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| C9R-BNSS-03 | act-bnss-2023 p.174, s.531(1) | STATUTE_COMPILATION | "The Code of Criminal Procedure, 1973 (2 of 1974) is hereby repealed." | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- C10 changed C9-AG-BNSS-REPEAL and C9-AG-BSA-REPEAL from NOT_LOCATED to UNRESOLVED_COMMENCEMENT: the repealing instruments are held (compilations and Hindi Gazette texts) but the commencement notifications (e.g. S.O. 849(E)) are not.
- C9 U-5 records how such references read after repeal as a legal question; no reading is proposed.

**Affected research records.** (6 KB records cite BNS s.358 per C9-AG-BNS-REPEAL; ids not listed there)

**Evidence still missing.**
- The BNS/BNSS/BSA commencement notifications (C5-ACQ-05); any post-BNSS adjustment rules; the CCCM Rules 1978 (PR #8).

### AQ-STA-20: Army Act s.133 and the Bharatiya Sakshya Adhiniyam 2023

**Priority:** P1. **Origin:** C9 ESC-07 (P1; C-07, LAQ-01).

**Question.** From what date, and for which pending proceedings, is AA s.133's reference to the Indian Evidence Act 1872 to be read as a reference to the BSA (General Clauses Act s.8; BSA s.170(2))?

**Sources.**
- C10 amendment_graph_c10.csv (no edge)
- C9 LEGAL_ADVISER_ESCALATION.md ESC-07

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| C9-S133 | act-army-1950 p.37, s.133 | STATUTE_COMPILATION | "The Indian Evidence Act, 1872 (1 of 1872), shall, subject to the provisions of this Act, apply to all proceedings before a court-martial." | verified (stated page) |
| C9-BSA-1-2 | act-bsa-2023 p.10, s.1(2) | STATUTE_COMPILATION | "It applies to all judicial proceedings in or before any Court, including Courts-martial" | verified (stated page) |
| C9-BSA-170-2 | act-bsa-2023 p.51, s.170(2) | STATUTE_COMPILATION | "shall be dealt with under the provisions of the Indian Evidence Act, 1872 (1 of 1872), as in force immediately before such" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- C9 classifies this as an interaction between two Acts, not a source conflict: AA s.133 still names the 1872 Act "subject to the provisions of this Act"; BSA s.1(2) applies the BSA to Courts-martial; BSA s.170(2) saves the IEA for pending proceedings; the 01-07-2024 date comes from a compilation footnote.
- Severity recalibration S-02 proposes lowering the CM-025 omission from P1 to P2; CIV-034's title states a timeless conclusion.

**Affected research records.** CM-025; EV-003; CIV-034

**Evidence still missing.**
- The BSA commencement notification (not held).

### AQ-STA-21: ADM-022 and Army Act s.26(2) (wording confirmation)

**Priority:** P2. **Origin:** C9 ESC-09 (P2, Part 3).

**Question.** May "explicitly directs complaint to next superior" in ADM-022 be replaced by the permissive statutory wording (C9-CP-C01, superseding E8-CP-08)? The adviser need only confirm the wording.

**Sources.**
- C10 amendment_graph_c10.csv (no edge)
- C9 LEGAL_ADVISER_ESCALATION.md ESC-09

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| C9-S26 | act-army-1950 p.16, s.26(2) | STATUTE_COMPILATION | "the aggrieved person may complain to such officer’s next superior officer" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- C9: s.26(2) and s.26(1) are permissive; s.26(3) imposes the receiving officer's duty. ADM-SC-06 and ADM-020 are already consistent with the statute.

**Affected research records.** ADM-022; ADM-SC-06; ADM-020

**Evidence still missing.**
- No Gazette copy of the 1950 Act is held; the evidence is a government compilation only.

**Edge coverage.**

| Edge | C10 status | Question |
| --- | --- | --- |
| C9-AG-AR-000 | UNRESOLVED_COMMENCEMENT | AQ-STA-11 |
| C9-AG-AR-006 | UNRESOLVED_COMMENCEMENT | AQ-STA-11 |
| C9-AG-AR-007 | UNRESOLVED_COMMENCEMENT | AQ-STA-11 |
| C9-AG-AR-008 | DISPUTED_PRESERVE_BOTH | AQ-STA-04 |
| C9-AG-AR-009 | UNRESOLVED_COMMENCEMENT | AQ-STA-11 |
| C9-AG-AR-010 | UNRESOLVED_COMMENCEMENT | AQ-STA-11 |
| C9-AG-AR-011 | UNRESOLVED_COMMENCEMENT | AQ-STA-11 |
| C9-AG-AR-014 | UNRESOLVED_COMMENCEMENT | AQ-STA-11 |
| C9-AG-AR-017 | UNRESOLVED_COMMENCEMENT | AQ-STA-11 |
| C9-AG-AR-018 | UNRESOLVED_COMMENCEMENT | AQ-STA-11 |
| C9-AG-AR-019 | UNRESOLVED_COMMENCEMENT | AQ-STA-11 |
| C9-AG-AR-020 | UNRESOLVED_COMMENCEMENT | AQ-STA-11 |
| C9-AG-AR-022 | UNRESOLVED_COMMENCEMENT | AQ-STA-11 |
| C9-AG-AR-023 | UNRESOLVED_COMMENCEMENT | AQ-STA-11 |
| C9-AG-AR-025 | UNRESOLVED_COMMENCEMENT | AQ-STA-11 |
| C9-AG-AA-01 | UNRESOLVED_COMMENCEMENT | AQ-STA-18 |
| C9-AG-AA-06 | UNRESOLVED_COMMENCEMENT | AQ-STA-18 |
| C9-AG-AA-08-s2 | UNRESOLVED_COMMENCEMENT | AQ-STA-06 |
| C9-AG-AA-08-s3 | UNRESOLVED_COMMENCEMENT | AQ-STA-06 |
| C9-AG-AA-08-s4 | UNRESOLVED_COMMENCEMENT | AQ-STA-06 |
| C9-AG-AA-08-s5 | UNRESOLVED_COMMENCEMENT | AQ-STA-06 |
| C9-AG-AA-08-s6 | UNRESOLVED_COMMENCEMENT | AQ-STA-06 |
| C9-AG-AA-08-s7 | UNRESOLVED_COMMENCEMENT | AQ-STA-06 |
| C9-AG-AA-08-s8 | UNRESOLVED_COMMENCEMENT | AQ-STA-06 |
| C9-AG-AA-08-s9 | UNRESOLVED_COMMENCEMENT | AQ-STA-06 |
| C9-AG-AA-08-s10 | UNRESOLVED_COMMENCEMENT | AQ-STA-06 |
| C9-AG-AA-08-s11 | UNRESOLVED_COMMENCEMENT | AQ-STA-06 |
| C9-AG-AA-08-s12 | UNRESOLVED_COMMENCEMENT | AQ-STA-06 |
| C9-AG-AA-08-s13 | UNRESOLVED_COMMENCEMENT | AQ-STA-06 |
| C9-AG-AA-08-s14 | UNRESOLVED_COMMENCEMENT | AQ-STA-06 |
| C9-AG-AA-08-s15 | UNRESOLVED_COMMENCEMENT | AQ-STA-06 |
| C9-AG-AA-08-s16 | UNRESOLVED_COMMENCEMENT | AQ-STA-06 |
| C9-AG-AA-08-s17 | UNRESOLVED_COMMENCEMENT | AQ-STA-06 |
| C9-AG-AA-08-s18 | UNRESOLVED_COMMENCEMENT | AQ-STA-06 |
| C9-AG-AA-08-s19 | UNRESOLVED_COMMENCEMENT | AQ-STA-06 |
| C9-AG-RES-C-01 | DISPUTED_PRESERVE_BOTH | AQ-STA-01 |
| C9-AG-RES-U-01 | DISPUTED_PRESERVE_BOTH | AQ-STA-01 |
| C9-AG-RES-C-02 | DISPUTED_PRESERVE_BOTH | AQ-STA-13 |
| C9-AG-RES-C-03 | DISPUTED_PRESERVE_BOTH | AQ-STA-14 |
| C9-AG-RES-SC4-01 | DISPUTED_PRESERVE_BOTH | AQ-STA-12 |
| C9-AG-RES-C-08 | DISPUTED_PRESERVE_BOTH | AQ-STA-15 |
| C9-AG-RES-U-07 | DISPUTED_PRESERVE_BOTH | AQ-STA-15 |
| C9-AG-RES-C-09 | DISPUTED_PRESERVE_BOTH | AQ-STA-16 |
| C9-AG-RES-U-08 | DISPUTED_PRESERVE_BOTH | AQ-STA-16 |
| C9-AG-RES-U-04 | DISPUTED_PRESERVE_BOTH | AQ-STA-15 |
| C9-AG-AFT-01 | UNRESOLVED_COMMENCEMENT | AQ-STA-10 |
| C9-AG-AFT-03 | UNRESOLVED_COMMENCEMENT | AQ-STA-10 |
| C9-AG-AFT-04 | UNRESOLVED_COMMENCEMENT | AQ-STA-10 |
| C9-AG-AFT-05 | UNRESOLVED_COMMENCEMENT | AQ-STA-09 |
| C9-AG-BNSS-REPEAL | UNRESOLVED_COMMENCEMENT | AQ-STA-19 |
| C9-AG-BSA-REPEAL | UNRESOLVED_COMMENCEMENT | AQ-STA-19 |
| C9-AG-BNS-REPEAL | UNRESOLVED_COMMENCEMENT | AQ-STA-19 |
| C9-AG-AR168 | DISPUTED_PRESERVE_BOTH | AQ-STA-03 |
| C9-AG-TRA2021-REPEAL | UNRESOLVED_COMMENCEMENT | AQ-STA-10 |
| C9-AG-AFTPRAC2009 | UNRESOLVED_COMMENCEMENT | AQ-STA-09 |
| C9-AG-CCCM-SO4010 | DISPUTED_PRESERVE_BOTH | AQ-STA-05 |
| C9-AG-SRO240-1955 | DISPUTED_PRESERVE_BOTH | AQ-STA-04 |
| C9-AG-LASTAMD-2019 | DISPUTED_PRESERVE_BOTH | AQ-STA-17 |

## 7. Authority ranking of copies (RR-04)

### AQ-AUT-01: Relative order of open-data bulk copies and law-report (SCR) renditions

**Priority:** P2. **Origin:** C10 RR-04.

**Question.** Is the authority-matrix order correct that places open-data bulk copies of Supreme Court judgments (tier 4: e.g. the AWS S3 buckets that supplied all 346 data/raw/sci and 3,605 data/raw/hc files) above law-report renditions including SCR (tier 5), under a heading that says a lower tier never overrides a higher one on content, and that keeps bulk copies at tier 2 for High Courts? If not settled, should the order be marked "not settled pending legal-side review"?

**Sources.**
- C10 DISPOSITIONS_final_head_confirmations.md RR-04 (ESCALATED, legal side)
- C10 final_head_confirmations/fable_review_7ccb9c2e.md RR-04
- C10 CORPUS_AUTHORITY_MATRIX.md section 3 ("Supreme Court judgments" tiers 1-6; "High Court and AFT judgments" tiers 1-3)

**Competing readings (as recorded in the artefacts; no view is taken).**
- (a) Current order (C10 matrix): tier 4 bulk copies ("Provenance of the copy is documented, but the copy is not court-hosted or certified") above tier 5 SCR renditions ("A comparator only ... never treated as a signed original"). No basis is stated.
- (b) Reviewer RR-04: the order needs legal-side confirmation; "it is not a finding that the order is wrong". Requested action: state the basis, or mark tiers 4/5 (and HC tier 2) as not settled.
- Documentary observation for the adviser (no conclusion): many held SC copies are labelled SCR_REPORT_RENDITION_AWS_ESCR_MIRROR (C11 dossier), i.e. law-report renditions obtained from an AWS mirror, so a single copy may fit the descriptions of both tier 4 and tier 5. The disposition records that the ranking is not used to change any status.

**Affected research records.** (no research record changes on the ranking; it governs copy precedence for SCR-only cases such as Tarsem, Shri Kant Sharma, S P Rathore)

**Evidence still missing.**
- Legal-side confirmation of the basis for the order.

### AQ-AUT-02: SCR-format renditions as comparators and locators

**Priority:** P2. **Origin:** C10 ESC-C10-05.

**Question.** May the raw-store SCR-format copies (AWS mirror of e-SCR) be registered as reported-version comparators (AP-C9-02), and may e-SCR report pages be cited as locators? They are not signed court originals.

**Sources.**
- C10 ADVISER_ESCALATIONS_C10.csv ESC-C10-05 (relates to LG-12; AP-C9-02; P-D3)
- C9 LEGAL_ADVISER_ESCALATION.md ESC-01 (Tarsem: AP-C9-02 as drafted covers statutory copies only)
- C9 DECISION_MATRIX_C9.md P-D3 (JUDIS renditions), RAW-01

**Excerpts with pinpoints.**

| Ref | Pinpoint | Voice | Excerpt (verbatim) | Check |
| --- | --- | --- | --- | --- |
| RD-PARASHOTAM-T1 | sc-2023-union-of-india-ors-2023insc265 p.17, para 32 | COURT_VOICE | "We have, thus, no hesitation in concluding that the judgment in" | verified (stated page) |

**Competing readings (as recorded in the artefacts; no view is taken).**
- C10 matrix tier 5: law-report renditions are "a comparator only, after its own identity and provenance are recorded". The C11 dossier uses SCR text-layer page numbers as locators throughout (e.g. Parashotam para 32 at SCR p.17 vs official p.22), and states that the official-copy locator was not re-read.
- No artefact proposes treating an SCR rendition as a signed original.

**Affected research records.** DCLR-SC-2008-N10; DCLR-SC-2015-N06; and every record whose only held copy is an SCR rendition

**Evidence still missing.**
- Owner/adviser decision on extending AP-C9-02 to judicial renditions.

## 8. Legal-approval role (PR #46 F-01)

### AQ-ROL-01: Approval tier and channel for operational use

**Priority:** P1. **Origin:** PR #46 review F-01.

**Question.** For each output class (authoritative template, mandatory constraint, procedural checklist, definitive advisory), is a designated legal-adviser decision sufficient, or is formal JAG validation required? How does an approval artefact reach an air-gapped deployment (signed release import only, or Admin transcription of an external artefact with the artefact attached, recording not being approving)?

**Sources.**
- scratchpad/c12/reviews/fable_review_pr46_c69eee41.md F-01 (P2) and capability rows 8 and 10
- PR #46 blueprint at c69eee41: Studio 3.2 and 8.1; Vision 2 and 6; ADR-0002 "Not decided"; ADR-0003 "Outstanding" (as cited by F-01)

**Competing readings (as recorded in the artefacts; no view is taken).**
- F-01 records that the gate depends on an "attributable competent legal approval" artefact but no role, operation or channel can record one: only Admin and User exist, User has no shared writes, and Admin action is explicitly not legal approval.
- The controlling policy treats a designated legal-adviser decision and formal JAG validation as separate gates (per F-01); the blueprint does not say which applies. Result today: fail-closed.

**Affected research records.** (none: no record is operationally approved; 658 records and 53 cases remain research/unapproved)

**Evidence still missing.**
- An owner/legal-side decision on the tier per output class; an ADR entry recording it, or recording it as a blocking open decision.

### AQ-ROL-02: Who decides "credible material" and who re-enables a blocked scope

**Priority:** P2. **Origin:** PR #46 review F-01, F-12.

**Question.** Who decides that new material is "credible" enough to mark an affected scope REVALIDATION_REQUIRED/BLOCKED, and who may re-enable it? Is the Vision's "Legal review workspace" Admin-operated, or deferred?

**Sources.**
- fable_review_pr46_c69eee41.md F-01, F-12 (INFO: "credible material" used as the blocking threshold in six files without criteria)

**Competing readings (as recorded in the artefacts; no view is taken).**
- F-01 records the gap; F-12 notes no criteria are defined. No artefact proposes a decider.

**Affected research records.** (none)

**Evidence still missing.**
- Named decider and criteria.

### AQ-ROL-03: Who reviews proposed supersession and overruling edges, and who confirms AI page readings

**Priority:** P1. **Origin:** CLAUDE.md open questions; C9 P-B.

**Question.** Who on the legal side reviews the proposed supersession, overruling and amendment edges in this package (an open question in the project brief), and who performs the human or reviewer-attested confirmation of AI page readings that option B2 of C9 decision P-B (recommended, not adopted) would require before an entry can create an anchor?

**Sources.**
- /home/user/mimamsa-corpus/CLAUDE.md, "Open questions to settle early"; Relations ("Anything other than cites needs human verification")
- C9 DECISION_MATRIX_C9.md P-B (recommendation B2: AI readings are supporting evidence only; nothing adopted)

**Competing readings (as recorded in the artefacts; no view is taken).**
- No competing readings: a role assignment. Every excerpt in this package is an AI reading and is not human-confirmed.

**Affected research records.** (all questions in this register)

**Evidence still missing.**
- A named reviewer or role.

## 9. Provenance

See `PROVENANCE_C12.md` for every input file (path, sha256, git state) and commit. Excerpt checks: `EXCERPT_VERIFICATION.csv`. Machine-readable register: `ADVISER_QUESTIONS.csv`.

**PREPARED BY AUTOMATED AGENTS. TECHNICAL AND DOCUMENTARY REVIEW ONLY. NO LEGAL VALIDATION.** Nothing in this package is a legal conclusion, a status change or an approval. Every reading of a source page was made by an AI agent from a text layer and is not human-confirmed. Questions are for a qualified legal adviser (or JAG, where the controlling policy requires it).
