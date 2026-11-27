# Confirmation: `claude/c13-security-aft` @ `4aa8edf4` (independent reviewer, read-only, 2026-11-25)

- Remote head: `4aa8edf4`, the same as the local worktree.
- `a4c0c382` is an ancestor of the head.
- Commits: `ac40b4be`, `f4986938`, `4aa8edf4`.

**Result: CONFIRMED. Safe to merge into staging.**

1. **F01 fixed.**
   - `aftjabalpur.in` has been removed from `aft.allowed_hosts` and is now in `blocked_hosts` with `www.`.
   - `is_url_allowed` checks the block before the allow-list, and `PoliteClient` re-checks every redirect hop.
   - Worst-case test: I removed the config block, re-added the host to `aft.allowed_hosts`, and set `aft` to `enabled: true`. The host and its subdomains (`https`, `http`, `www.`, `cdn.`) were still refused for all 10 sources.
   - Every path, including `--source aft`, `--all` and disabled sources, goes through `is_url_allowed`.
2. **F02 closed.**
   - `NEVER_CONTACT = frozenset({"aftjabalpur.in"})` is unioned into `is_blocked_host`.
   - The new test covers case, subdomains and the look-alike `notaftjabalpur.in`.
   - The worst-case check in item 1 passed only because of this backstop.
3. **No other change.**
   - `ac40b4be` and `f4986938` are patch-id identical to the reviewed 0001 and 0002 (`7c7bd6ee…` and `94fe7f7f…`).
   - `4aa8edf4` changes only `crawler/config.py` (+7 −1) and `tests/test_crawler_security.py` (+12).
   - The total diff from `a4c0c382` covers 4 files: the CI workflow, `config/sources.yaml`, `crawler/config.py` and `tests/test_crawler_security.py`.
   - Note: the author of `4aa8edf4` is `sim <sim@local>`. This is cosmetic.
4. **Tests pass.**
   - `tests/test_crawler_security.py`, `test_crawler_foundation.py`, `test_aft.py` and `test_indiacode.py`: 77 passed, 0 failed.
   - The CI workflow's inline yaml check passes.
5. **No HF sync.**
   - `sync-legal-knowledge-hf.yml` runs on a push to staging only when the push touches `legal_knowledge/**`, the listed `scripts/*`, `.mml_transfer/**` or the workflow file itself. Otherwise it needs a manual dispatch with typed approvals.
   - This branch touches none of those paths (0 files).
   - The new `crawler-security-ci.yml` triggers only on `pull_request` and `workflow_dispatch`, with `contents: read` permission and no HF step.
