# WS-C-MML status (issue #13)

**Research proposal only. Nothing here is legal-advisor adjudicated or JAG validated. Fixed determinations unchanged: r.23(3) CONFLICTING; r.193 = C-08 OPEN; r.194 = C-09 PROPOSAL.**

## Done
- Commit 1: `input_manifest.json` (8/8 originals re-hashed = manifest), `mml_edition_status.csv` (8 files), `page_image_checks_wsc.csv` (WSC-PIC-01..13, incl. coordinator task MML 2 p.227 r.193/r.194), `provision_index.csv`, `mml1_para_index.csv`, `mml_provision_crosswalk.csv` (847 rows), `open_questions.csv`, scripts.

## In progress / next
- DONE commit 2: `kb658_source_coverage_inventory.csv` (658/658 rows) + `scripts/build_kb658_inventory.py` (stdlib, deterministic, re-run byte-identical) + `kb658_coverage_summary.json`. FULL 379, PARTIAL 131, SOURCE_GAP 56, UNRESOLVED 14, NO_CITATION 78 (denominator 658). Source-coverage only; no correctness verdicts.
- DONE commit 3: `procedure_gap_conflict_register.csv` (17 rows; 15 image-checked or rendered, 2 text-only marked REQUIRES_VERIFICATION), `candidate_corrections.csv` (14 proposals, none applied), `page_image_checks_wsc.csv` extended to WSC-PIC-28; provision index fixed for suffix headings such as r.80A.
- `calibration_sample_ranked.csv`

## Blockers
- None blocking. Edition authentication (OQ-C-04) and cover pages (OQ-C-03) need the owner.

## Requests to other workstreams (via coordinator)
- WS-A: itemise S.R.O. 17(E)/1993 for r.193 (OQ-C-06). MML 2 p.227 footnote attributes r.193 to that instrument (WSC-PIC-10); this is evidence only.
