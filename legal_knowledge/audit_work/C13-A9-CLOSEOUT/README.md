# C13-A9: deferred findings and register closeout

**Records only.** No frozen record, protected hash, AUTH-LEDGER entry (v0), extractor, Cycle 12 register or capability
restriction was changed. The only non-record change is the cheap P3 fix A7 review F14 (CI). Nothing here is legally
reviewed. Restricted material RM-001 is referred to by its restriction id only. Independent review is still required.

## Files

| File | Content |
| --- | --- |
| `FINDINGS_REGISTER_C13.csv` | 226 rows: every finding of every Cycle 13 review (221) plus the 5 Cycle 12 deferred P2s, each with source review, severity, status and evidence (commit or file) |
| `FINDINGS_SUMMARY_C13.json` | Counts by status and severity, open P1/P2 lists, the review files read |
| `RESEARCH_RESTRICTIONS_C13.csv` | The five C12 research-use restrictions, Cycle 13 evidence and decision: **none lifted** |
| `TASK_REGISTER_C13_FINAL.md` | Final status of A0-A9, GOV, B0, B-PoC and B1 (IN_PROGRESS), with evidence |
| `RISK_REGISTER_C13.md` | 20 risks (open C12 risks carried, Cycle 13 risks added) |
| `OWNER_DECISIONS_C13.md` | 20 decisions waiting on the owner, with options and a recommendation |
| `tools/build_findings_c13.py` | Builds the register, summary and restriction files (`--check` reproduces byte for byte; verifies every finding id against its review file, CSV severities, cited commits and cited files) |
| `../../../tests/test_legal_audit_c13_a9_closeout.py` | unittest suite (4 tests) |

## Findings register (measured)

Review files read: every file under each `C13-*/reviews/` folder, `docs/architecture/reviews/` (including
`c13-assurance/`), `docs/architecture/poc/reviews/`, `C13-EVAL/reviews/`, and `C13-EVAL/REVIEW_GA4.md` (the GA4
evaluation review, which sits at the C13-EVAL root). A2 and A3 have no `reviews/` folder; their findings are in the
C13-EVAL reviews. Confirmation round 2 of B0 records R1 as "informational, not a finding"; it is not listed.

| Status | Cycle 13 review findings | C12 carry-overs | All |
| --- | ---: | ---: | ---: |
| CLOSED | 182 | 0 | 182 |
| DEFERRED | 24 | 5 | 29 |
| OPEN | 8 | 0 | 8 |
| ACCEPTED_DEVIATION | 7 | 0 | 7 |
| **Total** | **221** | **5** | **226** |

- **Open P1:** none.
- **Open P2 (3):** A7 F06 (20 unprobed redirect hosts), assurance R2-N01 and B-PoC F07 (both the selected Windows host).
- **Other open (5):** A6 F07 (INFO; human spot-check before the legal gate), GOV F12 (P3; restricted scratch
  derivative outside the repository), B0 F21 (P3; owner decision D-08), assurance ASR-E03 and ASR-E04 (unrated
  evidence gaps: restore under custody; blind performance).
- **Status rule.** CLOSED = fixed and confirmed by an independent review or a recorded merge, or informational with no
  action. A few CLOSED rows rest on an author fix without a separate re-confirmation; the `note` column says so
  (A4 N-01/N-02, importer N4/N5). DEFERRED = carried to a later cycle or gate with the reason. ACCEPTED_DEVIATION = a
  recorded disposition accepts it as is.

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
| `C12-CONSOLIDATION/adviser_package/tools/build_adviser_package.py --check` | CHECK FAILED: PROVENANCE_C12.md, SHA256SUMS. **Pre-existing**: it fails identically at C12 closeout `a4c0c382` and at this branch's base `daba057b` (run in a scratchpad-level worktree, the layout the tool expects). Not caused by A9; the frozen C12 package was not edited (RISK_REGISTER_C13 R13-18) |

The C13 tools added here (`C13-A8-ADVISER/tools/build_adviser_c13.py --check`, `tools/build_findings_c13.py --check`)
pass. The register depends on the commit ids cited as evidence; if the branch is rebased or squashed, the cited
commits must be updated before `--check` passes again.

## Integration gate

See `GATE_C13_CLOSEOUT.md`.

## Reproduce

```
PY=scratchpad/venv/bin/python
$PY -I -B legal_knowledge/audit_work/C13-A9-CLOSEOUT/tools/build_findings_c13.py --check
$PY -B -m unittest tests.test_legal_audit_c13_a9_closeout
cd legal_knowledge/audit_work/C13-A9-CLOSEOUT && sha256sum -c SHA256SUMS
```
