# Independent review: C13 A1, OCR recovery and false-negative audit

- Branch `claude/c13-a1-ocr`, head `39211848`; 9 A1 commits on top of staging `a4c0c382`.
- Output under review: `legal_knowledge/audit_work/C13-A1-OCR/`, `pipeline/text_quality.py`, `pipeline/relevance_states.py` and the two new tests.
- Reviewer: independent; did not write this work. Date: 2026-11-25.
- What I did not do: modify the branch, write to HF, or download anything from the web. All HF access was read-only through `HfApi()`.

## What I checked and confirmed

| Check | Result |
| --- | --- |
| `tools/c13_a1_ocr.py --check` | **CHECK PASS** (all 14 artefacts rebuilt or verified; restricted items absent). The worktree stayed clean afterwards. |
| `pytest tests/test_legal_audit_c13_ocr_*.py tests/test_legal_audit_c12_research_isolation.py` | 34 passed |
| Protected or frozen records | `git diff --diff-filter=MDR a4c0c382..HEAD` is empty: the branch only adds files. Nothing under `data/`, `config/`, `schema/`, AUTH-LEDGER or the C12 records was touched, and `pipeline/judgments.py` is unchanged. Commit trailers are correct, and there is no model id anywhere else. |
| HF commit `23acf21b8ebc…`: parent | Parent is `9e3cf9868a5d…` (C13 A7). It was the immediate predecessor and is still the current head. Correct. |
| HF commit: additive | Recursive tree diff, parent → new: 16,171 → 16,198 files. **27 added, 0 removed, 0 changed** (blob ids compared; nothing changed, not even `.gitattributes`). The added set equals `HF_STAGED_MANIFEST.csv` exactly. |
| HF commit: bytes | Re-downloaded all 27 at the pinned revision: **27/27 match** the manifest on sha256 and size. |
| HF commit: restricted material | No occurrence of `4284820e…` or `regs-regulations-for-the-air-force-reprinted-edition-2000` in any of the 27 files. The overlays keep `status_note` and `field_provenance` and are labelled AUTOMATED_CANDIDATE_NOT_VERIFIED. |
| OCR benchmark figures | I recomputed character accuracy over the 5 English pages with my own Levenshtein: PP-OCRv5 mobile **0.977**, RapidOCR **0.900**, text layer **0.110**. These reproduce the author's figures exactly. |
| Ground truth vs page images | I rendered GT03 (Delhi LA.APP p2) and GT04 (P&H CRM-M-23446-2025 p1) and read them against the transcriptions. Both are faithful to the printed text. |
| ~3,770 estimate | Reproduced at **3,764**, from `data/excluded_judgments.jsonl` at HF `3864faf3` (sha `46c7bd73…`): P&H by URL year band (4,251 / 14,971 / 25,339) × the kept-corpus CMap rates. |
| 24 in-corpus IRRELEVANT | I read the OCR and text-layer text of all 24 for military vocabulary (army, military, defence, armed, tribunal, cantonment, ex-servicemen and similar): zero hits. 21 are copies of one Delhi land-acquisition common judgment (Village Mundka, 8 July 2011). 3 are short P&H orders (a protection petition, a CrPC s.311 revision, an RSA delay condonation). On content, I found none that is relevant and wrongly marked. See A1-03 and A1-08 for the method concerns. |

## Findings

### A1-01 P1: 46 titles in the "re-acquire" population are already held on HF, at A1's own parent commit

**Evidence**
- I compared the 8,052 `REACQUIRE_FROM_SOURCE_URL_PENDING_OWNER_APPROVAL_FOR_DOWNLOAD_RUN` rows of `RECOVERY_POPULATION.csv` with the HF tree at `9e3cf986`, which is the parent A1 itself pinned.
- **46 are byte-held** under `legal_knowledge/preservation/c13_a7_acquired/`:
  - 29 verified by LFS sha256;
  - 17 non-LFS files, which I re-downloaded and hashed: 17/17 match.
- By tier, court and tranche:
  - **16 P&H T1 (tranche P0)**;
  - 12 Delhi T1;
  - 12 SC T1;
  - 4 J&K T1;
  - 2 Allahabad T1.
- `inputs/EXCLUDED_LOG_SUMMARY.json` gives `held_anywhere_by_sha256: 25`, computed against `3864faf3`, before A7's commit at 10:31 that day. A1 uploaded at 14:49 on top of A7's commit, but never refreshed the check.

**Claims that are false at head**
- "25 held; 8,052 need re-acquisition".
- "No excluded file other than those 25 is held anywhere (checked by SHA-256 against HF…)".
- "Nothing else could be ingested without a download run" / "0 new ingestions".
- "550 P&H T1 to re-acquire": 16 of these could have been OCR'd and given a state now, without approval for a download run.

**Required fix**
- Re-run the held check against the current HF head and make `--check` verify it against a pinned revision.
- Update `RECOVERY_POPULATION.csv`, `POPULATION_SUMMARY.json`, `README.md`, `MISSED_JUDGMENT_RISK.md` and `INGESTION_DECISIONS.csv`.
- OCR the held P&H files (and any other held file with an unusable text layer), give them states, and add them to the measured FN figures.

### A1-02 P1: the state machine returns IRRELEVANT (`may_remove()` True) for a document with unread pages that were never OCR'd

**Evidence**
- In `pipeline/relevance_states.py::decide`, `text_ok = verdict == "TEXT_OK" or usable_share >= 0.8`.
- So a document whose own verdict is `OCR_REQUIRED` passes as long as at least 80% of its content pages are usable, even with `ocr_done=False`.
- Reproduced:
  - Input: a 5-page civil text with page 1 `image_only`. `document_summary` returns `verdict=OCR_REQUIRED, usable_share=0.8`.
  - Result: `decide(..., ocr_done=False)` returns **IRRELEVANT**, and `may_remove()` is True.

**Why this matters**
- The cover page holds the parties ("… Vs Armed Forces Tribunal"). It is exactly the page most likely to be a scan, and it would never be read.
- This reproduces the "partly scanned file judged on its text pages alone" failure mode that the author identifies in `MISSED_JUDGMENT_RISK.md` §3.
- It contradicts the module docstring and the owner's directive ("never IRRELEVANT because its text could not be extracted").
- The tests only cover `usable_share=0.5` (`test_partial_usable_text_not_irrelevant`), not the 0.8 boundary.
- No current IRRELEVANT row hits this path: every IRRELEVANT row is either TEXT_OK or had OCR run. The defect is latent, but it sits in the module proposed to replace the deletion branch.

**Required fix**
- If any content page is unusable and has not been OCR'd, return `OCR_REQUIRED`, whatever the share.
- After OCR, allow IRRELEVANT only when the pages still unusable are a stated small exception: for example not page 1, and listed in `reasons`.
- Add boundary tests: share 0.8 and 0.99 without OCR, and an unusable page 1.

### A1-03 P2: IRRELEVANT verdicts rest on RapidOCR text below the engine's own measured quality bar, with exact keyword matching

**Evidence**
- The in-corpus tranche (406 of 483 pages) was OCR'd with RapidOCR, not with the engine the author chose (PP-OCRv5 mobile).
- GT03 is page 2 of `hc-delhi-2011-la-app-74-2010…`, one of the 24 IRRELEVANT documents. On that very page RapidOCR scores **word accuracy 0.405** (char 0.806). PP-OCRv5 scores 0.793 and 0.939.
- `DICT_RATIO = 0.15` lets pages through as "usable" at a dictionary ratio of 0.153: 18 of the 429 usable OCR pages are below 0.30.
- Keyword and context matching is exact-string, so "Arny Act" or "Armcd Forces" would be missed.
- A sample of the text shows the quality: crwp-6842 reads "StalcurPunjuh andahcrs", "CORAW: HONILLJUSIICLRAJLSHBHAHUAJ".
- My content read (above) finds these verdicts correct. That is by luck of the population, not by method.

**Required fix**
- Before IRRELEVANT is used as a removal candidate, re-OCR the pages with the chosen engine, or require a minimum OCR quality (dictionary ratio of about 0.35) on the pages the decision relies on. Otherwise return INSUFFICIENT_TEXT.
- Consider tolerant matching (edit distance 1) for keywords and context families on OCR text.
- Mark the 24 as "provisional (RapidOCR)" in `RELEVANCE_RERUN.csv`.

### A1-04 P2: the second check cannot see bare "Army", so a judgment that says "army" 33 times is IRRELEVANT

**Evidence**
- In `sc-1983-col-d-d-joshi…` (relevant per C12) the text layer contains **"army" ×33 and "commissioned" ×34**, yet the state is IRRELEVANT.
- `sc-1971-union-of-india-1970insc156` (army ×2, defence, military) is also IRRELEVANT.
- Synthetic check: a civil text plus "Army officers commissioned in the Army" ×15 comes out **IRRELEVANT**.
- The lexicon has no family for a bare service name, "Col.", "commissioned officer" or "Army Instruction".
- The author discloses D.D. Joshi but leaves the gap open as "not loosened to fit".

**Required fix**
- Add a blocking guard, not a positive signal: any bare mention of Army, Navy, Air Force, military or defence-service terms at or above a small count moves the case to CLASSIFICATION_UNCERTAIN, never to IRRELEVANT.
- This is a safety floor for the removal path, not tuning to the evaluation set.
- Re-run and report the change in the queue size.

### A1-05 P2: detector validation. The 9 corrections are pages missing from truncated files, not "no content"; the blank verdict is untested on intact files; both recall figures should lead

**Evidence**
- I re-rendered all 9 corrected pages (L010, L016, L019, L026, L070, L102, L119, L127, L130) with PyMuPDF: dark share 0.0, no text, no images.
- The 6 source files are 32,768 / 32,768 / 35,866 / 237,544 / 262,144 / 270,304 bytes. Several are exact powers of two, which points to truncated downloads.
- Poppler cannot read them ("Couldn't find trailer dictionary / xref table").
- MuPDF reports "non-page object in page tree".
- Every page after the truncation point is a phantom page. For example, `38bd54ea` has 76 content pages and then 95 phantom pages.
- So the relabel away from "needs OCR" is justified, because nothing exists to OCR. But NO_CONTENT is wrong: the source pages had content, and the bytes are missing.

**Wider problems**
- All 12 pages in the `blank` stratum are phantom pages from 7 truncated files. The detector's `blank` verdict was never validated on an intact PDF.
- `document_summary` drops phantom pages from the denominator. `f841d3fb` (32 pages, 5 readable, 27 missing) is summarised as **TEXT_OK, usable_share 1.0**. Only the separate `%%EOF` check protects the decision.
- Corrections were applied only where the label disagreed with the detector (FN → TN). The 13 FPs were not re-examined in the same way, so the correction is asymmetric.
- Both recall figures are disclosed, but 1.000 is the headline everywhere.

**Required fix**
- Add a `missing_page` flag for pages past a damaged page tree or in a truncated file, and do not count such pages as blank in `usable_share`. A truncated file should never be summarised as TEXT_OK.
- Relabel the 9 pages as MISSING_SOURCE_PAGE.
- Headline both figures: "recall 0.890 (0.804–0.941) on the original labels; 1.000 after relabelling 9 pages from truncated files".
- Re-examine the FPs symmetrically.
- Run the already-recommended independent relabel on a fresh sample, including blank pages from intact files.

### A1-06 P2: the ~3,770 estimate is presented as a floor without its uncertainty, and its inputs are not committed

**Evidence**
- I reproduce the point estimate: 3,764.
- About 1,700 of it comes from applying 12/30 (Wilson 95% CI **0.246–0.577**) to 4,251 files from 2014–15.
- Carrying the CIs of all three bands through gives roughly **2,650–5,230**, so "≥ about 3,770" is not a floor.
- The floor argument assumes the CMap defect is independent of case type. The 12/12 garbled AFT writs suggest it is not.
- The per-band counts of excluded files are not in `RISK_FIGURES.json` or `inputs/`, so `--check` cannot reproduce the figure.
- The label "ESTIMATED" is used correctly, and the measured/estimated separation is otherwise good.

**Required fix**
- State the figure as "≈ 3,760 (rough 95% range 2,650–5,200, assumption-dependent)" and drop "≥".
- Commit the band counts and the computation to `RISK_FIGURES.json` under `estimated`.
- Note that the floor assumption is unverified.

### A1-07 P3: the OCR benchmark's limits are not stated next to the figures

**Evidence**
- The figures are correct (reproduced above).
- n = 5 English pages plus 1 bilingual page, chosen by the author and transcribed by the same AI system that wrote the work, so there is no independent transcription. No interval is given.
- The text-layer baseline of 0.110 comes from pages selected because their layers were bad, so it is low by construction and is not a corpus figure.

**Required fix**
- Add a line under the benchmark table covering:
  - n = 5;
  - not independent;
  - pages chosen per category;
  - the baseline is by construction;
  - figures are indicative only.
- Get a second, independent transcription of at least 2 pages.

### A1-08 P3: the state machine ignores cover metadata

**Evidence**
- The 2 UNCERTAIN P&H writs (cwp-17142-2023, cwp-14834-2024) have titles "… Vs ARMED FORCES TRIBUNAL". Under CLAUDE.md, writs against AFT orders are in scope by definition.
- `hc-ph-2025-rsa-3901-2023` (Harpal Singh v Union of India through Secretary) is IRRELEVANT. It is a 2-page order that disposes of the appeal "in terms of" RSA 1582/2021, so its subject matter cannot be judged from its own text. It entered the corpus by party-name preselection.

**Required fix**
- Use the title and parties as a context family: an AFT party implies RELEVANT.
- Route short "covered by / in terms of" orders against the Union to CLASSIFICATION_UNCERTAIN.

### A1-09 P3: directive shortfall and hygiene

**Evidence**
- OCR recovery of the ~562 P&H titles: 12 done, 550 blocked pending a download run (16 of which are actually held; see A1-01).
- 8,052 flagged titles not processed.
- These are blocked legitimately and disclosed, but the owner decision should be an explicit, tracked request.
- `tools/c13_a1_ocr.py` and `tools/hf_ocr_c13.py` hard-code absolute scratchpad paths (`SCRATCH`, `STAGE`).
- PROGRESS.md not updated (disclosed).

**Required fix**
- Put an explicit approval request for a download run (tranche P0) in the task register.
- Make the paths configurable or relative.

## Answers to the six review questions

1. **Irrelevant vs unreadable.** States are distinct, and `legacy_relevance` never maps a non-final state to `rejected`. But the decision rule leaks: up to 20% of pages can be unread and un-OCR'd (A1-02), and IRRELEVANT can rest on low-quality OCR (A1-03). No current IRRELEVANT item is unreadable on my reading.
2. **Detector.** The relabel away from "needs OCR" is justified. The NO_CONTENT label is not (A1-05). Both figures should be headlined.
3. **Benchmark.** Transcriptions are faithful (GT03, GT04) and the accuracy reproduces exactly. The n=5 limits are under-stated (A1-07).
4. **HF commit.** Verified: correct parent, additive only, 27/27 sha256, no restricted material.
5. **Estimate and FN claims.** Measured and estimated are labelled honestly. The FN strata are disclosed as not random. The 3,770 figure lacks its interval and is wrongly called a floor (A1-06). The held-file count is stale (A1-01).
6. **Pipeline and tests.** `--check` passes and 34 tests pass. No protected or frozen record changed. The tests miss the 0.8 boundary (A1-02).

## Verdict

**CHANGES REQUIRED: 2 P1, 4 P2, 3 P3.**

The HF write, the benchmark arithmetic and the preservation of frozen records all hold. The two P1s must be fixed before the state machine is proposed for adoption or the population figures are reported to the owner:
- A1-01: the stale held-file count. 46 files, 16 of them P&H P0, are already on HF.
- A1-02: IRRELEVANT is possible with un-OCR'd pages.

---

## Confirmation round: head `c24da1ff` (`git log 39211848..c24da1ff`: 3 commits)

Scope of this round:
- I checked the fixes the author claims.
- I did not modify the branch, did not write to HF, and downloaded nothing from the web. HF was read-only.
- The branch still only adds files relative to staging: `git diff --diff-filter=MDR a4c0c382..c24da1ff` lists nothing outside `C13-A1-OCR/`, the two pipeline modules and the two tests. No frozen or protected record was changed.

### Re-run checks

| Check | Result |
| --- | --- |
| A1-02 reproduction | 5 pages, cover page image-only (share 0.8): **OCR_REQUIRED** without OCR, **INSUFFICIENT_TEXT** after OCR, `may_remove` False. The same holds at share 0.99 (100 pages, 1 bad page) and with 2 of 10 pages bad. The 80% rule is gone. |
| Truncated file | `document_summary(truncated=True)` gives **SOURCE_INCOMPLETE**, never TEXT_OK. The `missing_page` flag is in place. |
| A1-04 guard | A synthetic civil text plus "Army … commissioned" ×15 gives CLASSIFICATION_UNCERTAIN. **No rule special-cases D.D. Joshi:** grep for `joshi`, `1983insc17` and `2890b7b4` in `pipeline/`, `tests/` and `tools/` finds nothing. D.D. Joshi becomes UNCERTAIN through the general `GUARD` ("service vocabulary x67"), and so does `sc-1971 union-of-india` (x3). |
| A1-01 held count | 71 HELD_ON_HF: 46 at `9e3cf986`, 18 at `15bd03cc`, 7 at `3864faf3`. The 46 are **exactly** the 46 I found: old re-acquire list minus new re-acquire list = the new 9e3cf986 set. That leaves 8,006 to re-acquire. P&H T1 held: 28 (562 − 534), which is consistent. |
| A1-03 | The 2 remaining P&H IRRELEVANT were re-OCR'd with PP-OCRv5 (dictionary ratio 0.51–0.59, above the 0.35 floor). A fuzzy OCR guard and a by-reference rule were added. |
| Remaining 4 IRRELEVANT on content | I read all 4. **crwp-6842-2024**: a police-protection petition. **cr-5444-2024**: a civil revision under CrPC s.311. **J&K LPA 131/2026**: compensation for land acquired for a BSF Sector HQ; the appellant is a retired Lt Col. **J&K LPA 39/2022**: delay condonation refused after 22 years. None shows military-law content, so all 4 are irrelevant on their text. See A1-12 for a caveat. |
| A1-05, A1-06, A1-07, A1-09 | Done. Both recall figures are headlined. 9 labels are now MISSING_SOURCE_PAGE. The FPs were re-examined symmetrically. The estimate reads "≈ 3,760, range 2,650–5,240", with band counts under `RISK_FIGURES.json → estimated`. Benchmark limits are stated. `OWNER_REQUESTS.md` was added. Paths are configurable through environment variables. |
| HF `fafd4749628c…` | Parent `23acf21b` is correct (immediate predecessor, now head). Tree diff 16,198 → 16,240 files: **42 added, 0 removed, 0 changed**. The added set equals `HF_CANDIDATES_STAGED_MANIFEST.csv`. I re-downloaded all 42 at the pinned revision: **42/42 sha256 and size match**. No `4284820e…` or RM-001 doc_id appears in any file. |
| `--check` | CHECK PASS |
| Tests | `pytest tests/test_legal_audit_c13_ocr_*.py tests/test_legal_audit_c12_research_isolation.py`: **46 passed**. The full suite gives 922 passed, 1 skipped, and 1 collection error in `test_legal_audit_retrospective_deemed.py` (`ModuleNotFoundError`). That error comes from a file A1 did not touch, so A1 did not cause it. |

### Status of the original findings

| ID | Status |
| --- | --- |
| A1-01 | CLOSED |
| A1-02 | CLOSED. The boundary is fixed, but see the new A1-10 for a fail-open default. |
| A1-03 | CLOSED |
| A1-04 | CLOSED (general guard) |
| A1-05 | CLOSED |
| A1-06 | CLOSED |
| A1-07 | CLOSED |
| A1-08 | CLOSED in the pipeline and in `RELEVANCE_RERUN.csv`, but **not applied to the HF r1 overlays** (A1-11). |
| A1-09 | CLOSED |

### New findings

**A1-10 P2: `decide()` fails open when quality information is missing, a regression from the prior version.**
- **Evidence:** with a civil text of 150 or more words, each of these quality inputs gives **IRRELEVANT** with `may_remove` True:
  - `quality=None`;
  - `quality={}`;
  - `{"verdict": "OCR_REQUIRED", "usable_share": 0.5}`;
  - `{"verdict": "EXTRACTION_FAILED"}`.
- **Cause:** `unusable = q.get("unusable_pages") or []`, and the verdict is ignored.
- **Before the change:** `quality=None` gave OCR_REQUIRED.
- **Same pattern:** `ocr_quality_ok` defaults to True, so a caller that does not compute it skips the OCR quality floor.
- **Impact today:** none. The callers in `tools/` always pass a full `document_summary`, so no current state is affected. But this is the API proposed for adoption in `pipeline/judgments.py`, where it would control deletion.
- **Required fix:** fail closed.
  - IRRELEVANT only when `quality["verdict"] == "TEXT_OK"`, or when the caller passes an explicit list of unusable pages that is empty or fully covered by OCR.
  - Make `ocr_quality_ok` default to False, or make it a required argument.
  - Add tests for `None`, `{}` and a non-TEXT_OK verdict without a page list.

**A1-11 P2: the HF r1 overlays still record 2 of the 12 writs as UNCERTAIN, contradicting the README and `RELEVANCE_RERUN.csv`.**
- **Evidence:**
  - `data/meta_ocr/c13_r1/hc-ph-2023-cwp-17142-…json` and `…cwp-14834-2024…json` at `fafd4749` both carry `relevance.status = not_checked`, with the note "CLASSIFICATION_UNCERTAIN: keyword borderline; second check weak".
  - `RELEVANCE_RERUN.csv` and the README (task 5: "all 12 are RELEVANT (2 moved … by the AFT-party title rule); revised overlays published as r1") say RELEVANT.
  - **Cause:** `tools/hf_ocr_c13.py` calls `rs.decide(text=…, quality=…, ocr_done=True)` without `title=` or `ocr_quality_ok=`.
  - `--check` does not catch this, because it only compares the staged bytes with the same tool's own output.
- **Required fix:**
  - Pass `title` and `ocr_quality_ok` in `hf_ocr_c13.py`.
  - Publish corrected r2 overlays for the 2 records, additive and parent-pinned.
  - Add a `--check` assertion that the state in every staged overlay equals its `RELEVANCE_RERUN.csv` state.
  - Correct the README until r2 exists.

**A1-12 P3: caveats on the remaining IRRELEVANT verdicts, and the test count.**
- **J&K LPA 131/2026:** the court's own typos ("Lt. Co.", "Ltd. Col.") and "Border Security Force" slip past both the officer-rank family and the `GUARD`. The verdict is right on content, but only by chance.
- **J&K LPA 39/2022:** a delay-condonation order against the Union whose subject cannot be judged from its own text. This is the same pattern as A1-08's by-reference orders.
- **Suggested change:** route short procedural orders against the Union with no subject-matter text to UNCERTAIN, and add "Col." and the CAPF names to the guard.
- **Test count:** the author's "80 tests pass" is not reproducible. The documented command gives 46. Correct the figure.

### Verdict (confirmation round)

**CHANGES REQUIRED, minor: 0 P1, 2 new P2 (A1-10, A1-11), 1 new P3.**
- All 9 original findings are closed in the GitHub artefacts.
- A1-10 must be fixed before `relevance_states` is adopted.
- A1-11 needs an additive r2 HF correction.
- Neither affects the HF integrity (verified) or the frozen records.

---

## Confirmation round 2: head `cc190fde` (`git log c24da1ff..cc190fde`: 2 commits)

I did not modify the branch, did not write to HF, and made no web downloads. HF was read-only.

| Check | Result |
| --- | --- |
| A1-10 fail-open probes | I passed a civil text of 150 or more words with each of these quality inputs: `None`, `{}`, `{"verdict": "OCR_REQUIRED", "usable_share": 0.5}`, `{"verdict": "EXTRACTION_FAILED"}`, `{"verdict": "TEXT_OK"}` with no page list, `{"unusable_pages": []}`, and `{"verdict": "OCR_REQUIRED", "unusable_pages": []}`. I ran each both with and without `ocr_quality_ok=True`. Every case gives **INSUFFICIENT_TEXT** with `may_remove` False. Only complete TEXT_OK quality data plus `ocr_quality_ok=True` gives IRRELEVANT. `ocr_quality_ok` now defaults to False. The image-only cover page still gives OCR_REQUIRED, or INSUFFICIENT_TEXT after OCR. |
| HF `f4e6ba443ec9…` | Parent `fafd4749` is correct (immediate predecessor, now head). Tree diff 16,240 → 16,255 files: **15 added, 0 removed, 0 changed**. The added set equals `HF_R2_STAGED_MANIFEST.csv`. I re-downloaded all 15 at the pinned revision: **15/15 sha256 and size match**. No RM-001 sha or doc_id appears in any file. |
| Overlay states vs `RELEVANCE_RERUN.csv` | All 12 r2 overlays carry C13 state RELEVANT, matching the CSV; cwp-17142 and cwp-14834 now show status `borderline` with state RELEVANT. I also checked the 12 ingestion-candidate metas at `f4e6ba44`: all RELEVANT, matching. **0 mismatches across 24 records.** |
| A1-12 | `GUARD` now covers the CAPF names and "Col." typos, and short orders with the Union as a party go to UNCERTAIN. The 2 J&K LPAs moved from IRRELEVANT to UNCERTAIN. IRRELEVANT now totals 2 of 136 (the two P&H orders I read in round 1), and the README agrees. The test-count statement is corrected. |
| unittest conversion | I compared both test files at `c24da1ff` and `cc190fde` with an AST comparison that maps each `self.assertX` call to its plain `assert` form. **All 40 earlier tests are kept by name, with all 67 assertions identical** (45 in states, 22 in records). The only changes are to call sites: tests that expect IRRELEVANT now use the `decide_ok()` helper, which passes `ocr_quality_ok=True` as the new fail-closed default requires. That is a correct adaptation, not a weakening. 4 tests are new: missing quality data, OCR quality not established, CAPF/Col. typos, and short orders against the Union. |
| Tests and `--check` | `unittest discover … c13_ocr_*`: **44 tests OK**. Isolation: **6 tests OK**. pytest on the same files: 50 passed. `--check`: **CHECK PASS**. The worktree is clean. |
| Frozen records | Still unchanged. The branch only adds files relative to staging, and no file outside A1's scope was modified. |

### Status

| ID | Status |
| --- | --- |
| A1-01 to A1-09 | CLOSED |
| A1-10 | CLOSED |
| A1-11 | CLOSED |
| A1-12 | CLOSED |

**New P1 or P2:** none.

### Verdict (final)

**ACCEPT.** All 12 findings are closed and nothing new was found. Remaining owner items are tracked in `OWNER_REQUESTS.md`:
- a download run for the 534 P0 titles;
- adoption of the state machine;
- registration of the 12 candidates;
- human review.

The workstream status stays AUTOMATED_CANDIDATE_NOT_VERIFIED.
