# Scenario advisory engine: requirements and decision logic

**Recorded:** 2026-11-24  
**Status:** Proposed design, not implemented and not a legal SOP.  
**Scope:** Fully offline, evidence-grounded assistance for actual plain-English unit-level questions.

## 1. Goal

A commander asks “My sepoy was found drunk on duty; what should I do?” rather than “Interpret Section X.” The system should recognise possible issues, provide urgent non-punitive safety considerations, identify what facts change the legal route and present **legally supportable** next steps with source pinpoints and limitations.

**No autonomous punishment, guilt finding, disciplinary charge, administrative sanction or document execution.**

## 2. Inputs and outputs

**Inputs:** natural-language question, optional incident context, date, location/jurisdiction, service category, rank, document/stage, explicit facts and unknowns. All admitted app users share the same features and legal corpus; there is no user-role decision input.

**Outputs:** structured incident interpretation; immediate safety/welfare considerations where necessary; facts established versus alleged; governing candidate provision versions and why they might apply; material follow-ups; lawful procedural paths with prerequisites and competent authority; evidence/safeguard checklist; relevant judgments and proposition-level treatment; limitations and escalation; source links and review quality for each assertion.

**Query separation:** ordinary unit-incident question text remains in a session, never in the shared corpus by default. Intentional document uploads are explicitly shared with all app users. No per-user document permissions or role-specific workspaces are part of the initial product.

## 3. Processing flow

1. **Interpret language:** normalise common misspellings, military abbreviations and Indian-English/Hinglish variants. Generate multiple possible intents where ambiguity exists.
2. **Safety and welfare triage:** if ongoing armed-duty, custody, medical or immediate-harm concern exists, prioritise appropriate provisional risk reduction without declaring an offence proven.
3. **Recognise scenario family and stage:** candidate offences, family/service issue, complaint, trial document, grievance etc. Distinguish user reporting an allegation from a court-established fact.
4. **Identify material facts:** select the few questions that could actually change the applicable authority, jurisdiction, legal version, competent person or procedural safeguard. Use `UNKNOWN` explicitly.
5. **Retrieve law for relevant time:** original statute/Rule/Regulation and commencement/amendment chain, with source authority and historical validity evidence. Search user-uploaded policies and SOPs as clearly labelled supplemental sources, never as automatically binding law.
6. **Evaluate applicability:** only predicates supported by the relevant sources and the required legal-review status may determine mandatory steps or bar an option. AI or an uploaded SOP may propose candidates but cannot independently certify a legal route.
7. **Retrieve precedent:** search all legally accessible original judgments, passage-level matches, reviewed propositions, later treatment and adverse authorities. Keep candidate relationships labelled.
8. **Build response:** short commander-first steps, facts/limitations, conditional options, checklist and expandable JAG source view.
9. **Validate response:** fail closed on unsupported mandatory requirements, invented citations, missing date/version, unresolved decisive facts or conflicts; escalate to JAG where warranted.
10. **Record trace:** snapshot IDs, source/edge IDs, upload version where applicable, rule version, review status and response version. Keep incident query text separate from the shared index; retain only the session/audit information needed for operation and diagnostics.

## 4. Evidence and applicability rules

Each proposed advisory item must have:
- `guidance_id` and issue/scene;
- exact supporting `EvidenceAnchor` and `ProvisionVersion` or reviewed legal proposition;
- effective period, jurisdiction, rank/status and procedure-stage predicates;
- competent authority, if evidenced;
- prerequisites, exceptions and conflicting evidence;
- `binding_or_nonbinding` classification and whether authority is statute/court, service-policy assertion or unverified upload;
- independent documentary and legal-review status;
- blocking conditions and escalation route;
- audit/version identity.

Do not promote a candidate summary or inferred legal lesson into a mandatory rule without applicable authority. Absence of adverse authority in the indexed corpus is not proof that none exists.

## 5. Model of legal workflows

Use **conditional workflow transitions**, not fixed advice strings.

`
scenario + known facts + source versions + rule version
    -> admissible candidate routes
    -> required preconditions and safeguards
    -> source-backed checklist items
    -> unresolved blockers/escalation
`

A transition can be `AVAILABLE`, `BLOCKED`, `CONDITIONAL` or `UNKNOWN`. The user should see why a transition is in that state. No assumption should turn `UNKNOWN` into `AVAILABLE`.

The assistant must not infer a procedural deadline, witness-signature requirement, criminal charge, sentence or administrative power from analogy alone.

## 6. Illustrative scenario branching (not legal determinations)

### S-01: Reported intoxication on duty

- **First:** ongoing danger? armed/sensitive duty? medical attention required? Immediate safety and humane response may precede lengthy legal analysis.
- **Facts:** role/status, duty at time, incident date, witnesses, evidence, any pending disciplinary stage.
- **Law:** retrieve and verify the then-applicable offence provision and procedural route; preserve presumption against treating allegations as proven.
- **Output:** safety/record-preservation considerations; lawful inquiry/procedure options only when supported; source-backed procedural safeguards; precedents and legal adviser checkpoints.

### S-02: JCO refuses to sign a “charge-sheet”

- **First:** ask which document and whose signature. Signing a formal charge-sheet is a different event from acknowledging service or signing an evidentiary statement.
- **Facts:** document identity, procedural stage, actual communication/receipt, rank/status, competent officer and available record.
- **Law:** retrieve exact Rule/Regulation requiring the relevant signature or service and evidence for handling refusal. If not established, report that no verified substitute procedure is available.
- **Output:** document/stage-specific source checks, conditional options, safeguard requirements and JAG escalation when uncertain.

### S-03: Alleged second marriage by serving jawan

- **First:** do not presume legal validity, a subsisting first marriage, a criminal offence or disciplinary power from the allegation.
- **Facts:** dates of both marriages, status/dissolution, relevant personal/customary law, proof of solemnisation, service rules/authorisation and stage of any complaint.
- **Law:** verify dated personal/criminal/service-law provisions and exceptions; distinguish administrative from criminal and disciplinary routes.
- **Output:** conditional statute map, documents needed, legal-review questions and sourced options, with no preselected charge or sanction.

## 7. Response contract (proposed UI-independent schema)

The same logical response can render in a terse commander view or detailed legal-research view.

| Section | Requirement |
| --- | --- |
| Situation understood | Show interpretation and alternative if ambiguous |
| Immediate considerations | Practical safety/welfare guidance only if relevant, labelled by status |
| Facts | Known, alleged, unknown, material questions |
| Applicable law | Instrument, provision version, date, pinpoint, evidence strength |
| Possible way forward | Conditional routes, authority and prerequisite; no autonomous selection |
| Checklist | Each item linked to legal evidence or clearly labelled general/nonbinding |
| Cases and lessons | Relevant original judgments and specific source passages, with review state |
| Cautions | Conflicts, contrary cases, age of sources, unresolved dates or JAG referral |
| More detail | Original documents, chronology, graph edges and reasoning audit |

## 8. Test strategy

Start by locating and reusing the existing 50-question golden test set referenced by `CLAUDE.md`. Add an independent, curated **commander scenario** set and keep a separate blinded holdout.

Create positive, negative and metamorphic tests:
- change duty status, rank, incident date, jurisdiction, personal law or document type;
- give an ambiguous charge-sheet signature question and require a clarifier;
- supply an unsupported compulsory signature and expect refusal to assert it;
- provide an older law date and verify temporal differences;
- hide/withdraw a source or inject contradictory source and expect a downgrade;
- change procedure stage or competence and expect a different route;
- include false quotations, editorial headnotes and cases with mixed orders;
- test unknown facts and “cannot establish from verified corpus” as a correct outcome;
- verify all mandatory checklist items have actual source and approval records;
- test entirely disconnected operation, no per-user document/feature tiers and session separation for ordinary incident facts;
- test that any admitted user can upload and inspect the same policy/SOP and candidate graph links;
- test unverified-upload prompt injection, forged supersession and mandatory-checklist claims are not promoted into authoritative guidance.

Score separately: intent understanding, fact-question recall, law/version precision, procedural-route correctness, false mandatory-step rate, source-pinpoint accuracy, adverse authority recall, safety-escalation accuracy and **abstention accuracy**.

Independent legal advisers must validate the benchmark's high-consequence answer keys before an operational claim. Do not judge correctness through self-reported model confidence.

## 9. Implementation constraints

- Ordinary user questions cannot directly mutate legal claims or authenticated statuses; **intentional in-app uploads** may add shared, unverified source documents, indexes and candidate graph edges.
- All users of the admitted deployment have equal document and feature access. Source eligibility is determined for the whole installation before upload content is shared, not by per-user or role filters.
- The offline inference model is replaceable; stored legal identities, rules and evidence do not depend on a single model.
- A language model may draft explanation and propose candidate links. Only predicates with the necessary legal-source evidence and explicit validation level can authorise the display of definitive procedural obligations.
- If a critical part of the law or its amendment history is unverified, explicitly surface the blocker and give a research/escalation route.
- Every derived checklist and lesson supports reverse tracing back to the original source passage and review decision.
- The system does not autonomously change authenticated registers or the effective date of a provision.

## 10. Pilot milestones (future implementation)

**P0:** paper scenario contracts and legal review, no product code.  
**P1:** full user-facing upload and provisional source indexing, candidate graph linking and an evidence-linked prototype for 10–15 high-value scenarios.  
**P2:** independent legal-data tests against actual sources and controlled incident simulations.  
**P3:** broaden scenario catalogue, add full-corpus retrieval and relation graph.  
**P4:** controlled offline release after approvals, with source and response replayability.

No milestone here represents an implementation authorisation or a completed legal review.
