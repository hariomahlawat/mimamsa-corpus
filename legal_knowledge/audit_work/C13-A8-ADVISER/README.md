# C13-A8: consolidated legal-adviser package

**Status: NOT LEGALLY REVIEWED.** Records only. Built by automated agents from questions the Cycle 12 and Cycle 13
workstreams had already raised. No legal conclusion is drawn, no citation is invented, and no record, status, edge,
register, frozen record, protected hash, AUTH-LEDGER entry (v0) or extractor is changed. Restricted material RM-001
is excluded from every question, anchor and output (checked by the validator and the test). Independent review of
this package is still required.

## What is here

| File | Content |
| --- | --- |
| `outputs/ADVISER_QUESTIONS_C13.csv` | 204 de-duplicated questions, one row each, with priority, the question, origin ids, affected records, an anchor summary and the adviser status columns (`adviser_answer_status` = `AWAITING_ADVISER`; `legal_review_status` = `NOT LEGALLY REVIEWED`) |
| `outputs/ADVISER_ANCHORS_C13.csv` | 1,103 anchors: `doc_id`, `sha256`, `page`, `page_kind`, the originating reference, and the register(s) that bind the doc_id to the hash and record a stored path |
| `outputs/DEDUP_MAP_C13.csv` | Every originating id (233) and the A8 question that carries it (PRIMARY or MERGED_DUPLICATE) |
| `outputs/ADVISER_BRIEF_C13.md` | Readable brief: how to use, priority rule, all P0/P1 questions in full, P2 by group |
| `outputs/BUILD_INFO.json` | Counts, input and register hashes, the A7 scan result |
| `tools/build_adviser_c13.py` | Builder (`--check` reproduces byte for byte) |
| `tools/validate_adviser_c13.py` | Validator: schema, de-duplication, anchor resolution, RM-001, reproducibility |
| `tools/a8_registers.py` | Read-only index over the committed registers |
| `../../../tests/test_legal_audit_c13_a8_adviser.py` | unittest suite (11 tests) |

## Counts (measured)

| Priority | Questions |
| --- | ---: |
| P0 | 1 |
| P1 | 34 |
| P2 | 169 |
| **Total** | **204** |

| Source | Origin items | Notes |
| --- | ---: | --- |
| C12 adviser package (`C12-CONSOLIDATION/adviser_package`) | 59 | all open (none was answered); C12 P3 mapped to P2 |
| A4 adviser packet (`C13-A4-STATUTORY/outputs/ADVISER_REVIEW_PACKET_A4.csv`) | 96 | 67 evidence promotions, 29 others |
| A6 forms | 12 | 11 questions phrased from the A6 register/R04 status/README (IAFD-905 included), plus review F07 |
| A5 | 14 | 12 OVERRULES/DISAPPROVES candidates; the 99 reconfirmed SC case numbers (one question); the 266 unreviewed candidates (one question) |
| A1 | 52 | the 6 `ALREADY_INGESTED_C12_MANUAL_REVIEW_REQUIRED` items, 45 further `CLASSIFICATION_UNCERTAIN` and 1 further `MANUAL_REVIEW_REQUIRED` document |
| A7 dispositions | 0 | no legal question; F01-F16 and the PR dispositions are owner/technical items (`BUILD_INFO.json` `a7_scan`) |
| **Total** | **233** | 29 merged as duplicates, 204 questions |

Kinds: 67 evidence promotion, 52 relevance scope, 30 status/relation, 15 commencement/temporal, 9 documentary
verification, 8 text conflict, 6 source authority, 6 legal interpretation, 5 form text, 3 cross-reference, 3 role/process.

Anchors: 831 source-page anchors on 449 distinct (doc_id, sha256) copies and 272 record anchors. 172 questions are
anchored to source pages throughout; 9 have at least one copy with no page stated in the originating artefact
(`NOT_STATED_IN_SOURCE`, for example the 266 unreviewed case numbers); 23 have only record anchors because the
originating artefact gives no source page (for example the temporal-axis and role questions).

## Rules applied

**De-duplication.** Two items are merged only when they ask the same thing:
- C12/A4 pairs where the A4 packet's `cross_refs` cites the C12 id and asks the same question (10 clusters: r.23(3),
  r.182, r.177, r.192, rr.193-194, instruments with no commencement clause, AFT s.9A, BNS/BNSS/BSA commencement,
  S.O. 4010/1986, IEA references);
- the five A4 CrPC cross-reference rows, which ask the identical question for different Army Act sections;
- the 12 A5 OVERRULES/DISAPPROVES candidates, which sit on passages C12 already asks about (Parashotam -> Shri Kant
  Sharma, Ajmer Singh, Mafatlal, V. Sriharan, Puttaswamy 2017, Joseph Shine);
- A6 review F07 (human spot-check before the legal gate), which is C12 AQ-ROL-03.

Related but distinct questions (for example C12 AQ-STA-19's CrPC limb and the merged A4 CrPC group) are kept apart.
Identical template wording is allowed only where the passage or target differs; such rows say so in `dedup_note`
(Mafatlal p.133 and Puttaswamy 2017 p.167 each carry two leads on one page). The validator rejects any two
questions with the same wording and the same source-anchor references, and any origin id mapped twice.

**Priority** (triage by operational impact; the adviser sets the final priority):
- **P0:** the answer controls the wording of a procedural safeguard put to an accused (r.23(3) only);
- **P1:** the answer controls whether a military-law authority or provision is current, binding or in force on a
  date, the operative text of a court-martial or court-of-inquiry rule, the pension-rules version, a form that blocks
  R04 closure or every template, or who may approve operational use;
- **P2:** everything else.

Originating priorities are kept in `origin_priorities`. A8 raised these C12 items by the rule: AQ-PEN-06 and
AQ-STA-03 (named known-supersession cases in the project acceptance checks, P2 to P1) and, through their A4 clusters,
AQ-STA-10, -11, -12, -15, -16 (P2 to P1) and AQ-STA-13, -14 (P3 to P1). No item was lowered except C12 P3 to P2
(three tiers only).

**Anchors.** Each source anchor gives `doc_id`, `sha256` and `page` with a `page_kind`. A source anchor passes only if a
committed register binds that doc_id to that sha256 and a committed register records a stored path for the sha256
(`tools/a8_registers.py`: the HF-5524c3d9 crawler manifest and hash ledger, the C12 copy-verification manifest, the
AUTH-LEDGER v0 copy register, the C12 HF-ingested re-download record, the A1 recovery population (HF paths of held
titles), the C12 and C13-A7 acquisition manifests and HF verification, the C11 re-acquisition manifest, the C12
judicial ingestion log). Durable repository/HF paths are preferred over scratch paths, and the validator rejects any
absolute (ephemeral) stored path. A record anchor passes only if the file exists and its hash equals the one
listed in that workstream's SHA256SUMS. Page numbers are carried as the originating artefact states them; A8 did not
open any source copy.

**Wording.** C12 and A4 question text is verbatim (merged items keep the other source's wording in `also_asked_as`).
A8 phrased the A6, A5 case-number and A1 relevance questions from what those artefacts record as open, using only
the identifiers, pages and quotations they record.

## Reproduce

```
PY=scratchpad/venv/bin/python   # any Python >= 3.11; standard library only
$PY -I -B legal_knowledge/audit_work/C13-A8-ADVISER/tools/build_adviser_c13.py --check
$PY -I -B legal_knowledge/audit_work/C13-A8-ADVISER/tools/validate_adviser_c13.py
$PY -B -m unittest tests.test_legal_audit_c13_a8_adviser
cd legal_knowledge/audit_work/C13-A8-ADVISER && sha256sum -c SHA256SUMS
```

## Review response (independent review `C13-A9-CLOSEOUT/reviews/REVIEW_A8_A9.md`)

- **F05 (P3):** 13 anchors carried ephemeral scratchpad paths. The stored path now comes from the C12 HF-ingested
  re-download record (revision `15bd03cc`) or the A1 recovery population (HF `3864faf3`), and the validator fails on any
  absolute stored path.
- **F06 (P3):** A8-Q143 now says the 1954 heading "reads, as OCR, 'sections 83-84'" and that A6 records it as
  NOT_DETERMINED.
- Question counts, priorities and anchors are unchanged (204; P0 1, P1 34, P2 169; 1,103 anchors).

## Limits

- Every page reading behind these questions is an AI reading; none is human-confirmed.
- The relevance (A1) and case-number (A5) questions are documentary; a non-legal reviewer may answer them if the
  owner so decides (see C13-A9 `OWNER_DECISIONS_C13.md`, legal reviewer appointment).
- The adviser has not been appointed. The package cannot be acted on until an appointed adviser answers it and each
  answer is applied by a separate reviewed change with owner approval.
