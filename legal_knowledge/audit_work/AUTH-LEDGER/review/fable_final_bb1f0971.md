# Narrow final review of AUTH-LEDGER-02 merge candidate bb1f0971 (reviewed code head 3f486562, base 63a79729)

Reviewer: Fable 5.2 (model id claude-fable-5-2), acting as database and evidence validation agent. RESEARCH ONLY. This is a technical check of `git diff 3f486562 bb1f0971` only. It is not owner, legal or JAG approval and signs off for nobody.

## Result
No P1 and no P2. Two P3 and three INFO items, none blocking. The production controls are byte-identical to the reviewed head 3f486562; the only non-document change is five lines of one test fixture, and that fixture still exercises the forged commit-graph vector.

## False-pass limitations (read first)
- A matching sha256 proves bit integrity only, not authenticity, currency or legal correctness.
- The canonical Hugging Face dataset was not consulted (no network). Coverage against it is unknown.
- Local git is 2.43.0. git 2.56 was NOT available. The read-only chain file was simulated (see F-01); behaviour of a real git 2.56 (forged graph still honoured by plain git, chain layout) was not observed. On 2.56 the test could in principle pass vacuously if that git ignored the forged graph; the fixture has no assertion that plain git sees two parents.
- Nothing before 3f486562 was re-reviewed. Controls, tranche texts, URL rules and mutation coverage rest on the earlier reviews.
- No GitHub fact (PR #35, CI result, branch protection) was checked.
- 5 or 6 tests skip (below); the real-corpus variants did not run.

## 1. Changed files
`git diff --name-status 3f486562 bb1f0971` (5 files, +160 -2):
- aa77a305: M `AUTH-LEDGER/APPROVAL_CONTROLS.md` (one paragraph); A `AUTH-LEDGER/review/DISPOSITIONS_3f486562.md`, `fable_confirm_3f486562.md`, `fable_confirm_3f486562_findings.csv`.
- bb1f0971: M `tests/test_legal_audit_auth_ledger.py` (+4 -1, inside `_forge_commit_graph`).

`git diff --name-status 63a79729 bb1f0971`: 32 files (24 added, 8 modified, all mode 100644, no symlink, no deletion). Every path is under `legal_knowledge/audit_work/AUTH-LEDGER/`, or is `legal_knowledge/audit_work/C7-PREP/WORKSTREAMS_READINESS.md`, or `tests/test_legal_audit_auth_ledger.py`. Filter for anything else: empty. Diff restricted to CALIBRATION-02, SOURCE-LIBRARY-C5, `curated_originals`, C6-01-PROVENANCE, C6-PREP, `config`, `crawler`, `.github` (and also `data`, `schema`, `pipeline`): 0 files. Merge base of the two is 63a79729.

## 2. Test-fixture change
- No `.py` file other than the test module differs between 3f486562 and bb1f0971; `AUTH-LEDGER/tools` and `tranches/tools` are unchanged. Production control behaviour cannot have changed.
- The change: before overwriting `commit-graph-chain`, the fixture makes it mode 0644 if it exists. Nothing else.
- Vector still live (script `c8fin/vec.py`, run at bb1f0971): for both the single file and the split chain, plain git reports 2 parents for the innocent commit, `-c core.commitGraph=false` reports 1, `git status` is empty, and the tool rejects ("merge_commit has 1 parent(s)").
- Mutant (copy only): `"-c", "core.commitGraph=false"` removed from `binding._git`. `test_r01_forged_commit_graph_single_and_split` FAILS ("LedgerError not raised"); module total 160 run, 2 failures (r01 and r06). With the mutant the tool ACCEPTS both the single and the split forgery, so the split branch is exercised too, not only the first loop pass.
- Read-only chain: this sandbox runs as uid 0, which ignores file modes, so chmod alone proves nothing. I dropped CAP_DAC_OVERRIDE (`setpriv --bounding-set=-dac_override,-dac_read_search,-fowner --inh-caps=-all`); a write to a 0444 file then fails. Under that condition: the 3f486562 fixture errors with `PermissionError ... commit-graph-chain`; the bb1f0971 fixture passes (160 OK); the mutant still fails under the new fixture. The fix does what it says.
- F-01: git 2.43.0 already writes the chain file 0444. The cause of the CI failure is a non-root runner, not (or not only) git 2.56. The comment and commit message attribute it to the git version.

## 3. Documentation change (aa77a305)
- `fable_confirm_3f486562.md` and its CSV are byte-identical (`cmp`) to the originals in `scratchpad/rev04_out/`. "Copied verbatim" is true.
- Dispositions against the review: verdict ACCEPT, no P1/P2, R-01 to R-09 closed, R-10 open: all match. C-01 and C-02 P3, C-03 to C-06 INFO: match. No finding is described as closed that the review left open; C-01 and the C-02 code check are stated as open.
- C-02 symlink note: it names the vector, places it inside the trust assumption, gives a manual check, and states that the fail-closed code check is open. This is the second alternative of the review's own required correction. It does not claim the tool detects symlinks. No over-claim. Two small gaps: F-02 and F-03.
- C-04 disposition proposes `git fsck --connectivity-only` as a candidate; whether that mode re-hashes commit objects was not tested by anyone. It is worded as a candidate, not a control. INFO only (F-05).

## 4. Ledger state
- `tools/auth_ledger.py verify` (clone and plain export): `v0000 ok` / `HEAD 0 443c4bdf348b2a1bcd603d2701f097aa90a8155efd43c10760f5fd86c76c6b6b; frozen pins ok; ledger verified`, rc 0.
- `ledger/` holds `HEAD` and `manifest.jsonl` only (one line, version 0, `file: null`). No `ledger/v*.csv`.
- `decisions/` holds only `README.md`. No `D-*` or `R-*` file.
- `effective/v0000/` `source_master_register.csv`, `source_copy_register.csv`, `corpus_crosswalk.csv`, `coverage_summary.json` are byte-identical to `SOURCE-LIBRARY-C5/registers/`.
- `owner_decision` occurs as a column in one CSV under AUTH-LEDGER (`proposed_entries_PENDING.csv`, 20 rows): empty in all 20. The string APPROVED occurs only in schema, tool code, design/controls text, `decisions/README.md` and review records; not in any data row.

## 5. Protected hashes (all equal to the expected values)
- `records_658.jsonl` 9a8f0d193065762ffa987116dc761bcb734008d2a87a946f5591741f5befcfc1
- `cases_53.jsonl` 8b8d53cd1434f7c1c6eaebe77f1fe295fb8b81b755e93276999b4b40b3c8f89a
- `CALIBRATION-02/registers/source_authentication_register.csv` cfe5f4081997abbcb88061cd7a8e5cc5b949c585cd7835fa48df51ae1a0c1ece

## 6. Tests (git 2.43.0, uid 0, copies only)
- `python -m unittest tests.test_legal_audit_auth_ledger`: 160 run, OK, 0 skipped (also OK without CAP_DAC_OVERRIDE).
- `python -m unittest discover -s tests -p "test_legal_audit_*.py"`:
  - in a git clone of the worktree: 523 run, OK, 5 skipped;
  - in a `git archive` export (no `.git`): 523 run, OK, 6 skipped.
- Skips, none in the AUTH-LEDGER module:
  - `CanonicalCoverage.test_regeneration_is_byte_identical` and `IdentityMap.test_regeneration_is_byte_identical`: "crawler corpus ref unavailable".
  - `Fix3CodedRecordSections` x3 (`test_kb003_sections_bound_to_code_target`, `test_missing_section_file_downgrades_coded_record`, `test_mixed_forms_not_discarded`): local ref `origin/raw-data` absent; the same behaviour is asserted by `Fix3WithoutCorpusRef`.
  - sixth, export only: a regeneration test ("Regenerate from exactly the pinned inputs ..."): "pinned crawler corpus commit not available locally". It ran in the clone.
- Worktree after all work: `git status` empty, HEAD bb1f0971.

## Findings (detail in the CSV)
- **F-01 (P3)** Fixture comment and commit message attribute the read-only chain file to git 2.56; git 2.43.0 writes it 0444 too, and the real trigger is running without permission override (non-root).
- **F-02 (P3)** `DISPOSITIONS_3f486562.md` says no code or test changed, scoped to "the commit that adds this file"; the merge candidate has one later test change with no review record in the package.
- **F-03 (INFO)** The symlink advice names only the package directory; a symlinked parent (`legal_knowledge` or `audit_work`) would divert in the same way. Not tested here.
- **F-04 (INFO)** The R-01 fixture does not assert that plain git accepts the forgery, so on an untested git the test could pass vacuously.
- **F-05 (INFO)** `git fsck --connectivity-only` in the C-04 disposition is an untested candidate.

## Not checked
Anything before 3f486562; a real git 2.56; the CI run itself; GitHub settings; the Hugging Face snapshot; authenticity of any source file; tranche content; a symlinked parent directory; reftable or SHA-256 repositories.

VERDICT: ACCEPT

Model identity: Fable 5.2 (claude-fable-5-2).
