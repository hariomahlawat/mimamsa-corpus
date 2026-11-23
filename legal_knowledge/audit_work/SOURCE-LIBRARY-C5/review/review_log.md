# Independent review log: SOURCE-LIBRARY-C5

- Date: 2026-11-23
- Reviewer: independent subagent, read-only. No file in /home/user/c5 or any git repository was modified. All outputs are in this folder.
- Policy applied: /home/user/c5/docs/legal-audit/SOURCE_AUTHORITY_POLICY.md (v1).
- Findings: review_findings.csv has 32 rows (P1: 1, P2: 5, P3: 12, INFO: 14).

## Method

1. **R1 identity.** For all 62 HELD_* rows in registers/source_master_register.csv I took each held path, checked it exists, re-hashed it, compared it with the manifest, and extracted the p.1 text (dump2.py; full first-two-page dump in p1dump.txt).
   - For the Army Rules amendment Gazettes I located each S.R.O. in the held file (sro.py) and read the masthead number, date and Part.
   - I spot-checked printed page numbers.
   - I rendered page images for the image-only files (AR-031, CCCM, ER 2023) and wherever the text layer was doubtful (AR-006 date, S.R.O. 34).
   - For judgments I read party names and case numbers on p.1 and took the date from the last page.
2. **R2 authority.** I joined master sha256 values to CALIBRATION-02/registers/source_authentication_register.csv (13 rows), then compared holding_state, document_authority and carrier_provenance across like rows (compilations, Gazettes, judgments).
3. **R3 completeness.**
   - Page counts: pdfinfo on 12 files, plus a per-page profile (text characters and drawn-image coverage via get_image_rects).
   - Re-read the classifier in tools/build_baseline.py.
   - RA Ch.V extract: listed the paragraph headings and checked pdfinfo.
   - ER 2023 (13 MB): rendered all 35 pages as contact sheets (er_sheet0.png, er_sheet1.png) and pp.1, 19 and 20 at full size.
4. **R4 OCR.** Compared text layer with page image for three scanned Gazettes: 87578 (1961), 84713 (1963) and 1992-37 (Act 37/1992).
5. **R5 amendments.** r5.py re-derived every row of amendment_register (87) and provision_amendment_chain (154) from origin_register/origin_id, field by field. It also flagged any effective_date populated while the status is NOT_STATED or UNKNOWN. The 15+15 sample ids (seed 5) are listed in RV-24, but the whole population was checked.
6. **R6 supersession.** Read the image of 1992-37.pdf pp.1 and 3 (s.2 and s.11) and the text of p.4 (end of Act) against WS-A AA-08-s2 and AA-08-s11.
7. **R7 discovery.**
   - Sampled C5C-001, C5C-016, C5C-018, C5A-019, C5B-006 and C5B-009, and traced each to its *_requests.tsv lines.
   - Scanned all logs for binary GETs, blocked hosts and robots order.
   - Made 2 live archive.org metadata requests.
8. **R8 crosswalk.**
   - Stratified sample of 20 rows (6 EXACT, 8 PARTIAL, 6 MISSING; seed 8) checked against WS-D-QUALITY/canonical_coverage.csv and the master register.
   - Whole-population checks of status against holding_state.
   - Re-read the crosswalk logic in build_registers.py and compared amended_rules() with all Army Rules amendment records, including instrument-register hints.
9. **R9 reserved states.** Compared status fields verbatim with SOURCE-CONFLICTS-01 (C-01, U-01, C-08, C-09, U-07, U-08), CALIBRATION-02 source_conflicts_c4.csv (SC4-01) and WS-B open_inconsistencies_cycle3.csv (OI-01 to OI-13).

## Network requests (2 of the 10 allowed; metadata JSON only, no binary GET, no TLS bypass)

| utc | method | url | status/bytes |
|---|---|---|---|
| 2026-11-23T04:45:33Z | GET | https://archive.org/metadata/in.gazette.e.1950.306 | 200 / 4622 |
| 2026-11-23T04:45:36Z | GET | https://archive.org/metadata/in.gazette.central.e.2007-12-28.020 | 200 / 4868 |

The saved responses are in net/.

## Page renders made (all in this folder)
ar006_p1top.png, ar031_p1.png, sro34.png, a37_p1.png, a37_p2.png, a37_p3.png, cccm_p1.png, ra_p1.png, er_p1.png, er_p2.png, er_p19.png, er_p20.png, er_sheet0.png, er_sheet1.png

## Key results
- **P1, RV-01.** The CCCM (Adjustment of Jurisdiction) "amendment rules" file is actually a Rajya Sabha debates page (archive.org rsdebate.nic.in.313431) recording the laying of S.O. 4010 of 08-12-1986. It is not the instrument, and it does not come from India Code.
- **P2 findings:**
  - RV-02: S.R.O. 34/1963 and S.R.O. 2(E)/2018 are labelled amendment instruments although they are r.188(e) declarations.
  - RV-11: the BNSS and BSA rows give ENACTED_OR_NOTIFIED_PRIMARY authority to a held India Code compilation.
  - RV-19: the ER 2023 13 MB file is identified; GMO-2023 is absent, so the file is incomplete.
  - RV-20: the ER/GMO 2023 cover letter is wrongly recorded as not held.
  - RV-31: CM-018#r95 is EXACT_ANCHOR despite the AR-039 hint, and the amended-rule detection is incomplete.
- **Confirmed correct:** HELD_PRIMARY gating (RV-15), amendment-register derivation fidelity (RV-24), Act 37/1992 omissions and the absence of a commencement clause (RV-26), discovery provenance and logs (RV-27, RV-28), and reserved conflict states (RV-32).
