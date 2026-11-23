# C6-01 authentication addendum: incorporation process (DRAFT, not executed)

**The mechanism is specified only in `INTEGRATION_ARCHITECTURE.md` (revision 2, the overlay design).** This file covers process. Draft entries follow `addendum_entry.schema.json`.

## Draft entries
`authentication_addendum_v1_draft.csv` is built by `tools/build_addendum_plan.py` (deterministic, `--check`). On every build, the builder validates each row against the schema and checks that every evidence reference resolves.

- **32 entries:** 28 primary (20 Gazette facsimiles and 8 SC court copies) and 4 non-primary (TRA 2026, ER 2023 13 MB, the 2022 archive.org derivative e-Gazette, and the Rajbir court-system rendition). All are `entry_status=DRAFT`, `owner_decision=PENDING` and `reviewer_decision=PENDING`.
- **Not entries:** the Rajya Sabha papers-laid record and Rajbir copy C2. After the Fable review (F-01, F-02), both fall to PROVENANCE_PARTIALLY_DOCUMENTED by rule. The RS record is also WITHHELD by owner instruction and stays a discovery/evidence candidate. Its S.O. 4010 date is DISPUTED (C5 RV-01; C5 D7 disagreement OPEN).
- **Per-entry crosswalk effect:** informational only, because effects do not compose. Only the 7 SC primary entries for case records change a crosswalk row, moving 7 cases from PARTIAL to EXACT. N S Yadav, which is not one of the 53 cases, and all Gazette and non-primary entries change none.

## Process (each step a separate approval)
1. **Owner approval of the overlay design** (architecture revision 2). Then PR 1: the skeleton with zero entries.
2. **Owner decisions:**
   - per entry or per tranche;
   - on the copy-fidelity class rule (TRA 2026 and the 2022 derivative), see `reports/TRA2026_CLASS_COMPARISON.md`;
   - on Cycle 4 vocabulary normalisation (carrier and locator wording, R-09).
3. **Addendum-specific independent review** of each tranche against its evidence, recorded in `decisions/`.
4. **One PR per tranche.** It converts the approved draft rows to an immutable ledger version and shows the reader's joint-effect diff.
5. **Post-merge checks:** frozen-file pins unchanged; original 658/53 hashes unchanged; `--as-of` reproducibility.

No step changes legal status. No entry is approved because of its coverage effect.
