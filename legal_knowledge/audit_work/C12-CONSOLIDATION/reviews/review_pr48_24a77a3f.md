# Independent review of PR #48 at head `24a77a3f`

- **PR:** Cycle 12 integration into `legal-knowledge/v2.5-staging`
- **Base:** `21e73b83`
- **Branch:** `claude/c12-integration`
- **Head:** `24a77a3f034a5ec1a4d63adf70d8c5445bc016b9`
- **Reviewer:** independent technical reviewer. I did not build this PR. Review date: 2026-11-24.
- **Method:** disposable `git worktree` copies of `24a77a3f` under `scratchpad/rev48/`. I made no commits, pushes or GitHub comments, and the integrator's worktree was not touched. Every worktree I used was clean (`git status --porcelain` empty) after the runs.

## Verdict: **ACCEPT**

Every claim in the PR holds, and I reproduced each one independently:

- the six merges reproduce tree for tree;
- the single auto-merged file keeps every test from both sides;
- all 22 changed TXN-DEMO values are derived from tool bytes or commit ids, and the other 21 are byte-identical;
- the new CI gate fails on a stale value and on a stale transcript;
- the new test fails when the gate logic is bypassed;
- all suites and every builder `--check` I could run pass on the venv;
- the protected hashes and the ledger are unchanged, at version 0;
- the HF upload jobs cannot fire on this push.

I found no P1 or P2 issues. The P3 items below are non-blocking follow-ups.

## Evidence summary

| # | Check | Result |
| --- | --- | --- |
| 1 | `git merge-tree --write-tree` for each first-parent merge (p1, p2), and an independent re-chain from `21e73b83` through `e4d59196`, `a61c0e57`, `2ba7b0a4`, `bdc23f11`, `554c46cc`, `3980a183` | All six tree ids equal the PR's: `c0eb68e6`, `e730b81c`, `917f8bcf`, `3d4bf7c5`, `1a941527`, `4b95c311`. No conflicts. The merge parents are exactly the claimed heads, in the claimed order. |
| 1b | Blob provenance for every path in `90a542ad` against the base and the six sources | Each path's blob equals the base or the source that changed it. Paths changed by two sources are explained by stacking: `2ba7b0a4` is an ancestor of `bdc23f11`, and `554c46cc` is an ancestor of `3980a183`; the merged blob equals the descendant's. The only true auto-merge is `tests/test_legal_audit_auth_ledger.py`. |
| 1c | `tests/test_legal_audit_auth_ledger.py` | The base has 189 tests. `a61c0e57` adds 1 and `bdc23f11` adds 44 (the 21 from `2ba7b0a4` are included in those). The merged file has 234 = 189 + 1 + 44, with no (class, name) duplicate, none lost, none extra, and none removed. |
| 2a | `expected_hashes.json`, `90a542ad` against `24a77a3f` | The key set is identical (43 keys). Exactly 22 values changed: `source_package_tools_sha256`, 11 `commit.*`, `ledger.HEAD.final`, `ledger.manifest_sha256.final`, `cli.verify.v2`–`v8` and `cli.verify.final`. 21 are byte-identical: `asof.0`–`8`, `cli.build.asof1/2`, `cli.verify.v0/v1`, all 7 `neg.*`, and `real_ledger.HEAD`. |
| 2b | Derivation in the demo code | `source_package_tools_sha256` is the sha256 of each `AUTH-LEDGER/tools/*.py`. The new values equal `sha256sum` of the files at `24a77a3f`; `auth_ledger.py`, `common.py`, `ledger.py`, `pins.py`, `reader.py` and `strength.py` changed via #42/#44. Commits are made with fixed identities and dates, so their ids depend only on tree content, which includes the copied tool bytes. From v2 onward, BIND lines embed merge-commit ids, so HEAD and the `cli.verify` stdout change from v2. v0/v1 carry no commit id and are unchanged, which is consistent. `asof.*` and `neg.*` depend on entries and rules only, and are unchanged. |
| 2c | `TRANSCRIPT.md` diff | Only commit ids, HEAD lines, the tools-tree note (`22b4e6d7`→`84c94fe3`, which equals `git rev-parse 24a77a3f:…/AUTH-LEDGER/tools`), the `git log` line and the ff-only commit id. No behavioural text changed. All 19 `Result:` lines are PASS. |
| 2d | `--check` (`python -I -B … --check`) | python3.11.18: `CHECK OK: 43 recorded values compared; transcript compared` (46 s). Venv (3.13.18): same (47 s). Both left the tree clean. |
| 3a | Negative control: `commit.v0005[0]` set to `f…f` in a disposable copy | rc 1, `CHECK: values differ from expected_hashes.json: commit.v0005`. |
| 3b | Negative control: one character changed in `TRANSCRIPT.md` | rc 1, `CHECK: generated transcript differs from TRANSCRIPT.md`. |
| 3c | Gate bypass: in a copy, `if bad:` changed to `if False and bad:`, then `tests.test_legal_audit_txn_demo_gate` run | FAILED: `AssertionError: 0 == 0`. The test depends on the gate logic. |
| 4a | `python -m unittest discover -s tests -p 'test_legal_audit_*.py'` | python3.11: 732 tests OK (4 skipped: 3 need PyMuPDF, 1 needs jsonschema). Venv: 732 OK, 0 skipped. |
| 4b | `pytest -o pythonpath=tests tests` (venv) | 866 passed, 1 skipped, 18 subtests passed. |
| 4c | Builder `--check` across AUTH-LEDGER, C9, C10 and C11 (27 commands; `MIMAMSA_WORKING_STORE=<scratchpad>`, `--repo /home/user/c7`, judicial `--store <scratchpad>/downloads`) | Venv: 27/27 exit 0, covering `auth_ledger verify`, `build_tranche1`, `policy_impact`, SC-C9 `build_c9_pack`/`judis_scan`/`scr_pinpoint_check`/`sim_anchor_c9`, `build_stat_c9` (123 outputs), `build_corr` (also with `--verify-held`, 33 anchors), C10 `audit_judgments assemble` (14 files), `build_reconciliation` (8), `check_dataset_integrity`, `build_quality_c10`, `build_statutory_c10`, `build_judicial_c10`, and C11 identity, relations, scnum, scnum_reconcile, hf_verify, eval_holdout, holdout_sample, excluded_rank, curated, release_filter and preservation. python3.11: 20/27. Six fail on import (no `pymupdf`/`fitz`/`jsonschema`), and `preservation_c11.py` fails closed (see F-07). |
| 4d | CI on GitHub for head `24a77a3f` | `audit-kit-tests` succeeded in 3 min 18 s, against a 10-minute job timeout. |
| 5 | Protected hashes and ledger | `records_658` `9a8f0d19…fcc1`, `cases_53` `8b8d53cd…f89a`, CALIBRATION-02 register `cfe5f408…1ece`: all match, and CALIBRATION-02 has no diff against staging. `auth_ledger.py verify`: `HEAD 0 443c4bdf…c76c6b6b; frozen pins ok; ledger verified`. `git diff 21e73b83 24a77a3f -- AUTH-LEDGER/ledger AUTH-LEDGER/effective`: empty. |
| 6 | HF sync workflow | `sync-legal-knowledge-hf.yml` is unchanged against staging. The `upload` job requires `github.event_name == 'workflow_dispatch'` and the approval phrase. `upload_abbreviations` requires a push whose head commit message contains `[abbreviations-hf]`. No commit message in `21e73b83..24a77a3f` contains it (grep count 0, case-insensitive), and neither does the PR title or body. |
| 7 | CI YAML | `yaml.safe_load` parses both workflows. The new step runs after AUTH-LEDGER verify, under `actions/setup-python@v5` with python 3.11, with no pip install. The demo imports only stdlib plus the copied AUTH-LEDGER package and needs `git`. It passed locally on python3.11 without extra deps (that interpreter lacks httpx, pytest, pymupdf and jsonschema), and in the actual CI run. |

## Findings

| ID | Severity | Statement | Evidence | Requested action |
| --- | --- | --- | --- | --- |
| R48-01 | INFO | All six merges reproduce exactly, are conflict-free and are in the claimed order. | Item 1: merge-tree tree ids equal for every merge and for an independent re-chain from base. | None. |
| R48-02 | INFO | The only auto-merged file, `tests/test_legal_audit_auth_ledger.py`, keeps both sides' tests, with none lost or duplicated. Every other path equals its source or the base. | Items 1b and 1c: 234 = 189 + 1 + 44; per-path blob provenance. | None. |
| R48-03 | INFO | The TXN-DEMO regeneration is sound. All 22 changes are derived from tool bytes or commit ids, and the 21 other values and all behavioural results are unchanged. | Items 2a–2d. | None. |
| R48-04 | INFO | The new CI gate and the new test are effective negative controls. | Items 3a–3c. | None. |
| R48-05 | P3 | The docstring of `tests/test_legal_audit_txn_demo_gate.py` says "the committed values must pass", but the file has only the stale-value test. The positive path is covered only by the separate CI step and the local gate. | `test_legal_audit_txn_demo_gate.py` has one test method, `test_stale_expected_value_fails_the_gate`. | Add a positive test with an unmutated copy (rc 0), or correct the docstring. A positive test would cost about 46 s more per suite run, so correcting the docstring is acceptable. |
| R48-06 | P3 | CI now runs the full synthetic demo twice: once as the new step, and once inside the unittest step through the gate test, about 45 s each. The run took 3 min 18 s against `timeout-minutes: 10`, which is fine today, but headroom shrinks with every further ledger test. | `legal-audit-kit-ci.yml` line 47 plus the gate test; check run 138372448231. | Optional: watch the CI duration; consider marking the gate test slow or skipping it when the CI step has already run. |
| R48-07 | P3 (pre-existing, not introduced by this PR) | Without PyMuPDF, `C11-JUDICIAL-QUALITY/tools/preservation_c11.py --check` silently skips the printed-marking scan and then reports `CHECK FAILED: PRESERVATION_INVENTORY.csv, MARKING_SCAN.csv, PRESERVATION_SUMMARY.json`, not a missing-dependency error. It fails closed, but the message points away from the real cause. | python3.11 run (no pymupdf); the venv passes. The blob `9dc333da` is identical at `3980a183` and `24a77a3f`. | Follow-up in C11: fail explicitly ("PyMuPDF required") when `pymupdf` is missing. |
| R48-08 | INFO | CI installs no requirements, so the PyMuPDF and jsonschema tests skip on CI: 3 in `test_audit_judgments` and 1 in `test_build_reconciliation`. The C9, C10 and C11 builders are not in CI. This predates the PR. | Item 4a: skip reasons on python3.11. | None for this PR. Keep running the builder `--check` set locally with the venv at each integration; I ran it here (27/27). |
| R48-09 | INFO | The integrator's local gate (32 checks) covers no C9, C10 or C11 builder `--check`, so I ran them separately. | Item 4c. | Optional: add the store-dependent builders to the local gate script. They cannot go in CI because they need the working store and `/home/user/c7`. |
| R48-10 | INFO | Builders not run, because they need inputs outside the tree: `render_c9.py` (held manifest and render dirs), `extract_branch_pins.py` (documented snapshot plus refs; by design it reports DIFF against a non-snapshot tree) and `collect_readings_c9.py` (raw-data git). `docs_c9.py` has no `--check`. Their files are byte-identical to the reviewed source branches, and they do not read AUTH-LEDGER tools. | Item 1b provenance. | None. |
| R48-11 | INFO | The README pointer is correct. `REGENERATION_C12.md` cites `REGENERATION_C11.md`, which exists only on the superseded PR #45 and not in this tree. | `git ls-tree 24a77a3f …/TXN-DEMO/`. | Optional wording: "on PR #45 (not merged)". |
| R48-12 | INFO | Merging will start a run of the HF sync workflow (push to staging touching `legal_knowledge/**`), but both jobs evaluate to skipped. | Item 6. | Do not put `[abbreviations-hf]` in the merge commit message. After merge, confirm that both jobs show as skipped, as the PR already plans. |
| R48-13 | INFO | The protected hashes are unchanged and the ledger is at version 0; `ledger/` and `effective/` are identical to staging. | Item 5. | None. |
