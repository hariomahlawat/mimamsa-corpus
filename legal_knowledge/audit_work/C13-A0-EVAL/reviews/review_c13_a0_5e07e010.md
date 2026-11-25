# Independent review: C13-A0 evaluation infrastructure (GA0 gate)

> **Redacted copy (C13-A0 author, after confirmation finding C01).** Short quotations of judgment text and case details that could hint at holdout content were replaced with `[REDACTED: ...]`. The reviewer's unredacted original stays in the coordinator scratchpad (`scratchpad/c13/reviews/a0/`). Evidence files that quoted holdout text were removed from this folder; see `../EXPOSURE_REGISTER.md`.


- **Reviewed:** branch `claude/c13-a0-eval` at commit `5e07e010`, output `legal_knowledge/audit_work/C13-A0-EVAL/`.
- **Reviewer:** independent; I did not write this work. Read-only review. I worked in a scratch export (`git archive 5e07e010`) under `scratchpad/c13/reviews/a0/src`. I made no commits.
- **Date:** 2026-11-25.
- **Verdict: ACCEPT WITH CONDITIONS.**
  - The holdouts are valid, deterministic and free of spent judgments. They can stay frozen as registered.
  - The conditions are protocol and harness amendments (findings F01–F05). They must be committed as PROTOCOL_C13 v1.1 **before GA1, before any coding starts, and before any extractor is frozen**. None of them requires redrawing a holdout.
- **Findings:** no P1. Five P2s (F01–F05) and eleven P3s. Full list in `review_c13_a0_5e07e010_findings.csv`.

## 1. Reproduction

| Check | Result |
| --- | --- |
| `c13_check_all.py` (features, exclusions, frame, sampler, packets, score self-test, SHA256SUMS) | **ALL CHECKS OK**. It needs `MIMAMSA_C12_ADDITIONS` set when run outside the worktree (F16) |
| Each tool's `--check` separately | All OK. Stage 1 reproduces byte for byte from `/home/user/c7` at `ad77758d` plus the sha-verified C12 additions copy |
| Tests | **48 C13 tests pass** (17 coding + 16 frame + 7 score + 8 stats), run with `MIMAMSA_C13_FULL=1`. `test_legal_audit_c12_research_isolation.py` also passes (54 tests in total) |
| Holdout sha256 values against `HOLDOUT_REGISTRATION.json` | All 7 registered files match |
| Independent redraw | My own implementation (lowest SHA-256(seed\|judgment_key) per design cell from `FRAME_JUDGMENTS.csv`) reproduces H-OUT exactly. It also reproduces H-HOLD, its 38-item reserve, and every N_h, π and weight |
| Frame totals | 4,281 records, 3,973 files, 3,637 judgments. 121 non-usable records belong to 90 judgments; 89 judgments have a non-usable representative copy, and one has a usable copy. 682 excluded keys, 679 of them in the frame. 2,812 eligible. All confirmed |

## 2. Leakage and spent sets

**Independent rebuild.** I built my own identity map from `FRAME_RECORDS.csv` plus the C11 register. With it I rescanned:
- the C11 holdout (56), including `HOLDOUT_IDS.txt`;
- the C11 `dev_gold.json` (50). The author does not list this file, but `DEV_EVALUATION_ROWS.csv` covers all 50 of its judgments;
- the C12 V3 holdout (150), including all six coder files and `ADJUDICATION.csv`;
- the C12 holdings reference (30), including `holdings_eval/EVALUATION_ROWS.csv`;
- `dev_gold_v3.json`: 138 keys, of which 136 are judgments; the other 2 are `_note` and `_source`;
- `DEV_IDS.txt` (82).

**Result:**
- The union is 316 judgments. Every one is in the author's 682-key list.
- **None is in H-OUT, H-HOLD, the reserve or H-REL.**
- The C10, C11 and C12 review, dev and adjudication files have **zero** hits on holdout judgments. I checked this by scanning every CSV, JSON, JSONL, TXT and MD file under `audit_work`, excluding C13.

**Duplicate identities.**
- `HF_JUDGMENT_DUPLICATES` and the C11 `SAME_TEXT_GROUPS` link no holdout judgment to a spent judgment.
- The only multi-key group that touches a holdout is `DUP-NC-2018INSC185`. Both of its members (JK-48e3c2db…, JK-8a0be890…) are in H-OUT, but they are **different judgments**: [REDACTED: party name and the nature and dates of the two decisions]. This is correct.
- A frame-wide MinHash search (4,254 texts) and a holdout-vs-spent shingle-containment search found **no same-judgment duplicate** between a holdout and a spent judgment. They did find near-identical *sibling* orders: separate proceedings decided in identical terms. See F06.

**Negative control.**
- I injected `J-9e3b82ac12054e07`, an H-OUT item, into `DEV_IDS.txt`. `c13_exclusions --check` failed, the sampler `--check` failed on all 7 holdout files, and `test_no_spent_or_ineligible_unit` and `test_inclusion_probabilities_match_frame_counts` failed.
- `assert_drawable` refuses a spent unit.

**Leakage verdict: CLEAN.**
- No spent judgment and no duplicate identity in any fresh holdout.
- Pre-exposure that the spent list does not cover:
  - 4 holdout judgments with curated or KB content (F04);
  - 8 holdout judgments with a ≥0.90-containment spent sibling (F06).

**Restricted material.**
- RM-001 (sha `4284820e…`, doc_id `regs-regulations-for-the-air-force-reprinted-edition-2000`) appears only as the exclusion constant in `c13_common.py`.
- No output contains its source sha, its derived sha values or its doc_id.
- The frame reads `type == judgment` only, so the file is never opened.

## 3. Sampling and weighting maths

- **Inclusion probabilities and weights.** π = n_h/N_h and w = N_h/n_h are correct for H-OUT, H-HOLD and H-REL. The test suite and my independent recomputation agree. Every holdout is an unconditional SRS within its cells.
- **Size arithmetic** checks out:
  - Wilson ±2.74pp at p = 0.95 with n = 255;
  - Kish design effect 2.00, giving ±3.96pp weighted;
  - n = 253 for 80% power;
  - H-HOLD n_eff 185 (recall) and 124 (precision), with a cluster design effect of 1.26.
- **Simulation.** I ran 300 replicates on a synthetic finite population with the exact H-OUT N_h/n_h, multi-proceeding clusters, an 85% answer rate and a known true ratio. The harness used the author's `c13_stats` functions with 600 bootstrap replicates.

| Scenario | True | HT mean (sd) | Weighted bootstrap 95% coverage | Kish-Wilson coverage | Unweighted Wilson coverage of population value | P(MET_LOWER_BOUND) |
| --- | --- | --- | --- | --- | --- | --- |
| Heterogeneous by court and stratum | 0.9488 | 0.9491 (0.0145) | **0.923** | 0.977 | 0.867 (design bias, as expected) | 0.043 (true value is below target) |
| Uniform p = 0.98 | 0.9832 | 0.9825 (0.0086) | **0.830** | 0.967 | 0.977 | 0.813 |

- The HT ratio is unbiased.
- The **weighted bootstrap under-covers**, worst in the high-precision regime where the 95% target sits. Many cells with n_h of 10–31 contain no errors, so their bootstrap variance is zero, and those cells carry weights up to 28.
- The pre-registered `MET_LOWER_BOUND` rule uses exactly this lower bound (F01).
- With an honest interval, the Kish-Wilson lower bound at true precision 0.98 is 0.938. So `MET_LOWER_BOUND` is practically unreachable unless the true precision is about 0.99 or higher. The 80% power claim holds only for the unweighted test (F02).
- H-HOLD's ±7pp ignores its own Kish design effect from unequal weights (1.49). The weighted half-width is about ±8.5pp.
- H-REL's overall Kish design effect is 7.5. The weight on the 20 no-detected-citation pages is 1,199 for HC and 222 for SC, so weighted recall will be very imprecise. Relations has no owner target, but the protocol should say this.

## 4. Frame correctness (40 records against c7 `ad77758d` text and meta)

**Sample.** Seeded: 22 random records, 6 non-usable, 6 party-specific candidates and 6 batch records. The details, with head and tail excerpts, are in `scratchpad/c13/reviews/a0/frame_sample/`.

| Attribute | Correct | Notes |
| --- | --- | --- |
| Court | **40/40 (100%; Wilson lower bound 91%)** | The frame court equals the meta court, and the text header agrees in every case |
| Text quality | **40/40** under the pre-registered rules | Recomputed independently: page letters, letter share, usable pages, text method. GARBLED (letter share 0.43 and 0.06) and TRUNCATED (empty pages) are truly unusable. One IMAGE_ONLY record has readable OCR text (letter share 0.89) but is excluded by rule 5 (F15) |
| Stratum (intended meaning) | **24/38 = 63%** (95% CI 47–77%). Random subsample: **16/22 = 73%** | 2 garbled records could not be assessed. The 14 errors are listed below |

**Stratum errors (14):**
- 7 false PARTY_SPECIFIC;
- 3 pension matters labelled OTHER;
- 2 Supreme Court multi-proceeding judgments missed, because SC meta carries no case numbers ([REDACTED: quoted case-number text from two judgments]);
- 2 false BATCH_OR_MULTI, because the AFT OA number in the cause title is counted as a second proceeding.

**Party-specific cue.** In an additional seeded sample of 25 of the 60 judgment-level candidates, I found 3 true party-differentiated disposals. Combined with the frame sample, that is **3/27 unique, PPV ≈ 11% (95% CI 4–28%)**. The regex fires on AFT-writ boilerplate [REDACTED: two quoted sentences from candidate judgments].

**Impact on validity.** Validity is unaffected: strata only define cells, the weights are correct for any partition, and subset results use gold labels. Efficiency and the owner's party-specific breakdown are affected, because H-OUT will hold very few gold party-specific units (F03).

## 5. Coder kit

**Blinded sheets** carry only the pointer columns and blank coding fields:
- no stratum, weight, model output or other coder's labels;
- per-coder item order;
- opaque, seeded item ids.

**Leak checks, by deliberate failure:**
- A pre-filled label, pre-filled notes, an extra `model_output` column or an extra `hint` column all fail on a blank sheet.
- On a returned sheet, the check fails when another coder is named, when a model token appears in a coded field, or when an extra `model_pred` column is present.
- It **passes** when model output is pasted into `notes`: the notes, excerpt and legal_issue fields are exempt from the token scan.
- It **passes** when `--other-coder` is omitted.
- It cannot detect another coder's labels copied without attribution. This is inherent, and the protocol says independence rests on process (F08).

**Adjudication:**
- The sheet holds only the DISAGREE items as X and Y, with no coder ids. X is coder A for 52% of 100 items.
- A coder name injected into the sheet is caught.
- The sealed key can be **recomputed from the seed constant in the code** (F09).
- `build_truth` enforces exact adjudication coverage, as in the author's tests.

**Agreement.**
- Cohen's kappa and Krippendorff's alpha match hand computation (κ = 0, α = −0.333 on a constructed case).
- Proceeding-level strict agreement treats an unmatched unit as a disagreement.
- The test reproduces C12 V3 item agreement for 149 items.

**Versioned store.** It is immutable and tamper-evident, per the tests. The harness checks the store only when `--store` is passed (F07).

## 6. Protocol (`PROTOCOL_C13.md` v1.0)

| Requirement | Status |
| --- | --- |
| Outcome: strict precision ≥95% and coverage ≥85% per field; court-, proceeding- and party-specific results; evidence anchor; weighted | **Stated** (s.1, s.5, s.8). The met status is computed only overall, not per breakdown (F12) |
| Holdings: precision ≥80% and recall ≥60%, interim and not operational acceptance | **Stated** (s.1) |
| Freeze before evaluation | **Stated**: registration ancestry (s.3), GA3, and no post-hoc changes (header) |
| No tuning on holdouts | **Stated** (s.7: holdout texts are never read for development; authors use dev and spent sets only) |
| Unreadable files handled explicitly | **Stated at frame level**: five explicit states, the non-usable population listed, results restricted to USABLE text. **Missing at coding level**: no rule for an item found uncodable or out of scope during coding, and gold `unclear`/`other` shrinks coverage denominators without an explicit reporting rule (F05) |
| Shortfalls reported without manipulating the population | **Stated**: targets are never lowered, contamination is listed and not dropped, and a shortfall is reported as a shortfall |

## 7. Conditions for acceptance (PROTOCOL v1.1, before GA1)

1. **F01:** replace the weighted percentile-bootstrap lower bound in the met rule with a conservative bound, for example the minimum of the Kish-Wilson and bootstrap lower bounds, or a smoothed or BCa stratified bootstrap. Add a coverage-simulation test.
2. **F02:** restate the size and power justification for the weighted headline: H-OUT n_eff about 127, H-HOLD Kish design effect 1.49, H-REL Kish design effect 7.5. Tell the owner that `MET_LOWER_BOUND` for outcome is practically unreachable below a true precision of about 0.99.
3. **F03:** state the expected number of gold party-specific units in H-OUT. Pre-declare that the party-specific breakdown is descriptive, or a stated shortfall, if n is small.
4. **F04:** register a pre-exposed subset and report every headline with and without it:
   - 4 holdout judgments with curated or KB content (JK-16dcc07543999d26 in H-HOLD and H-REL; JK-76ec35cd7ab232b5, JK-88f84411abdb3028 and JK-05e9484593272fe0 in H-OUT);
   - for case numbers only, the 27 judgments in C11 `SCNUM_INDEPENDENT_REVIEW`.
5. **F05:** add a coding-time rule: an item stays in the sample, carries an explicit not-codable code, is counted and reported, and is never replaced. The count of gold `unclear`/`other` units is reported beside coverage.

The P3 items should be fixed before GA2 or GA4 as noted in the CSV. The reserve opening (F11) must work before GA2.

## Artefacts (reviewer scratch, not committed)

All under `scratchpad/c13/reviews/a0/`:
- `scripts/` holds `rebuild_spent.py`, `scan_all.py`, `neardup.py`, `fullfuzzy.py`, `sim_ci.py`, `frame_sample.py`, `party_ppv.py` and `leak_tests.py`;
- `my_spent_core.json`, `neardup_holdout_vs_spent.csv`, `fuzzy_frame_pairs.csv`, `sim_hetero.json`, `sim_p98.json`, `frame_sample/`, `party_ppv.txt`, `leak/`;
- `src_neg/` holds the negative-control copy.
