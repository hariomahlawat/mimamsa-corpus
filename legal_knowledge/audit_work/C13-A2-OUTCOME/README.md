# C13 workstream A2: judicial outcome extractor V4 (`c13-extract-v4/1.0.0`)

**Status: FREEZE CANDIDATE, NOT FROZEN. AUTOMATED_CANDIDATE_NOT_VERIFIED.** Every value is read by a deterministic
program from the PDF text layer. Nothing is legally verified. The capability stays NON_OPERATIONAL_RESEARCH_ONLY
(C12 `CAPABILITY_RESTRICTIONS.csv`) until an independent evaluation on the fresh holdout H-OUT-C13 meets strict
precision of at least 95% and coverage of at least 85% per field, plus legal-adviser sign-off.

V2 (`C11-JUDICIAL-QUALITY/extraction`) and V3 (`C12-CONSOLIDATION/extractor_v3`) are frozen comparators. V4 does not
import, modify or re-run them; their committed outputs are read only (a test checks the V3 tool hashes against
`FREEZE_V3.json` and the V2 output against its checksum file).

## Commands (Python 3.11+, standard library only; checked under 3.11 and 3.13)

| Command | What it does |
| --- | --- |
| `python3.11 -I -B tools/extract_v4.py ids --ids-file <IDS> --out <DIR>` | **Blind evaluation mode.** Writes `<DIR>/OUTCOMES_V4.csv` and `RUN_INFO.json` (tool hashes, repo head). Ignores `--exclude-ids`. |
| `python3.11 -I -B tools/extract_v4.py --exclude-ids EXCLUDE_IDS_H-OUT-C13.txt run` | Full corpus: the 3,936 PROCESSED judgments of the C10 register, text layer at c7 `ad77758d`, 20 resumable batches. Excluded judgments get one `EXCLUDED_BY_EXCLUDE_IDS` row. About 4 to 5 minutes. |
| `python3.11 -I -B tools/extract_v4.py --exclude-ids EXCLUDE_IDS_H-OUT-C13.txt --check` | Deterministic self-check: batch input keys (tool fingerprint, commit, inputs, exclusion list), assembled CSV, checksums, byte-identical re-extraction of batches 0 and 19, vocabularies, abstention rules, and an anchor on every answered row. |
| `python3.11 -I -B tools/eval_dev_v4.py [--write] [--errors tune\|late\|all] --exclude-ids EXCLUDE_IDS_H-OUT-C13.txt` | In-sample evaluation on the spent sets with V3/V2 comparison (`dev_eval/`). |
| `python3.11 -I -B tools/corpus_stats_v4.py` | Output-count comparison V4 vs V3 on the full corpus (`outputs/CORPUS_COMPARISON_V4_V3.*`). |
| `python3.11 -I -B tools/freeze_v4.py --confirmation <ref> --exclude-ids <list>` | Writes `outputs/FREEZE_V4.json`. **Not run.** Run only after the coordinator confirms A0's protocol. |
| `python -m pytest tests/test_legal_audit_c13_outcome_v4.py` | 22 fast tests (about 0.2 s), synthetic texts only. |

`EXCLUDE_IDS_H-OUT-C13.txt`: 331 judgment ids (325 PROCESSED) built only from the `judgment_key` and `rep_sha256`
identifier columns of A0's `SAMPLE.csv` (branch `claude/c13-a0-eval`, `5e07e010`), expanded to every stored copy with the
same judgment key, sha256 or text sha256 in the C11 identity register. No holdout text was opened. **Overlap with the
development material: none** (0 of 286 development judgments).

## Architecture

| Layer | Module | What is new in V4 |
| --- | --- | --- |
| Text layer | `v4_text.py` | Ported from V3 (offset-preserving masking, page index, sentences). |
| Structural segmentation | `v4_segment.py`, `v4core.py` | Signature segments and composite files (V3) plus **opinion boundaries** at author lines followed by a restarted paragraph 1; each opinion gets a **role** (main, concurring, dissent). A dissent never supplies the disposition when another opinion or order disposes; if only a dissent does, abstain. S.C.R. headnote and editorial tail stay excluded. Each row records its `segment` (opinion n of m, role, pages). |
| Operative section | `v4core.py` | Zone starts at the **paragraph or sentence holding the cue** (V3 cut mid-sentence at a line start); when there is no cue and no numbered last paragraph, the **closing passage** is used only if it holds a present-tense, court-voice disposition of a main proceeding. |
| Quoted vs operative language (C11 F08) | `v4_quotes.py` | An "as under:" block ends where the quotation it introduces closes, or where the court resumes after a closing mark; a marked quotation that swallows the court's next numbered paragraph (numbering continuing the court's own) is cut there; doubled single quotes are paired; `voice_at()` exposes court vs quoted. |
| Clause parsing | `v4_clauses.py` | V3 parser plus coordinated subjects ("the writ petition and the civil appeal are dismissed"), elliptical dispositions ("All the petitions dismissed."), bunch/lead-case references not taken as subjects. |
| Proceeding map | `v4_proceedings.py`, `v4_decide.py` | Abbreviated ranges ("8452-53" = 8452, 8453), "And" in number lists, Transfer Case type, lead case of a bunch decided elsewhere is not a host, a numbered writ petition in an appeal is the proceeding below, "all the petitions" covers a mixed group. Per-proceeding dispositions, batch sections and generic-to-host expansion as in V3. |
| Relief analysis (C11 F05) | `v4_relief.py` | **Extent phrases are resolved from the operative directions**: limiting words, or a refused/limited relief in the operative part, give `partly_allowed`; a referential phrase ("to the extent and in terms herein above") whose directions quash the impugned decisions with nothing refused gives `allowed`; otherwise abstain. **Transfer** to the Tribunal (record or paper book transmitted, transfer prayer "ordered accordingly") gives `transferred`/`no_adjudication`, also when the order then says "disposed of". An allowance "in the aforesaid terms" whose terms are a fresh decision gives `remanded_for_fresh_decision`. |
| Party-specific outcomes | `v4_decide.py` | One proceeding with relief granted to some parties and refused to others gives `partly_allowed` with the per-party outcomes in `party_specific`; across several proceedings without a case-number mapping V4 still abstains. |
| Interim vs final, remand, procedural | V3 rules kept (listing/adjournment cues, `not_final`, remand/set-aside signals, withdrawal, infructuous, default). |
| Multiple operative directions | `v4_relief.direction_kinds` | Each answered row lists the court-voice directions in its operative part (`operative_directions`: set_aside, remand, transfer, direction, relief, modification, withdrawal, liberty, listing, interim_relief, costs). "Liberty" alone no longer makes a disposal `disposed_of_with_directions`; a direction needs a party or authority subject. |
| Calibrated abstention | all | Explicit abstention reasons per field; `confidence` tier (high/medium/low) per answered row. **The tiers are not calibrated**: in-sample, all 6 remaining errors are in the high tier (see dev_eval). No local classifier was trained: with 6 in-sample errors there is nothing to fit, and none was used. No external service was used. |

Every answered row carries `page`, `paragraph` (when printed), `char_start`, `char_end` (offsets into the text blob named
in `text_source`) and `excerpt`; `--check` fails if any answered row lacks them. In-sample, 408 of 408 answered excerpts
were found at their offsets and 405 had the page of the preceding page marker.

## Development results (IN-SAMPLE; see `dev_eval/DEV_EVALUATION_V4.md`)

| Set | Field | V4 precision | V4 coverage | V3 precision | V3 coverage |
| --- | --- | --- | --- | --- | --- |
| C12 V3 holdout (spent), all 150 judgments | printed | 165/169 = 97.6% | 169/213 = 79.3% | 126/138 = 91.3% | 64.8% |
| | substantive | 139/141 = 98.6% | 141/207 = 68.1% | 108/113 = 95.6% | 54.6% |
| C12 LATE third (set aside, scored once at the end) | printed | 40/41 = 97.6% | 41/61 = 67.2% | 35/40 = 87.5% | 65.6% |
| | substantive | 36/36 = 100% | 36/61 = 59.0% | 31/31 = 100% | 50.8% |
| All spent sets (C12H + C10/C11 dev gold) | printed | 348/352 = 98.9% | 352/416 = 84.6% | 307/319 = 96.2% | 76.7% |
| | substantive | 314/316 = 99.4% | 316/405 = 78.0% | 281/286 = 98.2% | 70.6% |

The LATE third is the most honest of these figures: its coverage gain over V3 is small (+1.6 points printed,
+8.2 substantive), while the TUNE gain (+19.7 points printed) partly comes from fixes that unlock whole multi-proceeding
judgments (one judgment has 17 rows). **Expect blind coverage well below 85%**, and blind precision below the in-sample
figures.

## Known limits

- `disposed_of` vs `disposed_of_with_directions`, and `allowed` vs `set_aside_and_remanded`, remain convention-sensitive.
- `substantive_result` for "disposed of with directions" abstains unless withdrawal, transfer, set-aside, remand or
  in-terms relief is explicit; this is the main substantive coverage gap.
- OCR-garbled text layers abstain (PH 2025 font-encoded pages, old S.C.R. scans).
- Party-specific outcomes across several proceedings are not mapped to case numbers.
- F08: corpus `ONLY_QUOTED_DISPOSITION_LANGUAGE_FOUND` abstentions fell from 51 to 45 (excluded judgments dropped from
  both). The C11 request to review those rows by hand was not done: the rows were not restricted to the spent sets, and
  reading them could have exposed H-OUT-C13 texts (the holdout was drawn later).
- Inputs are the same 3,936 judgments as V3 (c7 `ad77758d`); judgments recovered later in C12 are not in that text layer.
