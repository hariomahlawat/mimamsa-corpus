# Mimamsa: Product vision and requirements

**Recorded:** 2026-11-24  
**Status:** Owner-confirmed product direction; detailed feature designs are proposals pending technical/legal review.  
**Audience:** Product owner, corpus maintainers, military legal reviewers and future authorised implementers.

## 1. Purpose

Mimamsa is intended to become a **fully offline Indian military-law research and controlled decision-support system**. It should allow a commander to ask about a real unit situation in ordinary English, without knowing an Act, Rule or case citation, and obtain an understandable, legally evidenced path to further action. Legal practitioners must also be able to inspect original authorities, source conflicts, alternative interpretations and applicable dates.

**Design principle:** The user describes the problem. Mimamsa helps identify the legally relevant facts, retrieves the governing material, distinguishes verified law from research candidates, and presents evidence-linked options, safeguards and escalation requirements. It does not decide guilt, select punishments, sign orders or replace the competent authority or JAG.

## 2. Users and their jobs

| User | Typical need | Required behaviour |
| --- | --- | --- |
| Unit commander | “A sepoy is drunk on duty; what now?” | Immediate safety considerations, material fact questions, lawful procedural routes, safeguards and source links |
| Adjutant/staff officer | “The accused refuses a signature; does the case stop?” | Identify the document and stage; clarify requirements and evidence, avoid invented procedure |
| JCO/NCO | “Which rules are relevant to this situation?” | Same published documents and research features as every other admitted app user, with plain-language presentation |
| JAG/legal practitioner | “Which precedents govern this disputed interpretation as of a date?” | Full source passages, contrary treatment, amendment history and unresolved questions |
| Researcher/content reviewer | “Which assertion needs more proof?” | Reproducible evidence chain, status history, correction and review queue |
| Admin | “Upload a new SOP, verify its processing and publish it for everyone.” | Upload and stage, review source eligibility and extraction, publish or withdraw, reprocess and inspect candidate graph links |
| Any admitted user (Document Studio) | “Prepare a charge-sheet or review an already prepared document.” | Use source-backed form guidance, guided drafting, a checklist and a non-certifying audit without altering the shared corpus |

## 3. Approved direction: capability requirements

Identifiers are stable requirement references, **not** statements that a feature exists.

- **PR-01 Full published research access.** Admin and User can equally search and access every **published** document and research/advisory feature, including unreviewed original judgments labelled as such. Admin alone can modify the corpus through upload, publication, withdrawal, replacement and reprocessing. No per-document viewing restrictions or further rank/JAG role tiers. Source access markings and deployment-wide eligibility remain mandatory.
- **PR-02 Statute-first exploration.** A user opening an Act, Rule or regulation can discover historical versions, related judgments, legal propositions, open conflicts and associated procedure/checklist research.
- **PR-03 Plain-English scenarios.** Understand informal language, misspellings and commonly used military vocabulary. Do not require an Act or section number in the prompt.
- **PR-04 Material-fact dialogue.** Identify questions that can change the applicable provision, legal route, urgency or competent authority. Ask a small number in priority order; handle unknown answers.
- **PR-05 Actionable but bounded response.** Explain immediate considerations, possible legal routes, procedural safeguards, evidence requirements, significant judgments, limitations and who must decide. Do not invent mandatory steps.
- **PR-06 Source-grounded claims.** Every substantive conclusion or checklist requirement must refer to identifiable authoritative evidence, with the relevant date/version and pinpoint.
- **PR-07 Judgment intelligence.** Provide original source access and structured research cards: facts, issues, actual disposition per proceeding, relevant law, reasoning, later treatment and possible lessons, with verification status per field.
- **PR-08 Connected knowledge.** Link Acts, provision versions, judgments, proceedings, individual propositions, treatment edges, lessons and checklists. Distinguish mere citation from application or interpretation.
- **PR-09 Lessons and checklists.** Create reusable procedural checklists and lessons from verified legal requirements and evidenced judicial findings. Candidate lessons must not be represented as approved doctrine.
- **PR-10 Temporal applicability.** Resolve the law applicable to the incident date where evidence permits, not merely the newest consolidated text. Explicitly expose incomplete commencement or amendment evidence.
- **PR-11 Explain uncertainty.** Return “not established from verified sources” when required; highlight contrary precedent, unresolved fact, source conflict or stale legal evidence rather than producing a confident answer.
- **PR-12 Entirely offline deployment.** All runtime retrieval, upload ingestion, graph processing, rule evaluation, model inference and source opening operate on an air-gapped LAN. Approved external acquisitions arrive only through controlled offline transfer; uploading local user documents requires no internet.
- **PR-13 Separate queries from Admin document ingestion.** Ordinary question/incident text stays in the session and is not silently published to shared search or model training. Only Admin can submit a source for ingestion. A document becomes available to all app users only after Admin publication; this is not a private-document workspace.
- **PR-14 Provenance and reversibility.** Preserve originals and all correction/review events. Never silently overwrite or backdate a legal assertion.
- **PR-15 Different research views, equal access.** Commander-friendly and detailed legal-research views use the same published sources. Either role can open both views; only document-management operations differ.
- **PR-16 Admin-only continuous upload.** Only Admin may submit, replace, withdraw or publish eligible policies, SOPs, instructions, judgments, circulars, manuals and other reference files over time. No developer or separate crawler invocation is required.
- **PR-17 Automated ingestion with publication gate.** On Admin upload, preserve the source, perform safety and eligibility checks, extract/OCR, identify document type/version and generate candidate provision, case and policy links. Keep the submission staged until the Admin reviews and publishes it. Shared search and graph results are updated after publication.
- **PR-18 Source-trust separation.** A newly **Admin-published** source becomes visible and searchable to all as an unverified research source, distinct from source authenticity and legal validation. Admin publication cannot automatically change operative law, verified propositions, statutory history or mandatory checklist obligations.
- **PR-19 Minimal two-role model.** The only initial roles are **Admin** (document-management authority plus all research features) and **User** (all published research and advisory features, no corpus writes). No per-user document viewing restrictions. If a source cannot lawfully be shown to all users, do not publish it into the shared index.
- **PR-20 Capability-first, basic cyber hygiene.** Prioritise search, Admin upload/publication, parsing, graph and commander capability. At launch enforce a basic Admin/User authentication boundary on all corpus mutation paths, offline perimeter controls, safe file handling, backups, integrity and isolated parsing. Advanced hardening may follow demonstrated capability.
- **PR-21 Source-backed Document Studio.** Both Admin and User may create editable military-law working documents, including charge-sheets where applicable, using only format templates with identifiable source, version, applicability and review status. Do not reconstruct a prescribed form from model memory.
- **PR-22 Form and Template Registry.** Inventory prescribed forms, statutory specimens, official service templates and administrative formats in applicable Army Rules appendices, authenticated MML editions, Defence Service Regulations, Army Orders/Instructions and later Admin-published sources. Capture exact page/appendix/paragraph, form image and status, and preserve conflicting/historical versions.
- **PR-23 Guided drafting and document sets.** Ask for only material facts, procedural stage and competent authority; guide required fields and supporting documents; create an editable DOCX or other approved export, leaving legal selection, final verification and signature to the competent person.
- **PR-24 Existing-document audit.** Both roles may submit an existing PDF/DOCX or scanned document to a temporary working session. Check format, internal and cross-document consistency, date/version, source-supported requirements, omissions and procedural preconditions. Provide cited findings and possible corrections without claiming a complete legal certification.
- **PR-25 Procedural checklists and file completeness.** Provide stage-appropriate lists distinguishing legally mandatory, conditional, locally prescribed and recommended checks; identify prerequisite records and where the submitted file is insufficient to determine compliance.
- **PR-26 Working-document separation.** A User's draft or review upload is **not** a knowledge-base contribution and is not visible in public/shared search, embeddings, graphs, template registry or model training. Implement session isolation, reasonable working-file lifecycle, safe processing and export. Admin-only publication remains the sole way to modify shared source/template records.
- **PR-27 Synchronized generator and auditor.** Generation, validation, reviews and checklists must use the same versioned source-backed field/constraint definitions, with separate detection of hard rule failures, review warnings and unverified questions. Do not mark a draft “legally valid” from automated tests alone.
- **PR-28 Impact and reproducibility.** On new law/policy evidence, identify impacted templates, checklists, validation rules and existing research propositions for re-examination. Preserve exact template/policy versions and source anchors used for each generated/audited document.

## 4. Intended user journey

1. **Ask:** “A JCO has refused to sign a charge-sheet. What should I do?”
2. **Recognise:** Could refer to the commanding officer's signature, service/receipt acknowledgment, an evidentiary statement or another document. Do not pick an interpretation prematurely.
3. **Establish facts:** Ask which document and procedural stage, and whether the accused received or was informed of the charges.
4. **Retrieve law:** Exact provision/version and any relevant procedural requirements, with original passages.
5. **Check cases:** Applicable holdings, adverse treatment and procedural lessons.
6. **Respond:** Immediate checks, conditional routes, what remains uncertain, source pinpoints and escalation to a competent legal authority when needed.
7. **Inspect:** Let the user open the actual source and see why the answer changes if a material fact changes.

Never treat the user’s allegation as a judicially established fact.

## 5. Full corpus versus validated knowledge

The first release need not wait for formal review of every judgment. **Full-text source search** and **legally validated answers** are separate products drawing on the same vault.

| Layer | Exposure rule |
| --- | --- |
| Admitted original judgments, legal sources and uploaded documents | Searchable by all app users with source identity, completeness and verification warnings |
| Automated extraction and candidate links (including upload-derived edges) | Searchable/discoverable, explicitly labelled unverified and not automatically relied upon |
| Independently checked documentary facts | Display review provenance and remaining legal questions |
| Substantive legally approved propositions/procedures | Identifiable approval record, precise applicability and evidence |

The C10 audit reported approximately 3,959 judgment files, 4,259 judgment metadata records and 3,936 processed files; the exact current inventory is revision-specific. File count is not a verified distinct-judgment count. C10 also found high outcome-extraction error rates; do not promote such outcomes automatically.

## 6. Product modes (proposed)

- **Library:** Search, filter, read originals, compare copies and citations.
- **Provision explorer:** View original text, temporal versions, case connections and amendment doubts.
- **Case intelligence:** Read a structured case card with each conclusion and treatment edge linked to source.
- **Commander guidance:** Situation-first guided research with conditional, stage-aware checklists.
- **Learning/lessons:** Browse evidenced procedural issues, observed failure modes and related cases.
- **Legal review workspace:** Escalation queues, correction proposals, provenance and review decisions.
- **Admin document management:** Only Admin uploads, reviews processing, publishes, withdraws, replaces or reprocesses sources. All published documents and candidate relationships remain searchable and inspectable by every user.
- **Document Studio:** Every user can select a prescribed/approved format, prepare or review a working document, view cited checks and download an editable draft or audit report. This is a temporary workspace, never a new shared source without Admin action.

The conversational assistant is an interface to this evidence system; it is not the system of record.

## 7. Non-goals and boundaries

No autonomous allegation assessment, legal adjudication, sanction recommendation, punishment selection, fabrication of forms, automatic case filing or substitution for statutory competence. Never silently convert uncertain source text or an uploaded policy into current law, or use an old manual alone as current authority. No data leakage to external inference or telemetry.

Access is simple, not fully flat: **Admin** alone controls shared source/template ingestion and publication; **Admin and User** share access to every published document, research/advisory function and temporary working-document drafting/review. Do not design deeper role hierarchies, rank/JAG feature tiers or private user document folders. Pending uploads remain outside shared search until publication. Apply deployment-wide eligibility; a document incompatible with universal app-user access must not appear in published results, snippets, embeddings or generated answers. Standard cyber hygiene and untrusted-upload isolation remain essential.

Lawfully published judicial originals are preserved faithfully, without masking personal, service or medical details merely because they appear in a judgment. Specific binding publication restrictions and appropriate access controls remain applicable.

## 8. Success measures

Measure separately:
- fraction of retained source bytes preserved/recoverable and checked;
- unique judgment/proceeding identity accuracy;
- source search coverage and relevance;
- citation and provision-date exactness;
- extraction precision/coverage on an independent, blinded gold set;
- proposition attribution correctness;
- treatment-edge evidence and legal review rate;
- scenario route correctness, required fact-question recall and safe escalation;
- percent of displayed mandatory checklist items supported by validated sources;
- completeness/integrity of offline release and lack of network dependency.
- Admin-upload processing success, eligibility review and publication turnaround, deterministic provenance, OCR/extraction quality and time to inclusion in shared search;
- measured relevance and false-positive rates for automatically suggested upload-to-law/judgment graph links;
- proof that non-Admin users cannot upload, publish, withdraw, replace or reprocess source documents;
- proof that both roles can submit temporary working documents for generation/audit but those bytes, content and embeddings never enter shared corpus without a separate Admin-controlled ingestion action;
- reviewed format fidelity, field validity and cross-document consistency of generated drafts against the exact applicable source-form version;
- independent detection and false-positive rates for draft audit findings with referenced source anchors;
- demonstrated non-promotion of Admin-published but legally unverified documents into mandatory guidance;
- baseline security checks for file safety, integrity, backups and isolated parsing.

**Do not use a single synthetic “legally accurate” percentage.**

## 9. Phased delivery recommendation

**Foundation first:** preserve vulnerable sources, reconcile HF/GitHub, maintain frozen originals.  
**Research breadth:** full accessible judgment search; correct judgment identities and copies.  
**Knowledge depth:** provision/version graph, proposition passports, case treatment and legal lessons; automated user-upload ingestion and candidate graph linking in early product capability work.  
**Scenario pilot:** reuse the existing 50-question golden test set referenced in `CLAUDE.md` where applicable; extend it with an independently reviewed commander-scenario benchmark and blinded variations. Pilot 10–15 high-value scenarios, then expand.  
**Document Studio pilot:** inventory and verify source-backed form templates, then pilot a charge-sheet and closely related documents with generator/auditor parity, original-preserving review and cross-document consistency tests. This is a proposal, not approval to issue any form.  
**Controlled offline release:** evidence-complete, explicitly scoped, reviewable and versioned; never claim blanket legal approval.

## 10. Policy and traceability

The legal requirements in this document are product requirements, not legal findings. Source authentication and legal-status decisions continue under:
- `docs/legal-audit/EVIDENCE_STANDARD.md`
- `docs/legal-audit/SOURCE_AUTHORITY_POLICY.md`
- `legal_knowledge/audit_work/AUTH-LEDGER/README.md`
- `docs/architecture/CONTINUOUS_DOCUMENT_INGESTION.md`
- `docs/architecture/DOCUMENT_STUDIO_AND_TEMPLATE_REGISTRY.md`
- `docs/architecture/decisions/ADR-0002-SHARED_ACCESS_AND_CONTINUOUS_INGESTION.md`
- `docs/architecture/decisions/ADR-0003-DOCUMENT_STUDIO_AND_TEMPLATE_REGISTRY.md`

Track design changes through a reviewable ADR; all code, schemas and ledger alterations require a separate authorised change.
