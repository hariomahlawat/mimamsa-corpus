# Integration record: cycle 2 (branch `claude/integration-cycle2`, 2026-11-22)

**Composition** (normal merges only, no history rewritten, no file chosen over another):
- `claude/next-stage-proposal` (PR #16), which itself merges PR #6 at 4dd1b2e1;
- WS-A `claude/ws-a-statutory` (PR #19), WS-B (PR #21), WS-C (PR #20) and WS-D (PR #18), at their pushed heads.

## Conflicts identified and how they were resolved
| # | Conflict | Type | Resolution |
| --- | --- | --- | --- |
| 1 | WS-D test `test_no_state_column_claims_approval` failed on WS-C `candidate_corrections.csv` (quoted statute text "approved of by the Judge Advocate General") | Cross-stream (test heuristic vs descriptive column) | Returned to WS-D (owner of the test). Fix 4239de20: shared detector ignores quoted text and counts only explicit approval states. Coordinator verified no weakening (ADJUDICATED, LEGALLY_VERIFIED, FORMALLY_APPROVED, JAG APPROVED and APPROVED still caught; negated and pending forms exempt). WS-C files untouched. |
| 2 | WS-D generated outputs (relation_graph_summary, coverage_reconciliation header) differ when regenerated on the integrated tree | Context-dependent output | Not nondeterminism: identical with the same arguments, except the page-image check count (29 → 144) because the integrated tree carries all workstreams' registers. Recorded; WS-D to regenerate after merge. |
| 3 | WS-C XC-03: MML attributes "or Military Secretary" in r.15 to 1993; WS-A finds no 1993 item for r.15 | Substantive disagreement between sources | **Both findings preserved.** OPEN (WS-A OQ-A-10, WS-C OQ-C-10). No source selected. |
| 4 | r.187(1) footnote "SRO 1 dated 12 March 1964" | Agreement (WS-A and WS-C both unresolved) | OPEN pending ACQ-C2-05..09 |
| 5 | Army Act s.129 wording (WS-C FID-03) | Open | Routed to WS-A (CP-06) |
| 6 | WS-C vs WS-D coverage figures | Definitional | Reconciled by WS-D (562/658 same bucket; 96 differences explained); canonical definitions are an owner decision (CP-01) |
| 7 | ACQ-01 inventory vs PR #8 config: doc_id spelling (Act 13/1975) and India Code items described by item ID | Naming only (crawler stack) | Mapping recorded in `docs/acquisition/inventory_match_2026-11-22.txt` (PR #17); frozen batches.json not edited |
| 8 | HTTPS not enforced for archive.org / India Code acquisition sources (found by a new ACQ-02 test) | Security gap (crawler stack) | `require_https: true` for `archive`, `official_instruments` (PR #8, 1b948727) and `archive_acq02` (PR #17); same code as PR #9; stack re-merged |

### Review-fix round (Codex review findings on #19 and #20, all verified by the coordinator before routing)
| # | Finding | Resolution |
| --- | --- | --- |
| 9 | #19: the WS-A README presented 25-01-1975 as the commencement date of Act 13/1975; s.4(2) is a saving ("as if") clause and the effective date is reserved for advice (OQ-A-04) | WS-A ba358fa2 corrected the README and 4 CSV summaries; effective date stays NOT_DETERMINED. Thread resolved. |
| 10 | WS-A PCL-BL-25 claimed an image check without a render (WS-D OQ-D-019); the first fix used a non-policy copy_fidelity value | WS-A 2fc75160: copy_fidelity NOT_CHECKED, REQUIRES_VERIFICATION in evidence_level; 31 rows re-pointed to real renders; provenance checker 0 new violations |
| 11 | #20: WS-C parser lost letter suffixes (r.15A, r.13A, s.169A), truncated lists (SC03 r.24, HCE-029 r.23) and missed short case titles, rating them FULL | WS-C ba3d370e fixed the parser, added a regression check and regenerated all dependent artifacts. Coverage FULL 379→370, PARTIAL 131→140, UNRESOLVED 14→15, NO_CITATION 78→77 (35 records changed). Coordinator spot-checked 8 records. Threads resolved. |
| 12 | WS-D reconciliation test failed on the integrated tree after #11 (built from the old WS-C inventory) | WS-D 1893f162 regenerated against WS-C @ba3d370e: agreement **554/658** (was 562), all 104 differences explained by definitional rules. The test now pins WS-C's input by SHA-256 and fails with an explicit "regenerate" message if it changes. |

### Final review remediation (owner instruction; five P2 threads on #18, #22, #23)
| # | Finding | Fix (tests written first, shown failing, then passing) |
| --- | --- | --- |
| 13 | #18: scorecard assessed only the first instrument per plain-text segment (ADM-JD-02 AR r14 counted as AA s14; V7-WF-12 Constitution ignored) | WS-D 6a191870: shared `instrument_locators()`; locators bind to their own instrument; an ambiguous unit is recorded, not reassigned. Regenerated scorecard, plain-text index, reconciliation. |
| 14 | #18: PAGE_IMAGE_READING proof accepted a nonexistent check ID when copy_fidelity was not PAGE_IMAGE_CHECKED | WS-D 6a191870: registered exact check ID required for PAGE_IMAGE_READING regardless of copy_fidelity |
| 15 | #22: workstream check-ID prefixes stripped (WSC-PIC-108 looked up as PIC-108) | WS-D 6a191870: full IDs matched in validate.py and check_provenance.py |
| 16 | #22: manual_supported evidence passed with another document's check and a fabricated render | WS-D 6a191870: check record must match the MML document, its manifest hash and the registered render SHA-256; the old valid fixture (PIC-01, an India Code page) was itself an instance of the defect and now uses PIC-02 (MML 2.pdf) |
| 17 | #23: India Code listing md5/size enforced as served-file expectations (host watermark) | Coordinator f5edf3ec (crawler stack): listing values informational; served SHA-256 recorded; page-image identity check; optional served-SHA-256 pin; archive.org still enforced |

Coordinator verification: WS-D regression tests on the pre-fix code fail 7 and error 2 (the 2 errors are calls to the extracted helper, which WS-D showed was a behaviour-preserving extraction with byte-identical outputs); all 10 pass on the fixed code. Regenerated figures: plain-text records with every statute instrument searchable **168/178** (was 169); Army Act sections in corpus 446/446; reconciliation WS-C vs WS-D **556/658** (was 554), all 102 differences explained.

## Validation on the integrated tree (head of this branch)
| Check | Result |
| --- | --- |
| Audit tests | 179 OK (after final remediation) |
| Schema check | pass |
| PILOT-01 and R23-VERIFY-01 strict | 0 errors |
| `build_code_inventory.py` (87 codes) | pass |
| Statutory registers (`check_registers.py`) | 47 instruments, 47 chronology events, 12 versions, 0 errors |
| CSV integrity (`check_csv.py`) | 89 files, 0 errors |
| Source provenance (`check_provenance.py`) | 3 known (PIC-08, PIC-09, PCL-BL-25), 0 new |
| Relation graph (`--corpus-ref origin/raw-data`) | 0 dangling, no ID collisions |
| Hash reproduction | pass (KB, cases, pilot manifests, MML manifest) |
| WS-B checker | pass |
| Originals SHA-256 | 658 KB `9a8f0d19…`, 53 cases `8b8d53cd…`: **unchanged** |
| Reproducibility | WS-C kb658 inventory and WS-D score, plain-text index, scorecard and v4 builder re-run: byte-identical |
| Promotion check | r.23(3) CONFLICTING (1 row), r.193 OPEN (3), r.194 OPEN (1954) and PROPOSAL (1989); no approval or verified-text state on disputed provisions; no legal-advisor or JAG approval anywhere (provenance checker) |

## Consolidated proposals
`CONSOLIDATED_PROPOSALS.csv` (CP-01..13): each proposal is traceable to its workstream files and evidence. None is applied to the originals.
