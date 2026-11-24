# Independent review: PR #44, AUTH-LEDGER file-type hardening (C11)

- **Reviewer:** Fable 5.2 (`claude-fable-5-2`), independent technical review, 2026-11-24.
- **Reviewed:** branch `claude/c11-ledger-fifo-hardening`, head `9f1d7560` (tree `b629f8b1`), base `claude/c10-auth-ledger-integrity` `2ba7b0a4`.
- **Scope:** code, tests and documentation accuracy only. No legal content was judged.
- **Method:** all experiments ran in disposable copies and worktrees under `<scratchpad>/rev_c11/`. The reviewed worktree `c11led` was not modified (clean, still at `9f1d7560`). FIFOs and symlinks were created only inside those copies.

## Verdict: ACCEPT WITH CONDITIONS

The change is a real improvement and has no regression. `ledger/HEAD`, `ledger/manifest.jsonl`, entry files and decision/review records are now read safely, and the ledger stays at version 0.

**Condition before merge (C11-01):** a FIFO at `frozen_inputs.json` still blocks `verify` and `build` indefinitely. The document and the PR body both say this file is covered. Fix the three remaining reads, add tests, and correct the document. The P3 items can be batched in the same commit.

## What was confirmed

| Claim | Result |
| --- | --- |
| FIFO at `ledger/HEAD` or `ledger/manifest.jsonl` no longer hangs | Confirmed. CLI `verify` exits rc 2 in 0.07 s with `not a regular file (mode prw-r--r--)`; `build --as-of 0` likewise. On the base both hang (rc 124 under `timeout 15`). |
| Directory at `ledger/HEAD` | rc 2, `LedgerError` (base: `IsADirectoryError` traceback, rc 1). |
| Symlinked `HEAD` / manifest with identical content | rc 2 (base: rc 0). |
| Strict walk of `ledger/` and `decisions/` | Stray FIFO, socket, file, nested directory, dangling symlink and extra hard-link name are all rc 2. |
| Version 1 and later (my probes, not in the PR's tests) | Symlink, FIFO or directory at `ledger/v0001.csv`, `decisions/D-v0001.md` or `decisions/R-v0001.md`: all `LedgerError`, no hang. |
| 15 new tests, 11 fail on unfixed code | Confirmed: new test file on base code gives 9 failures and 2 errors among the 15; the other 4 pass. |
| 241 ledger tests | 241 OK on Python 3.11.18 and on the venv (3.13.18). Base: 218. |
| Wider regression | `test_legal_audit_*`: 651 OK. Local gate on a clean checkout of `9f1d7560`: 30 of 30 checks. GitHub check `audit-kit-tests`: success. |
| Ledger at version 0 | `ledger/HEAD` = `0 443c4bdf348b2a1bcd603d2701f097aa90a8155efd43c10760f5fd86c76c6b6b`, one manifest line. Git trees of `ledger/` (`b49b5009`) and `effective/` (`6e16f82d`) are identical at `21e73b83`, `2ba7b0a4` and `9f1d7560`. `decisions/`, `frozen_inputs.json`, `schema/` and `evidence/` are untouched. |
| Protected hashes | `records_658` `9a8f0d19…`, `cases_53` `8b8d53cd…`, CALIBRATION-02 register `cfe5f408…`: unchanged. |
| Added warnings come only from `build_registers.py:455` | Confirmed against the real base: 13 more `ResourceWarning`s, every one at `SOURCE-LIBRARY-C5/tools/build_registers.py:455`. See C11-04 for the baseline figure. |

## Findings

| id | severity | statement | evidence | requested action |
| --- | --- | --- | --- | --- |
| C11-01 | P2 | A FIFO at `frozen_inputs.json` still blocks `verify` and `build` forever. `FILE_TYPE_HARDENING_C11.md` ("Covers … `frozen_inputs.json`") and the PR body say the file is covered. Only the hash in `apply_ledger` (`ledger.py:571`) was converted, and three unsafe reads run before it. A directory there raises a raw `IsADirectoryError` from the library (the CLI maps it to rc 2), not a `LedgerError`. | CLI on a disposable copy: `mkfifo frozen_inputs.json` → `verify` rc 124 and `build` rc 124 under `timeout 15`. `faulthandler` stack: `common.sha256_file` ← `reader.frozen_builder` (`reader.py:48`) ← `effective_state` ← `verify`. The other two reads are `pins.py:65` and `reader.py:53`. Same hang through `CLI.verify` on a `Synthetic` root. Reverting `ledger.py:571` to `sha256_file` fails no test (mutant M9). | Read `frozen_inputs.json` through `read_regular_bytes` at `reader.py:48`, `reader.py:53` and `pins.py:65`. Add tests for a FIFO, a symlink and a directory at that path. Correct the document. |
| C11-02 | P3 | Other reads reachable from `verify` and `build` can still block. (a) Any of the 76 pinned frozen inputs as a FIFO: `pins.verify` screens with `is_file()`, but then `pins.current()` hashes every listed path. (b) `schema/ledger_entry.schema.json` is read at import (`ledger.py:26`), outside the CLI `try`, and is not pinned. Pinned inputs reached through a symlink are accepted when the hash matches. All pre-existing and outside the wording of CA-01, but not listed under residual risks. | FIFO at `evidence/copy_facts.csv` and at `CALIBRATION-02/registers/source_authentication_register.csv`: rc 124, stack `pins.current` (`pins.py:55/59`) ← `pins.verify:73`. FIFO at the schema: rc 124, stack `ledger.py:26`. Symlinked `copy_facts.csv` with equal content: rc 0. | Either screen pinned paths with `lstat` before hashing and read the schema safely, or list these as residual risks in the document. |
| C11-03 | P3 | Several new guards are not pinned by any test. 10 of 15 mutants pass all 241 tests. Behaviour is correct today (my probes), but a later edit could remove these guards unnoticed. | Survivors: M1 drop `O_NOFOLLOW` (the symlink tests pass through the final walk instead; `build` has no walk); M4–M8 plain reads for record parsing, record hash, entry-file hash, pinned-record hash and header; M9 (see C11-01); M10 `head_value`; M12 symlinked-directory test in the walk (matters for a symlinked accounted subfolder of `decisions/`); M14 `OSError` removed from the CLI handler. M15 (`followlinks=True`) is equivalent. Killed: M2, M3, M11, M13. | Add: a direct `read_regular_bytes` symlink test; version-1 tests with a symlink and a FIFO at the entry file and at a D-/R- record; a symlinked `decisions/sub/`; one test through `main()` that asserts rc 2. |
| C11-04 | P3 | Documentation and PR-body accuracy. (a) "Warning lines rose from 188 to 248": 188 was measured at `4770c165`, not at this PR's base. From `2ba7b0a4` the figure is 222 → 248. (b) "Every `OSError` becomes a `LedgerError`" holds only inside `read_regular_bytes`. (c) "Every ledger, decision and review file is read through `read_regular_bytes`": the entry CSV is still parsed with `common.read_csv` (stated under residual risks, so the opening sentence overstates). | My gate: base 222 warning lines, head 248; the 26 added lines are 13 warnings at `build_registers.py:455`. Older log `gate_c10al.txt` (188 lines) is headed `HEAD 4770c165`, 607 tests. | Correct the three statements. |
| C11-05 | P3 | `getattr(os, "O_NOFOLLOW", 0)` and `getattr(os, "O_NONBLOCK", 0)` fall back to 0 silently, so on a platform without them the protection disappears without notice. | `ledger.py:82`. | Fail closed when either flag is missing, or state that the tool is POSIX-only. |
| C11-06 | INFO | After this PR merges, the TXN-DEMO expected values must be regenerated again, as the PR body says. The change is behaviour-neutral for the demo. | My scratch merge of `0fbd3400` + `9f1d7560` (clean auto-merge of the test file): `verify` rc 0 at version 0; 242 ledger tests OK; TXN-DEMO `--check` fails on the same 22 tool- and commit-derived keys with 19 PASS and 0 FAIL. | Regenerate in the integration commit. |
| C11-07 | INFO | The author's gate log for this PR is headed with the base commit, so it does not by itself show which tree was tested. | `gate_c11led` line 1: `HEAD 2ba7b0a4`. My gate on a clean `9f1d7560` checkout reproduces 30/30, 651 tests, 248 warning lines. | None; cite a gate run made on the committed head next time. |
| C11-08 | INFO | CA-04 is as documented: an absent `decisions/` (or absent `decisions/README.md`) passes at version 0. | CLI rc 0 for both; pinned by `test_absent_decisions_dir_passes_at_version_zero`. | None. |

## Not checked
- Behaviour on non-POSIX platforms, and as a non-root user (the sandbox runs as root, so permission-denied paths could not be exercised).
- Device nodes: none was created or touched.

## Evidence files
Under `<scratchpad>/rev_c11/`: `scripts/mut.sh` (CLI probes), `scripts/extra44.py` (version-1 probes), `scripts/mut44.py` and `logs/mut44.txt` (mutants), `logs/pr44_al_311.log`, `logs/pr44_al_313.log`, `logs/pr44base_al_311.log`, `logs/gate_wt44.txt`, `logs/gate_wt44base.txt`.
