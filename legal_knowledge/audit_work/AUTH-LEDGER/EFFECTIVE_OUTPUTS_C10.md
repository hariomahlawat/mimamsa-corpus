# Effective outputs: integrity rule and column semantics (Cycle 10)

## Integrity rule (C9 synthetic-transaction finding TXN-1)
`auth_ledger.py verify` already rebuilt each committed `effective/vNNNN` and compared every expected file. It did not notice **extra** entries, so a stray file sitting beside the real outputs went unreported. Since Cycle 10, `verify` also requires that `effective/` contains exactly:
- one `vNNNN` directory per manifest line, and
- in each directory, exactly the files the rebuild produces, plus `OUTPUT_MANIFEST.json`.

The walk never follows symbolic links. Each of the following is rejected with the message `entries in effective/ not accounted for by the manifest`:
- a symlinked directory or file, even one with identical content;
- a non-regular file;
- an unknown directory;
- a nested directory;
- an unknown file.

Version 0 is unchanged: the genesis line, `ledger/HEAD` and `effective/v0000` are byte-identical.

## `source_states.csv` column `basis` (C9 finding TXN-3)
The column name cannot be changed. Doing so would change the bytes of `effective/v0000/source_states.csv` and therefore the pinned `effective_sha256` of the genesis line. Its meaning is therefore recorded here:
- `basis` explains the `effective_holding_state` **relative to `frozen_holding_state`**, the frozen Cycle 5 state.
- `unchanged` means the effective state equals the frozen state; no ledger entry affects the source at this version.
- Any other value names the ledger effect that moved the state away from the frozen state, for example a primary or pending copy withdrawn or corrected.
- It never states legal currency, applicability or authenticity beyond the documented provenance class.

## Not changed (C9 finding TXN-2)
No append or bind command was added. Ledger lines are still written by hand in a reviewed PR and checked by `verify`. A controlled command would be a convenience feature, not an integrity fix, so it is left to the owner.
