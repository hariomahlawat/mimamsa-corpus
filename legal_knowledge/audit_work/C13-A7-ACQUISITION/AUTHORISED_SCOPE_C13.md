# C13 A7: proposed authorised acquisition scope (PROPOSAL; not applied)

Status: **proposal for coordinator and owner decision D-04.** The live `config/sources.yaml` is unchanged.
- Proposed config: `proposed/sources.yaml.proposed`.
- Diff against staging `a4c0c382`: `proposed/sources.yaml.diff`.
- Needed code: `proposed/crawler_revision/0003` (`redirect_scopes`, `ca_extra_pem`). The proposed config passes `crawler config-check` with that code.

Rebuild with `tools/build_scope_proposal.py --check`.

Evidence:
- `allowlist/PROBE_RESULTS.csv`: TLS, robots.txt, CAPTCHA and login flags per host (`tools/allowlist_probe.py`).
- `allowlist/PROBE_REQUEST_LOG.csv`: 138 logged requests.
- `allowlist/ARCHIVE_ITEM_NODES.csv`.
- `allowlist/ARCHIVE_REDIRECT_SCOPES.csv`.
- `allowlist/EGAZETTE_TLS_C13.md`.

Probe method:
- one robots.txt and one entry page per host, at least 2 s apart, no `From` header, no document downloaded from a non-allow-listed host;
- TLS checked with `openssl s_client -CAfile /root/.ccr/ca-bundle.crt -no-CApath -verify_hostname`;
- CAPTCHA detected by markers (captcha, recaptcha, g-recaptcha, …) in the served HTML; login detected by a password field or a login redirect.

## Decision rule (from the C13 brief)

A host is admitted only if:
- its TLS chain verifies;
- robots.txt permits the paths used;
- no CAPTCHA or login is involved in the requests the crawler would make.

A host whose relevant pages involve a CAPTCHA or login is **excluded**. Broad trust of redirect destinations is not accepted.

## Results

| Candidate | TLS (strict, proxy CA bundle) | robots.txt | CAPTCHA / login | Proposal |
|---|---|---|---|---|
| `sci.gov.in` | OK (Let's Encrypt YR2; 3 certificates served) | `/robots.txt` answers 301 to the `www.sci.gov.in` home page (HTML, so no rules). The probe recorded this as "parsed; allowed" (an HTML body parses to no rules) | Landing: none. Judgment search: see `www.sci.gov.in` | **Exclude** (only redirects to `www.sci.gov.in`) |
| `www.sci.gov.in` | OK (Let's Encrypt YR1; full chain) | 200: `Disallow: /wp-admin/` only | **CAPTCHA marker on `/judgements-judgement-date/`** (the judgment search) | **Exclude** under the CAPTCHA rule. Judgments are reachable only through the CAPTCHA search |
| `api.sci.gov.in` | OK (GlobalSign GCC R46 DV; SAN covers the host) | 200, no rules | Landing 200 with an empty body. No document URL was tested, because none is recorded and searching requires the CAPTCHA | **Conditional:** `sci_official` source, disabled, exact pinned URLs only. URLs come from a person's manual search, never a crawler search. Whether a file URL is CAPTCHA-free must be confirmed on the first owner-supplied URL; if it is not, exclude |
| `desw.gov.in` | OK (Sectigo Public Server Authentication CA DV R36) | 403, treated as "no robots file" (RFC 9309) | None on the landing page (no CAPTCHA marker, no password field) | **Admit** with exact document URLs only (3, from PR #9). The 13 MB ER 2023 copy gets its known `expected_sha256` (already preserved as C5-SRC-P1-ER-2023-HELD-13MB). The other two get a pin after a reviewed first fetch |
| archive.org storage nodes | All 74 node hosts probed: OK (GoDaddy-issued `*.us.archive.org` / `*.ca.archive.org` chain) | 404 on every node ("no robots file") | None (file servers) | **Admit only item-scoped `redirect_scopes`:** 85 (host, `/<n>/items/<identifier>/`) pairs for the 31 archive.org items still needed. No wildcard |
| `egazette.gov.in` (already allow-listed) | **Fails as served**: leaf only, missing YR1 and the Root YR cross-sign | 404, "no robots file" | None on the landing page | Keep. Add `ca_extra_pem` with 2 SHA-256 pins and strict chain building (`EGAZETTE_TLS_C13.md`). Use exact `WriteReadData` file URLs only |

### archive.org: why per-item scopes and not node hosts

The live run observed archive.org redirects (`acquisition/ACQUISITION_MANIFEST_C13.csv`, `attempts` column). For the
same item, the redirect sometimes goes to a node that the item's metadata API does not name. Example: the
1986-12-06 item's metadata lists `ia902803/ia802803` with `/22/items/…`, but the redirect went to
`dn790002.ca.archive.org/0/items/…`.

Each scope row therefore lists:
- the observed redirect host and path (31 rows, one per item);
- the metadata `d1`, `d2` and `server` hosts with the item `dir` (54 rows).

A redirect to any other host or path fails closed. It needs a new reviewed scope entry, never a wildcard. Every scope:
- names one exact host and one item directory;
- must be a subdomain of an allowed host (`archive.org`);
- is checked on every hop;
- applies with `require_https`.

The pinned md5 and size of every needed file equal the live archive.org metadata (`PR_PIN_CHECK_C13.csv`,
`archive_metadata_2026_11_25`), so the fetch-time integrity check (from PR #17, in patch 0003) still guards the bytes.

### Items that no longer need archive.org

7 of the 38 archive.org pins that are not in the corpus (ACQ-03 B3/B4 items whose files are named `E-…` or with a
2017–2018 ID) were served **byte-identically by the government host egazette.gov.in** under the archive item's file
name. They need no archive.org scope. For the 31 remaining items, mostly the numeric weekly-Gazette files of
1960–1975, the derived egazette URL answered 404.

## Not proposed

- Commercial databases: they stay on `blocked_hosts`.
- `aftjabalpur.in`: added to `blocked_hosts`, with subdomains (PR #7 content).
- `huggingface.co` as a crawler host: HF is the project's own preservation store, accessed through `HfApi` under governance, not by the crawler.
- Any CAPTCHA, login or search automation on SCI or egazette.

## What acceptance would unlock

| Decision | Unlocks |
|---|---|
| egazette `ca_extra_pem` | The 10 C12 egazette instruments (all 10 already fetched and preserved here) and future exact Gazette URLs |
| archive.org `redirect_scopes` (85 rows) | The 31 archive.org Gazette issues, including S.R.O. 348/1960 and 404/1960 (`acq03-011-b2`, `acq03-013-b2`), the 1966–1975 Army Rules amendments of ACQ-03, and S.O. 488/1978 and S.O. 4010/1986 |
| `desw` | ER 2023 (50 MB copy) and GMO 2023; the 13 MB ER 2023 copy re-fetch is pinned |
| `sci_official` (conditional) | Girish Kumar clarification (2026 INSC 1113) and Ram Avtar (C.A. 418/2012), once a person supplies the exact `api.sci.gov.in` URLs. Neither is in the allow-listed SC open-data bucket: its 2014 index has no Ram Avtar row; its 2026 index has only the 12-02-2026 Girish Kumar judgment (2026 INSC 149, already held) |
