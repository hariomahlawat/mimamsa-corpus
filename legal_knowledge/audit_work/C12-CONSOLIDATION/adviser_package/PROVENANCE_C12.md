# Provenance note: C12 legal-adviser package

**PREPARED BY AUTOMATED AGENTS. TECHNICAL AND DOCUMENTARY REVIEW ONLY. NO LEGAL VALIDATION.** Nothing in this package is a legal conclusion, a status change or an approval. Every reading of a source page was made by an AI agent from a text layer and is not human-confirmed. Questions are for a qualified legal adviser (or JAG, where the controlling policy requires it).

- Built by: `tools/build_adviser_package.py` (automated agent, Claude Opus 5.5 subagent), CLAUDE.md rules followed: no download, no commit, no source modified.
- Worktree holding the C9-C11 audit inputs: `/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c12w` at HEAD `b4948b0f952ceda17cf9789f521854bc6a3d9bf2`. Git state per file is given below (`committed-clean` = tracked and identical to HEAD).
- The worktree HEAD was `35ffaed2` when this task started; worktree inputs unchanged between `35ffaed2` and `b4948b0f`: yes.
- Raw-data / text-layer repository: `/home/user/c7`; text layer read at commit `ad77758d4569ba6aafa955cc7843d874489e10f7` (`data/text/<doc_id>.txt`).
- C9 commit `cfc52d5792796050dcae351afda5609f7db41a5f`: C9: apply legal-deliverables review conditions (LG-05, LG-06 P2; LG-01..LG-03, LG-07..LG-09, LG-11 P3); commit narrow reviews and dispositions
- C9 commit `a61c0e572c395022d606213fdfbf5dc6cbb7b359`: C9-LEGAL-EVIDENCE: apply final-head review 3b76ccd8 (FL-01 P2 checksum drift fixed; FL-02..FL-06 P3); add review record

## Input files

| Key | Path | sha256 | Git state |
| --- | --- | --- | --- |
| GRAPH_SUMMARY | `/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c12w/legal_knowledge/audit_work/C11-JUDICIAL-QUALITY/relations/outputs/GRAPH_SUMMARY.json` | `203df205c1ef7ed37e01a1f15b1c340fc0f4cfc819d2c644787e7d816fb3110e` | committed-clean |
| TREATMENT_CANDIDATES | `/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c12w/legal_knowledge/audit_work/C11-JUDICIAL-QUALITY/relations/outputs/TREATMENT_CANDIDATES.csv` | `28331abf17d4d296a4baf5e88444a61d1d105319156cb5ed5d042389057fce27` | committed-clean |
| DOSSIER | `/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c12w/legal_knowledge/audit_work/C11-JUDICIAL-QUALITY/relations/outputs/PRIORITY_TREATMENT_DOSSIER.md` | `2ea52aaa89d55afe069e2612045bd9792ae4987eba533be749a2eeb82df6416e` | committed-clean |
| DISP_REL | `/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c12w/legal_knowledge/audit_work/C11-JUDICIAL-QUALITY/review/DISPOSITIONS_relations_c11.md` | `ded89fae1e0fe10a8025d50d815ce1ad19ac73264f311fa0f02ab8d1aafa8594` | committed-clean |
| AFFECTED | `/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c12w/legal_knowledge/audit_work/C11-JUDICIAL-QUALITY/curated/AFFECTED_RESEARCH_RECORDS.csv` | `875e1a607bd593e0a218396696f81b0b24af1f860b6a5a6555aed95afaa087a5` | committed-clean |
| CURATED53 | `/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c12w/legal_knowledge/audit_work/C11-JUDICIAL-QUALITY/curated/CURATED_53_C11.csv` | `50b626d59e3247d7d5de456e391257d590bc48161da2b18aa305a6065c222746` | committed-clean |
| ESC_C10 | `/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c12w/legal_knowledge/audit_work/C10-RECONCILIATION/workstreams/judicial/ADVISER_ESCALATIONS_C10.csv` | `6d5bdc3dc916c09440fb50680cea7063d1d8fb346dad91007aa5452ce7847f24` | committed-clean |
| JT_C10 | `/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c12w/legal_knowledge/audit_work/C10-RECONCILIATION/workstreams/judicial/JUDICIAL_TREATMENT_C10.csv` | `4acc9303731c32f57a1969eefd95f62a65aa9bf7199f8ee320e1dd850d29477e` | committed-clean |
| C9STAT_C10 | `/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c12w/legal_knowledge/audit_work/C10-RECONCILIATION/workstreams/judicial/C9_FINDING_STATUS_C10.csv` | `139a870b6ce368e750cc5d75bdd2aa20a608779b81ef775c6fb39ccc4dcaece8` | committed-clean |
| AMD_GRAPH_C10 | `/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c12w/legal_knowledge/audit_work/C10-RECONCILIATION/workstreams/statutory/amendment_graph_c10.csv` | `c4e03860cedeec7c3f5aad2fa52f79e525869c32d116aaa31be89455fa5948db` | committed-clean |
| ESC_STAT_C10 | `/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c12w/legal_knowledge/audit_work/C10-RECONCILIATION/workstreams/statutory/escalation_matters_c10.csv` | `20917856f183c5e6e092dce7bab53e794ea7e0d4c982340a7a294d15eb5af945` | committed-clean |
| STAT_FIND_C10 | `/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c12w/legal_knowledge/audit_work/C10-RECONCILIATION/workstreams/statutory/STATUTORY_C10_FINDINGS.md` | `f2c38a6a1485918516a0aaee627fb97506ce52b2625827d239f9b34c4bc9886b` | committed-clean |
| DISP_FINAL | `/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c12w/legal_knowledge/audit_work/C10-RECONCILIATION/review/DISPOSITIONS_final_head_confirmations.md` | `a7d902768e5b1230e2185b95b8201b41b371c947252214efbb31ad0a365e6498` | committed-clean |
| RR04_REVIEW | `/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c12w/legal_knowledge/audit_work/C10-RECONCILIATION/review/final_head_confirmations/fable_review_7ccb9c2e.md` | `0763033e20a491404b7f82ccb6cbcedfb7718506db302df4793cbfed9fb34401` | committed-clean |
| AUTH_MATRIX | `/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c12w/legal_knowledge/audit_work/C10-RECONCILIATION/outputs/CORPUS_AUTHORITY_MATRIX.md` | `a5a0aee710530ca5c0821baaa53f1371feaf08f93cbbdc3307711b9b4dbc3485` | committed-clean |
| PR46_REVIEW | `/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c12/reviews/fable_review_pr46_c69eee41.md` | `d14084a8c57def3cb5bbfaa0507ea021fe2f249fcb02224d8a922b363d2cb5b6` | outside worktree |
| RECORDS658 | `/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/c12w/legal_knowledge/curated_originals/knowledge_base/v0.9/records_658.jsonl` | `9a8f0d193065762ffa987116dc761bcb734008d2a87a946f5591741f5befcfc1` | committed-clean |
| BRIEF | `/home/user/mimamsa-corpus/CLAUDE.md` | `89e18fa34d9a72cbe155bfde5351c5dad30039605ab68beafbfaac84750c0da2` | outside worktree (repo HEAD b20843d6) |

## C9 files read from git (not from a working tree)

| Commit | Path | Blob |
| --- | --- | --- |
| `cfc52d57` | `legal_knowledge/audit_work/C9-LEGAL-EVIDENCE/DECISION_MATRIX_C9.md` | `de05422fce4d9483e344f090d04084b99c57121c` |
| `cfc52d57` | `legal_knowledge/audit_work/C9-LEGAL-EVIDENCE/CORRECTIONS/LEGAL_ADVISER_ESCALATION.md` | `94b0e28f114a9a5ce4bb9bec866d0086977bf59d` |
| `cfc52d57` | `legal_knowledge/audit_work/C9-LEGAL-EVIDENCE/STATUTORY/UNRESOLVED_MATTERS.md` | `c8a020250501e9e0934d56154647c81121cf7774` |
| `a61c0e57` | `legal_knowledge/audit_work/C9-LEGAL-EVIDENCE/DECISION_MATRIX_C9.md` | `de05422fce4d9483e344f090d04084b99c57121c` |
| `a61c0e57` | `legal_knowledge/audit_work/C9-LEGAL-EVIDENCE/CORRECTIONS/LEGAL_ADVISER_ESCALATION.md` | `36c0942a2aedf4594683b0b33af7e786f75dd899` |
| `a61c0e57` | `legal_knowledge/audit_work/C9-LEGAL-EVIDENCE/STATUTORY/UNRESOLVED_MATTERS.md` | `c8a020250501e9e0934d56154647c81121cf7774` |

`DECISION_MATRIX_C9.md` and `STATUTORY/UNRESOLVED_MATTERS.md` are identical at both commits. `CORRECTIONS/LEGAL_ADVISER_ESCALATION.md` differs; the package uses the later version at `a61c0e57` (the final head accepted in C10 DISPOSITIONS_final_head_confirmations.md).

## Text-layer documents read for excerpt checks

| doc_id | blob at ad77758d |
| --- | --- |
| act-armed-forces-tribunal-2007 | `ae39e4efcb22dca65f5f7677c26ea339814894ca` |
| act-army-1950 | `c0eaf43bd3539804933e20a8e1dcdd62851b6c26` |
| act-bnss-2023 | `46f48aae18864463db12fcd46a98ede4b550a685` |
| act-bsa-2023 | `3b0d767c430413b1a4b8e69e05334ddb12cd6274` |
| act-the-finance-act-2017 | `0c147f80e3794812e33fb902eac7868257fb33cc` |
| act-the-tribunals-reforms-act-2026 | `b15edfdf39275c8183ed8e12a1ae80af08447875` |
| hc-allahabad-2026-wria-2923-2026-uphc011159512026-1-2026-04-02 | `a1a8b60d808288ca6cb6d6c021268cfeda31ae1f` |
| hc-delhi-2026-w-p-c-16771-2025-dlhc010862002025-1-2026-03-11 | `f106e808e429fe8f01bb3df4a600125a1ac1d0ea` |
| hc-delhi-2026-w-p-c-2053-2026-dlhc010054682026-1-2026-04-20 | `671879c186836118a312486ec0ef2a2384a20482` |
| hc-jkl-2025-wp-c-2370-2025-jkhc010050362025-1-2025-10-06 | `1967812365575f06678d0da5d764b0598ad36ca3` |
| hc-jkl-2026-wp-c-1426-2026-jkhc020026572026-1-2026-05-19 | `74fe95c4f3956f476881917274de56190a0f1cd8` |
| hc-ph-2026-cwp-7955-2026-phhc010370702026-1-2026-03-17 | `bc84161a053f0c08d4d476e5f584b1ce0c4f8136` |
| rules-army-rules-1954 | `9437a8ad81062a12089d885d53385de6d1d5f8be` |
| sc-1987-ajmer-singh-etc-etc-1987insc142 | `a06420e6eb4e3c02d21fcc288bff04df87ce7fd7` |
| sc-1996-mafatlal-industries-ltd-etc-et-1996insc1514 | `3ab2f2a03e1f266b28ab7859a84c7601665faa7f` |
| sc-2000-union-of-india-and-anr-2000insc231 | `9211ad641fd4824e058eaaf99b9e8cecd50981da` |
| sc-2008-union-of-india-ors-2008insc930 | `01736af14e5a7224b7dd83c9c8857f0df0260fc5` |
| sc-2013-dharamvir-singh-2013insc408 | `7f74a576675c98bfa9d4a2f1389861ff2d6237cb` |
| sc-2014-shatrughan-chauhan-anr-2014insc46 | `08290d073931e992d082c4dae5724cad9bc60676` |
| sc-2015-supreme-court-advocates-on-rec-2015insc285 | `938c0e3285248c874a05d7e84b8aeb3fca405c4d` |
| sc-2015-union-of-india-2015insc886 | `4bdfdda46f17e11d363d4e0393d73d5d3bcaf117` |
| sc-2015-union-of-india-ors-2015insc206 | `2a43c22f8ba5e4359ff577ee5baae568fee96a0e` |
| sc-2017-justice-k-s-puttaswamy-retd-an-2017insc801 | `95ff5f2b1856721fb99738ac1f9cce464359f70f` |
| sc-2018-joseph-shine-2018insc898 | `580a1d4eb36d6ea1a034139fea35ab8aa73570ae` |
| sc-2018-justice-k-s-puttaswamy-retd-2018insc880 | `5bf60460f5c2c83039fe2d4edcb705c4eb5d19b0` |
| sc-2019-g-h-union-of-india-ors-2019insc1359 | `449b4ce8f0814a3e54ead732fab9265e08500c3b` |
| sc-2023-union-of-india-ors-2023insc1074 | `ff6b5c39ea093209b465ee79acbe1348e732246a` |
| sc-2023-union-of-india-ors-2023insc265 | `569ce799022793d7390b113ab7c8de1c192a4bff` |
| sc-2026-union-of-india-through-its-sec-2026insc149 | `35b405243fb1821b6628a0000781cf2e117e10cb` |

## Outputs

`ADVISER_PACKAGE_C12.md`, `ADVISER_QUESTIONS.csv`, `EXCERPT_VERIFICATION.csv`, `PROVENANCE_C12.md`, `tools/` (build script and a read-only page grep helper), `SHA256SUMS`.

## Limits

- Every page reading is by an AI agent from a text layer; no page image was rendered and nothing is human-confirmed.
- Excerpts from copies outside the text layer (official copies in the C5 working store; Gazette facsimiles) could not be re-verified and are labelled so.
- Competing readings are taken from the artefacts; where none is recorded, the package says so rather than supplying one.
- Statutory edges not covered by a question: none.
