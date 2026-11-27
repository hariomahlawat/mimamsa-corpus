# Follow-up confirmation at cec4e92c

This re-checks the three items left open by `confirmation_c12_43190971.md`: the two PARTIALLY_CLOSED findings and the temp-directory P3. The review was read-only. Experiments ran in the fresh clone `confirm_c12/repo`, checked out at cec4e92c, and the adviser `--check` was also run in c12w.

| Source | ID | Verdict | Evidence | Remaining |
| --- | --- | --- | --- | --- |
| C11 extraction review | F04 | CLOSED_VERIFIED | See [C11 F04](#c11-f04) | None |
| C12 coordinator tools | F04 | CLOSED_VERIFIED | See [C12-tools F04](#c12-tools-f04) | Optional P3 pointers (see below) |
| Confirmation P3 | adviser `--check` temp directory | CLOSED_VERIFIED | See [Temp directory](#temp-directory) | P3: clean up with try/finally |
| Confirmation P3 | absolute path in provenance | DEFERRED, as the coordinator recorded | Not re-checked | Unchanged |

## C11 F04

All three gaps from the earlier review are fixed in `HOLDOUT_EVALUATION.md`:

- **Line 49:** "v2 is substantially better than both baselines" is struck through. It now gives the measured margins: 38/44, 33/44 and 31/48.
- **Family table:** each method now has a two-sided 95% Wilson interval.
  - I recomputed all three intervals and they match: 73.3–93.6%, 60.6–85.4% and 50.4–76.6%.
  - The statement that the intervals overlap holds.
- **Baseline rows (lines 24–25):** both rows are now labelled exact-label, with a pointer to the family scoring.

## C12-tools F04

`holdout_v3/PROCESS_NOTE.md` now documents how coder separation worked. It says separation rested on instructions alone: there was no technical isolation and no access log.

It also:
- states that the original 14 adjudications saw the codings labelled A/B;
- states that the two adjudications added later saw them anonymised as X/Y;
- corrects the "blind third coder" wording of commit ed5362e5;
- corrects 136 to 134.

All of this is consistent with the artefacts. `TASK_REGISTER.md` now says 134/150.

**Not verifiable:** the note's claim that the X/Y mapping was held outside the adjudicator's working directory, and the coders' adherence to their instructions. The note openly admits this.

**Remaining (P3, optional):** `CODING_CONVENTION.md` line 3 and the docstring of `holdout_v3_truth_c12.py` still say "blind ... to each other" without qualification. They should add a pointer to `PROCESS_NOTE.md`.

## Temp directory

`shutil.rmtree(OUT)` now runs before `sys.exit`, on both the pass and the fail path:

- **In c12w:** the check passed (rc 0), `git status` was unchanged, and no new `/tmp/adviser_check_*` directory was left behind.
- **In the fresh clone at cec4e92c:** the check failed (rc 1, because of the absolute path) and still left no directory.

**Remaining (P3):** an exception raised before the `rmtree` would still leave the directory. Wrapping the cleanup in try/finally would close this.

**Cleanup note:** while testing, I first ran the old code from a clone still at 43190971 by mistake. That left one directory, `/tmp/adviser_check_2mjbtge2`, which I removed.

No new P1 or P2.
