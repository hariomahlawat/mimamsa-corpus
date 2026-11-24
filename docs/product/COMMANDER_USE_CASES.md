# Commander use cases: plain-English military-law questions

**Recorded:** 2026-11-24  
**Status:** Product scenarios and benchmark seeds, **not approved legal advice or completed procedural SOPs**.  
**Relationship:** [Product vision](PRODUCT_VISION.md) and [Scenario engine](../architecture/SCENARIO_ADVISORY_ENGINE.md).

## 1. Purpose

A unit commander describes a **situation**, not a section number. This catalogue should help design data requirements, material-fact questions, search, conditional routes and tests. The legal result for each scenario must be derived separately from actual applicable Acts, Rules, Regulations, verified judgments and legal review.

## 2. Core examples supplied by the owner

### UC-01: Sepoy reportedly intoxicated on duty

**User utterances**
- “A sepoy was found drunk on duty. What to do?”
- “My jawan was drunk on sentry duty.”
- “He seems intoxicated while on guard. What is the procedure?”

**Intent:** Immediate safety, incident handling, potential offence, lawful disciplinary procedure.

**Urgent first response:** Check for immediate risk, safely relieve safety-sensitive duty where appropriate, obtain medical care if needed and preserve observations. These are provisional safety considerations, not a finding of intoxication or guilt.

**Material facts**
- Nature of duty: armed guard, sentry, operational, administrative, off duty?
- Timing and place; current condition and medical need?
- What behaviour was observed and by whom? Is evidence disputed?
- Person's service status and applicable procedure?
- Is a charge already framed? What procedural stage has been reached?
- Was there an incident or injury requiring another reporting route?

**Research required:** Applicable version of Army Act/Rules, procedural competence, evidentiary and medical safeguards, relevant judgments and adverse authority. The system must independently verify specific provisions and available procedure before naming them as definitive.

**Prohibited shortcut:** “Automatically punish under Section X.” Never equate suspected intoxication with proved guilt.

**Expected answer:** concise immediate considerations; sources and possible procedural route; facts/evidence checklist; relevant cases; authority/escalation and caveats.

### UC-02: JCO refuses to sign a charge-sheet

**User utterances**
- “The JCO won't sign the chargesheet.”
- “Accused refuses receipt. Can I proceed?”
- “Does refusing to sign invalidate the charge?”

**Intent:** Determine which document/signature, correct service/communication of charges and lawful procedure.

**Critical ambiguity:** Is the signature the commanding officer's signature on a formal charge-sheet, the accused's acknowledgment of receipt, a summary-of-evidence statement, or something else?

**Material facts**
- Exact document and who prepared it?
- Current stage (hearing of charge, summary of evidence, pre-trial service, trial etc.)?
- What was communicated/read/provided?
- What was actually refused? Is there contemporaneous evidence?
- Person's service category and relevant competent authority?

**Research required:** Exact requirements for that document and stage, including formal signing, service/notice, recording a refusal and associated safeguards, sourced to applicable Army Rules and judgments.

**Prohibited shortcut:** Inventing a witness-signing rule or stating that refusal is either an admission of guilt or automatically blocks proceedings.

**Expected answer:** identify ambiguity; give stage-appropriate checks; only then state an evidenced way forward; explain what cannot yet be determined.

### UC-03: Jawan reportedly contracted a second marriage

**User utterances**
- “A jawan has done second marriage. Which Act applies?”
- “My soldier married again while still married.”
- “Can the unit take action for plural marriage?”

**Intent:** Identify potentially applicable personal, criminal and service-law questions, without presuming the allegation is proved.

**Material facts**
- Was the first marriage legally subsisting when the second ceremony occurred?
- Dates and places of marriages, and governing personal/customary law as applicable?
- What evidence establishes each marriage and any dissolution/death?
- Was the second ceremony legally solemnised, and what is disputed?
- Which service regulations, permissions or exceptions applied on the relevant dates?
- Is there a complaint, investigation or already pending proceeding?

**Research required:** Verified applicable Regulation for the Army and its temporal status, relevant marriage/personal laws, criminal provisions applicable on the dates, proper administrative versus disciplinary routes, judicial interpretation and competent authorities.

**Prohibited shortcut:** Automatically assigning a generic Army Act charge or assuming bigamy/criminal liability from a reported relationship.

**Expected answer:** conditional law map, necessary facts and documents, authorised review route, legal uncertainty, relevant judgments and counsel/escalation where necessary.

## 3. Initial scenario families for expansion

| ID | Plain-language question | Primary unknowns or risk |
| --- | --- | --- |
| UC-04 | “A soldier has not returned from leave. What do I do?” | Absence duration, communication, status, statutory classification |
| UC-05 | “Someone disobeyed my order. Which procedure applies?” | Lawfulness of order, command context, evidence, service status |
| UC-06 | “A soldier refused a medical examination.” | Medical and procedural authority, consent/safeguards |
| UC-07 | “The witness has changed his statement.” | Stage, evidence record, procedural fairness |
| UC-08 | “A charge was wrongly worded. Can it be corrected?” | Stage and applicable amendment rules |
| UC-09 | “A person wants to submit a statutory complaint.” | Forum, limitation, competent channel, service status |
| UC-10 | “A civil police case is registered against a jawan.” | Civil-military jurisdiction, custody, duties to report |
| UC-11 | “A soldier has been arrested by civilian police.” | Competent authority, legal safeguards, notifications |
| UC-12 | “A soldier says he was denied opportunity to defend.” | Procedure and stage, natural justice, prejudice |
| UC-13 | “A witness isn't available for hearing.” | Applicable rules, admissibility, adjournment powers |
| UC-14 | “A jawan is asking for discharge on compassionate grounds.” | Eligibility, competent authority, service policy |
| UC-15 | “Disability pension was denied. What remedy is available?” | Service/medical history, entitlement rules, date, forums |
| UC-16 | “Court-martial proceedings are delayed. Is there a time limit?” | Limitation rules, offence and discovery dates, exceptions |
| UC-17 | “Is this summary punishment legally permissible?” | Rank, offence, legal competence, factual/procedural preconditions |
| UC-18 | “Can an accused obtain copies of documents?” | Stage, documents, applicable right and restrictions |
| UC-19 | “A soldier wants to withdraw a complaint.” | Complaint type, stage, applicable law |
| UC-20 | “A former soldier has challenged his discharge.” | Dates, remedy, forum, applicable regulations |
| UC-21 | “I have uploaded a new policy letter. Show the Rules and judgments it relates to.” | Publication date, issuer, source type, citations, source trust |
| UC-22 | “Does this new SOP replace an older SOP or contradict a Rule?” | Version authority, supersession evidence, temporal validity, competing interpretations |
| UC-23 | “We have scanned standing instructions. Add them to the searchable library.” | OCR quality, file safety, common access eligibility, provisional linking |

All cases are **research seeds**, not answers. Expand from corpus-derived recurring issues only after provenance and relevance checks.

### UC-21 to UC-23: User-uploaded policy/SOP material

An admitted app user may intentionally upload a policy, SOP, instruction, circular, scanned note or other eligible reference file. The app must explicitly explain that accepted uploads become visible to **every** app user. It automatically preserves the original, checks basic file safety and deployment-wide eligibility, extracts text/OCR, identifies document dates/issuer/version, and suggests connections to Acts, Rules, other policies and judgments. Search and graph discovery should become available after processing with `USER_UPLOADED_UNVERIFIED` status. An asserted `supersedes`, `mandatory procedure`, `legal exception` or `operative rule` is only a **candidate**, not an authoritative fact, until substantiated by source and applicable legal review. A restricted document not suitable for sharing with all admitted app users is not imported into the common corpus.

## 4. Required scenario record contract (design proposal)

Each reusable scenario should store:
- `scenario_id`, title, user utterances/aliases, version and review state;
- intent class and risk level; immediate-safety considerations, if any;
- `material_facts` with fact_id, question, why it matters, allowed/unknown values, priority and source where a legal condition is asserted;
- applicability predicates for dated provisions, rank/status, stage and jurisdiction;
- references to `ProvisionVersion`, `Judgment`, `LegalProposition` and `EvidenceAnchor`;
- action/checklist candidates, competent authority, safeguards, escalation and evidence status;
- conditions that must **block** a definitive answer;
- test variants where changing one fact changes the result;
- reviewer, revision and approval artefact (if any).
- optional linked uploaded-policy sources, origin, version, status and graph candidates, all explicitly distinguished from verified binding law;

Do not embed a fixed statutory section number in a scenario without a verified, date-aware binding to the source graph.

## 5. Response contract

A situation-based response should prefer this sequence:

1. **Immediate considerations** if delay creates an actual safety or welfare risk.
2. **What is established / what is alleged / what remains unknown.**
3. **Potentially applicable law and time period**, with exact source pinpoints.
4. **Stage- and authority-dependent route**, phrased conditionally until predicates are satisfied.
5. **Evidence and safeguard checklist**, each item sourced or clearly non-mandatory.
6. **Judgments and lessons** with direct/indirect relation and verification labels.
7. **Important uncertainty, contrary authority and JAG escalation.**
8. **One or two decisive follow-up questions**, when needed.

Offer a brief commander mode and an expandable detailed legal-research mode. Do not force a lengthy questionnaire when only one fact is material.

## 6. Benchmark and acceptance

The project brief `CLAUDE.md` already mentions a 50-question golden test set: **discover and reuse it rather than inventing its contents**. Develop a complementary commander benchmark with independently researched answer keys and holdout variants.

Tests must cover:
- paraphrases, misspellings, rank terms and Hinglish expressions;
- missing rank, date, document type or stage;
- older law versus new commencement, saving or amendment;
- facts with several valid routes, mixed proceedings or contradictory evidence;
- false-positive offence mapping, wrong competent authority and invented signatures;
- lack of authenticated source and conflicting historical wording;
- questions about a real person, kept in the active session rather than inadvertently entering shared search; intentional uploads are clearly shared;
- uploaded SOPs with incorrect effective dates, malicious instruction text, supersession claims or incompatible access markings;
- metamorphic cases: alter one fact and verify only legally justified changes;
- “not determinable from available evidence” as an expected correct answer.

Use measured precision and completeness, not mere LLM self-grading. Legal advisers must validate high-consequence answer keys before a scenario is deemed operationally approved.
