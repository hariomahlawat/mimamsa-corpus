# Repository-binding readiness (Cycle 8)

A BIND line is the step that makes an approved ledger version effective (`APPROVAL_CONTROLS.md`). **No BIND line exists yet; the ledger is at version 0.** This file lists what must be in place before the first one, and states what each control does and does not prove.

| Dependency | State at Cycle 8 | Needed before the first BIND line | Who |
| --- | --- | --- | --- |
| Full git history in CI | The audit workflow uses `actions/checkout@v4` with its default depth of 1. A shallow clone makes binding verification fail closed, by design | The `fetch-depth: 0` change, prepared as a separate draft PR. That PR also runs `auth_ledger.py verify` as an explicit CI step | owner (O-3) |
| Shallow-clone detection | Implemented: `git rev-parse --is-shallow-repository` must be false | — | done |
| Branch protection on `legal-knowledge/v2.5-staging` | Unknown. Not readable or changeable from here, and not changed | Require a PR, at least one approving review, dismissal of stale approvals on new pushes, no force-push, no bypass | owner (O-2) |
| Required independent review | Recorded in the BIND line as asserted values (review id, login, commit). The commit must equal `reviewed_head` | An auditor confirms them online (GitHub API: pull request reviews), because git history does not contain reviews | auditor |
| Stale-approval dismissal | GitHub setting (O-2). Offline, the BIND check already requires the review commit to equal `reviewed_head`, and the package tree to be identical at review and merge | Enable it in branch protection | owner |
| Owner identity assurance | Not provided. A merge commit, author text or a `decided_by` name does **not** prove who approved. An AI-agent owner name is rejected as a lint only | Optionally, an owner signature over the BIND statement, checked against an out-of-band key (O-1), plus a committed list of identities (O-4) | owner |
| Git-bundle reproducibility | Verification needs only local objects, and network transports are refused. A bundle made with `git bundle create <file> --all` and cloned offline verifies the same way as a full clone. Tested indirectly: a fresh local clone verifies (`C8Security.test_c02_fresh_clone_of_an_honest_layout_applies`) | Snapshots ship a full-history bundle, and the offline side clones it before verifying | packaging |
| Git object integrity | The merge, reviewed-head and parent commit objects are re-hashed from their stored bytes (Cycle 8). A forged object under a genuine id is rejected. A full `git fsck` (about 14 s on this 1.3 GB repository) is **not** run on every read | Optionally, run `git fsck --no-dangling` once per audit as an extra step | auditor |
| Online versus offline | Offline, git history proves topology: an ordinary two-parent merge of the reviewed head, with identical package bytes. Online, GitHub can prove that a named account approved a named commit. Neither proves legal authority | — | — |

**What a verified BIND line establishes.** The ledger version entered staging through an ordinary merge whose second parent was the stated reviewed head, and nothing in the ledger package changed between review and merge. It does **not** establish owner identity, legal or JAG approval, or documentary authenticity beyond the entry's own evidence checks.
