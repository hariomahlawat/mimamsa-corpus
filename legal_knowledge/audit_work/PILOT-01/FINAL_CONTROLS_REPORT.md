# PILOT-01 final controls: report and remaining blockers

**DATABASE ONLY. NO APPLICATION WORK.** 2026-11-22. No pull request merged; no calibration batch started; no correspondence sent; originals unchanged. No finding is advisor-approved or JAG-validated.

| # | Control | Result | Artifact |
| --- | --- | --- | --- |
| 1 | Complete citation-code inventory | **87 codes** actually used. The deterministic grammar covers structured objects, bracket tags, pipe/inline codes, leading digest codes and `sources` lists. 9 codes were missed earlier: SRC-RA, SRC-AO, AO, SRC-INDER, SRC-HUSSAIN, PPS, VISHAV, RANDHIR, VIRENDRA. 269 records use plain-text citations only; 2 records carry a `[VERIFY]` placeholder. On the complete denominator: **firm 72/87 = 82.8%; with co-citation 75/87 = 86.2%** (threshold 90% **not met**). Usage-weighted over 681 record-code links: firm 87.2%, inclusive 95.4% (information only) | `registers/source_code_resolution_v3.csv`, `source_code_coverage_v3.json`, `build_code_inventory.py` (exit 1 if any used code is missing from the register) |
| 2 | Independent review of F-REM-001/002 | Reviewer C, with its own retrievals, live re-fetch and page images. **F-REM-001 SUPPORTS** (P1; narrowed to "omits r.192, whose text conflicts"). **F-REM-002 SUPPORTS with one sub-claim disputed:** the vol 2(AA) note 6 also says criminal-court retrial is allowed (resting on omitted s.127), so my "tracks the section text" statement is withdrawn. Dispositions D-08/D-09 recorded; original findings unchanged | `reviews/independent-reviewer-C.json`, `sources/independent-reviewer-C.json`, `post_review/post_review_dispositions.csv` |
| 3 | Current validation artifact | **216 sources (209 + 7 reviewer C) / 126 findings / 35 reviews, 0 errors (strict, manifest, identity incl. per-reviewer exact `retrieved_by`)**; 34 tests OK. Historical `validation_result.json` (205/124/33) preserved unchanged | `validation_result_current.json`, `VALIDATION_INDEX.md` |
| 4 | Final advisor packet | v1.0: 32 items plus a 2-item annex. Each item has a technical "Independent review and disposition, NOT legal approval" block separate from a blank "Substantive legal decision" block. Status-layer legend (source verification / independent review / advisor decision / formal validation). Discovery addendum on the 1954 Gazette | `ADVISOR_REVIEW_PACKET.md`, `advisor_review_packet.csv` |
| 5 | Prioritised acquisition work order | 7 priorities and 20+ work orders, each with the discovered location, provenance class, steps and blocker | `SOURCE_ACQUISITION_WORK_ORDER.md`, `registers/source_discovery_2026-11-22.csv` |

## Discovery highlight (evidence only, no status change)
An archival scan of the **Gazette of India No. 47, 27-11-1954, Part II s.4 (S.R.O. 484)** is on archive.org (Public.Resource.Org; MD5 matches the published checksum). Page images: printed p.291 has the masthead and preamble; **printed p.300 shows r.23(3) "You are not obliged to say anything …"**. This agrees with the MML copies and disagrees with the India Code compilation. **The r.23(3) findings remain CONFLICTING** until four gates are met:
1. custodian authentication, or an advisor decision on the evidence tier
2. the r.23 amendment chain 1954 to date (amending S.R.O. scans located but not yet read)
3. an independent second reading of the image
4. an advisor decision

## Remaining blockers
1. **No legal advisor nominated.** The 32+2 packet cannot be decided, so there is no reference set and no accuracy measurement. This is the gate for the calibration batch.
2. **Citation-code coverage below 90%** (82.8% / 86.2%). The remaining 15 codes are 9 probable, 3 statistical co-citations, 2 category-only (Army Orders) and 1 unresolvable (V6-S03). Further gains need record-owner input; inflating the identities is not an option.
3. **Source access from this container:** egazette.gov.in, all AFT bench sites, pcdapension, cgda and indianarmy time out; web.archive.org and highcourtchd are reset. This blocks S.R.O. 258/2002, Entitlement Rules 1982/2008, AFT judgments, commencement notifications and post-BNSS rules (Indian network or owner machine needed).
4. **Owner actions pending:**
   - approve the work-order execution and allow-list additions (desw.gov.in, dmamod.gov.in)
   - send the custodian request
   - supply the Regulations for the Army and state their access marking
   - decide on the MML base64 parts in the private Git history of `legal-knowledge/v2.5-staging`
5. **Security:** `aftjabalpur.in` (in `config/sources.yaml`, AFT allow-list) now serves a betting site. Removal is recommended in a separate crawler PR.
6. **Merge safety:** merging PR 6 or PR 5 into `main` or `legal-knowledge/v2.5-staging` would trigger the HF sync workflow.
7. **Same-model limitation:** every agent and reviewer is the same model family. Human legal review is the only independent check.
8. **Crawler test suite** not in CI (missing dependencies; unrelated to the audit).
