# Integration gate: claude/c13-closeout

Run with the coordinator gate script (`scratchpad/gate.sh <worktree> <outfile>`) on 2026-11-26T00:54:34Z, after the
final update (B1 second confirmation, B0 relabel, A8/A9 review ACCEPT).

| Item | Value |
| --- | --- |
| Commit gated | `aa1c3040ac48a07cc12804574232eda324cfc514` (tree `8da50439f6279f80507919146987e4fbefaf155a`) |
| Checks | **32 run, 32 exit 0, 0 non-zero** |
| Legal-audit unittest discovery | **Ran 1058 tests, OK (skipped=3)** |
| HF sync workflow guard | Ran 12 tests, OK |
| Protected hashes | `records_658` 9a8f0d19..., `cases_53` 8b8d53cd..., CALIBRATION-02 cfe5f408...: OK |
| AUTH-LEDGER | `auth_ledger.py verify`: exit 0 (version 0) |
| Warning lines | 332 (ResourceWarnings from earlier tools and tests; none from the A8/A9 tests or tools) |

**Layout dependency (review F09).** The skip count depends on the worktree layout: six A4 tests derive
`SCRATCH = REPO.parent.parent` and skip unless the worktree sits at `scratchpad/c13/<ws>` (or `C13A4_SCRATCH` is
set). Gated from another location, the same commit gives skipped=9 with every check still passing.

Earlier runs: `eb29c15a`, `ccf9805d` and `3b250a73` (both 32/32; 1058 tests OK, skipped=3). The only later commit adds this record
and the A9 SHA256SUMS (records only).
