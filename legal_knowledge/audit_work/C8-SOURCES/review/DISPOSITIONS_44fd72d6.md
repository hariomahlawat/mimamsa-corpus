# Dispositions: independent review of C8-SOURCES at 44fd72d6

Review: `fable_review_c8_sources_44fd72d6.md` and `fable_review_c8_sources_44fd72d6_findings.csv` in this folder (verbatim copies).

Scope of these corrections:
- Implementation only: no legal status was changed, no original record or frozen register was edited, nothing was downloaded and no one was contacted.
- Generators were fixed and the outputs regenerated wherever a generator exists.
- RC-03 and RC-06 concern `RULE_VERSION_DECISION_PACK_C8.md`, which the coordinator handles. They are addressed by the coordinator in the same commit, in RULE_VERSION_DECISION_PACK_C8.md (see DISPOSITIONS_f98f7a2a.md).

| ID | Sev | Disposition | Change made | Files |
| --- | --- | --- | --- | --- |
| RC-01 | P1 | DONE | The invented "r.23 amended 2022" is removed from EV-016, HCE-010 and SC03. Those cells now state what the registers say: no amendment to r.23 located (31 instruments, 1960-2022, none amends r.23); S.R.O. 6(E)/2022 amends r.16A(4) only; open gaps AR-001 (E-7/1960), AR-030 (S.R.O. 258/2002) and AR-036 (after 06-06-2022, not searched); r.23(3) CONFLICTING, reserved (C-01/U-01). Every other dependency and amendment cell was then re-checked (list below), and 13 more cells were corrected. | `CORPUS-QUALITY/work/build_hr.py`, `high_risk_record_review.csv`, `HIGH_RISK_REVIEW.md` |
| RC-02 | P2 | DONE | `--out` is refused (exit 2) if it resolves to any input by real path, `samefile` or device+inode, even with `--overwrite`. Also refused: a path inside `curated_originals`, an existing file without the new `--overwrite` flag, a directory, and a missing parent. Writes are atomic: a temporary file in the target directory is hard-linked into place (no-clobber) or, with `--overwrite`, renamed, and the guard is re-checked before the switch. Six new tests cover symlink, hardlink, existing non-input file, input path with `--overwrite`, `curated_originals`, and directory or missing parent. All 25 existing tests still pass. The harness now deletes its own report before each run, because the tool no longer overwrites. Docs no longer claim "never overwrites". | `CORPUS-QUALITY/tools/reconcile_judgments.py`, `test_reconcile_judgments.py`, `tools/README.md`, `CORPUS_QUALITY_C8_FINDINGS.md`, `work/unittest_output.txt` |
| RC-03 | P2 | DONE BY THE COORDINATOR (decision pack; see DISPOSITIONS_f98f7a2a.md) | The decision pack is handled by the coordinator. | — |
| RC-04 | P2 | DONE | Generator rule `COMM_NOTIF_KNOWN`: D-AMC-AA-07 now has gap COMMENCEMENT NOTIFICATION REQUIRED. Its status reads "NOT_DETERMINED (C5 state preserved); separate commencement notification under s.1(2) of Act 20/1983 known, not held: ACQ03-024". D-SSM-012 now carries the CNR flag and the ACQ03-024 note. The findings summary names CNR for Act 19/1955 and Act 20/1983. The README list adds Act 19/1955 (S.R.O. 2(E)/1955; already CNR in the matrix as D-AMC-AA-01) and Act 20/1983, and names every CNR row in the matrix. No date was inferred. | `PRIMARY-SOURCES/tools/build_c8_d.py`, `amendment_commencement_matrix.csv/.md`, `statutory_source_matrix.csv/.md`, `PRIMARY_SOURCES_C8_FINDINGS.md`, `OUTPUT_SHA256SUMS`, `C8-SOURCES/README.md` |
| RC-05 | P2 | DONE | I re-checked the five held copies with a PyMuPDF full-text search. Only Girish (4f7ea3a4) prints its own neutral citation, 2026 INSC 149. E8-CP-10 for Girish stays a proposal, with evidence "as printed on the held copy". The other four (PPS Bedi 211dbaf4, Parashotam fe19875b, Dharamvir 3056712c, Ranjit Thakur ed7cf31f) become `UNVERIFIED_LEAD (not read from held copy)` with status `UNVERIFIED_LEAD_NO_PROPOSAL`: their values come from the WS-B specification column and the intern mirror only. The E8-XR-06 wording is corrected. | `work/build_cp.py`, `work/build_findings.py`, `correction_proposals.csv`, `cross_reference_findings.csv/.md`, `CORPUS_QUALITY_C8_FINDINGS.md` |
| RC-06 | P2 | DONE BY THE COORDINATOR (decision pack, pinned in f98f7a2a/0e75a4a3) | The decision pack is handled by the coordinator. | — |
| RC-07 | P2 | DONE | "w.e.f. 06-09-1992" is now attributed everywhere: India Code footnote, a compilation statement (the assent date); the Act prints no commencement clause (held Gazette f11d443e); commencement NOT_STATED_PENDING_ADVICE (AQ-05). This applies to HCE-017, CM-SC-18, CM-011, CM-012 and E8-XR-14. The CM-SC-18 gap changes from "NONE (verified)" to "COMMENCEMENT_NOT_STATED (AQ-05 pending); omission text verified". | `work/build_hr.py`, `work/build_findings.py`, `high_risk_record_review.csv`, `cross_reference_findings.csv/.md`, `HIGH_RISK_REVIEW.md` |
| RC-08 | P3 | DONE | X14b now scans `holdings_register.csv` and `subsequent_treatment.csv` as well as the cycle-3 registers. It splits on `;`, `,` and `|`, tests whole tokens, and ignores placeholders. Recount: 50 tokens in 47 rows (base 27 + 12, cycle-3 10 + 1); candidates rise from 125 to 164. E8-XR-07 is restated, and so is its root-cause sentence: WSB-T-005 holds valid ids and was incomplete, so the tokens did not cause E8-XR-01. E8-CP-11 is widened to all four registers. | `tools/xref_checks.py`, `work/xref_candidates.csv`, `work/build_findings.py`, `work/build_cp.py`, the three CSVs, both findings `.md` files |
| RC-09 | P3 | DONE | E8-XR-03 is re-marked EXISTING (pattern of E8-XR-13). The records are CITATION_LEAD, their review notes say "Cited by Supreme Court in Ravinder Kumar", and `reconciliation/v2.3/04_Case_53_Reconciliation_Queue.csv` lists the URL. The OI-08 comparison is withdrawn. The relabel proposal E8-CP-05 stays. Counts are now 8 NEW (1 P2, 7 P3) and 15 EXISTING. | `work/build_findings.py`, `cross_reference_findings.csv/.md`, `CORPUS_QUALITY_C8_FINDINGS.md`, `C8-SOURCES/README.md` |
| RC-10 | P3 | DONE | (a) A known hash with a contradictory court, case number or date (also within the batch) keeps EXACT_DUPLICATE but gets `flags=METADATA_CONFLICT_WITH_KNOWN_HASH`, a reason and a stderr warning. A new `flags` column is added to the report. (b) Strong classes need a typed case-number match; an untyped match gives POSSIBLE_MATCH_REVIEW. (c) Cells starting with formula characters are prefixed with `'`. (d) Non-UTF-8 input, CSV errors and unreadable corpus files exit 2; a directory or missing-parent `--out` exits 2. (e) Rejected: duplicate JSON keys, duplicate item_id, NUL or other control characters, dates before 1800 or after today, non-string list members, duplicate CSV headers. 13 new tests. The smoke batch was re-run with the same classes. | `tools/reconcile_judgments.py`, `test_reconcile_judgments.py`, `tools/README.md`, `work/smoke_report.csv`, `work/unittest_output.txt` |
| RC-11 | P3 | DONE | Generator rule `SIG_FAIL`, keyed on sha256 138c1da0. D-AMC-AR-034 `verification_status` now carries the caveat: embedded CMS signature does not verify, digest matches (C8 Gazette finding T1-20; re-checked by RC-11); date read from printed text; fidelity class awaits the owner decision. D-SSM-043 gets the gap flag `SIGNATURE_DOES_NOT_VERIFY (T1-20)` and the same note. The dependent C5 chain rows (r.15B, r.16A) are in the frozen C5 register and are not edited. D-AMC-AR-034 is the only matrix row with that hash, and it lists those chain rows. | `PRIMARY-SOURCES/tools/build_c8_d.py`, `amendment_commencement_matrix.csv`, `statutory_source_matrix.csv/.md` |
| RC-12 | P3 | DONE (in part) | AFT-01 and D-SSM-057 now read `NOTIFICATION_STATUS_UNKNOWN (instrument not held ...)` instead of the one-off label. D-SSM-006 gets a new category `OFFICIAL_TEXT_RENDERING` with gap `TEXT_RENDERING_NOT_GAZETTE`, and the category definitions in the `.md` are updated. For multi-copy sources, `c5_holding_state` now shows source-level and copy-level state (D-SSM-004/005/006, 054/055). Not changed: D-AMC-AA-C3-04. It is an extension instrument with no text amendment, its compiled dates are already labelled "per compilation", and NOT_APPLICABLE is the generator's rule for that class. | `PRIMARY-SOURCES/tools/build_c8_d.py`, matrices |
| RC-13 | P3 | DONE | CR-06 now reads "S.O. 4010 of 1986; date as printed to be confirmed: 24-11-1986 per ACQ-01/PILOT-01, 6 December 1986 per the C5 master title". CR-04 marks AO 13/2006/PS as an UNVERIFIED reference known only from the unopened third-party handbook listing (DV-SOH-2014-R4). D-REG-23 is classified `PUBLICLY_AVAILABLE (QUALIFIED: official host reachable; a FOUO marking is reported, release status to be confirmed from the printed copy)`. | `PRIMARY-SOURCES/tools/build_c8_d.py`, `CUSTODIAN_REQUEST_DRAFTS.md`, `regulations_custodian_inventory.csv` |
| RC-14 | P3 | DONE | `build_hr.py`, `build_cp.py` and `build_findings.py` take `REPO_ROOT`, `--out-dir`, `--check` (and `--sample` for build_hr). The `<scratchpad>` and `<c8out>` placeholders are gone; the builders read only the repo's curated JSONL and the committed sample. A new `CORPUS-QUALITY/OUTPUT_SHA256SUMS` is added. The "Output files (c8out/E/)" section and the `work/pdftext.py` reference are replaced by a reproduction section. AFT-032 and V8-JD-02 now cite their uncommitted derived texts by sha256 (c076b890…, e03a7562…, plus WS-B intern copy c6dd2135…). No text dumps are committed. | `CORPUS-QUALITY/work/build_*.py`, `OUTPUT_SHA256SUMS`, `CORPUS_QUALITY_C8_FINDINGS.md`, `high_risk_record_review.csv` |
| RC-15 | P3 | DONE (documented) | The findings doc names `docs/legal-audit/EVIDENCE_STANDARD.md` as the binding scale, keeps the CSV priorities as assigned (local scale), and adds an indicative mapping. E8-XR-01 is a P1 candidate there (missing contrary precedent), and the legal adviser sets it. The F-PROC-006 dispute (reviewer A: P2, provisionally adopted, PILOT-01 post_review D-05) is noted in the findings doc, E8-XR-09, E8-CP-09-CM-011 and the CM-011 high-risk row. The two weak sampler terms (`datedep` matches any year from 1950 to 2029; cases are `tg[:3]` by sort order) are documented in `select_sample.py` and `HIGH_RISK_REVIEW.md` but not changed, because changing them would replace the reviewed sample. | `CORPUS_QUALITY_C8_FINDINGS.md`, `HIGH_RISK_REVIEW.md`, `tools/select_sample.py`, `work/build_*.py` |
| RC-INFO-01..04 | INFO | No action | Confirmations only. | — |

## RC-01: dependency and amendment cells re-checked

Registers consulted:
- ARMY-RULES-CHAIN-01: `army_rules_provision_chronology.csv` and `army_rules_instrument_register.csv`;
- R23-VERIFY-01: `amendment_chain_r23.csv` and `amendment_search_2026-11-22.csv`;
- SOURCE-CONFLICTS-01 and the C5 `source_conflict_register.csv` (C-01, U-01);
- C5 `amendment_register.csv` and `provision_amendment_chain.csv`;
- `PRIMARY-SOURCES/amendment_commencement_matrix.csv` and `pension_source_coverage.csv`;
- CALIBRATION-02 `legal_adviser_questions.csv` (LAQ-05);
- Army Act compilation footnotes (e47a4265, pp.16, 27-28, 35).

| Row | Before | After / result |
| --- | --- | --- |
| HCE-017 | "Act 37/1992 ss.3-5 amended ss.80-81 ... w.e.f. 06-09-1992" | s.4 omitted s.80(j); s.5 omitted s.81(1) (matrix lists s.81(1),(4)). s.3 omitted 'field punishment' in **s.77**, not ss.80-81. 1992 date attributed (AQ-05). |
| EV-016 | "r.23 amended 2022 (S.R.O. per R23-VERIFY-01)" | Register state (RC-01). |
| HCE-010 | "as EV-016" | Explicit register state. |
| CIV-034 | "BSA commencement 01-07-2024" | Compilation footnote (S.O. 849(E)); notification not held; D-AMC-BSA-COMM CNR. |
| AFT-004 | — | Checked; nothing to correct. |
| CIV-008 | "r.197A insertion date not established in chain" | Made precise: no row in any chain register. |
| ADM-022 | "s.26(5) ... substituted by Act 19/1955" | Confirmed (compilation p.16 fn.1). Commencement of Act 19/1955 by S.R.O. 2(E)/1955 is CNR. |
| ADM-021, AFT-009, ADM-023, ADM-027, ADM-015, PEN-019, AFT-035, AFT-039, DCLR-SC-2005-L01, DCLR-SC-2008-N10 | none / "—" / policy or classification wording | Checked; nothing to correct. |
| ADM-013, ADM-014 | "edition/date unknown", "AO 45/2001 currency unknown" | Checked; consistent (sources not held). |
| PEN-001 | "ER 2023 commencement 21-09-2023 (as reported)" | Attributed to the KB records; MoD letter not held; ER2023-APPX-I NOT_HELD_COMPLETE. |
| PEN-013, PEN-WF-08, DCLR-SC-2013-N08 | Isaac / 27-12-2023 letter not held / ER regimes | Consistent with pension_source_coverage (CIRC-BROADBAND-2023 NOT_HELD) and WS-B; unchanged. |
| CM-011 | verification "(inserted by Act 37/1992 s.9)"; dependency "limbs inserted 1992" | The compilation says "Subs. ... s.9, for certain words": now **substituted**. Matrix D-AMC-AA-08-s9 cited. AQ-05 attribution. F-PROC-006 dispute noted. |
| CM-012 | "pre-1992 text was six months (LAQ-05)" | s.10 substitution cited (compilation p.35 fn.2; matrix -s10). Six months attributed to LAQ-05, as not read from a held copy. AQ-05. |
| AFT-032 | "2011 amendment rules (rawtext only)"; scratchpad path | Matrix D-AMC-AFT-05 INSTRUMENT_NOT_HELD. Derived text cited by sha256. |
| COI-046 | "chain gaps AR-030, AR-036" | AR-001 added; register states quoted. |
| CIV-032 | "01-07-2024 commencement" | Compilation footnote (S.O. 848(E)); BNS derived only; CNR. |
| V8-JD-02, V8-JD-03 | "1952 rules (historic)", "CrPC-era" | Unchanged. V8-JD-02 verification now cites its derived text by sha256. |
| CM-SC-18 | "omitted w.e.f. 06-09-1992"; gap "NONE (verified)" | s.11 cited; 1992 date attributed; gap COMMENCEMENT_NOT_STATED (AQ-05 pending). |
| HCE-015 | "06-12-1993" | Confirmed (AR-029, in force on publication, IMAGE_CHECKED). Reference added. |
| SC03 | "r.23 2022 amendment" | Register state for r.23. r.24: no chain row, so its status is stated as not established. |

## Checks run after the corrections (repository root)

| Command | Result |
| --- | --- |
| `python legal_knowledge/audit_work/C8-SOURCES/PRIMARY-SOURCES/tools/build_c8_d.py . --check` | check: OK (16 files reproduce) |
| same, with `--verify-held <held root>` (PyMuPDF environment) | verify-held: OK (67 hashes, 22 page readings, 6 derived readings) |
| `python .../CORPUS-QUALITY/work/build_hr.py . --check` (likewise `build_cp.py`, `build_findings.py`) | check: OK (33 / 24 / 23 rows) |
| `sha256sum -c OUTPUT_SHA256SUMS` in `CORPUS-QUALITY/` | 6 OK |
| `select_sample.py . <tmp> 3` vs `work/sample_selection.csv` | identical |
| `xref_checks.py . <held root> <tmp>` vs `work/xref_candidates.csv` | identical (164 rows) |
| `python tools/legal_audit/check_csv.py` | csv_files=223 errors=0 |
| `python tools/legal_audit/check_provenance.py` | violations=2 known=2 new=0 |
| `python -m unittest tests.test_legal_audit_reconcile_judgments` | 44 tests OK |
| recursive grep of `C8-SOURCES` for the absolute scratchpad path prefix | no match |

## Other correction found while working

`C8-SOURCES/README.md` quoted Girish Kumar as holding Tarsem Singh "of no assistance". The held copy (para 22) says "has no application". The quote is corrected.
