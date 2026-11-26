# Project Mimamsa: Cycle 13 completion report

**Date:** 26 November 2026
**Prepared by:** the coordinator. Every workstream was independently reviewed, and no work was approved by its own author.
**Status markings:** every legal-content figure is `AUTOMATED_CANDIDATE_NOT_VERIFIED`. AUTH-LEDGER is still at version 0, so nothing is legally approved.

**Where things are**

| Item | Location |
|---|---|
| Staging branch | `legal-knowledge/v2.5-staging` |
| Hugging Face (HF) dataset | `hariomahlawat/mimamsa-corpus`, which is private |
| Findings register | `legal_knowledge/audit_work/C13-A9-CLOSEOUT/` |
| Evaluation records | `C13-EVAL/` |
| Application documentation | `docs/architecture/` and `app/` |

---

## 1. Executive summary

Cycle 13 delivered the evaluation infrastructure, the corpus-recovery work, frozen extractors, a blind evaluation, and the first working offline application prototype. All of it went through independent review, then into staging in four gated tranches.

**Track A (legal knowledge)**
- **Fresh blind holdouts.** Three sets: H-OUT (300), H-HOLD (113) and H-REL (160).
- **Extractors frozen.** Outcome V4 (A2), holdings (A3) and treatment (A5) were frozen and scored blind. Coding was done by two independent coders plus an adjudicator, with an independent evaluator and an independent review of that evaluation.
- **No Track A extractor met its target under blind evaluation.**
  - Outcome V4 missed all four targets. Printed-disposal precision was 0.898 (95% interval 0.838–0.941) against a target of at least 0.95. Coverage was 0.833 against at least 0.85.
  - H-HOLD is **not scorable** under the protocol, because inter-coder agreement (span F1 0.566) fell below 0.6. A3's precision of 0.365 and recall of 0.517 are descriptive only.
  - A5 relation-type precision of 0.340 is descriptive only.
  - All research-use restrictions therefore stay in force.
- **OCR and false-negative audit (A1).** The audit found a large silent-loss problem:
  - Of 8,077 excluded titles, only 71 are held.
  - About 3,760 Punjab and Haryana judgments (estimated range 2,650–5,240) were deleted without readable text.
  - The pipeline rule was corrected so that "irrelevant" requires usable text on every page, and the rule fails closed.
  - 567 pages were OCR'd.
  - All 12 Punjab and Haryana writs that had no usable text are now RELEVANT.
- **Statutory version model (A4).** 488 records, with a date resolver that never assumes the latest text applies.
- **Forms (A6).** 21 of the 22 R04 families are closed and verified. The forms registry has 106 families.
- **Treatment graph (A5).** 13,406 nodes and 45,134 edges. 99 Supreme Court case numbers were reconfirmed; the 266 unreviewed corrections were not applied.
- **Acquisition (A7).** 63 new public source files were acquired and preserved, and every review finding has a recorded disposition.
- **Adviser package (A8).** 204 de-duplicated questions for a legal adviser.

**Track B (application)**
- **Technology.** ASP.NET Core on Kestrel as a Windows Service, chosen on proof-of-concept evidence. The architecture is Windows-first, not Windows-only: a portable core with thin OS adapters.
- **Importer (ASR-E05).** Verifies original bytes, SHA-256, size, physical page count, derived-file identity and passage boundaries before anything is served. Bad input is refused or quarantined.
- **Citation navigation (ASR-E06).** A citation opens the exact cited copy and page. The current edition is offered separately and is never silently substituted.
- **Protected large-PDF delivery (R2-N01).** Proven on Linux and on GitHub-hosted Windows, and independently confirmed as closable for the hosted-Windows proof-of-concept scope. **Your selected host is still blocked.**
- **B1 prototype.** A working ASP.NET Core application over 290 real, importer-verified documents. It has search, a protected viewer, citations, provenance, labelled candidate data and a professional UI, and it was **accepted as the B1 baseline** after independent review.

**Corpus repository, PR #53 and PR #54**
- **Hugging Face.** All writes were additive and verified. The current head is `f4e6ba44`.
- **PR #53 (intelligence architecture).** Integrated at the controlled point. Its disposition is ACCEPT WITH CONDITIONS; see §20.
- **PR #54 (independent assurance).** Integrated with its oracles unmodified. The blind holdout stays with its owner.

---

## 2. Live GitHub and Hugging Face status

**GitHub, as of this report**

| Ref | Commit | Note |
|---|---|---|
| main | `21de3531` | Untouched, never merged to |
| staging | `f79160f5` | After tranche 3. Tranche 4 is pending; see the PR noted at the end. |
| raw-data | `ad77758d` | |

Cycle 13 merges into staging:

| PR | Merge commit | Contents |
|---|---|---|
| #51 | `9ed152af` | Crawler security: aftjabalpur.in blocked, plus a code-level backstop |
| #52 | `ba308db0` | Tranche 1: governance and restricted material, backup tooling, A4, A6 |
| #55 | `dbe40b4f` | Tranche 2: PR #53, PR #54, app contract and design, importer, citation navigation |
| #56 | `f79160f5` | Tranche 3: A0, A1, frozen A2/A3/A5, blind evaluation, B-PoC |

The HF sync workflow was skipped or not triggered on every merge.

**Hugging Face** (private; head `f4e6ba443ec9`; 16,255 files)

| HF commit | Cycle | Content | Verified |
|---|---|---|---|
| `5524c3d9` | C12 | 48 working-store PDFs preserved | byte-verified |
| `af7f9d06`, `15bd03cc`, `3864faf3` | C12 | Judicial recovery and ingestion | verified |
| `844383f5` | C13 | A5: 99 SC case-number overlay | additive, verified |
| `9e3cf986` | C13 | A7: 63 acquired public PDFs | 63/63 re-download match |
| `23acf21b`, `fafd4749`, `f4e6ba44` | C13 | A1: OCR overlays and ingestion candidates, revision r2 | 27, then 42, then 15 files; all match |

Every write was pinned to its parent commit, re-downloaded and checked by SHA-256, and recorded in GitHub. Nothing was deleted and visibility was not changed.

## 3. Workstream-wise completion

Statuses:
- **DONE**: delivered and independently accepted.
- **DONE-NOT-MET**: delivered and evaluated, but its target was missed.

| WS | Status | Key output |
|---|---|---|
| GOV | DONE | RM-001 exclusion guard; decision note; owner-run backup create and verify tool; registers |
| A0 | DONE | Frame of 4,281; three fresh holdouts; protocol v1.1; leak guard; GA0 accepted after the C01 P1 fix |
| A1 | DONE | Explicit fail-closed states; OCR benchmark; false-negative audit; 3 HF commits |
| A2 | DONE-NOT-MET | Outcome V4 frozen at `9cdd5008`; blind results NOT_MET |
| A3 | DONE-NOT-MET | Frozen at `a520aa3a`; holdout not scorable; descriptive only |
| A4 | DONE | 488-record temporal version model and resolver; EXACT 99 → 109 (proposals only); 45 acquisition requests |
| A5 | DONE | Treatment graph; 99 case numbers reconfirmed; contract export (34,567 records, 0 validator issues); frozen at `e15af208` |
| A6 | DONE | R04: 21/22 closed; 106 families; 86-case oracle |
| A7 | DONE | 63 of 126 targets acquired; allow-list and PR recommendations; dispositions recorded |
| A8 | DONE | 204 adviser questions (P0 1, P1 34, P2 169); 1,103 anchors, all resolving |
| A9 | DONE | Findings register (261 rows); task, risk and owner-decision registers |
| B0 | DONE | ADR-0005; traceability matrix; security architecture; data contract revision R2; UX spec; PR #53 reconciliation |
| B-PoC | DONE | P1–P5 and P7 evidence; R2-N01 on Kestrel |
| B1 | DONE (baseline) | Working prototype; accepted after three review rounds |

The final task register is `C13-A9-CLOSEOUT/TASK_REGISTER_C13_FINAL.md`.

## 4. Updated corpus statistics

- **Baseline from Cycle 12:** 4,103 baseline documents, 4,121 distinct source copies and 4,277 judicial records.
- **Added this cycle:**
  - 63 public sources preserved by A7 (Gazette instruments, archive.org items).
  - 12 Punjab and Haryana writs recovered by OCR as overlays, all RELEVANT.
  - 12 new ingestion candidates. These are held, not registered in `data/`.
- **HF dataset:** 16,255 files in total.
- **Not yet in the corpus:**
  - 8,006 excluded titles that would have to be downloaded again. This needs your approval for a download run.
  - 45 statutory acquisition requests from A4.
  - 63 remaining A7 targets.

## 5. OCR recovery and missed-judgment analysis (A1)

**Population**
- 8,077 flagged titles, of which 71 are held (including 46 preserved by A7); 8,006 still need re-acquisition.
- The Punjab and Haryana T1 set has 562 titles: 28 held, 534 not.

**Detector of unusable text**
- Precision 0.849.
- Recall 0.890 against the original labels, or 1.000 after 9 labels were corrected because those pages came from truncated files. Both figures are reported.
- Known gap: Hindi text with broken character shaping passes as usable.

**OCR benchmark**, measured on 5 English pages the author transcribed. With only 5 pages this is indicative.

| Engine | Character accuracy |
|---|---|
| PaddleOCR v5 mobile | 0.977 |
| PaddleOCR v6 medium | 0.974 |
| RapidOCR | 0.900 |
| Existing PDF text layer | 0.110 |
| PaddleOCR Devanagari (on the Hindi page) | 0.985 |
| Tesseract | Blocked; installing it needs your approval for a system package |

**OCR run:** 567 pages, none remaining.

**States across 136 held documents**

| State | Count |
|---|---|
| RELEVANT | 36 |
| IRRELEVANT | 4 |
| UNCERTAIN | 48 |
| MANUAL_REVIEW | 2 |
| INSUFFICIENT_TEXT | 32 |
| SOURCE_INCOMPLETE | 14 |

Under the corrected rule, IRRELEVANT among the original 90 fell from 26 to 2.

**Missed judgments**
- **Measured:** 12 of 12 Punjab and Haryana AFT writs were lost because of garbled text layers. 6 of 13 Supreme Court judgments were lost to keyword gaps.
- **Estimated:** about 3,760 Punjab and Haryana judgments (range 2,650–5,240) were deleted without readable text. How many of those are relevant is very uncertain.

**Rule now enforced:** a judgment is never marked irrelevant solely because its text could not be extracted. The rule fails closed: missing or incomplete inputs give INSUFFICIENT_TEXT. It is not yet adopted in `pipeline/judgments.py`; that is your decision.

## 6. Outcome extraction results (A2)

Outcome V4 was frozen at `9cdd5008`. Scoring was blind, weighted, with design-effect Clopper-Pearson 95% intervals, judged against the lower bound.

| Metric | Result | Target | Verdict |
|---|---|---|---|
| printed_disposal precision | 0.898 [0.838, 0.941] | ≥0.95 | NOT_MET |
| printed_disposal coverage | 0.833 [0.743, 0.902] | ≥0.85 | NOT_MET |
| substantive_result precision | 0.882 [0.815, 0.932] | ≥0.95 | NOT_MET |
| substantive_result coverage | 0.760 [0.671, 0.835] | ≥0.85 | NOT_MET |

- Unweighted coverage is 0.623. The large misses sit in oversampled cells that carry low weight.
- The earlier in-sample figure of 97.6% precision at 79.3% coverage is superseded.
- C11 F05 was fixed. C11 F08 remains partial.

## 7. Holdings extraction results (A3)

Holdings were frozen at `a520aa3a`. **H-HOLD is not scorable under protocol §4** because inter-coder span F1 was 0.566, below 0.6. On top of that:
- PD-01: no substantive holdings guideline existed.
- The adjudicator agreed with neither coder on 55 of 79 items, which together supply 113 of the 183 gold holdings.

**Descriptive results only:** precision 0.365 [0.241, 0.503], from 100 seeded predictions adjudicated blind; recall 0.517 [0.424, 0.608]. Precision fails under every definition tried.

**Coordinator decision D-HHOLD:** H-HOLD is treated as spent, and the next holdings evaluation needs a fresh draw under an independently written guideline. You may override this.

**Status of C11 F06 and F07:** not resolved; restricted.

## 8. Statutory evidence improvement (A4)

- **Version model:** 488 provision-level temporal records covering the Army Act, Army Rules, AFT Act and the links between BNS/BNSS/BSA and IPC/CrPC/Evidence Act.
- **Resolver:** `resolve_at(family, provision, date)` returns one of NOT_YET_IN_FORCE, IN_FORCE_CANDIDATES, UNDETERMINED or NO_VERSION_IN_FORCE. It handles deemed retrospective dates and instrument-date floors, and never assumes the latest text applies.
- **Other outputs:**
  - 21 new page-image checks.
  - EXACT 99 → 109, as proposals only.
  - 45 acquisition requests.
  - A 96-question adviser packet, merged into A8.
- **Reviews:** independently reviewed and confirmed.
- **In the app:** B1 shows A4 versions only as labelled research aids.

## 9. Knowledge graph improvement (A5)

- **Graph:** 13,406 nodes and 45,134 edges, with reviewed edges kept separate.
- **Contract export:** 34,567 records, with 0 validator issues.
- **Excluded from the export:** DISTINGUISHES, APPLIES, EXPLAINS and DOUBTS, which are low-reliability candidates.
- **Case numbers:** 99 Supreme Court case numbers were reconfirmed (HF overlay `844383f5`). The 266 unreviewed corrections were **not applied**.
- **Blind H-REL results** (descriptive):
  - relation_type precision 0.340 [0.161, 0.560];
  - `follows` recall 0.032;
  - `distinguishes` recall: 0 of 53.
- **Development sample:** a fresh 50-edge sample had 31 of 32 exported edges correct. This is not blind.
- **Known limitations:** FOLLOWS and OVERRULES edges point at judgments, not propositions, and FOLLOWS edges are mostly boilerplate.

## 10. Forms registry improvement (A6)

- **R04:** 21 of 22 families closed and verified from official Gazette copies. Row accuracy is 99.42% (95% interval 98.53–99.78).
- **IAFD-905:** deferred, because only paragraph 9 exists as official text.
- **Outside R04:** 8 forms with no official copy.
- **Registry:** 106 families, including 39 Navy families.
- **Oracle:** 86 synthetic, source-derived cases.
- **Restriction:** the R04 research restriction stays in place until there is legal approval.

## 11. Acquisition and preservation status (A7)

- **Acquired:** 63 of 126 targets, preserved at HF `9e3cf986` with 63/63 re-download matches.
- **Allow-list proposals:**
  - DESW: exact URLs only.
  - SCI: excluded, because of its CAPTCHA.
  - api.sci.gov.in: conditional.
  - archive.org: 85 item-scoped entries.
- **egazette TLS:** the server sends only its leaf certificate. The proposed fix pins the intermediates. Adopting it means applying patch 0003, which needs your approval.
- **Dispositions:**
  - F01 and F02 are closed via PR #51.
  - Patch 0003 is not integrated.
  - F04, the pinned-intermediate trust used before acceptance, is accepted retroactively as a process deviation. Verification was never weakened.
  - F06 is open: 20 redirect hosts were not probed.
- **Earlier PRs:**
  - #7: superseded.
  - #8, #9, #23: revise.
  - #17: close as superseded.

  These are recommendations only; nothing was closed.
- **Preservation and backup:**
  - The 48 Cycle 12 working-store PDFs are preserved at `5524c3d9`.
  - The owner-run backup tool is delivered.
  - **No verified second backup exists.** It needs owner-controlled storage, so the temporary copies stay in place.

## 12. Technology selection and supporting evidence

The full record is `docs/architecture/poc/POC_RESULTS_C13.md`, plus ADR-0005, which stays PROPOSED until the selected host is proven.

- **P1, hosting: ASP.NET Core 10 LTS on Kestrel as a Windows Service.**
  - Quiet-host rerun against the best Django setup: 12,689 vs 1,226 metadata requests per second, and 893 vs 639 PDF requests per second.
  - Memory: one process using 85–135 MB, against 240–270 MB for four Django workers.
  - These figures are indicative. A reviewed rerun with pinned cores and three runs kept ASP.NET ahead. The protected path handles 100–140 responses per second.
- **P2, search:** BM25 (lexical) with abbreviation expansion and an exact-identifier layer.
  - nDCG@10 is 0.72, against 0.62 for PostgreSQL full-text search, 0.61 for head-only hybrid, and 0.33 for dense search alone.
  - The identifier layer lifts exact-ID Target@1 from 0.53 to 0.82. These labels were AI-made and need human verification.
- **P3, embeddings:** bge-small-en-v1.5 at int8, if a dense layer is used. The base models were measured for speed only.
- **P4, PDF:** pypdfium2 for extraction, and PDF.js with an authenticated range transport for viewing. Avoid PyMuPDF (AGPL) in the shipped product.
- **P5, jobs:** a PostgreSQL SKIP LOCKED queue with leases, now with per-attempt lease tokens and dead-lettering, both added after a Codex review.
- **P7:** SBOM shows 0 known vulnerabilities, but there is a licence issue: PyMuPDF is AGPL.
- **pgvector:** built on Windows CI; blocked locally.
- **Windows-first, not Windows-only:** a platform-neutral core plus OS adapters, as recorded in ADR-0005. Linux production is not in scope.

## 13. Windows deployment results

All of the following is on **GitHub-hosted windows-latest, not the owner's selected host.**

- **Services:**
  - The ASP.NET Core and Django PoC services installed as Windows Services under virtual accounts, then smoke-tested, restarted and crash-recovered.
  - B1 installed, passed its smoke test and crash-restarted as a Windows Service: runs 45716813226 and 45719359168.
- **R2-N01 service-mode checks:** 16/16 passed against the installed service, in test mode.
- **Not done:**
  - selected-host acceptance;
  - TLS;
  - an offline installer, MSI or signed update (P6/P8);
  - production signing.

## 14. Application capabilities actually implemented (B1)

All of these were demonstrated over **290 real public documents**: 223 judgments, 27 Acts, 15 Rules, 5 Regulations, 16 notifications and others, totalling 11,352 pages. Every one was verified by the importer, and RM-001 is excluded.

- **Service and security**
  - ASP.NET Core 10 on Kestrel, loopback only, with a Windows Service lifetime.
  - Local accounts using PBKDF2 with 600k iterations; sessions; lockout; CSRF protection.
  - A strict content security policy, `no-store`, and content-free logs.
  - A single instance, enforced by a lock.
- **Importer and data integrity**
  - Verified materialisation and atomic activation.
  - Re-hashing on startup.
  - The service fails closed: it refuses to start without a restricted-material register that matches the active release.
- **Search**
  - BM25 over 38,445 verified passages.
  - An exact-identifier layer for sections, citations and case numbers.
  - Abbreviation expansion.
  - Instrument scoping, which states when an instrument is not held and flags ambiguity.
  - Professional query syntax, field filters and facets, and page-anchored snippets.
- **Documents and citations**
  - A protected PDF viewer on the R2-N01 path: authenticated bounded ranges, a credit ledger, and a withdrawal fence.
  - A text view with page markers.
  - Citation navigation per ASR-E06, including a retained earlier edition with a separate "Open current edition" action.
  - A single eligibility check on every delivery path.
- **Evidence and research aids**
  - A seven-axis evidence panel and provenance on every result.
  - Candidate data always labelled AUTOMATED_CANDIDATE_NOT_VERIFIED: A2 outcomes, A4 versions and A5 edges.
- **Admin and interface**
  - Admin withdrawal, which covers every copy of a document.
  - Practitioner and Commander views; light and dark themes; the full keymap; a screen-reader mode with single-key shortcuts turned off.
  - Responsive down to an 800 px window.
- **No generative or agentic AI.** The assistant workspace is shown but gated closed.

## 15. Screenshots of the actual application

There are 22 screenshots at scale 2 in `docs/architecture/b1/screenshots/`, about 4.5 MB in total. Examples:

| File | Shows |
|---|---|
| `b1-02-judgment-evidence-1920.png` | Identifier search, a judgment and the evidence panel |
| `b1-04-statute-section-75-1920.png` | Statute section view with A4 candidates |
| `syn-12-cited-copy-not-current.png` | ASR-E06 notice for a cited copy that is not the current edition |
| `b1-09-commander-abbreviation.png` | Commander view and abbreviation expansion |
| `b1-10-dark-text-view.png` | Dark theme text view |
| `b1-11-admin-overview.png` | Admin overview |
| `b1-12-gated-assistant.png` | The gated assistant workspace |

## 16. UI/UX review results

The independent B1 review ran three rounds. Its verdict: **accepted as the B1 baseline**.

**Defects found and fixed**
- Highlights that hid the underlying text.
- Every passage labelled as an identifier hit.
- A wrong instrument pinned to the top.
- Truncated bench lists: now labelled as incomplete in the display; the upstream metadata gap is deferred to Track A.
- Leaks of withdrawn documents into the A4 and A5 surfaces.

**PR #54 UX journeys**

| Status | Count | Notes |
|---|---|---|
| Passed | 11 | |
| Partially passed | 3 | |
| Partially failed | 3 | UX-01, UX-02, UX-11 |
| Blocked | 1 | UX-19: no Devanagari font |
| Not implemented | 2 | UX-07, UX-08 |
| Not executed | 1 | UX-18 |

**Not yet done:** screen-reader and zoom testing, and practitioner walkthroughs.

**Open P3s:**
- "AA s.69" style references are not recognised.
- No manual account unlock, which is your decision.
- The twin-withdrawal policy, which is your decision.

## 17. Functional acceptance tests

**B1 at `f71957e5`**, re-run by the independent reviewer. The post-Codex fixes at `b4088344` were verified by the author, by CI and by a coordinator spot-check:

| Suite | Passed |
|---|---|
| C# unit and integration, against real Kestrel and PostgreSQL | 88/88 (at `b4088344`) |
| Playwright journeys | 30/30 (at `b4088344`) |
| Importer | 66/66 |
| Design | 117/117 |
| Contract | 226 |

**PR #54 oracles, unmodified**
- **Retrieval:** 10/14 (9/14 on the first run). The 4 misses expect hybrid search. RET-02 and RET-12 are not independent evidence, because the ranking was changed after they were seen.
- **Data assurance:** DA-01 and DA-35 passed. DA-03 and DA-04 partly passed. The cases that depend on A4/A5 adapters are blocked.
- **Transport:** the oracle accepted the Linux traces.
- **Platform and backup:** passed.

**Integration gate on staging:** 32/32 steps and 1,043 tests (tranche 3). The tranche 4 figures are in the PR.

## 18. Security and offline validation

- **aftjabalpur.in:** hard-blocked, both in config and by a code-level `NEVER_CONTACT` backstop (PR #51).
- **RM-001 (the For-Official-Use-Only Regulations for the Air Force 2000):**
  - Excluded from every index, embedding, bundle, graph, external call and app surface, verified by tests and by every reviewer.
  - The B1 service refuses to start without a matching restricted-material register.
  - The owner decision note on what to do with it has been delivered.
- **B1 security testing:** the independent reviewer tried unauthenticated access, another user's session, CSRF, path traversal, range abuse and withdrawal bypasses. All are blocked after the F01 fix.
- **Logs:** content-free.
- **Network:** no external calls at runtime, and no generative AI.
- **R2-N01:** crash after a reservation keeps the full charge; a withdrawal survives restart. 2,560 bytes left the server after the withdrawal acknowledgement, against a bound of 64 KiB.
- **Exclusion store:** a one-way latch, fail-closed checks and crash-safe activation.
- **HF sync workflow:** skipped or not triggered on every merge.
- **Not done:** TLS, production signing (no key was generated), and a penetration test on the selected host.

## 19. Performance measurements

All of these were measured on a shared 4-core Linux VM or on hosted Windows. They are indicative, not results from the selected host.

- **B1 search:** p95 of 92 ms for a single user, and 308 ms with 10 concurrent users. That covers 38,445 passages.
- **Large-PDF bootstrap:**
  - A 46.8 MB PDF needed 4.2% of its bytes to reach a page near the end.
  - The B1 viewer renders in about 1.3 s.
  - On Windows CI: first page 289–606 ms, then a jump to the target page in 27–43 ms.
- **P1 throughput:** see §12.
- **OCR:** PaddleOCR v5 runs at about 26 s per page on the shared host.

## 20. Independent review and findings dispositions

**Findings register** (`C13-A9-CLOSEOUT/FINDINGS_REGISTER_C13.csv`): 261 rows.

| Status | Count |
|---|---|
| CLOSED | 181 |
| CLOSED_UNCONFIRMED | 25 |
| DEFERRED | 35 (including the 5 Cycle 12 carry-overs) |
| OPEN | 12 |
| ACCEPTED_DEVIATION | 8 |

- **No P1 is open.**
- **Open P2s:**
  - A7 F06: unprobed redirect hosts.
  - R2-N01 on the selected host.
  - B-PoC F07: independent probes on the selected host.
- Each row records how it was verified: INDEPENDENT_CONFIRMED, COORDINATOR_SPOTCHECK or AUTHOR_ONLY.

**Cycle 12 deferred P2s:** C11 F05–F08 and WS-G R04 all remain restricted. No restriction was lifted, because no target was met.

**Disposition of PR #53 (intelligence architecture)**
- Verdict: ACCEPT WITH CONDITIONS, as determined by the independent R3 review. The R3.1 Windows-first portability amendment was independently confirmed, and all 25 architectural closures stand.
- Integrated into staging in tranche 2 (PR #55, `dbe40b4f`).
- Reconciliation with ADR-0005 and the data contract (`docs/architecture/INTELLIGENCE_ARCHITECTURE_RECONCILIATION_C13.md`) was independently accepted. Of its 61 requirements: 16 compatible, 11 partial, 13 incorporated, 15 deferred and 6 in conflict.
- Recorded conflicts and redevelopment risks:
  - X1: IIS/ARR vs single-process delivery.
  - X2: SignalR vs polling.
  - X3: PDF.js range loading, since resolved by the R2-N01 PoC.
  - X4: who holds the exclusion witness; your decision.
  - X5: approval scope.
  - X6: lossy mapping of A4/A5 data.
  - X7: local withdrawals can be undone by a database restore; a B2 risk.
- **Architectural compatibility:** the B1 foundation already carries the hooks PR #53 needs, without fundamental redevelopment: the verified importer, the evidence axes, candidate labelling, a gated assistant workspace, and an exclusion store. No agentic AI was activated.

**Disposition of PR #54 (independent assurance)**
- Integrated in tranche 2 with its oracles and fixtures unmodified. The blind application holdout stays with its owner.
- ASR-E05 and ASR-E06 are addressed, with evidence in §14 and §17.
- R2-N01 is closable for the hosted-Windows PoC scope. Selected-host evidence is still outstanding.

**Process deviations disclosed**
- PD-01 and its addendum: holdings coding started without a substantive guideline, which was the coordinator's error.
- Evaluator-only column reads by A2, A3 and A5.
- A3's development exposure to 15 H-OUT and H-REL judgments.
- A store-pointer defect.
- The A7 F04 TLS process deviation.
- All coding was done by AI instances, because no human annotators were available.

## 21. Actual agent and model utilisation

- **Instances:** about 36 agent instances worked in this cycle. They covered workstream authors, the coders and adjudicators, the evaluator, and independent reviewers and confirmers.
- **Model:** every one ran Claude Opus 5.5. **Fable was not used**, in line with your instruction to conserve it.
- **Independence:** reviewers were always separate instances from the authors. Coders and adjudicators were fresh instances with only blinded packets.
- **Interruptions:** two usage-limit interruptions paused agents. Each resumed from saved state.
- **External automated review:** Codex reviewed PR #56 and raised 3 P2s, all real and all fixed. It then reviewed PR #57 and raised 1 P1 and 2 P2s, also all real and fixed at B1 `b4088344`:
  - P1: reloading a cited earlier edition substituted the current edition, which breaks ASR-E06.
  - P2: research state was not cleared on a 401.
  - P2: drain reconciliation built endpoints that did not match the real connections.

  These three were found after the A9 register was frozen. They are recorded here, and the register update is carried to Cycle 14.

## 22. Outstanding limitations and owner decisions

**Limitations**
- No Track A target has been met.
- The holdings ground truth is not reliable.
- About 3,760 Punjab and Haryana judgments are lost.
- 8,006 titles still need to be acquired again.
- There are no human annotators and no legal reviewer.
- R2-N01 has not been tested on the selected host.
- B1 has no semantic search, TLS, installer or signed update.
- A5's reproduction checks are not run in CI.
- No verified second backup exists.

**Owner decisions:** 22 in total, in `C13-A9-CLOSEOUT/OWNER_DECISIONS_C13.md`, each with its options and a recommendation. The main ones:
1. RM-001 retain, quarantine or remove. Recommended: retain it, restricted, while you ask the competent authority.
2. A location for the second backup, and a verify-on-restore run.
3. Production signing key custody.
4. Appointing a legal reviewer, and human annotators.
5. The selected Windows host and hardware, which unblocks R2-N01, F07 and P6/P8.
6. Approval of Tesseract or other system packages.
7. A re-acquisition download run for 8,006 titles (A1 dry-run plan ready).
8. Adopting the A1 pipeline states in `pipeline/judgments.py`.
9. Allow-list additions and patch 0003 (egazette TLS, redirect scopes).
10. Action on PRs #8, #9, #17 and #23.
11. Overriding D-HHOLD.
12. The B1 twin-withdrawal policy, and manual account unlock.
13. Whether to add PyMuPDF to CI, given its AGPL licence.

## 23. Application readiness assessment

B1 is a **working, independently accepted research prototype**. It is not production-ready.

- **Ready:** offline search and reading over verified documents, with correct citation and provenance behaviour and strong integrity and security controls on a single machine.
- **Not ready:**
  - selected-host acceptance;
  - TLS;
  - an installer, signed update and restore (P6/P8);
  - full-corpus scale (B2);
  - semantic search;
  - accessibility testing with assistive technology;
  - practitioner walkthroughs.
- **Readiness:** prototype milestone B1 is met. B2, the full corpus, and B3, depth, remain.

## 24. Legal knowledge readiness assessment

**Not ready for any operational or authoritative use.**
- AUTH-LEDGER is at version 0, with no legal approval.
- Under blind evaluation, outcome extraction misses its targets and holdings extraction cannot be scored.
- The treatment graph is descriptive only.

**What is usable for research:**
- verified source copies, with their provenance;
- the statutory version model, as candidates;
- forms R04, as candidates;
- the adviser package of 204 questions.

All of it stays clearly labelled and restricted to non-operational research until a legal reviewer is appointed and the questions are answered.

## 25. Proposed Cycle 14 priorities

These are proposals, not commitments.

1. **Corpus completeness.**
   - With your approval, run the re-acquisition of the 8,006 titles from allow-listed hosts.
   - OCR everything the new rules mark INSUFFICIENT_TEXT.
   - Adopt the A1 pipeline states.
2. **Holdings measurement.**
   - Write an independent holdings guideline, with legal-reviewer input if appointed.
   - Draw a fresh H-HOLD sample.
   - Use human or mixed coding.
3. **Outcome V5.** Target the documented failure cells: oversampled batch orders and Supreme Court cells. Re-evaluate on a fresh holdout.
4. **Legal review.** Appoint a reviewer and work through the P0 and P1 adviser questions, which unblocks restrictions.
5. **Track B, B2.**
   - Selected-host acceptance, including R2-N01 and F07, plus TLS.
   - An offline installer and signed update/restore (P6/P8), once your signing-key decision is made.
   - A full-corpus import and performance run at full scale.
   - Hybrid or semantic search measured on the blind PR #54 application holdout.
   - Accessibility testing with assistive technology, and practitioner walkthroughs.
6. **Backup.** Verify a second backup on owner storage.
7. **Allow-list.** Probe the 20 redirect hosts and decide on patch 0003.

---

### Tranche 4 integration

A pull request to staging carries:
- B1 at `f71957e5`, with its review record;
- the A7 dispositions;
- A8;
- the A9 registers;
- this report.

Merging it into staging is subject to CI and the gate. There is no merge to main.
