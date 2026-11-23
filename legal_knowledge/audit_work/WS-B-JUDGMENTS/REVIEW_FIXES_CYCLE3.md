# WS-B cycle 3: review fixes for PR #26 (two Codex P2 findings, owner-verified)

**Regression check:** `tools/check_cycle3_fixes.py` (stdlib only; it lives in this directory because `tests/` is leased to WS-D). It exits 0 when both findings stay fixed.

**Scope:**
- Nothing was downloaded.
- The intern corpus and the curated originals were not modified.
- Only files under `WS-B-JUDGMENTS/` changed.

## F1: citation-lead PDF pages were shifted by one

**Defect.** `tools/cycle3_citescan.py` already produces one-based PDF pages: it counts the `[[page N]]` markers before the match, and the markers start at `[[page 1]]`. `tools/cycle3_registers.py` then wrote `str(pg + 1)`, so every citation lead moved to the next page.

**Check written first.** The check builds a synthetic five-page text with the citation on page 1, page 3 and page 5. For each, it compares the scanner page and the register's `pdf_page` against an independently parsed marker number. A boundary case covers a citation that appears before the first marker: the scanner returns 0, and the register must leave `pdf_page` blank rather than invent page 1.

**Result on the code as committed in `1f76f436` (before the fix):**
```
F1 register pdf_page 2 != 1 (citation on page 1)
F1 register pdf_page 4 != 3 (citation on page 3)
F1 register pdf_page 6 != 5 (citation on page 5)
```

**Minimal fix.**
- `cycle3_citescan.py` gains a documented helper `page_of(text, pos)`, which returns the one-based page or 0. The scan output is byte-identical to before.
- `cycle3_registers.py` writes `str(pg)`, or blank when the page is 0.
- The SCR headnote heuristic (`pg <= 4`) already assumed one-based pages, so it is unchanged.

**After:** the check passes. `subsequent_treatment_cycle3.csv` was regenerated.
- 77 citation-lead rows have `pdf_page` reduced by 1. Apart from the two new columns added to every row (`printed_page_if_verified`, `page_render_sha256`), no other column changed in those rows.
- Every changed row is listed in `review_fix_cycle3_corrected_rows.csv`, with its before and after value.
- `citation_scan_summary_cycle3.csv` is unchanged, since it holds counts only. No other register cites these pages.

**Page-image verification of corrected leads.** I extracted the intern mirror PDFs read-only from `origin/raw-data` and rendered the corrected pages at 110 dpi:

| Row | Citing document (mirror sha256) | Corrected pdf_page | Printed page | Render sha256 | Seen on image |
| --- | --- | --- | --- | --- | --- |
| WSB-T3-005 | Bijender Singh 2025 (`0831eb71…`) | 2 | [2025] 4 SCR 1551 | `93238c41…12f2` | "Union of India v. Angad Singh Titaria [2015] 2 SCR 524 : (2015) 12 SCC 257" in the Case Law Cited list |
| WSB-T3-007 | Secretary, MoD 2009 (`28f88d53…`) | 3 | [2009] 13 (Addl.) SCR 418 | `91b2cf98…6ccf` | "Controller of Defence Accounts (Pension) & Others v. S. Balachandran Nair (2005) 13 SCC 128, referred to." |
| WSB-T3-046 | EEVFAM 2016 (`15e63a38…`) | 11 | [2016] 4 SCR 919 | `43bcea02…67c8` | "State (NCT of Delhi) v. Navjot Sandhu (2005) 11 SCC" at the foot of the page |

- The PDF page and the printed reporter page differ, so they are now separate columns: `pdf_page` and `printed_page_if_verified`. The render hash is in `page_render_sha256`.
- In all three samples the citation sits in the SCR headnote or case list. The rows stay `CITED_TREATMENT_NOT_CLASSIFIED`, because an editorial label is not evidence of treatment.

## F2: network-log parser treated the content type as part of the status

**Defect.** The lookup TSV stores the HTTP status (column 5) and the content type (column 6) as separate fields. `authoritative()` kept the status in `res` and the content type in `extra`, but then tested `res.startswith('200') and 'application/pdf' in res`. As a result, BUTTAR's `200` with `application/pdf` was classified as inconclusive.

**Check written first.** It runs `authoritative()` on a temporary log containing:
- BUTTAR: 200, application/pdf;
- KULDEEP: 404, text/html;
- a boundary case: 200, text/html;
- a control line.

It asserts that:
- BUTTAR is classified as a responding PDF URL;
- the 404 stays inconclusive;
- 200 with text/html is not classified as a PDF;
- no row reports `official_copy_held` other than NO;
- the responding-URL state says explicitly that identity, authenticity and acquisition are not established.

**Result before the fix:**
```
F2 BUTTAR 200 application/pdf classified as OFFICIAL_HOST_URL_HEAD_INCONCLUSIVE (HEAD 404 also returned for control URL whose bytes were previously obtained)
```

**Minimal fix.**
- `parse_netlog_line()` parses the status, content type and headers independently.
- `classify_head(status, content_type)` returns one of:
  - `OFFICIAL_HOST_URL_RESPONDS_200_PDF (availability only; identity, authenticity and acquisition NOT established; bytes not held)`;
  - `..._RESPONDS_200_NOT_PDF`;
  - `..._HEAD_INCONCLUSIVE`.
- The planned state name `..._RESOLVES_TO_PDF_BYTES_NOT_HELD` was renamed so that the state describes availability only. The check was updated to the new name.

**Priorities in the pending queue.**
- Before, the queue treated the curated "L" prefix as P0, which wrongly made Buttar (L06) a P0 case.
- Priority now comes from:
  1. the explicit list of the 11 P0 cases in issue #4;
  2. then HTTP availability: P1 when an official PDF URL responds;
  3. otherwise P2.
- A boundary case in the check asserts that Buttar is not P0.
- A new column, `official_url_http_check`, records the HTTP result separately from priority, identity and acquisition.

**After:** the check passes. `authoritative_copy_status_cycle3.csv` and `pending_acquisition_cycle3.csv` were regenerated:
- BUTTAR's state is now `OFFICIAL_HOST_URL_RESPONDS_200_PDF …`. `official_copy_held` stays NO.
- PQ-C3-21 (BUTTAR) moves from P0 to P1.
- For the other 10 HEAD rows, only the field formatting changed (`status=404 content_type=text/html`). Their state is still inconclusive.
- Counts of `official_url_http_check`: 16 no official URL located, 10 HEAD inconclusive, 1 responds 200 PDF, 5 not checked.

**Not affected:** the 11 pairs of HEAD requests already recorded in CR-C3-02 (`corrections_cycle3.csv`) and `network_lookup_log_cycle3.csv`.

## Gates
Each gate's exit code was checked directly before the commit:
- unittest;
- PILOT-01 strict and R23-VERIFY-01 strict validation;
- `check_registers.py`, `check_csv.py`, `check_provenance.py` (0 new violations);
- `tools/check_ws_b.py`;
- `tools/check_cycle3_fixes.py`;
- `cases_53` SHA-256 `8b8d53cd…`.


## Final Cycle 3 reconciliation (owner instruction; branch claude/ws-b-cycle3-reconcile, base 2a66cd04)
No host was contacted. Nothing was downloaded. No legal determination was made.

**New checks in `tools/check_ws_b.py`:**
- **Holder/source check.** Fails if any CSV column naming a holder, source, URL, copy, carrier or official target contains indiankanoon, casemine, scconline, "SCC Online" or manupatra.
  - Exception: a `curated_*` column may reproduce the frozen original verbatim, but only when the same row's `discrepancies` field flags it as "commercial database ... not evidence".
- **Completeness check.** Fails if any identity in `identity_resolution.csv` without a held official copy lacks a row in `pending_acquisition_cycle3.csv`.
  - Rows are keyed by the stable `spec_key`.
  - It also checks each queue row's states (ACQUISITION_REQUEST_ONLY, NOT_APPROVED, downloaded_by_ws_b = NO) and rejects duplicates.

**Before** (`check_ws_b.py` on 2a66cd04, exit 1):
```
COMMERCIAL DATABASE AS HOLDER/SOURCE pending_acquisition_cycle3.csv PQ-C3-32 official_url_or_holder_if_known https://indiankanoon.org/doc/925325/
UNRESOLVED IDENTITY WITHOUT CYCLE-3 QUEUE ROW INDER_JIT CITATION_METADATA_CORROBORATED_BY_OFFICIAL_RECORD_NO_COPY
UNRESOLVED IDENTITY WITHOUT CYCLE-3 QUEUE ROW CHANDRA_KUMAR CITATION_METADATA_CORROBORATED_BY_OFFICIAL_RECORD_NO_COPY
UNRESOLVED IDENTITY WITHOUT CYCLE-3 QUEUE ROW SODHI CITATION_METADATA_CORROBORATED_BY_OFFICIAL_RECORD_NO_COPY
UNRESOLVED IDENTITY WITHOUT CYCLE-3 QUEUE ROW ROJER CITATION_METADATA_CORROBORATED_BY_OFFICIAL_RECORD_NO_COPY
UNRESOLVED IDENTITY WITHOUT CYCLE-3 QUEUE ROW RAM_AVTAR CITATION_METADATA_CORROBORATED_BY_OFFICIAL_RECORD_NO_COPY
UNRESOLVED IDENTITY WITHOUT CYCLE-3 QUEUE ROW SHAFHI CITATION_METADATA_CONFLICTS_WITH_OFFICIAL_RECORD_NO_COPY
UNRESOLVED IDENTITY WITHOUT CYCLE-3 QUEUE ROW RAM_SARUP CITATION_METADATA_CONFLICTS_WITH_OFFICIAL_RECORD_NO_COPY
UNRESOLVED IDENTITY WITHOUT CYCLE-3 QUEUE ROW MANI_RAM CITATION_METADATA_CORROBORATED_BY_OFFICIAL_RECORD_NO_COPY
UNRESOLVED IDENTITY WITHOUT CYCLE-3 QUEUE ROW SOM_DATT IDENTITY_CORROBORATED_INTERN_MIRROR_ONLY
UNRESOLVED IDENTITY WITHOUT CYCLE-3 QUEUE ROW BALBIR CITATION_METADATA_CORROBORATED_BY_OFFICIAL_RECORD_NO_COPY
UNRESOLVED IDENTITY WITHOUT CYCLE-3 QUEUE ROW ADG_CBI CITATION_METADATA_CORROBORATED_BY_OFFICIAL_RECORD_NO_COPY
UNRESOLVED IDENTITY WITHOUT CYCLE-3 QUEUE ROW SONU CITATION_METADATA_CORROBORATED_BY_OFFICIAL_RECORD_NO_COPY
UNRESOLVED IDENTITY WITHOUT CYCLE-3 QUEUE ROW SANDEEP_SHARMA UNRESOLVED_NO_COPY_IN_HAND
UNRESOLVED IDENTITY WITHOUT CYCLE-3 QUEUE ROW SANTOSH_LOHAR IDENTITY_LEAD_INTERN_METADATA_ONLY
UNRESOLVED IDENTITY WITHOUT CYCLE-3 QUEUE ROW PANDAPPA IDENTITY_CORROBORATED_INTERN_MIRROR_ONLY
UNRESOLVED IDENTITY WITHOUT CYCLE-3 QUEUE ROW SUKHDEV UNRESOLVED_NO_COPY_IN_HAND
UNRESOLVED IDENTITY WITHOUT CYCLE-3 QUEUE ROW NITISHA_MA UNRESOLVED_NO_COPY_IN_HAND
UNRESOLVED IDENTITY WITHOUT CYCLE-3 QUEUE ROW INSC_2023_985 UNRESOLVED_NO_COPY_IN_HAND
UNRESOLVED IDENTITY WITHOUT CYCLE-3 QUEUE ROW INSC_2026_281 UNRESOLVED_NO_COPY_IN_HAND
UNRESOLVED IDENTITY WITHOUT CYCLE-3 QUEUE ROW HARJEET IDENTITY_CORROBORATED_INTERN_MIRROR_ONLY
UNRESOLVED IDENTITY WITHOUT CYCLE-3 QUEUE ROW NALIN UNRESOLVED_NO_COPY_IN_HAND
UNRESOLVED IDENTITY WITHOUT CYCLE-3 QUEUE ROW POOJA_PAL UNRESOLVED_NO_COPY_IN_HAND
UNRESOLVED IDENTITY WITHOUT CYCLE-3 QUEUE ROW JOGINDER_HP CITATION_METADATA_CORROBORATED_BY_OFFICIAL_RECORD_NO_COPY
FAIL
```

**After:** `check_ws_b.py` exits 0 and prints OK. `check_cycle3_fixes.py` also passes.

**Item 1, CF-WSB-PQ-C3-32 (Ranjit Thakur review order)**
- PQ-C3-32's `official_target` now reads: "official Supreme Court of India copy required; no official URL located (a commercial database URL was previously recorded in the curated record - it is not a source or holder)".
- The row's `note` records that https://indiankanoon.org/doc/925325/ was listed before and has been removed.

**Items 2 and 3, the consolidated acquisition queue**
- `pending_acquisition_cycle3.csv` now has one row per unresolved `spec_key`: 55 rows, up from 32.
- PQ-C3-01 to PQ-C3-32 keep their ids. PQ-C3-33 to PQ-C3-55 are new and include HARJEET (PQ-C3-52) and PANDAPPA (PQ-C3-47).
- Separate fields now record:
  - identity status and identity uncertainty;
  - `official_copy_held` (always NO);
  - `mirror_copy` (intern doc id and SHA-256, marked not official);
  - `official_target`, which is never a commercial database. Ram Avtar's wrong-document URL is flagged rather than used as a target;
  - `official_url_http_check` (availability only);
  - `dependent_kb_records` (code-declared links vs lexical leads);
  - `prior_queue_ids` (cycle 1–2 rows);
  - `approval_state` = NOT_APPROVED and `downloaded_by_ws_b` = NO.
- **Priority rule, applied to every row:**
  1. P0 for the 11 P0 cases in issue #4;
  2. otherwise P1 if an official PDF URL responds, or the case has a code-declared KB dependency;
  3. otherwise P2.
- **Priority changes on existing rows:** PQ-C3-03, 04, 07, 08, 09 and 10 move P2 → P1. PQ-C3-29, 30 and 32 move P1 → P2. PQ-C3-31 (Dhingra, an issue-#4 P0 case) moves P1 → P0.

**Item 4, known inconsistencies**
- `open_inconsistencies_cycle3.csv` lists 13 OPEN items where official copies, mirror copies, curated records and transcribed text disagree.

**Other registers:** no other cycle-3 register changed. The generated output was byte-compared before and after.

**Unit-test gate (not caused by WS-B).**
- `python3 -m unittest discover -s tests -p 'test_legal_audit_*.py'` exits 1 with 2 failures:
  - `test_legal_audit_versioned_edges.test_inputs_pinned_and_current`
  - `test_legal_audit_versioned_edges.test_regeneration_is_byte_identical`
- Both fail identically on the untouched base 2a66cd04. The message is "input version_register changed - regenerate versioned edges", which follows PR #28's change to ARMY-RULES-CHAIN-01.
- The fix is outside the WS-B lease (WS-D `tests/` and the `scripts/` edge builder). It is reported to the coordinator.
- No WS-B change touches those inputs.
- All other gates exit 0.
