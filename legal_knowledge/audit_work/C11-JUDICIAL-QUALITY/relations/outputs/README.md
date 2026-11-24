# C11 judicial relationships and statute links (rev. 1.3, after three independent reviews)

**Status.** Evidence findings only.
- Every typed relation is a proposal. The status levels are AUTOMATED_DETECTED, DOCUMENTARY_CHECK_REQUIRED and LEGAL_INTERPRETATION_ADVISER_REVIEW. LEGALLY_VALIDATED is never assigned.
- No precedent is declared overruled.
- No provision version is assigned.
- Readings are text-layer readings by an AI agent (Claude Opus 5.5 subagent). They are not human-confirmed.

**Revision history.**
- **Rev. 1.1** answered review round 1 (`fable_review_relations_c11.md`, REL-01 to REL-19). The design goal was fewer proposals, each correctly bound.
- **Rev. 1.2** answers round 2 (`fable_review_relations_c11_v11.md`). It closes REL-05 (unbound own-voice overruling leads) and REL-10 (own-voice filter and jurisdiction articles for statute labels). It also handles REL-14 per case, V11-01 and V11-02.
- **Rev. 1.3** answers round 3 (`fable_review_relations_c11_v12.md`). It extends REL-05 leads to declaratory wording, records the opinion on every row, adds a corpus probe of own-voice overruling wording (`OVERRULING_PROBE_C11.csv`), renames JURISDICTION_INVOKED to JURISDICTION_REFERENCED (V12-01) and handles "as it stood then" for the CrPC (V12-03).

## Reproduce

```
python3.11 -B -I tools/relations_c11.py --repo /home/user/c7          # build outputs/
python3.11 -B -I tools/remeasure_review_c11.py                         # re-score on both reviewers' sampled rows
python3.11 -B -I tools/relations_c11.py --repo /home/user/c7          # rebuild so OUTPUT_SHA256SUMS covers the re-measure files
python3.11 -B -I tools/relations_c11.py --repo /home/user/c7 --check  # byte-compare
python3.11 -B -I -m unittest discover -s tests -v                     # C11_SKIP_SLOW=1 skips the --check test
```

- **Dependencies.** Standard library only. Runs on Python 3.11+ (also tested with the venv, which is Python 3.13).
- **`-B`** stops `__pycache__` from being written.
- **Re-measure inputs.** `remeasure_review_c11.py` reads the reviewers' row files from `review_inputs/`. It checks their SHA-256 against the values in the script, also listed in `review_inputs/SHA256SUMS`, and fails on a mismatch:
  - round 1: `f6747de1f903563f90bf0d2f4629e196f7a4fa8791563720dfaa1559baf1ff82`
  - round 2: `16774fb221a58f6d7280ab048ffd3a5d7f648742323ca7adf8357a4f07687c5b`

## Pinned inputs (read-only)

The SHA-256 of each input is in `GRAPH_SUMMARY.json` under `input_sha256`.

- `data/text` and `data/meta` at `ad77758d`, read as git objects;
- the amendment graph at `cfc52d57`, plus the C10 graph statuses;
- `cases_53.jsonl` at `21e73b83`, plus the C10 `CURATED_CASE_COPY_STATUS.csv`;
- C10 `JUDGMENT_RECONCILIATION.csv`;
- the C10 HF relationships and legal issues;
- `review_inputs/` (re-measure only).

`holdout/` was not opened.

## Outputs

| File | Content |
| --- | --- |
| `CASE_CITATION_GRAPH.csv` | One row per (citing judgment, cited authority). `relation` is always CITES. Treatment proposals are listed per edge, and unbound leads are marked `OVERRULES_LEAD_UNBOUND` |
| `TREATMENT_CANDIDATES.csv` | One row per cue word in the sentence carrying an anchor (CITATION_STRING, FOOTNOTE_MARKER or NAME_REFERENCE), plus first-person overruling leads. Columns include attribution, `binding_status`, `lead_target_raw`, proposed relation, status and reasons |
| `STATUTE_JUDGMENT_LINKS.csv` | One row per (judgment, instrument[, provision]). Each row has the normalised provision id and `printed_unit`, the relationship, the bound cue, the amendment-graph edges, the version status, the IPC-to-BNS note and the C10 cross-check |
| `PRIORITY_TREATMENT_DOSSIER.md` | Priority cases. The verified quotations are re-checked on every build. The candidate tables are regenerated |
| `OVERRULING_PROBE_C11.csv` | New in rev. 1.3. Every own-voice overruling hit in the corpus: page, wording, disposition (new lead, covered by an existing adviser row, or excluded with the reason), the adviser rows on that page, and an excerpt |
| `GRAPH_SUMMARY.json` | Counts, resolution rates, input hashes. `treatment.adviser_rows` lists every adviser row; `treatment.overruling_probe` gives the probe dispositions |
| `REVIEW_REMEASURE_C11.csv` / `.json` | Before/after for every row sampled in review rounds 1 (223) and 2 (132). The JSON records the hashes of the input files |
| `OUTPUT_SHA256SUMS` | Hashes of every output, including this README and the re-measure files |

## Method

### Citations
- **Running headers.** The citing judgment's own SCR running headers (its own year and volume) are blanked, at the same length, before detection.
- **Footnotes.** A footnote citation is tied to the body word carrying its marker (`Gawas Anil Madso4`).
- **Resolution order:**
  1. target-metadata keys;
  2. the C10-held curated crosswalk;
  3. learned parallel citations;
  4. case number plus party bigram;
  5. party bigram plus year plus court.
- **Fallback guards:**
  - a neighbour-contradiction check;
  - a citation-mismatch guard on every reporter key in a cluster;
  - generic words such as "court martial" are never party evidence.
- **Consistency (REL-14).** This works per case, not per string:
  - An ambiguous occurrence is resolved when the case-name segment just before it (the last 90 characters) names exactly one candidate's distinctive party word (PARTY_NAME_TIEBREAK).
  - A string that resolves cleanly elsewhere is applied to its ambiguous occurrences.
  - Conflicting unnamed fallback answers stay ambiguous.
  - Result: Major A. Hussain resolves the same way whenever his name is printed, under both "AIR 1998 SC 577" and "(1998) 1 SCC 537". The three occurrences with no party name stay unresolved.

### Treatment
A cue counts only in the sentence carrying the anchor, or in the next sentence through an explicit back-reference. A proposal needs all of these:
1. **Own voice.** Not reporter matter. Not a quotation: unclosed or unbalanced curly quotes looking back up to 4,000 characters, or a quotation lead-in, or an "(emphasis supplied)" closing the passage after the cue. Not a submission, in the sentence or the paragraph lead. Rev. 1.2 adds "grievance raised ... was that", "the case of the petitioner is that" and "it is pointed out". Not a report of another bench or lower forum.
2. **Tight binding** to the anchor.
3. **No other authority in the sentence**, except for strong relations.
4. **No negation** in the governing clause.
5. **Direction.** The cited authority must be the patient. Strong relations need a present or first-person form.

**Unbound adviser leads (REL-05, rev. 1.2).** A first-person overruling sentence also reaches LEGAL_INTERPRETATION_ADVISER_REVIEW as a lead when the target binding fails, is distant, or is blocked by a negation word elsewhere in the clause. This covers "... must be and is accordingly overruled", "we specifically overrule the same" and "We also overrule ...".
- The sentence must not be a quotation, a submission or reporter matter.
- The citing court must be the Supreme Court, or the same court as the target.
- The row is marked `COURT_OWN_VOICE_UNBOUND_LEAD` and records the raw target text (`lead_target_raw`).
- It records the best candidate citation: one in the sentence, or a citation elsewhere in the judgment whose name segment best matches the raw text, or the nearest citation in the paragraph.
- `binding_status` says that binding is NOT established.

**Declaratory leads (rev. 1.3).** The lead rule also covers declaratory wording: "stand(s) overruled", "hereby stand overruled", "is/are (hereby/accordingly) overruled (herewith)", "do(es) not lay down the correct law/position", "must be held to have been wrongly decided", "have also been wrongly decided" and "is no longer good law / is not good law".
- **Filters.** The same own-voice filters apply: not reporter matter (including per-opinion headnote blocks inside long SCR reports), not a quotation (stricter test for leads), not a submission, and not a report ("overruled by/in <another decision>", or another court's view). The citing court must be the Supreme Court.
- **Targets.** Each lead is tied to the authority named in the same sentence or, through a back-reference ("these two decisions"), in the preceding sentence. Failing that, the name is matched elsewhere in the judgment (full name phrase with initials, then single words, split per named authority). One row is written per authority, up to 4.
- **Opinion.** Every row records the opinion it comes from, using the SCR page headers ("[ASHOK BHUSHAN, J.]"), "ORDER OF THE COURT" headings and "(Dissenting)" markers:
  - SOLE_OPINION;
  - LEAD_OPINION (the first opinion in the report);
  - ORDER_OF_THE_COURT;
  - SEPARATE_OPINION;
  - DISSENT;
  - OPINION_NOT_IDENTIFIED.
- **Separate and dissenting opinions.** Overruling wording in a separate or dissenting opinion goes to adviser review as SEPARATE_OPINION_LEAD or DISSENT_OPINION_LEAD with **no proposal**, because such an opinion does not itself overrule. Other proposals that fall in a dissent are withdrawn.

**Status rules.**
- LEGAL_INTERPRETATION_ADVISER_REVIEW: own-voice strong proposals, unbound leads, and separate/dissent leads (no proposal).
- DOCUMENTARY_CHECK_REQUIRED: reported treatment of a patient-bound target, with no proposal.
- AUTOMATED_DETECTED: everything else.

### Statute links
**Labels.** A label says what the bound cue shows:

| Label | Status | When used |
| --- | --- | --- |
| STATUTE_MENTIONED | AUTOMATED_DETECTED | Statute-level rows |
| RELATIONSHIP_UNRESOLVED | AUTOMATED_DETECTED | Provision with no bound cue |
| PROVISION_QUOTED | AUTOMATED_DETECTED | Bound quotation cue |
| PARTY_INVOKED | AUTOMATED_DETECTED | "invoking / filed ... under" |
| CHARGED_OR_CONVICTED_UNDER | AUTOMATED_DETECTED | Charge or conviction under the provision |
| POWER_EXERCISED_UNDER | AUTOMATED_DETECTED | "in exercise of powers under" |
| JURISDICTION_REFERENCED | AUTOMATED_DETECTED | Articles 32, 136, 226 and 227 in a challenge context, unless the cue is "violative of / in violation of". The jurisdiction may be invoked, excluded or preserved; renamed from JURISDICTION_INVOKED in rev. 1.3 |
| PROVISION_CHALLENGED | DOCUMENTARY_CHECK_REQUIRED | "vires/validity of <provision>", or "<provision> is ultra vires" with the provision as subject |
| CHALLENGE_GROUND_CITED | DOCUMENTARY_CHECK_REQUIRED | Other Constitution articles in a challenge context |
| PROVISION_HELD_INAPPLICABLE | DOCUMENTARY_CHECK_REQUIRED | See the own-voice rule below |
| PROVISION_INTERPRETED | DOCUMENTARY_CHECK_REQUIRED | See the own-voice rule below |
| HISTORICAL_VERSION_RELEVANT | DOCUMENTARY_CHECK_REQUIRED | Bound historical-version wording |

**Own-voice rule for HELD_INAPPLICABLE and INTERPRETED (REL-10, rev. 1.2).** Both now need:
- the provision as the grammatical subject of the cue (only auxiliaries or adverbs in between);
- no quotation;
- no submission, in the sentence or the paragraph lead;
- no report of another court or judge ("Justice", "was in issue", "with reference to", "it was held").

"not available" no longer counts, which removes "an officer of the rank ... was not available".

Where precision could not be made reliable, rows were demoted to RELATIONSHIP_UNRESOLVED: HELD_INAPPLICABLE fell from 14 to 2 and INTERPRETED from 8 to 5.

**Instruments and units.** CRPC-1898 and CRPC-UNSPECIFIED are used before 1974-04-01. From rev. 1.3, CRPC-UNSPECIFIED is also used when the mention says "as it stood (then)" (V12-03; for example SL-7eb3f7c04030, Budhan Choudhry 1955). Units are normalised by instrument (rules `r.`, Acts `s.`).

**Versions.** All rows are VERSION_NOT_ESTABLISHED, and `COMPLETE_HISTORY_INSTRUMENTS` is deliberately empty. The IPC-to-BNS switch of 1 July 2024 is noted and not assumed.

## Build-wide counts across revisions

| | rev. 1.0 | rev. 1.1 | rev. 1.2 | rev. 1.3 |
| --- | --- | --- | --- | --- |
| Edges | 24,000 | 23,240 | 23,222 | 23,222 |
| Resolved (rate) | 2,586 (10.8%) | 2,954 (12.7%) | 3,008 (13.0%) | 3,008 (13.0%) |
| UNRESOLVED_AMBIGUOUS | 55 | 119 | 46 | 46 |
| APPLIES proposals | 198 | 201 | 195 | 195 |
| DISTINGUISHES proposals | 41 | 9 | 9 | 9 |
| FOLLOWS proposals | 30 | 5 | 4 | 4 |
| QUESTIONS proposals | 7 | 0 | 0 | 0 |
| OVERRULES proposals | 3 | 1 | 5 | 16 (1 bound + 15 unbound leads) |
| Separate/dissent overruling leads (no proposal) | – | – | – | 14 (12 separate, 2 dissent) |
| LEGAL_INTERPRETATION_ADVISER_REVIEW rows | 57 | 1 | 5 | 30 |
| DOCUMENTARY_CHECK_REQUIRED treatment rows | 269 | 218 | 211 | 211 |
| PROVISION_APPLIED | 303 | withdrawn | withdrawn | withdrawn |
| PROVISION_CHALLENGED | 284 | 28 | 22 | 22 |
| CHALLENGE_GROUND_CITED / JURISDICTION_REFERENCED | n/a | 754 / n/a | 695 / 44 | 695 / 44 |
| PROVISION_HELD_INAPPLICABLE | 20 | 14 | 2 | 2 |
| PROVISION_INTERPRETED | 172 | 8 | 5 | 5 |
| PROVISION_QUOTED | 146 | 138 | 140 | 140 |
| PARTY_INVOKED / CHARGED_OR_CONVICTED_UNDER / POWER_EXERCISED_UNDER | n/a | 539 / 221 / 77 | 550 / 223 / 80 | 550 / 223 / 80 |
| CRPC-1898 / CRPC-UNSPECIFIED | n/a | 37 / 5 | 37 / 5 | 37 / 7 |

### Adviser queue (rev. 1.3): 30 rows

The full list is in `GRAPH_SUMMARY.json` under `treatment.adviser_rows`. A lead's target is a best candidate: binding is not established unless the row says BOUND.

**Court's own voice: 16 rows, OVERRULES proposed.**
- **Parashotam (2023), p.17, para 32.** "does not lay down the correct law" → Shri Kant Sharma. BOUND; sole opinion.
- **Ajmer Singh (1987), p.9.** "We hold that these two decisions do not lay down the correct law" → Kerala HC (Subramanian) and Calcutta HC (Anand Singh Bisht). Raw text only: neither HC report citation is detected. Sole opinion.
- **Mafatlal (1996):**
  - p.105, two rows: "must be held to have been decided wrongly and are accordingly overruled herewith". Raw text only.
  - p.133, two rows: Kanhaiyalal, [1959] S.C.R. 1350 ("must be held to have been wrongly decided"; "have also been wrongly decided").
  - All four are in the opinion labelled LEAD_OPINION (AHMADI) from the page headers.
- **Puttaswamy (2017), lead opinion (Chandrachud J.):**
  - p.167, ADM Jabalpur, (1976) 2 SCC 521;
  - p.167, Bhanudas Gawde, (1977) 1 SCC 834;
  - p.275, M.P. Sharma, AIR 1954 SC 300;
  - p.276, Kharak Singh, (1964) 1 SCR 332.
- **Puttaswamy (2017), ORDER_OF_THE_COURT, p.432.** M.P. Sharma, 1954 SCR 1077.
- **Joseph Shine (2018), p.74, lead opinion (Dipak Misra CJI), two rows.** Sowmithri Vishnu (1985 Supp SCC 137) and V. Revathi ((1988) 2 SCC 72).
- **V. Sriharan (2015), p.99.** Sangeet, 2013 (2) SCC 452.
- **Union of India (2000), p.19.** "is overruled". Raw text only; this is a plea/objection being overruled, so the adviser should expect to reject it.
- **Shatrughan Chauhan (2014), p.54.** Vatheeswaran, (1983) 2 SCC 68. The wording may report Triveniben; adviser to check.

**Separate opinion, no proposal: 12 rows.**
- Joseph Shine: Nariman J. p.100; Chandrachud J. pp.109 and 154 (×2); Indu Malhotra J. p.186 (×2).
- Puttaswamy (2018): Ashok Bhushan J. pp.705 and 1065, each ×2 (Mohd Saeed Siddiqui, Yogendra Kumar).
- Supreme Court AoR (2015): Lokur J. pp.783 and 802.

**Dissent, no proposal: 2 rows.** Puttaswamy (2018), Chandrachud J., p.820, ×2.

### Corpus probe of own-voice overruling wording (`OVERRULING_PROBE_C11.csv`)

The probe found 74 hits for the lead wording across the corpus:

| Disposition | Hits |
| --- | --- |
| New adviser lead | 21 |
| Covered by an existing adviser row or a lead in the same sentence | 4 |
| Excluded, reporter headnote | 14 |
| Excluded, quoted passage | 12 |
| Excluded, submission | 7 |
| Excluded, High Court judgment | 16 |

Every excluded Supreme Court hit was checked on its probe excerpt, and Balkrishna Ram was read in full. They are correctly excluded except the known misses listed under Limits. Examples of correct exclusions:
- Balkrishna Ram p.7 quotes the Allahabad Full Bench.
- Shatrughan p.68 quotes Triveniben.
- Raghunathrao p.30 reports Kesavananda.
- Counsel's arguments in Ex-Navy Artificers p.23, Tamil Nadu Medical Officers p.39 and Union of India (2001) p.29.

**Rev. 1.1 statement corrected.** Rev. 1.1 said the Puttaswamy (2017) target "cannot be anchored". That was wrong: the passage is anchored on (1976) 2 SCC 521. The real cause was that the anchored cue row TC-3b178e403337 carries IR Coelho's statement ("this Court took the view that ADM Jabalpur has been impliedly overruled"). That statement is correctly classed as reported. Meanwhile the court's own first-person sentence just before it had no anchored candidate. Rev. 1.2 records that sentence as lead TC-8ff2b7904d7c, and the reason on TC-3b178e403337 now points to the lead.

**REL-08 wording corrected.** 8 edges still carry a key with the citing judgment's own SCR year and volume. Most are residue of the judgment's own header or first-page citation, not genuine page citations; one is a real citation in the same volume. All remain UNRESOLVED, so none becomes a link.

## Re-measure on the reviewers' sampled rows

The reviewers' verdicts are taken as the truth for each row. Full detail is in `REVIEW_REMEASURE_C11.json`.

**Round 1 (223 rows; rev. 1.0 outputs reviewed):**

| Category | Before (supported / proposed) | After (supported / still proposed) | Unsupported withdrawn | Supported lost |
| --- | --- | --- | --- | --- |
| OVERRULES / QUESTIONS | 1 / 10 | 1 / 1 | 9 | 0 |
| Reported treatment at adviser review | 13 / 47 | 3 / 3 (now DOCUMENTARY_CHECK_REQUIRED) | 34 | 10 |
| APPLIES / FOLLOWS | 18 / 25 | 12 / 12 | 7 | 6 |
| DISTINGUISHES | 5 / 15 | 3 / 3 | 10 | 2 |
| Resolved edges | 39 / 40 | 39 / 39 | 1 | 0 |
| Statute cue labels | 9 / 30 | 6 / 6 | 21 | 3 |

Of the 10 ambiguous edges in the round-1 sample:
- 9 now resolve. All are correct footnote-marker or per-case links (Rajveender Singh Mallhi ×3, Sudesh Kumar Sharma ×2, Manoj K L, Major A. Hussain ×2).
- 1 spurious own-header edge is removed.

**Round 2 (132 rows; rev. 1.1 outputs reviewed):**

| Category | Before (supported / proposed) | After (supported / still proposed) | Unsupported withdrawn | Supported lost |
| --- | --- | --- | --- | --- |
| Missed own-voice overruling (recall probe) | 0 of 2 at adviser review | 2 of 2 at adviser review (as leads) | – | – |
| Adviser OVERRULES | 1 / 1 | 1 / 1 | 0 | 0 |
| APPLIES / FOLLOWS | 29 / 30 | 29 / 29 | 1 (TC-715eb9003ade, claimant's grievance) | 0 |
| DISTINGUISHES | 6 / 6 | 6 / 6 | 0 | 0 |
| Reported treatment at documentary check | 3 / 3 | 3 / 3 | 0 | 0 |
| Resolved edges | 30 / 30 | 29 / 29 | 0 | 1 (case-number edge, now case-number-only) |
| PARTY_INVOKED / CHARGED / POWER / QUOTED | 14 / 14 | 14 / 14 | 0 | 0 |
| CHALLENGE_GROUND_CITED | 8 / 12 | 8 / 8 | 4 (now JURISDICTION_REFERENCED) | 0 |
| PROVISION_CHALLENGED | 3 / 4 | 2 / 2 | 1 | 1 |
| PROVISION_HELD_INAPPLICABLE | 4 / 12 | 1 / 1 | 8 | 3 |
| PROVISION_INTERPRETED | 4 / 8 | 2 / 3 | 3 | 2 |
| CRPC-1898 / CRPC-UNSPECIFIED | 10 / 10 | 10 / 10 | 0 | 0 |

TC-22a1de5f2e85, the quoted Nagaraj passage, is no longer proposed: it is now classed as QUOTED_PASSAGE through the balanced-quote check.

## Limits

- **Paragraph numbers** are heuristic.
- **Recall.** The rules trade recall for precision. Supported treatment is lost in reported, multi-authority, list and footnote-only contexts.
- **Unbound leads** carry a best-candidate target that an adviser must confirm. Opinion labels come from SCR page headers, so the first pages of a new opinion can still carry the previous judge's label. "LEAD_OPINION" means the first opinion in the report, not necessarily the majority.
- **Known misses in the own-voice overruling probe (REL-05 residual):**
  - Puttaswamy (2017) ORDER OF THE COURT (ii) on Kharak Singh: "stands ... over-ruled" is split by page-break debris across pp.432-433. Kharak Singh is still covered by the p.276 lead.
  - Puttaswamy (2017) separate opinions at p.399 (Bobde J.) and pp.354/373: excluded as quoted or headnote because of OCR quote marks and in-report headnote blocks.
  - High Court judgments (16 hits) are excluded wholesale. A High Court Full Bench overruling the same court's earlier Division Bench is not separated out and is not routed.
  - Implied overruling, and wording outside the lead patterns, is not detected. The probe is a floor, not a full recall measure.
- **PROVISION_INTERPRETED** still keeps one quoted row (SL-0a37ec5cac0c). The label has 5 rows build-wide.
- **Copies outside this input** were not read: the official copies of Girish, Parashotam, Mullikote and Isaac held in the C5 working store or HF.
- **SCR renditions** are AWS e-SCR mirror copies, not signed originals.
