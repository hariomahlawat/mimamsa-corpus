# CALIBRATION-02 — Reviewer D (independent legal-data challenge)

**Database only. Evidence review, not legal approval.** No row here is legal-advisor or JAG validation. The curated originals are unchanged. Reserved states are untouched: r.23(3) CONFLICTING; r.193 C-08 OPEN; r.194 C-09 PROPOSAL; r.15, r.187(1) and s.129 OPEN; AQ-05, AQ-06 and OQ-A-13 reserved. Where a proposition touches r.15 or r.23(3), the finding says that it does not decide the reserved item.

## Independence
Written in worktree `/home/user/c4-d`, branch `claude/c4-rev-d`, from base `67c6e0c1`. Reviewer D did not read the A, B, C or E worktrees or branches, or the `proposed_determination`, `independent_reviewer_assessment` and `uncertainty` columns of `COORDINATION/CALIBRATION-01/calibration_package.csv`. Nothing was downloaded.

## Method
1. Read every proposition in `propositions.csv` (382 propositions across 46 records) and challenge each one on five tests: unsupported; contradicted; a generalisation with missing exceptions; inconsistent with another record; silent on a step a commander or practitioner needs.
2. Read the provision or judgment text directly from a held file (grep plus a page read), and record the page marker or paragraph as the `locator`.
3. Scan `curated_originals/knowledge_base/v0.9/records_658.jsonl` (read only) for each topic: s.127, r.25, r.182, s.80, s.123, P S Gill, Som Datt, the 1978/1962 adjustment rules, Santosh Lohar, Kuldeep Yadav, Parashotam Dass, Isaac, r.14/15/15-A and s.89. Write cross-record issues as CROSS_VOLUME rows and in `cross_volume_register.csv`.
4. `findings.csv` was generated from a single reviewed table. The generator script stayed in the scratchpad; the CSV is the deliverable.

### Evidence-state policy used
- **VERIFIED_AGAINST_HELD_PRIMARY_SOURCE** is used only for official court copies (signed SC PDFs; the JUDIS copy of PPS Bedi) and for the Gazette text of Act 37 of 1992. SCR or mirror reproductions in the `origin/raw-data` corpus are SUPPORTED_BY_SECONDARY_SOURCE_ONLY (see Correction below).
- **Act and rule text read from India Code or MoD compilations is SUPPORTED_BY_SECONDARY_SOURCE_ONLY** (comparison text under SOURCE_AUTHORITY_POLICY v1). The hash and locator are still given. This is deliberately conservative: an Army Act or Army Rules proposition that matches the compilation is not marked VERIFIED.
- The MML is used only once, to identify the 1978 Rules notification number (S.O. 488), and is never treated as authority.

## Sources (identity = SHA-256)
| Key | File | SHA-256 |
|---|---|---|
| AA | scratchpad `derived/statutes/act-army-1950.txt` (India Code, as on 21 Jul 2025) | 88a9f1dcf859a0158c0a526f8abd82350cd3caf5af13dd1b1485b70a8abd2428 |
| AR | scratchpad `derived/statutes/rules-army-rules-1954.txt` (MoD compilation) | 94b464018d4c36fd62d1713bee6adbf48b4d711e04098125085c1da2904d5976 |
| AFT | scratchpad `derived/statutes/act-armed-forces-tribunal-2007.txt` | 9d128ae7bede5fdea1e2dfa32d6cf2ee56b53398a0618fd64984b54ada1da6d1 |
| BNSS | scratchpad `derived/statutes/act-bnss-2023.txt` | 3672ebd3fae8f2e254bd6506ecba5deb98879acf2edab320a1d962db0236fe27 |
| BSA | scratchpad `derived/statutes/act-bsa-2023.txt` | a88c574ddac5fd0713bd14be4219b6a69447b54771d200461e351a0178f702ed |
| A92 | scratchpad `downloads/statutory-auditor/1992-37.txt` (Act 37 of 1992, Gazette) | d1114517c003483e7d3fa19e849044b4e3e6b85e3c2c083cd6abbc9c916c15ec |
| GILL19 | scratchpad `downloads/citation-codes/psgill_2019.pdf` (Crl.A. 404/2013, 27 Nov 2019) | 7c32b8e87984c9f3dd52218f9030dffad3ea5aedc98d256744fd5e97d044a0ac |
| PARASH | scratchpad `derived_jud/parashotam_2023.txt` | 6b27be394632f8f60c1775da340b62dd6007142f800394696c57b40825203ccd |
| VK | scratchpad `derived_jud/virendra_2020.txt` | f73ee765c079fa6a9e34b27a2902b155b02e57f493e7448d6381104e7f443cee |
| ISAAC | scratchpad `downloads/independent-reviewer-B/isaac_2026_INSC_993.txt` | 1e315d45364846786efdbea8be797fef2c8cdb2044566e41c446fa7b6d17c5f5 |
| ER23 | scratchpad `downloads/discovery/desw_Entitlement_Rules_2023_13MB.pdf` (image only; not read) | 29f6fa2cfcd961aadce490679a686b5a3b7b2e683a0eaceb42bc2cd2ebb70dad |
| AAMML | scratchpad `downloads/independent-reviewer-C/aa2pdf.txt` (manual) | 914a7cd675d61f5e22caa02508375d51a6859d265614038e0c4c7520a91957d9 |
| PPSJ | scratchpad `downloads/citation-codes/ppsbedi_judis9884.pdf` (JUDIS official SC copy; 1983 SCR (1) 393) | 211dbaf4e20371cc476d09c158e41b976786d57f67336ff6fc802170178b3cca |
| PPS | raw-data `sc-1982-lt-col-prithi-pal-singh-bedi-e-1982insc65` (SCR mirror; superseded by PPSJ) | ebb86d4b3308eb89e9dfa2ef1d78d93463f15157278fce2c86b047c915251238 |
| SOMDATT | raw-data `sc-1968-som-datt-datta-1968insc246` | c6dd21359a7e3cbd4da711d87f80536f004cf206d7970cfb5eed0fbd5d427c83 |
| KY | raw-data `sc-2019-union-of-india-ors-2019insc1083` (Kuldeep Yadav) | b35f7f9e73f850351ed2779f17c3f0b68044a472f3a0a14fc0e68a865e36422a |
| LOHAR | raw-data `hc-ph-2023-cwp-3118-2023-phhc010194042023-1-2023-10-03` | bdcc30e45cea292770eadf30ebe4034ab0bb6fbd5baf7b102b0a97ae73ab2122 |
| GILL12 | raw-data `sc-2012-union-of-india-and-ors-2012insc146` (Brig P.S. Gill; used only for name-collision check) | 7908f5b4a7284402b44a85c334c2b1af47ac4546f78d74ed30ff9d5b37e010da |

For raw-data items, the SHA-256 is the raw-file hash recorded in `data/meta/<doc_id>.json`, and the text was read from `data/text/<doc_id>.txt`.

## Counts
- `findings.csv`: 382 rows, one per proposition, covering all 46 records.
- By severity: P1 1, P2 13, P3 69, NONE 299.
- By evidence state: VERIFIED 22; SECONDARY_ONLY 121; SOURCE_NOT_HELD 35; INTERPRETATION 5; HISTORICAL_UNRESOLVED 2; CONTRADICTORY 1; UNSUPPORTED 5; NOT_A_LEGAL_PROPOSITION 191.
- `cross_volume_register.csv`: 20 links: 5 INCONSISTENT, 5 MISSING_LINK, 3 MISSING_PREREQUISITE, 1 CONFLICTING_VERSION, 2 MISLINKED, 4 DUPLICATE.

The P1 row is COI-003 P6, which understates the r.182 exclusion (re-assessed in the second commit; see below).

The 13 P2 rows cover 10 distinct defects:
- HCE-016 P2: says s.80 "primarily" covers non-officers; it covers only non-officers.
- CM-028 P8 and REF: wrong rule; r.56 is cited, but the provisions are AR r.84 and AA s.145.
- COI-031 P3 and REF: AA s.89 is missing, and the s.89 and r.186 measures differ.
- V8-JD-02 P1: "1952 rules" should be the 1962 Rules (S.R.O. 709, seven days).
- V7-JD-05 P1: date, citation and holding attribution are unresolved.
- CM-026 P1 and P7: BSA s.63 certificate is missing and the record is unlinked to CM-025.
- ADM-CL-02 P1: misses the r.13-A, r.14 proviso, r.14(3) and r.15-A routes.
- PEN-WF-03 P2 and PEN-CL-06 P1: Isaac (2026 INSC 993) is absent from all 658 records.
- PEN-024 P4: unsourced dates.

## Correction (second commit, after a coordinator protocol check)
**1. Evidence state.** Eight rows had been marked VERIFIED against raw-data copies. Those copies are SCR or mirror reproductions, not official court copies, so under SOURCE_AUTHORITY_POLICY v1 they cannot support VERIFIED.
- **Reclassified to SUPPORTED_BY_SECONDARY_SOURCE_ONLY** (no official copy is in `registers/held_sources_scratchpad.csv`):
  - Kuldeep Yadav: D-0024 ADM-013#P2, D-0026 ADM-013#REF, D-0027 ADM-026#P1, D-0029 ADM-026#REF.
  - Som Datt: D-0183 COI-018#P2, D-0368 V8-JD-02#P1.
- **Re-verified against the official JUDIS copy** of PPS Bedi (`downloads/citation-codes/ppsbedi_judis9884.pdf`, sha 211dbaf4...), with new locators:
  - D-0071 CM-JD-01#P1 and D-0073 CM-JD-01#REF stay VERIFIED.
  - D-0072 CM-JD-01#P2 is re-pointed to the same copy.
- **Severities unchanged.** V8-JD-02#P1 stays P2. The "1952" versus "1962 Rules (S.R.O. 709)" discrepancy is read from a faithful SCR reproduction, so the reclassification does not lower the risk.

**2. Severity re-assessed on content alone.** Severity measures the consequence if the content is relied on, not the record's review status. The earlier statement that no P1 was assigned "because every record carries review-pending status" is withdrawn.
- **COI-003 P6: P2 raised to P1.** The sentence affirmatively implies that some CoI statements are admissible substantive evidence against the accused. Relied on, it leads to admitting evidence that r.182 excludes, and to a conviction open to being set aside. Cross-volume link D-CV-004 is raised to P1 as well.
- **HCE-016 P2: kept at P2.** "Primarily" misstates the scope of s.80 and could invite an unlawful award, but it neither affirmatively authorises an award nor states a wrong power.
- **CM-028 P8: kept at P2.** The wrong provision misdirects the procedure, but the record itself flags the citation "[exact rule verify]", and the substantive s.117(2) proposition is correct.

## Limitations
- The Gazette text of the Army Act, Army Rules, AFT Act, BNSS and BSA was not held, so statutory propositions stop at SECONDARY_ONLY.
- The Santosh Lohar text layer is font-encoded and largely illegible. A page-image read is needed.
- The held ER 2023 PDF has no text layer.
- The following are not held: the PRA, DESW FAQs, the 1978 Adjustment Rules, Pooja Pal (2026), AO 45/2001, the censure policy and the inter-services statute.
- Pension records were tested mainly for internal consistency and cross-volume links.
- The cross-volume scan was keyword-driven across 658 records. It is not an exhaustive pairwise comparison.
- Default NOT_A_LEGAL_PROPOSITION rows (headings, questions, checklist and design statements) were each read and challenged for any hidden legal claim. Such claims were split out as their own findings where found.
- The coordinator reconciles. Disagreements with other reviewers are not settled here.
