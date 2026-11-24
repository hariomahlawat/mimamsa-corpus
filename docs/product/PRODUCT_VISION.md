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
| JCO/NCO | “Which rules are relevant to this situation?” | Same documents and features as every other admitted app user, with plain-language presentation |
| JAG/legal practitioner | “Which precedents govern this disputed interpretation as of a date?” | Full source passages, contrary treatment, amendment history and unresolved questions |
| Researcher/content reviewer | “Which assertion needs more proof?” | Reproducible evidence chain, status history, correction and review queue |
| Any app user | “Upload a new SOP or policy and connect it to our legal material.” | Upload, extract, analyse, search and inspect candidate links in the common corpus |

## 3. Approved direction: capability requirements

Identifiers are stable requirement references, **not** statements that a feature exists.

- **PR-01 Full shared corpus access.** Every user admitted to the deployment may access the entire admitted corpus and every app feature, including unreviewed original judgments. No RBAC or per-document user permissions. Source access markings must be retained and material inappropriate for the whole deployment audience excluded or kept outside the shared corpus.
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
- **PR-13 Separate queries from intentional uploads.** Ordinary question/incident text stays in the session and is not silently published into the shared corpus or model training material. A deliberate document upload is clearly disclosed as **shared with all app users** after ingestion; do not provide a misleading private-upload option in the single-access design.
- **PR-14 Provenance and reversibility.** Preserve originals and all correction/review events. Never silently overwrite or backdate a legal assertion.
- **PR-15 Different views, equal access.** Commander-friendly concise guidance and detailed legal-research views use the same source collection. Any admitted user can open either view.
- **PR-16 In-app continuous upload.** Any app user can add eligible policies, SOPs, instructions, circulars, manuals and supporting reference files over time; no developer or separate crawler invocation is required.
- **PR-17 Automatic ingestion and integration.** Preserve the uploaded file, extract/OCR its contents, identify document type and version, detect relevant provisions and cross-references, and construct searchable candidate knowledge-graph edges and related-document suggestions.
- **PR-18 Source-trust separation.** A new user upload is visible and searchable as a user-provided, unverified research source once accepted and processed, but cannot automatically change the operative law, verified propositions, statutory history or mandatory checklist obligations.
- **PR-19 One common access domain.** No user roles, feature tiers or per-user document permissions in the initial product. Import eligibility is deployment-wide: if a source cannot lawfully be shown to all users with app access, do not ingest it into the shared index.
- **PR-20 Capability-first, basic cyber hygiene.** Prioritise dependable search, upload, parsing, legal connections and scenario usefulness; retain basic authentication/perimeter controls, safe file handling, local backups, integrity checks and network isolation from the first release. Advanced hardening may follow demonstrated capability.

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
- **Add documents:** Any app user uploads a policy/SOP/other eligible file, sees processing status, and opens its extracted text, candidate relationships and linked graph.

The conversational assistant is an interface to this evidence system; it is not the system of record.

## 7. Non-goals and boundaries

No autonomous allegation assessment, legal adjudication, sanction recommendation, punishment selection, fabrication of forms, automatic case filing or substitution for statutory competence. Never silently convert uncertain source text or an uploaded policy into current law, or use an old manual alone as current authority. No data leakage to external inference or telemetry.

Access is flat: all admitted users share all features and admitted documents. Do not design role hierarchies or private document folders. Apply a single deployment-level source-eligibility boundary; a document whose restrictions are incompatible with universal app-user access must not be exposed through shared search, snippets or generated answers. Standard cyber hygiene and untrusted-upload isolation remain essential.

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
- user-upload processing success, deterministic provenance, OCR/extraction quality and time to inclusion in shared search;
- measured relevance and false-positive rates for automatically suggested upload-to-law/judgment graph links;
- demonstrated non-promotion of unreviewed uploads into mandatory legal guidance;
- baseline security checks for file safety, integrity, backups and isolated parsing.

**Do not use a single synthetic “legally accurate” percentage.**

## 9. Phased delivery recommendation

**Foundation first:** preserve vulnerable sources, reconcile HF/GitHub, maintain frozen originals.  
**Research breadth:** full accessible judgment search; correct judgment identities and copies.  
**Knowledge depth:** provision/version graph, proposition passports, case treatment and legal lessons; automated user-upload ingestion and candidate graph linking in early product capability work.  
**Scenario pilot:** reuse the existing 50-question golden test set referenced in `CLAUDE.md` where applicable; extend it with an independently reviewed commander-scenario benchmark and blinded variations. Pilot 10–15 high-value scenarios, then expand.  
**Controlled offline release:** evidence-complete, explicitly scoped, reviewable and versioned; never claim blanket legal approval.

## 10. Policy and traceability

The legal requirements in this document are product requirements, not legal findings. Source authentication and legal-status decisions continue under:
- `docs/legal-audit/EVIDENCE_STANDARD.md`
- `docs/legal-audit/SOURCE_AUTHORITY_POLICY.md`
- `legal_knowledge/audit_work/AUTH-LEDGER/README.md`
- `docs/architecture/CONTINUOUS_DOCUMENT_INGESTION.md`
- `docs/architecture/decisions/ADR-0002-SHARED_ACCESS_AND_CONTINUOUS_INGESTION.md`

Track design changes through a reviewable ADR; all code, schemas and ledger alterations require a separate authorised change.
