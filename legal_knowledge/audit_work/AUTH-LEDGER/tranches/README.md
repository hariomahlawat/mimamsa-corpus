# Prepared evidence tranches (AUTH-LEDGER-02): NOT ledger entries

Nothing in this directory is part of the ledger. `ledger/manifest.jsonl` stays at version 0, there are no decision or review records, and nothing is approved, bound or active. These files prepare the owner and the independent reviewer for future tranche PRs. Each tranche PR will add a ledger version with its own D- and R- records, its own review and a BIND line after its merge.

| Path | Content |
| --- | --- |
| `T1-GAZETTE/` | Gazette tranche 1, the 20 primary Gazette candidates: source register, 14-item evidence matrix, contradiction register, inactive ledger-format rows (`owner_decision` left empty), simulated joint impact, and findings (`TRANCHE1_FINDINGS.md`) |
| `T2-SUPREME-COURT/` | Supreme Court tranche 2, the 8 primary judgment copies: evidence-review plan and risks (`EVIDENCE_REVIEW_PLAN.md`) |
| `tools/build_tranche1.py` | deterministic builder for `T1-GAZETTE/` (`--check` reproduces byte-for-byte). Simulations run in a temporary directory with synthetic records that are deleted afterwards |
| `tools/policy_impact.py` | data for `../RULE_DECISION_PACK.md` (`--check`) |

Commands (offline):
```bash
python legal_knowledge/audit_work/AUTH-LEDGER/tranches/tools/build_tranche1.py --check
```
```bash
python legal_knowledge/audit_work/AUTH-LEDGER/tranches/tools/policy_impact.py --check
```
