# Confirmation review (round 2) of the coordinator-written C11 tools

- **Reviewer:** Fable 5.2 (claude-fable-5-2)
- **Date:** 2026-11-24
- **Head reviewed:** `claude/c11-judicial-quality` at `bfd295d1` (fixes for round 1, which was at `c0c7362f`)
- **Scope:** narrow confirmation of C-01 to C-04, the P3 fixes and every `--check`. Uncommitted `relations/` files were ignored as instructed.
- **Findings:** `fable_review_coordinator_c11_r2_findings.csv`

## Verdict

**ACCEPT.** C-01, C-03 and C-04 are closed. C-02 is closed for the defects named in round 1, but T5 still holds a sizeable share of real leads. Three P3 residuals remain; none blocks the commit.

| Round-1 id | Status | Residual |
| --- | --- | --- |
| C-01 release filter | **Closed** | R2-01 (P3) |
| C-02 excluded ranking | **Closed for the named defects** | R2-02 (P3) |
| C-03 affected records | **Closed** | none found |
| C-04 marking scan | **Closed** | none |
| P3 items | Fixed as stated, two deferred | R2-03 (P3) |

## C-01: release filter

- The filter now reads the identity register (revision 2). I recomputed the multi-copy set independently: 414 judgment ids. **None keeps a released outcome.**
- `JK-07de16dabda06223`: all 44 copies are `OUTCOME_UNVERIFIED` with reason `MULTI_COPY_JUDGMENT_PER_PROCEEDING_SPLIT_REQUIRED`.
- Downgrade counts match the disposition: 226 shared text, 74 multi-copy, 278 multi-number label.
- `v2_outcome_original` equals the frozen outcome on all 3,948 rows; no other column changed.
- The two files in the not-merged group `STGN-88c999976778` keep their outcomes. That is correct: the register treats them as separate judgments.
- **R2-01 (P3), released outcomes left on multi-proceeding files:**
  - Two files are registered under more than one proceeding but are sole copies with a single-number label: `J-00b8c81fc752d46f` (W.P.(C) 2026/2020 and 2107/2020, released "dismissed") and `J-b5cef1571163212e` (four writ petitions, released "transferred").
  - 25 released rows have a range label such as "Civil Appeal 9367-9369 of 2011" (Babita Puniya). The new rule counts a range as one case reference. 24 of the 25 are Supreme Court rows.

## C-02: excluded ranking

- New tiers match the disposition: T1 1,790 / T2 1,570 / T3 706 / T4 317 / T5 3,694. All 8,077 rows still say `NOT_ACQUIRED_REQUIRES_OWNER_APPROVAL`.
- **Naval:** 649 rows moved from T1 to T5. Only two T1 titles now contain a bare "naval", and both have another valid signal.
- **Versus and respondent-side rank:** fixed. "COL. AVTAR SINGH SEKHON versus UNION OF INDIA", "LT. COL. KHAJOOR SINGH versus THE UNION OF INDIA" and "UNION OF INDIA Vs EX NK VIKRAM SINGH" are now T1.
- **MIN.OF DEFENCE:** fixed; no T5 title contains it.
- **Coast Guard:** all 51 moved from T4 to T2.
- **T3 defence land is intact:** 706 of the former 708 remain; the other two moved to T2. No defence-land term is left in T5.
- **Re-sample (seed 20261125).** T1: 20 of 20 carry a real military signal; about five are peripheral (a private dispute with a colonel, "JAWAN GUARDS SECURITY SERVICES"), which is acceptable for a lead list. T5: 9 of 20 are still plain service or defence matters, against 11 of 20 in round 1.
- **R2-02 (P3), T5 still under-ranks.** About 817 of the 3,694 T5 titles (22%) name the Union together with a rank or the word "defence". Remaining causes:
  - a service-number prefix before the rank ("Vs NO IC 44661A COL JEETENDRA GULATI", "JC 432597P NB SUB SIKANDER SINGH");
  - punctuation straight after the rank ("EX.SUB(CLK)", "EX SEP/SK");
  - "NAIK" is accepted on the respondent side only ("EX-NAIK SANWAT RAM Vs UOI");
  - J&K forms "U.O.I.TH.DEFENCE SECY", "UNION OF INDIA AND ORS. (DEFENCE)", and the typo "MINISRTY OF DEFENCE".
- `excluded/` still has no README (round-1 C-09, second half).

## C-03: affected research records

- Now 32 records and 37 record-case pairs, each with `match_basis` (28 by name, 5 by C5 crosswalk, 4 by C8 gap matrix).
- All seven named records are present with the right case: AFT-001, AFT-033, AFT-044 (Parashotam); AFT-014, V7-SC-14, V7-SC-16 (Tarsem); PEN-049 (Girish).
- **Further dependency paths: none found.** I tested two independently of the tool's method:
  - every record citing the source ids of the six cases (`V7-S08`, `V7-S09`, `V7-S11`, `V6-S14`, `V6-S17`, `V6-S18`, `V6-S19`) is paired with that case;
  - no unlisted record refers to a listed record id (for example through a workflow reference).
- Action texts are now adviser questions. The Ram Avtar and Dharamvir finding texts no longer hard-code counts, and the Dharamvir pinpoint reads "para 28 (p.27; 28(ii) read with 28(i))".

## C-04: marking scan

- The inventory has `pages` and `pages_without_text_layer`. Totals agree with my round-1 count: 892 pages, 73 without text, in 17 copies.
- Statuses: 31 all-text, 14 partial (with the number of unscanned pages in the status), 3 `NOT_SCANNED_IMAGE_ONLY`.
- The DESW Entitlement Rules letter (35 of 35 pages) and the Rajya Sabha extract (1 of 1) are both `NOT_SCANNED_IMAGE_ONLY`. So is `C5-SRC-P0-AR-AMD-AR-031~C1` (2 of 2).
- The register value is passed through as `NOT_OBSERVED_OR_NOT_CHECKED`, and the class is `NO_MARKING_RECORDED_IN_REGISTER_NOT_CHECKED`. The package says the unscanned pages need a visual check.

## P3 fixes

| Item | Result |
| --- | --- |
| Git-object claim scoped to the shallow store | Fixed (package line 12) |
| Composition count | Fixed: the wrong "16" is gone and the text points to the inventory |
| 47 anchor rows | Stated in section 1. **R2-03 (P3):** section 3, step 5 still says "all 42 anchors" |
| `holdout_sample_c11.py --check` | Fixed: reproduces on both interpreters, and the file's modification time is unchanged after the run |
| Delhi shortfall | Explained in `HOLDOUT_EVALUATION.md` |
| Coast Guard | Reclassified to T2 |
| Curated drift and action wording | Fixed |
| Unit tests for the seven tools | Deferred, as stated |
| Bedi and Ratan Singh comparison labels | Deferred, as stated |

## Checks run at `bfd295d1`

All reproduce: `preservation_c11.py` (4 files), `hf_verify_c11.py` (2), `excluded_rank_c11.py` (2), `holdout_sample_c11.py` (venv and python3.11), `eval_holdout_c11.py` (2), `release_filter_c11.py` (2), `curated_c11.py` (3). In-scope paths were clean in `git status` before and after.

I did not re-run the full test suite or the Hugging Face reads; neither is affected by this commit's changes.

## Housekeeping

No commits, no working-store changes, and no files written to the worktree. Nothing needed to be kept under `rev_coord2/`.
