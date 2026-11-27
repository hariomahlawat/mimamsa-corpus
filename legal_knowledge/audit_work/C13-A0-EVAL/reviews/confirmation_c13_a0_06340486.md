# Confirmation review: C13-A0 v1.1 at `06340486`

> **Copy note (C13-A0 author).** Copied without changes: this report lists judgment keys and hashes only and quotes no judgment text. The reviewer's original and evidence files stay in the coordinator scratchpad (`scratchpad/c13/reviews/a0/`). See `../EXPOSURE_REGISTER.md`.


- **Branch:** `claude/c13-a0-eval`. Read-only review of a scratch export at `reviews/a0/src2`; I made no commits.
- **Follows:** `review_c13_a0_5e07e010.md` (ACCEPT WITH CONDITIONS, findings F01–F16).
- **Date:** 2026-11-25.
- **Verdict: NOT ACCEPTED — one new P1 (C01), which the branch can fix quickly with no redraw.** Everything the author claimed is confirmed. Once C01 is fixed and checked, A0 can be accepted.

## 1. New finding

### C01 (P1): holdout text exposed by committed review evidence

**What happened.** Commit `a4865e76` added my GA0 reviewer scratch to the branch under `C13-A0-EVAL/reviews/`. Two of those files quote holdout judgments word for word:
- `reviews/frame_sample/*.txt` holds about 1,800 characters from the start and 2,500 characters from the end of each sampled judgment;
- `reviews/party_ppv.txt` holds the matched cue sentences and the last 600 characters of each judgment.

The endings carry the **operative disposal**, which is the label H-OUT codes.

**Who is affected.** 18 holdout judgments are exposed:
- 17 in H-OUT;
- 3 in H-HOLD;
- 1 in H-REL.

**What is unprotected.** Only 2 of the 18 (JK-c72781c1391284ec and JK-f3a273f09da43b54) are in `PRE_EXPOSED_SUBSET.csv`. The other 16 have no protection:
- JK-1aa3838f30b79141 (H-OUT and H-HOLD)
- JK-204366fba3be87b1
- JK-2890b7b47a443252
- JK-3775f27e8c6d1265
- JK-3c00f93d93f6804f
- JK-566556d10756008c
- JK-6ad23cfb89323b87
- JK-7b198edc7afe64e3
- JK-81730e236b81cfd5
- JK-8d5739ca50ff6b89
- JK-9c9c75f4aff795be
- JK-9da05d5ec12aa6fb (H-OUT and H-REL)
- JK-a5fe29566f0774ec
- JK-cbf165489b0d8623
- JK-dc279e9f44680bd8
- JK-e3c9f7c5d9d5a27c

The rest are H-OUT only.

**Why it is a P1.** A2 and A3 extractor authors work on descendants of this branch. Under protocol section 7, a holdout text visible to them is contamination. My scratch evidence caused this, because I did not mark the excerpt files as evaluator-only.

**Requested fix (before any A2 or A3 freeze):**
1. On the branch head, `git rm` the text-bearing files: `reviews/frame_sample/*.txt` and `reviews/party_ppv.txt`. Keep `frame_sample/SAMPLE.csv` (features and labels only) and the scripts. History stays as it is; do not force-push.
2. Add the 18 keys to `PRE_EXPOSED_SUBSET.csv` under a new category, `REVIEW_TEXT_EXPOSED`, with `primary_sensitivity=true`. Report the headline with and without them.
3. Record the exposure in the protocol change log. Tell the A2 and A3 authors that they must not open `reviews/`, and have them confirm whether they have already viewed it. If an author has viewed it, record that in the freeze record.
4. Correct the reserve decision's statement that "nothing has been coded or viewed". Three H-HOLD items (JK-1aa3838f…, JK-c72781c1…, JK-f3a273f0…) were viewed by the reviewer. The decision itself is not data-driven, so it stays valid.

## 2. Confirmations

| Check | Result |
| --- | --- |
| `c13_check_all.py` (now including sensitivity, CI simulation and power) | **ALL CHECKS OK**; SHA256SUMS OK |
| Tests (C13 suite, now including `test_..._v11.py`, plus C12 research isolation) | **73 passed** |
| H-OUT unchanged | `SAMPLE.csv` `0df7bd70…`, `DESIGN.json` `7b3078f2…`, `ITEM_MAP.csv`, coder sheets: **identical** to `5e07e010` |
| H-REL unchanged | `SAMPLE.csv` `000d057c…`, `DESIGN.json` `22dc344e…`, `ITEM_MAP.csv`, coder sheets: **identical** |
| H-HOLD = 75 + 38 | `SAMPLE.csv` `d10f6b95…` and `RESERVE.csv` `3d8dc7c8…` are unchanged. The regenerated packets list exactly these 113 sha256 values. `HOLDOUT_REGISTRATION.json`, the frame and the exclusions are unchanged |
| Reserve decision recorded before coding | `decisions/H-HOLD_RESERVE_DECISION.json` matches sha256 `d6d9a96a6695…`, as listed in SHA256SUMS and the protocol. Commit `06340486` (11:15:34Z) records FULL_OPEN. All six coder sheets in the tree are blank (0 filled rows), and no coded, agreement or truth file exists. The "nothing viewed" wording must be corrected (C01 step 4) |
| Leakage controls | Rebuilt spent set: 316 of 316 judgments are in the unchanged 682-key list, and 0 are in H-OUT, H-HOLD, the reserve or H-REL. The negative-control code path is unchanged |
| F08 | Model output pasted into `notes` is now detected, and `--other-coder` is required with `--completed` |
| F09 | The X/Y seed is secret per run (`secrets.token_hex`); the key can no longer be recomputed from the code |
| F07 | `--store` is required |
| F02 | The protocol states that the outcome lower-bound pass needs a true precision of about 0.99 |
| F03 | The party-specific breakdown is descriptive only (`DESCRIPTIVE_ONLY` status) |

## 3. F01: my own simulation of `design_cp`

This is an independent population generator (`scripts/sim_cp.py`), not the author's `c13_ci_sim.py`. It uses:
- the exact H-OUT N_h/n_h;
- multi-proceeding clusters of up to 10 proceedings;
- an 85% answer rate;
- cluster correlation through a share of all-or-nothing judgments;
- 1,000 replicates per scenario, 18 scenarios in all.

Nominal level 95%.

| Base precision | Homogeneous | Heterogeneous, 30% clustered | Heterogeneous, 80% clustered |
| --- | --- | --- | --- |
| 0.90 | 0.973 | 0.978 | 0.964 |
| 0.93 | 0.976 | 0.969 | 0.967 |
| 0.95 | 0.979 | 0.977 | 0.978 |
| 0.97 | 0.984 | 0.980 | 0.979 |
| 0.98 | 0.991 | 0.991 | 0.978 |
| 0.99 | 0.996 | 0.982 | 0.994 |

**Coverage is 0.964–0.996** in every scenario. That confirms the author's claim of ≥0.965, give or take 0.001 of Monte Carlo error, and the F01 defect (old bootstrap coverage 0.83) is fixed.

**Power.** I computed P(lower bound ≥ 0.95):
- at a true precision of about 0.95: 0.000–0.014;
- at 0.985 (homogeneous): 0.73;
- at 0.991 (homogeneous): 0.88;
- in heterogeneous scenarios with a true value of about 0.97: 0.09–0.24.

This agrees with the protocol's new statement that a lower-bound pass needs about 0.99. The interval is conservative, as intended.

## 4. Open findings

- **P1:** C01. Fix before any freeze.
- **P2:** none.
- **P3:** none new.

Evidence: `scripts/sim_cp.py`, `sim_cp_confirm.json`, `my_spent_core2.json`, `conf_checkall.txt`, `conf_tests.txt`.
