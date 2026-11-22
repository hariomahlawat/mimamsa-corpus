# Git workflow discipline for audit agents (owner rule, 2026-11-22)

**Binding for every agent and the orchestrator.**

## Rules
1. **Never overwrite another agent's or person's branch or uncommitted changes.** No force-push, no history rewrite, no `git checkout <other-ref> -- <path>` over files that someone else has changed since you last integrated.
2. **Isolation.** Concurrent agents work in separate git worktrees or branches, or write only to a scratchpad that the orchestrator integrates. Subagents never commit to a shared branch.
3. **Fetch and compare before integrating.**
   - `git fetch origin`, then list upstream commits since your last integration (`git log <last-synced>..origin/<branch>`).
   - If there are upstream commits, merge them first (`git merge`), and resolve conflicts by three-way merge (`git merge-file`), not by replacing files.
   - For each file you intend to update, confirm that the branch's committed version equals the version you last synced (`git diff --quiet <last-synced> origin/<branch> -- <file>`). If it differs, someone else changed it, so merge it instead of replacing it.
4. **Review before replacing.** Read the current committed version of any file before changing it. Commit messages state what was integrated and from where.
5. **One classification system.** `SOURCE_AUTHORITY_POLICY.md` (v1) and its schema fields are the only source-classification scheme. Do not add parallel classes.
6. **Gate on tests.** Run the full audit test suite and strict batch validation before every push. Never push while tests fail; a failing run must stop the command chain.

## Why (incident, 2026-11-22)
The orchestrator synced audit paths into PR 6 with `git checkout <working-branch> -- docs/legal-audit tools/legal_audit …`. That reverted the owner's newly pushed source-authority commits (b315347b..2256e1ad) in eight files, and the commit was pushed even though 9 tests failed (CI run 45028876106 failed). Commit cf80e182 restored the owner's files byte-for-byte by three-way merge, without rewriting history. Rules 3 and 6 exist to prevent a repeat.

## Integration helper (orchestrator)
```bash
git fetch origin
git log --oneline <last-synced>..origin/<branch>            # anything new upstream?
for f in <files>; do git diff --quiet <last-synced> origin/<branch> -- "$f" || echo "CHANGED UPSTREAM: $f"; done
```
