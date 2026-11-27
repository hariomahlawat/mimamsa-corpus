# Independent review: C12 coordinator tools at 25723740

Branch `claude/c12-consolidation`, commit `25723740`. Scope: `legal_knowledge/audit_work/C12-CONSOLIDATION/` — the holdout V3 sample, agreement and truth tools, the SC case-number overlay, and the adviser package builder. Reviewer: independent agent (did not write this code). This is a technical and documentary review only. It does not validate anything legally.

## Verdict: ACCEPT WITH CONDITIONS

Every stated figure reproduces exactly, and the four C12 tools' `--check` modes reproduce their outputs byte for byte. No frozen record outside `audit_work` has changed, and nothing from the 266 unreviewed SC records leaks into the overlay. The adviser package checksums verify, and the package makes no legal conclusion.

Four P2 problems remain:
- The adviser builder has no `--check` mode, and running it with `--check` overwrites tracked files.
- Agreement is measured on label sets, not on matched proceedings, although the docstring says proceedings are matched.
- For "agreed" judgments the ground truth silently takes coder A's rows, including two proceeding-level disagreements.
- The "blind third coder" claim is contradicted by the adjudication file itself.

Conditions for acceptance: fix or explicitly relabel F01–F04. P3 items can be dispositioned.

## Method

- Ran each tool's `--check` with the venv Python (`-I -B`) in the worktree.
- Built a disposable copy of the inputs at `scratchpad/review_c12tools/neg/audit_work/` (C12 tools, metadata and holdout_v3; the C11 scnum/holdout/identity files; the C10 review files and three output files). Confirmed all four `--check` runs pass there, then ran negative controls.
- Reproduced the agreement figures with my own script, `scratchpad/review_c12tools/scripts/agree.py`. It does exact-label set, multiset and proceeding-aligned comparison, plus a vocabulary check.
- Checked the sample independently: overlap with every CSV, JSONL and MD file under `audit_work` outside C12, quotas, strata, text quality and raw paths.
- Rebuilt the ground truth and compared it row by row with its sources.
- Checked the overlay: recomputed the tally, traced each value to C11 `proposed_value` or C12 `reconfirmed_value`, and confirmed with `git show` that the original `case_numbers` at `/home/user/c7@ad77758d` are empty for all 99.
- Adviser package: ran `sha256sum -c`, rebuilt it, imported `verify()` with altered quotes, and grepped for conclusion or validation language.
- Protected-hash check:
  - `git diff --name-status origin/legal-knowledge/v2.5-staging -- legal_knowledge | grep -v audit_work/` returns nothing.
  - Note: `--stat` abbreviates paths with `...`, so the requested `grep -v audit_work` on `--stat` output does not filter. I used `--name-status`.

## Reproduced figures

| Item | Stated | Reproduced |
| --- | --- | --- |
| Sample size and quotas | 150: SC 40, Delhi 30, P&H 30, J&K 25, Allahabad 25 | 150, same quotas; 150 distinct keys, sha256 values and judgment_ids |
| Sample overlap with spent sets (C10 review_A/B 30, WS20 20, REVIEW_SAMPLE 30 [= A∪B], C11 HOLDOUT_SAMPLE 56) | 0 | 0 by judgment_id and by judgment_key; also 0 with C11 ground_truth_A/B, evaluation rows, CALIBRATION-01/02 |
| Agreement, all fields | 136/150 | 136 |
| Printed disposal agreement | 97.3% | 146/150 = 0.9733 |
| Substantive result agreement | 92.7% | 139/150 = 0.9267 |
| Row-count agreement | 99.3% | 149/150 = 0.9933 |
| Coder rows | — | A 207, B 215; all labels exactly in the convention vocabulary |
| Stricter: multiset agreement | — | 135/150 |
| Stricter: proceeding-aligned agreement | — | 134/150 |
| Proceeding level (rows matched on `key()`) | not reported | 177/192 matched pairs agree; 15 A rows and 23 B rows unmatched |
| GROUND_TRUTH_V3 | 215 rows, 37 adjudicated | 215 = 178 BOTH_CODERS_AGREE + 37 ADJUDICATED; 150 judgments; 0 mismatches against source rows |
| Adjudication coverage | 14 DISAGREE | 14/14 adjudicated, no adjudication for any AGREE id; agrees_with: B 14, both 14, A 7, neither 2 |
| Overlay | 99 staged = 73 + 24 + 2; 266 + 3 not applied | STAGED 99; 73 C11-CORRECT, 24 CONFIRMED, 2 NEEDS_CHANGE; NOT_APPLIED unreviewed 266, UNRESOLVED 3; original_value [] matches empty originals for all 99 |
| Adviser package | 59 questions, 70/77 verified | 59 (unique ids); 70 VERIFIED_ON_STATED_PAGE + 7 NO_TEXT_FILE_AT_ad77758d; SHA256SUMS 6/6 OK; MD, QUESTIONS and EXCERPT byte-identical on rebuild |
| Frozen records | unchanged | No path outside `audit_work` differs from staging. Branch-only changes (`staging...25723740`) are 63 additions, all under C12-CONSOLIDATION. The deletions and modifications against the staging tip (AUTH-LEDGER, C8, C9) come from staging being 36 commits ahead, not from this branch. |

## Negative controls

| # | Perturbation (disposable copy) | Result |
| --- | --- | --- |
| NC1 | Added V3H010's judgment_id to the C11 HOLDOUT_SAMPLE (spent) | sample `--check` FAILED (rc 1): exclusion works |
| NC2 | Changed coder B V3H001 substantive to relief_granted | agreement `--check` FAILED; agree_all 135 |
| NC3 | Swapped coder B labels between the two V3H017 proceedings | agreement `--check` **still passes**: proceeding misalignment is undetected (F02) |
| NC5 | Added an adjudication row for an AGREE judgment (V3H001) | truth `--check` **still passes**: the stray adjudication is silently ignored (F09) |
| NC6 | Removed the V3H024 adjudication rows | truth raises AssertionError V3H024: missing adjudication is caught |
| NC7 | Added one of the 266 unreviewed docs to the reconfirmation file as CONFIRMED | overlay `--check` FAILED; STAGED 100, unreviewed 265: no status guard (F08) |
| NC8 | Flipped the DO_NOT_APPLY record's verdict to CONFIRMED | not staged only because its reconfirmed_value is empty (NO_NORMALISED_VALUE) |
| NC9 | Called adviser `verify()` with one word changed / a wrong page | NOT_FOUND / FOUND_ON_OTHER_PAGE: the excerpt check is effective |
| NC10 | Appended a byte to ADVISER_QUESTIONS.csv in a copy | `sha256sum -c` FAILED for that file |

## Findings

### F01 — P2 — adviser_package/tools/build_adviser_package.py:1079-1092, 1015-1020
The builder has no `--check` mode, and the argument is ignored. Running `build_adviser_package.py --check` rebuilt the package and **overwrote the tracked `PROVENANCE_C12.md` and `SHA256SUMS`**. This happened in this review. I restored both files with `git checkout`, re-verified SHA256SUMS (6/6 OK), and the worktree is clean of my changes.

`PROVENANCE_C12.md` embeds the live worktree HEAD. The committed file records HEAD `b4948b0f`, so any rebuild at a later commit changes PROVENANCE and SHA256SUMS. The package is therefore not reproducible with `--check` as claimed. The other three outputs did rebuild byte-identically.

Recommendation: add a real `--check` that builds in memory and compares, writing nothing. Pin the provenance HEAD (or record it as a build parameter) so a rebuild at a later commit does not drift.

### F02 — P2 — tools/holdout_v3_agreement_c12.py:4, 39-42
The docstring says proceedings "are matched on normalised case numbers" and that agreement is judgment level *and* proceeding level. In fact `ka`/`kb` are computed and never used. Agreement is equality of label **sets** plus equal row count, and no proceeding-level metric is output.

As a result, two judgments are counted AGREE while their coders disagree at proceeding level:
- **V3H015**, CA 282/2020: A relief_partly_granted, B unclear.
- **V3H017**: A assigns CA 8452 → allowed/remanded and CA 8453 → dismissed, noting the mapping was "assumed". B codes both under "8452-53" and says the mapping is not printed.

Proceeding-aligned agreement is 134/150, against the stated 136. At proceeding level, 177/192 matched pairs agree and 38 rows cannot be matched. NC3 confirms that swapping outcomes between proceedings goes undetected.

Recommendation: compare per proceeding, aligned on `key()`, with unmatched rows counted as disagreement. Report proceeding-level agreement, and route V3H015 and V3H017 to adjudication. Otherwise, correct the docstring and summary to say "label-set agreement".

### F03 — P2 — tools/holdout_v3_truth_c12.py:2, 24
For AGREE judgments the ground truth takes **coder A's rows** wholesale. Consequences:
- V3H015 CA 282/2020 enters the truth as relief_partly_granted, although B said unclear.
- V3H017 enters with A's *assumed* number-to-order mapping, which conflicts with the convention's "Never infer".
- Neither was adjudicated, so agreed items are in effect overridden in A's favour.
- Non-label fields also come from A only. Among single-row agreed judgments, page differs in 3 and party_specific in 1.

Recommendation: after fixing F02, adjudicate V3H015 and V3H017. Label BOTH_CODERS_AGREE only for rows that agree per proceeding, and record how non-label fields were chosen.

### F04 — P2 — tools/holdout_v3_truth_c12.py:3; commit ed5362e5 message; holdout_v3/ADJUDICATION.csv (reason column)
The tool and the commit describe a "blind third coder", but ADJUDICATION.csv shows the adjudicator knew each coder's label and identity. The reasons read "Disputed: substantive", "Agree A", "'partly' (A) misreads whose relief is measured", "A did not code … file read from reviewer-B copy" and "Not disputed; both coders agree".

Informed adjudication is a legitimate method, but it is not blind, and the claim is unsupported. Independence between coders A and B is asserted in CODING_CONVENTION.md, but no protocol or log evidences it. Of 134 pairs of free-text notes, 5 are identical and 29 have a similarity ratio above 0.8. That is plausible for short factual notes, but it is not evidence of blindness.

Recommendation: change the wording to "third-coder adjudication with sight of both codings", or provide artefacts (an assignment log, prompts) that show blindness. Record how the coders were kept apart.

### F05 — P3 — tools/holdout_v3_sample_c12.py:4, 45-46
The docstring says "text layer present", but the selection checks only `disposition == PROCESSED` and `COMPLETE_FILE_STRUCTURE`. Four selected judgments have `text_quality = NON_READABLE_TEXT_LAYER`: V3H086, V3H087, V3H096 and V3H119. This matters for any text-based extractor score on them.

Recommendation: filter on `text_quality == READABLE` and re-draw, or keep them and correct the docstring. Either way, report extractor results on these four separately.

### F06 — P3 — tools/holdout_v3_sample_c12.py:70
`raw_path` is not checked to be resolvable. V3H035 (`legal_knowledge/judgment_originals/sci/historical/v3.3/navjot_sandhu_2005.pdf`, empty doc_ids) is not in `/home/user/c7@ad77758d data/raw`, and coder A could not find the PDF (ADJUDICATION.csv reason).

Recommendation: validate each `raw_path` against the pinned raw store, or record a store column for each row.

### F07 — P3 — tools/holdout_v3_sample_c12.py:54-57, 69-71
The coder-visible sample carries `stratum`, and `disagreement` means a crawler-vs-extractor outcome contradiction. That gives coders a difficulty hint, although no values are exposed.

Delhi has no `disagreement` candidates, so its 8 slots were reallocated to `other` (Delhi: 9/0/8/13). That is correct per the code, but it is not stated in any artefact.

Recommendation: drop or blind `stratum` in the copy given to coders, and document the Delhi reallocation.

### F08 — P3 — tools/scnum_overlay_c12.py:34
The reconfirmation branch applies to any doc_id present in SCNUM_RECONFIRMATION_C12.csv with verdict CONFIRMED or NEEDS_CHANGE, whatever its C11 `application_status`. NC7 shows that one of the 266 unreviewed records added to that file would be staged.

The current data are clean: the reconfirmation file holds exactly 24 USE_REVIEWER_READING, 4 RECHECK and 1 DO_NOT_APPLY record, and the DO_NOT_APPLY record is UNRESOLVED.

Recommendation: restrict the branch to `st in {APPLY_CANDIDATE_USE_REVIEWER_READING, RECHECK_LOWER_COURT_TYPE_IN_HOST}`, and make the tool fail if any other status appears in the reconfirmation file.

### F09 — P3 — tools/holdout_v3_truth_c12.py:21-26
There is no assertion that adjudicated ids are a subset of the DISAGREE ids, and none that the adjudication covers each disputed proceeding. A stray adjudication row for an AGREE judgment is silently ignored (NC5).

Recommendation: assert `set(adj) == DISAGREE ids`, and check that the adjudicated proceedings cover both coders' proceedings.

### F10 — P3 — tools/holdout_v3_agreement_c12.py:27-28
`lab()` keeps only the first space-separated token, lower-cased. A free-text label such as "dismissed as withdrawn" would therefore match "dismissed", and blank compared with blank counts as agreement. This has no effect today: all 422 coder rows use exact vocabulary labels and none are blank.

Recommendation: compare exact labels, and fail on any label outside the vocabulary or any blank label.

### F11 — P3 — adviser_package/tools/build_adviser_package.py:24, 45
The builder reads inputs outside the repository: `/home/user/c7` (git) and `SCRATCH/c12/reviews/fable_review_pr46_c69eee41.md`, an unversioned scratchpad file. A rebuild therefore depends on this machine's state.

Recommendation: vendor or pin the PR46 review into the repository, and record the c7 commit as a parameter.

### F12 — INFO
The adviser package keeps the "NO LEGAL VALIDATION" banner, top and bottom, and states that readings are AI and not human-confirmed. Its questions are framed as questions, with competing readings drawn from existing artefacts. The "is overruled" and "stands overruled" hits are quotations or tool labels, not conclusions. The overlay marks every record `AI_DOCUMENTARY_REVIEW_NOT_LEGAL_VALIDATION` and `ORIGINAL_UNCHANGED`. I found no claim of legal validation.

### F13 — INFO
Ten sample judgments appear in the C11 extraction review items, but only in its section `3_proposition_origin`, not in its outcome sections. They are not spent for outcome evaluation.

### F14 — INFO
During this review another agent changed `TASK_REGISTER.md`, and `extractor_v3/` and `holdings_eval/` appeared untracked. These are outside scope, and I did not touch them. Of my own changes, only the F01 incident touched tracked files, and it was reverted.

## Files

- `scratchpad/review_c12tools/review_c12_coordinator_tools_25723740.md` (this file)
- `scratchpad/review_c12tools/findings.csv`
- I deleted the helper script (`scripts/agree.py`) and the disposable copy (`neg/`) after the run, so that only the two requested files remain. The method above is enough to recreate them.
