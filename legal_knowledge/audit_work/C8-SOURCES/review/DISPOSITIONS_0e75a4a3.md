# Dispositions: narrow Fable 5.2 confirmation of 0e75a4a3

- **Review:** `fable_confirm_c8_sources_0e75a4a3.md` and `_findings.csv`, copied verbatim.
- **Verdict:** ACCEPT WITH CONDITIONS. RR-01 (P2) is closed, and no P1 or P2 remains.

The wording corrections below are batched in the next commit. Other than the regenerated `high_risk_record_review.csv` and its sum, no data, generator logic or tool behaviour changed.

| ID | Sev | Disposition |
| --- | --- | --- |
| C3-01 | P3 | **Fixed.** The tools README lists every guard rule and states plainly that, without `--repo`, `--overwrite` replaces an existing file elsewhere. It names the residual race |
| C3-02 / RR-05 | P3 | **Fixed.** HCE-010 and COI-046 now also name the unopened hints AR-012, AR-013 and AR-015. The output is regenerated and the sum updated |
| C3-03 | P3 | **Fixed.** The README and `work/unittest_output.txt` now reflect the 47 tests |
| C3-04 / RR-07 | INFO | **Fixed.** The RC-03 and RC-06 rows of `DISPOSITIONS_44fd72d6.md` now say they were done by the coordinator |
| C3-05 | INFO | Recorded in the README as a residual |
| C3-06 | INFO | Not changed. The general compilation wording in D-AMC-AA-08-s2 to -s19 was made optional by the re-review; the per-row attribution in the high-risk review is correct |
| RR-03 remainder | P3 | Open for the next pass: CSV BOM handling, and type checks on non-string scalars |
