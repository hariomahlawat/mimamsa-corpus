# Cycle 12 completion report: Consolidation, Corpus Quality and Product Readiness

Branch `claude/c12-consolidation`. Staging is `e0b3e7d2`; main `21de3531` was not touched. Everything here is technical work. **None of it is formal legal validation**, and Cycle 12 being complete does not mean the knowledge base is complete.

## 1. Executive summary

- **Integration (WS-A).** PRs #40, #41, #42, #44, #43 and #47 were merged into staging through PR #48 (`0dd3640b`). TXN-DEMO was regenerated and its `--check` added to CI, with a negative-control test.
- **Blueprint (WS-C).** The product blueprint is in staging (PR #46, plus the review fixes in PR #49, `e0b3e7d2`). Fable confirmed it after a delta review.
- **Holdout (WS-D).** A fresh, double-coded, adjudicated holdout of 150 judgments now exists.
- **Outcome extractor V3 (WS-D)** was frozen, then scored under a pre-registered protocol. It **does not meet** the ≥95% precision / ≥85% coverage targets:
  - printed_disposal: 91.3% precision, 64.8% coverage;
  - substantive_result: 95.6% precision, 54.6% coverage.
- **Holdings extractor (WS-E)** was evaluated blind. It is **far below usable**: holding precision 41.7%, recall 29.3%.
- **Statutory citations (WS-F).** Proposed EXACT anchors rose from 42 to 99 after six promotions were withdrawn on adversarial review. The proposals are not applied.
- **Forms registry (WS-G).** Covers 67 form families, source-backed.
- **SC case numbers (WS-I).** The overlay stages 99 corrections. The originals are unchanged.
- **Review findings.** The register holds 622 rows: no P1 open, and 5 P2 deferred with recorded reasons.
- **Preservation (WS-B): done.** The 48 working-store copies are preserved in the private HF dataset at commit `5524c3d9` and byte-verified by a revision-pinned re-download. The full HF corpus is byte-verified (see the closeout addendum). The temporary copies are kept until a second persistent backup is verified. *(Corrected at closeout; this line previously said preservation was blocked.)*

## 2. Workstream status
See `TASK_REGISTER.md`.

| WS | Status | Key result |
| --- | --- | --- |
| A Integration | Done | PR #48 merged; 32/32 gate; ledger version 0; HF sync run 108 skipped |
| B Preservation | **Done** | Preserved to HF `5524c3d9` and byte-verified; 73 pages visually inspected, no markings; temporary copies retained |
| C Blueprint | Done | Fable confirmation and delta ACCEPT; PR #49 merged (docs only, no workflow triggered) |
| D Outcome V3 | Done, targets not met | See §5; independent review ACCEPT WITH CONDITIONS, conditions fixed |
| E Holdings | Done, far below usable | See §5 |
| F Statutory | Done | F-01..F-10 closed-verified |
| G Forms | Done | R01..R15 closed or documented deferral |
| H Acquisition | Done (partial by policy) | 25 first-tier judgments acquired. At closeout, 18 were ingested to HF (`15bd03cc`) and 7 excluded as not relevant. Other targets blocked by allow-list or TLS |
| I Metadata / backlog | Done | Overlay staged; adviser package; findings register |

## 3. Integration and repository status

**Staging**
- `0dd3640b` (PR #48): the six merges plus TXN-DEMO.
- `e0b3e7d2` (PR #49): the blueprint.
- The GitHub Actions HF sync workflow never ran an upload: run 108 was skipped, and PR #49 matched no workflow path. *(Corrected at closeout.)* Under the owner's approval and standing instruction, direct HF commits were later made from the session and byte-verified:
  - `5524c3d9`: preservation of the 48 copies;
  - `af7f9d06`: derived text and metadata for the 4 SC originals;
  - `15bd03cc`: ingestion of 18 judgments.

  All three are additive. The only automatic change was `.gitattributes`.

**Closed superseded PRs:** #44, #45 and #47 (branches kept). #46 was merged by the owner.

**`claude/c12-consolidation`**
- Contains staging (`a9bb5404` merge) plus the Cycle 12 deliverables in `legal_knowledge/audit_work/C12-CONSOLIDATION/` and one visible correction to C11 `HOLDOUT_EVALUATION.md`.
- No file outside `audit_work/` differs from staging.
- The PR into staging is opened after this report. It is not merged without owner instruction.

**Not done, by rule:** no merge to main, no ledger BIND, and no legal-authentication transaction.

## 4. Preservation and integrity

**Protected hashes, unchanged:**
- records_658 `9a8f0d19…`
- cases_53 `8b8d53cd…`
- CALIBRATION-02 `cfe5f408…`

**Ledger:** HEAD `0 443c4bdf…`, verified by the gate.

**The 48 working-store copies**
- Hashes match the register.
- Visual inspection of the 73 text-less pages found no restriction marking. Limit: markings that are very faint or cut off by the scan cannot be ruled out.
- The staging package is tested.
- **Persistent destination:** the private HF dataset (`legal_knowledge/preservation/c5_working_store/`, commit `5524c3d9`), byte-verified. *(Corrected at closeout.)* The earlier private-branch push was refused by the session's permission control and was not retried. **No second persistent backup is verified yet.** The owner holds the delivered ZIP (SHA-256 `214f11e8…`), so the temporary copies are kept.

**HF byte verification: done at closeout.** Every file at `5524c3d9` was downloaded and hashed: 15,971 files, 0 failures. The baseline of 4,103 copies is fully byte-verified (`copy_verification_c12/`). *(Corrected; this line previously said verification was not possible.)*

**WS-F promotions** depended on these copies. The availability and integrity risk is closed for all 274 dependent items (`copy_verification_c12/PRESERVATION_RISK_CLOSURE_C12.csv`). Evidence states are unchanged.

**Acquisition**
- The 18 truncated HC files are byte-identical at the source mirror.
- No copy was overwritten.
- Earlier disclosure: before C12-H's fix, the crawler sent the configured contact email in the `From:` header on 57 requests. It is now sent only if `MIMAMSA_CONTACT_EMAIL` is set.

## 5. Before and after indicators

| Indicator | Before (C11) | After (C12) |
| --- | --- | --- |
| Outcome holdout | 56 judgments, single-coded, spent | 150 judgments, double-coded (strict agreement 134/150), 16 adjudicated, 215 rows |
| Outcome strict precision (printed) | V2 84.1% on C11 holdout (exact labels) | V3 91.3% [85.4–95.0] on the fresh holdout; coverage 64.8% |
| Outcome substantive_result | not extracted | V3 95.6% [90.1–98.1]; coverage 54.6% |
| Judgment-level printed, common vocabulary | — | V3 = V2 = 105/115 (91.3%). V3's apparent lead comes from labels V2 cannot output |
| Population-weighted printed | ~79% (C11, V2) | 89.3% precision, 84.8% coverage (post hoc, court weights only; within-court stratum over-sampling not corrected, so not an unbiased corpus estimate) |
| Holdings: holding precision / recall | C11 ~12% recall of reviewer holdings | 41.7% [30.1–54.3] / 29.3% [22.0–37.8] (blind) |
| Statutory citations EXACT / PARTIAL / MISSING | 42 / 652 / 289 | 99 / 595 / 289 (proposed, not applied) |
| Forms registry | not started | 67 families, 215 occurrences, 541 fields; 39 statutorily prescribed (8 of them MML-only, not confirmed) |
| SC case-number corrections | 0 applied | 99 staged in a versioned overlay (originals unchanged; 266 unreviewed + 3 unresolved not applied) |
| Review findings register | none | 622 rows; P1 11/11 closed-verified; P2 112 closed-verified, 5 deferred |

## 6. Review results and dispositions
All reviews are in `reviews/`; the register is in `findings_consolidation/`.

| Review | Reviewer | Verdict | Disposition |
| --- | --- | --- | --- |
| PR #48 | Opus, independent | ACCEPT | P3 R48-05..07 deferred |
| PR #46 confirmation + delta | **Fable 5.2** | ACCEPT | P3 D-01..05 deferred |
| C12 coordinator tools | Opus | ACCEPT WITH CONDITIONS (4 P2) | All closed and confirmed. Agreement corrected 136→134/150; two judgments re-adjudicated |
| WS-F promotions | Opus, adversarial | ACCEPT WITH CONDITIONS (1 P1, 5 P2) | Remediated; confirmation: all closed-verified |
| WS-G forms | Opus | CONDITIONAL PASS (1 P1, 6 P2) | Remediated; confirmation: closed, or R04/R10/R13 documented deferrals |
| V3 holdout evaluation | Opus | ACCEPT WITH CONDITIONS (2 P2) | F01 closed-verified; F02 closed by stating the stratum-weighting limit (court × stratum weights deferred to Cycle 13) |
| C10 RR-01/02, RC-04; C11 F03/F04 | Opus confirmation | Closed-verified (F04 after a follow-up correction) | — |

**Deferred P2s (5)**
- C11 extraction F05 and F08: partial in V3.
- C11 F06 and F07: propositions. V3 has none; the WS-E successor is below target.
- WS-G R04: re-transcribe field lists from official copies before template use.

C11 F02 (single-coded holdout) is closed and confirmed by the V3 holdout review.

## 7. Tests and reproducibility

**Gate on `a9bb5404`:** 32/32 steps, 732 tests OK, AUTH-LEDGER verified at version 0, TXN-DEMO `--check` OK.

**Every C12 tool has a byte-reproducing `--check`:**
- holdout sample, agreement, truth;
- scnum overlay;
- adviser package (now builds to a temp directory);
- statutory build (27 tests);
- forms registry (27 tests);
- holdings (16 tests);
- extractor V3 (36 tests);
- the V3 evaluation;
- the holdings evaluation;
- the findings register.

**Pre-registration:** the V3 evaluation protocol and tool were committed in `761045d5` before the freeze in `1b46e368`.

**Python versions:** several tools were run only on Python 3.13; 3.11 lacks PyMuPDF and pytest here. This is recorded as a P3.

## 8. Actual agent and model utilisation

- **Fable 5.2 (`claude-fable-5-2`):** two reviews, the PR #46 confirmation and its delta review. Fable was conserved as directed.
- **Opus 5.5, all other roles:**
  - lead and coordinator;
  - execution agents for WS-D, E, F, G, H and I;
  - six blind holdout coders and two adjudicators;
  - a blind reference annotator;
  - a visual inspector;
  - independent reviewers, confirmers and evaluators.
- **Authorship separation:** no artefact was reviewed by its author. Where Opus reviewed Opus, the reviewer was a separate instance working on repo artefacts only.
- **Limit:** every coder, annotator and reviewer was an AI agent. No human has checked any figure here.

## 9. Outstanding legal and technical limitations

- **Outcome extraction** is not reliable enough for unreviewed use. Supreme Court multi-proceeding judgments have 42% coverage. Party-specific dispositions are not mapped. Some labels are convention-dependent.
- **Holdings and propositions:** about 6 in 10 predicted "holdings" are not holdings. This cannot support legal reasoning without human review.
- **Statutory anchors:** r.22 and r.23 stay PARTIAL (S.R.O. 258/2002 not held; C-01 wording conflict). r.15 is blocked by an unlocated "[or Military Secretary]" amendment. ~~The WS-F promotions depend on unpreserved copies.~~ *(At closeout, the copies are preserved and byte-verified on HF, and the availability risk is closed for the 274 dependent items.)*
- **Forms:** 32 families exist only in undated MML copies. Field lists are not yet transcribed from the official Gazette copies.
- **Acquisition:** the following remain unavailable: the Girish clarification, Ram Avtar, the egazette instruments and the DESW items. 4 SC files are HF-only.
- **Ground truth and reference sets** are single-pass AI work: two coders plus adjudication for outcomes, and one annotator for holdings.

## 10. Owner decisions required

1. ~~**Preservation destination** for the 48 copies: permit the private orphan-branch push, run `stage_and_verify.sh` to HF, or name another store. *Highest priority.*~~ *Done at closeout: preserved to HF `5524c3d9` and byte-verified.*
2. ~~**HF read credential**~~: done. A fine-grained network secret with read/write is in place, and the owner has directed that it be retained.
3. Confirm the **Legal Reviewer designation** in the blueprint.
4. **Allow-list** additions (archive.org storage nodes, `sci.gov.in`, `desw.gov.in`) or manual acquisition. Also a trust-store fix for `egazette.gov.in`.
5. Whether to **apply the SC case-number overlay** (99 staged).
6. **Legal adviser** review of `adviser_package/` (59 questions), plus review of the WS-F proposals and the forms "statutorily prescribed" classifications.
7. Handling of the **FOUO** AFR copy, and confirmation of the **contact-email** header policy.
8. Merge of the C12 PR into staging.

## 11. Application development readiness assessment

**Ready to start in parallel: the offline application foundation.** The blueprint is accepted, and the corpus layout, provenance model, manifests and review states are stable. The foundation covers:
- the ingestion pipeline;
- the document store and search index;
- the version and provenance model;
- the Admin/User access model;
- the review-state display;
- the Document Studio skeleton, with no legal rules yet.

All of this can be built against candidate data, provided the app treats every automated field as `AUTOMATED_CANDIDATE_NOT_VERIFIED` and shows that state to users.

**Not ready: legal-reasoning features.** These include:
- scenario advice;
- holding-based answers;
- automatic outcome statements;
- form compliance checks.

Outcome precision is short of target and coverage is far short. Holdings are far below usable. Statutory and forms layers are proposals awaiting legal review, and no legal authentication exists (ledger version 0).

**Recommendation:** start the application foundation in Cycle 13 behind a hard "candidate data" banner. Keep reasoning features gated on (a) legal-adviser sign-off and (b) re-measured extractor performance on a fresh holdout.

## 12. Cycle 13 work distribution (proposed)

| Track | Scope | Gate |
| --- | --- | --- |
| P0 Preservation | ~~Execute the owner-chosen destination; verify restore;~~ (done at closeout) Establish and verify a **second** persistent backup; then release the temporary copies | Owner choice of a second store |
| App foundation | Offline ingestion, store, search, provenance/version model, access model, candidate banners | Blueprint ADRs; no legal logic |
| Outcome V4 | SC multi-proceeding mapping; party-specific dispositions; coverage. Fresh holdout (the V3 holdout is now spent for tuning) | ≥95% / ≥85% on a new holdout |
| Holdings V2 | Opinion segmentation; court-voice vs quotation; holding vs reasoning. Second independent reference annotator | Measured P/R with inter-annotator agreement |
| Statutory | Acquire S.R.O. 258/2002 and the r.15 source; legal review of the 57 promotions; apply only approved ones | Legal adviser |
| Forms | Transcribe field lists from official copies (R04); Air Force and Navy instruments | Reviewer confirmation |
| Metadata | Owner decision on the overlay; reconfirm the 266 unreviewed in reviewed batches | Owner decision 5 |
| Backlog | 47 P3 deferred + 12 P3 open + 27 P3 closed by author only, in the register | — |

## Closeout addendum (2026-11-24, after owner instructions)

**Preservation (WS-B): done and verified.**
- The 48 working-store PDFs were uploaded to the private HF dataset at `legal_knowledge/preservation/c5_working_store/`, in HF commit `5524c3d99b6a069249012fecea75093b875a22c7`.
- A revision-pinned re-download verified them: 106/106 package checksums pass, and all 48 PDFs equal the manifest held in git.
- The owner also received the ZIP (SHA-256 `214f11e8…`).
- Temporary copies are retained. Releasing them is an owner decision.

**Complete HF corpus verification: done** (`hf_verification_c12/`).
- Every file at revision `5524c3d9` was downloaded and hashed: 15,971 files, 1.99 GB, 0 failures.
- 15,971 match the server hashes, and 15,689 are byte-identical to git `ad77758d`.
- `SHA256SUMS`, the raw filenames and `raw_manifest` show 0 mismatches.
- 5 files are newer on HF than in git: README, 3 schemas, and raw_manifest, which lacks 2 columns but has 0 differing cells. There are 277 HF-only and 42 git-only paths.
- The coordinator independently spot-checked 30 files; 30 of 30 match.
- Of the 23 incomplete files: the 4 HF-only Supreme Court files are complete on HF (they open and end with `%%EOF`), and 19 are truncated on HF too.

**Markings.** The FOUO RAF 2000 copy `4284820e…` is already in the private dataset. It has not been published. Removing or quarantining it is a decision for the owner. No new restricted material was found.

**Governance.** The owner's standing instruction is recorded in `CLAUDE.md`, `docs/governance/CORPUS_REPOSITORY_GOVERNANCE.md` and ADR-0004:
- HF is the central corpus repository, and routine HF operations are authorised.
- Deletion, publication of restricted material, visibility changes and legal authentication still need separate approval.

**Owner decisions: updated list.**
1. ~~Preservation destination~~ (done).
2. ~~HF credential~~ (done; a fine-grained network secret).
3. Release of the temporary working copies, now that verification has passed.
4. Handling of the FOUO RAF 2000 copy in the HF dataset.

The remaining items from §10 are unchanged: Legal Reviewer designation, allow-list, SC overlay, adviser review, contact-email header, and the PR #50 merge.

## Closeout addendum 2 (2026-11-24, owner closeout direction)

**Per-copy verification** (`copy_verification_c12/`)
- **Baseline:** exactly **4,103** copies: 4,039 held on both GitHub and HF, 16 HF-only, and 48 preserved. Every status rests on hashes computed from downloaded bytes:

  | Status | Copies |
  | --- | --- |
  | BYTE_VERIFIED | 4,062 |
  | BYTE_VERIFIED_INCOMPLETE_DOCUMENT | 19 |
  | BYTE_VERIFIED_TRUNCATED_TAIL_BASE_REVISION_PRESENT | 22 |
  | Missing, hash mismatch or not hosted | 0 |

- **Duplicate identities:** 128 copies, recorded separately.
- **Additions after the baseline:** the 18 ingested judgments, making **4,121** distinct source copies (the 7 excluded acquisitions are logged, not ingested).
- **Source-register overlay** for the 48 copies: hosted path, revision and SHA-256. The original registers are unchanged.
- **Preservation risk closed** for all **274** dependent items: 204 from the 1954 Army Rules and 70 from 12 SC judgments. Evidence states are unchanged.

**Judicial recovery** (`judicial_recovery_c12/`)
- The 4 HF-held SC originals were processed into derived text and metadata (`af7f9d06`).
- 18 of the 25 first-tier judgments were ingested (`15bd03cc`); 7 were excluded as not relevant, and there were 0 duplicates.
- All 55 added files are byte-verified.
- Coverage after ingestion: judgment records 4,259 → 4,277; unresolved incomplete files 23 → 19; first-tier titles held 0 → 18 of 1,790.
- Re-attempted acquisition: still blocked, because egazette's TLS certificate fails verification.

**Safety and controls**
- HF sync is now additive-only, with a guard and tests (R-04).
- Research-use isolation for the five deferred P2s is enforced by a test.
- Risk register: `RISK_REGISTER_C12.md`.

**Administrative**
- PR #36 closed as superseded: all 106 files are byte-identical in staging. Its branch is kept.
- Findings: 622 rows; P1 11/11 closed and confirmed; 5 P2 deferred with recorded reasons and restricted to research use.

**Cycle 13 planning:** `docs/planning/CYCLE13_EXECUTION_PLAN.md` and `docs/planning/OFFLINE_APP_TECHNOLOGY_ASSESSMENT.md`.
