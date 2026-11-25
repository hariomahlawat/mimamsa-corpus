# Missed-judgment risk: false negatives of the crawler's relevance rule (C13 A1)

**Status: AUTOMATED_CANDIDATE_NOT_VERIFIED.** Relevance references are LLM (Claude) reviews, not human or legal
review. Every figure below is labelled **MEASURED** (counted on bytes we hold) or **ESTIMATED** (extrapolated,
with the assumption stated). Machine-readable measured figures: `RISK_FIGURES.json` (rebuilt by `--check`).

## 1. What the old rule did

`pipeline/judgments.py::run` deleted every judgment whose extracted text had none of ten English keyword
phrases (`data/excluded_judgments.jsonl`: **120,185 entries**, all with reason "no military keyword in the
text"; Allahabad 30,321, Delhi 36,779, J&K 4,974, P&H 44,561, SC 3,550). A garbled or image-only text layer
is indistinguishable from an unrelated civil case under that rule. **71** of the 120,185 deleted files are held
on HF (18 ingested in C12, 7 preserved in C12, 46 preserved by C13 A7; SHA-256 check at HF `23acf21b`); the rest
would have to be re-downloaded. (The first version of this file said 25: that count predated A7's commit; review A1-01.)
**No download run was made in C13 A1** (owner approval is required for each real download run;
`RECOVERY_POPULATION.csv` is the dry-run plan).

## 2. MEASURED

### 2.1 The 25 first-tier titles acquired in C12 (selected by rank, not random)

| Court | Titles | Text layer unusable | Relevant per C12 review (= false negative of the old rule) | FN rate (Wilson 95% CI) |
| --- | --- | --- | --- | --- |
| P&H (12 Division Bench writs against AFT orders) | 12 | 12 (font without Unicode map) | 12 | 1.00 (0.76–1.00) |
| Supreme Court | 13 | 1 page in 1 file | 6 | 0.46 (0.23–0.71) |

Failure modes seen: P&H = **broken CMap / garbled Unicode** (all 12); SC = **keyword gaps** (6: seniority,
premature retirement, discharge, Art. 226 jurisdiction, promotion, Army Instruction 78/78 — readable
service-law judgments that use none of the ten phrases).

After C13 OCR (PaddleOCR PP-OCRv5 mobile) the revised C13 state machine puts all **12 P&H writs at RELEVANT**
(10 by keywords, 2 because the Armed Forces Tribunal is a party in the title; the first version left these 2
UNCERTAIN). For the 13 SC texts it gives 1 MANUAL_REVIEW_REQUIRED and 12 CLASSIFICATION_UNCERTAIN, **0 IRRELEVANT**:
all 6 keyword-gap judgments are kept from removal (the first version still discarded D.D. Joshi; the new
service-vocabulary guard stops that), but the 7 not-relevant ones also go to the review queue. The keyword-gap
risk is moved from silent deletion to human review; it is not resolved automatically.

### 2.1b The 46 first-tier titles re-acquired and preserved by C13 A7

States from the C13 rule only (no human or LLM review). RELEVANT = deleted by the old rule but relevant by keyword
pass or AFT party on readable or OCR text: an automated false-negative finding.

| Court | Titles | Unusable text layer | RELEVANT | MANUAL_REVIEW | UNCERTAIN | INSUFFICIENT_TEXT | IRRELEVANT |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P&H | 16 | 14 (broken CMap) | **12** | 0 | 2 | 2 | 0 |
| Delhi | 12 | 0 | 0 | 0 | 12 | 0 | 0 |
| SC | 12 | 2 | 0 | 1 | 10 | 1 | 0 |
| J&K | 4 | 0 | 0 | 0 | 1 | 1 | 2 |
| Allahabad | 2 | 0 | 0 | 0 | 1 | 1 | 0 |

So among the 28 held P&H T1 titles, 24 are RELEVANT under the C13 rule and 26 had unusable text layers. The 12 new
ones are written to HF as ingestion candidates (`fafd4749`).

### 2.1a In-corpus records the old pipeline could not judge

44 records were in the corpus with `relevance = not_checked` (Tesseract confidence below 70, or never extracted). After C13 OCR of their unusable pages: 24 IRRELEVANT, 14 SOURCE_INCOMPLETE, 6 INSUFFICIENT_TEXT, 3 CLASSIFICATION_UNCERTAIN, 0 RELEVANT. None is deleted; the IRRELEVANT ones are removal candidates for the owner. (`RELEVANCE_RERUN.csv`)

### 2.2 Text layers of the kept corpus (3,951 judgment files at `ad77758d`, detector v2)

| Court | Files | Broken-CMap pages (any) | …on most pages | Any unusable page | Image-only page(s) | Does not open | No `%%EOF` |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P&H | 1,208 | 99 | 78 | 139 | 36 | 0 | 0 |
| Delhi | 1,678 | 0 | 0 | 108 | 31 | 7 | 41 |
| J&K | 410 | 1 | 1 | 7 | 1 | 0 | 0 |
| Allahabad | 309 | 0 | 0 | 0 | 0 | 0 | 0 |
| SC | 346 | 0 | 0 | 30 | 10 | 0 | 0 |

P&H broken-CMap files by decision year (kept corpus): 2014–2015: 12 of 30 (40%); 2023–2026: 83 of 666
(12.5%); other years: 4 of 512 (0.8%). The 78 kept P&H files whose text is garbled on most pages survived only
because a few readable lines carried a keyword; their `relevance`, `statutes_cited` and outcome fields rest on
fragments. (This is a data-quality finding for kept records, separate from false negatives.)

### 2.3 Detector and benchmark (details in `README.md`)

Detector on 150 AI-labelled pages (stratified): precision 0.849 (0.758–0.909), recall 1.000 (0.950–1.000)
after 9 label corrections; recall 0.890 with the uncorrected labels. A known detector gap not in the sample:
Devanagari text with broken shaping (legacy-font mapping, e.g. GT06) passes as "non_latin_ok".

## 3. Failure modes found

| Mode | Evidence | Where it bites |
| --- | --- | --- |
| Broken CMap / garbled Unicode (glyph ids as control characters) | MEASURED: 12/12 held P&H FNs; 99 kept P&H files | P&H, mostly 2014–15 and 2023–26 |
| Image-only pages | MEASURED: 36/31/10 kept P&H/Delhi/SC files have at least one; the old extractor OCR'd a file only when more than half its pages were empty, so a partly scanned file was judged on its text pages alone | All courts |
| OCR failure / low confidence | MEASURED: 38 in-corpus records OCR'd by Tesseract below confidence 70 were left `not_checked` (not deleted; `OCR_TRUST` rule) | Delhi land-acquisition scans, P&H |
| Incomplete downloads | MEASURED: 7 kept Delhi files do not open; 41 lack `%%EOF`; C11/C12: 18 remote copies are truncated too. Phantom pages past the cut used to count as "blank" and could make a truncated file look TEXT_OK; now flagged `missing_page` and summarised SOURCE_INCOMPLETE | Delhi |
| Wrong reading order (column/vertical extraction) | MEASURED: 12 pages flagged `vertical_order` in the held set | P&H |
| Low-quality OCR | MEASURED: RapidOCR word accuracy 0.41 on a Delhi scan page; IRRELEVANT now requires OCR pages at dictionary ratio ≥ 0.35 and blocks on near-miss tokens | Scans |
| Multilingual (Hindi) text | MEASURED example only: an Allahabad Art. 227 order against the AFT is written in Hindi ("सशस्त्र बल अधिकरण" = Armed Forces Tribunal); it was kept only because the English cover sheet names the Tribunal. The keyword list is English-only | Allahabad (and other Hindi-belt benches) |
| Keyword gaps | MEASURED: 6/13 held SC titles | SC and HC service law not using the ten phrases |
| Misclassification by the second check | MEASURED: first version discarded 1/6 keyword-gap SC judgments; revised rule 0/6, at the cost of 7/7 not-relevant SC judgments going to review | All |

## 4. ESTIMATED (assumptions stated; low confidence where marked)

| Stratum | Basis | Estimate |
| --- | --- | --- |
| P&H T1 with an AFT party, not yet held | Every C11 "AFT"-signal title is now held (24 of 24); none left | — |
| P&H T1 without an AFT signal, not held (534) | Only 4 such titles are held (A7): 0 RELEVANT, 2 UNCERTAIN, 2 INSUFFICIENT_TEXT. The 12 RELEVANT A7 P&H titles are all AFT-signal titles | unknown; not estimable from 4 files |
| SC T1 not yet held (34 titles) | Measured 6/13 (CI 0.23–0.71); the held 13 were the highest-scored, so this is likely an upper range | **8–24** (low confidence) |
| P&H excluded files with no readable text, all tiers | Kept-corpus broken-CMap rate per decision-year band (12/30, 83/666, 4/512) applied to the 4,251 / 14,971 / 25,339 excluded P&H files per band (`RISK_FIGURES.json` → `estimated`) | **≈ 3,760 files (rough 95% range 2,650–5,240; per-band Wilson intervals added, not a joint interval)** deleted without any readable text. Not a floor: the assumption that the defect is independent of case type is unverified, and the 12/12 garbled AFT writs suggest it is not |
| …of which relevant | Unflagged titles: relevance prevalence of the readable P&H crawl (about 1,208 kept of about 42,000 readable ≈ 2.9%). Flagged titles: between 2.9% and the measured share for held P&H T1 | **unflagged ≈ 100 (range ≈ 70–150); flagged between a few and about 140** (low confidence) |
| Delhi, J&K, Allahabad garbled-layer FNs | Kept corpus shows almost no CMap garbling in these courts | low; not quantified |
| Allahabad Hindi orders | No measurement possible without bytes; 30,321 Allahabad exclusions | unknown; plausibly material |
| Partly scanned files (any court) | Kept-corpus prevalence of image-only pages 1.9–2.6% of files | unknown share relevant |

**How to replace these estimates with measurements.** With owner approval for a download run, re-acquire a
stratified random sample (court × tier × year band, e.g. 30 per cell from `RECOVERY_POPULATION.csv`, about
600 files, on the allow-listed open-data hosts), run `pipeline/text_quality.py` and the OCR runner on them, and
have a human code relevance on a subsample. Tranche P0 (534 P&H T1 titles not yet held) is the obvious first acquisition.

## 5. What changes now

`pipeline/relevance_states.py` (new; the old stage is untouched) returns IRRELEVANT only when every content page
has usable text of adequate quality and no armed-forces signal of any kind, and `may_remove()` allows removal
only for IRRELEVANT. Adopting it in place of the
deletion branch of `pipeline/judgments.py::run` would stop new false negatives of the CMap and image-only
kinds; it does not by itself recover the 120,114 deleted files not yet held, and it only partly addresses keyword gaps.
