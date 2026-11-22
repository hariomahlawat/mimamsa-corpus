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
- **Small, rule-compliant subset available:** about 44 PDFs (reportable judgments, larger-bench reference orders, regional-bench review cases) from static listings, if the owner approves the following:
  1. adding `aft.gov.in` (listing pages, HTTP) and `103.154.2.123` (PDFs) to the `aft` allow-list;
  2. recording for each PDF the referring official listing URL and row (case no., title, order date, bench) as provenance;
  3. accepting HTTP transport. Integrity then rests on recorded SHA-256 and re-fetch comparison.
- **Bulk AFT judgments still need** an Indian-network run against the bench sites (`crawler/aft.py`), owner-supplied request logs, or the owner's manual use of the portal search.
