# Dispositions: independent Fable 5.2 re-review of 64859d4d (AUTH-LEDGER-02)

- **Review:** `fable_rereview_64859d4d.md` and `fable_rereview_64859d4d_findings.csv`, copied verbatim.
- **Verdict:** ACCEPT WITH CONDITIONS. There was no P1. The 3 P2 findings must be fixed before merge; there were also 4 P3 and 3 INFO findings.
- **Implementer:** Claude Opus 5.5.
- **Next step:** the corrections are in the following commit, submitted for a narrow independent confirmation.

| ID | Sev | Disposition |
| --- | --- | --- |
| R-01 | P2 | **Fixed.** Every git call runs with `-c core.commitGraph=false`. The reviewer's forgery is reproduced in the test suite for a single commit-graph file and for a split chain (`ReviewFixes03.test_r01_*`). Both are now rejected: the direct push is seen with 1 parent. `APPROVAL_CONTROLS.md` states the trust assumption: the object store must not be tampered with, so audit from a fresh clone or bundle |
| R-02 | P2 | **Fixed.** `binding.verify(..., expected_top)` pins the repository top. For the committed ledger, `apply_ledger` passes the repository that contains `legal_knowledge/audit_work/AUTH-LEDGER`, so a nested `.git` directory or a `gitdir:` file in the ledger root is rejected. Tested |
| R-03 | P2 | **Fixed.** The source register now has `identifier_source` instead of a blanket YES: 13 rows are `IMAGE_CHECK_OR_TRANSCRIPTION` and 7 are `L5_DISCOVERY_REGISTER_ONLY`. For those 7, the pending rows' `limitations` say the L5 register was produced by a read-only discovery agent, is not approved, and is not an identity-reference kind under rule 1. Their recommendation advises a CONFIRMED identity check first. "A person read" is removed from the findings and the builder docstring. Decision pack B1 is corrected (13 image check or WS-A transcription, 7 L5 only). The 18/2 split is unchanged |
| R-04 | P3 | **Fixed.** No first-class locator may carry a query, on any class. None of the committed first-class locators has one; all 32 drafts still pass |
| R-05 | P3 | **Fixed.** Rejected now: segments made only of dots and/or spaces, of any length; U+2215, U+2044, U+29F8 and U+FFFD. Ogham space (Zs) is tested |
| R-06 | P3 | **Fixed.** New tests: environment and git-option assertions; a nested-prefix merge (an unrelated base change outside the package is accepted, a package change in the merge is rejected); `urlcheck.problem()` alone for `1.0x7f` and `example.1a`; court path prefix and suffix; both `_untruncated` call sites; the three L5 conditions. A mutation run on this round's 6 controls killed all 6 |
| R-07 | P3 | **Fixed.** For non-scanned files, v04 says the search covered the held page-1 excerpt only and that the instrument is printed on a later page |
| R-08 | INFO | **Recorded** in the decision pack: the anchor column is the typed C6-01 column, independently recomputed by the reviewer with the reader, and the two agree |
| R-09 | INFO | **Fixed** in `APPROVAL_CONTROLS.md`: `require_binding=False` is used by the synthetic tests and the tranche simulation, in temporary directories only |
| R-10 | INFO | Not changed. These are two empty temporary directories left by the pre-existing AUTH-LEDGER-01 tests, outside the repository |

**Unchanged:**
- version zero, HEAD and the four Cycle 5 outputs;
- the rule-1 outcome of all 32 drafts;
- all protected paths.

No entry was approved.
