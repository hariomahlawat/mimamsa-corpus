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
| Upload/edit/publish a source manual, SOP or template for shared use | Yes | No | Admin staging, then shared corpus after explicit publication |
| Withdraw, replace or reprocess shared source/template | Yes | No | Admin-managed, audited |

Normal working files are not permanently added to source-corpus records, Hugging Face, common search, embeddings, graph edges or training data. A working document cannot be promoted to the shared library by a User or through ordinary generation/review APIs. Apply simple temporary-session isolation, cleanup/retention controls, file-size and safe-parser checks. A deliberate Admin knowledge-base submission is a **separate action and workflow** requiring publication approval.

## 3. Inventory and classification: locate the actual forms

Before creating working templates, systematically inspect original, legally accessible and appropriate-edition materials:

- Army Act and Army Rules, including appendices and their amendments;
- the eight user-provided Manual of Military Law files, **only as edition-unverified practical references until authenticated**;
- applicable Defence Service Regulations / Regulations for the Army and relevant source amendments;
- authorised published Army Orders, Army Instructions, government forms and other Admin-admitted service policies/SOPs;
- relevant court judgments for actual procedural interpretation and legally significant defects.

The discovery process must find **forms and tables in scanned pages**, not rely on text search alone. Capture form title, number, exact page/paragraph/appendix, provenance, printed wording, images, tables, field layout, mandatory-versus-example language, amendment/commencement state and whether it is currently applicable. Compare source editions, identify collisions and send unverified copies or conflicting versions to a research queue.

**Form classification is compulsory:**
1. **Statutory prescribed form:** explicitly mandated by an operative Act/Rule or instrument; verify identity and applicability.
2. **Official specimen / illustrative form:** useful for faithful drafting but not automatically prescribed in every case.
3. **Official service/administrative template:** based on an applicable authenticated order/instruction/regulation; rank/period/stage constraints still apply.
4. **Research candidate / historical template:** unverified or superseded; discoverable with warnings but never silently offered as an authoritative current form.

The exact legal-source status must not be inferred merely from the word “form”, “Appendix”, “Manual” or a document's hosting domain.

## 4. Canonical registry and rule model (proposed)

A `FormTemplate` records:
- stable template ID, name, purpose, category and document family;
- prescribed/specimen/service/historical classification and authority basis;
- source document identity, exact copy SHA-256, page, printed form number, paragraph/appendix and passage/image locator;
- date(s): issue, commencement, applicable interval and version/supersession evidence;
- applicability by service status/rank, forum, case type, authority and **procedural stage**, with UNKNOWN supported;
- document layout: fields, tables, repeated sections, labels, instruction text, signature blocks and formatting tolerances;
- `FieldRequirement` records for mandatory/conditional/optional fields with conditions and source evidence;
- `DocumentConstraint` records: syntax, legal elements, cardinality, cross-field/date checks, competent signature, and source-linked rationale;
- `RelatedDocumentRequirement`: prerequisite/conditional/supporting companion documents and whether their existence can be tested from uploaded evidence;
- `TemplateReview`: documentary fidelity review, legal applicability review, explicit decisions, reviewer, date and version;
- version ID, schema/check engine version, publishing history and known adverse conflicts.

**Single rule source:** The generator, pre-export checks, independent document auditor and procedural checklists must use the **same approved versioned constraint definitions**. Do not create two drifting interpretations of a form.

A case's applicable date and stage may affect template selection; only an identified and source-supported version may be described as prescribed. Preserve historical and conflicting versions for research.

## 5. Creating a document

1. User chooses a document or asks a situation question, e.g. “Prepare a charge-sheet for a reported offence.”
2. Resolve **which legal procedure and document type** actually applies, and the relevant case/incident date, service status, forum and stage. If essential facts or current source authority cannot be established, show candidates and ask targeted questions; do not claim a prescribed format.
3. Display the source form, citation and its review/applicability status. If unverified, allow at most an explicitly labelled research draft, not a “legally compliant” template.
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

A checklist item may cite a source statute, published policy, judgment, verified proposition or formal template. If the source is amended, withdrawn, superseded or contradicted by later authority, flag dependent forms/checks for **review**, rather than rewriting them automatically.

Avoid treating a court's statement about a particular case as a universal document requirement without examining the ratio, scope and subsequent treatment.

## 9. Audit outputs and reproducibility

Store in the **temporary session** the source template version and rules revision, input hashes, parser/OCR versions, applicable legal date, tested fields, checks performed/not performed, warnings, source citations, and proposed changes. Allow local download of the report and editable draft; do not transmit it online or import its incident facts into the shared legal source corpus.

If the temporary session is cleared, the user's downloaded report should contain enough identifiers to re-run/reconstruct the review against the same published corpus revision, **subject to availability of any original confidential input retained by the user**. Never claim that the application retains a case file after session deletion.

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
- Generate an incomplete draft: mandatory-field errors are identified, while signatures/procedural acts remain unfilled; the export clearly states that human verification is needed.
- Audit a correct draft and an independently corrupted draft: track both false positives and missed material defects, including incorrect legal provision, missing particulars and mismatched dates.
- Upload a scanned form with illegible text: the checker returns uncertainty and page-image references rather than making up the missing content.
- Submit a multi-document pack with conflicting service number or dates: report exact source spans and distinguish detected contradiction from a legal conclusion.
- Confirm that an ordinary User can upload a **working document** for review but cannot upload or publish it into shared law/search/template records, even through a direct API.
- Withdraw a published template: new generation cannot silently keep using it as current; historic source remains preserved for research and previously issued audit reports remain traceable.
- Inject fake instructions into a draft: parser/model does not execute those instructions or alter the legal-rule engine.
- Test disconnected operation, local output export, working-file cleanup and absence of shared-index leakage.

## 12. Pilot selection and boundaries

Begin with a **source-verified charge-sheet form family** and a small set of closely related procedural forms identified through the actual applicable source editions. This is an inventory/research priority, **not a claim that the exact form and requirements have already been authenticated**. A broader inventory should follow based on recurring commander needs and document risk.

No implementation, generated operative instrument, formal legal certification, original KB amendment or shared-source publication is authorised merely by this specification.
