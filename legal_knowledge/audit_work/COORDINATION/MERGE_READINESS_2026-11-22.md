# Merge readiness: audit stack and HF safeguard (prepared 2026-11-22; NO merge executed)

Every merge below is a protected-branch action that needs the owner's explicit approval. Use **ordinary merge commits** ("Create a merge commit"); no squash, rebase or force-push.

## Sequence, SHAs and checks (verified by fetch; simulated locally in dependency order)
| Step | PR | Head → base | Ancestry | Conflicts (simulated) | Push-triggered workflows | Can it upload to HF? |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | #15 | `claude/hf-sync-guard-staging` 4ebbeb89 → `legal-knowledge/v2.5-staging` cdd11c2d | staging ⊂ head | none (4 files: sync workflow, guard CI, guard test, doc) | `sync-legal-knowledge-hf.yml` runs (its file changed) | **No.** Under the new workflow both jobs are skipped: not a dispatch, and no `[abbreviations-hf]` tag |
| 2 | #22 | `claude/integration-cycle2` (head carrying this file) → `claude/audit-pilot-01` 1a420f25 | #6 head ⊂ #22 head; #16 and WS-A/B/C/D heads ⊂ #22 head | none | none (not a sync branch; `legal-audit-kit-ci` is PR-only) | No |
| 3 | #6 | `claude/audit-pilot-01` (after step 2) → `legal-knowledge/claude-audit-agents-v1` a2570484 | #5 head ⊂ #6 head (a fast-forward is possible; use a merge commit to keep the record) | none | none (not a sync branch) | No |
| 4 | #5 | `legal-knowledge/claude-audit-agents-v1` (after step 3) → staging (after step 1) | staging ⊄ #5 (staging has 2 owner abbreviation commits): a true merge | none | `sync-legal-knowledge-hf.yml` runs (`legal_knowledge/**` changed) | **No.** The upload job runs only on a manual dispatch with the approval phrase; the abbreviation job needs the `[abbreviations-hf]` tag. **Do not** put that tag in the merge commit message |

**#16 and #18–#21** are already inside #22. Do **not** merge them separately: that would re-apply the same changes. Close them as "integrated via #22" after step 2, or leave them open for reference.

## Simulated post-merge state (computed at #22 = 9b48b08e; recomputed for the final head in the coordinator report)
- After step 1, the staging tree is `491f0696…`.
- After steps 2–3, the #5 branch tree is `c2fdc085…`.
- After step 4, the staging tree is `5a13c37a…`.
  - 281 files change against today's staging, **all** inside `legal_knowledge/audit_work/`, `docs/legal-audit/`, `tools/legal_audit/`, `tests/test_legal_audit_*`, `.claude/agents/` and the HF-guard files.
  - Nothing outside these paths changes.
- In the final tree:
  - the originals are unchanged (`9a8f0d19…`, `8b8d53cd…`);
  - the sync workflow is byte-identical to #15's;
  - the audit tests, schema check, both strict validations, register, CSV and provenance checks, hash reproduction and the 12 HF guard tests all exit 0.

## Approval wording requested from the owner (one per step)
1. "Approve merging PR #15 into legal-knowledge/v2.5-staging."
2. "Approve merging PR #22 into claude/audit-pilot-01."
3. "Approve merging PR #6 into legal-knowledge/claude-audit-agents-v1."
4. "Approve merging PR #5 into legal-knowledge/v2.5-staging."

**After each approved merge, the coordinator:**
- re-fetches;
- verifies the new base tree equals the simulated tree;
- confirms no sync job ran beyond the skipped jobs;
- confirms the originals' hashes are unchanged;
- checks CI.

If anything is unexpected, stop and report.

## Owner configuration before any future corpus upload (not needed for these merges)
- **Environment:** Settings → Environments → `hf-corpus-upload`; required reviewer = owner; optionally a deployment-branch rule.
- **Default-branch constraint:** `workflow_dispatch` is available only when the workflow exists on `main`. Until an approved copy is on `main`, a corpus upload **cannot be dispatched at all**.
- **Trusted Publisher:** a job with an environment presents OIDC subject `repo:hariomahlawat/mimamsa-corpus:environment:hf-corpus-upload`. Add it to the HF Trusted Publisher before an approved upload; otherwise the credential exchange fails closed.
- **No unprotected path:** no other workflow uploads to HF. The abbreviation path stays tag-gated.
