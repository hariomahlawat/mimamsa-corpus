# Corpus quality: Cycle 8, Workstream E findings

Scope: targeted cross-volume data-quality review of the snapshot `c8base` (commit bb1f0971), plus a deterministic judgment-batch reconciliation tool. Outputs are findings and PROPOSALS only. No original record, register or repository file was modified (`git status` was clean after the run). Nothing here determines legal status or judicial treatment as fact.

## Method

- **Scripted cross-reference checks** (`tools/xref_checks.py`, 21 check families, offline and stdlib only). They joined the KB records (658), the case records (53), the WS-B judgment registers, the WS-D relation and code registers, and the SOURCE-LIBRARY-C5 registers. The run produced 125 candidate observations, which were then triaged by hand. Full table: `cross_reference_findings.md`.
- **Novelty check.** Every candidate was compared against the existing registers named in the brief (WS-D, WS-B open inconsistencies and adverse queue, SOURCE-CONFLICTS-01, CALIBRATION-02, C6-PREP carry-over, PILOT-01, C5 conflict and correction registers), plus verification_batches and legal_review. Findings already recorded are marked EXISTING(ref) and are not counted as new.
- **High-risk sample.** 33 records (30 KB, 3 cases) were selected by a deterministic risk score across nine legal-consequence domains, with 3 documented manual additions. Each was verified against held authoritative copies by sha256 and page (`HIGH_RISK_REVIEW.md`).
- **Priority scale:**
  - P1: an incorrect relationship or unsupported classification that could materially mislead.
  - P2: important evidence missing or inconsistent.
  - P3: metadata or terminology with limited legal consequence.

  Cosmetic items (for example an id year that differs from the decision year) were not reported.

## Counts

| Priority | NEW | EXISTING (re-confirmed, listed for traceability) |
| --- | --- | --- |
| P0 | 0 | 1 (r.23(3) caution conflict, C-01) |
| P1 | 0 | 3 (Ram Avtar URL OI-08/A-C2-01; Parashotam holding F-JUD-017; BSA/s.133 C-07) |
| P2 | 1 | 3 (case copy binding OQ-D-012; Isaac propagation D-CV-012; unheld 2026 authorities A-C2-05 etc.) |
| P3 | 8 | 7 |
| **Total** | **9** | **14** |

The correction package (`correction_proposals.csv`) has 24 rows: 3 at P2 and 21 at P3, all PROPOSAL_NOT_APPLIED. There are more proposal rows than findings because one finding can affect several records or register rows.

## Highest-priority unresolved risks

1. **Treatment propagation (NEW, P2, E8-XR-01).** A later judgment recorded against a case is not carried to every record that relies on that case. Girish Kumar (2026 INSC 149, held official copy `4f7ea3a4…` pp.15-16 para 22) held Tarsem Singh inapplicable to broad-banding re-computation claims and the AFT s.22(1)(c) bar inapplicable to them. AFT-013 and V7-SC-02 still give Tarsem Singh as the arrears authority without that distinction. The root cause is structural: WS-B `affected_kb_ids` lists are hand-written and sometimes contain codes or wildcards (E8-XR-07). The X19 check now in `xref_checks.py` catches this pattern deterministically and should be run whenever a treatment row is added.
2. **Existing P0/P1 items remain unapplied:**
   - the r.23(3) caution conflict (C-01);
   - CM-011's s.122 computation and missing s.123(2) (F-PROC-006/007);
   - the Parashotam row omitting its ratio on Shri Kant Sharma (F-JUD-017);
   - the BSA/s.133 interaction (C-07);
   - the Ram Avtar URL pointing at the S P Rathore judgment (A-C2-01).

   CM-011 and CM-025 still display SOURCE_REVIEWED status while these items are open (E8-XR-09).
3. **Current pension and administrative law rests on unheld sources.** These include the Girish clarification (2026 INSC 1113; only a commercial-mirror URL exists), Pooja Pal (2026), 2023 INSC 985, 2026 INSC 281, the DESW FAQ and MoD letters on ER 2023, and the PRA 2008 parts. The held ER 2023 copy is image-only and incomplete.
4. **Provenance hygiene.** Four citation-lead case records point at another judgment's URL (E8-XR-03). 23 URL fields still point at commercial databases (EXISTING). No case record is byte-bound to its held official copy (EXISTING OQ-D-012).

Clean results worth recording:

- No KB record presents IPC, CrPC or the Evidence Act as current without a transition caveat.
- No KB record presents the 1992-omitted sections (ss.75-76, 127, 195-196) as live.
- Crosswalk, copy-register, amendment-chronology and versioned-edge integrity checks found 0 defects.
- The held-binary manifest hashes all match.

## Judgment-batch reconciliation tool

`tools/reconcile_judgments.py` (stdlib, offline) classifies incoming items as one of:

- EXACT_DUPLICATE
- VERSION_RELATIONSHIP
- SAME_JUDGMENT_NEW_COPY
- POSSIBLE_MATCH_REVIEW
- NEW

It works against cases_53, the WS-B identity and holdings registers, and the C5 copy register. Its safety properties:

- It validates required fields and fails closed: one malformed item means exit status 2 and no report.
- It never merges or overwrites, and refuses an output path that is one of its inputs.
- Its output is deterministic.
- It states that NEW means only "not in the supplied snapshot", not absent from every collection.

**Tests:** `tools/test_reconcile_judgments.py`, 25 unittest cases, all passing (log in `work/unittest_output.txt`). A smoke run on the real snapshot classified a synthetic 5-item batch built from known held copies as expected (`work/smoke_report.csv`). Usage and limits are in `tools/README.md`.

## Limitations

- The review is targeted, not exhaustive. The sample is risk-weighted, so no corpus-wide error rate can be inferred from it.
- Deterministic checks are bounded by register linkage (the WS-B crosswalk) and by lexical patterns.
- Statutory verification used India Code government compilations (no Gazette copy of the 1950 Act is held). Judgment readings used PDF text layers. No new page-image checks were made.
- Unheld sources (DESW, MoD letters, most 2026 judgments, AFT Procedure Rules binary, BNS) could not be verified offline.
- The outputs are CSV/Markdown deliverables. They are not packaged as a `tools/legal_audit/validate.py` JSON package. If they are later imported into that structure, every row should carry `requires_legal_review=true`.
- No legal status, treatment or interpretation is determined. Every proposal needs legal-adviser and JAG review before any overlay is applied.

## Output files (c8out/E/)

- `cross_reference_findings.csv`, `cross_reference_findings.md`
- `high_risk_record_review.csv`, `HIGH_RISK_REVIEW.md`
- `correction_proposals.csv`
- `CORPUS_QUALITY_C8_FINDINGS.md` (this file)
- `tools/`: `reconcile_judgments.py`, `test_reconcile_judgments.py`, `README.md`, `xref_checks.py`, `select_sample.py`
- `work/`: `xref_candidates.csv`, `sample_selection.csv`, `unittest_output.txt`, `smoke_batch.jsonl`, `smoke_report.csv`, builder scripts, and the text extracts used for verification (derived from held copies; regenerate them with `work/pdftext.py`)
