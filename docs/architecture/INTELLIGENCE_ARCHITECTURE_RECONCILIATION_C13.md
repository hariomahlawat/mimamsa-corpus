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

## 1. Classification summary

| Class | Count | Meaning |
| --- | --- | --- |
| COMPATIBLE_ALREADY | 24 | Already satisfied by the contract, the architecture or the matrix; no change needed |
| INCORPORATE_NOW | 11 | Small and in scope; done in this change (contract, policy or architecture), with tests where testable |
| DEFER_TO_LATER_MILESTONE | 12 | Belongs to B1/B2/B3 implementation or to a later gated intelligence milestone; the hooks are kept |
| CONFLICT / REDEVELOPMENT_RISK | 5 | Material tension; recorded in §3 (X1–X4, X6) and not resolved silently. X5 (typed approval binding) is classified DEFER (R40) but also listed in §3 as a risk |
| **Total** | **52** | |

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
| R18 | Crash-safe exclusion acceptance: staged pair, single acceptance record, CAS, pending vs accepted, halt on missing pair (S §4) | C `ExclusionStore` (staging, write-once pair, `ACCEPTED` CAS, `pending()`) | INCORPORATE_NOW | Reference protocol implemented. Tests: unaccepted pair is pending, missing pair halts, stale CAS rejected. Power-loss durability proof is deferred (R28) |
| R19 | Exclusion state outside rollbackable release DB; restore cannot lower it (S §4, §8) | C `ExclusionStore`, `state_for_restore`; SEC §8.3 | COMPATIBLE_ALREADY | Done in confirmation fix C06 |
| R20 | Independent witness custody of current state (S §8) | SEC §8.4 | DEFER_TO_LATER_MILESTONE | Owner decision on custody; proof in P8/B2. See X4 |
| R21 | Effective state precedence: denial dominates; no re-admission by omission (S §7) | SEC §8.4; C `items_to_suppress` | COMPATIBLE_ALREADY | Withdrawn and restricted items are suppressed regardless of channel. Explicit re-admission records come in B2 |
| R22 | Dependency closure for caches, saved results, exports (S §2, TC §7) | SEC §8.2 step 7 (dependency index) | COMPATIBLE_ALREADY | The dependency-record step exists. Per-artefact manifests come in the B2 implementation |
| R23 | Non-disclosure: hidden/not-found/restricted/withdrawn indistinguishable to unauthorised callers (TC §7) | SEC §7.3 | INCORPORATE_NOW | Row added to the authorisation model |
| R24 | Execution domains PUBLISHED_RESEARCH / STAGED_ADMIN_PROCESSING / PRIVATE_WORKING_SESSION (TC §7) | SEC §2.1 | INCORPORATE_NOW | Mapped to the existing layers; not roles |
| R25 | Typed read services callable without an LLM; broker never uses SQL/filesystem (AG §6, TC §6) | ADR §4 modules, §4b | COMPATIBLE_ALREADY | B1/B3 services are ordinary APIs. Recorded in ADR §4b |
| R26 | Typed error vocabulary (ACCESS_DENIED, GATE_CLOSED, WITHDRAWN, …) (TC §5) | B1 API design | DEFER_TO_LATER_MILESTONE | No API exists in B0. Adopt the vocabulary when the B1 API is specified |
| R27 | Gateway implementation with credit ledger, partial accept, WOULD_BLOCK (S §6, §10) | ADR AD-6 | DEFER_TO_LATER_MILESTONE | B1 implementation; R2-N01 proof under P4/P5 (PoC agent) |
| R28 | Durable storage proof on actual Windows storage (S §4, §8) | ADR AD-7 | DEFER_TO_LATER_MILESTONE | P8/B2 |
| R29 | REV-01..08 fault-injection oracle (S §5, §9) | SEC §9 T-VIS-02/03 | DEFER_TO_LATER_MILESTONE | Map REV tests into B1/B2 acceptance when the gateway exists |
| R30 | Windows-first portable core with replaceable adapters (README R3.1, RT §10) | ADR C-8, §4a (AD-1..AD-10); assessment §0 | INCORPORATE_NOW | Principle and adapter boundary list added. No Linux delivery claimed |
| R31 | Contract paths relative, platform-neutral, case-fold collisions rejected, no drive letters (RT §10) | C `paths.py` | COMPATIBLE_ALREADY | Already enforced on every OS |
| R32 | Lightweight Linux CI for portable core; Windows CI where toolchain exists (RT §10, EV §8) | `.github/workflows/app-ci.yml` (Linux) | DEFER_TO_LATER_MILESTONE | Linux CI runs today. A Windows runner is deferred to B1/P6: the path-hazard tests deliberately create device-name files, which are unsafe on a Windows runner without rework. Recorded rather than added unverified |
| R33 | No Docker/WSL/VM to support AI; native Windows inference later (RT §1) | ADR C-1; assessment §9 | COMPATIBLE_ALREADY | Same constraint |
| R34 | Model lifecycle: signed manifests, hashes, staged loader, revocation (RT §7) | Assessment §8 (model hash at start); C `pinned.model_bundles` | COMPATIBLE_ALREADY | Embedding model hashes are already pinned. LLM lifecycle comes later (R44) |
| R35 | Resource admission: non-AI SLO protected under inference load (RT §8) | Assessment §5 (Job Objects, separate worker services) | COMPATIBLE_ALREADY | Separate worker identities and limits. Mixed-load benchmark comes later |
| R36 | Prompt-injection: document text is data (RT §3) | SEC §6, T-INJ-01 | COMPATIBLE_ALREADY | Already in the threat list |
| R37 | Context/cache partitioning by owner and domain; no shared private caches (RT §6) | SEC §7.2a, client policy | COMPATIBLE_ALREADY | No persistent client storage; owner-scoped server state. Model caches come later |
| R38 | Final claim inventory, verification, frozen semantic tree, trusted issuer (FC §1–7) | CTM CAP-CA-03 dependency note | DEFER_TO_LATER_MILESTONE | Generated content is out of scope in Cycle 13. Citations already carry an unverified marker (C08) |
| R39 | Source-only fallback presentation (FC §7) | UX 03 (sources, page links, labels) | COMPATIBLE_ALREADY | Current UX is source-only by design |
| R40 | Typed executable approval binding (tuple/predicate scope, pack digest) (ENG §7, §10) | C `approval_record` | DEFER_TO_LATER_MILESTONE | Needs a later contract version with competent-authority agreement. See X5 |
| R41 | Deterministic evaluator, three-valued logic, procedural state machine (ENG §2–3, §8) | CTM CAP-CA-05, DS-03/04 | DEFER_TO_LATER_MILESTONE | Gated off; no rule logic in Cycle 13 |
| R42 | Shared impact service for dependencies (ENG §9) | SEC §8.2 step 7; Document Studio §8.1 | COMPATIBLE_ALREADY | Impact triggers come from `CHANGES.json` and the exclusion channel |
| R43 | Agent durable execution: leases, fencing tokens, CAS completion, budget reservations (AG §7–8) | ADR AD-4, P5 job table | DEFER_TO_LATER_MILESTONE | The PostgreSQL job table in P5 can carry the lease/fence fields later; no agent built now |
| R44 | Local inference runtime selection and benchmarking (RT §1, §8) | Assessment §9 | DEFER_TO_LATER_MILESTONE | Later gated milestone |
| R45 | Claim-specific coverage and contrary-authority search; absence ≠ no adverse authority (RG §7) | UX `AbsenceNotice`; CTM KG-05 | COMPATIBLE_ALREADY | The absence notice is mandatory. Coverage records come with GraphRAG |
| R46 | Structured identifier fields, alias history, OCR variants (RG §7, INT-F13) | UX 03 field search; P2 identifier queries | COMPATIBLE_ALREADY | Field search and identifier queries are specified; tuning is in P2 |
| R47 | Graph traversal only over allow-listed eligible edges; path strength ≤ weakest segment (CW §3) | CTM KG-01..05 | DEFER_TO_LATER_MILESTONE | Browsing in B3 already labels edges. Path-strength scoring comes with GraphRAG |
| R48 | A4/A5 producer → R1 adapter with lossless lineage (CW §6, §8) | §4 below | CONFLICT / REDEVELOPMENT_RISK | Lossy points identified (X6). The adapter is a B3/A-handoff task |
| R49 | Protected delivery topology T0 (app owns egress, no proxy) vs IIS/ARR T1 (S §6) | ADR §3.2, K10 | CONFLICT / REDEVELOPMENT_RISK | X1 |
| R50 | Polling default vs SignalR proposal (S §6) | Assessment §11 | CONFLICT / REDEVELOPMENT_RISK | X2 (narrowed now) |
| R51 | PDF.js stock URL loading vs authenticated range transport (S §10) | UX policy, CAP-US-06 | CONFLICT / REDEVELOPMENT_RISK | X3 (policy changed; proof pending R2-N01) |
| R52 | Durable witness with independent custody vs a file store on the same host (S §8) | C `ExclusionStore`; SEC §8.4 | CONFLICT / REDEVELOPMENT_RISK | X4 |

The table classifies X5 (typed approval binding) as DEFER (R40), because the gate is closed; §3 still records it as a risk. That makes six conflicts: five classified rows (R48–R52) plus X5.

## 3. Material conflicts and redevelopment risks (recorded, not resolved)

| ID | Conflict | Risk if ignored | Current position | Who resolves |
| --- | --- | --- | --- | --- |
| **X1** | **Hosting topology.** ADR-0005 lists IIS as a front end (and, for Django, IIS URL Rewrite/ARR as reverse proxy). PR #53 makes protected routes acceptable only where one process owns egress (T0), or where proxy buffering is proven inside the gateway's bounds (T1 conditional) | Selecting IIS+ARR for Django could force a re-architecture of PDF and search delivery, or leave protected routes disabled | ADR-0005 adds K10 (protected delivery and portability fit) and states that T1 needs proof. T0 is the preferred candidate for protected routes. Not decided | Owner at GB1 using P1 and P4 evidence |
| **X2** | **Real-time progress.** The assessment proposed SignalR (ASP.NET) or SSE (Django) for job progress; PR #53 disables protected event streams until proven | Content-bearing push could bypass the fence | Narrowed now: polling by default; push only for content-free status | B1 design review |
| **X3** | **PDF delivery.** The original plan opened PDFs with stock PDF.js URL loading; PR #53 requires an authenticated bounded-range transport from the first byte | Unbounded responses defeat withdrawal bounds; reworking the viewer later would be costly | Policy changed (custom range transport, bounded ranges). Feasibility and UX are unproven | **R2-N01, PoC agent (P4/P5)**; the route stays disabled until proven |
| **X4** | **Witness custody.** `ExclusionStore` keeps the acceptance record on the same host (outside the DB and release generations). PR #53 requires an independently recoverable current witness, and states that offline currency cannot be proven if all copies roll back | A full-host restore could reinstate an old exclusion state undetected | Reference protocol (CAS, pending vs accepted, halt on mismatch) now exists. Custody is not chosen | Owner (custody), with P8/B2 proof |
| **X5** | **Typed approval binding.** R1 `approval_record.scope` is free text and has no rule-pack subject or digest; the PR #53 engine needs exact tuple membership and pack digests | A post-v0 engine would need a contract version bump and migration of any approval records | No change now: the gate is closed, and no approval records exist or are allowed at v0 | A later contract version with competent-authority agreement |
| **X6** | **Producer fidelity (A4/A5 → R1).** See §4: single-valued `capability_restriction` vs A5 lists; A5 review objects cannot bind; A5 `evaluation_ref` is a string; R1 has no ProvisionVersion record | Graph and temporal features would be built on lossy or unmappable data | Adapter rules are documented in PR #53 CW §6. R1 is not widened now (owner directive 3) | B3 / A-track handoff; a contract minor version for ProvisionVersion when A4 is ready |

## 4. Crosswalk check against the actual A4 and A5 outputs (task e)

Checked against the current branch heads:
- A4 `claude/c13-a4-statutory` = `01132c34`, and A5 `claude/c13-a5-graph` = `f915ac11`. Both are **identical to the commits PR #53 pinned**, so PR #53 describes the current producer outputs.
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

## 5. What changed in this commit

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
