# C12 Workstream E, part 1: holdings extraction

Extractor `c12-holdings/1.0.0`. It is rule-based and deterministic, uses only the standard library, and runs on Python 3.11 or later.

It finds candidate **questions of law**, **holdings**, **reasoning**, **obiter**, **operative directions**, and, kept apart for audit, **quoted precedent**, **party submissions** and **lower-forum findings**. It works on the Supreme Court and other high-value military-law judgments in the Mimamsa corpus. Every item gives the page, paragraph and character offsets, a verbatim excerpt, and the opinion it comes from.

**Status policy.** Every item has `status = AUTOMATED_CANDIDATE_NOT_VERIFIED` and `verification = NOT_VERIFIED_RATIO_NOT_DETERMINED`.
- No item is ever marked as verified ratio.
- `holding` means "a sentence that looks like a candidate holding". It does not mean "the ratio".
- The tool never infers overruling. Treatment rows are copied unchanged from C11 relations (`TREATMENT_CANDIDATES.csv`), together with their own status (`DOCUMENTARY_CHECK_REQUIRED` / `LEGAL_INTERPRETATION_ADVISER_REVIEW`). The tool adds no relation of its own.

## Command for the blind evaluation

Run from this folder (`.../C12-CONSOLIDATION/holdings/`):

```
python3.11 -I -B tools/holdings_c12.py ids --ids-file <ids.txt> --out-dir <out_dir>
```

- `<ids.txt>`: one `judgment_id` per line, for example `J-14e2d11aa4b88fe0`. `#` comments are allowed. If a line holds a CSV row, its first field is used.
- Scope is **not** applied. Any judgment_id in the C10 copy register is extracted, High Court ones included.
- Output in `<out_dir>`:
  - `HOLDINGS_C12.jsonl`: the items.
  - `HOLDINGS_C12_JUDGMENTS.csv`: one row per requested id, with `text_status` = `TEXT_LAYER_READ`, `NO_TEXT_LAYER_AT_COMMIT` or `UNKNOWN_JUDGMENT_ID`.
  - `RUN_META.json`: the tool hashes and the ids-file hash.
- The text is read from `/home/user/c7` at commit `ad77758d`. Override with `--repo` / `--commit`, placed before `ids`.
- Before the run, confirm that `RUN_META.json` → `tool_sha256` equals the frozen hashes below. You can also run `python3.11 -I -B tools/holdings_c12.py check`.

Suggested scoring against a reference:
- Use `item_type == "holding"` for holding precision and recall.
- Use the court-voice set `{question_of_law, holding, reasoning, obiter_candidate, operative_direction}` for candidate recall.
- `holding_score` and `rank_in_opinion` let you trade precision against recall.
- Compare against `excerpt_clean`, which has SCR margin letters and running headers blanked. `excerpt` is the raw verbatim span.

The tool never opened `holdout_v3/` or `holdings_reference/`, and they were not used in development.

## Frozen state

| | sha256 |
| --- | --- |
| `tools/holdings_core.py` | `6d5b05e447e082cb8d9be4a1784148a18221091bd836b5fceb4cecbf6178fe8e` |
| `tools/holdings_c12.py` | `a1b0163824e4062b38efe1423985559935130f7e581f3c3ba61e29a50fc7bb89` |
| `tools/eval_dev_holdings.py` (dev evaluation only) | `b55088892eb5a7d1bde1222727483be05140d1c18a11b909960a9935e2ed44dd` |
| `outputs/HOLDINGS_C12.jsonl` | `a0c6714fc333dabc56114e9246e4fe91a7e50a2feab283bd19e494c40454168f` |

The full record is in `outputs/FREEZE.json`: version, tool hashes, input hashes, output hashes and thresholds. `OUTPUT_SHA256SUMS` covers the scope outputs and `DEV_SHA256SUMS` covers the dev evaluation files.

## Commands

| Command | What it does |
| --- | --- |
| `python3.11 -I -B tools/holdings_c12.py run` | Extracts the scope set into `outputs/` and writes `OUTPUT_SHA256SUMS` and `FREEZE.json` (about 40 s) |
| `python3.11 -I -B tools/holdings_c12.py check` | Checks the tool and input hashes against `FREEZE.json`, then re-extracts the scope in memory and compares every output byte for byte |
| `python3.11 -I -B tools/holdings_c12.py ids --ids-file F --out-dir D` | Extracts any list of ids (see above) |
| `python3.11 -I -B tools/eval_dev_holdings.py outputs/dev_predictions outputs/DEV_EVALUATION_HOLDINGS.md --rows outputs/DEV_EVALUATION_ROWS.csv` | Runs the in-sample dev evaluation |
| `python3.11 -I -B -m unittest discover -s tests` | Runs 16 tests: synthetic SCR judgment, opinions, attachment, determinism, freeze |

`check` passes under both Python 3.11 and 3.13, with byte-identical outputs.

## Scope (`outputs/SCOPE_C12.csv`, `CURATED_SCOPE_C12.csv`)

- 280 Supreme Court judgments classed `DIRECT_MILITARY_LAW` (193) or `MILITARY_ADMIN_SERVICE_PENSION` (87) in C10 `HF_JUDGMENT_RELEVANCE.csv`.
- Plus the curated cases held in C10 `CURATED_CASE_COPY_STATUS.csv`. Their copies are mapped through `JUDGMENT_RECONCILIATION.csv` group ids to corpus judgment_ids.
  - 25 curated cases fall in scope, and all of them are already among the 280.
  - 4 curated cases have a judgment_id but no text layer at the commit (`NO_TEXT_LAYER_AT_COMMIT`).
  - 4 more are HELD with no corpus judgment_id.
  - 20 are not held. Each has its own disposition in `CURATED_SCOPE_C12.csv`.
- Result: 284 scope rows, 280 with text, **21,642 items**:

| Item type | Count |
| --- | --- |
| question_of_law | 258 |
| holding | 2,325 |
| reasoning | 15,940 |
| obiter_candidate | 155 |
| operative_direction | 496 |
| quoted_precedent | 1,003 |
| submission | 952 |
| lower_court_finding | 513 |

- 2,031 items carry a C11 statute link and 20 carry a C11 treatment row.

## Method (`tools/holdings_core.py`)

1. **Layout mask.** The tool blanks SCR margin letters (A to H), page numbers, `SUPREME COURT REPORTS` and citation headers, repeated running headers and footers, and `[[page N]]` markers. It replaces them with spaces, so offsets do not move. Judge names in SCR running headers (`[X, J.]`) are kept for step 3.
2. **Judgment body.** The headnote and front matter are excluded. The body starts at one of these, in order:
   - the e-SCR banner `Judgment / Order of the Supreme Court`;
   - `The Judgment of the Court was delivered by`;
   - a `JUDGMENT`/`ORDER` heading after the counsel block;
   - the end of the counsel block that follows the `... JURISDICTION` line.

   Reporter tails (`Headnotes prepared by`, `Appeal allowed.`) are cut off. `HOLDINGS_C12_JUDGMENTS.csv` records `body_start_method`, `body_start_page` and `headnote_excluded_chars`.
3. **Opinions.** The tool looks for author lines (`NAME, J.`, `Name J.`, inline SCR `NAME, J.-The ...`) with first-person or concurrence/dissent cues. As a fallback it uses a lasting change of judge name in the SCR running headers; the start of such an opinion is approximate, to within a page.
   - `sole` means one opinion was found.
   - `lead` means the first opinion in the report, **not** necessarily the majority.
   - `separate` means a later opinion.
   - `dissent` means a later opinion with an explicit dissent cue in its first 3,000 characters. Its items carry `opinion_note = NOT_THE_COURT'S_HOLDING_IF_DISSENT`.
4. **Paragraphs.** Numbered paragraphs (`12.`, `12`, `12)`, `(12)`) are detected under a sequence constraint, and numbering restarts in each opinion. Unnumbered text gets `paragraph = null`.
5. **Quotations.** The tool detects paired curly or straight quotes (150 characters or more), unclosed block quotes, and blocks that follow an introduction ending in a colon ("observed as under:"). An unreliable span is cut at the first own-voice pivot line ("We are of the view", "In the present case", ...). The cue closest to the opening sets the kind of quotation: precedent, statute or document, lower forum, or submission.
6. **Sentence voice.** Each sentence is classed as one of:
   - quotation (by kind);
   - `precedent_report` ("In X v. Y, this Court held ...");
   - `submission`. Counsel cues are carried through a paragraph until the court pivots. Sentences that accept or reject a contention count as the court's;
   - `lower_court` (Tribunal or High Court held ..., without the court's own assessment);
   - `court`.
7. **Questions of law** (court voice). Framing patterns are required together with `whether` / `as to` / `?` / a list colon, or `Whether ...` list items in an issues zone. Questions about other cases are excluded. `legal_issue` holds the question text.
8. **Holdings and reasoning** (court voice). Scores are additive (`WEIGHTS`):
   - conclusion markers ("we hold", "in our view", "it cannot be said");
   - accepting or rejecting a contention;
   - a statement of law;
   - application to the facts;
   - a normative legal predicate;
   - a legal concept;
   - lateness in the opinion;
   - a lexical link to an earlier question of law;
   - penalties for facts, procedure, quotation introductions and length.

   A sentence becomes a candidate if it scores at least 4 and has a core signal. In each opinion the top candidates become `holding`, at most `clamp(round(0.06 × court-voice sentences), 4, 25)`. The rest, and other legal court-voice sentences scoring at least 1 or 2, become `reasoning`. Obiter cues ("before parting", "we may add", "we leave open", "need not decide", "we recommend") give `obiter_candidate`. Disposal and direction wording late in an opinion gives `operative_direction`. A holding is linked to an earlier question in the same opinion (Jaccard ≥ 0.15) through `answers_question`, and `legal_issue` then holds that question.
9. **Statutes.**
   - `statutes`: references normalised from the sentence itself (`AA-1950` `s.120`, `COI` `art.142`, ...), each with the basis for resolving the instrument.
   - `statute_links`: C11 `STATUTE_JUDGMENT_LINKS.csv` rows where the same provision is in the sentence and the link lists the page, or where the cue page matches and the text overlaps. The link's relationship and status are copied as-is.
10. **Treatment.** C11 `TREATMENT_CANDIDATES.csv` rows that carry a proposed relation or an adviser or documentary status are attached when the cue page matches and the text overlaps. They are copied unchanged, with `policy: carried unchanged ...; no overruling inferred`.

## Item fields (`HOLDINGS_C12.jsonl`)

- **Identity:** `item_id`, `judgment_id`, `sha256` (judgment PDF), `doc_id`, `court`.
- **Classification:** `item_type`, `voice`, `section_heading`.
- **Opinion:** `opinion` (lead/sole/separate/dissent), `opinion_author`, `opinion_index`, `opinion_method`, `opinion_note`.
- **Location:** `page`, `page_end`, `paragraph`, `char_start`, `char_end`.
- **Text:** `excerpt` (verbatim, whitespace squashed, 900-character cap) and `excerpt_clean`.
- **Scoring:** `holding_score`, `rank_in_opinion`, `signals`.
- **Issue:** `legal_issue`, `legal_issue_keywords`, `answers_question`.
- **Links:** `statutes`, `statute_links`, `treatment`.
- **Status:** `status`, `verification`, `extractor`.

## Dev evaluation (in-sample; `outputs/DEV_EVALUATION_HOLDINGS.md`)

The dev data are the C11 holdout ground-truth holdings (134 excerpted holdings in 52 judgments) and the C10 review_A/B principal issue and answer. All of it was read during development, so every figure below is in-sample. The matcher is the C11 review's rule: same page within one, and at least 40 common normalised characters.

| Recall | All dev (134) | Supreme Court (60) | C12 scope (51) |
| --- | --- | --- | --- |
| `holding` | 44.8% | 43.3% | 49.0% |
| Court-voice set | 85.8% | 83.3% | 90.2% |
| C11 baseline, court-labelled candidates | 9.7% | 6.7% | 5.9% |
| C11 baseline, any candidate | 37.3% | 23.3% | 25.5% |

Precision:
- **Against ground truth:** the lower bound for `holding` against the at most three ground-truth holdings per judgment is 18.4%. This is a lower bound only.
- **Hand check:** the developing agent hand-checked samples (an AI, not independent):
  - holdings: 25/40 = 62.5% on scope judgments outside dev, and 28/40 = 70% on dev;
  - own-voice errors in about 10% of sampled holdings;
  - questions of law: 13/20 before the final exclusion rules;
  - obiter candidates: 11/15.
- **C10 reviews:** a holding is emitted on a reviewer-pinpointed page in 26/30 reviewed judgments.

## Known limitations

- Rules are tuned in-sample. The blind reference is the first real test, and precision of `holding` is about 60 to 70% at best.
- `reasoning` is a broad bucket (about 57 items per scope judgment). It is meant for recall, not for direct use.
- Opinion detection is incomplete in large multi-opinion benches; for example, some opinions in Bommai, Supriyo and NJAC are missed or have approximate starts. `lead` is not "majority", and `dissent` relies on textual cues only.
- OCR-damaged old SCR text (broken words, inline margin letters) lowers sentence and quotation detection. Garbled font layers yield nothing useful.
- Quotation boundaries are heuristic. Some quoted passages with no closing mark leak into court voice, and the reverse also happens.
- Statute links cover only C11-linked instruments. A link's `relationship` describes the C11 cue mention, not necessarily this sentence.
- Batch texts shared by several judgment_ids are extracted per id. Shared blobs are listed in `shared_text_judgment_ids`.

## Files

- `tools/holdings_core.py`, `tools/holdings_c12.py`: the extractor (frozen).
- `tools/eval_dev_holdings.py`: the dev evaluator. It reads the dev ground truth and is never called by the extractor.
- `outputs/HOLDINGS_C12.jsonl`, `HOLDINGS_C12_JUDGMENTS.csv`, `SCOPE_C12.csv`, `CURATED_SCOPE_C12.csv`, `OUTPUT_SHA256SUMS`, `FREEZE.json`.
- `outputs/dev_predictions/`: `ids` output on the dev ids (`DEV_IDS.txt`).
- `outputs/DEV_EVALUATION_HOLDINGS.md`, `DEV_EVALUATION_ROWS.csv`, `PRECISION_HANDCHECK_C12.csv`, `DEV_SHA256SUMS`.
- `tests/test_holdings_c12.py`.
