# Evidence-classification harmonisation: regression evidence

**Change.** `tools/evidence_classification.py` is now the single evidence rule, imported by both `check_calibration02.py` and `reconcile.py`. Reviewer-claimed states are never modified. A separate effective status is derived from:
- the held-source index;
- `registers/source_authentication_register.csv`, which holds source-specific provenance for the 13 files cited by VERIFIED claims.

**Tests** (`tests/test_legal_audit_calibration02.py`):
- `EvidenceClassification` covers the ten owner-specified scenarios;
- `EvidenceIntegration` runs the validator and reconciler end to end.

| Run | Result |
| --- | --- |
| New test file on the original implementation c2fa137f (`tests_on_c2fa137f.log`) | FAILED: 3 failures, 28 errors |
| Same file after the fix (`tests_after_fix.log`) | OK |

The pre-fix errors have two causes. The shared module does not exist at c2fa137f, so the ten scenario tests and the fixture-based validator tests cannot import or copy it; this is a harness consequence, not a behaviour check. The three behavioural failures are the substantive evidence:
1. **The original reconciler counted a held PDF with unknown provenance as primary-backed:** `'PRIMARY_EVIDENCE_SUPPORTED' != 'AUTHENTICATION_PENDING'`.
2. **The original validator reported no effective status.** For identical bytes in official-claimed and secondary paths it printed only a generic warning.
3. **The original validator had no hash verification:** `0 != 1` on a deliberately mismatched file.

**Effect on figures (record level):**
- VERIFIED claims: 138, preserved.
- Effective primary: 134.
- AUTHENTICATION_PENDING: 4. These are Reviewer B's Isaac findings B-0109 (PEN-WF-03#P2), B-0111 (PEN-WF-03#P4), B-0248 (PEN-003#P7) and B-0272 (PEN-CL-06#P1). Reviewer D's four assessments of the same propositions remain SUPPORTED_BY_SECONDARY_SOURCE_ONLY, as submitted.
- Proposal CP2-B-0109 moves from SECONDARY_EVIDENCE_ONLY to AUTHENTICATION_PENDING. CP2-B-0248 and CP2-B-0272 remain DISPUTED_ESCALATED, which takes precedence; their effective status is now recorded as AUTHENTICATION_PENDING.
- Record classes, agreement classes, disagreements (12), severity splits (17) and the number of proposals (47) are unchanged.
- **Hash verification:** `check_calibration02.py --verify-files <scratchpad>` re-hashed every held file cited by a VERIFIED claim. There were 0 mismatches.
