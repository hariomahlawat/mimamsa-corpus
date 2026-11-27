# PILOT-01 validation artifacts

| Artifact | State captured | Counts | Errors | Status |
| --- | --- | --- | --- | --- |
| `validation_result.json` | Pilot completion (2026-11-22, before remediation) | 205 sources / 124 findings / 33 reviews | 0 | **Historical: preserved unchanged** |
| `validation_result_current.json` | After remediation and final controls | 216 sources (209 + 7 from reviewer C) / 126 findings / 35 reviews | 0 | **Current** |
| `CI_EVIDENCE.md` | GitHub Actions on PR 6 | runs 45023068164, 45023723373, 45023781301 | success | CI record |

The current artifact records the git commit, the validator and schema SHA-256, the SHA-256 of every batch input file and of the frozen originals, the unit-test result, and the controls exercised. Validation is structural and traceability only, not legal correctness.
