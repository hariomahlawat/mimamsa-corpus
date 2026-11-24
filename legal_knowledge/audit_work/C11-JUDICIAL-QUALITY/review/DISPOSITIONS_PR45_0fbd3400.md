# Dispositions: Fable 5.2 (claude-fable-5-2) review of PR #45 (integration candidate) at 0fbd3400

**Verdict: ACCEPT. No P1 or P2 findings.** The PR #45 head stays exactly as reviewed, so these dispositions are recorded here on the C11 branch instead of on #45.

The reviewer independently confirmed:
- **Merges:** all four merge trees reproduce (`c0eb68e6`, `e730b81c`, `917f8bcf`, `670f4730`); 1,291 paths are unaltered except the auto-merged ledger test file, which contains both sides (211 tests).
- **TXN-DEMO:** exactly 22 values changed, all derived from tool bytes or commit ids; behaviour is unchanged.
- **Tests:** 689 (unittest) / 811 (pytest) on the venv; 677 OK with 4 skipped on 3.11.
- **Builders:** all 23 `--check` commands pass.
- **Protected state:** hashes and ledger version 0 are unchanged.

| ID | Sev | Disposition |
| --- | --- | --- |
| I-01 | P3 | **Deferred to the next regeneration.** `TXN-DEMO/README.md` still describes the earlier run. `REGENERATION_C11.md` supersedes it, but the README has no pointer. TXN-DEMO must be regenerated again if #44 merges, and the README pointer will be added in that same reviewed commit. |
| I-02 | P3 | **Recommendation to the owner.** Add `TXN-DEMO --check` to CI in a separate reviewed change. Until then it must be run by hand after any AUTH-LEDGER tool change; this is recorded in the integration plan. |
| INFO | — | Plain `pytest tests` needs `-o pythonpath=tests` because of an existing bare sibling import on staging. The system Python 3.11 lacks `httpx`, so the six crawler test modules ran only on the venv. Both are environment facts, not regressions. |
| (scratch) | — | The reviewer merged #44 onto the candidate in a scratch tree: it merged cleanly, `verify` passed at version 0, and TXN-DEMO needed the same 22 keys regenerated. |
