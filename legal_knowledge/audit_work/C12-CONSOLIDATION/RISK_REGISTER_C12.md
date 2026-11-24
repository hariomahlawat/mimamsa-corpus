# Cycle 12 risk register (closeout, 2026-11-24)

| ID | Risk | Status | Evidence / next action |
| --- | --- | --- | --- |
| R-01 | Loss of the 48 working-store-only source copies | **CLOSED** (primary) | Preserved to HF `5524c3d9` and byte-verified (`preservation/`, `copy_verification_c12/`). Temporary copies kept until a **second persistent backup** is verified; that is still open, pending the owner (see R-02). |
| R-02 | Single persistent copy of the corpus: HF is the only verified store | **OPEN** | The owner holds the ZIP of the 48 (SHA-256 `214f11e8…`), but its storage has not been verified. A second verified backup of the whole corpus is needed: an owner-chosen store, then a verified restore. |
| R-03 | Availability and integrity risk for the 274 citation items that depend on those copies | **CLOSED** (availability/integrity only) | `copy_verification_c12/PRESERVATION_RISK_CLOSURE_C12.csv`. Evidence classifications unchanged. |
| R-04 | A sync deletes or overwrites HF-only or preserved files | **CLOSED** (after review R50-01: `legal_knowledge/judgment_sources/` added; a test checks that all 4,103 manifest paths are protected; the guard fails closed on missing repo/revision; listing and commit are pinned to one parent commit) | `scripts/push_hf.py` no longer passes `delete_patterns`. `scripts/hf_protect.py` stops the sync if a protected file would be overwritten. Covered by tests and a mutation check. |
| R-05 | Unverified HF corpus bytes | **CLOSED** | All 15,971 files byte-verified at `5524c3d9`. The 55 later additions were verified at `15bd03cc`. |
| R-06 | FOUO-marked RAF 2000 copy (`4284820e…`) held in the private HF dataset | **OPEN – owner decision** | Not published. Quarantine or removal needs owner approval. |
| R-07 | Truncated or incomplete judgment files | **OPEN** | 19 files are truncated at every known source. The 4 SC files are now complete. 22 have a truncated signature tail, but the judgment pages are present. |
| R-08 | Garbled P&H text layers caused relevant judgments to be dropped as irrelevant | **OPEN** | Found during ingestion: 12 P&H writs needed page-image reading. OCR and re-screening of the 562 P&H first-tier titles are planned for Cycle 13. |
| R-09 | Use of unverified legal knowledge in operation | **CONTROLLED** | `RESEARCH_USE_RESTRICTIONS.md` and `CAPABILITY_RESTRICTIONS.csv` (test-enforced). AUTH-LEDGER at version 0. |
| R-10 | Licensing: PyMuPDF is AGPL | **OPEN – owner decision** | Flagged in `docs/planning/OFFLINE_APP_TECHNOLOGY_ASSESSMENT.md`, for the app stack. |
| R-11 | Credential exposure | **CONTROLLED** | Fine-grained token held as a network secret limited to `huggingface.co`. Its value is never seen or logged. Retained by owner direction. |
