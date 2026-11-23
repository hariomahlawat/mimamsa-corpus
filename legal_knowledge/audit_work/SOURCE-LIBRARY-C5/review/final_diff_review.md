# Independent final-diff review: SOURCE-LIBRARY-C5 corrections (7bdde558)

## Method
- **Read-only.** I extracted commit 7bdde558 with `git archive` into `c5review2/tree` and ran every check there.
- **Re-ran:**
  - the unit tests: 322 OK, 6 skipped;
  - `build_registers.py --check`: passes;
  - `check_c5.py --verify-files <scratchpad>`: 0 errors, 0 warnings;
  - sha256 of the two originals: unchanged.
- **Diffs reviewed:**
  - 151f9358..7bdde558 (scope);
  - 33c2e1b4..7bdde558 (the correction delta).
- **Code read:** `copy_rows`, `check_holding_vs_copies`, `crosswalk`, `evidence_stage`, `discovery_guard.py`, `run_guarded_discovery.py`, and the new checks in `check_c5`.
- **Data inspected:**
  - D_candidates C5D-001..006;
  - every row of D_requests_v2.tsv;
  - earlier candidates C5B-021/022/023 and C5C-024/029;
  - the CALIBRATION-02 authentication register;
  - the copy register and copy annotations.
- **Act 37/1992 bytes:** `cmp` on the held binaries confirms 122 differing bytes at offsets 165208-165338.
- **Network:** 4 read-only requests, none of them a document GET:
  - 1 web search;
  - upload.indiacode.nic.in robots.txt (connection reset);
  - 2 Wayback availability API calls.

## Results by check
1. **Defects corrected.**
   - P1-b and P1-c: corrected, and the evidence checks out (FD-08, FD-09).
   - P1-a: corrected, with a structured-field gap (FD-01).
   - P2-a, P2-b, P2-c: corrected for the discovery tooling and wording. The runner has a residual GET gap (FD-02).
2. **Classifications.**
   - The TA candidate identification is reproducible: my own search returned the same index titles and URLs.
   - The direct block is real: robots.txt still resets.
   - The wording is evidence-bounded. However, BLOCKED_ACCESS is not carried in any structured field, and `discovery_state` still contains the superseded NOT_FOUND (FD-01).
   - The RA 1987 CDA leads are LEAD_ONLY, and historical evidence is kept separate from current access. The Wayback snapshot claim was verified.
   - RMSAF is NOT_FOUND_IN_SEARCHED_SOURCES, with bounded wording.
3. **Copy-level model.** Status is per sha, taken from that sha's own C4 register row through the shared rule. I found no promotion path for an undocumented or pending copy. Minor point: the HELD_PRIMARY subtype is not checked against the documented copy's class (FD-07).
4. **Counts.** All headline figures reproduce from the rebuilt registers (FD-10). Crosswalk evidence statuses are unchanged.
5. **Discovery controls.**
   - Behaviour that is correct:
     - robots.txt is fail-closed;
     - a 404 or 410 robots response is treated as no file, per RFC 9309;
     - 401, 403, 429, 5xx and off-host redirects are treated as unavailable;
     - each redirect hop gets its own robots check;
     - aftjabalpur.in and bare-IP hosts are blocked;
     - TLS verification is never disabled.
   - Residual weaknesses:
     - a GET can still transfer up to 3 MB of a document before it is discarded (FD-02);
     - the log validator does not require a robots decision before a request (FD-05);
     - one row records the proxy's content type instead of the target's (FD-06).
6. **Legal safeguards.**
   - No legal state changed, and the originals are unchanged.
   - Only authorised paths changed.
   - The conflict, amendment and provision-chain registers are unchanged.
   - Isaac is unchanged.
7. **New defects.** FD-03 (a dangling D8 reference) and FD-04 (inconsistent amendment years), both P3.
8. **PR scope.** Only SOURCE-LIBRARY-C5/** and tests/test_legal_audit_c5_sources.py. The remote head is 7bdde558.

## VERDICT: ACCEPT WITH CONDITIONS
Conditions:
1. **FD-01:** carry BLOCKED_ACCESS (verification) in a structured field for the TA Act, Rules and Regulations. Mark the superseded NOT_FOUND in their `discovery_state`. Add a test assertion for both.
2. **FD-02:** before `run_guarded_discovery.py` is used again:
   - cap GET bodies or abort the transfer early;
   - refuse a GET when the HEAD response has no content type;
   - correct the "never downloads" docstring;
   - add a mocked runner test.

   The committed logs show no document payload, so this does not invalidate the evidence in this package.
3. **P3 items FD-03..FD-07** may be fixed in the same follow-up or carried into C6.
