# Corpus quality: Cycle 8, Workstream E findings

Scope: targeted cross-volume data-quality review of the snapshot `c8base` (commit bb1f0971), plus a deterministic judgment-batch reconciliation tool. Outputs are findings and PROPOSALS only. No original record, register or repository file was modified (`git status` was clean after the run). Nothing here determines legal status or judicial treatment as fact.

## Method

- **Scripted cross-reference checks** (`tools/xref_checks.py`, 21 check families, offline and stdlib only). They joined the KB records (658), the case records (53), the WS-B judgment registers, the WS-D relation and code registers, and the SOURCE-LIBRARY-C5 registers. The first run produced 125 candidate observations, which were triaged by hand. After review RC-08, X14b also scans the two base WS-B registers, and the run now produces 164 candidates (39 more X14b tokens, all within E8-XR-07). Full table: `cross_reference_findings.md`.
- **Novelty check.** Every candidate was compared against the existing registers named in the brief (WS-D, WS-B open inconsistencies and adverse queue, SOURCE-CONFLICTS-01, CALIBRATION-02, C6-PREP carry-over, PILOT-01, C5 conflict and correction registers), plus verification_batches and legal_review. Findings already recorded are marked EXISTING(ref) and are not counted as new.
- **High-risk sample.** 33 records (30 KB, 3 cases) were selected by a deterministic risk score across nine legal-consequence domains, with 3 documented manual additions. Each was verified against held authoritative copies by sha256 and page (`HIGH_RISK_REVIEW.md`).
- **Priority scale.** The binding scale is the review-gate scale in `docs/legal-audit/EVIDENCE_STANDARD.md` (P0 critical; P1 likely wrong material doctrine or missing contrary precedent; P2 omission, ambiguous cross-reference, incomplete metadata affecting retrieval; P3 editorial). The priorities in the CSVs were assigned on a local C8 scale and are kept as assigned, so earlier references stay valid:
  - local P1: an incorrect relationship or unsupported classification that could materially mislead;
  - local P2: important evidence missing or inconsistent;
  - local P3: metadata or terminology with limited legal consequence.

  Indicative mapping of the NEW findings to the binding scale (for the legal adviser, who sets final priorities):

  | Finding | Local | EVIDENCE_STANDARD (indicative) | Reason |
  | --- | --- | --- | --- |
  | E8-XR-01 | P2 | P1 candidate | missing contrary (distinguishing) precedent on records that present Tarsem Singh as governing |
  | E8-XR-02 | P3 | P2 now; P1 candidate once an official S P Rathore copy is held | limiting treatment, evidenced only by an intern mirror |
  | E8-XR-04, -05, -07 | P3 | P2 | inconsistent registers / unusable cross-references |
  | E8-XR-06 | P3 | P2 | incomplete metadata affecting retrieval (one value evidenced, four unverified) |
  | E8-XR-08 | P3 | P2 | statutory wording overstated (permissive read as mandatory); low consequence |
  | E8-XR-09 | P3 | P2 | status label can mislead about open findings |

  Cosmetic items (for example an id year that differs from the decision year) were not reported.

## Counts

| Priority | NEW | EXISTING (re-confirmed, listed for traceability) |
| --- | --- | --- |
| P0 | 0 | 1 (r.23(3) caution conflict, C-01) |
| P1 | 0 | 3 (Ram Avtar URL OI-08/A-C2-01; Parashotam holding F-JUD-017; BSA/s.133 C-07) |
| P2 | 1 | 3 (case copy binding OQ-D-012; Isaac propagation D-CV-012; unheld 2026 authorities A-C2-05 etc.) |
| P3 | 7 | 8 (includes E8-XR-03, re-marked EXISTING after review RC-09) |
| **Total** | **8** | **15** |

The correction package (`correction_proposals.csv`) has 24 rows: 3 at P2 and 21 at P3. Twenty are PROPOSAL_NOT_APPLIED. Four (E8-CP-10 for PPS Bedi, Parashotam, Dharamvir and Ranjit Thakur) are UNVERIFIED_LEAD_NO_PROPOSAL: their held official copies print no neutral citation, so the values come only from the WS-B specification column and the intern mirror (review RC-05). There are more rows than findings because one finding can affect several records or register rows.

## Highest-priority unresolved risks

1. **Treatment propagation (NEW, P2, E8-XR-01).** A later judgment recorded against a case is not carried to every record that relies on that case. Girish Kumar (2026 INSC 149, held official copy `4f7ea3a4…` pp.15-16 para 22) held Tarsem Singh inapplicable to broad-banding re-computation claims and the AFT s.22(1)(c) bar inapplicable to them. AFT-013 and V7-SC-02 still give Tarsem Singh as the arrears authority without that distinction. The cause is that WS-B `affected_kb_ids` lists are hand-written and can be incomplete: WSB-T-005 holds only valid ids but omits AFT-013 and V7-SC-02. (Codes and wildcards in those lists, E8-XR-07, are a separate obstacle: 50 tokens in four registers that no propagation check can use.) The X19 check now in `xref_checks.py` catches the incomplete-list pattern deterministically for rows with explicit ids and should be run whenever a treatment row is added. On the binding EVIDENCE_STANDARD scale this is a P1 candidate (missing contrary precedent); the legal adviser sets the final priority.
2. **Existing P0/P1 items remain unapplied:**
   - the r.23(3) caution conflict (C-01);
   - CM-011's s.122 computation and missing s.123(2) (F-PROC-006/007). F-PROC-006 is recorded as disputed: independent reviewer A rated it P2 (a paraphrase ambiguity), and that position was adopted provisionally (PILOT-01 `post_review/post_review_dispositions.csv` D-05). F-PROC-007 is upheld;
   - the Parashotam row omitting its ratio on Shri Kant Sharma (F-JUD-017);
   - the BSA/s.133 interaction (C-07);
   - the Ram Avtar URL pointing at the S P Rathore judgment (A-C2-01).

   CM-011 and CM-025 still display SOURCE_REVIEWED status while these items are open (E8-XR-09).
3. **Current pension and administrative law rests on unheld sources.** These include the Girish clarification (2026 INSC 1113; only a commercial-mirror URL exists), Pooja Pal (2026), 2023 INSC 985, 2026 INSC 281, the DESW FAQ and MoD letters on ER 2023, and the PRA 2008 parts. The held ER 2023 copy is image-only and incomplete.
4. **Provenance hygiene.** Four citation-lead case records give the citing Ravinder Kumar order's URL as their accessible source (E8-XR-03; the records document it as a citing-document lead, so it is EXISTING, but the field label still misleads). 23 URL fields still point at commercial databases (EXISTING). No case record is byte-bound to its held official copy (EXISTING OQ-D-012).

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

It works against cases_53, the WS-B identity and holdings registers, and the C5 copy register. Its safety properties (hardened after review RC-02 and RC-10):

- It validates required fields and fails closed: one malformed item means exit status 2 and no report. Malformed includes duplicate JSON keys, duplicate item_id, NUL or other control characters, non-string list members, dates before 1800 or in the future, duplicate CSV header columns and a batch that is not valid UTF-8.
- It never merges. It refuses (exit 2) an `--out` that resolves to any input (same real path, `os.path.samefile`, or same device and inode, which covers symlinks and hard links), even with `--overwrite`; an `--out` inside a `curated_originals` directory; an existing file unless `--overwrite` is given; a directory; or a missing parent directory. The report is written to a temporary file in the target directory and then linked into place (no-clobber) or, with `--overwrite`, renamed.
- A known sha256 whose incoming court, case number or date contradicts the corpus is still EXACT_DUPLICATE but is flagged METADATA_CONFLICT_WITH_KNOWN_HASH (report `flags` column and a stderr warning). Strong classes need a typed case-number match; an untyped `n/yyyy` match is only POSSIBLE_MATCH_REVIEW.
- Report cells starting with `=`, `+`, `-`, `@`, TAB or CR are prefixed with `'`.
- Its output is deterministic.
- It states that NEW means only "not in the supplied snapshot", not absent from every collection.

**Tests:** `tools/test_reconcile_judgments.py`, 44 unittest cases, all passing (log in `work/unittest_output.txt`). They include symlinked, hard-linked, existing non-input and input `--out` paths. A smoke run on the real snapshot classified a synthetic 5-item batch built from known held copies as expected (`work/smoke_report.csv`, re-run after the changes with the same classes). Usage and limits are in `tools/README.md`.

## Limitations

- The review is targeted, not exhaustive. The sample is risk-weighted, so no corpus-wide error rate can be inferred from it.
- Deterministic checks are bounded by register linkage (the WS-B crosswalk) and by lexical patterns.
- Statutory verification used India Code government compilations (no Gazette copy of the 1950 Act is held). Judgment readings used PDF text layers. No new page-image checks were made.
- Unheld sources (DESW, MoD letters, most 2026 judgments, AFT Procedure Rules binary, BNS) could not be verified offline.
- The outputs are CSV/Markdown deliverables. They are not packaged as a `tools/legal_audit/validate.py` JSON package. If they are later imported into that structure, every row should carry `requires_legal_review=true`.
- No legal status, treatment or interpretation is determined. Every proposal needs legal-adviser and JAG review before any overlay is applied.

## Output files (CORPUS-QUALITY/)

- `cross_reference_findings.csv`, `cross_reference_findings.md`
- `high_risk_record_review.csv`, `HIGH_RISK_REVIEW.md`
- `correction_proposals.csv`
- `CORPUS_QUALITY_C8_FINDINGS.md` (this file)
- `OUTPUT_SHA256SUMS` (run `sha256sum -c OUTPUT_SHA256SUMS` from this directory)
- `tools/`: `reconcile_judgments.py`, `test_reconcile_judgments.py`, `README.md`, `xref_checks.py`, `select_sample.py`
- `work/`: `xref_candidates.csv`, `sample_selection.csv`, `unittest_output.txt`, `smoke_batch.jsonl`, `smoke_report.csv`, and the builders `build_hr.py`, `build_cp.py`, `build_findings.py`

**Reproducing.** From the repository root:

```
python legal_knowledge/audit_work/C8-SOURCES/CORPUS-QUALITY/work/build_hr.py . --check
python legal_knowledge/audit_work/C8-SOURCES/CORPUS-QUALITY/work/build_cp.py . --check
python legal_knowledge/audit_work/C8-SOURCES/CORPUS-QUALITY/work/build_findings.py . --check
python legal_knowledge/audit_work/C8-SOURCES/CORPUS-QUALITY/tools/select_sample.py . <out.csv> 3        # compare with work/sample_selection.csv
python legal_knowledge/audit_work/C8-SOURCES/CORPUS-QUALITY/tools/xref_checks.py . <held root> <out.csv>  # compare with work/xref_candidates.csv
```

The builders read only the curated JSONL files and the committed sample selection. `--check` proves the CSVs are deterministic, not that their hand-entered content is right. The page-text extracts used for verification were derived from held copies with PyMuPDF and are not committed (no text dumps in the repository); each reading in the CSVs cites the held file's sha256 and PDF page. Two readings rest on uncommitted derived texts with no held source binary, and cite those texts by sha256: AFT Procedure Rules r.18 (`c076b890…`) and Som Datt (`e03a7562…`, derived from WS-B intern copy `c6dd2135…`).
