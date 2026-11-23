# AUTH-LEDGER: immutable authentication overlay (Cycle 7, AUTH-LEDGER-01)

**Status: version zero only.** There are **no ledger entries, no approvals and no authentication promotions.** The overlay reads the frozen Cycle 4 and Cycle 5 records and reproduces the merged Cycle 5 state byte-for-byte. Nothing here changes legal status, currency or applicability.

- **Specification:** `../C6-01-PROVENANCE/addendum/INTEGRATION_ARCHITECTURE.md` (revision 2).
- **Implementation decisions and discrepancies:** `DESIGN_NOTES.md`.
- **Open rule policy questions:** `POLICY_OPTIONS.md`.

## Layout
| Path | Content |
| --- | --- |
| `frozen_inputs.json` | sha256 pins of the 76 historical files the overlay reads: the files the frozen Cycle 5 builder reads (traced), the frozen builder and Cycle 4 rule code, the Cycle 5 registers, the evidence registers used by `strength.py`, the original corpus files and `evidence/*`. Any mismatch **fails closed** |
| `evidence/` | `copy_facts.csv` and `copy_structure.csv`, copied once from C6-01 with provenance (`EVIDENCE_PROVENANCE.json`). The overlay never imports C6-01 code |
| `schema/ledger_entry.schema.json` | entry contract: ADD / CORRECTION / WITHDRAW, decision-chain fields, per-type rules; no legal-status field |
| `ledger/manifest.jsonl`, `ledger/HEAD` | hash-chained manifest; currently only the **genesis line (version 0)** |
| `ledger/vNNNN.csv` | immutable entry files (none yet) |
| `decisions/` | committed owner decision records and reviewer reports (none yet) |
| `corrections/` | documentary corrections to frozen texts (none recorded yet; `notes.csv` is created with the first note) |
| `effective/v0000/` | derived outputs of version 0, pinned by `effective_sha256` in the genesis line |
| `tools/` | `rules_v1.py` (copy-status rule), `strength.py` (evidence checks), `ledger.py` (chain, approvals, entry semantics), `reader.py` (effective state), `pins.py`, `auth_ledger.py` (command line) |

## Commands (offline)
```bash
python legal_knowledge/audit_work/AUTH-LEDGER/tools/auth_ledger.py verify
```
```bash
python legal_knowledge/audit_work/AUTH-LEDGER/tools/auth_ledger.py build --as-of 0 --out /tmp/auth-ledger-v0
```
```bash
python -m unittest tests.test_legal_audit_auth_ledger
```

## What version zero proves
- `effective/v0000/source_copy_register.csv`, `source_master_register.csv`, `corpus_crosswalk.csv` and `coverage_summary.json` are byte-identical to the frozen `SOURCE-LIBRARY-C5/registers/` files.
- Copy statuses are computed by the overlay's own rule (`rules_v1.py`), not by the frozen Cycle 4 module. A test proves the overlay rule gives the frozen rule's status for every one of the 328 held sha256 values.
- **Isaac stays AUTHENTICATION_PENDING.** The 13 Cycle 4 register rows keep their treatment, and none of the 32 C6-01 proposals is active.
- `source_states.csv` is a new representation. It holds one row per source with the frozen and effective holding states and the basis. At version 0 the two states are equal for every source (tested).
- `transitions.json` and `newly_withdrawn.json` are empty arrays.
