# Is `aft.gov.in` a legitimate, accessible route to AFT judgments? (read-only check, 2026-11-22)

**Method:** read-only HTTP GETs at intervals of at least 2 seconds, with the descriptive User-Agent. 10 page requests in total (robots.txt, home page, 3 judgment pages, 4 listing pages). No form was submitted, no CAPTCHA was attempted, and no PDF was downloaded.

## Findings
| Check | Result |
| --- | --- |
| Legitimacy | `aft.gov.in` resolves (45.127.74.206). Its pages are titled "Armed Forces Tribunal" with AFT branding and link to e-filing, cause lists, case status and judgments. It is a `gov.in` domain and is consistent with the official central AFT portal. The old bench sites (aftdelhi.nic.in and the others) time out from this container. |
| TLS | **HTTPS fails certificate verification here** ("unable to get local issuer certificate"). The cause may be the site's certificate chain or this environment's proxy and was not diagnosed. TLS verification was **not** disabled. Plain HTTP works, which gives no transport integrity. |
| robots.txt | `/robots.txt` returns the home-page HTML (HTTP 200), so **no robots rules are declared**. Apply the project's own politeness limits. |
| Main judgment search | `/judgements/daterange` (and the case-number, party, respondent, advocate, subject and free-text variants) is a GET form with a **`captcha` field**. **Not usable for automated collection** (project rule: no CAPTCHA bypass). Manual use by the owner is possible. |
| Static listings (no CAPTCHA) | `/reportable-judgements`: 8 rows, 7 PDFs. `/large-bench-orders`: about 44 rows, 32 PDFs. `/larger-bench-decided-orders`: 14 rows, no document links. `/review-cases-of-regional-benches`: 5 PDFs. `/aft-cases-appealed-in-high-court-supremecourt`: "No records found". |
| PDF host | Every listed PDF is served from a **bare IP, `http://103.154.2.123/~armedforces/...`, over HTTP**. The link comes from the official portal, but the host has no domain name and no TLS, so provenance rests on the referring official page. |

## Conclusion
- **Legitimate but limited.** `aft.gov.in` is the official portal. Bulk access to judgments goes only through a CAPTCHA-gated search, which is outside the crawler rules. It does **not** solve the AFT gap (GAP-12).
- **Small, rule-compliant subset available** *(the bare-IP/HTTP option below was REJECTED by the owner on 2026-11-22; see the Update section for the secure HTTPS route)*: about 44 PDFs (reportable judgments, larger-bench reference orders, regional-bench review cases) from static listings, if the owner approves the following:
  1. adding `aft.gov.in` (listing pages, HTTP) and `103.154.2.123` (PDFs) to the `aft` allow-list;
  2. recording for each PDF the referring official listing URL and row (case no., title, order date, bench) as provenance;
  3. accepting HTTP transport. Integrity then rests on recorded SHA-256 and re-fetch comparison.
- **Bulk AFT judgments still need** an Indian-network run against the bench sites (`crawler/aft.py`), owner-supplied request logs, or the owner's manual use of the portal search.

## Update 2026-11-22 (owner decision: no bare-IP HTTP route; find secure official alternatives)
**Cause of the HTTPS failure:** a server misconfiguration. `aft.gov.in` presents a leaf certificate (CN aft.gov.in, SAN www.aft.gov.in; valid 2026-11-12 to 2027-05-29) issued by **Sectigo Public Server Authentication CA DV R36**, but sends an unrelated eMudhra intermediate chain. Clients that do not fetch missing intermediates (curl, httpx) therefore fail with "unable to get local issuer certificate".

**Secure fix found (verification kept fully on):**
- The missing intermediate was obtained from the URL named in the leaf certificate's AIA extension (`http://crt.sectigo.com/SectigoPublicServerAuthenticationCADVR36.crt`). SHA-256 fingerprint: `8C:54:C3:34:B6:6B:A4:E4:26:77:2A:F4:A3:F9:13:6C:19:A1:AE:C7:29:FD:B2:8C:53:5C:07:A5:A4:EF:22:E0`.
- It verifies against the system trust store (issuer: Sectigo Public Server Authentication Root R46). With it, the `aft.gov.in` leaf verifies: `openssl verify` gives OK.
- The intermediate's authenticity rests on its signature chain to a trusted root, not on the HTTP transport used to fetch it.

**PDFs on the official domain over verified HTTPS:**
- `https://aft.gov.in/public/upload_document/<file>.pdf` answers 200 `application/pdf`. Example: `1743490037.pdf`, 223,144 bytes; HEAD only, nothing downloaded.
- So the static-listing documents (about 44: reportable judgments, larger-bench references, RB review cases) are reachable without the bare-IP HTTP host. The bare IP was **not** contacted.

**Still not a bulk route:** the portal's judgment search remains CAPTCHA-gated and will not be used.

**What execution would need (owner approval):**
1. A crawler change: a per-source `extra_ca_pem` (pinned intermediate, fingerprint-checked at load) added to the verification store for `aft.gov.in` only. Never `verify=False`.
2. `aft.gov.in` added to `aft.allowed_hosts` with `require_https: true` (as in PR 9).
3. Listing-page parsing that rewrites `http://103.154.2.123/~armedforces/armed-forces-main/public/upload_document/X.pdf` to `https://aft.gov.in/public/upload_document/X.pdf`, plus a test that no bare-IP or HTTP URL is ever queued.
4. Provenance recorded per PDF: the referring listing page and row, plus the HTTPS URL.
