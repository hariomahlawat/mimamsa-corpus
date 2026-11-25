# Mimamsa UI/UX specification (Cycle 13, B0)

- **Status:** PROPOSED, for independent UX and accessibility review. Framework-neutral: it applies whether ADR-0005 selects ASP.NET Core or Django; the frontend candidate is React + TypeScript.
- **Scope:** the offline research application for an air-gapped LAN, used in a browser on Windows desktops (and tablets where provided).
- **Traceability:** each workspace and component maps to capabilities in [`docs/architecture/CAPABILITY_TRACEABILITY_MATRIX.md`](../../docs/architecture/CAPABILITY_TRACEABILITY_MATRIX.md) (CAP-…).

| Document | Covers |
| --- | --- |
| [01_PERSONAS_AND_WORKFLOWS.md](01_PERSONAS_AND_WORKFLOWS.md) | Personas (commander, legal practitioner, research officer, Admin) and their key workflows |
| [02_INFORMATION_ARCHITECTURE.md](02_INFORMATION_ARCHITECTURE.md) | Information architecture, object model on screen, global navigation, URLs |
| [03_RESEARCH_WORKSPACE.md](03_RESEARCH_WORKSPACE.md) | The research workspace: persistent search, result excerpts, facets, resizable panes, PDF viewer with highlights, provenance and evidence-status panels, notes, related items, tabs |
| [04_VISUAL_IDENTITY.md](04_VISUAL_IDENTITY.md) | Original visual identity, typography, colour and contrast (WCAG AA), spacing, iconography |
| [05_COMPONENTS_AND_KEYBOARD.md](05_COMPONENTS_AND_KEYBOARD.md) | Component inventory and keyboard interaction standards |
| [06_RESPONSIVE_AND_STATES.md](06_RESPONSIVE_AND_STATES.md) | Responsive rules (1366×768, 1920×1080, 2560×1440, tablet) and loading, empty, error and degraded states |
| [tokens/design-tokens.json](tokens/design-tokens.json) | Design tokens (light and dark), checked by `tests/test_tokens.py` |

## Design principles

1. **The document is the hero.** Screen space goes to source text and the original PDF, not to chrome. No metric cards, no dashboard landing page, no hero banners.
2. **Evidence state is always visible and never merged.** The seven status axes appear as separate, labelled chips. There is no green "verified" tick anywhere. Candidate data is labelled as such at the point of display.
3. **Density with order.** Professional users read a lot; use compact rows, tight but consistent spacing, real tables, and keyboard paths for every frequent action. Whitespace separates groups; it is not decoration.
4. **Quiet and precise.** Square-ish geometry (radius ≤ 4 px), hairline rules, one accent colour for interaction, no decorative animation; motion only to confirm a state change, and none under reduced-motion settings.
5. **Honest about limits.** OCR text is labelled "search only"; empty graph neighbourhoods say that no edge does not mean no adverse authority; gated features say why they are closed.
6. **Offline by construction.** System fonts, local icons, no remote assets.
7. **Equal access, different views** (PR-15): Admin and User see the same published research; commander and practitioner views are layouts, not permissions.

## Interaction patterns studied (patterns only, no branding)

Patterns drawn from professional legal-research and document tools in general, and from code editors and reference managers: persistent query bar with parsed query chips; split result/document views with synchronised hit navigation; facet rails with counts; side panels for metadata and history; tabbed documents; citation copy with pinpoint; keyboard command palette; hit-by-hit navigation inside a document. No product's names, logos, colours, layouts as a whole, iconography or copy are reproduced.

## Non-goals in Cycle 13

No advice screens, no checklists, no readiness scores, no form filling, no "answer" boxes. The commander assistant appears only as a disabled workspace with a gate notice (CAP-CA-01).
