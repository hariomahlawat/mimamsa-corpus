# Independent review: Cycle 13 B1 application prototype

- **Branch under review:** `claude/c13-b1` at `fa72af91`. The diff is taken from integration `db801617`.
- **Reviewer:** independent. I did not build B1.
- **Date:** 2026-11-25.
- **Method:**
  - I exported the tree with `git archive fa72af91` into `reviews/b1/src` and built it Release there.
  - I vendored PDF.js from the PoC copy of 6.5.438. Its SHA256SUMS are identical to the author's vendor directory.
  - I used my own PostgreSQL 16 instance (loopback, port 55470) and my own rebuilt SYN site.
  - I used the author's real sample site (`c13/b1work/site`) read-only.
  - Every service was bound to 127.0.0.1.
  - The branch worktree was not modified: `git status` is clean.
- **Reviewer scripts and outputs:** `reviews/b1/scripts/` (`da_b1.py`, `held.py`, `scan.py`, `spot.py`, `anchors.py`, `ui.cjs`) and `reviews/b1/work/`.

## Verdict

**CHANGES REQUIRED. Not acceptable as the B1 baseline until F01 is fixed and re-tested.**

| Severity | Count |
| --- | --- |
| P1 | 1 |
| P2 | 6 |
| P3 | 6 |

The core is solid:
- Authentication is enforced on every content route.
- CSRF holds.
- Range handling is strict.
- Path traversal fails.
- Logs are content-free.
- RM-001 is absent.
- The importer extension is fail-closed for DA-01, DA-04 and DA-35.
- Citation page anchors are correct (31/31).
- Every suite reproduces.

However, the held-copy (ASR-E06) path serves original bytes of documents that are not eligible now. This includes the earlier edition of a document an Admin has just withdrawn, even though the withdrawal response says it was removed from original delivery. Withdrawn-document identifiers also leak through the A4 and A5 surfaces. The Windows CI job, described as "Not executed", actually ran and **failed**.

## What I re-ran (measured)

| Check | Result |
| --- | --- |
| `dotnet build -c Release` | 0 warnings, 0 errors |
| C# tests (real Kestrel and PostgreSQL, my DB and my SYN site) | **70/70 passed** |
| Importer pytest | **66/66 passed** |
| Playwright, SYN and sample (`--trace off`, my DBs) | **23/23 passed** (16 SYN, 7 sample) |
| PR #54 retrieval oracle (unmodified, via the worktree runner and my DLL) | **10/14** (RET-06, 07, 09 and 10 fail). Matches the author. |
| CI on GitHub for `fa72af91` | `app-ci.yml` `b1`: **success**. `app-windows-poc.yml` `b1-windows`: **failure** (see F03) |
| Unauthenticated access to `/api/search`, `/statutes`, `/documents/*`, `/text`, `/pdf-meta`, `/range`, `/admin/*`, `/cite` | All 401 |
| CSRF on `/api/admin/withdraw` (no token; another user's token; text/plain cross-origin) | All 403. A User with their own token also gets 403. Cross-origin login gets 403. Logout without a token gets 403 |
| Range abuse (missing, open-ended, suffix, multi-range, more than 64 KiB, reversed, malformed) | 400. Beyond EOF gives 416. An exact 64 KiB range gives 206. A doc/sha mismatch gives 404 |
| Path traversal (`..%2f` in docId, sha and static paths; `/appsettings.json`; `/Mimamsa.Web.dll`) | 404. An uppercase sha is canonicalised (206 for the same copy) |
| RM-001 sha `4284820e…` | Absent from the site, the bundle, the hfcache (522 MB re-hashed), every generation record, research file and vault object |
| Logs after about 860 requests including withdrawals | Method, route template, status and ms only. No query text, document text or withdrawal reason |
| External requests from the UI (Playwright) | None |
| Generative AI / LLM calls in `app/b1/src` | None. The only "llm" is a field-origin display label |
| Production signing key | None. The bundle uses a disposable in-memory key, and no private key is in the diff |

## Findings

### F01 (P1): the held-copy path serves originals that are not eligible, and withdrawal does not cover earlier editions

**Evidence (live, loopback):**

1. **SYN site, real Admin API.** I withdrew `syn-j-allow`. The response said: *"Removed from search, documents, citations and original delivery for every user, effective now."* Afterwards, as a User:
   - `/api/cite?doc=syn-j-allow&sha=a5c4093f7605&page=6` returned `CITED_COPY_ELIGIBLE_NOT_CURRENT` with the full R1 copy hash.
   - `GET /api/v2/documents/syn-j-allow/copies/a5c4093f…/range` returned **206** with the bytes.
   - The withdrawn judgment's earlier edition therefore stays readable through permalinks and the viewer.
2. **Reviewer two-release site** (`scripts/held.py`, real importer). R1 holds a PUBLISHED doc, a **STAGED** doc and a third doc. R2 holds only the first. As a User on the B1 service:
   - `toy-staged-r1` (never published): `/api/documents` says not available, but `/api/cite` gives `CITED_COPY_ELIGIBLE_NOT_CURRENT`, `/pdf-meta?copy=` gives 200, and `/range` gives **206** with the original bytes.
   - `toy-dropped-in-r2` (removed from the later release, which is exactly what happens when a copy is later found restricted and dropped): the same result, **206**.

**Cause.** `AppServices.AuthorizedCopy` and `CitationResolver.Resolve` accept any copy in `GenerationStore.HeldCopies`. That set is every `item_document` entry of every activated generation. The only checks are not-withdrawn (for that exact doc/sha pair) and vault re-hash. The code does not check:
- the copy's publication state in its generation;
- the current restricted register;
- whether the document is still in the active release;
- whether the document has been withdrawn at doc level.

`Api.cs /api/admin/withdraw` fences only `d.CopySha`, the current copy.

**Why P1.** This breaks PR-15 (Admin-only staging), DA-07, DA-09 (withdrawal must remove every User-visible derivation) and the withdrawal effect statement the Admin is shown. A future restricted-register hit on an earlier copy would be served by hash.

**Required fix:**
- A held copy is servable only if all of these hold:
  - it was PUBLISHED in the generation that held it;
  - neither its doc_id nor its sha is withdrawn, tombstoned or restricted under the current register and exclusions;
  - the policy explicitly allows earlier editions of documents absent from the active release.
- Withdrawal must fence the doc_id across all held copies, or give a per-copy choice that the dialog states.
- Add C# and Playwright tests for:
  - withdrawing a document that has an earlier edition;
  - a STAGED copy in an earlier generation;
  - a copy dropped from a later release;
  - a register hit on an earlier copy.
- Correct the withdrawal effect text until this is fixed.

### F02 (P2): withdrawn documents stay disclosed through A4 and A5 surfaces

**Evidence.** I withdrew `notif-appointed-day-aft-notification` and `sc-1987-ranjit-thakur-1987insc285`, then rescanned all 290 `/api/documents` responses as a User:
- **16 A4 evidence entries** on 8 Acts still name the withdrawn notification: `doc_id`, full copy sha, page and `resolution: "RESOLVED_TO_VERIFIED_COPY"`. Examples are the AFT Act 2007, Finance Act 2017 and the Tribunals Reforms Acts. `research.js` renders each one as a clickable "Evidence: … p.1" link.
- A5 edge `payload.target.node_id` still carries `JUD:JG-35b9c948fe62`, the SHA-12 of the withdrawn copy, in 3 citing documents.
- `edgeCard` shows that `node_id` as the target text whenever `target_in_library` is null, which is exactly the post-withdrawal case. Internal node ids are also shown to Users in normal use.

Search, documents, text, citation, cite, pdf-meta, range, edges_in and target_in_library were all correctly filtered.

**Required fix:**
- Resolve A4 evidence through `VisibleDocument` at response time. A copy that is not visible must read as unavailable with no doc_id or sha.
- Strip or redact `payload.target.node_id` and other internal ids from the User DTO.
- Never display node ids.
- Extend `WithdrawalNeedsCsrfAndThenRemovesTheDocumentFromEverySurface` to cover the A4 and A5 payloads.

### F03 (P2): the Windows CI job failed, but the document says "Not executed"

**Evidence.**
- Run 45713405941, job `b1-windows`: build and 70/70 tests passed on Windows.
- The oracle step then failed: `UnicodeDecodeError: 'charmap' codec can't decode byte 0x81`. The cause is `FIXTURE.read_text()` without `encoding="utf-8"` at `run_retrieval_oracle.py:60`.
- The Playwright journeys and the **Windows Service publish, install and crash-restart smoke were skipped**. B1_PROTOTYPE.md §2 and §4 say the jobs are "Not executed".

**Required fix:**
- Use `encoding="utf-8"` on every `read_text` and `open`, including the runner, `b1server.py` and the build scripts.
- Re-run `b1-windows`.
- Record the actual result: "Failed at oracle step; service smoke not reached" until it passes.

### F04 (P2): search highlights hide the original text in the protected viewer

**Evidence.** In `work/shots/r-doc-1024.png` (Dharamvir Singh, query `2013 INSC 408`), each "2013" in `[2013] 8 S.C.R. 1119`, `Civil Appeal No. 4949 of 2013` and `JULY 2, 2013` is covered by a solid yellow block, so the year cannot be read on the original page. `app.css:226` relies on `.textLayer mark { mix-blend-mode: multiply }`, which has no effect against the canvas in this stacking context. For a legal reader, the cited year being invisible on the original is a source-fidelity defect.

**Required fix:**
- Use a translucent highlight (for example rgba alpha 0.35), or an outline or underline that never hides glyphs, or fix the blend context.
- Add a pixel test that the canvas region under a mark still has dark glyph pixels.

### F05 (P2): defects in identifier search precision

**Evidence:**
- `2013 INSC 408`: all **94 passages** of the document are returned as tier `identifier` with the reason "Neutral citation … in document metadata". The viewer then shows "hit 1 of 94". This also happens for `OA 1541/2025`, where every passage is an "identifier" hit. Hit navigation and result counts become meaningless.
- `Rule 22 Army Rules`: the first pinned result is **Rule 22 of the Army and Air Force (Disposal of Private Property) Rules 1953**, labelled "provision text". Army Rules 1954 r.22 appears only as a "heading" hit. The act-name scoping (`actWords.All(w => TitleTerms.Contains(w))`) matches any statute whose title contains "army" and "rules".
- `army act` (plain) ranks the Disposal Rules and two SC judgments above `act-army-1950` (8th).

**Required fix:**
- For a document-level identifier, pin one representative passage (the cover or page 1) and leave the other passages to lexical scoring.
- Prefer an exact short-title match, or the lexicon's canonical instrument, when scoping "Army Rules" or "Army Act". When it is ambiguous, show a disambiguation chip rather than pinning another instrument.

### F06 (P2): metadata accuracy (15-document spot check against the original PDFs)

I checked 15 documents: 4 statutory, 5 SC, 3 Delhi HC and one each from P&H, J&K and Allahabad. For each I compared the original bytes from the vault (PyMuPDF page 1) with `/api/documents`.

**Correct:**
- page counts (15/15);
- titles and dates for the statutes and SC (where printed);
- neutral citations and reported citations for SC;
- HC case numbers, dates and judges (all 6 HC documents match the printed cover);
- search page anchors, for which snippet text was found on the stated physical page in **31/31** passages across 8 queries.

**Wrong or missing:**
- **SC judges truncated to the first judge in every SC document I could verify.** That is 4/4 sampled SC documents with a text layer, plus Dharamvir Singh, which I checked in the UI. The fifth sampled SC document, R.K. Anand, has no page-1 text layer, so I could not verify it. Examples:
  - Dharamvir Singh: Patnaik only; Mukhopadhaya is missing.
  - R.P. Yadav: Thomas only; Mohapatra and Pal are missing.
  - Also affected: Tarsem Singh, Brahma Duti Tripathi, Ranbir Singh Rathaur.

  These are displayed as "Judges" with a small "crawler" chip.
- SC `case_numbers` are `[]` although they are printed on the cover (for example *Civil Appeal No. 5151-52 of 2008*). Case-number search therefore cannot find SC judgments.
- Allahabad `hc-allahabad-2025-wria-4804-2025`: neutral citation `2025:AHC-LKO:27197` is printed on page 1, but `neutral_citation` is null.
- `hc-delhi-2021-w-p-c-8670-2020`: the copy is the common judgment headed *W.P.(C) 8668/2020 & connected matters*. The title names a connected petition and does not say so.

The values come from upstream crawler metadata, which B1 does not invent. However, B1 presents a truncated list as the bench composition.

**Required fix:**
- Label incomplete fields, for example "Judges (crawler; may be incomplete)".
- Show cover-page case numbers as candidates.
- Raise the upstream metadata defects with the A-track owner.
- Do not present `judges[0]` as the bench.

### F07 (P3): ranking honesty and how to report the oracle (RET-02)

**The change** (commit `e4d7795b`):
- In `SearchService.Eval(QPhrase)`, a phrase that is wholly one provision identifier gets `+1000 × strength` for passages that are the provision's own text in an Act or Rules document.
- `Identifiers.ProvisionStrength` was widened to accept a `Section|Rule|Regulation|Article` prefix and nested `(x)` subclauses on heading lines.
- The `section:` field was given the same ordering.

**Assessment:**
- The rule is general in form. It has no fixture tokens, ids or document names, and it follows the pre-existing design (03 §2) already used by the unquoted identifier tier.
- Its exact scope (the prefix word and nested subclauses) was shaped by the one failing case.
- It also changed RET-12.
- The disclosure in B1_PROTOTYPE.md is honest.

**Required reporting:**
- "PR #54 development fixture: 9/14 on first run; 10/14 after a post-hoc general identifier-ordering change. RET-02 and RET-12 are not independent evidence. 4 hybrid cases fail by design."
- Carry the same wording in the capability matrix.
- Do not cite 10/14 as retrieval quality until the blind holdout is run.

### F08 (P2): test and evidence gaps that let F01 to F04 through

**Evidence:**
- `sample.spec.cjs` S-02 takes the b1-02 screenshot without waiting for `.pagewrap canvas`. The committed screenshot shows a blank "Loading page 1…" pane.
  - **The viewer does render.** I re-ran it: the canvas appears in about 1.3 s and is non-blank (920×1414, 32,923 dark samples), and there is no "Loading" text after 1.5 s.
  - The evidence is still misleading.
- The journeys assert real behaviour, not just page loads. Examples:
  - UX-03 checks the exact citation string;
  - UX-12 checks the cited page;
  - UX-09 checks withdrawal on deep link, search and citation;
  - S-01 checks the canvas and marks;
  - the HTTP tests check exact range bounds.
- But nothing tests:
  - held-copy eligibility (F01);
  - A4 and A5 disclosure after withdrawal (F02);
  - highlight legibility (F04);
  - identifier hit inflation (F05).
- CI runs the oracle with `run_retrieval_oracle.py` always returning 0, so a regression from 10/14 to 0/14 would stay green.

**Required fix:**
- Wait for the canvas before every viewer screenshot, and re-take b1-02.
- Add the tests listed under F01, F02, F04 and F05.
- Make the CI oracle step fail when the result drops below the recorded baseline, while still recording the expected hybrid failures.

### F09 (P3): the viewer routinely hits 503 on its own ranges

Opening one document produced 6 range 503 responses in the service log and in the browser console. PDF.js issues more parallel ranges than `MaxStreamsPerSession` (6) or the slot budget allows, and `viewer.js` retries with a 50 ms × n backoff. It works, but it inflates latency and pollutes error telemetry. **Fix:** limit the PDF.js range concurrency below the per-session cap, or queue requests client-side.

### F10 (P3): withdrawing one of two shared-byte twins breaks the live twin's permalinks

The sample has 7 doc_ids that share bytes (for example `hc-delhi-2025-w-p-c-17880-2024` and `…-2942-2025`). After I withdrew 17880:
- 2942's permalink returns `CITED_COPY_UNAVAILABLE`, because `HeldCopies` is keyed by sha to the first doc_id;
- 2942's bytes are still served (206).

Before the withdrawal, 2942's permalink gave `REFERENCE_MISMATCH` (known limit 4). **Fix:** key held copies by (sha, doc_id), and decide and document whether a withdrawal for content reasons must also cover byte-identical twins.

### F11 (P3): smaller service hardening items

- `Program.cs` falls back to a hard-coded DSN with password `mimamsa` when `Mimamsa:Db` is unset. Fail at start-up instead.
- Authenticated POSTs rely only on the CSRF header and do not check Origin. This is acceptable, but add the same-origin check used for login as defence in depth.
- Lockout after 5 failures with no timeout stated lets any LAN user lock the Admin account. Document the unlock procedure and consider a timed lockout.
- `ResponseSlots` is acquired before the per-session check, so a 503 from the session cap holds a slot until the connection drains. This is minor because the connection is `Connection: close`.

### F12 (P3): screenshot weight and content

There are 22 PNGs at DSF 2 totalling **18 MB** in git. Several are full-page renders of corpus PDFs. They are public documents, but they are still corpus page images, which permanently enlarges the repository on every refresh. **Fix:** keep 2 or 3 representative images at DSF 1, as WebP or JPEG, in git. Publish the rest as CI artifacts.

### F13 (P3): the cited earlier edition shows the current edition's metadata header

When an earlier edition opens from a permalink, the header title, date and judges come from the current record, followed by the note "(the metadata above is the current edition's record)". The notice is honest, but a reader can still take an edition's date from the wrong copy. **Fix:** show only copy-level facts for a non-current copy (SHA, pages, release first held), or that release's own record.

## Areas checked with no defect found

**Source fidelity (ASR-E05) on B1's data path** (`scripts/da_b1.py`, real importer, then the B1 service):
- **DA-01:** unbound and missing originals are refused. No ACTIVE generation is created and the vault is empty.
- **DA-04:** an out-of-page passage makes the derivative UNRESOLVED. `records/derived_text.jsonl` and `derived/` are empty. B1 serves the document as "not available" and never shows the text.
- **DA-35:** a cross-bound anchor is quarantined and `records/candidates.jsonl` is empty.
- The control case is served.
- `GenerationStore` reads only `records/`, the `servable` and `candidate_evidence` data from generation.json, re-hashed derivative text, and re-hashed vault objects.
- Research JSONL files are signed and restricted-register-checked. They are labelled candidate on display.
- The F01 hole lies in the held-copy authorisation, not in the materialization.

**Citation navigation:**
- `/cite` opens the exact copy and page.
- The current edition is never substituted. It is offered only as a separate "Open current edition" action, and only when it is visible.
- Withdrawn and unknown copies give the identical notice, "The cited copy is not available in this installation.", with no copy or doc_id. Restricted status is not disclosed.
- See F01 for copies that wrongly resolve as eligible.

**Candidate labelling:**
- A2 outcomes, A5 edges and A4 versions are always presented with a "Candidate (automated, not verified)" chip.
- The DTO carries `status: AUTOMATED_CANDIDATE_NOT_VERIFIED`, and the popover shows `AUTOMATED_CANDIDATE_NOT_VERIFIED`.
- Non-CITES relations carry "Proposed, not verified".
- Absence notices appear on every empty surface.
- Legal applicability is "Not established" and legal approval is "T0 Research only". The assistant is gated.
- I found no legal conclusion drawn by the application.
- Minor point: the document header outcome strip shows the label (for example "allowed") in bold next to the chip. Consider a less assertive weight.

**UX and accessibility** (axe-core is not available offline, so I checked manually with `scripts/ui.cjs`):
- Landmarks and skip link are present.
- Tab order is logical: skip, nav, search, view switch, user, facets, results, document toolbar, viewer, context tabs.
- The computed WCAG contrast scan of visible text in light theme at 1920 found **0** failures.
- At 1366 and 1024 there is no horizontal scroll and no off-screen controls. The rail and context collapse to drawers.
- Not checked: dark-theme contrast, 200% and 400% zoom, screen readers.
- Overall the visual design is professional, dense and consistent. F04, F05 and F09 are the defects a practitioner would notice first.

## Required before acceptance

1. Fix F01 and add the tests.
2. Fix F02 and F04.
3. Fix F03 and obtain a real Windows result.
4. Correct the reporting per F03, F07 and F08 (b1-02 screenshot, oracle wording, Windows status).
5. Then request a focused re-review of F01 to F05.

---

## Confirmation re-review at `4fbe7c79` (fixes in `ae7d7da0`; `4fbe7c79` only adds 9 lines to B1_PROTOTYPE.md)

**Method:**
- I exported `4fbe7c79` into `reviews/b1/src2` and built it Release (0 warnings, 0 errors).
- I used fresh databases on my own PostgreSQL instance, a fresh SYN site and the author's sample site read-only.
- Everything ran on loopback only. The worktree is unmodified.
- Outputs are in `reviews/b1/work2/`.

### Suites (re-run by me)

| Suite | Result |
| --- | --- |
| C# | **78/78** |
| Importer | **66/66** |
| Design | **117/117** |
| Playwright | **27/27** (19 SYN, including the new F01, F04 and F05 journeys; 8 sample) |
| PR #54 oracle | **10/14**. The same 4 hybrid cases fail. RET-03 still passes with J1-MAJ out of its top 3 (the side effect of the F05 change, disclosed by the author). |

### CI (logs read)

Both runs are for `ae7d7da0`, the last code commit.

- **Windows run 45716813226, job `b1-windows`: success.** Steps that ran:
  - build;
  - 70+ C# tests on Windows;
  - the oracle;
  - **19/19 Playwright SYN journeys on Windows**;
  - `dotnet publish win-x64`;
  - `--add-user` printed "created";
  - service installed under `NT SERVICE\MimamsaB1` with SCM restart actions;
  - health, login and identifier search (`mode=identifier`, first `syn-j-allow`);
  - unauthenticated search returned 401;
  - `Stop-Process -Force`, after which SCM restarted the service and health returned 200 again.

  The sample journeys do not run in CI (no corpus there), as stated.
- **Linux run 45716813309: success**, as reported by the coordinator. I did not open its logs.

### Finding status

| Id | Status | Re-test evidence |
| --- | --- | --- |
| **F01** (P1) | **CLOSED** | One `Eligibility` class is used by search, documents, text, sections, citation, `/cite`, pdf-meta, range, A4 and A5. **Earlier published copy, document still visible:** before withdrawal it opens (`ELIGIBLE_NOT_CURRENT`, 200 and 206), so ASR-E06 still works. **Withdrawing `syn-j-allow`:** reports `copies_withdrawn: 2`. Cite on the R1 copy gives UNAVAILABLE, and pdf-meta and range give **404**. **After a restart without state reset:** still 404 (the withdrawal is durable). **Reviewer two-release site:** a STAGED earlier copy and a copy dropped from the later release give UNAVAILABLE, 404 and 404, both under their own doc_id and under a visible doc_id with the same hash. **Sample:** the withdrawn judgment gives 404 on cite, range, text, sections and citation, and it is absent from search and statutes. |
| **F02** (P2) | **CLOSED** | Full rescan of 290 documents after withdrawing 3. 0 occurrences of the withdrawn doc_ids or their copy SHA-12 anywhere. 16/16 A4 evidence entries are redacted to `COPY_NOT_AVAILABLE_IN_THIS_INSTALLATION` with no doc, copy or page. 0 documents contain `JUD:` node ids. |
| **F03** (P2) | **CLOSED** | Windows CI is green, including the oracle, 19 journeys and the service install, smoke test and crash restart (logs above). |
| **F04** (P2) | **CLOSED** | `work2/shots/r-doc-1024.png`: every highlighted "2013" is legible through a translucent highlight. A pixel test was added (journey F04). |
| **F05** (P2) | **CLOSED for the reported cases.** See **F14** for a related gap | `2013 INSC 408` now gives **1** passage, tier `document`, explicitly "does not itself contain the identifier", and "hit 1 of 1". `OA 1541/2025` gives 1. `Rule 22 Army Rules` is scoped to **Army Rules, 1954**. `army act` gives a title match for the Army Act 1950 first. **The scoping rule is general, not a special case:** among statutes whose title contains every query word, keep those with the fewest extra title words. Equal distinct titles produce an ambiguity chip and nothing is pinned, for example `Rule 14 AFT Rules`: "which instrument?". |
| **F06** (P2) | **CLOSED (display mitigation; the upstream data is still incomplete)** | The header reads "Judges (crawler; may be incomplete)" with a tooltip note. Cover-page case numbers are shown as a Candidate (for example "Civil Appeal No. 4949 of 2013"). The only other judge-dependent surface is the `judge:` field filter (see F15). |
| F07 (P3) | **CLOSED** | B1_PROTOTYPE.md now says "9/14 on the first run; 10/14 after a post-hoc general identifier-ordering change … not independent", and gives the hybrid cases. |
| F08 (P2) | **CLOSED** | New tests cover F01 (C# and journey), F04 (pixel), F05 (journey) and A4/A5 redaction (C#). The viewer screenshot waits for the canvas: I measured render in 0.8 s with a non-blank canvas. The oracle runner now fails on any failure outside the recorded 4. |
| F09 (P3) | **CLOSED** | No range 503s in the browser console when opening a document. |
| F10 (P3) | **Code CLOSED; policy OPEN (owner decision)** | Held copies are keyed by (sha, doc_id). The live twin's permalink now gives `CITED_COPY_ELIGIBLE`. The twin's bytes remain served (206), and the withdrawal message now says so explicitly. |
| F11 (P3) | **Mostly CLOSED** | There is no default DSN: start-up fails without one. Withdraw and logout now require same-origin (evil Origin with a valid token gives 403). **Open:** no manual unlock procedure. |
| F12 (P3) | **CLOSED** | Screenshots total 4.5 MB. |
| F13 (P3) | **CLOSED** | `/cite` returns `copy_pages` and `first_release` for a non-current copy. The header text was not re-inspected in a screenshot. |

### New findings at `4fbe7c79`

**F14 (P2): the fallback for an unmatched instrument pins provisions of a different instrument as "Rule N".**
- **Evidence:** `Rule 22 Navy Rules` (no "Navy Rules" instrument is held) shows the chip "Rule 22 · any Act, Rules or Regulations in the library". It then **pins the Air Force Act 1950 s.22 as "Rule 22: provision text in The Air Force Act, 1950"**, followed by the AFT Act 2007 s.22, in the identifier tier.
- The query also gives `shown 200`.
- A user who names an instrument that is not in the library gets a different statute's section presented as the rule asked for.
- A related, milder case: `Rule 22 Rules` silently scopes to Army Rules 1954, the shortest "Rules" title, rather than showing the ambiguity chip.
- This behaviour existed before F05 but was not covered by the F05 fix.
- **Required fix:**
  - When the query names an instrument (residual words remain) and no title matches, do not pin anything. Show "No instrument titled '<words>' in this library" and run lexical search only.
  - Only use the "any instrument" scope when no instrument words were given.
  - Treat a single generic word ("Rules", "Act") as ambiguous.
  - Add tests for both cases.

**F15 (P3): the `judge:` filter silently relies on incomplete metadata.** `judge:mukhopadhaya` gives `empty`, 0 documents, with no caveat. Mukhopadhaya sat in Dharamvir Singh, but the crawler kept only the first judge. **Fix:** add a note to the field chip and the empty state: "Judge metadata may be incomplete (crawler); absence here is not evidence."

**F16 (P3): the restricted-register re-check is optional and empty by default.** `Mimamsa:RestrictedRegister` is not set by default, which gives `RestrictedRegister.Empty`. The "document absent from the active release" rule covers the dropped-copy case I tested. However, an earlier copy of a still-present document that is later added to the register would be served unless an operator configures the file. **Fix:** load the register referenced by the active release, or require the setting outside test mode (fail closed). Document it in the operator procedure.

### Confirmation verdict

**ACCEPTABLE as the B1 prototype baseline, with conditions.**

- The P1 (F01) is closed, and all original P2s (F02, F03, F04, F05, F06, F08) are closed.
- One **new P2 (F14)** must be fixed before B1 identifier search is relied on in practitioner walkthroughs. It does not block merging as a labelled prototype, because results remain labelled and verifiable at the source.
- The F10 twin-withdrawal policy and the F11 unlock procedure need owner decisions.
- F15 and F16 are P3.

---

## Second confirmation at `f71957e5` (F14, F15, F16)

**Method:** I exported the commit into `reviews/b1/src3`, built Release (0 warnings, 0 errors) and used fresh DBs, all on loopback. The worktree is unmodified. Outputs are in `reviews/b1/work3/`.

**Suites:**

| Suite | Result |
| --- | --- |
| C# | **86/86** |
| Playwright | **28/28** |
| Importer | **66/66** |
| Design | **117/117** |
| Oracle | **10/14** (the same 4 hybrid cases; no regression) |

**CI:** Windows run 45719359168 for `f71957e5` passed. `b1-windows` ran build, tests, oracle, journeys, publish and the service step, with the service now configured with `RestrictedRegister`.

| Id | Status | Evidence |
| --- | --- | --- |
| **F14** (P2) | **CLOSED** | **Unheld instruments:** `Rule 22 Navy Rules`, `s.5 Coast Guard Act`, and the misspellings `Rule 22 Army Rulse` and `Section 22 Armi Act` each give the chip `not_held` "No instrument titled '…' in this library". Nothing is pinned and the words run as lexical text. **Generic words only:** `Section 22 Act` and `Rule 22 Rules` give an `ambiguous` chip listing the candidates, and nothing is pinned. **Equally close titles:** `Rule 14 AFT Rules` gives `ambiguous`. **Correct scoping still works:** `Rule 22 Army Rules` resolves to Army Rules 1954, `s.69 Army Act` to Army Act 1950, and `Section 22 Air Force Act 1950` to Air Force Act s.22. **The rule is general,** with three branches in `IdentifierTiers`: (1) only generic words means ambiguous; (2) no title match means not held; (3) otherwise the closest titles, with ties ambiguous. It contains no instrument-specific tokens. |
| **F15** (P3) | **CLOSED** | `judge:mukhopadhaya` returns the `caveat` chip "Judge metadata may be incomplete (crawler); absence here is not evidence." `research.js` renders `caveat`, `not_held` and `ambiguous` chips as notices. |
| **F16** (P3) | **CLOSED** | Production mode (no test flag) refuses to start in each failure case: <ul><li>no register: `InvalidOperationException` "required … refusing to start";</li><li>missing file: `FileNotFoundException`;</li><li>register with empty items: "no items";</li><li>register with an extra item (mismatched SHA-256): "does not match the register pinned by the active release";</li><li>`Test:AllowNoRegister=true` without test mode: still refuses.</li></ul>The correct register (`fc7ea07e…`, equal to RELEASE.json `config_sha256`) starts. The override works only with `Test:Enabled=true`. Production config path: there is no committed appsettings default. The Windows CI service writes `appsettings.Production.json` with `RestrictedRegister` and grants the service account read on the file. |

**Residual P3s (non-blocking):**
- **F17:** B1_PROTOTYPE.md line 101 still calls the register "optional". This is stale wording; §F16 of the same file is correct.
- **F18:** `s.69 AA` gives "No instrument titled 'AA'", and the lexicon expands AA only to Air Adviser or Air Attache. The common practitioner form "AA s.69" (Army Act) is not recognised. This is a lexicon or alias gap; add instrument aliases (AA, AR, AFA and so on) to the scoping step.
- **F19:** a query that is ambiguous only (for example `Rule 14 AFT Rules`) returns 0 results instead of also running the words lexically. The notice is shown, but consider a lexical fallback.

**Final verdict:** **ACCEPTED as the B1 prototype baseline.** No open P1 or P2. Owner decisions remain on F10 (twin withdrawal policy) and F11 (manual unlock procedure).
