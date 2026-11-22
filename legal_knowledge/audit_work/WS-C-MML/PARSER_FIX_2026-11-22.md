# Parser fix 2026-11-22 (PR #20 review: three Codex findings, verified by coordinator)

Scope: `scripts/kb_citations.py` and the artifacts derived from it. This is coverage and locator work only. The originals are read-only and no full MML text is committed.

## Fixes
1. **Letter suffixes.**
   - `15-A` and `13-A` are now read as 15A and 13A.
   - Suffixed range endpoints are kept: `167–169A` gives 167, 168, 169 and 169A.
2. **List continuation.**
   - Bare sub-clause continuations are allowed, e.g. `rr23(1),(3),24` gives 23 and 24.
   - Qualifier words after an item are allowed (proviso, note, explanation, exception, onwards, as applicable). So `rr 177-182, 22(1) proviso, 23` now keeps 23, and `180 exception, 181(a)` keeps 181.
3. **Uncoded short case titles.**
   - New `case_name_lexicon.csv` (71 keys, sha fc3055d4…), built by `scripts/build_case_lexicon.py`. Sources: the 53 curated case titles, plus WS-B `identity_resolution.csv` read via `git show origin/claude/ws-b-judgments` @ 97de40b3 (copy sha dcb9c628…).
   - `¶` now counts as a case-citation signal.
   - A case name that no citation code in the record covers raises `CASE_NAME_WITHOUT_CODE` and counts as unresolved. **A record is never FULL while any case reference is unresolved.**

Regression check: `scripts/test_kb_citations.py` (stdlib; the `tests/` folder is under the WS-D lease). It asserts:
- every case above;
- three unchanged controls (KB-003, EV-001, CIV-006);
- that no record is FULL while carrying an unresolved case flag;
- that HCE-029 appears in the r.23 crosswalk.

## Coverage state, before → after (denominator 658)
| State | Before | After |
| --- | ---: | ---: |
| FULL | 379 | 370 |
| PARTIAL | 131 | 140 |
| SOURCE_GAP | 56 | 56 |
| UNRESOLVED | 14 | 15 |
| NO_CITATION | 78 | 77 |

**Flag counts:**
- Records with a broken or unresolved flag: 63 → 74.
- PLAIN_CASE_CITATION_UNRESOLVED: 13 → 3. Ten of these are now named through the lexicon as CASE_NAME_WITHOUT_CODE.
- CASE_NAME_WITHOUT_CODE: new flag, 21 records.

**Unchanged:** Army Act pinpoint records (175), Army Rules pinpoint records (169), statutory anchor (456), pinpoint present (531), MML crosswalk link (293).

## Changed records (35)
- **State FULL → PARTIAL (10):** SC02, SC13, CM-009, CM-010, CM-015, CM-SC-02, CM-SC-03, CM-SC-05, V8-JD-05, plus V7-WF-08 (flag added; state unchanged). Cause: uncoded case names (Virendra Kumar, P S Gill, Vishav Priya Singh, Randhir Singh, Prithi Pal Singh Bedi, Ram Sarup, Parashotam Dass).
- **State NO_CITATION → UNRESOLVED (1):** ADM-013 (Kuldeep Yadav).
- **Flag renamed PLAIN_CASE → CASE_NAME_WITHOUT_CODE (10):** ADM-014, ADM-015, ADM-016, ADM-018, ADM-026, ADM-031, ADM-SC-09, ADM-SC-10, ADM-SC-12, ADM-SC-14.
- **Provisions corrected (10):**
  - ADM-007: r.15 → r.15A
  - ADM-008: r.13 → r.13A
  - ADM-019: r.15 → r.15A
  - CM-038 and CM-CL-11: + s.169A
  - SC03: + r.24
  - HCE-029: + r.23
  - COI-032: + r.181
- **Case pattern now detected, state unchanged (coded):** PEN-023, PEN-044, AFT-013, AFT-035, AFT-036, V7-CL-10.

## Regenerated artifacts
- `kb658_source_coverage_inventory.csv` and the summary (new column `case_names_matched`).
- `mml_provision_crosswalk.csv`: 847 → 858 rows. 219 provisions, up from 216 (adds r.13A, r.15A, s.169A). HCE-029 is now in the r.23 rows, SC03 in r.24, COI-032 in r.181. ADM-007, ADM-008 and ADM-019 moved from r.13/r.15 to r.13A/r.15A. The `xw_id` values are renumbered.
- `calibration_sample_ranked.csv`: still 46 records. SC13 added, AFT-005 dropped.
- `procedure_crosswalk.csv`: 198 → 199 distinct KB records. PX-03 goes 29 → 30 (HCE-029); PX-19 goes 18 → 19.
- `crosswalk_locator_verification.csv`: link columns refreshed by `scripts/refresh_lv_links.py` for the new `xw_id`s. Image-check columns unchanged.
- Hand-maintained lists:
  - PG-06 (r.15) and CC-08: ADM-007 and ADM-019 removed.
  - CC-11 now lists all 24 records with an unresolved case reference.
  - New FID-14 (r.13A(2) DOC omission; DOC side text-only) from the screen of the three new provisions.
- `provision_index.csv` and `mml1_para_index.csv` are not affected (they are built from MML text, not the KB parser).

Regeneration order: `build_case_lexicon.py <ws-b csv>` → `build_crosswalk.py` → `build_kb658_inventory.py` → `build_calibration_sample.py` → `build_procedure_crosswalk.py <pcl>` → `refresh_lv_links.py` → `test_kb_citations.py`.
