# Confirmation of review findings F01–F03 on `claude/c13-gov` at `1dcf2c0b`

- **Reviewer:** an independent Opus instance, not the author. Read-only: I committed and uploaded nothing.
- **What I checked:** the head after `eab084c2`, which is `1dcf2c0b3d4935b429b20b468053a7cd2dc288cc` (local and `origin` agree).
- **How:** I read the diff against `eab084c2`, re-ran my original probes and ran the tests. The full HF head re-scan from the original review (`9e3cf986`) is not repeated here.

## Results

| Finding | Status | Evidence |
| --- | --- | --- |
| **F01** (P2) | **CLOSED** | RM-001 now has `audit_record_references` with 3 entries: `MARKING_HITS.csv` row 482, `readings_c10.csv` C10R-RAF-01 and forms `SOURCE_COVERAGE.csv` COV-26. Each entry describes what the record contains and how it is handled. The decision note's "Where held" row now says that two records quote short excerpts, labels the change as a correction, and leaves redaction as an owner decision. This matches my original findings, and I found no other records quoting the text. |
| **F02** (P2) | **CLOSED** | I re-ran `guard_probe.py` and saved the output as `guard_probe_out_1dcf2c0b.txt`. These cases now return True: section ids (`#s5`, `#S5`, and an upper-case id with spaces plus `#s69`), an upper-case doc_id, a trailing space, upper-case Windows paths, upper-case hashes in paths, a `sha256:` prefix, a hash with whitespace, a percent-encoded doc_id and a double-encoded path. I also checked for new false positives and found none: `act-army-1950#s69`, `data/text/act-army-1950.txt`, a mixed-case unrelated path and empty arguments all return False. 11 tests pass, including `test_legal_audit_c12_research_isolation.py`. |
| **F03** (P2) | **CLOSED** | Every test used copies of my `bk1` prefix backup (`data/raw/hc/2007`, HF `9e3cf986`). Results are in the table below. |

**F03 test results:**

| Test | Exit code |
| --- | --- |
| Clean backup | 0 |
| Recorded `MISMATCH` status with the `mismatches` list populated | 1 |
| `mismatches` list populated, status left unchanged | 1 |
| LFS file and its `computed_sha256` both changed (checked against `lfs_sha256`) | 1 |
| Non-LFS file and its `computed_sha256` both changed (checked against `git_oid`) | 1 |
| Ordinary single-bit tamper | 1 |

## Remaining P3 issues

These do not block, and none is a new P1 or P2.

- **F02:** these are still not matched:
  - a doc_id passed with a `.txt` suffix;
  - a vault path split as `ab/cdef…`;
  - the India Code source URL.
- **F04:** `filter_unrestricted` still lets a record keyed by `source_doc_id` through.
- **F08:** `verify` still returns exit 0 when a stray file sits at the backup root. I retested this.
- **Unchanged:** F05–F07 and F09–F12 are still open, as originally filed.

## New issues

No new P1 or P2 issues.
