# Narrow confirmation: C8-SOURCES corrections at 0e75a4a3

RESEARCH ONLY. This is a technical check of the corrections to the focused re-review of f98f7a2a. It is not a fresh full review, not a legal sign-off, and it approves no record, source or rule. A hash match proves integrity only, not authenticity, currency or legal correctness.

- Commit checked: 0e75a4a3 (branch claude/c8-primary-sources-quality); correction diff f98f7a2a..0e75a4a3 (10 files).
- The worktree was not modified and is clean after all runs. Tool experiments ran in a `git archive` copy inside a `mktemp` directory under the scratchpad.
- No path outside that directory was passed to the tool. `/dev/null` is still a character device (1, 3) after the runs. Device nodes were not created; the device case was checked by mocking `os.lstat` on a temp file.
- Canonical private HF snapshot: not accessed (no network). Coverage against it is unknown.

## 1. Status of RR-01 to RR-08

| ID | Sev | Status | Evidence |
| --- | --- | --- | --- |
| RR-01 | P2 | CLOSED | With `--overwrite`, a FIFO, a Unix socket, a symlink to a regular file, a dangling symlink and a symlink to a FIFO are all refused with exit 2 ("not a regular file"); each keeps its type and the symlink target is unchanged. Mocked character-device, block-device and socket modes are refused. The check also runs on the re-check before the rename. |
| RR-02 | P3 | CLOSED for `--repo` mode; residual C3-01 | With `--repo`, an existing in-repo file is refused with `--overwrite` (register, `CLAUDE.md`, `data/text/.gitkeep`; also through `..`, a symlinked directory, and `--repo` given with a trailing slash, as a symlink, or as `.`). Without `--repo` (explicit corpus files) the same register is still replaced. |
| RR-03 | P3 | PARTIALLY CLOSED (as disclosed) | Three deep-nesting shapes exit 2 with no report and no traceback. Still open, as the dispositions say: a CSV BOM drops `item_id` (exit 0, `line2`), and `court=5`, `parties=7` are accepted (exit 0). |
| RR-04 | P3 | CLOSED | Held compilation (sha256 recomputed, 51 pages, text layer): "(w.e.f. 6-9-1992)" is printed on p.27 (ss.75, 76), p.36 (s.127) and p.48 (Chapter XVI) and nowhere else. The footnotes on pp.27, 28 and 35 for ss.77, 80, 81, 122, 123 carry no date. The new wording in HCE-017, CM-011, CM-012 and CM-SC-18 matches this. |
| RR-05 | P3 | PARTIALLY CLOSED (C3-02) | EV-016 and SC03 now name the hints AR-012, AR-013, AR-015, which the instrument register lists as HINT_ONLY / TO_CHECK. HCE-010 and COI-046 still list only AR-001, AR-030, AR-036. The re-review asked for all four cells; the dispositions say "Fixed". |
| RR-06 | P3 | CLOSED | DCLR-SC-2013-N08 cites WSB-T-007, which is the Dharamvir row. PEN-013 now reads "claims made after fifteen years (Isaac para 39(iii); WSB-T-007, WSB-T-008)". Held Isaac copy 3f49a314 (sha256 recomputed) p.93 para 39(iii): "If a claimant approaches the relevant forum after a period of fifteen years, the principle in Rule 7 of the Entitlement Rules 2008 applies and the burden shifts." |
| RR-07 | P3 | PARTIALLY CLOSED (C3-04) | The scope line of `DISPOSITIONS_44fd72d6.md` now says the coordinator addressed RC-03 and RC-06 in the same commit. Table rows 14 and 17 still read "NOT DONE HERE" with no file named. |
| RR-08 | P3 | CLOSED | Both pins resolve in this clone: `152045bd` is on `claude/c8-evidence-verification` and holds 106 files under `C8-EVIDENCE/`; `81df0e6c` is on `claude/c8-security-closeout` and holds `AUTH-LEDGER/DEMOTION_SEMANTICS_O5.md`. The re-review recorded at `152045bd` ends "VERDICT: ACCEPT". The files remain outside this commit, which the pack states. |

## 2. Output guard runs (RR-01, RR-02)

All runs used `--repo <copy>` unless stated. The copy and a sentinel file were hashed (content and tree listing) before and after.

| `--out` target | Flag | Exit | Result |
| --- | --- | --- | --- |
| new file outside the repo | none | 0 | written |
| new file outside the repo | `--overwrite` | 0 | written |
| existing regular file outside the repo | none | 2 | unchanged |
| existing regular file outside the repo | `--overwrite` | 0 | replaced by the report |
| FIFO | none / `--overwrite` | 2 / 2 | still a FIFO |
| Unix socket | `--overwrite` | 2 | still a socket |
| symlink to a regular file | none / `--overwrite` | 2 / 2 | still a symlink; target unchanged |
| dangling symlink; symlink to a FIFO | `--overwrite` | 2 | unchanged; nothing created at the target |
| existing register inside the repo | none / `--overwrite` | 2 / 2 | unchanged |
| same register via `..` or a symlinked directory | `--overwrite` | 2 | unchanged |
| `records_658.jsonl` | `--overwrite` | 2 | refused by the `curated_originals` rule |
| hard link from outside to an in-repo register | `--overwrite` | 0 | the link is replaced; the register is unchanged (link count back to 1) |
| new file inside the repo | none / `--overwrite` | 0 / 0 | written (allowed by design) |
| existing in-repo register, explicit corpus files, no `--repo` | `--overwrite` | 0 | register replaced (C3-01) |

- Only the permitted cases wrote. After removing the new files I created, the copy hashed the same as before. No temporary file was left by any of these runs.
- One harness error of mine, inside the copy only: I assumed `data/manifest.csv` existed; it did not, so the tool correctly created it as a new file. I removed it and re-ran the affected cases.

**Race between the re-check and the rename.** I forced the interleaving by wrapping `os.replace` so that the target changes after the re-check.

| Change made in the window | Exit | Result |
| --- | --- | --- |
| regular file swapped for a FIFO | 0 | the FIFO is replaced by the report |
| regular file swapped for a symlink to an in-repo register | 0 | the symlink itself is replaced; the register is unchanged |
| parent directory swapped for a symlink to an in-repo directory | 2 | rename fails (temp file not found); register unchanged; the temp file stays in the moved directory |

The window exists but needs write access to the output directory at that moment, so it cannot reach `/dev/null` or a path in a directory the attacker does not already control. `os.replace` never follows a symlink at the final component. Recorded as INFO (C3-05).

## 3. Regressions

| Check | Result |
| --- | --- |
| `build_c8_d.py . --check` | OK (16 files reproduce) |
| `build_c8_d.py . --check --verify-held <scratchpad>` | OK (67 hashes, 22 page readings, 6 derived readings) |
| `build_hr.py`, `build_cp.py`, `build_findings.py` `. --check` | OK (33 / 24 / 23 rows) |
| `sha256sum -c OUTPUT_SHA256SUMS` | CORPUS-QUALITY 6 OK; PRIMARY-SOURCES all OK |
| `python -m unittest tests.test_legal_audit_reconcile_judgments` | 47 tests OK |
| `tools/legal_audit/check_csv.py` | csv_files=224 errors=0 |
| `tools/legal_audit/check_provenance.py` | files=224 violations=2 known=2 new=0 baseline_absent=1 |
| Paths changed since 1a21a2e8 | only `C8-SOURCES/` and `tests/test_legal_audit_reconcile_judgments.py` |
| Absolute scratchpad paths | none in the diff or in `C8-SOURCES/` at 0e75a4a3 |
| Rows changed in `high_risk_record_review.csv` | 8: HCE-017, EV-016, PEN-013, CM-011, CM-012, CM-SC-18, SC03, DCLR-SC-2013-N08; no status or date added |

## 4. New findings

- **C3-01 (P3).** The RR-02 guard works only when `--repo` is passed. In explicit-corpus mode an existing register inside a repository is still replaced under `--overwrite`. The README "Known limits" line still says the guard "does not refuse other paths under `--repo`", and neither the README guard list nor the module docstring mentions the regular-file rule or the in-repo rule.
- **C3-02 (P3).** RR-05 is half done: HCE-010 and COI-046 still omit the three hint rows. The dispositions record "Fixed".
- **C3-03 (P3).** Test count is stale: the README says 44 tests and `work/unittest_output.txt` records a 44-test run; the suite now has 47.
- **C3-04 (INFO).** `DISPOSITIONS_44fd72d6.md` rows for RC-03 and RC-06 still say "NOT DONE HERE".
- **C3-05 (INFO).** Residual race window described in section 2.
- **C3-06 (INFO).** The matrix rows D-AMC-AA-08-s2 to -s19 all carry "India Code 'w.e.f. 6-9-1992' = assent date, compiler inference", including rows for provisions where the compilation prints no date. The re-review made this optional ("consider"); it is unchanged.

No new legal over-claim was found in the changed cells.

## 5. Not checked

- The canonical HF snapshot, and anything needing network access.
- A real device node as `--out` (forbidden by the safety rule; mocked instead).
- Whether 6-9-1992 is the assent date of Act 37 of 1992 (unchanged text; accepted in the earlier reviews from the held Gazette).
- The 39/28 counts and the "13" figure at the pinned commits; only the existence of the pinned files and the recorded verdict were checked.
- Any cell or row outside the eight changed rows and the registers named above. Legal correctness of any proposition is for the legal adviser and JAG.

## 6. False-pass limits

- The guard checks ran as root on one Linux filesystem. Behaviour on filesystems without hard links, or on other platforms, was not tested.
- The page checks use the PDF text layer of held copies. A matching hash says the bytes are the held bytes, nothing more.
- Passing `--check` shows the outputs reproduce from the builders. It does not show the hand-entered builder content is right.

Conditions (none blocks use of the tool with `--repo`): correct C3-01 to C3-03 in the next regeneration, and either finish RR-05 and RR-07 or change their dispositions to "partly fixed".

VERDICT: ACCEPT WITH CONDITIONS

Reviewer model: Fable 5.2 (claude-fable-5-2)
