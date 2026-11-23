# D8. Cycle 5 readiness report

**This cycle built the source base without downloading anything, and the most important gap remains: no official copy of the Regulations for the Army is publicly reachable.**

- **What exists now:** a deduplicated, hash-backed inventory of 112 sources, a ranked acquisition plan of 22 items in five batches, and a source-to-record crosswalk covering all 658 KB records and 53 cases.
- **What the coverage shows:** 618 of the 658 KB records have no exact anchor in a held, provenance-documented primary source.
- **What would change that:** almost all of it is fixable through public Gazette facsimiles and DESW PDFs, once downloads are approved.

## Completed
| Phase | Result |
| --- | --- |
| 1. Baseline | Staging `151f9358`. Originals unchanged: records_658 `9a8f0d19…cfc1`, cases_53 `8b8d53cd…f89a`. 93 held binary paths (67 unique) re-hashed MATCH. 147 earlier registers indexed by sha256. Six open PRs recorded; none touched. |
| 2. DSR discovery | D2. RA 1987 full text NOT_FOUND in the official public sources checked; only the Ch.V extract is held. RA 1962 is evidenced by citation only. The "RA 2008" mentions are a substring artefact. RMSAF, Air Force and Navy regulations located. |
| 3. Wider discovery | 86 candidates across three groups, all requests logged. Gazette facsimiles located for the Army Act as enacted, the AFT Act, BNSS, BSA, BNS, their commencement notifications, and 10 post-2022 S.R.O. candidates. DESW copies located for PRA 2008 I/II, ER 2008 (two files) and ER/GMO 2023. |
| 4. Amendment mapping | D4: 87 instrument rows, 154 provision-chain rows and 212 Army Rules provision-location rows, all carried verbatim with origin ids. Chain status: Army Act PARTIAL; Army Rules, RA, PRA and ER `PARTIAL/NOT_CHECKED (AMENDMENT_CHAIN_INCOMPLETE)`. |
| 5. Acquisition preparation | D3: 22 items in five batches, all NOT_APPROVED, with integrity pins where metadata allowed. |
| 6. Mapping and QA | D6 crosswalk. Builder is deterministic (`--check`), plus validator `check_c5.py` and 12 unit tests. Existing gates pass: 305 tests, PILOT-01/R23 strict, check_csv, check_provenance (no new violations), ARMY-RULES check_registers, WS-D checks. |
| 7. Review | D7: 1 P1, 5 P2 and 12 P3 findings, all dispositioned. One documentary disagreement stays open. |

## Unresolved source gaps (exact)
1. **Regulations for the Army 1987** (complete, with amendment slips) and **RA 1962**: no public location found (C5-ACQ-12/13).
2. **Gazette texts not held** (located on archive.org, pinned):
   - Army Act 1950 as enacted;
   - AFT Act 2007;
   - BNSS, BSA and BNS 2023;
   - the 2024 commencement notifications (C5-ACQ-01..05, 20).
3. **Army Rules after 06-06-2022:** 10 candidate S.R.O.s to read (C5-ACQ-06). Hint-only and gap instruments from ARMY-RULES-CHAIN-01 also remain.
4. **Pension:**
   - not held but located: PRA 2008 I/II, ER 2008 and GMO-2023;
   - NOT_FOUND: PRA 1961, ER 1982 and GMO 2002/2008.
5. **Territorial Army:** the Act was NOT_CHECKED because India Code was blocked; the Rules and Regulations were NOT_FOUND officially.
6. **Other instruments:**
   - **NOT_FOUND:** pay rules 2017 and the Army Orders actually cited.
   - **NOT_CHECKED:** CCCM Rules 1978 and S.O. 4010/1986; AFT Procedure Rules 2008/2011; ISO Act and Rules; Army Act s.4/s.9 notifications; IPC/CrPC/IEA historical texts.
7. **Provenance gap:** 34 held official copies (26 publications, 8 SC judgments) have no source-authentication register row, so they count only as partial anchors.

## Blockers
- **No public copy of RA, RMSAF or the Army Orders.** These need a custodian route, which is an owner decision. Their access marking is unknown, and the sibling RAF reprint is reported as FOUO.
- **Hosts unreachable from this environment:** India Code, egazette (TLS), pcdapension and cgda, indianarmy.nic.in. Discovery must be retried from the crawl machine.
- **DESW Compendium e-book links are broken (404).**
- **Downloads and crawler runs need owner approval.**

## Approvals required (none is implied by this package)
| Approval | Scope |
| --- | --- |
| A-C5-1 | Batch A download (archive.org Gazette facsimiles; pinned md5 and size), with its crawler-config PR kept separate from #7/#8/#17/#23 |
| A-C5-2 | Batch B download (DESW), extending the DESW allow-list beyond PR #9 |
| A-C5-3 | Custodian route for RA 1987/1962, RMSAF and specific AOs, plus a decision on handling any access marking |
| A-C5-4 | Batches D and E (historical; comparators with a marking review) |
| A-C5-5 | Retry discovery from the crawl machine (read-only, logged) |
| Legal | The 13 C4 adviser topics, SC4-01 and the reserved items. The ER 2023 effective-date clause is now documented, but the trigger-date question (LAQ-03) is still for the adviser. |

## Recommended next technical tasks (in order)
1. **After A-C5-1:** fetch batch A, verify the pins, and add source-authentication register rows with page-image checks of identity pages. Then index Army Act sections from the as-enacted Gazette into the provision register, alongside the 212 Army Rules rows.
2. **Read the 10 post-2022 S.R.O.s**, then update ARMY-RULES-CHAIN-01 through a reviewed addendum, not an in-place edit.
3. **Write source-authentication register rows for the 34 held official copies.** Retrieval evidence is in the earlier-cycle source JSONs, and no download is needed. This lifts 7 case records and many KB items from partial to exact.
4. **After A-C5-2:** fetch batch B, compare the two ER 2008 files (C5-CF-C5-02) and the two ER 2023 files (C5-CF-C5-03), and build the PRA 2008 amendment chain by paging the full DESW circular archive.
5. **Retry discovery** (A-C5-5) for India Code (Army Act amending Acts, TA Act, DPP Act, AFT Procedure Rules), egazette (pay rules, TA Rules, RA references) and pcdapension (ER 1982, PRA 1961).
6. **Re-run the D6 crosswalk** after each batch. It rebuilds deterministically.

## Success criteria (self-assessment; technical, not legal)
| # | Criterion | State |
| --- | --- | --- |
| 1 | DSR inventory with limitations documented | Met (D2): the inventory is complete for what is discoverable, and the limits are explicit |
| 2 | Historical vs current distinguished | Met: `currency_status`, and no currency claim anywhere |
| 3 | Acquired documents have provenance and integrity | No new acquisitions. All held files re-hashed; provenance gaps listed. |
| 4 | Missing material identified exactly | Met, with NOT_FOUND / NOT_CHECKED kept separate |
| 5 | Cross-references traceable | Partly met: provision-level for the Army Rules (location) and amendment chains; Army Act sections not yet indexed |
| 6 | Original hashes unchanged | Met |
| 7 | Conflicts keep explicit status | Met: reserved states verified by the validator and the reviewer |
| 8 | Technical checks pass | Met |
| 9 | Review findings incorporated or preserved | Met (D7) |
| 10 | Executable consolidation plan | Met (D3 + above) |

No record is legally approved because it passed technical validation.
