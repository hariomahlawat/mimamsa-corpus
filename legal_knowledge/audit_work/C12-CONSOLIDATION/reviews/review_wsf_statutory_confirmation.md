# Confirmation review: WS-F remediation (C12F-v1.1, commit 88ca5aa3)

The original reviewer carried out this confirmation review. It is an AI documentary review, not legal validation. All work was read-only, and the runs were done in the disposable copy `scratchpad/rev_wsf/copy2`.

**Result: F-01 to F-10 are all CLOSED_VERIFIED. No new P1 or P2 findings.** Two P3 notes are recorded in `review_wsf_statutory_confirmation_findings.csv`.

## Checks performed

**Build and tests (venv, Python 3.13)**
- `build_c12f.py --check`: CHECK OK.
- `render_pages_c12.py --verify`: 28/28 rows reproduce.
- `pytest`: 27 passed.
- Under python3.11, the build stops with the clear message that `require_env()` produces.

**Evidence states**
- Counts: EXACT 99, PARTIAL 595, MISSING 289. The only transitions are 57 PARTIAL to EXACT.
- The 6 withdrawn items are all PARTIAL, with the correct blockers.
- All six items citing r.15 (including C10Q-CW-0356) are PARTIAL.

**Page evidence**
- All 28 `render_png_sha256` values equal the full sha256 of the reviewer's own 110-dpi renders.
- Spot-checked observed text for PE-1954-296, -301, -331, -340 and -342 and PE-1961-141. Each agrees with the reviewer's earlier image reads.
- The r.186 continuation probe on printed p.343 was confirmed on a new render.

**Scope, ranges and notes**
- F-04: the `record_level_state` and `exact_scope` columns are present, with 39 citation-locator-only promotions.
- F-05: page ranges are recorded (for example r.179 at 340-341, the 1954 r.14 at 296-297 and the 1961 r.14 at 141-142).
- F-06: the r.15B note is on 18 verification rows.
- F-07: X002 lists 7 records.
- F-09: the r.135 note is present.

**Frozen originals and worktree**
- The frozen originals are verified by `--check`.
- The worktree has no uncommitted changes under `statutory_citations/` or `curated_originals/`.

## P3 notes

- **C-01:** the build reads the review's promotions CSV, but only for the reconciliation count; it never sets a state. Keep it reconciliation-only.
- **C-02:** the 16 baseline EXACT items that rest on text-layer-only 1954 pages remain out of scope. This is disclosed in `SUMMARY.json`.
