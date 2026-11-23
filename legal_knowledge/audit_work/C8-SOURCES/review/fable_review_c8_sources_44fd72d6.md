# Independent review: C8-SOURCES package at 44fd72d6

Reviewer C. Branch `claude/c8-primary-sources-quality`, base 1a21a2e8. Read-only review; nothing in the worktree was changed (`git status --short --ignored` empty after all runs). No network use, no downloads, no installs. RESEARCH ONLY: this is a technical review and does not sign off for the legal adviser, JAG or the owner.

**Result: one P1, six P2, eight P3.** The primary-source matrices are sound and reproduce. The defects are in the hand-built corpus-quality layer, the reconciliation tool's output guard, and the JUDIS recommendation.

Machine-readable findings: `fable_review_c8_sources_44fd72d6_findings.csv` (19 rows: 15 defects, 4 INFO confirmations).

## Findings by severity

| ID | Sev | Finding |
| --- | --- | --- |
| RC-01 | P1 | `high_risk_record_review.csv` says Army Rule 23 was amended in 2022 (rows EV-016, HCE-010, SC03). Every register, and the package's own matrix, says no amendment to r.23 has been located. |
| RC-02 | P2 | `reconcile_judgments.py` overwrites an input via symlink or hardlink, and overwrites any existing non-input file, including a copy of `records_658.jsonl`. |
| RC-03 | P2 | P-D3 option (b) leaves out PPS Bedi, an existing exact anchor that is the same kind of JUDIS rendition. |
| RC-04 | P2 | Act 20 of 1983 has a known, unheld commencement notification (ACQ03-024) but is not flagged COMMENCEMENT NOTIFICATION REQUIRED. |
| RC-05 | P2 | Four of five neutral-citation proposals cannot be read from the held official copies they name. |
| RC-06 | P2 | The decision pack cites `C8-EVIDENCE/` and `DEMOTION_SEMANTICS_O5.md`, neither of which is in this commit. |
| RC-07 | P2 | "w.e.f. 06-09-1992" for Act 37/1992 is stated as fact in the corpus-quality files, while the matrix holds that commencement as not stated (AQ-05). |
| RC-08 | P3 | E8-XR-07 counts 11 bad `affected_kb_ids` tokens; the base WS-B registers hold about 39 more that the check never scans. |
| RC-09 | P3 | E8-XR-03 is marked NEW although the four records already describe the URL as a citing-document lead, the pattern E8-XR-13 marks EXISTING. |
| RC-10 | P3 | Tool accepts contradictory metadata on a known hash, formula-leading cells, duplicate keys and ids, NUL bytes, future dates; non-UTF-8 input tracebacks. |
| RC-11 | P3 | The S.R.O. 17(E)/2019 file whose signature fails is used as commencement evidence in the matrix with no caveat. |
| RC-12 | P3 | Minor label inconsistencies (Finance Act 2017 gap label; a text rendering classed as a consolidation). |
| RC-13 | P3 | Custodian drafts: CR-06 asserts an unresolved date; CR-04 names an Army Order known only from an unverified lead. |
| RC-14 | P3 | Corpus-quality builders carry a `<scratchpad>` placeholder path and cite an uncommitted `pdftext.py`. |
| RC-15 | P3 | Local priority scale differs from `EVIDENCE_STANDARD.md`; a disputed item is listed as open P1; two weak terms in the sample selector. |

## What was and was not checked

**Checked:** every figure in task 1; all 11 evidenced commencement dates against the held Gazettes; all 42 held rows of the source matrix against manifest and copy register; 8 dependent-record counts; every NEW finding E8-XR-01..09 against registers and, where cited, held text; all 24 correction proposals; the tool under 30 malformed or adversarial inputs; each pack recommendation, with signature and file-profile claims re-tested on held files.

**Not checked:**
- The canonical Hugging Face snapshot was not consulted. Coverage against it is unknown; all results are against the local worktree and scratchpad binaries.
- The 14 EXISTING findings were not re-verified beyond spot checks (E8-XR-12, 13, 14, 19, 21).
- Of the 33 high-risk rows I re-read the statutory text points and the Girish passage; the other judgment readings were not repeated.
- `C8-EVIDENCE/` content and the O-5 design note (not in this commit).
- Archive.org pins and DESW state (offline).
- My page readings are AI readings of text layers and renders. Under the pack's own B2 clarification they are supporting evidence, not confirmation.

**False-pass limits:** a hash match shows the bytes are the ones registered, not that the copy is authentic or current. `--check` shows the builder is deterministic, not that its hand-entered content is right.

## 1. Baseline: confirmed

Recomputed with an independent script from `corpus_crosswalk.csv` and the two JSONL files.

| Figure | Package | Recomputed |
| --- | --- | --- |
| Crosswalk rows with a KB id | 1,060 | 1,060 |
| CITES / NO_CITATION | 983 / 77 | 983 / 77 |
| EXACT / PARTIAL / MISSING (all KB rows) | 42 / 652 / 366 | 42 / 652 / 366 |
| MISSING among genuine citation items | 289 | 289 |
| Records with no exact anchor | 618 | 618 |
| of which cite nothing / cite something | 77 / 541 | 77 / 541 |
| Anchor copy for all 42 | 1954 Army Rules Gazette | `C5-SRC-P0-ARMY-RULES-1954~C1` = 42 |
| KB / case records, sha256 vs frozen manifest | 658 / 53, match | 658 / 53, match |

The correction "1,060 crosswalk rows, 983 citation items" is right.

## 2. Source matrix and amendment/commencement matrix

- **No invented commencement date.** Eleven rows carry `commencement_date_evidenced`. Each instrument prints a commencement clause, and the date equals the Gazette issue date. Read from text layer: S.R.O. 188/1979, 278/1985, 216/1988, 61/1991, 17(E)/1993, 2(E)/2018, 17(E)/2019, 6(E)/2022. Read from page image: S.R.O. 44/1991, 235/1991, 8(E)/2003. The 1988 deemed effect from 04-06-1979 is kept separate.
- **Silent instruments stay undated.** Rows for the 1954 Rules, Act 37/1992, Act 13/1975 and the 1960s S.R.O.s are NOT_STATED or NOT_DETERMINED. I read Act 13/1975 and Act 37/1992: neither has a commencement clause, as the matrix says.
- **Notification flags.** Present for the Army Act (S.R.O. 120/1950), Act 19/1955, AFT Act (S.O. 14(E)/2008), TRA 2026, BNS, BNSS, BSA and the three repeal rows. Missing for Act 20/1983 (RC-04). The Finance Act 2017 row uses a different label (RC-12).
- **Consolidation vs enactment.** Kept apart for every instrument sampled (Army Act, Army Rules, AFT Act, BNSS, BSA; BNS correctly "derived text only"). One mislabel: D-SSM-006 (RC-12).
- **Reserved states preserved** verbatim from the C5 conflict register: r.23(3) CONFLICTING, r.182 OPEN, r.193 OPEN, r.194 PROPOSAL, plus r.192 and r.177 CONFLICTING. The exception is outside the matrix: RC-01.
- **No current-law status** is assigned anywhere in PRIMARY-SOURCES; a scan for "in force / current" assertions found none.
- **Register agreement.** All 42 held rows match the manifest hash, page count, copy class and anchor eligibility. `--verify-held` passes (67 hashes, 22 page readings, 6 derived readings).

Rows sampled: D-AMC-AR-016, 021, 024, 026, 027, 028, 029, 031, 033, 034, 035; D-AMC-AA-00, 01, 06, 07, 08-s11; D-AMC-AFT-00, 01, 03; D-AMC-BNS/BNSS/BSA-COMM; D-AMC-RES-C-01, SC4-01, C-08, C-09; D-SSM-001, 002, 004, 006, 012, 019, 043, 054, 059, 064, 067, 070.

## 3. Dependent-record counts: reproduce; method defensible with one caveat

| Gap | Package | Recomputed | Method |
| --- | --- | --- | --- |
| Army Act as enacted | 185 | 185 | records with a crosswalk row on the Army Act compilation |
| Army Rules, all / chain | 188 / 122 | 188 / 122 (131 items) | PARTIAL rows whose basis is "recorded amendment or reserved conflict" |
| AFT Act | 89 | 89 | as Army Act |
| BSA / BNSS | 64 / 49 | 64 / 49 | as Army Act |
| PRA 2008 Part I | 25 | 25 | code V6-S01 |
| GMO 2023 | 11 | 11 | code V6-S07, unmapped in C5, resolved through v3 |
| AFT Procedure Rules | 43 | 43 | C5 rows (37 records) plus unmapped rows naming the Rules |

Caveat: these are gross counts of citing records. They overlap across gaps and are not additive, and holding the enacted text does not clear a record whose section was later amended. The gap matrix says this in `legal_consequence`; the README table header "Records depending on it" does not.

## 4. Pension coverage: in order

- The held ER 2023 copy (`29f6fa2c`, 13,011,188 bytes) has its own row, is marked incomplete and provenance-undocumented, and is never treated as the complete publication.
- DESW blockers are preserved: allow-list extension, robots 403 fail-closed, A-C5-2.
- Nothing was downloaded; the readiness file states no network call.

## 5. Custodian drafts: in order, three small points

All seven drafts carry "DRAFT — NO CORRESPONDENCE AUTHORISED", are conditional on P-C6-04-SCOPE and A-C5-3, use placeholders only, and state that no restricted material is requested. The D&V handbook remains an unverified lead; the Scribd upload is recorded as not opened and not authoritative. Points: RC-13.

## 6. Corpus quality

| Finding | Verdict | Note |
| --- | --- | --- |
| E8-XR-01 (P2) | Confirmed | Girish `4f7ea3a4` pp.15-16 para 22 reads as quoted. AFT-013 and V7-SC-02 cite Tarsem with no reference to it. No earlier register flags either record. The court's words are tied to "the facts and circumstances"; the proposal leaves scope to legal review. |
| E8-XR-02 (P3) | Confirmed | Mirror-only evidence, correctly conditional. |
| E8-XR-03 (P3) | Fact confirmed, NEW marking doubtful | RC-09. |
| E8-XR-04 (P3) | Confirmed | Exactly six chain rows contradict the amendment register; the other twelve "not yet read" rows are consistent. |
| E8-XR-05 (P3) | Confirmed | C5-CF-C-04 has no pointer to C-08/C-09. |
| E8-XR-06 (P3) | Count confirmed (31), proposal not evidenced | RC-05. |
| E8-XR-07 (P3) | Undercount | RC-08. |
| E8-XR-08 (P3) | Confirmed | Army Act `e47a4265` p.16 s.26(2): "may complain". |
| E8-XR-09 (P3) | Confirmed | Both records carry the status; the three P1 items are PROPOSAL_NOT_APPLIED. F-PROC-006 is recorded as disputed by a reviewer, which the finding omits. |

- **Proposals do not edit originals.** All 24 are PROPOSAL_NOT_APPLIED and framed as overlays or supplements. Twenty are evidenced; four are not (RC-05).
- **Over-claims.** No P1/P2 inflation found. E8-XR-01 may be under-rated against the binding scale (RC-15). Two factual over-statements: RC-01 and RC-07.
- **Sample method.** Deterministic and reproducible (`select_sample.py` and `xref_checks.py` both reproduce byte-for-byte). Three manual additions are disclosed. Weak terms: RC-15.

## 7. Reconciliation tool

25 tests pass under both pytest and unittest. Fails closed (exit 2, no report) on: missing field, null parties, bad or impossible date, NaN, short, uppercase or full-width sha256, invalid JSON, BOM, empty batch, ragged CSV, missing corpus file. Refuses `--out` equal to an input by path, including `..` spellings. Output is deterministic. Unicode party names (Devanagari, dotless i, combining accent, non-breaking space) are handled without error.

Defects:
- **Overwrites (RC-02).** Symlink to an input, hardlink to an input, and any existing non-input file are all overwritten with exit 0. Tested only on copies in my temp directory.
- **Fail-open classification (RC-10).** A known hash with wholly different court, case number, date and parties is EXACT_DUPLICATE with no warning. An untyped `6820/2018` with unrelated parties is SAME_JUDGMENT_NEW_COPY.
- **Input hygiene (RC-10).** Formula-leading cells pass to the CSV unchanged; duplicate JSON keys, duplicate `item_id`, NUL bytes and year-2999 dates are accepted; non-UTF-8 CSV and a directory `--out` raise tracebacks (exit 1).

## 8. Rule-version pack

| Item | View | Reason |
| --- | --- | --- |
| A3 (only with B2) | Agree | Counts match the Cycle 7 data file (3 SOURCE_LOCATED records). Coupling to B2 is right: a located record plus a page-1 text match should not create an anchor. |
| B2 with AI-reader clarification | Agree | An AI reading has no accountable reader. The same limit applies to my readings here. The "39 Gazette and 28 court checks" are not in this commit (RC-06). |
| C2 | Agree, with a condition | `/details/` and `/download/` are different resources; the alias must be item identity plus a hash, not URL equivalence. Keeping the court-path alias out until bytes are compared is right. Tests should include path case and percent-encoding not being folded. |
| Fidelity split for a failing signature | Agree | Reproduced: 2018 verifies, 2019 fails at the signature while the digest matches, confirmed by a manual RSA check, so it is not an encoding artefact of one tool. Call the class "signature does not verify" rather than implying tampering, and carry the limitation into the matrix (RC-11). The test list sends unsigned files down "the scanned-facsimile route", but S.R.O. 6(E)/2022 is unsigned and text-layer, not a scan; that case needs its own class. |
| JUDIS option (b) | Disagree as written | Direction is defensible; the file facts reproduce. But PPS Bedi, already anchored as primary, is the same kind of file (RC-03). Either (b) demotes it too, giving 6 → 9, or the pack must say why not. I would take (c) as the stated end state, since the Ranjit headnote note shows the specific risk is headnote text and later orders, not the judgment body. |
| O-1 / O-4 | Agree | Decide before the first BIND line. A committed identity list alone is self-asserting, as the pack says. |
| O-5 activation policy 2 | Cannot assess | The design note is not in this commit (RC-06). In principle "demote now, promote staged" is the safe asymmetry, but it needs an answer to who may issue a demotion, or it becomes a way to strip anchors. |

## 9. Reproducibility and hygiene: pass

```
python legal_knowledge/audit_work/C8-SOURCES/PRIMARY-SOURCES/tools/build_c8_d.py . --check
  -> check: OK (16 files reproduce)
python .../build_c8_d.py . --check --verify-held <scratchpad>
  -> verify-held: OK (67 hashes, 22 page readings, 6 derived readings)
sha256sum -c PRIMARY-SOURCES/OUTPUT_SHA256SUMS      -> 15 OK
python tools/legal_audit/check_csv.py               -> csv_files=222 errors=0
python tools/legal_audit/check_provenance.py        -> files=222 violations=2 known=2 new=0 baseline_absent=1
python -m pytest -q -p no:cacheprovider tests/test_legal_audit_reconcile_judgments.py -> 25 passed
git diff --name-only 1a21a2e8 44fd72d6 | grep -v '^legal_knowledge/audit_work/C8-SOURCES/' -> tests/test_legal_audit_reconcile_judgments.py only
```

- No protected path changed: `curated_originals/`, `data/`, `schema/`, `crawler/`, `pipeline/`, `config/` untouched.
- No absolute scratchpad path, no email address, no document text dump. Relative scratchpad paths appear as provenance notes, and as a broken placeholder in two builders (RC-14).
- The corpus-quality layer has no `--check` or checksum file, unlike PRIMARY-SOURCES (RC-14).

## Conditions for acceptance

1. Correct RC-01 before merge and re-check the dependency cells of the high-risk review.
2. Fix the output guard (RC-02) or withdraw the "never overwrites" claims until fixed.
3. Restate P-D3 with PPS Bedi (RC-03) and make the pack's evidence reviewable (RC-06) before any owner decision is taken on it.
4. Apply the notification flag to Act 20/1983 (RC-04), reclassify the four neutral-citation proposals (RC-05), and attribute the 1992 date (RC-07).

P3 items can follow in the next cycle.

VERDICT: ACCEPT WITH CONDITIONS

Model identity: Fable 5.2 (claude-fable-5-2), acting as independent reviewer C.
