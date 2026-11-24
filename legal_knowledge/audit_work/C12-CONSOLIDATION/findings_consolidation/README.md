# C12 findings consolidation: the review-findings register and the current status of each finding

**What this is.** One register of every row in the review findings CSVs of the Mimamsa audit record. Each row carries its current status and the repository file that establishes that status. It is a record-keeping aid only. **It makes no legal conclusion**, and a status of CLOSED_VERIFIED says only that a later independent technical review recorded the item as closed. It does not say the underlying content is legally correct.

| File | Role |
| --- | --- |
| `DISPOSITIONS.csv` | Hand-assigned table: `source_file,id,current_status,status_evidence_file,reason_or_note,cycle13_action` (511 rows) |
| `SUPPLEMENTARY_FINDINGS.csv` | Hand-maintained inventory of the 7 findings recorded only in confirmation markdown, with no CSV row: `source_file,id,severity,finding_text` |
| `FINDINGS_CONSOLIDATED.csv` | Tool output: the inventory joined to the dispositions (511 rows). The finding text column is `finding_text`; it is not called "statement", so the APR-1 state-column rule does not pick it up |
| `tools/consolidate_findings_c12.py` | Deterministic builder. `--check` regenerates the output and byte-compares it with the committed file |

```
python -I -B legal_knowledge/audit_work/C12-CONSOLIDATION/findings_consolidation/tools/consolidate_findings_c12.py --check
```
The tool needs the staging commit `e0b3e7d2` locally (`git fetch origin legal-knowledge/v2.5-staging`). It fails (rc 2) in any of these cases:
- a findings row has no disposition, or a disposition has no row;
- a status is outside the vocabulary;
- an evidence file does not exist.

**State consolidated:** branch `claude/c12-consolidation` at `4e3571ee` (the first version was at `3a118cff`), plus the staging commit `e0b3e7d2`. The date is 2026-11-24.

**Gate checks on this output:** both of these pass:
- `tools/legal_audit/check_provenance.py`: new=0;
- `tests/test_legal_audit_register_semantics.py`: 10 passed.

The status value `CLOSED_VERIFIED` is not read as an approval claim, because `approval_claims("CLOSED_VERIFIED")` returns no hit, so it was kept. It means only "closure confirmed by a later independent technical review". It is not a legal verification.

## Counts: severity by status (511 rows)

| Severity | CLOSED_VERIFIED | CLOSED_BY_AUTHOR_UNCONFIRMED | DEFERRED_WITH_REASON | OPEN_NO_RECORD | SUPERSEDED | NOT_A_DEFECT | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| P1 | 11 | 0 | 0 | 0 | 0 | 0 | 11 |
| P2 | 95 | 0 | 6 | 0 | 0 | 0 | 101 |
| P3 | 146 | 17 | 41 | 14 | 3 | 0 | 221 |
| INFO | 22 | 1 | 16 | 7 | 18 | 114 | 178 |
| **Total** | 274 | 18 | 63 | 21 | 21 | 114 | 511 |

The rows are rows, not distinct issues. Re-reviews often restate earlier findings as status rows, and those status rows are counted here as rows in their own right. Examples:
- AUTH-LEDGER `fable_rereview_findings_2e2df5ce.csv` F-01 to F-17;
- C8 `fable_confirm_..._0e75a4a3` RR-01 to RR-08;
- C11 relations v11, v12 and v13 status rows.

Each status row gets the same status as the finding it restates.

## P1/P2: every P1 is closed and confirmed. Six P2s are deferred with a recorded reason; none is open without a record.

The confirmations recorded at `4e3571ee` closed 21 rows that the first version of this register listed as not confirmed:
- C10: RR-01, RR-02 and RC-04;
- C11: F03 and F04;
- C12-tools: F01 to F04;
- WS-F: F-01 (P1) and F-02 to F-06;
- WS-G: R01 (P1), R02, R03, R05, R06 and R07.

These are the records:
- `reviews/confirmation_c12_43190971.md`;
- `reviews/confirmation_followup_cec4e92c.md`;
- `reviews/review_wsf_statutory_confirmation.md`;
- `reviews/review_wsg_forms_confirmation.md`.

| File | ID | Sev | Status | Reason |
| --- | --- | --- | --- | --- |
| `C11-JUDICIAL-QUALITY/review/fable_review_extraction_c11_findings.csv` | F02, F05, F06, F07, F08 | P2 | DEFERRED_WITH_REASON | `confirmation_c12_43190971.md` recorded these as DEFERRED_V3_RECORDED. They wait for the V3 holdout evaluation, and the confirmation lists what that evaluation must report. |
| `C12-CONSOLIDATION/reviews/review_wsg_forms_findings.csv` | WSG-R04 | P2 | DEFERRED_WITH_REASON | The confirmation marked it PARTIAL, as an acceptable documented deferral. The MML-version field lists are labelled, but re-transcription from the official copies has not been done. It must be done before any template is used. |

**P2 closed only at wording level, with the work still open:**
- **What:** C10 `160adfd1` RC-05, the HF per-file listing and the full read of `SHA256SUMS`.
- **What the confirmation covers:** the wording fix (7ccb9c2e RR-09).
- **What is still open:** the verification itself. C11 `HF_VERIFICATION_REPORT.md` sampled `SHA256SUMS` but did not read it in full.
- **Owner action:** a download at a pinned revision, followed by `sha256sum -c`.

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
  - R48-05, R48-06 and R48-07: deferred, as `TASK_REGISTER.md` (WS-A) records.
  - Coordinator-tools F05 to F11: no disposition. The confirmations covered F01 to F04 only.
  - WS-G R10 (17 capped ranges, optional) and R13 (one Python 3.11 run): deferred.
  - WS-F C-01: the build reads the review promotions CSV, and no test shows that no state depends on it. No disposition yet.
  - WS-F C-02: image-check the 16 text-layer-only items. Deferred.
  - Confirmation P3s:
    - CONF43-P3-2: absolute paths in the adviser provenance. Deferred, together with F11.
    - FU-P3-1: wrap the adviser `--check` cleanup in try/finally.
    - CONF43-P3-4: `key()` range handling.
    - CONF43-RR02-RES: the CAPTURE.md heading and the per-row as-of date.
  - WS-G NEW-01 (INFO): the AR 140 wording is stale.
  - Optional: R48-09 and R48-11.
- **PR #46 (staging):** D-01 and D-03, both wording.

### Legal adviser
- **C10 RR-04:** the authority-matrix order of open-data bulk copies against SCR renditions. This was escalated, and no status depends on it.
- **C11 C-11:** read the two comparison labels, Prithi Pal Singh Bedi and Ratan Singh.
- **C11 F12:** adjudicate six holdout ground-truth rows, jointly with the owner.
- **WS-G R04:** the template-use gate. The re-transcribed field lists should be reviewed before any form template is relied on.
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
   - The tool collects every tracked file matching `findings*.csv` under `legal_knowledge/audit_work/{AUTH-LEDGER, C6-01-PROVENANCE, C8-SOURCES/review, C10-RECONCILIATION, C11-JUDICIAL-QUALITY, C12-CONSOLIDATION/reviews}`.
   - **Confirmation CSVs** are files with a `verdict` column, or with no severity column. They are treated as status evidence, not as new findings. Only rows whose verdict is not CLOSED, PARTIAL, DEFERRED or OPEN, and that carry a `severity` or `original_severity`, are inventoried. At `4e3571ee` those rows are WS-F C-01 and C-02 and WS-G NEW-01. `confirmation_c12_43190971_findings.csv` contributes none.
   - P3 items raised only in confirmation markdown come from `SUPPLEMENTARY_FINDINGS.csv`.
   - It adds the two PR #46 CSVs read from staging `e0b3e7d2`.
   - The first column is taken as the id.
   - Severity is normalised by the first `P1`/`P2`/`P3`/`INFO` token. For example, "P2 in round 1" becomes P2, and "was P3" becomes P3.
   - The finding text (column `finding_text`) is the first non-empty column among `title`, `statement`, `summary`, `finding`, `observation` and `evidence_or_counterexample`. The `2e2df5ce` re-review uses its status plus evidence instead. Whitespace is collapsed and the text is cut at 220 characters.
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
- **Live branch.** C12 reviews and confirmations keep arriving. Any new findings CSV, or any new non-closure confirmation row, makes the tool fail (rc 2) until `DISPOSITIONS.csv` is extended. That is intended.
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
