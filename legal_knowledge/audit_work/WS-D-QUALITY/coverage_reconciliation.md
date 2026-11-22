# Coverage reconciliation: WS-C kb658 inventory vs WS-D scorecard

WS-C input: `legal_knowledge/audit_work/WS-C-MML/kb658_source_coverage_inventory.csv` at `origin/claude/ws-c-mml` @ `a4c68cf24391` (sha256 `ef0775cf34f4…`), read-only via `git show`. WS-D: `scripts/coverage_scorecard.py`, crawler corpus `origin/raw-data` @ `ad77758d4569`. KB sha `9a8f0d193065…`.

**Coverage locates cited sources. It never says that a record is legally correct, current, or verified.**

## 1. Definitions side by side

| Aspect | WS-C (`build_kb658_inventory.py`) | WS-D (`coverage_scorecard.py`) |
| --- | --- | --- |
| Question answered | Is each citation anchored to an identified source held in the corpus, with a pinpoint and no broken flags? | Does every cited source exist as a document the database can search? |
| Citation parser | own `kb_citations.py`: v3 codes + AA/AR pinpoints by context + other-statute names + case pattern (references + sources) | PILOT-01 `build_code_inventory.py` codes (v3 grammar); plain-text records via `plaintext_citation_index.csv` segments |
| Code held | firm or co-citation class and target starts `act-`/`rules-`/`DCLR-`, not '(candidate)' | target is a DCLR id present in cases_53, or a doc_id present in crawler `data/meta` |
| Co-citation codes | never FULL (PARTIAL at best) | target counted if searchable; inferred status scored separately (citation_resolution_score) |
| Plain statutes | AA/AR pinpoints always anchors; fixed held list (BSA, BNSS, BNS, CrPC, Evidence Act, AFT Act, Procedure Rules, Air Force Act, Navy Act) | AA, AR, AFT Act, BNS, BNSS, BSA mapped to crawler doc_ids; Act sections checked against corpus section files |
| Pinpoint | required for FULL | not required |
| Placeholders, structural flags | downgrade FULL | ignored for searchability (reported in index) |
| Plain case names | counted as citation; unresolved flag | not counted as statute; case-or-locator-only record = NONE |
| States | FULL / PARTIAL / SOURCE_GAP / UNRESOLVED / NO_CITATION | coded: ALL / PARTLY / NONE searchable; plain: ALL / PARTLY / NOT searchable, CASE_OR_LOCATOR_ONLY, NO_STATUTE_OR_CASE |
| Denominator | 658 records, one state each | 658 records, one state each (389 coded + 269 plain) |

## 2. State totals

| WS-C state | n | | WS-D state | n |
| --- | --- | --- | --- | --- |
| FULL | 379 | | D_CODED_ALL_SEARCHABLE | 279 |
| NO_CITATION | 78 | | D_CODED_NONE_SEARCHABLE | 56 |
| PARTIAL | 131 | | D_CODED_PARTLY_SEARCHABLE | 54 |
| SOURCE_GAP | 56 | | D_PLAIN_ALL_STATUTE_SEARCHABLE | 169 |
| UNRESOLVED | 14 | | D_PLAIN_CASE_OR_LOCATOR_ONLY | 25 |
|  |  | | D_PLAIN_NO_STATUTE_OR_CASE | 66 |
|  |  | | D_PLAIN_PARTLY_SEARCHABLE | 6 |
|  |  | | D_PLAIN_STATUTE_NOT_SEARCHABLE | 3 |

Mapping to coarse buckets: WS-C FULL→COMPLETE, PARTIAL→PARTIAL, SOURCE_GAP/UNRESOLVED→NONE, NO_CITATION→NO_CITATION; WS-D *_ALL_*→COMPLETE, *_PARTLY_*→PARTIAL, *_NONE_*/STATUTE_NOT_SEARCHABLE/CASE_OR_LOCATOR_ONLY→NONE, NO_STATUTE_OR_CASE→NO_CITATION.

## 3. Agreement matrix (coarse buckets; rows WS-C, columns WS-D)

| WS-C \ WS-D | COMPLETE | PARTIAL | NONE | NO_CITATION | total |
| --- | --- | --- | --- | --- | --- |
| COMPLETE | 372 | 6 | 1 | 0 | 379 |
| PARTIAL | 76 | 54 | 1 | 0 | 131 |
| NONE | 0 | 0 | 70 | 0 | 70 |
| NO_CITATION | 0 | 0 | 12 | 66 | 78 |

**Agreement: 562/658 (85.4%).** Disagreements: 96; with at least one explanation tag: 96; unexplained: 0.

## 4. Fine-grained matrix (WS-C state × WS-D state)

| WS-C \ WS-D | D_CODED_ALL_SEARCHABLE | D_CODED_NONE_SEARCHABLE | D_CODED_PARTLY_SEARCHABLE | D_PLAIN_ALL_STATUTE_SEARCHABLE | D_PLAIN_CASE_OR_LOCATOR_ONLY | D_PLAIN_NO_STATUTE_OR_CASE | D_PLAIN_PARTLY_SEARCHABLE | D_PLAIN_STATUTE_NOT_SEARCHABLE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FULL | 208 | 0 | 0 | 164 | 0 | 0 | 6 | 1 |
| NO_CITATION | 0 | 0 | 0 | 0 | 12 | 66 | 0 | 0 |
| PARTIAL | 71 | 0 | 54 | 5 | 0 | 0 | 0 | 1 |
| SOURCE_GAP | 0 | 55 | 0 | 0 | 0 | 0 | 0 | 1 |
| UNRESOLVED | 0 | 1 | 0 | 0 | 13 | 0 | 0 | 0 |

## 5. Explained differences (tag counts over disagreeing records; a record can carry several)

| Rule | Records | Meaning |
| --- | --- | --- |
| R1_CO_CITATION | 39 | WS-C never rates a record FULL if a code is resolved only by co-citation; WS-D counts the co-citation target as searchable. |
| R2_NO_PINPOINT | 32 | WS-C FULL requires a pinpoint; WS-D searchability does not. |
| R3_STRUCTURAL_FLAG | 3 | WS-C downgrades FULL on provision-not-in-heading-index, Army Act/Rules cited without pinpoint, or non-official URL; WS-D has no such gate. |
| R4_PLACEHOLDER | 6 | WS-C counts [VERIFY]/'verify' placeholders as unresolved; WS-D ignores placeholders for searchability. |
| R5_GAP_CODE | 0 | Record has a firm code whose target is a declared GAP: WS-C counts it as a source gap; WS-D as not searchable. |
| R6_PLAIN_CASE | 3 | Plain-text case citation: WS-C flags it unresolved (and counts it as a citation); WS-D excludes case names from statute searchability (case-or-locator-only = NONE). |
| R7_PLAIN_INSTRUMENT_SET | 13 | Plain statute set differs: WS-C treats AA/AR pinpoints and a fixed held list (incl. CrPC, Evidence Act, Air Force/Navy Act, Procedure Rules) as anchors without checking the corpus; WS-D maps only AA/AR/AFT Act/BNS/BNSS/BSA to crawler doc_ids. |
| R8_NO_CITATION_DEFINITION | 12 | NO_CITATION differs: WS-C requires a code, AA/AR pinpoint, held statute name or case pattern; WS-D counts any statute token (incl. 'AR trial rules') or locator continuation as a reference. |
| R9_UNRESOLVED_CODE | 2 | Record has a PROBABLE/CATEGORY_ONLY/UNRESOLVABLE code: WS-C counts it unresolved whatever its target; WS-D searchability looks only at whether the register target exists (identity class is scored separately in citation_resolution_score). |
| R11_PLAIN_NAME_IN_CODED_RECORD | 3 | Coded record that also names a statute in plain text outside WS-C's held list (e.g. 'Constitution'): WS-C counts it as a gap; WS-D scores coded records by their codes only. |
| R10_TARGET_EXISTENCE | 0 | WS-D checks the register target exists (DCLR id in cases_53; doc_id in crawler corpus); WS-C accepts any act-/rules-/DCLR- prefix not marked '(candidate)'. |

Code sets agree on 658/658 records. (Both sides use the PILOT-01 v3 code grammar.)

## 6. Proposed canonical definition set (PROPOSAL ONLY; needs coordinator/owner decision)

Report **three separate, named measures** over the same 658 denominator instead of one blended state. Each must be computed by one shared, committed parser (proposal: WS-C `kb_citations.py` grammar extended with the WS-D plain-text segment index, so code sets and plain segments are identical on both sides):

1. **CITATION_PRESENT** (yes/no + kind): the record cites at least one code, statute token, statute locator or case. Placeholders and editorial labels are not citations. This replaces both NO_CITATION definitions (closes R8).
2. **SOURCE_IDENTIFIED** (ALL / PARTLY / NONE): each citation resolves to an identified instrument or judgment. Firm register classes only; co-citation is reported separately as INFERRED and never counted as identified (closes R1). Gap codes are NONE (R5); PROBABLE/CATEGORY_ONLY/UNRESOLVABLE are NONE (R9); plain case names are NONE until WS-B resolves them (R6).
3. **SOURCE_SEARCHABLE** (ALL / PARTLY / NONE / NOT_CHECKED): every identified source exists in a searchable corpus, checked by existence (DCLR id in cases_53; doc_id in crawler `data/meta`; Act section file where a section is cited) (closes R10 and R7: one instrument map, held list = instruments actually present in the corpus).

Pinpoint presence (R2), placeholders (R4) and structural flags (R3) become **quality flags reported alongside**, not gates inside the coverage state. Then 'FULL' would be the derived conjunction CITATION_PRESENT ∧ SOURCE_IDENTIFIED=ALL ∧ SOURCE_SEARCHABLE=ALL ∧ pinpoint ∧ no flags, published with its own name, e.g. `ANCHORED_FULL`. No measure implies text verification or legal correctness.

Per-record detail: `coverage_reconciliation.csv` (one row per record: both states, buckets, agreement, explanation tags, code sets, WS-C flags).
