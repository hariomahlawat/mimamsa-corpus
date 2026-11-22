# Workstream charters (coordinator: orchestrator; programme issue #10)

**DATABASE ONLY. NO APPLICATION, UI, API OR RAG WORK.**
Binding for every agent: `docs/legal-audit/SOURCE_AUTHORITY_POLICY.md` (v1), `docs/legal-audit/EVIDENCE_STANDARD.md`, `docs/legal-audit/GIT_WORKFLOW.md`.

## Common rules (all workstreams)
1. **Isolation.**
   - Each agent works only in its own worktree and branch, and writes only to the paths it owns (table below).
   - Other paths are read-only.
   - It commits locally on its own branch and never pushes. The coordinator reviews, pushes and opens the PR.
2. **Immutable inputs.** These are never edited:
   - `legal_knowledge/curated_originals/**` (658 KB records, sha 9a8f0d19…; 53 cases, sha 8b8d53cd…)
   - `legal_knowledge/manual_sources/**`
   - `data/**`
   - existing audit batches (PILOT-01, R23-VERIFY-01, ACQ-01, ACQ-02, ARMY-RULES-CHAIN-01, SOURCE-CONFLICTS-01)
   - `docs/legal-audit/*.md` policy files

   Corrections are new, versioned proposal files.
3. **No approval is implied by this programme.**
   - No downloads of source documents into the corpus.
   - No crawler-config change, HF upload or sync, PR merge, push, or correspondence.
   - Read-only network lookups are allowed: search pages, metadata JSON, HTML views of official pages. Each workstream may also read bytes **already held** in the session scratchpad.
   - A need for a new download becomes an **acquisition request row**, not a fetch.
4. **Evidence.**
   - Every result carries source identity, exact anchor (page/para), date/edition, carrier provenance (policy v1), SHA-256 of any file relied on, uncertainty, severity, and the affected KB/case IDs.
   - Legally significant wording (negations, numbers, provisos, dates) must be read from a page image, with the render SHA-256 recorded. OCR alone never establishes wording or amendment status. Absence in a search is NOT_FOUND, never "no amendment".
5. **States are distinct and never substituted:** source located → source/page verified → amendment chain complete → technical review completed → legal-advisor adjudicated → JAG formally validated. Agents can reach at most "technical review completed". Agreement between sources is not approval.
6. **Fixed determinations:**
   - Rule 23(3) = CONFLICTING.
   - Rule 194 = PROPOSAL pending legal review.
   - Rule 193 = OPEN (U-04, s.90(i)/91(i)); establish the chronology before proposing any correction.
7. **Resumability.**
   - Each workstream keeps `<WS-DIR>/STATUS.md`: done, in progress, next, blockers, open questions. Update it at every commit.
   - Commit early and often; each commit is self-describing.
8. **Before each commit:**
   - `python3 -m unittest discover -s tests -p 'test_legal_audit_*.py'` must pass;
   - the strict validation of PILOT-01 and R23-VERIFY-01 must pass;
   - `python3 legal_knowledge/audit_work/ARMY-RULES-CHAIN-01/check_registers.py` must pass (on branches that contain the next-stage proposal, i.e. all workstream branches).
9. **Unknowns go in the workstream's open-questions register.** Never invent an answer.

## Ownership and charters
| WS | Issue | Branch / worktree | Owns (write) | Inputs | Deliverables | Acceptance | Depends on |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A Statutory & Gazette | #11 | `claude/ws-a-statutory` · `/home/user/ws-a` | `legal_knowledge/audit_work/WS-A-STATUTORY/**` | ARMY-RULES-CHAIN-01 (baseline v1, read-only), ACQ-01/02, R23-VERIFY-01 registers; scratchpad Gazette PDFs | (1) deduplicated exhaustive instrument search inventory; (2) acquisition-request batches, each separate from PR #8's 14 URLs and from ACQ-02; (3) provision change log (notification → rule → text before/after → commencement → span), including S.R.O. 17(E)/1993 itemised and the r.193/194 1954 base text; (4) identity/hash/page-image/transcription register; (5) NOT_FOUND/NOT_CHECKED gaps; Army Act amendment chain (Acts 19/1955, 13/1975, 37/1992 …) | Every row traceable to an instrument and page; no OCR-only determination; r.23(3)/r.194/r.193 states unchanged | none (reads A-owned baseline) |
| B Judgments | #12 | `claude/ws-b-judgments` · `/home/user/ws-b` | `legal_knowledge/audit_work/WS-B-JUDGMENTS/**` | `origin/raw-data` (intern intake: data/meta, data/raw), cases_53 (frozen), issues #3/#4, PILOT-01 judgment findings | (1) dedup intake manifest; (2) identity/citation resolution register; (3) holding/obiter/argument with pinpoint paras; (4) statutes cited plus effective-date checks; (5) subsequent treatment; (6) adverse/conflict queue; (7) crosswalk to 53 cases and 658 KB | No collection duplicating the intern; no third-party holding treated as verified; every holding pinned to a para of an official copy | none |
| C MML & procedure | #13 | `claude/ws-c-mml` · `/home/user/ws-c` | `legal_knowledge/audit_work/WS-C-MML/**` | MML originals (private; scratchpad extraction, manifest SHA), PILOT-01 crosswalk/edition notes, advisor packet | immutable input manifest; provision crosswalk with para/page; edition status; gap/conflict register; candidate corrections; **all-658 read-only source-coverage inventory**; ranked high-risk calibration samples | No complete derived MML text committed (excerpts ≤ the minimum needed); no correctness verdicts on the 658; edition never asserted official without authentication | none (uses A's outputs later, if available) |
| D Data quality & CI | #14 | `claude/ws-d-quality` · `/home/user/ws-d` | `legal_knowledge/audit_work/WS-D-QUALITY/**`; **lease:** `tools/legal_audit/**`, `docs/legal-audit/schemas/**`, `tests/test_legal_audit_*.py` (new files freely; edits to existing tests only to extend, never weaken), `.github/workflows/legal-audit-kit-ci.yml` | 658/53 originals, code inventory (87), source_code_resolution_v3, all audit registers | (1) hash reproduction; (2) 87-code completeness test; (3) confirmed vs inferred score; (4) plain-text citation index (269 records, exact passages); (5) schema/validator tests (proof type, authority vs carrier, dates, relations, review-state separation); (6) relation graph and duplicate detection; (7) coverage scorecard with denominator; (8) reviewer provenance and CI report; CI job running `check_registers.py` | Existing tests never weakened; no KPI inflation (72/87 firm); CI green | Lease: no other WS touches the validator, schemas or CI |

**Branch stack (owner instruction, 2026-11-22):** PR #6 (`claude/audit-pilot-01`) → stacked proposal PR (`claude/next-stage-proposal`: ACQ-02, ARMY-RULES-CHAIN-01, update c/d, plan) → one PR per workstream (base `claude/next-stage-proposal`).

**Coordinating reviewer:** the orchestrator reviews each hand-off. Review notes go only in `COORDINATION/reviews/<WS>-<n>.md`. The reviewer never edits files in a workstream's directory; a required change is returned to the agent, or recorded as a review condition.

Coordinator-owned: `legal_knowledge/audit_work/COORDINATION/**` and `NEXT_STAGE_PLAN.md`.
**Conflict rule:** if a workstream needs a change in another's path, it writes a request in its own `STATUS.md`, and the coordinator routes it.
