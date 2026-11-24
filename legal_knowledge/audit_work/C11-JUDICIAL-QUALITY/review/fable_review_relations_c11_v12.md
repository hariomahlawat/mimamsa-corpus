# Narrow confirmation: C11 judicial relationships and statute links, rev. 1.2

- **Reviewer:** Fable 5.2 (claude-fable-5-2). AI documentary review, not legal validation.
- **Date:** 2026-11-24.
- **Object:** `C11-JUDICIAL-QUALITY/relations/` at commits `c0c7362f` and `48da982c`, branch `claude/c11-judicial-quality`.
- **Sources read:** `data/text` as git objects at `ad77758d` of `/home/user/c7`. `holdout/` was not opened. Nothing was committed or pushed; the worktree was not modified.
- **Companion file:** `fable_review_relations_c11_v12_findings.csv` (11 entries).

## Verdict

**Not yet at the bar: one P2 remains open.** REL-10 and all the P3 items are closed. REL-05 is only partly closed: the four new adviser leads are right, but the lead rule misses declaratory overruling wording, and a search of the whole text corpus finds five more judgments whose own overrulings get no row at all.

Nothing in the outputs states a false legal status. The open item is undisclosed lost recall on the one relation the adviser queue exists for.

## 1. REL-05: adviser-review rows and the recall probe

### The five rows

All five are the court's own words, the best candidate is correct, and binding is marked honestly.

| Row | Citing judgment | Wording | Best candidate | Binding as marked |
| --- | --- | --- | --- | --- |
| TC-222df5c885ad | Parashotam Dass, para 32 | "does not lay down the correct law" | Shri Kant Sharma (held) | BOUND |
| TC-8ff2b7904d7c | Puttaswamy (2017), p.167 | "must be and is accordingly overruled" | ADM Jabalpur, (1976) 2 SCC 521 | LEAD, name matched at p.351 |
| TC-e50681fcc126 | Puttaswamy (2017), p.167 | "We also overrule" | Bhanudas Krishna Gawde, (1977) 1 SCC 834 | LEAD, name matched at p.21 |
| TC-c0a555a4670d | V. Sriharan, p.99 para 105 | "we specifically overrule the same" | Sangeet, 2013 (2) SCC 452 | LEAD, binding not established |
| TC-f2d2326781b3 | Joseph Shine, p.100 | "we overrule" | Sowmithri Vishnu, 1985 Supp SCC 137 | LEAD, name matched at p.27 |

- I checked each candidate citation against the page where the name and citation appear together.
- The two Puttaswamy leads sit in Chandrachud J.'s opinion and the Joseph Shine lead in Nariman J.'s concurrence; the rows do not say which opinion they come from.
- The reason on TC-3b178e403337 now points to the lead, and the README corrects the rev. 1.1 explanation.

### Own-voice overrulings still missed

I searched every text for overruling wording in the court's own voice (94 hits in 39 documents) and read each hit. These five judgments declare authorities overruled or wrongly decided and have no candidate row for it:

| Judgment | Page | Wording | Authorities |
| --- | --- | --- | --- |
| Ajmer Singh (1987) | 9 | "We hold that these two decisions do not lay down the correct law." | Kerala HC (Subramanian); Calcutta HC (Anand Singh Bisht) |
| Mafatlal Industries (1996) | 133; 105 | "must be held to have been wrongly decided"; "are accordingly overruled herewith" | Kanhaiyalal, [1959] S.C.R. 1350 |
| Puttaswamy (2017) | 432; 275-276 | "stands over-ruled"; "is overruled" | M.P. Sharma; Kharak Singh |
| Joseph Shine (2018) | 74; 154; 186 | "stand overruled"; "hereby stand overruled" | V. Revathi; W. Kalyani |
| Puttaswamy (2018) | 705; 820, 1065 | "does not lay down the correct law"; "are overruled" | Mohd Saeed Siddiqui; Yogendra Kumar |

- **Cause.** The lead rule needs an active first-person verb. Declaratory forms ("stand overruled", "is overruled", plural "do not lay down", "wrongly decided") are not covered.
- **Scale.** The build routes five authorities to an adviser; at least nine more are declared overruled in the held texts and are not routed.
- **Why it is still P2.** Ajmer Singh is a core military-law authority (set-off under s.428 CrPC for court-martial convicts) and uses the same cue phrase as the Parashotam row, in the plural. The Puttaswamy (2017) order of the Court is the operative overruling of M.P. Sharma and Kharak Singh. The README Limits section does not mention the gap.
- **Caveat.** The two Puttaswamy (2018) passages are from a separate opinion and a dissent. They should reach an adviser as leads, with the opinion named, not as proposals of what the Court held.

## 2. REL-10: statute labels

| Label | Rows read | Supported | Precision |
| --- | --- | --- | --- |
| PROVISION_HELD_INAPPLICABLE | 2 (all) | 2 | 100% |
| PROVISION_INTERPRETED | 5 (all) | 3 | 60% |
| PROVISION_CHALLENGED | 22 (all) | 20 | 91% |
| CHALLENGE_GROUND_CITED | 20 fresh | 16 | 80% |
| JURISDICTION_INVOKED | 20 of 44 | 20 as "jurisdiction, not a ground"; 8 as literally "invoked" | see note |

- **PROVISION_CHALLENGED.** The two misses are ss.437 and 439 CrPC in Vijay Madanlal: they are the comparator, and the PMLA twin conditions are what is challenged. Several supported rows report a challenge decided in an earlier case, which the label does not distinguish.
- **PROVISION_INTERPRETED.** One miss is the quoted row the README already discloses; the other reports that Khajoor Singh "concerned the interpretation of Article 226". With five rows build-wide this is a P3.
- **CHALLENGE_GROUND_CITED.** The four misses are Article 110 (pari materia mention), Article 33 (the saving provision), Article 226 (the ground is the basic structure) and Article 329A (the article itself was struck down).
- **JURISDICTION_INVOKED.** The move out of the ground label is right in every sampled row. The name overstates: in 12 of 20 the jurisdiction is excluded or preserved by a law, not invoked by a party.
- **Instrument.** One CRPC-1973 row concerns the 1898 Code ("Section 30 of the Code of Criminal Procedure as it stood then", from a 1955 decision).
- **Version.** All 11,076 rows are VERSION_NOT_ESTABLISHED.

I rate REL-10 closed. The residuals are V12-01 to V12-03, all P3.

## 3. P3 items

- **Major A. Hussain (REL-14): closed.** 16 edges resolve to the case across the AIR, SCC and name forms. Six stay unresolved because they name no party or print the citation before the name; none is mislinked.
- **review_inputs hashes (V11-02): closed.** Both row files are in `review_inputs/` with `SHA256SUMS`; the hashes match my files, and the re-measure script reproduces its outputs byte-identically from a clean copy.
- **README before/after table (V11-04): closed.** The build-wide table covers rev. 1.0, 1.1 and 1.2. The REL-08 wording is corrected.

## 4. Reproducibility and commit 48da982c

- `--check`: "CHECK OK: 6 outputs reproduce byte-identically" at both commits.
- Tests: 38 of 38 pass under python3.11 and under the venv (Python 3.13) at both commits.
- `OUTPUT_SHA256SUMS` and `review_inputs/SHA256SUMS` verify. No `__pycache__` is written.
- **48da982c** changes exactly three files: `tools/relations_c11.py`, `outputs/GRAPH_SUMMARY.json` and `outputs/OUTPUT_SHA256SUMS`. The other seven outputs are byte-identical to `c0c7362f`.
- `check_provenance.py` reports 0 violations on the relations folder and 0 new violations on its default roots (2 known, both in the baseline).
- The README, the dossier and two test assertions still contain the words "LEGALLY_VALIDATED" in prose or as a value that must never occur. Rule APR-1 covers JSON keys and CSV columns, and the checker passes.

## Requested action

1. Extend the unbound-lead rule to declaratory overruling wording under the same own-voice filters, and record the opinion author on each lead (REL-05).
2. Until then, state the gap in the README Limits section.
3. Optional P3s: rename JURISDICTION_INVOKED, tighten the two ground patterns, and handle "as it stood then" for the Code of Criminal Procedure.

## Limits of this review

- Text-layer reading only; no PDFs or page images were opened.
- The recall probe is a regular-expression search read by me. It finds explicit wording; it does not find implied overruling, and the list above is a floor.
- Verdicts are documentary (the court's own words, about the stated target), not opinions on legal effect.
