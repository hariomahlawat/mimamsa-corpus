# C12 consolidation: independent confirmation of P2 fixes at 43190971

- **Reviewer:** an independent confirmation reviewer (Claude Opus 5.5 subagent). I did not write any of the fixes.
- **Mode:** read-only. Experiments ran in a fresh clone at `confirm_c12/repo` (detached at 43190971).
- **Inputs:**
  - raw data from `/home/user/c7` at `ad77758d`;
  - Python from `scratchpad/venv`;
  - no network.
- **Note:** while this review was running, another agent advanced the c12w branch to `88ca5aa3`. That commit touches only `statutory_citations/`, which is out of scope here.
- **Row-level evidence:** `confirmation_findings.csv`.

## Verdicts

| Source | ID | Verdict |
| --- | --- | --- |
| C10 `fable_review_7ccb9c2e` | RR-01 | CLOSED_VERIFIED |
| C10 `fable_review_7ccb9c2e` | RR-02 | CLOSED_VERIFIED (sentence-correction option) |
| C10 `fable_review_recon_160adfd1` | RC-04 | CLOSED_VERIFIED (jointly with RR-02) |
| C11 extraction review | F03 | CLOSED_VERIFIED |
| C11 extraction review | F04 | PARTIALLY_CLOSED |
| C12 coordinator tools | F01 | CLOSED_VERIFIED |
| C12 coordinator tools | F02 | CLOSED_VERIFIED |
| C12 coordinator tools | F03 | CLOSED_VERIFIED |
| C12 coordinator tools | F04 | PARTIALLY_CLOSED |

## How each verdict was reached

### RR-01

**Fix reproduced:** `build_reconciliation.py --check` reproduces at HEAD.
- There are 8 `RD-` groups, all statute groups, and none is a court bucket.
- All 17 tests pass.

**Negative control:** I reverted the one-line fix.
- `--check` then fails on 3 outputs.
- The new test also fails.

### RR-02 and RC-04

**What changed:**
- `CAPTURE.md` now names the two CSVs that carry `hf_snapshot`, and both CSVs do have the column.
- Every other output is hashed in `RECONCILIATION_MANIFEST.json`, which records `revision_pinned: NO`.
- `DATASET_INTEGRITY_NOTES.md` now states that the revision is unpinned.

**Reproduction:** both C10 tools reproduce with `--check`.

**Residual (P3):**
- The `CAPTURE.md` heading still begins "Limits stated in every output".
- `DATASET_INTEGRITY_SUMMARY.csv` rows carry no per-row as-of date.

### C11 F03

I reproduced the weighted figure independently: court-level post-stratification gives **78.85%**, against the reported "about 79%".

**Where it is reported:**
- `CYCLE11_REPORT.md` shows it beside the 84.1% headline.
- `HOLDOUT_EVALUATION.md` shows it only in its qualifications section.

The V3 holdout draws 25 to 40 judgments per court, which meets the reviewer's alternative of "large enough per court to weight".

### C11 F04

I reproduced the family baselines: crawler 33/44 and C10 extractor 31/48 (with "remanded" counted as its own family).

**Still open:**
- `HOLDOUT_EVALUATION.md` line 49 still says "v2 is substantially better than both baselines". The reviewer asked for this sentence to be replaced, and line 70 of the same file contradicts it.
- No intervals are given for the family figures.
- The exact-label baseline rows (lines 24 and 25) are not annotated as biased.

### C12 F01

**Run in c12w:**
- `--check` printed "no tracked file written" and exited with code 0.
- `git status --porcelain` was identical before and after.
- No file was modified.

**Run in the fresh clone:**
- Nothing was written.
- The check fails only because `PROVENANCE_C12.md` embeds the absolute worktree path. The file hashes are identical.

**Provenance pinning:** provenance is now pinned to `INPUT_REV b4948b0f` through `git show`, not the live HEAD.

**Residual (P3):**
- Each run leaves a `/tmp/adviser_check_*` directory behind.
- Because of the embedded path, the check passes only from c12w. This ties to F11.

### C12 F02

**Fix reproduced:**
- Agreement is now **134/150**.
- V3H015 and V3H017 are DISAGREE, with `agree_proceeding=False`.
- `--check` reproduces.

**Negative control:** I removed the proceeding-level condition, and the result returned to 136/14.

### C12 F03

**Ground truth:**
- 215 rows covering 150 judgments.
- 46 rows are adjudicated, from 16 judgments.
- The set of adjudicated ids equals the set of DISAGREE ids.
- V3H015 and V3H017 take their rows from `ADJUDICATION.csv`.

**PDF spot-check** (PyMuPDF on c7 `ad77758d`, file hashes verified):
- **V3H015:**
  - p17 lists CA 281 and 282/2020 only as "With" appeals.
  - p30, para 10, says counsel "appearing on behalf of the Mehsana District Co-operative Milk Producers Union in Civil Appeal No. 282 of 2020 supported" the Attorney General. It does not say which side that party is on.
  - p77, para 80, matches the excerpt.
  - **Faithful:** "unclear" for CA 282/2020 is correct.
- **V3H017:**
  - p5 links the dates to "WP (C) No. 229 of 2025 and RP No. 38 of 2025, respectively". It never maps appeal 8452 or 8453 to either order.
  - p20, paras 38 to 40, match both rows.
  - **Faithful.**

### C12 F04

**Accurate against the artefacts:** the relabelling of the adjudicator as "not blind to the competing codings".
- The original 14 rows' reasons cite A/B.
- The new rows record the X/Y anonymisation, and the coordinator's X→B mapping is consistent with the coder files.

**Not verifiable:** the X/Y anonymisation and the adjudicator's independence, because no prompts or assignment logs exist.

**Still open:**
- Coders A and B are still described as "independently blind" (truth-tool docstring; `CODING_CONVENTION.md` line 3) with no evidence that they were kept apart.
- Commit `ed5362e5` says "blind third coder". No correcting note exists in `holdout_v3/`.
- `TASK_REGISTER.md` at HEAD still says 136/150.

## Deferred C11 findings: what the V3 evaluation must address

- **F02:** the holdout must be double-coded under one written convention. Report inter-coder agreement (strict: 134/150) and score against adjudicated truth.
- **F05:** "partly succeeds" and extent-qualified allowances must map to `partly_allowed` or abstain. Add H011 and J-123f221f41ed354a as tests.
- **F06:** state holding recall (C11: 12.0%). Propositions are leads only: never a holdings index or negative evidence. Re-measure against the blind reference.
- **F07:** keep propositions NOT_VERIFIED. Do not surface `attributed_to`. Re-measure per-label origin precision after F08.
- **F08:** fix quote-span closing, with tests. Hand-review the 51 `ONLY_QUOTED_DISPOSITION_LANGUAGE_FOUND` rows and report how many V3 resolves.
- **Also, from F03:** V3 must report a population-weighted precision beside the unweighted figure.
- **Also, from the C12 F03 check:** in the V3H017 ground truth, proceedings are identified by impugned order, not by appeal number, and the scorer must allow for that.

## New issues found in this confirmation

No new P1 or P2 issues.

New P3 items:
1. `--check` leaves a temporary directory in `/tmp` on every run.
2. Absolute paths in provenance make the adviser `--check` non-portable.
3. `TASK_REGISTER.md` at HEAD is stale (136/150; the figure is now 134/150).
4. `key()` in the agreement tool turns "8452-53 of 2026" into `53-2026`. This has no effect on the current verdicts.
