# Dispositions: workstream and judgment-audit review of 3257ebb9

**Review:** `fable_review_ws_3257ebb9.md`, with findings in `fable_review_ws_3257ebb9_findings.csv` and the random sample of 20 in `fable_review_ws_3257ebb9_sample20.csv`. Reviewer: Fable 5.2 (claude-fable-5-2), independent of the implementer.

**Verdicts at 3257ebb9:**
- statutory: ACCEPT;
- judicial: ACCEPT WITH CONDITIONS;
- quality: ACCEPT WITH CONDITIONS;
- judgment audit: ACCEPT WITH CONDITIONS.

No P1 findings.

**The fixes below are in a later commit that has not itself been independently reviewed.** The PR body names that commit.

| ID | Sev | Disposition | What changed |
| --- | --- | --- | --- |
| WS-01 | P2 | FIXED | `audit_judgments.py` records `pdf_eof_anywhere`. A readable copy with no `%%EOF` anywhere is now `PROCESSED_TRUNCATED_COPY`: its extraction is partial, it counts as unresolved, it is in `CONTINUATION_MANIFEST.csv` ("a complete copy (re-acquisition needs approval)"), and it carries a verification-queue reason. There are 12 such files plus the 7 unreadable truncated copies, which equals the reviewer's 19 files with no `%%EOF`. |
| WS-02 | P2 | FIXED | The batch resume key now includes `extractor_fingerprint()`, the SHA-256 of `jextract.py` and of the extraction part of `audit_judgments.py`, so a batch made by other code is never reused. All 20 batches were deleted and re-extracted under `c10-jextract/6`. |
| WS-03 | P2 | FIXED | `build_quality_c10.py` gains `C9_COPY_NOT_INSTRUMENT`. d163e785 is now kind `C9_LISTED_COPY_NOT_THE_INSTRUMENT` and labelled as the Hindi text in Gazette pagination. C10-QP-02 now names d4449e99, and the 12 BNS citation rows no longer call d163e785 the compilation. Outputs regenerated; `--check` OK. |
| WS-04 | P2 | FIXED | Every record where the crawler outcome differs from the text candidate gets a contradiction note (549 of 1,775) and a verification-queue reason. The summary and `REVIEW_FINDINGS.md` report the ordinary-sample reliability (12 right, 3 wrong, 4 missed) and say to prefer the crawler metadata. |
| WS-05 | P3 | FIXED | `CORRECTION_PROPOSALS_C10.csv` CP-05..07 now show the verbatim current value read from the pinned raw-data meta (check `VERBATIM_FROM_PINNED_RAW_DATA_META`). My first attempt reused a builder variable name and emptied the curated-case table. That was caught before commit by the diff, and the builder now fails closed if the curated rows are not exactly 53. |
| WS-06 | P3 | FIXED | Coverage measure 2 counts files re-hashed equal (3,955 of 3,959). Measure 1 counts complete processed copies (3,936) and reports the 12 truncated-but-processed copies separately. |
| WS-07 | P3 | FIXED | `\bIndian Army\b` and `\bArmy\b` are added to the service-term rule. Sumit Arora (J-3489f75615a778b1) is now RELEVANCE_UNCERTAIN_REVIEW. NOT_RELEVANT fell from 74 to 71; the remainder are CAPF, railway, commercial or tax matters, excluded by rule rather than by a reading. |
| WS-08 | P3 | FIXED | The excluded-log title rule now covers bare "defence", M.O.D. and rank prefixes. The summary states the limits: title only, and Defence Estates land matters may be over-flagged. |
| WS-09 | P3 | FIXED | `registration_proposals_c10.csv` now has `hf_bytes = NOT_CHECKED` and a separate `hf_listing_check` column (path and size against the HF listing), replacing the misleading `hf_byte_verification` column. Outputs regenerated; `--check` OK. |
| WS-10 | P3 | ACCEPTED, DEFERRED | Three wording-only inconsistencies; no count or proposal depends on them: (a) the Girish reading count is 3 in the findings and 4 in the summary row; (b) Shri Kant rows cite the C9 escalation number ESC-06, while the C10 matter is ESC-C10-03; (c) presence `HF_ONLY` for four cases that also have identical-hash working copies (the copies are listed in `working_store_paths`). To be corrected in the next judicial-workstream revision. |
| WS-11 | INFO | ADOPTED | Measure 3 is renamed "Independent AI document-review coverage (not legal review)". |
| WS-12 | INFO | NOTED | The pattern-list limit is stated in the summary. Such misses are NOT_FOUND or NOT_CONFIRMED, never contradictions. |
| WS-13 | INFO | ADOPTED | The summary cross-references the judicial workstream's curated-case figure (33 held), and explains the difference in method from this audit's 11 matched. |
| WS-14 | INFO | NOTED | Truncation is a defect of the stored copies on both stores, which are hash-consistent with HF `SHA256SUMS`. The judgment audit now reports it, and a complete copy needs approved re-acquisition. |

**Results after the fixes (automated; not legal verification):**
- Source files: 3,959 = 3,936 processed (complete copies) + 23 unresolved:
  - 12 processed from truncated copies;
  - 7 truncated and unreadable;
  - 4 HF-only binaries without bytes.
- Records: 4,259 = AUDITED_AUTOMATED 4,238 + AUDITED_AUTOMATED_SOURCE_TRUNCATED 12 + AUDITED_METADATA_ONLY_SOURCE_TRUNCATED 9.
- Relevance: DIRECT 679 / ADMIN 2,693 / GENERAL 33 / NOT_RELEVANT 71 / UNCERTAIN 483.
- Case number against text: MATCH 3,242 (was 3,038 with the stale batches 0-3).
