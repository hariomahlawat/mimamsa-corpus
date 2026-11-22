# Progress

## 2026-11-22 — ACQ-01 acquisition configuration (B1, B2, B6) prepared; nothing downloaded

- Owner authorised B1 (S.R.O. 484 of 1954 and 8 amending S.R.O.s), B2 (1978 Adjustment of Jurisdiction
  Rules and S.O. 4010) and B6 (Army Act amending Acts). This PR only configures them; downloading waits
  for the owner's approval of this PR.
- `sources.archive`: 12 pinned `documents` (archive.org Gazette scans); `allowed_hosts` gains an explicit
  `*.archive.org` entry because archive.org/download answers 302 to per-item data servers
  (dnNNNNNN.{ca,eu}.archive.org, observed with HEAD requests on 2026-11-22). New `official_instruments`
  source: 2 India Code Gazette scans (Acts 13/1975 and 37/1992). Both sources stay `enabled: false`
  (explicit `--source` runs only); `archive` and `official_instruments` are mapped to `crawler/direct.py`.
- `crawler/config.py`: `host_allowed()` supports `*.<domain>` (subdomains only; never the bare domain or a
  look-alike); blocked hosts still take precedence; `check_config` rejects malformed wildcards.
- Evidence: `config-check` OK; `discover` queued 14 URLs with 0 network requests; `dry-run` reports 14 requests
  would be made, 0 refused; 49 offline tests pass (security, acquisition config, foundation).

## 2026-11-22 — Crawler security: compromised AFT Jabalpur host removed (PR, not merged)

- `aftjabalpur.in`, formerly the configured host for AFT Regional Bench Jabalpur, was found to serve
  unrelated betting content. It is removed from `sources.aft.allowed_hosts` and added to `blocked_hosts`
  (with `www.`). The Jabalpur bench keeps no listing address until an official one is found.
- `crawler/config.py`: blocked hosts now also block their subdomains; `check_config` reports any URL in a
  source's config (base_url, listing_urls, ...) whose host is blocked.
- `tests/test_crawler_security.py` (offline) and `.github/workflows/crawler-security-ci.yml` guard against
  reintroduction. The domain was not visited at any point.

## 2026-11-22 — Filter bug fixed; all removed judgments re-checked

- Bug: the keyword "Armed Forces Tribunal" matched only in all-lowercase or all-capitals, not the
  usual title case. Found while checking why Allahabad was thin. Fixed in `pipeline/judgments.py`
  with a test.
- Re-check (`scripts/recheck_removed.py`): all 121,027 removed judgments downloaded again from the
  open-data buckets and filtered again. Recovered 846. Judgments now: 2,871 relevant, 1,341
  borderline, 47 not checked (38 poor scans, 9 damaged PDFs), 120,185 removed.
  Corpus 4,327 documents, 2,755 relations, 0 validation errors. Both stores current (4,039 raw files).
- The text of removed judgments is kept in `state/rejected_text/` (local only, never pushed) so that
  a change to the keywords can be tested without downloading again.
- Why Allahabad is thin (309 kept of 30,658 pre-selected): bucket coverage starts in 2018; most
  files are one-page orders that use none of the brief's ten keywords; 92% were pre-selected only
  on "Union of India".
- OPEN (owner to decide): widen the keyword list. Counted on the removed text: 2,234 removed
  judgments have 2+ wider military terms or 3+ mentions (Delhi 1,150, Allahabad 320, P&H 296,
  J&K 249, SC 219); 6,067 have at least one. Paramilitary-only matches (CRPF, BSF...) excluded.

## 2026-11-22 — OCR of the scanned judgments

- 944 scanned judgments (4,705 pages) read with Tesseract, English only, 300 dpi, then run through the
  military filter: 11 kept (5 relevant, 6 borderline), 895 removed as not military.
- 38 scans (28 Delhi, 10 Punjab and Haryana) were read with mean confidence below 70. A "no keyword"
  result on such text is not trusted: they are kept as `not_checked` for a person to look at, and are
  listed in `reports/ocr_review.md`. Rule added in `pipeline/judgments.py` (`OCR_TRUST`).
- 9 Delhi files are damaged PDFs that cannot be opened; kept as `not_checked`.
- Judgment totals now: 2,331 relevant, 1,035 borderline, 47 not checked, 121,027 removed.
  Corpus 3,481 documents, 0 validation errors. Both stores current (3,197 raw files).
- `python -m pipeline ocr --langs eng` (new option); run script `scripts/ocr_judgments.sh`.
  The statute OCR review list is `reports/ocr_review_statutes.md`.

## 2026-11-21 — Judgment collection from the open-data buckets finished

Supreme Court (1950-2026) and four High Courts (Delhi, Jammu and Kashmir, Punjab and Haryana,
Allahabad; every year the bucket has an index for). 124,446 pre-selected judgments downloaded and
checked with the brief's keywords; only armed-forces judgments are kept.

| Court | relevant | borderline | removed | scans awaiting OCR |
| --- | --- | --- | --- | --- |
| Supreme Court | 240 | 110 | 3,566 | 2 |
| Delhi | 1,198 | 480 | 36,993 | 64 |
| Jammu and Kashmir | 199 | 70 | 5,062 | 53 |
| Punjab and Haryana | 635 | 290 | 44,020 | 834 |
| Allahabad | 54 | 79 | 30,497 | 0 |
| Total | 2,326 | 1,029 | 120,138 | 953 |

- Corpus: 4,376 documents, 2,998 sections, 2,596 relations (1,535 `cites` edges from judgments), 0
  validation errors. Both stores current (4,086 raw files; `raw-data` 2.29 GB of 10 GB).
- 161 downloads failed (missing from the bucket, or not valid PDFs); logged in the crawl state.
- Fixes during the run: extraction saves each record at once (an interrupted run resumes);
  `push_hf.py` uses the fixed dataset name (the account lookup is rate-limited); per-run removal log
  and relevance reports are kept in the data stores, not on `main`.
- Known reporting error: the per-year progress line in `collect.log` often says "downloaded 0".

Next / open
- OCR for the 953 scans, then the relevance check on them (they are neither kept nor removed yet).
- Second look at the 1,029 borderline judgments (single keyword, 1-2 mentions).
- Allahabad: only 133 kept of 30,630; check whether the party-name pre-selection suits this court
  and whether the Lucknow bench sits in a separate bucket folder (not verified).
- AFT judgments: still blocked from this container; waiting for the owner's request log.

## 2026-11-21 — Hugging Face is the central data repository

Decision (owner): the private Hugging Face dataset `hariomahlawat/mimamsa-corpus` holds ALL corpus
data for the application; the GitHub `raw-data` branch is a second copy (raw files capped at 10 GB).
- `scripts/push_hf.py` uploads every raw source folder, meta, sections, text, correspondence,
  relations, manifests and now `schema/`. The statute files that were on GitHub (India Code, official
  copies, 88 raw files), sections and correspondence tables were uploaded today; metadata, text and
  judgments follow at the collection run's next checkpoint.
- Cross-links: `README.md` (main), the dataset card, and `README_RAW_DATA.md` on `raw-data` (added at
  the next checkpoint by `scripts/push_data.py`).
- Collection run: High Courts expanded (Delhi all years, J&K, Punjab & Haryana, Allahabad), parallel
  download for the open-data buckets only, checkpoint to both stores after each court.

## 2026-11-21 — Supreme Court and High Court judgments from the open-data buckets (downloads in progress)

Decision (owner): collect SC and HC judgments from the AWS Open Data buckets; keep ONLY judgments
about the armed forces, not civil or other unrelated ones.

Collector (`crawler/opendata.py`; sources `sci` and `hc` in sources.yaml)
- Reads the buckets' yearly metadata indexes. The indexes have no judgment text, so cases are
  pre-selected by party names (`party_terms`: Union of India, defence bodies, service ranks), and only
  those PDFs are queued. Slices: `discover --source sci --only 2013`, `--source hc --only delhi:2023`.
- Supreme Court, all years 1950-2026: 43,594 index entries, 4,302 pre-selected and queued.
- Delhi High Court, 2023 only: 8,465 index entries, 1,203 pre-selected and queued. Other years and
  courts (Punjab & Haryana, Allahabad, J&K are configured) are not started.
- These buckets may be fetched faster than government sites (0.3 s between requests; flag
  `open_data_bucket`). The 2-second floor still applies to every government host.
- The index column `pdf_exists` is unreliable ("False" on every Delhi 2023 row) and is ignored.

Pipeline
- `pipeline/judgments.py`: a metadata record per judgment from its index row (parties, judges,
  neutral and reported citations, decision date, outcome); stage `relevance` (part of `all`) runs the
  brief's keywords on the text: relevant (2+ keywords or 3+ hits), borderline (1-2 hits of one keyword),
  rejected (none).
- REJECTED judgments are removed from the corpus (metadata, text, raw file). One line each stays in
  `data/excluded_judgments.jsonl` and `reports/relevance.csv`. To re-check after changing the keywords:
  delete that file's entries and re-queue the addresses.
- For kept judgments: `statutes_cited` ("section 69 of the Army Act") and `cites` relations to the
  section records in the corpus.
- Text extraction is now incremental (already-extracted files are skipped).
- 122 tests passing.

First results (Delhi HC 2023, 355 of 1,203 downloaded when checked): 4 relevant, 7 borderline,
344 removed. Download of the rest and of the Supreme Court set was still running when this was written.

AFT, first live try from the owner's PC (Chandigarh): stopped at robots.txt after one request
("disallowed by robots.txt"). Not yet known whether the file forbids the path or could not be read.

## 2026-11-21 — AFT module built (not run live); secondary sources for judgments checked

AFT module (`crawler/aft.py`, `python -m crawler discover --source aft --only <bench>`)
- NOT run against the live sites: they reset connections from the cloud container. Built from, and
  tested on, excerpts of listing pages saved from the live sites in 2023 (MIT-licensed repository
  github.com/L-Bellingcat/army-tribunals; excerpts in tests/fixtures/aft/). The sites may have changed.
- Two listing styles: `joodb` (Principal Bench, Chandigarh on aftdelhi.nic.in: labelled rows + ViewPDF
  link; asks for all results with limit=0 and pages on if the site returns fewer than its own
  "Results a - b of c") and `table` (Kolkata, Lucknow, Jabalpur: tables of PDF links; Kolkata's
  page:N links are followed).
- Configured with listing addresses: Principal Bench, Chandigarh, Kolkata. Layout known but listing
  address missing: Lucknow, Jabalpur. Nothing known: Guwahati, Chennai, Kochi, Mumbai, Jaipur, Srinagar.
- Reads listing pages only; queues each PDF link with the row's fields (case number, court, year,
  month, members). Heavy source: live runs only 20:00-08:00 IST. `aft` stays disabled in sources.yaml.
- In 2023 Chandigarh listed 8,685 judgments on one page. Kolkata's site needed certificate checks
  switched off in that project's scraper; this crawler will not do that.
- 116 tests passing.

Secondary sources for Supreme Court and High Court judgments (checked, nothing collected)
- AWS Open Data, bucket `indian-supreme-court-judgments`: reachable from the container. Taken from the
  Supreme Court's own e-SCR portal; CC-BY-4.0; per-year metadata + PDFs. The 2013 index has 854
  reported judgments, including Dharamvir Singh v. Union of India (2013 INSC 408, decided 02-07-2013).
  The index has no judgment text, so keyword filtering needs the PDFs.
- AWS Open Data, bucket `indian-high-court-judgments`: reachable. From the eCourts judgments portal;
  25 High Courts, about 17.8 million judgments, about 1.25 TiB; CC-BY-4.0.
- No bulk dataset of AFT judgments was found. Indian Kanoon, Casemine and vLex carry AFT judgments
  but are commercial or restricted, which the brief excludes.
- DECISION NEEDED: the brief says official sites only. These two buckets are a third party's copy
  of official court data, not the courts' own sites.

## 2026-11-21 — Better CrPC text and the correspondence tables

Corpus now: 68 documents, 2,998 section records, 1,061 relations, 1,194 correspondence rows; all validate.

Sources tried
- Legislative Department (lddashboard.legislative.gov.in): connection reset from the cloud container.
- BPR&D (bprd.nic.in): its TLS certificate has expired; not bypassed.
- NCRB (cytrain.ncrb.gov.in): connection reset.
- Reachable official copies used instead (new source `official_copies`, hand-listed documents only):
  CRPF site (Ministry of Home Affairs) for the CrPC; Kerala Prisons for the three BPR&D tables.
  The three unreachable sites are on the allow-list for a run from a machine in India.

CrPC
- `act-crpc-1973-consolidated`: consolidated text, 226 pages, amendment footnotes. Latest amending Act
  mentioned is of 2014, so it is NOT the text as it stood at repeal in 2024.
- `act-crpc-1973` sections are now cut from that copy: 532 of 532 in its table, 224 amendment notes,
  37 chapters. Each section names the copy in `text_source_doc_id`.
- Splitter improvements made for this file: type sizes judged per page; footnote blocks set in body
  size recognised by wording; a non-bold section start accepted when it is exactly the next one in
  the table. IPC stays 574/574 (457 notes), Evidence Act 185/185 (145 notes).
- Known residue: 6 footnote lines across the three codes are still inside section text.

Correspondence tables (`python -m pipeline correspondence`, part of `all`)
- BPR&D "Correspondence Table and Comparison Summary" PDFs: BNSS<->CrPC 487 rows, BNS<->IPC 525,
  BSA<->Evidence Act 182. Output `data/correspondence/<key>.jsonl` (schema/correspondence.schema.json):
  cells as printed, section numbers read from them, the table's summary of the change.
- Cross-check: every new-code and old-code section the tables name exists in the corpus section
  records, except CrPC "105I". 24 rows have no readable old section (see the report).
- Rows are `extracted`; a person should verify before the app relies on a mapping.

Curated fields
- Documents listed by hand in sources.yaml carry provenance "llm" for the fields written there
  (title, authority) until a person confirms them.

## 2026-11-21 — OCR, the three repealed codes, and sections cut from PDFs

Corpus now: 64 documents, 2,466 section records, 738 relations; 100% validate. 84 raw files.

OCR (`python -m pipeline ocr`; Tesseract 5.3.4 installed in the cloud container, hin+eng)
- 4 documents, 526 pages: the Hindi texts of BNS (145 pp, mean confidence 92.7), BNSS (319 pp, 90.8),
  BSA (61 pp, 91.6) and the bilingual AFT Guwahati notification (1 p, 86.2). No page fell below the
  review threshold of 70, so `reports/ocr_review.md` lists none.
- Two passes per page: Hindi-first reads Hindi words best but drops the digit 1 ("2010" -> "200");
  English-first reads numbers correctly. Number-bearing words are taken from the English-first pass.
  Residual errors remain (seen: "31st" read as "318"). OCR text is for search, not for quoting.
- Resumable: pages are cached in data/ocr/ (not in git).

IPC 1860, CrPC 1973, Evidence Act 1872: found on India Code in its "Repeal Acts" collection
- One PDF each, no section records at the source. Record titles read "... (Rep., Act 45/46/47 of 2023)".
- Recorded as `repealed`; `repeals` edges BNS->IPC, BNSS->CrPC, BSA->Evidence Act built from those
  titles (confidence `extracted`; need human verification).
- No enactment dates on these records (year only), so issue_date is null.

Sections cut from PDFs (`python -m pipeline split`, part of `all`)
- For Acts without section records at the source. Each section start must match the Act's own table of
  sections, in order; nothing is written below 98% coverage.
- IPC: 574 of 574 sections, 422 amendment notes, 23 chapters. Evidence Act: 185 of 185, 81 notes.
  Chapters ARE recorded for these (taken from the PDF).
- CrPC: NOT split. The file is a scan of the original 1974 print with a poor text layer (e.g.
  "Cfilef Judicial Ma2is•trate"), no amendments shown (no "Ins. by" notes; s.41A absent), and it fails
  the layout check. It is in the corpus as a whole document only. Needs a better source text.
- Found while checking: 18 places where the Act's table of sections and its body print a heading
  differently (source typos such as "miscarraige"), and IPC s.17 printed without its full stop.
  Listed in `reports/phase2_report.md`; kept as printed.
- A few sections have no separate heading where the source prints none in the usual form
  (IPC 216B; Evidence Act 4, 86).

## 2026-11-21 — Phase 2 pipeline built and run on the India Code files (awaiting review)

Commands: `python -m pipeline records | extract | validate | report | all` (each re-runnable alone).
Full results: `reports/phase2_report.md`.

Results on the real data
- 61 document records, 1,707 section records, 232 relations; 100% validate against the schemas
  (now v0.2.0; see below). `data/manifest.csv` written.
- Sections come from India Code's own section records (text + footnotes), not from cutting up PDFs.
  Section status: 9 omitted/repealed, ~130 amended, the rest in force. 191 amendment notes read by
  rules; each becomes an `amended_by` edge with the note as evidence (none resolved to a document yet).
- Brief's known cases: Army Act ss.75, 76, 127 are `omitted` with the 1992 Act as the reason.
- Text: 55 documents extracted cleanly, 2 flagged suspect (very short), 4 need OCR (the second files of
  BNS/BNSS/BSA, which are scans, and one AFT notification). No text is kept for those four.
- The "IndiaCode" download watermark is removed by dropping slanted text (41,670 characters dropped).
- Dates the source prints wrongly or with 2-digit years (e.g. "6-9-192", "16-12-74") are kept as
  printed in `effective_date_raw` and NOT turned into dates.

Needs a human look
- "Regulations for the Air Force (Reprinted Edition 2000)" is printed "For Official Use Only" on its
  first page, although India Code publishes it openly. Recorded in `access_marking`; decide whether
  it belongs in the corpus.
- All non-`cites` relations are `extracted`, not `human_verified`.

Schema v0.2.0 (changes from 0.1.0)
- document: new doc_types `schedule` and `executive_order`; new fields `language`, `parent_doc_id`,
  `original_filename`, `source_record`, `text_path`, `text_quality`, `needs_ocr`, `pages_without_text`.
- section: `notes`, `source_record`; amendment entries gain `origin` and `effective_date_raw`,
  and `by_ref_raw` may be null.

Not done
- OCR stage (4 documents waiting; Tesseract is a system package, not installed; Prism reuse is still
  an open question).
- Golden-set coverage report: the golden test set has not been given to the pipeline.
- Chapters on sections (the source records carry none).
- `supersedes` edges BNS->IPC etc.: the repealed central codes are not in the corpus.

## 2026-11-21 20:06 IST — Supreme Court first check: judgment search needs a CAPTCHA (stopped)

- www.sci.gov.in: robots.txt served (only /wp-admin/ disallowed) and obeyed; home page loads (200).
- https://www.sci.gov.in/judgements-case-no/ loads, but its search form carries a CAPTCHA image
  (the same form family covers Case Number, Diary No, Judge, Judgment Date, Free Text and
  Neutral Citation tabs; only the Case Number tab was opened). Per the brief: no CAPTCHA bypassing,
  stop and report. 4 requests in total, no documents downloaded. `sci` stays disabled.
- Options to decide: another official route for Supreme Court judgments that needs no CAPTCHA
  (to be identified and checked), or a hand-made list of judgment PDF addresses fed to the crawler.

## 2026-11-21 — India Code download run (approved): all 75 queued files fetched

- Run 20261121T143022Z-0c8b86: 76 requests, 74 new files, 1 duplicate (same bytes under two
  addresses, kept once with an alias), 0 failed, 0 skipped. 240 MB in this run.
- India Code total now: 82 documents queued and fetched, 81 files on disk, 246 MB, for 8 Acts:
  Army, Air Force, Navy, AFT, Army & Air Force (Disposal of Private Property), BNS, BNSS, BSA.
  Per Act: English text (tagged with the doc_id), a second file (Hindi, by file name), every
  linked rule / regulation / schedule / notification / order / amendment-Act file, and the JSON pages
  of section records.
- 57 PDFs differ from the MD5 in the site's listing (expected: download watermark).
- Largest files: BNSS second file 76.5 MB, AFT Procedure Rules 2008 46.8 MB, BNS second file 41 MB.
  The second files of BNS/BNSS/BSA do not follow the a…/h… naming, so their language is unconfirmed.
- Raw files are NOT in git and live only in this cloud container (data/raw/indiacode/). The crawl
  state (state/crawl.sqlite) is also local. Re-running `discover` + `fetch` on another machine
  reproduces them.

## 2026-11-21 — India Code works end to end against the live site (Phase 1 step 3 done for real)

What was found
- India Code MOVED: www.indiacode.nic.in only shows a migration notice; the site is now
  https://indiacode.gov.in, a DSpace 9 application built in the browser from a public REST API at
  /server/api. That is why robots.txt and the guessed search page hung on the old address.
- robots.txt on the new site answers HTTP 500 (generic error page). The India Code exception was
  extended to cover that (`robots_5xx: allow`, India Code only, reason in sources.yaml).
- The API gives structured records: one ACT record with its PDFs, one SECTION record per section
  (text + amendment footnotes), and RULE / REGULATION / SCHEDULE / NOTIFICATION records, all linked by
  `dc.identifier.act_id`.

What was built
- `crawler/indiacode.py` rewritten for the API (search -> Act record -> files -> all linked records).
  Old page-scraping code and the synthetic HTML fixtures are gone; tests now replay REAL recorded API
  answers (`tests/fixtures/indiacode_api/`). 74 tests passing.
- Pages of linked records are saved as raw documents (they hold the section text).
- State copies of central Acts share the title: the CENTRAL copy is chosen; otherwise unresolved.

Army Act 1950: downloaded (7 files, 6.3 MB, in data/raw/indiacode/, not in git)
- Act text a1950-46.pdf (51 pages, "as on the 21st July, 2025"), Hindi H195046.pdf, Army Rules 1954,
  the Schedule, and 3 JSON pages holding all 198 section records.
- Checked: ss.75, 76 and 127 are marked "Omitted by the Army (Amendment) Act, 1992 (37 of 1992)".
  Note the source itself has a typo in the date on ss.75-76 ("w.e.f. 6-9-192").
- The site stamps an "India Code" watermark on PDFs at download, so the bytes differ from the MD5 in
  its own listing (counted, not treated as damage). The watermark letters show up in extracted
  text; text extraction must strip them, or use the section records / the site's TEXT files instead.

Discovery for all India Code targets (listings only, nothing else downloaded yet; 75 files queued)
- Resolved: Army Act, Air Force Act, Navy Act, AFT Act (13 rules, 16 notifications, 3 amendment
  Acts, 1 order), Army & Air Force (Disposal of Private Property) Act, BNS, BNSS, BSA.
- NOT resolved: IPC 1860, CrPC 1973, Evidence Act 1872. India Code now lists only STATE copies of
  these (Chhattisgarh, Rajasthan, ...); no CENTRAL copy was found by title. Needs a decision:
  another source for the repealed central texts, or pick a state copy knowingly.
- NOT found: Regulations for the Army 1987 (no record on India Code).
- Gap: the Air Force Rules 1969 record exists but has no file attached.

Next
- Review, then run `fetch` for the remaining 75 queued India Code files (Phase 2).
- Phase 2 pipeline: metadata records + section records from the saved JSON (no PDF parsing needed
  for section splitting), validated against the schemas.

## 2026-11-21 — First live checks (from the cloud container, US address)

Setup
- Contact email set in `defaults.user_agent`. New `probe` command: reads robots.txt and a few listing
  pages through the polite client, lists links, downloads no documents.

Results
- mod.gov.in: BLOCKED. robots.txt and the home page both answered HTTP 403 to the crawler's
  User-Agent (2 requests, then stopped). An earlier plain reachability check with a different
  User-Agent got 200 for robots.txt, so the block may be on the User-Agent wording or on the address.
  Not retried. Needs a decision.
  Follow-up the same day: User-Agent reworded without "Bot"/"crawler" (now `Mimamsa-Corpus/0.1 (...)`),
  retried once: still 403 ("Access Denied" page from the site's Akamai front end), from both httpx and
  curl. The earlier check string `Mimamsa-corpus-setup/0.1 (reachability check)` still gets 200 from the
  same address, so the filter reacts to something in the User-Agent text (untested which part; the
  contact email is the main difference). Stopped there; MoD stays blocked pending a decision.
  DECISION (2026-11-21): skip MoD for now. `sources.mod.enabled: false`. Army Rules 1954, Air Force
  Rules 1969 and AFT (Procedure) Rules 2008 are to come from India Code's subordinate-legislation
  listings; `expect_subordinate` on those targets makes discovery warn if one is not listed.
  Still without a source: Regulations for the Army 1987 (India Code search first) and any MoD-only manuals.
- From the user's PC in India (same day): mod.gov.in AND indiacode.nic.in both answer 403 to robots.txt
  and the first page. So the block follows the identification string, not the address.
  Change: contact email moved from User-Agent to the HTTP `From` header (`defaults.contact_email`);
  User-Agent stays descriptive, no browser impersonation. Awaiting one retest from the PC.
  If still 403: stop; options are asking NIC how automated access should be done, or manual
  browser downloads fed in as `manual_upload`.
- Retest from the PC with the `From` header: no more 403 on either site, so the email in the
  User-Agent was the trigger.
  - indiacode.nic.in: robots.txt never answers (times out in the crawler and in a desktop browser).
    DECISION: per-source exception `robots_unreachable: allow` for indiacode only, reason recorded in
    sources.yaml. Awaiting retest of `discover`.
  - mod.gov.in: home page now 200, but 8277 bytes with no links and no title: either a JavaScript-only
    page or a bot-check page. Unknown until the recorded file is looked at. MoD stays disabled.
- archive.org: OK. robots.txt allows the search API. Title searches found the Indian Army Act 1911,
  the Manual of Indian Military Law (1911 and 1937) and British Manual of Military Law scans;
  identifiers recorded under `sources.archive.candidates` (unreviewed).
- sci.gov.in: not run; heavy source, only allowed 20:00-08:00 IST.
- Not reachable from this container: aftdelhi.nic.in (connection reset), egazette.gov.in (certificate
  cannot be verified), indiacode.nic.in (home page loads, robots.txt hangs, so the crawler refuses).

## 2026-11-21 — Phase 1, step 3 (built against SYNTHETIC pages; NOT verified on the live site)

Done
- `crawler/http.py`: PoliteClient, the only HTTP path. Allow-list on every hop (redirects included),
  robots.txt (unreachable robots = disallow; Crawl-delay honoured), per-host delay, size cap, audit of
  every request, stop on 401/403/login redirects, refuses live requests while the contact email is the
  placeholder. Replay mode (`--replay DIR`) serves saved pages; `--record DIR` saves live pages.
- `crawler/indiacode.py`: search -> Act page -> queue Act PDF + subordinate legislation PDFs.
  Resolves a target only on exactly one exact title match; otherwise reports candidates.
- `crawler/fetch.py` + `fetch --yes-download`: downloads queued documents to
  `data/raw/<source>/<yyyy>/<sha256>.<ext>`; duplicates become aliases; non-PDF answers for PDF links fail.
- CLI: `discover`, `fetch`; replay runs use separate state (`state/replay.sqlite`, `state/replay_data/`).
- Crawl-state schema v2 (`urls.meta`: listing title, category, printed date, parent doc).
- 65 tests passing.

Unverified (needs the live site or real saved pages)
- India Code page layout, link shapes (`/handle/`, `/bitstream/`, `ViewFileUploaded`) and the
  `search_url_template` come from memory. `tests/fixtures/indiacode/` is hand-written, with invented
  handles, dates and robots rules.
- First real check: `python -m crawler discover --source indiacode --only act-army-1950 --record <dir>`
  (listing pages only, 3 requests), then review the output before any `fetch`.

Open points
- Subordinate documents have no doc_id or year at download time (stored under `/0000/`); the metadata
  stage assigns them.
- Section pages (`show-data` links) are counted but not queued; decide in Phase 2 whether section
  splitting uses them or the PDF.
- Listing pages are not saved to data/raw (only their hash is kept).

## 2026-11-21 — Phase 1, step 2 (approved)

Done
- `crawler/state.py`: SQLite crawl state (`state/crawl.sqlite`, WAL, schema v1): URL queue with
  queued/fetched/failed/skipped, attempts + exponential backoff with jitter (give up after max_retries),
  ETag/Last-Modified, sha256 file registry with duplicate-URL aliases, runs table, request audit table.
  Every change commits immediately, so a killed crawler resumes where it stopped.
- `crawler/audit.py`: console + rotating `state/logs/crawl.log`; every request goes to
  `state/logs/requests-YYYYMMDD.jsonl` and the `requests` table.
- `crawler/config.py`: loads and checks sources.yaml (politeness floor, robots on, no off-site links,
  exact-host allow-list, blocked hosts, doc_id format, quiet hours in IST for heavy sources).
- `crawler/plan.py` + `python -m crawler dry-run`: per-source plan from config + crawl state, written to
  `reports/dry_run_<run_id>.{md,json}`. Makes no network requests (tested). Commands: `config-check`,
  `init-db`, `status`, `dry-run [--source S] [--all] [--json]`.
- 40 tests passing.

Notes
- Targets show "discover: needs source module" until step 3 adds the India Code module, which
  will plug in via `plan.register_planner("indiacode")`.
- The polite HTTP client (robots.txt, per-host rate limit, retries, User-Agent guard) is built in step 3
  with its first user, the India Code fetcher.

## 2026-11-21 — Phase 1, step 1 (approved)

Done
- Project skeleton per CLAUDE.md layout; CLAUDE.md = brief exported from the Claude Docs doc.
- `schema/document.schema.json`, `section.schema.json`, `relation.schema.json` (JSON Schema 2020-12, v0.1.0).
- `pipeline/schemas.py` loader + `tests/test_schemas.py` (18 tests passing).
- `config/sources.yaml` with Phase 2 seeds (India Code, MoD) enabled; later phases stubbed and disabled.
- `.venv` + pinned `requirements.txt` (from `requirements.in`).

Not done / blocked
- Seed hosts (indiacode.nic.in, mod.gov.in, aftdelhi.nic.in, sci.gov.in, egazette.gov.in, archive.org,
  delhihighcourt.nic.in) are blocked by this cloud environment's network policy (proxy 403).
  Nothing in sources.yaml has been checked against the live sites; entries are marked `verify: true`.
- User-Agent contact email is a placeholder; crawler will refuse to start until it is set.

Next (after approval)
- Step 3: India Code fetcher for the Army Act 1950 only, dry run.

## 2026-11-22: ACQ-02 crawler configuration (PROPOSED; not authorised for download)
- New source `archive_acq02` (disabled), separate from ACQ-01 (`archive`/`official_instruments`, PR #8): 16 Gazette of India issues found by the Army Rules amendment search, with `expected_sha256`/`expected_md5`/`expected_bytes` from the pre-verification in `legal_knowledge/audit_work/ACQ-02` (PR #16).
- `issue_date` = notification date; `gazette_publication_date` = Gazette date; no effective date asserted.
- Tests: `tests/test_acquisition_config_acq02.py` pins the 16 documents and proves the ACQ-01 list unchanged and non-overlapping. config-check OK; discover makes 0 requests; dry-run lists 16. Evidence: `legal_knowledge/audit_work/ACQ-02/config_pr_evidence/`.
- Next (needs owner approval of this PR and of a download run): fetch with `--yes-download`, compare against expected hashes, re-run page-image checks on record copies.
