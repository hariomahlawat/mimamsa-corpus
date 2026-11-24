# Final narrow confirmation: PR #50 at `3935c35e`

The work was read-only and nothing was edited in c12w or the register.

## Verdicts
| Finding | Verdict | Evidence |
| --- | --- | --- |
| **R50C-02** (P2) | **CLOSED_VERIFIED** | Live check against HF (`tools/live_guard2.py` and `tools/live_guard.py`, with `hf_protect` at `3935c35e`) under both library versions, huggingface_hub 0.36.0 (`venv`) and 2.4.0 (`venv_hf24`). Results: a missing folder returns `{}` (2.4.0 raises `RemoteEntryNotFoundError`, which is matched); a missing revision raises `RevisionNotFoundError`; a missing repo raises `RepositoryNotFoundError`. Identical bytes pass. Modified bytes are caught for non-LFS, LFS, preservation, and a file deep in a 1,121-entry directory, under 2.4.0 too. The new test uses the real library classes. |
| **R50C-03** (P3) | **CLOSED_VERIFIED** | Mutation rerun on `3935c35e` (`tools/mut3.py`) killed 23 of 25 under both versions. The earlier survivors (#16 NEVER_SYNC_PATTERNS, #17 preservation exclusion, #22 unpinned legal_knowledge guard) are now killed. Two remain. #13 (skipping folder entries) is harmless. #24 (checking only the exception's own class instead of its MRO) behaves identically for the real 0.x/1.x/2.x classes. |
| **R50C-01** (P2) | **CLOSED_VERIFIED** | The register now shows R50-01..10 as CLOSED_VERIFIED, citing the confirmation record. The author had already marked R50C-01 CLOSED_VERIFIED before this check; this review confirms it. |

## Combined-tree gate
The scratch clone merged `3935c35e` into staging `e0b3e7d2` with no conflicts; the merge commit is `a94ce600`.

Results:
- **Steps:** 31 of 32 exited 0.
- **Tests:** 754 ran, with 1 failure and 5 skipped. The workflow-guard tests passed (12).
- **The single failure is the expected one.** It is `test_deferred_set_matches_findings_register`, and the only extra item is `R50C-02`, because the register still records it as `CLOSED_BY_AUTHOR_UNCONFIRMED`. The test is working as intended. Once the register records R50C-02 (and R50C-03) as CLOSED_VERIFIED, citing this record, the gate should go back to 32/32.
- **Everything else passed:** the protected hashes (records_658, cases_53, CALIBRATION-02) are OK; AUTH-LEDGER HEAD is `0 443c4bdf…`; TXN-DEMO `--check` exits 0; and no workflow change can trigger an HF upload.

**No new P1 or P2.**
