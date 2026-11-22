# Mandatory evidence and legal-accuracy standard

**We classify data by evidentiary and review quality, not by whether a human or AI created it.** The same checks apply to all contributions.

## Mandatory source-authority policy
Read and apply `docs/legal-audit/SOURCE_AUTHORITY_POLICY.md` to every new source and all conflicting legal assertions. **Priority is determined by the authority of the underlying instrument, not by the host domain.** An actual Government Gazette facsimile held on a third-party archive is a copy of primary legal material, not third-party commentary. Record its identity, original publication, image fidelity, copy provenance, amendments and reviewer checks separately. Authentic government-issued manuals are privileged practical references compared with third-party commentary, but not enacted law. Relevant binding judgments, later amendments, and date/jurisdiction controls remain decisive. **Do not classify a source as legally verified or current merely because a government or archival domain hosts it.** For all new batches, include `source_authority_policy_version: v1` in the audit manifest so strict validation requires separate authority/carrier/fidelity/amendment-chain fields on every evidence entry.

## Foundational MML manuals
The eight user-provided Manual of Military Law DOC/PDF originals are a mandatory first-pass **practical military reference** collection. Check all eight private HF files against their receipt/manifest, version/edition, legal date, paragraph/page concordance, text extraction and access markings. Identify exact manual-to-statute/KB/judgment references and review whether the manual is out of date. A manual is not binding law merely because unit commanders use it. A manual passage alone cannot establish current statutory correctness; use original statute/Rules/Gazette or controlling judgment as required. Preserve versions and note disputed Rule 23(3) source text rather than correcting it automatically.

## Authority and identity
1. Prefer original authenticated official Gazette or enactment for historical and current statutory text; inspect the amendment and commencement chain and operative date. Government-hosted consolidated copies may differ from original Gazette. Document the hierarchy, not an imagined resolution.
2. For cases use official signed/issued full decision PDFs or reliable official archives with court, bench, case number, decision date, parties, pages/paragraphs. A listing, counsel summary, report or office note cannot replace a judgment.
3. Store source URL/archival identity, accessed date, provenance category, SHA-256 if bytes archived, and exact pinpoint. SHA is byte integrity only, not legal authenticity, current status or correctness.
4. Distinguish extracted quotation, original-record claim, legal inference and reviewer proposal. Preserve quotation context, exceptions and adverse passages. No invented citations or reconstructed quotes.
5. Record temporal scope, service/person category, forum and jurisdiction. Historical applicability and transitional enactments must not be flattened into present-tense guidance.
6. Case treatment is *proposition-level*: overruled in part, limited, followed and distinguished must point to explicit later authority and relevant passage; absence of found treatment is NOT proof of no treatment.

## Explicit blockers
- Army Rules 1954 Rule 23(3): an uncertified archival facsimile of the 27 Nov 1954 S.R.O. 484 Gazette has now been located (printed p.300 reportedly says 'not obliged'), corroborating MML but conflicting with India Code's transcription. Classify as a Gazette facsimile with separate carrier provenance; complete the later Rule 23 amendment chain, independent page-image review and legal-advisor decision before resolving. No autonomous correction.
- Curated original notes and cases (658 + 53) remain research/unapproved.
- Evidence for any source/case crosswalk based on fuzzy title/year is *lead only*, never verified document identity.
- Unavailable official sources, conflicting texts, incomplete chain of amendments, unclear licensing/access marking, missing page locator or adverse precedents -> unresolved, escalate.

## Finding taxonomy
For each claim record: original record ID and location; exact existing text; allegation; problem type; severity; exact primary sources and contrary sources; temporal applicability; source identity and pinpoint; verified/unverified/conflict state; proposed wording (nullable); confidence limits; legal advisor questions; review status. A source register entry and supporting passages are mandatory for any `SOURCE_VERIFIED` claim.

## Review gates
- P0 critical: wrong jurisdiction/authority, coercive/disciplinary powers, custody, punishments, court-martial, formal remedies, serious misstatement or false citation.
- P1 high: likely wrong material doctrine or missing contrary precedent.
- P2 medium: omission, ambiguous cross-reference, incomplete metadata affecting retrieval.
- P3 low: editorial issues that do not affect legal substance.
- Source-verified is not legally approved. No reviewer or agent can mark formal JAG validation absent an attributable formal approval artifact.
- Any claim in high-consequence content with unresolved authority blocks candidate operational use.

## Security
Do not expose repository private content in public issues, logs or external AI tools without authorisation. Preserve original access marks. Do not circumvent site protection, paywalls, robots or certificates. Keep licensed or restricted full-text evidence in authorised private stores only.
