# Independent re-review of AUTH-LEDGER-02 at 64859d4d (previous review 924047b1, base 63a79729)

Reviewer: Fable 5.2 (model id claude-fable-5-2), acting as database and evidence validation agent. RESEARCH ONLY. This is a technical check. It is not owner approval, legal approval or JAG approval, and it signs off for nobody.

## Result
No P1. Two prior P2 findings are only partly closed, and three P2 items remain (R-01, R-02, R-03). Full detail, reproduction and required correction are in `fable_rereview_64859d4d_findings.csv`.

| Prior finding | Severity then | Status now | Remaining item |
| --- | --- | --- | --- |
| F-01 BIND forgery | P2 | PARTIALLY CLOSED | R-01 (P2) forged commit-graph; R-02 (P2) nested `.git` at the ledger root |
| F-02 tranche finding F-T1-1 | P2 | PARTIALLY CLOSED | R-03 (P2) corrected text over-claims who read the image, and the limitation is not in the rows |
| F-03 "every second spelling" | P2 | CLOSED | none |
| F-04 change after review | P3 | CLOSED | nested-prefix branch untested (R-06) |
| F-05 assurance not in transitions | P3 | CLOSED | none |
| F-06 class path rules | P3 | CLOSED | R-04 (P3) queries still free on court and government classes |
| F-07 decoded characters | P3 | PARTIALLY CLOSED | R-05 (P3) `...` segments and a few others still accepted |
| F-08 URL truncation | P3 | CLOSED | call sites untested (R-06) |
| F-09 AI-name list | P3 | CLOSED as a lint | documented as not an identity control |
| F-10 manifest types and date | P3 | CLOSED | none |
| F-11 mutation survivors | P3 | PARTIALLY CLOSED | R-06 (P3) new survivors |
| F-12 pending-row wording | P3 | PARTIALLY CLOSED | R-07 (P3) scanned-page phrase still on the two text-layer files |
| F-13 decision pack | P3 | CLOSED | R-08 (INFO) |
| F-14 staged withdrawals, snapshots | INFO | CLOSED (recorded, O-5 raised) | none |
| F-15 `1.0x7f`, `GIT_NO_LAZY_FETCH` | INFO | CLOSED | urlcheck-alone test missing (R-06) |

## False-pass limitations (read first)
- **A matching sha256 proves bit integrity only.** No held file was re-hashed in this round, and no hash says anything about authenticity, currency or legal correctness.
- **The canonical Hugging Face dataset was not consulted** (no network). Coverage against it is unknown.
- **No page image was re-read.** Tranche checks compare committed register text with committed register text.
- **No signature was validated.** No GitHub fact (PR, review, branch protection) was checked.
- **Tests ran on git 2.43.0 only.**
- **Mutation testing** used the same simple operator set as before (680 AST mutants) plus 37 hand-written mutants. A killed mutant is not proof of a correct control.
- **The forgery vectors assume a tampered `.git` directory** handed to an offline verifier (copied directory, tar, mirror). They do not travel with an ordinary clone. The tool does not compare HEAD with any trusted value, so a plain local `--no-ff` merge still verifies topologically; that is disclosed in `APPROVAL_CONTROLS.md` (F-05).

## How the work was done
- The worktree was not modified. Head 64859d4d and base 63a79729 were exported with `git archive` into `scratchpad/rr3/head` and `scratchpad/rr3/base` and made throwaway repositories; further copies `head2`, `head3` and `mut/w0..w3` were used for tests and mutants.
- New scripts are in `scratchpad/rr3/scripts/` (`bind3.py`, `bind4.py`, `url3.py`, `tr3.py`, `misc.py`, `repoint.py`, `mut5.py`). Prior scripts in `scratchpad/fr_scripts/` were re-run unchanged. Mutation results are in `scratchpad/rr3/mut/results.json`.

## P2 findings

### R-01 A forged commit-graph file still makes a direct push verify as a merge (`tools/binding.py`, `_git`)
The previous review listed `-c core.commitGraph=false` as part of the required correction. It was not added. git reads parents from `objects/info/commit-graph` without checking them against the commit object.

| Case | Set-up | Result |
| --- | --- | --- |
| N2 | version added by direct commit `c1`; empty commit `c2`; BIND names `c1`, `c2`; commit-graph written, then the two parent slots of `c2` in the CDAT chunk rewritten to (base, `c1`) and the trailer re-hashed | `APPLIED`, `bound_by 2` |
| N2c | same, with a split chain under `objects/info/commit-graphs/` | `APPLIED`, `bound_by 2` |

In both cases `git status` is clean, HEAD is unchanged, and there is no `refs/replace` and no `info/grafts`. With `-c core.commitGraph=false` added to `_git` in a scratch copy, both are rejected ("merge_commit has 1 parent(s)") and all 153 module tests still pass.

Required: add `-c core.commitGraph=false` to every git call; one test per form (single file, split chain); state the residual in `APPROVAL_CONTROLS.md`.

### R-02 A nested `.git` in the ledger root diverts verification to another history (`tools/binding.py`, `verify`)
`verify` takes the repository from `git -C <root> rev-parse --show-toplevel`, which is the nearest `.git`. A `.git` directory, or a one-line `.git` file (`gitdir: <path>`), placed in the ledger root makes every check run against an attacker-built history. This is the on-disk form of the `GIT_DIR` case (A8) that the environment fix closed.

| Step | Result |
| --- | --- |
| outer repository: the version and BIND line added by one direct commit, no merge | rejected ("commit ... is not in the local history") |
| plus a nested `.git` directory in the ledger root holding a proper merge | `APPLIED`, `bound_by 2`; outer `git status` empty; outer HEAD unchanged |
| plus a nested `.git` file with `gitdir:` instead | `APPLIED`, `bound_by 2`; outer `git status` empty |

Required: for the committed ledger, require the repository top to be the expected ancestor (prefix exactly `legal_knowledge/audit_work/AUTH-LEDGER`), or fail closed when any `.git` entry exists at the ledger root or between it and the expected top; add a test; state the residual.

### R-03 The corrected finding F-T1-1 says "a person read" the identifiers; for 7 rows the reading is an agent's discovery-stage quotation, and the rows do not carry that limitation
What is right: the builder now reads the cited L5 records, all 20 identifiers are found, and the 18 / 2 split follows from the data. I recomputed it independently: 13 rows have the S.R.O. number in an image-check or transcription reference, and 7 (T1-02, T1-11, T1-14, T1-16, T1-17, T1-18, T1-19) have it only in the L5 record. Each L5 record carries this copy's sha256, status `LOCATED_IMAGE_CHECKED` and a 64-hex render hash, and the year in the quotation matches the identity.

What is wrong:
- `TRANCHE1_FINDINGS.md` F-T1-1 says the numbers "appear in text that a person read from the page image". `R23-VERIFY-01/registers/AMENDMENT_SEARCH_README.md` says the register "was produced by a read-only discovery agent", is a "review proposal, not approved", records one orchestrator spot check (S.R.O. 332), and notes that some later pages were read from the text layer only.
- The limitation that these quotations are "not an identity-reference kind under rule 1" is in matrix column v07 only. It is not in the `limitations` column of the 7 pending rows, not in `tranche1_source_register.csv` (`identifier_read_on_image` is a flat `YES`), and not in F-T1-1. The dispositions say the identifier limitation is in the `limitations` column; the code adds it only when the identifier is not found, which is now never.
- The 7 rows moved from "confirm before the owner decision" to "READY ... with the stated limitations" on this evidence.
- Decision pack B1 says "For the 20 Gazettes, the S.R.O. number and date line are in fact quoted from the page image in the cited L5 R23 records". Five rows (T1-04, T1-05, T1-07, T1-15, T1-20) cite no L5 record that quotes the number; theirs comes from WS-A transcriptions.

No eligibility outcome depends on this (rule 1 passes all 20 on other references), and nothing is approved. It is an over-claim of verification in an owner-facing document.

Required: replace "a person" with the actual source (agent-made image-check observation, transcription, or discovery-stage quotation; not human-confirmed unless a record says so); add the limitation to the `limitations` column of the 7 rows and a distinct value in `identifier_read_on_image` (for example `YES_L5_DISCOVERY_QUOTE_ONLY`); correct B1 to "15 of 20 in L5 records, 5 in WS-A transcriptions"; state in F-T1-1 that the owner may ask for a CONFIRMED image check for the 7.

## P3 and INFO findings (one line each; detail in the CSV)
- **R-04 (P3)** Court and government classes accept any query: `https://main.sci.gov.in/jonew/judis/1234.pdf?redirect=//evil` and `https://egazette.nic.in/redirect?to=//evil.com` pass. `COURT_PATH` also accepts any sub-domain of `sci.gov.in` and file name `-.pdf`. The host list for the government class is correctly left to the owner.
- **R-05 (P3)** Still accepted: `...` and `....` segments (named in F-07), a segment of one encoded space (`/%20/a`), U+2215, U+2044 and U+29F8 (slash look-alikes that NFKC does not change), U+FFFD, a leading combining mark. D-12 says "no control, format or compatibility characters", which is accurate; these are outside that wording.
- **R-06 (P3)** Mutation survivors on corrected controls (below).
- **R-07 (P3)** `evidence_verification_matrix.csv` v04 for T1-19 and T1-20 still says "(text-layer absence is not adverse for a scanned page)"; v10 for both is `TEXT_LAYER_NO_IMAGES_ALL_PAGES`. The disposition says the page-1 limit "is recorded"; I did not find that wording in the tranche files.
- **R-08 (INFO)** `policy_impact.py` still takes `creates_exact_anchor_alone` from the typed draft column. My reader recomputation agrees for all 32 (7 creators, joint 48 to 55). The disposition's "reproduced by the reader in `simulated_joint_impact.json`" covers only the 20 Gazettes, which create none.
- **R-09 (INFO)** `APPROVAL_CONTROLS.md` says `require_binding=False` is "for the synthetic evidence-rule tests only"; `build_tranche1.py` also uses it for the simulation in a temporary directory.
- **R-10 (INFO)** The AUTH-LEDGER test module leaves 2 empty temporary directories. The base does the same, so this is not a regression. Both `--check` tools and `verify` leave none.

## Task 1: evidence for each closed finding
- **F-01 vectors re-run.** Replace graft, `info/grafts`, altered merge behind a replace ref: all rejected (fail closed). `GIT_DIR` with `GIT_WORK_TREE`: ignored. Also ignored: `GIT_REPLACE_REF_BASE` (with a real hidden replace ref under `refs/hidden/`), `GIT_CONFIG_COUNT/KEY/VALUE`, `GIT_CONFIG_PARAMETERS`, `GIT_ALTERNATE_OBJECT_DIRECTORIES`, `GIT_COMMON_DIR`, `GIT_CEILING_DIRECTORIES`, `GIT_SHALLOW_FILE`, `GIT_NAMESPACE`, `GIT_INDEX_FILE`, `GIT_EXEC_PATH`.
- **New vectors rejected.** Repository config `core.useReplaceRefs=true` with a replace graft; `includeIf` in repository config; `core.worktree=/tmp` (fails closed); grafts in a linked worktree's own gitdir (no effect) and in the common directory (fail closed); a forged loose commit object; a forged loose object shadowing a packed genuine one; a mislabelled packed commit (pack index renamed to the merge id) is rejected at the ancestry step, and `git fsck` reports it. Alternates, shallow and partial clone: as before.
- **Not tried.** Submodule checkout (it reduces to R-02), reftable, a `git` wrapper earlier on `PATH`, SHA-256 repositories.
- **F-03.** Archive.org queries and trailing-slash paths are rejected. The docstring, D-12 and pack section C now list what is not canonicalised. Recommendation C no longer rests on the old claim. The 10 archive items under both forms reproduce; none has differing sha256 values.
- **F-06.** Bare `gov.in` and `nic.in`, site roots, directory paths, look-alike hosts (`evilgov.in`, `gov.in.evil.com`, `xsci.gov.in`), `web.archive.org`, `www.archive.org` and cross-class hosts are rejected. All 17 committed `sci.gov.in` locators match `COURT_PATH`.
- **F-07.** Fullwidth dot and solidus, bidi override, C1 controls, zero-width and soft-hyphen characters, NBSP, line separator, surrogates, out-of-range and overlong UTF-8 are rejected in path and query, each with a stated reason. `..%20`, `.%20` and `%20..` are rejected.
- **F-08.** 13 free-text forms tried; every form that would truncate is refused.
- **F-09, F-10.** `Fable5`, `claude_code`, `GPT4`, `ai-assistant`, `Gemini2` rejected. Dates `9999-99-99`, `20261123`, `2026-02-30`, non-ASCII digits, a trailing newline, int and null are rejected; `version` and `rule_version` as bool, float or string are rejected.
- **F-05.** `transitions.json` carries `binding_assurance` with "GitHub review ASSERTED_NOT_VERIFIED_OFFLINE".
- **F-13.** A2 count is 2. The re-pointing of 4acdb1a8 to `ACQ02-03` was run through rule 1 end to end in a synthetic ledger and passes. The A3 and B2 dependency is stated; P-A reads "only together with B2".
- **Committed data.** 75 pairs, 74 URLs, all pass the strict parser. All 32 draft first-class locators pass parser and class rule. Each of the 32 drafts passes rule 1 at head and at base with identical effective outputs, singly and jointly; no rule-1 outcome changed.

## Task 2: regressions
| Check | Result |
| --- | --- |
| `tools/auth_ledger.py verify` | `v0000 ok`; HEAD `0 443c4bdf348b2a1bcd603d2701f097aa90a8155efd43c10760f5fd86c76c6b6b` |
| Four Cycle 5 outputs against `effective/v0000` | byte-identical (`cmp`) |
| Protected paths against 63a79729 (CALIBRATION-02, SOURCE-LIBRARY-C5, `curated_originals`, C6-01-PROVENANCE, C6-PREP, `config`, `crawler`, `.github`, `data`, `schema`, `pipeline`) | no file changed |
| `ledger/`, `effective/`, `evidence/`, `schema/`, `frozen_inputs.json` against base | no file changed |
| Manifest | one line; no D- or R- record (`decisions/` and `corrections/` hold only a README) |
| APPROVED rows | none; the word occurs only in the schema enum and an earlier review CSV; `owner_decision` is empty in all 20 pending rows |
| `build_tranche1.py --check`, `policy_impact.py --check` | both reproduce; no temporary file left; repository status clean |
| Review copy | `fable_review_924047b1.md` and its CSV are byte-identical to my originals |

## Task 3: tests and mutation
- `tests.test_legal_audit_auth_ledger`: 153 pass. Full `test_legal_audit_*.py` discovery: 516 pass, 6 skipped.
- **AST mutants: 680; 593 killed, 87 survived; no timeout.** `binding.py` 173 of 173 killed; `ledger.py` 32 survived; `urlcheck.py` 33; `strength.py` 22. Ten survivors are on lines changed by the correction commit; most are redundant operands or messages.
- **Hand-written mutants on the corrected controls: 37; 26 killed, 11 survived.**

| Survivor | Meaning |
| --- | --- |
| M02 drop `GIT_GRAFT_FILE=/dev/null` | env hardening not tested by behaviour (the fail-closed check catches the file first) |
| M03 drop `-c core.useReplaceRefs=false` | same |
| M04 drop `GIT_CONFIG_NOSYSTEM` and `GIT_CONFIG_GLOBAL` | no test with a hostile global config |
| M11 package prefix ignored in the F-04 tree comparison | nested-prefix layout untested (it works: my nested case is rejected correctly) |
| M15 drop the Zs rule | largely redundant with NFKC |
| M18 top-level label rule back to `isdigit` | `1.0x7f` is tested only through the class rule, not `urlcheck` alone |
| M25 `COURT_PATH.search` instead of `fullmatch` | no test with a prefix or suffix around a valid court path |
| M26, M27 `_untruncated` not called (RET, DL) | the function is tested directly; its two call sites are not |
| M34, M35, M36 L5 status, sha256 and render-hash conditions | the builder's L5 filter is untested |

## Task 4: remaining over-claims
- **`TRANCHE1_FINDINGS.md`**: "a person read" (R-03). Otherwise it states preparation only, no legal status, copy provenance only for S.R.O. 34, and "STRUCTURAL ONLY" for signatures. Neutral S.R.O. 34 wording is in place; the frozen C5 and C6-01 files are unchanged.
- **`RULE_DECISION_PACK.md`**: B1 "in the cited L5 R23 records" for all 20, and "so the risk there is low" (R-03). Nothing is described as adopted. The fidelity table keeps fidelity apart from validity, authority and signature verification.
- **`APPROVAL_CONTROLS.md`**: item 5 is accurate as far as it goes, but the residual column for direct push and history rewrite does not mention local `.git` tampering (R-01, R-02). GitHub review is described as asserted throughout. No claim of legal effect.
- **`DESIGN_NOTES.md` D-12 to D-14**: D-12 is now accurate. D-13 says the BIND line is verified "offline against git history"; subject to R-01 and R-02. D-14 has no over-claim.

## Not checked
- Authenticity of any held file, any signature, any page image.
- The Hugging Face snapshot, GitHub settings and reviews.
- Whether the image-check and WS-A transcription records (13 rows) were made by a person or an agent; only the R23 amendment-search register's own statement was read.
- Tranche-2 plan (unchanged in this commit).
- git versions other than 2.43.0.

VERDICT: ACCEPT WITH CONDITIONS

Conditions: correct R-01, R-02 and R-03 before merge. Model identity as I understand it: Fable 5.2 (claude-fable-5-2).
