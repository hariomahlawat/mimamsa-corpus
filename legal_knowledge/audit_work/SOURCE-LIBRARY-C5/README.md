# SOURCE-LIBRARY-C5: authoritative source acquisition and verification (Cycle 5)

**DATABASE ONLY.** Nothing was downloaded, crawled, uploaded, merged or promoted. Discovery used HTML listing pages, metadata APIs and HTTP HEAD only, and every request is logged.

The rules that bound this cycle:
- The original 658 KB records and 53 case records are unchanged (hashes are checked by the validator).
- No legal status, reserved item or Cycle 4 result was changed.
- Technical validation is **not** legal approval.

- Baseline: staging `151f93588495639d1d0694bc9bfdf70ab9474a29`, frozen in `baseline/frozen_baseline_manifest.json`.
- Policy: `docs/legal-audit/SOURCE_AUTHORITY_POLICY.md` v1. Legal authority and copy provenance are recorded separately, and a hash proves bytes, not law.

## Layout
| Path | Content |
| --- | --- |
| `baseline/` | frozen manifest (original hashes, open PRs), `held_binaries_manifest.csv` (93 held binary paths, 67 unique files, all re-hashed MATCH, with page count and text-layer class), `existing_register_index.csv` (147 earlier CSV registers with sha256) |
| `discovery/` | brief, candidates (`A_` DSR/regulations, `B_` pension/service, `C_` statutes/Gazette: 86 rows) and request logs (`*_requests.tsv`) |
| `inputs/` | hand-authored, evidence-referenced inputs: target publications, acquisition batches, corpus/case source maps, C5 conflict and amendment additions, C5 page-image checks (`page_image_checks_c5.csv`, renders in `reports/evidence/`) |
| `registers/` | **built** registers (do not edit): source master (D1), acquisition (D3), amendment + provision chain (D4), provision register, source conflicts, corpus crosswalk + coverage summary (D6) |
| `schemas/c5_registers.schema.json` | column contracts and controlled values; which existing schema each register reuses |
| `reports/` | D1–D8 |
| `review/` | independent reviewer output, verbatim (`review_findings.csv`, `review_log.md`) |
| `tools/` | `build_baseline.py` (local; needs the held files), `build_registers.py` (deterministic, CI-safe), `check_c5.py` (validator) |

## Reproduce
```bash
python legal_knowledge/audit_work/SOURCE-LIBRARY-C5/tools/build_registers.py --check
```
```bash
python legal_knowledge/audit_work/SOURCE-LIBRARY-C5/tools/check_c5.py
```
```bash
python -m unittest tests.test_legal_audit_c5_sources
```
`check_c5.py --verify-files <held-root>` also re-hashes every held binary. It needs the session scratchpad that holds the files, which are not in git. CI runs the unit tests through the existing `test_legal_audit_*.py` discovery step.

## Controls carried forward
- `HELD_PRIMARY_*` is allowed only where the CALIBRATION-02 source-authentication register documents provenance. Other held official copies are `*_PROVENANCE_UNDOCUMENTED`, the same rule Cycle 4 used.
- No currency claim: no row is in force. `amendment_chain_status=CHECKED_FOR_RELEVANT_PERIOD` is rejected by the validator.
- These states are preserved exactly: r.23(3) CONFLICTING, r.182 SC4-01 OPEN, r.193 C-08 OPEN, r.194 C-09 PROPOSAL, the 13 WS-B inconsistencies, AQ-05/AQ-06, and the 29 Cycle 4 escalations (not touched).
- NOT_FOUND is never written for NOT_CHECKED.
