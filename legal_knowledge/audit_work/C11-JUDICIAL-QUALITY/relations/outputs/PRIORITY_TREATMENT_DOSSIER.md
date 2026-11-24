# Priority treatment dossier (Cycle 11, judicial relationships)

**Status: evidence findings only. Nothing here is legally validated.**
- No status was changed. Every typed relation is a proposal: AUTOMATED_DETECTED, DOCUMENTARY_CHECK_REQUIRED or LEGAL_INTERPRETATION_ADVISER_REVIEW. LEGALLY_VALIDATED is never assigned.
- **Readings.** All readings are by an AI agent (Claude Opus 5.5 subagent) of the text layer at raw-data commit ad77758d. They are not human-confirmed. No page images were rendered.
- **Copies.** Most held Supreme Court copies here are SCR renditions from the AWS e-SCR mirror. They are not signed court originals.
- **Quotation checks.** Each quotation in 'Verified readings' is re-checked on every build, verbatim (whitespace-insensitive) on the stated PDF page. The build fails on any miss.
- **Locators.** 'p.' is the text-layer PDF page ([[page N]]). 'para' is the printed paragraph number where shown. In graph tables the paragraph is a heuristic (the last numbered paragraph start before the citation).
- **Graph counts.** These come from CASE_CITATION_GRAPH.csv and TREATMENT_CANDIDATES.csv. A citing edge means the citing judgment carries a citation string resolved to the case, or a case number with party names. Name-only mentions are listed separately and are not resolved.
- **Overruling.** No precedent is declared overruled. Where the source wording is explicit, it is quoted, and the edge goes to adviser review.

## Summary of key findings

| Case | Held copy in text layer | Resolved citing judgments | Key finding (with uncertainty) |
| --- | --- | --- | --- |
| Union of India v. Tarsem Singh | sc-2008-union-of-india-ors-2008insc930 | 45 | Distinguished (2 grounds) by Girish para 22, p.11. Not overruled on held documents. Still applied by Delhi HC on 11-03-2026, after Girish: conflicting treatment preserved. |
| Union of India v. Sgt Girish Kumar (main judgment, 12-02-2026) | sc-2026-union-of-india-through-its-sec-2026insc149 | 22 | Holds the s.22(1)(c) bar inapplicable and treats Ram Avtar as in rem (para 22, p.11). HC uptake is listed below; documentary checks are pending. |
| Union of India v. Sgt Girish Kumar (reported clarification order, 12-10-2026) | NOT HELD | 0 | NOT HELD and NOT CITED in any held judgment (deterministic search). Its content is unknown. |
| Union of India v. Major General Shri Kant Sharma | sc-2015-union-of-india-ors-2015insc206 | 17 | Parashotam para 32 (p.17): 'does not lay down the correct law' (three Judges vs two). OVERRULES is proposed for adviser review only. J&K HC still relied on it on 06-10-2025. |
| Union of India v. Parashotam Dass | sc-2023-union-of-india-ors-2023insc265 | 6 | The para 32 wording is verified in the SCR rendition at pp.17-18. The official-copy locator (p.22, from C10) was not re-read. |
| Ranjit Thakur v. Union of India | sc-1987-ranjit-thakur-1987insc285 | 41 | A proportionality/bias authority with wide CITES uptake. No explicit negative treatment found. |
| S. N. Mukherjee v. Union of India | sc-1990-s-n-mukherjee-1990insc257 | 25 | Constitution Bench: no reasons are needed at confirmation, but Art. 32/226 review remains (p.27). Parashotam relies on it. |
| Union of India v. Ram Avtar (order of 10-12-2014) | NOT HELD | 0 resolved; 381 citing judgments by unresolved string | NOT HELD; known only through citing judgments. All citations are UNRESOLVED. |
| Dharamvir Singh v. Union of India | sc-2013-dharamvir-singh-2013insc408 | 352 | Construes the 1982 Entitlement Rules (para 28, p.27). C10 records Isaac (2026, 2008 Rules) as clarifying it; not re-read here. |

## Union of India v. Tarsem Singh

- **Curated record.** DCLR-SC-2008-N10. Curated date: 2008-08-13. Case number: Civil Appeals 5151–5152 of 2008. Reporter: (2008) 8 SCC 648.
- **C10 held status:** HELD.
- **C10 official-copy status (copies outside this text layer were not re-read):** NO_SIGNED_OR_OFFICIAL_COURT_PDF; held: SCR_REPORT_RENDITION_AWS_ESCR_MIRROR.
- **Held copy in the ad77758d text layer.** Group JG-f8a14181e47c (EXACT_DUPLICATE;MISSING_OFFICIAL_ORIGINAL). Renditions: SCR_REPORT_RENDITION_AWS_ESCR_MIRROR.
  - Records: sc-2008-union-of-india-ors-2008insc930 (sha f8a14181e47c, 6 pp.).
  - Neutral citation: 2008 INSC 930. Reported: [2008] 12 S.C.R. 104. Date: 2008-08-13.
- **C10 prior reading vs C11:** C10: holding SCR pp.5-6 paras 5-6; DISTINGUISHED by Girish para 22; APPLIED by Delhi HC W.P.(C) 16771/2025 p.9; DISTINGUISHED by W.P.(C) 2053/2026. C11: all four re-verified verbatim in the ad77758d text layer (Girish via its SCR rendition, p.11).

### Verified readings

| Reading | Kind | Document | p. | para | Quotation (verbatim) | Note |
| --- | --- | --- | --- | --- | --- | --- |
| RD-TARSEM-H1 | HOLDING | sc-2008-union-of-india-ors-2008insc930 | 5 | 5 | "will restrict the consequential relief relating to arrears normally" | SCR rendition [2008] 12 SCR 104 (AWS e-SCR mirror; not a signed court copy). Para 5 continues 'to a period of three years prior to the date of filing of tlie writ petition' (OCR noise in the text layer). |
| RD-TARSEM-H2 | HOLDING | sc-2008-union-of-india-ors-2008insc930 | 6 | 6 | "It ought to have restricted the relief relating to ar- rears to only three years before the date of writ petition" | Operative direction on the facts (16 years' delay). Two-Judge Bench per the printed bench line. |
| RD-GIRISH-T1 | TREATMENT | sc-2026-union-of-india-through-its-sec-2026insc149 | 11 | 22 | "The reliance placed by the appellant on the decision of a two-Judge Bench of this Court in Tarsem Singh (supra) is of no assistance to it, as the legal landscape did not remain static after decision in Tarsem Singh." | Girish's own wording (court voice, not a submission or quotation). First ground: later three-Judge Bench order in Ram Avtar. |
| RD-GIRISH-T2 | TREATMENT | sc-2026-union-of-india-through-its-sec-2026insc149 | 11 | 22 | "the decision in Tarsem Singh (supra) has no application to the case in hand as ex-servicemen in the instant appeals are already in receipt of disability pension" | Second, fact-based ground (claimants already in receipt of pension; only re-computation sought). |
| RD-GIRISH-ED | REPORTER_EDITORIAL | sc-2026-union-of-india-through-its-sec-2026insc149 | 2 | - | "Tarsem Singh [2008] 12 SCR 104 : (2008) 8 SCC 648 – held inapplicable." | Reporter's 'Case Law Cited' entry in the SCR rendition. Editorial matter: never used as the court's treatment. |
| RD-DHC-TARSEM-A | LATER_RELIANCE | hc-delhi-2026-w-p-c-16771-2025-dlhc010862002025-1-2026-03-11 | 9 | 27 | "view the law laid down by Supreme Court in Union of India & Ors v. Tarsem Singh8 , the arrears will be restricted to three years prior the OA," | Delhi HC, 11-03-2026 (after Girish, 12-02-2026): restricts arrears by Tarsem while granting rounding-off from Ram Avtar's date. Girish is not mentioned in this passage. |
| RD-DHC-TARSEM-D | LATER_RELIANCE | hc-delhi-2026-w-p-c-2053-2026-dlhc010054682026-1-2026-04-20 | 3 | 10 | "The reliance placed on Tarsem Singh (supra) is misconceived." | Delhi HC, 20-04-2026: petitioner's reliance on Tarsem rejected (p.4 explains Tarsem concerned recurring pension injury). |

### Citing judgments (graph)

- **Distinct citing judgments:** 45.
  - By court: Allahabad High Court 2, High Court of Delhi 30, High Court of Jammu and Kashmir 4, High Court of Punjab and Haryana 8, Supreme Court of India 1.
  - By year: 2009: 2, 2012: 3, 2014: 3, 2016: 1, 2018: 2, 2020: 1, 2021: 1, 2024: 10, 2025: 13, 2026: 9.

All Supreme Court citing edges are listed, plus the 12 most recent High Court edges (of 44). The paragraph number is heuristic.

| Citing judgment | Court | Date | p. | para | Method | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| sc-2026-union-of-india-through-its-sec-2026insc149 | SC | 2026-02-12 | 6 | 6 | CURATED_CROSSWALK_C10_HELD;REPORTER_CITATION_METADATA | dia & Ors. (1995) 5 SCC 628; Shiv Dass v. Union of India & Ors. (2007) 9 SCC 274; Union of India & Ors. v. Tarsem Singh (2008) 8 SCC 648; M. Siddiq (Ram Janmabhumi Temple case) v. Mahant Suresh Das & Ors. (2020) 1 SCC 1; P.K. Kapur v. Union of India… |
| hc-delhi-2026-w-p-c-2053-2026-dlhc010054682026-1-2026-04-20 | HC Delhi | 2026-04-20 | 3 | 10 | CURATED_CROSSWALK_C10_HELD | wrong” as sought to be invoked by the Petitioner. 10. The reliance placed on Tarsem Singh (supra) is misconceived. 1 (2008) 8 SCC 648 Signed By:SAVITA PASRICHA Signing Date:23.04.2026 13:25:48 Signature Not Verified [[page 4]] W.P.(C) 2053/2026 |
| hc-delhi-2026-w-p-c-1246-2026-dlhc010028892026-1-2026-04-20 | HC Delhi | 2026-04-20 | 6 | 14 | CURATED_CROSSWALK_C10_HELD | , such as the one under consideration is also against the Supreme Court’s decision in Union of India v. Tarsem Singh (2008) 8 SCC 648 and Shiv Dass v. Union of India (2007) 9 SCC 628, wherein it was held that financial benefits are subject to limita… |
| hc-delhi-2026-w-p-c-16771-2025-dlhc010862002025-1-2026-03-11 | HC Delhi | 2026-03-11 | 9 | 28 | CURATED_CROSSWALK_C10_HELD | o orders as to costs. MANMEET PRITAM SINGH ARORA, J V. KAMESWAR RAO, J MARCH 11, 2026/AJ 7 2014 SCC OnLine SC 1761 8 (2008) 8 SCC 648 Signed By:MOHIT Signing Date:18.03.2026 18:36 Signature Not Verified |
| hc-delhi-2026-w-p-c-750-2026-dlhc010013502026-1-2026-02-10 | HC Delhi | 2026-02-10 | 8 | 24 | CURATED_CROSSWALK_C10_HELD | e filing of the OA before the Tribunal i.e., with effect from the year 2015 [Reference Union of India v. Tarsem Singh, 2008 Vol 8 SCC 648]. In other words, we hold that the applicant shall be entitled to the disability element in pension assessed at… |
| hc-delhi-2026-w-p-c-18861-2025-dlhc011006732025-1-2026-02-10 | HC Delhi | 2026-02-10 | 8 | 24 | CURATED_CROSSWALK_C10_HELD | e filing of the OA before the Tribunal i.e., with effect from the year 2015 [Reference Union of India v. Tarsem Singh, 2008 Vol 8 SCC 648]. In other words, we hold that the applicant shall be entitled to the disability element in pension assessed at… |
| hc-delhi-2026-w-p-c-1299-2026-dlhc010031052026-1-2026-01-30 | HC Delhi | 2026-01-30 | 6 | 13 | CURATED_CROSSWALK_C10_HELD | y of more than 50 years along with liberty to reinstitute the same petition in view of Union of India V. Tarsem Singh 2008 (8) SCC 648, where the Supreme Court has held that in cases of pension, delay cannot be an impediment for grant of relief. Hen… |
| hc-delhi-2026-w-p-c-19340-2025-dlhc011039752025-1-2026-01-29 | HC Delhi | 2026-01-29 | 2 | 3 | CURATED_CROSSWALK_C10_HELD | he present OA, in terms of the verdict of the Hon’ble Supreme Court in Union of India & Ors vs Tarsem singh reported in 2008 8 SCC 648 which shall be paid by the respondents, failing which the applicant will be entitled for interest @ 6% p.a. from t… |
| hc-ph-2026-lpa-1147-2024-phhc010485332024-1-2026-01-27 | HC Punjab and Haryana | 2026-01-27 | 7 | 11 | CURATED_CROSSWALK_C10_HELD | writ petition, in view of the law laid down by the Hon’ble Supreme Court of India in ‘Union of India vs. Tarsem Singh (2008) 8 SCC 648’. 12. It is further submitted that the petitioner was required to be granted the ex-gratia amount of Rs. 5,00,000/… |
| hc-jkl-2025-wp-c-1740-2025-jkhc020037182025-1-2025-12-24 | HC Jammu and Kashmir | 2025-12-24 | 2 | 2 | CASE_NUMBER_PLUS_PARTY | to consider the judgment of the Hon’ble Supreme Court of India passed in case titled Union of India Vs. Tarsem Singh, Civil Appeal Nos.5151-5152 of 2008, wherein the issue relating to the period for which the arrears are payable to the respondent-ap… |
| hc-delhi-2025-w-p-c-18384-2025-dlhc010969602025-1-2025-12-03 | HC Delhi | 2025-12-03 | 4 | 13 | CURATED_CROSSWALK_C10_HELD | is category of cases, however, we must always bear in mind that a finding of fact recorded by the Tribunal cannot be 4 2008 (8) SCC 648 5 AIR 1964 SC 477 Digitally Signed By:AJIT KUMAR Signing Date:04.12.2025 19:19:40 Signature Not Verified [[page 5… |
| hc-jkl-2025-wp-c-2213-2024-jkhc020048542024-1-2025-11-20 | HC Jammu and Kashmir | 2025-11-20 | 5 | 13 | CURATED_CROSSWALK_C10_HELD | a continuing and recurring cause of action the Hon‟ble Supreme Court in case titled Union of India v. Tarsem Singh, (2008) 8 SCC 648) has held that “if the issue relates to payment or re-fixation of pay or pension, relief may be granted in spite of d |
| hc-delhi-2025-w-p-c-14393-2024-dlhc010695112024-1-2025-10-09 | HC Delhi | 2025-10-09 | 7 | 22 | CURATED_CROSSWALK_C10_HELD | the judgment in Tarsem Singh v Union of India7. C. HARI SHANKAR, J. OM PRAKASH SHUKLA, J. OCTOBER 9, 2025 dsn/gunn 7 2008 (8) SCC 648 Digitally Signed By:AJIT KUMAR Signing Date:13.10.2025 19:28:06 Signature Not Verified |

### Treatment candidates (cue wording near a citation or a later name reference)

- **Cue hits:** 11.
  - By attribution: COURT_LIKELY 6, LOWER_FORUM_REPORTED 2, PARTY_SUBMISSION_OR_MIXED 1, REPORTED_TREATMENT_OF_TARGET 1, REPORTER_EDITORIAL 1.
  - Only COURT_LIKELY hits can carry a proposed relation.

| Candidate | Citing judgment | Date | cue p./para | Cue | Attribution | Proposed | Status | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TC-910ca4002d71 | hc-delhi-2012-w-p-c-548-2012-dlhc010126312012-1-2012-01-25 | 2012-01-25 | 11/15 | distinguishable | COURT_LIKELY | DISTINGUISHES | DOCUMENTARY_CHECK_REQUIRED | without holding an Invalidation Medical Board. The case of Tarsem Singh (supra) is apparently distinguishable and the petitioner cannot place reliance on the same to cl |
| TC-776ee591c8c5 | hc-delhi-2012-w-p-c-586-2012-dlhc010126342012-1-2012-01-30 | 2012-01-30 | 10/16 | distinguishable | COURT_LIKELY | DISTINGUISHES | DOCUMENTARY_CHECK_REQUIRED | without holding an Invalidation Medical Board. The case of Tarsem Singh (supra) is apparently distinguishable and the petitioner cannot place reliance on the same to cl |
| TC-5a5eee86ef27 | hc-delhi-2014-w-p-c-6538-2013-dlhc011563952013-1-2014-11-24 | 2014-11-24 | 6/6 | is covered by | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | oint of limitation, we find that the case of the petitioner is covered by the judgment of Tarsem Singh (supra) since the petitioner is claiming disability pensio |
| TC-bc25a8b55c4f | hc-delhi-2020-w-p-c-6093-2020-dlhc010241772020-1-2020-09-08 | 2020-09-08 | 6/10 | overruled | REPORTED_TREATMENT_OF_TARGET | - | LEGAL_INTERPRETATION_ADVISER_REVIEW | Singh Titaria Vs. Sukhvinder Singh (2015) 12 SCC 257 and in other judgments, the opinion of the Medical Board has been overruled and thus Ravinder Kumar supra stands diluted; (k) the petitioner is bearing the maintenance |
| TC-0befe2825ad3 | sc-2026-union-of-india-through-its-sec-2026insc149 | 2026-02-12 | 11/22 | is of no assistance | COURT_LIKELY | DISTINGUISHES | DOCUMENTARY_CHECK_REQUIRED | llant on the decision of a two-Judge Bench of this Court in Tarsem Singh (supra) is of no assistance to it, as the legal landscape did not remain static after d |
| TC-206496479449 | sc-2026-union-of-india-through-its-sec-2026insc149 | 2026-02-12 | 11/22 | has no application | COURT_LIKELY | DISTINGUISHES | DOCUMENTARY_CHECK_REQUIRED | ecision is in rem. For, yet another reason, the decision in Tarsem Singh (supra) has no application to the case in hand as ex-servicemen in the instant appeals |
| TC-dc29c0f14482 | hc-delhi-2026-w-p-c-2053-2026-dlhc010054682026-1-2026-04-20 | 2026-04-20 | 3/10 | is misconceived | COURT_LIKELY | DISTINGUISHES | DOCUMENTARY_CHECK_REQUIRED | etitioner. 10. The reliance placed on Tarsem Singh (supra) is misconceived. 1 (2008) 8 SCC 648 Signed By:SAVITA PASRICHA Signing Date:23.04.2026 13:25:48 |
| TC-93e1bd6ea659 | sc-2026-union-of-india-through-its-sec-2026insc149 | 2026-02-12 | 2/- | held inapplicable | REPORTER_EDITORIAL | - | AUTOMATED_DETECTED | 4 SCC OnLine SC 1761; Union of India & Ors. v. Tarsem Singh [2008] 12 SCR 104 : (2008) 8 SCC 648 – held inapplicable. Shri Madhav Laxman Vaikunthe v. State of Mysore [1962] 1 |
| TC-21bd4ec1d2ba | hc-ph-2026-lpa-1147-2024-phhc010485332024-1-2026-01-27 | 2026-01-27 | 7/11 | in view of the law laid down | PARTY_SUBMISSION_OR_MIXED | - | AUTOMATED_DETECTED | 02 months, preceding the date of filing the writ petition, in view of the law laid down by the Hon’ble Supreme Court of India in ‘Union of India vs. Tarsem Singh (2008) 8 SCC 648’. 12. It is further submitted that the pe |
| TC-74456fb37e29 | hc-jkl-2025-wp-c-1876-2024-jkhc020041892024-1-2025-08-26 | 2025-08-26 | 1/2 | in view of the law laid down | LOWER_FORUM_REPORTED | - | AUTOMATED_DETECTED | the ground that the Tribunal has failed to appreciate that in view of the law laid down by the Supreme Court in case titled, ‘Union of India vs. Tarsem Singh’ 2008(8) SCC 648, the arrears payable to the respondent should |
| TC-d7e72653b772 | hc-jkl-2025-wp-c-517-2024-jkhc020010762024-1-2025-08-25 | 2025-08-25 | 1/1 | in view of the law laid down | LOWER_FORUM_REPORTED | - | AUTOMATED_DETECTED | be restricted to three years preceding the filing of O.A., in view of the law laid down by the Hon’ble Supreme Court in “Union of India v. Tarsem Singh”, (2008) 8 SCC 648. Sr. No. 6 [[page 2]] 2 WP(C) No. |

### Name-only mentions (not resolved; may be false positives)

- **Pattern:** `tarsem singh`. Searched in judgments with no resolved or string-matched edge to this case.
- **Window:** decided on or after 2008-08-13.
- **Hits:** 62 judgments.
  - hc-delhi-2026-w-p-c-14039-2026-dlhc010455852026-1-2026-09-30 (2026-09-30) p.3: "3 of 6 judgment of the Apex Court in the matter of Union of India & Ors. vs. Tarsem Singh [2009 (1) AISLJ 371], proceeded to condone the delay of more than 15 years. He"
  - hc-jkl-2026-wp-c-1554-2026-jkhc020029342026-1-2026-06-03 (2026-06-03) p.4: "placed by the appellant on the decision of a two- Judge Bench of this Court in Tarsem Singh (supra) is of no assistance to it, as the legal landscape did not remain stat"
  - hc-jkl-2026-wp-c-1426-2026-jkhc020026572026-1-2026-05-19 (2026-05-19) p.4: "placed by the appellant on the decision of a two- Judge Bench of this Court in Tarsem Singh (supra) is of no assistance to it, as the legal landscape did not remain stat"
  - hc-jkl-2026-wp-c-1291-2024-jkhc020028632024-1-2026-02-12 (2026-02-12) p.1: "r. Panel Counsel for UOI Versus No.13767121A Ex RFN Surinder Singh S/o Tarsem Singh R/o Village Regal P/O Mawa Tehsl Hiranagar, District Kathua ..."
  - hc-delhi-2026-w-p-c-1352-2026-dlhc010031492026-1-2026-02-03 (2026-02-03) p.2: "in keeping with the law la1d down in the case of Union of India and others Vs. Tarsem Singh [2008 (8)SCC 649]. (ii) to calculate, sanction and issue necessary PPO to the a"
  - hc-delhi-2026-w-p-c-860-2026-dlhc010016832026-1-2026-01-21 (2026-01-21) p.2: "in keeping with the law laid down in the case of Union of India and others Vs. Tarsem Singh /2008 (8)SCC 649].” 4. The submission made by the learned counsel for the peti"
  - hc-jkl-2025-wp-c-706-2024-jkhc020065612023-1-2025-11-03 (2025-11-03) p.4: "ner(s) …..Respondent(s) 36.WP(C) No.2275/2024 Union of India and others v. Tarsem Singh …..Petitioner(s) …..Respondent(s) 37.WP(C) No.2298/2024 Union"
  - hc-jkl-2025-wp-c-658-2025-jkhc020014222025-1-2025-11-03 (2025-11-03) p.4: "ner(s) …..Respondent(s) 36.WP(C) No.2275/2024 Union of India and others v. Tarsem Singh …..Petitioner(s) …..Respondent(s) 37.WP(C) No.2298/2024 Union"
  - hc-jkl-2025-wp-c-657-2025-jkhc020014192025-1-2025-11-03 (2025-11-03) p.4: "ner(s) …..Respondent(s) 36.WP(C) No.2275/2024 Union of India and others v. Tarsem Singh …..Petitioner(s) …..Respondent(s) 37.WP(C) No.2298/2024 Union"
  - hc-jkl-2025-wp-c-544-2025-jkhc020009822025-1-2025-11-03 (2025-11-03) p.4: "ner(s) …..Respondent(s) 36.WP(C) No.2275/2024 Union of India and others v. Tarsem Singh …..Petitioner(s) …..Respondent(s) 37.WP(C) No.2298/2024 Union"

### Contrary authority / conflicting treatment

- Girish (2026 INSC 149, two Judges) holds Tarsem 'of no assistance' and of 'no application' on two grounds (RD-GIRISH-T1, RD-GIRISH-T2). The wording is distinguishing, not overruling; both Benches have two Judges.
- Delhi HC W.P.(C) 16771/2025 (11-03-2026), after Girish, still restricts arrears to three years by Tarsem (RD-DHC-TARSEM-A). This conflicting treatment is kept as found; whether that reading survives Girish is a legal question.
- Delhi HC W.P.(C) 2053/2026 (20-04-2026) calls reliance on Tarsem 'misconceived' (RD-DHC-TARSEM-D). That is a fact-based distinction, not a statement about Tarsem's authority.

### Open questions and uncertainty

- Does Tarsem's three-year arrears rule survive for claims outside Girish's two grounds? Girish confines its reasoning to broad-banding claimants already in receipt of pension. Adviser question (C10 ESC-C10-01).
- C10 reports that Mullikote (2026 INSC 286) para 43 left the question open (official copy p.27). That copy is not in the ad77758d text layer, so it was not re-read here.
- Tarsem is held only as an SCR rendition, with OCR noise. No signed court copy is held.

## Union of India v. Sgt Girish Kumar (main judgment, 12-02-2026)

- **Curated record.** DCLR-SC-2026-007. Curated date: 2026-02-12. Case number: C.A. 6820–6824/2018 and connected appeals. Reporter: -.
- **C10 held status:** HELD.
- **C10 official-copy status (copies outside this text layer were not re-read):** YES_OFFICIAL_COURT_PDF. Working store: downloads/citation-codes/girish_feb2026.pdf.
- **Held copy in the ad77758d text layer.** Group JG-4f7ea3a451c6 (DIFFERENT_RENDITION). Renditions: SCR_REPORT_RENDITION_AWS_ESCR_MIRROR, SC_OFFICIAL_COURT_PDF.
  - Records: sc-2026-union-of-india-through-its-sec-2026insc149 (sha da0304734666, 12 pp.).
  - Neutral citation: 2026 INSC 149. Reported: [2026] 2 S.C.R. 615. Date: 2026-02-12.
- **C10 prior reading vs C11:** C10: 24 HC citing judgments after decision; 3 read, all APPLY. C11: see the graph counts below. Cue-based proposals need documentary checks.

### Verified readings

| Reading | Kind | Document | p. | para | Quotation (verbatim) | Note |
| --- | --- | --- | --- | --- | --- | --- |
| RD-GIRISH-T1 | TREATMENT | sc-2026-union-of-india-through-its-sec-2026insc149 | 11 | 22 | "The reliance placed by the appellant on the decision of a two-Judge Bench of this Court in Tarsem Singh (supra) is of no assistance to it, as the legal landscape did not remain static after decision in Tarsem Singh." | Girish's own wording (court voice, not a submission or quotation). First ground: later three-Judge Bench order in Ram Avtar. |
| RD-GIRISH-T2 | TREATMENT | sc-2026-union-of-india-through-its-sec-2026insc149 | 11 | 22 | "the decision in Tarsem Singh (supra) has no application to the case in hand as ex-servicemen in the instant appeals are already in receipt of disability pension" | Second, fact-based ground (claimants already in receipt of pension; only re-computation sought). |
| RD-GIRISH-T3 | TREATMENT | sc-2026-union-of-india-through-its-sec-2026insc149 | 11 | 22 | "decided the issue of applicability of instruction dated 31.01.2001 and the aforesaid decision is in rem." | Characterises Ram Avtar as a decision in rem. |
| RD-GIRISH-H1 | HOLDING | sc-2026-union-of-india-through-its-sec-2026insc149 | 11 | 22 | "Therefore, the bar contained in Section 22(1)(c) of the Act has no application to the" | Sentence continues on p.12: 'claims filed by the ex-servicemen before the Tribunal.' |
| RD-GIRISH-R1 | TREATMENT | sc-2026-union-of-india-through-its-sec-2026insc149 | 9 | 14 | "The legal position continued to be uncertain until it was settled by a three-Judge bench of this Court in Union of India & Others v. Ram Avtar (supra)." | Girish's account of Ram Avtar (not held in the corpus). |
| RD-GIRISH-ED | REPORTER_EDITORIAL | sc-2026-union-of-india-through-its-sec-2026insc149 | 2 | - | "Tarsem Singh [2008] 12 SCR 104 : (2008) 8 SCC 648 – held inapplicable." | Reporter's 'Case Law Cited' entry in the SCR rendition. Editorial matter: never used as the court's treatment. |
| RD-GIRISH-BENCH | BENCH | sc-2026-union-of-india-through-its-sec-2026insc149 | 1 | - | "[Pamidighantam Sri Narasimha and Alok Aradhe,* JJ.]" | Two-Judge Bench printed in the SCR rendition. |

### Citing judgments (graph)

- **Distinct citing judgments:** 22.
  - By court: High Court of Jammu and Kashmir 10, High Court of Punjab and Haryana 12.
  - By year: 2026: 22.

All Supreme Court citing edges are listed, plus the 12 most recent High Court edges (of 22). The paragraph number is heuristic.

| Citing judgment | Court | Date | p. | para | Method | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| hc-jkl-2026-wp-c-3134-2026-jkhc020062872026-1-2026-09-30 | HC Jammu and Kashmir | 2026-09-30 | 3 | 5 | PARTY_YEAR_COURT | Avtar (supra) and latest the judgment rendered by the Supreme Court in Union of India and SGT Girish Kumar and others 2026 SCC OnLine SC149. Therefore, the issue raised is no longer res integra. 06. Admittedly, the classification made by the petitio… |
| hc-jkl-2026-wp-c-2819-2025-jkhc020060772025-1-2026-09-16 | HC Jammu and Kashmir | 2026-09-16 | 4 | 11 | NEUTRAL_CITATION_METADATA | gment passed by the Hon’ble Supreme Court in the case of “Union of India and others Vs. SGT Girish Kumar and others”, 2026 INSC 149. (Shahzad Azeem) (Sanjeev Kumar) Judge |
| hc-ph-2026-cwp-24493-2026-phhc011270842026-1-2026-08-12 | HC Punjab and Haryana | 2026-08-12 | 3 | 5 | REPORTER_CITATION_METADATA | Hon'ble Supreme Court of India in Union of India through its Secretary and others Versus SGT Girish Kumar and others, 2026(2) SCR 615, whereby it has been held that benefit of arrears is to be given from 01.01.1996 or 01.01.2006 as the case may be, … |
| hc-ph-2026-cwp-21960-2026-phhc011164962026-1-2026-07-20 | HC Punjab and Haryana | 2026-07-20 | 3 | 6 | CASE_NUMBER_PLUS_PARTY | has been in dispute somewhat, has been settled by the Hon’ble Supreme Court of India in a recently passed judgment in Civil Appeal Nos. 6820-6824 of 2018 titled as Union of India through Secretary and others vs. SGT Girish Kumar and others, decided … |
| hc-ph-2026-cwp-1730-2026-phhc010092662026-1-2026-07-20 | HC Punjab and Haryana | 2026-07-20 | 2 | 2 | REPORTER_CITATION_METADATA | il Appeal No. 6824 of 2018 titled as "Union of India through its Secretary and others vs. SGT Girish Kumar and others" 2026 (2) SCR 615 and, therefore the restriction put upon the grant of arrears may kindly be modified so as to entitle the petition… |
| hc-jkl-2026-wp-c-1665-2026-jkhc020032292026-1-2026-06-04 | HC Jammu and Kashmir | 2026-06-04 | 3 | 8 | NEUTRAL_CITATION_METADATA | Page 3 of 3 Hon’ble Supreme Court in “Union of India v. Sgt. Girish Kumar & Ors.”, 2026 INSC 149. The Hon’ble Supreme Court has held that once entitlement to disability pension or its re-computation is recognized, t |
| hc-jkl-2026-wp-c-1661-2026-jkhc020032272026-1-2026-06-04 | HC Jammu and Kashmir | 2026-06-04 | 3 | 8 | NEUTRAL_CITATION_METADATA | y pension stands authoritatively settled by the Hon'ble Supreme Court in ‘Union of India v. Sgt. Girish Kumar & Ors.’, 2026 INSC 149, wherein it was held that once entitlement to disability pension or its re-computation is recognized, the benefit ca… |
| hc-jkl-2026-wp-c-1554-2026-jkhc020029342026-1-2026-06-03 | HC Jammu and Kashmir | 2026-06-03 | 3 | 8 | NEUTRAL_CITATION_METADATA | settled in terms of the judgment of the Hon’ble Apex Court in “Union of India v. Sgt. Girish Kumar and others etc.”, 2026 INSC 149. The Hon’ble Apex Court, while considering the grievance of the Union of India regarding payment of arrears of disabil |
| hc-ph-2026-cwp-17094-2026-phhc010913222026-1-2026-05-27 | HC Punjab and Haryana | 2026-05-27 | 4 | 7 | CASE_NUMBER_PLUS_PARTY | eriod starting from 01.12.2008 till his death 19.03.2013 and said issue is squarely covered by the judgment passed in Civil Appeal Nos. 6820-6824 of 2018 titled as Union of India through Secretary and others vs. SGT Girish Kumar and others, decided … |
| hc-jkl-2026-wp-c-1426-2026-jkhc020026572026-1-2026-05-19 | HC Jammu and Kashmir | 2026-05-19 | 3 | 9 | NEUTRAL_CITATION_METADATA | ands settled in terms of the judgment of the Hon‟ble Apex Court in “Union of India v. Sgt. Girish Kumar & ors. etc.”, 2026 INSC 149. The Hon‟ble Apex Court, while considering the grievance of the Union of India regarding payment of arrears of disabil |
| hc-ph-2026-cwp-14035-2026-phhc010747442026-1-2026-05-06 | HC Punjab and Haryana | 2026-05-06 | 3 | 10 | CASE_NUMBER_PLUS_PARTY | has been in dispute somewhat, has been settled by the Hon’ble Supreme Court of India in a recently passed judgment in Civil Appeal Nos. 6820- 6824 of 2018 titled as Union of India through Secretary and others vs. SGT Girish Kumar and others, decided… |
| hc-ph-2026-cwp-24977-2024-phhc011292812024-1-2026-05-05 | HC Punjab and Haryana | 2026-05-05 | 2 | 4 | CASE_NUMBER_PLUS_PARTY | has been in dispute somewhat, has been settled by the Hon’ble Supreme Court of India in a recently passed judgment in Civil Appeal Nos. 6820-6824 of 2018 titled as Union of India through Secretary and others vs. SGT Girish Kumar and others, decided … |

### Treatment candidates (cue wording near a citation or a later name reference)

- **Cue hits:** 15.
  - By attribution: COURT_LIKELY 9, LOWER_FORUM_REPORTED 2, PARTY_SUBMISSION_OR_MIXED 4.
  - Only COURT_LIKELY hits can carry a proposed relation.

| Candidate | Citing judgment | Date | cue p./para | Cue | Attribution | Proposed | Status | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TC-ed5133a3284c | hc-jkl-2026-wp-c-299-2026-jkhc020005882026-1-2026-02-16 | 2026-02-16 | 1/2 | in view of the law laid down | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | nterest @ 6% per annum. 2. The impugned judgment is assailed by the Union of India only on the ground, that, in view of the law laid down by the Hon’ble Supreme Court in the recent judgment titled “Union of India and oth |
| TC-679d28154b56 | hc-jkl-2026-wp-c-526-2026-jkhc020008992026-1-2026-03-03 | 2026-03-03 | 3/6 | is squarely covered by | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | lling for no interference from us in these proceedings. The issue which is sought to be raised in this petition is squarely covered by the judgment of Hon’ble Supreme Court in case titled “Union of India & Ors. Vs. SGT G |
| TC-37a3ef6a6e39 | hc-jkl-2026-wp-c-526-2026-jkhc020008992026-1-2026-03-03 | 2026-03-03 | 3/6 | squarely covered | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | lling for no interference from us in these proceedings. The issue which is sought to be raised in this petition is squarely covered by the judgment of Hon’ble Supreme Court in case titled “Union of India & Ors. Vs. SGT G |
| TC-01cf8c5949cf | hc-ph-2026-cwp-7955-2026-phhc010370702026-1-2026-03-17 | 2026-03-17 | 3/8 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | army personnel, which issue has been in dispute somewhat, has been settled by the Hon’ble Supreme Court of India in a recently passed judgment in Civil Appeal Nos. 6820-6824 of 2018 titled as Union of India through Secre |
| TC-830f1df6403c | hc-ph-2026-cwp-10796-2026-phhc010399782026-1-2026-04-09 | 2026-04-09 | 2/4 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | army personnel, which issue has been in dispute somewhat, has been settled by the Hon’ble Supreme Court of India in a recently passed judgment in Civil Appeal Nos. 6820-6824 of 2018 titled as Union of India through Secre |
| TC-1de45572b962 | hc-ph-2026-cwp-1632-2026-phhc012131162025-1-2026-04-23 | 2026-04-23 | 2/5 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | army personnel, which issue has been in dispute somewhat, has been settled by the Hon’ble Supreme Court of India in a recently passed judgment in Civil Appeal Nos. 6820-6824 of 2018 titled as Union of India through Secre |
| TC-9d6fcd7991fb | hc-ph-2026-cwp-13224-2026-phhc010714772026-1-2026-04-30 | 2026-04-30 | 2/5 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | to the army personnel, which has been in dispute somewhat, has been settled by the Hon’ble Supreme Court of India in a recently passed judgment in Civil Appeal Nos. 6820-6824 of 2018 titled as Union of India through Secr |
| TC-f3d2ba7c8b15 | hc-ph-2026-cwp-14035-2026-phhc010747442026-1-2026-05-06 | 2026-05-06 | 3/10 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | is to be given, which issue has been in dispute somewhat, has been settled by the Hon’ble Supreme Court of India in a recently passed judgment in Civil Appeal Nos. 6820- 6824 of 2018 titled as Union of India through Secr |
| TC-06195757a8fb | hc-ph-2026-cwp-21960-2026-phhc011164962026-1-2026-07-20 | 2026-07-20 | 3/6 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | army personnel, which issue has been in dispute somewhat, has been settled by the Hon’ble Supreme Court of India in a recently passed judgment in Civil Appeal Nos. 6820-6824 of 2018 titled as Union of India through Secre |
| TC-6d98472eccb7 | hc-ph-2026-cwp-17094-2026-phhc010913222026-1-2026-05-27 | 2026-05-27 | 4/7 | is squarely covered by | LOWER_FORUM_REPORTED | - | AUTOMATED_DETECTED | ng from 01.12.2008 till his death 19.03.2013 and said issue is squarely covered by the judgment passed in Civil Appeal Nos. 6820-6824 of 2018 titled as Union of India through Secretary and others vs. S |
| TC-931c83757146 | hc-ph-2026-cwp-17094-2026-phhc010913222026-1-2026-05-27 | 2026-05-27 | 4/7 | squarely covered | LOWER_FORUM_REPORTED | - | AUTOMATED_DETECTED | rom 01.12.2008 till his death 19.03.2013 and said issue is squarely covered by the judgment passed in Civil Appeal Nos. 6820-6824 of 2018 titled as Union of India through Secretary and others vs. S |
| TC-5fca0e03b0b1 | hc-ph-2026-cwp-24977-2024-phhc011292812024-1-2026-05-05 | 2026-05-05 | 2/4 | has been settled | PARTY_SUBMISSION_OR_MIXED | - | AUTOMATED_DETECTED | army personnel, which issue has been in dispute somewhat, has been settled by the Hon’ble Supreme Court of India in a recently passed judgment in Civil Appeal Nos. 6820-6824 of 2018 titled as Union of India through Secre |
| TC-367410498936 | hc-ph-2026-cwp-13239-2026-phhc010720812026-1-2026-04-30 | 2026-04-30 | 2/6 | has been settled | PARTY_SUBMISSION_OR_MIXED | - | AUTOMATED_DETECTED | 18 titled as Union of India through Secretary and others vs. SGT Girish Kumar and others, decided on 12.02.2026, it has been settled that the benefit of arrears of disability pension, including the benefit of ‘broad band |
| TC-11e5e0508393 | hc-jkl-2026-wp-c-408-2026-jkhc020007372026-1-2026-03-11 | 2026-03-11 | 2/5 | is squarely covered by | PARTY_SUBMISSION_OR_MIXED | - | AUTOMATED_DETECTED | perused the material available on record, we are of the considered view that the issue raised in this petition is squarely covered by the judgment of the Hon’ble Supreme Court rendered in the case of “Union of India And  |

### Name-only mentions (not resolved; may be false positives)

- **Pattern:** `girish kumar`. Searched in judgments with no resolved or string-matched edge to this case.
- **Window:** decided on or after 2026-02-12.
- **Hits:** 2 judgments.
  - hc-delhi-2026-w-p-c-4487-2026-dlhc010137522026-1-2026-04-29 (2026-04-29) p.1: ".....Respondents Through: Mr. Devvrat Yadav (SPC) with Mr. Kush Garg and Mr. Girish Kumar, Advocates for UOI. Mr. Sameer Vashisth Standing Counsel for GNCTD, (Civil) alo"
  - hc-ph-2026-cwp-3098-2026-phhc010174492026-1-2026-04-23 (2026-04-23) p.3: "s the case may be. The relevant paragraphs No. 15 to 21 of the judgment in SGT Girish Kumar and others' case (supra) are as under:- "15. Pension, as authoritatively settl"

### Contrary authority / conflicting treatment

- No held judgment was found that declines to follow Girish. The Delhi HC decision of 11-03-2026 applies Tarsem without mentioning Girish (see TARSEM). It is a tension, not an express disagreement.

### Open questions and uncertainty

- Is Girish's 'in rem' reading of Ram Avtar binding beyond broad-banding? Ram Avtar itself is NOT HELD.
- Some J&K HC orders of May-June 2026 reproduce Girish para 22 (about Tarsem) inside a quotation. They appear only in the Tarsem name-only list, because they carry no Tarsem citation string. The treatment words there are Girish's, not the HC's, and no Tarsem treatment candidate is generated from them. (The attribution test suite checks that wording of this kind is classed QUOTED_PASSAGE.)

## Union of India v. Sgt Girish Kumar (reported clarification order, 12-10-2026)

- **Curated record.** DCLR-SC-2026-008. Curated date: 2026-10-12. Case number: Misc. Application concerning C.A. 6820–6824/2018. Reporter: -.
- **C10 held status:** NOT_HELD.
- **C10 official-copy status (copies outside this text layer were not re-read):** NO_COPY_HELD.
- **Held copy in the ad77758d text layer:** NONE.
- **C10 prior reading vs C11:** C10: NOT HELD, 0 hits for '2026 INSC 1113'. C11 repeats the deterministic search below.

### Deterministic search for the clarification order

- **'2026 INSC 1113':** found in 0 held judgments.
- **'Girish Kumar' within 400 characters of 'clarif\*':** 1 held judgments.
  - hc-delhi-2024-w-p-c-14446-2024-dlhc010704192024-1-2024-12-06 p.5: "on the applicability or otherwise of the judgment of the Full Bench of the learned AFT in Ex Sgt. Girish Kumar (supra) or of the judgment of the Supreme Court in V.R. Nanukuttan Nair (supra) to the facts of the case of the petitio"
  - These hits are proximity matches only. They were not read as references to the clarification order.
- **Held judgments dated 2026-10-12:** 1 (hc-delhi-2026-w-p-c-15110-2026-dlhc010492862026-1-2026-10-12 mentions Girish: no).
- **Result:** the clarification order is NOT HELD, and no held judgment cites it by neutral citation.

### Contrary authority / conflicting treatment

- None identified in the held corpus. Absence of a hit is not proof of absence.

### Open questions and uncertainty

- The clarification order (curated DCLR-SC-2026-008; C10 records it as 2026 INSC 1113 of 12-10-2026) is NOT HELD. No held judgment cites it (see the deterministic search below). Its content, and whether it modifies Girish para 22-23, is UNKNOWN. Do not treat Girish as modified or unmodified on this evidence. Acquire the order (C10 ESC-C10-02).

## Union of India v. Major General Shri Kant Sharma

- **Curated record.** DCLR-SC-2015-N06. Curated date: 2015-03-11. Case number: Civil Appeal 7400/2013 and connected appeals. Reporter: (2015) 6 SCC 773.
- **C10 held status:** HELD.
- **C10 official-copy status (copies outside this text layer were not re-read):** NO_SIGNED_OR_OFFICIAL_COURT_PDF; held: SCR_REPORT_RENDITION_AWS_ESCR_MIRROR.
- **Held copy in the ad77758d text layer.** Group JG-86de3643e66e (EXACT_DUPLICATE;MISSING_OFFICIAL_ORIGINAL). Renditions: SCR_REPORT_RENDITION_AWS_ESCR_MIRROR.
  - Records: sc-2015-union-of-india-ors-2015insc206 (sha 86de3643e66e, 50 pp.).
  - Neutral citation: 2015 INSC 206. Reported: [2015] 4 S.C.R. 676. Date: 2015-03-11.
- **C10 prior reading vs C11:** C10: 'OVERRULED in documentary wording' by Parashotam para 32 (official copy p.22). C11: the wording is confirmed in the held SCR rendition at p.17 (para 32). It is recorded as a proposed OVERRULES edge for adviser review, not as a validated status.

### Verified readings

| Reading | Kind | Document | p. | para | Quotation (verbatim) | Note |
| --- | --- | --- | --- | --- | --- | --- |
| RD-PARASHOTAM-T1 | TREATMENT | sc-2023-union-of-india-ors-2023insc265 | 17 | 32 | "We have, thus, no hesitation in concluding that the judgment in" | Para 32 opening (printed report page 614 of [2023] 3 SCR). |
| RD-PARASHOTAM-T2 | TREATMENT | sc-2023-union-of-india-ors-2023insc265 | 17 | 32 | "Shri Kant Sharma & Anr.24 case does not lay down the correct law and is in conflict with judgments of the Constitution" | Exact wording in the held SCR rendition: 'does not lay down the correct law' (the '24' is a footnote marker; fn 24 reads '(supra)'). The word 'overruled' is not used. |
| RD-PARASHOTAM-T3 | TREATMENT | sc-2023-union-of-india-ors-2023insc265 | 18 | 32 | "power under Article 226 of the Constitution by the High Court. However, in respect of matters of self-discipline, the principles already stand enunciated." | Para 32 ends on p.18 (report page 615) with a reservation for 'matters of self-discipline'. |
| RD-PARASHOTAM-ED | REPORTER_EDITORIAL | sc-2023-union-of-india-ors-2023insc265 | 4 | - | "& Anr. (2015) 6 SCC 773 : [2015] 4 SCR 676 – held not correct law." | Reporter's case-law entry (editorial). |
| RD-SHRIKANT-H1 | HOLDING | sc-2015-union-of-india-ors-2015insc206 | 47 | 34(iv) | "226 of the Constitution if an effective alternative remedy is available to the aggrieved person or the statute" | Para 34(iv) summary: 'The High Court will not entertain a petition under Article 226 ...' (Refer: Nivedita Sharma). The same words also occur on p.44 inside a quotation of an earlier judgment. |
| RD-SHRIKANT-H2 | HOLDING | sc-2015-union-of-india-ors-2015insc206 | 49 | 38 | "we are of the view that Delhi High Court was not" | Para 38: Delhi HC 'not justified in entertaining the petition under Article 226' against AFT orders. |
| RD-SHRIKANT-H3 | HOLDING | sc-2015-union-of-india-ors-2015insc206 | 33 | 25 | "judicial review vested in the High Court under Article 226 is one of the basic essential features of theConstitution" | Para 25 (and 34(i) p.47): Shri Kant Sharma itself accepts that Art. 226 review is a basic feature; its restriction operates through discretion/alternative remedy. |
| RD-SHRIKANT-BENCH | BENCH | sc-2015-union-of-india-ors-2015insc206 | 1 | - | "[SUDHANSU JYOTI MUKHOPADHAYA AND" | Two-Judge Bench (with N.V. Ramana J., next line). |
| RD-JKHC-SKS | LATER_RELIANCE | hc-jkl-2025-wp-c-2370-2025-jkhc010050362025-1-2025-10-06 | 2 | 6 | "Since the Apex Court in case titled as “Union of India vs. Shri Kant Sharma (2015) 6 SCC 773 has specifically provided that High Court" | J&K HC (Srinagar), 06-10-2025, single Judge: relies on Shri Kant Sharma more than two years after Parashotam; Parashotam is not cited in this order. |
| RD-JKHC-SKS2 | LATER_RELIANCE | hc-jkl-2025-wp-c-2370-2025-jkhc010050362025-1-2025-10-06 | 3 | 6 | "should refrain from entertaining petitions under Article 226 if alternative or effective remedy is available" | Context: an original petition (not a writ against an AFT order); the AFT remedy was available. |

### Citing judgments (graph)

- **Distinct citing judgments:** 17.
  - By court: Allahabad High Court 4, High Court of Delhi 4, High Court of Jammu and Kashmir 6, Supreme Court of India 3.
  - By year: 2017: 6, 2020: 2, 2021: 3, 2022: 3, 2023: 1, 2025: 2.

All Supreme Court citing edges are listed, plus the 12 most recent High Court edges (of 14). The paragraph number is heuristic.

| Citing judgment | Court | Date | p. | para | Method | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| sc-2020-balkrishna-ram-2020insc26 | SC | 2020-01-09 | 7 | 10 | CURATED_CROSSWALK_C10_HELD;REPORTER_CITATION_METADATA | Court under Article 227 of the Constitution but 2 2012 (1) ESC 386 (All); Special Appeal (Defective) No.610 of 2002 3 (2015) 6 SCC 773 BALKRISHNA RAM v. UNION OF INDIA AND ANR. [DEEPAK GUPTA, J.] [[page 8]] A B C D E F G H 588 SUPREME COURT RE |
| sc-2023-union-of-india-ors-2023insc265 | SC | 2023-03-21 | 9 | 13 | CURATED_CROSSWALK_C10_HELD;REPORTER_CITATION_METADATA | ent since that 8 Jurisdiction, powers and authority in matters of appeal against court-martial 9 (1990) 4 SCC 594 10 (2015) 6 SCC 773 [[page 10]] A B C D E F G H 607 judgment sought to create a complete bar to the High Court’s power to review |
| sc-2025-s-k-jain-2025insc1215 | SC | 2025-10-10 | 7 | 13 | CURATED_CROSSWALK_C10_HELD;REPORTER_CITATION_METADATA | ed 03.09.2012 passed by the Tribunal. In the aforesaid factual background, this appeal arises for our consideration. 1 (2015) 6 SCC 773 [[page 8]] [2025] 10 S.C.R.  579 S.K. Jain v. Union of India & Anr. (II) SUBMISSIONS OF APPELLANT 14. Learned co |
| hc-jkl-2025-wp-c-2370-2025-jkhc010050362025-1-2025-10-06 | HC Jammu and Kashmir | 2025-10-06 | 2 | 6 | CURATED_CROSSWALK_C10_HELD | shall not include matters relating to- 6. Since the Apex Court in case titled as “Union of India vs. Shri Kant Sharma (2015) 6 SCC 773 has specifically provided that High Court [[page 3]] WP(C) 2370/2025 Page 3 of 3 should refrain from entertaining … |
| hc-delhi-2022-w-p-c-15180-2022-dlhc010409142022-1-2022-11-03 | HC Delhi | 2022-11-03 | 3 | 6 | CURATED_CROSSWALK_C10_HELD | unsel for petitioner are as under:- 13. What this Court in Shri Kant Sharma case [Union of India v. Shri Kant Sharma, (2015) 6 SCC 773 : (2015) 2 SCC (L&S) 386] held was that though the power of the High Court under Article 226 of the Constitution i… |
| hc-allahabad-2022-wria-19332-2021-uphc012115002021-1-2022-01-20 | Allahabad High Court | 2022-01-20 | 3 | 6 | CURATED_CROSSWALK_C10_HELD | elied upon the judgment of the Apex Court in Union of India Vs Major General Shri Kant Sharma and others, reported in 2015 (6) SCC 773 and judgment dated 1st November, 2021 passed by this Court in Writ-A No 15281 of 2021 – Ex-Hav Clerk (Stores) Ram … |
| hc-allahabad-2022-wria-17043-2021-uphc011879992021-1-2022-01-20 | Allahabad High Court | 2022-01-20 | 3 | 6 | CURATED_CROSSWALK_C10_HELD | elied upon the judgment of the Apex Court in Union of India Vs Major General Shri Kant Sharma and others, reported in 2015 (6) SCC 773 and judgment dated 1st November, 2021 passed by this Court in Writ-A No 15281 of 2021 – Ex-Hav Clerk (Stores) Ram … |
| hc-allahabad-2021-wria-15281-2021-uphc011718502021-1-2021-11-01 | Allahabad High Court | 2021-11-01 | 1 | 2 | CURATED_CROSSWALK_C10_HELD | 0 of the Act before the Supreme Court. In the case of Union of India & Ors. Vs. Major General Shri Kant Sharma & Anr. (2015) 6 SCC 773 , Hon'ble Supreme Court held as under : “33. Statutory Remedy In Union of India vs. Brigadier P.S. Gill, (2012) 4 … |
| hc-delhi-2021-w-p-c-5495-2021-dlhc010180182021-1-2021-05-27 | HC Delhi | 2021-05-27 | 8 | 15 | CURATED_CROSSWALK_C10_HELD | creation of a specialist Tribunal by the Act. Though at one time in Union of India Vs. Major General Shri Kant Sharma (2015) 6 SCC 773, a view was taken that Article 226 of the Constitution of India cannot be invoked [[page 9]] W.P.(C) No.5495/2021 … |
| hc-allahabad-2021-wria-1652-2021-uphc010174672021-1-2021-03-25 | Allahabad High Court | 2021-03-25 | 1 | - | CURATED_CROSSWALK_C10_HELD | le the Apex Court in paragraphs 42 and 43 of judgement and order passed in Union of India v. Srikant Sharma reported in 2015 (6) SCC 773. Confronted with this situation, learned counsel for the petitioner prays that the petitioner does not want to p… |
| hc-delhi-2020-w-p-c-2809-2020-dlhc010157312020-1-2020-03-13 | HC Delhi | 2020-03-13 | 2 | 4 | CURATED_CROSSWALK_C10_HELD | as per the dicta of the W.P.(C) 2809/2020 Page 1 of 4 [[page 2]] Supreme Court in Union of India Vs. Shri Kant Sharma (2015) 6 SCC 773. Attention is however drawn to Bal Krishna Sharma Vs. Union of India AIR 2020 SC 341, stating that though the same… |
| hc-jkl-2017-swp-2017-2017-jkhc020023852017-1-2017-08-28 | HC Jammu and Kashmir | 2017-08-28 | 1 | - | CURATED_CROSSWALK_C10_HELD | said view has been taken by the Supreme Court in the case of Union of India & others V. Major General Sri Kant Sharma, (2015) 6 SCC 773. However, it is fairly pointed out by the learned Assistant Solicitor [[page 2]] Page 2 of 2 General of India tha… |
| hc-jkl-2017-owp-156-2014-jkhc020021882014-1-2017-08-09 | HC Jammu and Kashmir | 2017-08-09 | 1 | - | CURATED_CROSSWALK_C10_HELD | based on the decision of the Hon’ble Supreme Court in Union of India & ors. v. Major General Shri Kant Sharma & anr. (2015) 6 SCC 773, grievance which is the subject-matter of the instant writ petition, is maintainable only before the Armed Forces Tr |
| hc-jkl-2017-swp-1833-2017-jkhc020066192017-1-2017-08-02 | HC Jammu and Kashmir | 2017-08-02 | 1 | - | CURATED_CROSSWALK_C10_HELD | based on the decision of the Hon’ble Supreme Court in Union of India & ors. v. Major General Shri Kant Sharma & anr. (2015) 6 SCC 773, grievance which is the subject-matter of the instant writ petition, is maintainable only before the Armed Forces T… |
| hc-jkl-2017-swp-1461-2017-jkhc020077472017-1-2017-08-02 | HC Jammu and Kashmir | 2017-08-02 | 1 | - | CURATED_CROSSWALK_C10_HELD | based on the decision of the Hon’ble Supreme Court in Union of India & ors. v. Major General Shri Kant Sharma & anr. (2015) 6 SCC 773, grievance which is the subject-matter of the instant writ petition, is maintainable only before the Armed Forces T… |

### Treatment candidates (cue wording near a citation or a later name reference)

- **Cue hits:** 9.
  - By attribution: COURT_LIKELY 2, REPORTER_EDITORIAL 7.
  - Only COURT_LIKELY hits can carry a proposed relation.

| Candidate | Citing judgment | Date | cue p./para | Cue | Attribution | Proposed | Status | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TC-ca11c261fb84 | hc-allahabad-2021-wria-15281-2021-uphc011718502021-1-2021-11-01 | 2021-11-01 | 7/11 | in view of the law laid down | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | cretion to entertain the present writ petition particularly in view of the law laid down by Hon'ble Supreme Court in the case of Union of India & Ors. Vs. Major General Shri Kant Sharma & Anr (supra). Consequently and wi |
| TC-222df5c885ad | sc-2023-union-of-india-ors-2023insc265 | 2023-03-21 | 17/32 | does not lay down the correct law | COURT_LIKELY | OVERRULES | LEGAL_INTERPRETATION_ADVISER_REVIEW | hesitation in concluding that the judgment in Major General Shri Kant Sharma & Anr.24 case does not lay down the correct law and is in conflict with judgments of the Constitution Bench |
| TC-bc65141e8628 | sc-2023-union-of-india-ors-2023insc265 | 2023-03-21 | 4/- | followed | REPORTER_EDITORIAL | - | AUTOMATED_DETECTED | 3 : [2015] 4 SCR 676 – held not correct law. Case law reference [1983] 1 SCR 393 referred to Para 1 [1997] 2 SCR 1186 followed Para 4 [1973] Suppl. SCR 1 referred to Para 5 [1990] 11 Suppl. SCR 44 followed Para 12 [2019] |
| TC-a29b1dca2688 | sc-2023-union-of-india-ors-2023insc265 | 2023-03-21 | 4/- | followed | REPORTER_EDITORIAL | - | AUTOMATED_DETECTED | 3] Suppl. SCR 1 referred to Para 5 [1990] 11 Suppl. SCR 44 followed Para 12 [2019] 16 SCR 1 followed Para 15 [2015] 4 SCR 676 held not correct law Para 13 UNION OF INDIA & ORS. v. PARA |
| TC-6ccb00b881a7 | sc-2023-union-of-india-ors-2023insc265 | 2023-03-21 | 4/- | followed | REPORTER_EDITORIAL | - | AUTOMATED_DETECTED | [1990] 11 Suppl. SCR 44 followed Para 12 [2019] 16 SCR 1 followed Para 15 [2015] 4 SCR 676 held not correct law Para 13 UNION OF INDIA & ORS. v. PARA |
| TC-0da5ab9b2111 | sc-2020-balkrishna-ram-2020insc26 | 2020-01-09 | 4/- | held inapplicable | REPORTER_EDITORIAL | - | AUTOMATED_DETECTED | ia and Others v. Major General Shri Kant Sharma and Another (2015) 6 SCC 773 : [2015] 4 SCR 676 – held inapplicable. Union of India v. T.R. Varma AIR 1957 SC 882 : [1958] SCR |
| TC-365408fd113f | sc-2020-balkrishna-ram-2020insc26 | 2020-01-09 | 5/- | held inapplicable | REPORTER_EDITORIAL | - | AUTOMATED_DETECTED | [[page 5]] A B C D E F G H 585 Case Law Reference [2015] 4 SCR 676 held inapplicable Para 9 [1997] 2 SCR 1186 followed Para 11 [1958] SCR 499 |
| TC-ee022012a311 | sc-2020-balkrishna-ram-2020insc26 | 2020-01-09 | 5/- | followed | REPORTER_EDITORIAL | - | AUTOMATED_DETECTED | [[page 5]] A B C D E F G H 585 Case Law Reference [2015] 4 SCR 676 held inapplicable Para 9 [1997] 2 SCR 1186 followed Para 11 [1958] SCR 499 referred to Para 14 2019 (15) SCAL |
| TC-ba574b084d5e | sc-2020-balkrishna-ram-2020insc26 | 2020-01-09 | 5/- | followed | REPORTER_EDITORIAL | - | AUTOMATED_DETECTED | [[page 5]] A B C D E F G H 585 Case Law Reference [2015] 4 SCR 676 held inapplicable Para 9 [1997] 2 SCR 1186 followed Para 11 [1958] SCR 499 referred to Para 14 2019 (15) SCALE 615 followed Para 16 CIVIL APPELLATE JURIS |

### Name-only mentions (not resolved; may be false positives)

- **Pattern:** `kant sharma | shri kant`. Searched in judgments with no resolved or string-matched edge to this case.
- **Window:** decided on or after 2015-03-11.
- **Hits:** 11 judgments.
  - hc-delhi-2026-w-p-c-14091-2026-dlhc010458182026-1-2026-09-24 (2026-09-24) p.1: "nts Through: Ms Ira Singh, SPC with Ms Pinky Pawar, GP alongwith Wg. Cdr. Gagan Kant Sharma. CORAM: HON'BLE MR. JUSTICE NITIN WASUDEO SAMBRE HON'BLE MR. JUSTICE SANJAY SH"
  - hc-jkl-2025-wp-c-1429-2025-jkhc010029452025-1-2025-06-24 (2025-06-24) p.2: "down in Supreme Court in the case titled as “Union of India Vs. Major General Shri Kant Sharma and Anr”, reported in (2015), 6 SCC 773, wherein the Hon’ble Supreme Co"
  - hc-jkl-2024-owp-1079-2016-jkhc010036492016-1-2024-07-24 (2024-07-24) p.7: "e Apex Court passed in case titled as “Union of India & Ors. Vs. Major General Shri Kant Sharma” reported in 2015 (6) SCC page 773 wherein it has been held that the ju"
  - hc-delhi-2023-w-p-c-12311-2023-dlhc010371712023-1-2023-09-19 (2023-09-19) p.1: "ment delivered on: 19.09.2023 W.P.(C) 12311/2023 &CM APPL. 48500/2023 MAJ GEN SHRI KANT SHARMA SM VSM RETD ..... Petitioner versus UNION OF IND"
  - hc-allahabad-2019-wria-18192-2019-uphc012150702019-1-2019-11-16 (2019-11-16) p.1: "on of the Apex Court in the case of Union of India and others Vs. Major General Shri Kant Sharma and another, (2015) 6 Supreme Court Cases 773, he stated that against th"
  - sc-2019-amit-kumar-roy-2019insc720 (2019-07-03) p.7: "tayed. In view of the decision of this Court in Union of India v Major General Shri Kant Sharma8, the High Court held that it had no jurisdiction to entertain the writ"
  - hc-jkl-2017-swp-2612-2000-jkhc020001552000-1-2017-07-31 (2017-07-31) p.4: "s decision rendered in the case of Union of India and others v. Major General Shri Kant Sharma and another; AIR 2015 SC 2465 is concerned, the same has no bearing on"
  - hc-ph-2017-cwp-21340-2016-phhc010866112016-1-2017-02-27 (2017-02-27) p.1: "wn by the Hon'ble Supreme Court in Union of India and others Vs. Major General Shri Kant Sharma and another 2015(2) SCT 519, this Court has held in CWP No.6958 of 2012"
  - hc-ph-2015-cwp-17387-2015-phhc010811672015-1-2015-09-24 (2015-09-24) p.4: "f the Supreme Court in the case of Union of India and others vs. Major General Shri Kant Sharma and another, 2015(2) SCT 519 to contend that the power of judicial revi"
  - hc-ph-2015-cwp-6958-2012-phhc010887172012-1-2015-05-18 (2015-05-18) p.3: "this document [[page 3]]              General Shri Kant Sharma & Anr., 2015(2) SCT 519. Out of various conclusions drawn therein, suf"

### Contrary authority / conflicting treatment

- Parashotam (three Judges) para 32: Shri Kant Sharma 'does not lay down the correct law' (RD-PARASHOTAM-T2). This is explicit source wording to that effect. The word 'overruled' is not used. The paragraph ends with a reservation for 'matters of self-discipline' (RD-PARASHOTAM-T3).
- The J&K HC (06-10-2025) still relies on Shri Kant Sharma for the alternative-remedy proposition, without citing Parashotam (RD-JKHC-SKS, RD-JKHC-SKS2). This conflicting later treatment is preserved.

### Open questions and uncertainty

- What survives of Shri Kant Sharma? Para 34(i)-(ii) (Art. 226 is a basic feature; due regard to legislative intent) are consistent with Parashotam. The proposition in para 37-38 (HC should not entertain writs against AFT orders) is what Parashotam rejects. Whether para 34(iii)-(iv) (alternative remedy) survives as a discretionary rule is an adviser question (C10 ESC-C10-03).
- Typed edge: the tool proposes OVERRULES (Parashotam -> Shri Kant Sharma) at LEGAL_INTERPRETATION_ADVISER_REVIEW only. Nothing is marked LEGALLY_VALIDATED. An adviser may prefer 'disapproved' or 'declared not good law'.

## Union of India v. Parashotam Dass

- **Curated record.** DCLR-SC-2023-009. Curated date: 2023-03-21. Case number: Civil Appeal No. 447 of 2023 with connected matters. Reporter: -.
- **C10 held status:** HELD.
- **C10 official-copy status (copies outside this text layer were not re-read):** YES_OFFICIAL_COURT_PDF. Working store: downloads/independent-reviewer-B/parashotam_2023.pdf;downloads/judgment-auditor/parashotam_2023.pdf.
- **Held copy in the ad77758d text layer.** Group JG-483b70cbbe27 (DIFFERENT_RENDITION). Renditions: SCR_REPORT_RENDITION_AWS_ESCR_MIRROR, SC_OFFICIAL_COURT_PDF.
  - Records: sc-2023-union-of-india-ors-2023insc265 (sha 483b70cbbe27, 20 pp.).
  - Neutral citation: 2023 INSC 265. Reported: [2023] 3 S.C.R. 598. Date: 2023-03-21.
- **C10 prior reading vs C11:** C10: APPLIED by SC 2023 INSC 1074; DISTINGUISHED by Allahabad HC WRIA 2923/2026 p.5. C11: see the treatment candidates below. These C10 readings were not re-read unless listed.

### Verified readings

| Reading | Kind | Document | p. | para | Quotation (verbatim) | Note |
| --- | --- | --- | --- | --- | --- | --- |
| RD-PARASHOTAM-T1 | TREATMENT | sc-2023-union-of-india-ors-2023insc265 | 17 | 32 | "We have, thus, no hesitation in concluding that the judgment in" | Para 32 opening (printed report page 614 of [2023] 3 SCR). |
| RD-PARASHOTAM-T2 | TREATMENT | sc-2023-union-of-india-ors-2023insc265 | 17 | 32 | "Shri Kant Sharma & Anr.24 case does not lay down the correct law and is in conflict with judgments of the Constitution" | Exact wording in the held SCR rendition: 'does not lay down the correct law' (the '24' is a footnote marker; fn 24 reads '(supra)'). The word 'overruled' is not used. |
| RD-PARASHOTAM-T3 | TREATMENT | sc-2023-union-of-india-ors-2023insc265 | 18 | 32 | "power under Article 226 of the Constitution by the High Court. However, in respect of matters of self-discipline, the principles already stand enunciated." | Para 32 ends on p.18 (report page 615) with a reservation for 'matters of self-discipline'. |
| RD-PARASHOTAM-ED | REPORTER_EDITORIAL | sc-2023-union-of-india-ors-2023insc265 | 4 | - | "& Anr. (2015) 6 SCC 773 : [2015] 4 SCR 676 – held not correct law." | Reporter's case-law entry (editorial). |
| RD-PARASHOTAM-BENCH | BENCH | sc-2023-union-of-india-ors-2023insc265 | 1 | - | "[SANJAY KISHAN KAUL, B. V. NAGARATHNA AND ABHAY S. OKA, JJ.]" | Three-Judge Bench. |

### Citing judgments (graph)

- **Distinct citing judgments:** 6.
  - By court: Allahabad High Court 1, High Court of Delhi 3, High Court of Punjab and Haryana 1, Supreme Court of India 1.
  - By year: 2023: 1, 2024: 1, 2025: 1, 2026: 3.

All Supreme Court citing edges are listed, plus the 5 most recent High Court edges (of 5). The paragraph number is heuristic.

| Citing judgment | Court | Date | p. | para | Method | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| sc-2023-union-of-india-ors-2023insc1074 | SC | 2023-12-14 | 3 | - | PARTY_YEAR_COURT | SCC OnLine SC 987; Union of India & Ors v. Ilmo Devi & Anr., 2021 SCC OnLine SC 899; Union of India v Parashotam Dass, 2023 SCC OnLine SC 314; Chandra Mohan Verma v. State of Uttar Pradesh, [2020] 1 SCR 1158: (2020) 13 SCC 261; Union of India v. Uza… |
| hc-delhi-2026-w-p-c-12024-2026-dlhc010387012026-1-2026-08-19 | HC Delhi | 2026-08-19 | 2 | 2 | REPORTER_CITATION_METADATA | aid contention, specific reliance has been placed on the judgment in the matter of Union of India v. Parashotam Dass, [2023] 3 S.C.R. 598, more particularly, paragraph 29 thereof, which reads as under:- “29. We believe that there is no necessity to … |
| hc-allahabad-2026-wria-2923-2026-uphc011159512026-1-2026-04-02 | Allahabad High Court | 2026-04-01 | 2 | 8 | NEUTRAL_CITATION_METADATA | 13 decided on 08.12.2025 by Madhya Pradesh High Court at Jabalpur Bench, Union of India and others v. Parashotam Dass : 2023 INSC 265, Paritosh Kumar v. Union of India and others : 2013 (9) ADJ 1, U.P. Rashtriya Chini Mills Limited v. State of U.P. … |
| hc-delhi-2026-w-p-c-254-2026-dlhc011083512025-1-2026-01-09 | HC Delhi | 2026-01-09 | 6 | 14 | CASE_NUMBER_PLUS_PARTY | aw laid down by the Supreme Court in judgment dated 21.03.2023 in titled as Union of India & Ors. v. Parashotam Dass, Civil Appeal No.447/2023. 15. Having heard the learned counsel for the petitioners and perused the record, at the outset, we may st… |
| hc-ph-2025-cwp-8888-2025-phhc011126632024-1-2025-05-14 | HC Punjab and Haryana | 2025-05-14 | 1 | 2 | NEUTRAL_CITATION_METADATA | filed in 2025 solely based on the judgment passed by Hon’ble the Supreme Court in Union of India vs. Parashotam Das, 2023 INSC 265. Prior to that right of appeal was available if there was any legal point involved but the petitioners chose not to fi |
| hc-delhi-2024-w-p-c-12202-2023-dlhc010366402023-1-2024-03-18 | HC Delhi | 2024-03-18 | 2 | 2 | PARTY_YEAR_COURT | No.261 of 2021. 2. In view of the recent decision rendered by this Court in Union of India & Ors. vs. Parashotam Dass, 2023 SCC Online SC 314, the appellant has an efficacious alternative remedy to assail the order passed by the Armed Forces Tribuna… |

### Treatment candidates (cue wording near a citation or a later name reference)

- **Cue hits:** 2.
  - By attribution: PARTY_SUBMISSION_OR_MIXED 1, QUOTED_PASSAGE 1.
  - Only COURT_LIKELY hits can carry a proposed relation.

| Candidate | Citing judgment | Date | cue p./para | Cue | Attribution | Proposed | Status | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TC-2c670517b96b | hc-allahabad-2026-wria-2923-2026-uphc011159512026-1-2026-04-02 | 2026-04-01 | 5/18 | have no application | QUOTED_PASSAGE | - | AUTOMATED_DETECTED | re WRIA No. 2923 of 2026 4 [[page 5]] concerned, the same have no application to the subject matter of the present case as in the case of Parashotam Dass (Supra), the only issue before the Hon'ble Supreme Court wa |
| TC-7f92daea43fd | hc-delhi-2026-w-p-c-254-2026-dlhc011083512025-1-2026-01-09 | 2026-01-09 | 6/14 | in view of the law laid down | PARTY_SUBMISSION_OR_MIXED | - | AUTOMATED_DETECTED | l authorities, has discharged its obligation. He also submits that, the petitioners have approached the Court in view of the law laid down by the Supreme Court in judgment dated 21.03.2023 in titled as Union of India & O |

### Name-only mentions (not resolved; may be false positives)

- **Pattern:** `parashotam dass`. Searched in judgments with no resolved or string-matched edge to this case.
- **Window:** decided on or after 2023-03-21.
- **Hits:** 5 judgments.
  - hc-delhi-2026-w-p-c-5992-2026-dlhc010190732026-1-2026-05-05 (2026-05-05) p.12: "respect to Article 30 sands clarified by the judgment of the Supreme Court in Parashotam Dass. Section 30 merely provides that, against a decision of the AFT, an appeal lie"
  - hc-delhi-2026-w-p-c-18927-2025-dlhc011011542025-1-2026-02-25 (2026-02-25) p.2: "e position of law as settled by the Supreme Court in Union of India & Ors. v. Parashotam Dass, reported in 2025 (5) SCC 786, these petition shall be This is a digitally sig"
  - hc-delhi-2024-w-p-c-16684-2023-dlhc010562532023-1-2024-08-28 (2024-08-28) p.4: "his Court. In this regard, reliance is placed on the case of Union of India Vs Parashotam Dass, (2023) SCC OnLine SC 314. Digitally Signed By:NEELAM Signing Date:28.08.2024"
  - hc-delhi-2023-w-p-c-16015-2023-dlhc010521972023-1-2023-12-13 (2023-12-13) p.2: "e may be had to the judgment of the Supreme Court in Union of India & Ors. vs. Parashotam Dass: 2023 SCC online 314, wherein the Supreme Court has held that the decision of"
  - hc-delhi-2023-w-p-c-12311-2023-dlhc010371712023-1-2023-09-19 (2023-09-19) p.3: "he decision dated 21.02.2023 of the Supreme Court in Union of India & Ors. Vs. Parashotam Dass 2023 SCC OnLine 314 whereby the Supreme Court has held that there is no per se"

### Contrary authority / conflicting treatment

- No held decision questions Parashotam. The J&K HC order of 06-10-2025 does not engage with it (see SHRIKANT).

### Open questions and uncertainty

- C10 located para 32 on p.22 of the official court PDF. That copy is outside the ad77758d text layer and was not re-read here. In the held SCR rendition, para 32 runs from p.17 to p.18 (report pp.614-615).
- Scope of the 'self-discipline' reservation (para 32, last sentence) is not defined in the paragraph.

## Ranjit Thakur v. Union of India

- **Curated record.** DCLR-SC-1987-R01. Curated date: 1987-10-15. Case number: Civil Appeal 2630 of 1987. Reporter: (1987) 4 SCC 611; [1988] 1 SCR 512.
- **C10 held status:** HELD.
- **C10 official-copy status (copies outside this text layer were not re-read):** NO_SIGNED_OR_OFFICIAL_COURT_PDF; held: JUDIS_TYPED_TEXT_RENDITION+SCR_REPORT_RENDITION_AWS_ESCR_MIRROR. Working store: downloads/citation-codes/ranjit_judis8566.pdf.
- **Held copy in the ad77758d text layer.** Group JG-35b9c948fe62 (DIFFERENT_RENDITION;MISSING_OFFICIAL_ORIGINAL). Renditions: JUDIS_TYPED_TEXT_RENDITION, SCR_REPORT_RENDITION_AWS_ESCR_MIRROR.
  - Records: sc-1987-ranjit-thakur-1987insc285 (sha 35b9c948fe62, 13 pp.).
  - Neutral citation: 1987 INSC 285. Reported: [1988] 1 S.C.R. 512. Date: 1987-10-15.
- **C10 prior reading vs C11:** C10: JUDIS + SCR renditions; date defect '3.?.1986' (SCR-C01).

### Verified readings

| Reading | Kind | Document | p. | para | Quotation (verbatim) | Note |
| --- | --- | --- | --- | --- | --- | --- |
| RD-RANJIT-H1 | HOLDING | sc-1987-ranjit-thakur-1987insc285 | 12 | - | "offence as to shock the conscience and amount in itself to conclusive evidence of bias. The doctrine of proportionality, as part of the con-" | Judgment body (after 'delivered by', p.5). The same proposition also appears in the reporter's headnote on p.4. |

### Citing judgments (graph)

- **Distinct citing judgments:** 41.
  - By court: Allahabad High Court 8, High Court of Delhi 16, High Court of Jammu and Kashmir 4, High Court of Punjab and Haryana 4, Supreme Court of India 9.
  - By year: 2008: 1, 2010: 1, 2011: 1, 2012: 2, 2013: 4, 2014: 1, 2015: 3, 2016: 3, 2017: 1, 2018: 1, 2019: 7, 2022: 1, 2023: 4, 2024: 3, 2025: 7, 2026: 1.

All Supreme Court citing edges are listed, plus the 12 most recent High Court edges (of 32). The paragraph number is heuristic.

| Citing judgment | Court | Date | p. | para | Method | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| sc-2008-ex-constable-ramvir-singh-2008insc1475 | SC | 2008-12-18 | 10 | 12 | CURATED_CROSSWALK_C10_HELD | urisdiction D under Article 226 of the Constitution of India. It was so held in Ranjit Thakur vs. Union oflndia & Ors. [(1987) 4 SCC 611], stating: "25. Judicial review generally speaking, is not directed E against a decision, but is directed agains… |
| sc-2010-charanjit-lamba-2010insc364 | SC | 2010-07-06 | 3 | - | CURATED_CROSSWALK_C10_HELD | CC 162 - relied on. Bhagat Ram v. State of Himacha/ Pradesh (1983) 2 SCC E 442; Ranjit Thakur v. Union of India & Ors. (1987) 4 SCC 611; Ex-Naik Sardar Singh v. Union of India & Ors. (1991) 3 SCC 213; Hind Construction & Engineering Co. Ltd. v. Work… |
| sc-2011-union-of-india-ors-2011insc672 | SC | 2011-09-12 | 27 | 19 | REPORTER_CITATION_METADATA | as a part of the decision making process by Court Martial, have been explained, in Ranjit Thakur vs. Union of India - 1987 (4) SCC 611, where this Court interfered with the punishment imposed by a court martial C on the ground that it was strikingly… |
| sc-2012-chandra-kumar-chopra-2012insc231 | SC | 2012-05-11 | 5 | - | CURATED_CROSSWALK_C10_HELD;REPORTER_CITATION_METADATA | State of Himachal Pradesh and others B (1981) 4 SCC 716: 1982 (1) SCR 1043; Ranjit Thakur v. Union of India and others (1987) 4 SCC 611: 1988 (1) SCR 512; Mis. Crawford Bayley & Co. & Ors. v. Union of India & Ors. AIR 2006 SC 2544: 2006 (3) Suppl. S… |
| sc-2013-manoj-h-mishra-2013insc227 | SC | 2013-04-09 | 6 | - | CURATED_CROSSWALK_C10_HELD;REPORTER_CITATION_METADATA | bes Mazdoor Sabha & Ors. (1980) 2 SCC 593: 1980 (2) SCR 146 - distinguished. D Ranjit Thakur vs. Union of India & Ors. (1987) 4 SCC 611: 1988 (1) SCR 512; Parivartan & Ors. vs. Union of India & Ors. [Order of Supreme Court in W.P.(C) No.93 of 2004 a… |
| sc-2013-sr-tewari-2013insc361 | SC | 2013-05-28 | 20 | 18 | PARTY_YEAR_COURT | ary, and thus, would violate the mandate of Article 14 of the Constitution. In Ranjit Thakur v. Union of India & Ors., AIR 1987 SC 2386, this Court observed as under: C "But the. sentence has to suit the offence and the offender. It should not be vi… |
| sc-2013-union-of-india-and-others-2013insc705 | SC | 2013-10-18 | 11 | - | REPORTER_CITATION_METADATA | (2004) 11 sec 625 referred to Para 38 2012 (5) SCR 1029 referred to Para 39 G 2013 (1) SCR 1 , referred to Para 40 1988 (1) SCR 512 referred to Para 42 H [[page 12]] A B c 506 SUPREME COURT REPORTS [2013] 16 S.C.R. (1991) 2 sec 382 referred to P |
| sc-2017-kamini-jaiswal-2017insc1112 | SC | 2017-11-14 | 6 | 9 | PARALLEL_CITATION_LEARNED | 10 SCC 337 : [2009] 15 SCR 317 ; Amrik Singh v. State (Delhi Admn.) (1971) 3 SCC 215 ; Bal Kishan Giri v. State of U.P. (2014) 7 SCC 280 : [2014] 6 SCR 545 - relied on. [[page 7]] KAMINI JAISWAL v. UNION OF INDIA & ANR. 195 Union of India & Ors. v. … |
| sc-2019-union-of-india-ors-2019insc1083 | SC | 2019-09-25 | 16 | 15 | CURATED_CROSSWALK_C10_HELD;REPORTER_CITATION_METADATA | ingh Dhaliwal6, Union of India and Others Vs. Dwarka Prasad Tiwari7 and S.R. Tewari Vs. Union of India and Another8. 1 (1987) 4 SCC 611 2 (1995) 6 SCC 749 3 (2011) 13 SCC 553 4 (1989) 2 SCC 177 5 (2003) 3 SCC 309 6 (1998) 1 SCC 756 7 (2006) 10 SCC 3 |
| hc-delhi-2026-w-p-c-4357-2018-dlhc010134402018-1-2026-01-07 | HC Delhi | 2026-01-07 | 12 | 23 | CURATED_CROSSWALK_C10_HELD | tream in the Indian legal jurisprudence. 23. Further, the Apex Court in the case of Ranjit Thakur v. Union of India, (1987) 4 SCC 611, observed as follows:- “Re contention (d): 25. Judicial review generally speaking, is not directed against a decisi… |
| hc-ph-2025-cwp-12291-2018-phhc010824572018-1-2025-12-12 | HC Punjab and Haryana | 2025-12-12 | 8 | 3 | CURATED_CROSSWALK_C10_HELD | and 16 of the Constitution. Support may be derived from the Apex court judgement of “Ranjit Thakur v. Union of India (1987) 4 SCC 611” wherein it was held as follows: NAINA KATHIAT 2026.01.14 16:09 I attest to the accuracy and integrity of this docu… |
| hc-jkl-2025-wp-c-1709-2024-jkhc020038112024-1-2025-11-03 | HC Jammu and Kashmir | 2025-11-03 | 7 | 10 | CURATED_CROSSWALK_C10_HELD | tionate or perverse. 10. The principle of proportionality was elaborated in <Ranjit Thakur v. Union of India & ors.=, 1987 (4) SCC 611, where it was held that judicial intervention is permissible only when the punishment is so disproportionate as to… |
| hc-delhi-2025-w-p-c-8474-2019-dlhc010321992019-1-2025-10-15 | HC Delhi | 2025-10-15 | 10 | 28 | CURATED_CROSSWALK_C10_HELD | gus document. 28. Reliance can be placed upon the judgment of the Supreme Court in Ranjit Thakur vs. Union of India, (1987) 4 SCC 611, where it was observed in the following words:- Signed By:ASHOK KUMAR CHOUHAN Signing Date:15.10.2025 16:37:54 Signa |
| hc-delhi-2025-w-p-c-8701-2017-dlhc014418842017-1-2025-10-10 | HC Delhi | 2025-10-10 | 27 | 25 | CURATED_CROSSWALK_C10_HELD | Page 27 of 45 proportionality laid down by the Apex Court in Ranjit Thakur v. Union of India, (1987) 4 SCC 611. 26. Per Contra, learned SPC appearing for the Respondent/BSF, has submitted as under: (i) The writ petition is liab |
| hc-ph-2025-cwp-26765-2018-phhc010984632018-1-2025-08-26 | HC Punjab and Haryana | 2025-08-26 | 5 | 4 | CURATED_CROSSWALK_C10_HELD | magnifies the misconduct. Guidance may be derived from the supreme court judgement of “Ranjit Thakur v. Union of India (1987) 4 SCC 611” wherein it was held as follows: 9. Re: contention (d): Judicial review generally speaking, is not directed again… |
| hc-delhi-2025-w-p-c-10624-2020-dlhc010346462020-1-2025-08-13 | HC Delhi | 2025-08-13 | 24 | 45 | CURATED_CROSSWALK_C10_HELD | 8.] also states that “proportionality” involves “balancing test” and “necessity test”. The “balancing test” permits 18 (1987) 4 SCC 611 19 (2018) 6 SCC 410, Signed By:GUNN Signing Date:13.08.2025 11:08:25 Signature Not Verified [[page 25]] W.P.(C) 1… |
| hc-ph-2025-cwp-18691-2021-phhc010850362021-1-2025-05-12 | HC Punjab and Haryana | 2025-05-12 | 12 | 8 | CURATED_CROSSWALK_C10_HELD | be commensurate with the sweep of the power. It said in the matter of Ranjit Thakur Versus Union of India reported as (1987) 4 SCC 611 that wider the powers, RAJENDER KUMAR 2025.05.25 22:50 I attest to the accuracy and authenticity of this order [[p… |
| hc-delhi-2024-w-p-c-6244-2020-dlhc010244382020-1-2024-11-21 | HC Delhi | 2024-11-21 | 16 | 15 | CURATED_CROSSWALK_C10_HELD | utrageous” defiance of logic. Neither Wednesbury nor CCSU tests are satisfied. We have still to explain “Ranjit Thakur [(1987) 4 SCC 611 : 1987 SCC (L&S) 1 : (1987) 5 ATC 113] ”. 33. In Ranjit Thakur [(1987) 4 SCC 611 : 1987 SCC (L&S) 1 : (1987) 5 A… |
| hc-jkl-2024-swp-9900009-2005-jkhc020030972005-1-2024-11-20 | HC Jammu and Kashmir | 2024-11-20 | 19 | 28 | CURATED_CROSSWALK_C10_HELD | shment to the charges, even if deemed to be proved. The Apex Court in “Ranjit Thakur Vs. Union of India” reported as (1987) 4 SCC 611 considered the question of „doctrine of proportionality‟ in the matter of awarding punishment under the Army Act. T |
| hc-delhi-2024-w-p-c-1522-2018-dlhc010440882018-1-2024-08-27 | HC Delhi | 2024-08-27 | 21 | 11 | CURATED_CROSSWALK_C10_HELD | rendered by this Court. We remain content with reference to only some of them. 11. In Ranjit Thakur v. Union of India [(1987) 4 SCC 611 : 1988 SCC (L&S) 1 : (1987) 5 ATC 113] this Court held that the doctrine of proportionality, as part of the conce… |
| hc-delhi-2023-w-p-c-9207-2023-dlhc010261732023-1-2023-08-16 | HC Delhi | 2023-08-16 | 17 | 24 | CURATED_CROSSWALK_C10_HELD | ook into because it amounts to an error of law apparent on the record.......‖ 24. In Ranjit Thakur v. Union of India, (1987) 4 SCC 611, the Apex Court has held as under: "25. Judicial review generally speaking, is not directed against a decision, bu… |

### Treatment candidates (cue wording near a citation or a later name reference)

- **Cue hits:** 2.
  - By attribution: REPORTER_EDITORIAL 2.
  - Only COURT_LIKELY hits can carry a proposed relation.

| Candidate | Citing judgment | Date | cue p./para | Cue | Attribution | Proposed | Status | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TC-ff2c2387607f | sc-2013-manoj-h-mishra-2013insc227 | 2013-04-09 | 6/- | distinguished | REPORTER_EDITORIAL | - | AUTOMATED_DETECTED | R.K. Jain vs. Union of India (1993) 4 SCC 119: 1993 (3) SCR 802 - referred to. Case Law Reference: 1980 (2) SCR 146 distinguished Para 18 1988 (1) SCR 512 referred to Para 20, 36 (201 O) 8 sec 281 referred to Para 21, 28 |
| TC-a32e3c3ed19c | sc-2013-manoj-h-mishra-2013insc227 | 2013-04-09 | 6/- | distinguished | REPORTER_EDITORIAL | - | AUTOMATED_DETECTED | R 802 - referred to. Case Law Reference: 1980 (2) SCR 146 distinguished Para 18 1988 (1) SCR 512 referred to Para 20, 36 (201 O) 8 sec 281 referred to Para |

### Name-only mentions (not resolved; may be false positives)

- **Pattern:** `ranjit thakur`. Searched in judgments with no resolved or string-matched edge to this case.
- **Window:** decided on or after 1987-10-15.
- **Hits:** 10 judgments.
  - hc-allahabad-2023-wria-8782-2022-uphc020784192022-1-2023-11-30 (2023-11-30) p.3: "ing disproportionate in terms of Hon’ble Supreme Court Order in “Bhagat Ram and Ranjit Thakur case”. B. To set aside the Order/Authority of Release no. LRDO I:01/2022 PART"
  - hc-ph-2012-crwp-245-2010-phhc010607232010-1-2012-11-19 (2012-11-19) p.18: "be appreciated in this background. Reference here can be made to the case of Ranjit Thakur Versus Union of India, AIR 1987 Supreme Court 2386, where the Hon'ble Supreme"
  - hc-delhi-2011-w-p-c-3952-2010-dlhc010899452010-1-2011-01-20 (2011-01-20) p.8: "which purpose the decision of the Supreme Court reported as AIR 1987 SC 2386 Ranjit Thakur vs. UOI & Ors. was cited. (iii) That the evidence clearly establish the petiti"
  - hc-delhi-2008-w-p-c-9509-2004-dlhc010299742004-1-2008-10-22 (2008-10-22) p.21: "28. In this regard reference can be made to the judgment of the Apex Court in Ranjit Thakur Vs. Union of India & Ors, [[page 22]] WP(C)9509/2004"
  - sc-2007-sheel-kr-roy-2007insc645 (2007-05-18) p.11: "h v.Union of India and Ors. (1991] 3 SCC 213. f 18. We may also notice that in Ranjit Thakur v. Union of India and Ors., -<-- reported in (1987] 4 SCC 611, this Court held"
  - sc-2003-union-of-india-and-ors-2003insc274 (2003-05-02) p.8: "r purposes of section 41 of the Act. Relying upon the judgment of this Court in Ranjit Thakur v. Union of India, [ 1987) 4 SCC 611 it was held that the said order of Wing Co"
  - sc-2003-union-of-india-and-ors-2003insc254 (2003-04-24) p.11: "t the High B Court had wrongly relied on the observations made by this Court in Ranjit Thakur's case (supra). According to him the principles laid down therein were wholly i"
  - sc-2001-union-of-india-and-ors-2001insc492 (2001-10-09) p.4: "The Division Bench also relied upon the following observations in the case of Ranjit Thakur v. Union of India reported in [1987] 4 SCC 611 : "Judicial review generally sp"
  - sc-1997-union-of-india-and-another-1997insc622 (1997-08-27) p.8: "ishment imposed was 'shockingly' disproportionate to the gravity of charges. In Ranjit Thakur v. Union of India, [1987) 4 SCC D 611, though the principle of 'proportionality"
  - sc-1991-ex-naik-sardar-singh-1991insc128 (1991-05-03) p.8: "f the European Economic Community, . , ...... " This principle was followed in Ranjit Thakur v. Union of India and Others, [1987] 4 SCC 611 where this Court considered the"

### Contrary authority / conflicting treatment

- No held decision found expressly departing from Ranjit Thakur on proportionality or bias. Later cases are listed below as citations; most are CITES without explicit treatment wording.

### Open questions and uncertainty

- Ranjit is held as a JUDIS/SCR rendition only (two crawler records share one sha). The Review Order (1989) 2 SCC 438 (curated R02) is NOT HELD, so citations to it stay unresolved.

## S. N. Mukherjee v. Union of India

- **Curated record.** DCLR-SC-1990-N02. Curated date: 1990-08-28. Case number: -. Reporter: (1990) 4 SCC 594; 1990 Supp (1) SCR 44.
- **C10 held status:** HELD.
- **C10 official-copy status (copies outside this text layer were not re-read):** NO_SIGNED_OR_OFFICIAL_COURT_PDF; held: JUDIS_TYPED_TEXT_RENDITION+SCR_REPORT_RENDITION_AWS_ESCR_MIRROR. Working store: downloads/citation-codes/snmukherjee_judis7439.pdf.
- **Held copy in the ad77758d text layer.** Group JG-239c4e386f0e (DIFFERENT_RENDITION;MISSING_OFFICIAL_ORIGINAL). Renditions: JUDIS_TYPED_TEXT_RENDITION, SCR_REPORT_RENDITION_AWS_ESCR_MIRROR.
  - Records: sc-1990-s-n-mukherjee-1990insc257 (sha 239c4e386f0e, 32 pp.).
  - Neutral citation: 1990 INSC 257. Reported: [1990] SUPP. 1 S.C.R. 44. Date: 1990-08-28.
- **C10 prior reading vs C11:** C10: C.A. 417/1984 agrees; date not legible.

### Verified readings

| Reading | Kind | Document | p. | para | Quotation (verbatim) | Note |
| --- | --- | --- | --- | --- | --- | --- |
| RD-SNM-H1 | HOLDING | sc-1990-s-n-mukherjee-1990insc257 | 27 | - | "no requirement to record reasons by the confirming authority while" | Five-Judge (Constitution) Bench; continues: confirmation of court-martial findings/sentence and the post-confirmation order need no reasons, but remain open to challenge under Art. 32 / Art. 226. |
| RD-SNM-H2 | HOLDING | sc-1990-s-n-mukherjee-1990insc257 | 27 | - | "it is open to the person aggrieved by such" | Text layer is OCR-noisy on this page ('te challenge'). |

### Citing judgments (graph)

- **Distinct citing judgments:** 25.
  - By court: Allahabad High Court 6, High Court of Delhi 11, High Court of Jammu and Kashmir 1, Supreme Court of India 7.
  - By year: 1993: 1, 2008: 1, 2010: 1, 2015: 2, 2016: 1, 2018: 1, 2019: 2, 2021: 2, 2022: 2, 2023: 3, 2024: 3, 2025: 5, 2026: 1.

All Supreme Court citing edges are listed, plus the 12 most recent High Court edges (of 18). The paragraph number is heuristic.

| Citing judgment | Court | Date | p. | para | Method | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| sc-1993-bhuwneshwar-singh-1993insc280 | SC | 1993-09-01 | 15 | - | CURATED_CROSSWALK_C10_HELD | defect or any other substantive error of law apparent on the face of the record (See S.N. Mukherjee v. Union of India, (1990) 4 SCC 594, Constitution Bench). Having found that the E appellant was in illegal detention from 29th June i989 to 25th July… |
| sc-2010-union-of-india-anr-2010insc99 | SC | 2010-02-16 | 12 | 10 | CURATED_CROSSWALK_C10_HELD | SC 414], which decision is followed by the Constitution Bench B in the decision in S.N. Mukherjee Vs. Union of India [1990 (4) SCC 594]. There also, the question arose as to whether the court martial authorities in case of Army personnel, as also th… |
| sc-2015-union-of-india-ors-2015insc206 | SC | 2015-03-11 | 30 | 23 | CURATED_CROSSWALK_C10_HELD | ave made general observations highlighting the significance of this feature." 23. In S.N. Mukherjee vs.Union of India, (1990)4 SCC 594, this Court noticed the special provision in regard to the members of the Armed Forces in the Constitution of Indi… |
| sc-2021-union-of-india-and-ors-2021insc817 | SC | 2021-12-03 | 25 | 26 | CURATED_CROSSWALK_C10_HELD | ral justice that a statutory tribunal should always and in every case give reasons in support of its decision. […] 16 (1990) 4 SCC 594 (“S N Mukherjee”) 17 AIR 1969 SC 414 (“Som Datt Datta“) [[page 26]] A B C D E F G H 1131 As already stated, |
| sc-2023-union-of-india-ors-2023insc265 | SC | 2023-03-21 | 9 | 13 | CURATED_CROSSWALK_C10_HELD | ished judicial precedent since that 8 Jurisdiction, powers and authority in matters of appeal against court-martial 9 (1990) 4 SCC 594 10 (2015) 6 SCC 773 [[page 10]] A B C D E F G H 607 judgment sought to create a complete bar to the High Cou |
| sc-2023-madhyamam-broadcasting-limited-2023insc324 | SC | 2023-04-05 | 49 | 57 | CURATED_CROSSWALK_C10_HELD | ely been trumped without providing them with an effective and reasonable avenue 47 See SN Mukherjee v. Union of India, (1990) 4 SCC 594; Seimens Engineering and Manufacturing Company v. Union of India, (1976) 2 SCC 981; CCI v. SAIL (2010) 10 SCC 744… |
| sc-2024-no-2809759h-ex-recruit-babanna-2024insc95 | SC | 2024-02-09 | 8 | 22 | CURATED_CROSSWALK_C10_HELD | osed to supplement the same by means of extraneous material or affidavit before the courts. 2 [1990] 1 Suppl. SCR 44 : (1990) 4 SCC 594 3 [1978] 2 SCR 272 : (1978) 1 SCC 405 [[page 9]] 250 [2024] 2 S.C.R. Digital Supreme Court Reports 23. In the cas |
| hc-jkl-2026-lpa-107-2022-jkhc010029582022-1-2026-10-22 | HC Jammu and Kashmir | 2026-10-22 | 20 | 47 | CURATED_CROSSWALK_C10_HELD | itary courts also recognises the distinctive nature of confirmation proceedings. In S.N. Mukherjee v. Union of India, (1990) 4 SCC 594, a Constitution Bench [[page 21]] Page 21 of 25 LPASW |
| hc-delhi-2025-w-p-c-1865-2025-dlhc010071312025-1-2025-12-06 | HC Delhi | 2025-12-06 | 6 | 17 | CURATED_CROSSWALK_C10_HELD | eme Court in G.S. Bajwa and S.N. Mukherjee. In Bajwa, it was noted that the Supreme Court had 10 (2003) 9 SCC 630 11 (1990) 4 SCC 594 12 (2) Any person aggrieved by an order, decision, finding or sentence passed by a court martial may prefer an appe… |
| hc-delhi-2025-w-p-c-1864-2025-dlhc010071302025-1-2025-12-06 | HC Delhi | 2025-12-06 | 6 | 17 | CURATED_CROSSWALK_C10_HELD | eme Court in G.S. Bajwa and S.N. Mukherjee. In Bajwa, it was noted that the Supreme Court had 10 (2003) 9 SCC 630 11 (1990) 4 SCC 594 12 (2) Any person aggrieved by an order, decision, finding or sentence passed by a court martial may prefer an appe… |
| hc-delhi-2025-w-p-c-10624-2020-dlhc010346462020-1-2025-08-13 | HC Delhi | 2025-08-13 | 22 | 42 | CURATED_CROSSWALK_C10_HELD | the face of the record, or where the finding is manifestly perverse or arbitrary. The relevant portion of the said 17 (1990) 4 SCC 594 Signed By:GUNN Signing Date:13.08.2025 11:08:25 Signature Not Verified [[page 23]] W.P.(C) 10624/2020 Page 23 of 26 |
| hc-delhi-2025-w-p-c-3321-2025-dlhc010136242025-1-2025-07-11 | HC Delhi | 2025-07-11 | 22 | 47 | CURATED_CROSSWALK_C10_HELD | Union of India13, has categorically held that while courts-martial are not required to record detailed reasons for 13(1990) 4 SCC 594 Signed By:AAKANSHA SHARMA Signing Date:11.07.2025 18:19:17 Signature Not Verified [[page 23]] W.P.(C) 3321/2025 |
| hc-allahabad-2025-wria-4492-2023-uphc010549422023-1-2025-05-05 | Allahabad High Court | 2025-05-04 | 25 | 43 | CURATED_CROSSWALK_C10_HELD | nd statutory purpose of the Army Act, 1950, the Constitution Bench in S.N. Mukherjee [S.N. Mukherjee v. Union of India, (1990) 4 SCC 594 : 1990 SCC (Cri) [[page 26]] 26 669 : 1991 SCC (L&S) 242] concluded that there was no requirement of furnishing … |
| hc-delhi-2024-w-p-c-6244-2020-dlhc010244382020-1-2024-11-21 | HC Delhi | 2024-11-21 | 11 | 13 | CURATED_CROSSWALK_C10_HELD | in RCT. There is not an iota of reasoning in the entire order. The Supreme Court in S.N. Mukherjee v. Union of India, (1990) 4 SCC 594 emphasised on the importance of passing a reasoned order and I quote: “36. Reasons, when recorded by an administra… |
| hc-delhi-2024-w-p-c-8148-2010-dlhc011754222010-1-2024-10-29 | HC Delhi | 2024-10-29 | 37 | 14 | PARTY_YEAR_COURT | misuse of power. The requirement of duty to give reasons was further crystallized in S.N. Mukherjee V Union of India, AIR 1990 SC 1984 and reasons due to which a reasoned decision must be passed were discussed. It was observed that reasoned decision… |
| hc-allahabad-2023-wria-9268-2022-uphc011085052022-1-2023-07-10 | Allahabad High Court | 2023-07-10 | 14 | 29 | CURATED_CROSSWALK_C10_HELD | s fundamental to good administration. A Constitution Bench of the Supreme Court in S.N. Mukherjee vs. Union of India:1990 (4) SCC 594 has reiterated the necessity of 14 of 16 [[page 15]] recording reasons by administrative body/authority. Thus the or |
| hc-allahabad-2022-wria-19332-2021-uphc012115002021-1-2022-01-20 | Allahabad High Court | 2022-01-20 | 8 | 14 | CURATED_CROSSWALK_C10_HELD | fer: L. Chandra Kumar [L. Chandra Kumar v. Union of India, (1997) 3 SCC 261 : 1997 SCC (L&S) 577] and S.N. Mukherjee [(1990) 4 SCC 594 : 1990 SCC (Cri) 669] .) (ii) The jurisdiction of the High Court under Article 226 and this Court under Article 32… |
| hc-allahabad-2022-wria-17043-2021-uphc011879992021-1-2022-01-20 | Allahabad High Court | 2022-01-20 | 8 | 14 | CURATED_CROSSWALK_C10_HELD | fer: L. Chandra Kumar [L. Chandra Kumar v. Union of India, (1997) 3 SCC 261 : 1997 SCC (L&S) 577] and S.N. Mukherjee [(1990) 4 SCC 594 : 1990 SCC (Cri) 669] .) (ii) The jurisdiction of the High Court under Article 226 and this Court under Article 32… |
| hc-delhi-2021-w-p-c-8896-2021-dlhc010258032021-1-2021-09-16 | HC Delhi | 2021-09-16 | 5 | 9 | CURATED_CROSSWALK_C10_HELD | ation petition. 9. He also places reliance on the judgment of the Supreme Court in S.N. Mukherjee vs. Union of India, (1990) 4 SCC 594 to submit that interpreting pari materia provisions in the Army Act, 1950, the Supreme Court had clearly held that… |

### Treatment candidates (cue wording near a citation or a later name reference)

- **Cue hits:** 4.
  - By attribution: COURT_LIKELY 1, REPORTER_EDITORIAL 3.
  - Only COURT_LIKELY hits can carry a proposed relation.

| Candidate | Citing judgment | Date | cue p./para | Cue | Attribution | Proposed | Status | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TC-aa5742d4bf9e | sc-2021-union-of-india-and-ors-2021insc817 | 2021-12-03 | 26/27 | Following the decision | COURT_LIKELY | FOLLOWS | DOCUMENTARY_CHECK_REQUIRED | 165 of the Army Act are in any way defective in law.” 27. Following the decision in Som Datt Datta (supra), the Constitution Bench in S N Mukherjee (supra) considered the provisions of the Army Act and concl |
| TC-e5a3e50db0e4 | sc-2023-union-of-india-ors-2023insc265 | 2023-03-21 | 4/- | followed | REPORTER_EDITORIAL | - | AUTOMATED_DETECTED | 0) 4 SCC 594 : [1990] 11 Suppl. SCR 44; Rojer Mathew v. South Indian Bank Ltd. & Ors. (2020) 6 SCC 1 : [2019] 16 SCR 1 – followed. Lt. Col. Prithi Pal Singh Bedi Etc. v. Union of India & Others (1982) 3 SCC 140 : [1983]  |
| TC-10d5e0c3848f | sc-2021-union-of-india-and-ors-2021insc817 | 2021-12-03 | 5/- | followed | REPORTER_EDITORIAL | - | AUTOMATED_DETECTED | to it. [Para 29][1134-E-G] S N Mukherjee v. Union of India (1990) 4 SCC 594 : [1990] 1 Suppl. SCR 44 – followed. Shyam Sunder v. Ram Kumar (2001) 8 SCC 24:[2001] 1 Suppl. |
| TC-d19e303e0b81 | sc-2010-union-of-india-anr-2010insc99 | 2010-02-16 | 2/- | followed | REPORTER_EDITORIAL | - | AUTOMATED_DETECTED | 003. [Para 12] [843-B-F] S.N. Mukherjee Vs. Union of India 1990 (4) SCC 594, followed. H [[page 3]] 832 SUPREME COURT REPORTS [2010] 2 S.C.R. A |

### Name-only mentions (not resolved; may be false positives)

- **Pattern:** `n mukherjee`. Searched in judgments with no resolved or string-matched edge to this case.
- **Window:** decided on or after 1990-08-28.
- **Hits:** 9 judgments.
  - hc-delhi-2026-w-p-c-12024-2026-dlhc010387012026-1-2026-08-19 (2026-08-19) p.2: "al Solicitor General. It was enunciated in the Constitution Bench judgment in S.N. Mukherjee case that even in respect of courts-martial, the High Court could grant appropr"
  - hc-allahabad-2021-wria-15281-2021-uphc011718502021-1-2021-11-01 (2021-11-01) p.3: "h Court under Article 226 of the Constitution of India.(Refer: L. Chandra and S.N. Mukherjee). (ii) The jurisdiction of the High Court under Article 226 and this Court unde"
  - hc-allahabad-2018-wria-12456-2000-uphc011039232000-1-2018-03-30 (2018-03-30) p.10: "d stage which was taken away by the Forty- second Amendment.” In the case of S.N. Mukherjee Vs. Union of India, (1990) 4 Supreme Court cases 594 the Apex Court [[page 11"
  - hc-delhi-2012-w-p-c-13360-2009-dlhc011805932009-1-2012-07-09 (2012-07-09) p.50: "aforenoted debate. 64. Indeed, in the decision reported as AIR 1990 SC 1984 S.N.Mukherjee Vs. UOI, in para 41 the Supreme Court observed as under:- ―41. Before referri"
  - sc-2007-ram-sunder-ram-2007insc748 (2007-07-11) p.9: "Col. Prithi Pal Singh Bedi v. Union of India & Ors., AIR ( 1982) SC 1413 and S. N. Mukherjee v. Union of India. [ 1990] 4 SCC 594. In the said decisions, this Court has dea"
  - sc-2003-union-of-india-and-ors-2003insc254 (2003-04-24) p.7: "Court Martial vitiated the order. Relying upon the judgment of this Court in S.N. Mukherjee v. Union of India, AIR (1990) SC 1984 it was held that the Court Martial is no"
  - sc-2000-union-of-india-and-anr-2000insc231 (2000-04-24) p.20: "he importance of role played by a Judge-Advocate was noticed by this Court in S.N. Mukherjee v. Union of India, [1990] 4 SCC 594 wherein it was held: "From the provisions"
  - sc-1992-union-of-india-and-ors-1992insc270 (1992-10-09) p.6: "o be given for the findings and sentences rendered by the Court Martial. See S .N. Mukherjee v. Union of India, (1990] 4 SCC 594, 617; Ram Sarup v. Tfie Union of India H ["
  - sc-1991-union-of-india-and-others-1991insc20 (1991-01-29) p.2: "Captain Barish Up pal v. Union of India and Others, [1973] 2 SCR 1025; SIJ.!i S.N. Mukherjee v. Union of India, JT 1990 (3} 630 and_ljnion_ offndia v. Col. J.N. Sinha and A"

### Contrary authority / conflicting treatment

- Parashotam relies on S N Mukherjee (Constitution Bench) for HC Art. 226 relief against court-martial proceedings. That supports S N Mukherjee rather than contradicting it.

### Open questions and uncertainty

- The held copy is an OCR-noisy SCR rendition; the printed date is illegible in the text layer.

## Union of India v. Ram Avtar (order of 10-12-2014)

- **Curated record.** DCLR-SC-2014-A08. Curated date: 2014-12-10. Case number: Civil Appeal No. 418/2012 and connected appeals. Reporter: -.
- **C10 held status:** NOT_HELD.
- **C10 official-copy status (copies outside this text layer were not re-read):** NO_COPY_HELD.
- **Held copy in the ad77758d text layer:** NONE.
- **C10 prior reading vs C11:** C10: NOT HELD; APPLIED by Girish as in rem; CLARIFIED by S P Rathore para 8 (SCR pp.4-5).

### Verified readings

| Reading | Kind | Document | p. | para | Quotation (verbatim) | Note |
| --- | --- | --- | --- | --- | --- | --- |
| RD-GIRISH-T3 | TREATMENT | sc-2026-union-of-india-through-its-sec-2026insc149 | 11 | 22 | "decided the issue of applicability of instruction dated 31.01.2001 and the aforesaid decision is in rem." | Characterises Ram Avtar as a decision in rem. |
| RD-GIRISH-R1 | TREATMENT | sc-2026-union-of-india-through-its-sec-2026insc149 | 9 | 14 | "The legal position continued to be uncertain until it was settled by a three-Judge bench of this Court in Union of India & Others v. Ram Avtar (supra)." | Girish's account of Ram Avtar (not held in the corpus). |

### Citing judgments (graph)

- **Distinct citing judgments:** 381.
  - By court: High Court of Delhi 93, High Court of Jammu and Kashmir 64, High Court of Punjab and Haryana 228, Supreme Court of India 3.
  - By year: 2019: 2, 2024: 15, 2025: 232, 2026: 139.
- **Target unresolved.** The case is not held, so these edges stay UNRESOLVED. They were matched only by the citation strings listed above.

All Supreme Court citing edges are listed, plus the 12 most recent High Court edges (of 385). The paragraph number is heuristic.

| Citing judgment | Court | Date | p. | para | Method | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| sc-2019-ex-hav-ashok-kumar-2019insc809 | SC | 2019-07-24 | 6 | 9 | UNRESOLVED | ischarged under the existing Rules. EX-HAV ASHOK KUMAR v. UNION OF INDIA & ORS. [DR DHANANAJAYA Y CHANDRACHUD, J.] 4 Civil Appeal No 418 of 2012 decided on 10 December 2014 [[page 7]] A B C D E F G H 36 SUPREME COURT REPORTS [2019] 11 S.C.R. Hence, … |
| sc-2019-g-h-union-of-india-ors-2019insc1359 | SC | 2019-12-11 | 4 | 7 | UNRESOLVED | d counsel for the Respondent on the Order dated 10.12.2014 of this Court in “Union of India and Ors. Versus Ram Avtar” (Civil Appeal No.418 of 2012 etc.) and subsequent letter dated 18.4.2016 sent by the Ministry of Defence to the Chief of all the A… |
| sc-2026-union-of-india-through-its-sec-2026insc149 | SC | 2026-02-12 | 5 | 3 | UNRESOLVED | oad banding of pension to the respondent from the date of his superannuation. 1 Union of India & Others. v. Ram Avtar, 2014 SCC Online SC 1761 [[page 6]] 620 [2026] 2 S.C.R. Supreme Court Reports (ii) REFERENCE TO THE FULL BENCH OF THE TRIBUNAL 4. … |
| hc-jkl-2026-wp-c-3134-2026-jkhc020062872026-1-2026-09-30 | HC Jammu and Kashmir | 2026-09-30 | 2 | 4 | UNRESOLVED | placing reliance upon the judgment passed by the Supreme Court in the case of Union of India and others vs. Ram Avtar 2014 SCC OnLine SC 1761 came to the conclusion that the classification made by the petitioners between the pensioners, who had been… |
| hc-jkl-2026-wp-c-2345-2025-jkhc020049702025-1-2026-09-16 | HC Jammu and Kashmir | 2026-09-16 | 2 | 4 | UNRESOLVED | 50% in terms of judgment rendered by the Hon’ble Supreme Court in case titled “Union of India Vs. Ram Avtar” bearing Civil Appeal No. 418/2012 decided on 10.12.2014. 3. Briefly stated the facts leading to filing of this petition are that the respond… |
| hc-ph-2026-cwp-28426-2026-phhc011400442026-1-2026-09-03 | HC Punjab and Haryana | 2026-09-03 | 2 | - | UNRESOLVED | dia in Dharamvir Singh versus Union of India and others, (2013) 7 SCC 316 and Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, has been wrongly allowed by the Tribunal. 3. We have heard learned counsel for the petitioners and have g… |
| hc-ph-2026-cwp-26964-2026-phhc011390482026-1-2026-08-24 | HC Punjab and Haryana | 2026-08-24 | 5 | 9 | UNRESOLVED | .1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Armed Forces personnel is entitled to be granted the benefit of rounding … |
| hc-ph-2026-cwp-26799-2026-phhc011402752026-1-2026-08-24 | HC Punjab and Haryana | 2026-08-24 | 2 | 2 | UNRESOLVED | inst 20 % for life has been wrongly granted to respondent No. 1 in terms of Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, as he was discharged from service. 3. We have heard learned counsels for their respective parties and have … |
| hc-ph-2026-cwp-23406-2026-phhc011059992026-1-2026-08-20 | HC Punjab and Haryana | 2026-08-20 | 2 | 2 | UNRESOLVED | inst 20 % for life has been wrongly granted to respondent No. 1 in terms of Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, as he was discharged from service at his own request on compassionate ground. 3. We have heard learned coun… |
| hc-jkl-2026-wp-c-2016-2024-jkhc020044482024-1-2026-08-18 | HC Jammu and Kashmir | 2026-08-18 | 3 | 5 | UNRESOLVED | erms of the ratio of the judgment of the Hon’ble Supreme Court in case titled Union of India and Ors. vs. Ram Avtar, (2014 SCC Online SC 1761). 6. Learned counsel for the petitioners submits that the AFT has committed a grave error in law by directi… |
| hc-delhi-2026-w-p-c-13401-2025-dlhc010633632025-1-2026-08-11 | HC Delhi | 2026-08-11 | 5 | 8 | UNRESOLVED | arned Armed Force Tribunal are based on the judgment passed by the Hon’ble Apex Court in Union of India v. Ram Avtar (Civil Appeal No. 418/2012) decided on 10th December, 2014 and also that of Secretary, Government of India & Ors. v. Dharamvir Singh… |
| hc-ph-2026-cwp-24275-2026-phhc011279632026-1-2026-08-06 | HC Punjab and Haryana | 2026-08-06 | 2 | 6 | UNRESOLVED | per the settled principle of law settled by Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, any officer serving in the Armed Forces, who had undergone the medical examination at the time of his/her… |
| hc-ph-2026-cwp-22423-2026-phhc011192972026-1-2026-07-23 | HC Punjab and Haryana | 2026-07-23 | 4 | 6 | UNRESOLVED | 1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC OnLine SC 1761, wherein it has been held that any officer serving in the Armed Forces, who had undergone the medical examin… |
| hc-ph-2026-cwp-21960-2026-phhc011164962026-1-2026-07-20 | HC Punjab and Haryana | 2026-07-20 | 3 | 7 | UNRESOLVED | granted to all eligible from 01.01.1996 or 01.01.2006, as the case may be. 7. Furthermore, in the judgment passed in Civil Appeal No.418 of 2012 titled Union of India and ors Vs. Ram Avtar, decided on 10.12.2014 an order dated 18.04.2016 passed by G… |
| hc-ph-2026-cwp-21544-2026-phhc011154112026-1-2026-07-17 | HC Punjab and Haryana | 2026-07-17 | 1 | 2 | UNRESOLVED | bunal in Dharamvir Singh vs. Union of India and others, (2013) 7 SCC 316 and Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761 , is arbitrary and illegal. It is also allged by the petitioner that even the NITIN 2026.07.27 11:01 I atte… |

### Treatment candidates (cue wording near a citation or a later name reference)

- **Cue hits:** 256.
  - By attribution: COURT_LIKELY 41, CUE_TOO_FAR 1, LOWER_FORUM_REPORTED 177, NEXT_SENTENCE_NO_BACK_REFERENCE 1, PARTY_SUBMISSION_OR_MIXED 22, QUOTED_PASSAGE 13, REPORTER_EDITORIAL 1.
  - Only COURT_LIKELY hits can carry a proposed relation.

| Candidate | Citing judgment | Date | cue p./para | Cue | Attribution | Proposed | Status | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TC-8af1e9de16b9 | hc-ph-2025-cwp-16116-2025-phhc010882012025-1-2025-08-20 | 2025-08-20 | 3/7 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | tioners qua the rounding off disability pension, the issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that any off |
| TC-df5872181052 | hc-ph-2025-cwp-12650-2025-phhc010707562025-1-2025-08-28 | 2025-08-28 | 3/5 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | ua the ‘rounding off of disability pension’ the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that any off |
| TC-1e82e85867bf | hc-ph-2025-cwp-9960-2025-phhc010532852025-1-2025-08-28 | 2025-08-28 | 5/7 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | ua the ‘rounding off of disability pension’ the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that any off |
| TC-8d8d4183c20a | hc-ph-2025-cwp-9946-2025-phhc010542132025-1-2025-09-09 | 2025-09-09 | 4/5 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | ua the ‘rounding off of disability pension’ the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that any off |
| TC-a29b38ef95a6 | hc-ph-2025-cwp-27065-2025-phhc011462212025-1-2025-09-11 | 2025-09-11 | 4/6 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | ua the ‘rounding off of disability pension’ the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that any off |
| TC-12ab9ba18d4a | hc-ph-2025-cwp-27149-2025-phhc011462332025-1-2025-09-11 | 2025-09-11 | 4/6 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | ua the ‘rounding off of disability pension’ the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that any off |
| TC-88f622c95d15 | hc-ph-2026-cwp-20739-2025-phhc011104582025-1-2026-01-27 | 2026-01-27 | 4/6 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | f of disability granted to respondent No.1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Arme |
| TC-7c46cba191e9 | hc-ph-2026-cwp-33963-2024-phhc011766792024-1-2026-01-27 | 2026-01-27 | 5/6 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | f of disability granted to respondent No.1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Arme |
| TC-b33713be4109 | hc-ph-2026-cwp-23265-2024-phhc011206822024-1-2026-02-09 | 2026-02-09 | 5/7 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | f of disability granted to respondent No.1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Arme |
| TC-0f8307269faa | hc-ph-2026-cwp-23840-2024-phhc011229322024-1-2026-02-09 | 2026-02-09 | 5/7 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | f of disability granted to respondent No.1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Arme |
| TC-93aa9ab8c99e | hc-ph-2026-cwp-7395-2026-phhc010400902026-1-2026-03-12 | 2026-03-12 | 4/6 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | f of disability granted to respondent No.1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Arme |
| TC-f9d4bace9003 | hc-ph-2026-cwp-7405-2026-phhc010410742026-1-2026-03-12 | 2026-03-12 | 5/6 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | f of disability granted to respondent No.1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Arme |
| TC-d2ce42f108b4 | hc-ph-2026-cwp-7955-2026-phhc010370702026-1-2026-03-17 | 2026-03-17 | 2/5 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | ff of disability granted to respondent No.1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Arm |
| TC-3d3ac8bc5594 | hc-ph-2026-cwp-10771-2026-phhc010567092026-1-2026-04-09 | 2026-04-09 | 4/6 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | of this document [[page 4]] 4 CWP-10771-2026 (O&M) issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Armed  |
| TC-028cda713745 | hc-ph-2026-cwp-10805-2026-phhc010508822026-1-2026-04-09 | 2026-04-09 | 4/6 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | f of disability granted to respondent No.1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Arme |
| TC-e1b884122fad | hc-ph-2026-cwp-10858-2026-phhc010587962026-1-2026-04-09 | 2026-04-09 | 2/6 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | ff of disability granted to respondent No.1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Arm |
| TC-6e106424e647 | hc-ph-2026-cwp-11021-2026-phhc010551682026-1-2026-04-10 | 2026-04-10 | 3/5 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | f of disability granted to respondent No.1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Arme |
| TC-ee255dda38bd | hc-ph-2026-cwp-11134-2026-phhc010603112026-1-2026-04-10 | 2026-04-10 | 4/15 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | f of disability granted to respondent No.1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that any off |
| TC-7f0ae38bb54f | hc-ph-2026-cwp-11431-2026-phhc010538252026-1-2026-04-17 | 2026-04-17 | 5/6 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | egrity of this order/judgment [[page 5]] CWP-11431-2026 5 has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Armed |
| TC-e571e7237f06 | hc-ph-2026-cwp-11800-2026-phhc010628192026-1-2026-04-20 | 2026-04-20 | 4/11 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | ners qua the ‘rounding off of disability pension’ the same has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that any off |
| TC-f21ec4b19750 | hc-ph-2026-cwp-12552-2026-phhc010496692026-1-2026-04-24 | 2026-04-24 | 3/7 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | ng off of disability granted to respondent, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Arme |
| TC-6105ff228f1b | hc-ph-2026-cwp-11900-2026-phhc010650542026-1-2026-04-28 | 2026-04-28 | 4/6 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | f of disability granted to respondent No.1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Arme |
| TC-6f6012c4e740 | hc-ph-2026-cwp-13189-2026-phhc010661742026-1-2026-04-30 | 2026-04-30 | 4/6 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | ua the ‘rounding off of disability pension’ the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that any off |
| TC-aead0354a4d1 | hc-ph-2026-cwp-13865-2026-phhc010747842026-1-2026-05-05 | 2026-05-05 | 4/7 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | ff of disability granted to respondent No.1, the same issue has been settled by the Hon’ble Supreme Court of India in Civil Appeal No.418/2012 titled as Union of India Vs. Ram Avtar (supra), wherein it |
| TC-46efaccb6d1f | hc-ph-2026-cwp-15321-2026-phhc010822372026-1-2026-05-18 | 2026-05-18 | 5/10 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | f of disability granted to respondent No.1, the said issue has been settled by the Hon’ble Supreme Court of India in Civil Appeal No.418/2012 titled as Union of India Vs. Ram Avtar, wherein it has bee |
| TC-966e32f20c7a | hc-ph-2026-cwp-16200-2026-phhc010873692026-1-2026-05-22 | 2026-05-22 | 4/8 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | f of disability granted to respondent No.1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Arme |
| TC-5ea15a87e503 | hc-ph-2026-untitled-phhc010886062026-1-2026-05-26 | 2026-05-26 | 4/7 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | ability pension granted to respondent No.1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Arme |
| TC-c2a61e1c935d | hc-ph-2026-untitled-phhc010900402026-1-2026-05-26 | 2026-05-26 | 4/8 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | injury pension granted to respondent No.1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Armed |
| TC-0373833904d3 | hc-ph-2026-untitled-phhc010900442026-1-2026-05-26 | 2026-05-26 | 3/8 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | f of disability granted to respondent No.1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Arme |
| TC-bdae28dab2ca | hc-ph-2026-cwp-17744-2026-phhc010890622026-1-2026-05-29 | 2026-05-29 | 4/6 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | f of disability granted to respondent No.1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Arme |
| TC-41491e74504d | hc-ph-2026-cwp-17837-2026-phhc010711322026-1-2026-05-29 | 2026-05-29 | 4/6 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | f of disability granted to respondent No.1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Arme |
| TC-b696f3c5e141 | hc-ph-2026-cwp-18206-2026-phhc010948852026-1-2026-05-29 | 2026-05-29 | 4/7 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | ability pension granted to respondent No.1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Arme |
| TC-d26804df123d | hc-ph-2026-cwp-18388-2026-phhc010935072026-1-2026-05-29 | 2026-05-29 | 4/8 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | injury pension granted to respondent No.1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Armed |
| TC-789eadc1660e | hc-ph-2026-cwp-18392-2026-phhc010951642026-1-2026-05-29 | 2026-05-29 | 4/6 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | f of disability granted to respondent No.1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Arme |
| TC-f70161952449 | hc-ph-2026-cwp-18775-2026-phhc010830372026-1-2026-07-01 | 2026-07-01 | 5/6 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | f of disability granted to respondent No.1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Arme |
| TC-3eba42fb6e5c | hc-ph-2026-cwp-19852-2026-phhc010964782026-1-2026-07-06 | 2026-07-06 | 4/7 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | ability pension granted to respondent No.1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein, it has been held that an Arm |
| TC-f9db5658a7d6 | hc-ph-2026-cwp-19854-2026-phhc011055252026-1-2026-07-06 | 2026-07-06 | 2/5 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | disability pension to respondent No.1. 5. The said issue has been settled by the Hon’ble Supreme Court of India in Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Armed Forces personnel i |
| TC-95b74e571516 | hc-ph-2026-cwp-19974-2026-phhc011060552026-1-2026-07-06 | 2026-07-06 | 4/8 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | f of disability granted to respondent No.1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Arme |
| TC-4a1d0cc1e9bd | hc-ph-2026-cwp-22423-2026-phhc011192972026-1-2026-07-23 | 2026-07-23 | 4/6 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | efit has been granted to respondent No. 1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC OnLine SC 1761, wherein it has been held that any offi |
| TC-9ad76aeca343 | hc-ph-2026-cwp-26964-2026-phhc011390482026-1-2026-08-24 | 2026-08-24 | 5/9 | has been settled | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | injury pension granted to respondent No.1, the same issue has been settled by the Hon’ble Supreme Court of India in Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, wherein it has been held that an Armed |

### Name-only mentions (not resolved; may be false positives)

- **Pattern:** `\bRam\s+Avtar\b`. Searched in judgments with no resolved or string-matched edge to this case.
- **Window:** decided on or after -.
- **Hits:** 104 judgments.
  - hc-ph-2026-cwp-28362-2026-phhc011463852026-1-2026-09-03 (2026-09-03) p.3: "the settled principle of law settled by the Hon’ble Supreme Court of India in Ram Avtar’s case (supra), disability element of disability pension is assessed @ 20%, th"
  - hc-jkl-2026-wp-c-757-2025-jkhc020016342025-1-2026-08-18 (2026-08-18) p.5: "eferred to above 09. Similarly in Hon’ble Supreme Court in Union of India and Ram Avtar &amp; ors. reported as 2014 SCC online SC 1761, the Hon’ble Apex Court has hel"
  - hc-ph-2026-cwp-24493-2026-phhc011270842026-1-2026-08-12 (2026-08-12) p.3: "tive or uneven. The judgment rendered by a three-Judge Bench of this Court in Ram Avtar’s case (supra) was a judgment in rem and, therefore, the benefit of same ought"
  - hc-ph-2026-cwp-24333-2026-phhc011276512026-1-2026-08-06 (2026-08-06) p.6: "roposition of law having been settled by the Hon’ble Supreme Court of India in Ram Avtar’s case (supra) to the effect that percentage of disability is to be rounded of"
  - hc-ph-2026-cwp-1730-2026-phhc010092662026-1-2026-07-20 (2026-07-20) p.3: "ective or uneven. The judgment rendered by a three-Judge Bench of this Court in Ram Avtar’s case (supra) was a judgment in rem and, therefore, the benefit of same ought"
  - hc-ph-2026-cwp-20360-2026-phhc010948432026-1-2026-07-08 (2026-07-08) p.2: "cided on 31.03.2011 and Civil Appeal No.418-2012 Union of India and others vs. Ram Avtar, decided on 10.12.2014 is incorrect and the facts of the present case have no"
  - hc-jkl-2026-wp-c-1554-2026-jkhc020029342026-1-2026-06-03 (2026-06-03) p.3: "ervice stands settled by the Hon’ble Apex Court in “Union of India & Ors. Vs. Ram Avtar”, wherein it was held that armed forces personnel retiring on completion of te"
  - hc-jkl-2026-wp-c-919-2026-jkhc020017952026-1-2026-05-30 (2026-05-30) p.4: "pension, the Tribunal relied on the judgment in case titled Union of India and Ram Avtar & Ors. (2014 [[page 5]] WP(C) No. 919 of 2026 Page 5 of 8 SCC Online SC 1761."
  - hc-ph-2026-untitled-phhc010900432026-1-2026-05-26 (2026-05-26) p.2: "ce upon the judgment in Civil Appeal No.418-2012 Union of India and others vs. Ram Avtar, decided on 10.12.2014, is incorrect and the facts of the present case have n"
  - hc-ph-2026-cwp-16469-2026-phhc010827862026-1-2026-05-25 (2026-05-25) p.2: "gment. [[page 2]] CWP-16469-2026 -2- No.418/2012 titled as Union of India Vs. Ram Avtar is incorrect. 3. We have heard learned counsel for the petitioners and have go"

### Contrary authority / conflicting treatment

- None identified in the held corpus. Absence of a hit is not proof of absence.

### Open questions and uncertainty

- NOT HELD in any input store; every citation to it stays UNRESOLVED. Its content is known here only through citing judgments: Girish paras 13, 14 and 22; S P Rathore per C10. 'Ram Avtar' is also a common party name, so name-only hits are unreliable.
- HC citations use at least '2014 SCC OnLine SC 1761' and 'Civil Appeal No. 418/2012'. One Delhi HC order prints 'Civil Appeal No. 418/2010'.

## Dharamvir Singh v. Union of India

- **Curated record.** DCLR-SC-2013-N08. Curated date: 2013-07-02. Case number: Civil Appeal No. 4949 of 2013. Reporter: (2013) 7 SCC 316.
- **C10 held status:** HELD.
- **C10 official-copy status (copies outside this text layer were not re-read):** YES_COURT_HOSTED_JUDIS_PATH_LAYOUT. Working store: downloads/independent-reviewer-B/dharamvir_40493.pdf;downloads/independent-reviewer/40493.pdf;downloads/judgment-auditor/dharamvir_judis_40493.pdf.
- **Held copy in the ad77758d text layer.** Group JG-3056712cc761 (DIFFERENT_RENDITION). Renditions: JUDIS_PATH_COURT_LAYOUT_PDF, SCR_REPORT_RENDITION_AWS_ESCR_MIRROR.
  - Records: sc-2013-dharamvir-singh-2013insc408 (sha a9ccc45cd8c4, 30 pp.).
  - Neutral citation: 2013 INSC 408. Reported: [2013] 8 S.C.R. 1119. Date: 2013-07-02.
- **C10 prior reading vs C11:** C10: APPLIED by Rajbir para 15; CLARIFIED by Isaac (2026 INSC 993).

### Verified readings

| Reading | Kind | Document | p. | para | Quotation (verbatim) | Note |
| --- | --- | --- | --- | --- | --- | --- |
| RD-DHARAMVIR-H1 | HOLDING | sc-2013-dharamvir-singh-2013insc408 | 27 | 28(ii) | "A member is to be presumed in sound physical and mental condition upon entering service if there is no note or record at the time of entrance." | Read with para 28(i): determined under the Entitlement Rules for Casualty Pensionary Awards, 1982 (Appendix II, Reg. 173). |

### Citing judgments (graph)

- **Distinct citing judgments:** 352.
  - By court: Allahabad High Court 5, High Court of Delhi 126, High Court of Jammu and Kashmir 63, High Court of Punjab and Haryana 151, Supreme Court of India 7.
  - By year: 2013: 1, 2014: 5, 2015: 3, 2016: 1, 2018: 1, 2019: 2, 2020: 1, 2021: 4, 2022: 1, 2023: 3, 2024: 35, 2025: 216, 2026: 79.

All Supreme Court citing edges are listed, plus the 12 most recent High Court edges (of 345). The paragraph number is heuristic.

| Citing judgment | Court | Date | p. | para | Method | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| sc-2015-union-of-india-anr-2015insc114 | SC | 2015-02-13 | 6 | 4 | CURATED_CROSSWALK_C10_HELD | were of no assistance in view of the later pronouncement of this Court in Dharamvir Singh v. Union c of India and Ors. (2013) 7 SCC 316 where a two-Judge Bench of this Court had, after a comprehensive review of the case law and the relevant rules an… |
| sc-2015-union-of-india-ors-2015insc150 | SC | 2015-02-24 | 9 | 7 | CURATED_CROSSWALK_C10_HELD | contention, learned counsel has placed reliance on this Court's judgment in Dharamvir Singh Vs. D Union of India & Ors. (2013) 7 SCC 316. He further contended that although the Release Medical Board is an expert body, the adjudicating authority has … |
| sc-2015-union-of-india-ors-2015insc402 | SC | 2015-05-12 | 26 | 25 | CURATED_CROSSWALK_C10_HELD | ned statutory provisio·ns had observed with reference as well to the enunciations in Dharamvir Singh vs. Union of India 2013(7) SCC 316, that the provision for payment of disability pension is a beneficial one and ought to be interpreted liberally s… |
| sc-2019-smt-sulekha-rani-2019insc769 | SC | 2019-07-16 | 3 | 4 | CURATED_CROSSWALK_C10_HELD | al condition upon entering service if there is no note or record at the time of entrance. In the event of his 1 AFT 2 (2013) 7 SCC 316 SMT. SULEKHA RANI v. UNION OF INDIA AND ORS. [[page 4]] A B C D E F G H 854 SUPREME COURT REPORTS [2019] 9 S. |
| sc-2019-no-1466828m-ex-cfn-narsingh-ya-2019insc1121 | SC | 2019-10-03 | 6 | 7 | CURATED_CROSSWALK_C10_HELD | bility pension. NO. 1466828M EX CFN NARSINGH YADAV v. UNION OF INDIA & ORS. [HEMANT GUPTA, J.] 2 (2017) 4 SCC 697 3 (2013) 7 SCC 316 4 (2015) 12 SCC 264 [[page 7]] A B C D E F G H 266 SUPREME COURT REPORTS [2019] 13 S.C.R. 8. In Dharamvir Si |
| sc-2025-bijender-singh-2025insc549 | SC | 2025-04-23 | 6 | 19 | CURATED_CROSSWALK_C10_HELD;REPORTER_CITATION_METADATA | ame is contrary to the law laid down by this Court in Dharamvir Singh Vs. Union of India,1 Union of India Vs. Rajbir 1 (2013) 7 SCC 316 [[page 7]] 1556 [2025] 4 S.C.R. Supreme Court Reports Singh2 and Union of India Vs. Angad Singh Titaria.3 By ign… |
| sc-2026-union-of-india-ors-2026insc689 | SC | 2026-07-13 | 13 | 15 | CURATED_CROSSWALK_C10_HELD;REPORTER_CITATION_METADATA | ely lost vision in one eye and was suffering from partial loss of vision in the other. At the relevant time, he was 11 (2013) 7 SCC 316 12 (1993) 2 SCC 411 13 (1999) 1 SCC 467 [[page 14]] [2026] 8 S.C.R.  231 Union of India & Ors. v. Bali Ram No. 8… |
| hc-ph-2026-cwp-28426-2026-phhc011400442026-1-2026-09-03 | HC Punjab and Haryana | 2026-09-03 | 2 | - | CURATED_CROSSWALK_C10_HELD | reliance upon the judgment of the Hon’ble Supreme Court of India in Dharamvir Singh versus Union of India and others, (2013) 7 SCC 316 and Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761, has been wrongly allowed by the Tribunal. 3.… |
| hc-ph-2026-cwp-26799-2026-phhc011402752026-1-2026-08-24 | HC Punjab and Haryana | 2026-08-24 | 2 | 2 | CURATED_CROSSWALK_C10_HELD | ng reliance upon the judgment of the Hon’ble Supreme Court of India in Dharamvir Singh vs. Union of India and others, (2013) 7 SCC 316 , is arbitrary and illegal. Learned counsel for the petitioners further submits that even the benefit of rounding … |
| hc-ph-2026-cwp-23406-2026-phhc011059992026-1-2026-08-20 | HC Punjab and Haryana | 2026-08-20 | 2 | 2 | CURATED_CROSSWALK_C10_HELD | g reliance upon the judgment of the Hon’ble Supreme Court of India in Dharamvir Singh vs. Union of India and others, (2013) 7 SCC 316 , is arbitrary and illegal. Learned counsel for the petitioners further submits that even the benefit of rounding o |
| hc-delhi-2026-w-p-c-7592-2026-dlhc010244722026-1-2026-08-11 | HC Delhi | 2026-08-11 | 2 | 4 | CURATED_CROSSWALK_C10_HELD | of rounding off it to 75% based on the judgment of the Apex Court in ‘Dharamvir Singh v. Union of India’, reported in (2013) 7 SCC 316. 5. In the present petition, learned counsel for the petitioner has made two-fold submissions: a. That the Tribunal |
| hc-delhi-2026-w-p-c-7456-2026-dlhc010240362026-1-2026-08-11 | HC Delhi | 2026-08-11 | 2 | 3 | CURATED_CROSSWALK_C10_HELD | element to 50% based on the judgment of the Apex Court in ‘Dharamvir Singh v. Union of India and Others’, reported in (2013) 7 SCC 316. 4. The counsel for the petitioner has made two-fold submissions: a. That the Tribunal ought not to have rounded o… |
| hc-delhi-2026-w-p-c-7452-2026-dlhc010240352026-1-2026-08-11 | HC Delhi | 2026-08-11 | 2 | 3 | CURATED_CROSSWALK_C10_HELD | element to 50% based on the judgment of the Apex Court in ‘Dharamvir Singh v. Union of India and Others’, reported in (2013) 7 SCC 316. 4. The counsel for the petitioner has made two-fold submissions: a. That the Tribunal ought not to have rounded o… |
| hc-delhi-2026-w-p-c-7353-2026-dlhc010238342026-1-2026-08-11 | HC Delhi | 2026-08-11 | 2 | 3 | CURATED_CROSSWALK_C10_HELD | element to 50% based on the judgment of the Apex Court in ‘Dharamvir Singh v. Union of India and Others’, reported in (2013) 7 SCC 316. 4. The counsel for the petitioner has made two-fold submissions: a. That the Tribunal ought not to have rounded o… |
| hc-ph-2026-cwp-31834-2025-phhc011736322025-1-2026-08-06 | HC Punjab and Haryana | 2026-08-06 | 3 | 3 | CURATED_CROSSWALK_C10_HELD | led principles of law, settled by the Hon’ble Supreme Court of India in Dharamvir Singh vs. Union of India and Others, 2013(7) SCC 316. Learned counsel further submits that even the same disability, has been treated to be attributable to the Militar… |
| hc-ph-2026-cwp-24333-2026-phhc011276512026-1-2026-08-06 | HC Punjab and Haryana | 2026-08-06 | 2 | 5 | CURATED_CROSSWALK_C10_HELD | d issue has already been settled by Hon’ble Supreme Court of India in Dharamvir Singh vs. Union of India and others, (2013) 7 SCC 316. 6. It should be noted that as per judgment in Dharamvir Singh’s case (supra) it has been held that in a case where |
| hc-ph-2026-cwp-21544-2026-phhc011154112026-1-2026-07-17 | HC Punjab and Haryana | 2026-07-17 | 1 | 2 | CURATED_CROSSWALK_C10_HELD | ion to respondent by placing reliance upon the judgement of Tribunal in Dharamvir Singh vs. Union of India and others, (2013) 7 SCC 316 and Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761 , is arbitrary and illegal. It is also allge… |
| hc-ph-2026-cwp-21368-2026-phhc010992152026-1-2026-07-16 | HC Punjab and Haryana | 2026-07-16 | 2 | 2 | CURATED_CROSSWALK_C10_HELD | grity of this document [[page 2]] CWP-21368-2026 2 Online SC 1761 and Dharamvir Singh vs. Union of India and others, (2013) 7 SCC 316 is incorrect. 3. We have heard learned counsel for the petitioners and have gone through the case file with her able |
| hc-ph-2026-cwp-20323-2026-phhc011062722026-1-2026-07-08 | HC Punjab and Haryana | 2026-07-08 | 2 | 2 | CURATED_CROSSWALK_C10_HELD | n Union of India and others vs. Ram Avtar, 2014 SCC Online SC 1761 and Dharamvir Singh vs. Union of India and others, (2013) 7 SCC 316 is incorrect. 3. We have heard learned counsel for the petitioners and have gone through the case file with his ab… |

### Treatment candidates (cue wording near a citation or a later name reference)

- **Cue hits:** 409.
  - By attribution: COURT_LIKELY 43, CUE_TOO_FAR 5, DIRECTION_UNCLEAR 2, LOWER_FORUM_REPORTED 219, NEXT_SENTENCE_NO_BACK_REFERENCE 1, PARTY_SUBMISSION_OR_MIXED 114, QUOTED_PASSAGE 17, REPORTED_TREATMENT_OF_TARGET 8.
  - Only COURT_LIKELY hits can carry a proposed relation.

| Candidate | Citing judgment | Date | cue p./para | Cue | Attribution | Proposed | Status | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TC-4aa68f96595f | hc-delhi-2014-w-p-c-6538-2013-dlhc011563952013-1-2014-11-24 | 2014-11-24 | 3/5 | is squarely covered by | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | ies. 5. We are of the view that the case of the petitioner is squarely covered by the judgment of the Supreme Court in the case of Dharamvir Singh v. Union of India, (2013) 7 SCC 316 which held:- “28. A conjoint reading  |
| TC-1647eaafb986 | hc-delhi-2014-w-p-c-6538-2013-dlhc011563952013-1-2014-11-24 | 2014-11-24 | 3/5 | squarely covered | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | . 5. We are of the view that the case of the petitioner is squarely covered by the judgment of the Supreme Court in the case of Dharamvir Singh v. Union of India, (2013) 7 SCC 316 which held:- “28. A conjoint reading of  |
| TC-7ec8e8956381 | hc-delhi-2018-w-p-c-7804-2016-dlhc012226132016-1-2018-10-10 | 2018-10-10 | 5/12 | following the ratio | COURT_LIKELY | FOLLOWS | DOCUMENTARY_CHECK_REQUIRED | ibutability or aggravation of the petitioner‟s disability, following the ratio of the decision in the case of Dharamvir Singh (supra), we have no hesitation in holding that the petitio |
| TC-5e3d4733ac68 | hc-delhi-2025-w-p-c-3545-2025-dlhc010148412025-1-2025-03-27 | 2025-03-27 | 48/34 | Applying the principles | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | 002 and, therefore, the impugned order cannot be sustained. Applying the principles of Dharamvir Singh case and Rajbir Singh case, it has to be presumed that the |
| TC-7b15209948a4 | hc-delhi-2025-w-p-c-3667-2025-dlhc011121642024-1-2025-03-27 | 2025-03-27 | 48/34 | Applying the principles | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | 002 and, therefore, the impugned order cannot be sustained. Applying the principles of Dharamvir Singh case and Rajbir Singh case, it has to be presumed that the |
| TC-31ab0dc015b5 | hc-delhi-2025-w-p-c-3229-2025-dlhc011104332024-1-2025-04-02 | 2025-04-02 | 5/17 | In view of the law laid down | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | tting in appeal over the decision of the learned Tribunal. In view of the law laid down by the Supreme Court in Dharamvir Singh (supra) and this Court in Ex Sub Gawas Anil Madso (supra), |
| TC-ce29896ee6cb | hc-delhi-2025-w-p-c-5482-2025-dlhc010247492025-1-2025-04-29 | 2025-04-29 | 1/2 | is covered by | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | II2 has been allowed by the AFT relying on the judgment of the Supreme Court in Dharamvir Singh v UOI3. 2. The issue is covered by a recent decision rendered by us in UOI v Ex Sub Gawas Anil Madso4. 1 “the AFT”, hereinaf |
| TC-2b31be7e3294 | hc-delhi-2025-w-p-c-5673-2025-dlhc010253962025-1-2025-05-02 | 2025-05-02 | 1/2 | is covered by | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | ity has been allowed by the AFT relying on the judgment of the Supreme Court in Dharamvir Singh v UOI4. 2. The issue is covered by a recent decision rendered by us in UOI v Ex Sub Gawas Anil Madso5. 1 “the AFT”, hereinaf |
| TC-9b0f50653198 | hc-delhi-2025-w-p-c-9470-2025-dlhc011199172024-1-2025-07-10 | 2025-07-10 | 1/2 | is covered by | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | II2 has been allowed by the AFT relying on the judgment of the Supreme Court in Dharamvir Singh v UOI3. 2. The issue is covered by a recent decision rendered by us in UOI v Ex Sub Gawas Anil Madso4. 1 “the AFT”, hereinaf |
| TC-24ff52b0997c | hc-delhi-2025-w-p-c-10012-2025-dlhc010445832025-1-2025-07-16 | 2025-07-16 | 1/2 | is covered by | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | II2 has been allowed by the AFT relying on the judgment of the Supreme Court in Dharamvir Singh v UOI3. 2. The issue is covered by a recent decision rendered by us in UOI v Ex Sub Gawas Anil Madso4. 1 “the AFT”, hereinaf |
| TC-29aaf2f80f31 | hc-delhi-2025-w-p-c-11561-2024-dlhc010528542024-1-2025-07-17 | 2025-07-17 | 20/2 | stand covered by | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | on date more than eighty judgments passed by this Bench as well as by a Coordinate Benche of this Court. They also stand covered by the judgment of the Supreme Court in Dharamvir Singh v UOI1 as well as the recent decisi |
| TC-01f29269e959 | hc-delhi-2025-w-p-c-16646-2024-dlhc010881022024-1-2025-07-17 | 2025-07-17 | 20/2 | stand covered by | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | on date more than eighty judgments passed by this Bench as well as by a Coordinate Benche of this Court. They also stand covered by the judgment of the Supreme Court in Dharamvir Singh v UOI1 as well as the recent decisi |
| TC-ba37607deb14 | hc-delhi-2025-w-p-c-3004-2025-dlhc011098562024-1-2025-07-17 | 2025-07-17 | 20/2 | stand covered by | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | on date more than eighty judgments passed by this Bench as well as by a Coordinate Benche of this Court. They also stand covered by the judgment of the Supreme Court in Dharamvir Singh v UOI1 as well as the recent decisi |
| TC-79364172b29e | hc-delhi-2025-w-p-c-525-2025-dlhc010010462025-1-2025-07-18 | 2025-07-18 | 1/2 | is covered by | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | II2 has been allowed by the AFT relying on the judgment of the Supreme Court in Dharamvir Singh v UOI3. 2. The issue is covered by a recent decision rendered by us in UOI v Ex Sub Gawas Anil Madso4. 1 “the AFT”, hereinaf |
| TC-ede8eab68588 | hc-delhi-2025-w-p-c-8288-2025-dlhc010371182025-1-2025-07-29 | 2025-07-29 | 1/2 | is covered by | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | I2 has been allowed by the AFT relying on the judgment of the Supreme Court in Dharamvir Singh v UOI3. 2. The issue is covered by a recent decision rendered by us in UOI v Ex Sub Gawas Anil Madso4. 1 “the AFT”, hereinaft |
| TC-b3612034e8d7 | hc-delhi-2025-w-p-c-9135-2025-dlhc010401162025-1-2025-07-29 | 2025-07-29 | 3/8 | following the judgment | COURT_LIKELY | FOLLOWS | DOCUMENTARY_CHECK_REQUIRED | ady stands laid down by a slew of decisions of this Court, following the judgment of the Supreme Court in Dharamvir Singh v UOI4 and Bijender Singh v UOI5, albeit in the context of |
| TC-914653660da7 | hc-delhi-2025-w-p-c-9135-2025-dlhc010401162025-1-2025-07-29 | 2025-07-29 | 5/12 | applying the law | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | ified [[page 5]] WP(C) 9135/2025 Page 5 of 6 12. As such, applying the law laid down in Dharamvir Singh and later decisions, it has to be held that the hypertensi |
| TC-39485a4c03e4 | hc-delhi-2025-w-p-c-11227-2025-dlhc010513232025-1-2025-07-31 | 2025-07-31 | 1/2 | is covered by | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | II2 has been allowed by the AFT relying on the judgment of the Supreme Court in Dharamvir Singh v UOI3. 2. The issue is covered by a recent decision rendered by us in UOI v Ex Sub Gawas Anil Madso4. 1 “the AFT”, hereinaf |
| TC-a601d2685863 | hc-delhi-2025-w-p-c-11300-2025-dlhc010513972025-1-2025-07-31 | 2025-07-31 | 1/2 | is covered by | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | 0% has been allowed by the AFT relying on the judgment of the Supreme Court in Dharamvir Singh v UOI3. 2. The issue is covered by a recent decision rendered by us in UOI v Ex Sub Gawas Anil Madso4. 1 “the AFT”, hereinaft |
| TC-4d6d1513d6d7 | hc-delhi-2025-w-p-c-1019-2025-dlhc010029062025-1-2025-08-05 | 2025-08-05 | 8/2 | stand covered by | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | on date more than eighty judgments passed by this Bench as well as by a Coordinate Bench of this Court. They also stand covered by the judgment of the Supreme [[page 9]] W.P.(C) 13731/2024 and connected matters Page 9 of |
| TC-1f180392f404 | hc-delhi-2025-w-p-c-1019-2025-dlhc010029062025-1-2025-08-05 | 2025-08-05 | 9/6 | doubted | REPORTED_TREATMENT_OF_TARGET | - | LEGAL_INTERPRETATION_ADVISER_REVIEW | ending merely because some issue is pending before the Supreme Court. Even where the correctness of a judgment has been doubted by the Supreme Court, the decision in Jammu & Kashmir National Conference directs High Court |
| TC-e2b7ed92b281 | hc-delhi-2025-w-p-c-1279-2025-dlhc011044222024-1-2025-08-05 | 2025-08-05 | 8/2 | stand covered by | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | on date more than eighty judgments passed by this Bench as well as by a Coordinate Bench of this Court. They also stand covered by the judgment of the Supreme [[page 9]] W.P.(C) 13731/2024 and connected matters Page 9 of |
| TC-7bac8b425491 | hc-delhi-2025-w-p-c-1279-2025-dlhc011044222024-1-2025-08-05 | 2025-08-05 | 9/6 | doubted | REPORTED_TREATMENT_OF_TARGET | - | LEGAL_INTERPRETATION_ADVISER_REVIEW | ending merely because some issue is pending before the Supreme Court. Even where the correctness of a judgment has been doubted by the Supreme Court, the decision in Jammu & Kashmir National Conference directs High Court |
| TC-7f2dc8e1adb5 | hc-delhi-2025-w-p-c-13731-2024-dlhc010661482024-1-2025-08-05 | 2025-08-05 | 8/2 | stand covered by | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | on date more than eighty judgments passed by this Bench as well as by a Coordinate Bench of this Court. They also stand covered by the judgment of the Supreme Digitally Signed By:AJIT KUMAR Signing Date:07.08.2025 13:55: |
| TC-254e3ba6de3b | hc-delhi-2025-w-p-c-13731-2024-dlhc010661482024-1-2025-08-05 | 2025-08-05 | 9/6 | doubted | REPORTED_TREATMENT_OF_TARGET | - | LEGAL_INTERPRETATION_ADVISER_REVIEW | ending merely because some issue is pending before the Supreme Court. Even where the correctness of a judgment has been doubted by the Supreme Court, the decision in Jammu & Kashmir National Conference directs High Court |
| TC-adf597c4e6bb | hc-delhi-2025-w-p-c-1472-2025-dlhc010050772025-1-2025-08-05 | 2025-08-05 | 8/2 | stand covered by | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | on date more than eighty judgments passed by this Bench as well as by a Coordinate Bench of this Court. They also stand covered by the judgment of the Supreme [[page 9]] W.P.(C) 13731/2024 and connected matters Page 9 of |
| TC-01bc59e63560 | hc-delhi-2025-w-p-c-1472-2025-dlhc010050772025-1-2025-08-05 | 2025-08-05 | 9/6 | doubted | REPORTED_TREATMENT_OF_TARGET | - | LEGAL_INTERPRETATION_ADVISER_REVIEW | ending merely because some issue is pending before the Supreme Court. Even where the correctness of a judgment has been doubted by the Supreme Court, the decision in Jammu & Kashmir National Conference directs High Court |
| TC-1b23d40640f4 | hc-delhi-2025-w-p-c-1885-2025-dlhc010071512025-1-2025-08-05 | 2025-08-05 | 8/2 | stand covered by | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | on date more than eighty judgments passed by this Bench as well as by a Coordinate Bench of this Court. They also stand covered by the judgment of the Supreme [[page 9]] W.P.(C) 13731/2024 and connected matters Page 9 of |
| TC-b851f0a0dd35 | hc-delhi-2025-w-p-c-1885-2025-dlhc010071512025-1-2025-08-05 | 2025-08-05 | 9/6 | doubted | REPORTED_TREATMENT_OF_TARGET | - | LEGAL_INTERPRETATION_ADVISER_REVIEW | ending merely because some issue is pending before the Supreme Court. Even where the correctness of a judgment has been doubted by the Supreme Court, the decision in Jammu & Kashmir National Conference directs High Court |
| TC-a5f47010d8a4 | hc-delhi-2025-w-p-c-1907-2025-dlhc011067402024-1-2025-08-05 | 2025-08-05 | 8/2 | stand covered by | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | on date more than eighty judgments passed by this Bench as well as by a Coordinate Bench of this Court. They also stand covered by the judgment of the Supreme [[page 9]] W.P.(C) 13731/2024 and connected matters Page 9 of |
| TC-21d0a94b3a95 | hc-delhi-2025-w-p-c-1907-2025-dlhc011067402024-1-2025-08-05 | 2025-08-05 | 9/6 | doubted | REPORTED_TREATMENT_OF_TARGET | - | LEGAL_INTERPRETATION_ADVISER_REVIEW | ending merely because some issue is pending before the Supreme Court. Even where the correctness of a judgment has been doubted by the Supreme Court, the decision in Jammu & Kashmir National Conference directs High Court |
| TC-89560869e270 | hc-delhi-2025-w-p-c-2011-2025-dlhc010076222025-1-2025-08-05 | 2025-08-05 | 8/2 | stand covered by | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | on date more than eighty judgments passed by this Bench as well as by a Coordinate Bench of this Court. They also stand covered by the judgment of the Supreme [[page 9]] W.P.(C) 13731/2024 and connected matters Page 9 of |
| TC-77fbdce26d4f | hc-delhi-2025-w-p-c-2011-2025-dlhc010076222025-1-2025-08-05 | 2025-08-05 | 9/6 | doubted | REPORTED_TREATMENT_OF_TARGET | - | LEGAL_INTERPRETATION_ADVISER_REVIEW | ending merely because some issue is pending before the Supreme Court. Even where the correctness of a judgment has been doubted by the Supreme Court, the decision in Jammu & Kashmir National Conference directs High Court |
| TC-668c01de0004 | hc-delhi-2025-w-p-c-990-2025-dlhc011027202024-1-2025-08-05 | 2025-08-05 | 8/2 | stand covered by | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | on date more than eighty judgments passed by this Bench as well as by a Coordinate Bench of this Court. They also stand covered by the judgment of the Supreme [[page 9]] W.P.(C) 13731/2024 and connected matters Page 9 of |
| TC-71b72f719ecd | hc-delhi-2025-w-p-c-990-2025-dlhc011027202024-1-2025-08-05 | 2025-08-05 | 9/6 | doubted | REPORTED_TREATMENT_OF_TARGET | - | LEGAL_INTERPRETATION_ADVISER_REVIEW | ending merely because some issue is pending before the Supreme Court. Even where the correctness of a judgment has been doubted by the Supreme Court, the decision in Jammu & Kashmir National Conference directs High Court |
| TC-715eb9003ade | hc-ph-2025-cwp-22838-2025-phhc011154262025-1-2025-08-07 | 2025-08-07 | 2/3 | is covered by | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | the military service and the said claim of respondent No.1 is covered by the judgment of the Hon’ble Supreme Court of India in Dharamvir Singh vs. Union of India, (2013) 7 SCC 316. 4. The Tribunal, after appreciating the |
| TC-339d46486a3b | hc-jkl-2025-wp-c-436-2024-jkhc020009872024-1-2025-08-30 | 2025-08-30 | 7/19 | in view of the ratio | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | bunal while relying upon Regulation 173 Regulation 292 of the Pension Regulation for the Army, 1961 (Part-1) and in view of the ratio of the judgment of Supreme Court in case titled Dharamvir Singh vs. [[page 8]] Page 8  |
| TC-a7b2ff2fd7d1 | hc-delhi-2025-w-p-c-17124-2024-dlhc010916102024-1-2025-09-08 | 2025-09-08 | 13/18 | squarely covered | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | 3 of 13 18. In our considered opinion, the matter would be squarely covered by the law laid down in Dharamvir Singh, Bijender Singh, Gawas Anil Madso and Balbir Singh. We are |
| TC-7d74d314c9f8 | hc-delhi-2025-w-p-c-14415-2025-dlhc010692622025-1-2025-09-23 | 2025-09-23 | 1/2 | is covered by | COURT_LIKELY | APPLIES | DOCUMENTARY_CHECK_REQUIRED | II2 has been allowed by the AFT relying on the judgment of the Supreme Court in Dharamvir Singh v UOI3. 2. The issue is covered by a recent decision rendered by us in UOI v Ex Sub Gawas Anil Madso4. 1 “the AFT”, hereinaf |
| TC-cba162ac6fbd | hc-delhi-2025-w-p-c-15009-2025-dlhc010740692025-1-2025-09-26 | 2025-09-26 | 2/3 | following the decision | COURT_LIKELY | FOLLOWS | DOCUMENTARY_CHECK_REQUIRED | ch identical grounds have been cited by the medical board, following the decision of Supreme Court in Dharamvir Singh v UOI2, Bijender Singh v Union of India3 as well as Union |

### Name-only mentions (not resolved; may be false positives)

- **Pattern:** `dharamvir singh`. Searched in judgments with no resolved or string-matched edge to this case.
- **Window:** decided on or after 2013-07-02.
- **Hits:** 113 judgments.
  - hc-jkl-2026-wp-c-757-2025-jkhc020016342025-1-2026-08-18 (2026-08-18) p.4: "The controversy involved in the present petition is no longer res integra. In Dharamvir Singh v. Union of India, the Hon'ble Supreme Court held that where a member of the"
  - hc-delhi-2026-w-p-c-13401-2025-dlhc010633632025-1-2026-08-11 (2026-08-11) p.5: "10th December, 2014 and also that of Secretary, Government of India & Ors. v. Dharamvir Singh v. Union of India and Ors., (2020) 14 SCC 582. 9. In view of the aforesaid, in"
  - hc-ph-2026-cwp-18775-2026-phhc010830372026-1-2026-07-01 (2026-07-01) p.2: "bility pension to respondent No.1, It should be noted that as per judgment in Dharamvir Singh vs. Union of India and others, (2013) 7 NITIN 2026.07.06 10:40 I attest to the"
  - hc-delhi-2026-w-p-c-1181-2025-dlhc011038082024-1-2026-04-20 (2026-04-20) p.1: "delivered on: 20.04.2026 Judgment uploaded on: 20.04.2026 + W.P.(C) 1181/2025 DHARAMVIR SINGH .....Petitioner versus UNION OF INDIA AND ORS .....Respondents Advocates who a"
  - hc-delhi-2026-w-p-c-9610-2023-dlhc010276422023-1-2026-04-17 (2026-04-17) p.5: "NT& ANR. .....Respondents 95 + W.P.(C) 18812/2025 and CM APPL. 78282/2025 DHARAMVIR SINGH .....Petitioner versus UNION OF INDIA AND OTHERS .."
  - hc-delhi-2026-w-p-c-8859-2025-dlhc010392102025-1-2026-04-17 (2026-04-17) p.5: "NT& ANR. .....Respondents 95 + W.P.(C) 18812/2025 and CM APPL. 78282/2025 DHARAMVIR SINGH .....Petitioner versus UNION OF INDIA AND OTHERS .."
  - hc-delhi-2026-w-p-c-8252-2024-dlhc010342572024-1-2026-04-17 (2026-04-17) p.5: "NT& ANR. .....Respondents 95 + W.P.(C) 18812/2025 and CM APPL. 78282/2025 DHARAMVIR SINGH .....Petitioner versus UNION OF INDIA AND OTHERS .."
  - hc-delhi-2026-w-p-c-7503-2024-dlhc010313462024-1-2026-04-17 (2026-04-17) p.5: "NT& ANR. .....Respondents 95 + W.P.(C) 18812/2025 and CM APPL. 78282/2025 DHARAMVIR SINGH .....Petitioner versus UNION OF INDIA AND OTHERS .."
  - hc-delhi-2026-w-p-c-7484-2023-dlhc010212732023-1-2026-04-17 (2026-04-17) p.5: "NT& ANR. .....Respondents 95 + W.P.(C) 18812/2025 and CM APPL. 78282/2025 DHARAMVIR SINGH .....Petitioner versus UNION OF INDIA AND OTHERS .."
  - hc-delhi-2026-w-p-c-549-2025-dlhc010011362025-1-2026-04-17 (2026-04-17) p.5: "NT& ANR. .....Respondents 95 + W.P.(C) 18812/2025 and CM APPL. 78282/2025 DHARAMVIR SINGH .....Petitioner versus UNION OF INDIA AND OTHERS .."

### Contrary authority / conflicting treatment

- C10 records N C Isaac (2026 INSC 993; official copy outside this text layer) as clarifying Dharamvir for the 2008 Entitlement Rules (Isaac p.91 para 34). Dharamvir applied the 1982 Rules (RD-DHARAMVIR-H1). Isaac was not re-read in C11.

### Open questions and uncertainty

- Instrument version: Dharamvir construes the Entitlement Rules 1982. Citing judgments that concern 2008-Rules claimants need an adviser check (C10 ESC-C10-04). The statute-link table marks ENT-1982 vs ENT-2008 vs ENT-UNSPECIFIED and never infers the version.

## Key authorities by in-degree (graph-derived; not priority-read)

In-degree is the number of distinct citing judgments with a resolved CITES edge. Proposals are cue-based and unverified.

| Rank | Authority | Date | Court | In-degree | Proposed treatments (by relation) | Adviser-review candidates |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | BIJENDER SINGH versus UNION OF INDIA & ORS. (sc-2025-bijender-singh-2025insc549) | 2025-04-23 | SC | 452 | APPLIES 2, DISTINGUISHES 1, FOLLOWS 4 | 0 |
| 2 | DHARAMVIR SINGH versus UNION OF INDIA & ORS. (sc-2013-dharamvir-singh-2013insc408) | 2013-07-02 | SC | 352 | APPLIES 37, DISTINGUISHES 1, FOLLOWS 5 | 8 |
| 3 | W.P.(C)/3545/2025 of UNION OF INDIA & ORS. Vs EX SUB GAWAS ANIL MADSO (hc-delhi-2025-w-p-c-3545-2025-dlhc010148412025-1-2025-03-27) | 2025-03-27 | High Court of Delhi | 127 | APPLIES 53 | 0 |
| 4 | SUKHVINDER SINGH versus UNION OF INDIA & ORS. (sc-2014-sukhvinder-singh-2014insc421) | 2014-06-25 | SC | 85 | APPLIES 2, DISTINGUISHES 1 | 0 |
| 5 | UNION OF INDIA & ANR. versus RAJBIR SINGH (sc-2015-union-of-india-anr-2015insc114) | 2015-02-13 | SC | 75 | APPLIES 2, DISTINGUISHES 3 | 0 |
| 6 | NO. 1466828M EX CFN NARSINGH YADAV versus UNION OF INDIA & ORS. (sc-2019-no-1466828m-ex-cfn-narsingh-ya-2019insc1121) | 2019-10-03 | SC | 73 | APPLIES 17 | 0 |
| 7 | RAJUMON T.M. versus UNION OF INDIA & ORS. (sc-2025-rajumon-t-m-2025insc644) | 2025-05-07 | SC | 61 | - | 0 |
| 8 | W.P.(C)/88/2026 of UNION OF INDIA & ORS. Vs 781466 EX SGT KRISHNA KUMA (hc-delhi-2026-w-p-c-88-2026-dlhc011079442025-1-2026-01-06) | 2026-01-06 | High Court of Delhi | 60 | - | 0 |
| 9 | MANEKA GANDHI versus UNION OF INDIA (sc-1978-maneka-gandhi-1978insc16) | 1978-01-25 | SC | 59 | - | 2 |
| 10 | K.J.S. BUTTAR versus UNION OF INDIA AND ANR. (sc-2011-k-j-s-buttar-2011insc249) | 2011-03-31 | SC | 48 | - | 0 |
| 11 | UNION OF INDIA & ORS. versus TARSEM SINGH (sc-2008-union-of-india-ors-2008insc930) | 2008-08-13 | SC | 45 | APPLIES 1, DISTINGUISHES 5 | 1 |
| 12 | WP(C)/1633/2024 of UNION OF INDIA TH SECRETARY GOI MINISTRY OF DEFENCE (hc-jkl-2025-wp-c-1633-2024-jkhc020007942024-1-2025-08-19) | 2025-08-19 | High Court of Jammu and Kashmir | 44 | - | 0 |
| 13 | RANJIT THAKUR versus UNION OF INDIA AND ORS. (sc-1987-ranjit-thakur-1987insc285) | 1987-10-15 | SC | 41 | - | 0 |
| 14 | SHIV DASS versus UNION OF INDIA AND ORS . (sc-2007-shiv-dass-2007insc64) | 2007-01-18 | SC | 34 | APPLIES 1, FOLLOWS 1 | 0 |
| 15 | UNION OF INDIA & ANR. versus PURUSHOTTAM (sc-2015-union-of-india-anr-2015insc2) | 2015-01-05 | SC | 27 | - | 0 |
| 16 | LT. COL. PRITHI PAL SINGH BEDI ETC. versus UNION OF INDIA & OTHERS (sc-1982-lt-col-prithi-pal-singh-bedi-e-1982insc65) | 1982-08-25 | SC | 25 | DISTINGUISHES 1 | 0 |
| 17 | S.N. MUKHERJEE versus UNION OF INDIA (sc-1990-s-n-mukherjee-1990insc257) | 1990-08-28 | SC | 25 | FOLLOWS 1 | 0 |
| 18 | SECRETARY, MINISTRY OF DEFENCE & OTHERS versus DAMODARAN A.V. (DEAD) T (sc-2009-secretary-ministry-of-defence-2009insc1059) | 2009-08-20 | SC | 22 | - | 0 |
| 19 | UNION OF INDIA THROUGH ITS SECRETARY & ORS. versus SGT GIRISH KUMAR AN (sc-2026-union-of-india-through-its-sec-2026insc149) | 2026-02-12 | SC | 22 | APPLIES 9 | 0 |
| 20 | UNION OF INDIA AND ANR. versus SH. BALJIT SINGH (sc-1996-union-of-india-and-anr-1996insc1198) | 1996-10-11 | SC | 20 | - | 0 |

## Method notes and limits

- **Citation detection.** Patterns cover SCC, SCC OnLine, SCR (all common layouts), AIR, INSC, JT, SLT, SCALE, SLR, HC neutral citations, and case numbers (Civil/Criminal Appeal, SLP, W.P.(C), CWP, SWP, OWP, WRIA, LPA).
- **Resolution order.**
  - First, deterministic keys from the target's own metadata (neutral citation, reported citation, or a self-printed HC neutral citation).
  - Then the C10-held curated crosswalk.
  - Then parallel citations learned from metadata-resolved clusters.
  - Last, a conservative fallback: case number plus a party-name bigram, or party bigram plus year plus court.
  - Ambiguous matches stay UNRESOLVED_AMBIGUOUS with their candidates.
- **Dropped references.** These are not citations and are dropped: self-citations, the citing judgment's own case numbers, and same-day connected matters.
- **Treatment attribution.** Cue words in reporter headnotes or case-law lists, in quoted passages, in party submissions, or in reports of what a lower forum or another bench did never produce a proposal. Neither do past-tense participles without present or first-person voice, or cues more than 150-250 characters from the citation. OVERRULES, REVERSES and QUESTIONS proposals always go to adviser review.
- **Coverage limits.** Coverage is limited to the crawler judgment corpus (ad77758d). The official copies of Girish, Parashotam, Mullikote, Isaac and others in the C5 working store or HF legal_knowledge were not part of this input. The absence of a hit is not proof that no treatment exists.

