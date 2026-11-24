# Acquisition reconciliation (C9-STAT)

Every page reading cited is by an AI agent (Claude Opus 5.5 subagent), not human-confirmed. No legal status, applicability or commencement date is determined or inferred; compilation footnotes and 'w.e.f.' notes are recorded as compiler statements only.

Source: `acquisition_reconciliation.csv` (one row per required document). Pending branches were read from locally present remote-tracking refs in `/home/user/c7` with `git show <ref>:config/sources.yaml` only (no fetch). Refs may lag the remote.

## Rows by reconciliation state

| state | rows |
| --- | --- |
| ALREADY_FETCHED_STAGING_SOURCE | 4 |
| ALREADY_HELD | 18 |
| AUTHORISED_ROUTE_PENDING_EXECUTION | 14 |
| BLOCKED | 11 |
| IN_PENDING_BRANCH | 52 |
| LOCATED_NOT_PINNED | 3 |
| NEEDS_CUSTODIAN_CORRESPONDENCE | 4 |
| NEEDS_CUSTODIAN_CORRESPONDENCE or Indian-network egazette | 2 |
| NEEDS_METADATA_PIN | 2 |
| NEEDS_OFFICIAL_SOURCE_DISCOVERY | 12 |
| NEEDS_OWNER_DECISION | 1 |
| PINNED_ARCHIVE_METADATA | 19 |

## Pending acquisition stack (local refs)

| PR | local ref commit | documents first introduced | research copy already held (md5-identical) | already in corpus raw store (same URL) |
| --- | --- | --- | --- | --- |
| PR #8 (ACQ-01) | 1b948727eeb3 | 14 | 9 | 0 |
| PR #17 (ACQ-02) | b8ee3176cfbb | 16 | 16 | 0 |
| PR #23 (ACQ-03) | 60715342b3f0 | 39 | 0 | 3 |
| PR #9 (DESW allow-list) | 97933ccf4e7d | 3 | 0 | 0 |
| staging (v2.5-staging) | 21e73b834876 | 4 | 0 | 4 |

- **PR #8** (`claude/acq-01-config`): 12 archive.org + 2 India Code documents. The owner authorised batches B1, B2 and B6 on 2026-11-22 (PROGRESS.md on that branch); the PR itself, and a download run, are still unapproved. 9 of its archive.org pins are byte-identical (md5) to research copies already held; S.O. 488/1978, S.O. 4010/1986 and the Act 19/1955 Gazette are not held.
- **PR #17** (`claude/acq-02-config`): all 16 pins are md5-identical to held research copies (they would create record copies with a retrieval log; they add no new text).
- **PR #23** (`claude/acq-03-config`): local ref is 60715342; COORDINATION/PROGRESS_REGISTER.md recorded c0e2a425 at time of writing - the later docs commit is on the branch. Its 3 India Code B5 pins (ACQ03-033..035) use the same bitstream URLs that the approved 2026-11-21 India Code run already fetched into the corpus raw store (raw-data); they are redundant. The archive.org AFT rules copies ACQ03-030..032 are independent second copies; ACQ03-032 may supply the Practice Rules masthead.
- **PR #9** (`claude/desw-allowlist` @97933ccf): lists ER 2023 (49.9 MB), the 13 MB ER 2023 copy and **GMO 2023** with byte sizes only (no hash). C8 said GMO 2023 is not in PR #9; on the local ref it is. DESW robots.txt returned 403, so it remains blocked (fail-closed).
- **Army Act 1950 as enacted** (archive.org in.gazette.e.1950.306, md5 68bcdd4e...) and the Batch A Gazettes (AFT, BNS, BNSS, BSA, the three 2024 notifications, 10 post-2022 S.R.O.s) are pinned only as metadata (C5/C6-02). They are in no configuration PR.

## Holdings C8 missed: corpus raw store

The corpus raw store `origin/raw-data` @ad77758d holds 67 statutory PDFs: 63 India Code files from the run approved 2026-11-21 (PROGRESS.md) and 4 official copies from other hosts, 3 of them correspondence tables (review LG-08) (`tools/inputs/rawdata_statutory_holdings.csv`). C8 counted only the scratchpad held binaries, so it missed these. Among them:
- AFT Act 2007 as published (Gazette Extraordinary No.66, 28-12-2007) - C9R-RD-AFT07-IMG [corpus raw store sha256 338d43addeaa14b7 p.1; render sha256 5cdf8ff7726f02f1] (crawl category 'rule', title 'AFT-Act2007': mislabelled);
- AFT (Procedure) Rules 2008 C9R-RD-AFTPR08-IMG2 [corpus raw store sha256 590cf7cd393564ea p.23; render sha256 8467a704581bf208], Amendment Rules 2011 C9R-RD-AFTPR11-IMG2 [corpus raw store sha256 fc27032fadfe44fd p.2; render sha256 a9fc6364bb179d12], Practice Rules 2009 C9R-RD-AFTPRAC09-IMG [corpus raw store sha256 c57b113a310d5ec1 p.1; render sha256 837a212e83999bfc];
- AFT Act (Removal of Difficulties) Order 2008 C9R-RD-AFTRDO-IMG2 [corpus raw store sha256 1c6db257efe5ac07 p.1; render sha256 6796fdc90e4bc181] and S.R.O. 9(E)/2009 (establishment, appointed day 10-08-2009) C9R-RD-AFTAPPT-IMG [corpus raw store sha256 8d774f1fcc3358e8 p.1; render sha256 4b943bdc84eda313] - in no C5/C8 register;
- Finance Act 2017 C9R-RD-FIN17-01 [corpus raw store sha256 7a5551bab08518a7 p.64] and Tribunals Reforms Act 2021 C9R-RD-TRA21-IMG [corpus raw store sha256 0c2f4e9e023d5d7b p.1; render sha256 3abbdbe6b554b239];
- BNS India Code compilation C9R-RD-BNS-01 [corpus raw store sha256 d4449e9995b21fd5 p.1]; DPP Act 1950 compilation C9R-RD-DPP-02 [corpus raw store sha256 0884f3b50114c71f p.2]; IPC/IEA/CrPC renderings; Air Force and Navy Act compilations.
- The 7 held India Code compilation copies classed PROVENANCE_UNDOCUMENTED (Army Act e47a4265, Army Rules 48f52219, AFT 665863d1 and Hindi 48f57c81, BNSS 572c7988, BSA 554b2b4a, TRA 2026 be619533) are byte-identical to raw-data files that do have retrieval records (source URL, timestamp, crawler run). That is a provenance lead for the owner (AP-C9-02). It is not an authentication.

## Rows not linked to a P1-P5 instrument

Regulations for the Army 1987/1962, RMSAF, Army Orders, Territorial Army instruments, historical RAI/RMS and RAF 1964 (C5-ACQ-12..19, 22..26). These are carried for completeness, with their C5 states.

## Limitations

- Only refs present locally were read. A PR head on the remote may differ. During this session the local staging ref advanced from ff425a9a to 21e73b83 (Merge PR #39, C8-SOURCES). Its official_copies entries are unchanged, and the acquisition refs (1b948727, b8ee3176, 60715342, 97933ccf) and raw-data (ad77758d) did not move.
- md5 identity of a pin to a held research copy proves byte identity, not authenticity. India Code serves watermarked PDFs, so listing md5s are not comparable.
- The raw-data copies have not been registered in C5 or AUTH-LEDGER. Their classification here is UNREGISTERED_CORPUS_RAW_COPY.
