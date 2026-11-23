# Narrow confirmation of AUTH-LEDGER-02 at 3f486562 (re-review 64859d4d, base 63a79729)

Reviewer: Fable 5.2 (model id claude-fable-5-2), acting as database and evidence validation agent. RESEARCH ONLY. This is a technical check. It is not owner approval, legal approval or JAG approval, and it signs off for nobody.

## Result
No P1 and no P2. The three P2 conditions of the re-review (R-01, R-02, R-03) are closed. Two new P3 items (C-01, C-02) and four INFO items are recorded; none blocks. Detail, reproduction and required correction are in `fable_confirm_3f486562_findings.csv`.

| Item | Severity then | Status now | Evidence in one line |
| --- | --- | --- | --- |
| R-01 forged commit-graph | P2 | CLOSED | single file, split chain, and both forms moved to an alternate object store: plain git sees 2 parents, the tool sees 1 and rejects |
| R-02 nested `.git` | P2 | CLOSED for every `.git` placement tried | 10 placements in the real layout all rejected; see C-01 (test gap) and C-02 (symlinked package) |
| R-03 F-T1-1 over-claim | P2 | CLOSED | 13 / 7 split recomputed and equal; limitation and advice present on exactly the 7 rows; "a person read" removed; B1 corrected |
| R-04 queries on court and government classes | P3 | CLOSED | every query now rejected on every class; no committed first-class locator has one |
| R-05 `...` segments, look-alikes | P3 | CLOSED | all forms named in the required correction rejected; further look-alikes noted (C-05) |
| R-06 mutation survivors | P3 | CLOSED | the 12 earlier survivors re-run: all killed; one new survivor on the R-02 wiring (C-01) |
| R-07 scanned-page phrase | P3 | CLOSED | v04 for T1-19 and T1-20 now says the search covered the held page-1 excerpt only |
| R-08 typed anchor column | INFO | CLOSED (recorded) | decision pack states the column is typed and was recomputed by the reviewer |
| R-09 `require_binding=False` wording | INFO | CLOSED | text now names the tranche simulation; the builder uses it only in a `tempfile.mkdtemp` directory |
| R-10 empty temporary directories | INFO | OPEN (accepted, optional) | not changed, as the disposition says; pre-existing at base; not a regression |

## False-pass limitations (read first)
- **A matching sha256 proves bit integrity only.** No held source file was re-hashed in this round. No hash says anything about authenticity, currency or legal correctness.
- **The canonical Hugging Face dataset was not consulted** (no network). Coverage against it is unknown.
- **No page image was re-read.** Tranche checks compare committed register text with committed register text. "Quoted from the page image" rests on the records' own status and render hashes.
- **No signature was validated, and no GitHub fact was checked** (PR, review, branch protection).
- **git 2.43.0 only.** Other git versions, reftable and SHA-256 repositories were not tried.
- **No full AST mutation run this round.** 31 hand-written mutants on the corrected controls only. A killed mutant is not proof of a correct control.
- **Forgery vectors assume a tampered working copy** handed to an offline verifier. `APPROVAL_CONTROLS.md` now states that trust assumption. A plain local `--no-ff` merge still verifies topologically; that was already disclosed.
- **A forged commit object stored under a genuine id is rejected only as a side effect** (C-04), not by an explicit check.

## How the work was done
- The worktree was not modified (`git status` empty, HEAD 3f486562 before and after). Head and base were exported with `git archive` into `scratchpad/c4/3f486562` and `scratchpad/c4/63a79729`; every experiment ran in further copies under `scratchpad/c4/`.
- New scripts are in `scratchpad/c4/scripts/`: `e2e.py` (real-layout binding vectors), `alt.py` and `alt2.py` (alternates), `reg.py` (URLs, drafts, rule 1 at head and base), `tr4.py` and `dl.py` (tranche recomputation), `hm.py` (mutants). `scratchpad/rr3/scripts/bind4.py` was re-run unchanged.

## Task 1: binding vectors

### R-01 commit-graph (CLOSED)
All runs use the real package layout in a throwaway repository: version 1 by direct commit, an empty commit, a BIND line naming the two.

| Case | Plain git | Tool |
| --- | --- | --- |
| no forgery | 1 parent | rejected ("merge_commit has 1 parent(s)") |
| forged `objects/info/commit-graph` | 2 parents | rejected, same reason |
| forged split chain | 2 parents | rejected |
| forged graph moved to an alternate store (`objects/info/alternates`) | 2 parents | rejected |
| forged split chain in an alternate store | 2 parents | rejected |
| forged graph plus hostile `HOME`, XDG, global and system config setting `core.commitGraph=true` | 2 parents | rejected |
| forged graph plus `core.commitGraph=true` in the repository's own config | 2 parents | rejected |

`git status` was empty in every case. Mutants that drop the option or set it to `true` are killed.

### R-02 nested `.git` (CLOSED for `.git` placements)
Outer repository: everything in one direct commit; the BIND line names commits of an attacker repository holding a proper merge. Control: rejected ("commit ... is not in the local history"). Honest control in the real layout: `APPLIED`, `bound_by 2`.

| Planted | Result |
| --- | --- |
| `.git` directory at the ledger root | rejected ("is not the expected repository") |
| `.git` file (`gitdir:`) at the ledger root | rejected, same |
| `.git` directory or file at `legal_knowledge/audit_work` | rejected, same |
| `.git` directory or file at `legal_knowledge` | rejected, same |
| `.git` directory at the ledger root or at `audit_work` with `core.worktree` set to the real top | top check passes; later calls run at the real top; rejected ("not in the local history") |
| ledger root dressed as a git directory (`HEAD`, `objects`, `refs`, `config`) | rejected ("no git history at the ledger root") |
| the same with `core.bare=false` and `core.worktree` set to the real top | rejected ("not in the local history") |

Outer `git status` stayed empty and outer HEAD unchanged for the `.git` placements.

Two points remain, both P3:
- **C-01.** The wiring is not tested by behaviour. Removing `expected_top=pinned_top` from the call in `apply_ledger` passes all 160 tests, and the nested `.git` then verifies again (`APPLIED`, `bound_by 2`, both forms). `test_r02_repository_top_is_pinned` checks `binding.verify` directly and then matches source text.
- **C-02.** A symlinked package diverts verification. With `legal_knowledge/audit_work/AUTH-LEDGER` committed as a symlink into a second full repository that holds a proper merge, `reader.effective_state()` run through the symlinked path returns `APPLIED`, `bound_by 2`. The audited repository has two commits, no merge, and an empty `git status`. Every path is resolved, so the pin follows the symlink. Limits of the vector: the symlink must be committed (it shows as mode 120000 in the tree and in any PR diff) or `git status` is dirty; the target must exist on the verifier's machine; a fresh clone leaves it dangling. It sits inside the stated trust assumption, but that text does not name symlinks.

### Alternates carrying forged objects
| Case | Plain git | Tool |
| --- | --- | --- |
| forged loose commit under the merge id in an alternate, genuine object removed | 2 parents | rejected ("not in the history of the checked-out HEAD") |
| the same, genuine object kept in the main store | 1 parent | rejected (1 parent) |
| mislabelled packed commit in an alternate | 2 parents | rejected ("not in the history ..."); `git fsck` reports it |
| honest merge with every loose object moved to an alternate | n/a | `APPLIED` (legitimate use still works) |

**C-04 (INFO).** In the forged-object cases `rev-list --parents` accepts the forged object and the two-parent check passes. Rejection comes from `merge-base --is-ancestor`, which hash-checks its argument ("error: hash mismatch"; return code 128). That is a property of git 2.43.0, not a stated control.

### `bind4.py` re-run
N1, N1p, N2, N2c and all ten environment vectors are rejected. N3 still returns `APPLIED` because it uses a synthetic ledger root, which is not pinned by design (C-03, INFO): `expected_top` defaults to `None`, and only the committed package root is pinned. The command-line tool always uses the package root.

## Task 2: regressions
| Check | Result |
| --- | --- |
| `tools/auth_ledger.py verify` | `v0000 ok`; `HEAD 0 443c4bdf348b2a1bcd603d2701f097aa90a8155efd43c10760f5fd86c76c6b6b`; rc 0 |
| Four Cycle 5 outputs | `effective/v0000` and a fresh `build --as-of 0` are both byte-identical to the frozen registers (`cmp`) |
| Protected paths against 63a79729 (CALIBRATION-02, SOURCE-LIBRARY-C5, `curated_originals`, C6-01-PROVENANCE, C6-PREP, `config`, `crawler`, `.github`, and also `data`, `schema`, `pipeline`) | no file changed |
| `ledger/`, `effective/`, `evidence/`, `schema/`, `frozen_inputs.json`, `corrections/` against base | no file changed |
| Committed ledger | one manifest line (version 0); `decisions/` and `corrections/` hold only a README; no D- or R- record |
| APPROVED rows | none; the word occurs only in the schema enum and an earlier review CSV; `owner_decision` is empty and status is `PENDING_NOT_IN_LEDGER` in all 20 pending rows |
| Committed URLs | 75 pairs, 74 URLs, all pass `urlcheck.problem` |
| Draft first-class locators | all 32 pass `strength.first_class` with their class |
| Rule-1 outcome of the 32 drafts | 32 pass at head and at base; effective outputs and transitions identical per draft and jointly |
| `build_tranche1.py --check`, `policy_impact.py --check` | both reproduce, rc 0; repository status clean afterwards |
| `tests.test_legal_audit_auth_ledger` | 160 pass |
| `test_legal_audit_*.py` discovery | 523 pass, 6 skipped |
| Review copies | `fable_rereview_64859d4d.md` and its CSV are byte-identical to my originals |

Outside the named protected list, two files differ from base: `AUTH-LEDGER/decisions/README.md` and `C7-PREP/WORKSTREAMS_READINESS.md`. Both changed in earlier commits of this package; neither is in the correction diff 64859d4d..3f486562 (C-06, INFO).

### Mutants on the corrected controls (31; 28 killed, 3 survived)
- Killed: both commit-graph mutants; the `expected_top` check removed or inverted; `pinned_top` always `None` or wrong ancestor; all 12 survivors of the last round (M02, M03, M04, M11, M15, M18, M25, M26, M27, M34, M35, M36); the query rule; each look-alike; the dots-and-spaces rule (two forms); `identifier_source`, the L5 limitation, the advice and the v04 phrase.
- Survived: `expected_top` not passed (C-01, a real gap); the separator rule dropped and the archive query branch dropped (both equivalent: an earlier or later rule still rejects the same inputs).

## Task 3: tranche texts against the registers
- **Split.** Recomputed from the cited records, using the observation and transcription fields only: 13 `IMAGE_CHECK_OR_TRANSCRIPTION`, 7 `L5_DISCOVERY_REGISTER_ONLY` (T1-02, 11, 14, 16, 17, 18, 19). Equal to `identifier_source` on all 20 rows. Sub-tranches are 18 / 2.
- **Pending rows.** The limitation "quoted only in the R23 amendment-search register ... produced by a read-only discovery agent ... not approved ... not an identity-reference kind under rule 1" is on exactly those 7 rows. "ADVISABLE FIRST" is in the recommendation of exactly those 7.
- **Date line.** The instrument date is in the quoted text for all 20 (in image-check or transcription text for the 13, in the L5 quotation for the 7).
- **Matrix v04.** 5 rows (T1-04, 05, 07, 15, 20) show `NOT FOUND` for the L5 quotation and are sourced from WS-A transcriptions, as B1 now implies. T1-19 and T1-20 carry the page-1 excerpt wording; both identities give printed p.2.
- **`TRANCHE1_FINDINGS.md` F-T1-1.** Matches the registers. It names the agent origin of the L5 register, states that the 13 are not established as human-made, and that no record is human-confirmed. The summary lists the six 1A rows for which a CONFIRMED check is advisable; the seventh (T1-19) is held in 1B and carries the same advice.
- **`RULE_DECISION_PACK.md` B1.** "13 in image checks or WS-A transcriptions; 7 only in the L5 R23 register, agent-produced and not approved" is accurate. "Risk is low for 13" is a judgement, stated as such.
- **Remaining over-claim.** None found in these four texts. One caution, not a finding: "quoted from the page image" is the records' own claim and was not re-checked against any image in this or the previous round.

## New findings (one line each; detail in the CSV)
- **C-01 (P3)** The R-02 wiring in `apply_ledger` is untested by behaviour; dropping `expected_top=pinned_top` passes all tests and re-opens the nested `.git` vector.
- **C-02 (P3)** A committed symlink in place of the package diverts verification to another repository.
- **C-03 (INFO)** `binding.verify` defaults to `expected_top=None`; non-package roots are unpinned by design.
- **C-04 (INFO)** Forged commit objects are rejected only through git's hash check in `merge-base`.
- **C-05 (INFO)** Still accepted, and not in the R-05 required correction: a leading combining mark (`/%CC%81a.pdf`), and U+2216, U+29F5, U+29F9, U+2571, U+27CB, U+3033. Every committed and draft locator decodes to printable ASCII, so an ASCII-only rule would reject none of them. Also still accepted: any sub-domain of `sci.gov.in`, and `-.pdf` under `/supremecourt/<year>/<n>/`.
- **C-06 (INFO)** Two files outside the named protected list differ from base (earlier commits of this package).

## Not checked
- Authenticity of any held file, any signature, any page image.
- The Hugging Face snapshot, GitHub settings and reviews.
- Whether the 13 image-check and transcription records were made by a person or an agent.
- Tranche-2 plan (unchanged in this commit).
- A full AST mutation run; git versions other than 2.43.0; a `git` wrapper earlier on `PATH`; reftable; SHA-256 repositories; submodules.
- A hostile system config file at `/etc/gitconfig` itself (tested through `GIT_CONFIG_SYSTEM`, which the tool drops).

VERDICT: ACCEPT

Model identity as I understand it: Fable 5.2 (claude-fable-5-2).
