# WS-B Judicial Precedents: judgment intake, identity, holdings and treatment (issue #12, programme #10)

**DATABASE ONLY. RESEARCH PROPOSALS ONLY.**
- No holding, treatment or link in this directory has been adjudicated by the legal advisor or validated by JAG.
- The originals (`cases_53.jsonl` sha `8b8d53cd…`, `records_658.jsonl` sha `9a8f0d19…`) and the intern corpus were read only.

## Inputs
- **Intern intake**: `origin/raw-data` at `ad77758d4569ba6aafa955cc7843d874489e10f7`.
  - 4,327 meta records, of which 4,259 are judgments.
  - Extracted read-only to the scratchpad with `git archive`.
- **Curated originals**: cases_53 and records_658, plus the PILOT-01 87-code register `registers/source_code_resolution_v3.csv`.
- **Official judgment PDFs already held in the session scratchpad**: 16 judgments. Each is listed in `tools/held_copies.csv` with its URL, its SHA-256, and the basis for treating it as a court copy.
  - No new judgment was downloaded.
- **Army Rules version chain**: ARMY-RULES-CHAIN-01 seed on `origin/claude/next-stage-proposal` @ `11ce905e`, read only.
- **GitHub issues #3, #4 and #12**: read with the GitHub tools.

## Files
| File | What | Rows |
| --- | --- | --- |
| `intake_manifest.csv` | one row per distinct judgment document (sha256) in the intern corpus, with WS-B's lexical re-check, intake decision, flags, carrier/authority classification | 3,951 |
| `identity_resolution.csv` | 67 identity specs: the 53 curated cases plus 14 cases cited by KB/87-code. Intern doc_ids and SHA, official copy URL and SHA, excluded-log hits, identity state, discrepancies | 67 |
| `holdings_register.csv` | passage-level holding / ratio / disposition / observation / argument rows, with PDF page, paragraph, verbatim anchor, render SHA where page-image checked | 43 |
| `statutes_cited_effective_dates.csv` | provisions applied per judgment; publication / commencement / effective dates kept separate (all effective dates unresolved); IPC→BNS / IEA→BSA / Army Rules chain flags | 21 |
| `subsequent_treatment.csv` | proposition-level later treatment, with the later judgment's copy and pinpoint | 17 |
| `adverse_conflict_queue.csv` | adverse authority, source conflicts and intake defects | 16 |
| `pending_source_queue.csv` | acquisition requests (no download made) | 22 |
| `open_questions.csv` | owner, legal-advisor and WS-D questions, including OQ-D-004/008/009/012 | 14 |
| `crosswalk_cases53_kb658.csv` | spec ↔ KB record links: `CURATION_DECLARED_SOURCE_CODE` (via the 87-code register), `LEXICAL_LEAD_ONLY`, or ambiguous; per-case link counts and empty-holding citability flag | 208 |
| `intake_stats.json` | all counts, with their denominators | |
| `validation_rules.md` | rules V1–V11 for checking future intern deliveries | |
| `tools/` | `build_registers.py` (machine part), `manual_registers.py` (hand-reviewed rows), `case_specs.py`, `reviewed_matches.py`, `held_copies.csv`, `check_ws_b.py` | |

## Rebuild
```sh
git archive ad77758d4569ba6aafa955cc7843d874489e10f7 data/meta data/text data/excluded_judgments.jsonl | tar -x -C <snap>
python3 tools/build_registers.py --snapshot <snap> --raw-data-commit ad77758d4569ba6aafa955cc7843d874489e10f7
python3 tools/manual_registers.py
python3 tools/check_ws_b.py      # CSV shape and frozen-original checks
```

## Key counts
All counts come from `intake_stats.json`.

**Judgment records (4,259)**
- By court: SC 368, Delhi 1,957, P&H 1,215, J&K 410, Allahabad 309.
- Intern relevance labels: relevant 2,871, borderline 1,341, not_checked 47.

**Distinct documents (3,951)**
- 308 records share bytes with another record and are collapsed:
  - SC year-folder duplicates;
  - HC common judgments, including one PDF filed under 209 Delhi writ records.
- WS-B intake decision: INCLUDE 3,356, HOLD_FOR_REVIEW 378, EXCLUDE_PROPOSED 217.
- WS-B lexical class:

| Class | Documents |
| --- | --- |
| MIL_CORE_LEXICAL | 3,209 |
| MIL_PROBABLE_LEXICAL | 147 |
| WEAK_SIGNAL_REVIEW | 206 |
| CAPF_OR_OTHER_FORCE_LEAD | 94 |
| NO_MILITARY_SIGNAL | 288 |
| TEXT_UNAVAILABLE | 7 |

- 243 kept documents (33 of them labelled relevant) are kept only because the intern's "invalided" keyword also matches "invalidation".
- There are **no AFT judgments** in the intern corpus.

**Curated 53 cases**
- 34 mapped to an intern document by cover-page identity.
- 13 official court copies are held; 7 of them also have an intern copy.
- 13 are unresolved, with no copy in hand.
- 10 have an empty curated holding. They are flagged not citable.
- 31 have no code-declared KB link; 27 have no KB link even lexically.

## Scope limits (exact)
- **Verified against an official court copy**: only the holdings rows marked `PASSAGE_LOCATED_OFFICIAL_COPY_*`, covering 16 judgments. Six of their pages were checked as page images (render SHA recorded).
- **Pinned on the intern AWS mirror only, which is not an official copy**: 7 P0 pension cases and Kuldeep Yadav.
- **Not reviewed**: the operative directions in Naga People's Movement.
- **Located on the text layer only (no page image)**: the Isaac references to the older pension cases (pp.49-51, 61). Their evidential role is open (A-16).
