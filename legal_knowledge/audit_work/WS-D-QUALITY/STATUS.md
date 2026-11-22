# WS-D Data quality and CI: STATUS

Branch `claude/ws-d-quality`, worktree `/home/user/ws-d`. Engineering/QA only; nothing here is legal adjudication. Never pushed.
Baseline: 658 KB (9a8f0d19...), 53 cases (8b8d53cd...), 87 codes (72 firm, 75 incl. 3 co-citation), 269 records without codes. Audit tests 54 at start, 113 after cycle 1, 166 after cycle 2.

## Done
- D1 `hash_reproduction.json` + `scripts/hash_reproduction.py`: KB/cases files match; PILOT-01 43/43 and R23-VERIFY-01 2/2 per-record manifest hashes reproduce (MML_PROVISION convention recovered: json.dumps sort_keys, default separators); MML manifest hash matches; 8/8 MML originals (scratchpad bytes) and transport ZIP match the receipt. CI step (no private bytes).
- D2 `tests/test_legal_audit_citation_register.py` (8): exact 87-code completeness, class counts 39/33/3/9/2/1, pinned non-firm membership; defect D-WSD-001 (8 stale register usage rows, 14 links) pinned.
- D3 `citation_resolution_score.json/.md`: code 72/87 confirmed (33 official, 39 record-explicit), 3/87 inferred, 12/87 unresolved; links 594/681; records 319/389 all-confirmed (319/658 overall).
- D4 `plaintext_citation_index.csv` + `scripts/build_plaintext_index.py`: 269/269 records, 403 segments, exact code-point offsets (references and body), deterministic; 11 UNANCHORED_LOCATOR segments.
- D5 validator/schema: always-on integrity rules + opt-in `audit_controls_version: v2`; additive schema fields; `tools/legal_audit/check_csv.py`; tests integrity controls (31), register semantics (8, owner date rule, no agent approval, r.23(3)/193/194 never promoted). Coordinator owner corrections adopted (date semantics; check_registers.py referenced by path, PR #16 version runs after integration; sync workflow untouched).
- D6 `relation_graph_report.md` / `relation_graph_summary.json` + script (CI step): 1716 edges, 0 dangling, 0 KB body duplicates; orphans/leads in OQ-D-008..011.
- D7 `coverage_scorecard.json/.md` + script: codes 52/87 searchable; links 520/681; coded records 279/389; plain-text Act sections 448/448 present; cases 23/53 official URL, 0/53 PDF hash.
- D8 `reviewer_provenance_ci_report.md`: identity bindings, 10 CI steps and coverage, stale validation record.
- CI workflow: +4 steps (CSV check, check_registers.py, hash reproduction, relation graph). YAML parses.
- Simulated integration onto origin/claude/next-stage-proposal (PR #16): all audit tests, strict validations, check_registers (corrected) and CSV check pass.

## Cycle 2 (started after coordinator merge 1be2a2e1)
- C2-1 DONE `coverage_reconciliation.md/.csv` + `scripts/coverage_reconciliation.py` (WS-C read-only via git ref or worktree): coarse agreement 562/658; 96 disagreements all explained by 11 definitional rules (R1 co-citation 39, R2 pinpoint 32, R8 no-citation definition 12, R7 plain instrument set 13 ...); code sets identical 658/658; canonical definition proposal (OQ-D-016). Tests `test_legal_audit_coverage_reconciliation.py` (7).
- C2-2 DONE `registers/source_code_resolution_v4_proposed.csv`, `registers/source_code_resolution_v4_diff.csv`, `registers/REGISTER_V4_PROPOSAL.md`, `scripts/build_register_v4.py`; root cause: v2 grammar lacked bare `[CODE]` and leading-digest forms, v3 refreshed forms_used but not usage on 78 v2-carried rows; 8 codes / 14 links (cycle-1 '15' corrected); classes unchanged; tests `test_legal_audit_register_v4.py` (7).
- C2-3 DONE `tools/legal_audit/check_provenance.py` (rules IMG-1/2/3, RV-1, CA-1/2, ACQ-1, APR-1 over all audit CSV/JSON; render evidence resolves via check ids, document hashes and foreign keys) + `tools/legal_audit/provenance_baseline.json` (21 known violations: ACQ-02 copy_fidelity x17, PILOT-01 PIC-08/09, WS-A PCL-BL-25 and stale AR-029 copy); passes on HEAD and on WS-A/B/C branch trees; CI step. Optional `manual_supported` relation layer: `docs/legal-audit/schemas/relation.schema.json` + validator `relation_checks` (never statutory authority; cannot be finding/review evidence; MML hash, registered render, KB id). Tests `test_legal_audit_provenance_controls.py` (21). OQ-D-017..020.
- C2-4 DONE `tests/test_legal_audit_check_registers.py` (18): runs the unmodified coordinator script on a temp copy of its inputs with one-cell mutations; covers date rule (effective date only with STATED_IN_INSTRUMENT, = publication date, ISO, missing status, version seed), continuation pages, TEXT_LAYER/LOCATED, unknown PIC, C-08/r.193 OPEN, C-09/r.194 PROPOSAL, r.23(3) CONFLICTING, approval; gap OQ-D-021.

## In progress
- Nothing (cycle 2 complete).

## Next (if continued)
- Coordinator decisions on OQ-D-001..015; possible v4 register proposal (D-WSD-001) and frozen-batch date-rule migration proposal (OQ-D-006), each as separate additive files.

## Blockers
- None. Human-reviewer nomination (OQ-D-007) needed before any v2 batch can record a legal-advisor review.

## Requests to coordinator
- See `open_questions.csv` (OQ-D-001..021).
