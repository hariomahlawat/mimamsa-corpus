# Human page-verification pack: Supreme Court anchor candidates (Cycle 9)

**Read this first.**
- Every reading in this pack is a **proposal** by an AI agent (Claude Opus 5.5 subagent). **It is not human confirmation.** Nothing here counts as a CONFIRMED identity check until a named person completes the blank fields.
- The pack approves nothing, authenticates nothing and says nothing about precedent status (good law, followed, overruled). The AUTH-LEDGER stays at version 0.
- Copies whose approval would create a new exact anchor: Ranjit Thakur, S N Mukherjee, Navjot Sandhu, Dharamvir Singh, Rajbir Singh C1, Girish Kumar, Mullikote. **Narsingh Yadav ("N S Yadav") is not included:** it has no case record, so approving it creates no anchor (C9 simulation: 6 -> 6). PPS Bedi is included as an optional context sheet for P-D3 only.
- Privacy: open the held PDF or the render; do not copy page text into this pack. Record only the identity elements listed. Service numbers are masked; do not write them down. Medical and personal details must not be recorded.

## How to review one copy
1. Re-hash the held file: `sha256sum <scratchpad>/<held path>` and compare with the sha256 shown. Stop if it differs.
2. Open the listed PDF pages (or regenerate the renders with `tools/render_c9.py`; each render's sha256 is given so you can check you are looking at the same image).
3. For each item, compare the AI proposal with the page and fill in `reviewer_name`, `review_date`, `result_CONFIRMED_or_NOT_CONFIRMED` and `reviewer_notes` in `human_verification_checklist.csv`.
4. Answer the discrepancy questions in the notes. A NOT CONFIRMED result on any identity element blocks that copy.

Render settings for every page: PyMuPDF 2.1 (MuPDF 1.28.6), 150 dpi, grayscale, full page. All 28 pages rendered in C8 were re-rendered in C9 and are byte-identical (`tools/render_facts_c9.jsonl`, column `c8_reproduced`).

## Ranjit Thakur v Union of India (1987)

- Copy: `C5-SRC-J-SC-1987-RANJIT-THAKUR~C1`; role: ANCHOR_CANDIDATE (depends on P-D3); case record: DCLR-SC-1987-R01; anchor effect if approved alone: 6 -> 7
- Re-hash: `downloads/citation-codes/ranjit_judis8566.pdf` must give `ed7cf31fd8fbe50822e0a60f80b96ed1187dcd465dc4ae2649424c58001ff399` (9 pages)

- PDF pages to open: 1, 3, 4, 9

| Item | Page | Render sha256 | Element | AI proposal (not human-confirmed) | Question |
| --- | --- | --- | --- | --- | --- |
| C9-HV-RANJIT-01 | 1 | `7e4bcd455e48a51e130bf6c3e58cf0e2fd2ab5b2a6c556f7559b65f4f254c9d2` | court / header | SUPREME COURT OF INDIA (database header 'http://JUDIS.NIC.IN ... Page 1 of 9') | Is this a JUDIS database rendition (URL header, field labels, JUDIS watermark) rather than a signed court-layout judgment? |
| C9-HV-RANJIT-02 | 1 | `7e4bcd455e48a51e130bf6c3e58cf0e2fd2ab5b2a6c556f7559b65f4f254c9d2` | parties | PETITIONER: RANJIT THAKUR / RESPONDENT: UNION OF INDIA AND ORS. | Confirm parties as printed. |
| C9-HV-RANJIT-03 | 1 | `7e4bcd455e48a51e130bf6c3e58cf0e2fd2ab5b2a6c556f7559b65f4f254c9d2` | date | DATE OF JUDGMENT 15/10/1987 | Confirm the date field. |
| C9-HV-RANJIT-04 | 1 | `7e4bcd455e48a51e130bf6c3e58cf0e2fd2ab5b2a6c556f7559b65f4f254c9d2` | bench | VENKATACHALLIAH, M.N. (J); SEN, A.P. (J) | Confirm the bench field. |
| C9-HV-RANJIT-05 | 1 | `7e4bcd455e48a51e130bf6c3e58cf0e2fd2ab5b2a6c556f7559b65f4f254c9d2` | citations (database block) | 1987 AIR 2386; 1988 SCR (1) 512; 1987 SCC (4) 611; JT 1987 (4) 93; 1987 SCALE (2)773 | Confirm the CITATION block. AIR 1987 SC 2386 is not in the case record: is it printed here? |
| C9-HV-RANJIT-06 | 3 | `7606bb0ecc3798f6bd89fe266a23e00102bea12126c126a26b2fe1c9ac72747c` | case number | Civil Appeal No. 2630 of 1987 (after 'JUDGMENT:') | Confirm the case number and that the HEADNOTE ends before 'JUDGMENT:' on this page. |
| C9-HV-RANJIT-07 | 3 | `7606bb0ecc3798f6bd89fe266a23e00102bea12126c126a26b2fe1c9ac72747c` | editorial note | Headnote note: point 1.3 to be read with and subject to the subsequent order dated 10.8.88 | Is this note part of the headnote (database/reporter matter), not the judgment? (The 10.8.88 order is not held.) |
| C9-HV-RANJIT-08 | 4 | `3976b6230f09ca8341a8e16fefe4d40c04fb2ac58d249bf0bdfd0682022d5e90` | author | VENKATACHALIAH, J. (judgment of the Court) | Confirm the author line. |
| C9-HV-RANJIT-09 | 9 | `a833f075ecec77b64cc3c566b96844307eda26d768c8a3a4c7177a9dadddd695` | end of text | Ends 'N.P.V. Appeal allowed.' then report page 525; no signature lines, names or date | Confirm there is no signature or date block (completeness against a signed original cannot be shown). |

**Discrepancy questions**
- Headnote and database fields occupy pp.1-3 up to 'JUDGMENT:'. Should any pinpoint into pp.1-3 be refused?
- The editorial note refers to a subsequent order dated 10.8.88 that is not held. Note this; do not resolve it.

| Reviewer name | Date | CONFIRMED / NOT CONFIRMED (copy as a whole) | Notes |
| --- | --- | --- | --- |
|  |  |  |  |

## S.N. Mukherjee v Union of India (1990)

- Copy: `C5-SRC-J-SC-1990-SN-MUKHERJEE~C1`; role: ANCHOR_CANDIDATE (depends on P-D3); case record: DCLR-SC-1990-N02; anchor effect if approved alone: 6 -> 7
- Re-hash: `downloads/citation-codes/snmukherjee_judis7439.pdf` must give `eb4420801e978469e9c7407f8c079273f9cd483ad45a4427daa53e3d229969cc` (23 pages)

- PDF pages to open: 1, 3, 4, 23

| Item | Page | Render sha256 | Element | AI proposal (not human-confirmed) | Question |
| --- | --- | --- | --- | --- | --- |
| C9-HV-SNM-01 | 1 | `3e29828807624ca53813e22796c6fa24dae0f3ae76279962c3889adb8a0a5f6e` | court / header | SUPREME COURT OF INDIA (JUDIS header, Page 1 of 23) | JUDIS database rendition? (as for Ranjit) |
| C9-HV-SNM-02 | 1 | `3e29828807624ca53813e22796c6fa24dae0f3ae76279962c3889adb8a0a5f6e` | parties | PETITIONER: S.N. MUKHERJEE / RESPONDENT: UNION OF INDIA | Confirm parties as printed. |
| C9-HV-SNM-03 | 1 | `3e29828807624ca53813e22796c6fa24dae0f3ae76279962c3889adb8a0a5f6e` | date | DATE OF JUDGMENT 28/08/1990 | Confirm the date field. |
| C9-HV-SNM-04 | 1 | `3e29828807624ca53813e22796c6fa24dae0f3ae76279962c3889adb8a0a5f6e` | bench | AGRAWAL, S.C. (J); MUKHARJI, SABYASACHI (CJ); KANIA, M.H.; SHETTY, K.J. (J); SAIKIA, K.N. (J) | Confirm five names in the bench field. |
| C9-HV-SNM-05 | 1 | `3e29828807624ca53813e22796c6fa24dae0f3ae76279962c3889adb8a0a5f6e` | citations (database block) | 1990 AIR 1984; 1990 SCR Supl. (1) 44; 1990 SCC (4) 594; JT 1990 (3) 630; 1990 SCALE (2)383 | Confirm the CITATION block (AIR 1990 SC 1984 is not in the case record). |
| C9-HV-SNM-06 | 3 | `a91a7f7643b982222329c6eacaa5032677fb6ac189fc9991481091257df6aecb` | case number | Civil Appeal No. 417 of 1984 (after 'JUDGMENT:'); headnote and cases-referred list end on this page | Confirm the case number (the case record DCLR-SC-1990-N02 has none) and the end of the headnote. |
| C9-HV-SNM-07 | 4 | `5867d0edd31fd01ab7d14263d11976c91dfaa5b5110acece1647832ad0ddb3a9` | author | S.C. AGRAWAL, J. (judgment of the Court) | Confirm the author line. |
| C9-HV-SNM-08 | 23 | `1a6cf0ed2b05deaaa1abafab8e0b220bdda6afd1a44de98583e503a0c4b2b63e` | end of text | Ends 'R.N.J. Appeal dismissed.' then report page 76; no signature or date block | Confirm there is no signature or date block. |

**Discrepancy questions**
- The case record has no case number; the copy prints Civil Appeal No. 417 of 1984 (p.3).
- The recorded locator is /judgment/judis/7439.pdf, not /jonew/judis/ (path alias unverified).

| Reviewer name | Date | CONFIRMED / NOT CONFIRMED (copy as a whole) | Notes |
| --- | --- | --- | --- |
|  |  |  |  |

## State (N.C.T. of Delhi) v Navjot Sandhu @ Afsan Guru (2005)

- Copy: `C5-SRC-J-SC-2005-NAVJOT~C1`; role: ANCHOR_CANDIDATE (depends on P-D3; C8 recommends keep PARTIAL); case record: DCLR-SC-2005-L01; anchor effect if approved alone: 6 -> 7
- Re-hash: `downloads/independent-reviewer-B/navjot_sandhu_2005.pdf` must give `3b75354869ffb928f73532f475f5f920e2f2a1f8817163caba2f7fb5e1eb215d` (107 pages)

- PDF pages to open: 1, 2, 107

| Item | Page | Render sha256 | Element | AI proposal (not human-confirmed) | Question |
| --- | --- | --- | --- | --- | --- |
| C9-HV-NAVJOT-01 | 1 | `0a447a1e4d36ab1ffaf11e77a2695f75058089f35a14d3c62c0d3763fd1f0ba6` | court / header | SUPREME COURT OF INDIA (JUDIS header, Page 1 of 107); no CITATION, CITATOR or HEADNOTE block | JUDIS database rendition without headnote? |
| C9-HV-NAVJOT-02 | 1 | `0a447a1e4d36ab1ffaf11e77a2695f75058089f35a14d3c62c0d3763fd1f0ba6` | case number | Appeal (crl.) 373-375 of 2004; with Crl.A. 376-378, 379-380 and 381 of 2004 | Confirm the lead and connected case numbers. |
| C9-HV-NAVJOT-03 | 1 | `0a447a1e4d36ab1ffaf11e77a2695f75058089f35a14d3c62c0d3763fd1f0ba6` | parties | STATE (N.C.T. OF DELHI) v NAVJOT SANDHU @ AFSAN GURU (connected appeals list three further accused by name) | Confirm the lead cause title. |
| C9-HV-NAVJOT-04 | 1 | `0a447a1e4d36ab1ffaf11e77a2695f75058089f35a14d3c62c0d3763fd1f0ba6` | date | DATE OF JUDGMENT: 04/08/2005 (read as 4 August 2005) | DISCREPANCY Q-NAVJOT-DATE: confirm the printed string. The field does not itself show day/month order; the sibling JUDIS files print 15/10/1987, 28/08/1990 and 25/08/1982 (day first). Record whether 4 August 2005 is the reading you accept. The date is absent from the case record and C6-01 identity. |
| C9-HV-NAVJOT-05 | 1 | `0a447a1e4d36ab1ffaf11e77a2695f75058089f35a14d3c62c0d3763fd1f0ba6` | bench / author | P. VENKATARAMA REDDI & P.P. NAOLEKAR; author P. VENKATARAMA REDDI, J. | Confirm the bench and author. |
| C9-HV-NAVJOT-06 | 2 | `7de6ee7fee4fd1597b98cd54509b31b862b78069e865a1321244384838e5e09c` | transcription defects (optional) | Literal escape sequences such as '\027' appear in running text (text layer: \005 x90, \026 x22, \027 x127) | Optional: do escape sequences appear on the page image as printed characters? |
| C9-HV-NAVJOT-07 | 107 | `bca06917ebcbe6fc86871edf74db7f8f073900f22885efc5fd92f3d87d4cfb96` | end of text | Ends at the operative paragraph; no signature lines, names or date | Confirm there is no signature or date block. |

**Discrepancy questions**
- Q-NAVJOT-DATE: printed '04/08/2005'; case record and C6-01 identity have no date or case number.
- First-class record S-REVB-012 is SOURCE_LOCATED, not VERIFIED. No paragraph numbers (WS-B OI-11).

| Reviewer name | Date | CONFIRMED / NOT CONFIRMED (copy as a whole) | Notes |
| --- | --- | --- | --- |
|  |  |  |  |

## Dharamvir Singh v Union of India (2013)

- Copy: `C5-SRC-J-SC-2013-DHARAMVIR~C1`; role: ANCHOR_CANDIDATE; case record: DCLR-SC-2013-N08; anchor effect if approved alone: 6 -> 7
- Re-hash: `downloads/independent-reviewer-B/dharamvir_40493.pdf` must give `3056712cc7614399f72ee19f529f91990e70dba8a317dd3bd07e76e4ac546b75` (36 pages)

- PDF pages to open: 1, 36

| Item | Page | Render sha256 | Element | AI proposal (not human-confirmed) | Question |
| --- | --- | --- | --- | --- | --- |
| C9-HV-DHARAMVIR-01 | 1 | `7adab58a0e1d2293415792e36d8cd9ef701f5be1e7f7d5a05a0fbab8a446c167` | court | IN THE SUPREME COURT OF INDIA, CIVIL APPELLATE JURISDICTION; REPORTABLE | Confirm court and marking. |
| C9-HV-DHARAMVIR-02 | 1 | `7adab58a0e1d2293415792e36d8cd9ef701f5be1e7f7d5a05a0fbab8a446c167` | case number | CIVIL APPEAL NO. 4949 OF 2013 (arising out of SLP(C) No. 6940 of 2010) | Confirm the case number. |
| C9-HV-DHARAMVIR-03 | 1 | `7adab58a0e1d2293415792e36d8cd9ef701f5be1e7f7d5a05a0fbab8a446c167` | parties | DHARAMVIR SINGH ... APPELLANT VERSUS UNION OF INDIA & ORS. ... RESPONDENTS | Confirm parties as printed. |
| C9-HV-DHARAMVIR-04 | 1 | `7adab58a0e1d2293415792e36d8cd9ef701f5be1e7f7d5a05a0fbab8a446c167` | reported citation | No neutral or reported citation printed | DISCREPANCY: the case record gives (2013) 7 SCC 316. Confirm it is NOT printed on this copy (so it cannot be confirmed from it). |
| C9-HV-DHARAMVIR-05 | 36 | `2cfbe0b19378f7f6bb527dbefd54940eec0cf0d3882e43c3c76e8aad565e9437` | bench and date | (A.K. PATNAIK) J.; (SUDHANSU JYOTI MUKHOPADHAYA) J.; NEW DELHI, JULY 2, 2013 | Confirm bench names and place/date; signature lines are dotted placeholders. |

**Discrepancy questions**
- (2013) 7 SCC 316 is in the case record but not printed on the copy.

| Reviewer name | Date | CONFIRMED / NOT CONFIRMED (copy as a whole) | Notes |
| --- | --- | --- | --- |
|  |  |  |  |

## Union of India v Rajbir Singh (2015), copy C1

- Copy: `C5-SRC-J-SC-2015-RAJBIR~C1`; role: ANCHOR_CANDIDATE (C1 only; C2/C3 are context); case record: DCLR-SC-2015-N09; anchor effect if approved alone: 6 -> 7
- Re-hash: `downloads/independent-reviewer-B/rajbir_42379.pdf` must give `970b96807bcbf8a1255fe16c574b575f64fe2edee1cbb271485fa7661a62c666` (20 pages)

- PDF pages to open: 1, 2, 20; context: C2 p.18, C3 p.1

| Item | Page | Render sha256 | Element | AI proposal (not human-confirmed) | Question |
| --- | --- | --- | --- | --- | --- |
| C9-HV-RAJBIR_C1-01 | 1 | `28d6d109297cda9b6f92e140ee6cf85ee0f37443385c62eb42f69e4c889ce9f2` | court / case number | IN THE SUPREME COURT OF INDIA, CIVIL APPELLATE JURISDICTION; REPORTABLE; CIVIL APPEAL NO.2904 OF 2011 (with connected appeals) | Confirm court, marking and lead case number. |
| C9-HV-RAJBIR_C1-02 | 1 | `28d6d109297cda9b6f92e140ee6cf85ee0f37443385c62eb42f69e4c889ce9f2` | parties | Union of India & Anr. ...Appellants Versus Rajbir Singh ...Respondent | Confirm parties as printed. |
| C9-HV-RAJBIR_C1-03 | 1 | `28d6d109297cda9b6f92e140ee6cf85ee0f37443385c62eb42f69e4c889ce9f2` | copy identity | This file (970b9680...) carries a watermark and a 'Page N' footer; it does not itself bear the identifiers 'rop_275403' or 'bosir' (those are the file names of copies C2 and C3) | DISCREPANCY Q-RAJBIR-C1: confirm you are reviewing C1 (re-hash) and that the C6-01/C5 identity string 'JUDIS 42379; rop_275403; bosir copy' is a source-level title naming all three copies, not C1's own identity. |
| C9-HV-RAJBIR_C1-04 | 2 | `3004d4d10cd6ea0dc7ffc1f2533ede5a71c9e3f0a77ae1f8b73d53f5070bd64e` | author / connected appeals | Remaining connected C.A. numbers; author T.S. THAKUR, J. | Confirm the author line. |
| C9-HV-RAJBIR_C1-05 | 20 | `b878d20eb2c653b3fc3f05c8b03fe8f3bd5e55ae37cea88e28eebeb9fe09f128` | bench and date | (T.S. THAKUR) J.; (R. BANUMATHI) J.; New Delhi February 13, 2015; judgment ends on p.20 of C1 | Confirm bench, date and that the judgment ends on p.20 of C1. |
| C9-HV-RAJBIR_C2-01 | 18 (RAJBIR_C2) | `be1cd82c056d1e567ed1118b60bb312529ffe1ea7b289d52d5b0f1fa15775156` | context: end of judgment in C2 | Same operative words and bench as C1 p.20, ending on C2 p.18 | Context only: is C2 p.18 the same ending as C1 p.20 (so pinpoints differ by copy)? |
| C9-HV-RAJBIR_C3-01 | 1 (RAJBIR_C3) | `2ff9d1d0c4994852acca3bd3c5ede14dd43ac82a66aa6dff855432f709057c47` | context: C3 rendition | Monospaced plain-text rendition of the C2 content (non-primary; never an anchor) | Context only: confirm C3 is a text rendition, not a court-layout copy. |

**Discrepancy questions**
- Q-RAJBIR-C1: the identity string 'JUDIS 42379; rop_275403; bosir copy' is the C5 source-level title naming all three copies; C1 is 970b9680 only.
- C1 judgment ends p.20; C2 ends p.18 (C2 pp.19-21 are the Record of Proceedings); C3 is a non-primary text rendition. Pinpoints are copy-specific.

| Reviewer name | Date | CONFIRMED / NOT CONFIRMED (copy as a whole) | Notes |
| --- | --- | --- | --- |
|  |  |  |  |

## Union of India v Sgt Girish Kumar (2026 INSC 149)

- Copy: `C5-SRC-J-SC-2026-GIRISH-FEB~C1`; role: ANCHOR_CANDIDATE; case record: DCLR-SC-2026-007; anchor effect if approved alone: 6 -> 7
- Re-hash: `downloads/citation-codes/girish_feb2026.pdf` must give `4f7ea3a451c6f9a11d7e4dd96822e68cd9cd7a01d8dc74cf46ad34e79029b86c` (17 pages)

- PDF pages to open: 1, 3, 17

| Item | Page | Render sha256 | Element | AI proposal (not human-confirmed) | Question |
| --- | --- | --- | --- | --- | --- |
| C9-HV-GIRISH-01 | 1 | `462d2e259420dbf50327aff6f3d2f0efe8ee53d68b49fcd3efb0fcda41582fbd` | court / marking / neutral citation | IN THE SUPREME COURT OF INDIA, CIVIL APPELLATE JURISDICTION; REPORTABLE; 2026 INSC 149 | DISCREPANCY: the case record reporter_citation is empty. Confirm '2026 INSC 149' is printed. |
| C9-HV-GIRISH-02 | 1 | `462d2e259420dbf50327aff6f3d2f0efe8ee53d68b49fcd3efb0fcda41582fbd` | case number / parties | CIVIL APPEAL NOS.6820-6824 OF 2018; UNION OF INDIA THROUGH ITS SECRETARY & ORS. v SGT GIRISH KUMAR AND ORS. ETC. | Confirm the lead case numbers and parties; note blank connected numbers. |
| C9-HV-GIRISH-03 | 1 | `462d2e259420dbf50327aff6f3d2f0efe8ee53d68b49fcd3efb0fcda41582fbd` | signature appearance | 'Signature Not Verified / Digitally signed by KAPIL TANDON / Date: 2026.02.12' | Confirm the visible appearance (no validation is asked of you). |
| C9-HV-GIRISH-04 | 3 | `922120cb7ba0fa100c3edd3750dc987ebc6fd155fb1ebbb2b58a19e2f9805a2d` | author | ALOK ARADHE, J. | Confirm the author line. |
| C9-HV-GIRISH-05 | 17 | `3e21477c09144bbddbf930124c73766697ae2df03783f79e62c915c472552789` | bench and date | [PAMIDIGHANTAM SRI NARASIMHA] J.; [ALOK ARADHE] J.; NEW DELHI; FEBRUARY 12, 2026. | Confirm bench and date. |

**Discrepancy questions**
- '2026 INSC 149' printed; the case record's reporter_citation is empty (proposal E8-CP-10--007, not applied).

| Reviewer name | Date | CONFIRMED / NOT CONFIRMED (copy as a whole) | Notes |
| --- | --- | --- | --- |
|  |  |  |  |

## Union of India v Balakrishnan Mullikote (2026 INSC 286)

- Copy: `C5-SRC-J-SC-2026-MULLIKOTE~C1`; role: ANCHOR_CANDIDATE (C8 recommends keep PARTIAL until pp.1-31 named); case record: DCLR-SC-2026-N16; anchor effect if approved alone: 6 -> 7
- Re-hash: `downloads/citation-codes/mullikote_2026.pdf` must give `10e1954f2e39916ea0f0e8e759c3823581becf752dd6ad2e9058569a1fd97444` (62 pages)

- PDF pages to open: 1, 4, 31, 32, 35, 62

| Item | Page | Render sha256 | Element | AI proposal (not human-confirmed) | Question |
| --- | --- | --- | --- | --- | --- |
| C9-HV-MULLIKOTE-01 | 1 | `4846bbf0df2bb5fb1fd0f1338eea0e251a3d130ffe86c43ca434f7309fd20aa3` | markings / neutral citation | CORRECTED; 2026 INSC 286; REPORTABLE; QR code | Confirm the CORRECTED marking and neutral citation on p.1. |
| C9-HV-MULLIKOTE-02 | 1 | `4846bbf0df2bb5fb1fd0f1338eea0e251a3d130ffe86c43ca434f7309fd20aa3` | case number / parties | CIVIL APPEAL NO ____ OF 2026 (Arising out of Diary No(s). 27246/2023); UNION OF INDIA & ORS. v BALAKRISHNAN MULLIKOTE (EX HAV [service number masked]) | Confirm the lead appeal number is blank and the cause title. Do not transcribe the service number. |
| C9-HV-MULLIKOTE-03 | 1 | `4846bbf0df2bb5fb1fd0f1338eea0e251a3d130ffe86c43ca434f7309fd20aa3` | signature appearance | 'Digitally signed by KAVITA PAHUJA / Date: 2026.04.04' (after the judgment date) | Confirm the visible signing date; is any correction date printed anywhere on p.1? |
| C9-HV-MULLIKOTE-04 | 4 | `11bad34f102460c10db2e16a07faa909088d3a33109cdfb2f505ff4f2811295f` | author / numbering (version 1) | J U D G M E N T; MANMOHAN, J.; paragraphs 1, 2, 3 then 4; questions lettered A and B | Confirm author and numbering in the first version. |
| C9-HV-MULLIKOTE-05 | 31 | `4bb6ef6e5a21a6b35efa32944d61c904eea1e18343eeb67c29cdcadf37fac941` | end of version 1 | Para 51 conclusion; [MANOJ MISRA,J] [MANMOHAN,J]; New Delhi; March 24, 2026 | Confirm that a complete judgment ends here (p.31 of 62). |
| C9-HV-MULLIKOTE-06 | 32 | `0a41a1199d428066c32d7a38d0058d96d723c880ef9b1701ccc3fa54718da869` | start of version 2 | Second cover: REPORTABLE; no CORRECTED marking, no neutral citation, no QR or signature appearance; service number differs from p.1 (one digit fewer) [service number masked] | DISCREPANCY Q-MULLIKOTE-VERSION: confirm a second cover begins here and compare the service number with p.1 by eye (record only SAME / DIFFERENT). |
| C9-HV-MULLIKOTE-07 | 35 | `e0e2b8b1934aa4d2f3839c5c7ebf10ae926c5722ddd270bbc328d2828e0e352a` | numbering (version 2) | J U D G M E N T; MANMOHAN, J.; paragraphs 4, 5, 6 then 52; questions lettered C and D | Confirm the second version continues numbering (4-6, 52-...) and re-letters the questions. |
| C9-HV-MULLIKOTE-08 | 62 | `cc389e1d7382e1886ba92663658e4c52a6e872e59030d301c8b8cb706cb3132c` | end of version 2 | Para 99 conclusion; same bench; New Delhi; March 24, 2026 | Confirm the same conclusion numbered 99. Which version is the corrected judgment? Any anchor must name pp.1-31. |

**Discrepancy questions**
- Q-MULLIKOTE-VERSION: pp.1-31 (CORRECTED, paras 1-51, questions A/B) and pp.32-62 (unmarked, paras 4-6 then 52-99, questions C/D, service number differs). Which is the corrected judgment? Is a correction date printed anywhere?
- Signed 2026-04-04, after the judgment date 2026-03-24. Lead appeal number blank. Any anchor must name pp.1-31.

| Reviewer name | Date | CONFIRMED / NOT CONFIRMED (copy as a whole) | Notes |
| --- | --- | --- | --- |
|  |  |  |  |

## Lt Col Prithi Pal Singh Bedi v Union of India (1982), baseline anchor

- Copy: `C5-SRC-J-SC-1982-PPS-BEDI~C1`; role: CONTEXT_FOR_P-D3 (optional; no approval sought); case record: DCLR-SC-1982-001; anchor effect if approved alone: already anchored at version 0
- Re-hash: `downloads/citation-codes/ppsbedi_judis9884.pdf` must give `211dbaf4e20371cc476d09c158e41b976786d57f67336ff6fc802170178b3cca` (38 pages)

- PDF pages to open: 1, 7, 38

| Item | Page | Render sha256 | Element | AI proposal (not human-confirmed) | Question |
| --- | --- | --- | --- | --- | --- |
| C9-HV-PPS_BEDI-01 | 1 | `50ffbe69a65737f64316fdf7eebf81585e784382e31dd9db6cf6f2c2c5bfb97a` | context: JUDIS rendition profile | JUDIS header 'Page 1 of 38'; PETITIONER: LT. COL. PRITHI PAL SINGH BEDI ETC. v UNION OF INDIA & OTHERS; DATE OF JUDGMENT25/08/1982; BENCH field repeats DESAI, D.A.; CITATION 1982 AIR 1413, 1983 SCR (1) 393, 1982 SCC (3) 140; CITATOR INFO; ACT; HEADNOTE | Context for P-D3: same rendition type as Ranjit/S N Mukherjee/Navjot? |
| C9-HV-PPS_BEDI-02 | 7 | `6fd04e35594baf94aea39a44de7b8f5a3548b60a699e8846fa13fe705c4b2dd8` | context: end of headnote | Headnote ends with report pinpoints [441 F-G; 442 B]; 'JUDGMENT:' Writ Petition Nos. 4903 of 1981, 1513 of 1979 and 5930 of 1980; author DESAI, J. | Context: pp.1-7 up to 'JUDGMENT:' are database/headnote matter. |
| C9-HV-PPS_BEDI-03 | 38 | `17a2d5bbcc3f47a887c43fd81eb9e8e3fd3061616c62ebf9d551cf765443a600` | context: end of text | Ends 'P.B.R. Petitions dismissed.' then report page 445; no signature or date block | Context: confirm no signature or date block. |

**Discrepancy questions**
- Context only (baseline anchor, no approval sought): confirms the four JUDIS renditions share one profile (P-D3).

| Reviewer name | Date | CONFIRMED / NOT CONFIRMED (copy as a whole) | Notes |
| --- | --- | --- | --- |
|  |  |  |  |

## After review
- A completed sheet is evidence for policy B2 only if the reviewer is a named person (not an AI agent) and the pages were re-hashed.
- Recording a CONFIRMED check in the AUTH-LEDGER evidence, and any approval, are separate owner steps (rule-version and ledger PRs). This pack does neither.
