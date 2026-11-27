# ADR-0006: Legal knowledge graph storage and the deterministic reasoning foundation

**Status:** accepted for development (Cycle 15, WP3 and WP4).

**Scope:** storage and query of the legal knowledge graph; the boundary between research-only evidence assessment and executable rule evaluation.

**Not changed:** AUTH-LEDGER, legal approval states, acceptance oracles, corpus bytes.

## Context

[LEGAL_KNOWLEDGE_ARCHITECTURE](../LEGAL_KNOWLEDGE_ARCHITECTURE.md) §5–§8 needs typed relationships between instruments, provisions, versions, judgments, procedures, authorities and forms. Each relationship needs its source anchor, temporal scope and its own verification and review state.

Its §8 proposes PostgreSQL. It states that a separate graph engine is "not presumed necessary" and should be introduced only after measured requirements cannot be met.

[DETERMINISTIC_LEGAL_ENGINE](../intelligence/DETERMINISTIC_LEGAL_ENGINE.md) §10 requires that, at AUTH-LEDGER v0, both evaluation admission and delivery are denied, and that the evaluator is not invoked "even for uncertainty".

WP1 is moving search to a bounded-memory, disk-backed design. The graph should not add a large in-process structure that grows with the corpus.

## Options evaluated

| Option | For | Against |
| --- | --- | --- |
| **A. PostgreSQL tables** (nodes, typed edges, review table), indexed by endpoint; neighbourhood and paths by level-wise indexed expansion | Already deployed (no new service or licence); transactional per-generation publication; integrity constraints; a mutable review table beside an immutable derived graph; disk-backed, so memory does not grow with the corpus; offline; Windows and Linux | Path queries need bounded expansion rather than a graph query language |
| B. In-process adjacency lists only | Fastest single lookups | Memory grows with the corpus (the WP1 concern); no persistence for review state; rebuilt on every start; a second copy of eligibility logic |
| C. Separate graph database (Neo4j Community, Memgraph, Apache AGE) | Graph query language | Another service, or a PostgreSQL extension needing system-package installation; licence constraints (GPLv3 or BSL); its own backup and upgrade path; the same eligibility filter would have to be reimplemented there. Not justified by the measured needs below |

**Recursive CTEs** were considered for paths. Unbounded `WITH RECURSIVE` explodes around hub nodes; one Act has 196 provisions, and popular provisions are cited many times. Level-wise expansion with the frontier capped at 5,000 nodes and depth capped at 4 is bounded and uses the endpoint indexes; one level is one `= ANY($frontier)` lookup.

## Decision

**Option A.**

1. **Derived graph.** The graph is derived deterministically from the active generation by `GraphBuilder`:
   - tables of contents;
   - A4 provision versions;
   - A5 citation and treatment candidates;
   - C14 correspondence tables and repeal/savings notices;
   - the C14 Commander task map.

   The same generation always yields the same node and edge ids and the same content digest.
2. **Atomic publication** (`GraphStore.PublishAsync`), in one transaction under an advisory lock:
   1. delete any rows for the generation;
   2. `COPY` the nodes and edges;
   3. insert the `graph_generation` row with counts and the digest, then commit.

   A crash before commit leaves the previous graph intact, which is tested. Start-up republishes only if the digest differs, then verifies the counts and digest (`VerifyAsync`). If that fails, the graph routes return 503 and the rest of the service is unaffected.
3. **Verification states.** The builder may only emit `CANDIDATE`, `EXTRACTED_STRUCTURE` or `CURATED_NAVIGATION`. Publication refuses any other value. `DOCUMENTARY_CHECKED` and `LEGAL_REVIEWED` can come only from a future authorised review process, recorded in `graph_edge_reviews`, which has no write path today. **No automatic promotion.**
4. **Eligibility per request, never baked into the stored graph.** Every query receives the set of documents that are not visible now, through the existing single eligibility decision. It drops:
   - nodes naming such a document;
   - edges whose source or either endpoint is hidden.

   Paths never cross a hidden document. Withdrawal and reinstatement take effect on the next request, with no republishing.
5. **Reasoning in two separate parts:**
   - **Rule evaluation** (`RuleEngine`): strong Kleene logic, typed decision tables with a unique hit policy (overlapping rows reject the pack), and a two-stage gate. The gate is closed at AUTH-LEDGER v0 and without an exact approved grant, and the table is **not invoked**. No rule pack or grant exists; tests use synthetic tables only.
   - **Research evidence assessment** (`EvidenceAssessor`): reports what held records show, finding by finding, as ESTABLISHED, CANDIDATE or INSUFFICIENT_INFORMATION, with evidence and missing facts. ESTABLISHED requires every supporting record to be LEGAL_REVIEWED **and** the ledger to be above v0, so at v0 nothing is ESTABLISHED, and the result says so. It never decides which law applies, never gives advice and never calls a model.

## Measurements

Real 290-document sample, development host (i7-10750H, 16 GB, PostgreSQL 18.6). Sources: `app/b1/evidence/c15_graph/graph_probe.json` and the service log.

| Measure | Value |
| --- | --- |
| Graph | 7,529 nodes and 9,161 edges |
| Build and publish at start-up | 1.45 s |
| PostgreSQL storage | edges 7.2 MB, nodes 2.8 MB, including indexes |
| One endpoint-indexed lookup (`EXPLAIN ANALYZE`) | 0.22 ms execution |
| Neighbourhood depth 1 (provision / judgment) | see the report; p95 well under 100 ms at 10 concurrent readers |
| Neighbourhood depth 2 | p95 246 ms at 10 concurrent readers (first run) |
| Path, depth 3 | p95 100 ms at 10 concurrent readers |

These are well within the 300 ms target. At full-corpus scale, the edge table grows with citations; the lookups stay index-bound. Re-measure at scale in WP1.

## Consequences

- **No new deployment dependency:** no extra service, no extension, no licence change.
- **Option C can be revisited** only on a measured requirement that bounded expansion cannot meet, such as deep multi-hop analytics.
- **Data not yet populated:** forms and competent authorities are model kinds but have no data, because nothing extracts them yet and they are not inferred. Commencement is held as instrument notices, not as `COMMENCES` edges, because no commencement notification is held.
