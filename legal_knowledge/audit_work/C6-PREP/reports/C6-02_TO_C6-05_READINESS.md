# C6-02 to C6-05 readiness (prepared; nothing downloaded, no correspondence)

## C6-02 Public Gazette acquisition (Batch A)
| Item | State |
| --- | --- |
| Files | 20 archive.org files: the Army Act 1950 as enacted, the AFT Act 2007, BNSS/BSA/BNS 2023, three 2024 commencement notifications, 10 possible Army Rules S.R.O.s (subject **not** confirmed) and 2 DPP Amendment Act 2000 items (`registers/c6_02_batch_a_files.csv`) |
| Integrity pins | **18 of 20** pinned (md5 + bytes, from archive.org metadata recorded in Cycle 5). **The 2 DPP Amendment Act 2000 items remain NOT_PINNED.** On 2026-11-23 the guarded runner tried the item metadata. archive.org `/metadata/<id>` answers HEAD with 405, and the data-node `_files.xml` HEAD has no content type. Both were refused fail-closed, and no GET was made (`discovery/c6_02_metadata_requests_v2.tsv`, 14 requests and decisions, 0 log errors). The policy was not overridden. |
| Identity | metadata only: archive.org title, date and the description's Ministry/Subject. Content is not examined. For the 10 S.R.O. candidates the subject is not confirmed |
| Overlap with PRs #8, #17, #23 | none: every row reads `NOT_CONFIGURED_IN_PR_STACK` (checked against the PR heads 1b948727, b8ee3176, 60715342) |
| Crawler security dependencies | PR #7 (aftjabalpur block) is the base of the stack and is unmerged. Staging `config/sources.yaml` lists `archive.org` only, but downloads redirect to `dn*.archive.org` data nodes. PR #8 adds `*.archive.org`, so a Batch A config PR must stack on #8. The discovery guard (fail-closed robots, payload classification) is **not** in the crawler (proposal C5-CRAWL-01). The India Code robots exception does not apply to archive.org and is not changed. |
| Exact hosts | `archive.org` (robots RULES_PARSED on 2026-11-23); `*.archive.org` data nodes (robots 404 = NO_ROBOTS_FILE). HTTPS only |
| Verification after download | sha256 recorded; md5 + bytes equal the pin; `%PDF` signature; page count; masthead page-image check with render hash (issue no., date, Part/Section, S.R.O. no.); then a reviewed source-authentication addendum entry |
| Rights and access | Government of India Gazette. The archive.org carrier is recorded as THIRD_PARTY_ARCHIVAL_FACSIMILE. Kept in a private store until the owner decides on redistribution. No access marking is expected on Gazettes; record any marking seen |
| Approval needed | **A-C5-1** (download), plus **C6-02-D1**: how to pin the two DPP items. Either (a) an owner-approved narrow rule allowing GET of `https://archive.org/metadata/<id>` JSON without a 200 HEAD, with all body gates kept; or (b) acquire them unpinned, with the pin taken from metadata after download. Option (a) is recommended. |

## C6-03 DESW pension sources
| Item | State |
| --- | --- |
| Targets | PRA 2008 Parts I and II; Entitlement Rules 2008 (two non-identical files); the complete ER 2023 + GMO 2023 file; amending circulars (`registers/c6_03_desw_package.csv`) |
| Held incomplete copy | sha256 `29f6fa2c…` (13 MB, 35 pages; ER 2023 Appendix-I without GMO 2023) stays separately identified. It is to be compared page by page with the complete file after download |
| Allow-list | only the ER/GMO 2023 file is in draft PR #9 (not authorised). The others need an allow-list extension in a separate config PR |
| Robots blocker | desw.gov.in robots.txt returned 403 in Cycle 5. Under the fail-closed rule, no automated request may be made until a readable policy is established or the owner records a decision. **No bypass.** |
| Approval needed | **A-C5-2**, the allow-list extension, and a decision on the robots blocker. Options: a later successful robots read, or a manual owner-side retrieval with the sha256 recorded |

## C6-04 DSR, procedural publications and the D&V handbook lead
| Request | State |
| --- | --- |
| RA 1987 Vols I and II, amendment and correction slips, RA 1962, RMSAF 2010 and 1983, AO 45/2001, Army Orders cited by category | prepared (`registers/c6_04_custodian_request_inventory.csv`). Access marking unknown. **No correspondence sent.** Archived CDA copies not examined (C5-ACQ-26) |
| **New: D&V Staff Officers' Handbook (May 2014)** | discovery lead `DV-SOH-2014` and custodian request rows `DV-SOH-2014` and `AO-13-2006-PS` (`inputs/c6_04_discovery_candidates.csv`) |

**D&V handbook: what is and is not established**
- **Known:** a third-party Scribd upload exists (document 733107547). It was **not opened or downloaded**: the title, issuer, date and references come from the owner brief.
- **Not established:** authenticity, completeness, currency and redistribution rights.
- **Not to be done:** import the text into the verified corpus, download it or redistribute it.
- **Reported references.** These are extraction candidates only, to be checked against an authorised copy and the original instruments: Army Act ss.26, 27 and 164; RA 1987 paras 364, 365 and 368; AO 13/2006/PS; D&V policy letters.
- **Guidance versus authority.** The handbook is staff guidance. The governing authority is the Army Act and the regulations and orders it cites. RA 1987 is not held, so the RA paragraph citations cannot be checked now. Internal policy letters are outside the public-document scope in CLAUDE.md, so the owner decides whether they are in scope.
- **Custodian question.** Can the issuing directorate (Addl DG D&V, AG's Branch) supply an authorised copy, and what is its access marking?
- **Future task:** once a permitted copy is held, inventory every regulation, order, instruction and policy letter it cites, tagged guidance or authority.

**Approval needed:** **A-C5-3**, covering the custodian route, the request text, the handling of access markings and the CDA archived copies. A further decision is needed on whether internal D&V policy letters are in scope.

## C6-05 Legal-adviser evidence pack
Unchanged: 13 topics, 29 escalations, 9 reserved items, 13 open WS-B inconsistencies and 0 determinations. Reserved states are preserved: r.23(3) CONFLICTING; r.182 SC4-01 OPEN; r.193 C-08 OPEN; r.194 C-09 PROPOSAL.

**C6-01 contributions** are documentary only:
- 7 SC judgments would gain documented provenance, which changes evidence availability, not holdings.
- The TRA 2026 identity page is image-checked. It shows s.1(2): commencement by notification, so commencement must be evidenced separately.
- Act 13/1975 masthead discrepancy: Hindi No.16, English No.15.

No agent may promote a legal conclusion.
