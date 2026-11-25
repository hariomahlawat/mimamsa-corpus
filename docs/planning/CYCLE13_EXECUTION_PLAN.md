# Mimamsa Cycle 13 execution plan

- **Recorded:** 2026-11-24. **Revised:** 2026-11-25 by workstream B0 to apply the owner's Cycle 13 directive and the verified baseline (§0). This remains the single Cycle 13 plan; superseded passages are marked **[SUPERSEDED 2026-11-25]** in place rather than deleted.
- **Status:** Proposed plan for owner review. It does not authorise implementation, external acquisition, merges, legal-status changes, AUTH-LEDGER transactions or deployment. Each of those still needs the approvals named in `CLAUDE.md`, `docs/governance/CORPUS_REPOSITORY_GOVERNANCE.md` (ADR-0004) and the ADRs.
- **Companions:** [OFFLINE_APP_TECHNOLOGY_ASSESSMENT.md](OFFLINE_APP_TECHNOLOGY_ASSESSMENT.md) (Windows-native revision); [ADR-0005](../architecture/decisions/ADR-0005-APPLICATION-STACK.md) (PROPOSED); [capability traceability matrix](../architecture/CAPABILITY_TRACEABILITY_MATRIX.md); [security and deployment architecture](../architecture/SECURITY_AND_DEPLOYMENT_ARCHITECTURE.md); [data contract v1](../../app/contract/README.md); [UI/UX specification](../../app/design/README.md).
- **Inputs:**
  - `CLAUDE.md`;
  - `docs/README.md`, `docs/product/*` and `docs/architecture/*`, including ADR-0001 to ADR-0004;
  - `docs/governance/CORPUS_REPOSITORY_GOVERNANCE.md`;
  - from `legal_knowledge/audit_work/C12-CONSOLIDATION/`: `CYCLE12_REPORT.md` (with its closeout addendum), `TASK_REGISTER.md`, `holdout_v3_eval/RESULTS.md`, `holdings_eval/EVALUATION_HOLDINGS_C12.md`, `statutory_citations/README.md`, `forms_registry/README.md` and `findings_consolidation/README.md`.

## 0. Cycle 13 directive revision (2026-11-25)

### 0.1 Verified baseline

| Item | Value | Source |
| --- | --- | --- |
| GitHub staging `legal-knowledge/v2.5-staging` | `a4c0c382` (Merge PR #50, Cycle 12 closeout) | git |
| GitHub `main` | `21de3531` (never touched) | git |
| GitHub `raw-data` | `ad77758d` (data snapshot: `data/raw`, `data/text`, `data/meta`, manifests) | git |
| Hugging Face dataset head | `3864faf3bb24edef4bfb18fa0916cc788eb68d79` | HF |
| HF byte-verified revision | `5524c3d9`: 15,971 files; later additions `af7f9d06`, `15bd03cc`, `3864faf3` | C12 HF verification |
| Distinct source copies | **4,121** (after the 18 ingested first-tier judgments) | CYCLE12_REPORT §closeout |
| Judicial records | **4,277** (from 4,259) | CYCLE12_REPORT |
| Findings register | **648 rows**: P1 11/11 and P2 116 closed-verified; **5 P2 deferred** (C11 F05, F06, F07, F08; WSG-R04), research-restricted | `findings_consolidation/`; `CAPABILITY_RESTRICTIONS.csv` |
| AUTH-LEDGER | version 0 (HEAD `443c4bdf…`); no BIND, no legal approval | AUTH-LEDGER |
| Protected originals | records_658 `9a8f0d19…`; cases_53 `8b8d53cd…`; CALIBRATION-02 `cfe5f408…` | unchanged |
| Restricted material | Register `config/restricted_material.json` (RM-001: FOUO Regulations for the Air Force 2000 copy and its `data/meta` and `data/text` derivatives) on `claude/c13-gov` | governance workstream |

The figures in §2 that predate this table (HF `5524c3d9` as head, 622 register rows) are kept for history and marked superseded.

### 0.2 Directive constraints applied to this plan

- **Effort split:** Track A (legal knowledge) about **70%**, Track B (application) about **30%** (directive).
- **Windows-native production** (IIS or Windows Service; offline LAN browsers); no Docker, WSL, Hyper-V or Linux VM. Provisional reference hardware 16 cores / 64 GB / 1 TB SSD; GPU optional. Plan for about 20 GB of source data.
- **Performance target:** search p95 under 1 s at 10 concurrent queries on the reference hardware; accuracy is not sacrificed to meet it.
- **Signing key:** the production release-signing key stays in the owner's custody; agents use disposable test keys only.
- Preferred candidates are **evaluated, not presumed** (ADR-0005 evidence table, PoCs P1–P9).
- **Modular monolith with isolated workers.** Two roles (Admin, User); Legal Reviewer is a designation, inactive until appointed; ownership checks in the backend.
- **No legal reasoning or compliance logic in Cycle 13.** The commander assistant and legal-rule features are architected but gated off.

### 0.3 Workstreams

**Track A (legal knowledge, ~70%).** Directive numbering; the detailed sections in §4 keep their content and are relabelled.

| New id | Workstream | Branch / output | Detailed in |
| --- | --- | --- | --- |
| A0 | Evaluation infrastructure | `claude/c13-a0-eval` → `C13-A0-EVAL/` | §4 A0 |
| A1 | OCR quality and benchmark (new) | `claude/c13-a1-ocr` → `C13-A1-OCR/` | §0.4 |
| A2 | Outcome extractor V4 (closes C11 F05, F08) | `claude/c13-a2-outcome` → `C13-A2-OUTCOME/` | §4 "A2 (was A1)" |
| A3 | Holdings and propositions V2 (closes C11 F06, F07) | `claude/c13-a3-holdings` → `C13-A3-HOLDINGS/` | §4 "A3 (was A2)" |
| A4 | Statutory evidence and temporal layer | `claude/c13-a4-statutory` → `C13-A4-STATUTORY/` | §4 "A4 (was A3)" |
| A5 | Treatment and knowledge graph (candidate) | `claude/c13-a5-graph` → `C13-A5-GRAPH/` | §4 "A5 (was A4)" |
| A6 | Forms: official transcription (closes WSG-R04), AF/Navy | `claude/c13-a6-forms` → `C13-A6-FORMS/` | §4 "A6 (was A5)" |
| A7 | Targeted acquisition (owner-gated) | `claude/c13-a7-acquisition` → `C13-A7-ACQUISITION/` | §4 "A7 (was A6)" |
| A8 | Legal-adviser review packages | coordinator to assign | §4 "A8 (was A7)" |
| A9 | Deferred findings (C11 F05–F08, WS-G R04), P3 closeout and findings-register regeneration | coordinator to assign | §4 "A9 (was A8 + A9)" |
| GOV | Governance: restricted-material register RM-001, decision notes | `claude/c13-gov` → `C13-GOV/` | — |

**Track B (application, ~30%).** The twelve 2026-11-24 workstreams B1–B12 are regrouped into the directive's milestones B0–B3.

| New id | Content (directive) | Old items folded in | Gate |
| --- | --- | --- | --- |
| B0 | **Architecture plus PoCs**: this revision; ADR-0005 PROPOSED; traceability matrix; security architecture; `app/contract` v1; `app/design`; and PoC evidence P1–P9 from B-PoC (`claude/c13-b-poc`): P1 Windows hosting, P2 search and retrieval, P3 local embeddings, P4 document processing and PDF navigation, P5 background processing, P6 offline Windows installation, P7 security and licence review, P8 offline update and restoration, P9 UI/UX functional prototype | old B0 | GB1 (ADR-0005 accepted after P1–P9) |
| B1 | **Minimum functional research prototype**: offline install, local DB, immutable vault, a real corpus subset, FTS plus hybrid search where benchmarked, excerpts, PDF viewer, page navigation, provenance, basic auth, professional workspace (banner and separate axes included) | old B1, B3, B5, B6, B7 (basic), B10 (install and import), B11, B12 (baseline) | GB2 (B1 on a clean, network-disabled Windows host) |
| B2 | **Full eligible corpus**, incremental ingestion, Admin staging, publication and withdrawal (withdrawal leak-proof), release update, rollback, full restore | old B2, B10 (update and rollback) | independent + security review |
| B3 | **Research depth**: judgment intelligence, statutory explorer, knowledge graph, research workspace depth, Document Studio working sessions (no rules), AD option, audit review, hardening | old B4, B8, B9, B12 (hardening) | GB3 security review |

Capabilities per phase are listed in the [traceability matrix](../architecture/CAPABILITY_TRACEABILITY_MATRIX.md) (52 capabilities by first phase: 17 B1, 2 B2, 23 B3, 10 later/gated; several B1 capabilities complete in B2).

### 0.4 A1 OCR (new workstream, summary)

Objective: measure and improve OCR on the scanned subset (944 judgments / 4,705 pages OCR'd with Tesseract in C12) against hand-transcribed ground truth; per-page confidence and word boxes for the app (contract `derived_text.pages[]`); feed P6 (engine comparison on Windows). Acceptance: benchmark with pre-registered protocol, character/word accuracy with CIs, low-confidence page list; OCR text remains search-only (contract rule `OCR_QUOTING`).

### 0.5 Acceptance criteria for Cycle 13 (directive-aligned)

**Track A**
1. Each workstream's protocol and evaluation tool committed before its extractor is frozen; fresh, pre-registered holdouts; weighted estimates; shortfalls reported plainly.
2. The 5 deferred P2s closed and independently confirmed, or re-deferred with measured reasons; capabilities stay `NON_OPERATIONAL_RESEARCH_ONLY` until then (`tests/test_legal_audit_c12_research_isolation.py` keeps passing).
3. No legal state changed without a recorded human decision; AUTH-LEDGER stays at version 0.
4. Restricted material (register RM-001) absent from every derivative, index, embedding, package and external call.
5. Protected originals byte-identical.

**Track B**
1. ADR-0005 decided from reviewed P1–P9 evidence and accepted by the owner (GB1).
2. Data contract v1 adopted by Track A exports; `app/contract` tests green in `app-ci.yml`; restricted-material rule keyed on `config/restricted_material.json`.
3. B1 installs offline on a clean Windows host with networking disabled and serves a real corpus subset (GB2); by B2, signed bundle import of the full eligible corpus, tamper rejection, N→N+1, rollback, backup and full restore pass (P6, P8). Search p95 < 1 s at 10 concurrent queries on reference hardware without loss of accuracy (P2).
4. Banner on every route; separate status axes in API and UI; no single "verified" flag anywhere.
5. Security review with no P1/P2 open; the directive's threat tests (malicious PDF/Word, path traversal, file-type spoofing, oversized and decompression attacks, cross-session access, privilege escalation, SQL injection, XSS, unauthorised source access, withdrawn-source leakage via indexes and caches, document-borne prompt injection) pass (security architecture §9; GB3).
6. No legal-rule logic, compliance check or advisory output anywhere in the app; gated features refuse to enable.

### 0.6 Superseded content in this document

| Location | Superseded statement | Replacement |
| --- | --- | --- |
| §2 Corpus row | HF `5524c3d9` as current; "about 3,936 processed judgments" | §0.1 (head `3864faf3`; 4,121 copies; 4,277 judicial records) |
| §2 Findings register row | 622 rows | 648 rows (§0.1) |
| §3 diagram, §5 B0–B12 headings | Twelve Track B workstreams | B0–B3 (§0.3) |
| §4 headings A1–A9 | 2026-11-24 numbering | Directive numbering (§0.3); internal cross-references in §4 still use the old numbers where not marked |
| §5 B0 | PoCs P1–P7; P5 on Linux VM/Hyper-V; ADR file name `ADR-0005-OFFLINE_APP_STACK.md` | Directive P1–P9 (§0.3; assessment §16); Windows host; `ADR-0005-APPLICATION-STACK.md` |
| §5 B2 "network-less container" | Container isolation | Windows Services, Job Objects, NTFS ACLs, firewall (security architecture §3–6) |
| §5 B10 "Container images" | Image bundles | Offline Windows installer + signed data bundles |
| §6 IC-01 table | Outline contract | `app/contract` v1 (schemas, validator, tests) |
| §11 D-01 recommendation | Linux host or Hyper-V Linux VM | Windows-native (directive); hardware baseline confirmed provisionally |
| §10 R6 | Mitigation via Linux VM | Windows-native PoCs P1/P8 on a Windows host |
| §5 "Minimal first deliverable (M-B1)" and §12 Track B exit | M-B1 MVP including Admin upload round trip, on an air-gapped VM | B1 prototype on a real corpus subset on a clean, network-disabled Windows host; Admin staging/publication/withdrawal move to B2 |

## 1. Purpose and hard boundaries

Cycle 13 runs two tracks in parallel:

- **Track A, Legal Knowledge Improvement.** Make the extracted legal knowledge measurably better and reviewable. Hand the legal questions to people qualified to answer them.
- **Track B, Offline Application Foundation.** Build the air-gapped research application on candidate data. It needs no legal logic.

The following boundaries hold for the whole cycle.

1. **No legal advisory or automated compliance function is planned or built on unverified knowledge.** Specifically, none of the following is in scope:
   - scenario or commander advice;
   - answers built from holdings;
   - automatic outcome statements presented as fact;
   - mandatory checklists;
   - form compliance or readiness checks that apply legal rules;
   - LLM-generated legal answers.

   The Legal Reviewer designation does not exist, and AUTH-LEDGER is at version 0. The operational-use gate therefore stays **closed** (fail-closed: Document Studio §3.3).
2. **Everything automated stays `AUTOMATED_CANDIDATE_NOT_VERIFIED`.** Track B displays this state on every surface (workstream B11). Track A never raises an evidence or legal state without the review that the evidence policy requires.
3. **Author ≠ reviewer** for every deliverable. A reviewing AI agent is a separate instance that works only from repository artefacts. Where Opus reviews Opus, the record says so. Every figure produced in Cycle 13 by AI coders and annotators carries the limitation "no human has checked this figure" until a human does.
4. **Holdout hygiene.** The following sets are spent for tuning:
   - the V3 outcome holdout (150 judgments);
   - the C11 holdout (56);
   - the C12 holdings reference (30 judgments).

   They can be used as development data. New measurements use fresh, pre-registered holdouts. Each protocol and evaluation tool is committed before its extractor is frozen.
5. **Repository governance (ADR-0004).**
   - Hugging Face is the corpus master. Routine, non-destructive HF writes are authorised, but each must be verified by revision-pinned re-download and recorded in GitHub.
   - GitHub holds code and review records.
   - The following still need separate approval: deleting sources, publishing restricted material, changing visibility, AUTH-LEDGER BINDs, merges to `main`, and the corpus-upload workflow gate.
6. **Protected originals stay byte-identical:**
   - records_658 `9a8f0d19…`;
   - cases_53 `8b8d53cd…`;
   - CALIBRATION-02 `cfe5f408…`.

   Corrections are overlays only.

## 2. Starting position (from Cycle 12)

| Area | State at Cycle 13 start | Consequence for planning |
| --- | --- | --- |
| Corpus **[SUPERSEDED 2026-11-25: see §0.1]** | HF revision `5524c3d9`: 15,971 files, 1.99 GB, fully hash-verified. There are 277 HF-only and 42 git-only paths. 19 files are truncated at the source as well. About 3,936 processed judgments plus Acts and Rules. Many scans; 944 scanned judgments (4,705 pages) were OCR'd with Tesseract | Track B imports from a **pinned HF revision**. The HF/git path differences and the truncated files must be visible in the app, not hidden |
| Outcome V3 | printed_disposal precision 91.3% / coverage 64.8%; substantive_result 95.6% / 54.6%. Targets are ≥95% / ≥85%: **not met**. SC printed coverage is 42.3%. Population weighting by court only is biased by stratum over-sampling | Outcome V4 (A1), with a fresh holdout weighted by court × stratum |
| Holdings | Precision 41.7%, recall 29.3% (blind, single adjudicator). 15% of sampled holdings are opinion-attribution errors. Paragraph anchors are unreliable; page anchors are reliable | Redesign (A2). **Holdings are not shown to Users** in the app this cycle |
| Statutory | 99 / 595 / 289 EXACT / PARTIAL / MISSING (proposed, not applied). r.22, r.23 and r.15 are blocked on specific instruments or conflicts. Army Act, AFT Act, BSA and BNSS are held only as India Code compilations | A3, with legal-adviser review |
| Forms | 67 families, 215 occurrences, 541 fields; 39 statutorily prescribed candidates; 32 families MML-only. Air Force and Navy not assessed. WSG-R04 deferred | A5 |
| Treatment / graph | C11 candidates: 2,595 treatment rows and 11,076 statute–judgment link rows, unevaluated. V13-01 noise is known | A4 |
| Acquisition | 25 first-tier judgments acquired but not ingested. Girish, Ram Avtar, egazette instruments and DESW items are blocked by the allow-list or TLS | A6 depends on owner decisions |
| Findings register **[SUPERSEDED 2026-11-25: 648 rows, §0.1]** | 622 rows. P1: 0 open. P2: 5 deferred (C11 F05–F08, WSG-R04) | A8 closes them |
| Legal side | Adviser package of 59 questions, unreviewed. No Legal Reviewer designation. AUTH-LEDGER at v0 | A7. Any gate that needs legal review stays closed until a person reviews |
| Application | Blueprint accepted. The C12 report rates the foundation "ready to start in parallel" behind a candidate-data banner | Track B |

## 3. Track structure and dependencies

```
                 G0  Cycle start (owner confirms plan + decisions D-01..D-05)
                  |
     +------------+-------------------------------+
     |                                            |
 TRACK A  Legal knowledge                    TRACK B  Offline app foundation
     |                                            |
 A0 Evaluation infra (stratum counts,        B0 Stack PoCs -> ADR-0005  [GB1]
    sampler fixes, annotation tooling)            |
     |                                       B1 Data model, DB, vault
 A1 Outcome V4 --------+                          |
 A2 Holdings/props V2 -+--> A8 deferred P2s  B2 Ingestion + OCR + indexing
 A3 Statutory/temporal -+                         |
 A4 Treatment + KG -----+--> IC-01 data contract (candidate graph export)
 A5 Forms R04 + AF/Navy |                         |
 A6 Targeted acquisition (owner-gated)       B3 Search   B5 PDF citation  B6 Provenance
 A7 Adviser packages (needs a human)         B4 Research UI   B7 Access   B8 Graph UI
 A9 P3 backlog (capacity)                    B9 Document Studio foundation (no rules)
     |                                       B10 Deployment + snapshot update
     |                                       B11 Candidate banner (cross-cutting)
     |                                       B12 Security baseline + network-denied tests
     |                                            |
     +------------------+-------------------------+
                        |
       GX  Release bundle R13-candidate: corpus at pinned HF revision + Track A
           candidate outputs, all labelled candidate, imported offline
                        |
       GC  Cycle close: reports, register update, owner review
```

**Coupling between tracks is deliberately one-way and thin.**

- Track A publishes versioned candidate artefacts (CSV/JSONL with schema, tool `--check`, sha256) in GitHub, with corpus objects on HF.
- Track B consumes them only through the **IC-01 data contract** (§6), at a pinned revision, as candidate data. Nothing in Track B writes back to Track A artefacts, HF originals or registers.
- Track B can finish every acceptance criterion without any Track A improvement. Track A can finish without the app.

## 4. Track A: Legal Knowledge Improvement

Default staffing:
- **Author:** an Opus execution agent.
- **Reviewer:** a separate Opus instance, independent and adversarial where stated.
- **Fable:** reserved for at most the reviews marked ★, to conserve it as in Cycle 12.
- **People:** human roles are named explicitly. No AI agent records a legal decision.

### A0. Shared evaluation infrastructure (prerequisite for A1 and A2)

| Item | Content |
| --- | --- |
| Objective | Remove the known defects in the measurement tooling before new holdouts are drawn |
| Scope | (a) **Corpus stratum counts** per court × stratum, using the V3 stratum definitions (batch_or_multi, disagreement, pension_or_disciplinary, other) and a deterministic, committed classifier, so that inclusion probabilities are known. (b) Fixes for the C12 coordinator-tools findings with no disposition: F05 (enforce the text-layer check in the sampler), F06 (validate raw_path), F07 (remove the stratum hint from the coder view; record the Delhi shortfall) and F08 (restrict the reconfirmation branch by C11 status). (c) Reusable double-coding and adjudication tooling for spans (holdings), not only labels. (d) Exclusion lists: V3 holdout, C11 holdout, C12 holdings reference and dev sets |
| Deliverables | `C13/eval_infra/` containing the stratum classifier with `--check`, the `STRATUM_COUNTS.csv` table, sampler v2 with tests, coder-view tests, and exclusion manifests |
| Depends on | Nothing (it starts first) |
| Acceptance | Stratum counts reproduce byte for byte. The sampler refuses text-less files and invalid paths (tests). A coder-view test shows that no stratum, court-weight or extractor output field leaks to coders. Coordinator-tools F05–F08 are recorded as closed and confirmed by an independent reviewer |
| Author / reviewer | Opus execution agent / independent Opus instance |
| Gate | GA0: infra accepted before any A1 or A2 sampling |

### A2 (was A1). Outcome extractor V4

| Item | Content |
| --- | --- |
| Objective | Reach strict precision ≥95% and coverage ≥85% for printed_disposal and substantive_result on a fresh holdout, with court × stratum weighted estimates. If the targets are missed, report the shortfall honestly |
| Scope | (a) **SC multi-proceeding judgments**: segment proceedings (CA, SLP, WP or connected matters), including proceedings identified by the impugned order (V3 eval F06). This targets SC printed coverage of 42.3%. (b) **Party-specific dispositions**: map the disposal per appellant or respondent and per proceeding, where the judgment differentiates. (c) Coverage: reduce ABSTAINED (41) and PROCEEDING_UNMATCHED (34) for the printed field, and ABSTAINED (64) and PROCEEDING_UNMATCHED (30) for the substantive field. (d) C11 **F05**: "partly succeeds" handling and the extent rule (V3H139 mislabels full relief as partly_allowed). (e) C11 **F08**: the court's own operative sentence after a closing quote; a human-readable report on the 51 `ONLY_QUOTED_DISPOSITION_LANGUAGE_FOUND` rows. (f) "transferred" disposals (missed 5/13, V3 eval F08) |
| Fresh holdout | Stratified by court × stratum, with inclusion probabilities recorded from A0 counts. **Weighted estimates** use Horvitz–Thompson weights; unweighted figures are reported alongside. Size target: ≥200 judgments (owner may adjust), with an SC share large enough for a per-court CI half-width of about ±7 points. Coding: two blind coders, then adjudication; strict agreement and kappa reported. Excludes every spent set. **Recommended (owner decision D-07):** a human legal assistant second-codes a random 20% subsample, so AI–human agreement is measured at least once |
| Deliverables | `C13/outcome_v4/` (extractor, tests including F05/F08 cases), `C13/holdout_v4/` (sample, codings, adjudication, truth hash), `C13/holdout_v4_eval/` (pre-registered `PROTOCOL.md`, tool, `RESULTS.md`), F08 hand-review report |
| Depends on | A0 (GA0) |
| Acceptance | (1) Protocol and evaluation tool committed before the V4 freeze commit. (2) The V4 tool hash is frozen before scoring. (3) RESULTS gives strict and family precision, coverage, Wilson and cluster-bootstrap CIs, weighted and unweighted per-court and per-stratum figures, and a failure taxonomy. (4) Targets met or not met, stated plainly; no post-hoc change to headline figures. (5) Traceability: excerpt at offset and page consistency ≥ V3 levels. (6) C11 F05 and F08 are closed and confirmed, or re-deferred with reasons |
| Author / reviewer | Opus extractor author; separate Opus coders (2) and adjudicator; independent Opus evaluator, who also scores; reviewer ★ Fable (optional) for the protocol only |
| Gate | GA1 protocol pre-registered → GA2 holdout coded and frozen → GA3 extractor frozen → GA4 independent evaluation review. Even if the targets are met, outcomes stay candidates: the app may show them **labelled with measured precision and coverage**, never as fact |
| Risks | AI-only truth labels (mitigated by D-07). SC segmentation errors look like coverage gains (check by per-proceeding matching). Over-fitting to dev (mitigated by exclusion manifests) |

### A3 (was A2). Holdings and proposition redesign (Holdings V2)

| Item | Content |
| --- | --- |
| Objective | Replace sentence-ranking "holdings" with an opinion-aware, voice-aware proposition model, and measure it against a **two-annotator** reference with agreement statistics |
| Scope | (a) **Opinion segmentation**: sole, lead, concurring, separate and dissent; split verdicts (Gene Campaign: from p.204 each judge writes separately); dissent cues anywhere in an opinion, not only in the first 3,000 characters (R.P. Yadav). (b) **Court voice vs quotation**: quote-boundary handling (shared with A1 F08); patterns for cited precedent such as "the issue for consideration before this Court was", "There the question was" and "The question before this court was"; submissions vs court rejection ("This submission is clearly misconceived."). (c) **Holding vs reasoning**: separate classification of factual recitals, rule restatements, reasoning steps, operative disposals and holdings. Remove the per-opinion cap and rank cut-off that pushed 44 true holdings into `reasoning`. (d) A **proposition record** following Architecture §4 `LegalProposition`: opinion, voice, scope, qualifiers, anchor (page always; paragraph only where the judgment has numbered paragraphs), and the provision version construed where stated. (e) C11 **F06** (proposition recall) and **F07** (origin label precision) |
| Reference set | A new stratified sample (proposal: 40–60 judgments, over-sampling multi-opinion SC judgments; exclude the 30 C12 reference judgments, which become dev data). **Two independent blind annotators**, working from a written annotation guideline that the legal adviser reviews (A7) before annotation starts. Agreement reported as span-level F1 and kappa on item type, with adjudication |
| Deliverables | `C13/annotation_guideline_holdings.md` (versioned), `C13/holdings_reference_v2/`, `C13/holdings_v2/` (segmenter, voice classifier, proposition builder, tests), `C13/holdings_v2_eval/` (pre-registered matcher, results) |
| Depends on | A0. Guideline review by the legal adviser (A7) is desirable; if no person is available, annotate under the guideline marked "not legally reviewed" |
| Acceptance | (1) Inter-annotator agreement reported before the extractor is evaluated. If span F1 on holdings is below 0.6, revise the guideline first (proposed threshold). (2) True precision is measured by blind adjudication over the full predicted set or a seeded sample of ≥100, with judgment-level macro figures beside the pooled ones. (3) Opinion-attribution error rate is reported separately and is below 5% of sampled holdings (proposed). (4) Proposed "candidate display" bar, **for owner decision D-08**: holding precision ≥80% and recall ≥60% on the new reference. Below that bar, holdings remain hidden from Users in the app. (5) C11 F06 and F07 closed and confirmed, or re-deferred with measured reasons |
| Author / reviewer | Opus extractor author; annotators = two separate Opus instances, **or preferably one human legal annotator and one AI** (D-07); independent Opus evaluator; ★ Fable optional for the guideline and matcher |
| Gate | GA1 guideline + matcher pre-registered → GA2 reference frozen with IAA → GA3 freeze → GA4 evaluation review |
| Risks | The definition of a holding is legally contested (needs the guideline and adviser input). Large judgments dominate pooled figures (report macro figures). The two annotators share a model's biases if both are AI (the human annotator mitigates this) |

### A4 (was A3). Statutory evidence and temporal applicability

| Item | Content |
| --- | --- |
| Objective | Turn the WS-F proposals into reviewable decisions and build the evidenced provision-version layer needed for temporal questions |
| Scope | (a) **Blockers**: S.R.O. 258/2002 (r.22, AR-030); the instrument behind "[or Military Secretary]" (r.15, OQ-A-10/GAP-15); S.R.O. 348/1960 and 404/1960; Gazette copies of the Army Act, AFT Act, BSA and BNSS, replacing India Code compilations of undocumented provenance. Acquisition runs through A6. (b) **Legal-adviser package** (A7) covering the 57 promotions, reserved conflicts C-01 (r.23 "not"), SC4-01 (r.182) and C-03 (r.177), r.135 "or abstract" scope (F-09) and r.15B applicability (F-06). (c) **Apply only adviser-approved proposals**, as a versioned overlay with owner approval. Originals are untouched. (d) **Section-level provision versions**: a `ProvisionVersion` dataset with valid-time intervals, amending instrument, commencement evidence and `amendment_chain_status`. Each row cites a page anchor in a registered copy. (e) **Temporal fixtures TA-01 to TA-05** (Architecture §7.1) as *representational* tests. Their identities, dates and sections must come from verified sources; where evidence is missing, the fixture asserts "blocked or unresolved" rather than a date. (f) WS-F P3s: C-01 (prove that no state depends on the review CSV) and C-02 (image-check the 16 text-layer-only items) |
| Deliverables | `C13/statutory/`: provision_versions.jsonl + schema, fixtures, adviser questions (feeding A7), overlay (only after approval) |
| Depends on | A6 for instruments; A7 and a human adviser for decisions; owner approval to apply the overlay |
| Acceptance | Every provision-version row has a page anchor or an explicit `UNRESOLVED` reason. No EXACT state is applied without a recorded adviser decision. Fixture tests pass in "representational" mode. `--check` reproduces. Independent adversarial review: no P1/P2 open |
| Author / reviewer | Opus / independent adversarial Opus. Legal decisions: human legal adviser only |
| Gate | GA5 legal-adviser decision before any state is applied |
| Risks | The adviser is unavailable (proposals stay proposals; this is acceptable). Instruments cannot be acquired (the blockers stay recorded) |

### A5 (was A4). Judicial treatment and knowledge graph (candidate layer)

| Item | Content |
| --- | --- |
| Objective | Produce a typed, evidence-anchored **candidate** graph that the app can explore, with measured precision per edge type |
| Scope | (a) **Identity canonicalisation**: Judgment, Proceeding, JudgmentRendition and Opinion, with file hash ≠ judgment ≠ proceeding (Architecture §4). Includes the decision on the SC case-number overlay (99 staged; owner decision D-09) and reconfirmation of the remaining 266 in reviewed batches. (b) **Edges**: `cites` (automatic, case-citation resolution to judgment IDs) and statute→judgment links from the C11 11,076 rows, normalised to provision IDs. Treatment candidates (C11: 2,595 rows) are typed as `follows`, `distinguishes`, `overrules` and so on. All non-`cites` types are `llm_proposed` or `extracted`, pending human verification. (c) Fix C11 V13-01 to V13-04 (relations), with V13-01 first; the four noisy adviser rows remain DISREGARD. (d) **Blind precision sample** per edge type and evidence-sentence verification. (e) Export conforming to IC-01 |
| Deliverables | `C13/graph/` containing nodes.jsonl, edges.jsonl, schema, `--check`, evaluation report and the IC-01 export |
| Depends on | A0 tooling for sampling; A2 for opinion and voice attribution of treatment sentences (can start with C11 origin labels) |
| Acceptance | Every edge has a source anchor (copy sha256, page, evidence text), type, confidence class and extractor version. Precision is reported per type with CIs. **No `overrules`/`supersedes` edge is marked anything above `llm_proposed`/`extracted` without a human decision.** Absence of an edge is never represented as absence of adverse authority (UI contract, B8) |
| Author / reviewer | Opus / independent Opus evaluator |
| Gate | GA4 evaluation review, then the IC-01 export accepted by B-side contract tests |
| Risks | Citation-resolution ambiguity (keep it unresolved rather than guess). Treatment noise misleading Users (B8 labelling, per-type precision shown) |

### A6 (was A5). Official form transcription (WS-G R04) and Air Force/Navy coverage

| Item | Content |
| --- | --- |
| Objective | Close WSG-R04: field lists come from the official copies, not MML. Extend discovery to Air Force and Navy instruments |
| Scope | (a) **Re-transcribe field lists** for the 22 BOTH families whose field set comes from MML 2, plus the official-only families, from page images of the 1954 Gazette, the 1993 amendment and the AFT (Procedure) Rules. Use a two-person method: one transcriber agent and a separate verifier agent, each reading the page image. Record bounding boxes (`page_region_bbox`, currently empty). (b) Resolve the conflict queue *documentarily* (offence report "Findings" column; IAFD-919C vs 919C/919A; "83-84" vs "83 to 85"). The legal effect goes to A7. (c) **Air Force and Navy**: acquire official copies (A6), then register forms under the same method. Coverage records follow the blueprint vocabulary, with no aggregate percentage. (d) WS-G R10 (capped ranges) and R13 (one run under the app's standard Python), if capacity allows |
| Deliverables | `C13/forms_registry/` v1.2 with `field_set_version=OFFICIAL_TRANSCRIBED` where done, a divergence queue, AF/Navy coverage rows and page-image check records |
| Depends on | A6 for AF/Navy copies and S.R.O. 348/404 of 1960 |
| Acceptance | Every re-transcribed field has an image check by the verifier, who is not the transcriber. Build fails on a label mismatch for native text. WSG-R04 confirmed closed by an independent reviewer. **No template is marked usable**; legal approval state stays `RESEARCH_ONLY` |
| Author / reviewer | Opus transcriber / separate Opus verifier / independent Opus reviewer |
| Gate | Reviewer confirmation. Template use stays gated on T2 legal approval (Document Studio §3.3), which does not exist |
| Risks | Poor scan legibility (record `ILLEGIBLE` with the image reference; never fill from MML) |

### A7 (was A6). Targeted acquisition (owner-gated)

| Item | Content |
| --- | --- |
| Objective | Acquire the specific missing sources that block A3, A5 and the golden set, within policy |
| Targets | Girish Kumar clarification (2026 INSC 1113); Ram Avtar (C.A. 418/2012, 10-12-2014); 10 egazette LOCATED_NOT_ACQUIRED instruments; DESW items; S.R.O. 258/2002; the r.15 instrument; S.R.O. 348/1960 and 404/1960; official Air Force and Navy rule copies; Gazette copies of the Army Act, AFT Act, BSA and BNSS; complete copies of the 19 truncated files from another official source; **ingest the 25 first-tier judgments already acquired** (HF upload under ADR-0004, then pipeline). Cross-check each target against golden-set coverage (`reports/golden_coverage.md`) |
| Depends on | Owner decision D-04: allow-list additions (`sci.gov.in`, `desw.gov.in`, archive.org storage nodes) and a trust-store fix for `egazette.gov.in`, or manual acquisition by the owner. The contact-email header policy (C12 §10 item 7). The 25 T1 ingestion can proceed now |
| Acceptance | Robots and politeness rules are obeyed. Every request is logged. Every file is hash-verified, preserved on HF with revision-pinned re-download verification, and recorded in GitHub. No CAPTCHA bypass, login or paywall: a blocked source is reported, not worked around. No commercial databases |
| Author / reviewer | Opus / independent Opus |
| Risks | The SC portal CAPTCHA blocks automation (manual acquisition by the owner is the fallback) |

### A8 (was A7). Legal-adviser review packages

| Item | Content |
| --- | --- |
| Objective | Give a qualified human the questions only they can answer, in a form that is quick to review. This is the only route by which legal states can change |
| Packages | (1) C12 package (59 questions), unchanged; add a decision-record template. (2) **Statutory**: the 57 WS-F promotions, C-01, SC4-01, C-03, r.135, r.15B. (3) **Forms**: the 39 statutorily-prescribed classifications under the mechanical "shall" rule, the AR 4(1) caveat, and the conflict queue. (4) **Evaluation conventions**: C11 F12 (six holdout truth rows), C11 C-11 (Prithi Pal Singh Bedi, Ratan Singh) and outcome label conventions. (5) **Annotation guideline** for holdings (A2). (6) C10 RR-04 (authority order of open-data copies vs SCR renditions) |
| Deliverables | `C13/adviser_packages/` with a builder tool, `--check`, excerpt verification, provenance and SHA256SUMS. A decision-record format: question id, decision, reviewer, capacity, date and scope, recorded **outside** the package |
| Depends on | A human legal adviser (owner decision D-03). The Legal Reviewer designation, if decisions are to be recorded as `Approval` records under Document Studio §3.3 |
| Acceptance | Each package builds reproducibly. Every excerpt is verified on its stated page or marked as having no text file. Packages contain no conclusions, only competing readings. Applying any decision is a separate reviewed change with owner approval |
| Author / reviewer | Opus builder / independent Opus reviewer (technical); a human legal adviser answers |
| Risks | **No human reviewer becomes available.** Then nothing legal moves, and Cycle 13 still delivers measurements and the app foundation |

### A9 (was A8). Deferred findings closure (C11 F05–F08, WS-G R04), P3 closeout and findings-register regeneration

| Finding | Workstream | Closure evidence required |
| --- | --- | --- |
| C11 F05: "partly succeeds" and extent rule | A1 | Tests for both C11 sentences plus V3H139. V4 holdout failure taxonomy shows no residual case, or a re-deferral with a count |
| C11 F06: proposition recall | A2 | Recall measured against the two-annotator reference, with CI |
| C11 F07: origin label precision | A2 | Per-origin precision on a blind sample, with ≥0.9 for court voice as proposed |
| C11 F08: own operative sentence after quote | A1 (+A2 shared quote logic) | Quote-closing tests, plus a hand-review report on the 51 rows |
| WSG-R04: field lists from official copies | A5 | Re-transcription with independent image verification |

Each closure is confirmed by an independent reviewer and recorded in the findings register (`findings_consolidation/`, regenerated with `--check`).

### A9 continued (was A9). P3 backlog (capacity permitting)

The register lists 47 P3 deferred, 12 P3 open and 27 P3 closed by the author only. Take the engineering items whose `cycle13_action` is concrete, for example AUTH-LEDGER CB-01/02, C10 RR-03/RR-06, the C12 confirmation P3s and the PR #46 wording items D-01/D-03. Close them with an independent confirmation. **Standardise one Python version** for tools and app images (the C12 P3 notes a 3.11/3.13 split).

## 5. Track B: Offline Application Foundation

Every Track B workstream builds **capability without legal rules**. The app is a research library over candidate data. Default staffing:
- **Author:** an Opus execution agent per workstream.
- **Code review:** a separate Opus instance.
- **Security review:** a separate Opus instance, distinct from the code reviewer, for B2, B7, B9, B10 and B12.
- **Fable:** ★ optional for ADR-0005.

The stack below is the recommendation of the technology assessment and is confirmed or changed by B0.

### B0. Stack selection and proofs of concept → ADR-0005 **[PARTLY SUPERSEDED 2026-11-25: §0.3, §0.6]**

| Item | Content |
| --- | --- |
| Objective | Confirm the recommended stack with measured PoCs on representative data, and record it in ADR-0005 |
| PoCs (from the assessment §16) **[SUPERSEDED 2026-11-25: renumbered P1–P9 for Windows; see assessment §16 and ADR-0005 §6]** | P1 hybrid retrieval quality: PostgreSQL FTS vs true BM25 (embedded Tantivy) vs vector vs hybrid, on a retrieval benchmark. P2 embedding and reranker models on CPU: quality and throughput. P3 PDF.js page anchoring and highlighting for native and OCR'd scans. P4 OCR: Tesseract vs PaddleOCR on the low-confidence page set (plus Prism, if D-10 makes it available). P5 air-gapped install and update on a clean VM (and on Windows via a Linux VM if D-01 requires Windows). P6 PostgreSQL-backed job queue under ingestion load. P7 licence review of the dependency tree (PyMuPDF AGPL, Ghostscript, model licences) |
| Retrieval benchmark | Dev queries are written fresh by an agent who has not seen the golden set. **The 50-question golden set is held out** for evaluation only. Relevance judgments are double-coded |
| Deliverables | `docs/architecture/decisions/ADR-0005-OFFLINE_APP_STACK.md`; `app/poc/` reports with raw measurements; a licence inventory |
| Acceptance | Each PoC reports measurements on stated hardware, with go or no-go against the assessment's criteria. ADR-0005 lists the choice, reasons, risks and exit paths. Licence inventory has no unresolved copyleft question (owner decision D-02 where needed) |
| Author / reviewer | Opus / independent Opus; ★ Fable optional |
| Gate | **GB1: ADR-0005 accepted by the owner** before B1 to B10 build beyond throwaway prototypes |

### Old B1 → B1 Foundation. Data model, database and document storage

- **Scope:**
  - PostgreSQL schema for the architecture entities needed now: SourceCopy, SourceDocument, LegalInstrument, ProvisionVersion (read-only from IC-01), Judgment, Proceeding, Opinion (candidate), ExtractedPassage with page and character anchors, CandidateRelationship, AdminSubmission, IngestionJob, PublicationRecord, ReleaseGeneration, AuditEvent and WorkingDocumentSession.
  - Status as **separate axes** (Architecture §6 reconciliation table). Never a single `verified` flag. Axis-qualified values.
  - A content-addressed **evidence vault** on the filesystem (`vault/sha256/<2>/<hash>`) for immutable originals, and a separate derivatives store keyed by (sha256, pipeline version).
- **Acceptance:**
  - Migrations are reproducible.
  - A constraint test shows that publication and legal approval never share a field.
  - A vault write is verified by re-hash, and originals are immutable (read-only mount in workers).
  - The IC-01 import round-trips.
- **Author / reviewer:** Opus / independent Opus.

### Old B2 → B1 Foundation. Offline ingestion and indexing (OCR included)

- **Two entry paths sharing one pipeline:**
  - **(a) Release import:** the corpus at a pinned HF revision (B10).
  - **(b) Admin upload (CORPUS_INGESTION):** stage → validate and quarantine (type, size, content sniffing, malformed-file checks) → preserve bytes and hash → extract text (PDF text layer if sane, else OCR) → passages with page markers → metadata candidates → candidate links → Admin review → publish.
- **OCR:**
  - The engine chosen in B0 P4, with per-page confidence.
  - Pages below threshold are flagged in staging and carry a warning after publication. They are never silently trusted.
  - OCR text is for search, not for quoting; the UI says so.
- **Isolation:** **[SUPERSEDED 2026-11-25]** ~~workers run as an unprivileged user in a network-less container~~ → workers run as separate Windows Services with low-privilege identities, outbound firewall block, read-only vault ACLs and Job Object limits (security architecture §3–6).
- **Acceptance:**
  - Full import of the pinned revision completes with a per-file report: OK, OCR'd, low-confidence, truncated, failed.
  - An interrupted job resumes without re-preserving or duplicating.
  - Re-import of the same bytes deduplicates (aliases recorded).
  - A same-identity, different-hash copy is kept as an alternate.
  - All ingestion acceptance tests in `CONTINUOUS_DOCUMENT_INGESTION.md` §7 that do not involve legal rules pass.
  - A network-denied run passes.
- **Author / reviewer:** Opus / independent Opus plus security reviewer.

### Old B3 → B1 Foundation. Full-text and semantic search

- **Scope:**
  - Passage-level BM25-style full-text search (per B0 P1).
  - Local embeddings (CPU, bundled model files, no network) and optional local reranking.
  - Hybrid fusion (reciprocal rank fusion as the baseline).
  - Filters: court, bench, year, document type, statute, candidate outcome label, publication state.
  - Exact phrase and section-number queries ("s.69", "rule 22") through legal-aware tokenisation.
  - **Withdrawn and unpublished content is excluded transactionally** from every index and from caches.
- **Acceptance:**
  - Retrieval metrics (recall@10/20, nDCG@10) reported on dev and on the held-out golden-set queries.
  - Hybrid is not worse than the best single method on the held-out recall@20; if it is, the ADR records why.
  - p95 latency on reference hardware meets the B0 target.
  - Withdrawal test: a withdrawn document disappears from full-text, vector and suggestion results within the same transaction or job, with no stale cache hits.
  - Results show **why relevant**: matched passage, page and statute (Architecture §10). No "binding" or "current" ranking signal.
- **Author / reviewer:** Opus / independent Opus. The relevance judges are separate from the search author.

### Old B4 → B2 Research depth. Judgment research UI

- **Views:**
  - search results;
  - judgment page (metadata with a status chip per field, original PDF, extracted text, proceedings list, candidate outcome **labelled with V3/V4 measured precision and coverage**, statutes cited, citing and cited cases);
  - Act and section viewer (section-level records and amendment footnotes as candidates; "temporal chain not established" shown where so).
- **Not shown:**
  - holdings and propositions (hidden from Users until D-08's bar is met; an Admin diagnostic view is allowed);
  - scenario guidance;
  - any "current law" assertion.
- **Acceptance:**
  - Usability walkthrough of 10 research tasks by a reviewer agent: find a judgment by party, by section, by phrase; open at a page; trace provenance.
  - Every field shows its verification axis.
  - Accessibility basics (keyboard, contrast).
- **Author / reviewer:** Opus / independent Opus.

### Old B5 → B1 Foundation. Source citation and PDF page navigation

- **Scope:**
  - PDF.js viewer opening the **original bytes** at a page, with the hit highlighted. Native PDFs use text-layer matching. Scans use OCR word boxes, or an OCR'd derivative clearly labelled as derived.
  - A stable citation format for any passage: doc ID, copy sha256 prefix, page, optional paragraph, release ID.
  - "Copy citation" and deep links that survive release updates. A link to a superseded copy resolves to it, with a notice.
- **Acceptance:**
  - On a sample of 100 search hits (native and scanned), the opened page contains the hit text in ≥98% of cases.
  - Highlight is correct in ≥90% for native PDFs. Scanned-page targets are set after P3.
  - PDF.js is configured with script evaluation disabled and kept at the current patched release.
- **Author / reviewer:** Opus / independent Opus.

### Old B6 → B1 Foundation. Provenance and version management

- **Scope:**
  - A provenance panel for every document: source URL, retrieved_at, sha256, HF revision, release generation, ingestion pipeline and OCR versions, aliases, alternate copies, access marking, completeness (truncated or unopenable flags), publication history.
  - Release generations, with diffs between them taken from the change lists.
  - Append-only audit of Admin actions (metadata only).
- **Acceptance:**
  - Any search hit can be traced to bytes on HF at a pinned revision, and the hash check passes.
  - A replaced version keeps both copies.
  - Audit events cannot be edited through the app.
  - Rollback to the previous generation restores identical search results on a fixed query set.
- **Author / reviewer:** Opus / independent Opus.

### Old B7 → B1 Foundation. Admin/User access

- **Scope:**
  - Exactly two roles.
  - Local accounts first, with LDAP/AD as an option behind configuration (D-05).
  - **All corpus mutation and staging endpoints are checked server-side.**
  - WORKING_DOCUMENT_PROCESSING endpoints check session ownership; Admin gets no access to other users' working sessions.
  - Password policy, session expiry, CSRF and lockout.
  - No Legal Reviewer function is built. The designation is a blocking open decision, and the gate fails closed.
- **Acceptance:**
  - API-level negative tests: a User cannot create ingestion jobs, view staging, publish, withdraw, replace or reprocess (UI and direct API).
  - Cross-session isolation tests (Document Studio §11 bullet on User A and User B).
  - Security reviewer: no P1/P2 open.
- **Author / reviewer:** Opus / independent Opus plus security reviewer.

### Old B8 → B2 Research depth. Knowledge-graph exploration

- **Scope:**
  - Navigate statute ↔ judgment ↔ judgment edges from IC-01, with edge type, confidence class, evidence sentence and page link.
  - Neighbourhood view and path between two nodes.
  - Edge-type legend with **per-type measured precision** from A4.
  - Edge types other than `cites` are visibly "proposed, not verified".
  - The UI never states or implies that "no edge" means "no adverse authority".
- **Acceptance:**
  - Graph queries on full candidate data return within the B0 latency target.
  - Every edge opens its evidence passage.
  - Label test: every non-`cites` edge renders the unverified marker.
- **Author / reviewer:** Opus / independent Opus.

### Old B9 → B3. Document Studio foundation (no legal rules)

- **Scope:**
  - Session-isolated working area: upload a PDF, DOCX or scan; view it; OCR it in the session; annotate; export.
  - Working files are excluded from the vault, search, embeddings, graph, template registry and backups (except under the same session ownership and retention).
  - Retention and cleanup.
  - A **read-only view of the forms registry** labelled `DISCOVERED_FROM_SOURCE_NOT_LEGALLY_APPROVED`.
  - **Explicitly excluded:** form generation from templates, field validation, compliance or readiness checks, any rule engine and LLM drafting.
- **Acceptance:**
  - Isolation tests (no leakage to shared search or other sessions; temporary derivatives cleaned up; no working text in logs).
  - Prompt-injection text in an uploaded working file has no effect. There is no model in the loop this cycle, but the parser path is tested.
- **Author / reviewer:** Opus / independent Opus plus security reviewer.

### Old B10 → B1 Foundation. Offline deployment and snapshot update

- **Online side:** a GitHub-committed `build_release` tool with `--check` turns a pinned HF revision plus Track A IC-01 artefacts into a release bundle containing:
  - `data/`;
  - `manifest.csv`;
  - the schema version;
  - `SHA256SUMS`;
  - `CHANGES.json` (added, updated, newly superseded, withdrawn, status changed);
  - `RELEASE.json` (HF commit, tools commit, model bundle IDs);
  - a detached signature.

  **[SUPERSEDED 2026-11-25]** ~~Container images~~ The offline Windows installer and model files ship as separate checksummed and signed bundles.
- **Offline side:**
  1. The importer verifies the signature and every checksum before changing anything. Any failure rejects the whole bundle.
  2. It loads the bundle into a new release generation and builds the indexes.
  3. It runs smoke queries, then switches atomically.
  4. The previous generation is retained for rollback.
  5. Local Admin uploads are reconciled under Architecture §9.1 (sha256 identity, aliases, no auto-merge, precedence, change list as impact trigger).
- **Acceptance:**
  - Install from bundles on a clean air-gapped VM with networking disabled.
  - A tampered byte or signature rejects the import with nothing changed.
  - Update N→N+1 and rollback both work.
  - A bundle containing an already-uploaded local file produces one SourceCopy with two provenances.
  - Backup and restore of DB plus vault is tested.
- **Author / reviewer:** Opus / independent Opus plus security reviewer.

### Old B11 → B1 Foundation. "Candidate data" banner everywhere (cross-cutting)

- **Scope:**
  - A persistent, non-dismissable banner on every page.
  - It is driven by release metadata, not hard-coded. It states that content is research and candidate data, not legally verified, and that AUTH-LEDGER is v0.
  - Per-field status chips.
  - Watermark on prints and exports.
  - API responses carry axis-qualified state fields.
- **Acceptance:**
  - An automated test renders every route and asserts the banner is present.
  - An API contract test checks that the state fields are present.
  - The export watermark test passes.
  - Turning the banner off requires a release flag that cannot be set while AUTH-LEDGER is at v0 and no approvals exist.
- **Author / reviewer:** Opus / independent Opus.

### Old B12 → B1 Foundation (baseline) and B3 (hardening). Security baseline and network-denied testing

- **Scope:** the minimum controls at launch (Architecture §11; Ingestion §6):
  - offline boundary;
  - TLS on the LAN with an internal CA;
  - file safety;
  - parser isolation;
  - integrity hashes;
  - backups;
  - metadata-only audit;
  - dependency SBOM and vulnerability scan done online before transfer;
  - a CI job that runs the full test suite with networking disabled.
- **Acceptance:**
  - Security review with no P1/P2 open.
  - The network-denied suite passes.
  - The SBOM ships with the release.
- **Author / reviewer:** Opus / separate Opus security reviewer.

### Minimal first deliverable (Track B milestone M-B1)

The foundation MVP is installable from bundles on an air-gapped reference **Windows host** (**[revised 2026-11-25]**; was "VM"). It is the B1 Foundation milestone. It includes:

1. offline import of a **pinned HF revision** (full corpus) with checksum and signature verification;
2. hybrid search over judgments and Acts with page-anchored results;
3. the original PDF opened at the hit page;
4. a provenance panel;
5. the candidate banner;
6. local Admin/User login with server-side mutation checks;
7. **one Admin upload → OCR → staging → publish → searchable → withdraw** round trip;
8. backup and restore.

Graph exploration (B8) and Document Studio (B9) are the second increment (M-B2).

## 6. Interface contract IC-01 (Track A → Track B) **[SUPERSEDED 2026-11-25 by `app/contract` v1]**

The outline below is retained for history. The binding definition is the versioned data contract in [`app/contract/`](../../app/contract/README.md): JSON Schemas, validator and tests, including the restricted-material rule keyed on `config/restricted_material.json`.

| Element | Rule |
| --- | --- |
| Format | JSONL with a JSON Schema per entity (judgment, proceeding, outcome_candidate, provision_version, edge, form_registry_row), versioned semver; sha256 per file |
| Required fields | `source_copy_sha256`, page anchor, `extractor_version`, `verification_axes` (axis-qualified states), `evaluation_ref` (link to the measured precision report, if any) |
| Pinning | A Track B release names the exact git commit of each artefact and the HF revision of the corpus |
| Semantics | Track B shows these only as candidates. Missing data is shown as missing, never inferred |
| Change control | A breaking schema change needs a new major version and a Track B contract-test update, reviewed by someone who is neither author |

## 7. Gates summary

| Gate | Condition | Decider |
| --- | --- | --- |
| G0 | Owner confirms this plan and decisions D-01 to D-05 (others may follow) | Owner |
| GA0 | Evaluation infra accepted | Independent reviewer |
| GA1 | Protocol, guideline and matcher pre-registered (A1, A2) | Independent reviewer (★ Fable optional) |
| GA2 | Holdout or reference frozen; agreement reported | Independent reviewer |
| GA3 | Extractor frozen (hash committed) before scoring | Coordinator records; reviewer verifies |
| GA4 | Evaluation independently reviewed; no P1/P2 open | Independent reviewer |
| GA5 | Legal decision recorded before any legal state is applied | Human legal adviser + owner approval to apply |
| GB1 | ADR-0005 stack accepted | Owner (after independent review) |
| GB2 | M-B1 MVP passes acceptance on an air-gapped VM | Independent reviewer + security reviewer |
| GB3 | Security baseline: no P1/P2 open | Security reviewer |
| GX | Release bundle R13-candidate imported offline; banner and state tests pass | Independent reviewer |
| GC | Cycle report, task register, findings register regenerated (`--check`), owner review | Owner |
| **Reasoning-feature gate (stays closed)** | Requires all of: Legal Reviewer designation confirmed and an appointment recorded; an approval tier table; T1/T2 approvals for the scope; extractor targets met on a fresh holdout; scenario benchmark independently reviewed | Owner + competent authority. **Not expected to open in Cycle 13** |

## 8. Sequencing (relative, no calendar commitment)

| Phase | Track A | Track B |
| --- | --- | --- |
| 1 | A0. A6 (ingest the 25 T1; prepare targets). A7 packages 1–2 assembled | B0 PoCs and ADR-0005 draft. B12 CI skeleton |
| 2 | A1 and A2 protocols pre-registered; holdout and reference sampling; coding. A3 provision-version build. A4 identity work | GB1 → B1, B2, B10 (import path), B11 |
| 3 | A1 and A2 development on dev data; A5 transcription; A4 edges and evaluation | B3, B5, B6, B7; M-B1 MVP |
| 4 | Freezes and scoring (GA3, GA4); A8 closures; adviser decisions applied if any (GA5) | B4, B8, B9; IC-01 import; GX release bundle |
| 5 | Cycle report | Cycle report; M-B2 |

## 9. Roles and model allocation

| Role | Who |
| --- | --- |
| Coordinator / lead | Opus (records gates, keeps the task register) |
| Execution agents | Opus, one per workstream |
| Coders, annotators, adjudicators | Separate Opus instances, blind to extractor output and strata. **Preferably one human legal annotator** for A1 (20% subsample) and A2 (D-07) |
| Independent reviewers | Separate Opus instances; a distinct security reviewer for Track B |
| Fable | ★ at most 2–3 reviews: candidates are ADR-0005 and the A1/A2 protocols |
| Legal adviser | Human; answers A7 packages; nothing legal changes without them |
| Owner | Decisions §11; approves applying overlays, ADR-0005 and merges into staging |

## 10. Risk register

| # | Risk | Likelihood / impact | Mitigation |
| --- | --- | --- | --- |
| R1 | All truth labels are AI-made, so measured quality may not reflect legal reality | High / high | D-07 human subsample. Report AI–human agreement. Keep the "no human checked" limitation on every figure |
| R2 | No legal adviser available, so the statutory, forms and treatment layers cannot advance | Medium / high | Plan delivers measurements and app regardless. Packages kept ready. Nothing applied without a decision |
| R3 | Scope creep into advice ("just add a checklist") | Medium / high | §1 boundary; the reasoning gate is closed; the B9 exclusion list; reviewer checks the release for any legal-rule logic |
| R4 | Holdout contamination or tuning on test data | Medium / high | A0 exclusion manifests; pre-registration; freeze hashes |
| R5 | Copyleft licences (PyMuPDF AGPL; Ghostscript AGPL if OCRmyPDF PDF/A is used) | Medium / medium | B0 P7 licence inventory; D-02. Permissive alternatives (pypdfium2, pdfminer.six) identified in the assessment |
| R6 | Windows-native production path unproven for the chosen stack **[revised 2026-11-25]** | High / medium | P1, P5, P8 on a Windows host; no Windows host is available to the agents (assessment Q-6) |
| R7 | Withdrawn content leaks through a secondary index, embeddings or cache | Medium / high | Prefer transactional, in-database indexes (assessment). B3 withdrawal test |
| R8 | OCR quality degrades search on scanned judgments | High / medium | Confidence flags; P4 engine comparison; UI states OCR limits |
| R9 | Unannounced edits to the shared worktree and files across parallel agents | Medium / medium | Separate branches per workstream (`claude/c13-a*`, `claude/c13-b*`); Track B code in its own tree (`app/`, or a separate repo per D-06); PRs into staging only |
| R10 | Supply chain (npm/pip/container images) in an air-gapped build | Medium / medium | Lockfiles with hashes; SBOM; vulnerability scan online; vendored offline build; minimal dependencies |
| R11 | HF/git divergence (277 HF-only, 42 git-only paths) confuses the import | Medium / low | Import manifest from HF at a pinned revision is canonical; the divergence report is shipped in the release |
| R12 | Allow-list and TLS blockers persist | High / medium | D-04; manual acquisition by the owner; blockers stay recorded |
| R13 | Displaying V3/V4 outcome candidates misleads Users | Medium / high | Label with measured precision and coverage; never in summaries; owner may hide them (D-08) |

## 11. Owner decisions

| ID | Decision | Needed by | Recommendation |
| --- | --- | --- | --- |
| **D-01** | **Deployment target** **[SUPERSEDED 2026-11-25 by the directive: Windows-native; 16 cores / 64 GB / 1 TB SSD provisional; GPU optional]**. Remaining: Windows Server edition, volume layout, number of LAN users, IIS vs Windows Service policy | B0 P1/P6, GB1 | Confirm edition and user count; provide a Windows host for P1/P5/P6/P8 evidence |
| **D-02** | **Accept the stack and licence posture** (ADR-0005), including whether AGPL components (PyMuPDF) are acceptable server-side for an internal deployment or must be replaced | GB1 | Accept PostgreSQL-centred stack. Decide AGPL after P7; a permissive fallback exists |
| **D-03** | **Human legal capacity**: name a legal adviser for A7, and confirm the Legal Reviewer designation path (Document Studio §3.3) | A3, A5, A7 decisions | Name an adviser now, even part-time. The designation can follow |
| **D-04** | **Acquisition access**: allow-list `sci.gov.in`, `desw.gov.in` and archive.org storage nodes; fix the egazette trust store; or the owner acquires manually. Confirm the contact-email header policy | A3, A5, A6 | Allow-list plus manual fallback for CAPTCHA-protected items |
| **D-05** | **Authentication mode** (local accounts vs LDAP/AD) and **release-signing key custody** (who holds the offline signing key) | B7, B10 | Local accounts first with an optional LDAP adaptor. Owner-held offline signing key with a backup custodian |
| D-06 | App code location: `app/` in this repository or a separate private GitHub repository | B1 | Separate repository, to keep corpus-tool CI and app CI independent |
| D-07 | Human annotator for the A1 20% subsample and as one of the two A2 annotators | GA2 | Yes. It is the only way to measure AI–human agreement |
| D-08 | Display bar for candidate holdings and outcomes in the User UI | B4 | Holdings hidden until ≥80% P / ≥60% R; outcomes shown labelled with measured figures |
| D-09 | Apply the SC case-number overlay (99 staged) | A4 | Apply as an overlay after independent reconfirmation |
| D-10 | Prism OCR: is it available as an offline module with known licence? | B0 P4 | If not confirmed early in Phase 1, proceed with Tesseract |
| D-11 | Carried from C12: release of temporary working copies; handling of the FOUO RAF 2000 copy in the HF dataset; merge of the C12 PR into staging | — | FOUO copy must be excluded from every app release bundle (B10 eligibility filter) whatever is decided |

## 12. Cycle 13 exit criteria

1. **Track A:**
   - V4 and Holdings V2 measured on fresh, pre-registered holdouts, with weighted estimates and agreement statistics;
   - targets met or shortfalls reported honestly;
   - the five deferred P2s closed and confirmed, or re-deferred with measured reasons;
   - adviser packages delivered;
   - no legal state changed without a recorded human decision.
2. **Track B:**
   - ADR-0005 accepted;
   - M-B1 MVP passes on a clean, network-disabled Windows host **[revised 2026-11-25]**;
   - the release bundle R13-candidate imports and rolls back;
   - banner and state tests green;
   - security baseline with no P1/P2 open;
   - no legal-rule logic anywhere in the app.
3. **Records:** cycle report, task register and regenerated findings register (`--check`), all on the C13 branch and PR into staging. No merge to `main`.
