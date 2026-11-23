# Re-review: 7bdde558..5bc2d12a (FD-01..FD-07 fixes)

## Method
- **Read-only.** I extracted commit 5bc2d12a with `git archive` into `c5review2/tree2` and ran every check there.
- **Re-ran:**
  - the unit tests: 328 OK, 6 skipped;
  - `build_registers.py --check`: rc 0;
  - `check_c5.py --verify-files`: 0 errors, 0 warnings;
  - sha256 of the originals: 9a8f0d19… and 8b8d53cd…, unchanged.
- **Diffs reviewed:** I read every changed file and compared the master register and inputs field by field against 7bdde558.
- **Network:** none used (0 of 3).

## Results
- **(a) FD-01: fixed.**
  - The new columns `direct_verification_state` and `superseded_candidate_ids` are added to the inputs, the build, the schema and check_c5.
  - BLOCKED_ACCESS is now structured for the TA Act, Rules and Regulations, and for RA 1987.
  - C5B-021, C5B-022 and C5B-023 are recorded as superseded. The build rejects a superseded id that is not one of the row's own candidates.
  - The TA Rules and Regulations `discovery_state` is now FOUND_CANDIDATE only.
  - Only these columns changed in the inputs, plus one TA Act `identity_notes`. `coverage_summary.json`, the crosswalk and the copy register are byte-identical to 7bdde558.
- **(b) FD-02: fixed for the reported path.**
  - The runner GETs only when HEAD returned an explicit listing content type. Otherwise it logs a NONE row with "GET refused".
  - It then sends a 0–2047 range probe (`--max-filesize 4096`). If the probe looks like a document, its bytes are deleted and the event is logged as a violation (rc 1).
  - The three mocked tests cover a missing content type, a lying probe and unreadable robots.
  - Residual paths are in RR-01 and RR-05.
- **(c) FD-03 to FD-07: fixed.**
  - The review files are committed and identical to my outputs.
  - C5D-001 now cites 1964, 2017 and 2023, all marked unverified, and matches the master register.
  - `validate_log_v2` now requires a robots decision before a request (partial: see RR-03).
  - LA-04 keeps the original value `text/plain; charset=utf-8`, and the runner now drops headers when status is 000.
  - `check_holding_vs_copies` checks the HELD_PRIMARY subtype against the documented copy's class, and a test covers it.
- **(d) No regression.**
  - Against 151f9358, only SOURCE-LIBRARY-C5/** and `tests/test_legal_audit_c5_sources.py` changed. The CALIBRATION-02 register and the originals are unchanged.
  - The remote head is 5bc2d12a.
  - No legal state changed.

## Findings (none blocking)
| ID | Sev | Observation | Recommendation |
| --- | --- | --- | --- |
| RR-01 | P3 | **A full GET can still move more than 4 KiB of a document.** After a probe classified as listing, the runner issues a full GET capped at 3 MB. A document still gets through if the server returns different content on the second request, or if a PDF is served as text/html with bytes before `%PDF` (the signature is checked at offset 0 only). In the second case the body is **kept**. The docstring names only the 4 KiB Range case. | Search the first 1 KiB for the signature. Lower the full-GET cap, or re-check headers against the probe. Name this residual risk in the docstring. |
| RR-02 | P3/INFO | TA Act `discovery_state` still contains NOT_FOUND, from C5C-029. That candidate is a search for a related Gazette item, so it is not a contradiction. The request's statement that no TA row has NOT_FOUND is still inaccurate, and the FD-01 test asserts it only for the Rules and Regulations. | Mark C5C-029's scope in notes, or supersede it. |
| RR-03 | P3 | `validate_log_v2` checks for a robots decision on the URL host only, not on each host in `redirect_hosts`. | Apply the same check to every redirect host. |
| RR-04 | P3 | D7 cites `review/final_diff_rereview.md`, which is not in 5bc2d12a. This is the same pattern as FD-03. | Commit this file. |
| RR-05 | INFO | When the size is not known in advance, the 4 KiB abort depends on curl ≥ 8.4 enforcing `--max-filesize` during the transfer. The local curl is 8.5.0. | State the minimum curl version in the docstring or the runner. |

## VERDICT: ACCEPT
Both P2 conditions are met. The P3 items may be handled in C6 or a later tidy-up.
