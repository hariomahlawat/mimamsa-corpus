# C15 S4: Commander workspace, Document Studio foundation, compact results (WP5, WP6, WP7)

**Branch and base:** `claude/c15-workspace-studio`, based on staging `e10a8647`.

**Design note:** [C15_WORKSPACE_STUDIO.md](../../../../docs/architecture/b1/C15_WORKSPACE_STUDIO.md).

**Not changed:**
- AUTH-LEDGER and legal approval states;
- acceptance oracles (0 files differ from staging);
- corpus, bundles and search ranking (S1/S2);
- the graph and reasoning core (S3).

## 1. What shipped

| Area | Delivered |
| --- | --- |
| Commander workspace `/c` | Six task areas with a shared label "Candidate / research aid — not legal advice" and a disclaimer. Each page shows:<ul><li>provisions grouped for the task, with heading and excerpt as printed in the held copy and links to the Statutes view;</li><li>safeguards;</li><li>search-backed form candidates ("not a form registry");</li><li>questions requiring legal review.</li></ul>"Add to Studio" works per provision and for the questions. The early Commander home links to the workspace |
| One engine | The corpus is read only through `ICommanderSource`; the default `TocCommanderSource` uses the held TOCs. It switches to S3's graph API at integration without API or UI changes. Eligibility is applied per response, and pages re-render on policy-epoch changes |
| Document Studio `/studio` | Private documents and research notes:<ul><li>generic, non-legal skeletons (blank, research note, memo);</li><li>block editor with a visible origin for every block (You / Template heading / Automated suggestion / From the library);</li><li>version history with read-only view and restore;</li><li>workflow labels (draft / in review / final draft), never approval;</li><li>HTML and Markdown export with a "Not legally approved" footer;</li><li>delete.</li></ul> |
| Citation insertion | The reader toolbar "Studio" button adds a copy-pinned citation, plus a quotation of the selected passage from the held text. Commander provisions and questions can also be added |
| Compact results (WP7) | Short-viewport layout (`max-height: 900px`). Results fully visible: **1366×768: 4** (was 2); **1920×1080: 5**; **2560×1440: 7** (unchanged) |

## 2. Commander provision check (real sample)

Every reference was resolved and its printed heading checked before release:
- Rule 24 is "Remand of accused", so it is grouped as remand, not as part of recording the summary.
- Army Act ss.80, 83 and 84 were first resolved to the contents page (p.5); the adapter moves them to their own text (pp.27–28).
- The query `"form of charge"` found nothing and was removed.

All 31 references in the six areas resolve on the sample. The Army pension regulations and Entitlement Rules are not held, and the service-and-pension area says so.

## 3. Tests

| Suite | Result |
| --- | --- |
| C# | **174/174**: 160 existing unchanged, plus 14 new in `WorkspaceStudioTests.cs` |
| Playwright | **67/67**: 58 existing unchanged, plus 9 new in `workspace.sample.spec.cjs`, W-01…W-07 with W-07 at three viewports. W-01 failed once and was fixed: "not a form registry" had been only in a tooltip and is now visible text |
| Design tests / `gen_tokens --check` | 117/117 / no drift |
| Retrieval oracle files | untouched |

## 4. Security and safety tests

| Property | Test |
| --- | --- |
| Session required on every workspace and Studio route (401) | C# `WorkspaceRoutesNeedASession` |
| CSRF token and same-Origin on every POST (403) | C# `StudioPostsNeedCsrfAndSameOrigin` |
| Owner isolation: another user, including an Admin, gets 404 on read, versions, export, save, append and delete, and the document is absent from their list | C# `AnotherUserIncludingAnAdminGets404OnEveryRoute`, `StoreIsOwnerScoped`; Playwright W-04 |
| Client cannot spoof library content: citation, title and quote text sent by the client are discarded; text blocks cannot claim `corpus` origin | C# `NormaliseKeepsOnlyReferencesForCorpusBlocksAndRejectsSpoofing`, plus "FAKE CITATION TEXT" in the HTTP test |
| Withdrawal of a cited source: "Source no longer available" in the UI, API, HTML and Markdown; the title and citation never appear; the author's text is kept; reinstatement restores it | C# `CitationsFollowWithdrawalWithoutDeletingTheAuthorsText`; Playwright W-05 (open page, no reload) |
| HTML export escapes user text (`<script>` becomes `&lt;script&gt;`); exports are attachments with `nosniff` and a sandbox CSP | C# (same test) |
| Audit entries and service logs carry no working content | C# `AuditEntriesAreMetadataOnly` |
| Commander items for unheld or unavailable sources carry no derived fields | C# `CommanderDomainsCarryNoSourceFieldsForUnheldProvisions` |
| Size limits; versions conflict (409) | C# `SavesAreVersionedAndConflictsAreRefused`, `Normalise…` |

## 5. Evidence

Screenshots in this folder (JPEG q70, DSF 1):
- `w01-commander-areas-1920`, plus one per area (`w01-commander-<area>-1920`);
- `w02-studio-editor-1920`;
- `w03-studio-quote-from-reader-1920`;
- `w04-owner-isolation-1920`;
- `w05-studio-citation-withdrawn-1920`;
- `w06-commander-questions-in-studio-1920`;
- `w07-density-{1366,1920,2560}`, with the matching `density-*.json`.

## 6. Open issues

1. **Graph-backed source:** switch `ICommanderSource` to S3's graph API at integration (`docs/architecture/b1/C15_GRAPH_API.md` was not present on this branch).
2. **Retention:** Studio retention policy and exclusion from backups are not implemented; documents persist until the author deletes them.
3. **DOCX export:** not implemented (needs a permissive offline OpenXML writer); HTML and Markdown are provided.
4. **Readiness report and template registry:** the Document Readiness Report and registry-backed templates are blocked on the Form/Template Registry and on legal approvals.
5. **Toolbar width:** the reader toolbar gains one button ("Studio"). No overflow was seen at 1366, but its density is worth checking with S3's viewer changes at integration.
6. **Integration conflicts to expect:** `research.js` (one import, one button, one function), `app.js` (routes, workspace link, policy handler), `home.js` (one link), `app.css` (appended blocks), `Api.cs` (one `MapWorkspace` line), `Program.cs` (store registration, schema, test reset), `AppServices.cs` (two members).
