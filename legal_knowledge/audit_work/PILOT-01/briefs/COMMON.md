# PILOT-01 common packet rules (all agents)

DATABASE ONLY. NO APPLICATION WORK. Owner approved this bounded pilot on 2026-11-22.
Advisor: NOT YET NOMINATED. All agent output is unapproved research.

## Paths (absolute)
- Repo root: `/home/user/mimamsa-corpus` (branch `claude/gifted-bardeen-byeim6`; do NOT commit, push, or change branches).
- Your agent definition: `/home/user/mimamsa-corpus/.claude/agents/<agent>.md` — read it first and follow it, plus
  `docs/legal-audit/EVIDENCE_STANDARD.md` and `docs/legal-audit/MML_SOURCE_PRIORITY.md`.
- Frozen input: `legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl` (SHA-256 9a8f0d19…5befcfc1),
  `legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl`. Pilot manifest with per-record hashes:
  `legal_knowledge/audit_work/PILOT-01/pilot-manifest.json`. NEVER edit any of these.
- Derived text (local only, never commit or paste at length):
  `/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/derived/`
  - `mml/<file>.pages.txt` — PDFs, markers `=== PDF_PAGE n / file=… ===` (locator = PDF page; printed page may differ)
  - `mml/<file>.lines.txt` — DOCs converted by LibreOffice, prefix `Lnnnnn|` (locator = derived LINE, not a printed page)
  - `statutes/*.txt` — corpus India Code texts with `[[page n]]` markers; `statutes/*.json` metadata incl. source_url and sha256
  - `DERIVED_SHA256SUMS`
- MML original hashes: `legal_knowledge/manual_sources/MML_Originals_Manifest.csv`.
- Downloads you make: save under `…/scratchpad/downloads/<agent>/`, compute SHA-256, record it.

## Network
Reachable official sources: indiacode.nic.in / indiacode.gov.in, api.sci.gov.in (JUDIS PDFs), sci.gov.in, archive.org.
Unreachable from this container (timeout): egazette.gov.in, mod.gov.in, aftdelhi.nic.in → record the gap, outcome BLOCKED/UNVERIFIED.
Commercial/unofficial (Indian Kanoon, SCC Online, Manupatra, Casemine, Legitquest, blogs): discovery only. If used, register
as source_type SECONDARY, authenticity SECONDARY; never the basis of SOURCE_VERIFIED. No login/CAPTCHA/paywall bypass.

## Outputs — write ONLY your own files
- `PILOT-01/sources/<agent>.json` and `PILOT-01/findings/<agent>.json`: each a JSON array of objects conforming to
  `docs/legal-audit/schemas/{source,finding}.schema.json` (additionalProperties=false — no extra keys).
- ID prefixes: sources `S-<TAG>-nnn`, findings `F-<TAG>-nnn`. TAG: MML, STAT, JUD, PROC, XVOL, BLIND, REV.
- Do NOT read `PILOT-01/blind_staging/` or other agents' findings unless your brief says so.
- Check your work: `python3 tools/legal_audit/validate.py --batch legal_knowledge/audit_work/PILOT-01 --manifest legal_knowledge/audit_work/PILOT-01/pilot-manifest.json --strict`
  (errors about other agents' missing coverage are expected; fix every error in YOUR files).

## Finding rules (validator-enforced)
- `batch_id` "PILOT-01"; `record_id` and `original_sha256` exactly from pilot-manifest.json.
- `original_location` "records_658.jsonl:line N" (or "MMLPKT-xx"); `original_text` = verbatim excerpt of the record's claim being tested.
- Every assigned record gets ≥1 finding with `examination_outcome`:
  NO_ISSUE_FOUND (only with SOURCE_VERIFIED, pinpointed primary authority) | DISCREPANCY | CONFLICTING_SOURCES (with verification_state CONFLICTING)
  | UNVERIFIED | BLOCKED (with review_state BLOCKED).
- SOURCE_VERIFIED requires ≥1 cited source of type STATUTE/RULE/GAZETTE/REGULATION/JUDGMENT/ORDER/OTHER_PRIMARY that is itself
  SOURCE_VERIFIED with a pinpoint; every source in `source_ids` of a verified finding must itself be SOURCE_VERIFIED.
  Manual (MML) sources go in `mml_anchor_ids`, never as sole proof.
- Statute/rule/gazette sources need `version_or_decision_date` or `effective_date`; judgments need `version_or_decision_date`.
- Fill `pinpoint` and `temporal_scope` (what date/version the check speaks to; e.g. "India Code consolidation retrieved 2026-11-21; amendment chain after 2019 not verified").
- severity per EVIDENCE_STANDARD (P0 coercive/court-martial/false citation …). P0/P1/CONFLICTING ⇒ `requires_legal_review: true`,
  `legal_review_state: "QUEUED_ADVISOR_NOT_NOMINATED"`. Otherwise `legal_review_state: "NOT_REQUIRED"` is allowed.
- `proposed_text`: a proposal only (or null). Never claim the record has been changed.
- Add `advisor_questions` and `limitations` (what you did NOT check). Set `agent` to your agent name.
- Source records: set `retrieved_by` to your agent name and `content_role`
  (ENACTED_TEXT / GAZETTE_TEXT / JUDGMENT_TEXT / MANUAL_REPRODUCED_LEGAL_TEXT / MANUAL_COMMENTARY / SECONDARY_TEXT / METADATA_ONLY).
  India Code corpus texts: source_type STATUTE/RULE, authenticity OFFICIAL_COMPILATION, sha256 from the meta JSON.
  MML: source_type MANUAL, authenticity USER_SUPPLIED_REFERENCE, sha256 from the manifest, locator naming the exact file.
- Quotations: ≤ 40 words per quote from MML. No invented pinpoints, citations or holdings.

## Fixed positions
- Army Rules r.23(3) caution: government compilations omit "not"; MML copies include it; original S.R.O. 484 (27-11-1954) not held.
  Record as CONFLICTING; never resolve.
- Absence of a found source/treatment is not proof of absence.

## Final reply (≤ 300 words)
Counts by outcome and severity, files written, blockers, anything you could not do. No legal approval language.
