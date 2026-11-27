# Cycle 14: application development, consolidated implementation report

- **Integration branch:** `claude/c14-integration`, based on staging `ee17b066`. Nothing is merged to staging or main.
- **Directive:** Cycle 14 application development (owner, 2026-11-26). Phases 1–4.
- **Constraints kept:**
  - no legal approval state or AUTH-LEDGER value changed;
  - no generative legal advice;
  - acceptance oracles unchanged (0 files differ from staging);
  - protected corpus hashes and signed bundles untouched;
  - fully offline at run time (the hybrid model is local, pinned and verified by SHA-256);
  - 6-character development password policy retained;
  - corpus acquisition not started.

## 1. Branches and PRs

| Stream | Branch | PR | Status |
| --- | --- | --- | --- |
| Phase 1: walkthrough audit and corrections | `claude/c14-walkthrough-audit` | [#64](https://github.com/hariomahlawat/mimamsa-corpus/pull/64) | Codex: "Didn't find any major issues" at `e134f7e2`. Corrections C1–C3 recorded |
| S1 Search | `claude/c14-search` | [#67](https://github.com/hariomahlawat/mimamsa-corpus/pull/67) | Draft; integrated |
| S2 Safety | `claude/c14-safety` | [#66](https://github.com/hariomahlawat/mimamsa-corpus/pull/66) | Draft; integrated |
| S3 Statutes and reader | `claude/c14-reader` | [#68](https://github.com/hariomahlawat/mimamsa-corpus/pull/68) | Draft; finished by the coordinator after the stream agent was interrupted; integrated |
| S4 Scale and hybrid | `claude/c14-scale-hybrid` | [#69](https://github.com/hariomahlawat/mimamsa-corpus/pull/69) | Draft; integrated |
| Integration (S1–S4) | `claude/c14-integration` | integration PR | For Codex review; not for merge without owner authorisation |

Stream reports:
- `app/b1/evidence/c14_search/S1_REPORT.md`
- `app/b1/evidence/c14_safety/S2_REPORT.md`
- `app/b1/evidence/c14_reader/S3_REPORT.md`
- `app/b1/evidence/c14_scale/SCALE_REPORT.md`, `HYBRID_REPORT.md`

## 2. Test evidence on the integrated build

| Suite | Result |
| --- | --- |
| C# unit, site and integration (real Kestrel and PostgreSQL) | **152/152**: 89 baseline, S1 +33, S2 +12, S3 +8, S4 +10 |
| Hybrid tests with the real model (`MIMAMSA_HYBRID_MODEL` set) | **11/11** |
| Playwright journeys, hybrid off (SYN and real sample, workers = 1) | **52/52**: 30 baseline plus 22 new |
| Retrieval oracle (PR #54, unchanged), hybrid **off** | **10/14**, the same 4 hybrid cases fail by design |
| Retrieval oracle (unchanged), hybrid **on** (PoC) | **12/14**: RET-06 and RET-09 now pass; RET-07 and RET-10 fail |
| Design tests / token drift | 117/117 / none |
| Build | 0 warnings, 0 errors |

**Existing tests changed intentionally:** one. UX-06 selects the instrument entry, because the grouped Statutes list now nests edition links. Every other existing test is unchanged.

**Oracle independence.**
- The dense floor (0.8579) was fixed by a rule written before calibration (S4). It was calibrated on the 43 audit queries only.
- No oracle text was used for tuning.
- The blind holdout was **not** accessed. A procedure for the independent evaluator is in `app/b1/evidence/c14_scale/`, and `build_fixture_site.py --fixture` accepts the holdout file.

## 3. What was implemented, against the directive

### Phase 1: close the walkthrough audit

**Both Codex findings fixed:**
- **C1, cite probe:** now uses a real copy hash, with positive and negative controls: `CITED_COPY_ELIGIBLE` before withdrawal and `UNAVAILABLE` after; a malformed hash is unavailable in both cases.
- **C2, server timing:** now read from `elapsed_ms`. All 43 rankings are identical to the original run.

**C3:** S2 showed that the deep-link half of F05 was a probe error, and the auditor confirmed it from the audit's own screenshot. The original evidence is preserved under `evidence/original/`.

**Codex confirmation:** received.

### Phase 2: application foundation

| Work package | Delivered |
| --- | --- |
| 1. Legal identifier resolution | `Mimamsa.Core/Identifiers/LegalIdentifierResolver.cs`, covering statutory abbreviations and aliases resolved against held titles (IPC, I.P.C., CrPC, IEA, BNS, BNSS, BSA, AA, AFA, NA, AFT Act, AR…), sections and sub-sections, party names (case-name tier), neutral citations, reported citations (SCR/SCC/AIR patterns, with page-1 parallel citations as candidates), case numbers, and ambiguity chips. Every alias expansion is shown as a chip. |
| 2. Ranking | Exact case-name and statutory-provision matches are pinned above documents that only cite them: "Dharamvir Singh" goes from rank 9 to rank 1, and "section 302 IPC" pins IPC s.302. |
| 3. Withdrawal enforcement | The policy epoch is returned on API responses. The client clears any open tab whose document becomes unavailable: at the next server action, or within the 10 s poll. The deep link shows the notice. Mid-transfer cut-off is tested (C# and Playwright, via the test-mode pause hook). Verified byte-identical duplicates are opted into the withdrawal scope explicitly; distinct editions are never included. Reinstatement is Admin-only, needs a reason, and re-verifies the copy (re-hash, register, active, published) before restoring it. All previous server guarantees still hold. |
| 4. Account safety | Attempts during a lock neither extend it nor count as failures (F15 fixed). Throttling per username and per source address, with a generic message. Admin unlock with a mandatory reason. Content-free audit logging of login, lockout, unlock, throttle, withdraw and reinstate. Read-only Admin audit-log view. The 6-character policy is retained. |
| 5. Statutory relationships | Evidence-linked candidate correspondence IPC↔BNS (431), CrPC↔BNSS (521) and IEA↔BSA (191), read from the held BPRD tables with page and row evidence. Separate notices for commencement (delegated; notification not held; secondary source), repeal, savings and transitional provisions, and "repealed by", each quoting held text with its page. Stated: **corresponding provisions are not legally interchangeable**. The A4 amendment display (s.75–76, s.127) is unchanged. |

### Phase 3: research experience

| Item | Delivered | Evidence |
| --- | --- | --- |
| Document-level pagination | 25 documents per page, deep-linkable; all 255 "court martial" documents reachable | S1 |
| Instrument and edition grouping | Results: one group per instrument with editions and languages nested (S1). Statutes: 51 instruments from 64 documents, by category, with a filter (S3) | S1, S3 R-01 |
| Spelling suggestions | "Did you mean", run only on click; the query is never rewritten | Q25–Q27 |
| Service-aware ranking | Army / Navy / Air Force / All selector as a ranking prior, stated in the run line. With Army selected, the Army Act ranks 1/3/2 for Q05/Q07/Q13, at document level only | S1 |
| Density and screen use | Compact cards, one-line provenance, one banner line. Results fully visible: 1366 → **2** (target 3 not met), 1920 → 5, 2560 → 7 | `c14_integration/density_check.json` |
| Scroll to the cited passage | Passage found in the text layer, scrolled into view and marked; passes at 1366, 1920 and 2560 | S3 R-05 |
| Statutory navigation and library home | Grouped Statutes list; library home with corpus summary, statute shortcuts and session-only recent items; early Commander task home (same engine, different workflow) | S3 R-01, R-07 |
| Readable evidence and provenance | Provenance grouped (where from / this copy / in this library / notes); raw text shown for unresolved citations | S3 R-08 |
| Language and unreliable text | Script-based language detection; 5 legacy-font Hindi Acts flagged unreliable and kept out of search (still readable); language marker and reliability chip in the header | S3 R-04 |

### Phase 4: scalability and hybrid retrieval

| Documents | Passages | Start-up | Search p95 at 1 / 10 / 25 readers | Live heap after forced GC |
| --- | --- | --- | --- | --- |
| 290 | 38,445 | 9.2 s | 84 / 187 / 243 ms | 311 MB |
| 1,000 | 24,195 | 17.5 s | 87 / 175 / 222 ms | 167 MB |
| 4,000 | 99,113 | 18 s warm, 56 s cold | 158 / 653 / 1,051 ms | 648 MB |
| 10,000 | 247,538 | 131 s | 548 / 2,252 / 4,679 ms | 1,589 MB |

The 1k–10k scales are synthetic, seeded fixtures built through the real importer. Import took 26 s, 146 s and 397 s respectively.

**Findings:**
- **GC retention, not a leak.** The live heap stays flat across 5 load cycles at every scale. The audit's F14 growth was the server garbage collector holding memory.
- **About 6.5 KB of live heap per passage.** By extrapolation, the full corpus would need about 12 GB, which does not fit with PostgreSQL on 16 GB. **A disk-backed index is required before a full-corpus import.**
- **Persistent index for start-up alone: not worth it.** Index build is 11–15% of start-up; re-hashing the originals dominates.
- **GC mode:** keep the default.

**Hybrid PoC:**
- Model: multilingual-e5-small (MIT, pinned revision and SHA-256), ONNX on CPU.
- Speed: 12 passages/s to embed, 5–8 ms per query. DirectML was slower; CUDA was not attempted.
- Off by default, behind one hook. Identifier priority is unchanged: all 13 identifier queries on the real sample give the same top result and mode.
- Cost: +4.3 s start-up, +620 MB, sequential p50 19 → 45 ms.

## 4. Audit findings: closure status

| Finding | Sev. | Status after C14 |
| --- | --- | --- |
| F01 instrument abbreviations | P1 | **Closed** (S1) |
| F02 party-name ranking | P1 | **Closed** (S1: rank 9 → 1) |
| F03 IPC→BNS not shown | P1 | **Closed for display**: candidate edges with evidence. Legal review of the edges is still required (owner decision) |
| F04 corpus coverage | P1 | **Open, out of scope**: corpus acquisition is a separate workstream |
| F05 open viewer after withdrawal | P2 | **Closed** (S2; bounded by the 10 s poll when the reader is idle) |
| F06 SCC citations | P2 | **Mitigated**: "Citation not recorded in this library" chip; parallel citations captured as candidates. Missing SCC metadata is a corpus item |
| F07 Hindi text | P2 | **Closed** (flagged, labelled, excluded from search). Re-extraction is a corpus/OCR item |
| F08 misspellings | P2 | **Closed** |
| F09 plain-language ranking | P2 | **Partly closed**: service prior (document level); hybrid PoC 12/14. Provision-level procedural ranking remains |
| F10 pagination | P2 | **Closed** |
| F11 duplicates and grouping | P2 | **Closed** |
| F12 scroll to passage | P2 | **Closed** |
| F13 density | P2 | **Partly closed**: 1366 → 2 results (target 3) |
| F14 memory | P2 | **Reclassified**: no leak (GC retention). The scale risk is now quantified: disk-backed index needed |
| F15 lockout extension | P2 | **Closed** |
| F16 facet labels | P3 | **Closed** |
| F17 reinstatement | P3 | **Closed**: owner policy implemented |
| F18 Commander view | P3 | **Partly closed**: early task home; a full task-oriented workflow is future work |

**P0: none. P1 within scope: all closed.** F04 is the corpus workstream's.

## 5. Integration notes

- **Conflicts:**
  - `journeys.spec.cjs`: S1 and S2 both appended tests; both kept.
  - `playwright.config.cjs`: S2's test-mode server settings kept.
  - `app.css`: both blocks kept.
  - `Api.cs` search run object: S4's hybrid label combined with S1's service fields.
- **Coordinator fixes:**
  - S3: a `home.js` syntax error, DocumentDto language and reliability fields not sent, Commander home not redrawn, and one wrong test expectation.
  - Integration: the opt-in `/api/diag/memory` benchmark endpoint (unauthenticated) now answers loopback callers only and logs a warning when enabled.
  - Integration: a nullability warning in `Api.Statutes.cs`.
- **Operational:** a session restart stopped all processes during the cycle. PostgreSQL recovered cleanly. `pg-start.ps1` now waits for `pg_isready`. Test runs use `Maximum Pool Size=10` and one Playwright worker, because `max_connections` is 50.
- **Commissioned instance:** `127.0.0.1:5199` now runs the integrated build (hybrid off) over the unchanged `mimamsa_b1` database. Smoke checks: IPC alias, case name and spelling suggestion all behave as designed; the diagnostics endpoint is not exposed (404).

## 6. Outstanding items and recommendations

1. **Disk-backed search index (next cycle, gate for the full corpus).** About 12 GB of live heap is projected at full scale, and search p95 at 10k documents is 2.25 s with 10 readers.
2. **Hybrid PoC to production.** Evaluate on the blind holdout (independent evaluator, procedure supplied). Consider a stronger model or a reranker for RET-07/RET-10, measure memory at scale, and decide on enabling it. Q01 regressed with hybrid on.
3. **Legal review of the candidate correspondence and supersession edges.** Needs a Legal Reviewer appointment (open owner decision). Nothing is approved automatically.
4. **Density at 1366×768.** Reach at least 3 visible results, for example a dense list mode.
5. **Commander workflow.** Grow the early task home into the task-oriented workspace (procedures, provisions, forms, safeguards) with the owner, alongside Document Studio.
6. **Corpus workstream items surfaced here:** AFT judgments and missing instruments (F04), SCC parallel citations (F06), Hindi re-extraction or OCR (F07), the 1 July 2024 commencement notification.
7. **Housekeeping:**
   - test databases `c14s1_*`, `c14s2_*`, `c14s3*`, `c14s4_*` and `c14int_*` remain on the private PostgreSQL;
   - the bench sites under `E:\Mimamsa-Data\bench` (synthetic) can be removed when no longer needed;
   - the audit instance (port 5299) is stopped.
