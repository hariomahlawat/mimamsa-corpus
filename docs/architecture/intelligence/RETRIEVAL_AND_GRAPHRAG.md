# Hybrid retrieval and legal GraphRAG

**Status:** proposed retrieval architecture extension. No assertion of legal accuracy or existing implementation. [Precedence](README.md).

## 1. Distinguish the mechanisms

Hybrid retrieval combines exact identifier matching, lexical retrieval and semantic vector retrieval; hybrid RAG uses those results as evidence for a generator. GraphRAG adds entity-seeded graph traversal and source-grounded path expansion before generation. A graph browser alone is not GraphRAG. A RAG answer is not legal validation.

For legal research, favour explicit typed, versioned, evidence-anchored relationships over opaque community summaries. Community clustering or graph summaries may be evaluated later as research aids; never use them as authority or allow them to hide restricted or withdrawn dependencies.

## 2. Corpus and search units

- Original source copy: immutable SHA-256 identity. Logical instrument, judgment, proceeding, provision version and document copy are distinct.
- Index eligible published sources only; search units are page-addressable passages respecting legal structure where possible. Retain native/OCR text, original page index, coordinate mapping, printed page label where known, language, extraction method/version and quality flags.
- Segment by headings, provision/subrule boundaries, paragraphs or opinion/proceeding when supported. Preserve surrounding context and parent-child links. Overlap may improve recall but deduplicate overlapping spans for scoring and prompt assembly.
- Keep original text and normalised search text distinct; never cite a normalised/OCR span as verbatim original without fidelity checks. Poor or missing text remains catalogued with extraction status.
- Record index generation, document/derivative hash, embedding model/tokenizer/normalisation/dimension and retrieval configuration. Rebuild or segregate incompatible vector spaces. No mixing models by similarity alone.
- Candidate holdings and outcome fields respect the active capability restrictions and ordinary-user display policy. Indexing for restricted diagnostics is not permission to expose those fields to all users or agents.

## 3. Retrieval and query routing

| Query type | Primary path | Fallback |
|---|---|---|
| Exact case number, citation or Rule | Identifier resolver with exact pins and aliases | Lexical search; show ambiguity |
| Legal phrase or known document | Phrase/lexical ranking with provision-aware filters | Semantic retrieval |
| Plain-English issue | Lexical + semantic candidates | Query decomposition and graph expansion |
| Amendment/history | Entity resolve + dated graph paths | Original sources; report missing chain |
| Subsequent treatment | Directed graph traversal, then passage retrieval | Search citing cases and explicitly flag coverage gaps |
| Working-document review | Session-local extraction and eligible published evidence | Ask user for missing facts/documents |

Normalise military abbreviations using versioned alias records; preserve exact query and offer alternate interpretations rather than overwriting ambiguous terms. Distinguish historical abbreviations and current usage where context is known. Never infer exact legal identifiers from embedding distance alone.

Suggested pipeline:

1. Authenticate, establish active publication/exclusion generation and allowed scope.
2. Parse identifiers, phrases, dates and facets; resolve candidate entities with ambiguity indicators.
3. Retrieve top-k lexical and top-k semantic passages with the same eligibility constraints. Exact verified identifier matches are protected from displacement by reranking.
4. Fuse using a tested method, e.g. reciprocal rank fusion (rank-based, not uncalibrated score addition); deduplicate by document/copy/passage and balance relevant sources. Candidate parameters: k and fusion constant selected on development queries only.
5. Optional local cross-encoder reranker, measured for incremental recall/ranking quality and latency; do not interpret a relevance score as authority or probability of legal correctness.
6. Expand selected graph seeds only when the intent benefits; reretrieve original evidence for each material edge and adjacent legal context.
7. Build evidence pack under a context budget; retain exact matches, contrary authorities, source status and evidence gaps. If required evidence cannot fit, retrieve narrower passages or abstain instead of truncating critical qualifications silently.
8. Recheck eligibility before passing evidence to a model or displaying results.

Retrieve first, generate later. Search service remains usable without any generative runtime.

## 4. Graph model and retrieval

Reuse relation types and canonical identities from Legal Knowledge Architecture §5 and the actual interchange schema. Do not create an alternative graph schema. Example conceptual paths:

```
ProvisionVersion <- AMENDS_PROVISION_VERSION - InstrumentVersion
Judgment -> CITES_PROVISION -> ProvisionVersion (version may be unresolved)
Judgment -> DISTINGUISHES/FOLLOWS -> Judgment
FormTemplateVersion -> source-backed requirement -> EvidenceAnchor
ApprovedRuleRevision -> dependency -> ProvisionVersion / LegalProposition
```

These are illustrative conceptual relationships; map directions and names to canonical schema before implementation. Never silently conflate citation to a provision with verified applicability to its version.

Future enriched edges need stable assertion identity, typed endpoints, direction, source copy/page, optional derivative span, extraction/review provenance, applicable interval/date basis where established and restrictions. R1 does not guarantee independent seven axes on an edge; see the [record-kind mapping and relation matrix](DATA_CONTRACT_CROSSWALK.md). An inferred path is a research lead, not a new legally approved edge.

Traversal policy:
- Select explicit seed entities from identifier resolution or high-ranked eligible passages. Record why each seed was selected.
- Bound depth, fan-out, visited nodes, total edges, time and evidence budget. Use cycle detection and deterministic ordering for reproducibility. Initial 1–3 hops are a proposed benchmark setting.
- Filter edges by publication/eligibility, capability restrictions and relationship type at every hop, not merely at endpoint rendering. Respect direction; display inverse navigation without inventing inverse legal meanings.
- Keep effective intervals and uncertain date bases distinct. Unknown intervals are not treated as valid at every date. For a historical question, carry conduct/proceeding/procedural-action/preparation dates separately and preserve savings/transition uncertainty.
- Traverse adverse treatment and conflicting authority explicitly; do not discard contrary evidence because it reduces semantic similarity. Graph incompleteness is reported, not interpreted as no contrary case exists.
- Return paths with each edge's evidence and status, endpoint labels, cutoffs and reasons for omission. Validate path support before model context assembly.
- Candidate edges may aid eligible research discovery only; they cannot establish a mandatory rule or authoritative legal inference. Hidden, withdrawn, staged, restricted or stale operational dependencies must not be resurrected by graph expansion or cached paths.

## 5. Generation and evidence use

A model receives only an authorised evidence pack after output-class authorization. Proposed synthesis is buffered and checked at the final substantive-claim level, including all material qualifiers, against independent evidence and permitted output class. The [final claim verification contract](FINAL_CLAIM_VERIFICATION_CONTRACT.md) binds the authorized artifact to the actual displayed/exported content. A citation that exists but does not support the claim is a failure.

No invented citations, exact legal text, case outcomes, or completeness claims. When no sufficient authority is established, report that fact. A relevant older version is not automatically the governing version.

## 6. Benchmark and implementation

Start with existing PostgreSQL-centred PoCs; graph storage may be relational and traversal may use bounded recursive queries. Consider specialised indexes or graph stores only on measured capability/latency need and with exclusion consistency. Compare exact/lexical, vector, hybrid, graph-augmented and reranked variants on the same frozen query set. Report incremental gain by query family, multi-hop evidence recall, contrary-authority retrieval, eligibility leakage, latency and memory. See [evaluation](EVALUATION_AND_ROADMAP.md).

## 7. Claim-specific coverage and contrary-authority search (INT-F04/F05/F13)

Before synthesis, build a coverage record per material question and later per proposed claim: required issue, relevant service/jurisdiction, controlling date basis, query variants, court/period/language/corpus partition and relation classes searched, known source/index coverage and OCR gaps, unresolved IDs, competing paths, cutoff and budget exhaustion. Unknown corpus coverage remains UNKNOWN, not 100%. Dedicate an independent contrary-authority query budget that cannot be consumed by the supporting search: search citing text and relevant passages, alternate citations/names, negation/limitation terms and relevant versions, even if the graph is empty. Preserve both adverse and qualifying passages in the evidence pack; if insufficient context remains, narrow scope, ask or abstain. Candidate or unresolved path segments are discovery-only; no downstream assertion can inherit stronger status from a valid later edge. Never infer that no contrary authority exists.

Treat valid time (legal effect, with evidenced date basis), transaction/review time (when recorded) and incident/procedural dates independently. Resolve each path edge's scoped proposition/proceeding and applicable version; an interval intersection alone cannot establish a saving or legal interpretation. Keep conflicting resolutions as separate versioned assertions rather than choosing highest confidence. Generic citation may have unresolved target/version; expose lead only. Typed relation and inverse navigation policy is in the crosswalk. Example: synthetic case B follows proposition A1 but distinguishes A2; the graph must not summarize B as following all of case A. A linked wrong-version path is excluded from a definitive claim even if eligible; an adverse text-only case is retrieved independently and shown with unknown treatment until resolved.

Index structured exact identifier fields (forum, case number/year, neutral citation, instrument/section/subsection); preserve punctuation and original script, separate normalized variants, ordered phrases and versioned time-scoped aliases. Evaluate English and relevant Indian scripts, transliteration and character/trigram recovery for OCR errors, ambiguous abbreviations and historic terminology. Use subissue coverage quotas and parent-context expansion to avoid duplicate top hits starving rare legal issues. Never silently disambiguate. For selectively filtered vector search, measure exact eligible subset search vs ANN with iterative scans/partitions; final eligibility remains mandatory. Evaluate lexical, semantic, fused, reranked and graph-enhanced variants against the same frozen families and report adverse recall, exact resolution, source/qualifier recall and tail latency. Use PostgreSQL first, alternatives only after measured gain and consistency/restore tests.
