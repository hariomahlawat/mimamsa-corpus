# WS-B STATUS (issue #12)

## Cycle 3 review fixes (PR #26)
- **F1, citation-lead pages off by one:** fixed. 77 rows corrected; 3 checked on page images, with the printed reporter page recorded separately.
- **F2, HEAD status and content type parsed together:** fixed.
  - BUTTAR is now classified as an official PDF URL that responds (availability only; not held). Its pending priority moves from P0 to P1.
  - Priority now comes from the explicit issue-#4 P0 list.
- **Evidence:** `REVIEW_FIXES_CYCLE3.md` and `review_fix_cycle3_corrected_rows.csv`. The regression check is `tools/check_cycle3_fixes.py`.

## Cycle 3 (worktree /home/user/ws-b-c3, branch claude/ws-b-cycle3, base 9b48b08e)

**Done (tasks 1–5).** Details are in the README "Cycle 3" section.

**For independent coordinator check:**
- Ram Avtar resolution (A-C2-01).
- Ram Sarup volume (A-C2-02).
- Naga conclusions (7)–(8) and (13)–(21) (mirror page images pp.53–54).
- Mullikote para 42 (page image p.26) and the para 33 wording (quoted para 125 says six months).
- Girish para 13 ("more than 800 appeals").
- Ranjit s.130 (page image p.6).
- CR-C3-01.

**Process deviation CR-C3-02.** The HEAD lookups were sent in pairs, less than 3 seconds apart: 22 requests to 2 hosts, with no body bytes. It is recorded and was not repeated.

**Next:**
- Obtain official copies (`pending_acquisition_cycle3.csv`).
- Read the Ram Sarup copy held on Hugging Face.
- Classify the citation leads in `subsequent_treatment_cycle3.csv` against the cited judgments' text.

**Blockers:**
- `api.sci.gov.in` HEAD returns 404 even for a known URL, so availability cannot be checked read-only.
- The court's search pages have a CAPTCHA.


## Cycle 2 (coordinator CYCLE 2 START; base 68290bae)
- Done: tasks 1-4 first pass (see README 'Cycle 2'). New files: intern_filter_audit.csv, allow_list_proposed.csv, intern_invalidation_false_positives.csv, case_relations.csv; new tools cycle2_filter_audit.py, cycle2_data.py.
- CC-09: Sonu identified as (2017) 8 SCC 570 from official Arjun (fn34, para 51); official copy not held -> PQ-C2-01. CC-11: all 13 KB records mapped to a case spec (Kuldeep - mirror-checked; Sukhdev, Nitisha MA 2023 - intern excluded log leads; Nalin Bhatia, Pooja Pal, 2023 INSC 985, 2026 INSC 281 - no copy, queued).
- For independent coordinator check: A-C2-01 (Ram Avtar URL = S P Rathore judgment), A-C2-03 (Shafhi identity vs Arjun), A-C2-04 (Nitisha MA removed by filter), A-C2-06 (PPS Bedi r.22/23 for officers, r.25 omitted 1993), Jasbir p.32 EEVFAM 'no absolute immunity' (H-048).
- Read-only network lookups this cycle: 2 SC office-report HTML pages + 2 empty directory probes on api.sci.gov.in (>=3 s apart, descriptive UA). No PDFs downloaded.
- Next: read HF-held Ram Sarup copy (A-C2-02); official copies for P0 mirror-only cases; review HOLD_FOR_REVIEW sample.


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
