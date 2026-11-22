# WS-D Data quality and CI: STATUS

Branch `claude/ws-d-quality`, worktree `/home/user/ws-d`. Engineering/QA only; nothing here is legal adjudication.
Baseline: 658 KB (9a8f0d19...), 53 cases (8b8d53cd...), 87 codes (72 firm, 75 incl. 3 co-citation), 269 records without codes; 54 audit tests at start.

## Done
- D1 `hash_reproduction.json` + `scripts/hash_reproduction.py`: KB/cases files match; PILOT-01 43/43 and R23-VERIFY-01 2/2 per-record manifest hashes reproduce; MML manifest hash matches; 8/8 MML originals (scratchpad bytes) and transport ZIP match the receipt.
- D2 `tests/test_legal_audit_citation_register.py` (8 tests): exact 87-code register completeness and class counts; pins defect D-WSD-001 (stale usage counts in 8 rows).
- D3 `citation_resolution_score.json/.md` + script: code 72/87 confirmed, 3/87 inferred, 12/87 unresolved; links 594/681 confirmed; records 319/389 all-confirmed (319/658 overall).
- D4 `plaintext_citation_index.csv` + `scripts/build_plaintext_index.py`: 269/269 uncoded records, 403 segments, exact code-point offsets (references + body), deterministic; 11 UNANCHORED_LOCATOR segments (ADM-JD-01/03/04/05, V7-T01..T07).
- `tests/test_legal_audit_wsd_artifacts.py` (7 tests): regeneration equality, offsets, no-inflation.
- D5 validator/schema (`tools/legal_audit/validate.py` integrity_checks; `source.schema.json` additive fields proof_type, render_sha256, publication_date, commencement_as_printed, effective_date_status). Always-on rules (pass frozen batches unchanged) + opt-in `audit_controls_version: v2`. `tools/legal_audit/check_csv.py` (generic CSV well-formedness). Tests: `test_legal_audit_integrity_controls.py` (31), `test_legal_audit_register_semantics.py` (8): owner date rule over every CSV with effective_date, no agent-asserted approval, r.23(3)/r.193/r.194 never promoted. Verified also against origin/claude/next-stage-proposal (PR #16) registers.
- CI: new steps check_csv.py, ARMY-RULES-CHAIN-01/check_registers.py (path reference only; PR #16's corrected version runs after integration), hash reproduction.

- D6 `relation_graph_report.md`, `relation_graph_summary.json`, `scripts/relation_graph.py` (CI step, exits 1 on dangling/ID collision): 1716 edges, 0 dangling (incl. 24 register targets checked against origin/raw-data@ad77758d data/meta, read locally); 0 exact/normalised/near-duplicate KB bodies; orphans and leads in OQ-D-008..011. Simulated integration onto origin/claude/next-stage-proposal: 111 audit tests pass.

- D7 `coverage_scorecard.json/.md` + script (crawler corpus read locally from origin/raw-data@ad77758d): codes 52/87 searchable; links 520/681; coded records 279/389 all-searchable; plain-text statute segments 251/261 instrument-searchable, cited Act sections 448/448 present; cases 23/53 official-host URL, 0/53 PDF hash; whole KB 279/658 + 169/658.

## In progress
- D8 reviewer provenance and CI report.

## Next
- D8 reviewer/CI report.

## Blockers
- None.

## Requests to coordinator
- See `open_questions.csv` (OQ-D-001..013).
