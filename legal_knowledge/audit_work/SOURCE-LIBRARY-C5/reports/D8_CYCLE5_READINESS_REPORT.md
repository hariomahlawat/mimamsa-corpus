# D8. Cycle 5 readiness report (including the C5 final corrections)

**Summary:** the source base was built and corrected without downloading anything.
- **What exists:** a deduplicated, hash-backed inventory of 112 sources with 67 copy-level records. A ranked plan of 26 acquisition items in six batches, all NOT_APPROVED. A source-to-record crosswalk covering all 658 KB records and 53 cases.
- **What the coverage shows:** 618 of the 658 KB records still have no exact anchor in a held copy with documented provenance.
- **The most important gap:** no complete official copy of the Regulations for the Army was located in the public sources successfully checked. Historical CDA-hosted leads exist, but they are leads only.

## Completed
| Phase | Result |
| --- | --- |
| 1. Baseline | Staging `151f9358`. Originals unchanged: records_658 `9a8f0d19…cfc1`, cases_53 `8b8d53cd…f89a`. 93 held binary paths (67 unique) re-hashed MATCH. 147 earlier registers indexed. |
| 2. DSR discovery | D2. RA 1987: LEAD_ONLY (CDA Guwahati / CDA Secunderabad historical file URLs for Vols I and II; current URLs 404 or unreachable). Only the Chapter V extract is held. RA 1962 is evidenced by citation only. "RA 2008" is a substring artefact. RMSAF: third-party copy only. |
| 3. Wider discovery | 92 candidates in four groups. A–C used v1 logs; D (corrections) used v2 fail-closed logs. Gazette facsimiles located for the Army Act as enacted, the AFT Act, BNSS, BSA and BNS, plus the commencement notifications and 10 post-2022 S.R.O. candidates. DESW copies of PRA 2008, ER 2008 and ER/GMO 2023 located. **TA Act, Rules and Regulations are OFFICIAL_CANDIDATE_LOCATED** on India Code from search-index evidence; direct verification BLOCKED_ACCESS. |
| 4. Amendment mapping | D4: 87 instrument rows, 154 provision-chain rows and 212 Army Rules provision-location rows. Chain status: Army Act PARTIAL; Army Rules, RA, PRA and ER `PARTIAL` / `NOT_CHECKED (AMENDMENT_CHAIN_INCOMPLETE)`. |
| 5. Acquisition preparation | D3: 26 items in batches A–F, all NOT_APPROVED. |
| 6. Mapping and QA | D6 crosswalk with copy-level eligibility. Builder is deterministic, plus validator and tests (see the PR for counts). |
| 7. Review | First independent review: 1 P1, 5 P2, 12 P3, all dispositioned (D7). The independent review of the final diff is recorded in `review/final_diff_review.md`. |

## Source authentication (derived, `coverage_summary.json`)
- **13 Cycle 4 register rows:** 12 documented-primary copies (5 Gazette + 7 official court copies) and 1 authentication-pending copy (Isaac, unchanged).
- **12 sources** hold a documented-primary copy. **54 held copies** have undocumented provenance.
- **No copy is custodian-authenticated.**

## Coverage (`coverage_summary.json`)
| Measure | EXACT_ANCHOR | PARTIAL_MATCH | MISSING_EVIDENCE |
| --- | --- | --- | --- |
| KB citation items (1,060) | 42 | 652 | 366 |
| Cases (53) | 6 | 7 | 40 |

**KB records:** 10 have all items exact, 30 some, and 618 none. These figures were unchanged by the copy-level model.

## Unresolved source gaps (exact)
1. **Regulations for the Army 1987** (complete, with amendment slips) and **RA 1962**:
   - custodian route (C5-ACQ-12/13);
   - archived CDA copies need an owner decision before examination (C5-ACQ-26).
2. **Gazette texts not held but located and pinned:**
   - Army Act 1950 as enacted;
   - AFT Act 2007;
   - BNSS, BSA and BNS;
   - the 2024 commencement notifications (C5-ACQ-01..05, 20).
3. **Army Rules after 06-06-2022:** 10 candidate S.R.O.s (C5-ACQ-06). Hint-only and gap instruments remain.
4. **Pension:**
   - located: PRA 2008 I/II, ER 2008 and the complete ER/GMO 2023 file;
   - not found in the sources checked: PRA 1961, ER 1982 and GMO 2002/2008.
5. **Territorial Army:** official candidates located for the Act, Rules and Regulations (Revised Edition 1976), but direct verification BLOCKED_ACCESS. The 2017 and 2023 amendments are not held.
6. **Other instruments:**
   - not found in the sources checked: pay rules 2017 and the specific Army Orders;
   - NOT_CHECKED: CCCM Rules 1978 and S.O. 4010/1986; AFT Procedure Rules; ISO Act and Rules; Army Act notifications; IPC/CrPC/IEA.
7. **Provenance gap:** 34 held official copies (26 publications or records, 8 SC judgments) have no register row.

## Blockers
- **Custodian-only material:** no public official copy of RA, RMSAF or the Army Orders was located in the sources checked. Their access marking is unknown.
- **Unreachable or robots-unreadable hosts (fail-closed):**
  - India Code (both hosts);
  - egazette.gov.in (TLS);
  - pcdapension and cgda;
  - indianarmy.nic.in;
  - cdasecbad.ap.nic.in;
  - web.archive.org.
- **India Code crawler exception:** the staging crawler config carries an owner-approved robots exception for India Code. It conflicts with the new fail-closed rule, so an owner decision is needed (DISCOVERY_SAFETY_POLICY §4).
- **Downloads and crawler runs need owner approval.**

## Approvals required (none implied by this package)
| Approval | Scope |
| --- | --- |
| A-C5-1 | Batch A download (archive.org Gazette facsimiles; pinned) |
| A-C5-2 | Batch B download (DESW; allow-list extension beyond PR #9) |
| A-C5-3 | Custodian route: RA 1987/1962, RMSAF, specific Army Orders; decision on archived CDA copies (C5-ACQ-26) and on any access marking |
| A-C5-4 | Batches D and E (historical; comparators with a marking review) |
| A-C5-5 | Discovery retries from a host where robots.txt is readable |
| A-C5-6 | Batch F (India Code TA files), after the robots policy is established or the owner rules on the India Code exception |
| CRAWL | Proposal C5-CRAWL-01: fail-closed robots handling and payload classification in the crawler (separate PR) |
| Legal | The C4 adviser topics, SC4-01, reserved items and the 29 calibration escalations (C6-05 pack). No legal determination is made here. |

## Next cycle
Work packages C6-01..C6-05 are specified in `reports/C6_WORK_PACKAGES.md`. They are prepared, not executed.

No record or source is legally approved by passing technical validation.
