# C13 A1 (Priority Zero): OCR recovery and the false-negative audit

Run 2026-11-25 on the 4-core / 15 GB build host, which other workstreams were using at the same time (load
average 8–18 for most of the run). **Status: AUTOMATED_CANDIDATE_NOT_VERIFIED.** Ground truth, page labels and
relevance references are AI work (Claude), not human or legal review. No legal conclusion is drawn.

## Results

| Task | Result |
| --- | --- |
| 1 Population | `RECOVERY_POPULATION.csv`: **8,077** C11-flagged excluded titles. **25 held** on HF (18 ingested in C12 at `15bd03cc`, 7 preserved at `3864faf3`); **8,052 need re-acquisition**, all from allow-listed open-data hosts. P&H T1: **562 titles, 12 held, 550 to re-acquire** (tranche P0). Plus 97 in-corpus text-risk records (65 files). The other 112,108 exclusions are counted (`POPULATION_SUMMARY.json`) but not listed. No excluded file other than those 25 is held anywhere (checked by SHA-256 against HF, the c7 object history and the scratchpad). |
| 2 Detector | `pipeline/text_quality.py`. On 150 AI-labelled pages (stratified, labeller blind to flags): **precision 0.849 (0.758–0.909), recall 1.000 (0.950–1.000)**, 73 TP / 13 FP / 0 FN. With the 9 uncorrected labels: recall 0.890. See "Detector validation" below. |
| 3 Benchmark | Table below. Tesseract: **BLOCKED_PENDING_OWNER_APPROVAL_FOR_SYSTEM_PACKAGE**. |
| 4 Relevance re-run | `pipeline/relevance_states.py` (8 explicit states) + `RELEVANCE_RERUN.csv`. 77 P&H pages OCR'd in full (PaddleOCR) and the in-corpus tranche OCR'd with RapidOCR (unusable pages only, early stop on a confirmed RELEVANT); throughput and remainder in `OCR_THROUGHPUT.md`. |
| 5 The 12 P&H writs | OCR text + schema-valid overlay meta uploaded: **HF commit `23acf21b8ebc64693b0162eb979646b4e3a58a2d`** (parent `9e3cf9868a5d553cd6218ed5ac51c383560bbf0b`), 27 new paths, re-downloaded at the pinned commit: 27/27 SHA-256 match, tree diff = only staged paths added, none removed (`HF_VERIFICATION.csv`). States: **10 RELEVANT, 2 CLASSIFICATION_UNCERTAIN**. |
| 6 Ingestion | **0 newly ingested.** The only held, not-yet-ingested excluded files are the 7 preserved SC judgments: 6 CLASSIFICATION_UNCERTAIN → MANUAL_REVIEW_REQUIRED, 1 IRRELEVANT (`INGESTION_DECISIONS.csv`). Nothing else could be ingested without a download run. |
| 7 Risk | `MISSED_JUDGMENT_RISK.md`: measured FN rate 12/12 (P&H AFT writs, garbled layers) and 6/13 (SC, keyword gaps); estimated ≥ about 3,770 P&H exclusions deleted without any readable text. |

### OCR benchmark (6 AI-transcribed pages; `OCR_BENCHMARK.csv/.json`)

| Engine (licence) | Char acc. English pages (5) | Word acc. English pages | Bilingual page (GT06) char acc. | Content-word recall (all 6) | s/page* |
| --- | --- | --- | --- | --- | --- |
| PDF text layer (baseline) | 0.110 (garbled/empty) | 0.052 | 0.724 (Hindi shaping broken) | 0.108 | – |
| RapidOCR 1.2.3, PP-OCRv3 ONNX (Apache-2.0) | 0.900 | 0.712 | 0.382 | 0.730 | 25.2 |
| PaddleOCR 3.7.0 PP-OCRv5 mobile en (Apache-2.0) | **0.977** | **0.905** | 0.397 | 0.836 | 26.1 |
| PaddleOCR 3.7.0 PP-OCRv6 medium (Apache-2.0) | 0.974 | 0.902 | 0.414 | 0.859 | 85.9 |
| PaddleOCR PP-OCRv5 mobile det + Devanagari mobile rec (Apache-2.0) | – (GT06 only) | – | **0.985** | 0.907 (GT06) | 30.1 |
| PaddleOCR `lang=hi` (server detector) | FAILED: 20 GB allocation on a 15 GB host | | | | |
| Tesseract | BLOCKED_PENDING_OWNER_APPROVAL_FOR_SYSTEM_PACKAGE | | | | |

\* 200 dpi, 2 threads, one engine at a time, alongside one other OCR process of this workstream and other
agents' load (load average 7–15). Idle-host reference: PP-OCRv6 medium 71–74 s/page in a smoke test. The first,
heavily contended round (load 15–18) is kept in `benchmark_round1_contended/`; its texts are byte-identical.

Per category (char accuracy, best English engine PP-OCRv5 mobile): garbled P&H 0.994 / 0.998, noisy photocopy
0.939, degraded print 0.965, old SCR image page 0.989. RapidOCR misses an indented block on GT02 and is weak on
degraded scans (0.78–0.81). Engine confidence is recorded but never used: RapidOCR's mean confidence (0.76–0.92) did not track
accuracy (0.38–0.99); it reported 0.79 on the bilingual page it read at 0.38.

Downstream effect (measured): on the 12 P&H writs the text layer gives 0 keyword hits (the old rule deleted
them); OCR text gives 1–56 hits each and the C13 states above. Content-word recall against the ground truth,
a retrieval proxy, rises from 0.11 (text layer) to 0.84 (PP-OCRv5 mobile) over the six pages.

**Choice:** PP-OCRv5 mobile for English text (same speed as RapidOCR here, much better on degraded scans);
the Devanagari model for Hindi/bilingual pages. Model files and SHA-256: `benchmark/MODEL_FILES.csv`; pinned
venvs: `benchmark/requirements-*.txt`. PaddleOCR models came from huggingface.co (PaddlePaddle organisation).

### Detector validation

- Sample: 150 pages from the held set, stratified by detector stratum (so flagged pages are over-represented;
  the figures are for this sample, not corpus prevalence). Labels from text-layer excerpts and, for pages with
  under 100 characters, page images. `ground_truth/DETECTOR_LABELS.csv`.
- **Correction, disclosed:** 9 pages were first labelled "needs OCR" from a contact sheet that turned out to be
  faulty. Individually rendered, all 9 are blank (dark-pixel share 0.0; earlier Tesseract text of those pages is
  empty; they sit in damaged PDFs). They are relabelled NO_CONTENT with the original label kept beside the
  correction. The v1 result on the original labels is frozen in `detector_v1/`.
- **Design change after v1:** a page with almost no text and no placed image is now checked for ink on a 30 dpi
  render (threshold 0.001; blank pages measure 0.0). It changed no verdict in the labelled sample; it guards
  against scans drawn without placed images. This was decided after seeing the sample, so the figures above are
  not a fresh hold-out for v2. An independent relabel of a fresh sample is recommended.
- The 13 false positives are lists of case numbers and party names (low dictionary ratio). Their cost is an
  unnecessary OCR pass, not a missed judgment.
- Known gap outside the sample: Devanagari with broken shaping (legacy font mapping) passes as usable.

## Explicit states and how they supersede the old rule

`pipeline/relevance_states.py` (new; `pipeline/judgments.py` is not modified):

| State | When |
| --- | --- |
| RELEVANT | keyword pass `relevant`, or `borderline` confirmed by ≥2 strong context families |
| IRRELEVANT | usable text over ≥80% of content pages, ≥150 words, no keyword, no context family |
| INSUFFICIENT_TEXT | text read (layer or full OCR) but too little usable text |
| OCR_REQUIRED | unusable text layer and OCR not (fully) done |
| EXTRACTION_FAILED | file or page cannot be read |
| CLASSIFICATION_UNCERTAIN | borderline keywords, or no keyword with weak context |
| SOURCE_INCOMPLETE | truncated file (no `%%EOF`) with no keyword in the readable part |
| MANUAL_REVIEW_REQUIRED | no keyword but ≥2 strong armed-forces context families (possible false negative) |

The second check is a fixed lexicon of context families (AFT proceeding, court martial, service statute,
other ranks, officer ranks, service HQ, service pension / medical board, ex-servicemen, MoD), returning the
matched strings. `may_remove()` is true only for IRRELEVANT; the module itself deletes nothing.
`legacy_relevance()` maps every non-final state to schema status `not_checked` (never `rejected`).
To adopt it, replace the `else:` deletion branch of `pipeline/judgments.py::run` with a call to `decide()` and
delete only when `may_remove()`; the text-quality summary comes from `text_quality.assess_pdf()`.

Measured limits of the second check: 5 of 6 keyword-gap SC judgments are kept from deletion (UNCERTAIN or
REVIEW), 1 (D.D. Joshi) is still IRRELEVANT; 6 of 7 SC judgments the C12 review called not relevant land in
UNCERTAIN, so the review queue carries noise.

## Restricted material

`inputs/restricted_material.snapshot.json` is a copy of `config/restricted_material.json` on
`claude/c13-gov` (`dfce9140`). Every tool refuses RM-001 (source sha256, derived sha256s and doc_id); `--check`
and `tests/test_legal_audit_c13_ocr_records.py` assert that neither its hashes nor its doc_id appear in any
output. RM-001 is not a judgment and was never in any population here.

## Files

| File | Content |
| --- | --- |
| `RECOVERY_POPULATION.csv`, `POPULATION_SUMMARY.json` | Task 1 |
| `DETECTOR_VALIDATION.csv/.json`, `detector_v1/` | Task 2 |
| `ground_truth/` | 6 AI-transcribed pages (`GT_MANIFEST.csv`; printed text only, margin symbols, SCR margin letters and handwriting excluded) and the 150 page labels |
| `benchmark/`, `OCR_BENCHMARK.csv/.json` | Task 3 (hypothesis texts, timings, model hashes, venv pins) |
| `ocr_text/`, `OCR_PAGES.csv`, `OCR_THROUGHPUT.md` | OCR output with page markers; per-page quality and timing |
| `RELEVANCE_RERUN.csv/.json`, `INGESTION_DECISIONS.csv` | Tasks 4 and 6 |
| `HF_STAGED_MANIFEST.csv`, `HF_VALIDATION.csv`, `HF_COMMITS.csv`, `HF_VERIFICATION.csv` | Task 5 |
| `MISSED_JUDGMENT_RISK.md`, `RISK_FIGURES.json` | Task 7 |
| `inputs/` | Held-copy list, text-layer scans (held set and the 3,951-file corpus), page verdicts, usable text layers, OCR jobs, C12 base meta of the 12 writs, excluded-log summary, restricted-material snapshot |
| `tools/` | `c13_a1_ocr.py` (all builders, `--check`), `hf_ocr_c13.py`, `ocr_engines.py`, `ocr_population.py` |

```
python -I -B tools/c13_a1_ocr.py --check     # rebuild population, detector eval, benchmark, relevance, risk,
                                             # HF staged bytes; check verification, SHA256SUMS, restricted absence
python -m pytest tests/test_legal_audit_c13_ocr_*.py
```

`--check` needs no network and no PDFs (text layers of usable pages are committed in `inputs/`). Re-running the
scans or OCR needs the bytes: corpus files from git `ad77758d` / HF, the 25 held files from their HF paths.
OCR venvs: `venvs/a1-ocr` (rapidocr-onnxruntime, PyMuPDF 2.1) and `venvs/a1-paddle` (paddlepaddle 3.3.1,
paddleocr 3.7.0; set `PADDLE_PDX_MODEL_SOURCE=huggingface`, oneDNN disabled because paddle 3.3.1 fails with it).

## Blockers and owner decisions

1. **Download run for re-acquisition** (8,052 flagged titles; P0 = 550 P&H T1). Not done: needs owner approval.
2. **Tesseract** (system package): BLOCKED_PENDING_OWNER_APPROVAL_FOR_SYSTEM_PACKAGE; PaddleOCR covers the need.
3. **Adopting the state machine** in `pipeline/judgments.py` (change to an existing crawler stage: owner decision).
4. **Human review** of the MANUAL_REVIEW / UNCERTAIN queue, the 2 uncertain P&H writs, and the detector labels.
5. PROGRESS.md was not updated (outside this workstream's scope).
