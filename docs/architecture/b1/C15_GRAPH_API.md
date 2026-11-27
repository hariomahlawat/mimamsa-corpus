# C15 graph and research-assessment API contract (WP3, WP4)

**For:** Commander workspace and Document Studio (stream S4) and any other client. All of them must use these routes and not duplicate graph or reasoning logic.

**Common rules for every route:**
- **Session:** `GET`; requires a session (401 otherwise).
- **Responses:** `no-store` responses; content-free logs.
- **Eligibility:** applied on every request through the single eligibility decision. A withdrawn or ineligible document, its nodes and every edge touching it disappear at once; reinstatement restores them.
- **Hashes:** node copy hashes are never returned.
- **Quotations:** only where the source permits quoting.

Implementation: `app/b1/src/Mimamsa.Web/Api.Graph.cs`, `Mimamsa.Core/Graph/*`, `Mimamsa.Core/Reasoning/*`. Design: [ADR-0006](../decisions/ADR-0006-LEGAL-GRAPH-STORAGE-AND-REASONING-FOUNDATION.md).

## Identifiers

| Node kind | Id form | Example |
| --- | --- | --- |
| instrument | `INST:<family key>` | `INST:no:46 of 1950` |
| provision | `PROV:<code>:<s|r|reg>.<number>` | `PROV:AA-1950:s.69`, `PROV:AR-1954:r.22`, `PROV:IPC-1860:s.302` |
| provision_version | `VER:<A4 version id>` | `VER:AA1950/s.75/v02` |
| judgment | `JUD:<doc_id>` (held) or `JUD:JG-<id>` (not held) | `JUD:sc-2013-dharamvir-singh-2013insc408` |
| unresolved_reference | `REF:<hash>` | label carries the raw citation |
| procedural_requirement | `PROC:<slug>` | `PROC:summary-court-martial` (Commander task) |
| form, competent_authority | reserved | not populated: no held extraction; never inferred |

Codes for held instruments: AA-1950, AR-1954, AFA-1950, NA-1957, AFT-2007, AFT-PR-2008, IPC-1860, CRPC-1973, IEA-1872, BNS-2023, BNSS-2023, BSA-2023. Other instruments use `DOC-<primary doc_id>`. Use `/api/graph/resolve` rather than building ids by hand.

## Routes

### `GET /api/graph/resolve?doc=<doc_id>[&section=<n>]`

Returns `{ node_id }`:
- a provision node when `section` is given;
- otherwise the instrument node;
- the judgment node for a judgment.

404 when the document is not available.

### `GET /api/graph/node?id=<node_id>[&depth=1|2][&limit=1..2000]`

Returns `{ node, edges[], truncated, depth, absence }`.
- **node:** `{ id, kind, label, doc_id, held, page, family, code }`.
- **edge:** `{ id, type, from: node, to: node, origin, source: { doc_id, page } | null, quote | null, temporal: { from, from_status, to, to_status }, verification, review_state, uncertainty, has_legal_effect, label }`.
- **verification:** `CANDIDATE` | `EXTRACTED_STRUCTURE` | `CURATED_NAVIGATION`. The reviewed values exist only for a future authorised review process.
- **review_state:** `UNREVIEWED`.
- **origin:** `TOC` | `A4` | `A5` | `C14_CORRESPONDENCE` | `C14_NOTICE` | `C14_COMMANDER_TASK`.
- **404** when the node is not available.

Edge types: `CONTAINS_PROVISION`, `VERSION_OF`, `AMENDS_PROVISION_VERSION`, `OMITS_PROVISION`, `SUBSTITUTES_PROVISION_TEXT`, `INSERTS_PROVISION`, `REPEALS_PROVISION`, `COMMENCES`, `REPEALS_INSTRUMENT`, `SAVES_OR_TRANSITIONS`, `RE_ENACTED_AS`, `CITES_PROVISION`, `QUOTES_PROVISION`, `CITES_JUDGMENT`, `FOLLOWS_PROPOSITION`, `OVERRULES_OR_LIMITS_PROPOSITION`, `PROCEDURE_REFERENCES_PROVISION`. Reserved: `COMPETENT_AUTHORITY_FOR`, `PRESCRIBES_OR_EXEMPLIFIES_FORM`.

**Display rules (clients must follow):**
- Label every `CANDIDATE` as "Candidate (automated, not verified)".
- Show `uncertainty` text with the edge.
- Never present `RE_ENACTED_AS` as equivalence.
- Show `absence` wherever a list may be empty.

### `GET /api/graph/path?from=<id>&to=<id>[&max_depth=1..4]`

Returns `{ found, max_depth, nodes[], edges[], notice }`: the shortest undirected path through visible records. A path is navigation, not a legal relationship.

### `GET /api/graph/stats`

Returns `{ generation, builder, nodes, edges, nodes_by_kind, edges_by_type, edges_by_verification, auth_ledger_version, notice }`. Counts reflect current eligibility.

### `GET /api/reasoning/assess?kind=<kind>&…`

Research-only evidence assessment.

| kind | Parameters | Reports |
| --- | --- | --- |
| `temporal` | `doc`, `section`, `as_of` | Versions held, the "printed as omitted" mark, whether any recorded interval determinably covers the date |
| `succession` | `doc`, `section`, `conduct_date`, `proceeding_date` | Correspondence (candidate), repeal, savings and commencement notices with held quotations, commencement not established, a date comparison with a secondary-source date |
| `procedure` | `task` (a Commander task name) | Referenced provisions (navigation aids); procedural prerequisites, competent authority and safeguards stated as not evaluated, with the rule-gate blockers |
| `conflicts` | `doc`, `section` | Compilation against version records, an undetermined version chain, crawler status against held repeal text |

Response: `{ kind, subject, inputs, overall, findings[], missing_facts[], blockers[], notice, auth_ledger_version }`.
- **finding:** `{ code, statement, state, basis, evidence[] }`.
- **evidence:** `{ doc_id, page, quote, edge_id, verification, origin }`.
- **state and overall:** `ESTABLISHED` | `CANDIDATE` | `INSUFFICIENT_INFORMATION`.

At AUTH-LEDGER v0 no finding is `ESTABLISHED`, and `blockers` says why. Statements are descriptive. **Clients must not rephrase them as advice, conclusions or instructions**, and must show `missing_facts`, `blockers` and `notice`.

### `GET /api/reasoning/rule-gate`

Returns `{ evaluation_admitted, delivery_authorized, blockers[], rule_packs_installed, auth_ledger_version }`. Today: not admitted, not authorised, 0 packs.

## Not provided

- No write routes.
- No review or approval actions.
- No generative output.
- No "applies / does not apply" result.
