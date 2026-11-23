# Dispositions of the Fable 5.2 re-review of 82a8ce0e..2e2df5ce

The re-review is filed verbatim in `fable_rereview_2e2df5ce.md` and `fable_rereview_findings_2e2df5ce.csv`.
- **Verdict:** ACCEPT WITH CONDITIONS.
- **Closed:** F-01 (P1), plus F-02, F-03, F-04, F-05 and F-07.
- **Opened:** one new P2 (N-01) and P3s.

| ID | Sev | Finding | Disposition |
| --- | --- | --- | --- |
| N-01 | P2 | Each historical withdrawal's `resulting_state` was compared with the **final** status, so a copy could never be re-authenticated after a for-cause withdrawal | **Fixed.** Only a withdrawal that is the latest applied event for its sha256 is checked. Tests: `test_n01_recertify_after_withdrawal_with_resulting_state` covers R1 (withdraw to pending, then CORRECTION to documented) and R2 (withdraw to unknown, then new ADD), plus `--as-of` of the intermediate version |
| N-02 | P3 | Frozen code ran before the manifest's `frozen_inputs_sha256` was checked; `sys.path` grew | **Fixed.** `frozen_builder` checks the frozen-inputs hash against every manifest line before any frozen code runs, and restores `sys.path` afterwards. Test: `test_n02_…` (also kills M11) |
| N-03 | P3 | Any archive.org subdomain, and `http`, accepted | **Fixed.** HTTPS only. For archive.org: the exact host `archive.org` and only the `/download/` or `/details/` paths (no `web.archive.org`). Userinfo is refused. Test: `test_n03_hosts` |
| N-04 | P3 | Record parsing residuals | **Fixed as far as unsigned text allows.** Keys are case- and indentation-insensitive, so duplicates are caught. The date must be a real calendar date. Persons are compared after normalisation. The identity of persons, and whether conditions really were discharged, remain review matters (stated in `decisions/README.md`). Tests: `test_n04_…`, `test_m04b_reviewer_and_m04c_date` |
| N-05 | P3 | Header not checked for a zero-entry file; evidence kind not tied to its file; T reference pointed to an unpinned C6-01 path | **Fixed.** The header is checked once per file. `KIND_FILES` ties each kind to its file family. The T reference must be `T:AUTH-LEDGER/evidence/copy_facts.csv#<copy_id>`, the pinned copy, and must resolve. Test: `test_n05_…` |
| N-06 | P3 | C7-PREP wording read as if B2 were adopted | **Fixed:** "If the owner adopts policy B2 …; rule 1 currently accepts them (B1)" |
| F-06 residual | P3 | 18 of 76 mutants survived | **Addressed.** Each named survivor now has a test asserting its own message: M04b, M04c, M11, M14b, M17, M19, M23, M25c, M31, M35, M36, M38, M43, N56, N58, N63, N64 and N67 (the last via `__spec__ is None` and no `__cached__`). The suite has 96 tests |
| F-08 / F-10 / F-12 / F-13 residuals | P3 | Edges | Zero-entry header and kind mapping fixed. The `D-v00019.md` prefix match is accepted as harmless, because the record must also name the exact version and entry. `effective_state` raising KeyError inside the library is accepted; the command line maps it to `LEDGER ERROR` exit 2 |

## Focused confirmation of 96e0d251: VERDICT ACCEPT (no P1 or P2)
The confirmation is filed verbatim in `fable_confirm_96e0d251.md`.
- N-01 is fixed without reopening F-09.
- N-02 to N-06 are fixed.
- 84 of 86 mutants are killed. The two survivors are redundant controls: M11 is masked by the earlier reader-side check, and the T-reference `resolve` call is redundant with the exact-string check.

| ID | Sev | Finding | Disposition |
| --- | --- | --- | --- |
| C-01 | P3 | Userinfo on non-archive hosts and `..` segments passed `host_ok` (latent) | **Fixed** in the next commit. The host must be followed by an optional numeric port and then `/`, `?`, `#` or end, so userinfo never matches. `.` and `..` path segments are refused. Tests are added to `test_n03_hosts` |
| C-02 | INFO | Drafts pass only after their T reference is rewritten to the pinned `evidence/copy_facts.csv` | Expected. The reviewed PR that converts the draft into `v0001.csv` must make this substitution (recorded in DESIGN_NOTES) |
