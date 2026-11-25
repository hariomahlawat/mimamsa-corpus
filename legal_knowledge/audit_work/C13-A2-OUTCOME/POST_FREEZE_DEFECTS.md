# Post-freeze defects (V4 c13-extract-v4/1.0.0)

Recorded, never fixed in the frozen tool (PROTOCOL_C13.md v1.1).

| Date | Defect | Effect |
| --- | --- | --- |
| 2026-11-25 | Not a tool defect, a coverage limit: 5 of 300 H-OUT-C13 items point to copies whose sha256 is not in the C10 register, so V4 (input: c7 `ad77758d` text layer) has no text for them. | One abstention row each (`NO_JUDGMENT_ID_FOR_ITEM_SHA`). |
| 2026-11-25 | Review A2-03: the scorer-format conversion was done by an uncommitted script. | Fixed by documentation/tooling only: `tools/predict_holdout_v4.py --check` reproduces sha256 `45c5a332…`. No extractor change. |
| 2026-11-25 | Review A2-06: the restricted-material guard hardcodes the RM-001 sha instead of reading `config/restricted_material.json`. | No leak. Not fixed in the frozen tool; next version should read the register. |
