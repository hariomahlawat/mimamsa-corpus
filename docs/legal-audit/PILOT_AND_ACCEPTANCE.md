# Database-only 25-record pilot and scale gate

## Sample: 25 UNIQUE actual v0.9 knowledge-base record IDs
Freeze original inputs and hashes before selecting; do NOT fabricate record identifiers. Suggested strata, adjust and log deviations based on actual record contents:
- 6 statute/rule interpretation records (amendments, commencement and repealed provisions)
- 5 disciplinary/administrative procedure records
- 5 judgment-linked propositions with later-treatment risk
- 4 high-consequence command/legal authority records
- 3 cross-volume conflict/duplicate-prone records
- 2 lower-risk control records

**MML is a priority source**: inventory all eight original MML files before picking the pilot. Target at least **12 of these 25 actual KB records** with a demonstrable specific MML passage/paragraph/page crosswalk, spread across the strata. If insufficient evidence supports 12, disclose the precise shortfall instead of inventing links. MML-only assertions remain manual-supported, not independently law-verified.

Overlap subject tags where necessary, never double-count IDs. Include breadth across nine volumes as the actual corpus permits. Separately audit any cited case rows from the existing 53-case repository without counting them as additional KB sample IDs. Retain the prior legal batches as *leads*, not authoritative conclusions.

## Flow
1. First-pass read-only inventory and hashes for ALL eight MML originals, edition/access-marking and DOC/PDF source-pair differences; mapping of manual passages to statutes and record IDs (owner approval)
2. Source and identity checks with statute/case/procedure agents; exact evidence links
3. Technical validation of JSON/JSONL and evidence
4. Independent reviewer checks critical issues and a blinded diverse sample
5. Legal advisor assesses every P0/P1, any disputed interpretation and risk-based controls
6. Compare against a human-adjudicated reference set: factual errors, missing issues, hallucinations, false positives, source identity defects and time spent
7. Owner GO/NO-GO for scaling to all 658. No auto-approval or app build.

## Required artefacts
`inventory.json`, `pilot-selection.json` (25 real IDs + seed/rationale), source evidence registry, `findings/*.json`, `reviews/*.json`, independent challenge report, advisor decisions, structural validation results, source access blockers, scorecard and signed/not-signed release decision. Version and hash all artifacts.

## Future-batch evidence policy
All new batches must set `source_authority_policy_version: v1` in their manifest, use separate `document_authority`, `carrier_provenance`, `copy_fidelity` and `amendment_chain_status` fields for every registered source, and pass strict validation. Historic PILOT-01 rows and manifests are frozen, not backfilled. Legal correctness and the operative amendment chain still require substantive verification and legal review.

## Release stopping criteria
**NO-GO** if any invented or non-existent source survives checking, any critical legal error would enter candidate guidance, unresolved P0 statutory/judicial conflict remains represented as resolved, source pinpoint traceability fails, schema/reference checks fail, or originals changed. Percentage thresholds for the remaining metrics must be fixed before scoring rather than chosen after seeing results.

## Metrics
Count examined, source-verified, partially verified, unverified, conflicting; confirmed P0-P3; false positives; detected omissions; primary-source coverage; later-treatment coverage; unverified source identity; unresolved legal-review queue; mean processing resources/time. Do not report a single legal accuracy percentage without a reviewed reference set.
