# C12 findings consolidation: the review-findings register and the current status of each finding

**What this is.** One register of every row in the review findings CSVs of the Mimamsa audit record. Each row carries its current status and the repository file that establishes that status. It is a record-keeping aid only. **It makes no legal conclusion**, and a status of CLOSED_VERIFIED says only that a later independent technical review recorded the item as closed. It does not say the underlying content is legally correct.

| File | Role |
| --- | --- |
| `DISPOSITIONS.csv` | Hand-assigned table: `source_file,id,current_status,status_evidence_file,reason_or_note,cycle13_action` (501 rows) |
| `FINDINGS_CONSOLIDATED.csv` | Tool output: the inventory joined to the dispositions (501 rows) |
| `tools/consolidate_findings_c12.py` | Deterministic builder. `--check` regenerates the output and byte-compares it with the committed file |

```
python -I -B legal_knowledge/audit_work/C12-CONSOLIDATION/findings_consolidation/tools/consolidate_findings_c12.py --check
```
The tool needs the staging commit `e0b3e7d2` locally (`git fetch origin legal-knowledge/v2.5-staging`). It fails (rc 2) in any of these cases:
- a findings row has no disposition, or a disposition has no row;
- a status is outside the vocabulary;
- an evidence file does not exist.

**State consolidated:** branch `claude/c12-consolidation` at `3a118cff`, plus the staging commit `e0b3e7d2`. The date is 2026-11-24.

## Counts: severity by status (501 rows)

| Severity | CLOSED_VERIFIED | CLOSED_BY_AUTHOR_UNCONFIRMED | DEFERRED_WITH_REASON | OPEN_NO_RECORD | SUPERSEDED | NOT_A_DEFECT | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| P1 | 9 | 0 | 0 | 2 | 0 | 0 | 11 |
| P2 | 76 | 9 | 5 | 11 | 0 | 0 | 101 |
| P3 | 136 | 16 | 38 | 19 | 3 | 0 | 212 |
| INFO | 20 | 1 | 15 | 6 | 18 | 117 | 177 |
| **Total** | 241 | 26 | 58 | 38 | 21 | 117 | 501 |

The rows are rows, not distinct issues. Re-reviews often restate earlier findings as status rows, and those status rows are counted here as rows in their own right. Examples:
- AUTH-LEDGER `fable_rereview_findings_2e2df5ce.csv` F-01 to F-17;
- C8 `fable_confirm_..._0e75a4a3` RR-01 to RR-08;
- C11 relations v11, v12 and v13 status rows.

Each status row gets the same status as the finding it restates.

## WARNING: 27 P1/P2 rows are not CLOSED_VERIFIED (expected zero)

### A. Earlier cycles (10 rows)

| File | ID | Sev | Status | Why |
| --- | --- | --- | --- | --- |
| `C10-RECONCILIATION/review/final_head_confirmations/fable_review_7ccb9c2e_findings.csv` | RR-01 | P2 | CLOSED_BY_AUTHOR_UNCONFIRMED | The author fixed the court-bucket groups in `554c46cc`, but no independent re-review covers that commit. A consolidator spot-check, which is not independent, found 0 `RD-*` rows and 8 groups. |
| same | RR-02 | P2 | CLOSED_BY_AUTHOR_UNCONFIRMED | The `hf_snapshot` wording was fixed in `554c46cc` and has not been re-reviewed. |
| `C10-RECONCILIATION/review/fable_review_recon_160adfd1_findings.csv` | RC-04 | P2 | CLOSED_BY_AUTHOR_UNCONFIRMED | The remainder of this finding is RR-02. |
| `C11-JUDICIAL-QUALITY/review/fable_review_extraction_c11_findings.csv` | F02 | P2 | DEFERRED_WITH_REASON | The single-coded holdout is recorded. The next holdout is to be double-coded: C12 WS-D `holdout_v3` is in progress. |
| same | F03, F04 | P2 | CLOSED_BY_AUTHOR_UNCONFIRMED | The weighted precision and the family baselines were added to `HOLDOUT_EVALUATION.md`. No review confirms them. |
| same | F05, F06, F08 | P2 | DEFERRED_WITH_REASON | These are carried as requirements for extractor v3. |
| same | F07 | P2 | DEFERRED_WITH_REASON | The origin-label precision is published. The labels are not to be used as unreviewed filters. |

### B. C12 reviews recorded on this branch while the consolidation was running (17 rows; in progress)

| File | IDs | Status |
| --- | --- | --- |
| `C12-CONSOLIDATION/reviews/review_wsf_statutory_findings.csv` | **F-01 (P1)**, F-02 to F-06 (P2) | OPEN_NO_RECORD. The review was recorded in `8f764ea2` and has no disposition yet. |
| `C12-CONSOLIDATION/reviews/review_wsg_forms_findings.csv` | **WSG-R01 (P1)**, WSG-R02 to WSG-R07 (P2) | OPEN_NO_RECORD. The review was recorded in `a3613e73` and has no disposition yet. |
| `C12-CONSOLIDATION/reviews/review_c12_coordinator_tools_25723740_findings.csv` | F01 to F04 (P2) | CLOSED_BY_AUTHOR_UNCONFIRMED. The author fixed these in `499b89ac` and `6a86882d`; no confirmation review has been run. |

**P2 closed only at wording level, with the work still open:**
- **What:** C10 `160adfd1` RC-05, the HF per-file listing and the full read of `SHA256SUMS`.
- **What the confirmation covers:** the wording fix (7ccb9c2e RR-09).
- **What is still open:** the verification itself. C11 `HF_VERIFICATION_REPORT.md` sampled `SHA256SUMS` but did not read it in full.
- **Owner action:** a download at a pinned revision, followed by `sha256sum -c`.

**Every other P1/P2 is CLOSED_VERIFIED.** That covers AUTH-LEDGER, C6-01, C8-SOURCES, the C10 workstreams, C11 coordinator, identity and relations, and the PR #46 blueprint.

## Open and deferred P3 (and the INFO items needing action), grouped by recommended Cycle 13 owner

Each row's `cycle13_action` column gives the specific action.

### Engineering
- **AUTH-LEDGER:**
  - CI-02 / CI-R3: record closure. R48 item 4d shows the job, which includes the full-history checkout, finishing in 3 min 18 s against a 10-minute timeout.
  - CB-01, CB-02: the PR #44 follow-up tests and wording.
  - C-05 (INFO): decide on an ASCII-only decoded-path rule.
  - Confirm the author-closed items bb1f0971 F-01 and F-04, and CA-03.
- **C8-SOURCES:**
  - RR-03 remainder: CSV BOM handling and scalar type checks in `reconcile_judgments.py`.
  - C3-01 and C3-03: the pr39 review N-02 found these only part done (docstring and README).
- **C10:**
  - The CL-01, CL-02 and CC-01 follow-ups, carried from PRs #40 and #41.
  - RR-03 and RR-06, the C10 core residuals: basis wording and invariant tests.
  - WS-10: judicial wording.
  - E2-09 (INFO): record the PyMuPDF version at the next re-extraction.
  - RC-13 (INFO): the anchor-count statement. Its anchor part has no disposition.
  - Confirm RC-06, RC-07, RC-08 and RC-12, which the author closed without confirmation.
  - Get an independent review of `554c46cc`, which closes RR-01, RR-02 and RC-04 above.
- **C11:**
  - R2-01 to R2-03 (coordinator) and R2-1 to R2-3 (identity) follow-ups.
  - V13-01 to V13-04 (relations). Until V13-01 is fixed, the adviser should disregard the four rows listed in `DISPOSITIONS_relations_c11.md`.
  - V12-02: OPEN_NO_RECORD. It is not in the round-4 closures.
  - F09 to F11: v3 requirements.
- **C12:**
  - R48-05, R48-06 and R48-07 (deferred).
  - Coordinator-tools F05 to F11 (no disposition yet).
  - WS-F F-07 to F-10 and WS-G R08 to R11 (no disposition yet).
  - Optional: R48-09 and R48-11.
- **PR #46 (staging):** D-01 and D-03, both wording.

### Legal adviser
- **C10 RR-04:** the authority-matrix order of open-data bulk copies against SCR renditions. This was escalated, and no status depends on it.
- **C11 C-11:** read the two comparison labels, Prithi Pal Singh Bedi and Ratan Singh.
- **C11 F12:** adjudicate six holdout ground-truth rows, jointly with the owner.
- **WS-G:** WSG-R12, which concerns the form typing of DPP Sch. II. WSG-R02 and WSG-R03 are P2 and listed above.
- **C8 RR-INFO-01 (optional):** whether to cite the Gazette recital of the pre-1992 wording.

### Owner decision
- **C6-01:**
  - R-08: whether the RS papers-laid record should be DOCUMENTED.
  - R-03 and R-09: NON_PRIMARY handling and vocabulary at incorporation. Check whether AUTH-LEDGER `COMPAT` already covers R-03.
  - R-04: the TRA 2026 class.
- **AUTH-LEDGER O-5:** demotion semantics.
- **PR #46:**
  - D-02, D-04 and D-05.
  - F-13: the cold-review record is missing; its author should commit it.
  - The Legal Reviewer designation (ADR-0003 blocking decision 1), noted against F-01.
- **C11 C-16 (INFO):** re-acquisition targets AWS open-data mirrors, not court-hosted copies.

### Carry-overs that need no new review
The C6-01 master-title corrections C5-CO-03 and C5-CO-04 are recorded, and are to be applied at the next C5 maintenance.

## Method
1. **Inventory.**
   - The tool collects every tracked file matching `findings*.csv` under `legal_knowledge/audit_work/{AUTH-LEDGER, C6-01-PROVENANCE, C8-SOURCES/review, C10-RECONCILIATION, C11-JUDICIAL-QUALITY, C12-CONSOLIDATION/reviews}`, giving 38 files.
   - It adds the two PR #46 CSVs read from staging `e0b3e7d2`.
   - The first column is taken as the id.
   - Severity is normalised by the first `P1`/`P2`/`P3`/`INFO` token. For example, "P2 in round 1" becomes P2, and "was P3" becomes P3.
   - The statement is the first non-empty column among `title`, `statement`, `summary`, `finding`, `observation` and `evidence_or_counterexample`. The `2e2df5ce` re-review uses its status plus evidence instead. Whitespace is collapsed and the text is cut at 220 characters.
2. **Status.** Each status was assigned by reading, for each review chain:
   - the review;
   - every later re-review or confirmation;
   - the `DISPOSITIONS_*` file;
   - closeout and closure documents: `C8_SECURITY_CLOSEOUT.md`, `D3_INDEPENDENT_VERIFICATION.md`, `DISPOSITIONS_final_head_confirmations.md`, `TASK_REGISTER.md` and `REVIEW_CLOSURE_C12.md`.

   Where later independent reviews exist only on staging, they were read there and are cited with a `staging:` prefix:
   - PR #38 `562a55ef`;
   - PR #39 `2d7c02cf`;
   - PR #44 `9f1d7560`;
   - the PR #46 delta.
3. **Status rules.**
   - **CLOSED_VERIFIED:** a later independent review records the item, or its residual, as closed.
   - **CLOSED_BY_AUTHOR_UNCONFIRMED:** only the author's disposition or commit records the fix.
   - **DEFERRED_WITH_REASON:** a record defers the item with a reason. This includes accepted and documented residuals ("Recorded"), carried follow-ups and v3 requirements.
   - **OPEN_NO_RECORD:** no disposition was found, or a later review found the item only part done and nothing disposes of the residual.
   - **SUPERSEDED:** the item is tracked under another finding or work item, which is named in the note.
   - **NOT_A_DEFECT:** a confirmation or PASS row, a by-design note, a reviewer scope statement, or an optional suggestion declined with a reason that the reviewer accepted.

## Limitations
- **Live branch.** Three C12 reviews (WS-F, WS-G, coordinator tools) were committed while this ran, and their dispositions are in progress. Any new findings CSV makes the tool fail (rc 2) until `DISPOSITIONS.csv` is extended. That is intended.
- **Uncommitted evidence.** For R48-05 to R48-07 and R48-12, the evidence is the working-tree edit of `TASK_REGISTER.md` made by another agent. It was not committed when this register was consolidated.
- **Not inventoried.** These findings CSVs exist on staging but not on this branch, and they are outside the requested input set:
  - `AUTH-LEDGER/review/fable_narrow_pr38_562a55ef`;
  - `AUTH-LEDGER/review/fable_review_c10_effective_4770c165`;
  - `AUTH-LEDGER/review/fable_review_pr44_9f1d7560`;
  - `C8-EVIDENCE/review/` (2 files);
  - `C8-SOURCES/review/fable_narrow_pr39_2d7c02cf`;
  - `C9-EVIDENCE-CLEAN/review/` (2);
  - `C9-LEGAL-EVIDENCE/review/` (2).

  Some of these were read as status evidence.
- **Out of the requested scope.** These were not inventoried:
  - findings in review markdown that has no CSV, such as C6-01 `fable_review_a165b0f3`, its re-reviews, and AUTH-LEDGER `fable_confirm_96e0d251`;
  - `CALIBRATION-02`, `SOURCE-LIBRARY-C5`, `COORDINATION`, `C8-SOURCES/CORPUS-QUALITY` and `verification_batches` findings CSVs.
- **ID mismatch.** `DISPOSITIONS_160adfd1.md` numbers its INFO rows differently from the findings CSV:
  - CSV RC-13 corresponds to disposition RC-13 together with RC-14;
  - CSV RC-14 corresponds to disposition RC-15;
  - CSV RC-15, the reviewer's scope note, has no disposition.
- **Consolidator checks.** Spot-checks the consolidator made, such as file contents for RR-01 and RR-02 and text present in `HOLDOUT_EVALUATION.md`, are recorded in the notes. They are not independent reviews, and they do not change any status.
