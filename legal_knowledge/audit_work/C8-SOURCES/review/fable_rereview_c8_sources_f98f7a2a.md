# Focused re-review: C8-SOURCES corrections at f98f7a2a

RESEARCH ONLY. This is a technical re-check of the corrections to the review of 44fd72d6. It is not a legal sign-off and it does not approve any record, source or rule. A hash match proves integrity only, not authenticity, currency or legal correctness.

- Commit reviewed: f98f7a2a (branch claude/c8-primary-sources-quality, base 1a21a2e8); correction diff 44fd72d6..f98f7a2a.
- Worktree was read-only and is clean after all runs. Experiments ran in a temporary copy under the scratchpad.
- Canonical private HF snapshot: not accessed (no network). Coverage against it is unknown.
- One side effect of my own testing: an attack run replaced `/dev/null` in the review container with a regular file (finding RR-01). I restored the device node with `mknod` (c 1 3, mode 666). Nothing in the repository or held library was affected.

## 1. Status of RC-01 to RC-15

| ID | Sev | Status | Evidence |
| --- | --- | --- | --- |
| RC-01 | P1 | CLOSED | No "amended 2022" text remains outside the review folder and the correction note. EV-016, HCE-010 and SC03 now match all registers. All 33 dependency cells re-checked (section 2). Residual P3s: RR-04, RR-05, RR-06. |
| RC-02 | P2 | CLOSED, with a new defect | Symlink, hardlink, `..` path, input with `--overwrite`, `curated_originals` (direct, via symlinked directory, via dangling symlink) and existing file are all refused with exit 2; inputs hash-identical afterwards. A hardlink to `records_658.jsonl` with `--overwrite` is safe, because the write is a rename and never goes through the link. New: RR-01 (P2), RR-02 (P3). |
| RC-03 | P2 | CLOSED | PPS Bedi facts confirmed on the held file; 6 → 9 is right (section 3). |
| RC-04 | P2 | CLOSED | D-AMC-AA-07 and D-SSM-012 carry COMMENCEMENT NOTIFICATION REQUIRED. The 12 flagged matrix rows equal the README list. No date added to `commencement_date_evidenced` (still the same 11 Army Rules rows). |
| RC-05 | P2 | CLOSED | Full-text search of the five held copies: only 4f7ea3a4 prints an INSC number (2026 INSC 149). Four rows are now UNVERIFIED_LEAD_NO_PROPOSAL; 20 proposals plus 4 leads = 24. |
| RC-06 | P2 | PARTIALLY CLOSED | Evidence location is now disclosed by branch, with an instruction to wait for those reviews. The files are still not in this commit and are not pinned by commit hash (RR-08). |
| RC-07 | P2 | CLOSED | Every "6-9-1992" in the package is attributed; CM-SC-18 gap is COMMENCEMENT_NOT_STATED (AQ-05 pending). Residual precision point: RR-04. |
| RC-08 | P3 | CLOSED | Independent recount: 27 + 12 + 10 + 1 = 50 tokens in 24 + 12 + 10 + 1 = 47 rows; `xref_candidates.csv` has 164 rows, 50 of them X14b. |
| RC-09 | P3 | CLOSED | E8-XR-03 is EXISTING; counts 8 NEW (1 P2, 7 P3) and 15 EXISTING recomputed from the CSV. |
| RC-10 | P3 | CLOSED | (a) conflict flag and warning present, also within a batch; (b) untyped number gives POSSIBLE_MATCH_REVIEW; (c) leading `=`, `+`, `-`, `@`, TAB, CR neutralised, including after whitespace normalisation; (d), (e) all listed cases exit 2. Residual: RR-03. |
| RC-11 | P3 | CLOSED | D-AMC-AR-034 and D-SSM-043 carry the signature caveat; it is the only matrix row with hash 138c1da0. The frozen C5 chain rows were correctly left unedited. |
| RC-12 | P3 | CLOSED | AFT-01 and D-SSM-057 use NOTIFICATION_STATUS_UNKNOWN; D-SSM-006 is OFFICIAL_TEXT_RENDERING with copy-level state. Declining to change D-AMC-AA-C3-04 is reasoned and acceptable. |
| RC-13 | P3 | CLOSED | CR-06, CR-04 and D-REG-23 read as stated in the dispositions. |
| RC-14 | P3 | CLOSED | All three builders run from the repo with `--check` and `--out-dir`; output byte-identical; checksum file verifies; no placeholder or scratchpad path. |
| RC-15 | P3 | CLOSED (documented) | Binding scale named, mapping added, F-PROC-006 dispute noted, weak sampler terms documented and left unchanged so the reviewed sample is stable. |

## 2. RC-01: independent re-check of the high-risk review cells

Checked against: ARMY-RULES-CHAIN-01 (chronology, instrument register), R23-VERIFY-01 (`amendment_chain_r23.csv`, `amendment_search_2026-11-22.csv`), SOURCE-LIBRARY-C5 (`source_conflict_register.csv`, `provision_amendment_chain.csv`), `amendment_commencement_matrix.csv`, `pension_source_coverage.csv`, CALIBRATION-02 `legal_adviser_questions.csv`, WS-B `subsequent_treatment.csv`, and the held files below.

**The two newly reported corrections are right.**
- HCE-017: the held Gazette of Act 37 of 1992 (f11d443e, p.1; text layer and page image) reads "3. In section 77 of the principal Act, the words ', field punishment' shall be omitted" and "4. In section 80 ... clause (j) shall be omitted"; p.2 s.5 omits s.81(1) and amends s.81(4). The compilation (e47a4265, p.27 fn.1 and fn.3, p.28 fn.1-2) agrees.
- CM-011: Gazette p.2 s.9 (text layer and page image): "for the words 'from the date of such offence', the following shall be substituted". The compilation p.35 fn.1 reads "Subs. by Act 37 of 1992, s. 9, for certain words". "Substituted" is correct; "inserted" was wrong.

**Other cells confirmed.**
- EV-016, HCE-010, SC03: chronology r.23 "NO AMENDMENT LOCATED (31 instruments examined ...)"; C5-CF-U-01 "31 in total, 1960-2022 ... none amends r.23"; S.R.O. 6(E)/2022 amends r.16A(4), `amends_r23` NO; AR-001, AR-030, AR-036 are GAP rows. r.24 and r.197A have no row in either chain register. The compilation prints r.197A at p.210.
- HCE-015: AR-029, S.R.O. 17(E)/1993, in force on publication 06-12-1993, IMAGE_CHECKED; compilation p.45 "Omitted vide SRO 17.E dated 6.12.93".
- ADM-022: compilation p.16 fn.1 "Subs. by Act 19 of 1955, s. 2 and the Sch."; matrix D-AMC-AA-01 is CNR.
- CM-012: Gazette p.3 s.10 and compilation p.35 fn.2.
- CM-SC-18: Gazette p.3 s.11; compilation p.36 prints "(w.e.f. 6-9-1992)" for s.127; the Act prints no commencement clause on pp.1-4.
- CIV-034, CIV-032: BSA p.10 fn.1 (S.O. 849(E), 23 February 2024) and BNSS p.18 fn.1 (S.O. 848(E), with the s.106(2) exception) read as stated; matrix rows are CNR.
- AFT-032 (D-AMC-AFT-05 INSTRUMENT_NOT_HELD), PEN-001 (ER2023-APPX-I NOT_HELD_COMPLETE; C5-CF-C5-03), PEN-WF-08 (CIRC-BROADBAND-2023 NOT_HELD), COI-046 (C5-CF-C5-04) match their registers.
- Rows with "—", "none located" or policy wording (AFT-004, ADM-021, AFT-009, ADM-013, ADM-023, ADM-027, ADM-014, ADM-015, PEN-019, V8-JD-02, V8-JD-03, AFT-035, AFT-039, L01, N10): no register entry contradicts them. I did not search outside the registers for amendments to these provisions.

**Residual defects (all P3).**
- RR-04: for s.77, s.80, s.81, s.122 and s.123 the compilation footnotes print no date. "(w.e.f. 6-9-1992)" appears only at ss.75-76 (p.27), s.127 (p.36) and Chapter XVI (p.48). HCE-017, CM-011 and CM-012 attribute the date to the compilation for provisions where it is not printed.
- RR-05: the gap list omits the hint rows AR-012, AR-013, AR-015 (HINT_ONLY, TO_CHECK) that the chronology names next to the three gaps.
- RR-06: DCLR-SC-2013-N08 cites WSB-T-008 (the Rajbir row); the Dharamvir row is WSB-T-007. PEN-013 says Isaac "applies ER 2008 r.7 to earlier claims"; para 39(iii) and the register say claims made after fifteen years.

No invented amendment, date or citation remains in these cells.

## 3. RC-02, RC-10 and RC-03 detail

**Output guard (sandbox copy; inputs hashed before and after).**

| Attack | Result |
| --- | --- |
| existing file, no flag | exit 2 |
| symlink to `cases_53.jsonl`, with and without `--overwrite` | exit 2 |
| hardlink to `cases_53.jsonl`, with and without `--overwrite` | exit 2 |
| hardlink to `records_658.jsonl` (not an input), `--overwrite` | exit 0; link replaced by rename, original unchanged |
| symlink to `records_658.jsonl`; symlinked directory into `curated_originals`; dangling symlink into it; new file inside it | exit 2 |
| `--incoming` path, also via `o/../b.jsonl`, with `--overwrite` | exit 2 |
| directory; missing parent | exit 2 |
| non-input register under the repo, `--overwrite` | exit 0, register replaced (RR-02) |
| `/dev/null` and a FIFO, `--overwrite` | exit 0, special file replaced by a regular file (RR-01) |

Races: without `--overwrite` the switch is `os.link`, which cannot clobber. With `--overwrite` it is `os.replace`, which replaces the directory entry and never follows a symlink planted between check and switch. No temporary file was left behind in any run. The fallback to `os.replace` when `os.link` raises a non-EEXIST error has a small clobber window on filesystems without hard links; not reproduced.

**Malformed input.** About 80 batches over two rounds. All listed RC-10 cases exit 2 with no report. Residual cases are in RR-03: deep nesting gives a traceback and exit 1; non-string scalars are stringified; a CSV BOM silently drops `item_id`.

**RC-03.** Held file `ppsbedi_judis9884.pdf`: sha256 211dbaf4e20371cc476d09c158e41b976786d57f67336ff6fc802170178b3cca recomputed; producer "GNU Ghostscript 7.05"; 38 pages; first page "http://JUDIS.NIC.IN / SUPREME COURT OF INDIA / Page 1 of 38"; HEADNOTE present; copy register row C5-SRC-J-SC-1982-PPS-BEDI~C1, DOCUMENTED_PRIMARY_COPY, eligible YES. A scan of every held PDF finds exactly four files of this kind; the other three (Ranjit ed7cf31f, S N Mukherjee eb442080, Navjot 3b753548) are eligible NO. Arithmetic: on the pack's own 13 under option (a), option (b) is 13 − 3 drafts − 1 baseline = 9. The "13" itself rests on PR B and was not checked.

## 4. Regressions

| Check | Result |
| --- | --- |
| `build_c8_d.py . --check` | OK (16 files reproduce) |
| `build_c8_d.py . --check --verify-held <held root>` | OK (67 hashes, 22 page readings, 6 derived readings) |
| `build_hr.py`, `build_cp.py`, `build_findings.py` `. --check` | OK (33 / 24 / 23 rows); `--out-dir` output byte-identical |
| `sha256sum -c OUTPUT_SHA256SUMS` | CORPUS-QUALITY 6 OK; PRIMARY-SOURCES 15 OK |
| `select_sample.py`, `xref_checks.py` | byte-identical to committed outputs |
| `tools/legal_audit/check_csv.py` | csv_files=223 errors=0 |
| `tools/legal_audit/check_provenance.py` | violations=2 known=2 new=0 |
| `python -m unittest tests.test_legal_audit_reconcile_judgments` | 44 tests OK |
| `python -m unittest discover -s tests -p "test_legal_audit_*.py"` in a committed copy | 567 tests OK, 6 skipped |
| Paths changed since 1a21a2e8 | only `C8-SOURCES/` and `tests/test_legal_audit_reconcile_judgments.py` |
| Originals and protected paths | none changed; no absolute scratchpad path, email address, text dump or binary committed |
| Legal status, new dates | no status changed; every date added by the correction diff traces to a register, a held document or synthetic test data |

## 5. Over-claims

- No new legal over-claim found.
- RR-07: the dispositions file says RC-03 and RC-06 are not addressed, though this commit changes the decision pack for both.
- RR-04 is an over-attribution to the compilation, in the cautious direction as to the conclusion.
- "Separate commencement notification under s.1(2) of Act 20/1983 known" rests on the acquisition schedule entry ACQ03-024 (candidate, not fetched); Act 20/1983 itself is not held. The row says "not held" and gives no date, so I do not raise it as a finding.

## 6. Not checked

- The canonical HF snapshot, and anything requiring network access.
- The C8-EVIDENCE and DEMOTION_SEMANTICS_O5 material on the other branches.
- Correctness of hand-entered builder content beyond the cells and rows named above.
- Legal correctness of any proposition; that is for the legal adviser and JAG.

## Findings

See `fable_rereview_c8_sources_f98f7a2a_findings.csv`: 1 P2 (RR-01), 7 P3 (RR-02 to RR-08), 3 INFO.

Conditions for acceptance: fix RR-01 before the tool is used with `--overwrite`; correct RR-04 to RR-07 in the next regeneration; pin or stack the evidence for RR-08.

VERDICT: ACCEPT WITH CONDITIONS

Reviewer model: Fable 5.2 (claude-fable-5-2)
