# WS-B STATUS (issue #12)

Updated: 2026-11-22, at commit time.

## Done
- **Intake manifest** from intern `origin/raw-data@ad77758d`.
  - 4,259 judgment records collapsed to 3,951 distinct documents.
  - Independent lexical re-check, intake decision, carrier classification (policy v1).
- **Intern filter defects**: "invalidation" false positives (243 documents); precedents removed by the keyword filter (L. Chandra Kumar, S.R. Dhingra); no AFT judgments.
- **Identity resolution** for the 53 curated cases plus 14 KB/87-code cases.
  - 34 of the 53 mapped to intern documents by cover-page reading (answers OQ-D-012).
  - 13 of the 53 have an official copy held.
- **Holdings register**: 43 rows.
  - 16 judgments on official copies; 6 pages checked as page images.
  - 7 P0 pension cases plus Kuldeep pinned on the mirror only.
  - Isaac 2026 paras 19.4, 22, 28, 34, 35 and 39 classified.
- **Statutes / effective-dates register**: no effective date inferred; Army Rules chain per seed `11ce905e`.
- **Subsequent treatment**: 17 rows.
- **Adverse/conflict queue**: 16 items (A-16: role of Isaac Part III paras 14-16).
- **Pending source queue**: 22 rows.
- **Open questions**: 14, including WS-D OQ-D-004/008/009/012.
- **Crosswalk**: 208 rows, with per-case link counts and empty-holding citability flags.
- `validation_rules.md` V1–V11 and `tools/check_ws_b.py`.

## In progress
- None. This is a natural stopping point.

## Next
1. Review the 378 HOLD_FOR_REVIEW and 217 EXCLUDE_PROPOSED intake rows: spot-check a sample of 50.
2. Re-pin the P0 mirror-only holdings once official copies are obtained (PQ-004 to PQ-010).
3. Read the Naga 1997 operative directions; read the Ranjit bias/s.130 reasoning; map the Mullikote first-copy paragraphs.
4. Page-image check of Isaac pp.49-51, 61 and 69 (located on the text layer in this pass).
5. Run a treatment search in later intern SC documents (citations of the 53 cases) at proposition level.

## Blockers
- Official SC copies for the P0 mirror-only cases: the sci.gov.in search has a CAPTCHA, which must not be bypassed. Owner route needed (OQ-07).
- No AFT judgments are available: owner decision needed.
- Canonical intern snapshot unclear: raw-data counts differ from PROGRESS.md (OQ-01).

## Requests to the coordinator (paths owned by others)
- **WS-D**: consider a CI check that runs `legal_knowledge/audit_work/WS-B-JUDGMENTS/tools/check_ws_b.py`.
- **WS-A**: r.62(1) (reasons) and r.180 version history are needed for the SN Mukherjee and Virendra temporal notes.

## States
- Technical review only.
- Legal-advisor adjudication: NOT_STARTED for all rows.
- JAG validation: NOT_STARTED for all rows.
