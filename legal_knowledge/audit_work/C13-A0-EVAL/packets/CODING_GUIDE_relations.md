# C13 citation-relation coding guide (H-REL-C13), version 1.1

You are one of two independent coders. Each item is one page of one judgment (`pages_to_code`). You see only the
source pointer and blank fields.

## Getting the file
Fetch `rep_raw_path` from `rep_raw_store`, verify SHA-256 equals `rep_sha256`, read page `pages_to_code` of the PDF
(1-based PDF page). Read the surrounding pages only to understand context.

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
One row for **every** citation of a judicial decision on that page (case name and/or report citation, neutral
citation or case number of another decision). If the page cites no decision, return one row with `page` filled,
`cited_string` = `NONE`, `relation_type` = `other`, `voice` = `unclear`, `confidence` = `high`.
Copy `item_id` and the pointer columns into each row and add `coder_id` as the first column when returning the sheet.

| Field | Rule |
| --- | --- |
| `page` | The page coded (equals `pages_to_code`). |
| `cited_string` | The citation exactly as printed (prefer the report or neutral citation; else the case number; else the case name). |
| `cited_case_name` | Case name as printed, if any. |
| `target` | The cited decision identified as precisely as the page allows: neutral citation, else report citation, else court + case number + date. `UNRESOLVED` if it cannot be identified from the page. |
| `relation_type` | How the citing court treats the cited decision in its own words: cites, follows, applies, distinguishes, overrules, doubts, not_followed, refers_to_larger_bench, other, unclear. |
| `voice` | Whose words the treatment is: court_own, quoted_passage, party_submission, lower_forum, editorial (headnote / reporter text), unclear. |
| `excerpt` | The sentence carrying the citation or the treatment, verbatim from the page. |
| `confidence` | high, medium, low. |
| `notes` | Free text. |

`overrules` only where the court itself, with authority to do so, says the cited decision is overruled or no longer
good law. A treatment in a party's submission or in a quoted passage keeps `voice` accordingly; do not convert it into
the court's treatment.
