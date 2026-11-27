# Research-use restrictions (Cycle 12 closeout)

The capabilities in `CAPABILITY_RESTRICTIONS.csv` are **restricted to non-operational research use**. Five P2 findings are deferred with a recorded reason (`findings_consolidation/`):
- C11 extraction F05, F06, F07 and F08;
- WS-G R04.

The other capabilities listed are restricted for related reasons.

## What "restricted" means here

**Status values.** Every output row keeps its candidate status:
- `AUTOMATED_CANDIDATE_NOT_VERIFIED` for outcomes and holdings;
- `NOT_VERIFIED_RATIO_NOT_DETERMINED` for holdings;
- `PROPOSED_NOT_APPLIED` for statutory proposals.

The test `tests/test_legal_audit_c12_research_isolation.py` fails if any row loses its status.

**Use in the offline application (blueprint, Track B).** These outputs may appear only as research leads labelled as candidate data. They must not drive:
- advice;
- checklists;
- compliance checks;
- form validation;
- any statement presented as the law or as the outcome of a case.

**No promotion.** Nothing here changes evidence classifications or AUTH-LEDGER state, which stays at version 0.

Each restriction is lifted only when its condition in the CSV is met and reviewed.
