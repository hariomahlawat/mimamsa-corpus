# CALIBRATION-01: methodology for the 46-record calibration (proposal; NOT yet accepted)

**State:** evidence package assembled; **no record adjudicated**. The full 658-record substantive audit must not start until this methodology is accepted by the owner and a human legal advisor is nominated.

## Inputs (frozen)
- **Sample:** `WS-C-MML/calibration_sample_ranked.csv` (46 records; selection only).
- **KB:** `records_658.jsonl`, sha `9a8f0d19…` (the assembler asserts it).
- **Evidence registers:**
  - WS-C inventory and crosswalk;
  - ARMY-RULES-CHAIN-01 chronology and version register;
  - WS-A provision change log;
  - WS-B crosswalk, holdings, treatment and adverse queue;
  - WS-C procedure gap register.
- **Build:** `build_calibration_package.py` (deterministic; re-run gives byte-identical output) produces `calibration_package.csv` and a summary.

## Per-record package fields
| Field | Content |
| --- | --- |
| Original record | `record_id`, `record_sha256`, `exact_claim` (verbatim body), `references_as_recorded` |
| Provisions | Army Act sections, Army Rules, other statutes (WS-C inventory, after the parser fix) |
| Relevant date | `relevant_date_as_recorded`: left empty for the adjudicator to fix from the record; never inferred |
| Chronology | Amendment and commencement events per cited rule; publication, commencement and effective date are kept distinct, and the effective date is null unless stated |
| Primary source and pinpoint | Citation codes, WS-A change-log IDs, version-register rows (with their determination state) |
| Manual | MML locators, marked manual, **not authority** |
| Judicial | Linked cases (identity and citability), holdings with paragraph pinpoints, subsequent treatment |
| Contradictions | WS-B adverse items and WS-C procedural gaps |
| Determination | `proposed_determination` and `uncertainty`: empty until calibration |
| Review | `independent_reviewer_assessment`: empty; `questions_reserved_for_legal_advisor`: generated from disputes, unstated commencement and adverse evidence |
| States | `adjudication_state = NOT_ADJUDICATED`; `legal_advisor_state` and `jag_validation_state = NOT_STARTED` |

## Proposed calibration procedure (needs owner acceptance)
1. **First reader** (Claude statutory or judgment auditor) proposes a determination per record: SUPPORTED / SUPPORTED_WITH_QUALIFICATION / OUTDATED / CONTRADICTED / INSUFFICIENT_EVIDENCE / CONFLICTING_SOURCES. The proposal must give the source, pinpoint, version and date applied, with each wording point image-checked.
2. **Independent reviewer** (a separate Claude instance, blind to the first reading) re-derives the determination from the same package. Disagreements are recorded, not averaged.
3. **The human legal advisor adjudicates** every record, starting with all disagreements and every disputed-provision record.
4. **Calibration metrics:**
   - first-reader vs advisor agreement and reviewer vs advisor agreement, by category and module;
   - error types (version or date error, wrong pinpoint, missed adverse authority, overstated holding).
5. **Acceptance gate for the full audit** (proposal): at least 90% agreement with the advisor on the 46, every error type analysed, and the methodology revised for each error type.

**Claude consensus is never human legal validation.** Agreement between the first reader and the reviewer only selects what the advisor sees first.

## Current package summary
- 46 records.
- 8 rely on a disputed provision (r.23(3) C-01, r.193 C-08, r.194 C-09).
- 13 have an amendment chronology.
- 13 have linked cases and 9 have holdings with pinpoints.
- 12 carry adverse or contradictory evidence.
- **0 adjudicated.**
