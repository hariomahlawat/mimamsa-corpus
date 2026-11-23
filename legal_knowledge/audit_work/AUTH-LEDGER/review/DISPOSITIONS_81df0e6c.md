# Dispositions: narrow Fable 5.2 confirmation of the security branch at 81df0e6c

- **Review:** `fable_confirm_c8_security_81df0e6c.md` and `_findings.csv`, copied verbatim.
- **Verdict:** **ACCEPT**. R-01 to R-05 are closed, and there is no P1 or P2.

The P3 items below are batched in the next commit: tests and a docstring only. No control logic changed.

| ID | Sev | Disposition |
| --- | --- | --- |
| N-01 | P3 | **Fixed.** The new test `test_n01_library_import_orders_through_a_symlink_are_rejected` runs five import orders (`ledger`, `binding`, `pins`, `strength` and `auth_ledger` first) through a symlinked package. All are rejected |
| N-02 | P3 | **Fixed.** The stale `check_committed_layout` docstring is corrected |
| N-03 | INFO | Recorded. The nested-export rejection needs a readable outer repository. In the other cases the package is treated as a plain export, where BIND lines cannot verify |
| N-04 | INFO | Recorded. `git` is required wherever a `.git` exists. An export without `.git` still verifies version zero with the filesystem checks only |
| N-05 | INFO | **Fixed.** A test confirms that a stale `$PWD` is ignored: the tool falls back to the real working directory and verifies |
| N-06 | INFO | Recorded. A brief `/dev/null` anomaly around 14:50:41 UTC was caused by another reviewer's attack run, as recorded in `C8-SOURCES/review/DISPOSITIONS_f98f7a2a.md`. It was restored at once. Results from that window were re-run |
| N-07, N-08 | INFO | Recorded. The HEAD trees read by the layout check are not re-hashed; the layout check is not the binding verdict. The R-01 residual is inherent |
