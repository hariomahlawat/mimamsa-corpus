# C13 Workstream A7: targeted acquisition and crawler PR review

Branch `claude/c13-a7-acquisition`, run on 2026-11-25. Staging baseline `a4c0c382`. HF parent `844383f5`: that is
`3864faf3` plus a sibling C13 metadata overlay committed at 10:17Z, which adds no source copy.

**Nothing here closes, merges or comments on a PR. The live `config/sources.yaml` and `crawler/` are unchanged.**
All candidate outputs are `AUTOMATED_CANDIDATE_NOT_VERIFIED`. Byte and pin checks are not legal authentication.

## Deliverables

| File | Content |
|---|---|
| `PR_REVIEW_C13.md` | Part 1: PRs #7, #8, #9, #17 and #23 (dependency order, security vs staging, manifest accuracy, conflicts, recommendations) |
| `pr_review/PR_PIN_CHECK_C13.csv`, `PR_PIN_CHECK_SUMMARY.txt`, `CORPUS_BYTE_INDEX.csv.gz` | The 72 PR pins against the corpus |
| `proposed/crawler_revision/0001-0003*.patch` | Proposed revision on top of `a4c0c382`. 0001 and 0002 are PR #7 replayed onto staging. 0003 adds exact-host allow-listing (no wildcards), item-scoped `redirect_scopes`, pinned `ca_extra_pem` with strict chains, a `From` header only when `MIMAMSA_CONTACT_EMAIL` is set, PR #17 fetch-time integrity, and tests |
| `AUTHORISED_SCOPE_C13.md`, `proposed/sources.yaml.proposed`, `proposed/sources.yaml.diff` | Part 2 allow-list proposal (not applied) |
| `allowlist/PROBE_RESULTS.csv`, `PROBE_REQUEST_LOG.csv`, `ARCHIVE_ITEM_NODES.csv`, `ARCHIVE_REDIRECT_SCOPES.csv`, `MANUAL_TLS_REQUESTS.csv` | Probe evidence |
| `allowlist/EGAZETTE_TLS_C13.md`, `egazette_intermediates.pem`, `egazette_served_leaf_2026-11-25.pem`, `aia_*.der` | egazette TLS root cause and fix |
| `acquisition/TARGETS_C13.csv` | The plan (126 targets), built without network access |
| `acquisition/REQUEST_LOG_C13.csv` | Every acquisition request (134, robots.txt included): time, URL, host, status, bytes, ms, content type, ETag, Last-Modified, error |
| `acquisition/ACQUISITION_MANIFEST_C13.csv` | One row per target: URLs, final URL, robots, HTTP chain, ETag and Last-Modified, retrieved_at, sha256, md5, bytes, original filename, integrity, completeness, access marking scan, access eligibility, relevance keywords, corpus duplicate, attempts |
| `acquisition/fetch_results_c13.json` | Raw results (the run is resumable) |
| `acquisition/MARKING_REVIEW_C13.csv` | 3 marking-term hits checked in context. All are "Annual Confidential Report" body text, not markings (agent check, not a human check) |
| `acquisition/HF_COMMITS_C13.csv`, `HF_VERIFY_C13.csv`, `HF_PACKAGE_SHA256SUMS` | HF commit and re-download verification |
| `tools/` | `corpus_md5_index.py`, `pr_pin_check.py`, `allowlist_probe.py`, `a7net.py` (shared policy), `acquire_c13.py`, `build_scope_proposal.py`, `preserve_hf_c13.py` |
| `SHA256SUMS` | Checksums of every file in this folder |

### Checks (all pass at the branch head)

```
P=/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/venv/bin/python
$P -I tools/corpus_md5_index.py --check      # needs /home/user/c7 and the 5524c3d9 mirror
$P -I tools/pr_pin_check.py --check
$P -I tools/allowlist_probe.py --check
$P -I tools/build_scope_proposal.py --check
$P -I tools/acquire_c13.py --check           # re-hashes the 63 stored files in the session store
$P -I tools/preserve_hf_c13.py --check
cd legal_knowledge/audit_work/C13-A7-ACQUISITION && sha256sum -c SHA256SUMS
```

## Part 3 results (measured)

| Group | Targets | Acquired | Not acquired (reason) |
|---|---|---|---|
| G1: 10 C12 LOCATED_NOT_ACQUIRED Gazette instruments, from egazette.gov.in | 10 | **10**. 8 match the archive.org md5/size pin. 2 (`236757`, `241268` of 2022) differ from the archive.org pin. Each is the egazette file at its Gazette-ID URL, and the printed Gazette ID `CG-DL-E-…-236757/-241268` was found in its text | – |
| G2: archive.org pins from PRs #8 and #23 not held in the corpus (38) | 38 | **7**, from egazette.gov.in, byte-identical to the PR pin | 31: derived egazette URL 404, and archive.org redirects to a storage node that is not allow-listed (redirect recorded, not followed) |
| G3: Ram Avtar (C.A. 418/2012, 10-12-2014); Girish Kumar clarification (2026 INSC 1113) | 2 | 0 | Not in the allow-listed SC open-data bucket: no Ram Avtar row in its 2014 index (795 rows); its 2026 index (261 rows) has only 2026 INSC 149. The official host is not allow-listed and its search has a CAPTCHA |
| G4: complete versions of the 19 truncated HC files | 19 | 0 | The HC index (Delhi 2025/2026, `dhcdb`) has no other file for any of the 19 CNRs. C12 already showed that the recorded URLs serve the same truncated bytes. No allow-listed alternative exists |
| G5: high-value first-tier titles (the 46 that met the C12 party and court tests beyond the C12 cap) | 46 | **46**, every sha256 equal to the crawler-logged value | – |
| G6: DESW items (5), SCI official copies (2), S.R.O. 258/2002, the r.15 "[or Military Secretary]" instrument, AF/Navy rules, A4/A6 requests | 11 | 0 | 7 host not allow-listed; 2 no locator; 1 no pinned URL; A4/A6: no `ACQUISITION_REQUESTS_*.csv` exists (A4 branch has no commits; A6 has none) |
| **Total** | **126** | **63** (61 pin-verified, 2 official copies differing from a third-party pin) | **63** |

Completeness of the 63 files:
- 62 are complete: `%%EOF` at the end, they open, and every page has text.
- 1 (`acq03-020-b4`, S.R.O. 2(E)/1955) is structurally complete but has a text layer on only 1 of 2 pages.

None of the 63 sha256 values is in the corpus. None is the FOUO Air Force Regulations copy.

### Observations for other workstreams (documentary, not conclusions)

- **G1 `236757` and `241268` (2022).** C5 listed them as "possible Army Rules amendment (subject unconfirmed)". Their printed text is notifications under the **Navy Act, 1957** (S.R.O. 9(E) of 23-06-2022 under s.9(2); S.R.O. 24(E) of 21-12-2022). Neither text contains the phrase "Army Rules". Referred to A3; no state was changed.
- **G5 relevance.** None of the 46 judgments contains a brief keyword (Army Act, AFT, court martial, disability pension, …) in its first 6 pages. This matches the crawler's original rejection reason ("no military keyword in the text"). They are preserved for reproducibility, and their relevance is **pending A1**. They are not ingested.

## HF preservation

- **Commit `9e3cf9868a5d553cd6218ed5ac51c383560bbf0b`** (parent `844383f55d3b8e61068c3c786a69e8160061cc32`, pinned with `parent_commit`).
- 127 files under `legal_knowledge/preservation/c13_a7_acquired/` (C12 preservation layout):
  - 63 PDFs, each at `<sha[:2]>/<sha>/<original filename>`;
  - 63 `.meta.json` sidecars (URL, HTTP metadata, hashes, original filename, integrity, access eligibility, `ingestion_state: NOT_INGESTED_PENDING_A1_RELEVANCE_AND_DUPLICATE_GATE`);
  - `PACKAGE_SHA256SUMS`.
- Before the commit:
  - a path-collision check found none;
  - `scripts/hf_protect.py::assert_additive` passed.
- After the commit, all 127 files were re-downloaded at `9e3cf986` and hashed: **127/127 equal** (`HF_VERIFY_C13.csv`).
- Distinct source copies on HF: 4,121 + 63 = **4,184**. The 63 are preserved but not ingested into `data/`.
- Nothing was deleted or overwritten, and visibility was not changed.

## Policy compliance

- **Hosts.** Acquisition requests went only to hosts in staging `config/sources.yaml` `allowed_hosts`: `egazette.gov.in`, `archive.org`, and the SC and HC open-data buckets. `tools/a7net.py` checks every URL and every redirect hop before sending.
- **Never contacted.** `aftjabalpur.in` (and subdomains), `blocked_hosts` and commercial databases: 0 log rows.
- **Probes.** The Part 2 probes of non-allow-listed candidates (SCI, DESW, archive.org storage nodes) requested only robots.txt and entry pages, as the brief's validation requires. No document was downloaded from them.
- **robots.txt.** It was read once per origin, before any other request there. A 4xx answer means no robots file (RFC 9309); a 5xx or an unreachable robots.txt means disallow.
- **Rate.** At least 2 s per host, sequential requests. The buckets' 0.3 s allowance was not used.
- **No login, CAPTCHA or search automation.**
- **TLS.** Verification was always on. For egazette.gov.in, the two pinned public intermediates were used with strict chain building to ISRG Root X1 (disclosed in `EGAZETTE_TLS_C13.md`; the coordinator may require acceptance of that mechanism first).
- **Headers.** No `From` header was sent: `MIMAMSA_CONTACT_EMAIL` was unset. The User-Agent was the config string.
- **Storage.** Downloads are stored outside the worktree at `scratchpad/c13_a7_acquired/<sha[:2]>/<sha>/<filename>`, written atomically and never overwritten.

## Not done / shortfalls

- The 31 archive.org Gazette issues remain un-acquired until a `redirect_scopes` decision. They include S.R.O. 348/1960 and 404/1960, which A5 and A3 need.
- No source was found for:
  - S.R.O. 258/2002;
  - the r.15 instrument;
  - Ram Avtar;
  - the Girish Kumar clarification;
  - complete versions of the 19 truncated HC files.
- No complete copy was sought in the HC bucket's tar archives (several GB per bench). A truncated object is likely to be truncated there too, but this was not verified.
- A1 relevance states do not exist yet (`claude/c13-a1-ocr` has no commits), so nothing was ingested.
- The `test_legal_audit_retrospective_deemed.py` collection error is pre-existing on staging and not addressed.
