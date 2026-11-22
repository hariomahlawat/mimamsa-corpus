# Source acquisition work order (prioritised), PILOT-01 final controls

**DATABASE ONLY. Status: PREPARED, NOT EXECUTED.** Discovery was read-only. Nothing was ingested into `data/`, no correspondence was sent, and no legal finding changed status.
**Basis:** `registers/source_discovery_2026-11-22.csv` (36 rows), `ACQUISITION_PLAN.md`, `registers/amendment_source_gaps.csv`.
Execution needs owner approval for each work order (CLAUDE.md: ask before any real download run).

## Standing rules for every work order
1. Use the existing crawler (`crawler/`). Run `dry-run` first, at no more than 1 request every 2 seconds per host, with a descriptive User-Agent, and obey robots.txt. Fetch only allow-listed hosts.
2. Store raw bytes under `data/raw/<source>/<yyyy>/<sha256>.<ext>`. Record SHA-256, plus MD5 where the host publishes one (archive.org) or serves download-specific bytes (India Code scans).
3. Write a metadata record valid against `schema/document.schema.json`, with `source_url`, `retrieved_at`, `issue_date`, `effective_date` and `access_marking`. Mark the provenance class: OFFICIAL_ORIGINAL, OFFICIAL_COMPILATION or ARCHIVAL_SCAN_OF_OFFICIAL.
4. Check the operative provision(s) against a page image (render SHA-256 recorded in `page_image_checks.csv`) before any audit finding cites the item.
5. **Archival reproductions of an official Gazette (e.g. archive.org / Public.Resource.Org scans) are evaluated as copies of the primary instrument** (owner rule 2026-11-22; `docs/legal-audit/SOURCE_HIERARCHY.md`), class `ARCHIVAL_COPY_OF_OFFICIAL`. With custody checks recorded (identity read from the image, checksum against the host value, completeness), they may support SOURCE_VERIFIED for what the Gazette prints. A custodian-certified copy is still sought where obtainable and prevails if the two differ. *(Revised 2026-11-22; the earlier wording treated such scans as needing an advisor evidence-tier decision.)*
6. After acquisition, run a delta review of only the affected PILOT-01 findings. No finding is promoted to approved.

## Priority 1: Army Rules 1954 Gazette notifications
| WO | Item | Discovered location (class) | Steps | Closes / feeds | Blocker |
| --- | --- | --- | --- | --- | --- |
| WO-1.1 | **S.R.O. 484, 27-11-1954** (Gazette No.47, Pt II s.4, pp.291–378) | archive.org `in.gazette.central.w.1954-11-27.103686` (ARCHIVAL_SCAN_OF_OFFICIAL). Verified: MD5 matches archive.org; masthead p.291 and r.23(3) p.300 image-checked (PIC-10/11; reads **"not obliged"**) | Ingest via the `archive` source. Independent second reading of p.300. Advisor decision on evidence tier. In parallel, the custodian request for a certified copy (draft, **not sent**; owner to send) | UQ-01 / F-STAT-001, F-STAT-020, F-XVOL-001/002, MMLPKT-02: evidence only, **dispute stays CONFLICTING** until gates are met | Owner approval; advisor evidence-tier decision |
| WO-1.2 | Amending S.R.O.s 34/1963, 116/1965, **215/1965 (r.192 proviso)**, 188/1979, 216/1988, 17(E)/1993, 8(E)/2003, 17(E)/2019, 6(E)/2022 | archive.org Gazette items (ARCHIVAL_SCAN_OF_OFFICIAL); identifiers in discovery rows T1-02 to T1-11 | Ingest. **Read each for any change to r.23**, so the amendment chain is complete. Check SRO 215 for the r.192 proviso (F-REM-001), SRO 8(E)/2003 for r.177 (F-PROC-018), and SRO 17(E)/1993 for r.22, 25 and 182 | Amendment chain for r.22/23/25/177/180/182/192; MMLPKT-01/03/04/05 BLOCKED findings | Owner approval |
| WO-1.3 | S.R.O. 258, 27-11-2002 | **Not found** on archive.org (no Nov–Dec 2002 Pt II s.4 items) | egazette search from an Indian network; or the custodian request (para 3) | r.22 Explanation (MML version difference) | egazette unreachable |
| WO-1.4 | Consolidated Army Rules on dmamod.gov.in | Same byte size as the India Code copy (OFFICIAL_COMPILATION) | Hash-compare with the corpus copy 48f52219…; add dmamod.gov.in to the allow-list only if approved | Confirms the compilation lineage | Allow-list change approval |

## Priority 2: Regulations for the Army
| WO | Item | Discovered location | Steps | Blocker |
| --- | --- | --- | --- | --- |
| WO-2.1 | Regulations for the Army 1987 (Revised Edition), **extract only: Chapter V, paras 201–220** | India Code item a1465f87-b991-407d-a2f9-c907db530fb8 (OFFICIAL_COMPILATION; no marking printed) | Ingest via the India Code source; record it as a partial document | Owner approval |
| WO-2.2 | **Full** Regulations for the Army 1987 and later corrections | Not on India Code or dmamod.gov.in; no official statement of access marking found | **Owner to supply an official copy** and state its access marking (e.g. FOUO) before ingest. If restricted, store it under the same controls as the MML (private; derived text not committed) | Owner action; access-marking decision |
| WO-2.3 | Regulations for the Army in India 1927 (historical) | archive.org `in.ernet.dli.2015.548585` (ARCHIVAL_SCAN) | Historical layer only; tag as superseded | Low priority |

## Priority 3: Entitlement Rules and Guide to Medical Officers
| WO | Item | Discovered location | Steps | Blocker |
| --- | --- | --- | --- | --- |
| WO-3.1 | **Entitlement Rules 2023 and GMO 2023** (MoD letter 21-09-2023) | desw.gov.in PDFs (OFFICIAL_ORIGINAL). Cover letter confirmed in a 13 MB scan (SHA-256 29f6fa2c…) | Add desw.gov.in to the allow-list (approval); ingest both; page-image check of commencement and applicability clauses | Allow-list approval |
| WO-3.2 | Entitlement Rules 1982, Entitlement Rules 2008, GMO 2008 | **Not found** on reachable hosts; pcdapension and cgda time out | Indian-network run against PCDA(P)/CGDA circular archives; or official copies annexed to SC judgments (e.g. Isaac 2026 cites them); or an owner-supplied copy | Network |

## Priority 4: AFT judgments
| WO | Item | Discovered location | Steps | Blocker |
| --- | --- | --- | --- | --- |
| WO-4.1 | AFT Principal Bench and regional bench judgments | aftdelhi.nic.in (joodb listing), aftkolkata.nic.in, aftlko.up.nic.in and others: **all time out** from this container. `crawler/aft.py` is ready (expects joodb rows with a ViewPDF link, "Results a–b of c", `limit=0`; table listings elsewhere) | Owner runs `discover --source aft --only <bench> --record <dir>` from an Indian network, then `dry-run`, then a by-month fetch; or supplies the request log noted in PROGRESS.md | Network |
| WO-4.2 | **Security fix:** remove `aftjabalpur.in` from `config/sources.yaml` (`aft.allowed_hosts`) | The host now serves a betting site | Owner-approved config change in a separate crawler PR (not part of the audit PR) | Owner approval |

## Priority 5: Jurisdiction rules (CIV-033 BLOCKED, CIV-008)
| WO | Item | Discovered location | Steps |
| --- | --- | --- | --- |
| WO-5.1 | Criminal Courts and Court-martial (Adjustment of Jurisdiction) Rules 1978: **S.O. 488 (MHA) of 09-02-1978**, Gazette 25-02-1978, Pt II s.3(ii), p.525 | archive.org `in.gazette.central.w.1978-02-25.48290` (ARCHIVAL_SCAN) | Ingest; image-check rr.3–9 |
| WO-5.2 | **S.O. 4010 dated 24-11-1986**, Gazette **06-12-1986**, pp.4881–82 | archive.org `in.gazette.central.w.1986-12-06.32435` | Ingest. **Register correction:** 06-12-1986 is the Gazette date; the notification date is 24-11-1986 (`amendment_source_gaps.csv` / ACQUISITION_PLAN item 6 to be read accordingly) |
| WO-5.3 | Post-BNSS rules (BNSS s.521/531) | Not found; egazette unreachable | Indian-network egazette search |

## Priority 6: Army Act amending Acts
| WO | Item | Location |
| --- | --- | --- |
| WO-6.1 | Act 19/1955 (Commanders-in-Chief (Change in Designation) Act) | Gazette scan: archive.org `in.gazette.e.1955.613`. The India Code copy lacks the amending Schedule |
| WO-6.2 | Act 13/1975 | India Code Gazette scan (downloaded for identity, SHA-256 8358d2b3…) |
| WO-6.3 | Acts 56/1974, 20/1983 | India Code records found, not opened |
| WO-6.4 | Act 37/1992 | Already located and image-checked (PIC-07) |

## Priority 7: other (from ACQUISITION_PLAN)
- BNS/BNSS/BSA commencement notifications (egazette).
- ISO Act 2023 (India Code) and Rules 2025 (egazette).
- Agniveer notifications (egazette / MoD).
- Missing judgments: N S Yadav 2019, Shri Kant Sharma 2015, Santosh Lohar (P&H HC 2023), Sundar 2023, Tarsem Singh 2008, L. Chandra Kumar 1997, Inder Jit Kumar 1997, Major A Hussain 1997. Most are reachable on api.sci.gov.in; Santosh Lohar is a P&H HC judgment (highcourtchd.gov.in reset).

## Execution sequence proposed (needs owner approval)
1. **Now, from this container:** WO-1.1, WO-1.2, WO-5.1, WO-5.2 and WO-6.1 (archive.org, already allow-listed); WO-2.1 and WO-6.2/6.3 (India Code); Priority 7 judgments (sci.gov.in).
2. **Allow-list approval, then this container:** WO-3.1 (desw.gov.in); WO-1.4 (dmamod.gov.in).
3. **Indian network / owner machine:** WO-1.3, WO-3.2, WO-4.1, WO-5.3 and the commencement notifications.
4. **Owner actions:** send the custodian request (WO-1.1, WO-1.3); supply the Regulations for the Army and state their marking (WO-2.2); approve the WO-4.2 security fix.
