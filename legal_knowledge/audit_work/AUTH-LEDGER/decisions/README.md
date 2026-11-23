# Decision and review records

Empty at version 0: there are no entries and no approvals.

Each future ledger version that approves entries must add, in the same reviewed PR:
- `D-vNNNN.md`, the owner decision. It contains lines `decision_id:`, `decision: APPROVED`, `ledger_version: NNNN`, `entries: <entry_id>=<sha256>;...`, `decided_by:` and `date:`.
- `R-vNNNN.md`, the independent review. It contains lines `review_id:`, `verdict: ACCEPT` or `ACCEPT_WITH_CONDITIONS`, `ledger_version: NNNN`, `entries: ...`, `reviewer:` and `date:`.

Both are pinned by sha256 in that version's manifest line, and every approved entry declares the same hashes.
