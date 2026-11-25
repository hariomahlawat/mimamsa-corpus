# C13 workstream A4: statutory evidence and temporal legal knowledge

**Status: research derivative, version `C13A4-v1` (evidence `C13A4-EV-v1`, version model `C13A4-VM-v1`).
Nothing has been applied and nothing is legally approved.** Every evidence-state change is a proposal, every version
record is `AUTOMATED_CANDIDATE_NOT_VERIFIED`, and the adviser packet asks questions without answering them. The frozen
originals (`records_658` `9a8f0d19…`, `cases_53` `8b8d53cd…`) are verified on every run and unchanged; no register of an
earlier cycle, no C12F output and no held copy was modified. AUTH-LEDGER stays at version 0. Independent review is
required (the author has not reviewed their own work).

## 1. Provision-level temporal version model

`schema/provision_version.schema.json` (JSON Schema 2020-12), `records/PROVISION_VERSIONS_C13.jsonl` (488 records),
`tools/build_versions_c13.py` (compiler, `--check`), `tools/validate_versions_c13.py` (validator and date resolver).

A record is **one version of one provision**. It starts with the located event that created it and ends when the next
located event takes effect. Each record carries:

* `version_kind`: as_notified / as_enacted / insertion / substitution / amendment_words / omission / retrospective_omission /
  repeal / repeal_with_savings / commencement / edition (+ establishment, applicability_exception, implementing_instrument in the schema);
* `created_by`: instrument id, instrument, date, publication date, item number and the register rows it was compiled from;
* `effective_from` and `effective_to`, each with a status. A date is filled only when the instrument states it
  (`STATED_IN_INSTRUMENT`, `STATED_DEEMED_IN_INSTRUMENT`). Compilation-only dates go to `reported_date`
  (`REPORTED_IN_COMPILATION_ONLY`); silent instruments are `NOT_STATED_PENDING_ADVICE` (AQ-05); a publication date is
  never treated as commencement. `retrospective_deemed_effect_from` is kept separately (AQ-06);
* `jurisdiction`, `applicability_exceptions` (e.g. r.15B for rr.14, 15, 15A from 28-12-2019; BNS s.106(2)),
  `savings_transitional` (BNS s.358(2)-(3), BNSS s.531(2), BSA s.170(2), Act 13/1975 s.4(2));
* `temporal_axes`: four **separate** slots - conduct date, proceedings date, procedural-action date, document
  preparation/review date - each `NOT_DETERMINED` with a legal question id (`outputs/TEMPORAL_AXES_A4.csv`);
* `text_evidence`: copy id, **sha256**, edition, PDF and printed page, method (IMAGE_CHECKED / TEXT_LAYER_ONLY /
  COMPILATION_TEXT_LAYER / COMPILATION_FOOTNOTE_IMAGE_CHECKED / NOT_LOCATED / NOT_HELD), evidence ids (C12/C13 page rows,
  WSA-PIC, C9R readings) and the anchoring copy (HF preservation path and revision where it exists);
* `text_basis` (self-contained / composite with earlier versions / omitted), `text_status`, `conflicts`, `open_items`
  (alleged or unlocated instruments are **open items, never versions**), `currency` (always NOT_ESTABLISHED with the chain gaps).

**Never assume the latest text governs.** `validate_versions_c13.resolve_at(records, family, provision, date)`
(remediated after independent review R-01..R-03) returns a status and reasons, never a default "latest" version:

* `NOT_YET_IN_FORCE` - the date precedes the earliest possible start of the first version: its stated commencement, or else
  the creating instrument's own date (assent/notification or publication), lowered only by a stated retrospective date.
  E.g. BNS in 1990, AFT s.9A in 2010 (Finance Act 2017), AA s.169A in 1990 (Act 37/1992), r.59A in 1950.
* `IN_FORCE_CANDIDATES` - at least one non-excluded version has an established start on or before the date (stated
  commencement, or a stated retrospective deemed date such as S.R.O. 216/1988 deemed from 04-06-1979, with AQ-06 noted);
  every version that cannot be excluded is listed. E.g. r.22 in 2000 -> v02 (S.R.O. 17(E)/1993); r.16A in 1985 -> v01 and v03.
* `UNDETERMINED` - versions are possible but none has an established start on or before the date (commencement not stated,
  compilation-reported only, or instrument not held): **no candidate is returned**; possible versions are listed with reasons.
  E.g. r.15 in 2000 (S.R.O. 205/1961 prints no commencement); BNS/BNSS/BSA on 30 June and 1 July 2024 (S.O. 848-850(E) not
  held; the reason notes when the compilation-reported 01-07-2024 is after the date); AA s.127 in 2000 (both the section and
  its 1992 omission stay open, AQ-05).
* `NO_VERSION_IN_FORCE` - omitted/repealed by a version with an established start (e.g. r.25 after 06-12-1993).

A version is never placed before its creating instrument's date unless the instrument states a retrospective date (R-03:
the 1992 omissions of AA ss.75, 76, 127 and Chapter XVI are excluded for 1960 and 05-09-1992). The governing date axis is
always `NOT_DETERMINED`.

### Coverage (measured)

| Family | Provisions | Versions | Notes |
| --- | ---: | ---: | --- |
| Army Rules 1954 (AR1954) | 136 | 209 | all 108 cited rules; every rule with a located event; priority rr.15, 22, 23, 24, 25, 180 |
| Army Act 1950 (AA1950) | 127 | 163 | all 110 cited sections; every section in the WS-A chain (incl. Chapter XVI) |
| AFT Act 2007 / Procedure Rules 2008 | 24 + 1 | 32 + 2 | s.9A 2017/2021/2026, s.6(3)(a) RDO 2008, cited sections |
| BNS / BNSS / BSA 2023 | 3 / 6 / 55 | 3 / 6 / 55 | commencement (compilation-reported 01-07-2024), cited sections |
| IPC 1860 / CrPC 1973 / IEA 1872 | 1 / 1 / 1 | 2 / 2 / 2 | repeal with savings |
| CCCM Rules 1978, ISO Act 2023 | 1 / 1 | 2 / 1 | S.O. 4010 date dispute preserved |
| RA 1987, DSR, PRA 2008/1961, ER 1982/2008/2023, GMO 2023 | 10 | 10 | instrument level only (texts not held) |
| **Total** | | **488** | |

Text status: IMAGE_CHECKED 137, TEXT_LAYER_ONLY 63, COMPILATION_ONLY 246, NOT_HELD 23, CONFLICTING 6, OMITTED 13.
Effective-from: stated 67 (62 + 3 deemed + 2 with a date from an inferred masthead, R-07), NOT_STATED_PENDING_ADVICE 165, compilation-reported 215, not determined 20,
instrument not held 19, disputed 1, unknown 1. Effective-to: ends on next version 61 (date known) + 61 (date not
determined), open on located instruments 349, ceased (omitted/repealed) 17. 436 of 488 records need legal review.
Full counts: `outputs/VERSION_COVERAGE_C13.json` (including the version list for each priority rule).

Not modelled: Army Rules appendices/forms (A6 scope); Army Act Bills and repeals of spent amending Acts (no text change);
regulations and pension instruments beyond instrument level (not held); Air Force Act and Navy Act (outside the A4 priority
list); the restricted RM-001 item and its derived text and metadata are excluded from every input and output (see section 6).

`outputs/CRIMINAL_LAW_TRANSITION_LINKS_A4.csv` lists Army Act provisions that refer to the old codes (as recorded in
image-checked WS-A rows) with the successor code; the provision-level mapping is `NOT_DETERMINED` (questions A4-LQ-XREF-01..03).

## 2. Evidence improvement on the 983 citation items

`tools/build_evidence_c13.py` imports the reviewed C12F-v1.1 engine **unchanged** and re-runs it with
`inputs/page_evidence_c13.csv`: **21 new page-image checks** (18 pages of the 1954 Gazette, printed pp.307-316 and
323-330; S.R.O. 17(E)/1993 pp.15-17), rendered at 110 dpi from the **HF preservation copies** (revision 5524c3d9, sha256
verified) and read on the image. Every row passes the engine's checks (copy hash, text-layer probes, heading-index /
page agreement, page ranges). A stricter C13 gate keeps a new promotion only if every 1954 page behind every cited rule is
image-checked. `tools/render_pages_c13.py --verify` reproduces all 21 render hashes (also identical to the C12 hashes for
the two pages both cycles rendered).

| Evidence state | Baseline (C5/C10) | C12F-v1.1 (proposed) | **C13 A4 (proposed)** | Change vs C12F |
| --- | ---: | ---: | ---: | ---: |
| EXACT_ANCHOR | 42 | 99 | **109** | +10 |
| PARTIAL_MATCH | 652 | 595 | **585** | −10 |
| MISSING_EVIDENCE | 289 | 289 | **289** | 0 |

The 10 proposals (`outputs/EVIDENCE_PROPOSALS_C13.csv`, C13A4-EP001..010) are court-martial procedure items whose only
C12F blocker was "no page evidence for the S.R.O. 17(E)/1993 item": CM-005, CM-018, CM-023, CM-024, CM-029 (2 items),
CM-SC-08, CM-CL-04, CM-CL-06, CM-CL-07 (rr.41-64, 96-133). No blocker rule was relaxed. No r.15, r.22, r.23, r.177 or r.182
item moved; no MISSING item moved; all 99 C12F EXACT items are retained. 19 more items gained page evidence without a state
change. Per-source breakdown: `outputs/BEFORE_AFTER_MATRIX_C13.csv`; per-item: `outputs/EVIDENCE_MATRIX_C13.csv`;
verification rows for the changed items: `outputs/VERIFICATION_CHANGED_ITEMS_C13.csv`.

Observations recorded with the checks: the 1993 text layer reads "rule 57 (2)" in item 11 (r.52(2A)) and "JlH" for r.118 in
item 24; the images read "rule 52 (2)" and "118" (image governs). The r.95 heading is printed on 1954 PDF p.33 but is absent
from the text-layer heading index; r.95 stays blocked (AR-039 / GAP-13).

Why the other items did not move (unchanged from C12F): r.22 (S.R.O. 258/2002), r.23 (C-01), r.15 (OQ-A-10/GAP-15),
r.177 (C-03), r.182 (SC4-01), inferred identities, missing paragraph locators, and Army Act / AFT / BNSS / BSA items for which
only government compilations are held.

## 3. Gaps and acquisition requests for A7

`outputs/ACQUISITION_REQUESTS_A4.csv`: 45 requests queued for A7; nothing fetched (status `QUEUED_FOR_A7`). Types: public
acquisition of pinned archive.org candidates (MD5 and size from the WS-A ACQ-03 register), discovery, registration of
copies already held, and custodian requests. Highest priority: S.R.O. 258/2002 (29 items); the source of r.15
"[or Military Secretary]" (6 items); E-7/1960; post-06-06-2022 instruments; the Army Act 1950 as enacted (190 items) and
S.R.O. 120/1950; S.O. 14(E)/2008 (AFT commencement); TRA 2026 commencement; S.O. 848/849/850(E) of 2024; registration of the
held AFT Procedure Rules (46 MISSING items); a custodian-certified r.23(3) (C-01); RA 1987; PRA 2008 / ER / GMO. Dependent
counts are reference-based (citation items whose blockers or source name the gap; version records whose open items,
evidence or currency name it). C12 WS-H found that archive.org redirects to storage nodes and egazette.gov.in TLS both block
fetches from the container: an allow-list decision by the owner is noted on each row.

## 4. Legal-adviser review packet

`outputs/ADVISER_REVIEW_PACKET_A4.csv` (96 entries) and `.md`: the 57 C12F promotions (with the C12 independent reviewer's
verdict), the 10 C13 promotions (not yet reviewed), 5 reserved wording conflicts (C-01, SC4-01, C-03, C-02, C-04/C-08/C-09),
r.135 scope, r.15B applicability, 2 alleged amendments (r.15, r.22), 3 commencement questions, retrospectivity (AQ-06), the
S.O. 4010 date dispute, the ER 2008 version identity, 7 temporal-axis questions and 7 cross-reference questions. Each gives
the exact question, the evidence, the competing readings, the affected records and the decision required, and links to the
existing AQ-STA-nn question where one exists. No legal conclusion is drawn.

## 5. Running

```
VENV=/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/venv/bin/python
cd legal_knowledge/audit_work/C13-A4-STATUTORY/tools
$VENV build_evidence_c13.py [--check]     # evidence rerun (needs the held copies, below)
$VENV build_versions_c13.py [--check]     # version model
$VENV build_packets_c13.py  [--check]     # acquisition requests + adviser packet
$VENV validate_versions_c13.py [--at AR1954 r.22 2000-01-01]
$VENV render_pages_c13.py --verify        # re-render the 21 page rows
$VENV sha256sums_c13.py --check
$VENV -m pytest -q ../../../../tests/test_legal_audit_c13_statutory_*.py
```

Held copies: the 48 HF preservation copies are expected under `$C13A4_HF_ANCHOR` (default
`scratchpad/c13/a4work/hf_anchor`, downloaded with `huggingface_hub.hf_hub_download` at the revisions in
`C12-CONSOLIDATION/copy_verification_c12/SOURCE_REGISTER_PRESERVATION_OVERLAY_C12.csv`; 48/48 sha256 verified on
2026-11-25). Copies outside the overlay (India Code compilations) come from the C5 held paths. The tools link them into
`$C13A4_HELD_BASE` and hash-verify every file before use. Tested with CPython 3.13.18, PyMuPDF 2.1, jsonschema 4.26.0,
pytest 9.2.0 (the scratchpad venv; nothing installed). Another MuPDF build may change text or PNG bytes; `--check` and
`--verify` then report drift. The unchanged C12F engine still reproduces its own outputs byte-for-byte from this worktree
(`C12F_HELD_BASE=<scratchpad> build_c12f.py --check` -> CHECK OK, run 2026-11-25).

## 6. Restricted material

The restricted RM-001 item (single source of truth: `config/restricted_material.json` and `scripts/restricted_material.py`
on branch `claude/c13-gov`) - its PDF, derived text and metadata - is not read, cited, extracted or modelled. The identifiers
are mirrored in `tools/c13a4_common.py` (loaded from the config file too when it exists on the branch) and every output is
scanned before it is written; a hit stops the build. The regulations inventory row for that publication is not carried into
any output.

## 7. Review and change log

| Version | Change | Finding |
| --- | --- | --- |
| C13A4-v1.1 | Resolver statuses NOT_YET_IN_FORCE / IN_FORCE_CANDIDATES / UNDETERMINED / NO_VERSION_IN_FORCE; no candidate without an established start | R-01 (P1) |
| C13A4-v1.1 | Stated retrospective deemed dates open the deemed window | R-02 |
| C13A4-v1.1 | Creating instrument's date used as an exclusion floor; C9 instrument dates carried for AFT/graph edges | R-03 |
| C13A4-v1.1 | 25 boundary tests and negative controls (BNS 1 July 2024, AFT s.9A, AA s.169A, rr.13A/15A/59A, r.16A/r.2 deemed window, 1992 omissions) | R-04 |
| C13A4-v1.1 | Record count: commit 47ffc4a9's message says 490; the correct count is 488 (two duplicates were removed before 5db80dfc) | R-05 |
| C13A4-v1.1 | A4-ADV-077 adds the date-of-assent reading for Act 37/1992 as a question; category-specific decision wording | R-06 |
| C13A4-v1.1 | `STATED_IN_INSTRUMENT_DATE_FROM_INFERRED_MASTHEAD` qualifier (AFT s.41 v02, AFT Procedure Rules 2008) | R-07 |
| C13A4-v1.1 | Multi-page rules list every page row in evidence_ids | R-08 |
| C13A4-v1.1 | C13PE-1993-16 check_note records the pasted-fragment scan artefact | R-10 |
| C13A4-v1.2 | NOT_YET_IN_FORCE uses the earliest possible start of any version (stated retrospective dates included): r.16A 04-06-1979 to 27-07-1979 returns v03 | N-01 |
| C13A4-v1.2 | Resolver reason keeps the inferred-masthead qualifier | N-02 |
| C13A4-v1.3 | Repository provenance gate: acquisition status `QUEUED_FOR_A7`; transition-link rows carry the WS-A check id and render hash (WSA-PIC-27) behind IMAGE_CHECKED | gate ACQ-1, IMG-2 |

Review records: `reviews/review_c13_a4_5db80dfc.md`, `_findings.csv` and `reviews/confirmation_c13_a4_fa8715fa*` (verdict ACCEPT WITH CONDITIONS; all 21 page
readings confirmed and all 10 promotions upheld; R-09, R-11 to R-13 informational).

## 8. Limits

* Image readings are by an AI agent, not human-confirmed; the 21 C13 page rows need an independent re-read.
* EXACT_ANCHOR is citation-level only and does not authenticate the archival facsimiles, establish currency after the
  located instruments, commencement of silent instruments, or legal applicability.
* Army Act, AFT Act, BNSS and BSA section texts are compilation-only; their versions carry compilation page leads, not anchors.
* The version model is compiled from reviewed registers; where registers are silent, the record is silent (null + status).
