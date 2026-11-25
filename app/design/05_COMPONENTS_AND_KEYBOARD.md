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
| `LeftRail` | Contextual navigation and facets | Collapsible (Ctrl+B); icon mode at compact widths |
| `PaneLayout` + `PaneDivider` | Resizable panes | Keyboard resizable (§2.4); double-click divider resets; layout persisted per user |
| `TabStrip` | Document tabs | Overflow menu; drag to reorder; close button on hover/focus |
| `CommandPalette` | All actions by name (Ctrl+Shift+P) | Lists shortcuts; respects role (Admin actions absent for Users) |

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
| `HitNavigator` | Previous/next hit with count | F3 / Shift+F3 |
| `TextView` | Extracted text with page dividers | OCR label per page |
| `CopySwitcher` / `CompareView` | Alternate copies | Sync pages when possible |
| `CitationButton` | Copy citation and permalink | Toast confirms text copied (no animation) |

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
| `ReleaseImportWizard` | Verify → import → smoke → switch | Shows every check with pass/fail; any fail stops |
| `VerificationReport` | Signature, checksums, compatibility, register, records | Restricted hits by id only |
| `AccountTable`, `DesignationRegistry` | Accounts; inert designations | Designation page shows "inactive until appointed" |
| `AuditTable` | Metadata-only events | Filters; export CSV (metadata only) |

### 1.7 Feedback

`InlineMessage` (info, warning, error), `Toast` (text, no motion), `Skeleton` (static grey blocks, no shimmer), `ProgressText` ("Importing: 1,240 of 4,121 copies"), `EmptyState`, `ErrorState`, `DegradedBanner` (secondary band under the candidate banner, see 06).

## 2. Keyboard interaction standards

### 2.1 General rules

- Every action reachable by mouse is reachable by keyboard; visible focus always (`focus.ring`, 2 px).
- Tab order follows visual order: banner → top bar → rail → results → document → context → footer. F6 / Shift+F6 cycles panes.
- ARIA patterns: tabs (`tablist`), tree (TOC), grid (results tables), listbox (suggestions), dialog (modal, focus-trapped, Esc closes, focus returns).
- Shortcuts avoid browser-reserved combinations where possible and are listed in the command palette and in a `?` help sheet. Single-key shortcuts (`/`, `j`, `k`) work only when focus is not in a text field and can be turned off in user settings (WCAG 2.1.4).

### 2.2 Global

| Keys | Action |
| --- | --- |
| Ctrl+K or `/` | Focus search |
| Ctrl+Shift+P | Command palette |
| F6 / Shift+F6 | Next / previous pane |
| Ctrl+B | Toggle left rail |
| Ctrl+Alt+→ / ← | Toggle context pane / results pane |
| Ctrl+1…5 | Switch workspace (Research, Statutes, Graph, Studio, Administration) |
| ? | Shortcut help |

### 2.3 Results and documents

| Keys | Action |
| --- | --- |
| ↑ / ↓ or `k` / `j` | Previous / next result |
| Enter / Ctrl+Enter / Space | Open in tab / open in new tab / preview |
| F3 / Shift+F3 | Next / previous hit in document |
| Ctrl+G | Go to page |
| Ctrl+Shift+C | Copy citation |
| Ctrl+Shift+O | Toggle Original / Text |
| Ctrl+W / Ctrl+Tab / Ctrl+Shift+Tab | Close / next / previous tab (when focus is in the app; browser may reserve these, so Alt+W / Alt+→ / Alt+← are provided as alternates) |
| Ctrl+Shift+N | New note pinned to the current passage |
| Ctrl+Shift+E | Open Evidence tab |

### 2.4 Pane resizing

Focus a divider (F6 lands on dividers too); ← / → resize by 16 px, Shift+← / → by 64 px, Home / End collapse / expand, Enter resets.

### 2.5 Graph

List view is primary: ↑ / ↓ move between nodes, → expands neighbours, ← collapses, Enter opens the node, E opens the edge inspector for the selected edge. Canvas mirrors selection.
