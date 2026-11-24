# Document Studio and source-backed Form/Template Registry

**Recorded:** 2026-11-24  
**Status:** Owner-confirmed product capability; implementation, source-specific templates and legal checks remain **proposed** pending exact-source review.  
**Related:** [Product vision](../product/PRODUCT_VISION.md), [Commander scenarios](../product/COMMANDER_USE_CASES.md), [Scenario engine](SCENARIO_ADVISORY_ENGINE.md), [ADR-0003](decisions/ADR-0003-DOCUMENT_STUDIO_AND_TEMPLATE_REGISTRY.md).

## 1. Purpose

Mimamsa must help an authorised unit user prepare a correctly sourced military legal/procedural document, review an already prepared document, and check a set of documents for procedural completeness. This includes potential charge-sheets, applicable court-martial forms, notices, statements, records of proceedings, statutory complaint documentation and other forms **only when an applicable authorised template/source and correct scope have been established**. It is a drafting and independent checking aid, not an adjudicator, document-signing authority or final legal certifier.

The Document Studio must **not** invent a format, charge wording, prescribed signature, procedural prerequisite or legal conclusion simply because an LLM recalls similar language. Its shared evidence base is the published, date-aware law graph and the Form/Template Registry.

## 2. Access boundary: distinguish two meanings of “upload”

| Operation | Admin | User | Persistence / visibility |
| --- | --- | --- | --- |
| Search or use a published registered form/template | Yes | Yes | Same published registry |
| Generate a draft from a published template | Yes | Yes | Temporary working session, not corpus |
| Upload existing PDF/DOCX/scan for checking | Yes | Yes | Temporary working session, not corpus |
| Review a multi-document procedural file | Yes | Yes | Temporary working session, not corpus |
| Download editable draft, annotated review or report | Yes | Yes | User output; no implicit source publishing |
| Upload/publish a source manual, SOP or template, or edit its descriptive metadata or template definition (source bytes are immutable) | Yes | No | Admin staging, then shared corpus after explicit publication |
| Withdraw, replace or reprocess shared source/template | Yes | No | Admin-managed, audited |

**Operation classes:** CORPUS_INGESTION is Admin-only and writes to shared-source staging; WORKING_DOCUMENT_PROCESSING is available to both roles and writes only to that user's temporary session. Distinct endpoints, storage namespaces, job types, output retrieval, and publication paths must enforce these semantics server-side. Working-file processing never triggers a corpus ingestion job, even when initiated by Admin.

Working files, prompts, extracted text, findings, generated drafts, local embeddings and AI context must never enter shared-source records, Hugging Face, common search, global graph, shared caches or training data. Only a separate, deliberate eligible Admin source submission can become a shared source. Use simple authenticated session ownership checks for all working inputs, job IDs, file URLs, reports, exports and model-context retrieval; an opaque identifier alone is insufficient. User A (including an Admin acting as another user) has no general Document Studio access to User B's session. Keep sensitive input/output out of ordinary diagnostics, shared logs and reusable caches; use minimal operational metadata instead. The audit log records metadata only (actor, session ID, action, time, hashes, sizes), never working content. Working-session data is excluded from deployment backups by default; if a deployment chooses to back it up, the backup must keep the same session ownership, retention and deletion rules, with deletion propagated to backups. Apply safe parsing, cleanup of derived artefacts and configurable, documented retention. No extra research roles or elaborate case-workspace system are required.

## 3. Inventory and classification: locate the actual forms

Before creating working templates, systematically inspect original, legally accessible and appropriate-edition materials:

- Army Act and Army Rules, including appendices and their amendments;
- the eight user-provided Manual of Military Law files, **only as edition-unverified practical references until authenticated**;
- applicable Defence Service Regulations / Regulations for the Army and relevant source amendments;
- authorised published Army Orders, Army Instructions, government forms and other Admin-admitted service policies/SOPs;
- relevant court judgments for actual procedural interpretation and legally significant defects.

The pilot inventory is **Army-first** (see the scope statement in the [Product vision](../product/PRODUCT_VISION.md#1-purpose)). Air Force and Navy forms are in the target scope but are not yet queued.

The discovery process must find **forms and tables in scanned pages**, not rely on text search alone. Capture form title, number, exact page/paragraph/appendix, provenance, printed wording, images, tables, field layout, mandatory-versus-example language, amendment/commencement state and whether it is currently applicable. Compare source editions, identify collisions and send unverified copies or conflicting versions to a research queue.

**Independent classification axes are compulsory.** These are proposed registry concepts, not changes to existing AUTH-LEDGER or evidence-policy vocabulary.

| Axis | Values / required distinction |
| --- | --- |
| Form authority/type | STATUTORY_PRESCRIBED (explicit requirement); OFFICIAL_SPECIMEN (illustrative); OFFICIAL_SERVICE_ADMINISTRATIVE (order/instruction with established scope); OTHER_OR_UNDETERMINED |
| Discovery / reproduction fidelity | DISCOVERED; TRANSCRIBED; FIDELITY_VERIFIED, with page-image comparison and recorded evidence |
| Applicability | NOT_ESTABLISHED; APPLICABILITY_VERIFIED for a stated scope and date basis; CONFLICTING; HISTORICAL/SUPERSEDED for a particular interval, never a blanket assertion that all earlier uses were invalid |
| Legal approval | RESEARCH_ONLY; LEGAL_REVIEWED; LEGAL_VALIDATED for specified requirements/scope, with attributable competent approval artefact; REVIEW_REQUIRED / BLOCKED |
| Publication | STAGED; PUBLISHED; WITHDRAWN, with Admin action and audience eligibility |
| Dependency/release freshness | CURRENT_FOR_CHECKED_SCOPE; REVALIDATION_REQUIRED; BLOCKED, with reason and version history |

A statutory prescribed form can be historical, faithfully transcribed, published and not currently applicable at the same time. An authenticated official specimen is not necessarily mandatory. A label on one axis cannot promote another. Where the source is unverified or historical, retain its candidate form type and status independently. Never infer authority from the words "form", "Appendix", "Manual", from a hosting domain, or from a file hash.

### 3.1 Discovery and coverage

Maintain the [Form Discovery and Coverage Register](../product/FORM_DISCOVERY_AND_COVERAGE_REGISTER.md). Before claiming coverage, record source identity, exact copy/hash, edition and page ranges, which pages were visually inspected, gaps and inaccessible pages, all forms found (including duplicates and conflicts), and the review disposition. All eight MML originals must receive the mandatory first-pass practical-reference assessment under the controlling evidence standard. No form count or source coverage is established by this design document.

### 3.2 Research versus operational drafting gate

A published candidate can be read and compared even when research-only. Fidelity review establishes reproduction, not legal applicability. Documentary checks establish source evidence, not legal authorisation. Applicability review must establish the relevant date basis, jurisdiction, procedure, conditions, authority, and governing amendment/saving chain. Substantive disputed interpretations are escalated to the designated legal adviser; formal JAG validation is recorded only with an attributable formal approval artefact, as required by EVIDENCE_STANDARD and SOURCE_AUTHORITY_POLICY. Technical checks, source verification, Admin publication and any independent review without that artefact cannot substitute for the required legal approval. The same evidentiary and technical tests apply regardless of authorship.

**Operational-use gate:** release an authoritative template, mandatory constraint, procedural checklist or definitive advisory only for the explicitly approved scope, with source identity/fidelity, applicability and requisite legal approval (the tier required for that output class, section 3.3) independently established, published eligibility and no blocking dependency conflict. Record the approval artefact identifier, reviewer/competence, scope, exact source/template/rule revision, date, limitations and subsequent revocation or supersession. High-consequence unresolved authority blocks candidate operational use. A form is not operationally approved merely because a source passage or template was independently verified. A research-only form may be inspected and, if useful, reproduced as an unmistakably labelled research specimen (not a filled instrument represented as fit for issue); do not activate unsupported mandatory rules. No machine-generated output certifies the validity of an actual proceeding.

### 3.3 Legal approval path on an air-gapped site (proposed; blocking open decision)

This section defines *how* an attributable legal approval could be recorded. **No approval, appointment or approval artefact exists today**, and none is created by this document. Until the owner confirms this path (ADR-0003, blocking open decisions) and a competent authority makes a recorded appointment, the operational-use gate in 3.2 fails closed: every output remains research-only.

**Legal Reviewer designation, not a third research tier.** Admin and User remain the only functional access roles; research access is unchanged. A *Legal Reviewer designation* is a recorded authorisation attached to a named, authenticated account. It permits exactly one additional class of action, recording legal review decisions within its stated scope. It must be backed by an `Appointment` record: appointing competent authority, appointee, capacity (designated legal adviser, or formal JAG approver), scope (output classes, subject areas, instruments), validity period, appointment artefact hash and any revocation. Admin capacity never confers it. Where one person holds both, the system records each action under a single capacity. An Admin publication, metadata correction or staging decision is never a legal approval, and an Admin cannot approve a scope in Admin capacity.

**Approval tiers.** "Requisite legal approval" means the tier required for the output class:

| Tier | Meaning | Recorded by |
| --- | --- | --- |
| `T0_RESEARCH_ONLY` | No legal approval; inspectable, labelled research only | Not applicable |
| `T1_LEGAL_ADVISER_REVIEWED` | Designated legal adviser's attributable decision for the stated scope (SOURCE_AUTHORITY_POLICY, conflict checklist step 6) | Legal Reviewer (legal adviser capacity) |
| `T2_FORMAL_JAG_VALIDATED` | Formal JAG validation, only with its attributable formal approval artefact (EVIDENCE_STANDARD, review gates) | Legal Reviewer (formal JAG capacity), or signed release import |

The competent authority must set the required tier per output class in a recorded *tier-requirement table*. Proposed fail-closed defaults until it does so: authoritative templates offered as fill-ready instruments, `MANDATORY_SOURCE_SUPPORTED` checklist items and mandatory document constraints need T2. Definitive advisory routes, `CONDITIONAL_SOURCE_SUPPORTED` and `ADMINISTRATIVE_OR_LOCAL` items need at least T1. An output class missing from the table is treated as requiring T2. These defaults are design proposals, not legal determinations.

**How an approval artefact reaches a deployment.** There are three channels. Each produces an `Approval` record pinned to the exact source, template or rule revision and scope:
1. **Signed release import:** approval records carried in a verified external release bundle and signed by the approving authority's offline key (see [Architecture 9.1](LEGAL_KNOWLEDGE_ARCHITECTURE.md#91-release-updates-and-local-sources)). An invalid signature or checksum rejects the record.
2. **Local Legal Reviewer decision:** recorded by the authenticated Legal Reviewer account within its appointment scope, optionally with a scanned signed decision attached by hash.
3. **Transcription of an external artefact:** an Admin may *record* an approval made elsewhere only by attaching the artefact (hash-preserved) and attributing it to the external approver, never to the Admin. Recording is not approving. The record stays `APPROVAL_RECORDED_UNCONFIRMED`, and the gate does not count it, until a Legal Reviewer confirms that the artefact identifies the approver, capacity, scope and revision, or until a signed release confirms it.

Each `Approval` stores the artefact ID and hash, approver and capacity, appointment reference, tier, scope, pinned revision, date, limitations and any later revocation or supersession. Approvals never carry forward automatically to a new revision.

**Fail-closed behaviour.** The gate refuses an output when any of these holds: no valid appointment covers the scope; the approval tier is below the required tier; the pinned revision differs from the revision in use; the approval or appointment has been revoked or has expired (historical records remain visible); the record is unconfirmed; or a dependency is `REVALIDATION_REQUIRED`/`BLOCKED`. Refusal yields research-only output with the reason shown.

**Who judges "credible material" (section 8.1).** An impact trigger is *credible* when (a) it comes from a verified release change list, or from a source whose `document_authority` is `ENACTED_OR_NOTIFIED_PRIMARY`, `OFFICIAL_JUDICIAL_DECISION` or a government-issued category with identity at least provisionally established; (b) an anchored passage resolves to a dependency in scope; and (c) its date overlaps the dependency's applicable interval. It is *material* when, on its face, it would change a requirement's existence, content, condition, competent authority, form version or controlling date (for example amendment, omission, repeal, substitution, commencement, overruling or limitation). Triggers meeting (a) to (c) with facial materiality automatically place the affected scope in `REVALIDATION_REQUIRED/BLOCKED`. Triggers from `UNKNOWN`-authority or `USER_SUPPLIED` sources go to the review queue as leads. An Admin or Legal Reviewer may place a *precautionary hold* on a scope, labelled as not a legal finding. **Only a Legal Reviewer** may dismiss a trigger as not credible or not material, lift a hold, or re-enable a blocked scope, and only by recording a new or reaffirmed approval at the required tier for the new revision.

**Review workspace.** The Vision's "Legal review workspace" is the operating surface of this designation: queues, impact triggers, proposed non-`cites` relations and approval recording. Until the designation is confirmed it is **deferred**. Admin may view queues but cannot record decisions in it.

## 4. Canonical registry and rule model (proposed)

A `FormTemplate` records:
- stable template ID, name, purpose, category and document family;
- independent form-type, fidelity, applicability, legal approval, publication and dependency-freshness axes, with supporting evidence;
- source document identity, exact copy SHA-256, page, printed form number, paragraph/appendix and passage/image locator;
- issue/commencement and applicable intervals, version/supersession evidence; controlling date basis per field/constraint, and saved/transitional scope;
- applicability by service status/rank, forum, case type, authority and **procedural stage**, with UNKNOWN supported;
- document layout: fields, tables, repeated sections, labels, instruction text, signature blocks and formatting tolerances;
- `FieldRequirement` records for mandatory/conditional/optional fields with conditions and source evidence;
- `DocumentConstraint` records: syntax, legal elements, cardinality, cross-field/date checks, competent signature, and source-linked rationale;
- `RelatedDocumentRequirement`: prerequisite/conditional/supporting companion documents and whether their existence can be tested from uploaded evidence;
- `TemplateReview`: documentary fidelity review, legal applicability review, explicit decisions, reviewer, date and version;
- version ID, schema/check engine version, publishing history and known adverse conflicts.

**Single rule source:** The generator, pre-export checks, independent document auditor and procedural checklists must use the **same approved versioned constraint definitions**. Do not create two drifting interpretations of a form. Shared-rule agreement is not an independent proof of correctness; see the external-to-the-engine test oracle in section 11.

### 4.1 Legally relevant dates

Store incident/conduct date or interval, commencement/initiation of proceedings, relevant procedural-action date, document preparation/review date, and the effective dates of applicable provisions/forms, distinctly from acquisition/review time. Each legal constraint records which event date(s) control, legal basis for that selection, applicable intervals, and transitional/saving/retrospective qualifications. Substantive offence law and procedural requirements can use different controlling events. Never assume that today, the incident date, or the date typed on a document governs all requirements. Repeal, omission, substitution, re-enactment, commencement and saving relations come from the graph ([Architecture 5](LEGAL_KNOWLEDGE_ARCHITECTURE.md#5-graph-relation-types)); the named temporal acceptance cases in [Architecture 7.1](LEGAL_KNOWLEDGE_ARCHITECTURE.md#71-named-temporal-acceptance-cases) apply to form and constraint selection as well. If dates, controlling-date basis or saving provisions are unresolved, the affected determination remains UNKNOWN/BLOCKED; ask targeted questions or give qualified research only. Preserve historically valid versions for the intervals and conditions actually supported.

## 5. Creating a document

1. User chooses a document or asks a situation question, e.g. “Prepare a charge-sheet for a reported offence.”
2. Resolve **which legal procedure and document type** actually applies, relevant event dates under section 4.1, service status, forum and stage. If essential facts, governing date or authority are unknown, show candidates and ask targeted questions; do not claim a prescribed format.
3. Display the source form, citation, independent status axes and applicable scope. Enforce the operational-use gate in section 3.2; if not met, offer source inspection or a clearly labelled research specimen only, with blocked requirements visible. Do not offer a fill-ready authoritative instrument or imply it is fit for issue.
4. Gather only necessary facts through a structured form. Distinguish alleged facts, verified facts and assertions provided by the user; never fabricate an incident record or a completed procedural act.
5. Render the source layout faithfully through deterministic document assembly. LLM may propose explanatory language or candidate factual narrative, but not invent charges, mandatory text, rank/date/number or signatory details.
6. Run template constraints, date/competence checks and any required accompanying-document checklist.
7. Explain failures and unresolved requirements with exact supporting evidence, possible corrections and conditions. The user remains responsible for factual accuracy and choice of lawful route.
8. Export an editable draft (DOCX as preferred design target), optionally PDF, plus a checklist/validation report. Label draft state; do not autogenerate a signed, served, witnessed, adjudicated or otherwise completed instrument.

Never silently pre-fill “hearing completed”, an accused's acknowledgment, a medical conclusion, signatures, dates, evidentiary facts or any officer's decision.

## 6. Auditing an existing document

A User or Admin may upload a working DOCX/PDF/scan to a temporary Document Studio session:

1. **Parse and preserve locally for the session:** obtain text plus tables/images, detect OCR uncertainties, keep the input unchanged, capture checksums and page anchors for the review report.
2. **Identify document and template version:** match to registered forms based on source/heading/layout; ask if multiple plausible sources or historic versions exist.
3. **Compare prescribed structure:** required labels/sections/table rows/numbering/signature blocks, with source-specific tolerance for permitted variants; do not reject harmless reflow or an approved alternative layout.
4. **Check content and legal elements:** charge or instrument language, required particulars, one-offence/one-charge requirements where applicable and verified, legal provision as-of date, competent signatory and conditional exceptions.
5. **Check internal consistency:** names, ranks, service numbers, unit names, dates, duty status, allegations, numbering, cross-references, logical sequence and duplicate/conflicting statements.
6. **Check procedural context:** identify prerequisites and required supporting documents. If the input alone cannot establish a fact (e.g. whether a prior hearing occurred), report **NOT_VERIFIABLE_FROM_DOCUMENT**, not “complied” or “invalid”.
7. **Produce a traceable finding:** finding ID, issue, detected excerpt/page, exact law/template requirement source, effective date, severity and type, verification level, limitations, explanation and proposed correction if supportable.
8. **Present a differential revision:** original versus proposed wording/format, human accept/reject, editable revised copy on demand. Do not change the original input or present inferred fixes as legally approved.
9. **Issue an audit report:** clearly distinguish technical/format compliance, legal issues requiring a competent reviewer, unknown surrounding facts and defects not checked.

**Severity must not be confused with legal consequence.** A missing field, potential procedural irregularity and judicially established invalidity are distinct. The application cannot pronounce a document “legally valid” or “legally void” solely from automated parsing.

## 7. Multi-document packs and dependency checks

Allow the user to provide a set of related drafts/records for one procedural matter without making them a permanently shared case repository. Compare:
- person and unit identity consistency;
- dates, sequence and time intervals;
- offence allegation and legal references across forms;
- stage-specific signature/service records and witness/medical evidence if legitimately applicable;
- mandatory versus conditional source-backed supporting documents;
- missing records, partial scans and inconsistent document versions.

The report must identify **what was checked**, **what documents were not supplied**, and **what facts cannot be verified**. No file-completeness claim unless the applicable procedure, stage, scope and governing source set are established.

## 8. Checklist and lesson integration

Checklist items should be classified as:
- **MANDATORY_SOURCE_SUPPORTED:** exact binding text, applicable dates and conditions separately verified and legally validated where required;
- **CONDITIONAL_SOURCE_SUPPORTED:** required only if a stated fact/procedure branch applies;
- **ADMINISTRATIVE_OR_LOCAL:** applicable official administrative/template requirement, with its issuer/version and scope verified;
- **PRACTICAL_RECOMMENDATION:** helpful but not legally required, with rationale and any supporting case;
- **RESEARCH_UNVERIFIED:** a lead or unresolved issue, not enforceable by the document checker.

A checklist item may cite a source statute, published policy, judgment, verified proposition or formal template. Apply the operational-use gate in section 3.2 to mandatory/conditional/admin requirements.

### 8.1 Dependency impact and stale-guidance controls

Maintain reverse dependencies from each requirement, form version, proposition and advisory to the exact underlying evidence and legal date/scope. An amendment, controlling judgment, withdrawal, corrected source, imported release change list ([Architecture 9.1](LEGAL_KNOWLEDGE_ARCHITECTURE.md#91-release-updates-and-local-sources)) or credible unresolved material contradiction triggers scoped impact assessment. Credibility and materiality criteria, and who may dismiss a trigger or re-enable a scope, are defined in section 3.3. Record trigger, affected dates/conditions, dependent IDs, reason, decision and reviewer. Unverified new uploads produce research leads and a review queue, not automatic supersession of established law. Where a credible material issue makes a current obligation unresolved, immediately mark that affected scope REVALIDATION_REQUIRED/BLOCKED and prevent definitive advice, authoritative generation, or a passing mandatory-check result based on the affected requirement; unaffected scopes and evidenced historical use remain available. No silent replacement of source bytes, approval or history. Re-enable only after evidence and a Legal Reviewer's approval at the required tier (section 3.3) of a new or reaffirmed scoped revision. Invalidate affected active caches and compiled rule sets; re-check before export or response, including already-open sessions. Previously exported reports remain dated records, not perpetually valid assurances; do not claim to recall external downloads. If later reopened, show the changed status and offer re-review.

Avoid treating a court's statement about a particular case as a universal document requirement without examining the ratio, scope and subsequent treatment.

## 9. Audit outputs and reproducibility

### 9.1 Document Readiness Report

Every generation/audit result offers a source-linked readiness report, with **no aggregate legal-compliance score**. List each check's applicability, tested input location, governing source and date basis, status, finding, outstanding human decision and next verification step. Distinguish PASS_FOR_TESTED_REQUIREMENT, FAIL_SOURCE_SUPPORTED, REVIEW_REQUIRED, NOT_VERIFIABLE_FROM_DOCUMENT, NOT_PROVIDED, NOT_APPLICABLE (with rationale), and NOT_CHECKED. Distinguish a mechanically detected inconsistency from a legal conclusion. Display tested versus untested coverage and material blockers; never label a pack or draft "legally valid", "ready for issue", or "proceedings compliant" from the report alone. Required human verification and signature remain pending. Allow export of an editable unsigned draft and its separate dated findings/checklist report (with clear research-only restrictions under section 3.2), preserving the original.

### 9.2 Replay and trace

Store in the **temporary session** the source template version and rules revision, input hashes, parser/OCR versions, the controlling event date(s) and date basis used for each constraint, tested fields, checks performed/not performed, warnings, source citations, and proposed changes. Allow local download of the report and editable draft; do not transmit it online or import its incident facts into the shared legal source corpus.

If the temporary session is cleared, the user's downloaded report should contain enough identifiers to re-run/reconstruct the review against the same published corpus revision, **subject to availability of any original confidential input retained by the user**. Replay is also subject to the referenced published content still being available to ordinary users. If a referenced source or template has since been withdrawn or become ineligible, replay against that revision is refused for ordinary users: the system reports which identifiers are no longer available and offers re-review against current published content. It never re-exposes withdrawn text. Never claim that the application retains a case file after session deletion.

## 10. Architecture placement

```text
ADMIN SOURCE INGESTION -> review/publish authoritative source candidates
                                |
                    PUBLISHED LEGAL LIBRARY
                                |
             source-linked FORM/TEMPLATE REGISTRY
                  |                     |
            DOC GENERATOR          DOC AUDITOR
                  +----------+----------+
                             |
          TEMPORARY WORKING SESSION (all app users)
                             |
                 EDITABLE DRAFT + AUDIT REPORT
```

Legal source/template publication remains Admin-controlled. A user-facing Document Studio upload is **only a working input**; it never creates a common-source ingestion job, new global graph edge or an authenticated law change.

## 11. Acceptance tests and evaluation

- Inventory a selected source appendix with known printed forms: every field, footer, table and appendix reference can be traced to the **actual page**, not an LLM paraphrase.
- Prepare a draft using a verified template: rendered fields/layout match the source and the auditor applies exactly the same versioned constraints.
- A changed incident date or stage selects a different form version when justified, or blocks definitive choice when the amendment chain is unresolved.
- Cross an amendment between conduct and procedural action; independently test different substantive/procedural controlling dates, applicable saving provisions and unknown dates. A document-preparation date must not silently replace the controlling date.
- Exercise the operational-use gate: publish a faithfully transcribed historical/unvalidated specimen; it is searchable but cannot activate an authoritative template or mandatory constraint. Legal validation requires the exact attributable approval and scope; unresolved authority blocks operational use.
- Generate an incomplete draft: mandatory-field errors are identified, while signatures/procedural acts remain unfilled; the export clearly states that human verification is needed.
- Audit independently prepared correct, borderline and deliberately defective drafts from an answer key constructed directly against the original forms, governing dated provisions and approval evidence, **without deriving the oracle from generator output, shared validation logic or the same rule-authoring process**. Keep blinded holdouts and record the source pinpoints and reviewer decisions. Obtain competent legal review of high-consequence answer keys. Measure false positives, missed material defects, wrong date/version, incorrect legal provision, missing particulars and mistaken pass/abstain outcomes separately. Test render-to-document fidelity against original source images; shared generator/auditor agreement alone is insufficient.
- Upload a scanned form with illegible text: the checker returns uncertainty and page-image references rather than making up the missing content.
- Submit a multi-document pack with conflicting service number or dates: report exact source spans and distinguish detected contradiction from a legal conclusion.
- Confirm that an ordinary User can upload a **working document** for review but cannot upload or publish it into shared law/search/template records, even through a direct API.
- Withdraw a published template: new generation cannot silently keep using it as current; preserve the original source, approval and publication history in the appropriate authorised store. Eligible, still-published historical versions remain available for research; withdrawn or ineligible content must not leak through ordinary-user research, cached outputs or old report replay. Previously exported reports remain dated user records.
- Exercise the approval path (section 3.3): with no recorded appointment the gate refuses every operational output; an Admin-transcribed external approval stays unconfirmed and does not open the gate; an Admin account cannot record a legal approval; an approval pinned to revision N does not apply to revision N+1; a T1 approval does not satisfy a T2-required output class; revoking an appointment or approval re-blocks new outputs while keeping historical records.
- Replay an old report after a referenced template is withdrawn: replay is refused for that revision with the unavailable identifiers listed, and no withdrawn text is shown.
- Add an unverified supersession claim (candidate only), then introduce credible material contrary authority: affected scopes must stop definitive output, including cached/open-session results, until revalidated; unaffected scopes and supported historical versions continue working. Reopen an old audit and show current status without editing the dated original report.
- User A cannot retrieve User B's file, OCR job, AI context, finding, cached result or export by a direct URL, guessed/known ID, or switching sessions; Admin's corpus role does not grant general access to other users' working sessions. Verify cleanup of temporary derivatives and no sensitive text in ordinary logs.
- Readiness report distinguishes passed, failed, not supplied, not applicable, unknown, untested and review-required items with citations; missing prerequisites never turn into a global readiness/legal-validity score.
- Inject fake instructions into a draft: parser/model does not execute those instructions or alter the legal-rule engine.
- Test disconnected operation, local output export, working-file cleanup and absence of shared-index leakage.

## 12. Pilot selection and boundaries

Begin with a **source-verified charge-sheet form family** and a small set of closely related procedural forms identified through the actual applicable source editions. This is an inventory/research priority, **not a claim that the exact form and requirements have already been authenticated**. A broader inventory should follow based on recurring commander needs and document risk.

No implementation, generated operative instrument, formal legal certification, original KB amendment or shared-source publication is authorised merely by this specification.
