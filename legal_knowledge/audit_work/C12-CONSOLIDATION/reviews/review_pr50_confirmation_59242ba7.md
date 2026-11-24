# Confirmation review: PR #50 findings R50-01..R50-10 at `59242ba7`

**Result: R50-01..R50-10 are all CLOSED_VERIFIED. There are two new P2s (R50C-01, R50C-02), so the PR is not ready to merge until both are fixed.** Findings and evidence: `confirmation_59242ba7_findings.csv`.

The work was read-only. Experiments ran in `rev_pr50/` (`mut2/`, `mut_iso2/`, `dl3864_*`, `hfhub_src/`, and the scripts `tools/live_guard2.py`, `tools/verify_3864.py` and `tools/mut2.py`). Nothing was written to HF or c12w.

## Dispositions confirmed
- **R50-01:** the new prefix is in place. The test covering all 4,103 manifest paths passes, and the mutant that removes the prefix is killed.
- **R50-02:** confirmed live at `3864faf3`. A missing repo or revision now raises, and a new folder still passes. See R50C-02 for newer library versions.
- **R50-03:** parent commits are pinned, and those mutants are killed.
- **R50-04:** 19 of 23 mutants are killed (previously 11 of 19). The 4 survivors are listed in R50C-03.
- **R50-05:** all isolation mutants are killed.
- **R50-06, R50-07, R50-08, R50-10:** the text corrections are visible and attributed.
- **R50-09:** HF `3864faf3` was checked independently:
  - it added 15 files, removed 0, and changed only `.gitattributes`;
  - the dataset is private;
  - all 7 PDF hashes equal the EXCLUDED rows of `INGESTION_LOG.csv`;
  - the package checksums pass, 14 of 14.

## New findings
- **R50C-01 (P2): the gate is red.** The isolation test treats R50-01 as an open P2, because the register still records it as `CLOSED_BY_AUTHOR_UNCONFIRMED`. Fix: record R50-01..R50-10 as CLOSED_VERIFIED, citing this review, then re-run the gate.
- **R50C-02 (P2): the guard breaks on supported library versions.** It matches the error class by its exact name, so it does not recognise huggingface_hub 1.x and 2.x, which raise `RemoteEntryNotFoundError`. CI pins version 1.19 or later, and `requirements.txt` pins 2.4.0. This fails closed, so no data is at risk. But any sync that adds a file under a protected folder not yet on HF will abort. Fix: use `isinstance`, and test against the real library class.
- **R50C-03 (P3):** the residual surviving mutants.

## Combined-tree gate
I merged `59242ba7` into staging `e0b3e7d2` in the scratch clone: no conflicts, merge commit `86a6b291`.
- **Gate: 31 of 32 steps exit 0.** 753 tests ran, with 1 failure (R50C-01) and 5 skipped. The workflow-guard tests pass (12).
- **Unaffected checks all pass:**
  - the protected hashes (records_658, cases_53 and CALIBRATION-02) are OK;
  - AUTH-LEDGER HEAD is `0 443c4bdf…`;
  - TXN-DEMO `--check` exits 0;
  - the only workflow change is the CI path list.
