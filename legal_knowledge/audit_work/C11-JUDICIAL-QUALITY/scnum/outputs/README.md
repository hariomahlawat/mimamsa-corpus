# C11 - Supreme Court case-number recovery (proposal, not applied)

Tool: `tools/scnum_c11.py` (scnum_c11/1.0). Deterministic; standard library only.
Regenerate: `python tools/scnum_c11.py --repo /home/user/c7`; verify: add `--check`.

## Scope

The 368 Supreme Court records in C10 `HF_JUDGMENT_METADATA_AUDIT.csv` whose `case_numbers_meta` is empty (the tool fails closed if the count differs). No metadata record is modified: every row is `status=PROPOSAL_NOT_APPLIED`, `method=AUTOMATED_RULES`.

## Inputs and integrity

* Source PDF bytes: `git show ad77758d:<path>` (path from C10 `HF_JUDGMENT_COPY_REGISTER.csv`); re-hashed, must equal the audited sha256, else the run aborts.
* Text layer: `ad77758d:data/text/<doc_id>.txt` (pipeline extraction of those bytes, `[[page N]]` markers = PDF page numbers). Metadata `ad77758d:data/meta/<doc_id>.json` (sha256 cross-checked).
* Curated cases: `21e73b83:legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl` (read-only), matched on identical decision date plus a shared significant title word.
* File names are never used.

## Method

1. Flatten the text layer (whitespace collapsed) keeping a map from every character to page and line.
2. Locate the jurisdiction heading (`CIVIL APPELLATE JURISDICTION:`, `ORIGINAL JURISDICTION`, ...; OCR tolerant, edit distance <= 4, must be upper-case and followed by a colon or preceded by APPELLATE/ORIGINAL; lower-case prose 'jurisdiction' is never used). The first heading opens the block; the block ends at counsel appearances (`for the Appellant`, `Appearances for Parties`, `Judgment of the Court was delivered`, ...) or after 2,500 characters.
3. Inside the block, find every `No./Nos./No(s).` marker followed by a number; read the case type backwards (label words / abbreviations, gutter letters A-H skipped) and the number list forwards (lists, `and`/`&`, ranges `4415-16`, `22 to 26`, `831/93`, `of 2004`, OCR `of2004`, gutter letters between tokens).
4. A small state machine assigns each reference: HOST (start of block, after a further jurisdiction heading, or after `WITH` / `With` / `AND` / `alongwith` = connected matter); ARISING after `From the Judgment and Order`, `Appeal by special leave from`, `arising out of`, `impugned`, `against the order` (recorded in `arising_from`, never as host); PARENT when the reference is introduced by `in`/`In` (e.g. `Civil Misc. Petition No. X In Civil Appeal No. Y`, `Contempt Petition ... in W.P.(C) ...`); DESC after `Under Article 32`. References followed by `decided on` / `reported in` are treated as citations and dropped. A host number identical to an arising number is removed.
5. Fallback for the newer SCR layout without a heading: the parenthesised cause-title number immediately before the decision date line (`(Civil Appeal No. 5605 of 2010) JUNE 25, 2014`) on pages 1-3. When both are present they are cross-checked.
6. Case types normalised: CA, CRLA, WPC, WPCRL, WP (unqualified), SLPC, SLPCRL, TPC, TCC, CONTC, RPC, CURPC, MA, CMP, CRLMP, IA, ELA, ELP, OS, REF, PET (bare 'Petition' under Art. 32 in old SCR), APPEAL (bare). Form `TYPE-NUMBER-YEAR`; ranges are expanded; suffix letters kept (`CA-5085A-1991`).

## Classification (exactly one per record)

* CONFIRMED_FROM_SOURCE - one host number, recognised type, clean number and year.
* CONFIRMED_MULTIPLE_CONNECTED - several clean host numbers (joint list, range or WITH matters).
* PARTIALLY_CONFIRMED - host located but some part needs a human: year/number OCR-garbled or repaired (letter->digit), unrecognised type, `etc.` elision, or heading found but no number parsed.
* AMBIGUOUS - competing candidates: cause-title number disagrees with the jurisdiction block, curated case number disagrees, or the only heading lies late in the file (may belong to the next reported case in an SCR page range).
* NOT_RECOVERABLE - no text layer, or no heading/cause-title number printed.

## Result

| classification | count |
| --- | --- |
| CONFIRMED_FROM_SOURCE | 219 |
| CONFIRMED_MULTIPLE_CONNECTED | 101 |
| PARTIALLY_CONFIRMED | 45 |
| AMBIGUOUS | 3 |
| NOT_RECOVERABLE | 0 |
| TOTAL | 368 |

`REVIEW_QUEUE.csv` holds 68 rows: every AMBIGUOUS, PARTIALLY_CONFIRMED and NOT_RECOVERABLE record plus 20 CONFIRMED records chosen by lowest sha256(`C11-SCNUM-REVIEW-SAMPLE-v1` + doc_id).

## Output columns (beyond the required ones)

`page` = PDF page marker of the first host reference in the text layer; `line` = line within that page of the text layer; `locator` = JURISDICTION_BLOCK or CAUSE_TITLE_PARENTHESIS; `parent_case` = matter in which an application/petition was filed; `flags` = parser warnings on host references; `notes` = cross-check results; `curated_match` = MATCH, MATCH_CURATED_SUBSET, PARTIAL_OVERLAP, MISMATCH, CURATED_RECORD_WITHOUT_NUMBER, CURATED_ONLY or NO_CURATED_RECORD.

## Known failure patterns (all routed to the review queue)

* OCR digit noise in number or year (`82 I of2001`, `of I999`, `of 200L`, `of 1~~`, `Petitions Nos. 22 to '.!G ... of Ul50`).
* Lists interrupted by a page break/running header that the header filter does not recognise, or missing commas (`879 1209`), split digits (`254 7`, `3 798`).
* Abbreviated second numbers (`Civil Appeal Nos. 2449 and 50 of 1992` = 2449-2450?).
* `etc.` / `Etc. Etc.` elisions of connected matters.
* Same number read both as host and in the arising/counsel section (S.P. Gupta).
* Cause-title year differing from the jurisdiction heading (`D. No. 32135 of 2013` vs 2015).
* Matters without a `No.` marker (`SLP (Civil) 27217 of 2010`) are recovered only via the cause-title fallback.

## Limits

* Works from the stored text layer, not a fresh PDF extraction; OCR noise in the SCR renditions (third-party mirror of e-SCR) can garble digits. Letter->digit year repairs are never auto-confirmed.
* The SCR rendition is not the official SC cause title; numbers should be confirmed against the official judgment where one is available before being applied.
* Connected matters printed only in the body (not in the jurisdiction block) are not captured; `etc.` elisions are flagged, not resolved.
* `arising_from` type codes are best-effort abbreviations of the lower-court label.
* Several doc_ids share one source file (same sha256); each is reported separately.
* Curated comparison only covers the few cases_53 entries whose decision date and title match.
* Proposal only: nothing is written to data/meta; legal/editorial review is required before use.
