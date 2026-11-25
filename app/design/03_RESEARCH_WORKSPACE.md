# 03. Research workspace

The research workspace is the default screen and the core of the product (CAP-US-*, CAP-RW-*, CAP-JI-*).

## 1. Layout (1920×1080, practitioner view)

```
┌ Banner: Research and candidate data. Not legally verified. AUTH-LEDGER v0 · Release R13-…  ┐ 28
├ [M] Research Statutes Graph Studio Assistant🔒 Admin │ [ s.69 Army Act ×][court martial ×] ⌕ │ Practitioner ▾ │ user ┤ 40
├──────────┬───────────────────────┬─┬─────────────────────────────────────┬─┬──────────────────┤
│ RAIL     │ RESULTS               │║│ DOCUMENT  [tab1][tab2][tab3]  ×    │║│ CONTEXT          │
│ Saved    │ 1,284 passages · 312  │║│ ┌ header: title · court · date ──┐ │║│ [Evidence]       │
│  searches│ documents             │║│ │ case nos · chips per field      │ │║│ [Provenance]     │
│ Sets     │ Sort: relevance ▾     │║│ └─────────────────────────────────┘ │║│ [Related]        │
│ Pins     │ ───────────────────── │║│ Toolbar: ◀ hit 3/17 ▶ · page 12/40 │║│ [Cited/Citing]   │
│          │ ▸ Title of judgment   │║│  · Original | Text · zoom · copy   │║│ [Notes]          │
│ FACETS   │   AFT PB · 2019 · OA… │║│ ┌───────────────────────────────┐   │║│                  │
│ Type     │   p.12 "…the court    │║│ │                               │   │║│ Seven axis rows  │
│ Court    │   martial was…" [OCR] │║│ │   PDF.js page with            │   │║│ each: value ·    │
│ Year     │   ⓒ candidate         │║│ │   highlighted hit             │   │║│ basis · ref      │
│ Statute  │ ▸ …                   │║│ │                               │   │║│                  │
│ Outcome* │                       │║│ └───────────────────────────────┘   │║│                  │
│ OCR qual │                       │║│                                     │║│                  │
├──────────┴───────────────────────┴─┴─────────────────────────────────────┴─┴──────────────────┤
└ Release R13-… · HF 3864faf3 · connected                                                        ┘ 24
```

`║` = draggable divider (6 px hit area, 1 px visible rule). Minimum pane widths: rail 200, results 320, document 480, context 280 (tokens `layout.pane_min_px`).

## 2. Persistent search

- Always in the top bar; `/` focuses it from anywhere outside a text field (keymap in `keymap.json`, conflict-free with Edge/Chrome reserved keys).
- **Parsed query chips:** recognised identifiers (section, rule, case number, neutral citation, year, court) become removable chips showing how they were read ("Section 69 · Army Act 1950"). Unrecognised text stays free text. The user can turn a chip back into text.
- **Modes:** default hybrid; explicit `"phrase"`; `exact:` prefix forces lexical only. A small "how this search ran" line under the result count states mode, filters and release.
- **Suggestions:** recent queries and search history are stored **server-side per user** (never in browser storage; client policy `policies/client_state_and_cache.json`), plus identifier completions from the published corpus; never from staged or withdrawn items.
- **Query syntax (professional search):**

  | Feature | Syntax | Example |
  | --- | --- | --- |
  | Boolean | `AND`, `OR`, `NOT` (upper case), parentheses; default operator AND | `(desertion OR "absent without leave") AND NOT pension` |
  | Phrase | `"…"` | `"summary of evidence"` |
  | Proximity | `NEAR/n` between terms or phrases (within n words, any order); `"a b"~n` as alternative | `"court martial" NEAR/10 delay` |
  | Prefix | `term*` (minimum 3 characters) | `invalid*` |
  | Field search | `field:value`; fields `title:`, `party:`, `judge:`, `court:`, `bench:`, `case:`, `citation:`, `section:`, `act:`, `type:`, `date:` with ranges `date:2019-01-01..2021-12-31` or `year:2015..2020` | `judge:"Example" section:69 act:"Army Act 1950"` |
  | Exact lexical | `exact:` prefix disables semantic expansion | `exact:"Rule 22(3)(a)"` |

  The parser shows its reading as chips ("Judge = Example", "Section 69 · Army Act 1950", "NEAR/10"); a malformed query is shown with the error position and run as plain words only after the user confirms. Field and Boolean queries run lexically (FTS); semantic expansion applies only to free-text clauses. Performance target for all query types: p95 < 1 s at 10 concurrent queries on reference hardware without reducing accuracy (P2).
- Search text is never logged server-side (security architecture §10).

## 3. Results pane

- **Grouping:** passages grouped by document by default (toggle to flat passages). Each document group shows title, type, court/bench or issuer, date, case numbers, and up to three passage excerpts.
- **Excerpt row:** page number first ("p.12"), excerpt with highlighted matched terms (`highlight.search`), match-reason chips (Lexical, Semantic, Identifier), and status chips: `OCR` (if the passage is OCR-derived), `Low OCR confidence`, `Candidate` (for derived fields shown).
- **Why relevant:** a one-line explanation from data only, e.g. "Matched: 'court martial' (3), Section 69 Army Act cited on p.12". No relevance score number, no "binding" or "leading case" badge.
- **Sort:** relevance, date (new/old), court. No sort by citation count in Cycle 13.
- **Selection:** ↑/↓ or J/K moves, Enter opens in the current tab, O in a new app tab, Space previews in the document pane without adding a tab.
- **Chip budget (F22):** at most two chips per excerpt row (one match reason, one state); further states collapse into a single "+n" state cell that expands on focus. Glyph shapes are distinct (see 04 §3.1).

## 4. Facets

Left rail, below saved items. Each facet: title, counts, "show more", search-within-facet for long lists. Facets: Document type, Court/Bench, Year (range), Statute cited (normalised), Publication state (Admin only sees staged), OCR quality, Candidate outcome label (labelled "candidate"; hidden if the owner decides under D-08). Selected facets appear as chips under the search field. Counts update in place without layout shift.

## 5. Document pane and tabs

- **Tabs:** up to 12 open documents; overflow menu; tab shows type glyph + short title; middle-click or X closes; tabs and scroll positions persist per user **on the server** (not in browser storage).
- **Header:** title as printed; court/bench or issuer; date(s); case numbers; neutral citation; each field followed by a small origin chip (`crawler`, `rule`, `LLM-derived`, `human`) and, on hover, its evidence fidelity.
- **Proceedings strip (judgments):** list of proceedings with candidate outcome chips: "Dismissed · candidate · P 95.6% / cov 54.6% · V3 · not human-checked" (figures only from the record's `evaluation_ref`; "not evaluated" otherwise).
- **Viewer (PDF.js):** original bytes; page thumbnails optional; hit navigation (◀ ▶, N / Shift+N; the browser's own F3 find is left alone) across all hits in the document; native PDFs highlight from the text layer with `pdf.highlight.search`; scans overlay OCR word boxes in `pdf.highlight.ocr` **with a dashed `pdf.highlight.ocr-outline`**, so OCR-derived positions differ by shape as well as hue; legend "Highlight from OCR boxes". PDF highlight tokens are theme-independent because pages render on white in both themes.
- **Original / Text toggle:** the Text view shows the extracted text with `[[page N]]` markers rendered as page dividers; OCR pages carry the "for search only" label.
- **Copy citation** (C): copies a **legal citation** in the conventional order, built only from printed or rule/crawler metadata (LLM-derived fields are never used; absent parts are omitted, never guessed): *Case name (petitioner v. respondent) or title, neutral citation (else reported citation, else case number), (Court, date), para N* where the judgment prints numbered paragraphs, otherwise *p. N*. Example shape: `A v. Union of India, 20XX INSC NNN (Supreme Court of India, 1 January 20XX), para 12`. Reference implementation and tests: `app/contract/mimamsa_contract/citation.py`.
- **Copy internal reference** (Shift+C): `[doc_id · copy sha256[:12] · p.N · release id]` plus the permalink, for provenance; never mixed into the legal citation. Never copies OCR text as a quotation without the label.
- **Export (research sets and selections):** citation list as plain text and CSV (legal citation, internal reference, permalink), with the banner text as header.
- **Copies switcher:** when alternate copies exist; side-by-side compare (two viewers, synchronised pages when page counts match).

## 6. Context pane

Tabs: Evidence · Provenance · Related · Cited/Citing · Notes.

### 6.1 Evidence-status panel

Seven rows, always in this order, never collapsed into one summary:

| Axis | Shows |
| --- | --- |
| Source integrity | value chip + basis ("re-hashed at HF 5524c3d9") |
| Source authenticity | value chip + policy v1 fields (document authority, carrier provenance, copy fidelity, amendment chain status) |
| Evidence fidelity | value chip + what was checked |
| Legal applicability | value chip ("Not established" in Cycle 13) |
| Legal approval | value chip ("T0 Research only") + gate explanation |
| Publication | value chip + who/when (Admin view) |
| Dependency freshness | value chip |

Each row expands to the basis text and evidence reference link. Chips use text + glyph + colour (never colour alone).

### 6.2 Provenance panel

Source URL (copyable, not clickable on the offline LAN), retrieved at, sha256 (full, copy button), HF repo + revision + path, release id and generation, pipeline and OCR versions, aliases, alternate copies, access marking, completeness flags, publication history (Admin sees actor; Users see dates).

### 6.3 Related

Same-judgment copies, same-case proceedings, documents citing or cited by this one, judgments citing the same section; each with relation type and confidence class.

### 6.4 Cited / Citing

Statutes cited (normalised, link to section), cases cited (resolved or raw), citing documents. Each item opens its evidence passage. Header line: "Extracted citations: candidates. Absence of a citation is not absence of authority."

### 6.5 Notes

Private notes and pins for the current document; each pin stores the anchor (copy, page, passage). Notes are plain text with simple formatting; never shared; never searched by others.

## 7. Commander presentation (CAP-CA-04)

Same data and permissions, different layout: results and document only (context collapsed to an "Evidence" drawer), larger excerpts (`font.reading` 16 px), facets reduced to Type and Year, provenance one click away. The banner and all candidate chips remain. No summaries, no generated text.

## 8. Statute workspace (summary)

TOC tree in the rail; section pane shows section text with page anchors, an **amendment strip** listing footnote-derived candidate edges ("Omitted by … — candidate, evidence p.N") and a chain notice "Temporal chain not established", plus tabs for related judgments and implementing instruments. The as-of date control is visible but disabled with the gate notice (CAP-SE-03).

## 9. Graph workspace (summary)

Canvas (Cytoscape.js) with a synchronised list view for keyboard and screen-reader users. Edges: solid for citation types, dashed with an open-circle marker for proposed (non-citation) types, each labelled. Legend lists edge types with per-type measured precision or "not evaluated" and the note "no human has checked this figure" where applicable. Empty neighbourhood state: "No extracted edges. This does not mean there is no related or adverse authority."
