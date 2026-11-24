# Dispositions of the Cycle 9 legal-deliverables review (b1a23234, fd32c7bb, 6fe5be5f)

The verdicts were:
- **A1 (`b1a23234`):** ACCEPT WITH CONDITIONS, P3 only.
- **A2 (`fd32c7bb`):** ACCEPT WITH CONDITIONS, on LG-05 and LG-06.
- **B (`6fe5be5f`, clean branch `SC-C9/`):** ACCEPT.

There was no P1. The review is committed beside this file and is copied verbatim. The fixes below are in the next commit on this branch, which **has not been re-reviewed**.

| Id | Severity | Disposition |
| --- | --- | --- |
| LG-01 | P3 | **Fixed.** The claim now reads: 10 tests added, 7 fail against the Cycle 8 tool, 3 are regression guards. |
| LG-02 | P3 | **Fixed.** Three tests added: the BOM in the corpus cases JSONL; every string field type-checked, with the list pinned in the test rather than read from the tool; and null party values accepted. Each kills the corresponding surviving mutant (checked). |
| LG-03 | P3 | **Fixed.** The narrow reviews of `562a55ef` and `2d7c02cf` are committed. `C8-SOURCES/review/ADDENDUM_C9_NARROW_2d7c02cf.md` dispositions N-01 to N-06. `work/unittest_output.txt` is kept as the historical Cycle 8 run. |
| LG-04 | INFO | Recorded. |
| LG-05 | P2 | **Fixed.** Tarsem: "no official court copy held". The unregistered SCR-format copy in the raw store ([2008] 12 S.C.R. 104; C.A. 5151-52 of 2008; 13 August 2008; `raw-data` `f8a14181…`) is now named in the finding, the proposal text, the findings document and ESC-01 / ESC-04. These elements were re-checked against the raw-store file by the coordinator. |
| LG-06 | P2 | **Fixed.** No disputed edge has an empty or truncated `preserved_readings` cell any more. C-01 now gives both r.23(3) caution readings verbatim, with page references. Where the C5 register does not itemise its sources (U-01, U-04, U-07, U-08, C-08, C-09), the cell says so and carries the register's full conflict text and evidence. The builder's exemption is removed: an empty reading now fails the build. |
| LG-07 | P3 | **Fixed.** The wording is now "eleven instrument records correct a C8 'not held' statement; a twelfth (GMO 2023) corrects a PR #9 listing". |
| LG-08 | P3 | **Fixed.** The 67 raw-store PDFs are described as 63 India Code files and 4 official copies from other hosts, 3 of them correspondence tables. |
| LG-09 | P3 | **Fixed.** ESC-01 no longer states that a coordinate Bench "cannot overrule"; the point is left to the adviser. |
| LG-10 | P3 | **Open (documentary).** The C9R-AA-09 page list (p.12 also prints the w.e.f. date) and the `provision` cell of C9-AG-AFT-02 are left for the next regeneration. Neither changes a status. |
| LG-11 | P3 | **Fixed.** Stale `c9out/…` and `TXN/` paths are replaced with in-repository paths. The bytecode note stands: run with `python -B`, or delete `tools/__pycache__`, which is git-ignored. |
| LG-12 | P3 | **Recorded on the clean branch** (`SC-C9/ADDENDUM_LG12.md`). The raw store holds unofficial SCR-format copies of PPS Bedi, Ranjit Thakur and S N Mukherjee. They are a possible comparator for JUDIS fidelity, subject to registration (AP-C9-02). "No signed original is held" stands. |
| LG-13 to LG-16 | INFO | Recorded: JUDIS consistency, the anchor counts, the proposals, privacy (0 hits) and authorisation. |
