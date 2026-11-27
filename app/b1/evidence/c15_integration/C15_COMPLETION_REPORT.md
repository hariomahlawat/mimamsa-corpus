# Cycle 15 completion report

**Branch:** `claude/c15-integration`, based on staging `e10a8647`.

**Streams merged:**

| Stream | Draft PR | Branch |
| --- | --- | --- |
| S1 persistent search index | #73 | `claude/c15-search-index` |
| S2 hybrid retrieval | #74 | `claude/c15-hybrid` |
| S3 graph and reasoning | #71 | `claude/c15-graph-reasoning` |
| S4 Commander workspace and Studio | #72 | `claude/c15-workspace-studio` |

**Not changed:**
- AUTH-LEDGER, legal approval states and acceptance oracles (0 oracle files differ from staging);
- corpus bytes and bundle signatures;
- the blind holdout, which was never accessed.

No paid infrastructure was added. **Nothing is merged to staging; that needs owner authorisation.**

## 1. Outcome per work package

| WP | Target | Result | Evidence |
| --- | --- | --- | --- |
| WP1 Persistent search (P0) | Disk-backed index; atomic publish and rollback; crash recovery; withdrawal enforced; benchmarks at 290/1k/4k/10k plus stress; **p95 ≤ 300 ms at 10 readers at 10k** | **Built; target not met at 10k.** The B1 evaluator stays, with postings in SQLite (ADR-0007). Results are byte-identical to the in-memory engine. The managed heap is about halved. 10-reader p95 is 77 ms at 290, 61 ms at 1k, **208 ms at 4k** and **1,166 ms at 10k**. Crash, corruption and truncation recovery were tested. The default engine stays `memory`; `disk` is opt-in | [INDEX_REPORT](../c15_index/INDEX_REPORT.md), [ADR-0007](../../../../docs/architecture/decisions/ADR-0007-PERSISTENT_SEARCH_INDEX.md) |
| WP2 Hybrid | Independent evaluation; RET-07 and RET-10; stronger models; reranking; persistent vectors; NL regression; **14/14 on the unchanged oracle** | **12/14; target not met.** RET-07 and RET-10 need contrary or paraphrase matching that no local permissive model does. e5-base and a cross-encoder reranker were evaluated with declared settings (no gain; reranker 1.4–4.6 s per query on CPU). The vector store persists and resumes. The provision-heading boost fixes the C14 natural-language regression ("summary court martial" now leads with the Army Act). Hybrid stays off by default | [HYBRID_EVAL](../c15_hybrid/HYBRID_EVAL.md), [DECLARATIONS](../c15_hybrid/DECLARATIONS.md) |
| WP3 Graph on PostgreSQL | Typed, evidence-bearing graph with eligibility | **Done.** Deterministic builder; atomic per-generation publish and verification; node, neighbourhood, path and statistics queries apply the hidden-document set on every request. All routes are within 300 ms at 10 readers on the sample | [GRAPH_REASONING_REPORT](../c15_graph/GRAPH_REASONING_REPORT.md), [ADR-0006](../../../../docs/architecture/decisions/ADR-0006-LEGAL-GRAPH-STORAGE-AND-REASONING-FOUNDATION.md), [API](../../../../docs/architecture/b1/C15_GRAPH_API.md) |
| WP4 Deterministic reasoning | Established / candidate / insufficient | **Done (foundation).** Strong Kleene rule engine with typed decision tables. The rule gate is closed at AUTH-LEDGER v0, so ESTABLISHED is impossible today and the response says so | same |
| WP5 Commander workspace | Task domains | **Done.** Six task areas: provisions with printed headings, safeguards, search-backed form candidates, questions for legal review. Each provision opens the shared graph (C15-INT-01) | [WORKSPACE_STUDIO_REPORT](../c15_workspace/WORKSPACE_STUDIO_REPORT.md) |
| WP6 Document Studio | Private drafting | **Done (foundation).** Per-user documents with block origins, versions, workflow labels (never approval), copy-pinned citations re-resolved on read, and HTML/Markdown export marked "Not legally approved" | same, [design note](../../../../docs/architecture/b1/C15_WORKSPACE_STUDIO.md) |
| WP7 Residuals | Density at 1366; procedural ranking; evidence consolidation; security and reliability tests; independent security review; housekeeping | **Done.** <ul><li>**Density at 1366:** 4 results fully visible (was 2).</li><li>**Procedural ranking:** heading boost (Q01 → Army Act; Q13 → s.39).</li><li>**Security review:** no critical or high findings; 2 medium and 3 low fixed with tests ([SECURITY_REVIEW](SECURITY_REVIEW.md)).</li><li>**Housekeeping:** 58 disposable test databases dropped and bench sites (≈2.9 GB) removed; evidence kept in git.</li></ul> | — |

## 2. Verification on the integrated branch

| Suite | Result |
| --- | --- |
| C# (SYN site, real sample, real e5-small and reranker models) | **205/205** |
| Playwright (SYN and real sample, Chromium, 1 worker) | **71/71** |
| Design checks (contrast, scaling, keymap, cache policy, capability matrix) | **117/117** |
| Retrieval oracle, hybrid off | **10/14**: RET-06, 07, 09 and 10 require hybrid, as on staging |
| Retrieval oracle, hybrid on (e5-small, floor 0.8579) | **12/14**: RET-07 and RET-10 open |

Integration fixes:
- the S1/S2 conflict in `SearchService.Reasons` was resolved by combining lazy reasons with the heading reason;
- the index ADR was renumbered to 0007;
- the W-06 journey now waits for the Studio document to render before counting.

## 3. Open issues carried to Cycle 16

1. **WP1b top-k evaluator:** the 10k latency is evaluator work per matching passage, not storage. A lazy, disk-backed text store is also needed: generation text is projected at about 7 GB for the full corpus. Linux has not been tested.
2. **RET-07 and RET-10:** need a legal-domain model for contrary and paraphrased holdings, or a reviewed synonym list, which is a legal-content decision. Q05 (s.80 heading only in the contents) and Q07 ("arrest" → s.101) are open for the same reasons.
3. **Commander source:** the workspace still reads held tables of contents through `ICommanderSource`. Switching to the graph API is a drop-in change but was not made in this cycle.
4. **Forms and competent authorities:** modelled but not populated; this needs the Form Discovery register. 1,583 unresolved citation references remain.
5. **Legal Reviewer workflow:** a blocking owner decision; until it exists, review states have no write path and nothing can be ESTABLISHED.
6. **Studio:** no retention policy, backup exclusion or DOCX export. The Readiness Report and template registry are blocked on the Form/Template Registry.
7. **Security residuals:** per-copy restriction in graph and reasoning (L4); rate limits and a Studio byte quota (L5); labels for reviewed edges (I7).

## 4. Constraints honoured

- No changes to the oracle or AUTH-LEDGER.
- No generative advice; the Assistant stays closed.
- No corpus acquisition.
- No paid infrastructure; models are local and permissively licensed, with vectors and models outside git.
- Credentials stay outside git and logs.
- No merge to staging.
