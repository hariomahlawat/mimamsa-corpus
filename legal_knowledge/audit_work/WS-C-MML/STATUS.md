# WS-C-MML status (issue #13)

**Research proposal only. Nothing here is legal-advisor adjudicated or JAG validated.**
Fixed determinations are unchanged: r.23(3) CONFLICTING; r.193 = C-08 OPEN; r.194 = C-09 PROPOSAL.

## Done
All eight deliverables are present. See README.md for counts, denominators and evidence levels.
1. Commit 1 delivered:
   - input manifest (8/8 originals equal the manifest);
   - edition status for the 8 files;
   - WSC-PIC-01..13, including the coordinator task: MML 2 p.227 r.193/r.194 image check;
   - provision index;
   - MML 1 paragraph index;
   - crosswalk (847 rows).
2. Commit 2 delivered the 658 source-coverage inventory, its script and the summary.
3. Commit 3 delivered:
   - the gap/conflict register (17 rows);
   - candidate corrections (14);
   - WSC-PIC-14..28.
4. Commit 4 delivered:
   - the calibration sample (46 records, selection only);
   - the full README;
   - a refreshed input manifest.

## Cycle 2 (started after coordinator merge a4c68cf2)
- C2 commit 1:
  - `doc_pdf_fidelity_register.csv` (13 rows; FID-01..11 image-checked, FID-12/13 text screen only);
  - `doc_pdf_screen_summary.json`;
  - `scripts/doc_pdf_diff.py`;
  - `wsa_itemisation_crosscheck.csv` (27 rows vs WS-A PCL @ origin/claude/ws-a-statutory 74530be9);
  - WSC-PIC-29..53.
- Key findings, FOR INDEPENDENT COORDINATOR CHECK:
  - FID-01: vol 2(AA) DOC and PDF omit 'not' in the s.41(2) second limb;
  - FID-02: vol 2(AA) omits 'or such other officer' in the s.85 proviso;
  - FID-03: MML 2 s.129 reads 'any person approved' where the DOC and India Code read 'an officer approved';
  - FID-05/09: the AR DOCs drop 'or' in r.22(3) and read 'or before' for 'and before' in r.58(1)(a)(ii);
  - FID-06/07/08/11: the AR DOCs do not apply the 1993 changes to r.36, r.37(4), r.26(3) and r.186;
  - XC-03: WS-A does not support MML's 17(E) note for r.15.
- C2 commit 2:
  - `crosswalk_locator_verification.csv` (47 MML 2 locators image-checked; 8 time/number clauses);
  - WSC-PIC-54..108;
  - `procedure_crosswalk.csv` (20 steps, 198 KB records);
  - CC-15..19;
  - OQ-C-09/10;
  - README cycle-2 section;
  - input manifest adds the WS-A PCL copy.
- Requests:
  - WS-A: s.129 'any person' vs 'an officer' (CC-17, OQ-C-09); source of the r.15 words (CC-19).

## Review fix 2026-11-22 (PR #20)
Parser fix for letter suffixes, list continuation and uncoded case names. Details in `PARSER_FIX_2026-11-22.md`.
- Coverage states before → after: FULL 379 → 370; PARTIAL 131 → 140; UNRESOLVED 14 → 15; NO_CITATION 78 → 77; SOURCE_GAP unchanged at 56.
- All dependent artifacts regenerated; `scripts/test_kb_citations.py` passes.

## Next (if continued)
- Image-check the crosswalk locators that the advisor selects. Every crosswalk locator is text-layer only (REQUIRES_VERIFICATION).
- DOC-vs-PDF comparison for vol 2(AA) and vol 3 beyond the pilot samples.
- Itemise MML vol 3 by instrument, linked to KB records that cite those instruments.

## Blockers
None hard. The owner is needed for:
- OQ-C-03: cover pages;
- OQ-C-04: edition authentication;
- OQ-C-07: handling restrictions.

## Requests to other workstreams (route via coordinator)
- **WS-A.** Itemise S.R.O. 17(E)/1993 for the rules that MML 2 notes but the AR chain does not list. These notes are leads only:
  - r.13A(3), r.14(4)-(5), r.15, r.16A, r.16B(1);
  - r.145, r.164, r.168(2), r.186(1);
  - r.193 (C-08).

  Also search for "SRO 1 dated 12 March 1964" (r.187(1)). See CC-03, CC-04, OQ-C-06.
- **WS-B.** Find the official copy for V9-JD-03 (CC-09) and the plain-text case identities (CC-11).
- **WS-D.** Placeholder and plain-text citation lists (CC-10, CC-11). Relation type for "manual_supported" (CC-13).
