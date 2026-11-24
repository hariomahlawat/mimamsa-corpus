# Narrow confirmation review: PR #44 delta `9f1d7560..bdc23f11` (AUTH-LEDGER file-type hardening, C11)

- **Reviewer:** Fable 5.2 (`claude-fable-5-2`), independent technical review, 2026-11-24.
- **Reviewed:** branch `claude/c11-ledger-fifo-hardening`, head `bdc23f11` (tree `dc7c496f`), one commit on top of `9f1d7560`.
- **Scope:** the delta only, against `review/DISPOSITIONS_9f1d7560.md`. Code, tests and documentation accuracy; no legal content.
- **Method:** my own probes, mutants and test runs in disposable copies and worktrees under `<scratchpad>/rev_c11/`. The reviewed worktree `c11led` was not modified (clean, at `bdc23f11`).

## Verdict: ACCEPT

The P2 condition (C11-01) is closed, and C11-02, C11-04 and C11-05 are fixed as stated. C11-03 is fixed in part: two of the three test gaps are closed, and the version-1 tests do not pin what the disposition says they pin (CB-01, P3). Nothing found blocks the merge. This is a technical verdict; merging still needs the owner's approval.

## Disposition check

| Earlier finding | Claimed | Result |
| --- | --- | --- |
| C11-01 (P2) FIFO at `frozen_inputs.json` hangs | Fixed | **Confirmed.** CLI on a disposable copy: FIFO → `verify` rc 2 in 0.07 s and `build` rc 2 in 0.07 s; directory → rc 2 `LedgerError`; symlink → rc 2. Same through `CLI.verify` and `reader.effective_state` on a `Synthetic` root. |
| C11-02 (P3) pinned inputs and schema | Fixed; schema import a stated residual | **Confirmed.** FIFO at each of 8 pinned inputs I tried → rc 2 in under 0.1 s (list below). FIFO at the schema → rc 1 `LedgerError` traceback in 0.08 s, no hang, as the document states. A pinned input reached through a symlink is now refused (rc 2); at `9f1d7560` it was accepted. |
| C11-03 (P3) unpinned guards | Fixed (tests) | **Partly.** `O_NOFOLLOW` and the CLI `OSError` handler are now pinned (mutants M1 and M14 die). The version-1 guards are still unpinned: see CB-01. |
| C11-04 (P3) wording | Fixed | **Confirmed.** The document no longer says "every `OSError`"; the PR body gives 222 warning lines at the base and 274 at the head, which my gate reproduces (274). Two small wording slips remain: CB-02. |
| C11-05 (P3) silent fallback | Fixed | **Confirmed.** Without `O_NOFOLLOW` or `O_NONBLOCK` the reader raises `LedgerError`; the test kills the mutant that removes the check. Only the `O_NOFOLLOW` half is tested (CB-01). |

Pinned inputs probed with a FIFO, all rc 2: `AUTH-LEDGER/evidence/copy_facts.csv`, `CALIBRATION-02/registers/source_authentication_register.csv`, `SOURCE-LIBRARY-C5/tools/build_registers.py`, `CALIBRATION-02/tools/evidence_classification.py`, `PILOT-01/sources/judgment-auditor.json`, `SOURCE-LIBRARY-C5/registers/source_copy_register.csv`, `curated_originals/case_law/v0.9/cases_53.jsonl`, `curated_originals/knowledge_base/v0.9/records_658.jsonl`. `ledger/HEAD`, `ledger/manifest.jsonl` and `effective/v0000/OUTPUT_MANIFEST.json` remain rc 2.

## Regression checks

| Check | Result |
| --- | --- |
| Ledger suite | 272 OK on Python 3.11.18 (unittest), on the venv 3.13.18 (unittest) and on the venv with pytest (272 passed). |
| Wider suite | `test_legal_audit_*`: 682 OK. Local gate on a clean `bdc23f11` checkout: 30 of 30 checks. GitHub check `audit-kit-tests`: success. |
| Ledger at version 0 | `verify` prints `v0000 ok`; HEAD `0 443c4bdf348b2a1bcd603d2701f097aa90a8155efd43c10760f5fd86c76c6b6b`. Git trees of `ledger/` (`b49b5009`) and `effective/` (`6e16f82d`) are unchanged; no diff in `decisions/`, `frozen_inputs.json`, `schema/`, `evidence/` or `curated_originals`. |
| Other users of the shared readers | On a scratch merge with the integration candidate `0fbd3400` (clean auto-merge): `verify` rc 0; `build_tranche1.py --check`, `policy_impact.py --check` and `sim_anchor_c9.py --check` all reproduce. |
| TXN-DEMO on that merge | 19 PASS, 0 FAIL; `--check` fails on the same 22 tool- and commit-derived keys as before, so one regeneration is still needed at integration. |
| Committed copies of my earlier review | `review/fable_review_pr44_9f1d7560.md` and its CSV are byte-identical to the files I wrote. |

## Mutants re-run (25 on `bdc23f11`, 272 tests each)

- **Killed (8):** M1 drop `O_NOFOLLOW`; M2 drop `O_NONBLOCK`; M3 drop `fstat` check; M14 `OSError` out of the CLI handler; N1–N3 `sha256_file`, `read_csv`, `load_json` made unsafe; N11 fail-closed check removed. M1 and M14 survived at `9f1d7560`.
- **Survived, redundant behind an earlier safe read of the same path (11):** M4 record parse, M8 header, M9 `apply_ledger` frozen hash, M10 `head_value`, N4 `reader.py` pin map, N5 `pins.verify`, N6 frozen-code exec read, N7 strength evidence JSON, N8 and N9 effective outputs, N10 frozen C5 registers. Each is preceded by a safe hash or walk of the same file. Removing one changes behaviour only under a concurrent swap. These are defence in depth; no action needed.
- **Survived, not redundant (6):** M5, M6, M7, M12, N12, N13. See CB-01.

## Findings

| id | severity | statement | evidence | requested action |
| --- | --- | --- | --- | --- |
| CB-01 | P3 | C11-03 is only partly closed. The two version-1 tests use a FIFO, which `is_file()` rejects before the safe read is reached, so they pass with the safe read removed and would also have passed at `9f1d7560`. The guard that matters there is the symlink refusal, and it has no test. Also untested: the symlinked-directory branch of the walk, the `O_NONBLOCK` half of the fail-closed check, and the schema read. Behaviour is correct today on all of these (my probes). | Mutants M5 (record hash), M6 (entry-file hash) and M7 (pinned-record hash) made unsafe: 272 tests still pass. M12, N12 and N13 also survive. My probes on a `Synthetic` version-1 root: a symlink with identical content at `ledger/v0001.csv`, `decisions/D-v0001.md` or `decisions/R-v0001.md` is refused with `cannot open as a regular file`. | Add version-1 tests with a symlink (identical content) at the entry file and at a D- and an R- record, asserted through `reader.effective_state`; optionally a symlinked `decisions/sub/` and a missing-`O_NONBLOCK` case. Can be batched with the next change; not a merge condition. |
| CB-02 | P3 | Two wording slips. (a) The disposition for C11-01 says `ledger.py` reads `frozen_inputs.json` "via `sha256_file`"; the code uses `sha256_regular` (`ledger.py:539`), which is equally safe. (b) In `FILE_TYPE_HARDENING_C11.md` the sentence "Against the unfixed code, 11 of the new tests fail" now sits in the `C11VersionOneFileTypes` bullet, though it describes the first 15 tests. | `ledger.py:77-79, 539`; document "Tests" list, third bullet. | Correct both in the next documentation touch. |
| CB-03 | INFO | C11-01 (P2) is closed and no regression was found: 272 ledger tests on both interpreters, 682 audit tests, gate 30/30, ledger at version 0 with unchanged trees. | Sections above; `rev_c11/logs/pr44b_*.log`, `gate_wt44b.txt`. | None. |
| CB-04 | INFO | Behaviour change to note for operators: the 76 pinned inputs, the frozen code files and the schema must now be regular files; a symlink at any of them fails `verify` even when the content hash matches. This is stricter than `9f1d7560` and consistent with the document. | Symlinked `evidence/copy_facts.csv`: rc 0 at `9f1d7560`, rc 2 at `bdc23f11`. | None. |
| CB-05 | INFO | The schema read at import remains outside the CLI `try`: a special file there gives rc 1 with a traceback rather than rc 2. Stated as a residual risk in the document. | FIFO or symlink at `schema/ledger_entry.schema.json`: rc 1, `common.LedgerError`, 0.08 s. | None required; moving the read inside `main()` would make it rc 2. |

## Not checked
- Non-POSIX platforms and non-root permission failures (the sandbox runs as root).
- Device nodes: none created or touched.

## Evidence files
Under `<scratchpad>/rev_c11/`: `scripts/mut44b.py` and `logs/mut44b.txt` (mutants), `scripts/extra44.py` (version-1 probes), `logs/pr44b_al_311.log`, `logs/pr44b_al_313.log`, `logs/pr44b_al_pytest.log`, `logs/gate_wt44b.txt`, `logs/txn_4544b.log`.
