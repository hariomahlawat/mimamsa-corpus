# C13 holdings annotation packet guide (H-HOLD-C13), version 1.1 (interim)

**Status:** interim field layout. The Holdings V2 workstream owns the substantive annotation guideline
(`annotation_guideline_holdings.md`). Annotation must not start until that guideline is committed with a version
number and its sha256 is recorded in the annotation store manifest. If no legal adviser has reviewed it, it is marked
"not legally reviewed". This file fixes only the sheet layout and the vocabulary that the toolkit validates.

You are one of two independent annotators. You see only the source pointer and blank fields; no model output, no
other annotator's work, no selection information.

## Getting the file
Fetch `rep_raw_path` from `rep_raw_store`, verify SHA-256 equals `rep_sha256`, read the PDF.

## Items you cannot code (UNCODABLE)

If an item cannot be coded, return exactly one row for it with `notes` = `UNCODABLE:<CODE>` followed by a short
explanation, `page` if relevant, and every other coding field blank. The item stays in the sample, is counted and
reported, and is never replaced. Codes:

| Code | When |
| --- | --- |
| `SHA_MISMATCH` | The fetched file's SHA-256 differs from `rep_sha256` (read nothing further) |
| `FILE_UNAVAILABLE` | The file cannot be fetched from the named store |
| `UNREADABLE` | The PDF does not open or its pages cannot be read, even as images |
| `CONTENT_MISSING_TRUNCATED` | Pages needed for coding are missing or cut off |
| `NOT_A_JUDGMENT` | The document is not a judgment or order of a court |
| `MISIDENTIFIED_DOCUMENT` | The file is a different case from the one it appears to be (e.g. wrong cause title) |
| `OUT_OF_SCOPE` | The document is outside the corpus scope (not a military-law or armed-forces service matter) |
| `PAGE_ABSENT` | The page to code does not exist in the file |
| `OTHER` | Anything else; explain in the note |

Use `unclear` labels, not UNCODABLE, when the document is readable but the answer is uncertain.

## Rows
One row per holding or question of law stated by the court. Copy `item_id` and the pointer columns into each row and
add `coder_id` as the first column when returning the sheet. For a readable judgment that states no holding or
question of law, return one row with `notes` = `NO_HOLDING` and every other coding field blank; it is reported, not
scored as an error.

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
