# Focused re-review: C8-EVIDENCE at 801d2c41 (corrections for review 5212a95b)

RESEARCH ONLY. This re-review checks the corrections to the earlier findings; it is not a fresh full review. It approves nothing and signs off for nobody. Page readings below are mine, an AI agent's, and are not human-confirmed. A matching hash shows bit integrity, not authenticity, currency or legal correctness.

## Result

All twelve findings B-01 to B-12 are closed in the worktree at 801d2c41. No regression was found. Two small P3 items and three INFO items remain; none blocks use of the packages by the owner. One matter needs an owner decision and is not a code defect: the page text removed by B-03 is still in commit 5212a95b, which is on the remote branch.

## Status of the earlier findings

| id | sev | status | evidence |
| --- | --- | --- | --- |
| B-01 | P2 | CLOSED | All six places now cite `AUTH-LEDGER/evidence/copy_structure.csv#C5-SRC-J-SC-2015-RAJBIR~C2` with range [0 149839 159611 4244], YES_AFTER_PREFIX, structural only. That matches line 7 of the pinned register. The spurious correction proposal is gone; only the Dharamvir producer-encoding proposal remains. |
| B-02 | P2 | CLOSED (see R-01) | T1-20 template limitations carry the CMS failure (C8-CR-03), C8-CR-14 and the five-instrument note. T1-19 carries "INTEGRITY ONLY, NOT AUTHENTICITY" with no chain, trust anchor, validity or revocation check. T1-02 carries "COPY PROVENANCE ONLY", S.R.O. 34 UNRESOLVED and "no amendment-chain inference". For all 20 Gazette rows the pending-entry limitation is contained verbatim and the register limitation is contained verbatim in the template. For all 8 Supreme Court rows the C6-01 addendum limitation is contained verbatim; "RETRIEVAL DATE NOT EVIDENCED" appears for exactly the four copies whose C6-01 retrieval_date is NOT_EVIDENCED (Ranjit, S N Mukherjee, Girish, Mullikote) and for no other. |
| B-03 | P2 | CLOSED in the worktree; history is an owner matter (R-04) | `render_run1/2.jsonl` are deleted. `render_facts.jsonl` has 28 rows with no text field; each `text_layer_sha256` and `text_layer_chars` equals the hash and length of the old dumped text. `page_structure.json` holds only line hashes. The diagnosis term and the two service numbers outside the Mullikote discrepancy occur nowhere in the package. The N S Yadav service number is masked in all three places. |
| B-04 | P3 | CLOSED | I rendered T1-20 PDF p.6 from the held file: PNG sha256 83ee998f... matches. My reading of the page agrees with C8-PIC-40 (header, S.R.O. 21(E), 28-12-2019, Air Force (Amendment) Regulations, 2019, M. SUBBARAYAN, footer, appearance at bottom right). The appearance wording is too small to read on the 150 dpi render; the check says it was taken from the text layer, which is correct. One Signature widget on p.6; time equals /M and ModDate. pp.3-5 text layer shows S.R.O. 18(E), 19(E), 20(E) as recorded. |
| B-05 | P3 | CLOSED | No `bd_work`, `c8out/B` or "not committed evidence" text remains. Renderer label reads PyMuPDF 2.1 (MuPDF 1.28.6). The one `c8out/C/tmp_sim` mention is written as `<scratchpad>/...`. |
| B-06 | P3 | CLOSED | Every quoted S.R.O. 34 form in C8-CR-02 (11 forms, English and Hindi) occurs in a committed page-check reading. Status still UNRESOLVED. |
| B-07 | P3 | CLOSED | "paras 1-3 become 4-6, 4-51 become 52-99" in the findings, evidence file, page check, register and template; consistent with `mullikote_half_diff.txt`. |
| B-08 | P3 | CLOSED | No truncating slices remain in `build_packages.py`; the Mullikote identity cell and the simulation label print in full. |
| B-09 | P3 | CLOSED | All 20 carried rows: sha256, status and `original_locator` equal the original register; the three original columns are contained in `description`. README and findings say "restructured". |
| B-10 | P3 | CLOSED | NAVJOT-2 is marked "UNVERIFIED ASSERTIONS, no primary source cited here". Commencement clauses in T1-07, 12, 15, 17, 18, 20 are quotations that occur in the readings. `original_carrier` reads "apparent original carrier ... origin not established". No "e-Gazette" or "in force on publication" wording remains. |
| B-11 | P3 | CLOSED | C8-CR-14 (UNRESOLVED) added; draws no inference; cited from C8-PIC-39. |
| B-12 | INFO | CLOSED | C8-PIC-19, -20, -35 carry the variance note; identity results unchanged. |

## Reproduction

| Check | Result |
| --- | --- |
| `build_c8b.py --base <root> --out <temp copy>` with the six output kinds deleted first | Regenerated; `diff -r` against the committed folder is empty. |
| `build_c8_registers.py`, `build_copy_register.py`, `build_treatment_leads.py` into a temp dir | All three outputs byte-identical. |
| `rehash_and_render.py` on the full plan (40 pages) from held files | `render_log.csv` byte-identical; 0 problems. |
| `render_pages.py` on the 28 Supreme Court pages | All fields of `render_facts.jsonl` reproduced. |
| `page_structure.py` on held files | `page_structure.json` byte-identical. |
| `sim_anchor.py` on an extracted copy of the commit | `exact_anchor_simulation.json` byte-identical: 6 at version 0, 13 jointly, 10 without the JUDIS three, 11 without Navjot and Mullikote. |
| `tools/build_packages.py --check` | "C8 packages reproduce (30 files)", rc 0. |
| `tools/legal_audit/check_csv.py` | csv_files=217 errors=0. |
| `tools/legal_audit/check_provenance.py` | violations=2 known=2 new=0. |

## Regression checks

- Scope: only `legal_knowledge/audit_work/C8-EVIDENCE/` differs from base 1a21a2e8 and from 5212a95b. No binary file. Worktree clean after my runs.
- Counts: 40 checks, 37 CONFIRMED, 3 PARTIAL, ids unique; every check hash equals `render_log.csv`. 20 candidates CONFIRMED. Recommendations 18 / 1 HOLD (T1-19) / 1 NEEDS_FURTHER_EVIDENCE (T1-20), unchanged.
- Contradiction register: 33 rows, T1-CR-01..20 plus C8-CR-01..14 without 07.
- No approval or status claim: ledger `decisions/` holds only README; templates say "Not a decision", `legal_approval: NOT_GIVEN`, owner fields blank. A search for approval, binding, good-law and authenticated wording found only negations and the template placeholders.
- AI-reader caveat present in every Markdown file; reader field is the same AI-agent string on all 40 checks.
- No absolute path in the package.
- The review files in `review/` are byte-identical to the ones I delivered.

## New findings

| id | sev | title |
| --- | --- | --- |
| R-01 | P3 | T1-19 limitations omit C8-CR-14 although the entry names T1-19 |
| R-02 | P3 | `mullikote_half_diff.txt` still holds fragments of the respondents' service-date table |
| R-03 | INFO | C8-PIC-40 is a context check counted as CONFIRMED; two cosmetic slips |
| R-04 | INFO | Removed page text and personal data remain in commit 5212a95b: owner decision |
| R-05 | INFO | What matched |

Detail is in `fable_rereview_c8_evidence_801d2c41_findings.csv`.

## Git history (task 3)

Commit 5212a95b still contains `render_run1.jsonl` (39,528 bytes) and `render_run2.jsonl` (19,175 bytes) with the text of 28 judgment pages, the old `page_structure.json` with first and last lines, and the unmasked N S Yadav service number. The commit is on `origin/claude/c8-evidence-verification`. This is not a defect in 801d2c41 and cannot be fixed by a further commit. Removing it needs a history rewrite and force-push of the branch (or a squash at merge with the branch then deleted), which is for the project owner to decide. Points for that decision: the text comes from published Supreme Court judgments, so the exposure is aggregation in a private repository, not disclosure of unpublished data; a squash merge would keep the text out of main but not out of the remote branch or any PR refs until those are deleted.

## Not checked

- Anything outside the corrections, except the regression items listed. Gazette pages other than T1-20 p.6 were not re-read; their render hashes were reproduced.
- Certificate chain, trust anchor, revocation, signing time: still not validated by anyone.
- No comparison with an egazette.gov.in or court-served copy; no network was used.
- The canonical private Hugging Face snapshot was not consulted; coverage against it is unknown.
- Hindi text in C8-CR-02 and C8-CR-14 was matched as strings against the readings, not re-read from images.

## False-pass limitations

Byte-identical regeneration shows the outputs come from the scripts and the committed inputs. It does not show the hand-entered readings in those scripts are right. My agreement with C8-PIC-40 is agreement between two AI readers using the same renderer on the same bytes. Nothing here shows that the archive.org or court-host files are what the Government or the Court issued, or says anything about currency or applicability.

VERDICT: ACCEPT

Reviewer model: Fable 5.2 (claude-fable-5-2)
