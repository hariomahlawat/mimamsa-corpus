# C12 Workstream H: targeted acquisition

Run on 2026-11-24, 10:13 to 10:16 UTC, from the cloud build container through its egress proxy.
Nothing was committed and nothing was uploaded anywhere. Downloaded bytes are kept outside the git worktree at
`/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c12_acquired/<sha256[:2]>/<sha256>/<original-filename>`
(43 files, about 11 MB). No stored corpus file was overwritten or modified.

## Files

| File | What it is |
| --- | --- |
| `ACQUISITION_MANIFEST.csv` | One row per target (70): URL, host, allow-listed?, robots result, status, sha256, bytes, pages, completeness, relation to the existing copy, provenance, every attempt |
| `REQUEST_LOG.csv` | Every network request made (58): time (UTC), target, purpose, URL, host, HTTP status, bytes, elapsed ms, error |
| `TARGETS.csv` | The plan built before any request (`tools/build_targets.py`, no network) |
| `T1_PRIORITISATION.csv` | The 71 first-tier excluded titles that met both the party test and the court test; the 25 selected are marked |
| `fetch_results.json` | Raw per-target results from `tools/acquire.py`. The run can be resumed: targets that already have a hash are skipped |
| `sources.yaml.snapshot` | `config/sources.yaml` at `origin/legal-knowledge/v2.5-staging` (21e73b83), the allow-list used |
| `tools/` | `build_targets.py` (plan), `acquire.py` (`--dry-run` / live), `build_manifest.py` (merges the plan and results, re-hashing the bytes on disk) |

## Results

| # | Target | Outcome |
| --- | --- | --- |
| 1 | 22 incomplete judgment files | **18 HC files re-fetched** from the recorded source_url on the HC open-data mirror. **All 18 are byte-identical to the stored truncated copy** (same SHA-256), so the remote copy is also truncated. None is complete (7 do not open; 11 open but have no trailing `%%EOF`). No replacement candidate exists on the mirror. **4 SC files** (RETRIEVE_HELD_BYTES) have no crawler source_url. They are held in the project's HF dataset (`huggingface.co`), which is not allow-listed, so they are recorded as BLOCKED_HOST_NOT_ALLOW_LISTED along with the URL that would be used. The 23rd row (d992ac2b…) was not targeted: the corpus already has a complete-content copy |
| 2 | Girish Kumar clarification order (2026 INSC 1113) | BLOCKED_HOST_NOT_ALLOW_LISTED. The only official source is `sci.gov.in` / `api.sci.gov.in`, which are not allow-listed; the SC judgment search also has a CAPTCHA. The open-data mirror was deliberately not used because the brief allows the official source only |
| 3 | Ram Avtar order (10-12-2014, C.A. 418/2012) | BLOCKED_HOST_NOT_ALLOW_LISTED, for the same reason. No diary number or official URL has ever been recorded |
| 4 | Statutory LOCATED_NOT_ACQUIRED | **0 of 10 acquired.** The government host `egazette.gov.in` is allow-listed, but its TLS certificate chain fails verification ("unable to get local issuer certificate"; httpx and curl both fail). robots.txt therefore could not be read, and the run failed closed. TLS verification was not disabled. The archive.org fallback (allow-listed `archive.org`, robots.txt 200, path allowed) answers each download with a redirect to a storage node (`dn7xxxxx.ca.archive.org`, `dn76xxxx.eu.archive.org`, `ia600408.us.archive.org`). Those node hosts are not allow-listed, so the redirect was not followed. 4 DESW items (PRA 2008, ER 2008, GMO 2023, circulars) are recorded as BLOCKED (`desw.gov.in` is not allow-listed). The other 6 LOCATED_NOT_ACQUIRED rows have no pinned file URL on an allow-listed host and were not attempted |
| 5 | First-tier excluded titles | **25 of 25 downloaded and verified.** Every SHA-256 equals the crawler-logged value, with no mismatches. 24 are complete (`%%EOF`, they open, every page has text). One SC file (rank 375) is structurally complete, but page 3 has no text layer (OCR needed) |

How the 25 were chosen (first-tier titles only). A title qualified only if it met both tests below:

- **Party test.** The case involves the AFT, a court martial, or an armed-forces service party. A service party means a ranked serviceman or service HQ against the Union. Army schools, welfare and housing bodies, MES contractors, estate officers and CAPF are excluded.
- **Court test.** The court is the Supreme Court or a Division Bench. A Division Bench is shown by an LPA or special appeal, or by a writ against an AFT order, which a Division Bench hears.

71 titles qualified. The 25 were filled in this order:

- the 13 Supreme Court rows with the highest crawler score (ties broken by rank);
- then 12 Division Bench rows with an AFT party, in rank order (all are Punjab and Haryana HC writs against AFT orders).

## Policy compliance statement

- **Allow-list only.** Requests went only to hosts in an `allowed_hosts` entry of `config/sources.yaml`:
  - `indian-high-court-judgments.s3.ap-south-1.amazonaws.com`
  - `indian-supreme-court-judgments.s3.ap-south-1.amazonaws.com`
  - `archive.org`
  - `egazette.gov.in` (TLS handshake only; no HTTP request completed)

  Redirects were followed only to allow-listed hosts; 10 archive.org redirects were refused for this reason. `acquire.py` checks every URL against the allow-list before sending it.
- **aftjabalpur.in was never contacted.** It is removed from the allow-list in code (`NEVER_CONTACT`), and no target used it. The `blocked_hosts` in the config were never contacted. No commercial database was contacted (Indian Kanoon, SCC Online, Manupatra, Casemine).
- **robots.txt was obeyed.** It was read once per origin before any other request there:
  - S3 buckets: 404, meaning no robots file, so allowed.
  - archive.org: 200, parsed, and the download paths were allowed.
  - egazette.gov.in: unreachable (TLS failure), so disallowed. This is fail-closed: egazette has no robots exception in the config.
- **Rate limit of at least 2 s per host.** It applied to every host, including the open-data buckets, whose config allows 0.3 s. That allowance was not used. Requests went one at a time, with no parallelism.
- **User-Agent and From header.**
  - The User-Agent was the config's `user_agent` string, with no cookies, login, CAPTCHA handling or paywall access.
  - **Disclosure: the live run also sent the config's `defaults.contact_email` in the HTTP `From` header,** as `crawler/http.py` does.
  - After the run, a session privacy policy objected to sending the account email address from this session. `acquire.py` now sends `From` only when the owner sets `MIMAMSA_CONTACT_EMAIL` in the environment. A later manual curl re-check of the egazette TLS failure sent no `From` header.
- **Retries.** Exponential backoff (4 s base, at most 5 tries) applied only to timeouts, 5xx and 429. Proxy policy refusals are not retried. No retries happened in this run.
- **Audit trail.** Every request, robots.txt included, is in `REQUEST_LOG.csv` (57 from `acquire.py` plus 1 manual curl probe).
- **No overwrites.** Files are content-addressed by SHA-256 and written atomically, and existing files are never replaced. Truncated corpus copies were not touched. Re-fetched copies were registered only by relation: all 18 are IDENTICAL_TO_STORED_TRUNCATED_COPY, and no replacement was registered.
- **Approval.** CLAUDE.md asks for approval before a real download run. This run was executed on the Cycle 12 Workstream H instruction and limited to the targets listed. Nothing acquired here is ingested, registered in `data/`, or committed. Registration is left to the owner.

## What would unblock the remaining targets (owner decisions, not done here)

1. **archive.org storage nodes.** Allow-list the storage-node hosts, for example with a reviewed subdomain rule for `*.archive.org` on the `archive` source. This unlocks all 10 pinned Gazette facsimiles, which can then be checked against the md5 pins in TARGETS.csv.
2. **egazette.gov.in certificate.** Fetch from a machine whose trust store holds egazette's intermediate certificate, or wait until the site serves a complete chain. Do not disable verification.
3. **Supreme Court official copies.** Fetch Girish Kumar (2026 INSC 1113) and Ram Avtar from `sci.gov.in` by hand. The search there needs a CAPTCHA, so this cannot be automated under the brief.
4. **The 4 SC held copies.** Retrieve them from the owner's own HF dataset, then re-hash them against the declared SHA-256.
5. **The 18 truncated HC files.** The mirror's own copies are truncated. A complete copy can only come from the court:
   - the Delhi High Court portal or eCourts, neither of which is allow-listed;
   - the dataset's upstream issue tracker.
