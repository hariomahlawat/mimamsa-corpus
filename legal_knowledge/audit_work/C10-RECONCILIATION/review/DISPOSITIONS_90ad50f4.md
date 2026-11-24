# Dispositions: final narrow review of 90ad50f4 (delta e2ec65c4..90ad50f4)

**Review:** `fable_review_90ad50f4.md` and `fable_review_90ad50f4_findings.csv`. Reviewer: Fable 5.2 (claude-fable-5-2).

**Verdict:** ACCEPT WITH CONDITIONS. No P1 findings.

The reviewer confirmed every disposition in `DISPOSITIONS_e2ec65c4.md` except E2-04.

| ID | Sev | Disposition | What changed |
| --- | --- | --- | --- |
| E3-01 | P2 | FIXED | The E2-04 rank separator `(?:\.\|\s)` consumed the dot, after which the closing `\b` failed before the space, so `CAPT. X` and similar titles went unflagged. The separator is now `(?:\.\s*\|\s)`, keeping the non-military exclusions. Re-screen candidates are now **8,077**, the number the reviewer predicted; this supersedes the 7,700 in `DISPOSITIONS_e2ec65c4.md`. The test now includes `CAPT. X`, `MAJ. GEN. X`, `HAV. X` and `SUB. INSPECTOR`. |
| E3-02 | INFO | ADOPTED | The truncated-PDF test now asserts `pdf_status == OPENED`, so it fails if the readable branch is not reached. |
| E3-03 | INFO | NOTED | A few non-military titles are still flagged (`SUB ZONE`, `LT GOVERNOR`, `GEN INSURANCE`; 8 in total). The summary already says over-flagging is possible, and a flag is a lead, not a finding. |

The fix touches only `jassemble.py` and its test. The extractor fingerprint and the batches are unchanged: `assemble --check` reproduces all 14 files.
