# Addendum (Cycle 9): dispositions of the narrow review of 2d7c02cf

The narrow review of PR #39 at `2d7c02cf`, combined with staging and #38 (`2a5707a4`), returned **ACCEPT WITH CONDITIONS**, with no P1 or P2. The review is committed beside this file as `fable_narrow_pr39_2d7c02cf.md`. PR #39 was merged at `21e73b83`. Earlier records are not edited.

| Id | Severity | Disposition (Cycle 9, branch `claude/c9-legal-evidence`) |
| --- | --- | --- |
| N-01 | P3 | **Fixed.** The COI-046 cell in `CORPUS-QUALITY/work/build_hr.py` now gives AR-001 and AR-030 (NOT_FOUND) and AR-036 (NOT_SEARCHED_AUTHORITATIVELY), plus all 13 HINT_ONLY rows (AR-012, AR-013, AR-015, AR-037 to AR-046). The output was regenerated and `OUTPUT_SHA256SUMS` updated. |
| N-02 | P3 | **Fixed.** The `reconcile_judgments.py` docstring now states the regular-file rule and the in-repository rule. The tools README names the RR-01 to RR-03 tests and the Cycle 9 tests. |
| N-03 | INFO | Recorded. |
| N-04 | INFO | Recorded. `HIGH_RISK_REVIEW.md` RC-01 is a narrative of the earlier correction and is left as written. |
| N-05 | P3 | **Fixed.** A leading UTF-8 BOM is accepted in batches and corpus files, and non-string scalar fields fail closed. 10 tests were added (57 in all): 7 fail against the Cycle 8 tool and 3 are regression guards (Cycle 9 review LG-01, LG-02). |
| N-06 | INFO | Recorded. |

`work/unittest_output.txt` is the recorded Cycle 8 test run (47 tests) and is kept as historical output. The current count is 57.
