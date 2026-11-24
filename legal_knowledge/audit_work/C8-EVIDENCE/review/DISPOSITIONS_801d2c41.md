# Dispositions: focused Fable 5.2 re-review of 801d2c41

- **Review:** `fable_rereview_c8_evidence_801d2c41.md` and `_findings.csv`, copied verbatim.
- **Scope:** a focused re-review of the corrections, not a fresh full review.
- **Verdict:** **ACCEPT**. B-01 to B-12 are closed and no regression was found.

This commit adds only the review record. No evidence, generator or package changed.

| ID | Sev | Disposition |
| --- | --- | --- |
| R-01 | P3 | **Open, next pass.** C8-CR-14 (the Hindi/English footnote difference) is to be added to the T1-19 limitations in `build_c8b.py`. It concerns chronology only; T1-19 is held for P-D2 in any case |
| R-02 | P3 | **Owner decision.** Trim `SC-T2/tools/mullikote_half_diff.txt`, which keeps two fragments of a service-date table as evidence for B-07, or accept it |
| R-03 | INFO | Recorded. C8-PIC-40 is a context check counted as CONFIRMED, as the README states |
| R-04 | INFO | **Owner decision.** Commit 5212a95b, already pushed, still contains page text later removed (B-03), including a named individual's medical detail from a published judgment. The options are to rewrite and force-push the branch, to squash at merge and delete the branch, or to accept it. No agent will rewrite history without that decision |
| R-05 | INFO | Recorded |
