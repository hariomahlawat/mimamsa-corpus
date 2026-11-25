# Pre-integration review: C13 Track A frozen extractors A2, A3 and A5 into staging

- **Reviewer:** an independent AI reviewer instance. It did not author, code, adjudicate or evaluate any of this work. It is not a legal reviewer.
- **Date:** 2026-11-25.
- **Staging:** `origin/legal-knowledge/v2.5-staging` at `dbe40b4f`. This differs from the merge-base `a4c0c382` of all three branches: staging has since gained the C13 tranche (GOV, A4, A6, B0/app, PR #53/#54).
- **Branches reviewed:** none was modified.

  | Branch | Freeze commit | Merge-base |
  | --- | --- | --- |
  | `claude/c13-a2-outcome` | `9cdd5008` | `a4c0c382` |
  | `claude/c13-a3-holdings` | `a520aa3a` | `a4c0c382` |
  | `claude/c13-a5-graph` | `e15af208` | `a4c0c382` |

  The A5 freeze delta is `d09b7d91..e15af208`, excluding the A0 merge `bf791e4b`.
- **Blind results used:** `claude/c13-eval` `20a4e55d`, `legal_knowledge/audit_work/C13-EVAL/eval/RESULTS_C13.md`.
- **Scratch:** `scratchpad/c13/tmp-review/`.
  - Worktrees: `trial` (staging plus the three merges) and `base` (staging), both detached.
  - Scripts: `scripts/leakscan.py`, `scripts/idscan.py`, `scripts/attrib.py`.
  - Logs: `logs/`.

## 1. Summary of checks

| # | Check | A2 | A3 | A5 (freeze delta) |
| --- | --- | --- | --- | --- |
| 1 | Frozen/protected records unchanged | PASS | PASS | PASS |
| 1 | Changes confined to own folder + tests (+ A0 registration) | PASS | PASS | PASS |
| 2 | RM-001 absent from every output | PASS | PASS | PASS |
| 3 | Candidate status on outputs | PASS | PASS | PASS |
| 4 | Honest claims / GA4 pointer | FAIL (A2-01, A2-02) | FAIL (A3-01) | FAIL (A5-03) |
| 5 | Holdout leakage, dev/training artifacts | PASS | FAIL (A3-02); X-01 | PASS; X-01 |
| 6 | unittest, no pytest-only files, `--check` | PASS; A2-03 reproducibility gap | PASS | FAIL after merge (A5-01, A5-02) |
| 7 | Trial merge | clean | clean | clean merge, broken tests (A5-01, A5-02) |

### Detail on checks 1, 2, 3, 6 and 7

**Protected records** (`git show <ref>:<path> | sha256sum`, identical at staging and at each freeze commit).

| Record | sha256 |
| --- | --- |
| `records_658.jsonl` | `9a8f0d193065…` |
| `cases_53.jsonl` | `8b8d53cd1434…` |
| CALIBRATION-02 `source_authentication_register.csv` | `cfe5f4081997…` |
| `AUTH-LEDGER/` tree | `eed99c62…` at all four refs; `effective/` holds only `v0000` |

**Scope of each diff against the merge-base.** Every diff is add-only (`A`). No `M` or `D` appears in any branch.

| Branch | What it adds |
| --- | --- |
| A2 | 52 files in `C13-A2-OUTCOME/`, plus `tests/test_legal_audit_c13_outcome_v4.py` |
| A3 | 50 files in `C13-A3-HOLDINGS/`, plus 2 holdings tests |
| A5 | 82 files in `C13-A5-GRAPH/`, plus 4 graph tests. The freeze delta itself adds `freeze/` (4 files), `tools/predict_hrel_c13.py` and 5 lines of `SHA256SUMS` |

Each branch also carries `C13-A0-EVAL/` (63 files) and the 6 `test_legal_audit_c13_eval_*` tests through the A0 registration merge. These are **byte-identical to `f1d61f71`** in all three branches (`git diff f1d61f71 <freeze> -- C13-A0-EVAL tests/test_legal_audit_c13_eval_*` is empty). See X-02.

**RM-001.** The sha `4284820e…` and the doc_id `regs-regulations-for-the-air-force-reprinted-edition-2000` were searched in every file of the three output folders, `.gz` decompressed, and in `C13-A0-EVAL/` and `tests/`.
- They occur only in guard code and tests: A2 `extract_v4.py`, A3 `c13_corpus.py`/`holdings_c13.py`, A5 `common_c13.py`, and the test files.
- They also occur in exclusion prose: the A5 `README.md` and `reviews/identity_check.txt`, and A0 `reviews/`.
- No data or output row contains either. `test_legal_audit_restricted_material` passes on the trial merge.

**Candidate status.**
- A2 `outputs/OUTCOMES_V4.csv`: 13,327 of 13,327 rows are `AUTOMATED_CANDIDATE_NOT_VERIFIED`. `FREEZE_V4.json` and `PREDICTIONS_INFO.json` carry the same status.
- A3 `outputs/HOLDINGS_C13.jsonl`: 3,268 of 3,268 rows are `AUTOMATED_CANDIDATE_NOT_VERIFIED`, with `verification = NOT_VERIFIED_RATIO_NOT_DETERMINED`.
- A5 contract export: every record is `AUTOMATED_CANDIDATE_NOT_VERIFIED`, with `review_ref` and `evaluation_ref` null. This is asserted by a test.
- The holdout prediction files are in scorer format, with no status column, which is acceptable. Their info and manifest files carry the status.
- No document claims legal validity.

**Tests.**
- All 13 new test files use `unittest.TestCase` only. There are 0 pytest imports and 0 module-level `test_` functions. The unittest counts match the method counts: A2 22, A3 17 (8+9), A5 51, A0 75.
- **No pytest-only file was found.**
- Suite runs (`python -m unittest discover -s tests -p "test_legal_audit_*.py"`):

  | Tree | Python | Result |
  | --- | --- | --- |
  | Staging baseline | system `/usr/bin/python3.11`, stdlib only, as in CI | 833 tests: 1 failure (pre-existing A6, X-03) |
  | Trial merge | system `/usr/bin/python3.11` | 998 tests: 2 failures, 1 error. Two are new and come from A5 (A5-01, A5-02); the third is the pre-existing A6 failure |
  | Trial merge | venv Python 3.13, with fitz and jsonschema | 998 tests: 1 failure (A5-01b), 2 m 46 s |

**Reproduction on the trial merge.**

| Command | Result |
| --- | --- |
| A2 `extract_v4.py --exclude-ids EXCLUDE_IDS_H-OUT-C13.txt --check` (py3.11) | CHECK PASS: 3,936 judgments, 13,327 rows, batches 0 and 19 byte-identical |
| A2 `extract_v4.py ids --ids-file predictions_H-OUT-C13/IDS.txt` | `raw/OUTCOMES_V4.csv` byte-identical (only `tool_repo_head` differs in RUN_INFO). The scorer-format file does not reproduce: see A2-03 |
| A2 `FREEZE_V4.json` | All 9 tool hashes and 2 output hashes match; the author statement hash matches |
| A3 `holdings_c13.py check` (py3.11) | CHECK OK: 3 files byte-identical, tool and model hashes match |
| A3 `predict_holdout_c13.py --packet …coder_1/CODER_SHEET.csv` | sha `3894ecbf…`, identical to the frozen file and to RESULTS §2.2 |
| A5 `predict_hrel_c13.py --check`, A5 worktree | CHECK OK |
| A5 `predict_hrel_c13.py --check`, trial merge | The predictions CSV reproduces (`c53ea96a…`); the manifest differs (A5-01b) |

**Trial merge.**
- `git merge --no-ff` of `9cdd5008`, `a520aa3a` and `e15af208` in turn onto `dbe40b4f` gives no conflicts (trial head `f0d7164d`).
- `claude/c13-eval` `20a4e55d` also merges cleanly onto that result (`git merge-tree`).

## 2. Findings

### P1

**A5-01 (P1). After the merge, the A5 `--check` tools fail, so `test_tools_reproduce` fails and staging CI goes red.**
- Evidence:
  - **(a) Missing dependency.** `tests/test_legal_audit_c13_graph_treatment.py::Build.test_tools_reproduce` runs `scnum_reconfirm_c13.py --check` first. That tool does `import fitz` (line 200). The legal-audit CI job (`legal-audit-kit-ci.yml`) runs Python 3.11 with no pip install, so the test fails with `ModuleNotFoundError: fitz`. Reproduced with `/usr/bin/python3.11`.
  - **(b) Provenance change.** With PyMuPDF present (venv 3.13), the test still fails after the merge: `SCNUM_SUMMARY_C13.json differs`.
    - Cause: staging now has `config/restricted_material.json` in the worktree, so `common_c13.load_restricted()` records `"source": "worktree:config/restricted_material.json"` instead of `"git:72fe7a75:config/restricted_material.json"`.
    - The register bytes are identical (`fc7ea07e…` both ways).
    - Run individually on the trial merge, 4 tools fail `--check`: `scnum_reconfirm_c13` (1 file), `identity_c13` (1), `graph_c13` (2: `GRAPH_SUMMARY_C13.json`, `IC01_EXPORT_MANIFEST.json`) and `contract_v1_export_c13` (1). The frozen `predict_hrel_c13` also fails on `freeze/H-REL-C13_PREDICTIONS_MANIFEST.json`.
    - I regenerated the outputs in the throwaway tree and diffed them. Only the `source` strings and the manifest hashes and byte counts derived from them change. No data row changes. The frozen predictions CSV still reproduces.
  - The test stops at the first failing tool, so a CI log shows only scnum.
  - These lines predate the freeze delta, but they surface only on integration.
- Required fix. Frozen hashes must not change: `common_c13.py` `ec7fe04a…`, `predict_hrel_c13.py` `eb2bbd96…`, predictions `c53ea96a…`.
  1. Make the test skip the PyMuPDF-dependent tool when `fitz` is not importable, as A4 did for pymupdf and jsonschema.
  2. Resolve the provenance dependence without editing frozen tools. Two options:
     - an integration-time override in a non-frozen layer, for example in the test, or an env/flag read only by non-frozen tools, that pins the register source to `git:72fe7a75:…` when the worktree bytes equal `fc7ea07e…`;
     - or regenerate the non-frozen summaries and manifests on the integration branch with the new provenance, and record the frozen predictions-manifest difference in a post-freeze defect note, without regenerating the frozen file.
  3. Re-run the full suite under bare Python 3.11 before merging.

**A5-02 (P1). `test_legal_audit_c13_graph_contract_v1::test_track_b_validator_accepts_every_record` errors when jsonschema is absent, which is the state of the legal-audit CI.**
- Evidence:
  - The test runs `python -m mimamsa_contract … record candidate` from a `git archive` of `app/contract` at `5f4b8071`.
  - Without jsonschema the validator prints nothing to stdout, and `json.loads(r.stdout)` raises `JSONDecodeError` (trial run with `/usr/bin/python3.11`, 1 error).
  - It passes in the venv (4 of 4).
  - The legal-audit CI installs nothing; only `app-ci.yml` installs `app/contract/requirements.txt`.
- Required fix:
  - `skipTest` when `jsonschema` (or `mimamsa_contract`'s imports) is unavailable, or when the subprocess returns non-zero with empty stdout. Report stderr in the failure message.
  - Alternatively, move this test to a job that installs `app/contract/requirements.txt`.

### P2

**A2-01 (P2). A2 README status is stale and does not report the blind result.**
- Evidence (`C13-A2-OUTCOME/README.md`):
  - l.3: "**Status: FREEZE CANDIDATE, NOT FROZEN.**" The branch is frozen (`FREEZE_V4.json`, commit `9cdd5008`).
  - l.21: `freeze_v4.py` "**Not run.**" It has been run.
  - l.4–6: the capability stays restricted "until an independent evaluation on the fresh holdout H-OUT-C13 meets strict precision ≥95% and coverage ≥85%". That evaluation has now been run, and the result is **NOT_MET on all four targets** (RESULTS §1.2, §9).
  - The README cites no GA4 figure anywhere.
- Required fix:
  - Change the status to FROZEN `c13-extract-v4/1.0.0`.
  - Add a "Blind evaluation (GA4)" section at the top, citing `claude/c13-eval` `20a4e55d` `RESULTS_C13.md`. It should give these figures as weighted [CP95] and unweighted:

    | Field | Strict precision | Coverage |
    | --- | --- | --- |
    | printed_disposal | 0.898 [0.838, 0.941], unweighted 0.825 | 0.833 [0.743, 0.902], unweighted 0.623 |
    | substantive_result | 0.882, unweighted 0.831 | 0.760, unweighted 0.577 |

  - It should also say:
    - SC printed_disposal: precision 0.576, coverage 0.391;
    - party-specific: not demonstrated;
    - status NOT_MET;
    - the capability remains NON_OPERATIONAL_RESEARCH_ONLY.

**A2-02 (P2). The in-sample figures need a GA4 pointer, and some statements overstate or contradict the blind results.** These are the statements, set against RESULTS_C13.md:

| # | Statement (README unless noted) | Blind result | Assessment |
| --- | --- | --- | --- |
| a | l.53 table row "C12 V3 holdout … printed 165/169 = 97.6% \| 169/213 = 79.3%" (the "97.6% at 79.3%" claim), plus substantive 98.6%/68.1% | printed SP 0.898 w / 0.825 unw; coverage 0.833 w / 0.623 unw | Labelled IN-SAMPLE (section heading and `DEV_EVALUATION_V4.md`), so it is not presented as expected performance. But it is the only performance table and appears with no blind comparison. **It must be flagged as superseded by GA4** |
| b | l.57–58 "All spent sets … 98.9% / 84.6%", "99.4% / 78.0%"; `DEV_EVALUATION_V4.md` DEVG rows "100.0%" | as above | Overstates relative to blind: precision is about 9–10 points lower. Must carry the same flag |
| c | l.62 "**Expect blind coverage well below 85%**, and blind precision below the in-sample figures" | coverage 0.833 w / 0.623 unw; precision 0.898 | Consistent in direction (not an overstatement). Replace it with the measured figures |
| d | l.40 "Party-specific outcomes … gives `partly_allowed` with the per-party outcomes in `party_specific`" | "No gold unit carries party_specific … requirement stays **not demonstrated**" (§4.1, §9) | Capability described, not demonstrated. Add "not demonstrated on H-OUT-C13 (0 gold units)" |
| e | l.47 / `DEV_EVALUATION_V4.md` confidence tiers "not calibrated" | — | Accurate; keep |
| f | `DEV_EVALUATION_V4.md` l.3–4 "The formal evaluation … is run by an independent evaluator" | It has been run: NOT_MET | Add the GA4 pointer |

- Required fix: add a one-line banner to `README.md` and to `dev_eval/DEV_EVALUATION_V4.md`: "In-sample development evidence only; superseded by GA4 blind results (RESULTS_C13.md §1.2): NOT_MET." Amend rows c, d and f as noted. This is a documentation addendum only; the frozen tools and outputs are unchanged.

**A2-03 (P2). The frozen scorer-format prediction file cannot be reproduced from committed code.**
- Evidence:
  - `predictions_H-OUT-C13/PREDICTIONS_OUTCOME_V4_H-OUT-C13.csv` (sha `45c5a332…`, the file GA4 scored) maps the following into the `c13_score.py` columns (`item_id`, `pred_id V4Pnnnnn`, …):
    - `raw/OUTCOMES_V4.csv`: 475 rows, which **do** reproduce byte-identically with `extract_v4.py ids`;
    - `ITEM_POINTERS.csv`;
    - 5 `NO_JUDGMENT_ID_FOR_ITEM_SHA` abstention rows.
  - No committed tool performs that mapping. `grep -r PREDICTIONS_OUTCOME_V4\|ITEM_POINTERS` over the tree finds only `PREDICTIONS_INFO.json`, and the freeze commit adds data files only.
  - `FREEZE_V4.json` also omits the predictions sha.
- Required fix:
  - Commit the converter, for example `tools/predict_holdout_v4.py`, with a `--check` that regenerates `45c5a332…` from `ITEM_POINTERS.csv` plus `raw/`.
  - Record it as a post-freeze addition that does not affect extraction, in `POST_FREEZE_DEFECTS.md` or a freeze addendum, with its sha.
  - The extractor tool hashes are unaffected.

**A3-01 (P2). The A3 README headline estimates are not reconciled with the GA4 descriptive results, and H-HOLD's non-scorable status is not stated.**
- Evidence (`C13-A3-HOLDINGS/README.md`):
  - l.10 "Holding precision … **about 50% (20/40, Wilson 35-65%)**", and l.15 "The best honest estimates are about 50% precision and 50-60% recall". GA4 descriptive adjudicated precision is **0.365 [0.241, 0.503]** (36/99). The second adjudicator's labels point to about 0.34 (§1.3, §4.2). The README's point estimate lies above the whole blind interval except its upper edge. Relative to the blind evidence this overstates precision, although GA4 calls it broadly "consistent".
  - l.15 "The independent evaluation on H-HOLD-C13 is the only valid test", and l.157 "C11 F06 … F07 … Closure needs the independent fresh-set measurement". H-HOLD is **NOT SCORABLE UNDER PROTOCOL v1.1**: span F1 is 0.566 (below 0.6), and there is PD-01. A3 has **no protocol verdict in C13**, and the F06/F07 closure stays open.
  - l.153 "Precision is the main shortfall, at about 50% estimated."
  - l.13 and l.107: the opinion misattribution of 6.4% is in-sample and comes from developer gold. It is correctly caveated in `opinion_check/`, but it is bold in the headline with no GA4 note. GA4 did not measure it.
  - `FREEZE.json` `targets_and_estimates` (immutable) repeats "about 50% precision". That is acceptable as a frozen record, but the README must supersede it.
  - The figures do not claim that targets were met: "not expected to be met" is stated. This is correct.
- Required fix: a README addendum at the top, citing RESULTS_C13.md §1.3, §4.2 and §9, that states:
  - H-HOLD is not scorable and A3 has no protocol verdict;
  - descriptive precision is 0.365 [0.241, 0.503] and recall 0.517 [0.424, 0.608], descriptive only under a deviation;
  - the most common false positives are fact-findings, quoted precedent, operative lines and narrative;
  - re-annotation under an independent guideline is required (D-12).

  The 50% estimate should be relabelled "pre-freeze developer estimate, superseded".

**A3-02 (P2). A3 development artifacts used judgments from the H-OUT and H-REL holdouts, and this exposure is undisclosed.**
- Evidence:
  - The ID attribution used `FRAME_RECORDS.csv` to expand `judgment_key` to `judgment_id`, sha256 and doc_id.
  - `selfcheck/SELFCHECK_SAMPLE.csv` is the developer's hand-check of 40 holdings. The developer read the excerpts in context and labelled them, and the vetoes were written from its errors (README l.89–101). **15 of its 40 rows come from 15 distinct holdout judgments**:
    - 9 in H-OUT: J-1def331cba2f5c4d, J-28f88d53cdcab798, J-6572f8e4e42b1acb, J-7a28577d8eb000c3, J-7f5e29192eb0b3a7, J-bf599845016b9ee4, J-ce74488cee822fa3, J-db759e27809627fc, J-fc44a11760634183;
    - 10 in H-REL: J-28f88d53cdcab798, J-38dce4e6ce951903, J-47dffe7ecd2f8159, J-4e51f01632d9595d, J-6572f8e4e42b1acb, J-7f5e29192eb0b3a7, J-84225cbed11f6dec, J-bf599845016b9ee4, J-cebc765ebc72096d, J-fd6798fbb10965c6;
    - 4 judgments are in both.
    - Two rows are on a page adjacent to the coded H-REL page: J-28f88d53 at p.20 against coded p.19, and J-47dffe7e at p.21 against coded p.22.
  - `gold/OPINION_GOLD_C13.csv` (developer-built from the text, with evidence per row) includes **J-28f88d53cdcab798**. That judgment is in H-OUT, and in H-REL with coded pages 8 and 19.
  - The README describes the sample as "unseen judgments" drawn from judgments "not used in training and not in the fresh set". That is true only for H-HOLD.
  - None of this is in `EXPOSURE_REGISTER.md`, `PRE_EXPOSED_SUBSET.csv` (only J-38dce4e6 is there, as CASE_NUMBER_REVIEWED), the A3 freeze statement or GA4 D-3.
- Impact:
  - The A3 author is a different agent instance from the A2 and A5 authors, and the A3 branch was unpushed. So no contamination of the A2 or A5 predictions follows.
  - It is still holdout-text exposure before scoring, and protocol §4.4 requires exposure to be registered.
  - A3's own holdout (H-HOLD) is not touched: 0 H-HOLD ids appear in any A3 dev or training artifact.
- Required fix:
  - Add an exposure entry (A3 author dev read, H-OUT/H-REL) to the A0 exposure register for future cycles.
  - Add a GA4 addendum with a descriptive sensitivity excluding these 15 judgments from the H-OUT and H-REL results, or a statement that it is immaterial, backed by a run.
  - Correct the A3 README wording ("unseen" means outside training and outside H-HOLD only).

**A5-03 (P2). A5 README not updated at freeze; no GA4 pointer.**
- Evidence (`C13-A5-GRAPH/README.md`, unchanged in the freeze delta):
  - l.3 and l.306 "The treatment extractor is **not frozen**". It is frozen (`freeze/FREEZE_RECORD_C13_A5.md`).
  - l.253 "Independent precision and recall per type need A0's H-REL-C13 evaluation".
  - l.248 in-sample "typed-treatment agreement 54/55 (98.2%); recall on supported rows 54/66 (81.8%)". The blind relation_type precision is **0.340 [0.161, 0.560]** (58/176). `follows` recall is **0.032** (5/154), and 0/53 `distinguishes` were identified. Target precision is 0.620, and weighted coverage 0.26 (§1.4, §9).
  - The in-sample row is correctly labelled "not measured performance, none may be displayed". It is not a target claim, but it must now be juxtaposed with GA4.
- Required fix:
  - Change the status to frozen `treatment-c13/0.9.0-dev` (GA3, `e15af208`).
  - Add a GA4 section with the figures above and the note "descriptive, no target".
  - Mark the 98.2%/81.8% figures as in-sample, superseded.
  - State that FOLLOWS/OVERRULES contract edges stay unverified candidates. GA4 shows treatment is rarely captured.

**X-01 (P2, cross-branch; decision before merging A3). H-HOLD may be reused, but the integration would publish H-HOLD text in staging.**
- Evidence:
  - RESULTS D-12 requires "re-annotation of H-HOLD by two fresh coders … before the next A3 freeze". That implies the same H-HOLD items may score the next A3 version, so H-HOLD is not clearly spent.
  - Integration would place H-HOLD judgment text in staging:
    - A3 `frozen_predictions/PRED_H-HOLD-C13.csv`: 837 rows with excerpts, and 2,051 fingerprint hits against the A0 holdout fingerprint;
    - A2 `outputs/OUTCOMES_V4.csv` and the batches: answered rows with excerpts for 110 H-HOLD judgment ids (A2 excluded only H-OUT);
    - A5 `treatment/TREATMENT_PASSAGES_C13.csv.gz` (94 H-HOLD judgments), `graph/edges_candidate.jsonl.gz` (110) and `contract_v1/` (104).
  - Combined with GA4 `ROWS.csv` on the eval branch, the A3 frozen predictions would show a future A3 developer exactly which H-HOLD items it got wrong.
  - H-OUT and H-REL are spent, so their text in the corpus-wide outputs is acceptable, as instructed.
- Required fix: an owner or coordinator decision recorded before A3 merges. Either:
  - **(a)** declare H-HOLD-C13 spent and draw a fresh holdings holdout for the next A3 freeze; or
  - **(b)** keep `PRED_H-HOLD-C13.csv` and the GA4 H-HOLD row-level files out of staging (evaluator store only), register H-HOLD in the A0 exposure register as "A3-predictions exposed", and require the next A3 author to state non-access.

  The A2 and A5 corpus outputs are generic corpus text, already readable from `c7` data/text. With (a) they need nothing; with (b) the next A3 author's exclusion list must cover them.

### P3

**A2-04 (P3).**
- Evidence: README l.22 gives the test command as `python -m pytest tests/test_legal_audit_c13_outcome_v4.py`. CI uses unittest, and the file is pure unittest (22 pass).
- Required fix: give `python -B -m unittest tests.test_legal_audit_c13_outcome_v4`.

**A2-05 (P3). Freeze-record clarity.**
- Evidence:
  - `FREEZE_V4.json` `exclusion_list_sha256` is `d1169093…`. That is `exclusion_key()`, the sha of the sorted ids joined by newline, not the file sha (`87227665…`). I verified it equals the key of the 331 ids.
  - The record also lacks the predictions sha and the holdout-ancestry check. A3 and A5 record both. GA4 independently verified the ancestry.
- Required fix: note these in a freeze addendum. Do not edit `FREEZE_V4.json`.

**A2-06 (P3). Restricted-material guard is hardcoded.**
- Evidence: A2 (`extract_v4.py`) and A3 (`c13_corpus.py`) hardcode the RM-001 sha rather than reading `config/restricted_material.json`, the GOV register now in staging. A5 reads the register.
- Required fix: recommend switching to the register in the next version, not in the frozen tools. No current leak.

**A3-04 (P3, informational; verified, no action).**
- Evidence:
  - `model/OOF_PREDICTIONS_TEXTS.jsonl.gz` has 758 fingerprint hits, `dev_eval/pred_*` 11–28 and `opinion_check/pred_opinion_gold` 30.
  - By ID, the 137 training judgments in `OOF_PREDICTIONS.jsonl.gz` include no holdout judgment. The holdout ids in `TRAINING_REPORT.json`, `c13_holdings_model.json` and `RUN_META.json` come only from the embedded exclusion list, and include the 34 H-OUT and 23 H-REL keys shared with H-HOLD.
  - The hits are therefore shared quoted text: precedents quoted in both a training judgment and a holdout judgment.
  - The A2 dev artifacts (`DEV_EVALUATION_V4_ROWS.csv`, 4 hits, below MIN_HITS) contain no holdout ids. A2 dev overlap with any holdout is 0.
- Required fix: none.

**X-02 (P3). The integration also brings in A0.**
- Evidence: each branch brings `C13-A0-EVAL/` at `f1d61f71` (GA0-accepted) and the 6 A0 tests. They are identical across the three branches, so there is no conflict. They sit outside the extractors' own folders, but they are the required registration ancestry.
- Required fix: name A0 `f1d61f71` explicitly in the integration merge message and PR, so that staging's history shows when the holdout registration (SAMPLE, ITEM_MAP, packets) entered.

**X-03 (P3, pre-existing; not caused by these branches).**
- Evidence: on staging `dbe40b4f` under bare Python 3.11, `test_legal_audit_c13_forms_a6.Reproducible.test_build_check` fails with `ModuleNotFoundError: pymupdf`, so staging's legal-audit CI is already red on this test.
- Required fix: none for A2, A3 or A5. The coordinator should open a separate fix (skip when pymupdf is absent) so that the A5 fixes can be verified against a green baseline.

**X-04 (P3).**
- Evidence: RESULTS_C13.md is on `claude/c13-eval` and not yet in staging.
- Required fix: until the eval branch merges, README addenda should cite it by branch, commit (`20a4e55d`) and path, then switch to the staging path.

## 3. Verdicts

| Branch | Verdict | Conditions before merge |
| --- | --- | --- |
| **A2 Outcome V4** (`9cdd5008`) | **ACCEPT WITH CONDITIONS** (0 P1, 3 P2) | A2-01 and A2-02 (README/dev-eval addendum with the GA4 NOT_MET figures and a "superseded" banner on the 97.6%/79.3% table); A2-03 (commit the prediction converter with `--check`). Merge mechanics, tests, protection, RM-001 and leakage are clean |
| **A3 Holdings** (`a520aa3a`) | **ACCEPT WITH CONDITIONS; hold pending X-01** (0 P1, 2 P2 + X-01) | A3-01 (README addendum: H-HOLD not scorable, descriptive precision 0.365); A3-02 (register the H-OUT/H-REL dev exposure, correct "unseen"); X-01 owner decision on H-HOLD reuse before `PRED_H-HOLD-C13.csv` enters staging. Tests, `check` and prediction reproduction are clean |
| **A5 Treatment graph** (`e15af208`) | **NOT READY: fix P1s, then ACCEPT WITH CONDITIONS** (2 P1, 1 P2) | A5-01 (fitz skip; restricted-register provenance after merge, with frozen hashes preserved); A5-02 (contract-v1 test skip without jsonschema); A5-03 (README frozen status and GA4 figures). The freeze delta's content (freeze record, predictions, manifest, predict tool) is otherwise sound, and the predictions reproduce |

**Counts:** P1 2 (A5-01, A5-02). P2 7 (A2-01, A2-02, A2-03, A3-01, A3-02, A5-03, X-01). P3 7 (A2-04, A2-05, A2-06, A3-04, X-02, X-03, X-04).

---

## 4. Confirmation review of the post-freeze fixes (2026-11-25)

- **New heads:** A2 `2a6c710e`, A3 `010aac1c`, A5 `a60f1079`.
- **Fresh scratch merge:** `tmp-review/trial2`, a detached worktree of staging `dbe40b4f` with the three heads merged `--no-ff`. Head `5330c91f`. No conflicts.
- No branch was modified. All mutations below were made in the throwaway tree and reverted with `git checkout`.
- **Eval branch:** `claude/c13-eval` is now at `6ea94ec9`. It adds the D-HHOLD decision and the A3 exposure log line.

### 4.1 Frozen artefacts byte-unchanged since each freeze commit

`git diff <freeze> HEAD` on the trial merge is **empty** for each path set below.

| Branch | Paths checked |
| --- | --- |
| A2 | `tools/extract_v4.py`, `tools/v4*.py`, `outputs/` (CSV, RUN_INFO, FREEZE_V4.json, batches), `predictions_H-OUT-C13/`, `EXCLUDE_IDS_H-OUT-C13.txt` |
| A3 | `tools/`, `model/`, `frozen_predictions/`, `outputs/`, `exclusions/EXCLUDE_H_HOLD_C13.txt` |
| A5 | `tools/treatment_c13.py`, `tools/common_c13.py`, `tools/predict_hrel_c13.py`, `C11-JUDICIAL-QUALITY/relations/`, `freeze/H-REL-C13_PREDICTIONS.csv`, `freeze/…_MANIFEST.json`, `freeze/FREEZE_C13_A5.json`, `treatment/`, `graph/`, `contract_v1/`, `scnum/`, `identity/` |

What each post-freeze delta changes:
- **A2:** adds `FREEZE_ADDENDUM_V4.md` and `tools/predict_holdout_v4.py`; edits `README.md`, `dev_eval/DEV_EVALUATION_V4.md` and `POST_FREEZE_DEFECTS.md`.
- **A3:** adds `FREEZE_ADDENDUM.md` and `exclusions/DEV_EXPOSURE_HOUT_HREL.csv`; edits `README.md`.
- **A5:** edits only the non-frozen tools `scnum`, `identity`, `graph` and `contract_v1_export`, each by importing the pin. It adds `provenance_pin_c13.py`, `run_check_c13.py` and a freeze addendum, and edits the README, `SHA256SUMS` and 2 tests.

The new test `test_frozen_tool_hashes_unchanged` asserts the frozen hashes and the predictions sha.

Other checks:
- Protected hashes are unchanged (`9a8f0d19`, `8b8d53cd`, `cfe5f408`), and the AUTH-LEDGER tree is `eed99c62` (v0).
- Nothing outside `C13-{A0-EVAL,A2,A3,A5}/` and `tests/test_legal_audit_c13_*` changes.
- RM-001 appears only in guard code, tests and prose.

### 4.2 P1 closure and CHECK PARTIAL mutation tests

**Every A5 check on the trial merge**, run through `run_check_c13.py` under bare `/usr/bin/python3.11` (no PyMuPDF, no jsonschema):
- scnum: `CHECK PARTIAL (PyMuPDF absent)`, naming the two skipped steps;
- identity, treatment, graph, review_recheck, contract_v1_export, predict_hrel and package: `CHECK OK`;
- hf_overlay: OK.

The provenance pin returns the established label only when the register sha equals `fc7ea07e…`, so a changed register still fails.

**Mutation tests**, run in the throwaway tree with no PyMuPDF:

| Mutation | `scnum --check` | `package --check` (SHA256SUMS) |
| --- | --- | --- |
| M1: `overlay_value` changed in `SC_CASE_NUMBER_OVERLAY_C13.jsonl` | **FAILED** | FAILED |
| M2: `anchor_page` and `excerpt` changed in `SCNUM_RECONFIRMATION_C13.csv` | PARTIAL (passes) | **FAILED** |
| M3: `staged_numbers` changed in `SCNUM_SUMMARY_C13.json` | PARTIAL (passes) | **FAILED** |
| M4: a verdict changed to NOT_RECONFIRMED | **FAILED** | FAILED |

- M3 was also run through the unittest: `test_tools_reproduce` **fails** (subtest `tool='package_c13.py'`).
- The scnum artefact check on its own does not cover every committed field. `package_c13`'s SHA256SUMS check in the same test does, so **CHECK PARTIAL cannot mask a mismatch at test level**. See N2.

**A2 converter.** `predict_holdout_v4.py --check` reproduces `45c5a332…` (CHECK PASS). After a `printed_disposal` value was mutated in `raw/OUTCOMES_V4.csv`, it reports `CHECK FAIL`.

### 4.3 Test runs (trial2)

| Python | Result |
| --- | --- |
| Bare 3.11, CI-like | 999 tests, **1 failure: the pre-existing A6 `test_build_check` (X-03)**, 18 skipped |
| venv 3.13, with PyMuPDF and jsonschema | 999 tests, **OK** (9 skipped) |

- A2 `extract_v4.py --check` gives CHECK PASS. A3 `holdings_c13.py check` gives CHECK OK.
- A5-02: under 3.11 the contract test now skips with a stated reason. With jsonschema present it passes.

### 4.4 README claims against RESULTS_C13.md

Every figure in the new README addenda matches RESULTS_C13.md at `20a4e55d` (sha `b8d0b252…`).
- **A2.** Precision 0.898 [0.838, 0.941], 0.825 (254/308); coverage 0.833 [0.743, 0.902], 0.623 (283/454); substantive 0.882 [0.815, 0.932], 0.831 and 0.760 [0.671, 0.835], 0.577; SC 0.576 and 0.391; 101 of 129 missed units in batches; family precision 0.941/0.870; anchors 403/2/75; party-specific not demonstrated; NOT_MET. The 97.6%/79.3% and 98.9%/84.6% figures and the DEVG 100% rows are bannered SUPERSEDED.
- **A3.** H-HOLD not scorable; 0.365 [0.241, 0.503], 0.517 [0.424, 0.608], 0.156; 113 of 183 gold holdings single-adjudicator; false-positive split 26/11/9/7/5; "about 50%" and 6.4% labelled superseded; F06/F07 open.
- **A5.** 0.340 [0.161, 0.560] (58/176); target 0.620 [0.467, 0.758]; coverage 0.26 weighted and 0.50 unweighted; `follows` 0.032 (5/154); 0/53 `distinguishes`; 0.341 sensitivity; in-sample 98.2% labelled superseded; status FROZEN.

No statement claims that a target was met or that anything is legally valid.

### 4.5 Finding status

| Finding | Status | Evidence |
| --- | --- | --- |
| A5-01 (P1) | **CLOSED** | §4.2. All checks pass after the merge under 3.11; frozen hashes are preserved |
| A5-02 (P1) | **CLOSED** | §4.3 |
| A2-01 (P2) | **CLOSED** | README states FROZEN, gives the GA4 table, NOT_MET and NON_OPERATIONAL |
| A2-02 (P2) | **CLOSED** | Banners on the README and DEV_EVALUATION; party-specific "not demonstrated"; "expect" sentence replaced |
| A2-03 (P2) | **CLOSED** | Converter committed; byte-exact; detects mutation |
| A3-01 (P2) | **CLOSED** | Addendum; superseded labels |
| A3-02 (P2) | **CLOSED** for the branch | `DEV_EXPOSURE_HOUT_HREL.csv` lists the same 15 judgments I found; README wording corrected; exposure logged in the eval `ASSIGNMENT_LOG.md` at `6ea94ec9`. Residual P3 (N3) |
| A5-03 (P2) | **CLOSED** | README FROZEN plus GA4 table |
| X-01 (P2) | **CLOSED** | Coordinator decision D-HHOLD (`6ea94ec9`, ASSIGNMENT_LOG l.38): H-HOLD-C13 is SPENT, and a fresh draw is required. The owner may override; if so, X-01 reopens |
| A2-04, A2-05 (P3) | CLOSED | — |
| A2-06 (P3) | Recorded (deferred to next version) | — |
| X-02, X-03, X-04 (P3) | Open, coordinator items | X-03 still fails on staging |

### 4.6 New findings

There are no new P1 or P2 findings.

**N1 (P3). CI never runs the A5 reproduction checks.**
- Evidence: `test_tools_reproduce` skips entirely when `/home/user/c7` is absent, which is always the case in CI. So CI never runs `package_c13 --check`, the SHA256SUMS integrity check, even though it does not read c7. The scnum artefact check also runs without c7. Only `test_frozen_tool_hashes_unchanged` guards A5 in CI.
- Required fix: move `package_c13.py --check` and the scnum artefact check outside the c7 skip.

**N2 (P3). The scnum artefact check alone does not hash all of its own outputs.**
- Evidence: `artifact_check` accepts mutations to `SCNUM_RECONFIRMATION_C13.csv` excerpt and anchor columns and to `SCNUM_SUMMARY_C13.json` counts (M2, M3). They are caught only by `package_c13`.
- Required fix: have the artefact check verify the three scnum files against `SHA256SUMS` itself.

**N3 (P3). The A3 exposure is not yet in the A0 exposure register, and the sensitivity run is still missing.**
- Evidence: the exposure is in the eval log, but not in the A0 `EXPOSURE_REGISTER.md` or `PRE_EXPOSED_SUBSET.csv`, which future cycles read. No H-OUT/H-REL sensitivity run excluding the 15 judgments was made. That is acceptable, because the authors are distinct.
- Required fix: carry the entry into the A0 register next cycle.

**N4 (P3, informational). The pinned provenance label can name the git source when the file was read from the worktree.**
- Evidence: the label reads `git:72fe7a75:…` even when the file came from the worktree. The sha in the same record proves the bytes, and the addendum documents this. No action is needed.

### 4.7 Confirmation verdicts

| Branch | Verdict |
| --- | --- |
| **A2** `2a6c710e` | **ACCEPT** for integration |
| **A3** `010aac1c` | **ACCEPT** for integration. This rests on D-HHOLD standing |
| **A5** `a60f1079` | **ACCEPT** for integration. N1 and N2 are recommended follow-ups |

**Integration note:** staging's legal-audit CI still fails on the pre-existing A6 test (X-03), independently of these branches.
