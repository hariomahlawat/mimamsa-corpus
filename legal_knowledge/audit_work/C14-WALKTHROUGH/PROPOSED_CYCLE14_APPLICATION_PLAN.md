# Proposed Cycle 14 application plan (from the C14 walkthrough)

**Status:** proposal for owner approval. Nothing here is implemented.

**Inputs:**
- `FINDINGS_REGISTER.json` (F01–F18);
- `SEARCH_EVALUATION.json` (Q01–Q43);
- items the owner deferred to Cycle 14: twin-withdrawal policy and manual account unlock.

**Constraints carried forward:**
- no generative or agentic AI;
- no change to AUTH-LEDGER or legal approval states;
- candidates stay labelled;
- every corpus download needs owner approval;
- the 6-character password minimum stays for development (PR #61).

## 1. Priorities

1. **First (P1, small to medium):** WP1 lookup fixes, WP2 supersession display, WP3 sample coverage. These are the gaps a legal user meets in the first minutes.
2. **Then (P2):** WP4 search usability, WP5 reading ergonomics, WP6 withdrawal UX, WP7 account safety.
3. **Gate before the full corpus:** WP8 scale run.
4. **Last, only after WP1/WP4 are measured:** WP9 hybrid search.

## 2. Work packages

### WP1: identifier and look-up completeness
**Findings:** F01, F02, F06.

**Scope:**
- a reviewed instrument-alias table resolved against held titles: IPC, CrPC, IEA/Evidence Act, BNS, BNSS, BSA, AA, AFA, NA, AFT Act, AR;
- a case-name tier on petitioner, respondent and title;
- parallel-citation capture from judgment covers and headnotes, as candidate aliases;
- a "citation not held" chip.

**Acceptance:**
- Q28 and Q29 pin IPC s.302 and BNS s.103, with an alias chip.
- Q18 ranks 2013 INSC 408 first.
- Q19 either pins it, or shows "citation not held".
- Regression tests for every alias.
- `retrieval_oracle` unchanged at ≥10/14, with no oracle edits.

**Size:** M.

### WP2: statutory supersession and equivalence display
**Findings:** F03.

**Scope:**
- candidate equivalence edges IPC↔BNS, CrPC↔BNSS and IEA↔BSA, from the held BPRD tables, with the table page as evidence;
- shown on both provisions and in Statutes, labelled "Candidate (automated, not verified)";
- a commencement notice: new codes apply from 1 July 2024;
- edges proposed for legal review, never auto-approved.

**Acceptance:**
- `/s/act-ipc-1860/302` shows candidate BNS s.103 with an evidence link.
- The BNS s.103 page shows IPC s.302.
- The brief's supersession checklist in `reports/` is updated: s.75–76, s.127, IPC→BNS.
- No approval state changes.

**Size:** M.

### WP3: development-sample coverage and text quality
**Findings:** F04, F07.

**Scope (needs owner approval for downloads):**
- one AFT bench-year of judgments;
- Regulations for the Army 1987;
- Air Force Rules and Navy Rules;
- Entitlement Rules and Pension Regulations for the Army;
- confirm whether the 2023 SC ruling on HC writs against AFT orders, and the Sept 2026 ruling on the 2008 Rules, are held;
- Hindi derivatives flagged "text unreliable" and excluded from default ranking until re-extracted;
- a language marker in document headers.

**Acceptance:**
- Q22, Q35 and the commander queries re-run with the new documents.
- Every new document is importer-verified, with RM-001 and the register applied.
- Q43 either returns the Hindi Act or states that Hindi text is unreliable.

**Size:** M (mostly data).

### WP4: search usability
**Findings:** F08, F09 (short-term part), F10, F11 (results).

**Scope:**
- "Did you mean" suggestions from the index vocabulary and party names (no silent rewrite);
- document-level pagination with deep-linkable pages;
- results grouped by instrument, with editions and languages nested;
- an optional service preference (Army / Navy / Air Force) as a facet and ranking prior.

**Acceptance:**
- Q25–Q27 offer the correct suggestion.
- Every document of a 255-document result set can be reached.
- s.69 Army Act shows one Army Act group with the Hindi copy nested.
- With service = Army, Q05, Q07 and Q13 have the Army Act provision in the top 3.
- Oracle unchanged.

**Size:** M.

### WP5: reading ergonomics and screens
**Findings:** F11 (Statutes), F12, F13, F16, F18; UX_REVIEW §4.

**Scope:**
- scroll to the first highlight on open;
- fit page;
- compact results density;
- provenance collapsed to one line;
- one merged banner;
- a library home (corpus summary, recent items, statute shortcuts);
- the Statutes list grouped by service and instrument, with a filter box;
- readable facet labels;
- the section number in statute legal citations;
- a Commander-view definition agreed with the owner before any build.

**Acceptance:**
- At 1366×768, at least 3 results are fully visible.
- The cited passage is visible on open for S-01 (s.69) at all three layouts.
- No horizontal overflow at 800–2560 px.
- Design-token and keymap tests pass.
- Before/after screenshots added to this package.

**Size:** M.

### WP6: withdrawal UX
**Findings:** F05, F17; twin-withdrawal policy (deferred owner decision).

**Scope:**
- the policy epoch returned with API responses;
- the client replaces any open tab whose document becomes unavailable with the standard notice;
- `/d/` shows the notice;
- dialog wording corrected;
- reinstatement, or a documented operator procedure (owner decision);
- the twin policy implemented as the owner decides.

**Acceptance:**
- J13 and J13b re-run: the open viewer shows the notice at the next action, and the deep link shows the notice.
- A mid-transfer cut-off is measured on a large PDF.
- All server-route refusals unchanged.

**Size:** S–M.

### WP7: account safety
**Findings:** F15; manual unlock (deferred owner decision).

**Scope:**
- attempts made while locked do not extend the lock;
- per-source throttling;
- Admin unlock with an audit-log entry;
- an Admin view of the audit log (read-only).

**Acceptance:**
- J14 re-run: the lock ends 5 minutes after the 5th failure regardless of attempts in between.
- An Admin can unlock, and the unlock is logged.
- No user enumeration (identical messages).

**Size:** S.

### WP8: scale and resources (gate before full corpus)
**Findings:** F14.

**Scope:**
- a full-corpus import and service run on this host, measuring start-up (re-hash time), working set, index memory, search p95 at 1/10/25 readers, and PostgreSQL memory;
- GC configuration trial (workstation or DATAS);
- an index memory budget.

**Acceptance:**
- A measured report.
- The service plus PostgreSQL fits within 10 GB on the 16 GB host at full corpus.
- Search p95 ≤ 300 ms at 10 readers.
- If not met, a design note before WP9.

**Size:** M (needs the full-corpus download, with owner approval).

### WP9: hybrid search (after WP1, WP4 and WP8)
**Findings:** F09 (long-term).

**Scope:** the semantic layer per the P2 evidence, CPU or 4 GB GPU-feasible, measured against the blind holdout under custody.

**Acceptance:**
- The 4 hybrid oracle cases are addressed without editing the oracle.
- A blind-holdout figure is reported.
- The lexical and identifier tiers are unchanged.

**Size:** L.

## 3. Traceability matrix

| Finding | Severity | Work package | Acceptance criterion (re-test) |
| --- | --- | --- | --- |
| F01 instrument abbreviations | P1 | WP1 | Q28, Q29 pin the provision with an alias chip; alias regression tests |
| F02 party-name ranking | P1 | WP1 | Q18 rank 1; J04 party-name step rank 1 |
| F03 IPC→BNS not shown | P1 | WP2 | J06 IPC s.302 shows candidate BNS s.103 with evidence; reverse link shown |
| F04 corpus coverage | P1 | WP3 | New instruments and AFT bench-year imported and verified; Q22, Q35 re-judged |
| F05 withdrawal UX | P2 | WP6 | J13/J13b: notice in the open viewer and on the deep link |
| F06 SCC citations | P2 | WP1 | Q19 pins the judgment, or shows "citation not held" |
| F07 Hindi text | P2 | WP3 | Hindi flagged unreliable or re-extracted; language marker in the header; Q43 re-judged |
| F08 misspellings | P2 | WP4 | Q25–Q27 offer the correct suggestion |
| F09 plain-language ranking | P2 | WP4 (prior), WP9 (hybrid) | Q05, Q07, Q13 with service = Army: provision in the top 3; hybrid oracle cases |
| F10 pagination | P2 | WP4 | All 255 documents for "court martial" reachable |
| F11 duplicates and grouping | P2 | WP4, WP5 | One group per instrument in results and Statutes |
| F12 scroll to passage | P2 | WP5 | S-01: highlight visible on open at all layouts |
| F13 density | P2 | WP5 | ≥3 results visible at 1366×768 |
| F14 memory and scale | P2 | WP8 | Full-corpus run within budget |
| F15 lockout extension | P2 | WP7 | J14: lock ends 5 min after the 5th failure |
| F16 facet labels | P3 | WP5 | Readable status labels; year hint |
| F17 reinstatement | P3 | WP6 | Owner decision implemented or documented |
| F18 Commander view | P3 | WP5 | Owner-agreed definition recorded before build |
| Deferred: twin withdrawal | — | WP6 | Policy implemented and tested |
| Deferred: manual unlock | — | WP7 | Admin unlock, logged |

## 4. Owner decisions needed

1. Approve the download run for WP3 (named instruments and one AFT bench-year; which bench and year).
2. Twin-withdrawal policy, and reinstatement in the UI or an operator procedure (WP6).
3. What the Commander view should do (WP5).
4. When to run the full-corpus scale gate (WP8), including the 8,006-title re-acquisition.
5. Who on the legal side reviews the WP2 equivalence edges.
