# C15 Commander workspace and Document Studio foundation (WP5, WP6)

**Status:** implemented foundation (stream S4, branch `claude/c15-workspace-studio`).

**What this is not:** legal advice, a form registry, or a source of legal approval. AUTH-LEDGER and approval states are unchanged.

**Controlling design:**
- [DOCUMENT_STUDIO_AND_TEMPLATE_REGISTRY.md](../DOCUMENT_STUDIO_AND_TEMPLATE_REGISTRY.md);
- [ADR-0003](../decisions/ADR-0003-DOCUMENT_STUDIO_AND_TEMPLATE_REGISTRY.md);
- [COMMANDER_USE_CASES.md](../../product/COMMANDER_USE_CASES.md).

## 1. Commander workspace (`/c`, `/c/<area>`)

**One engine.** The workspace has no reasoning system of its own. Each task area (`CommanderDomains.All`) is a fixed, reviewed list of provision references, safeguard references, form-search queries and questions requiring legal review.

**Reading the corpus.** References are resolved only through `ICommanderSource`:

```csharp
public interface ICommanderSource
{
    string Description { get; }
    ResolvedProvision? Resolve(ProvisionRef r);   // null: instrument not held; Found=false: provision not located
}
```

**Default source.** `TocCommanderSource` uses the held tables of contents, the same data as the C14 Commander home. It moves a contents-page hit (the arrangement of sections) to the provision's own page. An example is Army Act s.80, which moves from p.5 to p.27.

**Integration seam.** When the C15 graph and reasoning API ([C15_GRAPH_API.md](C15_GRAPH_API.md), stream S3) is integrated, a graph-backed `ICommanderSource` is registered in `Program.cs` in its place. The API and UI do not change.

**Eligibility.** It is applied on every response, through `VisibleDocument`. An unavailable source carries no source-derived field: no title, heading, page, excerpt or copy hash, only the fixed task label. Pages re-render on every policy-epoch change, and the epoch poll runs while a workspace page is shown.

**Content shown for each area:**

| Content | Origin |
| --- | --- |
| Provisions | Heading and excerpt as printed in the held copy; link to the Statutes view |
| Safeguards | Held provisions protecting the person concerned |
| Forms and procedural references | Search results in held Acts, Rules and Regulations. Labelled candidates; no form is verified or approved |
| Questions requiring legal review | Fixed prompts, not conclusions. They can be sent to the Studio as *automated suggestions* |

The task areas are Disciplinary matters, Court of Inquiry, Summary of Evidence, Administrative action, Service and pension matters, and Forms and procedural references.

## 2. Document Studio (`/studio`, `/studio/<id>`)

This is WORKING_DOCUMENT_PROCESSING. Studio content never becomes a shared source, a search entry, graph evidence or a template.

| Aspect | Implementation |
| --- | --- |
| Storage | `studio_documents`, `studio_versions` (full snapshot per version), `studio_notes`. Created idempotently at start-up and truncated by the test-mode reset |
| Access | Every query is scoped by owner, so another user's id is indistinguishable from a missing one (404 on every route). Admin capacity gives no access (registry §2) |
| Writes | `POST` only, with session, CSRF token and same-Origin. Body ≤ 60 kB (request limit 64 kB); ≤ 400 blocks; ≤ 20,000 characters per block; ≤ 500 documents and ≤ 200 versions each per user |
| Versions | Optimistic concurrency (`base_version`). A stale save gets 409. Earlier versions are read-only and can be restored as a new version |
| Block origins | `user`; `template` (generic skeleton heading); `suggestion` (automated, until edited); `corpus` (server-derived). The UI always shows the origin. Editing a template or suggestion block makes it `user` |
| Corpus integrity | Citation and quote blocks store only `{doc_id, copy (12 hex), page, passage_id, para}`; any text the client sends is discarded. Citation, title and quotation are produced at read time by `CitationResolver` from the current eligible copy. A withdrawn or ineligible source renders only "Source no longer available in this installation.", in the UI and in exports; the author's own text is untouched |
| Templates | `blank`, plus two generic skeletons (research note, memo) labelled "not a legal form". No legal form is offered, because none in this library is verified or approved (Form Discovery register) |
| States | `draft`, `in_review`, `final_draft`. These are the author's workflow labels, never legal approval |
| Export | HTML and Markdown, as an attachment with `nosniff` and a sandbox CSP. HTML is fully escaped. Every export carries "Not legally approved…" plus version, state and release. DOCX is not implemented (see §4) |
| Logging | Request logs are content-free (route templates). Audit entries are metadata only: action, document id, version, block count, template. A test asserts that working content never reaches `audit_log` or the service log |
| Notes | Short research notes, optionally pinned to a copy and page; rendered with the same eligibility rule |

**Integration points:**
- **Reader:** the toolbar "Studio" button adds a copy-pinned citation, plus a quotation when a passage is selected on the current edition.
- **Commander:** "Add to Studio" per provision, and for the area's questions.

## 3. Compact results (WP7)

A `@media (max-height: 900px)` layout makes these changes:
- titles clamp to 2 lines;
- group metadata stays on one line;
- snippets clamp to 2 lines (a selected or focused hit still expands);
- the results header is tighter.

**Measured** (`workspace.sample.spec.cjs`, W-07), results fully visible: 1366×768 → 4 (was 2); 1920×1080 and 2560×1440 unchanged (no matching media query).

## 4. Open items

- **Graph-backed source:** switch `ICommanderSource` to the S3 graph API at integration. Commander items then gain typed relations (procedural requirements, competent authorities) with evidence and review state.
- **Retention:** working documents persist until the author deletes them. The registry asks for configurable retention and exclusion from backups by default; both are not yet implemented.
- **Temporary uploads** for review (DOCX, PDF, scans): out of scope.
- **DOCX export:** not implemented. It needs a permissive offline OpenXML writer (e.g. DocumentFormat.OpenXml, MIT) and a review of its fidelity.
- **Document Readiness Report:** not implemented. It depends on the Form/Template Registry and on legal approvals that do not exist yet.
