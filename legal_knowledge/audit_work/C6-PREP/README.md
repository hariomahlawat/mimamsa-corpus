# C6-02 to C6-05: preparation packages (Cycle 6)

**Status:** prepared only. Nothing is downloaded, no correspondence is sent, and no legal determination is made. Each package needs the owner approval named in it.

`tools/build_prep.py` builds the registers. It needs the crawler PR commits locally for the overlap check (it reads them with `git show`; the PRs are not modified).

| Package | Register | Content |
| --- | --- | --- |
| **C6-02** Public Gazette acquisition (Batch A) | `registers/c6_02_batch_a_files.csv` | 20 archive.org files. 18 are pinned (md5 and bytes from archive.org metadata); the two DPP Amendment Act 2000 items are not pinned: a guarded metadata attempt on 2026-11-23 was refused fail-closed (`discovery/c6_02_metadata_requests_v2.tsv`), and pinning them needs owner decision C6-02-D1. Identity is metadata only (content not examined). **None is configured in PR #8, #17 or #23.** Prerequisites, rights and post-download validation are recorded per row. Approval A-C5-1. |
| **C6-03** Pension and entitlement (DESW) | `registers/c6_03_desw_package.csv` | Covers PRA 2008 Parts I and II, ER 2008 (two non-identical files), the complete ER/GMO 2023 file and the amending circulars. Only the ER/GMO 2023 URL is in the PR #9 allow-list, which is draft and not authorised; the others need an allow-list extension. desw.gov.in robots returned 403 in Cycle 5, so the fail-closed rule applies until a readable policy is established. **The held incomplete ER-2023 copy (sha256 `29f6fa2c…`) is kept separately identified.** Approval A-C5-2. |
| **C6-04** DSR custodian route | `registers/c6_04_custodian_request_inventory.csv` | Requests: RA 1987 Vol I, Vol II and its amendment and correction slips; RA 1962; RMSAF 2010 and 1983; AO 45/2001 (the only specific Army Order number found in the 658 records, at ADM-014); the Army Orders that 10 records cite by category (the owner must identify these first); and the new **D&V Staff Officers' Handbook (May 2014)** lead with AO 13/2006/PS (`inputs/c6_04_discovery_candidates.csv`: the Scribd upload was not opened; its reported references are unverified extraction candidates). Access marking is UNKNOWN; custody requirements are stated. **No correspondence has been sent. The archived CDA copies have not been examined** (owner decision, C5-ACQ-26). |
| **C6-05** Legal-adviser evidence pack | `registers/c6_05_adviser_pack_status.json` | Unchanged: 13 adviser topics, 29 calibration escalations, 9 reserved items and 13 open WS-B inconsistencies. Reserved states: r.23(3) CONFLICTING, r.182 SC4-01 OPEN, r.193 OPEN, r.194 PROPOSAL. **0 determinations.** The full pointer index is `SOURCE-LIBRARY-C5/registers/legal_adviser_evidence_index.csv`. |

**Readiness summary and approvals:** `reports/C6-02_TO_C6-05_READINESS.md`.
