# C13 A1: explicit requests for owner decisions (review A1-09)

None of these has been acted on. Each is needed to close part of the Priority Zero directive.

| ID | Request | Scope | Why |
| --- | --- | --- | --- |
| A1-REQ-01 | **Approve a download run** from the allow-listed open-data host `indian-high-court-judgments.s3.ap-south-1.amazonaws.com` for tranche **P0: 534 P&H first-tier titles** not yet held (`RECOVERY_POPULATION.csv`, `priority_tranche = P0`, `held = NO`). Rate ≥ 2 s per host, robots.txt obeyed, SHA-256 must equal the logged value, no `From` header unless `MIMAMSA_CONTACT_EMAIL` is set | about 534 files, roughly 8,000 pages; OCR about 21 hours with 2 processes | 24 of the 28 held P&H T1 titles are relevant under the C13 rule; the remaining P0 titles cannot be judged without bytes |
| A1-REQ-02 | Approve a **stratified measurement sample** (about 30 per court × tier × year band, about 600 files) from the rest of the 8,006 flagged titles | about 600 files | Replaces the estimates in `MISSED_JUDGMENT_RISK.md` §4 with measurements |
| A1-REQ-03 | Decide whether to **adopt `pipeline/relevance_states.py`** in place of the deletion branch of `pipeline/judgments.py::run` | code change to an existing crawler stage | Stops new false negatives of the CMap / image-only / truncation kinds |
| A1-REQ-04 | Decide whether to **register the 12 ingestion candidates** (HF `legal_knowledge/ingestion_candidates/c13_a1/`) in `data/` by copying the preserved bytes to `data/raw/hc/<yyyy>/` | 12 files, no new content | They are RELEVANT under the C13 rule and are writs against AFT orders |
| A1-REQ-05 | Assign a **human reviewer** for the review queue (`INGESTION_DECISIONS.csv`, `review_queue = YES`), the 12 candidates, and an **independent relabel** of a fresh detector sample (include blank pages from intact files) and an **independent transcription** of at least 2 benchmark pages | people | AI-only labels and transcriptions (A1-05, A1-07) |
| A1-REQ-06 | Tesseract system package: BLOCKED_PENDING_OWNER_APPROVAL_FOR_SYSTEM_PACKAGE (optional: PaddleOCR covers the need) | apt package | Benchmark completeness only |
