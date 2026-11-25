# Capability traceability matrix (Cycle 13, Track B)

- **Recorded:** 2026-11-25 (workstream B0). **Status:** PROPOSED for independent review.
- **Canonical form:** [`CAPABILITY_TRACEABILITY_MATRIX.csv`](CAPABILITY_TRACEABILITY_MATRIX.csv) (one row per capability, 16 columns). This page renders the same rows.
- **Scope:** the eight capability areas of the owner directive §18: 18.1 Universal Legal Search, 18.2 Judgment Intelligence, 18.3 Statutory Explorer, 18.4 Legal Knowledge Graph, 18.5 Commander Assistant (architected but not activated), 18.6 Document Studio, 18.7 Research Workspace, 18.8 Knowledge Administration. The decomposition into 52 capabilities is B0's; every area is covered (coordinator confirmed 2026-11-25).
- **Product references** use the stable IDs in [`docs/product/PRODUCT_VISION.md`](../product/PRODUCT_VISION.md) (PR-01..PR-30) and [`docs/product/COMMANDER_USE_CASES.md`](../product/COMMANDER_USE_CASES.md) (UC-01..UC-28). A reference means "this capability serves that requirement", not that the requirement is met.
- **Phases (directive milestones):** B0 architecture plus PoCs; **B1** minimum functional research prototype (offline install, local DB, immutable vault, real corpus subset, FTS plus hybrid where benchmarked, excerpts, PDF viewer, page navigation, provenance, basic auth, professional workspace); **B2** full eligible corpus with incremental ingestion and Admin staging, publication and withdrawal; **B3** research depth; *later* = behind a gate that cannot open in Cycle 13 (see the [revised execution plan](../planning/CYCLE13_EXECUTION_PLAN.md) §0.3). **Gated off = yes** means architected (module boundary, route returning `GATE_CLOSED`, data-model hook) but disabled. The commander assistant and every legal-rule feature are gated off.
- **Security and performance** columns reference [SECURITY_AND_DEPLOYMENT_ARCHITECTURE.md](SECURITY_AND_DEPLOYMENT_ARCHITECTURE.md) test ids (T-…) and PoC keys (P1–P9). Performance figures are **targets or estimates**, not measurements.
- **Data** columns reference the [data contract v1](../../app/contract/README.md) record kinds.

## 1. Summary

| Area | Capabilities | B1 | B2 | B3 | later | Gated off |
| --- | --- | --- | --- | --- | --- | --- |
| Universal legal search (18.1) | 7 | 7 | 0 | 0 | 0 | 0 |
| Judgment intelligence (18.2) | 7 | 0 | 0 | 5 | 2 | 1 |
| Statutory explorer (18.3) | 6 | 0 | 0 | 4 | 2 | 2 |
| Legal knowledge graph (18.4) | 6 | 0 | 1 | 5 | 0 | 0 |
| Commander assistant (18.5, architected, not activated) | 5 | 0 | 0 | 1 | 4 | 4 |
| Document Studio (18.6) | 5 | 0 | 0 | 3 | 2 | 2 |
| Research workspace (18.7) | 7 | 4 | 0 | 3 | 0 | 0 |
| Knowledge administration (18.8) | 9 | 6 | 1 | 2 | 0 | 1 |
| **Total** | **52** | **17** | **2** | **23** | **10** | **10** |

Phase counts use the first phase named for a capability (some start in B1 and complete in B2).

## 2. Overview by area

### 2.1 Universal legal search (18.1)

| ID | Capability | Product refs | Backend service | Frontend workspace | Phase | Gated off |
| --- | --- | --- | --- | --- | --- | --- |
| CAP-US-01 | Passage-level full-text search over the published corpus | PR-01; PR-12; PR-15; UC-01..UC-20 (research seeds) | search module (web) + index worker | Research workspace: search bar, results pane | B1 | no |
| CAP-US-02 | Identifier-aware queries (sections, rules, case numbers, neutral citations) | PR-01; PR-02; PR-06 | search module; query parser | Search bar with query chips (parsed identifiers shown) | B1 | no |
| CAP-US-03 | Semantic and hybrid retrieval with local embeddings | PR-01; PR-03 (later); PR-12 | embed worker (bulk, uploads); search module (query embedding) | Search results pane (match reason chips: lexical / semantic) | B1 | no |
| CAP-US-04 | Facets and filters | PR-01; PR-07 | search module | Facet rail (collapsible) | B1 (core facets); B3 (candidate-outcome and statute facets) | no |
| CAP-US-05 | Result excerpts with 'why relevant' and page anchor | PR-06; Architecture §10 | search module (snippet builder) | Result row component | B1 | no |
| CAP-US-06 | Open original PDF at page with hit highlighted | PR-06; T-03 | viewer endpoint (streams vault bytes after hash check) | Document pane (PDF viewer) | B1 | no |
| CAP-US-07 | Withdrawal- and restriction-consistent search | PR-13; PR-18; ADR-0002 d.7; T-07; T-14; PR-20 | search + admin modules; index worker | All result surfaces | B1 (restricted register); B2 (withdrawal with Admin staging) | no |

### 2.2 Judgment intelligence (18.2)

| ID | Capability | Product refs | Backend service | Frontend workspace | Phase | Gated off |
| --- | --- | --- | --- | --- | --- | --- |
| CAP-JI-01 | Judgment page with cover metadata and per-field status chips | PR-07; PR-14; PR-18 | catalogue module | Document pane: metadata header; evidence-status panel | B3 | no |
| CAP-JI-02 | Proceedings and identity (file ≠ judgment ≠ proceeding) | PR-07; Architecture §4 | catalogue module | Document pane: proceedings list; copies switcher | B3 | no |
| CAP-JI-03 | Candidate outcomes labelled with measured precision and coverage | PR-07; R13; CAPABILITY_RESTRICTIONS judicial_outcome_extraction | catalogue module | Document pane: outcome chip; evaluation popover | B3 | no |
| CAP-JI-04 | Statutes cited, cases cited, citing cases | PR-07; PR-08 | graph module | Context pane: 'Cited / Citing' tab | B3 | no |
| CAP-JI-05 | Holdings and propositions | PR-07; PR-08; CAPABILITY_RESTRICTIONS holdings_and_propositions, origin_labels_court_voice | catalogue module (Admin diagnostic route) | Admin diagnostics workspace | later (Admin diagnostic in B2) | no |
| CAP-JI-06 | Copy comparison and completeness flags | PR-14; Architecture §4 | catalogue + viewer | Document pane: copy switcher; split view | B3 | no |
| CAP-JI-07 | Structured research card (facts, issues, reasoning, later treatment, lessons) | PR-07 (full); PR-09 | Not applicable: gated, architected only | Not applicable: gated, architected only | later | yes |

### 2.3 Statutory explorer (18.3)

| ID | Capability | Product refs | Backend service | Frontend workspace | Phase | Gated off |
| --- | --- | --- | --- | --- | --- | --- |
| CAP-SE-01 | Act and Rules browser with section-level records | PR-02 | catalogue module | Statute workspace: TOC tree + section pane | B3 | no |
| CAP-SE-02 | Amendment footnotes as candidates; 'temporal chain not established' | PR-10; PR-11; TA-01..TA-05 (representational) | graph + catalogue | Section pane: amendment strip | B3 | no |
| CAP-SE-03 | As-of-date provision version view | PR-10 | Not applicable: gated, architected only | Section pane: date control (disabled) | later | yes |
| CAP-SE-04 | Related judgments per section | PR-02; PR-08 | graph module | Section pane: related judgments tab | B3 | no |
| CAP-SE-05 | Subordinate legislation and notifications | PR-02 | graph + catalogue | Statute workspace: related instruments | B3 | no |
| CAP-SE-06 | IPC→BNS / CrPC→BNSS / IEA→BSA correspondence | PR-10; TA-03 | Not applicable: gated, architected only | Not applicable: gated, architected only | later | yes |

### 2.4 Legal knowledge graph (18.4)

| ID | Capability | Product refs | Backend service | Frontend workspace | Phase | Gated off |
| --- | --- | --- | --- | --- | --- | --- |
| CAP-KG-01 | Neighbourhood exploration with typed edges | PR-08; T-05 | graph module (recursive CTE queries) | Graph workspace (Cytoscape.js canvas + list view) | B3 | no |
| CAP-KG-02 | Path between two nodes | PR-08 | graph module | Graph workspace | B3 | no |
| CAP-KG-03 | Edge evidence and anchors | PR-06; PR-08 | graph + viewer | Edge inspector panel | B3 | no |
| CAP-KG-04 | Edge-type legend with measured precision | PR-08; plan B8 | graph module | Graph legend | B3 | no |
| CAP-KG-05 | No-edge is not no-adverse-authority | Architecture §5; plan B8 | None recorded | Graph workspace empty state | B3 | no |
| CAP-KG-06 | Upload-derived candidate edges in staging | PR-17; UC-21; Ingestion §5 | ingest-parse worker; admin module | Admin staging workspace | B2 | no |

### 2.5 Commander assistant (18.5, architected, not activated)

| ID | Capability | Product refs | Backend service | Frontend workspace | Phase | Gated off |
| --- | --- | --- | --- | --- | --- | --- |
| CAP-CA-01 | Plain-English situation intake | PR-03; UC-01..UC-20 | assistant module (disabled) | Commander workspace shell (disabled state) | later | yes |
| CAP-CA-02 | Material-fact dialogue | PR-04 | assistant module (disabled) | Not applicable: gated, architected only | later | yes |
| CAP-CA-03 | Bounded, source-grounded response with uncertainty | PR-05; PR-06; PR-11 | assistant module (disabled) | Not applicable: gated, architected only | later | yes |
| CAP-CA-04 | Commander presentation of research results (plain-language view, no advice) | PR-15 | search module | Commander view toggle in research workspace | B3 | no |
| CAP-CA-05 | Procedural checklists and lessons | PR-09; PR-25 | Not applicable: gated, architected only | Not applicable: gated, architected only | later | yes |

### 2.6 Document Studio (18.6)

| ID | Capability | Product refs | Backend service | Frontend workspace | Phase | Gated off |
| --- | --- | --- | --- | --- | --- | --- |
| CAP-DS-01 | Session-isolated working area (upload, view, OCR, annotate, export) | PR-24 (view only); PR-26; UC-25 (view only) | studio module; ingest-ocr worker (session job type) | Document Studio workspace | B3 | no |
| CAP-DS-02 | Read-only forms registry view | PR-22; CAPABILITY_RESTRICTIONS form_field_lists | catalogue module | Document Studio: registry browser | B3 | no |
| CAP-DS-03 | Template-based draft generation | PR-21; PR-23; UC-24; UC-27 | studio module (disabled) | Not applicable: gated, architected only | later | yes |
| CAP-DS-04 | Document audit and readiness report | PR-24 (checks); PR-25; PR-27..PR-30; UC-25; UC-26; UC-28; PR-29 (readiness report, gated) | studio module (disabled) | Not applicable: gated, architected only | later | yes |
| CAP-DS-05 | Retention and cleanup of working sessions | PR-26; Document Studio §2 | studio module; cleanup task | Document Studio: session list | B3 | no |

### 2.7 Research workspace (18.7)

| ID | Capability | Product refs | Backend service | Frontend workspace | Phase | Gated off |
| --- | --- | --- | --- | --- | --- | --- |
| CAP-RW-01 | Persistent search and document tabs | PR-15; app/design | research module | Research workspace shell | B1 | no |
| CAP-RW-02 | Resizable panes (results / document / context) | app/design | research module | Research workspace shell | B1 | no |
| CAP-RW-03 | Notes and pinned passages | PR-13; PR-26 | research module | Context pane: notes tab | B3 | no |
| CAP-RW-04 | Copy citation and stable deep links | PR-06; plan B5 | viewer + catalogue | Citation button in document pane | B1 (citation); B2 (deep links across releases) | no |
| CAP-RW-05 | Provenance and evidence-status panels | PR-14; PR-18; plan B6 | catalogue module | Context pane: provenance tab; evidence tab | B1 | no |
| CAP-RW-06 | Related items | PR-08 | graph + catalogue | Context pane: related tab | B3 | no |
| CAP-RW-07 | Saved searches and research sets | PR-15 | research module | Left rail: saved items | B3 | no |

### 2.8 Knowledge administration (18.8)

| ID | Capability | Product refs | Backend service | Frontend workspace | Phase | Gated off |
| --- | --- | --- | --- | --- | --- | --- |
| CAP-KA-01 | Admin upload → staging → review → publish / withdraw / replace / reprocess | PR-16; PR-17; PR-18; UC-21; UC-23; ADR-0002 | admin module; ingest-parse, ingest-ocr, embed, index workers | Admin workspace: staging queue, review screen | B1 | no |
| CAP-KA-02 | Release bundle import, verification, generation switch, rollback | PR-12; PR-14; contract v1 | release-import worker | Admin workspace: releases | B1 | no |
| CAP-KA-03 | Restricted-material enforcement | T-14; ADR-0002 d.7; governance §3; PR-20 | release-import worker; admin module | Admin workspace: rejection notice (id only) | B1 | no |
| CAP-KA-04 | Accounts: local users, optional AD | PR-19; ADR-0002; D-05 | identity module | Admin workspace: accounts | B1 (local); B3 (AD) | no |
| CAP-KA-05 | Audit log review (metadata only) | PR-14; Architecture §11 | audit module | Admin workspace: audit | B3 | no |
| CAP-KA-06 | Legal Reviewer designation registry (inert) | PR-19; Document Studio 3.3; ADR-0003 | identity module | Admin workspace: designations (read-only notice) | B3 (model); activation later | yes |
| CAP-KA-07 | Review queues (non-cites edges, impact triggers, OCR low confidence) | PR-28; Document Studio 3.3; plan B2 | admin module | Admin workspace: queues | B2 (OCR list); B3 (edge/impact queues, view only) | no |
| CAP-KA-08 | Candidate-data banner driven by release metadata | PR-18; plan B11 | web shell | Global shell | B1 | no |
| CAP-KA-09 | Backup and restore | PR-14; T-08; PR-20 | backup task | Admin workspace: backup status | B1 (backup); B2 (full restore drill) | no |

## 3. Full traceability (all columns)

#### CAP-US-01: Passage-level full-text search over the published corpus

*Universal legal search (18.1)* · PR-01; PR-12; PR-15; UC-01..UC-20 (research seeds)

| Aspect | Detail |
| --- | --- |
| User workflow | Type query in persistent search bar → ranked passages → open document at page |
| Required data | documents.jsonl; derived_text passages (page, offsets); publication axis |
| Backend service | search module (web) + index worker |
| Storage / index model | PostgreSQL tsvector per passage (identifier-preserving + stemmed); GIN index; published view |
| Frontend workspace | Research workspace: search bar, results pane |
| Security | Authenticated User or Admin; published items only; server-side visibility filter; no query text in logs; Tests: T-SQL-01 (parameterised FTS input), T-NET-01 |
| Performance | Search p95 < 1 s at 10 concurrent queries on reference hardware (16 cores, 64 GB, 1 TB SSD), accuracy not sacrificed; sized for ~20 GB [P2] |
| Evidence / approval gates | Results labelled candidate where derived; no 'binding'/'current' ranking signal |
| Acceptance tests | Retrieval metrics recall@10/20, nDCG@10 on dev and held-out golden queries; withdrawal test; banner test |
| Phase | B1 |
| Gated off | no |
| Dependencies / limitations | P2 decides FTS vs BM25 index; golden set held out for evaluation only |

#### CAP-US-02: Identifier-aware queries (sections, rules, case numbers, neutral citations)

*Universal legal search (18.1)* · PR-01; PR-02; PR-06

| Aspect | Detail |
| --- | --- |
| User workflow | Query 's.69 Army Act', 'rule 22(3)(a)', '2025 INSC 549' → exact and normalised matches first |
| Required data | Passages; judicial.case_numbers, neutral_citation; statute normalisation table |
| Backend service | search module; query parser |
| Storage / index model | FTS 'simple' configuration column + synonym dictionary (AA→Army Act; court-martial↔court martial); B-tree on normalised identifiers |
| Frontend workspace | Search bar with query chips (parsed identifiers shown) |
| Security | Authenticated User or Admin; published items only; server-side visibility filter |
| Performance | Identifier queries p95 < 300 ms [P2] |
| Evidence / approval gates | Normalisation table is a technical artefact, not a legal mapping |
| Acceptance tests | Identifier query set (P2 queries_identifier) precision@5 |
| Phase | B1 |
| Gated off | no |
| Dependencies / limitations | Normalisation must not invent provisions; unresolved identifiers shown raw |

#### CAP-US-03: Semantic and hybrid retrieval with local embeddings

*Universal legal search (18.1)* · PR-01; PR-03 (later); PR-12

| Aspect | Detail |
| --- | --- |
| User workflow | Natural-language query → hybrid (lexical + vector, RRF) results with match reasons |
| Required data | Passage embeddings with model id and model-file hash |
| Backend service | embed worker (bulk, uploads); search module (query embedding) |
| Storage / index model | pgvector HNSW (halfvec) per passage; embedding generation table |
| Frontend workspace | Search results pane (match reason chips: lexical / semantic) |
| Security | Authenticated User or Admin; published items only; server-side visibility filter; models loaded from bundled hashed folder; no network |
| Performance | Query embedding < 100 ms; hybrid p95 < 1 s [P2, P3] |
| Evidence / approval gates | No relevance claim implies legal authority |
| Acceptance tests | Hybrid recall@20 ≥ best single method on held-out set, else ADR records why |
| Phase | B1 |
| Gated off | no |
| Dependencies / limitations | Model chosen in P3; bulk embeddings may be built online and shipped in the bundle; Later: hybrid RAG evidence packs reuse this service (PR #53 Retrieval §2-3) |

#### CAP-US-04: Facets and filters

*Universal legal search (18.1)* · PR-01; PR-07

| Aspect | Detail |
| --- | --- |
| User workflow | Narrow by court, bench, year, doc type, statute cited, publication state, candidate outcome label, OCR quality |
| Required data | Document fields; candidate outcomes (labelled); derived_text page quality |
| Backend service | search module |
| Storage / index model | Facet columns on documents; materialised counts per generation |
| Frontend workspace | Facet rail (collapsible) |
| Security | Authenticated User or Admin; published items only; server-side visibility filter |
| Performance | Facet counts < 300 ms |
| Evidence / approval gates | Outcome facet labelled 'candidate (measured P/coverage)'; hidden if owner decides (D-08) |
| Acceptance tests | Facet counts equal filtered result counts; outcome facet shows label and figures |
| Phase | B1 (core facets); B3 (candidate-outcome and statute facets) |
| Gated off | no |
| Dependencies / limitations | Statute facet depends on A-track citation normalisation |

#### CAP-US-05: Result excerpts with 'why relevant' and page anchor

*Universal legal search (18.1)* · PR-06; Architecture §10

| Aspect | Detail |
| --- | --- |
| User workflow | Each result shows passage excerpt with matched terms, page number, statute matched, evidence state |
| Required data | Passages; anchors; status axes |
| Backend service | search module (snippet builder) |
| Storage / index model | Stored passage text; ts_headline on passage only |
| Frontend workspace | Result row component |
| Security | Authenticated User or Admin; published items only; server-side visibility filter; snippets never from staged/withdrawn/restricted items |
| Performance | Snippet generation within the query budget |
| Evidence / approval gates | Excerpt from OCR text marked 'OCR, search only, not for quotation' |
| Acceptance tests | Snippet page equals opened page in ≥98% [P4] |
| Phase | B1 |
| Gated off | no |
| Dependencies / limitations | Later: claim/source presentation per PR #53 Final Claim §7; excerpts stay labelled derived |

#### CAP-US-06: Open original PDF at page with hit highlighted

*Universal legal search (18.1)* · PR-06; T-03

| Aspect | Detail |
| --- | --- |
| User workflow | Click result → PDF.js opens original bytes at page; native: text-layer highlight; scan: OCR box overlay |
| Required data | Vault original (sha256); OCR word boxes; anchors |
| Backend service | viewer endpoint (streams vault bytes after hash check) |
| Storage / index model | Vault (NTFS, content-addressed); word boxes in derived store |
| Frontend workspace | Document pane (PDF viewer) |
| Security | Authenticated User or Admin; published items only; server-side visibility filter; PDF.js isEvalSupported=false, scripting off, strict CSP; Tests: T-PDFJS-01, T-CACHE-01 |
| Performance | First page render < 1.5 s for typical judgment [P4] |
| Evidence / approval gates | Original bytes are the cited source; derived text layer labelled |
| Acceptance tests | Page correct ≥98%; native highlight ≥90%; scanned overlay per P4 |
| Phase | B1 |
| Gated off | no |
| Dependencies / limitations | Scanned highlight accuracy target set after P4; R2-N01 (PR #53 Serving §10) bounded authenticated range transport proof in P4 before enabling |

#### CAP-US-07: Withdrawal- and restriction-consistent search

*Universal legal search (18.1)* · PR-13; PR-18; ADR-0002 d.7; T-07; T-14; PR-20

| Aspect | Detail |
| --- | --- |
| User workflow | Admin withdraws → item disappears from FTS, vectors, suggestions, graph and caches; restricted items never present |
| Required data | Publication axis; restricted register |
| Backend service | search + admin modules; index worker |
| Storage / index model | Single PostgreSQL transaction boundary across passages, vectors and edges |
| Frontend workspace | All result surfaces |
| Security | Admin only, enforced at endpoint and service layer; audited (metadata only) for withdrawal; register fail-closed; Tests: T-VIS-02, T-VIS-03, T-CACHE-01, T-RM-04 |
| Performance | Withdrawal effective within the same transaction/job |
| Evidence / approval gates | Register `config/restricted_material.json` applied at import and publication |
| Acceptance tests | T-VIS-02, T-RM-01..03; contract tests test_restricted_material.py |
| Phase | B1 (restricted register); B2 (withdrawal with Admin staging) |
| Gated off | no |
| Dependencies / limitations | If a BM25 index is adopted (P2), generation check must block stale results; Serving fence via single delivery gateway (PR #53 Serving §1-3) |

#### CAP-JI-01: Judgment page with cover metadata and per-field status chips

*Judgment intelligence (18.2)* · PR-07; PR-14; PR-18

| Aspect | Detail |
| --- | --- |
| User workflow | Open judgment → metadata panel (court, bench, case numbers, parties, judges, dates) each with origin and axis chip |
| Required data | document records (judicial block; field_origin; status_axes) |
| Backend service | catalogue module |
| Storage / index model | documents table + JSONB for variable metadata |
| Frontend workspace | Document pane: metadata header; evidence-status panel |
| Security | Authenticated User or Admin; published items only; server-side visibility filter; Tests: T-XSS-01 |
| Performance | Page load < 1 s |
| Evidence / approval gates | Every field shows its origin (crawler/rule/llm/human) and evidence fidelity |
| Acceptance tests | B4-style walkthrough: 10 research tasks; every field shows axis |
| Phase | B3 |
| Gated off | no |
| Dependencies / limitations | Values are candidates unless DOCUMENTARY_CHECKED with review ref |

#### CAP-JI-02: Proceedings and identity (file ≠ judgment ≠ proceeding)

*Judgment intelligence (18.2)* · PR-07; Architecture §4

| Aspect | Detail |
| --- | --- |
| User workflow | See all proceedings in a judgment and all copies of a judgment |
| Required data | judgment_identity_id; alternate copies; A-track identity export |
| Backend service | catalogue module |
| Storage / index model | judgment, proceeding, source_copy tables with FKs |
| Frontend workspace | Document pane: proceedings list; copies switcher |
| Security | Authenticated User or Admin; published items only; server-side visibility filter |
| Performance | None recorded |
| Evidence / approval gates | Identity canonicalisation is a Track A candidate (A-track graph workstream) |
| Acceptance tests | Same-identity different-hash copies kept as alternates (Ingestion §7) |
| Phase | B3 |
| Gated off | no |
| Dependencies / limitations | Depends on Track A identity output via contract minor version |

#### CAP-JI-03: Candidate outcomes labelled with measured precision and coverage

*Judgment intelligence (18.2)* · PR-07; R13; CAPABILITY_RESTRICTIONS judicial_outcome_extraction

| Aspect | Detail |
| --- | --- |
| User workflow | Outcome chip per proceeding: label + 'candidate, P x%, coverage y%, report link' |
| Required data | candidate records (outcome) with evaluation_ref and capability_restriction |
| Backend service | catalogue module |
| Storage / index model | candidates table (type=outcome) |
| Frontend workspace | Document pane: outcome chip; evaluation popover |
| Security | Authenticated User or Admin; published items only; server-side visibility filter |
| Performance | None recorded |
| Evidence / approval gates | NON_OPERATIONAL_RESEARCH_ONLY (C11 F05, F08 deferred); never in summaries; owner may hide (D-08) |
| Acceptance tests | Label test: every outcome shows candidate marker and figures or 'not evaluated' |
| Phase | B3 |
| Gated off | no |
| Dependencies / limitations | V3 targets not met; A-track outcome V4 may change figures |

#### CAP-JI-04: Statutes cited, cases cited, citing cases

*Judgment intelligence (18.2)* · PR-07; PR-08

| Aspect | Detail |
| --- | --- |
| User workflow | Lists of cited provisions and cases, resolved to doc ids where possible; unresolved shown raw |
| Required data | candidate graph_edge records (CITES_PROVISION, CITES_JUDGMENT) |
| Backend service | graph module |
| Storage / index model | edges table (typed, anchored) |
| Frontend workspace | Context pane: 'Cited / Citing' tab |
| Security | Authenticated User or Admin; published items only; server-side visibility filter |
| Performance | < 500 ms |
| Evidence / approval gates | Citation edges are extraction candidates; no treatment inferred |
| Acceptance tests | Every listed edge opens its evidence passage |
| Phase | B3 |
| Gated off | no |
| Dependencies / limitations | Resolution ambiguity kept unresolved, never guessed; Later GraphRAG consumes these edges only through the A4/A5 crosswalk adapter (PR #53 Crosswalk §6) |

#### CAP-JI-05: Holdings and propositions

*Judgment intelligence (18.2)* · PR-07; PR-08; CAPABILITY_RESTRICTIONS holdings_and_propositions, origin_labels_court_voice

| Aspect | Detail |
| --- | --- |
| User workflow | Admin diagnostic view only |
| Required data | candidate records (holding) with capability_restriction=HIDDEN_FROM_USERS |
| Backend service | catalogue module (Admin diagnostic route) |
| Storage / index model | candidates table (type=holding) |
| Frontend workspace | Admin diagnostics workspace |
| Security | Admin only, enforced at endpoint and service layer; audited (metadata only) |
| Performance | None recorded |
| Evidence / approval gates | Hidden from Users until D-08 bar (≥80% P / ≥60% R on new reference); C11 F06, F07 deferred |
| Acceptance tests | Contract rule HOLDINGS_HIDDEN; API test: User endpoint never returns holdings |
| Phase | later (Admin diagnostic in B2) |
| Gated off | no |
| Dependencies / limitations | C12 precision 41.7% / recall 29.3%. The Admin-only diagnostic departs from equal research access (PR-01, ADR-0002 d.1): recorded as an exception for owner approval under D-08, expiring when the D-08 bar is met or at the Cycle 14 review |

#### CAP-JI-06: Copy comparison and completeness flags

*Judgment intelligence (18.2)* · PR-14; Architecture §4

| Aspect | Detail |
| --- | --- |
| User workflow | Compare alternate copies side by side; see truncated/unopenable flags |
| Required data | source_copy.completeness; alternate_copy_sha256 |
| Backend service | catalogue + viewer |
| Storage / index model | source_copy table |
| Frontend workspace | Document pane: copy switcher; split view |
| Security | Authenticated User or Admin; published items only; server-side visibility filter |
| Performance | None recorded |
| Evidence / approval gates | Completeness is technical, not legal |
| Acceptance tests | 19 truncated-at-source files show a warning |
| Phase | B3 |
| Gated off | no |
| Dependencies / limitations | None recorded |

#### CAP-JI-07: Structured research card (facts, issues, reasoning, later treatment, lessons)

*Judgment intelligence (18.2)* · PR-07 (full); PR-09

| Aspect | Detail |
| --- | --- |
| User workflow | Architected only |
| Required data | Propositions, treatment edges, lessons (future) |
| Backend service | Not applicable: gated, architected only |
| Storage / index model | Not applicable: gated, architected only |
| Frontend workspace | Not applicable: gated, architected only |
| Security | Not applicable: gated, architected only |
| Performance | Not applicable: gated, architected only |
| Evidence / approval gates | Reasoning-feature gate (plan §7) and D-08 |
| Acceptance tests | Not applicable: gated, architected only |
| Phase | later |
| Gated off | yes |
| Dependencies / limitations | Requires verified propositions; no legal reasoning in Cycle 13 |

#### CAP-SE-01: Act and Rules browser with section-level records

*Statutory explorer (18.3)* · PR-02

| Aspect | Detail |
| --- | --- |
| User workflow | Open Act → table of contents → section text with page anchors |
| Required data | Act/Rules documents; data/sections records (via contract minor version) |
| Backend service | catalogue module |
| Storage / index model | sections table keyed doc_id#sNN |
| Frontend workspace | Statute workspace: TOC tree + section pane |
| Security | Authenticated User or Admin; published items only; server-side visibility filter |
| Performance | Section open < 500 ms |
| Evidence / approval gates | Section text from India Code compilations is a GOVERNMENT_COMPILATION, provenance shown |
| Acceptance tests | Open each Act listed in CLAUDE.md scope; TOC complete vs source |
| Phase | B3 |
| Gated off | no |
| Dependencies / limitations | Section records need a contract v1 minor version (provision/section schema) |

#### CAP-SE-02: Amendment footnotes as candidates; 'temporal chain not established'

*Statutory explorer (18.3)* · PR-10; PR-11; TA-01..TA-05 (representational)

| Aspect | Detail |
| --- | --- |
| User workflow | Section shows footnotes (e.g. 'Omitted by…') as candidate amendment edges with evidence; chain status shown |
| Required data | Candidate edges (OMITS_PROVISION etc.); amendment_chain_status |
| Backend service | graph + catalogue |
| Storage / index model | edges table; provision axis |
| Frontend workspace | Section pane: amendment strip |
| Security | Authenticated User or Admin; published items only; server-side visibility filter |
| Performance | None recorded |
| Evidence / approval gates | Legal applicability stays NOT_ESTABLISHED/UNRESOLVED; no as-of answer asserted |
| Acceptance tests | Representational fixtures TA-01..05 render 'blocked/unresolved' where evidence is missing |
| Phase | B3 |
| Gated off | no |
| Dependencies / limitations | A-track statutory workstream provides provision versions |

#### CAP-SE-03: As-of-date provision version view

*Statutory explorer (18.3)* · PR-10

| Aspect | Detail |
| --- | --- |
| User workflow | Architected: choose a date → version valid then |
| Required data | ProvisionVersion with valid-time intervals (A-track) |
| Backend service | Not applicable: gated, architected only |
| Storage / index model | provision_version table (valid-time) |
| Frontend workspace | Section pane: date control (disabled) |
| Security | Not applicable: gated, architected only |
| Performance | Not applicable: gated, architected only |
| Evidence / approval gates | GA5 legal decision; reasoning-feature gate |
| Acceptance tests | Not applicable: gated, architected only |
| Phase | later |
| Gated off | yes |
| Dependencies / limitations | Needs evidenced commencement chains and legal review |

#### CAP-SE-04: Related judgments per section

*Statutory explorer (18.3)* · PR-02; PR-08

| Aspect | Detail |
| --- | --- |
| User workflow | Section → judgments citing it (candidate links) with evidence passage |
| Required data | CITES_PROVISION edges (C11: 11,076 rows, unevaluated) |
| Backend service | graph module |
| Storage / index model | edges table |
| Frontend workspace | Section pane: related judgments tab |
| Security | Authenticated User or Admin; published items only; server-side visibility filter |
| Performance | < 1 s |
| Evidence / approval gates | Per-type measured precision shown or 'not evaluated' |
| Acceptance tests | Each link opens evidence passage |
| Phase | B3 |
| Gated off | no |
| Dependencies / limitations | C11 links unevaluated; V13-01 noise known |

#### CAP-SE-05: Subordinate legislation and notifications

*Statutory explorer (18.3)* · PR-02

| Aspect | Detail |
| --- | --- |
| User workflow | Act → rules, regulations and notifications listed as 'implements' candidates |
| Required data | IMPLEMENTS edges; parent_doc_id |
| Backend service | graph + catalogue |
| Storage / index model | edges; documents.parent_doc_id |
| Frontend workspace | Statute workspace: related instruments |
| Security | Authenticated User or Admin; published items only; server-side visibility filter |
| Performance | None recorded |
| Evidence / approval gates | Candidate relation; enabling-power citation shown where present |
| Acceptance tests | None recorded |
| Phase | B3 |
| Gated off | no |
| Dependencies / limitations | None recorded |

#### CAP-SE-06: IPC→BNS / CrPC→BNSS / IEA→BSA correspondence

*Statutory explorer (18.3)* · PR-10; TA-03

| Aspect | Detail |
| --- | --- |
| User workflow | Architected only |
| Required data | RE_ENACTED_AS edges with correspondence source |
| Backend service | Not applicable: gated, architected only |
| Storage / index model | edges |
| Frontend workspace | Not applicable: gated, architected only |
| Security | Not applicable: gated, architected only |
| Performance | Not applicable: gated, architected only |
| Evidence / approval gates | Legal review of correspondence; never shown as equivalence |
| Acceptance tests | Not applicable: gated, architected only |
| Phase | later |
| Gated off | yes |
| Dependencies / limitations | Not applicable: gated, architected only |

#### CAP-KG-01: Neighbourhood exploration with typed edges

*Legal knowledge graph (18.4)* · PR-08; T-05

| Aspect | Detail |
| --- | --- |
| User workflow | From any node, expand neighbours; filter by edge type and confidence |
| Required data | Candidate graph_edge records; nodes (documents, provisions, judgments) |
| Backend service | graph module (recursive CTE queries) |
| Storage / index model | edges table + node views |
| Frontend workspace | Graph workspace (Cytoscape.js canvas + list view) |
| Security | Authenticated User or Admin; published items only; server-side visibility filter |
| Performance | Neighbourhood query < 1 s on full candidate data |
| Evidence / approval gates | Every non-CITES edge shows 'proposed, not verified' |
| Acceptance tests | Label test: every non-cites edge renders unverified marker |
| Phase | B3 |
| Gated off | no |
| Dependencies / limitations | Later legal GraphRAG traversal (PR #53 Retrieval §4, §7); candidate edges remain leads |

#### CAP-KG-02: Path between two nodes

*Legal knowledge graph (18.4)* · PR-08

| Aspect | Detail |
| --- | --- |
| User workflow | Pick two nodes → shortest typed paths |
| Required data | edges |
| Backend service | graph module |
| Storage / index model | recursive CTE with depth limit |
| Frontend workspace | Graph workspace |
| Security | Authenticated User or Admin; published items only; server-side visibility filter |
| Performance | < 2 s up to depth 4 |
| Evidence / approval gates | Path is navigation, not legal reasoning |
| Acceptance tests | Path query returns within target |
| Phase | B3 |
| Gated off | no |
| Dependencies / limitations | None recorded |

#### CAP-KG-03: Edge evidence and anchors

*Legal knowledge graph (18.4)* · PR-06; PR-08

| Aspect | Detail |
| --- | --- |
| User workflow | Click edge → evidence sentence and source page |
| Required data | anchors on candidates |
| Backend service | graph + viewer |
| Storage / index model | edges.anchor FK to passages |
| Frontend workspace | Edge inspector panel |
| Security | Authenticated User or Admin; published items only; server-side visibility filter |
| Performance | None recorded |
| Evidence / approval gates | Evidence shown verbatim; OCR evidence marked |
| Acceptance tests | Every edge opens its evidence passage |
| Phase | B3 |
| Gated off | no |
| Dependencies / limitations | None recorded |

#### CAP-KG-04: Edge-type legend with measured precision

*Legal knowledge graph (18.4)* · PR-08; plan B8

| Aspect | Detail |
| --- | --- |
| User workflow | Legend lists each edge type with per-type precision (A-track) or 'not evaluated' |
| Required data | evaluation_ref per edge type |
| Backend service | graph module |
| Storage / index model | edge_type_evaluation table |
| Frontend workspace | Graph legend |
| Security | Authenticated User or Admin; published items only; server-side visibility filter |
| Performance | None recorded |
| Evidence / approval gates | Figures carry 'no human has checked this figure' until a human does |
| Acceptance tests | Legend test |
| Phase | B3 |
| Gated off | no |
| Dependencies / limitations | Depends on A-track graph evaluation |

#### CAP-KG-05: No-edge is not no-adverse-authority

*Legal knowledge graph (18.4)* · Architecture §5; plan B8

| Aspect | Detail |
| --- | --- |
| User workflow | Empty neighbourhoods show the explicit notice |
| Required data | None recorded |
| Backend service | None recorded |
| Storage / index model | None recorded |
| Frontend workspace | Graph workspace empty state |
| Security | None recorded |
| Performance | None recorded |
| Evidence / approval gates | Mandatory notice |
| Acceptance tests | UI test: notice present on empty results |
| Phase | B3 |
| Gated off | no |
| Dependencies / limitations | None recorded |

#### CAP-KG-06: Upload-derived candidate edges in staging

*Legal knowledge graph (18.4)* · PR-17; UC-21; Ingestion §5

| Aspect | Detail |
| --- | --- |
| User workflow | Admin reviews suggested edges for a staged upload before publication |
| Required data | Candidate edges from ingest worker |
| Backend service | ingest-parse worker; admin module |
| Storage / index model | staging edges table (not in published view) |
| Frontend workspace | Admin staging workspace |
| Security | Admin only, enforced at endpoint and service layer; audited (metadata only) |
| Performance | None recorded |
| Evidence / approval gates | Publication is not legal approval; claimed supersession stays POSSIBLY_SUPERSEDES_DOCUMENT |
| Acceptance tests | Staged edges invisible to Users (T-VIS-01) |
| Phase | B2 |
| Gated off | no |
| Dependencies / limitations | Link suggestion uses deterministic citation extraction only (no LLM) |

#### CAP-CA-01: Plain-English situation intake

*Commander assistant (18.5, architected, not activated)* · PR-03; UC-01..UC-20

| Aspect | Detail |
| --- | --- |
| User workflow | Architected; route exists returning GATE_CLOSED |
| Required data | Scenario records (future) |
| Backend service | assistant module (disabled) |
| Storage / index model | scenario tables (empty) |
| Frontend workspace | Commander workspace shell (disabled state) |
| Security | Feature gate cannot open while AUTH-LEDGER v0; Tests: T-GATE-01 |
| Performance | Not applicable: gated, architected only |
| Evidence / approval gates | Reasoning-feature gate (plan §7): Legal Reviewer appointed, tier table, T1/T2 approvals, targets met, benchmark reviewed |
| Acceptance tests | T-GATE-01: enabling refused |
| Phase | later |
| Gated off | yes |
| Dependencies / limitations | No legal reasoning in Cycle 13; Future agentic orchestrator and policy gate (PR #53 Agentic §1-8); not implemented |

#### CAP-CA-02: Material-fact dialogue

*Commander assistant (18.5, architected, not activated)* · PR-04

| Aspect | Detail |
| --- | --- |
| User workflow | Architected only |
| Required data | MaterialFact, ApplicabilityPredicate (future) |
| Backend service | assistant module (disabled) |
| Storage / index model | Not applicable: gated, architected only |
| Frontend workspace | Not applicable: gated, architected only |
| Security | Not applicable: gated, architected only |
| Performance | Not applicable: gated, architected only |
| Evidence / approval gates | As CAP-CA-01 |
| Acceptance tests | Not applicable: gated, architected only |
| Phase | later |
| Gated off | yes |
| Dependencies / limitations | Not applicable: gated, architected only |

#### CAP-CA-03: Bounded, source-grounded response with uncertainty

*Commander assistant (18.5, architected, not activated)* · PR-05; PR-06; PR-11

| Aspect | Detail |
| --- | --- |
| User workflow | Architected only |
| Required data | Approved propositions and provision versions (future) |
| Backend service | assistant module (disabled) |
| Storage / index model | Not applicable: gated, architected only |
| Frontend workspace | Not applicable: gated, architected only |
| Security | Prompt-injection isolation before any model |
| Performance | Not applicable: gated, architected only |
| Evidence / approval gates | As CAP-CA-01; local LLM gate (assessment §9) |
| Acceptance tests | Not applicable: gated, architected only |
| Phase | later |
| Gated off | yes |
| Dependencies / limitations | Not applicable: gated, architected only; Future final-claim verification and output authorisation (PR #53 Final Claim) |

#### CAP-CA-04: Commander presentation of research results (plain-language view, no advice)

*Commander assistant (18.5, architected, not activated)* · PR-15

| Aspect | Detail |
| --- | --- |
| User workflow | Same published search in a simplified layout: fewer facets, larger excerpts, provenance always visible |
| Required data | Same as search |
| Backend service | search module |
| Storage / index model | Same as search |
| Frontend workspace | Commander view toggle in research workspace |
| Security | Authenticated User or Admin; published items only; server-side visibility filter |
| Performance | As search |
| Evidence / approval gates | Banner and candidate labels unchanged; no conclusions generated |
| Acceptance tests | Both roles can open both views (PR-15) |
| Phase | B3 |
| Gated off | no |
| Dependencies / limitations | Presentation only; no scenario logic |

#### CAP-CA-05: Procedural checklists and lessons

*Commander assistant (18.5, architected, not activated)* · PR-09; PR-25

| Aspect | Detail |
| --- | --- |
| User workflow | Architected only |
| Required data | ChecklistItem, LegalLesson (future) |
| Backend service | Not applicable: gated, architected only |
| Storage / index model | Not applicable: gated, architected only |
| Frontend workspace | Not applicable: gated, architected only |
| Security | Not applicable: gated, architected only |
| Performance | Not applicable: gated, architected only |
| Evidence / approval gates | T1/T2 approvals per Document Studio 3.3 |
| Acceptance tests | Not applicable: gated, architected only |
| Phase | later |
| Gated off | yes |
| Dependencies / limitations | Not applicable: gated, architected only; Future deterministic legal engine (PR #53 Engine) |

#### CAP-DS-01: Session-isolated working area (upload, view, OCR, annotate, export)

*Document Studio (18.6)* · PR-24 (view only); PR-26; UC-25 (view only)

| Aspect | Detail |
| --- | --- |
| User workflow | Any user opens a working session, uploads PDF/DOCX/scan, views, runs OCR, annotates, exports annotated copy |
| Required data | Working files (never in vault) |
| Backend service | studio module; ingest-ocr worker (session job type) |
| Storage / index model | sessions\<user>\ folder; session tables with owner_id; no shared index |
| Frontend workspace | Document Studio workspace |
| Security | Owner-only (owner_id checked on every read/write/download, Admin included); excluded from shared indexes and default backups; parser isolation; Tests: T-PARSE-01..05, T-OWN-01..03, T-CACHE-01, T-INJ-01 |
| Performance | OCR of 20-page scan < 2 min on reference CPU (estimate) |
| Evidence / approval gates | No checks, no compliance, no rules |
| Acceptance tests | T-OWN-01..03; T-INJ-01; temp derivatives cleaned |
| Phase | B3 |
| Gated off | no |
| Dependencies / limitations | B3 research depth (directive milestones) |

#### CAP-DS-02: Read-only forms registry view

*Document Studio (18.6)* · PR-22; CAPABILITY_RESTRICTIONS form_field_lists

| Aspect | Detail |
| --- | --- |
| User workflow | Browse form families with source page anchors, labelled DISCOVERED_FROM_SOURCE_NOT_LEGALLY_APPROVED |
| Required data | candidate records (form) |
| Backend service | catalogue module |
| Storage / index model | candidates (type=form) |
| Frontend workspace | Document Studio: registry browser |
| Security | Authenticated User or Admin; published items only; server-side visibility filter |
| Performance | None recorded |
| Evidence / approval gates | usable_as_template=false (contract); WSG-R04 deferred |
| Acceptance tests | Label test; no fill action exists |
| Phase | B3 |
| Gated off | no |
| Dependencies / limitations | None recorded |

#### CAP-DS-03: Template-based draft generation

*Document Studio (18.6)* · PR-21; PR-23; UC-24; UC-27

| Aspect | Detail |
| --- | --- |
| User workflow | Architected only |
| Required data | FormTemplate with T2 approval (future) |
| Backend service | studio module (disabled) |
| Storage / index model | Not applicable: gated, architected only |
| Frontend workspace | Not applicable: gated, architected only |
| Security | Not applicable: gated, architected only |
| Performance | Not applicable: gated, architected only |
| Evidence / approval gates | T2 approval per output class (Document Studio 3.3) |
| Acceptance tests | T-GATE-01 |
| Phase | later |
| Gated off | yes |
| Dependencies / limitations | Not applicable: gated, architected only; Future deterministic engine shared with Document Studio (PR #53 Engine §1, Agentic §4) |

#### CAP-DS-04: Document audit and readiness report

*Document Studio (18.6)* · PR-24 (checks); PR-25; PR-27..PR-30; UC-25; UC-26; UC-28; PR-29 (readiness report, gated)

| Aspect | Detail |
| --- | --- |
| User workflow | Architected only |
| Required data | DocumentConstraint (future) |
| Backend service | studio module (disabled) |
| Storage / index model | Not applicable: gated, architected only |
| Frontend workspace | Not applicable: gated, architected only |
| Security | Not applicable: gated, architected only |
| Performance | Not applicable: gated, architected only |
| Evidence / approval gates | T1/T2 approvals; independent oracles |
| Acceptance tests | T-GATE-01 |
| Phase | later |
| Gated off | yes |
| Dependencies / limitations | No compliance logic in Cycle 13; Future deterministic engine readiness checks (PR #53 Engine §3) |

#### CAP-DS-05: Retention and cleanup of working sessions

*Document Studio (18.6)* · PR-26; Document Studio §2

| Aspect | Detail |
| --- | --- |
| User workflow | Sessions expire after configured TTL; user can delete now |
| Required data | Session metadata |
| Backend service | studio module; cleanup task |
| Storage / index model | session tables; folder deletion |
| Frontend workspace | Document Studio: session list |
| Security | Owner-only (owner_id checked on every read/write/download, Admin included); excluded from shared indexes and default backups |
| Performance | Cleanup job daily |
| Evidence / approval gates | None recorded |
| Acceptance tests | Expired session files absent from disk and DB |
| Phase | B3 |
| Gated off | no |
| Dependencies / limitations | None recorded |

#### CAP-RW-01: Persistent search and document tabs

*Research workspace (18.7)* · PR-15; app/design

| Aspect | Detail |
| --- | --- |
| User workflow | Search bar stays visible; documents open in tabs; tabs survive reload |
| Required data | Workspace state (owner) |
| Backend service | research module |
| Storage / index model | workspace table (owner_id, JSON layout) |
| Frontend workspace | Research workspace shell |
| Security | Owner-only (owner_id checked on every read/write/download, Admin included); excluded from shared indexes and default backups |
| Performance | Tab switch < 100 ms (client) |
| Evidence / approval gates | None recorded |
| Acceptance tests | Keyboard: Ctrl+K focus search; Ctrl+W close tab |
| Phase | B1 |
| Gated off | no |
| Dependencies / limitations | None recorded |

#### CAP-RW-02: Resizable panes (results / document / context)

*Research workspace (18.7)* · app/design

| Aspect | Detail |
| --- | --- |
| User workflow | Drag dividers; collapse panes; layout remembered |
| Required data | Workspace state |
| Backend service | research module |
| Storage / index model | workspace table |
| Frontend workspace | Research workspace shell |
| Security | Owner-only (owner_id checked on every read/write/download, Admin included); excluded from shared indexes and default backups |
| Performance | 60 fps drag on reference client (target) |
| Evidence / approval gates | None recorded |
| Acceptance tests | Layout works at 1366×768, 1920×1080, 2560×1440 |
| Phase | B1 |
| Gated off | no |
| Dependencies / limitations | None recorded |

#### CAP-RW-03: Notes and pinned passages

*Research workspace (18.7)* · PR-13; PR-26

| Aspect | Detail |
| --- | --- |
| User workflow | Pin a passage with an anchor; write a note; notes private to owner |
| Required data | Anchors; note text (owner) |
| Backend service | research module |
| Storage / index model | notes table (owner_id); not indexed in shared search |
| Frontend workspace | Context pane: notes tab |
| Security | Owner-only (owner_id checked on every read/write/download, Admin included); excluded from shared indexes and default backups; note text never logged; Tests: T-XSS-01, T-OWN-01 |
| Performance | None recorded |
| Evidence / approval gates | Notes are personal research, never corpus |
| Acceptance tests | T-OWN-01 for notes; notes absent from shared search |
| Phase | B3 |
| Gated off | no |
| Dependencies / limitations | None recorded |

#### CAP-RW-04: Copy citation and stable deep links

*Research workspace (18.7)* · PR-06; plan B5

| Aspect | Detail |
| --- | --- |
| User workflow | Copy citation: doc id, copy sha256 prefix, page, paragraph (if printed), release id; deep link resolves after updates |
| Required data | Anchors; release generations |
| Backend service | viewer + catalogue |
| Storage / index model | release_generation; alias table |
| Frontend workspace | Citation button in document pane |
| Security | Authenticated User or Admin; published items only; server-side visibility filter |
| Performance | None recorded |
| Evidence / approval gates | Link to a superseded copy resolves with notice |
| Acceptance tests | Deep link survives N→N+1 import |
| Phase | B1 (citation); B2 (deep links across releases) |
| Gated off | no |
| Dependencies / limitations | Evidence keys PageKey/SpanKey (contract evidence.py; PR #53 Crosswalk §2) |

#### CAP-RW-05: Provenance and evidence-status panels

*Research workspace (18.7)* · PR-14; PR-18; plan B6

| Aspect | Detail |
| --- | --- |
| User workflow | Panel shows source URL, retrieved_at, sha256, HF revision, release, pipeline/OCR versions, aliases, alternates, marking, completeness, publication history; and all seven axes |
| Required data | document provenance; status_axes; derived_text pipeline |
| Backend service | catalogue module |
| Storage / index model | documents; provenance; publication_record |
| Frontend workspace | Context pane: provenance tab; evidence tab |
| Security | Authenticated User or Admin; published items only; server-side visibility filter |
| Performance | < 300 ms |
| Evidence / approval gates | Axes displayed separately; never collapsed into one 'verified' |
| Acceptance tests | Any hit traceable to HF bytes at pinned revision; hash check passes |
| Phase | B1 |
| Gated off | no |
| Dependencies / limitations | None recorded |

#### CAP-RW-06: Related items

*Research workspace (18.7)* · PR-08

| Aspect | Detail |
| --- | --- |
| User workflow | Context pane lists same-case copies, citing/cited items, same-section judgments |
| Required data | Edges; identity |
| Backend service | graph + catalogue |
| Storage / index model | edges |
| Frontend workspace | Context pane: related tab |
| Security | Authenticated User or Admin; published items only; server-side visibility filter |
| Performance | < 500 ms |
| Evidence / approval gates | Relations labelled by type and confidence |
| Acceptance tests | None recorded |
| Phase | B3 |
| Gated off | no |
| Dependencies / limitations | None recorded |

#### CAP-RW-07: Saved searches and research sets

*Research workspace (18.7)* · PR-15

| Aspect | Detail |
| --- | --- |
| User workflow | Save a query with filters; collect documents into a named set (owner only) |
| Required data | Owner data |
| Backend service | research module |
| Storage / index model | saved_search, research_set tables (owner_id) |
| Frontend workspace | Left rail: saved items |
| Security | Owner-only (owner_id checked on every read/write/download, Admin included); excluded from shared indexes and default backups |
| Performance | None recorded |
| Evidence / approval gates | None recorded |
| Acceptance tests | T-OWN-01 for sets |
| Phase | B3 |
| Gated off | no |
| Dependencies / limitations | None recorded |

#### CAP-KA-01: Admin upload → staging → review → publish / withdraw / replace / reprocess

*Knowledge administration (18.8)* · PR-16; PR-17; PR-18; UC-21; UC-23; ADR-0002

| Aspect | Detail |
| --- | --- |
| User workflow | Admin uploads → quarantine and checks → extraction/OCR → review metadata and quality → publish; later withdraw or replace |
| Required data | Upload bytes; candidate metadata; publication records |
| Backend service | admin module; ingest-parse, ingest-ocr, embed, index workers |
| Storage / index model | staging folder; vault; submission, ingestion_job, publication_record tables |
| Frontend workspace | Admin workspace: staging queue, review screen |
| Security | Admin only, enforced at endpoint and service layer; audited (metadata only); parser isolation; register check at publication; Tests: T-PARSE-01..05, T-RM-02, T-AUTH-01, T-SQL-01, T-INJ-01 |
| Performance | Upload to searchable < 10 min for a 20-page native PDF (estimate) |
| Evidence / approval gates | Publication ≠ legal approval; label ADMIN_PUBLISHED_UNVERIFIED |
| Acceptance tests | Ingestion §7 tests; T-AUTH-01; round trip upload→publish→search→withdraw |
| Phase | B1 |
| Gated off | no |
| Dependencies / limitations | None recorded |

#### CAP-KA-02: Release bundle import, verification, generation switch, rollback

*Knowledge administration (18.8)* · PR-12; PR-14; contract v1

| Aspect | Detail |
| --- | --- |
| User workflow | Admin selects bundle on media → verify → import to new generation → smoke queries → switch; rollback to N-1 |
| Required data | Release bundle (contract v1) |
| Backend service | release-import worker |
| Storage / index model | releases folder; release_generation tables |
| Frontend workspace | Admin workspace: releases |
| Security | Admin only, enforced at endpoint and service layer; audited (metadata only); pinned Ed25519 key; dev keys refused; Tests: T-UPD-01..03, T-VIS-03, T-LEDGER-01, T-PARSE-04 |
| Performance | Subset import (B1) and full-corpus import within one working day on reference hardware (estimate) [P6, P8] |
| Evidence / approval gates | AUTH-LEDGER v0 ⇒ only T0 records; banner required |
| Acceptance tests | app/contract tests; T-UPD-01..03 |
| Phase | B1 |
| Gated off | no |
| Dependencies / limitations | Exclusion acceptance record and restore authority (PR #53 Serving §4, §8) |

#### CAP-KA-03: Restricted-material enforcement

*Knowledge administration (18.8)* · T-14; ADR-0002 d.7; governance §3; PR-20

| Aspect | Detail |
| --- | --- |
| User workflow | Register applied at bundle build, import, upload and publication; hits rejected and logged by id |
| Required data | config/restricted_material.json |
| Backend service | release-import worker; admin module |
| Storage / index model | register loaded at start; config sha recorded per generation |
| Frontend workspace | Admin workspace: rejection notice (id only) |
| Security | Admin only, enforced at endpoint and service layer; audited (metadata only); fail closed when register missing |
| Performance | None recorded |
| Evidence / approval gates | Owner decision RM-001 pending; exclusion applies regardless |
| Acceptance tests | test_restricted_material.py; T-RM-01..03 |
| Phase | B1 |
| Gated off | no |
| Dependencies / limitations | Register owned by governance workstream |

#### CAP-KA-04: Accounts: local users, optional AD

*Knowledge administration (18.8)* · PR-19; ADR-0002; D-05

| Aspect | Detail |
| --- | --- |
| User workflow | Admin creates/disables accounts, assigns Admin or User; optional AD group mapping |
| Required data | Accounts (no passwords in logs) |
| Backend service | identity module |
| Storage / index model | accounts, sessions tables |
| Frontend workspace | Admin workspace: accounts |
| Security | Admin only, enforced at endpoint and service layer; audited (metadata only); strong hashing; lockout; CSRF; Tests: T-PRIV-01, T-AUTH-02..07 |
| Performance | None recorded |
| Evidence / approval gates | Exactly two roles |
| Acceptance tests | T-AUTH-01..07 |
| Phase | B1 (local); B3 (AD) |
| Gated off | no |
| Dependencies / limitations | None recorded |

#### CAP-KA-05: Audit log review (metadata only)

*Knowledge administration (18.8)* · PR-14; Architecture §11

| Aspect | Detail |
| --- | --- |
| User workflow | Admin filters audit events by actor, action, object, time |
| Required data | Audit events |
| Backend service | audit module |
| Storage / index model | append-only audit table; Event Log copy |
| Frontend workspace | Admin workspace: audit |
| Security | Admin only, enforced at endpoint and service layer; audited (metadata only); web role cannot update/delete audit rows; Tests: T-LOG-01 |
| Performance | None recorded |
| Evidence / approval gates | None recorded |
| Acceptance tests | T-LOG-01; audit rows immutable via app |
| Phase | B3 |
| Gated off | no |
| Dependencies / limitations | None recorded |

#### CAP-KA-06: Legal Reviewer designation registry (inert)

*Knowledge administration (18.8)* · PR-19; Document Studio 3.3; ADR-0003

| Aspect | Detail |
| --- | --- |
| User workflow | Data model records designation and appointment; no action is enabled |
| Required data | Appointment (none exist) |
| Backend service | identity module |
| Storage / index model | designation, appointment tables (empty) |
| Frontend workspace | Admin workspace: designations (read-only notice) |
| Security | Admin only, enforced at endpoint and service layer; audited (metadata only); approval endpoints return GATE_CLOSED; Tests: T-AUTH-04 |
| Performance | Not applicable: gated, architected only |
| Evidence / approval gates | Activation needs owner confirmation and a recorded appointment |
| Acceptance tests | T-AUTH-04 |
| Phase | B3 (model); activation later |
| Gated off | yes |
| Dependencies / limitations | Not applicable: gated, architected only |

#### CAP-KA-07: Review queues (non-cites edges, impact triggers, OCR low confidence)

*Knowledge administration (18.8)* · PR-28; Document Studio 3.3; plan B2

| Aspect | Detail |
| --- | --- |
| User workflow | Admin views queues; OCR low-confidence pages listed; legal decisions cannot be recorded |
| Required data | Candidate edges; derived_text low_confidence pages; CHANGES.json triggers |
| Backend service | admin module |
| Storage / index model | queue views |
| Frontend workspace | Admin workspace: queues |
| Security | Admin only, enforced at endpoint and service layer; audited (metadata only) |
| Performance | None recorded |
| Evidence / approval gates | Decisions on legal-effect edges require Legal Reviewer (inactive) |
| Acceptance tests | OCR pages below threshold listed, not silently trusted |
| Phase | B2 (OCR list); B3 (edge/impact queues, view only) |
| Gated off | no |
| Dependencies / limitations | None recorded |

#### CAP-KA-08: Candidate-data banner driven by release metadata

*Knowledge administration (18.8)* · PR-18; plan B11

| Aspect | Detail |
| --- | --- |
| User workflow | Every page shows non-dismissable banner text from the release manifest |
| Required data | candidate_banner in RELEASE.json; auth_ledger_version |
| Backend service | web shell |
| Storage / index model | release_generation |
| Frontend workspace | Global shell |
| Security | Authenticated User or Admin; published items only; server-side visibility filter; Tests: T-LEDGER-01, T-GATE-01 |
| Performance | None recorded |
| Evidence / approval gates | Cannot be disabled while AUTH-LEDGER v0 |
| Acceptance tests | Route test: banner on every route; contract rule BANNER_REQUIRED |
| Phase | B1 |
| Gated off | no |
| Dependencies / limitations | None recorded |

#### CAP-KA-09: Backup and restore

*Knowledge administration (18.8)* · PR-14; T-08; PR-20

| Aspect | Detail |
| --- | --- |
| User workflow | Scheduled backups; restore drill |
| Required data | DB, vault, configuration |
| Backend service | backup task |
| Storage / index model | pg_dump/basebackup; robocopy/restic to offline media |
| Frontend workspace | Admin workspace: backup status |
| Security | Admin only, enforced at endpoint and service layer; audited (metadata only); working sessions excluded by default; Tests: T-BKP-01, T-VIS-03 |
| Performance | Nightly backup within maintenance window |
| Evidence / approval gates | None recorded |
| Acceptance tests | T-BKP-01 restore drill |
| Phase | B1 (backup); B2 (full restore drill) |
| Gated off | no |
| Dependencies / limitations | None recorded |

## 4. Cross-cutting rules applied to every row

1. **No legal reasoning or compliance logic in Cycle 13.** Rows with legal effect are `later` and gated off.
2. **Every derived item is a candidate** (`AUTOMATED_CANDIDATE_NOT_VERIFIED` or `DOCUMENTARY_CHECKED` with a review reference), shown with its capability restriction from `C12-CONSOLIDATION/CAPABILITY_RESTRICTIONS.csv` and its measured quality or "not evaluated".
3. **Two roles only**; Legal Reviewer is an inert designation; all authorisation and ownership checks are server-side.
4. **Restricted material** (register `config/restricted_material.json`) never reaches any index, embedding, bundle, graph view or export.
5. **The 5 deferred P2s** (C11 F05–F08, WSG-R04) keep their capabilities non-operational: CAP-JI-03 (F05, F08), CAP-JI-05 (F06, F07), CAP-DS-02 (WSG-R04).

