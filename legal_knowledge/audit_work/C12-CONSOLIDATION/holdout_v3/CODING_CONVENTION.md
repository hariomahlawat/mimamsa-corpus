# V3 holdout coding convention (one convention for every coder)

Each judgment is coded **independently by two coders**, who are blind to every extractor output and to each other.

**One row per proceeding** disposed of by the deciding court: each appeal, petition or application with its own number. Use `ALL` only when one common order disposes of every proceeding alike **and** the numbers are not individually listed.

## Fields (per proceeding)
| Field | Rule |
| --- | --- |
| `host_case_numbers` | Every case number of the deciding court's own proceedings, as printed on the cover or in the cause title. **Never** cited cases or the impugned order's number. |
| `proceeding` | This row's case number, exactly as printed. |
| `printed_disposal` | The court's operative words, mapped to one of the labels below. |
| `substantive_result` | What the proceeding achieved for the party who brought it. This differs from `printed_disposal` when, for example, the order says "disposed of" but grants the relief. |
| `party_specific` | Fill in when relief differs between appellants or respondents; otherwise leave blank. |
| `final_or_interim` | `final` or `interim`. |
| `page` | The page holding the operative words. |
| `para` | The paragraph number, if printed. |
| `excerpt` | The operative words, verbatim, at most 200 characters. |
| `confidence` | `high`, `medium` or `low`. |
| `notes` | Separate or dissenting opinions, composite files, corrections, truncation, misc-application disposals. Misc-application disposals are noted here and are never the main outcome. |

**Labels for `printed_disposal`:** allowed, partly_allowed, dismissed, dismissed_as_withdrawn, dismissed_as_infructuous, dismissed_in_default, disposed_of, disposed_of_with_directions, remanded, set_aside_and_remanded, transferred, not_final, other, unclear.

**Labels for `substantive_result`:** relief_granted, relief_partly_granted, relief_refused, no_adjudication (withdrawn, infructuous, transferred, default), remanded_for_fresh_decision, interim_only, unclear.

## Rules
- Use `unclear` rather than guess.
- **Never infer.** Read the cause title and the operative part fully.
- Verify the file's SHA-256 before reading.
