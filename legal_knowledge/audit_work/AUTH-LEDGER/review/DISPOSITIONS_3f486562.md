# Dispositions: Fable 5.2 confirmation review of 3f486562 (AUTH-LEDGER-02)

- **Review:** `fable_confirm_3f486562.md` and `fable_confirm_3f486562_findings.csv`, copied verbatim.
- **Verdict:** **ACCEPT**. No P1 or P2. R-01 to R-09 are closed; R-10 is open and accepted as optional.
- **Review boundary:** the reviewed code head is **3f486562**. The commit that adds this file changes documentation only: these review records and one sentence in `APPROVAL_CONTROLS.md`. No code, test or data changed.

| ID | Sev | Disposition |
| --- | --- | --- |
| C-01 | P3 | **Open, for the next round.** A behavioural test of the repository-top pin at its `apply_ledger` call site, in the real package layout. The control itself works: the reviewer's ten nested `.git` placements were all rejected. What is missing is a test that would catch removal of the call-site argument |
| C-02 | P3 | **Documented now; code check for the next round.** A committed symlink in place of the package directory falls under the stated trust assumption: verify from a fresh clone and check that the package path is a real directory (`APPROVAL_CONTROLS.md`). A fail-closed symlink check is the open item |
| C-03 | INFO | Recorded. Only the committed package root is pinned. Synthetic roots in tests are not, and the command-line tool always uses the package root |
| C-04 | INFO | Recorded. Forged commit objects under a genuine id are rejected through `merge-base --is-ancestor` hash checking, not by `rev-list`. Candidate for an explicit `git fsck --connectivity-only` step in the next round |
| C-05 | INFO | Recorded. Some Unicode look-alikes, any sub-domain of `sci.gov.in`, and `-.pdf` under `/supremecourt/` are still accepted. Since every committed and draft locator decodes to printable ASCII, an ASCII-only decoded-path rule is a candidate for the next round |
| C-06 | INFO | Recorded. `decisions/README.md` and `C7-PREP/WORKSTREAMS_READINESS.md` changed earlier in this package by design; neither is protected |
