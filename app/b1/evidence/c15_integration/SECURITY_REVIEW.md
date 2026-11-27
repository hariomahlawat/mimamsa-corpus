# C15 independent security review and dispositions

- **Scope:** the Cycle 15 additions on `claude/c15-integration`, diffed from `e10a8647`:
  - graph and reasoning routes;
  - Commander workspace;
  - Document Studio;
  - persistent search index;
  - hybrid vector store;
  - client JS;
  - logging.
- **Reviewer:** an independent read-only agent. It was given the code and the product security rules, not the implementers' conclusions. It made no edits.
- **Result:** no critical or high findings. Two medium findings and five low or informational findings.

| # | Severity | Finding | Disposition | Where | Test |
| --- | --- | --- | --- | --- | --- |
| M1 | Medium | Studio quote blocks exported OCR text (`QuotingPermitted=false`) as a "From the library" quotation | **Fixed.** On an OCR copy, `RenderBlock` returns `quote_available=false` with a notice that says "quote from the original page". The citation stays. The client no longer offers the quote checkbox for OCR text | `Api.Workspace.cs`, `research.js` | `WorkspaceStudioTests.OcrTextIsNeverExportedAsAQuotation`: checks the API and both the HTML and Markdown exports |
| M2 | Medium | `/api/reasoning/assess` returned evidence quotations without the quoting gate | **Fixed.** `AssessmentDto` applies the same `QuotingPermitted` gate as `EdgeDto` | `Api.Graph.cs` | Covered by the gate shared with edges; the reasoning UI does not display quotes |
| L3 | Low | Unresolved-reference nodes (labelled with text from the citing judgment) stayed visible on lookup and in statistics after that judgment was withdrawn | **Fixed.** A node with no document of its own is visible only while a visible edge touches it. Edge-less structural nodes stay visible | `GraphStore.cs` (`Hidden`) | `GraphStoreTests.PublishVerifyQueryAndEligibility`: a probe reference cited only by `syn-j-allow` is hidden on withdrawal and leaves the counts |
| L4 | Low (conditional) | Graph and reasoning hide whole documents, not individual restricted copies | **Accepted, open (C16).** Anchors come from held copies of visible documents. The case needs a non-current held copy on the restricted register while its current copy is visible, which the present corpus does not contain. Recheck when continuous ingestion lands | — | — |
| L5 | Low | No cost or quota bounds | **Partly fixed:** path expansion is capped at 10,000 edges per level (was 50,000) and uses a set lookup; Studio's per-user caps now take a transaction-scoped advisory lock per owner, so parallel requests cannot exceed them. **Open (C16):** per-user rate limits, a total-bytes Studio quota, and the cost of Commander domain GETs when the reranker is on (the reranker is off by default) | `GraphStore.cs`, `StudioStore.cs` | Existing graph and Studio tests |
| L6 | Low | Index retention could delete directories under a misconfigured index root | **Fixed.** Retention deletes only directories whose manifest `format` starts with `mimamsa-search-index/` | `IndexStore.cs` | `PersistentIndexTests.OlderGenerationIndexesAreKeptForRollbackUpToTheLimit`: an unrelated older directory survives |
| I7 | Info | Reviewed edge states would get the label "Structure read from the held text" | **Deferred.** `PublishAsync` refuses non-builder verification values, so this cannot occur until the Legal Reviewer workflow exists. Add explicit labels with that workflow | — | `GraphStoreTests.TheBuilderCannotPublishReviewedEdges` |

## Checked and found sound (reviewer)

- Studio is strictly per user: every query is scoped by owner, ids are random 96-bit values, unknown and foreign ids both return 404, Admin has no access to users' documents, and writes require session, CSRF and same-origin.
- Studio corpus blocks store references only and are re-resolved when read.
- Exports are fully encoded and served with a sandbox CSP, `nosniff` and as attachments.
- Commander payloads pass through `VisibleDocument`.
- Graph SQL is parameterised, and hidden documents are excluded on neighbourhood, path and statistics queries.
- Reasoning cannot return ESTABLISHED at AUTH-LEDGER v0.
- The final visibility filter covers the heading, hybrid and rerank search tiers.
- The persistent index stores no eligibility data.
- The client has no `innerHTML` sinks.
- Logs and audit entries are content-free.
- C15 adds no new admin routes.
