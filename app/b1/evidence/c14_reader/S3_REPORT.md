# C14 S3: statutes and reader

**Branch:** `claude/c14-reader`, based on staging `ee17b066`.

**Scope:**
- statutory relationships (F03);
- Statutes navigation (F11);
- library home and the early Commander home;
- reader: scroll to the cited passage (F12), Fit page, one banner line, readable provenance;
- language and unreliable-text handling (F07).

**Not touched:** identifier resolution, ranking, pagination, results rendering, facets (S1); admin, identity, withdrawal, delivery (S2); hybrid search (S4).

**Not changed:** no legal approval state, no AUTH-LEDGER value, no acceptance oracle, no corpus bytes, no bundle signature.

## 1. What was built

| Area | Implementation | Files |
| --- | --- | --- |
| Correspondence (F03) | Candidate edges IPC↔BNS, CrPC↔BNSS and IEA↔BSA, read at first use from the three held comparison tables (`ref-bprd-comparison-*`, Bureau of Police Research and Development). Rows are accepted only in ascending order of the new section (jump ≤ 15 after the first row) and only when followed by a subject or old-section cell; unreadable rows are skipped, not guessed. Each edge carries the table document, page and row text. All three table layouts are handled (old section on its own line, at the end of the subject line, or beside the new section; `]` artefacts; "New"/"-" rows). | `Mimamsa.Core/Statutes/Correspondence.cs` |
| Commencement, repeal, savings (F03) | Every notice quotes held text with its page:<ul><li>*commencement delegated* (s.1(2) text of each new code);</li><li>*commencement notification not held* (stated, no date inferred);</li><li>*commencement date in a secondary source* (the comparison table's 1 July 2024 mention, labelled secondary);</li><li>*repeal* (s.358 BNS, s.531 BNSS, s.170 BSA, read from the held TOC);</li><li>*savings and transitional* (sub-section (2) onwards);</li><li>*repealed by* on the IPC, CrPC and IEA, quoting the repealing clause of the new code.</li></ul>A fixed caution states that corresponding provisions are **not legally interchangeable**. | `Statutes/StatuteRelations.cs` |
| Display | The Statutes section view shows correspondence first, with notices collapsed. The instrument overview shows notices. The document context pane (Related tab) shows relationships for the sections printed on the current page. Every row is labelled "Candidate (automated, not verified)", carries the evidence link, and links to the corresponding section in Statutes. | `wwwroot/assets/js/relations.js`, `pages.js`, `research.js` |
| Statutes navigation (F11) | Instrument catalogue:<ul><li>one entry per instrument (family = printed Act number; schedules join their parent);</li><li>editions, language versions and schedules nested, with labels such as "Hindi", "separately published copy", "consolidated (as amended)", "Schedule: The First Schedule";</li><li>categories: Army, Navy, Air Force, Armed Forces Tribunal, Criminal codes (in force from 1 July 2024), Criminal codes (repealed; historical), Other;</li><li>a filter box;</li><li>an overview pane in place of empty space;</li><li>an edition switcher on the instrument page.</li></ul>The TOC also reads headings printed as "22." on their own line (Army Rules, 1954), which were previously missing. | `Statutes/Instruments.cs`, `Generation/Toc.cs`, `pages.js` |
| Library home | Shown in the document pane while no document is open:<ul><li>corpus summary: documents, pages, years, release, counts by type and court;</li><li>statute shortcuts;</li><li>recent documents and searches, kept **in memory for this page only** (no browser storage; sessionStorage policy unchanged);</li><li>example queries.</li></ul> | `home.js`, `/api/library` |
| Commander workspace (early) | Same engine, different workflow. Task cards:<ul><li>investigating an offence and hearing the charge;</li><li>absence and desertion;</li><li>arrest and custody;</li><li>summary punishment;</li><li>summary court-martial;</li><li>safeguards;</li><li>forms.</li></ul>Each provision is resolved against the held TOC and shown with its heading as printed; unresolved items say so. Labelled "Early"; not legal advice. | `StatuteRelations.cs` (task list), `home.js` |
| Reader (F12) | On open, the viewer reads the cited passage's text from the verified derivative, finds it in the PDF text layer, scrolls it into view and draws a bar where it starts. Without a passage, the first highlight is scrolled into view. **Fit page** was added. | `viewer.js`, `research.js` |
| Banner | One line: the development-key statement moved onto the candidate banner (`#banner-dev`). `#degraded` now shows only the connection-lost notice. | `index.html`, `app.js`, `app.css` |
| Provenance | Grouped into "Where it came from", "This copy", "In this library" and "Notes", with one-line plain-language leads. "Unresolved reference" is replaced by what the extractor found and the citing sentence. | `research.js` |
| Language and reliability (F07) | Per document at generation load:<ul><li>detected language by script share;</li><li>legacy-font Devanagari signature: the share of Devanagari words that begin with a dependent vowel sign or virama, threshold 1%, at least 200 words;</li><li>measured: well-formed Hindi 0.000–0.001; legacy-font copies 0.033–0.545.</li></ul>Mostly-Hindi failures are **unreliable**: not indexed for search (one isolated hook in `SearchIndex.Build`; `Indexable`/Eligibility unchanged, so the documents stay openable). Mixed documents are **partly unreliable** (label only). Language marker and chip in the document header; notice in the Text view; fields in the document, summary and text API responses. | `Generation/TextQuality.cs`, `SearchIndex.cs`, `Api.cs`, `research.js` |

## 2. Tests

| Suite | Result |
| --- | --- |
| C# | 97/97: 89 existing unchanged, 8 new in `StatuteRelationsTests.cs`, including negative cases and the real-sample relations test |
| Playwright, full run on `9ad93cd4` + the `home.js` fix | 38/42: 30 existing and 12 new; 4 failed (below) |
| Playwright, after the fixes (UX-06 + R-01…R-08) | 11/11 |
| Design tests / `gen_tokens --check` | 117/117 / no drift |
| Retrieval oracle (not edited) | 10/14, the same 4 hybrid cases |

The full suite is re-run on the C14 integration branch.

**Completion note.** The original S3 agent and its resumed run were interrupted, by a session restart and then by a worktree write guard. The coordinator finished the branch from `9ad93cd4` and fixed the following:

1. **`home.js`:** one extra `)`. Every UI module failed to load, so all journeys timed out at sign-in.
2. **`Api.cs` `DocumentDto`:** `language_name`, `language_detected` and the `text_reliability` object were computed but not sent, so the header had no language marker or reliability chip (R-04).
3. **`research.js`/`app.js`:** switching to Commander view did not redraw the home, because `mountResearch` keeps the existing shell. Added `refreshHome()` (R-07).
4. **R-01 test:** expected 3 "sanhita" matches; there are 2, BNS and BNSS (the BSA is the *Sakshya Adhiniyam*). The test was corrected.
5. **UX-06 (existing test, intended change):** the grouped list now carries an instrument link plus nested edition links, so the test selects the instrument entry explicitly.

## 3. Acceptance

| Check | Result | Evidence |
| --- | --- | --- |
| `/s/act-ipc-1860/302` shows candidate BNS s.103 with evidence; reverse on BNS s.103 | Passed (R-02) | `r02-ipc-302-correspondence-1920.jpg`, `r02-bns-103-reverse-1920.jpg` |
| Repeal, savings and commencement notices quote held text with a page | Passed (R-03) | `r03-bns-repeal-savings-1920.jpg` |
| "Not legally interchangeable" caution | Passed (R-02) | |
| s.75 still printed as omitted; as-of closed | Passed (R-03) | |
| Correspondence rows read | IPC↔BNS 431, CrPC↔BNSS 521, IEA↔BSA 191 | `relations_stats.json` |
| Statutes grouped | 51 instruments from 64 statute documents; filter; editions nested | `r01-statutes-list-1920.jpg` |
| Hindi legacy-font copies flagged unreliable, with header marker, Text notice, not searched | 5 Acts flagged (Air Force, AFT, Army, Disposal of Private Property, Navy); 3 partly unreliable; the Unicode BNS/BNSS/BSA copies are reliable (R-04) | `r04-hindi-unreliable-text-1920.jpg` |
| Cited passage visible on open, s.69 Army Act | Passed at 1366, 1920 and 2560 (R-05) | `r05-scroll-to-s69-*.jpg` |
| Library home and early Commander home | Passed (R-07) | `r07-*.jpg` |
| One banner line; grouped provenance | Passed (R-08) | `r08-provenance-grouped-1920.jpg` |

## 4. Open issues

- The correspondence parser is heuristic and tuned to the three held BPRD layouts. A different table layout would yield fewer edges, never wrong ones: unreadable rows are skipped. Every edge stays a candidate for legal review.
- No commencement notification for 1 July 2024 is held. The date is shown only as a secondary-source statement.
- Commander task lists are a fixed, provision-level map, labelled "Early". Forms are reached by search only.
- The reliability threshold (1% signature, ≥ 200 Devanagari words) was set on this sample. Re-check it on the full corpus.