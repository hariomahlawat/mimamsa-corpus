# Narrow confirmation: AUTH-LEDGER C8 security branch at 81df0e6c

- **Scope:** only the corrections for R-01..R-05 of the focused re-review of 06a54c66 (`git diff 06a54c66 81df0e6c`), plus the regressions named in the task. Not a fresh full review.
- **Reviewed:** `claude/c8-security-closeout` at `81df0e6c1e6d4631b6f9511a41b1e233f9fbfe53`, base `1a21a2e8`. The worktree `revA_sec3` was read only and is unchanged (`git status --short` empty after the review).
- **Method:** all experiments ran in private `git clone --shared` copies under `scratchpad/revA4_tmp/` (`repo`, `mrepo`), Python 3.13.18, git 2.43.0, as root, no network. Earlier attack scripts (`revA3_tmp/scripts/forge_anc.py`, `forge_more.py`, `forge_base.py`, `forge_tree.py`, `vectors.py`, `imp.py`, `mut3.py`) were re-run unchanged against the copy; new scripts are in `revA4_tmp/scripts/` (`anc.py`, `r01b.py`, `s1.py`, `mut4.py`).
- **Status of this document:** RESEARCH ONLY. It is not a sign-off for the legal advisor, JAG or the project owner. A hash match shows bit integrity, not authenticity or legal correctness.

## Result
All five conditions are met. No P1 or P2 finding. Two new P3 findings (one test gap, one stale docstring) and six INFO notes; none blocks.

| ID | Status | Evidence |
| --- | --- | --- |
| R-01 relative CLI inside a link | **CLOSED** (residual stated accurately) | With `$PWD` naming the logical directory, every relative run inside the link target is rejected with "is a symlink": cwd = package, cwd = `tools/`, `./tools/../tools/...`, real `bash cd`, a subshell, `sh -c`, and a symlinked parent `legal_knowledge` (A2-A4, A9, A12, A13, B1). Without a usable `$PWD` the link is still invisible and the attacker's bound package builds "as of version 2": `$PWD` unset, stale, relative, equal to the resolved path, `cd -P`, `env -i` (A5-A8, A10, A11, B2). The docstring, usage line and both documents now say exactly this |
| R-02 forged ancestry commit | **CLOSED** | `forge_anc.py`: plain `merge-base --is-ancestor` returns 0 after the forgery; the reader now rejects ("merge_commit is not in the history of the checked-out HEAD"). Also rejected: forged commit on a second-parent path of HEAD, forged HEAD, undecodable object and missing object on the path. The two sentences are corrected |
| R-03 untested controls | **CLOSED** (one narrower gap, N-01) | Forged pinned blob, forged base manifest and reader-first library import each have a test that kills the matching mutant (H3, H8, S3, S4, L9, N10). "Killed all 8" is corrected |
| R-04 missing git, refused repository, nested export | **CLOSED** | Missing `git`: `LedgerError`, rc 2, no traceback, CLI and library (D1, D1b, D1c, E1b). Real "dubious ownership" (repository top chowned to another uid) and a garbage `.git` file fail closed (D2, D3). An export below another work tree is rejected and the rule is documented (E2). Edge cases in N-03 |
| R-05 stale text | **CLOSED** in the documents (N-02 for a docstring) | `C8_SECURITY_CLOSEOUT.md` C-02 row and the O-5 sentence are corrected |

## 1. Re-run of the earlier attacks (copy of 81df0e6c)
| Script | Result |
| --- | --- |
| `forge_anc.py` | no forgery: REJECTED; interior ancestor forged: REJECTED (was APPLIED at 06a54c66) |
| `forge_more.py blob` | 4 forged blobs under genuine ids: REJECTED (blob does not hash to its id) |
| `forge_more.py subtree` | 6 tree levels and 3 blobs, each forged in turn: all 9 REJECTED |
| `forge_more.py head` | forged HEAD commit object: REJECTED (layout check) |
| `forge_base.py` | direct push before an unrelated merge: REJECTED; base root tree forged: REJECTED |
| `forge_tree.py loose / alternate / packed` | fresh local-path clone REJECTED in all three; `--no-local` and bundle clones refused by git itself |
| `vectors.py` V01-V13 | all "as expected": V01-V04 APPLIED, V05-V13 REJECTED |

## 2. Ancestry re-hash on legitimate repositories
Synthetic real-layout repository: bound merge, then 300 commits and 38 side-branch merges (453 commits on the ancestry path, 456 in total), then the BIND commit.

| Case | Result | Time (whole `effective_state`) |
| --- | --- | --- |
| L1 loose objects | APPLIED | 0.39 s; `_ancestry_ok` alone 0.034 s |
| L1b after `git gc --aggressive` (packed, deltas) | APPLIED | 0.36 s |
| L1c commit-graph file present | APPLIED | 0.34 s |
| L2 later merge of a branch forked before the bound merge | APPLIED | 0.32 s |
| L3 `--no-local` clone | APPLIED | 0.33 s |
| L4 bundle clone | APPLIED | 0.32 s |
| L5 linked worktree | APPLIED | 0.34 s |
| L6 HEAD equals the merge, BIND line uncommitted | APPLIED | 0.34 s |
| L7 `--shared` clone (alternates) | APPLIED | 0.35 s |

Real CLI on a full clone of the repository with a synthetic bound version (`build`): relative from the top with and without `$PWD`, cwd = package, cwd = `tools/`, through a symlinked top directory, stale `$PWD`, cwd above the top, linked worktree: all rc 0 (C1-C9). No legitimate layout was rejected. The cost on the real repository was not measured: it has no BIND line.

## 3. Regressions
| Check | Result |
| --- | --- |
| `tools/auth_ledger.py verify` (worktree and copy) | `v0000 ok`; `HEAD 0 443c4bdf348b2a1bcd603d2701f097aa90a8155efd43c10760f5fd86c76c6b6b; frozen pins ok; ledger verified`; rc 0 |
| `test_legal_audit_auth_ledger.py` in the copy | 187 tests OK (16.5 s) on the valid run; see N-06 for an invalid first run |
| `test_legal_audit_*.py` in the copy | 550 tests OK, 6 skipped (25.3 s) |
| git-archive export outside any work tree, `verify` | v0000 verified, same HEAD value (E1) |

## 4. Mutation check (21 mutants, AUTH-LEDGER module)
16 killed, 5 survived.

| Mutant | Result | Assessment |
| --- | --- | --- |
| N1 ancestry call dropped; N2 sha1 compare neutralised; N5 only first commit hashed | KILLED by `test_r02_*` | |
| N6 `$PWD` ignored | KILLED by `test_r01_*` | |
| N8 missing-git handler removed; N9 refused repository tolerated | KILLED by `test_r04_*` | |
| H1, H3 (blob hash), H8 (base manifest unverified) | KILLED by `test_r03_forged_*` | H3 and H8 survived at 06a54c66 |
| S3, S4, L9, N10, N11 (reader `sys.path`, `LOGICAL_PKG`, `COMMITTED_PACKAGE`) | KILLED by `test_r03_library_import_*` | |
| A1, A2 (CLI `argv[0]` pin) | KILLED | |
| **S1 `ledger.py` `sys.path` resolved again** | **SURVIVED** | Not redundant: N-01 |
| N7 `$PWD` used without the same-directory check | SURVIVED | Guard works (A6, C7) but has no test: N-05 |
| N3 batch header check; N4 merge not in the list; H9 pinned blobs read unverified | SURVIVED | Redundant: the sha1 compare, `_object_ok` on the merge, and the earlier verified read of each pinned path cover them |

The dispositions' "7 of 7 killed" refers to the author's own seven mutants, whose list is not in the branch; it was not reproduced as such.

## 5. New findings
**N-01 (P3, test gap).** The library-import test imports `reader` first only. With `ledger.py`'s own `sys.path.insert` resolved again (mutant S1) the whole module passes, yet `import ledger` first through a symlinked package then returns `['APPLIED']` (`s1.py`). The same single-order coverage applies to the identical lines in `pins.py`, `strength.py` and `auth_ledger.py`. The shipped code rejects all tested import orders (reader, ledger, common, binding, auth_ledger). `C8_SECURITY_CLOSEOUT.md` says later rounds had "redundant-layer survivors"; S1 is not redundant. Remediation: loop the test over each tool module as the first import.

**N-02 (P3, stale text).** `tools/ledger.py` line 450, docstring of `check_committed_layout`: "Called first by reader.effective_state, auth_ledger.verify and apply_ledger." `apply_ledger` does not call it (line 465 says so). Same defect R-05 fixed in the document.

**N-03 (INFO).** "An exported snapshot ... extracted below another repository's work tree is rejected" holds only when git can read the outer repository. An export below a repository git refuses (E3), or inside a bare repository directory (E4), verifies as a plain export (v0000, rc 0). A `.git` that is a broken symlink is treated as "no repository" because `Path.exists()` follows links (D3b). No impact found: a BIND line cannot verify in any of these ("no git history at the ledger root", D3b, D4).

**N-04 (INFO).** git is now mandatory for every run. An export on a machine without git fails closed even at version zero (E1b). `C8_SECURITY_CLOSEOUT.md` ("Where git is present") and the `check_package_layout` docstring ("Where git is available") still read as if git were optional. Relevant to the offline side.

**N-05 (INFO).** The `os.path.realpath(pwd) == os.path.realpath(os.getcwd())` guard has no test (mutant N7 survives). Without it a stale `$PWD` (normal under `subprocess.run(cwd=...)`) would point the package pin at another directory.

**N-06 (INFO, environment).** My first run of the AUTH-LEDGER module failed 10 of 187 tests. Every failure carried `fatal: bad config line 1 in file /dev/null`: `/dev/null` was at that moment a regular, non-empty root-owned file. Seconds later it was a character device again (birth 14:50:41 UTC). I did not identify what replaced or restored it; other agents were active in the sandbox. The run is discarded; the device type was checked before and after every later run. The tool failed closed during the fault ("git cannot read the repository"). Any concurrent result produced in that window should be re-run.

**N-07 (INFO).** `check_package_layout` reads HEAD's trees with `git ls-tree`, not through re-hashed objects. The documents do not claim otherwise (they list manifest, package tree and pinned files). Analysed, not attacked.

**N-08 (INFO).** The R-01 residual is real and confirmed (section "Result"). It is inherent once the process's only view of its directory is the resolved one.

## 6. Documents
No over-claim found in `APPROVAL_CONTROLS.md`, `C8_SECURITY_CLOSEOUT.md`, `DEMOTION_SEMANTICS_O5.md` or `DISPOSITIONS_06a54c66.md` for the corrected items. The hashed-object sentence now lists exactly what is hashed and says other objects are not. Imprecise wording only: N-01 ("redundant-layer survivors"), N-03 ("is rejected"), N-04 ("where git is present").

## 7. Tested, skipped, blocked
- **Tested:** everything in sections 1-4, on git 2.43.0 and Python 3.13.18, as root, on synthetic repositories and private clones.
- **Not checked:** any code outside the correction diff; GitHub reviews, branch protection, review ids or logins; the CI branch; the Hugging Face dataset (coverage of the canonical corpus: unknown, not in scope); owner identity or signatures; authenticity or legal correctness of any source; other git or Python versions; non-root behaviour (the "dubious ownership" case was produced by chown, as root); attacker-controlled local `.git/config`; cost of the ancestry walk on the real repository.
- **False-pass limits:** the real ledger has only version zero and no BIND line, so every binding result here comes from synthetic fixtures. A passing `verify` shows that pinned bytes and the hash chain agree; it does not show that any record is authentic or correct.

## Recommendations (none is a condition)
1. N-01: run the library-import test once per tool module as first import.
2. N-02: correct the `check_committed_layout` docstring.
3. N-03, N-04: one sentence each in `C8_SECURITY_CLOSEOUT.md`; consider `os.path.lexists` for `.git`.
4. N-05: add a stale-`$PWD` test.

VERDICT: ACCEPT

Model identity: Fable 5.2 (`claude-fable-5-2`).
