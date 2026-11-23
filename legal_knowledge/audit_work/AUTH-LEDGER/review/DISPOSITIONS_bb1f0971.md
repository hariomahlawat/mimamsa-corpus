# Dispositions: narrow Fable 5.2 review of the PR #35 merge candidate bb1f0971

- **Review:** `fable_final_bb1f0971.md` and `fable_final_bb1f0971_findings.csv`, copied verbatim.
- **Scope:** a focused review of `git diff 3f486562 bb1f0971` by a Fable 5.2 agent. It is not a fresh full review.
- **Verdict:** **ACCEPT**. No P1 or P2.
- **Outcome:** PR #35 was then merged as an ordinary merge commit, `1a21a2e832c6a7affeeebc246b605b85faf24ff3`, whose tree `dc8f033c` is identical to the PR tree.

The fixes below are in the Cycle 8 security branch (`claude/c8-security-closeout`), not in PR #35.

| ID | Sev | Disposition |
| --- | --- | --- |
| F-01 | P3 | **Fixed.** The fixture comment now says that git writes `commit-graph-chain` read-only (0444), and that a non-root runner cannot overwrite it. It no longer attributes this to git 2.56 |
| F-02 | P3 | **Fixed by this record.** It is the review record that covers the test-only change in bb1f0971. `DISPOSITIONS_3f486562.md` was correct for aa77a305 only |
| F-03 | INFO | **Closed.** A symlinked parent directory is now rejected by the fail-closed layout check and tested (`C8Security.test_c02_nested_symlink_is_rejected`) |
| F-04 | INFO | **Fixed.** The R-01 fixture asserts that plain git honours the forged commit-graph (2 parents), so the rejection test cannot pass vacuously on a git that ignores it |
| F-05 | INFO | **Superseded.** Targeted object re-hashing of the merge, the reviewed head and both parents replaces the untested `git fsck --connectivity-only` candidate. A full fsck stays an optional audit step (`REPOSITORY_BINDING_READINESS.md`) |
