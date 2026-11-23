# Supreme Court tranche 2: evidence-review plan (prepared, NOT active)

**Status.** This is a plan only. No entry, record or simulation result here is active, and nothing approves any copy. Tranche 2 needs its **own** PR, its own independent review, its own owner decision records and its own BIND line, separate from Gazette tranche 1.

**No legal effect.** Documented provenance of a judgment copy says nothing about whether the case's proposition is current, binding, followed, distinguished or overruled. No crosswalk row may be marked current or binding because of this tranche.

## Candidates (C6-01 draft addendum)
| sha256 | Source | Identity as recorded | Pages | Format seen on page 1 | Crosswalk effect alone (C6-01) |
| --- | --- | --- | --- | --- | --- |
| ed7cf31f | C5-SRC-J-SC-1987-RANJIT-THAKUR | Ranjit Thakur v Union of India, SC 15-10-1987 (JUDIS 8566) | 9 | JUDIS header ("http://JUDIS.NIC.IN ... Page 1 of 9") | DCLR-SC-1987-R01 PARTIAL_MATCH → EXACT_ANCHOR |
| eb442080 | C5-SRC-J-SC-1990-SN-MUKHERJEE | S N Mukherjee v Union of India, SC 28-08-1990 (JUDIS 7439) | 23 | JUDIS header | DCLR-SC-1990-N02 → EXACT_ANCHOR |
| 3b753548 | C5-SRC-J-SC-2005-NAVJOT | State (NCT of Delhi) v Navjot Sandhu, SC 2005 (**no judgment date recorded** in the identity) | 107 | JUDIS header; "Appeal (crl.) 373-375 of 2004" | DCLR-SC-2005-L01 → EXACT_ANCHOR |
| 3056712c | C5-SRC-J-SC-2013-DHARAMVIR | Dharamvir Singh v Union of India, SC 02-07-2013 (JUDIS 40493) | 36 | court judgment layout; C.A. 4949 of 2013 | DCLR-SC-2013-N08 → EXACT_ANCHOR |
| 970b9680 | C5-SRC-J-SC-2015-RAJBIR (copy C1) | Union of India v Rajbir Singh, C.A. 2904/2011, SC 13-02-2015 | 20 | court judgment layout | DCLR-SC-2015-N09 → EXACT_ANCHOR |
| 3c50cdb7 | C5-SRC-J-SC-2019-NS-YADAV | Ex Cfn N S Yadav v Union of India, SC 2019 (C.A. 7672 of 2019) | 15 | court judgment layout | none |
| 4f7ea3a4 | C5-SRC-J-SC-2026-GIRISH-FEB | Union of India v Sgt Girish Kumar, 2026 INSC 149 | 17 | neutral citation on page 1 | DCLR-SC-2026-007 → EXACT_ANCHOR |
| 10e1954f | C5-SRC-J-SC-2026-MULLIKOTE | Union of India v Balakrishnan Mullikote, 2026 INSC 286 (**"CORRECTED"**) | 62 | neutral citation; "Civil Appeal No.____ of 2026 arising out of Diary No.27246/2023" | DCLR-SC-2026-N16 → EXACT_ANCHOR |

The non-primary Rajbir bosir rendition (6b495f14) is not part of tranche 2. It never anchors.

## Risks found while preparing (to be resolved in the tranche review)
- **R-T2-1. JUDIS renditions: court-issued, or system-rendered?**
  - Three candidates (Ranjit Thakur, S N Mukherjee, Navjot) carry the JUDIS header ("http://JUDIS.NIC.IN SUPREME COURT OF INDIA Page 1 of N"). That is a database rendition format, not the court's signed judgment layout.
  - The C6-01 draft classes them `PRIMARY_OFFICIAL_COURT_COPY`, and rule 1 accepts the class because carrier and host fit.
  - Under the fidelity table they could instead be `COURT_SYSTEM_RENDITION` (non-primary).
  - **This needs an explicit owner decision before tranche 2:** either JUDIS renditions from the court host are the official copy for these older judgments, or they are non-primary. Rule 1 cannot tell the difference; only the fidelity class does.
- **R-T2-2. Identity rests on page-1 text only.**
  - All 8 pass identity through the court page-1 text rule: two title words plus a year or case number in the text layer.
  - None has an image check (`RULE_DECISION_PACK_data.json`, B).
  - Under policy B2 the 7 anchor-creating entries need a C6-style CONFIRMED check, or a reviewer statement, before approval.
- **R-T2-3. Case number, date and citation gaps.**
  - Navjot: no judgment date in the recorded identity.
  - Mullikote: a corrected version with a blank civil appeal number on page 1; which version is held (corrected or original) must be recorded.
  - N S Yadav: diary number and appeal number both appear; the judgment date is not in the recorded identity.
  - Neutral citations should be read from the image (2026 INSC 149, 2026 INSC 286), not only from the text layer.
- **R-T2-4. Page completeness.** For every candidate, C6-01 records "full judgment file held (page completeness not re-checked)". The page count against the court's stated count ("Page 1 of N"), and the last page (signatures, date), must be checked.
- **R-T2-5. Extraneous material.** Confirm there is no headnote, publisher summary or third-party matter. The JUDIS renditions include a header block, and its origin should be described.
- **R-T2-6. Multiple copies.**
  - Rajbir has three copies: C1 (proposed primary), C2, and C3, the bosir rendition, which is non-primary.
  - The anchor must name exactly one copy (`anchor_copy_id`), and the others must not be counted twice (the AUTH-LEDGER-01 tests cover this for C1 plus the rendition).
- **R-T2-7. Subsequent judicial treatment.**
  - Dharamvir Singh (2013) is linked in the project brief to a later Supreme Court ruling on the 2008 Rules.
  - Any treatment (followed, distinguished, overruled, or applicable rules) is a legal question for the adviser (C6-05). The tranche records provenance only and must say so in each limitation.

## Required checks per entry (tranche 2 review protocol)
1. **Identity.** A CONFIRMED image check of page 1 and the last page records:
   - the parties, case number(s), judgment date, bench, and neutral citation if any;
   - the reportable marking;
   - for Mullikote, the "CORRECTED" marking.
2. **Carrier and fidelity class.**
   - Court-issued layout versus JUDIS rendition (R-T2-1).
   - The producer and structure facts (`evidence/copy_structure.csv`); for any signed PDF, the signature range coverage. That is structural only, never "signature verified".
3. **Provenance.**
   - The first-class record carries the copy's own sha256.
   - The locator passes the AUTH-LEDGER-02 parser for `PRIMARY_OFFICIAL_COURT_COPY` (sci.gov.in hosts only).
   - Retrieval date where recorded; otherwise the limitation is stated.
4. **Completeness.** Page count equals "Page 1 of N" where printed; last-page signature block present; no missing pages.
5. **Extraneous material.** None, or described.
6. **Copy-level anchor reproduction.**
   - For each of the 7 claimed anchor changes, rerun the reader in a temporary directory with only that entry, and with the full tranche jointly.
   - Confirm the crosswalk row, its `anchor_copy_id` and its evidence status. Confirm that no other row changes.
   - The C6-01 figure (EXACT_ANCHOR 6 → 13) must be reproduced from these runs, not copied.
7. **Contradiction.** Exact-string locator contradiction, plus any differing sha256 recorded for the same judgment in the registers.
8. **Limitations text.** Provenance only; no statement of currency, binding force or treatment.

## Approval path (nothing here is authorised)
1. Owner decision on R-T2-1, the JUDIS class.
2. Owner decision on policy B (B2 recommended).
3. New CONFIRMED identity checks. This is offline work on held files.
4. A tranche-2 PR containing:
   - `ledger/vNNNN.csv`;
   - D- and R- records with scope and `legal_approval: NOT_GIVEN`;
   - the joint-effect diff.
5. An independent review of that PR.
6. Merge.
7. A BIND line in a later PR.
