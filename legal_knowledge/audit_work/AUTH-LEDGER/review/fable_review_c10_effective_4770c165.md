# Review: AUTH-LEDGER effective/ integrity fix (C10)

Reviewer model: Fable 5.2 (claude-fable-5-2)
Branch claude/c10-auth-ledger-integrity, head 4770c165e801602c7df2542aff1f089cd209bdfa, base staging 21e73b8348767d5f1524167fcec538e1aad6e732.

## Verdict: ACCEPT WITH CONDITIONS

The fix closes TXN-1 for every stray kind tried except one (effective/ itself as a symlink), does not disturb version 0, and passes the suite. Conditions before merge:

1. AL-01: reject a symlinked `effective/` (or remove the claim from the document).
2. AL-02: correct the `basis` description; it is contradicted by the committed v0000 file.
3. AL-03: add the missing tests (8 meaningful mutants survive).

AL-04 to AL-06 are recommended, not blocking.

## Findings

| id | sev | statement |
| --- | --- | --- |
| AL-01 | P2 | `effective/` as a symlink (inside or outside the repository, committed as mode 120000 or not) verifies `v0000 ok`, rc=0. `os.walk` lists a symlinked top; `check_package_layout` stops at `AUTH-LEDGER`. The document says the walk never follows symlinks. |
| AL-02 | P2 | `basis` documentation is wrong on committed data: v0000 has no entries and frozen == effective on all 112 rows, yet 13 rows are not `unchanged` (12 `unchanged (primary copy of the same class)`, 1 `a pending copy and no primary copy`). The value names the `derive_holding` branch, not a ledger effect. |
| AL-03 | P2 | Tests do not pin hidden files/dirs, case or whitespace variants, empty stray dirs, a nested dir named like a version, non-regular files, unusual extensions, or more than one version. |
| AL-04 | P3 | The walk runs after the content reads. A FIFO named `OUTPUT_MANIFEST.json` hangs `verify`; a directory there gives an uncaught `IsADirectoryError` (rc=1). Pre-existing, but running the walk first would catch both. |
| AL-05 | P3 | Document: the single rejection message is not exact for non-regular entries at expected names; hard links are accepted (no impact, content is compared). |
| AL-06 | P3 | C9 synthetic transaction `--check` fails on this branch (22 of 43 values + transcript) only because the tools bytes changed; all 42 behavioural checks pass. C9 expected values need regenerating after merge. |
| AL-07 | INFO | No integrity-relevant TOCTOU; point-in-time check. Not exercised with a live race. |
| AL-08 | INFO | Version 0 byte-identical; HEAD 0 443c4bdf...6b6b; 197 tests OK. |
| AL-09 | INFO | 28 other stray cases rejected with rc=2. |

Full statements, evidence and recommendations: `findings.csv`.

## 1. Correctness (CLI `verify` in a disposable copy)

Rejected, rc=2, message `entries in effective/ not accounted for by the manifest`: stray file at root and in v0000; unmanifested `v0001`, `v00000`, `v-001`; empty and non-empty nested directories, including `v0000/v0000`; symlinked expected file with identical content (also `OUTPUT_MANIFEST.json`); extra, broken and directory symlinks; symlinked `v0000`; FIFO; unix socket; `Source_states.csv`, `source_states.csv `, `V0000`, `v0000 `; `.hidden`, `.DS_Store`, `.git/`; newline and non-UTF-8 names; extra hard link.

Not rejected:
- `effective/` itself a symlink: rc=0 (AL-01).
- Expected file hard-linked to an outside inode with identical content: rc=0 (AL-05, no impact).

Other outcomes: FIFO as `transitions.json` rc=2 with the older "differs from the rebuild" message; FIFO as `OUTPUT_MANIFEST.json` hangs; directory as `OUTPUT_MANIFEST.json` rc=1 traceback (AL-04).

Legitimate ledger: `v0000 ok` from a git clone and from a git-archive export. The nine-version synthetic ledger of the C9 demo also verifies, so multi-version layouts are not falsely rejected.

Expected set: `set(texts) | {"OUTPUT_MANIFEST.json"}`, the same names `write_outputs` writes. Correct.

## 2. Mutants (full suite, 197 tests, per mutant)

29 distinct mutants: 15 killed, 14 survived.

Killed: M01, M05, M07, M09, M10, M11, M13, M14, M15, M16, M22, M26, M27, M28, M29.

Survivors, equivalent or reporting-only (no action):
- M02 drop `is_symlink` in the prune only; M03 `followlinks=True`; M06 drop `depth == 0` in the prune - the report line already covers these.
- M08 `S_ISREG` -> `not S_ISLNK` - other non-regular files are caught by name or by the earlier `is_file`.
- M12 per-version name set -> union - identical while all versions produce the same names.
- M25 return only the first stray - verify still fails.

Survivors, meaningful (AL-03):
- M04 nested directory named like a version not reported
- M17 file names case-insensitive
- M18 file names whitespace-stripped
- M19 hidden files ignored
- M20 hidden directories ignored
- M21 directory names case-insensitive
- M23 only .csv/.json/.txt strays reported
- M24 empty stray directories ignored

Results: `work/mut/results.txt`; definitions: `work/mut/run.py`.

## 3. Regression

- `git diff base..head` touches nothing under `ledger/` or `effective/`.
- `ledger/HEAD` = `0 443c4bdf348b2a1bcd603d2701f097aa90a8155efd43c10760f5fd86c76c6b6b` = sha256 of the genesis line = `EXPECTED_HEAD` in the tests.
- `python -m unittest tests.test_legal_audit_auth_ledger`: 197 tests OK.
- C9 demo (`--check`, from the c9le root): base CHECK OK; head CHECK FAILED on derived values only (AL-06). Logs: `work/txn_base.log`, `work/txn_head.log`.

## 4. Documentation

- Integrity rule: accurate except the symlink claim (AL-01) and the single-message claim (AL-05).
- `basis`: inaccurate (AL-02).
- "Not changed": accurate; no append or bind command exists.

## Checked / not checked

Checked: diff, surrounding code (`check_committed_layout`, `check_package_layout`, `reader.derive_holding`), 33 filesystem cases, 29 mutants, suite, C9 demo on base and head, committed-symlink case in a disposable clone.

Not checked or reduced assurance:
- Live race (reasoned from code only).
- Unreadable directories/files (session runs as root, permissions do not bind).
- Case-insensitive or normalising filesystems (macOS, Windows); block/character devices (not created, by instruction).
- Other AUTH-LEDGER test modules outside `tests.test_legal_audit_auth_ledger`, if any.

Isolation: all mutations in `work/` (git-archive copy, three local clones, mutant copies). c10al untouched (clean, head unchanged). c9le was only read; during the session `CORRECTIONS/OUTPUT_SHA256SUMS` there had its mtime changed by another process (content diff empty; the demo script does not reference that file).
