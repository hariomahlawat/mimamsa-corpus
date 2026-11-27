# Approval packages (C9-STAT) - DRAFTS, NOTHING EXERCISED

Every page reading cited is by an AI agent (Claude Opus 5.5 subagent), not human-confirmed. No legal status, applicability or commencement date is determined or inferred; compilation footnotes and 'w.e.f.' notes are recorded as compiler statements only.

`acquisition_manifest_ready.csv` holds ONLY the documents already inside an approved scope: the 14 PR #8 documents of ACQ-01 batches B1, B2 and B6, which the owner authorised on 2026-11-22. Even these still need (1) owner approval/merge of PR #8 and (2) a logged download-run approval under the runbook. Every other acquisition needs one of the new permissions below.

| package | scope | documents | authorisation sought | dependent KB records (gross) | notes |
| --- | --- | --- | --- | --- | --- |
| AP-C9-01 | execute PR #8 (ACQ-01 B1/B2/B6) | 14 (ready manifest) | PR #8 approval + download-run approval (scope already authorised) | 34 (excl. Army Rules chain) | yields the CCCM Rules 1978 and S.O. 4010/1986 (resolves the date dispute by page check), the Act 19/1955 Gazette with Schedule, and record copies of 9 held Army Rules instruments |
| AP-C9-02 | register corpus raw-store copies; provenance leads | 15 raw-store documents + 7 held compilations | owner decision: C5 copy rows + AUTH-LEDGER rule-1 review (no download) | 75 | highest value per effort: the AFT Act as published (89 records) and the AFT rules (43) are already held |
| AP-C9-03 | A-C5-1 Batch A archive.org Gazettes | Army Act 1950 as enacted, BNSS, BSA, BNS, 3 notifications of 2024, 10 post-2022 S.R.O.s (AFT optional) | A-C5-1 + a NEW crawler-config PR stacked on #8 (none exists) | 113 | Army Act enacted text: 185 records |
| AP-C9-04 | PR #17 and PR #23 | 16 + 39 | config approval + download run per source; ACQ03-016 keep/drop; drop ACQ03-033..035 (redundant) | see csv | PR #17 adds record copies only; PR #23 adds the Army Act commencement candidate, ALO 1956, Ord. 1975, Act 20/1983 and hints |
| AP-C9-05 | discovery (no candidate in any register) | S.O. 14(E)/2008; TRA 2026 s.1(2) notification(s); Finance Act 2017 Part XIV notification; S.O. 3912(E)/2019; RAA 1957, 1960; 'S.R.O. 34 of 5-6-1963'; post-BNSS adjustment rules; IPC/CrPC/IEA as at repeal; AFA/NA Gazettes; ISO Act/Rules; Army Act notifications | discovery approval; Indian-network run for egazette (TLS failure from container) | n/a | no download in the discovery step |
| AP-C9-06 | DESW (A-C5-2) | PRA 2008 Pt I/II, ER 2008, ER/GMO 2023, circulars | A-C5-2 + allow-list extension beyond PR #9 + readable robots.txt (403 now) or owner-side manual retrieval with sha256 | 39 | PR #9 has no integrity pin; add expected sizes and hashes |
| AP-C9-07 | custodian (A-C5-3) + scope P-C6-04-SCOPE | RA 1987/1962, RMSAF, named AOs, E-7/1960, S.R.O. 258/2002 | approval of request text; access-marking handling | see csv | drafts in C8 CUSTODIAN_REQUEST_DRAFTS.md; no correspondence authorised |
| AP-C9-08 | P-C7-02-META | DPP Amendment Act 2000 (the compilation names it Act 31 of 2000) | metadata-only archive.org route, then A-C5-1 | 0 | low consequence |

## Gates common to every package

- Dry run first. Record retrievals with sha256, md5, size and URL. Page-image check the operative provisions before any finding cites them.
- Acquiring a document never changes a record's legal status. A delta review and legal review follow.
- No HF upload and no push to raw-data without separate approval.
