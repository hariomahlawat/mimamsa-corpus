# 06. Responsive rules and system states

## 1. Responsive rules

Breakpoints (viewport width, tokens `layout.breakpoints`): tablet < 1280 (touch layout below 768 is out of scope), compact 1280–1599, standard 1600–2199, wide ≥ 2200. Fixed vertical chrome: banner 28 + top bar 40 + footer 24 = 92 px.

### 1.1 1366×768 (compact; usable height ~ 676 px in the browser minus chrome ~ 580 px)

- Default panes: **results + document**; rail collapsed to icons (48 px); context pane as an overlay drawer from the right (opens over the document, 320 px, pinned open on request, which then narrows the document).
- Results 340 px; document takes the rest (≥ 900 px).
- Facets open from the rail as a popover panel.
- PDF default zoom: fit width. Doc header compresses to one line with an expander.
- Row height dense (28 px). Tabs show icon + 12-character titles.

### 1.2 1920×1080 (standard reference)

- Four regions: rail 220, results 380, document flexible (~ 880), context 320. All dividers active.
- PDF default zoom: fit width in the document pane.

### 1.3 2560×1440 (wide)

- Rail 260, results 440, context 380; document gets the remainder but the **Text view keeps a 60–80 ch measure**, centred with margins used for pinned notes (the "margin" of the identity).
- Optional second document pane (split view) for compare or for keeping a statute open beside a judgment.
- Do not upscale type; increase content, not size.

### 1.4 Tablet (landscape 1024×768 to 1180×820; portrait read-only)

- Touch targets 44 px (`row_height_px.touch`); single main pane with a segmented control: Results · Document · Context.
- Swipe is never the only way to do anything; every gesture has a visible control.
- Administration upload and release import are hidden on tablets (desktop tasks); a notice says so.
- Portrait: Document reading only, with Results and Context as full-screen sheets.

### 1.5 General

- Zoom to 200% must work without loss of content (WCAG 1.4.4); at 400% the layout falls back to the tablet single-pane pattern (WCAG 1.4.10 reflow).
- Pane minimums (rail 200, results 320, document 480, context 280) define when a pane converts to a drawer.
- Print: document text or PDF page with banner header and footer citation on every page; no chrome.

## 2. States

Every data region has five explicit states. Skeletons are static (no shimmer); spinners appear only after 400 ms; progress shows real counts.

### 2.1 Loading

| Region | Behaviour |
| --- | --- |
| Search results | Keep previous results dimmed with "Searching…" text for up to 400 ms, then static skeleton rows; cancel on new keystrokes |
| Document | Header renders from metadata first; PDF page placeholder at the correct aspect ratio; page counter shows "loading page 12" |
| Context panels | Per-tab skeleton; Evidence panel never shows a guessed value while loading |
| Admin jobs | Progress text with counts and current step; no percentage unless computed from counts |

### 2.2 Empty

| Situation | Message |
| --- | --- |
| No results | "No published documents match. Try fewer filters, or search the words without the section number." Shows active filters with one-click removal. Never suggests external sources |
| No related / cited items, empty graph neighbourhood | `AbsenceNotice`: "No extracted links. This does not mean there is no related or adverse authority." |
| No notes / pins | One line of guidance with the shortcut |
| Staging queue empty (Admin) | "Nothing waiting for review." |
| Candidate value absent | "Not extracted" (never blank, never a dash that looks like zero) |

### 2.3 Error

- Plain language, what happened, what the user can do, and an error reference id (no stack traces, no document text).
- 403 for a User on an Admin route shows "This action is for Admins." and records nothing else on screen.
- PDF fails to render: offer the Text view and the provenance panel; state "The original could not be displayed in the browser"; never substitute a derived PDF silently.
- Release import failure: the wizard stops at the failing check, shows which check failed (by code, e.g. `CHECKSUM_MISMATCH`, `RESTRICTED_MATERIAL`, never the matched restricted value) and confirms "Nothing was changed."

### 2.4 Degraded

A `DegradedBanner` appears under the candidate banner (never replacing it) when:

| Condition | Text | Behaviour |
| --- | --- | --- |
| Semantic search unavailable (embedding service down or model hash mismatch) | "Semantic search is unavailable. Showing word matches only." | Search runs lexical only; match chips show Lexical |
| Index generation behind the database (if a separate BM25 index is adopted) | "Search index is updating. Results may be incomplete." | Blocks stale results per the generation check |
| OCR worker unavailable (Admin) | "OCR is paused. Uploads will wait in staging." | Uploads accepted, not processed |
| Server unreachable | "Connection to the server lost. Retrying." | Read-only cached view of open tabs; no writes |
| Release older than a site-set threshold | "The library was last updated on {date}." | Informational |
| Non-production certificate | "Not a production installation." | Persistent |

### 2.5 Gated

Gated workspaces (Commander assistant; as-of statute view; template drafting; document audit) render a full-pane `GateNotice` with: what the feature would do, why it is closed ("No Legal Reviewer is appointed and AUTH-LEDGER is at version 0"), what must happen to open it, and a link back to research. They never show sample outputs.

### 2.6 Withdrawn and superseded

- A link to a withdrawn document (Users) resolves to a notice "This document has been withdrawn from the library on {date}." with no content or snippets.
- A citation link to a superseded copy opens that copy with a notice and a link to the current copy (CAP-RW-04).
