# Cycle 8 security closeout (branch `claude/c8-security-closeout`, base `1a21a2e8` = PR #35 merge)

**Scope:** production controls and tests only. Version zero, the genesis line, HEAD and every rule-1 eligibility outcome are unchanged, and no ledger entry exists.

| Item | Origin | Resolution | Tests |
| --- | --- | --- | --- |
| C-01 (P3): the repository-top pin was not tested at its call site | Fable confirmation review of 3f486562 | `ledger.COMMITTED_PACKAGE` (the logical package path) decides when the pin applies. End-to-end tests build a real git repository with the package at `legal_knowledge/audit_work/AUTH-LEDGER`, plant a nested `gitdir:` file or `.git` directory that points at an attacker repository with an honest merge, and show that the unpinned path applies while the real call site rejects. Removing `expected_top=pinned_top` fails these tests (mutation-checked) | `C8Security.test_c01_*` |
| C-02 (P3): a symlinked package could redirect verification | same | `binding.check_package_layout`: every component from the repository top down to the package must exist, be a real directory and not be a symlink. Where git is present, `HEAD` must record each as a tree (040000), not a committed symlink (120000). It runs before any ledger file is read (`reader.effective_state`, `auth_ledger.verify`). Since round 2, `apply_ledger` relies on these callers; a direct caller of `apply_ledger` gets the repository-top pin but not the layout check. The pin uses `common.LOGICAL_PKG` (`abspath`, not `resolve`) | `C8Security.test_c02_*` (symlink to another repository, nested symlink, broken symlink, committed symlink replaced by a real directory, fresh clone, check runs at version 0); `C8SecurityMore.test_c02_logical_package_path_is_not_symlink_resolved` |
| C-04 (INFO): forged commit objects were rejected only incidentally | same | `binding._object_ok` re-hashes the merge, the reviewed head and both parent commit objects from their stored bytes | `C8Security.test_c04_*`, `C8SecurityMore.test_c04_forged_parent_object_is_rejected` |
| bb1f0971 review F-01, F-04 | narrow review of the PR #35 merge candidate | Fixture comment corrected; the forgery fixture asserts that plain git honours the forged commit-graph | `ReviewFixes03.test_r01_*` |

A mutation run on the 8 controls of the first round killed all 8. Later rounds had redundant-layer survivors; these are documented in `review/DISPOSITIONS_be861ec0.md` and `review/DISPOSITIONS_06a54c66.md`.

**Also in this branch (analysis only, no semantic change):** `REPOSITORY_BINDING_READINESS.md` and `DEMOTION_SEMANTICS_O5.md` (O-5).

**Residual risks:**
- Owner identity is not proven by git (O-1, O-4).
- Branch protection is unverified and was not changed (O-2).
- CI still checks out depth 1 until the separate full-history PR is approved (O-3). **Update (Cycle 9):** that PR (#37) was merged into staging at `ff425a9a`; the audit workflow now checks out full history (`fetch-depth: 0`), pins the corpus ref and runs `auth_ledger.py verify` as an explicit step.
- Verification trusts the local object store beyond the mechanisms checked; audit from a fresh clone or bundle.
- Legal or JAG approval is outside the ledger.

## Round 2: corrections after the Fable review of be861ec0 (REJECT); see `review/DISPOSITIONS_be861ec0.md`
- **C-02 at the production entry point.** The tools no longer resolve their own directory, and the command-line tool pins the committed package to the invoked script path. Real-CLI subprocess tests through a committed package symlink and through a symlinked parent are rejected.
- **Forged trees and blobs.** Every tree and blob on each path the binding verdict reads is re-hashed (`binding._read_verified`).
- **Fail-closed committed layout.** A missing HEAD, a component absent from HEAD, a top mismatch, or a gitlink is rejected.
- **Bundle clone** reproducibility is tested.
- **Documentation:** the manual auditor instruction is restored, and the O-5 gaps are corrected.

**Revised residuals:**
- Run the tool by an absolute path, or from the repository top or above. A relative run from inside a symlink target is caught only where the shell provides `$PWD`.
- Hashing covers the commits on the ancestry path from the merge to HEAD (round 3), the four binding commits, and every tree and blob on the paths the verdict reads. Other objects are not hashed. Audit from a `--no-local` or bundle clone, and optionally run `git fsck`.
- An exported snapshot without `.git` that is extracted below another repository's work tree is rejected: that repository's top is not the package's own. Snapshots must be extracted outside any git work tree, or verified from their bundle.
- Owner identity (O-1, O-4) and branch protection (O-2) are unchanged.

## Round 3: corrections after the focused Fable re-review of 06a54c66 (ACCEPT WITH CONDITIONS, no P1 or P2); see `review/DISPOSITIONS_06a54c66.md`
- The ancestry walk is re-hashed in one batched read.
- The CLI uses `$PWD` for relative invocations.
- A missing `git` raises a `LedgerError`.
- A repository that git refuses, where `.git` exists, fails closed.
- Tests were added for blob forgery, base-manifest forgery, library import through a symlink, interior ancestry forgery and the `$PWD` case. In a mutation run on round 3's 7 controls, all 7 were killed.
