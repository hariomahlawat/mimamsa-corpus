# C8 / WS-E: high-risk record review

Per-record detail is in `high_risk_record_review.csv` (33 rows). The selection run is reproducible with `tools/select_sample.py <repo> <out> 3`, and its output is kept in `work/sample_selection.csv`.

## Selection method (defensible, deterministic)

1. **Domains.** Nine legal-consequence domains are defined by fixed keyword rules in `select_sample.py`: disciplinary authority, court-martial jurisdiction, statutory complaints, administrative remedies, pension/disability, procedural time limits, competing provisions, statutory amendments, and judicial overruling.
2. **Risk score.**

   `score = 3 × prior P0/P1 findings + 2 × min(crosswalk MISSING_EVIDENCE rows, 3) + 2 × date/amendment dependency + 1 × cites a judgment + 1 × status not SOURCE_REVIEWED`

   - Prior P0/P1 findings come from PILOT-01 corrections and CALIBRATION-02 proposals. They measure known uncertainty.
   - MISSING_EVIDENCE rows measure missing evidence.
3. **Picks.** The top 3 KB records per domain were taken (ties broken by id) and de-duplicated, giving 27 records.
4. **Cases.** Three case records with negative or qualifying later treatment in WS-B `case_relations.csv` were added.
5. **Manual additions (3).** The statutory-complaints keyword rule surfaced only weak proxies (ADM-013, ADM-023, AFT-009), so the two records that state the s.26 and s.27 rules directly were added (ADM-022, ADM-021). CM-012 (s.123) was also added as the companion to the s.122 record CM-011.

**Total: 33 records** (30 KB, 3 cases).

## How each record was reviewed

For each record the review recorded:

- an exact quote of the asserted proposition, and the source references the record itself gives;
- a check against the held authoritative copy, cited by sha256 and PDF page, or an explicit statement that no authoritative copy is held;
- amendment and date dependencies;
- inconsistent linked records;
- the remaining evidence-gap class;
- prior findings on the record;
- the C8 assessment, and a proposal where one is justified.

Records were never edited.

## Results

| Outcome | Records |
| --- | --- |
| Proposition verified against a held text, no new defect | ADM-021, AFT-009, ADM-023, CM-012, CM-SC-18, HCE-015, AFT-039 (EXISTING wording item), AFT-035, COI-046 |
| Existing P0/P1/P2 defect re-confirmed, no new defect | EV-016, HCE-010 (C-01 P0); HCE-017, CIV-008, AFT-004, CIV-034 (P1); ADM-014, PEN-013, V8-JD-02, DCLR-SC-2013-N08 (P2) |
| NEW defect | DCLR-SC-2008-N10 → E8-XR-01 (P2); PEN-WF-08 → E8-XR-02 (P3); ADM-022 → E8-XR-08 (P3); CM-011 → E8-XR-09 (P3, status label only) |
| No authoritative copy held, so not verifiable offline | ADM-013 (Kuldeep Yadav), ADM-027 (2023 INSC 985 and 2026 INSC 281 unidentified), ADM-015 (Sukhdev Singh), PEN-001/PEN-013/PEN-019 (DESW FAQ, MoD letters; ER 2023 held copy is image-only and incomplete), AFT-032 (Procedure Rules r.18: unpinned OCR text only), V8-JD-03 (Balbir Singh), CIV-032 (BNS limb) |
| Case metadata/copy-binding gap (EXISTING) | DCLR-SC-2005-L01: official copy `3b753548…` is held, but the record has no date or citation |

Verified statutory text points:

- **Army Act** (compilation `e47a4265…`):
  - s.26(2) "may complain" (p.16)
  - s.27 (p.16)
  - s.81(3)-(4) and s.81(1) omitted (p.28)
  - s.122 three years with the 1992 commencement limbs (p.35)
  - s.123(2) three years post-cessation (p.35)
  - s.127 omitted (p.7)
- **AFT Act** (`665863d1…`): s.14(4)(f) review power (p.9); s.21(2)(a)-(b) and s.22 (p.11); s.26(2) 14-day vacation rule (pp.12-13)
- **BSA** (`554b2b4a…`): s.1(2) applies to courts-martial (p.10)
- **BNSS** (`572c7988…`): s.531 repeal and savings (p.174)
- **Army Rules** (compilation `48f52219…`): r.25 omitted by SRO 17(E) 6-12-1993 (p.45); r.197A present

**Evidence-gap pattern across the sample.** The statutory propositions are mostly accurate against the government compilations, but no Gazette copy of the 1950 Act is held, so the evidence class remains GOVERNMENT_COMPILATION_ONLY. The material risk sits in two places:

- pension and administrative records that rely on DESW explainers, MoD letters and judgments not held officially;
- treatment propagation, where a later judgment is recorded against a case but not carried to every record that relies on it (E8-XR-01).

## Limitations

- The sample is risk-weighted, not random, so it does not estimate a corpus-wide defect rate.
- Domain assignment is keyword-based.
- Judgment readings by C8 used text layers. No page-image re-checks were made in this cycle.
- No legal-status or treatment determination is made here. Every proposal is PROPOSAL_NOT_APPLIED and is for legal-adviser and JAG review.
