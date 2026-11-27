# Decision and review records

Empty at version 0: there are no entries and no approvals.

Each future ledger version must add, in the same reviewed PR, separate files by different persons. In every file each key appears once, the id equals the file name, and the date is `YYYY-MM-DD`.
- `D-vNNNN.md` (and `D-vNNNN-<decision>.md` for WITHHELD or REJECTED entries) is the owner decision. It contains lines:
  - `decision_id:`
  - `decision: APPROVED|WITHHELD|REJECTED`
  - `ledger_version: NNNN`
  - `entries: <entry_id>=<sha256>:<entry_digest>;...`
  - `decided_by:` (a person; a name of an AI model or agent is rejected)
  - `date:` (not earlier than the review's date, and not later than the manifest line's date)
  - `scope: AUTHENTICATION_PROVENANCE_ONLY`
  - `legal_approval: NOT_GIVEN`
- `R-vNNNN.md` is the independent review. It contains lines:
  - `review_id:`
  - `verdict: ACCEPT` or `ACCEPT_WITH_CONDITIONS`. The latter also needs `conditions_status: DISCHARGED`.
  - `ledger_version: NNNN`
  - `entries: ...`, in the same form
  - `reviewer:`
  - `date:`
  - `scope: TECHNICAL_AND_EVIDENCE_REVIEW`
  - `legal_approval: NOT_GIVEN`

`entry_digest` is `tools/ledger.py entry_digest()`: the sha256 of the entry's content columns.

Both are pinned by sha256 in that version's manifest line, and every approved entry declares the same hashes. Every pinned record must be cited by an entry, and may name only entries of its own version that cite it, each once.

**Activation (AUTH-LEDGER-02).** A recorded version stays `PENDING_REPOSITORY_BINDING` until a later PR appends a BIND line naming the merge commit, the reviewed head and the approving GitHub review. `tools/binding.py` verifies the git facts offline. The GitHub review is recorded as asserted, not verified. See `../APPROVAL_CONTROLS.md`.

**Limits.** The ledger checks that the records exist, are pinned, are separate and name the exact entries. It cannot verify **who** wrote a record, or whether stated conditions were really discharged. Those are matters for the review of the PR that adds the version. Text-identity references use `T:AUTH-LEDGER/evidence/copy_facts.csv#<copy_id>`.
