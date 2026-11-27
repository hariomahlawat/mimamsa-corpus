# Re-review: 8e4e9dfe..efde223c (fix commit 2e01aa17 and raw-gate commit efde223c)

## Method
- **Read-only.** HEAD is efde223c and the worktree was clean before and after.
- **No network.** Every scenario was mocked at `run_guarded_discovery.http_open`, with `DELAY=0`. One class uses a real `http.client.HTTPResponse` over an in-memory socket, still with no network.
- **Read in full:** the 9-file diff, the current `discovery_guard.py` (DG) and `run_guarded_discovery.py` (RG), the new test harness, policy rule 7, D7 and the gate file.
- **Byte comparison:** the committed `review/final_commit_review.md` and `review/final_commit_findings.csv` are byte-identical to my outputs (`cmp`).
- **My tests:** `test_fix_rereview.py`, 23 tests, all pass. Output is in `test_output_fix.txt`. Each assertion records the observed behaviour, including the remaining gaps.
- **Repository re-run:**
  - unit tests: **339 OK, 0 skipped**;
  - `build_registers.py --check`: rc 0;
  - `check_c5.py`: 0 errors, 0 warnings, 112 sources.
- **Changed files:** against 151f9358, the only change outside `legal_knowledge/audit_work/SOURCE-LIBRARY-C5/` is `tests/test_legal_audit_c5_sources.py`. Against 8e4e9dfe, 9 files changed, all within that scope.

## (1) F-01: fixed
- **Order of checks in `guarded_get` (RG:72-105):**
  1. `get_response_gate` (DG:147-171) runs on the GET's own status and headers before any read. It checks for status 200, a text listing type, no attachment disposition, identity encoding and a declared length within the cap.
  2. Only then is `read(1024)` called, followed by `body_prefix_gate` (DG:174-196).
  3. The body accumulates in memory up to `CAP` (2 MB). It is written at RG:175-177 only after every gate has passed.
- **My P1 scenario re-run against `http_open`** (a 900 kB PDF served as text/html with Range ignored):
  - at most 1024 bytes are handed to the caller;
  - the response is closed;
  - nothing is written;
  - rc is 1 (DOCUMENT_PAYLOAD is logged).
- **Other cases checked:**
  - A declared length above the cap: 0 bytes read.
  - A NUL or binary prefix, and RTF: discarded after at most 1 KiB.
  - `subprocess`, curl, `CERT_NONE` and `check_hostname=False` are absent. `ssl.create_default_context` is used.

## (2) F-02, F-03 and F-05
- **Encoding:** gzip Content-Encoding is rejected unread. gzip bytes sent without the header are rejected by the prefix gate.
- **Status:** a 206 or 203 GET is not read. A 302 GET is not followed (with `_NoRedirect`, urllib raises HTTPError and the body is not read).
- **Discards:** an over-cap chunked body and a timeout mid-body are both discarded.
- **Stdlib only.** curl is no longer used.
- **Robots keyed by origin** (`origin_key`, DG:43-47):
  - a `:8443` redirect fetches `https://a.gov.in:8443/robots.txt` before the HEAD;
  - an https→http downgrade to a new host makes no request at all (RG:127-130);
  - a robots.txt served 200 without a content type is now UNAVAILABLE (stricter, fails closed).
- **Remaining gaps (P3):** see R-01 to R-03 below.

## (3) F-04 and F-06 to F-10
- **F-04:** the column semantics are documented (DG:27-28). The validator now also requires a robots decision per origin (DG:218-226).
- **F-06:** accepted and documented. The prefix gate still treats HTML containing `%PDF-` as a document (tested).
- **F-07:** explicit NONE rows for a 3xx with no Location (RG:168-170) and for the hop limit (RG:185-186, tested). Non-HTTPS origins are refused before any request.
- **F-08:** tests were added.
- **F-10:** `may_request(url, robots, UA)` applies UA-specific groups (tested).
- **F-09: partly fixed.** `C5R_GATE_RESULTS.txt` now holds real per-command output, exit codes and the commit under test (2e01aa17). However, several blocks are clearly **tail-truncated**: they start mid-JSON with `  ]` or `"finding": 126,`. The header says "unedited except replacing the scratchpad path". It is excerpted raw output, not complete raw output (R-05).

## (4) Documentation accuracy
- The RG docstring (RG:1-23) and policy rule 7 match the code, with these exceptions:
  - **R-04.** "At most 1 KiB was received" and "up to 1 KiB … received in memory" hold at the application layer only. `http.client` reads through a buffered socket file of about 8 KiB, and TLS records and kernel buffers can hold more. Nothing beyond 1 KiB is passed to the guard or written.
  - **R-01.** The stated limit, "publication served as plain text", understates one case. A **binary** document behind a text preamble of more than 1 KiB is kept even though its NUL bytes sit in memory and could be checked.
  - **R-02.** "Any read error discards it" is true, but a premature EOF with Content-Length raises no error in `http.client.read(amt)`, so a truncated listing is kept.
  - **R-06.** Policy rule 5 still says "curl runs with default verification", which is stale.
- **D7** cites `review/final_fix_rereview.md`, which is not yet committed. This is the same pattern as RR-04 (R-07).

## (5) Regressions
- None.
- The committed v2 log still validates under the per-origin validator (test at line 483).

## Findings
| id | sev | file:line | observation | evidence | recommendation |
|---|---|---|---|---|---|
| R-01 | P3 | RG:91-103 | **Binary documents behind a long text preamble are kept.** A body whose first 1 KiB is text but which carries PDF or ZIP bytes and NUL bytes after it is written as a listing. Only the prefix is scanned, although the whole body is in memory. A valid PDF needs its header within 1 KiB, so this mainly affects crafted files or ZIPs with a prefix. | `test_pdf_after_text_preamble_over_1k_is_kept`, `test_zip_with_text_preamble_over_1k_is_kept` | Before writing, scan the full in-memory body for NUL bytes and signatures. |
| R-02 | P3 | RG:92-103 | **Truncated bodies are kept.** With Content-Length set, a premature EOF returns `b""` without IncompleteRead, so a partial listing is kept. Chunked truncation is discarded correctly. | `TruncatedRealHttpClient` tests | Discard the body when the total differs from the declared Content-Length. |
| R-03 | P3 | DG:184-195 | **The control-byte check is skipped for valid UTF-8.** It runs only when UTF-8 decoding fails, so control-heavy ASCII passes. The "not decodable" branch is unreachable because latin-1 decoding never fails. | `test_control_bytes_valid_utf8_pass` | Count control bytes whenever decoding succeeds too. |
| R-04 | P3 | RG:15, RG:18; policy limits | **"At most 1 KiB received" holds at the application layer only.** Socket and TLS buffering can receive more. | `http.client` design (not live-tested) | Say "at most 1 KiB passed to the guard; transport buffers may hold more; nothing is written". |
| R-05 | P3 | reports/C5R_GATE_RESULTS.txt | **The gate output is tail-excerpted but labelled unedited.** | Blocks begin mid-JSON | State that the output is a tail excerpt per command, or include the full output. |
| R-06 | P3 | DISCOVERY_SAFETY_POLICY.md rule 5 | **Rule 5 still says "curl runs with default verification".** | diff context | Replace with "ssl default context". |
| R-07 | P3 | D7 last line | **D7 cites `review/final_fix_rereview.md`, which is not committed.** | git tree | Commit this file verbatim. |
| R-08 | P3 | RG:60-61, RG:187-195 | **An uncaught exception loses the whole request log.** `http.client.HTTPException` (for example LineTooLong or BadStatusLine) and InvalidURL are not caught, and the log is written only at the end, so all request records are lost. This predates the fix. It fails closed for downloads but loses the audit trail. | Code reading | Catch `http.client.HTTPException` and `ValueError`, and write the log in a `finally` block or row by row. |
| R-09 | INFO | -- | **F-01, F-02, F-03, F-05, F-07, F-08 and F-10 are fixed. F-04 and F-06 are accepted with documentation.** | Tests above | None needed. |
| R-10 | INFO | -- | **No regressions:** 339 OK, 0 skipped; build check rc 0; `check_c5` 0 errors; scope limited to authorised files. | Re-run | None needed. |

## Untested behaviour
- No live run, and no loopback server. Not exercised against a real server:
  - real urllib proxy CONNECT;
  - TLS through `/root/.ccr` CA (via `SSL_CERT_FILE`);
  - real `_NoRedirect` 3xx handling;
  - real HEAD semantics;
  - socket buffering amounts.
- Slow-drip servers: the timeout is per operation, with no total deadline.
- IDN or punycode hosts, hosts with a trailing dot, and userinfo in URLs.
- Duplicate target_ids in one TSV.
- Robots bodies of 200 kB or more (UNAVAILABLE by construction).

VERDICT: ACCEPT
