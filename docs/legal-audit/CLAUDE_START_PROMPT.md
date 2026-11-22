# Paste into Claude Code in the Mimamsa repository

You are the lead orchestrator for a **DATABASE-ONLY** independent legal/data-quality audit of the Indian Military Law Knowledge Base. Your job is to prepare a legally traceable and reproducible corpus for later legal/JAG validation. **DO NOT BUILD AN APPLICATION.** No UI, frontend, backend, API, chatbot, vector database, RAG runtime, search service, offline packaging or deployment work.

REPOSITORY: hariomahlawat/mimamsa-corpus.
Read first: root CLAUDE.md, README.md, PROGRESS.md, legal_knowledge/README.md, docs/legal-audit/README.md, EVIDENCE_STANDARD.md, ORCHESTRATION.md and PILOT_AND_ACCEPTANCE.md. Inspect the six .claude/agents/*.md agent definitions and existing repository schemas/tests before acting. Existing legal-data staging branch and PR must be respected.

CANONICAL DATA: private HF dataset hariomahlawat/mimamsa-corpus. The 658 original v0.9 KB research records and 53 original v0.9 curated-case rows are immutable. Preserve the crawler corpus and existing intern's judgment research. Do not infer that a source is missing based only on a failed title/year crosswalk. No source or legal review claim is approved yet.

IMMEDIATE ACTION — READ-ONLY FIRST:
1. Report current repo branch/commit and relevant active review work. Identify actual canonical input paths, IDs, counts and SHA-256s. If the HF dataset is inaccessible, STOP and report the precise access blocker; don't invent missing inputs.
2. Map existing verification batches and high-risk unresolved issues, especially Army Rules Rule 23(3) S.R.O. 484 (27 Nov 1954) original Gazette conflict, disputed case source identities, and later judicial treatment.
3. Propose EXACTLY 25 actual distinct KB record IDs as a balanced pilot. Include stratification across legal risk and volumes, selection reasons and frozen input hashes. Do not make up IDs.
4. Allocate explicit bounded work packets across statutory-auditor, judgment-auditor, procedure-auditor, cross-volume-auditor, database-validator and independent-reviewer. Distinguish first-pass from blind independent review. Use 2–3 concurrent agents maximum.
5. Produce an audit inventory, evidence-access matrix, proposed pilot-selection manifest, human-review queue and deterministic test plan. DO NOT modify any source or curated original files. STOP for my approval of the proposed 25-record pilot.

AFTER I APPROVE PILOT: agents may prepare additive review artefacts only under legal_knowledge/audit_work/<batch_id>/. Every allegation needs exact primary-source passage, locator, date/version, source identity/hash when available, contrary authority, impact and unresolved questions. No fabricated citations, no automatic formal sign-off. Run tools/legal_audit/validate.py on the pilot folder, independent challenge, and legal advisor decisions. Do not upload to HF, change canonical data, merge PR, initiate broad recrawl or proceed to all 658 until GO is expressly approved.

RETURN: (a) read-only inventory and source blockers, (b) 25-ID sample, (c) work packet allocations, (d) risks and legal advisor queue, (e) explicit STOP/GO recommendation. State "DATABASE ONLY, NO APPLICATION WORK" in final status.
