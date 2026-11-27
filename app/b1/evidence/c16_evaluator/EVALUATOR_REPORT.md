# C16 Tranche A / WP05: search evaluator optimisation, report

- **Branch:** `claude/c16-evaluator`, based on `legal-knowledge/v2.5-staging` at `c8fa5290`.
- **Result:** p95 with 10 concurrent readers at 10k documents is **81 ms (memory engine) and 58 ms (disk engine)**, against a target of ≤ 300 ms. Measured on the same host and with the same method, the C15 evaluator gave 633 ms and 461 ms. With `Page()` included (the full HTTP search path), the figures are 111 ms and 87 ms.
- **Exactness:** every output is **byte-identical** to the C15 evaluator. That covers 2,062 cases × 4 scales × 2 engines: every hit's passage, tier, score (round-trip) and reasons; chips, notes, highlight terms and phrases; facets; totals; and 15 `Page()` variants per case. The C# suite, Playwright and the retrieval oracle are unchanged.

## 1. Profile: where the time went (before)

**Method**
- Phase timers were added to a profiling build of the C15 `SearchService`. This build was not committed; the patch is in `raw/profile_instrumentation.diff`.
- The tool was IndexBench `--phase-profile`: 26 queries, 5 passes each, sequential, on the 10k site (246,020 passages).
- The figures are summed over the 26 per-query means. Nested sub-phases are shown separately.
- Raw files: `raw/profile-before-{memory,disk}-10000.json`.

| Phase | Memory engine | Disk engine |
| --- | --- | --- |
| Ordering the ranked tier: LINQ `OrderByDescending.ThenBy` over every match, plus one `Hit`, `LazyReasons` and closure per match | 408 ms (29%) | 377 ms (36%) |
| Scoring (`Eval` / `PlainScores`) | 367 ms (26%) | 188 ms (18%) |
| … of which per-term work: `Dictionary` tf accumulation | 82 ms | 31 ms |
| … of which per-term work: `Note()` (one dictionary entry per matched passage per display) | 129 ms | 76 ms |
| … of which posting-list fetch | ≈ 0 ms, cache hits | ≈ 0 ms, cache hits |
| Facets: `Distinct()` over every hit | 185 ms (13%) | 138 ms (13%) |
| `Page()`: iterates every `Hit` object twice | 168 ms (12%) | 140 ms (13%) |
| Withdrawal filter and filter/distinct: new `List<Hit>` and `Distinct()` | 160 ms (12%) | 125 ms (12%) |
| Identifier tiers, case name, title, speller | 99 ms (7%) | 81 ms (8%) |
| **Allocation per pass over 26 queries** | **706 MB** (court martial alone: 86 MB) | 706 MB |

**Findings**
1. **Storage is not the cost.** Posting fetch is effectively zero once the cache is warm. This confirms C15.
2. **About two-thirds of the time comes after scoring.** Each matching passage became a dictionary entry, a sorted LINQ element, a `Hit`, a `LazyReasons` with a closure, and an entry in two further lists and two `Distinct()` sets. `Page()` then walked all of them again.
3. **Allocation caused the concurrent collapse.** 10 to 86 MB per common query meant that 10 readers spent most of their time in GC: sequential p95 was 112 ms, while the 10-reader p95 was 633 ms.

## 2. Optimisations made, all exact

**Files changed:** `SearchService.cs` and `ProvisionHeadings.cs` (one seam). Nothing else in the evaluator changed.

| Change | Why it is exact |
| --- | --- |
| **Clause results are passage-ordered parallel arrays (`Scored`), not `Dictionary<int,double>`.** `AND` and `NEAR` are merge intersections; `NOT` is a merge difference; `OR`, multi-variant terms (stems, prefixes) and plain-word clauses are a **k-way heap merge** keyed by (passage, list index). | The heap yields one passage's contributions in list order, so every sum is formed as `0.0 + s₀ + s₁ …` in the operand order the dictionary used. The per-passage expressions are textually identical: coordination factor, `TfNorm`, phrase `+1000·st`, field scores, `act:` 0.5 + 1.0. No per-thread or corpus-sized state is held (a dense-array variant was tried and rejected for its memory at full scale). |
| **Deferred score explanations.** Each matched display keeps the clause's own (passage, count) arrays as segments. `Reasons(p)` sums them by binary search, and only for hits that are read. | The dictionary summed every note for (display, passage), and the segments sum the same numbers. A display takes its place in first-noted order when its first non-empty clause is noted, as before. `section:` registers its two displays in the order of their first passage. |
| **Ranked tier sorted once with a primitive key sort** (`Array.Sort(double[], int[])` on −score), then a tie pass that sorts equal-score runs by passage. The order is shared by the rerank, hybrid and tail steps. | This reproduces the stable `OrderByDescending(score).ThenBy(passage)` under `Comparer<double>` (0.0 and −0.0 compare equal). If a score were NaN, the original LINQ is used. |
| **Lazy hit list (`HitList`).** A ranked lexical hit is created on first read as `new Hit(p, "lexical", score, Reasons(p, ctx))` and then cached, so each index returns one object. Pinned, mention, case-name, title, heading-first, fused and reranked hits are created exactly as before. | Same values. A service-preference rescore of an explicit hit is `h with { Score }`, as before. |
| **Withdrawal, filters, facets and document counts work per document** (`sbyte`/`bool` per document), not per hit with `Distinct()`. | Withdrawal is still applied after ranking and before facets, counts and paging, for every tier. Each facet's values are fully ordered (by count then value, or by value), so the order in which documents are visited cannot change the output. |
| **`Page()` reads passage indexes from the hit list** and creates `Hit` objects only for the page. | The grouping, representative, sort and lead/per-group logic is unchanged. |
| **NEAR span source:** an operand's posting lists are resolved once per NEAR evaluation instead of once per candidate passage. | The lists, positions and span lists are the same. The exception for an unsupported operand is still raised at the first candidate passage. |
| **Statute title-word sets cached per index** for the short-title tier. | `NormTitle` is deterministic, and the comparison (`SetEquals`) is the same. |
| **`ProvisionHeadings.Picks`.** The boost rule, factored out so it can be applied to the arrays. `Boost()` delegates to it. | The arithmetic and order are unchanged. The existing `Boost` tests still pass, including `Assert.Same` when there is no cue. |

**Evaluated and not adopted**
- **WAND or MaxScore pruning, and bounded-heap top-k.** The contract returns every filtered hit in relevance order: `TotalPassages`, facets, document groups with per-group counts, the `new`/`old` sorts and every page beyond the first all depend on the full match set. Pruning cannot give exact totals or facets. Once the per-match cost was reduced to arrays, a full primitive sort costs about 5–8 ms at 100k matches, so top-k was not needed.
- **Bounded text retrieval.**
  - The evaluator reads passage text only in these places:
    - the identifier tier (`ProvisionStrength` over the scoped statute's passages, behind the existing substring guard);
    - phrase provision checks;
    - `section:`;
    - the rerank pool (bounded by `RerankPool`).
  - Reasons and paging read no text, and snippets are built by the API for page hits only.
  - A postings-based prefilter for `ProvisionStrength` would **not** be exact. The tokenizer keeps `section69` as one token, which the reference regex matches. So it was left unchanged.
  - Nothing here changes how `GenerationStore` holds text (WP04's area).

## 3. Parity (byte for byte)

**Harness**
- `IndexBench --parity` (new, `bench/IndexBench/Parity.cs`) writes full output signatures for **2,062 cases**:
  - **Queries (101):**
    - the 26 benchmark queries;
    - the **43 C14 walkthrough queries**, with Q42's filter parameters;
    - 59 additional queries covering:
      - phrases, `NEAR` (including `NEAR` over `OR` and phrases), `NOT`, `AND NOT`, `OR`, prefix and `exact:`;
      - every field: title, party, judge, court, bench, type, case, citation, date range, year, section, rule and act;
      - identifiers and citations: section, rule, regulation, OA, neutral, SCC, AIR and writ;
      - natural language, abbreviations and stopwords;
      - empty results and parser errors.
  - **Variants of each query:**
    - lexical;
    - provision headings on;
    - hybrid hook (deterministic stand-in scorer);
    - rerank hook (deterministic stand-in reranker);
    - service preference, army and navy (including hybrid);
    - plain-after-confirmation;
    - two extra filter sets;
    - each with and without a withdrawal set of about 14% of documents.
- **Recorded per case:**
  - state, mode, error and position, chips, notes, highlight terms and phrases in order, facets and totals;
  - a SHA-256 over every hit (passage:tier:round-trip score:all reasons), with the first 30 hits verbatim;
  - 15 `Page()` variants: sort relevance, new and old × page sizes 25, 100 and 7 × pages 1, 2, last, beyond-last and 0. Each is hashed over every group, variant, page hit, reason and count.

| Scale | Engine | Cases | Identical | Different | Hits compared | Signature files byte-identical |
| --- | --- | --- | --- | --- | --- | --- |
| 290 (real sample, fixed regression set) | memory | 2,062 | 2,062 | 0 | 5,504,083 | yes |
| 290 | disk | 2,062 | 2,062 | 0 | 5,504,083 | yes |
| 1k | memory / disk | 2,062 each | 2,062 each | 0 | 4,079,116 each | yes |
| 4k | memory / disk | 2,062 each | 2,062 each | 0 | 16,714,605 each | yes |
| 10k | memory / disk | 2,062 each | 2,062 each | 0 | 41,691,988 each | yes |

- The new memory and disk signatures are also byte-identical with each other at every scale.
- Details and SHA-256s are in `raw/parity_summary.json`. Outcomes: 1,755 results, 235 empty and 72 parser errors at 290; 1,613, 377 and 72 at 1k–10k.
- **Harness sensitivity check:** reversing only the tie order of equal scores made 316 of 516 cases differ at 290. The harness does detect ordering changes.

## 4. Benchmarks (before → after, same host, same method)

**Method**
- In-process IndexBench, Release, Server GC, run against the same synthetic sites and indexes.
- `before` is the C15 `Mimamsa.Core.dll` at `c8fa5290`; `after` is this branch. The harness binary is the same, built from this branch's `Program.cs`.
- Sequential: 26 queries × 3. Concurrent: N threads × 6 passes. These are the C15 settings (`--repeat 3 --readers 10,25`).
- Before and after ran back to back for each scale and engine.
- Synthetic sites were regenerated under `E:\Mimamsa-Data\bench\c16c\` with `build_scale_site.py` (pool of 220 sample documents).
- "Alloc" is managed bytes allocated per sequential query (new in IndexBench).

| Scale (passages) | Engine | Seq p50 / p95 before | Seq p50 / p95 after | 10 readers p95 before → after | 25 readers p95 before → after | Alloc per query before → after (MB) |
| --- | --- | --- | --- | --- | --- | --- |
| 290 (37,558) | memory | 2 / 14.9 ms | 0.9 / 7.4 ms | 62.3 → **12.2** ms | 79.7 → 15.6 ms | 2.38 → 0.47 |
| 290 (37,558) | disk | 2.4 / 16.2 ms | 1.2 / 7.8 ms | 50.5 → **11.8** ms | 63.8 → 13.5 ms | 2.37 → 0.47 |
| 1000 (24,030) | memory | 2.7 / 11.9 ms | 1.3 / 6.4 ms | 45.3 → **11.2** ms | 59 → 15.4 ms | 2.43 → 0.55 |
| 1000 (24,030) | disk | 2.3 / 12.6 ms | 1.5 / 6.6 ms | 40.2 → **11.4** ms | 47.2 → 12.3 ms | 2.42 → 0.55 |
| 4000 (98,486) | memory | 10.3 / 55.1 ms | 5.5 / 23.8 ms | 236.5 → **31.4** ms | 299.5 → 35.1 ms | 10.12 → 2.15 |
| 4000 (98,486) | disk | 9.9 / 61.7 ms | 4.6 / 20.9 ms | 152.3 → **25.9** ms | 198.3 → 28 ms | 10.09 → 2.15 |
| **10000 (246,020)** | memory | 24 / 112.2 ms | 9.8 / 51.4 ms | 632.6 → **81.3** ms | 1,509.3 → 96.8 ms | 23.73 → 5.01 |
| **10000 (246,020)** | disk | 16.1 / 141.1 ms | 8.1 / 66 ms | 460.6 → **57.6** ms | 535.4 → 73.1 ms | 23.72 → 5.01 |
| 10000, Search + `Page(1)` + page reasons | memory | 23.6 / 122.1 ms | 13.9 / 54.8 ms | 702.7 → **110.9** ms | 1,733.8 → 143.1 ms | 26.93 → 8.22 |
| 10000, Search + `Page(1)` + page reasons | disk | 17.6 / 123.2 ms | 13.4 / 78.6 ms | 468.4 → **87.3** ms | 574.2 → 105.9 ms | 26.92 → 8.22 |

**Target ≤ 300 ms p95 at 10 readers and 10k documents: met for both engines,** with or without paging.

**Host load**
- Load was sampled before and after each run (`raw/bench_run_log.txt`): 0–16% for the main matrix, and 26% at the start of one with-page run.
- During the earlier parity and test phases another stream was running Playwright on this host.
- The "before" 10k figures here (633 ms and 461 ms) are lower than C15's reported 1,494 ms and 1,166 ms, because C15's host was contended by three streams. The comparison in this report is before against after on the same host.

**Per-query medians at 10k** (memory engine, before → after; all in `raw/after-*-10000.json`):

| Query | Before | After | Alloc before → after |
| --- | --- | --- | --- |
| court martial | 112 ms | 58 ms | 77 → 13 MB |
| court marshal | 94 ms | 26 ms | 73 → 12 MB |
| natural justice court of inquiry | 84 ms | 41 ms | 78 → 13 MB |
| writ petition armed forces tribunal | 68 ms | 36 ms | 72 → 15 MB |
| s.69 Army Act (identifier tier, text regex) | 18 ms | 15 ms | — |
| title:army | 30 ms | 21 ms | 28 → 26 MB (title tokenised per document; §6) |

## 5. Tests

| Check | Result |
| --- | --- |
| C# suite, memory engine | **212/212** (207 existing + 5 new in `C16EvaluatorTests`) |
| C# suite, disk engine (`Mimamsa__Search__Engine=disk` for every spawned service, separate index directory) | **212/212** |
| Playwright journeys, memory engine | **81/81** |
| Playwright journeys, disk engine | **81/81** |
| Retrieval oracle (unchanged; blob `3884f86c…`; port 5722; database `c16c_oracle`) | **10/14 with hybrid off, 12/14 with hybrid on** (e5-small, floor 0.8579), as required. `raw/oracle/` |
| Regenerated evidence `.jpg` files | Restored, not committed |

**New tests (`C16EvaluatorTests`)**
- The ranked order is by score, then passage.
- A hit is the same object on every read, and pages carry those objects.
- A word repeated in the query sums its counts in the reason, as the C15 dictionary did.
- 64 concurrent searches equal the sequential signatures.
- Withdrawn documents are absent from hits, totals, document counts and page groups.

## 6. Open issues

- **`title:` (and the other metadata fields) tokenise every document's title or party for each query.** At 10k this is about 26 MB and 20 ms per query. It is exact and bounded by the number of documents, not passages, but a per-index token cache would remove it. Not done here, to keep the change set to the evaluator core.
- **Identifier tier for sections** (`s.69 Army Act`: 13–15 ms at 10k). It runs regexes over the passages of the scoped statute and over passages that mention the Act's name. That is exact and behind a substring guard. A token prefilter is not exact (§2).
- **Synthetic sites have a small vocabulary** (19,477 terms) and duplicated text. The real corpus will have longer posting lists for rare terms and more distinct terms. The array evaluator is linear in matches with a small constant, but the full-corpus figure is still a projection.
- **`Ranking` NaN fallback.** If a score is ever NaN, the original LINQ ordering is used; no NaN has been observed. This keeps exactness without assuming that NaN cannot occur.
- **The `wwwroot/vendor/pdfjs` bundle was missing in this worktree.** Without it the Playwright login page never rendered. It was vendored locally from an existing pinned `pdfjs-dist` 6.5.438 using `app/b1/web/vendor.mjs`; it is gitignored and not committed. Worktree setup for future streams should include this step.

## 7. Raw files

| File | Contents |
| --- | --- |
| `raw/profile-before-*.json` and `raw/profile_instrumentation.diff` | Profiling (§1) |
| `raw/{before,after}-{memory,disk}-{290,1000,4000,10000}.json` and `*-10000-withpage.json` | Benchmarks (§4) |
| `raw/bench_run_log.txt` | Timings and host-load samples |
| `raw/parity_summary.json` | Parity (§3). The 9–10 MB signature files themselves are not committed; they are regenerated with `IndexBench --parity <out> --walkthrough app/b1/evidence/c15_hybrid/scripts/queries.json` |
| `raw/oracle/` | Oracle outputs (§5) |
