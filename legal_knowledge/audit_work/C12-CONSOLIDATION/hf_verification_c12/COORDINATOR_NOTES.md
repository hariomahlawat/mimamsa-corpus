# HF verification: coordinator notes (not generated)

## Coordinator spot-check (independent of the verification author)
The coordinator re-downloaded 30 files at revision `5524c3d9`: 15 LFS and 15 non-LFS, drawn with the seeded sample `c12-owner-spotcheck`. Each was hashed independently. **30 of 30 match the ledger** on SHA-256 and size. `report --check` passes.

## Owner attention (no action taken)
- The FOUO-marked RAF 2000 copy `4284820e…` is already in the **private** HF dataset. This is not publication. Removing or quarantining it would be a deletion or visibility decision, which needs owner approval under `docs/governance/CORPUS_REPOSITORY_GOVERNANCE.md` §3.
- The 4 HF-only SC files open and end with `%%EOF`. They were retrieved to the session working store as candidates. Their HF copies remain the preserved originals.
