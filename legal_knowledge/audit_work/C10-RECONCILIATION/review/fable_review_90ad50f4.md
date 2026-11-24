# Final narrow review of 90ad50f4 (delta e2ec65c4..90ad50f4)

Branch `claude/c10-unified-reconciliation`. Reviewer: Fable 5.2 (claude-fable-5-2), independent of the implementer. The reviewed worktree was not modified; experiments ran in a disposable worktree, since removed. Automated review, not legal verification.

## Verdict: ACCEPT WITH CONDITIONS

One condition: E3-01, a regression in the E2-04 title rule. Everything else claimed in `DISPOSITIONS_e2ec65c4.md` is confirmed. No P1 findings.

## Dispositions verified

| ID | Claimed | Verified | Evidence |
| --- | --- | --- | --- |
| E2-01 | FIXED | Confirmed | Judicial builder emits `OUTPUT_SHA256SUMS`; `--check` OK (11 outputs); `sha256sum -c` 0 failures of 14 (also 0 of 7 quality, 0 of 8 statutory); changing the findings file makes `--check` fail on the checksum file |
| E2-02 | FIXED | Confirmed | `source_completeness` is on every row of holdings, issues, relevance and copy register and agrees with the copy register in all of them; the 12 are `STORED_COPY_TRUNCATED_CONTENT_MAY_BE_MISSING`; no relevance reason for a truncated copy mentions OCR; only those 12 relevance reasons changed; no holdings or copy-register value changed apart from the new field |
| E2-03 | FIXED | Confirmed | 22 `STORED_COPY_TAIL_CUT_AFTER_EARLIER_EOF_BASE_REVISION_PRESENT`; all 3,951 raw files match my own byte scan (0 mismatches); measure 1 reworded |
| E2-04 | FIXED | **Not confirmed: regression** | See E3-01 |
| E2-05 | FIXED | Confirmed | "later pages missing" remains only in the code comment at `audit_judgments.py` line 144, as stated |
| E2-06 | FIXED | Confirmed | README line 5 |
| E2-07 | FIXED | Confirmed, one gap | The synthetic PDF does reach `OPENED` and `PROCESSED_TRUNCATED_COPY` under PyMuPDF 2.1; completeness, contradiction, bare-"Army" and checksum tests exercise the logic. The title test misses the form that regressed (E3-01) |
| E2-08 | ADOPTED | Confirmed | Summary sentence present |
| E2-09, E2-10 | DEFERRED | Accepted | The summary now states the possible overcount of about 230 |

## Regression checks

| Check | Result |
| --- | --- |
| Batches and `jextract.py` | Unchanged since e2ec65c4; the `audit_judgments.py` edits are all after `def summary_md`, so the fingerprint is unchanged |
| `assemble --check` | reproduces 14 files |
| quality / statutory / judicial `--check` | OK (8 / 9 / 11) |
| `CURATED_CASE_COPY_STATUS.csv` | byte-identical to 3257ebb9 |
| Accounting | 3,959 = 3,936 + 12 + 7 + 4; metadata audit, continuation manifest, master inventory and batch status unchanged |
| Relevance class totals | unchanged (679 / 2,693 / 33 / 71 / 483) |
| Tests, venv (Python 3.13) | 37 run, 0 skipped, OK |
| Tests, python3.11 | 37 run, 4 skipped with stated reasons (PyMuPDF x3, jsonschema x1), OK |
| Copies of my previous report and findings CSV in `review/` | byte-identical to what I wrote |

## Findings

| ID | Sev | Statement | Evidence | Requested action |
| --- | --- | --- | --- | --- |
| E3-01 | P2 | The new rank rule no longer matches the most common form, rank + "." + space. `(?:\.\|\s)` consumes the dot and the closing `\b` then fails before the space, so `CAPT. X`, `COL. X`, `BRIG. X`, `HAV. X` and `MAJ. GEN. X` are unflagged unless another term matches. 417 titles flagged at e2ec65c4 lost their flag and 80 gained one. With `(?:\.\s*\|\s)` in place of `(?:\.\|\s)` the same rule flags 8,077; the committed rule flags 7,700, so 377 titles are missed, 95 of them naming Union of India or UOI. The reported figure 7,700 is therefore too low, and the new test passes because it has no dot-plus-space case. The intended exclusions (inspector, manager, divisional, secy) work. | `delta_check.txt`; `jassemble.py` `TITLE_SCREEN`; direct regex probes | Change the separator to `(?:\.\s*\|\s)`, add `CAPT. X v UOI` and `MAJ. GEN. X v UOI` to the test, regenerate (expected 8,077 candidates) |
| E3-02 | INFO | `test_readable_pdf_without_eof_is_truncated_copy` accepts either truncated disposition, so it would still pass if the readable branch stopped being reached. Today it reaches it. | Direct run: `OPENED`, `PROCESSED_TRUNCATED_COPY`, 2 pages | Optionally assert `pdf_status == "OPENED"` |
| E3-03 | INFO | A few non-military uses are still flagged by the rank rule: `SUB ZONE` 4, `LT GOVERNOR` 3, `GEN INSURANCE` 1. Negligible, and the summary states that over-flagging is possible. | `delta_check.txt` | None required |

## Not checked

- Legal correctness of any outcome, holding or relevance class.
- HF-hosted bytes (no access).
- Batches were not re-extracted again: they and the extractor are byte-identical to e2ec65c4, where all 20 reproduced.

## Evidence files (this folder)

`delta_check.txt`, `scripts/delta_check.py`, `scan_all.csv`.
