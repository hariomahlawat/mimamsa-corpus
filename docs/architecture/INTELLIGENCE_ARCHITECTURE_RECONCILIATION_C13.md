# Reconciliation: future intelligence architecture (PR #53) with the Cycle 13 application foundation

- **Recorded:** 2026-11-25, workstream B0, branch `claude/c13-b-app`. **Status:** PROPOSED, for independent review.
- **Inputs:**
  - PR #53 (draft), branch `docs/mimamsa-intelligence-architecture-2026-11-25` at `6a0ae735e4ea0b5e616a25db3019bd212d6604b1`, 11 documents under `docs/architecture/intelligence/`. The owner reports ACCEPT WITH CONDITIONS after three Codex reviews: 25 of 26 findings closed; R2-N01 open.
  - Compared against this branch: ADR-0005 (PROPOSED), the data contract v1 (`app/contract`), `SECURITY_AND_DEPLOYMENT_ARCHITECTURE.md` and the capability matrix.
  - PR #53 pinned this branch at `9eeb04a4`, data contract R1. This reconciliation produces contract **R2** (additive) and must be re-pinned by PR #53.
- **Owner directives applied:**
  1. The foundation must take the intelligence capabilities later without fundamental redevelopment; no agentic AI is implemented now.
  2. Windows-first, not Windows-only: a portable core with replaceable OS adapters; no Linux production support claimed in Cycle 13.
  3. No unnecessary abstraction; functionality, accuracy and UX come first.
- **R2-N01** (transport credit and large-PDF range proof) belongs to the PoC agent under P4/P5. It is referenced here, not addressed.
- **Revision 2 (2026-11-25)** follows the independent review `REVIEW_PR53_RECONCILIATION.md` (ACCEPT WITH CONDITIONS; F01–F04 P2, F05–F10 P3), copied to `reviews/`. The disposition is in §6.

## 1. Classification summary

| Class | Count | Meaning |
| --- | --- | --- |
| COMPATIBLE_ALREADY | 16 | Fully satisfied today by the contract, the architecture or the matrix; no deferred remainder |
| PARTIAL (hook present, remainder deferred) | 11 | The hook or part exists now; the remainder is named, with its owning milestone, in the row |
| INCORPORATE_NOW | 13 | Small and in scope; done in this change set (contract, policy or architecture), with tests where testable. Documentation-only incorporations are marked as such |
| DEFER_TO_LATER_MILESTONE | 15 | Belongs to B1/B2/B3 implementation or to a later gated intelligence milestone; rows marked **B1 design input** bear on B1 now |
| CONFLICT / REDEVELOPMENT_RISK | 6 | Material tension, recorded in §3 and not resolved silently. These rows are X1–X4, X6 and X7 |
| **Total** | **61** | 52 original rows plus R53–R61 added after the reconciliation review (F04) |
| Risks listed in §3 | 7 | 6 classified CONFLICT plus X5, which is classified DEFER (R40) because the gate is closed |

## 2. Requirement-by-requirement mapping

Abbreviations:
- **S** = Serving and revocation contract; **FC** = Final claim verification; **CW** = Data contract crosswalk; **RT** = Local AI security and runtime; **ENG** = Deterministic legal engine; **AG** = Agentic architecture; **TC** = Agent tool contracts; **RG** = Retrieval and GraphRAG; **EV** = Evaluation and roadmap.
- **Ours:** **C** = data contract v1; **SEC** = security and deployment architecture; **ADR** = ADR-0005; **CTM** = capability matrix; **UX** = `app/design`.

| # | PR #53 requirement (source) | Where it lands here | Class | Reason / action |
| --- | --- | --- | --- | --- |
| R01 | Canonical interchange is data contract R1; agent contracts are service projections, not competing schemas (TC §1, CW header) | C | COMPATIBLE_ALREADY | Contract v1 remains the only interchange schema. R2 adds optional fields only |
| R02 | Copy ≠ document ≠ judgment; no destructive dedup (CW §1) | C `source_copy`, `alternate_copy_sha256` | COMPATIBLE_ALREADY | Structural in schema and rules |
| R03 | Seven axes are document-only; never copied to edges or derivatives; no single verified flag (CW §1, TC §3) | C status_axes; candidate has no axes | COMPATIBLE_ALREADY | Closed axes; schema rejects a `verified` flag |
| R04 | Upstream publication ≠ site visibility; site activation publishes (CW §1–2) | C `publication_record` channels; SEC §8.2 | COMPATIBLE_ALREADY | Site-only channels are rejected in bundles |
| R05 | PageKey (copy hash + 1-based page) always resolvable (CW §2) | C `page_anchor` | COMPATIBLE_ALREADY | Page is required in every anchor |
| R06 | SpanKey only with complete derivative binding (pipeline name/version + derivative text hash); never resolve to a newer derivative (CW §2) | C `page_anchor.pipeline_name`, `derivative_text_sha256`; `evidence.py`; rules `SPAN_UNBOUND`, `DANGLING_SPAN_BINDING` | INCORPORATE_NOW | R1 lacked pipeline name and derivative hash. Added as optional fields with a page-only fallback. Tests: `test_evidence_and_reserved.py` |
| R07 | OCR forces derivative-wide `quoting_permitted=false`; OCR excerpts labelled derived (CW §7) | C rule `OCR_QUOTING`; UX 03 | COMPATIBLE_ALREADY | Already enforced and labelled |
| R08 | Raised axis values need exact, independent review binding; AI never confirms identity; technical reviews never set legal axes (CW §7) | C F02 rules | COMPATIBLE_ALREADY | Closed in the B0 review cycle (structural independence, commit binding) |
| R09 | Exclusion rows must have actionable identity; null-only rows are rejected and escalated (CW §7) | C `exclusion_update` schema and `accept_exclusion_update` | INCORPORATE_NOW | **A defect PR #53 found in R1:** `anyOf` accepted keys present with null values. Fixed. Tests: `test_null_only_withdrawal_row_rejected` (3 cases) |
| R10 | Approval and appointment prohibited at v0; scope free text, no typed grant inferred (CW §1, §4; ENG §7) | C rules `LEDGER_V0_*` | COMPATIBLE_ALREADY | v0 fail-closed stays as is. Typed binding is deferred (R40) and a known risk (X5) |
| R11 | Working sessions and agent state never in a bundle (CW §1) | C `WORKING_DOCUMENT_IN_BUNDLE` | COMPATIBLE_ALREADY | Already enforced for sessions |
| R12 | Agent private-write isolation (TC §7, AG §8) | C `RESERVED_NAMESPACE` (`agent/`, `private/`, `workflows/`, `claims/`, `policy/`) and `RESERVED_RECORD_KIND`; SEC §2.1 reserved folders | INCORPORATE_NOW | Reserved namespace only; no agent store is built. Tests: 11 parametrised cases |
| R13 | Candidate vs verified separation consumable by engine and GraphRAG (ENG §1, RG §4) | C candidate status, capability restriction, resolvable review/approval records | COMPATIBLE_ALREADY | No reinterpretation needed. ADR §4b records the hook |
| R14 | Withdrawal fence: durable acceptance; no affected hand-off after it (S §1–3) | SEC §7.4 single delivery gateway; §8.4 | INCORPORATE_NOW | Architecture rule added: one gateway, no static/sendfile/proxy serving of protected bytes. Implementation and proof come in B1/B2 (R27) |
| R15 | Protected PDF delivery as bounded authenticated ranges; no unbounded first GET (S §6, §10) | UX policy `pdfjs`; SEC §7.4 | INCORPORATE_NOW | Policy updated (custom range transport, `disableStream`/`disableAutoFetch`, ≤ 64 KiB) and tested. **Proof is R2-N01 (PoC agent, P4)** |
| R16 | No intermediary cache; no 304/ETag disclosure; protected compression disabled (S §6) | UX policy `protected_responses`; SEC §7.2a | INCORPORATE_NOW | Policy fields and tests added (`test_protected_responses_not_conditional_compressed_or_static`) |
| R17 | Progress by bounded polling; SSE/SignalR protected events disabled until proven (S §6, RT §9) | Assessment §0; SEC §7.4; UX policy | INCORPORATE_NOW | SignalR narrowed to content-free status. See X2 |
| R18 | Crash-safe exclusion acceptance: staged pair, single acceptance record, CAS, pending vs accepted, halt on missing pair, resume, lost-ack idempotency (S §4, §8 P3) | C `ExclusionStore` | INCORPORATE_NOW | Reference protocol. Covers: staging; write-once pair; single-writer LOCK; `ACCEPTED` CAS recording operation id, digest, signature digest, epoch and history; `pending()`; `complete_pending`; resume by identical bytes; staging residue quarantined; lost-ack retry returning the original acknowledgement; typed I/O errors. Tests reproduce the reviewer probes (a) and (b). Power-loss durability on Windows storage is R28 (P8/B2) |
| R19 | Exclusion state outside rollbackable release DB; restore cannot lower it (S §4, §8) | C `ExclusionStore`, `state_for_restore`; SEC §8.3 | COMPATIBLE_ALREADY | Done in confirmation fix C06 |
| R20 | Independent witness custody of current state (S §8) | SEC §8.4 | DEFER_TO_LATER_MILESTONE | Owner decision on custody; proof in P8/B2. See X4 |
| R21 | Effective state precedence: denial dominates; no re-admission by omission; explicit signed re-admission (S §7) | C `ExclusionStore.effective_state`, `exclusion_update.readmissions`; SEC §8.4 | PARTIAL (hook present, remainder deferred) | **Signed channel fixed now:** accepted withdrawals and register entries are monotone tombstones, and only an explicit signed `readmissions` row with `authority_ref` lifts one (tests: omission does not readmit; explicit readmission; readmission needs authority). **Remainder is conflict X7:** local Admin withdrawals still sit in the rollbackable DB. Owner: B2 storage design plus owner decision |
| R22 | Dependency closure for caches, saved results, exports, and query/count/coverage dependencies (S §2, §7; TC §7) | SEC §8.2 step 7 (dependency index: source → candidates/edges/templates) | PARTIAL (hook present, remainder deferred) | Source-level dependency index only. Per-artefact manifests for caches, saved results and exports, and query/count/coverage invalidation, belong to B2 (publication/withdrawal) and B3 (saved research) |
| R23 | Non-disclosure: hidden/not-found/restricted/withdrawn indistinguishable to unauthorised callers (TC §7) | SEC §7.3 | INCORPORATE_NOW | Row added to the authorisation model |
| R24 | Execution domains PUBLISHED_RESEARCH / STAGED_ADMIN_PROCESSING / PRIVATE_WORKING_SESSION (TC §7) | SEC §2.1 | INCORPORATE_NOW | Mapped to the existing layers; not roles |
| R25 | Typed read services callable without an LLM; broker never uses SQL/filesystem (AG §6, TC §6) | ADR §4 modules, §4b | COMPATIBLE_ALREADY | B1/B3 services are ordinary APIs. Recorded in ADR §4b |
| R26 | Typed error vocabulary (ACCESS_DENIED, GATE_CLOSED, WITHDRAWN, …) (TC §5) | B1 API design | DEFER_TO_LATER_MILESTONE | No API exists in B0. Adopt the vocabulary when the B1 API is specified |
| R27 | Gateway implementation with credit ledger, partial accept, WOULD_BLOCK (S §6, §10) | ADR AD-6 | DEFER_TO_LATER_MILESTONE | B1 implementation; R2-N01 proof under P4/P5 (PoC agent) |
| R28 | Durable storage proof on actual Windows storage (S §4, §8) | ADR AD-7 | DEFER_TO_LATER_MILESTONE | P8/B2 |
| R29 | REV-01..08 fault-injection oracle (S §5, §9) | SEC §9 T-VIS-02/03 | DEFER_TO_LATER_MILESTONE | Map REV tests into B1/B2 acceptance when the gateway exists |
| R30 | Windows-first portable core with replaceable adapters (README R3.1, RT §10) | ADR C-8, §4a (interfaces AD-1..AD-4, AD-6..AD-9; deployment controls DC-1, DC-2); assessment §0 | INCORPORATE_NOW | Principle and adapter boundary list added (AD-9 runtimes are PoC candidates, not selections). No Linux delivery claimed |
| R31 | Contract paths relative, platform-neutral, case-fold collisions rejected, no drive letters (RT §10) | C `paths.py` | COMPATIBLE_ALREADY | Already enforced on every OS |
| R32 | Lightweight Linux CI for portable core; Windows CI where toolchain exists (RT §10, EV §8) | `.github/workflows/app-ci.yml` (Linux) | DEFER_TO_LATER_MILESTONE | Linux CI runs today. A Windows runner is deferred to B1/P6: the path-hazard tests deliberately create device-name files, which are unsafe on a Windows runner without rework. Recorded rather than added unverified |
| R33 | No Docker/WSL/VM to support AI; native Windows inference later (RT §1) | ADR C-1; assessment §9 | COMPATIBLE_ALREADY | Same constraint |
| R34 | Model lifecycle: signed manifests, trust purpose, staged loader, monotone revocation (RT §7) | C `pinned.model_bundles` (model_id, sha256, licence); assessment §8 (hash check at start) | PARTIAL (hook present, remainder deferred) | Hash pinning only. Signed model manifest, a `model` trust purpose, staged loader and revocation state belong to the later model milestone (P7 for embedding models) |
| R35 | Resource admission: non-AI SLO protected under inference load (RT §8) | Assessment §5 (Job Objects, separate worker services) | PARTIAL (hook present, remainder deferred) | Worker separation and limits exist. Admission queues and the mixed-load benchmark belong to P5 (jobs) and the later inference pilot |
| R36 | Prompt-injection: document text is data (RT §3) | SEC §6, T-INJ-01 | COMPATIBLE_ALREADY | Already in the threat list |
| R37 | Context/cache partitioning by owner and domain; no shared private caches (RT §6) | SEC §7.2a, client policy | PARTIAL (hook present, remainder deferred) | Client storage forbidden; per-user state server-side. Model/KV/prefix cache partitioning comes with the later inference milestone |
| R38 | Final claim inventory, verification, frozen semantic tree, trusted issuer (FC §1–7) | CTM CAP-CA-03 dependency note | DEFER_TO_LATER_MILESTONE | Generated content is out of scope in Cycle 13. Citations already carry an unverified marker (C08) |
| R39 | Source-only fallback presentation (FC §7) | UX 03 (sources, page links, labels) | COMPATIBLE_ALREADY | Current UX is source-only by design |
| R40 | Typed executable approval binding (tuple/predicate scope, pack digest) (ENG §7, §10) | C `approval_record` | DEFER_TO_LATER_MILESTONE | Needs a later contract version with competent-authority agreement. See X5 |
| R41 | Deterministic evaluator, three-valued logic, procedural state machine (ENG §2–3, §8) | CTM CAP-CA-05, DS-03/04 | DEFER_TO_LATER_MILESTONE | Gated off; no rule logic in Cycle 13 |
| R42 | Shared impact service: append-only impact records, direct and scope-overlap triggers (ENG §9) | SEC §8.2 step 7; Document Studio §8.1 | PARTIAL (hook present, remainder deferred) | Triggers come from `CHANGES.json` and the exclusion channel. The append-only impact record and scope-overlap check belong to B2 (publication) and the later engine milestone |
| R43 | Agent durable execution: leases, fencing tokens, CAS completion, budget reservations (AG §7–8) | ADR AD-4, P5 job table | DEFER_TO_LATER_MILESTONE | The PostgreSQL job table in P5 can carry the lease/fence fields later; no agent built now |
| R44 | Local inference runtime selection and benchmarking (RT §1, §8) | Assessment §9 | DEFER_TO_LATER_MILESTONE | Later gated milestone |
| R45 | Claim-specific coverage and contrary-authority search; absence ≠ no adverse authority (RG §7) | UX `AbsenceNotice`; CTM KG-05 | PARTIAL (hook present, remainder deferred) | The absence notice is mandatory now. Coverage records and an independent contrary-search budget belong to the later GraphRAG milestone |
| R46 | Structured identifier fields, alias history, OCR variants (RG §7, INT-F13) | UX 03 field search; P2 identifier queries | PARTIAL (hook present, remainder deferred) | Field search and identifier queries are specified. Versioned alias history and OCR-variant/trigram recovery belong to P2 tuning and B1 search |
| R47 | Graph traversal only over allow-listed eligible edges; path strength ≤ weakest segment (CW §3) | CTM KG-01..05 | DEFER_TO_LATER_MILESTONE | Browsing in B3 already labels edges. Path-strength scoring comes with GraphRAG |
| R48 | A4/A5 producer → R1 adapter with lossless lineage (CW §6, §8) | §4 below | CONFLICT / REDEVELOPMENT_RISK | Lossy points identified (X6). The adapter is a B3/A-handoff task |
| R49 | Protected delivery topology T0 (app owns egress, no proxy) vs IIS/ARR T1 (S §6) | ADR §3.2, K10 | CONFLICT / REDEVELOPMENT_RISK | X1 |
| R50 | Polling default vs SignalR proposal (S §6) | Assessment §11 | CONFLICT / REDEVELOPMENT_RISK | X2 (narrowed now) |
| R51 | PDF.js stock URL loading vs authenticated range transport (S §10) | UX policy, CAP-US-06 | CONFLICT / REDEVELOPMENT_RISK | X3 (policy changed; proof pending R2-N01) |
| R52 | Durable witness with independent custody vs a file store on the same host (S §8) | C `ExclusionStore`; SEC §8.4 | CONFLICT / REDEVELOPMENT_RISK | X4 |
| R53 | Authenticated local service-to-service calls ("loopback is not authentication"); inference worker without DB, vault or network access (RT §2) | SEC §3 (per-service identities, DB roles); ADR AD-4 | DEFER_TO_LATER_MILESTONE | **B1 design input:** web↔worker traffic goes through the DB job table under distinct DB roles, not unauthenticated loopback HTTP. Any internal HTTP endpoint needs mutual authentication. The inference worker rule applies at the later model milestone |
| R54 | Content-free logs; session deletion removes derivatives, vectors, caches and exports (RT §4, TC §5) | SEC §10; CTM CAP-DS-05 | PARTIAL (hook present, remainder deferred) | Content-free logging is specified. Session deletion of files and rows is in DS-05 (B3); private vectors and model caches do not exist yet (later milestone) |
| R55 | Kill switch for generative features (RT §5) | SEC §7.3 gate (features cannot be enabled at v0) | DEFER_TO_LATER_MILESTONE | Today the gate is stronger than a kill switch: nothing generative can be enabled. An operational kill switch is designed with the later inference milestone |
| R56 | Index generation records embedding model and dimension; no mixed vector spaces; atomic model/index switch (RG §2, RT §7) | Assessment §7 (model id and file hash per passage); release generations | PARTIAL (hook present, remainder deferred) | Model id and hash per embedding, plus generation switching, are planned. Recording the dimension and refusing mixed spaces at query time are B1 implementation items (P2/P3 inform them) |
| R57 | Exact identifier matches cannot be displaced by semantic reranking; rank-based fusion (RG §3) | UX 03 §2–3 | INCORPORATE_NOW | Spec now states: parsed exact identifier matches are pinned above fused results, and fusion is rank-based (RRF). **B1 search design input** |
| R58 | Server-owned workspace state; typed progress events with monotone sequence; reconnect via fresh snapshot (AG §7) | Client policy (server-side per-user state); SEC §7.4 polling | PARTIAL (hook present, remainder deferred) | Server-owned state and polling exist in policy. Typed monotone progress events and snapshot-on-reconnect belong to B1 (job progress) and B3 (workspace) |
| R59 | Operation ID and idempotent acknowledgement for state-changing policy operations (S §8 P3) | C `ExclusionStore.append(operation_id=…)` | INCORPORATE_NOW | The acknowledgement is {operation_id, sequence, digest, epoch}. A retry with the same digest returns the original acknowledgement; the same bytes under another operation id are refused. Test: `test_lost_ack_retry_returns_original_ack`. Admin API idempotency for other mutations is a B2 item |
| R60 | Local Admin withdrawal history in the same durable monotone policy history (S §4 last sentence, §7) | none yet | CONFLICT / REDEVELOPMENT_RISK | X7 |
| R61 | INT-01..INT-20 mapped into B1/B2/P8 acceptance (EV §3, §6, §8) | none yet (REV and CLAIM are referenced in R29/R38) | DEFER_TO_LATER_MILESTONE | Map when the B1/B2 acceptance plans and P8 test plans are written. Owner: B1/B2 acceptance authors with the PoC agent. Not mapped here, to avoid inventing acceptance criteria before the services exist |

Risks in §3: six rows are classified CONFLICT (R48–R52, R60 → X6, X1, X2, X3, X4, X7). X5 (typed approval binding) is classified DEFER (R40) because the gate is closed, but §3 still lists it, so there are seven risks in all.

## 3. Material conflicts and redevelopment risks (recorded, not resolved)

| ID | Conflict | Risk if ignored | Current position | Who resolves |
| --- | --- | --- | --- | --- |
| **X1** | **Hosting topology.** ADR-0005 lists IIS as a front end (and, for Django, IIS URL Rewrite/ARR as reverse proxy). PR #53 makes protected routes acceptable only where one process owns egress (T0), or where proxy buffering is proven inside the gateway's bounds (T1 conditional) | Selecting IIS+ARR for Django could force a re-architecture of PDF and search delivery, or leave protected routes disabled | ADR-0005 adds K10 (protected delivery and portability fit) and states that T1 needs proof. T0 is the preferred candidate for protected routes. Not decided | Owner at GB1 using P1 and P4 evidence |
| **X2** | **Real-time progress.** The assessment proposed SignalR (ASP.NET) or SSE (Django) for job progress; PR #53 disables protected event streams until proven | Content-bearing push could bypass the fence | Narrowed now: polling by default; push only for content-free status | B1 design review |
| **X3** | **PDF delivery.** The original plan opened PDFs with stock PDF.js URL loading; PR #53 requires an authenticated bounded-range transport from the first byte | Unbounded responses defeat withdrawal bounds; reworking the viewer later would be costly | Policy changed (custom range transport, bounded ranges). Feasibility and UX are unproven | **R2-N01, PoC agent (P4/P5)**; the route stays disabled until proven |
| **X4** | **Witness custody.** `ExclusionStore` keeps the acceptance record on the same host (outside the DB and release generations). PR #53 requires an independently recoverable current witness, and states that offline currency cannot be proven if all copies roll back | A full-host restore could reinstate an old exclusion state undetected | Reference protocol (CAS, pending vs accepted, halt on mismatch) now exists. Custody is not chosen | Owner (custody), with P8/B2 proof |
| **X5** | **Typed approval binding.** R1 `approval_record.scope` is free text and has no rule-pack subject or digest; the PR #53 engine needs exact tuple membership and pack digests | A post-v0 engine would need a contract version bump and migration of any approval records | No change now: the gate is closed, and no approval records exist or are allowed at v0 | A later contract version with competent-authority agreement |
| **X7** | **Denial history and local-withdrawal durability** (review F02). (a) Re-admission by omission: re-applying only the latest signed list would re-admit an item dropped from it. (b) Local Admin withdrawals are a DB mutation, and the DB can be rolled back, so a restore taken before a local withdrawal would re-publish the item | (a) A withdrawn item reappears after the next activation, rollback or restore. (b) T-VIS-03 holds only for the signed channel. **Redevelopment risk:** B2 publication/withdrawal storage must keep local withdrawal history outside the rollbackable DB | (a) **Fixed for the signed channel:** monotone tombstones folded over the accepted history; explicit signed `readmissions` with `authority_ref`; tests. (b) **Open:** proposed minimal fix for B2 is that local Admin withdrawals append to the same `ExclusionStore` as a local channel (signed by the site's local publication key, or recorded with Admin identity and operation id), so restore cannot lower them. T-VIS-03 and the contract README are narrowed to the signed channel until then | Owner decision (local channel custody and signing) with B2 design; proof in P8 |
| **X6** | **Producer fidelity (A4/A5 → R1).** See §4: single-valued `capability_restriction` vs A5 lists; A5 review objects cannot bind; A5 `evaluation_ref` is a string; R1 has no ProvisionVersion record | Graph and temporal features would be built on lossy or unmappable data | Adapter rules are documented in PR #53 CW §6. R1 is not widened now (owner directive 3) | B3 / A-track handoff; a contract minor version for ProvisionVersion when A4 is ready |

## 4. Crosswalk check against the actual A4 and A5 outputs (task e)

Producer heads (corrected in revision 2, review F05):
- **A4:** `claude/c13-a4-statutory` is now `c7a93ab6`, merged into staging `ba308db0` (Cycle 13 tranche 1, PR #52). The commits after the PR #53 pin (`01132c34`) change tests and README only; `provision_version.schema.json` and the records are unchanged.
- **A5:** `claude/c13-a5-graph` is now `e92557de`, one commit after the pin (`f915ac11`). It adds the independent A5 review (`reviews/review_c13_a5_f915ac11.md`: ACCEPT WITH CONDITIONS, F01–F04 P2). Schemas and graph data are unchanged.
- So PR #53 still describes the current producer data. The A5 review's F04 (contract mismatch with Track B) agrees with this section and adds two points, recorded in the last two rows of the table.
- PR #53 CW §1–8 pinned app contract R1 at `9eeb04a4`. This change produces R2 (additive).

| Point | PR #53 crosswalk says | Actual producer output | Mismatch / note |
| --- | --- | --- | --- |
| A5 edge types | 28 enum values | `graph_edge.schema.json` `edge_type` enum: 28 values, same names | None |
| A5 node types | INS/PROV/PV/JUD/PROC/QL/PROP/FORM/AUTH/PROCEDURE/REQ/REF | `node_id` prefixes match exactly; `node_type` enum uses long names (INSTRUMENT … UNRESOLVED_REFERENCE, 12 values) | Naming only. An adapter must map long `node_type` names as well as `node_id` prefixes |
| A5 restrictions | HIDDEN_FROM_USERS_THIS_CYCLE → HIDDEN_FROM_USERS; CANDIDATE_DATA / UNVERIFIED_MARKER_REQUIRED kept as display restrictions; "use strongest combination" | Edge `restrictions` is an **array** of up to 4 values. Node restrictions have 3 values (no UNVERIFIED_MARKER_REQUIRED) | **Lossy:** R1 `capability_restriction` is a single value, and R1 has no field for UNVERIFIED_MARKER_REQUIRED or CANDIDATE_DATA. Display impact is nil because R1 labels every candidate, but the raw list survives only in lineage (X6) |
| A5 reviewed edges | REVIEWED_AI_DOCUMENTARY_NOT_LEGAL_VALIDATION maps to DOCUMENTARY_CHECKED only with an exact R1 `reviewed_record` | `edges_reviewed.jsonl`: 173 rows. `reviews[]` items are `{category, review, verdict}` with no reviewer_id, author_id, reviewed_commit, axis or value | **0 of 173 can bind** to an R1 review as produced. All map to AUTOMATED_CANDIDATE_NOT_VERIFIED unless A5 emits R1-shaped review records |
| A5 `evaluation_ref` | Resolve report path and commit independently | A string `path#fragment`; no commit | The adapter must pin the A5 commit (`f915ac11`) to build the R1 object, or set null |
| A5 evidence page | Missing physical page cannot satisfy R1 anchors | `evidence.page` is integer or null; `evidence.source_copy_sha256` is nullable | Confirmed. Null-page or null-copy rows cannot become R1 candidates |
| A5 `legal_effect` | Recompute per R1 enum | Boolean, set by A5's own rule | Confirmed. Recompute; never copy |
| A5 manifest label | IC-01 is historical | `IC01_EXPORT_MANIFEST.json`: `"contract": "IC-01"`, `"contract_version": "1.0.0"` | Label mismatch. R1/R2 supersede IC-01, and A5's "1.0.0" is not contract v1.0.0. A5 should relabel at the handoff |
| A5 verification axes | Raw lineage, not R1 axes | Prefixed six-dimension vocabulary (`byte.`, `identity.`, `extraction.`, `proposition.`, `temporal.`, `approval.NONE`) | Confirmed. Never mapped to R1 axes |
| A4 record | No R1 ProvisionVersion record | `provision_version.schema.json`: the 28 required fields listed in CW §6, `determination_state` const AUTOMATED_CANDIDATE_NOT_VERIFIED, `currency.status` const NOT_ESTABLISHED | Confirmed. R1/R2 known limit. Needs a later contract minor version (X6) |
| A4 evidence page | `pdf_page` is a nullable string, possibly a range | `$defs/evidence.pdf_page` is `["string","null"]`, alongside `printed_page`, `sha256`, `eligible_for_exact_anchor` | Confirmed. Never cast blindly |
| A4 effective date statuses | 9 `effective_from` statuses | Same 9 values | None |
| A5 passage identity (from A5 review F04) | A5 passage/passage_sha256 kept as raw evidence, not R1 passage_id | A5 passage ids look like `PE-…` and carry no character offsets; R1 `passage_id` is `^p\d+-\d+$` with offsets | Confirmed lossy. A5 rows map to page-only anchors (PageKey); no SpanKey without a derivative binding |
| A5 extractor commit (from A5 review F04) | Map to the actual pinned producer artefact commit | A5 edges carry `extractor_version` only; R1 requires `extractor.artefact_commit` | The adapter must supply the A5 commit. A5 F03 binding/subject errors and F02 voice errors also mean treatment edges stay candidates |

## 5. What changed in the first reconciliation commit (`31a21df4`)

**Contract R2** (`app/contract`)
- `page_anchor.pipeline_name` and `page_anchor.derivative_text_sha256`.
- `evidence.py` (PageKey/SpanKey, `resolve_span`).
- Rules `SPAN_UNBOUND`, `DANGLING_SPAN_BINDING`, `RESERVED_NAMESPACE` and `RESERVED_RECORD_KIND`.
- Exclusion rows require a non-null identity.
- `ExclusionStore` acceptance record with CAS and `pending()`.
- Tests: 21 new (contract 202 passed, 1 skipped).

**UX policy:** PDF.js bounded authenticated range transport; protected responses with no ETag/304, no compression and no static/sendfile; polling progress. Tests: 2 new (design 111 passed).

**Architecture**
- ADR-0005: C-8, C-9, K10, §4a adapter boundaries AD-1..AD-10, §4b intelligence hooks.
- Security: §2.1 execution domains and reserved folders; §7.3 non-disclosure; §7.4 single delivery gateway and serving fence; §8.4 acceptance protocol.
- Assessment §0: portability; SignalR narrowed.

**Capability matrix:** PR #53 references on 13 existing capabilities. No new capability IDs.

**Not done (by design):** no agent, model, rule engine, gateway implementation, Windows CI runner or Linux delivery. R2-N01 stays with the PoC agent.

## 6. Revision 2: disposition of the reconciliation review

| Finding | Disposition |
| --- | --- |
| F01 (P2) | **Fixed.** New class PARTIAL. R21, R22, R34, R35, R37, R42, R45 and R46 reclassified, each naming its owning milestone. Counts recomputed (§1) |
| F02 (P2) | **Fixed in part, rest recorded.** X7 added. Signed-channel re-admission by omission is fixed (monotone tombstones, explicit signed `readmissions`, 3 tests). Local Admin withdrawal durability is recorded as a redevelopment risk with a proposed B2 fix and an owner decision. T-VIS-03 and the contract README are narrowed to the signed channel |
| F03 (P2) | **Fixed.** Added: `complete_pending`; resume by identical bytes; refusal of different bytes; staging residue quarantined; lost-ack idempotency with operation id; single-writer LOCK; typed I/O errors; ACCEPTED record now carries signature digest, epoch and history. 8 tests, including reviewer probes (a) and (b), which now pass |
| F04 (P2) | **Fixed.** R53–R61 added: local service authentication (B1 design input), content-free logs/session deletion, kill switch, index model/dimension, exact-identifier protection (spec incorporated), workspace/progress, operation id (incorporated), local withdrawal history (X7), INT-01..20 mapping (deferred to the B1/B2/P8 acceptance authors) |
| F05 (P3) | **Fixed.** Heads corrected; A5 review considered; 2 rows added |
| F06 (P3) | **Fixed.** `resolve_span` checks offsets against passage bounds; test added |
| F07 (P3) | **Fixed.** ADR AD-5 and AD-10 relabelled as deployment controls (no core interface); AD-9 worded as PoC candidates |
| F08 (P3) | **Fixed.** Layer mapping aligned (PUBLISHED_RESEARCH = layers 1–8, published view) in ADR and security; §7.4 moved after §7.3; policy note on original streaming corrected |
| F09 (P3) | **Fixed.** `CONTRACT_REVISION = "R2"` with a test; README states revision is pinned by marker and commit |
| F10 (P3) | **Fixed.** The §1 table shows classified conflicts and total risks separately |

Tests after revision 2: contract 214 passed, 1 skipped (parity, awaiting governance integration); design 111 passed.
