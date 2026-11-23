# Integration record: cycle 3, final (branch `claude/integration-cycle3`, 2026-11-23)

**DATABASE ONLY. Technical integration. No legal determination; no legal-advisor or JAG approval claimed. Not to be merged into staging without the owner's explicit approval.**

**Base:** `legal-knowledge/v2.5-staging` @ b973e578 (tree 088e61eb). Normal `--no-ff` merges only. No history rewritten; no force-push; no conflicts.

## Merge sequence on this branch
| Merge commit | Merged branch @ head | Origin PR | Content |
| --- | --- | --- | --- |
| 727ef881 | `claude/ws-a-cycle3` @ bfc9765a | #24 | s.137 completeness (A.L.O. 1956, S.O. 3912(E)/2019) and completeness check |
| 2dd38736 | `claude/ws-b-cycle3` @ 6bdd9eb2 | #26 | PDF-page off-by-one; HEAD status/content-type parsing |
| e11503db | `claude/ws-c-cycle3` @ e9729c66 | #27 | PC-11/12/13/19 aligned with the chain |
| f3568981 | `claude/ws-d-cycle3` @ 4a17359e | #25 | provision lists; amendment-event identity; coded-record section checks |
| a5349b7f | `claude/ws-a-cycle3` @ 2a09a14a | #24 | review conditions (fixture self-test, token-boundary C1, OQ-A-13) |
| 474a5e44 | `claude/ws-d-cycle3` @ 1f47b7be | #25 | returned defect: AA-04 amending-Act s.3 (5 false edges removed) |
| **2a66cd04** | `claude/baseline-register-fix` @ **c166dac3** | **#28** | baseline commencement corrections; `retrospective_deemed_effect_from`; short titles as printed |
| 0b48c070 | `claude/ws-a-cycle3-reconcile` @ 18ae1078 | – | change log corrected in place; AA-C3-01 → ACQ03-021; ACQ03-029 candidate; AA-C3-05 |
| 8b3bf77c | `claude/ws-b-cycle3-reconcile` @ e4191114 | – | no commercial holder; 55-row queue (one per unresolved identity); 13 OPEN inconsistencies |
| ce269c0d | `claude/ws-c-cycle3-reconcile` @ ac351546 | – | PX-06/PX-19/PX-20; PG-01/02/04/07/08/09/14; PC-16; manifest |
| 83caacc2 | `claude/ws-d-cycle3-reconcile` @ a824686b | – | empty-section-index fix (PR #29 P2); edges after #28; addendum input; r.2 model |

The reconcile branches were cut from 2a66cd04 (this branch plus #28), so their outputs are computed on the reconciled inputs. WS-C and WS-D each merged the WS-A reconcile branch before regenerating. Merge commit 4c445df7 inside the WS-D reconcile branch carries the author identity `sim <sim@local>`, not the repository's usual identity. WS-D's hand-off said it had been amended; it had not. Its parents (7e2e1baa, 18ae1078) and content are correct, and it was left unrewritten.

**Redundancy:** this branch contains every commit of #24, #25, #26, #27 and #28. Merging it makes those five PRs redundant, so they can be closed as merged-through-#29 rather than merged separately. #30 is stacked on this branch.

## Defects fixed (test-first; each failure reproduced on the pre-fix code by the coordinator and the independent reviewer)
| Finding | Fix | Before → after |
| --- | --- | --- |
| #29 P2: an empty or missing section index rated KB-003 source_searchable=ALL | WS-D 7e2e1baa | `test_legal_audit_section_evidence.py`: 5 of 7 fail on 2a66cd04 → 7/7 pass |
| #29 P2: AA-04 "(s.3 and Second Schedule)" produced false Army Act s.3 edges | WS-D 2c633b04 | 5 false edges → 0 |
| #30 P2: authentication queue omitted unresolved judgments from identity_resolution.csv | planning a8e81e38, c57af76d | 20 missing (INDER_JIT, CHANDRA_KUMAR, HARJEET, PANDAPPA, …) → 0; planning test 5 fail + 2 errors on 983a8e82 → 9/9 |
| r.2 / r.16A deemed date stored in `effective_date` (WS-A change log) | WS-A 18ae1078; WS-D aef02e0e | CONFLICTING_EVIDENCE → one event: commencement 1988-09-17 + retrospective_deemed_effect_from 1979-06-04 (AQ-06) |
| Commercial database recorded as a holder (PQ-C3-32) | WS-B e4191114 | `check_ws_b.py` exit 1 on 2a66cd04 → 0 |
| Short titles as printed (S.R.O. 116 and 215 of 1965) | #28 c166dac3 | `test_legal_audit_short_title_as_printed.py` failed on AR-010 → pass |

## Figures (technical measures, not legal correctness)
| Measure | Before | After |
| --- | --- | --- |
| Canonical coverage: source searchable (all / partly / none / n/a) | 473 / 0 / 0 / 185 | 280 / 105 / 88 / 185 |
| ANCHORED_FULL | 362 (provisional) | **187** |
| Records flagged PROVISION_FILES_ABSENT | – | 193 (all from absent rule-level files: Army Rules 454 references / 157 records; AFT Procedure Rules 67 / 36; AFT Amendment Procedure Rules 11 / 9; no Act section is missing) |
| Instrument-level searchable (informational) | 473 | 473 |
| Versioned edges | 471 | **391** (375 after the AA-04 fix; +16 from the WS-A addendum input after #28) |
| Amendment events | 118 | 123 (29 group duplicate evidence; 9 from the WS-A addendum) |
| Edges with a stated commencement / flagged EFFECTIVE_DATE_UNSTATED | 177 / 198 | 177 / 214 |
| Zero-length or reversed intervals; conflicting-commencement events | 0; 1 (r.2) | 0; 0 |
| WS-B acquisition queue | 32 | 55 (one per unresolved identity; all NOT_APPROVED, not downloaded) |
| Audit tests | 202 | 244 |

**ANCHORED_FULL 362 → 187.** The independent reviewer recomputed this from `canonical_coverage.csv`. All 175 records that lost the status cite a rule, and the crawler corpus has no rule-level files for any Rules document. This is an owner decision point: either rule-level citations stay "absent", the current conservative rule, or rule-level splitting is added to the crawler pipeline in a later phase.

## Validation on 83caacc2 (exit codes read directly, no pipes)
All of these exit 0:
- schema check;
- 244 audit unittests;
- strict validation of PILOT-01 and R23-VERIFY-01;
- `build_code_inventory`, `check_registers`, `check_csv`, `check_provenance` (new=0);
- `relation_graph --no-write` and `hash_reproduction`;
- the WS-D `--check` for versioned edges, canonical coverage and identity map (all MATCH, each run twice);
- the WS-A completeness self-test (9/9), `check_ws_b`, `check_cycle3_fixes` and `test_kb_citations`;
- HF guard tests.

Byte-identical regeneration was confirmed for:
- WS-C `build_procedure_crosswalk <WS-A change log>`, `build_crosswalk` and `build_input_manifest <scratchpad>`;
- the calibration package.

Originals: records_658 9a8f0d193065762ffa987116dc761bcb734008d2a87a946f5591741f5befcfc1; cases_53 8b8d53cd1434f7c1c6eaebe77f1fe295fb8b81b755e93276999b4b40b3c8f89a; unchanged.

The HF workflow `sync-legal-knowledge-hf.yml` is unchanged. Its upload job runs only on `workflow_dispatch` with the phrase `I-APPROVE-CORPUS-UPLOAD`, so an ordinary push cannot start an upload.

### Output SHA-256
| File | SHA-256 |
| --- | --- |
| WS-D canonical_coverage.csv / .json / .md | 980ea956… / 71308586… / 77e78781… |
| WS-D relation_graph_versioned_edges.csv / _report.md / _summary.json | be32949f… / 284fc1dd… / 6b0d1866… |
| WS-C procedure_crosswalk.csv / mml_provision_crosswalk.csv / input_manifest.json | aff38095… / 70ca124b… / f5d9891e… |
| WS-C procedure_gap_conflict_register.csv / procedural_contradictions_cycle3.csv | 8faf871a… / 8df73433… |
| WS-B pending_acquisition_cycle3.csv | b3b02c59… |
| WS-A provision_change_log.csv | b61625ca… |
| ARMY-RULES-CHAIN-01 instrument register / chronology / version seed / page-image checks | 3ea14048… / 4bb18af8… / 595532f1… / 8699c9fe… |
| CALIBRATION-01 calibration_package.csv | 084937fa… |

## Independent review (fresh reviewer, read-only; author of none of the corrections)
Result: **no P1 or P2 finding.**
- ACCEPT: items 1 (coverage), 4 (baseline register), 6 (WS-B), 7 (WS-C), 8 (whole-diff invariants) and 9 (#30).
- ACCEPT WITH CONDITIONS: items 2 (AA-04), 3 (versioned edges) and 5 (WS-A).

The conditions are P3 and recorded below as known limitations.

## Known limitations (P3, recorded; none produces a false date or a false edge today)
1. **`expand_provisions` (WS-D):**
   - A list continued after a sub-clause loses its later numbers. "ss.137(3),(4), 151, 174" (AA-C3-02) yields s.137 only, so the amendment-event count understates; no KB record cites s.151 or s.174.
   - Amending-Act reference forms absent from the current data are not stripped: "ss.2 and 3 of Act …", "Act 56 of 1974, s.3", and Roman-numeral Acts.
2. **Predecessor intervals (WS-D):** the S.R.O. 188/1979 events for r.2 and r.16A end at 1988-09-17 with no AQ-06 flag, although S.R.O. 216/1988 has deemed effect from 1979-06-04. No current edge is affected.
3. **Conservative baseline rows (WS-A):** some rows still say NOT_DETERMINED with an empty date where the chain records a stated commencement: PCL-BL-01 and BL-16 (S.R.O. 188/1979), BL-14 and BL-21 (AR-034), BL-22 (AR-035), BL-36 (AR-031). These predate this diff and are outside the #28 instruments.
4. **PIC-37 note:** `observed_on_image` keeps its check-time remark that the register read "First Amendment". The register is corrected; the text is historical, and the file is a pinned WS-C input.

## Preserved (unchanged)
- r.23(3) CONFLICTING;
- r.193 C-08 OPEN;
- r.194 C-09 PROPOSAL;
- r.15, r.187(1) and s.129 OPEN.

Advisor questions AQ-05 (silent instruments) and AQ-06 (retrospective effect) are reserved. OQ-A-13 (the sections Act 19/1955 amended) is open. The 13 WS-B source inconsistencies are OPEN.
