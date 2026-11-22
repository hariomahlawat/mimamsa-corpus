# Current figures and superseded figures (2026-11-22)

**Coverage and searchability are not legal correctness.** FULL means only that every parsed citation resolves to a held source with a pinpoint.

## Current
| Measure | Value | Source |
| --- | --- | --- |
| WS-C coverage (denominator 658) | FULL 370, PARTIAL 140, SOURCE_GAP 56, UNRESOLVED 15, NO_CITATION 77 | WS-C @ba3d370e, `kb658_source_coverage_inventory.csv` |
| WS-D plain-text records with every statute instrument searchable | 168/178 | WS-D @dcd877b4, `coverage_scorecard.json` |
| WS-D cited Army Act sections present in the corpus | 446/446 | same |
| WS-D coded records with every code searchable | 279/389 | same |
| Citation codes | 72/87 confirmed, 3 inferred, 12 unresolved | WS-D register test |
| WS-C vs WS-D reconciliation | **556/658 agree; 102 differences, all explained by definitional rules** | WS-D `coverage_reconciliation.meta.json` |
| Provenance checker | **0 active new violations**; 2 known historical items (PILOT-01 PIC-08 and PIC-09, reviewer reports without renders, superseded for wording by rendered checks PIC-01/03/04/29 and WSC-PIC-08..10; see `pic_supersession_2026-11-22.csv`) | `check_provenance.py` on #22 |

## Superseded (kept for the record; not to be cited as current)
| Figure | Why superseded |
| --- | --- |
| Reconciliation 562/658 (96 differences) | Built from the WS-C inventory before the parser fix (ba3d370e) |
| Reconciliation 554/658 (104 differences) | Built before WS-D's multi-instrument fix (6a191870) |
| WS-C FULL 379 / PARTIAL 131 / UNRESOLVED 14 / NO_CITATION 78 | Parser defects (suffixes, list continuation, short case titles) |
| WS-D 169/178 plain-text; 448/448 Army Act sections | First-instrument-only parsing (ADM-JD-02 AR r14 counted as AA s14) |
| Provenance violations 21 (cycle 2), then 19, 3, 2 | 17 ACQ-02 copy_fidelity values fixed (8b436b67); WS-A PCL-BL-25 fixed (2fc75160). The current active count is 0 new; 2 historical items remain baselined |

## The five reviewed defects and their regression tests
| # | PR | Defect | Test | Fails on the original code | Passes on the fix |
| --- | --- | --- | --- | --- | --- |
| 1 | #18 | Only the first instrument per citation segment | `tests/test_legal_audit_review_fixes.py` (ADM-JD-02, V7-WF-12) | yes (coordinator re-run: 7 fail, 2 error across the WS-D set) | yes (10/10) |
| 2 | #18 | PAGE_IMAGE_READING accepted a nonexistent check ID | same file | yes | yes |
| 3 | #22 | Workstream check-ID prefixes stripped | same file | yes | yes |
| 4 | #22 | manual_supported evidence not bound to document and render | same file | yes | yes |
| 5 | #23 | India Code listing md5/size enforced on served bytes | `tests/test_verify_batch.py` | yes (real entry acq03-033-b5 rejected) | yes (7/7) |
| 6 (new) | #17 | Pinned values not enforced at fetch time | `tests/test_fetch_integrity.py` | yes (4/6 failed) | yes (6/6) |
