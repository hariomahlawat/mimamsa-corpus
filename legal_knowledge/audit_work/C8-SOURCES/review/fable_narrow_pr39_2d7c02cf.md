# Narrow review: PR #39 head 2d7c02cf and its integration with staging

RESEARCH ONLY. Technical check of the final commit (`git diff 0e75a4a3 2d7c02cf`) and of the local combined candidate 2a5707a4 (staging ff425a9a + PR #38 head 562a55ef + 2d7c02cf). It is not a fresh full review and not a legal sign-off; it approves no record, source or rule. A hash match proves integrity only, not authenticity, currency or legal correctness.

- Both worktrees were read-only and are clean after the runs. All runs used a local clone of the combined candidate inside a `mktemp -d` directory under `c9rev39_tmp/`, since removed.
- No network. The canonical private HF snapshot was not accessed: coverage against it is unknown.
- No tool experiment on the output guard was run: the tool and its test file are byte-identical to 0e75a4a3.

## 1. Final diff (0e75a4a3..2d7c02cf, 9 files)

| File | Change | Class |
| --- | --- | --- |
| `CORPUS-QUALITY/work/build_hr.py` | 2 literal strings (HCE-010, COI-046 dependency cells) | wording |
| `CORPUS-QUALITY/high_risk_record_review.csv` | the same 2 cells; nothing else differs (word diff) | regenerated |
| `CORPUS-QUALITY/OUTPUT_SHA256SUMS` | 1 line (the CSV above) | regenerated |
| `CORPUS-QUALITY/tools/README.md` | test count 44 to 47; guard rules and limits | wording |
| `CORPUS-QUALITY/work/unittest_output.txt` | 3 test lines added; "Ran 47 tests" | regenerated |
| `review/DISPOSITIONS_44fd72d6.md` | RC-03, RC-06 status cells | wording |
| `review/DISPOSITIONS_0e75a4a3.md`, `review/fable_confirm_c8_sources_0e75a4a3.md`, `_findings.csv` | new | review record |

- No tool logic changed: `reconcile_judgments.py`, `xref_checks.py`, `select_sample.py`, `build_c8_d.py`, `build_cp.py`, `build_findings.py` and `tests/test_legal_audit_reconcile_judgments.py` are not in the diff.
- No status, date, citation or proposal was added. `correction_proposals.csv` is unchanged.

**Gap text against ARMY-RULES-CHAIN-01.**

- Instrument register: AR-001 NOT_FOUND / GAP; AR-030 NOT_FOUND / GAP; AR-036 NOT_SEARCHED_AUTHORITATIVELY / GAP; AR-012, AR-013, AR-015 HINT_ONLY / TO_CHECK.
- Chronology r.23: "NO AMENDMENT LOCATED (31 instruments examined; gaps AR-001, AR-030, AR-036, hints AR-012/013/015)".
- HCE-010 now reads "gaps AR-001, AR-030, AR-036; unopened hints AR-012, AR-013, AR-015". This matches.
- COI-046 now reads "gaps AR-001, AR-030, AR-036, plus unopened hints AR-012, AR-013, AR-015 (... instrument register: NOT_FOUND / NOT_SEARCHED_AUTHORITATIVELY)". The ids match; see N-01 for the label and scope.

## 2. Combined candidate 2a5707a4

| Check | Result |
| --- | --- |
| Conflict markers in tracked files | none |
| `C8-SOURCES/` tree at 2a5707a4 vs 2d7c02cf | identical (tree 56d0a9b4 both) |
| `tests/test_legal_audit_reconcile_judgments.py` vs 2d7c02cf | identical |
| Files added by this merge over staging + #38 (1b20a16c) | 52, all additions, all under `C8-SOURCES/` or the one test file |
| `build_c8_d.py . --check` | OK (16 files reproduce) |
| `build_c8_d.py . --check --verify-held <scratchpad>` | OK (67 hashes, 22 page readings, 6 derived readings) |
| `build_hr.py`, `build_cp.py`, `build_findings.py` `. --check` | OK (33 / 24 / 23 rows) |
| `sha256sum -c OUTPUT_SHA256SUMS` | CORPUS-QUALITY 6 of 6 OK; PRIMARY-SOURCES 15 of 15 OK |
| `python -m unittest tests.test_legal_audit_reconcile_judgments` | 47 tests OK (also 47 OK run from `tools/`) |
| `python -m unittest discover -s tests -p "test_legal_audit_*.py"` | 599 tests OK, 5 skipped (no `origin/raw-data` ref) |
| Same, with `origin/raw-data` set in the copy to the CI pin ad77758d | 599 tests OK, 0 skipped |
| `tools/legal_audit/check_csv.py` | csv_files=229 errors=0 |
| `tools/legal_audit/check_provenance.py` | files=229 violations=2 known=2 new=0 baseline_absent=1 |
| `AUTH-LEDGER/tools/auth_ledger.py verify` | ledger verified; frozen pins ok |
| `ARMY-RULES-CHAIN-01/check_registers.py` | errors=0 |
| `tools/legal_audit/validate.py --schema-check` | OK |

The copy was clean (`git status`) after every run.

## 3. Proposals and protected paths

- `correction_proposals.csv`: 24 rows; status is PROPOSAL_NOT_APPLIED (20) or UNVERIFIED_LEAD_NO_PROPOSAL (4). No approval state.
- `records_658.jsonl` sha256 9a8f0d19..., `cases_53.jsonl` 8b8d53cd...: the same at 1a21a2e8, ff425a9a, 2d7c02cf and 2a5707a4.
- `CALIBRATION-02/registers/source_authentication_register.csv` sha256 cfe5f408... at 2a5707a4, as pinned in `AUTH-LEDGER/frozen_inputs.json`.
- staging..2a5707a4 touches only `C8-SOURCES/`, `AUTH-LEDGER/` and `tests/`. Nothing under `data/`, `curated_originals/`, `schema/`, `pipeline/`, `crawler/`, `.github/` or `CLAUDE.md`.

## 4. Scope and hygiene

- 1a21a2e8..2d7c02cf: 52 files, all added, all under `legal_knowledge/audit_work/C8-SOURCES/` or `tests/test_legal_audit_reconcile_judgments.py`.
- No `/tmp/claude`, `scratchpad/`, `/home/user` or `/root/` string under those paths at 2d7c02cf.
- No PDF, image or source-text dump. The only `.txt` file is `work/unittest_output.txt` (test names and a count).

## 5. Findings

| ID | Sev | Finding |
| --- | --- | --- |
| N-01 | P3 | COI-046: the parenthetical still gives only "NOT_FOUND / NOT_SEARCHED_AUTHORITATIVELY", which does not describe the three hints now listed (HINT_ONLY). COI-046 is a whole-chain statement, and the register holds 13 HINT_ONLY rows (AR-012, AR-013, AR-015, AR-037 to AR-046); the three named are the ones in the r.23 chronology row. Nothing is overstated, but the list is not the full hint set. |
| N-02 | P3 | C3-01 and C3-03 are recorded as "Fixed" but are part done: the module docstring of `reconcile_judgments.py` still omits the regular-file rule and the in-repo rule (the README now has both), and the README test sentence does not name the three new tests. Both are consistent with the "no tool change" scope of this commit. |
| N-03 | INFO | `DISPOSITIONS_0e75a4a3.md` says the corrections "are batched in the next commit"; they are in the same commit (2d7c02cf). |
| N-04 | INFO | `HIGH_RISK_REVIEW.md` RC-01 paragraph lists the three gaps without the hints. It is a narrative of the earlier correction, not a generated cell. |
| N-05 | P3 (carried, disclosed) | RR-03 remainder stays open: CSV BOM handling and type checks on non-string scalars in the reconciliation tool. |
| N-06 | INFO | Sections 1 to 4: all requested checks pass. |

No P1 or P2.

## 6. Not checked

- The canonical HF snapshot, and anything needing network access.
- The output guard behaviour (unchanged code; covered by the previous confirmation and the 47 tests).
- Any cell of `high_risk_record_review.csv` other than the two changed; any legal proposition.
- The content of PR #38 (AUTH-LEDGER) beyond its gates passing in the combination.
- GitHub CI itself: results are from a local clone with the scratchpad venv, not the workflow's Python 3.11 runner.

## 7. False-pass limits

- `--check` shows outputs reproduce from the builders, not that the hand-entered builder text is right.
- `--verify-held` reads held copies whose hashes match the manifest; that says nothing about authenticity or currency.
- The combined candidate is a local merge. The real merge result depends on the state of staging at merge time; it holds if staging is ff425a9a plus #38 at 562a55ef.

Conditions (none blocks the merge): correct N-01 and N-02 in the next regeneration, and keep N-05 on the open list.

VERDICT: ACCEPT WITH CONDITIONS

Reviewer model: Fable 5.2 (claude-fable-5-2)
