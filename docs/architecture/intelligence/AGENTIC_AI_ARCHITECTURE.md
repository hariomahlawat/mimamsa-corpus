# Agentic AI architecture and workflows

**Status:** proposed future design; see [extension status and precedence](README.md). This is neither an implemented service nor an operational legal SOP.

## 1. Architecture

Use a modular application and isolated local workers, rather than one network service per agent. A specialist is a logical role with a typed input, output and bounded set of tools. One local model may serve several roles; deterministic components are not artificially turned into model calls. Multiple model calls do not confer independent legal authority.

```mermaid
flowchart TD
  U[Research workspace / Document Studio] --> O[Bounded orchestrator]
  O --> H[Hybrid search and rerank]
  O --> G[Legal graph traversal]
  O --> F[Material facts and rule evaluation]
  O --> D[Private document tools]
  H --> S[Published eligible evidence services]
  G --> S
  F --> V[Operational policy gate]
  D --> V
  S --> E[Claim and source verification]
  V --> E
  E --> R[Conditional response / research-only / abstention]
  R --> U
```

The orchestrator is not a source of truth. Evidence services resolve identities, anchors and access at the actual serving generation. The policy gate is outside the model and is applied before operative rule evaluation and before output/export. The model cannot make the gate pass by declaring an answer verified. See [tool contracts](AGENT_TOOL_CONTRACTS.md) and [legal engine](DETERMINISTIC_LEGAL_ENGINE.md).

## 2. Logical responsibilities

| Role | Input | Output | Boundaries |
|---|---|---|---|
| Intent and fact analysis | User question and session facts | Intent alternatives; known/alleged/unknown facts; material questions | No guilt finding or assumed facts |
| Research planner | Question, scope, known facts, budget | Bounded typed tasks, dependencies and stop conditions | Cannot request privileged tools or choose a disciplinary action |
| Statute researcher | Provision identifiers, dates, query | Candidate provision versions, amendment and saving evidence | No inferred commencement |
| Case researcher | Issues, citations, query | Cases, passages, proceedings, treatment leads and contrary sources | No inferred overruling or holding |
| Graph researcher | Eligible seeds, relation filters, dates | Anchored paths and coverage gaps | No legal conclusion from connectivity |
| Applicability evaluator | Facts and eligible rule pack | Deterministic checks, blockers and missing predicates | No active legal rule execution at ledger v0 |
| Document workflow | Own-session files, approved template identity, relevant facts | Draft proposal or checks with source/field references | No official issuance, signing, shared indexing or auto-promotion |
| Evidence verifier | Proposed claims and cited anchors | Resolved support, contradiction, missing evidence or gate denial | A valid quote alone does not prove legal applicability |
| Synthesis | Validated evidence, unknowns, permitted findings | Research report or conditional response | No unsupported mandatory steps |
| Corpus enrichment (separate Admin jobs) | Staged eligible source | Candidate OCR, entities, links, impact leads | No autonomous publication, authentication or approval |

Prefer ordinary direct search for exact lookup. Use orchestration only when query ambiguity, multiple subquestions or relational exploration warrants it. No automatic multi-agent fan-out for every search. Use parallel tasks only for independent, scoped work; merge by evidence identity, not by majority vote.

## 3. Workflow and state

Proposed research state machine:

`CREATED → FACTS_PENDING | PLANNED → RUNNING → VERIFYING → RESEARCH_RESULT | CONDITIONAL_RESULT | ABSTAINED`

Terminal alternatives: `CANCELLED`, `BUDGET_EXHAUSTED`, `FAILED`, `INVALIDATED`. Status codes here are workflow states, not legal status axes.

- At creation, bind authenticated actor, session, operation class, site release generation, active exclusions/withdrawals, tool and model versions, and relevant fact revision. Server derives these values; client/model values cannot widen scope.
- Store a durable workflow record and immutable task attempts; checkpoint completed read-only tasks. When input facts change, invalidate dependent tasks and replan. On restart, re-check scope and generation; retry only idempotent work.
- Define bounded task count, graph depth, result limit, model token budget, elapsed time, concurrency and retry limits per workflow class. Proposed numerical defaults are benchmark inputs, not release specifications (e.g. 8 tool calls, 3 graph hops, 30 seconds for an interactive research workflow, configurable by policy). Long research jobs run with progress and cancellation rather than blocking the UI.
- Ask a small number of material questions where answers affect legal scope, version, authority or route. Allow explicit UNKNOWN. Do not silently fabricate dates, rank, service status, procedural stage, or events.
- Revalidate authorization, exclusion state and evidence generation at each tool call and again before rendering or export. If a source was withdrawn during a run, discard affected material and restart or stop; a pinned historical snapshot does not override active exclusions.
- The verifier must resolve anchors against eligible originals/derivatives, check source status and identify unsupported or contrary claims. For claim entailment, use independently tested methods and qualified review where required; a second model's agreement is not sufficient.
- Record concise user-visible research actions, sources, rule checks, limitations and gaps. Do not require or persist private model chain-of-thought. Trace replay records inputs/outputs only under session privacy rules; model replay need not be byte-identical.

## 4. User workflows

**Simple lookup:** exact citation/case ID → identifier resolver → ranked source results → original PDF. No generative model needed.

**Multi-source research:** question → lexical/semantic searches → entity seeds → bounded graph traversal → original passage resolution → evidence pack → source-linked research synthesis when authorised by a later research-generation gate. Surface alternative interpretations and missing coverage. Candidate propositions are not authoritative statements and do not bypass ordinary UI visibility restrictions.

**Future Commander Assistant:** explicit facts and event dates → relevant legal versions and candidate routes → validated deterministic constraints → permitted conditional guidance, unresolved facts and competent human review. No autonomous sanction, charge selection, finding, deadline invention or execution. The existing Scenario Advisory Engine remains the controlling product workflow.

**Future Document Studio:** authenticated private session → classify/extract working documents → confirm material fields → select eligible template version → check using the same approved rule pack as generation → cite each check → editable draft or readiness report. Keep pass/fail/unknown/not applicable/not checked/missing distinct. No aggregate legal-validity score. Export is an explicit user action, never an official issuance or approval.

**Admin continuous ingestion:** staged eligible source → isolated parsing/OCR and candidate linking → impact leads and scoped dependency holds according to Document Studio §§3.3/8.1 → explicit Admin publication when eligible. An agent cannot dismiss a credible trigger, lift a hold or publish independently. No source ingestion from user research or Document Studio context.

## 5. Professional user experience

Use the existing research workspace, not a separate generic chatbot. Simple search stays fast. For complex research display progress by meaningful steps, cancellable tasks, sources examined, expandable evidence cards, conflicting authority, controlling date(s), missing facts and why an answer is restricted. Keep original PDF navigation one action away. Clearly differentiate retrieval result, candidate summary, reviewed research and permitted legal guidance. Show partial results and reasons for abstention; never disguise a blocked legal gate with a confident prose answer.

A research user may switch between commander-friendly and detailed evidence views without losing the current workspace. Personal research history follows session retention and ownership controls. No rank tiers. Functional and visual review must exercise actual research journeys, not only screenshots or unit tests.

## 6. Cycle 13 compatibility

No new live agent implementation required. Prefer reusable, typed search/catalogue/graph/evidence services, stable source and page anchors, cancellation and explicit status fields **where already compatible with current B0/B1 scope**. The later orchestrator calls application service interfaces via a controlled broker, not direct SQL, filesystem or general shell tools. See [roadmap](EVALUATION_AND_ROADMAP.md) for gated delivery.
