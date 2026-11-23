# D3. Prioritised acquisition register

**Register:** `registers/acquisition_register.csv`, with 26 items.
- `acq_c5_id` values are stable identifiers; `rank` is a separate ordering column.
- **Every item is NOT_APPROVED. Nothing has been downloaded.**

| Batch | Items (id: rank) | Source | Approval needed |
| --- | --- | --- | --- |
| **A: archive.org Gazette facsimiles** | C5-ACQ-01..06 (ranks 1–6): Army Act 1950 as enacted; AFT Act 2007; BNSS; BSA; the three Sanhita commencement notifications; 10 post-2022 MoD/DMA S.R.O. items. Also C5-ACQ-20 (BNS) and C5-ACQ-21 (DPP Amendment Act 2000). | archive.org; md5 and size pinned from the metadata API, except C5-ACQ-21, which still needs pinning | Owner download approval, plus a crawler-config PR kept separate from the #7/#8/#17/#23 stack. **Duplicates:** none of these is a configured download in PR #23. PR #23's acquisition matrix lists the Army Act Gazette (`in.gazette.e.1950.306`) as "Not configured (candidate located)". |
| **B: DESW official PDFs** | C5-ACQ-07..11: PRA 2008 Parts I and II; ER/GMO 2023 combined (49.9 MB); ER 2008 (two non-identical files); PRA/ER amending circulars | desw.gov.in over HTTPS; HEAD 200 with sizes recorded | Owner approval, and the DESW allow-list must be **extended beyond PR #9**, which covers ER/GMO 2023 only and is draft and unauthorised |
| **F: India Code, when reachable (new)** | C5-ACQ-23..25 (ranks 12–14): TA Act 1948; TA Rules 1948; TA Regulations 1948 (Revised Edition 1976) | official India Code URLs, identified via the search index of the official host (C5D-001..003). **Direct verification is BLOCKED_ACCESS**: robots.txt was unreadable, and the fail-closed rule applies. | India Code's robots policy must first be established, or an owner decision recorded (DISCOVERY_SAFETY_POLICY §4). Then download approval. |
| **C: custodian route (owner)** | C5-ACQ-12 (rank 15): RA 1987 complete with amendment slips. C5-ACQ-26 (rank 16, new): archived copies of the former CDA-hosted RA 1987 Vol I/II files. C5-ACQ-13..15: RA 1962; RMSAF 2010/1983; the Army Orders actually cited. | No complete official copy was located in the public sources successfully checked. CDA leads are LEAD_ONLY (D2 §1A). | Owner decision, including how to handle any access marking. Agents send no correspondence. |
| **D: historical archive.org** | C5-ACQ-16..19: RA in India 1927 (expected md5 recorded in the staging planning file `ACQ-01/proposed_archive_documents.yaml`; **not** in the PR #8 crawler config); RA India Part II 1940; Regulations for the Medical Services 1930; 1950 interim rules | archive.org | Owner download approval (phase 6) |
| **E: DMA comparators** | C5-ACQ-22: Regulations for the Air Force 1964 (reprint 2000); Navy Parts I–III; INAS 1973; Navy amendment regulations 2022/2024 | dmamod.gov.in | Owner approval **and a review of the marking** (the RAF reprint is reported as FOUO) |

## Discovery retries (read-only, logged in v2 format, under DISCOVERY_SAFETY_POLICY)
| Host | Purpose of retry |
| --- | --- |
| India Code (both hosts) | TA files; Army Act amending-Acts list; DPP Act; AFT Procedure Rules |
| egazette.gov.in (TLS chain failure; never bypassed) | — |
| pcdapension.nic.in and cgda.nic.in | — |
| indianarmy.nic.in | — |
| cdasecbad.ap.nic.in | — |
| DESW pension-circular archive | pages 4–33+ |
| DESW Compendium | links return 404, so this needs owner contact |

Each retry must run from a host where robots.txt is readable.

The existing PR chain (#7 → #8 → #17 → #23, with #9 stacked on #8) is untouched. This register **implies no approval** of any of those PRs.
