# ARMY-RULES-CHAIN-01: Army Rules 1954 amendment-instrument register and provision chronology (review proposal)

**Status: research proposal. No legal determination is approved. Rule 23(3) remains CONFLICTING; Rule 194 remains a PROPOSAL; Rule 193 is OPEN (new discrepancy U-04).**

The register is built from the Gazette instruments themselves, **not** from the "previous S.R.O.s" notes or compilation footnotes. Those notes are inconsistent (see `official_note_discrepancies.csv`) and omit at least five amending instruments.

| File | Content |
| --- | --- |
| `army_rules_instrument_register.csv` | 37 rows: the principal notification, every amending instrument located or alleged, r.188(e) declarations wrongly listed as amendments, unchecked hints and gaps |
| `army_rules_provision_chronology.csv` | 46 provision-level events: inserted, substituted, amended, omitted, corrigendum. Commencement as printed and temporal notes are recorded separately from instrument and publication dates |
| `official_note_discrepancies.csv` | 10 inconsistencies in official amendment notes |
| `statutory_version_register_seed.csv` | Seed of the proposed authoritative version register (12 rows), for the provisions in conflict or under review; r.193 = C-08, r.194 = C-09 |
| `page_image_checks_chain.csv` | PIC-30..36: continuation pages previously read only from the text layer, now image-checked (S.R.O. 205/1961 pp.142-143 and blank p.144; 5/1968 p.10; 278/1985 p.532; 188/1979 pp.259-260) |
| `check_registers.py` | Deterministic cross-reference and date-semantics check (run in CI proposal) |

## Completeness (as of 2026-11-22)
| State | Count | Rows |
| --- | --- | --- |
| Located, operative page image-checked | 26 | AR-000, 006–011, 014, 016–029, 031, 033–035 |
| Located from text layer only (OCR), image check outstanding | 5 | AR-002–005 (S.R.O. 331, 348, 351, 404 of 1960), AR-032 (S.R.O. 22/2010) |
| Full-text-search hints, not yet opened | 3 | AR-012 (1966), AR-013 (1967), AR-015 (1974) |
| Not found | 2 | AR-001 E-7/1960; AR-030 S.R.O. 258/2002 |
| Not searched authoritatively | 1 | AR-036 (after 06-06-2022; egazette.gov.in unreachable from here) |

Of the located rows, two (AR-008 S.R.O. 34/1963 and AR-033 S.R.O. 2(E)/2018) are r.188(e) declarations, not amendments.
One row (AR-029, S.R.O. 17(E)/1993) still needs each affected rule itemised.

## Rules followed
- Wording relied on comes from page images. Rows from the text layer only are labelled and are not used for any legal determination.
- **Dates are distinct:** `publication_date` (Gazette issue), `commencement_as_printed` (copied from the instrument) and `effective_date`. `effective_date` is filled only when the instrument states its commencement; otherwise it is null with an explicit `effective_date_status` (`NOT_STATED_PENDING_ADVICE (AQ-05)`, `NOT_DETERMINED`, `NOT_APPLICABLE`, `UNKNOWN`). A publication date is never used as an effective date.
- **Continuation pages:** `continuation_pages_status` is `ALL_IMAGE_CHECKED` only when every operative page relied on was image-checked. Otherwise it is `REQUIRES_VERIFICATION`: the 5 OCR-only instruments, and S.R.O. 17(E)/1993 until WS-A itemises it.
- Compilation text is used only as a comparison (SOURCE_AUTHORITY_POLICY v1). It never overrides a located Gazette instrument, and a disagreement is recorded rather than resolved.
