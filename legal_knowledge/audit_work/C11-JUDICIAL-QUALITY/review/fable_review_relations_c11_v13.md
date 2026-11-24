# Narrow confirmation: C11 judicial relationships and statute links, rev. 1.3

- **Reviewer:** Fable 5.2 (claude-fable-5-2). AI documentary review, not legal validation.
- **Date:** 2026-11-24.
- **Object:** `C11-JUDICIAL-QUALITY/relations/` at commit `cc798a33`, branch `claude/c11-judicial-quality`.
- **Sources read:** `data/text` as git objects at `ad77758d` of `/home/user/c7`. `holdout/` was not opened. Nothing was committed or pushed; the worktree was not modified.
- **Companion file:** `fable_review_relations_c11_v13_findings.csv` (10 entries).

## Verdict

**Accept. No P1 or P2 is open.** REL-05 is closed: every own-voice overruling I named in round 3 now reaches adviser review, and my corpus probe finds none that is neither queued nor listed in the README Limits. The adviser queue is fit for an adviser, with four noise rows and a few label errors to clean up as P3s.

## 1. The nine named misses

All nine authorities are queued.

| Authority | Citing judgment | Row(s) | Opinion label | Best candidate |
| --- | --- | --- | --- | --- |
| Kerala HC (Subramanian) and Calcutta HC (Anand Singh Bisht) | Ajmer Singh, p.9 | TC-4289a1bc33bc | SOLE_OPINION, correct | Raw text only ("these two decisions"); honest but unhelpful |
| Kanhaiyalal | Mafatlal, p.133 | TC-cd1cb49fedd0 | LEAD_OPINION, correct; author name wrong | [1959] S.C.R. 1350, correct |
| M.P. Sharma | Puttaswamy (2017), pp.275, 432 | TC-7321756415bb, TC-44e4cead92b0 | LEAD_OPINION and ORDER_OF_THE_COURT, correct | AIR 1954 SC 300 / 1954 SCR 1077, correct |
| Kharak Singh | Puttaswamy (2017), p.276 | TC-a073b2e4fab8 | LEAD_OPINION, correct | (1964) 1 SCR 332, correct |
| V. Revathi | Joseph Shine, pp.74, 154 | TC-8682d402357c, TC-235c7582ce78 | LEAD_OPINION and SEPARATE_OPINION, correct | (1988) 2 SCC 72, correct |
| W. Kalyani | Joseph Shine, p.186 | TC-48e2ff70f085 | SEPARATE_OPINION (Indu Malhotra), correct | (2012) 1 SCC 358, correct |
| Mohd Saeed Siddiqui and Yogendra Kumar | Puttaswamy (2018), pp.705, 820, 1065 | six rows | p.705 and p.820 correct; p.1065 wrong | Correct on five rows; wrong on one |

The order-of-the-Court item on Kharak Singh (split across pp.432-433) is not caught and is listed in Limits; Kharak Singh is still queued through p.276.

## 2. The 30 adviser rows

I read all 30 against the source page.

| Check | Result |
| --- | --- |
| Real own-voice overruling statement | 26 of 30 |
| OVERRULES proposals that are supported | 14 of 16 |
| Separate-opinion and dissent rows carrying no proposal | 14 of 14 |
| Opinion label correct (kind) | 28 of 30 |
| Best candidate correct, or honestly marked as raw text / not established | 29 of 30 |

**Rows that are not overrulings (V13-01, P3):**

- **TC-9b500dbe0d15**, U.O.I. v. C.S. Gill p.19: "If the objection regarding such plea is overruled, the court shall proceed with the trial". A description of court-martial procedure. Carries an OVERRULES proposal.
- **TC-e8e740a5df2f**, Shatrughan Chauhan p.54: the sentence is inside a quotation from Triveniben. Carries an OVERRULES proposal. The same passage at p.68 is correctly excluded as quoted.
- **TC-8eee72cd601c**, SCAORA p.783: a rhetorical question ("Would a decision ... stand overruled ...?"). No proposal.
- **TC-741f5ae7f6ab**, SCAORA p.802: negated ("no one has said that that decision ... does not lay down the correct law"). No proposal.

**Label and candidate errors (V13-02, V13-03, P3):**

- **Puttaswamy (2018) p.1065**, two rows: labelled SEPARATE_OPINION (ASHOK BHUSHAN), but the passage is in Chandrachud J.'s dissent. The SCR rendition prints a Bhushan running header on every recto page from p.519 to p.1075; the bracketed footer on pp.725-1075 says Chandrachud. The p.820 rows from the same opinion are correctly DISSENT. Neither p.1065 row carries a proposal.
- **Mafatlal**, five rows: the kind (LEAD_OPINION) is right, the author "AHMADI" is not. Pages 105 and 133 are in the main judgment, before Ahmadi CJ.'s header first appears at p.139.
- **TC-09b5d373b025**: the candidate for Mohd. Saeed Siddiqui is (2004) 2 SCC 130, which is Teri Oat Estates, and the row calls it a name match. The right citation, (2014) 11 SCC 415, is used by the other rows.

**Is the queue fit for an adviser?** Yes. 26 of 30 rows point at a real overruling statement, every row is marked as a lead with binding not established, and separate and dissenting opinions carry no proposal. The four noise rows are obvious on reading. The two false OVERRULES proposals should be withdrawn at the next revision, because a proposal on a quoted passage is the round-1 failure in miniature.

## 3. Probe comparison

- My probe: 94 hits on 83 pages. `OVERRULING_PROBE_C11.csv`: 74 hits on 65 pages.
- The 22 pages only in mine are procedural ("overrule the preliminary objection"), submissions, or reports of other courts. None is an own-voice overruling.
- The 4 pages only in theirs are a High Court hit, two submissions and the SCAORA p.783 row.
- **High Court exclusion.** I read the 16 excluded High Court hits. None is a High Court overruling its own earlier bench in its own words: they are quotations of Full Bench or Supreme Court text, a tribunal's view being set aside, or procedural.
- **Disclosed misses.** The README Limits lists the Puttaswamy (2017) order item (ii), three separate-opinion passages excluded as quoted or headnote, and the High Court exclusion. In each case the target authority is queued through another row.

## 4. Regression, reproducibility, provenance

- **No regression.** Against `48da982c`:
  - the citation graph is unchanged in every target state;
  - APPLIES 195, DISTINGUISHES 9 and FOLLOWS 4 are unchanged;
  - statute links differ only by the rename to JURISDICTION_REFERENCED (44 rows) and the one CrPC row now CRPC-UNSPECIFIED:s.30;
  - on the 355 re-measure rows, no row changes its proposed or labelled state.
- **`--check`:** "CHECK OK: 7 outputs reproduce byte-identically".
- **Tests:** 41 of 41 pass under python3.11 and under the venv (Python 3.13).
- **Hashes:** `OUTPUT_SHA256SUMS` and `review_inputs/SHA256SUMS` verify; the re-measure reproduces byte-identically.
- **check_provenance:** no violation on the relations folder (7 files); none new on the default roots (2 known, both in the baseline).
- All 11,076 statute rows remain VERSION_NOT_ESTABLISHED. No `__pycache__` is written.

## Requested actions (all P3)

1. Withdraw the two false OVERRULES proposals and drop the two non-overruling separate-opinion rows (V13-01).
2. Use the bracketed footer when header and footer disagree; fix the Mafatlal author (V13-02).
3. Match candidates on the party name in the sentence, not on page-header debris (V13-03).
4. Carry the preceding sentences into `lead_target_raw` for "these two decisions"; merge two cues in one sentence (V13-04).

## Limits of this review

- Text-layer reading only; no PDFs or page images were opened.
- The probe finds explicit wording. Implied overruling is not detected by either probe, and the README says so.
- Verdicts are documentary (the court's own words, about the stated target), not opinions on legal effect.
