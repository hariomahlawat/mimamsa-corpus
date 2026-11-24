# Review: C11 judicial relationships and statute links

- **Reviewer:** Fable 5.2 (claude-fable-5-2). AI documentary review, not legal validation.
- **Date:** 2026-11-24.
- **Object:** `C11-JUDICIAL-QUALITY/relations/` (tools, tests, six outputs), commit `9529f7fe` of the c11 worktree.
- **Sources read:** `data/text` and `data/meta` as git objects at `ad77758d` of `/home/user/c7`. `holdout/` was not opened. Nothing was committed or pushed.
- **Companion files:** `fable_review_relations_c11_rows.csv` (223 per-row verdicts), `fable_review_relations_c11_findings.csv` (19 findings).

## Verdict

The build is reproducible, the dossier is accurate, and citation resolution is reliable. The typed treatment proposals and the cue-based statute labels are not ready for an adviser queue: most of the high-stakes proposals are not the court's own words, and one whole APPLIES family says the opposite of the text.

Nothing in the outputs declares a precedent overruled or assigns a provision version, so no false legal status has been recorded. The problem is the quality of what is queued for human review.

## Measured precision

| Category | Sample | Supported | Precision |
| --- | --- | --- | --- |
| OVERRULES / QUESTIONS proposals (all) | 10 | 1 | 10% |
| Reported-treatment rows at adviser review (all) | 47 | 13 | 28% |
| APPLIES / FOLLOWS proposals | 25 | 18 | 72% |
| DISTINGUISHES proposals | 15 | 5 | 33% |
| Resolved citation edges | 40 | 39 | 97.5% |
| AMBIGUOUS / citation-mismatch edges fairly left unresolved | 20 | 20 | 100% |
| Cue-based statute relationships | 30 | 9 | 30% |
| STATUTE_MENTIONED | 10 | 10 | 100% |
| Dossier quotations (all distinct readings) | 26 | 26 | 100% |

Samples are deterministic: lowest `sha256('C11-REL-REV' + row id)`. The resolved-edge sample is stratified by method (10 parallel-learned, 10 party/year/court, 8 curated, 8 case-number, 2 reporter metadata, 2 neutral metadata). The statute sample takes 6 rows per cue label.

Within the samples:

- **APPLIES / FOLLOWS:** APPLIES 17 of 22, FOLLOWS 1 of 3.
- **Resolution by method:** party/year/court 9 of 10; every other method fully correct.
- **Statute labels:** APPLIED 0 of 6, INTERPRETED 1 of 6, CHALLENGED 1 of 6, QUOTED 5 of 6, HELD_INAPPLICABLE 2 of 6. In all 30 rows the provision is at least named on the stated page.

## 1. Reproducibility

- `--check` passes: "CHECK OK: 6 outputs reproduce byte-identically", 93 s.
- Tests pass: 22 of 22 under python3.11 (89 s) and under the venv interpreter (101 s). The venv is Python 3.13.18, not 3.11.
- `OUTPUT_SHA256SUMS` verifies for all six outputs.
- The tests were run in a disposable copy with the sibling input folders symlinked.
- The documented command writes `tools/__pycache__` into the worktree. My first `--check` run created it there; I removed it, and the worktree is otherwise untouched.
- `README.md` sits in `outputs/`, not at the workstream root.

## 2. Treatment candidates

### OVERRULES and QUESTIONS proposals (REL-01, P1)

Only Parashotam para 32 on Shri Kant Sharma is the court's own wording. The other nine are:

- **Counsel submissions (4):** for example "Mr Sai Deepak ... has contended that the judgment in Navtej Singh Johar is per incuriam", which the court then declines to accept.
- **Inside quotations (3):** including both McDowell rows in Puttaswamy (2018), which are Shayara Bano's words.
- **Reports of another bench (2):** the referring Bench in Mafatlal, and "in the view of Justice Nariman" for Binoy Viswam.

Four of the nine also name the wrong authority. The README names the two Puttaswamy (2018) rows as OVERRULES proposals and says quoted or reported wording never produces a proposal; on this build it does.

### Inverted APPLIES (REL-02, P1)

All 17 APPLIES proposals for Narsingh Yadav come from one Punjab & Haryana boilerplate sentence: "such onus has not been discharged by the employer ... to show that the respondent's case is covered by Narsingh Yadav's case". The court holds the case not covered. I checked all 17, not only the three in the sample.

### Other treatment findings (P2)

- **Footnote adjacency (REL-03).** 11 of the 20 citation-string APPLIES proposals for Dharamvir come from "The issue is covered by ... Gawas Anil Madso"; Dharamvir is only the neighbouring footnote. Eight Delhi HC rows put Dharamvir at adviser review for "doubted" on the strength of a generic sentence about another case.
- **Direction inverted (REL-04).** In 13 of the 47 reported-treatment rows the stated target is the case doing the overruling (R.R. Pillai, Tulsiram Patel, Maneka Gandhi, L. Chandra Kumar and others). Six more are not treatment at all, such as a plea that "was overruled".
- **Missed own-voice overruling (REL-05).** Puttaswamy (2017), "ADM Jabalpur must be and is accordingly overruled. We also overrule ...", is classed as a report of another court and gets no proposal.
- **DISTINGUISHES (REL-06).** Two S.P. Gupta headnote entries ("held inapplicable", pp.21 and 91) are zoned as body text; the editorial zone ends too early for long headnotes.
- **Name references (REL-07).** All five "Navtej Singh" references mean Navtej Singh Johar but resolve to a different held case. "Mills Ltd" and the running header "MADRAS BAR" also resolve to held cases.

## 3. Citation resolution

Resolution is the strongest part: 39 of 40 targets are right, and the unresolved classes are conservative.

- **One mislink, nine edges (REL-09).** Indian Express Newspapers (Bombay) v. UOI, (1985) 1 SCC 641, is linked to the later Express Newspapers Pvt. Ltd. v. UOI. Three of those edges print "[1985] 2 SCR 287", which contradicts the target's own citation, so the mismatch guard should have fired.
- **Running headers counted as citations (REL-08).** At least 717 edges are the citing judgment's own SCR header plus a paragraph or page number. Two are resolved to unrelated judgments at AUTOMATED_DETECTED. The 24,000 edge total and the 10.8% resolution rate are both affected.
- **Unresolved edges.** None of the 20 should have been linked automatically. Three are recoverable with a named-party tie-break, and "Major A. Hussain, AIR 1998 SC 577" is resolved in one edge and ambiguous in another (REL-14).
- **Recall.** 61 other held texts name Parashotam Dass; 6 resolve to it (REL-18). The README discloses that name-only mentions are not resolved.

## 4. Statute links

- **Version.** No provision version is asserted anywhere: all 11,067 rows are VERSION_NOT_ESTABLISHED, and the IPC-to-BNS note is recorded without inference.
- **Wrong instrument (REL-11).** Six rows link a 1972 judgment that prints "Code of Criminal Procedure 1898" to CRPC-1973. This is not a version claim in the column sense, but it is a wrong instrument.
- **Labels overstate (REL-10).** 227 of 284 PROVISION_CHALLENGED rows are Constitution articles; in the sample those are the ground of challenge, not the provision challenged. 179 of 303 PROVISION_APPLIED cues are "invoking", "invoked" or "punishable under", which in the sample record a party's invocation or an FIR narration. Three sampled rows state the opposite of the text, for example Article 311 marked applied where the court says its protection "is not available".
- **Ids (REL-12).** The same Army Rule appears as `AR-1954:s.180` and `AR-1954:r.180`.

## 5. Dossier

- All 26 distinct quotations are verbatim on the stated page and paragraph, including the five named in the brief:
  - Parashotam para 32, pp.17-18;
  - Girish para 22, p.11;
  - Tarsem paras 5 and 6, pp.5-6;
  - Delhi HC W.P.(C) 16771/2025, p.9 para 27;
  - J&K HC WP(C) 2370/2025, para 6, pp.2-3.
- Kind labels fit: the two reporter entries are marked editorial, and the treatment quotations are first-person court voice.
- The two negative claims check out: "Parashotam" does not occur in the J&K order, and "Girish" does not occur in the Delhi one.
- The dossier never states an overruling as settled law. Shri Kant Sharma is described as "OVERRULES is proposed for adviser review only", with the note that the word "overruled" is not used.
- Graph counts in the summary table match the graph (Tarsem 45, Dharamvir 352, Shri Kant Sharma 17, Parashotam 6, Girish 22, Ranjit Thakur 41, S.N. Mukherjee 25).
- The graph-derived candidate tables inside the dossier repeat the errors in section 2 (REL-13).

## Requested actions, in order

1. Withdraw the nine unsupported OVERRULES/QUESTIONS proposals and the 17 Narsingh Yadav APPLIES proposals; correct the README sentence on Puttaswamy (REL-01, REL-02).
2. Fix attribution and target binding: quotation spans across pages, submission lead-ins, footnote markers, agent versus patient, first-person overruling (REL-03 to REL-07).
3. Strip running headers before citation detection and restate the edge counts (REL-08); unresolve the nine Express Newspapers edges (REL-09).
4. Rename or split the statute cue labels and add CRPC-1898 (REL-10, REL-11).
5. Regenerate the dossier tables after the above (REL-13).

## Limits of this review

- Text-layer reading only; no page images were rendered and no PDFs were opened.
- Treatment verdicts are documentary: whether the wording is the court's own and about the stated target. They are not opinions on the legal effect.
- The APPLIES/FOLLOWS, DISTINGUISHES, resolution and statute figures are sample estimates with small n; the two population counts (17 Narsingh, 11 Dharamvir/Gawas) and the 717 header edges were measured on the full output.
