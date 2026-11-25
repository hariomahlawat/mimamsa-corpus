# Mimamsa offline application (Track B)

Isolated tree for the offline research application. It shares no code with the crawler or audit tooling and is tested by its own workflow (`.github/workflows/app-ci.yml`, path-filtered to `app/**`).

| Folder | Content | Status |
| --- | --- | --- |
| `contract/` | Data interchange contract v1 (JSON Schemas, validator, tests) shared with Track A | Proposed, Cycle 13 B0 |
| `design/` | UI/UX specification and design tokens | Proposed, Cycle 13 B0 |
| `poc/` | Proof-of-concept evidence P1–P9 (workstream B-PoC, separate branch) | [P4 synthetic protected delivery](poc/p4_pdf/README.md) available. Windows decision evidence pending. |

Stack choice is open until ADR-0005 (`docs/architecture/decisions/ADR-0005-APPLICATION-STACK.md`) is accepted at gate GB1. No legal reasoning, compliance logic or rule engine belongs in this tree in Cycle 13.
