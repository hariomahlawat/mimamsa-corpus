# Dispositions: Fable 5.2 (claude-fable-5-2) review of extraction v2 and the holdout scoring

**Verdict:** the conclusion stands. The extractor is below the 95% bar, so outcome fields stay unverified candidates. The review raised 16 findings: 1 P1, 7 P2, 4 P3 and 4 INFO.

| ID | Sev | Disposition |
| --- | --- | --- |
| F01 | P1 | **FIXED by a release filter. The frozen extractor is not changed, so the holdout measurement stays valid.** `tools/release_filter_c11.py` → `extraction/release/OUTCOMES_V2_RELEASE.csv`.<br>Every outcome row whose judgment shares its text with another file (292 judgment ids), or whose proceeding label lists several case numbers, is released as `OUTCOME_UNVERIFIED` (227 rows), with `v2_outcome_original` kept.<br>Checked: all 34 copies of the H042 J&K batch, which were all "dismissed" although four petitions were allowed, partly allowed or set aside, are now unverified.<br>**Downstream use must read the RELEASE file, not `outputs/OUTCOMES_V2.csv`.** |
| F02 | P2 | **RECORDED.** The single-coded ground truth is stated in `HOLDOUT_EVALUATION.md`. The next holdout is to be double-coded under one convention. |
| F03 | P2 | **RECORDED.** Population-weighted precision (about 79%) is added to the report. |
| F04 | P2 | **RECORDED.** Family-based baselines (crawler 75.0%, C10 64.6%, v2 86.4%; the intervals overlap) are added to the report. |
| F05 | P2 | **v3 REQUIREMENT.** "Partly succeeds" and extent-qualified allowances must map to partly_allowed or abstain. |
| F06 | P2 | **RECORDED; v3 REQUIREMENT.** Holding recall is 16/133 = 12.0%. The proposition candidates are leads and do not cover the court's holdings; they must not be used as a holdings index. |
| F07 | P2 | **RECORDED.** Origin-label precision: holding 92.5%, reasoning 85.0%, quoted precedent 73.3%, submission 80.0%, headnote 100%, lower court 60.0%. The labels are not precise enough to filter on unreviewed, and every candidate stays `AUTOMATED_CANDIDATE_NOT_VERIFIED`. |
| F08 | P2 | **v3 REQUIREMENT.** A court sentence after a closing quote is treated as quoted. This causes 51 corpus abstentions, including H034 and H055. |
| F09 | P3 | **RECORDED.** The freeze is attested by the tool hashes and by the reviewer's byte-identical re-run. Its timing cannot be proved from the artifacts, because everything is in one commit. Next time the frozen extractor will be committed before predictions are made. |
| F10–F11 | P3 | **v3 REQUIREMENT.** Proceeding labels and abstain-reason text need tests and cleaning. |
| F12 | P3 | **RECORDED.** Six ground-truth rows to adjudicate (H010, H012, H019, H021, H026, H027). None moves the count except through the labelling convention. |
| INFO | — | Noted. The sample is dominated by Punjab & Haryana templates beyond the holdout; all excerpts are verbatim. |
