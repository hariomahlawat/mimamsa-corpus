# Integration gate: claude/c13-closeout

Run with the coordinator gate script (`scratchpad/gate.sh <worktree> <outfile>`) on 2026-11-25T23:15:15Z, after the
fixes for the independent review `reviews/REVIEW_A8_A9.md`.

| Item | Value |
| --- | --- |
| Commit gated | `3b250a738176ec624c3d212a42a20eb9d1fb2ecb` (tree `5745924127284f0102ffb0eb5c8868c968a31fa5`) |
| Checks | **32 run, 32 exit 0, 0 non-zero** |
| Legal-audit unittest discovery | **Ran 1058 tests, OK (skipped=3)** |
| HF sync workflow guard | Ran 12 tests, OK |
| Protected hashes | `records_658` 9a8f0d19..., `cases_53` 8b8d53cd..., CALIBRATION-02 cfe5f408...: OK |
| AUTH-LEDGER | `auth_ledger.py verify`: exit 0 (version 0) |
| Warning lines | 332 (ResourceWarnings from earlier tools and tests; none from the A8/A9 tests or tools) |

**Layout dependency (review F09).** The skip count depends on the worktree layout: six A4 tests derive
`SCRATCH = REPO.parent.parent` and skip unless the worktree sits at `scratchpad/c13/<ws>` (or `C13A4_SCRATCH` is
set). Gated from another location, the same commit gives skipped=9 with every check still passing.

Earlier runs: `eb29c15a` and `ccf9805d` (both 32/32; 1058 tests OK, skipped=3). The only later commit adds this record
and the A9 SHA256SUMS (records only).
