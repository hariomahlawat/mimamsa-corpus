# Independent review: PR #43 workstreams and judgment audit (head 3257ebb9)

Reviewer model: Fable 5.2 (claude-fable-5-2). Review only; the worktree was not modified (git status clean, no `__pycache__` left).
Findings: `fable_review_ws_3257ebb9_findings.csv`. Sample table: `fable_review_ws_3257ebb9_sample20.csv`. Scripts and raw evidence are in this folder.

## Verdicts

| Scope | Verdict | Conditions |
| --- | --- | --- |
| 1. Statutory workstream | ACCEPT | WS-09 (P3) is a naming fix |
| 2. Judicial workstream | ACCEPT WITH CONDITIONS | WS-05, WS-10 (P3) |
| 3. Quality workstream | ACCEPT WITH CONDITIONS | WS-03 (P2) |
| 4. C10-HF-JUDGMENTS audit | ACCEPT WITH CONDITIONS | WS-01, WS-02, WS-04 (P2); WS-06, WS-07, WS-08 (P3) |
| Core fixes 7ccb9c2e (regressions only) | No regression found | core `--check` reproduces 8 files; RC-01, RC-03, RC-04 fixes present |

No P1. Four P2, six P3, four INFO.

## Builder checks (all reproduce; worktree clean afterwards)

- Statutory `--check`: CHECK OK (9 files).
- Judicial `--check` with `--store`: 10 outputs byte-identical.
- Quality `--check`: 8 files byte for byte. The pinned input snapshot equals the live reconciliation outputs.
- Judgment audit `assemble --check`: 14 files reproduce. Unit tests: 11 pass.
- Reconciliation core `--check`: 8 files reproduce.
- Limit: `assemble --check` rebuilds from the persisted batches, so it does not test extraction. I re-ran extraction for all 20 batches: 16 identical, 4 different (WS-02).

## P2 findings

- **WS-01, truncated copies under-counted.** The 7 `INCOMPLETE_COPY_TRUNCATED` files do lack `%%EOF` and fail to open. But 19 raw files have no `%%EOF` anywhere and 41 have none in the last 2 KB. The extra ones open through PyMuPDF repair and are counted `PROCESSED`. At least 8 are missing their later pages (for example text on pp.1-16 of 34, 1-76 of 171, 1-7 of 32) and are labelled as needing OCR, which cannot recover them. None is in the continuation manifest.
- **WS-02, batches 0-3 are stale.** They were produced by an earlier case-number pattern under the same extractor version, and the resume check skipped them. 242 files gain case numbers on re-extraction; about 157 records would move to `MATCH`. Batches 4-19 are byte-identical.
- **WS-03, wrong hash in C10-QP-02.** The proposal registers "a separate compilation source with candidate copy d163e785", which is the Hindi Gazette-pagination text, and then says d163e785 is not proposed. The compilation is d4449e99. The builder picks the first candidate by sort order. The same mislabel is in 12 citation rows.
- **WS-04, outcome candidates on ordinary judgments.** In my 20-judgment random sample: 12 right, 3 wrong, 4 missed. Crawler and text outcomes disagree in 549 of 1,775 records that have both, and that disagreement is not flagged.

## Random sample of 20 ordinary judgments (seed 20261124; PROCESSED raw-store files not in the reviewed 30)

| Field | Result |
| --- | --- |
| File identity (SHA-256) | 20 of 20 |
| Crawler case number | 18 of 18 right; blank on the 2 Supreme Court records |
| Extractor case number | 13 confirmed or found, 7 missed, 0 wrong |
| Crawler decision date | 20 of 20 right |
| Extractor date status | 17 correct MATCH, 2 not found, 1 wrong DIFFERS (Supreme Court report layout) |
| Crawler outcome | 10 of 11 right where present; blank in 9 |
| Extractor outcome | 12 right, 3 wrong, 4 missed, 1 not applicable |
| Relevance class | no unjustified NOT_RELEVANT; 2 non-military Supreme Court cases and 1 land-acquisition case sit in UNCERTAIN; 2 CAPF cases sit in the military-administration class |

Per-row detail is in the CSV. The crawler metadata is more reliable than the extractor on every field measured. The sample is small (20), so the rates are indicative.

## Accounting identities (recomputed independently from git objects at ad77758d)

- Judgment metadata records: 4,259 (Delhi 1,957; P&H 1,215; J&K 410; SC 368; Allahabad 309). Matches.
- Raw judgment files under `data/raw/sci` and `data/raw/hc`: 3,951 paths, 3,951 distinct blobs, every one referenced by a judgment record. All 3,951 re-hash to their file name. Matches.
- Excluded log: 120,185 lines, per-court counts match.
- 3,959 = 3,951 + 8 curated binaries. The 4 `NOT_PROCESSED` files (Ram Sarup, Mani Ram Bhaira, Ravishankar Tandon, Chandrabhan Sanap) have no bytes in the raw-data tree, the staging tree or the working store (searched by hash and by declared size). Confirmed.
- The one-file-many-records case with 209 records is a real 85-page Delhi HC common judgment (01-07-2025).

## Spot checks against PDFs

Judicial (12 checked, all confirmed):
- Parashotam para 32, official copy p.22: "does not lay down the correct law". Recorded as documentary wording with escalation ESC-C10-03; no status changed.
- Tarsem holding, SCR copy pp.5-6 paras 5-7. Girish para 22 (official pp.15-16) and the s.22(1)(c) sentence on p.16.
- Ranjit "3.?.1986" (JUDIS p.3) against "3. 7.1986" (SCR p.5). PPS Bedi "2S" against "25" (both p.7).
- WSB-H-053 passage: JUDIS p.20, SCR PDF p.26 (report page 418).
- S P Rathore para 8 (SCR p.4). Mullikote para 43 (pp.26-27). Isaac p.93 para 39(iii) was not confirmed by me (my search pattern did not match; the builder checks the quote verbatim).
- "2026 INSC 1113": 0 hits in all of `data/` at ad77758d.
- Ram Sarup: sidecar declares 88f84411 on HF; no C5 register row in any of the 10 registers; no local bytes.
- NOT_HELD rows: no matching Supreme Court record by date or party for the 9 cases; Chandra Kumar and S.R. Dhingra are in the excluded log with the stated dates.

Statutory (7 checked, all confirmed):
- 338d43ad is the AFT Act Gazette (Part II s.1 No. 66, 28-12-2007), filed as category "rule".
- 4284820e prints "For Official Use Only" on p.1 (1,320 pp.).
- d163e785, 60d145c5, 72fc9a75 are Hindi texts paginated 9-153, 155-473, 475-535 with no masthead; the BSA file ends with the MGIPMRND 27-03-2024 imprint. Page image of BNS p.1 viewed.
- BNSS s.531 (572c7988 p.174) and BSA s.170 (554b2b4a p.51) print the repeals. Both edges are `UNRESOLVED_COMMENCEMENT`; `commencement_date_evidenced` is empty on all 84 unresolved or not-located edges.
- c57b113a has no masthead. 3a551c1f is a one-line compiler note.
- The C9 columns of the amendment graph are cell-for-cell identical to PR #41 (0 differences in 116 rows).

Quality (reproduced independently from the crosswalk, copy register and inventory):
- 983 citation items; 42 / 652 / 289; 77 placeholders; 53 case rows; all 42 anchors on `C5-SRC-P0-ARMY-RULES-1954~C1`.
- 274 working-store-only items (204 Army Rules Gazette + 70 on 12 judgments); 393 HF+GitHub; 27 HF-only. 252 KB records with an item at risk, 93 with all items at risk.

## Evidence discipline

- No legal status changed. All 9 judicial and 12 quality proposals are `PROPOSAL_NOT_APPLIED`.
- "Overruled" appears once, as wording, with an open escalation. Judgment-audit relationships are only `CITES` and `MATCHES_CURATED_CASE`.
- No commencement inferred from publication. Disputed readings (r.23(3), r.168(2), Act 37/1992 and others) carry both readings verbatim.
- AI readings are labelled on every reading row. Every judgment-audit value is labelled automated and not verified.
- Availability is not presented as authentication anywhere I read. WS-09 is a column-name weakness only.
- Current text is verbatim except in WS-05.

## Not checked

- Hugging Face bytes (no access; every claim rests on listings and sidecars).
- The treatment search totals (2,034 hits) and the 32 quoted readings beyond the 12 above.
- The SCR comparator ratios.
- The 60 registration rows beyond the 7 files opened; acquisition scores; the 267 finding-status rows.
- Legal correctness of any classification.
- NOT_RELEVANT: all 74 were screened by keyword and 9 were read; the other classes were not sampled beyond the 20.
