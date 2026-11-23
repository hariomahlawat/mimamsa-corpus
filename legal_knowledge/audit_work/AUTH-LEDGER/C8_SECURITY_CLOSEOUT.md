# Cycle 8 security closeout (branch `claude/c8-security-closeout`, base `1a21a2e8` = PR #35 merge)

**Scope:** production controls and tests only. Version zero, the genesis line, HEAD and every rule-1 eligibility outcome are unchanged, and no ledger entry exists.

| Item | Origin | Resolution | Tests |
| --- | --- | --- | --- |
| C-01 (P3): the repository-top pin was not tested at its call site | Fable confirmation review of 3f486562 | `ledger.COMMITTED_PACKAGE` (the logical package path) decides when the pin applies. End-to-end tests build a real git repository with the package at `legal_knowledge/audit_work/AUTH-LEDGER`, plant a nested `gitdir:` file or `.git` directory that points at an attacker repository with an honest merge, and show that the unpinned path applies while the real call site rejects. Removing `expected_top=pinned_top` fails these tests (mutation-checked) | `C8Security.test_c01_*` |
| C-02 (P3): a symlinked package could redirect verification | same | `binding.check_package_layout`: every component from the repository top down to the package must exist, be a real directory and not be a symlink. Where git is present, `HEAD` must record each as a tree (040000), not a committed symlink (120000). It runs before any ledger file is read (`reader.effective_state`, `auth_ledger.verify`, `apply_ledger`). The pin uses `common.LOGICAL_PKG` (`abspath`, not `resolve`) | `C8Security.test_c02_*` (symlink to another repository, nested symlink, broken symlink, committed symlink replaced by a real directory, fresh clone, check runs at version 0); `C8SecurityMore.test_c02_logical_package_path_is_not_symlink_resolved` |
| C-04 (INFO): forged commit objects were rejected only incidentally | same | `binding._object_ok` re-hashes the merge, the reviewed head and both parent commit objects from their stored bytes | `C8Security.test_c04_*`, `C8SecurityMore.test_c04_forged_parent_object_is_rejected` |
| bb1f0971 review F-01, F-04 | narrow review of the PR #35 merge candidate | Fixture comment corrected; the forgery fixture asserts that plain git honours the forged commit-graph | `ReviewFixes03.test_r01_*` |

A mutation run on the 8 new controls killed all 8.

**Also in this branch (analysis only, no semantic change):** `REPOSITORY_BINDING_READINESS.md` and `DEMOTION_SEMANTICS_O5.md` (O-5).

**Residual risks:**
- Owner identity is not proven by git (O-1, O-4).
- Branch protection is unverified and was not changed (O-2).
- CI still checks out depth 1 until the separate full-history PR is approved (O-3).
- Verification trusts the local object store beyond the mechanisms checked; audit from a fresh clone or bundle.
- Legal or JAG approval is outside the ledger.

## Round 2: corrections after the Fable review of be861ec0 (REJECT); see `review/DISPOSITIONS_be861ec0.md`
- **C-02 at the production entry point.** The tools no longer resolve their own directory, and the command-line tool pins the committed package to the invoked script path. Real-CLI subprocess tests through a committed package symlink and through a symlinked parent are rejected.
- **Forged trees and blobs.** Every tree and blob on each path the binding verdict reads is re-hashed (`binding._read_verified`).
- **Fail-closed committed layout.** A missing HEAD, a component absent from HEAD, a top mismatch, or a gitlink is rejected.
- **Bundle clone** reproducibility is tested.
- **Documentation:** the manual auditor instruction is restored, and the O-5 gaps are corrected.

**Revised residuals:**
- If the working directory is inside a symlink target and the script is named relatively, the link cannot be seen.
- Objects that the verdict never reads are not hashed. Audit from a `--no-local` or bundle clone, and optionally run `git fsck`.
- Owner identity (O-1, O-4) and branch protection (O-2) are unchanged.
