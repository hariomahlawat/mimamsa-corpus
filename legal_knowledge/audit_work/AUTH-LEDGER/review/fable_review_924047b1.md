# Independent review of AUTH-LEDGER-02 at 924047b1 (base 63a79729)

Reviewer: Fable 5.2 (model id claude-fable-5-2), acting as database and evidence validation agent. RESEARCH ONLY. This review is a technical check. It is not owner approval, legal approval or JAG approval, and it signs off for nobody.

## Result
No P1 finding. Three P2 findings must be corrected before merge. Ten P3 and two INFO findings follow. Full detail, reproduction and required correction for every finding are in `fable_review_924047b1_findings.csv`.

| Severity | Count |
| --- | --- |
| P1 | 0 |
| P2 | 3 |
| P3 | 10 |
| INFO | 2 |

## False-pass limitations (read first)
- **A matching sha256 proves bit integrity only.** All 20 tranche-1 held files were re-hashed from the scratchpad download directory and match. That says nothing about authenticity, currency or legal correctness.
- **The canonical Hugging Face dataset was not consulted** (no network). Coverage against it is unknown.
- **No page image was re-read.** Identity findings below compare committed register text with committed register text.
- **No signature was validated.** Signature statements are structural facts from `evidence/copy_structure.csv`.
- **No GitHub fact was checked** (PRs, reviews, branch protection).
- **Mutation testing used one simple operator set** (541 mutants). A killed mutant is not proof of a correct control.
- **Tests ran on git 2.43.0 only.**

## How the work was done
- The worktree was not modified. Two trees were exported with `git archive` (head 924047b1 and base 63a79729) into `scratchpad/fr_gR83` and `scratchpad/fr_gR83_base`, each made a throwaway git repository.
- Experiment scripts are in `scratchpad/fr_scripts/` (`url1.py`, `bind1.py`, `bind2.py`, `drafts.py`, `tr1.py`, `tr2.py`, `mut.py`). Mutation results are in `scratchpad/fr_mut/log.txt` and `results.json`.

## P2 findings

### F-01 BIND verification can be forged with replace refs, grafts or GIT_DIR (`tools/binding.py`)
`_git()` inherits the caller's environment and does not disable replace objects or grafts.

| Case | Set-up | Result |
| --- | --- | --- |
| A1 | version added by direct commit; `git replace --graft <c2> <base> <c1>` | `APPLIED`, `bound_by 2` |
| A1b | same, with `.git/info/grafts` | `APPLIED` |
| A2 | merge that alters `decisions/R-v0001.md`, hidden by `git replace <evil> <clean>` | `APPLIED` |
| A8 | `GIT_DIR` set to another repository holding a proper merge | `APPLIED` |

With `GIT_NO_REPLACE_OBJECTS=1` and `GIT_GRAFT_FILE=/dev/null` the same cases are rejected ("merge_commit has 1 parent(s)"), so the correction is small. Replace refs do not travel with an ordinary clone, but they do travel with a copied directory, a mirror clone, or a bundle that includes `refs/replace`, which is how an offline verifier would receive the repository.

Required: a minimal environment with every `GIT_*` variable removed, `GIT_NO_REPLACE_OBJECTS=1`, an empty graft file, `-c core.commitGraph=false`, fail closed when `refs/replace/*` or `info/grafts` exist, and one test per vector.

### F-02 Tranche finding F-T1-1 is contradicted by committed data
`TRANCHE1_FINDINGS.md` says that for 7 rows the S.R.O. number and date line are "not independently evidenced in a committed observation". They are transcribed, with a render hash and status `LOCATED_IMAGE_CHECKED`, in `R23-VERIFY-01/registers/amendment_search_2026-11-22.csv`, which every one of those pending entries already cites as an `L5` evidence reference.

| Row | Quotation in the amendment-search register |
| --- | --- |
| T1-02 | 'New Delhi, the 5th January 1963 S.R.O. 34.-In pursuance of clause (e) of rule 188...' |
| T1-11 | 'CORRIGENDUM New Delhi, the 1st April, 1985 S.R.O. 68.-' |
| T1-14 | 'New Delhi, the 18th September, 1987 S.R.O. 302' |
| T1-16 | 'New Delhi, the 26th September, 1989 S.R.O. 332' |
| T1-17 | '1st February, 1991 S.R.O. 44' and '7th February, 1991 S.R.O. 61' |
| T1-18 | 'New Delhi, the 1st October, 1991 S.R.O. 235' |
| T1-19 | 'New Delhi, the 20th February, 2018 S.R.O. 2(E).-' |

The builder scans only the records named in `identity_refs`. The accurate statement is narrower: the transcription exists in a discovery-stage register that rule 1 does not accept as an identity reference, and not in an independent image check. The error is in the cautious direction, but the 12 / 6 / 2 split, the "1A-READY only" simulation, decision-pack text B1 and the readiness note all depend on it.

### F-03 "Every second spelling is rejected" is not true
The claim appears in the `urlcheck.parse` docstring, `DESIGN_NOTES.md` D-12 and decision-pack section C. Accepted pairs for the same resource:
- `.../b@c` and `.../b%40c` (any encoded sub-delimiter, `:` or `@`);
- `https://archive.org/download/a/b` and the same with `?x`;
- `https://egazette.nic.in/a` and `.../a/`;
- reordered query parameters.

In committed data, 10 archive.org items are recorded under both `/details/<item>` and `/download/<item>/<file>`. None is a contradiction today (same sha256 under both). Exposure is limited because `official_locator_recorded` must equal the URL in a pinned first-class record. The documents should say what remains open, and recommendation C should not rest on the claim.

## P3 and INFO findings (one line each; detail in the CSV)
- **F-04 (P3)** Change-after-review compares only the manifest and pinned files. A merge that changes tools, tests or other files verifies (case A7). `APPROVAL_CONTROLS.md` states the residual as none.
- **F-05 (P3)** `VERIFIED_OFFLINE` proves merge topology only. A local `--no-ff` merge with invented PR, review and repository values is `APPLIED` (cases A3, A4, A13). This is disclosed, but `transitions.json` does not carry the asserted status.
- **F-06 (P3)** Per-class path rules exist only for archive.org. `https://gov.in/x`, `https://nic.in/x`, directory paths, redirect-style queries and any `*.nic.in` host pass a government class.
- **F-07 (P3)** Encoded fullwidth dots and solidus, a bidi override, C1 controls, `..%20` and `...` segments are accepted. Malformed UTF-8 is rejected in the path only through an incidental `UnicodeDecodeError`, and is accepted in the query.
- **F-08 (P3)** `strength.URL` truncates a recorded URL at `)`, `,`, `;` or `|` before the strict check; the truncated string passes. No committed record is affected (144 URLs scanned).
- **F-09 (P3)** The AI-name deny-list accepts "Fable5", "claude_code", "GPT4", "Codex" and rejects "Claude Shannon" and "Ai Weiwei".
- **F-10 (P3)** A manifest line date of "9999-99-99 not a date" is accepted and disables the record-date check; `true` and `1.0` are accepted for `version` and `rule_version`.
- **F-11 (P3)** Mutation survivors: 78 of 541 (see below).
- **F-12 (P3)** Pending rows: T1-02 identity text says "notes misdate as 05-06-1963" beside "UNVERIFIED"; limitations lack the identity and structural-only wording; a scanned-page phrase is applied to the two text-layer files; truncated matrix fields.
- **F-13 (P3)** Decision pack: numbers reproduce, three conclusions need qualification (see below).
- **F-14 (INFO)** Withdrawals are also staged until a BIND line; a snapshot without `.git` cannot verify a bound ledger.
- **F-15 (INFO)** `https://1.0x7f/x` passes `urlcheck` alone; `GIT_NO_LAZY_FETCH` is unknown to git 2.43.

## Challenge to the rule decision pack
Every number in `RULE_DECISION_PACK_data.json` was recomputed from the registers and agrees: 32 drafts; first-class kinds ARC 14, RET 13, COR 4, DL 1; retrieval states 10 verified and 3 located; identity basis 22 / 9 / 1; 75 pairs and 74 URLs; one exact contradiction (India Code bitstream `7a05a1f5`). The 7 anchor-creating entries were recomputed with the reader, singly and jointly (6 to 13), not taken from the typed column.

Where I disagree:
- **A2 count.** `4acdb1a8` (S.R.O. 34/1963) would not become ineligible. Its evidence references already include a second FULL first-class record, `ACQ-02/supplement_inventory.csv#ACQ02-03`. The count is 2, plus 1 that needs re-pointing.
- **A3 is the safest only together with B2.** `3b753548` (Navjot) has a `SOURCE_LOCATED` record as its only first-class evidence and page-1 text as its only identity evidence, and alone creates `EXACT_ANCHOR` for DCLR-SC-2005-L01. The pack does not state this dependency. If B2 is not adopted, A2 should apply at least to anchor-creating entries.
- **B1 risk text** cites F-T1-1, which is wrong as written (F-02).
- **C.** Deferral rests on the claim in F-03. An alias table would have real content today (details/download for 10 items).
- **Form.** Tables B and C have no "newly eligible" column; `policy_impact.c2()` normalises only scheme and host case and the default port.
- **Fidelity table.** It keeps fidelity apart from validity, authority and signature verification. I agree with it, and with holding the two born-digital rows.

## Tranche 1 spot checks (T1-02, T1-16, T1-19 and T1-20 read field by field; T1-01, T1-11 and T1-17 for identity evidence; all 20 for the listed fields)
| Check | Result |
| --- | --- |
| Tranche set equals the 20 `PRIMARY_GAZETTE_ARCHIVAL_FACSIMILE` drafts | yes |
| S.R.O. 6(E)/2022 (`2bdab5b7`) and Tribunals Reforms Act 2026 (`be619533`) excluded and non-primary | yes |
| Held bytes re-hashed | 20 of 20 match |
| source, copy, carrier, authority, publication type against Cycle 5 registers | no difference |
| Pending row fields against the C6-01 draft | no difference |
| `owner_decision` empty; no D- or R- record | yes |
| S.R.O. 34/1963 uncertainty stated; no chain inferred | yes, with the wording defect in F-12 |
| Born-digital rows: producer Ghostscript 8.15, byte range spans file, "NOT CRYPTOGRAPHICALLY VERIFIED" | yes |
| 13 "identifier read" rows | each quotation found in a WS-A or image-check record |
| `build_tranche1.py --check`, `policy_impact.py --check` | both reproduce |
| Temporary files after the runs (TMPDIR set to an empty directory) | none |
| Repository status after the runs | clean |

## Verified as correct
- **Tests.** `tests.test_legal_audit_auth_ledger`: 139 pass. Full `test_legal_audit_*.py` discovery: 502 pass, 6 skipped.
- **Version zero.** `auth_ledger.py verify` prints `v0000 ok`, HEAD `0 443c4bdf…6b6b`. The four Cycle 5 registers are byte-identical to `effective/v0000`. `ledger/`, `effective/`, `frozen_inputs.json`, `evidence/`, `schema/`, `rules_v1.py` and `pins.py` are unchanged against the base.
- **Protected paths.** No change against the base under CALIBRATION-02, SOURCE-LIBRARY-C5, C6-01-PROVENANCE, `curated_originals`, `data`, `schema`, `pipeline`.
- **No promotion.** The manifest has one line; `decisions/` holds only its README; no legal-status field was touched.
- **D-01.** The original reproduction and every encoded-traversal, double-encoding, backslash, userinfo, port, control-character, fragment and `;` variant tried was rejected (about 115 inputs).
- **No eligibility change.** All 32 drafts pass rule 1 at head and at base, with identical effective outputs per draft and jointly. All 74 committed URLs pass the strict parser.
- **Binding.** Rejected as intended: wrong second parent, octopus merge, reuse of an earlier merge, foreign commit through alternates, shallow clone (also with `.git/shallow` removed), partial clone (no fetch occurred), tampered pinned file in a nested-prefix layout. A checkout before the BIND commit shows the version as pending.
- **CLI.** It never selects `require_binding=False`. The only non-test caller that does is the tranche simulation, in a temporary directory.
- **Tranche 2.** Plan only; no proposition is marked current or binding.

## Mutation testing
541 mutants: 463 killed, 78 survived (`binding.py` 0 of 154; `urlcheck.py` 38; `ledger.py` 36; `strength.py` 4). Most survivors are redundant checks or message constants. These were confirmed by hand to leave all 139 tests passing:

| Removed control | Effect |
| --- | --- |
| scope check in `_check_record` (`ledger.py` line 184) | a decision record with any scope passes |
| `h != sha_declared` (`ledger.py` line 159) | an entry may declare a wrong record hash |
| host-label rule (`urlcheck.py` lines 78-79) | `https://a_b.nic.in/x.pdf` and `https://-a.gov.in/x.pdf` are accepted |
| `%3F` and `%23` rules (`urlcheck.py` line 33) | encoded `?` and `#` are accepted |

Also untested: genesis-line content rule (`ledger.py` 450-451), a BIND line carrying a file or review records (line 90), `--as-of` bounds (437-438), `/details/<bad item>` (`strength.py` 45).

## Not checked
- Authenticity of any held file, any signature, any page image.
- The Hugging Face snapshot, GitHub settings and reviews.
- Tranche-2 files (plan only was read).
- git versions other than 2.43.0; commit-graph tampering (recommended against in F-01 but not reproduced).

VERDICT: ACCEPT WITH CONDITIONS

Conditions: correct F-01, F-02 and F-03 before merge. Model identity as I understand it: Fable 5.2 (claude-fable-5-2).
