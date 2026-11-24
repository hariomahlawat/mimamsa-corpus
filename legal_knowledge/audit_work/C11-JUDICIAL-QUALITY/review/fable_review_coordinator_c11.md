# Independent review of the coordinator-written C11 tools and outputs

- **Reviewer:** Fable 5.2 (claude-fable-5-2), independent technical and documentary review
- **Date:** 2026-11-24
- **Branch / head reviewed:** `claude/c11-judicial-quality` at `c0c7362f`. The branch moved to `48da982c` during the review; that commit touches only `relations/`, and every in-scope file is byte-identical at both heads.
- **Base folder:** `legal_knowledge/audit_work/C11-JUDICIAL-QUALITY/`
- **Findings:** `fable_review_coordinator_c11_findings.csv` (same folder as this report)

## Verdict

**ACCEPT WITH CHANGES. No P1. Four P2 findings must be fixed before the affected outputs are relied on.**

The preservation package and the Hugging Face statuses are sound and honestly stated. Three outputs are narrower than their descriptions say: the release filter (C-01), the excluded-log ranking (C-02) and the affected-research-record list (C-03). The printed-marking scan gives a clean per-copy status to documents it could not read (C-04).

| Severity | Count | Ids |
| --- | --- | --- |
| P1 | 0 | |
| P2 | 4 | C-01, C-02, C-03, C-04 |
| P3 | 8 | C-05 to C-12 |
| INFO | 6 | C-13 to C-18 |

## 1. Preservation (`tools/preservation_c11.py`, `preservation/`)

**Confirmed independently.**
- `--check` reproduces all four files.
- All 48 manifest lines pass `sha256sum -c` against the working store. The 48 hashes are distinct.
- I also hashed every registered alternate path: 58 paths across the 48 copies, all equal to the registered SHA-256. The tool hashes alternates but records only the first.
- Git blob ids: I recomputed all 48 with `git hash-object --no-filters`. They equal the inventory column. All 48 are `missing` from the object store, and none appears among the 17,929 blobs in the object store, reachable or not (`cat-file --batch-all-objects`).
- None of the 48 SHA-256 values appears in `data/SHA256SUMS` at `ad77758d`. No file in the `raw-data` tree and no PDF under Hugging Face `legal_knowledge/` has the same byte size as any of the 48.
- `stage_and_verify.sh`, run into a temporary directory: 48 files staged, all byte-identical to their sources (`filecmp`, not only hash), original basenames kept, 48 sidecars, manifest comparison passed. It refuses a non-empty destination and a store without `downloads/`. The working store was unchanged afterwards (path, size and mtime listing identical). The temporary directory was deleted.
- Destination analysis is accurate as far as I could test it: the connector exposes only list, stat and text read.

**Overstated or wrong.**
- **C-04 (P2).** 73 of the 892 pages have no text layer, in 17 copies. Two copies are wholly image-only: the 35-page DESW Entitlement Rules 2023 letter and the one-page Rajya Sabha extract. Both still carry `NO_MARKING_FOUND_TEXT_LAYER`. The package mentions the limit in general terms but gives no count and no per-copy flag. The register value is `NOT_OBSERVED_OR_NOT_CHECKED` for all 48, which the package reports as "none recorded". The classifier also labels any hit on "restricted" or "confidential" as ordinary use by rule; the 34 hits are in fact ordinary (I read them all), but the label was not a reading. I viewed page 1 of the DESW letter: no marking there. Pages 2 to 35 remain unread.
- **C-05 (P3).** "Any git object of the repository (all fetched branches, any commit)" is too wide. The clone is shallow, with its boundary at `ad77758d`, so earlier `raw-data` history is not present. The conclusion is still well supported by the SHA256SUMS and size checks above.
- **C-06 (P3).** Composition text is wrong: the package says "16 Army Act / Army Rules amendment Gazettes". The inventory has 24 Army Rules amendment copies, plus Acts 13 of 1975 and 19 of 1955, three copies of Act 37 of 1992, the 1954 Rules and Regulations for the Army 1987 chapter 5. The total of 31 P0 is right.
- **C-07 (P3).** The six anchor-bearing copies carry 47 anchor rows (42 + 5), while section 3 says the risk covers "all 42 anchors". The two figures need reconciling in the text.

## 2. Hugging Face verification (`tools/hf_verify_c11.py`, `hf_verification/`)

**Honest and supported.**
- `--check` reproduces. No copy is `BYTE_VERIFIED` on Hugging Face. The mapping is conservative: an upload-run log claiming remote verification is still only `DECLARED_HASH_ONLY`, and the eight MML originals are `PATH_SIZE_MATCH_ONLY`.
- Counts agree with the C10 inventory: 4,039 / 8 / 8 / 48.
- I re-read `data/SHA256SUMS` through the connector. Size is 614,935 bytes. The three captured chunks (offsets 0, 307,000 and 613,435) match the git copy at `ad77758d`, and the chunk SHA-256 prefixes in `hf_capture_c11.json` are correct. I added offsets 150,000 and 460,000: both match. This remains a sample, as the report says.
- Seven file stats (four `data/raw`, two judgment originals, one MML `.doc`) return the sizes in the status file.

No finding beyond INFO (C-15: the claim that the dataset is private could not be checked through the connector).

## 3. Excluded-log ranking (`tools/excluded_rank_c11.py`, `excluded/`)

- `--check` reproduces. All 8,077 rows say `NOT_ACQUIRED_REQUIRES_OWNER_APPROVAL`. It is clear that nothing was acquired.
- **C-02 (P2): systematic misclassification in both directions.**
  - **T1 false positives.** 645 of the 2,238 T1 rows (29%) are there only because `\bnaval\b` matched a personal name ("NAVAL KISHORE Vs SOUTH DELHI MUNICIPAL CORPORATION", "RAM NAVAL Vs DEPUTY DIRECTOR OF CONSOLIDATION"). In my random sample of 20 T1 titles, 4 were of this kind and 3 more were private disputes involving an officer by rank. Smaller leaks: "COLONEL GANJ" (a place), "SAINIK" housing societies.
  - **T5 false negatives.** At least 1,249 of the 3,477 T5 rows carry a stronger signal than those. In my random sample of 20 T5 titles, 11 were plainly military service matters. Causes: `rank_vs_union` requires `Vs`, so every Supreme Court title using "versus" misses ("COL. AVTAR SINGH SEKHON versus UNION OF INDIA", "LT. COL. KHAJOOR SINGH versus THE UNION OF INDIA"); the rank must be on the petitioner side ("UNION OF INDIA Vs EX NK VIKRAM SINGH" is T5); a service-number prefix or `EX.`/`EX-` breaks the match; "MIN.OF DEFENCE", "TH. DEFENCE" and "INTEGRATED DEFENCE STAFF" are not recognised (767 T5 titles contain "defence").
  - Effect: an owner who works the list top-down reads hundreds of irrelevant titles before reaching real leads.
- **C-09 (P3).** Coast Guard titles (51) are placed in T4 as "central armed police forces", which they are not. There is no README in `excluded/`; the method is only in the tool docstring.
- **C-16 (INFO).** Every `source_url` points to the AWS open-data mirror buckets, not a court site. The manifest should say so before anyone approves re-acquisition.

## 4. Holdout sample (`tools/holdout_sample_c11.py`, `holdout/HOLDOUT_SAMPLE.csv`)

- Deterministic: three runs on two interpreters (3.13 venv, 3.11) gave a byte-identical file.
- Excludes the development set: 50 distinct ids from the three C10 review files, zero overlap by judgment id or SHA-256, also against `REVIEW_SAMPLE.csv`.
- Strata are as the evaluation report states: SC 20, Delhi 8, P&H 10, J&K 9, Allahabad 9; disagreement 18, multi-case 16, other 22.
- **C-08 (P3).** The tool has no `--check` and silently ignores arguments; it always overwrites the CSV. The Delhi quota is 12 but the Delhi disagreement stratum is empty, so the sample is 56 rather than 60, without a stated reason. "Pension and disciplinary topics represented" is not enforced by the code.
- **Disclosure:** because of this, my attempt to run `--check` rewrote `HOLDOUT_SAMPLE.csv` in the worktree. The content is byte-identical (`git status` clean); only the modification time changed.

## 5. Holdout evaluation and release filter

- `eval_holdout_c11.py` has not changed since `b6340e20`; only 16 lines were added to `HOLDOUT_EVALUATION.md`. `--check` reproduces on both interpreters. `OUTPUT_SHA256SUMS` of the frozen extractor outputs verifies.
- `release_filter_c11.py --check` reproduces. `v2_outcome_original` equals the frozen outcome on all 3,948 rows, and every other column is unchanged.
- Exact shared text: I recomputed the groups from the batches (292 judgment ids). None of them keeps a released outcome.
- **C-01 (P2): the filter covers exact text hashes only.** The identity register (revision 2) places 414 files in multi-copy judgments. The 122 beyond the exact-hash set are normalised-text copies, scanned copies, incomplete copies and pointer orders. **76 of them, in 17 judgment keys, still carry a released outcome**, and 15 of those keys span different proceedings. Example: `JK-07de16dabda06223`, 44 copies, released "disposed_of_with_directions" on each. This is the F01 hazard on the files the filter does not see. F01's requested action was to join to the identity register's same-text groups.
- Also in C-01: the second rule fires on one row only. It requires a comma and no semicolon. 334 released rows have a semicolon-separated label naming more than one case number. The F01 disposition says rows "whose proceeding label lists several case numbers" are downgraded, which overstates what the code does. Many of those labels are spelling variants of one number, so the right fix is a normalised comparison, not a blanket downgrade.

## 6. Curated cross-check (`tools/curated_c11.py`, `curated/`)

- Protected originals: I hashed both files at `21e73b83` independently. Both equal the pinned values, and both blobs are unchanged at the branch head.
- 53-case join: all 53 ids are found in the C10 copy-status file. 25 have a C11 case-number proposal. The `proposal` values are consistent with the curated `case_number` field (35 filled, 3 of the 25 empty). Every row is `PROPOSAL_NOT_APPLIED`.
- Affected records: I read all 28 record-case pairs, not a sample of 10. Every one refers to the named case; there are no namesake hits.
- Finding texts checked against the held PDFs at `ad77758d`:
  - Parashotam: both quoted phrases are on p.17, the self-discipline reservation on p.18, and "overrul" does not occur in the text layer.
  - Girish: both phrases are on p.11, and "overrul" does not occur.
  - Delhi W.P.(C) 16771/2025: Tarsem and the three-year restriction are on p.9; "Girish" occurs nowhere in the nine pages. The dossier only says "not mentioned in this passage", so the curated wording goes further than the dossier, but it is correct.
  - J&K WP(C) 2370/2025: Shri Kant Sharma on p.2; Parashotam nowhere in the three pages.
- **C-03 (P2): the list of 25 is an undercount.** Matching is by case name in the record text. Seven more records rely on the same cases through source-reference ids without naming them: AFT-001, AFT-033 and AFT-044 (`V7-S08`, Parashotam); AFT-014, V7-SC-14 and V7-SC-16 (`V7-S11`, Tarsem); PEN-049 (`V6-S19`, the Girish clarification).
- **C-10 (P3).** Hard-coded finding text has drifted from the dossier: Ram Avtar "381 citing judgments" against the dossier's 383; "known only through Girish" omits S P Rathore; Dharamvir "para 28(ii) (p.27) construes the Entitlement Rules 1982", where the 1982 Rules reference is para 28(i) and p.27 holds the presumption. `--check` cannot detect this because the text is a constant.
- **C-11 (P3).** Two carried-over comparison labels look wrong: Prithi Pal Singh Bedi is `PARTIAL_OVERLAP` although the three numbers are the same, and Ratan Singh is `NO_CURATED_RECORD` although the curated record has the number.
- **Legal conclusions.** None is asserted; every row is a proposal for adviser review. Two action texts steer content ("should not state the 3-year arrears limit as settled without Girish"; "not apply it to the 2008 Rules without the later authority"). They would be safer as questions to the adviser (C-12, P3).

## 7. Checks and tests run

| Command | Result |
| --- | --- |
| `preservation_c11.py --repo /home/user/c7 --check` | reproduces (4 files) |
| `hf_verify_c11.py --check` | reproduces (2 files) |
| `excluded_rank_c11.py --repo ... --check` | reproduces (2 files) |
| `eval_holdout_c11.py --check` (3.13 and 3.11) | reproduces (2 files) |
| `release_filter_c11.py --check` | reproduces (2 files) |
| `curated_c11.py --repo ... --check` | reproduces (3 files) |
| `holdout_sample_c11.py` | no `--check`; rerun gives identical bytes |
| `unittest discover -s tests`, venv (Python 3.13.18) | 649 tests, OK, **0 skipped** |
| `unittest discover -s tests`, `python3.11` (3.11.18) | 655 run, **6 errors, 4 skipped** |
| `pytest` on the six pytest-style files, venv | 122 passed, 1 skipped (tesseract not installed) |
| C11 `extraction/tests` | 25 OK |
| C11 `scnum/tests` | 17 OK |
| C11 `identity/tests` | 16 OK, 1 skipped (the no-PyMuPDF path, by design) |
| C11 `relations/tests` | 38 run, 2 failures: **not attributable to a commit** (see below) |

- **python3.11 errors and skips are environmental.** The system interpreter lacks `httpx`, `pytest`, `pymupdf` and `jsonschema`. The six errors are import failures of `test_aft`, `test_crawler_foundation`, `test_indiacode`, `test_opendata`, `test_pipeline`, `test_schemas`. The four skips are three PyMuPDF tests in `test_audit_judgments` and one jsonschema test in `test_build_reconciliation`.
- **`unittest discover` does not run the pytest-style crawler and pipeline tests at all** (0 tests collected from those six modules on the venv). They pass under pytest (C-14).
- **No unit tests exist for the seven coordinator tools.** `C11-JUDICIAL-QUALITY/tests/` is an empty, untracked directory (recorded under C-08).
- **Relations.** While I worked, another actor edited `relations/tools/relations_c11.py`, regenerated five relations outputs and committed `48da982c`; further uncommitted edits were present when I ran the relations tests. The two failures reflect that in-flight state. Relations is outside this review's scope and I did not investigate them.

## Housekeeping

- No commit, push, upload or deletion in the worktree, the repository or the working store.
- Temporary material was under `scratchpad/rev_coord/`. The staging test directory, an exported tree and three page renders were deleted. Small text files remain there (hash lists, test logs).
