# Final claim verification and output authorization contract

**R2 — INT-F02 (P1). Proposed normative design, not implemented.** Applies before any generated research output and later every operational output class. Cycle 13 has no live generation or legal-rule execution. Existing Scenario Advisory Engine, Document Studio and evidence policies control legal meaning and approval.

## 1. Why input verification is insufficient

A genuine citation and accurate retrieved text do not entail an arbitrary conclusion assembled from them. A model may join correct fragments into a false rule, omit a limiting exception, infer an unapproved deadline, or turn research into operative advice in a label, heading, draft, note or export. Verification must occur **after the final proposed synthesis**, with no subsequent unconstrained rewrite. Independent verification does not mean that a second model's agreement proves law.

## 2. Output authorization before context

Application policy derives allowed output class from actor, operation, user intent, deployment capabilities, release and existing competent-authority tier requirements. Illustrative classes: ORIGINAL_SOURCE_RESEARCH, GENERATED_RESEARCH_EXPLANATION (future), RESEARCH_SPECIMEN, CONDITIONAL_GUIDANCE, OPERATIVE_CHECK, FILL_READY_TEMPLATE. These are proposed service projections, not new legal tiers. Map to controlling domain output classes before implementation. The model cannot select a more permissive class or use a research label to disguise operative directions.

At ledger v0 permit eligible ordinary research only under the existing plan; C13 does not activate generated synthesis. Later research generation, if separately accepted, is non-operative and bounded by research policy. Rule evaluation and fill-ready generation require pre-authorized typed grant and required tier, exact pack/template and dependency revision, established legal applicability, no material conflicts and all existing gates. A trusted ledger state alone grants nothing. Unknown class or scope fails closed. Direct API and workers share the same server-owned gate.

Assemble only evidence allowed for the requested class, including required contrary passages and coverage gaps. Hidden candidate fields do not become visible via AI. Scope, fact revision and evidence generation are server-derived, not model assertions.

## 3. Claim inventory and verification

Generator produces a structured **proposal**, never a directly streamed response. Material claims include legal rules, scope, dates, legal effect, case treatment/outcome, obligations, rights, authority, procedural sequence, suggested actions, exceptions, conclusions, comparisons, factual assertions and implications. Titles, captions, notes, checklist labels, table cells, field values, template prose and export footnotes are within scope. Separate user-alleged facts, source quotations, supported research explanations and authorized typed operative results.

Each proposed atomic claim includes ID, exact canonical text or typed value, output class, subject/issue, service/jurisdiction/person/procedure scope, controlling date basis and version where material, factual assumptions, modalities (must/may/unknown), exceptions and limiting qualifiers, supporting and contrary anchor references, dependency IDs and known coverage gaps. Multi-claim sentences must be decomposed without losing qualifiers; linking two claims creates a new claim when the relation adds meaning. Non-substantive headings use controlled rendering vocabulary. If a substantive unit cannot be accounted for, reject it rather than mark it decorative.

Verify final proposed units using independently evaluated procedures and independent reference oracles:
- Resolve copy/page/derivative identity and source eligibility; verify quoted text fidelity where asserted, including OCR limitations.
- Check actual entailment of the *entire* claim, including direction, temporal scope, proceeding, proposition, conditional language, exceptions and modality. No unsupported conclusion from conjunction of true fragments.
- Compare contrary authority and missing-evidence coverage for the claim; flag disagreement or truncation. Absence of a graph edge is not absence of adverse authority.
- Distinguish factual attribution from established fact. Preserve disputed/unknown facts.
- Check allowed output class and legal gate independently of model confidence. Operative findings are generated only by the authorized deterministic evaluator's typed result, with exact rule/approval/dependency binding; models may not alter a mandatory step, outcome or legal qualification.
- If support, scope or class is not established, reject or narrow the unit and reverify the entire revised content. No numeric confidence alone substitutes for proof or competent approval.

Verification record includes claim ID, canonical text/typed-value digest, scope and qualifiers digest, dependency manifest, evidence refs, coverage record, supported/unsupported/uncertain/conflict reason, output class, verifier identity and version, policy/serving epoch, actual approval reference where required. The verifier must be independent of generator self-assessment; deterministic checks plus independently benchmarked entailment/qualified review as appropriate. Legal approval remains a distinct human-controlled decision.

## 4. Bind verification to delivery

Canonical immutable AuthorizedOutput (future service artifact):
- owner/session, response ID/revision, permitted output class, fact/plan revision, canonical content tree and hash;
- ordered block/claim IDs, each exact text/value and required qualifiers; every substantive block resolves to an accepted verification record;
- exact evidence and approval/dependency manifest digest, policy/serving epoch, renderer/template version, verifier and authorization record;
- expiry/invalidation conditions.

Server authorization validates completeness of the content inventory and every accepted claim against permitted class, binds digest to the full canonical content tree, and freezes it. The renderer may apply formatting, accessibility labels from approved vocabulary and layout only, never summarize, paraphrase, join claims, infer headings, remove qualifiers or change typed results. Display compact and detailed views from the same authorized units; material limitations travel with the claim even in compact view. A new translation, summary, edited draft, changed label or generated export text is a new proposal requiring verification. A user edit to an editable draft is explicitly unverified working content, not an authorized fit-for-issue result.

Exports are deterministic rendering of the same authorized content/approved template version; verify content mapping and generated artifact hash, including tables, footnotes, metadata and field values. Do not hand raw model files directly to user. Re-check current output grant, dependencies and artifact hash at the [serving barrier](SERVING_AND_REVOCATION_CONTRACT.md) for preview, stream chunks, reconnect, printing and download. Expired or invalidated artifact cannot be delivered via stale URL. Model output is buffered until final claim authorization; progress streams contain only bounded typed status or independently authorized immutable partial artifacts (with explicit incomplete coverage). Never stream raw substantive tokens.

If verification fails, bounded revise-and-reverify or source-only fallback: permitted original source references/quotes already authorized for research, transparent gaps and material questions, no rejected conclusions or operative equivalents in any field. If source eligibility or final authorization is uncertain, deny affected content; no failure explanation containing protected details. Preserve useful unaffected verified research.

## 5. Worked synthetic examples (no real legal rule)

- Source A supports a requirement for service X under version V; source B supports an unrelated date. Model writes "all services must act by date D." Both citations resolve but scope and relation/deadline entailment fail. Reject final claim; show permitted source material and unknown applicability, not a fabricated deadline.
- Synthetic approved rule produces typed UNKNOWN due to unestablished exception. Model says "check passed" in a heading. Reject because output digest/value and qualifiers differ; renderer must preserve UNKNOWN.
- At v0 a research note says "you must follow these three steps" based on candidate graph paths. Gate rejects disguised operative class, even when valid citations exist. No evaluator runs.
- A claim is supported at epoch 20, then its source is withdrawn at 21 before a DOCX download. The artifact remains in private staging but delivery barrier denies it; verification at 20 is not a reusable grant.

## 6. Acceptance (before feature activation)

Independent oracle labels each final claim, scope, qualification, contrary evidence and allowed output class; separately check rendered text/typed content and exported artifact mapping. Pin evidence, output proposal, verifier, rules, renderer and policy revisions. Include blind source-backed tests and synthetic negative controls. No actual legal approvals or rules in synthetic fixtures.

| ID | Test | Required result |
|---|---|---|
| CLAIM-01 | Valid quote, wrong service/date/proceeding scope | Reject unsupported conclusion; research source fallback |
| CLAIM-02 | Two individually true fragments combined into false relation/deadline | Reject new claim; no unverified prose emitted |
| CLAIM-03 | Omitted exception/adverse qualification, incomplete contrary search | Reject/narrow and reverify; preserve coverage/uncertainty |
| CLAIM-04 | Operative advice in label, note, table, template, export at v0 | Deny all equivalent representations, no evaluator execution |
| CLAIM-05 | Renderer or later model rewrites approved content / drops qualifier | Digest or mapping mismatch; no delivery; new verification needed |
| CLAIM-06 | Edit fact, revoke approval or withdraw evidence between verification and handoff | Invalidate affected artifact, no stale delivery |
| CLAIM-07 | Raw token stream, worker URL, cached preview or forged verifier record | No bypass; authorized immutable artifact only |
| CLAIM-08 | Supported permitted claim and useful source-only fallback | Positive controls succeed without excessive denial; record actual usefulness |

Targets: zero observed fabricated anchors, unsafe definitive outputs, unbound substantive blocks or gate bypass in negative tests; independently measured support/qualification and abstention targets in evaluation plan. No aggregate metric overrides the per-output policy gate. Architecture correction proposed; implementation, qualified legal review and independent confirmation remain outstanding.