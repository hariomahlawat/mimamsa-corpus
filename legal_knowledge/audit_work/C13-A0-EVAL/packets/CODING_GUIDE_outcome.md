# C13 outcome coding guide (H-OUT-C13), version 1

You are one of two independent coders. You see only the source pointer (file sha256, path and store) and blank
fields. You do not see any model output, any other coder's work, or how the item was selected. Do not look for them.
Do not discuss items with the other coder. Never infer: use `unclear` rather than guess.

## Getting the file
1. Fetch the PDF named by `rep_raw_path` from `rep_raw_store` (HF dataset `hariomahlawat/mimamsa-corpus` at the
   named commit; `data/raw/...` paths are also in the git raw-data commit `ad77758d`).
2. Verify its SHA-256 equals `rep_sha256` before reading. If it differs, code nothing and write `SHA_MISMATCH` in
   `notes` on one row.
3. Read the cause title and the whole operative part. Read the PDF itself, not a derived text file.

## Rows
One row per proceeding disposed of by the deciding court (each appeal, petition or application with its own number).
Copy the `item_id` and the four pointer columns unchanged into every row you add for the item. Add a first column
`coder_id` with your assigned coder id when you return the sheet. Use `ALL` in `proceeding` only when one common order
disposes of every proceeding alike and the numbers are not individually listed.

## Fields
| Field | Rule |
| --- | --- |
| `host_case_numbers` | Every case number of the deciding court's own proceedings, as printed on the cover or cause title. Never cited cases or the impugned order's number. |
| `proceeding` | This row's case number, exactly as printed. |
| `printed_disposal` | The court's own operative words mapped to one label (below). Quoted language from another order is not the court's disposal. |
| `substantive_result` | What the proceeding achieved for the party who brought it. |
| `party_specific` | Fill in (free text naming the parties) only when relief differs between appellants or respondents; otherwise blank. |
| `final_or_interim` | `final` or `interim`. |
| `page` | PDF page number (1-based) holding the operative words. |
| `para` | Paragraph number if printed, else blank. |
| `excerpt` | The operative words verbatim, at most 200 characters, copied from that page. |
| `confidence` | `high`, `medium` or `low`. |
| `notes` | Separate or dissenting opinions, composite files, corrections, truncation, misc-application disposals (never the main outcome). |

`printed_disposal` labels: allowed, partly_allowed, dismissed, dismissed_as_withdrawn, dismissed_as_infructuous,
dismissed_in_default, disposed_of, disposed_of_with_directions, remanded, set_aside_and_remanded, transferred,
not_final, other, unclear.

`substantive_result` labels: relief_granted, relief_partly_granted, relief_refused, no_adjudication (withdrawn,
infructuous, transferred, default), remanded_for_fresh_decision, interim_only, unclear.

Partly: use `partly_allowed` / `relief_partly_granted` only when the court grants less than the relief sought, not
when it grants all relief in other words.

Any value outside these vocabularies makes the sheet fail validation.
