# Source acquisition plan: missing authority (PILOT-01 remediation, item 7)

**Database only. This is a plan; nothing has been downloaded beyond the pilot, and no external correspondence has been sent.**
Each acquisition needs owner approval (CLAUDE.md: ask before any real download run). Every item follows the crawler rules: allow-listed official domains only; robots.txt obeyed; at most 1 request every 2 seconds per domain; descriptive User-Agent; no login, CAPTCHA or paywall.

## Acceptance standard for every acquired item
1. Official source identity: Gazette (egazette.gov.in or a custodian scan), India Code, the ministry's own site, or a court site.
2. Bytes stored under `data/raw/<source>/<yyyy>/` named by SHA-256. Also record the MD5 where the host serves download-specific bytes (India Code Gazette scans do this).
3. Metadata record validated against `schema/document.schema.json`, with `source_url`, `retrieved_at`, `issue_date`, `effective_date` and `access_marking`.
4. Page-image check of the operative provision(s) before any audit finding uses the item as SOURCE_VERIFIED.
5. A legal-advisor decision before any proposition relies on a newly acquired text to override a compilation.

## Access constraints observed from this container (2026-11-22)
| Host | Result | Consequence |
| --- | --- | --- |
| indiacode.nic.in / indiacode.gov.in | reachable | Acts, consolidated texts, some Gazette scans (e.g. Act 37 of 1992) |
| api.sci.gov.in, sci.gov.in | reachable (no CAPTCHA on direct PDF URLs) | Supreme Court judgments |
| archive.org | reachable | historical layer only |
| egazette.gov.in | **timeout** | Gazette S.R.O.s blocked: needs another network (Indian IP), the owner's request log, or a custodian copy |
| mod.gov.in, aftdelhi.nic.in | **timeout** | MoD publications and AFT judgments blocked from this container |

## Plan by item

| # | Item | Why needed (findings) | Primary route | Fallback | Owner / effort | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | **S.R.O. 484 of 27-11-1954** (Gazette Pt II s.4, No.47, pp.291–378) | r.23(3) P0 (F-STAT-001, MMLPKT-02) | Custodian request (draft `registers/RULE23_3_CUSTODIAN_REQUEST_DRAFT.md`, **not sent**) to Dept of Publication / CSL / National Archives | egazette archive search from an Indian network; Parliament Library | Owner approval to send; weeks | NOT STARTED |
| 2 | Army Rules amending S.R.O.s: 34/1963, 116/1965, **215/1965 (r.192 proviso)**, 188/1979, 216/1988, 17(E)/1993, 8(E)/2003 (r.177), 258/2002, 17(E)/2019, 6(E)/2022 | r.22, 25, 177, 180, 182, 192 (F-STAT-019/022, F-REM-001, F-PROC-018) | egazette.gov.in search by S.R.O. number and date (post-2000 items are generally online) | Custodian request (same letter, para 3); MoD Gazette compilations | Indian-network crawl run; 1–2 days | BLOCKED (egazette unreachable) |
| 3 | Amending Acts for the Army Act: 19/1955, 56/1974, 13/1975, 20/1983; Act 37/1992 (**located**) | AA amendment chain (amendment_source_gaps.csv) | India Code "Amending Acts" listings (Act 37/1992 found there as a Gazette scan) | egazette | Crawler run on India Code; hours | PARTLY DONE |
| 4 | **Regulations for the Army 1987** (and the revised edition, if any) | GAP-06; MML notes cite Regs Army paras throughout | mod.gov.in / Army HQ publications page, if publicly published | Owner-supplied official copy (record its access marking); India Code has none | Owner; check FOUO marking before ingest | BLOCKED (mod.gov.in unreachable); access marking unknown |
| 5 | **Entitlement Rules 1982, 2008, 2023** and Guide to Medical Officers (Military Pensions) 2008/2023 | PEN-043, PEN-J-01, Isaac 2026 (GAP-16) | DESW / pension portal official PDFs (MoD letter 21-09-2023 for ER 2023) | Official copies annexed to SC/AFT judgments; owner copies | Crawler module for DESW; 1 day | NOT STARTED |
| 6 | **Criminal Courts and Court-martial (Adjustment of Jurisdiction) Rules 1978**, S.O. 4010 (06-12-1986) amendment, and any post-BNSS rules | CIV-033 BLOCKED (F-STAT-010), CIV-008, BNSS s.531(2)(b) | egazette (G.S.R./S.O. search) | MHA/MoD compilations; Rajya Sabha records (lead found by reviewer A) | Indian-network crawl; hours | BLOCKED (egazette) |
| 7 | **AFT judgments** (Principal Bench and regional benches) | GAP-12; the brief's largest volume; AFT-* records cite none | aftdelhi.nic.in disposed-case listings by month (existing `crawler/aft.py`, built and not run live) | Owner's request log (PROGRESS.md); AFT judgments cited inside SC judgments; e-court services | Owner: run from an Indian network or supply the log; days | BLOCKED (site unreachable from container) |
| 8 | BNS/BNSS/BSA commencement notifications (1-7-2024) | CIV-032, EV-002, CM-025 | egazette | India Code notes | Indian-network crawl | BLOCKED |
| 9 | ISO Act 2023 and ISO Rules 2025; Agniveer enrolment notifications | Owner scope (GAP-11, GAP-13) | India Code (Act, reachable); egazette (Rules, notifications) | MoD press/PIB as leads only | Crawler run; hours | NOT STARTED (India Code part can run now) |
| 10 | Judgments not obtained in the pilot: N S Yadav 2019, Shri Kant Sharma 2015, Santosh Lohar, Sundar 2023, Tarsem Singh 2008, L. Chandra Kumar 1997 | PEN-043, KB-028, AFT records | api.sci.gov.in JUDIS / judgment PDFs (reachable) | — | Agent fetch; hours | NOT STARTED |

## Proposed order (for owner approval)
1. Now, from this container: items 3, 9 (India Code part) and 10. These are reachable official hosts.
2. From an Indian network or authorised machine: items 2, 6, 7 and 8 (egazette and AFT). The existing crawler modules apply; use dry-run first.
3. Owner action: send item 1 (custodian request); obtain item 4 and record its access marking before ingest.
4. After each acquisition: re-run the affected PILOT-01 findings as a delta review. Do not re-audit records that are unaffected.
