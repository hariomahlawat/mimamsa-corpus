# C12 WS-F remediation: review_wsf_statutory F-01 to F-11 → C12F-v1.1

Remediating author: C12 WS-F remediation (AI). Review: `../reviews/review_wsf_statutory.md`,
`review_wsf_statutory_findings.csv`, `review_wsf_statutory_promotions.csv`. This is documentary remediation, not legal
validation. Nothing has been applied to the KB, the C5 crosswalk or the C10 outputs; nothing was committed.

## Net result

| Evidence state | Baseline | C12F-v1 | C12F-v1.1 |
| --- | ---: | ---: | ---: |
| EXACT_ANCHOR | 42 | 105 | **99** |
| PARTIAL_MATCH | 652 | 589 | **595** |
| MISSING_EVIDENCE | 289 | 289 | **289** |

These match the reviewer's expected figures. They come from two general rules (F-01, F-02), not from item lists.
`SUMMARY.json` → `review_reconciliation`: 57/57 supported promotions still promoted; 6/6 not-supported withdrawn;
0 not-supported still promoted; 0 promotions outside the review. Transitions: only PARTIAL→EXACT (57).

Withdrawn: C10Q-CW-0031 (KB-018), C10Q-CW-0363 (ADM-006), C10Q-CW-0369 (ADM-012), C10Q-CW-0395 (ADM-032),
C10Q-CW-0402 (ADM-SC-03) [r.15, OQ-A-10/GAP-15]; C10Q-CW-0087 (COI-021) [annotation locator].

## Finding → change

| Finding | Change | Where |
| --- | --- | --- |
| **F-01 (P1)** r.15 promotions ignore OPEN OQ-A-10 | New inputs: WS-A `open_questions.csv`, `open_questions_cycle3.csv`, `gaps_register.csv` (+ cross-refs from WS-A `mml_footnote_crosscheck_cycle2.csv` and WS-C `open_questions.csv`). `open_alleged_amendments()` turns every OPEN row about an alleged/unlocated/unverified amendment that names a rule (`r.N`, via the strict `named_rules()`) into a hard blocker citing its ids. r.15 is blocked by OQ-A-10 + GAP-15 (cross-refs XC-03 DISCREPANCY, WS-C OQ-C-10); its 6 items stay PARTIAL with status `PAGES_ANCHORED_OPEN_ALLEGED_AMENDMENT_UNLOCATED` and action "locate the instrument behind OQ-A-10, GAP-15". X010 now states the r.15 issue; an OPEN_ALLEGED_AMENDMENT_NOTE proposal is generated per affected rule with citing items. Tests: `test_F01_r15_blocked_while_oq_a_10_open` (fails if any r.15 item is EXACT while OQ-A-10/GAP-15 is open), `test_F01_every_open_alleged_amendment_blocks_its_rule`, `test_F01_named_rules_ignores_instrument_numbers`. | `tools/build_c12f.py`; `tests/` |
| F-01 general sweep | **Other OPEN alleged-amendment rows naming a rule:** r.22 (GAP-02, S.R.O. 258/2002), r.23 (GAP-01 E-7/1960 chain; OQ-A-06 1967-74 hints), r.95 (GAP-13), r.187 (GAP-13, GAP-14; XC-11 DISCREPANCY), r.193 / r.194 (OQ-A-01, OQ-A-06). Each was already blocked by an instrument gap, a reserved conflict or a missing 1954 page, and r.187/193/194 have no citing items, so **no further state change**; the blockers are now recorded on those rules as well. Rows not naming a rule as `r.N` (OQ-A-08 'Rule 4-12' is the AFT rules; OQ-A-11/12, GAP-04/05 name instruments only) create no rule blocker; GAP-05's instruments already block r.13/r.168 through the instrument register. | `SUMMARY.json` → `open_alleged_amendment_blockers_F01` |
| **F-02** COI-021 cites an explanatory note | Army Rules citations whose locator is an annotation/note (`explanatory note`, `annotat`, `note`) get a blocker: no such note is printed in the 1954 Gazette (p.341 re-read: r.180 has no note; the only Explanation is r.181's) or the amending instruments. COI-021 withdrawn; COI-009 (r.177) and EV-017 (r.23) also carry the blocker but were already PARTIAL. Test `test_F02_annotation_locator_not_anchorable`. | build; tests |
| **F-03** text-layer basis for 1954 principal pages | 10 new `page_evidence_c12.csv` rows (`C12_IMAGE_CHECK_REMEDIATION`, checker "C12 WS-F remediation (AI)", 110 dpi, copy sha c5ef95a9…, render sha256, observed text): printed pp.296, 297, 301, 303, 304, 305 (rr.37-38), 306, 331, 340, 342. Each page, and continuation pages 297, 304-307, 341-343, was rendered by `tools/render_pages_c12.py` from the hash-verified held copy and read on the image by the remediation author (not copied from the review; the review's renders were not used). All 37 remaining Army Rules promotions now have `1954 page span IMAGE_CHECKED` for every cited rule (test `test_F03_promoted_army_rules_pages_image_checked`). The 10 render hashes for pp.6, 7, 11, 13, 14, 15, 16, 41, 50, 52 equal the reviewer's recorded prefixes (74fd6cc8, 2c7904b7, 9436eecf, 3b8949c5, ae12b212, f77a5aa9, 26496e2e, f47fd5a2, 66312380, 54274be6), which independently confirms the same bytes were examined. | `tools/page_evidence_c12.csv`; `tools/render_pages_c12.py` |
| **F-04** EXACT spilling to records | Matrix columns `record_level_state` (minimum over the record's items) and `exact_scope` (`CITATION_AND_RECORD` or `CITATION_LOCATOR_ONLY: …`). Promotion/anchor proposals on records below EXACT carry a RECORD SCOPE condition; judgment promotions on records with PARTIAL statutory content list those items. List: KB-005, COI-003, HCE-003, HCE-004, HCE-008, HCE-029, KB-012 (the review's seven) + COI-021 (new after F-02) + KB-025, KB-028 (Parashotam; AFT Act ss.30-32 items PARTIAL — found by the same rule, not named in the review). Test `test_F04_exact_never_propagates_to_record`. | build; `SUMMARY.json` → `record_scope_F04`; README |
| **F-05** page ranges | 1954: `text_layer_end_page()` for every indexed rule; image rows record `continues_rule` / `continues_to_pdf_page` / `continuation_probe` and must agree with the text layer (build fails otherwise). Amendments: span over all evidence rows for the rule. Result: r.179 340-341 and 1961 r.14 141-142 as requested; systematic check also found 1954 r.14 296-297, r.34 303-304, r.36 304-305, r.39 305-306, r.41 306-307, r.183 341-342, r.186 342-343 (image-checked), 1993 r.26 pp.14-15, and text-layer-only ranges for other cited rules (listed in `page_ranges_F05`). Test `test_F05_page_ranges`. | build; page evidence |
| **F-06** r.15B applicability | From the WS-A r.15 trace (item 8) and the C5 copy register (AR-034 eligible NO): `applicability_note` on every r.14/r.15/r.15A verification row and an APPLICABILITY_NOTE proposal per rule. Note only; no state change; scope after 28-12-2019 not claimed. Test `test_F06_r15b_applicability_note`. | build |
| **F-07** HCE-027 in X002/P0111 | `X002_EXCLUDE` with reason; X002 and its proposal now list 7 records (v1 P0111 is C12F-P0113 in v1.1: proposal ids are sequential and shifted because 6 promotions were withdrawn and notes added; X010 is now P0118). HCE-027 now falls in X003 (r.22-mentioning records that do not mention the 1993 proviso), which is accurate. Test `test_F07_x002_excludes_hce027`. | build |
| **F-08** provenance inconsistencies | PE-1961-141-R14: prior check is ACQ-02 `page_image_checks_acq02.csv` PIC-13 (WS-A WSA-PIC-47), not R23-VERIFY-01; PIC-30/PIC-31 confirmed in ARMY-RULES-CHAIN-01. Both 1961 pp.141-142 were also re-read in remediation. PE-1993-17 records item 25 in full. All 28 rows re-rendered with the recorded script (`render_script` column); `--verify` reproduces 28/28; v1 hashes kept in `check_note` as not reproducible. Tests `test_F08_render_hashes_reproduce`, `test_F08_prior_check_references_exist`. | page evidence; render script |
| **F-09** r.135 'or abstract' scope | VERSION_NOTE proposal for the legal adviser (two occurrences in 1954 r.135; "an abstract of his proposed evidence" survives; V9-WF-10, V9-SC-14 wording). No conclusion; the basis correction stands. Test `test_F09_r135_scope_note`. | build; README |
| **F-10** tests/--check not runnable under 3.11 | Tested interpreter pinned in README and `tools/requirements_c12f.txt` (CPython 3.13.18, PyMuPDF 2.1, pytest 9.2.0, venv path given). `require_env()` stops with a clear message under an interpreter without PyMuPDF (checked with /usr/bin/python3.11). No system packages installed. | build; README |
| F-11 (info) | Re-confirmed: frozen originals unchanged (records_658 9a8f0d19…, cases_53 8b8d53cd…), baseline 983 items, MISSING never promoted. | `--check`; tests |

## Verification run (venv, Python 3.13.18)

- `tools/build_c12f.py --check`: CHECK OK (6 outputs byte-for-byte; frozen originals verified).
- `tools/render_pages_c12.py --verify`: 28/28 rows reproduce.
- `pytest -q tests`: 27 passed (13 v1 + 14 remediation).

## Not changed / limits

- The 16 baseline EXACT items (page-anchor additions, not promotions) that rest partly on text-layer-only 1954 headings
  were outside F-03's scope; they are counted in `army_rules_exact_items_by_1954_page_basis_F03`.
- `review_wsf_statutory_promotions.csv` is read only for the reconciliation block; it never sets a state.
- Every promotion remains conditional on preserving the anchoring copies (C10 preservation risk).
