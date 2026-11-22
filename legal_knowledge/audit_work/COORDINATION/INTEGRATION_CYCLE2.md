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

## Validation on the integrated tree (head of this branch)
| Check | Result |
| --- | --- |
| Audit tests | 169 OK |
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
