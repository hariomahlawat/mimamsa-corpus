# Hugging Face sync safeguard (owner decision, 2026-11-22)

**General corpus upload** (`upload` job in `.github/workflows/sync-legal-knowledge-hf.yml`):
- **Never runs on push.** It runs only on `workflow_dispatch` with `approve_corpus_upload = I-APPROVE-CORPUS-UPLOAD`.
- **Defence in depth:** the job's first step re-checks both conditions and fails otherwise.
- **Environment gate:** the job declares `environment: hf-corpus-upload`.
- **Network source-acquisition steps:** the 10 steps that run `scripts/archive_*`, `acquire_*` or `probe_*` additionally need `run_source_acquisition = I-APPROVE-SOURCE-ACQUISITION`. Without it they are skipped. Later validation steps that expect freshly archived files may then fail, which is intended: acquisition is a separate approval.

**Abbreviation upload** (`upload_abbreviations`): unchanged. It runs only on a push whose head commit message contains `[abbreviations-hf]`.

**Tests:** `tests/test_hf_sync_workflow_guard.py` evaluates the workflow's own `if:` expressions for push, PR, schedule and dispatch events, with and without the approval phrases. It is run by `.github/workflows/hf-sync-guard-ci.yml` on every PR touching these files. Mutation checks showed that restoring the old push condition, or dropping an acquisition gate, makes the tests fail.

## GitHub constraints (owner actions)
1. **Default branch.** GitHub lists and triggers `workflow_dispatch` only for workflows present on the default branch (`main`). `main` currently has no sync workflow, so after this PR the corpus upload **cannot be dispatched at all** until an approved copy of this workflow is placed on `main`. That is the safest state.
   - When an upload is approved: merge this workflow to `main` (same guards), then dispatch with `ref` = the branch to upload from.
2. **Environment with required reviewers.** Create the environment in Settings → Environments → `hf-corpus-upload`, add yourself as a required reviewer, and optionally restrict it to the branch you upload from.
   - Until it exists, GitHub creates it unprotected on first use; the dispatch phrase still applies.
3. **OIDC / Trusted Publisher.** A job with an environment receives an OIDC subject claim `repo:<owner>/<repo>:environment:hf-corpus-upload`.
   - If the Hugging Face Trusted Publisher for the private dataset is bound to a branch- or ref-based subject, add the environment-based subject there before the first approved upload; otherwise credential exchange fails closed.
   - The abbreviation job has no environment, so its claim is unchanged.

## Relationship to the standing corpus instruction (2026-11-24)
The gates above govern only the **GitHub Actions** sync workflow, and they are unchanged. Routine corpus operations performed directly against the HF dataset, with securely injected credentials, are authorised by the standing owner instruction in `docs/governance/CORPUS_REPOSITORY_GOVERNANCE.md`. Those operations must be versioned, verified and recorded there. Never put `[abbreviations-hf]` in a commit message unless that upload is intended.
