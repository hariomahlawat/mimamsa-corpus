# C13 A1 (Priority Zero): OCR recovery and the false-negative audit

Run 2026-11-25 on the 4-core / 15 GB build host, which other workstreams were using at the same time (load
average 8–18 for most of the run). **Status: AUTOMATED_CANDIDATE_NOT_VERIFIED.** Ground truth, page labels and
relevance references are AI work (Claude), not human or legal review. No legal conclusion is drawn.

## Results (revised after independent review REVIEW_A1, findings A1-01..A1-09)

| Task | Result |
| --- | --- |
| 1 Population | `RECOVERY_POPULATION.csv`: **8,077** C11-flagged excluded titles. **71 held on HF** (18 ingested in C12 at `15bd03cc`; 7 preserved in C12 at `3864faf3`; **46 preserved by C13 A7** at `9e3cf986`), checked by SHA-256 against every PDF under `data/raw/` and `legal_knowledge/` at HF `23acf21b` (LFS sha256 plus re-download and A7's `PACKAGE_SHA256SUMS`). **8,006 need re-acquisition**, all on allow-listed open-data hosts. P&H T1: **562 titles, 28 held, 534 to re-acquire** (tranche P0). Plus 97 in-corpus text-risk records (65 files). *Correction:* the first version said "25 held"; that count was taken at `3864faf3`, before A7's commit, and was false at A1's own parent commit (A1-01). |
| 2 Detector | `pipeline/text_quality.py`. On 150 AI-labelled pages: **recall 0.890 (0.804–0.941) on the original labels; 1.000 (0.950–1.000) after relabelling 9 pages that lie past the cut of truncated downloads** (MISSING_SOURCE_PAGE, not OCR-able). Precision 0.849 (0.758–0.909) either way. See "Detector validation". |
| 3 Benchmark | Table below (n = 5 English pages + 1 bilingual page; indicative only). Tesseract: **BLOCKED_PENDING_OWNER_APPROVAL_FOR_SYSTEM_PACKAGE**. |
| 4 Relevance re-run | `pipeline/relevance_states.py` (8 explicit states; rule tightened per A1-02/03/04/08) + `RELEVANCE_RERUN.csv` over **136 held documents**: 36 RELEVANT, 2 IRRELEVANT, 50 CLASSIFICATION_UNCERTAIN, 2 MANUAL_REVIEW_REQUIRED, 32 INSUFFICIENT_TEXT, 14 SOURCE_INCOMPLETE (after the confirmation-round fixes A1-10 and A1-12). 567 pages OCR'd (174 PaddleOCR v5 mobile, 393 RapidOCR), 25 skipped by early stop, 0 left (`OCR_THROUGHPUT.md`). On the original 90 documents the tightened rule moved IRRELEVANT from 26 to 2: the 21 Delhi land-acquisition copies now stop at INSUFFICIENT_TEXT (their table pages stay unusable after OCR), and RapidOCR text below the 0.35 dictionary-ratio floor can no longer support IRRELEVANT. The 10 small P&H OCR'd orders were re-OCR'd with PaddleOCR; 21 rows still resting on RapidOCR text are marked `provisional`. |
| 5 The 12 C12 P&H writs | OCR text + overlay meta: HF `23acf21b8ebc64693b0162eb979646b4e3a58a2d` (27 paths, verified 27/27). Under the revised rule all **12 are RELEVANT** (2 moved from UNCERTAIN by the AFT-party title rule). The r1 overlays (`data/meta_ocr/c13_r1/`, HF `fafd4749`) were built by an upload tool that omitted `title=`, so they still record CWP-17142-2023 and CWP-14834-2024 as UNCERTAIN (review A1-11). **r2** (`data/meta_ocr/c13_r2/`, all 12 RELEVANT) is published at **HF `f4e6ba443ec9c0b89b2c5d21d0b5cda38f55d2dc`** (parent `fafd4749`), 15 paths, re-downloaded 15/15 SHA-256 match, tree diff = only staged paths (`HF_R2_VERIFICATION.csv`). `--check` asserts every r2 overlay state equals `RELEVANCE_RERUN.csv`. The c13 and r1 overlays stay unchanged on HF and are superseded. |
| 6 Ingestion | **12 new ingestion candidates** (all P&H T1 petitions by the Union against AFT orders; 11 had broken-CMap text layers and 1 a clipped text layer; all 12 OCR'd with PaddleOCR) written to `legal_knowledge/ingestion_candidates/c13_a1/{text,meta}/`: **HF `fafd4749628c04a71f6750160c7748c725a1b57d`** (parent `23acf21b`), 42 new paths with the r1 overlays; re-downloaded at the pinned commit 42/42 SHA-256 match, tree diff = only staged paths, none removed (`HF_CANDIDATES_VERIFICATION.csv`). Not registered in `data/` (needs the bytes copied to `data/raw/`: owner decision); meta valid except `raw_path`, which points at the preserved original. No duplicates against 4,345 meta records (doc_id, case number). No access marking on pages 1–2 of the OCR text. The other 34 A7-held titles: 28 CLASSIFICATION_UNCERTAIN, 1 MANUAL_REVIEW_REQUIRED, 5 INSUFFICIENT_TEXT → review queue (the 2 J&K LPAs first marked IRRELEVANT are now UNCERTAIN under A1-12). `INGESTION_DECISIONS.csv`. |
| 7 Risk | `MISSED_JUDGMENT_RISK.md`: measured FN 12/12 (C12 P&H AFT writs) and 6/13 (C12 SC, keyword gaps); 12 of 16 A7-held P&H T1 titles RELEVANT under the C13 rule; estimated ≈ 3,760 P&H exclusions without readable text (rough range 2,650–5,240, assumption-dependent). |

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

**Limits (A1-07):** n = 5 English pages plus 1 bilingual page, chosen by the author per category and transcribed by
the same AI system that did the work (no independent transcription yet; a second, independent transcription of at
least 2 pages is requested in `OWNER_REQUESTS.md`). No interval is given for n = 5. The text-layer baseline is low by
construction (pages were picked because their layers were bad) and is not a corpus figure. Treat all figures as
indicative.

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

- **Headline: recall 0.890 (95% CI 0.804–0.941) on the original labels; 1.000 (0.950–1.000) after relabelling 9
  pages from truncated files. Precision 0.849 (0.758–0.909).** 73 TP, 13 FP; FN 9 → 0 by the relabel.
- Sample: 150 pages from the held set, stratified by detector stratum (flagged pages over-represented; figures are
  for this sample, not corpus prevalence). One AI labeller, blind to flags. `ground_truth/DETECTOR_LABELS.csv`.
- **The 9 relabelled pages (A1-05):** first labelled "needs OCR" from a faulty contact sheet. They are phantom pages
  past the cut of truncated downloads (files of 32,768 / 262,144 bytes etc. without `%%EOF`; MuPDF rebuilds a page
  tree, Poppler cannot read them). Nothing exists to OCR, but the source pages had content, so they are labelled
  **MISSING_SOURCE_PAGE** (not "no content"), with the original label kept beside the correction.
- **Code change:** `assess_pdf` now flags empty pages of a file without `%%EOF` as `missing_page` (a defect), and
  `document_summary` never returns TEXT_OK for a truncated file (verdict SOURCE_INCOMPLETE). A file such as
  `f841d3fb` (32 pages, 27 missing) was previously summarised TEXT_OK.
- **Symmetric re-examination of the 13 FPs:** re-read from fuller page text; 12 are legible lists of case numbers
  or party/ailment lists (labels USABLE confirmed) and 1 is a header-only page with an emblem (NO_CONTENT,
  flagged image_only by the ink check). No label changed.
- **Not validated:** the `blank` verdict on intact files (all `blank` pages in the sample were from truncated files);
  the ink check (added after v1). An independent relabel of a fresh sample including blank pages from intact files is
  requested (`OWNER_REQUESTS.md`).
- Known gap: Devanagari text with broken shaping (legacy font mapping) passes as usable; the detector also missed a
  text layer with clipped lines (`hc-ph-2025-cwp-17353-2025`), which was re-OCR'd before its candidate record was written.

## Explicit states and how they supersede the old rule

`pipeline/relevance_states.py` (new; `pipeline/judgments.py` is not modified):

| State | When |
| --- | --- |
| RELEVANT | keyword pass `relevant`; or an Armed Forces Tribunal party in the case title (CLAUDE.md: writs against AFT orders); or `borderline` confirmed by ≥2 strong context families |
| IRRELEVANT | usable text (layer or OCR) on **every** content page, OCR pages at dictionary ratio ≥ 0.35, ≥ 150 words, no keyword, no context family, fewer than 3 bare service words (army, navy, military, commissioned…), fewer than 2 near-miss OCR tokens, not a short order disposed of "in terms of" another case |
| INSUFFICIENT_TEXT | text read but a page is still unusable after OCR, OCR text below the quality floor, or too few words |
| OCR_REQUIRED | any content page unusable and not OCR'd (any share, including one cover page) |
| EXTRACTION_FAILED | file or page cannot be read |
| CLASSIFICATION_UNCERTAIN | borderline keywords; or no keyword with weak context, bare service vocabulary, near-miss OCR tokens or a by-reference order |
| SOURCE_INCOMPLETE | truncated file (no `%%EOF`) with no keyword in the readable part |
| MANUAL_REVIEW_REQUIRED | no keyword but ≥2 strong armed-forces context families (possible false negative) |

The earlier rule (IRRELEVANT at ≥80% usable pages) is withdrawn (A1-02); boundary tests cover 0.8, 0.99 and a
single unread cover page. `decide()` fails closed (A1-10): IRRELEVANT needs `quality.verdict == TEXT_OK` with an
explicit empty `unusable_pages` list and `usable_share == 1.0`, and `ocr_quality_ok` defaults to False; missing or
incomplete inputs give INSUFFICIENT_TEXT. The guard also counts "Col.", "Lt. Co(l)." typos and CAPF names, and a
short order with the Union of India as a party goes to UNCERTAIN (A1-12). The second check is a fixed lexicon of context families (AFT proceeding, court martial, service statute,
other ranks, officer ranks, service HQ, service pension / medical board, ex-servicemen, MoD), returning the
matched strings. `may_remove()` is true only for IRRELEVANT; the module itself deletes nothing.
`legacy_relevance()` maps every non-final state to schema status `not_checked` (never `rejected`).
To adopt it, replace the `else:` deletion branch of `pipeline/judgments.py::run` with a call to `decide()` and
delete only when `may_remove()`; the text-quality summary comes from `text_quality.assess_pdf()`.

Measured on the 13 C12 SC judgments: all 6 keyword-gap judgments the C12 review called relevant are now kept
from removal (5 UNCERTAIN, 1 REVIEW; D.D. Joshi, with "army" ×33, moves from IRRELEVANT to UNCERTAIN through the
service-vocabulary guard, a general rule, not a special case). All 7 the review called not relevant also land in
UNCERTAIN, so the guard trades removals for a larger review queue (UNCERTAIN 23 → 22 and INSUFFICIENT_TEXT 6 → 27
on the original 90 documents; IRRELEVANT 26 → 2).

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
| `RELEVANCE_RERUN.csv/.json`, `INGESTION_DECISIONS.csv`, `HF_CANDIDATES_*.csv` | Tasks 4 and 6 |
| `HF_STAGED_MANIFEST.csv`, `HF_VALIDATION.csv`, `HF_COMMITS.csv`, `HF_VERIFICATION.csv` | Task 5 |
| `MISSED_JUDGMENT_RISK.md`, `RISK_FIGURES.json` | Task 7 |
| `inputs/` | Held-copy list, text-layer scans (held set and the 3,951-file corpus), page verdicts, usable text layers, OCR jobs, C12 base meta of the 12 writs, excluded-log summary, restricted-material snapshot |
| `tools/` | `c13_a1_ocr.py` (all builders, `--check`), `hf_ocr_c13.py`, `ocr_engines.py`, `ocr_population.py` |

```
python -I -B tools/c13_a1_ocr.py --check     # rebuild population, detector eval, benchmark, relevance, risk,
                                             # HF staged bytes; check verification, SHA256SUMS, restricted absence
python -m pytest -q tests/test_legal_audit_c13_ocr_states.py tests/test_legal_audit_c13_ocr_records.py \
    tests/test_legal_audit_c12_research_isolation.py   # 50 passed at this commit (the earlier "80" also counted tests/test_pipeline.py)
```

`--check` needs no network and no PDFs (text layers of usable pages are committed in `inputs/`). Re-running the
scans or OCR needs the bytes: corpus files from git `ad77758d` / HF, the 71 held files from their HF paths (`inputs/HELD_COPIES.csv`).
OCR venvs: `venvs/a1-ocr` (rapidocr-onnxruntime, PyMuPDF 2.1) and `venvs/a1-paddle` (paddlepaddle 3.3.1,
paddleocr 3.7.0; set `PADDLE_PDX_MODEL_SOURCE=huggingface`, oneDNN disabled because paddle 3.3.1 fails with it).

## Blockers and owner decisions (tracked in `OWNER_REQUESTS.md`)

1. **Download run for re-acquisition** (8,006 flagged titles; P0 = 534 P&H T1). Not done: needs owner approval.
2. **Tesseract** (system package): BLOCKED_PENDING_OWNER_APPROVAL_FOR_SYSTEM_PACKAGE; PaddleOCR covers the need.
3. **Adopting the state machine** in `pipeline/judgments.py` (change to an existing crawler stage: owner decision).
4. **Human review** of the MANUAL_REVIEW / UNCERTAIN queue, the 12 ingestion candidates, and the detector labels.
6. **Registering the 12 candidates in `data/`** (copy preserved bytes to `data/raw/`).
5. PROGRESS.md was not updated (outside this workstream's scope).
