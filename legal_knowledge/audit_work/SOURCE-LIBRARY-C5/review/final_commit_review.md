# Independent review: 5bc2d12a..8e4e9dfe (RR-01, RR-03..05 handling)

## Method
- **Read-only.** Nothing under /home/user/c5 was modified. `git status` was clean before and after; HEAD is 8e4e9dfe71063de636d4a30d8fa90c9b5a4c8df9.
- **No network.** No external or loopback requests were made. curl was invoked only as `curl --version`.
- **Files read in full:**
  - the 5-file diff;
  - the current `tools/discovery_guard.py` and `tools/run_guarded_discovery.py`;
  - the runner and guard tests in `tests/test_legal_audit_c5_sources.py` (lines 233-380);
  - `reports/DISCOVERY_SAFETY_POLICY.md`, the D7 section and `C5R_GATE_RESULTS.txt`.
- **Byte comparison:** `review/final_diff_rereview.md` and the scratch c5review2 original were compared with `cmp` and sha256.
- **Re-runs, offline, with venv Python 3.13:**
  - unit tests: **328 OK, 0 skipped** (the earlier re-review saw 6 skipped in another interpreter);
  - `build_registers.py --check`: rc 0;
  - `check_c5.py`: `{"errors": 0, "sources": 112, "warnings": 0}`, rc 0.
- **Own mocked tests** (curl monkeypatched, DELAY=0, the same pattern as the repository tests):
  - `test_c5r3.py`: 27 tests, all pass. Every assertion records the *observed* behaviour, including the gaps.
  - `test_c5r3_p1.py`: 2 tests, all pass.
  - Output is in `test_output.txt` and `test_output_p1.txt`.
- **Abbreviations:** RG = `run_guarded_discovery.py`, DG = `discovery_guard.py`. Both are in `legal_knowledge/audit_work/SOURCE-LIBRARY-C5/tools/`.

## Checks

### A. Signature detection (DG:109-116, RG:115, RG:119)
- **What is detected:**
  - `%PDF-` after junk is detected when the 5-byte header lies wholly inside bytes 0-1023. Offsets 1, 100 and 1018 were tested.
  - A header that starts at byte 1020 straddles the 1 KiB boundary and is missed.
  - Anything after 1 KiB is missed. It is classified METADATA_OR_LISTING when the content type is a listing type.
  - With content type text/html and leading junk plus PDF bytes, the result is DOCUMENT_PAYLOAD.
- **Other signatures:** only PDF gets the scan. ZIP/OOXML, OLE and TIFF are still checked at offset 0 only, so a BOM in front of PK is missed. RTF and gzip-compressed bytes are not recognised at all.
- **False positive:** an HTML page with the literal text `%PDF-` in its first 1 KiB (for example in a `<title>`) is classified DOCUMENT_PAYLOAD. The page is deleted and logged as a violation, and the run exits rc 1. This fails closed, but it loses the listing and puts a false violation in the audit log.
- **Read sites:** both classification reads now take 1024 bytes (RG:115 for the probe, RG:119 for the full GET). The robots read (RG:83) is not used for classification.
- **Coverage:** no repository test was added for the 1 KiB scan; the diff touches no tests.

### B. Redirect-host robots (RG:94-111, DG:139-153)
**What the runner does:**
- `ensure_robots(h)` (RG:96) runs before `may_request` and before every HEAD, on every hop.
- The off-host redirect order is robots(B), then HEAD(B). This was tested.
- Each of these cases fails closed with no request to the target:
  - unreadable robots (503);
  - Disallow;
  - a blocked host;
  - an IPv4 or IPv6 literal;
  - https→http on the same host (`NON_HTTPS`).
- A downgrade to a *new* host still fetches `https://new/robots.txt` before refusing. That is a decision-only contact.
- A relative Location is resolved with `urljoin`.
- A 3xx with no Location becomes a NONE row. Its note is the misleading "GET refused: HEAD gave no explicit listing content type".
- A loop (more than 6 hops) stops after 6 HEADs with no GET. **No row records that the redirect limit was hit.**
- The probe and full GET run without `-L`, so they never follow a 3xx.

**`redirect_hosts` semantics:**
- The runner writes the hosts visited so far *including the current host* (RG:106). The Location target is not in the column; it appears only in `final_url`.
- Every host in the column has already passed `ensure_robots`. The new validator check (DG:149-151) is therefore tautological for runner-produced logs: it can never fire, and it can never false-positive on them.
- It does catch hand-made logs that list an undecided host (tested).
- It ignores the `final_url` host (tested: an undecided `final_url` host passes). For this runner that is harmless, because nothing is fetched there without a new hop.

**Ports:**
- `host_of` drops the port. A redirect or target to `https://a.gov.in:8443/` is HEAD-requested using the robots decision for `a.gov.in:443`. `https://a.gov.in:8443/robots.txt` is never fetched (tested).
- RFC 9309 scopes robots to scheme, host and port.

### C. Document download (RG:112-126)
- **Empty-probe path (P1):** a server that ignores Range, returns a known `Content-Length` above 4096 and labels a PDF text/html goes through these steps:
  1. curl refuses before writing any byte (`--max-filesize` with a known length: exit 63).
  2. The probe file is absent, so `first = b""`.
  3. The classification uses headers only (`text/html`), giving METADATA_OR_LISTING.
  4. The **full GET writes the whole document (up to 3 MB) to disk**.
  5. Only then is it deleted, if `%PDF-` is in the first 1 KiB.
- **This needs no change of content between requests.** The docstring at RG:9-14 says such a server "could deliver up to 4 KiB" and puts the full-GET risk only on a server that changes content.
- **Caveat:** the mocks assume curl still prints `%{http_code}`=200 on exit 63, which tool_operate's write-out normally does. If it printed 000 instead, the headers would be dropped and the result would be UNKNOWN, which stops the run. This was **not verified against real curl**: no network and no loopback server were used.
- **Kept-document paths** (rc 0, file kept in out_dir, all tested):
  - a full GET whose PDF header is after 1 KiB;
  - a gzip `Content-Encoding` body (curl runs without `--compressed`, and signatures are not checked on decoded bytes);
  - an RTF or other unsigned document served as text/html;
  - a document that is itself HTML. That is inherent: the runner cannot tell an HTML judgment from a listing page.
- **The HTTP status is ignored when classifying a GET:**
  - A 3xx probe or full-GET body (text/html) is kept as a listing (tested). It is not followed.
  - A 200 to a Range request is not treated as "Range ignored".
  - `err2` (curl exit 63 or a timeout) is ignored. A partial body cut off at 3 MB or by a timeout is kept.
- **Stale files:** a stale `<target_id>.html` left in out_dir by an earlier run would be classified in place of an empty probe. This was not tested.
- **Docstring:** only partly accurate (see F-01).

### D. curl runtime
- The local curl is **8.5.0** (Ubuntu build 8.5.0-2ubuntu10.16).
- The runner has no version check anywhere. RG:41-46 runs `curl` unconditionally, and `--max-filesize` behaviour is never probed.
- The requirement appears only in the docstring (RG:15). It is not in DISCOVERY_SAFETY_POLICY.md.
- The ≥ 8.4 claim matches my recollection of the curl changelog. I could not confirm it offline.
- **On an older curl** (for example the 7.81 that Ubuntu 22.04 ships), a chunked response that ignores Range would let the probe stream for up to 40 s without the 4 KiB cap.

### E. Review evidence
- The committed `review/final_diff_rereview.md` is **byte-identical** to the scratch original (sha256 34c9452e…830f).
- **Review chain:**
  - first review: `review/review_log.md` and `review_findings.csv`;
  - final-diff review: `final_diff_review.md` and `final_diff_findings.csv`;
  - re-review: `final_diff_rereview.md`;
  - this review, which is not committed.
- **D7 dispositions (D7:68-76):**
  - RR-01 is accurate as to what changed (1 KiB scan plus docstring). The re-review's other options, a lower full-GET cap and re-checking headers against the probe, were not taken, and the stated residual risk is incomplete (F-01).
  - RR-02 is a reasoned retention.
  - RR-03 is accurate but adds no detection power for runner output (F-04).
  - RR-04 is accurate.
  - RR-05 is in the docstring only (F-03).
- **Gate log:** `C5R_GATE_RESULTS.txt` line 19 was edited by hand ("re-run after RR fixes: unchanged" with the old 8.916 s timing). It is no longer raw tool output.

### F. Regressions
- None found.
- The committed v2 log still validates under the stricter validator (test at line 377 passes).

## Findings
| id | sev | file:line | observation | evidence | recommendation |
|---|---|---|---|---|---|
| F-01 | P1 | RG:114-120; docstring RG:9-14 | **An empty probe is treated as a listing.** If curl writes no bytes (known Content-Length > 4096 with Range ignored, so exit 63), the header-only classification passes and the full GET downloads the whole document, up to 3 MB, before deletion. The docstring says such a server delivers at most 4 KiB and blames full-GET risk only on content changing between requests. | `test_c5r3_p1.py::test_known_length_over_cap_probe_writes_nothing_then_full_doc_fetched` (900 kB written, then deleted, rc 1); the unsigned variant is kept with rc 0 | Require a non-empty probe of at most 2048 bytes with status 206 (or a 200 with a body under the cap), and treat a non-empty `err2` or exit 63 as stop. Fix the docstring. Add a repository test. |
| F-02 | P2 | RG:118-122; DG:125-136 | **Kept-document paths beyond the docstring.** A gzip Content-Encoding body, a PDF header after 1 KiB, RTF, a partial body after timeout or exit 63, and a 3xx body all stay on disk as "listing". HTTP status and curl errors are ignored in GET classification. | `test_c5r3.py` C_Download tests: gzip kept, offset 1100 kept, 3xx kept | Reject non-identity Content-Encoding. Require status 200 or 206 with an empty `err2`. Name these cases in the docstring and the policy. |
| F-03 | P2 | RG:15, RG:41-46 | **The curl ≥ 8.4 requirement is not enforced.** It is documented only in the docstring, and the runner neither checks nor fails on an older curl. | No version check in RG. The policy file does not mention it. Local curl is 8.5.0. | Parse `curl --version` at start-up and exit if it is below 8.4. Add the requirement to DISCOVERY_SAFETY_POLICY.md. |
| F-04 | P3 | DG:149-151; RG:106 | **The RR-03 check is tautological for runner logs.** `redirect_hosts` holds hosts already visited (including the current one), never the Location target, and `final_url` is unchecked. It catches only hand-made logs. | `test_redirect_hosts_column_semantics`, `test_validator_ignores_final_url_host` | Document the column's meaning, or also check the `final_url` host on non-3xx rows. |
| F-05 | P2 | DG:32-33; RG:73-96 | **Robots decisions are keyed by host without the port.** A `:8443` target or redirect is requested under the robots of `:443`, which is not what RFC 9309 requires. | `test_port_uses_robots_of_default_port` | Key robots decisions by netloc (host and port), or refuse non-default ports. |
| F-06 | P3 | DG:114 | **False positive on listing text.** HTML containing the literal `%PDF-` in its first 1 KiB is discarded and logged as a violation (rc 1). | `test_listing_page_with_pdf_text_discarded_and_flagged_violation` | Accept for now (it fails closed). Consider skipping the scan when the bytes start with `<` or `<!DOCTYPE`, or record the event as a suspected false positive. |
| F-07 | P3 | RG:94-111, RG:127-129 | **Redirect handling leaves unclear log records.** Exhausting 6 hops leaves no record. A 3xx without Location gets the misleading "GET refused…FD-02" note. A downgrade to a new host still fetches that host's robots.txt. | `test_loop_capped_silently`, `test_location_missing`, `test_downgrade_to_new_host_still_fetches_its_robots` | Log a NONE row for "redirect limit" and for "3xx without Location". Check the scheme before calling `ensure_robots`. |
| F-08 | P3 | tests/test_legal_audit_c5_sources.py | **No tests were added for RR-01 or RR-03.** | The diff touches no test file. | Add a 1 KiB-offset test and a `redirect_hosts` validator test. |
| F-09 | P3 | reports/C5R_GATE_RESULTS.txt:19 | **The raw gate output was edited by hand.** The note sits on the old timing line. | diff | Re-run the gate and paste the raw output. |
| F-10 | P3 | DG:72-85 | **User-agent-specific robots groups are ignored.** `can_fetch("*")` is used, but the runner sends the UA "Mimamsa-…", so a `User-agent: Mimamsa` group is never applied. This predates the diff. | Code reading | Call `can_fetch` with the UA token, and treat Disallow from either the specific group or `*` as binding. |
| F-11 | INFO | review/final_diff_rereview.md | Byte-identical to the scratch original. The chain is complete through the re-review. | sha256 34c9452e… | None needed. |
| F-12 | INFO | -- | No regressions: 328 OK, 0 skipped; `build_registers --check` rc 0; `check_c5` 0 errors. | Gate re-run | None needed. |

## Untested behaviour
- **Real curl was never run against a server** (no network and no loopback). Unverified:
  - exit-63 write-out of `%{http_code}`, which is the premise of F-01;
  - `--max-filesize` enforcement on chunked bodies in 8.5.0, and on versions below 8.4;
  - whether curl creates an empty output file when it aborts;
  - behaviour through the agent proxy, and TLS failures;
  - parsing of the `-D` header file for HTTP/2 and for multiple response blocks.
- Stale `<target_id>.html` reuse across runs, and duplicate target_ids in one TSV.
- The 40 s `--max-time` partial-body case against a real slow server.
- IDN or punycode hosts, hosts with a trailing dot, and userinfo in the URL.
- Robots files that redirect on the same host (always UNAVAILABLE by construction at RG:86; not tested).
- The `head` kind's targets beyond the HEAD-only path.
- Concurrency: the runner is single-process. Timing politeness was not tested because DELAY was 0 in the mocks.

VERDICT: ACCEPT WITH CONDITIONS

Conditions:
1. Fix F-01, or formally withdraw the runner from use, before any further live discovery run.
2. Correct the docstring so it does not claim a 4 KiB bound.
3. Address F-02, F-03 and F-05 before the runner is reused in C6.

The registers, data and review evidence in this diff are acceptable as committed. If project rules treat any open P1 as blocking regardless of whether the tool is in use, read this verdict as REJECT for the runner component.
