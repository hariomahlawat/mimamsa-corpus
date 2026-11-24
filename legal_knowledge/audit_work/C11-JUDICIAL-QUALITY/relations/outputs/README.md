# C11 judicial relationships and statute links

**Status.** Evidence findings only.
- Every typed relation is a proposal. The status levels are AUTOMATED_DETECTED, DOCUMENTARY_CHECK_REQUIRED and LEGAL_INTERPRETATION_ADVISER_REVIEW. LEGALLY_VALIDATED is never assigned.
- No precedent is declared overruled.
- No provision version is assigned.
- Readings are text-layer readings by an AI agent (Claude Opus 5.5 subagent). They are not human-confirmed.

## Reproduce

```
python3.11 -I tools/relations_c11.py --repo /home/user/c7          # build outputs/
python3.11 -I tools/relations_c11.py --repo /home/user/c7 --check  # rebuild in memory, byte-compare
python3.11 -I -m unittest discover -s tests -v                     # C11_SKIP_SLOW=1 skips the --check test
```

- **Dependencies.** Standard library only: no PyMuPDF, no jsonschema. Runs on Python 3.11+ in about 90 seconds.
- **Deterministic.** Every row id is a SHA-256 of its key.

## Pinned inputs (read-only)

The SHA-256 of each input is in `GRAPH_SUMMARY.json` under `input_sha256`.

- **Text layer and metadata:** `data/text`, `data/meta` at raw-data commit `ad77758d`. These are read as git objects, with no checkout. There are 4,259 judgment/order records, which is 3,951 distinct copies by sha; 3,944 of them have text.
- **Amendment graph:** `cfc52d57:legal_knowledge/audit_work/C9-LEGAL-EVIDENCE/STATUTORY/amendment_graph.csv`, plus the C10 statuses in `C10-RECONCILIATION/workstreams/statutory/amendment_graph_c10.csv`.
- **Curated cases:** `21e73b83:legal_knowledge/curated_originals/case_law/v0.9/cases_53.jsonl`, plus the C10 `CURATED_CASE_COPY_STATUS.csv`.
- **C10 judicial outputs:**
  - `JUDGMENT_RECONCILIATION.csv`, which supplies the copy groups, so renditions of one judgment form one target;
  - `JUDICIAL_TREATMENT_C10.csv`;
  - `TREATMENT_CITATION_HITS.csv`;
  - `HF_JUDGMENT_RELATIONSHIPS.csv`, used as a cross-check: all 168 J-to-J CITES edges are reproduced;
  - `HF_JUDGMENT_LEGAL_ISSUES.jsonl`, used as the statute cross-check.
- **Holdout.** `holdout/` was not opened.

## Outputs

| File | Content |
| --- | --- |
| `CASE_CITATION_GRAPH.csv` | One row per (citing judgment, cited authority). `relation` is always CITES. The row gives the target, or the raw string with candidates; the resolution method; the first page and paragraph; a 250-character excerpt; occurrences; the zone (BODY or REPORTER_EDITORIAL); and treatment proposals |
| `TREATMENT_CANDIDATES.csv` | One row per treatment cue word near a citation, or near a later party-name reference to a resolved target. Each row has the attribution class, a negation flag, the proposed relation (only for COURT_LIKELY), the status and the reasons |
| `STATUTE_JUDGMENT_LINKS.csv` | One row per (judgment, instrument[, provision]). Each row has a normalised provision id (for example `AA-1950:s.69`, `AR-1954:r.180`, `COI:art.226`, `PRA-1961:reg.173`, `ENT-1982:r.5`), the relationship, the cue, pages, the matched amendment-graph edges, the version status, the IPC-to-BNS note and the C10 cross-check |
| `PRIORITY_TREATMENT_DOSSIER.md` | Priority cases, with verified pinpoints and excerpts (quotations are re-checked on every build), graph counts, treatment candidates, contrary authority and open questions |
| `GRAPH_SUMMARY.json` | Counts by relation, status, method and attribution; resolution rates; top in-degree; input hashes |
| `OUTPUT_SHA256SUMS` | Hashes of every output, including this README |

## Method

**1. Citation detection.**
- Reporter citations: SCC (bracketed, parenthesised, plain and Supp), SCC OnLine, SCR (all layouts and Supp), AIR, INSC, JT, SLT, SCALE and SLR.
- HC neutral citations.
- Case numbers: Civil and Criminal Appeal, SLP(C), W.P.(C), CWP, SWP, OWP, WRIA and LPA.
- Parallel citations joined by `:` / `=` / `,` form one cluster.

**2. Resolution.** Conservative, with the first match winning:
1. Neutral citation or reported citation in the target's own metadata, or a self-printed HC neutral citation. Status AUTOMATED_DETECTED.
2. The C10-HELD curated crosswalk.
3. Parallel citations learned from clusters resolved at step 1. Any alias that maps to more than one target is discarded.
4. Case number plus a party-name bigram.
5. Party-name bigram plus year plus court.

Steps 2-5 give DOCUMENTARY_CHECK_REQUIRED. A match is left unresolved, and its candidates recorded, when it is:
- ambiguous (UNRESOLVED_AMBIGUOUS);
- a conflict (UNRESOLVED_CONFLICT);
- later than the citing judgment (UNRESOLVED_TEMPORAL_CONFLICT);
- a party/year match whose cited page differs from the target's known citation (UNRESOLVED_CITATION_MISMATCH);
- a case number only (UNRESOLVED_CASE_NUMBER_ONLY).

These references are dropped, because they are not citations:
- self-citations (688);
- the citing judgment's own case numbers (38,444);
- same-day connected matters (5,124).

**3. Treatment.** A stronger relation is proposed only when all of these hold:
- the cue is explicit (for example "does not lay down the correct law", "distinguishable", "is of no assistance", "squarely covered by", "we follow");
- the attribution is COURT_LIKELY.

No proposal is made when the wording is in any of these:
- reporter headnote or case-law matter (REPORTER_EDITORIAL);
- a quoted passage (QUOTED_PASSAGE), detected from unclosed quotation marks or a quotation lead-in with no closing marker;
- a party submission (PARTY_SUBMISSION_OR_MIXED);
- a report of what a lower forum did (LOWER_FORUM_REPORTED);
- a report of another court's act (REPORTED_TREATMENT_OF_TARGET);
- wording where the cited decision is the agent (TARGET_IS_AGENT);
- a past participle with no present or first-person voice (DIRECTION_UNCLEAR);
- the following sentence, with no back-reference (NEXT_SENTENCE_NO_BACK_REFERENCE);
- a cue too far from the citation (CUE_TOO_FAR);
- a negated cue.

Further rules:
- OVERRULES needs a citing court of equal or higher rank.
- OVERRULES, REVERSES and QUESTIONS always go to LEGAL_INTERPRETATION_ADVISER_REVIEW.
- Other proposals get DOCUMENTARY_CHECK_REQUIRED.

**4. Statute links.**
- The relationship defaults to STATUTE_MENTIONED (no provision) or RELATIONSHIP_UNRESOLVED (provision, no cue).
- PROVISION_QUOTED, APPLIED, INTERPRETED, CHALLENGED and HELD_INAPPLICABLE, and HISTORICAL_VERSION_RELEVANT, need a cue within 120/150 characters in the same sentence. Cues inside quotations or submissions are ignored, except for CHALLENGED and QUOTED.
- Provisions are linked to the amendment-graph instrument and the matching edge ids.
- **Version.** `version_status` is VERSION_NOT_ESTABLISHED for every row. No instrument is shown to have a complete amendment history in the graph: each carries NOT_LOCATED or unknown-scope rows, and IPC, CrPC and IEA carry only repeal rows. The set `COMPLETE_HISTORY_INSTRUMENTS` is empty and auditable.
- **IPC to BNS.** For IPC/CrPC/IEA/BNS/BNSS/BSA rows, the 1 July 2024 switch is noted and not assumed. The BNS commencement edge is NOT_LOCATED in the graph.

## Counts (this build)

**Citation graph.**
- 24,000 edges, all CITES.
- RESOLVED: 2,586, which is a **10.8%** edge resolution rate. For edges carrying an SCC, SCR or INSC string the rate is 13.8% (1,490 of 10,794). The rate is low mainly because most cited authorities are not in the corpus.
- UNRESOLVED: 17,970.
- Other target states: CASE_NUMBER_ONLY 3,297, CITATION_MISMATCH 63, AMBIGUOUS 55, TEMPORAL_CONFLICT 27, CONFLICT 2.
- 262 distinct resolved targets.
- Top in-degree: Bijender Singh (2025 INSC 549) 452, Dharamvir 352, Delhi HC Gawas Anil Madso 127.

**Treatment.**
- 3,550 cue hits.
- Proposals: APPLIES 198, DISTINGUISHES 41, FOLLOWS 30, QUESTIONS 7, OVERRULES 3. The OVERRULES proposals are Parashotam to Shri Kant Sharma, and two from Puttaswamy (2018) concerning McDowell and Binoy Viswam.
- 57 rows are at adviser review.

**Statute links.**
- 11,067 links in 2,430 judgments.
- 515 match an amendment-graph edge.
- All are VERSION_NOT_ESTABLISHED.

## Limits

- **Paragraph numbers** in the graph are heuristic.
- **Cue lexicons** miss implicit treatment, and absence of a hit is not proof of absence.
- **Party-bigram fallback** can mislink cases with generic party names. Those rows are DOCUMENTARY_CHECK_REQUIRED.
- **Copies outside this input** were not read: the official copies of Girish, Parashotam, Mullikote and Isaac held in the C5 working store or HF.
- **SCR renditions** are AWS e-SCR mirror copies, not signed originals.
