# C11: structured outcome and legal-proposition extraction (extractor `c11-extract-v2/1.0.0`)

Everything in this folder is an **automated candidate** (`AUTOMATED_CANDIDATE_NOT_VERIFIED`). Nothing here is legally verified. No proposition is labelled a holding or ratio. An outcome may be promoted automatically only if it passes the coordinator's holdout precision bar (at least 95% on non-abstained rows). The dev figures below do not count toward that bar.

## Inputs (read-only)
- Text layer: `git -C /home/user/c7 show ad77758d:data/text/<doc_id>.txt`. It has `[[page N]]` markers and is read through one `git cat-file --batch` process. Each row records its blob id in `text_source`.
- Judgment list: `C10-HF-JUDGMENTS/outputs/HF_JUDGMENT_COPY_REGISTER.csv`, `disposition = PROCESSED` (3,936 judgments).
- Metadata: `C10-HF-JUDGMENTS/outputs/HF_JUDGMENT_METADATA_AUDIT.csv`, used for doc_ids, crawler `outcome_meta`, the old extractor's `outcome_text_candidate`, and metadata case numbers.
- The PDFs are not read, so PyMuPDF is not needed. Python 3.11+ and the standard library only.
- 4 PROCESSED shas have no text file at the commit. They are reported as `OUTCOME_UNVERIFIED` / `NO_TEXT_FILE_FOR_THIS_SHA_AT_COMMIT`.

## Files
| File | Content |
| --- | --- |
| `OUTCOMES_V2.csv` | One row per judgment × proceeding. Columns: `judgment_id, sha256, doc_ids, court, proceeding, outcome, page, paragraph, char_start, char_end` (offsets into the text file), `excerpt` (verbatim, whitespace squashed), `method, abstain_reason, flags, crawler_outcome, old_candidate, agree_crawler, agree_old, text_source, extractor, status` |
| `PROPOSITIONS_V2.jsonl` | Candidate sentences, at most 25 per judgment. Fields: `origin` (COURT_HOLDING_CANDIDATE, COURT_REASONING_CANDIDATE, QUOTED_PRECEDENT, PARTY_SUBMISSION, LOWER_COURT_FINDING, EDITORIAL_HEADNOTE, STATUTORY_QUOTATION, OTHER_OR_UNCERTAIN), `attributed_to` (for example the cited case name for a quotation), `legal_issue_keywords`, `statutory_references`, `relation_to_operative_decision`, `page, paragraph, char_start, char_end, sha256, doc_id, excerpt, verification = NOT_VERIFIED_NOT_A_HOLDING, status` |
| `CRAWLER_DISAGREEMENT_ANALYSIS.csv` | The 549 metadata records where the crawler outcome and the old text candidate disagreed. Both readings are kept verbatim, with the v2 reading and `v2_supports` (CRAWLER / OLD_EXTRACTOR / BOTH / NEITHER / V2_ABSTAINED / V2_MIXED_PER_PROCEEDING / V2_NOT_FINAL). Nothing is overwritten. |
| `DEV_EVALUATION.md`, `DEV_EVALUATION_ROWS.csv` | Precision and coverage on the 50 Cycle 10 reviewed judgments, which were also the tuning set |
| `batches/v2_batch_NNNN.json.gz` | Resumable per-batch results, 200 judgments each, with an input key |
| `OUTPUT_SHA256SUMS` | Checksums for the outputs, batches and tool sources |

## Outcome vocabulary and rules
`allowed, partly_allowed, dismissed, dismissed_as_withdrawn, dismissed_as_infructuous, disposed_of_with_directions, remanded, set_aside_and_remanded, transferred, not_final, OUTCOME_UNVERIFIED`.

Zones:
1. Boilerplate lines are masked, keeping the same length so offsets stay valid.
2. Signature blocks split the file into segments.
   - Author lines (`NAME, J.` followed by paragraph 1) are not signatures.
   - A page that opens with a court header and a cause title starts a new document. A foreign case is ignored (`COMPOSITE_FILE_FOREIGN_DOCUMENT_IGNORED_FROM_Pn`). A same-case successor (corrected copy or later order) must agree with the earlier one, or the extractor abstains.
3. S.C.R. editorial headnote: everything before `The Judgment of the Court was delivered by` / `JUDGMENT`. The reporter's tail note (`Appeal dismissed.`, `Result of the case:`) is also editorial and is never used.
4. Quoted blocks:
   - quotation marks: curly quotes, and straight quotes paired by direction;
   - unmarked blocks after `held as under:` and similar, up to the next paragraph number;
   - a sentence that ends in a closing quote.
5. Operative part:
   - starts at the earliest operative cue in the last 3,500 to 9,000 characters of the segment body, or at the last ORDER heading;
   - is extended back over adjacent paragraphs that themselves contain dispositions;
   - for short orders (under 4,000 non-space characters) it is the whole body;
   - when there is no cue, a final paragraph that ends just before the signature is used (`final_paragraph_no_cue`).

Disposition clauses:
- Verb form: passive with an auxiliary, active `we allow/dismiss/dispose of`, `deems it proper to transfer`, intransitive `succeeds/fails`, or a standalone `Dismissed.`.
- Tense:
  - past recitals (`was/has been/stood dismissed`) are excluded;
  - conditional or modal forms (`if…`, `would`, `may`) are excluded;
  - `deserves to be` and subjunctive `be transferred` are used only when no plain disposition exists;
  - counsel's statements (`counsel submits that the petition may be disposed of`) count only when followed by `Ordered accordingly`.
- Subject, taken as the first noun class in the clause, after any introductory phrase ending in a comma:
  - main proceeding;
  - miscellaneous application (excluded, which covers 'pending applications stand disposed of');
  - lower-forum proceeding such as an OA or court martial (excluded); this includes 'the writ petition filed by the respondent' in an appeal;
  - impugned decision (set-aside signal only);
  - pronoun or elided subject (inherits a Delhi-style case-number heading, so `CM APPL … (exemption) 1. Allowed` is excluded).
- Proceeding mapping:
  - case numbers in the subject, matched to host numbers (metadata plus cause title);
  - party descriptors (`filed by the Union of India`);
  - block headings in common orders (a case-number line followed by paragraph 1).

Abstain (`OUTCOME_UNVERIFIED` with `abstain_reason`) when:
- there is no operative cue in the final part;
- dispositions conflict without a proceeding mapping;
- only misc-application, quoted, lower-forum or past/conditional disposition language is found;
- the text in the operative part is garbled;
- separate opinions or successive orders give differing dispositions;
- the last segment is unresolved after an earlier disposition;
- an interim order follows a final one;
- the allowance is extent-qualified ('allowed to the extent indicated', which is ambiguous between allowed and partly_allowed), or a dismissal carries an exception ('dismissed except to the extent …');
- the disposition clause contains an exception or carve-out (`DISPOSITION_WITH_EXCEPTION_OR_CARVE_OUT`, for example 'all the appeals except the appeal filed by X are dismissed');
- there is no text file.

Mapping choices to note:
- 'disposed of as not pressed' maps to `dismissed_as_withdrawn`.
- A set-aside of the impugned decision without an explicit disposal maps to `allowed` (`method` contains `inferred_from_set_aside_of_impugned_decision`).
- `remanded` with a set-aside maps to `set_aside_and_remanded`, but an explicit 'appeal allowed … remitted' stays `allowed`.

Agreement flags compare outcome families:
- crawler: allowed / partly_allowed / dismissed / disposed;
- old extractor labels: as listed.

## Commands (run from this `extraction/` folder)
```
python3.11 tools/extract_v2.py run          # all PROCESSED judgments, resumable (up-to-date batches are skipped)
python3.11 tools/extract_v2.py check        # batch keys, assembled outputs vs batches, OUTPUT_SHA256SUMS, byte-identical re-extraction of 2 batches
python3.11 tools/extract_v2.py ids --ids-file <file with one judgment_id per line (or CSV whose first column is judgment_id)> --out <dir>
python3.11 tools/extract_v2.py ids --ids J-aaaa,J-bbbb --out <dir>
python3.11 tools/eval_dev.py -v             # dev-set evaluation (writes DEV_EVALUATION_ROWS.csv)
python3.11 -m unittest discover -s tests -v # synthetic tests (+1 integration test, skipped if /home/user/c7 is absent)
```
`ids` writes `OUTCOMES_V2.csv` and `PROPOSITIONS_V2.jsonl` for exactly those ids into `<dir>` and does not touch `outputs/`. An unknown id gets an `UNKNOWN_JUDGMENT_ID` abstain row. `--repo` and `--commit` override the text source; the defaults are `/home/user/c7` and `ad77758d`.

## Known limits
- The operative-part window can miss a disposal that is followed by long obiter material (for example a P&H judgment with a 7,000-character postscript). The result is an abstention, not a wrong answer.
- Participial dispositions ('allowing the appeals preferred by the Union …, we remit …') are not parsed. Such mixed judgments abstain.
- OCR noise in old S.C.R. scans can hide a disposition, which also produces an abstention.
- Host case-number labels in `proceeding` are raw strings read from the cause title and can carry stray words.
- Proposition origin labels are cue-based. An unquoted paraphrase of a precedent, or a court sentence beginning 'It is clear that' inside a long recital, can be mislabelled. Treat every proposition as a lead, to be read in its host paragraph.

## Corpus run summary (frozen `c11-extract-v2/1.0.0`)
- **Scope:** 3,936 PROCESSED judgments, giving 3,948 outcome rows (12 judgments have per-proceeding rows) and 51,250 proposition candidates.
- **Non-abstained judgments:** 3,309 (84%). By court:

| Court | Coverage |
| --- | --- |
| Supreme Court | 75% |
| Delhi | 88% |
| Punjab and Haryana | 84% |
| Jammu and Kashmir | 83% |
| Allahabad | 78% |

- **Outcome rows by label:**

| Outcome | Rows |
| --- | --- |
| dismissed | 1,776 |
| disposed_of_with_directions | 717 |
| allowed | 424 |
| transferred | 157 |
| dismissed_as_withdrawn | 152 |
| partly_allowed | 57 |
| not_final | 15 |
| set_aside_and_remanded | 10 |
| remanded | 9 |
| dismissed_as_infructuous | 4 |
| OUTCOME_UNVERIFIED | 627 |

- **The 549 crawler-versus-old-extractor disagreements:**

| v2 reading | Records |
| --- | --- |
| supports the crawler | 329 |
| supports the old extractor | 113 |
| abstains | 89 |
| supports neither | 11 |
| mixed per proceeding | 4 |
| compatible with both | 3 |

- **Proposition origins:**

| Origin | Candidates |
| --- | --- |
| OTHER_OR_UNCERTAIN | 28,317 |
| QUOTED_PRECEDENT | 4,255 |
| PARTY_SUBMISSION | 4,192 |
| STATUTORY_QUOTATION | 3,708 |
| COURT_REASONING_CANDIDATE | 3,574 |
| COURT_HOLDING_CANDIDATE | 2,750 |
| LOWER_COURT_FINDING | 2,421 |
| EDITORIAL_HEADNOTE | 2,033 |

- **Composite files:** 5 files carry a foreign document, which was ignored. 6 carry a same-case successive document.
