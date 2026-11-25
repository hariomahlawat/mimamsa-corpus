# 05. Component inventory and keyboard standards

## 1. Component inventory

Each component lists its states. "All states" means default, hover, focus-visible, active, disabled, loading, error where applicable. Components consume tokens only (no literal colours).

### 1.1 Shell

| Component | Purpose | Notes |
| --- | --- | --- |
| `CandidateBanner` | Non-dismissable top band from release metadata | No close button; `role="status"`, announced once per session; repeats in print header |
| `TopBar` | Mark, workspace switcher, search, view toggle, user menu | Administration item rendered only for Admin |
| `WorkspaceSwitcher` | Research · Statutes · Graph · Studio · Assistant (locked) · Administration | Locked item opens the gate notice, not an error |
| `StatusFooter` | Release id, HF revision, connection, job count (Admin) | Text only |
| `LeftRail` | Contextual navigation and facets | Collapsible (B); icon mode at compact widths |
| `PaneLayout` + `PaneDivider` | Resizable panes | Keyboard resizable (§2.4); double-click divider resets; layout persisted per user |
| `TabStrip` | Document tabs | Overflow menu; drag to reorder; close button on hover/focus |
| `CommandPalette` | All actions by name (`:`) | Lists shortcuts; respects role (Admin actions absent for Users) |

### 1.2 Search and results

| Component | Purpose | Notes |
| --- | --- | --- |
| `SearchField` | Persistent query input | Parsed `QueryChip`s inline; Esc clears suggestions, second Esc returns focus to previous pane |
| `QueryChip` | Recognised identifier | Text: interpretation; × removes; Backspace on empty field edits last chip |
| `SearchRunLine` | "Hybrid · 3 filters · release R13-…" | Read-only |
| `ResultGroup` / `ResultRow` | Document group and passage excerpt | Page first; highlighted terms; `MatchReasonChip`s; `StatusChip`s |
| `FacetGroup` / `FacetItem` | Filters with counts | Checkbox semantics; counts in tabular figures |
| `SelectedFilters` | Active filter chips | "Clear all" |

### 1.3 Document

| Component | Purpose | Notes |
| --- | --- | --- |
| `DocHeader` | Printed title, court/issuer, dates, numbers | Each field with `OriginChip` |
| `ProceedingsStrip` | Proceedings and candidate outcomes | `CandidateValue` with `EvaluationPopover` |
| `PdfViewer` | PDF.js viewer | Hit nav, page input, zoom (fit width / page / %), rotate, Original/Text toggle; script and eval disabled |
| `HitNavigator` | Previous/next hit with count | N / Shift+N |
| `TextView` | Extracted text with page dividers | OCR label per page |
| `CopySwitcher` / `CompareView` | Alternate copies | Sync pages when possible |
| `CitationButton` | Copy legal citation (C) or internal reference (Shift+C) | Toast confirms text copied (no animation) |

### 1.4 Evidence and context

| Component | Purpose | Notes |
| --- | --- | --- |
| `AxisPanel` | Seven axis rows | Fixed order; each row expandable to basis and reference |
| `StatusChip` | Glyph + label + colour | Variants: candidate, checked, warning, error, gated, withdrawn |
| `OriginChip` | crawler · rule · LLM-derived · human · release import · Admin-entered | LLM-derived always spelled out |
| `CandidateValue` | Any derived value | Shows value, "Candidate", measured P/coverage or "not evaluated", "not human-checked" when so |
| `EvaluationPopover` | Report path, commit, figures, CI note, restriction, deferred findings | Read-only |
| `ProvenanceList` | Provenance fields | Hashes in mono with copy |
| `RelatedList`, `CitationList` | Related and cited/citing items | Relation type and confidence column |
| `NoteEditor`, `PinList` | Private notes and pins | Owner only; autosave with explicit "Saved" text |
| `AbsenceNotice` | "No extracted edges/citations. Not evidence of absence of authority." | Mandatory on empty related/cited/graph states |
| `GateNotice` | Explains closed legal gate | Lists conditions; links back to research |

### 1.5 Graph and statutes

| Component | Purpose | Notes |
| --- | --- | --- |
| `GraphCanvas` + `GraphListView` | Visual and list views kept in sync | List view is the keyboard/screen-reader primary |
| `EdgeInspector` | Edge type, confidence, extractor, evidence passage, page link | "Proposed, not verified" for non-citation edges |
| `EdgeLegend` | Types with per-type precision | "no human has checked this figure" where applicable |
| `TocTree` | Act/Rules table of contents | Tree semantics; type-ahead |
| `AmendmentStrip` | Footnote-derived candidate edges on a section | "Temporal chain not established" notice |

### 1.6 Administration (Admin only)

| Component | Purpose | Notes |
| --- | --- | --- |
| `UploadDropzone` | Add source files | Size/type limits stated up front; no client-side parsing |
| `StagingQueue` | Items by state (Processing, Review required, Failed, Rejected) | Table with filters |
| `StagingReview` | Original vs extracted text, OCR per page, metadata candidates, suggested links, eligibility decision | Publish disabled until eligibility recorded |
| `PublishDialog` | Confirm publication | Fixed text: "Visible to all users. Not legal approval." |
| `WithdrawDialog` | Confirm withdrawal with reason | States effect on search |
| `ReleaseImportWizard` | Pick a bundle from the fixed import drop folder → verify → import → smoke → switch | The browser never uploads bundles or names server paths; shows every check with pass/fail; any fail stops |
| `VerificationReport` | Signature, checksums, compatibility, register, records | Restricted hits by id only |
| `AccountTable`, `DesignationRegistry` | Accounts; inert designations | Designation page shows "inactive until appointed" |
| `AuditTable` | Metadata-only events | Filters; export CSV (metadata only) |

### 1.7 Feedback

`InlineMessage` (info, warning, error), `Toast` (text, no motion), `Skeleton` (static grey blocks, no shimmer), `ProgressText` ("Importing: 1,240 of 4,121 copies"), `EmptyState`, `ErrorState`, `DegradedBanner` (secondary band under the candidate banner, see 06).

## 2. Keyboard interaction standards

### 2.1 General rules

- Every action reachable by mouse is reachable by keyboard; visible focus always (`focus.ring`, 2 px).
- Tab order follows visual order: banner → top bar → rail → results → document → context → footer. `.` / `,` cycle panes (F6 is left to the browser).
- ARIA patterns: tabs (`tablist`), tree (TOC), grid (results tables), listbox (suggestions), dialog (modal, focus-trapped, Esc closes, focus returns).
- Shortcuts never use browser-reserved combinations (tested) and are listed in the command palette and in a `?` help sheet. Single-key shortcuts (`/`, `j`, `k`) work only when focus is not in a text field and can be turned off in user settings (WCAG 2.1.4).

### 2.2 Keymap (normative: `keymap.json`)

The keymap avoids every combination that Edge or Chrome on Windows reserves or may not pass to the page (`browser_reserved_keys.json`), including Ctrl+Shift+P/N/C/O/K, Ctrl+W/T/Tab/1–9, Ctrl+K/L/E/G, Alt+←/→, F3, F6, F12. `tests/test_keymap.py` fails the build on any collision. The reserved list must be re-confirmed in P9 on the deployed browser versions.

| Keys | Action | Scope |
| --- | --- | --- |
| `/` | Focus search | outside text fields |
| `?` | Shortcut help | outside text fields |
| `:` | Command palette | outside text fields |
| G then R / S / G / D / A | Research / Statutes / Graph / Studio / Administration | outside text fields |
| `.` / `,` | Next / previous pane | outside text fields |
| B / Shift+B | Toggle left rail / context pane | outside text fields |
| `]` / `[` | Next / previous app tab | outside text fields |
| Esc | Leave field, close popover | anywhere |

### 2.3 Results and documents

| Keys | Action |
| --- | --- |
| J / K or ↓ / ↑ | Next / previous result |
| Enter / O / Space | Open in current tab / new app tab / preview |
| N / Shift+N | Next / previous hit in document (browser F3 left native) |
| P | Go to page |
| C / Shift+C | Copy legal citation / copy internal reference and permalink |
| T | Toggle Original / Text |
| M | New note pinned to the current passage |
| E | Open Evidence panel |
| X | Close app tab |
| Alt+↓ (in search field) | Open suggestions |
| Ctrl+Enter (in search field) | Run search in a new app tab |

Single-key shortcuts are active only when focus is outside editable fields and can be turned off in user settings (WCAG 2.1.4). Pane cycling with `.`/`,` lands on dividers too.

### 2.4 Pane resizing

Focus a divider (F6 lands on dividers too); ← / → resize by 16 px, Shift+← / → by 64 px, Home / End collapse / expand, Enter resets.

### 2.5 Graph

List view is primary: ↑ / ↓ move between nodes, → expands neighbours, ← collapses, Enter opens the node, E opens the edge inspector for the selected edge. Canvas mirrors selection.
