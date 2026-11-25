# Agent tool contracts and application integration

**Status:** proposed logical service API; not a release-schema change or executable implementation. [Precedence](README.md).

## 1. Contract rules

The existing app contract v1 R1 is the canonical interchange layer. Future agents receive typed projections via a server-owned broker. No direct database connection, shell, arbitrary file path, external URL, arbitrary SQL, raw filesystem or generic network tool. No model-generated tool name is executed unless registered and authorised. Validate input, output, scope, size and limits at the broker. Use strict JSON Schemas and reject unknown fields. The logical names below are proposals; reconcile with actual service names before freezing version 1.

### Envelope (illustrative JSON, not canonical wire schema)

```json
{
  "tool": "search_evidence",
  "contract_version": "1.0.0",
  "request_id": "synthetic-request-001",
  "arguments": {
    "query": "synthetic legal research query",
    "limit": 10,
    "mode": "HYBRID"
  }
}
```

Server-owned execution context (not model arguments): authenticated actor and effective capability set; operation class; session owner and session ID; release generation; local publication/exclusion revision; allowed scopes; budget/deadline; cancellation signal; policy version. The broker derives context from a verified session and checks all referenced objects at execution and response time. Requests cannot select another user's session, bypass a restriction, or select an unsafe old generation.

Response envelope: request/tool/contract version, execution status, generation and exclusion revision, result items, warnings, truncation/coverage flags, typed error and retryability, elapsed time, evidence dependencies. No sensitive payload in shared logs. Use opaque IDs only with server-side ownership and eligibility checks. Workflow status and legal status are separate.

## 2. Tool catalogue

| Logical tool | Input | Result | Access and safety |
|---|---|---|---|
| resolve_identifier | typed text, optional entity kind | candidate IDs, match type, ambiguity | published only |
| search_evidence | query, approved filters, mode, limit | ranked passage refs, match reasons, source status | published only; capability restrictions |
| get_document | canonical document/copy ID | metadata, provenance, version, permitted viewer ref | eligible published copy |
| get_source_passage | copy ID, page/span anchor ID | authorised text/quote, extraction quality, source ref | current eligibility, bounded excerpt |
| get_provision_versions | instrument/provision ID, event-date context | versions, evidence chain, unresolved gaps | research only until legal gate |
| get_judicial_treatment | judgment/proceeding ID, direction, type filters | supported edges, contrary leads, coverage | no unapproved legal inference |
| explore_relationships | seed IDs, relation allow-list, bounded depth | anchored paths, truncation/gaps | eligibility on every node/edge |
| get_evidence_state | canonical record ID | record-kind-specific status fields, restrictions, applicable review refs | never changes state |
| verify_anchor | anchor ID and expected copy/span | resolved/mismatch/unavailable/fidelity limit | no assertion of entailment or authority |
| get_form_versions | form family, relevant context | published specimens and version evidence | no fill-ready representation without approval |
| evaluate_validated_rule | approved pack/rule ID, explicit fact IDs and event dates | typed checks, blockers, source refs | future; gate before execute; disabled in C13 |
| read_working_fields | own session/document/field IDs | extracted fields, origin, confidence, unknowns | session owner only |
| propose_working_draft | own session, eligible template ID, explicit fields | editable draft preview and dependency manifest | future; no issuance; gated template |
| get_working_readiness | own session, eligible rule pack | report with distinct check states | future; no compliance execution until approved |

No tool for legal approval, BIND, publication, withdrawal, deletion, punitive execution or arbitrary source acquisition is available to the research/document model. Admin ingestion agents have a distinct operation class and scoped candidate-writing tools only within staged jobs. Human Admin publication and formal legal approval remain explicit separately authenticated workflows.

## 3. Evidence reference contract

Use canonical IDs and record-kind-specific statuses from data contract v1 R1. Seven axes are a document-level object, not a guarantee for derivatives or candidates; missing fields remain unestablished. See [field-level crosswalk](DATA_CONTRACT_CROSSWALK.md). Do not duplicate or flatten into a single verified flag. A logical evidence projection includes:
- document, source-copy SHA-256, logical judgment/proceeding/provision/version identity where relevant;
- page index and optional printed page label, anchor ID, span/coordinate/text hash, derivative version and extraction quality;
- source provenance and publication generation; eligibility/exclusion checks;
- candidate/review record references, graph-edge IDs and supporting anchor IDs where relevant;
- relevant event dates, uncertainty, applicability and freshness status;
- capability restriction/evaluation references.

References must be resolvable and current. If an exact span is not supported, return page-level evidence with explicit fidelity limits; never fabricate paragraph numbering. An exact source anchor can support research without having an approved interpretation.

## 4. Claim and result contract

The following are proposed response concepts; map them to existing Scenario Advisory Engine §7 and Document Studio §§9–11 rather than creating a second canonical report:
- user intent and material facts (known, alleged, unknown, disputed; source/user attribution);
- evidence references, contrary evidence and retrieval gaps;
- claim ID, text, scope, supporting and opposing refs;
- claim type (source quotation, research summary, candidate interpretation, approved conditional guidance, non-legal practical consideration);
- verification result (anchor resolved, support established/not established, conflict, stale, denied);
- required and actual approval tier and gate outcome when applicable;
- explicit limitations, missing facts, escalation, trace ID;
- model, tool, rule and evidence generation identifiers.

No unsupported legal claim is rendered as authoritative. Render research-only results under existing display policy. A denied legal result may return permitted evidence and a reason, not an actionable forbidden conclusion hidden in another field. All claims, typed values, headings, notes, labels and export content are bound by the [final claim verification contract](FINAL_CLAIM_VERIFICATION_CONTRACT.md); no raw model token stream is a user response.

## 5. Error handling and persistence

Typed failures: INVALID_INPUT, ACCESS_DENIED, GATE_CLOSED, NOT_FOUND, AMBIGUOUS, RESTRICTED, WITHDRAWN, GENERATION_CHANGED, STALE_DEPENDENCY, INSUFFICIENT_EVIDENCE, BUDGET_EXHAUSTED, CANCELLED, TOOL_UNAVAILABLE, INTERNAL_FAILURE. Avoid distinguishing hidden-object existence to unauthorised callers. Retries only for documented transient, idempotent read operations, never to circumvent a gate. Re-check after retry. Cache keys include scope/owner where applicable, generation, policy, exclusions and tool version; private content never enters a global cache. Revocation/withdrawal invalidates caches, running tasks and exports-in-preparation. The [serving and revocation contract](SERVING_AND_REVOCATION_CONTRACT.md) governs the final handoff for each chunk, range, event, cache hit and export, not merely the tool invocation.

Persist minimal audit metadata separately from session content. Session deletion removes model context, traces containing content, derivatives, private embeddings, exports and job results under the same retention policy. Do not save hidden model reasoning. Retain only permitted reproducibility artefacts.

## 6. Integration mapping and tests

B1 search/catalogue/viewer and B3 graph services should remain callable without an LLM. Use generated or hand-reviewed strict schemas and adapters after the current contract is adopted. Breaking canonical release changes require its established version/validator/independent review process.

Test direct invocation with forged actor/owner, another user's session, arbitrary path/URL, unknown fields/tool names, too many graph hops, hidden candidate, restricted alias, withdrawn source, generation change during run, stale cache, missing anchor, tool timeout, duplicate retry and invalid model JSON. The expected response must be derived independently of the implementation. See [runtime/security](LOCAL_AI_SECURITY_AND_RUNTIME.md) and [evaluation](EVALUATION_AND_ROADMAP.md).

## 7. Broker, private delegation and response projection (INT-F03/F08/F09/F14)

An authenticated server-side operation policy controls both tool invocation and result projection. Distinguish PUBLISHED_RESEARCH, STAGED_ADMIN_PROCESSING and PRIVATE_WORKING_SESSION execution domains (logical names, not new roles). A private workflow may read permitted published evidence and its own session data, but every combined result is private; only a deliberate separate Admin submission may enter staged processing. No reverse transfer. A staged Admin job cannot delegate to a user research model with staged data. Actor/session, output class, restrictions, fact/plan revisions and attempt fence are server-derived; no ambient credentials or arbitrary delegation.

Apply field/row visibility before counts, snippets, facets, graph paths and model context. For unauthorised callers normalize hidden/not-found/restricted/withdrawn responses to a single non-disclosing result; internal diagnostic distinctions are allowed only within authorized logs/diagnostics without private content. Avoid revealing hidden counts, timing or identifier hints; bound response size and test observable differences. Typed progress events and reconnect snapshots follow Agentic §7; no unverified text. Never expose raw model output or unverified file artifacts via direct worker routes. All generated content is buffered, independently verified and delivered only as authorized immutable artifacts. A delivery lease is not a reusable authorization; each final handoff checks current state under the barrier.

Use explicit idempotency for private draft writes; bind accepted results to task attempt/fact/plan revisions. Use dependency manifests for every derivative, cached result, graph path, saved comparison and export. If dependencies cannot be fully established, invalidate conservatively and deny delivery. The service projections are proposals; do not extend R1 schema or fabricate unsupported fields. Tests include reused passage IDs across derivatives, page-only and OCR-only references, upstream vs site publication, forged owner, cross-domain delegation, stale attempt completion, normalized errors and negative direct-API calls.
