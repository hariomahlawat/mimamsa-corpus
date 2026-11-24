# Confirmation review: PR #41 C9-LEGAL-EVIDENCE, delta 3b76ccd8..a61c0e57

Reviewer model: Fable 5.2 (claude-fable-5-2). Date: 2026-11-24. Review only; nothing committed or pushed.
Every builder ran with `--check`, in a disposable clone (`scratchpad/rev_heads/le`, detached at a61c0e57). The reviewed worktree `c9le` was not written to.

## Verdict: ACCEPT

FL-01 (the only condition) is fixed and verifies. FL-02, FL-04 and FL-06 are fixed as described. FL-03 is fixed for the two rows it named but its new label is also applied to a third row where it is wrong (CL-01, P3). No legal conclusion was added by the delta.

## Findings

| Id | Severity | Statement | Evidence | Requested action |
| --- | --- | --- | --- | --- |
| CL-01 | P3 | The FL-03 label is over-applied. `C9-AG-RES-SC4-01` now begins "register summary of the competing sources (not verbatim readings)", but its cell holds two quoted readings with document hash and page (S.R.O. 17(E)/1993 item 36, PDF p.18; Army Rules 1954 r.182, PDF p.51). The previous review counted this edge among those that quote competing readings. The label is correct for C-02 and C-03. Reading (a) also ends mid-word ("...giving false evidence bef"), as it does in the C5 register. | `amendment_graph.csv` row `C9-AG-RES-SC4-01` at both commits; `source_conflict_register.csv` row `C5-CF-SC4-01`; `build_stat_c9.py` lines 739-742: the branch applies to every register row with `source_a`/`source_b`, whatever they contain. | Label by content: for example "as recorded in the C5 conflict register (source_a / source_b)", and say that reading (a) is cut in the register. |
| CL-02 | P3 | FL-06 is fixed for `evidence` only. Other carried-forward cells are still cut with no marker: `provision` at 200 characters (2 edges: AR-029, AA-01), `amending_instrument` at 160 (2 edges: AA-C3-02, AA-C3-04), `edge_kind` at 60 (21 edges), and `commencement_as_printed` at 120 inside `status_detail` (2 C8 rows exceed it). The earlier finding cited these lines too; the disposition speaks only of `evidence`. | `build_stat_c9.py` lines 755, 841-843; my length counts over `amendment_graph.csv` and the C8 matrix. | Mark each cut or carry the text in full. |
| CL-03 | INFO | FL-01 confirmed. `build_corr.py <repo> --check` exits 0 on both interpreters and prints `OK OUTPUT_SHA256SUMS`. `sha256sum -c` passes 6 of 6 in `CORRECTIONS/` and 122 of 122 in `STATUTORY/`. | Clone runs. | None. |
| CL-04 | INFO | FL-02 confirmed: the reproduce block reads `--check --verify-held`, with a warning. With both flags the run printed "verify-held: OK (33 anchors)", rc 0, and left the tree clean. The tool itself still writes when `--verify-held` is given without `--check`; only the documentation changed, as the disposition says. | `CORRECTIONS_C9_FINDINGS.md` lines 162-164; clone `git status` empty after the run. | Optional: make `--verify-held` read-only. |
| CL-05 | INFO | Other builders, all with `--check`: `build_stat_c9.py` "CHECK OK: 123 outputs" (venv and python3.11); `collect_readings_c9.py` three "CHECK OK"; `extract_branch_pins.py` "CHECK OK" against the documented snapshot `c9src`; `synthetic_transaction_demo.py --check --work <scratch>` "CHECK OK: 43 recorded values compared; transcript compared". | Clone runs. | None. |
| CL-06 | INFO | The delta is confined to `C9-LEGAL-EVIDENCE/`. Data changes are exactly: 3 `preserved_readings` cells (C-02, C-03, SC4-01), 10 `evidence` cells with the truncation marker, finding C9-F-A03 `observation`, proposal C9-CP-A05 `proposed_change`. Row counts unchanged (116 edges; 17 / 41 / 43 / 15 by status; 23 findings; 40 proposals). FL-04 wording reads as claimed and the copy is nowhere called official. FL-05 text is unchanged, as recorded. | Cell-level diff of the three CSVs between the two commits. | None. |
| CL-07 | INFO | Tests: `TXN-DEMO/tools` 2 tests OK on both interpreters. Full `tests/test_legal_audit_*.py`: 610 OK, 6 skipped, on both. All six skips state their reason: the clone has no `origin/raw-data` ref. The committed review files are byte-identical to the delivered ones. No service-number-shaped token in the added lines. | `rev_heads/logs/ut.le.*.log`. | None. |

## Not checked
- The legal correctness of any proposal or reading.
- `extract_branch_pins.py --check` exit status when it reports a difference (it printed "CHECK DIFF" when I passed a non-snapshot tree as the snapshot argument; the documented snapshot gives "CHECK OK").

## Isolation
`c9le`: `git status --short --ignored` empty, HEAD a61c0e57.
