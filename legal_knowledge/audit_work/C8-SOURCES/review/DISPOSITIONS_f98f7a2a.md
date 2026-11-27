# Dispositions: focused Fable 5.2 re-review of f98f7a2a

- **Review:** `fable_rereview_c8_sources_f98f7a2a.md` and `_findings.csv`, copied verbatim.
- **Scope:** a focused re-review, not a fresh full review.
- **Verdict:** ACCEPT WITH CONDITIONS. RC-01 (P1) is closed; RR-01 (P2) is new.
- **Status:** the corrections are in the next commit, submitted for narrow confirmation.

| ID | Sev | Disposition |
| --- | --- | --- |
| RR-01 | P2 | **Fixed.** With `--overwrite`, an existing `--out` must be a regular file (`lstat`). Devices, FIFOs, sockets and symlinks are refused. Test: `test_out_non_regular_target_refused_even_with_overwrite` covers a FIFO and a symlink |
| RR-02 | P3 | **Fixed.** An existing file inside `--repo` is never overwritten, even with `--overwrite`. Test: `test_out_existing_file_inside_repo_refused_with_overwrite` |
| RR-03 | P3 | **Partly fixed.** Deeply nested JSON now fails closed with exit 2 (test added). Stringified non-string scalars, CSV BOM handling and bidi or C1 controls are recorded for the next pass |
| RR-04 | P3 | **Fixed.** The 1992 attribution now says the compilation prints "w.e.f. 6-9-1992" only at ss.75-76, s.127 and Chapter XVI (e47a4265 pp.27, 36, 48) |
| RR-05 | P3 | **Fixed.** The r.23 gap list adds AR-012, AR-013 and AR-015 (HINT_ONLY, TO_CHECK) |
| RR-06 | P3 | **Fixed.** DCLR-SC-2013-N08 now cites WSB-T-007. PEN-013 now says Isaac applies r.7 to claims made after fifteen years (para 39(iii)) |
| RR-07 | P3 | **Fixed.** The `DISPOSITIONS_44fd72d6.md` wording is corrected |
| RR-08 | P3 | **Fixed.** The cross-PR evidence is pinned by commit (PR #36 at `152045bd`; the security branch at `81df0e6c`) |
| INFO | — | Recorded. The reviewer's attack run temporarily replaced the container's `/dev/null`, outside the scratchpad, and restored it. The coordinator confirmed afterwards that `/dev/null` is a character device again (1, 3). That is exactly the defect class RR-01 fixes |
