# Integration gate: claude/c13-closeout

Run with the coordinator gate script (`scratchpad/gate.sh <worktree> <outfile>`) on 2026-11-25T22:37:10Z.

| Item | Value |
| --- | --- |
| Commit gated | `ccf9805d9988509fc851fb889de6bc6791c44caa` (tree `005957bbfb7b50fc5206b9dce9e7742a5de58ae5`) |
| Checks | **32 run, 32 exit 0, 0 non-zero** |
| Legal-audit unittest discovery | **Ran 1058 tests, OK (skipped=3)** |
| HF sync workflow guard | Ran 12 tests, OK |
| Protected hashes | `records_658` 9a8f0d19..., `cases_53` 8b8d53cd..., CALIBRATION-02 cfe5f408...: OK |
| AUTH-LEDGER | `auth_ledger.py verify`: exit 0 (version 0) |
| Warning lines | 332 (ResourceWarnings from earlier tools and tests; none from the A8/A9 tests or tools) |

An earlier run on `eb29c15a` gave the same result (32/32; 1058 tests OK, skipped=3; 338 warning lines; the 6 extra lines
were ResourceWarnings from the new A9 test, fixed in `ccf9805d`). The only later commit adds this record and the A9
SHA256SUMS (records only).
