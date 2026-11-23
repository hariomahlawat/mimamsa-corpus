# Exact-anchor recalculation for the Supreme Court primary candidates

> **SIMULATION ONLY.** The approval records here are synthetic. They were written in a temporary directory under `c8out/C/tmp_sim/`, which is deleted after each run. This is not a ledger version, not an approval, and not evidence of any owner or legal approval. The committed ledger stays at version 0. `git status` on the snapshot was empty after the runs.

## Method
- **Tool:** `tools/sim_anchor.py <audit_work> <tmp_parent> <out_json>`.
  - It imports the snapshot's own `AUTH-LEDGER/tools/reader.py` (`effective_state`), `ledger.py` and `strength.py`.
  - Bytecode writing is disabled.
  - It reuses the `Sim` and `to_entry` pattern of `tranches/tools/build_tranche1.py`.
- **Entries:**
  - The 8 C6-01 draft rows with `proposed_class = PRIMARY_OFFICIAL_COURT_COPY`.
  - Each `T:` identity reference is rewritten to `T:AUTH-LEDGER/evidence/copy_facts.csv#<copy_id>`.
  - Each entry is approved synthetically as ledger version 1 (`require_binding=False`).
- **Runs:**
  - (a) version 0;
  - (b) each candidate alone;
  - (c) all 8 together;
  - three further subsets, for context.
- **Comparison:** every crosswalk row is keyed on (source_id, provision_id, KB id, case_id, relationship, occurrence), and all columns are compared.
- **Output:** `exact_anchor_simulation.json` (sha256 `f96f2f3e2fdab7f4c951f3bb87684196962c893f615192985a8e1933fe186f80`).

## Results
| Run | Rule 1 | EXACT_ANCHOR case count | Crosswalk rows changed |
| --- | --- | --- | --- |
| (a) version 0 | n/a | **6** (PPS Bedi, Virendra, Jasbir, Parashotam, Anvar, Arjun) | n/a. Byte-identical to frozen C5 `corpus_crosswalk.csv` and `coverage_summary.json` |
| Ranjit Thakur alone | PASS | 7 | 1: DCLR-SC-1987-R01 |
| S N Mukherjee alone | PASS | 7 | 1: DCLR-SC-1990-N02 |
| Navjot alone | PASS | 7 | 1: DCLR-SC-2005-L01 |
| Dharamvir alone | PASS | 7 | 1: DCLR-SC-2013-N08 |
| Rajbir C1 alone | PASS | 7 | 1: DCLR-SC-2015-N09 |
| N S Yadav alone | PASS | 6 | 0 (no cases_53 record) |
| Girish alone | PASS | 7 | 1: DCLR-SC-2026-007 |
| Mullikote alone | PASS | 7 | 1: DCLR-SC-2026-N16 |
| **(c) all 8 jointly** | PASS | **13** | **7**, the same seven rows |
| Context: without the 3 JUDIS text renditions | PASS | 10 | n/a |
| Context: without Navjot and Mullikote | PASS | 11 | n/a |
| Context: without the 3 JUDIS renditions and Mullikote | PASS | 9 | n/a |

**The C6-01 claim "6 → 13" is reproduced.** C8 recomputed it with the actual reader; it was not copied from earlier work.

The joint run changes the seven case rows below:
- In each, `evidence_status` goes from PARTIAL_MATCH to EXACT_ANCHOR, and `anchor_copy_id` and `basis` change.
- The new basis is "documented-primary official judgment copy held (identity per mapping input)".
- **No KB row changes.** KB status counts stay EXACT 42, MISSING 366, PARTIAL 652. The KB rows for these sources carry "no provision locator" or "inferred identity", so the KB rule keeps them PARTIAL.
- 8 copies change PROVENANCE_UNKNOWN → EFFECTIVE_PRIMARY_VERIFIED. N S Yadav is one of them, but it changes no crosswalk row.
- 8 sources change HELD_OFFICIAL_COURT_COPY_PROVENANCE_UNDOCUMENTED → HELD_PRIMARY_OFFICIAL_COURT_COPY.
- Rajbir C2 and C3 are untouched, so nothing is double-counted.

**What "rule 1" means for case rows.** In the frozen C5 builder, `crosswalk()` (lines 463-464), a case row becomes EXACT_ANCHOR when its mapped source (`inputs/case_source_map.csv`, basis "case id") has any copy with `eligible_for_exact_anchor = YES`. The case rows apply no check of their own on date, case number or proposition. Case identity rests on the mapping input.

## Each newly anchored case
| case (cases_53) | supporting copy (anchor_copy_id, sha256) | citation relationship | C8 page evidence | Why it qualifies under rule 1 | C8 assessment |
| --- | --- | --- | --- | --- | --- |
| DCLR-SC-1987-R01 Ranjit Thakur | C5-SRC-J-SC-1987-RANJIT-THAKUR~C1, `ed7cf31f…f399` | IS_SOURCE_OF_CASE_RECORD. Record: CA 2630/1987, 1987-10-15, (1987) 4 SCC 611, [1988] 1 SCR 512. Document prints the same, plus AIR 1987 SC 2386 | C8-SCPIC-01 to 04: parties, date, bench (p.1), case number (p.3), author (p.4), end of text (p.9). All match | Mapping by case id; copy primary under synthetic approval (FULL locator; page-1 text identity) | Identity adequate. **Depends on P-D3**: JUDIS text rendition with HEADNOTE and an editorial note on a 10.8.88 order (review order not held). If anchored, pinpoints must exclude pp.1-3 up to "JUDGMENT:" |
| DCLR-SC-1990-N02 S N Mukherjee | C5-SRC-J-SC-1990-SN-MUKHERJEE~C1, `eb442080…69cc` | Record: 1990-08-28, (1990) 4 SCC 594, 1990 Supp (1) SCR 44; case_number empty. Document: CA 417/1984 | C8-SCPIC-05 to 07 | Same | Identity adequate. **Depends on P-D3**. The case record should carry CA 417/1984 |
| DCLR-SC-2005-L01 Navjot Sandhu | C5-SRC-J-SC-2005-NAVJOT~C1, `3b753548…215d` | Record: CITATION_LEAD with empty date, case number and holding. Document: Crl.A. 373-375/2004, 04/08/2005 | C8-SCPIC-08, 09 | Same; first-class record S-REVB-012 is SOURCE_LOCATED | **Recommend keeping PARTIAL.** (1) Depends on P-D3. (2) The first-class record is located but not verified (RULE_DECISION_PACK A2 would demote it). (3) The case record has no date or case number to match, so the anchor would attach to a citation lead with no proposition. The C8 page check supplies the date and number, but the record does not yet carry them |
| DCLR-SC-2013-N08 Dharamvir Singh | C5-SRC-J-SC-2013-DHARAMVIR~C1, `3056712c…6b75` | Record: CA 4949/2013, 2013-07-02, (2013) 7 SCC 316. Document: same case number and date; SCC citation not printed | C8-SCPIC-10, 11: cover, signature lines, NEW DELHI JULY 2, 2013 | Same | Page evidence adequate (agent reading, not human). Reported citation unconfirmable from this copy |
| DCLR-SC-2015-N09 Rajbir Singh | C5-SRC-J-SC-2015-RAJBIR~C1, `970b9680…c666` | Record: CA 2904/2011 and connected, 2015-02-13 | C8-SCPIC-12 to 14 | Same | Page evidence adequate. The C6-01 identity string wrongly lists C2 and C3 identifiers ("rop_275403; bosir copy") against C1, and should be corrected before any real entry. Pinpoints apply to C1 pagination (20 pp.) only |
| DCLR-SC-2026-007 Girish Kumar | C5-SRC-J-SC-2026-GIRISH-FEB~C1, `4f7ea3a4…b86c` | Record: CA 6820-6824/2018, 2026-02-12; reporter_citation empty. Document: 2026 INSC 149 | C8-SCPIC-17, 18: neutral citation, signature appearance, judges, date | Same | Page evidence adequate. The record should carry 2026 INSC 149 |
| DCLR-SC-2026-N16 Mullikote | C5-SRC-J-SC-2026-MULLIKOTE~C1, `10e1954f…7444` | Record: 2026-03-24, 2026 INSC 286, Diary 27246/2023 | C8-SCPIC-19 to 22: CORRECTED version on pp.1-31; second version on pp.32-62 with a different service number and continued numbering | Same | **Recommend keeping PARTIAL** until the anchor names pp.1-31 as the corrected judgment (WS-B OI-03 open). The file-level anchor covers two versions, and the date link of the corrected version is not evidenced (Fable F-15). Case identity itself is confirmed |

## Caveats
- All eight entries pass rule 1 on the **page-1 text rule** for identity. None has a CONFIRMED image check recorded in the snapshot.
- The C8 checks are agent readings and are not committed evidence. Whether an agent reading meets policy B2 is for the owner to decide.
- These results say nothing about whether any proposition is current, binding, followed or overruled.
