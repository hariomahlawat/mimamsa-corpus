# Confirmation review: PR #42 AUTH-LEDGER, delta 4770c165..2ba7b0a4

Reviewer model: Fable 5.2 (claude-fable-5-2). Date: 2026-11-24. Review only; nothing committed or pushed.
All probes and mutants ran in a disposable clone, `scratchpad/rev_heads/al` (detached at 2ba7b0a4). The reviewed worktree `c10al` was not written to.

## Verdict: ACCEPT

AL-01, AL-02 and AL-03 are fixed as claimed, verified from code and my own runs. AL-04 and AL-05 are fixed. Four P3 residuals are listed; none blocks.

## Findings

| Id | Severity | Statement | Evidence | Requested action |
| --- | --- | --- | --- | --- |
| CA-01 | P3 | The stricter handling stops at `effective/`. A FIFO at `ledger/HEAD` or `ledger/manifest.jsonl` still makes `verify` block, and a directory at `ledger/HEAD` gives an uncaught `IsADirectoryError` (rc 1 traceback, not rc 2). The original AL-04 also recommended adding `OSError` to the CLI's fail-closed `except`; that was not done, and the disposition does not say so. Pre-existing, not a regression. | Clone probes: `mkfifo ledger/HEAD` -> timeout rc 124; `mkfifo ledger/manifest.jsonl` -> rc 124; `mkdir ledger/HEAD` -> `IsADirectoryError`, rc 1. `auth_ledger.py` `main()` except tuple has no `OSError`. | lstat `ledger/manifest.jsonl` and `ledger/HEAD` as regular files before reading; add `OSError` to the except tuple. |
| CA-02 | P3 | Entries inside `ledger/` and `decisions/` are not held to the standard now applied to `effective/`. `verify` returns rc 0 with: `ledger/HEAD`, `ledger/manifest.jsonl` or `decisions/README.md` replaced by a symlink (README even to an unrelated file); a stray FIFO, a symlink to a directory, a broken symlink or an empty directory in `ledger/` or `decisions/`. `unexpected_files` uses `rglob` + `is_file()`, which follows links and ignores non-regular entries. Chain content is still hash-checked, so integrity of the chain is not affected. Pre-existing. | Clone probes `head_symlink`, `manifest_symlink`, `readme_symlink`, `ledger_stray_fifo`, `ledger_stray_dirsym`, `decisions_stray_brokenlink`, `decisions_emptydir`: all rc 0. A stray regular file and a symlink to a regular file are rejected (rc 2). | Walk `ledger/` and `decisions/` with the same no-follow, regular-files-only rule; or record the limit in `EFFECTIVE_OUTPUTS_C10.md`. |
| CA-03 | P3 | Three parts of the AL-01 fix are not pinned by a test. | My mutants on the 29 `C10Effective*` tests: `check_ledger_dirs` skipping `decisions` survives; removing the non-directory branch survives; removing the `base.is_symlink()` guard inside `unexpected_effective` survives (redundant behind `check_ledger_dirs` in `verify`, but the function is also called directly). | Add tests: symlinked `decisions/`; a file at `effective`; `unexpected_effective` called directly on a symlinked `effective`. |
| CA-04 | P3 | `decisions/` may be absent and `verify` still passes at version 0. Consistent with "when present" in the docstring, but not stated in the document. | Clone probe `rm -rf decisions` -> rc 0. | State it, or require the directory. |
| CA-05 | INFO | AL-01 confirmed. Symlinked `effective/` (inside or outside the tree), `ledger/` and `decisions/` are each rejected with rc 2 before the manifest is read; a regular file or FIFO at `effective` or `decisions` is rejected ("is not a directory"). | Probes `eff_symlink_inside`, `eff_symlink_outside`, `ledger_symlink`, `decisions_symlink`, `eff_is_file`, `eff_is_fifo`, `decisions_file`: rc 2. | None. |
| CA-06 | INFO | AL-04 ordering confirmed: layout, `check_ledger_dirs`, `read_manifest`, rebuild of every version (no read of `effective/`), stray walk (`os.walk(followlinks=False)`, `lstat`), then content comparison. A FIFO at `OUTPUT_MANIFEST.json` no longer hangs. Moving the walk after the comparison is killed by the tests. | FIFO at `OUTPUT_MANIFEST.json`, at `transitions.json`, as an extra entry and at `effective/` root: rc 2 with the "not accounted for" message. Directory at an expected name: rc 2. Also rc 2: nested directory, `v0000/v0000`, `v0001`, `v00000`, broken symlinks, directory symlink in `v0000`, symlinked `v0000`, symlinked expected file with identical content, dotfile, newline in name, unix socket, character device node. Hard link to an expected file: rc 0, as documented (AL-05). | None. |
| CA-07 | INFO | AL-03 confirmed. All eight earlier survivors are now killed (M04, M17, M18, M19, M20, M21, M23, M24). Of 11 further mutants, 7 are killed; the 4 survivors are the three in CA-03 and `followlinks=True`, which is equivalent because symlinked directories are pruned explicitly. | `rev_heads/scripts/mut_al.py`. | None. |
| CA-08 | INFO | AL-02 confirmed against the committed file: 112 rows; `basis` = `unchanged` 99, `unchanged (primary copy of the same class)` 12, `a pending copy and no primary copy` 1; frozen equals effective on all 112 rows. | My count over `effective/v0000/source_states.csv`. | None. |
| CA-09 | INFO | Ledger unchanged at version 0. `ledger/HEAD` = `0 443c4bdf348b2a1bcd603d2701f097aa90a8155efd43c10760f5fd86c76c6b6b` = sha256 of the single manifest line; no file under `ledger/` or `effective/` differs from 21e73b83; `verify` prints `v0000 ok`. No entries. | `git diff --stat 21e73b83..2ba7b0a4` over both folders is empty; CLI rc 0. | None. |
| CA-10 | INFO | Tests: 218 passed under the venv (Python 3.13, pytest) and 218 OK under python3.11 (unittest; pytest is not installed for 3.11). No skips. The committed review report and CSV are byte-identical to the delivered ones. The delta touches only the seven files named. | Runs in the clone. | None. |

## Not checked
- Live races (TOCTOU) and unreadable directories (running as root).
- The AL-06 follow-up (PR #41 `TXN-DEMO` expected values after this PR merges). On the PR #41 branch alone the demo `--check` passes.

## Isolation
`c10al`: `git status --short` empty, HEAD 2ba7b0a4. Three ignored `__pycache__` directories there are dated 2026-11-23 and predate this review. `/dev/null` untouched.
