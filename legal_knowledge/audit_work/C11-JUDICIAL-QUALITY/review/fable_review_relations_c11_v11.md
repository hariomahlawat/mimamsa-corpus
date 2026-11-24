# Confirmation review: C11 judicial relationships and statute links, rev. 1.1

- **Reviewer:** Fable 5.2 (claude-fable-5-2). AI documentary review, not legal validation.
- **Date:** 2026-11-24.
- **Object:** `C11-JUDICIAL-QUALITY/relations/` at commit `b262175f`, branch `claude/c11-judicial-quality`.
- **Sources read:** `data/text` and `data/meta` as git objects at `ad77758d` of `/home/user/c7`. `holdout/` was not opened. Nothing was committed or pushed; the worktree was not modified.
- **Companion files:** `fable_review_relations_c11_v11_rows.csv` (132 rows), `fable_review_relations_c11_v11_findings.csv` (19 entries).

## Verdict

**Accept with two open items.** The treatment proposals and citation resolution are now reliable on rows I had not seen before. Eleven of the fourteen round-1 findings are closed.

The two open items are:

- **Own-voice overruling is still missed (REL-05, P2).** A fresh probe found a second case beside Puttaswamy (2017).
- **Three statute labels still overstate (REL-10, P2).** HELD_INAPPLICABLE, INTERPRETED and CHALLENGE_GROUND_CITED are right about half the time or less.

Neither puts a false legal status in the outputs. The first is lost recall on the relation that matters most; the second is noise in a documentary-check queue.

## Measured precision on fresh rows

Samples are the lowest `sha256('C11-REL-REV2' + row id)`, excluding all 223 row ids from the round-1 file.

| Category | Fresh rows | Supported | Precision | Round 1 |
| --- | --- | --- | --- | --- |
| OVERRULES / QUESTIONS and adviser review | 0 fresh (1 row exists, seen before) | 1 of 1 | n/a | 10% |
| APPLIES / FOLLOWS proposals | 30 | 29 | 97% | 72% |
| DISTINGUISHES proposals (all remaining) | 6 | 6 | 100% | 33% |
| Resolved citation edges | 30 | 30 | 100% | 97.5% |
| Cue-based statute labels | 30 | 20 | 67% | 30% |
| CRPC-1898 / CRPC-UNSPECIFIED rows | 10 | 10 | 100% | n/a |

Notes on the samples:

- **Adviser tier.** The build has one adviser-review row and three reported-treatment rows at documentary check. All four were in my round-1 sample, so there is nothing fresh to measure; all four are supported.
- **DISTINGUISHES.** The build has 9 proposals; 3 were in round 1, so 6 are fresh, not 9.
- **APPLIES / FOLLOWS.** 20 of the 30 rows are one Delhi HC template ("The issue is covered by ... Gawas Anil Madso"). The other ten are 9 of 10. The sample holds 29 APPLIES and 1 FOLLOWS.
- **Resolved edges.** 13 party/year/court, of which 10 are footnote-marker links new in rev. 1.1; 5 key-consistency; 5 parallel-learned; 3 case-number; 2 curated; 1 reporter and 1 neutral metadata. Each footnote link was checked against the body word carrying the marker.

### Statute labels in detail

| Label | Fresh rows read | Supported |
| --- | --- | --- |
| PARTY_INVOKED | 4 | 4 |
| CHARGED_OR_CONVICTED_UNDER | 4 | 4 |
| POWER_EXERCISED_UNDER | 4 | 4 |
| PROVISION_QUOTED | 2 | 2 |
| PROVISION_CHALLENGED | 4 | 3 |
| CHALLENGE_GROUND_CITED | 12 | 8 |
| PROVISION_INTERPRETED | 8 (every row) | 4 |
| PROVISION_HELD_INAPPLICABLE | 14 (every row) | 4 |

The 30-row sample takes the first 4 rows per label (2 for QUOTED); the extra rows for the last three labels are a supplement, listed separately in the rows file. No version is asserted anywhere: all 11,076 rows are VERSION_NOT_ESTABLISHED.

## Disposition of round-1 findings

| Finding | Disposition | What I checked |
| --- | --- | --- |
| REL-01 quoted/submission OVERRULES | Closed | One adviser row left, supported; README corrected |
| REL-02 inverted Narsingh APPLIES | Closed | 0 proposals; 16 of 17 rows now flagged negated |
| REL-03 footnote adjacency | Closed | 0 of 24 Dharamvir proposals run on to Gawas; "doubted" rows gone |
| REL-04 direction inverted | Closed | 3 reported rows left, all about the stated target, no proposal |
| REL-05 missed own-voice overruling | **Open** | See below |
| REL-06 DISTINGUISHES | Closed | 6 of 6 fresh; S.P. Gupta headnotes now editorial |
| REL-07 name references | Closed | No weak bigram anchors remain |
| REL-08 running headers | Closed | 717 edges down to 8, all unresolved |
| REL-09 Express Newspapers | Closed | 0 edges to the wrong target |
| REL-10 statute labels | **Partly closed** | See below |
| REL-11 CrPC 1898 | Closed | 0 pre-1974 CRPC-1973 rows; 10 of 10 sampled |
| REL-12 unit normalisation | Closed | AR-1954 all `r.`, AA-1950 all `s.` |
| REL-13 dossier tables | Closed | Regenerated; 26 of 26 quotations still verify |
| REL-14 A. Hussain consistency | Partly closed | AIR string resolves; SCC string still ambiguous in 5 edges |

### REL-05, still open

- **Puttaswamy (2017), TC-3b178e403337.** "ADM Jabalpur must be and is accordingly overruled. We also overrule ..." is still classed as a report of another court, now at AUTOMATED_DETECTED. The README discloses the miss but says the target cannot be anchored; the row is in fact anchored on (1976) 2 SCC 521.
- **V. Sriharan (2015), TC-c0a555a4670d, new.** "We are, therefore, not in agreement with the opinion expressed by this Court in Sangeet ... 2013 (2) SCC 452 ... and we specifically overrule the same." The tool rejects it because the cue is 208 characters from the citation and a negation is in scope.

Both are Constitution Bench overrulings in the court's own first person. With one adviser row in the whole build, the tool now finds Parashotam and nothing else.

### REL-10, partly closed

- **HELD_INAPPLICABLE.** Three rows come from the cue "an officer of the rank of the petitioner was not available". Four are petitioners' arguments or submissions.
- **INTERPRETED.** Half are inside quotations or report another court's interpretation, which the README says are excluded.
- **CHALLENGE_GROUND_CITED.** 77 of the 754 rows are Articles 226, 227, 32 or 136, which in the rows read are the jurisdiction invoked, not a ground.

### Smaller points

- **REL-08.** Six of the eight remaining own-volume edges are still the judgment's own header or first-page citation, not "genuine page citations" as the README says. They are unresolved and harmless.
- **REL-14.** The README claim "resolves the same way everywhere" holds per citation string, not per case.
- **V11-01 (P3).** One fresh APPLIES proposal narrates the claimant's case (TC-715eb9003ade). TC-22a1de5f2e85, a quoted Nagaraj passage, is still proposed; the README already counts it as unsupported and kept.
- **V11-02 (P3).** The re-measure script reads my round-1 rows file from the session scratchpad and does not record its hash. From another location it fails; with `--review` it reproduces byte-identically.

## Reproducibility

- `--check`: "CHECK OK: 6 outputs reproduce byte-identically", 78 s.
- Tests: 35 of 35 pass under python3.11 and under the venv (Python 3.13).
- `OUTPUT_SHA256SUMS` verifies. With `-B` no `__pycache__` is written.
- All runs were in a disposable copy under `rev_rel2/`.

## Is recall loss honestly stated?

Mostly yes.

- The README table reports supported rows lost on my round-1 sample: 10 reported-treatment, 5 APPLIES/FOLLOWS, 2 DISTINGUISHES, 2 statute. I matched these to the re-measure CSV row by row.
- The Limits section says the rules trade recall for precision and names the contexts where supported treatment is lost.
- Two things are understated. Build-wide, DISTINGUISHES proposals fell from 41 to 9 and FOLLOWS from 30 to 5; the README gives the new counts but not the comparison. And the own-voice overruling miss is described with the wrong cause.

## Requested actions

1. Send first-person overruling sentences to adviser review as leads even when binding fails; fix the reason on TC-3b178e403337 and the README sentence (REL-05).
2. Apply the own-voice filter to INTERPRETED and HELD_INAPPLICABLE, and keep jurisdiction articles out of CHALLENGE_GROUND_CITED (REL-10).
3. Bring the round-1 rows file into the workstream or record its hash (V11-02).
4. Reword the two README claims (REL-08, REL-14) and add before/after proposal counts.

## Limits of this review

- Text-layer reading only; no PDFs or page images were opened.
- Verdicts are documentary (court's own words, about the stated target), not opinions on legal effect.
- The samples are small. The APPLIES/FOLLOWS figure rests largely on one template.
- The recall probe read the 41 OVERRULES/QUESTIONS/REVERSES cue rows classed as not bound to the target (duplicates read once); it is not a full recall measurement.
