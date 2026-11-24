# Independent review of e2ec65c4 (diff 3257ebb9..e2ec65c4)

Branch `claude/c10-unified-reconciliation`. Reviewer: Fable 5.2 (claude-fable-5-2), independent of the implementer. The reviewed worktree was not modified; all experiments ran in a disposable worktree. Automated review, not legal verification.

## Verdict: ACCEPT WITH CONDITIONS

Conditions: fix E2-01 and E2-02 before merge. No P1 findings. The WS-02, WS-03, WS-04, WS-05, WS-06, WS-07, WS-09, WS-11 and WS-13 fixes are confirmed. WS-01 and WS-08 are fixed in part.

## What was verified

| Check | Result |
| --- | --- |
| Files with no `%%EOF` anywhere (own scan of all 3,951 raw blobs at ad77758d) | 19 = 12 `PROCESSED_TRUNCATED_COPY` + 7 `INCOMPLETE_COPY_TRUNCATED`; all 3,951 re-hash equal |
| Truncated copies unresolved and in `CONTINUATION_MANIFEST.csv` | Yes: 23 rows = 12 + 7 + 4 bytes-unavailable |
| Accounting identities | 3,959 = 3,936 + 23; 4,259 = 4,238 + 12 + 9; 120,185 excluded rows |
| Re-extraction of all 20 batches with the committed tools (PyMuPDF 2.1, Python 3.13) | 20 of 20 byte-identical to the committed batches |
| Stale-batch rejection | Appending a comment to `jextract.py` makes `assemble --check` fail and `extract` plan a re-run; editing code after `summary_md` does not invalidate; editing a batch body fails `--check` through `BATCH_STATUS.csv` |
| `assemble --check` | reproduces 14 files |
| quality / statutory / judicial `--check` | OK (8 / 9 / 10 files) |
| `CURATED_CASE_COPY_STATUS.csv` | 53 rows, byte-identical to 3257ebb9 |
| WS-03 | QP-02 names d4449e99; the 12 BNS citation rows label d163e785 `C9_LISTED_COPY_NOT_THE_INSTRUMENT` |
| WS-05 | CP-05..07 current values match the pinned meta (companion records sc-1983 and sc-1988 hold the same values) |
| WS-09 | 88 rows, `hf_bytes = NOT_CHECKED`; no cell changed other than the column split |
| WS-04 logic | 1,775 records have both outcomes, 549 differ, 549 notes, 0 notes where either side is empty or `NOT_FOUND`; 546 queue reasons = 546 distinct judgments |
| WS-06 | 3,955 = 3,951 raw + 4 working copies |
| WS-07 | Sumit Arora is now `RELEVANCE_UNCERTAIN_REVIEW`; NOT_RELEVANT 74 to 71 |
| Sample statements in the summary | 12 / 3 / 4 / 1 and "crawler right 3 of 4" match the sample CSV |
| Tests, venv (Python 3.13) | 30 run, 0 skipped, OK |
| Tests, python3.11 | 30 run, 3 skipped with stated reasons (PyMuPDF x2, jsonschema x1), OK |
| Test weakening | None: the diff only adds tests |

## Findings

| ID | Sev | Statement | Evidence | Requested action |
| --- | --- | --- | --- | --- |
| E2-01 | P2 | `workstreams/judicial/OUTPUT_SHA256SUMS` was not regenerated. Three entries no longer match the committed files: `CORRECTION_PROPOSALS_C10.csv`, `JUDICIAL_C10_MANIFEST.json`, `tools/build_judicial_c10.py`. The file verified at 3257ebb9, so this is a regression of this commit. The judicial builder does not write it and no test checks it. | `sha256sum -c` in the judicial folder: 3 FAILED of 14; the file still holds the 3257ebb9 hashes | Regenerate it; have the builder emit and `--check` it as the other two builders do |
| E2-02 | P2 | The research outputs for the 12 truncated-but-readable copies are not marked partial. `HF_JUDGMENT_HOLDINGS.jsonl` and `HF_JUDGMENT_LEGAL_ISSUES.jsonl` give them the same status as complete files, and 2 carry a `dismissed` outcome candidate and 5 carry propositions. `HF_JUDGMENT_RELEVANCE.csv` has no truncation marker: 6 are classed MILITARY_ADMIN from a truncated copy, and 5 still say "scanned pages need OCR before any exclusion", which the previous review said is wrong for these files. The marking exists only in the copy register, metadata audit, master inventory and queue. | 12 SHAs in the continuation manifest against the three outputs; `jextract.py` line 347; `jassemble.py` line 158 | Add a truncation field or status to the holdings, issues and relevance rows; replace the OCR reason for truncated copies |
| E2-03 | P3 | 22 more stored copies are byte-truncated and are counted among the 3,936 "complete copies". Each has an earlier `%%EOF` and then an appended digital-signature update that is cut off (no `startxref`, no final `%%EOF`; 9 have sizes that are exact multiples of 1,024). Text is not affected: for all 22 the base revision alone gives the same page count and character count as the full file. So the "no `%%EOF` anywhere" rule finds every copy with lost text, but "complete copies" is not true of these 22, and the previous review asked for a disposition on the trailing marker. | `scan_all.csv` (41 without trailing `%%EOF` = 19 + 22); `t22.txt`; batches: `pdf_eof_marker` false and `pdf_eof_anywhere` true in 22 `PROCESSED` records | Flag them (for example text complete, signature update truncated), list them, and reword measure 1 |
| E2-04 | P3 | WS-08 is fixed in part. The rank rule needs whitespace after the rank, so `COL.T.PRASAD Vs UOI`, `MAJ.GEN.…`, `WG.CDR.…` are still unflagged: 76 titles by my pattern. The new rule also flags non-military uses, about 40 (`SUB INSPECTOR` 14, `GEN MANAGER` 11, `SUB DIVISIONAL` 10, `GEN SECY` 5). The summary says the rule "covers rank prefixes". | Own regex over `HF_JUDGMENT_EXCLUDED_DISPOSITIONS.csv.gz`; flagged 6,048 to 8,037 | Allow `.` without a space after the rank; exclude `sub inspector/divisional` and `gen manager/secy`; or state the limit |
| E2-05 | P3 | The summary and queue say "later pages missing" for all 12 truncated copies. Four of them (30cf7d58, d992ac2b, e04a2422, fb634cc6) have a text layer on every page; what they lack is the file tail. | `t22.txt`; copy register `text_extraction = TEXT_LAYER_OK` for those four | Say "stored copy truncated; content may be missing" |
| E2-06 | P3 | WS-11 was adopted in the summary only. `C10-HF-JUDGMENTS/README.md` line 5 still says "Independent legal review covers only the sample". | README.md | Use the same wording as the summary |
| E2-07 | P3 | The new tests do not exercise the new logic. Nothing builds a readable PDF without `%%EOF` to test `PROCESSED_TRUNCATED_COPY`; nothing tests the outcome contradiction rule; `test_bare_army_is_a_service_term` tests the regex, not the classification; nothing checks the judicial checksum file (E2-01). | `test_audit_judgments.py` class `ReviewFixes` | Add those four tests |
| E2-08 | INFO | At least 32 of the 549 outcome disagreements pair a crawler label with a text label the crawler never uses (`remanded`, `set_aside_quashed`, `transferred`), for example allowed against set_aside_quashed (10). These are flagged as differing but may not contradict. | Pair counts from `HF_JUDGMENT_METADATA_AUDIT.csv` | Optionally note the vocabulary difference |
| E2-09 | INFO | The extractor fingerprint covers `jextract.py` and the extraction part of `audit_judgments.py`, not the PyMuPDF version, which the batch header does not record. `requirements.txt` pins pymupdf 2.1, and that version reproduced all batches. | `extractor_fingerprint()`; batch header keys | Optionally record the library version in the header |
| E2-10 | INFO | Outside this diff. 62 groups (292 files) have identical extracted text but different file hashes, mostly a common judgment stored once per connected matter. Only one group appears in `HF_JUDGMENT_DUPLICATES.csv`, so "distinct judgments 3,959" may overstate by up to 230. `text_sha256` is already in the batches and unused. Seven of the 22 files in E2-03 are copies of one such judgment. | Own grouping of batch `text_sha256` (text over 500 characters) | Consider a `SAME_TEXT_DIFFERENT_FILES` duplicate kind in a later cycle |

## Not checked

- The legal correctness of any outcome, holding or relevance class.
- The 71 remaining NOT_RELEVANT judgments were not re-read.
- HF-hosted bytes (no access).
- The ACCEPTED/DEFERRED item WS-10, which this commit does not change.

## Evidence files (this folder)

`scan_all.csv`, `t22.txt`, `rerun_all_batches.log`, `scripts/scan.py`, `scripts/t22.py`.
