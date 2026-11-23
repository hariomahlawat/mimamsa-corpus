# Independent review: Cycle 8 authentication-security closeout

- **Security branch:** `claude/c8-security-closeout` at `be861ec0`, diff against `1a21a2e8` (13 files).
- **CI branch:** `claude/c8-ci-full-history` at `eed9e0bc`, diff against `1a21a2e8` (1 workflow file).
- **Reviewer:** Fable 5.2 (`claude-fable-5-2`), independent of the implementation. RESEARCH ONLY. This is a technical review; it is not a sign-off for the legal adviser, JAG or the project owner.
- **Findings:** `fable_review_c8_security_be861ec0_findings.csv` (12 rows: 3 P2, 4 P3, 5 INFO).

## Result
The security branch does not close C-02. A committed symlinked package is still accepted when verification is run through the command-line tool, which is the documented entry point and the one CI uses. C-01 is closed. C-04 is closed for commit objects only; a forged tree object still makes an unreviewed version effective. Version zero, the ledger, draft eligibility and the protected paths are unchanged. The CI change is minimal and safe in permissions, but it couples every audit PR to the moving tip of `raw-data`.

| Requirement | Result |
| --- | --- |
| 1. C-01 call-site pin tested end to end in the real layout | Met. Removing `expected_top=pinned_top`, forcing the pin to `None`, or forcing `committed` false each fails two tests |
| 2. C-02 fail-closed symlink check | **Not met** at the CLI and for three of five import orders (F-01). Met only when `common` or `binding` is imported first, or when the test patches `COMMITTED_PACKAGE` |
| 3. Readiness review | Met in coverage and it does not claim a merge proves owner identity. One overclaim on object integrity (F-02); bundle claim untested by the branch (F-07) |
| 4. O-5 procedure, no semantic change implemented | No semantic change implemented (confirmed). The procedure has gaps (F-06) |
| 5. Version zero, ledger, eligibility, protected paths | Met (F-08) |
| 6. CI branch minimal | Met, with a side effect the owner should decide on (CI-01, CI-02) |

## False-pass limitations (read first)
- No network was used. GitHub settings, reviews, branch protection and the remote tip of `raw-data` were not checked.
- The canonical Hugging Face snapshot was not read. Nothing here concerns the authenticity or legal correctness of any source.
- The local repository is shallow, so a real BIND line could not be verified in it. All binding tests used synthetic repositories built by the test suite's own fixtures.
- "Eligibility unchanged" means: each of the 32 C6-01 drafts, converted by the suite's `entry_from_draft`, gives the same transition effect and the same copy-register hash at base and head with `require_binding=False`. It is not a statement that any draft should be approved.
- The mutation set is mine (33 mutants) and is not exhaustive.
- Tree forgery was shown with one object under one id. Blob forgery was not tried; pinned blobs are checked by sha256 content, so it should gain nothing, but that was not tested.
- TOCTOU was tested for one swap point only (after the first layout check).
- Bind mounts, hard-linked directories and filesystem-level tricks were out of scope.

## 1. How the work was done
- Neither worktree was modified: `git status` is empty in both, and the heads are still `be861ec0` and `eed9e0bc`.
- Experiments ran in `/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/revA2_tmp`: `repo` (files of the security worktree, own `.git` with the main object store as an alternate), `base` (`git archive 1a21a2e8`), `attacker` (a second full-layout repository).
- Scripts are in `/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/revA2_tmp/scripts`: `mk_attacker.py`, `imp.py`, `forge_tree.py`, `vectors.py`, `mut.py`, `elig.py`.
- Python: `/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/venv/bin/python` with `PYTHONDONTWRITEBYTECODE=1`; git 2.43.0.

## 2. C-02: symlinked package (F-01, P2)
Set-up: `attacker` is a full copy of the branch with one honest reviewed merge and a BIND line (built by `mk_attacker.py` with the suite's `GitLedger` methods). `victim1` has two committed entries, `README` and `legal_knowledge/audit_work/AUTH-LEDGER` as mode 120000 pointing at the attacker package; one commit, no merge.

| Entry point | Result |
| --- | --- |
| `python victim1/legal_knowledge/audit_work/AUTH-LEDGER/tools/auth_ledger.py build --out X` | rc 0, `APPLIED` |
| the same with cwd inside the link and a relative script path | rc 0, `APPLIED` |
| `victim2`: `legal_knowledge` committed as a symlink, same command | rc 0, `APPLIED` |
| `auth_ledger.py verify` through a symlink to an honest copy | `v0000 ok`, rc 0 |
| library, link path on `sys.path`, `import ledger` first | `APPLIED` |
| library, `import reader` first | `APPLIED` |
| library, `import auth_ledger` first | `APPLIED` |
| library, `import common` first (the tested path) | rejected, "is a symlink" |
| library, `import binding` first | rejected, "is a symlink" |

Cause: Python puts the resolved script directory on `sys.path`, and `ledger.py` and `auth_ledger.py` insert `Path(__file__).resolve().parent` before importing `common`. `common.__file__` is then already resolved, so `LOGICAL_PKG` equals `PKG`. The layout check and the pin both run inside the link target, which is a real directory in the other repository.

The branch's tests do not see this because every C-02 test patches `ledger.COMMITTED_PACKAGE`, and the one test of `LOGICAL_PKG` imports `common` first. Mutant L09 (`COMMITTED_PACKAGE = PKG`) survives.

The same limits as the original C-02 apply: the link shows as 120000 in the tree, and the target must exist on the verifier's machine. What changed is that the documents now say the case fails closed, and the manual auditor instruction was removed (F-05).

Reproduction:
```
cd /tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/revA2_tmp
/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/venv/bin/python scripts/mk_attacker.py attacker        # on a fresh copy of the branch files
mkdir -p victim1/legal_knowledge/audit_work && ln -s $PWD/attacker/legal_knowledge/audit_work/AUTH-LEDGER victim1/legal_knowledge/audit_work/AUTH-LEDGER
git -C victim1 init -q -b main && git -C victim1 add -A && git -C victim1 commit -q -m victim
/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/venv/bin/python victim1/legal_knowledge/audit_work/AUTH-LEDGER/tools/auth_ledger.py build --out o_a ; grep effect o_a/transitions.json
/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/venv/bin/python scripts/imp.py victim1/legal_knowledge/audit_work/AUTH-LEDGER/tools reader
```

## 3. C-01 and other layout vectors
All from `vectors.py`; "committed" means `COMMITTED_PACKAGE` was pointed at the temporary layout, as the branch's tests do.

| Vector | Result | Expected |
| --- | --- | --- |
| V01 linked worktree (`.git` file at the top) | `APPLIED` | yes |
| V02 top directory reached through a symlink | `APPLIED` | yes |
| V03 `--no-local` clone under a symlinked parent | `APPLIED` | yes |
| V04 clone of `git bundle create --all` | `APPLIED` | yes |
| V05 depth-1 clone | rejected, shallow | yes |
| V06 `core.worktree` set elsewhere | rejected, top mismatch | yes |
| V07 `gitdir:` file at `legal_knowledge/` and at `audit_work/` | rejected, top mismatch | yes |
| V08 intermediate component committed as 120000, real directory on disk | rejected, mode 120000 | yes |
| V09 package committed as a gitlink (160000) | rejected, mode 160000 | yes |
| V10 package absent from HEAD | layout check passes; a BIND line is still rejected | see F-04 |
| V11 unborn HEAD | layout check passes | see F-04 |
| V12 packed forged commit under the merge id | rejected, hash | yes |
| V13 directory swapped for a symlink after the first check | rejected by the second check in `apply_ledger` | yes |

The real worktree used for this review is itself a linked worktree; `auth_ledger.py verify` passes there.

## 4. C-04: forged objects (F-02, P2)
`_object_ok` re-hashes `git cat-file commit` output, so it is independent of storage. Loose (branch tests) and packed (V12) forged commits are rejected.

Trees are not re-hashed. With an honest merge of an unrelated PR (H, M), a direct unreviewed commit of version 1 and a BIND line naming H and M:

| Store | Before | After forging the tree of H and M | `git fsck` | Local-path clone | `--no-local` clone, bundle clone |
| --- | --- | --- | --- | --- | --- |
| loose | rejected | `APPLIED` | rc 3 | `APPLIED` | fail, rc 128 |
| alternate | rejected | `APPLIED` | rc 3 | `APPLIED` | fail, rc 128 |
| packed (hand-built idx) | rejected | `APPLIED` | rc 4 | `APPLIED` | fail, rc 128 |

`REPOSITORY_BINDING_READINESS.md` says "A forged object under a genuine id is rejected". That is true for the four commit objects only. `APPROVAL_CONTROLS.md` and the closeout word it correctly ("forged commit objects"), and the closeout lists trust in the object store as a residual. The advice to use "a fresh clone" needs the transport named.

## 5. Mutation run
33 mutants over `check_package_layout`, `_object_ok` and its call sites, `check_committed_layout` and its three call sites, and `LOGICAL_PKG`. 21 killed, 12 survived. Full results: `/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/revA2_tmp/mutation_results.json`.

| Survivor | Meaning | Equivalent? |
| --- | --- | --- |
| L09 `COMMITTED_PACKAGE = PKG` | logical path not wired | no (F-01) |
| A01 layout call removed from `auth_ledger.verify` | call site untested | no |
| L04 layout call removed from `apply_ledger` | call site untested (V13 depends on it) | no |
| B07, B09 ls-tree skipped for intermediate components | untested | no |
| B10 toplevel-equality guard dropped | untested | no |
| B11 only 120000 rejected | gitlink untested | no |
| L02, L03 either clause of `is_committed_package` | untested | no |
| B01 suffix check, B03 `is_dir` check | defensive | near |
| B14 cat-file failure treated as ok | covered by the earlier `cat-file -t` for merge and head | near |
| B17, B21 one of the two re-hash sites narrowed | each is covered by the other site | yes |

Killed, as the closeout says: `expected_top` not passed (L06), pin `None` (L07), `committed` false (L05), no symlink check (B02), no ls-tree block (B06), `_object_ok` always true (B13), either re-hash site removed (B16, B19), `LOGICAL_PKG` resolved (C01), reader call removed (R01).

## 6. Requirement 5 and O-5
- `auth_ledger.py verify`: `v0000 ok`, `HEAD 0 443c4bdf348b2a1bcd603d2701f097aa90a8155efd43c10760f5fd86c76c6b6b`, in the read-only worktree, the copy and the base export.
- The four outputs `coverage_summary.json`, `source_master_register.csv`, `source_copy_register.csv`, `corpus_crosswalk.csv` in `effective/v0000` are byte-identical to `SOURCE-LIBRARY-C5/registers`. `effective/` is identical to base.
- No diff in `ledger/`, `decisions/`, `corrections/`, `tranches/`, `evidence/`, `schema/`, `frozen_inputs.json`. The manifest has one line (version 0). No entry or record exists.
- 32 of 32 drafts: same result at base and head (all `APPLIED` in a synthetic root without binding, 32 distinct register hashes, pairwise equal).
- No diff under `CALIBRATION-02`, `SOURCE-LIBRARY-C5`, `curated_originals`, `C6-01-PROVENANCE`, `C6-PREP`, `config`, `crawler`, `.github`.
- `rules_v1.py`, `strength.py`, `urlcheck.py`, `pins.py` and the schema are byte-identical to base. `activation_policy`, `demotion_basis` and `APPLIED_PENDING_BINDING` occur nowhere in `tools/` or `schema/`. O-5 is analysis only.
- The two review files are byte-identical to the originals in `/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c8out/revA/`.
- Tests: 172 in the AUTH-LEDGER module, 535 in `test_legal_audit_*.py`, all pass; 0 skipped with `origin/raw-data` present.

O-5 gaps are in F-06: the review record that gates an immediate demotion is text any repository writer can author; reversal needs a bound version; the stuck-unbound case is undefined; the CORRECTION field is misnamed.

## 7. CI branch
- One file, 7 added lines. `permissions: contents: read` unchanged; triggers unchanged; no secret; `persist-credentials: false`; one added step, `auth_ledger.py verify`.
- With `fetch-depth: 0`, checkout fetches all branches, so `origin/raw-data` exists. Locally that turns 5 skipped tests into 5 passing tests and both `--check` scripts from "NOT_CHECKED" to "MATCH".
- The regeneration reads `origin/raw-data` by name. The committed output pins commit `ad77758d`. A later checkpoint on `raw-data` breaks byte identity for every audit PR (CI-01). Whether the remote tip is still `ad77758d` is unknown.
- Fetch size is about 1.2 GiB packed locally, inside a 10-minute job (CI-02). Not measured on a runner.

## 8. Not checked
- GitHub branch protection, required reviews, stale-approval dismissal, any review id or login.
- The remote state of any branch; the Hugging Face dataset.
- Signatures or owner identity. None exists to check.
- Authenticity of any held source file.
- Behaviour on git versions other than 2.43.0, and on Python 3.11 specifically (the venv interpreter was used).
- Forged blob objects; hash-colliding objects; filesystem-level redirection other than symlinks.

## Required corrections before the security branch is accepted
1. F-01: bind the layout check and the pin to the caller's repository, not to the module's own path; test the real CLI through symlinks.
2. F-02: re-hash the trees the verdict depends on, or run fsck during BIND verification, or narrow the readiness text and name the residual; name the clone transport.
3. F-05: restore the manual auditor instruction until item 1 is done.
4. F-03, F-04, F-06, F-07: tests and wording, as listed in the CSV.

## Conditions for the CI branch
1. CI-01: owner decision on the `raw-data` coupling (accept and document, pin the commit, or fetch only what binding needs).
2. CI-02: measure the first run against the 10-minute limit.

Security branch (`claude/c8-security-closeout`, be861ec0):

VERDICT: REJECT

CI branch (`claude/c8-ci-full-history`, eed9e0bc):

VERDICT: ACCEPT WITH CONDITIONS

Model identity: Fable 5.2 (`claude-fable-5-2`).
