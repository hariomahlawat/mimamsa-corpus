# SYNTHETIC AUTH-LEDGER first-transaction demonstration

**Everything here is synthetic.** The demo writes no real approval record, no owner decision and no signature. **The real ledger stays at version 0.** Its HEAD is `0 443c4bdf…6c6b6b` before and after every run, and the demo checks this.

## What the demo does
`tools/synthetic_transaction_demo.py` runs offline and deterministically.

1. It copies the real AUTH-LEDGER package from `--source` (default: the repository that contains this folder). The recorded run used the **fully integrated staging** `21e73b83`, after PRs #37, #38 and #39. Its AUTH-LEDGER tools tree, `22b4e6d7`, is identical to the reviewed security head `562a55ef`; all 43 recorded values are identical to the first run on `562a55ef`, and `--check` passes against both. The package is copied into a fresh temporary git repository, created with `mktemp`-style naming under `TXN-DEMO/work/` and uses the real layout `legal_knowledge/audit_work/AUTH-LEDGER`. The copy includes:
   - `tools/*.py`, `schema/`, `frozen_inputs.json`;
   - the genesis `ledger/manifest.jsonl` and `ledger/HEAD`;
   - `decisions/README.md`, `evidence/` and `effective/v0000/`;
   - all **76 pinned input files** that `pins.py` and `reader.py` read.
2. It then drives a full transaction through the **real code**. The CLI `auth_ledger.py verify` and `build --as-of N` are invoked by absolute path inside the temporary repository. The tool therefore treats that package as the committed ledger: `COMMITTED_PACKAGE`, the layout check and the pinned repository top all apply.

| Step | Ledger versions | Shown |
| --- | --- | --- |
| 0 | genesis | The copied package verifies, and its HEAD equals the real genesis HEAD |
| a | v1 ADD | Built from two real C6-01 draft rows (Dharamvir Singh SC 2013; Army Rules Gazette S.R.O. 1 of 1962), with justification and limitations prefixed `SYNTHETIC DEMONSTRATION ENTRY`. The D-/R- records name `SYNTHETIC OWNER (test)` and `SYNTHETIC REVIEWER (test)`, with the required `scope:` and `legal_approval: NOT_GIVEN` lines. The version sits on a PR branch and is merged with `--no-ff`. It is `PENDING_REPOSITORY_BINDING`, and registers, crosswalk and coverage stay byte-identical to v0 |
| b | v2 BIND | A later PR adds the BIND line; `verify` passes. Both entries are `APPLIED` with `bound_by 2`, and the GitHub review is reported as `ASSERTED_NOT_VERIFIED_OFFLINE`. DCLR-SC-2013-N08 moves PARTIAL_MATCH → EXACT_ANCHOR |
| d | v3 CORRECTION + v4 BIND | The Gazette row's class is demoted to non-primary; the source falls back after the bind |
| e | v5 WITHDRAW + v6 BIND | The Dharamvir row goes to PROVENANCE_UNKNOWN. The withdrawal is staged until its bind (current O5-A semantics), then the EXACT_ANCHOR drops |
| f | v7 ADD + v8 BIND | Re-authentication with a new entry id and new records; the EXACT_ANCHOR returns |
| c | as-of 0..8 | Run with HEAD at v8. Every `--as-of N` equals the build made when N was recorded, the committed `effective/vNNNN`, and the manifest pin |
| g | negatives, each in a fresh `--no-local` clone | Each is rejected with exit 2 and the real message: an owner record naming an AI agent; a decision dated before the review; an unbound version followed by another entry version; a tampered pinned D-record; a BIND naming a `--ff-only` fast-forward, plus a variant naming a non-merge; and, as a design rule, a WITHDRAW targeting a CORRECTION |

Outputs:
- `TRANSCRIPT.md`: every step, command, exit code, output, check, and effective-state change and hash.
- `expected_hashes.json`: 43 recorded values. They cover commit ids, the final HEAD and manifest hash, per-version effective hashes and transitions, CLI outputs and negative messages.

## What it proves
The combined code base (C8 security branch with BIND-line verification) mechanically supports the full lifecycle:
- staging;
- offline-verified binding;
- CORRECTION, WITHDRAW and re-ADD;
- reproducible history;
- the listed rejections.

It does this through the real CLI, at the real package path, with commit ids that reproduce exactly.

## What it does not prove
- **No approval exists.** The records are synthetic, and the PR numbers, review ids and logins are invented. Binding verifies git topology only. As `APPROVAL_CONTROLS.md` states, a local `--no-ff` merge with invented review values verifies topologically.
- **Owner identity is not proven.** `decided_by` is text. There is no signature (O-1), and branch protection (O-2) is outside git.
- **Legal or JAG approval is out of scope.** Nothing here concerns legal status, currency or applicability.
- **The evidence is not judged.** The demo does not judge the evidence of the two draft rows beyond the real rule-1 checks that the code runs.

## Re-run
```bash
PYTHONDONTWRITEBYTECODE=1 <venv>/bin/python -B TXN-DEMO/tools/synthetic_transaction_demo.py --check     # compare (about 50 s)
```
```bash
PYTHONDONTWRITEBYTECODE=1 <venv>/bin/python -B TXN-DEMO/tools/synthetic_transaction_demo.py             # regenerate TRANSCRIPT.md + expected_hashes.json
```
```bash
PYTHONDONTWRITEBYTECODE=1 <venv>/bin/python -B -m unittest discover -s TXN-DEMO/tools -p 'test_synthetic_transaction.py'
```

Options:
- `--source REPO`, or the environment variable `AUTH_LEDGER_SOURCE`, chooses the package to exercise.
- `--keep` leaves the temporary repository in place for inspection.

How the run stays isolated:
- git runs with a repo-local empty config (`GIT_CONFIG_GLOBAL` points to an empty file in the temporary directory, plus `GIT_CONFIG_NOSYSTEM`), with fixed author and committer names and dates, and with no host git config.
- The temporary directory is deleted at the end.

Changing the package code or the pinned data changes the hashes. Regenerate the expected values only in a reviewed change.
