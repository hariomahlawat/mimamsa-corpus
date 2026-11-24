# Confirmation review: PR #40 C9-EVIDENCE-CLEAN, delta ba9676e9..e4d59196

Reviewer model: Fable 5.2 (claude-fable-5-2). Date: 2026-11-24. Review only; nothing committed or pushed.
Checks ran in a disposable clone (`scratchpad/rev_heads/cl`, detached at e4d59196). The reviewed worktree `clean` was not written to.

## Verdict: ACCEPT

The delta is four files and nothing else: one line of `SC-C9/SC_C9_FINDINGS.md` (the FR-04 path) and three new files under `review/`. Checksums, builders and tests hold.

## Findings

| Id | Severity | Statement | Evidence | Requested action |
| --- | --- | --- | --- | --- |
| CC-01 | P3 | FR-04 is half fixed. The finding named two places; section 7 of `SC_C9_FINDINGS.md` is corrected, but the usage text of `SC-C9/tools/build_c9_pack.py` still names `<c9out_SC_dir>` / `<c9out_SC>` (lines 3-8). The disposition says "Fixed" and mentions only section 7. | `git diff ba9676e9..e4d59196 --name-status`; `build_c9_pack.py` lines 3-8. | Fix at the next regeneration, or say so in the disposition. |
| CC-02 | INFO | Scope confirmed. Changed: `SC_C9_FINDINGS.md` (1 line). Added: `DISPOSITIONS_ba9676e9.md`, `fable_final_pr40_ba9676e9.md`, `..._findings.csv`. The two review files are byte-identical to the delivered ones. No tool, register, evidence file or earlier record changed. | `git diff --name-status`; `cmp`. | None. |
| CC-03 | INFO | Checksums and builders hold. `sha256sum -c`: `C8-SOURCES/CORPUS-QUALITY` 6 of 6, `C8-SOURCES/PRIMARY-SOURCES` 15 of 15 (the only checksum files on the branch). `build_c9_pack.py --check`, `judis_scan.py --check`, `scr_pinpoint_check.py --check`: each "CHECK OK", rc 0. `SC_C9_FINDINGS.md` is hand-written, is not a builder output and is in no checksum file, so the edit causes no drift. | Clone runs. | None. |
| CC-04 | INFO | Tests: full `tests/test_legal_audit_*.py` 599 OK, 6 skipped, on the venv and on python3.11. All six skips state their reason (no `origin/raw-data` ref in the clone). No service-number-shaped token in the added lines. | `rev_heads/logs/ut.cl.*.log`. | None. |
| CC-05 | INFO | The dispositions FR-01 to FR-03 are recorded as corrections in the new file only; the earlier records are not edited, as stated. I did not re-verify their substance. | `DISPOSITIONS_ba9676e9.md`. | None. |

## Not checked
- `render_c9.py --check` and `sim_anchor_c9.py` (not touched by the delta).
- The substance of FR-01 to FR-03.

## Isolation
`clean`: `git status --short --ignored` empty, HEAD e4d59196.
