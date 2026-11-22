# WS-D Data quality and CI: STATUS

Branch `claude/ws-d-quality`, worktree `/home/user/ws-d`. Engineering/QA only; nothing here is legal adjudication. Never pushed.
Baseline: 658 KB (9a8f0d19...), 53 cases (8b8d53cd...), 87 codes (72 firm, 75 incl. 3 co-citation), 269 records without codes. Audit tests 54 at start, now 113.

## Done
- D1 `hash_reproduction.json` + `scripts/hash_reproduction.py`: KB/cases files match; PILOT-01 43/43 and R23-VERIFY-01 2/2 per-record manifest hashes reproduce (MML_PROVISION convention recovered: json.dumps sort_keys, default separators); MML manifest hash matches; 8/8 MML originals (scratchpad bytes) and transport ZIP match the receipt. CI step (no private bytes).
- D2 `tests/test_legal_audit_citation_register.py` (8): exact 87-code completeness, class counts 39/33/3/9/2/1, pinned non-firm membership; defect D-WSD-001 (8 stale register usage rows) pinned.
- D3 `citation_resolution_score.json/.md`: code 72/87 confirmed (33 official, 39 record-explicit), 3/87 inferred, 12/87 unresolved; links 594/681; records 319/389 all-confirmed (319/658 overall).
- D4 `plaintext_citation_index.csv` + `scripts/build_plaintext_index.py`: 269/269 records, 403 segments, exact code-point offsets (references and body), deterministic; 11 UNANCHORED_LOCATOR segments.
- D5 validator/schema: always-on integrity rules + opt-in `audit_controls_version: v2`; additive schema fields; `tools/legal_audit/check_csv.py`; tests integrity controls (31), register semantics (8, owner date rule, no agent approval, r.23(3)/193/194 never promoted). Coordinator owner corrections adopted (date semantics; check_registers.py referenced by path, PR #16 version runs after integration; sync workflow untouched).
- D6 `relation_graph_report.md` / `relation_graph_summary.json` + script (CI step): 1716 edges, 0 dangling, 0 KB body duplicates; orphans/leads in OQ-D-008..011.
- D7 `coverage_scorecard.json/.md` + script: codes 52/87 searchable; links 520/681; coded records 279/389; plain-text Act sections 448/448 present; cases 23/53 official URL, 0/53 PDF hash.
- D8 `reviewer_provenance_ci_report.md`: identity bindings, 10 CI steps and coverage, stale validation record.
- CI workflow: +4 steps (CSV check, check_registers.py, hash reproduction, relation graph). YAML parses.
- Simulated integration onto origin/claude/next-stage-proposal (PR #16): all audit tests, strict validations, check_registers (corrected) and CSV check pass.

## In progress
- Nothing.

## Next (if continued)
- Coordinator decisions on OQ-D-001..015; possible v4 register proposal (D-WSD-001) and frozen-batch date-rule migration proposal (OQ-D-006), each as separate additive files.

## Blockers
- None. Human-reviewer nomination (OQ-D-007) needed before any v2 batch can record a legal-advisor review.

## Requests to coordinator
- See `open_questions.csv` (OQ-D-001..015).
