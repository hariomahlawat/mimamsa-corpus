# Addendum (Cycle 9): dispositions of the narrow review of 562a55ef

The narrow review of PR #38 at `562a55ef`, combined with staging `ff425a9a`, returned **ACCEPT**. PR #38 was then merged at `0fc1f5b4`. Its P3 and INFO items are dispositioned here. The historical records are not edited: `DISPOSITIONS_81df0e6c.md` and the earlier reviews stay as written.

| Id | Severity | Disposition |
| --- | --- | --- |
| F-01 | P3 | **Fixed.** Added `test_n05_existing_unrelated_pwd_is_ignored`, which sets `$PWD` to an existing but unrelated directory and expects `verify` to succeed from the real working directory. A guard weakened to "any existing absolute directory" fails this test. |
| F-02 | P3 | **Corrected here, not in the original.** The N-06 entry in `DISPOSITIONS_81df0e6c.md` gives a cause for the `/dev/null` anomaly. That cause is **reported, not verified**. The verbatim review recorded "cause not identified". The cited file, `C8-SOURCES/review/DISPOSITIONS_f98f7a2a.md`, was on branch `claude/c8-primary-sources-quality` at that time and has been on staging since PR #39 merged (`21e73b83`). It describes a reviewer run that replaced and restored `/dev/null`. Whether that run was the same event was not verified. |
| F-03 | P3 | **Fixed** by explicit "Update (Cycle 9)" notes in `C8_SECURITY_CLOSEOUT.md`, `REPOSITORY_BINDING_READINESS.md` and `APPROVAL_CONTROLS.md` (two places). The original sentences are kept, and each note states that PR #37 merged at `ff425a9a`. |
| F-04 | INFO | Recorded. The P3 items were in the same commit, `562a55ef`, not in the next one. |
| F-05 | INFO | Recorded. The `isabs` term is redundant with the realpath comparison and is left unchanged. |
| F-06 | INFO | Recorded. |
