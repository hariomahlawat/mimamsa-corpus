# Mimamsa B1: independent application walkthrough and acceptance audit (C14)

- **Date:** 2026-11-26.
- **Purpose:** to stand in for the owner's first manual review of the commissioned B1 application.
- **Method:** the application was driven through a real browser as a User and as an Admin, and measured. No fixes were made. No acceptance oracle was changed. Nothing in this report is a legal conclusion.

## 1. Baseline

| Item | Value |
| --- | --- |
| Git commit (code and docs) | `ee17b0660511b66fdd5307833e11d1268de35b56` (`legal-knowledge/v2.5-staging`: Cycle 13, plus PR #60 and PR #61) |
| Application binary | `Mimamsa.Web.dll` published from that commit, Release, net10.0 (SHA-256 prefix `94610122756EDF11`) |
| Release | `R13-b1-sample-20261126-4b31855f`, development-signed, from HF `hariomahlawat/mimamsa-corpus` at `3864faf3bb24edef4bfb18fa0916cc788eb68d79` |
| Corpus manifest | `app/b1/sample/SAMPLE_MANIFEST.json`. The local rebuild is byte-identical in ids, SHA-256, pages and text hashes: 290 documents, 11,352 pages, 38,445 passages. RM-001 excluded. Restricted register pin `fc7ea07e…` |
| Configuration | Loopback HTTP `127.0.0.1:5199`; `Mimamsa:Site` = sample site; `Mimamsa:RestrictedRegister` set; test mode off; `SecureCookies` false; password minimum 6 (PR #61); accounts `admin` (Admin) and `user` (User) |
| Database | PostgreSQL 18.6, private instance `127.0.0.1:55499`, database `mimamsa_b1`. Rows at baseline: app_users 4, app_sessions 6, audit_log 7, serving_policy 1, vault_copies 290, withdrawals 0, credit_pools 1, credit_instances 2, credit_reservations 23 |
| Isolation for destructive tests | `mimamsa_b1_audit` = `CREATE DATABASE … TEMPLATE mimamsa_b1`, taken with the service stopped. A second instance on `127.0.0.1:5299` serves the same site over it. Withdrawal, lockout and service-kill tests ran only there |
| Baseline preserved | After the audit, `mimamsa_b1` still has 0 withdrawals and the commissioned instance is unchanged (§7) |
| Tools | Playwright 1.63.0, Chromium 1243 headless; Python 3.13 (`urllib`); scripts in `scripts/` |

## 2. Verdict

**B1 is a sound, honest research prototype.** Its integrity and access-control foundations held under every probe:
- authentication on every route;
- role checks and CSRF;
- withdrawal enforced on all server routes;
- exact copy-pinned citations;
- seven-axis evidence status;
- candidate labelling;
- clear empty, error and outage states.

**No P0 was found.**

**It is not yet a satisfying research tool for the four target users.** The main reasons:

1. **Corpus coverage (F04).** The sample has no AFT judgments, no Regulations for the Army, no Air Force or Navy Rules and no Entitlement or Army pension rules. Commander and adjutant scenarios beyond the Army Act and Army Rules can't be answered.
2. **Lookup gaps that legal users hit at once:**
   - "section 302 IPC" and "103 BNS" are not understood (F01);
   - searching a case by party name ranks it 9th (F02);
   - SCC citations are unknown (F06).
3. **Legal-safety display gap:** IPC provisions give no hint of their replacement by the BNS (F03). It is mitigated by the "not established" labels, but it is one of the brief's named acceptance cases.
4. **Research ergonomics:**
   - no pagination beyond 200 passages (F10);
   - duplicate editions and languages (F11);
   - the cited passage is not scrolled into view (F12);
   - low density at 1366×768 (F13);
   - garbled Hindi text (F07).

**Performance is good at sample scale.** Search p95 is 44 ms for a single user and 172 ms with 10 readers, and the first PDF page appears in under 1 s. Memory growth (0.73 → 1.34 GB) leaves full-corpus scale unproven (F14).

## 3. Findings summary

| Severity | Count | Findings |
| --- | --- | --- |
| P0 | 0 | — |
| P1 | 4 | F01 instrument abbreviations · F02 party-name ranking · F03 IPC→BNS supersession not shown · F04 corpus coverage |
| P2 | 11 | F05 withdrawal UX · F06 SCC citations · F07 Hindi text · F08 misspellings · F09 plain-language ranking · F10 pagination · F11 duplicates/grouping · F12 scroll to passage · F13 density · F14 memory · F15 lockout extension |
| P3 | 3 | F16 facet labels · F17 no reinstatement · F18 Commander view |

Full details, with reproduction steps, evidence, root cause (marked *observed*, *code-confirmed* or *suspected*) and remediation, are in `FINDINGS_REGISTER.json`.

## 4. Coverage of the requested journeys

| Requested | Where | Result |
| --- | --- | --- |
| Authentication, logout, session | J01, J14 | Works. Lockout extension defect (F15). Idle and absolute expiry **not tested** |
| Dashboard and navigation | J01, J02 | No dashboard (UX §2). Navigation, palette and keyboard work |
| Exact identifier and provision search | J03, J04, Q09–Q20, Q28–Q34 | Strong for full titles. Fails for IPC/BNS abbreviations, party names, SCC |
| Natural-language, keyword, abbreviation search | Q01–Q08, Q13, Q21–Q24, Q35 | Army abbreviations expand. Plain-language ranking weak (F09) |
| Misspellings, ambiguity, zero results | J08, Q25–Q27, Q36–Q38 | Ambiguity, empty and parser states exemplary. No misspelling tolerance (F08) |
| Ranking, filters, pagination, sorting | J07, Q39–Q42 | Filters, sort and deep links work. No pagination (F10) |
| Judgment viewer and PDF navigation | J03, J04 | Works. Scroll-to-passage missing (F12) |
| Citation copy and exact page | J05 | Works, including reload |
| Provenance and evidence status | J04 | Complete and clear |
| Statutes, amendments, temporal applicability | J06 | 1992 omissions shown with candidates. IPC→BNS not shown (F03). As-of closed by design |
| Related judgments and cross-references | J04 | Cited/Citing candidates listed. Related empty for the judgment tested |
| Administrator functions | J12 | Overview and withdraw. No reinstatement (F17) or audit-log viewer |
| Withdrawal across all access routes | J13, J13b | Enforced on every server route. Open viewer and deep-link UX gaps (F05) |
| Access control | J11, J12 | All probes refused correctly |
| Error handling, recovery, responsiveness | J08, J15, PERFORMANCE_REPORT | Clean outage state; recovery 10.6 s including start-up |

## 5. Legal research scenarios

43 queries in `SEARCH_EVALUATION.json`: 24 pass, 8 partial, 10 fail, 1 not determinable.

| Persona | Pass | Partial | Fail | n/d | Typical outcome |
| --- | --- | --- | --- | --- | --- |
| Unit commander | 2 | 4 | 2 | 0 | Instruments found, but Navy/Air Force material or the criminal codes often rank above the Army Act for plain-language questions |
| Adjutant | 7 | 0 | 1 | 0 | Section and rule look-ups are reliable; the procedural natural-language query fails |
| JAG officer | 3 | 3 | 4 | 1 | Neutral citation and case number are exact. Party name, SCC citation and misspellings fail |
| Researcher | 5 | 1 | 2 | 0 | Full-title provisions and the BPRD tables work. IPC/BNS abbreviations fail |
| Edge cases | 7 | 0 | 1 | 0 | State handling is excellent. Hindi search unreliable |

| Failure class | Count |
| --- | --- |
| Retrieval failures | 9 |
| Incomplete features | 6 |
| Corpus deficiencies | 3 |
| Usability | 2 |

The verdicts are the auditor's judgements of what a researcher would expect first. They are not legal conclusions and not a retrieval metric, because there are no human relevance labels and the blind holdout was not used.

## 6. Not tested

| Item | Why |
| --- | --- |
| Session idle (30 min) and absolute (12 h) expiry | Time-bound; not waited out |
| Browser Back after sign-out | Inconclusive in a fresh test context (no prior history) |
| Withdrawal cut-off during a large in-progress PDF transfer | Both probe documents were fully delivered before withdrawal |
| Screen readers (NVDA/JAWS), 200%/400% zoom, print, greyscale | Need assistive technology or a human reviewer |
| Firefox, Edge | Chromium only |
| TLS, LAN access, Windows Service mode | Not configured in this commissioning |
| Cold start after reboot | Would need a reboot |
| Dharamvir Singh vs the Sept 2026 SC ruling on the 2008 Rules; 2023 SC ruling on HC writs against AFT | Not identifiable in the sample (F04) |
| 50-question golden test set | Not part of this walkthrough; the sample does not hold its sources |
| Graph, Studio, Notes, Assistant | Not implemented or closed by design (B2/B3) |

## 7. Post-audit checks

**Commissioned database untouched.** After the audit:
- `mimamsa_b1` has 0 withdrawals;
- no account there has failed attempts or a lock;
- the instance on 5199 is healthy.

**Audit copy.** `mimamsa_b1_audit` holds the two test withdrawals (`sc-1987-ranjit-thakur-1987insc285`, `sc-1991-ex-havildar-rat-an-singh-1991insc300`) and a test account `reader2`. It is disposable.

**Lockout expiry, on the audit instance.**
- *Sequence:* `user` was locked in J14. The auditor's own probes then made further attempts during the lock (a UI sign-in, two script sign-ins and one API check). Each one moved `locked_until` forward by 5 minutes: 19:18:26, then 19:20:15, then 19:24:40. `failed_count` reached 10 (F15).
- *Expiry:* with no further attempts, at 19:24:45 (after `locked_until`) a single correct sign-in succeeded (200, role User). `failed_count` and `locked_until` were then cleared.
- *Conclusion:* the lock expires as designed, but only if nobody tries to sign in during it.

## 8. Reproduction

From the repository root, with B1 running on 5199 and an audit instance on 5299 over a cloned database:

```
set NODE_PATH=<playwright dir>\node_modules
set PLAYWRIGHT_BROWSERS_PATH=<playwright dir>\browsers
set B1_URL=http://127.0.0.1:5199
set B1_AUDIT_URL=http://127.0.0.1:5299
set B1_PASSWORD=<password of admin and user>
set B1_STOP_AUDIT=<command>
set B1_START_AUDIT=<command>
node legal_knowledge/audit_work/C14-WALKTHROUGH/scripts/walkthrough.cjs legal_knowledge/audit_work/C14-WALKTHROUGH
node legal_knowledge/audit_work/C14-WALKTHROUGH/scripts/withdrawal_open_viewer.cjs legal_knowledge/audit_work/C14-WALKTHROUGH/evidence
python scripts/search_eval.py scripts/queries.json evidence/search_raw.json        (B1_USER, B1_PASSWORD)
python scripts/build_search_evaluation.py evidence/search_raw.json SEARCH_EVALUATION.json
python scripts/perf.py evidence/perf_raw.json                                     (B1_PID optional)
```

- `B1_ONLY=J06,J15` reruns selected journeys.
- Withdrawal, lockout and service-kill steps use only `B1_AUDIT_URL`. Point it at a disposable copy, never at the working database.

## 9. Package contents

| File | Contents |
| --- | --- |
| `WALKTHROUGH_REPORT.md` | This report |
| `FINDINGS_REGISTER.json` | 18 findings with reproduction, expected, actual, evidence, root cause and remediation |
| `USER_JOURNEYS.md` | Journey-by-journey observations |
| `SEARCH_EVALUATION.json` | 43 queries: what was returned, and the auditor's assessment |
| `UX_REVIEW.md` | Visual and UX review against professional legal-research expectations |
| `PERFORMANCE_REPORT.md` | Measurements and test conditions |
| `SCREENSHOT_INDEX.md`, `screenshots/` | 61 real browser screenshots |
| `walkthrough_observations.json`, `evidence/` | Raw observations: search, performance, withdrawal probe |
| `scripts/` | Reproducible walkthrough, search and performance scripts |
| `PROPOSED_CYCLE14_APPLICATION_PLAN.md` | Work packages, acceptance criteria and the traceability matrix |
