# 02. Information architecture and global navigation

## 1. Objects users meet

| Object | What the user sees | Identity shown | Notes |
| --- | --- | --- | --- |
| Document | Act, Rules, Regulations, manual, notification, judgment, order, historical book, policy/SOP | `doc_id`, title, number, date | Bound to one source copy; alternates switchable |
| Source copy | The original file | sha256 (first 12 hex, full on hover/copy), size, pages, completeness | Never edited |
| Passage | A paragraph-sized span with page anchor | page, paragraph label (if printed) | Basis of search hits and citations |
| Section | Section/Rule of an Act or Rules (`doc_id#sNN`) | number, heading | Amendment strip shows candidate edges |
| Judgment / proceeding | Decision and the cases it disposes | case numbers, neutral citation | File ≠ judgment ≠ proceeding |
| Candidate | Outcome, edge, form (holdings hidden from Users) | type, extractor version, status, restriction, measured quality | Always labelled |
| Release | Imported bundle generation | release id, HF revision, date | Shown in footer and provenance |
| Note / pin / research set / saved search | Private research objects | owner only | Never shared, never indexed |
| Working session (B3) | Document Studio private session | owner only, expiry | Never in the library |

## 2. Site map

```
Global shell (banner · top bar · workspace switcher · status footer)
├── Research (default)                       CAP-US-*, CAP-RW-*
│   ├── Search results  ─┬─ Document tabs (judgment | statute | other)
│   │                    └─ Context pane: Evidence · Provenance · Related · Cited/Citing · Notes
│   └── Saved: searches · research sets · pins (left rail)
├── Statutes                                 CAP-SE-*
│   └── Act/Rules → TOC → Section (amendment strip, related judgments, instruments)
├── Graph                                    CAP-KG-*
│   └── Canvas + list view · edge inspector · legend (per-type precision)
├── Document Studio (B3)                     CAP-DS-*
│   ├── My sessions → session (viewer, OCR, annotations, export)
│   └── Forms registry (read-only, labelled)
├── Commander assistant (gated, disabled)    CAP-CA-*
└── Administration (Admin only)              CAP-KA-*
    ├── Staging queue → review item
    ├── Library management (withdraw, replace, reprocess)
    ├── Releases (verify, import, switch, rollback)
    ├── Queues (OCR low confidence; edges and impact triggers, view only)
    ├── Accounts · Designations (inert)
    ├── Audit log
    └── Backup status
```

## 3. Global navigation

| Element | Position | Content | Rules |
| --- | --- | --- | --- |
| **Candidate-data banner** | Very top, full width, 28 px, non-dismissable | Text from `RELEASE.json` `candidate_banner.text` + "AUTH-LEDGER v0" + release id | Present on every route, print and export (CAP-KA-08). Never hidden by scrolling |
| **Top bar** | Below banner, 40 px | Product mark (left) · workspace switcher (Research, Statutes, Graph, Studio, Assistant (locked), Administration (Admin only)) · persistent search field (centre, grows) · view toggle (Practitioner / Commander) · user menu | Search field available in every workspace (Ctrl+K). Administration is absent for Users, not merely disabled |
| **Left rail** | Collapsible, 200–280 px | Context of the workspace: saved searches and sets (Research), TOC (Statutes), node filters (Graph), sessions (Studio), sections (Administration) | Collapses to icons at compact widths |
| **Status footer** | Bottom, 24 px | Release id and date · HF revision (short) · connection to server · background job count (Admin) | Text only, no metrics |

There is **no home dashboard**. Signing in opens Research with the cursor in the search field and the last workspace layout restored.

## 4. URL and deep-link scheme

URLs are stable across release updates and carry no secrets. Ids are opaque where they refer to private objects.

| Route | Meaning |
| --- | --- |
| `/r?q=…&f=…` | Research search with query and filters |
| `/d/{doc_id}?p={page}&a={passage_id}&copy={sha12}` | Document at page/passage; `copy` pins a specific source copy |
| `/s/{doc_id}/{section}` | Statute section |
| `/g?focus={node}&types=…` | Graph neighbourhood |
| `/studio/{session_id}` | Private working session (owner check) |
| `/admin/…` | Administration (Admin role check server-side) |
| `/cite/{release_id}/{doc_id}/{sha12}/{page}[/{para}]` | Citation permalink; resolves to the current copy with a notice if superseded |

## 5. Labels and vocabulary

- Use the axis names exactly: **Source integrity, Source authenticity, Evidence fidelity, Legal applicability, Legal approval, Publication, Dependency freshness.**
- Candidate wording: "Candidate (automated, not verified)". Never "AI answer", "verified", "confirmed" or "current law".
- Gate wording: "Closed: needs a Legal Reviewer appointment and recorded approvals. No legal reasoning is available in this version."
- OCR wording: "OCR text: for search only. Quote from the original page."
