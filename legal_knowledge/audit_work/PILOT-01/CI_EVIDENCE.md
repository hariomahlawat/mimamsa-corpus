# CI evidence: PILOT-01 remediation (GitHub Actions, actual results)

| Item | Value |
| --- | --- |
| Pull request | hariomahlawat/mimamsa-corpus#6 (draft): head `claude/audit-pilot-01`, base `legal-knowledge/claude-audit-agents-v1` (PR 5 kit) |
| Workflow | `.github/workflows/legal-audit-kit-ci.yml` ("Legal Database Audit Kit Validation"), event `pull_request` |
| Run | 45023068164 (run #11), attempt 1, head SHA `245dd04f621aaba5af044d117f7a2e0f8f8eae35` |
| Job | 137210009716 `audit-kit-tests`, ubuntu-latest, Python 3.11.18; started 12:35:27Z, finished 12:35:36Z (2026-11-22) |
| Conclusion | **success** |

Step results (from the job API and log):
1. Validate audit schemas: success ("Audit schema files readable and internally consistent").
2. Test fail-closed review checks: success, **"Ran 33 tests … OK"**. These are the 10 identity controls, 19 extended controls and 4 original validator tests. The JSON blocks in the log are the expected failure outputs that the negative tests deliberately produce.
3. Validate PILOT-01 audit batch (strict, frozen manifest, reviewer identities): success, `{"source": 209, "finding": 126, "review": 33}`, `"errors": []`.
4. Check frozen originals are unchanged: success. `records_658.jsonl: OK`, `cases_53.jsonl: OK`.

Warnings: GitHub's Node.js 20 deprecation notice for `actions/checkout@v4` and `actions/setup-python@v5` (forced to Node 24). Not a failure.

What CI does **not** cover:
- The full `tests/` crawler suite (needs pymupdf and other dependencies; 5 import errors locally, unrelated to the audit).
- MML extraction. The originals are not in CI by design, and determinism was verified locally (8/8 MATCH).
- Legal correctness. The validator checks structure and traceability only.

Earlier run on the PR 5 head (for comparison): run 45015175390, success.

Separation of changes: PR 6 contains audit paths only (75 files). The crawler and state changes from `main` commit 21de353 (`PROGRESS.md`, `reports/ocr_review.md`, `state/wider_terms_hits.json`) exist only on `claude/gifted-bardeen-byeim6`, via its merge of `main`, and are not part of the audit PR.
