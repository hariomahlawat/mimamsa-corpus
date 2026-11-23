# Effective outputs: integrity rule and column semantics (Cycle 10)

## Integrity rule (C9 synthetic-transaction finding TXN-1)
`auth_ledger.py verify` already rebuilt each committed `effective/vNNNN` and compared every expected file. It did not notice **extra** entries, so a stray file sitting beside the real outputs went unreported. Since Cycle 10, `verify` also requires that `effective/` contains exactly:
- one `vNNNN` directory per manifest line, and
- in each directory, exactly the files the rebuild produces, plus `OUTPUT_MANIFEST.json`.

`effective/`, `ledger/` and `decisions/` must themselves be real directories; a symbolic link is rejected (review AL-01). The walk runs **before** any committed output is read, so a FIFO or a directory at an expected name is rejected instead of hanging or crashing `verify` (review AL-04). The walk never follows symbolic links. Each of the following is rejected with the message `entries in effective/ not accounted for by the manifest`:
- a symlinked directory or file, even one with identical content;
- a non-regular file;
- an unknown directory;
- a nested directory;
- an unknown file, including hidden files, case or trailing-space variants and any extension.

A hard link to an expected file is accepted, because content is compared byte for byte (review AL-05).

Version 0 is unchanged: the genesis line, `ledger/HEAD` and `effective/v0000` are byte-identical.

## `source_states.csv` column `basis` (C9 finding TXN-3; corrected after review AL-02)
The column name cannot be changed. Doing so would change the bytes of `effective/v0000/source_states.csv` and therefore the pinned `effective_sha256` of the genesis line. Its meaning is therefore recorded here.

`basis` names the **derivation rule** (`reader.derive_holding`) that produced `effective_holding_state` from the frozen state and the active ledger entries. **It is not necessarily a ledger effect.** At version 0 there are no entries, and `effective_holding_state` equals `frozen_holding_state` on all 112 rows. Even so, 13 rows carry a value other than `unchanged`:
- 12 rows: `unchanged (primary copy of the same class)`;
- 1 row: `a pending copy and no primary copy` (C5-SRC-J-SC-2026-ISAAC).

Read it as follows:
- A value beginning `unchanged` means the effective state equals the frozen state.
- Other values describe the rule applied, for example the copy situation it is based on.
- Whether a ledger entry caused a change is shown by comparing the two state columns, and by `transitions.json`. It is never inferred from `basis` alone.
- `basis` never states legal currency, applicability or authenticity beyond the documented provenance class.

## Not changed (C9 finding TXN-2)
No append or bind command was added. Ledger lines are still written by hand in a reviewed PR and checked by `verify`. A controlled command would be a convenience feature, not an integrity fix, so it is left to the owner.
