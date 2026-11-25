# B1 prototype: research vertical slice (Cycle 13, Track B)

- **Branch:** `claude/c13-b1`, based on integration `db801617`. Not pushed.
- **Status:** working prototype for independent review. Nothing here is legally verified. AUTH-LEDGER stays at version 0. No generative or agentic AI.
- **Host:** ASP.NET Core 10 on Kestrel (ADR-0005 P1 recommendation). It runs as a Windows Service through `UseWindowsService`, or as a console process. It is bound to loopback only.

Status words follow PR #54 README §4: **Passed, Failed, Blocked, Not implemented, Not executed, Not applicable**. Everything below was **measured** on the shared 4-vCPU Linux scratch VM, unless it is marked otherwise.

## 1. What was built

| Area | Implementation | Main files |
| --- | --- | --- |
| Data path | The importer now **materializes** verified records, verified derivative text and signed research aids into the generation directory, before the atomic rename. UNRESOLVED items are never written. The service loads **only** the ACTIVE generation. At start-up it re-hashes every derivative text and every vault original, and leaves out anything that fails, counted by reason code. | `app/importer/mimamsa_importer/importer.py` (`_materialize`, `_research_files`; 4 new tests), `app/b1/src/Mimamsa.Core/Generation/GenerationStore.cs` |
| Sample bundle | **290 public documents**: 27 Acts, 15 Rules, 5 Regulations, 16 notifications, 1 order, 3 other, and 223 judgments (80 SC; 36 each from four High Courts, minus 1 dropped). They total 11,352 pages and 423 MB, taken from HF `hariomahlawat/mimamsa-corpus` at `3864faf3`. **RM-001 is excluded before download**, and the register is re-checked on every record, edge and research line. The bundle is signed with a disposable in-memory development key; no production key exists. Import result: 290/290 documents, 290/290 derivatives and 3,262/3,262 candidates verified and activated. The candidates are 503 A2 outcomes and 2,759 A5 graph edges. There are also 488 A4 provision versions and 1,221 lexicon abbreviations as research aids. **Corpus bytes are not in git.** | `app/b1/build/build_sample.py`, `app/b1/sample/SAMPLE_MANIFEST.json` (hashes, ids, counts) |
| Search | An in-process positional BM25 over 38,445 verified passages, plus three further layers. **Exact-identifier layer:** sections and rules, neutral and reported citations, case numbers from metadata and page-1 covers, pinned above ranked results. **Abbreviation expansion:** Army lexicon v1.0 plus the P2 supplement; uppercase codes only; every meaning searched is listed. **Professional syntax:** `exact:`, phrases, AND/OR/NOT, `NEAR/n`, prefix\*, and the fields title/party/judge/court/bench/case/citation/section/act/type/date/year. Filters cover type, court, year and corpus status, with per-facet counts. Snippets come from verified text, with highlight ranges and page and passage anchors. A malformed query returns its error position and runs as plain words only after the user confirms. | `app/b1/src/Mimamsa.Core/Search/*` |
| Protected original | The R2-N01 path is **refactored, not copied**: CreditLedger, the writer-priority ServingState fence, strict single bounded ranges, and settlement as ACCEPTED, RELEASED or UNCERTAIN. Durable withdrawal is a compare-and-set on the policy witness. Authentication uses the B1 session cookie. **Review N1:** finished but undrained connections that served a copy are reset at FENCE. **Review N2:** the TCP-state probe matches the full 4-tuple. PDF.js 6.5.438 is vendored offline with eval disabled, no URL is given to it, and it uses a range transport only. The slot and per-session cap are taken before staging (F11). A single instance is enforced by an advisory lock (F10). | `Mimamsa.Core/Delivery/*`, `Mimamsa.Web/ProtectedDelivery.cs`, `DrainProbe.cs`, `wwwroot/assets/js/viewer.js`, `app/b1/web/vendor.mjs` |
| Citations (ASR-E06) | The legal citation is a port of `citation.py` and produces the same test vector. The internal reference and permalink are separate. `/cite/{release}/{doc}/{sha12}/{page}` opens the **exact cited copy and page**. An earlier, held edition opens with the notice "This copy is not the current edition in the library." and a separate **Open current edition** action; the header then names the cited copy. Withdrawn, restricted and not-held copies all give the single notice "The cited copy is not available in this installation." | `Mimamsa.Core/Citation/Citations.cs`, `pages.js` |
| Provenance and status | Every result group shows source host, copy SHA-12, retrieval date and corpus status (labelled display-only). Every document shows the **seven axes** in fixed order with their basis, a Provenance panel (full SHA-256, HF repo, revision and path, release, generation, pipeline) and "Checked by this installation". Candidates (A2 outcomes, A5 edges, A4 temporal versions) appear only as **Candidate (automated, not verified)** with `AUTOMATED_CANDIDATE_NOT_VERIFIED`, measured figures or "not evaluated", and their restriction. Absence notices appear on every empty related, cited or graph surface. | `Api.cs` (`DocumentDto`), `research.js` |
| Service | Local accounts (PBKDF2-SHA256 at 600k iterations), server-side sessions (30 min idle, 12 h absolute), lockout after 5 failures with a generic error, CSRF tokens on every POST, and server-side Admin role checks. Logout sends `Clear-Site-Data`. CSP is `default-src 'self'` with no inline script or style. Every API and HTML response is `no-store`. Logs are **content-free**: method, route template, status and time only, with framework request logging suppressed. Accounts are created through `Mimamsa.Web --add-user <name> <role>`, with the password on stdin. Test accounts and hooks exist only in test mode. | `Mimamsa.Core/Identity/Identity.cs`, `Mimamsa.Web/Program.cs`, `Api.cs` |
| UI | Vanilla ES modules with no framework and no build step. `tokens.css` is **generated from `app/design/tokens/design-tokens.json`** and a CI check fails on drift. The IA covers banner, top bar, workspace switcher, persistent search, facet rail, results, document tabs, context pane and footer. Panes are resizable by pointer and keyboard. Practitioner and Commander views and light and dark themes are available. The full **keymap** is implemented; single-key shortcuts can be switched off (screen-reader mode). All state screens follow `06_RESPONSIVE_AND_STATES.md`: loading (dim, then static skeletons after 400 ms), empty, error with reference id, parser error, unavailable, degraded ("Not a production installation", connection lost blanks views) and gated. Layouts are responsive from wide down to an 800 px window, with no horizontal scroll. Only the allowed `sessionStorage` keys are used. | `app/b1/src/Mimamsa.Web/wwwroot/` |
| Statutes | A TOC is read from verified text. A section opens at its page. An amendment strip shows A4 temporal version candidates, linked to the Act through evidence in the held copy, with the notice "Temporal chain not established". The **as-of control is disabled** behind the gate. | `Generation/Toc.cs`, `pages.js` |
| Administration | Active-release overview: verification counts, start-up load issues, quarantine and policy epoch. **Withdraw** requires a reason and a confirmation dialog stating "not legal approval"; it takes effect at once on search, documents, citations and delivery. | `pages.js`, `Api.cs` |

## 2. How to run

```sh
# 1. data (scratchpad only; HF read with injected auth, no token printed)
python -I app/b1/build/build_sample.py --work <scratch>/b1work            # real sample site: <scratch>/b1work/site
python -I app/b1/build/build_fixture_site.py --out <scratch>/syn          # synthetic SYN site (PR #54 fixture)
# 2. offline PDF.js (connected build host: npm ci --omit=optional; or point at an installed copy of 6.5.438)
node app/b1/web/vendor.mjs [path/to/node_modules/pdfjs-dist]
# 3. build and run (PostgreSQL 16 on loopback; DSN in Mimamsa:Db)
dotnet build -c Release app/b1/Mimamsa.B1.slnx
Mimamsa__Site=<site> Mimamsa__Db="Host=127.0.0.1;..." ASPNETCORE_URLS=http://127.0.0.1:5199 dotnet app/b1/src/Mimamsa.Web/bin/Release/net10.0/Mimamsa.Web.dll
MIMAMSA_NEW_PASSWORD=... dotnet .../Mimamsa.Web.dll --add-user alice Admin --Mimamsa:Db="..."
# 4. tests
MIMAMSA_TEST_SITE=<syn>/site MIMAMSA_TEST_MAP=<syn>/fixture_map.json MIMAMSA_TEST_DB="..." dotnet test app/b1/Mimamsa.B1.slnx
python app/b1/tests/b1server.py --site <syn>/site --db "..." -- python app/b1/tests/oracles/run_retrieval_oracle.py --map <syn>/fixture_map.json --out out
B1_SYN_SITE=... B1_SYN_DB=... [B1_SAMPLE_SITE=... B1_SAMPLE_DB=...] node <playwright>/cli.js test --config app/b1/e2e/playwright.config.cjs --trace off
```

CI: `app-ci.yml` job `b1` (Linux, PostgreSQL service container) and `app-windows-poc.yml` job `b1-windows` (windows-latest). The Windows job also publishes win-x64, installs the service under `NT SERVICE\MimamsaB1` with SCM restart, creates an account through the CLI, and smoke-tests health, login, an identifier search, the 401 path and crash restart. **Both jobs are committed but Not executed:** pushing was not authorised.

## 3. Evidence (measured)

| Check | Result | Evidence |
| --- | --- | --- |
| Importer tests (including 4 B1 materialization tests) | **66/66 passed** | `app/importer/tests` |
| PR #54 DA comparator after the importer change | Unchanged: 64 lines, all "missing surface", **no contradicted value** (same as `RESULTS_DA.md`) | `da_cases.py` + `data_oracle.py --adapter-observations` |
| C# unit, site and integration tests (real Kestrel process + PostgreSQL) | **70/70 passed** | `app/b1/tests/Mimamsa.Tests` |
| Playwright journeys, SYN site (UX ids) | **16/16 passed** | `app/b1/e2e/journeys.spec.cjs`, `evidence/e2e_results.json` |
| Playwright journeys, real sample | **7/7 passed** | `app/b1/e2e/sample.spec.cjs` |
| PR #54 `retrieval_oracle.py` (unmodified; blob checked against HEAD before running) | **10/14 Passed, 4 Failed.** RET-06, 07, 09 and 10 expect mode `hybrid` and B1 is lexical only. RET-07 and RET-10 also miss J1-MAJ or J2-MAJ at rank 10. | `evidence/retrieval_oracle_*.json` |
| Design token, keymap and policy tests (`app/design/tests`) | Unchanged and still passing; `gen_tokens.py --check` shows no drift | |
| Search latency, sample, loopback, same host | Sequential: p50 20 ms, p95 92 ms. 10 concurrent: p50 80 ms, p95 308 ms (n = 200). **Informational only:** shared VM, client on the same host. | `evidence/search_latency_linux_vm.json` |

**Disclosure on RET-02.** RET-02 (`exact:"Rule 8(3)(a)"`) failed in the first run: the notice mentioning the rule ranked above the rule itself. I then added a general rule: when a phrase is itself a provision identifier, the provision's own text in an Act or Rules document ranks before mentions. RET-02 passed afterwards. The fixture is a public development set, so **this pass is not independent evidence**. RET-12's ranking also changed under the same rule. Nothing was tuned for the four hybrid cases.

### UX journeys (retrieval-ux.md), expected vs observed

| Test | Status | Observed / limits |
| --- | --- | --- |
| UX-01 W-01 | **Failed** (partial) | Filter counts are deterministic. J2-MAJ opens at p.7. Practitioner and Commander show the same counts. **J1-MAJ is not retrieved** (lexical only), so "both operative passages" fails. |
| UX-02 W-02 | **Failed** (partial) | Passed: identifier first, chips, restorable deep link with filters, malformed query held with caret and explicit "words only" run. **Not implemented:** select, remove or edit a parsed chip. |
| UX-03 W-03 | **Passed** | Hit navigation N/Shift+N; legal citation `Vale v. Lark, 2021 BRSYN 21 (…), para 12 (metadata not verified)`; Shift+C internal reference with permalink; OCR "search only" label. Bounding-box checks: Not executed. |
| UX-04 W-04 | **Passed** | Seven axes in order; full hash; the Admin sees the publication actor and the User does not. |
| UX-05 W-05 | **Passed** | Separate proceedings; "Candidate"; "not evaluated". Owner hide decision (D-08): Not implemented. |
| UX-06 W-06 | **Passed** | TOC to R-3A and R-3B at p.4 and p.5; as-of disabled with gate. N-20 candidate amendment edge: Not implemented (no amendment edge in SYN). |
| UX-07 graph | **Not implemented** | B3. Cited/Citing lists exist; no canvas or path. |
| UX-08 W-09 upload | **Not implemented** | B2. |
| UX-09 W-10 | **Passed** | The withdrawal is effective at once on deep link, search and citation; the User gets 403 on admin. Autocomplete: none exists. Graph: Not implemented. |
| UX-10 W-13 | **Passed** | |
| UX-11 compare | **Failed** (partial) | Truncation warning: Passed. **Side-by-side compare: Not implemented.** |
| UX-12 | **Passed** | R1 copy at p.6 with notice; current edition is a separate action; unknown prefix gives the generic notice. |
| UX-13 | **Passed** | |
| UX-14 | **Passed** (partial) | A late Q1 never overwrites Q2; offline blanks views and recovers. Embedding-service fallback: Not applicable (no semantic layer). |
| UX-15 | **Passed** | Through the test-only range fault control. |
| UX-16 | **Passed** (automated subset) | Keyboard path, focus return, landmarks and accessible names, 2 px focus ring, screen-reader mode. **NVDA/JAWS, 200%/400% zoom and tablet: Not executed.** |
| UX-17 | **Passed** (partial) | Glyph plus text; banner on every view. Print and greyscale: Not executed. |
| UX-18 | **Not executed** | Needs a human reviewer. |
| UX-19 | **Blocked** (partial) | Hindi query finds L-HI with OCR and low-confidence labels: Passed. The **Devanagari original page cannot be rendered**: no Devanagari font or imaging library, and apt is not allowed. A Latin placeholder page is used instead (`build_fixture_site.py` records this). |
| P9 independent walkthrough | **Not executed** | Requires a reviewer who did not design the screens. |

The PR #54 `transport_oracle.py` was **not re-run** on B1. The B1 delivery adapter emits the same trace events, but the PoC trace harness drives bearer tokens and a seed file, and B1 uses cookie sessions; adapting the harness was not done. Its last acceptance is for the PoC host (`POC_RESULTS_C13.md`).

## 4. Measured vs not measured

- **Measured:** the counts in §3; import verification; start-up re-hash; latency on the VM.
- **Not measured:**
  - retrieval quality on real queries (no human labels; the blind holdout is under custody);
  - performance on reference hardware;
  - Windows anything (CI not run);
  - TLS;
  - browsers other than Chromium;
  - screen readers;
  - memory at the 20 GB scale.

  The in-memory index holds 38k passages; full-corpus sizing is unproven.
- **P2 figures do not transfer.** P2 measured Tantivy. B1 is its own C# BM25 implementing the same method; its quality has only been exercised by the synthetic oracle.

## 5. Known limits and open items

1. **Selected host: BLOCKED** (owner hardware). **TLS is not configured.** The service is HTTP on loopback; LAN serving needs a certificate (AD-8) and `Mimamsa:SecureCookies=true`. **Signing:** dev-signed bundles only. No production trust list, Authenticode or MSI.
2. **No semantic or hybrid search**, so RET hybrid cases fail by design. The "Semantic search unavailable" degraded banner is replaced by a permanent run-line statement.
3. **Generations:** the service serves one generation per process lifetime and needs a restart after an import. **Withdrawals** are local Admin (PostgreSQL fence). They are not yet in the signed exclusion channel (contract README §3.3, X7/B2). The exclusion channel is configured as `none`.
4. **Shared copies:** 7 sample doc_ids share bytes with another doc_id. Citation resolution is keyed by copy hash, as in the importer reference, so a permalink naming the second doc_id gives REFERENCE_MISMATCH.
5. **A5 treatment spans** were bound to the c7 derivative with file-level offsets. They are carried as page-only anchors with the extractor quote, labelled as such.
6. **Notes, pins, saved searches, server-side tabs and history:** Not implemented (B3). The Notes tab says so.
7. **Highlights in the original** are word marks in the PDF.js text layer (approximate on justified text, per P4). There are no OCR word boxes.
8. **Accessibility:** contrast is enforced by the token tests; the other checks are automated basics only. There is no axe-core: it is not available offline and npm is not allowed here.
9. **R2-N01 review P3s:**
   - N1 and N2 are addressed in code, without new transport measurements.
   - N3: a pool without port information keeps its charge, as in the PoC. The operator procedure is to check that no process holds the socket, then restart the service; reconciliation then requires OS evidence.
   - N4 and N5: open for the selected host.
10. The PDF.js lockfile was assembled from the PoC's verified lock entries, because npm install was not allowed offline. CI uses `npm ci --omit=optional`.

## 6. Screenshots (deviceScaleFactor 2)

These are in `docs/architecture/b1/screenshots/`.
- **Real sample:**
  - `b1-01` identifier search with the document;
  - `b1-02` evidence;
  - `b1-03` provenance;
  - `b1-04` statute s.75;
  - `b1-05` and `b1-06` at 1366 (compact, evidence drawer);
  - `b1-07` and `b1-08` narrow at 1024 and 800;
  - `b1-09` Commander view and abbreviation chip;
  - `b1-10` dark Text view;
  - `b1-11` admin;
  - `b1-12` gated assistant.
- **SYN:** `syn-01` to `syn-19`, named by UX id.
