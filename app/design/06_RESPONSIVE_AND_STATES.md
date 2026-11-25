# 06. Responsive rules and system states

## 1. Responsive rules

### 1.0 Effective CSS pixels and Windows display scaling

All breakpoints are **effective CSS pixels** = physical pixels ÷ Windows display scale (browser zoom divides further). Windows commonly defaults to 125% or 150% on laptops and 1080p office monitors, so layouts are chosen from the effective width, and the **touch layout is chosen by input type** (`(pointer: coarse) and (hover: none)`), **never by width**. A narrow desktop window stays a desktop layout.

Breakpoints (tokens `layout.breakpoints`): narrow < 1280, compact 1280–1599, standard 1600–2199, wide ≥ 2200.

| Physical | 100% | 125% | 150% | 175% |
| --- | --- | --- | --- | --- |
| 1366×768 | 1366 compact | 1093 narrow | 911 narrow | 781 narrow |
| 1920×1080 | 1920 standard | 1536 compact | 1280 compact | 1097 narrow |
| 2560×1440 | 2560 wide | 2048 standard | 1707 standard | 1463 compact |

(Effective width in CSS px and resulting layout, fine pointer. `tests/test_tokens.py` checks every cell keeps a desktop layout with a document pane ≥ 480 px.)

Pane collapse order as width falls: rail → icons (48 px) below *standard*; context → right drawer when results + document + context minimums do not fit; results → left drawer when results + document do not fit. The document pane never goes below 480 px; below that (e.g. 781 CSS px) the results pane is a drawer and the document fills the width.

**Vertical budget.** Chrome: banner 28 (condensed 20) + top bar 40 + footer 24 CSS px, plus browser UI (~120 physical px) and taskbar (~48 physical px). At 1366×768 and 125% that leaves ≈ 410 CSS px for content (tested ≥ 380). Therefore at *narrow* and whenever available height < 600 CSS px:
- the banner condenses to one 20 px line (full text in a tooltip and on every print page); it stays on every view and is never hidden;
- the top bar merges the workspace switcher into a menu;
- the footer hides and its content moves to the user menu;
- at browser zoom ≥ 200% the banner scrolls with the content instead of being sticky, and reappears at the top of every view and in print (WCAG 1.4.10 reflow; the "persistent" requirement is per view, not per scroll position).

### 1.1 Narrow (< 1280 CSS px: e.g. 1366×768 at 125%, 1920×1080 at 175%)

- Panes: **results drawer + document**, or results + document if ≥ 1093 CSS px allows results 320 + document 480 + rail 48; context as an overlay drawer from the right (320 px), pinnable.
- Facets open from the rail as a popover panel. Doc header compresses to one line with an expander.
- PDF default zoom: fit width. Row height dense (28 px). Tabs show icon + 12-character titles.

### 1.2 Compact (1280–1599: 1366×768 at 100%, 1920×1080 at 125–150%)

- Rail icons (48), results 340, document ≥ 600; context as drawer unless pinned (then results narrows to 320 and document shrinks to its minimum).

### 1.3 Standard (1600–2199: 1920×1080 at 100%, 2560×1440 at 125–150%)

- Four regions: rail 220, results 380, document flexible (~ 880 at 1920), context 320. All dividers active.

### 1.4 Wide (≥ 2200: 2560×1440 at 100%)

- Rail 260, results 440, context 380; document gets the remainder but the **Text view keeps a 60–80 ch measure**, centred with margins used for pinned notes.
- Optional second document pane (split view). Do not upscale type; increase content, not size.

### 1.5 Tablet (coarse pointer, any width; landscape 1024×768 to 1180×820; portrait read-only)

- Touch targets 44 px; single main pane with a segmented control: Results · Document · Context.
- Swipe is never the only way to do anything. Administration upload and release import are hidden (desktop tasks); a notice says so.
- Portrait: Document reading only, with Results and Context as full-screen sheets.

### 1.6 General

- Zoom to 200% without loss of content (WCAG 1.4.4); at 400% the narrow single-pane pattern applies (WCAG 1.4.10), not the touch layout.
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
| Server unreachable | "Connection to the server lost. Retrying." | No cached content is shown (shared-desktop policy, `policies/client_state_and_cache.json`); open views are blanked to a reconnecting notice; no writes |
| Release older than a site-set threshold | "The library was last updated on {date}." | Informational |
| Non-production certificate | "Not a production installation." | Persistent |

### 2.5 Gated

Gated workspaces (Commander assistant; as-of statute view; template drafting; document audit) render a full-pane `GateNotice` with: what the feature would do, why it is closed ("No Legal Reviewer is appointed and AUTH-LEDGER is at version 0"), what must happen to open it, and a link back to research. They never show sample outputs.

### 2.6 Withdrawn and superseded

- A link to a withdrawn, restricted or unknown document (Users) resolves to one identical notice, "This document is not available in this installation.", with no content or snippets (non-disclosure, security architecture §7.3).
- **Citation links (CAP-RW-04, UX-12; ASR-E06 resolved; review E7–E9).** A citation permalink names a release, document, source-copy hash prefix and physical page. Resolution follows `policies/citation_resolution.json` (reference implementation `cite()` in `app/importer`):
  - **Cited copy eligible and current:** opens the exact cited copy at the cited physical page.
  - **Cited copy eligible but not current** (verified in an earlier release, still held, not withdrawn or restricted, for example replaced by a repaginated edition): opens the **exact cited copy** at the cited page, with the notice "This copy is not the current edition in the library." **Open current edition** is a separate action; **Compare** is offered where the copies are linked. The cited page number is never applied to a different copy.
  - **Cited copy unavailable** (withdrawn, restricted or not held): one identical notice for all three, "The cited copy is not available in this installation." No content, date, reason or current-edition offer. This states the limitation without disclosing which case applies (security architecture §7.3 non-disclosure). Admins see the reason only in the Admin withdrawal/audit view.
  - **Cited page not in the copy**, **ambiguous reference** (the hash prefix matches more than one held copy; a single full-hash match is required) and **document/copy mismatch**: a specific notice and no content. No clamping, no fallback to page 1 and no guessing by title or number.
  - In every case the copied citation and internal reference keep the original copy hash and page.
