# Cycle 8, Workstream C: Supreme Court primary-copy verification (findings)

**Status.** These are evidence findings only.
- No approval is given, and no ledger entry, decision record or activation is created.
- Nothing here states legal status or precedential value.
- Snapshot `c8base` (commit bb1f0971) was not modified (`git status` empty).
- Page readings were made by an AI agent (Claude Opus 5.5 subagent) and have not been confirmed by a person.
- All held files were re-hashed before use: 10 of 10 MATCH. That covers the 8 candidates plus Rajbir C2 and C3.
- Revised after independent review 5212a95b; the changes are listed in `../review/DISPOSITIONS_5212a95b.md`.

## 1. Identities read from the documents
| Copy | Printed identity (C8 reading) | Result | Main discrepancies |
| --- | --- | --- | --- |
| Ranjit Thakur `ed7cf31f` (9 pp.) | Ranjit Thakur v UOI & Ors; CA 2630/1987; 15/10/1987; Venkatachaliah & A.P. Sen JJ | CONFIRMED | JUDIS rendition with HEADNOTE on pp.1-3, which C6-01 did not record. Editorial note: "point 1.3 ... subject to the subsequent order dated 10.8.88". No signature or date block |
| S N Mukherjee `eb442080` (23 pp.) | S.N. Mukherjee v UOI; CA 417/1984; 28/08/1990; 5 judges | CONFIRMED | cases_53 case_number empty. HEADNOTE pp.1-3. Conflicting cases_53 source_note ("training institute transcription") against an sci.gov.in URL |
| Navjot Sandhu `3b753548` (107 pp.) | State (NCT of Delhi) v Navjot Sandhu @ Afsan Guru; Crl.A. 373-375/2004 with connected appeals; **04/08/2005**; Reddi & Naolekar JJ | CONFIRMED | The date and case number are absent from C6-01 identity and cases_53 (where the record is a CITATION_LEAD); the date is present in S-REVB-012. No headnote or citator anywhere in the text layer |
| Dharamvir Singh `3056712c` (36 pp.) | Dharamvir Singh v UOI & Ors; CA 4949/2013; July 2, 2013; Patnaik & Mukhopadhaya JJ; REPORTABLE | CONFIRMED | (2013) 7 SCC 316 is not printed, so it cannot be confirmed from this copy. copy_structure producer field is garbled (decoded: LibreOffice 3.6 + iText 2.1.7) |
| Rajbir Singh C1 `970b9680` (20 pp.) | UOI & Anr v Rajbir Singh; CA 2904/2011 with connected appeals; February 13, 2015; T.S. Thakur & Banumathi JJ; REPORTABLE | CONFIRMED | The C6-01 identity string for C1 cites C2/C3 identifiers ("rop_275403; bosir copy"). C1 and C2 paginate differently |
| N S Yadav `3c50cdb7` (15 pp.) | **Ex Cfn Narsingh Yadav** v UOI & Ors; CA 7672/2019 (Diary 27850/2017); October 03, 2019; L. Nageswara Rao & Hemant Gupta JJ | CONFIRMED | The corpus label "N S Yadav" is not supported by the document. Date missing from identity. Not in cases_53 |
| Girish Kumar `4f7ea3a4` (17 pp.) | UOI v Sgt Girish Kumar & Ors; CA 6820-6824/2018 with connected appeals; **2026 INSC 149**; February 12, 2026; P.S. Narasimha & Alok Aradhe JJ | CONFIRMED | cases_53 reporter_citation empty. Signature appearance: "Digitally signed by KAPIL TANDON 2026.02.12" (structural, not validated) |
| Mullikote `10e1954f` (62 pp.) | UOI & Ors v Balakrishnan Mullikote (Ex Hav 2568912 M); CA ___/2026 arising out of Diary 27246/2023; **2026 INSC 286**; **CORRECTED**; March 24, 2026; Manoj Misra & Manmohan JJ | CONFIRMED (pp.1-31); PARTIAL (pp.32-62) | **The file holds the judgment twice.** pp.1-31 are the CORRECTED version (paras 1-51). pp.32-62 are an unmarked version (paragraphs numbered 4-6 then 52-99, for 1-3 and 4-51 of the first version; service number "256812 M"). Lead appeal number blank. Signed and created 2026-04-04, after the judgment date. Already recorded as WS-B OI-03 |

Details are in `sc_copy_evidence_register.csv` (8 rows), `page_checks_sc_c8.csv` (28 rows: C8-SCPIC-01 to 28, with PNG sha256 and render settings), and `evidence/*.md`.

## 2. Classification (copy fidelity)
- **Three files are JUDIS typed-text renditions:** Ranjit, S N Mukherjee and Navjot.
  - Ghostscript 7.05, PDF 1.2.
  - "http://JUDIS.NIC.IN · Page X of N" header and "JUDIS" watermark.
  - Database field labels; no signature block.
  - The 1987 and 1990 files also carry SCR-style headnotes and inline report page numbers that run without a gap (513-525; 45-76), which fits text keyed from a law report.
  - Whether these are court-issued copies or court-system renditions is **owner decision P-D3**. It is set out, not decided, in `JUDIS_CLASSIFICATION_ANALYSIS.md`.
- **Two files come from /jonew/judis/ paths but are court-layout PDFs:** Dharamvir and Rajbir C1. Each has a watermark and a second page series overlaid. "JUDIS" is therefore a hosting system, not one format.
- **Three are current-format court PDFs:** N S Yadav, Girish and Mullikote. Girish and Mullikote carry embedded signature ranges that span the file. That fact is structural only; no cryptographic validation was done.
- **Rajbir copies:**
  - C2 `c6ec489d` (21 pp.) is the judgment on pp.1-18 plus the Record of Proceedings on pp.19-21. Its p.1 carries the signature appearance of Court Master Sarita Purohit, dated 2015-04-29. Its row in `AUTH-LEDGER/evidence/copy_structure.csv#C5-SRC-J-SC-2015-RAJBIR~C2` records one signature byte range [0 149839 159611 4244], YES_AFTER_PREFIX; that is a structural record, and the signature has not been validated.
  - C3 `6b495f14` (15 pp.) is a GNU-enscript plain-text rendition of C2, created in 2017. It is non-primary and must never anchor.
  - The text of C1 matches C2 pp.1-18 apart from watermark text and hyphenation.

## 3. Completeness
- "Page X of N" sequences are complete in every file that prints them: Ranjit, S N Mukherjee, Navjot and Mullikote. Document page-number sequences are complete in the others.
- The four current-format and court-layout PDFs end with signature lines and place and date: Dharamvir, Rajbir C1, N S Yadav and Girish.
- The three JUDIS renditions end with no signature or date block. Completeness against a signed original cannot be shown for them.
- Mullikote's "Page 1 of 62" covers two versions of a 31-page judgment.

## 4. Exact-anchor simulation
This is a simulation in a temporary directory, not an approval. Details are in `EXACT_ANCHOR_FINDINGS.md` and `exact_anchor_simulation.json`.
- Version 0 has 6 EXACT_ANCHOR cases, byte-identical to the frozen C5 registers.
- Each of the 8 entries alone passes rule 1. Seven of them add exactly one case row each; N S Yadav adds none.
- All 8 together give **13**. **The "6 → 13" claim reproduces.**
- Seven crosswalk case rows change and no KB row changes:
  - DCLR-SC-1987-R01
  - DCLR-SC-1990-N02
  - DCLR-SC-2005-L01
  - DCLR-SC-2013-N08
  - DCLR-SC-2015-N09
  - DCLR-SC-2026-007
  - DCLR-SC-2026-N16
- For context:
  - without the 3 JUDIS renditions: 10;
  - without Navjot and Mullikote: 11;
  - without both groups: 9.
- **Recommend keeping PARTIAL:**
  - **Navjot**, for three reasons: its classification depends on P-D3; its first-class record is SOURCE_LOCATED; and the case record is a citation lead with no date or number.
  - **Mullikote**, because the file holds two versions; any anchor must name pp.1-31.
- Ranjit and S N Mukherjee depend on P-D3.

## 5. Plan check (EVIDENCE_REVIEW_PLAN.md)
**Confirmed:**
- page counts;
- page-1 formats;
- the Navjot date gap;
- the Mullikote CORRECTED marking and blank appeal number;
- the N S Yadav diary and appeal numbers;
- three Rajbir copies;
- the joint figure of 13.

**Not stated in the plan:**
- the Mullikote duplication, which leaves R-T2-4 understated;
- the HEADNOTE in Ranjit and S N Mukherjee, which leaves R-T2-5 understated;
- the Ranjit editorial note on the 10.8.88 order;
- C6-01's merged Rajbir C1 identity string;
- C2's signature appearance (its copy_structure row, recording one signature range, YES_AFTER_PREFIX, already exists);
- the "Narsingh" name.

**Not verified by C8:** the plan's statement that the AUTH-LEDGER-01 tests cover Rajbir C1 plus the rendition.

## 6. Subsequent treatment
`subsequent_treatment_leads.csv` has 20 leads, all RESEARCH_LEAD_UNVERIFIED. Main questions:
- Ranjit: the 1988 review order (not held).
- S N Mukherjee: the later Army Rule 62(1) amendment.
- Navjot: Anvar, recorded as OVERRULED_IN_PART in WS-B, and the Evidence Act/IPC → BSA/BNS transition.
- Dharamvir and Rajbir: 1982 against 2008 Entitlement Rules and the 2023 framework. WS-B links N.C. Isaac (2026 INSC 993) as QUALIFIED_FOR_LATER_REGIME.
- Dharamvir: distinguished by Narsingh Yadav.
- Girish: the 12-10-2026 clarification (not held).
- Mullikote: OI-03 and OI-04.

No conclusion is drawn on whether any judgment is good law.

## 7. Unresolved questions
1. P-D3 (JUDIS class) and policy B (whether an agent page reading counts as a CONFIRMED check).
2. Mullikote:
   - which version is canonical;
   - the correction date;
   - whether the service number was the corrected item.
3. The Ranjit review order of 10-08-1988 needs an official copy.
4. Navjot needs a VERIFIED retrieval record; the case record needs the date and case number.
5. Corpus corrections for owners to consider (not made here):
   - S N Mukherjee case number;
   - Girish neutral citation;
   - Navjot date and number;
   - N S Yadav name;
   - Rajbir C1 identity string;
   - the Dharamvir producer encoding in copy_structure.csv.
6. Whether the /judgment/judis/ and /jonew/judis/ paths serve one resource (S N Mukherjee, Fable F-17).

## 8. Limitations
- Only page 1, the final page and a few identity-bearing pages were image-read for each copy. Other pages were examined through the text layer only: header sequences, labels, inline numbers and copy diffs.
- No digital signature was validated.
- No web retrieval was done.
- Four copies have no retrieval date in a retrieval record (C6-01 `provenance_recovery_register.csv` remaining_gaps): Ranjit Thakur, S N Mukherjee, Girish Kumar and Mullikote. This is now recorded per copy in `sc_copy_evidence_register.csv` (`retrieval_evidence_c6_01`, `limitations`) and carried into the templates.
- Page text layers are not committed. The render facts keep only hashes, page numbers and settings (`tools/render_facts.jsonl`).
- The treatment leads come from corpus records and were not researched.
- Render hashes depend on PyMuPDF version and settings, which are recorded per row.
