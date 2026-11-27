# Acquisition-readiness matrix (Cycle 4 planning; DATABASE ONLY)

**Planning only. Nothing was downloaded, fetched, configured or approved.** No host was contacted and no config was activated. No legal determination is made here. A located source is not an acquired source, and an acquired source is not an authenticated source. Configuration branches exist for some batches, but no repository file records owner approval of any download run, so `owner_approval_outstanding` is YES on every row except the excluded route. The AFT bare-IP HTTP route and aftjabalpur.in are never proposed. Commercial legal databases are never a source.

Reserved states are quoted, not changed: r.23(3) CONFLICTING (C-01); r.193 C-08 OPEN; r.194 C-09 PROPOSAL; r.15, r.187(1) and s.129 OPEN; AQ-05, AQ-06 and OQ-A-13 reserved.

## Files
| File | Content |
| --- | --- |
| `acquisition_readiness.csv` | 147 candidates, one row each, in recommended order |
| `acquisition_readiness_summary.json` | Counts, folded duplicates, config-label mismatches, branch commits |
| `build_acquisition_readiness.py` | Generator (stdlib; deterministic; `--out DIR` writes elsewhere) |
| `README.md` | This file (generated) |

## Method
- **Candidates.** Every row of `COORDINATION/CYCLE3-PLANNING/acquisition_schedule.csv` (140), which already consolidates ACQ-01 `batches.json`, ACQ-02, WS-A `acq03_pinned_candidates.csv` and `acquisition_requests*.csv`, WS-A cycle-3 requests and the WS-B queue `pending_acquisition_cycle3.csv`; plus the 8 MML editions in `source_authentication_queue.csv` (authentication, not download). The 55 judgment rows of that queue map onto the WS-B queue rows (`authentication_queue_ids`). Two schedule rows that name the same file and alias each other are folded into one (ACQ03-029 into ACQ-C3-01).
- **Coverage checks.** Every Army Rules register row with evidence TEXT_LAYER_ONLY, HINT_ONLY, NOT_FOUND or NOT_SEARCHED_AUTHORITATIVELY, and every WS-A gap with an acquisition request, resolves to a candidate. GAP-10 (Hindi text of a held instrument) and GAP-12 (legal advice on silent instruments) need no acquisition.
- **Integrity values** are copied as recorded (`sha256`/`md5`/`bytes`), else NOT_PINNED. For MML rows they are the hash of the held user-supplied copy, which proves byte identity only.
- **authority_class** copies the SOURCE_AUTHORITY_POLICY v1 values as recorded in the schedule or queue. **restrictions** are derived from the carrier: archival facsimile (HASH_ONLY until page-image check; historical wording only), government compilation (comparison text, never Gazette authority), official court copy only, UNVERIFIED_MANUAL, HTTPS only, owner approval, no bypass.
- **already_held** checks, in order: the pinned SHA-256 in `registers/held_sources_scratchpad.csv`; the same archive.org item in a held path (pinned md5/bytes not re-verified); the same source URL in an `origin/raw-data` `data/meta` record (crawler corpus copy); for judgments, a held mirror (never official). A held scratchpad or corpus copy is not a record copy from an approved run.
- **configured** reads `git show <branch>:config/sources.yaml` for claude/acq-01-config (PR #8), claude/desw-allowlist (PR #9), claude/acq-02-config (PR #17) and claude/acq-03-config (PR #23), and matches the candidate's URL, ACQ-01 doc_id or India Code item UUID. Every listed source is `enabled: false`. Configured is never approved.
- **records_unblocked** is the union of: the CYCLE3-PLANNING `affected_records_priority.csv` record-to-acq links (by ID or alias); WS-B `KB records` lists; MML `linked_records`; KB records whose cited Army Act sections or Army Rules intersect the candidate's provisions (schedule `provisions:` list, Army Rules register `provisions_affected`, Army Act chain `sections_affected`; a principal instrument covers every section or rule of its instrument); WS-D `canonical_coverage.csv` citations of the corpus document the candidate is a copy of (AFT rules); KB ID ranges in a gap's `affected_ids`; and calibration `linked_cases` naming the judgment. **calibration_records_unblocked** is the subset in `CALIBRATION-01/calibration_package.csv` (46).
- **legal_questions_unblocked** marks evidence that bears on a reserved question; it never answers it. Tokens in the candidate's own row and in the register rows it names: r.23(3) (r.23, C-01, R23; or an Army Rules register row with `amends_r23` enacts/YES/UNKNOWN); C-08 (r.193); C-09 (r.194); r.15 (r.15, OQ-A-10, GAP-15, XC-03); r.187(1) (r.187, OQ-A-11, GAP-14, OQ-C-06); s.129 (s.129, CC-17, FID-03); AQ-05 (named register row with commencement NOT_STATED_PENDING_ADVICE (AQ-05) or NOT_DETERMINED, or GAP-06/07/12); AQ-06 (a register row with `retrospective_deemed_effect_from` or deemed effect; OQ-A-12); OQ-A-13 (AA-01, GAP-07, Act 19/1955). A gap's text is expanded only when the row names no Army Rules register ID, because one gap lists several instruments. `unblock_count` = records_unblocked + legal questions.

## Priority rule (mechanical)
`recommended_priority` is the first tier that applies:
- **T1**: Army Act 1950 as enacted.
- **T2**: unverified Army Rules amendment instruments and Gazette issues (OCR-only, hints, NOT_FOUND, post-2022 search, S.R.O. 484/1954 original).
- **T3**: instruments bearing on commencement or retrospective dates (AQ-05, AQ-06, OQ-A-13).
- **T4**: authenticity and edition of the 8 MML copies.
- **T5**: official judgments needed to replace mirror citations.
- **T6**: sources needed for the 46 calibration records.
- **T7**: other pending acquisition items.
- **EXCLUDED**: route excluded (bare-IP HTTP or aftjabalpur.in); never contact.

Tier tests: T1 = the proposed file is `in.gazette.e.1950.306`. T2 = the row names an Army Rules register ID whose evidence is TEXT_LAYER_ONLY, HINT_ONLY, NOT_FOUND or NOT_SEARCHED_AUTHORITATIVELY, or is the S.R.O. 484/1954 original (AR-000), or names an Army Rules gap that is NOT_FOUND, LOCATED_UNVERIFIED, NOT_SEARCHED or not held (GAP-01, GAP-02, GAP-03, GAP-04, GAP-05, GAP-13, GAP-14, GAP-15). T3 = AQ-05, AQ-06 or OQ-A-13 in `legal_questions_unblocked`, a commencement gap (GAP-06/07/12), or an Army Act chain row with commencement NOT_DETERMINED. T4 = MML edition. T5 = WS-B row with a mirror copy recorded. T6 = at least one calibration record. T7 = the rest. EXCLUDED = exclusion recorded.

Within a tier, `priority_rank` sorts by: more reserved questions; not yet held before held; higher `unblock_count`; more calibration records; source located; integrity pinned; `acq_id`.

## Counts
- Rows: 147. By scope: ACQ-01 20; ACQ-02 17; ACQ-03 43; MML authentication 8; WS-A cycle 3 4; WS-B judgments 55.
- By tier: T1 1; T2 27; T3 22; T4 8; T5 31; T6 12; T7 45; EXCLUDED 1.
- Integrity pinned (hash + bytes): 72. Already held in some form: 37 (scratchpad, corpus or user-supplied MML; none is a record copy from an approved run). Document listed in a config branch: 72. Owner approval outstanding: 146 (the remaining row is the excluded route).
- Calibration: 35 of 46 records are linked to at least one candidate; 46 candidates link a calibration record. Without a candidate: ADM-CL-02, ADM-CL-03, ADM-CL-07, CM-040, CM-JD-01, J-03, PEN-003, PEN-006, PEN-024, PEN-CL-06, PEN-WF-03.
- Reserved questions (candidates bearing on each): r.23(3) 17; C-08 4; C-09 4; r.15 12; r.187(1) 9; s.129 4; AQ-05 28; AQ-06 1; OQ-A-13 2.
- **Config-label mismatches** (schedule batch label vs. the config branches as read):
  - ACQ-01:guide-medical-officers-mil-pensions-2023: schedule batch 'ACQ-01-B4 (not configured)' but a config branch lists the document
  - ACQ-01:rules-entitlement-2023: schedule batch 'ACQ-01-B4 (not configured)' but a config branch lists the document
  - ACQ03-029: schedule batch 'ACQ-03 B4 (archive_acq03 (PR #23, unmerged))' but the document is not listed in any config branch

## Top 20
| Rank | Tier | acq_id | Source | Held | Configured | Records (calib.) | Reserved questions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 001 | T1 | ACQ-C3-01 | Army Act, 1950 as enacted (Act XLVI of 1950) | NO | NO | 175 (21) | s.129;AQ-05 |
| 002 | T2 | ACQ-01:notif-army-rules-1954-sro-484 | Army Rules, 1954 (S.R.O. 484), Gazette of India No. 47, Part II-Sectio | YES | YES | 167 (16) | r.23(3);C-08;C-09;r.15;r.187(1);AQ-05 |
| 003 | T2 | ACQ03-001 | 'Army (First Amendment) Rules, 1966' (OCR: Part 1 of Appendix IV) | NO | YES | 6 (2) | r.23(3);r.15 |
| 004 | T2 | ACQ03-002 | unknown Army Rules amendment (OCR: 'further to amend the Army Rules, 1 | NO | YES | 6 (2) | r.23(3);r.15 |
| 005 | T2 | ACQ03-003 | unknown Army Rules amendment (OCR) | NO | YES | 6 (2) | r.23(3);r.15 |
| 006 | T2 | ACQ03-004 | 'Army Amendment Rules, 1968' (OCR: Appendix I) | NO | YES | 6 (2) | r.23(3);r.15 |
| 007 | T2 | ACQ03-005 | S.R.O. 66 dated 14-02-1969, 'Army Amendment Rules, 1969' (OCR: App. I  | NO | YES | 6 (2) | r.23(3);r.15 |
| 008 | T2 | ACQ03-006 | unknown Army Rules amendment (OCR) | NO | YES | 6 (2) | r.23(3);r.15 |
| 009 | T2 | ACQ03-007 | 'Army (First Amendment) Rules, 1972' (OCR: Appendix) | NO | YES | 6 (2) | r.23(3);r.15 |
| 010 | T2 | ACQ03-008 | 'Army (Amendment) Rules, 1974' (OCR; commencement clause) | NO | YES | 6 (2) | r.23(3);r.15 |
| 011 | T2 | ACQ03-009 | 'Army (Second Amendment) Rules, 1974' (OCR: App. 1 Form No.1) | NO | YES | 6 (2) | r.23(3);r.15 |
| 012 | T2 | ACQ03-037 | Army Rules amendment of r.187(1) item (r), dated 28-11-1958 (OCR) | NO | YES | 0 (0) | r.23(3);r.187(1) |
| 013 | T2 | ACQ03-012 | S.R.O. 351 dated 07-10-1960, Army (Third Amendment) Rules, 1960 (Table | NO | YES | 5 (1) | AQ-05 |
| 014 | T2 | ACQ03-014 | S.R.O. 22 dated 13-05-2010, Army (Amendment) Rules, 2010 (Table r.13) | NO | YES | 5 (1) | AQ-05 |
| 015 | T2 | ACQ03-038 | Army Rules amendments of r.95, dated 12-12-1958 (OCR) | NO | YES | 4 (0) | r.23(3) |
| 016 | T2 | ACQ03-010 | S.R.O. 331 dated 23-09-1960, Army (Second Amendment) Rules, 1960 (r.16 | NO | YES | 0 (0) | AQ-05 |
| 017 | T2 | ACQ03-011 | S.R.O. 348 dated 03-10-1960, Army (Amendment) Rules, 1960 (App. I Form | NO | YES | 0 (0) | AQ-05 |
| 018 | T2 | ACQ03-013 | S.R.O. 404 dated 21-11-1960, Army (Fourth Amendment) Rules, 1960 (r.16 | NO | YES | 0 (0) | AQ-05 |
| 019 | T2 | ACQ03-036 | Army Rules amendment (App. I), 1956 (OCR) | NO | YES | 0 (0) | r.23(3) |
| 020 | T2 | ACQ03-039 | Army Rules amendments, 1959 (OCR) | NO | YES | 0 (0) | r.23(3) |

## Rebuild
```
python3 legal_knowledge/audit_work/CALIBRATION-02/registers/acquisition_readiness/build_acquisition_readiness.py
```
Inputs are read from the working tree and from the git refs named above; two runs give byte-identical files while those refs are unchanged.
