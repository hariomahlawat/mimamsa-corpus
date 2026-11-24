# Independent review: PR #45, Cycle 11 integration candidate (#40 + #41 + #42 + #43) with TXN-DEMO regeneration

- **Reviewer:** Fable 5.2 (`claude-fable-5-2`), independent technical review, 2026-11-24.
- **Reviewed:** branch `claude/c11-integration-candidate`, head `0fbd3400` (tree `2e35b330`), base `legal-knowledge/v2.5-staging` `21e73b83`.
- **Scope:** merge construction, the regeneration commit, tests and builders on the combined tree. No legal content was judged.
- **Method:** merges were recreated in a separate `--shared` clone; tests and builders ran in disposable worktrees under `<scratchpad>/rev_c11/`. The reviewed worktree `c11int` was not modified (clean, still at `0fbd3400`).

## Verdict: ACCEPT

Every claim in the PR was reproduced. The findings are two P3 documentation and process items and do not block. This is a technical verdict on the evidence; merging still needs the owner's integration approval, as the PR says.

## What was confirmed

**Merges.** I recreated the four merges in order with `git merge-tree --write-tree`. Each of my tree ids equals the candidate's:

| Step | Merged head | Candidate commit | Tree (mine = candidate) | Conflicts |
| --- | --- | --- | --- | --- |
| 1 | #40 `e4d59196` | `63158932` | `c0eb68e6` | none |
| 2 | #41 `a61c0e57` | `1717f4b3` | `e730b81c` | none |
| 3 | #42 `2ba7b0a4` | `dc973b24` | `917f8bcf` | none; `tests/test_legal_audit_auth_ledger.py` auto-merged |
| 4 | #43 `554c46cc` | `f10a25b2` | `670f4730` | none |

- Each candidate merge has exactly two parents: the previous step and the named head. All four heads branch from `21e73b83`.
- **No content altered.** Across all 1,291 paths of `f10a25b2`, every blob equals the blob of the single branch that changed it, or the base blob. The only exception is `tests/test_legal_audit_auth_ledger.py`, the one path touched by two branches (#41 and #42).
- **The merged test file holds both sides.** It has 211 tests in 28 classes (base 189; #41 adds 1; #42 adds 21). No test or class name from either side is missing, none is duplicated, and the diff from #42's file to the merged file is exactly #41's 8-line addition.

**Regeneration commit `0fbd3400`.** It touches three files only, all in `C9-LEGAL-EVIDENCE/TXN-DEMO/`.

- `--check` on the candidate: **CHECK OK, 43 values, transcript compared**, on the venv (3.13.18) and on Python 3.11.18. The package's own unittest wrapper: 2 tests OK.
- `--check` on `f10a25b2` (before regeneration) fails on exactly 22 values plus the transcript, as claimed.
- 22 of 43 values changed and 21 are identical. The 22:
  - `source_package_tools_sha256`: 2 of 9 files, `auth_ledger.py` and `ledger.py`, the two tool files #42 changes;
  - `commit.genesis`, `commit.v0001.merge`, `commit.v0001.reviewed_head`, `commit.v0002.head`, `commit.v0002.merge`, `commit.v0003` … `commit.v0008` (11 keys);
  - `ledger.HEAD.final`, `ledger.manifest_sha256.final`;
  - `cli.verify.v2` … `cli.verify.v8` and `cli.verify.final` (8 keys).
- **Each is tool- or commit-derived** (demo code inspected):
  - The genesis commit of the temporary repository contains the copied tool files, so its id changes, and every later commit id chains from it.
  - BIND lines carry `reviewed_head` and `merge_commit`, so the manifest chain and HEAD change from version 2 on. `cli.verify.v0` and `cli.verify.v1` are unchanged, which fits: no commit id enters the chain before the first BIND.
  - The eight changed `cli.verify.*` outputs differ only in the 64-hex HEAD value.
- **Behaviour is unchanged.** All nine `asof.N` effective-state values, both `cli.build.*`, all seven negative cases and `real_ledger.HEAD` are identical. Old and new transcripts are identical once hex ids are masked. 19 PASS, 0 FAIL in both.

**Tests on the combined tree.**

| Run | Result |
| --- | --- |
| venv 3.13, `unittest discover -s tests` | 689 OK |
| venv 3.13, pytest (`-o pythonpath=tests`) | 811 passed, 1 skipped |
| Python 3.11, `unittest discover -s tests -p "test_legal_audit_*.py"` (the CI command) | 677 OK, 4 skipped (PyMuPDF and jsonschema are not installed for the system 3.11) |
| Python 3.11, `unittest discover -s tests` (all) | 6 crawler modules cannot import `httpx` on the system 3.11; environment only, see I-04 |
| Local gate on a clean `0fbd3400` checkout | 31 of 31 checks |
| GitHub check `audit-kit-tests` on `0fbd3400` | success |

**Builders, all `--check` on the candidate (23 commands, all exit 0; `extract_branch_pins.py` with the documented snapshot, see I-05).**

| Package | Command | Result |
| --- | --- | --- |
| AUTH-LEDGER | `auth_ledger.py verify` | `v0000 ok`, HEAD unchanged |
| AUTH-LEDGER | `tranches/tools/build_tranche1.py`, `policy_impact.py` | reproduce |
| C10-RECONCILIATION | `tools/build_reconciliation.py --repo` | 8 files reproduce |
| C10-RECONCILIATION | `tools/check_dataset_integrity.py --repo` | 2 files reproduce |
| C10 workstream quality | `build_quality_c10.py --repo` | 8 files byte-for-byte |
| C10 workstream statutory | `build_statutory_c10.py` | 9 files |
| C10 workstream judicial | `build_judicial_c10.py --repo /home/user/c7 --c10 … --store <scratchpad>/downloads` | 11 outputs byte-identical |
| C10-HF-JUDGMENTS | `audit_judgments.py assemble --repo` (with `MIMAMSA_WORKING_STORE`) | 14 files reproduce |
| C9-LEGAL-EVIDENCE | `CORRECTIONS/tools/build_corr.py`, also with `--verify-held` | OK; 33 anchors |
| C9-LEGAL-EVIDENCE | `STATUTORY/tools/build_stat_c9.py` | 123 outputs |
| C9-LEGAL-EVIDENCE | `STATUTORY/tools/collect_readings_c9.py`, `extract_branch_pins.py` | OK (pins: see I-05) |
| C9-LEGAL-EVIDENCE | `TXN-DEMO/tools/synthetic_transaction_demo.py` | CHECK OK |
| C9-EVIDENCE-CLEAN | `SC-C9/tools/sim_anchor_c9.py`, `judis_scan.py`, `scr_pinpoint_check.py`, `build_c9_pack.py`, `render_c9.py` | all CHECK OK |
| C9-EVIDENCE-CLEAN | `tools/verify_renders.py` | 40/40 Gazette and 28/28 SC renders match |
| C8-EVIDENCE | `tools/build_packages.py` | 30 files reproduce |

**Protected state.**
- `records_658.jsonl` `9a8f0d19…`, `cases_53.jsonl` `8b8d53cd…`, CALIBRATION-02 `source_authentication_register.csv` `cfe5f408…`: unchanged. The whole `legal_knowledge/curated_originals` tree is identical to staging (`6582c165`).
- Ledger at version 0: `ledger/HEAD` = `0 443c4bdf348b2a1bcd603d2701f097aa90a8155efd43c10760f5fd86c76c6b6b`, one manifest line. `ledger/` (`b49b5009`) and `effective/` (`6e16f82d`) trees are identical to staging; `decisions/`, `frozen_inputs.json`, `schema/` and `evidence/` are untouched.
- Against staging the candidate adds 446 files and modifies 12; none of the 12 is a protected file.

## Findings

| id | severity | statement | evidence | requested action |
| --- | --- | --- | --- | --- |
| I-01 | P3 | `TXN-DEMO/README.md` still describes the earlier run: source `21e73b83`, tools tree `22b4e6d7`, "`--check` passes against both". For the values now committed that is false; the tools tree is `8af003bc`. `REGENERATION_C11.md` says it supersedes the paragraph, but the README does not point to it, so the folder holds two contradictory statements. | `README.md` step 1; `TRANSCRIPT.md` line 13 now prints `8af003bc…`; `--check` on a `21e73b83` tools tree would fail. | Update the README paragraph in the regeneration commit, or add one line there that points to `REGENERATION_C11.md`. |
| I-02 | P3 | TXN-DEMO `--check` is in neither CI nor the local gate, so the break after #42 was invisible to both (disclosed by the author). It will break again when #44 merges. | Gate on `f10a25b2`: 31/31 while `--check` fails. My scratch merge of `0fbd3400` + `9f1d7560`: `--check` fails on the same 22 keys, 19 PASS, 0 FAIL. | Add the `--check` (about 55 s) to CI in a reviewed change, or make regeneration an explicit step of the merge checklist. Regenerate again if #44 is integrated. |
| I-03 | INFO | The merge and regeneration claims are confirmed in full: four identical tree ids, no altered content, both sides' tests present, 22 of 43 values changed and all derived, 19 PASS, `--check` OK on two interpreters. | Sections above; `rev_c11/logs/`. | None. |
| I-04 | INFO | Two test-running limits, both pre-existing and unrelated to the merges. Plain `pytest tests` stops at collection because `test_legal_audit_retrospective_deemed.py` imports a sibling module by bare name (the file is already on staging); it passes with `-o pythonpath=tests`. The system Python 3.11 lacks `httpx`, PyMuPDF and jsonschema, so the six crawler test modules could not be run on 3.11 here. | `rev_c11/logs/pr45_pytest_313.log`, `pr45_all_311.log`. | None for this PR. |
| I-05 | INFO | `extract_branch_pins.py --check` passes only with the documented snapshot `c9src` (`2d7c02cf`) as the snapshot argument. It records the snapshot's commit id, so it reports DIFF when given the candidate itself. This is by design, not a regression. | CHECK OK with `<scratchpad>/c9src`; CHECK DIFF with the candidate. | None. |
| I-06 | INFO | PR #44 is not included, as stated. It merges onto this candidate without conflict and does not change demo behaviour. | Scratch merge tree `5451e8a4`; `verify` rc 0; 242 ledger tests OK. | None. |

## Not checked
- The legal content of the four merged packages (reviewed separately at their own heads).
- Crawler tests on Python 3.11 (see I-04); they pass on the venv.

## Evidence files
Under `<scratchpad>/rev_c11/`: `mrg/` (clone used to recreate the merges), `ls_*.txt` (per-commit blob lists), `eh_old.json` and `eh_new.json`, `logs/pr45_builders*.txt`, `logs/pr45_all_313.log`, `logs/pr45_all_311.log`, `logs/gate_wt45.txt`, `logs/txn_pre.log`, `logs/txn_4544.log`.
