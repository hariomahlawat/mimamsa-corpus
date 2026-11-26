# C14 stream S1 (search): implementation report

- **Branch:** `claude/c14-search`, based on `ee17b066` (`legal-knowledge/v2.5-staging`).
- **Scope:** audit findings F01, F02, F06, F08, F09 (short term), F10, F11 (results part), F13 (results part) and F16.
- **Unchanged:** AUTH-LEDGER, approval states, corpus and sample manifest, signed bundles, the retrieval oracle and its fixture. No generative output.

## 1. What changed

| Area | Change | Files |
| --- | --- | --- |
| **Legal identifier resolver** (new, reusable) | `Mimamsa.Core.Legal.LegalIdentifierResolver` covers:<ul><li>**instrument scoping:** the F05/F14 rules moved here unchanged;</li><li>**aliases**, resolved only against **held** titles: IPC, CrPC, CPC, IEA, BNS, BNSS, BSA, AA, AFA, NA, AFT, AR, AFR, NR; dotted forms such as I.P.C. and Cr.P.C. collapse;</li><li>**case names:** petitioner/respondent, "X v Y" sides, generic party words never pin, more than 5 matches are reported but not pinned;</li><li>**citation queries in brackets** ("(2013) 7 SCC 316") are treated as identifiers, not query syntax;</li><li>**instrument group key**, variant label and primary copy (editions and language versions);</li><li>**service context** (Army, Navy, Air Force or general), used only as a ranking signal.</li></ul> | `Core/Identifiers/LegalIdentifierResolver.cs` |
| Citations | AIR and SCALE patterns added. Reported citations are recognised before neutral ones, so "AIR 1987 SC 2386" is not misread. Parallel citations in the **page-1 masthead** (first 600 characters) are captured as candidate identifiers ("printed at the top of p.1 (extracted, not verified)"). An unrecorded citation gives the chip *"Citation not recorded in this library: …"*. | `Search/Identifiers.cs`, `SearchIndex.cs`, `SearchService.cs` |
| Ranking | **Case-name tier** pinned above judgments that only cite the case (chip "Case name · …", tier `case_name`). **Statutory aliases** pin the provision exactly as full titles do; an `alias` chip discloses the expansion and says it is not a statement of equivalence. | `SearchService.cs` |
| Pagination (F10) | `/api/search` takes `page`, `page_size` (default 25, max 100) and `sort` (`relevance`, `new`, `old`, ordered server-side). It returns `page`, `page_count`, `total_groups` and `groups[]`. Every result group can be reached; the page number is in the URL and restores. A page carries the first 20 passages in relevance order unchanged, so the top of the ranking is as before, then at most 3 per document, with `passage_count` per group. | `SearchService.Page`, `Api.cs`, `research.js` |
| Grouping (F11, results) | One group per instrument. Hindi text, alternate prints and consolidated texts are nested ("Also held: Hindi text"). The English, unsuffixed copy represents the group when it has hits. Judgments are never merged. | resolver, `SearchService.Page`, `research.js` |
| Spelling (F08) | `SpellingSuggester`: deterministic edit distance (OSA) over the index vocabulary (seen in at least 3 passages) plus party names. It handles unknown words and rare word pairs ("court marshal" → "court martial"). The suggestion is shown as a "Did you mean" chip and runs **only when clicked**. | `Search/SpellingSuggester.cs`, `research.js` |
| Service preference (F09, short term) | A `service` parameter and a Service selector (default All). Ranked lexical hits score ×1.6 for the chosen service and ×0.5 for another service. Identifier, case-name and mention tiers never move, and nothing is excluded. The run line states the preference. | `SearchService.ServicePreference`, `Api.cs`, `research.js` |
| Density (F13 results, F16) | Provenance collapses to one line (`<details>`). Snippets are clamped to 3 lines and expand when selected. Two passages per group are shown, with a "n more" count. Status labels are readable ("In force (crawler)", "Status unknown"). The year inputs are empty, with the range shown as a hint. | `research.js`, `app.css` |

No change to: viewer or document pane, Statutes pages, admin, identity, delivery, hybrid search, Hindi reliability handling, or `sessionStorage` keys (none added).

## 2. Tests

| Suite | Result | Notes |
| --- | --- | --- |
| C# (unit, site, HTTP with real Kestrel and PostgreSQL) | **122/122** | 89 existing (none modified) plus 33 new: `C14SearchTests.cs` (resolver, case names, citations, grouping, service, edit distance, SYN case names, unrecorded citation, suggestion never applied, paging covers every document in relevance order, service never moves pinned tiers) and `HttpTests.SearchIsPagedByDocumentGroup` |
| Playwright | **35/35** | 30 existing (none modified) plus `C14-S1a` and `C14-S1b` (SYN) and `S-10`, `S-11`, `S-12` (sample). In one full run, S-05 showed "The original could not be displayed" once for one PDF (a protected-delivery step under heavy machine load). It passed in 3 isolated repeats and in two further full runs. It is recorded as intermittent and is not in S1's scope. |
| Retrieval oracle (unchanged, `run_retrieval_oracle.py`) | **10/14** | Same 4 hybrid failures (RET-06, 07, 09, 10). Top results identical to the C13 baseline. `oracle_*.json` |
| Design tests | **117/117** | `gen_tokens.py --check`: no drift |

## 3. Acceptance on the real 290-document sample

The audit's 43 queries plus Q05, Q07 and Q13 with `service=army` were run through `/api/search` (`search_raw_s1.json`) and compared with the audit baseline (`COMPARISON.md`, `ACCEPTANCE.json`).

| Criterion | Result | Detail |
| --- | --- | --- |
| Q28 `section 302 IPC` pins IPC s.302 with an alias chip | **Met** | Chips: "Section 302 · The Indian Penal Code" and "IPC → The Indian Penal Code". First passage "302. Punishment for murder" (identifier). `s.302 I.P.C.` behaves the same. |
| Q29 `section 103 BNS` pins BNS s.103 with an alias chip | **Met** | "BNS → The Bharatiya Nyaya Sanhita, 2023". The Hindi copy is nested in the group. |
| Q18 `Dharamvir Singh` ranks 2013 INSC 408 first | **Met** | Rank 1 (baseline: 9). Chip "Case name · DHARAMVIR SINGH v. UNION OF INDIA & ORS.". |
| Q19 `(2013) 7 SCC 316` pins, or says "citation not held" | **Met (not held)** | "Citation not recorded in this library". No SCC citation is in the metadata or the masthead. `[2013] 8 S.C.R. 1119` pins the judgment. |
| Q25–Q27 correct suggestion | **Met** | "dharamvir singh", "court martial", "disability pension". The query still runs as typed. |
| Service = Army: Army Act in the top 3 for Q05, Q07, Q13 | **Met at document level; partly at passage level** | Q05: Army Act rank 1 (baseline 3), but its lead passage is s.87, not s.80. Q07: rank 3 (baseline: absent), but the passage is the contents page listing ss.49–51, not ss.101–102. Q13: rank 2 (baseline: absent). Pointing to the exact provision for plain-language questions needs passage-level semantics (WP9). |
| All 255 "court martial" documents reachable | **Met** | 11 pages of 25 groups. 254 groups plus 1 nested variant equals 255 documents. Last page reachable, Next disabled (S-12). |
| Unchanged queries | — | Every other identifier query keeps its pinned result (`COMPARISON.md`). |

## 4. Density and latency

| Viewport | Results fully visible (audit baseline → S1) |
| --- | --- |
| 1366×768 | 1 → **2** |
| 1920×1080 | 4 → **5** |
| 2560×1440 | 5 → **7** |

The audit's WP5 target of at least 3 results at 1366 is **not reached** by the results-pane changes alone. Both banners (52 px) and the empty document pane belong to the reader-layout stream. Screenshots are in `screenshots/`.

**Latency.** `latency_ab.py` alternates query by query between this branch (A) and a baseline `ee17b066` build (B): 20 queries, 7 rounds, same machine, same moment. The machine was shared with other streams under heavy load.

| Measure | A (this branch) | B (baseline) |
| --- | --- | --- |
| Sum of per-query medians | 860 ms | 823 ms (+4.5%) |
| Median of medians | 24.7 ms | 27.6 ms |

The overhead is concentrated in multi-word plain-language queries (suggestion pair check and case-name check). The suggestion pair count was rewritten as an allocation-free merge join after the first measurement.

## 5. Known gaps and open items

1. **Plain-language procedural queries:** the service prior brings the right instrument up, not the right provision (§3). Needs WP9 (hybrid).
2. **Density at 1366:** 2, not 3 (§4); needs the reader-layout changes.
3. **Case names:** exact word matching on the parties only. Spelling variants are handled by the suggestion, not by matching. A word counts as a name when it occurs among the parties of at most 50 judgments; this threshold is untested at full-corpus scale.
4. **Masthead parallel citations:** only the first 600 characters of page 1 are read, so a parallel citation printed later is not captured, by design (later text may cite other cases). The sample has no SCC citation in any masthead.
5. **Service of a judgment:** dominant mentions (at least 5, and at least twice the next service). Display and ranking only, never a filter, and not shown to users as a fact about the case.
6. **Hindi copies** are nested but still searchable and represented in their groups. The reliability flag is the reader stream's.
7. **Local environment:** the vendored PDF.js (`wwwroot/vendor`, git-ignored) must exist for the UI to load. In a fresh worktree run `npm ci` and `node app/b1/web/vendor.mjs`, or copy a verified vendor folder (SHA256SUMS checked).
