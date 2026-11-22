# Coordinator review: WS-D cycle 2 (6eb8817a..451ba8d4; head after base merge ed3dcf90)
- **Scope / gates:** only WS-D-QUALITY and the leased paths; existing tests unmodified. The single removed validator line is a refactor (the summary print now also includes relation counts). 166 tests, schema check, strict validation, check_registers, check_csv and YAML all pass.
- **Process slip noted:** e285040b was committed with one failing test (gate exit status hidden by a pipe) and fixed in 60e3b975 without rewriting history. Acceptable as disclosed. The gate in GIT_WORKFLOW rule 6 applies: check exit codes directly.
- **Reconciliation:** WS-C and WS-D agree on 562/658 records; all 96 differences are explained by 11 definitional rules. Proposed three-measure canonical definitions (OQ-D-016, owner decision).
- **v4 register (new file):** usage recount only, 16 cells, all additions; resolution classes unchanged (72/87 confirmed). Frozen v3 untouched.
- **Provenance checker:** 21 legacy violations baselined. After coordinator commit 8b436b67 (the ACQ-02 authenticity/copy_fidelity split, OQ-D-017), 2 remain (PIC-08/09 render hashes, OQ-D-018) and 0 are new.
- **`manual_supported`:** as approved, it is never statutory authority and is refused as evidence.
- **check_registers tests:** 18 tests against the unmodified script. OQ-D-021 addressed by the coordinator in 8b436b67 (all r.23(3)/193/194 version rows are guarded).
- **Disposition:** accepted as a review proposal (PR #18 updated).
