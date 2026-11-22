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

## Cycle 3 (worktree /home/user/ws-c-c3, branch claude/ws-c-cycle3, from 9b48b08e)
- C3 commit 1, task 1: `mml_edition_evidence_cycle3.csv` (29 evidence items across 8 files).
  - Each row carries a 'what would authenticate this edition' column.
  - No edition is asserted official; all stay UNVERIFIED_MANUAL.
- C3 commit 1, task 2: `mml_provision_crosswalk_v2_cycle3.csv`, a versioned file; the cycle-1 crosswalk is unchanged.
  - 436 priority rows were rendered at 110 dpi and every crop was viewed: all crosswalk rows for provisions cited by the 46 calibration records, then the procedure-crosswalk provisions.
  - Result: 434 LOCATOR_IMAGE_CHECKED + 2 LOCATOR_CORRECTED_IMAGE_CHECKED.
  - The corrections are s.2 in vol 2(AA): the index pointed to a note; the heading is at PDF p.1 / L00011.
  - The remaining 422 rows stay REQUIRES_VERIFICATION.
  - DOC rows are LibreOffice renders of native DOC text (`render_source` column).
- C3 commit 2, task 3: `procedural_contradictions_cycle3.csv` (20 rows, proposals for independent review).
  - Each row gives the MML reading (page image + render sha; PC-12 and PC-19 are text-only), the comparator instrument and version, and the exact reviewer question.
  - Dates are kept distinct: publication, commencement as printed, effective date, status.
  - Severity: P1 = 5 (PC-02, 08, 09, 10, 11); P2 = 11; P3 = 4.
  - WSC-PIC-109 added (MML 1 Ch II para 13).
- Task 4: the parser was not touched in cycle 3; `test_kb_citations.py` re-run at every commit and passes.
- Fixed determinations unchanged: r.23(3) CONFLICTING; C-08 OPEN; C-09 PROPOSAL.
- Cycle-3 review (PR #27):
  - Verified all 436 checked rows of the v2 crosswalk: file SHA equals the manifest; render source is correct; every render hash re-computed from its PNG matches.
  - Corrected PC-11, PC-12, PC-13 and PC-19 comparator commencement/effective dates to the chain at 9b48b08e (AR-028, AR-031, AR-034 and AR-035: in force on publication).
  - Crosswalk and procedure crosswalk were already current; regenerating them gives byte-identical output.

## Cycle 3 reconciliation (branch claude/ws-c-cycle3-reconcile, base 2a66cd04 = integration #29 + PR #28)
PR #28 updated ARMY-RULES-CHAIN-01: AR-010, AR-011 and AR-025 have no commencement clause printed (NOT_STATED_PENDING_ADVICE); AR-024 has a separate field `retrospective_deemed_effect_from`.

**Regenerated files** (a second run gives byte-identical output):
- `procedure_crosswalk.csv`, from the in-tree WS-A `provision_change_log.csv`:
  - PX-06 (r.192) and PX-20 (r.194) now carry the new values;
  - PX-19 carries AR-024's effective date 1988-09-17;
  - new separate column `retrospective_deemed_effect_from` (r.16A:AR-024:1979-06-04), never merged into effective dates.
- `mml_provision_crosswalk.csv`: XW-C-0448..0451 (r.13) commencement text updated.
- `mml_provision_crosswalk_v2_cycle3.csv`: rebuilt from the crosswalk.
- `input_manifest.json`: now also lists the in-tree WS-A change log and `page_image_checks_chain.csv`.

**Hand-maintained rows corrected:**
- PG-02 and PC-16 (S.R.O. 332/1989): commencement and effective-date status set per AR-025; PIC-39 cited (render 260e5119…).

**Coordinator decision applied:** the stale gap-register date rows PG-01, PG-04, PG-07, PG-08, PG-09 and PG-14 (AR-006, AR-023, AR-029, AR-034, AR-035) now carry the current ARMY-RULES-CHAIN-01 publication date, commencement as printed, effective date and status.
- Two columns were added to the gap register: `chain_effective_date` and `chain_date_source`, which cites the chain row and its PIC or evidence locator.
- AR-006 and AR-023 stay NOT_STATED_PENDING_ADVICE (AQ-05), as recorded in the chain.
- The PG-02 source is also recorded.

**Pre-existing unittest failure (committed by coordinator decision):** `python3 -m unittest discover -s tests -p 'test_legal_audit_*.py'` exits 1 with two failures in `test_legal_audit_versioned_edges`:
- `test_inputs_pinned_and_current`: "input version_register changed - regenerate versioned edges: run scripts/build_versioned_edges.py";
- `test_regeneration_is_byte_identical`.

It reproduces identically at the untouched base 2a66cd04 (caused by PR #28). WS-D is regenerating those outputs on its reconcile branch. All other gates passed: PILOT-01 and R23-VERIFY-01 strict, `check_registers.py`, `check_csv.py`, `check_provenance.py` (new=0), records_658 sha, `test_kb_citations.py`.

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
