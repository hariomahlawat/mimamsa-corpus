# Confirmation review: C13 A4 remediation (`claude/c13-a4-statutory` @ `fa8715fa`)

The reviewer is independent and did not author this work. The review was read-only, done in a `git clone --shared` copy at `reviews/a4/src2` and run against the reviewer's own HF anchor (48/48 sha256 verified).

**Result: R-01 to R-08 and R-10 are CLOSED_VERIFIED. No new P1 or P2.** There are two new P3s (N-01, N-02). The previous verdict's condition on the resolver is met. Promotions still need legal-adviser sign-off before they are applied.

## Reproduction

- All `--check` runs pass.
- The validator reports 488 records.
- `render --verify` gives 21/21.
- `SHA256SUMS` lists 24 files.
- 58 tests pass: 52 statutory plus the C12 isolation tests.
- The frozen records are unchanged.
- The branch remains additive.

## Resolver results

| Provision | Date | Status | Versions |
| --- | --- | --- | --- |
| BNS whole / s.358 | 1990-01-01, 2023-12-24 | NOT_YET_IN_FORCE | floor 2023-12-25 (date of the Act) |
| BNS whole | 2024-06-30 | UNDETERMINED | possible v01; note that the compilation-reported start 2024-07-01 is later |
| BNS whole | 2024-07-01, 2025-01-01 | UNDETERMINED | possible v01 (S.O. 850(E) not held), no candidate |
| IPC whole | 2024-06-30, 2024-07-01 | UNDETERMINED | possible v01, v02 |
| AFT s.9A | 1950-01-01 | NOT_YET_IN_FORCE | floor 2017-03-31 |
| AA s.169A | 1950-01-01 | NOT_YET_IN_FORCE | floor 1992-09-06 |
| r.16A | 1979-07-28, 1985-01-01 | IN_FORCE_CANDIDATES | v01, v03 (retro, AQ-06) |
| r.16A | 1986-01-01, 1988-09-16 | IN_FORCE_CANDIDATES | v02, v03 |
| r.16A | 1988-09-17 | IN_FORCE_CANDIDATES | v03 |
| r.16A | 1979-06-04 to 1979-07-27 | NOT_YET_IN_FORCE | N-01: v03 is deemed from 1979-06-04 |
| AA s.75 / s.76 / s.127 | 1960-01-01 | UNDETERMINED | possible v01 only (omission excluded by floor) |
| AA s.75 / s.76 / s.127 | 1993-01-01 | UNDETERMINED | possible v01, v02 (Act 37/1992 commencement NOT_STATED_PENDING_ADVICE) |
| r.22 | 1993-12-05 / 1993-12-06 | UNDETERMINED [v01] / IN_FORCE [v02] | correct |

BNS dates before the Act's own date (25-12-2023) are NOT_YET_IN_FORCE, as asked. From 25-12-2023 onward they are UNDETERMINED. That is consistent with the commencement notification not being held, and no candidate is asserted.

## New findings

- **N-01 (P3).** The r.16A window from 04-06-1979 to 27-07-1979 ignores the retrospective deemed date of v03.
- **N-02 (P3).** The resolver's reason text drops the qualifier STATED_IN_INSTRUMENT_DATE_FROM_INFERRED_MASTHEAD.

Details: `confirmation_c13_a4_fa8715fa_findings.csv`.
