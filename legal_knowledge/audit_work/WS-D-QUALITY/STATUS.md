# WS-D Data quality and CI: STATUS

Branch `claude/ws-d-quality`, worktree `/home/user/ws-d`. Engineering/QA only; nothing here is legal adjudication.
Baseline: 658 KB (9a8f0d19...), 53 cases (8b8d53cd...), 87 codes (72 firm, 75 incl. 3 co-citation), 269 records without codes; 54 audit tests at start.

## Done
- D1 `hash_reproduction.json` + `scripts/hash_reproduction.py`: KB/cases files match; PILOT-01 43/43 and R23-VERIFY-01 2/2 per-record manifest hashes reproduce; MML manifest hash matches; 8/8 MML originals (scratchpad bytes) and transport ZIP match the receipt.
- D2 `tests/test_legal_audit_citation_register.py` (8 tests): exact 87-code register completeness and class counts; pins defect D-WSD-001 (stale usage counts in 8 rows).

## In progress
- D3 confirmed vs inferred score.

## Next
- D4 plain-text citation index; D5 validator/schema rules; D6 relation graph; D7 coverage scorecard; D8 reviewer/CI report; CI steps.

## Blockers
- None.

## Requests to coordinator
- See `open_questions.csv` (OQ-D-001..003).
