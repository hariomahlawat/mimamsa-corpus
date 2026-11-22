# Mandatory evidence and legal-accuracy standard

**We classify data by evidentiary and review quality, not by whether a human or AI created it.** The same checks apply to all contributions.

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
- Army Rules 1954 Rule 23(3): disputed negation between government-hosted compilations and manual extracts; obtain authoritative original S.R.O. 484 of 27 Nov 1954 and necessary amendments before resolving. No autonomous correction.
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

## Source hierarchy for conflicts (owner rule, 2026-11-22)
See `SOURCE_HIERARCHY.md` (binding). In summary:
- For each conflicting document, determine its authority, provenance, applicable date and amendment history.
- Prefer the authenticated original instrument over later transcriptions or compilations.
- Government-issued manuals outweigh third-party commentary but never override Acts, Rules, amendments or binding judgments.
- An archival reproduction of an official Gazette is evaluated as a copy of a primary document (class `ARCHIVAL_COPY_OF_OFFICIAL`, with custody checks), not as commentary because of its host.
