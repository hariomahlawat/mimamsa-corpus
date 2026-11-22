# WS-C-MML: Manual of Military Law and military procedures (programme #10, issue #13)

**DATABASE ONLY. Research proposals; nothing here is legal-advisor adjudicated or JAG validated.**
Policy: `docs/legal-audit/SOURCE_AUTHORITY_POLICY.md` v1. All eight MML files remain `UNVERIFIED_MANUAL` / `USER_SUPPLIED` / `HASH_ONLY` / amendment chain `NOT_CHECKED`. MML commentary is never statute. It never overrides Acts, Rules, amendments or binding judgments. The nine-volume mapping is inferred, not authoritative.
Fixed determinations are unchanged: r.23(3) CONFLICTING; r.193 = C-08 OPEN; r.194 = C-09 PROPOSAL. MML 2 agreeing with S.R.O. 332/1989 is evidence, not approval.

**No complete derived MML text is committed.** Files hold:
- locators (PDF page, printed page, derived line);
- headings of 60 characters or fewer;
- short excerpts, only inside page-image-check rows.

## Inputs
`input_manifest.json`: SHA-256 of every input.
- 24 repository files.
- 35 private scratchpad files: the 8 originals, the transport ZIP, 8 + 8 derived text files, 5 DOC→PDF renders and 4 India Code comparison files.
- All 8 originals are equal to `MML_Originals_Manifest.csv`.
- The derived text used is `repro1/`, which equals the PILOT-01 `mml_derived_manifest.json`.
- The older `derived/mml` DOC extractions differ from that manifest, so they are recorded as NOT_USED.
- Rebuild the manifest with `scripts/build_input_manifest.py <scratchpad>`.

## Deliverables
| File | Rows | Content |
| --- | ---: | --- |
| `mml_edition_status.csv` | 8 | One row per original: format, scope, cover pages, printing marks, date indicators, embedded file metadata (personal names redacted), access markings, policy v1 fields, authentication = NONE |
| `page_image_checks_wsc.csv` | 28 | WSC-PIC-01..28 with render SHA-256. 24 are renders of original PDF pages (20 from MML 2.pdf). 4 are LibreOffice renders of native DOC text, because a DOC has no page image |
| `provision_index.csv` | 410 | Locator of each Army Act section / Army Rule in MML 2.pdf, vol 2(AA) PDF/DOC and both vol 2(AR) DOCs, plus the doc-1 embedded printed page (`scripts/build_provision_index.py`) |
| `mml1_para_index.csv` | 352 | MML 1 Part I chapter/para → provisions cited (`scripts/build_mml1_para_index.py`) |
| `mml_provision_crosswalk.csv` | 847 | MML locator → provision (with ARMY-RULES-CHAIN-01 events: publication date, commencement as printed, effective date `NOT_DETERMINED`) → KB record IDs. The 78 PILOT-01 record/file/provision triples are excluded (`scripts/build_crosswalk.py`) |
| `procedure_gap_conflict_register.csv` | 17 | Procedural gaps, conflicts and obsolete guidance |
| `candidate_corrections.csv` | 14 | Proposals only; none applied |
| `kb658_source_coverage_inventory.csv` | 658 | Read-only source-coverage inventory (`scripts/build_kb658_inventory.py`; stdlib; re-runs byte-identical) |
| `kb658_coverage_summary.json` | – | Counts with denominators |
| `calibration_sample_ranked.csv` | 46 | Ranked high-risk records for the advisor's calibration. Selection only; none of these records was audited (`scripts/build_calibration_sample.py`) |
| `open_questions.csv` | 8 | Questions for the owner, the advisor or WS-A |

## Evidence levels
- **Gap register (17 rows).**
  - 14 rows rest on page images of the original MML 2.pdf.
  - 1 row rests on a render of native DOC text (PG-14).
  - 2 rows are text-only and marked REQUIRES_VERIFICATION: PG-08 (absence = NOT_FOUND) and PG-17.
- **Crosswalk and provision index.** All locators come from the text layer and are marked `REQUIRES_VERIFICATION`; no wording is relied on there. As a locator sanity check, the 18 PILOT-01 locators that were tested matched exactly (for example s.122 p.89, r.23 p.151, r.193 p.227, doc-1 r.23 p.351).
- **Corrections from image checks.** Two text-layer readings were wrong and were corrected by image check:
  - p.210: the 1993 note belongs to r.145, not r.147.
  - p.224: the 1993 note belongs to r.186, not r.184.

## 658 inventory: method and definitions (denominator 658)
**Inputs.** The parser (`scripts/kb_citations.py`) reads only the `references` field and the `sources` list. It uses:
- the PILOT-01 v3 code grammar and the 87-code register;
- plain-text Army Act and Army Rules pinpoints (context tracking for AA, AR and other instruments);
- other-statute mentions and case-citation patterns.

**Record SHA.** `record_sha256` = SHA-256 of the stored JSONL line without its LF (the PILOT-01 convention).

**What counts as held in the corpus.**
- Corpus-held codes are those classed CORROBORATED_OFFICIAL or RESOLVED_RECORD_EXPLICIT whose target is an `act-`, `rules-` or `DCLR-` id.
- Codes resolved only by co-citation (RESOLVED_CO_CITATION) are counted as anchors but cannot give FULL. This avoids KPI inflation.

**Coverage states.**

| State | Meaning | Records |
| --- | --- | ---: |
| FULL | Every parsed citation resolves to a corpus-held source; a pinpoint exists; no unresolved or gap items | 379 |
| PARTIAL | At least one corpus-held anchor, plus a gap, an unresolved item, co-citation only, or a missing pinpoint | 131 |
| SOURCE_GAP | Sources identified, but none held in the corpus | 56 |
| UNRESOLVED | Citations present, none resolvable | 14 |
| NO_CITATION | No citation (template text, internal links or placeholders only) | 78 |

FULL is a parsing and coverage state. It does **not** mean the wording or the law has been verified.

**Other counts (denominator 658).**
- 389 records carry a citation code; 269 carry none (this matches the v3 inventory).
- 175 records have an Army Act pinpoint; 169 have an Army Rules pinpoint.
- Statutory anchor present: 456.
- 63 records carry a broken or unresolved flag:
  - 16 placeholders;
  - 13 unresolved plain-text case citations;
  - 5 Army Act or Army Rules citations with no pinpoint;
  - 1 non-official URL (indiankanoon.org);
  - unresolved codes: AO, SRC-AO, V6-S02/03/10/13/22, V7-S04, V7-S16, V8-S11, V9-S08, AR_ALT.
- 6 records cite provisions that are shown as omitted. This is an informational flag, not a verdict.
- 17 records carry a duplicate-claim flag: 3 groups with the same title, plus 5 pairs of near-duplicate text (3-shingle Jaccard ≥ 0.25).
- **MML anchor in record: 0/658.** No record names the MML. 293/658 can be linked to an MML locator through the PILOT-01 or WS-C crosswalk.

## Calibration sample
46 records, drawn from the 633 non-pilot records.
- Ranking is by a transparent score: consequence keywords, coverage state, flags, link to a gap row or to r.23, near-approval status, and not yet piloted.
- At most 8 records per module, and at least 2 per module.
- This is a selection only. No record in it has been audited.
