# Focused re-review: Cycle 8 security corrections (06a54c66) and CI pin (30f6015f)

- **Security branch:** `claude/c8-security-closeout` at `06a54c66` (corrections to `be861ec0`; base `1a21a2e8`).
- **CI branch:** `claude/c8-ci-full-history` at `30f6015f` (prior `eed9e0bc`).
- **Reviewer:** Fable 5.2 (`claude-fable-5-2`), independent of the implementation. RESEARCH ONLY. This is a technical re-review of the corrections, not a fresh full review and not a sign-off for the legal adviser, JAG or the project owner.
- **Findings:** `fable_rereview_c8_security_06a54c66_findings.csv` (11 rows: 6 P3, 5 INFO; R-01 to R-08, CI-R1 to CI-R3).

## Result
The two P2 findings of the earlier review are closed for the vectors that were reported. No P1 or P2 finding is open. Five P3 findings remain on the security branch: a stated residual that is wider than the documents say (R-01), an unhashed read path that the documents say is hashed (R-02), three working controls with no test (R-03), three behaviours on legitimate layouts that are undocumented or uncaught (R-04), and stale document text (R-05). One P3 stays open on the CI branch (CI-02, listed as CI-R3). Version zero, the ledger, draft eligibility and the protected paths are unchanged. The CI pin step is correct and resolves CI-01.

| Prior finding | Status | Evidence |
| --- | --- | --- |
| F-01 (P2) symlinked package accepted at the CLI | **PARTIALLY CLOSED** | Every path-named CLI run and all seven import orders are rejected for three victims. A relative run from inside the link target still returns `APPLIED` (stated residual; wider than stated, R-01) |
| F-02 (P2) forged tree accepted | **CLOSED** for trees and blobs on the read paths | Loose, alternate, packed and local-path clone all rejected. Forged blobs and each subtree level rejected. One commit path is still unhashed (R-02) |
| F-03 (P3) mutation survivors | **PARTIALLY CLOSED** | 16 of 33 mutants killed; three surviving groups are not redundant (R-03) |
| F-04 (P3) committed-layout half fails open | **PARTIALLY CLOSED** | Unborn HEAD, absent package, gitlink, top mismatch all rejected. A failing `git rev-parse` still skips the half silently (R-04) |
| F-05 (P3) manual instruction removed | **CLOSED** | Restored in `APPROVAL_CONTROLS.md` |
| F-06 (P3) O-5 procedure gaps | **CLOSED** | All four points addressed; analysis only, no code |
| F-07 (INFO) bundle untested | **CLOSED** | `test_f07_bundle_clone_verifies`; reproduced with the real CLI |
| F-08 (INFO) requirement 5 | Still holds | Section 5 |
| F-09 (INFO) synthetic roots unpinned | Unchanged by design | Not re-tested |
| CI-01 (P2) coupling to the `raw-data` tip | **CLOSED** | Section 6 |
| CI-02 (P3) full fetch inside 10 minutes | **OPEN** | Cannot be measured offline |
| CI-03 (INFO) minimal change | Still holds | 18 added lines, one file |

## False-pass limitations (read first)
- No network was used. GitHub settings, reviews, branch protection, runner timing and the remote tip of `raw-data` were not checked.
- The canonical Hugging Face snapshot was not read. Nothing here concerns the authenticity, currency or legal correctness of any source.
- The local repository is shallow and has no BIND line. Every binding result comes from synthetic repositories built with the test suite's own fixtures.
- The interpreter was the venv's Python 3.13, not the 3.11 that CI uses. git was 2.43.0 only.
- "Eligibility unchanged" means the same transition effect and the same copy-register hash at base and head for each of the 32 C6-01 drafts, with `require_binding=False`. It says nothing about whether any draft should be approved.
- The mutation set is mine (33 mutants over this round's controls) and is not exhaustive.
- The ancestry forgery (R-02) was shown with a loose object only. Packed and alternate stores were not tried for it.
- Hash collisions, SHA-256 repositories, bind mounts and hard links were out of scope.
- This is a focused re-review. Code that the correction did not touch was not re-read.

## 1. How the work was done
- Neither worktree was modified: both are clean, at `06a54c66` and `30f6015f`.
- Working copies are in `/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/revA3_tmp`: `repo` and `mrepo` (files of `06a54c66`, own `.git`, main object store as an alternate), `base` (`git archive 1a21a2e8`), `export` (`git archive 06a54c66`, no `.git`), `ci` (files of `30f6015f`), `attacker`, `victim1` to `victim3`.
- Scripts are in `/tmp/claude-0/-home-user-mimamsa-corpus/9dd71a54-b050-5d1e-a2e9-2ceef8ac3e20/scratchpad/revA3_tmp/scripts`. The earlier `mk_attacker.py`, `imp.py`, `forge_tree.py`, `vectors.py` and `elig.py` were re-run unchanged. New: `forge_more.py`, `forge_anc.py`, `forge_base.py`, `mut3.py`.
- Environment: `PYTHONDONTWRITEBYTECODE=1`, `TMPDIR` inside the scratchpad.

## 2. F-01: symlinked package
`victim1` commits the package as mode 120000, `victim2` commits `legal_knowledge`, `victim3` commits `legal_knowledge/audit_work`; each points at `attacker`, which holds one honest merge and a BIND line (`build` there gives `APPLIED`).

| Entry point (each for all three victims) | Result |
| --- | --- |
| `auth_ledger.py build` and `verify`, absolute path | rejected, "is a symlink", rc 2 |
| the same by relative path from above the victim, and from the victim top (`python legal_knowledge/...`, `./legal_knowledge/...`) | rejected, rc 2 |
| cwd inside the link, script named by its absolute logical path or by `$PWD/auth_ledger.py` | rejected, rc 2 |
| `python -I` and `python -P` | rejected, rc 2 |
| library: link path on `sys.path`, first import `ledger`, `reader`, `auth_ledger`, `common`, `binding`, `pins` or `strength` | rejected in all seven orders |
| cwd inside the link, `python auth_ledger.py build --out X` | **rc 0, `APPLIED`** (stated residual) |
| cwd inside the link, `python -m auth_ledger verify` | not rejected by the layout check; it reads the attacker ledger |
| `victim2`, cwd `victim2/legal_knowledge`, `python audit_work/AUTH-LEDGER/tools/auth_ledger.py verify` | not rejected by the layout check; it reads the attacker ledger |

The last two `verify` runs end with rc 2 for a different reason: the attacker fixture has no rebuilt `effective/` output. That is not the control working.

**R-01 (P3).** The residual is real and stated, but three points remain:
- The guidance says to run the tool "from outside the package". For `victim2` and `victim3` the working directory `legal_knowledge` is outside the package and still inside the link. The safe rule is: run from the repository top or above, or name the script by an absolute path.
- The module docstring of `auth_ledger.py` shows the usage as `python auth_ledger.py verify`, which is the unsafe form.
- A shell that entered the directory through the link keeps the logical path in `$PWD` (confirmed: `$PWD` shows `victim1/...`, `os.getcwd()` shows `attacker/...`). Using `$PWD` when it resolves to the same directory as `os.getcwd()` would close the common interactive case.

## 3. F-02: forged objects
| Attack | be861ec0 | 06a54c66 |
| --- | --- | --- |
| Root tree of the reviewed head and merge forged (`forge_tree.py`), loose | `APPLIED` | rejected, "tree object ... does not hash to its id" |
| the same, alternate store | `APPLIED` | rejected |
| the same, hand-built pack | `APPLIED` | rejected |
| local-path clone of each forged store | `APPLIED` | rejected |
| `--no-local` clone and bundle clone of each forged store | fail, rc 128 | fail, rc 128 |
| Four blobs forged under genuine ids, trees and commits genuine (`forge_more.py blob`) | **`APPLIED`** | rejected, "blob object ... does not hash to its id" |
| Each object on the read path forged in turn: root, three intermediate trees, `ledger/`, `decisions/`, the manifest blob, the entry blob, a review blob (`forge_more.py subtree`) | not run | all nine rejected by the hash check |
| Root tree of the merge base forged, so that a directly pushed version looks as if it entered through the merge (`forge_base.py`) | `APPLIED` | rejected |
| HEAD commit object forged under the published id (`forge_more.py head`) | not run | rejected (git itself reports a hash mismatch) |
| Interior ancestor commit forged, between HEAD and the merge (`forge_anc.py`) | `APPLIED` | **`APPLIED`** (R-02) |

The blob row corrects the earlier review, which assumed that blob forgery "should gain nothing". At `be861ec0` it made an unreviewed replacement entry effective under an honest merge. The correction closes it.

**R-02 (P3).** `binding.verify` checks that the merge is an ancestor of HEAD with `git merge-base --is-ancestor`. The commits walked between HEAD and the merge are not re-hashed. With a genuine published tip X, an attacker-made head and merge that exist only locally, and the parent line of one interior ancestor of X rewritten under its genuine id, the result is `APPLIED` while `git rev-parse HEAD` still prints X. Without the forgery the same working tree is rejected ("merge_commit is not in the history of the checked-out HEAD").
- Limits: `git fsck` returns rc 3, and a `--no-local` clone fails with rc 128. The merge named by the BIND line is not a real pull request, so an online check of the asserted review would fail. The gain is only that a comparison of the HEAD id with a known-good tip no longer exposes the tampering.
- The documents say otherwise. `APPROVAL_CONTROLS.md`: "forged commit, tree or blob objects on every path the verdict reads ... all re-hashed". `C8_SECURITY_CLOSEOUT.md`: "Objects that the verdict never reads are not hashed". The ancestry commits are read by the verdict and are not hashed.
- Correction: re-hash each commit on `git rev-list --ancestry-path <merge>..HEAD`, or narrow both sentences and name the ancestry walk as a residual.

## 4. Legitimate layouts
All with the real CLI (`verify`) unless stated.

| Layout | Result |
| --- | --- |
| The real repository (linked worktree, `.git` file), read-only worktree | `v0000 ok`, rc 0 |
| Own-`.git` copy with alternates | `v0000 ok` |
| Linked worktree of a `--no-local` clone | `v0000 ok` |
| Repository top reached through a symlink | `v0000 ok` |
| `--no-local` clone under a symlinked parent; also with cwd at the top and cwd in `tools/` | `v0000 ok` in all three |
| Bundle clone (`git bundle create --all`) | `v0000 ok` |
| Depth-1 clone (no BIND line present) | `v0000 ok` |
| Export without `.git`, not under any git work tree | `v0000 ok` |
| `build --out` in the copy | rc 0; four outputs byte-identical to the Cycle 5 registers |
| `vectors.py` V01 to V04 (honest bound repository: worktree, symlinked top, symlinked parent, bundle) | `APPLIED` |
| `vectors.py` V05 to V13 | all rejected, including V10 and V11, which passed the layout check at `be861ec0` |
| **Export without `.git`, extracted below a directory that belongs to another git repository** | **rc 2**, "the git repository top ... is not the package's own repository top". Base and `be861ec0` print `v0000 ok` |
| **Export without `.git`, `git` not on `PATH`** | **uncaught `FileNotFoundError` traceback, rc 1**. Base prints `v0000 ok`. Same at `be861ec0` |
| **Clone owned by another user (git "dubious ownership", rc 128)** | `v0000 ok`; the committed-mode half is skipped without notice |

**R-04 (P3).** Three behaviours on legitimate layouts:
- **Nested export.** `test_f04_package_inside_a_larger_repository_fails_closed` makes this deliberate, and it fails closed. It is not documented, and `CLAUDE.md` places `snapshots/` inside the repository. State in `APPROVAL_CONTROLS.md` that an export must be verified outside any git work tree, and say so in the error message.
- **git absent.** `_git` does not catch `FileNotFoundError`, and `main()` does not catch `OSError`. The run fails, but not through the uniform `LEDGER ERROR` path, and an offline machine without git cannot verify version zero at all. This arrived at `be861ec0` and was missed by the earlier review.
- **Any git failure skips the committed half.** `DISPOSITIONS_be861ec0.md` says only "a directory with no git repository at all" skips it. A repository that git refuses to open (ownership, damaged `.git`) is skipped the same way. The on-disk symlink check still runs and BIND lines still fail closed there, so the exposure is the committed-symlink-with-real-directory case only. Distinguish "not a git repository" from other failures, or correct the sentence.

## 5. Regressions and tests
- `auth_ledger.py verify`: `v0000 ok`, `HEAD 0 443c4bdf348b2a1bcd603d2701f097aa90a8155efd43c10760f5fd86c76c6b6b`, in the read-only worktree, the copy and the export.
- The four outputs `coverage_summary.json`, `source_master_register.csv`, `source_copy_register.csv`, `corpus_crosswalk.csv`: `effective/v0000`, a fresh `build --out` and `SOURCE-LIBRARY-C5/registers` are byte-identical.
- The manifest has one line. `ledger/` holds only `HEAD` and `manifest.jsonl`; `decisions/` and `corrections/` hold only a README. No entry or record exists.
- 32 of 32 drafts give the same result at base and head (all `APPLIED` in a synthetic root without binding, 32 distinct register hashes). The two result files differ only in the print order of one Python set.
- No diff against base in `ledger/`, `decisions/`, `corrections/`, `tranches/`, `evidence/`, `schema/`, `effective/`, `frozen_inputs.json`, `rules_v1.py`, `urlcheck.py`, `CALIBRATION-02`, `SOURCE-LIBRARY-C5`, `curated_originals`, `C6-01-PROVENANCE`, `C6-PREP`, `config`, `crawler`, `.github`, `schema`, `pipeline`, `data`, `tools`.
- `strength.py` and `pins.py` differ from base only in the `import os` and `sys.path.insert` lines. Their eligibility results are unchanged (the 32 drafts above).
- The two frozen originals hash to `9a8f0d19...` and `8b8d53cd...`, as the CI step expects.
- `activation_policy`, `demotion_basis` and `APPLIED_PENDING_BINDING` occur nowhere in `tools/` or `schema/`.
- Tests in the copy: 181 in the AUTH-LEDGER module, 544 in `test_legal_audit_*.py`, all pass, 0 skipped with `origin/raw-data` at `ad77758d`.

### Mutation run (`mut3.py`, 33 mutants, results in `revA3_tmp/mutation_results.json`)
16 killed, 17 survived.

| Survivor | Redundant? | Reason |
| --- | --- | --- |
| S1 to S4: `sys.path` resolved again in `ledger.py`, `auth_ledger.py`, `reader.py`, or all five tools | **No, for library use** | The CLI is still covered by the `argv[0]` pin. A library caller is not: with S1 applied, `import ledger` first returns a result through a symlinked package, where the unmutated code rejects. No test imports through a link without patching `COMMITTED_PACKAGE` |
| L9: `COMMITTED_PACKAGE = PKG` | **No, for library use** | Same path as S1 |
| A1: `argv[0]` pin removed | Yes | The unresolved `sys.path` covers the CLI; removing both is killed (A2) |
| A3: CLI root set to the resolved `PKG` | Yes | The resolve clause of `is_committed_package` still triggers the check on the logical path |
| A5: layout call removed from `auth_ledger.verify` | Near | The reader call follows; only the order of the first reads changes |
| L2: abspath clause of `is_committed_package` | Yes | Implied by the resolve clause |
| **H3: blobs not re-hashed** | **No** | With H3 applied, `forge_more.py blob` returns `APPLIED`. The branch has no blob-forgery test |
| **H8: base manifest read without re-hashing** | **No** | With H8 applied, `forge_base.py` returns `APPLIED`. No test forges the base |
| H4: commit re-hash inside `_read_verified` | Yes | The same four commits are hashed at the earlier call sites |
| H5, H6: non-file tree entry not raised | Yes | `cat-file` fails or the content check fails; still closed |
| H7, H9: manifest or pinned blobs at the reviewed head read unverified | Yes | The equality loop verifies the same objects |
| H10, H11: package-tree and pinned-path ids by `rev-parse` | Yes | The same trees are verified by the other reads, and the package tree ids are equal |

Killed: both sides removed (A2), resolved `argv` (A4), reader layout call (R1), resolve clause (L3), top mismatch (G1), missing HEAD (G2), absent component (G3), 120000-only (G4), intermediate components (G5, G6), whole committed half (G7), no hash compare (H1), trees not hashed (H2), package-tree equality (H12).

**R-03 (P3).** The disposition of F-03 says the survivors are "documented redundant layers". That holds for the ones it lists. Its mutation set did not include blob hashing, the base path, or the library import path, and those three are not redundant. The production code is correct for all three; only the tests are missing. `C8_SECURITY_CLOSEOUT.md` still carries the round-1 sentence "A mutation run on the 8 new controls killed all 8", which the earlier review already showed to be selective.

## 6. CI branch
- `git diff eed9e0bc 30f6015f`: one file, 11 added lines, one new `run` step. Full diff against base: 18 added lines.
- Unchanged: `permissions: contents: read`, the triggers (`pull_request` with the same paths, `workflow_dispatch`), no secret, `persist-credentials: false`. The step interpolates no workflow expression, so no untrusted input reaches the shell.
- The pin `ad77758d4569ba6aafa955cc7843d874489e10f7` is the commit that `canonical_coverage.json` and the other committed WS-D outputs record.
- Simulated in a copy of `30f6015f`:

| Case | Step result | `canonical_coverage.py --check`, `build_identity_map.py --check` |
| --- | --- | --- |
| Ref absent, pin commit present | ref created at the pin, rc 0 | `MATCH`, `MATCH` |
| Ref moved to another commit (a newer tip), before the step | n/a | `DIFFERS`, `DIFFERS`, rc 1 (this is CI-01) |
| The same, after the step | ref reset to the pin, rc 0 | `MATCH`, `MATCH` |
| Pin commit unavailable | ref deleted, `::warning::` printed, rc 0 | "regeneration NOT_CHECKED; pinned inputs MATCH", rc 0 |
| Pin unavailable and ref already absent | warning, rc 0 (`|| true`) | as above |

- The ref is changed only in the runner's clone. Nothing is pushed, and no credential is kept.
- **CI-01 is resolved.**
- **CI-R1 (INFO).** The pin is a second copy of a value held in the committed outputs. When the WS-D outputs are regenerated from a newer corpus commit, the workflow must change in the same PR; if not, the check fails, which is the safe direction. Reading the commit from `canonical_coverage.json` would remove the duplicate.
- **CI-R2 (INFO).** If the pinned commit becomes unreachable, the job stays green with five tests skipped and one warning annotation. That is the documented fallback; the owner should know it lowers coverage quietly.
- **CI-02 stays open.** The first full-history run must be timed on a runner.

## 7. Documents
| Document | Over-claim or stale text | Finding |
| --- | --- | --- |
| `APPROVAL_CONTROLS.md` | "forged commit, tree or blob objects on every path the verdict reads (... and every tree and blob below them), all re-hashed". The ancestry commits are not hashed, and "every tree and blob below them" is wider than "on each path read", which the next sentence states correctly | R-02 |
| `APPROVAL_CONTROLS.md` | "run the command-line tool by its repository path from outside the package" is not enough for a link above the package | R-01 |
| `C8_SECURITY_CLOSEOUT.md` | "Objects that the verdict never reads are not hashed" | R-02 |
| `C8_SECURITY_CLOSEOUT.md` | Round-1 row still lists `apply_ledger` as a place where the layout check runs. This round removed that call | R-05 |
| `C8_SECURITY_CLOSEOUT.md` | "A mutation run on the 8 new controls killed all 8" | R-03 |
| `DISPOSITIONS_be861ec0.md` | F-04: "Only a directory with no git repository at all ... skips the git half" | R-04 |
| `DISPOSITIONS_be861ec0.md` | F-03: "The survivors are documented redundant layers" | R-03 |
| `REPOSITORY_BINDING_READINESS.md` | "tested for commits and trees" is accurate: blobs are hashed but not tested. No over-claim on owner identity | none |
| `DEMOTION_SEMANTICS_O5.md` | The four F-06 points are addressed and the text says "visible, not prevented". One sentence remains loose: "a demotion is never less safe than the status quo" sits beside the constraint that suppression is a harm. Analysis only; no code | INFO, in R-05 |

**R-06 (INFO).** `apply_ledger` no longer runs the layout check. A caller that uses `ledger.apply_ledger` directly, without the reader, reads version zero and unbound lines through a symlinked package. BIND lines are still protected there by the repository-top pin (V13 is still rejected by it).

## 8. Not checked
- GitHub branch protection, required reviews, any review id or login, runner timing.
- The remote state of any branch; the Hugging Face dataset.
- Signatures or owner identity. None exists to check.
- Authenticity or legal correctness of any held source.
- Python 3.11, and git versions other than 2.43.0.
- F-09 behaviour of synthetic roots; any code outside the correction diff.

## Conditions for the security branch
1. R-02: hash the ancestry commits, or correct the two sentences and list the ancestry walk as a residual.
2. R-03: add tests for a forged blob, a forged merge-base tree, and a library import through a symlinked package without patching `COMMITTED_PACKAGE`. Remove or correct "killed all 8".
3. R-04: document that an export must be verified outside any git work tree; turn a missing `git` into a `LedgerError`; correct the F-04 sentence or tell "not a git repository" apart from other failures.
4. R-01: reword the guidance (repository top or above, or absolute path), fix the usage line in `auth_ledger.py`, and consider the `$PWD` check.
5. R-05: correct the stale `apply_ledger` reference.

## Conditions for the CI branch
1. CI-02: time the first full-history run against the 10-minute limit.

VERDICT (security): ACCEPT WITH CONDITIONS
VERDICT (CI): ACCEPT WITH CONDITIONS

Model identity: Fable 5.2 (`claude-fable-5-2`).
