# C16 Tranche A: integration of WP04 (text store) and WP05 (evaluator)

> Superseded for status by `C16A_COMPLETION_REPORT.md` (PR #80 closeout). This note records the original integration.

**Branch:** `claude/c16-integration`, from staging `c8fa5290`.

**Merged:**
- `claude/c16-text-store` (draft PR #78)
- `claude/c16-evaluator` (draft PR #79)

**Not merged here:** the contract checkpoint, draft PR #77. It awaits ChatGPT review and has no runtime interfaces that these branches depend on.

**Conflict:** only in `app/b1/bench/IndexBench/Program.cs`, where both streams added options. I kept the union of both: `--text-store`/`--build-only` from WP04 and `--parity`/`--with-page` from WP05. Application code merged without conflict. WP04 touched only three lines in `Search/*`, all of them `Text.Length` → `Length`.

## Verification on the merged tree (same host)

| Check | Default (memory text, memory engine) | Disk text store + disk engine |
| --- | --- | --- |
| C# suite | 225/225 | 225/225 |
| Playwright (SYN and real sample) | 81/81 | 81/81 |

**Retrieval oracle:** unchanged; 10/14 with hybrid off and 12/14 with hybrid on (e5-small, floor 0.8579), as on staging.

**Evaluator parity:** `IndexBench --parity` ran 2,062 cases on the real 290-document sample with the walkthrough queries. All three combinations below give the same signature SHA-256 as the Cycle 15 evaluator baseline recorded in `c16_evaluator/raw/parity_summary.json`: `9cc23a4246c1b280e0dd1ffe6491e5e23eab7aca740fb3d10e525c06bf9df633`.
- memory engine with memory text;
- disk engine with disk text;
- memory engine with disk text.

## Defaults
- `Mimamsa:Text:Store=memory` and `Mimamsa:Search:Engine=memory`. Switching both to `disk` is an owner decision: see ADR-0008 and ADR-0007.
- Disk stores default to `<site>/text-store` and `<site>/search-index`. Set `Mimamsa:Text:Dir` and `Mimamsa:Search:IndexDir` to keep them outside the site.
