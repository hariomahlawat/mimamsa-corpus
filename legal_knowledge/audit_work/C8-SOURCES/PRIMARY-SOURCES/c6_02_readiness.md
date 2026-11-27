# C8-D Task 4: C6-02 Gazette acquisition readiness (offline reconciliation)

Source: `c6_02_readiness.csv` (20 files). No network call was made. Checks used only committed metadata: the C6-02 batch register, C5 discovery candidates, the C5 acquisition register and the committed archive.org metadata snapshots (`ACQ-01/archive_org_metadata_snapshot.json`, `ACQ-02/archive_org_metadata_snapshot_acq02.json`), plus md5 values computed from the 67 held binaries (`tools/inputs/held_md5.csv`).

## Results

- **18 of 20 pinned** (md5 + bytes); 2 DPP Amendment Act 2000 items unpinned (file name, URL, md5, bytes missing).
- Pins reconcile with the C5 candidate rows: 18 md5 MATCH, 18 bytes MATCH.
- **None of the 20 identifiers is in a committed metadata snapshot** (the ACQ-01/ACQ-02 snapshots cover the held Army Rules Gazettes only), so the pins rest on the Cycle 5 discovery records alone. They can be cross-checked only at download time.
- **No expected md5 equals any held binary or any snapshot file**: none of the 20 documents is already held under another identifier. Compilations of the same Acts are held (Army Act, AFT Act, BNSS, BSA) but they are different documents and are not substitutes.
- `sha256` is missing for every row by design (computable only after download).

| candidate | publication | identifier | pin | reconciliation | held elsewhere | KB items on dependent sources |
| --- | --- | --- | --- | --- | --- | --- |
| C5C-001 | Army Act, 1950 (Act XLVI of 1950) as enacted | in.gazette.e.1950.306 | PINNED | C5 candidate md5 MATCH; C5 candidate bytes MATCH; acquisition_register pin MATCH | NO (expected md5 matches none of the 67 held binaries, none  | 190 |
| C5C-016 | Armed Forces Tribunal Act, 2007 (Act 55 of 2007) | in.gazette.central.e.2007-12-28.020 | PINNED | C5 candidate md5 MATCH; C5 candidate bytes MATCH; acquisition_register pin MATCH | NO (expected md5 matches none of the 67 held binaries, none  | 89 |
| C5C-018 | Bharatiya Nagarik Suraksha Sanhita, 2023 (Act 46 of 2023) | in.gazette.central.e.2023-12-25.250884 | PINNED | C5 candidate md5 MATCH; C5 candidate bytes MATCH; acquisition_register pin MATCH | NO (expected md5 matches none of the 67 held binaries, none  | 50 |
| C5C-019 | Bharatiya Sakshya Adhiniyam, 2023 (Act 47 of 2023) | in.gazette.central.e.2023-12-25.250882 | PINNED | C5 candidate md5 MATCH; C5 candidate bytes MATCH; acquisition_register pin MATCH | NO (expected md5 matches none of the 67 held binaries, none  | 64 |
| C5C-021 | BNSS 2023 commencement notification under s.1(3) | in.gazette.central.e.2024-02-24.252354 | PINNED | C5 candidate md5 MATCH; C5 candidate bytes MATCH; acquisition_register pin is batch-level (md5 6288ffbc08004bbe858e6c4450524dc2 / 393d0cd8277d823bfeb38) | NO (expected md5 matches none of the 67 held binaries, none  | 1 |
| C5C-022 | BSA 2023 commencement notification under s.1(3) | in.gazette.central.e.2024-02-24.252352 | PINNED | C5 candidate md5 MATCH; C5 candidate bytes MATCH; acquisition_register pin is batch-level (md5 6288ffbc08004bbe858e6c4450524dc2 / 393d0cd8277d823bfeb38) | NO (expected md5 matches none of the 67 held binaries, none  | 1 |
| C5C-023 | BNS 2023 commencement notification under s.1(2) | in.gazette.central.e.2024-02-24.252353 | PINNED | C5 candidate md5 MATCH; C5 candidate bytes MATCH; acquisition_register pin is batch-level (md5 6288ffbc08004bbe858e6c4450524dc2 / 393d0cd8277d823bfeb38) | NO (expected md5 matches none of the 67 held binaries, none  | 1 |
| C5C-004 | Possible Army Rules 1954 amendment / Army Act s.191 S.R.O. ( | in.gazette.central.e.2022-06-23.236757 | PINNED | C5 candidate md5 MATCH; C5 candidate bytes MATCH; acquisition_register pin is batch-level (md5 per item in discovery/C_candidates.csv C5C-004..013) | NO (expected md5 matches none of the 67 held binaries, none  | 0 |
| C5C-005 | Possible Army Rules 1954 amendment / Army Act s.191 S.R.O. ( | in.gazette.central.e.2022-12-21.241268 | PINNED | C5 candidate md5 MATCH; C5 candidate bytes MATCH; acquisition_register pin is batch-level (md5 per item in discovery/C_candidates.csv C5C-004..013) | NO (expected md5 matches none of the 67 held binaries, none  | 0 |
| C5C-006 | Possible Army Rules 1954 amendment / Army Act s.191 S.R.O. ( | in.gazette.central.e.2023-05-30.246170 | PINNED | C5 candidate md5 MATCH; C5 candidate bytes MATCH; acquisition_register pin is batch-level (md5 per item in discovery/C_candidates.csv C5C-004..013) | NO (expected md5 matches none of the 67 held binaries, none  | 0 |
| C5C-007 | Possible Army Rules 1954 amendment / Army Act s.191 S.R.O. ( | in.gazette.central.e.2023-06-12.246457 | PINNED | C5 candidate md5 MATCH; C5 candidate bytes MATCH; acquisition_register pin is batch-level (md5 per item in discovery/C_candidates.csv C5C-004..013) | NO (expected md5 matches none of the 67 held binaries, none  | 0 |
| C5C-008 | Possible Army Rules 1954 amendment / Army Act s.191 S.R.O. ( | in.gazette.central.e.2024-05-22.254308 | PINNED | C5 candidate md5 MATCH; C5 candidate bytes MATCH; acquisition_register pin is batch-level (md5 per item in discovery/C_candidates.csv C5C-004..013) | NO (expected md5 matches none of the 67 held binaries, none  | 0 |
| C5C-009 | Possible Army Rules 1954 amendment / Army Act s.191 S.R.O. ( | in.gazette.central.e.2024-08-31.256844 | PINNED | C5 candidate md5 MATCH; C5 candidate bytes MATCH; acquisition_register pin is batch-level (md5 per item in discovery/C_candidates.csv C5C-004..013) | NO (expected md5 matches none of the 67 held binaries, none  | 0 |
| C5C-010 | Possible Army Rules 1954 amendment / Army Act s.191 S.R.O. ( | in.gazette.central.e.2025-04-23.262667 | PINNED | C5 candidate md5 MATCH; C5 candidate bytes MATCH; acquisition_register pin is batch-level (md5 per item in discovery/C_candidates.csv C5C-004..013) | NO (expected md5 matches none of the 67 held binaries, none  | 0 |
| C5C-011 | Possible Army Rules 1954 amendment / Army Act s.191 S.R.O. ( | in.gazette.central.e.2025-05-08.262992 | PINNED | C5 candidate md5 MATCH; C5 candidate bytes MATCH; acquisition_register pin is batch-level (md5 per item in discovery/C_candidates.csv C5C-004..013) | NO (expected md5 matches none of the 67 held binaries, none  | 0 |
| C5C-012 | Possible Army Rules 1954 amendment / Army Act s.191 S.R.O. ( | in.gazette.central.e.2026-01-30.269859 | PINNED | C5 candidate md5 MATCH; C5 candidate bytes MATCH; acquisition_register pin is batch-level (md5 per item in discovery/C_candidates.csv C5C-004..013) | NO (expected md5 matches none of the 67 held binaries, none  | 0 |
| C5C-013 | Possible Army Rules 1954 amendment / Army Act s.191 S.R.O. ( | in.gazette.central.e.2026-06-24.273809 | PINNED | C5 candidate md5 MATCH; C5 candidate bytes MATCH; acquisition_register pin is batch-level (md5 per item in discovery/C_candidates.csv C5C-004..013) | NO (expected md5 matches none of the 67 held binaries, none  | 0 |
| C5C-020 | Bharatiya Nyaya Sanhita, 2023 (Act 45 of 2023) | in.gazette.central.e.2023-12-25.250883 | PINNED | C5 candidate md5 MATCH; C5 candidate bytes MATCH; acquisition_register pin MATCH | NO (expected md5 matches none of the 67 held binaries, none  | 12 |
| C5C-026 | Army and Air Force (Disposal of Private Property) Amendment  | in.gazette.central.e.2000-08-25.168 | NOT_PINNED | not reconcilable (no pin) | NOT CHECKABLE (no md5) | 0 |
| C5C-027 | Army and Air Force (Disposal of Private Property) Amendment  | in.gazette.e.2000.379 | NOT_PINNED | not reconcilable (no pin) | NOT CHECKABLE (no md5) | 0 |

## Post-download verification procedure (for use only after approval A-C5-1)

1. Before any request: confirm the owner approval reference and the stacked crawler-config PR; read archive.org robots.txt (must be RULES_PARSED and allow the path); data-node redirects only to `*.archive.org`, each with its own robots decision. Unpinned identifiers are not fetched.
2. Fetch into a new, empty quarantine directory, one file per identifier; record time, URL, final URL, status, bytes in the request log (log format v2).
3. Verify **bytes == expected_bytes** and **md5 == expected_md5** from this register; any mismatch: quarantine, do not register, report.
4. Compute **sha256**; check the PDF signature (`%PDF`) and that no other container format is present; record page count and text-layer class with the same profiler used for `held_binaries_manifest.csv`.
5. Check the sha256 against all held binaries (duplicate detection) and record any alias.
6. Page-image check of the masthead (Gazette issue, date, Part/Section, S.R.O./Act number) and of every operative page relied on; record render sha256 in a page-image-check register.
7. For the 10 possible Army Rules S.R.O.s: read the subject on the page image; record whether each amends the Army Rules (and which rules) or is unrelated; never infer from metadata.
8. For the three commencement notifications: transcribe the appointed date and any section-specific exception exactly; only then may a commencement date be entered, as STATED_IN_INSTRUMENT, with the page reference.
9. Add a reviewed source-authentication addendum row (copy-level provenance) before any copy is used for EXACT_ANCHOR; locators must pass the AUTH-LEDGER-02 strict parser.
10. Re-run the crosswalk build; report the movement of items from PARTIAL to EXACT separately for each source; do not change legal status or reserved states.

## Decision item P-C7-02-META (restated; not executed)

- **Question for the owner:** approve a metadata-only request route for the two unpinned DPP Amendment Act 2000 identifiers (`in.gazette.central.e.2000-08-25.168`, `in.gazette.e.2000.379`)?
- **Scope:** only `https://archive.org/metadata/<identifier>` for the two listed identifiers; JSON only (content-type exactly application/json), body cap 512 KB, no redirects followed, no document body ever requested; keep only `files[]` entries for the expected PDF (`name`, `size`, `md5`, `sha1`); zero or several matches = PIN_AMBIGUOUS (fail closed); robots must be RULES_PARSED and allow `/metadata/`; GET without prior 200 HEAD allowed for this route only (archive.org answers HEAD 405, as logged in `C6-PREP/discovery/c6_02_metadata_requests_v2.tsv`).
- **Implementation if approved:** a separately reviewed change to `SOURCE-LIBRARY-C5/tools/discovery_guard.py` with the mocked tests listed in `C7-PREP/WORKSTREAMS_READINESS.md`; the crawler is not touched.
- **Still required afterwards:** A-C5-1 for any download. Unpinned downloads are not acceptable.
- **Status:** NOT APPROVED, NOT EXECUTED. No network call was made in Cycle 8.
