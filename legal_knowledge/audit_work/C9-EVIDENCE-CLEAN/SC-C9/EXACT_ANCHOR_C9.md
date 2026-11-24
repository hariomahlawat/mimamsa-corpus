# Exact-anchor simulations, Cycle 9 (Supreme Court)

> **SIMULATION ONLY.** Every approval record here is synthetic. Each run wrote a temporary ledger under `<scratchpad>/c9sim_tmp/`, which was deleted after the run; the parent folder was removed afterwards. Nothing was written to any ledger. The committed AUTH-LEDGER stays at version 0. `git status --short` on the snapshot `c9src` (2d7c02cf) was empty before and after, and no `__pycache__` was created. Nothing here says whether any judgment is good law, binding, followed or overruled.

## Method
- **Tool:** `tools/sim_anchor_c9.py <c9src>/legal_knowledge/audit_work <tmp_parent> exact_anchor_simulations_c9.json [--check]`.
  - It imports the snapshot's own `AUTH-LEDGER/tools/reader.py` (`effective_state`, rule version 1), `ledger.py` and `strength.py`, with bytecode writing disabled. The pattern is that of C8 `SC-T2/tools/sim_anchor.py`.
  - Candidates are the 8 C6-01 draft rows with `proposed_class = PRIMARY_OFFICIAL_COURT_COPY`. Each `T:` identity reference is rewritten to `T:AUTH-LEDGER/evidence/copy_facts.csv#<copy_id>`.
  - Each run approves its entries synthetically as ledger version 1 and reads the state with `require_binding=False`.
  - Option (b) adds a synthetic demotion of the PPS Bedi baseline row (`target_entry_id = BASELINE:211dbaf4…`). Its evidence references are the two records the Cycle 4 register itself cites: `PILOT-01/registers/source_code_resolution_v3.csv#SC_PPS` and `WS-B-JUDGMENTS/tools/held_copies.csv#PPS_BEDI`.
- **Output:** `exact_anchor_simulations_c9.json` (sha256 `74e7015a6fb4de58af2d2fe24130fe7f660462167e735375b21f92e3ec985468`). `--check` re-ran every scenario and reproduced the file byte for byte.
- **Counting rule:** every count is the number of distinct `case_id` values with `EXACT_ANCHOR` in the effective crosswalk of that run. Joint runs were computed as joint runs; single results were never added together.

## Results
| Run | Validator | EXACT_ANCHOR cases | Case rows changed vs v0 |
| --- | --- | --- | --- |
| Version 0 | n/a | **6** (PPS Bedi, Anvar, Virendra, Arjun, Jasbir, Parashotam); byte-identical to frozen C5 `corpus_crosswalk.csv` and `coverage_summary.json` | n/a |
| Ranjit alone | PASS | 7 | DCLR-SC-1987-R01 |
| S N Mukherjee alone | PASS | 7 | DCLR-SC-1990-N02 |
| Navjot alone | PASS | 7 | DCLR-SC-2005-L01 |
| Dharamvir alone | PASS | 7 | DCLR-SC-2013-N08 |
| Rajbir C1 alone | PASS | 7 | DCLR-SC-2015-N09 |
| Narsingh Yadav ("N S Yadav") alone | PASS | 6 | none (no case record) |
| Girish alone | PASS | 7 | DCLR-SC-2026-007 |
| Mullikote alone | PASS | 7 | DCLR-SC-2026-N16 |
| **All 8 jointly (option (a))** | PASS | **13** | the 7 rows above; 8 copies become EFFECTIVE_PRIMARY_VERIFIED; 8 sources become HELD_PRIMARY_OFFICIAL_COURT_COPY |
| Without the 3 JUDIS drafts (PPS Bedi untouched) | PASS | **10** | |
| Without Navjot and Mullikote (C8 recommendation) | PASS | **11** | |
| Without the 3 JUDIS drafts and Mullikote | PASS | **9** | |
| **Option (b), b2:** 5 non-JUDIS candidates + PPS Bedi CORRECTION to AUTHENTICATION_PENDING | PASS | **9** | DCLR-SC-1982-001 goes EXACT_ANCHOR → PARTIAL_MATCH; N08, N09, 007, N16 go PARTIAL → EXACT |
| Option (b), b3: same, with a WITHDRAW (CLASSIFICATION_ERROR, resulting AUTHENTICATION_PENDING) | PASS | **9** | same as b2 |
| Option (b), b4: b2 plus the 3 JUDIS drafts added as NON_PRIMARY_OFFICIAL_COURT_RENDITION | PASS | **9** | same as b2. The 3 copies become DOCUMENTED_NON_PRIMARY, eligible NO. Their source holding states do not change (they stay HELD_OFFICIAL_COURT_COPY_PROVENANCE_UNDOCUMENTED) |
| Option (b), **b1:** 5 non-JUDIS candidates + PPS Bedi CORRECTION to NON_PRIMARY_OFFICIAL_COURT_RENDITION (documented) | **FAIL** | n/a | validator: "reference 'AUTH-LEDGER/evidence/copy_facts.csv#C5-SRC-J-SC-1982-PPS-BEDI~C1' resolves to 0 records" |
| Option (b), b0: PPS Bedi demotion alone, from v0 | PASS | 5 | DCLR-SC-1982-001 only; source becomes HELD_AUTHENTICATION_PENDING |
| Option (b), b5: option (b) and Mullikote kept PARTIAL | PASS | 8 | |
| Option (c) count proxy, c1: all 8 minus Ranjit | PASS | 12 | count only; see below |
| Option (c) count proxy, c2: minus Ranjit, Navjot and Mullikote | PASS | 10 | count only |

KB rows are unchanged in every run: EXACT 42, MISSING 366, PARTIAL 652. The KB rows for these sources carry "no provision locator" or "inferred identity", so the KB rule keeps them PARTIAL.

## Confirmation of the stated figures
| Figure | Meaning | Result |
| --- | --- | --- |
| 6 | version 0 | **Confirmed** |
| 13 | all 8 jointly, option (a) | **Confirmed.** Same 13 case/source/copy triples as C8 |
| 10 | joint without the 3 JUDIS drafts | **Confirmed** |
| 11 | joint without Navjot and Mullikote | **Confirmed** |
| 9 | (i) joint without the 3 JUDIS drafts and Mullikote (C8 subset); (ii) option (b) applied consistently (PPS Bedi demoted) | **Confirmed for both**, but they are different sets of 9: (i) keeps PPS Bedi and leaves Mullikote PARTIAL; (ii) demotes PPS Bedi and anchors Mullikote |

Set (i), C8 subset: PPS Bedi, Anvar, Virendra, Arjun, Jasbir, Parashotam, Dharamvir, Rajbir, Girish.
Set (ii), option (b): Anvar, Virendra, Arjun, Jasbir, Parashotam, Dharamvir, Rajbir, Girish, Mullikote.

## What the option (b) runs show
1. **The arithmetic 6 → 9 holds**, but only through a demotion to **AUTHENTICATION_PENDING** (b2 and b3).
2. **The demotion that matches the option's wording does not validate under rule 1.** That demotion is a documented re-classification of PPS Bedi as `NON_PRIMARY_OFFICIAL_COURT_RENDITION` (b1).
   - A documented CORRECTION must pass the same identity check as an ADD.
   - PPS Bedi has no row in the pinned `AUTH-LEDGER/evidence/copy_facts.csv`, and no page-image check in any file the validator accepts.
   - Its baseline row predates the ledger evidence files.
3. **What would be needed:**
   - Either add PPS Bedi to the pinned evidence, which is a frozen-input change and needs its own reviewed PR;
   - or record a human-confirmed image check of its p.1 (the C9 render hashes are in `tools/render_facts_c9.jsonl`).
4. **What option (b) can say today.** Expressed in rule 1 now, option (b) states that PPS Bedi's provenance is *pending*. Its provenance is in fact documented; only its class changes. That overstates the doubt.
5. **Rule-1 artefact (b4).** Adding the three drafts as documented non-primary renditions has no effect on their source holding states. A DOCUMENTED_NON_PRIMARY copy is not reflected in `derive_holding`, which leaves the source "provenance undocumented".
6. **Timing.** Any real demotion is a ledger transaction with records, review and binding. Its timing depends on O-5 (demotion semantics), which is unresolved.

## Option (c)
- **Rule 1 cannot simulate (c).** It has no page-range or text-scope anchors, and its case rows check nothing beyond the case-to-source mapping.
- **The two proxy runs give counts only.**
  - They apply the JUDIS condition "only where no later order is known". This withholds Ranjit, because the review order of 10.8.88 is known but not held.
  - They leave PPS Bedi as at version 0.
- **Results:** 12 with all other candidates; 10 with the C8 keep-PARTIAL recommendations for Navjot and Mullikote.
- **What the counts do not model:** the exclusion of headnote pages. That is what (c) is for (see `JUDIS_POLICY_DECISION.md`).

## Caveats
- **Identity basis.** Every candidate passes rule 1 on the **page-1 text rule** for identity. None has a human-CONFIRMED image check. `HUMAN_VERIFICATION_PACK.md` exists to supply one under policy B2.
- **Case rows rely on the mapping input.** A case row becomes EXACT_ANCHOR when its mapped source has an eligible copy (frozen C5 `crosswalk()`). The case row itself does not check date, case number or proposition.
  - Navjot's case record has no date or case number.
  - Mullikote's anchor would be file-level, covering two versions.
- **Narsingh Yadav.** Its approval changes copy and source states but no crosswalk row.
