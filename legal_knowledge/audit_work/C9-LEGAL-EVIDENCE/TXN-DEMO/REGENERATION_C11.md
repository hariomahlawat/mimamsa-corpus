# TXN-DEMO regeneration on the Cycle 11 integration candidate

**Why.** PR #42 (AUTH-LEDGER integrity, head `2ba7b0a4`) changes the AUTH-LEDGER tool bytes. The demo records values derived from those bytes, so `--check` fails once #42 is merged; C10 review AL-06 predicted this. The `README.md` paragraph naming the source tree describes the original recorded run; this note supersedes it for the values now committed.

**Source of this run.** The combined tree `staging 21e73b83 + #40 e4d59196 + #41 a61c0e57 + #42 2ba7b0a4 + #43 554c46cc`, merged in that order on branch `claude/c11-integration-candidate`. PR #44, the C11 file-type hardening, is **not** included. If #44 merges, regenerate again.

**What changed: 22 of the 43 recorded values, all derived from tool bytes or commits:**
- `source_package_tools_sha256`;
- the commit ids of the genesis and of v0001 to v0008;
- the reviewed head, the merge commits, and `ledger.HEAD.final` / `ledger.manifest_sha256.final` (these chain over commit ids);
- the `cli.verify.*` outputs that print those ids.

**What did not change:**
- The other 21 values are identical.
- All 19 behavioural checks pass (0 FAIL), including every negative case.
- The real ledger stays at version 0, HEAD `0 443c4bdf…6b6b`, before and after the run.

**Reproduce:** `python -I -B tools/synthetic_transaction_demo.py --check` from this folder on the candidate tree (CHECK OK, 43 values, transcript compared).
