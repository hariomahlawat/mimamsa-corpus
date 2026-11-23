# Rule-level indexing of subordinate legislation: technical specification (DRAFT 0.1)

**Cycle 4 planning. DATABASE ONLY. Nothing is built, downloaded, configured or approved by this document.** It specifies how a later, owner-approved stage would extract and index the Army Rules 1954, the AFT (Procedure) Rules 2008, the AFT (Procedure) Amendment Rules 2011 and other subordinate legislation at provision level. No legal determination is made. Reserved states are quoted unchanged: r.23(3) CONFLICTING (C-01); r.193 C-08 OPEN; r.194 C-09 PROPOSAL; r.15, r.187(1) and s.129 OPEN; AQ-05, AQ-06 and OQ-A-13 reserved. A provision being searchable never means it is verified, current or correct.

## Files in this folder
| File | Content |
| --- | --- |
| `RULE_INDEX_SPEC.md` | This specification |
| `provision_record.schema.json` | JSON Schema (draft 2020-12) for one provision-version record. Draft 0.1, for review |
| `estimate_rule_index_coverage.py` | Deterministic estimate (stdlib; read-only; `--out DIR`) |
| `rule_index_coverage_estimate.csv` | One row per record flagged `PROVISION_FILES_ABSENT` (193): outcome, plus a conservative outcome |
| `rule_index_coverage_keys.csv` | One row per absent provision key (527): how it would resolve, and the compilation page |
| `compilation_rule_presence.csv` | Rule headings located in the three held compilation texts (247 rows) |
| `rule_index_coverage_summary.json` | Counts, input hashes, and the stated assumptions |

## 1. Scope and current holdings
| Instrument | doc_id (origin/raw-data) | Held compilation text (comparison grade) | Gazette carrier (wording source) | Register |
| --- | --- | --- | --- | --- |
| Army Rules, 1954 (S.R.O. 484, 27-11-1954) | `rules-army-rules-1954` | India Code bitstream, sha256 `48f52219…a727`, 214 pages, MoD compilation with interleaved NOTES and "(Authority: …)" lines | Gazette Pt II-S4 No.47 (archive.org `in.gazette.central.w.1954-11-27.103686`; scratchpad copy sha256 `c5ef95a9…aca6`; ACQ-01 record copy not yet approved) | `ARMY-RULES-CHAIN-01/army_rules_instrument_register.csv` AR-000 |
| Army Rules amendments (AR-001 … AR-046) | none (no corpus doc per instrument) | n/a | 26 ACQ-01/ACQ-02 Gazette files held as scratchpad copies (image-checked per the register; not record copies); text-layer-only, hint and NOT_FOUND instruments listed in `../acquisition_readiness/` (tier T2) | AR-001 … AR-046 |
| AFT (Procedure) Rules, 2008 (S.R.O. 26(E), Gazette Extr. 17-09-2008) | `rules-aft-procedure-rules-2008` | India Code bitstream, sha256 `590cf7cd…0e317`, 47 pages, bilingual Gazette scan with a poor English text layer | ACQ03-030 (archive.org, not held) | none yet (to be added; see §11) |
| AFT (Procedure) Amendment Rules, 2011 (S.R.O. 5(E), 29-07-2011) | `rules-aft-amendment-procedure-rules-2011` | India Code bitstream, sha256 `fc27032f…29904`, 2 pages, bilingual | ACQ03-031 (archive.org, not held) | none yet |
| Other subordinate legislation in the corpus | `rules-aft-practice-rules-2009`, `rules-aft-procedure-investigation-rules-2008`, `rules-the-army-and-air-force-disposal-of-private-property-rules-1953`, Adjustment of Jurisdiction Rules (ACQ-01 B2) | data/meta present | per acquisition matrix | to be added |

Regulations, manuals and policy letters (Regulations for the Army 1987, MML, Entitlement Rules 2023, Guide to Medical Officers 2023) use the same record shape but are separate instruments with their own `document_authority`; they are out of scope for the first build.

## 2. Identifiers
- **provision_id** (version-free): `<doc_id>#r<number><suffix>` with the suffix in lower case (`rules-army-rules-1954#r13a`). Sub-units append the printed path: `#r23(3)`, `#r187(1)(r)`. Appendices, forms, tables and schedules use `#app<n>`, `#form<n>`, `#tab<n>`, `#sch<n>`. This matches the Act convention (`act-army-1950#s69`) and the file key WS-D `canonical_coverage.provision_searchable` already checks (`"r" + number.lower()`).
- **version_id**: `<provision_id>@v<year>-<instrument key>`, e.g. `rules-army-rules-1954#r15@v1961-SRO-205`. The instrument key equals the WS-D `build_versioned_edges` `event_key` (`SRO-205-1961` → `v1961-SRO-205`), so edges and records join without a mapping table.
- **instrument_register_id**: the ARMY-RULES-CHAIN-01 `instr_id` (AR-000 …). New registers for AFT rules use their own prefix (proposed `AFTR-000` …) with the same columns.
- Printed forms are normalised only in the id (`15-A` → `15a`); `number_as_printed` keeps the printed form.

## 3. Record types and storage layout
```
data/provisions/<doc_id>/<key>.json          one file per provision (all versions inside, array "versions")
data/provisions/<doc_id>/_index.json         provision index: keys, order, headings, carrier hashes
data/provisions/<doc_id>/_instrument.json    instrument identity, Gazette identity, carriers, register id
data/provision_versions.jsonl                flat list, one provision_record (schema) per line
data/provision_change_events.jsonl           one row per amendment event (grouped as in build_versioned_edges)
```
- `data/provisions/<doc_id>/<key>.json` mirrors `origin/raw-data` `data/sections/<doc_id>/<key>.json` (schema 0.2.0: `section_id`, `parent_doc_id`, `unit`, `number`, `heading`, `order`, `text`, `page_start`, `amendment_history`, `field_provenance`). The new record is a superset: the Act fields keep their names, and each version becomes a `provision_record`. Existing Act section files are not rewritten; a later migration may add versions to them additively.
- A file exists for every provision in the instrument, including omitted ones (an omitted rule has a version whose `exact_text` is null and whose `change_event.event_type` is `omitted`). This keeps `canonical_coverage` from reporting an omitted-but-cited rule as absent, while the record still says it is omitted.
- Sub-rules are records in the same file (array `units`), not separate files, so a citation `r.23(3)` resolves to `r23.json` exactly as WS-D's key rule expects.

## 4. Extraction pipeline (each stage re-runnable; raw files never modified)
1. **Carrier intake.** Only carriers already acquired under an approved run (or held compilation texts for comparison). Record `carrier_sha256`, `source_url`, `acquisition_id`, `approval_ref`. A scratchpad copy is not a record copy.
2. **Text layer.** `pdfplumber`/`pymupdf` text with `[[page N]]` markers (the crawler's existing convention). Store `text_layer_sha256`. Per page: characters, dictionary-word ratio, script mix (Devanagari vs Latin). Pages failing the sanity check, and bilingual pages where the English column is garbled (both AFT files), go to OCR or manual page-image transcription.
3. **OCR (only where needed).** Tesseract/PaddleOCR English (and Hindi where a bilingual comparison is required). Store per-page confidence. Pages below threshold are listed in the review queue, never silently kept (`LOW_OCR_CONFIDENCE`).
4. **Editorial separation.** Compilation annotations are removed from `exact_text` and kept in `editorial_annotations_excluded`: "NOTES"/"NOTE" blocks with their own 1., 2. numbering, "(Authority: SRO … )" lines, compiler footnotes. The Army Rules compilation contains all of these (see `compilation_rule_presence.csv` method notes).
5. **Segmentation grammar** (Army Rules and AFT rules):
   - rule heading: a line `N.` / `N-A.` / `N. Heading.` / `N. Heading.—text`, or a range `N to M.` (e.g. "172 to 176. Cancelled vide SRO 17E dt 06 Dec 93");
   - monotonic window: the next rule is the same number with a later suffix, or at most 6 above the last (171 → 177 after omitted 172–176); lower numbers are sub-rule or note numbering;
   - sub-rule `(1)`, clause `(a)`, sub-clause `(i)`, proviso "Provided that", Explanation, each as a unit with its own path;
   - "Omitted"/"Cancelled"/"Deleted" within the heading block marks an omission marker;
   - numbers that break the sequence (OCR `43.` for `13.`) are never silently corrected: the rule is `HEADING_NOT_FOUND_IN_TEXT_LAYER` until read from the page image.
6. **Page location.** Every unit carries `pdf_page`, `printed_page` and character offsets in the text layer, so a citation can point to a page and the text can be re-derived from the carrier.
7. **Versioning** (§6) from the registers, not from the compilation's own footnotes. Compilation footnotes are comparison evidence only.
8. **Validation** against `provision_record.schema.json`; the run fails on any invalid record.
9. **Index build** (§9).

## 5. Dates (owner date rule, as in ARMY-RULES-CHAIN-01 and WS-D)
- `publication_date`, `commencement_as_printed`, `effective_date`, `effective_date_status` and `retrospective_deemed_effect_from` are separate fields.
- `effective_date` is filled only when the instrument states its commencement (`STATED_IN_INSTRUMENT …`). A silent instrument keeps `effective_date` null with `NOT_STATED_PENDING_ADVICE (AQ-05)`; publication is never copied into it.
- `retrospective_deemed_effect_from` carries a deemed date (S.R.O. 216/1988: commencement 1988-09-17, deemed from 1979-06-04). It never becomes `valid_from`; flag `RETROSPECTIVE_DEEMED_EFFECT_AQ06`; legal effect reserved to AQ-06.
- `valid_from` = `effective_date` when stated, else null with `EFFECTIVE_DATE_UNSTATED`; `valid_to` follows the successor's stated commencement, else `VALID_TO_UNSTATED`. Two different stated commencements for one event raise `EVIDENCE_EFFECTIVE_DATE_CONFLICT`. These are exactly the `build_versioned_edges` rules, so the index and the versioned edges cannot disagree.
- For the AFT 2011 amendment, the instrument states "come into force on the date of their publication" (text layer, p.2; to be confirmed from the page image), so its versions may carry a stated date once the Gazette copy is verified.

## 6. Amendment history and version relationships
- Inputs: `ARMY-RULES-CHAIN-01/army_rules_instrument_register.csv`, `army_rules_provision_chronology.csv`, `statutory_version_register_seed.csv`, WS-A `provision_change_log.csv` (and `provision_change_log_supersessions_cycle3.csv`), WS-A `army_act_amendment_chain.csv` for Act-level links.
- One `change_event` per (provision, amending-instrument key, publication date), grouping duplicate descriptions (seed row + change-log row) as `build_versioned_edges` does; `change_log_ids` lists them all.
- `predecessor_version_id` / `successor_version_id` link versions; zero-length or reversed intervals are rejected, never emitted.
- Event types: enacted, inserted, substituted, amended, renumbered (AFT 2011: r.7 renumbered as r.7(1)), omitted, repealed, superseded, corrigendum (S.R.O. 68/1985), declaration_not_amendment (S.R.O. 34/1963, S.R.O. 2(E)/2018: recorded so they are not mistaken for amendments).
- An amending instrument's own provisions are records too (`rules-aft-amendment-procedure-rules-2011#r3`), linked by `by_provision_id` to the principal provision they change (`rules-aft-procedure-rules-2008#r12a`).
- `known_chain_gaps` lists register gaps that may affect the version (AR-001 E-7/1960, AR-030 S.R.O. 258/2002, AR-036 post-2022, unverified hints AR-012/013/015/037–046, OCR-only AR-002–005/032). `chain_state` stays `CHAIN_PARTIAL` while any applies.
- `determination_state`, `conflict_id` and `legal_review_required` are copied from the registers (r.23(3) CONFLICTING C-01; r.193 OPEN C-08; r.194 PROPOSAL C-09); the index never changes them.

## 7. Source hash and reproducibility
- Every record stores the carrier SHA-256, the text-layer SHA-256, the render PNG SHA-256 where a page image was read, the extractor path and SHA-256, all input hashes and the register rows used, and its own `record_sha256` (canonical JSON, sorted keys, `record_sha256` zeroed during hashing).
- Builders are deterministic (sorted output, no timestamps, pinned dependencies in `requirements.txt`); two runs must be byte-identical, as for the audit generators.
- `text_sha256` is over `exact_text` after the declared normalisation, so a later re-extraction can prove the wording did not change.

## 8. Uncertain or incomplete extraction
- `extraction.method` (pdf_text, ocr, page_image_transcription), OCR engine and per-page confidence.
- `verification_state`: `UNVERIFIED_EXTRACTION` → `COMPILATION_COMPARISON_ONLY` (wording from a government compilation: never above this) → `PAGE_IMAGE_CHECKED` (needs a render hash; the schema enforces it) → `PAGE_IMAGE_CHECKED_SECOND_READING` (for consequential negations and numbers, as for r.23(3)).
- `uncertainty_flags`: OCR_ONLY, TEXT_LAYER_ONLY, BILINGUAL_TEXT_LAYER, LOW_OCR_CONFIDENCE, HEADING_NOT_FOUND_IN_TEXT_LAYER, NUMBER_INFERRED_FROM_SEQUENCE, BOUNDARY_UNCERTAIN, CONTINUATION_PAGE_UNREAD, EDITORIAL_TEXT_INTERLEAVED, COMPILATION_ONLY, HINT_ONLY_INSTRUMENT, INSTRUMENT_NOT_HELD.
- Instruments that exist only as OCR text or hints (AR-002–005, AR-032, AR-012/013/015/037–046) produce **no wording records**; they appear as change events with `INSTRUMENT_NOT_HELD` / `HINT_ONLY_INSTRUMENT` and keep dependent versions `CHAIN_PARTIAL`.
- The provenance controls apply unchanged: a text-layer or hint row never claims image-checked status (RV-1), and every image-checked claim resolves to a render hash (IMG-2/3).

## 9. Fully offline search
- Output is a single SQLite file in the snapshot (`snapshots/<date>/provisions.sqlite`) plus the JSON files above; no network, service or model is needed at query time.
- Tables: `instrument`, `provision` (version-free), `provision_version` (one row per schema record), `change_event`, `source_location`, `annotation` (excluded editorial text, searchable separately and labelled as such).
- Full-text: FTS5 virtual table over `provision_version.exact_text` and `heading`, with `unicode61 remove_diacritics 2` and a column for the provision path; the editorial-annotation FTS table is separate, so a hit in a NOTE is never presented as rule wording.
- Point-in-time query: `WHERE valid_from <= :date AND (valid_to IS NULL OR valid_to > :date)`; rows with `EFFECTIVE_DATE_UNSTATED` are returned with that flag, never dropped and never dated by publication.
- Citation lookup: a normaliser maps "AR 23(3)", "r.23(3)", "Rule 23(3) of the Army Rules" to `rules-army-rules-1954#r23(3)` (the same normalisation the WS-D plain-text parser uses for Acts).
- Every result displays `verification_state`, `uncertainty_flags`, `determination_state` and `known_chain_gaps`.
- The snapshot's `SHA256SUMS` covers the SQLite file and every JSON file; the offline side verifies before import.

## 10. Alignment with existing structures
| Existing structure | How the index uses it |
| --- | --- |
| ARMY-RULES-CHAIN-01 `army_rules_instrument_register.csv` | `instrument_register_id`, Gazette identity, `evidence_level` → `verification_state`/flags, `effective_date_status`, `retrospective_deemed_effect_from`, `amends_r23` |
| ARMY-RULES-CHAIN-01 `army_rules_provision_chronology.csv`, `statutory_version_register_seed.csv` | Version list per provision, `determination_state`, `conflict_id`, `legal_review_required` |
| ARMY-RULES-CHAIN-01 `page_image_checks_chain.csv` (and WS-A/WS-C page-image registers) | `render_png_sha256`, `render_dpi`, `page_image_check_id` on source locations |
| WS-A `provision_change_log.csv` | `change_log_ids`, `change_as_printed`, `page_anchor` → `printed_page` |
| WS-D `build_versioned_edges.py` / `relation_graph_versioned_edges.csv` | `event_key` = version key; identical date rules and flags; edges KB record → `version_id` |
| WS-D `canonical_coverage.py` `provision_searchable` | Provision files at `data/provisions/<doc_id>/r<n><suffix>.json` (or the same keys under `data/sections/<doc_id>/` if the owner prefers one tree) satisfy the existing check without changing WS-D code |
| origin/raw-data `data/sections/<doc>/` (Acts, schema 0.2.0) | Same identifier and file conventions; superset record; no rewrite of existing files |
| SOURCE_AUTHORITY_POLICY v1 | `provenance` block; compilation wording capped at `COMPILATION_COMPARISON_ONLY` (schema rule) |

## 11. Estimate: PROVISION_FILES_ABSENT records that verified rule-level indexing could make searchable
Computed by `estimate_rule_index_coverage.py` (deterministic; two runs byte-identical) from WS-D `canonical_coverage.csv` and the held compilation texts on `origin/raw-data` (commit `ad77758d`).

- **Flagged records: 193** (116 coded, 77 plain-text). The re-check reproduces the flag for all 193. Every absent key is a rule key: 449 Army Rules, 67 AFT Procedure Rules 2008, 11 AFT Amendment Rules 2011 (527 keys). No Act section file is missing for these records.
- **Upper estimate: 188 of 193** would have every cited provision present after indexing (the identified items would then all be searchable, so `source_searchable` would become ALL). 180 of these carry no other quality flag. The other 5 improve partly: AFT-004, AFT-020, AFT-023 and V7-CL-03 cite AFT r.7 or r.13, which the bilingual text layer does not yield; AFT-020 and HCE-015 also carry a year parsed as a rule key (`r2011`, `r1993`), which no index can resolve.
- **Conservative estimate: 155 of 193** (148 with no other flag). This counts only keys found as rule headings in the Army Rules compilation. It excludes every key resolved from the bilingual AFT texts, whether found as a heading, as a principal rule the 2011 instrument inserts (r.12A) or renumbers (r.7), or only through that amending instrument. It also excludes the two omitted-rule markers (r.25 in HCE-015 and HCE-033).
- By instrument: Army Rules 156 records fully resolved and 1 partly; AFT 2008 32 and 4; AFT 2011 7 and 2 (a record can cite several instruments).
- Located rule headings: 212 Army Rules keys (r.1–r.205 with 13A, 15A, 16A–16C, 80A, 170A, 170B; 172–176 as an omission range); not found: r.84 (printed without a full stop) and r.15B (inserted 2019; absent from this compilation, which therefore predates S.R.O. 17(E)/2019). AFT 2008: 28 keys; r.7, r.13, r.14, r.15, r.19 and r.32 are not recoverable from the text layer.

**Assumptions (stated, not verified):**
1. The held compilation texts are comparison-grade only (India Code / MoD compilation; SOURCE_AUTHORITY_POLICY v1). They are not Gazette authority, and their wording may differ from the Gazette (r.23(3) is the known case).
2. Every provision counted here still needs verification against Gazette page images and the registered amendment chain before it is relied on. Until then its records stay `COMPILATION_COMPARISON_ONLY` / `CHAIN_PARTIAL`.
3. "Technically searchable" means a provision record would exist for each cited key, so the WS-D check would pass. It says nothing about legal correctness, currency or which version a KB record means.
4. A heading found in a text layer shows the rule is present in that compilation only. The compilation's currency is limited: r.15B (2019) is absent.

## 12. Acceptance checks for the later build
- Schema validation of 100% of records. A provision file exists for every cited key that the instrument contains, omitted rules included.
- Every `PAGE_IMAGE_CHECKED` record resolves to a render hash. No compilation-sourced record rises above `COMPILATION_COMPARISON_ONLY`.
- Effective dates come only from `STATED_IN_INSTRUMENT` rows. Retrospective dates never appear in `valid_from`.
- Determination states are byte-equal to the registers. Two builds are byte-identical.
- Re-running WS-D `canonical_coverage.py` against the new corpus ref moves records out of `PROVISION_FILES_ABSENT` only for keys that have files.

## 13. Owner decisions needed
1. Directory: `data/provisions/` (new tree) vs. adding rule files under `data/sections/`.
2. Approval of the Gazette acquisitions that supply wording sources (ACQ-01 S.R.O. 484 record copy; ACQ03-030/031 for AFT rules). See `../acquisition_readiness/acquisition_readiness.csv`.
3. Whether the bilingual AFT Gazettes are transcribed from page images (recommended; the text layer is unusable for several rules) or OCR'd.
4. A register for AFT rule instruments in the ARMY-RULES-CHAIN-01 format.
