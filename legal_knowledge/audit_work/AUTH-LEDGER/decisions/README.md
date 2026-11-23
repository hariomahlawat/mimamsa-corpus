# Decision and review records

Empty at version 0: there are no entries and no approvals.

Each future ledger version must add, in the same reviewed PR, separate files by different persons. In every file each key appears once, the id equals the file name, and the date is `YYYY-MM-DD`.
- `D-vNNNN.md` (and `D-vNNNN-<decision>.md` for WITHHELD or REJECTED entries) is the owner decision. It contains lines:
  - `decision_id:`
  - `decision: APPROVED|WITHHELD|REJECTED`
  - `ledger_version: NNNN`
  - `entries: <entry_id>=<sha256>:<entry_digest>;...`
  - `decided_by:`
  - `date:`
- `R-vNNNN.md` is the independent review. It contains lines:
  - `review_id:`
  - `verdict: ACCEPT` or `ACCEPT_WITH_CONDITIONS`. The latter also needs `conditions_status: DISCHARGED`.
  - `ledger_version: NNNN`
  - `entries: ...`, in the same form
  - `reviewer:`
  - `date:`

`entry_digest` is `tools/ledger.py entry_digest()`: the sha256 of the entry's content columns.

Both are pinned by sha256 in that version's manifest line, and every approved entry declares the same hashes.
