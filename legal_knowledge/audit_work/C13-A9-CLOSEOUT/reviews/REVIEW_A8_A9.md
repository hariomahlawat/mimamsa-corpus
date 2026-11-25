# Independent review: Cycle 13 A8 (legal-adviser package) and A9 (closeout records)

- **Branch under review:** `claude/c13-closeout` at `9f5bf09a` (tree `6cc23dc3`). Diff against staging `f79160f5`; the diff includes the A7 merge `daba057b` and its coordinator-written `DISPOSITIONS_C13.md`.
- **Reviewer:** independent. I wrote none of A7, A8 or A9.
- **Date:** 2026-11-25.
- **Method:** I worked only in detached scratch worktrees (`reviews/a9/wt` at `9f5bf09a`, `reviews/a9/wt_stg` at `f79160f5`, and the scratchpad-level `a9rev_head`, `a9rev_stg` and `a9rev_a4c` at `a4c0c382`). I did not modify the branch: `git status` in `c13/closeout` shows only an ignored `__pycache__`. Reviewer artefacts are in `reviews/a9/`: the gate output `gate_9f5bf09a.txt`, the C12 check outputs `c12out_*` and the runner `run_c12check.py`.

## Verdict

**ACCEPT WITH CONDITIONS.** Fix F01 before the closeout records are merged or quoted to the owner. Fix F02 in the same pass. P3 items can be fixed where convenient.

| Severity | Count |
| --- | ---: |
| P1 | 1 |
| P2 | 1 |
| P3 | 7 |

**What holds up:**
- A8 is legally neutral: no conclusions and no invented citations. Every anchor resolves, RM-001 is absent, and the counts reproduce.
- The owner-decision list is well formed, and D-HHOLD is shown as overridable.
- The CI workflow change is exactly what was asked.
- The gate reproduces at 32/32 with 1,058 tests.
- The C12 `--check` failure is pre-existing, as claimed. I found its root cause (F07).

**What fails:**
- The register's headline "no P1 open" leaves out the Cycle 13 B1 review, which has an open P1. The records do not mention that review at all.
- Several closures rest on author responses or merge messages alone, and the note column does not say so.

## Results I measured

| Check | Result |
| --- | --- |
| A8 + A9 tests, `python -m unittest` (venv 3.13 and bare `/usr/bin/python3.11`, no pytest) | **15/15 OK** (11 A8 + 4 A9), both interpreters |
| `build_adviser_c13.py --check` / `validate_adviser_c13.py` | CHECK OK / VALIDATION OK (schema, dedup, anchors, RM-001, reproducibility) |
| `sha256sum -c SHA256SUMS` (A8, A9) | all OK |
| Gate `gate.sh reviews/a9/wt` at `9f5bf09a` | **checks=32 exit0=32 nonzero=0; Ran 1058 tests OK (skipped=9)**; HF guard 12 OK; protected hashes OK; AUTH-LEDGER verify exit 0 |
| skipped=9 vs the author's 3 | Caused by layout, not a defect. Six A4 tests derive `SCRATCH = REPO.parent.parent`, so they skip outside a `scratchpad/c13/<ws>` worktree. With `C13A4_SCRATCH=<scratchpad>` all 14 A4 tests pass. Same result as the author |
| Cited commits in the register | Every cited 8-hex commit is an ancestor of `9f5bf09a`. CI (`fetch-depth: 0`) will resolve them, so `test_register_reproduces` will not break in CI |
| C12 restriction files | No change under `C12-CONSOLIDATION/`, `config/` or `crawler/` in the diff. `RESEARCH_RESTRICTIONS_C13.csv`: 5 rows, all NOT_LIFTED |
| RM-001 (`4284820e…`, `regs-regulations-for-the-air-force-reprinted-edition-2000`) | Appears only in the A8 tool deny-list constants. No question, anchor, brief or register row contains it, and no anchor is any Air Force Regulations doc_id |

## Findings

### F01 (P1): the Cycle 13 B1 review (1 P1, 6 P2) is silently omitted, so "No P1 open" is misleading

**Evidence:**
- `FINDINGS_REGISTER_C13.csv` has 0 B1 rows.
- `README.md` describes the register as "every finding of every Cycle 13 review (221)" and states "**Open P1:** none".
- `TASK_REGISTER_C13_FINAL.md` l.33 repeats "No P1 open". Its B1 row (l.28) says only "IN_PROGRESS (elsewhere) | Not on this branch".
- The independent B1 review (`scratchpad/c13/reviews/b1/REVIEW_B1.md`, `claude/c13-b1` at `fa72af91`) reports CHANGES REQUIRED: P1 1, P2 6, P3 6.
- Its F01 (P1) is that the held-copy **ASR-E06** path serves original bytes of ineligible documents, including the earlier edition of a just-withdrawn document. Withdrawn ids also leak through the A4/A5 surfaces, and the Windows CI job actually ran and failed.
- Meanwhile the register marks ASR-E06 CLOSED (C13-FR on `ASR-E06`, citing the importer review). That is correct for the design-level conflict, but it reads as a clean bill for a path that has an open P1 in the B1 implementation.
- None of the README, task register, risk register or owner decisions mentions the B1 review.

**Required fix:**
- Add an explicit B1 entry. Either list B1 F01–F13 in the register, or add a scoped note in the README, the task register and the summary JSON. The note should read: "B1 review `REVIEW_B1.md` at `fa72af91`: P1 1, P2 6, P3 6. B1 is still in fixes, so it is out of scope of this register and pending."
- Qualify every "No P1 open" statement as "among reviews of work integrated into staging".
- Add to the ASR-E06 row note that the B1 held-copy implementation has an open P1 (B1 F01).
- Consider a risk row for it, or point R13-20 at it.

### F02 (P2): closures with no independent confirmation are not consistently disclosed, including two P1s

**Evidence:** the README status rule says that "a few CLOSED rows rest on an author fix without a separate re-confirmation; the note column says so (A4 N-01/N-02, importer N4/N5)". The disclosure is incomplete:

- **GA4 F1 (P1), F2–F4 (P2) and F5–F9:** CLOSED on `RESULTS_C13.md` s.10, which is the author's response. `REVIEW_GA4.md` and that s.10 were committed together in `20a4e55d`. No confirmation round of the GA4 review exists. The note column is blank.
- **A0 C01 (P1):** CLOSED on the merge message `b2f163ff` ("GA0 accepted, C01 closed"). The committed confirmation `confirmation_c13_a0_06340486.md` ends with C01 open. No re-confirmation is cited, and the note is silent on this.
- **Importer N1 (P2):** CLOSED, but the committed `REVIEW_IMPORTER_E05_E06.md` s.5.2 leaves it "**N1: OPEN** (narrowed)". The note column is blank.
  - An independent third confirmation that closes N1 and N4 does exist (s.6, `6927277d..fbf4dce7`, verdict ACCEPT). But it is only in `scratchpad/c13/reviews/b-app/REVIEW_IMPORTER_E05_E06.md`. The committed copy is stale and lacks s.6.
  - The register cites the merge message `df75ae89` instead.
- **Integration X-02, X-03, X-04 (P3):** the source (§4.5) says "Open, coordinator items".
  - X-03 and X-04 are now genuinely resolved. I verified `skipUnless(sources_available())` in the A6 test, and that `RESULTS_C13.md` is in `f79160f5`.
  - X-02 is marked ACCEPTED_DEVIATION by A9 itself. The source records no coordinator disposition accepting it (the merge message still does not name `f1d61f71`).

**Required fix:**
- Add an "author response only / not independently re-confirmed" note to GA4 F1–F9, A0 C01 and X-02 (as an A9-recorded deviation awaiting coordinator sign-off).
- Either obtain a short independent confirmation of GA4 F1–F4 and A0 C01, or list them in the README status-rule sentence.
- For importer N1/N4, commit the third confirmation (s.6) to `docs/architecture/reviews/REVIEW_IMPORTER_E05_E06.md` (or a sibling file) and cite it in place of the merge message.

### F03 (P3): A6 confirmation not used, and A6 F05 status mislabelled

**Evidence:**
- The register closes A6 F01–F06 citing the A6 author README. An independent confirmation exists: `scratchpad/c13/reviews/a6/confirmation_c13_a6_839c33e3.md` plus `_findings.csv`.
- That confirmation records F01–F04 and F06 as FIXED, but **F05 as NOTED_ACCEPTED** with an optional later action. Under A9's own rule that is ACCEPTED_DEVIATION, not CLOSED.
- The confirmation is not committed. The same is true of `reviews/a7/confirmation_security_4aa8edf4.md`, though that one is covered by the PR #51 merge.

**Required fix:**
- Commit the A6 confirmation (and, optionally, the A7 security confirmation) into the workstream `reviews/` folders and cite them.
- Re-label A6 F05 as ACCEPTED_DEVIATION.

### F04 (P3): A7 `DISPOSITIONS_C13.md` drops requested actions and omits F15

**Evidence:**
- **F15 (INFO):** absent from the table, although the register lists it.
- **F09:** the review asks to "record the official sha256 as pins … never use archive.org derivative files as byte pins … refer the Navy Act subject to A3". The disposition says only "Accepted as benign", so none of the three actions is dispositioned.
- **F10:** the review asks to extend the marking scanner to all pages and to OCR'd image pages. The disposition says "Recorded" with no deferral. The register correctly calls it DEFERRED.
- **F11:** the review asks to record the change "in the HF commit record". The disposition is the only record; `HF_COMMITS_C13.csv` and `HF_VERIFY_C13.csv` are unchanged.

Everything else checks out. F01 and F02 are verified in staging: `NEVER_CONTACT` is in `crawler/config.py:49` and is subdomain-matched by `is_blocked_host`, there is a test at `tests/test_crawler_security.py:99`, and PR #51 merge `9ed152af` is an ancestor of `f79160f5`. The F04 retroactive acceptance is within the options the review offered. The PR recommendations are correctly labelled as recommendations only.

**Required fix:** add F15. For F09, F10 and F11, state either the action or an explicit deferral with an owner. Mark F09's "official sha256 as pins" as a precondition for any pin list.

### F05 (P3): A8 stores 13 anchors' paths as ephemeral scratchpad paths although a durable HF path exists

**Evidence:**
- A8-Q153 to A8-Q165 (the A1 `ALREADY_INGESTED_C12` items) carry `stored_path` values such as `/tmp/claude-0/…/scratchpad/c12_acquired/1a/1aa3838f…/2012_9_1001_1006_EN.pdf`, with `stored_path_register=C12_ACQUISITION_MANIFEST`.
- The files exist today, so the validator passes. But they will not survive a scratchpad cleanup.
- The same shas are in `C12-CONSOLIDATION/copy_verification_c12/HF_INGESTED_REDOWNLOAD_C12.csv` at HF revision `15bd03cc`. For example, `data/raw/sci/2012/1aa3838f….pdf` is listed there with a matching sha256.
- `a8_registers.py` does not index that register.

**Required fix:** add `HF_INGESTED_REDOWNLOAD_C12` as a stored-path register, ranked ahead of `C12_ACQUISITION_MANIFEST`, and rebuild. Alternatively, have the validator reject absolute `/tmp` stored paths.

### F06 (P3): A8-Q143 drops the "as OCR" qualifier from its source

**Evidence:**
- A8-Q143 states: "The 1954 Gazette heading of Appendix IV Part I Forms 1 and 2 prints 'sections 83-84 Army Act'".
- The A6 register (`FORM_REGISTER_C13.csv`) records "AR54-GAZ p.75 (heading 'sections 83-84 Army Act' **as OCR**)" with `NOT_DETERMINED`.
- The question turns an OCR reading into a statement of what the Gazette prints. This is not a legal conclusion, but it overstates the evidence.
- The other A6, A5 and A1 phrasings I checked (Q140–Q152 and a sample of Q153–Q204) faithfully restate their sources.

**Required fix:** reword Q143 to read "reads, as OCR, 'sections 83-84'", then rebuild and refresh the hashes.

### F07 (P3): the C12 `build_adviser_package.py --check` failure is pre-existing (confirmed), but its root cause is not recorded

**Evidence:**
- **Confirmed pre-existing:** in scratchpad-level worktrees at `a4c0c382`, `f79160f5` and `9f5bf09a`, the tool reports `CHECK FAILED: PROVENANCE_C12.md, SHA256SUMS`, identically in all three.
- In the `reviews/a9/wt*` worktrees it fails earlier, with `FileNotFoundError` for `SCRATCH/c12/reviews/fable_review_pr46_c69eee41.md`. That is a layout dependency.
- **Root cause:** `write_provenance()` embeds the absolute path of the worktree it runs from (`C12W = AW.parent.parent`) in 17 lines of `PROVENANCE_C12.md`. The committed file names `…/scratchpad/c12w`.
  - After substituting `scratchpad/<worktree>` with `scratchpad/c12w`, the regenerated `PROVENANCE_C12.md` is **byte-identical** to the committed file at all three commits.
  - `SHA256SUMS` differs only on the PROVENANCE line.
  - So the content reproduces. The check fails only because it is run from a path other than the original `scratchpad/c12w`, which is now checked out at an unrelated commit, `44c462f0`.
- **Is a minimal fix in scope?** No. Any fix means changing the frozen C12 tool to emit repo-relative paths (which also changes the frozen `PROVENANCE_C12.md` bytes), or adding a path-normalising comparison to the tool. Neither belongs in a records-only closeout.
- A9's `RISK_REGISTER_C13` R13-18 ("investigate in Cycle 14") is acceptable, but it lacks the diagnosis.

**Required fix:**
- Record the root cause and the path-normalised identity in the A9 README and in R13-18.
- Give the re-run recipe: run from a worktree at `scratchpad/c12w`, or compare after normalising the path. Example: `reviews/a9/run_c12check.py` with `sed 's#scratchpad/<wt>#scratchpad/c12w#'`.
- Do not edit the frozen tool or package in C13.

### F08 (P3): counts quoted outside the README mix two denominators

**Evidence:**
- The claim relayed for review was "226 rows (182 CLOSED, 24 DEFERRED, 8 OPEN, 7 ACCEPTED_DEVIATION)". Those figures add up to 221.
- The committed records are internally consistent: README table, summary JSON and task register l.33 all give 221 Cycle 13 findings with 24 DEFERRED, plus 5 C12 carry-overs, for 226 rows with 29 DEFERRED.

**Required fix:** none in the files. When the closeout is reported to the owner, quote either "221 + 5 = 226; DEFERRED 24 + 5 = 29" or the README table.

### F09 (P3): GATE record does not state the worktree-layout dependency

**Evidence:**
- `GATE_C13_CLOSEOUT.md` reports skipped=3, and it gated `ccf9805d`, not the head `9f5bf09a`, which adds only records.
- Gated from any worktree that is not at `scratchpad/c13/<ws>`, the same commit gives skipped=9 (see "Results I measured").

**Required fix:** add one line saying the skip count depends on worktree layout (the A4 `SCRATCH` derivation). Optionally, re-gate `9f5bf09a` itself.

## Sample of findings checked (about 60 rows, every source file)

| Source | Rows checked | Result |
| --- | --- | --- |
| A0 review CSV and confirmation | F01–F16, C01 | IDs and severities match; C01 closure is by merge message only (F02) |
| `C13-EVAL/reviews/REVIEW_A1.md` | A1-01…A1-12 | All CLOSED in confirmation round 2 (`5bd0e3d5`, `cc190fde`); matches |
| `REVIEW_A2_A3_A5_INTEGRATION.md` | A5-01/02, A2-01…06, A3-01/02/04, A5-03, X-01…04, N1–N4 | Matches §4.5 except X-02/03/04 (F02; X-03 and X-04 verified as now resolved); X-01's dependence on D-HHOLD is noted |
| `C13-EVAL/REVIEW_GA4.md` | F1–F10 | Present; closures rest on the author's s.10 response (F02) |
| A4 review and confirmation CSVs | R-01…R-13, N-01…N-03 | R-01…R-08 and R-10 CLOSED_VERIFIED in the confirmation; N-01/N-02 author fix, disclosed |
| A5 findings CSV | F01–F09 | Present; severities match; F07 ACCEPTED_DEVIATION (ERRATA wording) is reasonable |
| A6 review CSV | F01–F10 | Present; F07 OPEN is correct; F05 mislabelled (F03) |
| A7 review CSV and dispositions | F01–F16 | Present; statuses follow the dispositions (gaps in the dispositions: F04) |
| GOV review CSV and confirmation | F01–F12, I01–I04 | F01–F03 CLOSED in the confirmation; F04–F11 "still open", which the register re-labels as DEFERRED to C14 (acceptable, with the reason given); F12 OPEN |
| B0 review, confirmation 1 and 2 | F01–F26, C01–C09 | F02 partial in confirmation 1 and closed in confirmation 2; C01–C09 closed; F21 OPEN (OD-14); matches |
| `REVIEW_IMPORTER_E05_E06.md` | E1–E10, N1–N5 | N1 OPEN in the committed file (F02); N4 and N5 disclosed |
| `REVIEW_PR53_RECONCILIATION.md` | F01–F10, C1–C5 | All CLOSED (s.5.2; C1–C5 in the importer review s.1); matches |
| c13-assurance README | R2-N01, ASR-E01…E06 | Matches s.5 (B1 caveat on ASR-E06: F01). The other assurance files contain no severity-rated findings (their P1/P2 labels are ADR phases) |
| `REVIEW_R2N01_POC.md` §10.5/10.6 | F01–F14, N1–N5 | Matches; F14 PARTIAL becomes ACCEPTED_DEVIATION, consistent with §10.8's "recorded exception" |

No finding in any listed review file is missing from the register. The register omits only B1, which is not on this branch (F01).

## A8 legal neutrality (check 2)

- **No legal conclusions.**
  - C12 and A4 questions are carried verbatim, per the README; I spot-checked Q001, Q002 and Q034.
  - The A8-phrased questions (A6 Q140–Q150, A5 Q151–Q152, A1 Q153–Q204) are framed as questions and attribute every factual premise to the originating artefact.
  - Q146's mention of BNS replacing the IPC is attributed to A6.
- **No invented citations.** Every provision, S.R.O., page and form designation I checked appears in the A6 register or the C12/A4 packets. The exception is the qualifier dropped in Q143 (F06).
- **20 anchors spot-checked** (seeded random sample, seed 1309):
  - 15 resolved to the blob at `ad77758d:data/raw/...` in `/home/user/c7`, with sha256 equal to the anchor and `data/meta/<doc_id>.json` binding the same sha.
  - In every case where the page was a number, it was within the PDF page count.
  - Q158 resolved to a scratch file whose sha matched; that file is durable on HF at `15bd03cc` (F05).
  - The 4 C5 anchors (`C5-SRC-P0-ARMY-RULES-1954`, `C5-SRC-J-SC-2020-VIRENDRA`) are bound by AUTH-LEDGER v0 and COPY_VERIFICATION_C12, with the sha present in the C12 HF hash ledger.
  - 0 mismatches.
- **Priorities are reasonable.**
  - P0 is r.23(3) only.
  - The 34 P1 cover the named acceptance-check supersession cases: field punishment 1992, IPC→BNS, Parashotam/Shri Kant Sharma, Dharamvir/2008 Rules. They also cover commencement, the operative text of court-martial and court-of-inquiry rules, the Entitlement Rules 2008 version, IAFD-905/AR 4(1), and approval roles.
  - P2 holds evidence promotions, relevance-scope and documentary items.
  - The raised C12 items are listed, and nothing was lowered except C12 P3→P2.
- **RM-001 absent:** see Results.

## Owner decisions (check 3)

- All 20 entries give the source, options and a recommendation, and the header says nothing has been acted on.
- No decision is presented as already taken. OD-06 "Decline for now" and OD-10 "As A7 recommends" are worded as recommendations.
- **D-HHOLD** appears as OD-11, with an "override and reuse H-HOLD (X-01 reopens)" option. The register's X-01 note repeats the reopen condition. This is compliant.
- The B1 review should feed OD-15 (ADR-0005/GB1) and OD-17 (X7 withdrawal durability) once F01 is addressed. This is advisory only.

## Workflow change (check 6)

The only workflow diff is `.github/workflows/crawler-security-ci.yml`:
- It adds a `push:` trigger on `legal-knowledge/v2.5-staging`, with a path filter identical to `pull_request`.
- It changes `pip install -r requirements.txt pytest` to `… pytest==9.2.0`, which matches `requirements.txt:40`.

Nothing else changed: jobs, permissions, the Python version and the guard steps are all unchanged, and no other workflow file is touched.

Observation, not a finding: `requirements.txt` is not in either path filter, so a dependency bump alone will not trigger the job. That was already true before the change.
