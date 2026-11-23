# C6-01 authentication addendum v1: incorporation plan (DRAFT, not executed)

The technical mechanism is specified in `INTEGRATION_ARCHITECTURE.md`; where this plan and that design differ, the design governs.

**Status:** plan only. Nothing here changes `CALIBRATION-02/registers/source_authentication_register.csv` (the Cycle 4 register, 13 rows) or any Cycle 5 register. Executing it needs separate owner approval.

## 1. Mechanism: a versioned addendum, not an in-place edit
- **Baseline kept as is.** The Cycle 4 register stays byte-identical as the auditable baseline. Its sha256 is recorded in the addendum header at execution time.
- **One new file per approved version:** `CALIBRATION-02/registers/source_authentication_addendum_v1.csv`. It has the Cycle 4 register columns plus:
  - `addendum_entry_id`, `proposal_id` and the full `sha256`, which is the canonical key;
  - `reviewer_decision`, `owner_decision` and `decision_record_ref`;
  - `superseded_by`, left empty: a later version can withdraw an entry without editing this file.
- **Reading rule (code change at execution).** The shared evidence rule (`CALIBRATION-02/tools/evidence_classification.py`, `Evidence.from_dir`) reads the baseline, then each approved addendum version in order. Only rows with `owner_decision=APPROVED` are read. A key already in the baseline is refused, as is a duplicate key across versions. That refusal is a validator error, not an overwrite.
- **Withdrawal.** A later version marks the entry `WITHDRAWN` with a reason and evidence. Rows are never deleted.
- **Cycle 5 holding states must move with it (final review R-02).** The Cycle 5 builder checks that each source's `holding_state` agrees with its copy-level evidence, so adding addendum rows alone makes the build stop (correctly) at the first affected source. The earlier draft proposed a reviewed hand relabel of about 29 sources. **That is superseded by `INTEGRATION_ARCHITECTURE.md`:** the authentication component of the holding state is derived from copy-level evidence, the check stays on, and no second register is kept in sync by hand.
- **Cycle 4 vocabulary (R-03, R-09).** The Cycle 4 rule has no NON_PRIMARY_* class: either add those classes to the rule with tests, or record non-primary entries outside the evidence rule. Carriers and locators are normalised to Cycle 4 terms (for example `OFFICIAL_COURT_HOST (api.sci.gov.in)`, file URL rather than item page), keeping the "(as reported; retrieval record not documented)" qualifier where only a corroboration record exists.
- **No coverage target.** No entry is approved or rejected because of its effect on coverage figures. The per-entry crosswalk effect is recorded for transparency only.

## 2. Draft entries
`addendum/authentication_addendum_v1_draft.csv` is built by `tools/build_addendum_plan.py`, which is deterministic (`--check`). It has one row per C6-01 proposal: 34 rows, 30 primary and 4 non-primary; 33 are `DRAFT_PENDING` and 1 (RS papers-laid) is `WITHHELD`. Each row records:

| Field | Meaning |
| --- | --- |
| `source_id`, `copy_id`, `sha256` | the existing Cycle 5 source and copy |
| `original_c5_holding_state`, `original_c4_register_state` | status before the addendum. Every copy has `NO_ROW` in the Cycle 4 register |
| `provenance_evidence_refs`, `locator_strength` | the exact file#row evidence. All entries are FULL |
| `identity_evidence_refs` | page-image (I) or, for court PDFs only, page-1 text (T) references |
| `proposed_authentication_state`, `proposed_effective_source_class`, `primary_or_non_primary` | what would be added |
| `justification`, `limitations` | why the entry is proposed, and what it does not prove. Every limitation carried by the proposal is preserved |
| `crosswalk_effect_this_entry_alone` | Cycle 5 crosswalk rows that would change if this entry alone were added (simulated) |
| `reviewer_decision`, `owner_decision` | always `PENDING` in the draft |

**Crosswalk effect.** Only the 8 Supreme Court primary entries change a crosswalk row: 7 case records move from PARTIAL_MATCH to EXACT_ANCHOR. The two Rajbir copies each lift the same case. The 21 Gazette entries, the 4 non-primary entries and the N S Yadav entry (not one of the 53 cases) change no row; in particular, no KB citation item changes.

## 3. Steps at execution (each a separate approval)
1. **Owner approval** of this plan and of the entry list. Entries may be approved individually.
2. **Addendum-specific review.** An independent reviewer checks each approved entry against its evidence references and against the baseline. The review is recorded in `decision_record_ref`.
3. **One reviewed PR against staging** that:
   - adds the addendum file;
   - changes the reader;
   - adds validator rules: key uniqueness; no baseline override; FULL strength only; `owner_decision=APPROVED` only;
   - implements the derived holding state (`INTEGRATION_ARCHITECTURE.md` section 2.4) so the about 29 affected sources change state by derivation, with the consistency check left **on**;
   - rebuilds the Cycle 5 registers with the holding-state check switched **on**.

   That PR must show the exact crosswalk diff, and the diff must equal the simulated effect recorded here.
4. **Post-merge check:**
   - the Cycle 4 baseline hash is unchanged;
   - the original 658/53 hashes are unchanged;
   - the coverage figures equal the reviewed simulation.

## 4. Decisions reserved
- **TRA 2026 class.** The draft keeps the conservative `NON_PRIMARY_OFFICIAL_PUBLICATION_COPY` for an IndiaCode-watermarked re-host of the e-Gazette. Cycle 4 gave `PRIMARY_GAZETTE_GOVERNMENT_HOSTED_SCAN` to an India Code Gazette scan (Act 37/1992). The final review notes that Cycle 4 recorded the watermark on Act 37/1992 too, so what distinguishes TRA is that it is born-digital and its embedded signature's byte range no longer covers the held file (R-04). Whether the class extends to born-digital re-hosts is an owner decision. If primary, documented-primary copies and sources would be 43 and 42. It does not affect coverage.
- **RS papers-laid record (R-08): WITHHELD** by owner instruction (PR #33 finalisation). It stays on record as a discovery/evidence candidate (`entry_status=WITHHELD`) and is not approvable as it stands: the retrieval record marks authenticity UNCONFIRMED, the URL is an item page, and the S.O. 4010 date it transcribes is DISPUTED (C5 RV-01; C5 D7 disagreement OPEN). A future entry would need stronger evidence and a new addendum version.
- **Non-primary entries** are recorded for completeness. They do not satisfy the primary rule in Cycle 5.
- **Legal status.** Authentication records where a copy came from and that it is what it says. It does not establish that an instrument is in force, current or applicable. No legal status changes.
