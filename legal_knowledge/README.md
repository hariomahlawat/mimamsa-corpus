# Curated Military Law database: research and verification layer

This directory is a **separate, unapproved research layer**, not an authenticated legal source and not a replacement for the existing crawler outputs.

## Contents
- `reconciliation/v2.3/`: 658-knowledge-record reconciliation queue, 53 curated cases, 81 propositions, uploaded-manual inventory, provenance risks. Matches to the Hugging Face corpus are still **pending**, not confirmed absent.
- `verification_batches/v2.5/`: 22 narrowly compared propositions for Army Rules 22, 23, 180 and 182; 80 proposed knowledge-base links; source-page anchors and discrepancy register.

## Critical quality controls
1. No claims are JAG-approved. No proposition has passed exhaustive amendment and judicial treatment verification.
2. Provisional links are not precedents, and text agreement is not proof of current legal force.
3. MML manual uploads are **not included** here pending copyright/access-marking, edition and transcription review.
4. Existing Mimamsa `data/`, `schema/` and raw source files are unchanged.
5. The updated `scripts/push_hf.py` uploads this folder additively as `legal_knowledge/` in the private Hugging Face dataset. It does not replace any crawler data.

## Deployment
Merge the review branch after checking the CSVs and then run the existing checkpoint script on a machine with the corpus checkout, crawl database and a write-authorised Hugging Face login:

```sh
python scripts/push_hf.py "curated legal review v2.5"
```

**Caution:** The existing checkpoint script also regenerates manifests and synchronises regular corpus folders; it must be run from the intern's complete local corpus workspace, not a source-code-only clone.

## Future work
Bring in the complete v0.9 source records, claim-level source passage checks, official amendment gazettes, authenticated judgments and MML commentary under their own provenance and licensing reviews before publishing any verified-release dataset.
