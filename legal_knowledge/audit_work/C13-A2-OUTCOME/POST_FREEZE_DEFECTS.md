# Post-freeze defects (V4 c13-extract-v4/1.0.0)

Recorded, never fixed in the frozen tool (PROTOCOL_C13.md v1.1).

| Date | Defect | Effect |
| --- | --- | --- |
| 2026-11-25 | Not a tool defect, a coverage limit: 5 of 300 H-OUT-C13 items point to copies whose sha256 is not in the C10 register, so V4 (input: c7 `ad77758d` text layer) has no text for them. | One abstention row each (`NO_JUDGMENT_ID_FOR_ITEM_SHA`). |
