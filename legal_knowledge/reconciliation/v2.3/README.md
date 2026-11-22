# Mimamsa / Military Law Database Reconciliation v2.3

## Scope
Read-only, reproducible first-stage reconciliation of user-provided MML files, earlier 658-record curated KB and 53-case/81-proposition repository against Mimamsa's documented structure and latest PROGRESS.md.

## Limitations
The Hugging Face connector can read metadata but cannot fetch individual private dataset files or write with its current OAuth scopes. GitHub companion repository README, brief, schema and progress log were inspected. Full Hugging Face manifest and individual document records were not retrieved. Therefore NO exact case, statute or source-document matches against remote inventory are claimed. 'NOT_EVALUATED_ITEM_LEVEL' does not mean missing.

## Internal deduplication
02_Local_Duplicate_Candidates.csv shows approximate token-shingle overlap between uploaded copies, not bibliographic equality or exact-page equivalence. Document bytes have distinct checksums. Keep all originals.

## Data safety
No remote repository was changed. Do not upload unpublished/restricted manuals without permission review. No curated statement is approved merely by being in the source collection.

## Reconciliation workflow
1. Export Mimamsa data/manifest.csv and relevant data/meta/*.json including source_url, doc_id, sha256, court, dates and case numbers.
2. Match raw document SHA256; fallback to normalized title/edition and official URL; create candidate matches only.
3. For cases match bench, parties, decision date, case number and original judgment hash.
4. Map 658 curated KB records to one or more versioned statute sections and confirm applicability.
5. Keep manuals as commentary/historical references; separately check legislation text against official sources.
6. Review unmatched records and judge-authorized holdings before marking verified.

## Source materials
- User uploads: MML Part I, Army Act, Army Rules, Volume III in PDF and Word variants.
- Local files: Military_Law_Source_Claim_Reconstruction_v2.1; immutable 658 KB and 53 cases baseline.
- Private companion GitHub: hariomahlawat/mimamsa-corpus README.md, CLAUDE.md, PROGRESS.md, schema/document.schema.json, accessed 2026-11-22.