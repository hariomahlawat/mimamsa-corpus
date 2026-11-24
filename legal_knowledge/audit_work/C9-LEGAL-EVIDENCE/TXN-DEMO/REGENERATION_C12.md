# TXN-DEMO regeneration on the Cycle 12 integrated tree

**Source tree:** staging `21e73b83`, then `--no-ff` merges in this order:
1. #40 `e4d59196`
2. #41 `a61c0e57`
3. #42 `2ba7b0a4`
4. #44 `bdc23f11`
5. #43 `554c46cc`
6. #47 `3980a183`

This happens on branch `claude/c12-integration`. #42 and #44 change AUTH-LEDGER tool bytes, so the recorded values derived from those bytes change. The Cycle 11 regeneration on PR #45 (`REGENERATION_C11.md`) did not include #44 and is superseded.

**Changed values:** 22 of 43. Every one is a commit id, a tool-tree hash, or a value that chains over commit ids:
- `source_package_tools_sha256`;
- `commit.genesis`, `commit.v0001.merge`, `commit.v0001.reviewed_head`, `commit.v0002.head`, `commit.v0002.merge`, `commit.v0003` to `commit.v0008`;
- `ledger.HEAD.final`, `ledger.manifest_sha256.final`;
- `cli.verify.v2` to `cli.verify.v8`, and `cli.verify.final`.

**Unchanged:**
- the other 21 values;
- 19 behavioural checks PASS and 0 FAIL, including every negative case;
- the real ledger stays at version 0, HEAD `0 443c4bdf…6b6b`.

**Guard:** `--check` is now a CI step (`legal-audit-kit-ci.yml`) and part of the local gate. A stale `expected_hashes.json` fails it; see `tests/test_legal_audit_txn_demo_gate.py`.
