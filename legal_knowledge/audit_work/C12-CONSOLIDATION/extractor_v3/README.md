# C12 Workstream D: judicial outcome extractor v3 (`c12-extract-v3/1.0.0`)

**Status: FROZEN, AUTOMATED_CANDIDATE_NOT_VERIFIED.** Every value is read by a deterministic program from the PDF text
layer. Nothing is legally verified. Not for unreviewed use until a blind evaluation clears the bar
(strict precision of at least 95% at coverage of at least 85%).

| Frozen file | SHA-256 |
| --- | --- |
| `tools/v3core.py` | `9b457624851ebe0cc91a964bba25392212777d536cee013a83074314c0e73067` |
| `tools/extract_v3.py` | `b399a0928ada0ddb83adf921d31496b10377d2873802042010feaa6e01900ae7` |

These hashes are also in `outputs/FREEZE_V3.json` and `outputs/OUTPUT_SHA256SUMS`. The blind set
`C12-CONSOLIDATION/holdout_v3/` was never opened, and no tool or test refers to it (a unit test checks this).

## Blind evaluation command

```
cd .../C12-CONSOLIDATION/extractor_v3
python3.11 -I -B tools/extract_v3.py ids --ids-file <IDS.csv> --out <OUTDIR>
```

- `<IDS.csv>` may be a CSV with a `judgment_id` column (any position), a headerless CSV whose first column is the
  judgment_id, or a plain list with one id per line. `#` lines are ignored.
- The command writes `<OUTDIR>/OUTCOMES_V3.csv` and `<OUTDIR>/RUN_INFO.json`, which records the tool hashes and commit.
- An unknown id gets one row with `abstain_reason` `UNKNOWN_JUDGMENT_ID`.

## Other commands

| Command | What it does |
| --- | --- |
| `python3.11 -I -B tools/extract_v3.py run` | Processes all 3,936 PROCESSED judgments in 20 resumable batches (`outputs/batches/`). A batch is skipped when its input key matches: tool hash, commit and inputs. Then writes `outputs/OUTCOMES_V3.csv` and `OUTPUT_SHA256SUMS`. Takes about 75 s. |
| `python3.11 -I -B tools/extract_v3.py check` | Checks batch keys, the assembled CSV and the checksums. Re-extracts batches 0 and 19 and confirms they are byte-identical. Validates vocabularies and abstention rules. Passes under Python 3.11 and 3.13. |
| `python3.11 -I -B tools/eval_dev_v3.py [--write] [-v]` | Scores v3 and the frozen v2 on the development gold. **This is in-sample.** |
| `python3.11 -I -B tools/build_dev_gold_v3.py` | Rebuilds `tools/dev_gold_v3.json` from the C10/C11 reviewer files. |
| `python3.11 -I -B -m unittest discover -s tests -v` | Runs 36 tests. The real-text tests are skipped, with the reason, if the c7 repository is missing. |

The tools use the standard library only. Paths are resolved relative to this folder.

**Inputs (all read-only):**
- the c7 text layer as git objects at commit `ad77758d` (`data/text/<doc_id>.txt`, with `[[page N]]` markers);
- `C10-HF-JUDGMENTS/outputs/HF_JUDGMENT_COPY_REGISTER.csv` and `HF_JUDGMENT_METADATA_AUDIT.csv`, for doc_ids, court and the crawler's case number (`case_numbers_meta`).

## Output: one row per proceeding

| Column | Meaning |
| --- | --- |
| `judgment_id`, `sha256`, `doc_ids`, `court` | The stored copy (one PDF). A batch judgment stored as many PDFs appears once per copy. |
| `proceeding` | Normalised host case number, `TYPE NUM/YEAR`, for example `WP(C) 1319/2024`, `CA 7805/1997`, `CWP 24683/2025` or `WRIT-A 4492/2023`. `UNIDENTIFIED` means no host number was found. |
| `file_case_role` | `OWN_CASE` means this row is the copy's own case number from the crawler metadata. `CONNECTED_CASE` means another proceeding decided by the same judgment. `UNKNOWN_NO_METADATA_CASE_NUMBER` means the metadata has no case number (mostly Supreme Court). **For a batch copy, use the `OWN_CASE` row.** |
| `printed_disposal` | The court's literal disposal for this proceeding: `allowed`, `partly_allowed`, `dismissed`, `dismissed_as_withdrawn`, `dismissed_as_infructuous`, `dismissed_in_default`, `disposed_of`, `disposed_of_with_directions`, `remanded`, `set_aside_and_remanded`, `transferred`, `not_final`, or `OUTCOME_UNVERIFIED`. |
| `substantive_result` | What the disposal means for the relief sought: `relief_granted`, `relief_partly_granted`, `relief_refused`, `no_adjudication` (withdrawn, infructuous, default, transferred, relegated), `remanded_for_fresh_decision`, `interim_only`, or `OUTCOME_UNVERIFIED`. |
| `party_specific` | Party-limited wording, for example `in regard to respondents 2 and 3 ...` or `disposition stated for proceedings by/of assessees`. |
| `final_or_interim` | `final`, `interim` (not_final), or empty when both fields abstain. |
| `page`, `paragraph`, `char_start`, `char_end`, `excerpt` | Pinpoint of the evidence sentence. Offsets index the text file. The excerpt is that span with whitespace squashed, capped at 450 characters, and may carry a page header or signature stamp. |
| `abstain_reason` | Why a field is `OUTCOME_UNVERIFIED`. A prefix of `printed:` or `substantive:` marks a single-field abstention. |
| `notes` | Remarks on non-abstained values, for example `EXTENT_QUALIFIED_ALLOWANCE_READ_AS_PARTLY_ALLOWED`. |
| `method`, `flags` | How the operative part was found (`operative_cue`, `batch_section@p114`, ...), and document flags (`HOSTS_45`, `BATCH_SECTIONS_45`, `SCR_RENDITION`, `BATCH_SECTIONS_REJECTED_...`). |
| `crawler_outcome`, `text_source`, `extractor`, `status` | The crawler's label for reference only, the git blob read, the version, and `AUTOMATED_CANDIDATE_NOT_VERIFIED`. |

## What changed from v2 (structural, not phrase lists)

1. **Two-field outcome.** `printed_disposal` keeps the literal words. `substantive_result` is read from the operative part:
   - set-aside signals (present tense, court's own voice);
   - remand or "fresh decision" wording;
   - withdrawal or relegation;
   - "in terms of the judgment ... same relief".

   Example: "disposed of in above terms" after a dismissal is set aside gives `disposed_of_with_directions` / `relief_granted`. Example: "remanded ... the writ petition is allowed" gives `allowed` / `remanded_for_fresh_decision`.
2. **Host proceedings.** These come from the cause title and metadata. Numbers introduced by any of these are not hosts:
   - "arising out of", "against", "impugned", "in O.A./Writ-A/CWP ...";
   - "From the Judgment ... in C.W.P. No." with no `WITH` before the number;
   - "in the case of", "decided on", "passed by".

   Ranges and lists are expanded, and an untyped list inherits its type ("WP(C) Nos. 233, ... of 2024 and 540 of 2025"). Labels are normalised.
3. **Batch splitting.** Heading lines that consist of a host case number ("25. WP(C) No.1319/2024") split a batch into per-proceeding sections. Each section is analysed on its own. Safety rules:
   - A gap in the printed serials marks the section before the gap unsafe, and it abstains.
   - Sections are used only if at least half are decided and the last section's disposition is not a plural common order.
   - Otherwise the judgment is read as one common order.
4. **Per-proceeding mapping.**
   - Numbered dispositions map to their hosts.
   - One sentence naming several hosts maps to each of them.
   - A plural generic disposition ("the present appeals") expands to hosts of the matching type, so special leave petitions are excluded when appeals are named.
   - A listing direction that names a case applies to that case only.
   - A **singular** generic disposition in a multi-proceeding judgment abstains (`SINGULAR_DISPOSITION_IN_MULTI_PROCEEDING_JUDGMENT`).
   - Numbers cited as a reason ("in view of our order in Criminal Appeal No. 242 of 2012, this appeal ...") are not subjects.
5. **Clause fixes.**
   - "partly succeeds", "allowed to the (above|aforesaid|limited) extent" and "to that extent" give `partly_allowed`, with a note.
   - "disposed of as allowed" gives `allowed`; "consigned to records" gives `disposed_of`; "transmitted to the AFT" gives `transferred`.
   - Coordinated active verbs are parsed ("we uphold ... and dismiss this petition").
   - The object of an active verb stops at the first comma or "and", so "allow the appeal, set aside ... and dismiss the writ petition filed by the respondent" gives `allowed`.
   - Operative "will stand dismissed" counts as an order.
   - "The petition and all pending applications are disposed of" is read as the petition, not the applications.
   - A party's prayer ("prays that ... be set aside") is not a set-aside signal.
6. **Quote boundary.** A closing quotation mark quotes only the text before it. Sentences split after a closing quote. An unmarked "held as under:" block ends where the court resumes ("Accordingly", "For the foregoing reasons", ...) after a paragraph break. Text layers that encode quotes as `<...=` are paired.
7. **Text hygiene.** Masked without moving offsets:
   - running page headers, only where they open a page;
   - the name and date lines after digital-signature stamps.

   Initials ("B.D. Khunte") do not end a sentence.
8. **Batch copies.** Every copy keeps all proceeding rows. Its own case number is marked `OWN_CASE`. If the own case cannot be mapped, there is an explicit `OWN_CASE_NUMBER_NOT_MAPPED_TO_A_PROCEEDING` row, never a borrowed outcome.

## Known limits (read before use)

- **In-sample numbers only.** Development precision is 100% because every development judgment was used to write the rules. Developer spot checks outside the development set are small and are not independent. Expect lower blind precision; see `outputs/DEV_EVALUATION_V3.md`.
- **`substantive_result` is a reading, not a fact.** It abstains often (about 71% judgment coverage corpus-wide against 85% for `printed_disposal`), especially for "disposed of with directions". Remand versus relief granted is the main borderline.
- **Conventions a blind coder may not share:**
  - `disposed_of` versus `disposed_of_with_directions`: a directive in the operative part gives the latter;
  - "allowed to the extent indicated" read as `partly_allowed`;
  - "disposed of as not pressed" read as `dismissed_as_withdrawn`.
- **Party-specific dispositions are not mapped to case numbers.** An example is "the appeals of the Union stand allowed ...; Raj Kumar's appeal is sans merit". Such judgments abstain, or keep only the literal closing words (C11 H010 gives `disposed_of` for all three appeals).
- **Host detection is heuristic.** Supreme Court judgments with no case number in the metadata depend on the S.C.R. case head and the jurisdiction line. OCR noise can hide a host or add one.
- **OCR-garbled text layers abstain.** Examples are pages with font-encoded glyphs and S.C.R. scans where the operative cue is unreadable.
- **No propositions.** v3 extracts outcomes only. The C11 propositions remain v2 output.
