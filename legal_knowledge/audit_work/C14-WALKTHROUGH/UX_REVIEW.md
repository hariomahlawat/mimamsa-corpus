# B1 walkthrough: visual and UX review (C14)

**Benchmark.** B1 is judged against what a professional legal-research product would offer, such as SCC Online, Manupatra or Westlaw-class tools, not against its own prototype brief. The comparison is about behaviour and layout only: B1 deliberately has no commercial content or headnotes.

**Evidence.** Screenshots in `screenshots/` (index: `SCREENSHOT_INDEX.md`), taken at 1366×768, 1920×1080 and 2560×1440 in headless Chromium at device scale 1.

## 1. Overall judgement

B1 is **trustworthy, clear and honest about uncertainty**, which is its strongest quality:
- seven evidence axes on every document;
- candidates always labelled;
- absence notices;
- exact, copy-pinned citations.

It looks like a careful engineering prototype, not yet like a professional research tool:
- density is low;
- duplicate entries clutter results and the Statutes list;
- the reading flow needs extra scrolling;
- there is no dashboard or research memory (history, notes, saved searches).

For *prolonged* research, the main costs are scrolling and re-finding, not the visual design.

| Dimension | Rating | Basis |
| --- | --- | --- |
| Professional appearance | Good | Restrained palette and consistent tokens; clear type hierarchy in document headers; dark theme complete (`J09-dark-document`) |
| Information hierarchy | Mixed | Document headers are excellent. Result cards give equal weight to provenance (source host, copy hash, retrieval date) and to the legal content (`J03-results`) |
| Navigation efficiency | Mixed | Keyboard map, palette, deep links and permalinks are strong. Missing: pagination (F10), scroll-to-passage (F12), instrument grouping (F11) |
| Readability of legal documents | Good (English) / Poor (Hindi) | PDF.js at fit width is crisp. The Text view has page markers. Hindi text is garbled (F07) |
| Screen-space use | Weak at 1366, fair at 1920, good at 2560 | One result visible at 1366×768 (F13). Two permanent banners about 52 px. An empty "No document open" pane takes about half the width until a document is opened |
| Information density | Low | About 3 passages per screen at 1920 in grouped mode. Snippets of about 60 words. Provenance repeated on every group |
| Search-result presentation | Good structure, weak triage | Identifier and Lexical chips, match reasons ("Matched: 'pension' (11)") and page numbers are excellent. No document-level summary line (court, date, outcome) that can be scanned without reading snippets |
| Accessibility and keyboard | Good (automated) | Landmarks, names and logical tab order; no positive tabindex; screen-reader mode. Not tested: NVDA/JAWS, zoom 200/400% |
| Consistency | Good | Same chip, button and table styles throughout. Exceptions: raw facet codes (`in_force`), upper-case schedule titles (F16, F11) |
| Suitability for prolonged research | Fair | No history, notes, pins or saved searches (B3). A cited copy reopens exactly, including after reload, which is excellent |

## 2. Screen-by-screen

**Sign-in** (`J01-signin`)
- Clear and appropriately serious.
- It states the lockout and session rules up front.
- No issue.

**Landing / research home** (`J01-landing-user`)
- Three empty panes and search tips.
- A professional tool would show at least:
  - what is in the library (counts by type and court, release date);
  - recent searches and documents;
  - quick links to the main statutes.
- **P3.** Proposed as a small "Library home" in WP5.

**Results** (`J03-results`, `J07-results`)
- **Strengths:**
  - the identifier chip and pinned provision;
  - honest head line ("showing the first 200 passages", "semantic search not part of B1");
  - sort options;
  - facets with counts.
- **Weaknesses:**
  - Hindi duplicate at rank 2;
  - per-group provenance block of 4 lines;
  - snippets not trimmed to the hit sentence;
  - the year placeholder reads like an applied filter (F16);
  - no pagination (F10).

**Document** (`J03-document`, `J04-judgment`)
- **Header:** dense but legible, with each field's origin labelled ("crawler", "rule").
- **Toolbar:** complete (hit navigation, page box, zoom, Fit width, Copy citation, Internal ref, Evidence).
- **Gaps:**
  - the cited passage is not scrolled into view (F12);
  - no "fit page";
  - no thumbnail or outline rail in the Research viewer for long Acts. The Statutes workspace has a TOC; whether it is linked from a document opened through Research was not checked.

**Context pane** (`J04-tab-*`)
- Seven axes with clear badges.
- Provenance is complete.
- Cited/Citing lists candidates honestly, but "Unresolved reference" rows add noise without context. Showing the raw citation text would help.

**Statutes** (`J06-statutes-home`, `J06-army-act-s75`)
- **The s.75 page is the best screen in the product:**
  - omission text;
  - compilation caveat;
  - A4 candidates with effective-from/to reasoning;
  - as-of control closed with the reason.
- **The list page is the weakest:**
  - duplicates and inconsistent titles (F11);
  - no filter box;
  - no grouping by service (Army / Navy / Air Force / criminal codes / tribunal);
  - empty right pane.

**Commander view** (`J09-commander-*`)
- Hides two facets and the context pane.
- It doesn't yet give commanders anything specific (F18).

**Administration** (`J12-overview`)
- A clear verification summary.
- The withdraw form has a proper confirmation dialog and "not legal approval" wording.
- No reinstatement (F17).
- No audit-log viewer, although the data exists in the `audit_log` table.

**State screens** (`J08-*`, `J15-outage`)
- The empty, parser-error and ambiguous states are exemplary: they explain, never guess, and offer a safe next action.
- The outage state clears views and recovers automatically.

## 3. Layout measurements (J10)

| Viewport | Results pane | Results fully visible | Document pane | PDF width | Overflow |
| --- | --- | --- | --- | --- | --- |
| 1366×768 | 360 px | 1 | 952 px | 904 px | none |
| 1920×1080 | 400 px | 4 | 968 px | 920 px | none |
| 2560×1440 | 400 px | 5 | 1608 px | 1530 px | none |

**Observations:**
- **1920:** the results pane is fixed at about 400 px while the context pane takes about 320 px, so the reading pane is about 50% of the width.
- **2560:** the PDF is scaled to 1530 px, which is larger than a reader needs. A max reading width, or a second page side by side, would use the space better.

## 4. Recommendations (to WP5 unless noted)

1. **Results:** compact density mode, and provenance collapsed into a single "source ▸" line (F13).
2. **Reading:** scroll to the first highlight on open (F12); add "fit page".
3. **Library home:** corpus summary, recent items and statute shortcuts.
4. **Statutes list:** group by service and instrument, with editions and languages nested; add a filter box (F11).
5. **Banners:** merge into one line, keeping both statements.
6. **Facets:** readable labels; year hint text (F16).
7. **Legal citation:** for statutes, add the section (e.g. "s. 69") alongside the page.
8. **Hindi:** language marker in document headers; hide unreliable Hindi text from default ranking (F07, WP3).
