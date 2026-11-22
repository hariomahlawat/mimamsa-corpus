# Reviewer provenance and CI coverage report (WS-D, issue #14)

Engineering/QA only. CI passing proves structure and traceability, **never** legal correctness, authenticity or currency. No agent can reach a state beyond "technical review completed" (charter rule 5).

## 1. Reviewer identity bindings

Binding mechanism: `<batch>/reviewer_identities.json`, enforced by `validate.py identity_checks` (and, from WS-D, `integrity_checks`). Sources and findings are bound to a reviewer by ID prefix. Where `require_exact_retrieved_by` is true, `retrieved_by` must also equal the reviewer ID.

### PILOT-01 (frozen; `require_exact_retrieved_by: false` at batch level)
| Reviewer | Stage | Exact `retrieved_by` | Sources (prefix) | `retrieved_by` on those sources | Findings | Reviews (decisions) |
| --- | --- | --- | --- | --- | --- | --- |
| independent-reviewer-blind | blind | no | 16 (`S-BLIND-`) | `independent-reviewer` (16) | 15 (`F-BLIND-`) | 0 |
| independent-reviewer-A | adversarial | no | 31 (`S-REVA-`) | `independent-reviewer` (31) | 0 | 21 (SUPPORTS 18, DISPUTES 2, RETURN_FOR_EVIDENCE 1) |
| independent-reviewer-B | adversarial | no | 13 (`S-REVB-`) | `independent-reviewer` (13) | 0 | 12 (SUPPORTS 8, DISPUTES 4) |
| independent-reviewer-C | adversarial | **yes** | 7 (`S-REVC-`) | `independent-reviewer-C` (7) | 0 | 2 (SUPPORTS 2) |

- First-pass agents: manual-of-military-law-auditor, statutory-auditor, judgment-auditor, procedure-auditor, cross-volume-auditor, orchestrator. Sources by first-pass agent: MML 79, statutory 29, procedure 16, judgment 12, cross-volume 9, orchestrator 4.
- **Weakness (documented, not a failure):** 60 of 67 reviewer sources carry the generic `retrieved_by = "independent-reviewer"`. Only the ID prefix distinguishes reviewers blind/A/B. A, B and blind cannot be told apart from `retrieved_by` alone. Reviewer C, and every R23-VERIFY-01 source, use exact IDs. Future batches should set `require_exact_retrieved_by: true` (already the R23 practice).
- Independent review reached 32/36 P0/P1 findings. The 4 without a review (F-BLIND-001, -004, -006, -010) are the blind reviewer's own findings, which are themselves the independent stage.
- All 35 reviews carry `reviewed_original_sha256`, equal to the finding's frozen record hash (checked by the new always-on rule). No review is `blind: true`; the blind stage is expressed as findings, not reviews.

### R23-VERIFY-01 (frozen; `require_exact_retrieved_by: true`)
| Reviewer | Stage | Sources | `retrieved_by` | Findings | Reviews |
| --- | --- | --- | --- | --- | --- |
| independent-reviewer-D | blind | 10 (`S-REVD-`) | `independent-reviewer-D` (10) | 2 (`F-REVD-`) | 0 |

The orchestrator wrote 3 sources and 2 findings. All 4 findings are CONFLICTING / CONFLICTING_SOURCES, require legal review, and are `QUEUED_ADVISOR_NOT_NOMINATED`.

### Human legal roles
- No batch contains any LEGAL_ADVISOR, PROJECT_DIRECTOR or FORMAL_AUTHORITY review. No finding is ADVISOR_REVIEWED, ACCEPTED_FOR_CANDIDATE or CURRENT_IN_FORCE (asserted by `test_no_existing_batch_claims_human_review_or_current_law`).
- From WS-D, always-on: an agent identity (any first-pass agent, any declared reviewer, or an ID matching `-auditor`, `orchestrator`, `independent-reviewer`, `agent`, `claude`, `ws-*`) can never hold a human role, whatever the strictness.
- Controls v2 (opt-in): human reviewers must be declared under `human_reviewers` with role and `binding_evidence`, and acceptance or approval needs an `approval_artifact`. No human reviewer is nominated yet (OQ-D-007).

## 2. CI workflow `.github/workflows/legal-audit-kit-ci.yml` (job `audit-kit-tests`, Python 3.11, stdlib only)
| # | Step | What it guards | Added by |
| --- | --- | --- | --- |
| 1 | Validate audit schemas | schema files readable; `additionalProperties: false`; required ⊆ properties | kit |
| 2 | `unittest discover tests/test_legal_audit_*.py` | **113 tests** (54 at WS-D start): authority 14, controls 30, validator 4, code inventory 6, citation register 8, integrity controls 31, register semantics 8, WS-D artifacts 12 | kit + WS-D |
| 3 | PILOT-01 strict validation (frozen manifest, reviewer identities) | 216 sources, 126 findings, 35 reviews; 0 errors | kit |
| 4 | R23-VERIFY-01 strict validation (policy v1) | 13 sources, 4 findings; 0 errors | kit |
| 5 | `build_code_inventory.py` | every one of the 87 codes registered | PILOT-01 |
| 6 | `tools/legal_audit/check_csv.py` | all 44 `audit_work/**/*.csv` are UTF-8 with no BOM, have unique non-blank headers, have no ragged rows, and parse strictly | **WS-D** |
| 7 | `ARMY-RULES-CHAIN-01/check_registers.py` | instrument, chronology and ACQ-02 cross-references and PIC IDs; r.23(3) CONFLICTING, r.193 OPEN, r.194 PROPOSAL; after integration of PR #16, also effective-date semantics, continuation pages and C-08/C-09 | **WS-D** (path reference only) |
| 8 | `WS-D-QUALITY/scripts/hash_reproduction.py` | frozen KB and cases files plus 45 per-record manifest hashes (PILOT-01 43, R23 2); MML manifest SHA | **WS-D** |
| 9 | `WS-D-QUALITY/scripts/relation_graph.py --no-write` | no dangling KB/case/code/source/finding/review/PIC edge; no ID collisions | **WS-D** |
| 10 | `sha256sum -c` on the two originals | frozen 658/53 bytes unchanged | kit |

### What CI does not cover
- Legal correctness, currency, amendment completeness or authenticity of anything.
- The private MML originals: checked locally only (8/8 match, `hash_reproduction.json`). CI cannot see the bytes, by design.
- Crawler-corpus measures (`coverage_scorecard`, register targets as doc_ids). CI checkouts lack `origin/raw-data`, so those are NOT_CHECKED in CI and computed locally.
- The non-audit `tests/` crawler suite (needs third-party packages).
- Frozen-batch migration to the owner date rule or controls v2. Both are deliberately not applied (OQ-D-006).

### Historical validation records are now stale (expected)
`PILOT-01/validation_result_current.json` records validator SHA `e5530ebf…` and finding-schema SHA `95fc4132…`. At WS-D start (commit 2a7ae7af) the validator was already `d57b5136…` and the finding schema `717c3328…`, so the record was stale before WS-D. After WS-D: validator `2645f66f…`, source schema `f56c4f36…` (additive fields only), review schema unchanged `1a30635d…`. PILOT-01 is frozen, so a fresh validation record should be a new file written by the coordinator (OQ-D-014).

## 3. Reproduction commands
```bash
python3 -m unittest discover -s tests -p 'test_legal_audit_*.py'
python3 tools/legal_audit/validate.py --schema-check
python3 tools/legal_audit/validate.py --batch legal_knowledge/audit_work/PILOT-01 --manifest legal_knowledge/audit_work/PILOT-01/pilot-manifest.json --strict
python3 tools/legal_audit/validate.py --batch legal_knowledge/audit_work/R23-VERIFY-01 --manifest legal_knowledge/audit_work/R23-VERIFY-01/pilot-manifest.json --strict
python3 tools/legal_audit/check_csv.py
python3 legal_knowledge/audit_work/ARMY-RULES-CHAIN-01/check_registers.py
python3 legal_knowledge/audit_work/WS-D-QUALITY/scripts/hash_reproduction.py [--mml-dir DIR --mml-zip FILE]
python3 legal_knowledge/audit_work/WS-D-QUALITY/scripts/relation_graph.py [--corpus-ref origin/raw-data]
python3 legal_knowledge/audit_work/WS-D-QUALITY/scripts/coverage_scorecard.py [--corpus-ref origin/raw-data]
```
