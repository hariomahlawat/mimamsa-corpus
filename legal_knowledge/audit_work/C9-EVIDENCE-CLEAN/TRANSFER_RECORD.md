# C9 clean evidence transfer: replacement for draft PR #36

**Status.** Evidence preparation only. Nothing is approved or active: the AUTH-LEDGER stays at version 0, and no legal status, provenance class or conclusion changes. This branch replaces draft PR #36 for review purposes. **It is not to be merged without separate owner approval.**

## 1. What was done
- **Base:** integrated staging `21e73b83` (after PRs #37, #38 and #39).
- **Source:** the final reviewed tree of `legal_knowledge/audit_work/C8-EVIDENCE/` at commit `152045bd` (branch `claude/c8-evidence-verification`). An independent re-review accepted that tree.
- **Method:** a tree transfer (`git checkout 152045bd -- legal_knowledge/audit_work/C8-EVIDENCE`), committed as one new commit with staging as its only parent. No commit of the old branch was cherry-picked, and none is an ancestor of this branch.
- **Scope check:** the old branch (merge base `1a21a2e8`) changed 106 files, all of them under `C8-EVIDENCE/`. All 106 are transferred.

## 2. Comparison with the reviewed tree
| Check | Result |
| --- | --- |
| Tree id of `C8-EVIDENCE/` on this branch | `d82436febd49067348d88acadd31c21185cef73e` |
| Tree id of `C8-EVIDENCE/` at `152045bd` | `d82436febd49067348d88acadd31c21185cef73e` (identical) |
| Files changed against staging, transfer commit | 106 added, 0 modified, 0 deleted, all under `C8-EVIDENCE/` |
| `152045bd`, `801d2c41`, `5212a95b` ancestors of this branch | none |

Because the tree ids are equal, every byte of the reviewed evidence is preserved.

## 3. Intended differences
- **Inside `C8-EVIDENCE/`:** none.
- **Added:** this directory, `C9-EVIDENCE-CLEAN/`, holding this record, the check tools and their counts-only outputs.
- **Historical references kept as they are.** Commit ids in `C8-EVIDENCE/README.md`, `C8-EVIDENCE/review/` and the merged `C8-SOURCES/RULE_VERSION_DECISION_PACK_C8.md` (`5212a95b`, `801d2c41`, `152045bd`) name commits on the old branch. They are not rewritten. Those commits remain on the old branch only and are not reachable from here.

## 4. Sensitive-history check (counts only; no content reproduced)
**Tool:** `tools/sensitive_check.py`; output in `outputs/sensitive_check_output.txt`.

**Intermediate blobs.**
- The old branch has 3 commits, which together hold 190 distinct `C8-EVIDENCE` blobs.
- Of these, 106 are in the final reviewed tree and **84 are intermediate** (removed or later changed).
- **0 of the 84 are reachable** from this branch (`git rev-list --objects`, 4,465 objects).
- This includes the 3 blob versions removed under review finding B-03: `SC-T2/tools/render_run1.jsonl`, `render_run2.jsonl` and the earlier `page_structure.json`.

**Fragment search.**
- The page-text fields of those 3 blobs were split in memory into overlapping windows: `text` in 40-character windows, `first_line`/`last_line` in 30-character windows, step 10.
- **In the transferred tree:** fragments occur in 17 files.
  - 88 distinct fragments match (`outputs/attribution_counts.txt`).
  - 9 of them contain a digit run, and their masked shapes are case-number forms (`No.NNNNN/NNNN`).
  - 7 come from the N S Yadav copy and sit in the page-1 identity readings (`SC-T2/page_checks_sc_c8.csv` and its builder).
  - All matches are identity elements that the reviewed tree quotes on purpose: cause titles, case numbers, dates and running headers.
  - The 801d2c41 re-review (`C8-EVIDENCE/review/fable_rereview_c8_evidence_801d2c41.md`, B-03 row) records that the diagnosis term and the service numbers do not occur in that tree. The fresh review of this branch is asked to re-confirm this independently.
- **Elsewhere in the repository:** `tools/repo_sweep.py` covers all text blobs outside `C8-EVIDENCE/`, with fragments of at least 20 letters. Matches occur in 41 files.
  - Every one is a pre-existing staging file, such as `AUTH-LEDGER/evidence/copy_facts.csv` or the WS-B registers.
  - These files predate the old branch and quote identity lines from the same public judgments.
  - The branch adds no object outside the byte-identical `C8-EVIDENCE/` tree and this directory.

**Reports, logs and review material.**
- `C8-EVIDENCE/review/` describes the removed material only generically ("a named individual's medical detail"); no fragment matched any file there.
- The outputs in this directory hold counts, blob ids and paths only.

**Residual privacy item.** The Cycle 9 Supreme Court work reports that committed C8 files (subsequent-treatment lead MULLIKOTE-1 and the SC findings) print service numbers of parties to the Mullikote judgment, as printed in the published judgment. They are transferred unchanged, because changing reviewed evidence silently is not allowed. **Owner decision PRIV-01:** mask them in a follow-up reviewed commit, which would need regeneration through the builders, or accept them as printed in a published judgment.

## 5. Document and render hashes
**Tool:** `tools/verify_renders.py`; output in `outputs/verify_renders_output.txt`.
- Each held file was re-hashed, and each page re-rendered in memory with PyMuPDF at 150 dpi grayscale, full page.
- **Gazette:** 40 of 40 file sha256 values match, and 40 of 40 render sha256 values match `GAZETTE-T1/render_log.csv`.
- **Supreme Court:** 28 of 28 file sha256 values match, and 28 of 28 render sha256 values match `SC-T2/tools/render_facts.jsonl`.

These are machine reproductions. They are not human confirmation of any reading.

## 6. Provenance and legal conclusions
No file under `C8-EVIDENCE/` differs from the reviewed tree. So no provenance record, classification, recommendation, limitation or legal statement changes. The builders' `--check` (`C8-EVIDENCE/tools/build_packages.py`) passes on this branch.

## 7. Old-branch exposure and owner actions
**Exposure.**
- Commit `5212a95b` is on the remote branch `claude/c8-evidence-verification` and in the history of open draft PR #36.
- It contains page-text dumps from published Supreme Court judgments, including a named individual's medical detail and service numbers.
- The material was removed in `801d2c41`, but the old commit remains fetchable by anyone with read access to the repository, through the branch and the PR's `refs/pull/36/head`.

**What this work did not do (not authorised).** It did not rewrite or force-push the branch, delete the branch or any object, close the PR, or contact GitHub.

**Owner actions to retire the exposure:**
1. Review and decide on this replacement PR.
2. Close draft PR #36 without merging, with a comment pointing to the replacement.
3. Delete the remote branch `claude/c8-evidence-verification` once nothing else depends on it.
   - Check first: the merged `C8-SOURCES` pack cites `152045bd` as historical evidence. That citation stays valid as text, but the commit will no longer be fetchable from a branch.
4. Deleting the branch does **not** remove `refs/pull/36/head` or cached views. To purge the commit, ask GitHub Support to remove the cached views and the PR reference for PR #36, and to run garbage collection. GitHub's documentation on removing sensitive data describes this procedure.
5. Review forks and local clones for copies of `5212a95b`: `git branch -a --contains 5212a95b`.
6. Decide PRIV-01 (section 4).
