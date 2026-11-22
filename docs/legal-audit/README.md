# Indian Military Law database: independent audit agents

**Phase: DATABASE ONLY. NOT an application build.**

The seven Claude Code agents under `.claude/agents/` audit legal **research records**, source documents, case-law relationships and metadata. They must not design or implement a UI, chat assistant, RAG retrieval service, API, vector index, search frontend, offline app or deployment.

## Existing architecture to preserve

- GitHub `main`: crawler code, source processors, `schema/`, validation and tests. Keep the existing top-level `CLAUDE.md` unchanged.
- GitHub `legal-knowledge/v2.5-staging`: active draft curated legal-data work and research artifacts. This audit layer is developed on its own branch and reviewed separately.
- Private HF dataset `hariomahlawat/mimamsa-corpus`: canonical corpus, including immutable originals at `legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl` (658 notes) and `legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl` (53 curated cases).
- GitHub `raw-data`: secondary copy, not a destination for audit-agent writes.
- Existing `legal_knowledge/verification_batches/`, `crosswalk/`, `judicial_treatment/` and `quality_audit/`: provenance-bearing research, not legal approvals.

The existing judgment collection is active and substantial; check the current manifests and review status before proposing any fresh collection.

## Files and process

1. `docs/legal-audit/MML_SOURCE_PRIORITY.md`: required first-pass inventory of all eight Manual of Military Law originals and provenance crosswalk.
2. `docs/legal-audit/CLAUDE_START_PROMPT.md`: prompt to paste into Claude Code.
3. `docs/legal-audit/ORCHESTRATION.md`: orchestration/delegation with independent checks.
4. `docs/legal-audit/EVIDENCE_STANDARD.md`: source hierarchy, claims and risk controls.
5. `docs/legal-audit/PILOT_AND_ACCEPTANCE.md`: bounded 25-record pilot; go/no-go.
6. `docs/legal-audit/schemas/`: schema of proposed source, finding and review records.
7. `tools/legal_audit/validate.py`: structural validator only, not legal truth certification.

## Required workflow

**First inventory all eight MML DOC/PDF sources, their editions, page maps and source hashes.** Then: read-only baseline -> immutable source hash manifest -> deterministic 25-ID pilot selection -> first-pass source audit -> blind reviewer -> advisor disposition -> technical validation -> owner GO/NO-GO. No full 658-record rollout until pilot sign-off.

Store draft batch artifacts in `legal_knowledge/audit_work/<batch_id>/`; never rewrite original corpus. Do not upload to HF, publish, merge, or change legal review statuses without explicit owner directions. Treat unverified sources and unresolved legal propositions as BLOCKED.

## Approval hierarchy

Agent output = research proposal. Independent agent result = challenge/evidence, not independent legal sign-off. Legal advisor review = documented professional validation, not a substitute for formal JAG validation. Technical validation = structure and traceability, not substantive law correctness. Final application guidance is out of scope.
