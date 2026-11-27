# Dispositions: narrow review of e2ec65c4 (diff 3257ebb9..e2ec65c4)

**Review:** `fable_review_e2ec65c4.md`, findings in `fable_review_e2ec65c4_findings.csv`. Reviewer: Fable 5.2 (claude-fable-5-2).

**Verdict:** ACCEPT WITH CONDITIONS. No P1 findings.

**Confirmed independently by the reviewer:**
- WS-02, WS-03, WS-04, WS-05, WS-06, WS-07, WS-09, WS-11 and WS-13 are fixed;
- all 20 batches re-extract byte-identically;
- a stale batch is rejected by both `extract` and `assemble --check`;
- all four builders reproduce under `--check`;
- the curated table is byte-identical to 3257ebb9.

**The fixes below are in the commit after e2ec65c4. That commit has a further narrow review; see the PR body.**

| ID | Sev | Disposition | What changed |
| --- | --- | --- | --- |
| E2-01 | P2 | FIXED | `build_judicial_c10.py` now emits `OUTPUT_SHA256SUMS` itself, so `--check` covers it. The file covers the outputs plus findings, input and tool sources, in the original order. `sha256sum -c` gives 0 failures. A new test, `WorkstreamChecksums`, verifies the judicial, quality and statutory checksum files. |
| E2-02 | P2 | FIXED | Each row of holdings, issues, relevance and the copy register now has a `source_completeness` field. The 12 truncated-but-readable copies are `STORED_COPY_TRUNCATED_CONTENT_MAY_BE_MISSING` in every research output. Their relevance reason no longer mentions OCR; it says a complete copy is needed and that the class rests on a truncated copy. Tests cover both. |
| E2-03 | P3 | FIXED | The 22 copies with an earlier `%%EOF` and a cut-off trailing update are `STORED_COPY_TAIL_CUT_AFTER_EARLIER_EOF_BASE_REVISION_PRESENT`. Coverage measure 1 is reworded: these files are processed, but the stored file is not byte-complete. They stay among the processed files, because the reviewer found their text unaffected. |
| E2-04 | P3 | FIXED | The rank rule now accepts `.` or whitespace after the rank and excludes `inspector`, `manager`, `divisional`/`division`, `registrar`, `secy`/`secretary` and `post office`. Re-screen candidates went from 8,037 to 7,700. A test covers the reviewer's examples. |
| E2-05 | P3 | FIXED | Summary, README and queue now read "stored copy truncated; content may be missing". The phrase "later pages missing" survives only in a code comment inside the extraction function, because editing it would change the extractor fingerprint and force a full re-extraction. That comment is the only remaining instance. |
| E2-06 | P3 | FIXED | README line 5 now says "Independent AI document review (not legal review)". |
| E2-07 | P3 | FIXED | New tests: a synthetic readable PDF with `%%EOF` removed goes through `_work` to `PROCESSED_TRUNCATED_COPY`; `source_completeness` rules; contradiction notes only when both outcomes are present and differ; bare "Army" moves the classification away from NOT_RELEVANT; rank-form title screen; workstream checksum files. |
| E2-08 | INFO | ADOPTED | The summary notes that some disagreements are differences of vocabulary only (`remanded`, `set_aside_quashed`, `transferred`). |
| E2-09 | INFO | NOTED, DEFERRED | Recording the PyMuPDF version in the batch header would change every batch. `requirements.txt` pins 2.1, which reproduced all batches. To be added at the next re-extraction. |
| E2-10 | INFO | NOTED, DEFERRED | 62 groups (292 files) have the same extracted text but different hashes. A same-text duplicate kind is proposed for the next cycle. Until then, "distinct judgments" counts distinct files and may overstate by up to 230. |
