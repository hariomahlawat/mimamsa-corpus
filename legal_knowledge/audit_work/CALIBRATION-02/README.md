# CALIBRATION-02: substantive review of the 46 CALIBRATION-01 records (Cycle 4)

**DATABASE ONLY. Evidence review, not legal approval.** No state here is legal-advisor or JAG validation. The 658 records and 53 cases are immutable. Reserved states are unchanged: r.23(3) CONFLICTING; r.193 C-08 OPEN; r.194 C-09 PROPOSAL; r.15, r.187(1) and s.129 OPEN; AQ-05, AQ-06 and OQ-A-13 reserved. The 13 WS-B inconsistencies stay OPEN.

## Sample
The sample is `COORDINATION/CALIBRATION-01/calibration_package.csv`, unchanged: 46 records, with the same denominator and selection.

`tools/build_propositions.py` splits each record body into sentences, producing `propositions.csv` (382 propositions). IDs are `<record>#P<n>`, plus `<record>#REF` for the references field. Text is copied verbatim. The script is deterministic and reruns byte-identically.

## Protocol
1. **Independent reviews**, each in its own branch and worktree, written without access to the others' findings:
   - **A Statutory:** Acts, Rules, Gazette instruments, amendment chains, versions and dates.
   - **B Judicial:** case identity, holding vs obiter vs headnote, subsequent treatment, copy authenticity.
   - **C Procedure:** competent authority, initiation, safeguards, hearing, evidence, limitation, review and remedies.
   - **D Challenge:** an independent assessment of the same 46 records that does not read A–C.
2. **Output:** each reviewer writes `reviews/<R>/findings.csv`, with exactly the columns in `tools/check_calibration02.py`. Every proposition gets at least one row.
3. **Evidence states:**
   - VERIFIED_AGAINST_HELD_PRIMARY_SOURCE: needs the held file's SHA-256 and an exact locator;
   - SUPPORTED_BY_SECONDARY_SOURCE_ONLY;
   - SOURCE_NOT_HELD;
   - HISTORICAL_VERSION_UNRESOLVED;
   - CONTRADICTORY_EVIDENCE;
   - INTERPRETATION_REQUIRES_LEGAL_ADVICE;
   - UNSUPPORTED;
   - NOT_YET_REVIEWED;
   - NOT_A_LEGAL_PROPOSITION: for design or administrative statements, e.g. on the eventual application.

   A citation existing, or a document being searchable, is never verification. The MML is a manual, not authority. Compilations (India Code, MoD) are comparison text under SOURCE_AUTHORITY_POLICY v1, never Gazette authority.
4. **Severity:**
   - P1: materially incorrect or unsupported, and could lead to unlawful or seriously flawed action.
   - P2: a significant omission, wrong authority, historical-version error, wrong citation or misleading procedure.
   - P3: minor.

   A P1 or P2 needs a proposed correction, or the missing evidence that blocks one.
5. **Reconciliation:** the coordinator reconciles by proposition (`reconciliation/`) only after all four reviews are committed. A disagreement is preserved and escalated; nothing is settled by majority.
6. **Proposals:** corrected text goes in `proposals/`, linked to the original record ID and proposition. The originals are never edited.

## Held sources (read-only; no downloads)
- **Index:** `registers/held_sources_scratchpad.csv` lists every held scratchpad file with its SHA-256. The scratchpad is not the evidence of record; the hash is the identity.
- **In the repository:**
  - audit batches PILOT-01, R23-VERIFY-01, ACQ-01/02, ARMY-RULES-CHAIN-01 and WS-A/B/C/D (registers and page-image checks);
  - `origin/raw-data` crawler corpus: `data/text` (Army Rules 1954 compilation, Acts, SC/HC judgments) and `data/sections`.

## Validation
- `python3 legal_knowledge/audit_work/CALIBRATION-02/tools/check_calibration02.py --require A,B,C,D`
- `tests/test_legal_audit_calibration02.py`
