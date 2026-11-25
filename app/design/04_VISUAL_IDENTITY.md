# 04. Visual identity, typography, colour, spacing

All values are tokens in [`tokens/design-tokens.json`](tokens/design-tokens.json); `tests/test_tokens.py` checks contrast and integrity in CI.

## 1. Identity: "Ledger and Margin"

*Mimamsa* means disciplined inquiry into the meaning of texts. The identity borrows from the physical working copy of a law book: a warm paper ground, dark ink, ruled lines, and notes in the margin. It signals a reading instrument, not a dashboard.

- **Mark:** a wordmark "Mimamsa" set in the UI font at semibold, preceded by a simple glyph of two vertical rules with a short horizontal tick between them (a text column and its margin note). Drawn as an inline SVG, single colour (`fg.primary`), 16 px tall in the top bar. No emblem, crest, flag, service insignia or seal. It must not resemble any government, service or vendor mark.
- **Ground:** `bg.canvas` paper (#F6F5F1) behind panes; panes are `bg.surface` white with hairline `border.subtle` rules. Dark theme for long reading sessions mirrors the same structure.
- **One accent:** `accent.interactive` (lapis blue, #2B5A8C) only for interactive elements: links, primary buttons, focused/selected states. Status colours are reserved for status chips and never used decoratively.
- **Rules not boxes:** separation by 1 px rules and spacing; no card shadows; elevation only for overlays (menus, dialogs).
- **Geometry:** radius 0 for panes, 2 px for controls and chips, 4 px maximum for overlays.
- **Motion:** none decorative. State feedback at 120 ms (e.g. pane divider snap, chip expand) and disabled entirely under `prefers-reduced-motion`.
- **Imagery:** none. The only images are the user's documents.

## 2. Typography

System fonts available on Windows clients; no fonts are shipped or fetched.

| Role | Stack | Size / line height | Use |
| --- | --- | --- | --- |
| UI | Segoe UI, system-ui, Noto Sans, Arial | 14 px / 1.35 (13 px dense tables) | Chrome, lists, forms, chips |
| Reading | Cambria, Noto Serif, Georgia | 16 px / 1.55; measure 60–80 ch | Extracted text view, excerpts in commander view, notes |
| Mono | Cascadia Mono, Consolas | 13 px | sha256, doc ids, citations, case numbers when shown as identifiers |
| Devanagari | Nirmala UI, Noto Sans Devanagari, Mangal | as UI | Hindi titles and text |

Scale (px): 12 · 13 · 14 · 16 · 18 · 21 · 25. Weights: 400 and 600 only. Headings are sentence case. Numbers in tables use tabular figures (`font-variant-numeric: tabular-nums`). Identifiers never wrap mid-token; long hashes truncate in the middle with full value on hover and copy.

## 3. Colour system and contrast

Two themes (light, dark) with the same token names. Every text/background pair used by components is declared in `contrast_pairs` and must meet **WCAG 2.2 AA**: 4.5:1 for text, 3:1 for non-text UI (control borders, focus ring, graph edge lines). The CI test fails the build otherwise.

### 3.1 Semantic roles

| Token family | Meaning | Rule |
| --- | --- | --- |
| `bg.*`, `fg.*`, `border.*` | Neutral structure | `fg.muted` is still ≥ 4.5:1; there is no "light grey text" below AA |
| `accent.interactive` | Can be clicked or is selected | Not used for status |
| `focus.ring` | Keyboard focus | 2 px outline, 2 px offset, ≥ 3:1 against adjacent colours |
| `highlight.search` | Search hit in text and native PDF | Text over it stays `fg.primary` (≥ 4.5:1) |
| `highlight.ocr-box` | Hit drawn from OCR boxes on scans | Different hue from search highlight so users can tell derived positions apart |
| `status.candidate` | Automated, not verified (the default state of derived data) | Amber; glyph ◇; label "Candidate" |
| `status.checked` | Documentary checked (with review ref) | Teal; glyph ◆; label "Checked against source" (never "verified") |
| `status.warning` | Low OCR confidence, truncated at source, not evaluated | Orange-brown; glyph △ |
| `status.error` | Failure, rejection | Red; glyph ✕; Admin rejections show restriction id only |
| `status.gated` | Feature closed by the legal gate | Slate; glyph 🔒 rendered as a local SVG lock |
| `banner.*` | Candidate-data banner | Amber band with 2 px bottom rule |
| `edge.cites` / `edge.proposed` | Graph edges | Proposed edges are also dashed and labelled; colour is never the only cue |

### 3.2 Status is never colour alone

Every chip = glyph + text + colour. Tables include a text column for state. Graph edges carry a type label on hover/focus and in the list view. Print styles keep glyphs and text and add the banner text to every page header.

## 4. Spacing

4 px base with a 2 px half-step: 0, 2, 4, 6, 8, 12, 16, 24, 32 (`space.0`–`space.8`).

- Row heights: dense 28 px (tables, result lists), default 32 px, touch 44 px (tablet).
- Pane padding 12 px; section gaps 16 px; between-group gaps 24 px; 32 px only for dialog padding.
- No empty hero areas; no centred narrow columns on wide screens except the reading text measure.

## 5. Iconography

A small local SVG set (stroke 1.5 px, 16 px grid, square caps): search, filter, tab, close, pin, note, copy, cite, external-source (non-clickable), page, hit-previous, hit-next, graph, statute, judgment, upload, publish, withdraw, release, lock, warning, check-against-source, candidate. Icons always have a text label or an accessible name; icon-only buttons have a tooltip with the shortcut.
