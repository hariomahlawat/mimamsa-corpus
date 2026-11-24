# Dispositions of the adversarial review of `4770c165` (PR #42)

The verdict was **ACCEPT WITH CONDITIONS** (AL-01, AL-02, AL-03). The report is copied verbatim beside this file. The fixes are in the next commit, which **has not been re-reviewed**.

| Id | Severity | Disposition |
| --- | --- | --- |
| AL-01 | P2 | **Fixed.** A new `check_ledger_dirs` rejects a symlinked `ledger/`, `decisions/` or `effective/` (or a non-directory there) before the manifest is read, and `unexpected_effective` reports a symlinked `effective` itself. This also closes the pre-existing gap for `ledger/`. Tests: `test_symlinked_effective_dir_rejected`, `test_symlinked_ledger_dir_rejected` |
| AL-02 | P2 | **Fixed.** `EFFECTIVE_OUTPUTS_C10.md` now says that `basis` names the derivation rule, not a ledger effect. It cites the 12 `unchanged (primary copy of the same class)` rows and the Isaac `a pending copy and no primary copy` row at version 0 |
| AL-03 | P2 | **Fixed.** 13 tests target each meaningful survivor: hidden file, hidden directory, case-variant file, trailing-space file, case-variant version directory, unusual extension, empty stray directory, nested version-named directory, and the two-version expected set (unit), plus the AL-01 and AL-04 cases. 218 AUTH-LEDGER tests pass. The re-run of the mutation set is left to the next review |
| AL-04 | P3 | **Fixed.** `verify` now rebuilds every version first, then walks `effective/`, and only then reads committed outputs. A FIFO or a directory at an expected name is rejected with rc 2 instead of hanging or raising `IsADirectoryError` (tests added) |
| AL-05 | P3 | **Fixed (documentation).** The message wording is clarified, and the document notes that hard links are accepted because content is compared |
| AL-06 | P3 | **Recorded; integration-order item.** If this PR merges, the C9 synthetic transaction (PR #41 `TXN-DEMO`) must regenerate `expected_hashes.json` and `TRANSCRIPT.md`. Only tool-byte-derived values change; all behavioural checks pass (confirmed independently by the coordinator) |
| AL-07 to AL-09 | INFO | Recorded |
