# C13-A5 post-freeze addendum (pre-integration review of e15af208)

The freeze at `e15af208` stands. `FREEZE_RECORD_C13_A5.md` and `FREEZE_C13_A5.json` are not edited, and neither are the frozen artefacts:
- `treatment_c13.py`: `f8be7a01…`
- `common_c13.py`: `ec7fe04a…`
- `predict_hrel_c13.py`: `eb2bbd96…`
- predictions: `c53ea96a…`

Post-freeze commits add tooling, tests and documentation only.

## A5-01a: PyMuPDF absent in legal-audit CI

**Tool change.** `scnum_reconfirm_c13.py` (not frozen) gains an artefact-only `--check` path for runs without PyMuPDF. It prints `CHECK PARTIAL (PyMuPDF absent)`, names the skipped steps (PDF text-layer re-extraction and text-layer matching), and verifies the committed artefacts. It never prints CHECK OK in that mode.

**PyMuPDF is not added to CI.** It is licensed AGPL, so adding it is the coordinator's decision.

## A5-01b: provenance label after the merge

**The problem.** The frozen `common_c13.load_restricted()` labels the register by where it read it from (worktree or git). Staging now carries `config/restricted_material.json`, so the label changed although the bytes (`fc7ea07e…`) did not.

**The fix.**
- `provenance_pin_c13.py` reports the established label `git:72fe7a75:config/restricted_material.json` whenever the bytes equal the pin.
- `run_check_c13.py` applies the pin to the frozen tools without editing them.
- With the pin, the frozen predictions manifest reproduces byte-identically in both environments, so no regeneration was needed.

## A5-02: contract v1 test without jsonschema

The Track B validator test now skips with an explicit reason when jsonschema is not installed. If the validator writes no report, the test fails with its stderr; it no longer raises `JSONDecodeError`.

## A5-03: README

The README now states the FROZEN status and gives the blind GA4 descriptive results:
- relation_type precision 0.340 [0.161, 0.560];
- `follows` recall 0.032 (5/154);
- 0/53 `distinguishes`;
- target precision 0.620.

The in-sample 98.2% figure is marked superseded, development evidence only.
