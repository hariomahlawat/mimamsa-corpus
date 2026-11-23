# Dispositions: focused Fable 5.2 re-review of the security branch 06a54c66 and CI branch 30f6015f

- **Review:** `fable_rereview_c8_security_06a54c66.md` and `_findings.csv`, copied verbatim.
- **Scope:** a focused re-review, not a fresh full review.
- **Verdicts:** security ACCEPT WITH CONDITIONS; CI ACCEPT WITH CONDITIONS. No P1 or P2.

| ID | Sev | Disposition |
| --- | --- | --- |
| R-01 | P3 | **Fixed.** For a relative `argv[0]`, the CLI joins it to `$PWD` when `$PWD` names the real working directory. A relative run from inside the link target is rejected (`C8SecurityRound3.test_r01_*`). The docstring and documents now say to use an absolute path or to run from the repository top or above |
| R-02 | P3 | **Fixed.** `binding._ancestry_ok` re-hashes every commit on `rev-list --ancestry-path merge..HEAD`, plus the merge, in one batched read. A forged interior commit is rejected (`test_r02_*`). The two over-claiming sentences are corrected |
| R-03 | P3 | **Fixed.** Tests were added for: a forged pinned blob; a forged base manifest; and a library import through a symlink. The import test exercises the unresolved `sys.path` and `LOGICAL_PKG` layer, independently of the CLI `argv[0]` pin. "Killed all 8" is corrected. Round 3 mutation run: 7 of 7 killed |
| R-04 | P3 | **Fixed and documented.** A missing `git` raises a `LedgerError`. A repository git refuses (for example "dubious ownership") while `.git` exists fails closed. The rule for exports nested below another repository's work tree is documented (extract outside any work tree, or verify from the bundle) |
| R-05 | P3 | **Fixed.** The stale `apply_ledger` reference and the loose O-5 sentence are corrected |
| R-06, R-07 | INFO | Recorded |
| CI-R3 / CI-02 | P3 | Open until the draft PR runs CI on a runner. The runtime will be reported in the PR |
| CI-R1, CI-R2 | INFO | Recorded. The pin must change in the same PR as any WS-D regeneration |
