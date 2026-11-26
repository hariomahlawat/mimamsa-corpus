# C13-A9: deferred findings and register closeout

**Records only.** No frozen record, protected hash, AUTH-LEDGER entry (v0), extractor, Cycle 12 register or capability
restriction was changed. The only non-record change is the cheap P3 fix A7 review F14 (CI). Nothing here is legally
reviewed. Restricted material RM-001 is referred to by its restriction id only. Independent review is still required.

## Files

| File | Content |
| --- | --- |
| `FINDINGS_REGISTER_C13.csv` | 261 rows: every finding of every Cycle 13 review (256, including the B1 review and the independent review of this closeout) plus the 5 Cycle 12 deferred P2s, each with source review, severity, status, **verification** and evidence (commit or file) |
| `FINDINGS_SUMMARY_C13.json` | Counts by status, severity and verification; staging-integrated, B1 and A8/A9 sub-counts; open P1/P2 and CLOSED_UNCONFIRMED P1 lists |
| `RESEARCH_RESTRICTIONS_C13.csv` | The five C12 research-use restrictions, Cycle 13 evidence and decision: **none lifted** |
| `TASK_REGISTER_C13_FINAL.md` | Final status of A0-A9, GOV, B0, B-PoC and B1 (IN_PROGRESS), with evidence |
| `RISK_REGISTER_C13.md` | 22 risks (open C12 risks carried, Cycle 13 risks added) |
| `OWNER_DECISIONS_C13.md` | 22 decisions waiting on the owner, with options and a recommendation |
| `reviews/` | Evidence copies of independent confirmations that were only in the coordinator scratchpad (A0 confirmation 2, A5 confirmation of `d09b7d91`, A6 confirmation `839c33e3`, A7 security confirmation `4aa8edf4`) and the independent review of this closeout (`REVIEW_A8_A9.md`) |
| `tools/build_findings_c13.py` | Builds the register, summary and restriction files (`--check` reproduces byte for byte; verifies every finding id against its review file, CSV severities, cited commits and cited files, and the status/verification rule) |
| `../../../tests/test_legal_audit_c13_a9_closeout.py` | unittest suite (4 tests) |

Also added outside this folder: `docs/architecture/b1/reviews/REVIEW_B1.md` (the B1 review with its confirmation; the
coordinator places the same file there when B1 merges) and
`docs/architecture/reviews/REVIEW_IMPORTER_E05_E06_confirmation3.md` (the importer review's third confirmation).

## Findings register (measured)

Review files read: every file under each `C13-*/reviews/` folder, `docs/architecture/reviews/` (including
`c13-assurance/`), `docs/architecture/poc/reviews/`, `C13-EVAL/reviews/`, `C13-EVAL/REVIEW_GA4.md`, the B1 review
(`docs/architecture/b1/reviews/REVIEW_B1.md`, review at `fa72af91`, confirmations at `4fbe7c79` and `f71957e5`; B1 is
ACCEPTED as the prototype baseline and not yet in staging), the confirmations copied into `reviews/`, and the review of this closeout. A2 and A3 have no `reviews/`
folder; their findings are in the C13-EVAL reviews. B0 confirmation 2 records R1 as "informational, not a finding"; it
is not listed.

| Status | Cycle 13 review findings | C12 carry-overs | All |
| --- | ---: | ---: | ---: |
| CLOSED | 181 | 0 | 181 |
| CLOSED_UNCONFIRMED | 25 | 0 | 25 |
| DEFERRED | 30 | 5 | 35 |
| OPEN | 12 | 0 | 12 |
| ACCEPTED_DEVIATION | 8 | 0 | 8 |
| **Total** | **256** | **5** | **261** |

Of the 256: reviews of work integrated into staging 227 (CLOSED 158, CLOSED_UNCONFIRMED 24, DEFERRED 29, OPEN 8,
ACCEPTED_DEVIATION 8); B1 19 (CLOSED 14, OPEN 4, DEFERRED 1); the A8/A9 review 10 (CLOSED 9, CLOSED_UNCONFIRMED 1).

| Verification | Rows |
| --- | ---: |
| INDEPENDENT_CONFIRMED (an independent reviewer's record states the status) | 218 |
| COORDINATOR_SPOTCHECK (coordinator disposition or spot-check) | 13 |
| AUTHOR_ONLY (author's or A9's own record) | 30 |

- **Open P1:** none, in any review including B1 (B1 F01 closed at `4fbe7c79`) and the A8/A9 review (F01 closed in its
  confirmation at `f7dae727`).
- **P1 CLOSED_UNCONFIRMED (1):** GA4 F1 (applied by the evaluator, recorded in `REVIEW_FIXES.json`; no reviewer
  re-confirmation).
- **Open P2 (3):** A7 F06 (20 unprobed redirect hosts), assurance R2-N01 and B-PoC F07 (both the selected Windows host).
  B1 F14, F15 and F16 are CLOSED in the B1 second confirmation at `f71957e5`.
- **Other open (9):** A6 F07 (INFO; human spot-check before the legal gate), GOV F12 (P3; restricted scratch derivative
  outside the repository), B0 F21 (P3; owner decision D-08), assurance ASR-E03 and ASR-E04 (unrated evidence gaps), B1
  F10 (twin-withdrawal policy, owner decision OD-21), B1 F17-F19 (P3 residuals: stale wording; "AA s.69" not recognised;
  no lexical fallback for ambiguous-only queries).
- **Status rule.** CLOSED needs an independent confirmation or a coordinator spot-check on record; an author fix
  without one is CLOSED_UNCONFIRMED (GA4 F1-F9, A4 N-01/N-02, B0 F13-F26 except F21 (accepted as dispositioned, not
  re-verified), and A8/A9 confirmation finding C-F01). DEFERRED = carried to a
  later cycle or gate with the reason. ACCEPTED_DEVIATION = accepted as is by a recorded disposition; X-02 is an
  A9-recorded deviation awaiting coordinator sign-off (AUTHOR_ONLY). The build enforces the rule.

### Cycle 12 deferred P2s in Cycle 13

| Finding | C13 work | C13 status | Restriction |
| --- | --- | --- | --- |
| C11 F05 (outcome extent rule) | A2 Outcome V4 | DEFERRED: blind H-OUT-C13 NOT_MET on all four targets | still restricted |
| C11 F08 (post-quote operative sentences) | A2 Outcome V4 | DEFERRED: same blind result | still restricted |
| C11 F06 (holdings precision) | A3 holdings redesign | DEFERRED: H-HOLD not scorable; descriptive precision 0.365 | still restricted |
| C11 F07 (origin labels) | A3 | DEFERRED: no independent origin-label precision measured | still restricted |
| WS-G R04 (form field lists) | A6 | DEFERRED: 21 of 22 families recommended CLOSED_VERIFIED (fidelity only); IAFD-905 still deferred; legal gate not met | still restricted |

**Research-use restrictions.** None can be lifted: no target was met under blind evaluation, every reference set was
AI-coded, and no legal adviser has signed anything off. `C12-CONSOLIDATION/CAPABILITY_RESTRICTIONS.csv` is unchanged and
`tests/test_legal_audit_c12_research_isolation.py` still passes.

## Cheap P3 fixes (A7 F12, F14, F16)

- **F14: done** (`2185a2c8`). `.github/workflows/crawler-security-ci.yml` now also runs on push to
  `legal-knowledge/v2.5-staging` (same path filter) and installs `pytest==9.2.0` (the version pinned in
  `requirements.txt`).
- **F12: deferred** as instructed. The 11 legacy `scripts/*.py` are not retired.
- **F16: deferred.** Logging a `from_header_sent` flag means changing the A7 acquisition tool, which is outside a
  records-only closeout.

## Register regeneration (Cycle 12 `--check` tools)

| Tool | Result on this branch |
| --- | --- |
| `C12-CONSOLIDATION/findings_consolidation/tools/consolidate_findings_c12.py --check` | CHECK OK: 648 rows reproduce byte-identically |
| `C12-CONSOLIDATION/tools/scnum_overlay_c12.py --check` | overlay reproduces |
| `C12-CONSOLIDATION/adviser_package/tools/build_adviser_package.py --check` | CHECK FAILED: PROVENANCE_C12.md, SHA256SUMS. **Pre-existing, DEFERRED**: it fails identically at C12 closeout `a4c0c382` and at this branch's base `daba057b`. **Root cause** (independent review F07): `write_provenance()` embeds the absolute path of the worktree it runs from (`C12W = AW.parent.parent`) in 17 lines of PROVENANCE_C12.md, and the committed file names `scratchpad/c12w`. After replacing `scratchpad/<worktree>` with `scratchpad/c12w`, the regenerated file is byte-identical, and SHA256SUMS differs only on the PROVENANCE line. Re-run recipe: run from a worktree at `scratchpad/c12w`, or compare after `sed 's#scratchpad/<wt>#scratchpad/c12w#'`. The frozen C12 tool and package were not edited (R13-18) |

The C13 tools added here (`C13-A8-ADVISER/tools/build_adviser_c13.py --check`, `tools/build_findings_c13.py --check`)
pass. The register depends on the commit ids cited as evidence; if the branch is rebased or squashed, the cited
commits must be updated before `--check` passes again.

## Review response (`reviews/REVIEW_A8_A9.md`: ACCEPT WITH CONDITIONS, then **ACCEPT** in the confirmation at `f7dae727`)

Confirmation finding C-F01 (P3, B0 F13-F26 labelled too generously) is fixed: those rows are now CLOSED_UNCONFIRMED /
AUTHOR_ONLY.

| Finding | Response |
| --- | --- |
| F01 (P1) B1 review omitted | B1 F01-F16 added from the confirmation (F01-F09, F12-F13 CLOSED; F05 for the reported cases; F06 display mitigation with the upstream gap DEFERRED to Track A; F10 OPEN, owner; F11 DEFERRED; F14 P2 OPEN; F15, F16 OPEN). ASR-E06 row now notes B1 F01 and its closure. "No P1 open" is restated from the recomputed counts. Risks R13-21/22 and owner decisions OD-21/22 added |
| F02 (P2) unconfirmed closures | `verification` column added; CLOSED_UNCONFIRMED status for author-only fixes. A0 C01 now cites the reviewer's confirmation 2; importer N1/N4 cite the committed third confirmation; GA4 F1-F9 are CLOSED_UNCONFIRMED; X-02 marked AUTHOR_ONLY; X-03/X-04 cite this review's verification |
| F03 (P3) | A6 confirmation committed in `reviews/`; A6 F05 is ACCEPTED_DEVIATION. A5 confirmation also committed (A5 F07 now CLOSED, errata E2; new P3 notes N1-N3 added) and A0 confirmation 2 (new P3s L01-L03 added) |
| F04 (P3) | A7 F15 recorded; F09, F10, F11 actions recorded as DEFERRED with an owner (coordinator) in the register notes; `DISPOSITIONS_C13.md` (coordinator record) not edited |
| F05 (P3) | A8 stored paths now durable (HF re-download record, A1 recovery population); validator rejects absolute paths |
| F06 (P3) | A8-Q143 now says "reads, as OCR" |
| F07 (P3) | Root cause recorded below and in R13-18 (DEFERRED) |
| F08 (P3) | No file change; quote counts as "256 + 5 = 261; DEFERRED 30 + 5 = 35" |
| F09 (P3) | Layout dependency noted in `GATE_C13_CLOSEOUT.md` |

## Integration gate

See `GATE_C13_CLOSEOUT.md`.

## Reproduce

```
PY=scratchpad/venv/bin/python
$PY -I -B legal_knowledge/audit_work/C13-A9-CLOSEOUT/tools/build_findings_c13.py --check
$PY -B -m unittest tests.test_legal_audit_c13_a9_closeout
cd legal_knowledge/audit_work/C13-A9-CLOSEOUT && sha256sum -c SHA256SUMS
```
