# STATUTORY_C9_FINDINGS (Cycle 9, statutory-source agent)

Every page reading cited is by an AI agent (Claude Opus 5.5 subagent), not human-confirmed. No legal status, applicability or commencement date is determined or inferred; compilation footnotes and 'w.e.f.' notes are recorded as compiler statements only.

Built on the reviewed C8-SOURCES baseline (snapshot 2d7c02cf) and the C8-EVIDENCE Gazette tranche. Regenerate everything with `python3 -I tools/build_stat_c9.py <repo> --evidence-repo <c8ev> [--check]`. The inputs are regenerated with `tools/extract_branch_pins.py` and `tools/collect_readings_c9.py`, both of which have `--check` modes.

## 1. Baseline metrics (re-verified)

All figures reproduce from the files: 658 KB records; 53 cases; 1,060 crosswalk rows = 983 citation items + 77 NO_CITATION; 42 exact / 652 partial / 289 missing; 618 records with no exact anchor (541 cite something, 77 cite nothing); 10 all-exact and 30 some-exact; cases 6/7/40. All 42 anchors rest on one copy (C5-SRC-P0-ARMY-RULES-1954~C1, sha256 c5ef95a9...). Details and method: `baseline_metrics.json` (all_match = true).

## 2. Principal new findings

1. **The corpus raw store was outside C8's gap analysis.** `origin/raw-data` @ad77758d (approved India Code run, 2026-11-21) already holds the AFT Act 2007 as published, the AFT Procedure Rules 2008, the Amendment Rules 2011 and the Practice Rules 2009, the Finance Act 2017, TRA 2021, the BNS, DPP Act, Air Force Act and Navy Act compilations, and IPC/IEA/CrPC renderings. Ten C8 statements of 'not held' are corrected (see each instrument record). The acquisition need for the AFT Act (89 records) and the AFT rules (43 records) becomes a **registration** need.
2. **Two AFT instruments are in no register:** the Removal of Difficulties Order 2008 (amends s.6(3)(a); EVIDENCED from 21-07-2008) and S.R.O. 9(E)/2009 (Tribunal established w.e.f. 10-08-2009, the appointed day). S.O. 14(E)/2008 (s.1(2)) is still not held.
3. **TRA 2021:** deemed in force 04-04-2021; s.26 amends AFT s.9A. Both EVIDENCED from the corpus copy.
4. **New text discrepancy:** in r.168(2), the compilation still prints field-punishment words that S.R.O. 17(E)/1993 item 31 omits. This is in no conflict register (C9-AG-AR168).
5. **S.O. 4010/1986:** the Rajya Sabha page reads '6th December, 1986', not '8 Dec' (C5 RV-01). The PILOT-01 date 24-11-1986 is preserved as the other reading.
6. **PR #9 does list GMO 2023** (C8 said it did not), with byte sizes only and no hash. PR #23's 3 India Code pins are redundant with the raw store. All 16 PR #17 pins and 9 PR #8 pins are md5-identical to research copies already held.
7. **Provenance lead:** 7 held compilation copies classed PROVENANCE_UNDOCUMENTED match raw-data files that carry retrieval records (owner decision; not authentication).
8. The 1992 'w.e.f. 6-9-1992' printing is confirmed only at ss.75-76, s.127 and Ch XVI. The 2024 commencement notifications are confirmed as three distinct S.O.s (850/848/849(E)), with different exceptions.

## 3. Ranked documentary requirements (dependent KB records, gross and overlapping; from C8 gap rows)

| rank | requirement | dependent KB records | state | authorisation |
| --- | --- | --- | --- | --- |
| 1 | Army Act 1950 Gazette as enacted | 185 | PINNED metadata only; needs a new config PR | A-C5-1 (AP-C9-03) |
| 2 | Army Rules chain: post-2022 S.R.O.s, E-7/1960, S.R.O. 258/2002, hints | 122 | 10 metadata pins (no PR); 2 need custodian/Indian network; hints in PR #23 | A-C5-1, PR #23, A-C5-3 |
| 3 | AFT Act 2007 as published | 89 | ALREADY HELD (corpus raw) - registration only | AP-C9-02 (no download) |
| 4 | BSA 2023 Gazette | 64 | PINNED metadata only | A-C5-1 |
| 5 | BNSS 2023 Gazette | 49 | PINNED metadata only | A-C5-1 |
| 6 | AFT Procedure/Practice Rules 2008/2009/2011 | 43 | ALREADY HELD (corpus raw) - registration only; Practice Rules masthead via ACQ03-032 | AP-C9-02 |
| 7 | PRA 2008 Part I | 25 | BLOCKED (robots 403) | A-C5-2 (AP-C9-06) |
| 8 | BNS 2023 Gazette (compilation already held) | 12 | PINNED metadata; compilation held raw | A-C5-1; AP-C9-02 |
| 9 | GMO 2023 | 11 | BLOCKED; listed in PR #9 without hash | A-C5-2 |
| 10 | PRA 2008 Part II | 9 | BLOCKED | A-C5-2 |
| 11 | CCCM Rules 1978 + S.O. 4010/1986 | 8 | AUTHORISED SCOPE (PR #8) - execution pending | AP-C9-01 |
| 12 | BNS/BNSS/BSA commencement notifications | 1 | PINNED metadata only (upper bound 114 records) | A-C5-1 |
| 13 | AFT commencement S.O. 14(E)/2008 (upper bound 89) | 0 | NO CANDIDATE | discovery (AP-C9-05) |
| 14 | Army Act commencement S.R.O. 120/1950 (upper bound 185) | 0 | candidate in PR #23 | PR #23 |

The counts overlap and cannot be added. Acquiring an enacted text does not by itself clear a record whose provision was later amended.

## 4. Acquisition-ready (existing approval) vs new approval

- **Ready under existing scope:** 14 PR #8 documents (ACQ-01 B1/B2/B6, owner-authorised 2026-11-22), listed in `acquisition_manifest_ready.csv`. Gates: PR #8 approval/merge and a logged download run.
- **New approval needed:** AP-C9-02 (registration, no download) to AP-C9-08. See `APPROVAL_PACKAGES.md`.

## 5. Amendment graph

116 edges: DISPUTED_PRESERVE_BOTH 15, EVIDENCED 17, NOT_LOCATED 43, UNRESOLVED_COMMENCEMENT 41. See `AMENDMENT_GRAPH_FINDINGS.md`.

## 6. Outputs

`instrument_records.csv` + `instruments/*.md` (111 records); `acquisition_reconciliation.csv/.md`; `acquisition_manifest_ready.csv`; `APPROVAL_PACKAGES.md`; `amendment_graph.csv`; `AMENDMENT_GRAPH_FINDINGS.md`; `UNRESOLVED_MATTERS.md`; `baseline_metrics.json`; `readings_index.csv`; `OUTPUT_SHA256SUMS`; `tools/` (builder, input extractors, inputs). Page renders viewed during reading are not retained; each render sha256 in `readings_index.csv` is recomputed deterministically by `tools/collect_readings_c9.py`.

## 7. Limitations

- Readings are AI-agent readings and need human re-check from the recorded render hashes before any approval.
- The raw-data blobs were read in memory from the local ref. They are unregistered, and their authenticity is not established.
- The PR refs are local and may lag the remote. No network was used, nothing was downloaded, and no crawler, robots or config file was changed.
