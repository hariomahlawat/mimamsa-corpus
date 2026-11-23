# Discovery safety policy (Cycle 5 correction; applies to future automated discovery)

**Status:**
- The policy is implemented for read-only discovery in `tools/discovery_guard.py` and `tools/run_guarded_discovery.py`, with tests in `tests/test_legal_audit_c5_sources.py` (class `C5DiscoveryGuard`).
- It is **not** implemented in the crawler. Section 4 is a separate proposal. The crawler PR stack (#7, #8, #9, #17, #23) is untouched.

## 1. Rules
| # | Rule | Implementation |
| --- | --- | --- |
| 1 | robots.txt must be **established** before any other request to a host. The result is one of: a 200 text body that is parsed (`RULES_PARSED`); 404 or 410 (`NO_ROBOTS_FILE`, no rules); or anything else (`UNAVAILABLE`). Anything else covers 401, 403, 429, 5xx, a timeout, a TLS or connection error, an HTML or non-text body, an off-host redirect, or no status at all. | `robots_decision` |
| 2 | An `UNAVAILABLE` host receives **no further automated request** until independently cleared. "Cleared" means a later successful robots read, or an owner decision recorded in the repository. | `may_request` → `ROBOTS_UNAVAILABLE` |
| 3 | Explicit `Disallow` is respected. | robotparser `can_fetch` |
| 4 | robots decisions are keyed by **origin** (scheme + host + port). Each redirect hop to another origin needs its own robots decision and must itself be allowed. | `redirect_chain_allowed`; the runner follows redirects hop by hop |
| 5 | HTTPS only. TLS verification is never disabled. No CAPTCHA, login or access-control bypass. | `may_request` → `NON_HTTPS`; the runner uses Python `ssl.create_default_context` (verification on; never disabled) |
| 6 | Hosts blocked by repository policy (`aftjabalpur.in` and its subdomains) and bare-IP hosts are always refused. | `host_blocked` |
| 7 | Probe with HEAD first. GET only when HEAD returned 200 with an explicit listing content type. The GET is then decided again on **its own** status and headers before any body byte is read: 200; an explicit text listing type; no attachment disposition; identity encoding; declared length within the cap. Next, only the first 1 KiB is read; it must look like text with no document signature (PDF/ZIP/OLE/RTF) anywhere in it. The body is capped at 2 MB, and any read error discards it. Nothing is written to disk until every gate has passed. Redirects are never followed automatically. | `run_guarded_discovery.guarded_get`; `get_response_gate`; `body_prefix_gate` |
| 8 | A response is classified by method, content type, content disposition, size and (when bytes exist) file signature: `METADATA_OR_LISTING`, `HEADERS_ONLY`, `HEADERS_ONLY_DOCUMENT_INDICATED`, `DOCUMENT_PAYLOAD` or `UNKNOWN`. **The URL extension is never sufficient.** It is only a warning heuristic (`url_suggests_document`), which also catches query endpoints such as `showfile?filename=x.pdf`. | `classify_response` |
| 9 | A GET returning `DOCUMENT_PAYLOAD` or `UNKNOWN` with no acquisition approval reference is a violation. | `validate_log_v2` |

**Stated limits (reviews F-01 and the fix re-review):**
- A binary document placed behind a text lead-in longer than 1 KiB passes the prefix gate and is kept (the full body is not rescanned).
- A body truncated below its declared Content-Length is kept, because Python's `http.client` raises no error for it.
- The control-byte check runs only when the first 1 KiB is not valid UTF-8.
- "At most 1 KiB received" holds at the application layer; the TLS and socket buffers may hold more before the connection closes.
- An unexpected exception from the HTTP library ends the run without writing the request log.
- Up to 1 KiB of a disguised document can be received in memory before the abort. Nothing is written to disk.
- A publication served as plain text that passes the text checks cannot be distinguished from a listing.
- HTML that merely mentions "%PDF-" in its first 1 KiB is discarded. That is a false positive, in the safe direction.

The runner uses only the Python standard library, with TLS verification always on. The earlier curl-based path, and its dependency on curl ≥ 8.4, was withdrawn after review F-01/F-03. This revision has been tested with mocks only; it has not been run live.

## 2. Log format v2
The columns are: `utc_time, method, url, final_url, redirect_hosts, http_status, content_type, content_disposition, content_length, payload_class, file_signature, robots_state, purpose, acquisition_approval_ref, note`.
- `method=NONE` rows record a decision **not** to make a request.
- `WEBSEARCH` rows record search-engine queries. These send nothing to the target host. The search tool gives no timestamp, so their times are approximate.

The first v2 log is `discovery/D_requests_v2.tsv`. `check_c5.py` validates it, and it is clean.

## 3. What the historical (v1) logs can and cannot show
- **Kept unchanged:** `A_requests.tsv`, `B_requests.tsv` and `C_requests.tsv` are preserved. Their only amendments are in `discovery/log_amendments.csv`: two header insertions (LA-01/02), plus a disclosed Group B correction whose original values were **not retained** by the agent (LA-03).
- **What they record:** method, URL, status and byte count. **No content type, disposition or final URL.**
- **What can be said from them:**
  - No GET line is to a document-like URL (by extension or query parameter; `legacy_log_findings`).
  - No GET line records more than 200 KB.
  - No line touches a blocked host.
- **What cannot be said:** they **do not prove** that no document payload was ever received. A query or redirect endpoint could serve a PDF under an innocuous URL. The v1 logs cannot show this either way.

**Recorded deviations in Cycle 5 v1 discovery (not repeated in v2):**
- A UK National Archives page was fetched although robots.txt disallows it.
- Requests to desw.gov.in continued after its robots.txt returned 403 or failed.
- A mod.gov.in listing request was made before a successful robots retry.

## 4. Separate crawler proposal (NOT implemented here)
**Finding:** staging `config/sources.yaml` (source `indiacode`) sets `robots_unreachable: allow` and `robots_5xx: allow`. This is recorded there as an owner-approved exception dated 2026-11-21. `crawler/http.py` honours it, and `crawler/config.py` accepts it when a reason is given. The exception **conflicts with rule 2** above.

**Proposal C5-CRAWL-01** (for a separate, narrowly scoped PR; owner decision required):
1. **Owner decision first:** keep, narrow (for example, metadata API only, never documents), or withdraw the India Code robots exception. Agents do not override an owner approval.
2. **If withdrawn:** make `robots_unreachable` and `robots_5xx` accept only `disallow` (`crawler/config.py`), and remove the lenient path in `crawler/http.py`.
3. **Every crawler fetch:**
   - classify the response by content type, content disposition and signature (the `discovery_guard.classify_response` rules);
   - write `final_url`, `content_type`, `content_disposition` and `payload_class` to the audit log;
   - assess each redirect hop's host separately.
4. **Tests:** misleading extensions; query endpoints; off-host redirects to blocked or unreadable-robots hosts; robots 403/429/5xx/timeout/HTML body.
5. **Dependency:** the crawler code on staging is the base. PR #7 (aftjabalpur block) changes the same allow-list logic. The proposal should be based on, or rebased after, #7, and must not alter the pinned file lists in #8/#17/#23.
