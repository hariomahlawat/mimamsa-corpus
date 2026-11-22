# Execution contract for Claude Code orchestrator

## Priority and scope
Do **database integrity/legal provenance work only**. The top-level crawler brief `CLAUDE.md` remains intact; this audit contract supplements it. Do not touch any application layer.

## First session: read-only inventory
0. **MANDATORY MML FIRST PASS**: read `docs/legal-audit/MML_SOURCE_PRIORITY.md`. Independently enumerate all eight originals from the canonical private HF dataset; inspect hashes, actual formats, edition/printing/access markings and page/paragraph layouts. Keep user-supplied MML DOC/PDF versions separate until equivalence is demonstrated. Build a candidate crosswalk to KB records and statutes without calling manual commentary current law. If inaccessible or restricted, report access blocker and do not claim examination.
1. Inspect Git branch, `PROGRESS.md`, active legal-data PR, source schemas and the private HF canonical dataset only if credentials and access are already authorised. Do not assume HF is mounted.
2. Inventory unique IDs, counts, SHA-256 of the 658 v0.9 KB records and 53 v0.9 case records. List latest derivative legal verification versions without mistaking research work for approved records. Inspect current corpus manifest, not progress-log numbers alone.
3. Identify existing evidence, source-index coverage, alleged duplicate documents, court case identity gaps and outstanding Gazette/authenticity blockers. Preserve existing intern judgment intake.
4. Report actual access gaps. Propose a stratified sample of 25 real IDs and a first-pass task partition. STOP for owner approval before any full-scale audit or bulk rewrite.

## After owner authorises pilot
- MML manual agent: anchored DOC/PDF source extraction, edition concordance and manual-to-claim crosswalk, priority for commander-referenced procedures. The eight originals are included in the baseline inventory even if some duplicate by content.
- Statutory agent: claims/rules and legal-date verification.
- Judgment agent: identity, exact holdings, later case treatment, relevant links.
- Procedure agent: disciplinary and administrative procedural chain.
- Cross-volume agent: duplicate/conflict/linkage checks using real record IDs.
- Database validator: schemas, references, hashes, counts, CI tests.
- Independent reviewer: blind challenge of critical findings and a stratified control sample BEFORE seeing first-pass answers when feasible.

Have the MML auditor perform read-only baseline BEFORE substantive work packets, then operate at most 2-3 research agents simultaneously. Assign disjoint primary task IDs with deliberate cross-check overlap; keep one canonical coordinator. Avoid unbounded recursive subagent spawning or a single oversized context. For each packet specify input snapshot/IDs, permitted source domains, maximum scope, output location, stop conditions and expected artifact schema.

## Change policy
Write only additive drafts under `legal_knowledge/audit_work/<batch_id>/`. No writes to `legal_knowledge/curated_originals/`, `data/`, `schema/`, raw source PDFs, manual originals, existing case collection, `raw-data` or HF. Never make a model-agreed source correction silently. Do not run `scripts/push_hf.py` or GitHub Actions sync workflows.
A patch to metadata or a derivative KB candidate is a separate reviewed step and separate PR.

## Independent verification
Evidence locators must name the exact page/paragraph and original PDF/file SHA where available. An agent saying 'verified' without inspectable evidence is a FAIL. Neither two agreeing models nor a reviewer paraphrase constitute independent primary verification. Escalate case-law precedent conflicts, disputed text, missing official source, and rights/access-marking issues to the legal advisor.

## Output at each checkpoint
- What actually exists (IDs, counts, hashes) and eight-source MML inventory, edition/page mapping and links to the original claims
- Sources accessed and not accessed
- Findings by P0/P1/P2/P3 with verified/unverified status
- Technical tests run with outputs and limitations
- Legal advisor decision queue and exact question for decision
- Proposed next packet and STOP/GO gate
- Explicit 'No application work performed'

Do not begin the 658-record full rollout until the legal advisor-reviewed pilot scorecard is accepted by owner.
