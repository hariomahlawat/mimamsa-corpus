# Independent delta review: PR #50 at `87ebf7d4` (`claude/c12-consolidation` → `legal-knowledge/v2.5-staging`)

**Verdict: ACCEPT WITH CONDITIONS.** No P1. One P2 (R50-01). Nine P3 and three INFO. Findings: `review_pr50_87ebf7d4_findings.csv`.

Scope: the substantive changes made since the recorded C12 reviews (governance, sync safety, research isolation, HF/copy verification, judicial recovery, report corrections, planning). The reviewer did not author any of this work. Everything was run read-only; experiments were made in `scratchpad/rev_pr50/`. Nothing was written to HF.

## Condition for merge
- **R50-01 (P2).** Add the missing protected prefix (or derive the protected set from `COPY_VERIFICATION_MANIFEST.csv`), with a test. Until then, R-04 "CLOSED" overstates the control by one original.

The P3s may be deferred with reasons in the findings register.

## 1. Governance
- **(a) Faithful.** The documents faithfully record the owner's instruction:
  - HF is the central repository.
  - Routine uploads, updates, metadata corrections, preservation and verification are authorised. Each must be versioned, non-destructive, revision-pinned, re-verified and recorded in GitHub.
  - Deletion, restricted publication, visibility changes and legal authentication need separate approval.
  - CLAUDE.md, ADR-0004, the governance doc, docs/README and HF_SYNC_SAFEGUARD are mutually consistent.
- **(b) No weakening.** These controls are stated as unchanged:
  - the main-merge rule;
  - the `I-APPROVE-CORPUS-UPLOAD` / `hf-corpus-upload` environment gate;
  - AUTH-LEDGER;
  - the evidence policies.

  No workflow trigger or job condition changed. The docs/README change only removes "Hugging Face uploads" from the non-authorisation list, and points to the governance doc.
- **Minor wording mismatch (R50-10).** The governance doc's "external acquisition beyond the allow-list rules" vs. CLAUDE.md's "ask before any real download run".

## 2. Sync safety
- **No deletion path remains** in `push_hf.py` or `push_legal_knowledge.py`:
  - `delete_patterns` is removed;
  - there is no `CommitOperationDelete`, delete or visibility call (grep plus the static test);
  - the other HF writer scripts contain no delete calls either.
- **Overwrite protection holds** for 4,102 of 4,103 baseline originals. The exception is `legal_knowledge/judgment_sources/.../mani_ram_bhaira_mirror_2016.pdf` (HF-only), which is outside `PROTECTED_PREFIXES` (**R50-01**).
- **The guard is fail-closed** on:
  - listing errors (500);
  - unknown identity (no LFS sha and no oid);
  - any byte difference.

  **It fails open on a 404 for the repo or revision.** This was demonstrated live (R50-02). Callers pass `revision=None` after checking the repo, so exposure is low.
- **Live end-to-end check against HF** (read-only, `tools/live_guard.py`):
  - identical bytes pass;
  - modified bytes are caught for non-LFS, LFS, preservation, and a file at position 1,051 or more of a 1,121-entry directory (so pagination works);
  - a new folder passes.
- **Prefix computation:** per parent directory, recursive. It is correct, but redundant API calls are possible.
- **LFS vs non-LFS:** LFS is compared by sha256, non-LFS by git blob sha1. Both are correct.
- **TOCTOU (R50-03):** the guarded scripts commit without a pinned parent.
- **Tests:** 7 tests pass. The mutation check (19 mutants: 11 killed, 8 survived) shows gaps, notably the non-LFS mismatch, three of the five prefixes, and the per-step call in `push_hf` (R50-04).
- **CI path addition:** correct.

## 3. Research isolation
- **Mapping:** all 5 deferred P2s (C11 F05–F08, WSG-R04) are mapped. This matches `FINDINGS_CONSOLIDATED.csv`: 622 rows, P1 11/11 CLOSED_VERIFIED, P2 112 closed + 5 DEFERRED_WITH_REASON.
- **Outcome and holding statuses** are enforced; the mutations were killed.
- **FORM_FIELDS (WSG-R04)** is checked only for existence: a status flip survives. **DEFERRED_P2 is hard-coded:** a new deferral in the register survives (R50-05).
- **No consumer** of these artefacts exists in code today.

## 4. HF and copy verification
- **`--check`:** `hf_verify_c12.py report --check` gives CHECK OK (8 files). `build_copy_verification_c12.py --check` reproduces (9 files). All SHA256SUMS files pass.
- **Independent seeded re-hash** (`random.Random(20261124)`, `tools/sample_rehash.py`, fresh directory): **42/42 MATCH.**
  - 35 at `5524c3d9`: 22 from the whole ledger, 10 from the copy manifest, 3 preservation copies. Each was checked against `computed_sha256`, the manifest's expected/computed values, and size.
  - 7 of the 18 ingested at `15bd03cc`. Each was checked against `HF_INGESTED_REDOWNLOAD`, `STAGED_MANIFEST` and the sha256 filename.
- **Arithmetic:**
  - 4,103 rows, 4,103 distinct sha256; segments 4,039 / 16 / 48. The set equals C10 `UNIFIED_CORPUS_INVENTORY.csv`.
  - The 18 ingested sha256 values are disjoint from the baseline and the ledger, so 4,121.
- **Every VERIFIED status is backed by computed hashes:**
  - 0 VERIFIED rows lack computed==expected==ledger and a size match;
  - the ledger has 15,971 rows, all with a computed sha256, and every server-match claim agrees with the LFS sha256 or the git oid.
- **The 274-item closure changes nothing:** the set equals the C10 `HELD_WORKING_STORE_ONLY_EPHEMERAL` items, all six "unchanged" columns equal the C10 source values, and the evidence change is NONE for all 274.
- **Limits:** reproducibility depends on `/home/user/c7` and on scratchpad bytes (R50-09).

## 5. Judicial recovery and ingestion
- **Both HF commits were additive** (independent tree listing):
  - `5524c3d9`→`af7f9d06`: +8, -0, 0 changed;
  - `af7f9d06`→`15bd03cc`: +47, -0, only `.gitattributes` changed (401,428→402,898);
  - the dataset is still private, and HEAD = `15bd03cc`.
- **`judicial_recovery_c12.py --check`:** PASS. The upload function also refuses any existing path and pins `parent_commit`.
- **Schema:** 18/18 new `data/meta` records validate independently (jsonschema with FormatChecker). Each record's sha256 matches its raw file and its `raw_path` is consistent.
- **Restricted material:** `access_marking` is null on all 18. The visual and text marking checks are documented, with their stated limit, and no restricted material was ingested.
- **LLM-derived fields and relevance:** the LLM-derived fields (P&H judges and bench; SC relevance with 0 keyword hits) are marked `llm` and queued for adviser review. The 12 P&H files have `relevance=not_checked` and no text file was written, consistent with "never keep bad text".
- **Duplicates and exclusions:** the duplicate method and the exclusion reasons are sound.
- **Coverage:** the coverage figures reproduce via `--check`.
- **Note:** the 7 excluded files are retained only in the scratchpad (R50-09).

## 6. Other changes
- **HOLDOUT_EVALUATION:** the correction is visibly struck through and attributed, and the Wilson intervals reproduce exactly. The leftover wording "real but not large" conflicts with it (R50-07).
- **Reports:** the CYCLE12_REPORT, TASK_REGISTER, RISK_REGISTER and PRESERVATION_STATUS corrections are visible and accurate. The 622 findings and 5 deferred P2s match `findings_consolidation/`. Some statements remain outdated (R50-06).
- **Planning docs (light read):** no plan implements legal advice or compliance on unverified knowledge. They contain explicit exclusions (plan §1, B9, R3) and candidate banners.

## 7. Combined-tree validation
- **Scratch clone and merge:** `rev_pr50/clone`. Merged `87ebf7d4` into `origin/legal-knowledge/v2.5-staging` (`e0b3e7d2`, which is also the merge base). The merge had **no conflicts**: merge commit `047c902d`, tree `3987ec15`.
- **`gate.sh`: checks=32, exit0=32, nonzero=0.** unittest: **745 tests OK (5 skipped)**, and `test_hf_sync_workflow_guard` 12 OK. The 13 new tests pass.
- **Protected hashes OK:** records_658 `9a8f0d19…`, cases_53 `8b8d53cd…`, CALIBRATION-02 `cfe5f408…`.
- **AUTH-LEDGER:** `verify` reports HEAD `0 443c4bdf…`.
- **TXN-DEMO:** `--check` exits 0, and its temporary ledger HEAD equals the genesis.
- **Workflows:** the only change adds CI paths. No change can trigger an HF upload on merge to staging (upload is dispatch, phrase and environment only; the abbreviation job needs the `[abbreviations-hf]` marker, which appears in none of the PR commits).

## Artefacts
`rev_pr50/` holds:
- `gate_combined.txt`;
- `sample_rehash.csv`;
- `tree_added.json`;
- the scripts in `tools/`: `sample_rehash.py`, `tree_diff.py`, `val_meta.py`, `live_guard.py`, `mut.py`;
- the mutation copies `mut/` and `mut_iso/`.
