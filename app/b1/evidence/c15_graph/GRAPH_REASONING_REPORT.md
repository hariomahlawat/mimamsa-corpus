# C15 S3: legal knowledge graph and deterministic reasoning foundation (WP3, WP4)

- **Branch:** `claude/c15-graph-reasoning`, based on staging `e10a8647`.
- **Design:** [ADR-0006](../../../../docs/architecture/decisions/ADR-0006-LEGAL-GRAPH-STORAGE-AND-REASONING-FOUNDATION.md).
- **API contract:** [C15_GRAPH_API.md](../../../../docs/architecture/b1/C15_GRAPH_API.md).
- **Not changed:** AUTH-LEDGER, legal approval states, acceptance oracles, corpus bytes or bundle signatures.
- **Not activated:** the closed Assistant; no generative model.

## 1. What was built

| Area | Implementation |
| --- | --- |
| Storage decision | **PostgreSQL**, already deployed; options A/B/C evaluated in ADR-0006. No graph database, extension, service or licence was added |
| Model | **Node kinds:** instrument, provision, provision version, judgment, unresolved reference, procedural requirement; form and competent authority are reserved. **Edge fields:** source identity (doc id and copy), evidence page and quote, typed relationship (architecture §5 vocabulary), temporal scope (from/to with status), verification, review state, uncertainty, legal-effect flag |
| Builder | Deterministic, from the generation only: TOC, A4 versions, A5 edges, C14 correspondence and notices, Commander task map. It can only emit `CANDIDATE`, `EXTRACTED_STRUCTURE` or `CURATED_NAVIGATION`; publication refuses anything else |
| Store | Atomic per-generation publication (one transaction; counts and content digest; skipped when unchanged) and verification at start-up. Eligibility-filtered node, neighbourhood (depth ≤ 2), path (depth ≤ 4, bounded frontier) and statistics queries |
| Eligibility | The current hidden-document set from the single eligibility decision is applied in every query, so withdrawal and reinstatement act on the next request |
| Rule engine (WP4) | Strong Kleene logic; typed decision tables with a unique hit policy (overlaps reject the pack); two-stage gate closed at AUTH-LEDGER v0 and without an exact grant, with the evaluator **not invoked**. No rule pack or grant exists |
| Evidence assessor (WP4) | Research only; ESTABLISHED / CANDIDATE / INSUFFICIENT_INFORMATION per finding, with evidence links, missing facts and blockers. ESTABLISHED requires LEGAL_REVIEWED records **and** a ledger above v0, so it is impossible today, and the result says so |
| API | `/api/graph/{resolve,node,path,stats}`, `/api/reasoning/{assess,rule-gate}`: read-only, authenticated, no-store, content-free logs, no node copy hashes |
| UI | The Graph workspace (`/g`) replaces the "later milestone" page. It shows a list view of typed relationships with status chips, evidence page links, uncertainty and temporal scope, and a research-assessment panel. The Commander and Studio UI is stream S4's |

## 2. Graph on the real 290-document sample

| Nodes | Count | Edges | Count |
| --- | --- | --- | --- |
| provision | 5,103 | CONTAINS_PROVISION | 4,793 |
| unresolved reference | 1,583 | CITES_JUDGMENT | 1,845 |
| provision version | 488 | RE_ENACTED_AS | 1,098 |
| judgment | 298 | CITES_PROVISION | 894 |
| instrument | 51 | VERSION_OF | 351 |
| procedural requirement | 6 | AMENDS_PROVISION_VERSION | 82 |
| **total** | **7,529** | SUBSTITUTES / INSERTS / OMITS / REPEALS_PROVISION / COMMENCES | 22 / 13 / 13 / 4 / 3 |
| | | REPEALS_INSTRUMENT / SAVES_OR_TRANSITIONS | 3 / 3 |
| | | QUOTES_PROVISION / FOLLOWS / OVERRULES_OR_LIMITS | 12 / 7 / 1 |
| | | PROCEDURE_REFERENCES_PROVISION | 17 |
| | | **total** | **9,161** |

**By verification:**
- CANDIDATE 4,351;
- EXTRACTED_STRUCTURE 4,793;
- CURATED_NAVIGATION 17;
- reviewed or verified: **0**.

**Storage:** edges 7.2 MB, nodes 2.8 MB, including indexes.

**Start-up:** build and publish 1.45 s; restart with an identical graph 1.10 s (republication skipped).

## 3. API latency

Real sample, same host, after warm-up. Source: `graph_probe.json`, from `graph_probe.py`.

| Route | Sequential p50 / p95 (ms) | 10 concurrent readers p50 / p95 (ms) |
| --- | --- | --- |
| node, provision, depth 1 | 32.8 / 56.5 | 30.9 / 52.7 |
| node, provision, depth 2 | 80.1 / 103.4 | 114.4 / 206.3 |
| node, judgment, depth 1 | 29.7 / 43.1 | 37.1 / 61.0 |
| path, depth 3 | 82.4 / 98.2 | 147.6 / 228.5 |
| stats | 6.9 / 17.9 | 16.7 / 29.9 |
| assess: succession | 17.6 / 37.2 | 13.4 / 32.1 |
| assess: temporal | 8.8 / 63.2 | 14.0 / 27.0 |

The first run measured stats p95 571 ms and succession p95 168 ms at 10 readers. Two fixes brought them to the figures above:
- statistics are cached per exact hidden-document set, so a withdrawal is never answered from a stale entry;
- the assessor's lookups are built once per graph.

**Every route is within the 300 ms target.** Scale behaviour is for WP1 to measure.

## 4. Reasoning coverage

| Evaluator | What it reports | Golden or synthetic test |
| --- | --- | --- |
| Temporal applicability | Versions held with recorded interval statuses; "printed as omitted"; whether a recorded interval determinably covers the date; the as-of date as a missing fact | **TA-01 Army Act s.75 @ 2000-01-01:** printed as omitted (candidate, evidence page); omission version effective-from NOT_STATED; overall INSUFFICIENT_INFORMATION |
| Commencement, repeal, savings, correspondence | RE_ENACTED_AS candidates with the "not interchangeable" caution; held repeal, savings and commencement-delegation quotations; commencement notification not held; conduct date compared with the secondary-source date | **TA-03:** IPC s.302 with conduct 2023-12-01 and BNS s.103 with conduct 2024-08-01. Correspondence both ways, repeal quote, commencement not established; overall INSUFFICIENT_INFORMATION. The proceeding date is reported as a separate missing fact |
| Procedural prerequisites, competent authority, safeguards | Referenced provisions as navigation aids. Prerequisites, authority and safeguards are stated as *not evaluated*, with the rule-gate blockers | "Summary court-martial": INSUFFICIENT_INFORMATION |
| Conflicts and unresolved records | Compilation omission mark against version records; undetermined version chain; crawler status against held repeal text | s.127: version chain undetermined. IPC: crawler status `repealed` agrees with held repeal text, so no conflict (negative control) |
| Rule evaluation | Kleene tables; unique-hit tables; gate | Synthetic P/Q/E oracle (§8), overlap rejection, gate closed at v0 with 0 invocations |

**At AUTH-LEDGER v0, no assessment contains an ESTABLISHED finding.** This is asserted across all golden cases.

**Eligibility in the assessor:**
- withdrawing the IPC/BNS comparison table removes the correspondence finding;
- withdrawing the IPC makes the provision "not available".

## 5. Tests

| Suite | Result |
| --- | --- |
| C# | **169/169**: 160 existing unchanged, plus 9 new — `RuleEngineTests` 4, `GraphBuilderTests` 2, `GraphStoreTests` 3 |
| Playwright | **61/61**: 58 existing unchanged, plus 3 new in `graph.sample.spec.cjs`:<br>• G-01 graph page and assessment;<br>• G-02 withdrawal removes the comparison-table relationships from the page, the statistics and the assessment, and reinstatement restores them;<br>• G-03 every graph and reasoning route returns 401 without a session |
| Retrieval oracle (no file changed) | 10/14, unchanged (the 4 hybrid cases) |
| Design tests / tokens | 117/117 / no drift |

**PostgreSQL store tests:**
- publication is idempotent;
- the verification digest is checked;
- an **interrupted publication rolls back**, leaving the previous graph intact, and the next publication succeeds;
- node, neighbourhood, path and statistics are each checked with a document withdrawn and then reinstated;
- a forged edge carrying a reviewed status is refused.

## 6. Evidence

- `graph_probe.py`, `graph_probe.json`: statistics, sample neighbourhoods, paths, assessments, latency.
- `g01-ipc-302-relationships-1920.jpg`, `g01-ipc-302-assessment-1920.jpg`: written by journey G-01.

## 7. Open issues

1. **Forms and competent authorities:** modelled but not populated, because no held extraction exists. Populating them needs the Form Discovery register (Document Studio) and reviewed authority records, not inference.
2. **Commencement:** held as notices (delegation, notification not held, secondary-source date). No `COMMENCES` edge to a commencement notification exists, because none is held. Three A4 `COMMENCES` candidates come from version records.
3. **Unresolved citations:** 1,583 unresolved-reference nodes (raw citations). Resolving them is a corpus and citation-resolution task.
4. **Review state:** `graph_edge_reviews` exists without a write path. A Legal Reviewer workflow is a blocking owner decision (Document Studio 3.3).
5. **Integration overlap:** S4 (Commander and Studio) should consume `C15_GRAPH_API.md`. At integration, `app.js` (the `/g` route) and `app.css` may conflict with S4's UI edits.
