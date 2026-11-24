# C11 judicial relationships and statute links (rev. 1.1, after independent review)

**Status.** Evidence findings only.
- Every typed relation is a proposal. The status levels are AUTOMATED_DETECTED, DOCUMENTARY_CHECK_REQUIRED and LEGAL_INTERPRETATION_ADVISER_REVIEW. LEGALLY_VALIDATED is never assigned.
- No precedent is declared overruled.
- No provision version is assigned.
- Readings are text-layer readings by an AI agent (Claude Opus 5.5 subagent). They are not human-confirmed.

**Revision 1.1.** This revision answers the independent review `c10out/rev_c11/fable_review_relations_c11.md` (findings REL-01 to REL-19). Its design goal is fewer proposals, each correctly bound. Anything that is not clearly the court's own words, bound to the right authority, stays CITES at AUTOMATED_DETECTED or DOCUMENTARY_CHECK_REQUIRED.

## Reproduce

```
python3.11 -B -I tools/relations_c11.py --repo /home/user/c7          # build outputs/
python3.11 -B -I tools/remeasure_review_c11.py                         # re-score on the reviewer's sampled rows
python3.11 -B -I tools/relations_c11.py --repo /home/user/c7          # rebuild so OUTPUT_SHA256SUMS covers the re-measure files
python3.11 -B -I tools/relations_c11.py --repo /home/user/c7 --check  # byte-compare
python3.11 -B -I -m unittest discover -s tests -v                     # C11_SKIP_SLOW=1 skips the --check test
```

- **Dependencies.** Standard library only. Runs on Python 3.11+ (also tested with the venv, which is 3.13).
- **`-B`** prevents `tools/__pycache__` from being written (REL-19).

## Pinned inputs (read-only)

The SHA-256 of each input is in `GRAPH_SUMMARY.json` under `input_sha256`.

- `data/text` and `data/meta` at `ad77758d`, read as git objects;
- the amendment graph at `cfc52d57`, plus the C10 graph statuses;
- `cases_53.jsonl` at `21e73b83`, plus the C10 `CURATED_CASE_COPY_STATUS.csv`;
- C10 `JUDGMENT_RECONCILIATION.csv` (copy groups);
- the C10 HF relationships and legal issues (cross-checks);
- the review's sampled rows, used only by `remeasure_review_c11.py`.

`holdout/` was not opened.

## Outputs

| File | Content |
| --- | --- |
| `CASE_CITATION_GRAPH.csv` | One row per (citing judgment, cited authority). `relation` is always CITES. The row gives the target or raw string with candidates, the resolution method, page/paragraph, an excerpt, occurrences, the zone and treatment proposals |
| `TREATMENT_CANDIDATES.csv` | One row per cue word in the sentence carrying an anchor. `anchor` is CITATION_STRING, FOOTNOTE_MARKER or NAME_REFERENCE. Each row has the attribution class, a negation flag, the proposed relation (only for COURT_OWN_VOICE), the status and the reasons |
| `STATUTE_JUDGMENT_LINKS.csv` | One row per (judgment, instrument[, provision]). Each row has the normalised provision id (`printed_unit` keeps the wording as printed), the relationship, the bound cue, the amendment-graph edges, the version status, the IPC-to-BNS note and the C10 cross-check |
| `PRIORITY_TREATMENT_DOSSIER.md` | Priority cases. The verified quotations are re-checked on every build. The candidate tables are regenerated from the revised rules |
| `GRAPH_SUMMARY.json` | Counts by relation, status, method and attribution; resolution rates; input hashes |
| `REVIEW_REMEASURE_C11.csv` / `.json` | Before/after for each of the 223 rows sampled by the review, with precision per category |
| `OUTPUT_SHA256SUMS` | Hashes of every output, including this README and the re-measure files |

## Method (rev. 1.1)

### Citations
- **Running headers (REL-08).** The citing judgment's own SCR running headers (its own year and volume, for example `[2018] 11 S.C.R.` at a page top) are blanked, at the same length, before detection.
- **Footnotes (REL-03).** A footnote citation is tied to the body word carrying its marker (`Gawas Anil Madso4`). That marker is used both as the party-name window for resolution and as the treatment anchor. A footnote with no marker gets no party fallback and no treatment.
- **Resolution order:**
  1. target-metadata keys (neutral or reported citation, or a self-printed HC neutral citation);
  2. the C10-held curated crosswalk;
  3. learned parallel citations;
  4. case number plus party bigram;
  5. party bigram plus year plus court.
- **Fallback guards:**
  - a neighbour-contradiction check (`Indian Express Newspapers` is not `Express Newspapers`; REL-09);
  - the citation-mismatch guard applied to every reporter key in a cluster (REL-09);
  - one answer per citation string (REL-14: `Major A. Hussain, AIR 1998 SC 577` now resolves the same way everywhere).

### Treatment
A cue counts only in the sentence carrying the anchor, or in the next sentence when that sentence opens with a back-reference ("The facts of the aforesaid case ..."). A proposal needs all of these:
1. **Own voice.** Not reporter headnote matter: the editorial zone, plus bracketed report-page references such as `[594 E-H]` (REL-06). Not inside a quotation: unclosed quote marks or a lead-in, looking back up to 4,000 characters across pages. Not a submission: the sentence or the paragraph lead before the cue, including "contended", "stand of", "According to him", "in the view of" (REL-01). Not a report of another bench or lower forum.
2. **Tight binding.** Only connecting words about the cited authority lie between cue and anchor. Page furniture (signatures, headers, page numbers) is ignored.
3. **No other authority in the same sentence.** OVERRULES, REVERSES and QUESTIONS are exempt, but their binding must hold.
4. **No negation in the governing clause** (REL-02: "has not been discharged ... to show that ... is covered by").
5. **Direction.** The cited authority must be the patient, never the agent (REL-04). OVERRULES, REVERSES and QUESTIONS need a present or first-person form: "is accordingly overruled", "we (also) overrule", "does not lay down the correct law", "is per incuriam" (REL-05).
6. **Name references (REL-07).** A name reference needs a case marker ("(supra)", "case", "v.", "in ...") and a strong bigram (no corporate or generic words). It must not be running-header text, and its neighbouring words must not contradict the target ("Navtej Singh **Johar**").

**Status rules.**
- Only own-voice strong proposals go to LEGAL_INTERPRETATION_ADVISER_REVIEW.
- Reported treatment of a patient-bound target is DOCUMENTARY_CHECK_REQUIRED with no proposal.
- Everything else is AUTOMATED_DETECTED.

### Statute links
**Labels (REL-10).** A label says what the bound cue shows:

| Label | Status | When used |
| --- | --- | --- |
| STATUTE_MENTIONED | AUTOMATED_DETECTED | Statute-level rows |
| RELATIONSHIP_UNRESOLVED | AUTOMATED_DETECTED | Provision with no bound cue |
| PROVISION_QUOTED | AUTOMATED_DETECTED | Bound quotation cue |
| PARTY_INVOKED | AUTOMATED_DETECTED | "invoking / filed ... under" |
| CHARGED_OR_CONVICTED_UNDER | AUTOMATED_DETECTED | Charge or conviction under the provision |
| POWER_EXERCISED_UNDER | AUTOMATED_DETECTED | "in exercise of powers under" |
| PROVISION_CHALLENGED | DOCUMENTARY_CHECK_REQUIRED | "vires/validity of <provision>", or "<provision> is ultra vires" |
| CHALLENGE_GROUND_CITED | DOCUMENTARY_CHECK_REQUIRED | Constitution articles cited in a challenge |
| PROVISION_HELD_INAPPLICABLE | DOCUMENTARY_CHECK_REQUIRED | Bound inapplicability wording, excluding statutory "shall not apply" and contrasts |
| PROVISION_INTERPRETED | DOCUMENTARY_CHECK_REQUIRED | Bound interpretation wording, not when reporting another judge |
| HISTORICAL_VERSION_RELEVANT | DOCUMENTARY_CHECK_REQUIRED | Bound historical-version wording |

PROVISION_APPLIED has been withdrawn.

**Instruments (REL-11).** CRPC-1898 is used when the text prints 1898. CRPC-UNSPECIFIED is used when no year is printed and the judgment is dated before 1974-04-01. CRPC-1973 is never assigned before that date.

**Units (REL-12).** Units are normalised by instrument: rules use `r.`, Acts use `s.`.

**Versions.** All rows are VERSION_NOT_ESTABLISHED. No instrument has a complete amendment history in the graph, and `COMPLETE_HISTORY_INSTRUMENTS` is deliberately empty. The IPC-to-BNS switch of 1 July 2024 is noted and not assumed.

## Counts (this build)

**Citation graph**
- 23,240 edges, all CITES.
- **RESOLVED: 2,954**, a **12.7%** edge resolution rate. For SCC/SCR/INSC edges the rate is 14.3% (1,438 of 10,074).
- Rev. 1.0 had 24,000 edges and a 10.8% rate. The difference comes from blanking 6,335 of the citing judgments' own running headers before detection, and from footnote-marker binding.
- Unresolved edges, by reason:

| State | Edges |
| --- | --- |
| Not in corpus / no match | 16,766 |
| Case number only | 3,292 |
| Ambiguous | 119 |
| Cited page contradicts the target's citation | 82 |
| Candidate decided after the citing judgment | 25 |
| Conflicting matches | 2 |

- 8 remaining edges carry a key with the citing judgment's own SCR year and volume. These are genuine page citations with a page number on the same line.

**Treatment**
- 2,567 cue hits.
- Proposals: APPLIES 201, DISTINGUISHES 9, FOLLOWS 5, OVERRULES 1. The single OVERRULES proposal is Parashotam para 32 on Shri Kant Sharma.
- **Adviser queue: 1 row.** 218 rows are DOCUMENTARY_CHECK_REQUIRED.
- The two Puttaswamy (2018) rows that rev. 1.0 proposed as OVERRULES (McDowell, Binoy Viswam) are withdrawn: they are Shayara Bano's words, inside a quotation or introduced by "in the view of Justice Nariman".

**Statute links**
- 11,076 links in 2,430 judgments; all are VERSION_NOT_ESTABLISHED.
- By label: PARTY_INVOKED 539, CHARGED_OR_CONVICTED_UNDER 221, POWER_EXERCISED_UNDER 77, CHALLENGE_GROUND_CITED 754, PROVISION_CHALLENGED 28, PROVISION_QUOTED 138, PROVISION_HELD_INAPPLICABLE 14, PROVISION_INTERPRETED 8, HISTORICAL_VERSION_RELEVANT 7.
- CRPC-1898: 37 rows. CRPC-UNSPECIFIED: 5 rows.

## Re-measure on the reviewer's sampled rows

The reviewer's verdicts are taken as the truth for each row. Full detail is in `REVIEW_REMEASURE_C11.json`.

| Category | Before (supported / proposed) | After (supported / still proposed) | Unsupported withdrawn | Supported lost |
| --- | --- | --- | --- | --- |
| OVERRULES / QUESTIONS | 1 / 10 | 1 / 1 | 9 | 0 |
| Reported treatment at adviser review | 13 / 47 | 3 / 3, now DOCUMENTARY_CHECK_REQUIRED | 34 | 10 |
| APPLIES / FOLLOWS | 18 / 25 | 13 / 14 | 6 | 5 |
| DISTINGUISHES | 5 / 15 | 3 / 3 | 10 | 2 |
| Resolved edges (40) | 39 / 40 | 39 / 39 | 1 | 0 |
| Statute cue labels (30) | 9 / 30 | 7 / 7 | 21 | 2 |

**Notes on the edge rows:**
- Among the 20 unresolved edges, 8 are now resolved. All 7 are correct footnote-marker or key-consistency links, each checked against its body marker: Rajveender Singh Mallhi ×3, Sudesh Kumar Sharma ×2, Manoj K L, and Major A. Hussain. The eighth row was a spurious own-header edge, now removed.
- The Express Newspapers mislink is gone: 0 edges.

## Limits

- **Paragraph numbers** are heuristic.
- **Recall.** The cue lexicons and the binding rules trade recall for precision. Supported treatment is lost when it sits in reported, multi-authority, list or footnote-only contexts.
- **Unanchored targets.** A target not held in the corpus, and named without a citation string in the same sentence, cannot be anchored. One example: the Puttaswamy (2017) own-voice overruling of "ADM J1;1balpur" (OCR) and Bhanudas Gawde, whose footnote 213 citation is not in the text layer.
- **Copies outside this input** were not read: the official copies of Girish, Parashotam, Mullikote and Isaac held in the C5 working store or HF.
- **SCR renditions** are AWS e-SCR mirror copies, not signed originals.
