# Dispositions: independent review 5212a95b of C8-EVIDENCE

The review is in this folder, copied verbatim: `fable_review_c8_evidence_5212a95b.md` and `fable_review_c8_evidence_5212a95b_findings.csv`. Its verdict was ACCEPT WITH CONDITIONS.

**What this file is.** An AI implementation agent (Claude Opus 5.5 subagent) made these corrections. It is not the reviewer.
- Nothing here approves anything. No legal status was changed, and no ledger entry, decision record or BIND line was created.
- The AUTH-LEDGER stays at version 0.
- The new page reading (C8-PIC-40) was made by an AI agent and is not human-confirmed.

**How the outputs were rebuilt.**
- Wherever possible, the generator scripts were corrected and re-run, so the outputs still come from the scripts:
  - `GAZETTE-T1/tools/build_c8b.py` was run as `--base <repo root> --out GAZETTE-T1`. It now reads only committed inputs plus the pinned registers. Before any change, it reproduced the five registers byte for byte.
  - `SC-T2/tools/build_copy_register.py`, `build_c8_registers.py` and `build_treatment_leads.py` were re-run.
  - `SC-T2/tools/page_structure.py` was re-run on the held files. Before the change it reproduced `page_structure.json` byte for byte.
  - `tools/build_packages.py` was re-run.
- The Markdown findings and per-case evidence files (`*_FINDINGS.md`, `SC-T2/evidence/*.md`) were always hand-written, so they were edited directly.

| Finding | Severity | Disposition | Files changed |
| --- | --- | --- | --- |
| B-01 | P2 | **Fixed.** Corrected the statements that Rajbir C2 (`c6ec489d…`) has no copy_structure row in all six places: SC_C8_FINDINGS.md (three places), rajbir_singh.md (two places), and the C8-SCPIC-23 discrepancy text, which comes from the generator. Each now cites `AUTH-LEDGER/evidence/copy_structure.csv#C5-SRC-J-SC-2015-RAJBIR~C2`: range [0 149839 159611 4244], YES_AFTER_PREFIX, structural record only, not validated. Removed the spurious correction proposal "copy_structure.csv rows for Rajbir C2"; the proposal for the Dharamvir producer encoding stays. | `SC-T2/SC_C8_FINDINGS.md`, `SC-T2/evidence/rajbir_singh.md`, `SC-T2/tools/build_c8_registers.py`, `SC-T2/page_checks_sc_c8.csv` (regenerated) |
| B-02 | P2 | **Fixed, driven by the registers.** See "B-02 in detail" below the table. `build_packages.py --check` passes (30 files). | `GAZETTE-T1/tools/build_c8b.py`; `GAZETTE-T1/eligibility_recommendations.csv`, `gazette_evidence_register.csv`, `evidence/T1-*.md` (regenerated); `SC-T2/tools/build_copy_register.py`; `SC-T2/sc_copy_evidence_register.csv` (regenerated); `SC-T2/evidence/*.md`; `tools/build_packages.py`; both `APPROVAL_PACKAGE.md` and all 28 templates (regenerated) |
| B-03 | P2 | **Fixed.** See "B-03 in detail" below the table. | `SC-T2/tools/render_run1.jsonl` and `render_run2.jsonl` (deleted); `SC-T2/tools/render_facts.jsonl` (new); `SC-T2/tools/render_pages.py`, `page_structure.py`, `page_structure.json`, `build_c8_registers.py`, `build_copy_register.py`; `SC-T2/evidence/ns_yadav.md`; `README.md` |
| B-04 | P3 | **Fixed.** Rendered T1-20 PDF p.6 with `tools/rehash_and_render.py`, using the same settings as the original renders (PyMuPDF 2.1 / MuPDF 1.28.6, 150 dpi gray, full page). The held file re-hashed as MATCH; the PNG sha256 is `83ee998f105ff44b4c1541a98adcf1beda26cd4d191f5b1486712d916b0ff5cc`. Recorded it as new check **C8-PIC-40** (reader: AI agent (Claude Opus 5.5 subagent), not human-confirmed). The check reads S.R.O. 21(E)/2019 and the footer, plus the appearance "Digitally signed by MANOJ KUMAR VERMA Date: 2019.12.28 20:01:43 +05'30'". That small type was read from the text layer, and the page has one Signature widget. The time equals /M and ModDate. pp.3-5 were identified from the text layer only: S.R.O. 18(E) and 19(E) (Navy regulations) and 20(E) (Air Force Rules), all signed M. SUBBARAYAN. The copy is recorded as carrying five instruments, and the entry would cover the copy. Counts are now 40 checks: 37 CONFIRMED, 3 PARTIAL. | `GAZETTE-T1/render_log.csv`, `tools/render_plan.csv`, `tools/readings_notes.txt`, `tools/build_c8b.py`, `page_image_checks_c8.csv`, `gazette_evidence_register.csv`, `evidence/T1-20.md`, `eligibility_recommendations.csv` (regenerated), `BORN_DIGITAL_FINDINGS.md`, `GAZETTE_C8_FINDINGS.md`, `README.md`, `APPROVAL_PACKAGE.md` |
| B-05 | P3 | **Fixed.** See "B-05 in detail" below the table. | `GAZETTE-T1/tools/build_c8b.py`, `contradiction_register_c8.csv`, `born_digital_structure.csv`, `page_image_checks_c8.csv`, `evidence/*.md` (regenerated), `BORN_DIGITAL_FINDINGS.md`, `GAZETTE_C8_FINDINGS.md`, `SC-T2/EXACT_ANCHOR_FINDINGS.md`, SC tools docstrings |
| B-06 | P3 | **Fixed.** The C8-CR-02 quotations are no longer typed by hand. `build_c8b.py` extracts each NOTE form from the reading of the page check it cites, and fails if a form is missing. Each form is now quoted as printed, for example "SRO 34 dated 5 June, 1963" (p.367), "S.R.O. 34 dated the 5th June, 1963" (p.617), "SRO 34 dated the 5th June, 1963" (p.736) and "SRO 34 dated 5th June 1963" (p.214). The Hindi quotation "5 जून, 1963" did not occur in any reading, so it was replaced with two forms that do: "का. नि. आ. 34 तारीख 5 जून 1963" (p.531) and "सं. 34, दिनांक 5-6-1963" (p.217). The substance and the UNRESOLVED status are unchanged. | `GAZETTE-T1/tools/build_c8b.py`, `contradiction_register_c8.csv` (regenerated) |
| B-07 | P3 | **Fixed.** The second Mullikote version is now described exactly: first-version paragraphs 1-3 become 4-6, and 4-51 become 52-99. The second version therefore runs 4-6, then 52-99. Checked against the committed `tools/mullikote_half_diff.txt`. | `SC-T2/SC_C8_FINDINGS.md`, `SC-T2/evidence/mullikote.md`, `SC-T2/tools/build_c8_registers.py`, `build_copy_register.py`, `page_checks_sc_c8.csv` and `sc_copy_evidence_register.csv` (regenerated) |
| B-08 | P3 | **Fixed.** Removed the `[:40]` and `[:60]` slices in `build_packages.py`. The Mullikote identity cell now reads in full "CONFIRMED (case identity); PARTIAL for the pp.32-62 version", and the simulation label is printed in full. | `tools/build_packages.py`, `SC-T2/APPROVAL_PACKAGE.md` |
| B-09 | P3 | **Fixed; the locator is restored.** The carried-forward rows T1-CR-01..20 now have an `original_locator` column holding the original register's locator. `c8_update` now says "content and status unchanged; structure changed in C8 (entry id assigned; ... merged into description; locator kept in original_locator)". The README and GAZETTE_C8_FINDINGS no longer say "unchanged". The three original finding columns stay merged into `description`, which equals them exactly; the review checked all 20 rows. | `GAZETTE-T1/tools/build_c8b.py`, `contradiction_register_c8.csv` (regenerated), `GAZETTE_C8_FINDINGS.md`, `README.md` |
| B-10 | P3 | **Fixed.** See "B-10 in detail" below the table. | `SC-T2/tools/build_treatment_leads.py`, `SC-T2/subsequent_treatment_leads.csv` (regenerated), `GAZETTE-T1/tools/build_c8b.py`, `gazette_evidence_register.csv`, `evidence/*.md` (regenerated) |
| B-11 | P3 | **Fixed.** Added **C8-CR-14 (UNRESOLVED)**. In S.R.O. 17(E)/2019, the Hindi footnote names "का.नि.आ. 2(अ), तारीख 20 फरवरी, 2018" as the last amendment; the English footnote says only "were last amended in 2018". S.R.O. 2(E)/2018 is on its face a r.188(e) declaration. No inference is drawn. The entry cites C8-PIC-39 and C8-PIC-37, is carried into the T1-20 limitations, and is noted on C8-PIC-39. | `GAZETTE-T1/tools/build_c8b.py`, `contradiction_register_c8.csv`, `page_image_checks_c8.csv`, `eligibility_recommendations.csv` (regenerated), `GAZETTE_C8_FINDINGS.md`, `README.md` |
| B-12 | INFO | **Recorded; the readings were not changed.** Each of C8-PIC-19, -20 and -35 now ends with a note naming the reviewer's variant reading (low confidence), and the glyph should be treated as UNCERTAIN on human re-check. No identity element is affected, and the identity results are unchanged. | `GAZETTE-T1/tools/build_c8b.py`, `page_image_checks_c8.csv` (regenerated) |
| B-13 | INFO | No action; this finding records what matched. | none |

## B-02 in detail
- **Gazette.** `build_c8b.py` now builds each candidate's `limitations` from three sources:
  - the AI-reader caveat;
  - a short limitation for each contradiction-register entry that names the candidate:
    - C8-CR-01, and C8-CR-02 (COPY PROVENANCE ONLY; S.R.O. 34 relationship UNRESOLVED; no amendment-chain inference);
    - C8-CR-03 (embedded CMS signature FAILS verification; cause UNCERTAIN);
    - C8-CR-04 (INTEGRITY ONLY, NOT AUTHENTICITY; no chain, trust anchor, validity or revocation check);
    - C8-CR-14;
  - the limitation of the candidate's row in `AUTH-LEDGER/tranches/T1-GAZETTE/proposed_entries_PENDING.csv`, carried verbatim. For T1-19 and T1-20, a note says that the pending phrase "signature NOT cryptographically validated" predates the C8 check.
- **T1-20** also records that the copy carries five instruments.
- **Supreme Court.** `build_copy_register.py` adds two columns, read from the pinned C6-01 registers:
  - `retrieval_evidence_c6_01`: the URL, date, method and remaining gaps from `provenance_recovery_register.csv`.
  - `limitations`: the AI caveat; "RETRIEVAL DATE NOT EVIDENCED" where C6-01 says so (Ranjit Thakur, S N Mukherjee, Girish Kumar, Mullikote); the C8 limitation for the copy, namely JUDIS/P-D3 for Ranjit, S N Mukherjee and Navjot, the two versions in the Mullikote file with pp.1-31 to be named, the C1-only scope for Rajbir C1, and so on; and the C6-01 draft-addendum limitation, verbatim.
- **Templates.** `build_packages.py` now fills "limitations to be recorded verbatim" from these register columns. A separate context line gives the contradiction entries (Gazette) or the C8 discrepancies (Supreme Court).
- Each `SC-T2/evidence/*.md` file gained a section on its retrieval record and limitations.

## B-03 in detail
- **Render logs.** Deleted `SC-T2/tools/render_run1.jsonl` and `render_run2.jsonl`. They are replaced by `render_facts.jsonl`, whose 28 rows keep the copy sha256, held path, page, PNG name and sha256, dimensions and settings. Each row also has `text_layer_sha256` and `text_layer_chars` in place of the page text.
- **Tools.**
  - `render_pages.py` no longer emits page text.
  - `build_c8_registers.py` reads `render_facts.jsonl`; the regenerated page checks are otherwise unchanged by this step.
- **Other committed files.** The search for long text fields and page-text dumps found two further issues, both fixed:
  - `page_structure.json` held each page's first and last text-layer lines, including a medical detail from the N S Yadav judgment. `page_structure.py` now records only the sha256 of those lines. It was re-run on the held files, and its other fields are unchanged.
  - The N S Yadav appellant's army service number was quoted in C8-SCPIC-15, the copy register and `ns_yadav.md`. It is now masked as "[service number masked: 8 digits + letter, as printed]".
- **Left in place.** The Mullikote service numbers stay: they are the discrepancy itself (2568912 M against 256812 M). The Gazette `readings_notes.txt` stays: it transcribes published notifications, and the only names in it are signing officials.
- **Not fully reviewed.** `SC-T2/tools/mullikote_half_diff.txt` was kept as the evidence for B-07. It is a list of short diff snippets, not a page dump, but it includes one line of the respondent's service-date table. The owner may wish to trim it.
- **Git history.** The deleted text remains in commit 5212a95b and in any branch history. Removing it from history would need a history rewrite, which is the coordinator's or owner's decision and was not done here.

## B-05 in detail
- **Evidence references.** `build_c8b.py` reads, and cites, `born_digital/` rather than `bd_work/`. All 8 `evidence_refs` and `BORN_DIGITAL_FINDINGS.md` now point to committed files.
- **GAZETTE_C8_FINDINGS.md.**
  - The renderer label is corrected to "PyMuPDF 2.1 (MuPDF 1.28.6)".
  - "renders/ (not committed)" is restated as "not committed; reproducible with tools/rehash_and_render.py".
  - The "Output files (c8out/B/)" list is replaced by the committed contents of the folder.
- **EXACT_ANCHOR_FINDINGS.md.**
  - The caveat no longer says the C8 checks "are not committed evidence". It now says they are committed in `page_checks_sc_c8.csv` but are AI-agent readings that are not in the reader's snapshot.
  - The tmp_sim path is written as `<scratchpad>/...`.
- **Docstrings.** The SC tool docstrings no longer name c8out.

## B-10 in detail
- **NAVJOT-2.** The question now marks the Evidence Act/BSA, IPC/BNS and POTA statements as "UNVERIFIED ASSERTIONS, no primary source cited here; each needs the enacting or repealing instrument (India Code / Gazette) before use".
- **Commencement clauses.** In the Gazette register (T1-07, 12, 15, 17, 18, 20), each "in force on publication" paraphrase is replaced by the commencement clause as transcribed in the page readings, for example "'(2) They shall come into force on the date of their publication in the Official Gazette.'". The T1-18 clause is quoted as printed ("These shall ..."), and the T1-15 deeming words are quoted.
- **Original carrier.** `original_carrier` now reads "apparent original carrier (inferred from ... only; origin not established ...)". For T1-20 it adds that the signature fails verification (C8-CR-03); for T1-19, that the check shows integrity only (C8-CR-04). The "e-Gazette" wording is removed.

## Checks run from the worktree root
- `python tools/legal_audit/check_csv.py`: csv_files=217 errors=0.
- `python tools/legal_audit/check_provenance.py`: violations=2 known=2 new=0.
- `python legal_knowledge/audit_work/C8-EVIDENCE/tools/build_packages.py --check`: C8 packages reproduce (30 files).
- A recursive grep of `legal_knowledge/audit_work/C8-EVIDENCE` for the absolute scratchpad prefix (the session temp directory): no output.
