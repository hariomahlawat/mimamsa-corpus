# C13 holdings annotation packet guide (H-HOLD-C13), version 1 (interim)

**Status:** interim field layout. The Holdings V2 workstream owns the substantive annotation guideline
(`annotation_guideline_holdings.md`). Annotation must not start until that guideline is committed with a version
number and its sha256 is recorded in the annotation store manifest. If no legal adviser has reviewed it, it is marked
"not legally reviewed". This file fixes only the sheet layout and the vocabulary that the toolkit validates.

You are one of two independent annotators. You see only the source pointer and blank fields; no model output, no
other annotator's work, no selection information.

## Getting the file
Fetch `rep_raw_path` from `rep_raw_store`, verify SHA-256 equals `rep_sha256`, read the PDF.

## Rows
One row per holding or question of law stated by the court. Copy `item_id` and the pointer columns into each row and
add `coder_id` as the first column when returning the sheet. A judgment with no holding gets one row with
`item_type` blank is not allowed in a normal row; instead return one row with `notes` = `NO_HOLDING` and leave the other coding
fields blank (it is reported, not scored as an error).

| Field | Rule |
| --- | --- |
| `item_type` | `holding` or `question_of_law`. |
| `opinion` | `sole`, `lead`, `concurring`, `separate`, `dissent` or `unclear`: the opinion in which the sentence is written. |
| `judge` | Author of that opinion as printed, if stated. |
| `page` | PDF page (1-based) where the span starts. |
| `para` | Printed paragraph number if any. |
| `excerpt` | The span verbatim, copied from the page (one or more sentences). |
| `legal_issue` | Short neutral description of the issue. Not a legal conclusion beyond the text. |
| `certainty` | `certain`, `probable` or `uncertain`. |
| `notes` | Free text. |

Spans are compared with the pre-registered matcher (at least 3 shared content words, overlap/min >= 0.60, page within
1), so copy the court's words exactly.
