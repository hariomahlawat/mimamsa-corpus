# Narrow review: PR #38 final commit 562a55ef and the combination with staging ff425a9a

RESEARCH ONLY. This is a technical review of tests, a docstring and review records. It is not a legal sign-off and
not an approval on behalf of the legal advisor, JAG or the project owner.

- Scope: `git diff 81df0e6c 562a55ef` (5 files, +159 -1) and the local merge 1b20a16c (staging ff425a9a + 562a55ef).
- The code through 81df0e6c was accepted earlier and was not re-reviewed here.
- All experiments ran in clones under `scratchpad/c9rev38_tmp/tmp.27raA7o6vh/` (`comb`, `mut`). Both worktrees stayed clean.
  No host path was passed as an argument, no global git config was changed, no network was used. `/dev/null` was a
  character device at the time of the runs.

## Result

No P1 and no P2. Three P3 and three INFO items, none blocking.

## Checks

### 1. Final commit touches only tests, a docstring and review records — PASS
`git diff 81df0e6c 562a55ef -- tools/*.py` is one line: the docstring of `ledger.check_committed_layout`
(ledger.py:450). The corrected text is accurate: `check_committed_layout` is called at auth_ledger.py:50 and
reader.py:161 only, and `apply_ledger` does not call it. The other four files are the test module (+20) and three
new files under `review/`.

### 2. The new tests exercise what they claim — PASS
Mutants applied one at a time in the `mut` clone; full AUTH-LEDGER module run for each (baseline 189 OK).

| Mutant | Result | Killed by |
| --- | --- | --- |
| ledger.py:20 `abspath` -> `realpath` (the earlier survivor S1) | KILLED | `test_n01_...` (first import `ledger`) |
| pins.py:8 same change | KILLED | `test_n01_...` (`pins`) |
| strength.py:14 same change | KILLED | `test_n01_...` (`strength`) |
| auth_ledger.py:10 same change | KILLED | `test_n01_...` (`auth_ledger`) |
| reader.py:14 same change | KILLED | `test_r03_library_import_through_a_symlink_is_rejected` |
| auth_ledger.py:91 same-directory guard removed (`$PWD` used whenever absolute) | KILLED | `test_n05_stale_pwd_is_ignored` |
| auth_ledger.py:91 `$PWD` not used at all | KILLED | `test_r01_relative_cli_inside_the_link_target_uses_the_logical_cwd` |
| auth_ledger.py:91 `isabs` term removed | SURVIVED | redundant with the realpath comparison (F-03) |
| auth_ledger.py:91 guard weakened to `os.path.isdir(pwd)` | SURVIVED | see F-01 |

`CLI_PATH` is relative, so N-05 does reach the `$PWD` branch.

### 3. Combined candidate in a copy — PASS
- `auth_ledger.py verify`: `v0000 ok`, `HEAD 0 443c4bdf348b2a1bcd603d2701f097aa90a8155efd43c10760f5fd86c76c6b6b; frozen pins ok; ledger verified`, rc 0.
- `tests.test_legal_audit_auth_ledger`: 189 tests OK, no skips (187 at 81df0e6c plus the two new tests).
- `unittest discover -s tests -p "test_legal_audit_*.py"`:
  - fresh clone: 552 OK, skipped=6. All six skips are corpus-ref tests (`origin/raw-data` absent in a `--no-local`
    clone): canonical_coverage (2), identity_map (1), review_fixes_cycle3 Fix3CodedRecordSections (3). None is an AUTH-LEDGER test.
  - same clone with `refs/remotes/origin/raw-data` set to the CI pin ad77758d (as the merged workflow does): 552 OK, 0 skipped.

### 4. Scope versus staging — PASS
- `git diff ff425a9a 1b20a16c` is byte-identical to `git diff 1a21a2e8 562a55ef`. No conflict markers.
  Staging differs from the PR base only in `.github/workflows/legal-audit-kit-ci.yml` (+18), which the PR does not touch.
- 24 changed files: 23 under `legal_knowledge/audit_work/AUTH-LEDGER/` (4 top-level documents, 12 in `review/`, 7 in `tools/`)
  and `tests/test_legal_audit_auth_ledger.py`. Nothing else, so the frozen originals, crawler data, schema, pipeline and `.github` are unchanged.
- `ledger/HEAD` and `ledger/manifest.jsonl` unchanged (version 0, one line). `decisions/` and `corrections/` hold only their README.
  `effective/v0000/` unchanged. No ledger entry, decision record, BIND line or approval state was added.

### 5. Review records — PASS with notes
- `fable_confirm_c8_security_81df0e6c.md` and `_findings.csv` are byte-identical to the originals in `c8out/revA4/`
  (SHA-256 e6ecbb90...affc6dec and 838e5e05...3219e89b).
- `DISPOSITIONS_81df0e6c.md` matches the findings: verdict ACCEPT, R-01 to R-05 closed, N-01 / N-02 / N-05 fixed
  (each confirmed above), N-03 / N-04 / N-07 / N-08 recorded. See F-02 for N-06 and F-04 for wording.

## Findings

- **F-01 (P3, tests).** `test_n05_stale_pwd_is_ignored` uses a non-existent stale `$PWD` only. A guard weakened to
  "any existing absolute directory" passes all 189 tests. Shipped code handles an existing but different `$PWD`
  correctly (`verify` rc 0); the weakened guard rejects ("... is not a directory"), so the gap is fail-closed, not a bypass.
  Remediation: add a second case with `$PWD` set to an existing unrelated directory.
- **F-02 (P3, records).** The N-06 disposition gives a cause for the `/dev/null` anomaly and cites
  `C8-SOURCES/review/DISPOSITIONS_f98f7a2a.md`. That file is not in this tree; it exists only on
  `claude/c8-primary-sources-quality` (commit 0e75a4a3). The verbatim review recorded "cause not identified".
  The cited file does describe a reviewer run that replaced and restored `/dev/null`, but I did not verify that it was the same
  event. Until the other branch merges the reference dangles. Remediation: mark the cause as reported, not verified, and name the branch.
- **F-03 (P3, documents; combination only).** Three statements are stale once this lands on a staging that already holds PR #37:
  `C8_SECURITY_CLOSEOUT.md:19` ("CI still checks out depth 1 until the separate full-history PR is approved"),
  `REPOSITORY_BINDING_READINESS.md:7` ("default depth of 1 ... prepared as a separate draft PR") and
  `APPROVAL_CONTROLS.md:56, 85` ("was not made here", "draft PR"). The workflow on ff425a9a has `fetch-depth: 0` and an explicit
  `auth_ledger.py verify` step. The documents understate the control, so this is not a safety issue. Remediation: a follow-up document correction.
- **F-04 (INFO).** `DISPOSITIONS_81df0e6c.md` says the P3 items "are batched in the next commit"; they are in the same commit, 562a55ef.
- **F-05 (INFO).** The `isabs` term at auth_ledger.py:91 is not pinned by a test; it is redundant with the realpath comparison.
- **F-06 (INFO).** Disposition N-01 says "all are rejected" for five import orders: confirmed. The sixth module order (`reader` first) is covered by the R-03 test.

## Not checked / false-pass limits

- Code through 81df0e6c (accepted earlier); the CI change of PR #37 itself; an actual CI run on a runner, including job time against the 10-minute limit.
- GitHub state: PR contents versus the local worktree, reviews, branch protection, whether ff425a9a is the current remote staging tip.
- The Hugging Face dataset: coverage of the canonical corpus is unknown and out of scope.
- A local merge with a different merge commit will have a different id than 1b20a16c; only the tree content was compared.
- Passing tests and matching hashes show internal consistency. They do not show authenticity, currency or legal correctness of any source, or who approved anything.
- Run as root, one Python and one git version.

VERDICT: ACCEPT

Model identity: Fable 5.2 (`claude-fable-5-2`).
