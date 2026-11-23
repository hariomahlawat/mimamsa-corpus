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
| `identity_resolution.csv` | 71 identity specs (4 added in cycle 2 for CC-11): the 53 curated cases plus 14 cases cited by KB/87-code. Intern doc_ids and SHA, official copy URL and SHA, excluded-log hits, identity state, discrepancies | 71 |
| `holdings_register.csv` | passage-level holding / ratio / disposition / observation / argument rows, with PDF page, paragraph, verbatim anchor, render SHA where page-image checked; `cycle` column | 58 |
| `statutes_cited_effective_dates.csv` | provisions applied per judgment; publication / commencement / effective dates kept separate (all effective dates unresolved); IPC→BNS / IEA→BSA / Army Rules chain flags | 21 |
| `subsequent_treatment.csv` | proposition-level later treatment, with the later judgment's copy and pinpoint | 28 |
| `adverse_conflict_queue.csv` | adverse authority, source conflicts and intake defects | 23 |
| `pending_source_queue.csv` | acquisition requests (no download made) | 30 |
| `open_questions.csv` | owner, legal-advisor and WS-D questions, including OQ-D-004/008/009/012 | 17 |
| `intern_filter_audit.csv` (cycle 2) | intern relevance filter tested against all 71 KB/53/87-code cited cases: kept / removed / absent, with assessment and evidence | 71 |
| `allow_list_proposed.csv` (cycle 2) | proposed allow-list (proposal only; intern corpus unchanged) | 32 |
| `intern_invalidation_false_positives.csv` (cycle 2) | documents kept only via the word "invalidation" | 243 |
| `case_relations.csv` (cycle 2) | case-to-case edges: curated related_cases (reciprocal / one-way) and directional citation/treatment edges observed in copies | 38 |
| `crosswalk_cases53_kb658.csv` | spec ↔ KB record links: `CURATION_DECLARED_SOURCE_CODE` (via the 87-code register), `LEXICAL_LEAD_ONLY`, or ambiguous; per-case link counts and empty-holding citability flag | 216 |
| `intake_stats.json` | all counts, with their denominators | |
| `validation_rules.md` | rules V1–V11 for checking future intern deliveries | |
| `tools/` | `build_registers.py` (machine part), `manual_registers.py` (hand-reviewed rows), `case_specs.py`, `reviewed_matches.py`, `held_copies.csv`, `check_ws_b.py` | |

## Rebuild
```sh
git archive ad77758d4569ba6aafa955cc7843d874489e10f7 data/meta data/text data/excluded_judgments.jsonl | tar -x -C <snap>
python3 tools/build_registers.py --snapshot <snap> --raw-data-commit ad77758d4569ba6aafa955cc7843d874489e10f7
python3 tools/cycle2_filter_audit.py --snapshot <snap>   # after build_registers.py (adds keys to intake_stats.json)
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
- 13 were unresolved with no copy in hand after cycle 1; 5 remain after cycle 2 (see below).
- 10 have an empty curated holding. They are flagged not citable.
- 31 have no code-declared KB link; 27 have no KB link even lexically.

## Scope limits (exact)
- **Verified against an official court copy**: only the holdings rows marked `PASSAGE_LOCATED_OFFICIAL_COPY_*`, covering 16 judgments. Six of their pages were checked as page images (render SHA recorded).
- **Pinned on the intern AWS mirror only, which is not an official copy**: 7 P0 pension cases and Kuldeep Yadav.
- **Not reviewed**: the operative directions in Naga People's Movement.
- **Located on the text layer only (no page image)**: the Isaac references to the older pension cases (pp.49-51, 61). Their evidential role is open (A-16).

## Cycle 2 (2026-11-22)
- **13 unresolved curated cases.** 8 now have their citation metadata cross-checked against an official record. Sources:
  - later official judgments that are already held (Virendra, Parashotam, Jasbir, Arjun, Isaac);
  - two Supreme Court office-report HTML pages fetched read-only from the court's own server (`api.sci.gov.in`). Their SHA-256 values are in `tools/reviewed_matches.py`.
- **Conflicts found.** For 2 of those 8 the curated metadata conflicts with the official record:
  - Shafhi: case number and reporter citation;
  - Ram Sarup: SCR volume.
- **Still unresolved: 5.** Girish clarification, Ravinder Kumar, Praful Desai, S.R. Dhingra, Ranjit Thakur review.
- **No new judgment PDF was downloaded.**
- **Intern filter audit**, 71 cited cases:

| Assessment | Cases |
| --- | --- |
| correct keep | 39 |
| absent (undetermined) | 18 |
| absent, likely unreported order | 6 |
| absent, recent-coverage gap | 3 |
| exclusion consistent with the filter but cited by the KB | 2 |
| exclusion conflicts with KB reliance (L. Chandra Kumar) | 1 |
| probable incorrect exclusion (Nitisha MA 2023) | 1 |
| kept but labelled borderline | 1 |

- **Holdings.** 15 new rows, covering:
  - Jasbir paras 23–39 (with KB pinpoint checks);
  - Virendra paras 10–11;
  - P.P.S. Bedi on rr.22/23, Rule 40 and s.130;
  - Isaac p.61;
  - Arjun para 51 (Sonu);
  - S P Rathore on Ram Avtar (mirror);
  - Pandappa (mirror).
- **Page images.** 5 more pages were checked (Isaac pp.61 and 69, PPS Bedi p.31, Jasbir p.32, Virendra p.13). The cycle-1 Isaac para 19.4 row (p.69) moved from text layer to page image.

## Cycle 3 (2026-11-22, branch claude/ws-b-cycle3)
New files only. No cycle 1–2 row was rewritten; supersessions are recorded in `corrections_cycle3.csv`.

| File | What | Rows |
| --- | --- | --- |
| `authoritative_copy_status_cycle3.csv` | the 27 curated cases held only as intern mirror copies: is an official copy held, or locatable read-only? | 27 |
| `pending_acquisition_cycle3.csv` | official copies still needed (27 mirror-only plus 5 unresolved) | 32 |
| `identity_resolution_cycle3.csv` | the 5 unresolved cases, plus proposed resolutions of A-C2-01 (Ram Avtar) and A-C2-02 (Ram Sarup) | 7 |
| `holdings_register_cycle3.csv` | Naga conclusions; Manjeet, Angad and Keshar ratio (mirror); Mullikote CORRECTED version; Girish paras 13–15; Parashotam paras 18–21; Ranjit s.130 | 20 |
| `subsequent_treatment_cycle3.csv` | 4 classified rows, plus citation leads from a name scan of the intern corpus (editorial headnote labels marked as not evidence) | 81 |
| `citation_scan_summary_cycle3.csv` | per-case counts of later citing documents (discovery only; no strength inferred) | 18 |
| `kb658_case_name_links_cycle3.csv` | the 37 KB records flagged by WS-C (`case_names_matched` / CASE_NAME_WITHOUT_CODE / PLAIN_CASE_CITATION_UNRESOLVED), mapped to case identities with KB text evidence | 43 |
| `corrections_cycle3.csv` | versioned corrections and process deviations | 3 |
| `network_lookup_log_cycle3.csv` | every network request in cycles 2–3 | 14 |

**Rebuild:**
```
python3 tools/cycle3_citescan.py <scan.json> <snap>
python3 tools/cycle3_registers.py --snapshot <snap> --citescan <scan.json> --wsc-inventory <WS-C inventory csv> --netlog <tsv>
```

**Findings**

*Official copies for the 27 mirror-only cases*
- None is held in the scratchpad. I identified the 33 JUDIS "probe" PDFs and the other held PDFs by their cover pages; none is one of the 27.
- 11 have an official-host URL in the curated record. 10 of those are on `api.sci.gov.in`, where a HEAD request gave 404 for every URL, including a control URL whose bytes were obtained earlier. The result is therefore inconclusive.
- Buttar's URL is a government-hosted SCR volume (s3waas), which answered HEAD 200 with a PDF.
- 16 have no official URL located. All 27 are queued for acquisition.

*Identities*
- Ram Avtar: the official Girish judgment (p.10, page image) and the court's office report support the identity "SC order of 10.12.2014, C.A. 418/2012". The curated URL is the S P Rathore judgment, so it is the wrong document.
- Ram Sarup: the official P.P.S. Bedi copy and four mirror judgments print [1964] 5 SCR 931. Only Jasbir prints volume 4. The proposal is volume 5; agreement between copies is not authority, so confirmation from the Hugging Face copy is still needed.
- Ravinder Kumar: a Delhi HC 2025 mirror judgment gives a lead citation, (2015) 12 SCC 291.
- Girish clarification, Praful Desai and the Ranjit Thakur review order remain unresolved.

*Holdings*
- Of the 10 curated cases with an empty holding, 8 now have proposals:
  - Navjot, on an official copy (cycle 1);
  - Manjeet, Angad, Baljit, Balachandran, Surinder, Keshar and Naga, on mirror copies only.
- Mani Ram and Dhingra cannot be done, because no copy is held.
- 8 new page images. Each is listed with its SHA-256 in the holdings rows.

*Correction CR-C3-01*
- Cycle-1 row WSB-H-030 cites the second, uncorrected version of the Mullikote PDF. That version is numbered differently from the CORRECTED one.
